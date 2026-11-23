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


def test_anlamsiz_yuzde_goc_kuyruguna_BAGLI():
    """Bagliydi, geri alindi, SIMDI YENIDEN BAGLI -- engel kalkti.

    2026-11-21'de baglandi ve URETIMDE OLCULDU: kosu #117'de kuyruk
    145 sayfa buldu, TAZELENEN 0. Sebep tazelemenin agdan veri
    cekmesi ve kaynagin ayni kosuda tukenmis olmasiydi. Geri alindi;
    gerekce "verim ~0,2 sayfa/kosu" idi ve dogruydu.

    2026-11-23'te engel KALKTI: `bilanco_defteri` ayni kosudaki
    ikinci cekimi ortadan kaldirdi. Kosu #123 olcumu:

        2026-3-ceyrek-surgy yenilendi
        tazelenen 1, atlanan 0
        defterden okunan: 1 şirket

    Bu sinama artik DUZ yonde tutuyor: bagliligi KALDIRMAK, 182
    yayimlanmis sayfayi duzeltilebilir olduklari halde duzeltmeden
    birakmak olur.
    """
    import ast
    import inspect
    agac = ast.parse(inspect.getsource(T.goc_kuyrugu))
    cagrilar = {n.func.id for n in ast.walk(agac)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)}
    assert "_anlamsiz_yuzde" in cagrilar, (
        "goc kuyrugu olcutu CAGIRMIYOR -- 182 sayfa duzeltilmeden kalir")


def test_goc_kuyrugu_olcutu_OZETI_DISLIYOR():
    """Tazeleme ozeti yeniden YAZMIYOR; olcut de ozete BAKMAMALI.

    Bakarsa: yalnizca ozetinde hatasi olan sayfa her kosuda kuyruga
    girer, tazelenir, DEGISMEZ ve yine kuyrukta kalir. Tukenmeyen
    kuyruk -- bu dosyanin korudugu kuralin tam tersi.

    Olcut AST degil DAVRANIS: `goc_kuyrugu`nun cagrisi varsayilan
    (dar) kipte mi.
    """
    import ast
    import inspect
    agac = ast.parse(inspect.getsource(T.goc_kuyrugu))
    for n in ast.walk(agac):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_anlamsiz_yuzde"):
            assert not n.keywords, (
                "goc kuyrugu olcutu `ozet_dahil` ile genisletilmis -- "
                "tazeleme ozeti duzeltemez, kuyruk tukenmez")


def test_ozet_dahil_olcutu_GENISLETIYOR():
    """`ozet_dahil=True` gercekten daha genis olmali.

    Iki olcut ayni sonucu verseydi, parametre bir dilek olurdu:
    yeniden uretim yalnizca ozette hatasi olan sayfalari HIC
    gormezdi ve hicbir sey kirmizi donmezdi.
    """
    sayfa = (
        "---" + chr(10) + "kod: ZZZZ" + chr(10)
        + "kategori: Bilanço Analizi" + chr(10) + "---" + chr(10)
        + "## Özet" + chr(10)
        + "faaliyet kârının %143,9 gerilemesi dikkat çekiyor." + chr(10)
        + "## Öne çıkan ölçümler" + chr(10)
        + "- Hasılat reel olarak -%12,0 geriledi." + chr(10))
    assert not T._anlamsiz_yuzde(sayfa), (
        "dar olcut ozetteki sayiyi saymamali")
    assert T._anlamsiz_yuzde(sayfa, ozet_dahil=True), (
        "genis olcut ozetteki sayiyi SAYMALI")


def test_yeniden_uretim_GENIS_olcutu_kullaniyor():
    """Denetleyen, DUZELTICININ kapsamini kullanmali.

    `uret_bilanco_sayfa --anlamsiz-yuzde` sayfayi bastan yaziyor ve
    ozet dahil her seyi duzeltiyor. Dar olcutle secseydi, yalnizca
    ozette hatasi olan 38 sayfa hicbir duzelticinin gorus alanina
    girmezdi: goc kuyrugu onlari zaten gormuyor.
    """
    import ast
    import inspect
    import uret_bilanco_sayfa as U
    agac = ast.parse(inspect.getsource(U.anlamsiz_yuzde_sayfalari))
    genis = [n for n in ast.walk(agac)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_anlamsiz_yuzde"
             and any(k.arg == "ozet_dahil"
                     and getattr(k.value, "value", None) is True
                     for k in n.keywords)]
    assert genis, (
        "yeniden uretim DAR olcutle seciyor -- ozet hatali sayfalar "
        "hicbir duzelticinin kapsamina girmiyor")


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

