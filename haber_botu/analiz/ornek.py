"""Oran motorunun ornek calistirmasi.

DIKKAT: Buradaki rakamlar KURGUSALDIR. Gercek bir BIST sirketine ait degil,
olmadigi da acikca belirtilmelidir. Amac hattin ucundan ucuna calistigini
gostermek.

Senaryo bilincli olarak secildi: manseti "net kar yuzde 32 artti" olan ama
gerceginde reel olarak kar KAYBEDEN bir sirket. Platformun tezi tam burada:
ham rakam yaniltiyor, yorum katmani degeri yaratiyor.

Calistirmak icin:  python ornek.py
"""

from __future__ import annotations

from oranlar import Donem, EnflasyonEsasi, hesapla

# --- KURGUSAL VERI ---

ONCE = Donem(
    etiket="2024/12",
    hasilat=12_400_000_000,
    brut_kar=3_100_000_000,
    faaliyet_kari=1_860_000_000,
    favok=2_480_000_000,
    net_kar=1_240_000_000,
    aktif_toplami=28_000_000_000,
    ozkaynak=16_800_000_000,
    donen_varliklar=9_200_000_000,
    kisa_vadeli_yukumlulukler=6_100_000_000,
    ticari_alacaklar=2_600_000_000,
    stoklar=1_900_000_000,
    net_borc=4_200_000_000,
    faaliyet_disi_net=180_000_000,
    faaliyet_nakit_akisi=2_150_000_000,
    yatirim_harcamasi=900_000_000,
    finansman_gideri=520_000_000,
)

SIMDI = Donem(
    etiket="2025/12",
    hasilat=17_360_000_000,
    brut_kar=3_820_000_000,
    faaliyet_kari=1_910_000_000,
    favok=2_780_000_000,
    net_kar=1_640_000_000,
    aktif_toplami=39_500_000_000,
    ozkaynak=21_300_000_000,
    donen_varliklar=12_800_000_000,
    kisa_vadeli_yukumlulukler=9_400_000_000,
    ticari_alacaklar=4_550_000_000,
    stoklar=3_100_000_000,
    net_borc=7_900_000_000,
    faaliyet_disi_net=620_000_000,
    # Nakit tarafi hikayenin en zayif yeri: FAVOK 2,78 milyara cikarken
    # faaliyet nakit akisi 1,62 milyara dusmus -- kar nakde donusmuyor.
    faaliyet_nakit_akisi=1_620_000_000,
    yatirim_harcamasi=2_100_000_000,
    finansman_gideri=1_180_000_000,
)

# Son dort ceyregin reel hasilat buyumesi -- trend karsilastirmasi icin.
# Analist konsensusu lisansli oldugu icin sirketin kendi gecmisi olcut.
GECMIS_HASILAT_BUYUMELERI = [28.0, 34.0, 31.0, 25.0]

# Sektor karsilastirmasi (Faz 1c'de otomatiklesecek; su an elle).
# KURAL: yalnizca marj ve oran karsilastirilir, mutlak rakam ASLA.
# Rakipler ayni muhasebe esasinda (TMS 29) ve ayni para biriminde olmali.
SEKTOR = """\
Ayni donem, BIST cimento sektoru (hepsi TMS 29 duzeltilmis):

  Olcut                  ORNEK    Rakip A   Rakip B   Sektor ortancasi
  FAVOK marji            16.0%     21.5%     18.2%      19.8%
  Net kar marji           9.4%     11.0%      8.1%       9.6%
  Net borc / FAVOK        2.84x     1.20x     2.10x      1.65x
  Cari oran               1.36x     1.85x     1.42x      1.63x
  Faaliyet disi / net kar  37.8%      9.0%     15.4%      12.2%
"""

# BIST sirketleri 31.12.2023'ten itibaren TMS 29 enflasyon duzeltmesi
# uyguluyor ve KAP'taki tablolarda karsilastirmali onceki donem rakamlari da
# cari donemin satin alma gucune cevriliyor. Bu yuzden esas TMS29 ve TUFE
# verilmiyor -- vermek enflasyonu iki kez dusmek olurdu.
ESAS = EnflasyonEsasi.TMS29
ENFLASYON = None

# Karsilastirma icin: ayni rakamlar nominal kabul edilseydi bu TUFE ile
# aritilmasi gerekirdi. Yalnizca dokumantasyon amaciyla burada.
NOMINAL_SENARYO_TUFE = 35.0


if __name__ == "__main__":
    rapor = hesapla(
        sirket="Ornek Cimento Sanayi A.S.",
        kod="ORNEK",
        simdi=SIMDI,
        once=ONCE,
        esas=ESAS,
        enflasyon=ENFLASYON,
    )
    print(rapor.metin())
