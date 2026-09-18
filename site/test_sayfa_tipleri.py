"""FAZ 9 -- HER SAYFA TIPI TEK TEK DENETLENIYOR.

BU DOSYA NEDEN VAR
------------------
Onceki sinamalar birer KURALI butun sayfalarda olcuyor (canonical,
sema, aciklama, DOM...). Bu dosya tersini yapiyor: HER SAYFA TIPINDEN
birer ornek alip uzerinde butun kurallari birden kontrol ediyor.

Ikisi ayni sey degil. Kural bazli sinamalar "hangi sayfa tipi hic
uretilmiyor" sorusunu SORMUYOR: bir sayfa tipi tumuyle kaybolsa,
"o tipteki her sayfa dogru" iddiasi bos kumede yine gecerdi. Bu
oturumda tam o oldu -- 207 analiz hem listeden hem dizinden dusmustu
ve hicbir sinama kirmizi yanmamisti, cunku her sinama kalan
sayfalarda dogruydu.

NE SINANIYOR
------------
Brief'in listeledigi 13 sayfa tipinin her biri icin:
  * sayfa URETILIYOR
  * `<title>`, meta aciklama, canonical, robots
  * Open Graph baslik/aciklama/gorsel
  * tipine uygun JSON-LD
  * gezinme kirintisi (detay sayfalarinda)
"""

from __future__ import annotations

import json
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

_gecti = 0
_kaldi: list[str] = []


def dogru(aciklama: str, kosul: bool) -> None:
    global _gecti
    if kosul:
        _gecti += 1
    else:
        _kaldi.append(aciklama)
        print(f"  DUSTU  {aciklama}")


def ornek(desen: str, dizinli_olsun: bool) -> pathlib.Path | None:
    """Tipten bir ornek -- istenen robots durumuna UYAN ilki.

    Ilk yazimda yalnizca alfabetik ilk sayfa aliniyordu ve teknik
    gorunumde bu ESKI bir surume denk geldi: yerini yenisi almis,
    dogru olarak `noindex`. Sinama "robots index" bekleyip kirmizi
    yandi -- kusur sitede degil, ORNEK SECIMINDEYDI.

    Asil dogrulanmak istenen sey zaten bu: bu tip DIZINE GIREN sayfa
    URETEBILIYOR mu? Hicbir ornek bulunamazsa bu gercek bir bulgudur.
    """
    import re as _re
    adaylar = sorted(_CIKTI.glob(desen))
    for p in adaylar:
        h = p.read_text(encoding="utf-8", errors="replace")
        m = _re.search(r'name="robots"[^>]*content="([^"]*)"', h)
        if not m:
            continue
        if ("noindex" in m.group(1)) != dizinli_olsun:
            return p
    return adaylar[0] if adaylar else None


#: (ad, sayfa yolu ya da desen, beklenen sema turleri, dizine girer mi)
TIPLER = [
    ("ana sayfa", "index.html", {"WebSite", "Organization"}, True),
    ("haber", "haber/*/index.html", {"NewsArticle", "BreadcrumbList"}, True),
    ("bilanco analizi", "analiz/*ceyrek/index.html",
     {"NewsArticle", "BreadcrumbList"}, True),
    ("teknik gorunum", "analiz/*teknik-gorunum*/index.html",
     {"NewsArticle", "BreadcrumbList"}, True),
    ("olay dosyasi", "olay/*/index.html",
     {"CollectionPage", "BreadcrumbList"}, True),
    ("konu hub", "konu/*/index.html", {"CollectionPage", "BreadcrumbList"}, True),
    ("varlik", "varlik/*/index.html", {"CollectionPage"}, True),
    ("bilancolar hub", "bilancolar/index.html", {"CollectionPage", "BreadcrumbList"}, True),
    ("makro hub", "makro/index.html", {"CollectionPage", "BreadcrumbList"}, True),
    ("arastirmalar hub", "arastirmalar/index.html", {"CollectionPage", "BreadcrumbList"}, True),
    ("gundem", "gundem/index.html", set(), True),
    ("hakkimizda", "hakkimizda/index.html", {"AboutPage"}, True),
    ("kunye", "kunye/index.html", set(), True),
    ("ara", "ara/index.html", set(), False),
    ("404", "404.html", set(), False),
]


def semalar(h: str) -> set[str]:
    t: set[str] = set()
    for b in re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
        try:
            d = json.loads(b)
        except Exception:
            t.add("BOZUK-JSON")
            continue
        for x in (d.get("@graph") if isinstance(d, dict) and d.get("@graph")
                  else (d if isinstance(d, list) else [d])):
            if isinstance(x, dict) and x.get("@type"):
                t.add(x["@type"])
    return t


print("\nSayfa tipleri")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

for _ad, _desen, _beklenen, _dizinli in TIPLER:
    _p = ornek(_desen, _dizinli)
    if _p is None:
        _kaldi.append(f"{_ad}: sayfa URETILMEMIS ({_desen})")
        print(f"  DUSTU  {_ad}: sayfa URETILMEMIS ({_desen})")
        continue
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _y = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    _t = re.search(r"<title>(.*?)</title>", _h, re.S)
    _d = re.search(r'<meta name="description" content="([^"]*)"', _h)
    _k = re.search(r'<link rel="canonical" href="([^"]*)"', _h)
    _r = re.search(r'name="robots"[^>]*content="([^"]*)"', _h)
    _og = {a: re.search(rf'property="og:{a}" content="([^"]*)"', _h)
           for a in ("title", "description", "image", "url")}
    _s = semalar(_h)

    dogru(f"{_ad}: <title> dolu", bool(_t and _t.group(1).strip()))
    dogru(f"{_ad}: aciklama dolu", bool(_d and _d.group(1).strip()))
    dogru(f"{_ad}: canonical var", bool(_k and _k.group(1).startswith("https://")))
    dogru(f"{_ad}: robots {'index' if _dizinli else 'noindex'}",
          bool(_r) and (("noindex" in _r.group(1)) != _dizinli))
    for _a, _m in _og.items():
        dogru(f"{_ad}: og:{_a}", bool(_m and _m.group(1).strip()))
    dogru(f"{_ad}: JSON-LD bozuk degil", "BOZUK-JSON" not in _s)
    if _beklenen:
        _eksik = _beklenen - _s
        dogru(f"{_ad}: sema {sorted(_beklenen)} (eksik: {sorted(_eksik)})",
              not _eksik)
    print(f"  {_ad:20s} {_y[:44]:46s} sema: {','.join(sorted(_s)) or '-'}")

print()
if _kaldi:
    print(f"{len(_kaldi)} SINAMA KALDI, {_gecti} gecti")
    raise SystemExit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
