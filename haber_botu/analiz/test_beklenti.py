"""beklenti.py testleri.

Bu motorun hatalari EKRANDA DOGRU GORUNUR: cumle duzgun kurulmustur,
yalnizca soyledigi sey yanlistir. Ilk surumde "issizlik orani yuksek
gelirse is gucu piyasasi GUCLU demektir" yaziyordu. O yuzden yon
burada sabitleniyor.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import beklenti as B  # noqa: E402

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


# --------------------------------------------------------------------
# SAYI BICIMI -- Turkce (binlik nokta, ondalik virgul)
# --------------------------------------------------------------------
es("yuzde bicimi", B.bicimle(3.7265, "%"), "%3,73")
es("birimli bicim", B.bicimle(158984.0, "bin kişi"), "158.984,00 bin kişi")
es("negatif deger", B.bicimle(-1459.0, "mn $"), "-1.459,00 mn $")

# --------------------------------------------------------------------
# ESIK KAYNAGI ACIKCA BELLI OLMALI.
# Onceki degeri "beklenti" diye sunmak uydurma olurdu.
# --------------------------------------------------------------------
k = B.kur("CPIAUCSL", "ABD TÜFE", "Enflasyon", 3.73, "%", "2026-06-01")
es("konsensus yoksa esik onceki deger", k.esik_kaynak, "onceki")
es("esik degeri son degere esit", k.esik_deger, k.son_deger)

k2 = B.kur("TP.TUKFIY2025.GENEL", "TÜFE", "Enflasyon", 31.75, "%",
           "2026-07-01", esik_deger=23.95, esik_birim="%")
es("konsensus varsa esik beklenti", k2.esik_kaynak, "beklenti")
es("beklenti degeri", k2.esik_deger, "%23,95")

# --------------------------------------------------------------------
# YON -- en pahali hata burada.
# --------------------------------------------------------------------
issiz = B.kur("TP.YISGUCU2.G8", "İşsizlik oranı", "İstihdam ve ücret",
              7.4, "%", "2026-06-01")
ust = issiz.dallar[0]
es("ustteki dal 'uzerinde'", ust.yon, "ustunde")
dogru("issizlik YUKSEK gelirse SOGUMA anlatilir",
      "soğuma" in ust.mekanizma or "gevşe" in ust.mekanizma)
dogru("issizlik yuksekken 'guclu' YAZILMAZ",
      "güçlü" not in ust.mekanizma)

istihdam = B.kur("PAYEMS", "Tarım Dışı İstihdam", "İstihdam ve ücret",
                 57.0, "bin kişi", "2026-06-01")
dogru("istihdam YUKSEK gelirse GUCLU anlatilir",
      "güçlü" in istihdam.dallar[0].mekanizma)

# Ayni konu, ters seri -> dallar YER DEGISTIRMIS olmali.
dogru("ters seri dallari yer degistiriyor",
      issiz.dallar[0].mekanizma != istihdam.dallar[0].mekanizma)
es("ters seri dallari ayni kumeden",
   sorted([d.mekanizma for d in issiz.dallar]),
   sorted([d.mekanizma for d in istihdam.dallar]))

cari = B.kur("TP.HARICCARIACIK.K1", "Cari denge", "Dış ticaret",
             -1459.0, "mn $", "2026-05-01")
dogru("cari denge YUKSEK gelirse acik DARALIR",
      "daralır" in cari.dallar[0].mekanizma)

# --------------------------------------------------------------------
# YON IDDIASI YOK: hicbir mekanizma cumlesi bir varligin fiyatinin ne
# yapacagini soylememeli. Bu, varlik grafindaki "bag yon soylemez"
# kuralinin ayni uygulamasi.
# --------------------------------------------------------------------
yasak = ("altın düşer", "altın yükselir", "borsa düşer", "borsa yükselir",
         "dolar güçlenir", "dolar zayıflar", "baskılanır")
for konu, (a, b) in B.MEKANIZMA.items():
    for metin in (a, b):
        for y in yasak:
            dogru(f"{konu}: '{y}' iddiasi yok", y not in metin.lower())

# --------------------------------------------------------------------
# OLCULMUS TEPKI -- az gozlemde YAZILMIYOR.
# Uc gozlemin ortalamasi bir egilim degildir.
# --------------------------------------------------------------------
es("iki gozlemde olcum yok", B._tepki_ozeti([("XAU", 1.0), ("XAU", 2.0)]), "")
ozet = B._tepki_ozeti([("XAU", 1.0), ("XAU", -2.0), ("XAU", 3.0)])
dogru("uc gozlemde olcum yaziliyor", bool(ozet))
dogru("olcum gozlem sayisini soyluyor", "3 gözlem" in ozet)
dogru("olcum yon iddia etmiyor, SAYIM veriyor", "yukarı" in ozet)

# Farkli varliklar ayri sayiliyor; biri esigi gecmiyorsa yazilmiyor.
karma = [("XAU", 1.0), ("XAU", 2.0), ("XAU", 3.0), ("BTC", 5.0)]
o2 = B._tepki_ozeti(karma)
dogru("esigi gecen varlik yaziliyor", "XAU" in o2)
dogru("esigi gecmeyen varlik yazilmiyor", "BTC" not in o2)

# --------------------------------------------------------------------
# EKSIK VERI
# --------------------------------------------------------------------
bos = B.kur("X", "X", "Enflasyon", None, "%", "")
dogru("son deger yoksa kutu basilmaz", not bos.dolu)

tanimsiz = B.kur("X", "X", "Bilinmeyen konu", 5.0, "%", "2026-01-01")
dogru("mekanizma tanimsizsa dal uretilmez", not tanimsiz.dallar)
dogru("mekanizma tanimsizsa kutu basilmaz", not tanimsiz.dolu)

# --------------------------------------------------------------------
# KIYAS TABANI CUMLEYE YAZILMALI.
#
# Kullanicinin gosterdigi hata: Tarim Disi Istihdam'da beklenti 85 bin,
# onceki 57 bin. Esik onceki degerken cumle "beklenenden güçlü"
# diyordu -- olmayan bir beklentiye gore konusuyordu. Gerceklesen
# 70 bin gelse "onceki uzerinde" ama "beklentinin altinda"dir.
# --------------------------------------------------------------------
_yok = B.kur("PAYEMS", "NFP", "İstihdam ve ücret", 57.0, "bin kişi",
             "2026-06-01")
dogru("konsensus yokken 'beklenenden' YAZILMAZ",
      "beklenenden" not in _yok.dallar[0].mekanizma)
dogru("konsensus yokken kiyas 'önceki döneme göre'",
      "önceki döneme göre" in _yok.dallar[0].mekanizma)

_var = B.kur("PAYEMS", "NFP", "İstihdam ve ücret", None, "", "",
             esik_metin="85K", son_metin="57K")
es("konsensus varsa esik odur", _var.esik_deger, "85K")
es("konsensus varsa kaynak 'beklenti'", _var.esik_kaynak, "beklenti")
es("konsensus varsa son deger kaynagin onceki degeri",
   _var.son_deger, "57K")
dogru("konsensus varken kiyas 'beklenenden'",
      "beklenenden" in _var.dallar[0].mekanizma)
dogru("dal basligi konsensusu tasiyor", "85K" in _var.dallar[0].baslik)

# Yer tutucu HICBIR cumlede acikta kalmamali -- kalirsa ekranda
# "{kiyas}" diye gorunurdu.
for _k, (_a, _b) in B.MEKANIZMA.items():
    for _m in (_a, _b):
        dogru(f"{_k}: yer tutucu bicimlenebilir",
              "{kiyas}" not in _m.format(kiyas="X"))
_hepsi = B.kur("CPIAUCSL", "x", "Enflasyon", 3.0, "%", "2026-01-01")
for _d in _hepsi.dallar:
    dogru("ciktida yer tutucu kalmiyor", "{" not in _d.mekanizma)


print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  X", k)
sys.exit(1 if kaldi else 0)
