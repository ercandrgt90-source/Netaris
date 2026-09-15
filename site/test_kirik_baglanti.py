"""URETILEN SITEDE KIRIK IC BAGLANTI OLMAMALI.

BU DOSYA NEDEN VAR
------------------
Kural, bir kusuru duzeltmek icin degil, YENI ACILAN BIR KOR NOKTAYI
kapatmak icin kondu.

2026-09-15'e kadar sitenin 404 sayfasi YOKTU: bulunamayan adres bos
bir sayfa donuyordu. Cirkin ama gorunur -- kirik bir baglantiya
tiklayan okur bembeyaz bir ekran goruyordu ve bunun bir ariza oldugu
belliydi.

Ayni gun duzgun bir 404 sayfasi eklendi (`bulunamadi.html`). Iyi bir
sey, ama bir yan etkisi var: artik kirik bir baglanti, gezinti ve
arama tasiyan DERLI TOPLU bir sayfaya dusuyor. Yani "kirik" ile
"kasitli" ayni goruntuyu veriyor. Bir duzeltme, bir hata sinifini
gorunmez kilarsa, o sinifi olcen bir kural gerekir.

Olculdu (2026-09-15, kuralin kondugu gun): 1820 sayfa, 6114 uretilen
yol, KIRIK HEDEF: 0. Kural bu temizligi koruyor.

NE SINANIYOR
------------
1. Uretilen her sayfadaki her `href`/`src` -- site KOKUNDEN baslayan
   yollar icin -- gercekten uretilmis bir dosyaya gidiyor.
2. Taramanin kendisi dolu: sayfa ve yol sayilari bir esigin ustunde.
   Bos bir tarama da "0 kirik" der ve hicbir sey olcmez.
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

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


def uretilen_yollar(kok: pathlib.Path) -> set[str]:
    """Sunulabilir yollarin kumesi.

    Dizin adresleri (`/gundem/`) ayrica ekleniyor: sunucu onlar icin
    `index.html` doner ve sayfalar da o bicimde baglaniyor.
    """
    var: set[str] = set()
    for p in kok.rglob("*"):
        if not p.is_file():
            continue
        r = "/" + p.relative_to(kok).as_posix()
        var.add(r)
        if r.endswith("/index.html"):
            var.add(r[: -len("index.html")])
    return var


def kirik_hedefler(kok: pathlib.Path) -> tuple[collections.Counter, dict, int]:
    """(kirik sayaci, ornek sayfa, taranan sayfa sayisi)."""
    var = uretilen_yollar(kok)
    kirik: collections.Counter = collections.Counter()
    ornek: dict[str, str] = {}
    sayfa = 0
    for p in kok.rglob("index.html"):
        sayfa += 1
        h = p.read_text(encoding="utf-8", errors="replace")
        for hedef in re.findall(r'(?:href|src)="(/[^"#?]*)', h):
            # `?v=...` surum etiketi dosya adinin parcasi degil.
            hedef = hedef.split("?")[0]
            if hedef in var:
                continue
            if (hedef.rstrip("/") + "/index.html") in var:
                continue
            kirik[hedef] += 1
            ornek.setdefault(hedef, str(p.relative_to(kok)))
    return kirik, ornek, sayfa


print("\nUretilen sitede kirik ic baglanti yok")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_kirik, _ornek, _sayfa = kirik_hedefler(_CIKTI)

# TARAMA DOLU MU. Bos bir tarama da "0 kirik" der; o cevap hicbir sey
# olcmez. Esikler olculen degerlerin (1820 sayfa) cok altinda --
# amac, taramanin CALISTIGINI dogrulamak, sayfa sayisini sabitlemek
# degil.
esit(_sayfa > 200, True, f"tarama dolu ({_sayfa} sayfa)")
esit(len(uretilen_yollar(_CIKTI)) > 500, True, "yol kumesi dolu")

if _kirik:
    print("\n  KIRIK HEDEFLER:")
    for _y, _n in _kirik.most_common(15):
        print(f"    {_n:5d} kez  {_y}   ornek: {_ornek[_y]}")
esit(sorted(_kirik)[:10], [], "kirik ic baglanti YOK")

print(f"\nTUM TESTLER GECTI ({_gecti})")
