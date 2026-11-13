# -*- coding: utf-8 -*-
"""`/arastirmalar/` SAYFASININ BOYU ICERIKTEN BAGIMSIZ OLMALI.

BU DOSYA NEDEN VAR
------------------
Sablon kart sayisini 60'ta tutuyordu -- ve bu dogru goruluyordu.
Ama hemen altindaki arsiv listesi KALAN HER ANALIZI ayni sayfaya
satir olarak basiyordu:

    {% for a in analizler[kart_siniri:] %}

Yani sinir KARTLARA konmustu, LISTEYE konmamisti. Sayfa arsivle
birlikte buyuyor ve DOM_SINIRI'na dogru ilerliyordu.

OLCULDU (2026-11-13, CANLI SITE):

    sayfa toplam        2289 etiket (+750 betik payi = 3039)
    arsiv listesi        288 satir, 1152 etiket  (4,00 etiket/satir)
    DOM_SINIRI          3400  ->  pay yalnizca 361

Pay `test_dom_agirligi.UYARI_PAYI` (500) altinda oldugu icin kayit
#14 on iki gun boyunca her kosuda uyardi (36 yorum). Esik asilirsa
`test_dom_agirligi` KIRMIZI yanar ve DAGITIM DURUR -- bu depoda uc
kez oldu (2026-09-18, 10-19, 10-26) ve her kesinti saatler surdu.

NE SINANIYOR -- SAYI DEGIL, SINIRIN KENDISI
-------------------------------------------
"Sayfa 2500 ogeden kucuk" demek icerige bagli bir iddia olurdu ve
bir gun sessizce dogru olmayi birakirdi. Burada SINIRIN UYGULANDIGI
sinaniyor: kart ve satir sayisi `insa.py`deki sabitleri ASMIYOR.
Bu, kac analiz olursa olsun dogru kalir.

Olcutler URETICIDEN okunuyor (`insa.ARASTIRMA_*_SINIRI`), kopya
degil: sabit degisirse sinama onunla birlikte degisir, iki ayri
sayi sessizce ayrismaz.

GORUNEN KUME TEK OLMALI
-----------------------
Kirpma yapisal veriyi (JSON-LD) ve sekme sayaclarini da ilgilendirir.
Sablonun kendi yorumu "LISTE SAYFADA GORUNENI ANLATIYOR" diyor;
JSON-LD butun listeyi sayarken sayfa 210 kalem gosterirse o yorum
yanlisa doner ve arama motoruna GORUNMEYEN sayfalar bildirilir.
Sekme sayaclari da sayfadakini saymali -- yoksa okur badge'de 240
gorup 38 kart bulur.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path.insert(0, str(_SITE))

import insa                                                # noqa: E402

gecti = 0
kaldi: list[str] = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


SAYFA = _CIKTI / "arastirmalar" / "index.html"

if not _CIKTI.exists() or not SAYFA.exists():
    # CI'in sinama adiminda `site/cikti` HENUZ YOK (gitignore'da ve
    # uretim adimi sonra kosuyor). Bu dosya `cikti_sinamalari.py`
    # tarafindan URETIMDEN SONRA yeniden kosturuluyor; asil olcum
    # orada yapiliyor.
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    raise SystemExit(0)

_HAM = SAYFA.read_text(encoding="utf-8", errors="replace")


def _blok(desen: str) -> str:
    m = re.search(desen, _HAM, re.S)
    return m.group(1) if m else ""


# ------------------------------------------------------------------ 1
print("1. SINIRLAR UYGULANIYOR")

_kart_blok = _blok(r'<ul class="izgara arastirma-liste">(.*?)</ul>')
_arsiv_blok = _blok(r'<ol class="olay-cizelge">(.*?)</ol>')

kart = len(re.findall(r"<li[ >]", _kart_blok))
satir = len(re.findall(r"<li[ >]", _arsiv_blok))

# ATILLIK: blok bulunamazsa ikisi de 0 olur ve "sinirin altinda"
# iddialari BEDAVA gecer. Once gercekten kalem BASILDIGI gosteriliyor.
dogru(f"kart basiliyor ({kart})", kart > 0)
dogru(f"arsiv satiri basiliyor ({satir})", satir > 0)

dogru(f"kart sayisi siniri asmiyor ({kart} <= "
      f"{insa.ARASTIRMA_KART_SINIRI})",
      kart <= insa.ARASTIRMA_KART_SINIRI)
dogru(f"arsiv satiri siniri asmiyor ({satir} <= "
      f"{insa.ARASTIRMA_SATIR_SINIRI})",
      satir <= insa.ARASTIRMA_SATIR_SINIRI)

gorunur = kart + satir


# ------------------------------------------------------------------ 2
print("2. SINIR GERCEKTEN ELEMELI (yoksa iddia bos)")

# Sayfa kendi toplamini yaziyor: "N arastirmadan M tanesi bu sayfada".
# Toplam gorunenden BUYUK degilse kirpma hic devreye girmemis demektir
# ve 1. bolumun iddialari hicbir seyi olcmez.
_m = re.search(r"(\d+)\s+araştırmadan\s+(\d+)\s+tanesi bu\s+sayfada", _HAM)
dogru("sayfa toplam/gorunen sayilarini yaziyor", _m is not None)
if _m:
    _toplam, _yazan = int(_m.group(1)), int(_m.group(2))
    es("yazilan gorunen sayi GERCEKTEN basilanla ayni", _yazan, gorunur)
    dogru(f"kirpma eliyor (toplam {_toplam} > gorunen {_yazan})",
          _toplam > _yazan)
    dogru("kalanlarin nerede oldugu soyleniyor",
          "kategori" in _HAM.split("araştırmadan")[1][:400].lower())


# ------------------------------------------------------------------ 3
print("3. YAPISAL VERI SAYFADA GORUNENI ANLATIYOR")

_ld = _blok(r'<script type="application/ld\+json">(.*?)</script>')
dogru("JSON-LD var", bool(_ld.strip()))
try:
    _veri = json.loads(_ld)
except ValueError as e:                                   # noqa: BLE001
    kaldi.append(f"JSON-LD cozulemedi: {e}")
    _veri = {}

_liste = (_veri.get("mainEntity") or {})
es("numberOfItems sayfadaki kalem sayisi", _liste.get("numberOfItems"),
   gorunur)
es("itemListElement uzunlugu da ayni",
   len(_liste.get("itemListElement") or []), gorunur)

# ADRESLER GERCEKTEN SAYFADA OLAN SAYFALARA GIDIYOR.
#
# Sayilar tutup kalemler baska olabilirdi: `numberOfItems` dogru,
# liste ise kirpilmamis kumeden gelmis olabilir. Olcut adres kumesi.
_ld_yollar = {
    (x.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
    for x in (_liste.get("itemListElement") or [])
}
_sayfa_yollar = {
    y.rstrip("/").rsplit("/", 1)[-1]
    for y in re.findall(r'href="(/analiz/[^"]+)"', _kart_blok + _arsiv_blok)
}
dogru(f"JSON-LD adresleri sayfadakilerle ayni kume "
      f"({len(_ld_yollar)} / {len(_sayfa_yollar)})",
      bool(_ld_yollar) and _ld_yollar == _sayfa_yollar)


# ------------------------------------------------------------------ 4
print("4. SEKME SAYACLARI SAYFADAKINI SAYIYOR")

_suz = _blok(r'<div class="akis-suzgec"[^>]*>(.*?)</div>')
_sayilar = [int(x) for x in re.findall(r'class="suzgec-say">(\d+)<', _suz)]
dogru("sayac basiliyor", len(_sayilar) >= 2)
if _sayilar:
    es("'Tumu' sayaci sayfadaki kalem sayisi", _sayilar[0], gorunur)
    es("kategori sayaclarinin toplami da ayni", sum(_sayilar[1:]), gorunur)


if kaldi:
    print("\narastirmalar boyu: KIRIK")
    for _x in kaldi:
        print("  ", _x)
    raise SystemExit(1)
print(f"\narastirmalar boyu: {gecti} dogrulama gecti"
      f" (kart {kart}, arsiv {satir})")
