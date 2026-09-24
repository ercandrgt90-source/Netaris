# -*- coding: utf-8 -*-
"""ANALIZ SAYFALARI BIRBIRINE BAGLANMALI -- AMA DOGRU OLCUTLE.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-24): 696 analiz sayfasinin her birinde `<main>`
icinde ortalama 1.9 ic bag vardi ve ikisi de hub'a gidiyordu
(`/arastirmalar/`, `/makro/`). Haber sayfalarinda ayni sayi 22.
Sitenin AYIRT EDICI icerigi, en yalitik icerigiydi.

En somut sonuc: 40 sirketin iki ceyregi yayimlanmisti (80 sayfa) ve
HICBIRI otekine baglanmiyordu. ADESE'nin ikinci ceyregini okuyan okur
birinci ceyrege gidemiyordu.

ASIL TEHLIKE: OLCUTUN YANLIS OLMASI
-----------------------------------
"Ayni kod" olcutu ilk bakista butun analizlere uygulanabilir gorunuyor
cunku `kod` alani 696 kaydin hepsinde DOLU. Ama anlami ayni degil:

    Bilanco Analizi -> gercek sirket kodu (ADESE), donem = ceyrek
    Teknik Gorunum  -> varlik kodu (ETH, PAXG), donem = TARIH
    Makro           -> SABIT yer tutucu ("OLAY", "MAKRO")

Makro'da kod sabit oldugu icin olcut genisletilirse 309 ALAKASIZ olay
birbirine "ayni sirket" diye baglanir. Ayni yer tutucu bu depoda daha
once de yanlis eslesme uretti (`guncel_olanlar` / `uret_olay.py`).

Bu dosyanin asil isi bagliligi degil, KAPSAMIN DAR KALDIGINI tutmak.

NE SINANIYOR
------------
1. Kardes ceyregi olan her sayfa ona BAGLANIYOR.
2. Akranlar ayni SEKTOR ve ayni DONEM -- karsilastirma gercek.
3. Kapsam dar: Makro/Teknik sayfalari sahte "ayni sirket" bagi almiyor.
4. Akran sayisi sinirli -- liste gezinme araci, gurultu degil.
5. Bos blok basilmiyor.
6. Yeni bir bilesen uretilmedi -- `haber.html`teki kalip kullaniliyor.
"""

from __future__ import annotations

import collections
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


#: Bu dosyanin bekledigi akran tavani. `insa.ILGILI_AKRAN_SINIRI`den
#: OKUNMUYOR: korunan degeri korunan modulden almak, sabiti degistiren
#: kisinin beklentiyi de degistirmesi demek olurdu ve mutasyon sessizce
#: yesil kalirdi (bkz. `test_besleme_payi.py` icindeki ayni ders).
AKRAN_TAVANI = 4

#: Yer tutucu kodlar -- "ayni sirket" olcutune ASLA girmemeli.
YER_TUTUCU = {"OLAY", "MAKRO"}

print("\nKapsam kurali")
esit(insa.ILGILI_AKRAN_SINIRI <= AKRAN_TAVANI, True,
     f"akran tavani asilmamis ({insa.ILGILI_AKRAN_SINIRI} <= {AKRAN_TAVANI})")

print("\nUretilen ciktida")
if not (_CIKTI / "analiz").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_sayfalar = sorted((_CIKTI / "analiz").glob("*/index.html"))
esit(len(_sayfalar) > 100, True, f"analiz sayfasi uretilmis ({len(_sayfalar)})")

# KARDES CEYREK. Adres kalibi: <kod>-<yil>-<ceyrek>-ceyrek
_CEYREK = re.compile(r"^([a-z0-9]+)-(\d{4})-(\d)-ceyrek$")
_kod_sayfa: dict[str, list[str]] = collections.defaultdict(list)
for _p in _sayfalar:
    _m = _CEYREK.match(_p.parent.name)
    if _m:
        _kod_sayfa[_m.group(1)].append(_p.parent.name)

_cok = {k: v for k, v in _kod_sayfa.items() if len(v) > 1}
esit(len(_cok) > 0, True,
     f"birden fazla donemi olan sirket var ({len(_cok)})")

_kopuk = []
for _kod, _adlar in _cok.items():
    for _ad in _adlar:
        _g = (_CIKTI / "analiz" / _ad / "index.html").read_text(
            encoding="utf-8", errors="replace")
        if not any(f"/analiz/{_b}/" in _g for _b in _adlar if _b != _ad):
            _kopuk.append(_ad)
if _kopuk:
    print(f"\n  KARDES CEYREGINE BAGLANMAYAN: {len(_kopuk)} -> {_kopuk[:5]}")
esit(_kopuk, [],
     f"kardes ceyregi olan her sayfa ona BAGLANIYOR "
     f"({sum(len(v) for v in _cok.values())} sayfa)")

