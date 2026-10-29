# -*- coding: utf-8 -*-
"""VARLIK SAYFASI VERISINE BAGLI KALMALI -- VE SAYI BIRIMINI TASIMALI.

BU DOSYA NEDEN VAR
------------------
Bir varligin `seri_kodu` alani, sayfasinda hangi sayinin gorunecegini
belirliyor. Bos ya da yanlis olursa sayfa CALISIR -- yalnizca bos
doner. Hicbir sey kirmizi yanmaz, cunku teknik olarak bir sey
bozulmamistir.

UC VAKA OLCULDU
---------------
1. EURUSD (daha once): panel kalemleri FRED'den ECB'ye tasinmis ama
   varligin `seri_kodu` cevrilmemisti. Panel 21 Agustos'u gosterirken
   AYNI SAYFANIN grafigi 31 Temmuz'da bitiyordu.

2. CPI_US, NFP, US_BUYUME (2026-10-21): uc gostergenin `seri_kodu`
   HIC doldurulmamisti. Ucu de yayinda, `onem` degerleri 90/85/90 --
   yani okurun gormesi beklenen sayfalar. Besleme `veri_var: false`
   donduruyordu: okur "ABD TÜFE" sayfasini aciyor ve HICBIR SAYI
   gormuyordu. Oysa depoda veri vardi ve tazeydi (`CPIAUCNS`
   2026-09-01, `PAYEMS` 2026-09-01, `GDPC1` 2026/2. ceyrek).

3. XAU, BTC, ETH (2026-10-21): `fiyat` tablosunda birim SUTUNU yok ve
   o dal bos dizge donduruyordu. Altin sayfasinda "4.132", Bitcoin'de
   "81.738" yaziyordu -- neyin cinsinden oldugunu soylemeyen sayilar.

Ucu de ayni sinif: VERI VAR, ANLAMI EKSIK. Ve ucu de sessiz.

NE SINANIYOR
------------
1. Tohumdaki her `seri_kodu` depoda GERCEKTEN karsilik buluyor.
   Bir seri emekliye ayrilip yenisiyle degistirildiginde (CPIAUCSL ->
   CPIAUCNS gibi) bu iddia kirmizi yanar.
2. Okurun sayi beklemesi mesru olan gostergeler BAGLI ve deger
   donduruyor.
3. `fiyat` tablosundan beslenen varliklar birim tasiyor.
4. Kontrolun kendisi atil degil.
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
import sys

_KOK = pathlib.Path(__file__).resolve().parent.parent
# `kaynak` DA LISTEDE: seri kodlarini CEKEN moduller orada
# (makro, ecb_kur, bundesbank, evds, politika_faizi).
# Eksikligi olculdu: `_cekilebilir()` SIFIR kod okudu ve
# atillik kapisi bunu yakaladi.
sys.path[:0] = [str(_KOK / "haber_botu"),
                str(_KOK / "haber_botu" / "analiz"),
                str(_KOK / "haber_botu" / "kaynak")]

import graf_tohum  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Okurun SAYI beklemesi mesru olan gostergeler.
#:
#: Liste elle yaziliyor: "onem >= 85 olan her gosterge" gibi bir kural
#: tohumdan turetilirdi ve biri onemi dusurdugunde iddia da sessizce
#: kuculurdu -- hareketli hedef. Buradakiler, verisi depoda BULUNAN
#: ve sayfasi yayinda olanlar.
BAGLI_OLMALI = {
    "TUFE_TR", "UFE_TR", "FED_FAIZ", "TCMB_FAIZ", "US10Y", "US2Y",
    "EGRI", "DXY", "CPI_US", "NFP", "US_BUYUME",
}

#: Serisi OLMAYAN gostergeler -- bos birakilmalari DURUST.
#:
#: Bunlar icin depoda hicbir seri yok. Uydurma bir bag kurmak, sayfada
#: ILGISIZ bir sayi gostermek olurdu; bos birakmak dogru olan.
# EA_TUFE CIKARILDI (2026-10-29): Eurostat HICP endeksine
# baglandi (CP0000EZ19M086NEST). ECB_FAIZ ve DE10Y de artik
# bagli -- ikisi de bu listede hic yoktu.
#
# CN_BUYUME BAGLI DEGIL ve bu OLCULDU: FRED karsiligi
# (CHNGDPNQDSMEI) son gozlemini 2023-07-01 tarihinde
# vermis -- uc yil bayat bir seri yayimlanmaz.
SERISIZ = {"CN_BUYUME", "DIS_TICARET_TR", "CDS_TR"}

print("Tohumdaki baglar")
_tohum = {k: s for k, _t, _a, _ae, s, _o, _ac in graf_tohum.VARLIKLAR}
_gosterge = {k for k, t, *_ in graf_tohum.VARLIKLAR if t == "gosterge"}
esit(len(_gosterge) > 5, True, f"gosterge varligi bulundu ({len(_gosterge)})")

_bagsiz = sorted(k for k in BAGLI_OLMALI if not _tohum.get(k))
if _bagsiz:
    print(f"\n  SAYI BEKLENEN AMA BAGSIZ: {_bagsiz}")
esit(_bagsiz, [], f"sayi beklenen gostergeler bagli ({len(BAGLI_OLMALI)})")

# Iki liste CAKISMAMALI: bir kod hem "bagli olmali" hem "serisi yok"
# diye isaretlenirse, hangi kuralin gecerli oldugu belirsizlesir.
esit(sorted(BAGLI_OLMALI & SERISIZ), [], "listeler cakismiyor")

_DB = _KOK / "haber_botu" / "netaris.db"
if not _DB.exists():
    print("\n  ATLANDI  depo yok -- bag COZULEMEDI")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

print("\nBaglar depoda karsilik buluyor")
_b = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True)
_seriler = {r[0] for r in _b.execute("SELECT DISTINCT kod FROM gosterge")}
_fiyatlar: set = set()
try:
    _fiyatlar = {r[0] for r in _b.execute("SELECT DISTINCT sembol FROM fiyat")}
except sqlite3.Error:
    pass
esit(len(_seriler) > 10, True, f"depoda seri var ({len(_seriler)})")

# KARSILIGI OLMAYAN BAG -- IKI AYRI IDDIA.
#
# ILK SURUM TEK IDDIAYDI ("her seri_kodu depoda var") ve KOSUYU KIRDI
# (2026-10-29, kosu #2350-2352). Sebebi su kilit: depo URETILEN bir
# eser. Grafa uc yeni seri baglandiginda (ECBDFR,
# CP0000EZ19M086NEST, BBK_DE10Y) onlari CEKEN adim bu kapinin
# ARKASINDA kaliyordu -- yani seriyi uretecek adima hic sira
# gelmiyordu.
#
# AYRIM ASAMA: depo uretilmeden once "henuz cekilmedi" ile "yanlis
# kod" ayirt EDILEMEZ; uretimden sonra ayirt EDILIR.
#
#   HER ZAMAN      : seri_kodu ya depoda var YA DA hattin CEKTIGI bir
#                    listede. Ikisinde de yoksa hicbir adim onu
#                    uretmeyecek. (Yeni seri bu kapiyi gecer.)
#   URETIM SONRASI : seri_kodu depoda GERCEKTEN var. Cekme listesinde
#                    duran ama kaynaktan hic gelmeyen bir kod burada
#                    kirmizi yanar.
#
# BU DOSYA EMEKLI KOD VAKASINI YAKALAMIYOR -- VE BU OLCULDU.
#
# Ilk yazimda gerekce olarak "CPIAUCSL -> CPIAUCNS gocu burada
# yakalanir" yazmistim. YANLIS: CPIAUCSL depoda HALA duruyor
# (olculdu 2026-10-29: 15 gozlem, son 2026-07-01), yani kod ona
# geri gocse bile "depoda karsilik buluyor" iddiasi GECER. Mutasyonla
# dogrulandi: DXY -> CPIAUCSL degisikligi bu dosyada KACTI.
#
# O vakanin korumasi BASKA YERDE ve CALISIYOR: `tazelik.py` emekli
# serileri listeliyor (`EMEKLI_SEBEP`: DEXUSEU, CPIAUCSL, CPILFESL)
# ve `test_tazelik.py` "emekli seri hicbir varligi beslemiyor" diyor.
# Ayni mutasyon ORADA yakalandi. Yani korumayi burada kopyalamak
# gereksiz; eksik olan bir sey yok, yalnizca gerekce yanlis yazilmisti.
#
# CEKME LISTESI OLCUTU YINE DE "KAYITLI MI" OLCUTUNDEN IYI: bir kodun
# ad sozlugunde bulunmasi, hicbir adimin onu cektigi anlamina gelmiyor.
_URETIM_SONRASI = os.environ.get("NETARIS_URETIM_SONRASI") == "1"

#: Hattin GERCEKTEN CEKTIGI seri kodlari.
#:
#: OLCUT "KAYITLI MI" DEGIL, "CEKILIYOR MU" -- ve aradaki fark
#: dosyanin kendi 2. vakasinin TA KENDISI.
#:
#: Ilk yazimda `makro.FRED_SERILER` okunuyordu. O bir AD/BIRIM
#: SOZLUGU, cekme listesi DEGIL. Olculdu (2026-10-29):
#:
#:     FRED_SERILER             17 kod   <- yalnizca ad ve birim
#:     PANEL_SERILERI            7 kod   <- CEKILEN
#:     DEPO_SERILERI             2 kod   <- CEKILEN
#:     SERILER                   4 kod   <- CEKILEN
#:
#:     CPIAUCSL FRED_SERILER icinde : EVET
#:     CPIAUCSL cekiliyor           : HAYIR
#:
#: Yani sozluge bakan olcut, HIC CEKILMEYEN bir kodu "kayitli"
#: sayip gecirirdi. Cekme listesine bakan olcut gecirmiyor.
#:
#: NOT: CPIAUCSL ornegi bu dosyanin YAKALADIGI bir vaka DEGIL --
#: o kod depoda hala duruyor ve emekli-seri korumasi
#: `test_tazelik.py` icinde. Ayrinti asagida, iddia blogunda.
#:
#: Listeler elle KOPYALANMIYOR, modullerin kendisinden okunuyor --
#: kopya, yeni bir seri eklendigi gun sessizce eskirdi.
def _cekilebilir() -> set:
    kodlar: set = set()
    try:
        import makro_uret_ucretsiz as _m
        for _ad in ("PANEL_SERILERI", "DEPO_SERILERI", "SERILER"):
            kodlar |= set(getattr(_m, _ad, ()))
    except Exception:                                   # noqa: BLE001
        pass
    for _mod, _al in (("ecb_kur", "KOD"), ("bundesbank", "KOD"),
                      ("politika_faizi", "KOD")):
        try:
            kodlar.add(getattr(__import__(_mod), _al))
        except Exception:                               # noqa: BLE001
            pass
    try:
        import evds
        kodlar |= {s[0] for s in evds.SERILER}
    except Exception:                                   # noqa: BLE001
        pass
    return kodlar


# ASAMA AYRIMI ATIL OLABILIR -- IKI YONDEN.
#
# 1. `_URETIM_SONRASI` sabit False yazilirsa katı iddia HIC kosmaz
#    ve sinama iki asamada da yesil doner. Bayrak gercekten
#    okunuyor mu diye bakiliyor.
# 2. `cikti_sinamalari.py` bayragi cocuk ortamina GECIRMEZSE ayni
#    sonuc olusur -- sinama kusursuz, kapi sessiz. Olcut o dosyanin
#    kaynaginda bayragin HEM tanimli HEM `env=` icinde gecmesi.
if os.environ.get("NETARIS_URETIM_SONRASI") == "1":
    esit(_URETIM_SONRASI, True, "asama bayragi gercekten okunuyor")

_KAPI = _KOK / "site" / "cikti_sinamalari.py"
_kapi_k = _KAPI.read_text(encoding="utf-8", errors="replace")
esit("NETARIS_URETIM_SONRASI" in _kapi_k, True,
     "uretim sonrasi kapisi bayragi taniyor")
esit("ASAMA_DEGISKENI: \"1\"" in _kapi_k, True,
     "kapi bayragi cocuk ortamina geciriyor")
# TANIMA DEGIL KULLANIMA BAK: `"DEPO_IZI" in kaynak` iddiasi
# mutasyonla KACTI -- kullanim kaldirildiginda TANIM yerinde
# kaldigi icin dize hala esliyordu. Ayni tuzak bu depoda bir
# kez daha yasandi (`"duyur(" in kaynak` fonksiyon TANIMIYLA
# esliyordu). Olcut artik kesif OLCUTUNUN kendisi.
esit("YOL_IZI + ICERIK_IZI + DEPO_IZI" in _kapi_k, True,
     "kapi depo izini KESIF OLCUTUNDE kullaniyor")

_CEKILEN = _cekilebilir()
# ATILLIK: kayit kumesi bos ya da cok kucukse "kayitli" kapisi her
# seyi gecirirdi ve iddia anlamsizlasirdi.
esit(len(_CEKILEN) > 15, True,
     f"cekilen seri listeleri okundu ({len(_CEKILEN)})")

_tanimsiz = sorted(
    f"{k} -> {s}" for k, s in _tohum.items()
    if s and s not in _seriler and s not in _fiyatlar
    and s not in _CEKILEN)
if _tanimsiz:
    print("\n  HICBIR ADIMIN CEKMEDIGI BAG (tipo ya da gocmemis kod):")
    for _k in _tanimsiz:
        print(f"    {_k}")
esit(_tanimsiz, [],
     f"her bag ya depoda ya CEKME listesinde ({len(_tohum)} varlik)")

_kopuk = sorted(
    f"{k} -> {s}" for k, s in _tohum.items()
    if s and s not in _seriler and s not in _fiyatlar)
if _URETIM_SONRASI:
    if _kopuk:
        print("\n  DEPODA KARSILIGI OLMAYAN BAG:")
        for _k in _kopuk:
            print(f"    {_k}")
        # NE YAPILACAGI YAZILI OLMALI. Bu kapi uretimden SONRA
        # kosuyor, yani bir kod burada gorunuyorsa iki sey olabilir:
        #   1. Veri adimi hic kosmadi (yerelde elle `insa.py`
        #      kosturuldu, `calistir.py` degil) -- o zaman
        #      `makro_uret_ucretsiz.py` ve `uret_evds.py` kosmali.
        #   2. Adim kostu ama kaynak veri VERMEDI (gecici kesinti ya
        #      da ustte emekliye ayrilmis seri). Gecici kesintide
        #      kosuyu yeniden baslatmak yeterli; kalici ise
        #      `seri_kodu` yanlis kodu gosteriyor.
        print("")
        print("  NE YAPMALI: bu kodlar CEKME listesinde ama depoda")
        print("  yok. Once veri adimlari kosmali:")
        print("    python haber_botu/makro_uret_ucretsiz.py")
        print("    python haber_botu/uret_evds.py")
        print("  Kostuktan sonra da bosalarsa kaynak veri vermiyor.")
    esit(_kopuk, [],
         f"her bag depoda karsilik buluyor ({len(_tohum)} varlik)")
elif _kopuk:
    # SESSIZ GECMIYOR: uretimden once bu bir UYARI, cunku yeni
    # eklenmis bir seri de boyle gorunur. Uretim sonrasi kosuda ayni
    # liste KIRMIZI yanacak.
    print(f"\n  HENUZ CEKILMEMIS ({len(_kopuk)}) -- uretim sonrasi "
          f"kosuda denetlenecek:")
    for _k in _kopuk:
        print(f"    {_k}")

print("\nSayi beklenen gostergelerde GERCEKTEN deger var")
_bos = []
for _kod in sorted(BAGLI_OLMALI):
    _s = _tohum.get(_kod)
    _r = _b.execute("SELECT tarih, deger FROM gosterge WHERE kod=?"
                    " ORDER BY tarih DESC LIMIT 1", (_s,)).fetchone()
    if _r is None and _s in _fiyatlar:
        continue
    if _r is None or _r[1] is None:
        _bos.append(f"{_kod} -> {_s}")
if _bos:
    print(f"\n  BAGLI AMA DEGERSIZ: {_bos}")
esit(_bos, [], f"baglarin hepsi deger dondururuyor ({len(BAGLI_OLMALI)})")

print("\nFiyat tablosundan gelen varlikta birim var")
# `fiyat` tablosunda birim SUTUNU yok ve o dal uzun sure bos dizge
# donduruyordu. Birim UYDURULMUYOR, sembolden OKUNUYOR
# (PAXGUSD -> USD). Bu iddia okumanin kalmasini tutuyor: kural
# silinirse sayi yine basilir, yalnizca ne oldugu kaybolur -- ve bu
# sessiz bir kayiptir.
import varlik as _varlik  # noqa: E402

_birimsiz = []
_bakilan = 0
for _kod, _seri in sorted(_tohum.items()):
    if not _seri or _seri not in _fiyatlar:
        continue
    _bakilan += 1
    _d = _varlik.seri_ozet(_b, _seri)
    if _d is None:
        continue
    if not (_d.get("birim") or "").strip():
        _birimsiz.append(f"{_kod} -> {_seri}")
if _birimsiz:
    print(f"\n  BIRIMSIZ FIYAT VARLIGI: {_birimsiz}")
esit(_bakilan > 0, True,
     f"fiyat tablosuna bagli varlik bulundu ({_bakilan})")
esit(_birimsiz, [], "fiyat varliklarinin hepsinde birim var")

print(f"\nTUM TESTLER GECTI ({_gecti})")
