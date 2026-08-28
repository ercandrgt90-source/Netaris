"""Bilanco sayfasi ATLAMA mantigi.

Bu dosyanin varlik sebebi olculmus bir kusur: atlama HIC calismiyordu
ve gorunur bir belirtisi yoktu. Hat her kosuda ayni sirketi yeniden
uretecek, AYNI MODEL CAGRISINI ikinci kez odeyecekti. Sessiz maliyet
hatalardan daha uzun yasar, cunku kimse aramaz.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import uret_bilanco_sayfa as u    # noqa: E402


def _yaz(klasor, ad, kod, donem):
    (klasor / ad).write_text(
        f"---\nslug: x\nbaslik: X\nkod: {kod}\ndonem: {donem}\n"
        f"kategori: Bilanço Analizi\n---\n\ngövde\n", encoding="utf-8")


def test_dosya_adi_ters_olsa_da_buluyor(tmp=None):
    """ASIL KUSUR. Dosya adi `2026-6-tera`, damga `tera-2026-6` idi.

    Onceki surum dosya ADINI tariyordu ve iki sira birbirini
    tutmuyordu; eslesme hicbir zaman olmadi.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        k = pathlib.Path(d)
        _yaz(k, "2026-6-tera.md", "TERA", "2026/6")   # TERS sirali ad
        eski, u.SITE = u.SITE, k
        try:
            assert ("TERA", "2026/6") in u._yayimlanmis()
        finally:
            u.SITE = eski


def test_yeni_ceyrek_atlanmiyor():
    """Gelecek ceyrek yayimlanabilmeli -- kilit degil, damga."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        k = pathlib.Path(d)
        _yaz(k, "2026-6-tera.md", "TERA", "2026/6")
        eski, u.SITE = u.SITE, k
        try:
            v = u._yayimlanmis()
            assert ("TERA", "2026/9") not in v
            assert ("AKBNK", "2026/6") not in v
        finally:
            u.SITE = eski


def test_makro_analiz_bilanco_sanilmiyor():
    """Ayni klasordeki makro analizler sizmamali.

    Onlarin `donem` alani TARIH ("2026-08-20"); bilanco donemi
    "YIL/AY". Suzgec bicime dayaniyor, ada degil -- ad kurali yarin
    degisirse suzgec de bozulurdu.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        k = pathlib.Path(d)
        _yaz(k, "2026-08-20-makro.md", "MAKRO", "2026-08-20")
        _yaz(k, "2026-6-tera.md", "TERA", "2026/6")
        eski, u.SITE = u.SITE, k
        try:
            v = u._yayimlanmis()
            assert v == {("TERA", "2026/6")}, v
        finally:
            u.SITE = eski


def test_klasor_yoksa_cokmuyor():
    """Ilk kosuda klasor henuz yok; hat kirmizi donmemeli."""
    eski, u.SITE = u.SITE, pathlib.Path("/olmayan/yol/xyz")
    try:
        assert u._yayimlanmis() == set()
    finally:
        u.SITE = eski


def test_gercek_depoda_tera_atlaniyor():
    """Asil depo: TERA yayimlanmis, bir daha uretilmemeli."""
    v = u._yayimlanmis()
    assert ("TERA", "2026/6") in v, sorted(v)[:5]
    # Makro analizler sizmadi mi?
    assert all("/" in donem for _, donem in v)


