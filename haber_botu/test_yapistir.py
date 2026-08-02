"""yapistir.py testleri -- sayi cozumleme ve kalem eslestirme.

Bu modulun hatalari SESSIZDIR: yanlis cozulen bir sayi hata firlatmaz,
sadece yanlis bilanco uretir. O yuzden sinir durumlar tek tek test edilir.

Calistirma:  python test_yapistir.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import yapistir  # noqa: E402

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


print("\nSayi cozumleme -- Turkce bicim")
esit(yapistir.sayi_coz("17.360.000.000"), 17360000000.0, "binlik nokta")
esit(yapistir.sayi_coz("1.234"), 1234.0, "uc haneli kuyruk = binlik")
esit(yapistir.sayi_coz("1.234,56"), 1234.56, "binlik nokta + ondalik virgul")
esit(yapistir.sayi_coz("12,5"), 12.5, "ondalik virgul")
esit(yapistir.sayi_coz("123"), 123.0, "duz sayi")

print("\nSayi cozumleme -- Ingilizce bicim")
esit(yapistir.sayi_coz("1,234,567"), 1234567.0, "binlik virgul")
esit(yapistir.sayi_coz("1,234.56"), 1234.56, "binlik virgul + ondalik nokta")

print("\nSayi cozumleme -- muhasebe isaretleri")
esit(yapistir.sayi_coz("(1.234)"), -1234.0, "parantez = negatif")
esit(yapistir.sayi_coz("-1.234"), -1234.0, "eksi isareti")
esit(yapistir.sayi_coz("(12.345,67)"), -12345.67, "parantez + ondalik")
esit(yapistir.sayi_coz(""), None, "bos deger None")
esit(yapistir.sayi_coz("-"), None, "cizgi None")
esit(yapistir.sayi_coz("n/a"), None, "metin None")

print("\nDeger olmayan parcalar temizleniyor")
esit(yapistir._satir_sayilari("Hasılat 2026/06 4.200 3.100"), [4200.0, 3100.0],
     "donem etiketi (2026/06) deger sayilmiyor")
esit(yapistir._satir_sayilari("Stoklar (Not 12) 2.024 1.870"), [2024.0, 1870.0],
     "dipnot numarasi ayikaniyor, 2.024 MESRU deger olarak kaliyor")
esit(yapistir._satir_sayilari("Ticari Alacaklar 31.12.2025 5.100"), [5100.0],
     "tam tarih deger sayilmiyor")

print("\nKalem eslestirme -- en uzun eslesme kazanir")
esit(yapistir._kalem_ara(yapistir.katla("Kısa Vadeli Ticari Alacaklar")),
     "ticari_alacaklar", "ozgul ad genel adi ezmiyor")
esit(yapistir._kalem_ara(yapistir.katla("TOPLAM VARLIKLAR")), "aktif_toplami",
     "buyuk harf")
esit(yapistir._kalem_ara(yapistir.katla("Brut Kar")), "brut_kar",
     "DIAKRITIKSIZ yazim -- kaynaklar boyle yaziyor")
esit(yapistir._kalem_ara(yapistir.katla("Brüt Kâr")), "brut_kar", "sapkali yazim")
esit(yapistir._kalem_ara(yapistir.katla("Ana Ortaklığa Ait Özkaynaklar")),
     "ozkaynak", "uzun ozkaynak adi")
esit(yapistir._kalem_ara(yapistir.katla("Rastgele bir satır")), None,
     "eslesmeyen satir None")

print("\nTam tablo ayristirma")
TABLO = """\
ÖZET FİNANSAL TABLOLAR (Bin TL)
                                      2026/06        2025/06
Hasılat                             4.200.000      3.100.000
Brüt Kâr                              980.000        810.000
Esas Faaliyet Karı                    520.000        470.000
FAVÖK                                 690.000        600.000
Dönem Karı                            310.000        260.000
TOPLAM VARLIKLAR                    9.800.000      7.400.000
Toplam Özkaynaklar                  4.100.000      3.500.000
Dönen Varlıklar                     3.200.000      2.600.000
Kısa Vadeli Yükümlülükler           2.400.000      1.900.000
Kısa Vadeli Ticari Alacaklar        1.150.000        820.000
Stoklar                               760.000        590.000
Finansal Borçlar                    2.900.000      2.100.000
Nakit ve Nakit Benzerleri             640.000        520.000
İşletme Faaliyetlerinden Nakit Akışları  430.000     510.000
Finansman Giderleri                   280.000        190.000
"""

olcek, aciklama = yapistir.olcek_sez(TABLO)
esit(olcek, 1000, f"olcek basliktan sezildi: {aciklama}")

simdi, once, notlar = yapistir.ayristir(TABLO, olcek)
esit(simdi["hasilat"], 4_200_000_000.0, "hasilat bin TL ile carpildi")
esit(once["hasilat"], 3_100_000_000.0, "onceki donem ikinci sutundan")
esit(simdi["ticari_alacaklar"], 1_150_000_000.0, "kisa vadeli ticari alacaklar")
esit(simdi["stoklar"], 760_000_000.0, "stoklar")
esit(simdi["net_borc"], 2_260_000_000.0, "net borc = finansal borc - nakit")
esit(once["net_borc"], 1_580_000_000.0, "onceki net borc de hesaplandi")
esit("_finansal_borc" in simdi, False, "ara alanlar temizlendi")
esit(simdi["faaliyet_nakit_akisi"], 430_000_000.0, "nakit akisi")
esit("yatirim_harcamasi" in simdi, False, "tabloda yok -> UYDURULMADI")

print("\n" + "=" * 62)
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
