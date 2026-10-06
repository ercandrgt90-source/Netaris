# -*- coding: utf-8 -*-
"""HICBIR SAYFA BAGLANTISIZ KALMAMALI.

BU DOSYA NEDEN VAR
------------------
Bir sayfanin URETILMIS olmasi, ona ULASILABILDIGI anlamina gelmiyor.
Sitemap'te durur, dosya diskte durur, sinamalar yesil kalir -- ve
siteye giren okur o sayfaya hicbir tiklama diziliminden varamaz.
Kusur yalnizca butun cikti taranip her sayfanin ALDIGI baglanti
sayildiginda goruluyor; tek tek sayfaya bakarak hic goruldugu yok.

OLCULDU (2026-10-06), uretilen 1984 sayfanin tamami taranarak:

  yetim sayfa                        86
    /haber/                          76
    /varlik/                         10

  76 yetim haberin konusu --
    Jeopolitik                       73
    Enerji                            3
    diger on bir konu                 0

Tesaduf degildi. Konu sayfasi en yeni `KONU_LISTE_SINIRI` (80) haberi
basiyor; Jeopolitik'te 572, Enerji'de 109 haber var. Yetimlerin
tamami tam da o iki konudan geliyordu. Bir haber sayfasina baglanti
dort yerden gelebiliyor -- baska haberin kenar seridi, varlik
sayfasi, olay dosyasi, konu sayfasi -- ve yetimlerin 66'sinin bagli
varligi hic yoktu. Konu sayfasi dusunce geriye yol kalmiyordu.

Cozum siniri kaldirmak DEGILDI (gerekcesi sayfa agirligi ve gecerli),
sinirin otesine giden bir yol acmakti: `/konu/<konu>/arsiv/`.

NE SINANIYOR
------------
1. `/haber/` ve `/analiz/` altinda YETIM SAYFA YOK. Sayi degil, sifir
   -- "birkac tane olabilir" demek, kuralin kendisini bosaltir.
2. Liste sinirini asan her konu sayfasi arsive BAGLANIYOR. Birinci
   madde sonucu olcuyor, bu madde DUZENEGI: arsiv sayfasi dururken
   ona giden bag silinse birinci madde de duserdi, ama o zaman neyin
   bozuldugu belli olmazdi.
3. `/varlik/` yetimleri BILINEN ve belgelenmis durum (`insa.py`
   icinde yazili): hakkinda guncel haber olmayan varlik hicbir
   yerden anilmiyor. Burada ISTISNA LISTESI TUTULMUYOR -- sayfanin
   kendisine bakiliyor: yetim bir varlik sayfasi HABER TASIYORSA bu
   belgelenmis durum degil, kusurdur ve sinama duser.

NEREYE BAKILIYOR -- VE NEDEN ORAYA
----------------------------------
Kaynak koda degil URETILEN CIKTIYA. "Sablonda baglanti var mi" sorusu
bu kusuru yakalayamazdi: bag sablonda vardi (`konu.haberler`
donguleniyordu) ama liste SINIRLIYDI. Yetimlik, kaynakta degil
toplamda olusan bir ozellik.

SINIR DEGERI BURAYA KOPYALANMADI -- VE BU BILINCLI
--------------------------------------------------
Ikinci madde "80" sayisini bilmiyor: sayfanin yazdigi toplam ile
sayfada BASILI oge sayisini karsilastiriyor. Sabiti kopyalamak,
sinirin degistigi gun sessizce yanlis sinanan bir kural birakirdi.

JS ILE KURULAN BAGLANTILAR SAYILMIYOR -- VE BU DA BILINCLI
----------------------------------------------------------
Yalnizca statik HTML'deki `href` okunuyor. Bir sayfaya ancak
JavaScript calistiktan sonra ulasilabiliyorsa o sayfa, betigi
calistirmayan tarayici ve tarayicilar icin zaten yetimdir; onu
"baglanti aliyor" saymak kurali bosaltirdi.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

_gecti = 0


def dogru(kosul, aciklama: str, ek: str = "") -> None:
    global _gecti
    if not kosul:
        print(f"  DUSTU  {aciklama}")
        if ek:
            print(f"    {ek}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Sayfanin verdigi ic baglantilar. Capa (`#`) ve sorgu (`?`) atiliyor:
#: ikisi de AYNI sayfaya gidiyor, ayri hedef degil.
_BAG = re.compile('href="(/[^"#?]*)"')
_SAYI = re.compile("<p>([0-9]+) haber")


def _dizin_yolu(h: str) -> str:
    """Baglanti hedefini sayfa adresine indirger."""
    if h.endswith("/"):
        return h
    return h if "." in h.rsplit("/", 1)[-1] else h + "/"


print("")
print("Yetim sayfa taramasi")

if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_uretilen: dict[str, pathlib.Path] = {}
for _p in _CIKTI.rglob("index.html"):
    _y = "/" + _p.parent.relative_to(_CIKTI).as_posix() + "/"
    _uretilen["/" if _y == "/./" else _y] = _p

_baglanan: set[str] = set()
for _p in _CIKTI.rglob("*.html"):
    for _h in set(_BAG.findall(_p.read_text(encoding="utf-8", errors="replace"))):
        _baglanan.add(_dizin_yolu(_h))

_yetim = sorted(set(_uretilen) - _baglanan)
print(f"  tarandi: {len(_uretilen)} sayfa, {len(_yetim)} yetim")
dogru(len(_uretilen) > 500, f"tarama dolu ({len(_uretilen)} sayfa)")

# 1. Haber ve analiz sayfalarinda yetim YOK.
for _on in ("/haber/", "/analiz/"):
    _k = [y for y in _yetim if y.startswith(_on)]
    dogru(not _k, f"{_on} altinda yetim sayfa yok",
          f"{len(_k)} tane, ilki: {_k[0] if _k else ''}")

# 2. Liste sinirini asan konu, arsive BAGLANIYOR.
_asan = 0
for _y, _p in sorted(_uretilen.items()):
    if not (_y.startswith("/konu/") and _y.count("/") == 3):
        continue
    _s = _p.read_text(encoding="utf-8", errors="replace")
    _m = _SAYI.search(_s)
    if not _m:
        continue
    _toplam = int(_m.group(1))
    _basili = len(re.findall('class="olay-baslik"', _s))
    if _toplam <= _basili:
        continue
    _asan += 1
    dogru(f'href="{_y}arsiv/"' in _s,
          f"{_y} ({_toplam} haberin {_basili} tanesi basili) arsive baglaniyor")
    _ap = _uretilen.get(f"{_y}arsiv/")
    dogru(_ap is not None, f"{_y}arsiv/ uretiliyor")
    _as = _ap.read_text(encoding="utf-8", errors="replace")
    _ab = len(set(re.findall('href="(/haber/[^"]*)"', _as)))
    dogru(_ab >= _toplam, f"{_y}arsiv/ {_toplam} haberin tamamini listeliyor",
          f"yalnizca {_ab} bag var")
    # Konu sayfasindaki ilk ogelerle ayni; indekslenirse ayni liste
    # iki sayfada birden dizine girerdi.
    dogru("noindex" in _as, f"{_y}arsiv/ noindex tasiyor")
dogru(_asan > 0, f"siniri asan konu gercekten var ({_asan} konu)")

# 3. Yetim varlik sayfasi HABER TASIMIYOR -- belgelenmis durum budur.
for _y in _yetim:
    if not _y.startswith("/varlik/"):
        continue
    _s = _uretilen[_y].read_text(encoding="utf-8", errors="replace")
    dogru('href="/haber/' not in _s,
          f"{_y} yetim ama haberi de yok (belgelenmis durum)")

# 4. Baska bir dizinde beklenmedik yetim cikarsa GORUNUR olsun.
_diger = [y for y in _yetim if not y.startswith("/varlik/")]
dogru(not _diger, "varlik disinda yetim sayfa yok",
      f"{len(_diger)} tane: {_diger[:5]}")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
