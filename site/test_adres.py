"""Sitenin ASIL ADRESI -- uc yerde ayni olmali.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): sitedeki HER SAYFANIN canonical, og:url ve
og:image adresi `netaris.ercandrgt90.workers.dev` gosteriyordu --
1.713 adres.

Sebep: `insa.TABAN_ADRES` varsayilani alan adi baglandiginda
guncellenmemisti. Kodda "alan adi baglandiginda tek is bu" diye bir
not bile duruyordu; not yazilmis, adim atlanmisti.

Sonuclari:
  * Google netaris.net'i degil workers.dev'i ASIL ADRES sayiyordu;
    alan adina yazilan hicbir SEO degeri birikmiyordu.
  * Paylasilan her baglanti workers.dev aciyordu.
  * O alan adi bazi aglarda ENGELLI -- yani erisilemeyen bir adresi
    asil adres ilan ediyorduk.

HICBIR HATA GORUNMUYORDU. Sayfalar uretiliyor, adresler gecerli, site
calisiyordu. Yalnizca yanlis alan adini gosteriyordu.

UC YERDE TUTULUYOR
------------------
    site/insa.py                TABAN_ADRES   sayfa adresleri
    site/dogrula.py             VARSAYILAN    yayin dogrulamasi
    haber_botu/uret_uye_yazi.py TABAN         uye yazisi baglantilari

Ayrisirlarsa: dogrulama BASKA BIR SITEYI kontrol eder ve "her sey
yolunda" der; uye yazisi kendi sitesinin disina baglanir. Ikisi de
sessiz.

Bu depoda ayni sinif ayrisma bugun UC KEZ cikti (JS/Python diakritik
tablolari, `_stem` ile kavram metni, ulke kodlari). Ortak yani: iki
yerde tutulan bir deger zamanla ayrisir ve AYRISMA HATA VERMEZ.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_KOK = _SITE.parent
sys.path.insert(0, str(_SITE))

import insa  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


def _varsayilan(dosya: pathlib.Path, ad: str) -> str:
    """Kaynaktan varsayilan adresi okur.

    Modulu ICE AKTARMIYORUZ: `uret_uye_yazi` ag ve depo baglantisi
    kuruyor, sinamayi ortama bagimli yapardi. Aranan sey bir metin
    sabiti ve metin olarak okunuyor.
    """
    m = dosya.read_text(encoding="utf-8")
    k = re.search(rf'{ad}\s*=\s*(?:os\.environ\.get\(\s*"[^"]+",\s*)?'
                  r'"(https://[^"]+)"', m)
    return k.group(1) if k else ""


ASIL = insa.TABAN_ADRES

print("\nAsil adres")
esit(ASIL, "https://netaris.net", "insa.TABAN_ADRES alan adini gosteriyor")
esit(ASIL.endswith("/"), False, "sonunda egik cizgi YOK")
esit("workers.dev" in ASIL, False, "workers.dev DEGIL")

print("\nUc kaynak ayni adresi tasiyor")
esit(_varsayilan(_SITE / "dogrula.py", "VARSAYILAN"), ASIL,
     "dogrula.py ayni adres")
esit(_varsayilan(_KOK / "haber_botu" / "uret_uye_yazi.py", "TABAN"), ASIL,
     "uret_uye_yazi.py ayni adres")

# --------------------------------------------------------------------
# HICBIR YERDE workers.dev KALMASIN.
#
# Yorum satirlarinda GECEBILIR: neden o adresten vazgecildigi orada
# yazili ve o bilgi kalmali. Aranan sey KOD icinde kullanilmasi.
# --------------------------------------------------------------------
print("\nKodda workers.dev kullanimi yok")
_TARANAN = (
    _SITE / "insa.py", _SITE / "dogrula.py", _SITE / "worker.js",
    _KOK / "haber_botu" / "uret_uye_yazi.py",
)
for dosya in _TARANAN:
    if not dosya.exists():
        continue
    kusurlu = []
    for no, satir in enumerate(dosya.read_text(encoding="utf-8").splitlines(),
                               1):
        cip = satir.strip()
        if cip.startswith("#") or cip.startswith("*") or cip.startswith("//"):
            continue
        if "workers.dev" in satir:
            kusurlu.append(f"{dosya.name}:{no}")
    esit(kusurlu, [], f"{dosya.name} kodunda workers.dev yok")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
