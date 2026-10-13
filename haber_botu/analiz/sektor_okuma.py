"""Sektor basina OKUMA KILAVUZU -- bilanco sayfalarina deterministik girer.

    sektor  ->  "bu sektorde hangi kalem neden okunur"

NEDEN MODELDEN DEGIL
--------------------
TERA sayfasini zengin yapan sey model cikarimi DEGILDI. Oradaki
kritik cumle suydu:

    "Sirkete kalan tutar brut kardir: komisyon gelirleri ile net alim
     satim karinin toplami"

Bu bir SEKTOR BILGISI. Araci kurumlarin gelir tablosu her zaman boyle
okunur -- sirkete gore degismez. Yani her sirket icin ayri ayri
uretilmesi gereken bir sey degil; sektor basina BIR KEZ yazilip o
sektordeki butun sirketlere uygulanabilir.

Bunun uc sonucu var:
  1. MARJINAL MALIYET SIFIR -- model cagrilmiyor
  2. TUTARLI -- ayni sektordeki iki sayfa ayni seyi ayni sekilde soyler
  3. KALICI -- gelecek ceyreklerde de calisir, cunku bilgi KODDA

Modelin isi geriye kalan kisim: BU sirkette BU donemde hangi kalem
neden hareket etti. O sirkete ozgu ve ancak orada uretilebilir.

NE YAZILMAZ
-----------
Bu bloklar OKUMA KILAVUZU, yorum degil. Icinde:
  - "iyi", "guclu", "cazip" gibi degerlendirme YOK
  - hangi sirketin daha iyi oldugu YOK
  - tahmin, beklenti, hedef YOK
Yalnizca "bu kalem bu sektorde ne anlama gelir" yaziyor.

SEKTORU OLMAYAN SIRKET
----------------------
Blok yoksa bolum HIC yazilmiyor. Yanlis bir okuma kilavuzu,
kilavuzsuzluktan kotudur -- okur ona guvenip yanlis kalemi okur.
"""

from __future__ import annotations

