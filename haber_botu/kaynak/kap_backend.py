"""KAP arka uc sunucusu sondasi.

Sirket ozet sayfasinda su ortaya cikti:

    "CLIENT_BASE_URL": "https://www.kap.org.tr"
    "SERVER_BASE_URL": "https://kapsitebackend.mkk.com.tr"

API www.kap.org.tr'de degil, ayri bir sunucuda. Onceki butun /tr/api/
tahminlerinin 404 donmesinin sebebi bu.

Bu betik iki is yapar:
  1. Indirilmis JS paketlerinde arka uc yollarini arar
  2. Bulunan yollari arka uca karsi dener

Calistirmak icin:  python kap_backend.py
"""

from __future__ import annotations

import json
import pathlib
import re
import time
from collections import Counter

import httpx

ARKA_UC = "https://kapsitebackend.mkk.com.tr"
ON_YUZ = "https://www.kap.org.tr"
KOK = pathlib.Path(__file__).parent
ONBELLEK = KOK / "_onbellek"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Origin": ON_YUZ,
    "Referer": f"{ON_YUZ}/",
}

BEKLEME = 1.2
ZAMAN_ASIMI = 25.0


def yollari_ara() -> list[str]:
    """Onbellekteki tum dosyalarda arka uca gidebilecek yollari arar."""
    adaylar: Counter[str] = Counter()

    # Hem HTML hem JS dosyalarina bak
    dosyalar = list(ONBELLEK.glob("*.html")) + list((ONBELLEK / "js").glob("*.js"))
    print(f"  {len(dosyalar)} onbellek dosyasi taraniyor")

    for d in dosyalar:
        try:
            icerik = d.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        icerik = icerik.replace('\\"', '"').replace("\\/", "/")

        # kapsitebackend gecen yerlerin etrafindaki yollar
        for m in re.finditer(r"kapsitebackend\.mkk\.com\.tr(/[a-zA-Z0-9._~/-]*)", icerik):
            if m.group(1) and m.group(1) != "/":
                adaylar[m.group(1)] += 1

        # api/ ile baslayan yollar (arka uca gidiyor olabilir)
        for m in re.finditer(r'["\'`](/(?:api|v\d)/[a-zA-Z0-9._~/-]+)["\'`]', icerik):
            adaylar[m.group(1)] += 1

    return [y for y, _ in adaylar.most_common()]


def dene(istemci: httpx.Client, yol: str, yontem: str = "GET", govde: dict | None = None) -> bool:
    try:
        y = istemci.post(yol, json=govde or {}) if yontem == "POST" else istemci.get(yol)
    except httpx.TimeoutException:
        print(f"     {yontem:4} {yol:<52} ZAMAN ASIMI")
        return False
    except httpx.HTTPError as e:
        print(f"     {yontem:4} {yol:<52} {type(e).__name__}")
        return False

    isaret = "OK " if y.status_code == 200 else "   "
    print(f"  {isaret}{yontem:4} {yol:<52} {y.status_code}  {len(y.content):,} bayt")

    if y.status_code == 200 and y.content:
        tur = y.headers.get("content-type", "").split(";")[0]
        if "json" in tur:
            try:
                veri = y.json()
                if isinstance(veri, list):
                    print(f"       JSON dizi, {len(veri)} oge")
                    if veri:
                        print(f"       ilk: {json.dumps(veri[0], ensure_ascii=False)[:200]}")
                elif isinstance(veri, dict):
                    print(f"       JSON nesne: {list(veri.keys())[:14]}")
                return True
            except ValueError:
                pass
        print(f"       {tur} | {y.text[:160]}")
    time.sleep(BEKLEME)
    return y.status_code == 200


def main() -> None:
    print(f"KAP arka uc sondasi -- {ARKA_UC}\n")

    print("[1] Onbellekte yol arastirmasi")
    bulunan = yollari_ara()
    if bulunan:
        print(f"  {len(bulunan)} aday yol bulundu:")
        for y in bulunan[:25]:
            print(f"    {y}")
    else:
        print("  onbellekte yol bulunamadi -- tahminle devam")

    print(f"\n[2] Arka uc denemeleri")
    with httpx.Client(
        base_url=ARKA_UC, headers=BASLIKLAR, timeout=ZAMAN_ASIMI, follow_redirects=True
    ) as istemci:
        # Once kok ve saglik kontrolu
        for yol in ("/", "/actuator/health", "/swagger-ui/index.html", "/v3/api-docs"):
            dene(istemci, yol)

        # Bulunan yollar
        for yol in bulunan[:15]:
            dene(istemci, yol)


if __name__ == "__main__":
    main()
