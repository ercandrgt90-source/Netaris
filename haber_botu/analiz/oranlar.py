"""Bilanco ve gelir tablosu kalemlerinden oran ve sinyal uretimi.

Bu modul veri kaynagindan tamamen bagimsizdir: kalemler nereden gelirse
gelsin (KAP, elle giris, ucuncu parti) ayni sekilde calisir. Veri kaynagi
degistiginde bu dosyaya dokunulmaz.

Tasarim ilkesi: **model hicbir sayi uretmez.** Butun rakamlar ve oranlar
burada hesaplanir, modele yalnizca yorum birakilir. Modelin aritmetik
yapmasina izin vermek, finansal icerikte en hizli guven kaybi yoludur.

Enflasyon notu -- DIKKAT
------------------------
Turkiye'de buyume rakamini yorumlamadan once kalemlerin hangi esasta
oldugunu bilmek zorunludur. Iki ayri durum var ve karistirilmasi ciddi
hataya yol acar:

1. **TMS 29 duzeltilmis tablolar.** BIST sirketleri 31.12.2023'te sona eren
   hesap donemlerinden itibaren enflasyon muhasebesi uyguluyor. TMS 29
   yalnizca cari donemi degil, **karsilastirmali onceki donem rakamlarini da**
   cari donemin satin alma gucune ceviriyor. Bu durumda iki donem arasindaki
   yuzde degisim ZATEN REELDIR -- ustune TUFE uygulamak enflasyonu iki kez
   dusmek olur ve buyumeyi belirgin sekilde oldugundan az gosterir.

2. **Nominal kalemler.** Duzeltme uygulanmamis rakamlar (ornegin vergi esasli
   tablolar, ya da 2023 oncesi donemler). Burada TUFE ile aritmak zorunludur.

Not: 2025-2027 icin ertelenen sey VUK'a gore **vergi** enflasyon
duzeltmesidir; TMS 29 finansal raporlamasi ayri bir rejimdir ve devam eder.
Ikisi karistirilmamalidir.

Bu yuzden `esas` parametresi ZORUNLUDUR ve varsayilani yoktur. Yanlis
varsayimla sessizce yanlis rakam uretmek, hesaplamayi hic yapmamaktan
kotudur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import bicim


class Kalem:
    """Buyume kalemlerinin adlari -- TEK KAYNAK.

    Bu dizgeler iki isi birden goruyor: sayfada gorunen basliklar ve
    `skor.py` ile `yazar.py` icindeki arama anahtarlari. Elle yazilan bir
    anahtarda harf hatasi sessizce None dondururdu (bolum "hesaplanamadi"
    derdi, kimse fark etmezdi). Sabit olarak tanimlaninca ayni hata
    AttributeError'a donusuyor -- gurultulu hata, sessiz hatadan iyidir.
    """

    HASILAT = "Hasılat"
    BRUT_KAR = "Brüt kâr"
    FAALIYET_KARI = "Faaliyet kârı"
    FAVOK = "FAVÖK"
    NET_KAR = "Net kâr"
    TICARI_ALACAKLAR = "Ticari alacaklar"
    STOKLAR = "Stoklar"
    NET_BORC = "Net borç"


class OranAdi:
    """Oran adlari -- TEK KAYNAK. Gerekcesi icin `Kalem`e bakin."""

    BRUT_MARJ = "Brüt kâr marjı"
    FAALIYET_MARJI = "Faaliyet kâr marjı"
    FAVOK_MARJI = "FAVÖK marjı"
    NET_MARJ = "Net kâr marjı"
    ROE = "Özkaynak kârlılığı (ROE)"
    ROA = "Aktif kârlılığı (ROA)"
    NET_BORC_FAVOK = "Net borç / FAVÖK"
    CARI_ORAN = "Cari oran"
    FAALIYET_DISI = "Faaliyet dışı / net kâr"

    #: Marj bolumunde bu sirayla gosterilir
    MARJLAR = (BRUT_MARJ, FAALIYET_MARJI, FAVOK_MARJI, NET_MARJ)


class Yon(Enum):
    """Bir sinyalin yorumlanma yonu."""

    IYI = "iyi"
    KOTU = "kotu"
    NOTR = "notr"
    DIKKAT = "dikkat"


class EnflasyonEsasi(Enum):
    """Kalemlerin enflasyon karsisindaki durumu.

    TMS29   -- kalemler TMS 29 ile duzeltilmis; karsilastirma zaten reel,
               TUFE ile ayrica aritilmaz. BIST sirketlerinin KAP'ta
               yayimladigi TMS/TFRS tablolari 2023 sonundan itibaren buna
               girer.
    NOMINAL -- kalemler duzeltilmemis; reel rakam icin donem TUFE'si sart.
    """

    TMS29 = "tms29"
    NOMINAL = "nominal"


@dataclass(frozen=True)
class Donem:
    """Tek bir donemin finansal kalemleri, TL cinsinden.

    Zorunlu olmayan kalemler None birakilabilir; ilgili oran o zaman
    hesaplanmaz ve raporda yer almaz. Uydurma degerle doldurmak yerine
    eksik birakmak tercih edilir.
    """

    etiket: str  # "2025/6", "2024/6" gibi

    # Gelir tablosu
    hasilat: float
    brut_kar: float | None = None
    faaliyet_kari: float | None = None
    favok: float | None = None
    net_kar: float | None = None

    # Bilanco
    aktif_toplami: float | None = None
    ozkaynak: float | None = None
    donen_varliklar: float | None = None
    kisa_vadeli_yukumlulukler: float | None = None
    ticari_alacaklar: float | None = None
    stoklar: float | None = None
    net_borc: float | None = None

    # Kar kalitesi icin
    faaliyet_disi_net: float | None = None  # kur farki, faiz, parasal kazanc vb.

    # Nakit akis tablosu -- "sirket gercekten para kazaniyor mu" sorusu
    faaliyet_nakit_akisi: float | None = None
    yatirim_harcamasi: float | None = None  # capex, pozitif sayi = nakit cikisi

    # Borc servisi
    finansman_gideri: float | None = None  # net faiz gideri, pozitif sayi

    @property
    def serbest_nakit_akisi(self) -> float | None:
        """Faaliyet nakit akisi eksi yatirim harcamasi."""
        if self.faaliyet_nakit_akisi is None or self.yatirim_harcamasi is None:
            return None
        return self.faaliyet_nakit_akisi - self.yatirim_harcamasi


@dataclass(frozen=True)
class Oran:
    ad: str
    deger: float
    birim: str  # "%", "x"
    onceki: float | None = None

    @property
    def degisim(self) -> float | None:
        """Puan cinsinden degisim (yuzde degisimi degil)."""
        if self.onceki is None:
            return None
        return self.deger - self.onceki

    def bicimle(self) -> str:
        yuzde_mi = self.birim == "%"
        s = bicim.yuzde(self.deger) if yuzde_mi else bicim.kat(self.deger)
        if self.onceki is not None:
            onc = bicim.yuzde(self.onceki) if yuzde_mi else bicim.kat(self.onceki)
            fark = (
                bicim.puan(self.degisim)
                if yuzde_mi
                else bicim.sayi(self.degisim, 2, isaretli=True) + "x"
            )
            s += f"  (önceki {onc}, {fark})"
        return s


@dataclass(frozen=True)
class Buyume:
    ad: str
    esas: EnflasyonEsasi
    ham: float  # tablodaki iki rakam arasindaki yuzde degisim
    reel: float | None  # enflasyondan aritilmis degisim

    def bicimle(self) -> str:
        if self.esas is EnflasyonEsasi.TMS29:
            # Ham degisim zaten reel -- ikinci bir rakam uretmek yanlis olur
            return f"reel {bicim.yuzde(self.ham, isaretli=True)}  (TMS 29 düzeltilmiş tablolar)"
        s = f"nominal {bicim.yuzde(self.ham, isaretli=True)}"
        if self.reel is not None:
            s += f", reel {bicim.yuzde(self.reel, isaretli=True)}"
        else:
            s += ", reel hesaplanamadı (dönem TÜFE'si verilmedi)"
        return s


class SinyalTuru(Enum):
    """Sinyalin konusu.

    `yazar.py` "neye bakmali" maddelerini bu alana gore seciyor. Onceden
    baslik metninde sozcuk ariyordu; baslik degistigi anda eslesme sessizce
    kayboluyordu. Tur alani metinden bagimsizdir.
    """

    REEL_KUCULME = "reel_kuculme"
    MARJ_DARALMASI = "marj_daralmasi"
    ALACAK_BUYUMESI = "alacak_buyumesi"
    STOK_BUYUMESI = "stok_buyumesi"
    KAR_KALITESI = "kar_kalitesi"
    BORCLULUK = "borcluluk"
    LIKIDITE = "likidite"
    KAR_ZARAR_GECISI = "kar_zarar_gecisi"


@dataclass(frozen=True)
class Sinyal:
    """Insan analistin bakacagi turden bir gozlem."""

    baslik: str
    yon: Yon
    gerekce: str
    tur: SinyalTuru


@dataclass
class Rapor:
    sirket: str
    kod: str
    donem: str
    onceki_donem: str
    esas: EnflasyonEsasi
    enflasyon: float | None
    buyumeler: list[Buyume] = field(default_factory=list)
    oranlar: list[Oran] = field(default_factory=list)
    sinyaller: list[Sinyal] = field(default_factory=list)

    def metin(self) -> str:
        """Modele verilecek ve insanin denetleyecegi duz metin ozet."""
        satirlar = [
            f"{self.sirket} ({self.kod})",
            f"Donem: {self.donem}  |  Karsilastirma: {self.onceki_donem}",
        ]
        if self.esas is EnflasyonEsasi.TMS29:
            satirlar.append(
                "Esas: TMS 29 enflasyon duzeltmesi uygulanmis tablolar. "
                "Karsilastirmali onceki donem rakamlari cari donemin satin alma "
                "gucune cevrilmistir, dolayisiyla asagidaki degisimler REELDIR. "
                "Bu rakamlari 'nominal' olarak adlandirma ve uzerine enflasyon "
                "hesabi yapma."
            )
        else:
            satirlar.append("Esas: nominal (enflasyon duzeltmesi uygulanmamis) kalemler.")
            if self.enflasyon is not None:
                satirlar.append(f"Donem TUFE (yillik): {bicim.yuzde(self.enflasyon)}")

        satirlar.append("\nBUYUME")
        for b in self.buyumeler:
            satirlar.append(f"  {b.ad:<28} {b.bicimle()}")

        satirlar.append("\nORANLAR")
        for o in self.oranlar:
            satirlar.append(f"  {o.ad:<28} {o.bicimle()}")

        satirlar.append("\nSINYALLER")
        if not self.sinyaller:
            satirlar.append("  (dikkat ceken sinyal yok)")
        for s in self.sinyaller:
            satirlar.append(f"  [{s.yon.value.upper():<6}] {s.baslik}")
            satirlar.append(f"           {s.gerekce}")
        return "\n".join(satirlar)


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

def _bol(pay: float | None, bolen: float | None) -> float | None:
    """Guvenli bolme. Bolen sifir, negatif ya da eksikse None doner.

    Negatif bolen ozellikle onemli: negatif ozkaynakla hesaplanan bir
    ozkaynak karliligi matematiksel olarak uretilebilir ama anlamsizdir ve
    yorumlandiginda yaniltir.
    """
    if pay is None or bolen is None or bolen <= 0:
        return None
    return pay / bolen


def _yuzde_degisim(yeni: float | None, eski: float | None) -> float | None:
    """Yuzde degisim. Eski deger sifir ya da negatifse anlamsizdir.

    Zarardan kara gecis gibi durumlarda yuzde degisim yaniltici oldugu icin
    hesaplanmaz; bu durum ayri bir sinyal olarak raporlanir.
    """
    if yeni is None or eski is None or eski <= 0:
        return None
    return (yeni / eski - 1) * 100


def _reel(nominal_yuzde: float, enflasyon_yuzde: float) -> float:
    """Nominal buyumeyi enflasyondan aritir.

    Dogru formul carpimsaldir: (1+n)/(1+e)-1. Basit cikarma (n-e) yuksek
    enflasyonda belirgin sekilde yanlis sonuc verir.
    """
    return ((1 + nominal_yuzde / 100) / (1 + enflasyon_yuzde / 100) - 1) * 100


def _buyume(
    ad: str,
    yeni: float | None,
    eski: float | None,
    esas: EnflasyonEsasi,
    enflasyon: float | None,
) -> Buyume | None:
    ham = _yuzde_degisim(yeni, eski)
    if ham is None:
        return None

    if esas is EnflasyonEsasi.TMS29:
        # Iki rakam da ayni satin alma gucunde -- degisim zaten reel
        reel: float | None = ham
    elif enflasyon is not None:
        reel = _reel(ham, enflasyon)
    else:
        reel = None

    return Buyume(ad=ad, esas=esas, ham=ham, reel=reel)


def _marj(pay: float | None, hasilat: float) -> float | None:
    o = _bol(pay, hasilat)
    return o * 100 if o is not None else None


def _yuz(oran: float | None) -> float | None:
    """Orani yuzdeye cevirir.

    `x * 100 if x else None` YAZILMAZ: dogruluk kontrolu, orani tam SIFIR
    olan kalemi "hesaplanamadi" sayar. Net kari tam sifir olan bir donemde
    ROE %0'dir -- olculemedi degil. Sifir da bir olcumdur ve skorda
    "olculemedi" ile "sifir performans" cok farkli sonuc verir.
    """
    return None if oran is None else oran * 100


def _oran_ekle(
    liste: list[Oran], ad: str, deger: float | None, birim: str, onceki: float | None
) -> None:
    if deger is not None:
        liste.append(Oran(ad=ad, deger=deger, birim=birim, onceki=onceki))


# ---------------------------------------------------------------------------
# Ana hesaplama
# ---------------------------------------------------------------------------

def hesapla(
    sirket: str,
    kod: str,
    simdi: Donem,
    once: Donem,
    esas: EnflasyonEsasi,
    enflasyon: float | None = None,
) -> Rapor:
    """Iki donemi karsilastirip oran ve sinyal raporu uretir.

    `esas` zorunludur ve varsayilani yoktur -- modulun basindaki enflasyon
    notuna bakin. NOMINAL esasta donem TUFE'si de zorunludur; verilmezse
    hesaplama reddedilir, cunku reel rakam uretmeden buyume yorumlamak
    Turkiye kosullarinda yaniltici olur.
    """
    if esas is EnflasyonEsasi.NOMINAL and enflasyon is None:
        raise ValueError(
            "NOMINAL esasta donem TUFE'si zorunludur. Kalemler TMS 29 ile "
            "duzeltilmisse esas=EnflasyonEsasi.TMS29 kullanin."
        )
    if esas is EnflasyonEsasi.TMS29 and enflasyon is not None:
        raise ValueError(
            "TMS 29 duzeltilmis tablolarda degisim zaten reeldir; TUFE "
            "vermek enflasyonu iki kez dusmeye yol acar. enflasyon=None birakin."
        )

    rapor = Rapor(
        sirket=sirket,
        kod=kod,
        donem=simdi.etiket,
        onceki_donem=once.etiket,
        esas=esas,
        enflasyon=enflasyon,
    )

    # --- Buyume ---
    for ad, y, e in (
        (Kalem.HASILAT, simdi.hasilat, once.hasilat),
        (Kalem.BRUT_KAR, simdi.brut_kar, once.brut_kar),
        (Kalem.FAALIYET_KARI, simdi.faaliyet_kari, once.faaliyet_kari),
        (Kalem.FAVOK, simdi.favok, once.favok),
        (Kalem.NET_KAR, simdi.net_kar, once.net_kar),
        (Kalem.TICARI_ALACAKLAR, simdi.ticari_alacaklar, once.ticari_alacaklar),
        (Kalem.STOKLAR, simdi.stoklar, once.stoklar),
        (Kalem.NET_BORC, simdi.net_borc, once.net_borc),
    ):
        b = _buyume(ad, y, e, esas, enflasyon)
        if b is not None:
            rapor.buyumeler.append(b)

    # --- Marjlar ---
    _oran_ekle(rapor.oranlar, OranAdi.BRUT_MARJ, _marj(simdi.brut_kar, simdi.hasilat), "%",
               _marj(once.brut_kar, once.hasilat))
    _oran_ekle(rapor.oranlar, OranAdi.FAALIYET_MARJI, _marj(simdi.faaliyet_kari, simdi.hasilat), "%",
               _marj(once.faaliyet_kari, once.hasilat))
    _oran_ekle(rapor.oranlar, OranAdi.FAVOK_MARJI, _marj(simdi.favok, simdi.hasilat), "%",
               _marj(once.favok, once.hasilat))
    _oran_ekle(rapor.oranlar, OranAdi.NET_MARJ, _marj(simdi.net_kar, simdi.hasilat), "%",
               _marj(once.net_kar, once.hasilat))

    # --- Karlilik ---
    roe_s, roe_o = _bol(simdi.net_kar, simdi.ozkaynak), _bol(once.net_kar, once.ozkaynak)
    _oran_ekle(rapor.oranlar, OranAdi.ROE, _yuz(roe_s), "%",
               _yuz(roe_o))
    roa_s, roa_o = _bol(simdi.net_kar, simdi.aktif_toplami), _bol(once.net_kar, once.aktif_toplami)
    _oran_ekle(rapor.oranlar, OranAdi.ROA, _yuz(roa_s), "%",
               _yuz(roa_o))

    # --- Borcluluk ve likidite ---
    _oran_ekle(rapor.oranlar, OranAdi.NET_BORC_FAVOK,
               _bol(simdi.net_borc, simdi.favok), "x", _bol(once.net_borc, once.favok))
    _oran_ekle(rapor.oranlar, OranAdi.CARI_ORAN,
               _bol(simdi.donen_varliklar, simdi.kisa_vadeli_yukumlulukler), "x",
               _bol(once.donen_varliklar, once.kisa_vadeli_yukumlulukler))

    # --- Kar kalitesi ---
    kalite_s = _bol(simdi.faaliyet_disi_net, simdi.net_kar)
    kalite_o = _bol(once.faaliyet_disi_net, once.net_kar)
    _oran_ekle(rapor.oranlar, OranAdi.FAALIYET_DISI,
               _yuz(kalite_s), "%",
               _yuz(kalite_o))

    rapor.sinyaller = _sinyaller(simdi, once, enflasyon, rapor)
    return rapor


def _sinyaller(
    simdi: Donem, once: Donem, enflasyon: float | None, rapor: Rapor
) -> list[Sinyal]:
    """Insan analistin bakacagi turden gozlemleri uretir.

    Bunlar yorum degil, olgu tespitidir: esikleri asan durumlar isaretlenir,
    ne anlama geldigini modele (ve insana) birakir.
    """
    sinyaller: list[Sinyal] = []
    bul = {b.ad: b for b in rapor.buyumeler}

    # 1. Reel kuculme
    for ad in (Kalem.HASILAT, Kalem.NET_KAR, Kalem.FAVOK):
        b = bul.get(ad)
        if b and b.reel is not None and b.reel < 0:
            if b.esas is EnflasyonEsasi.TMS29:
                gerekce = (
                    f"TMS 29 düzeltilmiş tablolarda {bicim.yuzde(b.reel, isaretli=True)} — "
                    "enflasyondan arıtılmış değişim negatif"
                )
            else:
                gerekce = (
                    f"nominal {bicim.yuzde(b.ham, isaretli=True)} artış, dönem enflasyonu "
                    f"{bicim.yuzde(enflasyon)} — reel {bicim.yuzde(b.reel, isaretli=True)}"
                )
            sinyaller.append(
                Sinyal(
                    baslik=f"{ad} reel olarak küçüldü",
                    yon=Yon.KOTU,
                    gerekce=gerekce,
                    tur=SinyalTuru.REEL_KUCULME,
                )
            )

    # 2. Marj daralmasi
    for o in rapor.oranlar:
        if o.ad in OranAdi.MARJLAR and o.degisim is not None and o.degisim <= -2.0:
            sinyaller.append(
                Sinyal(
                    baslik=f"{o.ad} daraldı",
                    yon=Yon.KOTU,
                    gerekce=(
                        f"{bicim.yuzde(o.onceki)} → {bicim.yuzde(o.deger)} "
                        f"({bicim.puan(o.degisim)})"
                    ),
                    tur=SinyalTuru.MARJ_DARALMASI,
                )
            )

    # 3. Alacaklar hasilattan hizli buyuduyse tahsilat sinyali.
    # Iki kalem de ayni esasta oldugu icin karsilastirma tutarli -- her iki
    # esasta da ham degisimler dogrudan kiyaslanabilir.
    has, alac = bul.get(Kalem.HASILAT), bul.get(Kalem.TICARI_ALACAKLAR)
    if has and alac and alac.ham > has.ham * 1.3:
        sinyaller.append(
            Sinyal(
                baslik="Ticari alacaklar hasılattan belirgin hızlı büyüdü",
                yon=Yon.DIKKAT,
                gerekce=(
                    f"alacaklar {bicim.yuzde(alac.ham, isaretli=True)}, "
                    f"hasılat {bicim.yuzde(has.ham, isaretli=True)} — "
                    "satışların nakde dönüşüm hızı yavaşlamış olabilir"
                ),
                tur=SinyalTuru.ALACAK_BUYUMESI,
            )
        )

    # 4. Stoklar hasilattan hizli buyuduyse talep sinyali
    stok = bul.get(Kalem.STOKLAR)
    if has and stok and stok.ham > has.ham * 1.3:
        sinyaller.append(
            Sinyal(
                baslik="Stoklar hasılattan hızlı büyüdü",
                yon=Yon.DIKKAT,
                gerekce=(
                    f"stoklar {bicim.yuzde(stok.ham, isaretli=True)}, "
                    f"hasılat {bicim.yuzde(has.ham, isaretli=True)} — "
                    "talepte yavaşlama ya da bilinçli stok politikası olabilir"
                ),
                tur=SinyalTuru.STOK_BUYUMESI,
            )
        )

    # 5. Kar kalitesi: net karin buyuk kismi faaliyet disiysa
    kalite = _bol(simdi.faaliyet_disi_net, simdi.net_kar)
    if kalite is not None and kalite >= 0.30:
        sinyaller.append(
            Sinyal(
                baslik="Net kârın önemli bölümü esas faaliyetten gelmiyor",
                yon=Yon.DIKKAT,
                gerekce=(
                    # Ayni yazida bu oran "Kar nereden geldi?" bolumunde de
                    # geciyor; iki yerde farkli yuvarlanirsa okur ayni sayinin
                    # iki degeri oldugunu sanir.
                    f"faaliyet dışı net gelir, net kârın "
                    f"{bicim.yuzde(kalite * 100)}'ini oluşturuyor — "
                    "bu kalem tekrarlanabilir olmayabilir"
                ),
                tur=SinyalTuru.KAR_KALITESI,
            )
        )

    # 6. Borclulukta bozulma
    nb_s = _bol(simdi.net_borc, simdi.favok)
    nb_o = _bol(once.net_borc, once.favok)
    if nb_s is not None and nb_o is not None and nb_s > nb_o + 0.5:
        yon = Yon.KOTU if nb_s >= 3.0 else Yon.DIKKAT
        sinyaller.append(
            Sinyal(
                baslik=f"{OranAdi.NET_BORC_FAVOK} yükseldi",
                yon=yon,
                gerekce=(
                    f"{bicim.kat(nb_o)} → {bicim.kat(nb_s)} — borcun faaliyet nakit "
                    "akışıyla kapanma süresi uzadı"
                ),
                tur=SinyalTuru.BORCLULUK,
            )
        )

    # 7. Likidite
    cari = _bol(simdi.donen_varliklar, simdi.kisa_vadeli_yukumlulukler)
    if cari is not None and cari < 1.0:
        sinyaller.append(
            Sinyal(
                baslik="Cari oran 1'in altında",
                yon=Yon.KOTU,
                gerekce=(
                    f"{bicim.kat(cari)} — kısa vadeli yükümlülükler dönen "
                    "varlıkları aşıyor"
                ),
                tur=SinyalTuru.LIKIDITE,
            )
        )

    # 8. Zarar/kar gecisleri: yuzde degisimin anlamsiz oldugu durumlar
    if simdi.net_kar is not None and once.net_kar is not None:
        if once.net_kar <= 0 < simdi.net_kar:
            sinyaller.append(
                Sinyal(
                    baslik="Önceki dönem zararıyla karşılaştırma",
                    yon=Yon.NOTR,
                    gerekce=(
                        "zarardan kâra geçiş — yüzde değişim hesaplanmadı, "
                        "yanıltıcı olurdu"
                    ),
                    tur=SinyalTuru.KAR_ZARAR_GECISI,
                )
            )
        elif simdi.net_kar <= 0 < once.net_kar:
            zarar = f"{abs(simdi.net_kar):,.0f}".replace(",", ".")
            sinyaller.append(
                Sinyal(
                    baslik="Dönem zararla kapandı",
                    yon=Yon.KOTU,
                    gerekce=(
                        f"önceki dönem kâr açıklanmıştı, bu dönem {zarar} TL zarar"
                    ),
                    tur=SinyalTuru.KAR_ZARAR_GECISI,
                )
            )

    return sinyaller
