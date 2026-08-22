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

/* ------------------------------------------------------------------
   YEREL PAYLASIM SAYFASI -- `navigator.share`.
   ------------------------------------------------------------------
   Telefonda bes ayri dugme yerine isletim sisteminin kendi paylasim
   sayfasi aciliyor: okurun KURULU uygulamalari cikiyor.

   Bir sey daha cozuyor: INSTAGRAM'IN WEB PAYLASIM ADRESI YOK. Bir web
   sayfasindan Instagram'a baglanti paylasilamaz; yerel sayfa bunu
   isletim sistemi uzerinden cozuyor.

   EN ONEMLI SINAMA SONUNCUSU: destek yoksa HICBIR SEY DEGISMEMELI.
   Dugmeyi acip `navigator.share` cagrilamazsa okur tiklar ve hicbir
   sey olmaz -- calismayan bir dugme, olmayan dugmeden kotudur ve ayni
   gerekce `paylas.js` icindeki kopyalama dugmesinde de yazili.
   ------------------------------------------------------------------ */
console.log("\nYerel paylasim sayfasi\n");

function sahteDom(destek, darEkran) {
  const dugme = { hidden: true, _oz: {
    "data-baslik": "Baslik", "data-metin": "Metin",
    "data-adres": "https://netaris.net/haber/x/" },
    getAttribute(a) { return this._oz[a] || null; } };
  const seri = { hidden: false };
  dugme.parentNode = { querySelector: (s) =>
    (s === ".sayfa-paylas-dugmeler" ? seri : null) };

  const belge = {
    createElement: () => ({ textContent: "", innerHTML: "" }),
    addEventListener: () => {},
    querySelectorAll: (s) =>
      (s === "[data-paylas-yerel]" ? [dugme] : []),
    readyState: "complete",
  };
  const p = {
    document: belge,
    location: { origin: "https://netaris.net", pathname: "/haber/x/" },
    setTimeout: () => {},
    navigator: destek ? { share: () => Promise.resolve() } : {},
    matchMedia: darEkran === null
      ? undefined
      : () => ({ matches: darEkran }),
  };
  p.window = p;
  vm.createContext(p);
  vm.runInContext(fs.readFileSync(
    path.join(__dirname, "statik", "paylas.js"), "utf8"), p);
  return { dugme, seri };
}

{
  const a = sahteDom(true, true);
  esit(a.dugme.hidden, false, "destek + dar ekran: yerel dugme ACILIYOR");
  esit(a.seri.hidden, true, "yerel dugme acilinca baglanti serisi gizleniyor");
}
{
  const b = sahteDom(true, false);
  esit(b.dugme.hidden, true, "genis ekranda yerel dugme ACILMIYOR");
  esit(b.seri.hidden, false, "genis ekranda seri duruyor");
}
{
  // EN ONEMLISI: destek yoksa hicbir sey degismemeli.
  const c = sahteDom(false, true);
  esit(c.dugme.hidden, true, "navigator.share YOKSA dugme acilmiyor");
  esit(c.seri.hidden, false, "destek yoksa seri OLDUGU GIBI duruyor");
}
{
  // `matchMedia` olmayan ortamda da dusmemeli.
  const d = sahteDom(true, null);
  esit(d.dugme.hidden, true, "matchMedia yoksa dugme acilmiyor");
  esit(d.seri.hidden, false, "matchMedia yoksa seri duruyor");
}

console.log("");
if (kaldi.length) { console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti"); process.exit(1); }
console.log("TUM TESTLER GECTI (" + gecti + ")");
