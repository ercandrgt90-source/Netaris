"""Konuya uygun GERCEK fotograf -- Openverse, ucretsiz ve anahtarsiz.

KAYNAK SECIMI
-------------
Openverse (WordPress.org'un acik gorsel arama servisi). Anahtar istemiyor,
`license_type=commercial` filtresiyle ticari kullanima acik sonuc veriyor
ve her sonucla birlikte hazir atif metni donuyor.

Denenip elenenler:
  Unsplash  401 -- anahtar zorunlu
  Pexels    anahtarsiz cevap verdi ama belgelenmis kullanim anahtarli;
            "calisiyor gorunuyor" uzerine sistem kurulmaz

LISANS -- atif zorunlu
----------------------
Sonuclarin cogu CC BY ya da CC BY-SA. Ikisi de ticari kullanima aciktir
ama **atif sarttir**: fotografcinin adi ve lisans, gorselin altinda
yazilir. Atif metnini Openverse hazir veriyor, biz saklayip basiyoruz.
Atifi dusuren bir kod degisikligi lisansi ihlal eder.

YEREL KOPYA
-----------
Gorseller indirilip kendi sunucumuzdan servis edilir. Sebepleri:
  * Uzaktan baglamak her sayfa acilisinda ucuncu partiye istek demek --
    ziyaretcinin IP'si Flickr'a gider, gizlilik sayfasinda anlatilacak
    yeni bir madde acilir
  * Kaynak gorsel silinirse ya da adres degisirse sayfada kirik gorsel kalir

KONU BASINA HAVUZ
-----------------
Her habere ayri fotograf indirmiyoruz. Konu basina kucuk bir havuz tutulup
haberin adresine gore belirlenimci sekilde secim yapiliyor: ayni haber her
zaman ayni fotografi alir, konu gorsel dili tutarli kalir, ve indirilen
dosya sayisi sinirli olur.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
from dataclasses import dataclass

import httpx

UC = "https://api.openverse.org/v1/images/"
BASLIKLAR = {"User-Agent": "Netaris/1.0 (finans arastirma; ercandrgt90@gmail.com)"}
ZAMAN_ASIMI = 40.0

#: IKINCI KAYNAK -- Wikimedia Commons.
#:
#: NEDEN: Openverse bu makineden once 429 (Cloudflare dogrulamasi),
#: sonra 69 sorgunun 69'unda 401 dondurdu. Yani havuz TEK bir API'ye
#: bagliydi ve o API kapaninca hic fotograf inmedi -- 26 varlik havuzu
#: bos kaldi, butun jeopolitik haberler dort gorseli paylasti.
#:
#: Commons'in iki ustunlugu var:
#:   * `iiurlwidth` ile SUNUCU TARAFINDA olcekleme. 4 MB'lik bir dosya
#:     900 piksele indirilmis haliyle geliyor; Pillow'a gerek kalmiyor.
#:   * Lisans ve yazar bilgisi `extmetadata` icinde yapisal duruyor,
#:     metinden cikarmak gerekmiyor.
#:
#: Openverse KALDIRILMADI: calistigi yerde (CI) iki kaynak birden daha
#: genis ve daha az tekrarli bir havuz demek.
COMMONS_UC = "https://commons.wikimedia.org/w/api.php"

#: Commons'tan istenecek genislik = HABER SUTUNUNUN GENISLIGI.
#:
#: `.yazi` kurali `max-width: 800px`; gorsel sayfada en fazla bu kadar
#: yer kapliyor. Daha buyugunu indirmek bant genisligi ve depo israfi,
#: daha kucugunu indirmek buyutulmus/bulanik gorsel demek.
#:
#: Olculdu: 1100 piksel 465 KB, 900 piksel ortalama 180 KB getiriyor.
#: Gorseller git gecmisine giriyor ve oradan bir daha cikmiyor -- bu
#: sayi dogrudan deponun kalici agirligi.
# 800 -> 1600.
#
# Olculdu (2026-08-23): havuzdaki JPEG'lerin medyan genisligi 960
# piksel. Kart yuvasi 800, manset yuvasi daha genis ve RETINA
# ekranda tarayici iki kat piksel istiyor. Sonuc: her gorsel bir tik
# yumusak, hicbiri "profesyonel" gorunmuyordu.
#
# Kullanicinin karsilastirdigi referans gorsel 1200 piksel genisligindeydi
# ve aradaki fark tam olarak buydu.
#
# `iiurlwidth` sunucu tarafinda olcekliyor: 6000 piksellik kaynak
# dosya indirilmiyor, Commons 1600'e indirip veriyor. Yani bant
# genisligi maliyeti kaynak dosyanin buyuklugune bagli DEGIL.
COMMONS_GENISLIK = 1600

#: Commons lisans kodlarini kabul listemize cevirir. `extmetadata`
#: icindeki makine okunur `License` alani kullaniliyor; gorunur ad
#: ("CC BY-SA 4.0") surumden surume degisebiliyor.
_COMMONS_LISANS = {
    "cc0": "cc0", "pd": "pdm", "cc-pd-mark": "pdm",
    "public domain": "pdm",
}

_KOK = pathlib.Path(__file__).parent.parent.parent
FOTO_KLASORU = _KOK / "site" / "statik" / "foto"
KAYIT_YOLU = pathlib.Path(__file__).parent / "foto_kayit.json"

#: Konu -> sirali arama terimleri. Ingilizce aranir; Openverse'te Turkce
#: etiketli gorsel sayisi cok az.
#:
#: DIKKAT: Openverse butun terimleri AND'liyor. "oil pump jack refinery"
#: SIFIR sonuc doner cunku dort etiketi birden tasiyan gorsel yok. Iki-uc
#: kelimelik sorgular calisiyor; havuz dolana kadar sirayla denenir.
#: Her konu icin en az iki terim olmali: ilki bos donerse sonrakine
#: geciliyor. Terimler `besleme.KONU_ISARETLERI` ile birebir ayni
#: anahtarlari kullanir -- test bunu dogruluyor, cunku eksik anahtar
#: fotografsiz habere yol aciyor ve hicbir hata firlatmiyor.
KONU_ARAMA = {
    "Enerji": ("oil pump jack", "oil refinery", "oil rig", "petroleum"),
    # Catisma gorseli ARANMIYOR: haber sayfasinin gorseli olayin siddetini
    # degil, konusunu isaret etmeli. Diplomasi, liman ve konteyner
    # gorselleri hem dogru hem izleyiciyi rahatsiz etmeyen secim.
    "Jeopolitik": ("diplomacy meeting", "united nations", "cargo ship port",
                   "shipping containers", "world map"),
    "Para politikası": ("federal reserve", "central bank", "bank building"),
    "Enflasyon": ("supermarket shopping", "grocery store", "market prices"),
    "Bankacılık": ("bank building", "financial district", "skyscraper finance"),
    "Piyasa düzenlemesi": ("stock exchange", "trading floor", "wall street"),
    "Düzenleme": ("courthouse", "government building", "capitol"),
    "Döviz": ("currency exchange", "banknotes", "money exchange"),
    "Altın ve emtia": ("gold bars", "gold bullion", "precious metal"),
    "Kripto varlıklar": ("bitcoin", "cryptocurrency", "blockchain"),
    "Borsa": ("stock exchange", "trading floor", "stock market"),
    "Dış ticaret": ("container port", "cargo ship", "shipping containers"),
    "İstihdam ve ücret": ("factory workers", "office workers", "job interview"),
    "Konut ve kira": ("apartment buildings", "housing construction", "real estate"),
    "Vergi ve kamu maliyesi": ("tax forms", "government building", "parliament"),
    "Tarım ve gıda": ("wheat field", "farm tractor", "harvest"),
    "Turizm": ("hotel resort", "airport terminal", "tourists"),
    "Şirket haberleri": ("office building", "corporate headquarters", "boardroom"),
}

#: VARLIK BAZLI SORGULAR -- konu havuzundan ONCE bakiliyor.
#:
#: NEDEN: konu havuzu "Jeopolitik" icin genel diplomasi gorseli
#: veriyor. Hurmuz Bogazi haberiyle Kuzey Kore fuzesi ayni fotografi
#: aliyor -- ikisi de jeopolitik, ama ayni gelisme degil.
#:
#: Varlik indeksi haberin METNINDEN cikiyor ve cok daha ozgul: bir
#: haber IR (Iran) varligina baglanmissa "strait of hormuz" sorgusu,
#: BRENT'e baglanmissa "oil tanker" sorgusu dogru gorseli getirir.
#:
#: KONU HAVUZU KALDIRILMADI: varligi olmayan ya da burada tanimli
#: olmayan varliga baglanan haber yine konu havuzunu kullaniyor.
#: Eksik bir eslesme, yanlis eslesmeden iyidir.
VARLIK_ARAMA = {
    "IR": ("strait of hormuz", "oil tanker persian gulf", "tehran"),
    "RU": ("moscow kremlin", "russia pipeline", "gas pipeline"),
    "CN": ("shanghai port", "china factory", "container terminal china"),
    "US": ("washington capitol", "wall street", "new york stock exchange"),
    "EA": ("european central bank", "brussels european commission"),
    "TR": ("istanbul bosphorus", "ankara", "turkish lira"),
    "BRENT": ("oil tanker", "offshore oil platform", "crude oil barrels"),
    "WTI": ("oil pump jack texas", "crude oil barrels"),
    "DGAZ": ("natural gas pipeline", "lng terminal", "gas compressor"),
    "XAU": ("gold bars", "gold bullion vault"),
    "XAG": ("silver bars", "silver bullion"),
    "XCU": ("copper wire", "copper mine"),
    # BINA ONCE, KISI SONRA. "federal reserve chair" sorgusu gorevdeki
    # kisiyi getiriyor ve o kisi degisince havuz sessizce eskiyor.
    # Bina her donemde dogru; kisi adi ayrica ve ACIKCA yaziliyor ki
    # degistiginde nereyi guncelleyecegimiz belli olsun.
    # KISI ONCE, BINA SONRA -- ama kisi sorgusu havuzun kucuk bir
    # kismini dolduruyor cunku Commons'ta gorevdeki baskanin birkac
    # fotografi var. Gerisini bina tamamliyor: baskana ozel haberde
    # baskan, kurum haberinde bina cikiyor.
    "FED": ("kevin warsh", "federal reserve building",
            "federal reserve bank"),
    "ECB": ("european central bank frankfurt", "euro currency"),
    "TCMB": ("central bank of turkey", "turkish lira banknotes"),
    # ARSIV ESIGI SORGUYU DA DEGISTIRDI: "stock exchange trading floor"
    # 1956 Toronto ve tarihsiz New York arsivi getiriyordu. Guncel
    # gorsel dondurenler onde.
    "BIST100": ("borsa istanbul", "istanbul financial center",
                "stock exchange building", "stock market screen"),
    "BTC": ("bitcoin atm", "cryptocurrency exchange screen",
            "cryptocurrency mining"),
    # "factory workers" 1913 grev ve 1920 fabrika arsivi getiriyordu.
    "NFP": ("job fair", "hiring sign", "job interview",
            "employment office"),
    "CPI_US": ("supermarket usa", "grocery prices"),
    "TUFE_TR": ("turkish market bazaar", "supermarket shopping"),
    "SEK_BANKA": ("bank branch", "financial district"),
    "SEK_ENERJI": ("power plant", "electricity grid"),
    "SEK_OTOMOTIV": ("car factory robot", "automobile assembly robot",
                     "car factory"),
    "SEK_TURIZM": ("hotel resort", "airport terminal"),
    "SEK_INSAAT": ("construction site", "housing construction"),
    "SEK_PERAKENDE": ("supermarket aisle", "shopping mall interior",
                      "retail store"),
}

#: CALISTIRMA BASINA EN COK KAC API ISTEGI.
#:
#: Olculdu: havuzu tek seferde doldurmak 96 istek uretiyor ve kaynak
#: bunu hemen sinirlayip Cloudflare dogrulama sayfasi donduruyor (429).
#: Yani "hepsini simdi indir" yaklasimi hicbir sey indirmiyor.
#:
#: Hat yarim saatte bir calisiyor. Calistirma basina alti istekle havuz
#: birkac saatte doluyor ve kaynak hic zorlanmiyor. Yavas dolan bir
#: havuz, hic dolmayandan iyidir.
CALISTIRMA_ISTEK_SINIRI = 6

#: Istekler arasi bekleme (saniye). Ucretsiz ve acik bir servise ard
#: arda istek yagdirmamak icin.
ISTEK_ARASI = 1.5

#: Konu basina indirilecek fotograf sayisi
# HAVUZ 4 -> 12.
#
# Olculdu: 28 sayfali haberde 16 farkli fotograf vardi ve
# `jeopolitik-2.jpg` BES haberde birden goruluyordu. Konu bazli secim
# dogru calisiyor -- sorun secimde degil, havuzun darliginda: konu
# basina dort fotografla 260 sayfada tekrar kacinilmaz.
#
# ONCEDEN INDIRILENLER KORUNUYOR: `doldur` havuz dolu degilse eksigi
# tamamliyor, mevcutlari silmiyor. Yani bu degisiklik bir sonraki
# calistirmada konu basina sekiz fotograf daha indirir ve orada durur.
#
# Ucretsiz servise saygi: havuz dolduktan sonra AG ISTEGI YAPILMIYOR.
#: Varsayilan 12 -> 6. `HAVUZ_OZEL`de adi gecmeyen havuzlar, haberlerde
#: dorder kez ya da daha az gecen varliklar: alti gorsel orada zaten
#: tekrarsiz. Buyuk havuzlar yukarida ayrica tanimli.
HAVUZ = 6

#: HAVUZ TALEBE GORE. Konulara esit dagitilmis havuz, carpik talebe
#: karsi tekrari GARANTI eder: 34 sayfali haberin 19'u jeopolitikti ve
#: o konuya da diger 17 konuya da dorder fotograf dusuyordu -- sonuc
#: `jeopolitik-2.jpg`in dokuz haberde gorunmesi oldu.
#:
#: Sayilar depodan olculdu (`haber_varlik` sayimi): US 84, TR 46,
#: FED 37, IR 30, TCMB 25, BRENT 21, TUFE_TR 18 gecis. Havuz bu
#: siralamayi izliyor. Burada olmayan anahtar `HAVUZ` kadar aliyor.
#: Sayilar OLCULEREK secildi ve bilerek kucuk tutuldu: her fotograf
#: ortalama 145 KB ve depoya kalici olarak giriyor. Butun havuzlari 12'ye
#: cikarmak 59 MB demekti -- deponun kendisi 51 MB. Dengeli dagitimla
#: (`insa.foto_dagit`) tekrar sayisi = haber / havuz oldugu icin, on
#: fotograflik bir havuz US'in 84 haberinde 8 tekrara, IR'in 30
#: haberinde 3 tekrara denk geliyor; okurun bir oturumda gordugu
#: pencerede bu gorunmuyor.
HAVUZ_OZEL = {
    "US": 12, "TR": 12, "FED": 10, "IR": 14, "TCMB": 10, "BRENT": 10,
    "Jeopolitik": 12, "Enerji": 10,
    "TUFE_TR": 6, "XAU": 6, "BIST100": 6, "NFP": 6, "CPI_US": 6,
    "EA": 6, "RU": 6, "CN": 6,
}

#: Ust boyut siniri. Pillow kurulu olmadigi icin yeniden
#: boyutlandiramiyoruz. 900 KB'den 400 KB'ye CEKILDI: fotograflar depoya
#: giriyor ve git gecmisinden bir daha cikmiyor. Olculdu -- kullanilabilir
#: gorsellerin cogu zaten 60-150 KB araliginda (Hurmuz aramasinda 74,
#: 59 ve 104 KB); ust sinir yalnizca aykirilari eliyor. 72 dosya 11 MB
#: tutuyordu ve tek bir 813 KB'lik dosya ortalamayi bozuyordu.
#:
#: Kucuk resim ucu (`thumbnail`) DENENDI ve VAZGECILDI: ayni aramada iki
#: sonucta 0 bayt ve JPEG olmayan icerik dondu, yani guvenilmez.
EN_FAZLA_BAYT = 400_000

#: EDITORYAL RED. Baslikta bunlardan biri geciyorsa gorsel ALINMAZ.
#:
#: Olculdu: "strait of hormuz" aramasi ucuncu sirada "Iran Air 655"
#: yolcu ucagi faciasinin gorselini donduruyor. Petrol sevkiyati
#: haberinin yaninda o fotograf, haberin soylemedigi bir sey soyler.
#:
#: Ayni gerekce `KONU_ARAMA["Jeopolitik"]` yorumunda da yaziyor:
#: gorsel olayin SIDDETINI degil KONUSUNU isaret etmeli. Orada sorguyu
#: secerek yapiliyordu; burada sonucu eleyerek.
YASAK_BASLIK = (
    # Facia ve siddet
    "crash", "disaster", "casualt", "victim", "funeral", "wreck",
    "bombing", "airstrike", "missile", "corpse", "massacre", "shooting",
    "wounded", "refugee camp", "protest clash", "riot",
    # ASKERI DONANIM. Olculdu: "strait of hormuz" aramasindan gelen 14
    # gorselin 7'si Bogaz'dan gecen ABD savas gemisiydi -- ucak gemisi,
    # kruvazor, muhafaza botu. Petrol sevkiyati ve muzakere haberinin
    # yaninda savas gemisi, haberin SOYLEMEDIGI bir sey soyler.
    #
    # Ayni aramadan gelen NASA uydu goruntusu, EIA petrol akis semasi ve
    # Bogaz haritasi tam da aranan gorsel; suzgec onlari tutuyor.
    "navy", "naval", "warship", "aircraft carrier", "destroyer",
    "frigate", "cutter", "uss ", "hms ", "submarine", "military",
    "soldier", "troops", "marines", "armed forces", "fighter jet",
    "air force", "army", "combat", "weapon",
    # "Iran Air 655 Strait of hormuz 80.jpg" bu listeyi asiyordu: adinda
    # facia bildiren bir kelime yok, cunku gorsel faciANIN KENDISI degil
    # OLAY HARITASI ("Incident map images" kategorisinde). Kategori
    # metni de tarandigi icin tek kelime yetiyor.
    "incident",
    "carrier strike", "strike group",
    # SPOR. Olculdu: CN havuzuna "Shanghai Port and Beijing Guoan
    # players" indi -- "Shanghai Port" bir FUTBOL KULUBU'nun adi ve
    # arama liman sanip getirdi. Kur savasi haberinin yaninda futbol
    # maci fotografi.
    "players", "football", "soccer", "stadium", "league", "match ",
    " fc ", "basketball", "olympic",
    # LOGO ve amblem: kurumsal isaret, haber gorseli degil.
    "logo", "coat of arms", "emblem",
)

#: ARSIV ESIGI. Bundan onceki bir yili anan gorsel alinmiyor.
#:
#: Olculdu: NFP (ABD istihdam) havuzunun yarisi arsivdi -- "Garment
#: Workers on Strike, New York City circa 1913", "Damm factory workers
#: 1920", "SS Tiger (1917)". 2026 istihdam raporunun yaninda 1913
#: grev fotografi, okura o donemin haberi gibi gorunur.
#:
#: Harita ve sema disarida tutulmuyor: eski bir harita da eski bir
#: fotograf kadar yaniltici. Guncel haritalar zaten aramada cikiyor.
ARSIV_YILI = 1990
_YIL = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")

#: GOREVDEN AYRILMIS KISILER -- kurum havuzlarindan cikariliyor.
#:
#: Kurum fotograflari kisi tasidiginda BOZULUYOR: kisi gider, fotograf
#: kalir ve haber yanlis insanla resimlenir. Olculdu -- FED havuzunda
#: uc Powell fotografi vardi ve dort sayfada basiliyordu, oysa kendi
#: haber akisimiz 7 ve 10 Agustos'ta "Fed Baskani Warsh" diyor.
#:
#: BU LISTE BAKIM ISTER ve istemesi kacinilmaz: gorev degisikligini
#: kod anlayamaz. Degisiklik duyuldugunda buraya bir satir eklenir.
#:
#: ASIL KORUMA SORGUDA: kurum havuzlarinin sorgulari BINAYA oncelik
#: veriyor (bkz. VARLIK_ARAMA["FED"]). Bina degismez; kisi degisir.
GECMIS_GOREVLI = (
    "jerome powell", "jerome h. powell",
)

#: SAVAS GEMISI GOVDE KODU. Bazi gorseller yalnizca kodla adlandirilmis:
#: "CVN 69 transits the Strait of Hormuz" -- baslikta tek bir yasakli
#: kelime yok. Arama sirasinda KATEGORIDEN ("United States Navy")
#: yakalaniyorlardi, ama kategori her zaman dolu gelmiyor ve indirilmis
#: bir gorseli sonradan elemek gerektiginde elde yalnizca dosya adi
#: kaliyor. Kod dogrudan taniniyor.
_ASKERI_KOD = re.compile(
    r"\b(cvn|cgn|cg|ddg|lha|lhd|lpd|ssbn|ssn|ffg|wpc|wmsl|whec|wagb)"
    r"[\s\-_]?\d{1,3}\b|\b(uscgc|usns|hmnzs|hmcs)\b",
    re.I)

#: Kabul edilen lisanslar. ND (NoDerivatives) DISARIDA: kart icinde
#: `object-fit: cover` ile kirpiyoruz ve kirpmanin turev sayilip
#: sayilmadigi tartismalidir. Tartismali olani hic almamak basit.
KABUL_LISANSLAR = ("by", "by-sa", "cc0", "pdm")


@dataclass(frozen=True)
class Foto:
    dosya: str        # /statik/foto/... site ici yol
    atif: str         # "X" by Y is licensed under CC BY 2.0
    lisans: str
    kaynak: str       # orijinal sayfa adresi
    #: Baslik ve kategori metni. VARSAYILANI BOS -- eski kayitlar bu
    #: alan olmadan yazildi ve `Foto(**f)` onlari da okuyabilmeli.
    #:
    #: Neden saklaniyor: editoryal suzgec indirme aninda BASLIK ve
    #: KATEGORI uzerinden calisiyor, ama kayitta yalnizca dosya adresi
    #: duruyordu. Suzgec sonradan siklastirilinca indirilmis gorselleri
    #: yeniden eleyemedim: savas gemileri govde koduyla adlandirilmis
    #: ("CVN 69 transits...") ve dosya adinda yasakli kelime yok --
    #: arama sirasinda KATEGORIDEN yakalanmislardi. Bu alanla ayni
    #: suzgec gecmise de uygulanabiliyor.
    kunye: str = ""
    #: Gorseli getiren arama terimi. Bkz. kayit yazimi.
    sorgu: str = ""

    @property
    def kisa_atif(self) -> str:
        """Gorsel altinda basilacak kisa atif: 'Ad · CC BY 2.0'.

        IKI KAYNAK, IKI BICIM. Openverse atfi bir CUMLE olarak veriyor
        ('"Baslik" by Ad is licensed under...'), Commons ise yazar adini
        ayri bir alanda. Desen yalnizca Openverse'e gore yazilmisti ve
        Commons'tan gelen ondort gorselin hepsi "bilinmeyen · PDM" diye
        basildi -- CC BY atfi zorunludur, bu bir lisans ihlaliydi.
        """
        m = re.search(r'"[^"]*"\s+by\s+(.+?)\s+is licensed', self.atif)
        if m:
            kim = m.group(1).strip()
        else:
            # Commons bicimi: "Yazar · CC BY-SA 4.0". Lisans adi zaten
            # ayrica basiliyor, bastaki yazar kismi aliniyor.
            kim = (self.atif or "").split(" · ")[0].strip()
        return f"{_atif_duzelt(kim) or 'bilinmeyen'} · {self.lisans.upper()}"


def _atif_duzelt(ad: str) -> str:
    """Atif metnindeki YAZIM artiklarini temizler -- ADI DEGISTIRMEDEN.

    Commons'un yazar alani kaynagindan bozuk geliyor:

        "Kurzycz , https://www.kurzy.cz/"
        "The original uploader was Alex Needham at English Wikipedia ."

    Noktalama oncesi bosluk Turkce'de de Ingilizce'de de yanlis ve
    sayfada gorunuyordu (olculdu: nokta/virgul oncesi bosluk iceren
    dokuz atif).

    YALNIZCA BOSLUK DUZELTILIYOR. Atif hukuken zorunlu ve SADIK olmali;
    ad kisaltilmiyor, yeniden yazilmiyor, yalnizca fazla bosluklar
    kaldiriliyor. Sonundaki noktalama da atiliyor -- ardindan zaten
    " · LISANS" geliyor.
    """
    if not ad:
        return ""
    # GERI GORUNUM YERINE LAMBDA.
    #
    # Once r"\1" yazdim; heredoc uzerinden dosyaya yazilirken
    # kacis bozuldu ve desen bir DENETIM KARAKTERINE donustu.
    # Sonuc: "Kurzycz ," metni "Kurzycz\x01" oldu -- yani
    # noktalamayi duzeltmek yerine gorunmez cop uretti.
    # Sinama yakaladi.
    #
    # Bu depoda heredoc ile regex yazmak tekrarlayan bir tuzak.
    # Lambda hem kacistan bagimsiz hem niyeti acik.
    ad = re.sub(r"\s+([,.;:])", lambda m: m.group(1), ad)
    ad = re.sub(r"\s{2,}", " ", ad).strip()
    return ad.rstrip(" ,.;:-")


class Kayit:
    """Indirilen gorsellerin defteri -- konu -> foto listesi."""

    def __init__(self, yol: pathlib.Path = KAYIT_YOLU):
        self.yol = yol
        self.veri: dict[str, list[dict]] = {}
        if yol.exists():
            try:
                self.veri = json.loads(yol.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.veri = {}

    def kaydet(self) -> None:
        self.yol.write_text(
            json.dumps(self.veri, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def havuz(self, konu: str) -> list[Foto]:
        return [Foto(**f) for f in self.veri.get(konu, [])]

    def varlik_sec(self, varliklar, konu: str, tohum: str):
        """Once VARLIGA, yoksa konuya gore gorsel secer.

        `varliklar` haberin varlik kodlari (varlik indeksinden).
        Birden fazla varlik varsa TOHUMA gore biri seciliyor -- ilkini
        almak, ayni varlik cifti gecen butun haberlere ayni gorseli
        vermek olurdu.

        Varlik havuzu bos ya da tanimsizsa KONU havuzuna dusuyor.
        """
        kodlar = [k for k in (varliklar or []) if k in VARLIK_ARAMA]
        if kodlar:
            i = int(hashlib.sha256((tohum + "v").encode("utf-8")).hexdigest(),
                    16) % len(kodlar)
            f = self.sec(kodlar[i], tohum)
            if f:
                return f
        return self.sec(konu, tohum)

    #: Atif GEREKTIRMEYEN lisanslar.
    #:
    #: CC BY ve CC BY-SA atfi SART kosuyor; kamu mali (PDM) ve CC0
    #: kosmuyor. Bu ayrim bir kolaylik degil, lisans metninin kendisi.
    ATIFSIZ = frozenset({"cc0", "pdm"})

    def havuz_yayin(self, konu: str) -> list["Foto"]:
        """Yayinda kullanilacak havuz -- ATIFSIZ lisanslar oncelikli.

        `havuz()` ham listeyi veriyor ve sayim/denetim icin oyle kalmali.
        Yayin secimi bu listeden geciyor: atif gerektirmeyen gorsel
        varsa yalnizca onlar, yoksa hepsi.

        Gerekce `sec()` icinde yazili.
        """
        h = self.havuz(konu)
        serbest = [f for f in h if (f.lisans or "").lower() in self.ATIFSIZ]
        return serbest or h

    def sec(self, konu: str, tohum: str) -> Foto | None:
        """Konudan belirlenimci secim -- ayni haber her zaman ayni gorseli alir.

        ATIFSIZ LISANSLAR ONCE DENENIYOR.
        ---------------------------------
        Kullanici geri bildirimi: "fotograflarin altinda aldigin yeri de
        gosterme". Atif satirini SILMEK CC BY icin lisans ihlali -- o
        yuzden satiri silmek yerine ATIF GEREKTIRMEYEN gorsel seciliyor.
        Sonuc okur icin ayni (alt yazi yok), lisans icin dogru.

        Olculdu (2026-08-23): havuzdaki 318 fotografin 133'u (%41) CC0
        ya da kamu mali. Uc konuda hic yok; orada CC BY gorsel kaliyor
        ve atif da kaliyor -- cunku alternatifi ihlal.

        Secim havuz DARALSA BILE belirlenimci: ayni haber her zaman ayni
        gorseli aliyor. Tohum ayni, yalnizca liste farkli.
        """
        h = self.havuz(konu)
        if not h:
            return None
        serbest = [f for f in h if (f.lisans or "").lower() in self.ATIFSIZ]
        liste = serbest or h
        i = int(hashlib.sha256(tohum.encode("utf-8")).hexdigest(), 16) % len(liste)
        return liste[i]


#: Turkce harfleri dosya adinda guvenli karsiliklarina cevirir.
#: `str.lower()` tek basina "Ü" harfini cozmez ve "d-zenleme" gibi bozuk
#: dosya adlari uretir -- bir kez oyle oldu.
_SLUG = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _dosya_adi(url: str, konu: str, sira: int) -> str:
    """Havuz adi + KAYNAK ADRESININ ozeti.

    SIRA NUMARASI TEK BASINA BENZERSIZ DEGIL. Ad `havuz-<sira>` idi ve
    sira `len(mevcut)+1` ile veriliyordu; havuzdan bir gorsel SILININCE
    numaralar kayiyor ve bir sonraki indirme AYNI adi aliyor. Iki farkli
    kayit ayni dosyayi gosteriyor, biri silininince digeri de kiriliyor.

    Olculdu: uc kayit diskte olmayan dosyayi gosteriyordu ve iki sayfada
    KIRIK GORSEL cikti. Ad artik kaynak adresine bagli; ayni gorsel her
    zaman ayni adi, farkli gorsel her zaman farkli adi alir.
    """
    uzanti = pathlib.Path(url.split("?")[0]).suffix.lower()
    if uzanti not in (".jpg", ".jpeg", ".png", ".webp"):
        uzanti = ".jpg"
    kisa = re.sub(r"[^a-z0-9]+", "-", konu.translate(_SLUG).lower()).strip("-")
    ozet = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"{kisa}-{sira}-{ozet}{uzanti}"


def lisans_kodu(ham: str) -> str:
    """Lisans metnini kabul listemizin koduna cevirir.

    Openverse zaten "by" / "by-sa" diye veriyor. Commons ise tam kodu
    yaziyor: "cc-by-4.0", "cc-by-sa-3.0", "cc-zero", "pd".

    BU CEVIRI OLMADAN BUTUN CC BY GORSELLERI REDDEDILIYORDU. Olculdu:
    "european central bank" aramasinin 24 sonucunun HEPSI lisans
    denetiminde eleniyordu ve EA havuzu bos kaliyordu -- ama sebep
    "uygun lisansli gorsel yok" degil, kodu tanimamamizdi. Havuzlarin
    arsiv/kamu mali gorsellerle dolmasinin sebebi de buydu: yalnizca
    "pd" ve "cc0" gecebiliyordu.

    ND (NoDerivatives) ve NC (NonCommercial) BILINCLI OLARAK disarida:
    kart icinde kirpiyoruz ve site ticari sayilabilir.
    """
    k = (ham or "").lower().strip()
    if k in ("cc0", "cc-zero", "zero"):
        return "cc0"
    if k in ("pd", "pdm", "public domain", "cc-pd-mark", "pd-old"):
        return "pdm"
    if "nd" in re.split(r"[-\s]", k) or "nc" in re.split(r"[-\s]", k):
        return ""
    if k.startswith("cc-by-sa") or k == "by-sa":
        return "by-sa"
    if k.startswith("cc-by") or k == "by":
        return "by"
    return k


def _lisans_uygun(s: dict) -> bool:
    return lisans_kodu(s.get("license") or "") in KABUL_LISANSLAR


#: Erisilemeyen fotograf sorgulari. `hazirla` her cagrida temizler.
OKUNAMAYAN: list[tuple[str, str, str]] = []

#: Bu calistirmada yapilan istek sayisi. `hazirla` sifirliyor.
_ISTEK = {"n": 0}


def _openverse_ara(sorgu: str, adet: int) -> list[dict]:
    """Openverse'te arar. Sonuc bicimi zaten bizim bekledigimiz bicim."""
    r = httpx.get(UC, params={
        "q": sorgu,
        "license_type": "commercial",
        "page_size": adet * 4,      # bir kismi elenecek
        "mature": "false",
    }, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    return r.json().get("results", [])


def _metni_ayikla(html_metni: str) -> str:
    """Commons `Artist` alanindaki HTML'i duz metne cevirir."""
    m = re.sub(r"<[^>]+>", " ", html_metni or "")
    return " ".join(m.replace("&amp;", "&").split())[:120]


def _commons_ara(sorgu: str, adet: int) -> list[dict]:
    """Commons'ta arar ve sonuclari OPENVERSE BICIMINE cevirir.

    Ayni bicime cevrilmesi bilincli: `doldur` icindeki indirme, lisans,
    editoryal ve tekrar suzgecleri iki kaynak icin de ayni kodda kaliyor.
    Ayri bir indirme dongusu yazmak, suzgeclerden birini bir kaynakta
    unutmaya davetiye olurdu.

    `filetype:bitmap` SART: filtresiz arama PDF donduruyor -- "Iran and
    the Strait of Hormuz" aramasinda ilk alti sonucun ucu akademik PDF'ti.
    """
    r = httpx.get(COMMONS_UC, params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{sorgu} filetype:bitmap",
        "gsrnamespace": "6", "gsrlimit": str(min(adet * 4, 50)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": str(COMMONS_GENISLIK),
    }, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    cikti = []
    for sayfa in (r.json().get("query", {}).get("pages", {}) or {}).values():
        bilgi = (sayfa.get("imageinfo") or [{}])[0]
        if bilgi.get("mime") not in ("image/jpeg", "image/png"):
            continue
        kucuk = bilgi.get("thumburl")
        if not kucuk:
            continue
        # BOYUT DENETIMI. `iiurlwidth` yalnizca KUCULTUYOR; kaynak
        # gorsel 32 piksel genisse cikti da 32 piksel kaliyor ve sayfada
        # 800 piksele YAYILIYOR.
        #
        # Olculdu ve YAYIMLANDI: havuzda `enerji-10.png` 32x37,
        # `xag-2.png` 72x30 idi -- bunlar fotograf degil, simge. Haber
        # sayfasinin ust gorseli olarak basildiklarinda tamamen bulanik
        # cikiyorlardi. Kullanicinin "haber resimleri bozuk" dedigi sey
        # buydu.
        #
        # Boyut bilgisi ZATEN isteniyordu (`iiprop: size`) ama hicbir
        # yerde bakilmiyordu.
        if not _boyut_uygun(bilgi.get("width"), bilgi.get("height")):
            continue
        em = bilgi.get("extmetadata", {})
        lisans_ham = (em.get("License", {}).get("value") or "").lower()
        lisans = _COMMONS_LISANS.get(lisans_ham, lisans_ham)
        yazar = _metni_ayikla(em.get("Artist", {}).get("value", ""))
        gorunur = em.get("LicenseShortName", {}).get("value", "")
        sayfa_adresi = bilgi.get("descriptionurl") or kucuk
        # ATIF ZORUNLU. Yazar bilinmiyorsa kamu malinda bile kaynak
        # yazilmali -- okur gorselin nereden geldigini gorebilmeli.
        atif = " · ".join(x for x in (yazar or "Wikimedia Commons",
                                      gorunur) if x)
        cikti.append({
            "url": kucuk,
            "attribution": atif,
            "foreign_landing_url": sayfa_adresi,
            "license": lisans,
            "license_version": "",
            "title": sayfa.get("title", ""),
            "tags": [em.get("Categories", {}).get("value", "")],
            # Siralama icin; cagiran taraf disinda kullanilmiyor.
            "_puan": kalite_puani(bilgi),
        })
    # EN IYI ONCE. Arama motoru ALAKAYA gore siraliyor, kaliteye gore
    # degil; ikisi ayni sey degil. Alaka suzgeci ayrica calisiyor
    # (`_DOLGU` ve baslik eslemesi), burada kalan adaylar arasindan
    # basmaya en uygun olani one aliniyor.
    cikti.sort(key=lambda x: -x.get("_puan", 0.0))
    return cikti


#: KAYNAK COZUNURLUGU KALITE ISARETI.
#:
#: Olculdu: ayni sorguda 6000x4000 profesyonel bir cekim ile 912x684
#: amatör bir enstantane yan yana donuyor ve secim ARALARINDA AYRIM
#: YAPMIYORDU. Ana sayfada cikan altin gorseli ikinci turdendi --
#: uzerinde yesil sansur kutulari olan bir sertifika fotografi.
#:
#: Cozunurluk kaliteyi GARANTI ETMEZ ama guclu bir gostergedir:
#: Commons'a 6000 piksel yukleyen kisi genellikle ekipmanla ve
#: niyetle cekmistir. Elimizde gorsel degerlendirme yok; olcebildigimiz
#: en iyi vekil bu.
#:
#: Esik degil AGIRLIK: kucuk gorsel elenmiyor, sadece geride kaliyor.
#: Elemek dar havuzlari bosaltirdi.
IYI_GENISLIK = 2000

#: Manset ve kart yuvalari 16:9. Bu orana yakin gorsel KIRPILMADAN
#: oturuyor; kare ya da dikey gorselden kadrajin ucta biri gidiyor ve
#: cogu zaman konunun kendisi kesiliyor.
IDEAL_ORAN = 16 / 9


def kalite_puani(bilgi: dict) -> float:
    """Aday gorsel icin 0-1 arasi kaba kalite puani.

    Iki bilesen: cozunurluk ve en-boy orani. Ikisi de OLCULEBILIR;
    "guzel mi" sorusunu cevaplamiyor, "basmaya uygun mu" sorusunu
    cevapliyor. Aradaki farki abartmamak icin puan siralama disinda
    hicbir yerde kullanilmiyor.
    """
    try:
        g = int(bilgi.get("width") or 0)
        y = int(bilgi.get("height") or 0)
    except (TypeError, ValueError):
        return 0.0
    if g <= 0 or y <= 0:
        return 0.0
    coz = min(g / IYI_GENISLIK, 1.0)
    oran = g / y
    # Orandan sapma 0 (tam) ile 1 (cok uzak) arasina getiriliyor.
    sapma = min(abs(oran - IDEAL_ORAN) / IDEAL_ORAN, 1.0)
    return 0.65 * coz + 0.35 * (1.0 - sapma)


#: Sorgu ilgisini olcerken atlanacak kelimeler.
_DOLGU = frozenset({"of", "the", "and", "in", "at", "for", "a", "an"})


#: Havuza girecek gorselin EN AZ olcusu.
#:
#: Haber sayfasindaki gorsel sutunu 800 piksel. Commons'in olcekleme
#: ucu yalnizca KUCULTUYOR -- kaynak daha darsa cikti da dar kaliyor ve
#: tarayici onu 800'e YAYIYOR. 640, retina olmayan ekranda kabul
#: edilebilir bir alt sinir; altina inince bulaniklik gorunur oluyor.
EN_AZ_GENISLIK = 640
EN_AZ_YUKSEKLIK = 360

#: En/boy oraninin ust ve alt siniri.
#:
#: Kartlar ve ust gorsel 16:9 (1,78) cerceve kullaniyor ve CSS
#: `object-fit: cover` ile kirpiyor. Kaynak bu orandan ne kadar
#: uzaksa o kadar cok goruntu kirpiliyor.
#:
#: OLCULDU: 331 gorselin 67'si 16:9'a girince iceriginin %38'inden
#: fazlasini kaybediyordu; en kotusu 960x1707 dikey bir fotografti ve
#: %68'i gidiyordu -- okur binanin ince bir dilimini goruyordu.
#: Kullanicinin "resimler bozuk gorunuyor" dedigi sey buydu.
#:
#: Alt sinir 0,5'ten 1,2'ye cikti: DIKEY fotograf 16:9 cerceveye
#: sigmaz. 1,2'de kayip en fazla %33 -- bu kirpma, kadraj tercihi
#: sayilabilecek olculerde.
EN_COK_ORAN = 2.4
EN_AZ_ORAN = 1.2


def _boyut_uygun(genislik, yukseklik) -> bool:
    """Gorsel haber sayfasinda basilacak kadar buyuk ve makul oranli mi?

    Olcu OKUNAMAZSA gecirilir: Commons alanlari her zaman dolu gelmiyor
    ve olcemedigimiz bir seye dayanip gorseli atmak, havuzu sebepsiz
    daraltir. Elenen sey "supheli" degil, OLCULMUS sekilde kucuk olan.
    """
    try:
        g = int(genislik)
        y = int(yukseklik)
    except (TypeError, ValueError):
        return True
    if g <= 0 or y <= 0:
        return True
    if g < EN_AZ_GENISLIK or y < EN_AZ_YUKSEKLIK:
        return False
    oran = g / y
    return EN_AZ_ORAN <= oran <= EN_COK_ORAN


def _ilgili(s: dict, sorgu: str, siki: bool = True) -> bool:
    """Sonuc gercekten SORGUYLA ilgili mi?

    Commons aramasi bulanik ve alakasiz sonuc donduruyor. Olculdu:
      * "borsa istanbul"  -> "De Bist beuk" (Hollandaca kayin agaci),
                             "Der du bist drei in Einigkeit (1799)"
      * "central bank of turkey" -> "Albania CentralBank Durres"
      * "ankara"          -> "Ankara Opera Bale", kilise konseri
    Ucu de arama motoru acisindan "eslesme"; okur acisindan hata.

    Kural: sorgunun her anlamli kelimesi baslikta ya da kategorilerde
    GECMELI. "borsa istanbul" arayan bir sonucta hem "borsa" hem
    "istanbul" olmali -- "bist" yetmez.

    `siki=False` cogunlugu yeterli sayar. Havuz siki eleme sonrasi
    bosalirsa buna dusuluyor: alakasiz gorsel kotu, ama fotografsiz
    haber de kotu.
    """
    metin = (f"{s.get('title') or ''} "
             f"{' '.join(str(t) for t in (s.get('tags') or []))}").lower()
    kelimeler = [k for k in re.split(r"[\s\-_]+", sorgu.lower())
                 if len(k) >= 3 and k not in _DOLGU]
    if not kelimeler:
        return True
    var = sum(1 for k in kelimeler if k in metin)
    return var == len(kelimeler) if siki else var * 2 >= len(kelimeler)


def _kunye_anahtari(kunye: str) -> str:
    """Basligin ilk anlamli kelimeleri -- yakin kopya tespiti icin."""
    ad = kunye.replace("File:", "").rsplit(".", 1)[0].lower()
    kelime = [k for k in re.split(r"[\s\-_,()]+", ad) if len(k) >= 3]
    return " ".join(kelime[:5])


def _yakin_kopya(kunye: str, mevcut: list[dict]) -> bool:
    """Havuzda AYNI OLAYIN baska bir karesi var mi?

    Commons ayni etkinlikten onlarca kare tutuyor. Olculdu: FED havuzuna
    "President Donald Trump speaks to Fed Chair Jerome Powell during..."
    basligiyla BES ayri gorsel indi -- hepsi ayni anin farkli karesi.
    Havuzu buyutmek boyle bir havuzda tekrari azaltmiyor: okur bes farkli
    haberde ayni sahneyi goruyor, dosya adlari farkli olsa bile.

    Olcut basligin ilk bes anlamli kelimesi. Ayni etkinlikten kareler
    Commons'ta ayni onekle adlandiriliyor; farkli gorsellerin ilk bes
    kelimesinin ayni olmasi ise beklenmez.
    """
    anahtar = _kunye_anahtari(kunye)
    if not anahtar:
        return False
    return any(_kunye_anahtari(f.get("kunye") or "") == anahtar
               for f in mevcut)


def _editoryal_uygun(s: dict) -> bool:
    """Baslik siddet/facia bildiriyorsa gorseli reddeder."""
    metin = f"{s.get('title') or ''} {' '.join(str(t) for t in (s.get('tags') or []))}"
    kucuk = metin.lower()
    if any(k in kucuk for k in YASAK_BASLIK):
        return False
    if _ASKERI_KOD.search(metin):
        return False
    if any(k in kucuk for k in GECMIS_GOREVLI):
        return False
    # ESKI TARIH. Metinde gecen EN KUCUK yil esige bakiliyor: bir
    # gorsel hem "1913" hem "2020" tasiyabilir (arsivin dijitallestirme
    # tarihi), ve o durumda icerik eski olandir.
    yillar = [int(y) for y in _YIL.findall(metin)]
    return not (yillar and min(yillar) < ARSIV_YILI)


def doldur(konu: str, kayit: Kayit, adet: int | None = None) -> int:
    """Konu icin fotograf havuzunu doldurur. Yeni indirilen sayisini doner.

    Havuz zaten doluysa AG ISTEGI YAPILMAZ -- her calistirmada yeniden
    indirmek hem bant genisligi hem de ucretsiz servise saygisizlik olur.

    Sorgular sirayla denenir: ilk sorgu az sonuc verirse ikinciye gecilir.
    """
    if adet is None:
        adet = HAVUZ_OZEL.get(konu, HAVUZ)
    if len(kayit.havuz(konu)) >= adet:
        return 0

    # Varlik kodu da olabilir: "IR", "BRENT"... Konu adiyla ayni
    # fonksiyondan doldurulmasi bilincli -- havuz, dosya adi ve atif
    # mantigi ikisinde de ayni.
    sorgular = VARLIK_ARAMA.get(konu) or KONU_ARAMA.get(konu)
    if not sorgular:
        return 0

    FOTO_KLASORU.mkdir(parents=True, exist_ok=True)
    mevcut = kayit.veri.setdefault(konu, [])
    eklendi = 0
    gorulen = {f["kaynak"] for f in mevcut}

    # IKI TUR. Once butun sorgular SIKI ilgi suzgeciyle deneniyor; havuz
    # hala bossa ayni sorgular gevsek suzgecle tekrarlaniyor.
    #
    # Neden iki tur: siki suzgec "gold bullion vault" gibi uc kelimelik
    # sorgularda havuzu bosaltabiliyor (her uc kelimeyi birden tasiyan
    # gorsel az). Alakasiz gorsel kotu ama fotografsiz haber de kotu.
    # Onceligi dogruluga verip, ancak mecbur kalinca gevsetiyoruz.
    for siki_tur in (True, False):
        if len(mevcut) >= adet:
            break
        eklendi += _tur(konu, kayit, sorgular, mevcut, gorulen, adet, siki_tur)
    return eklendi


def _tur(konu, kayit, sorgular, mevcut, gorulen, adet, siki_tur) -> int:
    eklendi = 0
    for sorgu in sorgular:
        if len(mevcut) >= adet:
            break
        # ISTEK SINIRI: havuz bu calistirmada dolmayabilir ve bu
        # SORUN DEGIL -- bir sonraki calistirma kaldigi yerden devam
        # ediyor (`doldur` mevcutlari koruyup eksigi tamamliyor).
        if _ISTEK["n"] >= CALISTIRMA_ISTEK_SINIRI:
            return eklendi
        if _ISTEK["n"]:
            time.sleep(ISTEK_ARASI)
        _ISTEK["n"] += 1
        # IKI KAYNAK SIRAYLA. Biri kapaliysa digeri deneniyor; ikisi de
        # kapaliysa sorgu OKUNAMAYAN'a yaziliyor.
        #
        # Sira Commons'ta baslıyor cunku olculdu: Openverse bu makineden
        # 69 sorgunun 69'unda 401 dondurdu, Commons ayni anda 200
        # donuyordu. Openverse calisan bir ortamda (CI) yine devrede --
        # iki kaynak, tek kaynaktan genis havuz demek.
        sonuclar = []
        hatalar = []
        for ad, getir in (("commons", lambda: _commons_ara(sorgu, adet)),
                          ("openverse", lambda: _openverse_ara(sorgu, adet))):
            try:
                sonuclar = getir()
            except (httpx.HTTPError, ValueError, KeyError) as e:
                hatalar.append(f"{ad}: {type(e).__name__}")
                continue
            if sonuclar:
                break
        # SESSIZ DEGIL. Kaynak erisilemezse havuz eksik kaliyor ve
        # denetim "ayni fotograf bes haberde" diye uyariyor -- ama
        # SEBEBI hicbir yerde gorunmuyordu. Kaynagin erisilemez olmasi
        # ile o konuda fotograf OLMAMASI ayni sey degil.
        if not sonuclar:
            OKUNAMAYAN.append((konu, sorgu, ", ".join(hatalar) or "sonuc yok"))
            continue

        for s in sonuclar:
            if len(mevcut) >= adet:
                break
            url = s.get("url")
            atif = (s.get("attribution") or "").strip()
            sayfa = s.get("foreign_landing_url") or url
            # Atif metni olmayan gorsel ALINMAZ: CC BY atfi zorunlu kilar
            if not url or not atif or sayfa in gorulen:
                continue
            if not _lisans_uygun(s) or not _editoryal_uygun(s):
                continue
            # ILGI SUZGECI. Once siki; havuz bu turda hic dolmazsa
            # asagida gevsek turla tekrar deneniyor.
            if not _ilgili(s, sorgu, siki=siki_tur):
                continue
            kunye_metni = (f"{s.get('title') or ''} "
                           f"{' '.join(str(t) for t in (s.get('tags') or []))}")
            if _yakin_kopya(kunye_metni, mevcut):
                continue

            try:
                g = httpx.get(url, headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                              follow_redirects=True)
                g.raise_for_status()
                if not g.headers.get("content-type", "").startswith("image/"):
                    continue
                if len(g.content) > EN_FAZLA_BAYT:
                    continue
            except httpx.HTTPError:
                continue

            ad = _dosya_adi(url, konu, len(mevcut) + 1)
            (FOTO_KLASORU / ad).write_bytes(g.content)
            gorulen.add(sayfa)
            mevcut.append({
                "dosya": f"/statik/foto/{ad}",
                "atif": atif,
                "kunye": f"{s.get('title') or ''} "
                         f"{' '.join(str(t) for t in (s.get('tags') or []))}"[:400],
                #: Hangi sorgudan geldigi. Ilgi suzgeci sonradan
                #: siklastirilirsa indirilmis gorseller de ayni olcute
                #: vurulabilsin diye saklaniyor -- `suz()` bunu kullaniyor.
                "sorgu": sorgu,
                "lisans": (s.get("license") or "cc") +
                          (" " + str(s.get("license_version") or "")).rstrip(),
                "kaynak": sayfa,
            })
            eklendi += 1

    return eklendi


#: Gundemde o gun hic haberi olmasa bile havuzu DOLU tutulan konular.
#:
#: Sebep: analiz yazilari da bu havuzdan fotograf aliyor ve onlar gunun
#: haber akisindan bagimsiz. Bir kez oyle oldu -- gunun haberlerinde
#: sirket haberi yoktu, havuz bos kaldi ve TERA bilanco analizi
#: fotografsiz yayimlandi. Hicbir hata mesaji cikmadi.
TEMEL_KONULAR = (
    "Şirket haberleri", "Para politikası", "Enerji", "Enflasyon",
    "Altın ve emtia", "Kripto varlıklar", "Borsa",
)


def hazirla(konular: list[str]) -> Kayit:
    """Verilen konularin havuzlarini doldurup defteri doner.

    `TEMEL_KONULAR` her zaman listeye ekleniyor. `doldur` havuz zaten
    doluysa ag istegi yapmiyor, dolayisiyla bunun gunluk maliyeti yok.
    """
    OKUNAMAYAN.clear()
    _ISTEK["n"] = 0
    kayit = Kayit()
    eksik = []
    for konu in dict.fromkeys(list(konular) + list(TEMEL_KONULAR)):
        n = doldur(konu, kayit)
        if n:
            print(f"  {konu:<20} {n} yeni fotograf")
        elif len(kayit.havuz(konu)) < HAVUZ:
            eksik.append((konu, len(kayit.havuz(konu))))
    kayit.kaydet()

    if OKUNAMAYAN:
        print(f"  UYARI: fotograf kaynagina {len(OKUNAMAYAN)} sorgu "
              f"ulasmadi -- havuz eksik kaliyor")
        for k, s, h in OKUNAMAYAN[:3]:
            print(f"    {k} / {s!r}: {h}")
    if eksik:
        print(f"  {len(eksik)} konuda havuz {HAVUZ}'in altinda: "
              + ", ".join(f"{k}({n})" for k, n in eksik[:6]))
    if _ISTEK["n"] >= CALISTIRMA_ISTEK_SINIRI:
        print(f"  istek siniri ({CALISTIRMA_ISTEK_SINIRI}) doldu -- havuz "
              f"bir sonraki calistirmada kaldigi yerden devam edecek")

    # KUCUK SURUMLER DE BURADA TAMAMLANIYOR.
    #
    # Yeni inen her gorselin akista kullanilabilmesi icin 96 piksellik
    # esi de gerekiyor. Calistirma basina sinirli tutuluyor (bir parti):
    # havuz gibi bunun da yavas dolmasi sorun degil, akis satiri o
    # gorsel inene kadar gorselsiz gorunuyor.
    try:
        n_kucuk = kucuk_uret(kayit, en_cok=KUCUK_PARTI)
        if n_kucuk:
            print(f"  {n_kucuk} kucuk (akis) gorseli indirildi")
        n_orta = orta_uret(kayit, en_cok=KUCUK_PARTI)
        if n_orta:
            print(f"  {n_orta} orta (kart) gorseli indirildi")
    except Exception as e:                                # noqa: BLE001
        print(f"  kucuk gorsel uretilemedi: {type(e).__name__}")
    return kayit


def suz(kayit: Kayit | None = None, uygula: bool = False) -> list[tuple[str, str]]:
    """Indirilmis gorselleri GUNCEL editoryal suzgecten gecirir.

    NEDEN GEREKLI: suzgec yalnizca indirme aninda calisiyordu. Suzgeci
    sonradan siklastirmak, o ana kadar inmis gorsellere hicbir sey
    yapmiyordu -- yani "askeri gorsel kullanmiyoruz" kurali dunku
    fotograflar icin gecerli olmuyordu. Kural degistiginde gecmise de
    uygulanabilmeli.

    `kunye` alani (baslik + kategori) bunun icin saklaniyor. Alani
    olmayan eski kayitlarda dosya adresinden okunuyor: Commons dosya
    sayfasi adresi dosya adini iceriyor.

    `uygula=False` yalnizca RAPORLAR. Silme, acikca istenince yapiliyor.
    """
    import urllib.parse

    kayit = kayit or Kayit()
    cikanlar: list[tuple[str, str]] = []
    for anahtar, liste in list(kayit.veri.items()):
        kalan = []
        for f in liste:
            kunye = f.get("kunye") or urllib.parse.unquote(
                f.get("kaynak", "")).rsplit("File:", 1)[-1].replace("_", " ")
            aday = {"title": kunye, "tags": []}
            # SILME OLCUTU YALNIZCA EDITORYAL SUZGEC.
            #
            # Ilgi suzgecini de silme olcutu yapmayi denedim ve olctum:
            # sekiz adayin DORDU yanlis pozitifti -- "Bandar Imam
            # Khomeini petrokimya tesisi" (Iran haberine tam uygun),
            # "Spice Bazaar" (Turkiye enflasyonuna uygun), "Istanbul
            # Financial Center" (TCMB'ye uygun), "Guadalupe Mountains'ta
            # petrol sondaji" (WTI'ye uygun). Hicbirinde sorgu kelimesi
            # gecmiyor ama hepsi dogru gorsel.
            #
            # Ilgi suzgeci INDIRME aninda dogru arac: orada onlarca aday
            # var, iyi bir gorseli elemek bedava. Silme aninda ayni olcut
            # elimizdekini yok ediyor. Bu yuzden burada yalnizca
            # RAPORLANIYOR.
            if _editoryal_uygun(aday):
                kalan.append(f)
                continue
            cikanlar.append((anahtar, kunye[:70]))
            if uygula:
                # BUTUN BOY SURUMLERI SILINIYOR.
                #
                # Ilk yazimda yalnizca buyuk dosya siliniyordu ve
                # `o/` ile `k/` surumleri diskte KALIYORDU. Olculdu:
                # gorevden ayrilan Fed baskaninin fotograflari
                # elendikten sonra `foto/o/fed-5.jpg`, `fed-6`,
                # `fed-7` ve kucuk esleri hala duruyordu -- hicbir
                # sayfa kullanmiyordu ama dosyalar yayimlanmis
                # halde, dogrudan adresle ulasilabilir durumdaydi.
                #
                # "Elendi" demek dosyanin gitmesi demek; yarim silme,
                # silinmis SANMAKTIR.
                ad = f["dosya"].rsplit("/", 1)[-1]
                for klasor in (FOTO_KLASORU, ORTA_KLASOR, KUCUK_KLASOR):
                    p = klasor / ad
                    if p.exists():
                        p.unlink()
        if uygula:
            kayit.veri[anahtar] = kalan
    if uygula:
        kayit.kaydet()
    return cikanlar


if __name__ == "__main__":
    import argparse

    a = argparse.ArgumentParser(description="Fotograf havuzu bakimi")
    a.add_argument("--suz", action="store_true",
                   help="guncel editoryal suzgeci indirilmis gorsellere uygula")
    a.add_argument("--uygula", action="store_true",
                   help="yalnizca raporlamakla kalma, sil")
    s = a.parse_args()
    if s.suz:
        cikan = suz(uygula=s.uygula)
        for k, ad in cikan:
            print(f"  {'silindi' if s.uygula else 'suzgece takildi'}: [{k}] {ad}")
        print(f"{len(cikan)} gorsel suzgeci gecemiyor"
              + ("" if s.uygula else "  (--uygula ile silinir)"))
    else:
        a.print_help()


#: KUCUK SURUM -- canli akistaki 40 satirin yanindaki kare gorsel.
#:
#: NEDEN AYRI DOSYA: havuzdaki gorseller haber sutunu genisliginde
#: (800px, ortalama 165 KB). Ana sayfadaki akista 40 satir var; ayni
#: dosyalari 40x40 piksele CSS ile kucultmek okura ~6 MB indirtir.
#: Kirk kucuk surum toplam ~250 KB.
KUCUK_KLASOR = FOTO_KLASORU / "k"
KUCUK_GENISLIK = 96

#: ORTA BOY -- liste sayfalarindaki KART gorseli.
#:
#: Olculdu: ana sayfa 1,88 MB iniyordu ve bunun 1,60 MB'i SEKIZ kart
#: gorseliydi. Kartlar 16:9 ve izgarada ~300 piksel genisliginde
#: gorunuyor; 800 piksellik dosya indirmek yedi kat fazla bayt demek.
#: Haber sayfasindaki BUYUK gorsel 800'de kaliyor -- orada sutun
#: genisligi gercekten 800.
ORTA_KLASOR = FOTO_KLASORU / "o"
ORTA_GENISLIK = 400

#: Commons `titles` parametresi anonim istekte 50 baslik aliyor.
KUCUK_PARTI = 50

#: Kucuk gorsel indirmeleri arasi bekleme (saniye).
KUCUK_ARASI = 0.7


def _commons_basligi(kaynak: str) -> str:
    """Commons dosya sayfasi adresinden `File:...` basligini cikarir."""
    import urllib.parse
    if "commons.wikimedia.org/wiki/" not in kaynak:
        return ""
    ad = kaynak.rsplit("/wiki/", 1)[-1]
    if not ad.startswith("File:"):
        return ""
    # ALT CIZGI BOSLUGA CEVRILIYOR. Adres "File:Oil_Drilling.jpg" yazar
    # ama API yanitinda baslik "File:Oil Drilling.jpg" diye BOSLUKLU
    # doner. Alt cizgiyle anahtarlayinca eslesme kaciyor: ilk denemede
    # 315 gorselden yalnizca 12'si -- tek kelimelik adlar -- indi.
    return urllib.parse.unquote(ad).replace("_", " ")


def boy_uret(klasor: pathlib.Path, genislik: int,
             kayit: Kayit | None = None,
             en_cok: int | None = None) -> int:
    """Havuzdaki Commons gorselleri icin 96 piksellik surum indirir.

    Commons'in olcekleme ucu kullaniliyor -- yerel bir goruntu
    kutuphanesine (Pillow) gerek yok. Baslıklar ELLI'ser gruplanip tek
    istekte soruluyor: 315 gorsel icin yedi istek.

    Openverse kaynakli eski gorsellerde olcekleme ucu YOK; onlarin kucuk
    surumu uretilmiyor ve akis satiri gorselsiz kaliyor. Eksik gorsel,
    yanlis olcekli gorselden iyidir.
    """
    kayit = kayit or Kayit()
    klasor.mkdir(parents=True, exist_ok=True)
    bekleyen: dict[str, str] = {}          # File basligi -> yerel dosya adi
    for liste in kayit.veri.values():
        for f in liste:
            ad = f["dosya"].rsplit("/", 1)[-1]
            if (klasor / ad).exists():
                continue
            baslik = _commons_basligi(f.get("kaynak", ""))
            if baslik:
                bekleyen[baslik] = ad
    if not bekleyen:
        return 0

    basliklar = list(bekleyen)
    if en_cok:
        basliklar = basliklar[:en_cok]
    inen = 0
    for i in range(0, len(basliklar), KUCUK_PARTI):
        parti = basliklar[i:i + KUCUK_PARTI]
        try:
            r = httpx.get(COMMONS_UC, params={
                "action": "query", "format": "json",
                "titles": "|".join(parti),
                "prop": "imageinfo", "iiprop": "url",
                "iiurlwidth": str(genislik),
            }, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
            r.raise_for_status()
            sayfalar = (r.json().get("query", {}).get("pages", {}) or {}).values()
        except (httpx.HTTPError, ValueError, KeyError) as e:
            OKUNAMAYAN.append((f"boy{genislik}", parti[0],
                               f"{type(e).__name__}"))
            continue
        for sayfa in sayfalar:
            bilgi = (sayfa.get("imageinfo") or [{}])[0]
            url = bilgi.get("thumburl")
            ad = bekleyen.get(sayfa.get("title", ""))
            if not url or not ad:
                continue
            try:
                g = httpx.get(url, headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                              follow_redirects=True)
                g.raise_for_status()
                if not g.headers.get("content-type", "").startswith("image/"):
                    continue
            except httpx.HTTPError:
                continue
            (klasor / ad).write_bytes(g.content)
            inen += 1
            # HER INDIRME ARASINDA BEKLEME.
            #
            # Aralik yokken 225 gorselin 197'si basarisiz oldu; ayni
            # adresler bir saniyelik araliklarla denendiginde 200
            # donuyor. Yani sorun gorselde degil, ard arda istekte.
            time.sleep(KUCUK_ARASI)
        time.sleep(ISTEK_ARASI)
    return inen



def kucuk_uret(kayit: Kayit | None = None, en_cok: int | None = None) -> int:
    """96 piksellik akis gorselleri."""
    return boy_uret(KUCUK_KLASOR, KUCUK_GENISLIK, kayit, en_cok)


def orta_uret(kayit: Kayit | None = None, en_cok: int | None = None) -> int:
    """400 piksellik KART gorselleri.

    Olculdu: ana sayfanin 1,88 MB'inin 1,60 MB'i sekiz kart gorseliydi
    ve hepsi 800 piksellik dosyaydi. Kart izgarada ~300 piksel
    gorunuyor; 800 piksel indirmek yedi kat fazla bayt.
    """
    return boy_uret(ORTA_KLASOR, ORTA_GENISLIK, kayit, en_cok)
