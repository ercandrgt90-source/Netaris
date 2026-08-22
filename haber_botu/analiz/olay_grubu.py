"""Olay GRUBU -- ayni gelismeye ait haberleri tek sayfada toplar.

NEDEN MEVCUT `olay` TABLOSU YETMIYOR
------------------------------------
Depoda 102 olay var ve 101 farkli habere bagli: yani 1'e 1. Her haber
kendi "olayini" yaratiyor. Sebep `olay.Olay.anahtar`: baslik
govdelerinin karmasi. Ayni gelismeyi anlatan iki haberin basligi biraz
farkliysa iki ayri anahtar cikiyor.

O anahtar KENDI isini dogru yapiyor -- amaci "ayni yaziyi iki kez
uretme". Gruplama baska bir soru ve daha KABA bir kimlik istiyor.

KIMLIK: ULKE + TUR + DONEM
--------------------------
    US:faiz:2026-08     Fed'in Agustos'taki faiz gundemi
    TR:enflasyon:2026-08 TUIK/TCMB enflasyon aciklamasi

Olculdu: 16 grup olusuyor, 7'si uc ve daha fazla haber tasiyor. Daha
ince bir kimlik (gun bazli) gruplari dagitiyor; daha kaba bir kimlik
(yil bazli) alakasiz gelismeleri birlestiriyor.

ULKE NEDEN SART
---------------
Ilk denememde ulke yoktu ve "faiz:2026-08" grubunda Fed, TCMB, BoJ ve
Brezilya haberleri BIRLIKTE duruyordu. Faiz kararlari ulkeye gore
ayrilmazsa grup "faiz haberleri" cop kutusuna donuyor.

Ayni olcum sirasinda `baglam.haber_ulkesi`de bir hata da bulundu:
"Brezilya merkez bankasi" TR sayiliyordu. Duzeltilmesi gruplamayi
duzeltmekle kalmadi, baglam denetiminde iki gercek ihlal daha
gorunur oldu.

ESIK NEDEN UC
-------------
Iki haberlik bir "olay sayfasi" okura yeni bir sey vermiyor -- zaten
ikisini de akista goruyor. Uc ve ustu, dagilmis bir gelismeyi
toparlamanin degerli oldugu yer.
"""

from __future__ import annotations

import collections
import pathlib
import sqlite3
import sys

_KOK = pathlib.Path(__file__).resolve().parent
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))
if str(_KOK.parent / "kaynak") not in sys.path:
    sys.path.insert(0, str(_KOK.parent / "kaynak"))

import baglam as _baglam        # noqa: E402
import olay as _olay            # noqa: E402

DEPO = _KOK.parent / "netaris.db"

#: Bir grup en az kac haber tasimali. Bkz. modul bas yorumu.
EN_AZ_HABER = 3

#: Olay turu -> okunur ad. Grup basliginda kullaniliyor.
TUR_ADI = {
    "faiz": "faiz kararı",
    "enflasyon": "enflasyon",
    "istihdam": "istihdam",
    "kur": "kur",
    "jeopolitik": "jeopolitik gelişmeler",
}

#: Ulke kodu -> okunur ad.
ULKE_ADI = {
    "US": "ABD", "EU": "Avro Bölgesi", "TR": "Türkiye", "JP": "Japonya",
    "GB": "İngiltere", "BR": "Brezilya", "RU": "Rusya", "CN": "Çin",
    "IN": "Hindistan", "KR": "Güney Kore", "CA": "Kanada",
    "AU": "Avustralya", "CH": "İsviçre", "SE": "İsveç", "NO": "Norveç",
    "MX": "Meksika", "AR": "Arjantin", "ZA": "Güney Afrika",
    "ID": "Endonezya", "SA": "Suudi Arabistan", "IL": "İsrail",
    "EG": "Mısır", "PL": "Polonya", "HU": "Macaristan", "CZ": "Çekya",
}

