# -*- coding: utf-8 -*-
"""Play magaza gorselini MARKA VARLIGINDAN uretir.

    python mobil/magaza_gorsel.py

Play "one cikan gorsel" (feature graphic) icin 1024x500 PNG
istiyor; her listede en ustte, arama sonuclarinda ve tanitim
alanlarinda gorunuyor.

NEDEN BETIK: ikonlarda oldugu gibi, logo degistiginde gorselin
eski kalmamasi icin. Elle yapilsa kimse haber vermezdi.

TASARIM KARARI -- SADE
Play'in kendi rehberi metni gorselin icine koymamayi oneriyor:
uygulama adi ve kisa aciklama zaten gorselin ALTINDA basiliyor ve
ikisi ust uste binince kalabalik oluyor. Ayrica metin cevrilmiyor,
yani tek dile cakiliyor.

Bu yuzden gorsel yalnizca marka isaretini ve zemini tasiyor:
    - zemin  #0b1018  (markanin kendi zemini, ikonla ayni)
    - isaret TAM ORTADA, yuksekligin %46'si
    - arkasinda cok hafif teal parilti (markanin #2dd4bf'i)

GUVENLI ALAN: Play bazi yerlesimlerde gorselin kenarlarini
kirpabiliyor. Isaret ortada ve kenarlardan uzak tutuluyor.
"""

from __future__ import annotations

import pathlib
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:                       # pragma: no cover
    print("Pillow gerekiyor:  pip install Pillow")
    raise SystemExit(1)

KOK = pathlib.Path(__file__).resolve().parent.parent
KAYNAK = KOK / "site" / "statik" / "marka" / "netaris-512.png"
HEDEF = KOK / "mobil" / "magaza" / "one-cikan-gorsel.png"

GEN, YUK = 1024, 500
ZEMIN = (11, 16, 24, 255)
TEAL = (45, 212, 191, 255)

#: Isaretin yukseklige orani. Play kenarlari kirpabildigi icin
#: bol pay birakiliyor.
ISARET_ORANI = 0.46


def _isaret(im: Image.Image) -> Image.Image:
    """Zemini atip yalnizca isareti birakir (ikon uretecinin aynisi)."""
    im = im.convert("RGBA")
    p = im.load()
    g, y = im.size
    for b in range(y):
        for a in range(g):
            r, ye, m, s = p[a, b]
            if s == 0 or (abs(r - ZEMIN[0]) < 26 and abs(ye - ZEMIN[1]) < 26
                          and abs(m - ZEMIN[2]) < 26):
                p[a, b] = (0, 0, 0, 0)
    kutu = im.getbbox()
    return im.crop(kutu) if kutu else im


def main() -> int:
    if not KAYNAK.is_file():
        print(f"marka varligi yok: {KAYNAK}")
        return 1
    HEDEF.parent.mkdir(parents=True, exist_ok=True)

    tuval = Image.new("RGBA", (GEN, YUK), ZEMIN)

    # HAFIF TEAL PARILTI -- isaretin arkasinda, derinlik icin.
    #
    # Ilk tasarimda sag kenarda uc teal cubuk vardi: logonun kendi
    # cubuklarini TEKRAR ediyordu, kenara cok yakindi (Play
    # kirpabiliyor) ve ortada buyuk bir bosluk birakiyordu.
    # Paritli kirpilmaya dayanikli ve tekrar etmiyor.
    parilti = Image.new("RGBA", (GEN, YUK), (0, 0, 0, 0))
    pc = ImageDraw.Draw(parilti)
    mx, my = GEN // 2, YUK // 2
    for i in range(44, 0, -1):
        r = int(YUK * 0.52 * i / 44)
        a = int(26 * (1 - i / 44) ** 2)
        if a <= 0:
            continue
        pc.ellipse([mx - r, my - r, mx + r, my + r],
                   fill=(TEAL[0], TEAL[1], TEAL[2], a))
    tuval = Image.alpha_composite(tuval, parilti)

    # ISARET ORTADA. Play bazi yerlesimlerde kenarlari kirpiyor;
    # ortada ve bol paylı durmasi her kirpimda saglam kaliyor.
    isaret = _isaret(Image.open(KAYNAK))
    hedef_yuk = int(YUK * ISARET_ORANI)
    olcek = hedef_yuk / isaret.height
    yeni = isaret.resize(
        (max(1, int(isaret.width * olcek)), hedef_yuk), Image.LANCZOS)
    tuval.paste(yeni, ((GEN - yeni.width) // 2, (YUK - yeni.height) // 2),
                yeni)

    tuval.convert("RGB").save(HEDEF)
    im = Image.open(HEDEF)
    print(f"  {HEDEF.relative_to(KOK)}  {im.size}  {im.mode}")
    print(f"  kaynak: {KAYNAK.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
