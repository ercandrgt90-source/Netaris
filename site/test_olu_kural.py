"""GIZLENMIS BIR KABIN ICINE KURAL YAZILMAZ -- uygulanamaz.

BU DOSYA NEDEN VAR
------------------
`.masa-yan` (canli akis + piyasa kutusunu tasiyan yan sutun) 899
pikselin altinda `display: none`. Buna ragmen dosyada, DAHA DAR
ekranlar icin, o sutunun ICINDEKI ogelere kural yaziliyordu:

    @media (max-width: 699px)  .akis-liste > li:nth-child(n+7)
    @media (max-width: 699px)  .masa-akis, .akis-liste, .kaynak-not
    @media (max-width: 640px)  .akis-liste > li:nth-child(n+9)
    @media (max-width: 640px)  .masa-akis .akis-devam

Hicbiri uygulanmiyordu. Ustelik yanlarinda 20 satirlik bir aciklama
duruyordu: "mobilde akis ALTI OGEYE kisaliyor". O karar 21
Agustos'ta alindi, 23 Agustos'ta akis mobilde tumuyle kaldirildi --
aciklama kaldi, davranis gitti.

ZARARI KODUN KENDISI DEGIL, ANLATTIGI SEY. Dosyanin kendi yorumu
bunu yaziyor: "erisilmeyen kod, sonraki okuyucuyu 'burada bir sey
var' diye yanlis yonlendirir". Ayni dosyada daha once "8 olu kural"
bu gerekceyle temizlenmisti; bu blok o taramadan kacmis.

NE SINANIYOR
------------
Bir sinif, SITEDE yalnizca `display: none` verilmis bir kabin
icinde geciyorsa, o kaba esit ya da daha dar bir medya sorgusunda
ona kural yazilamaz.

Olcum uretilmis HTML'den yapiliyor -- "hangi kabin icinde" sorusunun
cevabi sablonda degil, cikan sayfada.
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


def medya_bloklari(css: str):
    """(esik, blok) -- yalnizca `max-width` sorgulari."""
    for m in re.finditer(r"@media([^{]+)\{", css):
        bas = m.end()
        derinlik, i = 1, bas
        while i < len(css) and derinlik:
            if css[i] == "{":
                derinlik += 1
            elif css[i] == "}":
                derinlik -= 1
            i += 1
        mw = re.search(r"max-width:\s*(\d+)px", m.group(1))
        if mw:
            yield int(mw.group(1)), css[bas:i - 1]


def gizlenen_kaplar(css: str) -> dict[str, int]:
    """`display: none` verilmis sinif -> en GENIS esik."""
    cikti: dict[str, int] = {}
    for esik, blok in medya_bloklari(css):
        for r in re.finditer(r"([^{}\n;]+)\{[^}]*display\s*:\s*none[^}]*\}", blok):
            secici = r.group(1).strip()
            if secici.startswith(("/*", "*")) or "::" in secici:
                continue
            # GIZLENEN, SECICININ SON PARCASI.
            #
            # Ilk yazimda "secicideki son SINIF" aliniyordu ve
            # `.ust-ic > nav { display: none }` kurali `.ust-ic`i
            # gizli kap sandi -- oysa gizlenen `nav`. Sonuc: `.logo`,
            # `.ust-eylem`, `.menu-katman` yanlislikla "olu" diye
            # raporlandi. Yanlis pozitif, kacan kusur kadar zararli.
            #
            # Son parca bir SINIF degilse (oge, oznitelik, sozde
            # sinif) atlaniyor: ata haritasi sinif tabanli ve o
            # secicileri temsil edemiyor. Az kapsamak, yanlis
            # kapsamaktan iyi.
            son_parca = re.split(r"[\s>+~,]+", secici.strip())[-1]
            if not son_parca.startswith("."):
                continue
            ad = son_parca.lstrip(".").split(":")[0].split("[")[0]
            if ad:
                cikti[ad] = max(cikti.get(ad, 0), esik)
    return cikti


def siniflar_ve_atalari(kok: pathlib.Path, en_fazla: int = 60):
    """sinif -> HER GECISI icin ata siniflar kumesi (liste).

    Yigin ile gercek ata zinciri cikariliyor. Yaklasik bir "yakinlik"
    olcusu YETMIYOR: ilk yazimda 3.000 karakterlik geriye bakisla
    olctum ve `ai-akis-liste`yi `akis-liste` sanip yanlis sonuca
    vardim.
    """
    etiket = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>")
    kapanissiz = {"img", "br", "hr", "meta", "link", "input", "source"}
    harita: dict[str, list[set[str]]] = {}
    for n, p in enumerate(kok.rglob("index.html")):
        if n >= en_fazla:
            break
        h = p.read_text(encoding="utf-8", errors="replace")
        yigin: list[set[str]] = []
        for m in etiket.finditer(h):
            ad = m.group(2).lower()
            if ad in ("script", "style"):
                continue
            if m.group(1) == "/":
                if yigin:
                    yigin.pop()
                continue
            if ad in kapanissiz or m.group(3).rstrip().endswith("/"):
                continue
            c = re.search(r'class="([^"]*)"', m.group(3))
            kendi = set(c.group(1).split()) if c else set()
            atalar: set[str] = set()
            for k in yigin:
                atalar |= k
            for s in kendi:
                # HER GECIS AYRI KAYIT. Ilk yazimda butun gecislerin
                # atalarini tek kumede BIRLESTIRIYORDUM ve "yalnizca
                # su kabin icinde" sorusunu soramaz hale geliyordum --
                # mutasyon ikisini de kacirdi. Liste, her gecisin
                # kendi ata kumesini ayri tutuyor.
                harita.setdefault(s, []).append(atalar)
            yigin.append(kendi)
    return harita


def yorumsuz(css: str) -> str:
    """CSS yorumlarini cikarir.

    SART: bu dosyadaki aciklamalar kural ORNEKLERI iceriyor
    (yorum icinde `.masa > .masa-yan { display: none }` gibi) ve
    ciplak ayristirma onlari GERCEK kural saniyordu. Ilk olcumde
    `.ust-ic` "gizli kap" diye raporlandi -- oysa o dize yalnizca bir
    yorumda geciyor. Yanlis pozitif, kacan kusur kadar zararli:
    sinamaya guveni bitirir.
    """
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


print("\nCSS okunuyor")
_css = yorumsuz((_SITE / "statik" / "stil.css").read_text(encoding="utf-8"))
_kaplar = gizlenen_kaplar(_css)
esit(len(_kaplar) > 0, True, f"gizlenen kap bulundu ({len(_kaplar)})")
esit("masa-yan" in _kaplar, True,
     f"`.masa-yan` gizleniyor (esik {_kaplar.get('masa-yan')}px)")

if not _CIKTI.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

print("\nUretilen sayfalardan ata zinciri")
_harita = siniflar_ve_atalari(_CIKTI)
esit(len(_harita) > 100, True, f"sinif haritasi dolu ({len(_harita)})")

# Bir sinif SADECE gizli kabin icinde geciyorsa, o kaba esit ya da
# daha dar sorguda ona kural yazmak olu koddur.
_olu = []
for _esik, _blok in medya_bloklari(_css):
    for _r in re.finditer(r"([^{}\n;]+)\{", _blok):
        _secici = _r.group(1).strip()
        if _secici.startswith(("/*", "*", "@")) or not _secici:
            continue
        for _s in re.findall(r"\.([a-zA-Z0-9_-]+)", _secici):
            if _s in _kaplar:            # kabin kendisi -- kural mesru
                continue
            _gecisler = _harita.get(_s)
            if not _gecisler:
                continue
            # SORU: bu sinifin HER gecisinde, bu esikte zaten gizli
            # olan ortak bir kap var mi? Varsa kural hicbir oge
            # bulamaz.
            _ortak = set.intersection(*_gecisler) if _gecisler else set()
            _gizli_kap = sorted(k for k in _ortak
                                if k in _kaplar and _kaplar[k] >= _esik)
            if _gizli_kap:
                _olu.append((_esik, _secici[:48], _gizli_kap[0]))

if _olu:
    print("\n  OLU KURALLAR:")
    for _e, _s, _k in _olu[:10]:
        print(f"    @media(max-width:{_e}) {_s}  <- `.{_k}` zaten gizli")
esit(_olu[:5], [],
     "gizlenmis kabin icine yazilmis kural YOK")

print(f"\nTUM TESTLER GECTI ({_gecti})")
