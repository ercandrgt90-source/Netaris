# -*- coding: utf-8 -*-
"""TEMA BELIRTECLERI: MOBIL ILE SITE AYNI PALETI KULLANMALI.

BU DOSYA NEDEN VAR
------------------
Mobil uygulama rengi `stil.css`ten okuyor. Ayristirici sessizce
yanlis bir blok okursa uygulama YANLIS PALETLE boyanir ve hicbir sey
patlamaz -- yalnizca site ile uygulama farkli gorunur.

Bu kurgusal bir risk degil: ayristiricinin ILK YAZIMI tam bunu yapti.
`@media print` blogundaki siyah-beyaz paleti (`--zemin #fff`,
`--yazi #000`) sitenin paleti sandi. Sinama onu yakaladi.

IKINCI IS: TABANDA EKSIK JETON ARAMAK
-------------------------------------
Olculdu (2026-09-30): bes jeton yalnizca `[data-tema]` bloklarinda
tanimliydi, taban `:root`ta yoktu. Tema damgasi yalnizca okur ACIKCA
secim yaptiginda yaziliyor; secmeyen okur -- COGUNLUK -- o renkleri
hic gormuyordu. Kusur sessizdi. Bugun sifir; bu sinama geri
donmesini engelliyor.

AG KULLANILMIYOR. DISKE YAZILMIYOR.
"""

from __future__ import annotations

import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

import tema_belirtec as T                           # noqa: E402

_gecti = 0
STIL = _KOK / "statik" / "stil.css"


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
print("1. YORUMLAR SOYULUYOR")
# Dosyada 610 yorum var ve 17'si suslu parantez iceriyor. Soyulmazsa
# "ic ice parantez yok" varsayimi kiriliyor ve bloklar kayiyor.
_ornek = """
/* yorum icinde suslu parantez: { --zemin: KANDIRMA; } */
:root { --zemin: #aaa; }
"""
esit(T.cikar(_ornek)["taban"], {"zemin": "#aaa"},
     "yorum içindeki jeton OKUNMUYOR")

print("")
print("2. @media print PALETI SITENIN PALETI DEGIL")
# AYRISTIRICININ ILK YAZIMI TAM BURADA DUSTU: baskinin siyah-beyaz
# paletini taban sandi ve uygulama #fff zeminle boyanacakti.
_ornek = """
:root { --zemin: #f3f2ee; --yazi: #17160f; }
@media print {
  :root { --zemin: #fff; --yazi: #000; --cizgi: #bbb; }
}
"""
_c = T.cikar(_ornek)
esit(_c["taban"]["zemin"], "#f3f2ee", "baskı paleti tabanı EZMİYOR")
esit(_c["taban"]["yazi"], "#17160f", "yazı rengi de ezilmiyor")
esit("cizgi" in _c["taban"], False,
     "yalnızca baskıda tanımlı jeton tabana GİRMİYOR")

print("")
print("3. prefers-contrast ve forced-colors de DISLANIYOR")
# Ucu de paleti bilincli olarak bozuyor; dogru CSS ama mobil temanin
# kaynagi olamaz.
for _kural in ("@media (prefers-contrast: more)",
               "@media (forced-colors: active)"):
    _ornek = f"""
:root {{ --vurgu: #09726d; }}
{_kural} {{
  :root {{ --vurgu: #000; }}
}}
"""
    esit(T.cikar(_ornek)["taban"]["vurgu"], "#09726d",
         f"{_kural} dışlanıyor")

