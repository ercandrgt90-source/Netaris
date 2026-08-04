"""Haber beslemeleri -- resmi kurumlar + Turk ekonomi yayinlari.

UC KAYNAK SINIFI
----------------
resmi_yerli  TCMB. Turkce, kamu belgesi, serbestce aktarilir.
resmi_yabanci Fed, ECB, SEC, EIA. Kamu belgesi; ceviri gerekir.
ticari       AA, Dunya, Ekonomim, BloombergHT, NTV, Haberturk, CNN Turk,
             TRT, Ekonomist, Investing. Telif sahibi haber kuruluslari.

TICARI KAYNAKLARDA KUNYE ZORUNLU
--------------------------------
RSS yayimlamak "basligi al, ozetle, bana baglanti ver" davetidir; "kaynagi
sil, kendi icerigin gibi sun" degil. Bir kurumun muhabirinin urettigi haberi
kunyesiz aktarmak FSEK kapsaminda da, kuruluslarin kullanim sartlarinda da
karsiligi olan bir sey. Bu yuzden `ticari=True` olan her ogede kaynak adi ve
baglanti SAKLANIR ve sayfada gosterilir.

Bizim ozgun katkimiz basligin kendisi degil, "piyasalarda neyi etkiler"
bolumu. O tamamen bize ait ve `gundem_yorum.py` uretir.

TICARI OGE HAK EDEREK GIRER
---------------------------
Resmi beslemede her sey ekonomidir; varsayilan konu yeter. Ticari beslemede
degil -- olculdu: "ekonomi" beslemelerinde Super Loto sonuclari, antik kent
kazisi, spiker istifasi ve savas kayip haberleri cikti. Bu yuzden ticari
ogede POZITIF eslesme sarti var: `konu_bul` bir ekonomi konusu bulamazsa oge
alinmaz. Varsayilana dusurmek, gundemin cop kutusuna donmesi demekti.

BAYAT OGE
---------
Bazi yayinlar arama motoru icin surekli guncellenen sayfalari beslemede
tutuyor -- "Petrol fiyatlari 25 Mayis" agustosta hala geliyordu. Ticari
ogelerde GECERLILIK_GUN'den eski olanlar aliniyor degil.

AYNI HABER, BES KAYNAK
----------------------
Turist harcamasi haberi AA, Dunya, Ekonomim ve TRT'de ayni gun ayri
basliklarla cikti. Adrese gore tekilleme bunu yakalamaz. Baslik imzasina
gore ikinci bir tekilleme var; Turkce'nin ekleri yuzunden kelimeler
govdeye kirpilarak karsilastiriliyor ("turistler" ve "turistlerden" ayni).
"""

from __future__ import annotations

import concurrent.futures as _cf
import html
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

BASLIKLAR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
ZAMAN_ASIMI = 25.0

#: Ticari ogelerde bu yastan eski olanlar alinmaz.
GECERLILIK_GUN = 7

_TCMB = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR"
         "/Bottom+Menu/Diger/RSS/")

