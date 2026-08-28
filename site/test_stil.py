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

# --------------------------------------------------------------------
# MEDYA SORGUSUNDAKI KURAL, SONRAKI TEMEL KURAL TARAFINDAN EZILMESIN.
#
# Bu tuzak bu oturumda UC KEZ cikti ve ucunde de "kural yazildi,
# hicbir sey degismedi" sonucunu verdi:
#
#   .ana-akis       bolum araliklari `.masa` tarafindan geri alindi
#   .senaryo-davet  modul dolgusu 5.000 satir sonra geri alindi
#   .masa-yan       `display: none` 1.700 satir sonraki
#                   `display: flex` tarafindan ezildi -- mobilde
#                   piyasa kutusu ve canli akis GORUNMEYE DEVAM ETTI
#
# Sebep hep ayni ve CSS'in tanimli davranisi: medya sorgusu OZGULLUK
# EKLEMEZ. `@media { .a { display: none } }` ile `.a { display: flex }`
# esit ozgulluktedir (0,1,0) ve esitlikte DOSYADAKI SIRA karar verir.
# Sonraki kazanir.
#
# Hicbir arac uyarmiyor: iki kural da gecerli, tarayici sessizce
# birini seciyor.
#
# KURAL
# Bir medya sorgusu icindeki `secici { ozellik }` ciftinden SONRA,
# ayni seciciyi ayni ozellikle ayarlayan bir TEMEL kural gelmemeli.
#
# COZUM YOLU (ikisi de kabul)
#   1. Seciciyi guclendir: `.masa > .masa-yan` (0,2,0)
#   2. Medya blogunu temel kuraldan SONRAYA tasi
# --------------------------------------------------------------------
print()
print("Medya kurallari sonraki temel kurallarca ezilmiyor")

_ham2 = _CSS.read_text(encoding="utf-8")
_kod2 = re.sub(r"/\*.*?\*/", "", _ham2, flags=re.S)


def _ozgulluk(sec: str) -> tuple:
    """(kimlik, sinif, oge) -- kaba ama karsilastirma icin yeterli."""
    s = sec.strip()
    kimlik = len(re.findall(r"#[\w-]+", s))
    sinif = len(re.findall(r"\.[\w-]+", s)) + len(re.findall(r"\[[^\]]+\]", s))
    sinif += len(re.findall(r":(?!:)(?!not\b)[a-z-]+", s))
    oge = len(re.findall(r"(?<![.#\w-])\b[a-z][a-z0-9]*\b(?![\w-]*\()", s))
    return (kimlik, sinif, oge)


