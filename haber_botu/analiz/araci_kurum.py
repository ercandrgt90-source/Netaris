"""Araci kurum (yatirim menkul degerler) bilanco motoru.

NEDEN AYRI MODUL
----------------
`oranlar.py` sanayi/ticaret sirketi icin kurulu. Araci kuruma uygulanirsa
sessizce yanlis okur:

  * **Hasilat aldaticidir.** Araci kurumun "Satis Gelirleri" kalemi islem
    HACMINI icerir -- musteri adina alinip satilan menkul kiymetlerin brut
    tutari. Milyarlarca TL gorunur ve sirketin buyuklugunu degil, islem
    hacmini olcer. "Hasilat %300 artti" cumlesi burada anlamsizdir.
    Gercek gelir olcusu **brut kardir**: satis gelirleri eksi satislarin
    maliyeti = komisyon + net alim satim kari.
  * **Stok yoktur.** Stok/hasilat sinyali hic uretilmemeli.
  * **Net borc / FAVOK anlamsizdir.** Araci kurumun borcu operasyoneldir
    (musteri alacaklari, para piyasasi fonlamasi); sanayi sirketindeki gibi
    "kac yilda kapanir" sorusu sorulmaz.
  * **FAVOK standart metrik degildir.** Amortisman finansal kurumda kucuk
    bir kalemdir; FAVOK marji yanlis bir buyukluk uretir.

Bu yuzden burada AYRI oran seti, AYRI sinyaller ve AYRI skor var.

KAPSAM
------
Bu modul **araci kurum** icindir. Banka ve sigorta sirketi FARKLI kalemlerle
raporlar (net faiz geliri, sermaye yeterliligi, teknik karsiliklar,
kombine oran). Onlar icin bu modul kullanilmaz; `Sektor` kontrolu yanlis
kullanimi engeller. Yanlis sektorde sayi uretmektense hic uretmemek.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import bicim


class Sektor(Enum):
    """Hangi motorun kullanilacagini belirler."""

    SANAYI = "sanayi"            # oranlar.py
    ARACI_KURUM = "araci_kurum"  # bu modul
    BANKA = "banka"              # henuz yok
    SIGORTA = "sigorta"          # henuz yok


class DesteklenmeyenSektor(RuntimeError):
    """Bu sektor icin dogru motor henuz yazilmadi."""


class Kalem:
    """Araci kurum kalem adlari -- TEK KAYNAK."""

    BRUT_KAR = "Brüt kâr (komisyon + net alım satım)"
    FAALIYET_KARI = "Esas faaliyet kârı"
    NET_KAR = "Net kâr"
    OZKAYNAK = "Özkaynak"
    AKTIF = "Aktif toplamı"


class OranAdi:
    """Araci kurumda anlamli oranlar."""

    ROE = "Özkaynak kârlılığı (ROE)"
    ROA = "Aktif kârlılığı (ROA)"
    FAALIYET_MARJI = "Faaliyet kârı / brüt kâr"
    NET_MARJ = "Net kâr / brüt kâr"
    GIDER_ORANI = "Faaliyet gideri / brüt kâr"
    KALDIRAC = "Aktif / özkaynak"
    OZKAYNAK_PAYI = "Özkaynak / aktif"
    FAALIYET_DISI = "Faaliyet dışı / net kâr"
    NAKIT_DONUSUMU = "Faaliyet nakit akışı / net kâr"
    YATIRIM_PAYI = "Yatırım geliri / vergi öncesi kâr"
    MUSTERI_BORCU_PAYI = "Ticari borçlar / aktif"


class Yon(Enum):
    IYI = "iyi"
    KOTU = "kotu"
    NOTR = "notr"
    DIKKAT = "dikkat"


@dataclass(frozen=True)
class Donem:
    """Araci kurumun bir donemi.

    `satis_gelirleri` bilincli olarak SAKLANIR ama oran hesabinda
    kullanilmaz -- yazida "bu rakam islem hacmidir, gelir degildir"
    diyebilmek icin tutulur.
    """

    etiket: str

    brut_kar: float                      # ana gelir olcusu
    satis_gelirleri: float | None = None  # islem hacmi -- gelir DEGIL
    faaliyet_kari: float | None = None
    net_kar: float | None = None
    faaliyet_giderleri: float | None = None  # genel yonetim + pazarlama
    faaliyet_disi_net: float | None = None

    #: Yatirim faaliyetlerinden net gelir. Araci kurumda bu kalem esas
    #: faaliyet karini asabiliyor -- portfoyun getirisi komisyon gelirinden
    #: buyuk olabilir. Kar motorunun nerede oldugunu bu belirler.
    yatirim_gelirleri_net: float | None = None
    vergi_oncesi_kar: float | None = None
    #: Pozitifse vergi GELIRI (ertelenmis vergi). Kari yukseltir.
    vergi: float | None = None
    #: TMS 29 net parasal pozisyon kazanci/kaybi. Net parasal VARLIK tutan
    #: sirket enflasyonda kayip yazar -- nakdi bol araci kurumda buyuk olur.
    parasal_pozisyon: float | None = None

    aktif_toplami: float | None = None
    ozkaynak: float | None = None
    nakit: float | None = None
    #: Musteri varliklarindan dogan borclar. Araci kurumun bilancosunu
    #: sisiren ana kalem; "sirketin borcu" gibi okunmamali.
    ticari_borclar: float | None = None
    finansman_gideri: float | None = None
    faaliyet_nakit_akisi: float | None = None
    amortisman: float | None = None


@dataclass(frozen=True)
class Oran:
    ad: str
    deger: float
    birim: str  # "%" veya "x"
    onceki: float | None = None

    @property
    def degisim(self) -> float | None:
        return None if self.onceki is None else self.deger - self.onceki

    def bicimle(self) -> str:
        yuzde_mi = self.birim == "%"
        s = bicim.yuzde(self.deger) if yuzde_mi else bicim.kat(self.deger)
        if self.onceki is not None:
            onc = bicim.yuzde(self.onceki) if yuzde_mi else bicim.kat(self.onceki)
            fark = (
                bicim.puan(self.degisim) if yuzde_mi
                else bicim.sayi(self.degisim, 2, isaretli=True) + "x"
            )
            s += f"  (önceki {onc}, {fark})"
        return s


@dataclass(frozen=True)
class Buyume:
    ad: str
    reel: float


@dataclass(frozen=True)
class Sinyal:
    baslik: str
    yon: Yon
    gerekce: str


@dataclass
class Rapor:
    sirket: str
    kod: str
    donem: str
    onceki_donem: str
    sektor: Sektor = Sektor.ARACI_KURUM
    buyumeler: list[Buyume] = field(default_factory=list)
    oranlar: list[Oran] = field(default_factory=list)
    sinyaller: list[Sinyal] = field(default_factory=list)
    notlar: list[str] = field(default_factory=list)

    def bul(self, ad: str) -> Oran | None:
        return next((o for o in self.oranlar if o.ad == ad), None)

    def buyume(self, ad: str) -> float | None:
        b = next((x for x in self.buyumeler if x.ad == ad), None)
        return b.reel if b else None


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

def _bol(pay: float | None, bolen: float | None) -> float | None:
    if pay is None or bolen is None or bolen <= 0:
        return None
    return pay / bolen


def _degisim(yeni: float | None, eski: float | None) -> float | None:
    if yeni is None or eski is None or eski <= 0:
        return None
    return (yeni / eski - 1) * 100


def _yuz(oran: float | None) -> float | None:
    """Orani yuzdeye cevirir.

    `x * 100 if x else None` YAZILMAZ: bu dogruluk kontrolu yapar ve orani
    tam SIFIR olan bir kalemi "hesaplanamadi" sayar. Net kari tam sifir olan
    bir donemde ROE %0'dir -- olculemedi degil. Sifir da bir olcumdur.
    """
    return None if oran is None else oran * 100


def _ekle(liste: list[Oran], ad: str, deger: float | None, birim: str,
          onceki: float | None) -> None:
    if deger is not None:
        liste.append(Oran(ad=ad, deger=deger, birim=birim, onceki=onceki))


# ---------------------------------------------------------------------------
# Ana hesaplama
# ---------------------------------------------------------------------------

def hesapla(
    sirket: str, kod: str, simdi: Donem, once: Donem,
    sektor: Sektor = Sektor.ARACI_KURUM,
) -> Rapor:
    """Araci kurum icin oran ve sinyal raporu uretir.

    Kalemler TMS 29 duzeltilmis kabul edilir (BIST sirketleri 2023 sonundan
    beri boyle raporluyor), dolayisiyla degisimler zaten reeldir.
    """
    if sektor is not Sektor.ARACI_KURUM:
        raise DesteklenmeyenSektor(
            f"{sektor.value} icin dogru motor henuz yazilmadi. "
            "Banka ve sigorta farkli kalemlerle raporlar (net faiz geliri, "
            "sermaye yeterliligi, teknik karsiliklar); bu moduldeki oranlar "
            "onlarda yanlis sonuc verir."
        )

    r = Rapor(sirket=sirket, kod=kod, donem=simdi.etiket,
              onceki_donem=once.etiket, sektor=sektor)

    # --- Buyume: hasilat DEGIL, brut kar ---
    for ad, y, e in (
        (Kalem.BRUT_KAR, simdi.brut_kar, once.brut_kar),
        (Kalem.FAALIYET_KARI, simdi.faaliyet_kari, once.faaliyet_kari),
        (Kalem.NET_KAR, simdi.net_kar, once.net_kar),
        (Kalem.OZKAYNAK, simdi.ozkaynak, once.ozkaynak),
        (Kalem.AKTIF, simdi.aktif_toplami, once.aktif_toplami),
    ):
        d = _degisim(y, e)
        if d is not None:
            r.buyumeler.append(Buyume(ad=ad, reel=d))

    # Islem hacmi bilgi olarak tutulur, oran hesabina girmez
    if simdi.satis_gelirleri is not None:
        hacim_d = _degisim(simdi.satis_gelirleri, once.satis_gelirleri)
        r.notlar.append(
            "Satış gelirleri kalemi işlem hacmini içerir ve gelir ölçüsü "
            "değildir; büyüme hesaplarında brüt kâr esas alınmıştır"
            + (f" (hacim değişimi {bicim.yuzde(hacim_d, isaretli=True)})."
               if hacim_d is not None else ".")
        )

    # --- Karlilik ---
    roe_s, roe_o = _bol(simdi.net_kar, simdi.ozkaynak), _bol(once.net_kar, once.ozkaynak)
    _ekle(r.oranlar, OranAdi.ROE, _yuz(roe_s), "%",
          _yuz(roe_o))

    roa_s, roa_o = _bol(simdi.net_kar, simdi.aktif_toplami), _bol(once.net_kar, once.aktif_toplami)
    _ekle(r.oranlar, OranAdi.ROA, _yuz(roa_s), "%",
          _yuz(roa_o))

    # --- Verimlilik: marjlar brut kara gore, hasilata gore DEGIL ---
    fm_s, fm_o = _bol(simdi.faaliyet_kari, simdi.brut_kar), _bol(once.faaliyet_kari, once.brut_kar)
    _ekle(r.oranlar, OranAdi.FAALIYET_MARJI, _yuz(fm_s), "%",
          _yuz(fm_o))

    nm_s, nm_o = _bol(simdi.net_kar, simdi.brut_kar), _bol(once.net_kar, once.brut_kar)
    _ekle(r.oranlar, OranAdi.NET_MARJ, _yuz(nm_s), "%",
          _yuz(nm_o))

    g_s, g_o = _bol(simdi.faaliyet_giderleri, simdi.brut_kar), _bol(once.faaliyet_giderleri, once.brut_kar)
    _ekle(r.oranlar, OranAdi.GIDER_ORANI, _yuz(g_s), "%",
          _yuz(g_o))

    # --- Sermaye yapisi ---
    k_s, k_o = _bol(simdi.aktif_toplami, simdi.ozkaynak), _bol(once.aktif_toplami, once.ozkaynak)
    _ekle(r.oranlar, OranAdi.KALDIRAC, k_s, "x", k_o)

    o_s, o_o = _bol(simdi.ozkaynak, simdi.aktif_toplami), _bol(once.ozkaynak, once.aktif_toplami)
    _ekle(r.oranlar, OranAdi.OZKAYNAK_PAYI, _yuz(o_s), "%",
          _yuz(o_o))

    # --- Kar kalitesi ---
    fd_s, fd_o = _bol(simdi.faaliyet_disi_net, simdi.net_kar), _bol(once.faaliyet_disi_net, once.net_kar)
    _ekle(r.oranlar, OranAdi.FAALIYET_DISI, _yuz(fd_s), "%", _yuz(fd_o))

    # Nakit donusumu: negatif FNA MESRU bir sonuctur ve tam da gormek
    # istedigimiz sey -- bolen (net kar) pozitif oldugu surece oran anlamli.
    # Zararli donemde oran anlamsizlasir, o yuzden uretilmez.
    nd_s = (
        simdi.faaliyet_nakit_akisi / simdi.net_kar
        if simdi.faaliyet_nakit_akisi is not None and simdi.net_kar and simdi.net_kar > 0
        else None
    )
    nd_o = (
        once.faaliyet_nakit_akisi / once.net_kar
        if once.faaliyet_nakit_akisi is not None and once.net_kar and once.net_kar > 0
        else None
    )
    _ekle(r.oranlar, OranAdi.NAKIT_DONUSUMU, nd_s, "x", nd_o)

    yp_s = _bol(simdi.yatirim_gelirleri_net, simdi.vergi_oncesi_kar)
    yp_o = _bol(once.yatirim_gelirleri_net, once.vergi_oncesi_kar)
    _ekle(r.oranlar, OranAdi.YATIRIM_PAYI, _yuz(yp_s), "%", _yuz(yp_o))

    mb_s = _bol(simdi.ticari_borclar, simdi.aktif_toplami)
    mb_o = _bol(once.ticari_borclar, once.aktif_toplami)
    _ekle(r.oranlar, OranAdi.MUSTERI_BORCU_PAYI, _yuz(mb_s), "%", _yuz(mb_o))

    r.sinyaller = _sinyaller(r, simdi, once)
    return r


def _sinyaller(r: Rapor, simdi: Donem, once: Donem) -> list[Sinyal]:
    s: list[Sinyal] = []

    bk = r.buyume(Kalem.BRUT_KAR)
    if bk is not None and bk < 0:
        s.append(Sinyal(
            baslik="Brüt kâr reel olarak küçüldü",
            yon=Yon.KOTU,
            gerekce=(
                f"{bicim.yuzde(bk, isaretli=True)} — komisyon ve alım satım "
                "gelirlerinin toplamı geriledi"
            ),
        ))

    gider = r.bul(OranAdi.GIDER_ORANI)
    if gider is not None and gider.degisim is not None and gider.degisim >= 3.0:
        s.append(Sinyal(
            baslik="Gider oranı yükseldi",
            yon=Yon.KOTU,
            gerekce=(
                f"{bicim.yuzde(gider.onceki)} → {bicim.yuzde(gider.deger)} "
                f"({bicim.puan(gider.degisim)}) — brüt kârın daha büyük bölümü "
                "faaliyet giderlerine gidiyor"
            ),
        ))

    roe = r.bul(OranAdi.ROE)
    if roe is not None and roe.degisim is not None:
        if roe.degisim <= -3.0:
            s.append(Sinyal(
                baslik="Özkaynak kârlılığı geriledi",
                yon=Yon.KOTU,
                gerekce=(
                    f"{bicim.yuzde(roe.onceki)} → {bicim.yuzde(roe.deger)} "
                    f"({bicim.puan(roe.degisim)})"
                ),
            ))
        elif roe.degisim >= 3.0:
            s.append(Sinyal(
                baslik="Özkaynak kârlılığı yükseldi",
                yon=Yon.IYI,
                gerekce=(
                    f"{bicim.yuzde(roe.onceki)} → {bicim.yuzde(roe.deger)} "
                    f"({bicim.puan(roe.degisim)})"
                ),
            ))

    kaldirac = r.bul(OranAdi.KALDIRAC)
    if kaldirac is not None and kaldirac.degisim is not None and kaldirac.degisim >= 1.0:
        s.append(Sinyal(
            baslik="Kaldıraç arttı",
            yon=Yon.DIKKAT,
            gerekce=(
                f"aktif/özkaynak {bicim.kat(kaldirac.onceki)} → "
                f"{bicim.kat(kaldirac.deger)} — bilanço özkaynağa göre "
                "daha hızlı büyüdü"
            ),
        ))

    # Nakit: muhasebe kari ile gercek para arasindaki fark
    if simdi.faaliyet_nakit_akisi is not None and simdi.net_kar and simdi.net_kar > 0:
        fna = simdi.faaliyet_nakit_akisi
        if fna < 0:
            s.append(Sinyal(
                baslik="Faaliyet nakit akışı negatif",
                yon=Yon.KOTU,
                gerekce=(
                    f"dönem kârı {bicim.sayi(simdi.net_kar / 1e9, 2)} milyar TL iken "
                    f"işletme faaliyetlerinden nakit akışı "
                    f"{bicim.sayi(fna / 1e9, 2)} milyar TL — muhasebe kârı nakde "
                    "dönmemiş"
                ),
            ))
        elif fna / simdi.net_kar < 0.5:
            s.append(Sinyal(
                baslik="Kârın nakde dönüşümü zayıf",
                yon=Yon.DIKKAT,
                gerekce=(
                    f"faaliyet nakit akışı / net kâr "
                    f"{bicim.kat(fna / simdi.net_kar)}"
                ),
            ))

    # Kar motoru nerede: komisyon mu, portfoy mu
    yp = r.bul(OranAdi.YATIRIM_PAYI)
    if yp is not None and yp.deger >= 50:
        s.append(Sinyal(
            baslik="Kârın ağırlığı yatırım faaliyetlerinden geliyor",
            yon=Yon.DIKKAT,
            gerekce=(
                f"yatırım faaliyeti gelirleri, vergi öncesi kârın "
                f"{bicim.yuzde(yp.deger)}'ine denk — aracılık komisyonu değil "
                "portföy getirisi ağır basıyor, bu kalem piyasa koşullarına "
                "aracılık gelirinden daha duyarlıdır"
            ),
        ))

    # TMS 29: net parasal varlik tutan sirket enflasyonda kaybeder
    if simdi.parasal_pozisyon is not None and simdi.vergi_oncesi_kar:
        pp = simdi.parasal_pozisyon
        if pp < 0 and abs(pp) / abs(simdi.vergi_oncesi_kar) >= 0.10:
            s.append(Sinyal(
                baslik="Net parasal pozisyon kaybı",
                yon=Yon.NOTR,
                gerekce=(
                    f"TMS 29 kapsamında {bicim.sayi(abs(pp) / 1e9, 2)} milyar TL "
                    f"parasal kayıp yazılmış — vergi öncesi kârın "
                    f"{bicim.yuzde(abs(pp) / abs(simdi.vergi_oncesi_kar) * 100)}'i. "
                    "Nakit ve alacak gibi parasal varlıkları borçlarından fazla "
                    "olan şirket enflasyon ortamında bu kalemde kayıp yazar"
                ),
            ))

    # Vergi GELIRI kari yukseltmisse bunu soylemek sart
    if simdi.vergi is not None and simdi.vergi > 0 and simdi.vergi_oncesi_kar:
        pay = simdi.vergi / simdi.net_kar if simdi.net_kar else None
        if pay is not None and pay >= 0.05:
            s.append(Sinyal(
                baslik="Dönem kârını vergi geliri yükseltmiş",
                yon=Yon.DIKKAT,
                gerekce=(
                    f"vergi satırı gider değil {bicim.sayi(simdi.vergi / 1e9, 2)} "
                    f"milyar TL GELİR olarak yazılmış (net kârın "
                    f"{bicim.yuzde(pay * 100)}'i); ertelenmiş vergi kaynaklı bu "
                    "kalem her dönem tekrarlanmaz"
                ),
            ))

    # Gider orani iyilesmesi
    if gider is not None and gider.degisim is not None and gider.degisim <= -3.0:
        s.append(Sinyal(
            baslik="Gider oranı geriledi",
            yon=Yon.IYI,
            gerekce=(
                f"{bicim.yuzde(gider.onceki)} → {bicim.yuzde(gider.deger)} "
                f"({bicim.puan(gider.degisim)}) — brüt kâr, faaliyet "
                "giderlerinden hızlı büyümüş"
            ),
        ))

    if kaldirac is not None and kaldirac.degisim is not None and kaldirac.degisim <= -0.5:
        s.append(Sinyal(
            baslik="Kaldıraç geriledi",
            yon=Yon.IYI,
            gerekce=(
                f"aktif/özkaynak {bicim.kat(kaldirac.onceki)} → "
                f"{bicim.kat(kaldirac.deger)} — özkaynak bilançodan hızlı büyüdü"
            ),
        ))

    # Musteri varliklarinin bilancoyu ne kadar sisirdigi. Bu oranin buyuk
    # sicramasi, sirketin kendi buyumesinden cok musteri pozisyonlarinin
    # buyumesini gosterir -- aktif buyumesini "sirket buyudu" diye okumak
    # bu yuzden yanlis olur.
    mb = r.bul(OranAdi.MUSTERI_BORCU_PAYI)
    if mb is not None and mb.degisim is not None and abs(mb.degisim) >= 10.0:
        yon = "yükseldi" if mb.degisim > 0 else "geriledi"
        s.append(Sinyal(
            baslik=f"Bilançoda müşteri kaynaklı kalemlerin payı {yon}",
            yon=Yon.DIKKAT,
            gerekce=(
                f"ticari borçların aktife oranı {bicim.yuzde(mb.onceki)} → "
                f"{bicim.yuzde(mb.deger)} ({bicim.puan(mb.degisim)}) — "
                "aktif büyümesinin önemli bölümü müşteri pozisyonlarından "
                "kaynaklanıyor, şirketin kendi sermayesinden değil"
            ),
        ))

    fd = r.bul(OranAdi.FAALIYET_DISI)
    if fd is not None and fd.deger >= 30:
        s.append(Sinyal(
            baslik="Net kârın önemli bölümü esas faaliyetten gelmiyor",
            yon=Yon.DIKKAT,
            gerekce=(
                f"faaliyet dışı net gelir, net kârın {bicim.yuzde(fd.deger)}'ini "
                "oluşturuyor — bu kalem tekrarlanabilir olmayabilir"
            ),
        ))

    if simdi.net_kar is not None and once.net_kar is not None:
        if simdi.net_kar <= 0 < once.net_kar:
            zarar = f"{abs(simdi.net_kar):,.0f}".replace(",", ".")
            s.append(Sinyal(
                baslik="Dönem zararla kapandı",
                yon=Yon.KOTU,
                gerekce=f"önceki dönem kâr açıklanmıştı, bu dönem {zarar} TL zarar",
            ))
        elif once.net_kar <= 0 < simdi.net_kar:
            s.append(Sinyal(
                baslik="Önceki dönem zararıyla karşılaştırma",
                yon=Yon.NOTR,
                gerekce="zarardan kâra geçiş — yüzde değişim hesaplanmadı, yanıltıcı olurdu",
            ))

    return s
