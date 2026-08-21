"""Tazeleme SIFIR MODEL MALIYETIYLE calisiyor mu?

Buradaki testlerin tek isi su iddiayi korumak: tazeleme hicbir
model cagrisi yapmaz. Iddia korunmazsa kip anlamsizlasir -- zaten
yeniden uretmek de ayni iste.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bilanco_tazele as T   # noqa: E402


def test_eski_bicimden_yorum_okunuyor():
    """Eski sayfalarda yorum SONDA, '## Netaris yorumu' altinda."""
    g = ("## 2026/6 dönemi ölçümleri\n\n| Kalem | Değer |\n\n"
         "## Netaris yorumu\n\nHasılat arttı, nakit akışı düştü.\n")
    assert T.yorumu_al(g) == "Hasılat arttı, nakit akışı düştü."


def test_yeni_bicimden_yorum_okunuyor():
    """Yeni yapida yorum BASTA, '## Özet' altinda."""
    g = "## Özet\n\nKâr ikiye katlandı.\n\n## 2026/6 dönemi ölçümleri\n"
    assert T.yorumu_al(g) == "Kâr ikiye katlandı."


def test_ozet_once_geliyor():
    """Iki baslik da varsa '## Özet' kazanmali -- guncel olan o."""
    g = ("## Özet\n\nGüncel cümle.\n\n"
         "## Netaris yorumu\n\nEski cümle.\n")
    assert T.yorumu_al(g) == "Güncel cümle."


def test_yorum_yoksa_bos_donuyor():
    """Bulamayinca UYDURMUYOR.

    Bos donmesi onemli: cagiran taraf bos gorunce sayfaya HIC
    dokunmuyor. Yorumsuz sayfa uretmek, "her bilanco AI yorumundan
    gecer" kuralini tazeleme kapisindan delmek olurdu.
    """
    assert T.yorumu_al("## Ölçümler\n\n| a | b |\n") == ""


def test_cok_satirli_yorum_tek_satira_iniyor():
    """On bilgiye yazilacagi icin satir sonu KALMAMALI.

    Kalsaydi YAML on bilgi bozulur ve sayfa hic islenmezdi.
    """
    g = "## Özet\n\nBirinci satır\nikinci satır.\n\n## Ölçümler\n"
    o = T.yorumu_al(g)
    assert "\n" not in o
    assert o == "Birinci satır ikinci satır."


def test_bilanco_olmayan_sayfaya_dokunmuyor(tmp=None):
    """Makro analizler ayni klasorde -- tazeleme onlari atlamali."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "2026-08-20-makro.md"
        p.write_text("---\nkod: MAKRO\nkategori: Analiz\n---\n\ngövde\n",
                     encoding="utf-8")
        ok, not_ = T.sayfa_tazele(p, {}, {}, kuru=True)
        assert ok is False
        assert not_ == "", not_        # sessizce atlanir, hata degil


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
