# -*- coding: utf-8 -*-
"""UYGULAMA KAYNAGI KURALLARINI CI'IN BULDUGU DESENDEN KOSTURUR.

BU DOSYA NEDEN VAR
------------------
Gercek sinama `mobil/kaynak-sinamasi.mjs`. Orada yazildi cunku
sinanan sey uygulamanin KENDI kaynagi (TypeScript/JSX) ve kurallar
o metne bakiyor.

CI sinamalari su iki desenle buluyor:

    find haber_botu site -name "test_*.py"
    find haber_botu site -name "test_*.js"

`.mjs` uzantili ve `mobil/` altindaki bir dosya IKISINE DE girmiyor.
Bu dosya o bosluğu kapatiyor -- `site/test_mobil_sozlesme.py` ile
AYNI desen; o dosya zaten 2026-10-18'den beri sozlesme sinamasini
bu yoldan kosturuyor.

NEDEN AKISA AYRI BIR ADIM EKLENMEDI
-----------------------------------
Bir ara akisa "Uygulama kaynagi kurallara uyuyor mu" diye ayri bir
adim eklenmisti. Yanlisti: ayni karari iki yerde almak bu depoda
UC KEZ kosu dusurdu (iki liste ayrisinca). Sarmalayici deseni zaten
vardi; ikinci bir yol acmak yerine ona uyuluyor.

CIKTIYA BAKMIYOR
----------------
Sozlesme sinamasinin aksine bu sinama `site/cikti` okumuyor, yalnizca
uygulama kaynagina bakiyor. Dolayisiyla `cikti_sinamalari.py`nin
secicisine (`CIKTI` yol izi) girmiyor ve girmemeli: uretimden ONCE,
normal sinama adiminda kosmasi DOGRU -- kaynak kusuru icerik
uretilmeden once bilinmeli.

NODE YOKSA ATLANMIYOR, DUSUYOR
------------------------------
Sessizce atlamak, kurallari denetlenmemis bir dagitim demek olurdu.
CI'da Node kurulu ("Node kur" adimi).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
SINAMA = KOK / "mobil" / "kaynak-sinamasi.mjs"


def main() -> int:
    if not SINAMA.is_file():
        print(f"DUSTU  kaynak sinamasi bulunamadi: {SINAMA}")
        return 1

    dugum = shutil.which("node")
    if not dugum:
        print("DUSTU  node bulunamadi -- uygulama kaynagi DENETLENMEDI.")
        return 1

    k = subprocess.run([dugum, str(SINAMA)], cwd=str(KOK),
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if k.returncode != 0:
        print((k.stdout or "") + (k.stderr or ""))
        return 1
    # Gecen kosuda yalnizca son satir basiliyor: takim ciktisi
    # okunabilir kalsin.
    satirlar = [x for x in (k.stdout or "").splitlines() if x.strip()]
    print(satirlar[-1] if satirlar else "TUM KAYNAK SINAMALARI GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
