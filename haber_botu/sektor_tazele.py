# -*- coding: utf-8 -*-
"""Defterde SEKTORU EKSIK sirketleri doldurur.

    python sektor_tazele.py --sinir 40
    python sektor_tazele.py --kuru-calis     # yazmadan olc

BU DOSYA NEDEN VAR
------------------
`uret_bilanco --hepsi` sektor listesini defterdeki `sektor_tr`
alanindan kuruyor. O alani OLMAYAN sirket hicbir sektore dusmuyor,
yani bilanco hattinin gorus alaninda HIC YOK -- kac kosu kosulursa
kosulsun sayfasi uretilmiyor.

Koddaki gerekce "cogu icin bu dogru ve kasitli -- fon, varant,
yatirim ortakligi" diyordu. YARISI DOGRUYDU.

OLCULDU (2026-10-13): defterdeki 794 sirketin 441'inde `sektor_tr`
yok. Bu 441'den rastgele 25 ornek kaynaga soruldu:

    sektoru BULUNAN      13   KONYA (Temel malzeme), OBAMS (Temel
                              tuketim), LKMNH (Saglik), OYYAT
                              (Finans), GSRAY (Iletisim)...
    gercekten sektorsuz  12   varlik kiralama, menkul degerler

Yani kabaca 230 GERCEK sirket, yalnizca defterdeki bir alan bos
oldugu icin hic yayimlanmiyor. Kullanici "GSRAY'in bilancosu
aciklandi, bizde ne zaman cikar" diye sordugunda ortaya cikti:
GSRAY da bu listedeydi.

NE YAPIYOR
----------
Eksik alanlari kaynaktan ALIR ve deftere yazar. Kaynak sektor
vermiyorsa (gercekten sektorsuz kayit) dokunmaz -- "bilmiyorum" ile
"yok" ayni sey degil ve uydurma sektor, yanlis sektor medyani demek.

RESUMABLE: her kosu `--sinir` kadar sirkete bakiyor ve yazdigini
hemen kaydediyor. Kaynak kapanirsa kalan bir sonraki kosuda.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK / "kaynak"))

import sektor                                      # noqa: E402

DEFTER = _KOK / "kaynak" / "sirketler.json"

#: Bir kosuda kac sirkete sorulacak. Kaynak 429 vermeye baslamasin
#: diye kucuk tutuluyor; is RESUMABLE, kalan sonraki kosuda.
VARSAYILAN_SINIR = 40


#: Kaynakta bulunamayan sirket kac gun sonra YENIDEN deneniyor.
#:
#: Yeni kodlar listeye giriyor, yani "yok" kalici bir cevap degil.
#: Ama her kosuda tekrar sormak kuyrugu TIKIYOR (asagida).
YENIDEN_DENEME_GUN = 90


def eksikler(defter: dict) -> list:
    """Sektoru olmayan BUTUN sirketler -- sayim ve hedefli kip icin."""
    return sorted(k for k, v in defter["sirketler"].items()
                  if not v.get("sektor_tr"))


def kuyruk(defter: dict, bugun=None) -> list:
    """Bu kosuda SORULABILECEK sirketler.

    NEDEN `eksikler`DEN AYRI -- OLCULDU (2026-10-31, kosu #62)
    ---------------------------------------------------------
    Kuyruk `eksik[:sinir]` idi: alfabetik ve her kosuda AYNI ilk 25
    sirket. O ilk 25'in basindaki besi kaynakta YOK (gunluk:
    "5 x HTTP 404") ve adim onlari kisitlama sanip kendini
    kapatiyordu. Yani 438 sirket KALICI olarak kilitliydi -- adim
    aylardir hicbir sey yazmadi ve her kosuda YESIL dondu.

    Durum kodu ayrimi tek basina yetmez: 404 alan sirket kuyrugun
    basinda KALIR ve sira asla ilerlemez. Bu yuzden yokluk
    TARIHIYLE isaretleniyor ve `YENIDEN_DENEME_GUN` boyunca
    kuyruktan cikiyor. Isaret kalici degil: yeni kodlar listeye
    giriyor.

    SEKTOR ALANINA DOKUNULMUYOR. Isaret ayri bir alan; yanlis bir
    sektor yazmak sektor medyanini bozar ve sayfa gercek olmayan bir
    "sektore gore konum" iddiasi tasir.
    """
    import datetime as _dt                            # noqa: PLC0415
    bugun = bugun or _dt.date.today()
    cikti = []
    for kod in eksikler(defter):
        iso = (defter["sirketler"][kod] or {}).get("sektor_bulunamadi")
        if isinstance(iso, str):
            try:
                gecen = (bugun - _dt.date.fromisoformat(iso)).days
                if gecen < YENIDEN_DENEME_GUN:
                    continue
            except ValueError:
                pass            # bozuk tarih: kuyrukta KALSIN
        cikti.append(kod)
    return cikti


def tazele(sinir: int = VARSAYILAN_SINIR, kuru: bool = False,
           kodlar: list | None = None) -> dict:
    d = json.loads(DEFTER.read_text(encoding="utf-8"))
    eksik = eksikler(d)
    if kodlar:
        # BELIRLI SIRKETLER -- SIRA BEKLEMEDEN.
        #
        # Donen kuyruk 441 sirketi kosu basina 40'tan geciyor, yani
        # belirli bir sirkete sira gelmesi gunler aliyor. Okurun
        # sordugu sirket (GSRAY) kuyrugun ortasindaydi.
        #
        # Kural AYNI kaliyor: alani zaten dolu olan sirkete
        # DOKUNULMUYOR ve kaynak sektor vermiyorsa yine yazilmiyor.
        istenen = [k.upper() for k in kodlar]
        secilen = [k for k in istenen if k in eksik]
        atlanan = [k for k in istenen if k not in eksik]
        print(f"sektor tazele: istenen {len(istenen)}, "
              f"eksik olan {len(secilen)}")
        for k in atlanan:
            var = k in d["sirketler"]
            print(f"  {k:<9}DOKUNULMADI -- "
                  f"{'sektörü zaten dolu' if var else 'defterde YOK'}")
    else:
        _kuyruk = kuyruk(d)
        secilen = _kuyruk[:sinir]
        print(f"sektor tazele: {len(eksik)} eksik, "
              f"{len(_kuyruk)} sorulabilir, bu kosuda {len(secilen)}")
        if len(eksik) != len(_kuyruk):
            print(f"  ({len(eksik) - len(_kuyruk)} sirket kaynakta "
                  f"BULUNAMADI -- {YENIDEN_DENEME_GUN} gun sonra "
                  f"yeniden sorulacak)")

    yazilan, bossuz, hata = [], [], 0
    ardisik_bos = 0
    import datetime as _dt                              # noqa: PLC0415
    bulunamayan = []
    for kod in secilen:
        onceki_hata = len(sektor.OKUNAMAYAN)
        try:
            r = sektor.cek(kod)
        except sektor.Bulunamadi:
            # KAYNAKTA YOK -- KISITLAMA DEGIL.
            #
            # Ardisik red sayaci ISLETILMIYOR: `bilanco_ag` bu
            # ayrimi yillardir yapiyor, buraya yayilmamisti ve
            # bedeli olculdu (kosu #62: "5 x HTTP 404" ->
            # "KAYNAK KAPANDI -- 5 ardisik red").
            #
            # Yokluk TARIHLE isaretleniyor ki kuyruk ILERLESIN;
            # yoksa ayni bes sirket her kosuda yine basta olurdu.
            bulunamayan.append(kod)
            d["sirketler"][kod]["sektor_bulunamadi"] = (
                _dt.date.today().isoformat())
            ardisik_bos = 0
            # BEKLEME BU MODULUN ARALIGIYLA.
            #
            # `bilanco_ag.ara_ver()` yazilmisti; ayni sunucu olsa da
            # o AYRI bir aralik ve AYRI bir "kapandi" mandali
            # tutuyor. Tek dongude iki aralik sistemi, `ARA_SN`in
            # basina geleni geri getirirdi: hangi degerin
            # uyarlandigi belirsizlesir.
            time.sleep(sektor.ARA_SN)
            continue
        except Exception:
            hata += 1
            continue

        # "CEKILEMEDI" ILE "SEKTORU YOK" AYRI SEYLER.
        #
        # Ilk yazimda ikisi ayni sayiliyordu ve olcum YANILTTI:
        # 40 sirketin 39'u "kaynakta yok" diye bildirildi, oysa
        # hepsi HTTP 429 idi -- kaynak beni yavaslatiyordu. Ayni
        # kosuda rastgele bir orneklem 25'te 13 sektor bulmustu.
        #
        # Olcut `sektor.OKUNAMAYAN` listesinin BUYUMESI: cek()
        # basarisiz oldugunda oraya yaziyor.
        okunamadi = len(sektor.OKUNAMAYAN) > onceki_hata
        if okunamadi:
            hata += 1
            ardisik_bos += 1
            # KAYNAK KAPANDIYSA DEVAM ETMEK ANLAMSIZ.
            # Kalan istekler yalnizca gecikme ve yuk uretir; is
            # zaten RESUMABLE, kalan bir sonraki kosuda.
            if ardisik_bos >= 5:
                print(f"  KAYNAK KAPANDI -- {ardisik_bos} ardisik red. "
                      f"Kalan istekler YAPILMIYOR.")
                break
            time.sleep(sektor.ARA_SN)
            continue
        ardisik_bos = 0

        s = (r or {}).get("sektor_tr")
        if s:
            d["sirketler"][kod]["sektor"] = r.get("sektor", "")
            d["sirketler"][kod]["sektor_tr"] = s
            if r.get("alt_sektor"):
                d["sirketler"][kod]["alt_sektor"] = r["alt_sektor"]
            yazilan.append((kod, s))
        else:
            # KAYNAK SEKTOR VERMIYOR -- UYDURULMUYOR.
            # Yanlis sektor, yanlis sektor medyani demek: sirket
            # ait olmadigi bir kumeyle karsilastirilir ve sayfa
            # gercek olmayan bir "sektore gore konum" iddiasi tasir.
            bossuz.append(kod)
        time.sleep(sektor.ARA_SN)

    print(f"  sektoru bulunan : {len(yazilan)}")
    print(f"  kaynakta yok    : {len(bossuz)}")
    if bulunamayan:
        print(f"  sayfasi yok     : {len(bulunamayan)} "
              f"({', '.join(bulunamayan[:8])})")
    if hata:
        print(f"  hata            : {hata}")
        # SEBEP SOYLENIYOR, SAYI YETMIYOR.
        #
        # Sebep `sektor.OKUNAMAYAN`da zaten yaziliydi ve HIC
        # yazdirilmiyordu. OLCULDU (2026-10-31, kosu #61): adim 5/5
        # hata verip kapandi, gunlukte tek satir "hata: 5"; ayni uc
        # YERELDE 4/4 calisiyordu. Bu adim 438 sirketin sektorunu
        # dolduruyor ve sektoru olmayan sirket bilanco hattina HIC
        # girmiyor -- yani sessiz kalan sey kapsamin ta kendisi.
        from collections import Counter                  # noqa: PLC0415
        _say = Counter(sebep for _k, sebep in sektor.OKUNAMAYAN)
        for _sebep, _n in _say.most_common(5):
            print(f"    {_n:>3} x {_sebep}")
    for kod, s in yazilan[:12]:
        print(f"    + {kod:8s} {s}")
    # ISARET DE YAZILMALI -- YOKSA KUYRUK HIC ILERLEMEZ.
    #
    # Kosul `not kuru and yazilan` idi: hicbir sektor bulunamadiginda
    # defter YAZILMIYORDU. Arizali senaryonun tam olarak boyle
    # oldugu olculdu (kosu #62: "sektoru bulunan : 0"), yani
    # "kaynakta yok" isaretleri bellekte kalip KAYBOLACAKTI ve
    # duzeltme calismis GORUNUP hicbir sey degistirmeyecekti.
    if not kuru and (yazilan or bulunamayan):
        DEFTER.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print(f"  deftere yazildi: {DEFTER.name}")
    elif kuru:
        print("  (kuru calisma -- yazilmadi)")
    return {"eksik": len(eksik), "yazilan": len(yazilan),
            "bos": len(bossuz), "hata": hata,
            "bulunamayan": len(bulunamayan)}


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=VARSAYILAN_SINIR)
    a.add_argument("--kuru-calis", action="store_true")
    a.add_argument("--kod", nargs="+", metavar="KOD",
                   help="yalnizca bu sirketler (donen kuyrugu beklemeden)")
    n = a.parse_args()
    tazele(n.sinir, n.kuru_calis, n.kod)
    return 0


if __name__ == "__main__":
    sys.exit(main())
