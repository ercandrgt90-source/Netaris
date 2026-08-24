-- Calisan bir veritabanina uygulanacak DEGISIKLIKLER.
--
-- `sema.sql` sifirdan kurulum icin; bu dosya ise ZATEN VERI OLAN bir
-- veritabanini ilerletmek icin. Ikisi ayri tutuluyor cunku `CREATE
-- TABLE IF NOT EXISTS` var olan bir tabloya yeni sutun EKLEMEZ --
-- sessizce hicbir sey yapar ve eksik sutun ancak ilk sorguda,
-- calisma aninda ortaya cikar.
--
-- Uygulama:
--   npx wrangler d1 execute netaris-uyelik --remote --file=./d1/gocler.sql
--
-- Her ifade TEKRAR CALISTIRILABILIR olmali ya da hatasi zararsiz
-- olmali. D1'de "duplicate column name" hatasi verirse gocun zaten
-- uygulandigi anlasilir.

-- 2026-08-12 · Google ile giris
--
-- Google hesabinin kalici kimligi (`sub` savi). E-POSTA DEGIL: kisi
-- Google hesabinin e-postasini degistirebiliyor, `sub` degismiyor.
-- NULL olabilir -- parolayla acilmis hesaplarda bos; SQLite UNIQUE
-- sutunda birden fazla NULL'a izin veriyor.
ALTER TABLE uye ADD COLUMN google_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uye_google ON uye(google_id);


-- 2026-08-24 · Profil alanlari
--
-- NEDEN AYRI SUTUNLAR, TEK "ad" DEGIL
-- `ad` tek alandi ve hem isim hem soyisim oraya yaziliyordu. Kunye
-- disinda hicbir yerde kullanilamiyordu: "Sayin Durgut" diyemezsiniz,
-- listeyi soyada gore siralayamazsiniz, iki "Mehmet"i ayirt
-- edemezsiniz.
--
-- `ad` ANLAMI DEGISMIYOR ama artik YALNIZCA isim: var olan kayitlarda
-- tam ad yazili kaliyor ve `soyad` bos oldugu icin kunye eskisi gibi
-- gorunmeye devam ediyor. Uye profilini duzenlediginde ayrisiyor.
-- Boylece goc, calisan hicbir sayfayi bozmuyor.
--
-- `unvan` ve `hakkinda` KUNYENIN GUVENILIRLIGI ICIN: okur bir analiz
-- yorumunu kimin yazdigini degil, NE SIFATLA yazdigini bilmek ister.
-- Ikisi de BOS OLABILIR -- zorunlu kilmak, bos alanlari uydurma
-- unvanlarla doldurmaya davet olurdu.
--
-- DEFAULT '' ve NOT NULL: okuma tarafinda `null` kontrolu gerekmesin.
-- SQLite sabit varsayilanla ALTER TABLE'a izin veriyor.
ALTER TABLE uye ADD COLUMN soyad    TEXT NOT NULL DEFAULT '';
ALTER TABLE uye ADD COLUMN unvan    TEXT NOT NULL DEFAULT '';
ALTER TABLE uye ADD COLUMN hakkinda TEXT NOT NULL DEFAULT '';
