# -*- coding: utf-8 -*-
"""LISANS ATIFLARI SAYFADA GORUNMEK ZORUNDA.

BU DOSYA NEDEN VAR
------------------
Iki yukumluluk depoda ACIKCA yazili ama HICBIR SINAMA tutmuyordu:

  stil.css:2614  "Atif CC BY geregi ZORUNLU"
  stil.css:7510  "Atif: TradingView kosullari geregi ZORUNLU,
                  gorunur kalmali. Kucuk ama okunur -- gizlemek yasak."
  _tradingview.html  "ATIF -- TradingView kosullari geregi ZORUNLU."

`_lisans_denetimi` VERIDE atif olup olmadigini "hata" seviyesinde
tutuyor. Ama sablon o atfi BASMAYI birakirsa veri denetimi yine yesil
kalir ve sayfa atifsiz yayimlanir. Kural yazildi, zorlanmadi -- bu
depoda tekrar eden kusur siniflarindan biri.

OLCULDU (2026-09-24): IHLAL YOK
-------------------------------
848 sayfa lisansli fotograf tasiyor, 848'i de atif gosteriyor;
parcacigi olan tek sayfada TradingView atfi yerinde. Yani bu dosya
bir kusuru DUZELTMIYOR, sessizce kirilmasini engelliyor.

Ilk olcum "192 sayfa atifsiz" demisti ve YANLISTI: desen
`/statik/foto/uretilen/` altindaki KENDI cizdigimiz kavram
gorsellerini de lisansli sanmisti. Ikinci yanlis, ana sayfanin
`foto-kunye-toplu` (toplu kunye) sinifini tanimamakti. Olcum aracinin
kendisi iki kez yanlis alarm uretti; site dogruydu.

NE SINANIYOR
------------
1. Lisansli fotograf tasiyan her sayfa atif gosteriyor.
2. URETILEN gorsel muafiyeti GERCEK ve DAR -- lisansli yolu yutmuyor.
3. TradingView parcacigi olan her sayfa atif bagini tasiyor.
4. Hicbir CSS kurali bu atiflari tek basina gizlemiyor.
5. Kontrollerin kendisi calisiyor (uydurma ihlal yakalaniyor).
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_CSS = _SITE / "statik" / "stil.css"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Kendi urettigimiz kavram gorselleri -- atif gerektirmiyorlar
#: cunku kaynaklari biziz. Muafiyet TEK BIR dizinle sinirli.
MUAF_DIZIN = "/statik/foto/uretilen/"

#: Atif kunyesinin gecerli bicimleri. `-toplu`, kart gorsellerinin
#: ortak kunyesi (ana sayfa); tekil kunye ile ayni isi goruyor.
KUNYE = re.compile(r'class="(?:foto-atif|foto-kunye|foto-kunye-toplu)\b')
FOTO = re.compile(r'<img[^>]+src="(/statik/foto/[^"]+)"')
TV_KAP = "tradingview-widget-container"
TV_ATIF = "tradingview-widget-copyright"
TV_BAG = "https://www.tradingview.com/"


def lisansli_foto(govde: str) -> list[str]:
    return [s for s in FOTO.findall(govde) if MUAF_DIZIN not in s]


print("\nMuafiyet gercek ve DAR")
# Muafiyetin kendisi sinaniyor: genisletilirse burasi kirmizi yanar.
esit(lisansli_foto('<img src="/statik/foto/uretilen/kavram-1.jpg">'), [],
     "uretilen gorsel muaf (atif istemiyor)")
esit(lisansli_foto('<img src="/statik/foto/k/tcmb-7.jpg">'),
     ["/statik/foto/k/tcmb-7.jpg"],
     "lisansli fotograf MUAF DEGIL (muafiyet dar)")
esit(lisansli_foto('<img src="/statik/foto/uretilen2/x.jpg">'),
     ["/statik/foto/uretilen2/x.jpg"],
     "benzer isimli dizin muafiyete girmiyor")

print("\nKunye bicimleri taniniyor")
esit(bool(KUNYE.search('<p class="foto-kunye">Fotograf: X</p>')), True,
     "tekil kunye taniniyor")
esit(bool(KUNYE.search('<p class="foto-kunye-toplu">Gorseller: X</p>')), True,
     "TOPLU kunye taniniyor (ana sayfa bunu kullaniyor)")
esit(bool(KUNYE.search('<p class="foto-baslik">X</p>')), False,
     "ilgisiz sinif kunye sayilmiyor (kontrol zayif degil)")

print("\nCSS atfi gizlemiyor")
_css = _CSS.read_text(encoding="utf-8", errors="replace")
# Kural GOVDESI ile bakiliyor: yalnizca atif sinifini hedefleyip
# gizleyen bir kural ihlal. `.tv-kutu{display:none}` ihlal DEGIL --
# orada parcacik da gizleniyor, yani gosterilen bir sey yok.
_gizli = []
for _sec, _gov in re.findall(r"([^{}]+)\{([^{}]*)\}", _css):
    if not re.search(r"foto-atif|foto-kunye|" + TV_ATIF, _sec):
        continue
    if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|"
                 r"opacity\s*:\s*0(?!\.)|font-size\s*:\s*0", _gov):
        _gizli.append(_sec.strip()[:60])
if _gizli:
    print(f"\n  ATFI GIZLEYEN KURAL: {_gizli}")
esit(_gizli, [], "hicbir kural atif kunyesini gizlemiyor")

print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_foto_sayfa = _foto_atifli = 0
_atifsiz: list[str] = []
_tv_sayfa = 0
_tv_atifsiz: list[str] = []
for _p in _CIKTI.rglob("*.html"):
    _g = _p.read_text(encoding="utf-8", errors="replace")
    _yol = "/" + _p.relative_to(_CIKTI).as_posix()
    if lisansli_foto(_g):
        _foto_sayfa += 1
        if KUNYE.search(_g):
            _foto_atifli += 1
        else:
            _atifsiz.append(_yol)
    if TV_KAP in _g:
        _tv_sayfa += 1
        if TV_ATIF not in _g or TV_BAG not in _g:
            _tv_atifsiz.append(_yol)

esit(_foto_sayfa > 0, True,
     f"lisansli fotograf tasiyan sayfa var ({_foto_sayfa})")
if _atifsiz:
    print(f"\n  ATIFSIZ LISANSLI FOTOGRAF: {len(_atifsiz)} -> {_atifsiz[:5]}")
esit(_atifsiz, [], f"her lisansli fotografin kunyesi var ({_foto_atifli})")

esit(_tv_sayfa > 0, True, f"TradingView parcacigi kullaniliyor ({_tv_sayfa})")
if _tv_atifsiz:
    print(f"\n  TRADINGVIEW ATFI EKSIK: {_tv_atifsiz}")
esit(_tv_atifsiz, [], "parcacigin oldugu her sayfada TradingView atfi var")

print("\nKONTROLLERIN KENDISI CALISIYOR MU")
_sahte_foto = '<article><img src="/statik/foto/k/tcmb-7.jpg"></article>'
esit(bool(lisansli_foto(_sahte_foto)) and not KUNYE.search(_sahte_foto), True,
     "kunyesiz lisansli fotograf YAKALANIYOR")
_sahte_tv = f'<div class="{TV_KAP}"></div>'
esit(TV_KAP in _sahte_tv and TV_ATIF not in _sahte_tv, True,
     "atifsiz TradingView parcacigi YAKALANIYOR")
_gizleyen = ".foto-kunye { display: none }"
_bulundu = [
    s for s, gov in re.findall(r"([^{}]+)\{([^{}]*)\}", _gizleyen)
    if re.search(r"foto-kunye", s) and re.search(r"display\s*:\s*none", gov)
]
esit(len(_bulundu), 1, "atfi gizleyen CSS kurali YAKALANIYOR")

print(f"\nTUM TESTLER GECTI ({_gecti})")
