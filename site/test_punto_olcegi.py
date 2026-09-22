# -*- coding: utf-8 -*-
"""PUNTO OLCEGI VAR OLMAK YETMEZ, UYGULANMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-22): `stil.css`te belgelenmis yedi adimli bir punto
olcegi vardi ama 388 punto bildiriminin 101'i (%26) olcegin DISINDAYDI.
Sonuc, ayni ogenin baglamdan bagimsiz on farkli boyutta gorunmesiydi:

    h1 -> 23,2 / 24 / 27,2 / 28 px
    h2 -> 12 / 13 / 14 / 15,2 / 16 / 17 / 19 / 20,8 / 22 / 25,6 px

Ve bir TABAN sorunu: 27 bildirim 12 pikselin ALTINDAYDI, en kucugu
9,9px. Rozetler, fotograf kunyeleri, takvim etiketleri -- ve mobil
alt menunun sekme yazilari (11px), yani insanlarin PARMAKLA dokundugu
yer.

Dosyanin kendi yorumu su ilkeyi yaziyordu: "iki punto arasindaki fark
okurun ayirt edebilecegi kadar buyuk olmali, yoksa hiyerarsi degil
gurultu uretir." Ilke yaziliydi; UYGULANDIGINI kontrol eden yoktu.

SATIR YUKSEKLIGINDE AYNI HIKAYE
-------------------------------
112 bildirimin 89'u elle yazilmisti ve icinde SAHTE AYRIMLAR vardi:
1.5 ile 1.55 (onar kullanim) ayni isi yapiyordu, 1.35 ile 1.4 ayni
isi. Gozle gorulur fark yok ama sistem "burada bir karar var" diye
okunuyordu. Katmanlar adlandirildi (1.3 / 1.4 / 1.5 / 1.6 / 1.7) ve
her esleme en fazla 0,05em oynatti.

NE SINANIYOR
------------
1. Tarama gercekten calisiyor (kendi kendini sinar).
2. Hicbir metin 12 pikselin altinda degil.
3. Olcek adimlari birbirinden AYIRT EDILEBILIR -- hem puntoda hem
   satir yuksekliginde.
4. Olcek disi her bildirimin yazili gerekcesi var.
5. Her ISTISNANIN SINIRI da sinaniyor: defter genisletilirse ya da
   bir esik gevsetilirse kural KIRMIZI yanar. Bu, yazarken degil
   MUTASYONLA bulundu -- dort esigin dordu de once korumasizdi.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent

#: Hicbir metin bunun altinda olmamali.
#:
#: WCAG mutlak bir alt punto sinirI koymuyor ama 12px yaygin kabul
#: goren taban. Bunun altinda etiketler -- ozellikle telefonda,
#: hareket halinde, gunes altinda -- okunmuyor.
TABAN_PX = 12.0

#: Ayirt edilebilir adim: iki komsu basamak arasinda en az bu oran.
#:
#: Alt basamaklar (12/13/14) bilerek sik: onlar surekli OKUNAN metin
#: degil, yogun arayuz etiketi ve aralarindaki fark bir hiyerarsi
#: vaadi tasimiyor. Ust basamaklar editoryal hiyerarsiyi tasiyor ve
#: orada fark gorunur olmali.
EN_KUCUK_ORAN = 1.06

#: GEREKCE DEFTERI -- olcek disi kalabilecek seciciler.
#:
#: Buraya bir satir eklemeden once sorulacak soru: "bu deger olcege
#: NEDEN girmiyor?" Cevap "girmeli ama ugrasmadim" ise, defter degil
#: jeton gerekiyor.
GEREKCE = {
    "clamp":
        "akiskan baslik: `clamp(min, vw, max)` viewport'la surekli "
        "olcekleniyor. Sabit bir jeton bunu YAPAMAZ -- olcek disi "
        "olmasi kusur degil, tasarimin kendisi",
    "em":
        "EBEVEYNE GORE olcekleniyor (`.menu-ok`, `.dis-ok`, "
        "`.takvim-tarih`): simge ya da ek, yanindaki metinle birlikte "
        "buyuyup kuculmeli. Sabit jeton bu bagi koparirdi",
    "sayi-gosterimi":
        "buyuk sayi gosterimleri (`.skor-deger`, `.rakam b`, "
        "`.vd-sayi`, `.panel-sayim dd`, `.nabiz-oge dd`): bunlar metin "
        "degil GORSEL; boyutlari cevreleyen kutuya gore ayarlaniyor",
    "marka":
        "`.logo` ve `.ag-simge`: marka isareti, metin olcegine degil "
        "kendi orantisina bagli",
    "avatar":
        "`.panel-avatar`, `.avatar-onizleme`: dairenin icindeki tek "
        "harf; boyut daireye gore, `aria-hidden` ve dekoratif",
}

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def yorumsuz(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def jetonlar(css: str) -> dict[str, float]:
    """`:root` icindeki `--p-*` jetonlari -> piksel karsiliklari."""
    kok = re.search(r":root\s*\{([^}]*)\}", css, re.S)
    if not kok:
        return {}
    return {ad: float(deger) * (16 if birim == "rem" else 1)
            for ad, deger, birim in re.findall(
                r"(--p-[\w-]+)\s*:\s*([\d.]+)(rem|px)", kok.group(1))}


def bildirimler(css: str) -> list[tuple[str, str]]:
    """(secici, punto degeri) ciftleri."""
    cikti = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sec = " ".join(m.group(1).split())
        for f in re.finditer(r"font-size\s*:\s*([^;}]+)", m.group(2)):
            cikti.append((sec, f.group(1).strip()))
    return cikti


def mutlak_px(deger: str) -> float | None:
    """Sabit piksel karsiligi; goreli/akiskan degerlerde None."""
    m = re.fullmatch(r"([\d.]+)(rem|px)", deger.strip())
    return float(m.group(1)) * (16 if m.group(2) == "rem" else 1) if m else None


print("\nTarama gercekten calisiyor mu")
_D = (":root { --p-xs: 0.75rem; --p-l: 1.125rem; }"
      ".a { font-size: 0.5rem; } .b { font-size: var(--p-l); }"
      ".c { font-size: clamp(1rem, 2vw, 2rem); } .d { font-size: 0.8em; }")
_j = jetonlar(_D)
esit(_j.get("--p-xs"), 12.0, "jeton degeri cozuluyor (rem -> px)")
esit(mutlak_px("0.5rem"), 8.0, "rem -> px")
esit(mutlak_px("12px"), 12.0, "px -> px")
esit(mutlak_px("0.8em"), None, "`em` mutlak degil (goreli)")
esit(mutlak_px("clamp(1rem, 2vw, 2rem)"), None, "`clamp` mutlak degil")
_b = bildirimler(_D)
esit(len([1 for s, d in _b if mutlak_px(d) is not None]), 1,
     "yalnizca SABIT bildirimler mutlak sayiliyor")


def taban_alti(css: str) -> list[tuple[float, str, str]]:
    """TABAN_PX'in altinda kalan sabit punto bildirimleri."""
    cikti = []
    for sec, deger in bildirimler(css):
        p = mutlak_px(deger)
        if p is not None and p < TABAN_PX:
            cikti.append((p, deger, sec[:54]))
    return cikti


