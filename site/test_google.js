/* Google kimlik jetonu dogrulamasi -- GERCEK imzalarla.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * Bu fonksiyon "bu kisi kim" sorusunun tek cevabi. Yanlis calisirsa
 * sonuc bozuk bir sayfa degil, BASKASININ HESABINA GIRIS olur.
 *
 * En agir ve en sik atlanan denetim `aud`: Google'in imzaladigi her
 * jeton gecerli bir Google jetonudur, ama BIZE verilmis olmasi ayri
 * bir sey. `aud` bakilmazsa herhangi bir sitenin jetonu burada gecerli
 * olur -- saldirgan kendi uygulamasina giris yapip aldigi jetonu bize
 * gonderir.
 *
 * Test gercek RSA anahtari uretiyor, gercek JWT imzaliyor ve JWKS
 * ucunu taklit ediyor. Imza dogrulamasi gercekten kosuyor.
 *
 * Kullanim:  node site/test_google.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { webcrypto } = require("crypto");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (bulunan === beklenen) { gecti++; console.log("  gecti  " + aciklama); }
  else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

const b64url = (bayt) =>
  Buffer.from(bayt).toString("base64")
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function kur() {
  const cift = await webcrypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"]);

  const jwk = await webcrypto.subtle.exportKey("jwk", cift.publicKey);
  jwk.kid = "sinama-anahtari";
  jwk.alg = "RS256";
  jwk.use = "sig";
  delete jwk.key_ops;
  delete jwk.ext;

  /* worker.js bir ES modulu; `export default` bloğu VM'de calismaz.
     Yalnizca o blok cikariliyor, fonksiyonlarin kodu AYNEN kosuyor --
     yani test gercek kaynagi sinamis oluyor. */
  let kaynak = fs.readFileSync(
    path.join(__dirname, "worker.js"), "utf8");
  kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

  const ortam = {
    crypto: webcrypto,
    TextEncoder, TextDecoder,
    atob: (m) => Buffer.from(m, "base64").toString("binary"),
    console,
    Response: class {},
    fetch: async (u) => {
      if (String(u).indexOf("googleapis.com/oauth2/v3/certs") !== -1) {
        return { ok: true, json: async () => ({ keys: [jwk] }) };
      }
      return { ok: false };
    },
  };
  ortam.globalThis = ortam;
  vm.createContext(ortam);
  vm.runInContext(kaynak, ortam);
  return { ortam, ozel: cift.privateKey };
}

async function jetonYap(ozel, iddia, bas) {
  const b = Object.assign({ alg: "RS256", kid: "sinama-anahtari", typ: "JWT" },
                          bas || {});
  const govde = b64url(JSON.stringify(b)) + "." + b64url(JSON.stringify(iddia));
  const imza = await webcrypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", ozel, new TextEncoder().encode(govde));
  return govde + "." + b64url(new Uint8Array(imza));
}

(async function () {
  console.log("\nGoogle kimlik jetonu dogrulamasi\n");

  const { ortam, ozel } = await kur();
  const BIZ = "bizim-istemci.apps.googleusercontent.com";
  const ileri = Math.floor(Date.now() / 1000) + 3600;
  const geri = Math.floor(Date.now() / 1000) - 60;

  const temel = {
    iss: "https://accounts.google.com", aud: BIZ, exp: ileri,
    sub: "1234567890", email: "okur@ornek.com", email_verified: true,
    name: "Örnek Okur",
  };

  let s = await ortam.jetonDogrula(await jetonYap(ozel, temel), BIZ);
  esit(s && s.email, "okur@ornek.com", "gecerli jeton kabul ediliyor");

  // --- EN KRITIK: baska bir uygulamaya verilmis GECERLI Google jetonu
  s = await ortam.jetonDogrula(
    await jetonYap(ozel, Object.assign({}, temel, { aud: "baska-uygulama" })), BIZ);
  esit(s, null, "BASKA uygulamanin jetonu reddediliyor (aud denetimi)");

  s = await ortam.jetonDogrula(
    await jetonYap(ozel, Object.assign({}, temel, { iss: "kotu.example" })), BIZ);
  esit(s, null, "yanlis 'iss' reddediliyor");

  s = await ortam.jetonDogrula(
    await jetonYap(ozel, Object.assign({}, temel, { exp: geri })), BIZ);
  esit(s, null, "suresi dolmus jeton reddediliyor");

  s = await ortam.jetonDogrula(
    await jetonYap(ozel, Object.assign({}, temel, { email_verified: false })), BIZ);
  esit(s, null, "dogrulanmamis e-posta reddediliyor");

  // --- IMZA. Govde degistirilip imza korunuyor.
  const iyi = await jetonYap(ozel, temel);
  const p = iyi.split(".");
  const sahte = p[0] + "." + b64url(JSON.stringify(
    Object.assign({}, temel, { email: "saldirgan@ornek.com" }))) + "." + p[2];
  s = await ortam.jetonDogrula(sahte, BIZ);
  esit(s, null, "govdesi degistirilmis jeton reddediliyor (imza)");

  // --- Algoritma karistirma. "alg: none" klasik atlatma yolu.
  const yok = b64url(JSON.stringify({ alg: "none", kid: "sinama-anahtari" }))
            + "." + b64url(JSON.stringify(temel)) + ".";
  s = await ortam.jetonDogrula(yok, BIZ);
  esit(s, null, "'alg: none' reddediliyor");

  s = await ortam.jetonDogrula(
    await jetonYap(ozel, temel, { kid: "bilinmeyen" }), BIZ);
  esit(s, null, "bilinmeyen anahtar kimligi reddediliyor");

  esit(await ortam.jetonDogrula("bozuk", BIZ), null, "bicimsiz jeton");
  esit(await ortam.jetonDogrula("", BIZ), null, "bos jeton");
  esit(await ortam.jetonDogrula(null, BIZ), null, "null jeton");

  s = await ortam.jetonDogrula(
    await jetonYap(ozel, Object.assign({}, temel, { email: undefined })), BIZ);
  esit(s, null, "e-postasiz jeton reddediliyor");

  console.log("");
  if (kaldi.length) {
    console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti");
    process.exit(1);
  }
  console.log("TUM TESTLER GECTI (" + gecti + ")");
})();
