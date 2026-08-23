"""besleme.py testleri -- tarih cozumu, konu cikarimi, oge ayristirma.

Buradaki uc islev de HATA FIRLATMAZ. Yanlis calistiklarinda sonuc sessizce
bozulur ve ancak siteye bakinca fark edilir:

  * Tarih cozulemezse duyuru "tarihsiz" sayilip listenin dibine duser --
    TCMB'nin bugunku karari Fed'in bes gun onceki duyurusunun altinda kalir.
  * Konu bulunamazsa varsayilana duser ve habere alakasiz fotograf secilir.
  * Diakritikli yazilmis bir isaret HICBIR ZAMAN eslesmez.

Calistirma:  python kaynak/test_besleme.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import besleme  # noqa: E402

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
# GURULTU LISTESI ASCII KATLANMIS OLMALI.
#
# `gurultu_mu` basligi `_katla` ile ASCII'ye indirip karsilastiriyor.
# Turkce harf iceren bir kalip HICBIR ZAMAN eslesmez ve sessizce olu
# kalir -- eklendigi icin is gorduğu sanilir. Ilk yazimda "aranıyor"
# boyle eklenmisti.
# --------------------------------------------------------------------
_olu = [k for k in besleme.GURULTU_ISARETLERI if k != besleme._katla(k)]
esit(_olu, [], "gurultu kaliplarinin hepsi ASCII katlanmis")

# MECAZ kaliplari da ASCII katlanmis olmali -- ayni tuzak.
_olu_mecaz = [k for k, _ in besleme.MECAZ if k != besleme._katla(k)]
esit(_olu_mecaz, [], "mecaz kaliplarinin hepsi ASCII katlanmis")

# --------------------------------------------------------------------
# MECAZI "SAVAS" -- ciplak "savas" isareti Jeopolitik'te ve liste
# sirasinda Doviz'den de Sirket haberleri'nden de ONCE geliyor.
# Olculdu ve yayimlandi: "55 milyar euroluk miras savasi" jeopolitik
# sayildi ve sayfanin izleme listesi "Brent petrol, Ons altin, CDS
# primi" oldu -- bir miras davasinin altinda.
# --------------------------------------------------------------------
esit(besleme.konu_bul("55 milyar euroluk miras savaşı", "X"),
     "Şirket haberleri", "miras savasi sirket haberidir")
esit(besleme.konu_bul("Fiyat savaşı kızıştı", "X"),
     "Şirket haberleri", "fiyat savasi sirket haberidir")
esit(besleme.konu_bul("Asya-Pasifik'te kur savaşı riski", "X"),
     "Döviz", "kur savasi doviz konusudur")
esit(besleme.konu_bul("Ticaret savaşı tırmanıyor", "X"),
     "Dış ticaret", "ticaret savasi dis ticaret konusudur")

# GERCEK savas ve saldiri HALA jeopolitik: mecaz suzgeci fazla genis
# olsaydi asil konuyu kaybederdik.
esit(besleme.konu_bul("Rusya-Ukrayna savaşında yeni cephe", "X"),
     "Jeopolitik", "gercek savas jeopolitiktir")
esit(besleme.konu_bul("Hürmüz Boğazı'nda tanker saldırısı", "X"),
     "Jeopolitik", "gercek saldiri jeopolitiktir")

# --------------------------------------------------------------------
# MECAZI "YAPTIRIM" ve "ISGAL" -- ayni tuzagin iki ornegi daha.
#
# Jeopolitikte "yaptirim" ambargo demek; idari dilde para cezasi.
# Isaret listesinde CIPLAK "yaptirim" duruyordu ve olculdu:
#
#     "81 ilde kirtasiye denetimi: 367 isletmeye yaptirim"
#         -> Jeopolitik
#
# Sonucu bir etiket hatasi degildi. Sayfa jeopolitik aparatinin
# TAMAMINI aldi: "Bu neden kritik?" bolumunde petrol arz riski,
# "Piyasa" bolumunde Brent, "Kim etkilenir?" bolumunde havayolu yakit
# maliyeti, izleme listesinde CDS primi. Kirtasiye denetimi haberinde
# okurun gordugu sey buydu.
#
# "Isgal" de ayni: askeri isgal ile imar mevzuatindaki usulsuz isgal
# ayni kelime.
# --------------------------------------------------------------------
esit(besleme.konu_bul("81 ilde kırtasiye denetimi: 367 işletmeye yaptırım",
                      "X"), "Piyasa düzenlemesi",
     "isletmeye yaptirim idari duzenlemedir")
esit(besleme.konu_bul("Markete idari para cezası kesildi", "X"),
     "Piyasa düzenlemesi", "idari para cezasi jeopolitik degildir")
esit(besleme.konu_bul("Kaçak yapı ve usulsüz işgallere karşı yeni adım", "X"),
     "Konut ve kira", "usulsuz isgal imar konusudur")

# GERCEK yaptirim HALA jeopolitik -- suzgec fazla genis olmamali.
esit(besleme.konu_bul("AB, Rusya'ya yaptırımları genişletmeyi planlıyor", "X"),
     "Jeopolitik", "ulkeye yaptirim jeopolitiktir")
esit(besleme.konu_bul("ABD İran'a yeni yaptırım kararı aldı", "X"),
     "Jeopolitik", "gercek yaptirim karari jeopolitiktir")

# --------------------------------------------------------------------
# HER KONUNUN IZLEME LISTESI OLMALI.
#
# "Sirket haberleri" ve "Duzenleme" listesi BOSTU ve bos olmasi
# sessizdi: konu gecerli, fotograf havuzu var, kart turu var --
# yalnizca "Takip edilecekler" bolumu hic basilmiyordu.
# --------------------------------------------------------------------
import sys as _sys, pathlib as _pl  # noqa: E402
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent / "analiz"))
import dosya as _dosya  # noqa: E402
import foto as _foto  # noqa: E402

for _k in _foto.KONU_ARAMA:
    esit(bool(_dosya.IZLENECEKLER.get(_k)), True,
         f"'{_k}' konusunun izleme listesi var")

# Asayis/yasam gurultusu eleniyor, GERCEK jeopolitik elenmiyor.
esit(besleme.gurultu_mu("Mutfaklara bereket getiren lezzetler"), True,
     "yemek yazisi elenir")
esit(besleme.gurultu_mu("North Carolina eyaletinde silahli saldiri: 4 olu"),
     True, "asayis haberi elenir")
esit(besleme.gurultu_mu("Hurmuz Bogazi'nda tanker saldirisi"), False,
     "gercek jeopolitik elenmez")
esit(besleme.gurultu_mu("Israil Gazze'ye hava saldirisi duzenledi"), False,
     "askeri gelisme elenmez")
# Ekonomik "kayip" ELENMEMELI -- ilk yazimda "kayip" kalibi vardi ve
# sirket zarari haberlerini de eliyordu.
# --------------------------------------------------------------------
# ALT-DIZE YANLIS POZITIFI -- kalip SOZCUK BASINDAN eslesmeli.
#
# Serbest alt-dize eslesmesi GERCEK FINANS HABERINI eliyordu ve bu
# sessizdi: elenen haber hicbir yerde gorunmuyor. Uctu de olculdu.
# --------------------------------------------------------------------
esit(besleme.gurultu_mu(
        "Kizildeniz deniz tasimaciliginin onemi artiyor"),
     False, "'maci' kalibi 'tasiMACIlik' icinde eslesmemeli")
esit(besleme.gurultu_mu(
        "Cin, Kuzey Deniz Yolu uzerinden duzenli Avrupa tasimaciligi baslatti"),
     False, "ayni tuzak, ikinci baslik")
esit(besleme.gurultu_mu(
        "Trump: 3 milyar dolar degerinde bir dizi madencilik projesi"),
     False, "'bir dizi' televizyon dizisi degildir")
esit(besleme.gurultu_mu(
        "UKMTO: Tanker Hurmuz'de 2 patlama sesi duydu"),
     False, "Hurmuz'de tanker patlamasi PIYASA haberidir")
esit(besleme.gurultu_mu("Patlamada uc kisi hayatini kaybetti"),
     True, "can kaybi haberi elenir")

# Urun tanitimi ve toren -- sayfa bile uretilmisti.
esit(besleme.gurultu_mu(
        "Bebeklerin cildine pamuksu dokunus: BabyCo Bebek Urunleri 7-13 Agustos"),
     True, "urun tanitimi elenir")
esit(besleme.gurultu_mu(
        "Kultur ve Turizm Bakanligindan Cansever icin taziye mesaji"),
     True, "taziye mesaji elenir")

# "indirim" TEK BASINA kalip DEGIL: bu sitenin en merkezi konusu.
esit(besleme.gurultu_mu("Merkez bankasindan faiz indirimi karari"),
     False, "faiz indirimi elenemez")
esit(besleme.gurultu_mu("Konut kredisinde faiz kampanyasi basladi"),
     False, "kredi kampanyasi elenemez")

esit(besleme.gurultu_mu("Sirket 3. ceyrekte 2 milyar TL kayip acikladi"),
     False, "sirket zarari elenmez")
esit(besleme.gurultu_mu("Gumruk tarifesi degisikligi"), False,
     "tarife haberi elenmez")


print("\nTarih -- TCMB Turkce ay adi yaziyor, strptime cozemez")
esit(besleme._tarih_coz("30 Tem 2026 14:00:00"), "2026-07-30", "kisaltilmis ay")
esit(besleme._tarih_coz("6 Tem 2026 18:00:00"), "2026-07-06", "tek haneli gun")
esit(besleme._tarih_coz("1 Şub 2026 09:00:00"), "2026-02-01", "Ş harfi -- katlanmali")
esit(besleme._tarih_coz("3 Ağu 2026 10:00:00"), "2026-08-03", "Ğ harfi")
esit(besleme._tarih_coz("15 Ağustos 2026"), "2026-08-15", "tam ay adi da calisir")
esit(besleme._tarih_coz("11 Ara 2025 14:00:00"), "2025-12-11", "Aralik")
esit(besleme._tarih_coz("9 Eyl 2026"), "2026-09-09", "Eylul -- Ekim ile karismaz")
esit(besleme._tarih_coz("9 Eki 2026"), "2026-10-09", "Ekim -- Eylul ile karismaz")
esit(besleme._tarih_coz("5 Mar 2026"), "2026-03-05", "Mart -- Mayis ile karismaz")
esit(besleme._tarih_coz("5 May 2026"), "2026-05-05", "Mayis -- Mart ile karismaz")

print("\nTarih -- cozulemeyen BOS doner, bugun YAZILMAZ")
esit(besleme._tarih_coz("31 Nis 2026"), "", "olmayan gun (Nisan 30 cekiyor)")
esit(besleme._tarih_coz("30 Zzz 2026"), "", "olmayan ay")
esit(besleme._tarih_coz(""), "", "bos giris")
esit(besleme._tarih_coz("yakinda"), "", "tarih olmayan metin")

print("\nTarih -- yabanci bicimler bozulmadi")
esit(besleme._tarih_coz("Thu, 30 Jul 2026 09:53:38 -0400"), "2026-07-30", "RFC 822")
esit(besleme._tarih_coz("Fri, 31 Jul 2026  09:00:00 EST"), "2026-07-31", "EIA bicimi")
esit(besleme._tarih_coz("2026-07-30T10:00:00Z"), "2026-07-30", "ISO")

print("\nKatlama -- once translate, SONRA lower")
esit(besleme._katla("İSTANBUL"), "istanbul", "buyuk I noktali")
esit(besleme._katla("TÜFE"), "tufe", "U umlaut")
esit(besleme._katla("Ağustos"), "agustos", "yumusak g")
esit(besleme._katla("IŞIK"), "isik", "noktasiz i ve S cedilla")

print("\nKonu -- Turkce basliklar")
esit(besleme.konu_bul("Para Politikası Kurulu Toplantı Özeti (2026-32)", "Düzenleme"),
     "Para politikası", "PPK ozeti")
esit(besleme.konu_bul("Faiz Oranlarına İlişkin Basın Duyurusu", "Düzenleme"),
     "Para politikası", "faiz karari")
esit(besleme.konu_bul("Aylık Fiyat Gelişmeleri (Haziran 2026)", "Düzenleme"),
     "Enflasyon", "fiyat gelismeleri")
esit(besleme.konu_bul("TÜFE Aylık Değişim", "Düzenleme"),
     "Enflasyon", "TUFE -- diakritikli yazilmis")
esit(besleme.konu_bul("Ödemeler Dengesi İstatistikleri", "Düzenleme"),
     "Bankacılık", "odemeler dengesi")
esit(besleme.konu_bul("Elektrik Üretiminde Doğal Gaz Payı", "Düzenleme"),
     "Enerji", "dogal gaz")

print("\nKonu -- Ingilizce basliklar bozulmadi")
esit(besleme.konu_bul("FOMC statement", "Düzenleme"), "Para politikası", "FOMC")
esit(besleme.konu_bul("China's crude oil imports fell", "Düzenleme"), "Enerji", "crude oil")
esit(besleme.konu_bul("SEC charges firm with fraud", "Düzenleme"),
     "Piyasa düzenlemesi", "fraud")
esit(besleme.konu_bul("Hava durumu raporu", "Düzenleme"),
     "Düzenleme", "eslesme yoksa varsayilan")

print("\nKonu -- her varsayilan foto.KONU_ARAMA'da olmali")
import foto  # noqa: E402
for b in besleme.BESLEMELER:
    esit(b[4] in foto.KONU_ARAMA, True, f"{b[0]} varsayilani '{b[4]}' fotografli")
for konu, _ in besleme.KONU_ISARETLERI:
    esit(konu in foto.KONU_ARAMA, True, f"konu '{konu}' fotografli")

print("\nAtom ayristirma -- TCMB bicimi")
_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title></title>
<updated>22 Tem 2024 17:13:31</updated><entry>
<title type="text"><![CDATA[Para Politikası Kurulu Toplantı Özeti (2026-32)]]></title>
<link rel="alternate" type="text/html" href="http://www.tcmb.gov.tr/duy2026-32"></link>
<published>30 Tem 2026 14:00:00</published>
<updated>30 Tem 2026 14:00:59</updated>
<summary type="html"> </summary>
</entry></feed>"""
_o = besleme._ogeler(_ATOM)
esit(len(_o), 1, "tek entry okundu")
esit(_o[0]["baslik"], "Para Politikası Kurulu Toplantı Özeti (2026-32)", "CDATA acildi")
esit(_o[0]["adres"], "http://www.tcmb.gov.tr/duy2026-32", "Atom link href")
esit(_o[0]["tarih"], "2026-07-30", "Turkce tarih cozuldu")