def test_yeniden_uretim_bayragi_CALISIYOR():
    """Bayrak tanimli, DEGERI okunuyor ve dali seciciyi cagiriyor.

    "Tanimli ama hic bakilmayan bayrak" bu depoda tanidik bir kusur:
    kabul edilir, hicbir sey yapmaz, aylar sonra ortaya cikar.
    """
    import ast
    import inspect
    import uret_bilanco_sayfa as U
    kaynak = inspect.getsource(U.main)
    agac = ast.parse(kaynak)
    assert "--anlamsiz-yuzde" in kaynak, "bayrak tanimli degil"
    okunan = {n.attr for n in ast.walk(agac) if isinstance(n, ast.Attribute)}
    assert "anlamsiz_yuzde" in okunan, "bayrak DEGERI hic okunmuyor"
    cagrilar = {n.func.id for n in ast.walk(agac)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "anlamsiz_yuzde_sayfalari" in cagrilar, (
        "bayrak var ama seciciyi HIC cagirmiyor")


def test_yeniden_uretim_VARSAYILAN_KAPALI():
    """Bayraksiz kosuda yayimlanmis sayfa YENIDEN URETILMEZ.

    Bu bayrak mevcut AI yorumunun yerine YENISINI koyuyor. Boyle bir
    sey varsayilan olamaz; acikca istenmeli.
    """
    import ast
    import inspect
    import uret_bilanco_sayfa as U
    agac = ast.parse(inspect.getsource(U.main))
    for n in ast.walk(agac):
        if not isinstance(n, ast.Assign):
            continue
        for h in n.targets:
            if isinstance(h, ast.Name) and h.id == "_yenilenecek":
                # Ilk atama BOS kume olmali; dolum kosula bagli.
                assert isinstance(n.value, (ast.Call, ast.Set, ast.Name)), (
                    "beklenmeyen bicim")
                break
    kaynak = inspect.getsource(U.main)
    i = kaynak.index("_yenilenecek: set")
    j = kaynak.index("anlamsiz_yuzde_sayfalari", i)
    ara = kaynak[i:j]
    assert "if n.anlamsiz_yuzde" in ara, (
        "secici KOSULSUZ cagriliyor -- bayraksiz kosuda da yayimlanmis "
        "sayfalar yeniden uretilirdi")


def test_yeniden_uretim_DEFTER_KAPSAMIYLA_sinirli():
    """Bu adimin ag butcesi YOK -- kapsam deftere bagli olmali.

    Is akisinda yeniden uretim VERI ADIMINDAN SONRA kosuyor, yani
    kaynak butcesi o noktada tukenmis oluyor. Defteri olmayan sirket
    icin `sirket_isle` aga duser, uc istek harcar ve buyuk olasilikla
    "KAYNAK VERMEDI" doner -- goc kuyrugunu olduren kusurun ta
    kendisi (kosu #117: 145 sayfa denendi, 0 tazelendi).

    Olcut: `_yenilenecek` kumesine ekleme, bir defter okumasinin
    SONUCUNA bagli olmali.
    """
    import ast
    import inspect
    import uret_bilanco_sayfa as U
    agac = ast.parse(inspect.getsource(U.main))
    bagli = False
    for n in ast.walk(agac):
        if not isinstance(n, ast.If):
            continue
        if "bilanco_defteri" not in ast.dump(n.test):
            continue
        if "oku" not in ast.dump(n.test):
            continue
        for g in ast.walk(n):
            if (isinstance(g, ast.Call) and isinstance(g.func, ast.Attribute)
                    and g.func.attr == "add"
                    and isinstance(g.func.value, ast.Name)
                    and g.func.value.id == "_yenilenecek"):
                bagli = True
    assert bagli, (
        "yeniden uretim kuyrugu DEFTER OKUMASINA bagli degil -- adim "
        "tukenmis kaynak butcesine istek atar")


def test_yeniden_uretim_ESKI_DONEMI_atlamiyor_ama_SORGULAMIYOR():
    """Eski ceyrek sayfasi bu bayrakla da yeniden URETILMEZ.

    Dongu `(kod, GUNCEL donem)` ciftini sorguluyor. Eski ceyregin
    cifti hicbir zaman sorgulanmiyor, yani 2026-1/2026-2 sayfalari
    kapsam disi kaliyor -- ki kalmali: onlari guncel donemin
    verisiyle yeniden kurmak, bir donemi soyleyip baskasinin
    rakamlarini gostermek olurdu.

    Olcut: atlama kosulundaki IKI uyelik sinamasi AYNI demeti
    kullanmali.
    """
    import ast
    import inspect
    import uret_bilanco_sayfa as U
    agac = ast.parse(inspect.getsource(U.main))
    bulundu = False
    for n in ast.walk(agac):
        if not isinstance(n, ast.If):
            continue
        dump = ast.dump(n.test)
        if "_yenilenecek" not in dump:
            continue
        bulundu = True
        # Iki Compare: biri `var`a, biri `_yenilenecek`e bakiyor ve
        # SOL tarafları ayni olmali.
        sollar = [ast.dump(c.left) for c in ast.walk(n.test)
                  if isinstance(c, ast.Compare)]
        assert len(sollar) == 2, f"beklenen iki karsilastirma, {len(sollar)}"
        assert sollar[0] == sollar[1], (
            "iki uyelik sinamasi FARKLI demet kullaniyor -- eski donem "
            "sayfasi yanlislikla yeniden uretilebilir")
    assert bulundu, "atlama kosulu `_yenilenecek`e hic bakmiyor"


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
