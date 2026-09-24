# -*- coding: utf-8 -*-
"""URETILEN HER BESLEME DEFTERE GIRMELI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-24): on iki konu beslemesi uretilmisti ve her biri
YALNIZCA kendi hub'indan baglaniyordu -- on iki besleme, on iki bag,
hepsi kendine. Zaten o sayfada olmayan kimse varliklarindan haberdar
olamiyordu.

Bu, depoda tekrarlayan bir kusur: CEVAP URETILIYOR AMA OKUNABILIR
DEGIL. Beslemelerin kendisi dogruydu; eksik olan onlara giden yoldu.

ASIL IS: DEFTERIN GERI KALMASINI ENGELLEMEK
-------------------------------------------
Bugun deftere on uc besleme yazmak kolay. Tehlike, YARIN eklenen
on dorduncu beslemenin sessizce disarida kalmasi -- defter dogru
gorunur, eksik oldugu anlasilmaz.

Bu yuzden sinama sayiya bakmiyor: diskteki `rss.xml` KUMESI ile
defterdeki kume BIREBIR ayni olmak zorunda. Yeni besleme ekleyip
deftere baglamayan biri bu dosyayi kirmizi yakar.

NE SINANIYOR
------------
1. OPML gecerli ve her besleme icin bir `outline` tasiyor.
2. Defter = disk. Fazlasi da eksigi de kirmizi.
3. Defterdeki her adres GERCEKTEN var (olu bag yok).
4. Sayfa her beslemeye hem MAKINE hem INSAN icin baglaniyor.
5. Sayfanin kendisi siteden ulasilabilir (oksuz degil).
6. Kontrolun kendisi calisiyor -- uydurma besleme YAKALANIYOR.
"""

from __future__ import annotations

import pathlib
import re
import sys
import xml.etree.ElementTree as ET

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path[:0] = [str(_SITE)]

import insa  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("\nOPML ureteci")
_ornek = insa.opml_uret([
    {"ad": "Netaris — Deneme", "yol": "/konu/deneme/rss.xml",
     "sayfa": "/konu/deneme/"},
])
_k = ET.fromstring(_ornek)
esit(_k.tag, "opml", "kok oge `opml`")
esit(_k.get("version"), "2.0", "OPML 2.0")
esit(_k.find("head/title") is not None, True, "baslik var")
_o = _k.findall("body/outline")
esit(len(_o), 1, "her besleme icin bir `outline`")
esit(_o[0].get("type"), "rss", "tur bildirimi (`type=rss`)")
esit(_o[0].get("xmlUrl"), "https://netaris.net/konu/deneme/rss.xml",
     "`xmlUrl` mutlak adres -- okuyucu goreli adresi cozemez")
esit(_o[0].get("htmlUrl"), "https://netaris.net/konu/deneme/",
     "`htmlUrl` insan sayfasini gosteriyor")

# Sayfasi olmayan besleme de kirilmamali.
_sayfasiz = ET.fromstring(insa.opml_uret([{"ad": "A", "yol": "/rss.xml"}]))
esit(_sayfasiz.find("body/outline").get("htmlUrl"), "https://netaris.net/",
     "sayfasi olmayan besleme ana sayfaya dusuyor (uretec kirilmiyor)")

print("\nUretilen ciktida")
if not (_CIKTI / "beslemeler.opml").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_ham = (_CIKTI / "beslemeler.opml").read_text(encoding="utf-8")
_kok = ET.fromstring(_ham)
_defter = {(e.get("xmlUrl") or "").replace(insa.SITE["adres"], "")
           for e in _kok.findall("body/outline")}

# DEFTER = DISK. Asil iddia bu.
_diskte = {"/" + p.relative_to(_CIKTI).as_posix()
           for p in _CIKTI.rglob("rss.xml")}
_eksik = sorted(_diskte - _defter)
_fazla = sorted(_defter - _diskte)
if _eksik:
    print(f"\n  DEFTERE GIRMEMIS BESLEME: {_eksik}")
if _fazla:
    print(f"\n  DEFTERDE OLUP DISKTE OLMAYAN: {_fazla}")
esit(_eksik, [], f"uretilen her besleme defterde ({len(_diskte)} besleme)")
esit(_fazla, [], "defterde olu bag yok")

print("\nSayfa")
_g = (_CIKTI / "beslemeler" / "index.html").read_text(
    encoding="utf-8", errors="replace")
_gorunur = set(re.findall(r'href="(/[^"]*rss\.xml)"', _g))
_kesif = set(re.findall(
    r'rel="alternate"[^>]*href="[^"]*?(/(?:konu/[^"]*)?rss\.xml)"', _g))
esit(sorted(_diskte - _gorunur), [], "sayfa her beslemeye GORUNUR baglaniyor")
esit(sorted(_diskte - _kesif), [],
     "sayfa her beslemeyi MAKINEYE bildiriyor (rel=alternate)")
esit('href="/beslemeler.opml"' in _g, True, "paket indirilebiliyor")

# SAYFANIN KENDISI OKSUZ OLMAMALI. Dizine giren ama hicbir yerden
# baglanmayan sayfa, bu depoda defalarca duzeltilen kusurun ayni.
_nereden = sum(
    1 for p in (_CIKTI / "index.html", _CIKTI / "gundem" / "index.html")
    if p.exists() and 'href="/beslemeler/"' in p.read_text(
        encoding="utf-8", errors="replace"))
esit(_nereden, 2, "ana sayfa ve /gundem/ deftere baglaniyor (site geneli)")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Uydurma bir besleme dosyasi deftere girmediginden YAKALANMALI.
# Mekanizmayi kendi sinamasindan gecirmemek, bu oturumda dort kez
# mutasyonu yesil birakan kusurdu.
_sahte = _CIKTI / "konu" / "__sinama__" / "rss.xml"
_sahte.parent.mkdir(parents=True, exist_ok=True)
_sahte.write_text("<rss/>", encoding="utf-8")
try:
    _yeni = {"/" + p.relative_to(_CIKTI).as_posix()
             for p in _CIKTI.rglob("rss.xml")}
    esit(sorted(_yeni - _defter), ["/konu/__sinama__/rss.xml"],
         "deftere girmemis besleme YAKALANIYOR (kural sahte degil)")
finally:
    _sahte.unlink()
    _sahte.parent.rmdir()

print(f"\nTUM TESTLER GECTI ({_gecti})")
