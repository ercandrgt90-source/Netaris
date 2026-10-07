# -*- coding: utf-8 -*-
"""BEYAN EDILEN GENISLIK, DOSYANIN GERCEK GENISLIGI OLMALI.

BU DOSYA NEDEN VAR
------------------
`srcset` tarayiciya "bu dosya su kadar piksel genisliginde" diye bir
SOZ veriyor. Soz yanlissa tarayici bile bile yanlis adayi seciyor ve
kusur hicbir yerde gorunmuyor: sayfa dogru cizilir, sinamalar yesil
kalir, yalnizca okur gereksiz bayt indirir.

OLCULDU (2026-10-07), dort cercevede gercek aygit taklidiyle, haber
sayfasinin gorseli:

  mobil       yuva 356 px, dpr 2  -> 1920 px / 606 KB   YANLIS
  tablet      yuva 670 px, dpr 2  -> 1920 px            dogru
  masa        yuva 798 px, dpr 1  ->  960 px            dogru
  masa retina yuva 798 px, dpr 2  -> 1920 px            dogru

Sebep: `srcset="{kucuk} 1x, {buyuk} 2x"`. `x` tanimlayicisi YERLESIM
GENISLIGINI BILMEZ; tarayici yalnizca ekran yogunluguna bakar.
Telefonda 712 fiziksel piksel yetiyorken 1920 iniyordu.

Duzeltmeden sonra ayni cercevelerde olculdu:
  LCP 6.580 ms -> 3.252 ms,  aktarim 874 KB -> 445 KB.

IKINCI KUSUR, KART SABLONLARINDA: `srcset="{orta} 400w, {buyuk} 800w"`
yaziyordu ve IKI SAYI DA YANLISTI -- `o/` dosyalari 500 piksel, kok
dosyalarin 276'si 1920. Sabitler hedefi soyluyor (`ORTA_GENISLIK`
400, `COMMONS_GENISLIK` 1600), dosyalar gercegi. "800w" etiketli
1920 piksellik dosya, 400 piksellik bir karta iniyordu.

NE SINANIYOR
------------
1. `foto_kaynak_kumesi` tek adayla BOS donuyor (tek kaynakli gorsele
   `srcset` yazmak anlamsiz).
2. Ayni genislikteki iki aday TEKILLESIYOR -- tarayiciyi yaniltmasin.
3. Uretilen ciktidaki her `srcset` genislik tanimlayici kullaniyor;
   `1x`/`2x` bicimi hic gecmiyor.
4. `srcset` yazan her gorsel `sizes` da yaziyor -- `w` tanimlayici
   `sizes` olmadan varsayilan `100vw` ile calisir ve yine yanlis
   adayi secer.
5. BEYAN EDILEN HER GENISLIK, DOSYANIN GERCEK GENISLIGINE ESIT.
   Asil koruma bu: 400w/800w yalanini yakalayan madde.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path.insert(0, str(_SITE))

import insa                                      # noqa: E402

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


print("")
print("Gorsel kaynak kumesi")

dogru(insa.foto_kaynak_kumesi("/statik/foto/yok.jpg") == {},
      "tek adayla srcset yazilmiyor")
dogru(insa.foto_kaynak_kumesi("", "") == {}, "bos adayla srcset yazilmiyor")

if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

# Gercek bir cift bul: ayni adin kok ve `y/` surumu.
_ornek = next((p for p in (_CIKTI / "statik" / "foto" / "y").glob("*.jpg")
               if (_CIKTI / "statik" / "foto" / p.name).exists()), None)
dogru(_ornek is not None, "olcum icin gercek bir gorsel cifti var")
_buyuk = "/statik/foto/" + _ornek.name
_kucuk = "/statik/foto/y/" + _ornek.name
_k = insa.foto_kaynak_kumesi(_kucuk, _buyuk)
dogru(bool(_k), "gercek ciftte srcset uretiliyor")
dogru("w," in _k["srcset"] and _k["srcset"].rstrip().endswith("w"),
      "genislik tanimlayici kullaniliyor", _k["srcset"])
dogru(insa.foto_kaynak_kumesi(_buyuk, _buyuk) == {},
      "ayni genislikteki iki aday tekillesiyor (srcset yazilmiyor)")

_IMG = re.compile("<img[^>]*>")
_SRCSET = re.compile('srcset="([^"]*)"')
_SIZES = re.compile('sizes="([^"]*)"')
_ADAY = re.compile("([^ ,]+) +([0-9]+)w")

_sayfa = 0
_etiket = 0
_x_bicimi = []
_sizes_yok = []
_yanlis = []
for _p in _CIKTI.rglob("index.html"):
    _s = _p.read_text(encoding="utf-8", errors="replace")
    if "srcset" not in _s:
        continue
    _sayfa += 1
    _y = "/" + _p.parent.relative_to(_CIKTI).as_posix() + "/"
    for _m in _IMG.finditer(_s):
        _ss = _SRCSET.search(_m.group(0))
        if not _ss:
            continue
        _etiket += 1
        _ham = _ss.group(1)
        if "1x" in _ham or "2x" in _ham:
            _x_bicimi.append(_y)
            continue
        if not _SIZES.search(_m.group(0)):
            _sizes_yok.append(_y)
        for _yol, _g in _ADAY.findall(_ham):
            _gercek = insa.foto_genisligi(_yol)
            if _gercek and int(_g) != _gercek:
                _yanlis.append((_y, _yol, _g, _gercek))

print(f"  tarandi: {_sayfa} sayfa, {_etiket} srcset")
dogru(_etiket > 50, f"tarama dolu ({_etiket} srcset)")
dogru(not _x_bicimi, "hicbir srcset 1x/2x bicimi kullanmiyor",
      f"{len(_x_bicimi)} tane, ilki: {_x_bicimi[0] if _x_bicimi else ''}")
dogru(not _sizes_yok, "srcset yazan her gorsel sizes da yaziyor",
      f"{len(_sizes_yok)} tane, ilki: {_sizes_yok[0] if _sizes_yok else ''}")
dogru(not _yanlis, "beyan edilen genislik dosyanin gercek genisligi",
      f"{len(_yanlis)} yanlis, ilki: {_yanlis[0] if _yanlis else ''}")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
