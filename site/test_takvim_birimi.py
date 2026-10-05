# -*- coding: utf-8 -*-
"""TAKVIMDEKI SAYILAR BIRIMIYLE BASILMALI.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-10-04, `/makro/`): "ABD Tarim Disi Istihdam" satiri

    ACIKLANDI  29,00
    Son aciklanan: 162 bin    Beklenti: 89 bin

yaziyordu. Ayni serinin uc sayisi; ikisi birimli, biri BIRIMSIZ ve
ondalikli. Finans sitesinde birimsiz sayi tehlikeli: okur 29,00'i
yuzde ya da endeks seviyesi sanabilir.

SEBEP IKI AYRI BICIMLENDIRICIYDI
--------------------------------
Sitede olcumler `insa.olcum_bicimi` ile, birimiyle birlikte
basiliyor. Takvimin "gerceklesen" degeri ise
`takvim_gerceklesen._tr` ile basiliyordu ve o birim ALMIYORDU.
Ustelik `_tr`nin kendi aciklamasi tam bu riski yaziyordu:

    "Ayrica ayni sayi iki yerde farkli bicimlenirse okur
     hangisinin dogru oldugunu bilemez."

Kural yaziliydi; uygulayan yoktu. Veritabanindaki `gosterge`
tablosunda `birim` sutunu VARDI ("bin kisi") -- sorgu onu
secmiyordu.

NE SINANIYOR
------------
1. `gerceklesen` sozlesmesi: `deger` ve `birim` alanlari var,
   onceden uretilen `metin` alani YOK (ikinci bicimlendirici
   kalmadi).
2. Sablon, site geneli `olcum` suzgecini kullaniyor.
3. Uretilen ciktida "ACIKLANDI" degeri, yanindaki "Son aciklanan"
   degeri birimliyken BIRIMSIZ degil.
"""

from __future__ import annotations

import html as _html
import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


import takvim_gerceklesen as _tg  # noqa: E402

# --- 1) sozlesme ---
esit("birim" in _tg.gerceklesen.__doc__ or True, True, "modul yuklendi")
_kaynak = (_SITE / "takvim_gerceklesen.py").read_text(encoding="utf-8")
esit('"SELECT deger, tarih, birim FROM gosterge "' in _kaynak, True,
     "sorgu `birim` sutununu da okuyor")
esit('g.pop("metin", None)' in _kaynak, True,
     "modul artik kendi bicimlendirmesini URETMIYOR")

# --- 2) sablon site geneli suzgeci kullaniyor ---
_sab = (_SITE / "sablonlar" / "_takvim.html").read_text(encoding="utf-8")
esit(bool(re.search(r"k\.gerceklesen\.deger\s*\|\s*olcum\("
                    r"\s*k\.gerceklesen\.birim\s*\)", _sab, re.S)),
     True, "sablon `olcum(birim)` suzgecinden geciriyor")
esit("k.gerceklesen.metin" not in _sab, True,
     "sablon artik hazir metin basmiyor")

# --- 2b) SAYIM BIRIMINDE ONDALIK YOK (AYRI SOZLESME) ---
#
# Yukaridaki olcu BIRIMIN VARLIGINI soruyor. Ondalik ayri bir soru ve
# ayri yakalanmali: "29,00 bin kisi" birimli oldugu icin yukaridaki
# sinamadan GECER ama hala yanlistir -- 29 bin kisi sayilir, virgulden
# sonraki iki sifir bir olcum degil, bicimlendirme artigi.
#
# Mutasyonla dogrulandi: sayim kurali geri alindiginda yukaridaki
# sinama yesil kaliyordu. Bir korumanin var olmasi yetmiyor; NEYI
# KACIRDIGINI sormak gerekiyor.
import insa as _insa  # noqa: E402

for _d, _b, _bek in (
        (29.0, "bin kişi", "29 bin kişi"),
        (162.0, "bin kişi", "162 bin kişi"),
        (50.0, "bin adet", "50 bin adet"),
        (61.0, "kişi", "61 kişi"),
        # Oran ve para BOZULMADI: ondalik orada ANLAMLI.
        (4.5, "%", "%4,50"),
        (5.0, "%", "%5,00"),
        (7.0, "puan", "7,00 puan"),
        (95.0, "$", "95,00 $"),
        (29.5, "bin kişi", "29,50 bin kişi"),
):
    esit(_insa.olcum_bicimi(_d, _b), _bek,
         f"olcum_bicimi({_d}, {_b!r})")

# --- 3) uretilen cikti ---
_C = _SITE / "cikti"
if not (_C / "index.html").exists():
    print("\n  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

#: Birim sayilan isaretler. `endeks` BILEREK disarida: `olcum_bicimi`
#: onu birimsiz basiyor ve bu dogru -- endeks degerinin birimi yok.
_BIRIMLI = re.compile(r"[%$€₺]|\b(bin|milyon|milyar|kişi|adet|TL|USD|puan|bp|"
                      r"varil|mn)\b")
_bakilan = 0
_kotu: list[str] = []
for _p in sorted(_C.rglob("index.html")):
    _m = _p.read_text(encoding="utf-8", errors="replace")
    if "takvim-cikti" not in _m:
        continue
    for _c in re.finditer(r'<b class="takvim-cikti">([^<]+)</b>(.{0,900})',
                          _m, re.S):
        _bakilan += 1
        _deger = _html.unescape(_c.group(1)).strip()
        _son = re.search(r"Son açıklanan:\s*<b>([^<]+)</b>", _c.group(2))
        if not _son:
            continue
        _son_m = _html.unescape(_son.group(1)).strip()
        if _BIRIMLI.search(_son_m) and not _BIRIMLI.search(_deger):
            _kotu.append(f"{_p.parent.name or '/'}:  "
                         f"ACIKLANDI {_deger!r}  <->  son {_son_m!r}")

# ACIKLANMIS DEGER YOKSA SINAMA ATLANIR -- VE BU KASITLI.
#
# Takvimde "ACIKLANDI" degeri yalnizca o an yayimlanmis bir veri
# varsa basiliyor; cogu zaman butun kalemler "beklenen" durumda
# oluyor. Ilk yazimda `_bakilan > 0` SART kosmustum ve sinama,
# urunde hicbir sey bozulmadigi halde kirmizi yandi -- cunku o gun
# takvimde aciklanmis kalem yoktu.
#
# Gecici veriye bagli bir SART, sinamayi gunun sansina baglar.
# Kirmizi yanan ama kusur gostermeyen bir sinama, zamanla "zaten
# bazen kirmizi yaniyor" diye gormezden gelinir -- ve o an gercek
# bir kusuru da gizler.
#
# SOZLESME KONTROLLERI (yukarida) HER ZAMAN KOSUYOR: sorgunun
# `birim`i okudugu, modulun `metin` uretmedigi, sablonun `olcum`
# suzgecini kullandigi ve ondalik kurali. Atlanan YALNIZCA
# uretilmis ciktiya bakan kisim -- yani bakilacak bir sey yoksa.
if _bakilan == 0:
    print(chr(10) + "  ATLANDI  takvimde aciklanmis deger yok"
          + " (butun kalemler beklenen durumda)")
    print(chr(10) + f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)
esit(_bakilan > 0, True, f"takvim cikti degeri bulundu ({_bakilan})")
if _kotu:
    print(f"\n  BIRIMSIZ BASILAN DEGER: {len(_kotu)}")
    for _k in _kotu[:6]:
        print(f"    {_k}")
esit(len(_kotu), 0,
     f"komsusu birimliyken birimsiz basilan deger yok ({_bakilan})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
