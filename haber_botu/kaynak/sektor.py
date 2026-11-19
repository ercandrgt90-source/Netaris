"""BIST sirketlerinin sektor siniflandirmasi.

    stockanalysis.com/quote/IST/{kod}/  ->  Sector + Industry

NE OLDUGU -- VE NE OLMADIGI
---------------------------
Bu siniflandirma GICS duzenine yakin, ONBIR sektorluk uluslararasi
bir semadir (Financials, Materials, Industrials...). Borsa
Istanbul'un KENDI sektor endeksleri (XBANK, XUSIN, XMANA...) BUNDAN
FARKLIDIR ve bu dosya onlari temsil etmiyor.

Ayrimi yazmak onemli: okur "BIST sektoru" ile "uluslararasi sektor"
ayni sey saniyorsa, iki farkli kaynaktan gelen iki farkli listeyi
karsilastirdiginda tutmadigini gorur ve haksiz yere veriye guvenini
kaybeder. Sayfada hangisi oldugu YAZILMALI.

TURKCE ADLAR BIZIM. Kaynak Ingilizce veriyor; ceviri tablosu asagida
ve BIZE ait. Yani "BIST soyle diyor" degil, "biz boyle adlandirdik"
-- ikisi ayri iddia ve karistirilmamali.

IZIN
----
stockanalysis.com robots.txt yalnizca `/e/` ve `/p/` yollarini
kapatiyor; `/quote/...` acik. Ayni gerekceyle Is Yatirim'in
`/_layouts/` ucu ELENDI (bkz. `bilanco_ag`).
"""

from __future__ import annotations

import re
import time

import httpx

UC = "https://stockanalysis.com/quote/IST/{kod}/"
# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {
    "User-Agent": ajan("sektor verisi"),
}
ZAMAN_ASIMI = 30.0

#: Istekler arasi bekleme. 794 sirket icin ~5 dakika; acele edecek
#: bir sey yok ve kaynak bizim degil.
ARA_SN = 0.35

#: Sayfada sektor yapisal olarak gomulu:
#:     infoTable:[{t:"Industry",v:"Steel",...},{t:"Sector",v:"Materials",...}]
#: Gorunur metinden okumak yerine BURADAN aliniyor -- gorunur metinde
#: menu ogeleri de "Industry" diye geciyor ve ilk denemem menuyu
#: yakalamisti ("Stock Lists").
_INFO = re.compile(r"infoTable:\[(.*?)\]", re.S)
_CIFT = re.compile(r'\{t:"([^"]+)",v:"([^"]*)"')

#: Ingilizce sektor -> Turkce ad. BIZIM cevirimiz.
#:
#: KAYNAK IKI AYRI TAKSONOMI SERVIS EDIYOR -- OLCULDU (2026-11-19).
#:
#: Cogunlukla GICS adlari geliyor ("Consumer Staples", "Materials"),
#: ama bazi sirketlerde TRBC adlari ciktı: GMTAS icin sektor
#: "Consumer Non-Cyclicals", alt sektor "Food & Drug Retailing".
#: Ayni kavram, baska ad. Haritada olmadigi icin ham Ingilizce deger
#: akti ve dort gun dagitimi kilitledi (asagida `CEVIRI_YOK`).
#:
#: Bu yuzden TRBC karsiliklari da yaziliyor -- tahmin degil, ayni
#: kavramin ikinci adi:
#:
#:     TRBC                        GICS karsiligi
#:     Consumer Non-Cyclicals      Consumer Staples
#:     Consumer Cyclicals          Consumer Discretionary
#:     Basic Materials             Materials
#:     Telecommunications Services Communication Services
#:
#: EKLENMEYENLER de bilincli: TRBC'nin "Academic & Educational
#: Services" ve "Institutions, Associations & Organizations" ust
#: sektorlerinin bu defterde karsiligi YOK. Uydurmak yerine
#: `CEVIRI_YOK` ile isaretleniyorlar -- yanlis bir sektor, sektor
#: medyanini bozar ve sayfa gercek olmayan bir "sektore gore konum"
#: iddiasi tasir.
SEKTOR_TR = {
    "Financials": "Finans",
    "Materials": "Temel malzeme",
    "Basic Materials": "Temel malzeme",
    "Industrials": "Sanayi",
    "Energy": "Enerji",
    "Consumer Discretionary": "İsteğe bağlı tüketim",
    "Consumer Cyclicals": "İsteğe bağlı tüketim",
    "Consumer Staples": "Temel tüketim",
    "Consumer Non-Cyclicals": "Temel tüketim",
    "Communication Services": "İletişim",
    "Telecommunications Services": "İletişim",
    "Health Care": "Sağlık",
    "Healthcare": "Sağlık",
    "Information Technology": "Bilişim",
    "Technology": "Bilişim",
    "Utilities": "Kamu hizmetleri",
    "Real Estate": "Gayrimenkul",
}

