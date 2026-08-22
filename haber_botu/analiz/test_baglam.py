"""Baglam dogrulayicisi: sayi dogru mu degil, DOGRU YERDE mi.

BU DOSYA NEDEN VAR
------------------
Sayi kontrolu su soruyu soruyordu: "model bu sayiyi uydurdu mu?"
Sorulmasi gereken: "bu sayi BU HABERE ait mi?"

Fark somut olarak goruldu: Fed tutanaklari sayfasinda %31,75 yaziyordu.
Sayi gercekti (TCMB TUFE serisi), sayfada da vardi, uydurma degildi --
ama haber ABD'ydi.

Ayni sinif 2026-08 icinde uc katmanda tekrarladi (bolge
siniflandirmasi, takip kalemleri, acilis cumlesi) ve her seferinde
tek tek yamandi. Dorduncusu baska bir kombinasyonla geldi: yayimdaki
204 yorum tarandiginda 11 uyusmazlik cikti ve iceride bir de ECB
haberi vardi -- yani tek tek yamamanin bu sinifi bitirmedigi
olculerek gorundu.

Sinamalar IKI YONU birlikte tutuyor:
  * yabanci haberde yerli veri  -> YAKALANMALI
  * mesru "etkisi" anlatimi     -> YAKALANMAMALI
Ikincisi olmadan suzgec, sitenin en degerli icerigini (Fed karari
Turkiye'yi nasil etkiler) engellerdi.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from analiz import baglam  # noqa: E402

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
# ULKE COZUMLEME
# --------------------------------------------------------------------
esit(baglam.seri_ulkesi("TP.TUKFIY2025.GENEL"), "TR", "TP.* onegi -> TR")
esit(baglam.seri_ulkesi("CPIAUCNS"), "US", "ABD TUFE -> US")
esit(baglam.seri_ulkesi("DCOILBRENTEU"), "GLOBAL", "Brent -> GLOBAL")
esit(baglam.seri_ulkesi("BILINMEYEN_KOD"), "", "bilinmeyen -> karar yok")

esit(baglam.haber_ulkesi("Herhangi bir baslik", "Fed"), "US",
     "kurum en guclu isaret")
esit(baglam.haber_ulkesi("BoJ faiz artiracak mi?", "Ekonomim"), "JP",
     "basliktan ulke")
esit(baglam.haber_ulkesi("Rastgele bir baslik", "Ekonomim", "TR"), "TR",
     "isaret yoksa bolge")
esit(baglam.haber_ulkesi("Rastgele bir baslik", "Ekonomim", "DUNYA"), "",
     "DUNYA bir ulke DEGIL -- karar verilmiyor")


# --------------------------------------------------------------------
# UYUSMAZLIK -- gercek depoya karsi.
#
# Depo yoksa bu blok atlaniyor: testin CI disinda da calisabilmesi
# gerekiyor ve depo bir kaynak dosyasi degil, uretilen veri.
# --------------------------------------------------------------------
if baglam.DEPO.exists():
    _b = sqlite3.connect(f"file:{baglam.DEPO}?mode=ro", uri=True)

    def _var(metin, baslik, kurum="", bolge=""):
        return baglam.uyusmazlik(_b, metin, baslik, kurum, bolge) is not None

    # YAKALANMALI: yabanci haber, bastan sona yerli veri.
    esit(_var("Temmuz 2026 verisine göre TÜFE yıllık %31,75; "
              "çekirdek enflasyon %29,91.",
              "Fed tutanakları: birkaç üye faiz artışını savundu",
              "Ekonomim", "DUNYA"),
         True, "ABD haberi + yalniz TR verisi -> uyusmazlik")

    esit(_var("ABD işsizlik oranı %4,10 seviyesinde.",
              "TCMB faizi sabit tuttu", "TCMB", "TR"),
         True, "TR haberi + yalniz US verisi -> uyusmazlik")

    # YAKALANMAMALI: haberin kendi ulkesinden veri var.
    esit(_var("ABD politika faizi %3,63 seviyesinde.",
              "Fed tutanakları", "Ekonomim", "DUNYA"),
         False, "ABD haberi + ABD verisi -> temiz")

    # YAKALANMAMALI: mesru "etkisi" anlatimi -- iki ulke birlikte.
    # Bu sinama olmadan suzgec sitenin en degerli icerigini engeller.
    esit(_var("ABD politika faizi %3,63; Türkiye'de TÜFE %31,75 ile "
              "ayrışmayı sürdürüyor.",
              "Fed kararı Türkiye piyasalarını nasıl etkiler",
              "Ekonomim", "DUNYA"),
         False, "iki ulke birlikte -> etkisi anlatimi, temiz")

    # YAKALANMAMALI: emtia her yerde serbest.
    esit(_var("Brent petrol 95,29 $ seviyesinde.",
              "Brent petrol yükselişini sürdürüyor", "Investing", "DUNYA"),
         False, "GLOBAL seri -> her haberde serbest")

    # YAKALANMAMALI: haberin ulkesi bilinmiyorsa karar verilmiyor.
    esit(_var("TÜFE yıllık %31,75.", "Belirsiz bir başlık",
              "Investing", "DUNYA"),
         False, "haber ulkesi bilinmiyor -> karar yok")

    # HASSASIYET: metin yuvarlanmis deger yaziyor, depo ham deger tutuyor.
    # Ilk yazimimda tam eslesme aradim ve asil vaka KACTI:
    #   depo 31.75409679  /  metin 31,75
    esit(baglam.seri_ulkesi(
        next(iter(baglam.sayiyi_coz(_b, 31.75, 2)), "")), "TR",
        "yuvarlanmis deger ham seriye baglaniyor")

# --------------------------------------------------------------------
# ULKE ADI KURUM ADINDAN ONCE GELIR.
#
# OLCULEN HATA (2026-08-22): "Brezilya merkez bankasi faiz indirimine
# ragmen..." haberi TR siniflandirildi; Rusya ve Cin merkez bankasi
# haberleri de. "merkez bankasi" isareti dogru ama FAZLA GENEL -- her
# ulkenin bir merkez bankasi var. Ulke adi daha belirleyici.
#
# Hata olay gruplamasini olcerken cikti: "TR:faiz:2026-08" grubunda bir
# Brezilya haberi duruyordu. Duzeltince baglam denetimi iki GERCEK
# ihlal daha buldu (Hindistan haberinde TR verisi, Rusya haberinde US
# verisi) -- yani yanlis ulke atamasi, uyusmazlik kontrolunu de kor
# birakiyordu.
# --------------------------------------------------------------------
esit(baglam.haber_ulkesi("Brezilya merkez bankası faiz indirdi"), "BR",
     "yabanci ulke + genel kurum adi -> ULKE kazanir")
esit(baglam.haber_ulkesi("Rusya Merkez Bankası faizi düşürdü"), "RU",
     "Rusya merkez bankasi -> RU")
esit(baglam.haber_ulkesi("Merkez Bankası faiz kararı ne zaman"), "TR",
     "ulke adi YOKSA genel kurum adi TR kalir")
esit(baglam.haber_ulkesi("TCMB faizi sabit tuttu"), "TR", "TCMB -> TR")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
