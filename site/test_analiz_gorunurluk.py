"""OZGUN BIR ANALIZ HEM BULUNABILIR HEM DIZINE GIREBILIR OLMALI.

BU DOSYA NEDEN VAR
------------------
Tek karar UC isi birden yapiyordu: ana sayfa karisimi, kategori hub'i
ve `noindex`. Ucu ayri sorular ve birlestirilince en pahali cevap
cikiyordu.

Olculdu (2026-09-16):

  * `guncel_olanlar` ayni varligin ayni turdeki analizinden yalnizca
    en gunceli birakiyor; olcut `(kategori, kod)`.
  * `uret_olay.py` her olay analizine SABIT `kod="OLAY"` yaziyor.
  * Sonuc: ('Makro','OLAY') altinda 208 sayfa ve 208 FARKLI baslik --
    %100. Karsilastirma: ('Teknik Gorunum','BTC') 34 sayfa, 18 tekil
    baslik (%53); orada eleme dogru calisiyor.
  * Elenen 380 analizin 380'ine site icinden HIC baglanti yoktu ve
    hepsi `noindex` idi. 207 ozgun analiz dosya olarak vardi, deger
    olarak yoktu.

Ana sayfada eleme DOGRU: kaldirilinca ilk 16 kartin 11 bilancosu 15
makro olaya donuyor ve sitenin ayirt edici icerigi gomuluyor
(olculdu). Yer kisiti orada gercek. Dizine girmede yer kisiti YOK --
ozgun bir sayfayi "listede yer kalmadi" diye dizinden cikarmak,
kazanci olmayan bir kayip.

NE SINANIYOR
------------
1. Yer tutucu kod TASIYAN analiz hicbir zaman gecersiz kilinmaz.
2. Gercek kod TASIYAN analiz, daha yenisi varsa gecersiz kilinir.
3. Ana sayfa elemesi DURUYOR -- karisim bozulmasin.
4. Uretilen sitede: dizine giren her analizin en az bir IC BAGLANTISI
   var. "Dizine ekle ama hicbir yerden baglanma" tutarsizdir.
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

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


class _A:
    """Sinama icin en kucuk analiz taklidi."""

    def __init__(self, slug, kategori, kod):
        self.slug, self.kategori, self.kod = slug, kategori, kod


print("\nGecersiz kilinma KONU iliskisi")
# Yer tutucu: her olay kendi basina icerik. Ayni imzayi tasimalari
# ayni seyi anlattiklari anlamina GELMIYOR.
_g: set = set()
esit(insa.gecersiz_kilindi(_A("a", "Makro", "OLAY"), _g), False,
     "yer tutucu kodlu ilk olay gecersiz DEGIL")
esit(insa.gecersiz_kilindi(_A("b", "Makro", "OLAY"), _g), False,
     "yer tutucu kodlu IKINCI olay da gecersiz DEGIL")
esit(insa.gecersiz_kilindi(_A("c", "Makro", "OLAY"), _g), False,
     "ucuncusu de -- 208 farkli olay ayni imzayi tasiyor")

# Gercek kod: ayni konunun daha yeni olcumu eskisini gecersiz kiliyor.
_g = set()
esit(insa.gecersiz_kilindi(_A("btc-yeni", "Teknik Görünüm", "BTC"), _g), False,
     "en yeni surum gecerli")
esit(insa.gecersiz_kilindi(_A("btc-eski", "Teknik Görünüm", "BTC"), _g), True,
     "eski surum GECERSIZ kilindi")
esit(insa.gecersiz_kilindi(_A("eth", "Teknik Görünüm", "ETH"), _g), False,
     "baska konu etkilenmiyor")

# Kodu OLMAYAN elle yazilmis yazi -- eskiden beri hic elenmiyor.
_g = set()
esit(insa.gecersiz_kilindi(_A("x", "Analist Yorumu", ""), _g), False,
     "kodsuz yazi gecersiz kilinmaz")
esit(insa.gecersiz_kilindi(_A("y", "Analist Yorumu", ""), _g), False,
     "ikincisi de")

esit("OLAY" in insa.YER_TUTUCU_KOD, True,
     "OLAY yer tutucu olarak tanimli")

print("\nIKI KURAL AYRI ISE BAKIYOR")
# `guncel_olanlar` ANA SAYFA icin: orada yer kisitli ve eleme
# OLAYLARI DA kapsiyor -- bilerek. Olculdu: kapsamazsa ilk 16 kartin
# 11 bilancosu 15 makro olaya donuyor ve sitenin ayirt edici icerigi
# gomuluyor.
#
# `gecersiz_kilindi` DIZIN ve HUB icin: orada yer kisiti yok, o yuzden
# yalnizca GERCEKTEN yerini yenisi almis olanlari eliyor.
#
# Ilk yazimda bu sinama ikisinin AYNI davranmasini bekliyordu ve
# kirmizi yandi. Kod dogruydu, iddia yanlisti: ayni ayrimi her yerde
# uygulamak, karisim korumasini da yok ederdi.
_liste = [_A("btc1", "Teknik Görünüm", "BTC"),
          _A("btc2", "Teknik Görünüm", "BTC"),
          _A("olay1", "Makro", "OLAY"),
          _A("olay2", "Makro", "OLAY")]
_kalan = [a.slug for a in insa.guncel_olanlar(_liste)]
esit("btc2" in _kalan, False, "ana sayfa: eski BTC elenmis")
esit("olay2" in _kalan, False,
     "ana sayfa: olaylar da eleniyor -- yer kisiti gercek")

# Ayni girdi, DIZIN kurali: olaylar KORUNUYOR.
_g2: set = set()
_dizin_disi = [a.slug for a in _liste if insa.gecersiz_kilindi(a, _g2)]
esit(_dizin_disi, ["btc2"],
     "dizin: yalnizca yerini yenisi alan eleniyor, olaylar KALIYOR")

print("\nUretilen sitede: dizine giren her analiz BULUNABILIR")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_baglanti: collections.Counter = collections.Counter()
for _p in _CIKTI.rglob("index.html"):
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _kendi = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    for _y in set(re.findall(r'href="(/analiz/[^"#?]*)"', _h)):
        if _y != _kendi:
            _baglanti[_y] += 1

_dizinli, _noindex = [], []
for _p in (_CIKTI / "analiz").rglob("index.html"):
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _y = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    (_noindex if re.search(r'name="robots"[^>]*content="[^"]*noindex', _h, re.I)
     else _dizinli).append(_y)

esit(len(_dizinli) > 300, True, f"tarama dolu ({len(_dizinli)} dizinli analiz)")
_oksuz = sorted(y for y in _dizinli if _baglanti[y] == 0)
esit(_oksuz[:5], [],
     "dizine giren her analizin IC BAGLANTISI var (onceden 380 oksuz)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
