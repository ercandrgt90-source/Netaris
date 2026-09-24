# -*- coding: utf-8 -*-
"""BESLEME SITEYI TEMSIL ETMELI -- TEK BIR TUR ILE DOLMAMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-24): `/rss.xml` 40 oge tasiyordu ve 40'i da HABERDI.
Sitenin 689 analizinden HICBIRI beslemede yoktu.

Sebep durgunluk degildi -- son yedi gunde 72 analiz yayimlanmisti,
yalnizca dun 16 tane. Sebep SIRALAMAYDI: haberin ISO damgasi var
("2026-09-24T06:09"), analizin yalnizca gunu ("2026-09-24"). Ayni
gunde damgali kayit lexikografik olarak BUYUK, yani her haber her
analizi geciyor ve butun slotlari haber dolduruyor.

AYNI KUSUR DAHA ONCE TERS YONDE YASANDI: Agustos'ta besleme yalnizca
ANALIZ tasiyordu, duzeltildi, ve kimse obur tarafi olcmedi. Sarkac
otekine gitti. Bu dosya IKI YONU BIRDEN tutuyor, boylece bir sonraki
duzeltme yine tek tarafa savrulamaz.

NE SINANIYOR
------------
1. Yeterli analiz varsa besleme taban payi kadarini TASIYOR.
2. Haber de eziliyor degil -- iki tur birlikte var.
3. Pay bir TABAN: bir taraf az uretirse bosluk BOS KALMIYOR.
4. Pay bir TAVAN DEGIL ama sira da bozulmuyor -- kronolojik.
5. Konu beslemeleri (analiz yok) etkilenmiyor.
6. Uretilen gercek beslemede de her iki tur var.
"""

from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path[:0] = [str(_SITE)]

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


class _SahteAnaliz:
    """`rss_uret` analizden yalnizca dort alan okuyor."""

    def __init__(self, n: int, gun: str) -> None:
        self.tarih = gun
        self.baslik = f"Analiz {n}"
        self.ozet = f"ozet {n}"
        self.yol = f"/analiz/a{n}/"


def _yollar(x: str) -> list[str]:
    kok = ET.fromstring(x)
    return [(o.find("link").text or "").replace(insa.SITE["adres"], "")
            for o in kok.findall("channel/item")]


def _say(yollar: list[str]) -> tuple[int, int]:
    return (sum(1 for y in yollar if y.startswith("/analiz/")),
            sum(1 for y in yollar if y.startswith("/haber/")))


#: Bu dosyanin bekledigi taban. `insa.RSS_ANALIZ_PAYI` DEGIL.
#:
#: Ilk yazimda esik `insa.RSS_ANALIZ_PAYI` ile kiyaslaniyordu ve
#: mutasyon YESIL kaldi: sabiti sifira cekince beklenti de sifira
#: indi, `0 >= 0` gecti. Hareketli hedefe nisan alan bir kural,
#: kural degildir. Sayi burada, elle yaziyor: kod payi dusururse
#: bu dosya KIRMIZI yanar ve degisiklik bilincli olmak zorunda kalir.
TABAN = 10

# Haber HER ZAMAN daha yeni damga tasiyor: analizi ezen tam bu durum.
_HABERLER = [("2026-09-24", f"Haber {i}", f"ozet {i}", f"/haber/h{i}/",
              f"2026-09-24T{i // 60:02d}:{i % 60:02d}") for i in range(60)]
_ANALIZLER = [_SahteAnaliz(i, "2026-09-23") for i in range(60)]

print("\nPay gercekten uygulaniyor")
_x = insa.rss_uret(_ANALIZLER, _HABERLER)
_y = _yollar(_x)
_a, _h = _say(_y)
esit(len(_y), insa.RSS_OGE_SAYISI, f"besleme dolu ({insa.RSS_OGE_SAYISI} oge)")
esit(_a >= TABAN, True, f"analiz taban payi karsilaniyor ({_a} >= {TABAN})")
esit(insa.RSS_ANALIZ_PAYI >= TABAN, True,
     f"koddaki pay bu dosyanin bekledigi tabandan kucuk degil "
     f"({insa.RSS_ANALIZ_PAYI} >= {TABAN})")
esit(_h > 0, True, f"haber de eziliyor degil ({_h} haber)")
esit(_a + _h, insa.RSS_OGE_SAYISI, "her oge iki turden biri")

print("\nSira KRONOLOJIK kaliyor")
# Pay yalnizca KIMIN girecegini belirliyor, NEREDE duracagini degil.
# Analizi tepeye tasimak gunun haberini beslemenin dibine iterdi --
# 27 Agustos'ta tam bu yasandi.
esit(_y[0].startswith("/haber/"), True,
     "en ustte gunun HABERI var (analiz one alinmadi)")
_damga = [o.find("pubDate").text or ""
          for o in ET.fromstring(_x).findall("channel/item")]
_cev = [insa.datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %z") for d in _damga]
esit(_cev == sorted(_cev, reverse=True), True,
     "ogeler yeniden eskiye siralanmis")

print("\nPay bir TABAN, TAVAN degil")
# Bir taraf az uretirse bosluk BOS KALMAMALI.
_az = insa.rss_uret(_ANALIZLER, _HABERLER[:5])
_ay, _hy = _say(_yollar(_az))
esit(len(_yollar(_az)), insa.RSS_OGE_SAYISI,
     "haber yetmeyince bosluk analizle doluyor")
esit(_ay > TABAN, True, f"analiz payi asabiliyor ({_ay} > {TABAN})")
esit(_hy, 5, "var olan haberlerin hepsi giriyor")

# Ters yon: analiz yoksa besleme yine dolu.
_hic = insa.rss_uret([], _HABERLER)
_ah, _hh = _say(_yollar(_hic))
esit((_ah, _hh), (0, insa.RSS_OGE_SAYISI),
     "analiz yokken besleme tamamen haberle doluyor (konu beslemesi boyle)")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Pay sifirlanirsa bu dosya KIRMIZI yanmali. Mekanizmayi kendi
# sinamadan gecirmemek, bu oturumda dort kez mutasyonu yesil
# birakan kusurdu.
_gercek = insa.RSS_ANALIZ_PAYI
try:
    insa.RSS_ANALIZ_PAYI = 0
    _sifir = insa.rss_uret(_ANALIZLER, _HABERLER)
    _a0, _h0 = _say(_yollar(_sifir))
finally:
    insa.RSS_ANALIZ_PAYI = _gercek
esit((_a0, _h0), (0, insa.RSS_OGE_SAYISI),
     "pay 0 olunca analiz GERCEKTEN dusuyor (kural sahte degil)")

print("\nUretilen gercek beslemede")
if not (_CIKTI / "rss.xml").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_cy = _yollar((_CIKTI / "rss.xml").read_text(encoding="utf-8"))
_ca, _ch = _say(_cy)
print(f"  /rss.xml: {_ca} analiz + {_ch} haber = {len(_cy)} oge")
esit(_ca > 0, True, "canli besleme ANALIZ tasiyor")
esit(_ch > 0, True, "canli besleme HABER tasiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
