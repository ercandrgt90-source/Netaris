"""Bir metin dosyasini yayin oncesi ifade taramasindan gecirir.

Kullanim:  python tara_dosya.py ornek_cikti.md

Cikis kodu 0 ise icerik yayinlanabilir, 1 ise engellenmistir. Bu sayede
yayin hattinda dogrudan kapi olarak kullanilabilir.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "ai"))

import guvenlik  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("kullanim: python tara_dosya.py <dosya>")
        return 2

    yol = pathlib.Path(argv[1])
    if not yol.exists():
        print(f"dosya bulunamadi: {yol}")
        return 2

    metin = yol.read_text(encoding="utf-8-sig")
    print(f"Dosya: {yol.name}  ({len(metin.split())} kelime)")
    print("-" * 60)
    print(guvenlik.rapor(metin))

    tamam, _ = guvenlik.yayinlanabilir(metin)
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
