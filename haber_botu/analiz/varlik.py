"""Haber -> bilgi agi eslemesi.

    haber basligi -> `varlik.kod` -> haber_varlik
                                  -> "bununla ilgili diger gelismeler"
                                  -> "X daha once ne demisti"
                                  -> /varlik/<kod>/ arsiv sayfalari

BU DOSYA YENI VARLIK TANIMLAMAZ
-------------------------------
Varliklarin kendisi `graf_tohum.py`de tanimli ve depodaki `varlik`
tablosunda duruyor: kod, ad, aciklama, seri_kodu, onem. Burada YALNIZCA
"hangi metin hangi koda isaret eder" bilgisi var.

Ayrimin sebebi somut: ilk denemede burada ikinci bir varlik tablosu
tanimlanmisti ve `CREATE TABLE IF NOT EXISTS` sessizce hicbir sey yapmadi
(tablo zaten vardi, ama farkli sutunlarla). Tek kaynak `graf_tohum.py`.
Yeni varlik oraya eklenir, kalibi buraya.

DESENLER BOSLUKLU YAZILIR
-------------------------
Bu projede defalarca yasanan hatanin dersi: kisa kisaltmalar kelime
icinde eslesiyor. Gercekten olculenler:

    "iran"  -> "hazIRANin"     her haziran tarihli haber Iran'a baglanirdi
    "gold"  -> "GOLDman"
    "otel"  -> "OTELenebilir"
    "ges "  -> "charGES "
    "ons "  -> "billiONS "

Metin bosluklarla PAYLANARAK aranir; " iran " artik "haziranin" icinde
eslesmez ama basligin basinda/sonunda eslesir.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def katla(metin: str) -> str:
    return metin.translate(_KATLAMA).lower()


def _aranacak(metin: str) -> str:
    """Katlanmis metni bosluklarla paylar; noktalama da bosluga cevrilir.

    Noktalama bosluga cevriliyor cunku "Fed'in", "TCMB,", "(SPK)" gibi
    yazimlar bosluklu kalibin eslesmesini engelliyordu.

    TIRE DE BOSLUGA CEVRILIYOR. Ilk surumde tire korunmustu ("tarim-disi"
    kalibi icin) ve olculen sonuc suydu:

        "ABD-İran geriliminde yumuşama sinyali petrolü düşürdü"
        -> " abd-iran ... "  -> ne " abd " ne " iran " eslesti

    Yani sayfada Iran gerilimi ile petrol arasindaki yapisal bag --
    graftaki en degerli bagilardan biri -- hic kurulmuyordu. Tire iceren
    kaliplar bosluklu yazildi.
    """
    k = katla(metin)
    k = re.sub(r"[^a-z0-9&/%]+", " ", k)
    return " " + re.sub(r"\s+", " ", k).strip() + " "


#: Gövde kalibi isareti. `"~gumus"` -> "gumus" + Turkce eki.
#:
#: Turkce eklemeli bir dil ve bu iki yonlu hata uretti:
#:
#:   dar yazinca kaciyor : " gumus " kalibi "gumusTE"yi bulmuyor
#:                         " banka " kalibi "bankaSI"yi bulmuyor
#:   genis yazinca tasiyor: "petrol" oneki dogruydu ama "altin" oneki
#:                          "altinDA"yi da yakalar (topragin altinda)
#:
#: Govde kalibi ortasi: kelime BASINDAN eslesiyor, sonuna en fazla
#: `EK_UZUNLUK` harf gelebiliyor. Belirsiz govdeler (altin/altinda)
#: govde kalibi ALMAZ, acik yazim listesiyle verilir.
GOVDE = "~"
EK_UZUNLUK = 7

#: kod -> metin kaliplari. Kodlar `graf_tohum.VARLIKLAR` ile ayni olmali;
#: `dogrula()` bunu sinar.
KALIPLAR: dict[str, tuple[str, ...]] = {
    # --- kurumlar ---
    "FED": (" fed ", "federal rezerv", "federal reserve", " fomc "),
    "ECB": (" ecb ", "avrupa merkez bankasi"),
    "TCMB": (" tcmb ", "turkiye cumhuriyet merkez bankasi", " ppk ",
             "para politikasi kurulu"),
    "TUIK": (" tuik ", "istatistik kurumu"),
    "SPK": (" spk ", "sermaye piyasasi kurulu"),
    "BDDK": (" bddk ", "bankacilik duzenleme"),
    "SEC": (" sec ", "menkul kiymetler ve borsa komisyonu"),
    "EIA": (" eia ", "enerji bilgi idaresi"),
    "OPEC": (" opec ",),

    # --- derecelendirme ve arastirma kuruluslari ---
    # "sp global" ile SP500 karismasin diye " s&p " tek basina YAZILMADI:
    # "S&P 500 rekor kirdi" basligi derecelendirme kurulusuna baglanirdi.
    "MOODYS": ("moody",),
    "FITCH": (" fitch ", "fitch'"),
    "SPRATING": ("s&p global", "standard & poor"),
    "GOLDMAN": ("goldman",),
    "JPMORGAN": ("jp morgan", "jpmorgan"),
    "MORGANSTANLEY": ("morgan stanley",),
    "DEUTSCHE": ("deutsche bank",),
    "IMF": (" imf ", "uluslararasi para fonu"),
    "DUNYABANKASI": ("dunya bankasi", "world bank"),
    "OECD": (" oecd ",),

    # --- kisiler ---
    # Soyisim tek basina riskli: "Ciftci" hem bakan soyismi hem meslek.
    # Bu ucu ayirt edici, yine de tam ad kaliplari once yazildi.
    "POWELL": ("jerome powell", "powell"),
    "KARAHAN": ("fatih karahan", "karahan"),
    "LAGARDE": ("christine lagarde", "lagarde"),

    # --- gostergeler ---
    "FED_FAIZ": ("fed faiz", "fed'in faiz", "federal fonlama"),
    # "~faiz" govdesi: faiz, faizi, faizler, faize, faizin...
    # Tek tek yazildiginda "faiz uyarisi" gibi bir bicim kaciyordu ve
    # vitrin haberinin ANA varligi eksik kaliyordu. Turkiye baglami
    # zorunlu (BASTIRILABILIR), yani "Fed faiz karari" buraya dusmuyor.
    "TCMB_FAIZ": ("~faiz", "politika faizi", "haftalik repo",
                  "para politikasi karar", "para politikasi kurulu", " ppk "),
    # "enflasyon" genel; BASTIRILABILIR oldugu icin Turkiye baglami
    # (baslik ya da kurum) yoksa dusuyor. "Meksika analistleri enflasyon
    # tahminini dusurdu" boyle elendi.
    "TUFE_TR": (" tufe ", "~tufe'", "tuketici fiyat", "~enflasyon"),
    "CPI_US": ("abd tufe", "abd enflasyon", " cpi ", "abd tuketici fiyat"),
    "US10Y": ("10 yillik tahvil", "10 yillik getiri", "on yillik tahvil"),
    "US2Y": ("2 yillik tahvil", "iki yillik tahvil"),
    "EGRI": ("getiri egrisi", "verim egrisi"),
    "DXY": ("dolar endeksi", " dxy "),
    # Tire bosluga cevrildigi icin kaliplar bosluklu yazilir.
    "NFP": ("tarim disi", " nfp ", "nonfarm", "non farm"),
    "CARI_TR": ("cari islem", "cari acik", "cari denge", "cari fazla",
                "odemeler dengesi"),
    "UFE_TR": ("yi ufe", " ufe ", "uretici fiyat"),
    "VIX": (" vix ", "korku endeksi"),
    # "import" YAZILMADI -- "IMPORTant" icinde eslesiyor ve haberi
    # sessizce dis ticarete sokuyordu.
    "DIS_TICARET_TR": ("dis ticaret", "~ihracat", "~ithalat", "~disticaret"),
    "ISSIZLIK_TR": ("~issizlik", "~isgucu", "atil isgucu"),

    # --- piyasalar ---
    "USDTRY": ("usd/try", "dolar/tl", "dolar kuru", "dolar/turk"),
    "EURUSD": ("eur/usd", "euro/dolar", "eurusd"),
    "BIST100": ("bist 100", "bist100", " bist ", "borsa istanbul"),
    "SP500": ("s&p 500", "s&p500", "sp 500", "sp500"),
    "NASDAQ": ("nasdaq", "nasdak"),
    "CDS_TR": (" cds ", "risk primi"),
    "BTC": ("bitcoin", " btc "),
    "ETH": ("ethereum", " eth "),

    # --- emtia ---
    "BRENT": ("~brent", "~petrol", "crude", "~varil"),
    "WTI": (" wti ", "west texas"),
    "XAU": (" altin ", "altin fiyat", "gram altin", "ons altin", " gold ",
            "altini", "altinin"),
    "XAG": ("~gumus", " silver "),
    "DGAZ": ("dogal gaz", "natural gas", " lng ", "dogalgaz"),
    # Sifat "bakir" (el degmemis) ayni yazilir ama ekonomi beslemesinde
    # gecmiyor.
    "XCU": ("~bakir", " copper "),

    # --- sektorler ---
    #
    # "banka" TEK BASINA YAZILMAZ. Olculen yanlis: "Altin ne zaman
    # yukselecek? DEV BANKA yil sonu icin..." haberi bankacilik sektorune
    # baglaniyordu -- oysa haber altin tahmini, bir yatirim bankasinin
    # gorusu. Sektor icin ya sektor kelimesi ya da Turk bankasi adi
    # araniyor; "~bankasi" hem "Is Bankasi"ni hem "Ziraat Bankasi"ni alir.
    "SEK_BANKA": ("~bankacilik", "~mevduat", "kredi hacmi", "~bankalar",
                  "is bankasi", "ziraat bankasi", "vakifbank", "halkbank",
                  "akbank", "garanti bbva", "yapi kredi", "denizbank",
                  "qnb finansbank", "banka karlar", "bankacilik sektor"),
    "SEK_ENERJI": ("enerji sektor", "~elektrik", " ges ", " res ",
                   "~epdk", "dogalgaz zam"),
    "SEK_OTOMOTIV": ("~otomotiv", "~otomobil", "arac satis", "oto satis"),
    # "otel" tek basina "OTELenebilir"e dusuyordu -- govde de degil,
    # acik yazim listesi.
    "SEK_TURIZM": ("~turizm", "~turist", " otel ", " oteller ", "~otelcilik",
                   "~konaklama", "yabanci ziyaretci"),
    "SEK_HAVA": ("~havacilik", "~havayolu", "hava yolu", " thy ",
                 "turk hava yollari", "pegasus", "~havalimani"),
    "SEK_PERAKENDE": ("~perakende", "market zincir", "magaza satis",
                      "~bim ", "~a101", "~sok market"),
    "SEK_INSAAT": ("~insaat", "konut satis", "~muteahhit", "~toki",
                   "konut kredisi"),

    # --- ulkeler ---
    "TR": ("turkiye", " turk ", " turkiye'"),
    "US": (" abd ", "amerika", "washington", "birlesik devletler"),
    "EA": ("avro bolge", "euro bolge", "avrupa birligi", " ab "),
    "CN": (" cin ", "cin'", " pekin ", " china "),
    "RU": ("rusya", " moskova ", " kremlin "),
    # " iran " bosluklu OLMAK ZORUNDA: "haziranin" icinde eslesiyordu ve
    # her haziran tarihli Turkce haber Iran'a baglaniyordu.
    "IR": (" iran ", " iran'", " tahran "),
}

#: Turkiye'ye ozgu gostergeler, yurt disi haberde bastirilir.
#:
#: "Fed enflasyon verisini bekliyor" basliginda "enflasyon" gecer ama
#: kastedilen TUFE degildir. Metinde Turkiye isareti yoksa ve yabanci
#: isaret varsa bu kodlar dusurulur.
#: Turkiye baglami isteyen kodlar -- gostergeler VE sektorler.
#:
#: Sektorler de listede, cunku bunlar Turkiye piyasasinin sektorleri:
#: "ABD'de insaat harcamalari geriledi" haberini Turkiye insaat
#: sektorune baglamak okuru yanlis arsive goturuyordu.
BASTIRILABILIR = (
    "TUFE_TR", "UFE_TR", "CARI_TR", "TCMB_FAIZ", "DIS_TICARET_TR",
    "ISSIZLIK_TR", "BIST100", "USDTRY", "CDS_TR",
    "SEK_BANKA", "SEK_ENERJI", "SEK_OTOMOTIV", "SEK_TURIZM",
    "SEK_HAVA", "SEK_PERAKENDE", "SEK_INSAAT",
)
TURKIYE_ISARETI = ("turkiye", " turk ", " tcmb ", " tuik ", " tl ",
                   " lira ", "bist", " ankara ", " istanbul ", " spk ",
                   " bddk ", " ihracat", " ithalat", " esnaf ", " emekli")
#: Bu kurumlardan gelen haber Turkiye baglami sayilir.
TURK_KURUMLARI = ("tcmb", "tuik", "spk", "bddk", "hazine", "dunya",
                  "anadolu ajansi", " aa ", "trt", "haberturk", "ntv",
                  "bloomberg ht", "ekonomim", "patronlar", "borsa")
#: Baslikta bunlardan biri varsa haber yurt disi sayilir.
YABANCI_ISARETI = (
    " fed ", " ecb ", " abd ", "amerika", " fomc ", "avrupa merkez",
    "avro bolge", "euro bolge", " japonya ", " ingiltere ", " almanya ",
    " fransa ", " italya ", " ispanya ", " meksika ", " brezilya ",
    " hindistan ", " arjantin ", " kanada ", " avustralya ",
    " guney kore ", " rusya ", " cin ", " new york ", " londra ",
    " wall street ", " nasdaq ", " s&p 500 ",
)

#: Bir haberde en fazla kac varlik isaretlensin.
#: Sinirsiz birakildiginda uzun basliklar sekiz on varliga baglaniyor ve
#: "ilgili gelismeler" alakasiz haberlerle doluyor.
EN_COK_VARLIK = 6

SEMA = """
CREATE TABLE IF NOT EXISTS haber_varlik (
  adres          TEXT NOT NULL,
  varlik_kimlik  TEXT NOT NULL,
  PRIMARY KEY (adres, varlik_kimlik)
);
CREATE INDEX IF NOT EXISTS hv_varlik ON haber_varlik(varlik_kimlik);
"""


@dataclass(frozen=True)
class Varlik:
    kimlik: str          # varlik.kod
    ad: str
    tur: str


def dogrula() -> list[str]:
    """Grafta karsiligi olmayan kalip kodlarini dondurur.

    Sessiz kaymayi engelliyor: `graf_tohum.py`de bir kod degistirilirse
    buradaki kalip hicbir seye baglanmaz ve kimse fark etmez.
    """
    try:
        from graf_tohum import VARLIKLAR as _G
    except ImportError:
        return []
    kodlar = {v[0] for v in _G}
    return sorted(k for k in KALIPLAR if k not in kodlar)


@lru_cache(maxsize=512)
def _govde_deseni(govde: str) -> re.Pattern:
    """`~gumus` -> "gumus" + en fazla EK_UZUNLUK harf, kelime sinirinda."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(govde)}[a-z]{{0,{EK_UZUNLUK}}}"
                      rf"(?![a-z0-9])")


