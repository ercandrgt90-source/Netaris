"""GUVENLIK BASLIKLARI URETILIYOR MU.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-15): canli yanitta guvenlik basliklarinin HICBIRI
yoktu -- ne `nosniff`, ne `Referrer-Policy`, ne cerceve korumasi.
Donen basliklarin tamami sunucunun kendi verdikleriydi:

    CF-Cache-Status, CF-RAY, Cache-Control, Connection, Content-Type,
    Date, Nel, Report-To, Server, Transfer-Encoding, alt-svc

Statik bir blog icin kucuk bir eksik; UYELIK ve OTURUMU olan bir site
icin degil. `/giris/` ve `/panel/` cerez tasiyor.

Kusur SESSIZ: eksik bir baslik hicbir sey bozmaz, hicbir yerde hata
vermez. Yalnizca bir gun lazim olur.

NE SINANIYOR
------------
1. Basliklar `_headers`e yaziliyor ve `/*` kapsaminda -- yani her
   sayfada.
2. `/statik/*` gibi alt kurallar onlari DUSURMUYOR (`!` yalnizca
   `Cache-Control`i kaldirmali).
3. Kisitlanan yetenekler gercekten KULLANILMIYOR: bedeli olmayan bir
   kisitlama secildi, calisan bir sey kapatilmadi.
4. Baglayici olanlar (HSTS) BILEREK yok -- geri alinamaz bir karar
   koda sizmasin.
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


#: Her sayfada bulunmasi gereken basliklar.
ZORUNLU = (
    "X-Content-Type-Options",
    "Referrer-Policy",
    "X-Frame-Options",
    "Permissions-Policy",
)

#: `Permissions-Policy` ile kapatilan yetenekler. Her biri icin
#: depoda KULLANILMADIGI da sinanacak -- yoksa kisitlama, calisan
#: bir seyi kapatmis olurdu.
KAPATILAN = {
    "camera": ("getUserMedia", "navigator.camera"),
    "microphone": ("getUserMedia",),
    "geolocation": ("geolocation",),
    "payment": ("PaymentRequest",),
}

print("\nKaynak kodda tanimli")
_k = (_SITE / "insa.py").read_text(encoding="utf-8")
for _b in ZORUNLU:
    esit(f'"  {_b}:' in _k, True, f"{_b} insa.py'de yaziliyor")

# BAGLAYICI KARAR KODA SIZMASIN. HSTS tarayicida onbelleklenir ve
# suresi dolana kadar GERI ALINAMAZ -- bir yila kadar baglayici.
# Alan adi sahibinin karari, kod degisikligi degil.
esit("Strict-Transport-Security" in _k, False,
     "HSTS BILEREK yok (geri alinamaz, alan adi sahibinin karari)")

print("\nUretilen dosyada")
_h = _SITE / "cikti" / "_headers"
if not _h.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
else:
    _metin = _h.read_text(encoding="utf-8")

    # Kurallari kapsamlara ayir: hangi baslik HANGI yol icin gecerli.
    _kapsam: dict[str, list[str]] = {}
    _simdi = None
    for _s in _metin.splitlines():
        if _s and not _s.startswith((" ", "\t")):
            _simdi = _s.strip()
            _kapsam[_simdi] = []
        elif _simdi and _s.strip():
            _kapsam[_simdi].append(_s.strip())

    esit("/*" in _kapsam, True, "/* kurali var (her sayfa)")
    for _b in ZORUNLU:
        esit(any(x.startswith(_b + ":") for x in _kapsam["/*"]), True,
             f"{_b} /* kapsaminda")

    # `!` YALNIZCA Cache-Control'u kaldirmali. Bir alt kural guvenlik
    # basligini dusurse, o yollar sessizce korumasiz kalirdi.
    _dusurulen = []
    for _yol, _kurallar in _kapsam.items():
        for _x in _kurallar:
            if not _x.startswith("!"):
                continue
            _ad = _x.lstrip("! ").rstrip(":").strip()
            if _ad in ZORUNLU:
                _dusurulen.append(f"{_yol}: {_ad}")
    esit(_dusurulen, [], "hicbir alt kural guvenlik basligini DUSURMUYOR")

print("\nKisitlamanin bedeli yok -- kapatilan yetenek kullanilmiyor")
_kaynaklar = list((_SITE / "statik").glob("*.js"))
_kaynaklar += list((_SITE / "sablonlar").glob("*.html"))
_govde = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                   for p in _kaynaklar)
# Yorumlar ayiklaniyor: bir yetenegin NEDEN kapatildigini anlatan
# yazi, onu "kullaniliyor" gostermemeli.
_govde = re.sub(r"/\*[\s\S]*?\*/", " ", _govde)
_govde = re.sub(r"\{#[\s\S]*?#\}", " ", _govde)
_govde = re.sub(r"<!--[\s\S]*?-->", " ", _govde)
for _yetenek, _izler in KAPATILAN.items():
    _bulunan = [i for i in _izler if i in _govde]
    esit(_bulunan, [], f"{_yetenek} depoda kullanilmiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
