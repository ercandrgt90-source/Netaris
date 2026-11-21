"""TCMB gunluk kur bulteni -- ucretsiz, anahtarsiz, resmi.

    tcmb.gov.tr/kurlar/today.xml -> (bulten tarihi, doviz satis)

NEDEN GEREKLI -- "AYNI GUN" IDDIASI YANLISTI
---------------------------------------------
Serit USD/TRY ve EUR/TRY kalemlerini EVDS'nin `TP.DK.*.S.YTL`
serisinden aliyor ve `ecb_kur.py` basinda "EVDS hattindan AYNI GUN
geliyor" yaziyordu. OLCULDU (2026-11-21, Cumartesi) ve YANLISTI:

    depoda TP.DK.USD.S.YTL  tarih 2026-11-23  kayit ani 2026-11-20

Yani satir, iddia ettigi gunden UC GUN ONCE yazilmisti ve 2.973
yayimlanmis sayfada "23 Kasim 2026" diye gorundu -- OLMAMIS BIR GUN.

SEBEP: EVDS'nin tarihi GOZLEM GUNU DEGIL, kurun GECERLI OLDUGU gun.
Cuma aksami aciklanan bulten Pazartesi icin gecerli oluyor.

TCMB'nin kendi bulteniyle bes ardisik gun birebir dogrulandi:

    bulten 19.11.2026  USD satis 50,4694  ->  depoda 20.11
    bulten 20.11.2026  USD satis 50,4936  ->  depoda 23.11

Kayma +1 TAKVIM gunu degil +1 IS GUNU. Tatil sinirinda dogrulandi:

    depo 30.10 = 49,7892 = bulten 27.10   (28-29 Ekim'de bulten YOK)

Yani EVDS, yeni bulten olmayan gun icin ONCEKI degeri TEKRARLIYOR.
Bu da "gecerlilik tarihi" okumasini kesinlestiriyor.

NEDEN AYRI KOD -- EN ONEMLI TASARIM KARARI
-------------------------------------------
Bu modul `TP.DK.USD.S.YTL` koduna YAZMIYOR. Iki kaynak ayni
`(kod, tarih)` anahtarina FARKLI ANLAM yukluyor:

    EVDS      tarih = kurun GECERLI OLDUGU gun
    bu modul  tarih = bultenin ACIKLANDIGI gun

Ayni koda yazmak, `INSERT OR IGNORE` yuzunden hangi anlamin kazandigi
yazma SIRASINA baglı bir depo uretirdi -- ve ikisi sessizce karisirdi.
Ayni gerekce `ECB_EURUSD`in FRED'in `DEXUSEU`undan ayri tutulmasinda
da yazili.

HANGI ALAN
----------
`ForexSelling` (doviz satis) aliniyor, cunku EVDS karsiligi
`TP.DK.*.S.YTL` -- sondaki `S` satis demek. Bes gunun besinde deger
birebir ayni cikti; yani alan secimi tahmin degil, olcum.

BICIM UYARISI -- XML AYRISTIRICISI, REGEX DEGIL
------------------------------------------------
Ayni uyari `ecb_kur.py` icinde de var ve orada ACIYLA ogrenildi:
oznitelik tirnaklari dosyadan dosyaya degisiyor, regex sessizce SIFIR
kayit okuyor ve hicbir hata firlamiyor.

HAFTA SONU
----------
`today.xml` hafta sonu ve tatilde SON IS GUNUNUN bultenini sunmaya
devam ediyor (olculdu: 21 Kasim Cumartesi -> Tarih="20.11.2026").
Yani kaynak hafta sonu bos donmuyor; tarih de gelecege kaymiyor.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

UC = "https://www.tcmb.gov.tr/kurlar/today.xml"

# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan adres
# 20 dosyada suruklendi ve ucu bize ait olmayan bir alan adina
# isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan

BASLIKLAR = {"User-Agent": ajan("kur verisi")}
ZAMAN_ASIMI = 30.0

#: Depoya yazilan seriler. EVDS kodlarindan AYRI -- gerekcesi
#: dosyanin basinda, "NEDEN AYRI KOD" bolumunde.
KODLAR = {
    "USD": ("TCMB_USDTRY", "USD/TRY"),
    "EUR": ("TCMB_EURTRY", "EUR/TRY"),
}


def _tarih_coz(ham: str) -> str:
    """Bultenin `Tarih="20.11.2026"` oznitelini ISO'ya cevirir.

    NOKTAYLA ayrilmis gun.ay.yil. Ayni dosyada `Date="11/20/2026"`
    de var ve o AY/GUN/YIL -- yani iki oznitelik ayni sirayi
    KULLANMIYOR. Yanlisini okumak, 11 Kasim'i 20 Kasim sanmak gibi
    sessiz bir kaymayi uretirdi; bu yuzden `Tarih` aliniyor ve
    bicimi burada ACIKCA yaziliyor.
    """
    p = (ham or "").strip().split(".")
    if len(p) != 3:
        return ""
    try:
        return f"{int(p[2]):04d}-{int(p[1]):02d}-{int(p[0]):02d}"
    except ValueError:
        return ""


def coz(xml_metni: str) -> list[tuple[str, str, float]]:
    """XML'i (kod, tarih, satis kuru) listesine cevirir.

    Bulten TEK gun tasiyor; liste en fazla iki kalem doner.
    """
    kok = ET.fromstring(xml_metni)
    tarih = _tarih_coz(kok.get("Tarih", ""))
    if not tarih:
        return []
    cikti: list[tuple[str, str, float]] = []
    for para in kok.iter("Currency"):
        es = KODLAR.get(para.get("CurrencyCode") or para.get("Kod") or "")
        if not es:
            continue
        ham = (para.findtext("ForexSelling") or "").strip()
        birim = (para.findtext("Unit") or "1").strip()
        if not ham:
            continue
        try:
            deger = float(ham)
            kat = float(birim) or 1.0
        except ValueError:
            continue
        # `Unit` USD/EUR icin 1; JPY gibi paralarda 100 olabiliyor.
        # Bolmek, ileride baska para eklenirse sessiz 100 kat hatayi
        # engelliyor.
        cikti.append((es[0], tarih, deger / kat))
    return cikti


def cek(istemci=None) -> list[tuple[str, str, float]]:
    """TCMB'nin gunluk bultenini ceker."""
    al = (istemci or httpx).get
    r = al(UC, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    return coz(r.text)


def depoya_yaz(b, kayitlar: list[tuple[str, str, float]]) -> int:
    """Gosterge tablosuna yazar. `INSERT OR IGNORE` -- tekrar zararsiz."""
    if not kayitlar:
        return 0
    # TEK YAZMA YOLU -- gerekcesi `bundesbank.depoya_yaz` icinde yazili.
    # Ayrica `gosterge_yaz` gelecek tarihli gozlemi reddediyor; bu
    # seride boyle bir satir OLMAMALI, cunku bulten tarihi gecmistir.
    # Yine de koruma yerinde duruyor: kural kaynaga guvenmiyor.
    import beyin
    ad = {k: a for k, a in KODLAR.values()}
    return beyin.gosterge_yaz(b, [
        {"kod": kod, "tarih": tarih, "deger_ham": deger,
         "birim": "TL", "ad": ad.get(kod, kod), "kaynak": "TCMB"}
        for kod, tarih, deger in kayitlar
    ])


#: Gecmis doldurmanin penceresi (takvim gunu) ve kosu basina istek tavani.
#:
#: NEDEN SINIRLI: kaynak butcesi PAYLASIMLI. Bu depoda daha once bir
#: nobetci, bilinen bir soruya kosu basina 60 istek harcadi. Burada
#: tavan dusuk ve doldurma KENDILIGINDEN SONLANIYOR (asagiya bak).
GECMIS_PENCERE_GUN = 45
GECMIS_TAVAN = 20

#: Tarihli bulten adresi: /kurlar/202611/20112026.xml
GECMIS_UC = "https://www.tcmb.gov.tr/kurlar/{yilay}/{gunayyil}.xml"


def _is_gunu_mu(g) -> bool:
    """Cumartesi/Pazar degilse True. Resmi tatil BURADA BILINMIYOR --
    bilinmesi de gerekmiyor: tatilde bulten yok, istek 404 doner ve
    gun atlanir. Tatil takvimi tutmak, tutulmasi gereken ve eskiyen
    ikinci bir veri kaynagi yaratirdi."""
    return g.weekday() < 5


def gecmis_gerekli(b, kod: str = "TCMB_USDTRY") -> bool:
    """Gecmis doldurma HALA gerekli mi?

    KENDILIGINDEN SONLANIR: serinin EN ESKI satiri pencerenin disina
    ciktiginda doldurma biter ve bir daha hic istek yapilmaz. Boylece
    tatil gibi KALICI BOSLUKLAR her kosuda yeniden denenmez -- o,
    sonsuza kadar bosa istek harcamanin klasik bicimi olurdu.
    """
    import datetime as _d
    satir = b.execute("SELECT MIN(tarih) FROM gosterge WHERE kod=?",
                      (kod,)).fetchone()
    if not satir or not satir[0]:
        return True
    sinir = (_d.date.today()
             - _d.timedelta(days=GECMIS_PENCERE_GUN - 5)).isoformat()
    return satir[0] > sinir


def gecmis_cek(b, istemci=None, bugun=None) -> list[tuple[str, str, float]]:
    """Penceredeki EKSIK is gunlerinin bultenlerini ceker.

    Yalnizca depoda OLMAYAN gunler isteniyor; var olani yeniden
    cekmek hem bosa istek hem de gereksiz yuk olurdu.
    """
    import datetime as _d
    al = (istemci or httpx).get
    bugun = bugun or _d.date.today()
    var = {t for (t,) in b.execute(
        "SELECT tarih FROM gosterge WHERE kod='TCMB_USDTRY'")}
    cikti: list[tuple[str, str, float]] = []
    istek = 0
    for k in range(1, GECMIS_PENCERE_GUN + 1):
        if istek >= GECMIS_TAVAN:
            break
        g = bugun - _d.timedelta(days=k)
        if not _is_gunu_mu(g) or g.isoformat() in var:
            continue
        istek += 1
        try:
            r = al(GECMIS_UC.format(yilay=g.strftime("%Y%m"),
                                    gunayyil=g.strftime("%d%m%Y")),
                   headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
            if r.status_code != 200:
                continue                      # tatil ya da bulten yok
            cikti.extend(coz(r.text))
        except Exception:                                 # noqa: BLE001
            continue                          # tek gun butun adimi dusurmez
    return cikti
