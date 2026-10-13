# -*- coding: utf-8 -*-
"""OKUMA KILAVUZU YANLIS SIRKETE YAZILMAMALI.

BU DOSYA NEDEN VAR -- OLCULDU, YAYINDAYDI (2026-10-13)
------------------------------------------------------
Kilavuz yalnizca `sektor_tr`ye bakiyordu. Kaynak ise her sirkete
ALT SEKTOR de veriyor (defterde 354 sirkette dolu) ve ayni sektorun
icinde is modelleri birbirine hic benzemiyor:

    İletişim (6 sirket)
        TTKOM                Telecom Services
        FENER, BJKAS, TSPOR  Entertainment   <- futbol kulubu
        BIGTK, IHYAY         Publishing      <- yayincilik

İletişim kilavuzunun basligi "Telekomünikasyonda borç ve amortisman
neden yüksektir" ve metninde "abonelik modeli sayesinde faaliyet
nakit akışı net kârdan daha istikrarlıdır" yaziyor. Fenerbahce icin
bu cumle yanlis.

    Gayrimenkul (36 sirket)
        24 sirket  REIT - ...                 <- GYO
        12 sirket  Real Estate - Development / Diversified

Gayrimenkul kilavuzunun basligi "Gayrimenkul yatırım ortaklığında
kâr nereden gelir" ve metni GYO portfoy degerlemesini anlatiyor.
Bir gayrimenkul GELISTIRICISI icin yanlis cerceve.

Olculdu: yayindaki 16 bilanco sayfasi kapsam disi kilavuz tasiyor.

ILKE ZATEN DOSYANIN KENDISINDE YAZILI
-------------------------------------
`blok` doc metni: "Yanlis bir okuma kilavuzu, kilavuzsuzluktan
kotudur -- okur ona guvenip yanlis kalemi okur." Bu sinama ayni
ilkeyi ALT SEKTOR duzeyinde uyguluyor.

ALT SEKTOR BILINMIYORSA KISITLAMA YOK: ayrim yapmanin ispat yuku
ayrim yapanda.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import sektor_okuma as so                          # noqa: E402

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


print("1. Kapsam disi alt sektore kilavuz YAZILMIYOR")
esit(bool(so.blok("İletişim", "Telecom Services")), True,
     "telekoma telekom kilavuzu")
esit(so.blok("İletişim", "Entertainment"), None,
     "futbol kulubune telekom kilavuzu YAZILMIYOR")
esit(so.blok("İletişim", "Publishing"), None,
     "yayinciya telekom kilavuzu YAZILMIYOR")
esit(so.markdown("İletişim", "Entertainment"), [],
     "markdown da bos doniyor")
esit(bool(so.markdown("İletişim", "Telecom Services")), True,
     "kapsam icindeyken markdown uretiliyor")

print("")
print("2. GYO kilavuzu gelistiriciye yazilmiyor")
esit(bool(so.blok("Gayrimenkul", "REIT - Diversified")), True,
     "GYO'ya GYO kilavuzu")
esit(so.blok("Gayrimenkul", "Real Estate - Development"), None,
     "gelistiriciye GYO kilavuzu YAZILMIYOR")
esit(so.blok("Gayrimenkul", "Real Estate - Diversified"), None,
     "karma gayrimenkule GYO kilavuzu YAZILMIYOR")
# ONEK KURALI: defterde olmayan bir GYO turu de kapsamda olmali.
esit(bool(so.blok("Gayrimenkul", "REIT - Office")), True,
     "ONEK kurali: defterde henuz olmayan GYO turu de kapsamda")

print("")
print("3. ALT SEKTOR BILINMIYORSA kilavuz susturulmuyor")
esit(bool(so.blok("İletişim", "")), True, "bos alt sektor kisitlamiyor")
esit(bool(so.blok("İletişim")), True, "hic verilmezse kisitlamiyor")
esit(so.kapsamda("İletişim", None), True, "None da kisitlamiyor")

print("")
print("4. Kisitlanmayan sektorde her alt sektor kapsamda")
esit(bool(so.blok("Sanayi", "Conglomerates")), True, "sanayi serbest")
esit(bool(so.blok("Finans", "Insurance - Life")), True, "finans serbest")
esit(so.blok("Tanimsiz sektor", "X"), None, "tanimsiz sektor zaten None")

print("")
print("5. ALT_KAPSAM yalnizca TANIMLI kilavuzlara atif yapiyor")
# Olmayan bir sektore kapsam yazmak sessiz bir yazim hatasi olurdu:
# kisitlama hicbir seye uygulanmaz ve kimse fark etmez.
for s in so.ALT_KAPSAM:
    if s not in so.OKUMA:
        print(f"  DUSTU  ALT_KAPSAM'da kilavuzu olmayan sektor: {s!r}")
        raise SystemExit(1)
_gecti += 1
print(f"  gecti  {len(so.ALT_KAPSAM)} kapsam kaydi da tanimli sektore ait")

print("")
print("6. Kapsam, defterdeki GERCEK alt sektorlere karsi olculuyor")
_DEFTER = _KOK.parent / "kaynak" / "sirketler.json"
if _DEFTER.is_file():
    d = json.loads(io.open(_DEFTER, encoding="utf-8").read())["sirketler"]
    kapsamsiz: dict[str, set] = {}
    for v in d.values():
        s, a = v.get("sektor_tr") or "", v.get("alt_sektor") or ""
        if not s or not a or s not in so.ALT_KAPSAM:
            continue
        if not so.kapsamda(s, a):
            kapsamsiz.setdefault(s, set()).add(a)
    # Kisitlama GERCEKTEN bir seyi eliyor olmali. Elemiyorsa kurali
    # yazmak bos bir jest; esik gecen ama hicbir sey suzmeyen bir
    # denetim bu depoda daha once goruldu.
    esit(bool(kapsamsiz), True,
         "kisitlama defterde GERCEKTEN eliyor (bos jest degil)")
    for s, kume in sorted(kapsamsiz.items()):
        print(f"         {s}: kapsam dışı {len(kume)} alt sektör "
              f"({', '.join(sorted(kume))})")
    esit("Entertainment" in kapsamsiz.get("İletişim", set()), True,
         "futbol kulupleri gercekten kapsam disinda")
else:
    print("  ATLANDI  defter yok (sirketler.json)")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