def _kurallar(metin: str, kaydir: int = 0):
    """(yer, secici, ozellikler) uretir."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", metin):
        sec = " ".join(m.group(1).split())
        if sec.startswith("@") or not sec:
            continue
        ozs = set(re.findall(r"(?:^|;)\s*([a-z-]+)\s*:", m.group(2)))
        if ozs:
            yield (m.start() + kaydir, sec, ozs)


# Medya bloklarini ve temel kurallari YERLERIYLE topla.
_medya: list = []
_temel: list = []
_i = 0
while True:
    _k = _kod2.find("@media", _i)
    if _k < 0:
        for r in _kurallar(_kod2[_i:], _i):
            _temel.append(r)
        break
    for r in _kurallar(_kod2[_i:_k], _i):
        _temel.append(r)
    _d = 0
    _p = _kod2.find("{", _k)
    _bas = _p
    while _p < len(_kod2):
        if _kod2[_p] == "{":
            _d += 1
        elif _kod2[_p] == "}":
            _d -= 1
            if _d == 0:
                break
        _p += 1
    for r in _kurallar(_kod2[_bas + 1:_p], _bas + 1):
        _medya.append(r)
    _i = _p + 1

_ezilen = []
for _yer, _sec, _ozs in _medya:
    for _sec2 in _sec.split(","):
        _s2 = _sec2.strip()
        for _yer3, _sec3, _ozs3 in _temel:
            if _yer3 <= _yer:
                continue
            for _s3 in (x.strip() for x in _sec3.split(",")):
                if _s3 != _s2:
                    continue
                _ortak = _ozs & _ozs3
                if _ortak and _ozgulluk(_s3) >= _ozgulluk(_s2):
                    _ezilen.append(f"{_s2} -> {sorted(_ortak)}")

esit(sorted(set(_ezilen)), [],
     "medya sorgusundaki kural sonraki temel kuralla ezilmiyor")

# Tarama gercekten calisiyor mu -- sessizce bos donmesin.
esit(len(_medya) > 100, True,
     f"medya kurali bulundu ({len(_medya)})")
esit(len(_temel) > 200, True,
     f"temel kural bulundu ({len(_temel)})")


print()
print("Otomatik tekrarda BELIRSIZ iz yok")

# CSS Izgara sartnamesi: `repeat(auto-fit / auto-fill, ...)` icindeki
# izlerin boyutu BELIRLI olmali. `minmax(84px, auto)` ust siniri
# intrinsic ve bildirim gecersiz sayilabiliyor.
#
# Olculdu (2026-08-24): `.panel-sayim` tam bunu yaziyordu. Bazi
# tarayicilar tolere ediyor, bazilari bildirimi DUSURUYOR -- ve
# dusurdugunde `display: grid` sutunsuz kaliyor, dort sayi alt alta
# diziliyor. Tarayiciya gore degisen bir duzen, kullanicinin
# "mobilde kayma" diye bildirdigi seyin ta kendisi.
#
# Hata SESSIZ: gecersiz bildirim konsola bile dusmuyor, yalnizca
# yok sayiliyor.
_BELIRSIZ = re.compile(
    r"minmax\([^)]*,\s*(?:auto|min-content|max-content|fit-content[^)]*)\s*\)")

_otomatik = []
for _e in re.finditer(r"grid-template-columns\s*:\s*([^;}]+)", _CSS.read_text(encoding="utf-8")):
    _d = _e.group(1)
    if ("auto-fit" in _d or "auto-fill" in _d) and _BELIRSIZ.search(_d):
        _otomatik.append(_d.strip()[:60])

esit(sorted(set(_otomatik)), [],
     "auto-fit/auto-fill icinde intrinsic ust sinir yok")

# Tarama gercekten calisiyor mu -- sessizce bos donmesin.
_ct = _CSS.read_text(encoding="utf-8")
esit(_ct.count("auto-fit") > 5, True,
     f"auto-fit taramasi dolu ({_ct.count('auto-fit')} kullanim)")

# Desen GERCEKTEN yakaliyor mu (kendi kendini sinar).
esit(bool(_BELIRSIZ.search("minmax(84px, auto)")), True,
     "desen 'minmax(84px, auto)' yakaliyor")
esit(bool(_BELIRSIZ.search("minmax(84px, 1fr)")), False,
     "desen 'minmax(84px, 1fr)' yakalamiyor")


print()
print("Dar ekran tek-kolon listesi OLU AD tasimiyor")

# 640px altinda cok kolonlu izgaralari tek kolona indiren kural, ELLE
# TUTULAN bir sinif listesi. Yorumu bunun daha once KAYDIGINI
# soyluyor: uc ad izgara sanilip listeye konmustu, ucu de <table> ya
# da flex'ti ve `grid-template-columns` onlarda HICBIR SEY yapmiyordu.
#
# Olu bildirim zararsiz gorunur; zarari, sonraki okuyucunun o ogeleri
# izgara sanmasi ve gercek sorunu baska yerde aramasi.
_tam = _CSS.read_text(encoding="utf-8")
_blok = re.search(
    r"((?:\s*\.[a-z0-9-]+,\n)+\s*\.[a-z0-9-]+)\s*\{\s*grid-template-columns:\s*1fr;?\s*\}",
    _tam)
esit(_blok is not None, True, "tek-kolon kurali bulundu")

if _blok:
    _adlar = re.findall(r"\.([a-z0-9-]+)", _blok.group(1))
    esit(len(_adlar) >= 4, True, f"listede sinif var ({len(_adlar)})")
    _olu = []
    for _ad in _adlar:
        _kurallar = re.findall(r"\.%s\b[^{}]*\{([^{}]*)\}" % re.escape(_ad), _tam)
        # Kendi kurali disinda `grid-template-columns` tanimlayan
        # baska bir kural var mi
        _izgara = any("grid-template-columns" in _k and _k.strip() != "grid-template-columns: 1fr"
                      for _k in _kurallar)
        if not _izgara:
            _olu.append(_ad)
    esit(sorted(_olu), [], "listedeki her sinif GERCEKTEN izgara")


print()
print("Kirilma noktalari CAKISMIYOR")

# `max-width: 560px` ve `min-width: 560px` IKISI DE tam 560 pikselde
# eslesiyor: o genislikte birbirini ezen iki kural kumesi birden
# uygulaniyor. Okur icin bu, belirli bir genislikte duzenin
# "atlamasi" demek -- ve yalnizca O genislikte olusur, yani gozle
# aramakla bulunmasi cok zor.
#
# Olculdu (2026-08-24): sitede 899/900 ve 699/700 dogru eslenmisti,
# 560/560 eslenmemisti. Dogru kalip `min = max + 1`.
_ct = _CSS.read_text(encoding="utf-8")
_mx = {int(x) for x in re.findall(r"@media[^{]*max-width:\s*(\d+)px", _ct)}
_mn = {int(x) for x in re.findall(r"@media[^{]*min-width:\s*(\d+)px", _ct)}

esit(sorted(_mx & _mn), [], "ayni pikselde hem max hem min esigi yok")

# Tarama gercekten calisiyor mu
esit(len(_mx) >= 4, True, f"max-width esigi bulundu ({len(_mx)})")
esit(len(_mn) >= 3, True, f"min-width esigi bulundu ({len(_mn)})")

# Esik SAYISI da sinirli kalmali: her yeni esik, duzenin bir kez daha
# degistigi bir genislik demek. Yakin iki esik (720 ve 699 gibi) ayni
# dar bantta iki siçrama uretiyor ve bu da "kayma" olarak goruluyor.
_yakin = sorted((a, b) for a in _mx for b in _mx if a < b and b - a <= 20)
esit(_yakin, [], "birbirine 20 pikselden yakin iki max esigi yok")


print()
print("Medya kurali DAHA OZGUL temel kuralca da ezilmiyor")

# Yukaridaki kontrol yalnizca AYNI secici metnini karsilastiriyordu.
# Bosluk buydu: `main.kabuk` ile `.kabuk` FARKLI metinler ama AYNI
# ogeyi hedefliyor ve `main.kabuk` daha ozgul (0,1,1 karsi 0,1,0).
# Ozgulluk medya sorgusunu YENER -- kural nerede yazildigindan
# bagimsiz olarak.
#
# Olculdu (2026-08-24): `main.kabuk { padding: var(--b-7) }` dar ekran
# kuralini (`.kabuk { padding-inline: var(--b-4) }`) hicbir zaman
# devreye sokmuyordu. 360 piksellik telefonda ana icerik 264 piksel
# aliyordu, olmasi gereken 328 -- ve ust/alt seritler 16 piksel
# aldigi icin ana icerik onlardan 32 piksel iceride kaliyordu.
#
# Kontrol BILESIK seciciye bakiyor: `X.foo` bicimindeki bir temel
# kural, medyadaki `.foo` kuralini ayni ozellikte eziyorsa bulgu.

def _bildirilen(govde):
    return {x.split(":", 1)[0].strip().lower()
            for x in govde.split(";") if ":" in x}

def _kisa_ad(sec):
    """Tek sinifli secici ise sinif adi, degilse bos."""
    s = sec.strip()
    return s[1:] if re.fullmatch(r"\.[a-z0-9-]+", s) else ""

_ezen = []
for _yer, _sec, _ozs in _medya:
    for _parca in _sec.split(","):
        _ad = _kisa_ad(_parca)
        if not _ad:
            continue
        # Temel kurallarda `tag.ad` ya da `.baska.ad` bicimi
        for _yer3, _sec3, _ozs3 in _temel:
            for _p3 in (x.strip() for x in _sec3.split(",")):
                if _p3 == "." + _ad:
                    continue           # ayni secici -- ustteki kontrol bakiyor
                if not re.fullmatch(r"[a-z]*\.[a-z0-9-]+\." + re.escape(_ad)
                                    + r"|[a-z]+\." + re.escape(_ad), _p3):
                    continue
                _ortak = _ozs & _ozs3
                # Kisa yazim uzun yazimi da eziyor: `padding` ->
                # `padding-inline`. Ayni kok yeterli.
                _kok = {y.split("-")[0] for y in _ozs} & {y.split("-")[0] for y in _ozs3}
                if not ((_ortak or _kok) and _ozgulluk(_p3) > _ozgulluk(_parca)):
                    continue
                # DUZELTILMIS MI: medya blogunda ayni ozgullukte bir
                # kural varsa (ornegin `main.kabuk` da medya icinde
                # yeniden yaziliyorsa) ezme YOK. Bunu gormeyen bir
                # kontrol, dogru cozumu de hata sayar ve sonunda
                # kapatilir.
                _kapali = any(
                    _p3 in [x.strip() for x in _s4.split(",")]
                    and ((_ozs4 & (_ortak or _kok))
                         or {y.split("-")[0] for y in _ozs4} & _kok)
                    for _yer4, _s4, _ozs4 in _medya)
                if _kapali:
                    continue
                _ezen.append(f"{_p3} -> .{_ad} ({sorted(_ortak or _kok)})")

esit(sorted(set(_ezen)), [],
     "daha ozgul temel kural medya kuralini ezmiyor")

# Kendi kendini sinar: desen GERCEKTEN yakaliyor mu?
esit(_ozgulluk("main.kabuk") > _ozgulluk(".kabuk"), True,
     "ozgulluk hesabi main.kabuk > .kabuk diyor")
esit(bool(re.fullmatch(r"[a-z]+" + re.escape(".kabuk"), "main.kabuk")), True,
     "bilesik secici deseni main.kabuk yakaliyor")


print()
print("Dokunulan denetimler mobilde 44 pikselden kucuk degil")

# Esik dosyada ZATEN kural: "Apple ve Google'in erisilebilirlik
# kilavuzlari bu esikte birlesiyor; daha kucuk hedefte parmak isabet
# orani belirgin dusuyor." Ama uzun sure YALNIZCA form alanlarina
# uygulanmisti.
#
# Olculdu (2026-08-24): paylasim dugmesi ~33px, "Beğeniyi kaldır"
# ~26px, panel sekmesi ~34px. Paylasim dugmesi ozellikle onemli --
# artik her haber ve her bilanco sayfasinin basinda duruyor.
#
# Liste ELLE tutuluyor; o yuzden asagida ayrica her adin CSS'te
# gercekten var oldugu da sinaniyor. Bu depoda elle tutulan bir
# secici listesi bir kez kaydi ve olu adlar tasidi.
_DOKUNULAN = [
    ".sp-dugme", ".suzgec-dugme", ".panel-sekme button",
    ".menu-katman a", ".izleme li a", ".panel-paylas-baglanti",
    ".begeni-kaldir",
]

_ct = re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"),
             flags=re.S)

# 1. Her ad CSS'te var mi -- liste kaymasin.
_yok = [s for s in _DOKUNULAN
        if not re.search(re.escape(s) + r"[^{},]*[,{]", _ct)]
esit(sorted(_yok), [], "listedeki her secici CSS'te tanimli")

# 2. Her biri bir `min-height: 44px` kuralinda geciyor mu.
_kirkdort = []
for _e in re.finditer(r"([^{}]+)\{([^{}]*min-height:\s*44px[^{}]*)\}", _ct):
    _kirkdort += [x.strip() for x in _e.group(1).split(",")]

_eksik = [s for s in _DOKUNULAN if s not in _kirkdort]
esit(sorted(_eksik), [], "dokunulan her denetim 44px kuralinda")

# 3. `min-height` SATIR ICI ogede calismaz: her birinin bir yerde
#    blok ya da esnek kutu olmasi gerekiyor.
_blok = []
for _e in re.finditer(r"([^{}]+)\{([^{}]*display:\s*(?:block|flex|inline-flex|grid)[^{}]*)\}", _ct):
    _blok += [x.strip() for x in _e.group(1).split(",")]
_satirici = [s for s in _DOKUNULAN if s not in _blok]
esit(sorted(_satirici), [], "dokunulan her denetim blok/esnek kutu")


print()
print("Ayni ogedeki iki sinif AYNI ozelligi sessizce ezmiyor")

# Bir oge iki sinif tasidiginda (`class="a b"`) ve ikisi de tek
# sinifli seciciyle ayni ozelligi yaziyorsa, ozgullukler ESIT olur ve
# karari KAYNAK SIRASI verir. Yazan kisi bunu genellikle bilmiyor:
# sinifi ekliyor, "calismadi" diyor ve sebebini goremiyor.
#
# Olculdu (2026-08-24): `<ul class="ai-akis-liste serit-yatay">`.
# `.ai-akis-liste` dosyada 1800 satir SONRA geldigi icin rafin
# `overflow-x: auto` kuralini `overflow: hidden` ile eziyordu.
# Sonuc: bolumdeki SEKIZ karttan yedisi kirpiliyor ve okura
# ULASILAMIYORDU -- kaydirma da olmadigi icin baska yolu yoktu.
#
# Kontrol "hangisi dogru" demiyor; yalnizca CAKISMA VAR diyor.
# Cozum, birinin digerini sessizce ezmesi degil, bilesik bir kuralla
# (`.a.b`) hangisinin nerede gecerli oldugunun yazilmasi.

_ham3 = _CSS.read_text(encoding="utf-8")
_kod3 = re.sub(r"/\*.*?\*/", "", _ham3, flags=re.S)

# Temel (medya disi) tek sinifli kurallar: sinif -> {ozellik: sira}
_tekil = {}
_derinlik = 0
for _sat in _kod3.split("\n"):
    _medyada = _derinlik > 0
    _e = re.match(r"\s*(\.[a-z0-9-]+)\s*\{(.*)\}\s*$", _sat)
    if _e and not _medyada:
        _ad = _e.group(1)
        _ozs = {x.split(":")[0].strip() for x in _e.group(2).split(";") if ":" in x}
        _tekil.setdefault(_ad, set()).update(_ozs)
    _derinlik += _sat.count("{") - _sat.count("}")

# Cok satirli kurallari da al
for _e in re.finditer(r"(?m)^(\.[a-z0-9-]+)\s*\{([^{}]*)\}", _kod3):
    _ozs = {x.split(":")[0].strip() for x in _e.group(2).split(";") if ":" in x}
    _tekil.setdefault(_e.group(1), set()).update(_ozs)

# Sablonlardaki cok sinifli ogeler
_sablon = ""
for _p in sorted(pathlib.Path(_SITE / "sablonlar").glob("*.html")):
    _sablon += _p.read_text(encoding="utf-8", errors="replace")

_cakisan = []
for _e in re.finditer(r'class="([a-z0-9 -]+)"', _sablon):
    _adlar = ["." + x for x in _e.group(1).split() if x]
    if len(_adlar) < 2:
        continue
    for _i in range(len(_adlar)):
        for _j in range(_i + 1, len(_adlar)):
            _a, _b = _adlar[_i], _adlar[_j]
            if _a not in _tekil or _b not in _tekil:
                continue
            # YALNIZCA `overflow` CAKISMASI ISARETLENIYOR.
            #
            # Ilk yazim her ortak ozelligi bildirdi ve yirmi uc bulgu
            # uretti; yirmisi BILINCLI degistirici kalibiydi
            # (`.dugme.dugme-birincil`, `.rozet.rozet-vurgu`) -- yani
            # dogru CSS. Gurultulu bir kontrol sonunda kapatilir ve o
            # zaman gercek hatayi da tutmaz.
            #
            # `overflow` ozel: sessizce KIRPIYOR. Yanlis kazanan bir
            # `overflow: hidden` icerigi ekrandan siliyor ve okurun
            # ona ulasmasinin baska yolu kalmiyor -- 2026-08-24'te
            # "Netaris ne diyor" bolumundeki sekiz karttan yedisi tam
            # boyle kayboldu. Renk ya da dolgu cakismasi GORUNUR bir
            # kusur; `overflow` cakismasi GORUNMEZ bir kayip.
            _ov_a = {y for y in _tekil[_a] if y.startswith("overflow")}
            _ov_b = {y for y in _tekil[_b] if y.startswith("overflow")}
            if not (_ov_a and _ov_b):
                continue
            # Ayni ailedeki degistirici (`.x` ve `.x-y`) haric: orada
            # ezme zaten amaclanan sey.
            if _b.startswith(_a + "-") or _a.startswith(_b + "-"):
                continue
            _cozulmus = (_a + _b in _kod3.replace(" ", "")
                         or _b + _a in _kod3.replace(" ", ""))
            if not _cozulmus:
                _cakisan.append(f"{_a}{_b} ({sorted(_ov_a | _ov_b)})")

esit(sorted(set(_cakisan)), [],
     "cok sinifli ogelerde cozulmemis ozellik cakismasi yok")

# Tarama gercekten calisiyor mu
esit(len(_tekil) > 100, True, f"tek sinifli kural bulundu ({len(_tekil)})")
esit(".serit-yatay" in _tekil and ".ai-akis-liste" in _tekil, True,
     "bilinen iki sinif taramada gorunuyor")

# ------------------------------------------------------------------
# AYNI SECICI + AYNI OZELLIK IKI KEZ TANIMLANMAZ.
#
# Olculdu (2026-08-27): `@media (max-width: 640px)` kosulu dosyada 33
# AYRI blokta geciyordu ve 12 bildirim OLUYDU -- yazili ama hicbir
# zaman uygulanmayan. Ornekler:
#
#     h1  font-size   clamp(1.45rem,6.5vw,2.1rem) -> clamp(1.25rem,...)
#     h2  font-size   var(--p-xl)   -> 1.25rem
#     .kart padding   var(--b-4)    -> var(--b-3)
#
# Dikkat cekici olan sey: OLENLER TASARIM BELIRTECI kullaniyordu,
# kazananlar sabit deger. Yani mobilde belirtec sistemi devre disiydi
# -- `--p-xl` degistirmek hicbir sey degistirmiyordu ve bunu degistiren
# kisi sebebini bulamazdi.
#
# Temizlik GORUNUMU DEGISTIRMEDI: yalnizca zaten uygulanmayan satirlar
# silindi ve hesaplanan degerler once/sonra birebir karsilastirildi.
#
# `@keyframes` DISARIDA: oradaki `70%`, `100%` ayri animasyon
# adimlaridir, ayni secicinin tekrari degil.
# ------------------------------------------------------------------
import re as _re


def _olu_bildirimler(metin):
    """(kosul, secici, ozellik, olen, kazanan) listesi."""
    kod = _re.sub(r"/\*.*?\*/", " ", metin, flags=_re.S)
    # Animasyon adimlari ayri semantik -- disarida.
    kod = _re.sub(r"@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}",
                  " ", kod, flags=_re.S)

    def govde(kaynak, bas):
        j = kaynak.index("{", bas)
        d = 0
        for k in range(j, len(kaynak)):
            if kaynak[k] == "{":
                d += 1
            elif kaynak[k] == "}":
                d -= 1
                if d == 0:
                    return kaynak[j + 1:k]
        return ""

    gruplar = {}
    for mm in _re.finditer(r"@media ([^{]+)\{", kod):
        kosul = " ".join(mm.group(1).split())
        gruplar.setdefault(kosul, []).extend(
            _re.findall(r"([^{}]+)\{([^{}]*)\}", govde(kod, mm.start())))
    disi = _re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}",
                   " ", kod, flags=_re.S)
    gruplar["(medya disi)"] = _re.findall(r"([^{}]+)\{([^{}]*)\}", disi)

    bulgu = []
    for kosul, kurallar in gruplar.items():
        gorulen = {}
        for sec, gov in kurallar:
            s = " ".join(sec.split())
            if not s or s.startswith("@") or s.endswith("%"):
                continue
            for x in gov.split(";"):
                if ":" not in x:
                    continue
                oz, dg = x.split(":", 1)
                a = (s, oz.strip())
                if a in gorulen and gorulen[a] != dg.strip():
                    bulgu.append((kosul, s, oz.strip(), gorulen[a], dg.strip()))
                gorulen[a] = dg.strip()
    return bulgu


#: Istisna kalmadi. `.onem-kart` bir donem hem `display: grid` hem
#: `display: flex` tanimliyordu ve izgara duzeninin tamami oluydu;
#: 2026-08-27'de IZGARA secildi ve olen flex satirlari kaldirildi.
#: Kume bilerek bos: yeni bir olu bildirim buraya EKLENMEZ,
#: duzeltilir. Istisna listesi tutmak, kurali yavasca bosaltmanin
#: yoludur.
BEKLENEN_ISTISNA = set()

_olu = _olu_bildirimler(_CSS.read_text(encoding="utf-8"))
_yeni = {(k, s, o) for k, s, o, _a, _b in _olu} - BEKLENEN_ISTISNA
esit(sorted(_yeni), [], "olu CSS bildirimi yok")

print()
print("Her varlik turunun etiket rengi var")
# --------------------------------------------------------------------
# `varlik.html` etiketi `class="etiket etiket-{{ v.tur }}"` diye
# yaziyor -- yani sinif adi VERIDEN geliyor. CSS'te karsiligi olmayan
# bir tur, digerlerinden gorunur bicimde farkli ciziliyordu.
#
# Olculdu (2026-08-28): veritabaninda 11 tur var, CSS 7'sini
# boyuyordu. `oran`, `endeks`, `kur` ve `politika` cizgisiz kaliyordu
# -- 79 varligin 12'si.
#
# Kural CSS'te ZATEN YAZILIYDI: "butun turler icin etiket rengi
# olmali". Ama tur kurallari IKI AYRI BLOGA bolunmustu ve yeni turler
# eklendiginde ikisi de guncellenmedi. Yazili bir kural, kendisini
# uygulayan bir sinama olmadan eskiyor.
#
# `.etiket` artik notr bir sol cizgi veriyor, yani eksik tur KIRIK
# gorunmuyor -- ama yine de FARK EDILMELI; bu sinama onu yapiyor.
# --------------------------------------------------------------------
import sqlite3  # noqa: E402

_VT = _SITE.parent / "haber_botu" / "netaris.db"
if not _VT.is_file():
    print("  veritabani yok -- tur sinamasi ATLANDI")
else:
    with sqlite3.connect(f"file:{_VT.as_posix()}?mode=ro", uri=True) as _b:
        _turler = {t for (t,) in _b.execute(
            "select distinct tur from varlik where tur is not null")}
    _govde = re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"),
                    flags=re.S)
    # ACIKLAMALAR ATILIYOR: yukaridaki not eksik turlerin adlarini
    # SAYIYOR. Aciklamayi tarayan bir sinama, kural kaldirildiginda
    # bile yesil kalirdi -- bu oturumda tam bu tuzaga dort kez
    # dusuldu.
    _boyali = set(re.findall(r"\.etiket-([a-z]+)\s*\{", _govde))
    esit(sorted(_turler - _boyali), [],
         f"CSS karsiligi olmayan varlik turu ({len(_turler)} tur)")
    # Ters yon UYARI degil bilgi: veride su an bulunmayan bir tur icin
    # renk tanimli olmasi zararsiz, veri her kosuda degisiyor.
    esit(bool(_turler), True, "veritabaninda varlik turu bulundu")

# --------------------------------------------------------------------
# GUVENLI VARSAYILAN: `.etiket` kendi sol cizgisini vermeli.
#
# Yukaridaki sinama "her turun rengi var mi" diye soruyor. Ama veri
# CI'da her kosuda degisiyor ve yeni bir tur, o turun CSS satiri
# yazilmadan once yayina cikabiliyor. `.etiket`in kendi sol cizgisi
# o araligi kapatiyor: renk notr kalir, BICIM dogru kalir.
#
# Bu satir olmadan yukaridaki sinama hala yesil donuyor -- mutasyonla
# dogrulandi (2026-08-28). Yani varsayilan ayrica sinanmali, yoksa
# sessizce kaldirilabilir.
# --------------------------------------------------------------------
_govde_tam = re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"),
                    flags=re.S)
_m = re.search(r"\.etiket\s*\{(.*?)\}", _govde_tam, flags=re.S)
esit(bool(_m and "border-left" in _m.group(1)), True,
     ".etiket kendi sol cizgisini veriyor (turu olmayan etiket kirilmaz)")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
