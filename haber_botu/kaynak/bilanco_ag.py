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


def _tablo(metin: str) -> tuple[list[str], dict[str, list[float | None]]]:
    """HTML tablosunu (donemler, kalem -> degerler) haline getirir."""
    g = html.unescape(
        re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", metin, flags=re.S))
    donemler: list[str] = []
    kalemler: dict[str, list[float | None]] = {}

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
    return donemler, kalemler


def cek(kod: str, sayfa: str = "gelir",
        istemci: httpx.Client | None = None) -> tuple[list[str], dict]:
    """Bir sirketin bir tablosunu ceker. Basarisizsa BOS doner.

    Bos donmesi sorun degil: cagiran taraf elle girisi kullanmaya
    devam eder. Yarim veriyle bilanco yayimlamaktansa hic yayimlamamak
    dogru.
    """
    if sayfa not in SAYFALAR:
        raise ValueError(f"bilinmeyen sayfa: {sayfa}")
    u = UC.format(kod=kod.upper(), sayfa=SAYFALAR[sayfa])
    # KAPALI KAPIYA ISTEK ATILMIYOR.
    #
    # Kaynak ustuste reddetmeye basladiktan sonra kalan sektorlerin
    # istekleri yalnizca gecikme ve gereksiz yuk uretiyordu. Kayit
    # yine tutuluyor ki dokumde NEDEN eksik oldugu gorunsun.
    if KAPANDI:
        OKUNAMAYAN.append((f"{kod}/{sayfa}", "kaynak kapandi"))
        return [], {}
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
            return _tablo(r.text)
    OKUNAMAYAN.append((f"{kod}/{sayfa}", son_hata))
    if son_yavaslatan:
        _reddedildi()
    return [], {}


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


def ara_donem(kod: str, ceyrek: int = 2,
              istemci: httpx.Client | None = None) -> dict[str, dict]:
    """Sirketin KAP ara donemine denk gelen kalemlerini doner.

    Donen yapi:  {"gelir": {kalem: deger}, "bilanco": {...}, ...}
    Cekilemeyen tablo ATLANIR, digerleri doner -- kismi veri hicten
    iyidir, ama hangi tablonun eksik oldugu `OKUNAMAYAN`da yaziyor.
    """
    cikti: dict[str, dict] = {}
    for sayfa in SAYFALAR:
        donemler, kalemler = cek(kod, sayfa, istemci)
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
        cikti[sayfa + "_onceki"] = {
            ad: d for ad, deg in kalemler.items()
            if (d := donem_toplami(deg, ceyrek, akis, kaydir=4)) is not None
        }
        cikti.setdefault("_donem", {})[sayfa] = donemler[:ceyrek]
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


def donemi_kur(tablolar: dict, onceki: bool = False) -> dict:
    """Cekilen tablolari hattin bekledigi alan adlarina cevirir.

    `onceki=True` ise ONCEKI YILIN ayni donemi okunuyor. Ayni
    esleme tablosu kullaniliyor; tek fark hangi anahtardan okundugu.
    Iki ayri cevirici yazmak, birini duzeltip digerini unutmanin
    kestirme yolu olurdu.
    """
    _ek = "_onceki" if onceki else ""
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

def donem_getir(kod: str, etiket: str, ceyrek: int = 2,
                sektor_tr: str = "", istemci=None, ciftli: bool = False):
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


def son_donem(kod: str, istemci=None) -> tuple[int, int] | None:
    """Sirketin kaynaktaki EN YENI ceyregi. Bulunamazsa None.

    Tek istek: gelir tablosunun donem basliklari yeterli. Bilanco ve
    nakit tablolari ayni ceyrekleri kullaniyor.
    """
    donemler, _ = cek(kod, "gelir", istemci)
    for d in donemler:
        c = donem_coz(d)
        if c:
            return c
    return None