#: (kod, kisa ad, tam ad, adres, varsayilan konu, dil, ticari)
#:
#: SIRA EDITORYALDIR. Ayni haber birden fazla kaynakta oldugunda listede
#: ONCE gelen kaynak tutulur: once resmi kurum, sonra ekonomiye adanmis
#: yayinlar, en sonda genel yayinlarin ekonomi servisi.
#:
#: Varsayilan konu `foto.KONU_ARAMA` anahtarlarindan biri OLMAK ZORUNDA --
#: yoksa habere fotograf secilemez. Test bunu dogruluyor.
BESLEMELER = (
    # --- Resmi, yerli ---
    ("TCMB_BASIN", "TCMB", "Türkiye Cumhuriyet Merkez Bankası",
     _TCMB + "Basin+Duyurulari", "Para politikası", "tr", False),
    ("TCMB_PPK", "TCMB", "Türkiye Cumhuriyet Merkez Bankası",
     _TCMB + "PPK+Kararlari", "Para politikası", "tr", False),
    ("TCMB_VERI", "TCMB", "Türkiye Cumhuriyet Merkez Bankası",
     _TCMB + "Veriler", "Para politikası", "tr", False),
    ("TCMB_KONUSMA", "TCMB", "Türkiye Cumhuriyet Merkez Bankası",
     _TCMB + "Baskanin+Konusmalari", "Para politikası", "tr", False),
    ("TCMB_YAYIN", "TCMB", "Türkiye Cumhuriyet Merkez Bankası",
     _TCMB + "Yayinlar", "Para politikası", "tr", False),

    # --- Resmi, yabanci ---
    ("FED_PARA", "Fed", "Federal Reserve",
     "https://www.federalreserve.gov/feeds/press_monetary.xml",
     "Para politikası", "en", False),
    ("FED_BASIN", "Fed", "Federal Reserve",
     "https://www.federalreserve.gov/feeds/press_all.xml",
     "Düzenleme", "en", False),
    ("ECB", "ECB", "Avrupa Merkez Bankası",
     "https://www.ecb.europa.eu/rss/press.html", "Para politikası", "en", False),
    ("SEC", "SEC", "ABD Menkul Kıymetler ve Borsa Komisyonu",
     "https://www.sec.gov/news/pressreleases.rss", "Düzenleme", "en", False),
    ("EIA", "EIA", "ABD Enerji Bilgi İdaresi",
     "https://www.eia.gov/rss/todayinenergy.xml", "Enerji", "en", False),

    # --- Ticari, ekonomiye adanmis ---
    ("AA_EKO", "AA", "Anadolu Ajansı",
     "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
     "Şirket haberleri", "tr", True),
    ("DUNYA", "Dünya", "Dünya Gazetesi",
     "https://www.dunya.com/rss?dunya-ekonomi",
     "Şirket haberleri", "tr", True),
    ("EKONOMIM", "Ekonomim", "Ekonomim",
     "https://www.ekonomim.com/rss", "Şirket haberleri", "tr", True),
    ("BLOOMBERGHT", "BloombergHT", "Bloomberg HT",
     "https://www.bloomberght.com/rss", "Şirket haberleri", "tr", True),
    ("EKONOMIST", "Ekonomist", "Ekonomist",
     "https://www.ekonomist.com.tr/rss", "Şirket haberleri", "tr", True),
    ("INVESTING", "Investing", "Investing.com Türkiye",
     "https://tr.investing.com/rss/news_14.rss", "Borsa", "tr", True),
    ("INVESTING_GN", "Investing", "Investing.com Türkiye",
     "https://tr.investing.com/rss/news.rss", "Borsa", "tr", True),

    # --- Ticari, genel yayinlarin ekonomi servisi ---
    ("TRT_EKO", "TRT Haber", "TRT Haber",
     "https://www.trthaber.com/ekonomi_articles.rss",
     "Şirket haberleri", "tr", True),
    ("NTV_EKO", "NTV", "NTV",
     "https://www.ntv.com.tr/ekonomi.rss", "Şirket haberleri", "tr", True),
    ("HABERTURK_EKO", "Habertürk", "Habertürk",
     "https://www.haberturk.com/rss/ekonomi.xml",
     "Şirket haberleri", "tr", True),
    ("CNNTURK_EKO", "CNN Türk", "CNN Türk",
     "https://www.cnnturk.com/feed/rss/ekonomi/news",
     "Şirket haberleri", "tr", True),
    ("MILLIYET_EKO", "Milliyet", "Milliyet",
     "https://www.milliyet.com.tr/rss/rssnew/ekonomirss.xml",
     "Şirket haberleri", "tr", True),
    ("SABAH_EKO", "Sabah", "Sabah",
     "https://www.sabah.com.tr/rss/ekonomi.xml",
     "Şirket haberleri", "tr", True),
)


#: Turkce harfleri ASCII karsiligina indirir.
#:
#: DIKKAT -- once `translate`, SONRA `lower()`. Ters sirada "İ" bozulur:
#: Python `"İ".lower()` icin iki kod noktasi ("i" + birlesen nokta) uretir
#: ve tablodaki "İ" anahtarina artik uymaz. Baslik da eslesmez.
_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _katla(metin: str) -> str:
    return metin.translate(_KATLAMA).lower()


