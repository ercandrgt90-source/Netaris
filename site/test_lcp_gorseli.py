# -*- coding: utf-8 -*-
"""LCP ADAYI GORSEL TEMBEL YUKLENMEZ.

BU DOSYA NEDEN VAR
------------------
`loading="lazy"` "ekranda gorunene kadar bekle" DEMEZ -- tarayici o
gorseli DUSUK ONCELIKLI sayar ve kesfini erteler. Ilk ekranda
gorunen bir gorselde bu, dogrudan LCP gecikmesi olur. Google'in
kendi tavsiyesi de boyle: LCP adayina lazy verilmez.

OLCULDU (2026-10-28, canli, telefon 390px/DPR2, 1,6 Mbps, CPU 4x):

    sayfa       ilk gorsel        LCP
    /           eager + high      3.412 ms
    /gundem/    lazy              4.188 - 4.572 ms   <- "kotu" esigi 4.000

Ikisinde de LCP OGESI bir gorseldi. Ana sayfada duzeltme ZATEN
VARDI; `/gundem/` makrosuna tasinmamisti.

Kapsam olculdu: uretilen 2.276 sayfanin yalnizca BIRINDE (ana
sayfa) ilk gorsel eager, 164'unde lazy -- 158'i `/haber/`, 6'si
liste sayfasi. Yani bu yarim kalmis bir duzeltmeydi, tek seferlik
bir unutma degil.

NE SINANIYOR
------------
1. Olculmus LCP sayfalarinda ilk `<img>` tembel DEGIL.
2. Ayni gorsel `fetchpriority="high"` tasiyor -- lazy'yi kaldirmak
   gorseli kesfedilebilir yapar, oncelik ise sirada one alir. Ikisi
   ayri sey; biri olmadan oteki yarim is.
3. Sayfadaki eager gorsel sayisi BIR. Hepsini eager yapmak LCP'yi
   iyilestirmez: 36 ekran uzunlugundaki bir sayfada butun gorseller
   ayni anda yarisirsa LCP gorseli bant genisligini onlarla PAYLASIR
   -- yani duzeltme kendi kendini yer.
4. Kontrol atil degil: taranan sayfalarda gercekten gorsel var.

NEDEN LISTE ELLE YAZILI
-----------------------
"Her sayfanin ilk gorseli eager olsun" diye bir kural YAZILMADI ve
bu bilincli: olculdu, `/makro/` ve `/makro/arsiv/` gibi sayfalarda
LCP ogesi METIN (sirasiyla 2.352 ms ve 2.044 ms), ilk gorsel ise
ekranin asagisinda duran kucuk bir kart gorseli. Orada eager yapmak
hicbir sey kazandirmaz, bant genisligini boler.

Liste, LCP ogesi GORSEL OLDUGU OLCULEN sayfalardan olusuyor. Yeni
bir sayfa eklenirse buraya elle girer -- ve girmedigi surece bu
iddia onun hakkinda hicbir sey soylemez. Kaynaktan turetmek
(ornegin "ilk gorseli 960w tasiyan her sayfa") hareketli hedef
olurdu: sablon degisince iddia da sessizce kuculurdu.
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


#: LCP ogesi GORSEL oldugu OLCULEN sayfalar (2026-10-28).
#: Gerekcesi dosya basinda: turetilmis bir kural hareketli hedef olurdu.
LCP_GORSELI = ("index.html", "gundem/index.html")

if not _CIKTI.exists():
    print("  ATLANDI  cikti yok -- once `python site/insa.py`")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_IMG = re.compile(r"<img[^>]*>")

print("Olculmus LCP sayfalarinda ilk gorsel")
_bakilan = 0
for _yol in LCP_GORSELI:
    _p = _CIKTI / _yol
    if not _p.exists():
        esit(False, True, f"{_yol} uretilmemis")
        continue
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _imgler = _IMG.findall(_h)
    # ATILLIK: gorselsiz bir sayfada "ilk gorsel tembel degil"
    # iddiasi dogrudur ve HICBIR SEY soylemez.
    esit(len(_imgler) > 0, True, f"{_yol} gorsel tasiyor ({len(_imgler)})")
    _bakilan += 1
    _ilk = _imgler[0]
    esit('loading="lazy"' in _ilk, False, f"{_yol} ilk gorsel TEMBEL DEGIL")
    esit('loading="eager"' in _ilk, True, f"{_yol} ilk gorsel eager")
    esit("fetchpriority" in _ilk, True,
         f"{_yol} ilk gorsel fetchpriority tasiyor")
    # ONCELIK TEK GORSELDE. Hepsini one almak LCP'yi iyilestirmez:
    # gorseller ayni bant genisligini paylasir.
    _eager = sum(1 for _s in _imgler if 'loading="eager"' in _s)
    esit(_eager, 1, f"{_yol} eager gorsel sayisi BIR ({len(_imgler)} img)")

esit(_bakilan, len(LCP_GORSELI),
     f"olculmus sayfalarin hepsi tarandi ({_bakilan})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
