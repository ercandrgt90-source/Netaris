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
    # Turkce
    "para politikasi kurulu", "faiz oranlarina iliskin", "politika faizi",
    "faiz karari", "zorunlu karsilik", "enflasyon", "fiyat gelismeleri",
    "tufe", "odemeler dengesi", "finansal istikrar raporu",
    "beklenti anketi", "cari islemler",
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
}


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


def _icerir(metin: str, isaretler) -> bool:
    k = _katla(metin)
    return any(i in k for i in isaretler)


def siniflandir(baslik: str, konu: str, kurum: str = "") -> Baglam:
    """Haberin yorumlanip yorumlanmayacagina karar verir.

    Once RUTIN bakilir. "requests comment on interest rate rule" hem
    "requests comment" hem "interest rate" iceriyor; bu bir politika karari
    degil, bir idari sürectir. Rutin once bakilmazsa yanlis siniflanir.

    `kurum` YERLI_KURUMLAR icindeyse yerli baglam metni kullanilir.
    """
    if _icerir(baslik, RUTIN_ISARETLER):
        return Baglam(yorumlanir=False)

    if not _icerir(baslik, ETKILI_ISARETLER):
        return Baglam(yorumlanir=False)

    yerli = kurum in YERLI_KURUMLAR
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
        kanal_basligi=BASLIK_YERLI if yerli else BASLIK_YABANCI,
    )


#: Yorumlanan haberlerin sonuna eklenen ortak not
SINIR_NOTU = (
    "Yukarıdaki maddeler yapısal aktarım kanallarıdır, öngörü değildir. "
    "Etkinin ne zaman ve ne ölçüde görüleceği kur seviyesi, vergi "
    "düzenlemeleri ve sözleşme yapılarına bağlı olarak değişir; bu sayfada "
    "bir büyüklük tahmini yapılmamaktadır."
)
