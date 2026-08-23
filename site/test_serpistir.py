"""Gun ici konu dagilimi -- ayni rozet ard arda yigilmasin.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): `/gundem/` sayfasinin "Piyasa etkisi olanlar"
bolumunde 35 kalemin 21'i jeopolitikti ve ILK ONUN DOKUZU ard arda
jeopolitikti. Ekran goruntusunde ust uste ayni iki rozet goruluyordu:

    JEOPOLITIK  FINANCIALJUICE
    JEOPOLITIK  FINANCIALJUICE
    JEOPOLITIK  FINANCIALJUICE
    ...

Okur bundan "bu site yalnizca jeopolitik yaziyor" sonucunu cikariyor.
Oysa ayni gun makro (7), emtia (6) ve para politikasi kalemleri de
vardi -- katlanma cizgisinin altinda.

Sebep icerikte degil SIRADAYDI: akis tarihe gore diziliyor, ayni gune
dusen kalemler toplayicinin yazma sirasinda kaliyor ve tek ajanstan
toplu gelen haberler dogal olarak yan yana duruyor.

NE KORUNUYOR -- VE NEDEN BU DOGRU
---------------------------------
Kronoloji GUN DUZEYINDE aynen kaliyor. Gun ici sira karistirilabilir,
cunku o sira zaten bilgi tasimiyordu: kartlarda saat degil GUN
yaziyor (120 kalem, 11 farkli tarih). Okurun ayirt edebilecegi tek
zaman birimi gun.

Saat yayimlansaydi bu duzenleme YANLIS olurdu -- o zaman gun ici sira
gercek bir olcu olurdu. Sinama bunu da tutuyor.

Konu icindeki sira da korunuyor: hicbir kalem one cikarilmiyor,
yalnizca komsulari degisiyor.
"""

from __future__ import annotations

import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import insa  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


def _h(tarih, konu, ad):
    return {"tarih": tarih, "konu": konu, "baslik": ad}


serp = insa.konuya_gore_serpistir

print("\nTemel davranis")
esit(serp([]), [], "bos liste bos doner")

tek = [_h("2026-08-22", "A", "1")]
esit(serp(tek), tek, "tek kalem degismiyor")

print("\nGUN SIRASI KORUNUYOR")
karisik = [_h("2026-08-22", "A", "a1"), _h("2026-08-22", "B", "b1"),
           _h("2026-08-21", "A", "a2"), _h("2026-08-20", "C", "c1")]
esit([h["tarih"] for h in serp(karisik)],
     ["2026-08-22", "2026-08-22", "2026-08-21", "2026-08-20"],
     "tarihler ayni sirada kaliyor")

print("\nAYNI GUN ICINDE KONULAR DONUSUMLU")
yigin = ([_h("2026-08-22", "Jeopolitik", f"j{i}") for i in range(9)]
         + [_h("2026-08-22", "Makro", f"m{i}") for i in range(3)]
         + [_h("2026-08-22", "Enerji", f"e{i}") for i in range(2)])
c = [h["konu"] for h in serp(yigin)]
esit(len(set(c[:5])), 3, "ilk bes kalemde uc konu birden var")

# En uzun ard arda ayni konu dizisi
def _en_uzun_seri(konular):
    en = suan = 1
    for a, b in zip(konular, konular[1:]):
        suan = suan + 1 if a == b else 1
        en = max(en, suan)
    return en

esit(_en_uzun_seri([h["konu"] for h in yigin]), 9,
     "duzeltmeden once en uzun seri 9")
esit(_en_uzun_seri(c) <= 3, True,
     f"duzeltmeden sonra en uzun seri {_en_uzun_seri(c)}")

# KUYRUK DA SINANIYOR.
# Basit donusumlu dagitimda (ilk yazim) kucuk kumeler once tukeniyor
# ve SONDA alti kalemlik tek konulu bir kuyruk kaliyordu: yigilma
# ortadan kalkmiyor, listenin sonuna tasiniyordu.
esit(_en_uzun_seri(c[-6:]) <= 3, True,
     f"listenin SONUNDA da yigilma yok (en uzun {_en_uzun_seri(c[-6:])})")

print("\nKONU ICI SIRA KORUNUYOR")
esit([h["baslik"] for h in serp(yigin) if h["konu"] == "Jeopolitik"],
     [f"j{i}" for i in range(9)],
     "bir konunun kendi sirasi degismiyor")

print("\nHICBIR KALEM KAYBOLMUYOR VE COGALMIYOR")
esit(len(serp(yigin)), len(yigin), "sayi ayni")
esit(sorted(h["baslik"] for h in serp(yigin)),
     sorted(h["baslik"] for h in yigin), "ayni kalemler")

print("\nGUNLER BIRBIRINE KARISMIYOR")
iki_gun = ([_h("2026-08-22", "A", "a1"), _h("2026-08-22", "A", "a2")]
           + [_h("2026-08-21", "B", "b1")])
esit([h["baslik"] for h in serp(iki_gun)], ["a1", "a2", "b1"],
     "sonraki gunun kalemi one gecmiyor")

print("\nKONUSUZ KALEM DUSMUYOR")
konusuz = [_h("2026-08-22", None, "x"), _h("2026-08-22", "A", "y")]
esit(len(serp(konusuz)), 2, "konu alani bos olan kalem de basiliyor")

# --------------------------------------------------------------------
# SART: SAAT YAYIMLANMIYOR OLMALI.
#
# Bu duzenleme yalnizca gun ici sira BILGI TASIMADIGI icin mesru.
# Kartta saat gorunmeye baslarsa gun ici sira gercek bir olcu haline
# gelir ve serpistirme okuru yaniltir.
#
# Bu yuzden sablon deneteliyor: gundem kartinda saat basilirsa bu
# sinama duser ve karar yeniden dusunulur.
# --------------------------------------------------------------------
print("\nSart: gundem kartinda SAAT basilmiyor")
_sablon = (_SITE / "sablonlar" / "gundem.html").read_text(encoding="utf-8")
_kart = _sablon[_sablon.find('class="gundem-ust"'):][:600]
esit("tarih_gorunur" in _kart, True, "kartta tarih alani kullaniliyor")
for _iz in ("saat", "%H:%M", "zaman_gorunur"):
    esit(_iz in _kart, False, f"kartta saat izi yok: {_iz}")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