#: GURULTU -- ticari beslemelerde cikan, ekonomi disi ogeler.
#:
#: Cogu zaten pozitif eslesme sartina takilip eleniyor. Buradakiler o sarti
#: gecebilecek olanlar: icinde ekonomi kelimesi gecen ama haber degeri
#: ekonomik olmayan basliklar ("Musk yapay zekayla film cekecek").
GURULTU_ISARETLERI = (
    # sans oyunlari -- CNN Turk'un ekonomi beslemesinden geliyor
    "loto", "sans topu", "sayisal", "cekilis sonuc", "milli piyango",
    "iddaa", "at yarisi", "ganyan",
    # spor
    "super lig", "maci", "fikstur", "transfer bombasi", "gol krali",
    "sampiyonluk", "derbi",
    # magazin, kultur, yasam
    "spiker", "dizi", "belgesel", "sinema", "konser", "sanatci",
    "antik kent", "muze", "arkeolo", "burc", "fal", "yemek tarifi",
    "saglik durumu", "kaza gecirdi", "vefat etti", "hava durumu",
    "namaz vakti", "bayram tatili kac gun",
    # catisma/kayip haberleri -- ekonomi beslemelerine dusuyor
    "olduruldu", "oldurdu", "yarali", "sehit", "cenaze", "patlama",
    "saldirisinda", "bombardiman",
    # trafik/yerel
    "trafige kapali", "yol calismasi",
)