print("\nBesleme tanimlari -- alan sayisi ve tekillik")
esit(all(len(b) == 7 for b in besleme.BESLEMELER), True, "hepsi 7 alanli")
_kodlar = [b[0] for b in besleme.BESLEMELER]
esit(len(_kodlar), len(set(_kodlar)), "kodlar tekil")
_adresler = [b[3] for b in besleme.BESLEMELER]
esit(len(_adresler), len(set(_adresler)), "adresler tekil")
esit(all(b[5] in ("tr", "en") for b in besleme.BESLEMELER), True, "dil tr/en")
esit(all(isinstance(b[6], bool) for b in besleme.BESLEMELER), True, "ticari bool")
esit(all(not b[6] for b in besleme.BESLEMELER
         if b[0].startswith(("TCMB", "FED", "ECB", "SEC", "EIA"))), True,
     "resmi kurumlar ticari DEGIL -- kunye zorunlulugu onlara uygulanmaz")

print("\nGurultu -- ekonomi disi oge ticari beslemede elenmeli")
for _b in ("SÜPER LOTO SONUÇ SORGULAMA EKRANI TIKLA ÖĞREN",
           "ŞANS TOPU SONUÇLARI NEREDEN SORGULANIR",
           "Sardes Antik Kenti'nde 2 bin 500 yıllık heykel bulundu",
           "NOW TV haber spikeri istifa etti",
           "Moskova'da restoranda patlama: 3 ölü, 21 yaralı",
           "İlker Ayrılık kaza mı geçirdi, sağlık durumu nasıl?",
           "15 Temmuz Şehitler Köprüsü belgesel çekimi için trafiğe kapalı"):
    esit(besleme.gurultu_mu(_b) or not besleme.konu_bul(_b, ""), True,
         f"elendi: {_b[:44]}")

