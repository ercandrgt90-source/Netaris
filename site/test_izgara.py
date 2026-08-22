"""Iki sutunlu izgaralarda UCUNCU COCUK sessizce alt satira duser.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): AYNI GUN, AYNI SINIF HATA IKI YERDE.

1) Ana sayfa `.masa`
   Izgara `minmax(0,1fr) 316px` -- iki sutun. Ama uc dogrudan cocugu
   vardi: `.masa-ana`, piyasa kutusu, `.masa-akis`. Otomatik
   yerlestirme:

       masa-ana   -> sutun 1, satir 1
       tv-kutu    -> sutun 2, satir 1
       masa-akis  -> sutun 1, satir 2     <-- ANA SUTUNA DUSTU

   Canli akis yan sutunda degil, haber listesinin ALTINDA tam
   genislikte cikiyordu. Kodda "yan sutunda" yaziyordu, yorumda da.

2) Haber karti `.haber`
   `168px 1fr` -- iki sutun. Fotografi VE atfi olan kartlarda uc
   cocuk oluyordu (gorsel, atif, icerik):

       gorsel  -> sutun 1, satir 1
       atif    -> sutun 2, satir 1        <-- bos alanda asili
       icerik  -> sutun 1, satir 2        <-- 168px'e sikisti

   Baslik dort satira boluniyordu. Yalnizca ATFI OLAN kartlarda --
   yani cogu kart duzgun, arada biri bozuk. Sebebi en zor gorulen tur.

NEDEN SINAMA
------------
Hicbiri hata vermiyor. Izgara gecerli, butun ogeler basiliyor, sayfa
cikiyor. CSS "ucuncu cocuk fazla" diye uyarmaz -- yerlestirir.

Ve bu hata SABLONA BIR SATIR EKLEYINCE olusuyor: yan sutuna yeni bir
kutu koymak, karta yeni bir rozet eklemek. Yani en dogal degisiklik
onu geri getirir.

Cozum ikisinde de ayni: fazladan cocugu SARMALLAMAK. Sarmal
`.masa-yan` ve `.haber-medya`. Bu sinama sarmallarin durdugunu ve
cocuk sayisinin ikide kaldigini tutuyor.

NE SINANMIYOR
-------------
CSS'in kendisi degil, URETILEN HTML. Sablon dogru gorunup ciktinin
bozuk olmasi mumkun (`{% if %}` dallari); olculen sey okurun aldigi
sayfa.
"""

from __future__ import annotations

import pathlib
import sys
from html.parser import HTMLParser

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

_gecti = 0
_kaldi = 0

#: Kapanis etiketi olmayan ogeler -- derinlik saymada onemli.
_BOS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


class Cocuklar(HTMLParser):
    """Verilen sinifa sahip ogelerin DOGRUDAN cocuk sayilarini toplar."""

    def __init__(self, sinif: str) -> None:
        super().__init__(convert_charrefs=True)
        self.sinif = sinif
        self.sayilar: list[int] = []
        self._yigin: list[dict] = []      # acik ogeler
        self._izlenen: list[dict] = []    # ilgilendigimiz ogeler

    def handle_starttag(self, etiket, oznitelikler):
        if etiket in _BOS:
            # Bos oge cocuk sayilir ama yigina girmez.
            if self._izlenen and len(self._yigin) == self._izlenen[-1]["derinlik"]:
                self._izlenen[-1]["sayi"] += 1
            return
        sinif = dict(oznitelikler).get("class") or ""
        # Once: acik bir izlenen ogenin DOGRUDAN cocugu muyum?
        if self._izlenen and len(self._yigin) == self._izlenen[-1]["derinlik"]:
            self._izlenen[-1]["sayi"] += 1
        self._yigin.append({"etiket": etiket})
        if self.sinif in sinif.split():
            self._izlenen.append({"derinlik": len(self._yigin), "sayi": 0})

    def handle_endtag(self, etiket):
        if etiket in _BOS:
            return
        # Kapanan oge izlenen ise sayiyi kaydet.
        if self._izlenen and self._izlenen[-1]["derinlik"] == len(self._yigin):
            self.sayilar.append(self._izlenen.pop()["sayi"])
        if self._yigin:
            self._yigin.pop()


def cocuk_sayilari(dosya: pathlib.Path, sinif: str) -> list[int]:
    ay = Cocuklar(sinif)
    ay.feed(dosya.read_text(encoding="utf-8"))
    return ay.sayilar


# --------------------------------------------------------------------
# Cozumleyicinin KENDISI once sinaniyor.
#
# Bu depoda tekrar eden ders: eksik tarama TEMIZ RAPOR uretir. Bir
# cozumleyici sessizce bos liste dondurse, asagidaki butun sinamalar
# "gecti" derdi.
# --------------------------------------------------------------------
print("\nCozumleyici dogru sayiyor (kendi kendini sinar)")


def _say(html: str, sinif: str) -> list[int]:
    a = Cocuklar(sinif)
    a.feed(html)
    return a.sayilar


esit(_say('<div class="k"><p>1</p><p>2</p></div>', "k"), [2],
     "iki cocuk sayiliyor")
esit(_say('<div class="k"><p>1</p><p>2</p><p>3</p></div>', "k"), [3],
     "uc cocuk sayiliyor")
esit(_say('<div class="k"><div><p>a</p><p>b</p></div></div>', "k"), [1],
     "torunlar sayilmiyor")
esit(_say('<div class="k"><img src="x"><p>1</p></div>', "k"), [2],
     "kapanissiz oge (img) de cocuk")
esit(_say('<div class="k a"><p>1</p></div>', "k"), [1],
     "cok sinifli oge bulunuyor")
esit(_say('<div class="kk"><p>1</p></div>', "k"), [],
     "benzer isimli sinif eslesmiyor")
esit(_say('<div class="k"><p>1</p></div><div class="k"><p>1</p><p>2</p></div>',
          "k"), [1, 2], "birden cok oge ayri sayiliyor")

# --------------------------------------------------------------------
# IKI SUTUNLU IZGARALAR
# --------------------------------------------------------------------
print("\n.masa -- iki sutun, iki cocuk")
ana = _CIKTI / "index.html"
if not ana.exists():
    print("  ATLANDI  cikti yok (once `python insa.py`)")
else:
    masa = cocuk_sayilari(ana, "masa")
    esit(len(masa), 1, ".masa ana sayfada bir kez")
    esit([s for s in masa if s != 2], [],
         ".masa tam iki cocuk tasiyor (ana sutun + yan sutun)")
    esit(len(cocuk_sayilari(ana, "masa-yan")) >= 1, True,
         "yan sutun sarmali (.masa-yan) duruyor")

print("\n.haber -- iki sutun, en cok iki cocuk")
gundem = _CIKTI / "gundem" / "index.html"
if not gundem.exists():
    print("  ATLANDI  cikti yok")
else:
    kart = cocuk_sayilari(gundem, "haber")
    esit(len(kart) > 0, True, "kart bulundu")
    # Gorselsiz kartta tek cocuk (yalnizca icerik) -- o dogru.
    esit(sorted({s for s in kart}) and max(kart) <= 2, True,
         f"hicbir kartta ikiden fazla cocuk yok (en cok {max(kart)})")
    # Atifli kartlarda sarmal gercekten kullanilmis mi?
    medya = cocuk_sayilari(gundem, "haber-medya")
    esit(len(medya) > 0, True, "gorsel sarmali (.haber-medya) kullaniliyor")
    esit(max(medya) <= 2, True,
         "sarmal en cok iki cocuk tasiyor (gorsel + atif)")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
