-- UC KATMANI: TEL
--
-- NEDEN VAR
-- ---------
-- Site statik ve yalnizca yeniden kuruldugunda taze icerik tasiyor.
-- Olculdu (2026-09-30): zamanlanmis GitHub kosulari cron'un istedigi
-- ~37 kosunun yalnizca %19'unu teslim ediyor; ardisik kosular
-- arasindaki ortanca boslук ~4 saat, gorulen en buyuk ~7 saat. Yani
-- 14:00'te gelen bir haber okura 18:00'de gorunebiliyordu.
--
-- Bosluğu kapatan mekanizma (nobetci) GitHub'a `repository_dispatch`
-- gonderiyordu ve bunun icin bir JETON gerekiyordu. Jeton olunce
-- tempo tabana dustu. GitHub tarafinda jetonsuz tetik YOK -- tum
-- uclar kimlik istiyor.
--
-- Bu tablo o bagimliligi kaldiriyor: Cloudflare'in KENDI cron'u (on
-- dakikada bir, guvenilir) beslemeyi cekip buraya yaziyor ve sayfa
-- insadan DAHA YENI olan ogeleri buradan gosteriyor. GitHub tumden
-- dursa bile basliklar akmaya devam ediyor.
--
-- NEDEN BASLIK SAKLANIYOR, SAYFA DEGIL
-- ------------------------------------
-- Uc katmani hicbir KONU KARARI vermiyor ve sayfa URETMIYOR. Sayfa
-- uretimi `gundem_yorum.siniflandir`in isi ve orada kalmali. Burasi
-- yalnizca "su an ne oluyor"u tasiyor; islenmis surumu bir sonraki
-- insa getiriyor.
--
-- ATIF SEMA DUZEYINDE ZORUNLU
-- ---------------------------
-- `ticari=True` olan kaynakta sayfada kurum adi VE baglanti
-- gosterilmek zorunda (bkz. haber_botu/kaynak/besleme.py). Bu kural
-- simdiye kadar yalnizca KOD tarafindan tutuluyordu. Burada
-- `CHECK (length(...) > 0)` ile SEMAYA yaziliyor: kunyesi ya da
-- baglantisi olmayan bir satir veritabanina GIREMIYOR.
--
-- Sebep: kod yolu degisir, unutulur, bir dalda atlanir. Semadaki
-- kisit unutulamaz. Lisans yukumlulugu "hatirlanmasi gereken bir
-- sey" olmaktan cikip yapisal hale geliyor.
CREATE TABLE IF NOT EXISTS tel (
  -- Besleme `guid`i; yoksa baglanti adresi. Tekillemeyi bu tasiyor.
  kimlik        TEXT PRIMARY KEY,
  kod           TEXT NOT NULL,              -- besleme kodu (FJUICE)
  kurum         TEXT NOT NULL CHECK (length(kurum) > 0),
  kurum_tam     TEXT NOT NULL CHECK (length(kurum_tam) > 0),
  -- KAYNAGA BAGLANTI. Bos olamaz: atifin yarisi bu.
  adres         TEXT NOT NULL CHECK (length(adres) > 0),
  baslik_kaynak TEXT NOT NULL CHECK (length(baslik_kaynak) > 0),
  -- Makine cevirisi. Bos kalabilir: ceviri ucu cevap vermezse oge
  -- yine gosteriliyor, orijinal basligiyla. Ceviriyi BEKLEMEK,
  -- tazelik ugruna kurulan seyi geciktirmek olurdu.
  baslik_tr     TEXT NOT NULL DEFAULT '',
  konu          TEXT NOT NULL,
  ticari        INTEGER NOT NULL DEFAULT 1,
  tarih         TEXT NOT NULL,              -- ISO 8601, UTC
  eklendi       TEXT NOT NULL               -- ISO 8601, UTC
);

-- Sayfa "en yeniler"i istiyor; tarama degil, sirali okuma olmali.
CREATE INDEX IF NOT EXISTS tel_tarih ON tel(tarih DESC);

-- CEVIRI ONBELLEGI
--
-- Tel her on dakikada bir ayni basliklarin cogunu yeniden goruyor.
-- Onbelleksiz her tur MyMemory kotasini bastan harcardi (gunluk
-- 50.000 kelime) ve kota bitince ceviri sessizce kapanirdi.
--
-- `haber_botu/kaynak/ceviri.py` ayni isi dosya onbellegiyle yapiyor;
-- burasi onun uc karsiligi. Ayni ceviri iki yerde tutuluyor ama
-- KARAR tek yerde degil -- ikisi de ayni ucu cagiriyor ve sonucu
-- saklıyor; ayrisabilecek bir kural yok.
CREATE TABLE IF NOT EXISTS tel_ceviri (
  anahtar TEXT PRIMARY KEY,      -- kaynak metnin sha-256'si
  ceviri  TEXT NOT NULL,
  eklendi TEXT NOT NULL
);
