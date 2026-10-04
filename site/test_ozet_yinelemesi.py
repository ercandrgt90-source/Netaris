# -*- coding: utf-8 -*-
"""UST OZET CUMLESI GOVDEYI TEKRARLAMAMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-10-04, uretilen 772 analiz sayfasi):

    ozet cumlesi = Ozet bolumunun ilk paragrafi
      TAM AYNI    120
      BASI AYNI   259        -> 379 sayfa, yani %49
      farkli       86
      biri yok    307

Okur ayni cumleyi ~200 piksel arayla iki kez goruyordu ve ILKI
KIRPIKTI (772 ozetin 306'si "..." ile bitiyor). Yani tekrar, ustune
bir de yarim cumleyle yapiliyordu.

Kusur GORUNMEZ degildi -- sayfaya bakan herkes gorebilirdi. Ama
hicbir sey olcmedigi icin kimse SAYMADI, ve sayilmayan sey
duzeltilmez. Bu dosya sayiyor.

NE SINANIYOR
------------
1. Olcu fonksiyonu kendi kendini sinar (bilinen girdiler).
2. Uretilen ciktida ust ozet ile govde ozeti AYNI OLAN sayfa yok.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


import insa  # noqa: E402

_f = insa.ozet_govdede_tekrarlaniyor
_GOVDE = '<h2 id="ozet">Özet</h2>\n<p>Hasılat büyürken kâr düştü ve net sonuç zarara geçti.</p>'

print("\nOlcu fonksiyonu")
esit(_f("Hasılat büyürken kâr düştü…", _GOVDE), True, "kirpik ust, tam govde -> tekrar")
esit(_f("Hasılat büyürken kâr düştü ve net sonuç zarara geçti.", _GOVDE), True,
     "birebir ayni -> tekrar")
esit(_f("Dolar endeksi yükseldi", _GOVDE), False, "farkli cumle -> tekrar DEGIL")
esit(_f("Hasılat büyürken kâr düştü…", '<h2 id="giris">Giriş</h2>\n<p>x</p>'), False,
     "govdede Ozet bolumu yoksa -> tekrar DEGIL")
esit(_f("", _GOVDE), False, "bos ozet -> tekrar DEGIL")
esit(_f("Hasılat", ""), False, "bos govde -> tekrar DEGIL")
# Kisa ve rastlanti eseri benzeyen acilis elenmemeli.
esit(_f("Bu", _GOVDE), False, "cok kisa ozet tekrar SAYILMIYOR")

print("\nUretilen cikti")
_C = _SITE / "cikti" / "analiz"
if not _C.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_sade = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip().strip(".… ").lower()
_yineli = []
_sayfa = 0
for _p in sorted(_C.glob("*/index.html")):
    _m = _p.read_text(encoding="utf-8", errors="replace")
    _sayfa += 1
    _o = re.search(r'<p class="ozet-cumle">(.*?)</p>', _m, re.S)
    _g = re.search(r'<h2 id="ozet"[^>]*>.*?</h2>\s*<p>(.*?)</p>', _m, re.S)
    if not _o or not _g:
        continue
    _a, _b = _sade(_o.group(1)), _sade(_g.group(1))
    if not _a or not _b:
        continue
    _k = min(len(_a), len(_b), 60)
    if _a == _b or _a[:_k] == _b[:_k]:
        _yineli.append(_p.parent.name)

esit(_sayfa > 0, True, f"analiz sayfalari tarandi ({_sayfa})")
if _yineli:
    print(f"\n  AYNI OZETI IKI KEZ BASAN SAYFA: {len(_yineli)}")
    for _y in _yineli[:8]:
        print(f"    {_y}")
# Liste DEGIL SAYI karsilastiriliyor: 379 slug basmak CI gunlugunu
# okunamaz hale getiriyordu. Ornekler yukarida zaten yazildi.
esit(len(_yineli), 0, f"hicbir sayfa ozeti iki kez basmiyor ({_sayfa} sayfa)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
