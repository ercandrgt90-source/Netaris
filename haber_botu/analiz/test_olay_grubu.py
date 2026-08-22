"""Olay gruplamasi: ayni gelismeye ait haberler tek kimlik altinda.

BU DOSYA NEDEN VAR
------------------
Depodaki `olay` tablosu 102 olay tasiyor ve 101 farkli habere bagli --
yani 1'e 1, gruplama YOK. `olay.Olay.anahtar` baslik govdelerinin
karmasi ve kendi isini dogru yapiyor ("ayni yaziyi iki kez uretme");
gruplama daha KABA bir kimlik istiyor: ulke + tur + donem.

OLCUM SIRASINDA IKI GERCEK HATA CIKTI
-------------------------------------
1. "Brezilya merkez bankasi" haberi TR grubuna dusuyordu. "merkez
   bankasi" isareti fazla genel -- her ulkenin bir merkez bankasi var.
   Duzeltilince baglam denetimi IKI GERCEK IHLAL daha buldu (Hindistan
   haberinde TR verisi, Rusya haberinde US verisi): yanlis ulke atamasi
   uyusmazlik kontrolunu de kor birakiyormus.

2. "cin " deseni "iCIN " icinde eslesti ve butun Hurmuz Bogazi
   haberleri "Cin jeopolitik gelismeleri" grubuna dustu. Bu depoda ayni
   tuzak daha once " ges " ile yasandi.

Ikisi de ancak GRUPLARA BAKINCA gorundu -- birim sinamalari gecerken
gruplama saglamayi gosteriyordu.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from analiz import baglam, olay_grubu  # noqa: E402

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


# --------------------------------------------------------------------
# KIMLIK -- uc parcanin UCU DE gerekli.
# --------------------------------------------------------------------
esit(olay_grubu.kimlik("Fed faiz kararını açıkladı", "Investing",
                       "2026-08-19"), "US:faiz:2026-08",
     "ulke + tur + donem")
esit(olay_grubu.kimlik("Bugün hava güzel", "Investing", "2026-08-19"),
     None, "olay turu yoksa gruplanmiyor")
esit(olay_grubu.kimlik("Faiz kararı açıklandı", "Investing", ""),
     None, "tarih yoksa gruplanmiyor")

# --------------------------------------------------------------------
# BASLIK -- kimlikten okunur ada.
# --------------------------------------------------------------------
esit(olay_grubu.grup_basligi("US:faiz:2026-08"),
     "ABD faiz kararı — Ağustos 2026", "kimlik -> okunur baslik")
esit(olay_grubu.grup_basligi("bozuk"), "bozuk",
     "cozulemeyen kimlik oldugu gibi doner -- uydurulmaz")

# --------------------------------------------------------------------
# KISA ULKE ADLARI KELIME ICINDE ESLESMEMELI.
#
# "cin " -> "iCIN " esleşmesi butun Hurmuz haberlerini Cin grubuna
# tasidi. Kural: dort harften kisa desenler iki yani da bosluklu olmali.
# --------------------------------------------------------------------
esit(baglam.haber_ulkesi("NATO komutanı Hürmüz Boğazı için görüşme yaptı",
                         "", "TR"), "TR",
     '"icin" kelimesi Cin ile karistirilmiyor')
esit(baglam.haber_ulkesi("Çin Merkez Bankası likidite verdi"), "CN",
     "gercek Cin haberi taniniyor")
esit(baglam.haber_ulkesi("Çin'in ihracatı arttı"), "CN",
     "ek almis Cin taniniyor")

for _isaret, _u in baglam.ULKE_ADLARI:
    if len(_isaret.strip()) <= 4:
        esit(_isaret.startswith(" ") and _isaret.endswith((" ", "'")), True,
             f"{_isaret!r} kisa -- iki yani sinirli olmali")

# --------------------------------------------------------------------
# GERCEK DEPOYA KARSI: gruplar tutarli mi.
# --------------------------------------------------------------------
if olay_grubu.DEPO.exists():
    _b = sqlite3.connect(f"file:{olay_grubu.DEPO}?mode=ro", uri=True)
    _g = olay_grubu.gruplar(_b)

    # Her grup esigi gecmeli.
    esit([a for a, v in _g.items() if len(v) < olay_grubu.EN_AZ_HABER], [],
         f"her grup en az {olay_grubu.EN_AZ_HABER} haber tasiyor")

    # Kimlikler cozulebilmeli: cozulemeyen kimlik, basligi ham
    # basar ve okura "US:faiz:2026-08" gorunur.
    _ham = [a for a in _g if olay_grubu.grup_basligi(a) == a]
    esit(_ham, [], "butun grup kimlikleri okunur baslik uretiyor")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
