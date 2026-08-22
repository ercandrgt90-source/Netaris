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

#: ULKE -> O ULKENIN KENDI PIYASA UCLARI.
#:
#: NEDEN EKLENDI
#: -------------
#: Kanal yalnizca `YEREL_UC`e, yani Turkiye'ye cikiyordu. Bir Alman
#: enflasyon haberinin gidecegi tek yer USDTRY ya da BIST100'du ve
#: okurun ilk sorusu -- "bu Avrupa'da neyi etkiler" -- cevapsiz
#: kaliyordu.
#:
#: Yerel bakis yanlis degil, Turk okur icin gerekli. Ama TEK bakis
#: olmasi, kuresel bir olayi dar bir mercekten anlatmak demekti.
#:
#: Sira artik: ONCE olayin kendi piyasasi, SONRA buraya aktarim.
#: Ikisi ayri blok olarak gosteriliyor (bkz. `haber.html`), cunku
#: birbirine karistirilirsa "Almanya enflasyonu USD/TRY'yi belirler"
#: gibi okunur -- oysa ikisi ayri iki cumle.
#: ANAHTARLAR `baglam` SOZLUGUYLE AYNI OLMAK ZORUNDA.
#: Ilk yazimda Euro Bolgesi icin "EA" kullandim; `baglam.KURUM_ULKE`
#: ise "EU" doduruyor. Sonuc: `uclar("EU")` BOS donuyordu ve butun
#: Avrupa kanali HIC ATESLENMIYORDU -- yeni yazilmis bir ozellik,
#: sessizce olu. `test_yerel_etki` iki sozlugun ortustugunu siniyor.
PIYASA_UCLARI: dict[str, frozenset[str]] = {
    # "DE" AYRI BIR GIRDI DEGIL: `baglam` "almanya" isaretini "EU"ya
    # baglıyor ve Euro Bolgesi uclari DAX ile Bund'u zaten iceriyor.
    # Ilk yazimda ayri bir "DE" girdisi vardi ve HIC ULASILMIYORDU --
    # yeni eklenen sozluk sinamasi yakaladi.
    "EU": frozenset({"DAX", "STOXX", "DE10Y", "EURUSD", "ECB_FAIZ"}),
    "US": frozenset({"SP500", "NASDAQ", "US10Y", "US2Y", "DXY"}),
    "JP": frozenset({"NIKKEI", "USDJPY", "JGB", "BOJ_FAIZ"}),
    "GB": frozenset({"FTSE", "GBPUSD", "BOE_FAIZ"}),
    "CN": frozenset({"CN_BUYUME", "XCU", "BRENT"}),
    "TR": YEREL_UC,
}


def uclar(ulke: str | None) -> frozenset[str]:
    """Ulkenin piyasa uclari; tanimsizsa BOS.

    Bos donmesi bilincli: tanimadigimiz bir ulke icin Turkiye ucuna
    zorlamak, o haberi olmadigi bir sey hakkinda anlatmak olurdu.
    Kanal gosterilmemesi, yanlis kanal gostermekten iyidir.
    """
    return PIYASA_UCLARI.get((ulke or "").upper(), frozenset())

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


def kanal(b: sqlite3.Connection, baslangic: list[str],
          hedefler: frozenset[str] | None = None,
          kendi_piyasasi: bool = False) -> list[dict] | None:
    """`baslangic` varliklarindan bir HEDEF uca EN KISA yol.

    `hedefler` verilmezse Turkiye uclari kullaniliyor -- eski cagri
    bicimi bozulmasin diye. Yeni cagrilar hedefi ACIKCA veriyor:
    Alman haberi Alman piyasasina, Japon haberi Japon piyasasina.

    Doner: [{"kaynak", "hedef", "aciklama", "guc"}, ...] ya da None.

    Genislik-oncelikli arama: ilk bulunan yol en kisasi. Birden fazla
    esit uzunlukta yol varsa ilki aliniyor -- hepsini gostermek okuru
    "hangisi asil kanal" sorusuyla bas basa birakirdi.
    """
    if hedefler is None:
        hedefler = YEREL_UC
    if not hedefler:
        return None

    # KENDI PIYASASINDA BASLANGIC HEDEF SAYILMAZ.
    #
    # Asagidaki kisa devre ("haber zaten hedefe bagli, kanal gereksiz")
    # hedef TURKIYE iken dogruydu: yurt ici bir haberde Turkiye
    # verisi zaten sayfanin kendisinde.
    #
    # Kendi piyasasinda YANLIS oluyor. "BoJ faizi artirdi" haberinde
    # baslangic `BOJ_FAIZ` ve o da Japonya uclarindan biri; kural
    # devreye girince okurun en cok istedigi zincir -- BoJ faizi ->
    # USD/JPY -> Nikkei -- HIC gosterilmiyordu.
    #
    # Cozum baslangici hedeften cikarmak: zincir kendi uzerine
    # donmuyor ama piyasanin geri kalanina ulasabiliyor.
    if kendi_piyasasi:
        hedefler = hedefler - set(baslangic)
        if not hedefler:
            return None

    g = _kenarlar(b)
    kuyruk: collections.deque = collections.deque()
    for k in baslangic:
        if not kendi_piyasasi and k in hedefler:
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
            if hedef in hedefler:
                return adim
            gorulen.add(hedef)
            kuyruk.append((hedef, adim))
    return None


#: Varlik kodu -> okunur ad. Zincir okura kod degil AD gostermeli.
AD = {
    # --- kuresel piyasalar ---
    "ECB": "Avrupa Merkez Bankası",
    "CN": "Çin",
    "ECB_FAIZ": "ECB mevduat faizi",
    "DAX": "DAX",
    "STOXX": "Euro Stoxx 50",
    "DE10Y": "Almanya 10 yıllık tahvil getirisi",
    "EURUSD": "EUR/USD",
    "EA_TUFE": "Euro Bölgesi TÜFE",
    "BOJ_FAIZ": "BoJ politika faizi",
    "NIKKEI": "Nikkei 225",
    "USDJPY": "USD/JPY",
    "JGB": "Japonya 10 yıllık tahvil getirisi",
    "BOE_FAIZ": "BoE politika faizi",
    "FTSE": "FTSE 100",
    "GBPUSD": "GBP/USD",
    "CN_BUYUME": "Çin büyümesi",
    "SP500": "S&P 500",
    "NASDAQ": "Nasdaq",
    "XCU": "Bakır",

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
