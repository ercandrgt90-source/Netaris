# -*- coding: utf-8 -*-
"""HER HABER ADRESI TEK BIR HABERE AIT OLMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-18): 13 adres 54 kaydi tasiyordu ve on ucunde de
yayinda kalan EN ESKI surumdu.

    /haber/tcmb-...-fonlama-37-00/         12 surum, yayinda 24 Agustos
    /haber/borsa-gune-dususle-basladi/      8 surum, yayinda 25 Agustos
    /haber/akaryakit-...-zam-indirim/       7 surum, yayinda 21 Agustos

Okur bugunun akisindan yakit fiyatina tikliyor ve 28 gun onceki
fiyati goruyordu. Bu EKSIK SAYFA degil, YANLIS BILGI -- ve o
adreslere siteden ~512 ic baglanti gidiyordu.

SEBEP: IKI KOD YOLU AYNI SORUYA IKI CEVAP VERIYORDU
---------------------------------------------------
    tekilles   -> "ayni gun + ayni baslik" ayni haber;
                  FARKLI GUNLER AYRI HABER  (dogru karar)
    haber_yolu -> adres yalnizca BASLIKTAN;
                  farkli gunler AYNI ADRES

Liste tarih-azalan, yazma dongusu her seferinde uzerine yaziyor --
yani son yazilan, en eski surum kazaniyordu.

NE SINANIYOR
------------
1. Eleme en yeni surumu birakiyor -- listenin sirasi ne olursa olsun.
2. Sayfasi olmayan kayit elenmiyor (adres capismaz).
3. Uretilen ciktida hicbir adres birden fazla habere ait degil.
4. Yayinda kalan surum, o adresin EN YENI kaydi.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
import sys
from collections import defaultdict

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_DB = _SITE.parent / "haber_botu" / "netaris.db"
sys.path.insert(0, str(_SITE))

import insa  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _h(yol, tarih, ad):
    return {"yol": yol, "tarih": tarih, "baslik": ad, "adres": ad}


print("\nEleme en yeni surumu birakiyor")

# Iki sira da ayni cevabi vermeli: siranin dogruluguna GUVENMIYORUZ.
_yeni_once = insa._yolla_tekilles(
    [_h("/haber/x/", "2026-09-18", "YENI"), _h("/haber/x/", "2026-08-21", "ESKI")])
esit([h["baslik"] for h in _yeni_once], ["YENI"], "yeni onceyse yeni kaliyor")

_eski_once = insa._yolla_tekilles(
    [_h("/haber/x/", "2026-08-21", "ESKI"), _h("/haber/x/", "2026-09-18", "YENI")])
esit([h["baslik"] for h in _eski_once], ["YENI"], "eski onceyse yine yeni kaliyor")

# Cakismayanlar AYNEN kalmali -- eleme fazla calisirsa haber duser.
_karisik = insa._yolla_tekilles([
    _h("/haber/a/", "2026-09-18", "A"),
    _h("/haber/b/", "2026-09-17", "B"),
    _h("/haber/a/", "2026-08-01", "A-eski"),
    _h(None, "2026-09-16", "SAYFASIZ"),
    _h(None, "2026-09-15", "SAYFASIZ2"),
])
esit([h["baslik"] for h in _karisik], ["A", "B", "SAYFASIZ", "SAYFASIZ2"],
     "cakismayan kayitlar ve sayfasizlar korunuyor")

# Uc surumun en yenisi -- ikiden fazlada da dogru calismali.
_uc = insa._yolla_tekilles([
    _h("/haber/x/", "2026-08-21", "1"),
    _h("/haber/x/", "2026-09-18", "3"),
    _h("/haber/x/", "2026-09-01", "2"),
])
esit([h["baslik"] for h in _uc], ["3"], "uc surumden en yenisi kaliyor")

# ELEME GERCEKTEN BAGLI MI.
#
# Yukaridaki iddialar `_yolla_tekilles`i DOGRUDAN cagiriyor, yani
# fonksiyonun dogru calistigini gosteriyor -- BAGLI oldugunu degil.
# Olculdu (mutasyon D): `tekilles`in sonundaki cagriyi silmek sinamayi
# KIRMIZI yapmiyordu, cunku ciktiya bakan iddialar son KURULUMUN
# izlerini okuyor ve o kurulum duzeltilmis kodla yapilmisti. Yani
# kusur bir sonraki kuruluma kadar gorunmez kalirdi.
#
# Bu iddia zinciri `tekilles` uzerinden kuruyor: hatti kuran tek
# fonksiyon o, ve ciktisi "her kalem AYRI BIR SAYFA" garantisi
# vermek zorunda.
print("\nEleme hatta BAGLI")
_zincir = insa.tekilles([
    _h("/haber/borsa-gune-dususle-basladi/", "2026-09-18", "Borsa gune dususle basladi"),
    _h("/haber/borsa-gune-dususle-basladi/", "2026-08-21", "Borsa gune dususle basladi"),
])
esit([h["tarih"] for h in _zincir], ["2026-09-18"],
     "`tekilles` ciktisinda adresler BENZERSIZ (eleme bagli)")

print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists() or not _DB.exists():
    print("  ATLANDI  cikti ya da depo yok")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_db = sqlite3.connect(_DB)
_db.row_factory = sqlite3.Row
_kayit = [dict(r) for r in _db.execute(
    "SELECT tarih, yayin_yolu FROM haber"
    " WHERE yayimlandi = 1 AND yayin_yolu LIKE '/haber/_%'")]
esit(len(_kayit) > 200, True, f"yayimlanmis haber kaydi dolu ({len(_kayit)})")

_g: dict[str, list[str]] = defaultdict(list)
for _k in _kayit:
    _g[_k["yayin_yolu"]].append((_k["tarih"] or "")[:10])

_cak = {y: v for y, v in _g.items() if len(v) > 1}
if _cak:
    print("\n  BIR ADRESI PAYLASAN HABERLER:")
    for _y, _v in list(_cak.items())[:8]:
        print(f"    {len(_v)}x  {_y}  {sorted(_v)}")
esit(len(_cak), 0, "hicbir adres birden fazla habere ait degil")

# Sayfa GERCEKTEN en yeni surumu mu tasiyor: bayat sayfa kusurunun
# ta kendisi buradan yakalanir.
_bayat = []
for _y, _v in _g.items():
    _s = _CIKTI / _y.strip("/") / "index.html"
    if not _s.exists():
        continue
    _m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)',
                   _s.read_text(encoding="utf-8", errors="replace"))
    if _m and _m.group(1) != max(_v):
        _bayat.append((_y, _m.group(1), max(_v)))
if _bayat:
    print("\n  BAYAT SAYFALAR (yayinda / olmasi gereken):")
    for _b in _bayat[:8]:
        print(f"    {_b[0]}  {_b[1]} != {_b[2]}")
esit(len(_bayat), 0, f"her sayfa kendi adresinin EN YENI kaydini tasiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