def _esliyor(k: str, kalip: str) -> bool:
    if kalip.startswith(GOVDE):
        return _govde_deseni(kalip[1:]).search(k) is not None
    return kalip in k


def _turk_baglami(k: str, kurum: str) -> bool:
    """Metin Turkiye'den mi bahsediyor.

    `kurum` de sayiliyor: "Sektorel Enflasyon Beklentileri (Temmuz 2026)"
    basliginda tek bir Turkiye isareti yok ama TCMB'nin duyurusu. Kurumu
    gormezden gelmek bu duyuruyu TUFE'ye baglamamak demekti.
    """
    if any(i in k for i in TURKIYE_ISARETI):
        return True
    return _aranacak(kurum or "") .strip() != "" and any(
        i in _aranacak(kurum) for i in TURK_KURUMLARI)


def _kodlari_bul(metin: str, kurum: str = "") -> list[str]:
    if not metin:
        return []
    k = _aranacak(metin)
    bulunan = [kod for kod, kaliplar in KALIPLAR.items()
               if any(_esliyor(k, p) for p in kaliplar)]

    # TURKIYE'YE OZGU VARLIKLAR TURKIYE BAGLAMI ISTER.
    #
    # Olculen yanlislar: "Meksika analistleri enflasyon tahminini
    # dusurdu" -> TUFE (Turkiye TUFE'si), "ABD'de insaat harcamalari
    # geriledi" -> Insaat (Turkiye insaat sektoru). Ikisi de okura
    # yanlis arsiv gosteriyordu.
    #
    # Kural: baslikta yabanci isaret varsa dus; yoksa Turkiye baglami
    # (baslik ya da kurum) ara.
    if any(i in k for i in YABANCI_ISARETI) or not _turk_baglami(k, kurum):
        bulunan = [x for x in bulunan if x not in BASTIRILABILIR]
    return bulunan


