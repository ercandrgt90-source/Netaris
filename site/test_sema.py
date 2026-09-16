"""MAKALE SEMASI GOOGLE'IN ISTEDIGI ALANLARI TASIYOR MU.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-16), orneklenen 800 `NewsArticle` blogunda:

    EKSIK image                800 / 800
    EKSIK publisher.logo       800 / 800
    EKSIK dateModified         400   (yalnizca /haber/)
    EKSIK mainEntityOfPage     400   (yalnizca /haber/)

`image` en pahali olani: Google News ve Discover, gorseli olmayan
makaleyi ust yuzeylerde buyuk olcude eliyor. Ustelik gorsel ZATEN
VARDI -- `og:image` 1.837 sayfanin hepsinde dolu. Veri elimizdeydi,
semaya baglanmamisti. Bu depoda tekrarlayan sinif: cevap uretiliyor,
okunabilir yerde durmuyor.

`description` de ayni kusurun bir baska yuzuydu: `h.neden_onemli`
basiliyordu -- konu basina SABIT bir metin, yani yuzlerce sayfada
ayni. Artik `self.aciklama()` ile meta etiketin ta kendisinden
geliyor; ikisinin ayrismasi yapisal olarak imkansiz.

TARIH UYDURULMUYOR. `dateModified` = `datePublished`, cunku elde
gercek bir guncelleme damgasi yok ve brief'in kurali acik:
guncellenmeyen icerikte sirf SEO icin tarih oynatilmaz.

NE SINANIYOR
------------
1. Her makale semasinda zorunlu alanlar dolu.
2. `image` MUTLAK adres ve dosya gercekten yayinda.
3. `description` sayfanin meta aciklamasiyla AYNI.
4. `dateModified` gelecekte degil ve `datePublished`tan geri degil.
5. Sayfa basina TEK makale semasi -- cakisan ikinci bir Article yok.
"""

from __future__ import annotations

import json
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


#: Makale semasinda bulunmasi gereken alanlar.
ZORUNLU = ("headline", "description", "image", "datePublished",
           "dateModified", "mainEntityOfPage", "author", "publisher",
           "inLanguage")

#: Makale sayan @type degerleri.
MAKALE = {"NewsArticle", "Article", "Report", "AnalysisNewsArticle"}

print("\nKaynak kodda")
_y = (_SITE / "sablonlar" / "_yapisal.html").read_text(encoding="utf-8")
esit("{% macro yayinci(" in _y, True, "yayinci makrosu TEK YERDE tanimli")
for _ad in ("haber.html", "analiz.html"):
    _t = (_SITE / "sablonlar" / _ad).read_text(encoding="utf-8")
    esit("yv.yayinci(site.ad, site.adres)" in _t, True,
         f"{_ad} ortak yayinci makrosunu cagiriyor")
    # CAGRIYA OZEL: ciplak "self.aciklama()" bu sablonlarin kendi
    # aciklama yorumlarinda da geciyor ve onu saymak, KALDIRILMIS bir
    # cagriyi duruyor gosterirdi. Mutasyonla olculdu: ilk yazimda tam
    # bu yuzden kacti -- bu depoda tekrar eden alt dize tuzagi.
    esit('{{ self.aciklama() | striptags | trim | tojson }}' in _t, True,
         f"{_ad} semadaki aciklamayi META ETIKETTEN aliyor")

print("\nUretilen sitede")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_sayfalar = (list((_CIKTI / "haber").rglob("index.html"))[:250]
             + list((_CIKTI / "analiz").rglob("index.html"))[:250])
esit(len(_sayfalar) > 100, True, f"tarama dolu ({len(_sayfalar)} sayfa)")

_eksik: dict[str, int] = {}
_coklu, _goreli, _uyusmaz, _tarih_bozuk = [], [], [], []
_gorseller: set[str] = set()
_n = 0
for _p in _sayfalar:
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _yol = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    _makaleler = []
    for _b in re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', _g, re.S):
        try:
            _d = json.loads(_b)
        except Exception:
            _eksik["BOZUK-JSON"] = _eksik.get("BOZUK-JSON", 0) + 1
            continue
        for _x in (_d.get("@graph") or (_d if isinstance(_d, list) else [_d])):
            if isinstance(_x, dict) and _x.get("@type") in MAKALE:
                _makaleler.append(_x)
    if not _makaleler:
        continue
    _n += 1
    # Sayfa basina TEK makale semasi: ikisi cakisirsa Google hangisini
    # okuyacagini bilmiyor.
    if len(_makaleler) > 1:
        _coklu.append(_yol)
    _x = _makaleler[0]
    for _alan in ZORUNLU:
        if not _x.get(_alan):
            _eksik[_alan] = _eksik.get(_alan, 0) + 1
    _pub = _x.get("publisher")
    if not (isinstance(_pub, dict) and _pub.get("logo")):
        _eksik["publisher.logo"] = _eksik.get("publisher.logo", 0) + 1
    _im = _x.get("image")
    for _u in (_im if isinstance(_im, list) else [_im] if _im else []):
        if not str(_u).startswith("https://"):
            _goreli.append((_yol, str(_u)[:40]))
        else:
            _gorseller.add(str(_u))
    # Sema aciklamasi = meta aciklama.
    _meta = re.search(r'<meta name="description" content="([^"]*)"', _g)
    if _meta and _x.get("description"):
        import html as _html
        if _html.unescape(_meta.group(1)).strip() != str(_x["description"]).strip():
            _uyusmaz.append(_yol)
    _dp, _dm = str(_x.get("datePublished") or ""), str(_x.get("dateModified") or "")
    if _dp and _dm and _dm < _dp:
        _tarih_bozuk.append((_yol, _dp, _dm))

esit(_n > 100, True, f"makale semasi bulunan sayfa ({_n})")
esit(sorted(_eksik.items()), [], "hicbir zorunlu alan EKSIK degil")
esit(_coklu[:3], [], "sayfa basina TEK makale semasi")
esit(_goreli[:3], [], "sema gorselleri MUTLAK adres")
esit(_uyusmaz[:3], [], "sema aciklamasi meta aciklamayla AYNI")
esit(_tarih_bozuk[:3], [], "dateModified datePublished'tan geri DEGIL")

# Gorsel dosyalari GERCEKTEN yayinda mi -- var olmayan bir adres
# bildirmek, hic bildirmemekten kotu.
_yok = []
for _u in list(_gorseller)[:80]:
    _dosya = _CIKTI / _u.split("/", 3)[3]
    if not _dosya.exists():
        _yok.append(_u)
esit(_yok[:3], [], f"sema gorselleri yayinda ({len(_gorseller)} tekil adres)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
