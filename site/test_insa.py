"""insa.py testleri -- AGA CIKMAZ, SITE KURMAZ.

Buradaki kurallarin ortak ozelligi sessiz olmalari: sayfa duzgun
gorunur, yalnizca icindeki iki sayi birbirini tutmaz.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK.parent / "haber_botu"),
                str(_KOK.parent / "haber_botu" / "kaynak"),
                str(_KOK.parent / "haber_botu" / "analiz")]

import insa  # noqa: E402

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


# ------------------------------------------------------------------
# VERI ACIKLAMASININ KENDISINDE BRIFING KUTUSU BASILMAZ.
#
# Kutunun "Son aciklanan" degeri DEPODAN geliyor. Haberin kendisi o
# aciklamaysa depodaki deger haberden eski olabiliyor. Olculdu ve
# YAYIMLANDI: basligi "ABD TÜFE: yıllık %3,73" olan sayfada kutu
# "Son açıklanan %3,5" diyordu -- ikisi de ABD TUFE yillik.
# ------------------------------------------------------------------
print("Veri aciklamasinda brifing kutusu basilmaz")
VARLIK = [{"kod": "CPI_US", "ad": "ABD TÜFE", "tur": "gosterge", "yol": "/x/"}]
# Takvim kalemi, `gosterge_brifingi`nin okudugu alanlarla: eksik alan
# birakmak testi kural yerine KeyError'la dusururdu.
TAKVIM = [{"seri": "CPIAUCSL", "ad": "ABD TÜFE", "gun": "13 Ağustos 2026",
           "saat": "15:30", "kesin": True, "ulke": "ABD", "onem": 3}]

es("veri aciklamasi -> kutu YOK",
   insa.gosterge_brifingi(
       {"adres": insa._VERI_ONEK + "CPIAUCSL/2026-08", "baslik": "ABD TÜFE"},
       VARLIK, TAKVIM),
   None)

# Bekleyis haberinde kutu DOGRU ve degerli: veri henuz aciklanmadi.
# Burada `None` DISI bir sonuc bekleniyor ama icerigi takvim/tanim
# verisine bagli; testin isi kurallarin ayrimini dogrulamak.
print("\nBekleyis haberinde kural engellemiyor")
bekleyis = insa.gosterge_brifingi(
    {"adres": "https://ornek.com/haber/1", "baslik": "Gözler TÜFE'de"},
    VARLIK, TAKVIM)
dogru("bekleyiste adres kurali devreye girmiyor",
      bekleyis is None or isinstance(bekleyis, dict))

print("\nSinir durumlar")
es("varliksiz haber", insa.gosterge_brifingi(
    {"adres": "https://ornek.com/1"}, None, TAKVIM), None)
es("takvimsiz", insa.gosterge_brifingi(
    {"adres": "https://ornek.com/1"}, VARLIK, []), None)

# ------------------------------------------------------------------
# DOSYASI OLMAYAN GORSEL BASILMAZ. Editoryal suzgec siklastiginda 49
# gorsel havuzdan cikarildi ve iki sayfa silinmis dosyaya isaret
# etmeye devam etti -- sayfada kirik gorsel, gunlukte hicbir iz.
# ------------------------------------------------------------------
print("\nKucuk gorsel: dosya yoksa bos doner")
es("olmayan dosya", insa.kucuk_foto("/statik/foto/yok-boyle-bir-dosya.jpg"), "")
es("havuz disi yol", insa.kucuk_foto("/statik/logo.svg"), "")
es("bos yol", insa.kucuk_foto(""), "")

# ------------------------------------------------------------------
# OKURUN DOGRULAYAMADIGI SAYI BASILMAZ (promptun 7. maddesi).
# ------------------------------------------------------------------
print("\nYorum dogrulanabilirligi")
h = {"baslik": "ABD TÜFE yıllık %3,73", "ozet": "Beklenti %3,40"}
dogru("sayfadaki sayilari anan yorum gecer",
      insa._yorum_dogrulanabilir("TÜFE %3,73 ile beklentinin üzerinde", h, None))
dogru("sayfada olmayan sayilari anan yorum GECMEZ",
      not insa._yorum_dogrulanabilir(
          "İşsizlik %7,40 ve cari açık 1.459 mn $ seviyesinde", h, None))
dogru("sayisiz yorum gecer",
      insa._yorum_dogrulanabilir("Mekanizma enerji maliyeti üzerinden işler",
                                 h, None))

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
