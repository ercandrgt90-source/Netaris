# -*- coding: utf-8 -*-
"""JETONUN YANINDAKI px YORUMU YALAN SOYLEYEMEZ.

BU DOSYA NEDEN VAR
------------------
`stil.css` punto jetonlarini rem ile yaziyor ve yanina px karsiligini
yorum olarak koyuyor:

    --p-2xl: 1.5625rem;  /* 25,0 px */

Olculdu (2026-09-30): DORT jetonun yorumu yanlisti.

    --p-l    1.125rem  = 18px   yorum "17,0 px"
    --p-xl   1.3125rem = 21px   yorum "19,0 px"
    --p-2xl  1.5625rem = 25px   yorum "22,0 px"
    --p-3xl  1.9375rem = 31px   yorum "28,0 px"

Sebep: punto olcegi 2026-09-24'te degistirildi (12/13/14/16/18/21/
25/31), DEGERLER guncellendi, YORUMLAR guncellenmedi. Hatanin sahibi
bu oturumdaki kendi degisikligim.

NEDEN ONEMLI
------------
Deponun `/tasarim/` sayfasi tam bu yuzden var ve gerekcesi `insa.py`
icinde yazili: "Sayfa bir AYNA, kopya degil. Elle yazilan bir tasarim
sayfasi ilk gun dogru olur, `--p-l` degistigi gun sessizce
yanilticiya doner ve ekip ondan okuyup YANLIS DEGERI kullanir."

Ayni mantik bu yorumlar icin de gecerli: `--p-2xl /* 22 px */` okuyan
biri 22'ye gore tasarlar, tarayici 25 basar. Yanlis yorum, yorumsuz
olmaktan kotudur -- cunku dogru sanilir.

MEVCUT SINAMA BUNU TUTMUYORDU: `test_punto_olcegi.py` yorumlari
BILEREK soyuyor (`yorumsuz()`) ve yalnizca degerleri olcuyor. Dogru
bir tercih; ama boylece yorumlar korumasiz kaliyordu.

NE SINANIYOR
------------
1. px yorumu tasiyan her jetonun yorumu GERCEK degere esit.
2. Tarama gercekten jeton buluyor -- desen bosa dusmuyor.
3. Kontrolun kendisi calisiyor: uydurma bir sapma YAKALANIYOR.
"""

from __future__ import annotations

import pathlib
import re

_CSS = pathlib.Path(__file__).resolve().parent / "statik" / "stil.css"

#: `--ad: <sayi><birim>;  /* <sayi> px */`
_JETON = re.compile(
    r"--([a-z0-9-]+):\s*([0-9.]+)(rem|px)\s*;\s*/\*\s*([0-9,]+)\s*px")

#: Yuvarlama payi. Yorumlar tek ondalikla yaziliyor ("12,0 px").
TOLERANS_PX = 0.05

#: En az bu kadar jeton bulunmali. Desen bir gun bosa duserse
#: (bicim degisir, yorumlar tasinir) sinama SESSIZCE gecerdi --
#: "sifir ihlal" ile "sifir kontrol" ayni sonucu verir.
EN_AZ_JETON = 5

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def sapmalar(css: str) -> list[tuple[str, float, float]]:
    """(jeton, yorumdaki px, gercek px) -- yalnizca UYUSMAYANLAR."""
    kotu = []
    for ad, deger, birim, yorum in _JETON.findall(css):
        gercek = float(deger) * 16 if birim == "rem" else float(deger)
        yazan = float(yorum.replace(",", "."))
        if abs(gercek - yazan) >= TOLERANS_PX:
            kotu.append((ad, yazan, gercek))
    return kotu


_ham = _CSS.read_text(encoding="utf-8", errors="replace")

print("\nTarama gercekten calisiyor")
_bulunan = _JETON.findall(_ham)
esit(len(_bulunan) >= EN_AZ_JETON, True,
     f"px yorumlu jeton bulundu ({len(_bulunan)} >= {EN_AZ_JETON})")

print("\nYorumlar gercek degere esit")
_kotu = sapmalar(_ham)
if _kotu:
    print("\n  YORUMU YANLIS JETON:")
    for _ad, _y, _g in _kotu:
        print(f"    --{_ad}: yorum {_y:.1f} px, gercek {_g:.1f} px")
esit(_kotu, [], f"her px yorumu dogru ({len(_bulunan)} jeton)")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Uydurma bir sapma yakalanmali; yoksa "sifir ihlal" ile
# "sifir kontrol" ayni gorunur.
_sahte = "  --p-test: 1.5625rem;  /* 22,0 px */"
esit([a for a, _, _ in sapmalar(_sahte)], ["p-test"],
     "yanlis yorum YAKALANIYOR (kural sahte degil)")
_dogru = "  --p-test: 1.5625rem;  /* 25,0 px */"
esit(sapmalar(_dogru), [], "dogru yorum sorunlu sayilmiyor")
# px birimi de cozulmeli -- jetonlar bir gun px'e donerse.
esit([a for a, _, _ in sapmalar("  --b-test: 16px;  /* 12,0 px */")],
     ["b-test"], "px birimli jeton da denetleniyor")
esit(sapmalar("  --b-test: 16px;  /* 16,0 px */"), [],
     "px birimli dogru yorum geciyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
