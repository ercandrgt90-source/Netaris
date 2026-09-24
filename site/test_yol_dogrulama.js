/* SAYAC YOLU ISTEMCIDEN GELIYOR -- DOGRULANMADAN YAZILAMAZ.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * `worker.js` kendi kuralini yaziyor (satir ~1471):
 *
 *     YOL DOGRULAMASI SART
 *     `yol` istemciden geliyor. Dogrulanmazsa herkes istedigi
 *     anahtari yazar ve tablo cop olur.
 *
 * Kural yaziliydi, ZORLANMIYORDU: `yolGecerli`, `YOL_BICIMI` ve
 * `SAYILAN_KOK` hicbir sinamada gecmiyordu. Desen gevsetilse --
 * buyuk harf eklense, sorgu dizesi kabul edilse ya da kok kontrolu
 * kalksa -- hicbir sey kirmizi yanmazdi.
 *
 * Bu, depoda tekrar eden kusur sinifi: kural yazilir, zorlayicisi
 * yazilmaz. Burada bedeli somut -- sayac tablosu uydurma anahtarlarla
 * doldurulabilir ve sitenin yayimladigi goruntulenme sayilari
 * guvenilmez olur. Uydurma bir sayi basmak bu sitede en agir ihlal.
 *
 * NE SINANIYOR
 * ------------
 * 1. Gercek icerik yollari KABUL EDILIYOR.
 * 2. Bicimi bozuk yollar REDDEDILIYOR (buyuk harf, sorgu, capa,
 *    cift egik cizgi, ust dizin, kapanis egik cizgisi yok).
 * 3. Icerik olmayan bolumler REDDEDILIYOR -- sayac her sayfada degil.
 * 4. Sayilan kokler bu dosyada ELLE yazili: liste daraltilirsa
 *    kirmizi yanar (korunan degeri korunan koddan okumak, korumayi
 *    hareketli hedefe cevirirdi).
 * 5. Dogrulayici bir sey GERCEKTEN reddediyor -- her seye true
 *    donen bir fonksiyon sinamayi gecemez.
 *
 * Kullanim:  node site/test_yol_dogrulama.js
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
   Yalnizca o blok cikariliyor, fonksiyonlarin kodu AYNEN kosuyor.
   Ayni kalip `test_giris_siniri.js` icinde de kullaniliyor. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

const ortam = {
  console: { log() {}, error() {} },
  TextEncoder, TextDecoder, Date, Math, Number, JSON, String, Promise,
  crypto: require("crypto").webcrypto,
  Response: class {},
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const yolGecerli = ortam.yolGecerli;

/* SAYILAN_KOK'E DOGRUDAN BAKILMIYOR -- DAVRANISA BAKILIYOR.
   VM baglaminda `const` bildirimleri baglam nesnesine cikmiyor
   (fonksiyon bildirimleri cikiyor), yani liste buradan okunamaz.
   Daha onemlisi: okunabilse bile okumamak gerekirdi. Liste
   daralirsa asagidaki "kabul: haber" / "kabul: analiz" iddialari
   zaten kirmizi yanar -- ic degiskene degil DAVRANISA bakan bir
   koruma, yeniden adlandirmaya da dayanir. */

console.log("\nDogrulayici yuklendi mi");
esit(typeof yolGecerli, "function", "`yolGecerli` disa aciliyor");

console.log("\nGercek icerik yollari KABUL");
[
  ["/haber/abd-sanayi-uretimi-yillik-1-42/", "haber"],
  ["/analiz/adese-2026-2-ceyrek/", "analiz"],
  ["/olay/turkiye-faiz-2026-09/", "olay"],
  ["/varlik/bist100/", "varlik"],
  ["/arastirmalar/", "arastirmalar kokun kendisi"],
].forEach(function (c) {
  esit(yolGecerli(c[0]), true, "kabul: " + c[1]);
});

console.log("\nBicimi bozuk yollar RED");
[
  ["/haber/ABD-Sanayi/", "buyuk harf"],
  ["/haber/x/?utm_source=a", "sorgu dizesi"],
  ["/haber/x/#bolum", "capa"],
  ["/haber//x/", "cift egik cizgi"],
  ["/haber/../gizli/", "ust dizin"],
  ["/haber/x", "kapanis egik cizgisi yok"],
  ["haber/x/", "basta egik cizgi yok"],
  ["/haber/" + "a".repeat(200) + "/", "cok uzun"],
  ["/haber/x_y/", "alt cizgi"],
  ["/haber/x y/", "bosluk"],
  ["", "bos dizge"],
].forEach(function (c) {
  esit(yolGecerli(c[0]), false, "red: " + c[1]);
});

console.log("\nDizge olmayan girdi RED");
[null, undefined, 42, {}, []].forEach(function (d, i) {
  esit(yolGecerli(d), false, "red: dizge degil (" + i + ")");
});

console.log("\nIcerik OLMAYAN bolumler RED");
/* Sayac her sayfada degil, yalnizca ICERIKTE tutuluyor. Kunye ya da
   gizlilik sayfasina sayac yazmak, tabloyu icerik disi anahtarlarla
   sismek olurdu. */
[
  ["/kunye/", "kunye"],
  ["/gizlilik/", "gizlilik"],
  ["/beslemeler/", "besleme defteri"],
  ["/panel/", "uyelik paneli"],
].forEach(function (c) {
  esit(yolGecerli(c[0]), false, "red: " + c[1]);
});

console.log("\nKONTROLUN KENDISI CALISIYOR MU");
/* Her seye `true` donen bir dogrulayici bu dosyayi GECEMEZ: yukarida
   reddedilmesi gereken 20 girdi var. Burada da tersini kanitliyoruz --
   fonksiyon gercekten AYRIM yapiyor, sabit cevap vermiyor. */
const kabul = yolGecerli("/haber/x/");
const ret = yolGecerli("/haber/X/");
esit(kabul !== ret, true, "dogrulayici AYRIM yapiyor (sabit cevap degil)");
esit(kabul, true, "gecerli yol gercekten kabul ediliyor");
esit(ret, false, "gecersiz yol gercekten reddediliyor");

console.log("");
if (kaldi.length) {
  console.log("DUSTU (" + kaldi.length + "): " + kaldi.join(" | "));
  process.exit(1);
}
console.log("TUM TESTLER GECTI (" + gecti + ")");
