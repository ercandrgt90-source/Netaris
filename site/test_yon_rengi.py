# -*- coding: utf-8 -*-
"""YESIL VE KIRMIZI YALNIZCA SAYISAL YON ICIN KULLANILIR.

BU DOSYA NEDEN VAR
------------------
Kural `stil.css`in ILK SAYFASINDA yazili ve kesin:

    "YESIL VE KIRMIZI YALNIZCA SAYISAL YON ICINDIR. Arayuzun baska
     hicbir yerinde kullanilmaz: buton, etiket, baglanti, uyari...
     hicbiri. Sebep su: okur bu iki rengi gordugunde her zaman 'bir
     rakam degisti' diye okumali. Bir kez 'kaydet' butonunu yesil
     yaparsaniz o okuma bozulur ve bir daha kurulmaz."

OLCULDU (2026-10-05): kural ON BES yerde cigneniyordu --

    .rozet-kritik        kirmizi "KRITIK" rozeti
    .sondakika-etiket    kirmizi son dakika etiketi
    .uyelik-hata         kirmizi hata mesaji
    .panel-durum-hata    kirmizi durum
    .senaryo-sonuclanma  yesil/kirmizi sonuc cifti
    .etiket-kisi         kirmizi varlik etiketi
    .etiket-gosterge     yesil varlik etiketi
    .etiket-oran         yesil varlik etiketi
    .nokta-canli         yesil canli noktasi
    .akis-nokta          yesil akis noktasi
    .rozet-kaynak        yesil kaynak rozeti
    .ds-yeni             yesil "yeni" rozeti
    .uyelik-mesaj.iyi    yesil basari mesaji
    .panel-durum-tamam   yesil durum
    .takvim-oge.onem-3   kirmizi onem seridi

Yani kural yaziliydi, uygulayan hicbir sey YOKTU -- bu depodaki en
pahaliya mal olan kusur sinifi.

NASIL COZULDU -- YENI RENK ICAT EDILMEDI
----------------------------------------
Palet neredeyse dolu: uyari 34, artis 123, vurgu 177, konu renkleri
210-318, azalis 351 derece. Otuz derecelik bos bir bant YOK. Yeni
bir ton uydurmak ya mevcut bir sinyale yaklasirdi ya da paleti
dagitirdi.

Bunun yerine her bilesen NE ANLATTIGINA gore yerlestirildi:

    OLUMLU / CANLI / BIZE AIT  -> --vurgu (marka)
    DIKKAT (kritik, hata)      -> --uyari (zaten dikkat sinyali)
    KATEGORIK (varlik etiketi) -> --t-* konu paleti (ton ayrimi
                                  `test_kontrast.py` ile zorlaniyor)
    SIRALI (takvim onemi)      -> tek tonun uc gucu

Siddet farki RENKLE degil BICIMLE anlatiliyor: en yuksek sesli olan
(KRITIK, SON DAKIKA) dolu zemin, daha sakin olan (hata mesaji) sol
serit aliyor.

NE SINANIYOR
------------
`--artis` ve `--azalis` yalnizca YON tasiyan seciciler icinde
geciyor. Liste KISITLAYICI: yeni bir kullanim eklendiginde kirmizi
yanar ve ekleyen kisi "bu gercekten bir sayinin yonu mu" sorusuyla
karsilasir.
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

#: YON tasidigi KABUL EDILEN seciciler. Her biri bir sayinin ya da
#: bir grafik isaretinin yonunu gosteriyor.
#:
#: Liste ISTISNA DEGIL TANIM: "yesil/kirmizi nerede mesru" sorusunun
#: cevabi. Yeni bir giris eklemek, o bilesenin gercekten bir SAYININ
#: yonunu gosterdigini iddia etmek demek.
_YON_SECICILERI = (
    ".artis", ".azalis",                       # dogrudan yon siniflari
    ".kalem-kivilcim.artis", ".kalem-kivilcim.azalis",   # serit kivilcimi
    ".vd-degisim.artis", ".vd-degisim.azalis",           # deger degisimi
    ".varlik-kivilcim .kivilcim-artis",                  # varlik kivilcimi
    ".varlik-kivilcim .kivilcim-dusus",
    ".grafik-yukselis", ".grafik-dusus",                 # cizgi/alan grafigi
    ".yazi-gorsel svg",                                  # SVG renk eslemesi
)

_ihlal = []
for _m in re.finditer(r"([^{}]+)\{([^{}]*)\}", _SADE):
    _sec = re.sub(r"\s+", " ", _m.group(1)).strip()
    _gov = _m.group(2)
    for _j in ("--artis", "--azalis"):
        if not re.search(rf"var\(\s*{_j}\s*\)", _gov):
            continue
        if any(_y in _sec for _y in _YON_SECICILERI):
            continue
        _ihlal.append(f"{_sec[:52]}  ->  var({_j})")

if _ihlal:
    print(f"\n  YON RENGI, YON OLMAYAN YERDE: {len(_ihlal)}")
    for _x in _ihlal[:10]:
        print(f"    {_x}")
    print("  Yesil/kirmizi yalnizca bir SAYININ yonu icin.")
    print("  Olumlu/canli -> --vurgu · dikkat -> --uyari")
    print("  kategorik -> --t-* · sirali -> tek tonun gucleri")
esit(_ihlal, [], "yon renkleri yalnizca yon tasiyan secicilerde")

#: Olcum BOS DONMESIN: liste dogru calisiyorsa mesru kullanimlar
#: GORULUYOR olmali. Aksi halde desen bozulsa da sinama yesil kalirdi.
_mesru = len(re.findall(r"var\(\s*--(?:artis|azalis)\s*\)", _SADE))
esit(_mesru >= 12, True, f"yon rengi mesru yerlerde kullaniliyor ({_mesru})")

#: Donusturulen bilesenler ARTIK yon rengi tasimiyor -- deger
#: sabitlemesi, tek tek.
for _s, _beklenen in ((".rozet-kritik", "--uyari"),
                      (".sondakika-etiket", "--uyari"),
                      (".panel-durum-hata", "--uyari"),
                      (".panel-durum-tamam", "--vurgu"),
                      (".nokta-canli", "--vurgu"),
                      (".akis-nokta", "--vurgu"),
                      (".ds-yeni", "--vurgu"),
                      (".etiket-kisi", "--t-jeopolitik"),
                      (".etiket-gosterge", "--t-makro"),
                      (".etiket-emtia", "--t-emtia")):
    _k = re.search(rf"{re.escape(_s)}\s*\{{([^{{}}]*)\}}", _SADE, re.S)
    esit(bool(_k) and f"var({_beklenen})" in _k.group(1), True,
         f"{_s} -> {_beklenen}")

print(f"\nTUM TESTLER GECTI ({_gecti})")
