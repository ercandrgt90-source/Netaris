# -*- coding: utf-8 -*-
"""GUNDEM SAYFASININ GIRISI, SAYFANIN KENDISINI ANLATMALI.

BU DOSYA NEDEN VAR
------------------
Sayfanin basligi uzun sure "Merkez bankalari ve duzenleyiciler" idi
ve giris metni yalnizca Fed, ECB, SEC ve EIA'yi sayiyordu. Sayfa o
gun boyleydi; sonra buyudu ve metin yerinde kaldi.

OLCULDU (2026-10-04, uretilen sayfa, 120 oge):

    Jeopolitik        40      Duzenleme     3
    Sirketler         25      Sektorler     3
    Makro             24      Diger         2
    Emtia ve enerji   18
    Piyasalar          5

"Merkez bankalari ve duzenleyiciler" = Makro + Duzenleme = 27, yani
sayfanin %22'si. En buyuk kume Jeopolitik ve baslikla ilgisi yok.

Yanlis baslik, yanlis koddan kotudur: kod calisir, baslik okuyani
yanlis yone gonderir. H1 ayrica arama motoruna verilen en guclu
isaret.

NE SINANIYOR
------------
Giris metninde ADI GECEN her kurum, sayfada GERCEKTEN kaynak olarak
bulunmali. Bu, "metin kurum sayiyor ama o kurum artik sayfada yok"
kaymasini yakalar.

NE SINANMIYOR -- VE BU BILINCLI
-------------------------------
"Metin sayfanin ne kadarini anlatiyor" olculemiyor: bir basligin
icerigi ne olcude temsil ettigi bicimsel bir soru degil. Asil
koruma, metnin kurum SAYMAMASI -- saymak bu kusurun tekrar etmesinin
yoluydu. Sinama o karari koruyor: giriste kurum adi belirirse
kirmizi yanar ve yazan kisi "bu liste bir gun eskiyecek mi" sorusuyla
karsilasir.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_SABLON = (_SITE / "sablonlar" / "gundem.html").read_text(encoding="utf-8")
# Jinja yorumlari HARIC: gerekce yazisi kurum adi anabilir.
_SADE = re.sub(r"\{#.*?#\}", " ", _SABLON, flags=re.S)
_m = re.search(r'<div class="giris">(.*?)</div>', _SADE, re.S)
esit(bool(_m), True, "giris blogu bulundu")
_giris = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _m.group(1))).strip()

#: Sayfada kaynak olarak gecebilen kurum adlari. Liste KISITLAYICI
#: degil, TEMSILI: giriste bunlardan biri gecerse metin yine kurum
#: saymaya baslamis demektir.
_KURUMLAR = ("Fed", "SEC", "ECB", "EIA", "TCMB", "BoJ", "USTR", "BDDK",
             "SPK", "Avrupa Merkez Bankası", "ABD Enerji Bilgi İdaresi",
             "FinancialJuice", "Bloomberg", "Reuters", "AA")
_gecen = [k for k in _KURUMLAR
          if re.search(rf"(?<![\w]){re.escape(k)}(?![\w])", _giris)]
if _gecen:
    print(f"\n  GIRISTE KURUM ADI: {', '.join(_gecen)}")
    print("  Kurum saymak, listenin bir gun eskimesi demek.")
    print(f"  giris: {_giris[:120]}")
esit(_gecen, [], "giris metni kurum SAYMIYOR")

# H1 bos kalmasin ve hala eski basligi tasimasin.
_h1 = re.search(r"<h1>(.*?)</h1>", _m.group(1), re.S)
esit(bool(_h1), True, "giriste H1 var")
_h1m = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _h1.group(1))).strip()
esit(len(_h1m) >= 3, True, f"H1 dolu ({_h1m!r})")
esit("Merkez bankaları ve düzenleyiciler" not in _h1m, True,
     "H1 artik sayfanin %22'sini anlatan eski basligi tasimiyor")

# --- uretilen sayfa varsa: giriste anilan hicbir sey olu olmasin ---
_C = _SITE / "cikti" / "gundem" / "index.html"
if not _C.exists():
    print("\n  ATLANDI  cikti yok (uretilen sayfa kontrolu)")
else:
    _s = _C.read_text(encoding="utf-8", errors="replace")
    esit(_h1m in _s, True, "H1 uretilen sayfada da basiliyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