#: SEKTOR GELDI AMA CEVIRISI YOK -- DORDUNCU DURUM.
#:
#: Ucu zaten vardi: kisitlama (429/503), yokluk (404/410) ve
#: `ALAN_YOK` (sayfa var, sektor satiri yok). Bu dorduncusu ve
#: digerlerinden farki, EKSIGIN BIZDE olmasi: kaynak dogru cevap
#: verdi, haritamizda karsiligi yok.
#:
#: NEDEN HAM DEGER DONMUYOR -- OLCULDU, DORT GUN KILITLEDI.
#:
#: Satir soyleydi:
#:
#:     "sektor_tr": SEKTOR_TR.get(sektor, sektor)
#:
#: Yani eslesmeyen her ad TURKCEYMIS GIBI akiyordu. Bedeli uc
#: yerden birden odendi (2026-11-15 -> 11-19):
#:
#:   1. OKUR. Sayfa Turk okura "sektor: Consumer Non-Cyclicals"
#:      yaziyordu.
#:   2. VERI. `sektor_ozet.json` on bir Turkce anahtarin yaninda bir
#:      Ingilizce anahtar tasiyordu; GMTAS kendi sektorunun
#:      medyanindan (35 sirket) ayri, TEK BASINA bir "sektor"
#:      olmustu -- yani medyan karsilastirmasi anlamsizdi.
#:   3. DAGITIM. `test_sektor_okuma` "uretilen her sektorun kilavuzu
#:      olmali" diyor ve hakliydi; o sinama URETIMDEN ONCE kosuyor,
#:      yani hat kendini onaramadi. Otomasyon 15 Kasim 20:43'ten
#:      19 Kasim'a kadar KIRMIZI dondu.
#:
#: Artik ham deger DONMUYOR: eksiklik sebebiyle birlikte
#: `OKUNAMAYAN`a yaziliyor ve sirket sektorsuz kaliyor. Sektorsuz
#: sayfa mesru (okuma kilavuzu bolumu hic yazilmiyor); yanlis
#: sektorlu sayfa degil.
CEVIRI_YOK = "sektor cevirisi yok"


def ceviri_yok_mu(sebep: str) -> bool:
    """`OKUNAMAYAN` sebebi "cevirisi yok" mu?

    OLCUT BURADA, CAGIRANDA DEGIL. Sebep dizgesi ADI da tasiyor
    ("sektor cevirisi yok: Consumer Non-Cyclicals") cunku hangi adi
    haritaya ekleyecegimizi yalnizca o soyluyor. Dolayisiyla
    cagiran taraf duz esitlikle karsilastiramaz; karsilastirmayi
    URETEN taraf yapiyor ki iki kopya sessizce ayrismasin.
    """
    return str(sebep or "").startswith(CEVIRI_YOK)

#: Cekilemeyen kodlar burada birikiyor -- sessiz basarisizlik yok.
OKUNAMAYAN: list[tuple[str, str]] = []

#: Kaynakta OLMAYAN sirket -- bu bir kisitlama degil, bir YOKLUK.
#:
#: `bilanco_ag` ayni ayrimi ters yonden yapiyor: orada "yavaslatan"
#: kodlar (429/503) listelenip 404 DISLANIYOR. Burada yoklugun
#: kendisi listeleniyor, cunku cagiran tarafin ayri tepki verdigi
#: durum bu: kisitlamada duruyor, yoklukta siradakine geciyor.
#:
#: Yalnizca BU liste tutuluyor. "Yavaslatan" kodlarin bir kopyasini
#: da yazmak, hicbir yerde kullanilmayan ve kural oldugunu iddia
#: eden olu bir sabit olurdu.
BULUNAMAYAN = frozenset({404, 410})


def _coz(metin: str) -> dict[str, str]:
    m = _INFO.search(metin)
    if not m:
        return {}
    return {t: v for t, v in _CIFT.findall(m.group(1))}


class Bulunamadi(Exception):
    """Sirket KAYNAKTA YOK (404/410) -- kisitlama DEGIL.

    Ayri bir tur, cunku cagiran taraf ikisine ayri tepki veriyor:
    kisitlamada durup bekliyor, yoklukta siradakine geciyor.
    """


