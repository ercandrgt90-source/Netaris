# -*- coding: utf-8 -*-
"""TABLO DAR EKRANDA SESSIZCE KESILMEMELI.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-10-07), 390 piksel genisliginde gercek aygit taklidiyle
haber sayfasindaki duyarlilik tablosu:

    tablo icerigi   519 piksel
    tablo kutusu    358 piksel
    sayfa tasmasi     0 piksel

Ucuncu sutun ("neden") ekran disindaydi ve KAYDIRILABILIYORDU -- ama
bunu soyleyen hicbir isaret yoktu. Ekran goruntusu alindi: "Ara mali
t" diye kelimenin ortasinda kesiliyordu. Okur bunu kirik bir sayfa
sanar, kaydirmayi denemez.

Markdown tablolari zaten `.tablo-kaydir` kabinda ve o kabin cercevesi
"burasi ayri bir kutu" diyor. Duyarlilik tablosu kapsizdi: ayni isi
iki ayri duzenek yapiyordu ve isaret tasiyan taraf yoktu.

OLCUM BIR IDDIAMI DA CURUTTU. "Tabloya `display: block` vermek onu
erisilebilirlik agacindan dusurur" diye dusunmustum. Chrome'un
erisilebilirlik agaci cekildi: table 3, row 28, cell 55,
columnheader 7 -- roller YERINDE. O iddia geri alindi; olculmeden
yazilan kusur, kusur degildir.

GERCEK KUSUR BASKAYDI: kaydirmayi TABLO yapiyordu, isareti ise KAP
tasiyacakti. `kayiyor: true` ama `kapKayiyor: false`. Golge kabin
uzerinde, kaydirma tablonun icinde -- hicbir zaman bulusmuyorlardi.

NE SINANIYOR
------------
1. Uretilen HER tablo bir `.tablo-kaydir` kabinin icinde. Istisna
   YOK: `/tasarim/` sayfasinin tablolari da kaba alindi, cunku
   istisna listesi tutmak kurali yavasca bosaltmanin yolu.
2. `.tablo-kaydir > table` kuralinda `display: table` var -- bu
   olmadan dar ekran taban kurali tabloyu kendi kaydirma kabina
   cevirir ve isaret olu kalir. Olculen kusurun ta kendisi.
3. Kaydirma isaretinin dort katmani ve `background-attachment`
   ikilisi (local, local, scroll, scroll) duruyor. Biri silinirse
   golge ya hic gorunmez ya da KAYDIRILACAK YER KALMADIGINDA DA
   gorunur -- ikisi de yanlis isaret.

NEREYE BAKILIYOR
----------------
Hem uretilen ciktiya (madde 1) hem kaynak CSS'e (2 ve 3). Ciktiya
bakmak sablonda unutulan kabi yakaliyor; CSS'e bakmak kuralin kendisi
silindiginde haber veriyor. Biri otekini kapsamiyor.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_CSS = _SITE / "statik" / "stil.css"

_gecti = 0


def dogru(kosul, aciklama: str, ek: str = "") -> None:
    global _gecti
    if not kosul:
        print(f"  DUSTU  {aciklama}")
        if ek:
            print(f"    {ek}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("")
print("Tablo kaydirma kabi")

# Yorumlar atiliyor: bu dosyanin kendi aciklamasini kural sanmak,
# `test_stil.py` icinde bir kez yasanmis bir yanlis.
_kural = re.sub("/[*].*?[*]/", " ", _CSS.read_text(encoding="utf-8-sig"),
                flags=re.S)

_blok = re.search("[.]tablo-kaydir[ ]*[{](.*?)[}]", _kural, re.S)
dogru(_blok is not None, ".tablo-kaydir kurali duruyor")
_g = _blok.group(1)
dogru("overflow-x: auto" in _g, "kap yatay kayabiliyor")
dogru(_g.count("linear-gradient") == 4,
      "kaydirma isareti dort katman tasiyor",
      f"bulunan: {_g.count('linear-gradient')}")
dogru("local, local, scroll, scroll" in " ".join(_g.split()),
      "background-attachment ikilisi duruyor (local + scroll)")

_tab = re.search("[.]tablo-kaydir[ ]*>[ ]*table[ ]*[{]([^}]*)[}]", _kural, re.S)
dogru(_tab is not None, ".tablo-kaydir > table kurali duruyor")
dogru("display: table" in _tab.group(1),
      "kap icindeki tablo KENDI kaydirma kabina donmuyor")

if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print("")
    print(f"TUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_ACILIS = re.compile("<table( [^>]*)?>")
_toplam = 0
_kapsiz = []
for _p in _CIKTI.rglob("*.html"):
    _s = _p.read_text(encoding="utf-8", errors="replace")
    for _m in _ACILIS.finditer(_s):
        _toplam += 1
        # Kap tablodan hemen once aciliyor; arada baslik ya da
        # aciklama olabilir diye 300 karakterlik pencereye bakiliyor.
        if "tablo-kaydir" not in _s[max(0, _m.start() - 300):_m.start()]:
            _kapsiz.append("/" + _p.parent.relative_to(_CIKTI).as_posix() + "/")
print(f"  tarandi: {_toplam} tablo")
dogru(_toplam > 100, f"tarama dolu ({_toplam} tablo)")
dogru(not _kapsiz, "kabi olmayan tablo yok",
      f"{len(_kapsiz)} tane, ilki: {_kapsiz[0] if _kapsiz else ''}")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
