"""Beklenti motoru -- veri aciklanmadan ONCE ne yazabiliriz.

NEDEN VAR
---------
Yapay zeka yorum uretemedigi durumda sayfada su cikiyordu:

    "Verilen metinde sayisal bir olcum bulunmadigi icin, olculen bir
     degeri secip yorumlamak mumkun degildir."

Bu bir icerik degil, bir arizanin tutanagi. Oysa veri aciklanmadan
once bile soylenecek gercek seyler var: son deger ne, esik nerede,
hangi mekanizma calisir, gecmiste ne olmus.

YON IDDIASI KONUSUNDA CIZGI
---------------------------
"Beklenti uzeri gelirse altin baskilanir" turu cumleler YAZILMIYOR.
Bu sitenin varlik grafinde zaten yazili olan kurala aykiri: bag
"etkiler" der, "dusurur" demez. Gerekce olculmus bir sey -- 2022'de
Fed faizi de altin da yukseldi; "faiz artarsa altin duser" genellemesi
o yil boyunca yanlisti.

Bu yuzden iki dal SU AYRIMLA yaziliyor:

  MEKANIZMA   Yonlu ama tanim/politika duzeyinde: "enflasyon
              beklenenden yuksek gelirse faiz indirimi beklentisi
              zayiflar." Bu bir piyasa tahmini degil, merkez bankasi
              tepki fonksiyonunun tarifi.

  FIYAT       Yalnizca OLCULMUSSE ve olcum olarak yaziliyor: "son 5
              benzer aciklamada Brent ortalama %1,8 hareket etti."
              Olcum yoksa bu satir HIC BASILMIYOR.

ESIK NEDIR, NEDEN ONCEKI DEGER
------------------------------
Ekranda "beklenti" olarak bir konsensus rakami gostermek isterdik ama
olculdu: ucretsiz kaynaklarimizin hicbiri ONCEDEN konsensus vermiyor
(bkz. yayin_takvimi.py). Bu yuzden esik SON ACIKLANAN DEGER ve ekranda
oyle yaziyor. Istisna: TCMB Piyasa Katilimcilari Anketi gercek bir
beklenti olcumu ve Turkiye enflasyonunda esik olarak o kullaniliyor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Seri kodu -> beklentiyi TASIYAN seri kodu.
#:
#: Gercek bir konsensus olcumumuz olan tek yer burasi: TCMB'nin
#: Piyasa Katilimcilari Anketi. Digerlerinde esik onceki deger.
BEKLENTI_SERISI = {
    "TP.TUKFIY2025.GENEL": "TP.ENFBEK.PKA12ENF",
}

#: Konu -> (yukari dal, asagi dal).
#:
#: Cumleler YALNIZCA mekanizma anlatiyor. Hicbiri bir varligin
#: fiyatinin ne yapacagini soylemiyor; soyleseydi olculmemis bir
#: tahmini olcum gibi sunmus olurduk.
MEKANIZMA = {
    "Enflasyon": (
        "Faiz indirimi beklentisi zayıflar; para politikasında sıkı "
        "duruşun süresi uzar. Reel getiri hesabı ve tahvil getiri "
        "eğrisi yeniden fiyatlanır.",
        "Faiz indirimi için alan genişler; sıkı duruşun daha erken "
        "gevşeyebileceği beklentisi güçlenir. Reel getiri hesabı ve "
        "tahvil getiri eğrisi yeniden fiyatlanır.",
    ),
    "İstihdam ve ücret": (
        "İş gücü piyasası beklenenden güçlü demektir; ücret baskısı ve "
        "hizmet enflasyonu kanalı canlı kalır, faiz indirimi için "
        "aciliyet azalır.",
        "İş gücü piyasasında soğuma işareti sayılır; ücret baskısı "
        "gevşer ve para politikasının gevşemesi için gerekçe güçlenir.",
    ),
    "Para politikası": (
        "Politika faizinin daha uzun süre yüksek kalacağı fiyatlanır; "
        "bankaların fonlama maliyeti ve kredi faizleri bu orandan "
        "türediği için ikisi de yukarı ayarlanır.",
        "Fonlama maliyetinin gerileyeceği fiyatlanır; kredi faizleri ve "
        "mevduat getirisi aynı yönde ayarlanır.",
    ),
    "Dış ticaret": (
        "Cari işlemler dengesine yazılan açık büyür; dış finansman "
        "ihtiyacı ve o ihtiyacın küresel faiz koşullarına bağımlılığı "
        "artar.",
        "Cari işlemler dengesine yazılan açık daralır; dış finansman "
        "ihtiyacı azalır.",
    ),
    "Büyüme": (
        "Talep beklenenden güçlü demektir; kapasite kullanımı ve fiyat "
        "baskısı kanalları canlanır.",
        "Talepte yavaşlama işareti sayılır; kapasite kullanımı ve fiyat "
        "baskısı gevşer.",
    ),
    "Enerji": (
        "Enerji faturası büyür. Türkiye net enerji ithalatçısı olduğu "
        "için bu doğrudan cari işlemler dengesine ve maliyet "
        "enflasyonuna yazılır.",
        "Enerji faturası küçülür; cari işlemler dengesi ve maliyet "
        "enflasyonu aynı kanaldan rahatlar.",
    ),
}

#: Konu icin mekanizma tanimli degilse iki dal da BASILMIYOR.
#: Uydurma bir mekanizma cumlesi, bos birakmaktan kotudur.

#: YUKSEK OKUMA, KONUNUN GENEL YONUNUN TERSI OLAN SERILER.
#:
#: Mekanizma tablosu konu bazli ve "yuksek gelirse" dalini konunun
#: genel mantigina gore yaziyor. Bazi serilerde bu ters calisiyor ve
#: olculdu -- ilk surumde ekranda sunlar cikti:
#:
#:   "İşsizlik oranı %7,40 üzerinde gelirse: iş gücü piyasası
#:    beklenenden GÜÇLÜ demektir"          <- yanlis, tam tersi
#:
#:   "Cari denge -1.459 mn $ üzerinde gelirse: açık BÜYÜR"
#:                                          <- yanlis, aciк KUCULUR
#:
#: Isaretli serilerde iki dal yer degistiriyor. Bu bir uslup tercihi
#: degil, olcunun isaretiyle ilgili bir olgu: issizlik oraninda yuksek
#: sayi kotu haberdir, cari dengede (negatif duzey) yuksek sayi iyi.
TERS_SERILER = frozenset({
    "UNRATE",                 # ABD issizlik orani
    "TP.YISGUCU2.G8",         # Turkiye issizlik orani
    "ICSA",                   # ABD haftalik issizlik basvurulari
    "TP.HARICCARIACIK.K1",    # Cari islemler dengesi (negatif duzey)
})


@dataclass(frozen=True)
class Dal:
    yon: str            # "ustunde" | "altinda"
    baslik: str
    mekanizma: str
    #: Olculmus fiyat tepkisi. Olcum yoksa BOS ve satir basilmiyor.
    olcum: str = ""


@dataclass(frozen=True)
class Beklenti:
    kod: str
    ad: str
    #: Son aciklanan deger, bicimlenmis ("45,8 bin kişi")
    son_deger: str = ""
    son_tarih: str = ""
    #: Esigin ne oldugu ACIKCA yaziliyor: konsensus mu, onceki deger mi.
    esik_deger: str = ""
    esik_kaynak: str = ""     # "beklenti" | "onceki"
    dallar: tuple[Dal, ...] = field(default_factory=tuple)

    @property
    def dolu(self) -> bool:
        """Basmaya deger mi.

        Son deger YOKSA basmiyoruz: "su olursa su olur" cumleleri, neyin
        uzerinde/altinda oldugunu soylemeden havada kalir.
        """
        return bool(self.son_deger and self.dallar)


def _vir(x: float, basamak: int = 2) -> str:
    """Turkce sayi bicimi: binlik nokta, ondalik virgul."""
    s = f"{x:,.{basamak}f}"
    return s.replace(",", " ").replace(".", ",").replace(" ", ".")


def bicimle(deger: float, birim: str) -> str:
    if birim == "%":
        return f"%{_vir(deger)}"
    if birim:
        return f"{_vir(deger)} {birim}"
    return _vir(deger)


def _tepki_ozeti(tepkiler: list[tuple[str, float]], en_az: int = 3) -> str:
    """Olculmus fiyat tepkilerinin ozeti. Az gozlem varsa BOS.

    `en_az` altinda ortalama yaziimiyor: uc gozlemin ortalamasi bir
    egilim degildir ve oyle sunmak, olcumun tasimadigi bir kesinlik
    iddia etmek olurdu.
    """
    if len(tepkiler) < en_az:
        return ""
    # Varliga gore grupla
    grup: dict[str, list[float]] = {}
    for varlik, d in tepkiler:
        grup.setdefault(varlik, []).append(d)
    parca = []
    for varlik, degerler in sorted(grup.items()):
        if len(degerler) < en_az:
            continue
        ort = sum(abs(d) for d in degerler) / len(degerler)
        yukari = sum(1 for d in degerler if d > 0)
        parca.append(f"{varlik} ortalama %{_vir(ort)} hareket etti "
                     f"({len(degerler)} gözlemin {yukari}'inde yukarı)")
    if not parca:
        return ""
    return "Geçmiş benzer açıklamalarda " + "; ".join(parca) + "."


def kur(kod: str, ad: str, konu: str, son_deger: float | None,
        son_birim: str, son_tarih: str,
        esik_deger: float | None = None,
        esik_birim: str = "",
        tepkiler: list[tuple[str, float]] | None = None) -> Beklenti:
    """Bir veri aciklamasi icin beklenti kutusu.

    `esik_deger` verilmezse esik SON ACIKLANAN DEGER olur ve ekranda
    "önceki" diye etiketlenir.
    """
    if son_deger is None:
        return Beklenti(kod=kod, ad=ad)

    son = bicimle(son_deger, son_birim)
    if esik_deger is not None:
        esik, kaynak = bicimle(esik_deger, esik_birim or son_birim), "beklenti"
    else:
        esik, kaynak = son, "onceki"

    mek = MEKANIZMA.get(konu)
    if not mek:
        # Mekanizma tanimli degilse dal URETILMIYOR. Genel gecer bir
        # cumle ("piyasalar hareketlenebilir") hicbir sey soylemez ve
        # sayfayi doldurmaktan baska ise yaramaz.
        return Beklenti(kod=kod, ad=ad, son_deger=son, son_tarih=son_tarih,
                        esik_deger=esik, esik_kaynak=kaynak)

    olcum = _tepki_ozeti(tepkiler or [])

    # Ters serilerde YUKSEK okuma konunun genel yonunun tersini anlatir;
    # iki dal yer degistiriyor (bkz. TERS_SERILER).
    yukari, asagi = (mek[1], mek[0]) if kod in TERS_SERILER else mek

    dallar = (
        Dal(yon="ustunde", baslik=f"{esik} üzerinde gelirse",
            mekanizma=yukari, olcum=olcum),
        Dal(yon="altinda", baslik=f"{esik} altında gelirse",
            mekanizma=asagi, olcum=olcum),
    )
    return Beklenti(kod=kod, ad=ad, son_deger=son, son_tarih=son_tarih,
                    esik_deger=esik, esik_kaynak=kaynak, dallar=dallar)
