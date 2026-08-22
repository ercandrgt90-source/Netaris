"""Olay tespiti ve siddet hesabi.

HER HABER OLAY DEGILDIR
-----------------------
Gunde 130 haber geliyor. Bunlarin belki besi hakkinda "piyasada ne oldu"
yazisi yazmaya deger. Olay esigi bu ayrimi yapar.

ESIK IKI PARCALI
----------------
1. KONU  -- haber su turlerden biri mi: enflasyon, faiz karari, istihdam,
            jeopolitik, arz soku, kur.
2. AGIRLIK -- ayni turde her haber ayni degil. "TCMB faiz kararini
            acikladi" ile "TCMB haftalik istatistik yayimladi" ikisi de
            para politikasi konusunda ama biri olay, digeri degil.

Agirlik uc kaynaktan gelir:
  * kalip gucu   -- "faiz karari" gucludur, "faiz" zayiftir
  * kaynak       -- resmi kurumun kendi duyurusu, gazete aktariminda agir
  * yayilim      -- ayni haberi kac kaynak verdi (ilgi yogunlugu)

NEDEN SAYISAL BIR SIDDET
------------------------
Esigi "gecti/gecmedi" yapmak yerine puan vermek, ana sayfada siralama
ve arsivde "en buyuk olaylar" sorgusu icin gerekli. Ayrica esik sonradan
kalibre edilebilir hale geliyor.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

#: Turkce harfleri ASCII karsiligina indirir. Once translate, SONRA lower.
_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def katla(metin: str) -> str:
    return metin.translate(_KATLAMA).lower()


def _ara(metin: str) -> str:
    """Bosluklarla paylanmis, katlanmis metin.

    Kisa kaliplarin ("zam", "veri") kelime icinde eslesmesini engelliyor;
    ayrica basliktaki ilk ve son kelimeye de erisim veriyor.
    """
    return " " + re.sub(r"\s+", " ", katla(metin)) + " "


#: Olay turleri ve kaliplari.
#:
#: Her kalip bir AGIRLIK tasiyor. Yuksek agirlikli kalip tek basina
#: esigi gecirebilir; dusuk agirlikli olanlar birikerek gecirir.
#:
#: Sira onemli: ilk eslesen tur kazanir, o yuzden en ozgul olan ustte.
OLAY_TURLERI: tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...] = (
    ("faiz", "Faiz kararı", (
        ("faiz oranlarina iliskin", 10),
        ("para politikasi kurulu", 10),
        ("politika faizi", 8),
        ("faiz karari", 9),
        ("faizi sabit", 8),
        ("faizde indirim", 8),
        ("faiz indirim", 7),
        ("faiz artir", 7),
        ("fomc", 9),
        ("rate decision", 9),
        ("monetary policy decision", 9),
        ("zorunlu karsilik", 6),
    )),
    ("enflasyon", "Enflasyon verisi", (
        ("enflasyon rakam", 9),
        ("enflasyon verisi", 9),
        ("tufe", 8),
        ("enflasyon acikla", 9),
        ("fiyat gelismeleri", 7),
        ("uretici fiyat", 6),
        ("enflasyon raporu", 8),
        ("cpi", 7),
        ("inflation", 6),
    )),
    ("istihdam", "İstihdam verisi", (
        ("tarim disi istihdam", 10),
        ("nonfarm payroll", 10),
        ("issizlik orani", 7),
        ("istihdam verisi", 7),
        ("unemployment rate", 7),
        ("jobs report", 8),
    )),
    ("jeopolitik", "Jeopolitik gelişme", (
        ("saldiri duzenledi", 8),
        ("hava saldirisi", 8),
        ("askeri operasyon", 8),
        ("savas ilan", 9),
        ("ateskes", 7),
        ("yaptirim karari", 6),
        ("ambargo", 7),
        ("hurmuz", 9),
        ("bogazi kapat", 9),
        ("misilleme", 7),
    )),
    ("arz", "Arz gelişmesi", (
        ("opec karar", 9),
        ("uretim kotasi", 8),
        ("uretim kesinti", 8),
        ("arz kesinti", 8),
        ("boru hatti", 6),
        ("rafineri yangin", 7),
        ("stok verisi", 5),
        ("production cut", 8),
    )),
    ("kur", "Kur hareketi", (
        ("dolar endeksi", 6),
        ("kur artis", 6),
        ("doviz kur", 5),
        ("muhalefet mudahale", 7),
        ("doviz mudahale", 8),
    )),
)

#: Resmi kurumun KENDI duyurusu, gazete aktarimindan agirdir. Fed'in
#: kendi sitesinde yayimladigi FOMC bildirisi birincil kaynaktir.
KAYNAK_AGIRLIGI = {
    "TCMB": 4, "Fed": 4, "ECB": 3, "SEC": 2, "EIA": 2,
    "AA": 1, "TRT Haber": 1,
}

#: Bu puanin altindaki haber icin olay yazisi URETILMEZ.
#: Kalibrasyon notu: 8, "tek gucli kalip + resmi kaynak" ya da "iki orta
#: kalip + yayilim" demek. Deneyimle ayarlanacak bir sayi.
ESIK = 8


@dataclass
class Olay:
    tur: str
    tur_adi: str
    baslik: str
    siddet: int
    eslesmeler: tuple[str, ...] = field(default_factory=tuple)
    kaynak: str = ""
    adres: str = ""
    an: str = ""
    yayilim: int = 1

    @property
    def anahtar(self) -> str:
        """Tekrar uretimi engelleyen kimlik.

        Adres degil BASLIK IMZASI kullaniliyor: ayni olay farkli
        kaynaklarda farkli adreste cikiyor. Adres kullansaydik ayni olay
        icin bes yazi uretilirdi.
        """
        cekirdek = re.sub(r"[^a-z0-9 ]", " ", katla(self.baslik))
        govdeler = sorted({p[:5] for p in cekirdek.split() if len(p) > 3})
        im = hashlib.sha256(
            (self.tur + "|" + " ".join(govdeler[:8])).encode("utf-8")
        ).hexdigest()[:16]
        return f"{self.tur}:{im}"


def siniflandir(baslik: str, kurum: str = "", yayilim: int = 1) -> Olay | None:
    """Baslik bir olay mi? Degilse None.

    `yayilim` ayni haberi kac kaynagin verdigi. Tekilleme sirasinda
    sayilir; bir haberin bes kaynakta cikmasi ilgi yogunlugunun olcusu.
    """
    metin = _ara(baslik)

    for tur, tur_adi, kaliplar in OLAY_TURLERI:
        bulunan = [(k, a) for k, a in kaliplar if k in metin]
        if not bulunan:
            continue

        # Kalip puani: en gucluyu tam, kalanlari yarim sayiyoruz.
        # Toplamak, ayni seyi soyleyen iki kalibi iki kat onemli
        # gosterirdi ("faiz karari" ve "politika faizi" ayni olay).
        puanlar = sorted((a for _, a in bulunan), reverse=True)
        puan = puanlar[0] + sum(p // 2 for p in puanlar[1:3])
        puan += KAYNAK_AGIRLIGI.get(kurum, 0)
        # Yayilim: iki kaynaktan sonrasi icin kaynak basina 1 puan,
        # en fazla 3. Sinir olmasa magazinlesen bir haber esigi gecerdi.
        puan += min(max(yayilim - 1, 0), 3)

        return Olay(
            tur=tur, tur_adi=tur_adi, baslik=baslik.strip(),
            siddet=puan, kaynak=kurum, yayilim=yayilim,
            eslesmeler=tuple(k for k, _ in bulunan),
        )
    return None


def esigi_gecti(o: Olay | None) -> bool:
    return o is not None and o.siddet >= ESIK


#: Olay turu -> etkilenmesi beklenen varlik kodlari.
#:
#: Bu liste GRAFTAN turetilemez cunku graf "neyin neyi etkiledigini"
#: soyler, "hangi olayda hangisine bakilacagini" degil. Jeopolitik bir
#: olayda once petrol ve altina bakilir; enflasyon verisinde faize ve
#: tahvile. Baslangic noktasi burada, yayilim graftan.
#: SP500 ve VIX CIKARILDI -- lisanslari bizde degil ve bu liste bir
#: OLCUM listesi: olay sayfasinda her varligin DEGERI ve degisimi
#: basiliyor. Adini anmak serbest (gazetecilikte oldugu gibi), degerini
#: yayimlamak lisans istiyor. Gerekce:
#: `makro_uret_ucretsiz.LISANSSIZ_SERILER`.
OLAY_VARLIKLARI = {
    "faiz":       ("XAU", "BTC", "DXY", "US10Y", "US2Y"),
    "enflasyon":  ("XAU", "BTC", "US10Y", "DXY"),
    "istihdam":   ("XAU", "BTC", "US10Y", "DXY"),
    "jeopolitik": ("BRENT", "XAU", "XAG", "BTC"),
    "arz":        ("BRENT", "WTI", "XAU"),
    "kur":        ("XAU", "DXY", "USDTRY"),
}

#: Olculecek pencereler (saniye). Kisa pencere haber etkisini, uzun
#: pencere gunluk egilimi gosterir. Ikisi de yaziliyor cunku "bir saatte
#: %2 yukseldi" ile "gun boyunca %2 yukseldi" ayni sey degil.
PENCERELER = ((3600, "1 saat"), (4 * 3600, "4 saat"), (24 * 3600, "24 saat"))
