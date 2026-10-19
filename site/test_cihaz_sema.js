/* Cihaz semasi IKI YERDE yaziliyor -- ayni kalmak ZORUNDA.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * `test_tel_sema.js` ile ayni gerekce: sema iki yerde duruyor,
 *
 *   `d1/gecis_cihaz.sql`   -- insan tarafindan okunan, gerekceli
 *   `worker.js` CIHAZ_SEMA -- Worker'in KENDI kurdugu surum
 *
 * ve ayni semayi iki yerde tutmak bu depoda defalarca ayrisma
 * uretti. Fark su ki burada ayrisma MEKANIK olarak yakalaniyor.
 *
 * AYRICA UC DAVRANIS KURALI SINANIYOR -- hepsi bildirimin
 * kotuye kullanilmamasi icin:
 *
 *  1. Cihaz jetonu BIRINCIL ANAHTAR. Olmazsa ayni cihaz her
 *     kayitta yeni satir acar ve kullanici ayni bildirimi
 *     onlarca kez alir -- bildirimleri tamamen kapatmanin en
 *     hizli yolu.
 *  2. `uye_id` NULL OLABILIR. Icerigin tamami uyeliksiz
 *     okunabiliyor; "onemli gelisme" bildirimi icin uyelik
 *     istemek tutarsiz olurdu.
 *  3. `bildirim_izi.anahtar` BIRINCIL ANAHTAR. Iz tutulmazsa ayni
 *     bilanco her kosuda yeniden duyurulur.
 *
 * Calistirma:  node site/test_cihaz_sema.js
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

/* --- worker.js icindeki CIHAZ_SEMA --- */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));
const ortam = { console: { log() {}, error() {} }, String, Array, JSON };
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);
const CIHAZ_SEMA = vm.runInContext("CIHAZ_SEMA", ortam);
const BILDIRIM_TURLERI = vm.runInContext("BILDIRIM_TURLERI", ortam);

/* --- gecis_cihaz.sql --- */
const sql = fs.readFileSync(
  path.join(__dirname, "d1", "gecis_cihaz.sql"), "utf8");

function sadelestir(s) {
  return s
    .replace(/--[^\n]*/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\s*,\s*/g, ", ")
    .replace(/\(\s+/g, "(")
    .replace(/\s+\)/g, ")")
    .trim();
}

function coz(ifade) {
  const t = sadelestir(ifade);
  const m = t.match(
    /^CREATE (TABLE|INDEX) IF NOT EXISTS (\w+)\s*(.*)$/i);
  if (!m) return null;
  return { tur: m[1].toUpperCase(), ad: m[2], govde: m[3].trim() };
}

const sqlIfadeler = sadelestir(sql).split(";")
  .map((x) => x.trim()).filter(Boolean).map(coz).filter(Boolean);
const wkIfadeler = CIHAZ_SEMA.map(coz).filter(Boolean);

console.log("\nIki tanim da okunabiliyor");
dogru(sqlIfadeler.length >= 5, `gecis_cihaz.sql: ${sqlIfadeler.length} ifade`);
dogru(wkIfadeler.length >= 5, `worker CIHAZ_SEMA: ${wkIfadeler.length} ifade`);

console.log("\nAyni nesneler");
const ad = (x) => `${x.tur} ${x.ad}`;
esit(wkIfadeler.map(ad).sort(), sqlIfadeler.map(ad).sort(),
     "tablo ve indeks listeleri AYNI");

console.log("\nAyni govdeler");
const sqlHarita = new Map(sqlIfadeler.map((x) => [ad(x), x.govde]));
for (const w of wkIfadeler) {
  esit(w.govde, sqlHarita.get(ad(w)), `${ad(w)} govdesi ayni`);
}

