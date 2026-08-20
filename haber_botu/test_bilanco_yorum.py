"""Bilanco AI yorumu -- GIRDI ve yonerge.

Model cikisi burada sinanmiyor (o `ai/yorumcu` ve `cop_cikti`
tarafindan dogrulaniyor). Sinanan sey MODELE NE VERDIGIMIZ: yanlis
bicimli ya da yargi tasiyan bir girdi, yargi tasiyan cikti uretir.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bilanco_yorum as by  # noqa: E402

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


print("\nBilanco AI yorumu -- girdi\n")

# --- YUZDE BICIMI ---
# Ilk yazimda "%-0,7" cikiyordu; dogrusu "-%0,7".
esit(by._yuzde(-0.7), "-%0,7", "eksi YUZDE ISARETINDEN once")
esit(by._yuzde(5.4), "%5,4", "pozitif yuzde")
esit(by._yuzde(0.0), "%0,0", "sifir")


class D:
    hasilat = 13_670_000_000.0
    net_kar = -100_000_000.0
    ozkaynak = 28_530_000_000.0
    brut_kar = None
    faaliyet_kari = None
    favok = None
    aktif_toplami = None
    net_borc = None
    faaliyet_nakit_akisi = None
    yatirim_harcamasi = None


g = by.girdi_kur("AKCNS", "AKÇANSA A.Ş.", "Temel malzeme", "2026/6",
                 simdi=D(), oranlar_kendi={"net_marj": -0.7},
                 medyanlar={"net_marj": -2.8}, sirket_sayisi=42)

esit("Hasılat: 13,67 milyar TL" in g, True, "kalem milyar TL cinsinden")
esit("Brüt kâr" in g, False,
     "OLMAYAN kalem girdiye GIRMIYOR -- model uydurmasin")
esit("-%0,7" in g, True, "negatif marj dogru bicimde")
esit("sektör medyanı -%2,8, 42 şirket" in g, True,
     "medyan OLCUM olarak veriliyor, kac sirkete dayandigi yaziyor")

# --- YONERGE YARGI YASAKLIYOR ---
#
# Medyana gore konum bir SIRALAMA; "daha iyi" bir YARGI. Hangi oranin
# yuksek olmasinin iyi oldugu is modeline gore degisir.
for s in ("İyi", "güçlü", "zayıf", "cazip", "riskli", "başarılı"):
    esit(s in by.SISTEM, True, f"yonerge {s!r} sozcugunu YASAKLIYOR")
esit("EN FAZLA 3 CÜMLE" in by.SISTEM, True, "uzunluk siniri yonergede")
esit("YALNIZCA sana verilen sayıları" in by.SISTEM, True,
     "model RAKAM BULMUYOR, verileni cumleye ceviriyor")

# Onceki donem verilirse DEGISIM de veriliyor -- model kendisi
# hesaplamasin diye. Hesap bizim, cumle onun.
class E:
    hasilat = 10_000_000_000.0
    net_kar = None
    ozkaynak = None
    brut_kar = None
    faaliyet_kari = None
    favok = None
    aktif_toplami = None
    net_borc = None
    faaliyet_nakit_akisi = None
    yatirim_harcamasi = None


g2 = by.girdi_kur("X", "X A.Ş.", "Sanayi", "2026/6", simdi=D(), once=E())
esit("önceki dönem 10,00 milyar TL" in g2, True,
     "onceki donem girdide -- model hesap yapmasin")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
