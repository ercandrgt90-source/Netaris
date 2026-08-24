-- Netaris uyelik veritabani (Cloudflare D1)
--
-- D1 SQLite'tir; `haber_botu/netaris.db` ile ayni lehce. Depo semasi bu
-- dosyayla bilincli olarak UYUMLU tutuluyor: ileride uye yazilarini
-- yerel depoya almak gerekirse ayni sorgular calisir.
--
-- TASARIM KARARLARI
-- -----------------
-- * Parola ASLA duz metin tutulmaz. `parola_ozet` alani
--   "pbkdf2$<dongu>$<tuz>$<ozet>" bicimindedir; dongu sayisi ozetin
--   ICINDE saklanir ki ileride artirildiginda eski kayitlar dogrulanmaya
--   devam etsin.
-- * Oturum jetonu de OZETLENEREK saklanir. Veritabani sizsa bile
--   jetonlarla oturum acilamaz -- cerezdeki asil jeton burada yok.
-- * Uye yazisi DOGRUDAN yayimlanmaz. `durum` alani sirayla ilerler ve
--   yayin adimi ayri bir surecte (guvenlik taramasi + insan onayi)
--   gerceklesir.

CREATE TABLE IF NOT EXISTS uye (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  eposta            TEXT NOT NULL UNIQUE,
  -- YALNIZCA ISIM. Soyisim ayri sutunda; ikisini tek alanda tutmak
  -- kunye disinda her kullanimi imkansiz kiliyordu (siralama,
  -- hitap, ayni isimli iki uyeyi ayirt etme).
  ad                TEXT NOT NULL,
  soyad             TEXT NOT NULL DEFAULT '',
  -- Kunyede adin altinda gorunur: "Bagimsiz analist" gibi. BOS
  -- OLABILIR -- zorunlu kilmak, uydurma unvan yazmaya davet olurdu.
  unvan             TEXT NOT NULL DEFAULT '',
  -- Kisa ozgecmis. Okur bir yorumu kimin degil, NE SIFATLA
  -- yazdigini bilmek ister.
  hakkinda          TEXT NOT NULL DEFAULT '',
  parola_ozet       TEXT NOT NULL,
  -- beklemede: e-posta dogrulanmadi | etkin | askida
  durum             TEXT NOT NULL DEFAULT 'beklemede',
  -- yazar | yonetici
  rol               TEXT NOT NULL DEFAULT 'yazar',
  -- Google hesabinin kalici kimligi (`sub` savi). E-posta DEGIL:
  -- kisi Google hesabinin e-postasini degistirebiliyor, `sub`
  -- degismiyor. UNIQUE ama NULL olabilir -- parolayla acilmis
  -- hesaplarda bos ve SQLite birden fazla NULL'a izin veriyor.
  google_id         TEXT UNIQUE,
  dogrulama_ozeti   TEXT,
  dogrulama_biter   INTEGER,
  kayit_ani         TEXT NOT NULL,
  son_giris         TEXT
);

CREATE INDEX IF NOT EXISTS uye_durum ON uye(durum);

