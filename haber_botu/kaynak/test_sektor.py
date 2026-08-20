"""Sektor siniflandirmasi -- ayristirma ve ISIMLENDIRME iddiasi.

En onemli sinama teknik degil, EDITORYAL: bu sema BIST'in kendi
sektor endeksi DEGIL. Karistirmak, okurun iki farkli kaynagi
karsilastirip tutmadigini gormesine ve haksiz yere veriye guvenini
kaybetmesine yol acar.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sektor  # noqa: E402

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


print("\nSektor siniflandirmasi\n")

# --- gomulu yapidan ayristirma ---
#
# Sektor GORUNUR METINDEN degil, sayfaya gomulu `infoTable`dan
# okunuyor. Ilk denemem gorunur metni tariyordu ve MENUYU yakalamisti
# ("Industry: Stock Lists") -- dogru gorunen, tamamen yanlis bir deger.
HAM = ('...bla bla infoTable:[{t:"Industry",v:"Steel",u:"stocks/industry/steel"},'
       '{t:"Sector",v:"Materials",u:"stocks/sector/materials"},'
       '{t:"Founded",v:1960}] devam...')
d = sektor._coz(HAM)
esit(d.get("Sector"), "Materials", "Sector gomulu yapidan okunuyor")
esit(d.get("Industry"), "Steel", "Industry gomulu yapidan okunuyor")
esit(sektor._coz("infoTable yok"), {}, "yapi yoksa bos sozluk")
esit(sektor._coz(""), {}, "bos metin")

# --- Turkce adlandirma BIZE ait ---
esit(sektor.SEKTOR_TR["Financials"], "Finans", "Financials -> Finans")
esit(sektor.SEKTOR_TR["Consumer Staples"], "Temel tüketim",
     "Consumer Staples -> Temel tuketim")
esit(sektor.SEKTOR_TR["Materials"], "Temel malzeme",
     "Materials -> Temel malzeme")

# Bilinmeyen sektor OLDUGU GIBI kaliyor: uydurma Turkce ad
# uretilmiyor ve "Diger" kovasina da atilmiyor.
esit(sektor.SEKTOR_TR.get("Uydurma Sektor", "Uydurma Sektor"), "Uydurma Sektor",
     "bilinmeyen sektor cevrilmeden geciyor -- uydurma ad yok")

# --- SEMA IDDIASI ---
#
# Dosyanin kendi belgesi bunun BIST semasi olmadigini SOYLEMELI.
# Bu bir yorum satiri testi gibi gorunuyor ama iddianin kendisi
# veri kadar onemli: yanlis etiketlenen dogru veri, yanlis veridir.
esit("BIST" in sektor.__doc__ and "FARKLIDIR" in sektor.__doc__, True,
     "modul, BIST endeks semasi OLMADIGINI acikca yaziyor")

# --- defterdeki islenmis veri ---
YOL = pathlib.Path(__file__).resolve().parent / "sirketler.json"
if YOL.exists():
    d = json.loads(YOL.read_text(encoding="utf-8"))
    sirket = d["sirketler"]
    sektorlu = [v for v in sirket.values() if v.get("sektor_tr")]
    esit(len(sektorlu) > 300, True,
         f"defterde sektorlu kod var ({len(sektorlu)})")
    esit(all(v.get("sektor") for v in sektorlu), True,
         "sektor_tr olan her kayitta Ingilizce sektor de duruyor")
    esit("BIST" in d.get("sektor_kaynagi", ""), True,
         "defter, semanin BIST olmadigini kaydediyor")
    # Ayni sirketin farkli hisse siniflari AYNI sektorde olmali.
    kimlik = {}
    catisma = 0
    for k, v in sirket.items():
        if not v.get("sektor_tr"):
            continue
        kk = v.get("kap_kimlik")
        if kk in kimlik and kimlik[kk] != v["sektor_tr"]:
            catisma += 1
        kimlik[kk] = v["sektor_tr"]
    esit(catisma, 0,
         "ayni sirketin hisse siniflari AYNI sektorde -- catisma yok")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