# TABAN ESIGI GERCEKTEN CALISIYOR MU.
#
# Olculdu (mutasyon D): `TABAN_PX`i 0'a cekmek sinamayi KIRMIZI
# yapmiyordu -- cunku CSS'te artik taban alti metin yok, yani esik ne
# olursa olsun bulgu cikmiyor. Esik sessizce etkisizlestirilebilirdi
# ve kimse gormezdi.
#
# Bu iddia esigi BILINEN bir girdiyle sinar: 8px'lik bir kural taban
# altinda sayilmali, 20px'lik olan sayilmamali. Site nasil degisirse
# degissin gecerli.
_T = ".kucuk { font-size: 0.5rem; } .buyuk { font-size: 1.25rem; }"
esit([p for p, _, _ in taban_alti(_T)], [8.0],
     f"taban esigi ({TABAN_PX}px) 8px'i yakaliyor, 20px'i saymiyor")


def dar_adimlar(olcek: list[float]) -> list[tuple[float, float]]:
    """Birbirine `EN_KUCUK_ORAN`dan yakin komsu basamaklar."""
    s = sorted(olcek)
    return [(a, b) for a, b in zip(s, s[1:]) if b / a < EN_KUCUK_ORAN]


# AYIRT EDILEBILIRLIK ESIGI GERCEKTEN CALISIYOR MU.
#
# Olculdu (mutasyon E): `EN_KUCUK_ORAN`i 1.0'a cekmek sinamayi
# KIRMIZI yapmiyordu -- mevcut olcekte zaten cok yakin adim yok, yani
# esik gevsetilse de bulgu cikmiyordu. Esigin kendisi korumasizdi.
#
# ILK YAZIMDA CAPA YANLISTI: `[16, 17, 24]` verip 16->17'nin dar
# sayilmasini bekledim. Oysa 17/16 = 1,0625, yani esigin (1,06)
# USTUNDE -- dar sayilmamasi DOGRUYDU. Sinama kendi capasini
# duzeltti. Asagidaki cift gercekten dar: 21/20 = 1,05.
esit(dar_adimlar([20.0, 21.0, 30.0]), [(20.0, 21.0)],
     f"oran esigi ({EN_KUCUK_ORAN}) 20->21'i dar sayiyor, 21->30'u saymiyor")

