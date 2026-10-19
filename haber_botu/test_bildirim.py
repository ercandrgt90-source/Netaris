# -*- coding: utf-8 -*-
"""BILDIRIM: GERCEK OLAY, BIR KEZ, VAR OLAN SAYFAYA.

BU DOSYA NEDEN VAR
------------------
Bildirim, kullanicinin uygulamayi kapatmasinin en hizli yoludur --
yanlis kullanildiginda. Uc kural bunu engelliyor ve ucu de SESSIZCE
kaybedilebilir:

 1. **Gercek olay olmadan bildirim yok.** Sartnamenin kendi kurali.
    Olaylar DEPODAN okunuyor; uydurulmuyor.

 2. **Ayni sey iki kez gonderilmiyor.** Iz tutulmazsa ayni bilanco
    her kosuda yeniden duyurulur -- gunde onlarca kez.

 3. **Sayfasi olmayan icerik icin bildirim yok.** OLCULDU
    (2026-10-19): `icerik` tablosundaki yirmi bilanco kaydinin
    SEKIZININ uretilmis sayfasi yoktu. Dogrulanmadan gonderilseydi
    bildirim okuru 404'e goturuyordu.

Ayrica KOSU SINIRI sinaniyor: bir aksama sonrasi birikmis olaylar
aynı anda gonderilirse telefon arka arkaya titrer. Birikmis olanlar
ATLANMIYOR, erteleniyor.

AG KULLANILMIYOR, D1 KULLANILMIYOR.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sqlite3
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

import bildirim_gonder as B                         # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _depo(kayitlar):
    """Bellekte `icerik` tablosu."""
    b = sqlite3.connect(":memory:")
    b.execute("CREATE TABLE icerik (slug TEXT, tur TEXT, baslik TEXT,"
              " kod TEXT, kategori TEXT, tarih TEXT, kelime INTEGER,"
              " kayit_ani TEXT)")
    b.executemany("INSERT INTO icerik VALUES (?,?,?,?,?,?,?,?)", kayitlar)
    return b


print("")
print("1. SAYFASI OLMAYAN ICERIK ICIN BILDIRIM YOK")
#
# OLCULDU: yirmi bilanco kaydinin sekizinin sayfasi yoktu. Depodaki
# kayit "uretilmeye aday" demek; yayimlanmis olmasi AYRI bir sey.
_g = pathlib.Path(tempfile.mkdtemp())
_ASIL_SITE = B.SITE
try:
    B.SITE = _g
    (_g / "cikti" / "analiz" / "var-2026-2-ceyrek").mkdir(parents=True)
    (_g / "cikti" / "analiz" / "var-2026-2-ceyrek" / "index.html").write_text(
        "<html></html>", encoding="utf-8")

    b = _depo([
        ("var-2026-2-ceyrek", "bilanco-analizi", "Var A.Ş.", "VAR",
         "Bilanço", "2026-10-18", 800, "2026-10-18T12:00:00"),
        ("yok-2026-2-ceyrek", "bilanco-analizi", "Yok A.Ş.", "YOK",
         "Bilanço", "2026-10-18", 800, "2026-10-18T12:00:00"),
    ])
    o = B.bilanco_olaylari(b, set())
    esit([x["anahtar"] for x in o], ["bilanco:VAR:2026-10-18"],
         "yalnizca SAYFASI OLAN icerik bildiriliyor")
    esit(o[0]["yol"], "/analiz/var-2026-2-ceyrek/", "yol dogru kuruluyor")

    # `site/cikti` HIC YOKSA hicbir sey gonderilmiyor.
    B.SITE = _g / "olmayan"
    esit(B.bilanco_olaylari(b, set()), [],
         "cikti dizini yoksa HICBIR bildirim (dogrulayamadigimizi"
         " yayimlanmis saymiyoruz)")
    esit(B.sayfasi_var("/analiz/var-2026-2-ceyrek/"), False,
         "cikti yokken sayfasi_var False")
    esit(B.sayfasi_var(""), False, "bos yol False")
finally:
    B.SITE = _ASIL_SITE

print("")
print("2. AYNI OLAY IKI KEZ GONDERILMIYOR")
try:
    B.SITE = _g
    b = _depo([
        ("var-2026-2-ceyrek", "bilanco-analizi", "Var A.Ş.", "VAR",
         "Bilanço", "2026-10-18", 800, "2026-10-18T12:00:00"),
    ])
    esit(len(B.bilanco_olaylari(b, set())), 1, "ilk koşuda gönderilecek")
    esit(B.bilanco_olaylari(b, {"bilanco:VAR:2026-10-18"}), [],
         "iz varsa YENIDEN gonderilmiyor")
finally:
    B.SITE = _ASIL_SITE

print("")
print("3. BILANCO OLMAYAN TUR KARISMIYOR -- SAYFASI OLSA BILE")
#
# ILK YAZIM ATILDI: makro ve teknik kayitlarin sayfasi YOKTU, yani
# onlari eleyen sey tur suzgeci degil SAYFA DENETIMI idi. Mutasyon
# gosterdi: `WHERE tur LIKE '%'` yapildiginda sinama yine yesil
# gecti.
#
# Simdi uc kaydin da sayfasi VAR; eleyen tek sey tur suzgeci.
try:
    B.SITE = _g
    for s in ("makro-yazi", "teknik-yazi"):
        (_g / "cikti" / "analiz" / s).mkdir(parents=True, exist_ok=True)
        (_g / "cikti" / "analiz" / s / "index.html").write_text(
            "<html></html>", encoding="utf-8")
    b = _depo([
        ("makro-yazi", "makro", "Makro yazı", "MAKRO", "Makro",
         "2026-10-18", 500, "2026-10-18T12:00:00"),
        ("teknik-yazi", "teknik-gorunum", "Teknik", "ALTIN", "Teknik",
         "2026-10-18", 500, "2026-10-18T12:00:00"),
        ("var-2026-2-ceyrek", "bilanco-analizi", "Var A.Ş.", "VAR",
         "Bilanço", "2026-10-18", 800, "2026-10-18T12:00:00"),
    ])
    esit([x["anahtar"] for x in B.bilanco_olaylari(b, set())],
         ["bilanco:VAR:2026-10-18"],
         "sayfasi OLSA BILE yalnizca 'bilanco-analizi' bildiriliyor")
finally:
    B.SITE = _ASIL_SITE

print("")
print("4. TAKVIM: YALNIZCA YUKSEK ETKI VE SAATI KESIN OLAN")
#
# Her veri icin bildirim gondermek bildirimleri gurultuye cevirir.
# Saati kesinlesmemis aciklama icin bildirim ise okuru YANLIS
# saatte beklemeye cagirmak olurdu.
_t = pathlib.Path(tempfile.mkdtemp())
_ASIL = B.SITE
try:
    B.SITE = _t
    (_t / "cikti" / "v1").mkdir(parents=True)
    simdi = _dt.datetime.now(_dt.timezone.utc)
    yakin = (simdi + _dt.timedelta(minutes=45)).isoformat()
    uzak = (simdi + _dt.timedelta(hours=20)).isoformat()
    (_t / "cikti" / "v1" / "takvim.json").write_text(json.dumps({
        "ogeler": [
            {"ad": "Fed faiz kararı", "seri": "DFF", "onem": 3,
             "kesin": True, "an": yakin, "gun": "19.10", "saat": "14:00"},
            {"ad": "Düşük etkili veri", "seri": "X", "onem": 1,
             "kesin": True, "an": yakin, "gun": "19.10", "saat": "14:00"},
            {"ad": "Saati belirsiz", "seri": "Y", "onem": 3,
             "kesin": False, "an": yakin, "gun": "19.10", "saat": "14:00"},
            {"ad": "Uzak", "seri": "Z", "onem": 3,
             "kesin": True, "an": uzak, "gun": "20.10", "saat": "10:00"},
        ]}, ensure_ascii=False), encoding="utf-8")
    o = B.takvim_olaylari(set())
    esit([x["baslik"] for x in o], ["Fed faiz kararı yaklaşıyor"],
         "yalnizca yuksek etkili, saati kesin ve YAKIN olan")
    esit(B.takvim_olaylari({o[0]["anahtar"]}), [],
         "iz varsa yeniden gonderilmiyor")

    # Dosya yoksa cokmuyor.
    B.SITE = _t / "yok"
    esit(B.takvim_olaylari(set()), [], "takvim dosyasi yoksa bos")
finally:
    B.SITE = _ASIL

print("")
print("5. KOSU SINIRI VAR")
# Birikmis olaylari aynı anda gondermek telefonu arka arkaya
# titretir ve kullanici bildirimleri kapatir.
esit(B.KOSU_SINIRI <= 5, True,
     f"bir kosuda en fazla {B.KOSU_SINIRI} bildirim")
esit(B.KOSU_SINIRI >= 1, True, "sinir en az bir")

print("")
print("6. SQL KACISI")
# Olay basligi depodan geliyor ve icinde tek tirnak olabilir
# ("Koç Holding'in...").
esit(B._tirnak("Koç'un"), "Koç''un", "tek tirnak kaciriliyor")
esit(B._tirnak("x"), "x", "duz metin degismiyor")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