#: SAYFA VAR AMA SEKTOR SATIRI YOK. Ucuncu bir durum ve ne
#: "kisitlama" ne "sayfasi yok" -- cagiran tarafin ayirmasi
#: gereken bir yokluk.
#:
#: OLCULDU (2026-11-12): BLUME icin kaynak HTTP 200 donuyor,
#: `infoTable` icinde `Industry: "Hotels and Motels"` var ama
#: **Sector satiri hic yok**. Yani yokluk gercek ve KALICI.
#:
#: Sebep dizgisi SABIT: cagiran taraf (`sektor_tazele`) bunu
#: metin karsilastirarak taniyor ve iki yerde ayri yazilmis bir
#: dizge sessizce ayrisirdi.
ALAN_YOK = "sektor alani yok"


def cek(kod: str, istemci: httpx.Client | None = None) -> dict[str, str]:
    """Bir sirketin sektor bilgisi. Bulunamazsa BOS sozluk.

    Bos donmesi sorun degil ve UYDURMA yapilmiyor: sektoru bilinmeyen
    sirket "Diger" kovasina atilmiyor, sektorsuz kaliyor. Yanlis
    sektore koymak, sektor ortalamasini da bozar.
    """
    try:
        al = (istemci or httpx).get
        r = al(UC.format(kod=kod.upper()), headers=BASLIKLAR,
               timeout=ZAMAN_ASIMI, follow_redirects=True)
        r.raise_for_status()
    except (httpx.HTTPError, ValueError) as e:
        # SEBEP DURUM KODUYLA KAYDEDILIYOR.
        #
        # Onceki hali yalnizca `type(e).__name__` yaziyordu ve her
        # HTTP hatasi "HTTPStatusError" goruluyordu. 403 ile 429
        # AYRI sorunlar: biri "bu yola girme", oteki "yavasla".
        # OLCULDU (2026-10-31, kosu #61): bu adim 5/5 hata verip
        # kapandi, gunlukte yalnizca "hata: 5" yaziyordu; ayni uc
        # YERELDE 4/4 calisiyordu. Hangi kod geldigini bilmeden
        # "CI'in IP'si mi engelli" sorusu cevaplanamiyor.
        _durum = getattr(getattr(e, "response", None), "status_code", None)
        OKUNAMAYAN.append((kod, f"HTTP {_durum}" if _durum
                           else type(e).__name__))
        # 404 KISITLAMA DEGIL -- cagiran taraf ikisini ayirabilsin.
        #
        # `bilanco_ag` bu ayrimi yillardir yapiyor ("404 sayaci
        # ISLETMIYOR: 'o sayfa yok' demek, 'cok hizli gidiyorsun'
        # demek degil"). Buraya HIC YAYILMAMISTI ve bedeli olculdu
        # (2026-10-31, kosu #62): adim "5 x HTTP 404" alip
        # "KAYNAK KAPANDI -- 5 ardisik red" diyerek kendini
        # kapatti. Kuyruk alfabetik ve her kosuda AYNI ilk 25
        # sirketi deniyor, yani 438 sirket KALICI olarak kilitliydi.
        if _durum in BULUNAMAYAN:
            raise Bulunamadi(f"HTTP {_durum}") from e
        return {}

    d = _coz(r.text)
    sektor = d.get("Sector", "").strip()
    if not sektor:
        OKUNAMAYAN.append((kod, ALAN_YOK))
        return {}
    tr = SEKTOR_TR.get(sektor)
    if not tr:
        # HAM INGILIZCE DEGER DONMUYOR -- gerekcesi `CEVIRI_YOK`
        # uzerinde yazili (okur, veri ve dagitim, uc ayri bedel).
        # ADI SEBEBE YAZIYORUZ: haritaya hangi satirin eklenecegini
        # yalnizca bu soyluyor.
        OKUNAMAYAN.append((kod, f"{CEVIRI_YOK}: {sektor}"))
        return {}
    return {
        "sektor": sektor,
        "sektor_tr": tr,
        "alt_sektor": d.get("Industry", "").strip(),
    }


def hepsi(kodlar, ilerleme=None) -> dict[str, dict]:
    """Cok sayida sirket icin sektor. Tek istemciyle, araliklı."""
    cikti: dict[str, dict] = {}
    with httpx.Client() as c:
        for i, kod in enumerate(kodlar, 1):
            d = cek(kod, c)
            if d:
                cikti[kod] = d
            if ilerleme and i % 25 == 0:
                ilerleme(i, len(kodlar), len(cikti))
            time.sleep(ARA_SN)
    return cikti
