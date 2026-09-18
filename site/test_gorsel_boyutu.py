# -*- coding: utf-8 -*-
"""TEMBEL YUKLENEN HER GORSEL BOYUTUNU YAZMALI.

BU DOSYA NEDEN VAR
------------------
Mobil denetiminde (2026-09-18) `gundem.html` icindeki kart gorseli
`loading="lazy"` tasiyor ama `width`/`height` tasimiyordu. Tembel
yuklenen bir gorsel, boyutu bilinmeden YER AYIRMAZ: fotograf indigi
anda altindaki icerigi asagi iter.

OLCEK DURUST OLSUN: bu tek sablondu ve sonucu kucuktu -- mobilde
`.haber-gorsel` zaten `aspect-ratio: 16/9` tasiyor ve alani koruyor
(`aspect-ratio: auto` yalnizca 561px USTUNDE devreye giriyor). Yani
bir kusurdan cok TUTARSIZLIKTI: sitedeki diger butun gorsel
sablonlari boyut yaziyordu, burasi tek istisnaydi.

Yine de kural olarak yaziliyor, cunku:
  * oznitelik, CSS daha inmeden tarayiciya orani verir,
  * yarin `aspect-ratio` tasimayan yeni bir kart eklendiginde koruma
    sessizce kaybolur -- tam olarak bu dosyanin kardeslerinde
    (test_mobil_gizleme, test_yatay_tasma) anlatilan kusur sinifi.

NE SINANIYOR
------------
1. Tarama bilinen girdide dogru cevap veriyor.
2. Sablonlardaki her `loading="lazy"` gorseli `width` ve `height`
   tasiyor.
3. Uretilen ciktida da ayni sey gecerli.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_SABLON = _SITE / "sablonlar"
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


#: GEREKCELI ISTISNA -- sinif: neden boyut YAZILAMAZ.
#:
#: Kural "her tembel gorsel boyutunu yazsin" ama istisnasi olmali:
#: bazi gorsellerin ORANI her ornekte farklidir ve sabit bir deger
#: yazmak tarayiciya YANLIS oran vermek olur -- boyutu hic yazmamaktan
#: kotudur, cunku yanlis yer ayirir ve gorsel inince yine kayar.
#:
#: Buraya bir sinif eklemeden once sorulacak soru: "bu gorselin orani
#: SABIT mi?" Sabitse istisna degil, boyut yazilmasi gereken bir
#: gorseldir.
ISTISNA = {
    "amblem-gorsel":
        "gercek sirket logolari (`site/amblem.py`). Her logonun kendi "
        "orani var; CSS bilerek `width: auto; height: auto; object-fit: "
        "contain` kullaniyor ve olcuyu KAP veriyor (`flex: 1 1 auto`, "
        "`max-width: min(86%, 460px)`, kart icinde `max-height: 40%`). "
        "Sabit bir deger yazmak yanlis oran bildirmek olurdu. "
        "DAHA IYISI MUMKUN ama pahali: her dosyanin gercek boyutunu "
        "kurulum aninda okuyup yazmak (PNG basligi, SVG viewBox). "
        "Kazanc kucuk -- alani zaten kap belirliyor.",
}


def boyutsuz_tembeller(html: str) -> list[str]:
    """`loading="lazy"` tasiyip `width`/`height` tasimayan <img>'ler.

    ISTISNA listesindeki siniflar atlanir.
    """
    eksik = []
    for m in re.finditer(r"<img\b([^>]*)>", html, re.S):
        oz = m.group(1)
        if "lazy" not in oz:
            continue
        if re.search(r"\bwidth\s*=", oz) and re.search(r"\bheight\s*=", oz):
            continue
        sinif = re.search(r'class="([^"]*)"', oz)
        if sinif and any(s in ISTISNA for s in sinif.group(1).split()):
            continue
        eksik.append(" ".join(m.group(0).split())[:84])
    return eksik


print("\nTarama gercekten calisiyor mu")
_D = (
    '<img src="a.jpg" loading="lazy">'                       # eksik
    '<img src="b.jpg" loading="lazy" width="4" height="3">'  # tam
    '<img src="c.jpg">'                                      # tembel degil
    '<img src="d.jpg" loading="lazy"\n     width="9">'       # yalniz genislik
)
_b = boyutsuz_tembeller(_D)
esit(len(_b), 2, "yalnizca eksik olanlari sayiyor (a ve d)")
esit(any("a.jpg" in x for x in _b), True, "boyutsuz tembeli yakaliyor")
esit(any("b.jpg" in x for x in _b), False, "boyutlu tembeli saymiyor")
esit(any("c.jpg" in x for x in _b), False, "tembel olmayani saymiyor")
esit(any("d.jpg" in x for x in _b), True,
     "YALNIZCA genislik yeterli degil (satira bolunmus olsa da)")

# ISTISNA MEKANIZMASI DAR MI.
#
# Olculdu (mutasyon C): istisna kontrolunu `if sinif:` haline
# getirmek -- yani SINIFI OLAN her gorseli muaf tutmak -- sinamayi
# kirmizi yapmiyordu. Cunku sinifli tembel gorsellerin hepsinde zaten
# boyut vardi; kural etkisizlesiyor ama kimse gormuyordu.
#
# Asagidaki iki iddia mekanizmayi DOGRUDAN sinar: defterdeki sinif
# atlanmali, defterde OLMAYAN sinif atlanmamali.
_ist = next(iter(ISTISNA))
_M = (f'<img class="{_ist}" src="x.svg" loading="lazy">'
      '<img class="baska-bir-sinif" src="y.jpg" loading="lazy">')
_mb = boyutsuz_tembeller(_M)
esit(any("x.svg" in x for x in _mb), False,
     f"defterdeki sinif (`{_ist}`) atlaniyor")
esit(any("y.jpg" in x for x in _mb), True,
     "defterde OLMAYAN sinif atlanmiyor (istisna genisletilemez)")

print("\nSablonlarda")
_toplam = 0
_eksik: list[tuple[str, str]] = []
for _f in sorted(_SABLON.glob("*.html")):
    _h = _f.read_text(encoding="utf-8", errors="replace")
    _toplam += len(re.findall(r"<img\b", _h))
    for _e in boyutsuz_tembeller(_h):
        _eksik.append((_f.name, _e))
esit(_toplam > 5, True, f"sablonlarda gorsel bulundu ({_toplam})")
if _eksik:
    print("\n  BOYUTSUZ TEMBEL GORSEL:")
    for _ad, _e in _eksik:
        print(f"    {_ad}: {_e}")
esit(len(_eksik), 0, "her tembel gorsel boyutunu yaziyor")

print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_c_eksik: dict[str, int] = {}
_c_toplam = 0
for _p in _CIKTI.rglob("index.html"):
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _c_toplam += len(re.findall(r"<img\b", _h))
    for _e in boyutsuz_tembeller(_h):
        _c_eksik[_e] = _c_eksik.get(_e, 0) + 1
esit(_c_toplam > 100, True, f"ciktida gorsel bulundu ({_c_toplam})")
if _c_eksik:
    print("\n  CIKTIDAKI BOYUTSUZ TEMBEL GORSELLER:")
    for _e, _n in sorted(_c_eksik.items(), key=lambda x: -x[1])[:6]:
        print(f"    {_n:>4}x  {_e}")
esit(sum(_c_eksik.values()), 0, "ciktidaki her tembel gorsel boyutunu yaziyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
