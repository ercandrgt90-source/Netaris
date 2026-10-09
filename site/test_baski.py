# -*- coding: utf-8 -*-
"""BASKI KURALLARI OLU SECICIYE BAGLANMAMALI.

BU DOSYA NEDEN VAR
------------------
`@media print` icindeki "arayuz kagida gitmez" listesi, sayfa
chrome'unu gizleyen uzun bir secici dizisi. Icindeki bir sinif adi
degisirse kural SESSIZCE eslesmeyi birakir: ekranda hicbir sey
degismez, sinamalar yesil kalir, ve kusur yalnizca biri sayfayi
YAZDIRDIGINDA goruluyor. Kimse yazdirmadigi icin de hic goruldugu
yok.

OLCULDU (2026-10-04), sayfa baski kipinde cizdirilip BAKILDI:

  LISTEDE OLMAYAN ama kagida giden uc sey --
    .onay-bandi    cerez cubugu, sayfanin dibinde koyu bir serit
    .yazi-serit    kenar serit; kagitta tiklanamaz, metni daraltiyor
    .alt-gezinme   mobil alt cubuk

  LISTEDE OLAN ama hicbir seye baglanmayan dort secici --
    .menu  .mobil-menu  .suzgec  .uyelik-cagri

Yani liste iki yonden birden gerisinde kalmisti. Dordu de
kaldirildi; gizledikleri sanilan bilesenlerin baska kurallarla zaten
gizlendigi tarayicida dogrulandi (menu `.ust` icinde, suzgec kabinin
gercek adi `.akis-suzgec`).

NE SINANIYOR
------------
1. Baski listesindeki her sinif secicisi, sablonlarda ya da
   betiklerde GERCEKTEN bir sinif adi olarak geciyor.
2. Bilinen chrome bilesenleri listede DURUYOR (deger sabitlemesi).
3. Serit gizlenince izgara da sifirlaniyor -- yoksa yazi, bos bir
   216 piksellik sutunun saginda asili kalir.

NEREYE BAKILIYOR -- VE NEDEN ORAYA
----------------------------------
Ilk yazimda "sinif stil dosyasinda tanimli mi" diye bakiyordum.
YANLIS YERDI: bir sinifin kendi CSS kurali olmayabilir ama HTML'de
pekala bulunabilir (`.menu` gibi -- kurallari `.menu-grup`,
`.menu-katman`). O olcu bes yanlis pozitif uretti.

Uretilen cikti da bakilabilirdi ama KOR NOKTASI var: cerez cubugunu
JavaScript kuruyor ve `.onay-bandi` statik HTML'de hic gecmiyor.
O olcu "olu" derdi ve gercekten gereken bir kural silinirdi.
Dogru yer KAYNAK: sablonlar + betikler.

NE SINANMIYOR -- VE BU BILINCLI
-------------------------------
"Yeni eklenen bir chrome bileseni listeye girdi mi" statik olarak
olculemiyor: bir bilesenin "arayuz" mi "icerik" mi oldugu bicimsel
bir soru degil. Onu yakalayan sey tarayicida baski kipinde BAKMAK.
Yeni bir yapiskan/sabit bilesen eklerken ayni bakisi tekrarlayin.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_CSS = (_SITE / "statik" / "stil.css").read_text(encoding="utf-8")
_SADE = re.sub(r"/\*.*?\*/", " ", _CSS, flags=re.S)

_i = _SADE.find("@media print")
esit(_i > 0, True, "@media print blogu bulundu")
_BASKI = _SADE[_i:]

_gizle = re.findall(r"([^{}]+)\{\s*display:\s*none\s*!important\s*\}", _BASKI)
esit(bool(_gizle), True, f"gizleme kurali bulundu ({len(_gizle)})")

_siniflar: set[str] = set()
for _kural in _gizle:
    _siniflar |= set(re.findall(r"\.([a-zA-Z][\w-]*)", _kural))
esit(len(_siniflar) >= 10, True,
     f"baski listesinde {len(_siniflar)} sinif secicisi var")

_KAYNAK = (sorted((_SITE / "sablonlar").glob("*.html"))
           + sorted((_SITE / "statik").glob("*.js")))
_METIN = [p.read_text(encoding="utf-8", errors="replace") for p in _KAYNAK]
esit(len(_METIN) > 10, True, f"kaynak dosya okundu ({len(_METIN)})")


def _kullaniliyor(ad: str) -> bool:
    """Sinif adi TAM TOKEN olarak geciyor mu.

    Parca eslesmesi yanlis sonuc verir: `begeni` ile `begeni-sayi`
    ayri seyler ve ilki yoksa kural oludur. Tirnak turu (tek, cift,
    ters) ARANMIYOR -- JS'te sinif adi her ucuyle de yazilabiliyor ve
    tirnak esleyen bir desen yalnizca kirilganlik ekler.
    """
    desen = re.compile(rf"(?<![\w-]){re.escape(ad)}(?![\w-])")
    return any(desen.search(m) for m in _METIN)


_olu = sorted(a for a in _siniflar if not _kullaniliyor(a))
if _olu:
    print(f"\n  HICBIR SEYI GIZLEMEYEN SECICI: {len(_olu)}")
    for _s in _olu:
        print(f"    .{_s}")
    print("  Sablonlarda ve betiklerde bu adla bir sinif yok --")
    print("  ad degismis ya da bilesen kaldirilmis olabilir.")
esit(_olu, [],
     f"baski listesindeki her secici bir seye baglaniyor ({len(_siniflar)})")

# --- 2) bilinen chrome bilesenleri listede ---
#: Deger sabitlemesi. Biri listeden cikarilirsa kirmizi yanar ve
#: cikaran kisi "bu kagida gitmeli mi" sorusuyla karsilasir.
#: `.atla` 2026-10-09'da eklendi ve AYNI GUN kagitta goruldu:
#: `left: -9999px` ile ekran disinda duruyor ama `display` hala blok,
#: yani baski alani hesabina giriyor. Yeni bir arayuz ogesi eklerken
#: bu listeye bakmak BIR ADIM; eklemeyi unutmak, listenin zamanla
#: gerisinde kalmasinin tam yolu -- bu dosyanin var olma sebebi de o.
_SART = ("ust", "serit", "sayfa-paylas", "sayac",
         "onay-bandi", "yazi-serit", "alt-gezinme", "tel-kap", "atla")
_eksik = [s for s in _SART if s not in _siniflar]
if _eksik:
    print(f"\n  BASKI LISTESINDEN DUSMUS: "
          f"{', '.join('.' + x for x in _eksik)}")
esit(_eksik, [], f"bilinen chrome bilesenleri listede ({len(_SART)})")

# --- 3) serit gizlenince izgara da sifirlaniyor ---
esit(bool(re.search(r"\.yazi-duzen[^{}]*\{[^{}]*display:\s*block\s*!important",
                    _BASKI, re.S)),
     True, "serit gizlenince yazi duzeni tek kolona donuyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
