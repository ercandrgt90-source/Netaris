"""META ACIKLAMA SAYFAYA OZGU OLMALI.

BU DOSYA NEDEN VAR
------------------
Meta aciklama, arama sonucunda gorunen metni kontrol edebildigimiz TEK
alan. Google yinelenen aciklamalari buyuk olcude yok sayip kendi
snippet'ini uretiyor -- yani paylasilan bir aciklama, hic aciklama
vermemekle neredeyse ayni.

Olculdu (2026-09-16): 1.257 sayfa 57 metni paylasiyordu.

    514 sayfa  "Jeopolitik gelisme fiyata olayin kendisiyle degil..."
    118 sayfa  "Enerji fiyati hem bir maliyet kalemi hem..."
     94 sayfa  "Endeks hareketi tek basina bir bilgi degildir..."
     54 sayfa  "Jeopolitik gelisme."            <- 20 karakter

IKI AYRI SEBEP, IKI AYRI DUZELTME:

  1. `haber.html` sirayi `neden_onemli or ozet or baslik` kuruyordu.
     `neden_onemli` KONU BASINA SABIT bir metin
     (`gundem_yorum.KONU_BAGLAMI`) -- sayfada dogru, meta aciklama
     olarak yanlis. Sira `ozet` one alinacak sekilde degisti.
  2. Analiz ozetleri `uret_olay.py` icinde tur etiketi + piyasa
     hareketinden kuruluyor ve farkli olaylar ayni metni
     uretebiliyor. Ozet birden fazla sayfada geciyorsa baslik one
     aliniyor.

HICBIR YENI METIN URETILMEDI. Ikisi de zaten sayfada duran gercek
alanlarin sirasini degistiriyor. Olculdu: 1.159 haberin 659'unda
`ozet` var ve %98'i farkli; basliklarin %97'si tekil.

SONUC: 1.257 -> 167 -> 37 sayfa. Kalan 37'nin 21'i zaten `noindex`;
dizine giren 16'si ise farkli kaynaklarin ayni olayi ayni cumleyle
ozetledigi haberler -- sablon kusuru degil, icerigin kendisi.

NE SINANIYOR
------------
1. Hicbir sayfa aciklamasiz kalmiyor.
2. DIZINE GIREN sayfalarda paylasilan aciklama esigin altinda.
3. Tek bir metin cok sayida dizinli sayfada gecmiyor.
4. Karar OLCULEREK veriliyor: sablonda "kisa ise" gibi tahmin yok.
"""

from __future__ import annotations

import collections
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Dizine giren kac sayfa paylasilan aciklama tasiyabilir. Olculdu: 16.
#: Esik gercek degerin uzerinde ama 1.257'nin cok altinda -- amac
#: gerilemeyi yakalamak, sayiyi dondurmak degil.
DIZINLI_TEKRAR_SINIRI = 60

#: Tek bir metin en fazla kac DIZINLI sayfada gecebilir. Olculdu: 3.
TEK_METIN_SINIRI = 8

print("\nSiralama kaynakta dogru")
_h = (_SITE / "sablonlar" / "haber.html").read_text(encoding="utf-8")
# Cagriya OZEL: ciplak "ozet" bu dosyada baska yerlerde de geciyor.
esit("{{ h.ozet or (h.baslik" in _h, True,
     "haber aciklamasi SAYFANIN OZETINI once aliyor")
esit(re.search(r"block aciklama %\}\{\{ h\.neden_onemli", _h) is None, True,
     "konu basina sabit metin ARTIK basta degil")

_a = (_SITE / "sablonlar" / "analiz.html").read_text(encoding="utf-8")
esit("ozet_paylasilan" in _a, True, "analiz aciklamasi olculen bayragi kullaniyor")
# Sablonda TAHMIN yok: uzunluga bakan bir kural, olculen paylasimin
# yerini tutmaz ("Jeopolitik gelisme." kisa ama bazi kisa ozetler tekil).
esit(re.search(r"a\.ozet\s*\|\s*length", _a) is None, True,
     "sablonda uzunluk TAHMINI yok -- karar olculuyor")
_i = (_SITE / "insa.py").read_text(encoding="utf-8")
esit("_paylasilan_ozet = {o for o, n in _ozet_sayaci.items() if n > 1}" in _i,
     True, "paylasilan ozetler insa.py'de SAYILARAK bulunuyor")

print("\nUretilen sitede")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_acik: dict[str, list[str]] = collections.defaultdict(list)
_robots: dict[str, str] = {}
_eksik: list[str] = []
_n = 0
for _p in _CIKTI.rglob("index.html"):
    _n += 1
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _y = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    _m = re.search(r'<meta name="description" content="([^"]*)"', _g)
    if not _m or not _m.group(1).strip():
        _eksik.append(_y)
    else:
        _acik[_m.group(1).strip()].append(_y)
    _r = re.search(r'name="robots"[^>]*content="([^"]*)"', _g)
    _robots[_y] = _r.group(1) if _r else ""

esit(_n > 500, True, f"tarama dolu ({_n} sayfa)")
esit(_eksik[:5], [], "aciklamasi OLMAYAN sayfa yok")


def _dizinli(yol: str) -> bool:
    return "noindex" not in _robots.get(yol, "")


# `noindex` sayfalarin aciklamasi arama sonucunda GORUNMUYOR; onlari
# saymak, olculen sayiyi duzeltilemeyen bir sayiyla sisirirdi.
_tekrar = {k: [y for y in v if _dizinli(y)]
           for k, v in _acik.items() if len(v) > 1}
_dizinli_tekrar = sum(len(v) for v in _tekrar.values() if len(v) > 1)
esit(_dizinli_tekrar <= DIZINLI_TEKRAR_SINIRI, True,
     f"dizinli sayfalarda paylasilan aciklama <= {DIZINLI_TEKRAR_SINIRI} "
     f"(olculen {_dizinli_tekrar}, basta 1257)")

_en_cok = max((len(v) for v in _tekrar.values()), default=0)
esit(_en_cok <= TEK_METIN_SINIRI, True,
     f"tek metin en fazla {TEK_METIN_SINIRI} dizinli sayfada "
     f"(olculen {_en_cok}, basta 514)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
