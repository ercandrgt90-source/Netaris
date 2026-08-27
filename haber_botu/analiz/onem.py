"""Haber onem puani: hangi haber one cikar, hangisi akista kalir.

NEDEN VAR
---------
Gunde 130 haber geliyor ve hepsi ayni buyuklukte basiliyordu. 50 karti
yan yana dizmek, "hangisi onemli" kararini okura geri devretmek demek --
okur zaten tam olarak bundan kacmak icin geliyor. Bir haber sitesi
"bugun neler oldu" der; arastirma platformu "bugun ne degisti ve bu ne
anlama geliyor" der. Ikincisi tek bir seyle acilir, ellisiyle degil.

PUAN EKRANDA GORUNMEZ
---------------------
Bu, sitenin en eski kuralinin dogrudan uygulamasi: hesaplamadigimizi
olcum gibi sunmayiz. "Onem: 87" yazmak, arkasinda kalibre edilmis bir
model varmis izlenimi verir -- yok. Ayni gerekceyle "Veri Gucu 97"
kaldirilmis, "Guven Skoru %83" hic yazilmamisti.

Ama SIRALAMAK baska bir sey. Puan iceride kaliyor; disariya yalnizca
katman cikiyor (kritik / onemli / normal / akis). Katman bir yargidir ve
sitenin sahiplendigi bir yargidir; sayi ise olculmus bir buyukluk
iddiasidir. Ikisi ayni sey degil.

OLCEMEDIGIMIZ OLCUTLER
----------------------
Onem icin alti olcut istendi. Ucu olculebiliyor, biri kismen, ikisi hic:

  olculuyor   verinin buyuklugu (surpriz)  -> beklenti-gerceklesme farki
  olculuyor   kaynagin guvenilirligi       -> birincil mi, aktarim mi
  olculuyor   kapsam                       -> kac varliga dokunuyor
  kismen      piyasaya etkisi              -> surprizle YAKLASIK olarak;
                                              fiyat hareketini habere
                                              ATFETMEK nedensellik iddiasi
                                              olurdu, onu yapmiyoruz
  YOK         arama hacmi                  -> Google Trends'in acik ve
                                              ticari kullanima uygun ucu
                                              yok
  YOK         kullanici ilgisi             -> sitede olcum (analytics)
                                              kurulu degil; kurulsa bile
                                              yeni sitede veri yok

Olculemeyen ikisi puana SAHTE bir katkiyla girmiyor. Eksik bir suzgec,
uydurulmus bir suzgecten iyidir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

try:  # paket icinden de, dogrudan da calisiyor
    from . import olay as _olay
    from . import veri_basligi as _vb
except ImportError:  # pragma: no cover
    import olay as _olay
    import veri_basligi as _vb


# --------------------------------------------------------------------
# Bilesenler. Toplami 100.
# --------------------------------------------------------------------

#: Konu tabani (0-30).
#:
#: Bir haberin onemi once NE HAKKINDA oldugundan gelir. Faiz karari
#: kotu yazilmis olsa da faiz kararidir; festival haberi mukemmel
#: yazilmis olsa da festival haberidir.
#:
#: Anahtarlar `besleme.KONULAR` ile ayni olmali. `dogrula()` bunu
#: denetliyor -- daha once dort uydurma konu anahtari sessizce
#: varsayilana dusmustu.
#: AGIRLIK YENIDEN DAGITILDI, TAVAN 100'DE KALDI.
#:
#: Bilesenlerin toplami TAM 100 olmali -- puanin "100 uzerinden"
#: okunabilmesi ve esiklerin (85/70/40) anlamli kalmasi buna bagli.
#: Tabani yukseltip tavani da yukseltmek, esikleri indirmenin baska
#: bir yolu olurdu ve olcegi anlamsizlastirirdi.
#:
#: O yuzden agirlik KONUYA KAYDIRILDI:
#:   OLAY_EN_COK     32 -> 24   olay siddeti tek basina belirleyici
#:                              olmasin; hangi KONU oldugu daha cok
#:                              sey soyluyor
#:   SURPRIZ_EN_COK  16 -> 14
#:   KAPSAM_EN_COK   10 ->  8
#: 42 + 24 + 12 + 14 + 8 = 100
#:
#: TABAN PUANLAR YUKSELTILDI (2026-08-21) -- KATMANLAR ERISILEMEZDI.
#:
#: OLCULDU: esikler KRITIK=85, ONEMLI=70 iken gercek verideki EN
#: YUKSEK puan 61, ortanca 26. Yani "kritik" ve "onemli" katmanlarina
#: HICBIR haber ulasmiyordu; son dakika seridi ve uc katmanli
#: hiyerarsi bu yuzden oluydu.
#:
#: Iki secenek vardi: esikleri indirmek ya da puanlamayi yukseltmek.
#: Ikincisi secildi cunku sorun kesme noktasinda degil OLCEKTEYDI --
#: TCMB'nin birincil kaynaktan yayimladigi aylik fiyat raporu 61
#: aliyordu ve o rapor bir finans sitesi icin tanimi geregi ONEMLI.
#:
#: YALNIZCA UST SIRA yukseltildi. Alt siradakiler (konut, tarim,
#: sirket haberleri) DEGISMEDI: amac herkesi yukari cekmek degil,
#: gercekten yuksek etkili konulari esige ulastirmak. Hepsini
#: yukseltmek esigi indirmenin baska bir yolu olurdu.
KONU_TABANI = {
    "Para politikası": 42,
    "Enflasyon": 40,
    "Jeopolitik": 34,
    "Döviz": 30,
    "Enerji": 28,
    "İstihdam ve ücret": 27,
    "Dış ticaret": 24,
    "Bankacılık": 22,
    "Altın ve emtia": 18,
    "Borsa": 17,
    "Vergi ve kamu maliyesi": 17,
    "Kripto varlıklar": 15,
    "Piyasa düzenlemesi": 14,
    "Konut ve kira": 13,
    "Şirket haberleri": 12,
    "Tarım ve gıda": 12,
    "Turizm": 10,
}
KONU_VARSAYILAN = 10

#: Kaynak agirligi (0-12).
#:
#: Birincil kaynak = iddianin SAHIBI. Fed'in kendi bildirisi ile o
#: bildiriyi aktaran akis ayni agirlikta degil.
#:
#: DIKKAT: `kurum` alani bizim hattimizin urunu. FinancialJuice uzerinden
#: gelen bir ABD TUFE haberinde kurum "FinancialJuice" yaziyor ama
#: iddianin sahibi BLS. Bu yuzden veri acikLAMASI olarak COZULEBILEN
#: basliklar birincil sayiliyor (bkz. `_kaynak_puani`) -- yoksa hattimizin
#: sekli, haberin onemini belirlerdi.
BIRINCIL_KAYNAKLAR = frozenset({
    "TCMB", "Fed", "ECB", "TÜİK", "TUIK", "BDDK", "SPK", "KAP",
    "EIA", "SEC", "BLS", "Hazine ve Maliye Bakanlığı", "TÜİK Başkanlığı",
})
KURUMSAL_KAYNAKLAR = frozenset({"AA", "Anadolu Ajansı", "TRT Haber", "Reuters"})

KAYNAK_BIRINCIL = 12
KAYNAK_KURUMSAL = 7
KAYNAK_AKTARIM = 4

#: Surpriz (0-16).
#:
#: "Verinin buyuklugu" olcutunun olculebilir karsiligi. Bir veri, mutlak
#: degeriyle degil BEKLENTIDEN SAPMASIYLA piyasayi hareket ettirir --
#: beklenen enflasyon zaten fiyatlanmistir.
#:
#: Yuzde puanli seriler (TUFE, issizlik) ile duzey serileri (istihdam
#: sayisi, stok) ayri olculuyor: %3,1'e karsi %2,9 beklenti 0,2 PUANLIK
#: bir sapmadir ve buyuktur; 33.429'a karsi 45.849 ise oransal okunur.
SURPRIZ_EN_COK = 14
SURPRIZ_PUAN_TAM = 0.5      # yuzde serilerde "tam surpriz" sayilan sapma
SURPRIZ_ORAN_TAM = 0.10     # duzey serilerde ayni sey (%10 sapma)

#: Kapsam (0-10). Kac varliga dokunuyor.
#: Tek bir sirketi ilgilendiren haber ile faiz-kur-tahvil-banka
#: zincirini birden hareket ettiren haber ayni degil.
KAPSAM_BASINA = 2
KAPSAM_EN_COK = 8

#: Olay siddeti (0-32). `olay.siniflandir` zaten kalibrasyonu yapilmis
#: bir kalip agirligi hesapliyor; sifirdan ikinci bir tablo yazmak onu
#: ikiye bolerdi. Ham siddet ~5-20 arasinda; katsayi onu 0-32'ye tasiyor.
OLAY_KATSAYI = 1.7
OLAY_EN_COK = 24


# --------------------------------------------------------------------
# Katmanlar
# --------------------------------------------------------------------

#: Esikler kullanicinin belirledigi degerler. Puanin kendisi gorunmuyor
#: ama esikler DAVRANIS belirliyor: senaryo acilir mi, son dakika olur mu.
KRITIK = 85
ONEMLI = 70
NORMAL = 40

KATMAN_ADLARI = {
    "kritik": "Kritik",
    "onemli": "Önemli",
    "normal": "Normal",
    "akis": "Akış",
}

#: Bu olay turu, surpriz olmasa bile kritiktir.
#:
#: BU BIR OLCUM DEGIL, EDITORYAL KURALDIR. Faiz karari beklendigi gibi
#: ciksa bile gunun en onemli olayidir -- cunku "degismedi" bilgisi de
#: bir karardir ve piyasa onu fiyatlar.
#:
#: LISTE DARALTILDI. Once {"faiz", "enflasyon", "istihdam"} idi ve
#: `--onem` dokumu sunu gosterdi: en yuksek sekiz haberin YEDISI tabanla
#: 85'e cikiyordu. "Issizlik orani: %7,40" gibi rutin aylik bir yayin
#: da, FOMC bildirisi de ayni katmandaydi. Taban o haliyle puani
#: DESTEKLEMIYOR, puanin YERINE geciyordu -- ve her sey kritik olunca
#: hicbir sey kritik olmaz. Bu tam olarak "her haber son dakika
#: gorunuyor" sorununun baska kapidan donusuydu.
#:
#: Enflasyon ve istihdam verisi artik puanini KENDI topluyor: konu
#: tabani + olay siddeti + birincil kaynak + surpriz. Boylece beklentiyi
#: sasirtan bir TUFE kritik olur, sasirtmayan bir issizlik orani olmaz
#: -- aradaki farki zaten olcebiliyoruz.
KRITIK_OLAYLAR = frozenset({"faiz"})

#: Jeopolitik ve arz olaylari icin taban, kaliplarin gucune bagli:
#: "Hurmuz Bogazi kapatildi" kritiktir, "yaptirim karari" degil.
KRITIK_SIDDET = 14


@dataclass(frozen=True)
class Onem:
    puan: int
    katman: str
    olay_turu: str = ""
    #: Puanin nereden geldigi. Ekrana BASILMIYOR; `--onem` dokumu ve
    #: testler icin. Puani gormeden kalibre etmek imkansiz olurdu.
    bilesenler: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    taban_uygulandi: bool = False

    @property
    def kritik(self) -> bool:
        return self.katman == "kritik"

    @property
    def one_cikar(self) -> bool:
        """Katman 2'ye ("Bugunun onemli gelismeleri") girer mi."""
        return self.katman in ("kritik", "onemli")

    @property
    def ad(self) -> str:
        return KATMAN_ADLARI.get(self.katman, self.katman)