_AY = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
       "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def kimlik(baslik: str, kurum: str, tarih: str,
           bolge: str = "") -> str | None:
    """Haberin ait oldugu olay grubunun kimligi. Belirlenemezse None.

    Uc parcanin UCU DE gerekli: biri eksikse haber gruplanmiyor.
    Eksik parcayla gruplamak, yanlis gruba koymak demek.
    """
    o = _olay.siniflandir(baslik, kurum or "")
    if not o:
        return None
    u = _baglam.haber_ulkesi(baslik, kurum or "", bolge)
    if not u:
        return None
    ay = (tarih or "")[:7]
    if len(ay) != 7:
        return None
    return f"{u}:{o.tur}:{ay}"


def grup_basligi(anahtar: str) -> str:
    """"US:faiz:2026-08" -> "ABD faiz kararı — Ağustos 2026" """
    try:
        u, tur, ay = anahtar.split(":")
        yil, a = ay.split("-")
        return (f"{ULKE_ADI.get(u, u)} {TUR_ADI.get(tur, tur)} — "
                f"{_AY[int(a) - 1]} {yil}")
    except (ValueError, IndexError, KeyError):
        return anahtar


def gruplar(b: sqlite3.Connection,
            en_az: int = EN_AZ_HABER) -> dict[str, list[dict]]:
    """Yayimlanmis haberleri olay gruplarina dagitir.

    Yalnizca `en_az` esigini gecen gruplar donuyor; kalanlar bir olay
    sayfasini hak etmiyor (bkz. modul bas yorumu).
    """
    kova: dict[str, list[dict]] = collections.defaultdict(list)
    r = b.execute(
        """SELECT COALESCE(baslik_tr, baslik_kaynak) AS b,
                  baslik_kaynak, tarih, kurum, yayin_yolu, adres
             FROM haber
            WHERE yayimlandi = 1 AND yayin_yolu IS NOT NULL
            ORDER BY tarih DESC""").fetchall()
    for gorunen, ozgun, tarih, kurum, yol, adres in r:
        k = kimlik(ozgun or gorunen, kurum, tarih)
        if not k:
            continue
        kova[k].append({
            "baslik": gorunen,
            "tarih": tarih,
            "kurum": kurum,
            "yol": yol,
            "adres": adres,
        })
    return {a: v for a, v in kova.items() if len(v) >= en_az}


def listeden(haberler: list[dict],
             en_az: int = EN_AZ_HABER) -> dict[str, list[dict]]:
    """Gruplari BELLEKTEKI listeden kurar -- depoya gitmeden.

    NEDEN GEREKLI
    `gruplar()` depodan `yayimlandi=1` okuyor ve o bayrak ancak yayim
    dongusu bitince yaziliyor. Ama haber sayfalari O DONGU ICINDE
    uretiliyor: sayfaya "bu olayin 9 haberinden biri" baglantisi
    koymak icin gruplar sayfalardan ONCE bilinmeli.

    Depodan okumaya calisinca sira problemi cikiyordu: olay sayfalari
    haber sayfalarindan sonra uretiliyor, dolayisiyla harita haber
    sablonuna yetismiyor. Ayni veriden bellekte gruplamak sirayi
    tamamen ortadan kaldiriyor.

    Beklenen anahtarlar: baslik, baslik_kaynak, tarih, kurum, yol,
    adres.
    """
    kova: dict[str, list[dict]] = collections.defaultdict(list)
    for h in haberler:
        if not h.get("yol") or not h.get("adres"):
            continue
        ozgun = h.get("baslik_kaynak") or h.get("baslik") or ""
        k = kimlik(ozgun, h.get("kurum", ""), h.get("tarih", ""),
                   h.get("bolge", ""))
        if not k:
            continue
        kova[k].append({
            "baslik": h.get("baslik", ""),
            "tarih": h.get("tarih", ""),
            "kurum": h.get("kurum", ""),
            "yol": h["yol"],
            "adres": h["adres"],
        })
    return {a: v for a, v in kova.items() if len(v) >= en_az}
