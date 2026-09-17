"""SAYFA DOM'U MOBILDE TASINABILIR OLMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-18): uc hub sayfasi asiri DOM tasiyordu.

    /makro/          6.904 oge
    /bilancolar/     6.669
    /arastirmalar/   5.753

Lighthouse'un esikleri ~1.400 (uyari) ve ~3.000 (hata). Bedeli dusuk
donanimli telefonda cizim suresi ve INP.

AKTARIM SORUN DEGILDI -- ayri olculdu ve onemli: sayfa tel uzerinde
36 KB gidiyor (Cloudflare sikistiriyor). Kendi denetim karnemde "426
KB, mobilde LCP riski" yazmistim; o HAM boyuttu ve YANLIS ALARMDI.
Gercek maliyet baytta degil, dugum sayisinda.

`/makro/` 6.904'e bu oturumda CIKTI: hub sayfalari tam arsivi
gostersin diye degistirilmisti (207 ozgun analiz hicbir yerden
baglanti almiyordu). Duzeltmenin bedeli olcuye vurunca gorundu.

COZUM BAGLANTI KESMIYOR: ilk 60 analiz tam kart, kalani ayni sayfada
derli toplu bir liste. Her analiz hala GERCEK baglantiyla duruyor --
kart kirpip baglantiyi da kesmek, 207 analizde duzeltilen kusuru geri
getirirdi. Kullanilan bilesen `olay-cizelge`, sitede zaten var (yeni
kart turu uretilmedi).

NE SINANIYOR
------------
1. Hicbir sayfa DOM esigini asmiyor.
2. Hub sayfalari analiz baglantilarini KAYBETMEDI.
"""

from __future__ import annotations

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


#: DOM ust siniri. Lighthouse "hata" esigi ~3.000; olculen en agir
#: sayfa 2.927. Sinir 3.400: gerilemeyi yakalar, normal buyumeyi
#: bogmaz.
DOM_SINIRI = 3400

#: Hub sayfasi basina en az kac analiz baglantisi kalmali. Olculen:
#: bilancolar 220, arastirmalar 226, makro 231. Kart siniri
#: baglantiyi KESMEMELI.
HUB_EN_AZ_BAGLANTI = {"bilancolar": 200, "arastirmalar": 200, "makro": 200}


def dom_sayisi(html: str) -> int:
    """Kaba DOM oge sayisi -- betik ve stil disarida."""
    g = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    return len(re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)\b", g))


print("\nDOM agirligi")
if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_agir = []
_n = 0
_en_agir = (0, "")
for _p in _CIKTI.rglob("index.html"):
    _n += 1
    _d = dom_sayisi(_p.read_text(encoding="utf-8", errors="replace"))
    _y = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    if _d > _en_agir[0]:
        _en_agir = (_d, _y)
    if _d > DOM_SINIRI:
        _agir.append((_y, _d))

esit(_n > 500, True, f"tarama dolu ({_n} sayfa)")
if _agir:
    print("\n  ESIGI ASANLAR:")
    for _y, _d in sorted(_agir, key=lambda x: -x[1])[:8]:
        print(f"    {_d:6d}  {_y}")
esit(_agir[:5], [],
     f"hicbir sayfa {DOM_SINIRI} DOM ogesini asmiyor "
     f"(en agir: {_en_agir[1]} {_en_agir[0]})")

print("\nHub baglantilari KORUNDU")
for _ad, _en_az in HUB_EN_AZ_BAGLANTI.items():
    _p = _CIKTI / _ad / "index.html"
    if not _p.exists():
        continue
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _bag = len(set(re.findall(r'href="(/analiz/[^"#?]*)"', _h)))
    esit(_bag >= _en_az, True,
         f"/{_ad}/ {_bag} analiz baglantisi tasiyor (>= {_en_az})")

print(f"\nTUM TESTLER GECTI ({_gecti})")
