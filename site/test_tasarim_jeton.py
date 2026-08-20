"""Tasarim sayfasi gercekten AYNA mi?

Buradaki testlerin hepsi tek bir soruyu soruyor: sayfa `stil.css`i
mi anlatiyor, yoksa bir zamanlar oyle oldugunu mu? Fark, sayfanin
yardimci mi yanilticiyi mi oldugunu belirliyor.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import tasarim_jeton as tj    # noqa: E402


def test_degeri_css_belirliyor():
    """CSS'te deger degisirse sayfa da degismeli.

    ELLE YAZMAYA KARSI ASIL TEST. Uydurma bir CSS veriliyor; okuyucu
    onu okumuyorsa sonuc degismez ve test dusesr.
    """
    sahte = ":root { --p-m: 99px; --b-2: 77px; }"
    p = {j["ad"]: j["deger"]
         for o in tj.jetonlar(sahte) for j in o["jeton"]}
    assert p["--p-m"] == "99px", p
    assert p["--b-2"] == "77px", p


def test_ilk_tanim_geceriyor():
    """Sonraki tanimlar tema EZMESI; temel deger ilkidir.

    Koyu tema ayni jetonu yeniden tanimliyor. Sonuncuyu alsaydik
    sayfa acik temayi anlatirken koyu temanin degerini gosterirdi.
    """
    css = (":root { --p-m: 1rem; }\n"
           "@media (prefers-color-scheme: dark){:root{--p-m: 2rem;}}")
    p = {j["ad"]: j["deger"]
         for o in tj.jetonlar(css) for j in o["jeton"]}
    assert p["--p-m"] == "1rem", p


def test_kullanim_sayiliyor():
    """Kullanim sayisi ORNEK degil, gercekten sayiliyor."""
    css = ":root{--b-2:8px;--b-3:12px;} .a{gap:var(--b-2);} .c{padding:var(--b-2)}"
    d = {j["ad"]: j["kullanim"]
         for o in tj.jetonlar(css) for j in o["jeton"]}
    assert d["--b-2"] == 2, d
    assert d["--b-3"] == 0, d


def test_yedekli_kullanim_da_sayiliyor():
    """`var(--x, yedek)` da bir kullanimdir.

    Desen `var\\(--ad\\)` olsaydi yedekli kullanimlari KACIRIRDI ve
    sayfa kullanilan bir jetonu "kullanilmiyor" diye isaretlerdi --
    yani dogru bir jetonun silinmesini onerirdi. Bu test o daralmayi
    kapali tutuyor.
    """
    css = ":root{--b-2:8px;} .a{gap:var(--b-2, 4px);}"
    d = {j["ad"]: j["kullanim"]
         for o in tj.jetonlar(css) for j in o["jeton"]}
    assert d["--b-2"] == 1, d


def test_onek_tam_eslesiyor():
    """`--b-2` sayilirken `--b-24` sayilmamali."""
    css = ":root{--b-2:8px;--b-24:96px;} .a{gap:var(--b-24);}"
    d = {j["ad"]: j["kullanim"]
         for o in tj.jetonlar(css) for j in o["jeton"]}
    assert d["--b-2"] == 0, d
    assert d["--b-24"] == 1, d


def test_renk_olmayan_jeton_renk_sayilmiyor():
    """Punto bir renk degil; renk kutusunda gorunmemeli."""
    css = ":root{ --yazi: #111; --p-m: 1rem; --olcu: 68ch; }"
    ad = {r["ad"] for r in tj.renkler(css)}
    assert ad == {"--yazi"}, ad


def test_izgara_disi_gercekten_olculuyor():
    """Izgara disi sayaci GIZLEMIYOR.

    Sayfa kendi uyum oranini yaziyor. Sayac calismasaydi sayfa her
    zaman "sifir ihlal" derdi ve bu en kotu tur yanlis olurdu:
    olcum kiligina girmis bir temenni.
    """
    css = ".a{padding:6px;margin:16px;gap:10px;} .b{padding:2px;}"
    # 6 ve 10 izgara disi; 16 izgarada; 2 esik altinda (kenarlik payi)
    assert tj.olculer(css)["izgara_disi"] == 2, tj.olculer(css)


def test_gercek_css_okunuyor():
    """Asil dosya. Olcek yerinde mi?"""
    o = tj.olculer()
    assert o["punto_kullanim"] >= 160, o
    assert o["bosluk_kullanim"] >= 300, o
    obek = tj.jetonlar()
    assert {b["onek"] for b in obek} >= {"p-", "b-"}, obek
    assert len(tj.renkler()) > 10


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
