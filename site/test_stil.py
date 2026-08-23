"""CSS kisayol tuzagi: tek degerli `margin` HIZAYI BOZAR.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): `stil.css` icinde YEDI kural `margin` kisayolunu
TEK DEGERLE yaziyordu:

    .yazi > header              { margin: 22px}
    .ara-alan                   { margin: 26px}
    .kaynak-etiket              { margin:  2px}
    .foto-atif                  { margin: 18px}
    .panel-satir-kart .panel-eylem { margin: 10px}
    .basmanset-ozet             { margin: 14px}
    .onem-liste li              { margin:  2px}

Tek deger DORT YANA birden uygulanir -- SOL VE SAGA DA. Sayfalarimiz
dikey yigin: bir blogun sol kenari, ustundeki ve altindaki bloklarin
sol kenariyla ayni olmali. Tek degerli margin o hizayi bozuyor.

GORUNEN SONUCLARI
  * `.basmanset-ozet`  ana sayfanin en onemli blogunda ozet, kendi
                       basligindan 14px sagda basliyordu.
  * `.yazi > header`   HER yazi sayfasinda baslik blogu, metinden
                       22px icerideydi.
  * `.foto-atif`       bir ustteki kural `var(--b-2) 0 0` veriyordu,
                       bu satir onu hemen eziyordu; CC BY atfi ait
                       oldugu fotografla hizasizdi.
  * `.hero-dar h1`     sayfanin en buyuk yazisi 10px sagdaydi.
  * `.hero-butonlar`   `margin: 22px` -- ayni sey.

HICBIRI HATA VERMIYORDU. CSS gecerli, sayfa cikiyor, hicbir sey
kirilmiyor. Yalnizca sayfa "biraz dagi̇nik" gorunuyor ve sebebi
bakildiginda goze carpmiyor -- tek bir sayida gizli.

NEDEN SINAMA
------------
Kisayol yazmak kolay ve dogal: "ustune altina bosluk koyayim" diye
dusunulup `margin: 14px` yaziliyor. Yani bu hata BIR KEZ duzeltilse
bile geri gelir. Kural burada duruyor.

ISTISNA
-------
Gercekten dort yandan bosluk isteniyorsa satira `/* dort-yan */`
yazilir; sinama o satiri gecer. Istisna YAZILI olmali -- niyet ile
kaza arasindaki fark, ancak yazilinca gorunur.

`padding` SINANMIYOR
--------------------
Dolgu bir KUTUNUN ICI: dort yandan esit dolgu normaldir ve hizayi
bozmaz, cunku kutunun dis kenari yerinde kalir. Sorun disariya
verilen boslukta.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CSS = _SITE / "statik" / "stil.css"

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


#: `margin:` -- ama `scroll-margin:` ya da `margin-top:` DEGIL.
#: Onundeki harf/tire dislaniyor, ardindan dogrudan iki nokta geliyor.
_MARGIN = re.compile(r"(?<![-A-Za-z])margin\s*:\s*([^;}]+)")

#: Hizayi bozmayan tek degerler.
#: Hizayi bozmayan tek degerler.
#:
#: `auto` BILEREK LISTEDE DEGIL. Esnek kutunun cocugunda `margin: auto`
#: serbest boslugu IKI YANDAN birden yutar:
#:   * satir ebeveynde  -> oge saga DAYANMAZ, kalan boslugun ortasina
#:     oturur ("Haberi oku" bagi kartin ortasinda duruyordu)
#:   * sutun ebeveynde  -> alta iter (genellikle istenen) AMA ayrica
#:     yatayda ortalar (neredeyse hic istenmeyen)
#: Yedi kural bu yuzden yanlis hizalaniyordu. Gercekten iki yanli
#: isteniyorsa `/* dort-yan */` yaziliyor -- ust bar ve altbilgi
#: gezinmesi gibi.
_ZARARSIZ = {"0", "inherit", "initial", "unset", "revert"}


def _tek_degerli(deger: str) -> bool:
    """Tek bir SIFIRDAN FARKLI uzunluk mu?"""
    parca = deger.split()
    if len(parca) != 1:
        return False
    d = parca[0].strip().lower()
    if d in _ZARARSIZ:
        return False
    # `var(--b-4)` de tek deger ve o da dort yana gider.
    return not d.startswith("0")


print("\nTek degerli margin kullanilmiyor")

satirlar = _CSS.read_text(encoding="utf-8").splitlines()
kusurlu = []
for no, satir in enumerate(satirlar, 1):
    if "dort-yan" in satir:          # yazili istisna
        continue
    for m in _MARGIN.finditer(satir):
        if _tek_degerli(m.group(1)):
            kusurlu.append(f"stil.css:{no}  margin: {m.group(1).strip()}")

esit(kusurlu, [], "stil.css icinde tek degerli margin yok")

# --------------------------------------------------------------------
# Desenin KENDISI de sinaniyor.
#
# Yukaridaki tarama sessizce ise yaramaz hale gelebilir: `_MARGIN`
# duzenli ifadesi bozulursa liste bos doner ve sinama "gecti" der.
# Bu depoda tam olarak bu yasandi -- `test_lisans.py` dort listeyi
# tariyordu, "temiz" diyordu ve 573 sayfa ihlalliydi.
#
# Asagisi taramanin HALA GORDUGUNU kanitliyor.
# --------------------------------------------------------------------
print("\nTarama gercekten goruyor (kendi kendini sinar)")

ORNEK = [
    (".a { margin: 14px}", True, "tek deger yakalaniyor"),
    (".a { margin: 14px 0}", False, "iki deger temiz"),
    (".a { margin: 0}", False, "sifir temiz"),
    (".a { margin: 0 auto}", False, "0 auto temiz"),
    (".a { margin: auto}", True,
     "tek auto da yakalaniyor -- esnek kutuda iki yani yutar"),
    (".a { margin: 0 auto}", False, "0 auto temiz -- yatay ortalama"),
    (".a { margin: var(--b-4)}", True, "tek degerli degisken de yakalaniyor"),
    (".a { margin-top: 14px}", False, "margin-top baska ozellik"),
    (".a { scroll-margin: 120px}", False, "scroll-margin baska ozellik"),
    (".a { margin: 14px} /* dort-yan */", None, "yazili istisna gecer"),
]
for kaynak, beklenen, aciklama in ORNEK:
    if beklenen is None:
        esit("dort-yan" in kaynak, True, aciklama)
        continue
    bulundu = any(_tek_degerli(m.group(1)) for m in _MARGIN.finditer(kaynak))
    esit(bulundu, beklenen, aciklama)


# --------------------------------------------------------------------
# IZGARA IZI, IZGARA OLMAYAN OGEYE YAZILMIS OLMASIN.
#
# Olculdu (2026-08-23): uc sinif `grid-template-columns` aliyordu ama
# hicbiri izgara degildi:
#
#     .duyarlilik   bir <table>  (border-collapse)
#     .etki-alan    display: flex
#     .seyir        display: flex
#
# Uculle de bildirim HICBIR SEY YAPMIYORDU. Ucu de "dar ekranda tek
# kolona insin" diye yazilmis bir kuralin icindeydi -- yani amaclanan
# davranis hic gerceklesmemisti.
#
# Kuralin basinda "sinif adiyla degil YAPIYLA" yaziyordu; liste ise
# elle tutulan sinif adlariydi. Niyet dogru, uygulama kaymisti.
#
# Olu bildirim zararsiz gorunur. Zarari, sonraki okuyucunun o ogeleri
# izgara sanmasi ve uzerlerine izgara kurallari yazmasi -- onlar da
# sessizce hicbir sey yapar.
# --------------------------------------------------------------------
print()
print("Izgara izleri yalnizca izgaralara yaziliyor")

_kod = re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"), flags=re.S)


def _anahtar(sec: str) -> str:
    """Secicinin SON sinifi.

    `.haber:not(:has(.haber-gorsel))` ile `.haber` ayni ogedir; sozde
    siniflar ayiklanmazsa ikincisi "izgara degil" sanilirdi.
    """
    sec = re.sub(r"::?[a-z-]+(\([^()]*\))?", "", sec)
    k = re.findall(r"\.([A-Za-z0-9_-]+)", sec)
    return k[-1] if k else ""


_izgara: set = set()
_izli: dict = {}
for _sec, _govde in re.findall(r"([^{}]+)\{([^{}]*)\}", _kod):
    if "@" in _sec:
        continue
    _ig = re.search(r"display\s*:\s*(inline-)?grid", _govde)
    _st = re.search(r"grid-template-(columns|rows|areas)\s*:", _govde)
    for _s in _sec.split(","):
        _a = _anahtar(_s.strip())
        if not _a:
            continue
        if _ig:
            _izgara.add(_a)
        if _st:
            _izli.setdefault(_a, " ".join(_s.split()))

esit(sorted(a for a in _izli if a not in _izgara), [],
     "izgara izi tasiyan her sinif display:grid de tanimliyor")

# Tarama gercekten goruyor mu -- sessizce bos donmesin.
esit(len(_izli) > 20, True,
     f"tarama izgara buluyor ({len(_izli)} sinif)")

# --------------------------------------------------------------------
# KART ZEMINDEN AYIRT EDILEBILMELI.
#
# Olculdu (2026-08-23): ana sayfaya modul kartlari eklendi. Isaretleme
# dogru basildi, CSS dogru yuklendi, canli sayfa dogrulandi -- ve
# kullanici HICBIR DEGISIKLIK GORMEDI.
#
# Sebep renkti: sayfa zemini #fbfcfe, kart #ffffff. Aradaki fark
# 4/3/1 birim ve goz bunu ayirt etmiyor. Kartlar vardi, gorunmuyordu.
#
# Jetonun uzerindeki yorum "panel zeminin uzerinde YUKSELIYOR
# gorunuyor" diyordu. Niyet dogruydu, deger onu karsilamiyordu -- ve
# hicbir sey hata vermedi.
#
# Bir tasarim kararinin gerceklesip gerceklesmedigi niyetten degil
# OLCUDEN anlasilir. Bu sinama olcuyu tutuyor.
#
# ESIK NEDEN 12
# sRGB'de kanal basina 12 birim, acik tonlarda gozle secilebilen en
# kucuk yuzey farkinin civari. Daha dusugu "belki vardir" olur;
# tasarim kararlari "belki" uzerine kurulamaz.
# --------------------------------------------------------------------
print()
print("Kart zemini sayfa zemininden ayirt edilebiliyor")

_kok = re.search(r":root\s*\{(.*?)\}", _CSS.read_text(encoding="utf-8"),
                 re.S)


def _renk(ad: str, govde: str) -> tuple:
    m = re.search(rf"--{ad}:\s*#([0-9a-fA-F]{{6}})", govde)
    if not m:
        return ()
    h = m.group(1)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


_g = _kok.group(1) if _kok else ""
_zemin, _panel = _renk("zemin", _g), _renk("panel", _g)
esit(bool(_zemin and _panel), True, "iki jeton da tanimli")
if _zemin and _panel:
    _fark = max(abs(a - b) for a, b in zip(_zemin, _panel))
    esit(_fark >= 12, True,
         f"zemin ile panel arasinda gorulebilir fark var ({_fark} birim)")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
