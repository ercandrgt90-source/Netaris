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


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
