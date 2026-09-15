/* JS'te aranan her `data-` seciciyi URETEN bir yer olmali.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * Eslesme SESSIZ bozulur: `querySelectorAll` bulamayinca bos liste
 * doner, hata vermez. Dugme tiklanir ve HICBIR SEY olmaz. Bir harf
 * hatasi ya da yeniden adlandirmada unutulan bir taraf, olu bir
 * arayuz birakir ve hicbir yerde kirmizi yanmaz.
 *
 * Bugun (2026-09-15) bunun somut bir ornegi cikti: "Askıya al"
 * dugmesi `data-uye-askı` ile isaretleniyordu -- depodaki tek ASCII
 * disi oznitelik adi. Kural o vakadan dogdu.
 *
 * URETICI UC BICIMDE OLABILIR ve ucu de sayilmali; ilk yazimda
 * yalnizca ilki sayildi ve sinama ALTI HAYALET kusur bildirdi:
 *
 *   1. Isaretleme      : <b data-yol="..."> ya da ciplak <b data-panel>
 *   2. dataset atamasi : el.dataset.begeniKaldir = "..."   (camelCase!)
 *   3. setAttribute    : el.setAttribute("data-serit-kopya", "")
 *
 * Ikincisi ozellikle sinsi: `dataset.sayacG` ile `data-sayac-g` ayni
 * seydir ama metin olarak hic benzemiyor.
 *
 * Kullanim:  node site/test_secici.js
 */

"use strict";

const fs = require("fs");
const path = require("path");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (JSON.stringify(bulunan) === JSON.stringify(beklenen)) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

/* Kural ISARETLEMEYI olcuyor, onun hakkinda yazilan duzyaziyi degil.
   `//` satirlari BILEREK ayiklanmiyor: dizge icindeki "https://"
   yanlislikla yorum sanilirdi. */
function yorumsuz(metin) {
  return metin
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/\{#[\s\S]*?#\}/g, " ")
    .replace(/<!--[\s\S]*?-->/g, " ");
}

function dosyalar(kok, uzanti) {
  const d = path.join(__dirname, kok);
  if (!fs.existsSync(d)) return [];
  return fs.readdirSync(d)
    .filter((a) => uzanti.test(a))
    .map((a) => path.join(d, a));
}

/* `dataset.sayacG` -> `data-sayac-g` */
function dataseti(ad) {
  return "data-" + ad.replace(/[A-Z]/g, (h) => "-" + h.toLowerCase());
}

const jsler = dosyalar("statik", /\.js$/);
const htmller = dosyalar("sablonlar", /\.html$/);

console.log("\nAranan her secicinin bir URETICISI var\n");
esit(jsler.length > 3 && htmller.length > 3, true,
     `tarama dolu (${jsler.length} js, ${htmller.length} html)`);

const aranan = new Map();
for (const y of jsler) {
  const m = yorumsuz(fs.readFileSync(y, "utf8"));
  for (const x of m.matchAll(/\[\s*(data-[A-Za-z0-9_-]+)/g)) {
    if (!aranan.has(x[1])) aranan.set(x[1], path.basename(y));
  }
}

const uretilen = new Set();
for (const y of jsler.concat(htmller)) {
  const m = yorumsuz(fs.readFileSync(y, "utf8"));
  /* 1. isaretleme -- degerli ya da ciplak */
  for (const x of m.matchAll(/\b(data-[A-Za-z0-9_-]+)\s*=/g)) uretilen.add(x[1]);
  for (const x of m.matchAll(/<[a-zA-Z]+[^>]*?\s(data-[A-Za-z0-9_-]+)[\s>]/g)) {
    uretilen.add(x[1]);
  }
  /* 1b. sablonda kosullu ciplak oznitelik: {% if x %}data-y{% endif %} */
  for (const x of m.matchAll(/%\}\s*(data-[A-Za-z0-9_-]+)/g)) uretilen.add(x[1]);
  /* 2. dataset atamasi (camelCase) */
  for (const x of m.matchAll(/\.dataset\.([A-Za-z0-9_]+)/g)) {
    uretilen.add(dataseti(x[1]));
  }
  /* 3. setAttribute / getAttribute / hasAttribute */
  for (const x of m.matchAll(/Attribute\(\s*["'](data-[A-Za-z0-9_-]+)["']/g)) {
    uretilen.add(x[1]);
  }
}

esit(aranan.size > 40, true, `secici taramasi dolu (${aranan.size})`);
esit(uretilen.size > 40, true, `uretici taramasi dolu (${uretilen.size})`);

const oksuz = [...aranan.keys()].filter((k) => !uretilen.has(k)).sort();
esit(oksuz.slice(0, 6), [],
     "karsiligi olmayan secici yok (olu dugme yok)");

console.log("\nKural gercekten olcuyor\n");
/* camelCase cevrimi dogru mu -- bu olmadan alti gercek uretici
   'eksik' gorunuyordu. */
esit(dataseti("sayacG"), "data-sayac-g", "dataset.sayacG cevriliyor");
esit(dataseti("begeniKaldir"), "data-begeni-kaldir",
     "dataset.begeniKaldir cevriliyor");
esit(dataseti("yol"), "data-yol", "tek sozcuklu dataset cevriliyor");

console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
process.exit(kaldi.length ? 1 : 0);