#: sektor_tr -> (baslik, paragraflar)
#:
#: Basliklar SORU bicimde: okur sayfada gezerken hangi bolumun kendi
#: sorusunu cevapladigini basliktan gorsun.
OKUMA: dict[str, tuple[str, tuple[str, ...]]] = {

    "Finans": (
        "Bankada ve finans kuruluşunda hangi kalem okunur",
        (
            "Bankaların gelir tablosunda **hasılat** kalemi, sanayi "
            "şirketlerindekiyle aynı anlama gelmez. Bir bankanın brüt "
            "faiz geliri, mevduata ödediği faizi içermez; şirkete kalan "
            "tutar **net faiz geliri**dir. Hasılatı tek başına okumak, "
            "maliyeti görmeden ciroya bakmak olur.",

            "Aynı sebeple **aktif toplamı** bankada bir büyüklük "
            "ölçüsüdür, bir performans ölçüsü değil: kredi hacmi "
            "büyüdükçe aktif de büyür. Kârlılık için **özkaynak "
            "kârlılığı** (ROE) okunur.",

            "Aracı kurumlarda tablo bir kez daha farklıdır. Alım satım "
            "işlemlerinin toplam hacmi hasılata yazılabildiği için "
            "hasılat çok büyük görünür; şirkete kalan tutar **brüt "
            "kâr**dır — komisyon gelirleri ile net alım satım kârının "
            "toplamı.",

            "**Net borç** bankada ve finans kuruluşunda anlamlı bir "
            "ölçü değildir: borçlanmak bu iş modelinin kendisidir, bir "
            "yük değil.",
        )),

    "Gayrimenkul": (
        "Gayrimenkul yatırım ortaklığında kâr nereden gelir",
        (
            "GYO'ların kârı iki ayrı kaynaktan gelir ve ikisi aynı şey "
            "değildir: **kira geliri** (nakit yaratan, tekrarlayan) ve "
            "**yeniden değerleme kârı** (portföydeki gayrimenkulün "
            "değerinin yükselmesi). İkincisi nakit üretmez.",

            "Bu yüzden GYO'da net kâr ile **faaliyet nakit akışı** "
            "arasındaki fark, diğer sektörlerdekinden çok daha büyük "
            "olabilir. Değerleme kârı yüksek bir dönemde net kâr "
            "artarken nakit akışı yerinde sayabilir; bu bir tutarsızlık "
            "değil, iki kalemin farklı şeyleri ölçmesidir.",

            "Türkiye'de enflasyon muhasebesi (TMS 29) uygulandığı için "
            "yeniden değerleme etkisi ayrıca büyür. Aşağıdaki değişimler "
            "reeldir; yine de kâr artışının ne kadarının kiradan, ne "
            "kadarının değerlemeden geldiği tabloda ayrışmaz.",
        )),

    "Sanayi": (
        "Sanayi şirketinde hangi kâr ölçüsü neyi gösterir",
        (
            "**Brüt kâr** üretimin kendisinden kalan tutardır: hasılat "
            "eksi satılan malın maliyeti. Brüt marjın değişmesi genelde "
            "hammadde fiyatı, kur ya da fiyatlama gücüyle ilgilidir.",

            "**FAVÖK** ile **net kâr** arasındaki fark üç kalemden "
            "oluşur: amortisman, finansman gideri ve vergi. Sermaye "
            "yoğun bir sanayi şirketinde amortisman büyük olduğu için "
            "FAVÖK yüksek, net kâr düşük görünebilir — bu bir çelişki "
            "değil, yatırımın muhasebeye yansımasıdır.",

            "**Yatırım harcaması** (capex) ile faaliyet nakit akışını "
            "birlikte okumak gerekir: nakit üreten ama üretiminin "
            "tamamını yeniden yatırıma çeviren bir şirketle, üretip "
            "biriktiren şirket aynı net kârı gösterebilir.",
        )),

    "Temel malzeme": (
        "Çevrimsel sektörde tek dönem neyi anlatır, neyi anlatmaz",
        (
            "Çimento, demir-çelik, kimya ve madencilik **çevrimsel** "
            "sektörlerdir: kârlılık emtia fiyatına ve talep dönemine "
            "göre geniş bir bantta gezinir. Tek bir dönemin marjı, "
            "şirketin olağan kârlılığı hakkında sınırlı bilgi verir.",

            "**Brüt marj** bu sektörlerde girdi maliyetine çok "
            "duyarlıdır; enerji ve hammadde fiyatındaki hareket birkaç "
            "çeyrek gecikmeyle tabloya yansıyabilir.",

            "Kapasite yatırımları büyük ve uzun ömürlü olduğu için "
            "**amortisman** yüksektir; FAVÖK ile net kâr arasındaki "
            "makas bu sebeple açıktır.",
        )),

    "Kamu hizmetleri": (
        "Elektrik, gaz ve su dağıtımında tablo nasıl okunur",
        (
            "Bu sektörde gelirin önemli bir kısmı **düzenlenmiş "
            "tarifelere** bağlıdır. Hasılat artışı her zaman talep "
            "artışı anlamına gelmez; tarife güncellemesi de aynı sonucu "
            "verir. İkisi tabloda ayrışmaz.",

            "Şebeke ve santral yatırımları büyük olduğu için borç ve "
            "amortisman yüksektir. **Net borç / özkaynak** oranının "
            "yüksek olması bu iş modelinde olağandır; tek başına bir "
            "kırılganlık göstergesi değildir.",

            "**Faaliyet nakit akışı** bu sektörde net kârdan daha "
            "istikrarlıdır, çünkü amortisman nakit çıkışı değildir.",
        )),

    "Bilişim": (
        "Yazılım ve bilişimde hangi ayrım önemlidir",
        (
            "Yazılım ile donanım/entegrasyon işinin marj yapısı çok "
            "farklıdır: lisans ve abonelik gelirinin brüt marjı yüksek, "
            "donanım satışı ve proje işininki düşüktür. Aynı sektörde "
            "iki şirketin brüt marjı bu yüzden kıyaslanamayacak kadar "
            "ayrışabilir.",

            "Ar-Ge harcaması muhasebeleştirme tercihine göre gidere "
            "yazılabilir ya da aktifleştirilebilir; ikisi net kârı "
            "farklı etkiler. Tablodaki tek bir rakam bu tercihi "
            "göstermez.",

            "Bu sektörde **faaliyet nakit akışı** özellikle önemlidir: "
            "abonelik modelinde nakit tahsilatı gelir kaydından önce "
            "gelebilir.",
        )),

    "Temel tüketim": (
        "Gıda ve perakendede marj neden düşük okunur",
        (
            "Temel tüketimde **brüt marj** yapısal olarak düşüktür; iş "
            "modeli marjdan değil **devir hızından** kâr eder. Düşük "
            "marj burada bir zayıflık göstergesi değildir.",

            "Perakendede mağaza açılışları hasılatı büyütürken kârlılığı "
            "geçici olarak baskılayabilir: yeni mağazanın gideri hemen, "
            "olgun cirosu sonra gelir.",

            "**Cari oran** bu sektörde genelde 1'in altındadır ve bu "
            "olağandır: perakendeci müşteriden peşin tahsil eder, "
            "tedarikçiye vadeli öder. Negatif işletme sermayesi bu iş "
            "modelinin bir özelliğidir.",
        )),

    "İsteğe bağlı tüketim": (
        "Dayanıklı tüketim ve otomotivde neye bakılır",
        (
            "Bu sektörün talebi **çevrimseldir**: kredi faizi, kur ve "
            "hane halkı geliri değiştikçe satışlar hızla değişir. Tek "
            "dönemin büyümesi kalıcı bir eğilim olarak okunmamalıdır.",

            "Otomotiv ve beyaz eşyada **kur etkisi** iki yönlüdür: "
            "ihracat gelirini artırırken ithal girdi maliyetini de "
            "yükseltir. Net etki brüt marjda görünür.",

            "Stok ve alacak devir hızı bu sektörde nakit akışını "
            "belirler; kâr artarken **faaliyet nakit akışının** "
            "gerilemesi çoğu zaman stok birikimine işaret eder.",
        )),

    "Sağlık": (
        "Sağlık ve ilaçta hangi kalem belirleyicidir",
        (
            "İlaç ve sağlık hizmetinde fiyatlar önemli ölçüde "
            "**düzenlemeye ve geri ödeme kurumlarına** bağlıdır; hasılat "
            "artışı serbest fiyatlamadan çok hacim ve kur "
            "değişiminden gelebilir.",

            "Hastane işletmeciliğinde sabit maliyet yüksektir; doluluk "
            "oranındaki küçük bir değişim **faaliyet kârına** büyütülmüş "
            "olarak yansır.",

            "İlaç üreticilerinde Ar-Ge ve ruhsat süreçleri uzun "
            "olduğundan, bir dönemin kârı ile o dönemde yapılan "
            "yatırımın karşılığı aynı tabloda görünmez.",
        )),

    "İletişim": (
        "Telekomünikasyonda borç ve amortisman neden yüksektir",
        (
            "Şebeke yatırımı ve lisans bedelleri peşin ve büyük olduğu "
            "için bu sektörde **borç** ve **amortisman** yapısal olarak "
            "yüksektir. Net borcun özkaynağa oranı, sanayi ortalamasıyla "
            "kıyaslanmamalıdır.",

            "**FAVÖK** bu sektörde en çok izlenen ölçüdür, çünkü "
            "amortismanı dışarıda bırakarak işletme performansını "
            "gösterir. Net kâr ise finansman gideri ve kur farkıyla "
            "dönemden döneme sert değişebilir.",

            "Abonelik modeli sayesinde **faaliyet nakit akışı** net "
            "kârdan daha istikrarlıdır.",
        )),

    "Enerji": (
        "Rafineri ve enerji ticaretinde marj neden dar okunur",
        (
            "Rafinerilerde kârlılık, ham petrol ile ürün fiyatı "
            "arasındaki farktan (**rafineri marjı**) gelir. Hasılat ham "
            "petrol fiyatıyla birlikte büyür ya da küçülür; bu yüzden "
            "hasılattaki değişim tek başına performansı göstermez.",

            "**Brüt marj** bu sektörde yapısal olarak dardır ve "
            "hasılatın büyüklüğüyle kıyaslandığında düşük görünür. "
            "Ölçek büyük, marj ince olduğu için küçük bir marj "
            "değişimi net kârda büyük bir harekete dönüşür.",

            "**Stok değerleme etkisi** önemlidir: petrol fiyatı "
            "değiştiğinde elde tutulan stoğun değeri de değişir ve bu, "
            "faaliyetten bağımsız olarak kârı etkiler.",
        )),
}


