"""Uretilen dosya adi ve adres, isletim sisteminin sinirini asmamali.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-14): ticari bir kaynagin anahtar kelime yigilmis
basligindan 214 karakterlik bir slug ve 223 karakterlik bir dosya adi
uretildi:

    2026-09-14-makro-piyasa-tepkisi-eylul-ayi-kira-artis-orani-
    hesaplama-2026-eylul-ayi-kira-artis-orani-belli-oldu-eylul-kira-
    zammi-ne-kadar-gozler-tuik-te-iste-tuik-aciklamasina-gore-tefe-
    tufe-ve-kira-artis-orani-hesaplama.md

Sonuclari:

  * `git pull` Windows'ta DUSTU:
        error: cannot stat '...': Filename too long
    Yani depo, Windows'ta klonlanamaz hale geldi.

  * Dosya diske yazildiktan sonra bile `python site/insa.py` acamadi:
    tam yol 282 karakter, Windows siniri 260. Site YERELDE HIC
    KURULAMIYORDU.

  * Adres paylasilabilir olmaktan cikti.

Linux'ta (yani CI'da) hicbiri gorunmuyordu: kosu yesil bitti, sayfa
yayina cikti. Ariza yalnizca gelistiricinin makinesinde vardi -- ve
orasi sitenin denendigi yer.

`site/insa.py` haber capalarini zaten 70 karakterle sinirliyordu;
karar verilmisti, yalnizca URETIM tarafinda uygulanmamisti.

NE SINANIYOR
------------
1. `slug_kisalt` kelime sinirindan kesiyor ve kesilene kararli bir
   ozet ekliyor (cakisma korumasi).
2. Ozet SUREC BASINA DEGISMIYOR -- `hash()` kullanilsaydi ayni yazi
   her kosuda baska bir adres alirdi.
3. `yaz_makro` hem dosya adini hem frontmatter slug'ini sinirliyor.
4. Depoda sinirlari asan icerik yok.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
_DEPO = _KOK.parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai"), str(_DEPO / "site")]

import yayin                                          # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


# ---------------------------------------------------------------------
print("\nslug_kisalt -- sinirin altindakine DOKUNULMUYOR")
# Mevcut adreslerin hicbiri degismemeli: kisa slug aynen gecmeli.
_kisa = "tcmb-faiz-karari-2026-09-14"
esit(yayin.slug_kisalt(_kisa), _kisa, "kisa slug aynen doner")
esit(yayin.slug_kisalt(""), "", "bos slug cokmez")
_tam = "a" * yayin.SLUG_SINIRI
esit(yayin.slug_kisalt(_tam), _tam, "tam sinirdaki slug kirpilmaz")

print("\nslug_kisalt -- uzun slug KELIME SINIRINDAN kesiliyor")
_uzun = ("piyasa-tepkisi-eylul-ayi-kira-artis-orani-hesaplama-2026-eylul-"
         "ayi-kira-artis-orani-belli-oldu-eylul-kira-zammi-ne-kadar-gozler-"
         "tuik-te-iste-tuik-aciklamasina-gore-tefe-tufe-ve-kira-artis-"
         "orani-hesaplama")
_k = yayin.slug_kisalt(_uzun)
esit(len(_uzun) > 200, True, "girdi gercekten uzun (olculen vaka)")
esit(len(_k) <= yayin.SLUG_SINIRI, True,
     f"cikti sinirin altinda ({len(_k)} <= {yayin.SLUG_SINIRI})")
esit(_k.startswith("piyasa-tepkisi-"), True, "bas taraf korunuyor")
esit("--" not in _k and not _k.endswith("-"), True,
     "kesik tire birakmiyor")

print("\nCAKISMA KORUMASI -- kirpma tek basina veri kaybettirir")
# Ilk 80 karakteri AYNI, devami farkli iki konu. Yalnizca kirpilsaydi
# ikisi de ayni dosyaya yazilir, biri otekini sessizce ezerdi.
_onek = ("abd-enflasyon-rakamlari-ne-zaman-saat-kacta-aciklanacak-temmuz-"
         "ayi-abd-enflasyon-tahminleri-ne-yonde-")
_a = _onek + "beklenti-yukari-yonlu-revize-edildi-piyasa-tepkisi"
_b = _onek + "beklenti-asagi-yonlu-revize-edildi-piyasa-tepkisi"
esit(_a[:yayin.SLUG_SINIRI] == _b[:yayin.SLUG_SINIRI], True,
     "iki konu ilk 80 karakterde AYNI")
esit(yayin.slug_kisalt(_a) != yayin.slug_kisalt(_b), True,
     "yine de AYRI adres uretiyorlar")
esit(yayin.slug_kisalt(_a), yayin.slug_kisalt(_a),
     "ayni girdi ayni cikti -- yeniden uretim ayni dosyaya yazar")

print("\nOZET SUREC BASINA DEGISMIYOR (hash() kullanilmiyor)")
# `hash()` PYTHONHASHSEED ile rastgeleleniyor: ayni yazi her kosuda
# BASKA bir adres alirdi ve arsiv her gun bastan kirilirdi.
_betik = (
    "import sys; sys.path.insert(0, %r); import yayin;"
    "print(yayin.slug_kisalt(%r))" % (str(_KOK), _uzun)
)
_ciktilar = []
for _tohum in ("0", "1", "12345"):
    _ort = dict(os.environ, PYTHONHASHSEED=_tohum)
    _ciktilar.append(subprocess.run(
        [sys.executable, "-c", _betik], capture_output=True, text=True,
        env=_ort, cwd=str(_DEPO)).stdout.strip())
esit(len(set(_ciktilar)), 1,
     f"uc ayri PYTHONHASHSEED, tek sonuc: {_ciktilar[0][:40]}...")
esit(_ciktilar[0], yayin.slug_kisalt(_uzun), "alt surec ile ayni")


# ---------------------------------------------------------------------
print("\nyaz_makro -- HEM dosya adi HEM adres sinirli")
with tempfile.TemporaryDirectory() as _d:
    _yol = yayin.yaz_makro("## Özet\n\nMetin.\n", _uzun.replace("-", " "),
                           tarih_ustu="2026-09-14",
                           klasor=pathlib.Path(_d))
    _ad = _yol.name
    _on = _yol.read_text(encoding="utf-8")
    _slug = next(s[6:].strip() for s in _on.splitlines()
                 if s.startswith("slug: "))
    esit(len(_ad) <= 120, True, f"dosya adi sinirli ({len(_ad)})")
    esit(len(_slug) <= 120, True, f"adres sinirli ({len(_slug)})")
    # TARIH KIRPMANIN DISINDA: slug'in sonunda tarih vardi ve kirpma
    # oldugu gibi uygulansaydi tarih kesilirdi -- farkli gunlerin
    # yazilari ayni adrese duserdi.
    esit(_slug.endswith("2026-09-14"), True,
         "tarih kirpilmadi -- gunler ayrisiyor")
    esit(_ad.startswith("2026-09-14-makro-"), True, "dosya adi bicimi")


# ---------------------------------------------------------------------
# DEPO TARAMASI
#
# Sinirlar MAX_PATH aritmetiginden geliyor (Windows: 260):
#   kaynak  = depo koku + "/site/icerik/analizler/" (23) + dosya adi
#   cikti   = depo koku + "/site/cikti/analiz/"     (19) + slug + 11
# 60 karakterlik bir depo koku varsayilirsa dosya adi icin ~177,
# slug icin ~170 kaliyor. Paylara biraz bosluk birakiliyor.
# ---------------------------------------------------------------------
print("\nDepoda sinirlari asan icerik YOK")
AD_SINIRI = 170
SLUG_SINIRI_DEPO = 160

_dosyalar = subprocess.run(
    ["git", "ls-files", "site/icerik"], capture_output=True, text=True,
    encoding="utf-8", cwd=str(_DEPO)).stdout.splitlines()
esit(len(_dosyalar) > 100, True, f"tarama dolu ({len(_dosyalar)} dosya)")

_uzun_ad = [y for y in _dosyalar if len(y.rsplit("/", 1)[-1]) > AD_SINIRI]
esit(_uzun_ad, [], f"dosya adi {AD_SINIRI} karakteri asan yok")

_uzun_slug = []
for _y in _dosyalar:
    _p = _DEPO / _y
    if not _p.exists():
        continue
    for _s in _p.read_text(encoding="utf-8", errors="replace").splitlines():
        if _s.startswith("slug: "):
            if len(_s[6:].strip()) > SLUG_SINIRI_DEPO:
                _uzun_slug.append(_y)
            break
esit(_uzun_slug, [], f"slug {SLUG_SINIRI_DEPO} karakteri asan yok")


# ---------------------------------------------------------------------
print("\nKisaltilan adres YONLENDIRILIYOR")
import insa                                           # noqa: E402

esit(bool(insa.ESKI_ADRESLER), True, "yonlendirme tablosu dolu")
for _e, _y in insa.ESKI_ADRESLER:
    esit(_e.startswith("/") and _e.endswith("/"), True,
         f"eski adres bicimi: {_e[:40]}...")
    esit(_y.startswith("/") and _y.endswith("/"), True,
         f"yeni adres bicimi: {_y}")
    esit(_e != _y, True, "eski ve yeni adres FARKLI")

print(f"\nTUM TESTLER GECTI ({_gecti})")
