"""yayin_takvimi.py testleri -- AG'A CIKMAZ.

Takvimin hatalari sessizdir: yanlis saat "yanlis saat" diye gorunmez,
yalnizca okur veriyi kacirir. En pahali hatalar zaman dilimi
donusumunde ve ayristirmada oldugu icin ikisi de burada sabitleniyor.
"""

import sys
import pathlib
from datetime import datetime, timezone

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import yayin_takvimi as Y  # noqa: E402

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
# ZAMAN DILIMI -- en pahali hata burada.
#
# BLS saati US-Eastern veriyor. Ham degeri UTC saymak, TUFE'yi sayfada
# dort saat erken gosterirdi.
# --------------------------------------------------------------------
yaz = Y._ics_an("20260812T083000")      # 12 Agustos, yaz saati (EDT)
es("yaz saati UTC'ye cevriliyor", yaz.astimezone(timezone.utc).hour, 12)
es("yaz saati Turkiye'de 15:30", yaz.astimezone(Y._TR).hour, 15)

kis = Y._ics_an("20260115T083000")      # 15 Ocak, kis saati (EST)
es("kis saati UTC'ye cevriliyor", kis.astimezone(timezone.utc).hour, 13)
es("kis saati Turkiye'de 16:30", kis.astimezone(Y._TR).hour, 16)

# Yaz ve kis AYNI yerel saatte farkli UTC anlari uretmeli; uretmiyorsa
# saat dilimi hic uygulanmiyordur.
dogru("yaz ve kis farkli UTC ofseti",
      yaz.astimezone(timezone.utc).hour != kis.astimezone(timezone.utc).hour)

# Zulu damgasi oldugu gibi kalir.
z = Y._ics_an("20260812T083000Z")
es("Z damgasi cevrilmez", z.astimezone(timezone.utc).hour, 8)

# Saatsiz kayit cokmemeli.
dogru("saatsiz kayit cozulur", Y._ics_an("20260812") is not None)
# Bozuk kayit None doner, patlamaz.
es("bozuk damga None", Y._ics_an("abc"), None)
es("bos damga None", Y._ics_an(""), None)

# --------------------------------------------------------------------
# BLS ESLEME
# --------------------------------------------------------------------
kod, ad, onem = Y._bls_esle("Employment Situation")
es("istihdam raporu seriye baglanir", kod, "PAYEMS")
es("istihdam raporu yuksek onem", onem, 3)

kod, ad, onem = Y._bls_esle("Consumer Price Index")
es("TUFE seriye baglanir", kod, "CPIAUCSL")
es("TUFE Turkce adlanir", ad, "ABD TÜFE")

# Eslesmeyen yayin DUSMEZ, dusuk onemle gecer: bilmedigimiz bir yayini
# atmak, takvimde delik birakmak olurdu.
kod, ad, onem = Y._bls_esle("Some Unknown Release 2026")
es("bilinmeyen yayin dusuk onem", onem, Y.BLS_VARSAYILAN_ONEM)
es("bilinmeyen yayin ozgun adiyla kalir", ad, "Some Unknown Release 2026")

# --------------------------------------------------------------------
# YERLI RITIM -- turetilmis, `kesin=False` olmali.
# --------------------------------------------------------------------
b = datetime(2026, 8, 7, 12, 0, tzinfo=Y._TR)
yerli = Y.yerli_uret(b, ay_sayisi=1)
dogru("yerli yayin uretiliyor", len(yerli) > 0)
dogru("yerli yayinlarin hicbiri KESIN degil",
      all(not y.kesin for y in yerli))
dogru("yerli yayinlar TR", all(y.ulke == "TR" for y in yerli))
# Hafta sonuna denk gelen yayin is gunune otelenmeli.
dogru("hafta sonuna yayin konmuyor",
      all(y.yerel.weekday() < 5 for y in yerli))
# Her seri kodu gercekten tanimli olmali -- uydurma kod, sayfada
# "onceki deger" bulunamamasi demek.
dogru("yerli kodlar bos degil", all(y.kod for y in yerli))

# --------------------------------------------------------------------
# Yayin nesnesi
# --------------------------------------------------------------------
y = Y.Yayin(kod="X", ad="Test", ad_kaynak="Test", ulke="ABD", onem=2,
            kesin=True,
            an=datetime(2026, 8, 12, 12, 30, tzinfo=timezone.utc))
es("yerel saat Turkiye", y.yerel.hour, 15)

print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  X", k)
sys.exit(1 if kaldi else 0)
