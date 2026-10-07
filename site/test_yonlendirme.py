# -*- coding: utf-8 -*-
"""SILINEN SAYFANIN ADRESI 404 VERMEMELI.

BU DOSYA NEDEN VAR
------------------
`haber_botu/tekrar_temizle.py` ayni haberin ikinci kaydini yayimdan
dusuruyor ve kendi bas yorumunda su guvenceyi veriyor:

  "Kaldirilan sayfalar yayimlanmisti; arama motorlari ve paylasilan
   baglantilar onlari biliyor. Silip birakmak, okuru bos sayfaya
   gondermek olurdu. Her silinen adres icin KALAN adrese yonlendirme
   yaziliyor ve worker onu 301 olarak sunuyor."

OLCULDU (2026-10-07) ve bu guvence GERCEK DEGILDI:

  site/yonlendirme.json       duruyordu -- 2 bayt, yani bos
  onu okuyan satir            YOKTU (butun depoda sifir)
  worker.js "yonlendirme"     bos bir basliktan ibaretti
  site/cikti/_redirects       yalnizca elle yazilmis iki satir

Yani araci biri calistirsaydi silinen HER sayfa dogrudan 404
verecekti. Kural yaziliydi, uygulanmiyordu -- bu depoda defalarca
tekrarlanan kusur sinifi.

NE SINANIYOR
------------
Kural artik `insa.yonlendirme_satirlari` icinde ve BURADA SENTETIK
durumlarla sinaniyor. Gercek `yonlendirme.json` su an BOS; ona
bakan bir sinama hicbir sey elemezdi -- "gecti" derdi ve kural yine
uygulanmiyor olurdu.

  1. Gecerli kayit 301 satirina ceviriliyor.
  2. HEDEFI URETILMEMIS kayit atlaniyor -- 301, 404'e giden zincir
     olurdu.
  3. KAYNAGI URETILMIS kayit atlaniyor -- duran bir sayfayi
     yonlendirmek, yayimdaki icerigi gizlemek demek.
  4. Bolum koku ("/haber/") iki tarafta da reddediliyor.
  5. Zincir COZULUYOR: A -> B, B -> C ise A dogrudan C'ye.
  6. Dongu (A -> B -> A) sonsuz donguye girmiyor.
  7. Uretilen `_redirects` dosyasinda zincir ve kendine yonlendirme
     YOK -- bu, veriden bagimsiz bir sozlesme.
"""

from __future__ import annotations

import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import insa                                      # noqa: E402

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
print("Yonlendirme kurali")

URETILEN = ["/haber/kalan/", "/haber/baska/", "/gundem/"]

# 1. Gecerli kayit
sat, atlanan = insa.yonlendirme_satirlari({"/haber/giden/": "/haber/kalan/"},
                                          URETILEN)
esit(sat, ["/haber/giden/  /haber/kalan/  301"], "gecerli kayit 301 oluyor")
esit(atlanan, 0, "gecerli kayit atlanmiyor")

# 2. Hedef uretilmemis
sat, atlanan = insa.yonlendirme_satirlari({"/haber/giden/": "/haber/yok/"},
                                          URETILEN)
esit(sat, [], "hedefi uretilmemis kayit yazilmiyor")
esit(atlanan, 1, "atlanan sayiliyor")

# 3. Kaynak hala uretiliyor
sat, _ = insa.yonlendirme_satirlari({"/haber/kalan/": "/haber/baska/"},
                                    URETILEN)
esit(sat, [], "duran sayfa yonlendirilmiyor")

# 4. Bolum koku
sat, _ = insa.yonlendirme_satirlari({"/haber/": "/haber/kalan/"}, URETILEN)
esit(sat, [], "bolum koku KAYNAK olamaz")
sat, _ = insa.yonlendirme_satirlari({"/haber/giden/": "/gundem/"}, URETILEN)
esit(sat, [], "bolum koku HEDEF olamaz")

# 5. Zincir
sat, _ = insa.yonlendirme_satirlari(
    {"/haber/a/": "/haber/b/", "/haber/b/": "/haber/kalan/"}, URETILEN)
esit(sorted(sat), ["/haber/a/  /haber/kalan/  301",
                   "/haber/b/  /haber/kalan/  301"],
     "zincir cozuluyor (a -> b -> kalan)")

# 6. Dongu
sat, _ = insa.yonlendirme_satirlari({"/haber/a/": "/haber/b/",
                                     "/haber/b/": "/haber/a/"}, URETILEN)
esit(sat, [], "dongu sonsuza girmiyor")

# 7. Uretilen dosyada zincir ve kendine yonlendirme yok
_D = _SITE / "cikti" / "_redirects"
if not _D.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_kaynak = {}
for _s in _D.read_text(encoding="utf-8").splitlines():
    _p = _s.split()
    if len(_p) >= 2:
        _kaynak[_p[0]] = _p[1]
esit([k for k, h in _kaynak.items() if k == h], [],
     "_redirects icinde kendine yonlendirme yok")
esit([k for k, h in _kaynak.items() if h in _kaynak], [],
     "_redirects icinde zincir yok")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
