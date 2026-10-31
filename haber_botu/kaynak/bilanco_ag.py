"""BIST sirketlerinin mali tablolari -- ucretsiz, anahtarsiz, IZINLI.

    stockanalysis.com/quote/IST/{kod}/financials/?p=quarterly
        -> ceyreklik kalemler -> Turk ara donemi (3/6/9/12 aylik)

NEDEN BU KAYNAK
---------------
Bilanco rakamlari simdiye kadar ELLE giriliyordu cunku KAP otomatik
cekilemiyor: rakamlar istemci tarafinda, Next.js Server Actions ile
yukleniyor ve o cagri disaridan calismiyor (olculdu, uc ayri bildirim
GET ile cekildi; govdede yalnizca menu/kabuk vardi).

ELENEN YOL -- IZIN YOK, TEKNIK ENGEL DEGIL
------------------------------------------
Is Yatirim'in `/_layouts/.../MaliTablo` ucu ARANAN HER SEYI veriyordu:
anahtarsiz, temiz JSON, 147 kalem, TERA'nin brut kari ve donem kari
bizim KAP'tan elle girdigimiz rakamla BIREBIR ayni.

Kullanilmadi. `robots.txt` acikca soyluyor:

    User-agent: *
    Disallow: /_layouts/

Site sahibi otomatik erisime hayir demis. Calisiyor olmasi izin
verildigi anlamina gelmiyor; bu, WAF'tan bile net bir sinyal cunku
YAZILI. Ayni gerekceyle KAP'in WAF'i, Fintables'in Cloudflare
dogrulamasi ve Investing/TradingView kazima yollari da elenmisti.

SECILEN KAYNAGIN IZNI
---------------------
stockanalysis.com robots.txt yalnizca `/e/` ve `/p/` yollarini
kapatiyor; `/quote/...` acik. Sayfa sunucuda basiliyor, anahtar
istemiyor.

DONEM CEVIRISI -- BURASI KRITIK
-------------------------------
Kaynak CEYREKLIK veriyor (Q1, Q2...), KAP ise KUMULATIF ara donem
(3/6/9/12 aylik). Ikisi ayni sey DEGIL:

    KAP "6 aylik donem kari"  =  Q1 + Q2

Olculdu (TERA 2026/6):
    Q1 21.582 + Q2 24.647 = 46.229 mn TL
    bizim KAP'tan elle girdigimiz: 46.260 mn TL   -> %0,07 fark

Fark yuvarlamadan: kaynak milyon cinsinden bes anlamli basamak
gosteriyor. Esik `SAPMA_ORANI` ile denetleniyor.

BILANCO KALEMLERI TOPLANMAZ. Gelir tablosu kalemleri (hasilat, kar)
DONEM AKISI oldugu icin ceyrekler toplanir; bilanco kalemleri
(varliklar, ozkaynak) belirli bir ANIN stogudur ve toplanmaz --
donem sonundaki ceyregin degeri AYNEN alinir. Bu ayrimi karistirmak,
toplam varliklari dort katina cikarir.
"""

from __future__ import annotations

import html
import re
import time

import httpx

UC = "https://stockanalysis.com/quote/IST/{kod}/financials/{sayfa}"
# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {
    # Kim oldugumuz ve nasil ulasilacagi ACIK yaziyor. Kaynak
    # trafigimizden rahatsiz olursa bize ulasabilmeli.
    "User-Agent": ajan("bilanco arastirma"),
}
ZAMAN_ASIMI = 40.0

#: Istekler arasi bekleme. Kaynak bizim degil; hizli cekmek icin
#: sebep yok ve yavas cekmek icin sebep var.
#:
#: DEGISKEN: kaynak "yavasla" dediginde `_yavasla()` bunu buyutuyor ve
#: kaynak toparlayinca `_gecti()` geri indiriyor.
ARA_SN = 0.5

#: OLCULEN DONEMIN BILDIRIM PENCERESI -- gun.
#:
#: NEDEN UCUNCU BIR KAPI VAR
#: -------------------------
#: `BILDIRIM_AYLARI` TAHMIN, nobetci bayragi OLAY. Ikisi de "bu
#: donemde yapilacak IS KALDI MI" sorusunu cevaplamiyor:
#:
#:   - Takvim yalnizca Mart/Mayis/Agustos/Kasim'i aciyor. 9 aylik
#:     tablolar EKIM SONUNDA gelmeye basliyor; ekimin tamami kapali.
#:   - Bayrak "YENI ceyrek GORDUM" olayini tasiyor ve kosu sonunda
#:     INIYOR. Bir kez acilip bir kosu calisiyor, sonra kapaniyor.
#:
#: OLCULDU (2026-10-30/31, kosu #60-#61):
#:   #60  13:12  bayrak KALKTI -> veri adimi kostu, ozet 20 sirkette
#:               2026-09-30'u gordu, kosu sonunda bayrak INDI
#:   #61  01:23  "10. ay bildirim ayi degil ... ve nobetci yeni
#:               ceyrek gormedi" -> veri adimi ATLANDI
#:               sayfa adimi tam o 20 sirkete Q3 sayfasi yazdi
#:
#: Yani ozet 14:00'teki fotoğrafta DONDU. Sonraki kosular sifir yeni
#: Q3 sayfasi yazacakti: sayfa adimi ancak OZETTE `2026-09-30` yazan
#: sirkete Q3 sayfasi yaziyor ve ozeti tazeleyen adim kapali.
#:
#: UCUNCU KAPI OLCUME DAYANIYOR: nobetci kaynakta gordugu EN YENI
#: donem bitisini (`son_bitis`) zaten saklıyor -- ek istek yok.
#: O tarihten bu yana pencere kadar gun gectiyse hat ACIK.
#:
#: 60 GUN SECILDI. SPK ara donem sinirlari: konsolide olmayan 30
#: gun, konsolide 40 gun. 2026-09-30 icin 30 Ekim ve 9 Kasim. 60
#: gun ikisini de, geciken bildirimleri de kapsiyor ve 29 Kasim'da
#: KAPANIYOR -- bir sonraki donem 31 Aralik'ta bittigi icin
#: pencereler CAKISMIYOR. Kapanmayan kapi da bir kusurdur: her
#: kosuda 333 sirketi bosuna cekmek olurdu.
BILDIRIM_PENCERESI_GUN = 60


def pencere_acik(son_bitis, bugun) -> tuple[bool, int]:
    """(acik_mi, gecen_gun) -- olculen donemin bildirim penceresi.

    `son_bitis` nobetcinin kaynakta gordugu EN YENI donem bitisi
    (ISO). Yok ya da cozulemezse pencere KAPALI sayiliyor: "bilmiyorum"
    ile "acik" ayni sey degil.

    GELECEKTE BITEN DONEM ACMIYOR. Kaynak gelecek kolonlari da
    yaziyor; negatif gun sayisi pencereyi acsaydi hat yil boyu acik
    kalirdi.
    """
    import datetime as _dt                            # noqa: PLC0415
    if not isinstance(son_bitis, str):
        return False, 0
    try:
        bitis = _dt.date.fromisoformat(son_bitis)
    except ValueError:
        return False, 0
    gun = (bugun - bitis).days
    return 0 <= gun <= BILDIRIM_PENCERESI_GUN, gun


def _uyu(saniye: float) -> None:
    """Bekleme TEK YERDEN -- sinamalar bunu yamaliyor."""
    time.sleep(saniye)


def ara_ver() -> float:
    """Istekler arasi bekleme. BEKLENEN SUREYI doner (olculebilsin).

    KAYNAGA NAZIK DAVRANMA KURALI BURADA, `ARA_SN`IN YANINDA
    ---------------------------------------------------------
    OLCULDU (2026-10-31, kosu #61): sayfa adimi 20 sayfa yazdiktan
    sonra kaynak 429 vermeye basladi, gunluge `istek araligi 2.0 ->
    4.0 -> 8.0 sn` dustu ve "KAYNAK KAPANDI -- 8 ardisik red" geldi.
    Kalan 131 sirket "eksik: hasilat, net_kar, aktif_toplami" diye
    atlandi; bolum gocu de ayni kosuda 128 sayfanin HICBIRINI
    tasiyamadi. AYNI KOSUDA veri adimi 333 sirketi sonuna kadar
    cekti.

    Fark tek bir seydi: veri adimi istekler arasinda bekliyordu, o
    iki adim HIC BEKLEMIYORDU. `_yavasla()` `ARA_SN`i buyutuyordu ve
    bekleyen kimse olmadigi icin UYARLAMA ETKISIZDI -- gunluk
    tedbirin alindigini soyluyor, alinan tedbir yok. Olculen bir
    degerin kullanilmamasi, hic olculmemesinden daha sinsidir.

    KURAL BU DOSYADA DURUYOR, cagiranlarda degil. Beklemeyi her
    donguye elle yazmak, bir sonraki dongude yine unutulmasi
    demekti; `test_bilanco_penceresi` kaynaga giden HER dongunun bu
    cagriyi tasidigini mekanik olarak denetliyor.

    ARALIK HER CAGRIDA YENIDEN OKUNUYOR, basta bir kez degil: deger
    kosu sirasinda degisiyor ve bir kez yakalamak uyarlamayi yine
    etkisiz kilardi.

    KAYNAK KAPANDIYSA BEKLEMEK YOK. `cek` o durumda istek atmadan
    donuyor, yani beklenecek bir sey yok. Kalan ~130 sirket icin 8
    saniye beklemek 17 dakikayi hicbir seye harcamak olurdu.
    """
    if KAPANDI:
        return 0.0
    sure = ARA_SN
    _uyu(sure)
    return sure


