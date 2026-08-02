"""Teknik gostergeler -- hepsi burada hesaplanir, model hicbir sey uretmez.

Bilanco motoruyla ayni ilke. RSI, MACD, hareketli ortalamalar, Bollinger,
ATR ve destek/direnc seviyeleri fiyat serisinden koda hesaplanir; yazi
katmani yalnizca bunlari cumleye dokur.

DIL DISIPLINI -- bu modul icin ozellikle onemli
------------------------------------------------
Teknik analiz, yatirim tavsiyesi diline en yakin duran icerik tipidir.
Kural su: **gosterge DURUMU bildirilir, EYLEM onerilmez.**

  YAZILIR : "RSI 72. Geleneksel yorumda 70 uzeri asiri alim bolgesi
            sayilir." -- olcum + yaygin kabul goren tanim
  YAZILMAZ: "RSI yuksek, satis zamani" / "hedef 75.000" / "yukselis
            bekleniyor" -- eylem onerisi ve ongoru

Destek ve direnc seviyeleri GECMIS fiyat noktalaridir, tahmin degil:
"son 90 gunde 3 kez tepki verilen seviye" bir olgudur.

`guvenlik.py` taramasi bu ayrimi ayrica denetler; sablonda olmayan cumle
zaten uretilmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Temel hesaplar
# ---------------------------------------------------------------------------

def sma(degerler: list[float], n: int) -> float | None:
    """Basit hareketli ortalama."""
    if len(degerler) < n:
        return None
    return sum(degerler[-n:]) / n


def ema_serisi(degerler: list[float], n: int) -> list[float]:
    """Ustel hareketli ortalama serisi.

    Ilk deger basit ortalamayla tohumlanir -- ilk fiyati tek basina tohum
    almak, serinin basinda belirgin sapma uretir.
    """
    if len(degerler) < n:
        return []
    k = 2 / (n + 1)
    cikti = [sum(degerler[:n]) / n]
    for d in degerler[n:]:
        cikti.append(d * k + cikti[-1] * (1 - k))
    return cikti


def rsi(degerler: list[float], n: int = 14) -> float | None:
    """Goreli Guc Endeksi -- Wilder yumusatmasiyla.

    Basit ortalama ile hesaplayan uygulamalar farkli sonuc verir; standart
    olan Wilder'dir ve grafik programlariyla tutmasi icin o kullanilir.
    """
    if len(degerler) < n + 1:
        return None

    kazanclar, kayiplar = [], []
    for onceki, simdi in zip(degerler, degerler[1:]):
        fark = simdi - onceki
        kazanclar.append(max(fark, 0.0))
        kayiplar.append(max(-fark, 0.0))

    ort_kazanc = sum(kazanclar[:n]) / n
    ort_kayip = sum(kayiplar[:n]) / n
    for k, z in zip(kazanclar[n:], kayiplar[n:]):
        ort_kazanc = (ort_kazanc * (n - 1) + k) / n
        ort_kayip = (ort_kayip * (n - 1) + z) / n

    if ort_kayip == 0:
        return 100.0
    rs = ort_kazanc / ort_kayip
    return 100 - (100 / (1 + rs))


def macd(degerler: list[float], hizli: int = 12, yavas: int = 26,
         isaret: int = 9) -> tuple[float, float, float] | None:
    """MACD cizgisi, isaret cizgisi ve histogram."""
    if len(degerler) < yavas + isaret:
        return None
    h = ema_serisi(degerler, hizli)
    y = ema_serisi(degerler, yavas)
    # Iki seri farkli uzunlukta baslar; sondan hizalanir
    boy = min(len(h), len(y))
    cizgi = [a - b for a, b in zip(h[-boy:], y[-boy:])]
    if len(cizgi) < isaret:
        return None
    isaret_serisi = ema_serisi(cizgi, isaret)
    if not isaret_serisi:
        return None
    return cizgi[-1], isaret_serisi[-1], cizgi[-1] - isaret_serisi[-1]


def bollinger(degerler: list[float], n: int = 20, k: float = 2.0):
    """Bollinger bantlari: (alt, orta, ust, bant genisligi %)."""
    if len(degerler) < n:
        return None
    pencere = degerler[-n:]
    orta = sum(pencere) / n
    varyans = sum((d - orta) ** 2 for d in pencere) / n
    sapma = varyans ** 0.5
    ust, alt = orta + k * sapma, orta - k * sapma
    genislik = (ust - alt) / orta * 100 if orta else 0.0
    return alt, orta, ust, genislik


def atr(mumlar, n: int = 14) -> float | None:
    """Ortalama Gercek Aralik -- oynaklik olcusu."""
    if len(mumlar) < n + 1:
        return None
    araliklar = []
    for onceki, simdi in zip(mumlar, mumlar[1:]):
        araliklar.append(max(
            simdi.yuksek - simdi.dusuk,
            abs(simdi.yuksek - onceki.kapanis),
            abs(simdi.dusuk - onceki.kapanis),
        ))
    return sum(araliklar[-n:]) / n


def seviyeler(mumlar, pencere: int = 90, tolerans: float = 0.015,
              en_fazla: int = 3) -> tuple[list[float], list[float]]:
    """Destek ve direnc seviyeleri -- salinim dipleri ve tepeleri.

    Bir nokta, solunda ve sagindaki `k` mumun hepsinden dusukse (ya da
    yuksekse) salinim noktasidir. Yakin seviyeler tek seviyede birlestirilir
    -- 100 ile 100,5 iki ayri direnc degil, ayni bolgedir.

    Bunlar TAHMIN DEGIL, gecmis fiyat noktalaridir.
    """
    veri = mumlar[-pencere:] if len(mumlar) > pencere else mumlar
    if len(veri) < 11:
        return [], []
    k = 3
    dipler, tepeler = [], []
    for i in range(k, len(veri) - k):
        cevre = veri[i - k:i + k + 1]
        if veri[i].dusuk == min(m.dusuk for m in cevre):
            dipler.append(veri[i].dusuk)
        if veri[i].yuksek == max(m.yuksek for m in cevre):
            tepeler.append(veri[i].yuksek)

    def kumele(noktalar: list[float]) -> list[float]:
        if not noktalar:
            return []
        noktalar = sorted(noktalar)
        kumeler = [[noktalar[0]]]
        for d in noktalar[1:]:
            if abs(d - kumeler[-1][-1]) / kumeler[-1][-1] <= tolerans:
                kumeler[-1].append(d)
            else:
                kumeler.append([d])
        # Cok test edilen seviye once gelir -- kume buyuklugu tepki sayisidir
        kumeler.sort(key=len, reverse=True)
        return [sum(c) / len(c) for c in kumeler[:en_fazla]]

    son = veri[-1].kapanis
    destek = sorted([d for d in kumele(dipler) if d < son], reverse=True)
    direnc = sorted([d for d in kumele(tepeler) if d > son])
    return destek, direnc


# ---------------------------------------------------------------------------
# Rapor
# ---------------------------------------------------------------------------

@dataclass
class Rapor:
    sembol: str
    ad: str
    kisa: str
    tur: str
    aralik: str
    mum_sayisi: int

    fiyat: float
    degisim_1g: float | None = None
    degisim_7g: float | None = None
    degisim_30g: float | None = None

    sma20: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    rsi14: float | None = None
    macd_cizgi: float | None = None
    macd_isaret: float | None = None
    macd_histogram: float | None = None
    bb_alt: float | None = None
    bb_orta: float | None = None
    bb_ust: float | None = None
    bb_genislik: float | None = None
    atr14: float | None = None

    destek: list[float] = field(default_factory=list)
    direnc: list[float] = field(default_factory=list)
    donem_zirve: float | None = None
    donem_dip: float | None = None

    @property
    def atr_yuzde(self) -> float | None:
        """Gunluk oynaklik, fiyata oran olarak."""
        if self.atr14 is None or not self.fiyat:
            return None
        return self.atr14 / self.fiyat * 100

    @property
    def zirveden_uzaklik(self) -> float | None:
        if self.donem_zirve is None or not self.donem_zirve:
            return None
        return (self.fiyat / self.donem_zirve - 1) * 100

    @property
    def ort_ustunde(self) -> list[str]:
        """Fiyatin uzerinde oldugu hareketli ortalamalar."""
        sonuc = []
        for ad, deger in (("20 günlük", self.sma20), ("50 günlük", self.sma50),
                          ("200 günlük", self.sma200)):
            if deger is not None and self.fiyat > deger:
                sonuc.append(ad)
        return sonuc

    @property
    def ort_altinda(self) -> list[str]:
        sonuc = []
        for ad, deger in (("20 günlük", self.sma20), ("50 günlük", self.sma50),
                          ("200 günlük", self.sma200)):
            if deger is not None and self.fiyat < deger:
                sonuc.append(ad)
        return sonuc


def _degisim(kapanislar: list[float], geri: int) -> float | None:
    if len(kapanislar) <= geri or kapanislar[-1 - geri] <= 0:
        return None
    return (kapanislar[-1] / kapanislar[-1 - geri] - 1) * 100


def hesapla(seri) -> Rapor:
    """Fiyat serisinden teknik gosterge raporu uretir."""
    k = seri.kapanislar
    m = seri.mumlar
    pencere = m[-90:] if len(m) > 90 else m

    bb = bollinger(k)
    mc = macd(k)
    destek, direnc = seviyeler(m)

    return Rapor(
        sembol=seri.sembol, ad=seri.ad, kisa=seri.kisa, tur=seri.tur,
        aralik=seri.aralik, mum_sayisi=len(m),
        fiyat=k[-1],
        degisim_1g=_degisim(k, 1),
        degisim_7g=_degisim(k, 7),
        degisim_30g=_degisim(k, 30),
        sma20=sma(k, 20), sma50=sma(k, 50), sma200=sma(k, 200),
        rsi14=rsi(k),
        macd_cizgi=mc[0] if mc else None,
        macd_isaret=mc[1] if mc else None,
        macd_histogram=mc[2] if mc else None,
        bb_alt=bb[0] if bb else None,
        bb_orta=bb[1] if bb else None,
        bb_ust=bb[2] if bb else None,
        bb_genislik=bb[3] if bb else None,
        atr14=atr(m),
        destek=destek, direnc=direnc,
        donem_zirve=max(x.yuksek for x in pencere),
        donem_dip=min(x.dusuk for x in pencere),
    )