print("\nOlcek")
_css = yorumsuz((_SITE / "statik" / "stil.css").read_text(encoding="utf-8"))
_JETON = jetonlar(_css)
esit(len(_JETON) >= 6, True, f"punto jetonu okundu ({len(_JETON)})")

_sirali = sorted(_JETON.values())
# Yukarida bilinen girdiyle sinanan fonksiyonun ta kendisi.
_dar = dar_adimlar(_sirali)
if _dar:
    print("\n  BIRBIRINE COK YAKIN ADIMLAR (hiyerarsi degil gurultu):")
    for a, b in _dar:
        print(f"    {a}px -> {b}px  (oran {b / a:.3f}, en az {EN_KUCUK_ORAN})")
esit(_dar, [], f"olcek adimlari ayirt edilebilir ({_sirali})")
esit(min(_sirali) >= TABAN_PX, True,
     f"en kucuk jeton tabanda ya da ustunde ({min(_sirali)}px)")

print("\nTaban: hicbir metin 12 pikselin altinda degil")
# Yukarida BILINEN girdiyle sinanan fonksiyonun ta kendisi. Ayni
# taramayi burada ikinci kez yazmak, "iki kod yolu ayni soruya iki
# cevap veriyor" kusuruna acik kapi birakirdi.
_kucuk = taban_alti(_css)
if _kucuk:
    print("\n  TABANIN ALTINDA:")
    for _p, _d, _s in sorted(_kucuk):
        print(f"    {_p:>5.1f}px  {_d:<12} {_s}")
esit(_kucuk, [], "12px altinda metin yok")

print("\nOlcek disi bildirimlerin gerekcesi var")


#: Defterdeki "sayi-gosterimi / marka / avatar" gerekcelerine karsilik
#: gelen seciciler. Ad listesi BURADA duruyor ki gerekce metniyle
#: kodun baktigi liste ayrisamasin -- bu depoda "iki kod yolu ayni
#: soruya iki cevap veriyor" kusuru defalarca yasandi.
MUAF_SECICI = (
    ".skor-deger", ".rakam b", ".vd-sayi", ".panel-sayim dd",
    ".nabiz-oge dd",          # sayi gosterimi
    ".logo", ".ag-simge",     # marka
    ".panel-avatar", ".avatar-onizleme",  # avatar
)


def gerekce_var(sec: str, deger: str) -> bool:
    if "clamp(" in deger:
        return True
    if re.fullmatch(r"[\d.]+em", deger.strip()):
        return True
    return any(parca in sec for parca in MUAF_SECICI)


# GEREKCE MEKANIZMASI DAR MI.
#
# Olculdu (mutasyon F): `gerekce_var`i `return True` yapmak -- yani
# HER SEYI muaf tutmak -- sinamayi kirmizi YAPMIYORDU, cunku kalan
# olcek disi bildirimlerin hepsi zaten muaf. Kural etkisizlesiyor ama
# kimse gormuyordu. Ayni katman eksigi bu depoda ucuncu kez: once
# mobil gizleme defterinde, sonra gorsel boyutu defterinde, simdi
# burada. Bir DEFTER varsa, defterin SINIRI da sinanmali.
esit(gerekce_var(".skor-deger", "2.4rem"), True, "defterdeki secici muaf")
esit(gerekce_var(".yeni-bilesen", "0.93rem"), False,
     "defterde OLMAYAN secici muaf DEGIL (defter genisletilemez)")
esit(gerekce_var(".yeni-bilesen", "clamp(1rem, 2vw, 2rem)"), True,
     "akiskan deger her secicide muaf")

_disi = []
for _sec, _deger in bildirimler(_css):
    _p = mutlak_px(_deger)
    if _p is None and "clamp(" not in _deger and not re.fullmatch(
            r"[\d.]+em", _deger.strip()):
        continue
    if _deger.startswith("var(--p-"):
        continue
    if gerekce_var(_sec, _deger):
        continue
    if _p is not None and _p in _JETON.values():
        # Deger olcekte VAR ama jeton yerine elle yazilmis: bu sapma.
        _disi.append((_p, _deger, _sec[:54], "jeton VAR, elle yazilmis"))
    elif _p is not None:
        _disi.append((_p, _deger, _sec[:54], "olcekte karsiligi yok"))

