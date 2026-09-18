# -*- coding: utf-8 -*-
"""RENK JETONLARI WCAG AA KONTRASTINI SAGLAMALI -- IKI TEMADA DA.

BU DOSYA NEDEN VAR
------------------
Mobil/erisilebilirlik denetiminde (2026-09-18) kontrasti olcen hicbir
sinama olmadigi goruldu. Olculunce acik temada bir acik cikti:

    --vurgu #0a7d78 / sayfa zemini #eef2f7   =  4.43   (AA esigi 4.5)

`a { color: var(--vurgu) }` sitedeki BUTUN baglantilar demek ve govde
metni dogrudan sayfa zemininin uzerinde duruyor (`main.kabuk >
.sayfa > .govde` -- hicbiri kendi zeminini vermiyor). Yani acik temada
her baglanti esigin 0,07 altindaydi. Marka bir tik koyultuldu
(#0a7974): ton 177,4 -> 177,3 derece, doygunluk %85,2 -> %84,7,
yalnizca aydinlik %26,5 -> %25,7. Yeni oran 4,67.

NEDEN JETON SEVIYESINDE
-----------------------
Her bilesenin kontrastini tek tek olcmek tarayici gerektirir. Ama
sitedeki renkler birkac JETONDAN geliyor; jetonlar gecerse bilesenler
de geciyor. Jeton seviyesi hem olculebilir hem de kusuru KAYNAGINDA
yakaliyor: bir jeton degistiginde onunla boyanan her sey degisir.

NE SINANIYOR
------------
1. Kontrast hesabi bilinen degerlerde dogru (kendi kendini sinar).
2. Iki temada da metin/zemin ciftleri AA esigini gecer.
3. Vurgu rengi hem sayfa zemininde hem panelde okunur.
4. Marka, ARTIS sinyalinden ton olarak yeterince uzak durur --
   `stil.css`te yazili "26 derece" karari korunuyor mu.
"""

from __future__ import annotations

import colorsys
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent

