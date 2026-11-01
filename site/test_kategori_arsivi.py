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
# UST SINIR 258 NASIL SECILDI:
#     40 kart x 20 oge              =   800
#     (SINIR - 40) arsiv satiri x 4
#     sabit yuk                     =   477
#     BETIK PAYI                    =   750
#
# Yani sunulan sayi 1.277 + 4 x (SINIR - 40), islenmis sayi onun
# 750 fazlasi. Uyari bolgesinin disinda kalmak icin
# (`DOM_SINIRI - UYARI_PAYI` = 2.900):
#
#     1.277 + 4 x (SINIR - 40) + 750 <= 2.900   ->   SINIR <= 258
#
# UST SINIR 400'DEN 258'E INDI VE SEBEBI OLCUM (2026-11-01):
# `test_dom_agirligi.dom_sayisi` SUNULAN HTML'i sayiyor, oysa
# Lighthouse ISLENMIS DOM'u olcuyor. Fark gercek Chrome'da olculdu
# ve en agir sayfada 741 oge cikti (gerekce `BETIK_PAYI` uzerinde).
# Eski hesapla 400 "guvenli" gorunuyordu; islenmis olcuyle
# 400 -> 3.467 oge, yani `DOM_SINIRI`nin (3.400) USTUNDE.
#
# Duzeltilmis olcum, ona DAYANAN siniri da duzeltmeli: iki yerde
# ayri kalsaydi, biri digerinin varsayimini sessizce curutur.
# Yururlukteki deger 240 ve yeni sinirin ALTINDA, yani bu
# daraltma hicbir seyi kirmiyor.
#
# ALT SINIR 50: `test_dom_agirligi.py` hub iddiasi sayfanin en az
# 200 analiz baglantisi tasimasini istiyor, yani 200'un altindaki
# bir sinir O iddiayi zaten dusurur. 50, bu iddianin isini "ucu
# acik olmasin" ile sinirli tutuyor; asil koruma orada.
# UST SINIR HESAPLANIYOR, YAZILMIYOR.
#
# Ilk yazimda sayi (400, sonra 258) ELLE yaziliydi ve mutasyon onu
# KACIRDI: siniri gevsetmek yururlukteki degeri (240) etkilemiyor,
# yani iddia yesil kaliyordu. Daha kotusu, elle yazilan sayi
# dayandigi olcumden sessizce AYRILIR -- `BETIK_PAYI` eklendigi gun
# 400 artik guvenli degildi ama sayi oldugu yerde duruyordu.
#
# Simdi ucu de kaynagindan okunuyor ve sinir yukaridaki aritmetikten
# TURETILIYOR.
_dom_kaynak = (_SITE / "test_dom_agirligi.py").read_text(encoding="utf-8")


def _sabit(ad: str) -> int:
    m = re.search(r"^" + ad + r" = (\d+)", _dom_kaynak, re.M)
    esit(m is not None, True, f"{ad} `test_dom_agirligi.py`de bulundu")
    return int(m.group(1))


_ESIK = _sabit("DOM_SINIRI")
_UYARI = _sabit("UYARI_PAYI")
_PAY = _sabit("BETIK_PAYI")
esit(_PAY > 0, True, f"betik payi sifir degil ({_PAY})")

#: Sayfanin sabit yuku ve oge basina maliyeti -- olculdu (2026-10-26).
_SABIT_YUK, _KART, _KART_OGE, _SATIR_OGE = 477, 40, 20, 4
_UST = _KART + max(0, (_ESIK - _UYARI - _PAY - _SABIT_YUK
                       - _KART * _KART_OGE)) // _SATIR_OGE
print(f"  ust sinir {_UST} (esik {_ESIK} - uyari {_UYARI} "
      f"- betik {_PAY} - sabit yuk {_SABIT_YUK} - kart yuku "
      f"{_KART * _KART_OGE}, satir basina {_SATIR_OGE})")
esit(50 <= SINIR <= _UST, True,
     f"sinir makul aralikta ({SINIR}; 50-{_UST})")
