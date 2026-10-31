# -*- coding: utf-8 -*-
"""SON DORT DONEM TABLOSU -- EGILIM, TEK NOKTA DEGIL.

BU DOSYA NEDEN VAR
------------------
Bilanco sayfasi iki soruyu cevapliyordu: "su an ne kadar" (olcum
tablosu) ve "gecen yilin ayni donemine gore ne degisti". Ikisi de
IKI NOKTA; egilim gostermiyorlar. Tek seferlik bir sicrama ile
surekli bir yukselis ayni goruntuyu veriyor.

Dort ardisik donem bir TAM yillik dongu: mevsimsel bir isletmede
inisin mevsimden mi egilimden mi geldigi ancak boyle ayirt
ediliyor.

EK ISTEK OLMAMASI BIR SART, SUS DEGIL
-------------------------------------
Kaynak (stockanalysis.com) bizi zaten kisitliyor; gunluk kosuda
"KAYNAK KAPANDI -- ardisik red" satiri olculdu. Seri icin AYRI bir
cekim yapmak 325 sirkette ~975 fazladan istek demekti. Seri bu
yuzden ZATEN CEKILMIS tablodan, `donem_toplami`nin `kaydir`
parametresiyle uretiliyor -- onceki yilin ayni donemi de yillardir
boyle uretiliyordu.

Bu dosyadaki `cek` sayaci tam olarak bunu tutuyor: seri eklendikten
SONRA da sayfa basina istek sayisi DEGISMEMELI.

EN KRITIK IDDIA: BIRINCI SUTUN = OLCUM TABLOSU
----------------------------------------------
Seri ile olcum tablosu AYRI yollardan uretiliyor (`alanlar` ve
`donemi_kur(ek=...)`). Ikisi ayrismaya baslarsa sayfa ayni
baslikta IKI AYRI DONEM anlatir. Bu depo tam bu kusuru bir kez
yasadi: 258 bilanco sayfasinin 203'u oran ile seviye tablosunu
ayri kaynaklardan aliyordu. O yuzden ozdeslik BURADA tutuluyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_ag                                        # noqa: E402
import uret_bilanco_sayfa as US                          # noqa: E402

#: Ters bolu kacisi bu depoda defalarca SESSIZCE baska bir
#: seye dondu; sabit olarak tutuluyor.
NL = chr(10)

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


# ---------------------------------------------------------------------
# SAHTE KAYNAK -- AG YOK
# ---------------------------------------------------------------------
#
# Degerler ELLE secildi ve her ceyrekte FARKLI: ayni sayiyi dort kez
# yazmak, kaydirmanin calismadigi bir kodu da gecirirdi.
_DONEMLER = ["Q3 2026", "Q2 2026", "Q1 2026", "Q4 2025", "Q3 2025"]
_TARIHLER = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31",
             "2025-09-30"]
_GELIR = {
    "Revenue": [100.0, 90.0, 80.0, 70.0, 60.0],
    "Net Income": [10.0, 9.0, 8.0, 7.0, 6.0],
}
_BILANCO = {"Total Assets": [500.0, 480.0, 460.0, 440.0, 420.0],
            "Shareholders' Equity": [200.0, 190.0, 180.0, 170.0, 160.0]}

_cagri = {"n": 0}


def _sahte_cek(kod, sayfa="gelir", istemci=None, tarih_de=False):
    _cagri["n"] += 1
    kalem = _GELIR if sayfa == "gelir" else _BILANCO
    if tarih_de:
        return list(_DONEMLER), dict(kalem), list(_TARIHLER)
    return list(_DONEMLER), dict(kalem)


print("")
print("1. ARDISIK DONEM ANAHTARLARI URETILIYOR")
# ISTEK ARALIGI SIFIRLANIYOR -- SINAMA BEKLEMEYI OLCMUYOR.
#
# `ara_donem` artik tablolar arasinda da `ara_ver()` cagiriyor
# (kaynak sirket basina UCLU PATLAMA goruyordu). Gercek bekleme bu
# dosyayi 12 saniyeye cikardi ve olculen seyi -- istek SAYISINI --
# hic etkilemiyor.
bilanco_ag.ARA_SN = 0

_asil = bilanco_ag.cek
bilanco_ag.cek = _sahte_cek
try:
    _cagri["n"] = 0
    _t = bilanco_ag.ara_donem("TEST", 1, bugun=None)
finally:
    bilanco_ag.cek = _asil

# ATILLIK: once sahte kaynagin GERCEKTEN kullanildigini goster.
# Hicbir cagri olmasaydi asagidaki iddialarin hepsi bos olurdu.
esit(_cagri["n"] > 0, True, f"sahte kaynak kullanildi ({_cagri['n']} cagri)")
esit("gelir" in _t, True, "su anki donem uretildi")
for _i in (1, 2, 3):
    esit(f"gelir_g{_i}" in _t, True, f"gelir_g{_i} anahtari var")
esit("gelir_g4" in _t, False,
     f"GERIYE_DONEM={bilanco_ag.GERIYE_DONEM} disina cikilmiyor")

# KAYDIRMA GERCEKTEN KAYIYOR. Ayni degeri dondurse de anahtarlar
# var olurdu; olcut DEGERIN kendisi.
esit(_t["gelir"]["Revenue"], 100.0, "su anki donem en yeni ceyrek")
esit(_t["gelir_g1"]["Revenue"], 90.0, "bir onceki ceyrek")
esit(_t["gelir_g3"]["Revenue"], 70.0, "uc onceki ceyrek")

esit(_t.get("_seri_bitis"), ["2026-09-30", "2026-06-30",
                             "2026-03-31", "2025-12-31"],
     "bitis tarihleri sirayla")

print("")
print("1b. GELIR TABLOSU EKSIK GECMIS DONEM SERIDEN DUSUYOR")
# URETIMDE COKTU (kosu #55, 2026-10-29):
#
#     TypeError: Donem.__init__() missing 1 required positional
#                argument: 'hasilat'
#
# Suzgec "hasilat YA DA aktif_toplami" diyordu; `Donem` ise
# `hasilat`i ZORUNLU istiyor. Gecmis bir ceyrekte bilanco tablosu
# gelip gelir tablosu gelmezse kosul geciyor, nesne kurulamiyor.
#
# Ilk sinamam iki alani da DOLU verdigi icin bu yolu HIC yurumedi.
# Burada gelir tablosu BILEREK kisa: en yeni iki ceyrek var, daha
# eskisi yok -- bilanco tablosunda ise dordu de var.
# `yeterli()` cekirdek + SEKTOR EKI ariyor; "Bilisim" secildi cunku
# stok beklemiyor (bkz. `SEKTOR_EK`). Eksiklik SADECE gecmis
# donemlerin GELIR tablosunda olsun istiyoruz.
_GELIR_KISA = {"Revenue": [100.0, 90.0, None, None, None],
               "Net Income": [10.0, 9.0, None, None, None],
               "Gross Profit": [40.0, 36.0, None, None, None],
               "Operating Income": [20.0, 18.0, None, None, None]}
_BILANCO_TAM = dict(_BILANCO)
_BILANCO_TAM["Total Current Assets"] = [300.0, 290.0, 280.0, 270.0, 260.0]
_BILANCO_TAM["Total Current Liabilities"] = [150.0, 145.0, 140.0, 135.0,
                                             130.0]


def _kisa_cek(kod, sayfa="gelir", istemci=None, tarih_de=False):
    kalem = _GELIR_KISA if sayfa == "gelir" else _BILANCO_TAM
    if tarih_de:
        return list(_DONEMLER), dict(kalem), list(_TARIHLER)
    return list(_DONEMLER), dict(kalem)


_asil2 = bilanco_ag.cek
bilanco_ag.cek = _kisa_cek
try:
    _s, _o, _e, _dz = bilanco_ag.donem_getir(
        "KISA", "2026 3. çeyrek", sektor_tr="Bilişim",
        ciftli=True, seri=True)
except TypeError as _hata:
    bilanco_ag.cek = _asil2
    print(f"  DUSTU  gelir tablosu eksik donemde COKUYOR: {_hata}")
    raise SystemExit(1)
finally:
    bilanco_ag.cek = _asil2

# ATILLIK: veri gercekten uretilmis olmali, yoksa "cokmedi" iddiasi
# bos bir yoldan geciyor demektir.
esit(_s is not None, True, "su anki donem kuruldu")
esit(len(_dz) >= 1, True, f"seri bos degil ({len(_dz)} donem)")
# Hasilati OLMAYAN donemler seriye GIRMEMELI.
esit(all(d.hasilat is not None for _a, _i, d in _dz), True,
     "seride hasilatsiz donem YOK")
esit(len(_dz), 2, f"yalnizca hasilati olan iki donem ({len(_dz)})")

# SIFIR HASILAT MESRU BIR OLCUM -- ELENMEMELI.
#
# "Hasilat yok" ile "hasilat sifir" ayri seyler. Olcut `is None`
# yerine dogruluk denetimi olsaydi (`if not alan.get("hasilat")`),
# satis yapmayan bir ceyrek seriden sessizce DUSER ve okur o
# ceyregi hic gormezdi. Mutasyon bunu bir kez KACIRDI.
_GELIR_SIFIR = {"Revenue": [100.0, 0.0, 80.0, 70.0, 60.0],
                "Net Income": [10.0, -5.0, 8.0, 7.0, 6.0],
                "Gross Profit": [40.0, 0.0, 32.0, 28.0, 24.0],
                "Operating Income": [20.0, -6.0, 16.0, 14.0, 12.0]}


def _sifir_cek(kod, sayfa="gelir", istemci=None, tarih_de=False):
    kalem = _GELIR_SIFIR if sayfa == "gelir" else _BILANCO_TAM
    if tarih_de:
        return list(_DONEMLER), dict(kalem), list(_TARIHLER)
    return list(_DONEMLER), dict(kalem)


bilanco_ag.cek = _sifir_cek
try:
    _s2, _o2, _e2, _dz2 = bilanco_ag.donem_getir(
        "SIFIR", "2026 3. çeyrek", sektor_tr="Bilişim",
        ciftli=True, seri=True)
finally:
    bilanco_ag.cek = _asil2

esit(len(_dz2), 4, f"dort donemin dordu de seride ({len(_dz2)})")
esit([d.hasilat for _a, _i, d in _dz2], [100.0, 0.0, 80.0, 70.0],
     "hasilati SIFIR olan donem seride DURUYOR")

print("")
print("2. EK ISTEK YOK")
# Seri eklenmeden once sayfa basina BIR istek yapiliyordu. Bu sayi
# DEGISMEMELI: seri ayni cekimden turetiliyor.
esit(_cagri["n"], len(bilanco_ag.SAYFALAR),
     f"tablo basina tek istek ({_cagri['n']} istek, "
     f"{len(bilanco_ag.SAYFALAR)} tablo)")

print("")
print("3. BICIM HER YOLDA KORUNUYOR")
# `seri=True` istendiginde demet uzunlugu, veri eksik olsa DA ayni
# olmali -- yoksa "eksik" dalinda cozme hatasi verir ve veri
# eksikligi COKMEYE donusur.
bilanco_ag.cek = lambda *a, **k: ([], {}, []) if k.get("tarih_de") else ([], {})
try:
    _bos = bilanco_ag.donem_getir("YOK", "2026 3. çeyrek",
                                  sektor_tr="Sanayi", ciftli=True, seri=True)
    esit(len(_bos), 4, "veri yokken de dortlu demet")
    esit(_bos[0], None, "donem None")
    esit(_bos[3], [], "seri bos liste")
    _bos2 = bilanco_ag.donem_getir("YOK", "2026 3. çeyrek",
                                   sektor_tr="Sanayi", seri=True)
    esit(len(_bos2), 3, "ciftli degilken uclu demet")
finally:
    bilanco_ag.cek = _asil

print("")
print("4. GOVDE: BOLUM YAZILIYOR VE BIRINCI SUTUN OLCUM TABLOSUYLA AYNI")


class _D:
    """Tek donem -- yalnizca sayfanin okudugu alanlar."""

    def __init__(self, hasilat, net_kar):
        self.hasilat = hasilat
        self.net_kar = net_kar
        self.ozkaynak = None
        self.aktif_toplami = None
        self.brut_kar = self.favok = self.faaliyet_kari = None
        self.net_borc = None
        self.faaliyet_nakit_akisi = self.yatirim_harcamasi = None


_simdi = _D(100e9, 10e9)
_seri = [("2026 3. çeyrek", "2026-09-30", _simdi),
         ("2026 2. çeyrek", "2026-06-30", _D(90e9, 9e9)),
         ("2026 1. çeyrek", "2026-03-31", _D(80e9, 8e9)),
         ("2025 4. çeyrek", "2025-12-31", _D(70e9, 7e9))]

_g = US.govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026 3. çeyrek",
                  _simdi, {}, {}, 0, "Örnek yorum.", seri=_seri)

esit("## Son dört dönem" in _g, True, "bolum basligi yazildi")
for _ad in ("2026 2. çeyrek", "2025 4. çeyrek"):
    esit(_ad in _g, True, f"sutun basligi: {_ad}")

# OZDESLIK: seri ile olcum tablosu AYRI yollardan geliyor. Ayrisirlarsa
# sayfa ayni baslikta IKI AYRI DONEM anlatir -- bu depo o kusuru bir
# kez yasadi (258 sayfanin 203'u).
_satir = [l for l in _g.splitlines() if l.startswith("| Hasılat |")]
esit(len(_satir), 2, "hasilat iki tabloda da var (olcum + seri)")
_olcum = _satir[0].split("|")[2].strip()
_seri_ilk = _satir[1].split("|")[2].strip()
esit(_olcum.startswith(_seri_ilk), True,
     f"birinci sutun olcum tablosuyla AYNI ({_seri_ilk} / {_olcum})")

print("")
print("5. TEK DONEMDE BOLUM YAZILMIYOR")
# Tek sutunluk bir "egilim" tablosu olcum tablosunu tekrar etmekten
# baska bir sey yapmaz ve egilim oldugu izlenimi verir.
_tek = US.govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026 3. çeyrek",
                    _simdi, {}, {}, 0, "Örnek yorum.", seri=_seri[:1])
esit("## Son dört dönem" in _tek, False, "tek donemde bolum YOK")
_hic = US.govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026 3. çeyrek",
                    _simdi, {}, {}, 0, "Örnek yorum.")
esit("## Son dört dönem" in _hic, False, "seri verilmezse bolum YOK")
# ATILLIK: iddianin anlamli olmasi icin bolumun yazilabildigi de
# gosterilmeli -- yukarida gosterildi, burada kiyas icin tutuluyor.
esit(len(_g) > len(_tek), True, "seri bolumu govdeyi gercekten buyutuyor")

print("")
print("6. URETIM ZINCIRI SERIYI GECIRIYOR")
# Kaynak dogru uretse de `sirket_isle` istemezse bolum OLU kalir.
# Olcut AST: metin aramak bicimlendirme degisince sessizce eslesmeyi
# birakiyor (bu depoda iki kez oldu).
import ast                                              # noqa: E402

_ag = ast.parse(pathlib.Path(US.__file__).read_text(encoding="utf-8"))
_getir = [c for c in ast.walk(_ag) if isinstance(c, ast.Call)
          and isinstance(c.func, ast.Attribute)
          and c.func.attr == "donem_getir"]
esit(len(_getir), 1, "tek donem_getir cagrisi")
# DEGERE BAKILIYOR, ANAHTARIN VARLIGINA DEGIL.
#
# Ilk yazim `any(k.arg == "seri")` diyordu ve MUTASYON KACTI:
# `seri=False` yazildiginda anahtar hala oradaydi, iddia hala
# dogruydu ve seri OLU kaliyordu. Bir anahtarin bulunmasi, istenen
# davranisin istendigi anlamina gelmiyor.
_sk = [k for k in _getir[0].keywords if k.arg == "seri"]
esit(len(_sk), 1, "cekim cagrisinda seri anahtari var")
esit(isinstance(_sk[0].value, ast.Constant) and _sk[0].value.value is True,
     True, "cekim seri=True istiyor (deger DOGRU)")
_govde = [c for c in ast.walk(_ag) if isinstance(c, ast.Call)
          and isinstance(c.func, ast.Name) and c.func.id == "govde_kur"]
esit(any(any(k.arg == "seri" for k in c.keywords) for c in _govde), True,
     "govde_kur seriyi aliyor")

print("")
print("7. BOLUM GOCU KUYRUGU -- KORUMAYI BESLEMIYOR")
# Var olan 275 sayfa bolumu tasimiyor. Bunu
# `bilanco_denetim.onarim_gereken`e bir "eksiklik" olarak eklemek
# CAZIPTI ve YANLIS olurdu: o islev ayni anda
# `site/test_bilanco_sayfa_saglam.py` korumasini besliyor, yani 275
# sayfa BIR ANDA bozuk ilan edilir ve CI kirmiziya donerdi -- site
# dagitilmazdi. Bolumun yoklugu bir KUSUR degil, bir GOC.
import tempfile                                          # noqa: E402

import bilanco_denetim as _bd                            # noqa: E402
import bilanco_tazele as BT                              # noqa: E402

_ON = """---
slug: x
baslik: X A.S. 2026 2. ceyrek bilanco analizi
kod: {kod}
donem: 2026 2. çeyrek
kategori: Bilanço Analizi
tarih: 2026-08-26
---

