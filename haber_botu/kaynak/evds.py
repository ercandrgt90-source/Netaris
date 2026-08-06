"""TCMB EVDS -- Turkiye makro verisi.

NEDEN GEREKLI
-------------
Sitede Turkiye'ye dair TEK BIR makro seri yoktu. Elimizde FRED (ABD) ve
Kraken (kripto) vardi; TUFE, politika faizi, resmi USD/TRY hicbiri yoktu.
Turk finans sitesi olarak bu, "arastirma dosyasi" hedefinin onundeki en
buyuk engeldi: bir faiz haberinin altina koyacak yerli rakamimiz yoktu.

ADRES BICIMI -- ALISILMIS DEGIL
-------------------------------
Parametreler sorgu dizesinde DEGIL, YOLUN ICINDE:

    /igmevdsms-dis/series=TP.DK.USD.S.YTL&startDate=01-01-2026&type=json

Yani `&` ile ayrilmis bir tek yol parcasi. httpx'in `params=` argumani
kullanilamaz -- kullanilirsa istek `/igmevdsms-dis/?series=...` olur ve
sunucu bunu tanimaz. Adres elle kuruluyor, sebebi bu.

ANAHTAR BASLIKTA
----------------
Sorgu parametresi olarak gonderilirse 403 doner. Ucretsiz; EVDS uyeligi
sonrasi profilden aliniyor ve ortam degiskeninde tutuluyor:

    setx EVDS_ANAHTARI "..."          # yerelde, kalici
    GitHub > Secrets > EVDS_ANAHTARI  # otomasyonda

Anahtar yoksa modul bos doner ve hat devam eder.

TASINMA NOTU
------------
Eski `evds2.tcmb.gov.tr/service/evds` ucu KAPANDI; o hosttaki her yol
evds3 anasayfasina yonleniyor. Eski ornekleri internette bulup
kullanmayin, sessizce bos doner.

FORMUL PARAMETRESI -- ENFLASYONDA KRITIK
----------------------------------------
TUFE serisinin kendisi ENDEKSTIR (2003=100). "Enflasyon %31,75" demek
icin yillik degisim gerekiyor ve EVDS bunu kendisi hesapliyor:

    formulas=0  duzey (endeksin kendisi)
    formulas=3  yillik yuzde degisim   <- enflasyon bu

Endeksi yuzde sanip yayimlamak, finans yayininda geri donusu olmayan
hatalardan biri; o yuzden her serinin formulu tabloda ACIKCA yaziyor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

TABAN = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
ZAMAN_ASIMI = 35.0

#: Bitis tarihi UZAK gelecek olmali ki sorgu hep guncel veriyi alsin --
#: kilavuzun kendi onerisi.
UZAK_BITIS = "01-01-2999"

#: Tek istekte en fazla 1000 gozlem. Asilirsa EVDS sondan 1000 tanesini
#: donduruyor; hata vermiyor, sessizce kirpiyor.
EN_COK_GOZLEM = 1000

#: formulas
DUZEY = "0"
YILLIK_YUZDE = "3"

#: frequency
GUNLUK = "1"
AYLIK = "5"


def anahtar() -> str:
    return os.environ.get("EVDS_ANAHTARI", "").strip()


@dataclass(frozen=True)
class Gozlem:
    tarih: str          # ISO
    deger: float


@dataclass(frozen=True)
class Seri:
    kod: str
    ad: str
    birim: str
    gozlemler: list[Gozlem]

    @property
    def son(self) -> Gozlem | None:
        return self.gozlemler[-1] if self.gozlemler else None

    def onceki(self, geri: int = 1) -> Gozlem | None:
        i = len(self.gozlemler) - 1 - geri
        return self.gozlemler[i] if i >= 0 else None


def _tarih_coz(ham: str) -> str:
    """EVDS tarih bicimleri FREKANSA GORE DEGISIYOR ve sirasi ayni degil:

        gunluk    "04-08-2026"   gun-ay-yil
        aylik     "2026-1"       YIL-AY      <- ters!
        ceyreklik "Q1-2026"
        yillik    "2026"

    Aylik bicimi gun-ay sanmak sessiz ve agir bir hata uretiyordu:
    "2026-1" -> "0012-2025-01" gibi bozuk tarihler cikiyor, siralama
    bozuluyor ve `son` gozlem YANLIS satiri gosteriyordu. Yani ekrana
    aralik verisi "en guncel" diye basilabilirdi.

    Aylik seride GUN BILGISI YOK; ayin ilkine sabitleniyor. Bugune
    sabitlemek, ocak verisini agustosta cikmis gibi gostermek olurdu.
    """
    ham = (ham or "").strip()
    if not ham:
        return ""
    p = ham.split("-")
    try:
        if len(p) == 3:                                   # 04-08-2026
            return f"{int(p[2]):04d}-{int(p[1]):02d}-{int(p[0]):02d}"
        if len(p) == 2 and p[0].upper().startswith("Q"):  # Q1-2026
            return f"{int(p[1]):04d}-{int(p[0][1:]) * 3:02d}-01"
        if len(p) == 2:                                   # 2026-1
            yil, ay = int(p[0]), int(p[1])
            # Dort haneli olan YILDIR. Bicim degisirse de dogru okunur.
            if yil < 100 <= ay:
                yil, ay = ay, yil
            if not 1 <= ay <= 12:
                return ""
            return f"{yil:04d}-{ay:02d}-01"
        if len(p) == 1:                                   # 2026
            return f"{int(p[0]):04d}-12-01"
    except (ValueError, IndexError):
        return ""
    return ""


def cek(kod: str, ad: str = "", birim: str = "", formul: str = DUZEY,
        frekans: str = "", gun: int = 1500,
        api_anahtari: str = "") -> Seri | None:
    """Tek seri ceker. Anahtar yoksa, cevap bos ya da hataliysa None.

    `formul` YILLIK_YUZDE verilirse EVDS degisimi kendi hesaplayip
    donduruyor -- bizim endeksten hesaplamamiza gerek kalmiyor.
    """
    a = api_anahtari or anahtar()
    if not a:
        return None

    bas = (date.today() - timedelta(days=gun)).strftime("%d-%m-%Y")
    # Parametreler YOLUN ICINDE -- httpx `params=` kullanilamaz.
    yol = (f"{TABAN}/series={kod}&startDate={bas}&endDate={UZAK_BITIS}"
           f"&type=json&formulas={formul}")
    if frekans:
        yol += f"&frequency={frekans}"

    try:
        y = httpx.get(
            yol,
            headers={"key": a, "User-Agent": "Netaris/0.1 (finansal yayin)"},
            timeout=ZAMAN_ASIMI,
            follow_redirects=True,
        )
        y.raise_for_status()
        veri = y.json()
    except (httpx.HTTPError, ValueError):
        return None

    satirlar = veri.get("items") or []
    if not satirlar:
        return None

    # Alan adi: seri kodundaki noktalar ALT CIZGIYE donuyor, ama formul
    # eki TIRE ile ekleniyor -- "TP_FG_J0-3". Karisik ama olculdu.
    taban_alan = kod.replace(".", "_")
    adaylar = [taban_alan]
    if formul != DUZEY:
        adaylar.insert(0, f"{taban_alan}-{formul}")
        adaylar.insert(1, f"{taban_alan}_{formul}")

    alan = ""
    for aday in adaylar:
        if any(aday in s for s in satirlar[:3]):
            alan = aday
            break
    if not alan:
        # Tarih disindaki ilk sayisal alani kullan -- EVDS alan adini
        # degistirmis olabilir, seriyi bu yuzden kaybetmeyelim.
        for s in satirlar:
            for k in s:
                if k.upper() not in ("TARIH", "UNIXTIME", "YEARWEEK"):
                    alan = k
                    break
            if alan:
                break
    if not alan:
        return None

    gozlemler: list[Gozlem] = []
    for s in satirlar:
        ham = s.get(alan)
        if ham in (None, "", "null"):
            continue
        try:
            deger = float(ham)
        except (TypeError, ValueError):
            continue
        t = _tarih_coz(s.get("Tarih", ""))
        if t:
            gozlemler.append(Gozlem(tarih=t, deger=deger))

    if not gozlemler:
        return None
    gozlemler.sort(key=lambda g: g.tarih)
    return Seri(kod=kod, ad=ad or kod, birim=birim, gozlemler=gozlemler)


#: (kod, gorunur ad, birim, formul, frekans)
#:
#: Her seri CANLI dogrulandi. Dogrulanmamis kod EKLEMEYIN.
#:
#: ARSIV SERISI TUZAGI -- bu bolumun en onemli notu.
#: EVDS durdurulmus seriyi silmiyor, "(Arsiv)" grubuna tasiyor ve eski
#: veriyi dondurmeye DEVAM EDIYOR. Hata yok, uyari yok. Olculdu:
#:
#:   TP.FG.J0  -> son gozlem Ocak 2026'da donmus (arsiv)
#:   dogrusu   -> TP.TUKFIY2025.GENEL, Temmuz 2026
#:
#: Eski kodu yayimlasaydik site aylarca yedi ay eski enflasyonu "guncel"
#: diye gosterecekti ve kimse fark etmeyecekti. Kod eklerken
#: `datagroups/mode=0` ciktisinda grubun adinda "(Arsiv)" olup olmadigina
#: ve END_DATE'e MUTLAKA bakin.
SERILER: tuple[tuple[str, str, str, str, str], ...] = (
    ("TP.TUKFIY2025.GENEL", "TÜFE (yıllık)", "%", YILLIK_YUZDE, AYLIK),
    ("TP.FE25.OKTG04", "Çekirdek enflasyon (C)", "%", YILLIK_YUZDE, AYLIK),
    ("TP.TUFE1YI.T1", "Yİ-ÜFE (yıllık)", "%", YILLIK_YUZDE, AYLIK),
    ("TP.APIFON4", "TCMB ağırlıklı fonlama", "%", DUZEY, GUNLUK),
    ("TP.DK.USD.S.YTL", "USD/TRY", "TL", DUZEY, GUNLUK),
    ("TP.DK.EUR.S.YTL", "EUR/TRY", "TL", DUZEY, GUNLUK),
    ("TP.YISGUCU2.G8", "İşsizlik oranı", "%", DUZEY, AYLIK),
    ("TP.HARICCARIACIK.K1", "Cari işlemler hesabı", "mn $", DUZEY, AYLIK),

    # --- BEKLENTILER ---
    #
    # Ucretsiz konsensus verisi bulunamadigi icin veri haberlerinde
    # "beklenti neydi" sorusu cevapsiz kaliyordu. TCMB'nin Sektorel
    # Enflasyon Beklentileri anketi bu bosluğu Turkiye tarafinda
    # kapatiyor: uc ayri kesimin 12 ay sonrasi icin beklentisi.
    #
    # DIKKAT: "Piyasa Katilimcilari Anketi" (bie_bekodtufe) ARSIVDE --
    # 2023'te durmus. Guncel grup `bie_enfbek`. Ayni tuzak daha once
    # TUFE serisinde yasandi ve yedi aylik eski veriyi guncel gibi
    # gostermisti; datagroup tarihi her yeni seride kontrol ediliyor.
    ("TP.ENFBEK.PKA12ENF", "Piyasa katılımcıları enflasyon beklentisi (12 ay)",
     "%", DUZEY, AYLIK),
    ("TP.ENFBEK.IYA12ENF", "Reel sektör enflasyon beklentisi (12 ay)",
     "%", DUZEY, AYLIK),
    ("TP.ENFBEK.HBA12ENF", "Hanehalkı enflasyon beklentisi (12 ay)",
     "%", DUZEY, AYLIK),
)


def hepsi(gun: int = 1400) -> dict[str, Seri]:
    """Tablodaki butun serileri ceker. Cekilemeyen ATLANIR.

    Tek seri cekilemedi diye butun makro bolumu bos kalmamali; cagiran
    taraf hangilerinin geldigini sozlukten gorur.
    """
    a = anahtar()
    if not a:
        return {}
    sonuc: dict[str, Seri] = {}
    for kod, ad, birim, formul, frekans in SERILER:
        s = cek(kod, ad, birim, formul, frekans, gun=gun, api_anahtari=a)
        if s:
            sonuc[kod] = s
    return sonuc