# ATILLIK: ust sinir gercekten bir seyi kisitliyor mu? Cok buyuk
# cikarsa iddia hicbir sey soylemez.
esit(_UST < 1000, True, f"ust sinir anlamli bir kisit ({_UST})")

# MODEL GERCEK SAYFAYLA DOGRULANIYOR.
#
# Yukaridaki sabitler sayfanin bir MODELI ve model yanlissa turetilen
# sinir da yanlis olur. Mutasyon bunu gosterdi: satir maliyeti 4 ->
# 1 yapildiginda ust sinir 258'den 1.032'ye cikti ve hicbir iddia
# kirmizi donmedi -- sinir "turetildi" ama dayanagi olculmemisti.
#
# Olcut HUB SAYFASININ KENDISI: model o sayfanin sunulan oge
# sayisini tahmin ediyor; tahmin ile olcum ayrisirsa sabitler artik
# sayfayi anlatmiyor.
_hub = _CIKTI / "makro" / "index.html"
if _hub.exists():
    _etiket_on = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)")
    _olculen = len(_etiket_on.findall(
        _hub.read_text(encoding="utf-8", errors="replace")))
    _tahmin = (_SABIT_YUK + _KART * _KART_OGE
               + max(0, SINIR - _KART) * _SATIR_OGE)
    _sapma = abs(_tahmin - _olculen)
    print(f"  model: /makro/ tahmin {_tahmin}, olculen {_olculen}, "
          f"sapma {_sapma}")
    # TOLERANS %12: model kaba ve olmali -- amac tam sayi degil,
    # sabitlerin sayfadan KOPMADIGINI gormek.
    esit(_sapma <= max(60, _olculen * 12 // 100), True,
         f"maliyet modeli gercek sayfayla uyusuyor "
         f"(tahmin {_tahmin}, olculen {_olculen})")
else:                                                  # pragma: no cover
    print("  (makro hub sayfasi yok -- model dogrulamasi atlandi)")

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
# ESIK VE BETIK PAYI KOPYALANMIYOR: ikisi de yukarida
# `test_dom_agirligi.py`den OKUNDU (`_sabit`). Burada ikinci kez
# okumak, ayni degeri iki desenle aramak demekti -- desenlerden biri
# degistigi gun ikisi sessizce ayrisirdi.
#
# ADI DOGRUDAN ARANIYOR (bkz. `_sabit`). Ilk yazimda desen
# ESIK|TAVAN ariyordu, sabitin adi ise `DOM_SINIRI` -- eslesmedi ve
# yedek desen ("dosyadaki ilk dort haneli sayi") devreye girdi.
# Dogru degeri buldu ama RASTGELE.
#
# OLCUT ISLENMIS DOM: sunulan sayiyla karsilastirmak, okurun
# odemedigi bir buyuklugu korumak olurdu.
_etiket = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)")
for _slug in _sluglar:
    _ap = _CIKTI / _slug / "arsiv" / "index.html"
    if not _ap.exists():
        continue
    _ham = len(_etiket.findall(_ap.read_text(encoding="utf-8",
                                             errors="replace")))
    _n = _ham + _PAY
    _pay = _ESIK - _n
    print(f"  /{_slug}/arsiv/ islenmis {_n} oge "
          f"(sunulan {_ham} + betik {_PAY}), pay {_pay} (esik {_ESIK})")
    # KARSILASTIRILAN SAYI GERCEKTEN ISLENMIS SAYI MI.
    #
    # Mutasyon bunu KACIRDI: pay eklenmese de `_n < _ESIK` dogru
    # kaliyordu, yani iddia payin uygulandigini HIC olcmuyordu.
    # Olculen deger kullanilmazsa olculmemis sayilir.
    esit(_n - _ham, _PAY, f"/{_slug}/arsiv/ karsilastirilan sayi "
                          f"betik payini ICERIYOR")
    esit(_n < _ESIK, True, f"/{_slug}/arsiv/ esigin altinda")

print(f"\nTUM TESTLER GECTI ({_gecti})")