## Özet

Bir cümle.

{kiyas}

| Oran | Şirket | Sektör medyanı |
| --- | ---: | ---: |
| Net kâr marjı | %1,0 | %2,0 |
{ek}
"""

with tempfile.TemporaryDirectory() as _t:
    _d = pathlib.Path(_t)
    (_d / "eksik.md").write_text(_ON.format(kod="AAA", ek="", kiyas=US.KIYAS_BASLIGI),
                                 encoding="utf-8")
    _seri_ek = (NL + US.SERI_BASLIGI + NL + NL + "| a | b |" + NL)
    (_d / "var.md").write_text(
        _ON.format(kod="BBB", ek=_seri_ek, kiyas=US.KIYAS_BASLIGI), encoding="utf-8")
    _haber = ("---" + NL + "kategori: Haber" + NL + "kod: CCC"
              + NL + "---" + NL + NL + "Metin." + NL)
    (_d / "haber.md").write_text(_haber, encoding="utf-8")
    _asil_site = US.SITE
    US.SITE = _d
    try:
        _k = BT.goc_kuyrugu({}, None)
    finally:
        US.SITE = _asil_site
    _adlar = sorted(y.name for y, _s in _k)
    # ATILLIK: tarama gercekten dosya gormus olmali. Bos bir dizinde
    # "bolumu olan sayfa kuyruga girmiyor" DOGRUDUR ve hicbir sey
    # soylemez -- bu depoda mesru sifiri kusur sayan kontroller
    # dagitimi durdurdu.
    esit(len(_adlar) > 0, True, f"kuyruk bos degil ({_adlar})")
    esit(_adlar, ["eksik.md"], "yalnizca bolumu OLMAYAN bilanco sayfasi")

# OLCUT URETILEN BASLIKLA AYNI OLMALI.
#
# Kuyruk `US.SERI_BASLIGI` ariyor, govde o sabiti yaziyor. Ikisi
# ayrisirsa kuyruk BUTUN sayfalari eksik sayar ve her kosuda hepsini
# yeniden kurar -- sessiz, sonsuz bir is. Bu iddia ikisini baglar.
esit(US.SERI_BASLIGI in _g, True,
     f"uretilen govde kuyrugun aradigi basligi tasiyor ({US.SERI_BASLIGI})")
esit(_g.count(US.SERI_BASLIGI), 1, "baslik govdede TEK kez")

# KORUMA ETKILENMEMELI: bolumu olmayan bir sayfa "onarim gereken"
# sayilmamali, yoksa CI kirmiziya doner.
_eksik_sayfa = _ON.format(kod="AAA", ek="", kiyas=US.KIYAS_BASLIGI)
esit(_bd.bilanco_sayfasi(_eksik_sayfa), True, "ornek bir bilanco sayfasi")
esit([s for s in _bd.onarim_gereken(_eksik_sayfa)
      if "dört dönem" in s or "dort donem" in s], [],
     "bolum eksikligi ONARIM SEBEBI sayilmiyor")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