def _kaynak_puani(kurum: str, veri_mi: bool) -> int:
    if veri_mi or kurum in BIRINCIL_KAYNAKLAR:
        return KAYNAK_BIRINCIL
    if kurum in KURUMSAL_KAYNAKLAR:
        return KAYNAK_KURUMSAL
    return KAYNAK_AKTARIM


def _surpriz_puani(v) -> int:
    """Beklentiden sapma -> 0..16.

    Beklenti yoksa ONCEKI donemle karsilastiriliyor: "beklenti yoktu"
    demek "hicbir sey olmadi" demek degil. Ikisi de yoksa 0.
    """
    if v is None or v.gelen is None:
        return 0

    olcut = v.beklenti if v.beklenti is not None else v.onceki
    if olcut is None:
        return 0

    sapma = abs(v.gelen - olcut)
    if v.birim == "%":
        oran = sapma / SURPRIZ_PUAN_TAM
    else:
        taban = abs(olcut)
        if taban < 1e-9:
            return 0
        oran = (sapma / taban) / SURPRIZ_ORAN_TAM

    pay = min(oran, 1.0)

    # Beklentisi olan veri, beklentisi olmayanla ayni olcekte
    # degerlendirilmemeli: "beklenti tutmadi" ile "gecen aydan farkli"
    # ayni bilgi degil. Beklentisizde katki yariya iniyor.
    #
    # Yarilama TAVANDAN SONRA: once yapilsaydi buyuk bir oransal degisim
    # yarilandiktan sonra da tavani asar ve yarilama hicbir ise yaramazdi
    # (Challenger verisi tam olarak boyle davraniyordu).
    if v.beklenti is None:
        pay *= 0.5

    return int(round(pay * SURPRIZ_EN_COK))


