"""Yayin oncesi ifade taramasi.

Amac: uretilen metnin yatirim tavsiyesi olarak yorumlanabilecek ifadeler
icermedigini yayin oncesi dogrulamak. Turkiye'de yatirim danismanligi SPK
izni gerektirir; metni AI uretse bile sorumluluk yayinciya aittir.

Iki kademeli calisir:
  YASAK  -> icerik yayinlanamaz, yeniden uretilmeli
  UYARI  -> insan denetiminde ozellikle bakilmali

Bu modul son savunma hatti, ilk savunma degil. Al/sat dili once prompt
seviyesinde yasaklanir; buradaki tarama modelin o kurala uymadigi durumlari
yakalar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class Seviye(Enum):
    YASAK = "yasak"
    UYARI = "uyari"


@dataclass(frozen=True)
class Bulgu:
    seviye: Seviye
    terim: str
    baglam: str
    aciklama: str

    def __str__(self) -> str:
        return f"[{self.seviye.value.upper()}] {self.terim!r} — {self.aciklama}\n    ...{self.baglam}..."


# ---------------------------------------------------------------------------
# Turkce normalizasyon
# ---------------------------------------------------------------------------
# Iki ayri sorun cozuluyor:
#
# 1. Python'un str.lower() metodu "İ" harfini "i" + birlesik nokta olarak
#    cozumler; bu desen eslesmesini sessizce bozar.
#
# 2. Turkce metin sahada cok sik diakritiksiz yazilir ("yukselecek",
#    "portfoyunuze"). Desenler diakritikli yazilirsa bu varyantlar sessizce
#    gecer -- yasal risk tasiyan bir yanlis negatif. Bu yuzden hem metni hem
#    desenleri ASCII'ye katliyoruz: "ı" ve "i" ayni, "ş" ve "s" ayni sayilir.
#
# Katlamanin bedeli, yanlis pozitif riskinin bir miktar artmasi. Insan
# denetimi hatti zaten kapattigi icin bu takas dogru yonde: kacirmak
# yakalamaktan pahali.

_ASCII_KATLAMA = str.maketrans(
    {
        "ı": "i", "İ": "i", "I": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
        "â": "a", "Â": "a",
        "î": "i", "Î": "i",
        "û": "u", "Û": "u",
    }
)


def normalize(metin: str) -> str:
    """Metni ASCII'ye katlanmis kucuk harfe cevirir.

    Desenler de ayni bicimde yazilmalidir; aksi halde eslesme sessizce
    basarisiz olur.
    """
    metin = unicodedata.normalize("NFC", metin)
    return metin.translate(_ASCII_KATLAMA).lower()


# ---------------------------------------------------------------------------
# Desenler
# ---------------------------------------------------------------------------
# Her desen kelime siniriyla eslesir. Bu kritik: "al" alt dizgesi "alacak",
# "analiz", "kalan", "alan" gibi tamamen masum kelimelerin icinde geciyor.
# Turkce sondan eklemeli oldugu icin cekimli biciimler ayri ayri yazilir.

# DIKKAT: Desenler ASCII'ye katlanmis bicimde yazilir (normalize() ile ayni
# bicim). Yani "yükselecek" degil "yukselecek", "fırsatı" degil "firsati".
# Diakritikli bir desen HICBIR ZAMAN eslesmez.

_YASAK_DESENLER: list[tuple[str, str]] = [
    # Dogrudan islem yonlendirmesi.
    # "satin al-" birlesigi disarida tutuluyor: "sirketi satin aldi" bir
    # sirket devralma haberidir, yatirim tavsiyesi degil.
    (r"(?<!satin )\bal(?:in|inir|inabilir|inmali|abilirsiniz)\b",
     "dogrudan alim yonlendirmesi"),
    (r"\balim\s+(?:firsati|zamani|yapilabilir|onerisi|tavsiyesi)", "alim onerisi"),
    (r"\bsatis\s+(?:firsati|zamani|yapilabilir|onerisi|tavsiyesi)", "satis onerisi"),
    (r"\bsat(?:ilabilir|ilmali|abilirsiniz)\b", "dogrudan satis yonlendirmesi"),
    (r"\bpozisyon\s+(?:acil|alin|kapat)", "pozisyon yonlendirmesi"),
    (r"\bportfoy(?:unuz|e|une|unuze)\s+(?:ekle|dahil|kat)", "portfoy yonlendirmesi"),

    # Fiyat hedefi / getiri taahhudu
    (r"\bhedef\s+fiyat", "hedef fiyat beyani"),
    (r"\bfiyat\s+hedefi", "hedef fiyat beyani"),
    (r"\b(?:getiri|kazanc)\s+(?:garanti|vaad|taahhut)", "getiri taahhudu"),

    # Kesin fiyat yonu tahmini.
    # Not: "artacak" ve "gerileyecek" burada DEGIL, UYARI listesinde --
    # makro icerikte ("enflasyon artacak") mesru bicimde kullanilabiliyorlar.
    (r"\b(?:yukselecek|dusecek|patlayacak|cakilacak|ucacak|eriyecek)\b",
     "kesin fiyat yonu tahmini"),
    (r"\bkesinlikle\s+(?:yuksel|dus|art|geril)", "kesin yon tahmini"),

    # Tavsiye dili
    (r"\b(?:oneriyoruz|oneririz|tavsiye\s+ediyoruz|tavsiye\s+ederiz)\b",
     "dogrudan tavsiye"),
    (r"\b(?:al|tut|sat)\s+tavsiyesi\b", "derecelendirme tavsiyesi"),
    (r"\b(?:kacirmayin|firsati\s+kacir)", "aciliyet/tesvik dili"),
]

_UYARI_DESENLER: list[tuple[str, str]] = [
    # Degerleme yargilari - analitik baglamda kabul edilebilir ama gozden gecirilmeli
    (r"\b(?:ucuz|pahali|degerinin\s+(?:altinda|ustunde))\b",
     "degerleme yargisi — olcute dayandigi dogrulanmali"),
    (r"\b(?:cazip|iskontolu|primli)\b", "degerleme nitelemesi — gerekce belirtilmeli"),

    # Makro baglamda mesru olabilen yon tahminleri
    (r"\b(?:artacak|gerileyecek|azalacak)\b",
     "yon tahmini — konusu hisse fiyatiysa YASAK sayilmali"),

    # Ileriye yonelik ifadeler
    (r"\b(?:beklentimiz|tahminimiz|ongorumuz)\b",
     "ileriye yonelik ifade — kaynagi belirtilmeli (sirket beklentisi mi, analist konsensusu mu?)"),
    (r"\b(?:muhtemelen|buyuk\s+olasilikla)\s+(?:yuksel|dus|art|geril)",
     "olasilikli yon tahmini"),

    # Belirsiz kaynak
    (r"\b(?:piyasa|yatirimcilar)\s+(?:bekliyor|dusunuyor|umuyor)\b",
     "kaynaksiz piyasa beklentisi atfi"),
]


def _derle(desenler: list[tuple[str, str]]) -> list[tuple[re.Pattern[str], str]]:
    return [(re.compile(d, re.IGNORECASE | re.UNICODE), a) for d, a in desenler]


_YASAK = _derle(_YASAK_DESENLER)
_UYARI = _derle(_UYARI_DESENLER)

# Yasal uyarinin varligini dogrulamak icin aranan ifade (ASCII katlanmis)
_UYARI_METNI_DESEN = re.compile(r"yatirim\s+(?:tavsiyesi|danismanligi)\s+degil", re.IGNORECASE)


def _baglam(metin: str, bas: int, son: int, pencere: int = 45) -> str:
    b = max(0, bas - pencere)
    s = min(len(metin), son + pencere)
    return metin[b:s].replace("\n", " ").strip()


def tara(metin: str) -> list[Bulgu]:
    """Metni tarar ve bulunan sorunlu ifadeleri dondurur.

    Eslesme normalize edilmis metin uzerinde yapilir, ancak baglam orijinal
    metinden alinir; boylece rapor okunabilir kalir.
    """
    hedef = normalize(metin)
    bulgular: list[Bulgu] = []

    for seviye, desenler in ((Seviye.YASAK, _YASAK), (Seviye.UYARI, _UYARI)):
        for desen, aciklama in desenler:
            for eslesme in desen.finditer(hedef):
                bulgular.append(
                    Bulgu(
                        seviye=seviye,
                        terim=metin[eslesme.start():eslesme.end()],
                        baglam=_baglam(metin, eslesme.start(), eslesme.end()),
                        aciklama=aciklama,
                    )
                )
    return bulgular


def yasal_uyari_var_mi(metin: str) -> bool:
    """Icerikte 'yatirim tavsiyesi degildir' ifadesinin bulunup bulunmadigi."""
    return bool(_UYARI_METNI_DESEN.search(normalize(metin)))


def yayinlanabilir(metin: str) -> tuple[bool, list[Bulgu]]:
    """Yayin karari.

    Yasak seviyesinde tek bulgu varsa ya da yasal uyari eksikse icerik
    yayinlanamaz. Uyari seviyesindeki bulgular yayini engellemez, insan
    denetimine isaret eder.
    """
    bulgular = tara(metin)
    engel = [b for b in bulgular if b.seviye is Seviye.YASAK]

    if not yasal_uyari_var_mi(metin):
        bulgular.append(
            Bulgu(
                seviye=Seviye.YASAK,
                terim="(eksik)",
                baglam="",
                aciklama="icerikte 'yatirim tavsiyesi degildir' uyarisi bulunamadi",
            )
        )
        engel.append(bulgular[-1])

    return (not engel), bulgular


def rapor(metin: str) -> str:
    """Insan tarafindan okunacak tarama raporu."""
    tamam, bulgular = yayinlanabilir(metin)
    satirlar = [f"SONUC: {'YAYINLANABILIR' if tamam else 'ENGELLENDI'}"]

    yasak = [b for b in bulgular if b.seviye is Seviye.YASAK]
    uyari = [b for b in bulgular if b.seviye is Seviye.UYARI]
    satirlar.append(f"  {len(yasak)} yasak, {len(uyari)} uyari")

    for b in yasak + uyari:
        satirlar.append("")
        satirlar.append(str(b))
    return "\n".join(satirlar)
