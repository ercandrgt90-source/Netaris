# -*- coding: utf-8 -*-
"""Uygulama ikonlarini SITENIN MARKA VARLIGINDAN uretir.

    python mobil/ikon_uret.py

NEDEN BETIK, NEDEN ELLE DEGIL
-----------------------------
Expo sablonu kendi ornek ikonlariyla geliyor ve onlari oylece
birakmak, magazada baska bir urunun ikonunu yayimlamak olurdu.
Marka varligi depoda zaten var (`site/statik/marka/netaris-512.png`)
-- ikonlar ondan TURETILIYOR, elle cizilmiyor.

Elle yapilsa: logo degistiginde uygulama ikonu ESKI kalirdi ve
hicbir sey bunu haber vermezdi. Betikle tek komut.

KAYNAGIN SINIRI ACIKCA YAZILIYOR
--------------------------------
Depodaki en buyuk marka rendisi 512x512 raster; vektor kaynak YOK
(arandi, bulunamadi). 1024'e buyutme LANCZOS ile yapiliyor ve
sekiller basit oldugu icin sonuc kabul edilebilir. Yine de MAGAZA
TESLIMINDEN ONCE vektorden uretilmis 1024'luk bir asil dosya
istenmeli -- bu betik o dosya geldiginde KAYNAK yolunu degistirmek
disinda degismez.

URETILENLER
-----------
icon.png                     1024, OPAK  -- iOS kendi maskesini uygular
android-icon-foreground.png  1024, saydam, GUVENLI BOLGEDE
android-icon-background.png  1024, duz marka zemini
android-icon-monochrome.png  1024, tek renk siluet (temali ikon)
splash-icon.png              1024, saydam
favicon.png                    48

ANDROID GUVENLI BOLGE
---------------------
Uyarlanabilir ikonun yalnizca ic %66'lik dairesi her cihazda
gorunuyor; disi maskeleniyor. Marki dogrudan kenara dayamak, bazi
baslaticilarda "N"in uclarinin KESILMESI demek. Bu yuzden on plan
icerigi guvenli bolgeye sigdiriliyor.
"""

from __future__ import annotations

import pathlib
import sys

try:
    from PIL import Image
except ImportError:                       # pragma: no cover
    print("Pillow gerekiyor:  pip install Pillow")
    raise SystemExit(1)

KOK = pathlib.Path(__file__).resolve().parent.parent
KAYNAK = KOK / "site" / "statik" / "marka" / "netaris-512.png"
HEDEF = KOK / "mobil" / "assets"

#: Marka zemini -- kaynaktaki en sik renk. `app.json` icindeki
#: `backgroundColor` ile AYNI olmali.
ZEMIN = (11, 16, 24, 255)

#: Uyarlanabilir ikonda icerigin kaplayacagi oran. Guvenli bolge
#: %66; biraz daha kucuk tutmak nefes payi birakiyor.
GUVENLI = 0.60

BOY = 1024


def _mark(im: Image.Image) -> Image.Image:
    """Zemini atip yalnizca isareti (N + cubuklar) birakir."""
    im = im.convert("RGBA")
    piksel = im.load()
    g, y = im.size
    for b in range(y):
        for a in range(g):
            r, ye, m, s = piksel[a, b]
            # Zemine YAKIN her piksel saydam yapiliyor. "Tam esit"
            # olcutu kenar yumusatmasindaki ara tonlari birakir ve
            # isaretin cevresinde koyu bir hale olusur.
            if s == 0 or (abs(r - ZEMIN[0]) < 26 and abs(ye - ZEMIN[1]) < 26
                          and abs(m - ZEMIN[2]) < 26):
                piksel[a, b] = (0, 0, 0, 0)
    return im


def _kirp(im: Image.Image) -> Image.Image:
    kutu = im.getbbox()
    return im.crop(kutu) if kutu else im


def _ortala(icerik: Image.Image, boy: int, oran: float,
            zemin=(0, 0, 0, 0)) -> Image.Image:
    """Icerigi kareye, verilen orani kaplayacak sekilde yerlestirir."""
    tuval = Image.new("RGBA", (boy, boy), zemin)
    en_cok = int(boy * oran)
    g, y = icerik.size
    olcek = min(en_cok / g, en_cok / y)
    yeni = icerik.resize((max(1, int(g * olcek)), max(1, int(y * olcek))),
                         Image.LANCZOS)
    tuval.paste(yeni, ((boy - yeni.width) // 2, (boy - yeni.height) // 2),
                yeni)
    return tuval


def main() -> int:
    if not KAYNAK.is_file():
        print(f"marka varligi yok: {KAYNAK}")
        return 1
    HEDEF.mkdir(parents=True, exist_ok=True)
    asil = Image.open(KAYNAK).convert("RGBA")

    # 1) iOS / genel ikon -- OPAK kare.
    #
    # Saydam koseli bir ikon iOS'ta siyah ya da bozuk kenar gosterir;
    # iOS maskeyi KENDISI uyguluyor. Kaynaktaki yuvarlatilmis koseler
    # marka zeminiyle dolduruluyor.
    buyuk = asil.resize((BOY, BOY), Image.LANCZOS)
    opak = Image.new("RGBA", (BOY, BOY), ZEMIN)
    opak.paste(buyuk, (0, 0), buyuk)
    opak.convert("RGB").save(HEDEF / "icon.png")

    isaret = _kirp(_mark(asil))

    # 2) Android on plan -- GUVENLI BOLGEDE, saydam.
    _ortala(isaret, BOY, GUVENLI).save(HEDEF / "android-icon-foreground.png")

    # 3) Android arka plan -- duz marka zemini.
    Image.new("RGBA", (BOY, BOY), ZEMIN).convert("RGB").save(
        HEDEF / "android-icon-background.png")

    # 4) Temali ikon -- tek renk siluet.
    #
    # Android 13+ kullanicinin duvar kagidina gore renklendiriyor;
    # verilen goruntunun RENGI degil, YALNIZCA siluet kullaniliyor.
    # Cok renkli bir goruntu vermek siluetin bulanik cikmasina yol
    # acar.
    siluet = Image.new("RGBA", isaret.size, (255, 255, 255, 0))
    siluet.putalpha(isaret.getchannel("A"))
    beyaz = Image.new("RGBA", isaret.size, (255, 255, 255, 255))
    beyaz.putalpha(isaret.getchannel("A"))
    _ortala(beyaz, BOY, GUVENLI).save(HEDEF / "android-icon-monochrome.png")

    # 5) Acilis ekrani -- saydam, zemin `app.json`dan geliyor.
    _ortala(isaret, BOY, 0.52).save(HEDEF / "splash-icon.png")

    # 6) Web favicon.
    opak.resize((48, 48), Image.LANCZOS).convert("RGB").save(
        HEDEF / "favicon.png")

    for p in sorted(HEDEF.glob("*.png")):
        im = Image.open(p)
        print(f"  {p.name:32} {str(im.size):12} {im.mode}")
    print(f"kaynak: {KAYNAK.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
