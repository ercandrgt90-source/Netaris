"""TCMB politika faizi -- kurumun KENDI duyurusundan okunur.

NEDEN AYRI BIR MODUL
--------------------
Panelde "Politika faizi %40,00" yaziyordu; gercek politika faizi %37
idi. Deger TP.APIFON4'ten, yani agirlikli ortalama FONLAMA
MALIYETINDEN geliyordu -- ayri bir buyukluk ve sapabiliyor.

Dogru seri arandi: EVDS'de politika faizi icin calisan bir kod
bulunamadi (TP.APIFON1..12, TP.FE.OKTG01, TP.PY.P01 denendi; hepsi bos
donuyor). EVDS'nin ust veri ucu ise tek sayfalik bir uygulamaya
dusuyor ve onun ic API'si kurcalanmiyor.

AMA GEREK DE YOK: politika faizi olculen bir seri degil, ILAN EDILEN
bir karar. TCMB onu PPK sonrasi basin duyurusunda yaziyor ve o duyuru
zaten bizim besleme listemizde:

    "Para Politikasi Kurulu, politika faizi olan bir hafta vadeli repo
     ihale faiz oraninin yuzde 37'de sabit tutulmasina karar
     vermistir."

Birincil kaynak, makine okunur, kendi hattimizda. Sayi ELLE
YAZILMIYOR: her PPK duyurusunda yeniden okunuyor.

SAYIYI ELLE YAZMAK NEDEN OLMAZDI
--------------------------------
Bir kez dogru yazilir, sonra PPK toplanir ve sayi sessizce yanlis olur.
Sitede "bugunku gorunum" diye durur. Tam da duzeltmeye calistigimiz
hata sinifi -- sayi dogru gorunur, anlami yanlistir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

BASLIKLAR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
}
ZAMAN_ASIMI = 30.0

#: Bizim seri kodumuz. `gosterge` tablosuna bu adla yaziliyor.
KOD = "TCMB_POLITIKA"
AD = "Politika faizi"

#: PPK duyurusunun basligi. Besleme bunu zaten cekiyor.
DUYURU_KALIBI = "Faiz Oranlarına İlişkin"

#: Politika faizi cumlesi. Duyuru metni kalipli:
#:
#:   "politika faizi olan bir hafta vadeli repo ihale faiz oraninin
#:    yuzde 37'de sabit tutulmasina karar vermistir"
#:   "... yuzde 39,5'ten yuzde 38'e indirilmesine ..."
#:
#: Cumlede birden fazla "yuzde N" olabilir; DEGISIKLIKTE ikisi var ve
#: YENI oran IKINCISIDIR. Bu yuzden cumlenin tamami alinip icindeki
#: son deger okunuyor -- ilkini almak, faiz degistiginde ESKI orani
#: yayimlamak olurdu.
_CUMLE = re.compile(
    r"politika faizi[^.]{0,200}?(?:repo ihale faiz oran|faiz oran)[^.]{0,200}?\.",
    re.I)
_YUZDE = re.compile(r"yüzde\s*(\d{1,3}(?:[,.]\d{1,2})?)", re.I)

#: Makul sinir. Disina cikan bir okuma AYRISTIRMA HATASIDIR, veri degil.
#: Duyuruda baska yuzdeler de geciyor ("enflasyon yuzde 5 hedefi") ve
#: yanlis cumleye takilirsak sinir bunu yakalar.
EN_AZ, EN_COK = 1.0, 100.0


@dataclass(frozen=True)
class Karar:
    oran: float
    tarih: str          # duyuru tarihi (ISO)
    adres: str          # kaynak baglantisi
    cumle: str          # okunan cumle -- denetim ve seffaflik icin


def _metin(html: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html)
    # Turkce tirnak ve kesme isaretleri normalize: "37’de" ile "37'de"
    # ayni sey ve desen ikisini de gormeli.
    t = t.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", t)


def coz(html: str) -> tuple[float | None, str]:
    """Duyuru sayfasindan politika faizini okur. (oran, cumle).

    Okunamazsa (None, ""). UYDURMA YOK: kalip tutmazsa bos donuyor ve
    cagiran taraf eski degeri koruyor.
    """
    t = _metin(html)
    m = _CUMLE.search(t)
    if not m:
        return None, ""
    cumle = m.group(0).strip()
    degerler = _YUZDE.findall(cumle)
    if not degerler:
        return None, ""
    try:
        oran = float(degerler[-1].replace(",", "."))
    except ValueError:
        return None, ""
    if not (EN_AZ <= oran <= EN_COK):
        # Sinir disi okuma = yanlis cumleye takildik. Yanlis sayiyi
        # yayimlamaktansa hic yayimlamamak.
        return None, cumle
    return oran, cumle


def son_karar(b, istemci: httpx.Client | None = None) -> Karar | None:
    """Depodaki en yeni PPK duyurusunu bulur ve oranini okur.

    `b` acik bir depo baglantisi. Duyuru depoda yoksa (besleme henuz
    cekmemisse) None -- bu bir hata degil, yalnizca "elimizde yok".
    """
    try:
        r = b.execute(
            "SELECT adres, tarih FROM haber"
            " WHERE baslik_tr LIKE ? AND adres LIKE '%tcmb.gov.tr%'"
            " ORDER BY tarih DESC LIMIT 1",
            (DUYURU_KALIBI + "%",)).fetchone()
    except Exception:
        return None
    if not r:
        return None

    adres, tarih = r[0], r[1]
    kapat = istemci is None
    c = istemci or httpx.Client(timeout=ZAMAN_ASIMI, follow_redirects=True,
                                headers=BASLIKLAR)
    try:
        y = c.get(adres)
        y.raise_for_status()
    except httpx.HTTPError:
        return None
    finally:
        if kapat:
            c.close()

    oran, cumle = coz(y.text)
    if oran is None:
        return None
    return Karar(oran=oran, tarih=tarih, adres=adres, cumle=cumle)


#: TCMB PPK duyuru beslemesi. `besleme.BESLEMELER` icinde de var ama
#: burada dogrudan kullaniliyor: gecmis kurmak icin haber hattinin
#: pencere sinirlarina takilmak istemiyoruz.
PPK_BESLEME = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR"
               "/Bottom+Menu/Diger/RSS/PPK+Kararlari")


def gecmis(b, en_cok: int = 24) -> list[Karar]:
    """PPK beslemesindeki duyurulari okuyup faiz gecmisini kurar.

    NEDEN GEREKLI: panel bir gostergeyi basmak icin EN AZ IKI gozlem
    istiyor -- degisimi gostermek icin. Tek karar yazildiginda
    "Politika faizi" satiri panelde HIC gorunmuyordu.

    YALNIZCA EKSIK OLANLAR CEKILIYOR. Duyuru sayfalari TCMB'den tek tek
    aliniyor; depoda tarihi zaten olan duyuru icin istek YAPILMIYOR.
    Boylece ilk calistirma gecmisi kuruyor, sonrakiler yalnizca yeni
    karari okuyor.
    """
    try:
        var = {r[0] for r in b.execute(
            "SELECT tarih FROM gosterge WHERE kod=?", (KOD,))}
    except Exception:
        var = set()

    try:
        import besleme
    except ImportError:
        return []

    with httpx.Client(timeout=ZAMAN_ASIMI, follow_redirects=True,
                      headers=BASLIKLAR) as c:
        try:
            y = c.get(PPK_BESLEME)
            y.raise_for_status()
        except httpx.HTTPError:
            return []

        cikti: list[Karar] = []
        for o in besleme._ogeler(y.text)[:en_cok]:
            tarih = (o.get("tarih") or "")[:10]
            if not tarih or tarih in var:
                continue
            if DUYURU_KALIBI not in (o.get("baslik") or ""):
                continue
            try:
                d = c.get(o["adres"])
                d.raise_for_status()
            except httpx.HTTPError:
                continue
            oran, cumle = coz(d.text)
            if oran is None:
                continue
            cikti.append(Karar(oran=oran, tarih=tarih, adres=o["adres"],
                               cumle=cumle))
    return cikti
