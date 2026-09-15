"""KOSUNUN COZECEGI ILE COZEMEYECEGI AYRI RAPORLANMALI.

BU DOSYA NEDEN VAR
------------------
`kumulatif_temizle` ve `denetim` karsiligi olmayan her kumulatif
sayfa icin "bilanco uretim kosusu gerekiyor" diyordu.

Olculdu (2026-09-15): bekleyen 29 sayfanin 1'i (TERA) sirket
defterinde `sektor_tr` TASIMIYOR. `uret_bilanco.py --hepsi` sektor
listesini o alandan kuruyor ve sirketleri sektor sektor geziyor;
alani olmayan sirket hicbir sektore dusmuyor. Yani kac kosu
kosulursa kosulsun ceyrekligi URETILMEYECEK.

Defterde 794 sirketin 441'inde bu alan yok -- cogu icin dogru ve
kasitli (fon, varant, yatirim ortakligi). Ama arada KUMULATIF SAYFASI
olan biri varsa, o sayfa sonsuza kadar bekleyen sayiliyordu.

Yanlis tavsiye yanlis sayidan pahali: kosuyu tekrarlayan biri sonucun
degismedigini gorur ve bir sure sonra satiri hic okumaz. Hic
kapanmayan bir uyari, yanindaki GERCEK uyariyi da goturur.

NE SINANIYOR
------------
1. `uretilebilir_kodlar` yalnizca `sektor_tr` TASIYANLARI veriyor.
2. Ayrim dogru: sektorlu -> bekleyen, sektorsuz -> oksuz.
3. Defter okunamazsa OKSUZ DENMIYOR -- "bilmiyorum" ile "uretilemez"
   ayni sey degil.
4. Ayrim TEK YERDE: `denetim` kendi kopyasini tutmuyor, bu islevi
   cagiriyor.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import kumulatif_temizle as kt   # noqa: E402


def _defter(kayitlar: dict) -> pathlib.Path:
    p = pathlib.Path(tempfile.mkdtemp()) / "sirketler.json"
    p.write_text(json.dumps({"sirketler": kayitlar}), encoding="utf-8")
    return p


def test_yalnizca_sektorlu_kodlar_uretilebilir():
    y = _defter({
        "AAA": {"kod": "AAA", "sektor_tr": "Sanayi"},
        "BBB": {"kod": "BBB"},                       # sektorsuz
        "CCC": {"kod": "CCC", "sektor_tr": ""},      # bos = yok
    })
    assert kt.uretilebilir_kodlar(y) == {"AAA"}


def test_ayrim_dogru():
    bekleyen, oksuz = kt.bekleyen_ve_oksuz(["AAA", "BBB"], {"AAA"})
    assert bekleyen == ["AAA"]
    assert oksuz == ["BBB"]


def test_kucuk_harfli_kod_da_eslesiyor():
    """Sayfa adlari kucuk harfli; defter buyuk harfli."""
    bekleyen, oksuz = kt.bekleyen_ve_oksuz(["aaa"], {"AAA"})
    assert bekleyen == ["aaa"], (bekleyen, oksuz)
    assert oksuz == []


def test_defter_bilinmiyorsa_oksuz_denmiyor():
    """"Bilmiyorum" ile "uretilemez" AYNI SEY DEGIL.

    Defter okunamadiginda bos kume donmek, butun bekleyenleri oksuz
    damgalardi -- yani bir okuma hatasi, calisan onlarca sirketi
    "kosu cozmez" diye bildirirdi.
    """
    bekleyen, oksuz = kt.bekleyen_ve_oksuz(["AAA", "BBB"], None)
    assert bekleyen == ["AAA", "BBB"]
    assert oksuz == []


def test_denetim_kendi_kopyasini_tutmuyor():
    """Ayrim TEK YERDE.

    Ilk yazimda ayni ayrim iki yerde duruyordu. Bu depoda en sik
    tekrarlayan kusur sinifi tam bu: ayni karari veren iki kod yolu,
    birinin degisip otekinin degismemesi demek.
    """
    d = (_KOK / "denetim.py").read_text(encoding="utf-8")
    assert "_kt.bekleyen_ve_oksuz(kalan, _uretilebilir)" in d
    # Kopya kalmadi: kendi liste kavramasini yapmiyor.
    assert "k.upper() not in _uretilebilir" not in d


def test_denetim_iki_ayri_bulgu_uretiyor():
    """Gercek depoda: bekleyen ve oksuz AYRI satirlar."""
    import denetim
    b = denetim._kumulatif_bilanco_denetimi()
    metin = " | ".join(x.mesaj for x in b)
    if not b:
        return                              # goc bitmis: iddia yok
    # Hangi satir varsa DOGRU tavsiyeyi vermeli.
    for x in b:
        assert x.agirlik == "bilgi", x.agirlik
        if "OKSUZ" in x.mesaj:
            assert "COZMEZ" in x.mesaj, metin
        else:
            assert "uretim kosusu gerekiyor" in x.mesaj, metin


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