def bul(b: sqlite3.Connection, baslik: str, ozet: str = "",
        kurum: str = "") -> list[Varlik]:
    """Metinde gecen varliklari, GRAFTAKI kayitlariyla dondurur.

    Baslik ONCELIKLI: baslikta gecen varlik haberin konusu, ozette gecen
    yalnizca deginilmis olabilir. Siralama `onem` alanina gore, cunku
    sinir asildiginda birakilacaklar en az onemli olanlar olmali.
    """
    kodlar = _kodlari_bul(baslik, kurum)
    for k in _kodlari_bul(ozet, kurum):
        if k not in kodlar:
            kodlar.append(k)
    if not kodlar:
        return []
    yer = ",".join("?" * len(kodlar))
    r = b.execute(
        f"SELECT kod, ad, tur FROM varlik WHERE kod IN ({yer})"
        " ORDER BY onem DESC", kodlar).fetchall()
    return [Varlik(x[0], x[1], x[2]) for x in r][:EN_COK_VARLIK]


def sema_kur(b: sqlite3.Connection) -> None:
    b.executescript(SEMA)


def yaz(b: sqlite3.Connection, adres: str, varliklar: list[Varlik]) -> int:
    """Haber-varlik bagini yazar. Yeniden calistirmak gecmisi bozmaz."""
    sema_kur(b)
    n = 0
    for v in varliklar:
        imlec = b.execute(
            "INSERT OR IGNORE INTO haber_varlik (adres, varlik_kimlik)"
            " VALUES (?, ?)", (adres, v.kimlik))
        n += imlec.rowcount
    return n


