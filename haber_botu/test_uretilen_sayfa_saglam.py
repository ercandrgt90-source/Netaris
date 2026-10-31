# -*- coding: utf-8 -*-
"""URETTIGIMIZ SAYFA KENDI DENETIMIMIZDEN GECMELI.

BU DOSYA NEDEN VAR
------------------
`site/test_bilanco_sayfa_saglam.py` YAYINDAKI sayfalari denetliyor
ve eski bozuk sayfalar icin bir miras listesi tutuyor. Ama o koruma
"yeni uretilen sayfa saglam mi" sorusunu ancak sayfa YAZILDIKTAN
SONRA ve bir CI kosusu gecikmesiyle cevapliyor.

Bu sinama ayni soruyu URETIM ANINDA soruyor: `govde_kur` ciktisini
dogrudan `bilanco_denetim.onarim_gereken`e veriyor. Yani uretici ile
denetleyici ayni masada.

NEDEN YAPISAL OLARAK SAGLAM OLMALI -- OLCULDU (2026-10-13)
----------------------------------------------------------
Sayfanin seviye tablosu `donem_getir`den gelen `d`den, oran tablosu
ise `sektor_ozet.json`dan geliyordu. Iki ayri kaynak, iki ayri
vintage, bazen iki ayri DONEM: 258 bilanco sayfasinin 203'u seviye
tablosundan hesaplanan oranla yazili orani uyusturmuyordu.

Ara donemin kac ceyrekten olustugunu tek kaynaga baglamak kusuru
KURAL duzeyinde kapatti. Sonra oran, sayfanin gosterdigi tablonun ta
kendisinden turetildi -- yani ayrilmasi YAPISAL olarak imkansiz
hale geldi. Bu sinama o iddianin kendisi.

AG KULLANILMIYOR, MODEL CAGRISI YOK.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bilanco_denetim as bd                       # noqa: E402
import oranlar                                     # noqa: E402
import uret_bilanco as U                           # noqa: E402
import uret_bilanco_sayfa as US                    # noqa: E402

#: Satir sonu ELDE kuruluyor -- bu dosya here-doc ile
#: yazildiginda kacisli satir sonu gercek satir sonuna donusup
#: dizgeyi kapanmamis birakiyor; tuzak depoda kayitli.
SATIR_SONU = chr(10)


def sayfa(govde, donem: str = "2026 2. çeyrek") -> str:
    """Govdeyi GERCEK SAYFA haline getirir: on bilgi + govde.

    NEDEN GEREKLI. `govde_kur` yalnizca GOVDEYI uretiyor; on bilgiyi
    `yayin.yaz_sektorel` ekliyor. Denetim ise diskteki DOSYAYI
    okuyor, yani her zaman on bilgili metni goruyor
    (`bilanco_tazele.onarim_kuyrugu`: `metin = yol.read_text(...)`).

    Ciplak govdeyi denetlemek, uretimde HIC olusmayan bir girdiyle
    olcmek demekti: `bilanco_denetim.bilanco_sayfasi` sayfayi
    ON BILGIDEKI `kategori` alanindan taniyor ve ciplak govdede o
    alan yok. Kategori burada LITERAL yaziliyor; kanonik sabitle
    ayni oldugu `test_bilanco_sayfa_olcutu.py` icinde tutuluyor.
    """
    metin = govde if isinstance(govde, str) else SATIR_SONU.join(govde)
    on = ["---", "slug: x", "kod: KOD", f"donem: {donem}",
          "kategori: Bilanço Analizi", "tarih: 2026-10-31", "---", ""]
    return SATIR_SONU.join(on) + metin


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


#: Gercekci sinir durumlari. Hepsi bir sayfa uretmeli VE uretilen
#: sayfa denetimden gecmeli.
DURUMLAR = (
    ("normal sanayi", "Sanayi", "Conglomerates", dict(
        hasilat=12_400_000_000.0, brut_kar=2_100_000_000.0,
        faaliyet_kari=900_000_000.0, net_kar=640_000_000.0,
        ozkaynak=8_300_000_000.0, aktif_toplami=19_700_000_000.0,
        donen_varliklar=7_100_000_000.0,
        kisa_vadeli_yukumlulukler=5_400_000_000.0,
        stoklar=2_200_000_000.0, ticari_alacaklar=1_800_000_000.0,
        faaliyet_nakit_akisi=1_050_000_000.0)),
    ("zarar eden sirket", "Bilişim", "Software - Application", dict(
        hasilat=1_870_000_000.0, brut_kar=82_000_000.0,
        faaliyet_kari=-190_000_000.0, net_kar=-269_000_000.0,
        ozkaynak=3_330_000_000.0, aktif_toplami=6_300_000_000.0,
        donen_varliklar=2_400_000_000.0,
        kisa_vadeli_yukumlulukler=890_000_000.0)),
    ("NEGATIF OZKAYNAK", "Temel tüketim", "Grocery Stores", dict(
        hasilat=4_200_000_000.0, brut_kar=640_000_000.0,
        faaliyet_kari=120_000_000.0, net_kar=-282_000_000.0,
        ozkaynak=-220_000_000.0, aktif_toplami=5_100_000_000.0,
        donen_varliklar=1_300_000_000.0,
        kisa_vadeli_yukumlulukler=2_600_000_000.0)),
    ("futbol kulubu (brut kar negatif)", "İletişim", "Entertainment", dict(
        hasilat=1_000_000_000.0, brut_kar=-794_000_000.0,
        faaliyet_kari=-880_000_000.0, net_kar=-610_000_000.0,
        ozkaynak=240_000_000.0, aktif_toplami=5_600_000_000.0,
        donen_varliklar=420_000_000.0,
        kisa_vadeli_yukumlulukler=1_900_000_000.0)),
    ("cok kucuk tutarlar", "Sağlık", "Biotechnology", dict(
        hasilat=38_000_000.0, brut_kar=9_000_000.0,
        faaliyet_kari=1_000_000.0, net_kar=600_000.0,
        ozkaynak=71_000_000.0, aktif_toplami=94_000_000.0,
        donen_varliklar=40_000_000.0,
        kisa_vadeli_yukumlulukler=22_000_000.0)),
)

#: Medyan, kiyas kumesinden geliyor; iceriginin bu sinamayla ilgisi
#: yok, var olmasi yeterli.
MEDYAN = {"brut_marj": 14.9, "net_marj": 0.3, "roe": 1.3,
          "cari_oran": 1.24, "borc_ozkaynak": -0.04}

print("")
print("1. Uretilen sayfa KENDI denetimimizden geciyor")
for ad, sektor, alt, alanlar in DURUMLAR:
    d = oranlar.Donem(etiket="2026 2. çeyrek", **alanlar)
    # ORAN SAYFANIN KENDI VERISINDEN -- uretimdeki yolun aynisi.
    oran = U._oranlari(d)
    govde = US.govde_kur("KOD", "Örnek Şirket A.Ş.", sektor,
                         "2026 2. çeyrek", d, oran, MEDYAN, 12,
                         "Örnek yorum cümlesi.", alt_sektor=alt)
    metin = sayfa(govde)
    esit(bd.bilanco_sayfasi(metin), True, f"{ad}: bilanço sayfası üretildi")
    esit(bd.onarim_gereken(metin, {"sektor_tr": sektor,
                                   "alt_sektor": alt}), [],
         f"{ad}: denetimden SORUNSUZ geçiyor")

print("")
print("2. Olcum araci calisiyor: ORAN BASKA KAYNAKTAN gelirse DUSUYOR")
# Bu madde sinamanin kendisini sinıyor. Oran sayfanin verisinden
# DEGIL baska bir donemden gelirse denetim bunu GORMELI; gormuyorsa
# birinci madde bos bir jesttir.
_d = oranlar.Donem(etiket="2026 2. çeyrek", **DURUMLAR[0][3])
_baska = dict(U._oranlari(_d))
_baska["brut_marj"] = _baska["brut_marj"] * 2.3      # baska bir donem
_g = US.govde_kur("KOD", "Örnek Şirket A.Ş.", "Sanayi", "2026 2. çeyrek",
                  _d, _baska, MEDYAN, 12, "Örnek yorum.",
                  alt_sektor="Conglomerates")
_m = sayfa(_g)
_sebep = bd.onarim_gereken(_m, {"sektor_tr": "Sanayi",
                                "alt_sektor": "Conglomerates"})
esit(bool(_sebep), True, "başka dönemden gelen oran YAKALANIYOR")
esit(_sebep[0].startswith("dönem tutarsız"), True, "sebebi doğru adlanıyor")

print("")
print("3. Negatif ozkaynakta ROE sayfaya HIC yazilmiyor")
_nd = oranlar.Donem(etiket="2026 2. çeyrek", **DURUMLAR[2][3])
_no = U._oranlari(_nd)
esit("roe" in _no, False, "oran kümesinde roe YOK")
_ng = US.govde_kur("KOD", "Örnek Şirket A.Ş.", "Temel tüketim",
                   "2026 2. çeyrek", _nd, _no, MEDYAN, 12, "Yorum.",
                   alt_sektor="Grocery Stores")
_nm = _ng if isinstance(_ng, str) else "\n".join(_ng)
esit("Özkaynak kârlılığı" in _nm, False,
     "sayfada ROE satırı YOK (anlamsız olurdu)")
esit(bd.ozkaynak_celiskisi(_nm), "", "çelişki denetimi de temiz")

print("")
print("4. Kapsam disi kilavuz uretilen sayfaya GIRMIYOR")
_kd = oranlar.Donem(etiket="2026 2. çeyrek", **DURUMLAR[3][3])
_kg = US.govde_kur("FENER", "Örnek Kulüp A.Ş.", "İletişim",
                   "2026 mart–mayıs dönemi", _kd, U._oranlari(_kd),
                   MEDYAN, 4, "Yorum.", alt_sektor="Entertainment",
                   mali_not="Şirketin mali yılı mayıs sonunda bitiyor.")
_km = _kg if isinstance(_kg, str) else "\n".join(_kg)
esit("Telekomünikasyonda" in _km, False,
     "futbol kulübüne telekom kılavuzu yazılmıyor")
esit("mali yılı mayıs sonunda bitiyor" in _km, True,
     "mali takvim açıklaması sayfada")
esit("aynı dönemi bildiren" in _km, True,
     "kıyas cümlesi doğru ifadeyi taşıyor")

print("")
print("5. KIYAS KUMESI YOKSA SAYFA YINE CIKAR -- bolum YAZILMAZ")
#
# OLCULDU (2026-10-14): spor kuluplerinin mali yillari ayni ama AYNI
# UC AYI bildirmiyorlar. GSRAY ve BJKAS haziran-agustos bilancosunu
# acikladi, FENER ve TSPOR hala mart-mayista:
#
#   2026-08-31 -> GSRAY, BJKAS   (2 sirket)
#   2026-05-31 -> FENER, TSPOR   (2 sirket)
#
# Her grup `sektor_ozet.EN_AZ_SIRKET` esigi altinda, yani medyan
# URETILMIYOR. Onceki kural sayfayi tumden atliyordu ve GSRAY'in
# aciklanmis bilancosu haftalarca yayimlanmadan kalirdi.
#
# Kullanici karari (2026-10-14): sektor karsilastirmasi olmadan
# yayimla. Sayfanin geri kalani kiyasa bagli degil.
_kd = oranlar.Donem(
    etiket="2026 haziran–ağustos", hasilat=820_000_000.0,
    brut_kar=-640_000_000.0, faaliyet_kari=-710_000_000.0,
    net_kar=-480_000_000.0, ozkaynak=380_000_000.0,
    aktif_toplami=6_100_000_000.0, donen_varliklar=520_000_000.0,
    kisa_vadeli_yukumlulukler=2_900_000_000.0)
_kg = US.govde_kur("GSRAY", "Örnek Kulüp A.Ş.", "İletişim",
                   "2026 haziran–ağustos", _kd, U._oranlari(_kd),
                   {}, 0, "Örnek yorum.", alt_sektor="Entertainment",
                   mali_not="Şirketin mali yılı mayıs sonunda bitiyor.")
_km = _kg if isinstance(_kg, str) else SATIR_SONU.join(_kg)
esit("## Sektör içindeki konum" in _km, False,
     "kıyas tablosu bölümü YAZILMIYOR")
esit("## Sektör karşılaştırması bu dönem yapılmadı" in _km, True,
     "yerine SEBEBİ yazılıyor")
esit("| —" in _km, False,
     "boş medyan sütunu YOK (kıyas yapılmış izlenimi vermiyor)")
esit("Yukarıdaki" in _km, True, "yön doğru (o bölümler yukarıda)")
esit("Aşağıdaki **bir yıl" in _km, False, "yanlış yön kullanılmıyor")
# SAYFANIN GERI KALANI DURUYOR: olcum tablosu ve kulup kilavuzu.
esit("dönemi ölçümleri" in _km, True, "ölçüm tablosu duruyor")
esit("Futbol kulübü" in _km, True, "kulüp kılavuzu duruyor")
esit("Örnek yorum." in _km, True, "AI yorumu duruyor")
# VE KENDI DENETIMIMIZDEN GECIYOR.
#
# BU IDDIA ESKIDEN BOSTA DONUYORDU: kiyas bolumu olmadigi icin
# `onarim_gereken` ilk satirda cikip BOS liste veriyordu, yani
# "sorunsuz geciyor" sonucu denetimden DEGIL, denetime hic
# girilmemesinden geliyordu. On bilgi eklenince kontrol gercekten
# kosuyor (bkz. `test_bilanco_sayfa_olcutu.py`).
_kms = sayfa(_kg, donem="2026 haziran–ağustos")
esit(bd.bilanco_sayfasi(_kms), True,
     "kıyassız sayfa DENETIME GIRIYOR")
esit(bd.onarim_gereken(_kms, {"sektor_tr": "İletişim",
                              "alt_sektor": "Entertainment"}), [],
     "kıyassız sayfa da denetimden SORUNSUZ geçiyor")

# MEDYAN VARSA eski davranis: kiyas tablosu yaziliyor.
_vg = US.govde_kur("TTKOM", "Örnek A.Ş.", "İletişim", "2026 2. çeyrek",
                   _kd, U._oranlari(_kd), MEDYAN, 3, "Yorum.",
                   alt_sektor="Telecom Services")
_vm = _vg if isinstance(_vg, str) else SATIR_SONU.join(_vg)
esit("## Sektör içindeki konum" in _vm, True,
     "medyan varsa kıyas tablosu YAZILIYOR")
esit("## Sektör karşılaştırması bu dönem yapılmadı" in _vm, False,
     "o durumda açıklama bölümü yok")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
