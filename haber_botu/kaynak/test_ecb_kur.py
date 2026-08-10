"""ecb_kur.py testleri -- AGA CIKMAZ."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ecb_kur  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


# ECB'nin gercek bicimi. DIKKAT: `-hist-90d.xml` CIFT tirnak,
# `eurofxref-daily.xml` TEK tirnak kullaniyor. Regex ile ayristirmak bu
# yuzden guvenilmez -- ilk denemede 90 gunluk dosyadan SIFIR kayit
# okundu ve hicbir hata firlamadi. Iki bicim de test ediliyor.
CIFT = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
<Cube>
 <Cube time="2026-08-07">
  <Cube currency="USD" rate="1.1535"/><Cube currency="JPY" rate="182.64"/>
 </Cube>
 <Cube time="2026-08-06">
  <Cube currency="USD" rate="1.1542"/>
 </Cube>
</Cube></gesmes:Envelope>"""

TEK = CIFT.replace('"2026-08-07"', "'2026-08-07'").replace(
    '"USD"', "'USD'").replace('"1.1535"', "'1.1535'")

print("Iki tirnak bicimi de okunmali")
es("cift tirnak", ecb_kur.coz(CIFT), [("2026-08-07", 1.1535),
                                      ("2026-08-06", 1.1542)])
es("tek tirnak ilk kayit", ecb_kur.coz(TEK)[0], ("2026-08-07", 1.1535))

print("\nSinir durumlar")
es("bos gun listesi", ecb_kur.coz(
    '<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"'
    ' xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">'
    "<Cube></Cube></gesmes:Envelope>"), [])
es("olmayan para birimi", ecb_kur.coz(CIFT, para="XXX"), [])
# Bozuk oran ATLANIR, patlamaz: tek bir bozuk satir yuzunden gunun
# tamami kaybolmamali.
es("bozuk oran atlanir",
   ecb_kur.coz(CIFT.replace('rate="1.1535"', 'rate="bozuk"')),
   [("2026-08-06", 1.1542)])

print("\nSeri kodu FRED'inkinden AYRI olmali")
# Ikisi ayni buyuklugu olcuyor ama farkli kaynak ve farkli tarih
# tasiyor; tek koda yazmak hangi degerin nereden geldigini kaybettirir.
es("kod", ecb_kur.KOD, "ECB_EURUSD")

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
