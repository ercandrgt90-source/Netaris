# -*- coding: utf-8 -*-
"""GENEL OKUMA UCLARI ACIK, KIMLIKLI UCLAR KAPALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-10-20): mobil uygulamanin WEB cikisi canli tel akisini
ve senaryo listesini cekemiyordu --

    Access to fetch at 'https://netaris.net/api/tel?limit=12' from
    origin '...' has been blocked by CORS policy

Yerli iOS/Android fetch'i tarayicinin kaynak kisitina TABI DEGIL, yani
telefonda calisiyordu. Eksiklik tam bu yuzden gorunmuyordu: ozellik
"calisiyor" gibi duruyor, yalnizca bir yuzeyde hic calismiyor.

Cozum `worker.js` icinde `acikYanit()` -- ama asil mesele COZUM DEGIL,
cozumun GENISLEMEMESI.

NICIN TEHLIKELI
---------------
`access-control-allow-origin: *` bir uca verildiginde, BASKA BIR
SITEDEKI betik o uctan yanit okuyabilir. Kimlik istemeyen genel bir
okma ucunda bunun bedeli yok -- veri zaten herkese acik. Kimlikli bir
uctaysa (`/api/ben`, `/api/begenilerim`) bedeli dogrudan: ziyaretcinin
OTURUMUYLA gelen yanit yabanci bir sayfaya acilmis olur.

Yani buradaki iki iddia simetrik degil. Birincisi bir KOLAYLIGI,
ikincisi bir SINIRI koruyor; ikincisi kirilirsa ortaya guvenlik
kusuru cikar.

NE SINANIYOR
------------
1. Izin listesi yalnizca kimlik ISTEMEYEN uclari sayiyor.
2. `acikYanit` YALNIZCA o uclarda cagriliyor -- baska hicbir yerde.
3. Uygulamanin cagirdigi genel uclar listede (yoksa web'de yine
   bozuk kalir ve kimse farketmez).
"""

from __future__ import annotations

import pathlib
import re

_KOK = pathlib.Path(__file__).resolve().parent.parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_w = (_KOK / "site" / "worker.js").read_text(encoding="utf-8")

#: Kimlik isteyen ya da YAZAN uclar. Hicbiri acilamaz.
#:
#: Liste elle yaziliyor ve bilerek: kaynaktan turetilseydi (ornegin
#: "oturum kapisindan sonra gelenler") kapinin kendisi degistiginde
#: iddia da sessizce kuculurdu -- hareketli hedef.
KAPALI_KALMALI = (
    "ben", "begeni", "begenilerim", "giris", "cikis", "hesap-sil",
    "disari-aktar", "senaryo", "yayimlandi", "goruntulenme", "cihaz",
)

print("Izin listesi")
_m = re.search(r"const GENEL_OKUMA = new Set\(\[(.*?)\]\)", _w, re.S)
esit(_m is not None, True, "GENEL_OKUMA listesi bulundu")
_acik = re.findall(r'"([^"]+)"', _m.group(1))
print(f"  acik uclar: {_acik}")
esit(len(_acik) > 0, True, f"liste dolu ({len(_acik)} uc)")

_sizan = [u for u in _acik if u in KAPALI_KALMALI]
if _sizan:
    print(f"\n  KIMLIKLI UC ACILMIS: {_sizan}")
esit(_sizan, [], "kimlik isteyen hicbir uc listede degil")

print("\n`acikYanit` yalnizca o uclarda")
# Her `acikYanit(` cagrisinin AYNI SATIR GRUBUNDA hangi ucun
# yonlendirildigine bakiliyor. Cagrinin kendisi bir sey kanitlamaz;
# HANGI yolda cagrildigi kanitlar.
_satirlar = _w.splitlines()
_cagri_uclari: list[str] = []
for _i, _s in enumerate(_satirlar):
    if "acikYanit(" not in _s or "function acikYanit" in _s:
        continue
    # Yonlendirme kosulu ya ayni satirda ya bir onceki satirda.
    _blok = (_satirlar[_i - 1] if _i else "") + " " + _s
    _y = re.search(r'y === "([^"]+)"', _blok)
    _cagri_uclari.append(_y.group(1) if _y else f"(satir {_i + 1}: yol yok)")

print(f"  cagri yerleri: {_cagri_uclari}")
esit(len(_cagri_uclari) > 0, True,
     f"acikYanit gercekten kullaniliyor ({len(_cagri_uclari)})")
_izinsiz = [u for u in _cagri_uclari if u not in _acik]
if _izinsiz:
    print(f"\n  IZIN LISTESINDE OLMAYAN YERDE ACILMIS: {_izinsiz}")
esit(_izinsiz, [], "acikYanit yalnizca GENEL_OKUMA uclarinda cagriliyor")

print("\nUygulamanin cagirdigi genel uclar listede")
# Burasi ters yondeki kusuru tutuyor: uc listeden DUSERSE web'de
# sessizce bozulur ve kimse farketmez -- telefonda calismaya devam
# ettigi icin.
_app = []
for _p in (_KOK / "mobil" / "src").glob("*.ts"):
    _app.append(_p.read_text(encoding="utf-8"))
_kaynak = "\n".join(_app)
GEREKEN = {"tel": "/api/tel", "tel/durum": "/api/tel/durum",
           "senaryo/hepsi": "/api/senaryo/hepsi"}
_eksik = [u for u, iz in GEREKEN.items()
          if iz in _kaynak and u not in _acik]
if _eksik:
    print(f"\n  UYGULAMA CAGIRIYOR AMA ACIK DEGIL: {_eksik}")
esit(_eksik, [], f"uygulamanin genel uclari acik ({len(GEREKEN)} uc)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