#: Yavaslama olmadigindaki normal aralik. `ARA_SN` degisken oldugu
#: icin baslangic degeri AYRI bir sabitte duruyor -- iki yerde 0,5
#: yazmak, birini degistirip otekini unutmak demekti.
TABAN_ARA_SN = 0.5

#: Bir istek en fazla kac kez denenir.
#:
#: Olculdu (2026-09-14): kosu 11 sektorun yalnizca ILK UCUNU cekebildi,
#: kalan 8'i "donem belirlenemedi" ile elendi ve kapsam 327 sirketten
#: 47'ye dustu. Ayni sektorler TEK BASINA calistirilinca sorunsuz
#: cekildi (Sanayi 69 sirket, Saglik 9, 0 hata). Yani ariza sektore
#: degil SIRAYA bagliydi: kaynak belli sayida istekten sonra
#: reddediyor.
#:
#: Uc deneme: gecici bir reddi asmaya yeter, kalici bir engeli
#: asmaya calismaz. Kaynak gercekten kapatiyorsa israr etmek dogru
#: olmaz -- ne ise yarar ne de nazik olur.
DENEME = 3

#: Yeniden denemeden once beklenen taban sure (deneme sayisiyla
#: carpiliyor: 2, 4, 6 saniye).
GERI_CEKILME = 2.0

#: Bu durum kodlari "cok hizli gidiyorsun" demek.
YAVASLATAN = frozenset({429, 503})

#: Bir kez yavaslatildiktan sonra istekler arasi bekleme bu kadar
#: olur. Kosunun geri kalanini korur.
YAVAS_ARA_SN = 2.0


#: Bekleyerek asilmayacak tavan. Bunun otesi beklemek degil,
#: kapali bir kapiyi zorlamaktir.
TAVAN_ARA_SN = 8.0

#: Ustuste bu kadar istek reddedilirse kaynak bizi kapatmis demektir
#: ve kalan istekler HIC YAPILMAZ.
#:
#: Olculdu (2026-09-14): 56 ardisik HTTP 429. Yavaslama bir kez
#: ateslenip 2 sn'de KALIYORDU; 56 red, 2 sn'nin yetmedigini
#: kanitliyor. Ustelik her istek 3 kez deneniyordu -- yani kapali
#: kapiya yaklasik 168 istek gonderildi. Ne ise yarar ne de nazik.
ARDISIK_RED_SINIRI = 8

#: Bu kadar ARDISIK basarili istekten sonra aralik YARIYA iner.
#:
#: YAVASLAMA GERI DONMUYORDU -- olculdu 2026-09-15.
#:
#: 15:12'de calisan kosu, "Bilanco verisi" adiminda 81 DAKIKADIR
#: duruyordu; ayni adim onceki kosuda dakikalar surmustu. Asili
#: degildi, BEKLIYORDU: 326 sirket x 2 sayfa = 652 istek, her biri
#: tavandaki 8 saniyeyi odeyerek = 87 dakika SADECE uyku. Olcum:
#:
#:     ara 0,5 sn ->  5,4 dk      ara 4,0 sn -> 43,5 dk
#:     ara 2,0 sn -> 21,7 dk      ara 8,0 sn -> 86,9 dk
#:
#: Tek bir erken 429, kalan 650 istegin HEPSINE tavan fiyati
#: odetiyordu. Kaynak bes dakika sonra toparlamis olsa bile.
#:
#: "Kosunun geri kalanini korur" gerekcesi, DEVRE KESICI YOKKEN
#: yazilmisti: o zaman kalici yavaslama, israr etmemenin tek
#: yoluydu. `ARDISIK_RED_SINIRI` geldiginde gercek koruma oraya
#: gecti; kalici tavan ise yerinde kaldi ve artik hicbir seyi
#: korumuyor -- yalnizca odetiyor. Sebebi olen bir varsayim.
#:
#: ASIMETRIK, BILEREK: bir redde ikiye katlaniyor, inmek icin yirmi
#: temiz istek gerekiyor. Tavanda bu 160 saniyelik kesintisiz temiz
#: trafik demek. Hizli cekil, yavas yaklas.
IYILESME_ESIGI = 20

#: Kaynak kapandi mi. Kosu boyunca surer, sektorden sektore tasinir.
KAPANDI = False

_ardisik_red = 0
_ardisik_gecen = 0


def _yavasla() -> None:
    """Kaynak reddedince kosunun geri kalanini seyreltir.

    BASAMAKLI: once tek atislik bir sicramaydi (0,5 -> 2,0) ve orada
    KALIYORDU. Kaynak 2 saniyeyle de yetinmeyince yapacak bir sey
    kalmiyordu. Artik her redde ikiye katlaniyor, tavana kadar.
    """
    global ARA_SN, _ardisik_gecen
    # Iyilesme sayaci sifirlaniyor: "ardisik" gercekten ardisik olsun.
    # Arasinda red olan yirmi basari, kaynagin toparladigini gostermez.
    _ardisik_gecen = 0
    onceki = ARA_SN
    ARA_SN = min(max(ARA_SN * 2, YAVAS_ARA_SN), TAVAN_ARA_SN)
    if ARA_SN != onceki:
        print(f"    kaynak yavaslatti -- istek araligi {ARA_SN} sn")


def _reddedildi() -> None:
    """Bir istek, denemeleri bitince REDLE kapandi."""
    global _ardisik_red, KAPANDI
    _ardisik_red += 1
    if _ardisik_red >= ARDISIK_RED_SINIRI and not KAPANDI:
        KAPANDI = True
        print(f"    KAYNAK KAPANDI -- {_ardisik_red} ardisik red. "
              f"Kalan istekler YAPILMIYOR.")


def _gecti() -> None:
    """Bir istek basarili oldu: kapi hala acik.

    YAVASLAMAYI GERI ALIR. Yukselmek tek redde oluyor, inmek
    `IYILESME_ESIGI` kadar ardisik temiz istek istiyor -- neden orada
    yaziyor.
    """
    global _ardisik_red, _ardisik_gecen, ARA_SN
    _ardisik_red = 0
    if ARA_SN <= TABAN_ARA_SN:
        return                       # zaten normal hizda; sayacak sey yok
    _ardisik_gecen += 1
    if _ardisik_gecen < IYILESME_ESIGI:
        return
    _ardisik_gecen = 0
    ARA_SN = max(ARA_SN / 2, TABAN_ARA_SN)
    print(f"    kaynak toparladi -- istek araligi {ARA_SN} sn")


def sifirla() -> None:
    """Kosu durumunu basa alir (sinamalar ve art arda kosular icin)."""
    global ARA_SN, _ardisik_red, _ardisik_gecen, KAPANDI
    ARA_SN = TABAN_ARA_SN
    _ardisik_red = 0
    _ardisik_gecen = 0
    KAPANDI = False
    OKUNAMAYAN.clear()

#: Turetilen kumulatif deger ile kaynagin kendi rakami arasinda kabul
#: edilebilir sapma. Yuvarlamadan buyugu hesap hatasidir.
SAPMA_ORANI = 0.01

#: Ingilizce ay kisaltmasi -> ay numarasi. Kaynak "May 31, 2026"
#: biciminde yaziyor; donem bitis tarihini cozmek icin gerekli.
_AY_NO = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

#: KAC CEYREK TOPLANACAK -- TEK KAYNAK.
#:
#: OLCULDU (2026-10-13), GERCEK BIR KUSUR:
#: Bu sayi IKI YERDE ayri ayri belirleniyordu ve UYUSMUYORLARDI.
#:   * `uret_bilanco --ceyrek` varsayilani 1  -> oranlar ve sektor
#:     medyani TEK ceyrekten hesaplaniyordu,
#:   * `donem_getir`/`ara_donem` varsayilani 2 -> sayfadaki TL
#:     seviyeleri ALTI AYLIK geliyordu.
#: Ikisini de kimse acikca vermiyordu (ne `calistir.py` ne CI).
#:
#: Sonuc: ALCTL sayfasinda (2026-2-ceyrek-alctl.md) "2026 2. çeyrek
#: dönemi ölçümleri" basligi altinda hasilat 1,87 milyar yaziyor ama
#: hemen altindaki brut marj %4,4 -- seviye tablosundan hesaplanan
#: %7,5 degil. Cunku biri alti ayin toplami, oteki tek ceyregin.
#: Ayni sayfada IKI AYRI DONEM, tek etiketle.
#:
#: Ceyreklik dogru olan: `ceyrek_etiketi` gerekcesi orada yazili.
#: Artik tek yerde duruyor ve ikisi de buradan okuyor.
VARSAYILAN_CEYREK = 1

