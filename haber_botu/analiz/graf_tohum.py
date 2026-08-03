"""Bilgi agi tohumu -- varliklar ve aralarindaki yapisal baglar.

NE OLDUGU
---------
Sitenin asil entelektuel varligi burasi. Haber toplamak herkesin
yapabilecegi bir is; "Fed faizi neyi, hangi mekanizmayla etkiler"
bilgisi ise birikimle olusur.

NEYIN GIRDIGI, NEYIN GIRMEDIGI
------------------------------
GIRER : Yapisal, mekanik, kitaba yazilmis iliskiler. "Turkiye net enerji
        ithalatcisidir, petrol fiyati cari dengeye yazilir" -- bu bir
        tahmin degil, muhasebe.

GIRMEZ: Yon ve buyukluk. "Fed faiz artirirsa altin duser" YANLIS bir
        genellemedir; 2022'de faiz artti altin da yukseldi. Bag "etkiler"
        der, "su yone iter" DEMEZ. Yonu veriden okuruz, kuraldan degil.

`dayanak` alani bunu ayirir:
  yapisal -- muhasebe kimligi ya da tanim geregi dogru
  veri    -- gozlemden cikarilmis, degisebilir
  kaynak  -- bir kurumun kendi aciklamasina dayaniyor

BU DOSYA BUYUYECEK
------------------
Ilk surum kamuya acik, tartismasiz iliskilerle sinirli. Alan bilgisi
(hangi oran hangi sektorde hangi esikte anlamli) buraya eklenecek --
kimsede olmayan katman o.
"""

from __future__ import annotations