CREATE TABLE IF NOT EXISTS oturum (
  jeton_ozeti       TEXT PRIMARY KEY,
  uye_id            INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,
  biter             INTEGER NOT NULL,
  olusma            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS oturum_uye ON oturum(uye_id);
CREATE INDEX IF NOT EXISTS oturum_biter ON oturum(biter);

CREATE TABLE IF NOT EXISTS yazi (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  uye_id            INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,
  baslik            TEXT NOT NULL,
  ozet              TEXT NOT NULL DEFAULT '',
  govde             TEXT NOT NULL,
  kategori          TEXT NOT NULL DEFAULT 'Analist Yorumu',
  -- taslak -> incelemede -> onaylandi -> yayimlandi
  --                      -> reddedildi
  durum             TEXT NOT NULL DEFAULT 'taslak',
  ret_nedeni        TEXT,
  -- Yayin hatti guvenlik taramasinin ciktisini buraya yazar
  guvenlik_notu     TEXT,
  slug              TEXT,
  olusma            TEXT NOT NULL,
  guncelleme        TEXT NOT NULL,
  gonderim          TEXT,
  yayin             TEXT
);

CREATE INDEX IF NOT EXISTS yazi_uye ON yazi(uye_id);
CREATE INDEX IF NOT EXISTS yazi_durum ON yazi(durum);

-- Kaba kuvvet denemesini yavaslatir. KV yerine D1: gunde birkac yuz
-- giris denemesi olan bir sitede ayri bir depo acmaya gerek yok.
CREATE TABLE IF NOT EXISTS deneme (
  anahtar           TEXT PRIMARY KEY,   -- "giris:<eposta>" ya da "kayit:<ip>"
  sayi              INTEGER NOT NULL DEFAULT 0,
  sifirlanir        INTEGER NOT NULL
);


-- ---------------------------------------------------------------------
-- SENARYO
--
-- Sitenin temel ayrimi burada somutlasiyor: resmi veri ile kullanici
-- gorusu ayri tablolarda, sayfada ayri bolumlerde ve farkli dille
-- sunuluyor. Yapay zeka bilgiyi getirir, insan fikir uretir.
--
-- NEDEN "KOSUL -> SONUC" IKI AYRI ALAN
-- Serbest metin birakilsaydi "bence altin yukselir" gibi kosulsuz
-- tahminler gelirdi. Iki alan, yazani kosulunu soylemeye ZORLUYOR:
-- neyin gerceklesmesi halinde ne bekliyor. Kosulsuz tahmin
-- degerlendirilemez; kosullu olan degerlendirilebilir.
--
-- NEDEN OLASILIK ALANI YOK
-- Sitenin "hesaplamadigimiz sayiyi olcum gibi sunmayiz" ilkesi burada
-- da gecerli. "%55 olasilikla" yazan bir kullanici da hesaplamiyor.
-- Bunun yerine UFUK var: senaryo ne zamana kadar gecerli. Ufuk dolunca
-- senaryo GERCEKLESTI/GERCEKLESMEDI diye isaretlenebilir -- yani
-- yazarin gecmis isabeti zamanla olculebilir hale geliyor. Olasilik
-- beyani hicbir zaman denetlenemez, ufuklu kosul denetlenebilir.
--
-- Bu tablo bugun kurulmazsa o olcum hic baslamaz.
CREATE TABLE IF NOT EXISTS senaryo (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  uye_id            INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,

  -- Neye baglandigi. `capa_tur`: 'haber' | 'varlik' | 'konu'
  -- `capa`: /haber/<slug>/ ya da 'BRENT' ya da 'Para politikası'
  capa_tur          TEXT NOT NULL DEFAULT 'haber',
  capa              TEXT NOT NULL,
  -- Capanin o anki basligi. Kopya gibi gorunuyor ama gerekli: haber
  -- basligi sonradan duzeltilirse senaryonun hangi baglamda yazildigi
  -- kaybolmasin.
  capa_baslik       TEXT NOT NULL DEFAULT '',

  kosul             TEXT NOT NULL,      -- "Hürmüz Boğazı fiilen kapanırsa"
  sonuc             TEXT NOT NULL,      -- "navlun maliyeti sert artar"
  gerekce           TEXT NOT NULL DEFAULT '',

  -- '1 hafta' | '1 ay' | '3 ay' | '6 ay' | '1 yıl'
  ufuk              TEXT NOT NULL DEFAULT '3 ay',
  ufuk_biter        TEXT,               -- ISO tarih; ufuktan hesaplanir

  -- taslak -> incelemede -> yayimlandi
  --                      -> reddedildi
  durum             TEXT NOT NULL DEFAULT 'taslak',
  ret_nedeni        TEXT,
  guvenlik_notu     TEXT,

  -- Ufuk dolunca isaretlenir: NULL | 'gerceklesti' | 'gerceklesmedi'
  --                                  | 'belirsiz'
  sonuclanma        TEXT,
  sonuclanma_notu   TEXT,

  olusma            TEXT NOT NULL,
  guncelleme        TEXT NOT NULL,
  gonderim          TEXT,
  yayin             TEXT
);

-- ---------------------------------------------------------------------
-- SENARYO OYU
--
-- NEDEN "DEGERLI BULDUM", "KATILIYORUM" DEGIL
-- Katilim oyu sayisi bir OLASILIK gibi okunur: "%70 katildi" yazan bir
-- kutu, hesaplamadigimiz bir olasiligi olcum gibi sunar ve sitenin en
-- temel ilkesini bozar. "Degerli buldum" ise iyi kurulmus senaryoyu one
-- cikarir; bir tahmin uretmez.
--
-- NEDEN OLUMSUZ OY YOK
-- Asagi oy azinlik gorusunu bastirir ve linc araci olur. Yukari oy
-- siralamak icin yeterli: iyi senaryo one cikar, kotu senaryo sessizce
-- geride kalir.
--
-- NEDEN UYELIK SART
-- Anonim oy sayilabilir bir sey degil. Ayni kisi yuz kez oy verebilir
-- ve siralama anlamini kaybeder.
CREATE TABLE IF NOT EXISTS senaryo_oy (
  senaryo_id  INTEGER NOT NULL REFERENCES senaryo(id) ON DELETE CASCADE,
  uye_id      INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,
  an          TEXT NOT NULL,
  PRIMARY KEY (senaryo_id, uye_id)
);

CREATE INDEX IF NOT EXISTS senaryo_oy_senaryo ON senaryo_oy(senaryo_id);

CREATE INDEX IF NOT EXISTS senaryo_uye ON senaryo(uye_id);
CREATE INDEX IF NOT EXISTS senaryo_durum ON senaryo(durum);
-- Haber sayfasi capaya gore soruyor; en sik sorgu bu.
CREATE INDEX IF NOT EXISTS senaryo_capa ON senaryo(capa, durum);
CREATE INDEX IF NOT EXISTS senaryo_ufuk ON senaryo(ufuk_biter, sonuclanma);

-- ---------------------------------------------------------------------
-- OLCULEBILIR TETIKLEYICI (2026-08-22)
--
-- NEDEN GEREKLI
-- `sonuclanma` alani en bastan beri var ve senaryo sayfasinda
-- gosteriliyor -- ama HICBIR SUREC onu yazmiyordu. Yani "ufku dolunca
-- ne oldugu gorunur" vaadi kodda duruyor, uygulamada calismiyordu.
--
-- Sebep: `kosul` serbest metin. "TUFE %30'un altina inerse" cumlesini
-- makine ile olcmek, dogal dil ayristirmasi ister ve yanlis
-- ayristirilan bir kosul YANLIS SONUCLANDIRMA uretir -- ki bu,
-- sonuclandirmamaktan kotudur.
--
-- Cozum: kosulu yazan kisi ISTERSE olculebilir bir tetikleyici de
-- secer. Uc alan yeter: hangi seri, hangi yon, hangi esik.
--
-- ZORUNLU DEGIL, BILINCLI
-- Her senaryo sayisal bir esige indirgenemez ("Hurmuz fiilen
-- kapanirsa"). Tetikleyicisi olmayan senaryo ufku dolunca 'belirsiz'
-- isaretlenir ve bu DURUST bir cevaptir. Zorunlu kilmak, sayisal
-- olmayan gecerli senaryolari disarida birakirdi.
--
-- SICIL BUNUN UZERINE KURULUYOR
-- Sonucu olculemeyen senaryo sonuclanamaz; sonuclanmayan sicil
-- olusturamaz; sicil olmadan kalite katmani kurulamaz. Katman
-- sisteminin butun temeli bu uc sutun.
ALTER TABLE senaryo ADD COLUMN olcut_kod TEXT;      -- gosterge kodu
ALTER TABLE senaryo ADD COLUMN olcut_yon TEXT;      -- 'ustunde' | 'altinda'
ALTER TABLE senaryo ADD COLUMN olcut_esik REAL;     -- esik degeri

-- ---------------------------------------------------------------------
-- CURUTME KOSULU -- "beni ne yanıltır?"
--
-- NEDEN EN ONEMLI ALAN BU
-- -----------------------
-- Bir senaryoyu bir GORUSTEN ayiran tek sey, yazarin kendi kendini
-- yanlislayabilecek gelismeyi ONCEDEN yazmasidir. Onu yazmayan metin
-- her sonucta hakli cikar ve hicbir sey soylemez.
--
-- `senaryo_kapi.yanislanabilir` KOSULUN olculebilirligine bakiyor --
-- gerekli ama yeterli degil. "TUFE %30'un altina inerse" olculebilir
-- bir kosul; ama yazar "peki ne olursa tezim cokerdi" sorusunu
-- cevaplamadan da yazabilir.
--
-- ZORUNLU DEGIL. Zorunlu kilmak, kisa ve gecerli senaryolari
-- disarida birakirdi; bos birakan senaryo yayimlanir ama sayfasinda
-- bu bolum GORUNMEZ -- yani alan dolduran icin gorunur bir fark var.
ALTER TABLE senaryo ADD COLUMN curutme TEXT;

-- KAYNAKLAR -- yazarin dayandigi veri nerede.
--
-- `senaryo_kapi.dogrulanmayan_sayilar` gerekcede gecip sitenin
-- verisinde BULUNMAYAN sayilari isaretliyor ve yazara "kaynagini
-- belirtin" diyor -- ama belirtecegi bir ALAN YOKTU. Denetim bir sey
-- istiyor, arayuz onu vermiyordu.
ALTER TABLE senaryo ADD COLUMN kaynaklar TEXT;

-- ---------------------------------------------------------------------
-- GORUNTULENME VE BEGENI
-- ---------------------------------------------------------------------
-- NEDEN VAR
-- Tasarim taslaginda her kartin altinda goruntulenme ve begeni sayisi
-- duruyor. Site bunlari HIC olcmuyordu; sayfaya uydurma bir sayi
-- basmak ise bu sitede en agir ihlal olurdu ("olculmemis seyi olcum
-- gibi sunma"). Bu yuzden once olcum, sonra gosterim.
--
-- GORUNTULENME KESIN BIR SAYI DEGIL -- ve oyle sunulmuyor.
-- Tarayici tarafinda gunde bir kez sayiliyor (yerel depoda isaret),
-- sunucuda da IP'ye gore degil YOLA gore toplaniyor. Yani bu bir
-- "tekil ziyaretci" olcusu degil, sayfa acilis sayisi. Gizlilik
-- beyaninda da boyle yaziyor ve `beyan_denetimi.py` beyanin gercekle
-- ortustugunu denetliyor.
--
-- NEDEN IP SAKLANMIYOR
-- Saklansa daha iyi bir sayim yapilabilirdi. Saklanmiyor cunku IP
-- kisisel veri ve bir sayacin dogrulugu, okurun izini tutmaya
-- degmez. Bu bir eksiklik degil, bir tercih.
CREATE TABLE IF NOT EXISTS sayac (
  yol           TEXT PRIMARY KEY,
  goruntulenme  INTEGER NOT NULL DEFAULT 0,
  guncelleme    TEXT
);

-- BEGENI UYELIK ISTIYOR.
-- Anonim begeni sayilabilir bir sey degil: ayni kisi yuz kez basar ve
-- sayi anlamini kaybeder. `senaryo_oy` ile ayni gerekce, ayni yapi.
CREATE TABLE IF NOT EXISTS begeni (
  yol     TEXT NOT NULL,
  uye_id  INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,
  an      TEXT NOT NULL,
  PRIMARY KEY (yol, uye_id)
);

CREATE INDEX IF NOT EXISTS begeni_yol ON begeni(yol);
CREATE INDEX IF NOT EXISTS begeni_uye ON begeni(uye_id);