#: Baslikta gecen anahtar sozcuklerden konu cikarimi.
#:
#: SIRA = OZGULLUK. Ustteki kazanir, o yuzden en ozgul konu en ustte
#: olmali. Olculdu, sira yanlisken cikanlar:
#:
#:   "Turistler ... 6 milyar DOLAR harcadi"      -> Doviz  (Turizm olmali)
#:   "Yillik IHRACAT 278,6 milyar DOLARla"       -> Doviz  (Dis ticaret)
#:   "SSK ve BAG-KUR emeklilerinin zammi"        -> Doviz  ("kur " eslesti)
#:
#: Sebep ayni: "dolar" ve "kur" neredeyse her ekonomi basliginda OLCU
#: BIRIMI olarak geciyor, konu olarak degil. Bu yuzden Doviz asagida
#: duruyor ve isaretleri daraltildi -- yalin "dolar" ve "kur " YOK,
#: yalnizca paranin kendisinin konu oldugu kaliplar var ("dolar endeksi",
#: "doviz kuru"). Konu bulunamayan ticari oge zaten alinmiyor; yanlis
#: siniflandirmaktansa almamak dogru.
#:
#: Isaretler KATLANMIS yazilir -- "enflasyon" evet, "fiyat gelişmeleri"
#: hayir. Diakritikli bir isaret hicbir zaman eslesmez ve hatayi sessizce
#: yapar: konu varsayilana duser, alakasiz fotograf secilir.
KONU_ISARETLERI = (
    ("Para politikası", (
        "para politikasi", "ppk", "politika faizi", "faiz orani",
        "faiz oranlar", "faizi sabit", "faizde indirim", "faiz indirim",
        "faiz artir", "zorunlu karsilik", "reeskont", "merkez bankasi",
        # "faiz karari" ve " tcmb " listede HIC YOKTU. "TCMB faiz kararini
        # acikladi" basligi bu yuzden hicbir zaman para politikasi
        # sayilmiyordu -- kurumun en onemli duyurusu, en temel konusuna
        # dusmuyordu. Testle yakalandi.
        "faiz karari", "faiz kararlar", " tcmb ", "tcmb'", "tcmb’",
        # Faiz haberi her zaman "karar" kelimesiyle gelmiyor; degerlendirme
        # ve beklenti haberleri de bu konuya girer.
        "faiz uyari", "faiz beklenti", "faiz patika", "faiz gorunum",
        "indirim beklentisi", "sikilastirma", "gevseme",
        "fomc", "monetary policy", "interest rate", "federal funds",
        "discount rate", "policy decision", "governing council",
        "monetary", "rate decision",
    )),
    ("Enflasyon", (
        "enflasyon", "fiyat gelismeleri", "tufe", "ufe", "fiyat endeksi",
        "hayat pahalilig", "uretici fiyat", "fiyati en cok artan",
        # "zam orani" BILEREK yok: kira zammi, maas zammi ve elektrik
        # zammi ayri konular. Yalin haliyle uc konuyu birden calardi.
        "inflation", "cpi", "price index", "deflation",
    )),
    ("İstihdam ve ücret", (
        "issizlik", "istihdam", "asgari ucret", "emekli", "maas",
        "isten cikar", "is piyasasi", "sendika", "toplu sozlesme",
        "bag-kur", "ssk", "sgk", "kidem tazminat", "ikramiye",
        "unemployment", "employment", "wage", "labor market", "layoff",
    )),
    ("Konut ve kira", (
        # "rent" YALIN YAZILMAZ -- "B-RENT" petrolu icinde eslesiyor ve
        # enerji yazisini konut haberi yapiyordu. Olculdu.
        "konut", "kira", "emlak", "insaat", "ipotek", "tapu", "mortgage",
        "housing", " rent ", "rental", "construction",
    )),
    ("Tarım ve gıda", (
        # "ciftci" YOK -- Tarim ve Orman Bakani'nin soyadi Ciftci ve
        # bakanin uyusturucu operasyonu aciklamasini tarim haberi yapti.
        "tarim", "hasat", "rekolte", "bugday", "pamuk", "findik", "gida",
        "tarsim", "hububat", "seker pancar", "tohum", "gubre", " yem ",
        "agriculture", "harvest", "grain", "food price",
    )),
    ("Turizm", (
        # "otel" YALIN YAZILMAZ -- "ÖT-EL-enebilir" icinde eslesiyor ve
        # Goldman'in faiz degerlendirmesini turizm haberi yapiyordu.
        # Olculdu; " otel" de yetmez, cunku o kelimeden once bosluk var.
        "turizm", "turist", " otel ", "oteli ", "otelde", "oteller",
        "otelcilik", "havayolu", "yolcu sayisi", "konaklama",
        "tourism", "tourist",
    )),
    # Enerji, Dis ticaret'in USTUNDE: "petrol ithalati" once enerji
    # haberidir. Ters sirada EIA'nin "crude oil imports" haberi Dis
    # ticaret'e dusuyordu.
    ("Enerji", (
        "enerji", "petrol", "brent", " wti ", "varil", "opec",
        "dogal gaz", "elektrik", "akaryakit", "rafineri", " ges ", " res ",
        "yenilenebilir", "tpao", "botas", "yeka", "santral", " lng ",
        "benzin", "motorin", "kwh",
        "oil", "crude", "petroleum", "natural gas", "energy",
        "electricity", "renewable",
    )),
    ("Dış ticaret", (
        "ihracat", "ithalat", "dis ticaret", "cari acik", "cari islem",
        "gumruk", "tarife", "ticaret acig", "ticaret fazla",
        # "import"/"export" YALIN HALDE YAZILMAZ -- "important" icinde
        # eslesiyor. Cogul bicimler boyle bir kelimenin icinde gecmiyor.
        "exports", "imports", "trade deficit", "tariff",
    )),
    ("Kripto varlıklar", (
        "kripto", "bitcoin", "ethereum", "stablecoin", "dijital turk lira",
        "crypto", "digital asset",
    )),
    # DIKKAT -- yalin "altin" ve "gold" YAZILMAZ. Olculdu:
    #   "toprağın ALTINDA kalan heykel" -> Altin      ("altinda")
    #   "GOLDMAN Sachs hisse onerisi"   -> Altin      ("goldman")
    # "altinda" Turkce'nin en sik kelimelerinden biri; yalin haliyle
    # arkeoloji haberini emtia haberi yapiyordu.
    ("Altın ve emtia", (
        " altin ", "altin fiyat", "altin piyasa", "gram altin",
        "ons altin", "kulce altin", "altinin ", "gumus", " ons ",
        "emtia", "bakir", "celik fiyat", "bugday fiyat",
        " gold ", "gold price", "silver", "commodity",
    )),
    # Doviz, Borsa'nin USTUNDE: "endeks" ikisinde de gecebiliyor ve
    # "Dolar ENDEKSINDE yon asagi dondu" Borsa'ya dusuyordu. Doviz
    # isaretleri dar oldugu icin ustte durmasi Borsa'dan bir sey calmaz.
    ("Döviz", (
        "doviz kur", "dolar kur", "dolar endeksi", "dolar/tl", "usd/try",
        "eur/usd", "dolar neden", "kurda ", "kur artis", "parite",
        "sterlin", "swap hatti", "doviz piyasas", "doviz rezerv",
        "exchange rate", "dollar index",
    )),
    ("Borsa", (
        "borsa", "bist", "endeks", "hisse", "halka arz", "seans",
        "piyasalar", "portfoy yonetim", "yatirim fonu",
        "stock", "equity", "shares",
    )),
    ("Vergi ve kamu maliyesi", (
        "vergi", "butce", "hazine ihale", "borclanma", "tahvil ihrac",
        "kamu maliyes", "mali kural", "tesvik", "destek paketi",
        "tax", "budget", "fiscal", "treasury",
    )),
    ("Bankacılık", (
        "banka", "kredi", "mevduat", "rezerv", "likidite",
        "odemeler dengesi", "finansal hesap", "finansal istikrar",
        "bddk", "katilim banka",
        "banking", "capital requirement", "stress test", "basel",
        "deposit", "supervis",
    )),
    ("Piyasa düzenlemesi", (
        "menkul kiymet", "sermaye piyasa", " spk ", " kap ", "teblig",
        "rekabet kurumu", "birlesme onay", "satin alma anlasmasi",
        "securities", "disclosure", "enforcement", "fraud", "investor",
        "market structure", "trading",
    )),
    ("Şirket haberleri", (
        "bilanco", "net kar", "net zarar", "ciro", "faaliyet kari",
        "temettu", "sermaye artirim", "yatirim karari", "fabrika",
        "uretim tesisi", "ihale kazandi", "sozlesme imzala",
        "earnings", "profit", "revenue", "acquisition", "merger",
    )),
)