#: (kod, tur, ad, ad_en, seri_kodu, onem, aciklama)
#:
#: `kod` DILDEN BAGIMSIZ. Cok dilli yayinda ad degisir, kod degismez;
#: baglar bu yuzden bozulmaz.
VARLIKLAR: tuple[tuple, ...] = (
    # --- kurumlar ---
    ("FED", "kurum", "Fed", "Federal Reserve", None, 100,
     "ABD merkez bankası. Politika faizini belirler, küresel sermayenin "
     "fiyatını etkileyen ana kurum."),
    ("ECB", "kurum", "Avrupa Merkez Bankası", "European Central Bank", None, 90,
     "Avro Bölgesi para politikasını yürütür."),
    ("TCMB", "kurum", "TCMB", "Central Bank of Türkiye", None, 100,
     "Türkiye Cumhuriyet Merkez Bankası. Politika faizi, zorunlu karşılık "
     "ve rezerv yönetiminden sorumlu."),
    ("TUIK", "kurum", "TÜİK", "Turkish Statistical Institute", None, 90,
     "Türkiye İstatistik Kurumu. TÜFE, ÜFE, işsizlik ve büyüme verilerini "
     "yayımlar."),
    ("SPK", "kurum", "SPK", "Capital Markets Board", None, 70,
     "Sermaye Piyasası Kurulu. Halka açık şirketlerin denetimi ve "
     "kamuyu aydınlatma kurallarından sorumlu."),
    ("BDDK", "kurum", "BDDK", "Banking Regulation Agency", None, 70,
     "Bankacılık Düzenleme ve Denetleme Kurumu."),
    ("SEC", "kurum", "SEC", "Securities and Exchange Commission", None, 60,
     "ABD sermaye piyasası düzenleyicisi."),
    ("EIA", "kurum", "EIA", "Energy Information Administration", None, 60,
     "ABD Enerji Bilgi İdaresi. Petrol ve doğal gaz stok verilerini yayımlar."),
    ("OPEC", "kurum", "OPEC", "OPEC", None, 80,
     "Petrol İhraç Eden Ülkeler Örgütü. Üretim kotalarıyla arzı belirler."),

    # --- kisiler ---
    ("POWELL", "kisi", "Jerome Powell", "Jerome Powell", None, 80,
     "Fed Başkanı."),
    ("LAGARDE", "kisi", "Christine Lagarde", "Christine Lagarde", None, 70,
     "ECB Başkanı."),
    ("KARAHAN", "kisi", "Fatih Karahan", "Fatih Karahan", None, 80,
     "TCMB Başkanı."),

    # --- ulkeler / bolgeler ---
    ("TR", "ulke", "Türkiye", "Türkiye", None, 100, ""),
    ("US", "ulke", "ABD", "United States", None, 95, ""),
    ("EA", "ulke", "Avro Bölgesi", "Euro Area", None, 80, ""),
    ("CN", "ulke", "Çin", "China", None, 75, ""),
    ("RU", "ulke", "Rusya", "Russia", None, 60, ""),
    ("IR", "ulke", "İran", "Iran", None, 60, ""),

    # --- politika faizleri ---
    ("FED_FAIZ", "gosterge", "Fed politika faizi", "Fed Funds Rate",
     "DFF", 100, "ABD gecelik politika faizi."),
    ("TCMB_FAIZ", "gosterge", "TCMB politika faizi", "CBRT Policy Rate",
     None, 100, "Bir hafta vadeli repo ihale faiz oranı."),

    # --- makro gostergeler ---
    ("TUFE_TR", "gosterge", "TÜFE", "Türkiye CPI", None, 100,
     "Tüketici fiyat endeksi. Politika faizi kararlarının, kira ve ücret "
     "yenilemelerinin ve TMS 29 enflasyon muhasebesinin ortak girdisi."),
    ("UFE_TR", "gosterge", "ÜFE", "Türkiye PPI", None, 80,
     "Üretici fiyat endeksi. Maliyet tarafındaki baskıyı gösterir."),
    ("CPI_US", "gosterge", "ABD TÜFE", "US CPI", None, 90, ""),
    ("NFP", "gosterge", "Tarım Dışı İstihdam", "Nonfarm Payrolls", None, 85,
     "ABD istihdam verisi. Fed'in çift yönlü görevinin istihdam ayağı."),
    ("US10Y", "gosterge", "ABD 10 yıllık tahvil", "US 10Y Treasury",
     "DGS10", 90, "Küresel risksiz getirinin referansı."),
    ("US2Y", "gosterge", "ABD 2 yıllık tahvil", "US 2Y Treasury",
     "DGS2", 75, ""),
    ("EGRI", "gosterge", "Getiri eğrisi (10Y-2Y)", "Yield Curve",
     "T10Y2Y", 70, "Negatife dönmesi tarihsel olarak resesyon sinyali "
     "sayılmıştır."),
    ("DXY", "gosterge", "Dolar endeksi", "Dollar Index", "DTWEXBGS", 90,
     "Doların bir sepet para birimine karşı değeri."),
    ("VIX", "gosterge", "VIX", "VIX", "VIXCLS", 70,
     "Oynaklık endeksi. Piyasa stresinin ölçüsü."),
    ("CARI_TR", "gosterge", "Cari işlemler dengesi", "Current Account",
     None, 85, "Türkiye'nin dış finansman ihtiyacının ana ölçüsü."),

    # --- emtia ---
    ("BRENT", "emtia", "Brent petrol", "Brent Crude", "DCOILBRENTEU", 95,
     "Küresel petrol fiyat referansı."),
    ("WTI", "emtia", "WTI petrol", "WTI Crude", "DCOILWTICO", 80, ""),
    ("XAU", "emtia", "Altın", "Gold", "XAU", 95,
     "Hem tasarruf aracı hem rezerv varlık. Türkiye'de hanehalkı "
     "tasarrufunun önemli bölümü bu araçta tutulur."),
    ("XAG", "emtia", "Gümüş", "Silver", "XAG", 70,
     "Hem değerli maden hem sanayi girdisi."),
    ("DGAZ", "emtia", "Doğal gaz", "Natural Gas", None, 75, ""),

    # --- piyasalar ---
    ("BIST100", "piyasa", "BIST 100", "BIST 100", None, 95,
     "Borsa İstanbul ana endeksi."),
    ("SP500", "piyasa", "S&P 500", "S&P 500", "SP500", 85, ""),
    ("NASDAQ", "piyasa", "NASDAQ", "NASDAQ", "NASDAQCOM", 80, ""),
    ("BTC", "piyasa", "Bitcoin", "Bitcoin", "XBTUSD", 80, ""),
    ("ETH", "piyasa", "Ethereum", "Ethereum", "ETHUSD", 65, ""),
    ("USDTRY", "piyasa", "USD/TRY", "USD/TRY", None, 100, ""),
    ("EURUSD", "piyasa", "EUR/USD", "EUR/USD", "DEXUSEU", 75, ""),
    ("CDS_TR", "piyasa", "Türkiye CDS", "Türkiye CDS", None, 85,
     "Ülke risk primi. Dış borçlanma maliyetinin göstergesi."),

    # --- sektorler ---
    ("SEK_BANKA", "sektor", "Bankacılık", "Banking", None, 90, ""),
    ("SEK_ENERJI", "sektor", "Enerji", "Energy", None, 85, ""),
    ("SEK_HAVA", "sektor", "Havacılık", "Airlines", None, 70,
     "Yakıt maliyetinin gider içindeki payı yüksek."),
    ("SEK_PERAKENDE", "sektor", "Perakende", "Retail", None, 70, ""),
    ("SEK_OTOMOTIV", "sektor", "Otomotiv", "Automotive", None, 75, ""),
    ("SEK_INSAAT", "sektor", "İnşaat", "Construction", None, 70, ""),
    ("SEK_TURIZM", "sektor", "Turizm", "Tourism", None, 75, ""),
)


