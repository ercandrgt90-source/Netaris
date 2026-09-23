# -*- coding: utf-8 -*-
""""BEN MAKALEYIM" DIYEN SAYFA TARIHINI DE SOYLEMELI.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-09-24): 1837 sayfanin 1724'u `og:type="article"`
bildiriyordu ama `article:published_time` ve `article:author` HIC
yoktu.

NEDEN JSON-LD YETMIYOR: arama motorlari yapisal veriyi okuyor ve o
eksiksizdi (datePublished, dateModified, author, publisher). Ama
LinkedIn ve Facebook paylasim kartini OPEN GRAPH'tan kuruyor,
JSON-LD'ye bakmiyor. Finans icerigi agirlikli olarak LinkedIn'de
dolasiyor; orada tarihsiz gorunmek icerigi eski ya da kaynaksiz
gosteriyor.

IKI KAYNAK AYRISMASIN
---------------------
Bu depoda "ayni soruya iki cevap veren iki kod yolu" kusuru
defalarca yasandi (haber adresi, izgara sayaci, satir yuksekligi...).
Tarih artik iki yerde YAZIYOR -- JSON-LD ve Open Graph -- ama tek
alandan besleniyor. Bu dosya ikisinin AYNI kalmasini sinar; ayni
kalmiyorsa biri digerinin kopyasi degil, RAKIBI olur.

NE SINANIYOR
------------
1. `og:type="article"` diyen her sayfa `article:published_time`
   ve `article:author` tasiyor.
2. Open Graph tarihi JSON-LD `datePublished` ile AYNI.
3. Makale olmayan sayfalar bu alanlari TASIMIYOR (yanlis vaat).
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def alan(html: str, desen: str) -> str:
    m = re.search(desen, html)
    return m.group(1) if m else ""


def makale_mi(html: str) -> bool:
    return alan(html, r'property="og:type" content="([^"]*)"') == "article"


def og_tarih(html: str) -> str:
    return alan(html, r'property="article:published_time" content="([^"]*)"')


def ld_tarih(html: str) -> str:
    return alan(html, r'"datePublished"\s*:\s*"([^"]*)"')


print("\nTarama gercekten calisiyor mu")
_D = ('<meta property="og:type" content="article">'
      '<meta property="article:published_time" content="2026-01-02">'
      '"datePublished": "2026-01-02",')
esit(makale_mi(_D), True, "makale tipi taniniyor")
esit(og_tarih(_D), "2026-01-02", "OG tarihi okunuyor")
esit(ld_tarih(_D), "2026-01-02", "JSON-LD tarihi okunuyor")
esit(makale_mi('<meta property="og:type" content="website">'), False,
     "website tipi makale sayilmiyor")

print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_makale = _eksik_tarih = _eksik_yazar = _ayrisik = 0
_yanlis_vaat = []
_ornek_eksik: list[str] = []
_ornek_ayrisik: list[tuple[str, str, str]] = []

for _p in _CIKTI.rglob("index.html"):
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _yol = _p.relative_to(_CIKTI).as_posix()
    if not makale_mi(_h):
        # Makale olmayan sayfa makale alani TASIMAMALI: tasirsa
        # platforma tutamayacagi bir vaat veriyor.
        if og_tarih(_h):
            _yanlis_vaat.append(_yol[:44])
        continue
    _makale += 1
    _og = og_tarih(_h)
    if not _og:
        _eksik_tarih += 1
        if len(_ornek_eksik) < 4:
            _ornek_eksik.append(_yol[:44])
    if 'property="article:author"' not in _h:
        _eksik_yazar += 1
    _ld = ld_tarih(_h)
    if _og and _ld and _og[:10] != _ld[:10]:
        _ayrisik += 1
        if len(_ornek_ayrisik) < 4:
            _ornek_ayrisik.append((_yol[:38], _og, _ld))

esit(_makale > 100, True, f"makale sayfasi bulundu ({_makale})")

if _ornek_eksik:
    print("\n  TARIHSIZ MAKALE ORNEKLERI:")
    for _y in _ornek_eksik:
        print(f"    {_y}")
esit(_eksik_tarih, 0, f"her makale yayim tarihini bildiriyor ({_makale})")
esit(_eksik_yazar, 0, "her makale yazarini bildiriyor")

if _ornek_ayrisik:
    print("\n  OPEN GRAPH ILE JSON-LD AYRISMIS:")
    for _y, _o, _l in _ornek_ayrisik:
        print(f"    {_y}  OG={_o}  LD={_l}")
esit(_ayrisik, 0, "OG tarihi JSON-LD ile AYNI (tek kaynak)")

if _yanlis_vaat:
    print("\n  MAKALE OLMADIGI HALDE MAKALE ALANI TASIYAN:")
    for _y in _yanlis_vaat[:6]:
        print(f"    {_y}")
esit(_yanlis_vaat, [], "makale olmayan sayfa makale alani tasimiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