#: Sayfada gosterilen ardisik donem sayisi (su an dahil).
#:
#: DORT SECILDI: bir yillik dongu. Mevsimsel bir isletmede dort
#: ceyrek bir TAM tur demek, yani egilim mevsimsellikten ayirt
#: edilebiliyor. Uc ceyrek yarim tur gosterir ve mevsimsel inisi
#: egilim sanmaya davet eder.
#:
#: Kaynak 20 ceyrek donduruyor, yani sinir veri degil OKUNABILIRLIK:
#: telefon genisliginde yan yana dort sutun sigiyor.
GERIYE_DONEM = 4

#: Sayfa -> hangi tablo. Bilanco ve gelir tablosu AYRI sayfalarda.
SAYFALAR = {
    "gelir": "?p=quarterly",
    "bilanco": "balance-sheet/?p=quarterly",
    "nakit": "cash-flow-statement/?p=quarterly",
}

#: Gelir tablosu kalemleri DONEM AKISI -- ceyrekler toplanir.
#: Bilanco kalemleri STOK -- toplanmaz, son ceyrek aynen alinir.
AKIS_SAYFALARI = frozenset({"gelir", "nakit"})

#: Cekilemeyen sayfalar burada birikiyor; sessiz basarisizlik yok.
OKUNAMAYAN: list[tuple[str, str]] = []


def _sayi(ham: str) -> float | None:
    """Tablodaki metni sayiya cevirir. Kaynak MILYON cinsinden yaziyor.

    "-" bos hucre demek, "1,234.5" binlik virgullu. Yuzde iceren
    hucreler (buyume satirlari) REDDEDILIYOR -- onlar kalem degil.
    """
    m = (ham or "").strip()
    if not m or m in {"-", "--", "n/a"}:
        return None
    if "%" in m:
        return None
    m = m.replace(",", "")
    try:
        return float(m) * 1_000_000
    except ValueError:
        return None


