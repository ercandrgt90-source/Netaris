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

#: Rutin duyuru isaretleri -- bunlar yorumlanmaz.
#: Sirasi onemli degil, herhangi biri eslesirse rutin sayilir.
RUTIN_ISARETLER = (
    "enforcement action", "civil money penalty", "consent order",
    "advisory committee", "committee meeting", "announces continuation",
    "appoints", "appointment", "names ", "personnel", "retirement",
    "requests comment", "seeks comment", "proposed rule", "comment period",
    "technical correction", "administrative", "agenda", "schedule of",
    "speech by", "remarks by", "testimony",
)

#: Etkili duyuru isaretleri -- bunlar yorumlanir. Rutin isaretlerden
#: SONRA bakilir; "requests comment on interest rate rule" rutindir.
ETKILI_ISARETLER = (
    "fomc statement", "monetary policy decision", "interest rate decision",
    "policy rate", "federal funds rate", "rate decision",
    "inflation", "cpi", "price index",
    "crude oil", "oil production", "oil imports", "natural gas",
    "energy outlook", "opec",
    "monetary policy statement", "governing council decision",
)


@dataclass(frozen=True)
class Baglam:
    """Bir haberin okura anlatilacak baglami."""

    yorumlanir: bool
    neden_onemli: str = ""
    kanallar: tuple[str, ...] = ()


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


def _icerir(metin: str, isaretler) -> bool:
    k = metin.lower()
    return any(i in k for i in isaretler)


def siniflandir(baslik: str, konu: str) -> Baglam:
    """Haberin yorumlanip yorumlanmayacagina karar verir.

    Once RUTIN bakilir. "requests comment on interest rate rule" hem
    "requests comment" hem "interest rate" iceriyor; bu bir politika karari
    degil, bir idari sürectir. Rutin once bakilmazsa yanlis siniflanir.
    """
    if _icerir(baslik, RUTIN_ISARETLER):
        return Baglam(yorumlanir=False)

    if not _icerir(baslik, ETKILI_ISARETLER):
        return Baglam(yorumlanir=False)

    veri = KONU_BAGLAMI.get(konu)
    if veri is None:
        return Baglam(yorumlanir=False)

    neden, kanallar = veri
    return Baglam(yorumlanir=True, neden_onemli=neden, kanallar=kanallar)


#: Yorumlanan haberlerin sonuna eklenen ortak not
SINIR_NOTU = (
    "Yukarıdaki maddeler yapısal aktarım kanallarıdır, öngörü değildir. "
    "Etkinin ne zaman ve ne ölçüde görüleceği kur seviyesi, vergi "
    "düzenlemeleri ve sözleşme yapılarına bağlı olarak değişir; bu sayfada "
    "bir büyüklük tahmini yapılmamaktadır."
)
