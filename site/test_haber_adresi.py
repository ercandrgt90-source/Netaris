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

import json
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

print("\nGercek veriyle")
# BURADA DEPODAKI `yayin_yolu` OKUNMUYOR -- NEDEN ONEMLI.
#
# Ilk yazimda bu bolum `yayin_yolu` sutununu gruplayip "cakisan var
# mi" diye soruyordu ve ILK CALISTIRMADA KIRMIZI YANDI. Kod dogruydu:
# o sutunu SON KURULUM yaziyor ve depodaki surum, duzeltmeden onceki
# kodla uretilmisti. Yani sinama kodu degil, GECMISI olcuyordu.
#
# Kusur olmadigi halde kirmizi yanan bir sinama, gormezden gelinen
# sinamadir. Soru dogru soruluyor: BUGUNKU kod, GERCEK veriyle
# calistirildiginda benzersiz adres uretiyor mu? Cevap depo
# tazeliginden bagimsiz.
if not _DB.exists():
    print("  ATLANDI  depo yok")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_db = sqlite3.connect(_DB)
_db.row_factory = sqlite3.Row
_ham = [dict(r) for r in _db.execute(
    "SELECT adres, baslik_tr, baslik_kaynak, tarih, yayin_yolu, sayfa_veri"
    "  FROM haber WHERE yayimlandi = 1")]
esit(len(_ham) > 200, True, f"yayimlanmis haber kaydi dolu ({len(_ham)})")

# Adres BUGUNKU kuralla yeniden turetiliyor, depodan okunmuyor.
_girdi = [{"adres": r["adres"], "baslik": r["baslik_tr"],
           "baslik_kaynak": r["baslik_kaynak"], "tarih": r["tarih"],
           "yol": insa.haber_yolu({"baslik": r["baslik_tr"],
                                   "baslik_kaynak": r["baslik_kaynak"],
                                   "adres": r["adres"]})}
          for r in _ham]

_ham_g: dict[str, list[str]] = defaultdict(list)
for _k in _girdi:
    _ham_g[_k["yol"]].append((_k["tarih"] or "")[:10])
_ham_cak = {y: v for y, v in _ham_g.items() if len(v) > 1}
print(f"  not: ham veride {len(_ham_cak)} adres birden fazla habere denk"
      f" geliyor ({sum(len(v) - 1 for v in _ham_cak.values())} fazla surum)"
      f" -- eleme tam da bunun icin var")

_sonuc = insa.tekilles(_girdi)
_son_g: dict[str, list[str]] = defaultdict(list)
for _k in _sonuc:
    _son_g[_k["yol"]].append((_k["tarih"] or "")[:10])
_cak = {y: v for y, v in _son_g.items() if len(v) > 1}
if _cak:
    print("\n  ELEMEDEN SONRA HALA BIR ADRESI PAYLASANLAR:")
    for _y, _v in list(_cak.items())[:8]:
        print(f"    {len(_v)}x  {_y}  {sorted(_v)}")
esit(len(_cak), 0,
     f"elemeden sonra hicbir adres paylasilmiyor ({len(_sonuc)} haber)")

# Her adreste KALAN surum, o adresin EN YENISI olmali.
_yanlis = [(k["yol"], (k["tarih"] or "")[:10], max(_ham_g[k["yol"]]))
           for k in _sonuc
           if (k["tarih"] or "")[:10] != max(_ham_g[k["yol"]])]
if _yanlis:
    print("\n  ESKI SURUM KALMIS (kalan / olmasi gereken):")
    for _w in _yanlis[:8]:
        print(f"    {_w[0]}  {_w[1]} != {_w[2]}")
esit(len(_yanlis), 0, "her adreste EN YENI surum kaliyor")

print("\nUretilen ciktida")
# Bu bolum son kurulumun izlerine bakar, yani YEREL bir kontrol.
# CI'da `site/cikti` sinama aninda yok (once sinamalar, sonra kurulum)
# ve burasi atlanir -- kasitli: yukaridaki iddialar zaten kodu olcuyor.
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

