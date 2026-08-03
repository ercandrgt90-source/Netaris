"""Kucuk seri grafikleri (sparkline) -- fiyat seridi ve panel icin.

NEDEN DEPODAN
-------------
`gostergeler.json` yalnizca SON degeri tasiyor; bir cizgi cizmek icin seri
gerekiyor. Seri zaten depoda birikiyor (`gosterge` ve `fiyat` tablolari).
Ayrica veri cekmiyoruz -- depo tam da bunun icin kuruldu.

NEDEN INLINE SVG
----------------
Harici bir grafik kitapligi yok ve olmayacak: Artifact/CSP kisiti bir yana,
serit sayfanin EN USTUNDE ve her sayfada var. Oraya bir JS kitapligi koymak
ilk boyamayi geciktirir. Uretilen SVG ~200 bayt ve dogrudan HTML'e gomulu
geliyor; JavaScript kapaliyken de gorunuyor.

RENK KURALI
-----------
Cizgi rengi YONE gore: yukselen yesil, dusen kirmizi. Bu sitede kirmizi ve
yesil YALNIZCA sayisal yon icin ayrilmis durumda; kivilcim de ayni kurala
uyuyor ki okur iki farkli anlam ogrenmek zorunda kalmasin.
"""

from __future__ import annotations

import pathlib
import sqlite3

#: Depo yolu -- haber_botu/netaris.db
DEPO = pathlib.Path(__file__).parent.parent / "haber_botu" / "netaris.db"

#: Kivilcimda gosterilecek en fazla nokta. On dortten fazlasi 46 piksel
#: genislikte ayirt edilemiyor, azi da egilimi gostermiyor.
NOKTA = 14

GENISLIK = 46
YUKSEKLIK = 16

#: Seri duz cizgi oldugunda (butun degerler ayni) bolme sifira dusuyor.
#: O durumda orta yukseklikte duz bir cizgi ciziliyor.
_EN_AZ_ARALIK = 1e-9


def _seri_cek(baglanti: sqlite3.Connection, tablo: str, sutun: str,
              anahtar_sutun: str, anahtar: str) -> list[float]:
    satirlar = baglanti.execute(
        f"SELECT {sutun} FROM {tablo} WHERE {anahtar_sutun} = ? "
        f"ORDER BY tarih DESC LIMIT ?",
        (anahtar, NOKTA),
    ).fetchall()
    # DESC cekip ters cevirmek, LIMIT'in SON noktalari almasini sagliyor.
    return [s[0] for s in reversed(satirlar) if s[0] is not None]


def cizgi(degerler: list[float]) -> str:
    """Seriden inline SVG uretir. Iki noktadan azsa BOS doner.

    Bos donmek onemli: tek noktadan cizilen "grafik" bir bilgi tasimaz ama
    okura egilim varmis izlenimi verir.
    """
    if len(degerler) < 2:
        return ""

    en_az, en_cok = min(degerler), max(degerler)
    aralik = en_cok - en_az
    n = len(degerler)
    adim = GENISLIK / (n - 1)

    if aralik < _EN_AZ_ARALIK:
        noktalar = [f"{i * adim:.1f},{YUKSEKLIK / 2:.1f}" for i in range(n)]
    else:
        # SVG'de y asagi dogru buyur -- deger buyudukce y KUCULMELI.
        # Bir kez ters cizildi ve butun kivilcimlar aynanin icinde gibi
        # gorundu: yukselen seri asagi iniyordu.
        pay = 1.5          # cizgi kalinliginin tasmamasi icin ust/alt bosluk
        yuk = YUKSEKLIK - 2 * pay
        noktalar = [
            f"{i * adim:.1f},{pay + yuk - (d - en_az) / aralik * yuk:.1f}"
            for i, d in enumerate(degerler)
        ]

    yon = "artis" if degerler[-1] >= degerler[0] else "dusus"
    return (
        f'<svg class="kivilcim kivilcim-{yon}" width="{GENISLIK}" '
        f'height="{YUKSEKLIK}" viewBox="0 0 {GENISLIK} {YUKSEKLIK}" '
        f'aria-hidden="true" focusable="false">'
        f'<polyline points="{" ".join(noktalar)}" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def gosterge_kivilcimlari(kodlar: list[str]) -> dict[str, str]:
    """FRED gostergeleri icin kod -> SVG.

    Depo yoksa ya da okunamiyorsa BOS sozluk doner; serit kivilcimsiz ama
    calisir halde basilir. Grafik sus, deger asil bilgi.
    """
    if not DEPO.exists():
        return {}
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            return {
                kod: c
                for kod in kodlar
                if (c := cizgi(_seri_cek(b, "gosterge", "deger", "kod", kod)))
            }
    except sqlite3.Error:
        return {}


def fiyat_kivilcimlari(semboller: list[str]) -> dict[str, str]:
    """Kraken sembolleri icin sembol -> SVG."""
    if not DEPO.exists():
        return {}
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            return {
                s: c
                for s in semboller
                if (c := cizgi(_seri_cek(b, "fiyat", "kapanis", "sembol", s)))
            }
    except sqlite3.Error:
        return {}
