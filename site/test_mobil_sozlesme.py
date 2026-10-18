# -*- coding: utf-8 -*-
"""MOBIL BESLEMESI <-> UYGULAMA SOZLESMESINI CIKTI UZERINDE SINAR.

BU DOSYA NEDEN VAR -- ATIL BIR KORUMAYI KURTARMAK ICIN
------------------------------------------------------
Sozlesme sinamasinin kendisi `mobil/sozlesme-sinamasi.mjs`. Orada
yazildi cunku sinanan sey UYGULAMANIN okudugu alanlar ve uygulama
JavaScript.

Ama CI sinamalari su iki desenle buluyor:

    find haber_botu site -name "test_*.py"
    find haber_botu site -name "test_*.js"

`.mjs` uzantili ve `mobil/` altindaki bir dosya IKISINE DE girmiyor.
Yani sozlesme sinamasi yazildigi anda ATIL olacakti: yerelde kosar,
CI'da hic kosmazdi. Bu depoda tam bu sinif yasandi -- bir koruma
`sys.exit(1)` kapisinin arkasinda kaldi ve mutasyonlarin ucte ikisi
yesil gecti.

Bu dosya o bosluğu kapatiyor: CI'in bulduğu desene uyuyor ve gercek
sinamayi kosturuyor.

NEDEN URETIMDEN SONRA KOSMALI
-----------------------------
Sinama `site/cikti/v1` icine bakiyor. CI'in "Testleri calistir"
adimi icerik URETILMEDEN once kosuyor ve `site/cikti` `.gitignore`
icinde -- yani taze kopyada o dizin YOK.

Bu yuzden dosya `CIKTI` yoluna deginiyor: `cikti_sinamalari.py`
ciktiya bakan sinamalari YOL IZINE gore seciyor ve bu dosyayi
uretimden SONRA, dagitimdan ONCE yeniden kosturuyor. Cikti varken
"ATLANDI" yazarsa orada KIRMIZI sayiliyor.

NODE YOKSA ATLANMIYOR, DUSUYOR
------------------------------
Node bulunamazsa sinama kirmizi doner. Sessizce atlamak, sozlesmenin
denetlenmedigi bir dagitim demek olurdu ve bu dosyanin butun varlik
sebebi o sessizligi bozmak. CI'da Node kurulu ("Node kur" adimi).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
CIKTI = KOK / "site" / "cikti"
SINAMA = KOK / "mobil" / "sozlesme-sinamasi.mjs"


def main() -> int:
    if not (CIKTI / "v1" / "surum.json").is_file():
        # Konvansiyon: cikti yokken ATLANDI + 0. `cikti_sinamalari.py`
        # bunu cikti VARKEN gorurse kirmizi sayiyor.
        print("ATLANDI  cikti/v1 yok -- once `python site/insa.py`")
        return 0

    if not SINAMA.is_file():
        print(f"DUSTU  sozlesme sinamasi bulunamadi: {SINAMA}")
        return 1

    dugum = shutil.which("node")
    if not dugum:
        print("DUSTU  node bulunamadi -- sozlesme DENETLENMEDI.")
        print("  Sessizce atlamak, sozlesmesi denetlenmemis bir")
        print("  dagitim demek olurdu.")
        return 1

    k = subprocess.run([dugum, str(SINAMA)], cwd=str(KOK),
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    # Gecen ciktinin tamamini basmiyoruz; dusenin tamamini basiyoruz.
    if k.returncode != 0:
        print(k.stdout or "")
        print(k.stderr or "")
        print("DUSTU  mobil besleme sozlesmesi bozuldu")
        return 1

    son = [s for s in (k.stdout or "").splitlines() if s.strip()]
    print(son[-1] if son else "TUM SOZLESME SINAMALARI GECTI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
