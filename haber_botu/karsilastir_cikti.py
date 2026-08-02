"""Uretilen ciktilarin ayni bolumlerini yan yana koyar.

Model secimi maliyetle degil, analiz kalitesiyle verilmeli. Bu betik ayni
bilanco icin farkli modellerin/ayarlarin yazdigi metni bolum bolum
karsilastirir -- ozellikle "Kar nereden geldi" ve "Nakit" bolumleri, cunku
urunun farki orada.

Kullanim:
    python karsilastir_cikti.py "Kâr nereden geldi"
"""

from __future__ import annotations

import pathlib
import re
import sys

DOSYALAR = [
    ("ciktilar/ORNEK-2025-12.md", "OPUS 5 / high"),
    ("ciktilar/ORNEK-effort-medium.md", "OPUS 5 / medium"),
    ("ciktilar/ORNEK-sonnet5.md", "SONNET 5 / medium"),
]


def bolum(yol: pathlib.Path, baslik: str) -> str:
    if not yol.exists():
        return "(dosya yok)"
    metin = yol.read_text(encoding="utf-8")
    desen = re.compile(r"^##\s*" + re.escape(baslik) + r"[^\n]*\n(.*?)(?=^##\s|\Z)",
                       re.M | re.S)
    m = desen.search(metin)
    return " ".join(m.group(1).split()) if m else "(bolum bulunamadi)"


def main() -> int:
    baslik = sys.argv[1] if len(sys.argv) > 1 else "Kâr nereden geldi"
    sinir = int(sys.argv[2]) if len(sys.argv) > 2 else 850
    kok = pathlib.Path(__file__).parent

    for yol, etiket in DOSYALAR:
        print("=" * 72)
        print(etiket)
        print("=" * 72)
        icerik = bolum(kok / yol, baslik)
        print(icerik[:sinir] + ("..." if len(icerik) > sinir else ""))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
