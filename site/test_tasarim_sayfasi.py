# -*- coding: utf-8 -*-
"""TASARIM SAYFASI KENDI VAADINI TUTMALI: ELLE RENK YAZILMAZ.

BU DOSYA NEDEN VAR
------------------
Sayfanin kendi girisi su vaadi veriyor:

    "Bu sayfadaki hicbir deger elle yazilmadi -- hepsi stil.css
     ayristirilarak uretiliyor... Elle yazilsaydi sayfa ilk gun
     dogru olur, ikinci gun sessizce yaniltici hale gelirdi."

OLCULDU (2026-10-04): vaat TUTULMUYORDU. "Vurgu rengi" bolumu
secilen rengi UC DUZ DEGERLE gosteriyordu --

    #0a7974  (vurgu)   #075f5c  (vurgu-koyu)   #14b8a6  (parlak)

Ayni gun palet degisti, `--vurgu` #09726d oldu ve bu bolum
guncellenmedi. Yani sayfa, "secilen renk budur" diye ARTIK
KULLANILMAYAN bir rengi gosteriyordu. Vaadin tarif ettigi sey
kelimesi kelimesine gerceklesti: ikinci gun sessizce yaniltici.

Daha once ayni sinifta bir kusur daha yasanmisti: "Yedi adimli
olcek" diyen cumle sekiz jeton varken guncellenmemisti. O zaman
CUMLEDEKI SAYI uretilir hale getirildi; RENKLER elle kaldi.

NE SINANIYOR
------------
Sablonda, IZIN VERILENLER DISINDA duz renk degeri yok.

IZIN VERILENLER -- VE NEDEN
---------------------------
Degerlendirilen MAVI palet (#146EF5 ve tonlari) elle kaliyor ve bu
DOGRU: o bir TARIHSEL karsilastirma, sitenin bir jetonu degil.
"Neden mavi degil" sorusunun cevabi o degerle anlamli ve jetonlardan
okunamaz -- cunku sitede boyle bir jeton hic olmadi.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_P = _SITE / "sablonlar" / "tasarim.html"
_HAM = _P.read_text(encoding="utf-8")
esit(len(_HAM) > 500, True, "tasarim.html okundu")

#: Jinja yorumlari ({# ... #}) HARIC: gerekce metni tarihsel bir
#: degeri anabilmeli, cunku gerekce bayatlamaz -- deger bayatlar.
_SABLON = re.sub(r"\{#.*?#\}", " ", _HAM, flags=re.S)

#: Degerlendirilen mavi palet. Tarihsel karsilastirma; jetonu yok.
#:
#: `#1a1a1a` AYRI BIR DURUM: sayfanin kendi metninde gecen bir
#: ORNEK -- "Bilesen #1a1a1a degil var(--yazi) kullanir" diyor.
#: Yani tam da bu sinamanin savundugu kurali anlatiyor ve bir jetonu
#: temsil etmiyor; jetondan okunamaz cunku karsiligi yok.
_IZINLI = {"#146ef5", "#0b52c0", "#4a92ff", "rgba(20,110,245,0.10)",
           "#1a1a1a"}

_hex = set(re.findall(r"#[0-9a-fA-F]{6}\b", _SABLON))
_rgba = set(re.findall(r"rgba\([^)]*\)", _SABLON))
_bulunan = {h.lower() for h in _hex} | {r.replace(" ", "") for r in _rgba}
_kacak = sorted(_bulunan - _IZINLI)

if _kacak:
    print(f"\n  SABLONDA ELLE YAZILMIS RENK: {len(_kacak)}")
    for _k in _kacak:
        _m = re.search(rf".{{0,60}}{re.escape(_k)}.{{0,30}}", _SABLON, re.I)
        print(f"    {_k}   ...{re.sub(r's+', ' ', _m.group(0)).strip()[:84]}...")
    print("  Jetonlardan okunmali -- `renkler` listesi sablona veriliyor.")
esit(_kacak, [],
     f"tasarim sayfasinda elle yazilmis renk yok ({len(_IZINLI)} izinli)")

# Secilen rengin GERCEKTEN jetondan okundugu dogrulaniyor: aksi halde
# yukaridaki sinama, renk tamamen silinse de yesil kalirdi.
esit(bool(re.search(r'selectattr\(\s*"ad"\s*,\s*"equalto"\s*,\s*"--vurgu"',
                    _SABLON)),
     True, "secilen vurgu rengi `renkler` jeton listesinden okunuyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
