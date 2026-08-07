"""Veri yayin takvimi -- hangi veri NE ZAMAN aciklanacak.

NEDEN VAR
---------
Sitedeki her sey geriye bakiyordu: ne aciklandi, ne anlama geldi. Oysa
bir karar platformunun asil isi ileriye bakmak -- "yarin 15:30'da ABD
TUFE var" bilgisi, aciklandiktan sonraki yorumdan daha degerlidir cunku
okur ona gore HAZIRLANABILIR.

KAYNAKLAR VE NEDEN BUNLAR
-------------------------
Investing.com'un takvim modulu ornek olarak verildi. Oradan KAZIMA
YAPILMADI: site bot erisimini engelliyor ve kullanim sartlari bunu
yasakliyor. Gerek de yok -- veriyi URETEN kurumlarin kendileri makine
okunur takvim yayimliyor:

  BLS   `bls.ics` -- standart iCalendar. ABD'nin en onemli veri
        aciklamalari (TUFE, UFE, Tarim Disi Istihdam, issizlik) tam
        TARIH VE SAATIYLE burada. Kurumun kendi yayimladigi dosya,
        kamuya acik, makine okunur.

  Fed   FOMC toplanti takvimi. Faiz kararlarinin gunleri.

Ikisi de BIRINCIL kaynak: aktarim degil, kararin sahibi.

TURKIYE ICIN DURUM FARKLI VE ACIKCA SOYLENIYOR
----------------------------------------------
TCMB'nin "Veri Yayimlama Takvimi" sayfasi tabloyu JavaScript ile
kuruyor; sayfanin HTML'inde takvim YOK, yalnizca sunum PDF'leri var.
TUIK'in bulten sayfasi da tek sayfalik bir uygulama.

Ikisinin de ic API'sini kurcalamak yerine yerli seriler serinin KENDI
YAYIN RITMINDEN turetiliyor (TUFE her ayin ilk is gunlerinde, PPK
duyurulan tarihlerde). Bu bir TAHMIN ve `kesin=False` ile
isaretleniyor; sayfada da "beklenen" diye gorunuyor. Tahmini kesin
saat gibi sunmak, olcmedigimizi olcmus gibi gostermek olurdu.

KONSENSUS (BEKLENTI) SORUNU
---------------------------
Olculdu: elimizdeki ucretsiz kaynaklarin hicbiri ONCEDEN konsensus
vermiyor. FinancialJuice beklentiyi yalnizca ACIKLAMA aninda basligin
icinde veriyor (101 baslikta ileriye donuk 1 tane, o da genel bir
"Week Ahead"). Konsensus rakamlari Reuters/Bloomberg anketleri, yani
lisansli.

Bu yuzden esik olarak SON ACIKLANAN DEGER kullaniliyor ve ekranda oyle
yaziyor ("önceki 45,8 bin"). Turkiye tarafinda istisna var: TCMB
Piyasa Katilimcilari Anketi gercek bir konsensus ve zaten depomuzda.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

BASLIKLAR = {
    # BLS bot erisimini engelliyor ama politikasi tanitici tanimlayan
    # istemcilere izin veriyor. Kimligimizi ve iletisimi yaziyoruz --
    # tarayici taklidi yapmak yerine kim oldugumuzu soylemek dogru olan.
    "User-Agent": "Netaris/1.0 (finans arastirma; ercandrgt90@gmail.com)",
}
ZAMAN_ASIMI = 25.0

BLS_ICS = "https://www.bls.gov/schedule/news_release/bls.ics"
FED_FOMC = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

def _bolge(ad: str, yedek_saat: int):
    """Saat dilimi. Veritabani yoksa SABIT ofsete duser ve UYARIR.

    Windows'ta sistem tz veritabani yok; `tzdata` paketi
    requirements.txt'te ama yerel bir kurulumda eksik olabiliyor.
    Sessizce sabit ofsete dusmek, yaz saatinde saatleri BIR SAAT yanlis
    gosterirdi ve bu tam olarak fark edilmeyen turden bir hata --
    "08:30 aciklanan veri" sayfada 14:30 yerine 15:30 yazardi. O yuzden
    dusus ekrana yaziliyor.
    """
    try:
        return ZoneInfo(ad)
    except Exception:
        print(f"  UYARI: saat dilimi veritabani yok ({ad}); "
              f"sabit UTC{yedek_saat:+d} kullaniliyor. "
              f"Yaz saatinde saatler bir saat kayabilir. "
              f"Cozum: pip install tzdata")
        return timezone(timedelta(hours=yedek_saat))


# Yedek ofsetler yaz saati degerleri: BLS takviminin yogun oldugu
# donem yaz aylari ve kis dususu daha az zarar veriyor.
_NY = _bolge("America/New_York", -4)
_TR = _bolge("Europe/Istanbul", 3)


@dataclass(frozen=True)
class Yayin:
    """Bir veri aciklamasinin planlanmis ani."""
    kod: str            # bizim seri kodumuz ("PAYEMS") ya da ""
    ad: str             # Turkce gorunur ad
    ad_kaynak: str      # kaynagin verdigi ozgun ad
    an: datetime        # UTC
    ulke: str           # "ABD" | "TR" | "AB"
    onem: int           # 1 dusuk, 2 orta, 3 yuksek
    kesin: bool         # kaynak tarih+saat verdi mi, yoksa TURETILDI mi

    @property
    def yerel(self) -> datetime:
        return self.an.astimezone(_TR)


#: BLS yayin adi -> (bizim seri kodumuz, Turkce ad, onem)
#:
#: Sira onemli: ilk eslesen kazanir, o yuzden en OZGUL olan ustte.
#: "Consumer Price Index" ile "Consumer Price Index Detailed Report"
#: ayni onemde degil ve ikincisi rutin bir ek yayindir.
BLS_ESLEME: tuple[tuple[str, str, str, int], ...] = (
    ("employment situation", "PAYEMS", "ABD Tarım Dışı İstihdam", 3),
    ("consumer price index", "CPIAUCSL", "ABD TÜFE", 3),
    ("producer price index", "PPIACO", "ABD ÜFE", 2),
    ("real earnings", "CES0500000003", "ABD reel kazançlar", 1),
    ("employment cost index", "", "ABD istihdam maliyeti endeksi", 2),
    ("job openings", "", "ABD açık iş sayısı (JOLTS)", 2),
    ("import and export price", "", "ABD ithalat-ihracat fiyatları", 1),
    ("productivity and costs", "", "ABD verimlilik ve maliyetler", 1),
    ("state employment", "", "ABD eyalet istihdamı", 1),
    ("county employment", "", "ABD ilçe istihdamı", 1),
    ("union members", "", "ABD sendika üyeliği", 1),
    ("consumer expenditures", "", "ABD tüketici harcamaları", 1),
)
BLS_VARSAYILAN_ONEM = 1


def _bls_esle(ad: str) -> tuple[str, str, int]:
    d = ad.lower()
    for kalip, kod, tr, onem in BLS_ESLEME:
        if kalip in d:
            return kod, tr, onem
    return "", ad, BLS_VARSAYILAN_ONEM


def _ics_an(ham: str) -> datetime | None:
    """iCalendar DTSTART -> UTC datetime.

    BLS `TZID=US-Eastern` yaziyor ve saat YEREL. Ham degeri UTC saymak,
    yaz saatinde dort saat kaymaya yol acardi -- 08:30'da aciklanan TUFE
    sayfada 11:30 yerine 08:30 gorunurdu.
    """
    v = ham.strip()
    try:
        if v.endswith("Z"):
            return datetime.strptime(v[:15], "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc)
        if "T" in v:
            y = datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
            return y.replace(tzinfo=_NY).astimezone(timezone.utc)
        # Saatsiz kayit: gun basi sayiliyor ama `kesin` yine de True --
        # tarih kaynaktan geliyor, yalnizca saat yok.
        return datetime.strptime(v[:8], "%Y%m%d").replace(
            tzinfo=_NY).astimezone(timezone.utc)
    except ValueError:
        return None


def bls_cek(c: httpx.Client) -> list[Yayin]:
    """BLS'in kendi yayimladigi iCalendar dosyasi."""
    try:
        y = c.get(BLS_ICS)
        y.raise_for_status()
    except httpx.HTTPError:
        return []

    cikti: list[Yayin] = []
    for blok in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", y.text, re.S):
        d = re.search(r"DTSTART[^:]*:([0-9TZ]+)", blok)
        s = re.search(r"SUMMARY:(.*)", blok)
        if not d or not s:
            continue
        an = _ics_an(d.group(1))
        if an is None:
            continue
        ad = s.group(1).strip()
        kod, tr, onem = _bls_esle(ad)
        cikti.append(Yayin(kod=kod, ad=tr, ad_kaynak=ad, an=an,
                           ulke="ABD", onem=onem, kesin=True))
    return cikti


