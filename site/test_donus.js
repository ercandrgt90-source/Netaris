/* Giris sonrasi donus adresi.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * Iki ayri sey siniyor ve ikisi de SESSIZ:
 *
 * 1. FUNI SIZINTISI. Haber sayfasindaki "Senaryo yaz" dugmesi
 *    `/panel/?senaryo=/haber/xxx/&baslik=...` adresine gidiyor. Okur
 *    oturum acmamissa giris yapiyor ve `location.href = "/panel/"`
 *    calisiyordu -- SORGU PARAMETRELERI DUSUYORDU.
 *
 *    Sonuc: okur bir haber icin senaryo yazmaya geldi, BOS BIR PANELE
 *    dustu. Hicbir hata gorunmuyordu; giris basarili, panel aciliyor,
 *    her sey "calisiyor". Yalnizca okurun NIYETI kayboluyordu.
 *
 * 2. ACIK YONLENDIRME. Donus adresi ADRESTEN geliyor, yani saldirgan
 *    kontrolunde. Dogrudan kullanilirsa
 *    `/giris/?donus=https://kotu.example/` baglantisi okuru giris
 *    yaptiktan sonra baska siteye atardi.
 *
 *    Ikinci sinama grubu bu yuzden daha uzun: sizinti bir kayip,
 *    acik yonlendirme bir GUVENLIK acigi.
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

function ortam(arama, yol) {
  const p = {
    location: { pathname: yol || "/panel/", search: arama || "", hash: "" },
    URLSearchParams: URLSearchParams,
    encodeURIComponent: encodeURIComponent,
  };
  p.window = p;
  vm.createContext(p);
  vm.runInContext(fs.readFileSync(
    path.join(__dirname, "statik", "donus.js"), "utf8"), p);
  return p.NetarisDonus;
}

console.log("\nDonus adresi -- funi sizintisi\n");
{
  const D = ortam("?donus=%2Fpanel%2F%3Fsenaryo%3D%2Fhaber%2Ffed%2F");
  esit(D.hedef(), "/panel/?senaryo=/haber/fed/",
       "capali panel adresi KORUNUYOR");
}
{
  const D = ortam("");
  esit(D.hedef(), "/panel/", "donus yoksa varsayilan panel");
}
{
  // Giris baglantisi su anki adresi tasimali.
  const D = ortam("?senaryo=%2Fhaber%2Ffed%2F", "/panel/");
  esit(D.suanki(), "/panel/?senaryo=%2Fhaber%2Ffed%2F",
       "su anki adres sorguyla birlikte");

  const a = {
    _h: "/giris/",
    getAttribute() { return this._h; },
    setAttribute(_, v) { this._h = v; },
  };
  D.baglantiyaEkle(a);
  esit(a._h.indexOf("donus=") !== -1, true,
       "giris baglantisina donus ekleniyor");
  esit(decodeURIComponent(a._h.split("donus=")[1]),
       "/panel/?senaryo=%2Fhaber%2Ffed%2F",
       "eklenen donus SU ANKI adres");

  // Iki kez cagrilirsa ikinci kez EKLEMEMELI -- yoksa adres her
  // cagrida uzar ve ic ice donus zinciri olusur.
  D.baglantiyaEkle(a);
  esit(a._h.split("donus=").length, 2, "ikinci cagri TEKRAR EKLEMIYOR");
}

console.log("\nAcik yonlendirme -- dis adres REDDEDILIYOR\n");
{
  const D = ortam("");
  const KOTU = [
    "https://kotu.example/",
    "http://kotu.example/",
    "//kotu.example/",            // protokol-goreli: tarayici dis adres cozer
    "/\\kotu.example/",           // ters egik cizgi de oyle
    "javascript:alert(1)",
    "data:text/html,x",
    "kotu.example/",              // egik cizgiyle baslamiyor
    "",
  ];
  for (const y of KOTU) {
    esit(D.guvenli(y), "/panel/", "reddediliyor: " + JSON.stringify(y));
  }

  // Ayni sitedeki yollar GECMELI.
  for (const y of ["/panel/", "/panel/?senaryo=/haber/x/",
                   "/topluluk/", "/haber/fed/#senaryo-3"]) {
    esit(D.guvenli(y), y, "kabul: " + y);
  }
}
{
  // Adresten gelen DIS donus da varsayilana dusmeli -- `hedef`
  // `guvenli`den geciyor, bu zincir kirilmamali.
  const D = ortam("?donus=https%3A%2F%2Fkotu.example%2F");
  esit(D.hedef(), "/panel/", "adresteki DIS donus varsayilana dusuyor");
}
{
  const D = ortam("?donus=%2F%2Fkotu.example%2F");
  esit(D.hedef(), "/panel/", "protokol-goreli donus varsayilana dusuyor");
}

console.log("");
if (kaldi.length) {
  console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti");
  process.exit(1);
}
console.log("TUM TESTLER GECTI (" + gecti + ")");