print("\nGercek ekonomi haberi ELENMEMELI")
for _b, _k in (("Temmuz enflasyonu açıklandı", "Enflasyon"),
               ("Dolar endeksinde 2 ayın ardından yön aşağı döndü", "Döviz"),
               ("Borsa yeni haftaya 13.544,32 puandan başladı", "Borsa"),
               ("İhracatta tüm zamanların temmuz rekoru", "Dış ticaret"),
               ("Ağustos ayı kira zam oranları açıklandı", "Konut ve kira"),
               ("SSK ve Bağ-Kur emeklilerinin zam oranı belli oldu",
                "İstihdam ve ücret"),
               ("Turistlerden Türk mutfağına 5,9 milyar dolarlık ilgi",
                "Turizm"),
               ("Altın haftaya yükselişle başladı", "Altın ve emtia"),
               ("Kripto paraların değeri temmuzda 123 milyar dolar arttı",
                "Kripto varlıklar"),
               ("TARSİM sisteminde 1,1 trilyon liralık varlık sigortalandı",
                "Tarım ve gıda"),
               ("Elektrik santrallerine kapasite mekanizması desteği",
                "Enerji")):
    esit(besleme.konu_bul(_b, ""), _k, f"{_k}: {_b[:40]}")

print("\nOlcu birimi konu CALMAMALI -- 'dolar' ve 'kur' her baslikta gecer")
esit(besleme.konu_bul("Turistler ilk 6 ayda 6 milyar dolar harcadı", ""),
     "Turizm", "'dolar' Turizm'i calmadi")
