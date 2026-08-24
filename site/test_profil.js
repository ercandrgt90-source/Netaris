/* Profil alanlarinin temizlenmesi ve dogrulanmasi.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * Bu dort alan KUNYEDE beliriyor: okurun bir yaziyi kimin ve NE
 * SIFATLA yazdigini gordugu yer. Yani buraya giren metin, sitenin en
 * cok guvenilmesi gereken satirini olusturuyor.
 *
 * Iki ayri risk siniyor:
 *
 * 1. GORUNMEZ KARAKTER. Sifir genislikli bosluk (U+200B) ve yon
 *    degistirici (U+202E) bir adin icine gomulebiliyor. Ekranda
 *    "Ahmet" yazan bir ad kopyalandiginda baska bir sey oluyor;
 *    yon degistirici ise satirin geri kalanini ters cevirebiliyor.
 *    Ikisi de HTML kacislariyla ENGELLENMEZ -- kacis `<` ve `&`
 *    icindir, gecerli ama gorunmez bir karakter icin degil.
 *
 * 2. SATIR SONU. Kunye "Necati Ercan\nDurgut" yazildiginda HTML'de
 *    tek satir gorunur ama RSS'te, `og:title` icinde ve arama
 *    sonucunda satir kirilir. Yani sorun ancak sayfanin DISINDA
 *    ortaya cikar ve gozle bakarak fark edilmez.
 *
 * `profilDogrula` bu yuzden ayri ve saf bir fonksiyon: veritabani ya
 * da istek nesnesi olmadan cagrilabiliyor. Uc noktanin icinde
 * kalsaydi sinamak icin sahte bir D1 kurmak gerekirdi ve buyuk
 * olasilikla hic sinanmazdi.
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
   Yalnizca o blok cikariliyor, fonksiyonlarin kodu AYNEN kosuyor --
   yani sinama gercek kaynagi sinamis oluyor. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

const ortam = {
  console, crypto: require("crypto").webcrypto, TextEncoder, TextDecoder,
  atob: function (s) { return Buffer.from(s, "base64").toString("binary"); },
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const dogrula = ortam.profilDogrula;

console.log("\nProfil dogrulama -- alan yuklendi mi\n");
esit(typeof dogrula, "function", "profilDogrula bulundu");

console.log("\nAd ZORUNLU, digerleri degil\n");
{
  const s = dogrula({ ad: "Necati", soyad: "Durgut" });
  esit(s.tamam, true, "ad ve soyad yeterli");
  esit(s.deger.unvan, "", "unvan bos kalabiliyor");
  esit(s.deger.hakkinda, "", "hakkinda bos kalabiliyor");
}
esit(dogrula({ ad: "" }).tamam, false, "bos ad reddediliyor");
esit(dogrula({ ad: "A" }).tamam, false, "tek harflik ad reddediliyor");
esit(dogrula({}).tamam, false, "alan hic yoksa reddediliyor");
esit(dogrula({ ad: 42 }).tamam, false, "sayi gonderilirse reddediliyor");
esit(dogrula({ ad: null }).tamam, false, "null reddediliyor");

/* Ret SEBEBI donuyor: "Kaydedilemedi" diyen bir form, kullaniciyi
   hangi alani duzeltecegini bilmeden birakir. */
esit(typeof dogrula({ ad: "" }).sebep, "string", "ret sebebi metin olarak donuyor");

console.log("\nSoyad AYRI tutuluyor -- tek alanda birlestirilmiyor\n");
{
  const s = dogrula({ ad: "Necati Ercan", soyad: "Durgut" });
  esit(s.deger.ad, "Necati Ercan", "ad oldugu gibi kaliyor");
  esit(s.deger.soyad, "Durgut", "soyad ayri duruyor");
}

