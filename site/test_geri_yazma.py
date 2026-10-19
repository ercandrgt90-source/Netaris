# -*- coding: utf-8 -*-
"""ELLE YAZILAN SAYFALAR GERI YAZMAYLA SILINMESIN.

BU DOSYA NEDEN VAR -- OLCULDU (2026-10-18)
------------------------------------------
Bot commiti `a73dc292`, `site/icerik/sayfalar/gizlilik.md`den
**21 SATIR SILDI** -- uygulama ici hesap silmeyi anlatan bolumu.
Kimse silmedi; kosu kendi ESKI calisma agacini geri yazdi.

Kanit:

    git show --stat a73dc292 -- site/icerik/sayfalar/gizlilik.md
        1 file changed, 21 deletions(-)

MEKANIZMA
---------
Kosu checkout'unu aldiktan SONRA o dosya depoda degisti.
`reset --mixed` indeksi uzak uca esitliyor ama CALISMA AGACI eski
kaldigi icin `git add site/icerik` eski icerigi asamaya aliyor ve
commit degisikligi GERI ALIYOR. Hicbir hata cikmiyor, kosu yesil
bitiyor.

Is akisi bu sinifin SILME yonunu zaten koruyordu (`UST_SILINEN`
dongusu, 2026-08-28'de eklenmis). DEGISTIRME yonu acikti ve iki ay
sonra bu dosyayi yedi.

NE SINANIYOR
------------
Geri yazma yapan HER is akisinda:

 1. `git add` elle yazilan sayfalari DISLIYOR mu
 2. Yontemden bagimsiz bir KAPI var mi (o sayfa asamaya girerse
    kosu kirmizi donsun)

Is akislari DOSYADAN okunuyor; liste buraya yazilmiyor. Yarin
ucuncu bir is akisi geri yazma yaparsa, bu sinama onu da
denetler.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
AKISLAR = KOK / ".github" / "workflows"

#: Elle yazilan, hicbir hattin URETMEDIGI dizin.
#: `insa.py` oraya yalnizca okuyor (`ICERIK / "sayfalar"`).
ELLE_DIZIN = "site/icerik/sayfalar"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("")
print("1. ELLE YAZILAN SAYFALAR GERCEKTEN ELLE YAZILIYOR")
#
# Varsayim once DOGRULANIYOR: bu dizine yazan bir hat varsa
# disarida birakmak veri kaybi olurdu.
dizin = KOK / ELLE_DIZIN
esit(dizin.is_dir(), True, f"{ELLE_DIZIN} var")
dosyalar = sorted(p.name for p in dizin.glob("*.md"))
esit(len(dosyalar) >= 3, True, f"{len(dosyalar)} sayfa: {dosyalar}")

yazan = []
for p in list(KOK.glob("site/*.py")) + list(KOK.glob("haber_botu/**/*.py")):
    if p.name.startswith("test_"):
        continue
    try:
        k = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    # `ICERIK / "sayfalar"` yoluna YAZMA izi: write_text / open(..,"w")
    for m in re.finditer(r'sayfalar"\s*/\s*f?"[^"]*"', k):
        pencere = k[max(0, m.start() - 200):m.end() + 200]
        if "write_text" in pencere or '"w"' in pencere:
            yazan.append(f"{p.name}: {m.group(0)[:40]}")
esit(yazan, [],
     "hicbir hat bu dizine YAZMIYOR (yalnizca okuyor)")

print("")
print("2. GERI YAZAN HER IS AKISI DISLIYOR")
geri_yazan = []
for p in sorted(AKISLAR.glob("*.yml")):
    k = p.read_text(encoding="utf-8")
    if "git add --ignore-removal" not in k:
        continue
    geri_yazan.append(p.name)

    # 2a. `git add` cagrilari ELLE DIZINI disliyor mu.
    # SATIR BASINA SABITLENIYOR: ilk yazim bir YORUM satirini
    # ("# `git add --ignore-removal` kullaniyor...") gercek bir
    # cagri sandi ve sinama kendi kendine kirmiziya dondu.
    cagrilar = re.findall(
        r"(?m)^[ \t]*git add --ignore-removal[^\n]*", k)
    esit(len(cagrilar) >= 1, True, f"{p.name}: {len(cagrilar)} git add")
    disalamayan = [c for c in cagrilar if f"':!{ELLE_DIZIN}'" not in c]
    esit(disalamayan, [],
         f"{p.name}: her `git add` elle sayfalari disliyor")

    # 2b. YONTEMDEN BAGIMSIZ KAPI.
    #
    # Pathspec tek basina yeterli gorunuyor ama bir karari tek yerde
    # almak, o yer degisince korumayi da kaybetmek demek -- is
    # akisinin kendi notu da ayni seyi soyluyor.
    esit(bool(re.search(
        r"grep -E '\^site/icerik/sayfalar/'", k)), True,
        f"{p.name}: asamada elle sayfa ararsa KIRMIZI donuyor")
    esit("geri yazma DURDURULDU" in k, True,
         f"{p.name}: kapi kapanınca is duruyor")

esit(len(geri_yazan) >= 2, True,
     f"geri yazan is akisi bulundu: {geri_yazan}")

print("")
print("3. SILME YONU DE KORUNUYOR (onceki duzeltme yerinde)")
# 2026-08-28'de eklenmisti; kaldirilmadigini dogruluyoruz.
for ad in geri_yazan:
    k = (AKISLAR / ad).read_text(encoding="utf-8")
    esit("--diff-filter=D" in k, True,
         f"{ad}: uzak ucta silinmis dosya diriltilmiyor")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
