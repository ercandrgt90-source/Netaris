"""Arastirma dosyasi -- haberin arkasindaki veri agini kurar.

    haber -> Turkiye gorunumu -> seri analizi -> duyarlilik
          -> izlenecekler -> kosullu senaryolar -> seffaflik sayimi

NEDEN AYRI MODUL
----------------
Bu dosyanin urettigi seylerin HICBIRI dil modeli gerektirmiyor. Hepsi
depodaki seriden hesaplanan olcum:

  * manset ile cekirdegin kac kez ayristigi
  * enflasyonun kac aydir hangi bantta seyrettigi
  * reel faizin kac puan oldugu
  * haberin hangi veri aciklamasinin ardindan geldigi

Model geldiginde onun isi bunlari cumleye cevirmek olacak; BULMAK degil.
Bu ayrim maliyeti dusuruyor ve daha onemlisi uydurmayi kapatiyor -- model
rakami aramiyor, verileni yaziyor.

TAHMIN URETILMEZ
----------------
Senaryolar KOSULLUDUR ve agirliksizdir: "X olursa Y olabilir". Bir
senaryoya "%55 olasilik" yazmak, hesaplanmamis bir sayiyi olcum gibi
sunmak olurdu -- sitenin "okumadigimiz raporun gerekcesini atfetmeyiz"
ilkesiyle celisirdi.

Gecmis varsa SAYIYLA konusulur: "benzer oruntu alti kez gorundu, dordunde
sunu izledi". Bu bir olcum; olasilik degil.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date

DEPO = pathlib.Path(__file__).parent.parent / "netaris.db"

#: Turkiye panelinde gosterilecek seriler. (kod, ad, birim, basamak)
#:
#: CDS BILINCLI OLARAK YOK: lisansli veri, ucretsiz ve ticari kullanima
#: acik kaynagi bulunamadi. Olmayan bir satiri bos basmaktansa hic
#: basmamak dogru.
TURKIYE_PANEL = (
    ("TP.TUKFIY2025.GENEL", "Enflasyon", "%", 2),
    ("TP.FE25.OKTG04", "Çekirdek (C)", "%", 2),
    # ETIKET "POLITIKA FAIZI" DEGIL.
    #
    # TP.APIFON4 = TCMB agirlikli ortalama FONLAMA MALIYETI. Politika
    # faizi (bir hafta vadeli repo) AYRI bir buyukluk ve ikisi
    # sapabiliyor -- olculdu: panel "Politika faizi %40,00" yaziyordu,
    # gercek politika faizi %37 idi. Ayni dosyada `takvim.TANIM` zaten
    # "politika faizinden sapabilir" diye yaziyordu; yanlis olan
    # yalnizca bu etiketti.
    #
    # Serinin dogru adi kullaniliyor. Politika faizinin kendisi icin
    # EVDS'de calisan bir kod bulunamadi (TP.APIFON1/2/3, TP.FE.OKTG01
    # denendi, hepsi bos donuyor); bulununca AYRI kalem olarak eklenir.
    ("TP.APIFON4", "Ortalama fonlama", "%", 2),
    ("TP.DK.USD.S.YTL", "USD/TRY", "", 2),
    ("TP.YISGUCU2.G8", "İşsizlik", "%", 1),
)

#: Reel faiz hesabinda kullanilan cift
REEL_FAIZ = ("TP.APIFON4", "TP.TUKFIY2025.GENEL")

#: Konu -> (sektor, yildiz, gerekce)
#:
#: BU TABLO SITENIN EN DEGERLI VARLIGI OLACAK.
#: Taslak burada; alan bilgisiyle duzeltilmesi gereken yer de burasi.
#: Yildiz bir tahmin degil, DUYARLILIK sirasi: hangi sektorun gelir ya da
#: maliyet kalemi bu degiskene daha dogrudan bagli.
DUYARLILIK: dict[str, tuple[tuple[str, int, str], ...]] = {
    "Para politikası": (
        ("Bankacılık", 5, "Net faiz marjı ve kredi talebi doğrudan bağlı"),
        ("GYO / İnşaat", 4, "Konut kredisi faizi talebi belirler"),
        ("Otomotiv / Dayanıklı tüketim", 4, "Taksitli satış ve kredi kanalı"),
        ("Perakende", 3, "İç talep üzerinden dolaylı"),
        ("İhracatçı sanayi", 2, "Kur kanalı baskın, faiz ikincil"),
    ),
    "Enflasyon": (
        ("Perakende / Gıda", 5, "Fiyatlama gücü ve stok devir hızı"),
        ("Bankacılık", 4, "Reel getiri ve politika beklentisi"),
        ("Konut ve kira", 4, "Kira TÜFE sepetinde ağırlıklı kalem"),
        ("İhracatçı sanayi", 3, "Birim maliyet ve rekabet gücü"),
        ("Savunma / Kamu ihalesi", 2, "Sözleşmeler çoğunlukla endeksli"),
    ),
    "Döviz": (
        ("İthalatçı sanayi", 5, "Ara malı maliyeti döviz cinsinden"),
        ("Bankacılık", 4, "Döviz pozisyonu ve kredi kalitesi"),
        ("İhracatçı sanayi", 4, "Ters yönde çalışır — gelir tarafı döviz"),
        ("Havacılık / Turizm", 3, "Gelir döviz, gider kısmen TL"),
        ("Perakende", 3, "İthal ürün ağırlığına göre değişir"),
    ),
    "Enerji": (
        ("Havayolu / Lojistik", 5, "Yakıt gider kaleminin en büyük parçası"),
        ("Petrokimya", 5, "Girdi maliyeti doğrudan bağlı"),
        ("Enerji üretimi", 4, "Girdi ve satış fiyatı birlikte hareket eder"),
        ("Çimento / Demir-çelik", 4, "Enerji yoğun üretim"),
        ("Bankacılık", 2, "Cari denge üzerinden dolaylı"),
    ),
    "Dış ticaret": (
        ("İhracatçı sanayi", 5, "Doğrudan gelir kalemi"),
        ("Lojistik / Liman", 4, "Hacme bağlı"),
        ("Bankacılık", 3, "Dış finansman ve kur üzerinden"),
        ("İç piyasa perakendesi", 2, "Dolaylı"),
    ),
    # Jeopolitik etkinin BUYUKLUGU olayin turune gore cok degisir;
    # asagidaki siralama "hangi sektor once haber olur" siralamasidir,
    # bir etki tahmini degil. Bir yaptirim karari ile bir ateskes
    # haberinin ayni sektore etkisi ters yonde olabilir.
    "Jeopolitik": (
        ("Havayolu / Lojistik", 5, "Yakıt maliyeti ve güzergâh riski"),
        ("Enerji üretimi", 5, "Arz güvenliği ve girdi fiyatı"),
        ("Savunma sanayi", 4, "Sipariş ve ihracat izinleri"),
        ("İhracatçı sanayi", 4, "Pazar erişimi ve gümrük rejimi"),
        ("Bankacılık", 3, "Ülke risk primi ve dış borçlanma maliyeti"),
        ("Turizm", 3, "Bölgesel gerilim ziyaretçi planını etkiler"),
    ),
    "Borsa": (
        ("Aracı kurumlar", 5, "İşlem hacmi komisyon gelirini belirler"),
        ("Bankacılık", 4, "Portföy ve yatırım bankacılığı"),
        ("Halka arz adayları", 4, "Değerleme ve iştah"),
        ("Reel sektör", 2, "Öz kaynak maliyeti üzerinden dolaylı"),
    ),
    "Altın ve emtia": (
        ("Kuyumculuk / Mücevher", 5, "Doğrudan girdi ve stok değeri"),
        ("Bankacılık", 3, "Altın mevduatı ve kıymetli maden hesapları"),
        ("Sanayi (bakır, çelik)", 4, "Girdi maliyeti"),
        ("Perakende", 2, "Dolaylı"),
    ),
    "İstihdam ve ücret": (
        ("Emek yoğun sanayi", 5, "Ücret gideri kâr marjının ana belirleyicisi"),
        ("Perakende / Hizmet", 4, "Hem maliyet hem talep tarafı"),
        ("Lojistik", 4, "Ücret gideri yüksek"),
        ("Bankacılık", 2, "Dolaylı — iç talep üzerinden"),
    ),
    "Konut ve kira": (
        ("GYO / İnşaat", 5, "Doğrudan gelir ve stok değeri"),
        ("Çimento / Demir-çelik", 4, "Bağlantılı talep"),
        ("Beyaz eşya / Mobilya", 4, "Konut teslimine bağlı"),
        ("Bankacılık", 3, "Konut kredisi hacmi"),
    ),
    "Tarım ve gıda": (
        ("Gıda sanayi", 5, "Hammadde maliyeti doğrudan bağlı"),
        ("Perakende / Market", 4, "Raf fiyatı ve marj"),
        ("Gübre / Tarım kimyasalı", 4, "Talep rekolteyle birlikte hareket eder"),
        ("Bankacılık", 3, "Tarım kredileri ve TARSİM"),
        ("Lojistik", 3, "Hasat dönemi taşıma hacmi"),
    ),
    "Turizm": (
        ("Konaklama", 5, "Doğrudan gelir kalemi"),
        ("Havayolu", 5, "Yolcu sayısı ve doluluk"),
        ("Yeme-içme / Perakende", 4, "Turist harcaması"),
        ("GYO — kıyı bölgeleri", 3, "Kira ve değerleme"),
        ("Bankacılık", 2, "Cari denge üzerinden dolaylı"),
    ),
    "Bankacılık": (
        ("Bankacılık", 5, "Doğrudan düzenleme muhatabı"),
        ("Reel sektör", 4, "Kredi arzının miktarı ve maliyeti"),
        ("GYO / İnşaat", 3, "Proje finansmanına erişim"),
        ("Aracı kurumlar", 2, "Dolaylı"),
    ),
    "Vergi ve kamu maliyesi": (
        ("Tüm halka açık şirketler", 4, "Vergi oranı net kâra doğrudan yansır"),
        ("Perakende / Otomotiv", 4, "ÖTV ve KDV nihai fiyata geçer"),
        ("Bankacılık", 3, "İç borçlanma ve tahvil portföyü"),
        ("İhracatçı sanayi", 2, "Teşvik ve iade rejimine bağlı"),
    ),
    "Kripto varlıklar": (
        ("Aracı platformlar", 5, "İşlem hacmi komisyon gelirini belirler"),
        ("Bankacılık", 2, "Ödeme ve transfer kanalı"),
        ("Perakende yatırımcı", 4, "Portföy değeri doğrudan etkilenir"),
    ),
    "Piyasa düzenlemesi": (
        ("Aracı kurumlar", 5, "İşlem kuralları ve yükümlülükler doğrudan"),
        ("Halka açık şirketler", 4, "Kamuyu aydınlatma yükümlülüğü"),
        ("Bankacılık", 3, "Yatırım bankacılığı ve portföy yönetimi"),
        ("Bireysel yatırımcı", 3, "Erişim ve koruma kuralları"),
    ),
    # "Şirket haberleri" BILINCLI OLARAK YOK.
    # Tek bir sirketin islemi icin sektor duyarliligi tablosu uretmek,
    # olmayan bir genelleme yapmak olurdu. O konuda kutu basilmiyor.
}

#: Konu -> izlenecek gostergeler. Kullanici bunlari takip listesine ekler.
# --------------------------------------------------------------------
# VARLIK TABANLI DUYARLILIK VE SENARYO
# --------------------------------------------------------------------
#
# NEDEN: konu tablosu tek basina kullanildiginda olculdu -- 121 haber
# sayfasinda yalnizca 13 FARKLI duyarlilik tablosu vardi ve en siki 34
# sayfada birebir ayniydi. Ayni konudaki her haber ayni analizi
# tasiyordu.
#
# Varlik kumesi konudan cok daha ayrisik: ayni olcumde 149 haberin 59
# farkli varlik kumesi vardi. Haberin METNINDEN cikan varliklara gore
# kurmak, analizi habere ozgu kiliyor.
#
# KONU TABLOSU KALDIRILMADI, TABAN OLARAK KALIYOR. Varligi olmayan ya
# da tanimadigimiz varliga baglanan haberde yine konu tablosu
# calisiyor -- eksik bir analiz, hic analiz olmamasindan iyi.

#: Varlik kodu -> (sektor, duyarlilik 1-5, gerekce)
#:
#: Puanlar ELLE YAZILMIS bir siralama, olculmus bir katsayi DEGIL --
#: sayfada da yildiz olarak gorunuyor, sayi olarak degil. Veriden
#: hesaplamak icin sektor endeksi gerekiyor; BIST sektor endeksleri
#: lisansli ve ucretsiz kaynagi yok.
VARLIK_DUYARLILIK: dict[str, tuple[tuple[str, int, str], ...]] = {
    "BRENT": (
        ("Havayolu / Ulaştırma", 5, "Yakıt en büyük maliyet kalemi"),
        ("Enerji / Rafineri", 5, "Ürün marjı ham petrol fiyatına bağlı"),
        ("Petrokimya", 4, "Nafta girdisi doğrudan türev"),
        ("Lojistik", 4, "Akaryakıt ve navlun maliyeti"),
        ("Cari denge", 4, "Türkiye net enerji ithalatçısı"),
    ),
    "WTI": (
        ("Enerji / Rafineri", 5, "Ürün marjı ham petrol fiyatına bağlı"),
        ("Havayolu / Ulaştırma", 4, "Yakıt maliyeti"),
    ),
    "DGAZ": (
        ("Enerji / Elektrik", 5, "Santral yakıt maliyeti"),
        ("Çimento / Cam / Seramik", 5, "Isıl işlem enerji yoğun"),
        ("Gübre / Kimya", 4, "Doğal gaz doğrudan hammadde"),
        ("Cari denge", 4, "İthalat faturasının büyük kalemi"),
    ),
    "XAU": (
        ("Mücevherat / Perakende", 4, "Girdi maliyeti ve talep esnekliği"),
        ("Madencilik", 4, "Satış fiyatı doğrudan bağlı"),
        ("Cari denge", 3, "Külçe ithalatı dış ticaret dengesine yazılır"),
    ),
    "XCU": (
        ("Kablo / Elektrik ekipmanı", 5, "Bakır ana hammadde"),
        ("İnşaat", 3, "Tesisat ve elektrik girdisi"),
    ),
    "TCMB_FAIZ": (
        ("Bankacılık", 5, "Net faiz marjı ve fonlama maliyeti"),
        ("GYO / İnşaat", 5, "Konut kredisi faizi talebi belirler"),
        ("Otomotiv / Dayanıklı tüketim", 4, "Taksitli satış kredi kanalı"),
        ("Borçluluğu yüksek şirketler", 4, "Finansman gideri kâr marjını yer"),
        ("Perakende", 3, "İç talep üzerinden dolaylı"),
    ),
    "TCMB": (
        ("Bankacılık", 5, "Fonlama maliyeti ve zorunlu karşılık"),
        ("GYO / İnşaat", 4, "Kredi koşulları"),
    ),
    "TUFE_TR": (
        ("Perakende / Gıda", 5, "Fiyatlama gücü ve stok devir hızı"),
        ("Konut ve kira", 4, "Kira TÜFE sepetinde ağırlıklı"),
        ("Bankacılık", 4, "Reel getiri ve politika beklentisi"),
        ("Ücrete bağlı sektörler", 4, "Asgari ücret ve toplu sözleşme çıpası"),
    ),
    "UFE_TR": (
        ("Üretici sanayi", 5, "Birim maliyetin doğrudan ölçüsü"),
        ("Perakende / Gıda", 3, "Maliyet geçişi tüketici fiyatına yansır"),
    ),
    "USDTRY": (
        ("İhracatçı sanayi", 5, "Gelir dövizde, maliyet kısmen TL"),
        ("İthalata bağımlı üretim", 5, "Girdi maliyeti doğrudan kurdan"),
        ("Döviz borçlu şirketler", 5, "Kur farkı bilançoya yazılır"),
        ("Turizm", 4, "Gelir dövizde, rekabet gücü kurdan"),
    ),
    "DIS_TICARET_TR": (
        ("İhracatçı sanayi", 5, "Dış talep doğrudan ciro"),
        ("Cari denge", 5, "Dış ticaret cari işlemlerin ana bileşeni"),
        ("Lojistik / Liman", 4, "Hacim ticaret akışına bağlı"),
    ),
    "ISSIZLIK_TR": (
        ("Perakende", 4, "Hanehalkı geliri ve harcama eğilimi"),
        ("Ücrete bağlı sektörler", 4, "İş gücü sıkılığı ücreti belirler"),
    ),
    "NFP": (
        ("Küresel risk iştahı", 4, "Fed patikası beklentisini değiştirir"),
        ("Gelişen ülke varlıkları", 4, "Sermaye akımı yönü"),
        ("Bankacılık", 3, "Küresel faiz koşulları fonlama maliyetine geçer"),
    ),
    "CPI_US": (
        ("Küresel faiz koşulları", 5, "Fed tepki fonksiyonunun ana girdisi"),
        ("Gelişen ülke varlıkları", 4,
         "Reel getiri farkı sermaye akımını yönlendirir"),
        ("Borçluluğu yüksek şirketler", 3, "Dış finansman maliyeti"),
    ),
    "FED": (
        ("Küresel faiz koşulları", 5, "Politika faizi küresel sermayenin fiyatı"),
        ("Bankacılık", 4, "Dış fonlama maliyeti"),
        ("Gelişen ülke varlıkları", 4, "Sermaye akımı yönü"),
    ),
    "ECB": (
        ("İhracatçı sanayi", 4, "Avro Bölgesi Türkiye'nin en büyük pazarı"),
        ("Küresel faiz koşulları", 4, "Avro tarafının politika patikası"),
    ),
    "BIST100": (
        ("Aracı kurumlar / Portföy", 5, "İşlem hacmi doğrudan gelir"),
        ("Bankacılık", 4, "Endeksin en ağırlıklı sektörü"),
    ),
    "IR": (
        ("Denizcilik / Navlun", 5, "Hürmüz güzergâhı ve savaş riski primi"),
        ("Havayolu / Ulaştırma", 4, "Rota ve sigorta maliyeti"),
        ("Enerji / Rafineri", 4, "Arz riski primi"),
    ),
    "RU": (
        ("Enerji / Elektrik", 4, "Doğal gaz tedarik güzergâhı"),
        ("Tarım / Gıda", 4, "Tahıl ve gübre arzı"),
        ("Turizm", 3, "Ziyaretçi sayısında ağırlıklı pazar"),
    ),
    "CN": (
        ("İthalata bağımlı üretim", 4, "Ara malı tedarikinde ağırlıklı kaynak"),
        ("Madencilik / Emtia", 4, "Küresel talebin belirleyicisi"),
    ),
}

#: Varlik kodu -> kosullu senaryolar.
#: "Su olursa su OLABILIR" -- olasilik atanmiyor, yon iddia edilmiyor.
VARLIK_SENARYOLARI: dict[str, tuple[tuple[str, str], ...]] = {
    "BRENT": (
        ("Arz kesintisi kalıcı hale gelirse",
         "enerji ithalat faturası ve cari açık büyüyebilir"),
        ("Gerilim yatışıp risk primi çözülürse",
         "maliyet enflasyonunda aşağı yönlü alan açılabilir"),
    ),
    "DGAZ": (
        ("Sevkiyat güzergâhında kesinti olursa",
         "elektrik ve enerji yoğun sanayi maliyeti yukarı gidebilir"),
    ),
    "TCMB_FAIZ": (
        ("Çekirdek enflasyon yüksek seyrini korursa",
         "faiz indirimi beklentisi ötelenebilir"),
        ("Fonlama maliyeti gerilerse",
         "kredi faizleri ve mevduat getirisi aynı yönde ayarlanabilir"),
    ),
    "TUFE_TR": (
        ("Gıda ve enerji kaynaklı düşüş çekirdeğe yayılırsa",
         "dezenflasyon kalıcılık kazanabilir"),
        ("Manşet düşerken çekirdek yatay kalırsa",
         "hizmet enflasyonu ana direnç olarak öne çıkabilir"),
    ),
    "USDTRY": (
        ("Kurda hızlı bir hareket olursa",
         "ithal girdi maliyeti ve döviz borçlu bilançolar öne çıkabilir"),
    ),
    "NFP": (
        ("İş gücü piyasası beklenenden güçlü kalırsa",
         "Fed'in indirim patikası ötelenebilir"),
        ("Soğuma işaretleri birikirse",
         "gelişen ülke varlıklarına yönelik risk iştahı güçlenebilir"),
    ),
    "CPI_US": (
        ("Enflasyon hedefe yakınsamada duraksarsa",
         "küresel faiz koşulları uzun süre sıkılıkta kalabilir"),
    ),
    "IR": (
        ("Hürmüz Boğazı'nda geçiş fiilen kısıtlanırsa",
         "petrol ve navlun fiyatlarında risk primi büyüyebilir"),
        ("Anlaşma yürürlüğe girerse",
         "arz kaygısı kaynaklı prim çözülebilir"),
    ),
    "DIS_TICARET_TR": (
        ("Dış talepte zayıflama sürerse",
         "cari dengeye yazılan açık ve dış finansman ihtiyacı artabilir"),
    ),
    "BIST100": (
        ("Yabancı takas oranı yön değiştirirse",
         "endeks ve işlem hacmi bundan etkilenebilir"),
    ),
}

#: Kac sektor / senaryo basilir.
VARLIK_EN_COK = 5
VARLIK_SENARYO_EN_COK = 3


def varlik_duyarliligi(varliklar, konu: str) -> tuple:
    """Haberin varliklarindan duyarlilik tablosu.

    Ayni sektor birden fazla varliktan geliyorsa EN YUKSEK puan
    tutuluyor: bir sektor iki kanaldan birden etkileniyorsa, zayif
    kanal onu daha az duyarli yapmaz.

    Varlik yoksa ya da hicbiri tanimli degilse KONU tablosuna dusuyor.
    """
    if not varliklar:
        return DUYARLILIK.get(konu, ())
    toplu: dict[str, tuple[int, str]] = {}
    for kod in varliklar:
        for sektor, puan, neden in VARLIK_DUYARLILIK.get(kod, ()):
            eski = toplu.get(sektor)
            if eski is None or puan > eski[0]:
                toplu[sektor] = (puan, neden)
    if not toplu:
        return DUYARLILIK.get(konu, ())
    sirali = sorted(toplu.items(), key=lambda x: (-x[1][0], x[0]))
    return tuple((s, p, n) for s, (p, n) in sirali[:VARLIK_EN_COK])


def varlik_senaryolari(varliklar, konu: str) -> tuple:
    """Haberin varliklarindan kosullu senaryolar. Yoksa konu tablosu."""
    if not varliklar:
        return SENARYOLAR.get(konu, ())
    cikti: list[tuple[str, str]] = []
    gorulen: set = set()
    for kod in varliklar:
        for kosul, sonuc in VARLIK_SENARYOLARI.get(kod, ()):
            if kosul in gorulen:
                continue
            gorulen.add(kosul)
            cikti.append((kosul, sonuc))
    if not cikti:
        return SENARYOLAR.get(konu, ())
    return tuple(cikti[:VARLIK_SENARYO_EN_COK])


IZLENECEKLER: dict[str, tuple[str, ...]] = {
    "Para politikası": (
        "Bir sonraki TÜFE açıklaması",
        "PPK kararı ve toplantı özeti",
        "Çekirdek (C) enflasyon",
        "TCMB piyasa katılımcıları anketi",
        "USD/TRY",
        "ABD 10 yıllık tahvil getirisi",
    ),
    "Enflasyon": (
        "Bir sonraki TÜFE açıklaması",
        "Çekirdek (C) enflasyon",
        "Yİ-ÜFE",
        "PPK kararı",
        "Brent petrol",
        "USD/TRY",
    ),
    "Döviz": ("USD/TRY", "Dolar endeksi", "TCMB rezervleri",
              "Cari işlemler dengesi", "Politika faizi"),
    "Enerji": ("Brent petrol", "Cari işlemler dengesi", "Yİ-ÜFE",
               "TÜFE — akaryakıt kalemi", "USD/TRY"),
    "Dış ticaret": ("Aylık dış ticaret verisi", "Cari işlemler dengesi",
                    "USD/TRY", "Brent petrol"),
    "Jeopolitik": ("Brent petrol", "Ons altın", "Türkiye CDS primi",
                   "Cari işlemler dengesi", "Doğal gaz fiyatı",
                   "Navlun ve sigorta maliyetleri"),
    "Borsa": ("BIST 100", "USD/TRY", "ABD 10 yıllık", "Politika faizi"),
    "Altın ve emtia": ("Ons altın", "Dolar endeksi", "ABD 10 yıllık",
                       "Cari işlemler dengesi"),
    "İstihdam ve ücret": ("İşsizlik oranı", "Asgari ücret takvimi",
                          "TÜFE", "İç talep göstergeleri"),
    "Konut ve kira": ("Konut kredisi faizi", "TÜFE — kira kalemi",
                      "Politika faizi", "Konut satış istatistikleri"),
    "Tarım ve gıda": ("TÜFE — gıda kalemi", "Yİ-ÜFE", "Rekolte tahminleri",
                      "Gübre ve yem fiyatları", "USD/TRY"),
    "Turizm": ("Turizm geliri istatistikleri", "Cari işlemler dengesi",
               "Ziyaretçi sayısı", "USD/TRY", "EUR/TRY"),
    "Bankacılık": ("Politika faizi", "Zorunlu karşılık oranları",
                   "Kredi büyümesi", "TCMB rezervleri", "TÜFE"),
    "Vergi ve kamu maliyesi": ("Bütçe gerçekleşmeleri", "İç borçlanma ihaleleri",
                               "TÜFE", "Politika faizi"),
    "Kripto varlıklar": ("Bitcoin", "Dolar endeksi", "ABD 10 yıllık",
                         "Düzenleme gelişmeleri"),
    "Piyasa düzenlemesi": ("SPK bülteni", "Halka arz takvimi", "BIST işlem hacmi",
                           "Kamuyu aydınlatma bildirimleri"),
}

#: Konu -> kosullu senaryolar. (kosul, sonuc)
#: AGIRLIK YOK -- yukaridaki modul aciklamasina bakin.
SENARYOLAR: dict[str, tuple[tuple[str, str], ...]] = {
    "Para politikası": (
        ("Çekirdek enflasyon yüksek seyrini korursa",
         "faiz indirimi beklentisi ötelenebilir"),
        ("Çekirdek ve enerji birlikte gerilerse",
         "gevşeme adımları gündeme gelebilir"),
        ("Kur veya enerji fiyatlarında yeni bir yükseliş olursa",
         "sıkı duruş beklenenden uzun sürebilir"),
    ),
    "Enflasyon": (
        ("Gıda ve enerji kaynaklı düşüş çekirdeğe yayılırsa",
         "dezenflasyon kalıcılık kazanabilir"),
        ("Manşet düşerken çekirdek yatay kalırsa",
         "fiyat katılığı sürüyor demektir"),
        ("Kur geçişkenliği hızlanırsa",
         "manşette yeniden yukarı yönlü baskı oluşabilir"),
    ),
    "Döviz": (
        ("Faiz farkı korunursa", "TL varlıklara yönelen akım desteklenebilir"),
        ("Enerji faturası artarsa", "cari denge üzerinden baskı oluşabilir"),
        ("Küresel risk iştahı bozulursa",
         "gelişmekte olan ülke para birimleri birlikte etkilenebilir"),
    ),
    "Enerji": (
        ("Arz riski fiyatlanmaya devam ederse",
         "ithalat faturası ve cari denge etkilenebilir"),
        ("Fiyatlar gerilerse", "enflasyona akaryakıt kanalından destek gelebilir"),
        ("Kur ve enerji birlikte yükselirse", "maliyet baskısı katlanabilir"),
    ),
    # Senaryolar KOSULLU ve AGIRLIKSIZ. Jeopolitikte bu ozellikle onemli:
    # "gerilim artarsa petrol yukselir" yaygin ama olculmemis bir
    # genellemedir. 2020 Suleymani suikastinde petrol iki gunde yukselip
    # geri verdi. Kosulu yaziyoruz, olasiligi degil.
    "Jeopolitik": (
        ("Fiili arz kesintisi olmadan gerilim sürerse",
         "risk primi zamanla erimeye eğilimlidir"),
        ("Sevkiyat güzergâhı fiilen kapanırsa",
         "petrol ve navlun maliyeti üzerinden enerji faturası artabilir"),
        ("Yaptırım ya da gümrük kararı yürürlüğe girerse",
         "etki, ihracatçının o pazara bağımlılık oranı kadar olur"),
        ("Gerilim düşerse",
         "önceden fiyatlanmış risk primi geri verilebilir"),
    ),
    "Tarım ve gıda": (
        ("Rekolte beklentiyi aşarsa",
         "gıda enflasyonunda aşağı yönlü katkı oluşabilir"),
        ("Girdi maliyetleri (gübre, yem, akaryakıt) yükselirse",
         "rekolteden gelen destek sınırlı kalabilir"),
        ("İthalat bağımlı kalemlerde kur yükselirse",
         "gıda fiyatlarına yukarı baskı gelebilir"),
    ),
    "Dış ticaret": (
        ("İhracat artışı sürerse", "cari işlemler dengesine olumlu yansır"),
        ("Enerji ithalatı artarsa", "ihracat artışının katkısı zayıflayabilir"),
        ("Dış talep yavaşlarsa", "ihracat ağırlıklı sektörler önce hisseder"),
    ),
    "Turizm": (
        ("Sezon beklentiyi aşarsa", "cari dengeye net döviz katkısı artabilir"),
        ("Kur reel olarak değerlenirse", "fiyat rekabeti zayıflayabilir"),
        ("Bölgesel jeopolitik risk artarsa", "rezervasyonlar etkilenebilir"),
    ),
    "Konut ve kira": (
        ("Konut kredisi faizi gerilerse", "talep canlanabilir"),
        ("Kira artışları TÜFE'nin üzerinde seyrederse",
         "enflasyon sepetine yukarı katkı sürebilir"),
        ("İnşaat maliyetleri artarsa", "yeni arz yavaşlayabilir"),
    ),
    "Bankacılık": (
        ("Politika faizi yüksek kalırsa",
         "net faiz marjı korunabilir ama kredi talebi zayıflayabilir"),
        ("Kredi büyümesi sınırlandırılırsa",
         "reel sektörün işletme sermayesi finansmanı daralabilir"),
        ("Enflasyon gerilerse",
         "mevduatın reel getirisi ve tasarruf tercihi değişebilir"),
    ),
    "İstihdam ve ücret": (
        ("Ücret ayarlamaları enflasyonun üzerinde kalırsa",
         "iç talep desteklenirken birim maliyet artabilir"),
        ("İşsizlik düşük seyrini korursa",
         "ücret pazarlığında işgücü tarafı güçlü kalabilir"),
        ("Emekli ve memur ödemeleri artarsa",
         "bütçe harcama tarafında baskı oluşabilir"),
    ),
    "Vergi ve kamu maliyesi": (
        ("Bütçe açığı genişlerse",
         "iç borçlanma artabilir ve tahvil getirilerine yansıyabilir"),
        ("Dolaylı vergilerde değişiklik olursa",
         "nihai tüketici fiyatına doğrudan geçer"),
        ("Teşvik ve istisnalar genişlerse",
         "ilgili sektörlerde net kâr etkisi görülebilir"),
    ),
    "Borsa": (
        ("Reel faiz yüksek kalırsa",
         "hisse senedi mevduata göre görece cazibesini kaybedebilir"),
        ("Yabancı yatırımcı payı artarsa",
         "işlem hacmi ve değerleme çarpanları etkilenebilir"),
        ("Şirket kârlılıkları enflasyonun altında kalırsa",
         "reel getiri baskı görebilir"),
    ),
    "Altın ve emtia": (
        ("Reel faiz gerilerse", "faizsiz varlıkların görece cazibesi artabilir"),
        ("Dolar endeksi yükselirse", "dolar cinsi emtia fiyatlarına baskı gelebilir"),
        ("Jeopolitik risk artarsa", "güvenli liman talebi güçlenebilir"),
    ),
    "Kripto varlıklar": (
        ("Küresel risk iştahı güçlenirse", "risk varlıklarıyla birlikte hareket edebilir"),
        ("Düzenleme çerçevesi netleşirse", "kurumsal katılım koşulları değişebilir"),
        ("Reel faiz yükselirse", "getirisi olmayan varlıklara talep zayıflayabilir"),
    ),
}


# --------------------------------------------------------------------------
# Seri analizi
# --------------------------------------------------------------------------

@dataclass
class Gosterge:
    kod: str
    ad: str
    birim: str
    son: float
    onceki: float
    tarih: str
    onceki_tarih: str

    @property
    def fark(self) -> float:
        return self.son - self.onceki

    @property
    def degisim(self) -> str:
        """Degisim metni -- BIRIME GORE.

        Baz puan yalnizca ORAN serilerinde anlamli. Kuru "+10 bp" diye
        yazmak olculdu ve sacmaydi: 47,43'ten 47,54'e cikan bir fiyat 10
        baz puan degil, 11 kurus artmis demektir. Oranda puan, fiyatta
        yuzde gosteriliyor.
        """
        if self.birim == "%":
            bp = round(self.fark * 100)
            return f"{bp:+d} bp"
        if not self.onceki:
            return "—"
        y = (self.son - self.onceki) / self.onceki * 100
        return f"{'+' if y >= 0 else '−'}%{abs(y):.1f}".replace(".", ",")

    @property
    def yon(self) -> str:
        return "artis" if self.fark >= 0 else "azalis"


@dataclass
class Dosya:
    """Bir haberin arastirma dosyasi. Bos alanlar sayfada BASILMAZ."""

    turkiye: list[Gosterge] = field(default_factory=list)
    reel_faiz: float | None = None
    seyir: list[tuple[str, float]] = field(default_factory=list)
    seyir_ad: str = ""
    bulgular: list[str] = field(default_factory=list)
    #: Bulten basligi icin veriden uretilen acilis cumlesi.
    acilis: str = ""
    duyarlilik: tuple[tuple[str, int, str], ...] = ()
    izlenecekler: tuple[str, ...] = ()
    senaryolar: tuple[tuple[str, str], ...] = ()
    neden_bugun: str = ""
    sayim: dict[str, int] = field(default_factory=dict)

    @property
    def dolu(self) -> bool:
        return bool(self.turkiye or self.duyarlilik or self.izlenecekler)


def _seri(b: sqlite3.Connection, kod: str, n: int = 24) -> list[tuple[str, float]]:
    r = b.execute(
        "SELECT tarih, deger FROM gosterge WHERE kod = ? "
        "ORDER BY tarih DESC LIMIT ?", (kod, n),
    ).fetchall()
    return [(t, d) for t, d in reversed(r) if d is not None]


def _gosterge(b: sqlite3.Connection, kod: str, ad: str, birim: str) -> Gosterge | None:
    s = _seri(b, kod, 2)
    if len(s) < 2:
        return None
    return Gosterge(kod=kod, ad=ad, birim=birim, son=s[-1][1], onceki=s[-2][1],
                    tarih=s[-1][0], onceki_tarih=s[-2][0])


def _ayrisma_say(manset: list[tuple[str, float]],
                 cekirdek: list[tuple[str, float]]) -> tuple[int, int]:
    """Mansetin dusup cekirdegin yukseldigi ay sayisi.

    Bu, "fiyat katiligi" tartismasinin OLCULEBILIR hali. Iki seri ayni
    tarihlerde hizalaniyor; hizalanmayan aylar sayima girmiyor.
    """
    c = dict(cekirdek)
    ortak = [(t, d) for t, d in manset if t in c]
    if len(ortak) < 2:
        return 0, 0
    ayrisma = 0
    for i in range(1, len(ortak)):
        t, d = ortak[i]
        _, onceki = ortak[i - 1]
        cd, co = c[t], c[ortak[i - 1][0]]
        if d < onceki and cd > co:
            ayrisma += 1
    return ayrisma, len(ortak) - 1


def _bant(seri: list[tuple[str, float]], ay: int = 6) -> tuple[float, float, int]:
    son = seri[-ay:] if len(seri) >= ay else seri
    d = [x[1] for x in son]
    return min(d), max(d), len(son)


def _vir(x: float, b: int = 1) -> str:
    return f"{x:.{b}f}".replace(".", ",")


# --------------------------------------------------------------------------
# "Veri ne diyor" -- konuya gore bulgular
#
# Her uretec, seriyi bulamazsa BOS liste dondurur. Veri yoksa cumle
# uydurmak degil, susmak dogru.
# --------------------------------------------------------------------------

#: Basligi tek basina hicbir sey soylemeyen resmi bulten kaliplari.
#:
#: "Aylik Fiyat Gelismeleri (Temmuz 2026)" bir baslik degil, bir dosya
#: adi: okurda beklenti olusturmuyor ve TCMB'nin RSS'i ozet de
#: vermiyor. Sayfa "fiyat gelismeleri" diyor ama gelismenin KENDISI
#: sayfada yok -- kullanicinin bildirdigi hata tam olarak buydu.
#:
#: Bu basliklarda veriden bir ACILIS CUMLESI uretiliyor: rakam zaten
#: depoda, haberin anlattigi sey de o rakam.
BULTEN_KALIPLARI = (
    "fiyat gelismeleri", "aylik fiyat", "beklenti anketi",
    "faiz oranlarina iliskin", "para politikasi kararlari",
    "toplanti ozeti", "reel efektif doviz kuru", "menkul kiymet",
    "finansal hesaplar", "istatistikleri", "gostergeleri",
)


#: Turkce harfleri ASCII karsiligina indirir. Once translate, SONRA
#: lower: "İ".lower() iki kod noktasi uretiyor ve eslesme sessizce
#: bozuluyor. (Ayni katlama besleme.py, varlik.py ve gundem_yorum.py'de
#: de var; ortak bir module tasinmasi ileride yapilacak temizlik.)
_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def katla(metin: str) -> str:
    return metin.translate(_KATLAMA).lower()


def bulten_mi(baslik: str) -> bool:
    # Noktalama bosluga cevriliyor -- "TCMB:" gibi yazimlar kaliplari
    # bloke ediyordu. Ayni tuzak bu projede uc modulde yasandi.
    k = " " + re.sub(r"[^a-z0-9]+", " ", katla(baslik)).strip() + " "
    return any(p in k for p in BULTEN_KALIPLARI)


def acilis_cumlesi(konu: str, baslik: str) -> str:
    """Bulten basligi icin veriden acilis cumlesi.

    Kaynagin metnini YENIDEN YAYIMLAMIYOR -- TCMB'nin bulten metnini
    almiyoruz. Cumle tamamen bizim depomuzdaki OLCUMLERDEN kuruluyor:
    hangi seri, hangi tarih, hangi deger. Bulten zaten o rakami
    duyurdugu icin sayfa haberin konusuyla ortusuyor.

    Veri yoksa BOS doner ve sayfada hicbir sey basilmaz; uydurulmus bir
    acilis cumlesi, bos sayfadan kotudur.
    """
    if not bulten_mi(baslik) or not DEPO.exists():
        return ""
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            return _acilis(b, konu)
    except sqlite3.Error:
        return ""


def _son_iki(b, kod: str):
    s = _seri(b, kod, 2)
    return (s[-1], s[-2]) if len(s) >= 2 else (None, None)


def _yon(fark: float) -> str:
    if fark > 0.05:
        return "yükseldi"
    if fark < -0.05:
        return "geriledi"
    return "yatay kaldı"


def _acilis(b, konu: str) -> str:
    if konu in ("Enflasyon", "Para politikası"):
        m, mo = _son_iki(b, "TP.TUKFIY2025.GENEL")
        c, co = _son_iki(b, "TP.FE25.OKTG04")
        if not m:
            return ""
        ay = _ay_etiketi(m[0])
        p = [f"{ay} verisine göre TÜFE yıllık %{_vir(m[1], 2)}"]
        if mo:
            p.append(f"bir önceki aya göre {round((m[1] - mo[1]) * 100):+d} "
                     f"baz puanla {_yon(m[1] - mo[1])}")
        if c:
            p.append(f"çekirdek enflasyon (C) %{_vir(c[1], 2)}")
            if co:
                p.append(f"çekirdekte değişim {round((c[1] - co[1]) * 100):+d} "
                         f"baz puan")
        return "; ".join(p) + "."

    if konu == "Döviz":
        u, uo = _son_iki(b, "TP.DK.USD.S.YTL")
        e, _ = _son_iki(b, "TP.DK.EUR.S.YTL")
        if not u:
            return ""
        p = [f"{_ay_etiketi(u[0], gunlu=True)} itibarıyla USD/TRY {_vir(u[1], 4)}"]
        if uo and uo[1]:
            y = (u[1] - uo[1]) / uo[1] * 100
            p.append(f"önceki güne göre %{_vir(abs(y), 2)} "
                     f"{'yükseldi' if y >= 0 else 'geriledi'}")
        if e:
            p.append(f"EUR/TRY {_vir(e[1], 4)}")
        return "; ".join(p) + "."

    if konu == "İstihdam ve ücret":
        i, io = _son_iki(b, "TP.YISGUCU2.G8")
        if not i:
            return ""
        p = [f"{_ay_etiketi(i[0])} verisine göre işsizlik oranı %{_vir(i[1], 1)}"]
        if io:
            p.append(f"bir önceki aya göre {round((i[1] - io[1]) * 100):+d} "
                     f"baz puan")
        return "; ".join(p) + "."

    if konu == "Dış ticaret":
        c, co = _son_iki(b, "TP.HARICCARIACIK.K1")
        if not c:
            return ""
        ad = "fazlası" if c[1] > 0 else "açığı"
        p = [f"{_ay_etiketi(c[0])} verisine göre cari işlemler {ad} "
             f"{abs(c[1]):,.0f} mn $".replace(",", ".")]
        if co:
            p.append(f"önceki ay {abs(co[1]):,.0f} mn $".replace(",", "."))
        return "; ".join(p) + "."

    # Yurt disi konular. Turkiye serileri yerine kuresel fiyat serisi.
    kod = _KURESEL.get(konu)
    if kod:
        return _kuresel_cumle(b, *kod)
    return ""


#: Konu -> (seri kodu, gorunen ad, birim, tablo). Ozeti olmayan yurt disi
#: haberlerde acilis cumlesi bu serilerden kuruluyor.
_KURESEL = {
    "Enerji": ("DCOILBRENTEU", "Brent petrol", "$", "gosterge"),
    "Altın ve emtia": ("PAXGUSD", "Altın", "$", "fiyat"),
    "Borsa": ("SP500", "S&P 500", "", "gosterge"),
    "Kripto varlıklar": ("XBTUSD", "Bitcoin", "$", "fiyat"),
    "Jeopolitik": ("DCOILBRENTEU", "Brent petrol", "$", "gosterge"),
}


def _kuresel_cumle(b, kod: str, ad: str, birim: str, tablo: str) -> str:
    """Kuresel seriden acilis cumlesi.

    NEDEN: ozeti olmayan yabanci haberde sayfada HICBIR metin
    kalmiyordu -- baslik, fotograf ve piyasa kutusu. "Altinin grami gune
    yukselisle basladi" basligiyla acilan sayfada altinin fiyati bile
    yoktu. Cumle yine olcum: seviye ve iki pencerede degisim.
    """
    try:
        if tablo == "fiyat":
            r = b.execute("SELECT tarih, kapanis FROM fiyat WHERE sembol=?"
                          " ORDER BY tarih DESC LIMIT 70", (kod,)).fetchall()
        else:
            r = b.execute("SELECT tarih, deger FROM gosterge WHERE kod=?"
                          " ORDER BY tarih DESC LIMIT 70", (kod,)).fetchall()
    except sqlite3.Error:
        return ""
    s = [(t, float(d)) for t, d in r if d is not None]
    if len(s) < 2:
        return ""
    son = s[0]
    p = [f"{_ay_etiketi(son[0], gunlu=True)} kapanışına göre {ad} "
         f"{_vir(son[1], 2)}{(' ' + birim) if birim else ''}"]
    for n, etiket in ((21, "1 ayda"), (63, "3 ayda")):
        if len(s) > n and s[n][1]:
            y = (son[1] - s[n][1]) / s[n][1] * 100
            p.append(f"{etiket} %{_vir(abs(y), 1)} "
                     f"{'yükseldi' if y >= 0 else 'geriledi'}")
    return "; ".join(p) + "."


def _ay_etiketi(iso: str, gunlu: bool = False) -> str:
    """ISO tarihten "Temmuz 2026" ya da "4 Ağustos 2026".

    `_ay_adi` ADIYLA CAKISIYORDU: dosyanin ilerisinde `date` alan ayni
    adli bir islev var ve Python sonuncuyu tuttugu icin bu surum sessizce
    devre disi kaliyordu ("str has no attribute month").
    """
    try:
        y, a, g = iso[:10].split("-")
        ad = f"{_AYLAR[int(a) - 1]} {y}"
        return f"{int(g)} {ad}" if gunlu else ad
    except (ValueError, IndexError):
        return iso[:10]


def _bulgu_enflasyon(b, d) -> list[str]:
    manset = _seri(b, "TP.TUKFIY2025.GENEL", 13)
    cekirdek = _seri(b, "TP.FE25.OKTG04", 13)
    cikti: list[str] = []
    if len(manset) >= 6:
        d.seyir, d.seyir_ad = manset, "TÜFE (yıllık, %)"
        alt, ust, n = _bant(manset, 6)
        cikti.append(f"Enflasyon {n} aydır %{_vir(alt)}–%{_vir(ust)} bandında")
    if len(manset) >= 3 and len(cekirdek) >= 3:
        ayrisma, toplam = _ayrisma_say(manset, cekirdek)
        if toplam:
            # "Son 12 ayin 2'inde" yazmiyoruz: Turkce'de sayiya gelen ek
            # okunusa gore degisiyor (2'sinde, 3'unde, 6'sinda). Cumleyi
            # ek gerektirmeyen bicimde kurmak hem dogru hem daha akici.
            cikti.append(f"Son {toplam} ayda manşet {ayrisma} kez gerilerken "
                         f"çekirdek yükseldi")
        cikti.append("Manşet ile çekirdek arasındaki fark "
                     f"{_vir(abs(manset[-1][1] - cekirdek[-1][1]), 2)} puan")
    return cikti


def _bulgu_faiz(b, d) -> list[str]:
    faiz = _seri(b, "TP.APIFON4", 90)
    enf = _seri(b, "TP.TUKFIY2025.GENEL", 2)
    if not faiz:
        return []
    # ETIKET "POLITIKA FAIZI" DEGIL -- seri TP.APIFON4, yani agirlikli
    # ortalama FONLAMA MALIYETI. Ikisi ayri buyukluk ve sapabiliyor;
    # olculdu: bulgu "Politika faizi %40,00" diyordu, gercek politika
    # faizi %37 idi. Panel etiketi duzeltildi ama BU SATIR gozden
    # kacmisti -- ayni yanlis ad iki ayri yerde yasiyordu.
    cikti = [f"Ortalama fonlama maliyeti %{_vir(faiz[-1][1], 2)}"]
    if enf:
        reel = faiz[-1][1] - enf[-1][1]
        # Reel faiz TANIM GEREGI fark; "yaklasik" demiyoruz ama neyin
        # neyden cikarildigini sayfada yaziyoruz.
        cikti.append("Manşet enflasyona göre reel fonlama "
                     f"{_vir(reel, 2)} puan")
    if len(faiz) >= 30:
        onceki = faiz[-30][1]
        fark = faiz[-1][1] - onceki
        if abs(fark) >= 0.05:
            cikti.append(f"Fonlama maliyeti son 30 işlem gününde "
                         f"{round(fark * 100):+d} baz puan değişti")
        else:
            cikti.append("Fonlama maliyeti son 30 işlem gününde yatay")
    return cikti


def _bulgu_dis_ticaret(b, d) -> list[str]:
    cari = _seri(b, "TP.HARICCARIACIK.K1", 13)
    if len(cari) < 2:
        return []
    d.seyir, d.seyir_ad = cari, "Cari işlemler dengesi (mn $)"
    son = cari[-1][1]
    # "acikI" DEGIL "aciGI": Turkce'de sonu k ile biten sozcuk unlu ekten
    # once yumusar. Eki koda gomup "{yon}i" yazmak yanlis uretiyordu.
    # Cekimli bicimleri hazir tutmak tek dogru yol.
    ad = "fazlası" if son > 0 else "açığı"
    cikti = [f"Cari işlemler {ad} {abs(son):,.0f} mn $ ({cari[-1][0][:7]})"
             .replace(",", ".")]
    if len(cari) >= 12:
        # 12 aylik toplam, tek ayin gurultusunu temizler.
        toplam = sum(x[1] for x in cari[-12:])
        y = "fazla" if toplam > 0 else "açık"
        cikti.append(f"Son 12 ayın toplamı {abs(toplam):,.0f} mn $ {y}"
                     .replace(",", "."))
    return cikti


def _bulgu_issizlik(b, d) -> list[str]:
    s = _seri(b, "TP.YISGUCU2.G8", 13)
    if len(s) < 2:
        return []
    d.seyir, d.seyir_ad = s, "İşsizlik oranı (%)"
    cikti = [f"İşsizlik oranı %{_vir(s[-1][1], 1)} ({s[-1][0][:7]})"]
    if len(s) >= 12:
        alt, ust, n = _bant(s, 12)
        cikti.append(f"Son {n} ayda %{_vir(alt)}–%{_vir(ust)} aralığında")
    return cikti


def _bulgu_kur(b, d) -> list[str]:
    s = _seri(b, "TP.DK.USD.S.YTL", 260)
    if len(s) < 2:
        return []
    cikti = [f"USD/TRY {_vir(s[-1][1], 2)}"]
    for gun, ad in ((22, "1 ayda"), (66, "3 ayda")):
        if len(s) > gun:
            y = (s[-1][1] - s[-1 - gun][1]) / s[-1 - gun][1] * 100
            cikti.append(f"Kur {ad} %{_vir(abs(y))} "
                         f"{'arttı' if y >= 0 else 'geriledi'}")
    return cikti


URETECLER = {
    "enflasyon": _bulgu_enflasyon,
    "faiz": _bulgu_faiz,
    "dis_ticaret": _bulgu_dis_ticaret,
    "issizlik": _bulgu_issizlik,
    "kur": _bulgu_kur,
}

#: Bir sayfada en fazla kac bulgu. Uc satirdan sonrasi "30 saniyede"
#: kutusunu 30 saniyelik olmaktan cikariyor.
EN_COK_BULGU = 4


def _bulgulari_kur(b, d, konu: str) -> None:
    for ad in BULGU_KONULARI.get(konu, VARSAYILAN_BULGU):
        uretec = URETECLER.get(ad)
        if uretec is None:
            continue
        for satir in uretec(b, d):
            if satir not in d.bulgular:
                d.bulgular.append(satir)
        if len(d.bulgular) >= EN_COK_BULGU:
            del d.bulgular[EN_COK_BULGU:]
            return


# --------------------------------------------------------------------------
# Neden bugun
# --------------------------------------------------------------------------

#: Bir veri aciklamasindan sonra kac gun icinde cikan haber "bunun
#: ardindan" sayilir. Bes is gunu, yani bir hafta.
YAKINLIK_GUN = 7


def _neden_bugun(b: sqlite3.Connection, haber_tarihi: str,
                 konu: str) -> str:
    """Haberin hangi veri aciklamasinin ardindan geldigini soyler.

    HESAPLANIR, uydurulmaz: serilerin son gozlem tarihine bakiliyor.
    Yakinda bir aciklama yoksa BOS doner ve bolum basilmaz.
    """
    try:
        h = date.fromisoformat(haber_tarihi)
    except ValueError:
        return ""

    adaylar = [
        ("TP.TUKFIY2025.GENEL", "temmuz enflasyonu", "TÜFE"),
        ("TP.APIFON4", "", "politika faizi"),
    ]
    for kod, _, ad in adaylar:
        s = _seri(b, kod, 1)
        if not s:
            continue
        try:
            v = date.fromisoformat(s[0][0])
        except ValueError:
            continue
        # Aylik seri ayin ilkine sabitli; aciklama genelde ertesi ayin
        # ilk gunlerinde yapiliyor. Gozlem ayindan sonraki 40 gunu
        # "yakin" sayiyoruz.
        gun = (h - v).days
        if 0 <= gun <= 40 and ad == "TÜFE":
            return (f"{_ay_adi(v)} enflasyon verisinin açıklanmasının "
                    f"ardından yayımlandı")
    return ""


_AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _ay_adi(d: date) -> str:
    return _AYLAR[d.month - 1]


def tarih_tr(iso: str) -> str:
    try:
        y, a, g = (int(p) for p in iso.split("-"))
        return f"{_AYLAR[a - 1]} {y}"
    except (ValueError, IndexError):
        return iso


# --------------------------------------------------------------------------
# Ana giris
# --------------------------------------------------------------------------

#: Konu -> "Veri ne diyor" bolumunde kullanilacak bulgu uretecleri.
#:
#: ONCEDEN HEPSI TUFE'YDI ve olculen sonuc suydu: "Is Bankasi bilanco
#: acikladi", "Turkiye'nin findik ihracati", "TOKI kiralik konut" --
#: hepsinin altinda ayni cumle vardi: "Enflasyon 6 aydir %30,9-%32,6
#: bandinda". Dogru bir cumle ama haberle ilgisiz; okur "veri ne diyor"
#: basligi altinda haberin verisini bekler.
#:
#: Listede olmayan konu ENFLASYONA duser -- Turkiye'de fiyat gelismesi
#: hemen her makro haberin ortak zeminidir; ama artik bu bir SECIM,
#: tek secenek degil.
#: ANAHTARLAR `besleme.KONULAR` ile BIREBIR AYNI OLMALI.
#: Ilk yazimda dort anahtar uydurulmustu ("Istihdam ve ucretLER",
#: "Doviz ve kur", "Altin ve emtia", "Emeklilik ve sosyal guvenlik") ve
#: hicbiri eslesmedi: o konular sessizce varsayilana dustu, yani
#: istihdam haberinde issizlik yerine enflasyon yazildi. Hata gorunmez
#: cunku cikti yine makul bir cumle. `dogrula()` bunu sinar.
BULGU_KONULARI = {
    "Dış ticaret": ("dis_ticaret",),
    "Para politikası": ("enflasyon", "faiz"),
    "Enflasyon": ("enflasyon",),
    "Bankacılık": ("faiz",),
    "Konut ve kira": ("faiz",),
    "İstihdam ve ücret": ("issizlik", "enflasyon"),
    "Şirket haberleri": ("faiz", "kur"),
    "Enerji": ("kur", "dis_ticaret"),
    # Jeopolitik olayin Turkiye'ye yazildigi yer once cari denge, sonra
    # kur. Enflasyon burada uc adim uzakta kaliyor.
    "Jeopolitik": ("dis_ticaret", "kur"),
    "Tarım ve gıda": ("enflasyon",),
    "Turizm": ("kur", "dis_ticaret"),
    "Borsa": ("faiz", "kur"),
    "Vergi ve kamu maliyesi": ("enflasyon", "faiz"),
    "Düzenleme": ("faiz",),
    "Piyasa düzenlemesi": ("faiz",),
}
VARSAYILAN_BULGU = ("enflasyon",)


def dogrula() -> list[str]:
    """`BULGU_KONULARI` anahtarlarindan besleme listesinde olmayanlar.

    Sessiz kaymayi engelliyor: konu adi degistiginde ya da yanlis
    yazildiginda eslesme kaybolur ama sayfa yine dolu gorunur.
    """
    try:
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent
                              / "kaynak"))
        from besleme import KONULAR as _K
    except ImportError:
        return []
    adlar = {k[0] if isinstance(k, tuple) else k for k in _K}
    return sorted(k for k in BULGU_KONULARI if k not in adlar)

#: Haberin Turkiye ile ilgili oldugunu gosteren varlik kodlari.
#:
#: `bolge` alanindan DAHA GUVENILIR. Olculen sebep: bolge siniflandirmasi
#: Turkce basligi varsayilan olarak "TR" sayiyor, dolayisiyla Turk
#: kaynagin cevirdigi her yabanci haber de "TR" oluyordu -- "ABD'de
#: insaat harcamalari geriledi" haberinde Turkiye enflasyon paneli
#: basiliyordu. Varlik indeksi metnin NEDEN bahsettigine bakiyor.
TURKIYE_VARLIKLARI = frozenset({
    "TR", "TCMB", "TUIK", "SPK", "BDDK", "TUFE_TR", "UFE_TR", "TCMB_FAIZ",
    "CARI_TR", "DIS_TICARET_TR", "ISSIZLIK_TR", "BIST100", "USDTRY",
    "CDS_TR", "KARAHAN",
    "SEK_BANKA", "SEK_ENERJI", "SEK_OTOMOTIV", "SEK_TURIZM", "SEK_HAVA",
    "SEK_PERAKENDE", "SEK_INSAAT",
})


#: Yurt disi haberde de aktarim zinciri kurulan konular.
#:
#: Olcut su: haberin Turkiye'ye gecisi TAHMIN mi, MUHASEBE mi. Hurmuz
#: Bogazi'nda arz riski, Turkiye net enerji ithalatcisi oldugu icin
#: enerji faturasina yazilir -- bu muhasebedir. "New York borsasi
#: yukselisle kapandi" haberinin Turkiye'ye gecisi ise tahmindir; o
#: yuzden listede yok.
ZINCIR_KONULARI = frozenset({"Jeopolitik", "Enerji"})


def turkiye_haberi(bolge: str, varliklar) -> bool:
    """Haber Turkiye'yi mi anlatiyor.

    `varliklar` None ise varlik indeksi bagli degil demektir; o zaman
    eski olcut olan `bolge`ye duseriyor. Bos LISTE ise indeks calisti ve
    Turkiye varligi BULAMADI -- bu bir cevaptir, panel basilmaz.
    """
    if varliklar is None:
        return bolge == "TR"
    return bool(TURKIYE_VARLIKLARI & set(varliklar))


def kur(konu: str, bolge: str, haber_tarihi: str = "",
        varliklar=None, baslik: str = "", ozetsiz: bool = False) -> Dosya:
    """Haberin arastirma dosyasini kurar. Veri yoksa bos Dosya doner.

    `baslik`  bulten tespiti icin: basligi tek basina bir sey soylemeyen
              resmi duyurularda veriden acilis cumlesi uretiliyor.
    `ozetsiz` haberin kendi ozeti yok demektir; o zaman bulten olmasa da
              acilis cumlesi uretiliyor, cunku aksi halde sayfada hicbir
              metin kalmiyor.
    """
    tr = turkiye_haberi(bolge, varliklar)

    # DUYARLILIK / IZLENECEKLER / SENARYOLAR TURKIYE'YE OZGU.
    # Tablolar Turkiye sektorlerini ve Turkiye veri takvimini anlatiyor;
    # siradan bir yabanci haberde "En cok kim etkilenir: Konaklama,
    # Havayolu" yazmak kurulmamis bir aktarim zincirini kurulmus gibi
    # gostermek olurdu.
    #
    # JEOPOLITIK ISTISNA. Bu konuda aktarim zinciri haberin KENDISI:
    # Hurmuz Bogazi'ndaki bir gelisme Turkiye'ye enerji faturasi ve risk
    # primi uzerinden yazilir, cunku Turkiye net enerji ithalatcisidir --
    # bu bir tahmin degil, muhasebe. Yabanci olmasi tabloyu gecersiz
    # kilmiyor; tam tersine tablo o haber icin yazildi.
    zincir = tr or konu in ZINCIR_KONULARI
    d = Dosya(
        duyarlilik=(varlik_duyarliligi(varliklar, konu)
                    if zincir else ()),
        izlenecekler=IZLENECEKLER.get(konu, ()) if zincir else (),
        senaryolar=(varlik_senaryolari(varliklar, konu)
                    if zincir else ()),
    )
    if not DEPO.exists():
        return d

    # Turkiye GOSTERGE PANELI yalnizca Turkiye haberinde: Hurmuz
    # haberinin altina TUFE ve issizlik basmak, kullanicinin bildirdigi
    # hatanin ta kendisi olurdu.
    #
    # Ama YABANCI haberde de acilis cumlesi gerekebiliyor: ozeti olmayan
    # bir haberde sayfada hicbir metin kalmiyor. O yuzden burada erken
    # donmek yerine, panel bloguna girmeden yalnizca acilis uretiliyor.
    if not tr:
        if ozetsiz or (baslik and bulten_mi(baslik)):
            try:
                with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
                    d.acilis = _acilis(b, konu)
            except sqlite3.Error:
                pass
        return d

    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            for kod, ad, birim, _bas in TURKIYE_PANEL:
                g = _gosterge(b, kod, ad, birim)
                if g:
                    d.turkiye.append(g)

            faiz = _seri(b, REEL_FAIZ[0], 1)
            enf = _seri(b, REEL_FAIZ[1], 1)
            if faiz and enf:
                d.reel_faiz = faiz[0][1] - enf[0][1]

            _bulgulari_kur(b, d, konu)

            if (baslik and bulten_mi(baslik)) or ozetsiz:
                d.acilis = _acilis(b, konu)

            if haber_tarihi:
                d.neden_bugun = _neden_bugun(b, haber_tarihi, konu)

            # Seffaflik sayimi -- SKOR DEGIL, SAYIM.
            # "Veri Gucu 97" gibi bir puan olcum gibi gorunur ama
            # hesaplanmamistir; sayim ise dogrudur ve dogrulanabilir.
            kaynak = b.execute(
                "SELECT COUNT(DISTINCT kaynak) FROM gosterge").fetchone()
            gozlem = b.execute("SELECT COUNT(*) FROM gosterge").fetchone()
            seri_sayisi = b.execute(
                "SELECT COUNT(DISTINCT kod) FROM gosterge").fetchone()
            d.sayim = {
                "kaynak": kaynak[0] if kaynak else 0,
                "gozlem": gozlem[0] if gozlem else 0,
                "seri": seri_sayisi[0] if seri_sayisi else 0,
                "veri_noktasi": len(d.turkiye) + len(d.bulgular),
            }
    except sqlite3.Error:
        return d
    return d
