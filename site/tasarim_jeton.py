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

#: CSS yorumu. `_css()` bunu ayikliyor -- gerekcesi orada.
_YORUM = re.compile(r"/\*.*?\*/", re.S)

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
    """`stil.css` -- YORUMLARI AYIKLANMIS.

    NEDEN AYIKLANIYOR
    -----------------
    Olculdu (2026-09-18): `renkler()` temel blogu
    `:root\\s*\\{(.*?)\\}` ile, yani TEMBEL eslesmeyle ariyor. Bu
    dosyanin yorumlari ornek CSS icerebiliyor ve bir yorumun icindeki
    tek bir `}` blogu erkenden kapatiyor. Nitekim `--vurgu` jetonunun
    yanina yazilan "`a { color: var(--vurgu) }` sitedeki BUTUN
    baglantilar demek" aciklamasi jeton listesini 59'dan 3'e dusurdu
    ve /tasarim/ sayfasi renk kutularini kaybetti.

    Kusur aciklamada degil AYRISTIRICIDA: bir CSS okuyucusu, yorumun
    icindekini kural sanmamali. Ayni sinif daha once ters yonde de
    yasandi -- bir denetim, yorum icindeki ornegi GERCEK kural sanip
    sahte bulgu uretmisti.
    """
    return _YORUM.sub(" ", STIL.read_text(encoding="utf-8"))


def _hazirla(css: str | None) -> str:
    """Disaridan gelen CSS de yorumsuz olmali.

    Ilk duzeltmede yalnizca `olculer()` yorumlari ayikliyordu;
    `renkler()` ve `jetonlar()` disaridan CSS aldiklarinda
    ayiklamiyordu. Uretimde fark etmiyordu (orada `css is None`)
    ama ayni soruya iki farkli cevap veren iki kod yolu demekti --
    ve bu depoda o desen defalarca sessiz kusur uretti.
    """
    return _css() if css is None else _YORUM.sub(" ", css)


def jetonlar(css: str | None = None) -> list[dict]:
    """`stil.css`teki jeton obekleri, kullanim sayilariyla."""
    css = _hazirla(css)
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
    css = _hazirla(css)
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
    # SAYIM YORUMSUZ, BOYUT HAM DOSYADAN.
    #
    # Olculdu (2026-09-18): yorumlar sayilinca `--b-` kullanimi 658
    # gorunuyordu, gercegi 648; "izgara disi" 168 idi, gercegi 165 --
    # uc tanesi yorumun icindeki ORNEKTI. Bir olcum sayfasi kendi
    # yorumlarini kural sayamaz.
    #
    # "CSS satiri" ise DOSYANIN BOYUTU: orada yorumlar da sayiliyor,
    # cunku okurun sordugu "bu stil dosyasi ne kadar buyuk" ve
    # yorumlar da bakilan, tutulan, tasinan satirlar.
    ham = STIL.read_text(encoding="utf-8") if css is None else css
    css = _hazirla(css)

    # IZGARA IKI PIKSEL, DORT DEGIL -- OLCULDU.
    #
    # Burada `% 4` yaziyordu ve sayfa "izgara disi 165" diyordu. O sayi
    # YANLISTI: `stil.css`teki jeton blogunun kendi yorumu izgaranin
    # aslinda IKI piksel oldugunu olcup yaziyor ("dort piksel yalnizca
    # ANA adimlar"). Yani sayfa, yanlis oldugu BELGELENMIS bir kurala
    # gore ihlal sayiyordu.
    #
    # Gercek dagilim (2026-09-23):
    #     4'un kati    11
    #     2'nin kati  157   <- belgelenen yarim adimlar, ihlal DEGIL
    #     tek sayi      8   <- asil izgara disi (sonra sifirlandi)
    #
    # Bir olcum sayfasinin tek isi dogruyu soylemek; yirmi kat sisik
    # bir "ihlal" sayisi, bakan kisiyi sorunun oraya bakmaya
    # degmeyecegine ikna eder.
    izgara_disi = 0
    for m in re.finditer(
            r"\b(padding|margin|gap|row-gap|column-gap)[a-z-]*\s*:"
            r"([^;{}]+);", css):
        for v in re.findall(r"(\d+)px", m.group(2)):
            # 2 ve altI kenarlik/cizgi payi, olcek disi sayilmiyor.
            if int(v) > 2 and int(v) % 2:
                izgara_disi += 1
    return {
        "punto_kullanim": len(re.findall(r"var\(--p-", css)),
        "bosluk_kullanim": len(re.findall(r"var\(--b-", css)),
        "izgara_disi": izgara_disi,
        "satir": len(ham.splitlines()),
    }
