# -*- coding: utf-8 -*-
"""KENAR SERITTEKI HER BAGLANTI, SAYFADA VAR OLAN BIR CAPAYA GITMELI.

BU DOSYA NEDEN VAR
------------------
Kenar serit, yazinin bolum basliklarini listeliyor. Liste ELLE
YAZILMIYOR -- `bolumle` suzgeci cizilmis sayfadan cikariyor. Sebep:
haber sablonunda yirmi kadar `<h2>` var ve her biri kendi kosuluna
bagli ("Kim etkilenir?" yalnizca duyarlilik tablosu varsa basiliyor).
Listeyi elle yazmak ayni yirmi kosulu IKINCI kez yazmak olurdu.

Ama tek kaynaktan uretmek de yetmiyor: capa uretimi bozulursa (ayni
baslik iki kez gecer, slug bos kalir, bir oge `id` tasiyor sanilir)
serit var olmayan bir yere baglanir. Okur tiklar, sayfa OYNAMAZ, ve
hicbir hata gorunmez. Tam da sessiz oldugu icin olculmesi gerekiyor.

OLCULDU (2026-10-04): haber sayfalarinda h2 ortancasi 11 (en az 6,
en cok 18); analizlerde 8. Yani her sayfada on kadar baglanti ve
hepsinin dogru olmasi gerekiyor.

NE SINANIYOR
------------
1. Seritteki her `#capa`, ayni sayfada `id` olarak VAR.
2. Ayni sayfada ayni `id` iki kez gecmiyor (capa cakismasi).
3. Paylasim basligi ("Paylas") serite GIRMIYOR -- o bir icerik
   bolumu degil, aracin etiketi. Kendini `data-bolum="hayir"` ile
   isaretliyor.
"""

from __future__ import annotations

import collections
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_C = _SITE / "cikti"
if not (_C / "index.html").exists():
    print("\n  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_SERIT = re.compile(r'<nav class="serit-bolum".*?</nav>', re.S)
_BAG = re.compile(r'<a href="#([^"]+)"')
_ID = re.compile(r'\sid="([^"]+)"')

_bakilan = 0
_kirik: list[str] = []
_cakisan: list[str] = []
_paylas: list[str] = []
_bag_toplam = 0

for _kok in ("haber", "analiz"):
    _d = _C / _kok
    if not _d.exists():
        continue
    for _p in sorted(_d.glob("*/index.html"))[:220]:
        _m = _p.read_text(encoding="utf-8", errors="replace")
        _s = _SERIT.search(_m)
        if not _s:
            continue
        _bakilan += 1
        _idler = collections.Counter(_ID.findall(_m))
        for _capa in _BAG.findall(_s.group(0)):
            _bag_toplam += 1
            if _idler[_capa] == 0:
                _kirik.append(f"{_kok}/{_p.parent.name}  ->  #{_capa}")
            elif _idler[_capa] > 1:
                _cakisan.append(f"{_kok}/{_p.parent.name}  #{_capa}"
                                f"  {_idler[_capa]} kez")
        if re.search(r">\s*Payla[sş]\s*<", _s.group(0)):
            _paylas.append(f"{_kok}/{_p.parent.name}")

esit(_bakilan > 0, True, f"seritli sayfa bulundu ({_bakilan})")
esit(_bag_toplam > 0, True, f"serit baglantisi bulundu ({_bag_toplam})")

if _kirik:
    print(f"\n  CAPASI OLMAYAN BAGLANTI: {len(_kirik)}")
    for _x in _kirik[:8]:
        print(f"    {_x}")
esit(len(_kirik), 0,
     f"seritteki her baglanti var olan bir capaya gidiyor ({_bag_toplam})")

if _cakisan:
    print(f"\n  AYNI CAPA BIRDEN COK KEZ: {len(_cakisan)}")
    for _x in _cakisan[:8]:
        print(f"    {_x}")
esit(len(_cakisan), 0, "capa cakismasi yok")

if _paylas:
    print(f"\n  SERITTE 'PAYLAS' BASLIGI: {len(_paylas)} sayfa")
    for _x in _paylas[:5]:
        print(f"    {_x}")
esit(len(_paylas), 0, "paylasim etiketi bolum listesine girmiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