#: FOMC sayfasindaki ay adlari. Sayfa Ingilizce.
_AYLAR = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def fed_cek(c: httpx.Client) -> list[Yayin]:
    """FOMC toplanti takvimi.

    Faiz karari toplantinin IKINCI gununde, 14:00 New York saatiyle
    aciklaniyor. Sayfa gun ARALIGI veriyor ("27-28"); karar gunu
    aralikta ikinci gun.
    """
    try:
        y = c.get(FED_FOMC)
        y.raise_for_status()
    except httpx.HTTPError:
        return []

    cikti: list[Yayin] = []
    # Yil basliklari sayfada bolum bolum; her bolumun icindeki ay-gun
    # ciftleri o yila ait.
    # Yil basligi bir <a> icinde: <h4><a id="42828">2026 FOMC Meetings</a></h4>
    # Ilk yazimda <h4> ile yil arasinda dogrudan metin varsayilmisti ve
    # desen HICBIR SEY eslemedi -- hata vermedigi icin takvim yalnizca
    # BLS ile doldu ve eksiklik ancak ciktiya bakinca goruldu.
    for yil_blok in re.finditer(
            r'<h4[^>]*>.*?(\d{4})\s+FOMC Meetings?.*?</h4>(.*?)(?=<h4|\Z)',
            y.text, re.S | re.I):
        yil = int(yil_blok.group(1))
        govde = yil_blok.group(2)

        # AY VE GUN BELGE SIRASINA GORE ESLESTIRILIYOR.
        #
        # Once ay listesi ve gun listesi ayri ayri toplanip `zip`
        # ediliyordu. Olculdu: 2026 blogunda 4 ay ama 8 gun kaydi cikti
        # -- cunku sayfa HER SATIRDA IKI TOPLANTI gosteriyor ve
        # ikincisinin ay etiketi ayni sinifi tasimiyor. `zip` fazlayi
        # sessizce atiyordu, yani toplantilarin YARISI kayboluyordu.
        #
        # Cozum: her iki kalibi TEK taramada, gorunme sirasiyla okumak.
        # Bir ay adini, kendisinden sonraki ilk gun kaydi izliyor.
        parcalar = re.finditer(
            r'<strong>\s*(January|February|March|April|May|June|July|'
            r'August|September|October|November|December)\s*</strong>'
            r'|class="fomc-meeting__date[^"]*"[^>]*>([^<]+)<',
            govde, re.I)
        ciftler: list[tuple[str, str]] = []
        bekleyen: str | None = None
        for p in parcalar:
            if p.group(1):
                bekleyen = p.group(1)
            elif bekleyen:
                ciftler.append((bekleyen, p.group(2)))
                bekleyen = None

        for ad_ay, gun in ciftler:
            ay = _AYLAR.get(ad_ay.strip().lower())
            if not ay:
                continue
            # "22 (notation vote)" gibi kayitlar TOPLANTI DEGIL, yazili
            # oylama. Faiz karari saati yok; takvime konmuyor.
            if "notation" in gun.lower():
                continue
            # "27-28*" -> 28 ; "8-9" -> 9 ; tek gun olabilir
            sayilar = re.findall(r"\d+", gun)
            if not sayilar:
                continue
            try:
                an = datetime(yil, ay, int(sayilar[-1]), 14, 0,
                              tzinfo=_NY).astimezone(timezone.utc)
            except ValueError:
                continue
            cikti.append(Yayin(kod="FED_FAIZ", ad="Fed faiz kararı (FOMC)",
                               ad_kaynak=f"FOMC Meeting {ad_ay} {gun}",
                               an=an, ulke="ABD", onem=3, kesin=True))
    return cikti


