"""Binance kamuya acik piyasa verisi -- anahtar gerektirmez.

NEDEN BU KAYNAK
---------------
Teknik analiz fiyat GECMISI ister. BIST icin bu veri lisanslidir ve
ucretsiz bir kaynagi yok. Kripto ve tokenlestirilmis altin icin ise
Binance'in kamuya acik piyasa uclari anahtarsiz, CORS'lu ve gercek
zamanlidir.

Bu yuzden teknik analiz modulu YALNIZCA bu varliklari kapsar. BIST hissesi
icin teknik analiz uretmiyoruz -- veri yok, uydurma da yapmayiz.

ALTIN VE GUMUS
--------------
Altin: PAXG, bir ons altina %100 dayali token. Spot altini yakindan izler
ama LBMA fiksingi DEGILDIR; yazida da oyle etiketlenir.

Gumus: **YOK.** Binance'te paritesi bulunmuyor, FRED'de gunluk fiyat
serisi yok, Stooq bot dogrulamasi calistiriyor. Ucretsiz ve mesru bir
kaynak bulunana kadar gumus icerigi uretilmez.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

TABAN = "https://api.binance.com/api/v3"
BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin)"}
ZAMAN_ASIMI = 30.0

#: Kapsanan varliklar. Ad sayfada aynen gorunur.
VARLIKLAR = {
    "BTCUSDT": ("Bitcoin", "BTC", "kripto"),
    "ETHUSDT": ("Ethereum", "ETH", "kripto"),
    "BNBUSDT": ("BNB", "BNB", "kripto"),
    "SOLUSDT": ("Solana", "SOL", "kripto"),
    "PAXGUSDT": ("Altın (PAXG)", "PAXG", "emtia"),
}


@dataclass(frozen=True)
class Mum:
    """Tek bir donemin acilis-yuksek-dusuk-kapanis-hacim degerleri."""

    zaman: int  # milisaniye
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
    """Mum verisi ceker.

    `adet` varsayilani 260: 200 gunluk hareketli ortalamayi hesaplamak icin
    en az 200 mum gerekiyor, ustune bir miktar pay birakiliyor.
    """
    ad, kisa, tur = VARLIKLAR.get(sembol, (sembol, sembol, "bilinmiyor"))
    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI) as c:
        y = c.get(f"{TABAN}/klines",
                  params={"symbol": sembol, "interval": aralik, "limit": adet})
        y.raise_for_status()
        ham = y.json()

    if not isinstance(ham, list) or not ham:
        raise VeriYok(f"{sembol} icin mum verisi bos dondu")

    mumlar = []
    for m in ham:
        try:
            mumlar.append(Mum(
                zaman=int(m[0]),
                acilis=float(m[1]),
                yuksek=float(m[2]),
                dusuk=float(m[3]),
                kapanis=float(m[4]),
                hacim=float(m[5]),
            ))
        except (ValueError, IndexError, TypeError):
            continue

    if len(mumlar) < 30:
        raise VeriYok(
            f"{sembol} icin yalnizca {len(mumlar)} mum var; gostergeler "
            "guvenilir hesaplanamaz"
        )
    return Seri(sembol=sembol, ad=ad, kisa=kisa, tur=tur,
                aralik=aralik, mumlar=mumlar)
