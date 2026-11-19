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

URETILEN DOSYALARA BAKMIYOR
--------------------------
Sozlesme sinamasinin aksine bu sinama uretilen dosyalari okumuyor,
yalnizca uygulama kaynagina bakiyor. Uretimden ONCE, normal sinama
adiminda kosmasi DOGRU: kaynak kusuru icerik uretilmeden once
bilinmeli.

BU DOSYADA BUYUK HARFLI "C-I-K-T-I" GECMIYOR -- bilerek.
`cikti_sinamalari.py` uretim sonrasi kosturacagi sinamalari
KAYNAKTAKI yol izine gore seciyor ve o izlerden biri tam o kelime.
Ilk yazimda aciklama yorumunda gectigi icin dosya o kumeye DE
giriyordu; yani yorum "girmiyor" derken dosya giriyordu. Zararsiz
bir cift kosuydu (secicinin kendi belgesi de boyle diyor) ama
yorumun iddiasi yanlisti -- bu depoda ayri bir kusur sinifi.

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

    # KAPININ KENDISI DE SINANIYOR -- OLCULDU (2026-11-19, M12).
    #
    # `kaynak-sinamasi.mjs` icindeki bir kurali "her zaman gecer"
    # hale getiren mutasyon KACTI: kurali tutan hicbir sey yoktu.
    # Ayni bosluk `sozlesme-sinamasi.mjs` icin daha once gorulmus ve
    # `test_mobil_besleme.py` beslemeyi BOZUP kirmizi donmesini
    # bekleyerek kapatilmisti. Ayni desen burada.
    #
    # Agac KOPYALANIP bozuluyor; gercek kaynak hic degismiyor.
    return _kapi_gercekten_eliyor_mu(dugum)


#: Bozma senaryolari: (ad, eski, yeni). Her biri AYRI bir kurali
#: hedefliyor -- biri otuyor diye otekiler bedava gecmesin.
_BOZMALAR = (
    ("Amblem `Image` kullanirsa",
     "  if (!kod || !renk) return null;",
     "  if (!kod || !renk) return null;\n  const _s = Image;"),
    ("Amblem eksik-veri korumasi kalkarsa",
     "  if (!kod || !renk) return null;",
     "  if (true) { /* koruma yok */ }"),
    ("Amblem SVG yolunu gorsel kaynagi yaparsa",
     "  if (!kod || !renk) return null;",
     '  if (!kod || !renk) return null;\n'
     '  const _s = api.varlikAdresi("/statik/amblem/x.svg");'),
)


def _kapi_gercekten_eliyor_mu(dugum: str) -> int:
    import tempfile                                     # noqa: PLC0415

    kaynak = KOK / "mobil"
    hedef_ad = kaynak / "src" / "bilesen.tsx"
    if not hedef_ad.is_file():
        print("DUSTU  bilesen.tsx yok -- kapi sinanamadi")
        return 1
    asil = hedef_ad.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as gec:
        kopya = pathlib.Path(gec) / "mobil"
        kopya.mkdir()
        for ad in ("src", "app"):
            if (kaynak / ad).is_dir():
                shutil.copytree(kaynak / ad, kopya / ad)
        shutil.copy2(kaynak / "package.json", kopya / "package.json")
        kop_bilesen = kopya / "src" / "bilesen.tsx"

        def kos() -> int:
            return subprocess.run(
                [dugum, str(SINAMA), "--kok", str(kopya)], cwd=str(KOK),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace").returncode

        # ATILLIK: bozulmamis KOPYA gecmeli. Gecmezse asagidaki
        # "bozunca kirmizi" iddialari hicbir sey olcmez -- kopya
        # zaten kirmiziydi demektir.
        if kos() != 0:
            print("DUSTU  bozulmamis kopya KIRMIZI -- kapi sinanamadi")
            return 1
        for ad, eski, yeni in _BOZMALAR:
            if eski not in asil:
                print(f"DUSTU  bozma desen bulunamadi: {ad}")
                return 1
            kop_bilesen.write_text(asil.replace(eski, yeni, 1),
                                   encoding="utf-8")
            if kos() == 0:
                print(f"DUSTU  kapi ELEMEDI: {ad}")
                return 1
            kop_bilesen.write_text(asil, encoding="utf-8")
    print(f"  kapi {len(_BOZMALAR)} bozma senaryosunda da KIRMIZI dondu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