#: Yerli serilerin yayin ritmi: (seri kodu, gorunur ad, ayin kacinci
#: GUNU, saat, onem).
#:
#: BU TABLO BIR TAHMINDIR ve oyle isaretleniyor (`kesin=False`).
#: TCMB ve TUIK makine okunur takvim yayimlamiyor (bkz. modul basi).
#: Gunler serilerin gecmis yayin tarihlerinden okunmus tipik degerler;
#: resmi tatil ve hafta sonu kaydirmalari BURADA HESAPLANMIYOR, yalnizca
#: hafta sonundan bir sonraki is gunune oteleniyor.
YERLI_RITIM: tuple[tuple[str, str, int, int, int], ...] = (
    ("TP.TUKFIY2025.GENEL", "TÜFE (TÜİK)", 3, 10, 3),
    ("TP.TUFE1YI.T1", "Yİ-ÜFE (TÜİK)", 3, 10, 2),
    ("TP.FE25.OKTG04", "Çekirdek enflasyon (C)", 3, 10, 2),
    ("TP.YISGUCU2.G8", "İşsizlik oranı (TÜİK)", 10, 10, 2),
    ("TP.HARICCARIACIK.K1", "Cari işlemler dengesi", 11, 10, 2),
    ("TP.ENFBEK.PKA12ENF", "TCMB Piyasa Katılımcıları Anketi", 18, 14, 2),
)


