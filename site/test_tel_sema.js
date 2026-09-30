/* Tel semasi IKI YERDE yaziliyor -- ayni kalmak ZORUNDA.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * Sema iki yerde duruyor:
 *
 *   `d1/gecis_tel.sql`  -- insan tarafindan okunan, gerekceli kaynak
 *   `worker.js` TEL_SEMA -- Worker'in KENDI kurdugu surum
 *
 * Ikincisi 2026-09-30'da EKLENDI ve sebebi olculdu: `otomasyon.yml`
 * icindeki "D1 göçü" adimi `conclusion: success` bildirdi ama
 * tablolar kurulmamisti. Sebep adimin `continue-on-error: true`
 * olmasi -- GitHub boyle bir adimi, komut BASARISIZ OLSA DA adim
 * API'sinde `success` olarak bildiriyor. "Adim yesil" ile "goc
 * calisti" ayni sey degil.
 *
 * Worker D1'e BAGLANTI uzerinden eristigi icin kendi tablosunu
 * kurabiliyor; aradaki butun ariza noktalari dusuyor.
 *
 * AMA: ayni semayi iki yerde tutmak, bu depoda defalarca ayrisma
 * uretti (2026-09-30, tema paleti: ayni jetona karar veren dort blok
 * birbirinden ayri dustu). Fark su ki burada ayrisma MEKANIK olarak
 * yakalaniyor: asagidaki sinama iki tanimin ayni tablolari, ayni
 * sutunlari ve ayni kisitlari uretmesini zorluyor.
 *
 * Calistirma:  node site/test_tel_sema.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  const a = JSON.stringify(bulunan), b = JSON.stringify(beklenen);
  if (a === b) { gecti++; console.log("  gecti  " + aciklama); }
  else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + b);
    console.log("         bulunan : " + a);
  }
}

const dogru = (k, a) => esit(Boolean(k), true, a);

/* --- worker.js icindeki TEL_SEMA --- */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));
const ortam = { console: { log() {}, error() {} }, String, Array, JSON };
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);
const TEL_SEMA = vm.runInContext("TEL_SEMA", ortam);

/* --- gecis_tel.sql --- */
const sql = fs.readFileSync(
  path.join(__dirname, "d1", "gecis_tel.sql"), "utf8");

/** SQL'i karsilastirilabilir hale getirir: yorum yok, tek bosluk. */
function sadelestir(s) {
  return s
    .replace(/--[^\n]*/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\s*,\s*/g, ", ")
    .replace(/\(\s+/g, "(")
    .replace(/\s+\)/g, ")")
    .trim();
}

/** Bir CREATE ifadesinden (tur, ad, govde) cikarir. */
function coz(ifade) {
  const t = sadelestir(ifade);
  const m = t.match(
    /^CREATE (TABLE|INDEX) IF NOT EXISTS (\w+)\s*(.*)$/i);
  if (!m) return null;
  return { tur: m[1].toUpperCase(), ad: m[2], govde: m[3].trim() };
}

const sqlIfadeler = sadelestir(sql).split(";")
  .map((x) => x.trim()).filter(Boolean).map(coz).filter(Boolean);
const wkIfadeler = TEL_SEMA.map(coz).filter(Boolean);

console.log("\nIki tanim da okunabiliyor");
dogru(sqlIfadeler.length >= 5, `gecis_tel.sql: ${sqlIfadeler.length} ifade`);
dogru(wkIfadeler.length >= 5, `worker TEL_SEMA: ${wkIfadeler.length} ifade`);

console.log("\nAyni nesneler");
const ad = (x) => `${x.tur} ${x.ad}`;
esit(wkIfadeler.map(ad).sort(), sqlIfadeler.map(ad).sort(),
     "tablo ve indeks listeleri AYNI");

console.log("\nAyni govdeler");
const sqlHarita = new Map(sqlIfadeler.map((x) => [ad(x), x.govde]));
for (const w of wkIfadeler) {
  esit(w.govde, sqlHarita.get(ad(w)), `${ad(w)} govdesi ayni`);
}

/* ATIF KISITLARI SEMADA -- kod yolu degisse bile kunyesiz satir
   veritabanina giremesin. Bu, lisans yukumlulugunun yapisal
   karsiligi ve iki tanimda da BULUNMAK zorunda. */
console.log("\nAtif kisitlari iki tanimda da var");
for (const [etiket, metin] of [["worker", sadelestir(TEL_SEMA.join(";"))],
                               ["sql", sadelestir(sql)]]) {
  for (const sutun of ["kurum", "kurum_tam", "adres", "baslik_kaynak"]) {
    dogru(metin.includes(`CHECK (length(${sutun}) > 0)`),
          `${etiket}: ${sutun} bos olamaz`);
  }
}

if (kaldi.length) {
  console.log("\ntel semasi: " + kaldi.length + " KALDI");
  process.exit(1);
}
console.log("\ntel semasi: " + gecti + " dogrulama gecti");
