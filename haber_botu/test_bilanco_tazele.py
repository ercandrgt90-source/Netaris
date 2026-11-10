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


def _kurgu_sayfa(klasor):
    """Tazelemenin CEKIME kadar ilerledigi en kucuk sayfa."""
    p = pathlib.Path(klasor) / "2026-2-ceyrek-ornek.md"
    p.write_text(
        "---\nkod: ORNEK\nkategori: Bilanço Analizi\n"
        "donem: 2026 2. çeyrek\n---\n\n## Özet\n\n"
        "Saklı yorum cümlesi burada duruyor.\n",
        encoding="utf-8")
    baglam = {"ORNEK": ("Sanayi", {"brut_marj": 12.0},
                        {"brut_marj": 20.0}, 12, "2026 2. çeyrek", "")}
    defter = {"ORNEK": {"unvan": "Örnek A.Ş.", "sektor_tr": "Sanayi"}}
    return p, baglam, defter


def _cekim_kur(okunamayan_ekle):
    """`donem_getir`i VERI VERMEYEN bir cekimle degistirir.

    `okunamayan_ekle` verilirse cekim `bilanco_ag.OKUNAMAYAN`a kayit
    birakiyor -- kaynagin istegi reddettigi hal. Verilmezse kaynak
    cevap vermis ama alanlar gercekten eksiktir.
    """
    def _getir(kod, etiket, ceyrek=1, sektor_tr="", istemci=None,
               ciftli=False, seri=False):
        if okunamayan_ekle:
            T.bilanco_ag.OKUNAMAYAN.append((kod, okunamayan_ekle))
        return (None, None, ["hasilat", "net_kar"], []) if ciftli \
            else (None, ["hasilat", "net_kar"], [])
    return _getir


def test_kaynak_reddi_veri_eksikligi_gibi_YAZILMIYOR():
    """OLCULDU (2026-11-10, kosu #78): goc kuyrugundaki 28 sayfanin
    28'i `ATLANDI -- eksik: hasilat, net_kar` dondu. Gercek sebep
    ustteki uc satirdaydi (`KAYNAK KAPANDI`), sayfa basina yazilan
    satir onu tasimiyordu. Gunluge bakan biri 28 sirketin verisinin
    bozuk oldugu sonucuna varirdi.

    Ayni kusur `uret_bilanco.main` icinde bir kez duzeltilmisti
    ("KAYNAK REDDEDIYOR (veri eksikligi degil)"); buraya
    tasinmamisti.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p, baglam, defter = _kurgu_sayfa(d)
        _asil = T.bilanco_ag.donem_getir
        _n = len(T.bilanco_ag.OKUNAMAYAN)
        try:
            T.bellegi_bosalt()
            T.bilanco_ag.donem_getir = _cekim_kur("kaynak kapandi")
            ok, not_ = T.sayfa_tazele(p, baglam, defter, kuru=True)
        finally:
            T.bilanco_ag.donem_getir = _asil
            del T.bilanco_ag.OKUNAMAYAN[_n:]
            T.bellegi_bosalt()
        assert ok is False, not_
        # DIAKRITIK TUZAGINA DIKKAT: kodda etiket ASCII ("VERMEDI"),
        # aranan desen de ASCII. `upper()` ve "İ" ile yazilmis bir
        # desen burada sessizce eslesmezdi.
        assert "KAYNAK VERMEDI" in not_, not_
        assert "kaynak kapandi" in not_, not_
        # ASIL IDDIA: yanlis etiket ARTIK YOK.
        assert not not_.startswith("eksik"), not_


def test_gercek_veri_eksikligi_HALA_eksik_diyor():
    """Kapi karsi yone de calismali: kaynak cevap verdigi halde
    alanlar yoksa sebep "eksik" olmali. Yoksa her sey "kaynak
    vermedi" olur ve etiket yine bilgi tasimaz."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p, baglam, defter = _kurgu_sayfa(d)
        _asil = T.bilanco_ag.donem_getir
        try:
            T.bellegi_bosalt()
            T.bilanco_ag.donem_getir = _cekim_kur(None)
            ok, not_ = T.sayfa_tazele(p, baglam, defter, kuru=True)
        finally:
            T.bilanco_ag.donem_getir = _asil
            T.bellegi_bosalt()
        assert ok is False, not_
        assert not_ == "eksik: hasilat, net_kar", not_


def test_bellek_sebebi_de_tasiyor():
    """Ayni sirketin IKINCI sayfasi yeniden SORMUYOR ama sebebi
    DOGRU soylemeye devam ediyor. Bellek yalnizca veriyi saklarsa,
    ikinci sayfa yanlis etikete geri doner."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p, baglam, defter = _kurgu_sayfa(d)
        p2 = pathlib.Path(d) / "2026-2-ceyrek-ornek-iki.md"
        p2.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        _asil = T.bilanco_ag.donem_getir
        _n = len(T.bilanco_ag.OKUNAMAYAN)
        _cagri = []

        def _say(*a, **k):
            _cagri.append(1)
            return _cekim_kur("HTTP 429")(*a, **k)
        try:
            T.bellegi_bosalt()
            T.bilanco_ag.donem_getir = _say
            _, n1 = T.sayfa_tazele(p, baglam, defter, kuru=True)
            _, n2 = T.sayfa_tazele(p2, baglam, defter, kuru=True)
        finally:
            T.bilanco_ag.donem_getir = _asil
            del T.bilanco_ag.OKUNAMAYAN[_n:]
            T.bellegi_bosalt()
        assert len(_cagri) == 1, f"ikinci sayfa yeniden sordu: {_cagri}"
        assert "HTTP 429" in n1 and "HTTP 429" in n2, (n1, n2)


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
