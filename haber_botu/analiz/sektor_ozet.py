"""Sektor ozeti -- sirketin kendi sektorune gore nerede durdugu.

    sirket oranlari + sektordeki digerleri  ->  medyan  ->  konum

NEDEN MEDYAN, ORTALAMA DEGIL
----------------------------
Turkiye'de enflasyon donemi oranlari UC DEGER uretiyor: tek bir
sirketin %4000 hasilat buyumesi (bir onceki donem neredeyse sifirsa)
sektor ortalamasini tek basina tasiyor ve geri kalan her sirket
"ortalamanin altinda" gorunuyor. Medyan bu tek kalemden etkilenmiyor.

Olculmus ornek: TERA'nin hasilat buyumesi bir donemde %5987 idi.
Ortalama alinsaydi "araci kurum sektoru" o tek sayinin etrafinda
tanimlanirdi.

NEDEN ASGARI ORNEK SARTI
------------------------
Iki sirketlik bir sektorde "medyan" iki sayinin ortasi demek ve
"sektor boyle" diye sunulamaz. `EN_AZ_SIRKET` altindaki sektor icin
ozet URETILMIYOR -- az veriyle konusmak, susmaktan kotudur.

NE SOYLENMIYOR
--------------
Konum bir SIRALAMA, bir YARGI degil. "Sektor medyaninin uzerinde"
cumlesi kuruluyor; "daha iyi", "guclu", "cazip" gibi degerlendirme
sozcukleri KURULMUYOR. Hangi oranin yuksek olmasinin iyi oldugu
sektore ve is modeline gore degisir; onu okur ve yazar karar verir.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

#: Bu sayidan az sirketi olan sektor icin ozet uretilmiyor.
#:
#: UC secildi: iki sirkette medyan iki sayinin ortalamasidir ve
#: "sektor" iddiasini tasimaz. Uc, en az bir sirketin gercekten
#: ortada olmasini saglayan en kucuk sayi.
EN_AZ_SIRKET = 3

#: Karsilastirilan oranlar. Hepsi `oranlar.py` tarafindan zaten
#: hesaplaniyor; burada yeniden hesap YOK, yalnizca karsilastirma.
ORANLAR = (
    ("brut_marj", "Brüt kâr marjı"),
    ("net_marj", "Net kâr marjı"),
    ("roe", "Özkaynak kârlılığı"),
    ("cari_oran", "Cari oran"),
    ("borc_ozkaynak", "Borç / özkaynak"),
)


@dataclass(frozen=True)
class Konum:
    """Bir oranin sektor icindeki yeri."""

    oran: str
    ad: str
    deger: float
    medyan: float
    sirket_sayisi: int

    @property
    def fark_yuzde(self) -> float:
        """Medyandan yuzde kac uzakta. Medyan sifirsa tanimsiz."""
        if not self.medyan:
            return 0.0
        return (self.deger - self.medyan) / abs(self.medyan) * 100

    @property
    def cumle(self) -> str:
        """Okura gosterilen cumle. YARGI ICERMIYOR -- bkz. modul basi."""
        yon = "üzerinde" if self.deger > self.medyan else (
            "altında" if self.deger < self.medyan else "seviyesinde")
        return (f"{self.ad}, {self.sirket_sayisi} şirketlik sektör "
                f"medyanının {yon}")


def medyan(degerler) -> float | None:
    """Bos ve None'lari eleyip medyan doner. Yetersizse None."""
    temiz = [d for d in degerler if d is not None]
    if len(temiz) < EN_AZ_SIRKET:
        return None
    return statistics.median(temiz)


def sektor_medyanlari(sirketler: dict[str, dict]) -> dict[str, float]:
    """{kod: {oran: deger}} -> {oran: medyan}.

    Her oran KENDI dolu sayisiyla degerlendiriliyor: bir sirkette
    brut marj yoksa (GYO gibi) o oran icin sayilmiyor ama diger
    oranlari sektore katkida bulunmaya devam ediyor. Sirketi tumden
    elemek, sektoru gereksiz yere daraltirdi.
    """
    cikti: dict[str, float] = {}
    for anahtar, _ad in ORANLAR:
        m = medyan([o.get(anahtar) for o in sirketler.values()])
        if m is not None:
            cikti[anahtar] = m
    return cikti


def konumlar(kendi: dict[str, float], medyanlar: dict[str, float],
             sirket_sayisi: int) -> list[Konum]:
    """Sirketin oranlarini sektor medyanlariyla karsilastirir.

    Yalnizca IKI TARAFTA DA olan oranlar karsilastiriliyor. Bir tarafi
    eksik olani "sifir" sayip karsilastirmak, olmayan bir olcumu
    olcum gibi sunmak olurdu.
    """
    cikti: list[Konum] = []
    for anahtar, ad in ORANLAR:
        d, m = kendi.get(anahtar), medyanlar.get(anahtar)
        if d is None or m is None:
            continue
        cikti.append(Konum(anahtar, ad, d, m, sirket_sayisi))
    return cikti
