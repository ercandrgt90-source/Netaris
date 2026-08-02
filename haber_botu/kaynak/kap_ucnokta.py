"""KAP'in gercek API uc noktalarini JS paketlerinden cikarir.

Uc nokta tahmin etmek verimsiz: on tahminin onu 404 dondu. Uygulama
tarayicida calisiyorsa, cagirdigi adresler JS paketlerinin icinde duz metin
olarak duruyor demektir. Paketleri indirip icindeki API yollarini aramak,
tahmin etmekten cok daha kesin.

Iki is yapar:
  1. Sayfadaki <script src> paketlerini toplar ve indirir
  2. Paketlerin icinde API yolu benzeri dizgeleri arar

Calistirmak icin:  python kap_ucnokta.py
"""

from __future__ import annotations

import pathlib
import re
import time
from collections import Counter

import httpx

TABAN = "https://www.kap.org.tr"
KOK = pathlib.Path(__file__).parent
ONBELLEK = KOK / "_onbellek" / "js"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# API yolu gibi gorunen dizgeler. KAP'in uc noktalari /api/ ile basliyor
# ya da acikca isimlendirilmis (memberDisclosureQuery gibi).
YOL_DESENI = re.compile(r'["\'`](/[a-zA-Z0-9._~/-]*api[a-zA-Z0-9._~/-]*)["\'`]')
SORGU_DESENI = re.compile(r'["\'`]([a-zA-Z][a-zA-Z0-9]*(?:Query|Search|List|Detail|Item|Financial|Report)[a-zA-Z0-9]*)["\'`]')


def getir(url: str, ad: str) -> str:
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    dosya = ONBELLEK / ad
    if dosya.exists():
        return dosya.read_text(encoding="utf-8", errors="replace")

    with httpx.Client(headers=BASLIKLAR, timeout=45.0, follow_redirects=True) as c:
        y = c.get(url)
        y.raise_for_status()
    dosya.write_text(y.text, encoding="utf-8")
    time.sleep(0.8)
    return y.text


def main() -> None:
    print("KAP uc nokta arastirmasi\n")

    sayfalar = {
        "bist-sirketler": "/tr/bist-sirketler",
        "kalem-karsilastirma": "/tr/kalem-karsilastirma",
    }

    tum_betikler: set[str] = set()

    for ad, yol in sayfalar.items():
        onbellek_html = KOK / "_onbellek" / f"tr-{ad}.html"
        if onbellek_html.exists():
            html = onbellek_html.read_text(encoding="utf-8")
        else:
            with httpx.Client(headers=BASLIKLAR, timeout=45.0, follow_redirects=True) as c:
                y = c.get(f"{TABAN}{yol}")
                y.raise_for_status()
            html = y.text
            onbellek_html.parent.mkdir(parents=True, exist_ok=True)
            onbellek_html.write_text(html, encoding="utf-8")

        betikler = re.findall(r'<script[^>]+src="([^"]+)"', html)
        print(f"[{ad}] {len(html):,} karakter, {len(betikler)} betik")

        # Sayfanin kendi icinde de API yolu gecebilir
        for m in YOL_DESENI.finditer(html):
            tum_betikler.add(("SAYFA", m.group(1)))

        for b in betikler:
            tum_betikler.add(("BETIK", b))

    js_yollari = sorted({b for tur, b in tum_betikler if tur == "BETIK"})
    sayfa_yollari = sorted({b for tur, b in tum_betikler if tur == "SAYFA"})

    if sayfa_yollari:
        print(f"\n  sayfa HTML'inde gecen api benzeri yollar ({len(sayfa_yollari)}):")
        for y in sayfa_yollari[:20]:
            print(f"    {y}")

    print(f"\n[JS paketleri] {len(js_yollari)} benzersiz betik indiriliyor")
    bulunanlar: Counter[str] = Counter()
    sorgular: Counter[str] = Counter()
    indirilen = 0

    for i, yol in enumerate(js_yollari):
        url = yol if yol.startswith("http") else f"{TABAN}{yol}"
        ad = re.sub(r"[^a-zA-Z0-9]+", "_", yol)[-90:] + ".js"
        try:
            icerik = getir(url, ad)
        except httpx.HTTPError:
            continue
        indirilen += 1
        for m in YOL_DESENI.finditer(icerik):
            bulunanlar[m.group(1)] += 1
        for m in SORGU_DESENI.finditer(icerik):
            sorgular[m.group(1)] += 1

    print(f"  {indirilen} paket indirildi\n")

    print("=" * 66)
    print("BULUNAN API YOLLARI")
    print("=" * 66)
    if bulunanlar:
        for yol, n in bulunanlar.most_common(40):
            print(f"  {n:>4}x  {yol}")
    else:
        print("  hicbir api yolu bulunamadi")

    print("\n" + "=" * 66)
    print("SORGU/RAPOR BENZERI ADLAR")
    print("=" * 66)
    for ad, n in sorgular.most_common(30):
        print(f"  {n:>4}x  {ad}")


if __name__ == "__main__":
    main()
