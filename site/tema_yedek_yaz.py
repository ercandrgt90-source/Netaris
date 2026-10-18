# -*- coding: utf-8 -*-
"""Mobil uygulamanin yedek paletini `stil.css`ten yeniden uretir.

    python site/tema_yedek_yaz.py

Ciktiyi `mobil/src/tema-yedek.ts` dosyasina yaziyor. O dosya ELLE
DUZENLENMEZ; `site/test_tema_belirtec.py` dosyanin CSS ile bire bir
ayni oldugunu siniyor ve ayrisirsa kirmiziya donuyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

import tema_belirtec as T                           # noqa: E402

STIL = _KOK / "statik" / "stil.css"
HEDEF = _KOK.parent / "mobil" / "src" / "tema-yedek.ts"


def main() -> int:
    if not STIL.is_file():
        print(f"stil.css bulunamadi: {STIL}")
        return 1
    icerik = T.ts_yedek(STIL)
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    # `newline=""` bilincli: dosya LF ile yaziliyor ve Windows'ta
    # CRLF'e cevrilmiyor. Cevrilse sinamanin bire bir karsilastirmasi
    # her makinede baska sonuc verirdi.
    HEDEF.write_text(icerik, encoding="utf-8", newline="")
    print(f"yazildi: {HEDEF}  ({len(icerik)} bayt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
