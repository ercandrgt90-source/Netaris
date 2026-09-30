# -*- coding: utf-8 -*-
"""BASLIK HIYERARSISI DAR EKRANDA DUZLESMEMELI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-30): `h1` akiskandi (`clamp`, 28-42px) ama `h2`
SABIT 25px duruyordu. Sonuc, hiyerarsinin dar ekranda duzlesmesi:

     360px  h1 28 / h2 25  -> oran 1,12
    1200px  h1 42 / h2 25  -> oran 1,68

Uc piksellik fark basligi alt bashktan ayirmaya yetmez. Telefonda
sayfa duzeyi kayboluyordu -- ve site trafiginin buyuk bolumu
telefondan geliyor.

Ayni tuzak bir basamak asagida da vardi: h2'nin dar ekrandaki degeri
`--p-xl` (21px) ve h3 TAM OLARAK o jetondaydi. h2 akiskan yapilip h3
birakilsaydi 360px'te ikisi de 21px olurdu.

NEDEN ORAN, NEDEN PIKSEL DEGIL
------------------------------
Mutlak punto degerlerini sinamak olcegi DONDURUR: tasarim
degistiginde sinama, degisiklik yanlis olmasa bile kirmizi yanar ve
"guncelle gecsin" refleksi uretir. Burada sinanan sey ILISKI: h1
h2'den, h2 h3'ten AYIRT EDILEBILIR olmali. Olcek serbest, hiyerarsi
korunuyor.

NE SINANIYOR
------------
1. h1/h2 ve h2/h3 oranlari her genislikte esigin uzerinde.
2. Hicbir genislikte iki baslik AYNI puntoda degil.
3. Basliklar kucukten buyuge dogru siralanmis (h1 > h2 > h3).
4. `clamp` cozumleyicisi bilinen girdide dogru cevap veriyor.
5. Esikler bu dosyada ELLE yazili -- CSS'ten okunmuyor.
"""

from __future__ import annotations

import pathlib
import re

_CSS = pathlib.Path(__file__).resolve().parent / "statik" / "stil.css"

#: Sinanan ekran genislikleri. 360 en yaygin telefon, 768 tablet,
#: 1440 masaustu. Aradaki gecis noktalari da orneklenyor.
GENISLIKLER = (360, 414, 600, 768, 1024, 1280, 1440)

#: En az bu kadar ayrim. 1,15 "gozle ayirt edilebilir" icin alt sinir:
#: 21px ile 18px arasindaki fark (1,17) okunabiliyor, 28 ile 25
#: arasindaki (1,12) okunmuyordu -- olcum bu araliktan geldi.
EN_AZ_ORAN = 1.15

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def jetonlar(css: str) -> dict[str, float]:
    kok = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    if not kok:
        return {}
    d = {}
    for ad, deger, birim in re.findall(
            r"(--p-[\w-]+)\s*:\s*([\d.]+)(rem|px)", kok.group(1)):
        d[ad] = float(deger) * 16 if birim == "rem" else float(deger)
    return d


def coz(deger: str, jet: dict[str, float], genislik: int) -> float | None:
    """`clamp(a, Nvw, b)` ya da `var(--p-x)` -> px. Cozulemezse None."""
    deger = deger.strip()
    m = re.fullmatch(r"var\((--p-[\w-]+)\)", deger)
    if m:
        return jet.get(m.group(1))
    m = re.fullmatch(r"clamp\(\s*(.+?)\s*,\s*([\d.]+)vw\s*,\s*(.+?)\s*\)",
                     deger)
    if not m:
        return None

    def parca(x: str) -> float | None:
        x = x.strip()
        v = re.fullmatch(r"var\((--p-[\w-]+)\)", x)
        if v:
            return jet.get(v.group(1))
        r = re.fullmatch(r"([\d.]+)rem", x)
        if r:
            return float(r.group(1)) * 16
        p = re.fullmatch(r"([\d.]+)px", x)
        return float(p.group(1)) if p else None

    alt, ust = parca(m.group(1)), parca(m.group(3))
    if alt is None or ust is None:
        return None
    return max(alt, min(float(m.group(2)) / 100 * genislik, ust))


