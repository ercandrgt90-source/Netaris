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

#: Esige KALAN PAY bu degerin altina inerse UYARI duyurulur.
#:
#: BU SABIT NEDEN VAR
#: ------------------
#: `DOM_SINIRI` asildiginda sinama kirmizi yanar ve DAGITIM DURUR.
#: Bu uc kez yasandi (2026-09-18, 10-19, 10-26) ve her seferinde
#: kesinti SAATLER surdu -- cunku esigin asildigi, ancak asildiktan
#: SONRA ogrenildi.
#:
#: Oysa asilma hep YAVAS geldi: 2026-10-26 olcumunde sayfa gunde
#: 7,4 analiz x 3-4 oge buyuyordu, yani son 400 oge yaklasik iki
#: HAFTA once gorulebilirdi.
#:
#: Uyari sinamayi DUSURMEZ. Dusurmek dagitimi durdurur ve bu, tam
#: olarak onlenmek istenen sey; uyarinin isi durmadan ONCE haber
#: vermek.
#:
#: 500 NASIL SECILDI: oge basina ~3 dugum ve 7,4 analiz/gun ile
#: 500 oge ~22 GUNLUK haber verme suresi demek. Daha kucuk bir pay
#: (200) bir haftadan az kalirdi; daha buyugu (1.000) saglikli
#: sayfalari da uyari listesine sokar ve uyari gurultuye donusur.
UYARI_PAYI = 500

#: Uyari dosyasi -- is akisi bunu okuyup kayit aciyor.
#: `dusen-sinamalar.txt` ile ayni desen (bkz. `cikti_sinamalari.py`).
UYARI_DOSYASI = "yaklasan-esik.txt"


def uyari_gerek(dom: int, sinir: int = DOM_SINIRI,
                pay: int = UYARI_PAYI) -> bool:
    """Sayfa esigi ASMIYOR ama paya girdi mi?

    SAF: ag yok, dosya yok, sinanabilir. Esigi ASAN sayfa icin
    False doner -- o zaten KIRMIZI yaniyor ve iki kez duyurmak
    alarmi degersizlestirir.
    """
    return sinir - pay <= dom <= sinir


def _uyar(yaklasanlar: list) -> None:
    """Paya giren sayfalari kosu ozetine ve uyari dosyasina yazar.

    CI DISINDA HICBIR SEY YAZMIYOR: yerelde dosya birakmak, bir
    sonraki kosuda bayat bir listeyi duyuruya tasima riski olurdu.
    Ayni gerekce `cikti_sinamalari.py` icinde de yazili.
    """
    import os                                    # noqa: PLC0415

    if not os.environ.get("GITHUB_ACTIONS"):
        return
    satirlar = [f"{_y} {_d} oge (pay {DOM_SINIRI - _d})"
                for _y, _d in yaklasanlar]
    try:
        yol = (pathlib.Path(os.environ.get("RUNNER_TEMP") or ".")
               / UYARI_DOSYASI)
        # BOS DOSYA DA YAZILIYOR: temiz bir kosudan sonra sonraki
        # kosunun bayat listeyi devralmasi, var olmayan bir sayfayi
        # suclamak olurdu.
        yol.write_text(chr(10).join(satirlar), encoding="utf-8")
    except OSError:
        pass
    ozet = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet and satirlar:
        try:
            with open(ozet, "a", encoding="utf-8") as f:
                f.write(chr(10) + "**DOM esigine YAKLASAN sayfalar**"
                        + chr(10) * 2)
                for s in satirlar:
                    f.write(f"- `{s}`" + chr(10))
        except OSError:
            pass


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
_yaklasan = []
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
    elif uyari_gerek(_d):
        _yaklasan.append((_y, _d))

esit(_n > 500, True, f"tarama dolu ({_n} sayfa)")
if _agir:
    print("\n  ESIGI ASANLAR:")
    for _y, _d in sorted(_agir, key=lambda x: -x[1])[:8]:
        print(f"    {_d:6d}  {_y}")
esit(_agir[:5], [],
     f"hicbir sayfa {DOM_SINIRI} DOM ogesini asmiyor "
     f"(en agir: {_en_agir[1]} {_en_agir[0]})")

# ESIGE YAKLASMAK KIRMIZI DEGIL, AMA SESSIZ DE DEGIL.
#
# Bu blok sinamayi DUSURMUYOR. Amaci, esigin asildigi gun degil
# haftalar ONCESINDE haber vermek: uc kesintinin ucu de "asildiktan
# sonra ogrenildi" diye uzadi.
if _yaklasan:
    print(f"\n  UYARI -- esige {UYARI_PAYI} ogeden az pay kaldi:")
    for _y, _d in sorted(_yaklasan, key=lambda x: -x[1]):
        print(f"    {_d:6d}  pay {DOM_SINIRI - _d:5d}  {_y}")
_uyar(_yaklasan)

# UYARI DUZENEGI ATIL OLMAMALI.
#
# Su an hicbir sayfa paya girmiyor olabilir -- bu IYI HABER, ama o
# zaman duzenegin calistigi hic gorulmez ve bozuldugunda da
# gorulmez. Bu yuzden karar fonksiyonu DOGRUDAN sinaniyor: iddia
# icerige degil MEKANIZMAYA bakiyor.
esit(uyari_gerek(DOM_SINIRI - 1), True, "esigin bir altinda uyarir")
esit(uyari_gerek(DOM_SINIRI - UYARI_PAYI), True, "payin tam sinirinda uyarir")
esit(uyari_gerek(DOM_SINIRI - UYARI_PAYI - 1), False,
     "payin disinda uyarmaz")
esit(uyari_gerek(DOM_SINIRI + 1), False,
     "esigi ASAN sayfa icin uyarmaz -- o zaten kirmizi")

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
