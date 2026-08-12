/* One cikan senaryolarin SIRALAMASI -- gercek SQLite ile.
 *
 * NEDEN SINANIYOR
 * ---------------
 * Siralama sessizce yanlis olabilecek bir sey: liste doludur, kartlar
 * duzgundur, yalnizca YANLIS senaryolar ustedir. Kimse fark etmez.
 *
 * Sinanan davranis:
 *   * pencere OY TARIHINE bakiyor, yayin tarihine degil
 *   * pencere disinda kalan eski oy siralamayi belirlemiyor
 *   * pencerede hic oy yoksa tum zamanlara duşuluyor ve bu
 *     `pencere: false` ile BILDIRILIYOR
 *   * oy almamis senaryo listeye girmiyor
 *
 * Worker'in SQL'i buraya kopyalanmiyor -- `worker.js` okunup sorgu
 * oradan cikariliyor, yani test gercek sorguyu sinamis oluyor.
 *
 * Kullanim:  node site/test_one_cikan.js     (sqlite3 varsa)
 */

"use strict";

const fs = require("fs");
const path = require("path");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  const b = JSON.stringify(bulunan);
  const k = JSON.stringify(beklenen);
  if (b === k) { gecti++; console.log("  gecti  " + aciklama); }
  else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + k);
    console.log("         bulunan : " + b);
  }
}

let DatabaseSync;
try {
  ({ DatabaseSync } = require("node:sqlite"));
} catch {
  console.log("\nnode:sqlite yok -- siralama testi atlandi (Node 22+ gerekiyor)");
  process.exit(0);
}

/* worker.js'ten sabitleri okuyoruz ki test ile kod ayrisamasin. */
const kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
const GUN = Number(/ONE_CIKAN_GUN\s*=\s*(\d+)/.exec(kaynak)[1]);
const ADET = Number(/ONE_CIKAN_ADET\s*=\s*(\d+)/.exec(kaynak)[1]);

console.log("\nOne cikan senaryolar -- siralama\n");
esit(GUN, 7, "pencere yedi gun");

const db = new DatabaseSync(":memory:");
db.exec(`
  CREATE TABLE uye (id INTEGER PRIMARY KEY, ad TEXT);
  CREATE TABLE senaryo (id INTEGER PRIMARY KEY, uye_id INTEGER,
    kosul TEXT, sonuc TEXT, capa TEXT, capa_baslik TEXT, ufuk TEXT,
    durum TEXT, yayin TEXT);
  CREATE TABLE senaryo_oy (senaryo_id INTEGER, uye_id INTEGER, an TEXT);
  INSERT INTO uye VALUES (1,'Okur A'),(2,'Okur B'),(3,'Okur C'),(4,'Okur D');
`);

const gunOnce = (n) => new Date(Date.now() - n * 86400000).toISOString();

function senaryo(id, kosul, yayinGun) {
  db.exec(`INSERT INTO senaryo VALUES (${id}, 1, '${kosul}', 'sonuc',
    '', '', '3 ay', 'yayimlandi', '${gunOnce(yayinGun)}')`);
}
function oy(senaryoId, uyeId, gun) {
  db.exec(`INSERT INTO senaryo_oy VALUES (${senaryoId}, ${uyeId},
    '${gunOnce(gun)}')`);
}

// ESKI ama COK oylu: butun oylari pencere disinda.
senaryo(1, "eski-populer", 200);
oy(1, 1, 190); oy(1, 2, 189); oy(1, 3, 188); oy(1, 4, 187);
// YENI ve az oylu ama oylari PENCERE ICINDE.
senaryo(2, "yeni-taze", 2);
oy(2, 1, 1); oy(2, 2, 1);
// ESKI ama yeniden ilgi goren: yayin eski, OY taze.
senaryo(3, "eski-yeniden", 90);
oy(3, 1, 3); oy(3, 2, 2); oy(3, 3, 2);
// Hic oy almamis.
senaryo(4, "oysuz", 1);

const esik = gunOnce(GUN);
const HAFTALIK = "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id AND o.an >= ?)";
const TOPLAM = "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id)";
const alanlar = "SELECT s.id, s.kosul, u.ad AS yazar, " + TOPLAM + " AS oy_toplam";

const pencereSorgu = db.prepare(
  alanlar + ", " + HAFTALIK + " AS oy" +
  " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
  " WHERE s.durum = 'yayimlandi' AND " + HAFTALIK + " > 0" +
  " ORDER BY oy DESC, s.yayin DESC LIMIT ?");

let sonuc = pencereSorgu.all(esik, esik, ADET);

esit(sonuc.map((r) => r.kosul), ["eski-yeniden", "yeni-taze"],
     "pencere OY tarihine bakiyor -- yayin eski ama oyu taze olan basta");
esit(sonuc.some((r) => r.kosul === "eski-populer"), false,
     "oylari pencere disinda kalan senaryo listeye GIRMIYOR");
esit(sonuc.some((r) => r.kosul === "oysuz"), false,
     "oy almamis senaryo listeye girmiyor");
esit(sonuc[0].oy, 3, "gosterilen sayi HAFTALIK oy (siralamayi ureten sayi)");
esit(sonuc[0].oy_toplam, 3, "toplam oy ayri alanda");

// Sessiz hafta: butun oylar pencere disinda kalirsa tum zamanlara dus.
const db2 = new DatabaseSync(":memory:");
db2.exec(`
  CREATE TABLE uye (id INTEGER PRIMARY KEY, ad TEXT);
  CREATE TABLE senaryo (id INTEGER PRIMARY KEY, uye_id INTEGER,
    kosul TEXT, sonuc TEXT, capa TEXT, capa_baslik TEXT, ufuk TEXT,
    durum TEXT, yayin TEXT);
  CREATE TABLE senaryo_oy (senaryo_id INTEGER, uye_id INTEGER, an TEXT);
  INSERT INTO uye VALUES (1,'Okur A');
  INSERT INTO senaryo VALUES (1,1,'yalniz-eski','s','','','3 ay',
    'yayimlandi','${gunOnce(300)}');
  INSERT INTO senaryo_oy VALUES (1,1,'${gunOnce(290)}');
`);
const bos = db2.prepare(
  alanlar + ", " + HAFTALIK + " AS oy" +
  " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
  " WHERE s.durum = 'yayimlandi' AND " + HAFTALIK + " > 0" +
  " ORDER BY oy DESC LIMIT ?").all(esik, esik, ADET);
esit(bos.length, 0, "sessiz haftada pencere sorgusu BOS doner");

const yedek = db2.prepare(
  alanlar + ", " + TOPLAM + " AS oy" +
  " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
  " WHERE s.durum = 'yayimlandi' AND " + TOPLAM + " > 0" +
  " ORDER BY oy DESC LIMIT ?").all(ADET);
esit(yedek.map((r) => r.kosul), ["yalniz-eski"],
     "bos pencerede TUM ZAMANLAR siralamasina duşuluyor");

console.log("");
if (kaldi.length) {
  console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti");
  process.exit(1);
}
console.log("TUM TESTLER GECTI (" + gecti + ")");