#: ALT SEKTORE OZEL kilavuzlar. `OKUMA`dan ONCE bakiliyor.
#:
#: NEDEN AYRI BIR KATMAN
#: ---------------------
#: `ALT_KAPSAM` kapsam disi kalan sirketi kilavuzSUZ birakiyor ve bu
#: yanlis kilavuzdan iyi. Ama bazi alt sektorlerin kendi okuma
#: kurallari var ve onlari yazmak, bos birakmaktan iyi.
#:
#: Spor kulubu bu durumun en nettigi. Olculdu (2026-10-13):
#: İletişim sektorunun `Entertainment` alt sektoru TAM OLARAK dort
#: futbol kulubu (BJKAS, FENER, GSRAY, TSPOR) ve tablolari
#: telekomla hic benzesmiyor -- mali yili 31 Mayis'ta bitiyor,
#: haziran-agustos ceyreginde lig oynanmiyor ve brut marji eksi
#: cikiyor (olculdu: -%76 ile -%101 arasi).
ALT_OKUMA = {
    ("İletişim", "Entertainment"): (
        "Futbol kulübü bilançosunda hangi kalem neyi gösterir",
        (
            "Kulüplerin **mali yılı 31 Mayıs'ta** biter, yani tablo "
            "takvim yılını değil **futbol sezonunu** anlatır. Bu "
            "yüzden çeyrekler takvim çeyreklerine denk gelmez ve "
            "aşağıdaki dönem ay adlarıyla yazılır; takvim çeyreğiyle "
            "kıyaslanmamalıdır.",

            "Sezon takvimi geliri ve gideri farklı çeyreklere "
            "dağıtır: **sezon arası** haziran–ağustos çeyreğine "
            "denk gelir, maç günü geliri durur ama futbolcu "
            "ücretleri ve amortisman sürer. Bu yapı yüzünden "
            "**brüt kârın negatif** çıkması olağandır ve tek başına "
            "bir bozulma işareti sayılmamalıdır. Kıyas, aynı dönemi "
            "bildiren diğer kulüplerle yapılmalı; aynı sektörde yer "
            "alan bir telekom şirketiyle değil.",

            "**Transfer harcaması** peşin ödenip sözleşme süresine "
            "yayılarak amortize edilir. Bu yüzden kadroya yapılan "
            "yatırım gelir tablosunda yıllara dağılmış görünür, "
            "satıştan doğan kazanç ise tek seferde yazılır: iyi bir "
            "transfer döneminin kârı ile sahadaki kadro gücü aynı "
            "tabloda okunmaz.",

            "Zarar eden bir kulüpte **özkaynak kârlılığı** negatif "
            "çıkar ve zarar sürdükçe özkaynak erir. Özkaynağın sıfıra "
            "inmesi ya da negatife geçmesi halinde bu oran "
            "**hesaplanmaz**: negatif bir bölenle üretilen kârlılık "
            "matematiksel olarak mümkün ama anlamsızdır ve ters "
            "işaretiyle yanıltır. O durumda borçluluğu okumak için "
            "net borcun kendisine ve faaliyet nakit akışına bakmak "
            "gerekir.",
        )),
}