esit(besleme.konu_bul("Yıllık ihracat 278,6 milyar dolarla rekor kırdı", ""),
     "Dış ticaret", "'dolar' Dis ticaret'i calmadi")
esit(besleme.konu_bul("SSK ve BAĞ-KUR emeklilerinin zammı belli oldu", ""),
     "İstihdam ve ücret", "'BAG-KUR' icindeki 'kur' Doviz'e dusurmedi")

print("\nTicari oge POZITIF eslesme ile girer")
esit(besleme.konu_bul("Bugün hava çok güzel", ""), "",
     "konu yoksa bos -- ticari oge alinmaz")
esit(besleme.konu_bul("Bugün hava çok güzel", "Düzenleme"), "Düzenleme",
     "resmi beslemede varsayilana duser")

print("\nAyni haber, farkli kaynak -- baslik imzasiyla tekilleme")
esit(besleme.ayni_haber_mi("Temmuz enflasyonu açıklandı",
                           "Temmuz enflasyonu açıklandı"), True,
     "birebir ayni baslik -- kisa baslikta da yakalanmali")
esit(besleme.ayni_haber_mi("İhracatta temmuz rekoru: Yıl sonu hedefi belli",
                           "İhracatta tüm zamanların temmuz rekoru"), True,
     "ayni haber, farkli kelimeler")
