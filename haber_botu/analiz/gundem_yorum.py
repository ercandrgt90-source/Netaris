"""Gundem haberlerine baglam ekler -- kural tabanli, model kullanmadan.

NEDEN MODEL DEGIL
-----------------
Bir dil modeline "bu haber neyi etkiler" diye sormak, dogrulanamayan bir
cevap uretir ve her calistirmada farkli olur. Oysa aktarim kanallari
YAPISALDIR ve degismez: Fed faizi degistiginde gelismekte olan ulke
borclanma maliyeti etkilenir -- bu bir tahmin degil, mekanik bir iliski.

Bu yuzden yorum katmani da kod: hangi konunun hangi kanallardan gectigi
burada tanimli, her haber ayni konuda ayni kanallari gosterir.

IKI SINIF
---------
YORUMLANMAZ (rutin): tek bir bankaya kesilen ceza, komite toplanti
    duyurusu, atama, teknik/idari bildirim. Bunlarda "neyi etkiler"
    sorusunun anlamli bir cevabi yok; zorlama yorum eklemek okuru yorar
    ve guveni asindirir.

YORUMLANIR (etkili): faiz karari, para politikasi metni, enflasyon
    verisi, enerji piyasasi gelismesi, sistemik duzenleme. Bunlarda
    aktarim kanallari anlatilir.

NE YAZILMAZ
-----------
Yon tahmini ("faiz inecek"), buyukluk tahmini ("TUFE'yi 2 puan artirir"),
al/sat onerisi. Yalnizca KANAL soylenir: "su kalem su yoldan su tarafi
etkiler". Etkinin buyuklugu model gerektirir, uydurulmaz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Turkce harfleri ASCII karsiligina indirir.
#:
#: Her modulde ayri bir tablo duruyor; bu bilincli. Bu dosya yalnizca
#: stdlib'e dayaniyor ve baska bir moduleden ice aktarma yapmiyor -- boylece
#: analiz katmani kaynak katmanina bagimli hale gelmiyor.
_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _katla(metin: str) -> str:
    # Once translate, SONRA lower -- ters sirada "İ".lower() iki kod noktasi
    # uretir ve tablodaki anahtara artik uymaz.
    return metin.translate(_KATLAMA).lower()


#: YERLI KURUMLAR -- kararlari Turkiye'de dogrudan uygulanan kurumlar.
#:
#: Ayrim baglam metni icin sart. Fed faizi Turkiye'yi *aktarim kanallariyla*
#: etkiler; TCMB faizi Turkiye'de dogrudan uygulanir. Ikisine ayni metni
#: yazmak, TCMB kararini "gelismekte olan ulkelere referans olusturur" diye
#: anlatmak olurdu -- Turkiye'nin kendi merkez bankasi icin anlamsiz.
YERLI_KURUMLAR = frozenset({"TCMB", "SPK", "BDDK", "TUIK", "Hazine"})

#: Baslikta gectiginde haberi YERLI baglama sokan isaretler.
#:
#: Yayimlayan kurum ticari bir gazete olsa bile, haberin oznesi bir Turk
#: kurumuysa yerli cerceve dogrudur. Isaretler KATLANMIS yazilir.
#:
#: "turkiye" TEK BASINA YAZILMADI bilerek: "Goldman'in Turkiye tahmini"
#: gibi bir baslikta yabanci kurumun gorusu anlatiliyor ve yerli
#: cerceveye (yani "bizim faiz kararimiz") sokmak yanlis olurdu.
#: Buradakiler KARAR ALAN ya da VERI YAYIMLAYAN yurt ici kurumlar.
YERLI_ISARETLER = (
    " tcmb ", "tcmb'", "merkez bankasi", "para politikasi kurulu", " ppk ",
    " tuik ", "tuik'", "istatistik kurumu",
    " spk ", " bddk ", "hazine ve maliye", "hazine bakanl",
    "cumhurbaskani", "bakan simsek", "resmi gazete",
)

#: Rutin duyuru isaretleri -- bunlar yorumlanmaz.
#: Sirasi onemli degil, herhangi biri eslesirse rutin sayilir.
#: Turkce isaretler KATLANMIS yazilir ("haftalik", "cagr").
RUTIN_ISARETLER = (
    # Turkce
    "haftalik", "katilim cagr", "cagrisi", "takvimi", "atama",
    "gorevlendirme", "revizyon", "yontemsel degisiklik", "duzeltme",
    "sorgulama", "ekosistem",
    # Ingilizce
    "enforcement action", "civil money penalty", "consent order",
    "advisory committee", "committee meeting", "announces continuation",
    "appoints", "appointment", "names ", "personnel", "retirement",
    "requests comment", "seeks comment", "proposed rule", "comment period",
    "technical correction", "administrative", "agenda", "schedule of",
    "speech by", "remarks by", "testimony",
)

#: Etkili duyuru isaretleri -- bunlar yorumlanir. Rutin isaretlerden
#: SONRA bakilir; "requests comment on interest rate rule" rutindir.
#: Ayni sekilde "Haftalik Akim Faiz Istatistikleri" icinde "faiz" gecer
#: ama rutin bir veri yayimidir -- "haftalik" onu once yakalar.
ETKILI_ISARETLER = (
    # Turkce -- para ve fiyat
    "para politikasi kurulu", "faiz oranlarina iliskin", "politika faizi",
    "faiz karari", "faizi sabit", "faizde indirim", "zorunlu karsilik",
    "enflasyon", "fiyat gelismeleri", "tufe", "uretici fiyat",
    "odemeler dengesi", "finansal istikrar raporu", "beklenti anketi",
    "cari islemler", "cari acik",
    # Turkce -- ticari akistan gelen, gercekten etkili olaylar
    "asgari ucret", "emekli zam", "memur zam", "issizlik orani",
    "kira zam", "konut kredisi", "vergi duzenleme", "vergi indirim",
    "butce acig", "dis ticaret acig", "ihracat rekor", "gumruk tarife",
    "dolar endeksi", "kurda ", "ons altin", "altin rekor",
    "borsa rekor", "endeks rekor", "halka arz", "bilanco acikla",
    # Ingilizce
    "fomc statement", "monetary policy decision", "interest rate decision",
    "policy rate", "federal funds rate", "rate decision",
    "inflation", "cpi", "price index",
    "crude oil", "oil production", "oil imports", "natural gas",
    "energy outlook", "opec",
    "monetary policy statement", "governing council decision",
)


#: Kanal listesinin ustundeki baslik. Yerli ve yabanci icin AYRI olmali:
#: TCMB karari Turkiye'ye "gecmez", Turkiye'de alinir ve buradan yayilir.
BASLIK_YABANCI = "Türkiye'ye hangi kanallardan geçer"
BASLIK_YERLI = "Hangi kanallardan yansır"


@dataclass(frozen=True)
class Baglam:
    """Bir haberin okura anlatilacak baglami."""

    yorumlanir: bool
    neden_onemli: str = ""
    kanallar: tuple[str, ...] = ()
    kanal_basligi: str = BASLIK_YABANCI


#: Konu -> (neden onemli, Turkiye'ye gecis kanallari)
KONU_BAGLAMI: dict[str, tuple[str, tuple[str, ...]]] = {
    "Para politikası": (
        "ABD ve Avro Bölgesi politika faizi, küresel sermayenin fiyatını "
        "belirleyen ana değişkendir. Gelişmekte olan ülkeler için doğrudan "
        "bir referans oluşturur.",
        (
            "Dış borçlanma maliyeti: ABD faizleri yükseldiğinde gelişmekte "
            "olan ülkelerin tahvil ihraç maliyeti de yükselir.",
            "Sermaye akımları: faiz farkı daraldığında gelişmekte olan ülke "
            "varlıklarına yönelen akım görece azalır.",
            "Kur kanalı: sermaye hareketleri ve faiz farkı, kur üzerinde "
            "dolaylı baskı oluşturur.",
        ),
    ),
    "Enflasyon": (
        "Enflasyon verisi, merkez bankalarının politika patikasını belirleyen "
        "temel girdidir.",
        (
            "Politika beklentisi: enflasyonun seyri, faiz kararlarının "
            "zamanlaması hakkındaki piyasa beklentisini değiştirir.",
            "Reel getiri: enflasyon ile nominal faiz arasındaki fark, tahvil "
            "ve mevduatın reel getirisini belirler.",
        ),
    ),
    "Enerji": (
        "Türkiye net enerji ithalatçısıdır; ham petrol ve doğal gaz faturası "
        "cari işlemler dengesinin en büyük kalemlerinden biridir.",
        (
            "İthalat faturası: enerji fiyatındaki hareket, cari işlemler "
            "dengesine doğrudan yansıyan bir girdidir.",
            "Enflasyon geçişi: akaryakıt fiyatları üzerinden tüketici "
            "enflasyonuna geçiş kanalı vardır; hız ve büyüklük vergi "
            "yapısına ve kur seviyesine bağlıdır.",
            "Sektörel maliyet: yakıt maliyetinin gider içindeki payı yüksek "
            "sektörler (havayolu, karayolu lojistiği, petrokimya, enerji "
            "yoğun sanayi) bu kalemden daha erken etkilenir.",
        ),
    ),
    "Bankacılık": (
        "Bankacılık düzenlemeleri, kredi arzının maliyetini ve miktarını "
        "belirleyen kuralları değiştirir.",
        (
            "Kredi kanalı: sermaye ve likidite kuralları, bankaların kredi "
            "verme kapasitesini etkiler.",
            "Düzenleyici uyum: küresel standartlar (Basel gibi) zamanla "
            "yerel düzenlemelere de yansır.",
        ),
    ),
    "Piyasa düzenlemesi": (
        "Sermaye piyasası düzenlemeleri, işlem yapısını ve şirketlerin "
        "kamuyu aydınlatma yükümlülüklerini belirler.",
        (
            "Raporlama standardı: ABD'deki açıklama kuralları, çok uluslu "
            "şirketlerin raporlama pratiğini etkiler.",
        ),
    ),

    # --- Ticari haber akisiyla gelen konular ---
    # Bunlarin yerli/yabanci ayrimi yok: kur hareketi de kira zammi da
    # Turkiye'de olan seylerdir, "Turkiye'ye gecmez". Baslik farki
    # KONU_BASLIGI'nda tanimli.
    "Döviz": (
        "Kur, ithalat maliyetinin ve döviz cinsi borç servisinin ortak "
        "değişkenidir. Üretimin ara malı ithalatına bağımlılığı yüksek "
        "olduğu için kur hareketi maliyet tarafına hızlı geçer.",
        (
            "İthalat maliyeti: ara malı ve enerji ithalatı döviz cinsinden "
            "fiyatlanır; kur hareketi üretici maliyetine doğrudan yansır.",
            "Enflasyon geçişi: maliyet artışının tüketici fiyatına yansıma "
            "hızı, sektörün fiyatlama gücüne ve stok devir süresine bağlıdır.",
            "Şirket bilançosu: döviz açık pozisyonu taşıyan şirkette kur "
            "farkı gideri kâr tablosuna yazılır; ihracatçıda ters yönde "
            "çalışır. Yön, şirketin net döviz pozisyonuna bağlıdır.",
            "Dış borç servisi: döviz cinsi yükümlülüğün TL karşılığı değişir.",
        ),
    ),
    "Altın ve emtia": (
        "Altın hem tasarruf aracı hem rezerv varlığıdır; hanehalkı "
        "tasarrufunun önemli bir kısmı Türkiye'de bu araçta tutulur.",
        (
            "Tasarruf tercihi: altın getirisi ile TL mevduatın reel getirisi "
            "arasındaki fark, hanehalkı tasarruf kompozisyonunu etkiler.",
            "Cari denge: külçe altın ithalatı cari işlemler dengesinde ayrı "
            "ve büyük bir kalemdir.",
            "Girdi maliyeti: sanayi metalleri (bakır, çelik) imalatta "
            "doğrudan girdi maliyetidir.",
        ),
    ),
    "Kripto varlıklar": (
        "Kripto varlıklarda Türkiye yüksek işlem hacmine sahip ülkeler "
        "arasında; fiyat hareketi hanehalkı portföyüne ve aracılık "
        "gelirlerine yansır.",
        (
            "Portföy etkisi: fiyat hareketi doğrudan hanehalkı servetine "
            "yansır. Bu varlıklarda mevduat güvencesi yoktur.",
            "Aracılık geliri: işlem hacmi, platformların ve aracı kurumların "
            "komisyon gelirini belirler.",
            "Düzenleme çerçevesi: alanın kuralları gelişmekte; değişiklik "
            "erişimi ve vergilendirmeyi etkileyebilir.",
        ),
    ),
    "Borsa": (
        "Endeks seviyesi şirketlerin öz kaynak maliyetini ve halka arz "
        "iştahını belirler.",
        (
            "Öz kaynak maliyeti: değerleme seviyesi, şirketlerin sermaye "
            "artırımı ve halka arz yoluyla kaynak bulma maliyetini değiştirir.",
            "Tasarruf tabanı: bireysel emeklilik ve yatırım fonları "
            "üzerinden geniş bir tasarruf kitlesine yansır.",
            "Yabancı payı: yabancı yatırımcı payındaki değişim tek başına "
            "değil, kur ve faiz ile birlikte okunur.",
        ),
    ),
    "Dış ticaret": (
        "Dış ticaret dengesi cari işlemler hesabının en büyük bileşenidir "
        "ve dış finansman ihtiyacını belirler.",
        (
            "Cari denge: ihracat ile ithalat arasındaki fark doğrudan cari "
            "işlemler dengesine yazılır.",
            "Dış finansman: cari açık, dışarıdan kaynak bulma ihtiyacı "
            "demektir; bu kaynağın maliyeti küresel faiz koşullarına bağlıdır.",
            "Sektörel etki: ihracat ağırlıklı sektörler (otomotiv, tekstil, "
            "beyaz eşya) dış talepteki değişimi önce hisseder.",
        ),
    ),
    "İstihdam ve ücret": (
        "Ücret hem hanehalkı gelirinin hem işletme maliyetinin iki "
        "tarafıdır; asgari ücret ve aylık ayarlamaları geniş bir kitleyi "
        "aynı anda etkiler.",
        (
            "İç talep: ücret ve aylık ayarlamaları harcanabilir geliri "
            "değiştirir; perakende ve gıda talebine yansır.",
            "İşletme maliyeti: emek yoğun sektörlerde (tekstil, hizmet, "
            "lojistik) ücret gideri kâr marjının ana belirleyicisidir.",
            "Bütçe kalemi: kamu personeli ve emekli ödemeleri bütçe "
            "harcamalarının büyük bir bölümünü oluşturur.",
        ),
    ),
    "Konut ve kira": (
        "Konut hem hanehalkının en büyük varlık kalemi hem tüketici fiyat "
        "endeksinde ağırlığı yüksek bir harcama başlığıdır.",
        (
            "Enflasyon sepeti: kira, TÜFE'de ağırlığı yüksek kalemlerden "
            "biridir ve endekse gecikmeli yansır.",
            "Bağlantılı sektörler: konut talebi çimento, demir, beyaz eşya "
            "ve mobilyaya yayılır.",
            "Kredi kanalı: konut kredisi faizi talebi belirler; bu da "
            "politika faizi kararlarına doğrudan bağlıdır.",
        ),
    ),
    "Vergi ve kamu maliyesi": (
        "Vergi düzenlemeleri ve bütçe dengesi hem şirket kârlılığını hem "
        "devletin borçlanma ihtiyacını belirler.",
        (
            "Şirket kârlılığı: vergi oranı ve istisna değişiklikleri net "
            "kâra doğrudan yansır.",
            "Borçlanma ihtiyacı: bütçe açığı iç borçlanmayı artırır; bu da "
            "tahvil getirilerini ve banka bilançolarını etkiler.",
            "Tüketici fiyatı: dolaylı vergiler (ÖTV, KDV) nihai fiyata "
            "doğrudan geçer.",
        ),
    ),
    "Tarım ve gıda": (
        "Gıda, tüketici fiyat endeksinde en yüksek ağırlıklı gruplardan "
        "biridir; rekolte ve girdi maliyeti enflasyona hızlı geçer.",
        (
            "Enflasyon: gıda fiyatları manşet enflasyonun en oynak "
            "bileşenidir; bu yüzden çekirdek enflasyon ayrıca izlenir.",
            "Girdi maliyeti: gübre, yem ve akaryakıt fiyatı üretici "
            "maliyetini belirler; bunların çoğu ithal ve döviz cinsidir.",
            "Dış ticaret: hububat ve yağlı tohumda ithalat bağımlılığı, "
            "rekolte sonucunu cari dengeye bağlar.",
        ),
    ),
    "Turizm": (
        "Turizm geliri en büyük net döviz kazandırıcı kalemlerden biridir "
        "ve cari açığı doğrudan azaltır.",
        (
            "Cari denge: turizm geliri hizmet ihracatı olarak cari işlemler "
            "hesabına artı yazılır.",
            "Sektörel istihdam: konaklama, yeme-içme ve havayolu mevsimsel "
            "istihdamın büyük bölümünü taşır.",
            "Bölgesel yayılım: gelir kıyı illerinde yoğunlaşır; perakende ve "
            "gayrimenkul talebine yansır.",
        ),
    ),
    "Şirket haberleri": (
        "Şirket bazlı gelişmeler sektörün geneli için erken gösterge "
        "olabilir.",
        (
            "Sektör okuması: bir şirketin marj ve talep verisi, aynı "
            "sektördeki diğer şirketler için gösterge niteliği taşır.",
            "Tedarik zinciri: büyük bir yatırım ya da kapanış kararı "
            "tedarikçi ve müşteri şirketlere yayılır.",
            "Değerleme: birleşme ve satın alma çarpanları, benzer şirketler "
            "için referans oluşturur.",
        ),
    ),
    # JEOPOLITIK.
    #
    # Kanallar YON SOYLEMEZ. "Gerilim artarsa petrol yukselir" yaygin ama
    # yanlis bir genelleme: 2020 Suleymani suikastinde petrol iki gunde
    # yukselip geri verdi, 2023'te bolgesel catisma sirasinda Brent
    # geriledi. Fiyata gecen sey olayin kendisi degil, ARZ RISKININ
    # degismesi -- asagidaki maddeler o mekanizmayi anlatiyor, sonucu
    # degil.
    "Jeopolitik": (
        "Jeopolitik gelişmeler piyasaya doğrudan değil, arz riski ve risk "
        "iştahı üzerinden geçer. Türkiye için ana kanal enerji faturası ve "
        "risk primidir.",
        (
            "Enerji arzı: üretim ya da sevkiyat güzergâhı tehdit "
            "altındaysa petrol ve doğal gaz fiyatına risk primi eklenir. "
            "Türkiye net enerji ithalatçısı olduğu için bu, cari işlemler "
            "dengesine doğrudan yazılır.",
            "Risk iştahı: belirsizlik arttığında gelişmekte olan ülke "
            "varlıklarından çıkış görülebilir; ülke risk primi ve "
            "borçlanma maliyeti yeniden fiyatlanır.",
            "Ticaret akışı: gümrük vergisi, yaptırım ve ambargo kararları "
            "ihracat pazarlarının bileşimini değiştirir; etki sektörün "
            "o pazara bağımlılığı kadardır.",
            "Güvenli liman talebi: altın ve dolar talebi değişebilir; "
            "yönü ve büyüklüğü olayın ne kadarının önceden fiyatlandığına "
            "bağlıdır.",
        ),
    ),
}

#: "Turkiye'ye gecer" cercevesinin yanlis oldugu konular. Kira zammi ya da
#: BIST endeksi Turkiye'ye gecmez, Turkiye'de olur.
KONU_BASLIGI = {k: BASLIK_YERLI for k in (
    "Döviz", "Altın ve emtia", "Kripto varlıklar", "Borsa", "Dış ticaret",
    "İstihdam ve ücret", "Konut ve kira", "Vergi ve kamu maliyesi",
    "Tarım ve gıda", "Turizm", "Şirket haberleri",
)}


#: YERLI kurum kararlari icin baglam. Yukaridaki tablo yabanci merkez
#: bankalari icin yazildi ve aktarim kanallarini anlatiyor; TCMB karari ise
#: Turkiye'de DOGRUDAN uygulanir, aktarilmaz.
#:
#: Burada olmayan konu icin KONU_BAGLAMI'na dusulur -- enerji baglami zaten
#: Turkiye merkezli yazilmis, ikinci kez yazmaya gerek yok.
YERLI_BAGLAMI: dict[str, tuple[str, tuple[str, ...]]] = {
    "Para politikası": (
        "TCMB politika faizi, yurt içi fonlama maliyetinin çıpasıdır. "
        "Ticari kredi faizi, mevduat getirisi ve tahvil getiri eğrisi bu "
        "oranın etrafında yeniden fiyatlanır.",
        (
            "Kredi maliyeti: bankaların Merkez Bankası'ndan fonlanma "
            "maliyeti değiştiğinde ticari ve bireysel kredi faizleri "
            "buradan fiyatlanır.",
            "Şirket finansman gideri: değişken faizle borçlanan ve net borç "
            "pozisyonu yüksek şirketlerde finansman gideri kalemi doğrudan "
            "etkilenir; bu kalem kâr marjına gelir tablosu üzerinden "
            "yansır.",
            "Mevduat ve tahvil getirisi: TL mevduat ile devlet iç borçlanma "
            "senedi getirileri politika faizine göre yeniden konumlanır. "
            "Reel getiri, enflasyon beklentisiyle birlikte değerlendirilir.",
            "Faiz farkı: yurt içi ve yurt dışı faiz arasındaki fark, TL "
            "cinsi varlıklara yönelen sermaye akımının belirleyicilerinden "
            "biridir.",
        ),
    ),
    "Enflasyon": (
        "TÜFE yalnızca bir fiyat ölçüsü değildir; politika faizi "
        "kararlarının, kira ve ücret yenilemelerinin ve enflasyon "
        "muhasebesinin ortak girdisidir.",
        (
            "Politika patikası: enflasyonun seyri, Para Politikası Kurulu "
            "kararlarına ilişkin piyasa beklentisini değiştirir.",
            "Reel getiri: nominal faiz ile enflasyon arasındaki fark, "
            "mevduatın ve tahvilin reel getirisini belirler.",
            "Enflasyon muhasebesi: TÜFE, TMS 29 kapsamında finansal "
            "tabloların düzeltilmesinde kullanılan endekstir. Düzeltilmiş "
            "tablolarda raporlanan büyüme zaten reeldir; bu rakamı ayrıca "
            "enflasyondan arındırmak çift sayım olur.",
            "Maliyet yenilemesi: kira, ücret ve uzun vadeli sözleşme "
            "yenilemeleri bu endekse bağlıdır.",
        ),
    ),
    "Bankacılık": (
        "Zorunlu karşılık, likidite ve teminat düzenlemeleri kredi arzının "
        "miktarını ve maliyetini doğrudan belirler.",
        (
            "Kredi arzı: zorunlu karşılık oranları, bankaların kredi olarak "
            "kullandırabileceği kaynağın büyüklüğünü değiştirir.",
            "Fonlama kompozisyonu: TL ve döviz mevduat arasındaki maliyet "
            "farkı, bankaların bilanço yapısını etkiler.",
            "Reel sektör: kredi kanalının daralması, işletme sermayesini "
            "kısa vadeli borçla çeviren şirketlerde önce hissedilir.",
        ),
    ),
    "Piyasa düzenlemesi": (
        "Sermaye piyasası düzenlemeleri işlem yapısını ve şirketlerin "
        "kamuyu aydınlatma yükümlülüklerini belirler.",
        (
            "Kamuyu aydınlatma: bildirim yükümlülüğündeki bir değişiklik, "
            "yatırımcının şirket verisine erişim hızını ve kapsamını "
            "değiştirir.",
            "İşlem yapısı: piyasa kuralları, fiyat oluşumunun ve likiditenin "
            "koşullarını belirler.",
        ),
    ),
}


#: MAKRO KONULAR -- aktarim kanali anlatmanin okura bir sey kattigi konular.
#: Disarida kalanlar ("Şirket haberleri", "Düzenleme"): tek bir sirketin ya
#: da tek bir idari islemin haberi. Orada "piyasalarda neyi etkiler"
#: sorusunun durust cevabi cogu zaman "kayda deger bir sey etkilemez".
MAKRO_KONULAR = frozenset({
    "Para politikası", "Enflasyon", "Döviz", "Altın ve emtia",
    "Kripto varlıklar", "Borsa", "Dış ticaret", "İstihdam ve ücret",
    "Konut ve kira", "Vergi ve kamu maliyesi", "Bankacılık", "Enerji",
    "Tarım ve gıda", "Turizm", "Jeopolitik",
})

#: OLAY ISARETLERI -- basligin bir VERI ya da KARAR duyurdugunu gosterir.
#:
#: Ticari akista kalip aramak calismiyor. Turkce'de kelimeler araya
#: giriyor: "emekli zam" deseni "emekliLERININ temmuz ayi ZAM orani"
#: icinde eslesmez. Olculdu, boyle kacanlar:
#:
#:   "SSK ve Bag-Kur emeklilerinin Temmuz ayi zam orani belli oldu"
#:   "Temmuz ayi dis ticaret rakamlari aciklandi"
#:   "2027 memur ve emekli maasi Ocak zammi sekilleniyor"
#:
#: Bu yuzden ticari ogede iki ayri sart aranir: konu MAKRO_KONULAR'da
#: olacak VE baslikta bir olay isareti bulunacak. "Shell portfoyunu
#: satiyor" konu olarak enerji ama olay isareti tasimiyor -- rutin kalir.
#:
#: DIKKAT: " zam " bosluklu yazilir, yoksa "ZAMan" icinde eslesir.
#: " veri " de oyle -- yoksa "VERIldi" ve "VERImi" eslesir.
OLAY_ISARETLERI = (
    "acikla", "belli oldu", "rakamlar", "rakami", " veri ", "verisi",
    "verileri", "karar", "orani", "oranlari", "rekor", "artis", "dusus",
    "yukseldi", "geriledi", "yukselis", "gerileme", " zam ", "zammi",
    "zamlar", "indirim", "beklenti", "tahmin", "hedefi", "acigi",
    "fazla verdi", "raporu", "anketi", "istatistik", "yuzde",

    # OLAY OLARAK SAYILAN FIILLER -- eksikligi olculdu.
    #
    # 216 haberin 107'si bu kapida duruyordu ve arasinda gercek olaylar
    # vardi: "Bakan Simsek: dezenflasyon sureci kararlilikla surdurulecek"
    # bir politika beyanidir, "Israil ve Hizbullah ateskes anlasmasi
    # imzalandi" petrol fiyatini hareket ettiren bir olaydir. Ikisi de
    # "acikla/rakam/oran" kalibina girmedigi icin eleniyordu.
    #
    # Liste yine de KAPALI tutuluyor: her fiili eklemek gurultu kapisini
    # tamamen acardi. Buraya yalnizca "bir sey OLDU ya da SOYLENDI"
    # anlamini tasiyan fiiller giriyor.

    # resmi beyan
    " dedi", "belirtti", "vurgula", "uyardi", "uyarisi", "cagrisinda",
    "degerlendirme", "aciklamasi", "mesaji", "sinyali", "yanit",
    # karar ve yururluk
    "imzalandi", "onaylandi", "yururluge", "kabul edildi", "getirdi",
    "kaldirdi", "yasakla", "serbest birak", "iptal etti", "erteledi",
    "baslatti", "sonlandirdi", "uzatildi",
    # jeopolitik olay
    "anlasma", "uzlasi", "ateskes", "saldiri", "yaptirim", "gerilim",
    "muzakere", "tatbikat", "misilleme", "tehdit",
    # Ingilizce karsiliklari
    "signed", "approved", "agreement", "ceasefire", "sanction",
    "warned", "said ", "announces", "imposes", "lifts",
)


def _icerir(metin: str, isaretler) -> bool:
    # Bastaki ve sondaki bosluk, " zam " gibi bosluklu isaretlerin
    # basligin basinda ve sonunda da eslesmesini saglar.
    #
    # NOKTALAMA BOSLUGA CEVRILIYOR. Eksikligi olculdu:
    #
    #   "TCMB: Enflasyonun ana egilimi Temmuz'da geriledi"
    #   -> " tcmb: ... " ve " tcmb " isareti ESLESMEDI
    #
    # Haber yerli baglama girmesi gerekirken yabanci cerceveyle
    # ("ABD ve Avro Bolgesi politika faizi...") sunuluyordu. Iki nokta,
    # virgul, tirnak ve parantez kelimeyi isaretten ayirmiyordu.
    # Tire KORUNUYOR: "bag-kur" gibi isaretler ona dayaniyor.
    k = " " + re.sub(r"[^a-z0-9&/%-]+", " ", _katla(metin)).strip() + " "
    return any(i in k for i in isaretler)


#: BIRIM TASIYAN SAYI -- kelime listesinden bagimsiz olay isareti.
#:
#: Kelime listesi Turkce'nin ek yapisinda surekli kaciriyordu; 216
#: haberin 97'si "olay isareti yok" diye eleniyordu ve arasinda su
#: basliklar vardi:
#:
#:   "Savunma ve havacilik sanayisinden temmuzda 1,12 milyar dolarlik..."
#:   "TARSIM'den ureticiye 6,6 milyar liralik hasar destegi"
#:   "Borsa yeni haftaya 13.544,32 puandan basladi"
#:
#: Ucu de nicelik bildiriyor. Bir baslik OLCULMUS bir buyukluk tasiyorsa
#: bir olay anlatiyordur -- bu, fiil listesinden daha guvenilir bir
#: olcut.
#:
#: BIRIM ZORUNLU. Yalin sayi yetmiyor, cunku "kontenjan 500'e cikti" ya
#: da "desteklenen bolum sayisi 38" olay degil. Olculdu.
#:
#: BUYUKLUK DE ZORUNLU: "milyar" ve ustu. Ilk yazimda "milyon" da
#: sayiliyordu ve test bunu yakaladi -- "Flotek, Porto Riko'da 400 milyon
#: dolarlik sozlesme imzaladi" yayima giriyordu. Tek bir sirketin
#: sozlesmesi makro haber degil; bu sitenin bilincli kapsam karari.
#: Endeks puani ayri tutuluyor ("Borsa 13.544,32 puandan basladi"):
#: seviye bildirimi toplulastirilmis bir olcumdur.
_SAYISAL = re.compile(
    r"\d[\d.,]*\s*(?:milyar|trilyon)\s*"
    r"(?:dolar|lira|euro|avro|sterlin|tl\b|metrekup|kwh|mwh)"
    r"|\d[\d.,]*\s*puan"
)

#: Tek sirketin islemi -- buyuklugu ne olursa olsun makro haber degil.
_SIRKET_ISLEMI = (
    "sozlesme", "satin al", "ihale kazan", "sermayesini", "sermaye artir",
    "hisseye cevir", "portfoyunu", "halka arz basvuru", "pay devri",
    "bedelli sermaye", "birlesme anlasmasi",
)


def _sayisal_olay(baslik: str) -> bool:
    if _icerir(baslik, _SIRKET_ISLEMI):
        return False
    return _SAYISAL.search(_katla(baslik)) is not None


#: "... Actual <sayi> ..." -- veri aciklamasi kalibi.
#: Basligin kendisi olay: rakam, beklenti ve onceki deger icinde.
_VERI_KALIBI = re.compile(r"\bactual\s+-?[\d.,]", re.I)


def _veri_aciklamasi(baslik: str) -> bool:
    return _VERI_KALIBI.search(baslik) is not None


def siniflandir(baslik: str, konu: str, kurum: str = "",
                ticari: bool = False) -> Baglam:
    """Haberin yorumlanip yorumlanmayacagina karar verir.

    Once RUTIN bakilir. "requests comment on interest rate rule" hem
    "requests comment" hem "interest rate" iceriyor; bu bir politika karari
    degil, bir idari sürectir. Rutin once bakilmazsa yanlis siniflanir.

    Sonra kaynak turune gore ayrilir:
      resmi  -- ETKILI_ISARETLER. Duyuru basliklari kalipli oldugu icin
                kalip aramak calisiyor.
      ticari -- MAKRO_KONULAR + OLAY_ISARETLERI. Gazete basligi kalipli
                degil; kalip aramak Turkce'nin ek yapisinda kaciriyor.

    `kurum` YERLI_KURUMLAR icindeyse yerli baglam metni kullanilir.
    """
    if _icerir(baslik, RUTIN_ISARETLER):
        return Baglam(yorumlanir=False)

    if ticari:
        if konu not in MAKRO_KONULAR:
            return Baglam(yorumlanir=False)
        # Jeopolitik konunun KENDI isaretleri zaten olay bildiriyor
        # ("ateskes", "yaptirim", "saldiri", "anlasma"). Ikinci bir olay
        # kapisi koymak ayni sarti iki kez aramak olurdu.
        #
        # VERI ACIKLAMASI KALIBI da ayni sekilde: "Actual 0.7% (Forecast
        # 1%, Previous 1.6%)" basligi zaten bir olayin kendisidir --
        # rakam, beklenti ve onceki deger basligin icinde. Fiil aramak
        # gereksiz, ustelik bu basliklarda fiil hic yok.
        if konu != "Jeopolitik" and not (
                _icerir(baslik, OLAY_ISARETLERI)
                or _sayisal_olay(baslik)
                or _veri_aciklamasi(baslik)):
            return Baglam(yorumlanir=False)
    elif not _icerir(baslik, ETKILI_ISARETLER):
        return Baglam(yorumlanir=False)

    # YERLI/YABANCI AYRIMI KURUMA DEGIL, BASLIGA DA BAKIYOR.
    #
    # Onceden yalnizca yayimlayan kuruma bakiliyordu ve olculen sonuc
    # suydu:
    #
    #   "TCMB: Enflasyonun ana egilimi Temmuz'da geriledi"  (kaynak:
    #   Ekonomim)  ->  "ABD ve Avro Bolgesi politika faizi, kuresel
    #   sermayenin fiyatini belirleyen ana degiskendir."
    #
    # Haber TCMB'nin Turkiye enflasyonu aciklamasi; ticari bir gazete
    # aktardigi icin yabanci cerceveye dusuyordu. Turk kurumu haberin
    # OZNESI oldugunda, aktaran kim olursa olsun yerli baglam dogru.
    yerli = kurum in YERLI_KURUMLAR or _icerir(baslik, YERLI_ISARETLER)
    veri = YERLI_BAGLAMI.get(konu) if yerli else None
    if veri is None:
        veri = KONU_BAGLAMI.get(konu)
    if veri is None:
        return Baglam(yorumlanir=False)

    neden, kanallar = veri
    return Baglam(
        yorumlanir=True,
        neden_onemli=neden,
        kanallar=kanallar,
        kanal_basligi=(BASLIK_YERLI if yerli
                       else KONU_BASLIGI.get(konu, BASLIK_YABANCI)),
    )


#: Yorumlanan haberlerin sonuna eklenen ortak not
SINIR_NOTU = (
    "Yukarıdaki maddeler yapısal aktarım kanallarıdır, öngörü değildir. "
    "Etkinin ne zaman ve ne ölçüde görüleceği kur seviyesi, vergi "
    "düzenlemeleri ve sözleşme yapılarına bağlı olarak değişir; bu sayfada "
    "bir büyüklük tahmini yapılmamaktadır."
)
