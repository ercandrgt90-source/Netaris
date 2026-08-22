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

    # --- derecelendirme ve arastirma kuruluslari ---
    #
    # Bunlar veri KAYNAGI degil, GORUS kaynagi. Ayri tutulmalari sitenin
    # temel ayrimidir: TUIK'in yayimladigi TUFE olcumdur, Goldman'in
    # beklentisi gorustur. Sayfada ikisi ayni yerde durmaz.
    #
    # Arsivdeki degerleri "daha once ne demisti" sorusundadir: bir kurumun
    # gecmis tahminleri, bugunku tahmininin agirligini belirler.
    ("MOODYS", "kurum", "Moody's", "Moody's", None, 75,
     "Kredi derecelendirme kuruluşu. Not kararları ülke ve şirket "
     "borçlanma maliyetini etkileyen referanslardan biridir."),
    ("FITCH", "kurum", "Fitch", "Fitch Ratings", None, 75,
     "Kredi derecelendirme kuruluşu."),
    ("SPRATING", "kurum", "S&P Global Ratings", "S&P Global Ratings", None, 75,
     "Kredi derecelendirme kuruluşu."),
    ("GOLDMAN", "kurum", "Goldman Sachs", "Goldman Sachs", None, 70,
     "Yatırım bankası. Makro tahminleri piyasada geniş biçimde izlenir; "
     "yayımladığı beklenti ölçüm değil, kurumun görüşüdür."),
    ("JPMORGAN", "kurum", "JP Morgan", "JPMorgan Chase", None, 70,
     "Yatırım bankası."),
    ("MORGANSTANLEY", "kurum", "Morgan Stanley", "Morgan Stanley", None, 65,
     "Yatırım bankası."),
    ("DEUTSCHE", "kurum", "Deutsche Bank", "Deutsche Bank", None, 60,
     "Yatırım bankası."),
    ("IMF", "kurum", "IMF", "International Monetary Fund", None, 80,
     "Uluslararası Para Fonu. Üye ülkeler için düzenli makro değerlendirme "
     "ve tahmin yayımlar."),
    ("DUNYABANKASI", "kurum", "Dünya Bankası", "World Bank", None, 70,
     "Kalkınma finansmanı kuruluşu; büyüme ve yoksulluk verileri yayımlar."),
    ("OECD", "kurum", "OECD", "OECD", None, 70,
     "Ekonomik İşbirliği ve Kalkınma Örgütü. Üye ülkeler için "
     "karşılaştırmalı istatistik ve tahmin yayımlar."),

    # --- kisiler ---
    # GOREVDEKI BASKAN ONCE. Tanimlar GOREVE bagli oldugu icin gorev
    # degistiginde burasi guncellenmek zorunda; kod bunu anlayamaz.
    # Olculdu -- kullanici sayfada eski baskanin fotografini gordu ve
    # bu kaydin aciklamasi da hala "Fed Başkanı." diyordu.
    ("WARSH", "kisi", "Kevin Warsh", "Kevin Warsh", None, 80,
     "Fed Başkanı."),
    # Tarih YAZILMIYOR: gorev bitis tarihini olcmedik, kendi haber
    # akisimiz yalnizca "artik Warsh" diyor. Olcmedigimizi yazmiyoruz.
    ("POWELL", "kisi", "Jerome Powell", "Jerome Powell", None, 60,
     "Fed'in önceki başkanı."),
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
     "TP.APIFON4", 100, "Bir hafta vadeli repo ihale faiz oranı."),

    # --- makro gostergeler ---
    ("TUFE_TR", "gosterge", "TÜFE", "Türkiye CPI", "TP.TUKFIY2025.GENEL", 100,
     "Tüketici fiyat endeksi. Politika faizi kararlarının, kira ve ücret "
     "yenilemelerinin ve TMS 29 enflasyon muhasebesinin ortak girdisi."),
    ("UFE_TR", "gosterge", "ÜFE", "Türkiye PPI", "TP.TUFE1YI.T1", 80,
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
     "TP.HARICCARIACIK.K1", 85, "Türkiye'nin dış finansman ihtiyacının ana ölçüsü."),
    # Asagidaki ucu ilk tohumda yoktu ve eksikligi olculdu: "Temmuz ayi
    # dis ticaret rakamlari aciklandi" gibi basliklar hicbir varliga
    # baglanmiyordu -- oysa dis ticaret sitenin kendi konu listesinde var.
    ("DIS_TICARET_TR", "gosterge", "Dış ticaret dengesi", "Trade Balance",
     None, 85, "İhracat ile ithalat arasındaki fark. Cari işlemler "
     "dengesinin en büyük bileşeni."),
    ("ISSIZLIK_TR", "gosterge", "İşsizlik oranı", "Türkiye Unemployment",
     "TP.YISGUCU2.G8", 80, "İşgücüne katılanlar içinde iş arayıp bulamayanların oranı. "
     "Geniş tanımlı atıl işgücü oranı ayrı yayımlanır ve daha yüksektir."),

    # --- emtia ---
    ("BRENT", "emtia", "Brent petrol", "Brent Crude", "DCOILBRENTEU", 95,
     "Küresel petrol fiyat referansı."),
    ("WTI", "emtia", "WTI petrol", "WTI Crude", "DCOILWTICO", 80, ""),
    ("XAU", "emtia", "Altın", "Gold", "PAXGUSD", 95,
     "Hem tasarruf aracı hem rezerv varlık. Türkiye'de hanehalkı "
     "tasarrufunun önemli bölümü bu araçta tutulur."),
    ("XAG", "emtia", "Gümüş", "Silver", None, 70,
     "Hem değerli maden hem sanayi girdisi."),
    ("DGAZ", "emtia", "Doğal gaz", "Natural Gas", None, 75, ""),
    ("XCU", "emtia", "Bakır", "Copper", None, 70,
     "Sanayi girdisi olduğu için küresel talebin öncü göstergelerinden "
     "sayılır; elektrifikasyon yatırımları talebi ayrıca artırır."),

    # --- piyasalar ---
    ("BIST100", "piyasa", "BIST 100", "BIST 100", None, 95,
     "Borsa İstanbul ana endeksi."),
    ("SP500", "piyasa", "S&P 500", "S&P 500", "SP500", 85, ""),
    ("NASDAQ", "piyasa", "NASDAQ", "NASDAQ", "NASDAQCOM", 80, ""),
    ("BTC", "piyasa", "Bitcoin", "Bitcoin", "XBTUSD", 80, ""),
    ("ETH", "piyasa", "Ethereum", "Ethereum", "ETHUSD", 65, ""),
    ("USDTRY", "piyasa", "USD/TRY", "USD/TRY", "TP.DK.USD.S.YTL", 100, ""),
    # SERI ECB'YE CEVRILDI, FRED'in DEXUSEU'suna DEGIL.
    #
    # Panel kalemleri bir donem once ECB'ye tasinmisti (bkz.
    # kaynak/ecb_kur.py): FRED'in DEXUSEU serisi ALTI IS GUNU geride
    # geliyor ve "fiyat seridi"nde o kadar gecikme fiyat degil arsiv
    # demek.
    #
    # Ama varligin `seri_kodu` cevrilmemisti. Sonuc, tazelik olcumunde
    # cikti: panel 21 Agustos'u gosterirken VARLIK SAYFASININ GRAFIGI
    # 31 Temmuz'da bitiyordu -- ayni sayfada iki farkli tarih.
    #
    # Bir kaynak degistirilirken ona bagli HER YER taranmali; tek bir
    # tuketici atlandiginda hata sessiz kaliyor cunku iki deger de
    # "gercek", yalnizca ayni gune ait degil.
    ("EURUSD", "piyasa", "EUR/USD", "EUR/USD", "ECB_EURUSD", 75, ""),
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

    # === KURESEL PIYASALAR =============================================
    #
    # NEDEN EKLENDI
    # -------------
    # Olculdu: agda 50 dugum vardi ve FIYATLANAN uclerin neredeyse
    # tamami Turkiye'ydi (USDTRY, BIST100, CDS_TR, TUFE_TR...). DAX,
    # Nikkei, FTSE, EURUSD, Bund, ECB faizi -- HICBIRI YOKTU.
    #
    # Sonuc: bir Alman enflasyon haberinin gidecegi tek yer Turkiye'ydi.
    # Aktarim kanali "Almanya -> ... -> USDTRY" diye kuruluyordu ve
    # okurun asil sorusu ("bu Avrupa'da neyi etkiler") cevapsiz
    # kaliyordu. Kanal fiilen HIC CALISMIYORDU: sifir sayfada
    # gorunuyordu, cunku cogu yabanci varliktan Turkiye ucuna
    # aciklamali bir yol yoktu.
    #
    # Yerel bakis yanlis degil -- Turk okur icin dogru ve gerekli. Ama
    # TEK bakis olmasi, kuresel bir olayi yalnizca bir ulkeye bakan
    # dar bir mercekten anlatmak demekti.
    #
    # --- Euro Bolgesi ---
    ("ECB_FAIZ", "oran", "ECB mevduat faizi", "ECB deposit rate", None, 95,
     "Euro Bölgesi para politikasının çıpası."),
    ("DAX", "endeks", "DAX", "DAX", None, 85,
     "Almanya'nın en büyük 40 şirketini içeren endeks; Avrupa sanayi "
     "görünümünün en çok izlenen göstergelerinden."),
    ("STOXX", "endeks", "Euro Stoxx 50", "Euro Stoxx 50", None, 85, ""),
    ("DE10Y", "oran", "Almanya 10 yıllık tahvil", "German 10Y Bund", None, 90,
     "Euro Bölgesinin risksiz getiri çıpası; diğer üye ülke tahvilleri "
     "buna göre fiyatlanır."),
    # EURUSD BURADA TANIMLI DEGIL: yukarida "piyasa" turuyle zaten
    # var. Ikinci kez eklemek `varlik.kod` benzersizlik kisitini
    # dusuruyordu ve `test_varlik.py` bunu yakaladi.
    ("EA_TUFE", "gosterge", "Euro Bölgesi TÜFE", "Euro area HICP", None, 90, ""),

    # --- Japonya ---
    ("BOJ_FAIZ", "oran", "BoJ politika faizi", "BoJ policy rate", None, 85, ""),
    ("NIKKEI", "endeks", "Nikkei 225", "Nikkei 225", None, 80, ""),
    ("USDJPY", "kur", "USD/JPY", "USD/JPY", None, 85, ""),
    ("JGB", "oran", "Japonya 10 yıllık tahvil", "Japan 10Y JGB", None, 80, ""),

    # --- Birlesik Krallik ---
    ("BOE_FAIZ", "oran", "BoE politika faizi", "BoE bank rate", None, 80, ""),
    ("FTSE", "endeks", "FTSE 100", "FTSE 100", None, 75, ""),
    ("GBPUSD", "kur", "GBP/USD", "GBP/USD", None, 75, ""),

    # --- Cin ---
    ("CN_BUYUME", "gosterge", "Çin büyümesi", "China GDP growth", None, 85,
     "Küresel emtia talebinin en büyük tek belirleyicisi."),
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

    # --- dis ticaret, istihdam, bakir ---
    # Bu bag MUHASEBE, tahmin degil: dis ticaret dengesi cari islemler
    # hesabinin bir kalemidir. `dayanak=yapisal` tam olarak bunu ayirir.
    ("DIS_TICARET_TR", "CARI_TR", "bileseni", "yapisal", 3,
     "Dış ticaret dengesi cari işlemler hesabının en büyük kalemidir; "
     "toplama tanım gereği girer."),
    ("TUIK", "DIS_TICARET_TR", "yayimlar", "yapisal", 3, ""),
    ("TUIK", "ISSIZLIK_TR", "yayimlar", "yapisal", 3, ""),
    ("USDTRY", "DIS_TICARET_TR", "etkiler", "yapisal", 2,
     "Kur, ihracat ve ithalatın TL karşılığını ve göreli fiyatını "
     "değiştirir; miktar tepkisinin hızı sektöre göre farklıdır."),
    ("BRENT", "DIS_TICARET_TR", "etkiler", "yapisal", 3,
     "Enerji ithalat faturası dış ticaret açığının doğrudan kalemi."),
    # Issizlik -> TCMB faizi bagi VERI dayanakli: kanunla verilmis bir
    # cift gorev yok, iliski gozlemden okunuyor. Fed'de durum farkli --
    # istihdam yasal gorevin parcasi, o bag yapisal.
    ("ISSIZLIK_TR", "TCMB_FAIZ", "etkiler", "veri", 1,
     "İşgücü piyasasındaki gevşeme talep baskısının göstergelerinden "
     "biri sayılır; TCMB'nin yasal hedefi ise fiyat istikrarıdır."),
    ("NFP", "FED_FAIZ", "etkiler", "yapisal", 3,
     "İstihdam, Fed'in yasayla tanımlı çift görevinin ayaklarından biri."),
    ("CN", "XCU", "etkiler", "yapisal", 3,
     "Çin küresel bakır talebinin en büyük tek kaynağı."),
    ("XCU", "SEK_ENERJI", "etkiler", "yapisal", 1,
     "Şebeke ve yenilenebilir yatırımlarının girdi maliyeti."),

    # --- derecelendirme ve arastirma ---
    #
    # DAYANAK BURADA "VERI", "YAPISAL" DEGIL. Not indirimi risk primini
    # mekanik olarak yukseltmez; cogu zaman piyasa kararı zaten
    # fiyatlamis olur, bazen tepki ters yonde cikar. Bunu yapisal saymak,
    # olculmemis bir kurali muhasebe kimligi gibi sunmak olurdu.
    ("MOODYS", "CDS_TR", "etkiler", "veri", 2,
     "Not kararları risk primine yansıyabilir; tepkinin yönü ve büyüklüğü "
     "kararın ne kadarının önceden fiyatlandığına bağlıdır."),
    ("FITCH", "CDS_TR", "etkiler", "veri", 2, ""),
    ("SPRATING", "CDS_TR", "etkiler", "veri", 2, ""),
    ("IMF", "TR", "degerlendirir", "kaynak", 2, ""),
    ("OECD", "TR", "degerlendirir", "kaynak", 2, ""),
    ("DUNYABANKASI", "TR", "degerlendirir", "kaynak", 2, ""),

    # === KURESEL AKTARIM KANALLARI =====================================
    #
    # Bu blok, agin YALNIZCA Turkiye'ye bakan yapisini kiriyor. Bir
    # Alman enflasyon haberinin gidecegi tek yer Turkiye'ydi; artik
    # once kendi piyasasina, oradan -- istenirse -- buraya geliyor.
    #
    # KURAL AYNI: hicbir bagda YON yok. "etkiler" var, "yukseltir" yok.

    # --- kurumsal aidiyet ---
    ("ECB", "ECB_FAIZ", "belirler", "yapisal", 3,
     "ECB Yönetim Konseyi mevduat faizini belirler."),

    # --- Euro Bolgesi ic kanallari ---
    ("ECB_FAIZ", "DE10Y", "etkiler", "yapisal", 3,
     "Alman tahvil getirisi, politika faizi beklentisini fiyatlar; "
     "Euro Bölgesinin risksiz getiri çıpası budur."),
    ("ECB_FAIZ", "EURUSD", "etkiler", "yapisal", 3,
     "İki para birimi arasındaki faiz farkı, sermaye akımının "
     "belirleyicilerinden."),
    ("EA_TUFE", "ECB_FAIZ", "etkiler", "yapisal", 3,
     "ECB'nin yasal görevi fiyat istikrarı; enflasyon verisi politika "
     "faizi kararının temel girdisi."),
    ("DE10Y", "DAX", "etkiler", "yapisal", 2,
     "İskonto oranı yükseldiğinde gelecekteki kârların bugünkü değeri "
     "yeniden hesaplanır."),
    ("DE10Y", "STOXX", "etkiler", "yapisal", 2, ""),
    ("EURUSD", "DAX", "etkiler", "yapisal", 2,
     "DAX şirketlerinin gelirlerinin büyük bölümü yurt dışından; "
     "euronun değeri çevrilen kâra doğrudan yazılır."),
    ("DAX", "STOXX", "bileseni", "yapisal", 3,
     "Alman şirketleri Euro Stoxx 50'nin en büyük ağırlığı."),

    # --- ABD -> Euro Bolgesi ---
    ("FED_FAIZ", "ECB_FAIZ", "etkiler", "veri", 1,
     "Merkez bankaları birbirinin kararını dikkate alır; kur kanalı "
     "üzerinden enflasyon görünümü etkilenir."),
    ("US10Y", "DE10Y", "etkiler", "yapisal", 2,
     "Uzun vadeli tahvil getirileri küresel sermaye piyasasında "
     "birbirine bağlı fiyatlanır."),
    ("DXY", "EURUSD", "bileseni", "yapisal", 3,
     "Euro, dolar endeksinin en büyük ağırlıklı bileşeni."),
    ("SP500", "DAX", "etkiler", "veri", 1,
     "Küresel risk iştahı hisse piyasalarında birlikte hareket eder."),
    ("SP500", "STOXX", "etkiler", "veri", 1, ""),

    # --- Japonya ---
    ("BOJ_FAIZ", "JGB", "etkiler", "yapisal", 3,
     "Japonya tahvil getirisi, politika faizi ve getiri eğrisi "
     "kontrolü çerçevesinde fiyatlanır."),
    ("BOJ_FAIZ", "USDJPY", "etkiler", "yapisal", 3,
     "ABD ile Japonya arasındaki faiz farkı, yen üzerindeki en çok "
     "izlenen belirleyici."),
    ("USDJPY", "NIKKEI", "etkiler", "yapisal", 2,
     "Nikkei ağırlıklı olarak ihracatçı şirketlerden oluşur; yenin "
     "değeri çevrilen kâra yazılır."),
    ("FED_FAIZ", "USDJPY", "etkiler", "yapisal", 2, ""),
    ("JGB", "US10Y", "etkiler", "veri", 1,
     "Japon yatırımcı küresel tahvil piyasasının en büyük alıcılarından; "
     "yurt içi getiri yükseldiğinde yurt dışı tahvil talebi değişir."),

    # --- Birlesik Krallik ---
    ("BOE_FAIZ", "GBPUSD", "etkiler", "yapisal", 2, ""),
    ("GBPUSD", "FTSE", "etkiler", "yapisal", 2,
     "FTSE 100 gelirlerinin büyük bölümü yurt dışından; sterlinin "
     "değeri çevrilen kâra yazılır."),
    ("BRENT", "FTSE", "etkiler", "yapisal", 2,
     "Endekste enerji şirketlerinin ağırlığı yüksek."),

    # --- Cin ve emtia ---
    ("CN_BUYUME", "BRENT", "etkiler", "yapisal", 3,
     "Çin, küresel ham petrol ithalatının en büyük tek alıcısı."),
    ("CN_BUYUME", "XCU", "etkiler", "yapisal", 3,
     "Çin küresel bakır talebinin yarısından fazlasını oluşturur."),
    ("CN", "CN_BUYUME", "uyesi", "yapisal", 3, ""),

    # --- kuresel -> Turkiye (mevcut kanallarin devami) ---
    ("EURUSD", "USDTRY", "etkiler", "yapisal", 2,
     "TL sepeti hem dolar hem euro içerir; çapraz kur TL'nin efektif "
     "değerine yazılır."),
    ("EA_TUFE", "DIS_TICARET_TR", "etkiler", "yapisal", 2,
     "Euro Bölgesi Türkiye'nin en büyük ihracat pazarı; oradaki talep "
     "ve fiyat görünümü ihracat gelirine yazılır."),
    ("DAX", "BIST100", "etkiler", "veri", 1,
     "Avrupa risk iştahı gelişmekte olan piyasa akımlarıyla birlikte "
     "hareket eder."),
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
