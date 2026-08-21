"""`bolge_bul` KONUYA baksin, kaynagin diline degil.

BULUNAN HATA (2026-08-21)
-------------------------
"Capital Economics'ten kritik degerlendirme: BoJ faiz artiracak mi?"
haberi TR siniflandirildi. Sonuc: Japon yeni konulu bir sayfaya
TURKIYE TUFE'si (%31,75) ve "Son on uc ayda TUFE" grafigi basildi.

Sebep, basliktaki "BoJ"un isaret listesinde olmamasiydi; listede
yalnizca "japonya" vardi. Isaret bulunamayinca dorduncu kural
("isaretsiz kalan TR") devreye girdi.

Turk bir yayinin BoJ analizi hala JAPONYA haberidir. Bolge, haberin
yazildigi dilden degil KONUSUNDAN cikmali.

BU DOSYA NEDEN VAR
------------------
Duzeltirken kendi ekledigim isaretlerden biri (" yeni ") "Borsada yeni
rekor" haberini DUNYA yapti -- Turkce'de "yeni" her yerde geciyor.
Yani bu alanda bir duzeltme sessizce baska bir yeri bozabiliyor ve
bozuldugu ancak SAYFADA goruluyor.

Sinamalar iki yonu birlikte tutuyor: yabanci konular DUNYA'ya
gitmeli, yurt ici konular TR'de KALMALI. Ikincisi olmadan liste
buyudukce her sey DUNYA'ya kayar.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import besleme  # noqa: E402

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


# --------------------------------------------------------------------
# YABANCI KONU -> DUNYA. Ulke adi GECMEDEN de taninmali; hata tam
# olarak buradaydi.
# --------------------------------------------------------------------
for _baslik in (
    "Capital Economics'ten kritik değerlendirme: BoJ faiz artıracak mı?",
    "Fed tutanakları: Birkaç üye faiz artışını savundu",
    "BoE faiz kararını açıkladı",
    "Powell Jackson Hole'da konuştu",
    "Lagarde enflasyon hedefini yineledi",
    "Japon yeni dolar karşısında geriledi",
):
    esit(besleme.bolge_bul(_baslik, "tr"), "DUNYA", _baslik[:52])

# --------------------------------------------------------------------
# YURT ICI KONU -> TR. Bu yon olmadan liste buyudukce her sey DUNYA'ya
# kayar; " yeni " ile tam bunu yasadim.
# --------------------------------------------------------------------
for _baslik in (
    "TCMB faizi sabit tuttu",
    "Enflasyon temmuzda yüzde 31,75 oldu",
    "Merkez Bankası yeni kararını açıkladı",
    "Borsada yeni rekor",
    "Dolar/TL yeni zirvede",
    "Hazine yeni tahvil ihracı yaptı",
    "Borsa günü yükselişle tamamladı",
):
    esit(besleme.bolge_bul(_baslik, "tr"), "TR", _baslik[:52])

# --------------------------------------------------------------------
# TURKCE OLMAYAN KAYNAK KOSULSUZ DUNYA -- basliga bakilmadan.
# --------------------------------------------------------------------
esit(besleme.bolge_bul("Fed holds rates steady", "en"), "DUNYA",
     "yabanci dil kosulsuz DUNYA")
esit(besleme.bolge_bul("Turkey's central bank cuts", "en"), "DUNYA",
     "yabanci dil, Turkiye konusu olsa bile DUNYA")

# --------------------------------------------------------------------
# KISA ISARETLER KELIME ICINDE ESLESMEMELI.
#
# Ayni tuzak daha once " ges " ile yasandi: "char-GES " icinde eslesip
# "SEC charges firm" haberini Enerji yapmisti.
# --------------------------------------------------------------------
for _isaret in besleme.YABANCI_PARA_OTORITESI:
    if len(_isaret.strip()) <= 4:
        esit(_isaret.startswith(" ") and _isaret.endswith(" "), True,
             f"{_isaret!r} kisa -- bosluklu olmali")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
