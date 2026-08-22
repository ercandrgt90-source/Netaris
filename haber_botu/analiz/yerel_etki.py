"""Yabanci gelismenin Turkiye'ye AKTARIM KANALI -- tahmin degil.

NEDEN GEREKLI
-------------
Yabanci konulu sayfalardan Turkiye verisini cikardim (bkz. `baglam`)
cunku Fed tutanaklari sayfasinda Turkiye TUFE'si yaziyordu ve okur onu
haberin verisi saniyordu. Duzeltme dogruydu ama EKSIK: Turk okurun bir
Fed haberindeki asil sorusu zaten "bu bizi nasil etkiler".

Veriyi yasaklamak o soruyu cevapsiz birakti. Dogru cozum veriyi
KALDIRMAK degil, ADI KONMUS bir yere koymak.

TAHMIN URETMIYOR
----------------
"Fed faiz artirirsa BIST duser" bir ONGORU ve bu sitede yasak. Burada
gosterilen sey KANAL: hangi degisken hangisini hangi mekanizmayla
etkiliyor. Kanal yapisal bir iliski, bir yon tahmini degil.

Zincirin her kenari `bag` tablosundan geliyor ve her kenarin kendi
gerekcesi var:

    FED_FAIZ -> US10Y -> CDS_TR -> USDTRY
                  |        |
                  |        +-- "Kuresel risksiz getiri yukseldiginde
                  |            gelismekte olan ulke risk primi..."
                  +-- "Kisa vadeli tahvil getirisi politika faizi
                      beklentisini fiyatlar."

Gerekcesi OLMAYAN kenar gosterilmiyor: mekanizmasi yazilamayan bir ok,
okura "bir sekilde etkiliyor" demekten baska bir sey soylemez.

EN KISA YOL, EN COK UC ADIM
---------------------------
Uzun zincirler ("A B'yi, B C'yi, C D'yi, D E'yi etkiler") her seyi her
seye baglayabiliyor ve aciklayici gucu sifira dusuyor. Uc adim, olculen
grafikte anlamli zincirleri yakalarken zorlamayi engelliyor.
"""

from __future__ import annotations

import collections
import pathlib
import sqlite3

DEPO = pathlib.Path(__file__).resolve().parent.parent / "netaris.db"

#: Zincirin varmasi gereken yurt ici varliklar.
#: `dosya.TURKIYE_VARLIKLARI` ile ayni aileden; burada yalnizca
#: FIYATLANAN olanlar var -- kurum (TUIK, SPK) bir aktarim ucu degil.
YEREL_UC = frozenset({
    "USDTRY", "BIST100", "CDS_TR", "TCMB_FAIZ", "TUFE_TR", "CARI_TR",
})

#: En fazla kac kenar. Bkz. modul bas yorumu.
EN_COK_ADIM = 3


def _kenarlar(b: sqlite3.Connection) -> dict[str, list[tuple[str, str, int]]]:
    """kaynak -> [(hedef, aciklama, guc)] -- yalnizca ACIKLAMALI kenarlar.

    Aciklamasi olmayan kenar disarida: mekanizmasi yazilamayan bir ok
    okura "bir sekilde etkiliyor" demekten baska bir sey soylemiyor.
    Olculdu: 63 bagin 34'unun aciklamasi var.
    """
    g: dict[str, list[tuple[str, str, int]]] = collections.defaultdict(list)
    for kaynak, hedef, aciklama, guc in b.execute(
            """SELECT kaynak, hedef, aciklama, guc FROM bag
                WHERE tur IN ('etkiler', 'belirler', 'bileseni')
                  AND aciklama IS NOT NULL AND aciklama <> ''"""):
        g[kaynak].append((hedef, aciklama, guc or 0))
    return g


def kanal(b: sqlite3.Connection, baslangic: list[str]) -> list[dict] | None:
    """`baslangic` varliklarindan yurt ici bir uca EN KISA yol.

    Doner: [{"kaynak", "hedef", "aciklama", "guc"}, ...] ya da None.

    Genislik-oncelikli arama: ilk bulunan yol en kisasi. Birden fazla
    esit uzunlukta yol varsa ilki aliniyor -- hepsini gostermek okuru
    "hangisi asil kanal" sorusuyla bas basa birakirdi.
    """
    g = _kenarlar(b)
    kuyruk: collections.deque = collections.deque()
    for k in baslangic:
        if k in YEREL_UC:
            # Haber ZATEN yurt ici bir varliga bagli; kanal anlatmaya
            # gerek yok, sayfa bunu dogrudan gosteriyor.
            return None
        kuyruk.append((k, []))
    gorulen = set(baslangic)
    while kuyruk:
        dugum, yol = kuyruk.popleft()
        if len(yol) >= EN_COK_ADIM:
            continue
        for hedef, aciklama, guc in g.get(dugum, ()):
            if hedef in gorulen:
                continue
            adim = yol + [{"kaynak": dugum, "hedef": hedef,
                           "aciklama": aciklama, "guc": guc}]
            if hedef in YEREL_UC:
                return adim
            gorulen.add(hedef)
            kuyruk.append((hedef, adim))
    return None


#: Varlik kodu -> okunur ad. Zincir okura kod degil AD gostermeli.
AD = {
    "FED_FAIZ": "Fed politika faizi (hedef aralık)",
    "US10Y": "ABD 10 yıllık tahvil getirisi",
    "US2Y": "ABD 2 yıllık tahvil getirisi",
    "DXY": "Dolar endeksi",
    "BRENT": "Brent petrol",
    "DGAZ": "Doğal gaz",
    "CDS_TR": "Türkiye CDS primi",
    "USDTRY": "USD/TRY",
    "BIST100": "BIST 100",
    "TCMB_FAIZ": "TCMB politika faizi",
    "TUFE_TR": "TÜFE (yıllık)",
    "CARI_TR": "Cari işlemler dengesi",
    "UFE_TR": "Yİ-ÜFE",
    "ECB_FAIZ": "ECB politika faizi",
    "MOODYS": "Moody's", "FITCH": "Fitch", "SPRATING": "S&P",
    # ULKE KODLARI. Zincirin basi cogu zaman bir ulke oluyor
    # ("IR -> Brent -> Cari islemler") ve sayfada HAM KOD gorunuyordu.
    # Olculdu: 21 sayfada "IR", 8 sayfada "CN" yaziyordu. Okur icin
    # "IR" bir sey ifade etmiyor.
    "IR": "İran", "CN": "Çin", "RU": "Rusya", "US": "ABD",
    "EA": "Avro Bölgesi", "EU": "Avro Bölgesi", "TR": "Türkiye",
    "SA": "Suudi Arabistan", "IL": "İsrail", "UA": "Ukrayna",
    "DIS_TICARET_TR": "Dış ticaret dengesi",
}


def ad(kod: str) -> str:
    return AD.get(kod, kod)
