/* 404 SAYFASINI WORKER SERVIS EDIYOR -- ve baska hicbir seyi bozmuyor.
 *
 * NEDEN BU DOSYA VAR
 * ------------------
 * Olculdu (2026-09-15): `/analiz/` SIFIR BAYT donuyordu ve sitede 404
 * sayfasi hic yoktu -- yanlis yazilmis her adres bembeyaz bir
 * sayfaydi. Kusur SESSIZDI: Cloudflare dogru statuyu (404) doner,
 * yalnizca govde bostur.
 *
 * ILK DUZELTME GERI ALINDI. `not_found_handling = "404-page"` tek
 * satirlik cozum GORUNUYORDU. Ama varlik katmani worker'dan ONCE
 * calisiyor ve `assets_navigation_prefers_asset_serving` (2025-04-01
 * sonrasi uyumluluk tarihlerinde varsayilan; bizimki 2026-07-31)
 * gezinme isteklerinin worker'i HIC cagirmamasina yol aciyor. Bu
 * sitede eslesen dosyasi olmayan ama worker'in URETTIGI adresler var:
 *
 *     /senaryo/1/  -> 200, 10888 bayt   (worker uretti)
 *     /haber       -> 301 /gundem       (worker yonlendirdi)
 *
 * Yani ayar, CALISAN iki ozelligi belgesiz bir davranisa yaslayarak
 * riske atiyordu. Karar artik varlik katmani ZATEN 404 dedikten SONRA
 * veriliyor.
 *
 * NE SINANIYOR
 * ------------
 * 1. Varlik 404 dedi -> 404 sayfasi, STATU YINE 404 (soft-404 degil).
 * 2. Varlik buldu    -> govde oldugu gibi geciyor, worker karismiyor.
 * 3. Yonlendirme     -> 301 404'e cevrilmiyor.
 * 4. `/api/`         -> varlik katmanina HIC ugramiyor.
 * 5. 404.html yoksa  -> ciplak 404, worker kendi sayfasini uydurmuyor.
 *
 * Kullanim:  node site/test_bulunamadi_servis.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

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

/* `export default {...}` bir ES modul sozdizimi; vm icinde
   calismiyor. Adi olan bir degiskene baglaniyor ki fetch isleyicisine
   ULASILABILSIN -- eski sinamalar onu KESIP atiyordu ve bu yuzden
   isleyiciyi hic kimse olcmuyordu. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
esit(kaynak.includes("export default"), true, "worker.js varsayilan disa aktarim tasiyor");
kaynak = kaynak.replace("export default", "globalThis.__wrk =");

const kap = {
  crypto: require("crypto").webcrypto,
  URL, Request, Response, Headers, TextEncoder, TextDecoder,
  fetch: async () => new Response("", { status: 200 }),
  console, atob, btoa, globalThis: null,
};
kap.globalThis = kap;
vm.createContext(kap);
vm.runInContext(kaynak, kap);
const wrk = kap.__wrk;
esit(typeof wrk.fetch, "function", "fetch isleyicisi bulundu");

const SAYFA_404 = "<html><h1>Bu sayfa yok</h1></html>";

/* Varlik katmanini taklit eder. `dosyalar` icinde OLAN yol 200,
   olmayan 404 doner -- gercek `not_found_handling = "none"` davranisi. */
function sahteVarlik(dosyalar, izle) {
  return {
    async fetch(istek) {
      /* Gercek baglanti gibi: dizge, URL ya da Request kabul ediyor.
         Ilk yazimda yalnizca dizge/Request vardi ve uretim kodu URL
         gonderdigi icin sinama URL AYRISTIRMA HATASIYLA patladi --
         olcum degil, kaza. */
      const y = new URL(
        istek instanceof URL ? istek.href
          : typeof istek === "string" ? istek : istek.url,
      ).pathname;
      if (izle) izle.push(y);
      if (dosyalar[y] === undefined) return new Response("", { status: 404 });
      return new Response(dosyalar[y], {
        status: 200,
        headers: { "Content-Type": "text/html" },
      });
    },
  };
}

const DOSYALAR = { "/gundem/": "GUNDEM SAYFASI", "/404.html": SAYFA_404 };

async function iste(yol, dosyalar = DOSYALAR, izle) {
  const env = { ASSETS: sahteVarlik(dosyalar, izle), DB: null };
  return wrk.fetch(new Request("https://netaris.net" + yol), env);
}

(async () => {
  console.log("\nVarlik 404 dediginde 404 SAYFASI doniyor\n");
  let y = await iste("/analiz/");
  esit(y.status, 404, "statu 404 KALIYOR (soft-404 degil)");
  esit(await y.text(), SAYFA_404, "govde 404 sayfasi -- bos degil");
  esit((y.headers.get("Content-Type") || "").includes("text/html"), true,
       "icerik turu html");

  console.log("\nBulunan sayfaya KARISMIYOR\n");
  y = await iste("/gundem/");
  esit(y.status, 200, "var olan sayfa 200");
  esit(await y.text(), "GUNDEM SAYFASI", "govde degismeden geciyor");

  console.log("\nYonlendirme 404'e cevrilmiyor\n");
  y = await iste("/haber");
  esit(y.status, 301, "/haber 301 KALIYOR");
  esit(y.headers.get("Location"), "https://netaris.net/gundem",
       "hedef /gundem");

  console.log("\n/api/ varlik katmanina UGRAMIYOR\n");
  const izlenen = [];
  y = await iste("/api/uye", DOSYALAR, izlenen);
  esit(izlenen, [], "/api/ icin varlik katmani hic cagrilmadi");
  esit(y.status, 503, "DB yokken 503 -- 404 sayfasi degil");

  console.log("\n404.html yoksa worker bir sey UYDURMUYOR\n");
  y = await iste("/analiz/", { "/gundem/": "x" });
  esit(y.status, 404, "sayfasiz da olsa 404");
  esit(await y.text(), "", "govde bos -- worker kendi sayfasini uydurmuyor");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
})();