def _tablo(metin: str) -> tuple[list[str], dict[str, list[float | None]],
                               list[str]]:
    """HTML tablosunu (donemler, kalem -> degerler, bitis tarihleri).

    Tarihler `donemler` ile AYNI sirada ve ISO biciminde. Kaynakta
    okunamayan bir hucre varsa o konumda bos dizge duruyor -- liste
    kaymasin, hizalama bozulmasin diye atlanmiyor.
    """
    g = html.unescape(
        re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", metin, flags=re.S))
    donemler: list[str] = []
    kalemler: dict[str, list[float | None]] = {}
    tarihler: list[str] = []

    for satir in re.findall(r"<tr[^>]*>(.*?)</tr>", g, re.S):
        hucre = [re.sub(r"<[^>]+>", "", h).strip()
                 for h in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", satir, re.S)]
        hucre = [h for h in hucre if h]
        if len(hucre) < 2:
            continue
        ad = hucre[0]
        if ad.startswith("Fiscal"):
            donemler = hucre[1:]
            continue
        if ad.startswith("Period Ending"):
            # DONEM BITIS TARIHLERI -- ETIKETTEN DAHA GUVENILIR.
            #
            # Kaynagin "Q3 2026" etiketi MALI ceyregi gosteriyor ve
            # takvim disi mali yili olan sirkette takvim ceyregine
            # denk DUSMUYOR. Olculdu (2026-10-13), spor kulupleri --
            # mali yillari 31 Mayis'ta bitiyor:
            #
            #   GSRAY  Q4 2026 etiketi  ->  gercek bitis 2026-05-31
            #   THYAO  Q2 2026 etiketi  ->  gercek bitis 2026-06-30
            #
            # Tarih tek basina kesin: hangi donem oldugu, hangi mali
            # takvime ait oldugu ve gercekten bitip bitmedigi
            # tarihten okunuyor. Etiket ise yoruma acik.
            #
            # Hucre hem mobil hem masaustu bicimini tasiyor
            # ("May '26 May 31, 2026"); uzun bicim ayiklaniyor.
            #
            # SATIR BIRDEN COK KEZ GECIYOR -- OLCULDU (2026-10-13).
            #
            # Ilk yazim her bulusta listeye EKLIYORDU. Gercek sayfada
            # "Period Ending" satiri her tablo bolumunde bir kez
            # tekrarlaniyor: GSRAY sayfasinda 20 donem icin 101 tarih
            # toplandi ve `mali_yil_sonu` uzunluk uyusmazligi yuzunden
            # None dondu. Yani sentetik ornegim gercegi yansitmiyordu.
            #
            # Artik EKLEMIYOR, ATIYOR -- `donemler` ile ayni davranis.
            # Ustelik yalnizca basliklarla AYNI SAYIDA hucre tasiyan
            # satir kabul ediliyor; hizalamasi bozuk bir satir sessizce
            # kabul edilmiyor.
            satir_tarih = []
            for h in hucre[1:]:
                m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", h)
                satir_tarih.append(
                    f"{m.group(3)}-{_AY_NO[m.group(1)]:02d}-"
                    f"{int(m.group(2)):02d}" if m else "")
            if donemler and len(satir_tarih) == len(donemler):
                tarihler = satir_tarih
            continue
        # KALEM ADI KENDI "Growth" IKIZINI TASIYOR.
        #
        # Kaynak "Revenue    Revenue Growth" yaziyor: kalem adi ve
        # hemen ardindan buyume satirinin etiketi. Ayri bir satir
        # olarak da yalnizca "Revenue Growth" geliyor.
        #
        # ONCE KIRPILIYOR, SONRA ELENIYOR. Ilk yazimda tersti --
        # "Growth ile biteni atla" kurali once calisiyordu ve GERCEK
        # kalemleri de atiyordu; gelir tablosu bombos donuyordu.
        # Bilanco kalemlerinde ikiz etiket olmadigi icin orasi
        # calisiyordu ve hata YARIM gorunuyordu.
        kisa = re.sub(r"\s{2,}\S.*?Growth$", "", ad).strip()
        if kisa.endswith("Growth"):
            continue          # gercekten yalnizca buyume satiri
        ad = kisa
        degerler = [_sayi(h) for h in hucre[1:]]
        if ad and any(d is not None for d in degerler):
            kalemler.setdefault(ad, degerler)
    return donemler, kalemler, tarihler


def cek(kod: str, sayfa: str = "gelir",
        istemci: httpx.Client | None = None,
        tarih_de: bool = False) -> tuple:
    """Bir sirketin bir tablosunu ceker. Basarisizsa BOS doner.

    Bos donmesi sorun degil: cagiran taraf elle girisi kullanmaya
    devam eder. Yarim veriyle bilanco yayimlamaktansa hic yayimlamamak
    dogru.
    """
    if sayfa not in SAYFALAR:
        raise ValueError(f"bilinmeyen sayfa: {sayfa}")
    # ESKI CAGIRANLAR IKILI BEKLIYOR.
    #
    # Donem bitis tarihleri sonradan eklendi. Donus bicimini
    # degistirmek, tarihe ihtiyaci olmayan her cagirani sessizce
    # bozardi; bu yuzden ucuncu deger yalnizca ISTENDIGINDE var.
    bos: tuple = ([], {}, []) if tarih_de else ([], {})
    u = UC.format(kod=kod.upper(), sayfa=SAYFALAR[sayfa])
    # KAPALI KAPIYA ISTEK ATILMIYOR.
    #
    # Kaynak ustuste reddetmeye basladiktan sonra kalan sektorlerin
    # istekleri yalnizca gecikme ve gereksiz yuk uretiyordu. Kayit
    # yine tutuluyor ki dokumde NEDEN eksik oldugu gorunsun.
    if KAPANDI:
        OKUNAMAYAN.append((f"{kod}/{sayfa}", "kaynak kapandi"))
        return bos
    al = (istemci or httpx).get
    son_hata = "?"
    son_yavaslatan = False
    for deneme in range(DENEME):
        try:
            r = al(u, headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                   follow_redirects=True)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            kodu = e.response.status_code
            son_hata = f"HTTP {kodu}"
            # 404 sayaci ISLETMIYOR: "o sayfa yok" demek, "cok hizli
            # gidiyorsun" demek degil. Ikisini karistirmak, eksik bir
            # sirket yuzunden saglam bir kosuyu durdururdu.
            son_yavaslatan = kodu in YAVASLATAN
            if kodu in YAVASLATAN and deneme < DENEME - 1:
                # KAYNAK "YAVASLA" DIYOR -- dinleniyor.
                #
                # Olculdu (2026-09-14): kosu 11 sektorun 3'unu cekip
                # kalan 8'ini kaybetti. Sektor sirasi alfabetikti ve
                # gecenler ILK UCTU -- yani ariza sektore degil SIRAYA
                # bagliydi. Tek basina calistirilinca ayni sektorler
                # sorunsuz cekildi (Sanayi 69 sirket, Saglik 9).
                #
                # Yani kaynak belli sayida istekten sonra reddediyor ve
                # bu kod reddi SESSIZCE bos veri sayiyordu: yeniden
                # deneme yok, bekleme yok, gunluge tek satir bile yok.
                _yavasla()
                time.sleep(GERI_CEKILME * (deneme + 1))
                continue
            break
        except (httpx.HTTPError, ValueError) as e:
            son_hata = type(e).__name__
            if deneme < DENEME - 1:
                time.sleep(GERI_CEKILME * (deneme + 1))
                continue
            break
        else:
            _gecti()
            donemler, kalemler, tarihler = _tablo(r.text)
            if tarih_de:
                return donemler, kalemler, tarihler
            return donemler, kalemler
    OKUNAMAYAN.append((f"{kod}/{sayfa}", son_hata))
    if son_yavaslatan:
        _reddedildi()
    return bos


def donem_toplami(degerler: list[float | None], ceyrek: int,
                  akis: bool, kaydir: int = 0) -> float | None:
    """Ceyreklik degerleri Turk ara donemine cevirir.

    `degerler` EN YENI ceyrek basta olacak sekilde siralı geliyor.
    `ceyrek` kac ceyregin toplanacagi: 6 aylik icin 2, 9 aylik icin 3.

    AKIS ise toplanir, STOK ise son deger AYNEN doner. Bilanco
    kalemlerini toplamak toplam varliklari kat kat sisirir.

    `kaydir` KAC CEYREK GERI gidilecegi. Onceki YILIN ayni donemi
    icin `kaydir=4` veriliyor -- dort ceyrek, tam bir yil.

    NEDEN BURADA, AYRI BIR CEKIMDE DEGIL. Ceyreklik seri zaten
    tamamiyla cekiliyor; onceki yil AYNI VERININ icinde. Ikinci bir
    ag istegi atmak, elde olani yeniden istemek olurdu -- 325 sirkette
    972 fazladan istek demek.

    YIL FARKI DORT CEYREK, UC AY DEGIL. Bir onceki DONEMLE (`kaydir=
    ceyrek`) karsilastirmak mevsimselligi degisim sanmaya yol acar:
    perakendede son ceyrek her yil yuksektir ve bu bir buyume degil,
    takvimdir.
    """
    if not degerler:
        return None
    if not akis:
        # STOK: tek bir andaki deger. Onceki yil, o donemin SON
        # ceyregindeki deger -- toplanmaz, secilir.
        i = kaydir
        return degerler[i] if i < len(degerler) else None
    bas = kaydir
    pencere = degerler[bas:bas + ceyrek]
    if len(pencere) < ceyrek or any(d is None for d in pencere):
        return None
    return sum(pencere)          # type: ignore[arg-type]


def ara_donem(kod: str, ceyrek: int = VARSAYILAN_CEYREK,
              istemci: httpx.Client | None = None,
              bugun=None) -> dict[str, dict]:
    """Sirketin KAP ara donemine denk gelen kalemlerini doner.

    Donen yapi:  {"gelir": {kalem: deger}, "bilanco": {...}, ...}
    Cekilemeyen tablo ATLANIR, digerleri doner -- kismi veri hicten
    iyidir, ama hangi tablonun eksik oldugu `OKUNAMAYAN`da yaziyor.

    `_mali` anahtari sirketin MALI TAKVIMINI tasiyor (gelir
    tablosundan, EK ISTEK OLMADAN). Takvimi bilmek sart: takvim disi
    mali yila sahip sirketin donemi takvim ceyregine denk dusmuyor ve
    takvim ceyregiyle kurulmus sektor medyaniyla kiyaslanamaz.
    """
    import datetime as _dt                          # noqa: PLC0415
    sinir = (bugun or _dt.date.today()).isoformat()
    cikti: dict[str, dict] = {}
    for sayfa in SAYFALAR:
        donemler, kalemler, tarihler = cek(kod, sayfa, istemci,
                                           tarih_de=True)
        # SIRKET BASINA UC ISTEK -- ARALARINDA DA BEKLENIYOR.
        #
        # Bu dongu gelir, bilanco ve nakit tablolarini ARKA ARKAYA
        # cekiyordu: cagiran taraf sirketler arasinda bekliyor olsa
        # bile kaynak UCLU PATLAMALAR goruyordu. Kaynagin bizi
        # kisitlamasinda payi olan sey tam bu sekil.
        #
        # Bekleme cekimin hemen ardinda ve KOSULSUZ: asagidaki
        # dallardan birine konulsa, yeni bir dal eklendiginde yine
        # atlanirdi.
        ara_ver()
        if sayfa == "gelir":
            cikti["_mali"] = {
                "yil_sonu_ayi": mali_yil_sonu(donemler, tarihler),
                "son_bitis": tarihler[0] if tarihler else None,
            }
        # BITMEMIS DONEM TOPLANMAZ.
        #
        # Kaynak gelecekte biten kolon yazabiliyor. `donem_toplami`
        # EN YENI ceyrekten baslayarak topluyor, yani boyle bir kolon
        # varsa ara donem bitmemis bir ceyregi iceriyor. En ustteki
        # kolonlar tarihleri gecmise dusene kadar KIRPILIYOR; kirpma
        # kalem degerlerine de uygulaniyor ki hizalama bozulmasin.
        at = 0
        if len(tarihler) == len(donemler):
            while at < len(tarihler) and tarihler[at] > sinir:
                at += 1
        if at:
            donemler = donemler[at:]
            tarihler = tarihler[at:]
            kalemler = {ad: d[at:] for ad, d in kalemler.items()}
            cikti.setdefault("_kirpilan", {})[sayfa] = at
        if not kalemler:
            continue
        akis = sayfa in AKIS_SAYFALARI
        cikti[sayfa] = {
            ad: d for ad, deg in kalemler.items()
            if (d := donem_toplami(deg, ceyrek, akis)) is not None
        }
        # ONCEKI YILIN AYNI DONEMI -- AYNI CEKIMDEN.
        #
        # Ek istek YOK: ceyreklik seri zaten tamamiyla elimizde.
        # Ayri bir cekim, 325 sirkette 972 fazladan istek olurdu.
        #
        # Bu olmadan sayfa yalnizca SEVIYE anlatabiliyor ("hasilat
        # 662 milyar"). Okurun sordugu soru ise degisim: artti mi,
        # ne kadar. Karsilastirma olmadan "artti" denemez.
        #
        # KAYDIRMA TARIHTEN BULUNUYOR, SAYILMIYOR -- gerekcesi
        # `onceki_yil_kaydirmasi` uzerinde yazili (seride boskuk olan
        # sirkette sabit 4, on bes ay oncesini gosteriyordu).
        kaydir = onceki_yil_kaydirmasi(tarihler, ceyrek)
        if kaydir is None:
            cikti.setdefault("_onceki_yok", {})[sayfa] = (
                "önceki yılın aynı dönemi kaynakta yok")
        else:
            cikti[sayfa + "_onceki"] = {
                ad: d for ad, deg in kalemler.items()
                if (d := donem_toplami(deg, ceyrek, akis,
                                       kaydir=kaydir)) is not None
            }
        cikti.setdefault("_donem", {})[sayfa] = donemler[:ceyrek]
        # SON DORT DONEM -- AYNI CEKIMDEN, EK ISTEK YOK.
        #
        # Sayfa tek donem + bir yil oncesini anlatiyordu. Okurun
        # sordugu soru ise EGILIM: "son ceyreklerde ne oldu".
        # Iki nokta egilim gostermez; donus mu, surekli mi, tek
        # seferlik mi ayirt edilemez.
        #
        # Seri zaten TAMAMIYLA elimizde (olculdu: kaynak 20 ceyrek
        # donduruyor) ve `donem_toplami` kaydirmayi destekliyor.
        # Ayri bir cekim 325 sirkette ~975 fazladan istek olurdu --
        # kaynak bizi zaten kisitliyor, bu kabul edilemez.
        #
        # ONCEKI YILDAN AYRI: o, mevsimselligi disarida birakmak
        # icin ayni donemi bir yil oncesiyle kiyasliyor ve kaydirmayi
        # TARIHTEN buluyor. Bu seri ise ARDISIK donemler; ikisi ayri
        # soru ve ikisi de sayfada duruyor.
        for _adim in range(1, GERIYE_DONEM):
            _k = _adim * ceyrek
            _g = {ad: d for ad, deg in kalemler.items()
                  if (d := donem_toplami(deg, ceyrek, akis,
                                         kaydir=_k)) is not None}
            if _g:
                cikti[f"{sayfa}_g{_adim}"] = _g
        if sayfa == "gelir" and len(tarihler) == len(donemler):
            # Bitis tarihleri GELIR tablosundan: donem adini kuran
            # tablo o. Eksikse seri yine uretiliyor, yalnizca
            # basliklari kaynagin etiketinden aliniyor.
            cikti["_seri_bitis"] = [
                tarihler[i * ceyrek] for i in range(GERIYE_DONEM)
                if i * ceyrek < len(tarihler)]
            cikti["_seri_etiket"] = [
                donemler[i * ceyrek] for i in range(GERIYE_DONEM)
                if i * ceyrek < len(donemler)]
        if not KAPANDI:
            time.sleep(ARA_SN)
    return cikti

# ---------------------------------------------------------------------
# KALEM ESLESTIRMESI
# ---------------------------------------------------------------------
#
# Kaynak Ingilizce etiket kullaniyor, hat (`analiz/oranlar.Donem`)
# Turkce alan adlari bekliyor. Arada bire bir karsilik OLMADIGI icin
# esleme tek tek yazildi ve muhasebe OZDESLIKLERIYLE dogrulandi
# (bkz. `ozdeslik_denetimi`) -- kaynaktan bagimsiz tek gercek sinama
# budur: bilanco tutuyorsa esleme dogrudur.
#
# (alan, sayfa, etiket)
ESLESME = (
    ("hasilat",                  "gelir",   "Revenue"),
    ("brut_kar",                 "gelir",   "Gross Profit"),
    ("faaliyet_kari",            "gelir",   "Operating Income"),
    ("net_kar",                  "gelir",   "Net Income"),
    ("aktif_toplami",            "bilanco", "Total Assets"),
    ("ozkaynak",                 "bilanco", "Shareholders' Equity"),
    ("donen_varliklar",          "bilanco", "Total Current Assets"),
    ("kisa_vadeli_yukumlulukler","bilanco", "Total Current Liabilities"),
    ("ticari_alacaklar",         "bilanco", "Accounts Receivable"),
    ("stoklar",                  "bilanco", "Inventory"),
    ("faaliyet_nakit_akisi",     "nakit",   "Operating Cash Flow"),
    ("finansman_gideri",         "nakit",   "Cash Interest Paid"),
)

#: NET BORC ISARETI TERS. Kaynak "Net Cash (Debt)" yaziyor: POZITIF
#: deger net NAKIT demek, negatif net BORC. Hattaki `net_borc` alani
#: ise borcu POZITIF bekliyor. Isareti cevirmeden aktarmak, borclu
#: sirketi nakit zengini gostermek olurdu -- yonu ters bir rakam,
#: eksik rakamdan kotudur.
NET_NAKIT_ETIKETI = "Net Cash (Debt)"

#: FAVOK KAYNAKTA YOK, TURETILIYOR:
#:     FAVOK = Faaliyet kari + Amortisman
#: Amortisman nakit akis tablosunda. Ikisinden biri eksikse FAVOK
#: URETILMIYOR -- yaklasik bir FAVOK, FAVOK degildir.
AMORTISMAN_ETIKETI = "Depreciation & Amortization"


def donemi_kur(tablolar: dict, onceki: bool = False,
               ek: str = "") -> dict:
    """Cekilen tablolari hattin bekledigi alan adlarina cevirir.

    `onceki=True` ise ONCEKI YILIN ayni donemi okunuyor. Ayni
    esleme tablosu kullaniliyor; tek fark hangi anahtardan okundugu.
    Iki ayri cevirici yazmak, birini duzeltip digerini unutmanin
    kestirme yolu olurdu.

    `ek` dogrudan bir anahtar soneki verir ("_g1", "_g2", ...) ve
    ardisik donem serisi bunun icin var. AYNI gerekce: ucuncu bir
    cevirici yazmak yerine sonek disaridan geliyor; isaret cevirme,
    net borc turetme ve amortisman kurallari TEK yerde kaliyor.
    """
    _ek = ek or ("_onceki" if onceki else "")
    cikti: dict[str, float] = {}
    for alan, sayfa, etiket in ESLESME:
        d = (tablolar.get(sayfa + _ek) or {}).get(etiket)
        if d is not None:
            cikti[alan] = d

    net_nakit = (tablolar.get("bilanco" + _ek) or {}).get(NET_NAKIT_ETIKETI)
    if net_nakit is not None:
        cikti["net_borc"] = -net_nakit

    # YATIRIM HARCAMASI -- ISARET CEVRILIYOR.
    #
    # Nakit akis tablosunda capex NEGATIF yaziliyor: nakit CIKISI.
    # Hattaki `yatirim_harcamasi` alani ise pozitif sayi bekliyor
    # ("pozitif sayi = nakit cikisi" -- `oranlar.Donem` boyle
    # belgeliyor). Olculdu: EREGL capex -1,93 mlr.
    #
    # Cevirmeden aktarmak yatirim yapan sirketi yatirim GELIRI olan
    # sirket gostermek olurdu; serbest nakit akisi hesabini da ters
    # yone cevirirdi.
    capex = (tablolar.get("nakit" + _ek) or {}).get("Capital Expenditures")
    if capex is not None:
        cikti["yatirim_harcamasi"] = abs(capex)

    amortisman = (tablolar.get("nakit") or {}).get(AMORTISMAN_ETIKETI)
    if amortisman is not None and cikti.get("faaliyet_kari") is not None:
        cikti["favok"] = cikti["faaliyet_kari"] + amortisman
    return cikti


def ozdeslik_denetimi(bilanco: dict, tolerans: float = 0.01) -> list[str]:
    """Bilanco kendi icinde tutuyor mu? Bozulan ozdeslikleri doner.

    ESLESMENIN DOGRULUGUNU KAYNAKTAN BAGIMSIZ SINAR. Bir etiketi
    yanlis alana baglarsak toplamlar tutmaz; tutuyorsa esleme
    dogrudur. Baska bir siteye "acaba ayni mi" diye sormaktan cok
    daha guclu, cunku ikinci site de yanilabilir.

    Tolerans ORANSAL: kaynak milyon cinsinden bes anlamli basamak
    gosteriyor ve yuvarlama farki kacinilmaz.
    """
    hatalar: list[str] = []

    def al(ad):
        return bilanco.get(ad)

    def karsilastir(ad, sol, sag):
        if sol is None or sag is None:
            return
        buyuk = max(abs(sol), abs(sag), 1.0)
        if abs(sol - sag) / buyuk > tolerans:
            hatalar.append(
                f"{ad}: {sol:,.0f} != {sag:,.0f} "
                f"(fark %{abs(sol - sag) / buyuk * 100:.2f})")

    varlik = al("Total Assets")
    karsilastir("Varliklar = Kaynaklar", varlik, al("Total Liabilities & Equity"))

    borc, ozkaynak = al("Total Liabilities"), al("Shareholders' Equity")
    if borc is not None and ozkaynak is not None:
        karsilastir("Varliklar = Borc + Ozkaynak", varlik, borc + ozkaynak)

    ana, azinlik = al("Total Common Equity"), al("Minority Interest")
    if ana is not None and azinlik is not None:
        karsilastir("Ozkaynak = Ana ortaklik + Azinlik", ozkaynak, ana + azinlik)

    donen, kvy = al("Total Current Assets"), al("Total Current Liabilities")
    if donen is not None and kvy is not None:
        karsilastir("Isletme sermayesi", al("Working Capital"), donen - kvy)
    return hatalar

# ---------------------------------------------------------------------
# SEKTORE GORE ZORUNLU ALANLAR
# ---------------------------------------------------------------------
#
# NEDEN VAR: eksik alanin iki ayri anlami var ve karistirmak yayin
# hatasi uretir --
#
#   "bu sektorde o kalem YOK"      -> normal, analiz yine yapilabilir
#   "veri gelmedi"                 -> analiz YAPILMAMALI
#
# Ayrimi yapmadan yorum uretmek, EKSIK TABLOYU TAM SANMAK demek.
#
# OLCULDU, VARSAYILMADI. On bir sektorde ornek sirketlerin alanlari
# tek tek sayildi ve eksikler SISTEMATIK cikti:
#
#   Sanayi, Temel malzeme, Temel tuketim, Bilisim, Saglik, Enerji
#       -> 12 alanin 12'si doluyor
#   Gayrimenkul (GYO)
#       -> brut kar, faaliyet kari, FAVOK, donen varlik, kisa vadeli
#          yukumluluk, stok HIC gelmiyor (0/2). GYO'lar bu sunumu
#          kullanmiyor; donen/duran ayrimi yapmiyorlar.
#   Kamu hizmetleri
#       -> brut kar, faaliyet kari, FAVOK gelmiyor
#   Finans
#       -> banka ile banka disi finans farkli; brut kar ve stok
#          bankada anlamsiz
#
# CEKIRDEK DORT ALAN her sektorde doluyor ve analiz icin asgari sart.
CEKIRDEK = ("hasilat", "net_kar", "aktif_toplami", "ozkaynak")

#: Sektorun EK olarak beklemesi gereken alanlar. Burada olmayan bir
#: alanin bos olmasi eksiklik DEGIL, o sektorun sunumu.
SEKTOR_EK = {
    "Sanayi": ("brut_kar", "faaliyet_kari", "stoklar", "donen_varliklar",
               "kisa_vadeli_yukumlulukler"),
    "Temel malzeme": ("brut_kar", "faaliyet_kari", "stoklar",
                      "donen_varliklar", "kisa_vadeli_yukumlulukler"),
    "Temel tüketim": ("brut_kar", "faaliyet_kari", "stoklar",
                      "donen_varliklar", "kisa_vadeli_yukumlulukler"),
    "İsteğe bağlı tüketim": ("brut_kar", "faaliyet_kari", "stoklar",
                             "donen_varliklar", "kisa_vadeli_yukumlulukler"),
    "Bilişim": ("brut_kar", "faaliyet_kari", "donen_varliklar",
                "kisa_vadeli_yukumlulukler"),
    "Sağlık": ("brut_kar", "faaliyet_kari", "donen_varliklar",
               "kisa_vadeli_yukumlulukler"),
    "Enerji": ("brut_kar", "faaliyet_kari", "donen_varliklar",
               "kisa_vadeli_yukumlulukler"),
    "İletişim": ("brut_kar", "faaliyet_kari", "donen_varliklar",
                 "kisa_vadeli_yukumlulukler"),
    # Asagidakiler EK ISTEMIYOR -- olculdu, bu kalemler gelmiyor ve
    # gelmemesi o sektorun sunumu.
    "Gayrimenkul": (),
    "Kamu hizmetleri": ("donen_varliklar", "kisa_vadeli_yukumlulukler"),
    "Finans": (),
}


def yeterli(donem: dict, sektor_tr: str = "") -> tuple[bool, list[str]]:
    """Bu veriyle analiz yapilabilir mi? (yapilabilir, eksik alanlar)

    Sektoru BILINMEYEN sirkette yalnizca cekirdek araniyor: bilmedigimiz
    bir sektore ek sart koymak, kesfedilmemis bir sunumu hata sanmak
    olurdu.
    """
    beklenen = list(CEKIRDEK) + list(SEKTOR_EK.get(sektor_tr, ()))
    eksik = [a for a in beklenen if donem.get(a) is None]
    return (not eksik), eksik

def donem_getir(kod: str, etiket: str,
                ceyrek: int = VARSAYILAN_CEYREK,
                sektor_tr: str = "", istemci=None, ciftli: bool = False,
                seri: bool = False):
    """Sirketin bir ara donemini `oranlar.Donem` olarak doner.

    Yetersiz veride `None` DONER, yarim nesne degil. Cagiran taraf
    "veri gelmedi" ile "bu sektorde o kalem yok" ayrimini yapmak
    zorunda kalmasin diye karar BURADA veriliyor -- esik zaten
    sektore gore olculmus durumda (bkz. `yeterli`).

    Donen ikili: (Donem, eksik_alanlar). Donem None ise eksik listesi
    NEDEN uretilmedigini soyluyor; sessiz basarisizlik yok.
    """
    import sys as _sys
    import pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent / "analiz"))
    import oranlar                                    # noqa: PLC0415

    tablolar = ara_donem(kod, ceyrek, istemci)
    alanlar = donemi_kur(tablolar)
    tamam, eksik = yeterli(alanlar, sektor_tr)
    if not tamam:
        # YETERSIZ VERIDE DE BICIM KORUNUYOR: cagiran `seri=True`
        # istediyse demetin uzunlugu her yolda ayni olmali, yoksa
        # "eksik" dalinda cozme hatasi verir -- veri eksikligi
        # cokmeye donusurdu.
        if seri:
            return (None, None, eksik, []) if ciftli else (None, eksik, [])
        return (None, None, eksik) if ciftli else (None, eksik)
    simdi = oranlar.Donem(etiket=etiket, **alanlar)

    # ONCEKI YIL -- VARSA. Yoksa sayfa yine uretiliyor, yalnizca
    # degisim bolumu olmuyor. Yeni halka acilan sirketin gecmisi
    # olmamasi bir kusur degil, bir gercek; sayfayi dusurmemeli.
    once = None
    try:
        o = donemi_kur(tablolar, onceki=True)
        if o.get("hasilat") or o.get("aktif_toplami"):
            once = oranlar.Donem(etiket="önceki yıl", **o)
    except (TypeError, ValueError):
        once = None
    # `Donem` DONDURULMUS bir veri sinifi -- uzerine alan yazilamaz
    # ve yazilmamali: olculmus bir donem, uretildikten sonra
    # degismemeli. Onceki yil bu yuzden AYRI donuyor.
    #
    # ARDISIK DONEM SERISI -- AYNI CEKIMDEN.
    #
    # `seri=True` istenmedikce HESAPLANMIYOR ve DONDURULMUYOR: donus
    # bicimini degistirmek, seriye ihtiyaci olmayan her cagirani
    # sessizce bozardi (ayni gerekce `tarih_de` ve `ciftli` icin de
    # yazili).
    #
    # Her ogesi (etiket, bitis_iso, Donem). Eksik kalan adim ATLANIR:
    # yeni halka acilan sirkette gecmis olmamasi kusur degil, gercek.
    if seri:
        dizi: list = []
        bitisler = tablolar.get("_seri_bitis") or []
        etiketler = tablolar.get("_seri_etiket") or []
        for adim in range(GERIYE_DONEM):
            alan = (alanlar if adim == 0
                    else donemi_kur(tablolar, ek=f"_g{adim}"))
            # OLCUT TAM OLARAK `hasilat` -- `Donem`IN ZORUNLU ALANI.
            #
            # Ilk yazim "hasilat YA DA aktif_toplami varsa" diyordu ve
            # URETIMDE COKTU (kosu #55, 2026-10-29):
            #
            #     TypeError: Donem.__init__() missing 1 required
            #                positional argument: 'hasilat'
            #
            # Gecmis bir ceyrekte bilanco tablosu gelip gelir tablosu
            # gelmeyebiliyor; o zaman kosul geciyor ama `Donem`
            # kurulamiyor. Sinamam iki alani da DOLU verdigi icin bu
            # yolu hic yurumemisti.
            #
            # Eksik olani sifirla doldurmak uydurma olurdu: "hasilat
            # yok" ile "hasilat sifir" ayri seyler. O donem seriden
            # DUSUYOR; seri ikiden kisa kalirsa bolum hic yazilmiyor.
            if alan.get("hasilat") is None:
                continue
            ad = (etiketler[adim] if adim < len(etiketler)
                  else f"-{adim} dönem")
            iso = bitisler[adim] if adim < len(bitisler) else ""
            # ETIKET OKURA GORE YAZILIYOR, KAYNAGIN DILIYLE DEGIL:
            # "Q1 2027" Ekim 2026'da okuru yanlis yere goturur.
            # Bitis tarihi varsa ondan turetiliyor.
            if iso:
                ad = donem_etiketi(iso, ceyrek)
            dizi.append((ad, iso, oranlar.Donem(etiket=ad, **alan)))
        if ciftli:
            return simdi, once, [], dizi
        return simdi, [], dizi
    # Cagiranlar bozulmasin diye ucuncu deger yalnizca `ciftli=True`
    # istendiginde veriliyor.
    if ciftli:
        return simdi, once, []
    return simdi, []

