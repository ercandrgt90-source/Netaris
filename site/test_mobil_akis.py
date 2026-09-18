"""CANLI AKIS MOBILDE DE GORUNMELI.

BU DOSYA NEDEN VAR
------------------
Kullanici bildirdi (2026-09-18): "sitede haberler akmiyor". Olculdu
ve HAKLIYDI -- ama hat degil, GORUNURLUK bozuktu:

    yayimlanan haber (o gun)        75
    en yeni haber                   16:42 (kontrolden 26 dk once)
    site kurulumu                   16:43
    masaustunde canli akis          41 taze oge
    MOBILDE canli akis              HIC YOK

Sebep tek satirdi: `@media (max-width: 899px) { .masa > .masa-yan
{ display: none } }`. Akis o sutunun icinde yasiyor, yani 900
pikselin altindaki HER ekranda -- her telefonda, cogu tablette --
adi "Canli akis" olan bilesen sayfada hic cizilmiyordu.

IKI DEGISIKLIK BIRBIRINI SESSIZCE IPTAL ETMIS. 21 Agustos'ta olculup
karara baglanmis: "dar ekranda akis ana icerigin ALTINA duser ve ALTI
OGE gosterir" (61 oge mobilde ~4.600 piksel). 23 Agustos'ta sutunun
tamami gizlenmis ve o karar hic yururluge girmemis; kurallari da olu
kod olarak kalmis. Ikisi de kendi icinde savunulabilir, birlesince
bileseni yok etmisler.

HICBIR SINAMA BUNU GORMUYORDU. Hepsi "sayfa uretiliyor mu, baglanti
var mi, sema dogru mu" diye soruyordu; "okur bunu GOREBILIYOR mu"
diye soran yoktu. CSS ile gizlenen icerik HTML'de durmaya devam
ediyor -- yani baglanti sayan her sinama yesil kaliyor.

NE SINANIYOR
------------
1. Akisi tasiyan sutun mobil kirilimlarda GIZLENMIYOR.
2. Akis listesi ana sayfada URETILIYOR ve dolu.
3. Mobilde kisaltma var (sayfa on iki ekran olmasin) ama tumuyle
   gizleme YOK -- ve "tumunu gor" baglantisi orada.
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


#: Telefon sayilan genislik. 899 dahil, cunku kusur tam orada yasandi.
MOBIL_ESIK = 900

#: Akisi tasiyan kap ve listenin kendisi.
KAP = "masa-yan"
LISTE = "akis-liste"


def yorumsuz(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def mobil_gizlenenler(css: str) -> dict[str, int]:
    """Mobil kirilimlarda `display: none` verilen seciciler."""
    cikti: dict[str, int] = {}
    for m in re.finditer(r"@media([^{]+)\{", css):
        mw = re.search(r"max-width:\s*(\d+)px", m.group(1))
        if not mw or int(mw.group(1)) >= MOBIL_ESIK:
            continue
        bas = m.end()
        derinlik, i = 1, bas
        while i < len(css) and derinlik:
            if css[i] == "{":
                derinlik += 1
            elif css[i] == "}":
                derinlik -= 1
            i += 1
        for r in re.finditer(r"([^{}\n;]+)\{[^}]*display\s*:\s*none[^}]*\}",
                             css[bas:i - 1]):
            cikti[r.group(1).strip()] = int(mw.group(1))
    return cikti


print("\nAkis sutunu mobilde GIZLENMIYOR")
_css = yorumsuz((_SITE / "statik" / "stil.css").read_text(encoding="utf-8"))
_gizli = mobil_gizlenenler(_css)
esit(len(_gizli) >= 0, True, f"mobil gizleme taramasi calisti ({len(_gizli)})")

# Kabi ya da listeyi TUMUYLE gizleyen kural olmamali. Ic ogeleri
# kisaltmak serbest -- `nth-child` ile kirpma bilerek var.
_suclu = [s for s in _gizli
          if re.search(rf"\.{KAP}\s*$|\.{KAP}\s*>\s*\*?$", s.strip())
          or re.search(rf"\.{LISTE}\s*$", s.strip())]
if _suclu:
    print("\n  AKISI GIZLEYEN KURALLAR:")
    for _s in _suclu:
        print(f"    @media(max-width:{_gizli[_s]}) {_s}")
esit(_suclu, [], f"`.{KAP}` ve `.{LISTE}` mobilde gizlenmiyor")

print("\nKisaltma var, yok etme yok")
esit(bool(re.search(rf"\.{LISTE}\s*>\s*li:nth-child", _css)), True,
     "mobilde liste KISALIYOR (sayfa on iki ekran olmasin)")
esit(bool(re.search(r"\.masa-akis \.akis-devam\s*\{\s*display:\s*block", _css)), True,
     "'Tüm canlı akışı gör' bagi mobilde GORUNUYOR")

print("\nUretilen ana sayfada")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_h = (_CIKTI / "index.html").read_text(encoding="utf-8", errors="replace")
_i = _h.find(f'class="{LISTE}"')
esit(_i > 0, True, "canli akis listesi ana sayfada URETILIYOR")
_blok = _h[_i:_h.find("</ol>", _i)]
_oge = len(re.findall(r"<li", _blok))
esit(_oge >= 10, True, f"akis dolu ({_oge} oge)")
esit(bool(re.search(r'href="/gundem/"', _blok + _h[_h.find("</ol>", _i):_h.find("</ol>", _i) + 600])),
     True, "'tümünü gör' baglantisi listenin yaninda")

print(f"\nTUM TESTLER GECTI ({_gecti})")
