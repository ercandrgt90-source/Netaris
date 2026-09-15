/* Giris deneme sinirlari -- HESABA ve KAYNAGA ayri.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * Giris sinirI yalnizca E-POSTAYA baglaniyordu:
 *
 *     denemeArtir(db, `giris:${eposta}`, 900, 8)
 *
 * Bu, tek bir hesaba yapilan kaba kuvveti durduruyor. Ama PAROLA
 * PUSKURTMEsi -- her hesaba BIRER deneme, binlerce hesap -- o siniri
 * HIC gormez: her anahtar ilk denemesinde ve sayac hep 1 kalir.
 * Sizmis e-posta listeleriyle yapilan gercek saldirinin bicimi budur.
 *
 * Telafi olarak anilan PBKDF2 dongusu 100.000'de TAVANLI ve bu bir
 * tercih degil, Cloudflare Workers siniri (bkz. `PBKDF2_DONGU`).
 * Yani tek basina yeterli degil.
 *
 * NE SINANIYOR
 * ------------
 * 1. Ayni hesaba israr -> e-posta siniri kilitliyor.
 * 2. FARKLI hesaplara birer deneme -> IP siniri kilitliyor.
 *    (Bu, duzeltmeden once HIC yakalanmayan durum.)
 * 3. Basarili giris IKI sayaci da sifirliyor -- ayni ag arkasindaki
 *    mesru kullanicilar birbirini kilitlememeli.
 *
 * Kullanim:  node site/test_giris_siniri.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (bulunan === beklenen) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

/* worker.js bir ES modulu; `export default` blogu VM'de calismaz.
   Yalnizca o blok cikariliyor, fonksiyonlarin kodu AYNEN kosuyor. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

const ortam = {
  console: { log() {}, error() {} },
  TextEncoder, TextDecoder, Date, Math, Number, JSON, String, Promise,
  crypto: require("crypto").webcrypto,
  Response: class {},
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const denemeArtir = ortam.denemeArtir;
const denemeSifirla = ortam.denemeSifirla;

/* Sahte D1: `deneme` tablosunu bellekte tutuyor. */
function sahteDB() {
  const satir = new Map();
  return {
    satir,
    prepare(sql) {
      let par = [];
      const api = {
        bind(...p) { par = p; return api; },
        async first() {
          if (sql.indexOf("SELECT sayi, sifirlanir") !== -1) {
            return satir.get(par[0]) || null;
          }
          return null;
        },
        async run() {
          if (sql.indexOf("INSERT INTO deneme") !== -1) {
            satir.set(par[0], { sayi: 1, sifirlanir: par[1] });
          } else if (sql.indexOf("UPDATE deneme") !== -1) {
            const s = satir.get(par[0]);
            if (s) s.sayi += 1;
          } else if (sql.indexOf("DELETE FROM deneme") !== -1) {
            satir.delete(par[0]);
          }
          return {};
        },
      };
      return api;
    },
  };
}

async function kos() {
  console.log("\nAlan yuklendi mi\n");
  esit(typeof denemeArtir, "function", "denemeArtir bulundu");
  esit(typeof denemeSifirla, "function", "denemeSifirla bulundu");

  console.log("\nAYNI HESABA israr -- e-posta siniri kilitliyor\n");
  let db = sahteDB();
  let kilit = false;
  for (let i = 0; i < 9; i++) {
    kilit = await denemeArtir(db, "giris:kurban@ornek.test", 900, 8);
  }
  esit(kilit, true, "dokuzuncu denemede kilitlendi");

  console.log("\nPUSKURTME -- farkli hesaplara BIRER deneme\n");
  /* Duzeltmeden ONCE: her e-posta anahtari ilk denemesinde, sayac hep
     1, hicbir sinir ateslenmiyor. */
  db = sahteDB();
  let epostaKilidi = false;
  for (let i = 0; i < 50; i++) {
    epostaKilidi = epostaKilidi
      || await denemeArtir(db, `giris:hedef${i}@ornek.test`, 900, 8);
  }
  esit(epostaKilidi, false,
       "e-posta siniri puskurtmeyi GORMUYOR (kusurun kendisi)");

  /* Duzeltme: ayni kaynaktan gelen denemeler IP anahtarinda birikiyor. */
  db = sahteDB();
  let ipKilidi = false;
  for (let i = 0; i < 50; i++) {
    ipKilidi = await denemeArtir(db, "giris-ip:203.0.113.7", 900, 40);
  }
  esit(ipKilidi, true, "IP siniri puskurtmeyi KILITLIYOR");

  /* Sinir BOL: mesru kullanim bu esige yaklasmamali. */
  db = sahteDB();
  let erken = false;
  for (let i = 0; i < 20; i++) {
    erken = await denemeArtir(db, "giris-ip:203.0.113.7", 900, 40);
  }
  esit(erken, false, "yirmi denemede kilitlenmiyor -- sinir bol");

  console.log("\nBASARILI giris IKI sayaci da sifirliyor\n");
  db = sahteDB();
  for (let i = 0; i < 5; i++) {
    await denemeArtir(db, "giris:mesru@ornek.test", 900, 8);
    await denemeArtir(db, "giris-ip:198.51.100.3", 900, 40);
  }
  esit(db.satir.size, 2, "iki sayac da dolu");
  await denemeSifirla(db, "giris:mesru@ornek.test");
  await denemeSifirla(db, "giris-ip:198.51.100.3");
  esit(db.satir.size, 0, "basarili giristen sonra ikisi de sifirlandi");

  console.log("\nKaynak: giris yolu IKI siniri da cagiriyor\n");
  /* Sayac mantigi dogru olsa bile `giris()` onu CAGIRMAZSA koruma
     yoktur. Ilk yazimda sinama yalnizca `denemeArtir`i olcuyordu ve
     cagri yerini hic gormuyordu. */
  const govde = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
  const giris = govde.slice(govde.indexOf("async function giris("),
                            govde.indexOf("async function cikis("));
  /* CAGRIYA OZGU ARAMA. Ilk yazimda yalnizca "giris-ip:" dizgesi
     araniyordu; o dizge YORUMDA ve sifirlama satirinda da geciyor,
     dolayisiyla cagriyi kaldiran mutasyon KACTI. Alt dizge tuzagi --
     bu depoda bugun ucuncu kez. */
  esit(giris.indexOf("denemeArtir(db, `giris-ip:") !== -1, true,
       "giris() IP sinirini CAGIRIYOR (yorumda gecmesi yetmez)");
  esit(giris.indexOf("denemeArtir(db, `giris:${eposta}`") !== -1, true,
       "giris() e-posta sinirini CAGIRIYOR");
  esit(giris.indexOf("denemeSifirla(db, `giris-ip:") !== -1, true,
       "basarili giriste IP sayaci sifirlaniyor");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
}

kos();