print("")
print("4. KOYU TEMA IKI SECICIDEN DE KURULUYOR")
# Biri isletim sistemi koyu modunda (medya sorgusu icinde), oteki
# okur acikca koyu sectiginde (ust duzeyde). Yalnizca birini okumak
# okurun yarisinda yanlis palet demek.
_ornek = """
:root { --zemin: #f3f2ee; --vurgu: #09726d; --panel: #fff; }
@media (prefers-color-scheme: dark) {
  :root:not([data-tema="light"]) { --zemin: #14130f; --vurgu: #2dd4bf; }
}
:root[data-tema="dark"] { --panel: #1e1c17; }
"""
_c = T.cikar(_ornek)
esit(_c["koyu"]["zemin"], "#14130f", "medya sorgusundan geliyor")
esit(_c["koyu"]["vurgu"], "#2dd4bf", "vurgu da")
esit(_c["koyu"]["panel"], "#1e1c17", "damgalı seçiciden geliyor")
esit(_c["acik"]["zemin"], "#f3f2ee", "AÇIK tema koyudan etkilenmiyor")

print("")
print("5. CASCADE: SONRA GELEN ONCEYI EZIYOR")
# `:root` dosyada SEKIZ yerde geciyor. Tek blogu okuyup "palet bu"
# demek, asagidaki duzeltmeleri kacirmak olurdu.
_ornek = """
:root { --vurgu: #ESKI; }
:root { --vurgu: #YENI; }
"""
esit(T.cikar(_ornek)["taban"]["vurgu"], "#YENI", "son tanım kazanıyor")

print("")
print("6. ACIK VE KOYU HER IKISI DE TAM PALET")
# Uygulama tarafi iki sozlugu birlestirmek zorunda kalmasin; o
# birlestirmeyi unutmak yarim boyanmis bir ekran demek.
_ornek = """
:root { --zemin: #f3f2ee; --yazi: #17160f; --vurgu: #09726d; }
:root[data-tema="dark"] { --zemin: #14130f; }
"""
_c = T.cikar(_ornek)
esit(_c["koyu"].get("yazi"), "#17160f",
     "koyu temada DEVRALINAN jeton da var")
esit(_c["koyu"].get("vurgu"), "#09726d", "ezilmeyen jeton devralınıyor")

print("")
print("7. GERCEK stil.css -- ZORUNLU JETONLAR IKI TEMADA DA VAR")
if not STIL.is_file():
    print("  DUSTU  stil.css bulunamadi")
    raise SystemExit(1)
_ham = STIL.read_text(encoding="utf-8")
_c = T.cikar(_ham)
print(f"  taban {len(_c['taban'])} · acik {len(_c['acik'])} "
      f"· koyu {len(_c['koyu'])} jeton")
if len(_c["taban"]) < 40:
    print(f"  DUSTU  tabanda yalnizca {len(_c['taban'])} jeton var --")
    print("         ayristirici yanlis blok okuyor olabilir")
    raise SystemExit(1)
_gecti += 1
print("  gecti  taban palet makul buyuklukte")

for _ad in T.ZORUNLU:
    esit(bool(_c["acik"].get(_ad)), True, f"acik: --{_ad} var")
    esit(bool(_c["koyu"].get(_ad)), True, f"koyu: --{_ad} var")

print("")
print("8. GERCEK stil.css -- PALET BASKI PALETI DEGIL")
# Dogrudan olcut: taban zemin ile yazi, baskinin zorladigi saf
# siyah-beyaz OLMAMALI. Bu sinama ayristiricinin ilk yazimini
# yakalayan sinama.
esit(_c["taban"]["zemin"] in ("#fff", "#ffffff"), False,
     "taban zemin saf beyaz DEĞİL (baskı paleti kaçmadı)")
esit(_c["taban"]["yazi"] in ("#000", "#000000"), False,
     "taban yazı saf siyah DEĞİL")
# Koyu tema GERCEKTEN koyu olmali: bir ayrisma olursa bu tutar.
_k = _c["koyu"]["zemin"].lstrip("#")
if len(_k) == 6:
    _parlaklik = sum(int(_k[i:i + 2], 16) for i in (0, 2, 4)) / 3
    if _parlaklik > 80:
        print(f"  DUSTU  koyu tema zemini cok parlak ({_parlaklik:.0f})")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  koyu zemin gercekten koyu (parlaklik {_parlaklik:.0f})")

