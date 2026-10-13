# -*- coding: utf-8 -*-
"""ONARIM OLCUTU: HANGI SAYFA BOZUK, VE KUYRUK GERCEKTEN KISALIYOR MU.

BU DOSYA NEDEN VAR
------------------
`bilanco_denetim` iki tarafin birlikte kullandigi TEK olcut:

    site/test_bilanco_donem_tutarliligi.py  -> koruma
    bilanco_tazele --onarim                 -> onarim

Olcut iki yerde ayri yazilsaydi birinin degisip otekinin unutulmasi
kacinilmazdi; bu depoda tam o sinif kusur yayina cikti (ara donemin
kac ceyrekten olustugu `uret_bilanco` ile `donem_getir` arasinda
farkliydi).

KUYRUK SIRASI DA SINANIYOR. Alfabetik sira + `--sinir`, kuyrugun
sonuna HIC ulasmiyor: her kosu ayni ilk N sayfayi yeniden kuruyor.
Ayni tuzaga sektor sirasinda dusulmustu (olculdu 2026-09-14: 11
sektorun hep ayni ilk ucu cekiliyordu). Onarim kuyrugu bu yuzden
IHTIYACA gore kuruluyor ve onarilan sayfa kuyruktan DUSUYOR.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_denetim as bd                       # noqa: E402

#: Satir sonu ELDE kuruluyor. Bu dosya bir here-doc ile
#: yazildiginda kacisli satir sonu sessizce GERCEK satir sonuna
#: donusuyor ve dizge kapanmamis kaliyor; tuzak depoda kayitli.
SATIR_SONU = chr(10)

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _sayfa(hasilat, brut, net, ozkaynak, brut_marj, roe,
           kilavuz="", kod="ZZZZ"):
    s = [
        "---", f"kod: {kod}", "kategori: Bilanço Analizi", "---", "",
        "## 2026 2. çeyrek dönemi ölçümleri", "",
        "| Kalem | Değer |", "| --- | ---: |",
        f"| Hasılat | {hasilat} milyar TL |",
        f"| Brüt kâr | {brut} milyar TL |",
        f"| Net kâr | {net} milyar TL |",
        f"| Özkaynak | {ozkaynak} milyar TL |", "",
        "## Sektör içindeki konum", "",
        "| Oran | Şirket | Sektör medyanı |", "| --- | ---: | ---: |",
        f"| Brüt kâr marjı | {brut_marj} | %20,0 |",
        f"| Özkaynak kârlılığı | {roe} | %5,0 |", "",
    ]
    if kilavuz:
        s += [f"## {kilavuz}", "", "Bir paragraf.", ""]
    return "\n".join(s)


print("1. Tutarli sayfa BOZUK sayilmiyor")
# 5,00 / 10,00 = %50,0 ;  1,00 / 10,00 = %10,0
_T = _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0")
esit(bd.bilanco_sayfasi(_T), True, "bilanço sayfası tanınıyor")
esit(len(bd.olc(_T)), 2, "iki oran da ölçülebiliyor")
esit(bd.donem_tutarsizligi(_T), [], "tutarlı sayfada uyuşmazlık yok")
esit(bd.onarim_gereken(_T), [], "onarım gerekmiyor")

print("")
print("2. Seviye ile oran uyusmuyorsa YAKALANIYOR")
_B = _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0")
_k = bd.donem_tutarsizligi(_B)
esit([a for a, _h, _y in _k], ["brut_marj"], "brüt marj uyuşmazlığı")
esit(round(_k[0][1], 1), 50.0, "seviyeden hesaplanan %50,0")
esit(round(_k[0][2], 1), 12.0, "yazılı %12,0")
esit(bd.onarim_gereken(_B), ["dönem tutarsız (brut_marj)"],
     "onarım sebebi yazılıyor")

print("")
print("3. Yuvarlanma payi TOLERE ediliyor, gercek fark EDILMIYOR")
# 1,48 / 16,20 = %9,136 -- iki ondalikli yazimin payi icinde.
esit(bd.donem_tutarsizligi(
    _sayfa("16,20", "1,48", "1,00", "10,00", "%9,1", "%10,0")), [],
    "yuvarlanma payı içindeki fark bozuk sayılmıyor")
# Ayni sayfada yazili %8,8 ise fark yuvarlanmayla aciklanamaz
# (olculdu: 2026-1-ceyrek-asuzu.md tam boyleydi).
esit(len(bd.donem_tutarsizligi(
    _sayfa("16,20", "1,48", "1,00", "10,00", "%8,0", "%10,0"))), 1,
    "payın dışındaki fark YAKALANIYOR")

print("")
print("4. Kapsam disi kilavuz YAKALANIYOR")
_TELEKOM = "Telekomünikasyonda borç ve amortisman neden yüksektir"
_F = _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
            kilavuz=_TELEKOM, kod="FENER")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", "Entertainment"), _TELEKOM,
     "futbol kulübünde telekom kılavuzu yakalanıyor")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", "Telecom Services"), "",
     "telekomda aynı kılavuz SORUN DEĞİL")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", ""), "",
     "alt sektör bilinmiyorsa kısıtlama yok")
esit(bd.onarim_gereken(_F, {"sektor_tr": "İletişim",
                            "alt_sektor": "Entertainment"}),
     [f"kapsam dışı kılavuz ({_TELEKOM})"],
     "onarım sebebi kılavuz olarak yazılıyor")
# Kilavuz sayfada YOKSA uyusmazlik da yok -- sebep sayfada olmali.
esit(bd.kilavuz_uyusmazligi(_T, "İletişim", "Entertainment"), "",
     "kılavuz sayfada yoksa uyuşmazlık YOK")

print("")
print("4b. Negatif ozkaynakla ROE gosterilmesi YAKALANIYOR")
# Projenin kendi kurali: `oranlar._bol` negatif bolende None doner,
# cunku negatif ozkaynakla hesaplanan ROE anlamsizdir ve yaniltir.
# Olculdu (2026-10-13): yayindaki alti sayfa bunu yapiyordu --
# `bizim` ozkaynagi -0,22 milyar iken ROE +%128,5 yaziyordu.
_NEG = _sayfa("10,00", "5,00", "-1,00", "-0,22", "%50,0", "%128,5")
esit(bd.ozkaynak_celiskisi(_NEG),
     "özkaynak -0.22 milyar iken ROE %128,5 yazılı",
     "negatif özkaynakta ROE yakalanıyor")
# Negatif ROE de anlamsiz: isaret degil BOLEN sorunlu.
_NEG2 = _sayfa("10,00", "5,00", "1,00", "-0,50", "%50,0", "-%8,0")
esit(bool(bd.ozkaynak_celiskisi(_NEG2)), True,
     "negatif ROE de yakalanıyor (sorun bölen)")
# SIFIR ozkaynak da bolen olarak gecersiz.
_SIFIR = _sayfa("10,00", "5,00", "1,00", "0,00", "%50,0", "%5,0")
esit(bool(bd.ozkaynak_celiskisi(_SIFIR)), True, "sıfır özkaynak da geçersiz")
# POZITIF ozkaynakta sorun YOK.
esit(bd.ozkaynak_celiskisi(_T), "", "pozitif özkaynakta sorun yok")
# ROE sayfada YAZILI DEGILSE celiski de yok -- zaten uretilmemis.
_YOK = _sayfa("10,00", "5,00", "-1,00", "-0,22", "%50,0", "%0,0").replace(
    "| Özkaynak kârlılığı | %0,0 | %5,0 |", "")
esit(bd.ozkaynak_celiskisi(_YOK), "",
     "ROE yazılmamışsa çelişki de yok (doğru davranış)")
esit("anlamsız ROE (özkaynak -0.22 milyar iken ROE %128,5 yazılı)"
     in bd.onarim_gereken(_NEG), True, "onarım sebebi olarak yazılıyor")

print("")
print("5. Iki sebep birlikte yaziliyor")
_IKI = _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0",
              kilavuz=_TELEKOM, kod="FENER")
esit(bd.onarim_gereken(_IKI, {"sektor_tr": "İletişim",
                              "alt_sektor": "Entertainment"}),
     ["dönem tutarsız (brut_marj)",
      f"kapsam dışı kılavuz ({_TELEKOM})"],
     "iki sebep birlikte")

print("")
print("6. Bilanco sayfasi OLMAYAN dosyaya dokunulmuyor")
esit(bd.onarim_gereken("---\nkategori: Haber\n---\n\nMetin."), [],
     "haber sayfası onarım kuyruğuna girmiyor")
esit(bd.olc("boş"), [], "kıyas bölümü yoksa ölçüm yok")

print("")
print("7. ONARIM KUYRUGU IHTIYACA gore kuruluyor, alfabetik DEGIL")
import uret_bilanco_sayfa as U                     # noqa: E402
import bilanco_tazele as BT                        # noqa: E402

_ASIL_SITE = U.SITE
try:
    g = pathlib.Path(tempfile.mkdtemp())
    U.SITE = g
    # Alfabetik olarak ONCE gelen sayfa SAGLAM, sonra gelen BOZUK.
    # Kuyruk alfabetikse saglam olan basta cikar ve `--sinir 1`
    # bozugu HIC onarmaz.
    (g / "aaa-saglam.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kod="AAA"), encoding="utf-8")
    (g / "zzz-bozuk.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0",
               kod="ZZZ"), encoding="utf-8")
    kuyruk = BT.onarim_kuyrugu({})
    esit([y.stem for y, _ in kuyruk], ["zzz-bozuk"],
         "kuyrukta YALNIZCA bozuk sayfa var (saglam olan yok)")
    # Sayfa duzeltilince kuyruktan DUSUYOR -- adim kendiliginden
    # etkisiz hale geliyor, sonsuza kadar ayni isi yapmiyor.
    (g / "zzz-bozuk.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kod="ZZZ"), encoding="utf-8")
    esit(BT.onarim_kuyrugu({}), [], "onarılan sayfa kuyruktan DÜŞÜYOR")

    # KUYRUK DEFTERI GERCEKTEN OKUYOR MU.
    #
    # Alt sektor denetimi yalnizca defter kaydi gecirildiginde
    # calisiyor. Kuyruk kaydi gecirmezse kilavuz uyusmazligi SESSIZCE
    # gorunmez olur -- islev dogru olur, kullanimi yanlis.
    (g / "mmm-kulup.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kilavuz=_TELEKOM, kod="FENER"), encoding="utf-8")
    esit(BT.onarim_kuyrugu({}), [],
         "defter kaydı olmayan şirkette kılavuz kısıtlanmıyor")
    _defter = {"FENER": {"sektor_tr": "İletişim",
                         "alt_sektor": "Entertainment"}}
    esit([y.stem for y, _ in BT.onarim_kuyrugu(_defter)], ["mmm-kulup"],
         "DEFTERDEN okunan alt sektörle kılavuz uyuşmazlığı yakalanıyor")
finally:
    U.SITE = _ASIL_SITE

print("")
print("8. sayfa_tazele UCTAN UCA: onarilan sayfa denetimden geciyor")
#
# BU MADDE NEDEN VAR: `sayfa_tazele` hic sinanmiyordu ve icine
# yanlis modulden cagri yazildi (`U._oranlari`, oysa `_oranlari`
# `uret_bilanco` icinde). Hata ancak GERCEK kosuda AttributeError
# olarak ortaya cikti. Yanlis modul adi gibi bir kusur, yalnizca
# kodu CALISTIRAN bir sinamayla yakalanir.
#
# SINAMA GERCEK ICERIK DIZININE YAZMAZ. `yayin.yaz_sektorel`
# kanonik yola yaziyor; ilk yazim bu yuzden `site/icerik/analizler`
# icine gercek bir dosya birakti. Depodaki kural net: hicbir sinama
# urunun ciktisini kirletmez. Yazma cagrisi artik YAKALANIYOR.
import oranlar                                     # noqa: E402

_ASIL_GETIR = BT.bilanco_ag.donem_getir
_ASIL_YAZ = BT.yayin.yaz_sektorel
try:
    g = pathlib.Path(tempfile.mkdtemp())
    yol = g / "2026-2-ceyrek-ornek.md"
    yol.write_text(SATIR_SONU.join([
        "---", "kod: ORNEK", "kategori: Bilanço Analizi",
        "donem: 2026 2. çeyrek", "---", "",
        "## Özet", "",
        "Saklı yorum cümlesi burada duruyor.", "",
        "## 2026 2. çeyrek dönemi ölçümleri", "",
        "| Kalem | Değer |", "| --- | ---: |",
        "| Hasılat | 10,00 milyar TL |",
        "| Brüt kâr | 5,00 milyar TL |", "",
        "## Sektör içindeki konum", "",
        "| Oran | Şirket | Sektör medyanı |", "| --- | ---: | ---: |",
        "| Brüt kâr marjı | %12,0 | %20,0 |", "",
    ]), encoding="utf-8")
    esit(bool(bd.onarim_gereken(yol.read_text(encoding="utf-8"))), True,
         "baslangicta sayfa BOZUK (seviyeden %50, yazili %12)")

    _d = oranlar.Donem(
        etiket="2026 2. çeyrek", hasilat=12_400_000_000.0,
        brut_kar=2_100_000_000.0, faaliyet_kari=900_000_000.0,
        net_kar=640_000_000.0, ozkaynak=8_300_000_000.0,
        aktif_toplami=19_700_000_000.0, donen_varliklar=7_100_000_000.0,
        kisa_vadeli_yukumlulukler=5_400_000_000.0)
    BT.bilanco_ag.donem_getir = (
        lambda kod, etiket, ceyrek=1, sektor_tr="", istemci=None,
        ciftli=False: (_d, None, []) if ciftli else (_d, []))
    _yazilan = {}
    BT.yayin.yaz_sektorel = lambda **kw: _yazilan.update(kw)

    # Baglam OZETTEN gelen BOZUK orani tasiyor; tazeleme onu
    # KULLANMAMALI, sayfanin kendi verisinden turetmeli.
    baglam = {"ORNEK": ("Sanayi", {"brut_marj": 12.0, "net_marj": 3.0},
                        {"brut_marj": 20.0, "net_marj": 5.0}, 12,
                        "2026 2. çeyrek", "")}
    defter = {"ORNEK": {"unvan": "Örnek A.Ş.", "sektor_tr": "Sanayi",
                        "alt_sektor": "Conglomerates"}}
    ok, not_ = BT.sayfa_tazele(yol, baglam, defter, False)
    esit(ok, True, f"sayfa tazelendi ({not_})")
    esit(bool(_yazilan), True, "yazma cagrisi YAKALANDI (diske yazilmadi)")
    _g = _yazilan["govde"]
    _m = _g if isinstance(_g, str) else SATIR_SONU.join(_g)
    esit(bd.onarim_gereken(_m, defter["ORNEK"]), [],
         "ONARILAN govde denetimden SORUNSUZ geciyor")
    esit("Saklı yorum cümlesi" in _m, True,
         "saklı yorum korundu (model çağrısı yok)")
    esit("%16,9" in _m, True,
         "oran sayfanın KENDİ verisinden (2,10/12,40 = %16,9)")
    esit("%12,0" in _m, False, "özetteki BOZUK oran kullanılmadı")
finally:
    BT.bilanco_ag.donem_getir = _ASIL_GETIR
    BT.yayin.yaz_sektorel = _ASIL_YAZ

print("")
print("9. AYNI SIRKETIN IKI SAYFASI TEK CEKIMLE onariliyor")
#
# Darbogaz kaynagin izni: kosu basina yaklasik 17 sayfalik veri
# veriyor, sonra reddediyor. Kuyrukta 187 sayfa icin 169 benzersiz
# sirket vardi -- 18 sayfa ayni veriyi IKINCI kez istiyordu, yani 54
# gereksiz istek. Tasarruf edilen her istek o pencerede onarilan
# sayfa sayisini artiriyor.
_ASIL_GETIR2 = BT.bilanco_ag.donem_getir
_ASIL_YAZ2 = BT.yayin.yaz_sektorel
try:
    _sayac = {"n": 0}
    _dd = oranlar.Donem(
        etiket="2026 2. çeyrek", hasilat=12_400_000_000.0,
        brut_kar=2_100_000_000.0, faaliyet_kari=900_000_000.0,
        net_kar=640_000_000.0, ozkaynak=8_300_000_000.0,
        aktif_toplami=19_700_000_000.0, donen_varliklar=7_100_000_000.0,
        kisa_vadeli_yukumlulukler=5_400_000_000.0)

    def _say(kod, etiket, ceyrek=1, sektor_tr="", istemci=None,
             ciftli=False):
        _sayac["n"] += 1
        return (_dd, None, []) if ciftli else (_dd, [])

    BT.bilanco_ag.donem_getir = _say
    BT.yayin.yaz_sektorel = lambda **kw: None
    BT.bellegi_bosalt()

    g2 = pathlib.Path(tempfile.mkdtemp())
    for ceyrek in ("1", "2"):
        (g2 / f"2026-{ceyrek}-ceyrek-ornek.md").write_text(
            SATIR_SONU.join([
                "---", "kod: ORNEK", "kategori: Bilanço Analizi", "---", "",
                "## Özet", "", "Saklı yorum.", "",
                "| Hasılat | 10,00 milyar TL |",
                "| Brüt kâr | 5,00 milyar TL |", "",
                "## Sektör içindeki konum", "",
                "| Brüt kâr marjı | %12,0 | %20,0 |", "",
            ]), encoding="utf-8")
    baglam2 = {"ORNEK": ("Sanayi", {"brut_marj": 12.0},
                         {"brut_marj": 20.0}, 12, "2026 2. çeyrek", "")}
    defter2 = {"ORNEK": {"unvan": "Örnek A.Ş.", "sektor_tr": "Sanayi",
                         "alt_sektor": "Conglomerates"}}
    for yol2 in sorted(g2.glob("*.md")):
        BT.sayfa_tazele(yol2, baglam2, defter2, False)
    esit(_sayac["n"], 1, "IKI sayfa icin TEK cekim yapildi")

    # BASARISIZLIK DA SAKLANIYOR: kapali kapiya ikinci kez vurulmuyor.
    BT.bellegi_bosalt()
    _sayac["n"] = 0
    BT.bilanco_ag.donem_getir = (
        lambda kod, etiket, ceyrek=1, sektor_tr="", istemci=None,
        ciftli=False: _say(kod, etiket) and None or
        ((None, None, ["hasilat"]) if ciftli else (None, ["hasilat"])))
    for yol2 in sorted(g2.glob("*.md")):
        ok2, _ = BT.sayfa_tazele(yol2, baglam2, defter2, False)
        esit(ok2, False, "veri gelmeyince sayfaya dokunulmuyor")
    esit(_sayac["n"], 1, "basarisizlik da bellekte -- ikinci istek YOK")

    # BELLEK KOSUYA AIT: bosaltilinca yeniden soruluyor.
    BT.bilanco_ag.donem_getir = _say
    BT.bellegi_bosalt()
    _sayac["n"] = 0
    BT.sayfa_tazele(sorted(g2.glob("*.md"))[0], baglam2, defter2, False)
    esit(_sayac["n"], 1, "bellek bosaltilinca yeniden soruluyor")

    # MAIN HER CAGRIDA BELLEGI BOSALTMALI -- davranissal olarak.
    #
    # Islevin dogru olmasi, cagrildigi anlamina gelmiyor; bu depoda
    # ayni bosluk birkac kez yasandi. `main` iki kez cagriliyor ve
    # IKINCI cagrinin da cekim yapmasi bekleniyor.
    import sys as _sys                              # noqa: PLC0415
    _ASIL_ARGV = _sys.argv
    _ASIL_SITE2 = U.SITE
    _ASIL_BAGLAM = BT.baglam_kur
    try:
        _sys.argv = ["bilanco_tazele", "--onarim", "--sinir", "1"]
        U.SITE = g2
        BT.baglam_kur = lambda: (baglam2, defter2)
        _sayac["n"] = 0
        esit(BT.main(), 0, "main calisti")
        _ilk = _sayac["n"]
        # ILK KOSU GERCEKTEN CEKMELI. Bu satir olmadan sinama BOSA
        # dusuyordu: `main` bellegi bosaltmazsa ilk kosu da onceki
        # maddeden kalan bellegi kullanir, `_ilk` sifir olur ve
        # "0 == 0" diye gecer. Mutasyon bunu gosterdi.
        if _ilk < 1:
            print("  DUSTU  ilk main cagrisi HIC cekim yapmadi "
                  "(bellek bosaltilmiyor)")
            raise SystemExit(1)
        _gecti += 1
        print(f"  gecti  ilk main cagrisi cekim yapti ({_ilk})")
        esit(BT.main(), 0, "main ikinci kez calisti")
        esit(_sayac["n"], _ilk * 2,
             "IKINCI kosu yeniden cekiyor (bellek kosuya ait)")
    finally:
        _sys.argv = _ASIL_ARGV
        U.SITE = _ASIL_SITE2
        BT.baglam_kur = _ASIL_BAGLAM
finally:
    BT.bilanco_ag.donem_getir = _ASIL_GETIR2
    BT.yayin.yaz_sektorel = _ASIL_YAZ2
    BT.bellegi_bosalt()

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
