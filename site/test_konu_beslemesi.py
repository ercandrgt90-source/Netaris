# -*- coding: utf-8 -*-
"""HER KONUNUN KENDI BESLEMESI OLMALI -- VE GERCEKTEN SUZULMUS.

BU DOSYA NEDEN VAR
------------------
Sitede TEK besleme vardi (`/rss.xml`) ve icine her sey giriyordu.
Yalnizca para politikasini izleyen bir okur, jeopolitik ve sirket
haberlerini de almak zorundaydi -- besleme okuyucusunda bu, aboneligi
birakma sebebi.

Konu hub'lari zaten vardi (`/konu/*`), yani veri ve sayfa duruyordu;
eksik olan yalnizca beslemeydi.

EN KRITIK IDDIA: SUZME GERCEK MI
--------------------------------
On iki dosya uretip hepsine AYNI icerigi koymak, ozelligi "yapilmis"
gosterir ama hicbir ise yaramaz. Bu dosya beslemelerin gercekten
ayrildigini olcuyor: bir haber BIRDEN FAZLA beslemede gorunuyorsa
suzgec calismiyor demektir.

NE SINANIYOR
------------
1. Her konu hub'inin bir beslemesi var.
2. Besleme gecerli RSS ve zorunlu alanlari tasiyor.
3. Beslemeler GERCEKTEN ayri: bir haber tek beslemede.
4. Besleme kendi adresini dogru bildiriyor (`atom:link rel=self`).
5. Hub sayfasi beslemeye hem MAKINE hem INSAN icin baglaniyor.
"""

from __future__ import annotations

import pathlib
import re
import xml.etree.ElementTree as ET
from collections import Counter

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_ATOM = "{http://www.w3.org/2005/Atom}link"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_hublar = sorted((_CIKTI / "konu").glob("*/index.html"))
esit(len(_hublar) > 0, True, f"konu hub'i bulundu ({len(_hublar)})")

_beslemesiz = [p.parent.name for p in _hublar
               if not (p.parent / "rss.xml").exists()]
if _beslemesiz:
    print(f"\n  BESLEMESI OLMAYAN KONULAR: {_beslemesiz}")
esit(_beslemesiz, [], f"her konunun beslemesi var ({len(_hublar)})")

print("\nBesleme gecerli ve dolu")
_bozuk, _eksik, _sayilar = [], [], {}
_nerede: Counter = Counter()
for _p in _hublar:
    _ad = _p.parent.name
    _x = (_p.parent / "rss.xml").read_text(encoding="utf-8")
    try:
        _kok = ET.fromstring(_x)
    except ET.ParseError as _e:
        _bozuk.append((_ad, str(_e)[:40]))
        continue
    _ogeler = _kok.findall("channel/item")
    _sayilar[_ad] = len(_ogeler)
    for _alan in ("title", "link", "description"):
        if _kok.find(f"channel/{_alan}") is None:
            _eksik.append((_ad, _alan))
    for _o in _ogeler:
        for _alan in ("title", "link", "guid", "pubDate"):
            if _o.find(_alan) is None or not (_o.find(_alan).text or "").strip():
                _eksik.append((_ad, f"item/{_alan}"))
                break
        _bag = _o.find("link")
        if _bag is not None and _bag.text:
            _nerede[_bag.text] += 1

if _bozuk:
    print(f"\n  BOZUK BESLEME: {_bozuk}")
esit(_bozuk, [], "her besleme gecerli XML")
if _eksik:
    print(f"\n  EKSIK ALAN: {_eksik[:6]}")
esit(_eksik, [], "zorunlu alanlar eksiksiz")
esit(all(v > 0 for v in _sayilar.values()), True,
     f"hicbir besleme bos degil ({min(_sayilar.values())}-"
     f"{max(_sayilar.values())} oge)")

print("\nBeslemeler GERCEKTEN ayri")
# En kritik iddia: ayni haber iki beslemede gorunuyorsa suzgec
# calismiyor ve on iki dosya bir ise yaramiyor demektir.
_cok_yerde = {k: v for k, v in _nerede.items() if v > 1}
if _cok_yerde:
    print(f"\n  BIRDEN FAZLA BESLEMEDE GORUNEN HABER: {len(_cok_yerde)}")
    for _k, _v in list(_cok_yerde.items())[:5]:
        print(f"    {_v}x  {_k[-60:]}")
esit(_cok_yerde, {}, f"her haber TEK beslemede ({len(_nerede)} haber)")
# Sayilar da ayrisiyor mu -- hepsi ayni sayida ise supheli.
esit(len(set(_sayilar.values())) > 1, True,
     f"besleme buyuklukleri farkli ({sorted(set(_sayilar.values()))})")

print("\nBesleme kendi adresini bildiriyor")
_yanlis_self = []
for _p in _hublar:
    _ad = _p.parent.name
    _kok = ET.fromstring((_p.parent / "rss.xml").read_text(encoding="utf-8"))
    _self = _kok.find(f"channel/{_ATOM}")
    _href = _self.get("href") if _self is not None else ""
    if not _href.endswith(f"/konu/{_ad}/rss.xml"):
        _yanlis_self.append((_ad, _href[-50:]))
if _yanlis_self:
    print(f"\n  YANLIS SELF-LINK: {_yanlis_self[:4]}")
esit(_yanlis_self, [], "her besleme KENDI adresini gosteriyor")

print("\nHub sayfasi beslemeye baglaniyor")
_kesif_yok, _gorunur_yok = [], []
for _p in _hublar:
    _ad = _p.parent.name
    _h = _p.read_text(encoding="utf-8", errors="replace")
    if not re.search(rf'rel="alternate"[^>]*konu/{re.escape(_ad)}/rss\.xml',
                     _h, re.S):
        _kesif_yok.append(_ad)
    if f'href="/konu/{_ad}/rss.xml"' not in _h:
        _gorunur_yok.append(_ad)
if _kesif_yok:
    print(f"\n  KESIF BAGI OLMAYAN: {_kesif_yok[:5]}")
esit(_kesif_yok, [], "makine icin kesif bagi var (rel=alternate)")
if _gorunur_yok:
    print(f"\n  GORUNUR BAG OLMAYAN: {_gorunur_yok[:5]}")
esit(_gorunur_yok, [], "insan icin gorunur bag var")

print(f"\nTUM TESTLER GECTI ({_gecti})")
