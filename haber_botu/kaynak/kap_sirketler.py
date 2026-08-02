"""BIST sirket kayit defteri -- KAP'tan cikarilir.

/tr/bist-sirketler sayfasi sunucu tarafinda islenip veriyi HTML'e gomuyor.
Next.js "flight" bicimindeki `self.__next_f.push(...)` parcalarinin icinde
sirket nesneleri duz JSON olarak duruyor:

    {"mkkMemberOid": "...", "kapMemberTitle": "...", "stockCode": "THYAO",
     "cityName": "...", "kapMemberType": "IGS"}

`mkkMemberOid` bu isin anahtari: KAP'in dahili sirket kimligi. Bir sirketin
bildirimlerine ve finansal tablolarina bu kimlikle ulasiliyor.

Cikti: sirketler.json -- hisse kodundan KAP kimligine esleme.

Calistirmak icin:
    python kap_sirketler.py            # onbellekten uret
    python kap_sirketler.py --yenile   # KAP'tan yeniden indir
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import asdict, dataclass

import httpx

TABAN = "https://www.kap.org.tr"
KOK = pathlib.Path(__file__).parent
ONBELLEK = KOK / "_onbellek"
CIKTI = KOK / "sirketler.json"

BASLIKLAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


@dataclass(frozen=True)
class Sirket:
    kod: str  # BIST hisse kodu, orn. THYAO
    unvan: str  # ticari unvan
    kap_kimlik: str  # mkkMemberOid -- KAP dahili kimligi
    sehir: str
    uye_turu: str  # IGS = islem goren sirket
    denetci: str


def _getir(yol: str, yenile: bool = False) -> str:
    ONBELLEK.mkdir(exist_ok=True)
    dosya = ONBELLEK / (re.sub(r"[^a-z0-9]+", "-", yol.lower()).strip("-") + ".html")

    if dosya.exists() and not yenile:
        return dosya.read_text(encoding="utf-8")

    with httpx.Client(headers=BASLIKLAR, timeout=45.0, follow_redirects=True) as c:
        y = c.get(f"{TABAN}{yol}")
        y.raise_for_status()
    dosya.write_text(y.text, encoding="utf-8")
    return y.text


def _alan(blok: str, ad: str) -> str:
    """Tek bir JSON alanini ceker. Bulunamazsa bos dizge.

    Alan sirasi sayfa surumune gore degisebildigi icin her alani ayri
    ariyoruz -- tek bir buyuk desene guvenmek kirilgan olurdu.
    """
    m = re.search(rf'"{ad}"\s*:\s*"((?:[^"\\]|\\.)*)"', blok)
    if not m:
        return ""
    return m.group(1).replace('\\"', '"').replace("\\\\", "\\").strip()


def ayikla(html: str) -> list[Sirket]:
    """Gomulu JSON'dan sirket nesnelerini cikarir.

    Next.js flight bicimini tam ayristirmak yerine sirket nesnelerini
    dogrudan ariyoruz. Bicim degisse bile alanlar ayni kaldigi surece
    calisir; tam ayristirici her surum degisikliginde kirilirdi.
    """
    # Kacisli tirnaklar cozulmeden alan araması yapmak zor
    duz = html.replace('\\"', '"')

    sirketler: dict[str, Sirket] = {}
    for m in re.finditer(r'\{[^{}]*"mkkMemberOid"[^{}]*\}', duz):
        blok = m.group(0)
        ham_kod = _alan(blok, "stockCode").upper()
        kimlik = _alan(blok, "mkkMemberOid")
        unvan = _alan(blok, "kapMemberTitle")

        # Hisse kodu olmayan kayitlar islem gormeyen kuruluslar (fonlar,
        # araci kurumlar). Faz 1 icin islem goren sirketler yeterli.
        if not ham_kod or not kimlik or not unvan:
            continue

        # Bazi sirketlerin birden fazla hisse kodu var ve alan virgulle
        # ayrilmis geliyor: "A1CAP, ACP" ya da "ADB, ADBNK". Her kodu ayri
        # kaydediyoruz -- aksi halde "GARAN" gibi kodlar defterde hic
        # bulunmuyor, cunku kayit "GARAN, TGB" olarak duruyor.
        for kod in (p.strip() for p in ham_kod.split(",")):
            if not kod:
                continue
            sirketler.setdefault(
                kod,
                Sirket(
                    kod=kod,
                    unvan=unvan,
                    kap_kimlik=kimlik,
                    sehir=_alan(blok, "cityName"),
                    uye_turu=_alan(blok, "kapMemberType"),
                    denetci=_alan(blok, "relatedMemberTitle"),
                ),
            )

    return sorted(sirketler.values(), key=lambda s: s.kod)


def yukle() -> dict[str, Sirket]:
    """Kaydedilmis defteri okur. Hisse kodundan Sirket'e esleme dondurur."""
    if not CIKTI.exists():
        raise FileNotFoundError(
            f"{CIKTI.name} yok. Once 'python kap_sirketler.py' calistirin."
        )
    ham = json.loads(CIKTI.read_text(encoding="utf-8"))
    return {k: Sirket(**v) for k, v in ham["sirketler"].items()}


def main(yenile: bool) -> int:
    print("BIST sirket defteri cikariliyor")
    html = _getir("/tr/bist-sirketler", yenile=yenile)
    print(f"  kaynak: {len(html):,} karakter")

    sirketler = ayikla(html)
    if not sirketler:
        print("  HATA: hicbir sirket bulunamadi -- sayfa yapisi degismis olabilir")
        return 1

    CIKTI.write_text(
        json.dumps(
            {
                "kaynak": f"{TABAN}/tr/bist-sirketler",
                "sirket_sayisi": len(sirketler),
                "sirketler": {s.kod: asdict(s) for s in sirketler},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"  {len(sirketler)} sirket bulundu -> {CIKTI.name}")
    print("\n  ilk on kayit:")
    for s in sirketler[:10]:
        print(f"    {s.kod:<8} {s.unvan[:44]:<44} {s.kap_kimlik}")

    # Bilinen sirketlerle dogrulama
    print("\n  dogrulama:")
    for kod in ("THYAO", "GARAN", "ASELS", "EREGL"):
        s = next((x for x in sirketler if x.kod == kod), None)
        print(f"    {kod}: {s.unvan if s else 'BULUNAMADI'}")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="KAP BIST sirket defteri")
    a.add_argument("--yenile", action="store_true", help="KAP'tan yeniden indir")
    sys.exit(main(a.parse_args().yenile))
