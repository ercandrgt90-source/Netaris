"""MARKA ISARETI ARAMA SONUCUNDA GORUNEBILIR MI.

BU DOSYA NEDEN VAR
------------------
Marka isareti `temel.html` icinde bir `data:image/svg+xml` URI olarak
yasiyordu. Tarayici sekmesinde calisiyordu -- yani gozle bakinca her
sey yolunda goruyordu -- ama arama sonucunda HIC cikamazdi.

Google'in favicon sartlari ucunu birden dusuruyordu
(developers.google.com/search/docs/appearance/favicon-in-search):

  * "Google Search supports the following favicon file formats: BMP,
    GIF, ICO, PNG, JPEG, PPM, and TIFF."   -> SVG DESTEKLENMIYOR
  * "The favicon URL must be stable"       -> `data:` URI adres degil
  * "Googlebot-Image must be able to crawl the favicon file"
                                           -> `data:` URI taranamaz

Ayni sekilde `publisher` yalnizca bir ISIMDI; Google'in logo sartlari
(structured-data/logo) marka logosu icin `Organization.logo` istiyor:

  * "The image must be 112x112px, at minimum."
  * "The image URL must be crawlable and indexable."

Kusur SESSIZ: hicbir sey bozulmuyor, kurulum yesil, sayfa dogru
gorunuyor. Yalnizca arama sonucunda marka yok.

NE SINANIYOR
------------
1. Favicon GERCEK DOSYA -- `data:` URI degil, ve dosya uretiliyor.
2. Bicim PNG (SVG kabul edilmiyor), KARE, 48'den buyuk.
3. `Organization.logo` var, en az 112x112, MUTLAK adres, dosya var.
4. TEK KURULUS: `WebSite.publisher` ile `Organization` ayni `@id`.
5. `robots.txt` isaret dosyalarini engellemiyor.
"""

from __future__ import annotations

import json
import pathlib
import re
import struct
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


#: Google'in kabul ettigi favicon bicimleri. SVG BILEREK YOK.
KABUL = (".bmp", ".gif", ".ico", ".png", ".jpg", ".jpeg", ".ppm", ".tif",
         ".tiff")

#: Google'in logo icin istedigi en kucuk kenar.
LOGO_EN_AZ = 112

#: Favicon icin onerilen alt sinir ("larger than 48x48px").
FAVICON_EN_AZ = 48


