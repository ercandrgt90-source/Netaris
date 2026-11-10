# -*- coding: utf-8 -*-
"""Sitede sayfasi olan sirket kodlari -- TEK KAYNAK.

NEDEN AYRI MODUL
----------------
Bu soruyu UC yer soruyor ve ucu de ayni cevabi vermek zorunda:

  * `sektor_tazele.kuyruk`  -- hangi sirkete sektor sorulacak
    (kaniti olan once: hakkinda sayfa yayimladigimiz sirket, islem
    goren bir sirkettir)
  * `uret_bilanco.main`     -- sayfasi olup OZETTE OLMAYAN sirket
    var mi (sessiz dusmenin olcumu)
  * ileride baska bir adim

Uc kopya, "ayni karari veren iki liste" kusurunun ta kendisi olurdu;
bu depoda o kusur bir kez olculup kayda gecti (`$YOLLAR` ile geri
yazma kapisi iki ayri listeyle karar veriyordu).

OKUMA ON BILGIDEN, DOSYA ADINDAN DEGIL
--------------------------------------
`yayin.yaz_sektorel` dosyayi TERS sirada adlandiriyor:

    damga   : tera-2026-6
    dosya   : 2026-6-tera.md

Dosya adindan kod cikarmak, kodu BULAMAMAK demek. Ayni tuzak
`uret_bilanco_sayfa._yayimlanmis` icinde atlamayi TUMDEN calismaz
hale getirmisti: hat her kosuda ayni sirketi yeniden uretip ayni
model cagrisini ikinci kez odeyecekti.

AG YOK, YAZMA YOK: yalnizca diskteki on bilgi okunuyor.
"""

from __future__ import annotations

import pathlib

_KOK = pathlib.Path(__file__).resolve().parent

#: Analiz sayfalarinin klasoru. `uret_bilanco_sayfa.SITE` ile ayni
#: yer; burada ayri yazilmasinin sebebi o modulun AI katmanini da
#: ice almasi -- bu islevi cagiran adimlarin cogu model cagirmiyor.
SAYFALAR = _KOK.parent / "site" / "icerik" / "analizler"


def sayfasi_olan_kodlar(klasor=None, kategori: str = "") -> set[str]:
    """Sitede analiz sayfasi olan sirket kodlari.

    `kategori` verilirse YALNIZCA o kategorideki sayfalar sayilir.

    NEDEN GEREKLI -- OLCULDU (2026-11-10)
    -------------------------------------
    Suzgec olmadan BTC ve ETH de listeye giriyor: ikisinin "Teknik
    Gorunum" sayfasi var ama ikisi de SIRKET degil. Sayfasi olup
    bilanco ozetinde olmayan sirketleri sayan olcum bu yuzden 47
    bildiriyordu, dogrusu 45 ve ikisi sahteydi. Olcum araci kendi
    yanlisini uretiyordu.

    Kategori istemeyen cagiran da var: sektor kuyrugu icin "herhangi
    bir sayfa" gecerli bir kanit, cunku o kuyruk zaten yalnizca
    DEFTERDEKI sirketleri geziyor.

    `Path.glob` olmayan yolda da, bir DOSYAYA isaret eden yolda da
    bos uretiyor ve hic yukselmiyor -- bu yuzden ayri bir "klasor var
    mi" korumasi YOK. Onceki surumde boyle bir koruma vardi ve bir
    MUTASYON ondan kacti: korudugu dal hic yurunmuyordu, yani onu
    sinayan iddia her halde geciyordu.
    """
    yer = klasor if klasor is not None else SAYFALAR
    cikti: set[str] = set()
    for p in yer.glob("*.md"):
        try:
            satirlar = p.read_text(encoding="utf-8").splitlines()[:25]
        except OSError:
            continue
        kod = ""
        kat = ""
        for satir in satirlar:
            if satir.startswith("kod:"):
                kod = satir[4:].strip().upper()
            elif satir.startswith("kategori:"):
                kat = satir[9:].strip()
        if kod and (not kategori or kat == kategori):
            cikti.add(kod)
    return cikti


#: Bilanco sayfalarinin kategorisi. Sayfayi URETEN taraf bu dizgiyi
#: on bilgiye yaziyor; olcen taraf da ayni dizgiyi kullanmali.
BILANCO_KATEGORI = "Bilanço Analizi"
