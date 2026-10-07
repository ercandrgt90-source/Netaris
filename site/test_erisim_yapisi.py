# -*- coding: utf-8 -*-
"""YER ISARETLERI ADLI VE BIRBIRINDEN AYIRT EDILEBILIR OLMALI.

BU DOSYA NEDEN VAR
------------------
Ekran okuyucu kullanicisi sayfayi bastan sona okumuyor; YER
ISARETLERINI (landmark) liste halinde gezip istedigine atliyor. O
listede iki tane adsiz "navigation" gorunuyorsa ikisi birbirinden
ayirt edilemez -- kullanici hangisinin ust menu hangisinin alt bilgi
oldugunu ancak ikisini de acip deneyerek bulur.

OLCULDU (2026-10-07), tarayicinin KENDI erisilebilirlik agacindan
cekilerek: her sayfada IKI adsiz `<nav>` vardi (ust menu ve alt
bilgi), uyelik panelinde bir ucuncusu.

IKINCI BULGU -- AYNI BILESEN, IKI AD: kirinti yolu 1.907 sayfada
"Neredesiniz", 15 sayfada "Konum" diye adlandirilmisti. Ayni bilesen,
iki ad; kullanici icin sitenin bir bolumunde baska bir seymis gibi
duyuluyor.

OLCU NEREDEN ALINIYOR -- VE NEDEN ORADAN
----------------------------------------
Bu turda kendi yazdigim DOM kurallari ARKA ARKAYA IKI YANLIS ALARM
uretti:

  * `/gundem/` icindeki gorsel baglantilari "adsiz" diye bildirdi;
    oysa `aria-hidden="true" tabindex="-1"` tasiyorlar ve ad zaten
    yanlarindaki baslik baglantisinda -- yani DOGRU desen.
  * `/giris/` formundaki alanlari "etiketsiz" diye bildirdi; oysa
    `<label>` ICINDE duruyorlar ve erisilebilirlik agaci adlarini
    "E-posta" ve "Parola" olarak veriyor.

Ders: erisilebilir ad, DOM'a bakarak tahmin edilmez; tarayicinin
hesapladigi agactan OKUNUR. Bu sinama yine de uretilen HTML'e
bakiyor, ama yalnizca yapisal ve tartismasiz olani soruyor: bir
`<nav>` ad TASIYOR MU. "Ad dogru mu" sorusu tarayicida cevaplandi.

NE SINANIYOR
------------
1. Uretilen her `<nav>` bir ad tasiyor (`aria-label` ya da
   `aria-labelledby`).
2. Bir sayfadaki `<nav>` adlari BIRBIRINDEN FARKLI.
3. Kirinti yolu (`konum-izi`) butun sitede TEK bir ad kullaniyor.
4. Her sayfada tam bir `<main>` var.
"""

from __future__ import annotations

import collections
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


print("")
print("Yer isaretleri")

if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_NAV = re.compile("<nav([^>]*)>")
_AD = re.compile('aria-label="([^"]*)"')
_LABELLEDBY = re.compile('aria-labelledby="([^"]*)"')
# Kirinti yolu iki ayri sinifla uretiliyor: `konum-izi` (bagli) ve
# `kirinti` (duz metin, varlik sayfasi). Okur icin AYNI bilesen,
# dolayisiyla adi da ayni olmali.
_KIRINTI = re.compile('<nav class="(?:konum-izi|kirinti)"([^>]*)>')
_MAIN = re.compile("<main[ >]")

_sayfa = 0
_adsiz = []
_cakisan = []
_kirinti_adlari = collections.Counter()
_main_yanlis = []

for _p in _CIKTI.rglob("index.html"):
    _s = _p.read_text(encoding="utf-8", errors="replace")
    _y = "/" + _p.parent.relative_to(_CIKTI).as_posix() + "/"
    _sayfa += 1
    _adlar = []
    for _m in _NAV.finditer(_s):
        _nitelik = _m.group(1)
        _a = _AD.search(_nitelik) or _LABELLEDBY.search(_nitelik)
        if not _a:
            _adsiz.append(_y)
        else:
            _adlar.append(_a.group(1))
    if len(_adlar) != len(set(_adlar)):
        _cakisan.append(_y)
    for _m in _KIRINTI.finditer(_s):
        _a = _AD.search(_m.group(1))
        if _a:
            _kirinti_adlari[_a.group(1)] += 1
    if len(_MAIN.findall(_s)) != 1:
        _main_yanlis.append(_y)

print(f"  tarandi: {_sayfa} sayfa")
dogru(_sayfa > 500, f"tarama dolu ({_sayfa} sayfa)")
dogru(not _adsiz, "adsiz nav yok",
      f"{len(_adsiz)} sayfada, ilki: {_adsiz[0] if _adsiz else ''}")
dogru(not _cakisan, "bir sayfadaki nav adlari birbirinden farkli",
      f"{len(_cakisan)} sayfada, ilki: {_cakisan[0] if _cakisan else ''}")
dogru(len(_kirinti_adlari) == 1,
      f"kirinti yolu TEK ad kullaniyor ({list(_kirinti_adlari)})",
      f"bulunan: {dict(_kirinti_adlari)}")
dogru(not _main_yanlis, "her sayfada tam bir main var",
      f"{len(_main_yanlis)} sayfada, ilki: {_main_yanlis[0] if _main_yanlis else ''}")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
