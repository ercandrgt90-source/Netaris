"""KAP sayfalarina gomulu veriyi bulur.

Sonda, /tr/bist-sirketler adresinin 1,5 MB dondugunu gosterdi. Bos bir
JavaScript kabugu bu kadar buyuk olmaz -- veri sunucu tarafinda islenip
sayfaya gomuluyor demektir. Modern Next.js uygulamalari bunu ya
`__NEXT_DATA__` etiketinde ya da `self.__next_f.push(...)` parcalarinda
yapar.

Bu betik veriyi bulmaya calisir: bilinen bir hisse kodunu (THYAO) arayip
etrafindaki bicimi gosterir. Bicim anlasilinca ayristirici yazilabilir.
"""

from __future__ import annotations

import pathlib
import re

import httpx

TABAN = "https://www.kap.org.tr"
ONBELLEK = pathlib.Path(__file__).parent / "_onbellek"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def getir(yol: str, yenile: bool = False) -> str:
    """Sayfayi indirir ve diske onbellekler.

    Onbellek onemli: ayni sayfayi tekrar tekrar indirmek hem yavas hem de
    KAP sunucusuna gereksiz yuk. Gelistirirken tek indirme yetiyor.
    """
    ONBELLEK.mkdir(exist_ok=True)
    ad = re.sub(r"[^a-z0-9]+", "-", yol.lower()).strip("-") + ".html"
    dosya = ONBELLEK / ad

    if dosya.exists() and not yenile:
        print(f"  onbellekten: {dosya.name} ({dosya.stat().st_size:,} bayt)")
        return dosya.read_text(encoding="utf-8")

    print(f"  indiriliyor: {TABAN}{yol}")
    with httpx.Client(headers=BASLIKLAR, timeout=45.0, follow_redirects=True) as c:
        y = c.get(f"{TABAN}{yol}")
        y.raise_for_status()
    dosya.write_text(y.text, encoding="utf-8")
    print(f"  kaydedildi: {dosya.name} ({len(y.text):,} karakter)")
    return y.text


def yapi_incele(html: str) -> None:
    """Sayfanin veri tasima bicimini raporlar."""
    print("\n  --- veri tasiyicilari ---")

    next_data = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S
    )
    print(f"  __NEXT_DATA__ etiketi : {'VAR (' + str(len(next_data.group(1))) + ' karakter)' if next_data else 'yok'}")

    parcalar = re.findall(r"self\.__next_f\.push\(", html)
    print(f"  self.__next_f.push()  : {len(parcalar)} parca")

    betikler = re.findall(r"<script[^>]*>", html)
    print(f"  toplam <script>       : {len(betikler)}")


def kod_ara(html: str, kodlar: tuple[str, ...] = ("THYAO", "GARAN", "ASELS")) -> None:
    """Bilinen hisse kodlarini arayip etrafindaki bicimi gosterir."""
    print("\n  --- hisse kodu araniyor ---")
    for kod in kodlar:
        yerler = [m.start() for m in re.finditer(kod, html)]
        if not yerler:
            print(f"  {kod}: bulunamadi")
            continue
        print(f"  {kod}: {len(yerler)} kez geciyor")
        yer = yerler[0]
        baglam = html[max(0, yer - 260) : yer + 260]
        baglam = baglam.replace("\\", "").replace("\n", " ")
        print(f"       ...{baglam}...")
        break


def main() -> None:
    print("KAP gomulu veri arastirmasi\n")
    print("[/tr/bist-sirketler]")
    html = getir("/tr/bist-sirketler")
    yapi_incele(html)
    kod_ara(html)


if __name__ == "__main__":
    main()
