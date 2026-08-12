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
