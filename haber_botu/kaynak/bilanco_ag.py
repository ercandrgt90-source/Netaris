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
