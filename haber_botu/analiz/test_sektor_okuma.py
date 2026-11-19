"""Sektor okuma kilavuzu -- kapsam ve DIL denetimi.

Bu bloklar OKUMA KILAVUZU, yorum degil. Testlerin isi tam olarak bu
ayrimi korumak: kilavuz "bu kalem ne anlama gelir" der, "bu sirket
iyidir" demez.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import sektor_okuma as S    # noqa: E402

#: Hangi ASAMADA kosuyoruz. Bayragi `site/cikti_sinamalari.py`
#: kuruyor -- asamayi BILEN tek yer orasi.
_URETIM_SONRASI = os.environ.get("NETARIS_URETIM_SONRASI") == "1"

#: Degerlendirme sozcukleri -- kilavuzda BULUNMAMALI.
#:
#: Ayni liste `bilanco_yorum.SISTEM` icinde modele de yasak. Kural
#: modelde varken kodda olmamasi tutarsizlik olurdu: okur metnin
#: hangisinden geldigini bilmiyor.
YARGI = ("cazip", "başarılı", "güçlü şirket", "kötü", "riskli",
         "fırsat", "ucuz", "pahalı", "tavsiye", "önerilir")

#: Gelecege donuk ifadeler -- kilavuz TANIMLAR, ONGORMEZ.
ONGORU = ("yükselecek", "düşecek", "artacak", "azalacak", "beklenir",
          "olacaktır")


def _metinler():
    for sektor, (baslik, paragraflar) in S.OKUMA.items():
        yield sektor, baslik, " ".join(paragraflar)


def test_yargi_sozcugu_yok():
    for sektor, _b, metin in _metinler():
        d = metin.lower()
        for y in YARGI:
            assert y not in d, f"{sektor}: '{y}'"


def test_ongoru_yok():
    for sektor, _b, metin in _metinler():
        d = metin.lower()
        for y in ONGORU:
            assert y not in d, f"{sektor}: '{y}'"


def test_sayi_yok():
    """Kilavuzda OLCUM olmamali.

    Olcumler tablodan geliyor ve donemle degisiyor; kilavuz ise
    sabit. Icine bir rakam yazilirsa bir sonraki ceyrekte YANLIS
    olur ve kimse fark etmez -- cunku kilavuz yeniden uretilmiyor.

    Muhasebe standardi adi (TMS 29) ve oran esigi (1'in altinda)
    olcum degil, tanim.
    """
    for sektor, _b, metin in _metinler():
        temiz = metin.replace("TMS 29", "").replace("1'in", "")
        assert not re.search(r"\d[.,]\d", temiz), sektor


def test_baslik_soru_bicimde():
    """Okur hangi bolumun kendi sorusunu cevapladigini gormeli."""
    for sektor, baslik, _m in _metinler():
        assert len(baslik) > 15, sektor
        assert not baslik.endswith("."), sektor


def test_taninmayan_sektor_bos_donuyor():
    """Kilavuz yoksa bolum HIC yazilmamali.

    Yanlis bir okuma kilavuzu, kilavuzsuzluktan KOTUDUR: okur ona
    guvenip yanlis kalemi okur.
    """
    assert S.blok("Olmayan sektör") is None
    assert S.markdown("Olmayan sektör") == []
    assert S.markdown("") == []


def test_markdown_baslik_uretiyor():
    m = S.markdown("Finans")
    assert any(x.startswith("## ") for x in m)
    assert any("net faiz geliri" in x for x in m)


def test_defterdeki_sektorlerin_hepsi_kapsandi():
    """Uretilen her sektorun kilavuzu OLMALI.

    Bu test kapsamı sessizce daralmaktan koruyor: yeni bir sektor
    eklendiginde kilavuzsuz kalirsa burada goruluyor.
    """
    yol = _KOK.parent / "kaynak" / "sektor_ozet.json"
    if not yol.exists():
        return
    d = json.loads(yol.read_text(encoding="utf-8"))
    eksik = [s for s in d if S.blok(s) is None]
    if _URETIM_SONRASI:
        assert not eksik, f"kılavuzu olmayan sektör: {eksik}"
    else:
        # OLCUM, KAPI DEGIL -- OLCULDU, DORT GUN KILITLEDI.
        #
        # Bu iddia 2026-11-15 ile 11-19 arasinda otomasyonu kirmizi
        # tuttu: kaynak `Consumer Non-Cyclicals` dondurdu, ceviri
        # haritasinda yoktu, ham deger `sektor_ozet.json`a anahtar
        # olarak akti ve kilavuzu yoktu. Iddia DOGRUYDU; yeri
        # yanlisti.
        #
        # Sinamalar `calistir.py`den ONCE kosuyor; o dosyayi URETEN
        # adim (`uret_bilanco`) kapinin arkasinda. Yani depodaki eski
        # veri, kendisini duzeltecek adimi arkasinda birakip
        # kilitliyordu.
        #
        # Garanti asagidaki iki iddiada: ikisi de URETICIYE bakiyor
        # ve icerikten BAGIMSIZ, dolayisiyla veri surprizi dagitimi
        # durduramiyor. Uretim SONRASI ayni iddia KATI kosuyor
        # (`site/cikti_sinamalari.py` bu dosyayi secmiyor olabilir
        # diye degil; bkz. test_uretici_*).
        if eksik:
            print(f"   olcum: kılavuzu olmayan sektör = {eksik}")


def test_uretici_CEVIRMEDIGI_ADI_ASLA_DONDURMUYOR():
    """Haritada olmayan sektor adi HAM haliyle akmamali.

    ICERIKTEN BAGIMSIZ: kaynagin ne dondurdugune degil, `cek`in ne
    YAPTIGINA bakiyor. Bu yuzden yeni bir kaynak adi dagitimi
    durdurmuyor -- yalnizca o sirket sektorsuz kaliyor ve sebep
    raporlaniyor.
    """
    sys.path.insert(0, str(_KOK.parent / "kaynak"))
    import sektor as SK                                   # noqa: PLC0415

    sayfa = ('x infoTable:[{t:"Industry",v:"Food & Drug Retailing"},'
             '{t:"Sector",v:"Bilinmeyen Ust Sektor"}] y')

    class _Y:
        status_code = 200
        text = sayfa

        def raise_for_status(self):
            return None

    class _I:
        def get(self, *a, **k):
            return _Y()

    onceki = len(SK.OKUNAMAYAN)
    sonuc = SK.cek("XTEST", _I())
    yeni = [s for _k, s in SK.OKUNAMAYAN[onceki:]]

    assert sonuc == {}, f"cevrilmeyen ad icin kayit dondu: {sonuc}"
    assert yeni and all(SK.ceviri_yok_mu(s) for s in yeni), yeni
    assert "Bilinmeyen Ust Sektor" in yeni[0], \
        f"sebep ADI tasimali (haritaya ne eklenecegini o soyluyor): {yeni[0]}"

    # ATILLIK: ayni akis CEVRILEN bir ad icin kayit DONDURMELI.
    # Yoksa `cek` her zaman {} donuyor olabilirdi ve ustteki iddia
    # hicbir sey olcmezdi.
    _Y.text = ('x infoTable:[{t:"Industry",v:"Steel"},'
               '{t:"Sector",v:"Materials"}] y')
    iyi = SK.cek("XTEST2", _I())
    assert iyi.get("sektor_tr") == "Temel malzeme", iyi


def test_uretici_HER_CEVIRININ_KILAVUZU_VAR():
    """`SEKTOR_TR`in her Turkce degeri bir kilavuza baglanmali.

    ASIL KURAL BU. Veriye bakan iddia sonucu olcuyor; bu, kaynagi:
    haritaya yeni bir Turkce kova eklenip kilavuzu yazilmazsa
    burada goruluyor -- ve hicbir veri surprizi gerekmiyor.
    """
    sys.path.insert(0, str(_KOK.parent / "kaynak"))
    import sektor as SK                                   # noqa: PLC0415

    adlar = sorted(set(SK.SEKTOR_TR.values()))
    assert len(adlar) >= 10, f"atillik: yalnizca {len(adlar)} ad"
    eksik = [a for a in adlar if S.blok(a) is None]
    assert not eksik, f"ceviri var, kılavuz yok: {eksik}"


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