console.log("\nDavranis kurallari iki tanimda da var");
for (const [etiket, metin] of [["worker", sadelestir(CIHAZ_SEMA.join(";"))],
                               ["sql", sadelestir(sql)]]) {
  // 1. Ayni cihaz iki kez kaydedilemesin.
  dogru(/cihaz \(jeton TEXT PRIMARY KEY/.test(metin),
        `${etiket}: cihaz jetonu BIRINCIL ANAHTAR`);
  // 2. Uyelik zorunlu olmasin.
  dogru(/uye_id INTEGER REFERENCES uye\(id\) ON DELETE SET NULL/.test(metin),
        `${etiket}: uye_id NULL olabilir (uyelik zorunlu degil)`);
  dogru(!/uye_id INTEGER NOT NULL/.test(metin),
        `${etiket}: uye_id NOT NULL DEGIL`);
  // 3. Ayni olay iki kez duyurulmasin.
  dogru(/bildirim_izi \(anahtar TEXT PRIMARY KEY/.test(metin),
        `${etiket}: bildirim izi anahtari BIRINCIL ANAHTAR`);
}

console.log("\nTercih kumesi kapali");
/* Istemciden gelen tercihler BU KUMEYE gore suzuluyor. Serbest
   birakmak, istemcinin veritabanina istedigi anahtari
   yazabilmesi demekti. */
dogru(Array.isArray(BILDIRIM_TURLERI) && BILDIRIM_TURLERI.length >= 3,
      `BILDIRIM_TURLERI tanimli (${(BILDIRIM_TURLERI || []).join(", ")})`);
const govde = kaynak.slice(kaynak.indexOf("async function cihazKaydet"));
dogru(/for \(const t of BILDIRIM_TURLERI\)/.test(govde),
      "tercihler BILDIRIM_TURLERI ile suzuluyor");
dogru(/ExponentPushToken/.test(govde),
      "jeton bicimi denetleniyor (tablo cop dolmasin)");

console.log("\nCihaz kaydi oturum ISTEMIYOR");
/* Icerigin tamami uyeliksiz okunabiliyor; bildirim icin uyelik
   istemek tutarsiz olurdu. Yonlendirme oturum kapisindan ONCE
   olmali. */
/* TAM DOSYA okunuyor, `kaynak` DEGIL.
 *
 * `kaynak` yukarida `export default`ta kesiliyor (islevleri `vm`
 * icinde kosturabilmek icin) ve YONLENDIRME o blogun ICINDE.
 * Kesilmis metinde arayinca `indexOf` -1 donuyordu.
 *
 * Daha kotusu: ikinci denetim `-1 < kapiYeri` oldugu icin SAHTE
 * YESIL veriyordu. Bu depoda bilinen desen -- sira karsilastirmasi
 * once "ikisi de BULUNDU mu" diye sormali. */
const tamKaynak = fs.readFileSync(
  path.join(__dirname, "worker.js"), "utf8");
const yolYeri = tamKaynak.indexOf('if (y === "cihaz" && m === "POST")');
const silYeri = tamKaynak.indexOf('if (y === "cihaz" && m === "DELETE")');
/* KAPI, YONLENDIRICININ ICINDEKI olan. `uyeBul` cagrisi dosyada
 * birden cok yerde geciyor -- `cihazKaydet` de oturum VARSA
 * okumak icin cagiriyor ve o cagri dosyada DAHA ONCE. Ilk
 * eslesmeyi "kapi" saymak, sinamanin kendi eklediği islevi kapi
 * sanmasi demekti (ilk yazimda tam bu oldu).
 *
 * Yonlendiricideki kapi yorumuyla aniliyor. */
const kapiYeri = tamKaynak.indexOf("Buradan sonrasi oturum istiyor");
dogru(yolYeri > 0, "cihaz kayit yonlendirmesi var");
dogru(silYeri > 0, "cihaz silme yonlendirmesi var");
dogru(kapiYeri > 0, "oturum kapisi bulundu");
dogru(yolYeri > 0 && kapiYeri > 0 && yolYeri < kapiYeri,
      "cihaz yonlendirmesi OTURUM KAPISINDAN ONCE");

if (kaldi.length) {
  console.log("\ncihaz semasi: " + kaldi.length + " KALDI");
  process.exit(1);
}
console.log("\ncihaz semasi: " + gecti + " dogrulama gecti");
