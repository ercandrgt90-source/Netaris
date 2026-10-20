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

import pathlib
import sqlite3
import sys

_KOK = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_KOK / "haber_botu"), str(_KOK / "haber_botu" / "analiz")]

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
SERISIZ = {"EA_TUFE", "CN_BUYUME", "DIS_TICARET_TR", "CDS_TR"}

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

# KARSILIGI OLMAYAN BAG = SESSIZ BOS SAYFA. Seri emekliye ayrilip
# yenisi geldiginde (CPIAUCSL -> CPIAUCNS) tam burasi kirmizi yanar.
_kopuk = sorted(
    f"{k} -> {s}" for k, s in _tohum.items()
    if s and s not in _seriler and s not in _fiyatlar)
if _kopuk:
    print("\n  DEPODA KARSILIGI OLMAYAN BAG:")
    for _k in _kopuk:
        print(f"    {_k}")
esit(_kopuk, [], f"her bag depoda karsilik buluyor ({len(_tohum)} varlik)")

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