@dataclass(frozen=True)
class Haber:
    kaynak_kodu: str
    kurum: str        # kisa ad -- rozetlerde
    kurum_tam: str    # tam ad -- kaynak kutusunda
    baslik: str
    adres: str
    ozet: str
    tarih: str          # ISO, cozulemezse bos
    konu: str
    dil: str = "en"     # "tr" ise ceviri katmanina hic ugramaz
    ticari: bool = False  # True ise kunye ve baglanti ZORUNLU

    @property
    def tarih_gorunur(self) -> str:
        aylar = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
        try:
            d = datetime.strptime(self.tarih, "%Y-%m-%d")
        except ValueError:
            return self.tarih
        return f"{d.day} {aylar[d.month - 1]} {d.year}"


def _metin(ham: str) -> str:
    """CDATA, HTML etiketi ve fazla bosluktan arindirir."""
    ham = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", ham, flags=re.S)
    ham = re.sub(r"<[^>]+>", " ", ham)
    return re.sub(r"\s+", " ", html.unescape(ham)).strip()


_TARIH_BICIMLERI = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)

#: TCMB tarihleri Turkce yazar: "30 Tem 2026 14:00:00".
#: `strptime` bunu HICBIR bicimle cozemez -- %b sistemin diline bagli ve
#: sunucuda Ingilizce. Cozulemeyince tarih bos kaliyor, duyuru "tarihsiz"
#: sayilip listenin en sonuna dusuyordu: TCMB'nin dunku karari Fed'in bes
#: gun onceki duyurusunun altinda kaliyor demek.
#:
#: Anahtarlar katlanmis ve UC harfe kirpilmis. Boylece hem kisaltma
#: ("Şub" -> "sub") hem tam ad ("Şubat" -> "sub") ayni girise dusuyor.
_TURKCE_AYLAR = {
    "oca": 1, "sub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6,
    "tem": 7, "agu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12,
}


def _tarih_coz(ham: str) -> str:
    """RSS tarih bicimlerini ISO'ya cevirir. Cozulemezse BOS doner.

    Bos donmek onemli: cozulemeyen tarihe bugunu yazmak, eski bir duyuruyu
    bugun cikmis gibi gostermek olurdu.
    """
    ham = ham.strip()
    for bicim in _TARIH_BICIMLERI:
        try:
            return datetime.strptime(ham, bicim).date().isoformat()
        except ValueError:
            continue

    # "30 Tem 2026 14:00:00" -- TCMB
    m = re.match(r"(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})", ham)
    if m:
        ay = _TURKCE_AYLAR.get(_katla(m.group(2))[:3])
        if ay:
            try:
                return date(int(m.group(3)), ay, int(m.group(1))).isoformat()
            except ValueError:      # 31 Nisan gibi olmayan gun
                return ""

    # "Tue, 29 Jul 2026 14:30:00 GMT" gibi son care
    m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", ham)
    if m:
        try:
            d = datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")
            return d.date().isoformat()
        except ValueError:
            pass
    return ""