def puanla(
    baslik: str,
    baslik_kaynak: str = "",
    konu: str = "",
    kurum: str = "",
    varlik_sayisi: int = 0,
    veri_mi: bool = False,
    yayilim: int = 1,
) -> Onem:
    """Bir haberin onem puani ve katmani.

    `baslik_kaynak` cevrilmemis ozgun baslik: veri basliklarindaki
    "Actual / Forecast / Previous" yapisi yalnizca orada duruyor.
    `veri_mi` haberin bizim veri hattimizdan gelip gelmedigi.
    """
    bilesenler: list[tuple[str, int]] = []

    tabani = KONU_TABANI.get(konu, KONU_VARSAYILAN)
    bilesenler.append(("konu", tabani))

    o = _olay.siniflandir(baslik_kaynak or baslik, kurum, yayilim)
    if o is None and baslik_kaynak:
        # Cevrilmis baslikta yakalanan kalip, ozgununde yakalanmayabilir
        # (ve tersi). Ikisini de deniyoruz -- kalip tablosu hem Turkce
        # hem Ingilizce kalip tasiyor.
        o = _olay.siniflandir(baslik, kurum, yayilim)
    olay_puani = min(int(round((o.siddet if o else 0) * OLAY_KATSAYI)),
                     OLAY_EN_COK)
    bilesenler.append(("olay", olay_puani))

    kaynak = _kaynak_puani(kurum, veri_mi)
    bilesenler.append(("kaynak", kaynak))

    v = _vb.coz(baslik_kaynak) if baslik_kaynak else None
    surpriz = _surpriz_puani(v)
    bilesenler.append(("surpriz", surpriz))

    kapsam = min(max(varlik_sayisi, 0) * KAPSAM_BASINA, KAPSAM_EN_COK)
    bilesenler.append(("kapsam", kapsam))

    puan = min(sum(p for _, p in bilesenler), 100)

    taban = False
    if o is not None:
        guclu_kaynak = kaynak >= KAYNAK_BIRINCIL
        if o.tur in KRITIK_OLAYLAR and guclu_kaynak and puan < KRITIK:
            puan, taban = KRITIK, True
        elif o.siddet >= KRITIK_SIDDET and puan < KRITIK:
            puan, taban = KRITIK, True

    if puan >= KRITIK:
        katman = "kritik"
    elif puan >= ONEMLI:
        katman = "onemli"
    elif puan >= NORMAL:
        katman = "normal"
    else:
        katman = "akis"

    return Onem(puan=puan, katman=katman, olay_turu=(o.tur if o else ""),
                bilesenler=tuple(bilesenler), taban_uygulandi=taban)


