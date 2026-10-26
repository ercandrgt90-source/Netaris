# -*- coding: utf-8 -*-
"""CI'NIN KOSTUGU BATARYANIN TAMAMINI KOSTURUR.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-10-26): `sayac.js` degistirildi, "ilgili sandigim"
sinamalar tek tek kosturuldu (stil, olu kural, kacis, is akisi) ve
hepsi yesildi. CI'da `site/test_secici.js` kirmizi yandi -- o dosya
listemde YOKTU.

Sonuc: dagitim bir kosu daha kapali kaldi. Sebep kodda degil, SECIMDE:
bir modulu degistirirken "hangi sinamalar ilgili" diye dusunmek,
CAPRAZ kontrolleri (secici taramasi, olu kural, beyan denetimi)
kaciriyor. Onlar zaten "kimsenin ilgili sanmadigi" yerde durduklari
icin degerliler.

CI'nin kendi kesif komutu BURAYA KOPYALANMADI, `otomasyon.yml`den
OKUNUYOR: iki yerde tutulan bir liste zamanla ayrisir ve ayrisma
hata vermez -- bu depoda ayni ders defalarca yasandi.

NE KOSAR
--------
`find haber_botu site -name "test_*.py"` ve ayni deseni `.js` icin.
Olculdu: 168 sinama.

CIKTIYA BAKAN TAKIM BU LISTEDE DEGIL. `cikti_sinamalari.py` adi
`test_` ile baslamadigi icin kesfe girmiyor -- CI'da da oyle: o takim
AYRI bir adimda, icerik URETILDIKTEN sonra kosuyor (gerekce kendi
modul basinda). Yani tam dogrulama iki komut:

    python site/tum_sinamalar.py
    python site/cikti_sinamalari.py

KOSTURMA
--------
    python site/tum_sinamalar.py            # hepsi
    python site/tum_sinamalar.py --hizli    # yalnizca degisenler (git)
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import pathlib
import re
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent.parent
AKIS = KOK / ".github" / "workflows" / "otomasyon.yml"


def ci_desenleri() -> list[tuple[str, str]]:
    """(dizinler, desen) ciftleri -- is akisindan OKUNUYOR."""
    try:
        metin = AKIS.read_text(encoding="utf-8")
    except OSError:
        return []
    cikti = []
    for m in re.finditer(r'find\s+([\w/ ]+?)\s+-name\s+"([^"]+)"', metin):
        dizinler, desen = m.group(1).strip(), m.group(2)
        # `find site/cikti -type f` gibi sinama disi satirlar elensin.
        if not desen.startswith("test_"):
            continue
        cikti.append((dizinler, desen))
    return cikti


def dosyalar() -> list[pathlib.Path]:
    bulunan: set[pathlib.Path] = set()
    for dizinler, desen in ci_desenleri():
        for d in dizinler.split():
            kok = KOK / d
            if kok.is_dir():
                bulunan.update(kok.rglob(desen))
    return sorted(bulunan)


def kos(p: pathlib.Path) -> tuple[pathlib.Path, int, str]:
    komut = (["node", str(p)] if p.suffix == ".js"
             else [sys.executable, str(p)])
    try:
        r = subprocess.run(komut, cwd=str(KOK), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=600)
        return p, r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return p, 1, "ZAMAN ASIMI (600 sn)"


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--hizli", action="store_true",
                   help="yalnizca git'te degismis sinamalar")
    n = a.parse_args()

    hepsi = dosyalar()
    if not hepsi:
        print("KESIF BOS -- is akisindaki `find` satirlari okunamadi.")
        # BOS LISTE YESIL DONMEMELI: hicbir sey kosturmamak,
        # her seyin gectigi anlamina gelmez.
        return 1

    secilen = hepsi
    if n.hizli:
        try:
            r = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                               cwd=str(KOK), capture_output=True, text=True)
            degisen = {pathlib.Path(x).name for x in r.stdout.split()}
            secilen = [p for p in hepsi if p.name in degisen] or hepsi
        except Exception:                                # noqa: BLE001
            secilen = hepsi

    print(f"{len(secilen)} sinama kosuyor"
          f"{' (hizli)' if n.hizli else ''}...")
    bas = time.time()
    dusen: list[tuple[pathlib.Path, str]] = []
    with cf.ThreadPoolExecutor(max_workers=6) as havuz:
        for p, kod, cikti in havuz.map(kos, secilen):
            if kod != 0:
                dusen.append((p, cikti))

    sure = time.time() - bas
    print(f"  {len(secilen) - len(dusen)} yesil / {len(dusen)} kirmizi "
          f"({sure:.0f} saniye)")
    for p, cikti in dusen:
        print("")
        print(f"  KIRMIZI {p.relative_to(KOK)}")
        for satir in cikti.strip().splitlines()[-12:]:
            print(f"      {satir}")
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
