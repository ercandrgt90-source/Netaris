"""KAP veri erisim noktasi sondasi.

Amac: hangi uc noktalarin calistigini, ne dondurdugunu ve yapilandirilmis
veri verip vermediklerini olcmek. Kazima yazmadan once haritayi cikarmak.

KAP, sermaye piyasasi mevzuati geregi kamuya aciklama yapilan resmi
platformdur; buradaki veriler tam da kamuya aciklanmak uzere yayimlanir.
Yine de nazik davraniyoruz: istekler arasi bekleme var, es zamanli istek
yok, tarayici gibi davranan basliklar gonderiliyor.

Calistirmak icin:  python kap_sonda.py
"""

from __future__ import annotations

import json
import time

import httpx

TABAN = "https://www.kap.org.tr"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Referer": f"{TABAN}/tr/bildirim-sorgu",
    "Origin": TABAN,
}

# Istekler arasi bekleme -- sunucuyu zorlamamak icin
BEKLEME = 1.5
ZAMAN_ASIMI = 30.0


def _ozet(yanit: httpx.Response, sinir: int = 220) -> str:
    tur = yanit.headers.get("content-type", "?").split(";")[0]
    govde = yanit.text
    if "json" in tur:
        try:
            veri = json.loads(govde)
            if isinstance(veri, list):
                return f"JSON dizi, {len(veri)} oge | ilk: {json.dumps(veri[0], ensure_ascii=False)[:sinir] if veri else '-'}"
            if isinstance(veri, dict):
                return f"JSON nesne, anahtarlar: {list(veri.keys())[:12]}"
        except json.JSONDecodeError:
            pass
    return govde[:sinir].replace("\n", " ")


def dene(istemci: httpx.Client, yontem: str, yol: str, govde: dict | None = None) -> None:
    etiket = f"{yontem:4} {yol}"
    try:
        if yontem == "GET":
            y = istemci.get(yol)
        else:
            y = istemci.post(yol, json=govde or {})
    except httpx.TimeoutException:
        print(f"  {etiket}\n       ZAMAN ASIMI ({ZAMAN_ASIMI:.0f}s)")
        return
    except httpx.HTTPError as e:
        print(f"  {etiket}\n       HATA: {type(e).__name__}")
        return

    isaret = "OK " if y.status_code == 200 else "   "
    print(f"  {isaret}{etiket}  -> {y.status_code}  {len(y.content):,} bayt")
    if y.status_code == 200 and y.content:
        print(f"       {_ozet(y)}")
    time.sleep(BEKLEME)


def main() -> None:
    print(f"KAP sondasi -- {TABAN}\n")

    with httpx.Client(
        base_url=TABAN,
        headers=BASLIKLAR,
        timeout=ZAMAN_ASIMI,
        follow_redirects=True,
    ) as istemci:
        print("[1] Sirket listesi uc noktalari")
        for yol in (
            "/tr/api/company/all",
            "/tr/api/member/all",
            "/tr/api/kapMember/all",
            "/tr/api/companies",
            "/tr/api/bist-sirketler",
        ):
            dene(istemci, "GET", yol)

        print("\n[2] Bildirim sorgu")
        dene(
            istemci,
            "POST",
            "/tr/api/memberDisclosureQuery",
            {
                "fromDate": "2026-01-01",
                "toDate": "2026-07-31",
                "disclosureClass": "FR",
                "subjectList": [],
                "memberTypeList": ["IGS"],
                "mkkMemberOidList": [],
                "inactiveMkkMemberOidList": [],
                "bdkReview": "",
                "representativeList": [],
                "term": "",
                "ruleTypeList": [],
                "year": "",
                "fromSrc": "N",
                "srcCategory": "",
                "discIndex": [],
            },
        )

        print("\n[3] Finansal tablo kalem sorgulama")
        for yol in (
            "/tr/api/financialItemComparison",
            "/tr/api/kalem-karsilastirma",
            "/tr/api/financialStatement",
        ):
            dene(istemci, "GET", yol)

        print("\n[4] HTML sayfalari (arayuz nereden besleniyor)")
        for yol in ("/tr/bist-sirketler", "/tr/kalem-karsilastirma"):
            dene(istemci, "GET", yol)


if __name__ == "__main__":
    main()
