# -*- coding: utf-8 -*-
"""SESSIZ ARIZAYI DUYULUR KILAN MANTIK SINANIYOR.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-29): sitenin kurulma tempsu 38 kosu/gunden 4'e
dustu ve sebebi tanilama ucunda AYNEN yaziyordu:

    17 tetigin 17'si `yanit: 401`. Basarili: 0.

Nobetci dogru calisiyordu; GitHub jetonu reddediyordu. Ama bu bilgi
yalnizca bir ucun tamponunda duruyordu ve oraya kimse bakmiyordu.
Depodaki CI alarmi KIRMIZI KOSUYU duyuruyor -- burada kirmizi kosu
yok, kosu hic BASLAMIYOR.

`nobet_denetimi.degerlendir` o bosluga bakiyor. Bu dosya onun
kararlarini uydurma veriyle sinar: AG KULLANMAZ, yani hem CI'da hem
cevrimdisi ayni sonucu verir.

NEDEN AG KULLANILMIYOR
----------------------
Canli uca vuran bir sinama, ag kesildiginde KIRMIZI yanar ve CI'da
dusen bir sinama butun kosuyu (dolayisiyla dagitimi) durdurur. Yani
"site seyrek guncelleniyor" sorunu "site hic guncellenmiyor"a
donerdi. Ariza is akisinda DAGITIMI ENGELLEMEYEN bir adimda
duyuruluyor; burada yalnizca MANTIK tutuluyor.

NE SINANIYOR
------------
1. Hepsi basarisiz tetik -> BOZUK, ve tanisi dogru.
2. Tek bir basarili tetik -> SAGLIKLI (gecici hata alarm uretmiyor).
3. Yetersiz kanit -> BILINMIYOR, bozuk DEGIL.
4. Uca ulasilamamasi -> BILINMIYOR, bozuk DEGIL.
5. Jeton hic kurulmamis -> BOZUK.
6. Esikler bu dosyada ELLE yazili -- kodu gevsetmek kirmizi yakar.
"""

from __future__ import annotations

import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_SITE)]

import nobet_denetimi as nd  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Bu dosyanin BEKLEDIGI en az tetik sayisi. `nd.EN_AZ_TETIK`ten
#: OKUNMUYOR: korunan degeri korunan modulden almak, sabiti
#: degistiren kisinin beklentiyi de degistirmesi demek olurdu ve
#: mutasyon sessizce yesil kalirdi (ayni ders `test_besleme_payi.py`).
#:
#: KORUMA TAVAN, TABAN DEGIL. Ilk yazimda `>=` yazmistim ve yon
#: YANLISTI: bu sabiti YUKSELTMEK alarmi susturur (kanit esigi
#: erisilemez olur), dusurmek degil. Mutasyon A'yi davranissal iddia
#: yakaladi ama yanlis yonlu bir koruma zamanla curur.
BEKLENEN_EN_AZ = 3


def kayit(karar: str, yanit=None) -> dict:
    return {"an": "2026-09-29T18:00:00.000Z", "yas": 1.0,
            "karar": karar, "yanit": yanit}


def veri(kararlar, jeton=True) -> dict:
    return {"jeton_kurulu": jeton, "icerik_yasi_saat": 1.3,
            "esik_saat": 0.6, "son_kararlar": kararlar}


print("\nEsikler gevsetilmemis")
esit(nd.EN_AZ_TETIK <= BEKLENEN_EN_AZ, True,
     f"kanit esigi yukseltilip alarm susturulmamis "
     f"({nd.EN_AZ_TETIK} <= {BEKLENEN_EN_AZ})")
esit(nd.EN_AZ_TETIK >= 2, True,
     f"tek bir gecici hata alarm uretmiyor ({nd.EN_AZ_TETIK} >= 2)")
esit(204 in nd.BASARILI_YANIT, True,
     "204 basarili sayiliyor (repository_dispatch bunu doner)")
esit(401 in nd.BASARILI_YANIT, False, "401 basarili SAYILMIYOR")
esit(403 in nd.BASARILI_YANIT, False, "403 basarili SAYILMIYOR")

