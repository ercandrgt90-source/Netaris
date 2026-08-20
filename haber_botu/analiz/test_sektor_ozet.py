"""Sektor ozeti -- medyan, asgari ornek ve YARGISIZLIK."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sektor_ozet as so  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama):
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


print("\nSektor ozeti\n")

# --- MEDYAN, ORTALAMA DEGIL ---
#
# Turkiye'de enflasyon donemi oranlari uc deger uretiyor. Olculmus
# ornek: TERA'nin hasilat buyumesi bir donemde %5987 idi. Ortalama
# alinsaydi sektor o tek sayinin etrafinda tanimlanirdi.
esit(so.medyan([10.0, 12.0, 14.0, 5987.0]), 13.0,
     "UC DEGER medyani tasimiyor (ortalama 1505 olurdu)")
esit(so.medyan([10.0, 20.0, 30.0]), 20.0, "tek sayida orta deger")
esit(so.medyan([10.0, None, 20.0, 30.0]), 20.0, "None'lar eleniyor")

# --- ASGARI ORNEK ---
esit(so.medyan([10.0, 20.0]), None,
     "iki sirketlik 'sektor' medyani URETILMIYOR")
esit(so.medyan([]), None, "bos sektor")
esit(so.EN_AZ_SIRKET, 3, "asgari uc sirket")

# --- sektor medyanlari ---
SIRKET = {
    "A": {"brut_marj": 20.0, "net_marj": 8.0, "roe": 15.0},
    "B": {"brut_marj": 30.0, "net_marj": 10.0, "roe": 25.0},
    "C": {"brut_marj": 40.0, "net_marj": 12.0, "roe": 35.0},
}
m = so.sektor_medyanlari(SIRKET)
esit(m["brut_marj"], 30.0, "brut marj medyani")
esit(m["roe"], 25.0, "ROE medyani")
esit("cari_oran" in m, False, "hic veri olmayan oran icin medyan yok")

# Bir sirkette bir oran eksikse o oran icin sayilmiyor ama DIGER
# oranlari sektore katkida bulunmaya devam ediyor -- sirketi tumden
# elemek sektoru gereksiz daraltirdi.
EKSIKLI = dict(SIRKET, **{"D": {"net_marj": 9.0, "roe": 20.0}})
m2 = so.sektor_medyanlari(EKSIKLI)
esit(m2["brut_marj"], 30.0, "brut marji olmayan sirket o orani BOZMUYOR")
esit(m2["net_marj"], 9.5, "ayni sirket net marja KATILIYOR")

# --- konum ---
k = so.konumlar({"brut_marj": 45.0, "roe": 10.0}, m, 3)
esit([x.oran for x in k], ["brut_marj", "roe"], "iki oran karsilastirildi")
esit(k[0].deger > k[0].medyan, True, "brut marj medyanin uzerinde")
esit(round(k[0].fark_yuzde, 1), 50.0, "medyandan %50 uzakta")

# Bir tarafi eksik olan oran KARSILASTIRILMIYOR -- olmayan olcumu
# sifir sayip karsilastirmak, olcum uydurmak olurdu.
esit(so.konumlar({"cari_oran": 2.0}, m, 3), [],
     "medyani olmayan oran karsilastirilmiyor")
esit(so.konumlar({}, m, 3), [], "orani olmayan sirket")

# --- YARGI ICERMEMELI ---
#
# "Sektor medyaninin uzerinde" bir SIRALAMA; "daha iyi", "guclu",
# "cazip" bir YARGI. Hangi oranin yuksek olmasinin iyi oldugu is
# modeline gore degisir ve o karar okurun.
YASAK = ("iyi", "kötü", "güçlü", "zayıf", "cazip", "başarılı",
         "olumlu", "olumsuz", "riskli")
c = k[0].cumle
esit(any(y in c.lower() for y in YASAK), False,
     f"cumlede YARGI sozcugu yok: {c!r}")
esit("medyanının üzerinde" in c, True, "cumle konumu tarif ediyor")
esit("3 şirketlik" in c, True, "kac sirkete dayandigi CUMLEDE yaziyor")

# Medyan sifirsa fark tanimsiz -- bolme hatasi olmamali.
sifir = so.Konum("x", "X", 5.0, 0.0, 3)
esit(sifir.fark_yuzde, 0.0, "medyan sifirken bolme hatasi yok")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
