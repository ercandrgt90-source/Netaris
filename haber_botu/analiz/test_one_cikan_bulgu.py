"""One cikan bulgular -- SEKTORE GORE BASTIRMA en kritik kisim.

Testlerin asil isi su celiskiyi onlemek: `sektor_okuma.py` bankada
"borclanmak bu is modelinin kendisidir" diyor. Ayni sayfada yuksek
borclulugu "dikkat gerektiren" diye yazmak, okuru kendi sayfamiz
icinde celiskiye dusururdu.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK.parent), str(_KOK.parent / "kaynak")]

import one_cikan as O    # noqa: E402


class _D:
    hasilat = 1.0e9
    brut_kar = 3.0e8
    net_kar = 2.0e8
    ozkaynak = 5.0e8
    aktif_toplami = 9.0e8
    faaliyet_nakit_akisi = 3.0e8
    yatirim_harcamasi = 1.0e8
    favok = faaliyet_kari = net_borc = None


class _Once(_D):
    hasilat = 5.0e8          # +%100
    brut_kar = 1.0e8         # marj %20 -> %30
    net_kar = 1.0e8          # +%100


def _metinler(bulgu):
    return " ".join(b.metin for b in bulgu)


def test_hasilat_ve_kar_lehte():
    lehte, _ = O.bulgular(_D(), _Once())
    m = _metinler(lehte)
    assert "Hasılat reel olarak %100,0 arttı" in m, m
    assert "Net kâr" in m


def test_marj_puan_olarak_olculuyor():
    """Marj YUZDE oldugu icin degisimi PUAN -- 'yuzdenin yuzdesi'
    okunmaz bir sayidir."""
    lehte, _ = O.bulgular(_D(), _Once())
    m = _metinler(lehte)
    assert "puan" in m and "genişledi" in m, m
    assert "%20,0 → %30,0" in m, m


def test_bankada_borc_bastiriliyor():
    """ASIL SINAV. `sektor_okuma` bankada 'borclanmak is modelinin
    kendisi' diyor; burada eksi yazmak celiski olurdu."""
    o = {"borc_ozkaynak": 4.0}
    m = {"borc_ozkaynak": 1.0}
    _l, a = O.bulgular(_D(), None, o, m, sektor="Finans")
    assert "Net borç / özkaynak" not in _metinler(a)
    # Sanayide AYNI olcum uretiliyor
    _l2, a2 = O.bulgular(_D(), None, o, m, sektor="Sanayi")
    assert "Net borç / özkaynak" in _metinler(a2)


def test_perakendede_cari_oran_bastiriliyor():
    """Negatif isletme sermayesi perakendede is modelinin ozelligi."""
    o = {"cari_oran": 0.6}
    _l, a = O.bulgular(_D(), None, o, {}, sektor="Temel tüketim")
    assert "Cari oran" not in _metinler(a)
    _l2, a2 = O.bulgular(_D(), None, o, {}, sektor="Sanayi")
    assert "Cari oran" in _metinler(a2)


def test_gyoda_nakit_ayrismasi_bastiriliyor():
    """GYO'da deger artisi nakit uretmez -- ayrisma YAPISAL."""
    class _Z(_D):
        faaliyet_nakit_akisi = 5.0e7     # net karin %25'i
    _l, a = O.bulgular(_Z(), None, {}, {}, sektor="Gayrimenkul")
    assert "ayrışıyor" not in _metinler(a)
    _l2, a2 = O.bulgular(_Z(), None, {}, {}, sektor="Sanayi")
    assert "ayrışıyor" in _metinler(a2)


def test_yatirim_asimi_NOTR():
    """Yon ATANMIYOR: buyuyen sirkette beklenen, olgun sirkette
    dikkat gerektiren. Hangisi oldugunu tablo SOYLEMIYOR."""
    class _Z(_D):
        yatirim_harcamasi = 9.0e8        # nakit akisini asiyor
    lehte, aleyhte = O.bulgular(_Z(), None, {}, {}, sektor="Sanayi")
    assert "dış kaynakla" in _metinler(aleyhte)
    assert "dış kaynakla" not in _metinler(lehte)
    hepsi = O.bulgular(_Z(), None, {}, {}, sektor="Sanayi")
    notr = [b for b in hepsi[1] if b.lehte is None]
    assert len(notr) == 1


def test_sifira_yakin_medyan_karsilastirilmiyor():
    """OLCULDU: 'Ozkaynak karliligi %4,7; sektor medyani %0,1'.

    Olcum dogru ama karsilastirma yaniltici: medyan sifira
    yaklastikca oransal sapma sonsuza gidiyor. Sifira yakin medyan,
    sektorde karsilastirilacak bir ORTA NOKTA olmadigi anlamina
    gelir; susmak buyuk bir sayi yazmaktan dogru.
    """
    l1, a1 = O.bulgular(_D(), None, {"roe": 4.7}, {"roe": 0.1}, "Sanayi")
    assert "Özkaynak kârlılığı" not in _metinler(l1 + a1)
    # Anlamli medyanda karsilastirma YAPILIYOR
    l2, a2 = O.bulgular(_D(), None, {"roe": 40.0}, {"roe": 10.0}, "Sanayi")
    assert "Özkaynak kârlılığı" in _metinler(l2 + a2)


def test_yargi_sozcugu_uretmiyor():
    """Bulgu metinlerinde DEGERLENDIRME sozcugu olmamali."""
    lehte, aleyhte = O.bulgular(
        _D(), _Once(), {"roe": 40.0, "cari_oran": 2.0,
                        "borc_ozkaynak": 0.2},
        {"roe": 10.0, "borc_ozkaynak": 1.0}, sektor="Sanayi")
    m = (_metinler(lehte) + " " + _metinler(aleyhte)).lower()
    for y in ("iyi", "kötü", "güçlü", "zayıf", "cazip", "riskli",
              "başarılı", "fırsat", "tavsiye"):
        assert y not in m, y


def test_her_bulgu_rakam_tasiyor():
    """Okur ayni sonuca KENDI ulasabilmeli -- bize inanmak zorunda
    kalmasin."""
    import re
    lehte, aleyhte = O.bulgular(
        _D(), _Once(), {"roe": 40.0, "cari_oran": 2.0},
        {"roe": 10.0}, sektor="Sanayi")
    for b in lehte + aleyhte:
        if b.lehte is None:
            continue                      # notr madde oran tasimayabilir
        assert re.search(r"\d", b.metin), b.metin


def test_bulgu_yoksa_bolum_hic_yok():
    """Bulgusuz bir baslik, BAKILIP bulunamadigini degil BAKILMADIGINI
    dusundurur."""
    class _Bos:
        hasilat = net_kar = brut_kar = ozkaynak = None
        aktif_toplami = faaliyet_nakit_akisi = None
        yatirim_harcamasi = favok = faaliyet_kari = net_borc = None
    assert O.markdown(_Bos(), None, {}, {}, "Sanayi") == []


def test_markdown_iki_grup_uretiyor():
    o = {"roe": 40.0, "cari_oran": 0.5}
    m = "\n".join(O.markdown(_D(), _Once(), o, {"roe": 10.0}, "Sanayi"))
    assert "## Öne çıkan ölçümler" in m
    assert "Şirket lehine işleyenler" in m
    assert "Dikkat gerektirenler" in m
    assert "sektöre göre değişir" in m


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