print("")
print("9. GERCEK stil.css -- TABANDA EKSIK TEMA JETONU YOK")
# Olculdu (2026-09-30): bes jeton yalnizca `[data-tema]` bloklarinda
# tanimliydi. Damgasiz okur -- cogunluk -- o renkleri hic gormuyordu.
_eksik = T.eksik_jetonlar(_ham)
if _eksik:
    print(f"  DUSTU  {len(_eksik)} jeton YALNIZCA tema blogunda tanimli:")
    for _e in _eksik[:12]:
        print(f"           --{_e}")
    print("         Tema damgasi olmayan okur bu renkleri GORMEZ.")
    raise SystemExit(1)
_gecti += 1
print("  gecti  her tema jetonu tabanda da tanimli")

print("")
print("10. besleme() sozlesmesi")
_b = T.besleme(STIL)
esit(_b["surum"], 1, "sürüm")
esit(_b["kaynak"], "site/statik/stil.css", "kaynak bildiriliyor")
esit(list(_b["zorunlu"]), list(T.ZORUNLU), "zorunlu liste dosyada")
esit(set(_b) >= {"acik", "koyu"}, True, "iki tema da var")
# Renk degerleri gecerli gorunmeli -- bozuk bir deger uygulamada
# sessizce seffaf bir yuzey demek.
_gecersiz = [f"{t}/{a}" for t in ("acik", "koyu")
             for a, d in _b[t].items()
             if a in T.ZORUNLU and not re.match(
                 r"^(#[0-9a-f]{3,8}|rgb|hsl|var\()", d.strip(), re.I)]
esit(_gecersiz, [], "zorunlu jetonların hepsi geçerli renk biçiminde")

print("")
print("11. MOBIL YEDEK PALETI CSS ILE BIRE BIR AYNI")
#
# Uygulama paleti `/v1/tema.json`dan okuyor ama ILK ACILISTA ag henuz
# cevap vermemis olabilir; o yuzden kaynakta bir yedek palet duruyor
# (`mobil/src/tema-yedek.ts`).
#
# YEDEK, PALETIN IKINCI BIR KOPYASIDIR -- yani tam olarak bu depoda
# pahaliya ogrenilen kusur sinifi: ayni kural iki yerde durur, biri
# duzelir, oteki unutulur. Renkte ayrilma HICBIR hata uretmez;
# yalnizca uygulama ile site farkli gorunur.
#
# Bu yuzden dosya elle duzenlenmiyor, URETILIYOR ve burada bire bir
# karsilastiriliyor. Ayrisirsa bu sinama kirmiziya doner ve cozum tek
# komut: `python site/tema_yedek_yaz.py`.
_YEDEK = _KOK.parent / "mobil" / "src" / "tema-yedek.ts"
if _YEDEK.is_file():
    _diskte = _YEDEK.read_text(encoding="utf-8")
    _uretilen = T.ts_yedek(STIL)
    if _diskte != _uretilen:
        print("  DUSTU  mobil yedek paleti stil.css ile AYRISMIS")
        print(f"         diskte {len(_diskte)} bayt, "
              f"uretilen {len(_uretilen)} bayt")
        print("         Cozum: python site/tema_yedek_yaz.py")
        raise SystemExit(1)
    _gecti += 1
    print("  gecti  yedek palet CSS ile bire bir ayni")
    # Yedek, zorunlu jetonlarin HEPSINI tasimali.
    for _ad in T.ZORUNLU:
        esit(f'"{_ad}":' in _diskte, True, f"yedekte --{_ad} var")
else:
    # ATLANMIYOR, DUSUYOR. Dosya yoksa uygulama ilk karede renksiz
    # basar; "dosya yok" sessizce gecilecek bir durum degil.
    print(f"  DUSTU  mobil yedek paleti yok: {_YEDEK}")
    print("         Cozum: python site/tema_yedek_yaz.py")
    raise SystemExit(1)

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
