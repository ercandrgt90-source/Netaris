"""Siteyi uretip Cloudflare'e yayimlar -- tek komut.

    python yayinla.py

Elle ZIP paketleyip panele surukleme dongusu bitiyor. Betik iki isi
sirayla yapiyor:

  1. site/insa.py  -> icerikten HTML uretir
  2. wrangler deploy -> Cloudflare'e yukler

Ilk kullanimdan once bir kez kimlik dogrulamasi gerekiyor:

    npx wrangler login

Tarayicida onay verildikten sonra kimlik makinede saklanir; bir daha
sorulmaz.

Yayina almadan once dogrulama yapar: yer tutucu alan adi, doldurulmamis
kunye alani ve islenmemis sablon etiketi varsa dagitimi DURDURUR. Bir kez
yer tutucu bilgilerle yayina cikildi; bu kontrol onu tekrarlatmamak icin.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

KOK = pathlib.Path(__file__).parent
CIKTI = KOK / "cikti"

# Yayina cikmasi kabul edilemez izler
ENGELLER = (
    ("ALAN-ADI-BELIRLENMEDI", "site adresi hala yer tutucu (insa.py icinde SITE['adres'])"),
    ("[Ad Soyad", "kunye sayfasinda doldurulmamis alan"),
    ("[Acik adres", "kunye sayfasinda doldurulmamis alan"),
    ("[Açık adres", "kunye sayfasinda doldurulmamis alan"),
    ("DOLDURULACAK", "yayina cikmamasi gereken not blogu"),
    ("{{", "islenmemis sablon etiketi"),
    ("{%", "islenmemis sablon etiketi"),
)


def _node_yolu() -> None:
    """Node kurulum dizinini PATH'e ekler.

    winget ile kurulan Node yeni acilan kabuklarda PATH'te gorunuyor ama
    calisan oturumda gorunmeyebiliyor. Elle eklemek bu farki kapatiyor.
    """
    for aday in (r"C:\Program Files\nodejs", r"C:\Program Files (x86)\nodejs"):
        if pathlib.Path(aday).exists() and aday not in os.environ["PATH"]:
            os.environ["PATH"] = f"{aday};{os.environ['PATH']}"


# Windows'ta alt surec ciktisi varsayilan olarak sistem kod sayfasiyla
# (Turkce kurulumda cp1254) cozulmeye calisiliyor. Wrangler UTF-8 yaziyor
# ve emoji kullaniyor -- cozumleme UnicodeDecodeError ile patliyor, stdout
# None kaliyor. Kodlamayi acikca vermek bunu kapatiyor.
_CALISTIR = {"text": True, "capture_output": True, "encoding": "utf-8", "errors": "replace"}


def insa_et() -> int:
    print("[1/3] site uretiliyor")
    sonuc = subprocess.run([sys.executable, str(KOK / "insa.py")], cwd=KOK, **_CALISTIR)
    print("  " + "\n  ".join((sonuc.stdout or "").strip().splitlines()))
    if sonuc.returncode:
        print(sonuc.stderr or "")
    return sonuc.returncode


def denetle() -> list[str]:
    print("[2/3] yayin oncesi denetim")
    bulgular: list[str] = []
    for dosya in CIKTI.rglob("*.html"):
        metin = dosya.read_text(encoding="utf-8")
        goreli = dosya.relative_to(CIKTI).as_posix()
        for iz, aciklama in ENGELLER:
            if iz in metin:
                bulgular.append(f"{goreli}: {aciklama}")
    return sorted(set(bulgular))


def dagit(kuru: bool) -> int:
    print("[3/3] Cloudflare'e yukleniyor")
    npx = shutil.which("npx")
    if not npx:
        print("  HATA: npx bulunamadi -- Node.js kurulu mu?")
        return 1

    komut = [npx, "--yes", "wrangler@latest", "deploy"]
    if kuru:
        komut.append("--dry-run")

    sonuc = subprocess.run(komut, cwd=KOK, **_CALISTIR)
    cikti = ((sonuc.stdout or "") + (sonuc.stderr or "")).strip()
    print("  " + "\n  ".join(cikti.splitlines()[-18:]))

    if "You are not authenticated" in cikti:
        print("\n  Once bir kez kimlik dogrulamasi gerekiyor:")
        print("      npx wrangler login")
    return sonuc.returncode


def main() -> int:
    a = argparse.ArgumentParser(description="Netaris yayina alma")
    a.add_argument("--kuru", action="store_true", help="yuklemeden dene (dry-run)")
    a.add_argument("--zorla", action="store_true", help="denetim bulgularina ragmen devam et")
    args = a.parse_args()

    _node_yolu()

    if insa_et():
        return 1

    bulgular = denetle()
    if bulgular:
        for b in bulgular:
            print(f"  ENGEL  {b}")
        if not args.zorla:
            print("\nDAGITIM DURDURULDU. Duzeltip tekrar calistirin.")
            print("(bilerek devam etmek icin --zorla)")
            return 1
        print("\n  --zorla verildi, bulgulara ragmen devam ediliyor")
    else:
        print("  temiz")

    if dagit(args.kuru):
        return 1

    print("\nYAYINDA." if not args.kuru else "\nKURU DENEME TAMAM (yukleme yapilmadi).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
