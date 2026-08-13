"""Teknik gosterge formulleri -- ELLE hesaplanabilir degerlerle.

NEDEN VAR
---------
Bu modul EMA, RSI, SMA ve Bollinger hesapliyor ve sonuclari sayfada
SAYI olarak basiliyor. Testi HIC YOKTU.

Bir formul hatasi burada tam olarak makro verisindeki gibi sessiz
olurdu: deger makul araliktadir, birimi dogrudur, denetimden gecer.
Yayimlanan ABD TUFE'sinin %3,73 yerine %3,46 olmasi gerektigini de
ancak KAYNAKTAN yeniden hesaplayinca gormustuk.

YONTEM: beklenen degerler ELLE hesaplanabilir secildi. Modulun kendi
ciktisini beklenen deger olarak yazmak, formulu degil kendini
dogrulayan bir test uretirdi -- hata varsa onu da kilitlerdi.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import teknik  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama, tolerans=1e-9):
    global _gecti, _kaldi
    if isinstance(bulunan, float) and isinstance(beklenen, float):
        tamam = abs(bulunan - beklenen) <= tolerans
    else:
        tamam = bulunan == beklenen
    if tamam:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


print("\nTeknik gostergeler -- elle dogrulanabilir degerler\n")

# --- SMA ---------------------------------------------------------
esit(teknik.sma([1.0, 2.0, 3.0, 4.0], 4), 2.5, "SMA: (1+2+3+4)/4")
esit(teknik.sma([1.0, 2.0, 3.0, 4.0], 2), 3.5,
     "SMA yalnizca SON n degeri kullaniyor: (3+4)/2")
esit(teknik.sma([1.0, 2.0], 5), None, "veri yetmezse None -- uydurma yok")

# --- EMA ---------------------------------------------------------
#
# n=3, [1,2,3,4,5]:
#   tohum = (1+2+3)/3 = 2          <- BASIT ortalama ile tohumlaniyor
#   k = 2/(3+1) = 0,5
#   4 -> 4*0,5 + 2*0,5 = 3
#   5 -> 5*0,5 + 3*0,5 = 4
e = teknik.ema_serisi([1.0, 2.0, 3.0, 4.0, 5.0], 3)
esit(e, [2.0, 3.0, 4.0], "EMA serisi: elle hesaplanan uc deger")

# Tohumun BASIT ORTALAMA olmasi bir karar ve korunmali: ilk fiyati
# tek basina tohum almak serinin basinda belirgin sapma uretir.
esit(teknik.ema_serisi([10.0, 20.0, 30.0], 3)[0], 20.0,
     "EMA tohumu ilk fiyat DEGIL, ilk n degerin ortalamasi")

# Sabit seride EMA o sabite esit kalmali -- formulun en temel sagdirmasi.
esit(teknik.ema_serisi([7.0] * 30, 10)[-1], 7.0,
     "sabit seride EMA sabitin kendisi")

esit(teknik.ema_serisi([1.0, 2.0], 5), [],
     "veri yetmezse BOS liste -- kisa seriden gosterge uretilmiyor")

# DOGRUSAL SERIDE EMA TAM OLARAK SMA'YA ESIT.
#
# Ilk yazimda "artan seride EMA > SMA" diye kaba bir beklenti
# yazmistim ve test DUSTU. Kod dogruydu, beklentim yanlisti; olcunce
# cok daha guclu bir ozellik cikti:
#
#   Egimi sabit bir seride her iki ortalamanin da gecikmesi (n-1)/2'dir.
#   SMA  = son - (n-1)/2
#   EMA  = son - (1-k)/k  ve  k = 2/(n+1)  =>  (1-k)/k = (n-1)/2
#
# Yani ikisi AYNI degere yakinsiyor. Bu tek esitlik hem yumusatma
# katsayisini hem tohumlamayi birden dogruluyor -- katsayi yanlis
# olsaydi esitlik bozulurdu.
artan = [float(i) for i in range(1, 201)]
esit(teknik.ema_serisi(artan, 20)[-1], teknik.sma(artan, 20),
     "dogrusal seride EMA = SMA (ikisinin de gecikmesi (n-1)/2)",
     tolerans=1e-6)

# Duyarlilik farki SICRAMADA gorunuyor: seri duz giderken son deger
# firlarsa EMA daha hizli tepki verir.
duz = [10.0] * 60 + [20.0] * 3
esit(teknik.ema_serisi(duz, 20)[-1] > teknik.sma(duz, 20), True,
     "sicramada EMA, SMA'dan hizli tepki veriyor")

# --- RSI ---------------------------------------------------------
#
# Kesintisiz artan seride kayip yok: RSI 100.
esit(teknik.rsi([float(i) for i in range(1, 30)], 14), 100.0,
     "hic kayip yoksa RSI 100")

# Kesintisiz dusen seride kazanc yok: RSI 0.
esit(teknik.rsi([float(i) for i in range(30, 1, -1)], 14), 0.0,
     "hic kazanc yoksa RSI 0")

esit(teknik.rsi([1.0, 2.0], 14), None,
     "veri yetmezse None -- eksik veriyle gosterge uretilmiyor")

# RSI sinirlari: her zaman 0-100 arasinda olmali.
import random  # noqa: E402
random.seed(7)
_d = [100.0]
for _ in range(200):
    _d.append(max(1.0, _d[-1] * (1 + random.uniform(-0.05, 0.05))))
_r = teknik.rsi(_d, 14)
esit(0.0 <= _r <= 100.0, True, f"RSI 0-100 araliginda kaliyor ({_r:.1f})")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
