"""Makro veri baglayicilari -- ucretsiz ve ticari kullanima acik kaynaklar.

TASARIM ILKESI, BILANCO MOTORUYLA AYNI
--------------------------------------
Butun rakamlar ve degisimler burada hesaplanir; modele hazir verilir.
Model yalnizca yorumlar. Makro icerikte de tek uydurma rakam guveni bitirir.

KAYNAK SECIMI -- lisans onemli
------------------------------
* **FRED** (St. Louis Fed): 800 binden fazla seri, gunluk sinir yok,
  **ticari kullanim acikca serbest**, grafik CSV ucu icin anahtar bile
  gerekmiyor. ABD ve kuresel gostergeler icin ana kaynak.

* **TCMB EVDS**: Turkiye verisi icin resmi kaynak. Kayit ucretsiz, API
  anahtari gerekiyor. Turkiye pazari icin vazgecilmez -- TUFE, politika
  faizi, kur, rezervler.

* **Dunya Bankasi**: cok serbest sartlar, yeniden dagitima izin veriyor.
  Yavas olabiliyor; yedek kaynak.

Bilincli olarak KULLANILMAYANLAR: "ucretsiz katman" sunan haber API'leri
(NewsAPI vb.) genellikle ticari kullanimi yasaklar. isyatirimhisse'de
gordugumuz tuzagin aynisi -- kod serbest, veri kullanimi degil.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from datetime import date

import httpx

BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin; iletisim@netaris.com)"}
ZAMAN_ASIMI = 40.0


@dataclass(frozen=True)
class Gozlem:
    tarih: str
    deger: float


@dataclass
class Seri:
    kod: str
    ad: str
    birim: str
    kaynak: str
    gozlemler: list[Gozlem]

    @property
    def son(self) -> Gozlem | None:
        return self.gozlemler[-1] if self.gozlemler else None

    def onceki(self, geri: int = 1) -> Gozlem | None:
        i = len(self.gozlemler) - 1 - geri
        return self.gozlemler[i] if i >= 0 else None

    def degisim(self, geri: int = 1) -> float | None:
        """Puan cinsinden degisim. Oran serilerinde dogru olcu budur.

        Faiz %3,63'ten %4,00'a ciktiginda "yuzde 10 artti" demek yaniltir;
        dogru ifade "37 baz puan artti"dir.
        """
        s, o = self.son, self.onceki(geri)
        if s is None or o is None:
            return None
        return s.deger - o.deger

    def bicimle(self) -> str:
        if self.son is None:
            return f"{self.ad}: veri yok"
        satir = f"{self.ad}: {self.son.deger:,.2f} {self.birim} ({self.son.tarih})"
        d = self.degisim()
        if d is not None:
            satir += f"  onceki gozleme gore {d:+.2f} {self.birim}"
        return satir


# ---------------------------------------------------------------------------
# FRED -- anahtar gerektirmeyen CSV ucu
# ---------------------------------------------------------------------------

# Adlar sayfada aynen gorunuyor -- duzgun Turkce yazilmalari sart.
# Hepsi FRED'in anahtarsiz CSV ucundan geliyor ve ticari kullanima acik.
FRED_SERILER = {
    # Faiz
    "DFF": ("ABD politika faizi (efektif fed fonu)", "%"),
    "DGS2": ("ABD 2 yıllık tahvil getirisi", "%"),
    "DGS10": ("ABD 10 yıllık tahvil getirisi", "%"),
    "DGS30": ("ABD 30 yıllık tahvil getirisi", "%"),
    "T10Y2Y": ("10Y-2Y getiri farkı", "puan"),
    # Endeksler
    "SP500": ("S&P 500", "endeks"),
    "NASDAQCOM": ("Nasdaq Composite", "endeks"),
    "DJIA": ("Dow Jones Sanayi", "endeks"),
    # Risk ve kur
    "VIXCLS": ("VIX oynaklık endeksi", "endeks"),
    "DTWEXBGS": ("Dolar endeksi (geniş)", "endeks"),
    "DEXUSEU": ("EUR/USD", "USD"),
    "BAMLH0A0HYM2": ("Yüksek getirili tahvil primi", "puan"),
    # Emtia
    "DCOILBRENTEU": ("Brent petrol", "USD/varil"),
    "DCOILWTICO": ("WTI petrol", "USD/varil"),
    # Enflasyon
    "CPIAUCSL": ("ABD TÜFE (endeks)", "endeks"),
}

#: Ana sayfadaki piyasa ozeti panelinde gruplama.
#: BIST 100 BILINCLI OLARAK YOK: BIST endeks verisi lisansli, ucretsiz ve
#: ticari kullanima acik bir kaynagi bulunmuyor. Uydurmak yerine yok.
PANEL_GRUPLARI = (
    ("Endeksler", ("SP500", "NASDAQCOM", "DJIA")),
    ("Emtia", ("DCOILBRENTEU", "DCOILWTICO")),
    ("Faiz", ("DFF", "DGS2", "DGS10", "T10Y2Y")),
    ("Risk ve kur", ("VIXCLS", "DTWEXBGS", "DEXUSEU")),
)


def fred(kod: str, son_n: int = 60) -> Seri:
    """FRED'den seri ceker. API anahtari gerektirmez.

    fredgraph.csv ucu grafik icin tasarlanmis ama duz CSV donduruyor ve
    anahtar istemiyor. Resmi API'ye gore avantaji budur.
    """
    ad, birim = FRED_SERILER.get(kod, (kod, ""))
    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI) as c:
        y = c.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": kod})
        y.raise_for_status()

    gozlemler: list[Gozlem] = []
    okuyucu = io.StringIO(y.text)
    next(okuyucu, None)  # baslik satiri
    for satir in okuyucu:
        parcalar = satir.strip().split(",")
        if len(parcalar) < 2:
            continue
        tarih, ham = parcalar[0], parcalar[1]
        # FRED eksik gozlemi "." ile isaretler -- sifir degil, veri yok
        if ham in (".", ""):
            continue
        try:
            gozlemler.append(Gozlem(tarih, float(ham)))
        except ValueError:
            continue

    return Seri(kod, ad, birim, "FRED (St. Louis Fed)", gozlemler[-son_n:])


# ---------------------------------------------------------------------------
# TCMB EVDS -- Turkiye verisi, anahtar gerekiyor
# ---------------------------------------------------------------------------

EVDS_SERILER = {
    "TP.FG.J0": ("TÜFE (2003=100)", "endeks"),
    "TP.FE.OKTG01": ("Politika faizi", "%"),
    "TP.DK.USD.A.YTL": ("USD/TRY (alış)", "TL"),
    "TP.AB.A01": ("Brüt rezervler", "milyon USD"),
}


class EvdsAnahtariYok(RuntimeError):
    pass


def evds(kod: str, baslangic: str = "01-01-2024", bitis: str | None = None) -> Seri:
    """TCMB EVDS'den seri ceker.

    Anahtar: evds2.tcmb.gov.tr adresinden ucretsiz kayitla alinir, sonra
    EVDS_API_ANAHTARI ortam degiskenine yazilir.
    """
    anahtar = os.environ.get("EVDS_API_ANAHTARI")
    if not anahtar:
        raise EvdsAnahtariYok(
            "EVDS_API_ANAHTARI ayarlanmamis.\n"
            "  1. evds2.tcmb.gov.tr adresinden ucretsiz kayit olun\n"
            "  2. Profilim sayfasindan 'API Key Kopyala'\n"
            '  3. PowerShell:  $env:EVDS_API_ANAHTARI = "..."'
        )

    ad, birim = EVDS_SERILER.get(kod, (kod, ""))
    bitis = bitis or date.today().strftime("%d-%m-%Y")

    with httpx.Client(headers={**BASLIKLAR, "key": anahtar}, timeout=ZAMAN_ASIMI) as c:
        y = c.get(
            "https://evds2.tcmb.gov.tr/service/evds/",
            params={
                "series": kod,
                "startDate": baslangic,
                "endDate": bitis,
                "type": "json",
            },
        )
        y.raise_for_status()
        veri = y.json()

    alan = kod.replace(".", "_")
    gozlemler = []
    for satir in veri.get("items", []):
        ham = satir.get(alan)
        if ham in (None, "", "null"):
            continue
        try:
            gozlemler.append(Gozlem(satir.get("Tarih", ""), float(ham)))
        except (ValueError, TypeError):
            continue

    return Seri(kod, ad, birim, "TCMB EVDS", gozlemler)


# ---------------------------------------------------------------------------
# Gorunum
# ---------------------------------------------------------------------------

def kuresel_gorunum(kodlar: tuple[str, ...] = ("DFF", "DGS10", "DGS2", "DCOILBRENTEU")) -> str:
    """Modele verilecek makro anlik goruntu.

    Rakamlari kod hesaplar; modelin isi bunlarin BIST sirketlerinin
    bilancolarina ne yapacagini acikamak.
    """
    satirlar = ["KURESEL GOSTERGELER", "-" * 62]
    for kod in kodlar:
        try:
            s = fred(kod)
        except httpx.HTTPError as e:
            satirlar.append(f"{kod}: cekilemedi ({type(e).__name__})")
            continue
        satirlar.append("  " + s.bicimle())

        # 30 gozlem oncesine gore degisim -- yon tayini icin
        d30 = s.degisim(30)
        if d30 is not None:
            satirlar.append(f"      30 gozlem oncesine gore: {d30:+.2f} {s.birim}")
    return "\n".join(satirlar)


if __name__ == "__main__":
    print(kuresel_gorunum())
    print()
    try:
        print("  " + evds("TP.FG.J0").bicimle())
    except EvdsAnahtariYok as e:
        print(f"TURKIYE VERISI\n{'-' * 62}\n{e}")
