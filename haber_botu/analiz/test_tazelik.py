"""Veri tazeligi: seri KENDI RITMININ gerisinde mi.

BU DOSYA NEDEN VAR
------------------
Ilk olcumumde "45 gunden eski seri" diye baktim ve 24 seri cikti. Liste
yaniltiyordu: aylik TUFE'nin Temmuz verisi 1 Temmuz etiketiyle durur ve
Agustos'ta yayimlanir -- 52 gunluk gorunur ve TAMAMEN NORMALDIR.
Ceyreklik GSYH 143 gun "eski" ve o da normal.

Ham yasa bakan bir uyari, dogru calisan serileri sikayet eder ve kisa
surede gormezden gelinir. Frekansa gore olcunce 24 uyari 7'ye indi ve
iceride GERCEK bir sorun vardi:

    varlik EURUSD -> seri DEXUSEU -> son veri 31 Temmuz
    panel kalemi  -> seri ECB_EURUSD -> son veri 21 Agustos

Ayni sayfada iki farkli tarih. Panel bir donem once ECB'ye tasinmis
ama varligin `seri_kodu` cevrilmemisti; hata sessiz kaldi cunku iki
deger de "gercek", yalnizca ayni gune ait degil.

Sinamalar frekans cikariminin dogrulugunu ve donem etiketinin yayin
tarihinden ayrilmasini tutuyor.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from analiz import tazelik  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


# --------------------------------------------------------------------
# FREKANS CIKARIMI -- veriden turuyor, elle yazilmiyor.
# --------------------------------------------------------------------
esit(tazelik.frekans([1, 1, 3, 1, 1]), "gunluk", "is gunu araligi -> gunluk")
esit(tazelik.frekans([7, 7, 7]), "haftalik", "yedi gun -> haftalik")
esit(tazelik.frekans([31, 30, 31]), "aylik", "ay -> aylik")
esit(tazelik.frekans([92, 91, 92]), "ceyreklik", "ceyrek -> ceyreklik")
# MEDYAN, ORTALAMA DEGIL: tek bir uzun tatil boslugu ortalamayi
# kaydirir, medyani kaydirmaz.
esit(tazelik.frekans([1, 1, 1, 1, 40]), "gunluk",
     "tek uzun bosluk frekansi BOZMUYOR (medyan)")

# --------------------------------------------------------------------
# DONEM ETIKETI -- yayin tarihinden AYRI okunmali.
#
# Okur icin "2026-07-01" bir gun gibi gorunuyor; oysa aylik seride o
# TEMMUZ AYININ verisi. Editoryal geri bildirimde bildirilen sorun
# tam buydu: olay tarihi / veri donemi / yayin tarihi uc ayri sey.
# --------------------------------------------------------------------
esit(tazelik.donem_etiketi("2026-07-01", "aylik"), "Temmuz 2026",
     "aylik seri AY olarak yaziliyor, gun olarak degil")
esit(tazelik.donem_etiketi("2026-04-01", "ceyreklik"), "2026 2. çeyrek",
     "ceyreklik seri CEYREK olarak yaziliyor")
esit(tazelik.donem_etiketi("2026-08-20", "gunluk"), "20 Ağustos 2026",
     "gunluk seri gun olarak yaziliyor")
esit(tazelik.donem_etiketi("bozuk-tarih", "aylik"), "bozuk-tarih",
     "cozulemeyen tarih oldugu gibi doner -- uydurulmaz")

# --------------------------------------------------------------------
# BAYAT OLCUMU -- gercek depoya karsi.
# --------------------------------------------------------------------
if tazelik.DEPO.exists():
    _b = sqlite3.connect(f"file:{tazelik.DEPO}?mode=ro", uri=True)

    # Dort gozlemden az olan seride frekans OLCULEMEZ; tahmin edip
    # uyari uretmek olculmemis bir yargi olurdu.
    esit(tazelik.seri_durumu(_b, "OLMAYAN_KOD"), None,
         "bilinmeyen seri -> karar yok")

    # VARLIK->SERI TAZELIK KONTROLU BURADAN KALDIRILDI (2026-09-14).
    # Yerine `denetim.varlik_seri_tazeligi()` kondu; asagida NEDEN.
    #
    # KONTROLUN KENDISI DOGRUYDU ve gercek bir hata yakalamisti
    # (EURUSD->DEXUSEU bayat kalirken panel ECB_EURUSD kullaniyordu).
    # Yanlis olan YERIYDI.
    #
    # KISIR DONGU. `otomasyon.yml`de adim sirasi soyle:
    #
    #     Testleri calistir          <- burasi
    #     Veri topla ve icerik uret  <- seriyi TAZELEYEN adim
    #
    # Yani bu sinama, "veri bayat" diye is akisini durduruyordu --
    # veriyi tazeleyecek adimi da birlikte. Bir kez bayatlayinca
    # sistem kendi kendine ASLA toparlanamiyordu.
    #
    # OLCULDU (2026-09-14): son basarili yazma 1 Eylul 23:04. On uc
    # gun boyunca HER kosu ayni yerde dustu -- nobetci her yarim
    # saatte tetikledi, tetiklediği kosu ayni kapiya carpti. Site
    # 12,7 gun boyunca donmus icerik yayinladi. 200 donuyordu, yani
    # disaridan "calisiyor" gorunuyordu.
    #
    # KURAL: bir sinama, CALISMASI ICIN BORU HATTININ KOSMASI GEREKEN
    # bir kosulu kapi yapamaz. Veri tazeligi kodun degil, hattin
    # durumudur; yeri denetimdir (raporlar, durdurmaz), test degil.
    #
    # Asagidaki sinamalar KALDI cunku hicbiri canli veriye bagli
    # degil: frekans cikarimi ve donem etiketi saf islevler.

print("")
print("EMEKLI SERI AYRIMI -- SUSTURMA ARACINA DONUSMEMELI")
# Olculdu (2026-10-21): tazelik raporu YEDI seri bildiriyordu ve
# yedisi de artik CEKILMEYEN serilerdi -- rapor %100 yanlis alarmdi.
# Emekliler haric tutuldu.
#
# AMA bir haric tutma listesi, kirmizi bir seriyi susturmanin en
# kolay yoludur. Asagidakiler onu tutuyor -- ve TAZELIK KARARINI
# OKUMADAN tutuyor: bu depoda sinama dosyalari o karari kapi
# yapamaz (gerekce `test_isakisi.py` icinde). Olculen sey listenin
# KENDISI: neyi icerdigi ve neyi iceremeyecegi.
esit(all(str(v).strip() for v in tazelik.EMEKLI_SEBEP.values()), True,
     "her emekli serinin yazili bir sebebi var")
esit(len(tazelik.EMEKLI_SEBEP) > 0, True,
     f"emekli listesi dolu ({len(tazelik.EMEKLI_SEBEP)})")

# HALA CEKILEN BIR SERI EMEKLI SAYILAMAZ.
#
# Asil tehlike bu: hat bir seriyi cekmeye devam ederken o seri
# listeye konursa, gercek bir gecikme kalici olarak susturulmus
# olur. Cekilen kume KAYNAKTAN okunuyor, buraya yazilmiyor.
try:
    import makro_uret_ucretsiz as _mak
    _cekilen = set(_mak.SERILER) | set(_mak.PANEL_SERILERI)
    _celisen = sorted(set(tazelik.EMEKLI_SEBEP) & _cekilen)
    if _celisen:
        print(f"\n  HALA CEKILIYOR AMA EMEKLI SAYILMIS: {_celisen}")
    esit(_celisen, [], "emekli seriler artik cekilmiyor")
    esit(len(_cekilen) > 3, True,
         f"cekilen kume gercekten okundu ({len(_cekilen)})")
except ImportError:
    print("  ATLANDI  makro modulu okunamadi")

# EMEKLI SERI BIR SAYFAYI BESLEMIYOR OLMALI.
#
# `EMEKLI_SEBEP` listesindekiler YERINE BASKASI GECTIGI icin emekli.
# Biri hala bir varligin `seri_kodu` ise, o sayfa donmus veri
# gosteriyor demektir -- EURUSD vakasinin ta kendisi.
try:
    import graf_tohum as _tohum_mod
    _bagli = {s for *_a, s, _o, _ac in
              ((k, t, a, ae, s, o, ac)
               for k, t, a, ae, s, o, ac in _tohum_mod.VARLIKLAR) if s}
    _hala = sorted(set(tazelik.EMEKLI_SEBEP) & _bagli)
    if _hala:
        print(f"\n  EMEKLI AMA HALA SAYFA BESLIYOR: {_hala}")
    esit(_hala, [], "emekli seri hicbir varligi beslemiyor")
except ImportError:
    print("  ATLANDI  tohum okunamadi")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