#: Gercek sayfasi olan haber. "/haber/" YER TUTUCU -- haber hatti site
#: adresini bilmediginden onu yaziyor, tam adres site kurulurken olusuyor.
#: `_%` en az bir karakter daha istiyor, yani yer tutucuyu eliyor.
_YAYIMLI = "h.yayimlandi = 1 AND h.yayin_yolu LIKE '/haber/_%'"


def ilgili_haberler(b: sqlite3.Connection, adres: str,
                    en_fazla: int = 5) -> list[dict]:
    """Ayni varliklari paylasan, yayimlanmis diger haberler.

    Paylasilan varlik sayisina gore siralanir: iki ortak varligi olan
    haber, birini paylasandan daha ilgilidir.
    """
    try:
        r = b.execute(
            f"""
            SELECT h.baslik_tr, h.yayin_yolu, h.tarih, h.kurum,
                   COUNT(*) AS ortak
            FROM haber_varlik hv
            JOIN haber_varlik hv2 ON hv2.varlik_kimlik = hv.varlik_kimlik
            JOIN haber h ON h.adres = hv2.adres
            WHERE hv.adres = ? AND hv2.adres != ? AND {_YAYIMLI}
            GROUP BY h.adres
            ORDER BY ortak DESC, h.tarih DESC
            LIMIT ?
            """, (adres, adres, en_fazla)).fetchall()
    except sqlite3.Error:
        return []
    return [{"baslik": x[0], "yol": x[1], "tarih": x[2],
             "kurum": x[3], "ortak": x[4]} for x in r]


