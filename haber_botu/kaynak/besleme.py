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

    # --- Kuresel makro akis ---
    #
    # FinancialJuice, sitesinde RSS baglantisini KENDISI yayimliyor
    # (feed.ashx?xy=rss). Diger ticari kaynaklarla ayni kurala tabi:
    # `ticari=True`, yani sayfada kunye ve kaynaga baglanti ZORUNLU.
    #
    # Iki sebeple degerli:
    #   1. Dunya sekmesini gercekten dolduruyor -- kuresel veri
    #      aciklamalari ve jeopolitik gelismeler dakika dakika.
    #   2. Basliklarin bir kismi "Actual X (Forecast Y, Previous Z)"
    #      kalibinda geliyor, yani BEKLENTIYI de tasiyor. Ucretsiz
    #      konsensus verisi bulunamadigi icin cevapsiz kalan "beklenti
    #      neydi" sorusu bu kaynakta cevaplaniyor.
    ("FJUICE", "FinancialJuice", "FinancialJuice",
     "https://www.financialjuice.com/feed.ashx?xy=rss",
     "Şirket haberleri", "en", True),

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
    # "dizi" TEK BASINA CIKARILDI: Turkce'de "bir dizi X" = "bir dizi
    # halinde X" demek ve finans basliginda sik geciyor. Olculdu:
    # "Trump: 3 milyar $ degerinde BIR DIZI madencilik projesini
    # duyuruyoruz" gurultu sayilip eleniyordu. Televizyon anlaminda
    # kullanim ekli bicimde geliyor.
    "spiker", "dizisi", "dizi filmi", "belgesel", "sinema", "konser",
    "sanatci",
    "antik kent", "muze", "arkeolo", "burc", "fal", "yemek tarifi",
    # ASAYIS VE YASAM -- ekonomi beslemelerinde cikiyor ve dosya
    # zincirlerine sizıyor. Olculdu: "ABD'nin North Carolina
    # eyaletinde silahli saldiri" haberi JEOPOLITIK olarak siniflandi
    # (kalip: "saldiri") ve Hurmuz Bogazi dosyasinin icine girdi;
    # "Mutfaklara bereket getiren lezzetler: 11-17 Agustos" ise findik
    # fiyati dosyasina girdi.
    #
    # Bunlar haber degil sayilmiyor -- baska bir yayinin isi. Bizim
    # akisimizda yer kaplamalari, gercek zinciri seyreltiyor.
    "silahli saldiri", "bicakli", "cinayet", "gozaltina alindi",
    "tutuklandi", "hayatini kaybetti", "olu sayisi", "yarali sayisi",
    # DIKKAT: bu liste ASCII KATLANMIS metinle karsilastiriliyor
    # (bkz. `_katla`). Turkce harf iceren bir kalip HICBIR ZAMAN
    # eslesmez -- ilk yazimda "aranıyor" boyle yazilip sessizce olu
    # kalmisti. "kayip" ise cikarildi: sirket zarari haberlerini de
    # elerdi ("ceyrekte kayip acikladi").
    "operasyonda yakalandi",
    "lezzetler", "tarifi", "ne pisirsem", "menu onerisi",
    # URUN TANITIMI ve TOREN. Ikisi de ekonomi beslemesinden geliyor ama
    # arastirma icerigi degil; olculdu, sayfa bile uretilmisti:
    #   "Bebeklerin cildine pamuksu dokunus: BabyCo Bebek Urunleri 7-13"
    #   "Kultur ve Turizm Bakanligindan Cansever icin taziye mesaji"
    #
    # "indirim" TEK BASINA EKLENMEDI: "faiz indirimi" bu sitenin en
    # merkezi konusu. Kalip, urun kataloguna ozgu olacak kadar dar.
    "bebek urunleri", "aktuel urun", "indirim katalogu",
    "taziye", "kutlama mesaji", "acilis toreni",
    "burclar", "ruya tabiri", "tatil rotasi", "gezi rehberi",
    "saglik durumu", "kaza gecirdi", "vefat etti", "hava durumu",
    "namaz vakti", "bayram tatili kac gun",
    # catisma/kayip haberleri -- ekonomi beslemelerine dusuyor
    # "patlama" -> "patlamada". Genel bicim PIYASA HABERINI eliyordu:
    # "UKMTO: Tanker Hurmuz'de 2 patlama sesi duydu" -- Hurmuz'de tanker
    # patlamasi tam olarak Brent'i hareket ettiren olaydir. Bulunma
    # ekli bicim ("patlamada uc kisi oldu") can kaybi haberine ozgu.
    "olduruldu", "oldurdu", "yarali", "sehit", "cenaze", "patlamada",
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
#: IKINCIL ISARETLER -- YALNIZCA varsayilan kova doldugunda bakiliyor.
#:
#: NEDEN AYRI TABLO, neden asagidakine eklenmedi
#: --------------------------------------------
#: Bu kaliplar ana tablodakilerden daha ZAYIF. Ana tabloya
#: karistirilsalardi ilk eslesen kazandigi icin DOGRU etiketleri de
#: ezerlerdi. Olculdu: "zirve" kalibi hem diplomatik zirveyi hem
#: "Gumus 7 haftanin ZIRVESINDE" basligini yakaliyor ve Enflasyon
#: etiketini Jeopolitik'e ceviriyordu.
#:
#: Buraya yalnizca konusu HIC bulunamamis baslik geliyor; yani en
#: kotu ihtimalle yanlis bir etiket, hicbir etiket olmayan yerde
#: duruyor. Dogru etiket asla bozulmuyor -- tasarim geregi.
#:
#: NEDEN GEREKLI. Olculdu: ana sayfadaki 40 akis kaleminin 22'si
#: "Sirket haberleri" varsayilanindaydi ve neredeyse hicbiri sirket
#: haberi degildi -- KDV zammi, Iran muzakeresi, MUFG'nin yen notu,
#: volatilite tablosu. Akisa tema etiketi basmadan once bu kovanin
#: temizlenmesi gerekiyordu: yanlis etiket, etiketsizlikten kotudur.
IKINCIL_ISARETLER = (
    ("Jeopolitik", (
        "baris sureci", "mutabakat", "ateskes", "telefon gorusme",
        "deniz ussu", "insansiz hava araci", "anlasmayi ihlal",
        "muzakere", "disisleri", "buyukelci", "savunma harcama",
        "askeri operasyon",
    )),
    # Doviz masasi notlari: "MUFG: JPY", "ING: EUR" gibi kisa basliklar.
    # "usd" ve "eur" BILEREK YOK -- her ikinci baslikta geciyor ve
    # kovayi doviz haberi olmayan seylerle doldururlardi.
    ("Döviz", (
        "doviz gucu", "parite", "jpy", "gbp", "chf", "sterlin",
        "yen kuru",
    )),
    # Piyasa teknik verisi. Bunlar haber degil TABLO, ama okurun
    # gordugu akista yer aliyorlar ve bir temaya ait olmalilar.
    ("Borsa", (
        "volatilite", "korelasyon", "vadeli islem", "islem hacmi",
    )),
    ("Vergi ve kamu maliyesi", (
        "kdv", "maliye bakanlig", "hazine bonosu", "tahvil ihrac",
        "butce acig", "vergi orani",
    )),
)

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
    # JEOPOLITIK -- Enerji ve Dis ticaret'in ALTINDA duruyor.
    #
    # Sira bilincli: "ABD Venezuela'ya petrol yaptirimlarini kaldirdi"
    # once bir ENERJI haberidir, "Trump Cin mallarina gumruk vergisi
    # getirdi" once bir DIS TICARET haberidir. Jeopolitik, fiyatlanacak
    # bir kanali olmayan siyasi olaylari topluyor: savas, ateskes,
    # yaptirim, secim, anlasma.
    #
    # Bu konu HIC YOKTU ve sonucu olculdu: dokuz jeopolitik baslikta
    # sekizi "Sirket haberleri"ne dusup eleniyordu -- ABD-Iran anlasmasi,
    # Hurmuz'da tanker saldirisi, Trump'in Fed cikisi dahil. Oysa petrol
    # ve altin fiyatini en sert hareket ettiren haberler bunlar.
    ("Jeopolitik", (
        # catisma ve cozum
        "savas", "catisma", "saldiri", "ateskes", "baris gorusme",
        "muzakere", "nukleer anlasma", "askeri", "tatbikat", "isgal",
        "hava saldirisi", "fuze", "insansiz hava",
        # yaptirim ve kisitlama
        "yaptirim", "ambargo", "kara liste", "ihracat kisitlamas",
        "ticaret savas", "misilleme",
        # aktorler ve yerler (fiyat tasiyan)
        " trump ", "trump'", "beyaz saray", "kremlin", " nato ",
        "hurmuz", "kizildeniz", "suveys", "tayvan",
        # siyasi takvim
        "secim sonuc", "hukumet krizi", "guven oyu", "kabine",
        # Ingilizce
        "sanction", "ceasefire", "military strike", "airstrike",
        "trade war", "tariff war", "geopolit", "embargo",
     # Akis beslemesi askeri gelismeleri INGILIZCE veriyor ve Turkce
     # kaliplarin hicbirine takilmiyordu. Olculdu: Yemen/Husi ve Kuzey
     # Kore basliklari "Sirket haberleri" olarak siniflaniyordu.
     "houthi", "missile launch", "armed forces", "warplane", "drone strike",
     "troops", "militar", "attack on", "killed in", "war ", "warns against",
     "retaliat", "escalat", "nuclear", "peace talks", "hostilit",
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


#: Temizlikten SONRA hala duran kod izleri. Bunlardan biri kaldiysa
#: elimizdeki sey duzyazi degil; ozetsiz yayimlamak, cop yayimlamaktan
#: iyidir (sablon `{% if h.ozet %}` ile zaten koruyor ve kayitlarin
#: 200/462'sinde ozet olculdugunde ZATEN bostu).
#:
#: Liste DAR tutuldu. `Trump: "..."` gibi haber dilinde olagan kaliplar
#: yanlis pozitif uretmesin diye yalnizca tartismasiz kod isaretleri
#: var; iki nokta + tirnak gibi bicimler BILEREK disarida.
_KOD_IZI = re.compile(
    r"\{\{|\{%|</?\s*[a-z][a-z0-9]*[\s/>]|"
    r"\bfunction\s*\(|\bvar\s+\w+\s*=|\bnew\s+[A-Z]\w+\s*\(",
    re.I)


def _metin(ham: str) -> str:
    """CDATA, HTML etiketi ve fazla bosluktan arindirir.

    SIRA HAYATI: KACIS ONCE COZULUR, ETIKET SONRA SILINIR.
    ---------------------------------------------------
    Ilk yazimda ters sirada yapiliyordu -- once `<[^>]+>` siliniyor,
    sonra `html.unescape` cagriliyordu. Beslemede etiketler XML
    kacisiyla (`&lt;script&gt;`) geldiginde ilk adim hicbir sey
    bulamiyor, ikinci adim ise onlari GERCEK ETIKETE cevirip metne
    geri koyuyordu. Yani isaretleme temizlikten SONRA doguyordu.

    Olculdu: iki haber kaydinin ozeti ham bir TradingView gomme
    betigiydi ve okur bunu "Ne oldu?" sorusunun CEVABI olarak gordu:

        <script ...>new TradingView.chart({... "desc_{{NewsID}}"});</script>

    Dongu iki kez kacis cozup siliyor: cift kacirilmis
    (`&amp;lt;script&amp;gt;`) besleme de temizleniyor. Ucuncu tur
    guvenlik payi -- sabit noktaya varinca kendiliginden duruyor.

    SCRIPT/STYLE ICERIGI DE SILINIYOR. Yalnizca etiketi silmek JavaScript
    GOVDESINI metin olarak birakirdi. Kapanis etiketi yoksa satir sonuna
    kadar atiliyor: bozuk isaretleme, en cok cop birakan durumdur.
    """
    ham = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", ham, flags=re.S)

    onceki = None
    for _ in range(3):
        if ham == onceki:
            break
        onceki = ham
        ham = html.unescape(ham)
        ham = re.sub(r"<\s*(script|style)\b.*?(?:</\s*\1\s*>|$)", " ", ham,
                     flags=re.S | re.I)
        ham = re.sub(r"<[^>]+>", " ", ham)

    metin = re.sub(r"\s+", " ", ham).strip()
    return "" if _KOD_IZI.search(metin) else metin


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
#: YABANCI MERKEZ BANKALARI VE PARA BIRIMLERI.
#:
#: Olculdu (2026-08-21): "Capital Economics'ten kritik degerlendirme:
#: BoJ faiz artiracak mi?" haberi TR sayildi ve sayfaya TURKIYE TUFE'si
#: (%31,75) ile "Son on uc ayda TUFE" grafigi basildi. Japon yeni
#: konusu, butun veri Turkiye.
#:
#: Sebep: baslikta "BoJ" geciyordu ama listede yalnizca "japonya"
#: vardi. Isaret bulunamayinca dorduncu kural devreye girip TR dedi.
#:
#: Tek tek ulke adi eklemek kostebek oyunu olurdu. Buradaki liste bir
#: SINIF kapatiyor: bir haber yabanci bir MERKEZ BANKASINI ya da
#: yabanci bir PARA BIRIMINI konu ediyorsa, hangi dilde yazildigindan
#: bagimsiz olarak yurt disi haberidir. Turk bir yayinin BoJ analizi
#: hala Japonya haberidir.
#:
#: TEK BASINA GECEN PARA BIRIMI ADLARI BILEREK DISARIDA.
#:
#: Ilk yazimimda " yen ", " dolari ", " real " gibi adlari da koydum ve
#: SINAYINCA KIRILDI:
#:
#:     "Borsada yeni rekor"  ->  DUNYA   (yanlis)
#:
#: " yeni " Turkce'de "new" demek ve her yerde geciyor; " dolari " ise
#: yurt ici kur haberlerinin tamaminda ("dolar/TL"). Bu adlar bir
#: haberin yurt disi oldugunu KANITLAMIYOR -- yalnizca para biriminden
#: soz edildigini soyluyor ve o para birimi Turkiye'nin gundeminde de
#: olabilir.
#:
#: Geriye yalnizca TEK ANLAMA GELEN isaretler kaldi: yabanci merkez
#: bankalarinin adlari, baskanlari ve para biriminin ULKEYLE birlikte
#: yazildigi kaliplar ("japon yeni"). Bir isaretin listede olmamasi
#: haberi TR yapmaz -- dorduncu kural zaten muhafazakar taraf.
#:
#: Bosluklu yazim bilincli: kisaltmalar kelime icinde eslesmesin. Ayni
#: tuzak daha once " ges " ile yasandi, bkz. `_aranacak`.
YABANCI_PARA_OTORITESI = (
    " boj ", "bank of japan", " boe ", "bank of england",
    " snb ", " rba ", " rbnz ", " pboc ", "riksbank", "norges bank",
    " fomc ", "federal reserve", "avrupa merkez bankasi",
    "powell", "lagarde", " ueda ", "bailey",
    "japon yeni", "cin yuani", "ingiliz sterlini", "isvicre frangi",
)

DUNYA_ISARETLERI = (
    *YABANCI_PARA_OTORITESI,
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

    NOKTALAMA DA BOSLUGA CEVRILIYOR. Eksikligi olculdu:

        "Trump: Fed baskanini gorevden alabilirim"
        -> " trump: ... "  ve " trump " isareti ESLESMEDI

    Iki nokta, virgul, parantez ve tirnak kelimeyi isaretten ayirmiyordu.
    Tire ve egik cizgi KORUNUYOR: "bag-kur" ve "usd/try" gibi isaretler
    onlara dayaniyor.
    """
    k = re.sub(r"[^a-z0-9&/%-]+", " ", _katla(baslik))
    return " " + k.strip() + " "


def gurultu_mu(baslik: str) -> bool:
    """Ekonomi disi oge mi? Ticari beslemelerde kullanilir.

    KALIP SOZCUK BASINDAN ESLESIR. Serbest alt-dize eslesmesi GERCEK
    FINANS HABERINI ELIYORDU ve bu sessizdi -- elenen haber hicbir yerde
    gorunmuyor. Olculdu, 1038 baslikta:

        "maci"  -> "Kizildeniz deniz tasiMACIliginin..."   (tasimacilik)
                -> "Kuzey Deniz Yolu uzerinden duzenli Avrupa tasimaciligi"
        Ikisi de deniz TASIMACILIGI haberi; futbol maci sanilip atildi.

    `_aranacak` metni zaten bosluklarla cevreliyor ve noktalamayi
    bosluga ceviriyor, yani " " + kalip araması sozcuk basi demek.
    Kalibin sonu serbest birakiliyor: "arkeolo" -> "arkeoloji",
    "arkeolojik"; Turkce ekler boyle yakalaniyor.
    """
    k = _aranacak(baslik)
    return any(" " + i in k for i in GURULTU_ISARETLERI)


#: MECAZI "SAVAS" KULLANIMLARI -- kalip -> gercek konu.
#:
#: Turkce'de "savas" ve "saldiri" mecazi olarak sik kullaniliyor ve
#: Jeopolitik isaretleri arasinda ciplak "savas" var. Olculdu:
#:   "55 milyar euroluk miras savasi" -> Jeopolitik
#:   "Fiyat savasi kizisti"           -> Jeopolitik
#: Yanlis konu yalnizca etiketi degil, sayfanin IZLEME LISTESINI de
#: bozuyor: miras davasinin altinda "Brent petrol, Ons altin, CDS"
#: yaziyordu.
#:
#: "Kur savasi" ve "ticaret savasi" GERCEKTEN ekonomik olaylar ama
#: jeopolitik degil; kendi konularina yonlendiriliyorlar.
#:
#: DIKKAT: bu liste ASCII KATLANMIS metinle karsilastiriliyor
#: (bkz. `_katla`). Turkce harf iceren bir kalip HICBIR ZAMAN eslesmez.
MECAZ: tuple[tuple[str, str], ...] = (
    ("miras savasi", "Şirket haberleri"),
    ("fiyat savasi", "Şirket haberleri"),
    ("patent savasi", "Şirket haberleri"),
    ("reklam savasi", "Şirket haberleri"),
    ("taht savasi", "Şirket haberleri"),
    ("kur savasi", "Döviz"),
    ("ticaret savasi", "Dış ticaret"),
    ("tarife savasi", "Dış ticaret"),
)


def konu_bul(baslik: str, varsayilan: str = "") -> str:
    """Baslikta ekonomi konusu arar. Bulamazsa `varsayilan` doner.

    Ticari cagrilarda `varsayilan` BOS gecilir: konu bulunamayan oge
    alinmaz. Resmi cagrilarda varsayilan verilir, cunku o beslemelerde
    her sey zaten ekonomidir.
    """
    k = _aranacak(baslik)
    # MECAZ ONCE COZULUYOR.
    #
    # "savas" isareti Jeopolitik'te ve liste sirasinda Doviz'den de
    # Sirket haberleri'nden de ONCE geliyor -- ilk eslesen kazandigi
    # icin siralamayla duzeltilemez. Olculdu ve yayimlandi:
    #   "55 milyar euroluk miras savasi"  -> Jeopolitik
    #   "Fiyat savasi kizisti"            -> Jeopolitik
    # Ikisi de sirket haberi. Miras davasi jeopolitik sayilinca izleme
    # listesi de o konudan geldi: "Brent petrol, Ons altin, CDS primi".
    for kalip, konu in MECAZ:
        if kalip in k:
            return konu
    for konu, isaretler in KONU_ISARETLERI:
        if any(i in k for i in isaretler):
            return konu
    # Ana tablo bos dondu: zayif kaliplara BURADA bakiliyor. Sirasi
    # onemli -- once bakilsaydi dogru etiketleri ezerdi.
    for konu, isaretler in IKINCIL_ISARETLER:
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


#: Besleme basina oge siniri. Varsayilan `en_fazla`; burada yazan ezer.
#:
#: FinancialJuice dakika dakika yayin yapiyor ve tek cagrida 100 oge
#: donuyor. 12'lik varsayilan sinirla o akisin yalnizca son on dakikasi
#: aliniyordu -- olculdu: 100 ogeden 3'u siteye giriyordu.
#:
#: 70 -> 100: kaynak zaten 100'de kesiyor, biz ustune 30 oge daha
#: atiyorduk. Calistirmalar arasi bir saat varsa o 30 oge bir daha hic
#: gorunmuyor -- kalici kayip.
BESLEME_SINIRI = {"FJUICE": 100}

#: AKIS BESLEMELERI -- konu bulunamasa da ALINIR.
#:
#: Normalde ticari bir ogede konu bulunamazsa oge atiliyor. Kural genel
#: gazeteler icin dogru: "Ünlü oyuncu boşandı" haberinin ekonomi
#: konusu yoktur ve siteye girmemelidir.
#:
#: FinancialJuice bir GAZETE DEGIL, finans teli. Kural orada tersine
#: caliSiyordu -- olculdu, 100 ogenin 45'i "konu bulunamadi" diye
#: atiliyordu ve atilanlarin icinde sunlar vardi:
#:
#:   US Wholesale Inventories MoM Actual 0.2% (Forecast 0.3%)
#:   U.S. military aware of North Korea missile launch
#:   Yemen: Houthi spokesperson statement
#:
#: Yani tam olarak sitenin aradigi sey: rakam+beklenti tasiyan veri
#: aciklamalari ve jeopolitik gelismeler. Konu isaretleri Turkce
#: kaliplar uzerine kurulu ve bu basliklarin hicbirine takilmiyor.
#:
#: Bu beslemelerde konu bulunamayan oge, beslemenin VARSAYILAN konusuyla
#: aliniyor. Konu bulunamamis olmasi, sayfa uretilecegi anlamina gelmez
#: -- `gundem_yorum.siniflandir` o karari ayrica veriyor ve govdesi
#: olmayan baslik yine sayfa almiyor. Oge yalnizca CANLI AKISA giriyor.
AKIS_BESLEMELERI = frozenset({"FJUICE"})

#: Basliktan silinecek kaynak onekleri. Kunye sayfada ayrica basiliyor;
#: onek basligin yarisini yiyor ve listede tekrar gorunuyor.
_ONEKLER = (
    re.compile(r"^\s*FinancialJuice\s*:\s*", re.I),
)

#: Veri aciklamasi basliginda konu bulunamazsa kullanilacak esleme.
#:
#: "Eurozone Retail Sales YoY Actual 0.7%" gibi basliklar Turkce konu
#: isaretlerinin hicbirine takilmiyor ve ticari kaynakta konu
#: bulunamayan oge ALINMIYOR. Oysa bunlar sitenin en degerli
#: iceriklerinden: rakam ve beklenti basligin icinde.
VERI_KONULARI = (
    (("cpi", "inflation", "price index", "ppi", "hicp"), "Enflasyon"),
    (("unemployment", "payroll", "jobless", "employment", "wage",
      "labour", "labor"), "İstihdam ve ücret"),
    (("trade balance", "exports", "imports", "current account"),
     "Dış ticaret"),
    # "wholesale", "durable goods", "factory orders" eksikti ve bu
    # basliklar -- rakam ve BEKLENTI tasiyan, sitenin en degerli veri
    # ogeleri -- konu bulunamadigi icin "Sirket haberleri"ne dusuyordu.
    (("retail sales", "gdp", "pmi", "industrial production",
      "industrial orders", "confidence", "sentiment", "consumer spending",
      "wholesale", "durable goods", "factory orders", "business climate",
      "economic activity", "capacity utilization"),
     "Borsa"),
    (("interest rate", "rate decision", "central bank", "boe", "fed",
      "ecb", "boj"), "Para politikası"),
    (("crude", "oil", "gas", "opec", "refinery"), "Enerji"),
    (("housing", "building permits", "construction"), "Konut ve kira"),
)


def _onek_sil(baslik: str) -> str:
    for d in _ONEKLER:
        baslik = d.sub("", baslik)
    return baslik.strip()


def veri_konusu(baslik: str) -> str:
    """Veri aciklamasi basligindan konu. Bulamazsa bos."""
    k = _aranacak(baslik)
    for isaretler, konu in VERI_KONULARI:
        if any(i in k for i in isaretler):
            return konu
    return ""


#: Okunamayan beslemeler. `cek()` her cagrida temizler ve doldurur.
#:
#: NEDEN VAR: besleme hatasi SESSIZDI -- `except: return []`. Bir kaynak
#: coktugunde gundem o kaynaksiz uretiliyor ve hicbir yerde iz kalmiyordu.
#: Olculdu: FinancialJuice bir calistirmada hic gelmedi ve gundemde
#: 89 haberin 0'i o kaynaktandi; hata mesaji olmadigi icin once
#: siniflandirma sorunu sanildi. Bir kaynagin CALISMAMASI ile o kaynakta
#: HABER OLMAMASI ayni sey degil ve ayirt edilebilmeli.
OKUNAMAYAN: list[tuple[str, str]] = []


def _besleme_oku(c: httpx.Client, tanim, en_fazla: int) -> list[Haber]:
    kod, kisa, tam, adres, varsayilan, dil, ticari = tanim
    try:
        y = c.get(adres)
        y.raise_for_status()
    except httpx.HTTPError as e:
        OKUNAMAYAN.append((kod, f"{type(e).__name__}: {e}"[:120]))
        return []

    eski_sinir = (datetime.now(timezone.utc).date()
                  - timedelta(days=GECERLILIK_GUN)).isoformat()
    cikti: list[Haber] = []
    sinir = BESLEME_SINIRI.get(kod, en_fazla)

    for o in _ogeler(y.text)[:sinir]:
        baslik = _onek_sil(o["baslik"])
        if not baslik or len(baslik) < 12:
            continue

        if ticari:
            # Gurultu suzgeci AKIS BESLEMELERINDE DE calisiyor: konu
            # sartini kaldirmak, magazin/asayis basligini kabul etmek
            # anlamina gelmemeli.
            if gurultu_mu(baslik):
                continue
            konu = konu_bul(baslik, "") or veri_konusu(baslik)
            if not konu:
                # Genel gazetede konu bulunamayan oge ALINMAZ.
                # Akis beslemesinde ALINIR (bkz. AKIS_BESLEMELERI).
                if kod not in AKIS_BESLEMELERI:
                    continue
                konu = varsayilan
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
    OKUNAMAYAN.clear()
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
    #    ELEME GUNE GORE KOVALANIYOR.
    #
    #    Imza karsilastirmasi butun listede yapiliyordu ve DUZENLI
    #    YAYIMLANAN resmi belgeleri birbirine eziyordu. Olculdu:
    #
    #      "Minutes of the FOMC, March 17-18, 2026"   (8 Nisan)
    #      "Minutes of the FOMC, July 28-29, 2026"    (19 Agustos)
    #
    #    Govdeler: ortak 6 / kisa 7 = 0,86 ortusme. Tek fark ay adi;
    #    gun numaralari govdeye kirpilirken dusuyor. Sonuc, Temmuz
    #    toplantisinin tutanaklari NISAN'dakine benzedigi icin hic
    #    alinmadi -- 5 Agustos'tan beri depoda tek bir Fed kaydi yok.
    #
    #    Elemenin amaci "ayni gun bes kaynakta cikan ayni haber"; farkli
    #    aylarda cikan iki ayri belge degil. Gun olcute katiliyor.
    #
    #    Ayni hata sinifi bu depoda daha once `insa.tekilles` icinde de
    #    yasandi ("Borsa gunu yukselisle tamamladi" her yukselis gununde
    #    yeniden yaziliyor) ve orada da cozum gunu olcute katmakti.
    secili: list[Haber] = []
    imzalar: dict[str, list[frozenset[str]]] = {}
    for h in tekil:
        im = _imza(h.baslik)
        gun = (h.tarih or "0000-00-00")[:10]
        if any(_ortusuyor(im, v) for v in imzalar.get(gun, ())):
            continue
        secili.append(h)
        imzalar.setdefault(gun, []).append(im)

    # En yeni once; tarihi cozulemeyenler sona
    secili.sort(key=lambda h: h.tarih or "0000-00-00", reverse=True)
    return secili


def bugun() -> str:
    return datetime.now(timezone.utc).date().isoformat()