print("\nAkranlar gercekten akran")
# Ayni sektor VE ayni donem sarti: farkli ceyreklerin rakamlarini yan
# yana koymak, karsilastirma gibi gorunen ama olmayan bir sey uretirdi.
_analizler = {a.yol: a for a in insa.analizleri_yukle()}
_yanlis_donem, _yanlis_sektor, _bloklu = [], [], 0
for _p in _sayfalar:
    _yol = "/" + _p.relative_to(_CIKTI).as_posix().removesuffix("index.html")
    _a = _analizler.get(_yol)
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _m = re.search(r'<section class="okumaya-devam">.*?</section>', _g, re.S)
    if not _m:
        continue
    _bloklu += 1
    _blok = _m.group(0)
    # "Ayni sektor" oberkindeki baglar
    _sek = re.search(r"aynı dönem</h3>(.*?)</ul>", _blok, re.S)
    if not (_sek and _a):
        continue
    for _b in re.findall(r'href="(/analiz/[^"]+)"', _sek.group(1)):
        _hedef = _analizler.get(_b)
        if _hedef is None:
            continue
        if _hedef.donem != _a.donem:
            _yanlis_donem.append((_yol, _b))
        if _hedef.sektor != _a.sektor:
            _yanlis_sektor.append((_yol, _b))

esit(_bloklu > 0, True, f"makale sonu blogu basilmis ({_bloklu} sayfa)")
if _yanlis_donem:
    print(f"\n  FARKLI DONEMDEN AKRAN: {_yanlis_donem[:3]}")
esit(_yanlis_donem[:3], [], "her akran AYNI donemden")
if _yanlis_sektor:
    print(f"\n  FARKLI SEKTORDEN AKRAN: {_yanlis_sektor[:3]}")
esit(_yanlis_sektor[:3], [], "her akran AYNI sektorden")

print("\nKAPSAM DAR KALIYOR MU")
# Asil koruma burasi: yer tutucu kodlu analizler sahte "ayni sirket"
# bagi ALMAMALI. Olcut genisletilirse burasi kirmizi yanar.
_yer_tutuculu = [a for a in _analizler.values() if a.kod in YER_TUTUCU]
esit(len(_yer_tutuculu) > 50, True,
     f"yer tutucu kodlu analiz var ({len(_yer_tutuculu)}) -- olcut onlari "
     f"kapsasaydi hepsi birbirine baglanirdi")
_sahte_bag = []
for _a in _yer_tutuculu[:120]:
    _p = _CIKTI / _a.yol.strip("/") / "index.html"
    if not _p.exists():
        continue
    _g = _p.read_text(encoding="utf-8", errors="replace")
    if "okumaya-devam" in _g:
        _sahte_bag.append(_a.yol)
if _sahte_bag:
    print(f"\n  YER TUTUCU KODLU SAYFAYA BLOK BASILMIS: {_sahte_bag[:4]}")
esit(_sahte_bag, [], "yer tutucu kodlu analiz sahte ilgili bagi ALMIYOR")

print("\nAkran sayisi sinirli")
_asan = []
for _p in _sayfalar:
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _m = re.search(r"aynı dönem</h3>(.*?)</ul>", _g, re.S)
    if _m:
        _n = len(re.findall(r'href="/analiz/', _m.group(1)))
        if _n > AKRAN_TAVANI:
            _asan.append((_p.parent.name, _n))
if _asan:
    print(f"\n  TAVANI ASAN: {_asan[:4]}")
esit(_asan, [], f"hicbir sayfada {AKRAN_TAVANI}'ten fazla akran yok")

print("\nYENI BILESEN URETILMEDI")
# `haber.html` ayni isi `.okumaya-devam` ile yapiyor. Ikinci bir
# "ilgili icerik" bileseni, ayni soruya iki cevap veren iki kod yolu
# olurdu -- bu depoda defalarca temizlenen kusur.
_css = (_SITE / "statik" / "stil.css").read_text(
    encoding="utf-8", errors="replace")
esit(".okumaya-devam" in _css, True, "kullanilan bilesen stilde tanimli")
_h = (_SITE / "sablonlar" / "haber.html").read_text(encoding="utf-8")
_an = (_SITE / "sablonlar" / "analiz.html").read_text(encoding="utf-8")
esit("okumaya-devam" in _h and "okumaya-devam" in _an, True,
     "haber ve analiz AYNI bileseni kullaniyor")

print("\nKONTROLLERIN KENDISI CALISIYOR MU")
esit(bool(_CEYREK.match("adese-2026-2-ceyrek")), True,
     "ceyrek kalibi taniniyor")
esit(bool(_CEYREK.match("makro-gunluk-2026-09-24")), False,
     "ceyrek olmayan adres kalibi DISARIDA (kontrol zayif degil)")
esit("OLAY" in YER_TUTUCU and "ADESE" not in YER_TUTUCU, True,
     "yer tutucu listesi gercek sirket kodunu kapsamiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