def varlik_gecmisi(b: sqlite3.Connection, kod: str,
                   en_fazla: int = 30) -> list[dict]:
    """Bir varlikla ilgili yayimlanmis haberler, yeniden eskiye."""
    try:
        r = b.execute(
            f"""
            SELECT h.baslik_tr, h.yayin_yolu, h.tarih, h.kurum
            FROM haber_varlik hv JOIN haber h ON h.adres = hv.adres
            WHERE hv.varlik_kimlik = ? AND {_YAYIMLI}
            ORDER BY h.tarih DESC LIMIT ?
            """, (kod, en_fazla)).fetchall()
    except sqlite3.Error:
        return []
    return [{"baslik": x[0], "yol": x[1], "tarih": x[2], "kurum": x[3]}
            for x in r]


def kunye(b: sqlite3.Connection, kod: str) -> dict | None:
    """Varligin graftaki tanimi -- varlik sayfasinin ust bolumu."""
    r = b.execute(
        "SELECT kod, ad, ad_en, tur, aciklama, seri_kodu, onem"
        " FROM varlik WHERE kod = ?", (kod,)).fetchone()
    if not r:
        return None
    return {"kod": r[0], "ad": r[1], "ad_en": r[2], "tur": r[3],
            "aciklama": r[4], "seri_kodu": r[5], "onem": r[6]}


