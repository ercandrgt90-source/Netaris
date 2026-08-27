"""uret_ai_yorum.girdi_kur testleri -- AGA CIKMAZ, MODEL CAGIRMAZ.

Girdi neyi tasirsa model onu anlatiyor. Buradaki durum uretimde
gorulen gercek bir hatanin dondurulmus halidir.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "ai"), str(_KOK / "analiz"),
                str(_KOK / "kaynak")]

import uret_ai_yorum as U  # noqa: E402
import yorumcu  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


class SahteDosya:
    """Dosyanin girdi_kur'un okudugu alanlari."""

    def __init__(self, acilis="", bulgular=(), turkiye=()):
        self.acilis = acilis
        self.bulgular = list(bulgular)
        self.turkiye = list(turkiye)
        self.duyarlilik = [("Enerji", 1, 1), ("Havayolu", 1, 1)]
        self.izlenecekler = ["Brent", "Hürmüz Boğazı"]

    # SAHTE, GERCEGINI YANSITMALI.
    # Gercek `Dosya` bu ikisini ozellik olarak hesapliyor; sahte
    # yalnizca alanlari tasisaydi, kural degistiginde test eski
    # davranisi dogrulamaya devam ederdi.
    @property
    def dolu(self):
        return bool(self.turkiye or self.duyarlilik or self.izlenecekler)

    @property
    def acilis_basilir(self):
        return bool(self.acilis) and not self.dolu


BULGU = "Brent 88,90 $ (bir ayda +%29,4)"


# ------------------------------------------------------------------
# OLCUMU OLMAYAN HABERE DOSYA BULGUSU GONDERILMEZ.
#
# Olculdu ve ANA SAYFADA YAN YANA YAYIMLANDI: "Yemen'de Mocha limanina
# saldiri", "Iran cumhurbaskani Hamaney'le gorustu" ve "Axios roportaji"
# haberlerinin UCU DE ayni cumleyle basladi -- "Brent petrolun kapanis
# fiyati 88,90 $...". Ucu de ayni jeopolitik dosyaya bagliydi ve o
# dosyadaki tek sayi Brent'ti; model elindeki tek olcumu anlatti.
# ------------------------------------------------------------------
print("Olcumu olmayan haber -- dosya bulgusu gonderilmemeli")
olcumsuz = {"baslik": "Yemen askeri sözcüsü: Mocha limanına saldırı",
            "konu": "Jeopolitik", "kurum": "AA", "ozet": ""}
g = U.girdi_kur(olcumsuz, SahteDosya(bulgular=[BULGU]))
dogru("bulgu satiri YOK", "Bulgu:" not in g)
dogru("Brent sayisi girdide YOK", "88,90" not in g)
dogru("haber basligi VAR", "Mocha" in g)
dogru("sektor listesi VAR -- sayi degil yapi", "Etkilenen sektörler" in g)
dogru("izlenecekler VAR", "İzlenecekler" in g)
es("mekanizma yonergesine dusuyor", yorumcu.olcum_var(g), False)

# ------------------------------------------------------------------
# HABERIN KENDI OLCUMU VARSA baglam GONDERILIR: orada dosya bulgusu
# yorumu saptirmiyor, zenginlestiriyor.
# ------------------------------------------------------------------
print("\nOlcumu olan haber -- baglam gonderilmeli")
olcumlu = {"baslik": "ABD TÜFE temmuzda %2,8", "konu": "Enflasyon",
           "kurum": "BLS", "ozet": "Gerçekleşen %2,8, beklenti %2,9"}
g2 = U.girdi_kur(olcumlu, SahteDosya(bulgular=[BULGU]))
dogru("bulgu satiri VAR", "Bulgu:" in g2)
dogru("haberin kendi verisi VAR", "beklenti %2,9" in g2)
es("veri yonergesine dusuyor", yorumcu.olcum_var(g2), True)

# Acilis cumlesi de haberin KENDI olcumu sayilir.
print("\nAcilis cumlesi haberin kendi olcumudur")
g3 = U.girdi_kur({"baslik": "TCMB faiz karari", "konu": "Para politikası",
                  "kurum": "TCMB", "ozet": ""},
                 SahteDosya(acilis="Politika faizi %37'de sabit",
                            bulgular=[BULGU]))
dogru("acilis varken bulgu da gonderiliyor", "Bulgu:" in g3)

# ------------------------------------------------------------------
# `neden_onemli` HICBIR DURUMDA gonderilmiyor -- model onu oldugu gibi
# kopyaliyordu ve uc yorum ayni cumleyle bitiyordu.
# ------------------------------------------------------------------
print("\nKopyalanmasini istemedigimiz metin hic gonderilmiyor")
dogru("neden_onemli girdide yok",
      "neden_onemli" not in U.girdi_kur(
          {**olcumlu, "neden_onemli": "Bu cumle kopyalanmamali"},
          SahteDosya()))

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
