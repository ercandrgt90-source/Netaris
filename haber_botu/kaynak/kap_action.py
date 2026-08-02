"""KAP'in Next.js Server Action kimliklerini toplar.

Next.js App Router'da sunucu fonksiyonlari REST uc noktasi olarak degil,
"Server Action" olarak cagrilir:

    POST <sayfa adresi>
    Next-Action: <40 haneli onaltilik kimlik>
    govde: [arguman1, arguman2, ...]   (JSON dizi)

Kimlikler istemci JS parcalarina gomulu olur. Genellikle
`createServerReference("<hex40>", ...)` ya da benzeri bir cagri icinde
gecerler.

Bu betik bildirim sorgu sayfasinin JS parcalarini indirip aday kimlikleri
cikarir. Sonraki adim onlari denemek.

Calistirmak icin:  python kap_action.py
"""

from __future__ import annotations

import pathlib
import re
import time
from collections import defaultdict

import httpx

TABAN = "https://www.kap.org.tr"
KOK = pathlib.Path(__file__).parent
ONBELLEK = KOK / "_onbellek" / "app_js"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Next.js action kimligi: 40 haneli onaltilik (bazi surumlerde 64)
HEX40 = re.compile(r"\b([a-f0-9]{40})\b")
HEX64 = re.compile(r"\b([a-f0-9]{64})\b")

# Kimligin gectigi tipik baglamlar
BAGLAMLAR = (
    "createServerReference",
    "$ACTION_ID",
    "callServer",
    "findSourceMapURL",
)

SAYFALAR = {
    "bildirim-sorgu": "/tr/bildirim-sorgu",
    "kalem-karsilastirma": "/tr/kalem-karsilastirma",
}


def indir(istemci: httpx.Client, url: str, ad: str) -> str:
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    dosya = ONBELLEK / ad
    if dosya.exists():
        return dosya.read_text(encoding="utf-8", errors="replace")
    y = istemci.get(url)
    y.raise_for_status()
    dosya.write_text(y.text, encoding="utf-8")
    time.sleep(0.7)
    return y.text


def main() -> None:
    print("KAP Server Action kimlik avi\n")

    # kimlik -> nerede gecti
    adaylar: dict[str, set[str]] = defaultdict(set)
    baglamli: dict[str, set[str]] = defaultdict(set)

    with httpx.Client(headers=BASLIKLAR, timeout=45.0, follow_redirects=True) as istemci:
        for ad, yol in SAYFALAR.items():
            print(f"[{ad}] {yol}")
            html = istemci.get(f"{TABAN}{yol}").text
            time.sleep(0.7)

            # Sayfanin kendisinde de kimlik gecebilir
            duz = html.replace("\\", "")
            for desen in (HEX40, HEX64):
                for m in desen.finditer(duz):
                    adaylar[m.group(1)].add(f"{ad}:html")

            betikler = re.findall(r'<script[^>]+src="([^"]+)"', html)
            print(f"  {len(betikler)} betik")

            for b in betikler:
                url = b if b.startswith("http") else f"{TABAN}{b}"
                dosya_adi = re.sub(r"[^a-zA-Z0-9]+", "_", b)[-80:] + ".js"
                try:
                    js = indir(istemci, url, dosya_adi)
                except httpx.HTTPError:
                    continue

                for desen in (HEX40, HEX64):
                    for m in desen.finditer(js):
                        kimlik = m.group(1)
                        adaylar[kimlik].add(f"{ad}:{dosya_adi[:26]}")

                        # Kimligin etrafinda action isareti var mi
                        a, s = max(0, m.start() - 220), m.start() + 220
                        cevre = js[a:s]
                        for isaret in BAGLAMLAR:
                            if isaret in cevre:
                                baglamli[kimlik].add(isaret)

    print(f"\n{'=' * 68}")
    print(f"{len(adaylar)} aday onaltilik dizge bulundu")
    print(f"{len(baglamli)} tanesi action baglaminda geciyor")
    print("=" * 68)

    if baglamli:
        print("\nGUCLU ADAYLAR (action baglaminda):")
        for kimlik, isaretler in sorted(baglamli.items()):
            nerede = ", ".join(sorted(adaylar[kimlik]))[:60]
            print(f"  {kimlik}")
            print(f"      baglam: {', '.join(sorted(isaretler))}")
            print(f"      kaynak: {nerede}")
    else:
        print("\nAction baglaminda kimlik bulunamadi.")
        print("En sik gecen 15 onaltilik dizge (baglamsiz):")
        for kimlik in list(adaylar)[:15]:
            print(f"  {kimlik}  <- {', '.join(sorted(adaylar[kimlik]))[:50]}")

    # Sonraki adim icin kaydet
    (KOK / "action_adaylari.txt").write_text(
        "\n".join(sorted(baglamli) or sorted(adaylar)), encoding="utf-8"
    )
    print(f"\nkaydedildi: action_adaylari.txt")


if __name__ == "__main__":
    main()