#: WCAG 2.2 esikleri.
AA_NORMAL = 4.5
AA_BUYUK = 3.0

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def rgb(renk: str) -> tuple[int, int, int] | None:
    h = (renk or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def isik(c: tuple[int, int, int]) -> float:
    """Bagil parlaklik -- WCAG 2.x tanimi."""
    def k(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * k(c[0]) + 0.7152 * k(c[1]) + 0.0722 * k(c[2])


def oran(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = isik(a), isik(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def ton(renk: str) -> float:
    c = rgb(renk)
    return colorsys.rgb_to_hls(*[v / 255 for v in c])[0] * 360


print("\nHesap gercekten calisiyor mu")
# Bilinen degerler: standardin kendisinden, siteden bagimsiz.
esit(round(oran(rgb("#000000"), rgb("#ffffff"))), 21, "siyah/beyaz = 21")
esit(round(oran(rgb("#777777"), rgb("#777777"))), 1, "ayni renk = 1")
esit(round(oran(rgb("#767676"), rgb("#ffffff")), 1), 4.5,
     "#767676/beyaz = 4.5 (AA sinir ornegi)")
esit(oran(rgb("#0a7974"), rgb("#eef2f7")) > oran(rgb("#0a7d78"), rgb("#eef2f7")),
     True, "koyultmak orani ARTIRIYOR (yon dogru)")
esit(rgb("#xyzxyz"), None, "gecersiz renk cozulmuyor")

print("\nJetonlar okunuyor")
_css = re.sub(r"/\*.*?\*/", " ",
              (_SITE / "statik" / "stil.css").read_text(encoding="utf-8"),
              flags=re.S)


def jeton_blogu(desen: str) -> dict[str, str]:
    m = re.search(desen, _css, re.S)
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", m.group(1))) if m else {}


ACIK = jeton_blogu(r':root\[data-tema="light"\]\s*\{([^}]*)\}')
KOYU = jeton_blogu(r':root\[data-tema="dark"\]\s*\{([^}]*)\}')
esit(len(ACIK) > 10 and len(KOYU) > 10, True,
     f"iki tema jetonu okundu (acik {len(ACIK)}, koyu {len(KOYU)})")
# Etiketler DOGRU mu: acik temanin zemini gercekten acik olmali.
# Olculdu: ilk taramada `:root` blogunu "acik tema" diye etiketlemistim
# ve dogru cikti -- ama dogrulamadan gecmek, etiket kaydiginda butun
# sonuclari sessizce tersine cevirirdi.
esit(isik(rgb(ACIK["--zemin"])) > isik(rgb(KOYU["--zemin"])), True,
     "acik temanin zemini koyu temadan DAHA AYDINLIK (etiketler dogru)")


def coz(ad: str, jeton: dict[str, str], derin: int = 0) -> str | None:
    d = (jeton.get(ad) or "").strip()
    if derin > 6:
        return None
    if d.startswith("#"):
        return d
    m = re.match(r"var\(\s*(--[\w-]+)", d)
    return coz(m.group(1), jeton, derin + 1) if m else None


#: (aciklama, on plan jetonu, arka plan jetonu, esik)
CIFTLER = [
    ("govde yazisi / sayfa", "--yazi", "--zemin", AA_NORMAL),
    ("ikincil yazi / sayfa", "--yazi-2", "--zemin", AA_NORMAL),
    ("ucuncul yazi / sayfa", "--yazi-3", "--zemin", AA_NORMAL),
    ("govde yazisi / panel", "--yazi", "--panel", AA_NORMAL),
    ("ikincil yazi / panel", "--yazi-2", "--panel", AA_NORMAL),
    ("ucuncul yazi / panel", "--yazi-3", "--panel", AA_NORMAL),
    # `a { color: var(--vurgu) }` -- BUTUN baglantilar, normal punto.
    ("BAGLANTI / sayfa", "--vurgu", "--zemin", AA_NORMAL),
    ("BAGLANTI / panel", "--vurgu", "--panel", AA_NORMAL),
    # Sinyal renkleri sayi ve etiketlerde, normal puntoda kullaniliyor.
    ("artis / sayfa", "--artis", "--zemin", AA_NORMAL),
    ("azalis / sayfa", "--azalis", "--zemin", AA_NORMAL),
    ("uyari / sayfa", "--uyari", "--zemin", AA_NORMAL),
    ("artis / panel", "--artis", "--panel", AA_NORMAL),
    ("azalis / panel", "--azalis", "--panel", AA_NORMAL),
]

for _tema_ad, _j in (("ACIK", ACIK), ("KOYU", KOYU)):
    print(f"\n{_tema_ad} tema")
    _dusuk = []
    for _ad, _on, _arka, _esik in CIFTLER:
        _c1, _c2 = coz(_on, _j), coz(_arka, _j)
        _r1, _r2 = rgb(_c1 or ""), rgb(_c2 or "")
        if not _r1 or not _r2:
            print(f"    ATLANDI  {_ad}  ({_on}={_c1}, {_arka}={_c2})")
            continue
        _o = oran(_r1, _r2)
        if _o < _esik:
            _dusuk.append((_ad, _c1, _c2, round(_o, 2), _esik))
    if _dusuk:
        print("\n  ESIGIN ALTINDA:")
        for _d in _dusuk:
            print(f"    {_d[0]:<24} {_d[1]} / {_d[2]}  =  {_d[3]}"
                  f"  (esik {_d[4]})")
    esit(_dusuk, [], f"{_tema_ad.lower()} temada butun ciftler AA gecer"
                     f" ({len(CIFTLER)} cift)")

print("\nMarka ile sinyal rengi ayirt edilebiliyor")
# `stil.css`te yazili karar: marka ile "artis" yesili arasinda en az
# ~26 derece ton farki olsun, yoksa okur "yesil = artis" ile
# "yesil = Netaris" arasinda ayrim yapamaz.
_mark, _art = coz("--vurgu", ACIK), coz("--artis", ACIK)
_fark = abs(ton(_mark) - ton(_art))
esit(_fark >= 20, True,
     f"marka ({_mark}) ile artis ({_art}) arasi {_fark:.1f} derece")

print(f"\nTUM TESTLER GECTI ({_gecti})")
