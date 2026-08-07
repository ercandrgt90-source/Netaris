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

ESIK KONSENSUS, YOKSA ONCEKI DEGER
----------------------------------
Ilk surumde esik HER ZAMAN onceki degerdi ve bu sadece eksik degil
YANLIS sonuc uretiyordu. Kullanici gosterdi: Tarim Disi Istihdam'da
beklenti 85 bin, onceki 57 bin. Gerceklesen 70 bin gelse kutu "onceki
57'nin UZERINDE -> is gucu piyasasi beklenenden GUCLU" derdi; oysa
70 bin beklentinin ALTINDA ve tam tersini anlatir.

Artik konsensus varsa esik ODUR (bkz. yayin_takvimi.FF_ESLEME).
Konsensus yoksa esik onceki degerdir ve ekranda ACIKCA oyle yaziyor --
ikisini ayni etiketle sunmak yukaridaki hatayi geri getirirdi.
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
#:
#: `{kiyas}` KIYAS TABANINI tasiyor ve bos birakilamaz. Sebep somut:
#: ilk surumde cumleler "beklenenden güçlü" diyordu ama esik cogu
#: seride BEKLENTI DEGIL ONCEKI DEGERDI. Yani cumle, olmayan bir
#: beklentiye gore konusuyordu. Konsensus varsa "beklenenden", yoksa
#: "önceki döneme göre" yaziliyor -- ikisi ayni sey degil ve okur
#: hangisine baktigini bilmeli.
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
        "İş gücü piyasası {kiyas} güçlü demektir; ücret baskısı ve "
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
        "Talep {kiyas} güçlü demektir; kapasite kullanımı ve fiyat "
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
        tepkiler: list[tuple[str, float]] | None = None,
        esik_metin: str = "", son_metin: str = "",
        esik_kaynagi: str = "") -> Beklenti:
    """Bir veri aciklamasi icin beklenti kutusu.

    KONSENSUS VARSA ESIK ODUR. `esik_metin` bir takvim kaynagindan
    gelen KONSENSUS rakami ("85K", "0.3%") -- kaynagin yayimladigi
    bicimde, cevrilmeden.

    NEDEN CEVIRMIYORUZ: konsensus ve onceki deger AYNI kaynaktan
    geliyor, yani birimleri kesinlikle uyumlu. Kendi depomuzdaki
    degerle karistirmak iki farkli birimi ayni cumleye koyma riski
    demek ("85K" ile "57,00 bin kişi" ayni sey ama ayni bicimde degil).

    Konsensus yoksa esik SON ACIKLANAN DEGER olur ve ekranda acikca
    "önceki" diye etiketlenir -- cunku ikisini karistirmak YANLIS
    yorum uretiyor: beklenti 85, onceki 57 iken gerceklesen 70,
    "onceki uzerinde" ama "beklentinin altinda"dir ve mekanizma
    cumlesi ters calisir.
    """
    # Kaynaktan gelen metin varsa sayisal degere ihtiyac yok.
    if son_metin or esik_metin:
        son = son_metin or (bicimle(son_deger, son_birim)
                            if son_deger is not None else "")
        if esik_metin:
            esik, kaynak = esik_metin, (esik_kaynagi or "beklenti")
        elif son:
            esik, kaynak = son, "onceki"
        else:
            return Beklenti(kod=kod, ad=ad)
    elif son_deger is None:
        return Beklenti(kod=kod, ad=ad)
    else:
        son = bicimle(son_deger, son_birim)
        if esik_deger is not None:
            esik = bicimle(esik_deger, esik_birim or son_birim)
            kaynak = "beklenti"
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

    # Kiyas tabani cumleye yaziliyor: esik konsensus mu, onceki deger mi.
    kiyas = ("beklenenden" if kaynak == "beklenti"
             else "önceki döneme göre")
    yukari = yukari.format(kiyas=kiyas)
    asagi = asagi.format(kiyas=kiyas)

    dallar = (
        Dal(yon="ustunde", baslik=f"{esik} üzerinde gelirse",
            mekanizma=yukari, olcum=olcum),
        Dal(yon="altinda", baslik=f"{esik} altında gelirse",
            mekanizma=asagi, olcum=olcum),
    )
    return Beklenti(kod=kod, ad=ad, son_deger=son, son_tarih=son_tarih,
                    esik_deger=esik, esik_kaynak=kaynak, dallar=dallar)
