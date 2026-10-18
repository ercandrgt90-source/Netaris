// HESAP SILME -- EKSIK SILINEN TABLO SESSIZ KALIR.
//
// BU DOSYA NEDEN VAR
// ------------------
// Google Play, hesap olusturulabilen her uygulamada UYGULAMA ICINDEN
// erisilebilen bir hesap silme yolu istiyor. Uc eklendi; asil risk
// uygun olmasi degil, EKSIK silmesi.
//
// Yetim satir hicbir hata uretmez: kullanici "hesabim silindi" goruyor,
// begenileri ya da senaryolari veritabaninda duruyor. Kimse fark
// etmez -- ta ki biri sorana kadar.
//
// UC KURAL SINANIYOR:
//
//  1. UYEYE BAGLI HER TABLO ACIKCA SILINIYOR. Semada alti tabloda
//     `ON DELETE CASCADE` yazili ama hicbir yerde
//     `PRAGMA foreign_keys = ON` cagrilmiyor. SQLite'ta yabanci
//     anahtar varsayilan olarak KAPALI. Cascade'e guvenmek,
//     silindigini VARSAYMAK olurdu.
//
//  2. SIRA DOGRU: once cocuklar, sonra uye. Ters sirada yabanci
//     anahtar acikken silme REDDEDILIR.
//
//  3. YENIDEN KIMLIK DOGRULAMA VAR. Calinmis bir oturumla hesap
//     silinememeli.
//
// Semadaki `REFERENCES uye(id)` satirlari OKUNUYOR -- liste burada
// yeniden yazilmiyor. Yarin yeni bir tablo eklenir ve silmeye
// konmazsa, bu sinama kirmizi doner.
//
// AG KULLANILMIYOR, D1 KULLANILMIYOR.

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const KOK = path.resolve(
  import.meta.dirname ?? path.dirname(new URL(import.meta.url).pathname),
);
const S = fs.readFileSync(path.join(KOK, "worker.js"), "utf8");
const D1 = path.join(KOK, "d1");

let gecti = 0;
const dusen = [];

function dogru(kosul, aciklama) {
  if (!kosul) {
    dusen.push(aciklama);
    return;
  }
  gecti += 1;
  console.log(`  gecti  ${aciklama}`);
}

// ISLEVIN GOVDESI, ACIKLAMA BLOGUYLA BIRLIKTE.
//
// Aciklama bloğu `async function` satirindan ONCE geliyor. Yalnizca
// govdeyi almak, "kodda su gerekce yazili mi" turu kontrolleri
// yanlisliklka kirmiziya dondururdu -- ilk yazimda tam bu oldu.
const govde = (() => {
  const i = S.indexOf("async function hesapSil(istek, env, u) {");
  if (i < 0) return null;
  // Aciklama blogunun basi: islevden geriye dogru ilk `/* HESAP`.
  const b = S.lastIndexOf("/* HESAP SILME", i);
  const bas = b >= 0 ? b : i;
  // Islevin sonu: bir sonraki ust duzey `async function`.
  const j = S.indexOf("\nasync function ", i + 10);
  return S.slice(bas, j < 0 ? S.length : j);
})();

/** Yorumlari atilmis worker kaynagi.
 *
 *  "PRAGMA foreign_keys cagriliyor mu" sorusu YORUMDA gecen metinle
 *  cevaplanamaz: bu dosyanin kendi aciklamasi o ifadeyi iceriyor ve
 *  ilk yazimda sinama kendi yorumunu yakalayip kirmiziya dondu.
 *  Soru KODA sorulmali. */
const KOD = S
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/(^|[^:])\/\/.*$/gm, "$1");

console.log("");
console.log("1. UC VAR VE OTURUM KAPISININ ARDINDA");
dogru(govde, "hesapSil bulundu");
const yol = S.indexOf('if (y === "hesap-sil"');
const kapi = S.indexOf('const uye = await uyeBul(istek, env.DB);');
dogru(yol > 0, "hesap-sil yonlendirmesi var");
dogru(kapi > 0 && yol > kapi,
  "yonlendirme OTURUM KAPISININ ARDINDA (kimliksiz silinemiyor)");

console.log("");
console.log("2. UYEYE BAGLI HER TABLO ACIKCA SILINIYOR");
//
// Liste SEMADAN okunuyor. Burada yeniden yazmak, yarin eklenen bir
// tablonun sessizce disarida kalmasi demekti -- ve sinama yine
// yesil gorunurdu.
const semalar = fs.readdirSync(D1)
  .filter((f) => f.endsWith(".sql"))
  .map((f) => fs.readFileSync(path.join(D1, f), "utf8"))
  .join("\n");

