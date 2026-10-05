# -*- coding: utf-8 -*-
"""BAGIMSIZ EYLEMLER 44 PIKSEL DOKUNMA HEDEFI TASIMALI.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-10-05, 390x844 mobil) -- her sayfada tekrar eden
hedefler esigin altindaydi:

    .logo                           91x28     her sayfa
    .ust-giris / .ust-kayit         61x36     her sayfa
    .tema-dugme                     36x36     her sayfa
    .haber-git "Haberi oku ->"      80x27     /gundem/ 36 adet
    summary "Ne olursa ne olur?"   295x29     /makro/ 7 adet
    .modul-tum "Tum gelismeler ->"  87x21     ana sayfa 5 adet
    .sp-dugme (paylasim ikonu)      36x44     GENISLIK dar

Hicbiri WCAG 2.5.8 (AA, 24x24) ihlali DEGILDI. Ama 2.5.5 (AAA) ve
hem Apple hem Google kilavuzlari 44 piksel diyor; parmak ucunun
gercek temas alani bu. Ust serit YAPISKAN, yani okur dort hedefe
HER SAYFADA ve cogunlukla tek elle uzaniyor.

CUMLE ICI BAGLANTILAR BILEREK DISARIDA
--------------------------------------
Kirinti yolu ("Arastirmalar"), gizlilik metnindeki atiflar, "uye
olun" gibi cumle ici baglantilar BUYUTULMEDI. Onlari buyutmek satir
araligini bozar ve WCAG metin ici baglantilari zaten muaf tutuyor.
Kural BAGIMSIZ EYLEMLERE bakiyor.

NE SINANIYOR -- VE NEDEN BOYLE
------------------------------
Gercek olcu TARAYICI gerektiriyor (ogenin cizilmis kutusu), CI'da
tarayici yok. Onun yerine KARARLAR sabitleniyor: her biri bir
olcumun sonucu ve degistiren kisi bu dosyayi da guncellemek zorunda
kalir -- o an "44 pikselden kucuk olmali mi" sorusuyla karsilasir.

Tarayici olcumu `scratchpad/tarayici/supurge.mjs` ile yapildi ve
sonuc: ana sayfa, /gundem/, /makro/, /topluluk/ ve analiz
sayfalarinda bagimsiz eylem hedefi KALMADI (yalnizca kirinti yolu,
ki o bilerek disarida).
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
esit(len(_SADE) > 1000, True, "stil dosyasi okundu")

#: Ust seritteki butun ogeler TEK jetondan olculuyor. Ayri ayri
#: `min-height` yazmak denendi ve `.ust-eylem .tema-dugme` (0,2,0)
#: onu eziyordu -- jetonla yarismak yerine jeton degisti.
_m = re.search(r"--ust-oge:\s*(\d+)px", _SADE)
esit(bool(_m), True, "`--ust-oge` jetonu bulundu")
esit(int(_m.group(1)) >= 44, True,
     f"ust serit oge olcusu >= 44px (gelen: {_m.group(1)}px)")

#: `.logo` ayni jetona bagli -- gorsel buyumuyor, yalnizca
#: tiklanabilir alan.
esit(bool(re.search(r"\.logo\s*\{[^{}]*min-height:\s*var\(--ust-oge\)",
                    _SADE, re.S)),
     True, "marka baglantisi ayni olcuye bagli")

#: `.haber-git` DOLGU + NEGATIF KENAR ile buyuyor: 36 kartta
#: tekrarlandigi icin `min-height` sayfayi 612 piksel uzatirdi.
#: Deger 18; 17 denenmisti ve ham yukseklik 43,797 cikmisti --
#: olcum araci yuvarlayip "44" gosteriyordu.
_h = re.search(r"\.haber-alt \.haber-git\s*\{([^{}]*)\}", _SADE, re.S)
esit(bool(_h), True, "`.haber-git` kurali bulundu")
_gov = _h.group(1)
esit(bool(re.search(r"padding:\s*6px 0 18px", _gov)), True,
     "`.haber-git` dolgusu 18px (hedef 44,8 piksel)")
esit(bool(re.search(r"margin:\s*0 0 -18px", _gov)), True,
     "`.haber-git` negatif kenari dolguyu dengeliyor (duzen degismiyor)")

#: Bagimsiz bolum eylemleri.
for _s in (".modul-tum", ".bolum-baglanti", ".akis-devam",
           ".senaryo-davet-ikincil"):
    esit(bool(re.search(rf"{re.escape(_s)}[^{{}}]*\{{[^{{}}]*min-height:\s*44px",
                        _SADE, re.S))
         or bool(re.search(rf"{re.escape(_s)},", _SADE)),
         True, f"{_s} 44px kuralinda")
esit(bool(re.search(r"\.senaryo-davet-ikincil\s*\{[^{}]*min-height:\s*44px",
                    _SADE, re.S)),
     True, "bolum eylemleri kurali gercekten 44px veriyor")

#: Acilir baslik (`<details>` togglesi) ve ikon dugmesi.
esit(bool(re.search(r"summary\s*\{[^{}]*min-height:\s*44px", _SADE, re.S)),
     True, "acilir baslik 44px")
esit(bool(re.search(r"\.sp-dugme\s*\{[^{}]*min-width:\s*44px", _SADE, re.S)),
     True, "paylasim ikon dugmesi 44px GENISLIK (yukseklik zaten 44)")

#: BEGENI DUGMESI -- yalnizca CANLIDA goruluyor (sayac `sayac.js`
#: ile doluyor; yerel sunucuda API yok). Yerel tarama "temiz"
#: demisti, kusuru canli olcum gosterdi: 25,2x19,2 ve sayfa basina
#: 26-60 adet.
#:
#: WCAG 2.5.8 IHLALI DEGIL -- standardin ARALIK istisnasi var ve en
#: yakin HEDEF satirin diger ucunda. Yine de parmakla basilan bir
#: dugme icin kucuk.
#:
#: ASIMETRIK dolgu BILINCLI: saginda 17, altinda 21 piksel bosluk
#: var; solunda goruntulenme sayaci, USTUNDE kart metni. Buyume
#: asagi veriliyor ki metnin son satirindan yanlislikla begeni
#: dokunusu alinmasin.
_b = re.search(r"\.sayac-begeni\s*\{([^{}]*)\}", _SADE, re.S)
esit(bool(_b), True, "`.sayac-begeni` kurali bulundu")
esit(bool(re.search(r"padding:\s*4px 10px 21px", _b.group(1))), True,
     "begeni dolgusu asimetrik (agirlik ASAGI)")
esit(bool(re.search(r"margin:\s*-4px -10px -21px", _b.group(1))), True,
     "negatif kenar dolguyu dengeliyor (kart uzamiyor)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