print("\nGercek ariza: hepsi basarisiz")
_d, _a = nd.degerlendir(veri([kayit("tetiklendi", 401)] * 17
                             + [kayit("taze")] * 3))
esit(_d, nd.DURUM_BOZUK, "17 basarisiz tetik -> BOZUK")
esit("401" in _a, True, "aciklama baskin yaniti soyluyor")
esit("iptal" in _a or "suresi" in _a, True,
     "aciklama 401'in ne demek oldugunu soyluyor (tani veriyor)")

# 403 baska bir tani vermeli -- kod ayrimi GERCEKTEN yapiyor mu.
_d3, _a3 = nd.degerlendir(veri([kayit("tetiklendi", 403)] * 5))
esit(_d3, nd.DURUM_BOZUK, "403 de BOZUK")
esit("yetki" in _a3 or "kota" in _a3, True,
     "403 icin AYRI tani veriliyor (sabit metin degil)")

print("\nGecici hata alarm uretmiyor")
_d, _a = nd.degerlendir(veri(
    [kayit("tetiklendi", 401)] * 6 + [kayit("tetiklendi", 204)]))
esit(_d, nd.DURUM_SAGLIKLI, "tek basarili tetik varsa SAGLIKLI")
esit("1/7" in _a, True, "aciklama orani veriyor")

print("\nYetersiz kanit BOZUK DEGIL")
# Bu depoda olcum araci defalarca yanlis alarm uretti. Az kanitla
# "bozuk" demek, gercek arizayi da inandiriciliktan dusururdu.
_d, _a = nd.degerlendir(veri([kayit("tetiklendi", 401)] * 2
                             + [kayit("taze")] * 10))
esit(_d, nd.DURUM_BILINMIYOR, f"{nd.EN_AZ_TETIK}'ten az tetik -> BILINMIYOR")
_d, _a = nd.degerlendir(veri([kayit("taze")] * 20))
esit(_d, nd.DURUM_BILINMIYOR, "hic tetik yoksa BILINMIYOR (site taze)")
_d, _a = nd.degerlendir(veri([]))
esit(_d, nd.DURUM_BILINMIYOR, "bos kayit -> BILINMIYOR")

print("\nUca ulasilamamasi ARIZA DEGIL")
esit(nd.degerlendir(None)[0], nd.DURUM_BILINMIYOR,
     "uc okunamadi -> BILINMIYOR (yanlis alarm uretilmiyor)")
esit(nd.degerlendir("bozuk yanit")[0], nd.DURUM_BILINMIYOR,
     "sozluk olmayan yanit -> BILINMIYOR")

print("\nJeton hic kurulmamissa BOZUK")
_d, _a = nd.degerlendir(veri([kayit("taze")] * 5, jeton=False))
esit(_d, nd.DURUM_BOZUK, "jeton kurulu degilse BOZUK (tetik beklenmiyor)")
esit("KURULMAMIS" in _a, True, "aciklama sebebi soyluyor")

print("\nKIMLIK GONDERILIYOR MU")
# Varsayilan `Python-urllib` kimligi ucta 403 aliyor. Kimlik
# gonderilmezse denetim her zaman "bilinmiyor" derdi -- yani alarm
# kurulur ama HICBIR ZAMAN calmazdi.
esit("urllib" not in nd.KIMLIK.lower(), True,
     "varsayilan kimlik kullanilmiyor")
esit(nd.KIMLIK.startswith("Netaris"), True, "kendi kimligimizi soyluyoruz")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Her duruma ayni cevabi veren bir degerlendirici bu dosyayi GECEMEZ.
_hepsi = {nd.degerlendir(veri([kayit("tetiklendi", 401)] * 5))[0],
          nd.degerlendir(veri([kayit("tetiklendi", 204)] * 5))[0],
          nd.degerlendir(None)[0]}
esit(len(_hepsi), 3, "degerlendirici UC durumu da ayirt ediyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
