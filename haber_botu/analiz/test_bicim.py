"""bicim.py testleri.

Buradaki kurallarin hepsi sessizce yanlis calisabilecek turden: yuzde
isaretinin yeri, ondalik ayraci, Turkce'ye ozgu buyuk/kucuk harf cevrimi.
Hicbiri hata firlatmiyor, sadece yanlis metin uretiyor -- bu yuzden test
edilmeleri sart.

Calistirma:  python analiz/test_bicim.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import bicim  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}\n         bulunan : {bulunan!r}")


print("\nYuzde -- isaret sayinin ONUNDE, ondalik virgul")
esit(bicim.yuzde(40.0), "%40,0", "yuzde(40.0) -> %40,0")
esit(bicim.yuzde(9.44), "%9,4", "yuvarlama tek basamak")
esit(bicim.yuzde(40.0, isaretli=True), "+%40,0", "artili degisim")
esit(bicim.yuzde(-5.2, isaretli=True), "-%5,2", "eksili degisim -- isaret en basta")
esit(bicim.yuzde(0.0, isaretli=True), "+%0,0", "sifir artili sayilir")
esit(bicim.yuzde(None), "—", "eksik deger tire")
esit("40,0%" in bicim.yuzde(40.0), False, "Ingilizce bicim URETILMIYOR")

print("\nFaiz hassasiyeti -- ikinci ondalik baz puan demek")
esit(bicim.yuzde(4.68, basamak=2), "%4,68", "tahvil getirisi iki ondalik")
esit(bicim.yuzde(4.68), "%4,7", "varsayilan tek ondalik (fiyat/marj icin)")
esit(bicim.yuzde(4.675, basamak=2), "%4,67", "tam yarim -> bankaci yuvarlamasi (cift basamaga)")
esit(bicim.yuzde(4.676, basamak=2), "%4,68", "yarimin ustu yukari yuvarlanir")

print("\nTarih -- Turkce okunus")
esit(bicim.tarih("2026-07-27"), "27 Temmuz 2026", "ISO -> Turkce")
esit(bicim.tarih("2026-01-01"), "1 Ocak 2026", "yilin ilk gunu")
esit(bicim.tarih("2026-12-31"), "31 Aralık 2026", "yilin son gunu")
esit(bicim.tarih("gecersiz"), "gecersiz", "cozumlenemezse girdi aynen doner")
esit(bicim.tarih("2026-13-01"), "2026-13-01", "gecersiz ay -- uydurma ay adi yok")

print("\nCarpan ve puan")
esit(bicim.kat(2.8421), "2,84x", "carpan iki basamak")
esit(bicim.kat(None), "—", "eksik carpan")
esit(bicim.puan(-3.0), "-3,0 puan", "negatif puan degisimi")
esit(bicim.puan(0.3), "+0,3 puan", "pozitif puan degisimi isaretli")
esit(bicim.sayi(1234.5, 1), "1234,5", "ondalik ayraci virgul")

print("\nTurkce buyuk/kucuk harf -- Python'un varsayilani yanlis")
esit(bicim.buyuk("istanbul"), "İSTANBUL", "i -> İ (Python 'I' verirdi)")
esit(bicim.kucuk("İSTANBUL"), "istanbul", "İ -> i")
esit(bicim.kucuk("Kârlılık"), "kârlılık", "sapkali harf korunuyor")
esit(bicim.kucuk("Nakit akışı"), "nakit akışı", "kriter adi kucultme")
esit(bicim.bas_harf("işletme geliri"), "İşletme geliri", "bas harf i -> İ")
esit(bicim.bas_harf("zarardan kâra geçiş"), "Zarardan kâra geçiş", "bas harf z -> Z")
esit(bicim.bas_harf(""), "", "bos metin cokmez")

print("\nKisa unvan -- amac dogru kisaltma degil, YANLIS kisaltma uretmemek")
esit(bicim.kisa_ad("Örnek Çimento Sanayi A.Ş."), "Örnek Çimento",
     "hukuki bicim ve 'Sanayi' atiliyor")
esit(bicim.kisa_ad("Türk Hava Yolları A.O."), "Türk Hava Yolları",
     "uc sozcuklu ad korunuyor")
esit(bicim.kisa_ad("Ereğli Demir ve Çelik Fabrikaları T.A.Ş."), "Ereğli Demir",
     "baglacla bitmiyor")
esit(bicim.kisa_ad("Koç Holding A.Ş."), "Koç Holding",
     "'Holding' gunluk adin parcasi, atilmiyor")
esit(bicim.kisa_ad("A.Ş."), "A.Ş.", "her sey atilirsa unvan geri veriliyor")
esit(bicim.kisa_ad("Aselsan"), "Aselsan", "tek sozcuklu unvan")

# ---------------------------------------------------------------- baslik
#
# Kaynaklarin bir kismi tiklama icin yazilmis baslik veriyor. Buradaki
# ornekler uretimde gorulen gercek basliklar.
print("\nBaslik sadelestirme")
# TURKCE HARFLERLE yaziliyor: ASCII "I" Turkce'de "ı"ya doner ve bu
# DOGRU davranistir. Testi ASCII'ye cevirince beklenen deger yanlis
# oluyor ("Benzıne"), yani test modulun asil isini olcmuyor.
esit(bicim.baslik_sadelestir(
        "BENZİNE NE KADAR, KAÇ TL ZAM GELECEK? Güncel akaryakıt fiyatları"),
     "Benzine Ne Kadar, Kaç TL Zam Gelecek? Güncel akaryakıt fiyatları",
     "bagiran bolum baslik bicimine cevriliyor")
esit(bicim.baslik_sadelestir("TUIK acikladi: enflasyon belli oldu!"),
     "TUIK acikladi: enflasyon belli oldu",
     "sondaki unlem kalkiyor")
esit(bicim.baslik_sadelestir("Altin aciklamasi! Dev banka rakam verdi"),
     "Altin aciklamasi. Dev banka rakam verdi",
     "cumle ortasindaki unlem NOKTAYA doner -- silinirse cumleler yapisir")

# KURUM ADI BOZULMAMALI. Bu iki kisaltma yan yana gelince "bagirma"
# sanilip "Garanti Bbva, Gmtn" uretilmisti.
esit(bicim.baslik_sadelestir(
        "Garanti BBVA, GMTN programinda 10 milyon USD tahvil ihraci"),
     "Garanti BBVA, GMTN programinda 10 milyon USD tahvil ihraci",
     "yan yana iki kisaltma bagirma sayilmaz")
esit(bicim.baslik_sadelestir("TCMB faiz kararini acikladi"),
     "TCMB faiz kararini acikladi", "normal baslik degismez")
esit(bicim.baslik_sadelestir("ABD Tarim Disi Istihdam Ne Zaman?"),
     "ABD Tarim Disi Istihdam Ne Zaman?", "baslik bicimi bagirma degildir")
esit(bicim.baslik_sadelestir(""), "", "bos baslik")
esit(bicim.bagiriyor("Normal bir Turkce baslik"), False, "bagirmiyor")
esit(bicim.bagiriyor("TURKIYE EKONOMISI BUYUDU"), True, "bagiriyor")


print("\n" + "=" * 60)
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
