"""Ana sayfa arastirma secimi -- COKLUK ONEM DEMEK DEGIL.

Olculdu: ana sayfadaki dokuz arastirmanin dokuzu da bilancoydu.
Sebep listede 144 bilanco, 3 teknik, 2 makro olmasi. Bir kategoride
cok sayfa uretiliyor olmasi o kategorinin okur icin daha onemli
oldugunu gostermiyor; yalnizca o hattin daha sik kostugunu.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import anasayfa_secim as A    # noqa: E402


class _A:
    def __init__(self, kategori, baslik=""):
        self.kategori = kategori
        self.baslik = baslik or kategori


def test_tek_tur_hepsini_kapmiyor():
    """ASIL SINAV. 144 bilanco listeyi bastirmamali."""
    liste = [_A("Bilanço Analizi", f"B{i}") for i in range(144)]
    liste += [_A("Makro", "M1"), _A("Teknik Görünüm", "T1")]
    s = A.dengeli(liste, sinir=9)
    d = A.dagilim(s)
    # ASIL OLCUT: az sayidaki turler GORUNUYOR mu.
    #
    # Bilanconun yedi tane cikmasi bir kusur DEGIL: gosterilecek
    # baska sey yok, ikinci tur bos yerleri dolduruyor. Kotanin isi
    # bilancoyu kisitlamak degil, digerlerine YER ACMAK.
    assert "Makro" in d, d
    assert "Teknik Görünüm" in d, d

    # Yeterli cesitlilik VARSA kota gercekten kisitliyor.
    bol = [_A("Bilanço Analizi", f"B{i}") for i in range(144)]
    bol += [_A("Makro", f"M{i}") for i in range(5)]
    bol += [_A("Teknik Görünüm", f"T{i}") for i in range(5)]
    # sinir=8: kota toplami (4+2+2) tam doluyor, ikinci tur
    # devreye girmiyor. sinir=9 olsaydi bir fazla yer ikinci
    # turdan dolar ve saf kota davranisi olculemezdi.
    d2 = A.dagilim(A.dengeli(bol, sinir=8))
    assert d2["Bilanço Analizi"] == 4, d2
    assert d2["Makro"] == 2, d2
    assert d2["Teknik Görünüm"] == 2, d2


def test_sira_korunuyor():
    """Kota SIRALAMAYI degistirmiyor; her tur kendi icinde en gunceli
    veriyor. Sira bozulsaydi secim rastgele gorunurdu."""
    liste = [_A("Makro", "M1"), _A("Makro", "M2"), _A("Makro", "M3")]
    s = A.dengeli(liste, sinir=3)
    assert [x.baslik for x in s] == ["M1", "M2", "M3"]


def test_bos_yer_birakmiyor():
    """Kotasi dolmayan turun yeri BOS KALMAMALI.

    Teknik analizden yalnizca ikisi varsa kalan yer bilancoya
    geciyor. Aksi halde ana sayfa URETILMEMIS icerik icin yer
    ayirirdi -- okur icin kayip, bizim icin tutarsizlik.
    """
    liste = [_A("Bilanço Analizi", f"B{i}") for i in range(20)]
    s = A.dengeli(liste, sinir=8)
    assert len(s) == 8, len(s)


def test_sinira_uyuyor():
    liste = [_A("Bilanço Analizi", f"B{i}") for i in range(50)]
    assert len(A.dengeli(liste, sinir=5)) == 5
    assert len(A.dengeli(liste, sinir=0)) == 0


def test_az_icerikte_cokmuyor():
    """Tek analiz varsa da calismali -- ilk gunlerin durumu."""
    assert len(A.dengeli([_A("Makro")], sinir=9)) == 1
    assert A.dengeli([], sinir=9) == []


def test_bilinmeyen_kategori_varsayilan_kota():
    """Yeni bir kategori eklendiginde sinirsiz akmamali."""
    liste = [_A("Yepyeni Tür", f"Y{i}") for i in range(10)]
    liste += [_A("Makro", "M1")]
    s = A.dengeli(liste, sinir=4)
    d = A.dagilim(s)
    assert "Makro" in d, d


def test_gercek_veriyle_denge():
    """Asil depo: tek tur hepsini kapmamali."""
    import insa                                        # noqa: PLC0415
    s = A.dengeli(A and insa.guncel_olanlar(insa.analizleri_yukle()),
                  sinir=9)
    d = A.dagilim(s)
    assert len(d) >= 3, d          # en az uc farkli tur gorunuyor
    assert max(d.values()) <= 5, d


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
