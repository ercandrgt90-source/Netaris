"""Kumulatif (2026/6) bilanco sayfalarini ceyrekligi VARSA kaldirir.

NEDEN
-----
KAP donemleri KUMULATIF: "2026/6" yilin ilk YARISI demek, ikinci
ceyrek degil. Sayfalar bir donem bu etiketle uretildi ve okur
"2026/6 bilanco analizi" basligini gorup ikinci ceyregi sandi.

Uretim ceyreklige cevrildi; bu arac ESKI kumulatif sayfalari
topluyor.

NEDEN HEPSI DEGIL
-----------------
Olculdu (2026-08-21): 144 kumulatif sayfa var ama yalnizca 33'unun
ceyreklik karsiligi uretilmis. Kalan 111 sirket icin ceyreklik sayfa
HENUZ YOK.

Hepsini silmek, 111 sirketi sayfasiz birakirdi -- yani bir bicim
sorununu icerik kaybina cevirmek. Arac yalnizca KARSILIGI OLANI
siliyor; kalanlar sonraki uretim kosularinda degisiyor ve o zaman
tekrar calistirilabiliyor.

Kosu basina ~60 sayfa uretiliyor, yani 111 sirket icin iki kosu daha
gerekiyor.
"""

from __future__ import annotations

import argparse
import pathlib
import re

KOK = pathlib.Path(__file__).resolve().parent.parent
ANALIZ = KOK / "site" / "icerik" / "analizler"

#: Kaldirilacak donem etiketi. Kumulatif bicim: "YYYY/A" (A = ay).
KUMULATIF = re.compile(r"^\d{4}/\d{1,2}$")


def _alan(metin: str, ad: str) -> str:
    m = re.search(rf"^{ad}:\s*(.+)$", metin, re.M)
    return m.group(1).strip() if m else ""


def tara() -> tuple[dict[str, list], dict[str, list]]:
    """Bilanco sayfalarini kumulatif / ceyreklik diye ayirir."""
    kum: dict[str, list] = {}
    cey: dict[str, list] = {}
    for p in ANALIZ.rglob("*.md"):
        t = p.read_text(encoding="utf-8", errors="replace")
        # Bas kisma bakiliyor: govdede gecen "bilanço" kelimesi bir
        # haber sayfasini yanlislikla bilanco saymaya yeter.
        if "ilanço" not in t[:900]:
            continue
        kod, donem = _alan(t, "kod"), _alan(t, "donem")
        if not kod or not donem:
            continue
        hedef = kum if KUMULATIF.match(donem) else cey
        hedef.setdefault(kod, []).append(p)
    return kum, cey


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true",
                    help="olcmekle kalma, gercekten sil")
    n = ap.parse_args()

    kum, cey = tara()
    silinecek = [(k, v) for k, v in kum.items() if k in cey]
    kalan = sorted(k for k in kum if k not in cey)

    print(f"kumulatif sayfa      : {sum(len(v) for v in kum.values())}")
    print(f"ceyreklik sayfa      : {sum(len(v) for v in cey.values())}")
    print(f"karsiligi VAR (silinir): {len(silinecek)}")
    print(f"karsiligi YOK (kalir)  : {len(kalan)}")
    if kalan:
        print(f"  ornek: {', '.join(kalan[:10])}")
        print(f"  -> bunlar icin ~{-(-len(kalan) // 60)} uretim kosusu daha")

    if not silinecek:
        print("\nSilinecek sayfa yok.")
        return 0

    if not n.uygula:
        print("\n(olcum modu -- silmek icin --uygula)")
        for kod, yollar in silinecek[:6]:
            print(f"  {yollar[0].name}  ->  {cey[kod][0].name}")
        return 0

    adet = 0
    for kod, yollar in silinecek:
        for p in yollar:
            p.unlink()
            adet += 1
    print(f"\n{adet} kumulatif sayfa silindi "
          f"({len(silinecek)} sirketin ceyrekligi yerini aldi).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
