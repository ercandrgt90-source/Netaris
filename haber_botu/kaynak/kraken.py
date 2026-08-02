"""Kraken kamuya acik piyasa verisi -- anahtarsiz, cografi kisit yok.

NEDEN BINANCE DEGIL
-------------------
Binance ABD IP adreslerinden gelen istekleri **HTTP 451** ("Unavailable
For Legal Reasons") ile reddediyor -- duzenleme geregi, ABD icin ayri bir
sirket (Binance.US) var. GitHub Actions sunuculari ABD'de calisiyor,
dolayisiyla otomasyon her seferinde 451 aliyordu:

    VERI CEKILEMEDI: Client error '451' for url
    'https://api.binance.com/api/v3/klines?symbol=BTCUSDT...'

Bu bir hata degil, yasal bir cografi kisit. Vekil sunucuyla asilmaya
calisilmaz.

Kraken ABD merkezli ve ABD'ye hizmet veriyor; hem yerel makineden hem
GitHub'dan calisiyor. Ustelik gunluk mum sayisi daha yuksek: 721'e karsi
Binance'in 260'i -- 200 gunluk ortalama icin bolca pay.

CIFT ADLARI
-----------
Kraken eski varlik kodlarini kullaniyor: Bitcoin "XBT" (BTC degil), ve
sonuc anahtarlari "XXBTZUSD" gibi X/Z onekli geliyor. Istek adiyla cevap
anahtari AYNI DEGIL; bu yuzden cevaptaki anahtar isimle degil, "last"
disindaki tek anahtari alarak bulunuyor.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

TABAN = "https://api.kraken.com/0/public"
BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin)"}
ZAMAN_ASIMI = 30.0

#: (istek cifti, gorunen ad, kisa kod, tur)
#: Kraken'de Bitcoin "XBT" -- kullaniciya "BTC" olarak gosteriliyor.
VARLIKLAR = {
    "XBTUSD": ("Bitcoin", "BTC", "kripto"),
    "ETHUSD": ("Ethereum", "ETH", "kripto"),
    "SOLUSD": ("Solana", "SOL", "kripto"),
    "PAXGUSD": ("Altın (PAXG)", "PAXG", "emtia"),
}

#: Gunluk mum
ARALIK_DK = 1440


@dataclass(frozen=True)
class Mum:
    zaman: int          # saniye
    acilis: float
    yuksek: float
    dusuk: float
    kapanis: float
    hacim: float


@dataclass
class Seri:
    sembol: str
    ad: str
    kisa: str
    tur: str
    aralik: str
    mumlar: list[Mum]

    @property
    def kapanislar(self) -> list[float]:
        return [m.kapanis for m in self.mumlar]

    @property
    def son(self) -> Mum:
        return self.mumlar[-1]


class VeriYok(RuntimeError):
    pass


def klines(sembol: str, aralik: str = "1d", adet: int = 260) -> Seri:
    """Gunluk mum verisi ceker.

    `aralik` ve `adet` imzasi Binance surumuyle ayni birakildi ki cagiran
    taraf (uret_teknik.py) degismeden calissin. Kraken tek istekte 720
    mum donduruyor; `adet` yalnizca sondan kirpmak icin kullaniliyor.
    """
    ad, kisa, tur = VARLIKLAR.get(sembol, (sembol, sembol, "bilinmiyor"))

    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI) as c:
        y = c.get(f"{TABAN}/OHLC",
                  params={"pair": sembol, "interval": ARALIK_DK})
        y.raise_for_status()
        veri = y.json()

    hatalar = veri.get("error") or []
    if hatalar:
        raise VeriYok(f"{sembol}: {', '.join(hatalar)}")

    sonuc = veri.get("result") or {}
    # Cevap anahtari istek adindan farkli ("XBTUSD" -> "XXBTZUSD").
    # "last" disindaki tek anahtar veri anahtaridir.
    anahtarlar = [k for k in sonuc if k != "last"]
    if not anahtarlar:
        raise VeriYok(f"{sembol} icin mum verisi bos dondu")

    mumlar: list[Mum] = []
    for m in sonuc[anahtarlar[0]]:
        try:
            mumlar.append(Mum(
                zaman=int(m[0]),
                acilis=float(m[1]),
                yuksek=float(m[2]),
                dusuk=float(m[3]),
                kapanis=float(m[4]),
                hacim=float(m[6]),
            ))
        except (ValueError, IndexError, TypeError):
            continue

    if len(mumlar) < 30:
        raise VeriYok(
            f"{sembol} icin yalnizca {len(mumlar)} mum var; gostergeler "
            "guvenilir hesaplanamaz"
        )

    return Seri(sembol=sembol, ad=ad, kisa=kisa, tur=tur,
                aralik=aralik, mumlar=mumlar[-adet:])