def dogrula() -> list[str]:
    """`KONU_TABANI` anahtarlarindan besleme listesinde olmayanlar.

    Uydurma konu anahtari SESSIZCE varsayilana duser ve bir daha fark
    edilmez -- daha once `BULGU_KONULARI`'nda dort tane boyle anahtar
    cikmisti. Testte cagriliyor.
    """
    try:
        from besleme import KONU_ISARETLERI, VERI_KONULARI
    except ImportError:
        try:
            from ..kaynak.besleme import KONU_ISARETLERI, VERI_KONULARI
        except ImportError:
            return []
    # KONU_ISARETLERI: (konu, isaretler) -- konu BASTA
    # VERI_KONULARI:   (isaretler, konu) -- konu SONDA
    adlar = {k for k, _ in KONU_ISARETLERI} | {k for _, k in VERI_KONULARI}
    return sorted(k for k in KONU_TABANI if k not in adlar)


# --------------------------------------------------------------------
# Katman 2 secimi
# --------------------------------------------------------------------

#: "Bugunun onemli gelismeleri" kac kalem olsun.
#: Alt sinir bos bolume, ust sinir yeniden haber listesine karsi.
EN_AZ_SECIM = 8
EN_COK_SECIM = 15

#: Ayni konudan en fazla kac kalem.
#:
#: Bir olay cok sayida FARKLI haber uretiyor. Hurmuz Bogazi gelismesinde
#: dort ayri baslik one cikan listeye girdi:
#:
#:   Kuresel piyasalarda Hurmuz sorulari
#:   Iran'a Hurmuz Bogazi'nda kontrol yetkisi verecek anlasma mi
#:   Trump Iran gorusmelerinin iyi gittigini soyledi
#:   Iran, Hurmuz Bogazi deniz yolu konusunda Umman ile anlasti
#:
#: Bunlar tekrar DEGIL -- gercekten farkli gelismeler ve dordunu de
#: "ayni haber" ilan etmek yanlis olurdu. Sorun tekrar degil DENGE:
#: on uc kalemlik bir bolumun dordunu tek konu aliyor.
#:
#: Bu yuzden kural bir tekilleme degil, bir CESITLILIK kurali. Sinira
#: takilan haber siliniyor degil: canli akista ve kendi konusunun
#: sayfasinda duruyor.
KONU_BASINA_EN_COK = 3


