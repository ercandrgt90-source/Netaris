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
    # `**k` BILINCLI: gercek `donem_getir` yeni bir anahtar kelime
    # aldiginda (`tablolar`) bu sahte imza onu REDDEDIYORDU ve sinama
    # TypeError ile dusuyordu. Sahte bir imzanin gercegi birebir
    # taklit etmesi SART degil; reddetmemesi sart.
    def _getir(kod, etiket, ceyrek=1, sektor_tr="", istemci=None,
               ciftli=False, seri=False, **k):
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


# ----------------------------------------------------------------
# ANLAMSIZ YUZDE -- UCUNCU GOC SEBEBI
#
# OLCULDU (2026-11-21): 220 yayimlanmis sayfada 597 kez %100'u
# asan bir AZALIS yaziyordu ("faaliyet karinin %1.897,5
# gerilemesine"). %100'u asan azalis, degerin SIFIRI GECTIGI
# demektir -- "yuzde kac azaldi" sorusunun cevabi yoktur.
#
# Kaynak duzeltildi (`oranlar._yuzde_degisim`) ama KURALI
# SIKILASTIRMAK ESKI ICERIGI TEMIZLEMEZ. Sayfalar goc kuyruguna
# alindi; kuyruk tazelendikce kisaliyor.
# ----------------------------------------------------------------


def test_anlamsiz_yuzde_yakalaniyor():
    assert T._anlamsiz_yuzde("brüt kârın %574,5 düşmesi")
    assert T._anlamsiz_yuzde("net kârın %476,5 azalmasına")
    assert T._anlamsiz_yuzde("%101 geriledi")
    # BINLIK AYRACLI BICIM. Ilk yazim bunu KACIRIYORDU: desen yuzde
    # isaretinden sonra UC HANE bekliyordu ve "1.897,5" dizgisinde
    # ilk hane tekti -- docstring bu ornegi verdigi halde
    # eslesmiyordu. Birim sinamasi yakaladi.
    assert T._anlamsiz_yuzde("faaliyet kârının %1.897,5 gerilemesine")
    assert T._anlamsiz_yuzde("faaliyet kârının %1897,5 gerilemesine")


def test_mesru_yuzde_yakalanmiyor():
    # Kurali genis yazmak calisani bozar; sinir iki yandan tutuluyor.
    assert not T._anlamsiz_yuzde("hasılatın %48,2 düşmesi")
    # TAM %100 MESRU: deger sifira inmistir.
    assert not T._anlamsiz_yuzde("kârın %100,0 azalması")
    assert not T._anlamsiz_yuzde("%99,9 geriledi")
    # ARTIS TARAFI KONUMUZ DEGIL: %500 artis olabilir (dusuk
    # tabandan kata cikis), %500 AZALIS olamaz. Bu ayrim olmadan
    # kural her yuksek yuzdeyi yakalar ve kuyruk hic tukenmezdi.
    assert not T._anlamsiz_yuzde("FAVÖK'ün %787,1 artmasıyla")
    assert not T._anlamsiz_yuzde("%1.234 arttı")
    assert not T._anlamsiz_yuzde("hiç yüzde yok")


def test_ai_ozetindeki_yuzde_kuyruga_SOKULMUYOR():
    """Tazeleme AI ozetini yeniden yazmaz -- onu kuyruga almak,
    tukenmeyen bir kuyruk demektir.

    `sayfa_tazele` SIFIR MODEL CAGRISI yapiyor: ozeti sayfadan
    OKUYUP yeniden kullaniyor. Yaniltici yuzde yalnizca ozetteyse
    tazeleme onu DUZELTEMEZ; sayfa her kosuda denenir ve her kosuda
    ayni halde kalir.

    OLCULDU (2026-11-21): 220 sayfanin 24'unde yuzde YALNIZCA
    ozetteydi, 89'unda ozette DE vardi. Ozeti saysaydik 113 sayfa
    kuyruktan hic dusmez, kosu basina 60 sayfalik butceyi kalici
    olarak yer ve tamamlanabilen bolum gocunu ac birakirdi.
    """
    ozet_ici = (
        "---" + chr(10) + "kod: ORNEK" + chr(10) + "---" + chr(10)
        + chr(10) + "## Özet" + chr(10) + chr(10)
        + "Net kârın %476,5 azalmasıyla birlikte..." + chr(10)
        + chr(10) + "## Öne çıkan ölçümler" + chr(10) + chr(10)
        + "- Hasılat reel olarak -%5,4 geriledi." + chr(10))
    assert not T._anlamsiz_yuzde(ozet_ici), (
        "yalnizca OZETTE olan yuzde kuyruga sokulmamali")

    # Ayni sayfa, bu kez DETERMINISTIK bolumde de var: kuyruga
    # girmeli, cunku tazeleme o bolumu yeniden uretiyor.
    disarida_da = ozet_ici.replace(
        "- Hasılat reel olarak -%5,4 geriledi.",
        "- Net kâr reel olarak -%282,7 geriledi.")
    assert T._anlamsiz_yuzde(disarida_da), (
        "deterministik bolumdeki yuzde kuyruga GIRMELI")

    # Ozet bolumu YOKSA tum metin taranmali -- kirpma, ozeti
    # olmayan sayfayi sessizce bosaltmamali.
    ozetsiz = ("---" + chr(10) + "kod: ORNEK" + chr(10) + "---" + chr(10)
               + chr(10) + "- Net kâr reel olarak -%282,7 geriledi."
               + chr(10))
    assert T._anlamsiz_yuzde(ozetsiz), (
        "ozet bolumu olmayan sayfa da taranmali")


