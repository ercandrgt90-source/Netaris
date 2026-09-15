"""Lisansi bizde OLMAYAN seriler yayina sizmasin.

BU DOSYA NEDEN VAR
------------------
Olculdu: S&P 500, Dow, Nasdaq ve VIX fiyat seridindeydi ve serit
`temel.html` icinde -- yani SITEDEKI 1.707 SAYFANIN HEPSINDE
gorunuyorlardi. En genis maruziyet, en az fark edilen yerdeydi.

Dordu de FRED uzerinden geliyor. Ama FRED bunlari kendi verisi olarak
degil, saglayicinin IZNIYLE dagitiyor:

    SP500, DJIA      S&P Dow Jones Indices LLC
    NASDAQCOM        Nasdaq, Inc.
    VIXCLS           Cboe Global Markets

O izin bize gecmiyor. Seriyi FRED'den alabilmek, onu yeniden
yayimlama hakkini da aldigimiz anlamina gelmiyor.

NEDEN SINAMA GEREKLI
--------------------
Kodlar SILINMEDI: `SERIT_ADLARI`, `PANEL_ADLARI`, graf dugumleri ve
depo gecmisi duruyor -- lisans alinirsa tek satirla geri gelsinler
diye. Ama duran bir kod, yeni bir listeye yanlislikla eklenebilir ve
bu HATA VERMEZ: seri gecerli, veri gercek, sayfa duzgun cikar.
Yalnizca yayimlama hakkimiz olmayan bir sey yayimlanmis olur.

Bu depoda ayni sinif sessiz sizinti birkac kez yasandi. Sinama,
serilerin YAYIN YOLLARINA girmedigini tutuyor.

NE SINANMIYOR
-------------
Depoya yazilmalari ve graf dugumu olarak durmalari sinanmiyor --
ikisi de yayin degil. Aktarim kanalinda bir dugumun ADI gecebilir
("S&P 500 -> DAX"); orada yayimlanan sey DEGER degil ILISKI ve iliski
bizim.
"""

from __future__ import annotations

import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import makro_uret_ucretsiz as mak  # noqa: E402
from kaynak import makro  # noqa: E402
from analiz import senaryo_kapi  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


LIS = mak.LISANSSIZ_SERILER

print("\nLisanssiz seriler tanimli")
esit(sorted(LIS), ["DJIA", "NASDAQCOM", "SP500", "VIXCLS"],
     "liste dort seriyi tasiyor")

# --------------------------------------------------------------------
# YAYIN YOLLARI -- her biri okurun GORDUGU bir yer.
# --------------------------------------------------------------------
print("\nYayin yollarinda lisanssiz seri YOK")

esit(sorted(set(mak.PANEL_SERILERI) & LIS), [],
     "fiyat seridi (PANEL_SERILERI) temiz")

panel_kodlari = {k for _ad, grup in makro.PANEL_GRUPLARI for k in grup}
esit(sorted(panel_kodlari & LIS), [],
     "piyasa ozeti paneli (PANEL_GRUPLARI) temiz")

tetik = {k for k, _ad, _birim in senaryo_kapi.TETIKLEYICILER}
esit(sorted(tetik & LIS), [], "senaryo tetikleyicileri temiz")

# Yaziya giren seriler de yayin: metinde deger geciyor.
esit(sorted(set(mak.SERILER) & LIS), [], "makro yazisi serileri temiz")

# --------------------------------------------------------------------
# ILK SINAMA EKSIKTI -- OLCUM BUNU GOSTERDI.
#
# Ilk surumde yalnizca dort liste taraniyordu ve sinama "temiz" dedi.
# Ama insa sonrasi olculdu:
#
#     VIX          573 sayfa
#     S&P 500      159 sayfa
#     NASDAQ       154 sayfa
#
# Dort yayin yolu daha vardi ve hicbiri taranmiyordu:
#
#     site/piyasa_kutusu.py   haber sayfasindaki piyasa kutusu
#     site/insa.py            KONU_GOSTERGELERI ve olay gostergeleri
#     analiz/dosya.py         yabanci haberin acilis cumlesi
#     analiz/olay.py          olay sayfasindaki olcum listesi
#
# Bu, bu depoda tekrar eden dersin ta kendisi: EKSIK TARAMA TEMIZ
# RAPOR URETIR. Sinamanin "gecti" demesi, sorunun olmadigini degil,
# sinamanin oraya bakmadigini gosteriyordu.
#
# Asagidaki tarama artik KAYNAK DOSYALARI okuyor: yeni bir liste
# eklenirse ve icine lisanssiz bir kod girerse, o dosya bu taramaya
# yakalanir -- listeyi elle eklemeyi beklemeden.
# --------------------------------------------------------------------