#: Kelime ortakligi esigi: neredeyse ayni cumlenin iki yazimi.
#:
#: KELIME ORTAKLIGI TEK BASINA YETMIYOR ve bu olculdu. Daly'nin tek
#: konusmasindan uretilen dort baslik %33 ortakliga sahipti; ayni
#: konudaki FARKLI iki TCMB haberi %25'e. Aradaki bosluk, esigin guvenle
#: konulamayacagi kadar dar -- cunku o dort baslik gercekten FARKLI
#: seyler soyluyor, sadece ayni konusmadan geliyorlar.
BENZERLIK_ESIGI = 0.6

#: Asil sinyal: ORTAK ONEK.
#:
#: Aktarim akislari tek bir konusmayi "Fed'den Daly: ..." kalibiyla
#: parcaliyor. Onek, haberin hangi AKISA ait oldugunu soyluyor ve
#: cumlelerin ne kadar farkli oldugundan bagimsiz.
#:
#: Kural bilerek genis: ayni onekten en fazla BIR kalem one cikan
#: listeye giriyor. Iki gercekten farkli TCMB duyurusu da birlesebilir
#: -- ama "bugunun en onemlileri" bolumunun isi cesitlilik, ve elenen
#: haber canli akista duruyor. Yanlis yon, tekrar yonunden iyidir.
ONEK_EN_UZUN = 40
ONEK_EN_KISA = 4

_GOVDE_UZUNLUK = 5


def _onek(baslik: str) -> str:
    """Basligin ":" oncesi akis oneki. Yoksa bos.

    Rakam iceren onek KABUL EDILMIYOR: "TÜFE %31,75: ..." gibi
    basliklarda onek verinin kendisini tasir ve iki farkli ay ayni
    haber sayilirdi.
    """
    bas = baslik.split(":", 1)[0].strip()
    if not (ONEK_EN_KISA <= len(bas) <= ONEK_EN_UZUN):
        return ""
    if any(c.isdigit() for c in bas):
        return ""
    # TURKCE EK KESILIYOR.
    #
    # Olculdu (2026-08-27, canli akis): ayni kisinin ayni konusmasi
    # IKI AYRI kume sayiliyordu --
    #
    #     "Fed'den Hammack: ..."   4 baslik
    #     "Fed'in Hammack'i: ..."  4 baslik
    #
    # Kaynak basligi ayni kalipta ("Fed's Hammack"); ceviri, cumleye
    # gore farkli ek uretiyor. Ek dilbilgisi, kimlik degil -- kesince
    # ikisi ayni anahtara duşuyor.
    #
    # YALNIZCA KESME ISARETI SONRASI atiliyor, son kelime DEGIL:
    # "Kanada Cari Hesabi" -> "hesabi" olsaydi "ABD Cari Hesabi" ile
    # birlesirdi ve iki ayri ulkenin verisi tek haber sayilirdi.
    bas = " ".join(k.split("'")[0] for k in bas.split())
    return _olay.katla(bas)


def _imza(baslik: str) -> frozenset[str]:
    """Basligin govde imzasi. Ekleri atarak karsilastiriyoruz.

    Turkce'de ayni kok cok farkli eklerle gelir ("enflasyonun",
    "enflasyona", "enflasyondaki"); tam kelime karsilastirmasi bu
    uclunun uc AYRI kelime oldugunu soylerdi.
    """
    ascii_ = _olay.katla(baslik)
    kelimeler = re.findall(r"[a-z0-9]{4,}", ascii_)
    return frozenset(k[:_GOVDE_UZUNLUK] for k in kelimeler)


