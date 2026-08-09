"""ceviri.py testleri -- AGA CIKMAZ.

Ceviri hatalari sessizdir: baslik duzgun Turkce gorunur, yalnizca
YANLIStir. Buradaki durumlarin hepsi uretimde gorulen gercek basliklar.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import ceviri  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


# ------------------------------------------------------------- tire
#
# Cevirmen birlesik sozcuklerin tiresinin etrafina bosluk ekliyor.
# 313 basligin 12'sinde goruldu.
print("Tire -- cevirmenin ekledigi bosluklar kaldirilmali")
for ad, kaynak, ceviri_metni, beklenen in (
    ("ABD-Kanada",
     "The U.S.-Canada natural gas trade value rose in 2025",
     "ABD - Kanada doğalgaz ticaret değeri 2025'te arttı",
     "ABD-Kanada doğalgaz ticaret değeri 2025'te arttı"),
    ("Mythos-FT",
     "Bytedance targets mega AI model approaching Anthropic's Mythos-FT",
     "Bytedance, Anthropic'in Mythos - FT'sine yaklaşan model",
     "Bytedance, Anthropic'in Mythos-FT'sine yaklaşan model"),
    ("Asya-Pasifik",
     "Firmus: Nvidia AI factory growth in Australia and Asia-Pacific",
     "Firmus: Avustralya ve Asya - Pasifik'te Nvidia AI büyümesi",
     "Firmus: Avustralya ve Asya-Pasifik'te Nvidia AI büyümesi"),
    # Kaynakta HIC tire yok: bosluklu tire tamamen cevirmenin isi.
    ("Q&A -> Soru-Cevap",
     "Christine Lagarde: Monetary policy statement (with Q&A)",
     "Christine Lagarde: para politikası açıklaması (Soru - Cevap ile)",
     "Christine Lagarde: para politikası açıklaması (Soru-Cevap ile)"),
):
    es(ad, ceviri.tire_duzelt(ceviri_metni, kaynak), beklenen)

# BOZMAMASI GEREKENLER. Ikisi de ilk yazimda BOZULDU.
print("\nTire -- kaynagin kendi ayiricisina dokunulmamali")
for ad, kaynak, metin in (
    # Kaynakta "May-July" birlesik AMA " - " ile ayrilan baska bir parca
    # da var: cevirmen "vs"i de " - " yapmis. Sayilar tutmuyor.
    ("vs -> ikinci tire",
     "Swedish Apartment Prices Rise 4.6% May-July vs Year Earlier",
     "İsveç'te Daire Fiyatları %4,6 Arttı Mayıs - Temmuz - Bir Önceki Yıl"),
    # Kaynak eki tireyle baglamis: " -Lloyds". Bosluga komsu tire
    # ayiricidir, birlesik sozcuk degil.
    ("-Lloyds eki",
     "UK house prices rose 0.1% on the year in July -Lloyds",
     "İngiltere'de konut fiyatları %0,1 arttı - Lloyd's"),
    # Kaynagin kendisi bosluklu tire kullaniyor.
    ("kaynakta bosluklu tire",
     "Iran talks in focus; Sandisk, Block earnings - what moves markets",
     "İran görüşmeleri odakta; Sandisk, Block kazançları - piyasaları"),
    ("baslikta tarih ayirici",
     "Financial Accounts - 2026 Q1",
     "Finansal Hesaplar - 2026 I. Çeyrek"),
):
    es(ad, ceviri.tire_duzelt(metin, kaynak), metin)

print("\nTire -- sinir durumlar")
es("bos ceviri", ceviri.tire_duzelt("", "a-b"), "")
es("bos kaynak", ceviri.tire_duzelt("A - B", ""), "A - B")
es("tiresiz metin", ceviri.tire_duzelt("Basit baslik", "Simple title"),
   "Basit baslik")

# --------------------------------------------------------- bicim
print("\nBicim duzeltmeleri")
es("yuzde bitisik", ceviri._duzelt("Enflasyon % 2,7 oldu"),
   "Enflasyon %2,7 oldu")
es("kesme oncesi bosluk", ceviri._duzelt("2027 'nin ilk ceyregi"),
   "2027'nin ilk ceyregi")
es("ozel ad korunuyor", ceviri._duzelt("Bölgeler Bankası açıkladı"),
   "Regions Bank açıkladı")
es("EIA kisaltmasi", ceviri._duzelt("ÇED Doğal Gaz raporu"),
   "EIA Doğal Gaz raporu")

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