console.log("\nGORUNMEZ KARAKTERLER temizleniyor\n");
{
  /* U+200B sifir genislikli bosluk: ekranda hicbir sey gorunmuyor. */
  const s = dogrula({ ad: "Ah​met", soyad: "Y‍ilmaz" });
  esit(s.deger.ad, "Ahmet", "sifir genislikli bosluk ADdan siliniyor");
  esit(s.deger.soyad, "Yilmaz", "sifir genislikli birlestirici siliniyor");
}
{
  /* U+202E yon degistirici: satirin kalanini ters cevirebiliyor. */
  const s = dogrula({ ad: "Ali‮", unvan: "Analist‭" });
  esit(s.deger.ad, "Ali", "yon degistirici ADdan siliniyor");
  esit(s.deger.unvan, "Analist", "yon degistirici UNVANdan siliniyor");
}
{
  const s = dogrula({ ad: "﻿Mehmet" });
  esit(s.deger.ad, "Mehmet", "bayt sirasi isareti siliniyor");
}

console.log("\nTEK SATIRLIK alanlarda satir sonu bosluga cevriliyor\n");
{
  const s = dogrula({ ad: "Necati\nErcan", soyad: "Dur\tgut" });
  esit(s.deger.ad, "Necati Ercan", "ADdaki satir sonu bosluk oluyor");
  esit(s.deger.soyad, "Dur gut", "SOYADdaki sekme bosluk oluyor");
}
{
  const s = dogrula({ ad: "  Necati   Ercan  " });
  esit(s.deger.ad, "Necati Ercan", "bas/son bosluk ve tekrar temizleniyor");
}

console.log("\nHAKKINDA cok satirli -- satir sonu KORUNUYOR\n");
{
  const s = dogrula({ ad: "Ali", hakkinda: "Birinci satir.\nIkinci satir." });
  esit(s.deger.hakkinda, "Birinci satir.\nIkinci satir.",
       "iki satir korunuyor");
}
{
  /* Ard arda cok bos satir sayfada kocaman bir bosluk demek. */
  const s = dogrula({ ad: "Ali", hakkinda: "A.\n\n\n\n\nB." });
  esit(s.deger.hakkinda, "A.\n\nB.", "ucten fazla bos satir buduluyor");
}
{
  const s = dogrula({ ad: "Ali", hakkinda: "A.\r\nB." });
  esit(s.deger.hakkinda, "A.\nB.", "windows satir sonu normallestiriliyor");
}

console.log("\nUZUNLUK sinirlari uygulaniyor\n");
{
  const s = dogrula({
    ad: "a".repeat(200),
    soyad: "b".repeat(200),
    unvan: "c".repeat(200),
    hakkinda: "d".repeat(2000),
  });
  esit(s.deger.ad.length, 60, "ad 60 karaktere kirpiliyor");
  esit(s.deger.soyad.length, 60, "soyad 60 karaktere kirpiliyor");
  esit(s.deger.unvan.length, 80, "unvan 80 karaktere kirpiliyor");
  esit(s.deger.hakkinda.length, 600, "hakkinda 600 karaktere kirpiliyor");
}

console.log("\nTurkce harfler BOZULMUYOR\n");
{
  const s = dogrula({ ad: "Şüheda", soyad: "Çağlayanoğlu", unvan: "İktisatçı" });
  esit(s.deger.ad, "Şüheda", "Ş ve ü korunuyor");
  esit(s.deger.soyad, "Çağlayanoğlu", "Ç, ğ ve o korunuyor");
  esit(s.deger.unvan, "İktisatçı", "İ ve ç korunuyor");
}

console.log("\nHTML KACISI BU KATMANDA YAPILMIYOR -- metin oldugu gibi saklaniyor\n");
{
  /* Kacis GOSTERIM katmaninin isi: panel `textContent` kullaniyor,
     Jinja otomatik kaciriyor. Burada kacirmak CIFT KACIS uretir ve
     kunyede "&amp;" gorunurdu. Saklanan sey KULLANICININ YAZDIGI. */
  const s = dogrula({ ad: "Ali & Veli", unvan: "<analist>" });
  esit(s.deger.ad, "Ali & Veli", "ampersan oldugu gibi saklaniyor");
  esit(s.deger.unvan, "<analist>", "acili parantez oldugu gibi saklaniyor");
}

const avatar = ortam.avatarDogrula;

