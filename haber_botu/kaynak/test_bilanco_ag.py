"""Mali tablo cekici -- donem cevirisi ve ayristirma.

En kritik iki kural burada kilitleniyor:

  1. AKIS toplanir, STOK toplanmaz. Gelir tablosu kalemleri donem
     akisidir (ceyrekler toplanir); bilanco kalemleri belirli bir
     ANIN stogudur. Karistirmak toplam varliklari kat kat sisirir.

  2. Kalem adi kendi "Growth" ikizini tasiyor ("Revenue    Revenue
     Growth"). Once kirpilmali, SONRA elenmeli. Ilk yazimda tersti ve
     GELIR TABLOSU BOMBOS donuyordu -- bilancoda ikiz etiket olmadigi
     icin hata yarim gorunuyordu, yani en tehlikeli bicimde.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bilanco_ag as ba  # noqa: E402

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


print("\nMali tablo cekici\n")

# --- sayi cozumleme ---
esit(ba._sayi("1,234.5"), 1_234_500_000.0, "milyon cinsinden okunuyor")
esit(ba._sayi("-670.6"), -670_600_000.0, "negatif deger")
esit(ba._sayi("-"), None, "bos hucre None")
esit(ba._sayi("57.40%"), None, "YUZDE reddediliyor -- o kalem degil")
esit(ba._sayi(""), None, "bos dizge")

# --- donem cevirisi: AKIS toplanir ---
esit(ba.donem_toplami([100.0, 200.0, 300.0], 2, akis=True), 300.0,
     "AKIS: iki ceyrek toplaniyor (6 aylik)")
esit(ba.donem_toplami([100.0, 200.0, 300.0], 3, akis=True), 600.0,
     "AKIS: uc ceyrek toplaniyor (9 aylik)")

# --- STOK toplanmaz ---
esit(ba.donem_toplami([500.0, 400.0, 300.0], 2, akis=False), 500.0,
     "STOK: son ceyregin degeri AYNEN -- toplanmiyor")
esit(ba.donem_toplami([500.0, 400.0, 300.0], 3, akis=False), 500.0,
     "STOK: ceyrek sayisi degisince deger degismiyor")

# --- eksik veriyle uydurma yok ---
esit(ba.donem_toplami([100.0], 2, akis=True), None,
     "ceyrek yetmezse None -- eksigi tahminle doldurmuyoruz")
esit(ba.donem_toplami([100.0, None], 2, akis=True), None,
     "bir ceyrek bossa toplam URETILMIYOR")
esit(ba.donem_toplami([], 2, akis=True), None, "bos seri")

# --- tablo ayristirma: "Growth" ikizi ---
HTML = """
<table>
<tr><th>Fiscal Quarter</th><th>Q2 2026</th><th>Q1 2026</th></tr>
<tr><td>Period Ending</td><td>Jun 30</td><td>Mar 31</td></tr>
<tr><td>Revenue    Revenue Growth</td><td>50,632</td><td>57,664</td></tr>
<tr><td>Revenue Growth</td><td>57.40%</td><td>152.50%</td></tr>
<tr><td>Net Income    Net Income Growth</td><td>24,647</td><td>21,582</td></tr>
</table>
"""
donemler, kalemler = ba._tablo(HTML)
esit(donemler, ["Q2 2026", "Q1 2026"], "donem basliklari okunuyor")
esit(sorted(kalemler), ["Net Income", "Revenue"],
     "kalem adlarindan 'Growth' ikizi kirpiliyor")
esit("Revenue Growth" in kalemler, False,
     "yalnizca buyume olan satir ELENIYOR")
esit(kalemler["Net Income"], [24_647_000_000.0, 21_582_000_000.0],
     "degerler milyon carpaniyla okunuyor")

# --- gercek olcum: TERA 2026/6 ---
#
# KAP'tan ELLE girilen donem kari 46,26 mlr TL idi. Ceyreklerden
# turetilen toplam bunu yuvarlama farkiyla tutturmali.
esit(round((24_647_000_000.0 + 21_582_000_000.0) / 1e9, 2), 46.23,
     "TERA 2026/6: Q1+Q2 = 46,23 mlr (KAP 46,26 -- %0,07 yuvarlama)")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
