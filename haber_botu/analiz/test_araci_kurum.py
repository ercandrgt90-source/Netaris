"""araci_kurum.py testleri.

En kritik test: **islem hacmi gelir sayilmamali.** Araci kurumun satis
gelirleri kalemi musteri adina yapilan islemlerin brut tutarini icerir;
onu hasilat gibi okumak "gelir %400 artti" turunden anlamsiz cumleler
uretir. Bu modulun var olma sebebi o hata.

Calistirma:  python analiz/test_araci_kurum.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import araci_kurum as ak  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}\n         bulunan : {bulunan!r}")


def yakin(bulunan, beklenen, aciklama: str, tolerans: float = 0.05) -> None:
    global _gecti, _kaldi
    if bulunan is not None and abs(bulunan - beklenen) <= tolerans:
        _gecti += 1
        print(f"  gecti  {aciklama} ({bulunan:.2f})")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: ~{beklenen}\n         bulunan : {bulunan}")


# Islem hacmi cok buyuk, brut kar kucuk -- araci kurumun tipik goruntusu
SIMDI = ak.Donem(
    etiket="2026/06",
    satis_gelirleri=880_000_000_000,   # islem hacmi
    brut_kar=1_240_000_000,            # gercek gelir olcusu
    faaliyet_kari=520_000_000,
    net_kar=430_000_000,
    faaliyet_giderleri=720_000_000,
    faaliyet_disi_net=60_000_000,
    aktif_toplami=14_800_000_000,
    ozkaynak=2_900_000_000,
)
ONCE = ak.Donem(
    etiket="2025/06",
    satis_gelirleri=210_000_000_000,
    brut_kar=980_000_000,
    faaliyet_kari=470_000_000,
    net_kar=390_000_000,
    faaliyet_giderleri=510_000_000,
    faaliyet_disi_net=40_000_000,
    aktif_toplami=9_100_000_000,
    ozkaynak=2_400_000_000,
)

r = ak.hesapla("Örnek Yatırım Menkul Değerler A.Ş.", "ORNK", SIMDI, ONCE)

print("\nIslem hacmi gelir sayilmiyor -- bu modulun var olma sebebi")
adlar = [b.ad for b in r.buyumeler]
esit(any("Satış" in a or "Hasılat" in a for a in adlar), False,
     "satis gelirleri BUYUME olarak uretilmedi")
esit(ak.Kalem.BRUT_KAR in adlar, True, "brut kar buyume olarak var")
yakin(r.buyume(ak.Kalem.BRUT_KAR), 26.53, "brut kar buyumesi (%26,5)")
esit(any("işlem hacmini" in n for n in r.notlar), True,
     "hacim kalemi NOT olarak aciklandi")

print("\nSanayi motoruna ait oranlar URETILMIYOR")
oran_adlari = [o.ad for o in r.oranlar]
for yasak in ("Stoklar", "Net borç", "FAVÖK", "Brüt kâr marjı"):
    esit(any(yasak in a for a in oran_adlari), False, f"{yasak!r} oranı yok")

print("\nAraci kuruma ait oranlar")
yakin(r.bul(ak.OranAdi.ROE).deger, 14.83, "ROE = net kar / ozkaynak")
yakin(r.bul(ak.OranAdi.ROE).onceki, 16.25, "onceki ROE")
yakin(r.bul(ak.OranAdi.GIDER_ORANI).deger, 58.06, "gider orani = gider / brut kar")
yakin(r.bul(ak.OranAdi.KALDIRAC).deger, 5.10, "kaldirac = aktif / ozkaynak")
yakin(r.bul(ak.OranAdi.NET_MARJ).deger, 34.68, "net marj brut kara gore")
yakin(r.bul(ak.OranAdi.FAALIYET_DISI).deger, 13.95, "faaliyet disi payi")

print("\nSinyaller")
basliklar = [s.baslik for s in r.sinyaller]
esit("Gider oranı yükseldi" in basliklar, True,
     "gider orani 52,0 -> 58,1 (+6,1 puan) yakalandi")
esit(any("Kaldıraç" in b for b in basliklar), True,
     "kaldirac 3,79x -> 5,10x yakalandi")
esit(any("Brüt kâr reel olarak küçüldü" in b for b in basliklar), False,
     "brut kar BUYUDU, kuculme sinyali uretilmedi")

print("\nSektor korumasi -- yanlis motorda sayi uretmektense hic uretme")
for sektor in (ak.Sektor.BANKA, ak.Sektor.SIGORTA, ak.Sektor.SANAYI):
    try:
        ak.hesapla("X", "X", SIMDI, ONCE, sektor=sektor)
        esit(True, False, f"{sektor.value} icin hata firlatilmadi")
    except ak.DesteklenmeyenSektor:
        esit(True, True, f"{sektor.value} reddedildi")

print("\nZarar gecisi")
zararli = ak.Donem(etiket="2026/06", brut_kar=900_000_000, net_kar=-120_000_000,
                   ozkaynak=2_400_000_000)
r2 = ak.hesapla("X", "X", zararli, ONCE)
esit(any("zararla kapandı" in s.baslik for s in r2.sinyaller), True,
     "kardan zarara gecis yakalandi")
yakin(r2.bul(ak.OranAdi.ROE).deger, -5.0,
      "negatif ROE URETILDI -- ozkaynagin %5'i eridi demek, gercek bilgi")

print("\nSifir tuzagi -- 'if x else None' bir olcumu yok sayardi")
sifir = ak.Donem(etiket="2026/06", brut_kar=900_000_000, net_kar=0.0,
                 ozkaynak=2_400_000_000, aktif_toplami=9_000_000_000)
r3 = ak.hesapla("X", "X", sifir, ONCE)
esit(r3.bul(ak.OranAdi.ROE) is not None, True, "net kar tam sifirken ROE var")
yakin(r3.bul(ak.OranAdi.ROE).deger, 0.0, "ROE %0 olarak raporlandi")

print("\n" + "=" * 62)
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
