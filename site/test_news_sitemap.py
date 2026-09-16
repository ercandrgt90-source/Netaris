"""GOOGLE NEWS HARITASI -- yalnizca TAZE ve yalnizca DIZINE GIREN.

BU DOSYA NEDEN VAR
------------------
Normal site haritasi butun sayfalari tasiyor ve Google onu kendi
temposunda geziyor. Haber icin o tempo gec: bir gelisme yayimdan
saatler sonra taranirsa haber olmaktan cikiyor.

Google'in kurali dar: yalnizca SON IKI GUNUN haberleri, en fazla
1.000 adres. Olculdu (2026-09-16): son iki gunde 247 haber -- sinirin
cok altinda.

BU DOSYANIN ASIL ISI PENCEREYI KORUMAK. En kolay ve en zararli
"iyilestirme", kapsami buyutmek icin eski haberleri de haritaya
koymak: Google acikca istemiyor ve guvenilmez buldugu bir haber
haritasini bastan yok sayabiliyor.

NE SINANIYOR
------------
1. Pencere: iki gunden eski haber GIRMIYOR, taze olan giriyor.
2. Ust sinir 1.000.
3. Yalnizca DIZINE GIREN sayfalar -- `noindex` bir sayfayi haber
   haritasina koymak Google'a birbirinin tersini soylemektir.
4. Yayin tarihi sayfanin SEMASIYLA ayni ve her adres BIR KEZ.
5. `robots.txt` iki haritayi da bildiriyor.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path[:0] = [str(_SITE)]

import insa  # noqa: E402

_AD = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_NEWS = "{http://www.google.com/schemas/sitemap-news/0.9}"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("\nPencere dogru")
# Sabit bir "bugun" ile olculuyor: gercek tarihe bagli bir sinama,
# yarin baska sey olcerdi.
_girdi = [
    ("2026-09-16", "Bugunku haber", "/haber/a/"),
    ("2026-09-15", "Dunku haber", "/haber/b/"),
    ("2026-09-14", "Iki gun oncesi -- SINIRDA", "/haber/c/"),
    ("2026-09-13", "Uc gun oncesi -- DISARIDA", "/haber/d/"),
    ("2026-08-01", "Cok eski", "/haber/e/"),
]
_x = insa.news_sitemap_uret(_girdi, bugun="2026-09-16")
_k = ET.fromstring(_x)
_yollar = [u.find(_AD + "loc").text for u in _k.findall(_AD + "url")]
esit(len(_yollar), 3, "iki gunluk pencere: 5 haberin 3'u giriyor")
esit(any("/haber/d/" in y for y in _yollar), False,
     "uc gun onceki haber GIRMIYOR")
esit(any("/haber/e/" in y for y in _yollar), False, "cok eski haber GIRMIYOR")
esit(_yollar[0].endswith("/haber/a/"), True, "en yeni BASTA")

# Ust sinir: Google 1.000 diyor.
_cok = [("2026-09-16", f"Haber {i}", f"/haber/{i}/") for i in range(1500)]
_x2 = insa.news_sitemap_uret(_cok, bugun="2026-09-16")
esit(len(ET.fromstring(_x2).findall(_AD + "url")), insa.NEWS_SINIR,
     f"ust sinir {insa.NEWS_SINIR} adres")
esit(insa.NEWS_GUN <= 2, True, "pencere en fazla 2 gun (Google'in kurali)")

print("\nUretilen dosyada")
_d = _CIKTI / "news-sitemap.xml"
if not _d.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_kok = ET.fromstring(_d.read_text(encoding="utf-8"))
_url = _kok.findall(_AD + "url")
esit(len(_url) > 0, True, f"harita dolu ({len(_url)} haber)")
esit(len(_url) <= insa.NEWS_SINIR, True, "sinir asilmiyor")
# TEKIL ADRES. Olculdu: 247 girdi / 243 tekil adres -- ayni yol
# iki kez listeleniyordu. `sitemap_uret` bu dersi ogrenmisti
# ("her adres BIR KEZ"), haber haritasi ogrenmemisti.
_loclar = [u.find(_AD + "loc").text for u in _url]
esit(len(_loclar), len(set(_loclar)), "her adres BIR KEZ")

_eksik, _noindex, _baslik_uyusmaz = [], [], []
for _u in _url:
    _loc = _u.find(_AD + "loc").text
    _n = _u.find(_NEWS + "news")
    if _n is None or _n.find(_NEWS + "publication_date") is None \
            or _n.find(_NEWS + "title") is None:
        _eksik.append(_loc)
        continue
    _yol = _loc.replace("https://netaris.net", "")
    _p = _CIKTI / _yol.strip("/") / "index.html"
    if not _p.exists():
        _eksik.append(_loc)
        continue
    _h = _p.read_text(encoding="utf-8", errors="replace")
    if re.search(r'name="robots"[^>]*content="[^"]*noindex', _h, re.I):
        _noindex.append(_yol)
    # TARIH SAYFANIN SEMASIYLA AYNI OLMALI.
    #
    # Ilk yazimda sayfadaki ilk `<time datetime=...>` ile
    # karsilastiriyordum ve %36 "uyusmuyor" cikti. OLCUM YANLISTI:
    # yakalanan etiket sayfanin kendi tarihi degil, ILGILI ICERIK
    # listesindeki bir tarihti. Dogru karsilastirma semadaki
    # `datePublished` -- Google'in okudugu deger de odur.
    _sema = None
    for _b in re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', _h, re.S):
        try:
            _d = json.loads(_b)
        except Exception:
            continue
        for _o in (_d if isinstance(_d, list) else [_d]):
            if isinstance(_o, dict) and _o.get("@type") == "NewsArticle":
                _sema = _o
    if _sema and _sema.get("datePublished") != _n.find(
            _NEWS + "publication_date").text:
        _baslik_uyusmaz.append(
            (_yol[:44], _n.find(_NEWS + "publication_date").text,
             _sema.get("datePublished")))

esit(_eksik[:3], [], "her girdide yayin tarihi, baslik ve GERCEK sayfa var")
esit(_noindex[:3], [], "haber haritasinda `noindex` sayfa YOK")
esit(_baslik_uyusmaz[:3], [], "yayin tarihi sayfanin SEMASIYLA ayni")

print("\nrobots.txt")
_r = (_CIKTI / "robots.txt").read_text(encoding="utf-8")
esit("Sitemap: https://netaris.net/sitemap.xml" in _r, True, "ana harita bildirilmis")
esit("Sitemap: https://netaris.net/news-sitemap.xml" in _r, True,
     "haber haritasi bildirilmis")

print(f"\nTUM TESTLER GECTI ({_gecti})")