# ---------------------------------------------------------------------
# DONEM TESPITI -- TAKVIMDEN DEGIL VERIDEN
# ---------------------------------------------------------------------
#
# Hat once donemi ELLE aliyordu (`--donem 2026/6`). Kasim'da dokuz
# aylik tablolar geldiginde yine alti aylik cekilirdi ve kimse fark
# etmezdi: sayfa uretilirdi, rakamlar dogru olurdu, yalnizca ESKI
# donem olurdu.
#
# Takvimden tahmin etmek de yanlis olurdu -- sirketler ayni gun
# bildirmiyor; bazi sirket Kasim'in ilk gunu, bazisi son gunu
# aciklar. Bir sirket icin "su an hangi donemdeyiz" sorusunun tek
# dogru cevabi O SIRKETIN VERISINDE yaziyor.
#
# Kaynak donemi kendisi soyluyor: "Q2 2026". Buradan hem KAP
# kumulatif etiketi ("2026/6") hem toplanacak ceyrek sayisi (2)
# turuyor.
_CEYREK = re.compile(r"Q([1-4])\s+(\d{4})")


def donem_coz(etiket: str) -> tuple[int, int] | None:
    """"Q2 2026" -> (2026, 2). Cozulemezse None."""
    m = _CEYREK.search(etiket or "")
    if not m:
        return None
    return int(m.group(2)), int(m.group(1))