#: DUNYA isaretleri -- baslikta yabanci bir ulke ya da kurum geciyorsa
#: haber Turkiye sekmesine degil Dunya sekmesine gider.
#:
#: Ayrim KAYNAGA gore degil ICERIGE gore yapilir: Ekonomist Turk bir yayin
#: ama "Fed belirsizligi dolari vurdu" bir dunya haberi. Kaynaga baksaydik
#: Turk yayinlarinin butun dis haberleri Turkiye sekmesine dolardi.
DUNYA_ISARETLERI = (
    " abd ", "amerika", "washington", " fed ", "beyaz saray", "trump",
    "avrupa", "avro bolge", " ecb ", "brüksel", "bruksel",
    "almanya", "fransa", "ingiltere", "italya", "ispanya", "hollanda",
    " cin ", "japonya", "hindistan", "guney kore", "rusya", "ukrayna",
    # DIKKAT -- bu uc isaret bosluklu yazilir, yalin hali Turkce kelime
    # icinde eslesiyor ve olculdu:
    #   "haz-IRAN-in ardindan"  -> Iran haberi   (her haziran haberi!)
    #   "deger KATAR-ak"        -> Katar haberi
    #   "MISIR" hem ulke hem tahil -- tarim haberini disariya atiyordu,
    #   ayirt edilemedigi icin tamamen cikarildi.
    " iran", "israil", "suudi", " bae ", " katar ",
    "meksika", "brezilya", "arjantin", "kanada", "avustralya",
    "isvicre", "isvec", "norvec", "polonya", "yunanistan", "portekiz",
    "endonezya", "vietnam", "tayvan", "singapur", "nijerya",
    "opec", " imf ", "dunya bankasi", "wall street", "nasdaq",
    "s&p 500", "dow jones", "nikkei", "asya borsalar", "avrupa borsalar",
    "kuresel piyasa", "tesla", "apple", "amazon", "nvidia", "microsoft",
    "goldman", "deutsche bank", "shell", "stellantis", "volkswagen",
)

#: TURKIYE isaretleri -- DUNYA'dan ONCE bakilir.
#:
#: Sira boyle olmali cunku Turkiye haberi cogu zaman bir yabanci ulkeden
#: de soz eder: "Turkiye'nin ABD'ye ihracati artti" once Turkiye
#: haberidir. Dunya isaretine once baksaydik " abd " gorup Dunya
#: sekmesine atardik.
TURKIYE_ISARETLERI = (
    "turk", " tcmb ", "merkez bankasi", " bist ", "borsa istanbul",
    " tuik ", " spk ", " bddk ", "hazine", " toki ", " tl ", "lira",
    "kurus", "asgari ucret", "bag-kur", " ssk ", " sgk ", "emekli",
    "bakan", "cumhurbaskani", "meclis", "resmi gazete",
    "ankara", "istanbul", "izmir", "antalya", "anadolu", "guneydogu",
    # Bolge adlari EKLI bicimleriyle de yazilir: " ege " yalniz basina
    # "EGELI ihracatcilar" basligini kaciriyordu.
    "marmara", " ege ", "egeli", "egede", "ege ihracat", "ege bolge",
    "ihracatci birlik", "karadeniz", "akdeniz", "tarsim", "botas",
    "tpao", " yeka ", " kdv ", " otv ", "yerli", "milli",
)


def bolge_bul(baslik: str, dil: str) -> str:
    """Haberin "TR" mi "DUNYA" mi oldugunu soyler. Sekme ayrimi icin.

      1. Turkce olmayan kaynak (Fed, ECB, SEC, EIA) her zaman DUNYA.
      2. Baslikta Turkiye isareti varsa TR.
      3. Yabanci ulke/kurum geciyorsa DUNYA.
      4. Isaretsiz kalan TR.

    Dorduncu kural bilincli: Turk bir yayinin ekonomi servisinde isaretsiz
    kalan haber ("Altin haftaya yukselisle basladi") yurt ici okura yurt
    ici baglamda sunuluyor. Yanlis tarafa dusen tek bir haberin bedeli
    dusuk; onemli olan Dunya sekmesinin gercekten dis haber tasimasi.
    """
    if dil != "tr":
        return "DUNYA"
    k = " " + _katla(baslik) + " "
    if any(i in k for i in TURKIYE_ISARETLERI):
        return "TR"
    if any(i in k for i in DUNYA_ISARETLERI):
        return "DUNYA"
    return "TR"


