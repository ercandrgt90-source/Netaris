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


# ---------------------------------------------------------------------
# LASTMOD ICERIKTEN TURETILIYOR, KURULUM TARIHINDEN DEGIL.
#
# Google `lastmod`u yalnizca TUTARLI DOGRU oldugunda kullaniyor;
# guvenilmez bulursa alani bastan yok sayiyor. Yani yanlis bir tarih,
# hic tarih vermemekten KOTU.
#
# En sik yapilan yanlis, kapsami "duzeltmek" icin her kuruluma bugunu
# yazmak. Bu site gunde birkac kez kuruluyor; o zaman 1600 sayfa her
# gun degismis gorunur ve alan ise yaramaz hale gelir. Bu bolumun asil
# isi o "duzeltmeyi" engellemek.
#
# Olculdu (2026-09-16): lastmod'u olmayan adres 103'ten 34'e indi.
# Kalanlar tarihi GERCEKTEN bilinmeyenler: yasal/statik sayfalar ve
# henuz haber baglanmamis 26 varlik sayfasi. "Bilmiyorum" ile "bugun
# degisti" ayni sey degil.
print("\nlastmod dogru mu")

import datetime as _dt                                   # noqa: E402

# Islevin kendisi: yalnizca BILINEN ve GECERLI tarihi yaziyor.
_t: dict = {}
insa.lastmod_kur(_t, "/a/", "2026-09-15")
esit(_t.get("/a/"), "2026-09-15", "gecerli tarih yaziliyor")
insa.lastmod_kur(_t, "/b/", "")
esit("/b/" in _t, False, "bos tarih YAZILMIYOR")
insa.lastmod_kur(_t, "/c/", None)
esit("/c/" in _t, False, "None YAZILMIYOR")
insa.lastmod_kur(_t, "/d/", "bilinmiyor")
esit("/d/" in _t, False, "bicimsiz deger YAZILMIYOR")
insa.lastmod_kur(_t, "/e/", "2026-09-15T14:22:00+00:00")
esit(_t.get("/e/"), "2026-09-15", "zaman damgasi gune kirpiliyor")

_HRT = _SITE / "cikti" / "sitemap.xml"
if not _HRT.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
else:
    _s = _HRT.read_text(encoding="utf-8")
    _girdi = re.findall(r"<url>(.*?)</url>", _s, re.S)
    _tarihli = [x for x in _girdi if "<lastmod>" in x]
    esit(len(_girdi) > 500, True, f"harita dolu ({len(_girdi)} adres)")
    esit(len(_tarihli) * 100 // len(_girdi) >= 95, True,
         f"adreslerin >=%95'inde lastmod var "
         f"({len(_tarihli)}/{len(_girdi)})")

    _degerler = re.findall(r"<lastmod>([^<]+)</lastmod>", _s)
    _bozuk = [d for d in _degerler
              if not re.match(r"^\d{4}-\d{2}-\d{2}$", d)]
    esit(_bozuk[:5], [], "her lastmod tam tarih bicimde")

    _bugun = _dt.date.today().isoformat()
    _gelecek = [d for d in _degerler if d > _bugun]
    esit(_gelecek[:5], [], "GELECEK tarihli lastmod yok")

    # ASIL KORUMA: hepsi bugun olamaz. Olculdu: 1626 tarihten 137'si
    # bugun. Oran %50'yi asiyorsa deger icerikten degil kurulumdan
    # geliyordur.
    _bugunku = sum(1 for d in _degerler if d == _bugun)
    esit(_bugunku * 100 // len(_degerler) < 50, True,
         f"lastmod KURULUM TARIHI degil, icerikten "
         f"({_bugunku}/{len(_degerler)} bugun)")

    # Hub'lar tarih TASIYOR: en cok taranan sayfalar onlar.
    for _h in ("/", "/gundem/", "/makro/", "/bilancolar/"):
        _m = re.search(r"<loc>https://netaris\.net" + re.escape(_h)
                       + r"</loc>\s*<lastmod>", _s)
        esit(bool(_m), True, f"{_h} lastmod tasiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