# ---------------------------------------------------------------------
# DEGER YAYIMLANMIYOR -- AD ANMAK SERBEST
#
# `olay.OLAY_VARLIKLARI` SP500 ve VIX'i zaten disarida birakiyor, yani
# YENI olcum yapilmiyor. Ama eski satirlar `tepki` tablosunda duruyordu
# ve okuyucularin hicbiri lisans suzgeci uygulamiyordu.
#
# Olculdu (2026-09-15): yayimlanan 10 sayfada su satirlar vardi --
#
#     2026-08-07 — ... (BTC +%0,2, SP500 -%0,2, XAU +%0,2)
#     2026-08-23 — ... (BRENT +%3,1, BTC +%0,4, VIX +%7,5, XAU +%0,1)
#
# depoda 63 VIX ve 5 SP500 tepki kaydi duruyordu. Karar dogruydu,
# VERIYE uygulanmiyordu. Ayrica bu satirlar donmus icerige (`.md`)
# yazilmisti: kodu duzeltmek yayimlanmis metni duzeltmiyor.
#
# Ad anmak serbest ("gazetecilikte oldugu gibi"); lisans DEGERI
# yayimlamak icin gerekiyor. Sinama bu ayrimi tutuyor.
# ---------------------------------------------------------------------
import re as _re                                      # noqa: E402

_KODLAR = sorted(set(LIS) | {"VIX", "NASDAQ"})
#: "SP500 -%0,2" gibi KOD+DEGER ciftleri. Yalniz ad eslesmiyor.
_DEGERLI = _re.compile(
    r"\b(?:" + "|".join(_KODLAR) + r")\b[^<)\n]{0,12}[+-]?%\s*\d")

_ICERIK = _KOK.parent / "site" / "icerik"
_kirli = [y.name for y in _ICERIK.rglob("*.md")
          if _DEGERLI.search(y.read_text(encoding="utf-8", errors="replace"))]
esit(_kirli[:3], [], "yayimlanan icerikte lisanssiz DEGER yok")

_CIKTI = _KOK.parent / "site" / "cikti"
if _CIKTI.exists():
    _sayfa = [p.parent.name for p in _CIKTI.rglob("index.html")
              if _DEGERLI.search(p.read_text(encoding="utf-8",
                                             errors="replace"))]
    esit(_sayfa[:3], [], "uretilen sayfalarda lisanssiz DEGER yok")
else:
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")

# AD ANMAK SERBEST: kural degeri eliyor, adi degil.
esit(bool(_DEGERLI.search("S&P 500 ve VIX endeksleri izleniyor.")), False,
     "yalniz ad eslesmiyor")
esit(bool(_DEGERLI.search("(BTC +%0,2, SP500 -%0,2)")), True,
     "ad + deger eslesiyor")

# DEPODAN CIKISTA SUZULUYOR: kodu duzeltmek yetmez, depoda kalmis
# satir bir daha sizmamali.
import sqlite3 as _sq                                 # noqa: E402
import beyin as _beyin                                # noqa: E402

_db = _KOK / "netaris.db"
if _db.exists():
    _b = _sq.connect(f"file:{_db}?mode=ro", uri=True)
    _b.row_factory = _sq.Row
    try:
        _yasak = _beyin.lisanssiz_varliklar(_b)
        esit("VIX" in _yasak and "VIXCLS" in _yasak, True,
             "varlik kodu depodan turetiliyor (VIXCLS -> VIX)")
        esit("NASDAQ" in _yasak, True, "NASDAQCOM -> NASDAQ")
        esit(_beyin.olay_gecmisi(_b, "VIX"), [],
             "lisanssiz varligin gecmisi BOS doner")
        esit(len(_beyin.olay_gecmisi(_b, "XAU")) > 0, True,
             "lisansli varligin gecmisi etkilenmiyor")
        import json as _json                          # noqa: E402
        _kacak = 0
        for _tur in ("faiz", "enflasyon", "istihdam", "jeopolitik"):
            for _r in _beyin.benzer_olaylar(_b, _tur, None, 40):
                for _t in _json.loads(_r["tepkiler"] or "[]"):
                    if _t["varlik"] in _yasak:
                        _kacak += 1
        esit(_kacak, 0, "benzer_olaylar lisanssiz tepki DONDURMUYOR")
    finally:
        _b.close()
