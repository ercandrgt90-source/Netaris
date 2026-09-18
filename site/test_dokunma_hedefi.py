"""DOKUNMA HEDEFLERI ASGARI OLCUYU TUTMALI.

BU DOSYA NEDEN VAR
------------------
WCAG 2.2 AA (SC 2.5.8, "Target Size (Minimum)") dokunma hedefleri
icin 24x24 CSS pikseli sart kosuyor.

Olculdu (2026-09-18): `.paylas-dugme` 22 piksel yuksekligindeydi --
12px yazi + 2x4px dolgu + 2x1px kenarlik. 1.758 sayfada kullaniliyor.

DURUST OLMAK GEREKIRSE sayfa muhtemelen zaten uygundu: olcutun
"spacing" istisnasi, hedefler arasinda yeterli bosluk varsa kucuk
hedefe izin veriyor ve buradaki bosluk 8px. Ama "muhtemelen uygun"
ile "olculebilir sekilde uygun" ayni sey degil, ve aradaki fark iki
pikseldi.

BU SINAMANIN SINIRI VAR, bilerek yaziliyor: CSS'i ayristirip yukseklik
TAHMIN ediyor, tarayicida olcmuyor. Yani "gecti" demesi sayfanin
erisilebilir oldugunu KANITLAMAZ; yalnizca bilinen olculerin asgarinin
altina dusmedigini soyler. Gercek dogrulama bir tarayicida yapilir.

NE SINANIYOR
------------
1. Acikca olcu veren etkilesimli kurallar 24px'in altinda degil.
2. `.paylas-dugme` -- olculmus vakanin kendisi -- asgariyi tasiyor.
3. Jetonlar okunabiliyor (olcum bos donmuyor).
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


#: WCAG 2.2 AA asgarisi.
ASGARI = 24

#: Etkilesimli oldugu bilinen secici izleri.
ETKILESIMLI = re.compile(r"(dugme|button|\bnav a\b|\.sp-|\.tik\b)", re.I)


def yorumsuz(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def jetonlar(css: str) -> dict[str, float]:
    return {k: float(v) for k, v in re.findall(r"--([a-z0-9-]+):\s*(\d+)px", css)}


def piksel(deger: str, jeton: dict[str, float]) -> float | None:
    deger = deger.strip()
    m = re.match(r"var\(--([a-z0-9-]+)\)", deger)
    if m:
        return jeton.get(m.group(1))
    m = re.match(r"(\d+(?:\.\d+)?)px", deger)
    return float(m.group(1)) if m else None


print("\nCSS okunuyor")
_css = yorumsuz((_SITE / "statik" / "stil.css").read_text(encoding="utf-8"))
_jeton = jetonlar(_css)
esit(len(_jeton) > 5, True, f"olcu jetonlari okundu ({len(_jeton)})")

print("\nAcik olcu veren etkilesimli kurallar")
_kucuk = []
for _m in re.finditer(r"([^{}]+)\{([^}]*)\}", _css):
    _s = _m.group(1).strip().split("\n")[-1].strip()
    if not ETKILESIMLI.search(_s) or "::" in _s:
        continue
    _g = _m.group(2)
    # EKRAN OKUYUCU ETIKETI HEDEF DEGIL.
    #
    # `position: absolute` + 1px olcu + `overflow: hidden` yaygin
    # "gorsel olarak gizli" kalibi: metin ekran okuyucuya gider,
    # ekranda cizilmez, dokunulmaz. Ilk olcumde bu kalip "1px hedef"
    # diye raporlandi -- yanlis pozitif, kacan kusur kadar zararli.
    if ("position: absolute" in _g or "position:absolute" in _g) and (
            "overflow: hidden" in _g or "overflow:hidden" in _g
            or "clip" in _g):
        continue
    # Yalnizca ACIKCA olcu verenler: tahmin yurutmuyoruz.
    _h = (re.search(r"(?<![-\w])min-height\s*:\s*([^;]+)", _g)
          or re.search(r"(?<![-\w])height\s*:\s*([^;]+)", _g))
    if not _h:
        continue
    _y = piksel(_h.group(1), _jeton)
    if _y is not None and 0 < _y < ASGARI:
        _kucuk.append((_s[:46], _y))

if _kucuk:
    print("\n  ASGARININ ALTINDA:")
    for _s, _y in sorted(_kucuk, key=lambda x: x[1]):
        print(f"    {_y:5.0f}px  {_s}")
esit(_kucuk[:5], [], f"acik olculu hicbir hedef {ASGARI}px altinda degil")

print("\nOlculmus vaka: .paylas-dugme")
_m = re.search(r"(?<![\w-])\.paylas-dugme\s*\{([^}]*)\}", _css)
esit(_m is not None, True, "kural duruyor")
_govde = _m.group(1)
_mh = re.search(r"min-height\s*:\s*([^;]+)", _govde)
esit(_mh is not None, True, "min-height tanimli")
esit(piksel(_mh.group(1), _jeton) >= ASGARI, True,
     f"min-height >= {ASGARI}px (olculen {piksel(_mh.group(1), _jeton):.0f})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