esit(besleme.ayni_haber_mi(
     "Turistler, Türk yemekleri için ilk 6 ayda 6 milyar dolar harcadı",
     "Turistlerden Türk mutfağına 5,9 milyar dolarlık ilgi"), True,
     "Turkce ekler govdeye kirpilinca eslesiyor")
esit(besleme.ayni_haber_mi("Altın haftaya yükselişle başladı",
                           "Borsa yeni haftaya 13.544 puandan başladı"), False,
     "iki ortak kelime yetmez -- ayri haberler")
esit(besleme.ayni_haber_mi("Temmuz enflasyonu açıklandı",
                           "Temmuzda fiyatı en çok artan ürünler"), False,
     "ayni ay, ayri haber")
esit(besleme.ayni_haber_mi("", "Temmuz enflasyonu"), False, "bos baslik")

print("\nKisa kisaltmalar kelime ICINDE eslesmemeli")
esit(besleme.konu_bul("SEC charges firm with fraud", "Düzenleme"),
     "Piyasa düzenlemesi", "'char-GES ' Enerji'ye dusurmedi")
esit(besleme.konu_bul("Billions of dollars in aid announced", ""),
     "", "'billi-ONS ' Altin'a dusurmedi")
esit(besleme.konu_bul("Company shares rose after the report", ""),
     "Borsa", "'sha-RES ' Enerji'ye dusurmedi")
