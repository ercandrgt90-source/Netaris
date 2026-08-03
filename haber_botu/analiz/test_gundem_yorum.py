"""gundem_yorum.py testleri -- hangi haber yorumlanir, hangi metinle.

Iki tur sessiz hata var:

  1. Isaret diakritikli yazilirsa HICBIR ZAMAN eslesmez. Haber rutin
     sayilir, sayfasi uretilmez, kimse fark etmez -- TCMB'nin 16
     duyurusunun 16'si bir sure boyle gorunmez kaldi.
  2. Yerli kurum yabanci baglam metnini alirsa cikan yazi YANLIS olur:
     TCMB karari "gelismekte olan ulkelere referans olusturur" diye
     anlatilir. Kod calisir, test yoksa fark edilmez.

Calistirma:  python analiz/test_gundem_yorum.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import gundem_yorum as gy  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


def yorumlanir(baslik: str, konu: str, kurum: str = "",
               ticari: bool = False) -> bool:
    return gy.siniflandir(baslik, konu, kurum, ticari).yorumlanir


print("\nTCMB -- yorumlanmasi GEREKENLER")
esit(yorumlanir("Para Politikası Kurulu Toplantı Özeti (2026-32)",
                "Para politikası", "TCMB"), True, "PPK toplanti ozeti")
esit(yorumlanir("Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
                "Para politikası", "TCMB"), True, "faiz karari")
esit(yorumlanir("Aylık Fiyat Gelişmeleri (Haziran 2026)",
                "Enflasyon", "TCMB"), True, "fiyat gelismeleri")
esit(yorumlanir("Sektörel Enflasyon Beklentileri (Temmuz 2026)",
                "Enflasyon", "TCMB"), True, "enflasyon beklentileri")
esit(yorumlanir("Hanehalkı Beklenti Anketi (Temmuz 2026)",
                "Para politikası", "TCMB"), True, "beklenti anketi")
esit(yorumlanir("Ödemeler Dengesi İstatistikleri",
                "Bankacılık", "TCMB"), True, "odemeler dengesi")
esit(yorumlanir("Finansal İstikrar Raporu (Mayıs 2026)",
                "Bankacılık", "TCMB"), True, "finansal istikrar raporu")

print("\nTCMB -- rutin sayilmasi GEREKENLER")
esit(yorumlanir("Haftalık Akım Faiz ve Kâr Payı İstatistikleri",
                "Para politikası", "TCMB"), False,
     "haftalik veri -- 'faiz' gecse de rutin")
esit(yorumlanir("Haftalık Para ve Banka İstatistikleri",
                "Bankacılık", "TCMB"), False, "haftalik banka verisi")
esit(yorumlanir("Dijital Türk Lirası Projesi Ekosistemine Katılım Çağrısı",
                "Para politikası", "TCMB"), False, "katilim cagrisi")
esit(yorumlanir("Menkul Kıymet İstatistikleri",
                "Piyasa düzenlemesi", "TCMB"), False, "rutin istatistik")
esit(yorumlanir("Veri Yayımlama Takvimi 2027",
                "Para politikası", "TCMB"), False, "takvim duyurusu")

print("\nYabanci kaynaklar bozulmadi")
esit(yorumlanir("Federal Reserve issues FOMC statement",
                "Para politikası", "Fed"), True, "FOMC bildirisi")
esit(yorumlanir("Federal Reserve Board requests comment on a rule",
                "Bankacılık", "Fed"), False, "gorus talebi rutin")
esit(yorumlanir("China's crude oil imports fell in the second quarter",
                "Enerji", "EIA"), True, "ham petrol ithalati")
esit(yorumlanir("SEC announces personnel appointment",
                "Piyasa düzenlemesi", "SEC"), False, "atama rutin")

print("\nRutin ONCE bakilir -- ortusen isaretler")
esit(yorumlanir("Requests comment on interest rate rule",
                "Para politikası", "Fed"), False,
     "hem 'requests comment' hem 'interest rate' -- rutin kazanir")

print("\nDiakritik -- katlanmis eslesme")
esit(yorumlanir("PARA POLİTİKASI KURULU KARARI",
                "Para politikası", "TCMB"), True, "buyuk harf + noktali I")
esit(yorumlanir("TÜFE Aylık Değişim", "Enflasyon", "TCMB"), True, "TUFE umlautlu")
esit(gy._katla("İSTANBUL Ğ Ş Ü Ö Ç I ı"), "istanbul g s u o c i i", "katlama tablosu")

print("\nYERLI vs YABANCI -- ayni konu, AYRI metin")
_y = gy.siniflandir("Faiz Oranlarına İlişkin Basın Duyurusu",
                    "Para politikası", "TCMB")
_d = gy.siniflandir("Federal Reserve issues FOMC statement",
                    "Para politikası", "Fed")
esit(_y.neden_onemli == _d.neden_onemli, False, "baglam metinleri ayri")
esit("TCMB" in _y.neden_onemli, True, "yerli metin TCMB'den soz eder")
esit("gelişmekte olan" in _y.neden_onemli, False,
     "yerli metin Turkiye'yi 'gelismekte olan ulke' diye ANLATMAZ")
esit(any("finansman gideri" in k for k in _y.kanallar), True,
     "yerli kanal sirket bilancosuna baglanir")
esit(_y.kanal_basligi, gy.BASLIK_YERLI, "yerli baslik")
esit(_d.kanal_basligi, gy.BASLIK_YABANCI, "yabanci baslik")
esit("geçer" in _d.kanal_basligi, True, "yabanci: Turkiye'ye GECER")
esit("geçer" in _y.kanal_basligi, False,
     "yerli: TCMB karari Turkiye'ye 'gecmez', burada alinir")

print("\nEnflasyon yerli baglami -- TMS 29 cift sayim uyarisi")
_e = gy.siniflandir("Aylık Fiyat Gelişmeleri", "Enflasyon", "TCMB")
esit(any("TMS 29" in k for k in _e.kanallar), True, "TMS 29 kanali var")
esit(any("çift sayım" in k for k in _e.kanallar), True,
     "duzeltilmis tabloyu tekrar aritmanin cift sayim oldugu yaziyor")

print("\nBaglam tabloları -- eksiksizlik")
for konu in gy.YERLI_BAGLAMI:
    esit(konu in gy.KONU_BAGLAMI, True, f"'{konu}' iki tabloda da var")
for konu, (neden, kanallar) in gy.YERLI_BAGLAMI.items():
    esit(bool(neden) and len(kanallar) >= 2, True,
         f"'{konu}' neden + en az 2 kanal")
esit(gy.siniflandir("Faiz kararı", "Bilinmeyen konu", "TCMB").yorumlanir,
     False, "tanimsiz konu yorumlanmaz")

print("\nTicari akis -- MAKRO konu + OLAY isareti")
esit(yorumlanir("SSK ve Bağ-Kur emeklilerinin Temmuz ayı zam oranı belli oldu",
                "İstihdam ve ücret", "Dünya", True), True,
     "kalip arama kacirmisti: 'emekliLERININ ... ZAM orani'")
esit(yorumlanir("Temmuz ayı dış ticaret rakamları açıklandı",
                "Dış ticaret", "AA", True), True, "veri duyurusu")
esit(yorumlanir("2027 memur ve emekli maaşı Ocak zammı şekilleniyor",
                "İstihdam ve ücret", "Ekonomist", True), True, "zam haberi")
esit(yorumlanir("Temmuzda fiyatı en çok artan ve azalan ürünler belli oldu",
                "Enflasyon", "TRT Haber", True), True, "fiyat verisi")

print("\nTicari akis -- sirket haberi RUTIN kalir")
esit(yorumlanir("Shell, Avrupa portföyünü TotalEnergies'e satıyor",
                "Enerji", "AA", True), False,
     "makro konu ama olay isareti yok -- tek sirketin islemi")
esit(yorumlanir("Flotek, Porto Riko'da 400 milyon dolarlık sözleşme imzaladı",
                "Enerji", "Ekonomist", True), False, "sozlesme haberi")
esit(yorumlanir("Çelebi Havacılık portföyüne THY'yi dahil etti",
                "Şirket haberleri", "Ekonomim", True), False,
     "Sirket haberleri makro konu DEGIL")

print("\nOlay isaretlerinde bosluk tuzagi")
esit(gy._icerir("Bu zaman diliminde", (" zam ",)), False,
     "'ZAMan' icinde ' zam ' eslesmemeli")
esit(gy._icerir("Zam geldi", (" zam ",)), True,
     "baslikta ILK kelime olsa da eslesir -- metin bosluklarla paylaniyor")
esit(gy._icerir("Kirada zam oranı", (" zam ",)), True, "gercek 'zam' eslesir")
esit(gy._icerir("Karar verildi", (" veri ",)), False,
     "'VERIldi' icinde ' veri ' eslesmemeli")

print("\nIsaretler katlanmis yazilmis olmali")
for i in gy.RUTIN_ISARETLER + gy.ETKILI_ISARETLER:
    if gy._katla(i) != i:
        esit(gy._katla(i), i, f"isaret diakritikli: {i!r}")
esit(all(gy._katla(i) == i for i in
         gy.RUTIN_ISARETLER + gy.ETKILI_ISARETLER + gy.OLAY_ISARETLERI),
     True, "butun isaretler ASCII -- yoksa hic eslesmezler")

print("\nMAKRO_KONULAR baglam tablosunda karsiligi olmali")
for _k in gy.MAKRO_KONULAR:
    esit(_k in gy.KONU_BAGLAMI, True, f"'{_k}' baglami var")
esit("Şirket haberleri" in gy.MAKRO_KONULAR, False,
     "tek sirket haberi makro kanal anlatmayi hak etmez")
esit("Düzenleme" in gy.MAKRO_KONULAR, False, "idari islem makro degil")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
