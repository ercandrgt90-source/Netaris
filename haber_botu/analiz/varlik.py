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
    # "Faiz Oranlarina Iliskin Basin Duyurusu" ve "Para politikasi
    # kararlari" TCMB'nin EN SIK basligi ve hicbiri eslesmiyordu.
    "TCMB_FAIZ": ("politika faizi", "faiz karari", "tcmb faiz",
                  "haftalik repo", "faiz oran", "para politikasi karar",
                  "faiz indirim", "faiz artirim"),
    # "enflasyon" genel; asagidaki BASTIRMA kurali yurt disi haberlerde
    # bunu dusuruyor.
    "TUFE_TR": (" tufe ", "tuketici fiyat", "enflasyon"),
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
    # "ithalat" ONEK: "ithalatci", "ithalatta", "ithalatin" hepsi ayni
    # kalemi anlatiyor. "import" YAZILMADI -- "IMPORTant" icinde
    # eslesiyordu ve haberi sessizce dis ticarete sokuyordu.
    "DIS_TICARET_TR": ("dis ticaret", " ihracat", " ithalat", "disticaret"),
    "ISSIZLIK_TR": ("issizlik", "isgucu", "atil isgucu"),

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
    # " petrol" ONEK olarak araniyor (sonunda bosluk yok): Turkce'de ek
    # aliyor -- "petrolu dusurdu", "petrolun varili", "petrole talep".
    # Sadece "petrol fiyat" arandiginda bunlarin hicbiri eslesmiyordu.
    "BRENT": ("brent", " petrol", "crude", " varil "),
    "WTI": (" wti ", "west texas"),
    "XAU": (" altin ", "altin fiyat", "gram altin", "ons altin", " gold ",
            "altini", "altinin"),
    "XAG": (" gumus ", "gumus fiyat", " silver "),
    "DGAZ": ("dogal gaz", "natural gas", " lng ", "dogalgaz"),
    # " bakir" onek: "bakirda", "bakirin". Sifat "bakir" (el degmemis)
    # ayni yazilir ama ekonomi beslemesinde gecmiyor.
    "XCU": (" bakir", " copper "),

    # --- sektorler ---
    "SEK_BANKA": ("bankacilik", " banka ", " bankalar ", "kredi hacmi"),
    "SEK_ENERJI": ("enerji sektor", "elektrik uretim", " ges ", " res ",
                   "elektrik fiyat"),
    "SEK_OTOMOTIV": ("otomotiv", "otomobil satis", " oto satis "),
    # "otel" tek basina "otelenebilir"e dusuyordu -- bosluklu ve cogul.
    "SEK_TURIZM": ("turizm", " turist ", " oteller ", "konaklama"),
    "SEK_HAVA": ("havacilik", "havayolu", "hava yolu", " thy ",
                 "turk hava yollari", "pegasus"),
    "SEK_PERAKENDE": ("perakende", "market zincir", "magaza satis"),
    "SEK_INSAAT": ("insaat", "konut satis", "muteahhit"),

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
BASTIRILABILIR = ("TUFE_TR", "UFE_TR", "CARI_TR", "TCMB_FAIZ",
                  "DIS_TICARET_TR", "ISSIZLIK_TR")
TURKIYE_ISARETI = (" tcmb ", "turkiye", " turk ", " tuik ", " tl ",
                   " lira ", "bist", " ankara ", " istanbul ", " spk ",
                   " bddk ", "turkiye'")
YABANCI_ISARETI = (" fed ", " ecb ", " abd ", "amerika", " fomc ",
                   "avro bolge", "euro bolge", " cin ", " japonya ",
                   " ingiltere ", "avrupa merkez")

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


def _kodlari_bul(metin: str) -> list[str]:
    if not metin:
        return []
    k = _aranacak(metin)
    bulunan = [kod for kod, kaliplar in KALIPLAR.items()
               if any(p in k for p in kaliplar)]
    # Yurt disi haberde Turkiye gostergelerini dusur.
    if not any(i in k for i in TURKIYE_ISARETI) and \
            any(i in k for i in YABANCI_ISARETI):
        bulunan = [x for x in bulunan if x not in BASTIRILABILIR]
    return bulunan


def bul(b: sqlite3.Connection, baslik: str, ozet: str = "") -> list[Varlik]:
    """Metinde gecen varliklari, GRAFTAKI kayitlariyla dondurur.

    Baslik ONCELIKLI: baslikta gecen varlik haberin konusu, ozette gecen
    yalnizca deginilmis olabilir. Siralama `onem` alanina gore, cunku
    sinir asildiginda birakilacaklar en az onemli olanlar olmali.
    """
    kodlar = _kodlari_bul(baslik)
    for k in _kodlari_bul(ozet):
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
