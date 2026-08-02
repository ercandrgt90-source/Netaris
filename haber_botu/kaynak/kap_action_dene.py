"""Toplanan Server Action kimliklerini dener.

Next.js Server Action cagrisi:

    POST /tr/bildirim-sorgu
    Next-Action: <kimlik>
    Content-Type: text/plain;charset=UTF-8
    govde: [arguman1, arguman2, ...]        <- JSON dizi

Yanit React Flight akisidir (text/x-component). Kimlik gecersizse Next.js
genellikle sayfayi yeniden isler ya da hata dondurur; gecerliyse eylemin
ciktisi akista yer alir.

Once bos argumanla deniyoruz: gecerli kimlik "eksik arguman" turu bir hata
verir, gecersiz kimlik bambaska davranir. Bu ayrim kimligi dogrulamaya
yeter.

Calistirmak icin:  python kap_action_dene.py
"""

from __future__ import annotations

import json
import pathlib
import time

import httpx

TABAN = "https://www.kap.org.tr"
SAYFA = "/tr/bildirim-sorgu"
KOK = pathlib.Path(__file__).parent

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/x-component, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Content-Type": "text/plain;charset=UTF-8",
    "Origin": TABAN,
    "Referer": f"{TABAN}{SAYFA}",
}

# Bildirim sorgusunun bekleyebilecegi filtre. Alan adlari KAP'in eski
# uc noktasindan biliniyor.
FILTRE = {
    "fromDate": "2026-01-01",
    "toDate": "2026-07-31",
    "disclosureClass": "FR",
    "memberTypeList": ["IGS"],
    "mkkMemberOidList": [],
    "subjectList": [],
    "term": "",
    "year": "",
    "period": "",
    "fromSrc": "N",
}

BEKLEME = 2.0


def _ozetle(y: httpx.Response) -> str:
    tur = y.headers.get("content-type", "?").split(";")[0]
    govde = y.text
    ipuclari = []
    for isaret in ("disclosureIndex", "stockCode", "publishDate", "basic",
                   "error", "Error", "NEXT_REDIRECT", "kapTitle"):
        if isaret in govde:
            ipuclari.append(isaret)
    return f"{tur} | {len(govde):,} krk | ipucu: {ipuclari or '-'}"


def dene(istemci: httpx.Client, kimlik: str, argumanlar: list) -> bool:
    try:
        y = istemci.post(
            SAYFA,
            headers={"Next-Action": kimlik},
            content=json.dumps(argumanlar, ensure_ascii=False),
        )
    except httpx.TimeoutException:
        print(f"    ZAMAN ASIMI")
        return False
    except httpx.HTTPError as e:
        print(f"    {type(e).__name__}")
        return False

    print(f"    {y.status_code}  {_ozetle(y)}")

    if "disclosureIndex" in y.text or "stockCode" in y.text:
        ornek = KOK / f"action_yanit_{kimlik[:8]}.txt"
        ornek.write_text(y.text, encoding="utf-8")
        print(f"    >>> VERI GELDI, kaydedildi: {ornek.name}")
        return True
    time.sleep(BEKLEME)
    return False


def main() -> None:
    aday_dosya = KOK / "action_adaylari.txt"
    if not aday_dosya.exists():
        print("action_adaylari.txt yok. Once kap_action.py calistirin.")
        return

    kimlikler = [s.strip() for s in aday_dosya.read_text().splitlines() if s.strip()]
    print(f"{len(kimlikler)} aday kimlik deneniyor\n")

    basarili = []
    with httpx.Client(
        base_url=TABAN, headers=BASLIKLAR, timeout=30.0, follow_redirects=False
    ) as istemci:
        for kimlik in kimlikler:
            print(f"  {kimlik}")
            print("   [bos arguman]")
            if dene(istemci, kimlik, []):
                basarili.append(kimlik)
                continue
            print("   [filtre argumani]")
            if dene(istemci, kimlik, [FILTRE]):
                basarili.append(kimlik)

    print("\n" + "=" * 60)
    if basarili:
        print("VERI DONDUREN KIMLIKLER:")
        for k in basarili:
            print(f"  {k}")
    else:
        print("Hicbir kimlik bildirim verisi dondurmedi.")


if __name__ == "__main__":
    main()
