# -*- coding: utf-8 -*-
"""ICERIGI OLMAYAN VARLIK SAYFASI DIZINE GIRMEZ.

BU DOSYA NEDEN VAR
------------------
Canli site elle incelendiginde olculdu (2026-10-29): 75 varlik
sayfasinin 20'sinde ne veri serisi ne yayimlanmis haber vardi ve
hepsi `index, follow` basip `sitemap.xml`de duruyordu. En zayifi
`/varlik/powell/`: 558 gorunur karakter, tek yapisal iliski,
govdesinde "Bu konuda henuz yayimlanmis haber yok".

Sayfanin kendi vaadi "Veri arsivi" ve "Gelismeler". Ikisi de bossa
sayfa vaat ettigi seyi veremiyor.

OLCUT DUZENEK, KARAKTER SAYISI DEGIL
------------------------------------
"N karakterden kisa sayfa" esigi secmek, dagilimlar cakistigi icin
yalnizca hangi hatayi yapacagimizi secmek olurdu: /varlik/dax/ 1.130
karakter tasiyor ve BOS (uc yapisal iliski + tanim), /varlik/spk/ 418
karakter tasiyor ve DOLU (bir haber). Olcut bu yuzden iceriktir:
seri YOK ve yayimlanan haber YOK.

IKI YON DE SINANIYOR
--------------------
Yalnizca "bos sayfa noindex tasiyor" denetlenirse kural BUTUN
sayfalari noindex yaparak sahte bicimde dogrulanabilir -- ve o
degisiklik siteyi aramadan tamamen silerdi. Bu yuzden ikinci yon de
var: ICERIGI OLAN sayfa noindex TASIMAMALI.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti" / "varlik"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_NOINDEX = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)
#: Sayfa govdesindeki iki icerik isareti. Sablonun yazdigi metne
#: DEGIL, sayilara bakiliyor.
_SERI = re.compile(r"(\d+) g[^<]{0,3}zlemlik seri")
_HABER = re.compile(r"Ar[^<]{0,3}ivde (\d+) haber")

if not _CIKTI.exists():
    print("  ATLANDI  cikti yok -- once `python site/insa.py`")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

print("Varlik sayfalarinda dizin karari")

_bos_ama_acik: list[str] = []
_dolu_ama_kapali: list[str] = []
_bos = 0
_dolu = 0

for _p in sorted(_CIKTI.glob("*/index.html")):
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _duz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _h))
    _g = _SERI.search(_duz)
    _a = _HABER.search(_duz)
    _seri = int(_g.group(1)) if _g else 0
    _haber = int(_a.group(1)) if _a else 0
    _kapali = bool(_NOINDEX.search(_h))
    _yol = "/varlik/" + _p.parent.name + "/"
    if _seri == 0 and _haber == 0:
        _bos += 1
        if not _kapali:
            _bos_ama_acik.append(_yol)
    else:
        _dolu += 1
        if _kapali:
            _dolu_ama_kapali.append(_yol)

# ATILLIK: hic sayfa taranmazsa iki iddia da DOGRU olur ve hicbir sey
# soylemez. Bu depoda mesru sifiri kusur sayan kontroller dagitimi
# durdurdu, o yuzden olcut MEKANIZMA: tarama sayfa BULMUS olmali.
esit(_bos + _dolu > 40, True,
     f"varlik sayfasi tarandi ({_bos + _dolu})")
# Ikinci atillik kapisi: iki SINIFIN IKISI DE dolu olmali. Hepsi bos
# ya da hepsi dolu olsaydi, iddialardan biri hicbir sey sinamiyor
# olurdu ve bunu fark etmezdik.
esit(_bos > 0 and _dolu > 0, True,
     f"iki sinif da bulundu (bos {_bos}, dolu {_dolu})")

if _bos_ama_acik:
    print(f"  ICERIKSIZ AMA DIZINE ACIK ({len(_bos_ama_acik)}):")
    for _y in _bos_ama_acik[:8]:
        print(f"    {_y}")
esit(len(_bos_ama_acik), 0,
     f"iceriksiz sayfa dizine kapali ({_bos} sayfa)")

if _dolu_ama_kapali:
    print(f"  ICERIGI VAR AMA DIZINE KAPALI ({len(_dolu_ama_kapali)}):")
    for _y in _dolu_ama_kapali[:8]:
        print(f"    {_y}")
esit(len(_dolu_ama_kapali), 0,
     f"icerigi olan sayfa dizine acik ({_dolu} sayfa)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
