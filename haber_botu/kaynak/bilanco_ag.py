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
BASLIKLAR = {
    # Kim oldugumuz ve nasil ulasilacagi ACIK yaziyor. Kaynak
    # trafigimizden rahatsiz olursa bize ulasabilmeli.
    "User-Agent": "Netaris/1.0 (finans arastirma; ercandrgt90@gmail.com)",
}
ZAMAN_ASIMI = 40.0

#: Istekler arasi bekleme. Kaynak bizim degil; hizli cekmek icin
#: sebep yok ve yavas cekmek icin sebep var.
ARA_SN = 0.5

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
    try:
        al = (istemci or httpx).get
        r = al(u, headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
               follow_redirects=True)
        r.raise_for_status()
    except (httpx.HTTPError, ValueError) as e:
        OKUNAMAYAN.append((f"{kod}/{sayfa}", type(e).__name__))
        return [], {}
    return _tablo(r.text)


def donem_toplami(degerler: list[float | None], ceyrek: int,
                  akis: bool) -> float | None:
    """Ceyreklik degerleri Turk ara donemine cevirir.

    `degerler` EN YENI ceyrek basta olacak sekilde siralı geliyor.
    `ceyrek` kac ceyregin toplanacagi: 6 aylik icin 2, 9 aylik icin 3.

    AKIS ise toplanir, STOK ise son deger AYNEN doner. Bilanco
    kalemlerini toplamak toplam varliklari kat kat sisirir.
    """
    if not degerler:
        return None
    if not akis:
        return degerler[0]
    pencere = degerler[:ceyrek]
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
        cikti.setdefault("_donem", {})[sayfa] = donemler[:ceyrek]
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


def donemi_kur(tablolar: dict) -> dict:
    """Cekilen tablolari hattin bekledigi alan adlarina cevirir."""
    cikti: dict[str, float] = {}
    for alan, sayfa, etiket in ESLESME:
        d = (tablolar.get(sayfa) or {}).get(etiket)
        if d is not None:
            cikti[alan] = d

    net_nakit = (tablolar.get("bilanco") or {}).get(NET_NAKIT_ETIKETI)
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
    capex = (tablolar.get("nakit") or {}).get("Capital Expenditures")
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
                sektor_tr: str = "", istemci=None):
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

    alanlar = donemi_kur(ara_donem(kod, ceyrek, istemci))
    tamam, eksik = yeterli(alanlar, sektor_tr)
    if not tamam:
        return None, eksik
    return oranlar.Donem(etiket=etiket, **alanlar), []
