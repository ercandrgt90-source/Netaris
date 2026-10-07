# -*- coding: utf-8 -*-
"""YONLENDIRME HARITASI BIRLESTIRILMELI, USTUNE YAZILMAMALI.

BU DOSYA NEDEN VAR
------------------
`tekrar_temizle.py` silinen her sayfa icin "eski adres -> kalan adres"
yaziyor ve bu haritayi `site/yonlendirme.json` dosyasinda tutuyor.
Once dosyayi DUZ YAZIYORDU:

    HARITA.write_text(json.dumps(harita, ...))

Yani aracin ikinci kosusu, birinci kosunun yazdigi butun
yonlendirmeleri SILIYORDU. Daha onceki silmelerin adresleri sessizce
404'e donerdi -- hem de dosya yine "dolu" gorundugu icin kimsenin
fark etmeyecegi bicimde.

Ikinci sorun ZINCIR: eski haritada A -> B varken yeni kosuda B -> C
yazilirsa, A iki adimli bir yonlendirmeye dusuyor. Okur iki kez
yonleniyor, arama motoru zincirin sonunu ayri bir adres sayiyor.

NE SINANIYOR
------------
1. Eski kayitlar KORUNUYOR.
2. Ayni kaynak icin yeni hedef eskisini EZIYOR (en son karar gecerli).
3. Zincir coz uluyor: A -> B, B -> C ise A dogrudan C'ye.
4. Dongu (A -> B -> A) sonsuz donguye girmiyor ve kendine isaret eden
   kayit birakmiyor.

SENTETIK VERI -- VE BU BILINCLI. Gercek `yonlendirme.json` su an bos;
ona bakan bir sinama hicbir sey elemezdi.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import tekrar_temizle                            # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("")
print("Yonlendirme haritasi birlestirme")

esit(tekrar_temizle.birlestir({"/haber/a/": "/haber/x/"},
                              {"/haber/b/": "/haber/y/"}),
     {"/haber/a/": "/haber/x/", "/haber/b/": "/haber/y/"},
     "eski kayit korunuyor")

esit(tekrar_temizle.birlestir({"/haber/a/": "/haber/x/"},
                              {"/haber/a/": "/haber/y/"}),
     {"/haber/a/": "/haber/y/"},
     "ayni kaynakta yeni karar gecerli")

esit(tekrar_temizle.birlestir({"/haber/a/": "/haber/b/"},
                              {"/haber/b/": "/haber/c/"}),
     {"/haber/a/": "/haber/c/", "/haber/b/": "/haber/c/"},
     "zincir cozuluyor")

esit(tekrar_temizle.birlestir({"/haber/a/": "/haber/b/", "/haber/b/": "/haber/c/"},
                              {"/haber/c/": "/haber/d/"}),
     {"/haber/a/": "/haber/d/", "/haber/b/": "/haber/d/",
      "/haber/c/": "/haber/d/"},
     "uc adimli zincir de cozuluyor")

_d = tekrar_temizle.birlestir({}, {"/haber/a/": "/haber/b/",
                                   "/haber/b/": "/haber/a/"})
esit([k for k, v in _d.items() if k == v], [], "dongu kendine isaret birakmiyor")

esit(tekrar_temizle.birlestir({}, {"/haber/a/": "/haber/a/"}), {},
     "kendine yonlendirme atiliyor")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
