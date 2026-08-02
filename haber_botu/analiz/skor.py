"""Bilanco Kalitesi Skoru -- 100 puan uzerinden, koddan hesaplanir.

NE OLCER, NE OLCMEZ
-------------------
Bu skor **finansal tablolarin sagligini** olcer. Hissenin cazip olup
olmadigi, fiyatinin ucuz ya da pahali oldugu, alinip alinmamasi gerektigi
hakkinda HICBIR SEY soylemez ve soyleyemez. Fiyat, piyasa degeri ve getiri
verisi bu hesaba hic girmez.

Yuksek skorlu bir sirketin hissesi deger kaybedebilir; dusuk skorlu bir
sirketinki yukselebilir. Skor sirketin defterini degerlendirir, piyasasini
degil.

TASARIM KURALLARI
-----------------
1. **Skoru model vermez, kod hesaplar.** Ayni tablolar her zaman ayni skoru
   uretir. Kurallar yayimlanabilir ve itiraz edilebilir olmalidir; modelin
   takdirine birakilan bir puan bunlarin hicbirini saglamaz.

2. **Olculemeyen kriter sifir almaz.** Nakit akis tablosu yoksa "nakit
   akisi 0/20" demek yanlistir -- veri eksikligi kotu performans degildir.
   Olculemeyen kriter hesap disi kalir, skor olculebilen puan uzerinden
   normalize edilir ve kapsam yuzdesi ayrica raporlanir.

3. **Kapsam dusukse skor yayimlanmaz.** Verinin yarisi eksikken uretilen
   "78/100" yaniltir. KAPSAM_ESIGI altinda skor yayina uygun sayilmaz.

4. **Esikler burada, tek yerde ve isimlendirilmis.** Hepsi ilk elden
   secilmis, HENUZ GERCEK VERIYLE KALIBRE EDILMEMIS degerlerdir. 20-30
   gercek bilanco uzerinde calistirilip gozden gecirilmeleri gerekir.

5. **Sektor notrlugu.** Marj *seviyesi* sektore gore cok degisir (havacilik
   ile cimento kiyaslanamaz), bu yuzden seviye degil **degisim** puanlanir.
   Seviye karsilastirmasi sektor modulunun isidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import bicim
from oranlar import Donem, Kalem, OranAdi, Rapor

# ---------------------------------------------------------------------------
# Esikler -- hepsi kalibre edilmeyi bekliyor
# ---------------------------------------------------------------------------

# Reel hasilat buyumesi (%) -> puan orani
HASILAT_ESIKLERI: list[tuple[float, float]] = [
    (20.0, 1.00),   # %20 uzeri reel buyume -> tam puan
    (10.0, 0.80),
    (0.0, 0.60),
    (-10.0, 0.30),
    (float("-inf"), 0.0),
]

# Marj degisimi (puan) -> puan orani. Daralma cezalandirilir.
MARJ_DEGISIM_ESIKLERI: list[tuple[float, float]] = [
    (2.0, 1.00),    # 2 puan ve uzeri genisleme
    (0.0, 0.80),
    (-2.0, 0.50),
    (-5.0, 0.20),
    (float("-inf"), 0.0),
]

# Faaliyet nakit akisi / FAVOK -- nakde donusum kalitesi
NAKDE_DONUSUM_ESIKLERI: list[tuple[float, float]] = [
    (0.90, 1.00),   # FAVOK'un %90'i nakde donuyor
    (0.70, 0.80),
    (0.50, 0.55),
    (0.25, 0.25),
    (float("-inf"), 0.0),
]

# Net borc / FAVOK -- dusuk olan iyi, bu yuzden ters siralanir
BORC_FAVOK_ESIKLERI: list[tuple[float, float]] = [
    (1.0, 1.00),    # 1x altinda
    (2.0, 0.85),
    (3.0, 0.60),
    (4.5, 0.30),
    (float("inf"), 0.0),
]

# FAVOK / finansman gideri -- faiz karsilama
FAIZ_KARSILAMA_ESIKLERI: list[tuple[float, float]] = [
    (6.0, 1.00),
    (3.0, 0.80),
    (2.0, 0.55),
    (1.0, 0.25),
    (float("-inf"), 0.0),
]

# Cari oran
CARI_ORAN_ESIKLERI: list[tuple[float, float]] = [
    (1.50, 1.00),
    (1.20, 0.85),
    (1.00, 0.60),
    (0.80, 0.25),
    (float("-inf"), 0.0),
]

# Net kar buyumesi ile hasilat buyumesi arasindaki makas (puan farki).
# Hasilat hizli buyurken kar yerinde sayiyorsa marj bozuluyor demektir.
MAKAS_ESIKLERI: list[tuple[float, float]] = [
    (0.0, 1.00),     # kar en az hasilat kadar buyumus
    (-10.0, 0.75),
    (-25.0, 0.45),
    (-50.0, 0.15),
    (float("-inf"), 0.0),
]

# Faaliyet disi gelirin net kar icindeki payi -- dusuk olan iyi
FAALIYET_DISI_ESIKLERI: list[tuple[float, float]] = [
    (0.10, 1.00),
    (0.25, 0.80),
    (0.40, 0.50),
    (0.60, 0.20),
    (float("inf"), 0.0),
]

# Skorun yayimlanabilmesi icin olculmesi gereken asgari puan orani
KAPSAM_ESIGI = 0.60


def _kademe(deger: float, esikler: list[tuple[float, float]], artan: bool = True) -> float:
    """Degeri esik tablosunda arayip puan oranini dondurur.

    artan=True  -> buyuk deger iyi (hasilat buyumesi gibi)
    artan=False -> kucuk deger iyi (net borc / FAVOK gibi)
    """
    for sinir, oran in esikler:
        if artan and deger >= sinir:
            return oran
        if not artan and deger <= sinir:
            return oran
    return 0.0


@dataclass(frozen=True)
class Kriter:
    """Tek bir degerlendirme kalemi.

    `tam_puan` tasarim agirligidir ve sabittir. `olculen_puan` bu donemde
    verinin yettigi kisimdir -- kismi olcum mumkundur (ornegin borc oraninin
    hesaplanip faiz karsilamasinin hesaplanamamasi). Ikisini ayirmak, kapsam
    yuzdesinin dogru cikmasi icin sart: olculen agirligi tam agirlik saymak
    eksik veriyi gizler.
    """

    ad: str
    tam_puan: int
    olculen_puan: int
    puan: float | None  # kazanilan; None = hic olculemedi
    gerekce: str

    @property
    def olculdu(self) -> bool:
        return self.puan is not None and self.olculen_puan > 0

    def bicimle(self) -> str:
        if not self.olculdu:
            return f"{self.ad:<22} {'ölçülemedi':>10}  {self.gerekce}"
        kismi = "" if self.olculen_puan == self.tam_puan else f" [kısmi /{self.tam_puan}]"
        return (
            f"{self.ad:<22} {self.puan:>5.1f}/{self.olculen_puan:<4}"
            f"  {self.gerekce}{kismi}"
        )


@dataclass
class Skor:
    kriterler: list[Kriter] = field(default_factory=list)

    @property
    def olculebilen_puan(self) -> int:
        return sum(k.olculen_puan for k in self.kriterler if k.olculdu)

    @property
    def toplam_puan(self) -> int:
        return sum(k.tam_puan for k in self.kriterler)

    @property
    def kazanilan(self) -> float:
        return sum(k.puan or 0.0 for k in self.kriterler if k.olculdu)

    @property
    def kapsam(self) -> float:
        """Olculebilen puanin toplam puana orani."""
        if self.toplam_puan == 0:
            return 0.0
        return self.olculebilen_puan / self.toplam_puan

    @property
    def skor(self) -> float | None:
        """100 uzerinden normalize skor. Hicbir kriter olculemediyse None."""
        if self.olculebilen_puan == 0:
            return None
        return self.kazanilan / self.olculebilen_puan * 100

    @property
    def yayimlanabilir(self) -> bool:
        """Kapsam esigin altindaysa skor yayimlanmamalidir."""
        return self.skor is not None and self.kapsam >= KAPSAM_ESIGI

    def metin(self) -> str:
        satirlar = ["BİLANÇO KALİTESİ SKORU", "-" * 68]
        satirlar.extend(k.bicimle() for k in self.kriterler)
        satirlar.append("-" * 68)

        if self.skor is None:
            satirlar.append("Hiçbir kriter ölçülemedi — skor üretilemiyor.")
            return "\n".join(satirlar)

        satirlar.append(
            f"{'SKOR':<24} {self.skor:>5.0f}/100   "
            f"({bicim.sayi(self.kazanilan)}/{self.olculebilen_puan} ölçülebilen puan)"
        )
        satirlar.append(f"{'kapsam':<24} {'%' + f'{self.kapsam * 100:.0f}':>5}")

        if not self.yayimlanabilir:
            eksik = [k.ad for k in self.kriterler if not k.olculdu]
            satirlar.append(
                f"\nYAYIMLANMAMALI: kapsam %{KAPSAM_ESIGI * 100:.0f} eşiğinin altında.\n"
                f"Ölçülemeyen kriterler: {', '.join(eksik)}"
            )
        satirlar.append(
            "\nBu skor finansal tabloların sağlığını ölçer. Hissenin cazipliği,\n"
            "fiyatı ya da getirisi hakkında hiçbir şey ifade etmez."
        )
        return "\n".join(satirlar)


# ---------------------------------------------------------------------------
# Kriterler
# ---------------------------------------------------------------------------

def _gelir_buyumesi(rapor: Rapor) -> Kriter:
    TAM = 20
    b = next((x for x in rapor.buyumeler if x.ad == Kalem.HASILAT), None)
    if b is None or b.reel is None:
        return Kriter("Gelir büyümesi", TAM, 0, None, "hasılat büyümesi hesaplanamadı")
    oran = _kademe(b.reel, HASILAT_ESIKLERI)
    return Kriter("Gelir büyümesi", TAM, TAM, oran * TAM,
                  f"reel {bicim.yuzde(b.reel, isaretli=True)}")


def _karlilik(rapor: Rapor) -> Kriter:
    """Marj DEGISIMI puanlanir, seviyesi degil -- seviye sektore gore degisir."""
    TAM = 20
    hedefler = (OranAdi.FAVOK_MARJI, OranAdi.NET_MARJ)
    degisimler = [
        o.degisim for o in rapor.oranlar if o.ad in hedefler and o.degisim is not None
    ]
    if not degisimler:
        return Kriter("Kârlılık", TAM, 0, None, "marj değişimi hesaplanamadı")

    ortalama = sum(degisimler) / len(degisimler)
    oran = _kademe(ortalama, MARJ_DEGISIM_ESIKLERI)
    return Kriter("Kârlılık", TAM, TAM, oran * TAM,
                  f"marjlar ortalama {bicim.puan(ortalama)}")


def _nakit_akisi(simdi: Donem) -> Kriter:
    """Sirket gercekten para kaziyor mu -- skorun en agirlikli sorusu."""
    TAM = 20
    fna = simdi.faaliyet_nakit_akisi
    if fna is None:
        return Kriter("Nakit akışı", TAM, 0, None, "nakit akış tablosu yok")

    parcalar: list[str] = []
    puan = 0.0
    olculen = 0

    # a) Faaliyet nakit akisi pozitif mi (8 puan)
    olculen += 8
    if fna > 0:
        puan += 8
        parcalar.append("FNA pozitif")
    else:
        parcalar.append("FNA NEGATİF")

    # b) FAVOK'un ne kadari nakde donuyor (7 puan)
    if simdi.favok and simdi.favok > 0:
        donusum = fna / simdi.favok
        puan += _kademe(donusum, NAKDE_DONUSUM_ESIKLERI) * 7
        olculen += 7
        parcalar.append(f"FNA/FAVÖK {bicim.sayi(donusum, 2)}")
    else:
        parcalar.append("FAVÖK yok, dönüşüm ölçülemedi")

    # c) Serbest nakit akisi pozitif mi (5 puan)
    sna = simdi.serbest_nakit_akisi
    if sna is not None:
        olculen += 5
        if sna > 0:
            puan += 5
            parcalar.append("SNA pozitif")
        else:
            parcalar.append("SNA negatif")
    else:
        parcalar.append("yatırım harcaması yok, SNA ölçülemedi")

    return Kriter("Nakit akışı", TAM, olculen, puan, ", ".join(parcalar))


def _borc_yonetimi(rapor: Rapor, simdi: Donem) -> Kriter:
    TAM = 15
    parcalar: list[str] = []
    puan = 0.0
    olculen = 0

    nb = next((o for o in rapor.oranlar if o.ad == OranAdi.NET_BORC_FAVOK), None)
    if nb is not None:
        puan += _kademe(nb.deger, BORC_FAVOK_ESIKLERI, artan=False) * 8
        olculen += 8
        parcalar.append(f"net borç/FAVÖK {bicim.kat(nb.deger)}")

    if simdi.favok and simdi.finansman_gideri and simdi.finansman_gideri > 0:
        karsilama = simdi.favok / simdi.finansman_gideri
        puan += _kademe(karsilama, FAIZ_KARSILAMA_ESIKLERI) * 7
        olculen += 7
        parcalar.append(f"faiz karşılama {bicim.sayi(karsilama, 1)}x")

    if olculen == 0:
        return Kriter("Borç yönetimi", TAM, 0, None, "borç oranları hesaplanamadı")
    return Kriter("Borç yönetimi", TAM, olculen, puan, ", ".join(parcalar))


def _marj_kalitesi(rapor: Rapor) -> Kriter:
    """Buyume makasi + karin kaynagi.

    Hasilat %40, net kar %5 buyuduyse marj bozuluyordur. Ayrica karin buyuk
    bolumu faaliyet disindan geliyorsa kalite dusuktur.
    """
    TAM = 10
    parcalar: list[str] = []
    puan = 0.0
    olculen = 0

    has = next((b for b in rapor.buyumeler if b.ad == Kalem.HASILAT), None)
    kar = next((b for b in rapor.buyumeler if b.ad == Kalem.NET_KAR), None)
    if has is not None and kar is not None:
        makas = kar.ham - has.ham
        puan += _kademe(makas, MAKAS_ESIKLERI) * 6
        olculen += 6
        parcalar.append(f"kâr-hasılat makası {bicim.puan(makas)}")

    fd = next((o for o in rapor.oranlar if o.ad == OranAdi.FAALIYET_DISI), None)
    if fd is not None:
        puan += _kademe(fd.deger / 100, FAALIYET_DISI_ESIKLERI, artan=False) * 4
        olculen += 4
        parcalar.append(f"faaliyet dışı pay {bicim.yuzde(fd.deger)}")

    if olculen == 0:
        return Kriter("Marj kalitesi", TAM, 0, None, "makas ve kâr kalitesi ölçülemedi")
    return Kriter("Marj kalitesi", TAM, olculen, puan, ", ".join(parcalar))


def _sermaye_yapisi(rapor: Rapor) -> Kriter:
    TAM = 10
    parcalar: list[str] = []
    puan = 0.0
    olculen = 0

    cari = next((o for o in rapor.oranlar if o.ad == OranAdi.CARI_ORAN), None)
    if cari is not None:
        puan += _kademe(cari.deger, CARI_ORAN_ESIKLERI) * 5
        olculen += 5
        parcalar.append(f"cari oran {bicim.kat(cari.deger)}")

    roe = next((o for o in rapor.oranlar if o.ad == OranAdi.ROE), None)
    if roe is not None and roe.degisim is not None:
        puan += _kademe(roe.degisim, MARJ_DEGISIM_ESIKLERI) * 5
        olculen += 5
        parcalar.append(f"ROE değişimi {bicim.puan(roe.degisim)}")

    if olculen == 0:
        return Kriter("Sermaye yapısı", TAM, 0, None, "sermaye oranları hesaplanamadı")
    return Kriter("Sermaye yapısı", TAM, olculen, puan, ", ".join(parcalar))


def _trend_performansi(rapor: Rapor, gecmis_buyumeler: list[float] | None) -> Kriter:
    """Analist konsensusunun yerine gecen olcu.

    Konsensus verisi lisansli ve erisilemez oldugu icin sirketi kendi
    gecmisiyle karsilastiriyoruz: bu donemin buyumesi son donemlerin
    ortalamasinin uzerinde mi?
    """
    TAM = 5
    if not gecmis_buyumeler:
        return Kriter("Trend performansı", TAM, 0, None, "geçmiş dönem verisi yok")

    b = next((x for x in rapor.buyumeler if x.ad == Kalem.HASILAT), None)
    if b is None or b.reel is None:
        return Kriter("Trend performansı", TAM, 0, None, "hasılat büyümesi hesaplanamadı")

    ortalama = sum(gecmis_buyumeler) / len(gecmis_buyumeler)
    fark = b.reel - ortalama
    if fark >= 5:
        puan, not_ = 5.0, "trendin belirgin üzerinde"
    elif fark >= 0:
        puan, not_ = 4.0, "trendin üzerinde"
    elif fark >= -5:
        puan, not_ = 2.5, "trende yakın"
    else:
        puan, not_ = 1.0, "trendin altında"

    return Kriter(
        "Trend performansı",
        TAM,
        TAM,
        puan,
        f"{bicim.yuzde(b.reel, isaretli=True)} — son {len(gecmis_buyumeler)} dönem "
        f"ort. {bicim.yuzde(ortalama, isaretli=True)}, {not_}",
    )


def hesapla(
    rapor: Rapor,
    simdi: Donem,
    gecmis_hasilat_buyumeleri: list[float] | None = None,
) -> Skor:
    """Rapordan bilanco kalitesi skorunu uretir."""
    return Skor(
        kriterler=[
            _gelir_buyumesi(rapor),
            _karlilik(rapor),
            _nakit_akisi(simdi),
            _borc_yonetimi(rapor, simdi),
            _marj_kalitesi(rapor),
            _sermaye_yapisi(rapor),
            _trend_performansi(rapor, gecmis_hasilat_buyumeleri),
        ]
    )


def tek_cumle(skor: Skor, rapor: Rapor) -> str:
    """Skorun yaninda yer alacak tek cumlelik ozet.

    Bu cumle de koddan uretilir -- en guclu ve en zayif kriteri isaret eder,
    yorum katmayi modele birakir.
    """
    olculenler = [k for k in skor.kriterler if k.olculdu and k.olculen_puan > 0]
    if not olculenler:
        return "Yeterli veri olmadığı için değerlendirme yapılamadı."

    def oran(k: Kriter) -> float:
        return (k.puan or 0.0) / k.olculen_puan

    en_guclu = max(olculenler, key=oran)
    en_zayif = min(olculenler, key=oran)

    if en_guclu.ad == en_zayif.ad:
        return f"{en_guclu.ad} tarafında tablo dengeli."
    return (
        f"{bicim.kucuk(en_guclu.ad)} tarafında güçlü, "
        f"{bicim.kucuk(en_zayif.ad)} tarafında zayıf görünüyor."
    )
