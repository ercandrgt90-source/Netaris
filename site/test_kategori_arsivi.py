# -*- coding: utf-8 -*-
"""KATEGORI SAYFASI ICERIKTEN BAGIMSIZ BUYUKLUKTE KALMALI.

BU DOSYA NEDEN VAR
------------------
`/makro/` sayfasi UC KEZ DOM esigini asti ve her seferinde dagitim
durdu:

    2026-09-18   5.753 oge
    2026-10-19   3.417 oge   (esik 3.400)   dagitim 4 saat kapali
    2026-10-26   3.401 oge   (BIR oge asma) dagitim 4,3 saat kapali

Her seferinde ayni kol cekildi: kart sayisi dusuruldu (48 -> 44 -> 40)
ya da kart hafifletildi. Her seferinde icerik buyudu ve esigi yeniden
yakaladi. Ucuncusunden sonra olculdu:

    sayfadaki analiz          474
    bunlardan kart            40
    bunlardan arsiv satiri    434   <- SINIRSIZ BIRIKIYOR
    satir basina oge          4
    yeni oge / gun            7,4
    kalan pay                 387 oge  =  DOKUZ GUN

Yani kusur kart sayisinda degildi: sayfa TUM kategoriyi listeliyordu
ve her yeni analiz sayfayi kaliciolarak buyutuyordu. Kart sayisini bir
kez daha dusurmek esigi ERTELERDI, kaldirmazdi.

NE SINANIYOR
------------
1. Hicbir kategori sayfasi `KATEGORI_LISTE_SINIRI`den fazla analiz
   BASMIYOR. Bu, sayfa buyuklugunu icerik miktarindan ayiran iddia.
2. Siniri asan her kategori arsive BAGLANIYOR. Birinci madde sonucu
   olcuyor, bu madde DUZENEGI: arsiv sayfasi dururken ona giden bag
   silinse birinci madde yine gecerdi -- ama o zaman arsivin kendisi
   ve listeledigi her analiz YETIM kalirdi.
3. Arsiv sayfasi kategorinin TAMAMINI listeliyor. Arsivi KIRPMAK bu
   depoda bir kez denendi (432 -> 288 satir) ve `test_yetim_sayfa`
   47 OKSUZ SAYFA bildirdi; o yol kapali ve bu iddia kapali
   tutuyor.
4. Kategori sayfasindaki "N analizden" cumlesi TOPLAMI soyluyor,
   basili liste uzunlugunu degil. Liste kirpildiktan sonra bu cumle
   uzunluga bakmaya devam etseydi okur "240 analizden" okurdu ve
   geri kalan 235 analiz hic anilmazdi -- hata vermeyen, sessiz bir
   yanlis.

NEDEN CIKTIYA BAKIYOR
---------------------
Sablonda bir dongu olmasi, dongunun kirpilmis bir liste uzerinde
dondugunu kanitlamaz. Bu kusur sinifi -- "bag sablonda var ama liste
sinirli" -- bu depoda `test_yetim_sayfa` dosyasinin dogus sebebi.

YENI YUZEY, YENI KORUMA
-----------------------
`/<kategori>/arsiv/` YENI bir cikti turu. `test_yetim_sayfa` yalnizca
`/haber/` ve `/analiz/` altini tariyor, yani arsiv sayfasinin KENDISI
yetim kalsa onu hicbir sinama gormezdi. Bu depoda ayni ders yazili:
yeni bir yayin yuzeyi, mevcut korumalarin tamamini atlatir.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path.insert(0, str(_SITE))

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


if not _CIKTI.exists():
    print("  ATLANDI  cikti yok -- once `python site/insa.py`")
    raise SystemExit(0)

# SINIR KOPYALANMIYOR, `insa.py`DEN OKUNUYOR.
#
# Sabiti buraya yazmak, sinirin degistigi gun sessizce yanlis sinanan
# bir kural birakirdi. Bu depoda ayni ders defalarca yasandi.
_kaynak = (_SITE / "insa.py").read_text(encoding="utf-8")
_m = re.search(r"^KATEGORI_LISTE_SINIRI = (\d+)", _kaynak, re.M)
esit(_m is not None, True, "KATEGORI_LISTE_SINIRI `insa.py`de bulundu")
SINIR = int(_m.group(1))
print(f"  sinir: {SINIR} analiz")

# SINIRIN KENDISI DE SINANIYOR -- HAREKETLI HEDEF KAPATILIYOR.
#
# OLCULDU (mutasyon, 2026-10-26): sinir 240 -> 9999 yapildi ve bu
# sinama YESIL kaldi. Sebep yukaridaki okuma: mutasyon hem siniri
# hem BEKLENTIYI birlikte buyuttu. "Hicbir sayfa 9999 analizi
# asmiyor" dogru ama BOS bir cumle.
#
# Okuma KALIYOR -- siniri kopyalamak, degistigi gun sessizce yanlis
# sinanan bir kural birakirdi (bu depodaki en pahali kusur sinifi).
# Ustune ARALIK konuyor.
#
# UST SINIR 400 NASIL SECILDI:
#     40 kart x 20 oge         =   800
#     360 arsiv satiri x 4     = 1.440
#     sabit yuk                =   477
#                                ------
#                                2.717 oge
# `DOM_SINIRI` 3.400, yani pay 683. `UYARI_PAYI` 500 oldugu icin
# 400'den buyuk bir sinir sayfayi DOGUSTAN uyari bolgesine sokar;
# yani sinir kendi amacini yemis olur.
#
# ALT SINIR 50: `test_dom_agirligi.py` hub iddiasi sayfanin en az
# 200 analiz baglantisi tasimasini istiyor, yani 200'un altindaki
# bir sinir O iddiayi zaten dusurur. 50, bu iddianin isini "ucu
# acik olmasin" ile sinirli tutuyor; asil koruma orada.
esit(50 <= SINIR <= 400, True,
     f"sinir makul aralikta ({SINIR}; 50-400)")

# BLOK PARANTEZ DENGELENEREK CIKARILIYOR.
#
# Ilk yazimda desen `^\s*\("([a-z0-9-]+)",` idi ve ESLESMEDI:
# `KATEGORILER` yapisinda acilis parantezi ile slug AYRI SATIRLARDA.
# Arama dosyanin geri kalanina tasti, `giris`/`kayit`/`panel` gibi
# ilgisiz dizgeler dondu ve sinama YESIL yanarak hicbir sey olcmedi
# -- var olan `/makro/arsiv/` sayfasini bile gormedi.
_bas = _kaynak.index("KATEGORILER = (")
_d, _son = 0, len(_kaynak)
for _i in range(_bas + len("KATEGORILER = "), len(_kaynak)):
    if _kaynak[_i] == "(":
        _d += 1
    elif _kaynak[_i] == ")":
        _d -= 1
        if _d == 0:
            _son = _i
            break
_blok = _kaynak[_bas:_son]
_sluglar = re.findall(r'\(\s*"([a-z0-9-]+)"', _blok)
esit(len(_sluglar) >= 3, True,
     f"kategori slug'lari okundu ({_sluglar})")
# SINAMA ATIL OLMAMALI -- MEKANIZMA SINANIYOR, ICERIK DEGIL.
#
# Yukaridaki okuma sessizce bozulabilir (bir kez bozuldu). Bu iddia
# okumanin DOGRU YERDEN geldigini tutuyor: bu iki kategori
# `KATEGORILER` listesinin kendisinde yazili, yani liste okunduysa
# ikisi de gelir. Analiz SAYISI sinanmiyor -- o icerige bagli ve
# icerik mesru olarak degisir.
for _beklenen in ("bilancolar", "makro"):
    esit(_beklenen in _sluglar, True,
         f"{_beklenen!r} slug listesinde (okuma dogru yerden)")
esit(len(_sluglar) <= 12, True,
     f"liste makul boyda ({len(_sluglar)}) -- tasma yok")

_BAG = re.compile(r'href="(/analiz/[^"#?]+)')

print("\n1) Kategori sayfalari siniri ASMIYOR")
_asan = []
_bulunan = 0
_gorulen_bag = 0
for _slug in _sluglar:
    _p = _CIKTI / _slug / "index.html"
    if not _p.exists():
        continue
    _bulunan += 1
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _bag = len(set(_BAG.findall(_h)))
    _gorulen_bag += _bag
    if _bag > SINIR:
        _asan.append(f"/{_slug}/ {_bag} analiz (sinir {SINIR})")
esit(_bulunan > 0, True, f"kategori sayfasi bulundu ({_bulunan})")
# TARAMA DOLU MU? Hicbir sayfada analiz baglantisi bulunmazsa
# birinci madde bos bir kume uzerinde "sinir asilmadi" der ve bu
# hicbir sey kanitlamaz.
esit(_gorulen_bag > 0, True,
     f"taranan sayfalar analiz baglantisi tasiyor ({_gorulen_bag})")
if _asan:
    print(f"\n  SINIRI ASAN SAYFA: {_asan}")
esit(_asan, [], f"hicbir kategori sayfasi {SINIR} analizi asmiyor")

print("\n2) Siniri asan kategori arsive BAGLANIYOR")
_arsivli = 0
for _slug in _sluglar:
    _p = _CIKTI / _slug / "index.html"
    _ap = _CIKTI / _slug / "arsiv" / "index.html"
    if not _p.exists():
        continue
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _bag = len(set(_BAG.findall(_h)))
    # Arsiv VARSA, ona giden bag da olmali.
    if _ap.exists():
        _arsivli += 1
        esit(f'href="/{_slug}/arsiv/"' in _h, True,
             f"/{_slug}/ arsive baglaniyor")
    # Sayfa siniri DOLDURUYORSA kategoride daha fazla analiz var
    # demektir ve arsiv URETILMIS olmali.
    elif _bag >= SINIR:
        esit(False, True,
              f"/{_slug}/ {_bag} analiz basiyor ama arsiv sayfasi YOK")
print(f"  arsivi olan kategori: {_arsivli}")

print("\n3) Arsiv sayfasi kategorinin TAMAMINI listeliyor")
for _slug in _sluglar:
    _ap = _CIKTI / _slug / "arsiv" / "index.html"
    _p = _CIKTI / _slug / "index.html"
    if not _ap.exists() or not _p.exists():
        continue
    _ah = _ap.read_text(encoding="utf-8", errors="replace")
    _h = _p.read_text(encoding="utf-8", errors="replace")
    _a_bag = set(_BAG.findall(_ah))
    _k_bag = set(_BAG.findall(_h))
    # Kategori sayfasindaki her analiz arsivde de olmali: arsiv
    # "kalanlar" degil TAM liste. Boylece bir analiz hangi tarafta
    # kirpilirsa kirpilsin ulasilabilir kaliyor.
    _eksik = sorted(_k_bag - _a_bag)
    if _eksik:
        print(f"\n  ARSIVDE OLMAYAN: {_eksik[:5]}")
    esit(_eksik, [],
         f"/{_slug}/arsiv/ kategori sayfasindakilerin tamamini tasiyor")
    # Ve arsiv, kategori sayfasindan DAHA COK tasimali -- yoksa
    # arsivin var olma sebebi yok.
    esit(len(_a_bag) > len(_k_bag), True,
         f"/{_slug}/arsiv/ {len(_a_bag)} > sayfa {len(_k_bag)}")
    # Toplam SAYFADA YAZILI olanla tutmali.
    _t = re.search(r"<p>(\d+) analizden", _h)
    esit(_t is not None, True, f"/{_slug}/ toplami yaziyor")
    esit(int(_t.group(1)), len(_a_bag),
         f"/{_slug}/ yazdigi toplam ({_t.group(1)}) arsivdeki sayiyla ayni")

print("\n4) Arsiv sayfasi DOM esiginin altinda")
# ESIK KOPYALANMIYOR: `test_dom_agirligi.py`den okunuyor.
_dom = (_SITE / "test_dom_agirligi.py").read_text(encoding="utf-8")
# ADI DOGRUDAN ARANIYOR. Ilk yazimda desen ESIK|TAVAN ariyordu,
# sabitin adi ise `DOM_SINIRI` -- eslesmedi ve yedek desen
# ("dosyadaki ilk dort haneli sayi") devreye girdi. Dogru degeri
# buldu ama RASTGELE: dosyaya baska bir dort haneli sayi eklendigi
# gun sessizce yanlis esigi okurdu.
_me = re.search(r"^DOM_SINIRI = (\d+)", _dom, re.M)
esit(_me is not None, True, "DOM esigi okundu")
_ESIK = int(_me.group(1))
_etiket = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)")
for _slug in _sluglar:
    _ap = _CIKTI / _slug / "arsiv" / "index.html"
    if not _ap.exists():
        continue
    _n = len(_etiket.findall(_ap.read_text(encoding="utf-8",
                                           errors="replace")))
    _pay = _ESIK - _n
    print(f"  /{_slug}/arsiv/ {_n} oge, pay {_pay} (esik {_ESIK})")
    esit(_n < _ESIK, True, f"/{_slug}/arsiv/ esigin altinda")

print(f"\nTUM TESTLER GECTI ({_gecti})")
