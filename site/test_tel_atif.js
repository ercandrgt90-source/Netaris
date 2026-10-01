/* Tel: uctan gelen ogede ATIF -- basilmis ogeyle AYNI.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * `ticari=True` olan kaynakta sayfada kurum adi VE kaynaga baglanti
 * gosterilmek zorunda (haber_botu/kaynak/besleme.py). Bu kural
 * simdiye kadar iki yerde tutuluyordu:
 *
 *   `site/test_ticari_atif.py`  -- BASILMIS HTML'i denetliyor
 *   sema `CHECK` kisitlari      -- veritabanina giren satiri
 *
 * Tel ucuncu bir yol acti: ogeler sayfaya ISTEMCIDE ekleniyor. O
 * yol yukaridaki iki korumanin da DISINDA -- basilmis HTML'de
 * gorunmuyor, veritabanindan gecse bile isaretlemesi burada
 * uretiliyor. Koruma olmadan atif sessizce dusebilirdi: sayfa
 * duzgun gorunur, yalnizca kunye yoktur.
 *
 * Calistirma:  node site/test_tel_atif.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function dogru(kosul, aciklama) {
  if (kosul) { gecti++; console.log("  gecti  " + aciklama); }
  else { kaldi.push(aciklama); console.log("  KALDI  " + aciklama); }
}

function esit(bulunan, beklenen, aciklama) {
  const a = JSON.stringify(bulunan), b = JSON.stringify(beklenen);
  if (a === b) { gecti++; console.log("  gecti  " + aciklama); }
  else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + b + "\n         bulunan : " + a);
  }
}

/* --- Kucuk sahte DOM -------------------------------------------
 *
 * `textContent` YAZINCA `innerHTML` KACIRILMIS HALE GELMELI.
 *
 * `tel.js` metni tam olarak boyle kaciriyor: bos bir `div` yaratip
 * `textContent` yaziyor ve `innerHTML` okuyor. Ilk surumde bu sahte
 * DOM'da `textContent` duz bir alandi ve `innerHTML` bos kaliyordu --
 * yani `metin()` HER SEY icin bos donuyordu.
 *
 * Uc sinama kirmizi yandi, ama tehlikeli olan DORDUNCUSUYDU:
 * "baslikta `<img` yok" sinamasi GECTI -- cunku ortada hicbir sey
 * yoktu. Bos cikti, kacirilmis cikti gibi gorunur. Olcum araci
 * once KENDINI dogrulamali; bu dosyada `kacirilmis hali basildi`
 * sinamasi tam da onun icin var.
 */
function kacir(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function sahteOge(etiket) {
  return {
    etiket,
    className: "",
    innerHTML: "",
    set textContent(d) { this.innerHTML = kacir(d); },
    get textContent() { return this.innerHTML; },
    cocuklar: [],
    ozellik: {},
    setAttribute(a, d) { this.ozellik[a] = String(d); },
    removeAttribute(a) { delete this.ozellik[a]; },
    getAttribute(a) { return a in this.ozellik ? this.ozellik[a] : null; },
    appendChild(c) { this.cocuklar.push(c); return c; },
    insertBefore(c, _r) { this.cocuklar.unshift(c); return c; },
    querySelector() { return null; },
    get firstChild() { return this.cocuklar[0] || null; },
  };
}

function ortamKur(ogeler, uretim) {
  const kap = sahteOge("div");
  kap.setAttribute("data-tel-uretim", uretim);
  kap.setAttribute("hidden", "");
  const liste = sahteOge("ul");

  const belge = {
    querySelector(sec) {
      if (sec === "[data-tel-kap]") return kap;
      if (sec === '[data-akis-kap="rutin"]') return liste;
      return null;
    },
    createElement: sahteOge,
    createDocumentFragment() {
      const f = sahteOge("#fragment");
      return f;
    },
  };

  let istenenAdres = "";
  const ortam = {
    document: belge,
    console: { log() {}, error() {} },
    Date, String, Number, JSON, Promise, RegExp, Boolean, Array, Object,
    isNaN, encodeURIComponent,
    fetch(u) {
      istenenAdres = String(u);
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ogeler }),
      });
    },
  };
  ortam.globalThis = ortam;
  vm.createContext(ortam);
  return { ortam, kap, liste, adres: () => istenenAdres };
}

const KAYNAK = fs.readFileSync(
  path.join(__dirname, "statik", "tel.js"), "utf8");

/* Fragment `insertBefore` ile tek parca giriyor; icindekileri duz
   listeye cevirip inceliyoruz. */
function basilanlar(liste) {
  const cikti = [];
  liste.cocuklar.forEach(function (c) {
    if (c.etiket === "#fragment") cikti.push.apply(cikti, c.cocuklar);
    else cikti.push(c);
  });
  return cikti;
}

const TICARI = {
  baslik: "US CPI YoY Actual 3.1%",
  baslik_kaynak: "US CPI YoY Actual 3.1%",
  cevrildi: false,
  kurum: "FinancialJuice",
  kurum_tam: "FinancialJuice",
  adres: "https://www.financialjuice.com/News/1/a.aspx",
  konu: "Enflasyon",
  ticari: true,
  tarih: "2026-09-30T11:31:51Z",
};

