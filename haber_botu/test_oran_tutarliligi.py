# -*- coding: utf-8 -*-
"""SEKTOR KIYAS ORANI ILE SAYFA ORANI AYNI HESAPTAN GELMELI.

BU DOSYA NEDEN VAR -- OLCULDU (2026-10-13)
------------------------------------------
`uret_bilanco._oranlari` sektor medyaninin ve sayfadaki kiyas
tablosunun kaynagi. Doc metni bastan beri "oranlar burada yeniden
hesaplanmiyor, `oranlar.py` ne hesapliyorsa o" diyordu. KOD ise
satir ici bolme yapiyordu ve ikisi ayni kurali TASIMIYORDU.

`oranlar._bol` boleni sifir YA DA NEGATIF ise None donuyor. Gerekce
orada yazili: "negatif ozkaynakla hesaplanan bir ozkaynak karliligi
matematiksel olarak uretilebilir ama anlamsizdir ve yorumlandiginda
yaniltir."

Satir ici hesap bu korumayi tasimadigi icin:

    net kar -100, ozkaynak -500
        _oranlari  ->  roe = +20,0        <- ZARAR EDEN SIRKET
        oranlar    ->  roe = None

Yani zarar eden bir sirket POZITIF ozkaynak karliligi ile
gosterilebiliyordu; hem kendi sayfasinda hem SEKTOR MEDYANINDA.
Negatif ozkaynak spor kuluplerinde ve agir borclu sirkette olagan
-- kurgusal bir risk degil. Sektorune yeni eklenen dort futbol
kulubu tam bu gruptadir.

NE SINANIYOR
------------
Iki tarafin AYNI sayiyi uretmesi, bir dizi sinir durumunda:
negatif/sifir bolen, tam sifir pay, eksik kalem. Sayilar
karsilastirilirken `oranlar.hesapla` raporundan okunuyor -- yani
sinama beklentisini kendi hesabindan degil OTEKI TARAFTAN aliyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "analiz")]

import oranlar                                     # noqa: E402
import uret_bilanco as U                           # noqa: E402

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


#: `_oranlari` anahtari -> `oranlar.OranAdi` karsiligi.
#: `borc_ozkaynak` yalnizca sektor kiyasinda var, raporda yok.
ESLESME = (
    ("brut_marj", oranlar.OranAdi.BRUT_MARJ),
    ("net_marj", oranlar.OranAdi.NET_MARJ),
    ("roe", oranlar.OranAdi.ROE),
    ("cari_oran", oranlar.OranAdi.CARI_ORAN),
)

DURUMLAR = (
    ("normal sirket", dict(
        hasilat=1000.0, brut_kar=200.0, net_kar=100.0, ozkaynak=500.0,
        aktif_toplami=2000.0, donen_varliklar=300.0,
        kisa_vadeli_yukumlulukler=400.0, net_borc=150.0)),
    ("NEGATIF OZKAYNAK", dict(
        hasilat=1000.0, brut_kar=200.0, net_kar=-100.0, ozkaynak=-500.0,
        aktif_toplami=2000.0, donen_varliklar=300.0,
        kisa_vadeli_yukumlulukler=400.0, net_borc=150.0)),
    ("ozkaynak TAM SIFIR", dict(
        hasilat=1000.0, brut_kar=200.0, net_kar=-100.0, ozkaynak=0.0,
        aktif_toplami=2000.0, donen_varliklar=300.0,
        kisa_vadeli_yukumlulukler=400.0)),
    ("net kar TAM SIFIR", dict(
        hasilat=1000.0, brut_kar=200.0, net_kar=0.0, ozkaynak=500.0,
        aktif_toplami=2000.0, donen_varliklar=300.0,
        kisa_vadeli_yukumlulukler=400.0)),
    ("kisa vadeli yukumluluk SIFIR", dict(
        hasilat=1000.0, brut_kar=200.0, net_kar=100.0, ozkaynak=500.0,
        aktif_toplami=2000.0, donen_varliklar=300.0,
        kisa_vadeli_yukumlulukler=0.0)),
    ("brut kar NEGATIF (futbol kulubu)", dict(
        hasilat=1000.0, brut_kar=-800.0, net_kar=-610.0, ozkaynak=200.0,
        aktif_toplami=2000.0, donen_varliklar=100.0,
        kisa_vadeli_yukumlulukler=400.0)),
    # `Donem.hasilat` zorunlu alan; "olculemedi" durumu 0,0 ile
    # temsil ediliyor ve iki taraf da onu bolen olarak REDDETMELI.
    ("hasilat SIFIR", dict(
        hasilat=0.0, brut_kar=200.0, net_kar=100.0, ozkaynak=500.0,
        aktif_toplami=2000.0)),
    ("hasilat NEGATIF", dict(
        hasilat=-50.0, brut_kar=200.0, net_kar=100.0, ozkaynak=500.0,
        aktif_toplami=2000.0)),
)

print("")
print("1. Iki hesap AYNI sayiyi uretiyor (beklenti OTEKI TARAFTAN)")
for ad, alanlar in DURUMLAR:
    d = oranlar.Donem(etiket="şimdi", **alanlar)
    rapor = oranlar.hesapla("Sirket", "KOD", d, d,
                            oranlar.EnflasyonEsasi.TMS29)
    rapordaki = {o.ad: o.deger for o in rapor.oranlar}
    bizdeki = U._oranlari(d)
    for anahtar, oran_adi in ESLESME:
        bek = rapordaki.get(oran_adi)
        bul = bizdeki.get(anahtar)
        if bek is None:
            esit(bul, None, f"{ad}: {anahtar} ikisinde de URETILMIYOR")
        else:
            esit(bul if bul is None else round(bul, 9),
                 round(bek, 9), f"{ad}: {anahtar} ayni")

print("")
print("2. Negatif ozkaynakta ROE ve borc/ozkaynak URETILMIYOR")
_d = oranlar.Donem(etiket="t", hasilat=1000.0, brut_kar=200.0,
                   net_kar=-100.0, ozkaynak=-500.0, aktif_toplami=2000.0,
                   net_borc=150.0)
_o = U._oranlari(_d)
esit("roe" in _o, False, "roe YOK (pozitif cikardi -- yanilticiydi)")
esit("borc_ozkaynak" in _o, False, "borc_ozkaynak YOK")
esit(round(_o["brut_marj"], 2), 20.0, "boleni saglam oran YINE uretiliyor")

print("")
print("3. TAM SIFIR bir olcumdur, 'olculemedi' degil")
# `oranlar._yuz` doc metni bu kurali acikca koyuyor: net kari tam
# sifir olan donemde ROE %0'dir. Kisa yol (`x * 100 if x else None`)
# bunu "olculemedi" sayardi ve skorda cok farkli sonuc verirdi.
_s = oranlar.Donem(etiket="t", hasilat=1000.0, brut_kar=200.0,
                   net_kar=0.0, ozkaynak=500.0, aktif_toplami=2000.0)
_os = U._oranlari(_s)
esit(_os.get("roe"), 0.0, "roe tam sifir olarak URETILIYOR")
esit(_os.get("net_marj"), 0.0, "net marj tam sifir olarak URETILIYOR")

print("")
print("4. Medyan da ayni korumadan geciyor")
# Sektor medyani `_oranlari` ciktilarindan kuruluyor; negatif
# ozkaynakli sirket ROE medyanina HIC girmemeli.
import sektor_ozet                                 # noqa: E402

_kume = {
    "SAGLAM1": U._oranlari(oranlar.Donem(
        etiket="t", hasilat=1000.0, brut_kar=200.0, net_kar=100.0,
        ozkaynak=500.0, aktif_toplami=2000.0)),
    "SAGLAM2": U._oranlari(oranlar.Donem(
        etiket="t", hasilat=1000.0, brut_kar=300.0, net_kar=150.0,
        ozkaynak=500.0, aktif_toplami=2000.0)),
    "SAGLAM3": U._oranlari(oranlar.Donem(
        etiket="t", hasilat=1000.0, brut_kar=250.0, net_kar=125.0,
        ozkaynak=500.0, aktif_toplami=2000.0)),
    "NEGATIF": U._oranlari(oranlar.Donem(
        etiket="t", hasilat=1000.0, brut_kar=200.0, net_kar=-100.0,
        ozkaynak=-500.0, aktif_toplami=2000.0)),
}
esit("roe" in _kume["NEGATIF"], False, "negatif ozkaynakli sirkette roe yok")
_m = sektor_ozet.sektor_medyanlari(_kume)
esit(round(_m["roe"], 4), 25.0,
     "ROE medyani yalnizca saglam ucten (20, 30, 25 -> 25)")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
