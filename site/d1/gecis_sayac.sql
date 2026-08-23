-- GORUNTULENME VE BEGENI -- yalnizca yeni tablolar.
--
-- `sema.sql` bastan sona calistirilamiyor: icinde bir kez calismis
-- `ALTER TABLE ... ADD COLUMN` var ve ikinci calistirmada
-- "duplicate column name" ile duruyor. Yeni tablolar bu yuzden ayri
-- bir gecis dosyasinda. `sema.sql` yine TAM SEMAYI tarif ediyor --
-- sifirdan kurulum oradan yapilir.
CREATE TABLE IF NOT EXISTS sayac (
  yol           TEXT PRIMARY KEY,
  goruntulenme  INTEGER NOT NULL DEFAULT 0,
  guncelleme    TEXT
);

CREATE TABLE IF NOT EXISTS begeni (
  yol     TEXT NOT NULL,
  uye_id  INTEGER NOT NULL REFERENCES uye(id) ON DELETE CASCADE,
  an      TEXT NOT NULL,
  PRIMARY KEY (yol, uye_id)
);

CREATE INDEX IF NOT EXISTS begeni_yol ON begeni(yol);
CREATE INDEX IF NOT EXISTS begeni_uye ON begeni(uye_id);