def _basamak(deger: float) -> int:
    """Buyuklukten ondalik basamak. Sabit basamak kullanildiginda
    47,5432 ile 119,70 ayni sayfada ya asiri ya yetersiz hassasiyetle
    cikiyordu."""
    m = abs(deger)
    if m >= 1000:
        return 0
    if m >= 100:
        return 2
    if m >= 1:
        return 2
    return 4


def _sayi(deger: float, birim: str) -> str:
    s = f"{deger:,.{_basamak(deger)}f}"
    # Turkce bicim: binlik nokta, ondalik virgul.
    s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"%{s}" if birim == "%" else s


def seri_ozet(b: sqlite3.Connection, seri_kodu: str | None,
              gun: int = 60) -> dict | None:
    """Varligin bagli oldugu serinin son degeri ve degisimi.

    Iki tabloya birden bakiyor: makro gozlemler `gosterge`de, gunluk
    kapanislar `fiyat`ta. Varlik hangisinde varsa oradan okunuyor.

    Seri kodu yoksa ya da veri gelmezse None -- sayfada bos bir kutu
    basmaktansa bolumu hic basmamak dogru. (Gumusun serisi yok; "XAG"
    yazip bos donmek, veri varmis gibi gostermekti.)
    """
    if not seri_kodu:
        return None
    satirlar = []
    birim = ""
    try:
        satirlar = b.execute(
            "SELECT tarih, deger, birim FROM gosterge WHERE kod=?"
            " ORDER BY tarih DESC LIMIT ?", (seri_kodu, gun)).fetchall()
        if satirlar:
            birim = satirlar[0][2] or ""
        else:
            satirlar = b.execute(
                "SELECT tarih, kapanis, '' FROM fiyat WHERE sembol=?"
                " ORDER BY tarih DESC LIMIT ?", (seri_kodu, gun)).fetchall()
    except sqlite3.Error:
        return None
    if len(satirlar) < 2:
        return None

    son, onceki = satirlar[0], satirlar[1]
    d_son, d_onceki = float(son[1]), float(onceki[1])

    fark = d_son - d_onceki
    yon = "artis" if fark > 0 else ("azalis" if fark < 0 else "yatay")

    if fark == 0:
        # "+0 bp" teknik olarak dogru ama okunmuyor.
        degisim = "değişmedi"
    elif birim == "%":
        # ORAN SERILERINDE DEGISIM PUAN CINSINDEN.
        # %31,75'ten %31,40'a inis yuzde degil, 35 baz puanlik
        # gerilemedir; yuzde yazmak olcuyu bozar.
        degisim = f"{round(fark * 100):+d} bp"
    elif d_son <= 0 or d_onceki <= 0:
        # DENGE SERILERINDE YUZDE ANLAMSIZ.
        # Cari islemler dengesi isaret degistirebilen bir AKIM. -5.600'den
        # -1.459'a gecisi "−%74" diye yazmak, acigin DARALDIGI bir ayi
        # dusus rengiyle gostermek olurdu; okur tersini anlar. Fark kendi
        # biriminde yaziliyor.
        degisim = f"{fark:+,.0f}".replace(",", ".")
    else:
        y = fark / d_onceki * 100
        degisim = f"{'+' if y >= 0 else '−'}%{abs(y):.1f}".replace(".", ",")

    return {
        "deger": _sayi(d_son, birim),
        "birim": birim if birim != "%" else "",
        "degisim": degisim,
        "yon": yon,
        "tarih": son[0],
        # Kivilcim icin eskiden yeniye.
        "seri": [float(s[1]) for s in reversed(satirlar)],
        "gozlem": len(satirlar),
    }