/* JPEG ve PNG sihirli baytlari, base64'e cevrilmis hali. */
function b64(baytlar, ek) {
  const b = Buffer.concat([Buffer.from(baytlar),
                           Buffer.from(ek || "x".repeat(64))]);
  return b.toString("base64");
}
const JPEG = b64([0xFF, 0xD8, 0xFF]);
const PNG = b64([0x89, 0x50, 0x4E, 0x47]);

console.log("\nAvatar -- bicim ve BOS DEGER\n");
esit(typeof avatar, "function", "avatarDogrula bulundu");
esit(avatar("").tamam, true, "bos dize gecerli (KALDIRMA demek)");
esit(avatar("").deger, "", "bos dize bos donuyor");
esit(avatar("   ").tamam, true, "yalnizca bosluk da kaldirma sayiliyor");
esit(avatar(null).tamam, false, "null reddediliyor");
esit(avatar(123).tamam, false, "sayi reddediliyor");

console.log("\nGecerli JPEG ve PNG kabul ediliyor\n");
esit(avatar("data:image/jpeg;base64," + JPEG).tamam, true, "JPEG kabul");
esit(avatar("data:image/png;base64," + PNG).tamam, true, "PNG kabul");

console.log("\nSVG ACIKCA REDDEDILIYOR\n");
/* SVG bir BELGE bicimi; icine <script> konabiliyor. `<img src>`
   icinde calismasa da dogrudan acildiginda calisir. Depoladigimiz
   seyin calistirilabilir olmamasi, gosterildigi yere bagli olmamali. */
esit(avatar("data:image/svg+xml;base64," + Buffer.from(
  "<svg onload=alert(1)></svg>").toString("base64")).tamam, false,
  "SVG reddediliyor");
esit(avatar("data:text/html;base64," + Buffer.from("<b>x</b>")
  .toString("base64")).tamam, false, "HTML reddediliyor");
esit(avatar("https://baska.example/a.jpg").tamam, false,
     "dis adres reddediliyor");
esit(avatar("javascript:alert(1)").tamam, false, "javascript: reddediliyor");

console.log("\nONEKE GUVENILMIYOR -- sihirli baytlar sinaniyor\n");
/* `data:image/jpeg;base64,` yazip icine baska bir sey koymak bedava:
   onek istemcinin YAZDIGI bir etiket, dosyanin kendisi degil. */
esit(avatar("data:image/jpeg;base64," + Buffer.from(
  "<svg onload=alert(1)></svg>" + "x".repeat(40)).toString("base64")).tamam,
  false, "JPEG etiketli SVG icerigi reddediliyor");
esit(avatar("data:image/png;base64," + JPEG).tamam, false,
     "PNG etiketli JPEG icerigi reddediliyor");
esit(avatar("data:image/jpeg;base64," + PNG).tamam, false,
     "JPEG etiketli PNG icerigi reddediliyor");

console.log("\nBase64 ALFABESI sinaniyor\n");
esit(avatar("data:image/jpeg;base64,!!!!" + "A".repeat(60)).tamam, false,
     "gecersiz karakter reddediliyor");
esit(avatar("data:image/jpeg;base64,QQ").tamam, false,
     "cok kisa govde reddediliyor");

console.log("\nBOYUT TAVANI -- ham dosya yuklemeyi engelliyor\n");
/* Tavan kota icin degil: tarayicidaki yeniden kodlama adiminin
   ATLANAMAMASI icin. O adim EXIF'i -- yani telefon fotografindaki
   GPS koordinatini -- dusuruyor. Ham dosya zaten sigmiyor. */
esit(avatar("data:image/jpeg;base64," + "A".repeat(70000)).tamam, false,
     "64 KB ustu reddediliyor");
esit(avatar("data:image/jpeg;base64," + JPEG).deger.length < 65536, true,
     "normal avatar tavanin altinda");


console.log("");
kaldi.forEach(function (x) { console.log("  KALDI " + x); });
console.log(gecti + " gecti, " + kaldi.length + " kaldi");
process.exit(kaldi.length ? 1 : 0);
