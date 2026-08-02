"""TERA YATIRIM 2026/6 -- KAP finansal tablolarindan.

Rakamlar bin TL cinsinden girilir, kod TL'ye cevirir.

KARSILASTIRMA DONEMI -- her iki tablo da 2025/6
-----------------------------------------------
Ilk denemede bilancoyu 2025/12 (yil sonu) ile karsilastirmistim; finansal
raporlamada bilanco icin standart olan budur. AMA oran hesabinda bu ciddi
bir hataya yol aciyordu:

    ROE(cari)   = 2026/6 kari / 2026/6 ozkaynak
    ROE(onceki) = 2025/6 kari / 2025/12 ozkaynak   <-- ELMA ARMUT

Payin donemi ile paydanin donemi farkli olunca oran karsilastirilamaz hale
geliyor ve "onceki ROE %68,5" gibi anlamsiz bir rakam uretiyordu.

Bu yuzden ORAN karsilastirmasinda her iki tablo da 2025/6 alinir: hem kar
hem ozkaynak ayni tarihten gelir, karsilastirma birebir olur.

NOT: ROE burada ALTI AYLIK kar / donem sonu ozkaynak seklindedir,
yillandirilmamistir. Iki donem de ayni yontemle hesaplandigi icin
karsilastirma gecerlidir, ama seviye yillik ROE olarak okunmamalidir.

DOGRULAMA
---------
Butun aritmetik kimlikler tutuyor (brut kar = satis + maliyet, faaliyet
kari = brut kar - giderler + diger, vergi oncesi = finansman oncesi + net
finansal + parasal, donem kari = vergi oncesi + vergi, aktif = donen +
duran, kaynaklar = kv + uv + ozkaynak).
"""

B = 1_000  # Bin TL -> TL

SIRKET = "TERA YATIRIM MENKUL DEĞERLER A.Ş."
KOD = "TERA"
DONEM = "2026/6"
ONCEKI_DONEM = "2025/6"
BILANCO_KARSILASTIRMA = "2025/6"

SIMDI = dict(
    # Gelir tablosu (6 aylik kumulatif)
    satis_gelirleri=112_716_214 * B,
    brut_kar=25_287_212 * B,
    faaliyet_giderleri=(3_392_670 + 496_443) * B,   # genel yonetim + pazarlama
    faaliyet_kari=23_260_697 * B,
    yatirim_gelirleri_net=(50_315_572 - 53_128) * B,
    parasal_pozisyon=-7_259_948 * B,
    vergi_oncesi_kar=39_651_685 * B,
    vergi=6_609_145 * B,                            # POZITIF = vergi geliri
    net_kar=46_260_830 * B,
    amortisman=88_717 * B,
    faaliyet_nakit_akisi=-4_715_551 * B,
    # Bilanco (2026/6 sonu)
    aktif_toplami=251_825_814 * B,
    ozkaynak=92_356_277 * B,
    nakit=22_509_555 * B,
    ticari_borclar=134_940_730 * B,
)

ONCE = dict(
    satis_gelirleri=59_625_365 * B,
    brut_kar=5_390_971 * B,
    faaliyet_giderleri=(1_279_037 + 180_772) * B,
    faaliyet_kari=4_591_031 * B,
    yatirim_gelirleri_net=(36_357_192 - 13_354_819) * B,
    parasal_pozisyon=-1_587_060 * B,
    vergi_oncesi_kar=20_546_880 * B,
    vergi=3_953_124 * B,
    net_kar=24_500_004 * B,
    amortisman=33_527 * B,
    faaliyet_nakit_akisi=-33_271_540 * B,
    # Bilanco: 2025/6 -- karla ayni tarih (yukaridaki nota bakin)
    aktif_toplami=74_463_783 * B,
    ozkaynak=25_429_445 * B,
    nakit=3_102_318 * B,
    ticari_borclar=5_018_814 * B,
)

#: Yil sonu bilancosu -- yapisal karsilastirma icin, oran hesabinda
#: KULLANILMAZ. Yazida "yil basindan bu yana" demek gerekirse buradan.
YIL_SONU_2025 = dict(
    aktif_toplami=153_912_523 * B,
    ozkaynak=35_743_205 * B,
    nakit=13_304_423 * B,
    ticari_borclar=84_630_178 * B,
)
