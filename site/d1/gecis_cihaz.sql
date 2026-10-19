-- BILDIRIM CIHAZLARI -- yalnizca yeni tablo.
--
-- `sema.sql` bastan sona calistirilamiyor (icinde bir kez calismis
-- `ALTER TABLE` var), bu yuzden yeni tablolar ayri gecis
-- dosyalarinda. `sema.sql` yine TAM SEMAYI tarif ediyor.
--
-- Uygulama:
--   npx wrangler d1 execute netaris-uyelik --remote --file=./d1/gecis_cihaz.sql
--
-- NOT: worker bu semayi KENDI de kuruyor (`CIHAZ_SEMA`). Gerekce
-- `gecis_tel.sql` yaninda yazili: "adim yesil" ile "goc calisti"
-- ayni sey degil. `site/test_cihaz_sema.js` iki tanimin
-- ayrismamasini zorluyor.


-- CIHAZ JETONU
-- ============
-- Bildirim gonderilecek cihazin adresi. Expo Push jetonu
-- (`ExponentPushToken[...]`) ya da ileride baska bir saglayicinin
-- jetonu.
--
-- NEDEN JETON BIRINCIL ANAHTAR: ayni cihaz yeniden kayit
-- oldugunda yeni satir degil GUNCELLEME olmali. Jeton cihaz basina
-- benzersiz ve uygulama silinip kurulunca degisiyor.
--
-- NEDEN `uye_id` NULL OLABILIR: bildirim uyelik GEREKTIRMIYOR.
-- "Takip ettigim sirket bilanco acikladi" uyelik ister ama "onemli
-- gelisme" istemez. Uyelik zorunlu kilinsaydi, icerigin tamami
-- uyeliksiz okunabilirken bildirimin uyelik istemesi tutarsiz
-- olurdu.
--
-- `ON DELETE SET NULL`: uye hesabini silince cihaz kaydi KALIYOR
-- ama kime ait oldugu dusuyor. Boylece misafir olarak bildirim
-- almaya devam edebiliyor ve kisisel bag kopuyor. (Hesap silme ucu
-- `begeni`, `senaryo` gibi tablolari ACIKCA siliyor; cihaz
-- kasitli olarak oradan HARIC -- bkz. `hesapSil` yanindaki not.)
CREATE TABLE IF NOT EXISTS cihaz (
  jeton       TEXT PRIMARY KEY,
  uye_id      INTEGER REFERENCES uye(id) ON DELETE SET NULL,
  -- "ios" | "android" | "web"
  platform    TEXT NOT NULL DEFAULT '',
  -- Hangi bildirimleri istiyor: JSON nesnesi.
  -- Ornek: {"onemli":true,"bilanco":false,"takvim":true}
  --
  -- NEDEN JSON: tercih kumesi buyuyecek (takip edilen sirket,
  -- esik bildirimi...) ve her yeni tercih icin sutun eklemek,
  -- her seferinde bir goc demek. Sorgu yalnizca "bu tercihi
  -- isteyenler" diye suzuyor; iliskisel derinlik gerekmiyor.
  tercihler   TEXT NOT NULL DEFAULT '{}',
  -- Cihazin dili; ileride cok dilli bildirim icin.
  dil         TEXT NOT NULL DEFAULT 'tr',
  olusma      TEXT NOT NULL,
  -- Her kayit tazelemesinde guncelleniyor. Olu jetonlari
  -- ayiklamak icin: uzun suredir gorulmeyen cihaz silinebilir.
  son_gorulme TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS cihaz_uye ON cihaz(uye_id);
CREATE INDEX IF NOT EXISTS cihaz_gorulme ON cihaz(son_gorulme);


-- GONDERIM IZI
-- ============
-- AYNI SEY IKI KEZ GONDERILMESIN.
--
-- Bildirim hatti her kosuda "yeni olan ne" diye bakiyor. Iz
-- tutulmazsa ayni bilanco her kosuda yeniden duyurulur -- gunde
-- onlarca kez. Bu, kullanicinin bildirimleri tamamen kapatmasinin
-- en hizli yolu.
--
-- `anahtar` olayin kimligi: "bilanco:THYAO:2026-2" gibi.
CREATE TABLE IF NOT EXISTS bildirim_izi (
  anahtar   TEXT PRIMARY KEY,
  tur       TEXT NOT NULL,
  baslik    TEXT NOT NULL DEFAULT '',
  gonderim  TEXT NOT NULL,
  -- Kac cihaza gitti; sifir da gecerli bir sonuc (kimse o turu
  -- istemiyor olabilir) ve "hic denenmedi"den FARKLI.
  cihaz     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS bildirim_izi_an ON bildirim_izi(gonderim DESC);
