# -*- coding: utf-8 -*-
"""GRAFIK PALETI stil.css JETONLARIYLA AYNI OLMALI.

BU DOSYA NEDEN VAR
------------------
`gorsel.py`nin kendi yorumu su kurali yaziyordu:

    "Tema renkleri -- stil.css :root degerleriyle AYNI olmali.
     Ayrisirsa gorsel sayfadan kopuk durur."

OLCULDU (2026-09-23): yedi rengin YEDISI de ayrismisti.

    gorsel.py          stil.css
    #0a7ea4  (mavi)    --vurgu  #0a7974  (marka teal)
    #cf2740            --azalis #c8203a
    #0f8a4d            --artis  #0a7f47
    #eef2f8            --zemin  #eef2f7
    ... ve uc renk daha

Yani grafikteki "yesil", yanindaki sayinin yesili DEGILDI ve grafigin
vurgusu markanin vurgusu degildi. Kural yaziliydi; uygulandigini
kontrol eden yoktu.

IKINCI KUSUR: TEMA
------------------
680 sayfada gomulu grafik var ve hicbiri temayi takip etmiyordu --
koyu temada okur, koyu sayfanin ortasinda PARLAK BEYAZ bir dikdortgen
goruyordu. Cozum `stil.css`te oznitelik secicisiyle ezme (gerekcesi
orada yazili); bu dosya eslemenin EKSIKSIZ kalmasini sinar.

NE SINANIYOR
------------
1. `gorsel.py`deki her renk sabiti bir stil.css jetonuna ESIT.
2. Uretilen grafiklerde kullanilan her renk tema eslemesinde VAR
   (ya da yazili gerekcesi var).
3. Koyu temada metin/vurgu kontrasti yeterli.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import gorsel  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_css = re.sub(r"/\*.*?\*/", " ",
              (_SITE / "statik" / "stil.css").read_text(encoding="utf-8"),
              flags=re.S)


def jetonlar(desen: str) -> dict[str, str]:
    m = re.search(desen + r"\s*\{([^}]*)\}", _css, re.S)
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})",
                           m.group(1))) if m else {}


ACIK = jetonlar(r':root\[data-tema="light"\]')
KOYU = jetonlar(r':root\[data-tema="dark"\]')

#: `gorsel.py` sabiti -> stil.css jetonu.
#:
#: Bu esleme kuralin KENDISI: bir sabit eklenir de buraya yazilmazsa
#: sinama onu "gerekcesiz" diye bildirir.
BAG = {
    "ZEMIN": "--zemin",
    "CIZGI": "--cizgi",
    "VURGU": "--vurgu",
    "VURGU_KOYU": "--vurgu-koyu",
    "YAZI": "--yazi",
    "YAZI_3": "--yazi-3",
    "ARTIS": "--artis",
    "AZALIS": "--azalis",
    "PARLAMA": "--sayfa-isik",
}

print("\nPalet jetonlarla ESIT")
esit(len(ACIK) > 10, True, f"acik tema jetonu okundu ({len(ACIK)})")
_ayrisan = []
for _sabit, _jeton in sorted(BAG.items()):
    _deger = getattr(gorsel, _sabit, None)
    _hedef = ACIK.get(_jeton)
    if _deger is None:
        _ayrisan.append((_sabit, "TANIMSIZ", _jeton, _hedef))
    elif _hedef and _deger.lower() != _hedef.lower():
        _ayrisan.append((_sabit, _deger, _jeton, _hedef))
if _ayrisan:
    print("\n  JETONDAN AYRISAN RENKLER:")
    for _s, _d, _j, _h in _ayrisan:
        print(f"    {_s:<12} {_d}  !=  {_j} {_h}")
esit(_ayrisan, [], f"{len(BAG)} renk sabitinin hepsi jetonuna esit")

# `gorsel.py`de BAG'da olmayan bir renk sabiti kalmasin -- yoksa
# yeni bir renk sessizce eklenir ve kural onu hic gormez.
_kaynak = (_SITE / "gorsel.py").read_text(encoding="utf-8")
_sabitler = set(re.findall(r'^([A-Z][A-Z_0-9]*)\s*=\s*"#[0-9a-fA-F]{3,8}"',
                           _kaynak, re.M))
_kayitsiz = sorted(_sabitler - set(BAG))
if _kayitsiz:
    print(f"\n  BAG defterinde OLMAYAN renk sabiti: {_kayitsiz}")
esit(_kayitsiz, [], "her renk sabiti defterde")

print("\nTema eslemesi eksiksiz")
# `stil.css`teki esleme kurallari OKUNUYOR, elle yazilmiyor.
_ESLEME = set(re.findall(
    r'\.yazi-gorsel svg \[(?:fill|stroke|stop-color)="(#[0-9a-fA-F]{6})"\]',
    _css))
esit(len(_ESLEME) >= 8, True, f"tema eslemesi okundu ({len(_ESLEME)} renk)")

#: Eslenmesi GEREKMEYEN renkler ve nedeni.
MUAF = {
    "#ffffff": "cubuk uzerindeki yari saydam parlaklik (opacity 0.22 / "
               "0.4) -- tema rengi degil, isik efekti; koyu zeminde de "
               "dogru calisiyor",
}

_CIKTI = _SITE / "cikti"
if not (_CIKTI / "index.html").exists():
    print("\n  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_GRAFIK = re.compile(r'<svg[^>]*viewBox="0 0 1200 675"[^>]*>.*?</svg>', re.S)
_kullanilan: set[str] = set()
_sayfa = 0
for _p in _CIKTI.rglob("index.html"):
    _m = _p.read_text(encoding="utf-8", errors="replace")
    _g = _GRAFIK.search(_m)
    if not _g:
        continue
    _sayfa += 1
    _kullanilan |= set(re.findall(
        r'(?:fill|stroke|stop-color)="(#[0-9a-fA-F]{6})"', _g.group(0)))
    if _sayfa >= 60:      # altmis grafik palet icin fazlasiyla yeterli
        break
esit(_sayfa > 0, True, f"ciktida grafik bulundu ({_sayfa} sayfa tarandi)")

_eslenmeyen = sorted(c for c in _kullanilan
                     if c not in _ESLEME and c.lower() not in MUAF)
if _eslenmeyen:
    print("\n  TEMA ESLEMESINDE OLMAYAN RENKLER:")
    for _c in _eslenmeyen:
        print(f"    {_c}")
    print("\n  Bunlar koyu temada OLDUGU GIBI kalir. Ya `stil.css`teki")
    print("  esleme blokuna eklenmeli ya da MUAF'a sebebiyle yazilmali.")
esit(_eslenmeyen, [], f"grafikteki {len(_kullanilan)} rengin hepsi eslenmis")

print("\nKoyu temada okunabilir")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _isik(c):
    def k(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return .2126 * k(c[0]) + .7152 * k(c[1]) + .0722 * k(c[2])


def _oran(a, b):
    la, lb = _isik(a), _isik(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


_zemin_k = KOYU.get("--zemin")
esit(bool(_zemin_k), True, "koyu tema zemini tanimli")
# Izgara cizgisi BILEREK disarida: dekoratif, zaten 0.35 opaklikta.
# 3:1 kontrastli bir izgara veriyi bastirirdi.
for _ad, _jeton, _esik in (("grafik yazisi", "--yazi", 4.5),
                           ("ikincil yazi", "--yazi-3", 4.5),
                           ("vurgu (cubuk)", "--vurgu", 3.0),
                           ("azalis", "--azalis", 4.5),
                           ("artis", "--artis", 4.5)):
    _k = KOYU.get(_jeton)
    if not _k:
        continue
    _o = _oran(_rgb(_k), _rgb(_zemin_k))
    esit(_o >= _esik, True,
         f"{_ad} koyu temada okunur ({_o:.2f} >= {_esik})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
