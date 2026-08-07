"""Veri aciklamalari -- seriden habere.

NEDEN VAR
---------
Besleme RSS okuyor; RSS'te olmayan haber siteye hic girmiyor. Olculen
sonuc: 266 haberde TEK BIR ADP, NFP ya da ABD TUFE kaydi yok. Oysa bir
finans sitesinin en degerli iceriklerinden biri veri aciklamalaridir --
gunu ve saati onceden bilinen, piyasayi hareket ettiren olaylar.

Kaynak zaten elimizde: FRED borusu fiyat ve getiri icin kullaniliyordu.
Ayni boru istihdam, enflasyon ve issizlik serilerini de veriyor.

FARKI SU: bu haberler VERIDEN uretiliyor, RSS'ten degil. Dolayisiyla
rakam, onceki deger ve degisim sayfada TANIM GEREGI var -- "haber var
ama icerik yok" sorunu bu hatta olusamaz.

NE URETILIR, NE URETILMEZ
-------------------------
URETILIR : Serinin YENI bir gozlemi geldiginde, bir kez.
URETILMEZ: Ayni gozlem icin ikinci kez (depoya bakilir), ya da gozlem
           `BAYAT_GUN`den eskiyse -- gecmisi haber diye yayimlamayiz.

YON YAZILMAZ, OLCUM YAZILIR
---------------------------
"Istihdam guclu geldi" bir yorumdur; "225 bin, onceki 190 bin" bir
olcumdur. Bu dosya yalnizca olcum uretir. Yorum katmani ayri.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))

import makro  # noqa: E402

#: Serinin NEDEN izlendigi. Sayfadaki "Neden onemli" bolumu.
#:
#: Bu metinler YAPISAL: kurumun gorevi, serinin tanimi ve hangi karara
#: girdigi. Yon ya da beklenti YOK -- "istihdam guclu gelirse Fed
#: beklemeye gecer" bir tahmindir; "istihdam Fed'in yasal cift
#: gorevinin bir ayagidir" bir olgudur.
#:
#: Seri kodu -> GOSTERGE NEDIR.
#:
#: `NEDEN` sozlugu "neden onemli"yi anlatiyor; bu sozluk "ne olctugunu".
#: Ikisi ayri soru ve okur once ikincisini soruyor -- ozellikle veri
#: HENUZ ACIKLANMAMISKEN. Bekleyis haberinde sayfada su cikiyordu:
#:
#:     "Verilen metinde sayisal bir olcum bulunmadigi icin, olculen bir
#:      degeri secip yorumlamak mumkun degildir."
#:
#: Aciklanmamis bir veri icin bu dogru ama ise yaramaz bir cumle.
#: Oysa veri gelmeden once de soylenecek gercek seyler var: gosterge ne
#: olcuyor, kim yayimliyor, hangi siklikta, neyi etkiliyor.
TANIM: dict[str, str] = {
    "PAYEMS":
        "Tarım dışı istihdam, ABD ekonomisinde bir ay içinde tarım "
        "sektörü dışında oluşan net istihdam değişimini ölçer. Çalışma "
        "İstatistikleri Bürosu (BLS) her ayın ilk cuma günü yayımlar; "
        "işletme anketine dayanır ve sonraki iki ayda revize edilir.",
    "UNRATE":
        "İşsizlik oranı, iş arayan ve çalışmaya hazır kişilerin iş "
        "gücüne oranıdır. Hanehalkı anketinden gelir, yani istihdam "
        "verisinden farklı bir kaynağa dayanır; ikisi aynı ay farklı "
        "yön gösterebilir.",
    "CES0500000003":
        "Ortalama saatlik kazanç, özel sektörde saat başına ödenen "
        "ücretin ortalamasıdır. Ücret artışı hizmet enflasyonunun ana "
        "girdisi olduğu için istihdam raporunun en çok izlenen "
        "kalemlerinden biridir.",
    "ICSA":
        "Haftalık işsizlik başvuruları, ilk kez işsizlik ödeneğine "
        "başvuran kişi sayısıdır. Haftalık yayımlandığı için iş gücü "
        "piyasasındaki dönüşü en erken gösteren seridir.",
    "ADPMNUSNERSA":
        "ADP istihdam raporu, özel sektör bordro verisinden üretilir ve "
        "resmî istihdam verisinden iki gün önce gelir. Aynı şeyi "
        "ölçmez: yöntemi ve kapsamı farklıdır, bu yüzden ikisi "
        "ayrışabilir.",
    "CPIAUCSL":
        "Tüketici fiyat endeksi, hanehalkının satın aldığı mal ve "
        "hizmet sepetinin fiyat değişimini ölçer. BLS yayımlar; Fed'in "
        "hedefi bu seri değil çekirdek PCE'dir, ama piyasa en çok bunu "
        "fiyatlar.",
    "CPILFESL":
        "Çekirdek TÜFE, gıda ve enerjiyi dışlayan fiyat endeksidir. Bu "
        "iki kalem arz şoklarıyla savrulduğu için, enflasyonun kalıcı "
        "eğilimi çekirdekte okunur.",
    "PCEPILFE":
        "Çekirdek PCE, Fed'in resmen tercih ettiği enflasyon ölçüsüdür. "
        "TÜFE'den farklı ağırlıklandırma ve ikame varsayımı kullanır; "
        "politika metinlerinde referans alınan seri budur.",
    "PPIFIS":
        "Üretici fiyat endeksi (nihai talep), üreticinin sattığı mal ve "
        "hizmetin fiyat değişimini ölçer. Maliyet tarafındaki baskıyı "
        "tüketici fiyatlarından önce gösterir.",
    "GDPC1":
        "Reel gayrisafi yurt içi hasıla, enflasyondan arındırılmış "
        "toplam üretimdir. Çeyreklik yayımlanır ve öncü, ikinci, "
        "nihai olmak üzere üç kez açıklanır.",
    "RSAFS":
        "Perakende satışlar, hanehalkı harcamasının en hızlı gelen "
        "göstergesidir. ABD ekonomisinin yaklaşık üçte ikisi tüketim "
        "olduğu için büyüme beklentisine doğrudan girer.",
    "FED_FAIZ":
        "Fed politika faizi, Federal Açık Piyasa Komitesi'nin belirlediği "
        "gecelik fonlama hedefidir. Kararla birlikte yayımlanan bildiri "
        "ve üye projeksiyonları çoğu zaman kararın kendisinden daha çok "
        "fiyatlanır.",
    "TP.TUKFIY2025.GENEL":
        "TÜFE, Türkiye'de hanehalkının satın aldığı mal ve hizmet "
        "sepetinin fiyat değişimidir. TÜİK her ayın ilk iş günlerinde "
        "yayımlar; kira, asgari ücret ve birçok sözleşme bu seriye "
        "endekslidir.",
    "TP.FE25.OKTG04":
        "Çekirdek enflasyon (C endeksi), enerji, gıda, alkollü içecek, "
        "tütün ve altını dışlar. Para politikasının etkileyebildiği "
        "fiyat eğilimi burada okunur.",
    "TP.TUFE1YI.T1":
        "Yurt içi üretici fiyat endeksi, üreticinin maliyet tarafını "
        "ölçer. Tüketici fiyatlarına geçiş gecikmeli olur ve geçişin "
        "büyüklüğü sektörün fiyatlama gücüne bağlıdır.",
    "TP.YISGUCU2.G8":
        "İşsizlik oranı, iş gücüne katılan ve iş arayanların oranıdır. "
        "TÜİK hanehalkı iş gücü anketinden üretir; iş gücüne katılım "
        "oranıyla birlikte okunmadığında yanıltıcı olabilir.",
    "TP.HARICCARIACIK.K1":
        "Cari işlemler dengesi, ülkenin dış dünyayla mal, hizmet ve "
        "gelir alışverişinin net sonucudur. Açık, dışarıdan finansman "
        "ihtiyacı demektir ve o ihtiyacın maliyeti küresel faiz "
        "koşullarına bağlıdır.",
    "TP.APIFON4":
        "TCMB ağırlıklı ortalama fonlama maliyeti, bankaların Merkez "
        "Bankası'ndan fonlandığı efektif faizdir. Politika faizinden "
        "sapabilir; piyasanın fiilen ödediği maliyet budur.",
    "TP.ENFBEK.PKA12ENF":
        "Piyasa katılımcıları anketi, profesyonel tahmincilerin 12 ay "
        "sonrası enflasyon beklentisini ölçer. Beklentilerin çıpadan "
        "kopması merkez bankalarının en açık tepki verdiği "
        "gelişmelerden biridir.",
}


#: Serisi olan her habere yaziliyor cunku eksikligi olculdu: veri
#: haberlerinin "Neden onemli" bolumu tamamen BOS basiliyordu.
NEDEN = {
    "PAYEMS":
        "Tarım dışı istihdam, Fed'in yasayla tanımlı çift görevinin "
        "istihdam ayağıdır; para politikası kararına doğrudan girdi olan "
        "iki seriden biridir. Ay sonu revizyonları büyük olabildiği için "
        "ilk okuma ile nihai değer farklılaşır.",
    "ADPMNUSNERSA":
        "ADP raporu özel sektör istihdamını resmî veriden önce ölçer ve "
        "bu yüzden tarım dışı istihdam için erken gösterge sayılır. "
        "Kapsamı ve yöntemi resmî seriden farklıdır; ikisi arasında "
        "sistematik sapma görülebilir.",
    "UNRATE":
        "İşsizlik oranı, Fed'in istihdam hedefinin en görünür ölçüsüdür. "
        "İşgücüne katılım oranı değiştiğinde oran istihdam artmadan da "
        "düşebilir; bu yüzden tek başına okunmaz.",
    "ICSA":
        "Haftalık işsizlik başvuruları, işgücü piyasasının en yüksek "
        "frekanslı göstergesidir; aylık verilerden önce dönüş noktalarını "
        "gösterebilir.",
    "CES0500000003":
        "Saatlik kazanç artışı, hizmet enflasyonunun ana maliyet "
        "bileşenidir. Ücret artışı verimlilik artışını aştığında birim "
        "işgücü maliyeti üzerinden fiyatlara geçiş kanalı açılır.",
    "CPIAUCSL":
        "ABD tüketici enflasyonu, küresel faiz beklentisinin ana "
        "girdisidir. ABD faiz patikası değiştiğinde gelişmekte olan ülke "
        "borçlanma maliyeti ve sermaye akımları yeniden fiyatlanır.",
    "CPILFESL":
        "Çekirdek TÜFE gıda ve enerjiyi dışlar; fiyat artışının geçici "
        "mi yoksa yaygın mı olduğunu ayırmak için kullanılır.",
    "PCEPILFE":
        "Çekirdek PCE, Fed'in resmen tercih ettiği enflasyon ölçüsüdür. "
        "TÜFE'den farklı ağırlıklandırma kullandığı için iki seri "
        "ayrışabilir; politika metinlerinde referans alınan budur.",
    "PPIFIS":
        "Üretici fiyatları, maliyet tarafındaki baskıyı tüketici "
        "fiyatlarından önce gösterir. Geçişin hızı ve büyüklüğü sektörün "
        "fiyatlama gücüne bağlıdır.",
    "MICH":
        "Enflasyon beklentisi, ücret ve fiyat kararlarının girdisidir. "
        "Beklentilerin çıpadan kopması merkez bankalarının en açık "
        "biçimde tepki verdiği gelişmelerden biridir.",
    "GDPC1":
        "Reel büyüme, kâr beklentilerinin ve vergi gelirlerinin ortak "
        "zeminidir. Çeyreklik ve gecikmeli yayımlandığı için piyasa "
        "genellikle öncü göstergeleri izler.",
    "RSAFS":
        "Perakende satışlar, ABD ekonomisinin yaklaşık üçte ikisini "
        "oluşturan hanehalkı tüketiminin en hızlı okunan ölçüsüdür.",
    "INDPRO":
        "Sanayi üretimi, emtia talebinin ve küresel ticaret hacminin "
        "öncü göstergelerinden biridir; Türkiye'nin ihracat pazarlarına "
        "dair sinyal taşır.",
    "UMCSENT":
        "Tüketici güveni, harcama eğiliminin öncü göstergesidir. "
        "Seviyeden çok yönü ve hızı okunur.",
    "HOUST":
        "Konut başlangıçları faize en duyarlı talep kalemlerinden "
        "biridir; para politikasının reel ekonomiye geçişini erken "
        "gösterir.",
}

#: (kod, ad, birim, konu, sıklık, önem, sunum)
#:
#: `sunum`: "seviye"    -- serinin degeri okunur (issizlik %4,3)
#:          "degisim"   -- onceki doneme gore FARK okunur
#:          "yillik"    -- 12 ay onceye gore yuzde degisim okunur
#:
#: SUNUM ALANI NEDEN VAR: bazi serilerde seviye anlamsizdir. PAYEMS
#: 158.984 (bin kisi) yazmak okura hicbir sey soylemez; o seride okunan
#: sey AYLIK DEGISIMDIR ("+147 bin"). Endeks serilerinde (TUFE) ise
#: seviye de degisim de anlamsiz; okunan YILLIK yuzde degisimdir.
#:
#: SECIM OLCUTU: gunu onceden belli, piyasayi hareket ettiren ve FRED'de
#: UCRETSIZ bulunan seriler. Kodlarin HEPSI tek tek dogrulandi -- ilk
#: yazimda iki kod olu cikti: `NPPTTL` (ADP) 2022'de durmus, `WCESTUS1`
#: (petrol stogu) hic yok. Ikisi de sessizce bos donuyordu.
SERILER: tuple[tuple[str, str, str, str, str, int, str], ...] = (
    # --- ABD istihdam ---
    ("PAYEMS", "ABD Tarım Dışı İstihdam", "bin kişi",
     "İstihdam ve ücret", "aylık", 10, "degisim"),
    # ADP'nin GUNCEL serisi bu. `NPPTTL` 2022'de durduruldu; kurum
    # yontemini degistirdi ve seriyi yeniledi.
    ("ADPMNUSNERSA", "ABD Özel Sektör İstihdamı (ADP)", "kişi",
     "İstihdam ve ücret", "aylık", 8, "degisim"),
    ("ICSA", "ABD haftalık işsizlik başvuruları", "kişi",
     "İstihdam ve ücret", "haftalık", 6, "seviye"),
    ("UNRATE", "ABD işsizlik oranı", "%",
     "İstihdam ve ücret", "aylık", 8, "seviye"),
    # SEVIYE DEGIL YILLIK DEGISIM.
    #
    # Seviye ($37,64) piyasanin izledigi buyukluk degil; aciklamada
    # manset olan aylik/yillik DEGISIM. Seviye esik yapilinca kutu
    # sacmaliyor: bir sonraki ay 37,70 gelse "37,64 uzerinde" olur ama
    # bu %0,16'lik artis demek, yani beklentinin (%0,3) ALTINDA.
    # Kullanicinin Tarim Disi Istihdam'da gosterdigi hatanin aynisi.
    ("CES0500000003", "ABD ortalama saatlik kazanç", "%",
     "İstihdam ve ücret", "aylık", 7, "yillik"),

    # --- ABD enflasyon ---
    ("CPIAUCSL", "ABD TÜFE", "%", "Enflasyon", "aylık", 10, "yillik"),
    ("CPILFESL", "ABD çekirdek TÜFE", "%", "Enflasyon", "aylık", 9, "yillik"),
    # Fed'in tercih ettigi olcu -- politika kararina en yakin seri.
    ("PCEPILFE", "ABD çekirdek PCE", "%", "Enflasyon", "aylık", 9, "yillik"),
    # MANSET UFE SERISI `PPIFIS` (nihai talep), `PPIACO` DEGIL.
    #
    # Olculdu: ayni gun PPIACO yillik %10,11, PPIFIS %5,51. Ikisi de
    # dogru hesap ama farkli sey olcuyor -- PPIACO "tum emtialar" ham
    # endeksi, ham madde fiyatlariyla savruluyor. BLS'in "Producer
    # Price Index" haberinde manset olan, piyasanin fiyatladigi ve
    # Fed'in konustugu seri NIHAI TALEP.
    #
    # "ABD ÜFE" etiketiyle %10,11 basmak, okura manset UFE'yi iki kat
    # yuksek gostermek olurdu.
    ("PPIFIS", "ABD ÜFE (nihai talep)", "%",
     "Enflasyon", "aylık", 7, "yillik"),
    ("MICH", "ABD tüketici enflasyon beklentisi", "%",
     "Enflasyon", "aylık", 6, "seviye"),

    # --- ABD buyume ve talep ---
    ("GDPC1", "ABD reel GSYH", "%", "Borsa", "çeyreklik", 9, "yillik"),
    ("RSAFS", "ABD perakende satışlar", "%", "Borsa", "aylık", 7, "yillik"),
    ("INDPRO", "ABD sanayi üretimi", "%", "Borsa", "aylık", 6, "yillik"),
    ("UMCSENT", "ABD tüketici güveni (Michigan)", "endeks",
     "Borsa", "aylık", 6, "seviye"),
    ("HOUST", "ABD konut başlangıçları", "bin adet",
     "Konut ve kira", "aylık", 6, "seviye"),
)

#: TURKIYE SERILERI -- kaynak EVDS, FRED degil.
#:
#: Ayri tabloda cunku cekme yolu farkli: FRED anahtarsiz CSV veriyor,
#: EVDS anahtar ve kendi tarih bicimini istiyor. Ayrica bu seriler
#: okurun ASIL ilgilendigi veriler; ABD takvimi onlarin baglami.
YERLI_SERILER: tuple[tuple[str, str, str, str, str, int, str], ...] = (
    ("TP.TUKFIY2025.GENEL", "TÜFE", "%", "Enflasyon", "aylık", 10, "seviye"),
    ("TP.FE25.OKTG04", "Çekirdek enflasyon (C)", "%",
     "Enflasyon", "aylık", 9, "seviye"),
    ("TP.TUFE1YI.T1", "Yİ-ÜFE", "%", "Enflasyon", "aylık", 8, "seviye"),
    ("TP.YISGUCU2.G8", "İşsizlik oranı", "%",
     "İstihdam ve ücret", "aylık", 8, "seviye"),
    ("TP.HARICCARIACIK.K1", "Cari işlemler dengesi", "mn $",
     "Dış ticaret", "aylık", 9, "seviye"),
    ("TP.APIFON4", "TCMB ağırlıklı ortalama fonlama maliyeti", "%",
     "Para politikası", "günlük", 7, "seviye"),
    ("TP.ENFBEK.PKA12ENF", "Piyasa katılımcılarının enflasyon beklentisi", "%",
     "Enflasyon", "aylık", 8, "seviye"),
    ("TP.ENFBEK.HBA12ENF", "Hanehalkının enflasyon beklentisi", "%",
     "Enflasyon", "aylık", 6, "seviye"),
)

#: Yerli serilerin "neden onemli" metinleri.
YERLI_NEDEN = {
    "TP.TUKFIY2025.GENEL":
        "TÜFE yalnızca bir fiyat ölçüsü değildir; politika faizi "
        "kararlarının, kira ve ücret yenilemelerinin ve TMS 29 enflasyon "
        "muhasebesinin ortak girdisidir.",
    "TP.FE25.OKTG04":
        "Çekirdek gösterge gıda, enerji, alkol-tütün ve altını dışlar. "
        "Manşetle çekirdek arasındaki fark, fiyat artışının geçici mi "
        "yaygın mı olduğunu ayırmakta kullanılır.",
    "TP.TUFE1YI.T1":
        "Yurt içi üretici fiyatları, maliyet tarafındaki baskıyı tüketici "
        "fiyatlarından önce gösterir. Geçişin hızı sektörün fiyatlama "
        "gücüne ve kur seviyesine bağlıdır.",
    "TP.YISGUCU2.G8":
        "İşsizlik oranı işgücüne katılanlar içinde iş arayıp "
        "bulamayanların oranıdır. Geniş tanımlı atıl işgücü oranı ayrı "
        "yayımlanır ve daha yüksektir; ikisi birlikte okunur.",
    "TP.HARICCARIACIK.K1":
        "Cari işlemler dengesi Türkiye'nin dış finansman ihtiyacının ana "
        "ölçüsüdür. Enerji faturası bu kalemin en büyük bileşenlerinden "
        "biridir; petrol fiyatı buraya doğrudan yazılır.",
    "TP.APIFON4":
        "TCMB'nin ağırlıklı ortalama fonlama maliyeti, bankaların "
        "Merkez Bankası'ndan borçlanma maliyetidir ve ticari kredi "
        "faizinin çıpasıdır.",
    "TP.ENFBEK.PKA12ENF":
        "Piyasa katılımcılarının 12 ay sonrası enflasyon beklentisi, "
        "TCMB'nin anketle ölçtüğü çıpa göstergesidir. Beklentinin hedefe "
        "yakınsaması para politikasının açık amaçlarından biridir.",
    "TP.ENFBEK.HBA12ENF":
        "Hanehalkı beklentisi ücret pazarlığına ve harcama kararına "
        "girer. Piyasa katılımcılarının beklentisinden sistematik olarak "
        "yüksek seyreder; seviyeden çok yönü okunur.",
}

#: Gozlem bundan eskiyse haber URETILMEZ. Siklik basina ayri esik.
#:
#: OLCUT GOZLEM TARIHI, YAYIN TARIHI DEGIL -- ve ikisi cok farkli.
#: Aylik seri ayin BASINI tarihler ama ayin ortasinda yayimlanir:
#: "2026-06-01" satiri haziran verisidir ve 3 Temmuz'da cikar. Ilk
#: yazimda tek bir 45 gunluk esik vardi ve butun aylik seriler
#: "atlandi: 64 gun" diye eleniyordu -- yani hat calisiyor ama HICBIR
#: aylik veri haberi uretmiyordu.
BAYAT_GUN = {"haftalık": 21, "aylık": 75, "çeyreklik": 150}
BAYAT_VARSAYILAN = 75


@dataclass(frozen=True)
class Aciklama:
    kod: str
    ad: str
    birim: str
    konu: str
    siklik: str
    onem: int
    sunum: str
    tarih: str
    deger: float
    onceki: float | None
    #: 12 dönem önceki değer -- yillik degisim icin
    yil_once: float | None = None
    #: Okunan buyuklugun son 12 donemlik ortalamasi -- karsilastirma cipasi
    ortalama: float | None = None

    @property
    def fark(self) -> float | None:
        if self.onceki is None:
            return None
        return self.deger - self.onceki

    @property
    def yillik(self) -> float | None:
        if not self.yil_once:
            return None
        return (self.deger - self.yil_once) / self.yil_once * 100

    @property
    def okunan(self) -> float | None:
        """Sunuma gore okura GOSTERILEN sayi."""
        if self.sunum == "degisim":
            return self.fark
        if self.sunum == "yillik":
            return self.yillik
        return self.deger

    @property
    def adres(self) -> str:
        """Haberin kimligi. Kod + gozlem tarihi -- ayni gozlem ikinci kez
        geldiginde depo onu TEKRAR olarak taniyor ve haber uretilmiyor."""
        return f"netaris:veri/{self.kod}/{self.tarih}"


def _tr(x: float, basamak: int) -> str:
    """Turkce sayi: binlik nokta, ondalik virgul."""
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _kisi(x: float) -> str:
    """Kisi sayisini okunur buyuklukte yazar.

    ADP serisi KISI cinsinden geliyor (132.763.000) ve aylik degisim
    ~100.000 mertebesinde. "103.000 kisi" yerine "103 bin kisi" hem
    kisa hem sektorun konustugu bicim.
    """
    b = abs(x)
    if b >= 1_000_000:
        return f"{_tr(x / 1_000_000, 2)} milyon"
    if b >= 1000:
        return f"{_tr(x / 1000, 0)} bin"
    return _tr(x, 0)


def bicim(d: float | None, birim: str) -> str:
    """Disariya acik ad. Takvim kutulari da BU bicimlendiriciyi kullanir.

    Ikinci bir bicimlendirici yazmak olculdu ve kaydi: `beklenti.py`
    kendi `bicimle`sini kullaniyordu ve ayni sayi iki yerde iki turlu
    goruniyordu -- haberde "44 bin kişi", takvimde "44.000,00 kişi".
    """
    return _bicim(d, birim)


def _bicim(d: float | None, birim: str) -> str:
    """Sayiyi birimiyle Turkce yazar.

    ISARET YUZDENIN ONUNDE: "%-0,10" okunmuyor, "−%0,10" okunuyor.
    Turkce'de yuzde isareti sayidan ONCE gelir ve eksi ondan da once.

    "bin kişi" BIN KATI: FRED'in PAYEMS serisi BIN KISI cinsinden
    (158.984 = 159 milyon kisi), ADP serisi ise KISI cinsinden
    (132.763.000). Ayni kavram, farkli olcek. Ilk yazimda ikisi de kisi
    sayilmis ve PAYEMS'in aylik degisimi "57 kişi" cikmisti -- dogrusu
    57 BIN kisi.
    """
    if d is None:
        return "—"
    if birim == "%":
        isaret = "−" if d < 0 else ""
        return f"{isaret}%{_tr(abs(d), 2)}"
    if birim == "bin kişi":
        return f"{_kisi(d * 1000)} kişi"
    if birim == "kişi":
        return f"{_kisi(d)} kişi"
    if birim == "bin adet":
        return f"{_tr(d, 0)} bin adet"
    if birim == "$":
        isaret = "−" if d < 0 else ""
        return f"{isaret}{_tr(abs(d), 2)} $"
    if birim in ("mn $", "mlr $"):
        return f"{_tr(d, 0)} {birim}"
    return _tr(d, 1)


def baslik(a: Aciklama) -> str:
    """Haber basligi -- RAKAM BASLIKTA.

    "ABD Tarim Disi Istihdam aciklandi" hicbir sey soylemiyor: okurda
    beklenti kurmuyor, arama sonucunda tiklanmiyor ve sayfaya girince
    ogrenilecek sey basliktan tahmin edilemiyor. Rakam basliga girince
    baslik kendi basina bilgi tasiyor.
    """
    d = a.okunan
    if d is None:
        return f"{a.ad}: {_donem(a)} verisi açıklandı"
    if a.sunum == "degisim":
        return (f"{a.ad}: {_donem(a)} döneminde "
                f"{_bicim(abs(d), a.birim)} "
                f"{'artış' if d >= 0 else 'azalış'}")
    if a.sunum == "yillik":
        return f"{a.ad}: yıllık {_bicim(d, '%')}"
    return f"{a.ad}: {_bicim(d, a.birim)}"


def ozet(a: Aciklama) -> str:
    """Haberin govdesi. Yalnizca OLCUM -- yorum yok.

    "Istihdam guclu geldi" bir yorumdur; "103 bin, onceki 76 bin" bir
    olcumdur. Bu dosya yalnizca ikincisini uretir.
    """
    p = []
    if a.sunum == "degisim" and a.fark is not None:
        p.append(f"{a.ad}, {_donem(a)} döneminde "
                 f"{_bicim(abs(a.fark), a.birim)} "
                 f"{'arttı' if a.fark >= 0 else 'azaldı'}.")
        p.append(f"Seri seviyesi {_bicim(a.deger, a.birim)}.")
    elif a.sunum == "yillik" and a.yillik is not None:
        p.append(f"{a.ad}, {_donem(a)} döneminde yıllık "
                 f"{_bicim(a.yillik, '%')} olarak gerçekleşti.")
        if a.onceki is not None and a.yil_once:
            p.append(f"Endeks {_tr(a.deger, 2)}; bir önceki dönem "
                     f"{_tr(a.onceki, 2)}.")
    else:
        p.append(f"{a.ad}, {_donem(a)} dönemi için "
                 f"{_bicim(a.deger, a.birim)} olarak açıklandı.")
        if a.onceki is not None:
            p.append(f"Önceki dönem {_bicim(a.onceki, a.birim)}; değişim "
                     f"{_bicim(a.fark, a.birim)}.")
    # KARSILASTIRMA CIPASI.
    #
    # "Beklenti neydi?" sorusunu ucretsiz konsensus verisi olmadigi icin
    # cevaplayamiyoruz. Uydurmak yerine OLCULEBILIR bir cipa
    # veriliyor: serinin son 12 donemlik ortalamasi. "44 bin geldi,
    # beklenti 60 bindi" diyemiyoruz ama "44 bin geldi, son 12 ayin
    # ortalamasi 71 bin" diyebiliyoruz -- ve bu bir olcum, tahmin degil.
    if a.ortalama is not None and a.okunan is not None:
        birim = "%" if a.sunum == "yillik" else a.birim
        p.append(f"Son 12 dönem ortalaması {_bicim(a.ortalama, birim)}.")

    kaynak = ("TCMB EVDS" if a.kod.startswith("TP.")
              else "FRED (St. Louis Fed)")
    p.append(f"Veri {kaynak} üzerinden {a.kod} serisinden alınmıştır; "
             f"yorum içermez.")
    return " ".join(p)


_AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def tarih_tr(iso: str) -> str:
    """ISO tarihi "5 Ağustos 2026" biçimine cevirir."""
    try:
        y, ay, g = iso[:10].split("-")
        return f"{int(g)} {_AYLAR[int(ay) - 1]} {y}"
    except (ValueError, IndexError):
        return iso[:10]


def _donem(a: Aciklama) -> str:
    try:
        y, ay, g = a.tarih[:10].split("-")
        if a.siklik == "haftalık":
            return f"{int(g)} {_AYLAR[int(ay) - 1]} {y} haftası"
        if a.siklik == "çeyreklik":
            return f"{y} {(int(ay) - 1) // 3 + 1}. çeyrek"
        return f"{_AYLAR[int(ay) - 1]} {y}"
    except (ValueError, IndexError):
        return a.tarih[:10]


def _ortalama(g, sunum: str, adim: int, n: int = 12) -> float | None:
    """Okunan buyuklugun son `n` donemlik ortalamasi.

    SUNUMA GORE hesaplaniyor: "degisim" serisinde seviyelerin degil
    FARKLARIN ortalamasi anlamli. Tarim disi istihdamda "son 12 ayin
    ortalamasi 159 milyon" bilgi tasimaz; "ortalama aylik artis 71 bin"
    tasir.
    """
    d = [float(x.deger) for x in g if x.deger is not None]
    if len(d) < 3:
        return None
    if sunum == "degisim":
        farklar = [d[i] - d[i - 1] for i in range(1, len(d))][-n:]
        return sum(farklar) / len(farklar) if farklar else None
    if sunum == "yillik":
        if len(d) <= adim + 1:
            return None
        y = [(d[i] - d[i - adim]) / d[i - adim] * 100
             for i in range(adim, len(d)) if d[i - adim]][-n:]
        return sum(y) / len(y) if y else None
    son = d[-n:]
    return sum(son) / len(son)


def cek_yerli(bugun: str) -> list[Aciklama]:
    """Turkiye serilerini EVDS'den ceker.

    Anahtar yoksa BOS liste doner ve hat kirmizi donmez -- ABD tarafi
    calismaya devam etmeli.
    """
    from datetime import date

    try:
        import evds
    except ImportError:
        return []
    if not evds.anahtar():
        print("  EVDS_ANAHTARI yok -- yerli seriler atlandi")
        return []

    try:
        b = date.fromisoformat(bugun[:10])
    except (ValueError, TypeError):
        b = date.today()

    # FORMUL SERININ KENDISINDEN OKUNUYOR, SABIT YAZILMIYOR.
    #
    # `evds.SERILER` her seri icin dogru formulu tutuyor: TUFE ham
    # endeks olarak geliyor ve YILLIK_YUZDE formuluyle istenmezse
    # seviye doner. Ilk yazimda `DUZEY` sabitlenmisti ve olculen sonuc
    # suydu:
    #
    #   "TUFE: %132,31"   <- endeks seviyesi, yillik oran degil
    #   "Yi-UFE: %5.637"  <- ayni hata, daha gorunur
    #
    # Sayfa dogru gorunuyordu; yalnizca rakam yanlisti.
    formuller = {s[0]: s[3] for s in evds.SERILER}

    cikti: list[Aciklama] = []
    for kod, ad, birim, konu, siklik, onem, sunum in YERLI_SERILER:
        frekans = evds.GUNLUK if siklik == "günlük" else evds.AYLIK
        s = evds.cek(kod, ad, birim, formuller.get(kod, evds.DUZEY),
                     frekans, gun=800)
        if not s or not s.gozlemler:
            print(f"  {kod:<22} alinamadi")
            continue
        g = s.gozlemler
        son = g[-1]
        try:
            yas = (b - date.fromisoformat(son.tarih[:10])).days
        except ValueError:
            continue
        esik = BAYAT_GUN.get(siklik, BAYAT_VARSAYILAN)
        if siklik == "günlük":
            esik = 7
        if yas > esik:
            print(f"  {kod:<22} atlandi: {son.tarih} ({yas} gun > {esik})")
            continue
        adim = 12 if siklik == "aylık" else 250
        a = Aciklama(
            kod=kod, ad=ad, birim=birim, konu=konu, siklik=siklik,
            onem=onem, sunum=sunum, tarih=son.tarih,
            deger=float(son.deger),
            onceki=float(g[-2].deger) if len(g) > 1 else None,
            yil_once=float(g[-1 - adim].deger) if len(g) > adim else None,
            ortalama=_ortalama(g, sunum, adim),
        )
        cikti.append(a)
        print(f"  {kod:<22} {son.tarih}  {baslik(a)[:52]}")
    return cikti


def cek(bugun: str, gecmis: int = 8) -> list[Aciklama]:
    """Butun serileri ceker, TAZE gozlemleri Aciklama olarak dondurur.

    Ag hatasi tek seriyi dusurur, hatti degil: bir seri cekilemedigi
    icin butun veri aciklamalarini kaybetmek yanlis olurdu.
    """
    from datetime import date

    try:
        b = date.fromisoformat(bugun[:10])
    except (ValueError, TypeError):
        b = date.today()

    cikti: list[Aciklama] = []
    for kod, ad, birim, konu, siklik, onem, sunum in SERILER:
        try:
            # Yillik degisim icin 13 gozlem gerekiyor; haftalikta 60.
            n = 60 if siklik == "haftalık" else max(gecmis, 14)
            s = makro.fred(kod, son_n=n)
        except Exception as e:                      # ag, kota, bicim
            print(f"  {kod:<16} alinamadi: {str(e)[:60]}")
            continue
        g = [x for x in s.gozlemler if x.deger is not None]
        if not g:
            print(f"  {kod:<16} bos seri")
            continue
        son = g[-1]
        try:
            yas = (b - date.fromisoformat(son.tarih[:10])).days
        except ValueError:
            continue
        esik = BAYAT_GUN.get(siklik, BAYAT_VARSAYILAN)
        if yas > esik:
            print(f"  {kod:<16} atlandi: son gozlem {son.tarih} "
                  f"({yas} gun > {esik})")
            continue

        # Yillik karsilastirma icin 12 donem oncesi. Haftalik seride 52.
        adim = 52 if siklik == "haftalık" else (4 if siklik == "çeyreklik" else 12)
        yil_once = float(g[-1 - adim].deger) if len(g) > adim else None

        a = Aciklama(
            kod=kod, ad=ad, birim=birim, konu=konu, siklik=siklik,
            onem=onem, sunum=sunum, tarih=son.tarih,
            deger=float(son.deger),
            onceki=float(g[-2].deger) if len(g) > 1 else None,
            yil_once=yil_once,
            ortalama=_ortalama(g, sunum, adim),
        )
        # Sunum "yillik" ama 12 donem gecmis yoksa haber KURULAMAZ:
        # okunacak sayi hesaplanamiyor demektir.
        if a.okunan is None:
            print(f"  {kod:<16} atlandi: {sunum} icin yeterli gecmis yok")
            continue
        cikti.append(a)
        print(f"  {kod:<16} {son.tarih}  {baslik(a)[:56]}")
    return cikti
