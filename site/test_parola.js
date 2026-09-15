/* Parola degistirme -- eski parola, oturum temizligi, sinir.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * Denetimde (2026-09-15) gorulen eksik: uye parolasini
 * DEGISTIREMIYORDU. Parolasi baska bir sitede sizan bir kullanicinin
 * yapabilecegi hicbir sey yoktu.
 *
 * Uc kural birden tasiyor ve ucu de sessizce bozulabilir:
 *
 *   1. ESKI PAROLA soruluyor. Oturum tek basina yetmez -- odunc
 *      alinmis ya da calinmis bir oturum, hesabi KALICI olarak ele
 *      geciremesin.
 *   2. DIGER OTURUMLAR kapaniyor. Parola degistirmenin asil amaci
 *      budur; yalnizca parolayi guncelleyip oturumlari birakmak,
 *      kullaniciya YAPILMAMIS bir seyi yapilmis gibi gosterirdi.
 *   3. KENDI oturumu KORUNUYOR -- kullanici kendi islemi yuzunden
 *      disari atilmamali.
 *
 * Kullanim:  node site/test_parola.js
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

let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

const ortam = {
  console: { log() {}, error() {} },
  TextEncoder, TextDecoder, Date, Math, Number, JSON, String, Promise, Object,
  crypto: require("crypto").webcrypto,
  /* `yanit` bir Response uretiyor; VM baglaminda yok. Govdeyi ve
     durumu okuyabilen en kucuk taklit. */
  Response: class {
    constructor(govde, ayar) {
      this._g = govde;
      this.status = (ayar && ayar.status) || 200;
    }
    async json() { return JSON.parse(this._g); }
  },
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const parolaDegistir = ortam.parolaDegistir;
const parolaOzetle = ortam.parolaOzetle;
const parolaKurali = ortam.parolaKurali;
const sha256 = ortam.sha256;

/* Sahte D1: uye parolasi, oturum satirlari ve deneme sayaci. */
function sahteDB(ozet) {
  const durum = {
    ozet,
    oturumlar: ["ozet-BENIM", "ozet-BASKA-1", "ozet-BASKA-2"],
    deneme: new Map(),
    guncelleme: 0,
  };
  durum.prepare = function (sql) {
    let par = [];
    const api = {
      bind(...p) { par = p; return api; },
      async first() {
        if (sql.indexOf("SELECT parola_ozet FROM uye") !== -1) {
          return { parola_ozet: durum.ozet };
        }
        if (sql.indexOf("SELECT sayi, sifirlanir") !== -1) {
          return durum.deneme.get(par[0]) || null;
        }
        return null;
      },
      async run() {
        if (sql.indexOf("UPDATE uye SET parola_ozet") !== -1) {
          durum.ozet = par[0];
          durum.guncelleme += 1;
        } else if (sql.indexOf("DELETE FROM oturum") !== -1) {
          /* TAKLIT KARSILASTIRMAYI GERCEKTEN UYGULUYOR.
             Ilk yazimda hangi operator olursa olsun "yalnizca
             verileni birak" deniyordu; `<>` yerine `=` koyan
             mutasyon KACTI -- yani "kendi oturumu korunuyor"
             iddiasi hicbir sey olcmuyordu. */
          const disla = sql.indexOf("jeton_ozeti <> ?") !== -1;
          durum.oturumlar = durum.oturumlar.filter(
            (x) => (disla ? x === par[1] : x !== par[1]));
        } else if (sql.indexOf("INSERT INTO deneme") !== -1) {
          durum.deneme.set(par[0], { sayi: 1, sifirlanir: par[1] });
        } else if (sql.indexOf("UPDATE deneme") !== -1) {
          const d = durum.deneme.get(par[0]);
          if (d) d.sayi += 1;
        } else if (sql.indexOf("DELETE FROM deneme") !== -1) {
          durum.deneme.delete(par[0]);
        }
        return {};
      },
    };
    return api;
  };
  return durum;
}

function istekYap(govde, jeton) {
  return {
    headers: {
      get(ad) {
        if (ad.toLowerCase() === "cookie") {
          return jeton ? `netaris_oturum=${jeton}` : null;
        }
        return null;
      },
    },
    async json() { return govde; },
  };
}