def _aranacak(baslik: str) -> str:
    """Katlanmis basligi bosluklarla PAYLAR.

    Kisa kisaltmalar (" ges ", " res ", " ons ") kelime icinde eslesiyordu
    ve sessiz yanlis siniflandirma uretiyordu -- olculdu:

        "SEC charges firm with fraud"  -> Enerji
         cunku "char-GES " icinde "ges " geciyor
        "Billions of dollars"          -> Altin
         cunku "billi-ONS " icinde "ons " geciyor

    Bastaki ve sondaki bosluk, isaretin " ges " diye yazilabilmesini
    saglar; boylece baslik "GES kurulumu" diye BASLASA bile eslesir.
    """
    return " " + _katla(baslik) + " "


def gurultu_mu(baslik: str) -> bool:
    """Ekonomi disi oge mi? Ticari beslemelerde kullanilir."""
    k = _aranacak(baslik)
    return any(i in k for i in GURULTU_ISARETLERI)


def konu_bul(baslik: str, varsayilan: str = "") -> str:
    """Baslikta ekonomi konusu arar. Bulamazsa `varsayilan` doner.

    Ticari cagrilarda `varsayilan` BOS gecilir: konu bulunamayan oge
    alinmaz. Resmi cagrilarda varsayilan verilir, cunku o beslemelerde
    her sey zaten ekonomidir.
    """
    k = _aranacak(baslik)
    for konu, isaretler in KONU_ISARETLERI:
        if any(i in k for i in isaretler):
            return konu
    return varsayilan


#: Imza cikarilirken atilan, ayirt ediciligi olmayan kelimeler.
_ETKISIZ = frozenset({
    "ve", "ile", "icin", "bir", "bu", "su", "the", "and", "for", "with",
    "son", "yeni", "daha", "gore", "sonra", "once", "kadar", "olarak",
    "dakika", "haberi", "aciklandi", "belli", "oldu", "sonuc",
})

#: Turkce eklerin karsilastirmayi bozmamasi icin kelimeler govdeye
#: kirpilir. "turistler" ve "turistlerden" ayni govdeye ("turis") duser.
#: Bes harf olculdu: dorde inince alakasiz kelimeler birlesiyor
#: ("kredi"/"kriz" -> "kred"/"kriz" ayri ama "banka"/"bankacilik" zaten
#: birlesiyordu), altiya cikinca ekli bicimler ayrisiyor.
_GOVDE_UZUNLUK = 5


def _imza(baslik: str) -> frozenset[str]:
    k = re.sub(r"[^a-z0-9 ]", " ", _katla(baslik))
    return frozenset(
        p[:_GOVDE_UZUNLUK] for p in k.split()
        if len(p) > 2 and p not in _ETKISIZ
    )


#: Iki baslik ayni haberi mi anlatiyor?
#: Ortusme orani = ortak govde / kisa basligin govde sayisi.
ORTUSME_ESIGI = 0.55

#: En az kac ortak govde aransin -- tek ortak kelimeyle %50 orana ulasip
#: alakasiz iki basligin birlesmesini engelliyor.
#:
#: AMA bu sart tek basina kisa basliklarda tekillemeyi TAMAMEN kapatiyordu.
#: "Temmuz enflasyonu aciklandi" imzasi yalnizca {temmu, enfla} -- cunku
#: "aciklandi" etkisiz kelime. Iki gazete AYNI basligi attiginda bile ortak
#: govde ikide kaliyor, uc sarti hic saglanmiyordu; olculdu, TRT ve
#: Haberturk ayni basligi ayni gun iki kez yayimladi.
#:
#: Bu yuzden esik kisa basligin govde sayisiyla sinirlanir: iki govdeli iki
#: baslik ancak IKISI DE ortakken birlesir, ki o zaten ayni basliktir.
EN_AZ_ORTAK = 3


def _ortusuyor(ia: frozenset[str], ib: frozenset[str]) -> bool:
    if not ia or not ib:
        return False
    kisa = min(len(ia), len(ib))
    if len(ia & ib) < min(EN_AZ_ORTAK, kisa):
        return False
    return len(ia & ib) / kisa >= ORTUSME_ESIGI


def ayni_haber_mi(a: str, b: str) -> bool:
    return _ortusuyor(_imza(a), _imza(b))


