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

# --------------------------------------------------------------------
# KONSENSUS AYRISTIRMASI -- sabit ornekle, AGA CIKMADAN.
#
# Bu kaynak HIZ SINIRLI (429). Testi aga bagLAMAK, testin kaynagin
# yukune gore rastgele kirilmasi demekti.
# --------------------------------------------------------------------
_ORNEK = """<?xml version="1.0" encoding="windows-1252"?>
<weeklyevents>
 <event>
  <title>Non-Farm Employment Change</title>
  <country>USD</country>
  <date><![CDATA[08-07-2026]]></date>
  <time><![CDATA[12:30pm]]></time>
  <impact><![CDATA[High]]></impact>
  <forecast><![CDATA[85K]]></forecast>
  <previous><![CDATA[57K]]></previous>
 </event>
 <event>
  <title>Unemployment Rate</title>
  <country>CAD</country>
  <date><![CDATA[08-07-2026]]></date>
  <time><![CDATA[12:30pm]]></time>
  <impact><![CDATA[High]]></impact>
  <forecast><![CDATA[6.5%]]></forecast>
  <previous><![CDATA[6.5%]]></previous>
 </event>
 <event>
  <title>OPEC-JMMC Meetings</title>
  <country>All</country>
  <date><![CDATA[08-03-2026]]></date>
  <time><![CDATA[All Day]]></time>
  <impact><![CDATA[Low]]></impact>
  <forecast></forecast>
  <previous></previous>
 </event>
</weeklyevents>"""


class _SahteIstemci:
    """Aga cikmayan istemci. `_ff_indir` yerine dogrudan XML veriyor."""
    def get(self, adres):
        raise AssertionError("test aga cikmamali")


_eski = Y._ff_indir
Y._ff_indir = lambda c: _ORNEK
try:
    _ff = Y.ff_cek(_SahteIstemci())
finally:
    Y._ff_indir = _eski

es("yalnizca eslesen olay aliniyor", len(_ff), 1)
_n = _ff[0]
es("konsensus okunuyor", _n.beklenti, "85K")
es("onceki deger okunuyor", _n.onceki, "57K")
es("seriye baglaniyor", _n.kod, "PAYEMS")
es("kaynak yaziliyor", _n.kaynak, "ForexFactory")
# 12:30pm UTC -> Turkiye 15:30
es("FF saati UTC sayiliyor", _n.yerel.hour, 15)
es("FF dakikasi", _n.yerel.minute, 30)

# ULKE AYRIMI SART: "Unemployment Rate" hem ABD hem Kanada'da var.
# Ulke kontrol edilmeseydi Kanada verisi ABD serisine baglanirdi.
dogru("Kanada verisi ABD serisine baglanmiyor",
      all(x.ulke != "ABD" or x.kod != "UNRATE" for x in _ff))

es("saatsiz kayit cozulur",
   Y._ff_an("08-03-2026", "All Day").hour, 0)
es("ogleden sonra saati", Y._ff_an("08-07-2026", "2:00pm").hour, 14)
es("oglen 12 saati", Y._ff_an("08-07-2026", "12:30pm").hour, 12)
es("gece yarisi 12", Y._ff_an("08-07-2026", "12:30am").hour, 0)
es("bozuk tarih None", Y._ff_an("abc", "12:30pm"), None)


print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  X", k)
sys.exit(1 if kaldi else 0)