def test_on_bilgideki_kopya_da_kuyruga_SOKULMUYOR():
    """On bilgi ozetten TURETILMIS bir kopya -- o da duzelmez.

    OLCULDU: bir sayfa GERCEKTEN tazelendi ve olcut HALA True
    donuyordu. Ayni cumle iki kez geciyordu: biri on bilgideki
    `aciklama` alaninda (kirpilmis), biri "## Ozet" icinde.
    Yalnizca ozeti cikarmak sayfayi kuyrukta BIRAKIYORDU.

    Kuru kosu bunu GOSTERMEDI -- yalnizca gercek tazeleme gosterdi.
    "Kirptim" demek yetmiyor; kirpmadan sonra gercekten dustugunu
    OLCMEK gerekiyor.
    """
    sayfa = (
        "---" + chr(10)
        + "kod: ORNEK" + chr(10)
        + "aciklama: faaliyet kârının %132,7 düşerek negatifleşmesi…"
        + chr(10) + "---" + chr(10) + chr(10)
        + "## Özet" + chr(10) + chr(10)
        + "faaliyet kârının %132,7 düşerek negatifleşmesi." + chr(10)
        + chr(10) + "## Öne çıkan ölçümler" + chr(10) + chr(10)
        + "- Hasılat reel olarak -%5,4 geriledi." + chr(10))
    assert not T._anlamsiz_yuzde(sayfa), (
        "on bilgi + ozet disinda temiz sayfa kuyruga girmemeli")

    # ON BILGI KIRPMASI GOVDEYI YUTMAMALI: deterministik bolumdeki
    # yuzde hala yakalanmali.
    kirli = sayfa.replace("- Hasılat reel olarak -%5,4 geriledi.",
                          "- Net kâr reel olarak -%282,7 geriledi.")
    assert T._anlamsiz_yuzde(kirli), (
        "on bilgi kirpmasi govdedeki yuzdeyi yutmamali")

    # ON BILGISI OLMAYAN sayfa da taranmali.
    onsuz = "## Öne çıkan ölçümler" + chr(10) + chr(10) + (
        "- Net kâr reel olarak -%282,7 geriledi." + chr(10))
    assert T._anlamsiz_yuzde(onsuz)


def test_anlamsiz_yuzde_goc_kuyruguna_BAGLANMIYOR():
    """Bagliydi; URETIMDE OLCULDU ve CALISMIYORDU -- geri alindi.

    Kosu #117: kuyruk 145 sayfa buldu, TAZELENEN 0. Tazeleme
    "sifir MODEL cagrisi" yapiyor ama AGDAN VERI CEKIYOR; kaynak
    uretim adiminda tukenmisti (HTTP 429) ve kesici sekiz redden
    sonra acildi.

    Son bes bilanco kosusunda goc adiminin tazeledigi TOPLAM sayfa:
    1. Yani ~0,2 sayfa/kosu; 145 sayfa ~725 kosu eder. Kuyruk
    tukenmez, her kosuda sekiz istegi kapali kaynaga harcar ve
    TAMAMLANABILEN bolum gocunu ac birakir (#117'de o da 0 kaldi).

    Bu sinama kurali TERSINE tutuyor: bagliligi geri koymak,
    olculmus bir cikmaza geri donmek olur.
    """
    import ast
    import inspect
    agac = ast.parse(inspect.getsource(T.goc_kuyrugu))
    cagrilar = {n.func.id for n in ast.walk(agac)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)}
    assert "_anlamsiz_yuzde" not in cagrilar, (
        "goc kuyruguna geri baglanmis -- olculdu, tukenmiyor")


def test_anlamsiz_yuzde_OLCUM_secenegi_CALISIYOR():
    """Sunulan secenek calismali.

    Kuyruktan cikarilan olcut bir OLCUM aracina donustu. Bayragi
    belgeleyip islemeyen bir dal, bu depoda tanidik bir kusur:
    kabul edilir, hicbir sey yapmaz, aylar sonra ortaya cikar.
    """
    import ast
    import inspect
    kaynak = inspect.getsource(T.main)
    agac = ast.parse(kaynak)
    # Bayrak TANIMLI mi?
    assert "--anlamsiz-yuzde" in kaynak, "bayrak tanimli degil"
    # ...ve gercekten OKUNUYOR mu? "tanimli ama hic bakilmayan"
    # bayrak sessizce hicbir sey yapmaz.
    okunan = {n.attr for n in ast.walk(agac)
              if isinstance(n, ast.Attribute)}
    assert "anlamsiz_yuzde" in okunan, (
        "bayrak tanimli ama DEGERI HIC OKUNMUYOR")
    # ...ve o dal `_anlamsiz_yuzde` cagiriyor mu?
    cagrilar = {n.func.id for n in ast.walk(agac)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)}
    assert "_anlamsiz_yuzde" in cagrilar, (
        "bayrak var ama olcumu HIC cagirmiyor")

if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