// `CREATE TABLE ... ( ... uye_id ... REFERENCES uye(id) ... )`
const tablolar = new Set();
for (const m of semalar.matchAll(
  /CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)\s*\(([\s\S]*?)\n\);/g,
)) {
  if (/REFERENCES\s+uye\s*\(\s*id\s*\)/i.test(m[2])) tablolar.add(m[1]);
}
console.log(`  uyeye bagli tablo: ${[...tablolar].join(", ")}`);
dogru(tablolar.size >= 4, "semadan en az dort bagli tablo okundu");

if (govde) {
  const eksik = [...tablolar].filter(
    (t) => !new RegExp(`DELETE FROM ${t}\\b`).test(govde),
  );
  dogru(
    eksik.length === 0,
    eksik.length
      ? `EKSIK SILINEN TABLO: ${eksik.join(", ")} -- yetim satir kalir`
      : "uyeye bagli her tablodan siliniyor",
  );

  // `uye` tablosunun KENDISI de silinmeli.
  dogru(/DELETE FROM uye\b/.test(govde), "uye kaydinin kendisi siliniyor");

  console.log("");
  console.log("3. SIRA DOGRU: once cocuklar, sonra uye");
  const uyeYeri = govde.search(/DELETE FROM uye\b/);
  const gecSilinen = [...tablolar].filter((t) => {
    const i = govde.search(new RegExp(`DELETE FROM ${t}\\b`));
    return i > uyeYeri;
  });
  dogru(
    gecSilinen.length === 0,
    gecSilinen.length
      ? `uye'den SONRA silinen tablo: ${gecSilinen.join(", ")}`
      : "butun cocuk tablolar uye'den ONCE siliniyor",
  );

  console.log("");
  console.log("4. senaryo_oy IKI YOLDAN TEMIZLENIYOR");
  // Uye hem OY VEREN hem OYU ALINAN olabilir. Yalnizca `uye_id`
  // silinirse, silinen uyenin senaryolarina baskalarinin verdigi
  // oylar yetim kalir.
  dogru(/DELETE FROM senaryo_oy WHERE uye_id/.test(govde),
    "uyenin verdigi oylar siliniyor");
  dogru(/senaryo_oy WHERE senaryo_id IN/.test(govde),
    "uyenin senaryolarina gelen oylar da siliniyor");

  console.log("");
  console.log("5. YENIDEN KIMLIK DOGRULAMA ZORUNLU");
  dogru(/parolaDogrula\(/.test(govde),
    "parolali hesapta parola dogrulaniyor");
  dogru(/SILME_ONAYI/.test(govde),
    "parolasiz (Google) hesapta onay metni isteniyor");
  dogru(/denemeArtir\(/.test(govde),
    "hiz siniri var (calinan oturumla parola denenemesin)");

  console.log("");
  console.log("6. OTURUM CEREZI TEMIZLENIYOR");
  dogru(/cerezSil\(\)/.test(govde),
    "yanitla birlikte cerez siliniyor");

  console.log("");
  console.log("7. CASCADE'E GUVENILMEDIGI BELGELI");
  // Semada CASCADE yazili ama PRAGMA yok; kod bunu BILEREK
  // yapmali, kazara degil.
  //
  // SORU KODA SORULUYOR, yoruma degil: bu dosyanin kendi aciklamasi
  // "PRAGMA foreign_keys" ifadesini iceriyor ve ilk yazimda sinama
  // kendi yorumunu yakalayip kirmiziya dondu.
  const pragma = /PRAGMA\s+foreign_keys/i.test(KOD);
  dogru(!pragma,
    pragma
      ? "worker PRAGMA foreign_keys ACIYOR -- bu sinamanin varsayimi"
        + " gecersiz, silme mantigi gozden gecirilmeli"
      : "worker PRAGMA foreign_keys acmiyor (varsayim dogru)");
  dogru(/CASCADE/i.test(govde),
    "cascade'e neden guvenilmedigi kodun yaninda YAZILI");
}

console.log("");
if (dusen.length) {
  console.error(`DUSTU (${dusen.length}):`);
  for (const d of dusen) console.error(`  - ${d}`);
  process.exit(1);
}
console.log(`TUM TESTLER GECTI (${gecti})`);