def benzer(a: str, b: str) -> bool:
    """Iki baslik one cikan listede AYNI YERI mi doldurur.

    Iki yoldan biri yeter:
      1. ayni akis oneki  ("Fed'den Daly: ...")
      2. yuksek kelime ortakligi (ayni cumlenin iki yazimi)

    Ortaklik KUCUK kumeye orantilaniyor. Buyuk kumeye orantilansaydi,
    uzun bir baslik ile onun kisa ozeti "farkli" cikardi -- oysa
    aktarim akislarinda tam olarak bu cift sik gorulur.
    """
    oa, ob = _onek(a), _onek(b)
    if oa and oa == ob:
        return True

    ia, ib = _imza(a), _imza(b)
    if not ia or not ib:
        return False
    return len(ia & ib) / min(len(ia), len(ib)) >= BENZERLIK_ESIGI


def tekille(puanli, anahtar=None):
    """Ayni gelismeyi anlatan basliklardan EN YUKSEK PUANLIYI birak.

    Iki eleme yolu var:

      baslik  -- ortak onek ya da yuksek kelime ortakligi (bkz.
                 `benzer`). Aktarim akislari tek bir konusmayi dort
                 ayri baslik olarak veriyor.

      anahtar -- cagiranin verdigi KUME anahtari. Baslikten
                 okunamayan gruplari birlestirmek icin: ayni gun
                 yayimlanan TUFE / Yi-UFE / cekirdek enflasyon /
                 hanehalki beklentisi dort AYRI seri ama TEK
                 enflasyon hikayesi ve basliklari birbirine hic
                 benzemiyor. Anahtar bos donerse eleme yapilmaz.

    Elenen haber KAYBOLMUYOR -- canli akista ve haberin kendi sayfasinin
    "ayni konuda son gelismeler" bolumunde duruyor. Burada yapilan sey
    silmek degil, one cikan listede yer israfini onlemek.
    """
    tutulan: list = []
    kumeler: set = set()
    for o, h in sorted(puanli, key=lambda t: -t[0].puan):
        if anahtar is not None:
            k = anahtar(h)
            if k:
                if k in kumeler:
                    continue
                kumeler.add(k)
        b = h.get("baslik", "") if isinstance(h, dict) else str(h)
        if any(benzer(b, t[1].get("baslik", "") if isinstance(t[1], dict)
                      else str(t[1])) for t in tutulan):
            continue
        tutulan.append((o, h))
    return tutulan


def sec(puanli, en_az: int = EN_AZ_SECIM, en_cok: int = EN_COK_SECIM,
        anahtar=None):
    """Katman 2'ye girecek haberleri sec.

    `puanli`: (Onem, haber) ciftleri.

    NEDEN SABIT ESIK DEGIL
    ----------------------
    "Puani 70'in ustunde olanlar" kurali, yavas bir gunde bolumu tek
    kaleme dusurur, Fed gununde yirmiye cikarir. Ikisi de kotu: biri
    sayfayi bos gosterir, digeri bolumun anlamini -- SECIM olmasini --
    yok eder.

    Bunun yerine puana gore SIRALANIP tepeden en cok `en_cok` kalem
    aliniyor. Bolumun adi zaten mutlak bir esik iddia etmiyor: "bugunun
    en onemlileri" gorece bir ifadedir ve bu liste tam olarak odur.

    Yine de `NORMAL` esiginin altina inilmiyor -- listeyi doldurmak icin
    onemsiz haber koymak, secimi yapmamakla ayni sey olurdu. Bu yuzden
    alt sinir bir GARANTI DEGIL: elde yeterli haber yoksa bolum kisa
    kalir.

    Tekrar elemesi ONCE yapiliyor: eleme sonradan yapilsaydi, ayni
    olayin dort basligi once listeyi doldurur, sonra elenir ve geriye
    dort bos yer kalirdi.
    """
    uygun = tekille([(o, h) for o, h in puanli if o.puan >= NORMAL],
                    anahtar=anahtar)

    # CESITLILIK: ayni konudan en fazla `KONU_BASINA_EN_COK` kalem.
    # Sinira takilanlar TAMAMEN ATILMIYOR, sona aliniyor -- boylece
    # elde baska konu kalmadiginda bolum yine dolabiliyor.
    sayac: dict = {}
    onde, arkada = [], []
    for o, h in uygun:
        k = h.get("konu", "") if isinstance(h, dict) else ""
        sayac[k] = sayac.get(k, 0) + 1
        (onde if sayac[k] <= KONU_BASINA_EN_COK else arkada).append((o, h))
    uygun = onde + arkada

    if len(uygun) > en_cok:
        return uygun[:en_cok]
    return uygun[:max(en_az, len(uygun))]
