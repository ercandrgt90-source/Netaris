"""Yayimlanan her sayiyi KAYNAGIYLA karsilastirir ve gerekirse duzeltir.

    depo  ->  kaynaktan yeniden hesapla  ->  karsilastir  ->  (--duzelt)

NEDEN VAR
---------
`denetim.py` sayinin MAKUL olup olmadigina bakiyor: araligi, birimi,
etiketi, tazeligi. Hicbiri "bu sayi DOGRU MU" sorusunu sormuyor --
cunku cevap yalnizca kaynaga sorularak bulunur.

Olculdu ve YAYIMLANDI: ABD TUFE yillik degisimi %3,73 diye basildi,
dogrusu %3,46 idi. Sebep `uret_takvim.py` icinde konum aritmetigiydi
(`g[i - 12]`, yani "on iki gozlem geri"). FRED'in CPIAUCSL serisinde
2025-10 gozlemi YOK; bosluktan sonraki her gozlem icin on iki konum
geri gitmek ON UC AY geri gitmek anlamina geliyordu.

Hata SESSIZDI ve sessiz kalmasinin sebebi onemli: deger makul
araliktaydi (%3,73 bir enflasyon orani olabilir), birim dogruydu,
etiket dogruydu, tazelik uygundu. Yani var olan butun denetimler
"temiz" diyordu. Bir sayinin makul gorunmesi, dogru oldugu anlamina
gelmiyor.

NE YAPIYOR
----------
Depodaki her FRED gozlemi icin seriyi kaynaktan yeniden cekiyor,
serinin `sunum` kuralini (seviye / aylik degisim / yillik degisim)
TARIHE GORE yeniden uyguluyor ve sonucu depodakiyle karsilastiriyor.

TOLERANS var cunku FRED serileri REVIZE EDILIYOR: gecmis bir ayin
endeksi sonradan duzeltilebiliyor ve o durumda depodaki eski deger
"yanlis" degil, ESKI. Ikisini ayirmak icin sapma esigi kullaniliyor;
esigin uzerindeki fark hesap hatasi, altindaki revizyon sayiliyor.

    python veri_dogrula.py            # yalnizca rapor, cikis 0/1
    python veri_dogrula.py --duzelt   # sapan degerleri depoda duzelt
    python veri_dogrula.py --sessiz   # yalnizca sapmalari bas
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import beyin          # noqa: E402
import evds           # noqa: E402
import makro          # noqa: E402
import takvim         # noqa: E402
import uret_takvim    # noqa: E402

#: MANSET SERISI OLMAKTAN CIKMIS ama depoda verisi duran seriler.
#:
#: Bunlar `takvim.SERILER`de yok, dolayisiyla sunum kurallari orada
#: bulunamiyor. Denetim disi birakmak yanlis: depodaki her deger
#: yayimlanabilir durumda.
EMEKLI_SUNUM = {
    # Mevsimsellikten arindirilmis TUFE. Manset NSA'ya gecti
    # (bkz. `kaynak/takvim.py`), bu ikisi gecmis kayit olarak duruyor.
    "CPIAUCSL": "yillik",
    "CPILFESL": "yillik",
}

#: Kac gozlem geriye bakiliyor. Yillik degisim icin en az 13 gozlem
#: gerekiyor; 40 iki yildan fazlasini kapsiyor ve tek istekte geliyor.
PENCERE = 40

#: Sapma esigi. Altindaki fark GURULTU (yuvarlama), ustundeki
#: raporlanacak bir sapma sayiliyor.
#:
#: MUTLAK esik tek basina yetmiyor: "%" serilerinde 0,02 anlamli bir
#: fark, ama cari islemler dengesi MILYON DOLAR cinsinden ve orada 2
#: birimlik fark yuvarlama gurultusu. Bu yuzden ORAN esigi de var --
#: sapma hem mutlak hem oransal esigi asmali.
#:
#: SAPMANIN SEBEBI HER ZAMAN HATA DEGIL. Iki ayri sey ayni testten
#: gecmis oluyor:
#:   * HESAP HATASI  -- bizim tarafimizda yanlis hesaplanmis deger
#:   * REVIZYON      -- kaynak sayiyi sonradan duzeltmis
#: Ikisinde de dogru davranis AYNI: kaynagin bugunku degerini almak.
#: Revizyon da yeni veridir; onu almamak, eski bir sayiyi yayimda
#: tutmak demek. Ayrim rapor icin onemli, eylem icin degil.
#:
#: 0,02 secildi: FRED revizyonlari tipik olarak ikinci ondalikta
#: kaliyor, hesap hatalari ise (13 ay / 12 ay gibi) ondalik oncesinde
#: ya da hemen sonrasinda buyuk fark uretiyor -- olculen ornek 0,26
#: puandi, esigin on uc kati.
ESIK = 0.02

#: Oransal esik. 0,005 = binde bes.
ORAN_ESIK = 0.005


def _beklenen(kod: str, sunum: str, gozlemler) -> dict[str, float]:
    """Serinin her tarihi icin OKURA GOSTERILMESI gereken deger."""
    tarihli = {o.tarih: o.deger for o in gozlemler}
    cikti: dict[str, float] = {}
    for o in gozlemler:
        if sunum == "yillik":
            taban = tarihli.get(uret_takvim._bir_yil_once(o.tarih))
            if not taban:
                continue
            cikti[o.tarih] = (o.deger - taban) / taban * 100
        elif sunum == "degisim":
            taban = tarihli.get(uret_takvim._bir_ay_once(o.tarih))
            if taban is None:
                continue
            cikti[o.tarih] = o.deger - taban
        else:
            cikti[o.tarih] = o.deger
    return cikti


def calistir(duzelt: bool = False, sessiz: bool = False) -> int:
    seriler = {s[0]: s for s in takvim.SERILER}

    with beyin.baglan() as b:
        depo: dict[str, dict[str, float]] = {}
        for kod, tarih, deger in b.execute(
                # ETIKETLE DEGIL KODLA suzuluyor.
                #
                # `kaynak` alani iki farkli deger tasiyor: "FRED" ve
                # "FRED (St. Louis Fed)" -- iki ayri hat ayni veriyi
                # farkli adlandirmis. Olculdu: esitlikle sorgulayan ilk
                # surumum 3537 gozlemin yalnizca 330'unu denetliyordu,
                # yani verinin %9'unu. Geri kalani "temiz" raporunun
                # icinde gorunmez kaldi.
                #
                # Kod deseni daha saglam: TP.* TCMB'nin, digerleri
                # FRED'in. Yeni bir etiket yazimi bu suzgeci bozmuyor.
                "SELECT kod, tarih, deger FROM gosterge"
                " WHERE kod NOT LIKE 'TP.%' AND kod NOT LIKE 'ECB!_%' ESCAPE '!'"
                " AND kod <> 'TCMB_POLITIKA'"):
            depo.setdefault(kod, {})[tarih] = float(deger)

    sapan: list[tuple] = []
    okunamayan: list[str] = []
    bakilan = 0

    # EMEKLI SERILER DE DENETLENIYOR.
    #
    # Ilk yazimda `seriler.get(kod)` bos donunce seri ATLANIYORDU.
    # Olculdu: `CPIAUCSL` manset serisi olmaktan cikarilinca (NSA'ya
    # gecildi) depodaki YANLIS degerleri denetim disi kaldi ve
    # yayimlanmis sayfalarda durmaya devam etti.
    #
    # Depoda duran her sey yayimlanabilir; dolayisiyla denetlenmeli.
    # Emekli serinin sunum kurali `EMEKLI_SUNUM`dan okunuyor.
    for kod in sorted(depo):
        s = seriler.get(kod)
        sunum = s[6] if s else EMEKLI_SUNUM.get(kod)
        if not sunum:
            continue
        try:
            seri = makro.fred(kod, son_n=PENCERE)
        except Exception as e:                       # noqa: BLE001
            # Kaynaga ulasilamadi: bu bir VERI hatasi degil, AG hatasi.
            # Sessizce "dogru" demiyoruz, ayrica raporluyoruz.
            okunamayan.append(f"{kod}: {type(e).__name__}")
            continue
        if not seri or not getattr(seri, "gozlemler", None):
            okunamayan.append(f"{kod}: bos seri")
            continue

        beklenen = _beklenen(kod, sunum, list(seri.gozlemler))
        for tarih, bizdeki in sorted(depo[kod].items()):
            if tarih not in beklenen:
                continue
            bakilan += 1
            fark = abs(beklenen[tarih] - bizdeki)
            if fark > ESIK and fark > abs(bizdeki) * ORAN_ESIK:
                sapan.append((kod, tarih, bizdeki, beklenen[tarih], fark, sunum))

    # --- TCMB / EVDS ---
    #
    # NEDEN AYRI: EVDS yillik degisimi KENDISI hesapliyor
    # (`formulas=3`), yani bizde konum aritmetigi yok ve FRED'de
    # bulunan hata sinifi burada olusamiyor. Denetlenen sey hesap
    # degil, AKTARIM: depodaki sayi TCMB'nin verdigi sayiyla ayni mi.
    #
    # Bir sayi yolda bozulabilir -- yanlis formul parametresi, birim
    # karismasi, tarih kaymasi. Olculmus ornek var: EVDS formulu
    # DUZEY'e sabitlendiginde TUFE "%132,31" diye yayimlanmisti.
    #
    # ANAHTAR YOKSA ATLANIR ama SESSIZ DEGIL: yerelde anahtar
    # bulunmuyor, CI'da bulunuyor. "Denetlemedik" ile "temiz" ayri
    # seyler ve rapor bunu soyluyor.
    if evds.anahtar():
        evds_seriler = {x[0]: x for x in evds.SERILER}
        with beyin.baglan() as vb:
            evds_depo: dict[str, dict[str, float]] = {}
            for kod, tarih, deger in vb.execute(
                    "SELECT kod, tarih, deger FROM gosterge"
                    " WHERE kod LIKE 'TP.%'"):
                evds_depo.setdefault(kod, {})[tarih] = float(deger)
        for kod, tarihler in sorted(evds_depo.items()):
            tanim = evds_seriler.get(kod)
            if not tanim:
                continue
            try:
                seri = evds.cek(kod, tanim[1], tanim[2], tanim[3], tanim[4])
            except Exception as e:                    # noqa: BLE001
                okunamayan.append(f"{kod}: {type(e).__name__}")
                continue
            kaynakta = {o.tarih: float(o.deger)
                        for o in getattr(seri, "gozlemler", [])}
            for tarih, bizdeki in sorted(tarihler.items()):
                if tarih not in kaynakta:
                    continue
                bakilan += 1
                fark = abs(kaynakta[tarih] - bizdeki)
                if fark > ESIK and fark > abs(bizdeki) * ORAN_ESIK:
                    sapan.append((kod, tarih, bizdeki, kaynakta[tarih],
                                  fark, "EVDS aktarim"))
    else:
        okunamayan.append("EVDS: anahtar yok -- TCMB serileri DENETLENMEDI")

    if not sessiz:
        print("=" * 68)
        print("  VERI DOGRULAMA -- depo ile kaynak karsilastirmasi")
        print("=" * 68)
        print(f"  bakilan gozlem : {bakilan}")
        print(f"  sapan          : {len(sapan)}")
        if okunamayan:
            print(f"  OKUNAMAYAN     : {len(okunamayan)}")
            for x in okunamayan:
                print(f"      {x}")

    if sapan:
        print()
        print(f"{'kod':<16}{'tarih':<12}{'depoda':>12}{'kaynakta':>12}"
              f"{'fark':>9}  sunum")
        for kod, tarih, bizdeki, dogru, fark, sunum in sapan[:40]:
            print(f"{kod:<16}{tarih:<12}{bizdeki:>12.4f}{dogru:>12.4f}"
                  f"{fark:>9.4f}  {sunum}")
        if len(sapan) > 40:
            print(f"... ve {len(sapan) - 40} tane daha")

    if duzelt and sapan:
        with beyin.baglan() as b:
            for kod, tarih, _b, dogru, _f, _s in sapan:
                b.execute("UPDATE gosterge SET deger=? WHERE kod=? AND tarih=?",
                          (dogru, kod, tarih))
            b.commit()
        print()
        print(f"  {len(sapan)} deger DUZELTILDI.")
        return 0

    if not sessiz and not sapan:
        print()
        print("  Butun degerler kaynagiyla uyusuyor.")
    return 1 if sapan else 0


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--duzelt", action="store_true",
                   help="sapan degerleri depoda duzelt")
    a.add_argument("--sessiz", action="store_true")
    n = a.parse_args()
    return calistir(duzelt=n.duzelt, sessiz=n.sessiz)


if __name__ == "__main__":
    raise SystemExit(main())