def baglar(b: sqlite3.Connection, kod: str) -> list[dict]:
    """Varligin yapisal baglari -- "bu neyi etkiler, neye baglidir".

    Bu, sitenin haber toplamaktan ayrilan yeri: iliski bilgisi birikimle
    olusuyor. `dayanak` alani "yapisal / veri / kaynak" ayrimini tasiyor
    ve sayfada GORUNUR kaliyor -- muhasebe kimligi ile gozlem ayni sey
    degil.
    """
    try:
        r = b.execute(
            """
            SELECT g.kaynak, g.hedef, g.tur, g.aciklama, g.dayanak, g.guc,
                   vk.ad, vh.ad
            FROM bag g
            LEFT JOIN varlik vk ON vk.kod = g.kaynak
            LEFT JOIN varlik vh ON vh.kod = g.hedef
            WHERE g.kaynak = ? OR g.hedef = ?
            ORDER BY g.guc DESC
            """, (kod, kod)).fetchall()
    except sqlite3.Error:
        return []
    cikti = []
    for x in r:
        kaynak, hedef = x[0], x[1]
        cikti.append({
            "kaynak": kaynak, "hedef": hedef, "tur": x[2],
            "aciklama": x[3] or "", "dayanak": x[4], "guc": x[5],
            "kaynak_ad": x[6] or kaynak, "hedef_ad": x[7] or hedef,
            # Sayfa "bu varliktan cikan" ve "buna gelen" baglari ayri
            # gosteriyor; yon bilgisi burada hesaplaniyor.
            "yon": "cikan" if kaynak == kod else "gelen",
        })
    return cikti