esit(besleme.konu_bul("An important inflation report", ""),
     "Enflasyon", "'IMPORTant' Dis ticaret'i calmadi")
esit(besleme.konu_bul("An important announcement", ""), "",
     "'important' tek basina hicbir konuya dusmez")
esit(besleme.konu_bul("GES kurulumuna başlandı", ""), "Enerji",
     "baslikta ILK kelime olan kisaltma yine de eslesir")
esit(besleme.konu_bul("China's crude oil imports fell", "Düzenleme"),
     "Enerji", "petrol ithalati once enerji haberidir")

print("\nSik Turkce kelimeler konu CALMAMALI")
esit(besleme.konu_bul("Toprağın altında kalan 2500 yıllık heykel", ""), "",
     "'altINDA' Altin'a dusurmedi -- arkeoloji haberi emtia olmaz")
esit(besleme.konu_bul("Goldman Sachs hisse önerisini yükseltti", ""),
     "Borsa", "'GOLDman' Altin'a dusurmedi")
esit(besleme.konu_bul("Bakan Çiftçi suç çetelerine operasyon açıkladı", ""),
     "", "bakanin soyadi 'Ciftci' Tarim'a dusurmedi")
esit(besleme.konu_bul("Gram altın rekor tazeledi", ""), "Altın ve emtia",
     "gercek altin haberi hala yakalaniyor")
esit(besleme.konu_bul("Altın haftaya yükselişle başladı", ""),
     "Altın ve emtia", "yalin 'Altin' kelimesi bosluklu eslesiyor")

esit(besleme.konu_bul("Brent %41,7 yükselip geri çekildi", ""), "Enerji",
     "'B-RENT' icindeki 'rent' Konut'a dusurmedi")
esit(besleme.konu_bul("Rental prices climbed in June", ""), "Konut ve kira",
     "gercek kira haberi hala yakalaniyor")

print("\nBolge -- Turkiye / Dunya sekmesi")
for _b, _d, _bek in (
        ("Güneydoğu'nun temmuz ihracatı yüzde 19,3 arttı", "tr", "TR"),
        ("Merkez Bankası rezervlerinde artış", "tr", "TR"),
        ("Türkiye'nin ABD'ye ihracatı arttı", "tr", "TR"),
        ("Fed belirsizliği doları da vurdu", "tr", "DUNYA"),
        ("Asya borsaları haftaya karışık başladı", "tr", "DUNYA"),
        ("Tesla'nın kârı beklentilerin altında kaldı", "tr", "DUNYA"),
        ("Federal Reserve issues FOMC statement", "en", "DUNYA")):
    esit(besleme.bolge_bul(_b, _d), _bek, f"{_bek}: {_b[:42]}")
esit(besleme.bolge_bul("Altın haftaya yükselişle başladı", "tr"), "TR",
     "isaretsiz Turkce haber TR'ye duser")

print("\nKonu listesi tekil olmali")
_konular = [k for k, _ in besleme.KONU_ISARETLERI]
esit(len(_konular), len(set(_konular)),
     "mukerrer konu yok -- ikinci tanim OLU KOD olur, hic calismaz")

