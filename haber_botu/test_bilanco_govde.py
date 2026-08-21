"""Bilanco govdesi YAYIMLANABILIR mi?

Bu dosyanin varlik sebebi olculmus ve PARA MALIYETI olan bir kusur:
2026-08-20 kosusunda 277 sirket `guvenlik: [YASAK] '(eksik)'` ile
atlandi. `yayinlanabilir()` yasal uyariyi METNIN ICINDE ariyor,
govde ise onu icermiyordu.

Kritik nokta: 277 model cagrisi YAPILDI, metinler URETILDI ve hepsi
atildi. Uretimden SONRA yapilan bir denetim, girdi maliyetini geri
getirmiyor. O yuzden bu kontrol artik model cagrilmadan, burada.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import guvenlik              # noqa: E402
import uret_bilanco_sayfa as u   # noqa: E402


class _D:
    """En az alanli sahte Donem."""
    hasilat = 1.0e9
    net_kar = 2.0e8
    ozkaynak = 5.0e8
    aktif_toplami = 9.0e8
    brut_kar = favok = faaliyet_kari = None
    net_borc = faaliyet_nakit_akisi = yatirim_harcamasi = None


def _govde(yorum="Hasılat arttı, faaliyet nakit akışı geriledi."):
    return u.govde_kur(
        kod="TEST", unvan="Test A.Ş.", sektor="Sanayi", donem="2026/6",
        d=_D(), oran={"net_marj": 20.0}, medyan={"net_marj": 12.0},
        n=5, yorum=yorum)


def test_govde_yayinlanabilir():
    """ASIL SINAV. 277 sirketi dusuren kontrol artik geciyor mu?"""
    tamam, bulgular = guvenlik.yayinlanabilir(_govde())
    assert tamam, [b.aciklama for b in bulgular]


def test_yasal_uyari_govdede():
    """Uyari METINDE olmali -- sablonda degil.

    Haber tarafinda uyari sayfa sablonunun altbilgisindeydi ve oradan
    geliyordu. Bilanco govdesi sifirdan kuruldugu icin o miras yoktu.
    `yayinlanabilir()` ise sabloni GORMUYOR, yalnizca metni goruyor.
    """
    assert guvenlik.yasal_uyari_var_mi(_govde())


def test_uyari_yorumdan_gelmiyor():
    """Uyari GOVDENIN kendisinden gelmeli, modelin metninden degil.

    Model bir gun uyariyi yazmayi birakirsa sayfa dusmemeli. Kontrol
    bu yuzden bos yorumla da yapiliyor.
    """
    tamam, bulgular = guvenlik.yayinlanabilir(_govde(yorum=""))
    assert tamam, [b.aciklama for b in bulgular]


def test_yorum_govdede_geciyor():
    """Yorum gercekten sayfaya giriyor mu -- uyari onu ezmesin."""
    g = _govde(yorum="Kendine özgü bir cümle.")
    assert "Kendine özgü bir cümle." in g
    assert "## Özet" in g


def test_yillik_degisim_tablosu():
    """Onceki yil VARSA degisim tablosu cikmali.

    Bu bolum olmadan sayfa yalnizca SEVIYE anlatiyordu ("hasilat 662
    milyar"). Okurun sordugu soru degisim; karsilastirma olmadan
    "artti" denemez.
    """
    class _Once(_D):
        hasilat = 5.0e8      # simdi 1.0e9 -> +%100
        net_kar = 1.0e8      # simdi 2.0e8 -> +%100
    g = u.govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026/6", _D(),
                    {"net_marj": 20.0}, {"net_marj": 12.0}, 5,
                    "Yorum.", once=_Once())
    assert "bir yıl öncesine göre" in g, g[:400]
    assert "Reel değişim" in g
    assert "%100,0" in g, g[:400]
    # TMS 29: reel oldugu SOYLENMELI, yoksa okur TUFE ile ariticak
    assert "TMS 29" in g


def test_onceki_yil_yoksa_bolum_hic_yok():
    """Bos tablo, veri oldugunu sanmaya yol acar -- hic yazilmasin."""
    g = _govde()
    assert "bir yıl öncesine göre" not in g
    assert "Reel değişim" not in g


def test_ozet_tablo_degil_cumle():
    """Meta aciklama tabloyla baslamamali.

    Olculdu: `ozet:` alanina ham tablo yaziliyordu --
    "| Kalem | Değer | | --- | ---: | | Hasılat |..." Arama
    sonucunda ve kart ozetinde gorunen metin buydu.
    """
    import yayin
    o = yayin._ozet_ayikla(_govde(yorum="Hasılat arttı, nakit düştü."))
    assert not o.startswith("|"), o
    assert "Hasılat arttı" in o, o


def test_sektor_medyani_yargisiz():
    """Medyan bir SIRALAMA, yargi degil -- govde bunu soyluyor mu?"""
    g = _govde()
    assert "değerlendirme değildir" in g


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