def png_olcu(p: pathlib.Path) -> tuple[int, int]:
    """PNG genislik/yukseklik -- IHDR'den, kutuphanesiz.

    Imza da dogrulaniyor: uzantisi .png olan ama PNG OLMAYAN bir dosya
    Google tarafindan okunamaz ve sinama "var" deyip gecerdi.
    """
    ham = p.read_bytes()
    if ham[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{p.name} PNG imzasi tasimiyor")
    if ham[12:16] != b"IHDR":
        raise ValueError(f"{p.name} IHDR ile baslamiyor")
    return struct.unpack(">II", ham[16:24])


print("\nKaynak kodda: `data:` URI kalmadi")
_t = (_SITE / "sablonlar" / "temel.html").read_text(encoding="utf-8")
esit(re.search(r'rel="icon"[^>]*href="data:', _t, re.S) is None, True,
     "favicon `data:` URI DEGIL (taranamaz, Google okuyamaz)")

print("\nUretilen sitede")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_h = (_CIKTI / "index.html").read_text(encoding="utf-8")

# `re.S` SART: etiketler satira boluniyor ve `[^>]*` satir sonunu
# gecmiyor. Ilk yazimda bu yuzden "baglanti yok" sanildi -- olcum
# hatasi, kusur degil.
_ikonlar = re.findall(r'<link[^>]*rel="(icon|apple-touch-icon)"[^>]*'
                      r'href="([^"]+)"[^>]*>', _h, re.S)
esit(len(_ikonlar) >= 2, True, f"ikon baglantisi var ({len(_ikonlar)})")

_favicon = [y for t, y in _ikonlar if t == "icon"]
esit(len(_favicon), 1, "tek bir `rel=icon` (Google tek isaret okuyor)")

for _tur, _yol in _ikonlar:
    esit(_yol.startswith("/"), True, f"{_tur} koke gore mutlak yol ({_yol})")
    esit(pathlib.Path(_yol).suffix.lower() in KABUL, True,
         f"{_tur} bicimi Google'in kabul ettiklerinden ({_yol})")
    _d = _CIKTI / _yol.lstrip("/")
    esit(_d.exists(), True, f"{_tur} dosyasi YAYINDA ({_yol})")
    _g, _y = png_olcu(_d)
    esit(_g == _y, True, f"{_tur} KARE ({_g}x{_y})")
    esit(_g >= FAVICON_EN_AZ, True, f"{_tur} {FAVICON_EN_AZ}px'ten buyuk ({_g})")

print("\nOrganization logosu")
_bloklar = [json.loads(b) for b in re.findall(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>', _h, re.S)]
_dugumler = [x for b in _bloklar for x in (b.get("@graph") or [b])]
_kurulus = [x for x in _dugumler if x.get("@type") == "Organization"]
_site = [x for x in _dugumler if x.get("@type") == "WebSite"]
esit(len(_kurulus), 1, "ana sayfada TEK Organization")
esit(len(_site), 1, "ana sayfada TEK WebSite")

_k = _kurulus[0]
esit(bool(_k.get("name")), True, "Organization.name var")
esit(bool(_k.get("url")), True, "Organization.url var")
_logo = _k.get("logo")
esit(isinstance(_logo, dict) and bool(_logo.get("url")), True,
     "Organization.logo var")
_lu = _logo["url"]
esit(_lu.startswith("https://"), True, f"logo MUTLAK adres ({_lu})")
esit(pathlib.Path(_lu).suffix.lower() in KABUL, True, "logo bicimi kabul ediliyor")
_lp = _CIKTI / _lu.split("/", 3)[3]
esit(_lp.exists(), True, "logo dosyasi YAYINDA")
_lg, _ly = png_olcu(_lp)
esit(_lg >= LOGO_EN_AZ and _ly >= LOGO_EN_AZ, True,
     f"logo en az {LOGO_EN_AZ}x{LOGO_EN_AZ} ({_lg}x{_ly})")

# TEK KURULUS. `publisher`i ayri bir Organization olarak yazmak,
# Google'a birbirinin ayni IKI kurulus bildirmek demekti -- bu depoda
# tekrar eden "ayni seyi iki yerde soylemek" kusurunun yapisal veri
# surumu.
esit(_site[0].get("publisher"), {"@id": _k["@id"]},
     "WebSite.publisher AYNI kurulusa isaret ediyor")

# KOKTEKI /favicon.ico -- YEDEK YOL.
# Asil yol ana sayfadaki `<link rel="icon">`; Google onu okuyor. Ama
# tarayicilar ve bazi kaziyicilar etiketi okumadan once kokteki
# `/favicon.ico` adresini yokluyor ve olculdu (2026-09-16): orasi 404
# donuyordu. Etiketin YERINI ALMIYOR, yaninda duruyor.
_ico = _CIKTI / "favicon.ico"
esit(_ico.exists(), True, "/favicon.ico cikti KOKUNDE")
_ib = _ico.read_bytes()
esit(struct.unpack("<HH", _ib[:4]), (0, 1), "gecerli ICO basligi")
_girdi = struct.unpack("<H", _ib[4:6])[0]
esit(_girdi >= 1, True, f"ICO en az bir olcu tasiyor ({_girdi})")
# Govdelerin GERCEKTEN goruntu olmasi sinaniyor: bos ya da bozuk bir
# govde tasiyan ICO, "dosya var" diyen bir sinamayi gecerdi.
for _i in range(_girdi):
    _ig, _iy, _, _, _, _, _iboy, _ikay = struct.unpack(
        "<BBBBHHII", _ib[6 + _i * 16:22 + _i * 16])
    esit(_ib[_ikay:_ikay + 8] == b"\x89PNG\r\n\x1a\n", True,
         f"ICO {_ig}x{_iy} govdesi gercek PNG")
    esit(_ig >= FAVICON_EN_AZ, True, f"ICO olcusu {FAVICON_EN_AZ}+ ({_ig})")

print("\nPaylasim karti")
# Olculdu (2026-09-16): 106 sayfanin hic `og:image`i yoktu ve
# paylasildiklarinda onizleme BOS kutuydu. Ana sayfa ise
# `haberler[0].foto`ya dusuyordu -- "netaris.net" paylasan biri
# markayi degil o anki en yeni haber fotografini goruyordu.
_KART = "/statik/marka/netaris-kart.png"
_kart_yolu = _CIKTI / _KART.lstrip("/")
esit(_kart_yolu.exists(), True, "marka karti YAYINDA")
_kg, _ky = png_olcu(_kart_yolu)
esit((_kg, _ky), (1200, 630), f"kart Open Graph olcusunde ({_kg}x{_ky})")

_ana_og = re.search(r'property="og:image"[^>]*content="([^"]*)"', _h)
esit(bool(_ana_og) and _ana_og.group(1).endswith(_KART), True,
     "ANA SAYFA markayi paylasiyor (haber fotografini degil)")

# HER SAYFADA gorsel var mi -- ve bildirilen tur DOGRU mu. Yanlis tur
# bildirmek, bazi kaziyicilarin gorseli hic basmamasina yol aciyor.
_gorselsiz = []
_tur_yanlis = []
_n = 0
for _p in _CIKTI.rglob("index.html"):
    _n += 1
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _mi = re.search(r'property="og:image"[^>]*content="([^"]*)"', _g)
    if not _mi:
        _gorselsiz.append(str(_p.relative_to(_CIKTI)))
        continue
    _mt = re.search(r'property="og:image:type"[^>]*content="([^"]*)"', _g)
    _bekle = "image/png" if _mi.group(1).endswith(".png") else "image/jpeg"
    if _mt and _mt.group(1) != _bekle:
        _tur_yanlis.append((str(_p.relative_to(_CIKTI)), _mt.group(1), _bekle))
esit(_n > 200, True, f"tarama dolu ({_n} sayfa)")
esit(_gorselsiz[:5], [], "og:image'i OLMAYAN sayfa yok (onceden 106)")
esit(_tur_yanlis[:5], [], "og:image:type uzantiyla UYUSUYOR")

print("\nTaranabilir")
_r = (_CIKTI / "robots.txt").read_text(encoding="utf-8")
_yasak = [s.split(":", 1)[1].strip() for s in _r.splitlines()
          if s.lower().startswith("disallow:") and s.split(":", 1)[1].strip()]
_engelli = [y for y in _yasak
            if _lu.split("/", 3)[3].startswith(y.lstrip("/"))]
esit(_engelli, [], "robots.txt isaret dosyalarini ENGELLEMIYOR")

print(f"\nTUM TESTLER GECTI ({_gecti})")
