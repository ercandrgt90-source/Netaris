/* "Veri akisi durdu" seridi -- sahte DOM ile.
 *
 * NEDEN VAR
 * ---------
 * OLCULDU (2026-09-14): site 1 Eylul 23:04'ten beri guncellenmiyordu.
 * On uc gun boyunca her otomasyon kosusu ayni testte dustu. Site 200
 * donuyor, sayfalar aciliyor, tarihler dogru yaziyordu -- ama rakamlar
 * on uc gunlukti ve hicbir yerde bunu SOYLEYEN bir sey yoktu.
 *
 * BU DOSYANIN KORUDUGU ASIL SEY
 * -----------------------------
 * Kararin TARAYICIDA verilmesi. Hat kilitlenince site yeniden
 * KURULMUYOR; kurulum aninda hesaplanacak bir "taze/bayat" bayragi son
 * saglikli kurulumun degerinde donar ve sonsuza dek "taze" der -- yani
 * tam ihtiyac duyuldugu anda susar.
 *
 * Asagidaki "ayni HTML, iki farkli saat" sinamasi bunu tutuyor: sayfa
 * degismeden, yalnizca zaman gectigi icin serit belirmeli.
 *
 * Kullanim:  node site/test_bayat_uyari.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function dogru(aciklama, kosul) {
  if (kosul) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
  }
}

// --- sablondaki satir ici betigi cikar ----------------------------
// KAYNAKTAN OKUNUYOR, KOPYALANMIYOR. Betigin kopyasini bu dosyaya
// yazsaydik sablon degistiginde sinama eski kodu olcmeye devam eder ve
// yesil kalirdi -- bu depoda "hicbir sey olcmeyen test" tuzagina
// defalarca dusuldu.
const SABLON = path.join(__dirname, "sablonlar", "temel.html");
const ham = fs.readFileSync(SABLON, "utf8");
const bloklar = ham.match(/<script>([\s\S]*?)<\/script>/g) || [];
const hedef = bloklar.filter((b) => b.indexOf("bayat-uyari") !== -1);
dogru("sablonda serit betigi bulundu", hedef.length === 1);
const BETIK = hedef.length
  ? hedef[0].replace(/^<script>/, "").replace(/<\/script>$/, "")
  : "";

// --- en kucuk sahte DOM -------------------------------------------
function ogeYap(sinif) {
  const o = {
    className: sinif || "",
    hidden: true,
    textContent: "",
    ozellikler: {},
    cocuklar: [],
    getAttribute: (k) => (k in o.ozellikler ? o.ozellikler[k] : null),
    setAttribute: (k, v) => { o.ozellikler[k] = v; },
    querySelector: (s) => {
      if (s[0] !== ".") return null;
      const ad = s.slice(1);
      for (const c of o.cocuklar) if (c.className === ad) return c;
      return null;
    },
  };
  return o;
}

/** Sayfayi kurar ve betigi `simdi` anında calistirir. */
function calistir({ uretim, esik, simdi, serit = true }) {
  const kutu = ogeYap("bayat-uyari");
  const metin = ogeYap("bayat-uyari-metin");
  kutu.cocuklar.push(metin);
  if (uretim !== null) kutu.setAttribute("data-uretim", uretim);
  if (esik !== null) kutu.setAttribute("data-esik", String(esik));

  // Saat KONTROL EDILEBILIR olmali: sinama "13 gun sonra" durumunu
  // gercekten 13 gun bekleyerek kuramaz.
  const SahteDate = class extends Date {};
  SahteDate.now = () => simdi;
  SahteDate.parse = Date.parse;

  const ortam = {
    document: {
      querySelector: (s) => (serit && s === ".bayat-uyari" ? kutu : null),
    },
    Date: SahteDate,
    Math: Math,
    parseFloat: parseFloat,
    isNaN: isNaN,
  };
  vm.createContext(ortam);
  vm.runInContext(BETIK, ortam);
  return { kutu: kutu, metin: metin };
}

const T = Date.parse("2026-09-01T23:00:00Z");
const SAAT = 3600000;

console.log("\nTaze sayfada serit GORUNMUYOR");
// Serit normal islemede HIC gorunmemeli: gereksiz cikan bir uyari,
// gercek olanini da inandiriciliktan dusurur.
dogru("1 saatlik icerik -> gizli",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 1 * SAAT })
    .kutu.hidden === true);
