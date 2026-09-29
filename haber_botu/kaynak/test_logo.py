# -*- coding: utf-8 -*-
"""YANLIS LOGO BASMAK, LOGO BASMAMAKTAN KOTUDUR.

BU DOSYA NEDEN VAR
------------------
`logo.py` (443 satir) iki agir kurali yaziyor ve HICBIRINI hicbir
sinama tutmuyordu:

  LISANS   "YALNIZCA kamu mali ve CC0. 'Adil kullanim' gerekcesiyle
            duran logolar ALINMIYOR: o gerekce Wikipedia'ya ait ve
            bize gecmez."
  ESLESME  "Kural dort parcali ve hepsi ZORUNLU."

Ikisinin de bedeli somut. Dosyanin kendi ornegi: "Garanti BBVA logo"
sorgusu su sonucu da veriyor --

    File:Logo Garanti Koza Tournament of Champions Sofia 2013.svg

Bu bir TENIS TURNUVASI. Dosyanin kendi ifadesiyle: "Yanlis logo
basmak, alakasiz fotograftan DAHA kotudur: okur onu sirketin kendi
isareti sanar."

TARIHCE, KURALIN NEDEN KORUNMASI GEREKTIGINI SOYLUYOR
-----------------------------------------------------
Ikinci madde ("dosya adinda 'logo' gececek") BIR ARA GEVSETILMIS --
`File:Garanti BBVA 2019.svg` gibi dogru logolar eleniyordu diye. Ama
gevseklik "cok daha fazla YANLIS eslesme" getirmis ve geri alinmis.
Yani bu kural bir kez zaten esnetildi; zorlayicisi olmadan yeniden
esnetilebilir ve kimse fark etmez.

NEDEN BU SINAMA GUVENLI
-----------------------
`_eslesiyor` ve `_uygun_lisans` saf: dizge alir, boolean doner. Ag,
veritabani, uretilmis cikti YOK. Bu depoda her yeni kapi dagitimi
durdurma riski tasiyor (bkz. `yorum_denetimi.py` tarihcesi: bir kapi
siteyi bir gun durdurdu ve 18 ihlalin 18'i sahteydi). Belirlenimci
bir kapi o riski tasimiyor.

NE SINANIYOR
------------
1. Lisans suzgeci: PD/CC0 KABUL, adil kullanim ve telifli RED.
2. Belgelenmis tenis turnuvasi ornegi REDDEDILIYOR.
3. Dort maddenin HER BIRI tek basina gerekli.
4. Kisa anahtar (<4 harf) hicbir zaman kabul edilmiyor.
5. Kelime siniri: "ard" -> "bundesarbeitskreis" ICINDE eslesmiyor.
6. Gecerli logo KABUL EDILIYOR -- kural her seyi elemiyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK.parent)]

from kaynak import logo  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def lis(ad: str) -> bool:
    return logo._uygun_lisans({"LicenseShortName": {"value": ad}})


print("\nLisans suzgeci")
for _ad in ("Public domain", "CC0", "PD-textlogo", "public domain"):
    esit(lis(_ad), True, f"kabul: {_ad}")
# ADIL KULLANIM ALINMIYOR -- o gerekce Wikipedia'ya ait, bize gecmez.
for _ad in ("Fair use", "Non-free logo", "CC BY-SA 4.0", "All rights reserved",
            "GFDL", "CC BY 3.0", ""):
    esit(lis(_ad), False, f"red: {_ad or '(bos)'}")

print("\nBelgelenmis YANLIS eslesme reddediliyor")
# Dosyanin kendi ornegi. Bu satir kirmizi yanarsa, site bir tenis
# turnuvasinin logosunu Garanti'nin isareti diye basiyor demektir.
esit(logo._eslesiyor(
    "File:Logo Garanti Koza Tournament of Champions Sofia 2013.svg",
    "garanti"), False, "tenis turnuvasi logosu REDDEDILIYOR")

print("\nGecerli logo KABUL EDILIYOR (kural her seyi elemiyor)")
esit(logo._eslesiyor("File:Garanti BBVA logo.svg", "garanti"), True,
     "duz logo dosyasi kabul")
esit(logo._eslesiyor("File:Aselsan logo.png", "aselsan"), True,
     "kisa ad + logo kabul")

print("\nDort maddenin HER BIRI gerekli")
# 1. Gurultu kelimesi
esit(logo._eslesiyor("File:Aselsan logo sponsor.svg", "aselsan"), False,
     "1. gurultu kelimesi ('sponsor') eliyor")
esit(logo._eslesiyor("File:Aselsan logo stadium.svg", "aselsan"), False,
     "1. gurultu kelimesi ('stadium') eliyor")
# 1b. Tarihce yili
esit(logo._eslesiyor("File:Aselsan logo 1975.svg", "aselsan"), False,
     "1b. 2000 oncesi yil eliyor (tarihce logosu)")
esit(logo._eslesiyor("File:Aselsan logo 1933-1956.svg", "aselsan"), False,
     "1b. yil araligi eliyor")
# Ama GUNCEL surum yili elenmemeli -- suzgec fazla genisti, daraltildi.
esit(logo._eslesiyor("File:Garanti BBVA logo 2019.svg", "garanti"), True,
     "1b. 2000 SONRASI yil ELEMIYOR (dogru logo korunuyor)")
# 2. "logo" kelimesi
esit(logo._eslesiyor("File:Aselsan.svg", "aselsan"), False,
     "2. dosya adinda 'logo' yoksa red")
# 3. Kelime siniri
esit(logo._eslesiyor("File:Bundesarbeitskreis logo.svg", "ard"), False,
     "3. anahtar KELIME ICINDE eslesmiyor")
esit(logo._eslesiyor("File:Turkcell logo.svg", "turkcel"), False,
     "3. kismi anahtar eslesmiyor")
# 4. Kisa dosya adi
esit(logo._eslesiyor(
    "File:Aselsan logo used by the company since the year two.svg",
    "aselsan"), False, "4. bes kelimeden uzun dosya adi red")

print("\nKisa anahtar HICBIR ZAMAN kabul edilmiyor")
# Uc harfli anahtar dunyada yuzlerce seyin kisaltmasi.
for _k in ("eth", "ard", "tr", "a"):
    esit(logo._eslesiyor(f"File:{_k} logo.svg", _k), False,
         f"red: {len(_k)} harfli anahtar ({_k})")
esit(logo._eslesiyor("File:Ford logo.svg", "ford"), True,
     "dort harfli anahtar kabul (sinir 4'te)")

print("\nKONTROLLERIN KENDISI CALISIYOR MU")
# Her seye False donen bir eslestirici bu dosyayi gecemez: yukarida
# kabul edilmesi gereken dort ornek var. Tersini de kanitliyoruz.
_kabul = logo._eslesiyor("File:Garanti BBVA logo.svg", "garanti")
_ret = logo._eslesiyor("File:Garanti BBVA.svg", "garanti")
esit(_kabul != _ret, True, "eslestirici AYRIM yapiyor (sabit cevap degil)")
esit(any(lis(a) for a in ("CC0",)), True, "lisans suzgeci kabul de ediyor")
esit(all(not lis(a) for a in ("Fair use",)), True,
     "lisans suzgeci red de ediyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