else:
    print("  ATLANDI  netaris.db yok")

print()
print("Kaynak dosyalarda VERI LISTESI olarak gecmiyor")

_SITE = _KOK.parent / "site"

#: Taranan dosyalar -- her biri okurun GORDUGU bir deger uretiyor.
_YAYIN_DOSYALARI = (
    _SITE / "piyasa_kutusu.py",
    _SITE / "insa.py",
    _KOK / "analiz" / "dosya.py",
    _KOK / "analiz" / "olay.py",
    _KOK / "kaynak" / "makro.py",
)

#: AD TANIMLARI YAYIN DEGIL -- tarama disinda.
#:
#: Kisitlama VERIYE, isim anmaya degil. Gazetecilikte "S&P 500 dustu"
#: yazmak lisans gerektirmiyor; DEGERINI yayimlamak gerektiriyor.
#:
#: Bu ayrim olmadan tarama kullanilamaz hale gelirdi: `FRED_SERILER`
#: kod->ad sozlugu, `SERIT_ADLARI` kisa ad sozlugu, `varlik.KALIPLAR`
#: baslikta gecisi yakalayan desen. Hicbiri deger yayimlamiyor ve
#: hepsinin durmasi gerekiyor -- lisans alinirsa geri donusun yolu bu.
#:
#: Tarama SATIRA degil BLOGA bakiyor: bir kodun hangi listede oldugu,
#: satirin kendisinden okunamaz.
_AD_SOZLUKLERI = ("FRED_SERILER", "PANEL_ADLARI", "SERIT_ADLARI",
                  "KALIPLAR", "EVDS_SERILER", "AD")


def _blok_adi(satir: str, onceki: str) -> str:
    """Satirin hangi ust duzey atamaya ait oldugu."""
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=", satir)
    return m.group(1) if m else onceki


for dosya in _YAYIN_DOSYALARI:
    metin = dosya.read_text(encoding="utf-8")
    kusurlu = []
    blok = ""
    for no, satir in enumerate(metin.splitlines(), 1):
        if satir[:1] not in (" ", "	", "#", ""):
            blok = _blok_adi(satir, blok)
        cip = satir.strip()
        # Yorum satiri gerekce olabilir; kod degil.
        if cip.startswith("#") or blok in _AD_SOZLUKLERI:
            continue
        for kod in LIS:
            if f'"{kod}"' in satir:
                kusurlu.append(f"{dosya.name}:{no} ({blok or '?'})")
                break
    esit(kusurlu, [], f"{dosya.name} veri listelerinde lisanssiz kod yok")

# --------------------------------------------------------------------
# KOD SILINMEDI -- lisans alinirsa geri gelsin.
#
# Adlarin durmasi bilincli. Silmek, bir gun lisans alindiginda hangi
# kodlarin geri gelecegini ve neden cikarildiklarini kaybettirirdi.
# --------------------------------------------------------------------
print("\nKod silinmedi, yalnizca yayindan cikarildi")
for kod in LIS:
    esit(kod in mak.SERIT_ADLARI or kod in getattr(mak, "PANEL_ADLARI", {}),
         True, f"{kod} adi hala tanimli (geri donus icin)")

# --------------------------------------------------------------------
# GEREKCE KODDA YAZILI OLMALI.
#
# "Neden yok" sorusunun cevabi kaybolursa, biri seriyi iyi niyetle geri
# ekler. Liste bir yasak degil, bir KARARIN kaydi.
# --------------------------------------------------------------------
print("\nGerekce kodda yazili")
kaynak = (_KOK / "makro_uret_ucretsiz.py").read_text(encoding="utf-8")
for iz in ("S&P Dow Jones Indices", "Nasdaq, Inc.", "Cboe Global Markets",
           "LISANSSIZ_SERILER"):
    esit(iz in kaynak, True, f"gerekcede geciyor: {iz}")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
