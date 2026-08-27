/* Nobetci -- GitHub takvimi durdugunda akisi geri getiren yedek tetik.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * 2026-08-26 aksami GitHub Actions kotasi doldu. Kota bitince is
 * KIRMIZI DONMUYOR, sadece BASLAMIYOR -- yani hicbir yerde uyari
 * gorunmuyor. Depo ertesi gun herkese acildi (dakika sinirsiz) ama
 * zamanlanmis kosular geri gelmedi: 26 Agustos 16:36'dan sonra bir
 * tane bile dusmedi, elle tetiklenenler ise sorunsuz calisti. Yani
 * hat saglamdi; calismayan sey ZAMANLAYICIYDI. Site saatlerce bayat
 * kaldi ve bunu ancak birisi bakinca fark etti.
 *
 * Nobetci bu bosluğu kapatiyor: saat basi bakiyor, yayindaki icerik
 * esikten eskiyse GitHub'i tetikliyor.
 *
 * NEDEN SINANMASI GEREKIYOR
 * -------------------------
 * Bu kodun iki yanlis davranisi da PAHALI ve ikisi de SESSIZ:
 *
 *   * Fazla tetiklerse: her saat gereksiz kosu baslatir. GitHub'in
 *     kendi takvimi zaten calisirken ikinci bir kosu bosa is demek.
 *   * Az tetiklerse: hicbir sey olmaz ve site yine saatlerce bayat
 *     kalir -- yani nobetci VARMIS GIBI gorunur ama yoktur.
 *
 * Ozellikle "okunamadi" hali onemli: BILINMIYOR ile BAYAT ayni sey
 * degil. Bilinmezlikte tetiklemek, RSS'e gecici olarak ulasilamayan
 * her saatte bir kosu baslatmak olurdu.
 *
 * Calistirma:  node site/test_nobetci.js
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

/* Tetik cagrilarini yakalayan sahte `fetch`. */
let cagrilar = [];
function sahteFetch(url, ayar) {
  cagrilar.push({ url: String(url), ayar: ayar || {} });
  return Promise.resolve({ status: 204, ok: true });
}

const ortam = {
  console: { log() {}, error() {} },   /* gunluk gurultusu bastiriliyor */
  fetch: sahteFetch,
  Date, Number, JSON, Promise, String,
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const nobetci = ortam.nobetci;

/* `const` bildirimleri VM baglaminda `globalThis`e BAGLANMIYOR --
   yalnizca `function` bildirimleri baglaniyor. Ilk yazimda
   `ortam.NOBET_ESIK_SAAT` okundu, `undefined` geldi ve sinir
   sinamalari sessizce `NaN` ile kostu: "esigin ustunde tetikliyor"
   sinamasi gecersiz bir tarih uretip tetiklemedigi icin KALDI verdi.
   Ayni baglamda ikinci bir betik calistirmak sozcuksel baglamayi
   goruyor. */
const ESIK = vm.runInContext("NOBET_ESIK_SAAT", ortam);

/* Verilen yasa sahip bir RSS dondüren sahte ASSETS. */
function ortamKur(saat, jeton) {
  const govde = saat === null
    ? "<rss><channel></channel></rss>"
    : "<rss><channel><item><pubDate>"
      + new Date(Date.now() - saat * 3600000).toUTCString()
      + "</pubDate></item></channel></rss>";
  return {
    GITHUB_TETIK_JETONU: jeton,
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        text: () => Promise.resolve(govde),
      }),
    },
  };
}

async function kos() {
  console.log("\nNobetci -- alan yuklendi mi\n");
  esit(typeof nobetci, "function", "nobetci bulundu");
  esit(typeof ESIK, "number", "esik sayi olarak tanimli");

  console.log("\nJETON YOKSA HICBIR SEY YAPMAZ\n");
  /* Bu kodun dagitilmasi risksiz olmali: jeton eklenene kadar
     davranis degismemeli. */
  cagrilar = [];
  await nobetci(ortamKur(99, undefined));
  esit(cagrilar.length, 0, "jeton tanimsizken tetiklemiyor");
  cagrilar = [];
  await nobetci(ortamKur(99, ""));
  esit(cagrilar.length, 0, "jeton bos dizgiyken tetiklemiyor");

  console.log("\nTAZEYKEN KARISMIYOR\n");
  /* GitHub'in kendi takvimi calisirken nobetci sessiz durmali;
     aksi halde her sey iki kez kosar. */
  cagrilar = [];
  await nobetci(ortamKur(0.1, "jtn"));
  esit(cagrilar.length, 0, "6 dakikalik icerikte tetiklemiyor");
  cagrilar = [];
  await nobetci(ortamKur(ESIK - 0.2, "jtn"));
  esit(cagrilar.length, 0, "esigin hemen altinda tetiklemiyor");

  /* CIFT KOSU OLMAMALI.
     GitHub'in takvimi hafta ici YARIM SAATTE BIR kosuyor. O calisirken
     icerik yasi hicbir zaman ~30 dakikayi gecmez; nobetci o araliga hic
     karismamali, yoksa her sey iki kez kosar. Esik asagi cekilirse once
     bu sinama kirilir -- amaci tam olarak bu. */
  cagrilar = [];
  await nobetci(ortamKur(0.5, "jtn"));
  esit(cagrilar.length, 0, "GitHub normal araliginda (30 dk) susuyor");
  cagrilar = [];
  await nobetci(ortamKur(0.75, "jtn"));
  esit(cagrilar.length, 0, "GitHub 15 dk gecikse de susuyor");

  console.log("\nBAYATLAYINCA TETIKLIYOR\n");
  cagrilar = [];
  await nobetci(ortamKur(ESIK + 0.2, "jtn"));
  esit(cagrilar.length, 1, "esigin hemen ustunde tetikliyor");
  cagrilar = [];
  await nobetci(ortamKur(9, "jtn"));
  esit(cagrilar.length, 1, "9 saatlik icerikte tetikliyor");

  console.log("\nISTEK DOGRU KURULUYOR\n");
  const c = cagrilar[0];
  esit(c.url.endsWith("/dispatches"), true, "dispatches ucuna gidiyor");
  esit(c.ayar.method, "POST", "POST kullaniyor");
  /* GitHub API User-Agent'i ZORUNLU kiliyor; yoksa 403 doner ve
     tetik sessizce calismaz. */
  esit(typeof c.ayar.headers["User-Agent"], "string",
       "User-Agent gonderiliyor (GitHub zorunlu kiliyor)");
  esit(c.ayar.headers["Authorization"], "Bearer jtn",
       "jeton Authorization basliginda");
  esit(JSON.parse(c.ayar.body).event_type, "tazele",
       "olay turu is akisindakiyle ayni");

  console.log("\nBILINMIYOR, BAYAT DEMEK DEGIL\n");
  /* RSS okunamazsa tetiklememeli: gecici bir okuma hatasi her saat
     kosu baslatmamali. */
  cagrilar = [];
  await nobetci(ortamKur(null, "jtn"));
  esit(cagrilar.length, 0, "pubDate yoksa tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: { fetch: () => Promise.resolve({ ok: false }) },
  });
  esit(cagrilar.length, 0, "RSS 404 verirse tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: { fetch: () => Promise.reject(new Error("ag yok")) },
  });
  esit(cagrilar.length, 0, "RSS istegi patlarsa tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        text: () => Promise.resolve(
          "<rss><item><pubDate>tarih degil</pubDate></item></rss>"),
      }),
    },
  });
  esit(cagrilar.length, 0, "tarih cozulemezse tetiklemiyor");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
}

kos();
