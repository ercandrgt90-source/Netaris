# -*- coding: utf-8 -*-
"""AMBLEM ORANI, KARTIN GORSEL YUVASIYLA AYNI OLMALI.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-10-04): amblem 1200x400 (3:1) uretiliyordu ama kartin
gorsel yuvasi (`.kart-gorsel`) 16:9 ve `.kart-amblem .amblem` kurali
`object-fit: cover` kullaniyor. `cover`, kutuyu DOLDURMAK icin
gorseli kirpar. Sonuc: amblemin genisliginin yalnizca %60'i
goruluyordu; %40'i -- her yandan %20 -- kirpiliyordu.

Gorunur sonuc, uzun sirket adlarinin iki yanindan kesilmesiydi:

    GIRISIM ELEKTRIK SANAYI TAAHHUT VE TICARET A.S.
      ->  RISIM ELEKTRIK SANAYI TAAHHUT VE TICARET

SVG kendi icinde SIGIYORDU (metin 815 / viewBox 1200). Kirpan sey
kartti. Bu yuzden "metni kisalt" yanlis cozumdu -- duzeltilmesi
gereken ORANDI.

Kusur sessizdi: hicbir sey hata vermiyor, kart dolu gorunuyor ve
yalnizca ADI UZUN olan sirketlerde fark ediliyor. 767 amblemin
cogunda kod kisa oldugu icin goze carpmiyordu.

NE SINANIYOR
------------
1. `amblem.py` olculeri ile `.kart-gorsel` orani AYNI.
2. Uretilen SVG gercekten o olculeri tasiyor.
3. Sablonlardaki `<img width height>` degerleri de ayni -- yoksa
   tarayici yanlis yer ayirir ve sayfa yuklenirken ziplar (CLS).
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


import amblem  # noqa: E402

# --- 1) kart yuvasinin orani CSS'ten OKUNUYOR, yazilmiyor ---
_CSS = (_SITE / "statik" / "stil.css").read_text(encoding="utf-8")
_m = re.search(r"\.kart-gorsel\s*\{[^}]*aspect-ratio:\s*(\d+)\s*/\s*(\d+)",
               _CSS, re.S)
esit(bool(_m), True, "`.kart-gorsel` orani CSS'te bulundu")
_kart_oran = int(_m.group(1)) / int(_m.group(2))

_amblem_oran = amblem.GEN / amblem.BOY
esit(round(_amblem_oran, 3), round(_kart_oran, 3),
     f"amblem orani ({amblem.GEN}x{amblem.BOY} = {_amblem_oran:.3f})"
     f" kart yuvasiyla ayni ({_m.group(1)}/{_m.group(2)}"
     f" = {_kart_oran:.3f})")

# --- 2) uretilen SVG gercekten o olculeri tasiyor ---
_svg = amblem.amblem("GESAN", "GİRİŞİM ELEKTRİK SANAYİ TAAHHÜT VE TİCARET A.Ş.",
                     "Sanayi", "2026 2. çeyrek")
_v = re.search(r'viewBox="0 0 (\d+) (\d+)"', _svg)
esit(bool(_v), True, "uretilen SVG viewBox tasiyor")
esit((int(_v.group(1)), int(_v.group(2))), (amblem.GEN, amblem.BOY),
     "viewBox, sabitlerle ayni")
# Metin kutunun DISINA tasmamali (kaba ust sinir: yarim em basina harf).
for _t in re.finditer(r'<text[^>]*font-size="(\d+)"[^>]*>([^<]*)</text>', _svg):
    _punto, _metin = int(_t.group(1)), _t.group(2)
    _tahmin = sum(_punto * (0.26 if c == " " else 0.62) for c in _metin)
    esit(_tahmin < amblem.GEN, True,
         f"\"{_metin[:28]}\" viewBox'a sigiyor (~{_tahmin:.0f} < {amblem.GEN})")

# --- 3) sablonlardaki olculer de ayni ---
_kotu = []
for _p in sorted((_SITE / "sablonlar").glob("*.html")):
    _s = _p.read_text(encoding="utf-8")
    for _im in re.finditer(r'class="amblem"[^>]*width="(\d+)"\s+height="(\d+)"',
                           _s):
        if (int(_im.group(1)), int(_im.group(2))) != (amblem.GEN, amblem.BOY):
            _kotu.append(f"{_p.name}: {_im.group(1)}x{_im.group(2)}")
if _kotu:
    print("\n  SABLONDAKI OLCU AMBLEMDEN FARKLI:")
    for _k in _kotu:
        print(f"    {_k}")
esit(_kotu, [], f"sablonlardaki <img> olculeri amblemle ayni"
                f" ({amblem.GEN}x{amblem.BOY})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