# BAYAT CIKTI KUSUR DEGIL -- KIRMIZI YANMAMALI.
#
# Olculdu (2026-09-22): dort gun once kurulmus bir `site/cikti` ile
# bugunun deposu karsilastirildi ve sekiz sayfa "bayat" gorundu.
# Hicbiri kusur degildi: o sayfalar 18 Eylul'de dogru uretilmisti,
# aradan gecen dort gunde depo tazelendi, cikti tazelenmedi.
#
# Kusur olmadigi halde kirmizi yanan sinama, gormezden gelinen
# sinamadir -- bu dosyanin kendi ustundeki yorumda yazan sey. Ayni
# tuzaga burada dusulmustu.
#
# Tazelik OLCULUYOR, varsayilmiyor: depodaki en yeni haber gunu ile
# ciktidaki en yeni gun karsilastiriliyor. Cikti geride ise bolum
# atlaniyor ve SEBEBI yaziliyor.
_depo_gun = max((k["tarih"] or "")[:10] for k in _ham)
_cikti_gun = ""
for _p in (_CIKTI / "haber").glob("*/index.html"):
    _m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)',
                   _p.read_text(encoding="utf-8", errors="replace"))
    if _m and _m.group(1) > _cikti_gun:
        _cikti_gun = _m.group(1)
if _cikti_gun and _cikti_gun < _depo_gun:
    print(f"  ATLANDI  cikti BAYAT (cikti {_cikti_gun}, depo {_depo_gun})."
          f"\n           Bu bir kusur degil: kurulum depodan eski."
          f"\n           `python site/insa.py` ile yenileyin.")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

# SAYFAYI BESLEYEN ALANLA KARSILASTIR -- SUTUNLA DEGIL.
#
# Olculdu (2026-09-24): bu iddia iki sayfayi "bayat" diye bildirdi ve
# IKISI DE DOGRUYDU. Sebep karsilastirmanin kendisiydi: sayfa
# `haber.sayfa_veri` JSON'undan uretiliyor, ben ise `haber.tarih`
# SUTUNUYLA kiyasliyordum. 3770 kaydin 5'inde ikisi ayrisik --
# ucunde saat dilimi sinirindan (21:34 / 23:02 / 00:11 UTC), ikisinde
# periyodik bir yayinin sayfa yuku tazelenirken sutunun kalmasindan.
#
# Sayfanin okumadigi bir alanla kiyaslamak, kusuru degil FARKI olcer.
# Kusur olmadigi halde kirmizi yanan sinama gormezden gelinir; bu
# dosyanin kendi ustundeki yorum da bunu soyluyor.
def _sayfa_tarihi(kayit: dict) -> str:
    """Sayfanin GERCEKTEN bastigi tarih: `sayfa_veri` varsa o."""
    ham = kayit.get("sayfa_veri") or ""
    if ham:
        try:
            sv = (json.loads(ham).get("tarih") or "")[:10]
            if sv:
                return sv
        except (ValueError, TypeError):
            pass
    return (kayit.get("tarih") or "")[:10]


_yol_kayit: dict[str, dict] = {}
for _r in _ham:
    _y = _r["yayin_yolu"]
    if _y not in _yol_kayit or (_r["tarih"] or "") > (_yol_kayit[_y]["tarih"] or ""):
        _yol_kayit[_y] = _r

_bayat = []
for _k in _sonuc:
    _s = _CIKTI / _k["yol"].strip("/") / "index.html"
    if not _s.exists():
        continue
    _m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)',
                   _s.read_text(encoding="utf-8", errors="replace"))
    _kazanan = _yol_kayit.get(_k["yol"])
    if not _m or not _kazanan:
        continue
    _beklenen = _sayfa_tarihi(_kazanan)
    if _m.group(1) != _beklenen:
        _bayat.append((_k["yol"], _m.group(1), _beklenen))
if _bayat:
    print("\n  BAYAT SAYFALAR (yayinda / olmasi gereken):")
    for _b in _bayat[:8]:
        print(f"    {_b[0]}  {_b[1]} != {_b[2]}")
    print("\n  Not: son kurulum duzeltmeden ONCEKI kodla yapildiysa bu"
          " beklenen bir sonuctur; `python site/insa.py` ile yenileyin.")
esit(len(_bayat), 0, "her sayfa kendi adresinin EN YENI kaydini tasiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
