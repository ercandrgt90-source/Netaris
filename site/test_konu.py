"""KONU HUB'LARI -- yeterli icerik, gercek baglanti, sinirli agirlik.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-16): sitede 15 konu etiketi vardi ve HICBIRININ
sayfasi yoktu. Haber sayfasindaki kirinti yolu konuyu yaziyor ama
hicbir yere baglamiyordu -- okur "Enflasyon" gorup tiklayamiyordu.

COGALTMA DEGIL, once olculdu: `/gundem/` suzgeci TURE gore calisiyor
(makro/haber), konuya gore degil; 15 konunun yalnizca 3'unun
`/varlik/` karsiligi var ve onlar sektor kayitlari.

BU DOSYANIN ASIL ISI IKI SINIRI KORUMAK:

  1. ESIK. Brief'in kendi kurali "bos veya birkac icerikli konu
     sayfasi uretme" diyor. Uc haberlik bir hub, tam da yasaklanan
     ince sayfadir. Esik dusurulurse bu sinama kirmizi yanar.

  2. BAGLANTI. Ilk yazimda yalnizca JSON-LD kirintisini baglamistim
     ve 13 sayfa da HIC ic baglanti almadi -- sema `item`i bir `href`
     degil. Dizine giren ama hicbir yerden baglanmayan sayfa, bu
     oturumda 207 analizde duzeltilen kusurun ta kendisi.

NE SINANIYOR
------------
1. `uygun_konular` esigi uyguluyor ve "Sirket haberleri"ni disliyor.
2. Uretilen her konu sayfasi IC BAGLANTI aliyor.
3. Baglanan her konu adresi GERCEKTEN var (kirik baglanti yok).
4. Gorunur kirinti ile JSON-LD kirintisi AYNI seyi soyluyor.
5. Sayfa agirligi sinirli -- liste kapaginin sebebi bu.
"""

from __future__ import annotations

import collections
import json
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


#: Bir konu sayfasinin en fazla agirligi. Kiyas: `/bilancolar/` 220
#: kartla 426 KB ve mobilde LCP'yi zorluyor. Olculen en agir konu
#: sayfasi 71 KB.
AGIRLIK_SINIRI_KB = 150

print("\nEsik kurali")
_h = ([{"konu": "Enflasyon"}] * 12 + [{"konu": "Turizm"}] * 3
      + [{"konu": "Şirket haberleri"}] * 40 + [{"konu": ""}] * 5)
_u = insa.uygun_konular(_h, esik=10)
esit(_u, {"Enflasyon"}, "yalnizca esigi asan konu sayfa hak ediyor")
esit("Turizm" in insa.uygun_konular(_h, esik=3), True,
     "esik dusunce az icerikli konu da giriyor (esik GERCEKTEN uygulaniyor)")
esit("Şirket haberleri" in insa.uygun_konular(_h, esik=1), False,
     "'Şirket haberleri' konu sayilmiyor -- o bir tur, konu degil")
esit(insa.KONU_ESIGI >= 10, True,
     f"varsayilan esik >= 10 (su an {insa.KONU_ESIGI})")

print("\nUretilen sitede")
if not (_CIKTI / "konu").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_sayfalar = sorted((_CIKTI / "konu").glob("*/index.html"))
esit(len(_sayfalar) >= 5, True, f"konu sayfasi uretilmis ({len(_sayfalar)})")

# IC BAGLANTI. Dizine giren ama hicbir yerden baglanmayan sayfa,
# 207 analizde duzeltilen kusurun ayni.
_gelen: collections.Counter = collections.Counter()
_baglanan: set[str] = set()
for _p in _CIKTI.rglob("index.html"):
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _kendi = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    for _y in set(re.findall(r'href="(/konu/[^"#?]*)"', _g)):
        _baglanan.add(_y)
        if _y != _kendi:
            _gelen[_y] += 1

_var = {"/konu/" + _p.parent.name + "/" for _p in _sayfalar}
_oksuz = sorted(y for y in _var if _gelen[y] == 0)
esit(_oksuz[:5], [], "her konu sayfasi IC BAGLANTI aliyor")

# KONU ALTINDA SAYFA DISI DOSYA DA OLABILIR.
#
# Olculdu (2026-09-24): her konuya kendi RSS beslemesi eklendi
# (`/konu/<konu>/rss.xml`) ve bu iddia KIRMIZI yandi -- cunku varlik
# kontrolu yalnizca `index.html` ariyordu. Baglanti kirik degildi;
# KONTROL eksikti.
#
# Uzantili yol DOSYANIN KENDISINE bakilarak dogrulaniyor. Boylece
# kural zayiflamiyor: olmayan bir besleme adresine baglanmak yine
# kirmizi yanar.
def _hedef_var(yol: str) -> bool:
    ic = yol.lstrip("/")
    if yol.endswith("/"):
        return (_CIKTI / ic / "index.html").exists()
    return (_CIKTI / ic).exists()


_kirik = sorted(y for y in _baglanan if y not in _var and not _hedef_var(y))
esit(_kirik[:5], [], "baglanan her konu adresi GERCEKTEN var")

# Kontrolun kendisi calisiyor mu: olmayan bir adres YAKALANMALI.
esit(_hedef_var("/konu/olmayan-konu/rss.xml"), False,
     "olmayan dosya `var` sayilmiyor (kontrol zayiflamadi)")

print("\nSayfa icerigi")
_agir, _semasiz, _uyusmaz = [], [], []
for _p in _sayfalar:
    _y = "/konu/" + _p.parent.name + "/"
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _kb = len(_g.encode("utf-8")) // 1024
    if _kb > AGIRLIK_SINIRI_KB:
        _agir.append((_y, _kb))
    _bloklar = []
    for _b in re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', _g, re.S):
        try:
            _bloklar.append(json.loads(_b))
        except Exception:
            _semasiz.append(_y)
    _tipler = {x.get("@type") for x in _bloklar if isinstance(x, dict)}
    if "CollectionPage" not in _tipler or "BreadcrumbList" not in _tipler:
        _semasiz.append(_y)

esit(_agir[:3], [], f"hicbir konu sayfasi {AGIRLIK_SINIRI_KB} KB'yi asmiyor")
esit(sorted(set(_semasiz))[:3], [],
     "her konu sayfasinda CollectionPage + BreadcrumbList var")

print("\nGorunur kirinti ile sema AYNI")
# Deponun kendi kurali: "sayfada zaten gorunen kirinti yolu ile
# buradaki veri AYNI olmali". Ilk yazimda yalnizca semayi baglamistim.
_ornek = next(iter((_CIKTI / "haber").rglob("index.html")))
_g = _ornek.read_text(encoding="utf-8", errors="replace")
_gorunur = set(re.findall(r'<a class="konum-simdi" href="(/konu/[^"]+)"', _g))
_semada: set[str] = set()
for _b in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', _g, re.S):
    try:
        _d = json.loads(_b)
    except Exception:
        continue
    if isinstance(_d, dict) and _d.get("@type") == "BreadcrumbList":
        for _o in _d.get("itemListElement", []):
            _it = str(_o.get("item") or "")
            if "/konu/" in _it:
                _semada.add(_it.replace("https://netaris.net", ""))
esit(_gorunur, _semada,
     "haber sayfasinda gorunur konu baglantisi = semadaki konu baglantisi")

print(f"\nTUM TESTLER GECTI ({_gecti})")
