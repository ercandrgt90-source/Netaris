"""Sitemap ile sayfanin robots karari BIRBIRINI TUTMALI.

BU DOSYA NEDEN VAR
------------------
Iki ayri yer ayni karari veriyordu: hangi sayfanin `noindex`
tasiyacagini sablon, hangisinin haritaya gireceğini `yollar` listesi.
Ikisi ayrisinca harita "bunu dizine ekle", sayfa "ekleme" diyor ve
arama motoru celiskili iki isaret aliyor.

Bedeli somut: Google bunu "Submitted URL marked noindex" diye HATA
raporluyor ve her biri icin TARAMA BUTCESI harciyor -- guncel
sayfalarin tarandigi butceden.

Olculdu (2026-08-28): 276 eskimis analiz sayfasi haritadaydi ve
`noindex` tasiyordu -- haritanin %15'i. O zaman analiz tarafi ELLE
duzeltildi.

Olculdu (2026-09-15): ayni celiski `/ara/` sayfasinda HALA duruyordu.
Yani elle eslesmeyi korumak yetmedi; bir sonraki sayfa yine gozden
kacti. Karar artik TEK YERDE: sayfa kendi `noindex` etiketini
basiyorsa haritaya girmiyor.

NE SINANIYOR
------------
1. `haritaya_girer` sayfanin KENDI etiketini okuyor.
2. Bilinmeyen dosya haritadan atilmiyor: "bilmiyorum" ile "dizine
   ekleme" ayni sey degil.
3. Uretilen sitede celiski yok (cikti varsa).
"""

from __future__ import annotations

import pathlib
import re
import sys
import tempfile

_SITE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_SITE)]

import insa                                           # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


DIZINLENIR = ('<html><head><meta name="robots" content="index, follow">'
              "</head><body>x</body></html>")
NOINDEX = ('<html><head><meta name="robots" content="noindex, follow">'
           "</head><body>x</body></html>")


def _kur(kok: pathlib.Path, yol: str, govde: str) -> None:
    p = kok / yol.strip("/") / "index.html" if yol != "/" else kok / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(govde, encoding="utf-8")


print("\nKarar SAYFANIN KENDISINE soruluyor")
_d = tempfile.mkdtemp()
try:
    _kok = pathlib.Path(_d)
    _kur(_kok, "/haber/a/", DIZINLENIR)
    _kur(_kok, "/ara/", NOINDEX)
    _kur(_kok, "/", DIZINLENIR)
    esit(insa.haritaya_girer("/haber/a/", _kok), True,
         "dizinlenebilir sayfa haritaya girer")
    esit(insa.haritaya_girer("/ara/", _kok), False,
         "noindex sayfa haritaya GIRMEZ")
    esit(insa.haritaya_girer("/", _kok), True, "kok sayfa okunuyor")
    # BILMIYORUM ile DIZINE EKLEME ayni sey degil: sayfa henuz
    # yazilmamis olabilir ve onu sessizce haritadan dusurmek,
    # var olan bir sayfayi gorunmez yapardi.
    esit(insa.haritaya_girer("/boyle-bir-sey-yok/", _kok), True,
         "dosya yoksa haritadan ATILMIYOR")
finally:
    import shutil
    shutil.rmtree(_d, ignore_errors=True)


print("\nUretilen sitede CELISKI yok")
_CIKTI = insa.CIKTI
if (_CIKTI / "sitemap.xml").exists():
    _loc = set(re.findall(r"<loc>https?://[^/]+([^<]*)</loc>",
                          (_CIKTI / "sitemap.xml").read_text(encoding="utf-8")))
    esit(len(_loc) > 100, True, f"harita dolu ({len(_loc)} girdi)")
    _kirli = []
    for _p in _CIKTI.rglob("index.html"):
        _y = "/" + _p.parent.relative_to(_CIKTI).as_posix() + "/"
        _y = _y.replace("/./", "/")
        if _y in ("//", "/./"):
            _y = "/"
        if _y in _loc and insa.NOINDEX.search(
                _p.read_text(encoding="utf-8", errors="replace")):
            _kirli.append(_y)
    esit(_kirli[:5], [], "haritadaki hicbir sayfa noindex TASIMIYOR")
else:
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
