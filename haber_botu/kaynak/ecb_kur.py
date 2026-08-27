"""ECB gunluk referans kurlari -- ucretsiz, anahtarsiz, resmi.

    eurofxref-hist-90d.xml -> (tarih, kur) -> gosterge tablosu

NEDEN GEREKLI
-------------
Serit kur kalemlerini FRED'in `DEXUSEU` serisinden aliyordu ve o seri
olculdugunde ALTI IS GUNU geride geliyordu (2026-07-31, o gun
2026-08-10'du). Bir "fiyat seridi"nde alti is gunluk kur, fiyat degil
arsiv demektir.

ECB kendi referans kurunu HER IS GUNU 16:00 CET'te yayimliyor; ayni
olcumde son tarih 2026-08-07, yani en son is gunu. Kaynak resmi,
anahtar istemiyor ve ticari kullanima acik.

TRY ICIN KULLANILMIYOR
----------------------
ECB euro bazli yayimliyor ve TRY'yi de veriyor, ama Turk okur icin
kaynak TCMB olmali: `TP.DK.USD.S.YTL` zaten EVDS hattindan AYNI GUN
geliyor ve resmi alis/satis kuru odur. ECB'nin TRY capraz kuru ikinci
bir dogruluk kaynagi olurdu ve iki kaynak arasindaki kucuk farklar
sayfada aciklanamaz.

BICIM UYARISI
-------------
`eurofxref-daily.xml` oznitelikleri TEK tirnakla, `-hist-90d.xml` CIFT
tirnakla yaziyor. Regex ile ayristirmak bu yuzden guvenilmez -- ilk
denemede 90 gunluk dosyadan SIFIR kayit okundu ve hicbir hata
firlamadi. XML ayristiricisi kullaniliyor.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

UC = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {"User-Agent": ajan("kur verisi")}
ZAMAN_ASIMI = 30.0

#: ECB'nin ad alani. `Cube` etiketleri bunun altinda.
_AD_ALANI = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"

#: Depoya yazilan seri. FRED'in `DEXUSEU` kodundan AYRI tutuluyor:
#: ikisi ayni buyuklugu olcuyor ama farkli kaynak ve farkli tarih
#: tasiyor; tek koda yazmak hangi degerin nereden geldigini
#: kaybettirirdi.
KOD = "ECB_EURUSD"
AD = "EUR/USD"


def coz(xml_metni: str, para: str = "USD") -> list[tuple[str, float]]:
    """XML'i (tarih, kur) listesine cevirir. Yeniden eskiye sirali."""
    kok = ET.fromstring(xml_metni)
    cikti: list[tuple[str, float]] = []
    for gun in kok.iter(_AD_ALANI):
        tarih = gun.get("time")
        if not tarih:
            continue
        for kalem in gun:
            if kalem.get("currency") == para:
                try:
                    cikti.append((tarih, float(kalem.get("rate", ""))))
                except ValueError:
                    pass
                break
    return cikti


def cek(istemci=None, para: str = "USD") -> list[tuple[str, float]]:
    """ECB'den son 90 gunun kurunu ceker."""
    al = (istemci or httpx).get
    r = al(UC, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
    r.raise_for_status()
    return coz(r.text, para)


def depoya_yaz(b, kayitlar: list[tuple[str, float]]) -> int:
    """Gosterge tablosuna yazar. `INSERT OR IGNORE` -- tekrar zararsiz."""
    if not kayitlar:
        return 0
    n = 0
    for tarih, deger in kayitlar:
        imlec = b.execute(
            "INSERT OR IGNORE INTO gosterge"
            " (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
            " VALUES (?, ?, ?, '', ?, 'ECB', datetime('now'))",
            (KOD, tarih, deger, AD))
        n += imlec.rowcount or 0
    return n