def test_ret_depoya_yaziliyor():
    """Reddedilen yorum `ai_ret`e girmeli -- gunluge degil.

    Olculdu (2026-08-28): bilanco kosusu 287 sirketi atladi, 286'si
    "girdide olmayan sayi" idi. Hepsi gunluge basilip kayboldu;
    `ai_ret` tablosunda bilanco hattindan TEK SATIR yoktu. Yani hangi
    sayilarin uydurulduğu ve saglayici degisince duzelip duzelmedigi
    olculemiyordu -- oysa is akisinda tam bu karsilastirma icin bir
    `saglayici` girdisi var.
    """
    import contextlib
    import sqlite3
    import tempfile
    # `closing` SART: `with sqlite3.connect(...)` islemi kapatir,
    # BAGLANTIYI degil. Windows acik tanimlayiciyla dosyayi
    # sildirmiyor ve gecici dizin temizligi WinError 32 ile patliyor
    # -- ilk yazimda tam bu oldu ve ayni kusur `ret_yaz`da da vardi.
    with tempfile.TemporaryDirectory() as t:
        vt = pathlib.Path(t) / "d.db"
        with contextlib.closing(sqlite3.connect(vt)) as b, b:
            b.execute("CREATE TABLE ai_ret (id INTEGER PRIMARY KEY"
                      " AUTOINCREMENT, adres TEXT NOT NULL, baslik TEXT"
                      " NOT NULL DEFAULT '', neden TEXT NOT NULL, model"
                      " TEXT NOT NULL DEFAULT '', ham TEXT NOT NULL"
                      " DEFAULT '', kayit_ani TEXT NOT NULL)")
        eski, u.VT = u.VT, vt
        try:
            u.ret_yaz("ADEL", "ADEL KALEMCİLİK A.Ş.", "2026 2. çeyrek",
                      "girdide olmayan sayi: 357.1", "@cf/x", "ham metin")
        finally:
            u.VT = eski
        with contextlib.closing(sqlite3.connect(vt)) as b:
            satir = b.execute("SELECT adres, baslik, neden, model, ham"
                              " FROM ai_ret").fetchall()
    assert len(satir) == 1, satir
    adres, baslik, neden, model, ham = satir[0]
    # Adres bilanco hattini AYIRT ETMELI: haber retleriyle ayni
    # tabloda duruyorlar ve karsilastirma ancak ayirt edilebilirse
    # yapilabilir.
    assert adres.startswith("bilanco:"), adres
    assert "ADEL" in adres, adres
    assert "357.1" in neden, neden
    assert model == "@cf/x", model
    # HAM CIKTI SAKLANMALI: "neden reddedildi" ancak metne bakarak
    # cevaplanir.
    assert ham == "ham metin", ham


def test_ret_yazamamak_isi_dusurmuyor():
    """Depo yoksa uretim devam etmeli -- rapor uretimden onemsizdir."""
    eski, u.VT = u.VT, pathlib.Path("Z:/olmayan/dizin/yok.db")
    try:
        u.ret_yaz("X", "X A.Ş.", "2026 2. çeyrek", "sebep", "m", "h")
    finally:
        u.VT = eski


def _ozetle(sebepler, yazilan, atlanan):
    """`_dokum`u sahte bir kosu ozetiyle calistirir, yazilani dondurur."""
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        yol = pathlib.Path(t) / "ozet.md"
        yol.write_text("", encoding="utf-8")
        eski = os.environ.get("GITHUB_STEP_SUMMARY")
        os.environ["GITHUB_STEP_SUMMARY"] = str(yol)
        try:
            u._dokum(sebepler, yazilan, atlanan)
        finally:
            if eski is None:
                os.environ.pop("GITHUB_STEP_SUMMARY", None)
            else:
                os.environ["GITHUB_STEP_SUMMARY"] = eski
        return yol.read_text(encoding="utf-8")


def test_sebep_dokumu_kosu_ozetine_yaziliyor():
    """"Neden 2 sayfa" sorusu kosu SAYFASINDA cevaplanmali.

    Olculdu (2026-08-28): kosu 44 dakika calisti, 149 adaydan ikisini
    yazdi. Sebep dokumu URETILMISTI ama 328 satirlik gunlugun icinde
    kaldi; ustelik Actions gunlukleri API'den kimlik dogrulamasi
    istiyor (403). Yani cevap vardi ve okunamadi.
    """
    c = _ozetle({"güvenlik": 140, "yorum yok": 7}, 2, 147)
    assert "yazılan 2" in c, c
    assert "atlanan 147" in c, c
    assert "güvenlik" in c and "140" in c, c
    assert "yorum yok" in c and "7" in c, c


def test_ozet_siklikla_siralaniyor():
    """En cok goruleni once: uc satir okumak, 328 satiri okumaktan iyi.

    ARANAN DIZGI TABLO HUCRESI, CIPLAK KELIME DEGIL. Ilk yazimda
    `c.index("az")` deniyordu ve test KIRMIZI dondu: "az", ozetin
    kendi "**yazılan 0**" satirinin icinde gecıyor. Bu depoda tekrar
    eden hata sinifi -- parcali eslesme -- ve bu kez sinamanin
    kendisine carpti.
    """
    c = _ozetle({"az": 1, "cok": 99}, 0, 100)
    assert c.index("| cok |") < c.index("| az |"), c


def test_ozet_degiskeni_yoksa_cokmuyor():
    """Yerel calistirmada `GITHUB_STEP_SUMMARY` tanimsiz."""
    import os
    eski = os.environ.pop("GITHUB_STEP_SUMMARY", None)
    try:
        u._dokum({"güvenlik": 3}, 0, 3)      # coker mi
    finally:
        if eski is not None:
            os.environ["GITHUB_STEP_SUMMARY"] = eski


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
