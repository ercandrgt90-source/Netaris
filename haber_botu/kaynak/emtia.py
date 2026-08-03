"""Kiymetli maden ve gun ici fiyat -- anahtarsiz.

NEDEN BU MODUL VAR
------------------
Olay motorunun cekirdek sorusu su: "haber ciktiginda fiyat ne yapti?"
FRED bunu cevaplayamiyor -- gunluk ve BIR IS GUNU GECIKMELI. Pazartesi
14:00'te cikan bir haberin fiyat tepkisini sali sabahi yazmak, haber
sitesinde gec kalmaktir.

OLCULDU (2026-08-03)
--------------------
CANLI, ANAHTARSIZ:
  Gold-API      XAU altin, XAG gumus, XPT platin -- saniye damgali
  Kraken        BTC, ETH, PAXG + 15 dakikalik mum (OHLC interval=15)
  Coinbase      spot fiyat, yedek kaynak

BULUNAMADI:
  Petrol (Brent/WTI) icin anahtarsiz gun ici kaynak YOK. Kraken'in 1428
  ciftinde petrol gecmiyor; EIA, Twelve Data, FMP ve Commodities-API
  anahtar istiyor. Petrol FRED'den geliyor ve bir is gunu gecikmeli --
  bu yuzden petrol iceren yorumda gozlem tarihi ACIKCA yaziliyor.

GUMUS ARTIK VAR
---------------
Gumus daha once "ucretsiz kaynagi yok" diye kapatilmisti (borsalarda
paritesi yok, FRED'de gunluk seri yok, Stooq bot dogrulamasi calistiriyor).
Gold-API onu anahtarsiz veriyor. Kapatilmis bir kalemin sonradan acilmasi
mumkun -- kaynak taramasi tek seferlik bir is degil.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin; iletisim@netaris.com)"}
ZAMAN_ASIMI = 20.0

GOLD_API = "https://api.gold-api.com/price/{}"
KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker?pair={}"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC?pair={}&interval={}"

#: (kod, ad, kaynak, sembol)
#: Kod site genelinde kullanilan kimlik; sembol kaynagin kendi adlandirmasi.
VARLIKLAR = (
    ("XAU", "Altın (ons)", "gold-api", "XAU"),
    ("XAG", "Gümüş (ons)", "gold-api", "XAG"),
    ("XPT", "Platin (ons)", "gold-api", "XPT"),
    ("BTC", "Bitcoin", "kraken", "XBTUSD"),
    ("ETH", "Ethereum", "kraken", "ETHUSD"),
)


class VeriYok(Exception):
    """Kaynak cevap vermedi ya da beklenen alan gelmedi."""


@dataclass(frozen=True)
class Fiyat:
    kod: str
    ad: str
    deger: float
    an: str            # ISO 8601, kaynagin bildirdigi an
    kaynak: str

    @property
    def yas_dk(self) -> float:
        """Verinin kac dakikalik oldugu.

        Bir "canli" fiyatin ne kadar canli oldugu YAZILMALI. Dort saat
        onceki bir fiyati anlik gibi sunmak, okuru yanlis bilgilendirir.
        """
        try:
            t = datetime.fromisoformat(self.an.replace("Z", "+00:00"))
        except ValueError:
            return -1.0
        return (datetime.now(timezone.utc) - t).total_seconds() / 60.0


def _gold_api(c: httpx.Client, sembol: str) -> tuple[float, str]:
    y = c.get(GOLD_API.format(sembol))
    y.raise_for_status()
    v = y.json()
    if "price" not in v:
        raise VeriYok(f"gold-api {sembol}: fiyat alani yok")
    return float(v["price"]), str(v.get("updatedAt") or "")


def _kraken_son(c: httpx.Client, sembol: str) -> tuple[float, str]:
    y = c.get(KRAKEN_TICKER.format(sembol))
    y.raise_for_status()
    v = y.json()
    if v.get("error"):
        raise VeriYok(f"kraken {sembol}: {v['error']}")
    sonuc = v.get("result") or {}
    if not sonuc:
        raise VeriYok(f"kraken {sembol}: bos sonuc")
    # Kraken cevap anahtarini kendi adlandirmasiyla veriyor: XBTUSD ->
    # XXBTZUSD. Tek anahtar oldugu icin adiyla degil sirasiyla aliniyor.
    kalem = next(iter(sonuc.values()))
    return float(kalem["c"][0]), datetime.now(timezone.utc).isoformat()


def anlik(kodlar: tuple[str, ...] = ()) -> dict[str, Fiyat]:
    """Istenen varliklarin anlik fiyatini doner.

    Bir kaynak coktugunde digerleri DEVAM EDER. Tek bir varligin
    alinamamasi, olay motorunun tamamen susmasi anlamina gelmemeli.
    """
    secilen = [v for v in VARLIKLAR if not kodlar or v[0] in kodlar]
    cikti: dict[str, Fiyat] = {}
    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                      follow_redirects=True) as c:
        for kod, ad, kaynak, sembol in secilen:
            try:
                if kaynak == "gold-api":
                    deger, an = _gold_api(c, sembol)
                else:
                    deger, an = _kraken_son(c, sembol)
            except (httpx.HTTPError, VeriYok, KeyError, ValueError, TypeError):
                continue
            cikti[kod] = Fiyat(kod=kod, ad=ad, deger=deger,
                               an=an or datetime.now(timezone.utc).isoformat(),
                               kaynak=kaynak)
            time.sleep(0.15)      # ucretsiz servise saygili davranmak
    return cikti


#: Gun ici mum araliklari (dakika). Kraken bunlari destekliyor.
ARALIKLAR = (5, 15, 60)


def kraken_mum(sembol: str, aralik_dk: int = 15,
               adet: int = 136) -> list[tuple[int, float]]:
    """(zaman damgasi, kapanis) listesi -- en eskiden yeniye.

    Olay anindaki hareketi olcmek icin gunluk mum yetmiyor: haber
    14:00'te ciktiysa, gunun tamamini kapsayan tek mum "haberden once mi
    sonra mi" sorusunu cevaplayamaz.

    VARSAYILAN NEDEN 136 -- tam 96 degil.
    96 x 15 dk = 24 saat "eder" ama son mum YARIM: acik mum. Pencere
    23,8 saate dusuyor ve 24 saatlik karsilastirma None donuyordu. 136
    mum ~34 saatlik pencere birakiyor, gunluk karsilastirmaya payi var.
    """
    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                      follow_redirects=True) as c:
        y = c.get(KRAKEN_OHLC.format(sembol, aralik_dk))
        y.raise_for_status()
        v = y.json()
    if v.get("error"):
        raise VeriYok(f"kraken OHLC {sembol}: {v['error']}")
    sonuc = v.get("result") or {}
    # "last" imlecini atla -- geri kalan tek anahtar seri.
    seri = next((d for k, d in sonuc.items() if k != "last"), None)
    if not seri:
        raise VeriYok(f"kraken OHLC {sembol}: seri yok")
    return [(int(m[0]), float(m[4])) for m in seri[-adet:]]


def degisim(seri: list[tuple[int, float]], andan_once_sn: int) -> float | None:
    """Belirtilen kadar sure onceki fiyata gore yuzde degisim.

    Olay saatine gore "once/sonra" karsilastirmasi icin. Seri o kadar
    geriye gitmiyorsa None doner -- eksik veriyle hesaplanan bir yuzde,
    hic hesaplanmamis olmasindan kotudur.
    """
    if len(seri) < 2:
        return None
    hedef = seri[-1][0] - andan_once_sn
    onceki = [(t, f) for t, f in seri if t <= hedef]
    if not onceki:
        return None
    baz = onceki[-1][1]
    if baz == 0:
        return None
    return (seri[-1][1] - baz) / baz * 100.0