#: Kilavuzun GECERLI oldugu alt sektor ONEKLERI. Yalnizca OLCULMUS
#: bir uyusmazlik varsa tanimli; tanimsiz sektorde kilavuz butun alt
#: sektorlere yaziliyor.
#:
#: ONEK, TAM LISTE DEGIL. Defterde alti ayri GYO turu var (REIT -
#: Diversified / Retail / Residential / Hotel & Motel / Specialty /
#: Industrial). Tek tek saymak, kaynak yedinci turu dondurdugu gun
#: onu SESSIZCE kapsam disinda birakirdi; "REIT" oneki birakmaz.
#:
#: NEDEN GEREKLI -- OLCULDU (2026-10-13)
#: Kaynak her sirkete alt sektor de veriyor (defterde 354 sirkette
#: `alt_sektor` dolu) ve kilavuz yalnizca `sektor_tr`ye bakiyordu.
#: Sonuc, canli sayfalarda duran duz yanlis cumleler:
#:
#:   İletişim sektorunde ALTI sirket var:
#:     TTKOM  Telecom Services   <- kilavuz BUNUN icin yazilmis
#:     FENER, BJKAS, TSPOR  Entertainment  (futbol kulubu)
#:     BIGTK, IHYAY         Publishing     (yayincilik)
#:   Kilavuz "abonelik modeli sayesinde faaliyet nakit akisi net
#:   kardan daha istikrarlidir" diyor. Fenerbahce icin bu cumle
#:   yanlis.
#:
#:   Gayrimenkul kilavuzunun basligi "Gayrimenkul yatirim
#:   ortakliginda kar nereden gelir" ve metni GYO'yu anlatiyor. Ama
#:   sektordeki 36 sirketin 12'si GYO DEGIL (Real Estate -
#:   Development / Diversified).
#:
#: Diger dokuz sektorun metni alt sektorlerini kapsayacak genislikte
#: yazilmis; olcum bir uyusmazlik gostermedi, bu yuzden kisitlanmadi.
#: Kisitlamak icin gerekce OLCUM olmali, tahmin degil.
ALT_KAPSAM = {
    "İletişim": ("Telecom Services",),
    "Gayrimenkul": ("REIT",),
}


