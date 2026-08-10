"""denetim.py siniflandirma ve yayin karari testleri -- AGA CIKMAZ.

Yayin karari dagitimi durduran seydir (`calistir.py` hata gorunce
yayimlamiyor). Bu yuzden esiklerinin sessizce kaymasi, bozuk icerigin
yayimlanmasi demek.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import denetim  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def B(alan, agirlik="uyari"):
    return denetim.Bulgu(agirlik, alan, "kod", "mesaj")


# ------------------------------------------------------------------
# SINIFLANDIRMA -- promptun 15. maddesi.
# ------------------------------------------------------------------
print("Siniflandirma -- alan simgeye cevriliyor")
es("etiket hatasi kritik", denetim.sinif(B("etiket", "hata")), "🔴")
es("gorsel uyarisi", denetim.sinif(B("gorsel")), "🟣")
es("ai uyarisi", denetim.sinif(B("ai")), "🟠")
es("editoryal uyari", denetim.sinif(B("editoryal")), "🔵")
es("tekrar uyarisi", denetim.sinif(B("tekrar")), "⚪")
es("veri uyarisi", denetim.sinif(B("veri")), "🟡")

# AGIRLIK SINIFI YUKSELTIR. "Bayat veri" uyaridir ama "imkansiz deger"
# ayni alanda HATA agirligindadir ve kritik isaretlenmeli.
print("\nAgirlik sinifi yukseltiyor")
es("veri HATASI kritik olur", denetim.sinif(B("veri", "hata")), "🔴")
es("aralik HATASI kritik olur", denetim.sinif(B("aralik", "hata")), "🔴")
# Gorsel ve AI kendi simgesini KORUYOR: onlar zaten ayri sinif ve
# "kritik" demek hangi turden hata oldugunu kaybettirirdi.
es("gorsel HATASI simgesini korur", denetim.sinif(B("gorsel", "hata")), "🟣")

print("\nBilinmeyen alan sessizce dusmuyor")
es("bilinmeyen alan editoryal sayilir", denetim.sinif(B("yeni_alan")), "🔵")

# ------------------------------------------------------------------
# YAYIN KARARI -- promptun 19. maddesi, uc seviye.
# ------------------------------------------------------------------
print("\nYayin karari uc seviye")
es("bulgu yoksa hazir", denetim.yayin_karari([], [])[0], "🟢")
es("yalniz uyari varsa sarti", denetim.yayin_karari([], [B("gorsel")])[0], "🟡")
es("hata varsa uygun degil",
   denetim.yayin_karari([B("etiket", "hata")], [])[0], "🔴")
es("hata uyariyi bastirir",
   denetim.yayin_karari([B("etiket", "hata")], [B("gorsel")])[0], "🔴")
es("karar metni", denetim.yayin_karari([], [])[1], "YAYINA HAZIR")

# ------------------------------------------------------------------
# HER SINIF ALANI RAPORDA BIR BOLUME DUSMELI. Bir alan hicbir bolume
# dusmezse bulgu uretilir ama raporun ust ozetinde GORUNMEZ.
# ------------------------------------------------------------------
print("\nHer alan raporda bir bolume dusuyor")
rapor_alanlari = {k for _ad, kodlar, _i, _k in denetim.RAPOR_ALANLARI
                  for k in kodlar}
for alan in denetim.SINIFLAR:
    es(f"'{alan}' raporda", alan in rapor_alanlari, True)

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