dogru("11 saatlik icerik -> gizli",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 11 * SAAT })
    .kutu.hidden === true);
// TAM ESIKTE gizli: olcut "asarsa", "ulasirsa" degil.
dogru("tam esikte (12 saat) -> gizli",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 12 * SAAT })
    .kutu.hidden === true);

console.log("\nAkis durunca serit BELIRIYOR");
const _13s = calistir({
  uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 13 * SAAT });
dogru("13 saat -> gorunur", _13s.kutu.hidden === false);
dogru("13 saat -> sure SAAT olarak yaziliyor",
  _13s.metin.textContent.indexOf("13 saat") !== -1);

const _13g = calistir({
  uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 13 * 24 * SAAT });
dogru("13 gun -> gorunur", _13g.kutu.hidden === false);
// Uzun duraklamada "312 saat" demek okura hicbir sey anlatmaz.
dogru("13 gun -> sure GUN olarak yaziliyor",
  _13g.metin.textContent.indexOf("13 gün") !== -1);
dogru("metin son guncelleme tarihini iceriyor",
  _13g.metin.textContent.indexOf("2026") !== -1);
dogru("metin rakamlarin eskimis olabilecegini soyluyor",
  _13g.metin.textContent.indexOf("yansıtmıyor olabilir") !== -1);

console.log("\nKARAR SAYFADA DEGIL, ACILIS ANINDA");
// BU DOSYANIN ASIL SINAMASI. Hat kilitlenince site yeniden kurulmuyor;
// kurulumda hesaplanan bir bayrak sonsuza dek "taze" derdi. Ayni HTML,
// iki farkli saat -> iki farkli sonuc olmali.
const ayniSayfa = { uretim: "2026-09-01T23:00:00Z", esik: 12 };
const erken = calistir(Object.assign({ simdi: T + SAAT }, ayniSayfa));
const gec = calistir(Object.assign({ simdi: T + 40 * SAAT }, ayniSayfa));
dogru("ayni HTML erken acilista gizli", erken.kutu.hidden === true);
dogru("ayni HTML gec acilista gorunur", gec.kutu.hidden === false);
dogru("karar sayfaya GOMULU DEGIL (iki sonuc farkli)",
  erken.kutu.hidden !== gec.kutu.hidden);

console.log("\nEsik SAYFADAN geliyor, betige gomulu degil");
// `insa.BAYAT_UYARI_SAAT` tek kaynak. Betik 12'yi kendi icinde
// tasisaydi esigi degistiren kisi hicbir sey degismedigini gorurdu --
// bu depoda "ayni karari veren iki yer" hatasi defalarca yasandi.
dogru("esik 1 iken 2 saatlik icerik -> gorunur",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 1, simdi: T + 2 * SAAT })
    .kutu.hidden === false);
dogru("esik 99 iken 40 saatlik icerik -> gizli",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 99, simdi: T + 40 * SAAT })
    .kutu.hidden === true);

console.log("\nBozuk girdide sessiz kaliyor");
// Uyarinin kendisi hataya donusmemeli: yanlis ya da eksik veri
// yuzunden HER sayfada serit gostermek, sorunu ikiye katlar.
dogru("zaman damgasi yoksa -> gizli",
  calistir({ uretim: null, esik: 12, simdi: T + 99 * SAAT })
    .kutu.hidden === true);
dogru("zaman damgasi bozuksa -> gizli",
  calistir({ uretim: "bozuk", esik: 12, simdi: T + 99 * SAAT })
    .kutu.hidden === true);
dogru("esik yoksa -> gizli",
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: null, simdi: T + 99 * SAAT })
    .kutu.hidden === true);
try {
  calistir({ uretim: "2026-09-01T23:00:00Z", esik: 12, simdi: T + 99 * SAAT,
             serit: false });
  dogru("serit ogesi yoksa cokmuyor", true);
} catch (e) {
  dogru("serit ogesi yoksa cokmuyor (" + e.message + ")", false);
}

console.log("");
for (const k of kaldi) console.log("  KALDI " + k);
console.log(gecti + " gecti, " + kaldi.length + " kaldi");
process.exit(kaldi.length ? 1 : 0);