def kap_etiketi(yil: int, ceyrek: int) -> str:
    """(2026, 3) -> "2026/9" -- KAP KUMULATIF donem adi.

    DIKKAT: bu ad yilin ILK N AYINI anlatiyor, tek bir ceyregi degil.
    "2026/6" = Ocak-Haziran toplami (Q1+Q2). Sayfalarda artik
    `ceyrek_etiketi` kullaniliyor; bu islev KAP'la konusan yerlerde
    duruyor.
    """
    return f"{yil}/{ceyrek * 3}"


def ceyrek_etiketi(yil: int, ceyrek: int) -> str:
    """(2026, 2) -> "2026 2. çeyrek".

    NEDEN KUMULATIF DEGIL CEYREKLIK
    -------------------------------
    KAP donemleri kumulatif: "2026/6" alti ayin TOPLAMI. Okur icin bu
    iki sorun uretiyor:

      1. Ikinci ceyregin kendi performansi gorunmuyor -- iyi bir Q1
         zayif bir Q2'yi gizleyebiliyor.
      2. Yillik karsilastirma alti ayi alti ayla kiyasliyor; ceyreklik
         kiyas (Q2'ye karsi gecen yil Q2) daha keskin.

    Ceyreklik hesap `donem_toplami(..., ceyrek=1)` ile yapiliyor:
    akis kalemleri yalnizca EN SON ceyregi aliyor, stok kalemleri
    zaten belirli bir andaki deger.
    """
    return f"{yil} {ceyrek}. çeyrek"