async function kos() {
  console.log("\nTicari ogede kunye VE baglanti");
  let k = ortamKur([TICARI], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  let ogeler = basilanlar(k.liste);
  esit(ogeler.length, 1, "oge basildi");
  const h = ogeler[0].innerHTML;
  dogru(h.indexOf('class="rozet rozet-kaynak-bag"') !== -1,
        "kunye BAGLANTI olarak basildi (rozet-kaynak-bag)");
  dogru(h.indexOf('href="' + TICARI.adres + '"') !== -1,
        "kaynak adresi href'te");
  dogru(h.indexOf('rel="nofollow noopener"') !== -1,
        "rel basilmis ogeyle ayni");
  dogru(h.indexOf("FinancialJuice") !== -1, "kurum adi gorunuyor");
  dogru(h.indexOf("gundem-baslik") !== -1, "baslik sinifi basilmisla ayni");

  console.log("\nBaglantisiz oge HIC BASILMIYOR");
  const baglantisiz = Object.assign({}, TICARI, { adres: "" });
  k = ortamKur([baglantisiz], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  esit(basilanlar(k.liste).length, 0, "baglantisiz oge basilmadi");

  console.log("\nKunyesiz oge HIC BASILMIYOR");
  const kunyesiz = Object.assign({}, TICARI, { kurum: "" });
  k = ortamKur([kunyesiz], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  esit(basilanlar(k.liste).length, 0, "kunyesiz oge basilmadi");

  console.log("\njavascript: adresi REDDEDILIYOR");
  const kotu = Object.assign({}, TICARI,
    { adres: "javascript:alert(1)" });
  k = ortamKur([kotu], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  esit(basilanlar(k.liste).length, 0, "http(s) olmayan adres basilmadi");

  console.log("\nIsaretleme kacisi");
  const zararli = Object.assign({}, TICARI,
    { baslik: '<img src=x onerror=alert(1)>' });
  k = ortamKur([zararli], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  const z = basilanlar(k.liste)[0].innerHTML;
  dogru(z.indexOf("<img") === -1, "baslikteki isaretleme kacirildi");
  dogru(z.indexOf("&lt;img") !== -1, "kacirilmis hali basildi");

  console.log("\nMakine cevirisi BILDIRILIYOR");
  const cevrili = Object.assign({}, TICARI,
    { baslik: "ABD TÜFE yıllık %3,1", cevrildi: true });
  k = ortamKur([cevrili], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  const c = basilanlar(k.liste)[0].innerHTML;
  dogru(c.indexOf("makine çevirisi") !== -1,
        "ceviri oldugu okura SOYLENIYOR");

  console.log("\nYalnizca insadan YENI oge isteniyor");
  k = ortamKur([], "2026-09-30T09:00:00Z");
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  dogru(k.adres().indexOf("sonra=") !== -1,
        "istek `sonra` parametresi tasiyor (ayni haber iki kez cikmasin)");
  dogru(k.adres().indexOf("2026-09-30T09%3A00%3A00Z") !== -1,
        "sayfanin uretim ani gonderiliyor");

  /* URETILEN HER SINIF CSS'TE TANIMLI OLMALI.
     Uctan gelen ogeler sayfaya ISTEMCIDE ekleniyor; bir sinif adi
     degisirse ya da yeni bir sinif eklenip bicimi yazilmazsa oge
     BICIMSIZ basilir. Sayfa calisir gorunur, yalnizca oge kirik
     durur -- yani kusur sessizdir. Hicbir baska sinama bunu
     gormezdi: isaretleme dogru, bicim yok. */
  console.log("\nUretilen siniflar bicimlendirilmis");
  const css = fs.readFileSync(
    path.join(__dirname, "statik", "stil.css"), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "");
  const sablon = fs.readFileSync(
    path.join(__dirname, "sablonlar", "gundem.html"), "utf8");
  const siniflar = new Set();
  for (const m of KAYNAK.matchAll(/class="([^"]+)"/g)) {
    m[1].split(/\s+/).forEach((x) => x && siniflar.add(x));
  }
  for (const m of KAYNAK.matchAll(/className\s*=\s*"([^"]+)"/g)) {
    m[1].split(/\s+/).forEach((x) => x && siniflar.add(x));
  }
  for (const m of sablon.matchAll(/class="(tel[^"]*)"/g)) {
    m[1].split(/\s+/).forEach((x) => x && siniflar.add(x));
  }
  dogru(siniflar.size >= 10,
        `uretilen sinif sayisi olculdu (${siniflar.size})`);
  const eksik = [];
  for (const s of siniflar) {
    const kalip = new RegExp("\\." + s.replace(/[-]/g, "\\-")
                             + "[\\s,{:.\\[]");
    if (!kalip.test(css)) eksik.push(s);
  }
  esit(eksik, [], "her sinif stil.css'te tanimli");

  console.log("\nTel dusse sayfa bozulmuyor");
  k = ortamKur([], "2026-09-30T09:00:00Z");
  k.ortam.fetch = function () { return Promise.reject(new Error("ag")); };
  vm.runInContext(KAYNAK, k.ortam);
  await new Promise((r) => setTimeout(r, 10));
  esit(basilanlar(k.liste).length, 0, "hata yutuldu, liste bos kaldi");
}

kos().then(() => {
  if (kaldi.length) {
    console.log("\ntel atfi: " + kaldi.length + " KALDI");
    process.exit(1);
  }
  console.log("\ntel atfi: " + gecti + " dogrulama gecti");
}).catch((e) => { console.error(e); process.exit(1); });
