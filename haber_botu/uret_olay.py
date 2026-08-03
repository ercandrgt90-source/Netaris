"""Olay motoru -- haber akisindan piyasa aciklamasi uretir.

    haber -> esik -> anlik fiyat olcumu -> graf kanallari -> emsal -> yazi

VIZYONDAKI YERI
---------------
"ABD Iran'i vurdu" haberini alip "bolge petrol bolgesi, kriz altini
etkiler, su kadar hareket etti" acikamasina ceviren katman bu.

DORT PARCA, DORT KAYNAK
-----------------------
  ne oldu        <- haber akisi (RSS)
  piyasa ne yapti <- emtia.py (anlik) + gostergeler (gecikmeli)
  hangi kanal    <- beyin grafi (varlik/bag)
  daha once      <- beyin olay gecmisi

Hicbiri digerinin yerine gecmez ve yazida ayri basliklarda durur.

OLCUM SINIRI -- durust olmak gerekiyor
--------------------------------------
Altin, gumus, platin, BTC ve ETH icin anlik veri var (Gold-API, Kraken).
PETROL ICIN YOK: anahtarsiz gun ici kaynak bulunamadi, Brent FRED'den
geliyor ve bir is gunu gecikmeli. Petrol satiri bu yuzden "gecikmeli"
isaretiyle ve gozlem tarihiyle yaziliyor.

Kullanim:
    python uret_olay.py               # tespit et, ekrana bas
    python uret_olay.py --yayinla     # site icerigine yaz
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

_KOK = pathlib.Path(__file__).parent
for _alt in ("analiz", "ai", "kaynak"):
    sys.path.insert(0, str(_KOK / _alt))
sys.path.insert(0, str(_KOK))

import besleme  # noqa: E402
import beyin  # noqa: E402
import emtia  # noqa: E402
import graf_tohum  # noqa: E402
import guvenlik  # noqa: E402
import olay as olay_modulu  # noqa: E402
import prompt  # noqa: E402
import yayin  # noqa: E402
import yazar_olay  # noqa: E402

#: Bir calistirmada en fazla kac olay yazisi. Sinir moderasyon degil
#: kalite icin: ayni gun on yazi cikarsa hicbiri okunmaz.
EN_COK_OLAY = 3

#: Olay bu kadar gunden eskiyse ISLENMEZ.
#:
#: TCMB'nin beslemeleri ARSIV tutuyor: "Enflasyon Raporu (2024-III)" ve
#: "Faiz Oranlarina Iliskin Basin Duyurusu (2024-45)" bugunku akista
#: geliyor. Tarih suzgeci olmadan motor 2024 tarihli bir faiz kararini
#: bugunku fiyat hareketiyle eslestirip yayimliyordu -- finans yayininda
#: geri donusu olmayan hatalardan biri.
#:
#: Uc gun: hafta sonuna denk gelen cuma duyurusu pazartesi hala islenir.
EN_ESKI_GUN = 3

#: Tarihi COZULEMEYEN haber olay sayilmaz.
#: "Bugun olmus olabilir" varsayimi, yukaridaki suzgeci delerdi.

#: Gecikmeli gozlem bu kadar gunden eskiyse "piyasada ne oldu" bolumune
#: GIRMEZ. FRED kalemleri farkli hizlarda guncelleniyor.
EN_ESKI_GOZLEM_GUN = 4

#: Gostergeler dosyasi -- gecikmeli kalemler (petrol, DXY, tahvil) icin.
GOSTERGE_JSON = _KOK.parent / "site" / "icerik" / "gostergeler.json"


def _gun_farki(tarih: str) -> int:
    """Bugunden kac gun once. Cozulemezse cok buyuk sayi -- yani elenir.

    Cozulemeyen tarihi "taze" saymak, suzgeci delerdi.
    """
    try:
        d = datetime.strptime(tarih[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 9999
    return (datetime.now(timezone.utc).date() - d).days


def _gostergeler() -> dict[str, dict]:
    try:
        v = json.loads(GOSTERGE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k["kod"]: k for k in v.get("kalemler", [])}


def _varlik_defteri(b) -> dict[str, dict]:
    return {
        s["kod"]: dict(s)
        for s in b.execute("SELECT kod, ad, seri_kodu FROM varlik").fetchall()
    }


def tepkileri_olc(b, tur: str, defter: dict) -> list[dict]:
    """Olay turune gore ilgili varliklarin fiyat tepkisini olcer.

    Anlik olculebilenler icin gun ici mum, olculemeyenler icin gunluk
    gosterge kullaniliyor. Ikisi AYNI listede ama `gecikmeli` bayragiyla
    ayrilmis durumda -- yazida da oyle gorunuyor.
    """
    kodlar = olay_modulu.OLAY_VARLIKLARI.get(tur, ())
    gost = _gostergeler()
    cikti: list[dict] = []

    # --- anlik olculebilenler ---
    anlik_kodlar = tuple(v[0] for v in emtia.VARLIKLAR)
    istenen = tuple(k for k in kodlar if k in anlik_kodlar)
    fiyatlar = emtia.anlik(istenen) if istenen else {}

    for kod in istenen:
        f = fiyatlar.get(kod)
        if not f:
            continue
        # Gold-API yalnizca ANLIK fiyat veriyor, gecmis yok -- degisim
        # hesaplanamiyordu ve altin satiri hep "—" cikiyordu.
        # PAXG altin teminatli ve bire bir spot takip eden bir varlik;
        # Kraken'de mum gecmisi var. Fiyat Gold-API'den, DEGISIM PAXG
        # mumundan. Gumus icin boyle bir vekil yok: onun degisimi ancak
        # kendi biriktirdigimiz seriyle, birkac gun sonra hesaplanacak.
        sembol = {"BTC": "XBTUSD", "ETH": "ETHUSD",
                  "XAU": "PAXGUSD"}.get(kod)
        degisim = None
        pencere_sn, pencere_adi = olay_modulu.PENCERELER[0]
        if sembol:
            try:
                seri = emtia.kraken_mum(sembol, 15)
                degisim = emtia.degisim(seri, pencere_sn)
            except (emtia.VeriYok, Exception):
                degisim = None
        cikti.append({
            "varlik": kod,
            "ad": defter.get(kod, {}).get("ad", f.ad),
            "deger": f.deger,
            "degisim": degisim,
            "pencere_sn": pencere_sn,
            "pencere_adi": pencere_adi,
            "gozlem_ani": f.an,
            "kaynak": f.kaynak,
            "gecikmeli": False,
        })

    # --- gecikmeli olanlar (petrol, DXY, tahvil, endeks) ---
    for kod in kodlar:
        if kod in istenen:
            continue
        seri_kodu = defter.get(kod, {}).get("seri_kodu")
        k = gost.get(seri_kodu or "")
        if not k:
            continue
        # BAYAT GOZLEM ALINMAZ.
        # FRED kalemleri farkli hizlarda guncelleniyor; DXY on gun onceki
        # gozlemle gelebiliyor. On gunluk bir veriyi "bugunku olayin
        # tepkisi" diye sunmak, okuru yanlis bilgilendirmek olur.
        # Gozlem tarihi yaziliyor olsa bile bolumun BASLIGI "piyasada ne
        # oldu" -- oraya bayat satir girmemeli.
        if _gun_farki(k.get("tarih", "")) > EN_ESKI_GOZLEM_GUN:
            continue
        degisim, gosterim = _fark_coz(str(k.get("fark", "")))
        cikti.append({
            "varlik": kod,
            "ad": defter.get(kod, {}).get("ad", k.get("ad", kod)),
            "deger": None,
            "degisim": degisim,
            "gosterim": gosterim,
            "pencere_sn": 86400,
            "pencere_adi": "günlük",
            "gozlem_ani": k.get("tarih", ""),
            "gozlem_tarih": k.get("tarih", ""),
            "kaynak": "FRED",
            "gecikmeli": True,
        })
    return cikti


def _fark_coz(ham: str) -> tuple[float | None, str]:
    """Gosterge fark metnini (yuzde, gosterim) olarak cozer.

    DIKKAT -- BAZ PUAN YUZDE DEGILDIR.
    Tahvil getirilerinde fark "+1 bp" bicimde geliyor. Bunu sayiya cevirip
    yuzde diye yazmak "ABD 10 yillik tahvil %1 yukseldi" demekti; dogrusu
    1 baz puan, yani %0,01 ve zaten bir SEVIYE degisimi, oransal degil.
    Bir kez oyle yazildi ve rakam on kat buyuk cikti.

    Baz puanli kalemlerde `degisim` None doner: yuzde alanina yazilacak
    bir sey yok. Gosterim metni oldugu gibi tasiniyor.
    """
    ham = ham.strip()
    if not ham:
        return None, ""
    if "bp" in ham.lower():
        return None, ham          # baz puan -- yuzde alanina YAZILMAZ
    if "%" in ham:
        try:
            return float(ham.replace("%", "").replace(",", ".")
                         .replace("+", "").strip()), ham
        except ValueError:
            return None, ham
    return None, ham


def kanallari_bul(b, tur: str, tepkiler: list[dict]) -> list[dict]:
    """Etkilenen varliklardan cikan yapisal baglar.

    Graf sorgusu: "bu varlik neyi etkiler". Ayni hedefe birden cok
    yoldan gelinirse en gucu yuksek olan tutuluyor.
    """
    kokler = [t["varlik"] for t in tepkiler] or \
        list(olay_modulu.OLAY_VARLIKLARI.get(tur, ()))
    gorulen: dict[str, dict] = {}
    for kok in kokler:
        for s in beyin.komsular(b, kok, derinlik=1):
            h = s["hedef"]
            # ACIKLAMASI OLMAYAN BAG YAZIYA GIRMEZ.
            # "- **BIST 100**" tek basina okura hicbir sey soylemiyor;
            # kanal listesini doldurup gercek maddeleri disari itiyor.
            # Bag graftan silinmiyor -- ag sorgusunda duruyor, yalnizca
            # metne yazilmiyor.
            if not (s["aciklama"] or "").strip():
                continue
            if h in gorulen and gorulen[h]["guc"] >= s["guc"]:
                continue
            gorulen[h] = {
                "hedef": h, "hedef_ad": s["hedef_ad"],
                "aciklama": s["aciklama"], "guc": s["guc"],
            }
    return sorted(gorulen.values(), key=lambda x: -x["guc"])[:6]


def _yayilim_say(haberler, baslik: str) -> int:
    """Ayni haberi kac kaynak verdi -- ilgi yogunlugu.

    Tekilleme zaten benzerleri eliyor; burada ELENENLERI sayiyoruz.
    Bir haberin bes kaynakta cikmasi, o haberin buyuklugunun olcusu.
    """
    return 1 + sum(
        1 for h in haberler
        if h.baslik != baslik and besleme.ayni_haber_mi(h.baslik, baslik)
    )


def main() -> int:
    a = argparse.ArgumentParser(description="Olay motoru")
    a.add_argument("--yayinla", action="store_true")
    a.add_argument("--esik", type=int, default=olay_modulu.ESIK)
    a.add_argument("--gun", type=int, default=EN_ESKI_GUN,
                   help="bu kadar gunden eski haber olay sayilmaz")
    args = a.parse_args()

    print("=" * 70)
    print("OLAY MOTORU")
    print("=" * 70)

    with beyin.baglan() as b:
        # Graf her calistirmada tazeleniyor: tohum dosyasi buyudukce
        # yeni varlik ve baglar kendiliginden giriyor.
        v, g = graf_tohum.tohumla(b)
        defter = _varlik_defteri(b)
        print(f"graf: {v} varlik, {g} yeni bag\n")

        # Tekillemeden ONCEKI ham liste -- yayilim sayimi icin gerekli.
        ham = besleme.cek(en_fazla=14)
        print(f"{len(ham)} haber tarandi")

        sinir = (datetime.now(timezone.utc).date()
                 - timedelta(days=args.gun)).isoformat()
        adaylar: list[olay_modulu.Olay] = []
        eski = tarihsiz = 0
        for h in ham:
            # Tarihi cozulemeyen haber olay sayilmaz: "bugun olmus
            # olabilir" varsayimi tarih suzgecini delerdi.
            if not h.tarih:
                tarihsiz += 1
                continue
            if h.tarih < sinir:
                eski += 1
                continue
            o = olay_modulu.siniflandir(h.baslik, h.kurum,
                                        _yayilim_say(ham, h.baslik))
            if o and o.siddet >= args.esik:
                o.adres = h.adres
                o.an = h.tarih
                adaylar.append(o)
        print(f"  {eski} tanesi {args.gun} gunden eski (arsiv), "
              f"{tarihsiz} tanesi tarihsiz -- elendi")

        adaylar.sort(key=lambda o: -o.siddet)
        # Ayni olayin farkli basliklarini tek sefer isle
        secili: list[olay_modulu.Olay] = []
        gorulen: set[str] = set()
        for o in adaylar:
            if o.anahtar in gorulen:
                continue
            gorulen.add(o.anahtar)
            secili.append(o)

        print(f"{len(adaylar)} aday, {len(secili)} tekil olay "
              f"(esik {args.esik})\n")
        for o in secili[:10]:
            print(f"  [{o.siddet:>2}] {o.tur:<11} x{o.yayilim} "
                  f"{o.baslik[:52]}")

        if not secili:
            print("\nEsigi gecen olay yok. Bu normal -- her gun olay olmaz.")
            return 0

        yazilan = 0
        for o in secili[:EN_COK_OLAY]:
            if beyin.olay_yaz(b, {
                "anahtar": o.anahtar, "tur": o.tur, "baslik": o.baslik,
                "haber_adres": o.adres, "an": o.an, "siddet": o.siddet,
            }) is None:
                print(f"\n  atlandi (daha once islendi): {o.baslik[:50]}")
                continue

            olay_id = b.execute("SELECT id FROM olay WHERE anahtar=?",
                                (o.anahtar,)).fetchone()["id"]

            print(f"\n{'-' * 70}\n  {o.baslik[:66]}")
            tepkiler = tepkileri_olc(b, o.tur, defter)
            beyin.tepki_yaz(b, olay_id, tepkiler)
            for t in tepkiler:
                d = t["degisim"]
                print(f"    {t['ad']:<22} "
                      f"{'—' if d is None else format(d, '+.2f') + '%':>9}"
                      f"  {t['pencere_adi']}"
                      f"{'  (gecikmeli)' if t['gecikmeli'] else ''}")

            kanallar = kanallari_bul(b, o.tur, tepkiler)
            emsaller = beyin.benzer_olaylar(b, o.tur, haric_id=olay_id, adet=4)
            print(f"    kanal {len(kanallar)}, emsal {len(emsaller)}")

            govde = yazar_olay.yaz(o, tepkiler, kanallar, emsaller,
                                   kaynak_adi=o.kaynak)
            metin = f"{govde}\n{prompt.UYARI_METNI_OLAY}\n"
            tamam, bulgular = guvenlik.yayinlanabilir(metin)
            if not tamam:
                print(f"    ENGELLENDI: {bulgular[0].terim if bulgular else '?'}")
                continue

            # Her olayin kaniti: hangi veri, hangi an, hangi kaynak.
            beyin.kanit_yaz(b, [
                {"konu_turu": "olay", "konu_id": olay_id, "tur": "veri",
                 "kaynak": t["kaynak"], "gozlem_ani": t["gozlem_ani"],
                 "alinti": f"{t['ad']} {t['degisim']}"}
                for t in tepkiler if t.get("degisim") is not None
            ])

            if args.yayinla:
                dosya = yayin.yaz_makro(
                    metin, konu=o.baslik,
                    kaynak="Olay motoru — ölçülen fiyat verisi",
                    kategori="Makro", kod="OLAY",
                    ozet_metni=yazar_olay.ozet_cikar(o, tepkiler),
                    kaynaklar="Gold-API, Kraken, FRED",
                )
                b.execute("UPDATE olay SET yayimlandi=1 WHERE id=?", (olay_id,))
                print(f"    yazildi: {dosya.name}")
            yazilan += 1

        print(f"\n{yazilan} olay islendi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