def yerli_uret(bugun: datetime, ay_sayisi: int = 2) -> list[Yayin]:
    """Yerli serilerin BEKLENEN yayin anlari.

    Kaynak takvim olmadigi icin turetiliyor; `kesin=False` ve sayfada
    "beklenen" diye gorunuyor.
    """
    cikti: list[Yayin] = []
    for i in range(ay_sayisi + 1):
        ay = bugun.month + i
        yil = bugun.year + (ay - 1) // 12
        ay = (ay - 1) % 12 + 1
        for kod, ad, gun, saat, onem in YERLI_RITIM:
            try:
                an = datetime(yil, ay, gun, saat, 0, tzinfo=_TR)
            except ValueError:
                continue
            # Hafta sonuna denk gelirse bir sonraki is gunune.
            while an.weekday() >= 5:
                an += timedelta(days=1)
            cikti.append(Yayin(kod=kod, ad=ad, ad_kaynak=ad,
                               an=an.astimezone(timezone.utc),
                               ulke="TR", onem=onem, kesin=False))
    return cikti


#: Okunamayan kaynaklar. `cek()` her cagrida temizler.
#: Sessiz hata, takvimi bos birakip hicbir iz birakmazdi.
OKUNAMAYAN: list[tuple[str, str]] = []


def cek(gun: int = 21) -> list[Yayin]:
    """Onumuzdeki `gun` gun icindeki yayinlar, zamana gore sirali."""
    OKUNAMAYAN.clear()
    simdi = datetime.now(timezone.utc)
    son = simdi + timedelta(days=gun)

    hepsi: list[Yayin] = []
    with httpx.Client(timeout=ZAMAN_ASIMI, follow_redirects=True,
                      headers=BASLIKLAR) as c:
        for ad, islev in (("BLS", bls_cek), ("FED", fed_cek)):
            try:
                p = islev(c)
            except Exception as e:                     # ag/ayristirma
                OKUNAMAYAN.append((ad, f"{type(e).__name__}: {e}"[:120]))
                continue
            if not p:
                OKUNAMAYAN.append((ad, "kayit donmedi"))
            hepsi.extend(p)

    hepsi.extend(yerli_uret(simdi.astimezone(_TR)))

    # GECMIS ELENIYOR: "bugun ne var" bolumune dun aciklanmis bir veri
    # koymak, bolumun tek isini -- ileriye bakmayi -- bozar.
    yakin = [y for y in hepsi if simdi <= y.an <= son]
    yakin.sort(key=lambda y: y.an)
    return yakin