if _disi:
    print(f"\n  GEREKCESIZ OLCEK DISI BILDIRIM: {len(_disi)}")
    for _p, _d, _s, _n in sorted(_disi)[:20]:
        print(f"    {_p:>5.1f}px  {_d:<12} {_s:<56} {_n}")
    print("\n  Bunlar ya bir jetona cevrilmeli ya da GEREKCE defterine")
    print("  sebebiyle eklenmeli. 'Ugrasmadim' bir gerekce degildir.")
esit(len(_disi), 0, "her olcek disi bildirimin gerekcesi var")

print("\nSatir yuksekligi olcegi")
# Olculdu (2026-09-22): 112 satir yuksekligi bildiriminin 89'u elle
# yazilmisti ve icinde SAHTE AYRIMLAR vardi -- 1.5 ile 1.55 (onar
# kullanim) ayni isi yapiyordu, 1.35 ile 1.4 ayni isi. Gozle gorulur
# fark yok, ama sistem "burada bir karar var" diye okunuyordu.
#
# Katmanlar ADLANDIRILDI: 1.3 baslik, 1.4 kart/olay basligi, 1.5
# arayuz kunyesi, 1.6 okuma metni, 1.7 uzun govde. Her esleme en
# fazla 0,05em oynatti.

#: Jetona baglanmayan satir yuksekligi degerleri ve NEDEN.
SATIR_GEREKCE = {
    "1": "simge ve tek satirlik sayi/etiket: fazladan bosluk hizayi "
         "bozar. Bir 'ritim' degeri degil, 'ritim YOK' demek",
    "manset": "1.1 / 1.14 / 1.16 / 1.2 / 1.24 -- manset ve hero "
              "basliklari. Burada fark GERCEK: 30 piksellik bir "
              "baslikta 1.14 ile 1.3 arasi bes piksel, yani gorunur",
}
_MANSET = {"1.1", "1.14", "1.16", "1.2", "1.24"}


def satir_muaf(deger: str) -> bool:
    """Bu satir yuksekligi jetona baglanmak ZORUNDA degil mi?"""
    return deger == "1" or deger in _MANSET


# MUAFIYETIN SINIRI DA SINANIYOR.
#
# Olculdu (mutasyon J): muafiyet kontrolunu `if True` yapmak -- yani
# HER degeri muaf saymak -- sinamayi kirmizi YAPMIYORDU, cunku CSS
# zaten temizdi. Ayni katman eksigi bu oturumda DORDUNCU kez: mobil
# gizleme, gorsel boyutu, punto gerekcesi, simdi burada.
#
# Artik bir kural yazarken varsayilan olarak sunu soruyorum: "bu
# kuralin ISTISNASI genisletilirse kim fark eder?"
esit(satir_muaf("1"), True, "`1` muaf (simge/tek satir)")
esit(satir_muaf("1.14"), True, "manset degeri muaf")
esit(satir_muaf("1.55"), False, "sahte ayrim muaf DEGIL (istisna genisletilemez)")

_satir_jeton = {}
_kok_m = re.search(r":root\s*\{([^}]*)\}", _css, re.S)
for _ad, _v in re.findall(r"(--satir-[\w-]+)\s*:\s*([\d.]+)", _kok_m.group(1)):
    _satir_jeton[_ad] = float(_v)
esit(len(_satir_jeton) >= 3, True,
     f"satir yuksekligi jetonu okundu ({sorted(_satir_jeton.values())})")

_satir_dar = dar_adimlar(list(_satir_jeton.values()))
esit(_satir_dar, [], "satir yuksekligi adimlari ayirt edilebilir")

_kok_metin = _kok_m.group(0)
_disi_satir = []
for _m in re.finditer(r"([^{}]+)\{([^}]*)\}", _css.replace(_kok_metin, " ", 1)):
    _sec = " ".join(_m.group(1).split())
    for _v in re.finditer(r"(?<![\w-])line-height\s*:\s*([\d.]+)\s*[;}]",
                          _m.group(2)):
        _d = _v.group(1)
        if satir_muaf(_d):
            continue
        _disi_satir.append((_d, _sec[:52]))
if _disi_satir:
    print("\n  JETONA BAGLANMAMIS SATIR YUKSEKLIGI:")
    for _d, _s in sorted(set(_disi_satir)):
        print(f"    {_d:<6} {_s}")
    print("\n  Ya bir jetona baglanmali ya da SATIR_GEREKCE'ye sebebiyle")
    print("  eklenmeli. Iki deger ayni isi yapiyorsa ikisi de gerekmez.")
esit(_disi_satir, [], "her satir yuksekligi jetonlu ya da gerekceli")

print(f"\nTUM TESTLER GECTI ({_gecti})")
