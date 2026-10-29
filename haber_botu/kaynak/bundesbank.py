# -*- coding: utf-8 -*-
"""Almanya 10 yillik devlet tahvili getirisi -- Bundesbank'in KENDISINDEN.

    BBSIS zaman serisi ucu -> (tarih, getiri) -> gosterge tablosu

NEDEN AYRI BIR MODUL
--------------------
`/varlik/de10y/` sayfasi bos duruyordu: ne serisi ne haberi vardi
(olculdu 2026-10-29, canli site). Varligin kendi tanimi ise
"Euro Bolgesinin risksiz getiri cipasi; diger uye ulke tahvilleri
buna gore fiyatlanir" -- yani rakami olmadan sayfa vaat ettigi seyi
veremiyor.

NEDEN FRED DEGIL
----------------
FRED'in Almanya 10 yilligi `IRLTLT01DEM156N` ve iki sorunu var:

  1. AYLIK. Olculdu: son gozlem 2026-09-01, yani ~2 ay geride. Bir
     getiri cipasinin aylik ortalamasi, gunluk hareketi okuyan bir
     sayfada "bugunku gorunum" olarak duramaz.
  2. KAYNAGI OECD. Bu depo yeniden yayimladigi veriyi kaynagina gore
     seciyor (bkz. `makro_uret_ucretsiz.LISANSSIZ_SERILER`): Fed,
     ECB, Eurostat, TCMB, EIA kamu kurumu ve kisitlama yok. OECD
     ayri bir durum ve emin olunamadi.

Bundesbank ikisini de cozuyor: tahvili IHRAC EDEN ulkenin merkez
bankasi, yani BIRINCIL KAYNAK, ve seri GUNLUK. Olculdu (2026-10-29):
7.419 gozlem (1997-08-07'den bugune), son gozlem 2026-10-28 = %3,40
-- ECB kuruyla ayni gun.

SAYI DUZELTILDI: ilk olcumde "10.681 gozlem" yazilmisti; o HAM SATIR
sayisiydi ve tatil gunlerinin bos degerlerini de iceriyordu.
Ayristirici onlari atliyor, geriye 7.419 gercek gozlem kaliyor.

Ayni tercih bu depoda daha once de yapildi: politika faizi EVDS'nin
dolayli serisinden degil TCMB'nin KENDI duyurusundan okunuyor
(bkz. `politika_faizi.py`).

YENI BAGIMLILIK YOK: `httpx` zaten kullaniliyor, ayristirma duz CSV.

BICIM UYARISI
-------------
Uc, basligi ve ustverisi olan bir CSV donduruyor; veri satirlari
`YYYY-MM-DD,deger,bayrak` bicimde. Ustveri satirlari ("Decimals,2,"
gibi) de virgul tasiyor, yani "virgulle ayir ve ikinciyi al" diyen
bir ayristirici ustveriyi VERI sanar. Satir, TARIH BICIMIYLE
suzuluyor; ayrica eksik gozlemler bos deger tasiyor ve atlaniyor.
"""

from __future__ import annotations

import re

import httpx

# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan adres
# 20 dosyada suruklendi.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan

#: Bundesbank BBSIS serisi: listelenmis federal menkul kiymetlerin
#: faiz yapisindan turetilen getiri, kalan vade 10,0 yil.
SERI = "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"
UC = ("https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
      + SERI + "?format=csv&lang=en")

BASLIKLAR = {"User-Agent": ajan("tahvil getirisi")}
ZAMAN_ASIMI = 30.0

#: Depoya yazilan seri kodu. `graf_tohum` icindeki DE10Y varligi
#: `seri_kodu` olarak bunu tasiyor.
KOD = "BBK_DE10Y"
AD = "Almanya 10 yıllık tahvil getirisi"
BIRIM = "%"
KAYNAK = "Deutsche Bundesbank"

#: Veri satiri AYIRT EDICISI: satir bir ISO tarihle BASLAMALI.
#: Ustveri satirlari da virgul tasidigi icin alan sayisina bakmak
#: yetmiyor.
_TARIH = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def coz(csv_metni: str) -> list[tuple[str, float]]:
    """CSV'yi (tarih, getiri) listesine cevirir. Eskiden yeniye."""
    cikti: list[tuple[str, float]] = []
    for satir in csv_metni.splitlines():
        parca = satir.split(",")
        if len(parca) < 2:
            continue
        tarih = parca[0].strip().strip('"').lstrip("\ufeff")
        if not _TARIH.match(tarih):
            continue
        ham = parca[1].strip().strip('"')
        if not ham:
            # Tatil ya da eksik gozlem -- sifir DEGIL, veri yok.
            #
            # ESDEGER MUTANT UYARISI: bu satir asagidaki
            # `except ValueError` ile AYNI sonucu veriyor --
            # `float('')` zaten firlatiyor. Olculdu
            # (2026-10-29): denetim devre disi birakildiginda
            # `coz()` BIREBIR ayni listeyi donduruyor.
            #
            # Yani `test_bundesbank.py` bu mutasyonu
            # yakalamiyor ve bu bir sinama BOSLUGU DEGIL;
            # mutant davranisi degistirmiyor. Satir
            # NIYETI yazdigi icin duruyor: eksik gozlem
            # atlanmali, kazara 0.0 olarak yazilmamali.
            continue
        try:
            cikti.append((tarih, float(ham)))
        except ValueError:
            continue
    return cikti


def cek(istemci=None) -> list[tuple[str, float]]:
    """Bundesbank'tan butun seriyi ceker."""
    al = (istemci or httpx).get
    r = al(UC, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    return coz(r.text)


def depoya_yaz(b, kayitlar: list[tuple[str, float]],
               son_n: int = 260) -> int:
    """Gosterge tablosuna yazar. `INSERT OR IGNORE` -- tekrar zararsiz.

    `son_n`: 260 islem gunu bir yil demek. Derin cekmenin ek maliyeti
    yok (uc seriyi butun halinde donduruyor) ama depoya her kosuda
    10.681 satir yazmaya calismanin da anlami yok.
    """
    if not kayitlar:
        return 0
    n = 0
    for tarih, deger in kayitlar[-son_n:]:
        imlec = b.execute(
            "INSERT OR IGNORE INTO gosterge"
            " (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
            " VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (KOD, tarih, deger, BIRIM, AD, KAYNAK))
        n += imlec.rowcount or 0
    return n
