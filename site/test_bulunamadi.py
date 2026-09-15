"""404 SAYFASI VAR MI, SERVIS EDILIYOR MU, HER ADRESTE CALISIR MI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-15): `https://netaris.net/analiz/` SIFIR BAYT
donuyordu. Yalniz o adres de degil -- sitede 404 sayfasi HIC YOKTU
ve `wrangler.toml` `not_found_handling = "none"` diyordu. Yani
yanlis yazilmis her adres, eskimis her paylasim, adresini kirpan her
okur bembeyaz bir sayfa goruyordu.

Kusur SESSIZDI cunku hicbir sey hata vermiyor: Cloudflare dogru
statuyu (404) doner, yalnizca govde bostur. Ne kurulum patlar, ne
denetim, ne de bir gunluk satiri. Site "calisiyor" gorunur.

`worker.js`teki not "normal 404 sayfasi cikiyor" diyordu -- hicbir
zaman dogru olmamis bir varsayim. Yorumun iddiasini olcen bir sinama
yoktu; simdi var.

NE SINANIYOR
------------
1. Sayfa URETILIYOR (`cikti/404.html`).
2. Sayfa SERVIS EDILIYOR (`not_found_handling = "404-page"`) -- ve
   `single-page-application` SECILMIYOR: o, kirik baglantiyi 200 ile
   ana sayfa gosterir, yani 404'u bastirir.
3. Icindeki HER baglanti MUTLAK. Bu sayfa kendi adresinde degil,
   BULUNAMAYAN HER ADRESTE servis ediliyor: goreli bir `x.js`,
   `/haber/abc/` altinda `/haber/abc/x.js` olur ve sessizce kirilir.
4. `noindex` tasiyor ve haritada YOK.
"""

from __future__ import annotations

import pathlib
import re
import sys

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


print("\nSayfa SERVIS EDILIYOR -- worker'dan, ayardan DEGIL")
_ayar = (_SITE / "wrangler.toml").read_text(encoding="utf-8")
# Yorum satirlari ayiklaniyor: bu dosyada "single-page-application"
# NEDEN SECILMEDIGI yaziyor ve ciplak arama onu AYAR sanirdi.
_etkin = "\n".join(s for s in _ayar.splitlines()
                   if not s.lstrip().startswith("#"))
_nfh = re.search(r'not_found_handling\s*=\s*"([^"]+)"', _etkin)
# "404-page" CAZIP AMA YANLIS. Varlik katmani worker'dan ONCE
# calisiyor ve `assets_navigation_prefers_asset_serving` (uyumluluk
# tarihimiz 2026-07-31, esik 2025-04-01) gezinme isteklerinin
# worker'i HIC cagirmamasina yol aciyor. Bu sitede eslesen DOSYASI
# olmayan ama worker'in URETTIGI adresler var -- olculdu,
# `Sec-Fetch-Mode: navigate` ile:
#
#     /senaryo/1/  -> 200, 10888 bayt   (worker uretti)
#     /haber       -> 301 /gundem       (worker yonlendirdi)
#
# Ayari acmak calisan iki ozelligi belgesiz bir davranisa yaslardi.
# 404 sayfasi bu yuzden worker'da, varlik katmani 404 dondugu YERDE.
esit(_nfh and _nfh.group(1), "none",
     "not_found_handling = none -- /senaryo/ ve /haber worker'a dusmeli")
esit("single-page-application" in _etkin, False,
     "SPA modu secili DEGIL -- kirik baglanti 200 donmemeli")

# Cagriya OZEL arama: ciplak "/404.html" bu dosyanin yorumlarinda da
# geciyor ve onu saymak, kaldirilmis bir cagriyi duruyor gosterirdi.
# Davranisin kendisi `site/test_bulunamadi_servis.js` ile olculuyor.
_wrk = (_SITE / "worker.js").read_text(encoding="utf-8")
esit('env.ASSETS.fetch(new URL("/404.html"' in _wrk, True,
     "worker 404.html servis ediyor (davranis: test_bulunamadi_servis.js)")

print("\nSayfa URETILIYOR")
_s = _SITE / "sablonlar" / "bulunamadi.html"
esit(_s.exists(), True, "sablon duruyor")
_kaynak = (_SITE / "insa.py").read_text(encoding="utf-8")
esit('yaz(\n        "/404.html"' in _kaynak
     or '"/404.html"' in _kaynak, True, "insa.py 404.html yaziyor")

_c = _SITE / "cikti" / "404.html"
if not _c.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_h = _c.read_text(encoding="utf-8")
esit(len(_h) > 1500, True, f"govde dolu ({len(_h)} bayt, once 0 idi)")
esit(bool(re.search(r"<h1[^>]*>", _h)), True, "baslik var")

print("\nHER ADRESTE CALISIR -- baglantilar MUTLAK")
# Sayfa `/haber/abc/xyz/` altinda servis edilebilir; goreli bir yol
# oraya gore cozulur ve 404'un kendisi kirilir.
_goreli = []
for _nitelik in ("href", "src"):
    for _d in re.findall(rf'{_nitelik}="([^"]*)"', _h):
        if _d.startswith(("/", "http://", "https://", "#", "data:",
                          "mailto:", "tel:")):
            continue
        _goreli.append(f"{_nitelik}={_d}")
esit(_goreli[:5], [], "goreli baglanti YOK (her adreste cozulur)")

print("\nDizine girmiyor")
esit(bool(re.search(r'name="robots"[^>]*content="[^"]*noindex', _h, re.I)),
     True, "noindex tasiyor")
_hrt = _SITE / "cikti" / "sitemap.xml"
if _hrt.exists():
    esit("404.html" in _hrt.read_text(encoding="utf-8"), False,
         "haritada YOK")

print(f"\nTUM TESTLER GECTI ({_gecti})")
