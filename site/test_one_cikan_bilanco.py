# -*- coding: utf-8 -*-
"""BILANCO ANALIZI "BUGUNUN ONEMLI GELISMELERI"NE GIRIYOR -- PUAN UYDURMADAN.

BU DOSYA NEDEN VAR
------------------
Kullanici istedi: "bilancolari da aciklandikca gunun onemli haberleri
icine alabilir miyiz".

Bolum puana gore seciyor (`one_cikan_haberler` -> `onem >= NORMAL`).
Bilanco analizlerinin ise puani YOK ve bu bilincli bir karar:
`yayin.yaz_sektorel` doc metni "skor esikleri her sektor icin kalibre
edilmedi, kalibre edilmemis bir skoru yayimlamak olculmemis bir seyi
olculmus gibi gostermek olur" diyor. Olculdu (2026-10-13): 268
bilanco sayfasinin HICBIRINDE `onem` alani yok, yani bolume yapisal
olarak hic giremiyorlardi.

COZUM PUAN UYDURMAK DEGIL. Bir sirketin bilanco aciklamasi gunun
gelismesidir; bunu soylemek icin ona sayi vermek gerekmiyor. Bu
yuzden puanli haberlerle YARISTIRILMIYOR:

  * MANSET her zaman puanli bir haber kaliyor,
  * alti kartin SON ikisi bilancoya ayriliyor, onlerine gecmiyor.

YALNIZCA BUGUN. Bolumun adi "BUGUNUN onemli gelismeleri"; eski bir
analizi oraya koymak bolumun kendi vaadini bozar (ayni gerekce
`ONE_CIKAN_TAZE_SAAT` icin de yazili).
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import insa                                        # noqa: E402

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


class SahteAnaliz:
    """`Analiz` NESNE, sozluk DEGIL.

    Ilk yazim `.get()` kullaniyordu ve uretimde AttributeError
    verirdi; sahte veriyle degil GERCEK veriyle denenince ortaya
    cikti. Bu sahte sinif da bu yuzden sozluk degil nesne.
    """

    def __init__(self, kod, tarih, donem="2026 2. çeyrek",
                 kategori="Bilanço Analizi", baslik="", ozet="",
                 foto="", tarih_tr="", yol=None):
        self.kod = kod
        self.tarih = tarih
        self.tarih_tr = tarih_tr or tarih
        self.donem = donem
        self.kategori = kategori
        self.baslik = baslik or f"{kod} {donem} bilanço analizi"
        self.ozet = ozet or "Özet cümlesi."
        self.foto = foto
        self._yol = yol if yol is not None else f"/analiz/{kod.lower()}/"

    @property
    def yol(self):
        return self._yol


BUGUN = "2026-10-13"

print("")
print("1. YALNIZCA BUGUNUN bilanco analizleri")
_a = [
    SahteAnaliz("AAAA", BUGUN),
    SahteAnaliz("BBBB", BUGUN),
    SahteAnaliz("CCCC", "2026-10-12"),            # dun
    SahteAnaliz("DDDD", BUGUN, kategori="Makro"),  # bilanco degil
    SahteAnaliz("EEEE", BUGUN, yol=""),            # sayfasi yok
]
_b = insa.bilanco_one_cikanlar(_a, BUGUN)
esit([x["kurum"] for x in _b], ["BBBB", "AAAA"],
     "dun, makro ve sayfasiz olanlar ELENDI")
# Verilen gun NE ISE o seciliyor: dun sorulursa dunun analizi gelir.
esit([x["kurum"] for x in insa.bilanco_one_cikanlar(_a, "2026-10-12")],
     ["CCCC"], "verilen gun ne ise o seciliyor")
esit(insa.bilanco_one_cikanlar(_a, "2026-10-11"), [],
     "o gun bilanco yoksa bos -- bolum zorla doldurulmuyor")
esit(insa.bilanco_one_cikanlar(_a, ""), [], "gun verilmezse bos")
esit(insa.bilanco_one_cikanlar(_a, BUGUN, en_cok=0), [], "slot sifirsa bos")

print("")
print("2. SLOT SINIRI -- bolum bilancoya donmuyor")
_cok = [SahteAnaliz(f"K{i:03d}", BUGUN) for i in range(40)]
esit(len(insa.bilanco_one_cikanlar(_cok, BUGUN)), insa.BILANCO_ONE_CIKAN,
     f"bir gunde 40 bilanco olsa da {insa.BILANCO_ONE_CIKAN} kart")

print("")
print("3. Kart alanlari sablonun bekledigi gibi")
_k = insa.bilanco_one_cikanlar(
    [SahteAnaliz("TTKOM", BUGUN, foto="/f.jpg", tarih_tr="13 Ekim 2026")],
    BUGUN)[0]
esit(_k["konu"], "Bilanço", "rozet 'Bilanço'")
esit(_k["kurum"], "TTKOM", "kurum yerine HISSE KODU")
esit(_k["tarih_gorunur"], "13 Ekim 2026", "tarih_tr -> tarih_gorunur")
esit("katman" in _k, False,
     "katman YOK -- 'kritik' rozetini yalnizca puanlama verebilir")
esit(insa.kart_turu(_k), insa.KART_TURU.get("Bilanço", insa.KART_VARSAYILAN),
     "kart_turu suzgeci cokmuyor")
# `an` YAZILMIYOR: bilanco sayfasinda saat yok, sablon o durumda
# goreli zaman yerine tarihi basiyor.
esit("an" in _k, False, "saat damgasi UYDURULMUYOR")

print("")
print("4. MANSET puanli haber kaliyor, bilanco KUYRUKTA")
_haber = [{"yol": f"/h{i}/", "baslik": f"haber {i}", "onem": 50}
          for i in range(10)]
_m = insa.one_cikan_birlestir(_haber, _b)
esit(_m[0]["baslik"], "haber 0", "manset puanli haber")
esit([x.get("kurum") or x["baslik"] for x in _m[:7]],
     ["haber 0", "haber 1", "haber 2", "haber 3", "haber 4",
      "BBBB", "AAAA"],
     "bilanco alti kartin SON ikisinde")
esit(len(_m), len(_haber) + len(_b), "hicbir haber DUSURULMEDI")

print("")
print("5. Bilanco yoksa liste AYNEN kaliyor")
esit(insa.one_cikan_birlestir(_haber, []), _haber, "bos bilancoda degisme yok")

print("")
print("6. Bolum az dolduysa bilanco BOSLUGA ekleniyor")
# Uc haber + iki bilanco = bes kalem; kimse yerinden edilmiyor.
_az = _haber[:3]
_m2 = insa.one_cikan_birlestir(_az, _b)
esit([x.get("kurum") or x["baslik"] for x in _m2],
     ["haber 0", "haber 1", "haber 2", "BBBB", "AAAA"],
     "kimsenin yerini almiyor")
# Tek haber varsa manset yine haber kaliyor.
_m3 = insa.one_cikan_birlestir(_haber[:1], _b)
esit(_m3[0]["baslik"], "haber 0", "tek haber varsa manset yine O")
esit(len(_m3), 3, "bilanco arkasina ekleniyor")

print("")
print("7. Haber hic yoksa bilanco manset OLMUYOR mu -- OLUYOR, bilerek")
# Puanli hicbir haber yoksa bolum bos kalacakti. O durumda bilanco
# kalemi mansete dusuyor: "bugun hicbir gelisme yok" demek, yayimlanan
# bir bilanco analizi varken dogru olmazdi.
_m4 = insa.one_cikan_birlestir([], _b)
esit([x["kurum"] for x in _m4], ["BBBB", "AAAA"],
     "haber yoksa bilanco bolumu dolduruyor")

print("")
print("8. PENCERE SABLONLA AYNI")
# Sablon `one_cikanlar[0]` ve `one_cikanlar[1:7]` basiyor. Pencere
# ayri yazilsa biri degisip oteki unutulurdu.
_sablon = (_KOK / "sablonlar" / "anasayfa.html").read_text(encoding="utf-8")
esit("one_cikanlar[1:7]" in _sablon, True, "sablon 1:7 basiyor")
esit(insa.ONE_CIKAN_PENCERESI, 7, "pencere sabiti sablonla uyusuyor")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