print("\nGovde kirpma")
esit(besleme._imza("turistler") & besleme._imza("turistlerden") != frozenset(),
     True, "'turistler' ve 'turistlerden' ayni govde")
esit("aciklandi" in besleme._ETKISIZ, True,
     "'aciklandi' ayirt edici degil -- imzadan atilir")


# --------------------------------------------------------------------
# BESLEMEDEN GELEN ISARETLEME
# --------------------------------------------------------------------
#
# Gercek olay: bir haberin ozeti ham bir TradingView gomme betigiydi ve
# okur bunu "Ne oldu?" sorusunun CEVABI olarak gordu. Sebep SIRA
# hatasiydi -- once etiket siliniyor, sonra kacis cozuluyordu; yani
# isaretleme temizlikten SONRA doguyordu.
esit(besleme._metin('&lt;script&gt;new TradingView.chart({a:"b"});&lt;/script&gt;'),
     "", "kacirilmis betik metne DONUSMUYOR")
esit(besleme._metin("&amp;lt;script&amp;gt;var x = 1;&amp;lt;/script&amp;gt;"),
     "", "cift kacirilmis besleme de temizlenir")
esit(besleme._metin("<script>var gizli = 1;</script>Asil metin burada."),
     "Asil metin burada.", "script GOVDESI de gidiyor")
esit(besleme._metin("Metin. <script>var a=1;"),
     "Metin.", "kapanmamis script satir sonuna kadar atilir")
esit(besleme._metin("Sunucu {{NewsID}} yazdi"),
     "", "cozulmemis yer tutucu ozeti bosaltir")

# YANLIS POZITIF OLMAMALI -- suzgec dar tutuldu. Haber dilinde olagan
# kaliplar (iki nokta, tirnak, yuzde, kesme isareti) DUZYAZIDIR.
esit(besleme._metin("Trump: &quot;Anlasma yakin&quot; dedi; TCMB faizi %37 seviyesinde tuttu."),
     'Trump: "Anlasma yakin" dedi; TCMB faizi %37 seviyesinde tuttu.',
     "duz haber metni korunur")
esit(besleme._metin("<![CDATA[Brent 88,90 dolara geriledi.]]>"),
     "Brent 88,90 dolara geriledi.", "CDATA icindeki duz metin korunur")
esit(besleme._metin("&lt;p&gt;Fed faizi sabit tuttu.&lt;/p&gt;"),
     "Fed faizi sabit tuttu.", "HTML bicimli ama DUZYAZI ozet korunur")


# --------------------------------------------------------------------
# IKINCIL KONU ISARETLERI
# --------------------------------------------------------------------
#
# Olculdu: ana sayfadaki 40 akis kaleminin 23'u "Sirket haberleri"
# varsayilaninda kaliyordu ve neredeyse hicbiri sirket haberi degildi.
# Ikincil tablo o kovayi dolduruyor.
# "Emtia Ima Edilen Volatilite" ANA tabloda "emtia" ile eslesiyor ve
# ikincil tabloya hic gelmiyor -- dogrusu da bu, baslik emtia hakkinda.
esit(besleme.konu_bul("Emtia İma Edilen Volatilite", "Şirket haberleri"),
     "Altın ve emtia", "ana tablo once: 'emtia' kelimesi kazaniyor")
esit(besleme.konu_bul("120 Günlük Korelasyon Matrisi", "Şirket haberleri"),
     "Borsa", "korelasyon tablosu Borsa'ya duşuyor")
esit(besleme.konu_bul("ABD Endeksi Vadeli İşlemleri", "Şirket haberleri"),
     "Borsa", "vadeli islem Borsa'ya duşuyor")
esit(besleme.konu_bul("MUFG: JPY - FJElite", "Şirket haberleri"),
     "Döviz", "doviz masasi notu Doviz'e duşuyor")
esit(besleme.konu_bul("İsviçre hükümeti KDV zammı öneriyor", "Şirket haberleri"),
     "Vergi ve kamu maliyesi", "KDV vergi konusuna duşuyor")