#: Ceyreklerin bittigi ay. Bir ceyrek BITMEDEN tablosu yayimlanamaz.
_CEYREK_BITIS_AYI = {1: 3, 2: 6, 3: 9, 4: 12}


def makul_ceyrek(c, bugun=None) -> bool:
    """Bu ceyrek GERCEKTEN bitmis mi?

    NEDEN GEREKLI -- OLCULDU (2026-10-13)
    -------------------------------------
    Kaynak, takvim disi mali yili olan sirketlerde donemleri ILERI
    etiketliyor. ARENA'nin gelir tablosu basliklari:

        Q1 2027, Q4 2026, Q3 2026, Q2 2026, Q1 2026, ...

    Ekim 2026'dayken "Q1 2027" diye bir bilanco olamaz. `son_donem`
    ilk cozulebilen etiketi donduruyordu, yani ARENA icin (2027, 1).

    IKI YERDE ZARAR VERIYOR:
      * `uret_bilanco.sektor_donemi` sektorun etiketini ILK yanit
        veren sirketten aliyor. ARENA o sirket olursa butun sektor
        "2027 1. ceyrek" diye etiketlenir. Bugun sans eseri olmuyor
        -- ARENA Bilisim sektorunun 4. sirasinda ve ondan once ALCTL
        yanit veriyor. Ilk uc sirket cevap vermedigi gun olurdu.
      * Bilanco nobetcisi her kosuda "yeni donem acildi" derdi:
        defterdeki ceyrek ne olursa olsun 2027 ondan yeni.

    OLCUT TAKVIM: ceyregin BITIS ayi gecmiste olmali. Q3 2026
    30 Eylul'de bitiyor; 13 Ekim'de makul. Q4 2026 ve Q1 2027 degil.
    """
    if not c:
        return False
    import datetime as _dt                          # noqa: PLC0415
    bugun = bugun or _dt.date.today()
    yil, ceyrek = int(c[0]), int(c[1])
    ay = _CEYREK_BITIS_AYI.get(ceyrek)
    if not ay:
        return False
    # Ceyregin son gunu: o ayin bitisi. Gun tam dogrulugu gereksiz --
    # bir gun once/sonra karari degistirmiyor, ay yeterli.
    return (yil, ay) <= (bugun.year, bugun.month)


#: Mali yil bitis ayi -> Turkce ad. Gruplama adlarinda kullaniliyor.
_AY_ADI = {
    1: "ocak", 2: "şubat", 3: "mart", 4: "nisan", 5: "mayıs",
    6: "haziran", 7: "temmuz", 8: "ağustos", 9: "eylül",
    10: "ekim", 11: "kasım", 12: "aralık",
}


#: Mali takvimin guvenilir sayilmasi icin en yeniden baslayarak kac
#: kolonun ayni cevabi vermesi gerektigi. Tek kolon her zaman
#: kendisiyle uyusur; esigin anlami olmasi icin en az ucu gerekiyor.
_EN_AZ_UYUSAN = 3


def mali_yil_sonu(donemler: list[str],
                  tarihler: list[str]) -> int | None:
    """Sirketin mali yilinin bittigi AY; cozulemezse None.

    NEDEN ETIKET YETMIYOR -- OLCULDU (2026-10-13)
    ---------------------------------------------
    Kaynagin "Q3 2026" etiketi MALI ceyregi gosteriyor. Takvim disi
    mali yili olan sirkette bu takvim ceyregi DEGIL:

        GSRAY  Q3 2026  ->  gercek bitis 2026-02-28
        THYAO  Q3 2026  ->  gercek bitis 2026-09-30

    Etiketle tarihi birlikte okuyunca mali takvim cikiyor: n. ceyrek
    bittiginde yil sonuna (4-n) ceyrek, yani 3*(4-n) ay kalmistir.
    Ay sayisi 12'yi asabilecegi icin hesap sifir tabanli yapiliyor
    (once 1 cikar, bolumden sonra geri ekle):

        GSRAY  Q3, bitis ayi 2  ->  (2-1 + 3) % 12 + 1 =  5  mayis
        THYAO  Q3, bitis ayi 9  ->  (9-1 + 3) % 12 + 1 = 12  aralik

    SIRKET MALI YILINI DEGISTIREBILIYOR -- OLCULDU (2026-10-13).
    Ilk yazim BUTUN kolonlarin ayni cevabi vermesini sart kosuyordu
    ve bu, mali yilini degistirmis sirketi tumden eliyordu:

        ARENA  son 8 kolon mart sonu, oncesi 11 kolon aralik
        BALSU  son 6 kolon haziran sonu, oncesi 3 kolon aralik

    Gecmisteki takvim bizi ilgilendirmiyor; SON donem hangi takvime
    aitse o. Bu yuzden EN YENIDEN baslayan, birbiriyle uyusan dizi
    aliniyor ve o dizinin en az `_EN_AZ_UYUSAN` kolon olmasi
    isteniyor -- tek kolonla "uyusuyor" demek, denetimi tumden
    kaldirmak olurdu.
    """
    if not donemler or len(donemler) != len(tarihler):
        # UZUNLUK ESIT DEGILSE HIZALAMA GUVENILMEZ.
        #
        # Iki satir ayni hucre suzgecinden geciyor; bos bir hucre
        # birinde eksildiyse etiket-tarih eslesmesi KAYAR ve yanlis
        # mali takvim uretir. Sessiz kaymaya izin verilmiyor.
        return None
    dizi: list[int] = []
    for etiket, iso in zip(donemler, tarihler):
        c = donem_coz(etiket)
        if not c or not iso:
            continue
        try:
            ay = int(iso[5:7])
        except ValueError:
            continue
        if not 1 <= ay <= 12:
            continue
        dizi.append((ay - 1 + 3 * (4 - int(c[1]))) % 12 + 1)
    if not dizi:
        return None
    # EN YENI KOLON BASTA. Ondan baslayarak ayni cevabi veren kolonlar
    # sayiliyor; ilk farkli cevapta duruluyor (takvim degisimi).
    ay = dizi[0]
    uyusan = 0
    for a in dizi:
        if a != ay:
            break
        uyusan += 1
    if uyusan < min(_EN_AZ_UYUSAN, len(dizi)) or uyusan < 2:
        return None
    return ay


#: Onceki yilin ayni donemi icin kabul edilen sapma (ay).
#: Ceyrek bitisleri 28-31 gun arasi degistigi icin tam 12 ay
#: beklemek gereksiz katilik; 11-13 arasi ayni donem sayiliyor.
ONCEKI_YIL_SAPMASI = 1


def _ay_sayisi(iso: str) -> int:
    """ISO tarihi mutlak ay sayisina cevirir (karsilastirma icin)."""
    return int(iso[:4]) * 12 + int(iso[5:7])


def onceki_yil_kaydirmasi(tarihler: list[str],
                          ceyrek: int = 1) -> int | None:
    """Onceki yilin ayni donemi KACINCI kolonda; yoksa None.

    NEDEN SABIT 4 DEGIL -- OLCULDU (2026-10-13)
    -------------------------------------------
    Kod "dort kolon geri = bir yil once" varsayiyordu. Kaynagin
    ceyreklik serisinde BOSLUK olabiliyor ve o zaman varsayim
    sessizce yanlis donemi gosteriyor:

        TTKOM  4 kolon geri -> 12 ay once   dogru
        ARENA  4 kolon geri -> 12 ay once   dogru
        BALSU  4 kolon geri -> 15 AY once   YANLIS (2025-12-31 kolonu yok)
        GSRAY  4 kolon geri -> 15 AY once   YANLIS (2025-11-30 kolonu yok)

    Yani GSRAY sayfasinda "bir yil oncesine gore" basligi altinda
    on bes ay oncesiyle kiyas yayimlanirdi. Sayi dogru, ETIKET
    yanlis -- ve okur etikete inanir.

    Artik kolon TARIHTEN bulunuyor: bitisi 11-13 ay once olan kolon
    aranıyor. Yoksa None doner ve karsilastirma HIC yapilmaz;
    yanlis bir kiyas, eksik bir kiyastan kotudur.

    Kumulatif donemde (ceyrek > 1) ayrica pencerenin KESIKSIZ olmasi
    isteniyor: arada eksik kolon varsa toplam bir yili anlatmaz.
    """
    if not tarihler or not tarihler[0]:
        return None
    hedef = _ay_sayisi(tarihler[0]) - 12
    for i, iso in enumerate(tarihler):
        if not iso:
            continue
        if abs(_ay_sayisi(iso) - hedef) > ONCEKI_YIL_SAPMASI:
            continue
        pencere = tarihler[i:i + max(1, ceyrek)]
        if len(pencere) < max(1, ceyrek) or not all(pencere):
            return None
        # Pencere icindeki kolonlar ardisik ceyrekler olmali.
        for a, b in zip(pencere, pencere[1:]):
            if not 2 <= _ay_sayisi(a) - _ay_sayisi(b) <= 4:
                return None
        return i
    return None


