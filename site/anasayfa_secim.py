"""Ana sayfada hangi arastirmalar gorunur -- TURE GORE DENGELI.

    butun analizler  ->  kategori kotasi  ->  ana sayfa listesi

NEDEN KOTA
----------
Olculdu: ana sayfadaki dokuz arastirmanin DOKUZU da bilancoydu ve
cogu gayrimenkul yatirim ortakligiydi. Sebep basit -- listede 144
bilanco, 3 teknik, 2 makro var; tarihe gore siralayinca bilancolar
digerlerini tamamen bastiriyor.

Sonuc, okurun gozunde sitenin YALNIZCA bilanco yayimladigi izlenimi.
Oysa makro ve teknik analizler de uretiliyor; yalnizca sayica az
olduklari icin hic gorunmuyorlar.

Cokluk, onem demek degil. Bir kategoride cok sayfa uretiliyor olmasi
o kategorinin okur icin daha onemli oldugu anlamina gelmiyor; yalnizca
o hattin daha sik kostugunu gosteriyor.

KOTA SIRALAMAYI DEGISTIRMIYOR
-----------------------------
Her kategori KENDI icinde en gunceli veriyor; kota yalnizca "her
turden en fazla kac tane" diyor. Yani secim rastgele degil, yalnizca
tek bir turun tamami kapmasi engelleniyor.

KOTASI DOLMAYAN TURUN YERI BOS KALMIYOR
---------------------------------------
Teknik analizden yalnizca ikisi varsa kalan yer bilancoya geciyor.
Aksi halde ana sayfa, uretilmemis icerik icin bos yer ayirirdi --
okur icin bir kayip, bizim icin bir tutarsizlik.
"""

from __future__ import annotations

#: kategori -> ana sayfada en fazla kac tane.
#:
#: Bilancoya 4 verildi cunku sayica en zengin ve sirket bazli
#: oldugu icin okurun aradigi sey cogu zaman orada. Digerlerine
#: 2'ser: gorunur olmalari icin yeterli, bastirmalari icin degil.
KOTA = {
    "Bilanço Analizi": 4,
    "Makro": 2,
    "Teknik Görünüm": 2,
    "Analist Yorumu": 2,
}

#: Kotasi tanimlanmamis kategoriler icin.
VARSAYILAN_KOTA = 2


def dengeli(analizler: list, sinir: int = 8) -> list:
    """Ture gore dengelenmis ana sayfa listesi.

    Sira KORUNUYOR: girdi hangi sirada geldiyse cikti da o sirada.
    Yalnizca kotasi dolmus kategoriden yeni oge alinmiyor.

    Kota tamamlanmadan `sinir`a ulasilmazsa kalan yerler ikinci
    turda dolduruluyor -- bos yer birakmak, uretilmemis icerik icin
    yer ayirmak olurdu.
    """
    sayac: dict[str, int] = {}
    secilen: list = []
    atlanan: list = []

    for a in analizler:
        if len(secilen) >= sinir:
            break
        k = getattr(a, "kategori", "") or ""
        kota = KOTA.get(k, VARSAYILAN_KOTA)
        if sayac.get(k, 0) >= kota:
            atlanan.append(a)
            continue
        sayac[k] = sayac.get(k, 0) + 1
        secilen.append(a)

    # IKINCI TUR: kota yuzunden bos kalan yerler dolduruluyor.
    for a in atlanan:
        if len(secilen) >= sinir:
            break
        secilen.append(a)

    return secilen


def dagilim(secilen: list) -> dict[str, int]:
    """Secimin kategori dagilimi -- denetim ve gunluk icin."""
    d: dict[str, int] = {}
    for a in secilen:
        k = getattr(a, "kategori", "") or "?"
        d[k] = d.get(k, 0) + 1
    return d