#: (kaynak, hedef, tur, dayanak, guc, aciklama)
#:
#: DIKKAT -- hicbir bagda YON yok. "etkiler" var, "yukseltir" yok.
#: "Fed faiz artirirsa altin duser" yanlis bir genellemedir: 2022'de
#: faiz de altin da yukseldi. Yonu veriden okuruz.
BAGLAR: tuple[tuple, ...] = (
    # --- kurumsal aidiyet ---
    ("POWELL", "FED", "baskani", "kaynak", 3, ""),
    ("LAGARDE", "ECB", "baskani", "kaynak", 3, ""),
    ("KARAHAN", "TCMB", "baskani", "kaynak", 3, ""),
    ("FED", "US", "uyesi", "yapisal", 3, ""),
    ("TCMB", "TR", "uyesi", "yapisal", 3, ""),
    ("ECB", "EA", "uyesi", "yapisal", 3, ""),
    ("TUIK", "TR", "uyesi", "yapisal", 3, ""),

    # --- politika araci ---
    ("FED", "FED_FAIZ", "belirler", "yapisal", 3,
     "Fed açık piyasa komitesi politika faizini belirler."),
    ("TCMB", "TCMB_FAIZ", "belirler", "yapisal", 3,
     "Para Politikası Kurulu bir hafta vadeli repo faizini belirler."),
    ("TUIK", "TUFE_TR", "yayimlar", "yapisal", 3, ""),
    ("TUIK", "UFE_TR", "yayimlar", "yapisal", 3, ""),
    ("OPEC", "BRENT", "etkiler", "yapisal", 3,
     "Üretim kotası kararları küresel arzı doğrudan değiştirir."),

    # --- ABD faizinin gecis kanallari ---
    ("FED_FAIZ", "US2Y", "etkiler", "yapisal", 3,
     "Kısa vadeli tahvil getirisi politika faizi beklentisini fiyatlar."),
    ("FED_FAIZ", "US10Y", "etkiler", "yapisal", 2, ""),
    ("FED_FAIZ", "DXY", "etkiler", "yapisal", 3,
     "Faiz farkı, dolara yönelen sermaye akımının belirleyicilerinden."),
    ("US10Y", "CDS_TR", "etkiler", "yapisal", 2,
     "Küresel risksiz getiri yükseldiğinde gelişmekte olan ülke risk "
     "primi de yeniden fiyatlanır."),
    ("US10Y", "BIST100", "etkiler", "veri", 1, ""),
    ("DXY", "XAU", "etkiler", "yapisal", 3,
     "Altın dolar cinsinden fiyatlanır; doların değeri fiyatın "
     "bileşenlerinden biridir."),
    ("DXY", "BRENT", "etkiler", "yapisal", 2, "Petrol dolar cinsinden fiyatlanır."),
    ("CDS_TR", "USDTRY", "etkiler", "yapisal", 2, ""),
    ("CDS_TR", "SEK_BANKA", "etkiler", "yapisal", 2,
     "Dış borçlanma maliyeti banka fonlama maliyetine yansır."),

    # --- Turkiye para politikasi ---
    ("TCMB_FAIZ", "USDTRY", "etkiler", "yapisal", 2,
     "Yurt içi ve yurt dışı faiz farkı, TL varlıklara yönelen akımı etkiler."),
    ("TCMB_FAIZ", "SEK_BANKA", "belirler", "yapisal", 3,
     "Bankaların fonlama maliyetinin çıpası."),
    ("TCMB_FAIZ", "SEK_INSAAT", "etkiler", "yapisal", 2,
     "Konut kredisi faizi talebi belirler."),
    ("TCMB_FAIZ", "BIST100", "etkiler", "yapisal", 2,
     "İskonto oranı değişimi şirket değerlemesine yansır."),
    ("TUFE_TR", "TCMB_FAIZ", "etkiler", "yapisal", 3,
     "Enflasyonun seyri, Para Politikası Kurulu kararına ilişkin "
     "beklentiyi değiştirir."),
    ("UFE_TR", "TUFE_TR", "etkiler", "yapisal", 2,
     "Üretici maliyeti tüketici fiyatına gecikmeli geçer."),

    # --- enerji ve Turkiye ---
    ("BRENT", "CARI_TR", "etkiler", "yapisal", 3,
     "Türkiye net enerji ithalatçısı; enerji faturası cari işlemler "
     "dengesinin en büyük kalemlerinden biri."),
    ("BRENT", "TUFE_TR", "etkiler", "yapisal", 2,
     "Akaryakıt üzerinden tüketici enflasyonuna geçiş kanalı vardır; "
     "hız ve büyüklük vergi yapısına ve kura bağlıdır."),
    ("BRENT", "SEK_HAVA", "etkiler", "yapisal", 3,
     "Yakıt, havayolu gider kaleminin en büyüğü."),
    ("BRENT", "SEK_ENERJI", "etkiler", "yapisal", 3, ""),
    ("BRENT", "SEK_OTOMOTIV", "etkiler", "yapisal", 1, ""),
    ("DGAZ", "CARI_TR", "etkiler", "yapisal", 3, ""),
    ("DGAZ", "SEK_ENERJI", "etkiler", "yapisal", 2, ""),
    ("CARI_TR", "USDTRY", "etkiler", "yapisal", 2,
     "Cari açık, dış finansman ihtiyacı demektir."),

    # --- jeopolitik ---
    ("IR", "BRENT", "etkiler", "yapisal", 3,
     "Hürmüz Boğazı üzerinden geçen arz nedeniyle bölgesel gerilim "
     "petrol fiyatında risk primi oluşturur."),
    ("RU", "DGAZ", "etkiler", "yapisal", 3, ""),
    ("RU", "BRENT", "etkiler", "yapisal", 2, ""),
    ("CN", "BRENT", "etkiler", "yapisal", 2,
     "Dünyanın en büyük ham petrol ithalatçısı; talep tarafının "
     "belirleyicisi."),

    # --- risk ve tasarruf ---
    ("VIX", "XAU", "etkiler", "veri", 1,
     "Piyasa stresi arttığında güvenli liman talebi değişir."),
    ("VIX", "BTC", "etkiler", "veri", 1, ""),
    ("XAU", "XAG", "etkiler", "veri", 2,
     "İki maden büyük ölçüde birlikte hareket eder; gümüşün sanayi "
     "talebi ayrışmaya yol açabilir."),
    ("TUFE_TR", "XAU", "etkiler", "yapisal", 2,
     "Reel getiri hesabında altın, TL mevduatın alternatifidir."),
    ("SP500", "NASDAQ", "etkiler", "veri", 2, ""),
    ("TUFE_TR", "SEK_PERAKENDE", "etkiler", "yapisal", 2, ""),
    ("TUFE_TR", "SEK_INSAAT", "etkiler", "yapisal", 1, ""),
    ("USDTRY", "SEK_TURIZM", "etkiler", "yapisal", 2,
     "Turizm geliri döviz cinsinden; kur, TL karşılığını değiştirir."),
    ("USDTRY", "SEK_OTOMOTIV", "etkiler", "yapisal", 2,
     "Ara malı ithalatı döviz cinsinden fiyatlanır."),
)


def tohumla(b) -> tuple[int, int]:
    """Varlik ve baglari depoya yazar. `beyin` modulunu ice aktarmaz --
    cagrian taraf baglantiyi verir, boylece bu dosya saf veri kalir."""
    import beyin

    v = beyin.varlik_yaz(b, [
        {"kod": k, "tur": t, "ad": a, "ad_en": ae, "seri_kodu": s,
         "onem": o, "aciklama": ac}
        for k, t, a, ae, s, o, ac in VARLIKLAR
    ])
    g = beyin.bag_yaz(b, [
        {"kaynak": k, "hedef": h, "tur": t, "dayanak": d, "guc": gu,
         "aciklama": ac}
        for k, h, t, d, gu, ac in BAGLAR
    ])
    return v, g