def ay_adi(ay: int | None) -> str:
    """Ay numarasindan Turkce ay adi; cozulemezse bos dizge.

    Sayfa metni mali yilin bittigi ayi yaziyor ve bu ad TEK YERDE
    tutulmali: `_AY_ADI`ya modul disindan erismek, ozel bir adi
    sozlesme gibi kullanmak olurdu.
    """
    return _AY_ADI.get(ay or 0, "")


def donem_adi(bitis_iso: str, ceyrek_sayisi: int = 1) -> str:
    """Bitis tarihinden okunabilir donem adi: "2026 haziran–ağustos".

    "DONEMI" EKLENMIYOR -- OLCULDU (2026-10-14). Ilk yazim
    "...dönemi" ile bitiyordu ve sayfa basligi `f"## {donem} dönemi
    ölçümleri"` oldugu icin cikti "2026 mart–mayıs dönemi dönemi
    ölçümleri" diye basiliyordu. Etiket bir donem ADI olmali;
    "2026 2. çeyrek" de "dönemi" tasimiyor.

    NEDEN CEYREK NUMARASI DEGIL
    ---------------------------
    Takvim disi mali yila sahip sirkette kaynagin ceyrek numarasi
    MALI numara. Spor kuluplerinin haziran-agustos donemi kaynakta
    "Q1 2027" diye etiketli; bunu okura "2027 1. çeyrek" diye
    yazmak Ekim 2026'da duz yanlis okunur -- henuz yasanmamis bir
    donem gibi gorunur.

    Ay adlari hem dogru hem tek anlamli: hangi uc ay oldugunu
    soyluyor ve mali takvim bilgisi gerektirmiyor. Ayrica donem
    ANAHTARI olarak da tekil -- sayfa tekrar uretimi buna dayaniyor.
    """
    yil, ay = int(bitis_iso[:4]), int(bitis_iso[5:7])
    toplam = 3 * max(1, int(ceyrek_sayisi))
    # Aylar mutlak sayiya cevriliyor: yil atlamasi (aralik->subat)
    # boylece kendiliginden dogru cikiyor.
    bas = (yil * 12 + ay - 1) - (toplam - 1)
    bas_yil, bas_ay = divmod(bas, 12)
    bas_ay += 1
    if bas_yil == yil:
        return f"{yil} {_AY_ADI[bas_ay]}–{_AY_ADI[ay]}"
    return f"{bas_yil} {_AY_ADI[bas_ay]}–{yil} {_AY_ADI[ay]}"


#: Takvim ceyreklerinin son gunu (ay, gun).
_CEYREK_SON_GUN = {(3, 31): 1, (6, 30): 2, (9, 30): 3, (12, 31): 4}


def donem_etiketi(bitis_iso: str, ceyrek_sayisi: int = 1) -> str:
    """Bitis tarihine en UYGUN donem adi.

    TAKVIM CEYREGIYSE ALISILMIS ADI KULLANILIYOR. "2026 2. çeyrek"
    Turkce'de nisan-haziran demek ve okur bu ibareyi bekliyor; onu
    ay adlariyla degistirmek bir kazanc degil, gereksiz bir
    yabancilasma olurdu.

    TAKVIM CEYREGI DEGILSE ay adlari yaziliyor: kaynagin mali
    ceyrek numarasi okuru yanlis yere goturur ("Q1 2027").

    NEDEN ETIKET COGUNLUGA BAGLANAMAZ -- OLCULDU (2026-10-13)
    --------------------------------------------------------
    Ilk surum sektorun "ana donemi"ni en cok sirketin bildirdigi
    tarih sayiyor ve ana gruba SEKTORUN takvim etiketini veriyordu.
    İletişim sektoru bunu curuttu: yedi sirketin DORDU futbol
    kulubu, yani ana donem 2026-05-31 oldu ve FENER "2026 2. çeyrek"
    etiketini devraldi -- oysa donemi mart-mayis.

    Etiket artik yalnizca TARIHE bakiyor; hangi grubun cogunlukta
    oldugu etiketi etkilemiyor.
    """
    yil, ay = int(bitis_iso[:4]), int(bitis_iso[5:7])
    gun = int(bitis_iso[8:10])
    c = _CEYREK_SON_GUN.get((ay, gun))
    if c and int(ceyrek_sayisi) == 1:
        return ceyrek_etiketi(yil, c)
    return donem_adi(bitis_iso, ceyrek_sayisi)


def mali_takvim(kod: str, istemci=None, bugun=None) -> dict | None:
    """Sirketin mali takvimi ve EN YENI GERCEKLESMIS donemi.

    Doner: `yil_sonu_ayi`, `takvim_disi`, `son_bitis` (ISO),
    `son_etiket` (yil, ceyrek) -- veya cozulemezse None.

    `son_donem`den farki: etiketin takvim ceyregi olmasini SART
    kosmuyor. Takvim disi mali yila sahip sirket burada ELENMIYOR,
    kendi takvimiyle birlikte donuyor; kiyaslamasi ayni takvimdeki
    sirketlerle yapiliyor.
    """
    import datetime as _dt                          # noqa: PLC0415
    bugun = bugun or _dt.date.today()
    donemler, _, tarihler = cek(kod, "gelir", istemci, tarih_de=True)
    ay = mali_yil_sonu(donemler, tarihler)
    if ay is None:
        return None
    sinir = bugun.isoformat()
    # BITMEMIS DONEM AYIKLANIYOR -- TARIHTEN, ETIKETTEN DEGIL.
    #
    # Kaynak gelecekte biten kolonlari da yaziyor (ARENA "Q1 2027").
    # Eski olcut etiketin ayini tahmin ediyordu ve takvim disi
    # sirkette yanilmasi kacinilmazdi. ISO tarih dizgesel olarak
    # siralanabilir, bu yuzden kiyas tek satir.
    gecmis = [(e, t) for e, t in zip(donemler, tarihler)
              if t and t <= sinir and donem_coz(e)]
    if not gecmis:
        return None
    gecmis.sort(key=lambda p: p[1], reverse=True)
    etiket, bitis = gecmis[0]
    return {
        "yil_sonu_ayi": ay,
        "takvim_disi": ay != 12,
        "son_bitis": bitis,
        "son_etiket": donem_coz(etiket),
    }



def son_donem(kod: str, istemci=None, bugun=None) -> tuple[int, int] | None:
    """Sirketin kaynaktaki EN YENI GERCEKLESMIS ceyregi; yoksa None.

    Tek istek: gelir tablosunun donem basliklari yeterli. Bilanco ve
    nakit tablolari ayni ceyrekleri kullaniyor.

    HENUZ BITMEMIS CEYREKLER ATLANIYOR -- gerekcesi `makul_ceyrek`
    uzerinde yazili (takvim disi mali yil, ARENA ornegi).
    """
    donemler, _ = cek(kod, "gelir", istemci)
    cozulen = [donem_coz(d) for d in donemler]
    cozulen = [c for c in cozulen if c]
    if not cozulen:
        return None

    # TAKVIM DISI MALI YIL -- ETIKETLERI KARSILASTIRILAMAZ.
    #
    # Bazi sirketlerin mali yili takvim yiliyla ortusmuyor ve kaynak
    # donemleri ILERI etiketliyor. Olculdu (2026-10-13), Ekim ayinda:
    #
    #   ARENA : Q1 2027, Q4 2026, Q3 2026, Q2 2026, Q1 2026
    #   BALSU : Q4 2026, Q3 2026, Q1 2026, Q4 2025   (Q2 2026 YOK)
    #   THYAO : Q2 2026, Q1 2026, Q4 2025            (normal)
    #
    # ISARET: basliklarda GELECEKTE biten bir ceyrek var. Normal bir
    # sirkette bu imkansiz -- bitmemis ceyregin tablosu yayimlanmaz.
    #
    # Bu sirketlerin etiketi takvim ceyregine denk DUSMUYOR; "Q3 2026"
    # onlar icin baska bir donem. Dolayisiyla:
    #   * sektor donem etiketi onlardan alinamaz (butun sektoru yanlis
    #     etiketlerdi),
    #   * "yeni ceyrek belirdi mi" sorusunda sayilamazlar (her zaman
    #     one bakiyorlar).
    #
    # Olcemedigimizi tahmin etmiyoruz: None donuyor, cagiran bir
    # sonraki sirkete geciyor.
    if any(not makul_ceyrek(c, bugun) for c in cozulen):
        return None

    return cozulen[0]
