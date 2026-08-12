/* Senaryo paylasim baglantilari.
 *
 * Paylasim adresi SESSIZCE bozulabilecek bir sey: dugme yerinde durur,
 * tiklanir, yanlis sayfaya gider. Kimse fark etmez. Bu yuzden adres
 * kurulumu sinaniyor.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

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

function ortam(yol) {
  const belge = {
    createElement: () => {
      const o = { textContent: "", get innerHTML() {
        return String(o.textContent)
          .replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      } };
      return o;
    },
    addEventListener: () => {},
  };
  const p = { document: belge, location: { origin: "https://ornek.test", pathname: yol },
              setTimeout: () => {}, navigator: {} };
  p.window = p;
  vm.createContext(p);
  vm.runInContext(fs.readFileSync(
    path.join(__dirname, "statik", "paylas.js"), "utf8"), p);
  return p.NetarisPaylas;
}

console.log("\nSenaryo paylasimi -- adres kurulumu\n");

{
  const P = ortam("/haber/fed-faizi-sabit-tuttu/");
  // Haber sayfasinda `capa` GONDERILMIYOR -- adres bulunulan sayfa olmali.
  esit(P.adres({ id: 42, kosul: "a", sonuc: "b" }),
       "https://ornek.test/haber/fed-faizi-sabit-tuttu/#senaryo-42",
       "capa yoksa BULUNULAN sayfa kullaniliyor");
}
{
  const P = ortam("/topluluk/");
  esit(P.adres({ id: 7, capa: "/haber/brent-geriledi/" }),
       "https://ornek.test/haber/brent-geriledi/#senaryo-7",
       "capa varsa o sayfaya gidiyor");
  esit(P.adres({ id: 9 }),
       "https://ornek.test/topluluk/#senaryo-9",
       "topluluk sayfasinda capa yoksa topluluk kaliyor");
  esit(P.adres({ id: 3, capa: "https://baska.test/x" }),
       "https://baska.test/x#senaryo-3",
       "mutlak capa AYNEN korunuyor");

  const h = P.html({ id: 5, kosul: "Hürmüz kapanırsa", sonuc: "navlun sert artar" });
  esit(h.indexOf("x.com/intent/post") !== -1, true, "X baglantisi kuruluyor");
  esit(h.indexOf("linkedin.com/sharing/share-offsite") !== -1, true,
       "LinkedIn baglantisi kuruluyor");
  esit(h.indexOf(encodeURIComponent("Hürmüz kapanırsa → navlun sert artar")) !== -1,
       true, "X metni senaryonun KENDISI -- yalnizca adres degil");
  esit(h.indexOf('rel="noopener noreferrer"') !== -1, true,
       "disari acilan baglantida noopener");

  // X siniri: 280 karakterlik gonderide adres ~23 karakter yiyor.
  const uzun = "x".repeat(400);
  const m = decodeURIComponent(
    P.html({ id: 1, kosul: uzun, sonuc: uzun })
      .match(/intent\/post\?text=([^&]+)/)[1]);
  esit(m.length <= 200, true, "uzun senaryo 200 karaktere kirpiliyor");
  esit(m.slice(-1), "…", "kirpilan metin uc nokta ile bitiyor");
}

console.log("");
if (kaldi.length) { console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti"); process.exit(1); }
console.log("TUM TESTLER GECTI (" + gecti + ")");
