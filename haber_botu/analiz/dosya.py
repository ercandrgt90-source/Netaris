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
    ("TP.APIFON4", "Politika faizi", "%", 2),
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

def kur(konu: str, bolge: str, haber_tarihi: str = "") -> Dosya:
    """Haberin arastirma dosyasini kurar. Veri yoksa bos Dosya doner."""
    d = Dosya(
        duyarlilik=DUYARLILIK.get(konu, ()),
        izlenecekler=IZLENECEKLER.get(konu, ()),
        senaryolar=SENARYOLAR.get(konu, ()),
    )
    if not DEPO.exists():
        return d

    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            if bolge == "TR":
                for kod, ad, birim, _bas in TURKIYE_PANEL:
                    g = _gosterge(b, kod, ad, birim)
                    if g:
                        d.turkiye.append(g)

                faiz = _seri(b, REEL_FAIZ[0], 1)
                enf = _seri(b, REEL_FAIZ[1], 1)
                if faiz and enf:
                    d.reel_faiz = faiz[0][1] - enf[0][1]

            # Enflasyon seyri ve ayrisma sayimi
            manset = _seri(b, "TP.TUKFIY2025.GENEL", 13)
            cekirdek = _seri(b, "TP.FE25.OKTG04", 13)
            if len(manset) >= 6:
                d.seyir = manset
                d.seyir_ad = "TÜFE (yıllık, %)"
                alt, ust, n = _bant(manset, 6)
                d.bulgular.append(
                    f"Enflasyon {n} aydır %{alt:.1f}–%{ust:.1f} bandında"
                    .replace(".", ","))
            if len(manset) >= 3 and len(cekirdek) >= 3:
                ayrisma, toplam = _ayrisma_say(manset, cekirdek)
                if toplam:
                    # "Son 12 ayin 2'inde" yazmiyoruz: Turkce'de sayiya
                    # gelen ek okunusa gore degisiyor (2'sinde, 3'unde,
                    # 6'sinda) ve dogru uretmek icin sayiyi yaziyla
                    # cozmek gerekir. Cumleyi ek gerektirmeyen bicimde
                    # kurmak hem dogru hem daha akici.
                    d.bulgular.append(
                        f"Son {toplam} ayda manşet {ayrisma} kez gerilerken "
                        f"çekirdek yükseldi")
                fark = manset[-1][1] - cekirdek[-1][1]
                d.bulgular.append(
                    f"Manşet ile çekirdek arasındaki fark {abs(fark):.2f} puan"
                    .replace(".", ","))

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