def taban_punto(css: str, etiket: str) -> str | None:
    """`h2 { ... }` TABAN kuralindaki font-size (bilesen ezmeleri haric)."""
    gov = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sec, ic in re.findall(r"([^{}]+)\{([^{}]*)\}", gov):
        if " ".join(sec.split()) != etiket:
            continue
        m = re.search(r"font-size:\s*([^;}]+)", ic)
        if m:
            return m.group(1).strip()
    return None


print("\nCozumleyici bilinen girdide dogru")
_j = {"--p-l": 18.0, "--p-xl": 21.0, "--p-2xl": 25.0}
esit(coz("var(--p-xl)", _j, 360), 21.0, "jeton cozuluyor")
esit(coz("clamp(var(--p-xl), 2.6vw, var(--p-2xl))", _j, 360), 21.0,
     "dar ekranda alt sinir")
esit(coz("clamp(var(--p-xl), 2.6vw, var(--p-2xl))", _j, 1440), 25.0,
     "genis ekranda ust sinir")
esit(round(coz("clamp(var(--p-xl), 2.6vw, var(--p-2xl))", _j, 900), 2), 23.4,
     "arada vw degeri")
esit(coz("1.75rem", _j, 360), None, "desteklenmeyen bicim None (sessiz gecmiyor)")

print("\nTaban basliklar okunuyor")
_css = _CSS.read_text(encoding="utf-8", errors="replace")
_jet = jetonlar(_css)
esit(len(_jet) >= 6, True, f"punto jetonu okundu ({len(_jet)})")

_punto = {}
for _e in ("h1", "h2", "h3"):
    _d = taban_punto(_css, _e)
    esit(_d is not None, True, f"{_e} taban kurali bulundu")
    _punto[_e] = _d

print("\nHer genislikte hiyerarsi korunuyor")
_duz, _cakisan, _ters = [], [], []
for _w in GENISLIKLER:
    _p = {e: coz(_punto[e], _jet, _w) for e in ("h1", "h2", "h3")}
    if any(v is None for v in _p.values()):
        _duz.append((_w, "cozulemedi", _p))
        continue
    if not (_p["h1"] > _p["h2"] > _p["h3"]):
        _ters.append((_w, _p))
    if _p["h1"] == _p["h2"] or _p["h2"] == _p["h3"]:
        _cakisan.append((_w, _p))
    for _a, _b in (("h1", "h2"), ("h2", "h3")):
        if _p[_b] and _p[_a] / _p[_b] < EN_AZ_ORAN:
            _duz.append((_w, f"{_a}/{_b}", round(_p[_a] / _p[_b], 2)))

if _duz:
    print(f"\n  HIYERARSI DUZ: {_duz}")
esit(_duz, [], f"her genislikte oran >= {EN_AZ_ORAN} ({len(GENISLIKLER)} olcum)")
if _cakisan:
    print(f"\n  AYNI PUNTO: {_cakisan}")
esit(_cakisan, [], "hicbir genislikte iki baslik ayni puntoda degil")
esit(_ters, [], "h1 > h2 > h3 sirasi her genislikte korunuyor")

print("\nOlculen degerler")
for _w in (360, 768, 1440):
    _p = {e: coz(_punto[e], _jet, _w) for e in ("h1", "h2", "h3")}
    print(f"  {_w:5d}px  h1 {_p['h1']:.0f}  h2 {_p['h2']:.0f}  "
          f"h3 {_p['h3']:.0f}   oranlar "
          f"{_p['h1']/_p['h2']:.2f} / {_p['h2']/_p['h3']:.2f}")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Sabit bir h2 ile hiyerarsi 360px'te duzlesirdi -- duzeltilen kusur.
_sabit = coz("var(--p-2xl)", _jet, 360)
_h1_dar = coz(_punto["h1"], _jet, 360)
esit(_h1_dar / _sabit < EN_AZ_ORAN, True,
     f"SABIT h2 ile 360px orani esigin altinda ({_h1_dar/_sabit:.2f}) "
     f"-- duzeltilen kusur gercekten yakalaniyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
