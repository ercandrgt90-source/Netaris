# -*- coding: utf-8 -*-
"""ISTENEN AMA YAPILMAYAN DAGITIM, YESIL BIR KOSU OLAMAZ.

BU DOSYA NEDEN VAR -- OLCULDU (2026-10-18)
------------------------------------------
CI gunlugunden okundu:

    Çıktıya bakan sınamalar
      DUSTU  GELECEK tarihli lastmod yok
    CIKTIYA BAKAN SINAMALAR DUSTU -- dagitim YAPILMADI.
    Site uretimi basarisiz -- dagitim YAPILMADI

Ve is **YESIL** dondu. Site UC SAAT boyunca yayimlanmadi; hicbir
sey bunu duyurmadi. Kullanici uyurken oldu.

IKI AYRI DELIK VARDI
--------------------
1. `sonuclar["Dağıtım"]` YALNIZCA dagitim gercekten kostugunda
   yaziliyordu. Kapi dagitimi engelledigi anda anahtar hic
   olusmuyordu ve `sonuclar.get("Dağıtım") is False` ifadesi
   `None is False` -> False donuyordu. Yani "dagitim yapilmadi"
   kritik hata SAYILMIYORDU.

   "Dagitim istendi ve olmadi" ile "dagitim istenmedi" ayri
   seylerdir. Ikincisi normal, birincisi arizadir.

2. Dagitimi DURDURAN iki kapi (`Çıktı denetimi`,
   `Çıktı sınamaları`) KRITIK listesinde yoktu. Oysa kritik
   olmanin olcutu dosyada yazili: "kritik olan: site uretilebildi
   mi, yorum kapisi acik mi, DAGITIM YAPILDI MI". Dagitimi
   durduran her kapi tanim geregi bu olcutun icinde.

NE SINANIYOR
------------
`calistir.py` kaynagi okunuyor; ag, dagitim ve uzun kosu YOK.

Olcut DAVRANIS: dagitimi `ok = False` ile engelleyen her adim
KRITIK listesinde olmali. Liste kaynaktan cikariliyor, buraya
kopyalanmiyor -- kopyalansaydi yarin eklenen bir kapi sessizce
disarida kalirdi.
"""

from __future__ import annotations

import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
BETIK = KOK / "calistir.py"

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


S = BETIK.read_text(encoding="utf-8")

print("")
print("1. DAGITIM ATLANINCA 'Dağıtım' BASARISIZ ISARETLENIYOR")
#
# `elif args.yayinla:` dali, dagitim istenmis ama kapi kapali
# oldugunda kosuyor. O dal `sonuclar["Dağıtım"] = False` yazmazsa
# kosu yesil doner.
_dal = re.search(
    r"elif args\.yayinla:(.*?)(?=\n    [^\s#])", S, re.S)
esit(bool(_dal), True, "elif args.yayinla dali bulundu")
if _dal:
    esit('sonuclar["Dağıtım"] = False' in _dal.group(1), True,
         "atlanan dagitim BASARISIZ olarak kaydediliyor")

print("")
print("2. DAGITIMI DURDURAN HER ADIM KRITIK LISTESINDE")
#
# Liste KAYNAKTAN cikariliyor. Buraya kopyalamak, yarin eklenen bir
# kapinin sessizce disarida kalmasi demekti -- ve sinama yine yesil
# gorunurdu.
_k = re.search(r"KRITIK = \((.*?)\)", S, re.S)
esit(bool(_k), True, "KRITIK listesi bulundu")
_kritik = set(re.findall(r'"([^"]+)"', _k.group(1)))
print(f"  KRITIK: {sorted(_kritik)}")

# `ok = False` yazan her blogun hemen ustundeki
# `sonuclar["..."] = <ad>` atamasi, o adimin adini veriyor.
_durduran = set()
for m in re.finditer(r'sonuclar\["([^"]+)"\]\s*=', S):
    ad = m.group(1)
    # Atamadan sonraki 400 karakterde `ok = False` var mi?
    pencere = S[m.end():m.end() + 400]
    if re.search(r"^\s*ok = False", pencere, re.M):
        _durduran.add(ad)
print(f"  dagitimi durduran: {sorted(_durduran)}")

esit(len(_durduran) >= 3, True, "en az uc durdurucu adim bulundu")
_eksik = sorted(_durduran - _kritik)
esit(_eksik, [],
     "dagitimi durduran her adim KRITIK listesinde"
     + (f" -- EKSIK: {_eksik}" if _eksik else ""))

print("")
print("3. 'Dağıtım' KRITIK LISTESINDE")
esit("Dağıtım" in _kritik, True, "Dağıtım kritik sayiliyor")

print("")
print("4. CIKIS KODU KRITIK HATAYA BAKIYOR")
esit(bool(re.search(
    r"kritik_hata = \[k for k in KRITIK if sonuclar\.get\(k\) is False\]",
    S)), True, "kritik_hata KRITIK listesinden kuruluyor")
# Kritik hata varken 1 donmeli.
esit(bool(re.search(r"if kritik_hata[\s\S]{0,400}?return 1", S)), True,
     "kritik hata varsa cikis kodu 1")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
