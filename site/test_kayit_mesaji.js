/* Kayit yaniti DEPODAKI GERCEGI anlatmali.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * `durum` alani gonderimden ONCE, yalnizca anahtarin varligina
 * bakilarak yaziliyor:
 *
 *     durum: postaVar ? "beklemede" : "etkin"
 *
 * Mesaj ise IKI duruma bakiyordu, oysa UC durum var:
 *
 *   1. posta kapali (anahtar yok)  -> uye ETKIN, giris yapabilir.
 *   2. posta acik, gonderim TAMAM  -> uye BEKLEMEDE, baglanti geldi.
 *   3. posta acik, gonderim DUSTU  -> uye BEKLEMEDE, baglanti GELMEDI.
 *
 * Ucuncusunde kullaniciya "Kaydiniz tamamlandi. Giris yapabilirsiniz."
 * deniyordu -- oysa `durum` hala `beklemede` ve giris YAPILAMIYOR.
 * Mesaj, depodaki gercegin TERSINI soyluyordu.
 *
 * Kodun kendi basligi "MESAJ GERCEGI SOYLUYOR" idi; duzeltme eksik
 * kalmisti.
 *
 * Kullanim:  node site/test_kayit_mesaji.js
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
  URL,
  crypto: require("crypto").webcrypto,
  fetch: async () => ({ ok: false, status: 422 }),   /* gonderim DUSUYOR */
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

const kayit = ortam.kayit;

/* Sahte D1: uye tablosu ve deneme sayaci. */
function sahteDB() {
  const durum = { uyeler: [], deneme: new Map() };
  durum.prepare = function (sql) {
    let par = [];
    const api = {
      bind(...p) { par = p; return api; },
      async first() {
        if (sql.indexOf("SELECT id FROM uye") !== -1) return null;
        if (sql.indexOf("SELECT sayi, sifirlanir") !== -1) {
          return durum.deneme.get(par[0]) || null;
        }
        return null;
      },
      async run() {
        if (sql.indexOf("INSERT INTO uye") !== -1) {
          durum.uyeler.push({ eposta: par[0], durum: par[3] });
        } else if (sql.indexOf("INSERT INTO deneme") !== -1) {
          durum.deneme.set(par[0], { sayi: 1, sifirlanir: par[1] });
        } else if (sql.indexOf("UPDATE deneme") !== -1) {
          const d = durum.deneme.get(par[0]);
          if (d) d.sayi += 1;
        }
        return {};
      },
    };
    return api;
  };
  return durum;
}

function istekYap(eposta) {
  return {
    url: "https://netaris.net/api/kayit",
    headers: { get() { return "203.0.113.9"; } },
    async json() {
      return { ad: "Deneme", eposta, parola: "yeterince-uzun-parola" };
    },
  };
}

async function kos() {
  console.log("\nAlan yuklendi mi\n");
  esit(typeof kayit, "function", "kayit bulundu");

  console.log("\n1. Posta KAPALI -- uye etkin, giris hazir\n");
  let db = sahteDB();
  let y = await kayit(istekYap("a@ornek.test"), { DB: db });
  let v = await y.json();
  esit(db.uyeler[0].durum, "etkin", "uye ETKIN yazildi");
  esit(v.girisHazir, true, "girisHazir dogru");
  esit(v.mesaj.indexOf("Giriş yapabilirsiniz") !== -1, true,
       "mesaj giris yapilabilecegini soyluyor");

  console.log("\n3. Posta ACIK ama gonderim DUSTU\n");
  /* ASIL KUSUR. Uye `beklemede` kaliyor ve GIRIS YAPAMIYOR; mesaj
     bunu soylemeli. */
  db = sahteDB();
  y = await kayit(istekYap("b@ornek.test"),
                  { DB: db, RESEND_API_KEY: "anahtar" });
  v = await y.json();
  esit(db.uyeler[0].durum, "beklemede", "uye BEKLEMEDE kaldi");
  esit(v.posta, false, "posta gitmedi olarak bildiriliyor");
  esit(v.girisHazir, false, "girisHazir YANLIS -- giris yapilamaz");
  esit(v.mesaj.indexOf("Giriş yapabilirsiniz") === -1, true,
       "mesaj giris yapilabilecegini SOYLEMIYOR");
  esit(v.mesaj.indexOf("gönderilemedi") !== -1, true,
       "mesaj sebebi soyluyor");

  console.log("\n2. Posta ACIK ve gonderim TAMAM\n");
  ortam.fetch = async () => ({ ok: true, status: 200 });
  db = sahteDB();
  y = await kayit(istekYap("c@ornek.test"),
                  { DB: db, RESEND_API_KEY: "anahtar" });
  v = await y.json();
  esit(db.uyeler[0].durum, "beklemede", "uye BEKLEMEDE (dogrulama bekliyor)");
  esit(v.posta, true, "posta gitti");
  esit(v.mesaj.indexOf("gönderildi") !== -1, true,
       "mesaj baglantinin gittigini soyluyor");

  console.log("\nIstemci ucunu TAHMIN ETMIYOR\n");
  /* "Giris yapabilir miyim" sorusunun cevabi sunucudan geliyor;
     istemci `posta` alanindan cikarim yapmiyor. */
  const betik = fs.readFileSync(
    path.join(__dirname, "statik", "uyelik.js"), "utf8");
  esit(betik.indexOf("y.veri.girisHazir") !== -1, true,
       "istemci girisHazir alanini okuyor");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
}

kos();
