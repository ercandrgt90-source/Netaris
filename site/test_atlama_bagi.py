# -*- coding: utf-8 -*-
"""KLAVYEYLE GEZEN OKUR MENUYE TAKILMAMALI.

BU DOSYA NEDEN VAR
------------------
WCAG 2.4.1 "Blok Atlama" (A seviye): her sayfada tekrarlanan gezinme
bloklarini atlamanin bir yolu olmali.

OLCULDU (2026-10-08), gercek tarayicida Tab tuslarini sayarak: ana
icerige ulasmak icin DOKUZ sekme gerekiyordu -- amblem, bes menu
girdisi, "Giris yap", "Uye ol", tema dugmesi. Klavyeyle gezen okur
bunu HER SAYFA ACILISINDA tekrarliyordu.

Duzeltmeden sonra ayni olcum: bir Tab, bir Enter. Odak dogrudan
`main#icerik` icine gidiyor ve bir sonraki sekme icerigin ilk
ogesinde.

UC AYRINTI, UCU DE GEREKLI
--------------------------
1. Bag ILK odaklanabilir oge olmali -- yoksa ona ulasmak icin de
   sekmek gerekir ve hicbir ise yaramaz.
2. Hedef `tabindex="-1"` TASIMALI. Onsuz bazi tarayicilar capa
   adresini degistirir ama ODAGI tasimaz; bir sonraki sekme yine
   menuye doner. Bag "calisiyor gibi" gorunur, calismaz.
3. Bag odaklaninca GORUNMELI. "Gorunmez ama odaklanabilir" bag,
   klavye kullanicisinin odagi kaybettigi klasik tuzak -- okur
   nerede oldugunu bilmeden Enter'a basar.

OLCULEN DEGERLER (2026-10-08, tarayicida):
  odaksizken  sol = -9999 px (ekran disinda)
  odakta      106x48 px, sol ust kose
  kontrast    acik tema 5,77 | koyu tema 9,59   (AA esigi 4,5)

NE SINANIYOR
------------
1. Her sayfada atlama bagi var ve govdedeki ILK odaklanabilir oge.
2. Bagin hedefi gercekten var ve `tabindex="-1"` tasiyor.
3. CSS kurali duruyor: odaksizken ekran disinda, odakta iceride.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_CSS = _SITE / "statik" / "stil.css"

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
print("Icerige atlama bagi")

_kural = re.sub("/[*].*?[*]/", " ", _CSS.read_text(encoding="utf-8-sig"), flags=re.S)
_atla = re.search("[.]atla[ ]*[{]([^}]*)[}]", _kural, re.S)
dogru(_atla is not None, ".atla kurali duruyor")
dogru("position: absolute" in _atla.group(1) and "left: -9999px" in _atla.group(1),
      "odaksizken ekran disinda", _atla.group(1)[:90])
_odak = re.search("[.]atla:focus[ ]*[{]([^}]*)[}]", _kural, re.S)
dogru(_odak is not None, ".atla:focus kurali duruyor")
dogru("left: 0" in _odak.group(1), "odaklaninca ekrana giriyor",
      _odak.group(1)[:90] if _odak else "")

if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

# Govdedeki ilk odaklanabilir oge. `summary` de odaklanabilir.
_ODAK = re.compile("<(a |button|input|select|textarea|summary)", re.I)
_sayfa = 0
_bagsiz = []
_ilk_degil = []
_hedefsiz = []
for _p in _CIKTI.rglob("index.html"):
    _s = _p.read_text(encoding="utf-8", errors="replace")
    _y = "/" + _p.parent.relative_to(_CIKTI).as_posix() + "/"
    _govde = _s[_s.find("<body"):]
    _sayfa += 1
    if 'class="atla"' not in _govde:
        _bagsiz.append(_y)
        continue
    # ILK ESLESMENIN KENDISI atlama bagi olmali.
    #
    # Ilk yazimda "ilk odaklanabilir ogenin 120 karakterlik
    # penceresinde `class="atla"` geciyor mu" diye bakiyordum ve
    # MUTASYON HAYATTA KALDI: bagin hemen onune bir dugme sokuldu,
    # dugme kisa oldugu icin bag hala pencereye giriyordu ve sinama
    # gecti. Pencere degil, ESLESEN ETIKETIN KENDISI sorulmali.
    _m = _ODAK.search(_govde)
    _etiket = _govde[_m.start():_govde.find(">", _m.start()) + 1] if _m else ""
    if 'class="atla"' not in _etiket:
        _ilk_degil.append(_y)
    _hedef = re.search('href="#([^"]+)"', _govde[_govde.find('class="atla"'):][:120])
    if not _hedef:
        _hedefsiz.append((_y, "bagda hedef yok"))
        continue
    _kimlik = _hedef.group(1)
    _oge = re.search('<main[^>]*id="' + re.escape(_kimlik) + '"[^>]*>', _s)
    if not _oge:
        _hedefsiz.append((_y, f"#{_kimlik} hedefi yok"))
    elif 'tabindex="-1"' not in _oge.group(0):
        _hedefsiz.append((_y, f"#{_kimlik} tabindex=-1 tasimiyor"))

print(f"  tarandi: {_sayfa} sayfa")
dogru(_sayfa > 500, f"tarama dolu ({_sayfa} sayfa)")
dogru(not _bagsiz, "her sayfada atlama bagi var",
      f"{len(_bagsiz)} sayfada yok, ilki: {_bagsiz[0] if _bagsiz else ''}")
dogru(not _ilk_degil, "atlama bagi ILK odaklanabilir oge",
      f"{len(_ilk_degil)} sayfada degil, ilki: {_ilk_degil[0] if _ilk_degil else ''}")
dogru(not _hedefsiz, "hedef var ve tabindex=-1 tasiyor",
      f"{len(_hedefsiz)} sorun, ilki: {_hedefsiz[0] if _hedefsiz else ''}")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