esit(besleme.konu_bul("Pakistan: ABD-İran Mutabakat Zaptı uzatılabilir",
                      "Şirket haberleri"),
     "Jeopolitik", "mutabakat Jeopolitik'e duşuyor")

# EN ONEMLI KURAL: ikincil tablo DOGRU etiketi ASLA ezmiyor.
#
# Ilk denememde ikincil kaliplar ana tabloyla birlikte taraniyordu ve
# "zirve" kalibi "Gümüş 7 haftanın ZIRVESINDE" basligini Jeopolitik
# yapiyordu. Ikincil tabloya yalnizca ana tablo BOS dondugunde
# bakiliyor; bu sinama o sirayi kilitliyor.
esit(besleme.konu_bul("Gümüş 7 haftanın zirvesinde", "Şirket haberleri"),
     "Altın ve emtia", "fiyat 'zirvesi' Jeopolitik SANILMIYOR")
esit(besleme.konu_bul("TCMB faiz kararını açıkladı", "Şirket haberleri"),
     "Para politikası", "ana tablonun dogru etiketi korunuyor")
esit(besleme.konu_bul("Brent petrol ihracatı arttı", "Şirket haberleri"),
     "Enerji", "enerji etiketi ikincil tabloyla bozulmuyor")

# "usd" ve "eur" BILEREK ikincil tabloda yok: her ikinci baslikta
# geciyorlar ve kovayi doviz haberi olmayan seyle doldururlardi.
esit(besleme.konu_bul("ABD'de konut satışları arttı", "Şirket haberleri"),
     "Konut ve kira", "genel para birimi adi yanlis eslesme URETMIYOR")


# --------------------------------------------------------------------
# ELEME GUNE GORE KOVALANMALI.
#
# OLCULEN HATA (2026-08-22): imza karsilastirmasi butun listede
# yapiliyordu ve DUZENLI YAYIMLANAN resmi belgeleri birbirine eziyordu:
#
#     "Minutes of the FOMC, March 17-18, 2026"   (8 Nisan)
#     "Minutes of the FOMC, July 28-29, 2026"    (19 Agustos)
#
# Govde ortusmesi 0,86 -- tek fark ay adi, gun numaralari govdeye
# kirpilirken dusuyor. Sonuc: Temmuz tutanaklari HIC alinmadi ve
# 5 Agustos'tan beri depoda tek bir yeni Fed kaydi yoktu. Duzeltince
# cekilen oge sayisi 172'den 211'e cikti.
#
# Elemenin amaci "ayni gun bes kaynakta cikan ayni haber"; farkli
# aylarda cikan iki ayri belge degil.
# --------------------------------------------------------------------
_A = "Minutes of the Federal Open Market Committee, March 17-18, 2026"
_B = "Minutes of the Federal Open Market Committee, July 28-29, 2026"

# Imzalar GERCEKTEN ortusuyor -- sorun eslesmede degil, KAPSAMDA.
esit(besleme._ortusuyor(besleme._imza(_A), besleme._imza(_B)), True,
     "duzenli belgelerin imzalari ortusuyor (beklenen)")


def _ele(ogeler):
    """`cek` icindeki eleme mantiginin ayni kopyasi -- gune gore."""
    secili, imzalar = [], {}
    for baslik, gun in ogeler:
        im = besleme._imza(baslik)
        if any(besleme._ortusuyor(im, v) for v in imzalar.get(gun, ())):
            continue
        secili.append(baslik)
        imzalar.setdefault(gun, []).append(im)
    return secili


esit(len(_ele([(_A, "2026-04-08"), (_B, "2026-08-19")])), 2,
     "FARKLI gunlerdeki iki belge IKISI DE kaliyor")
esit(len(_ele([(_A, "2026-04-08"), (_A, "2026-04-08")])), 1,
     "AYNI gunde ayni haber tekilleniyor")
esit(len(_ele([("Borsa günü yükselişle tamamladı", "2026-08-20"),
               ("Borsa günü yükselişle tamamladı", "2026-08-21")])), 2,
     "her gun tekrarlanan baslik gunler arasi ELENMIYOR")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
