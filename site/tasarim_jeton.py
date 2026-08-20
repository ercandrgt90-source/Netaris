"""Tasarim sistemi sayfasinin verisi -- `stil.css`ten OKUNUR.

    stil.css  ->  jetonlar  ->  /tasarim/ sayfasi

NEDEN OKUNUYOR, ELLE YAZILMIYOR
-------------------------------
Bir tasarim sistemi sayfasinin tek isi DOGRUYU SOYLEMEK. Jetonlari
elle yazsaydim sayfa ilk gun dogru olurdu, ikinci gun `--p-l` degisir
ve sayfa eski degeri gostermeye devam ederdi -- hicbir hata vermeden.
O noktadan sonra sayfa yardimci degil YANILTICI olur: ekip ondan
okuyup yanlis degeri kullanir.

O yuzden burasi bir AYNA. Sayfada gorunen her deger `stil.css`ten
ayristirildi; CSS degisirse sayfa kendiliginde degisir. Ayni sebeple
burada hicbir jeton TANIMLANMIYOR -- tanim tek yerde, CSS'te.

KULLANIM SAYISI DA GOSTERILIYOR
-------------------------------
Her jetonun yaninda kac yerde kullanildigi yaziyor. Bunun sebebi
olculdu: bir jeton tanimli olup HIC kullanilmiyorsa olcek degil
suslemedir, ve olcegin gercekten uygulanip uygulanmadigi ancak
sayarak anlasilir. Sifir kullanimli jeton sayfada ISARETLENIYOR.
"""

from __future__ import annotations

import pathlib
import re

STIL = pathlib.Path(__file__).resolve().parent / "statik" / "stil.css"

#: Sayfada gosterilecek jeton oBEKLERI: (onek, baslik, aciklama).
#:
#: Renkler bilerek DISARIDA: onlarin dogru gosterimi ornek kutu,
#: liste degil -- ayri bolumde ele aliniyor.
OBEK = (
    ("p-", "Punto",
     "Yedi adimli olcek. Ara degerler kullanilmiyor: iki punto "
     "arasindaki fark okurun ayirt edebilecegi kadar buyuk olmali, "
     "yoksa hiyerarsi degil gurultu uretir."),
    ("b-", "Bosluk",
     "Dort piksel tabanli izgara. 20 ve 28 sonradan eklendi, cunku "
     "ikisi de izgaradaydi ve sirasiyla 30 ve 12 yerde kullaniliyordu "
     "-- eksik olan kullanim degil, olcegin kendisiydi."),
    ("satir-", "Satir yuksekligi",
     "Uzun metin genis, baslik dar. Baslikta satirlar birbirine "
     "yaklasir cunku goz zaten kisa mesafe kat ediyor."),
)


def _css() -> str:
    return STIL.read_text(encoding="utf-8")


def jetonlar(css: str | None = None) -> list[dict]:
    """`stil.css`teki jeton obekleri, kullanim sayilariyla."""
    css = _css() if css is None else css
    tanim: dict[str, str] = {}
    for ad, deger in re.findall(r"--([\w-]+)\s*:\s*([^;{}]+);", css):
        # ILK tanim geceriyor: sonrakiler karanlik tema ya da dar
        # ekran icin yapilan EZMELER, temel deger degil.
        tanim.setdefault(ad, deger.strip())

    cikti = []
    for onek, baslik, aciklama in OBEK:
        satir = []
        for ad, deger in tanim.items():
            if not ad.startswith(onek):
                continue
            n = len(re.findall(rf"var\(--{re.escape(ad)}\s*[,)]", css))
            satir.append({"ad": f"--{ad}", "deger": deger, "kullanim": n})
        if satir:
            cikti.append({"onek": onek, "baslik": baslik,
                          "aciklama": aciklama, "jeton": satir})
    return cikti


def renkler(css: str | None = None) -> list[dict]:
    """Renk jetonlari. AYIRT EDILME olcusuyle birlikte.

    Yalnizca `#rrggbb` ve `rgb()` cozuluyor; `var()` zincirleri
    burada takip EDILMIYOR cunku zincirin ucu temaya gore degisir ve
    tek bir kutu ile gosterilemez -- yanlis kutu, kutu olmamasindan
    kotudur.
    """
    css = _css() if css is None else css
    # Temel (acik) tema: ilk :root blogu.
    m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    govde = m.group(1) if m else ""
    cikti = []
    for ad, deger in re.findall(r"--([\w-]+)\s*:\s*([^;{}]+);", govde):
        d = deger.strip()
        if not re.match(r"^(#[0-9a-fA-F]{3,8}|rgba?\()", d):
            continue
        n = len(re.findall(rf"var\(--{re.escape(ad)}\s*[,)]", css))
        cikti.append({"ad": f"--{ad}", "deger": d, "kullanim": n})
    return cikti


def olculer(css: str | None = None) -> dict:
    """Sayfanin kendi hakkinda soyledigi OLCUMLER.

    Tasarim sistemi sayfalari genelde kurallari anlatir; burada
    kurallarin NE KADAR TUTTUGU da yaziyor. Izgara disi deger sayisi
    gizlenmiyor cunku gizlenen sayi duzelmiyor.
    """
    css = _css() if css is None else css
    izgara_disi = 0
    for m in re.finditer(
            r"\b(padding|margin|gap|row-gap|column-gap)[a-z-]*\s*:"
            r"([^;{}]+);", css):
        for v in re.findall(r"(\d+)px", m.group(2)):
            if int(v) > 2 and int(v) % 4:
                izgara_disi += 1
    return {
        "punto_kullanim": len(re.findall(r"var\(--p-", css)),
        "bosluk_kullanim": len(re.findall(r"var\(--b-", css)),
        "izgara_disi": izgara_disi,
        "satir": len(css.splitlines()),
    }