def _ogeler(xml: str) -> list[dict]:
    """RSS <item> ve Atom <entry> ogelerini ayristirir."""
    sonuc = []
    for kalip in (r"<item[ >].*?</item>", r"<entry[ >].*?</entry>"):
        for blok in re.findall(kalip, xml, re.S):
            baslik = re.search(r"<title[^>]*>(.*?)</title>", blok, re.S)
            # Atom'da <link href="...">, RSS'te <link>...</link>
            adres = re.search(r'<link[^>]*href="([^"]+)"', blok) or \
                re.search(r"<link[^>]*>(.*?)</link>", blok, re.S)
            ozet = re.search(r"<description[^>]*>(.*?)</description>", blok, re.S) or \
                re.search(r"<summary[^>]*>(.*?)</summary>", blok, re.S)
            tarih = re.search(r"<pubDate[^>]*>(.*?)</pubDate>", blok, re.S) or \
                re.search(r"<published[^>]*>(.*?)</published>", blok, re.S) or \
                re.search(r"<updated[^>]*>(.*?)</updated>", blok, re.S) or \
                re.search(r"<dc:date[^>]*>(.*?)</dc:date>", blok, re.S)
            if not baslik or not adres:
                continue
            sonuc.append({
                "baslik": _metin(baslik.group(1)),
                "adres": _metin(adres.group(1)),
                "ozet": _metin(ozet.group(1)) if ozet else "",
                "tarih": _tarih_coz(_metin(tarih.group(1))) if tarih else "",
            })
    return sonuc


def _besleme_oku(c: httpx.Client, tanim, en_fazla: int) -> list[Haber]:
    kod, kisa, tam, adres, varsayilan, dil, ticari = tanim
    try:
        y = c.get(adres)
        y.raise_for_status()
    except httpx.HTTPError:
        return []

    eski_sinir = (datetime.now(timezone.utc).date()
                  - timedelta(days=GECERLILIK_GUN)).isoformat()
    cikti: list[Haber] = []

    for o in _ogeler(y.text)[:en_fazla]:
        baslik = o["baslik"]
        if not baslik or len(baslik) < 12:
            continue

        if ticari:
            if gurultu_mu(baslik):
                continue
            # Ticari ogede varsayilan YOK -- konu bulunamazsa alinmaz.
            konu = konu_bul(baslik, "")
            if not konu:
                continue
            # Arama motoru icin tutulan bayat sayfalari eler.
            if o["tarih"] and o["tarih"] < eski_sinir:
                continue
        else:
            konu = konu_bul(baslik, varsayilan)

        cikti.append(Haber(
            kaynak_kodu=kod, kurum=kisa, kurum_tam=tam,
            baslik=baslik, adres=o["adres"], ozet=o["ozet"][:400],
            tarih=o["tarih"], konu=konu, dil=dil, ticari=ticari,
        ))
    return cikti


def cek(kod: str = "", en_fazla: int = 12) -> list[Haber]:
    """Beslemeleri okur. `kod` verilirse yalnizca o besleme.

    Beslemeler PARALEL okunur. Yirmi dort besleme sirayla okundugunda
    calisma bir dakikaya yaklasiyordu; bu dogrudan GitHub Actions dakikasi
    demek ve saatlik calismada aylik kotayi yiyor.
    """
    secilen = [b for b in BESLEMELER if not kod or b[0] == kod]
    haberler: list[Haber] = []

    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                      follow_redirects=True) as c:
        with _cf.ThreadPoolExecutor(max_workers=8) as havuz:
            for parca in havuz.map(
                    lambda t: _besleme_oku(c, t, en_fazla), secilen):
                haberler.extend(parca)

    # 1) Ayni duyuru birden fazla beslemede olabilir -- adrese gore tekille
    gorulen: set[str] = set()
    tekil = [h for h in haberler
             if not (h.adres in gorulen or gorulen.add(h.adres))]

    # 2) Ayni HABER farkli kaynaklarda farkli baslikla cikar. Besleme
    #    sirasi editoryaldir: listede once gelen kaynak tutulur.
    sira = {b[0]: i for i, b in enumerate(BESLEMELER)}
    tekil.sort(key=lambda h: (sira.get(h.kaynak_kodu, 99),
                              h.tarih or "0000-00-00"))
    secili: list[Haber] = []
    imzalar: list[frozenset[str]] = []
    for h in tekil:
        im = _imza(h.baslik)
        if any(_ortusuyor(im, v) for v in imzalar):
            continue
        secili.append(h)
        imzalar.append(im)

    # En yeni once; tarihi cozulemeyenler sona
    secili.sort(key=lambda h: h.tarih or "0000-00-00", reverse=True)
    return secili


def bugun() -> str:
    return datetime.now(timezone.utc).date().isoformat()