async function kos() {
  console.log("\nAlan yuklendi mi\n");
  esit(typeof parolaDegistir, "function", "parolaDegistir bulundu");
  esit(typeof parolaKurali, "function", "parolaKurali bulundu");

  console.log("\nParola kurali TEK YERDE\n");
  esit(parolaKurali("kisa"), "Parola en az 10 karakter olmalı.",
       "on karakterin altI reddediliyor");
  esit(parolaKurali("x".repeat(201)), "Parola çok uzun.",
       "asiri uzun reddediliyor");
  esit(parolaKurali(""), "Parola gerekli.", "bos reddediliyor");
  esit(parolaKurali("yeterince-uzun-parola"), "", "gecerli parola geciyor");
  /* Kayit yolu da AYNI kurali cagiriyor -- iki yerde iki kural olmasin. */
  const govde = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
  const kayit = govde.slice(govde.indexOf("async function kayit("),
                            govde.indexOf("async function dogrula("));
  esit(kayit.indexOf("parolaKurali(parola)") !== -1, true,
       "kayit yolu ayni kurali CAGIRIYOR");

  console.log("\nESKI PAROLA soruluyor\n");
  const eskiOzet = await parolaOzetle("dogru-eski-parola");
  let db = sahteDB(eskiOzet);
  let y = await parolaDegistir(
    istekYap({ eski: "YANLIS-parola", yeni: "yepyeni-parolam" }, "jtn"),
    { DB: db }, { id: 7 });
  esit(y.status, 400, "yanlis eski parola reddediliyor");
  esit(db.guncelleme, 0, "parola DEGISMEDI");
  esit(db.oturumlar.length, 3, "oturumlar DOKUNULMADI");

  console.log("\nDogru eski parola -- degisim ve oturum temizligi\n");
  db = sahteDB(eskiOzet);
  const benimJeton = "benim-jetonum";
  const benimOzet = await sha256(benimJeton);
  db.oturumlar = [benimOzet, "ozet-BASKA-1", "ozet-BASKA-2"];
  y = await parolaDegistir(
    istekYap({ eski: "dogru-eski-parola", yeni: "yepyeni-parolam" },
             benimJeton),
    { DB: db }, { id: 7 });
  esit(y.status, 200, "dogru parolayla degisiyor");
  esit(db.guncelleme, 1, "parola guncellendi");
  esit(db.ozet !== eskiOzet, true, "ozet gercekten degisti");
  esit(db.oturumlar.length, 1, "DIGER oturumlar kapatildi");
  esit(db.oturumlar[0], benimOzet, "KENDI oturumu korundu");

  console.log("\nAyni parola tekrar konulamaz\n");
  db = sahteDB(eskiOzet);
  y = await parolaDegistir(
    istekYap({ eski: "dogru-eski-parola", yeni: "dogru-eski-parola" }, "j"),
    { DB: db }, { id: 7 });
  esit(y.status, 400, "eskiyle ayni parola reddediliyor");
  esit(db.guncelleme, 0, "parola degismedi");

  console.log("\nGoogle hesabinda parola KURULMUYOR\n");
  /* Oturumu ele geciren biri, hesaba kalici bir giris yolu
     eklememeli. Sebep sessizce gizlenmiyor, adiyla yaziliyor. */
  db = sahteDB("");
  y = await parolaDegistir(
    istekYap({ eski: "", yeni: "yepyeni-parolam" }, "j"), { DB: db },
    { id: 7 });
  esit(y.status, 400, "parolasiz hesapta reddediliyor");
  esit((await y.json()).hata.indexOf("Google") !== -1, true,
       "sebep adiyla yaziliyor");
  esit(db.guncelleme, 0, "parola kurulmadi");

  console.log("\nDeneme sinirI var\n");
  db = sahteDB(eskiOzet);
  let sonDurum = 0;
  for (let i = 0; i < 9; i++) {
    const r = await parolaDegistir(
      istekYap({ eski: "YANLIS", yeni: "yepyeni-parolam" }, "j"),
      { DB: db }, { id: 7 });
    sonDurum = r.status;
  }
  esit(sonDurum, 429, "israrli deneme kilitleniyor");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
}

kos();