def kapsamda(sektor_tr: str, alt_sektor: str = "") -> bool:
    """Kilavuz bu alt sektor icin GECERLI mi.

    ALT SEKTOR BILINMIYORSA KISITLAMA YOK. Ayrim yapmanin ispat
    yuku ayrim yapanda; kaynaktan alt sektor gelmemis olmasi,
    kilavuzu susturmak icin yeterli bir gerekce degil.
    """
    onekler = ALT_KAPSAM.get((sektor_tr or "").strip())
    if not onekler:
        return True
    alt = (alt_sektor or "").strip()
    if not alt:
        return True
    return any(alt.startswith(o) for o in onekler)


def blok(sektor_tr: str,
         alt_sektor: str = "") -> tuple[str, tuple[str, ...]] | None:
    """Sektorun okuma kilavuzu. Yoksa ya da kapsam disiysa None.

    None donmesi ONEMLI: cagiran taraf bolumu HIC yazmiyor. Yanlis
    bir okuma kilavuzu, kilavuzsuzluktan kotudur -- okur ona guvenip
    yanlis kalemi okur. Ayni gerekce ALT SEKTOR icin de gecerli:
    bkz. `ALT_KAPSAM`.
    """
    s = (sektor_tr or "").strip()
    alt = (alt_sektor or "").strip()
    # ALT SEKTORE OZEL KILAVUZ ONCE. Sektor genelinden daha
    # keskin oldugu icin; bkz. `ALT_OKUMA`.
    ozel = ALT_OKUMA.get((s, alt))
    if ozel:
        return ozel
    if not kapsamda(s, alt):
        return None
    return OKUMA.get(s)


def markdown(sektor_tr: str, alt_sektor: str = "") -> list[str]:
    """Sayfaya eklenecek satirlar. Kilavuz yoksa BOS liste."""
    b = blok(sektor_tr, alt_sektor)
    if not b:
        return []
    baslik, paragraflar = b
    satir = ["", f"## {baslik}", ""]
    for p in paragraflar:
        satir += [p, ""]
    return satir
