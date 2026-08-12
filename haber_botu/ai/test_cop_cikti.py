"""Cop cikti eleyicisi -- yorum OLMAYAN metni tanir mi?

Bu sinamanin her maddesi olculmus bir arizadan ya da onun yakin
akrabasindan geliyor. En onemlisi YANLIS POZITIF olmamasi: saglam bir
yorumu elemek, cop yayimlamak kadar kotu.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cop_cikti  # noqa: E402

_gecti = 0
_kaldi = 0


def red(metin, aciklama):
    global _gecti, _kaldi
    s = cop_cikti.sebep(metin)
    if s:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama} -- ELENMEDI")


def temiz(metin, aciklama):
    global _gecti, _kaldi
    s = cop_cikti.sebep(metin)
    if not s:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama} -- YANLIS POZITIF: {s}")


print("\nCop cikti eleyicisi\n")

# --- GERCEKTE YAYIMLANAN METIN ---
YAYIMLANAN = (
    'analysis 0️⃣\n\nWe need to produce a " news release ( Basın Duyuru )" '
    'about inflation rates etc. The user wants a news release '
    "Haber: Fa Fa Or Or Or Or Or Or Or Or Or Or Or Or Or Or Or Or Or")
red(YAYIMLANAN, "yayimlanan bozuk metin eleniyor")

# --- dusunme kanali ---
red("analysis Bu haberde enflasyon...", "'analysis' oneki")
red("assistantfinal Enflasyon geriledi.", "'assistantfinal' oneki")
red("<|channel|>final<|message|>Enflasyon geriledi.", "harmony isaretleri")

# --- istem yankisi ---
red("We need to produce a short comment.", "'we need to'")
red("The user wants a summary of the data.", "'the user wants'")
red("Here is a short comment about inflation.", "'here is a'")

# --- bozulma ---
red("Enflasyon Or Or Or Or Or Or geriledi.", "bes kez tekrarlanan hece")
red("veri veri veri veri veri veri", "tekrarlanan sozcuk")

# --- dil ---
red("Inflation eased to 31.75 percent in July, which reduces the pressure "
    "on household budgets and supports real income recovery over time.",
    "uzun Ingilizce metin (Turkce harf yok)")

# --- YANLIS POZITIF OLMAMALI ---
temiz("Enflasyon %31,75 seviyesine geriledi; bu gelişme hanehalkı "
      "bütçesinde reel gelir üzerinden hissedilir.",
      "saglam Turkce yorum")
temiz("Fed faizi 25 baz puan indirdi.",
      "kisa cumle, Turkce ozel harf YOK -- elenmemeli")
temiz("", "bos metin (baska denetim ilgilenir)")
temiz("TCMB politika faizini sabit tuttu; karar piyasa beklentisiyle "
      "uyumlu olduğu için kurda sert bir tepki görülmedi.",
      "iki cumlelik saglam yorum")
# "final" sozcugu METIN ICINDE gecebilir -- yalnizca BASTA kanal isareti.
temiz("Küresel piyasalarda final rakamlar açıklandıktan sonra "
      "oynaklık geriledi ve işlem hacmi normale döndü.",
      "'final' sozcugu metin ORTASINDA -- kanal isareti degil")
# Ayni sozcugun uc kez gecmesi dogal olabilir.
temiz("Veri, veri kalitesi ve veri kaynağı ayrı konulardır; üçü de "
      "raporda ayrı başlıklarda ele alınmıştır.",
      "ayni sozcuk uc kez, dongu DEGIL")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
