// BEARER OTURUMU -- CEREZ AKISINI BOZMADAN, HttpOnly GUVENCESINI
// KAYBETMEDEN.
//
// BU DOSYA NEDEN VAR
// ------------------
// Mobil uygulamada HttpOnly cerez yonetimi platforma bagli ve
// kirilgan, bu yuzden worker `Authorization: Bearer <jeton>` da
// kabul ediyor. Iki kural bu eklemeyi guvenli kiliyor ve ikisi de
// SESSIZCE kaybedilebilir:
//
//  1. TARAYICI AKISI DEGISMEDI. Cerez hala yaziliyor, hala
//     `HttpOnly; Secure; SameSite=Lax`. Bir harf degisse oturum
//     guvenligi duser ve hicbir sey patlamaz.
//
//  2. JETON GOVDEDE YALNIZCA UYGULAMA ISTEDIGINDE DONER. Tarayicida
//     jeton HttpOnly cerezde duruyor, yani sayfadaki JavaScript onu
//     OKUYAMIYOR -- XSS durumunda oturumun calinmasini engelleyen
//     asil koruma bu. Jetonu her girise govdede koymak o korumayi
//     kaldirirdi.
//
// AG KULLANILMIYOR, D1 KULLANILMIYOR. Sinama worker kaynagini metin
// olarak okuyup davranis gerektiren parcalari ayri ayri kosturuyor.
//
//   node site/test_bearer_oturum.js

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const KAYNAK = path.resolve(
  import.meta.dirname ?? path.dirname(new URL(import.meta.url).pathname),
  "worker.js",
);
const S = fs.readFileSync(KAYNAK, "utf8");

let gecti = 0;
const dusen = [];

function esit(bulunan, beklenen, aciklama) {
  if (bulunan !== beklenen) {
    dusen.push(
      `${aciklama}\n      beklenen: ${JSON.stringify(beklenen)}` +
        `\n      gelen   : ${JSON.stringify(bulunan)}`,
    );
    return;
  }
  gecti += 1;
  console.log(`  gecti  ${aciklama}`);
}

function dogru(kosul, aciklama) {
  esit(!!kosul, true, aciklama);
}

console.log("");
console.log("1. CEREZ OZNITELIKLERI KORUNUYOR");
// Bir harf degisse oturum guvenligi duser ve hicbir sey patlamaz.
const cerezSatiri = S.match(/function cerezYaz\([^)]*\)\s*\{[\s\S]*?\n\}/);
dogru(cerezSatiri, "cerezYaz bulundu");
if (cerezSatiri) {
  const g = cerezSatiri[0];
  dogru(g.includes("HttpOnly"), "cerez HttpOnly");
  dogru(g.includes("Secure"), "cerez Secure");
  dogru(g.includes("SameSite=Lax"), "cerez SameSite=Lax");
  dogru(g.includes("Path=/"), "cerez Path=/");
}

console.log("");
console.log("2. jetonOku CEREZI ONCELIYOR, SONRA Bearer");
// Cerez once: tarayici akisi oncelikli kalmali. Bearer'i one almak,
// bir saldirganin kendi jetonunu basliga koyup oturumu DEGISTIRMESINE
// izin verebilirdi ("oturum sabitleme" benzeri bir yuzey).
const jetonOku = S.match(/function jetonOku\(istek\)\s*\{[\s\S]*?\n\}/);
dogru(jetonOku, "jetonOku bulundu");
if (jetonOku) {
  const g = jetonOku[0];
  const cerezYeri = g.indexOf("cerezOku");
  const bearerYeri = g.indexOf("authorization");
  dogru(cerezYeri >= 0, "cerez okunuyor");
  dogru(bearerYeri >= 0, "authorization basligi okunuyor");
  dogru(
    cerezYeri >= 0 && bearerYeri >= 0 && cerezYeri < bearerYeri,
    "CEREZ Bearer'DAN ONCE deneniyor",
  );
}

console.log("");
console.log("3. Bearer DESENI DAVRANISI -- gercekten kosturuluyor");
// Desen metinden cikarilip CALISTIRILIYOR: "var mi" demek yetmez,
// dogru seyi eslestirdigini gormek gerekiyor.
// `[^)]+` KULLANILAMAZ: cikarilacak desenin kendisi parantez
// iceriyor ((\S+)) ve sinif ilk parantezde duruyordu. Tembel
// `.*?` ile `/i)` sonlandiricisina kadar okunuyor.
const desenEs = S.match(/b\.match\((\/\^.*?\/i)\)/);
dogru(desenEs, "Bearer deseni bulundu");
if (desenEs) {
  // eslint-disable-next-line no-eval
  const desen = eval(desenEs[1]);
  const al = (b) => {
    const e = String(b).match(desen);
    return e ? e[1] : null;
  };
  esit(al("Bearer abc123"), "abc123", "duz Bearer");
  esit(al("bearer abc123"), "abc123", "kucuk harf kabul");
  esit(al("BEARER abc123"), "abc123", "buyuk harf kabul");
  esit(al("  Bearer   abc123  "), "abc123", "fazladan bosluk");
  esit(al("Basic abc123"), null, "Basic REDDEDILIYOR");
  esit(al("abc123"), null, "oneksiz REDDEDILIYOR");
  esit(al("Bearer"), null, "jetonsuz REDDEDILIYOR");
  esit(al("Bearer "), null, "bos jeton REDDEDILIYOR");
  esit(al("Bearer a b"), null, "bosluklu jeton REDDEDILIYOR");
  esit(al(""), null, "bos baslik");
}

console.log("");
console.log("4. uyeBul ve cikis JETONOKU KULLANIYOR");
// `cikis` cerezOku'da kalsaydi uygulama "cikis yaptim" der, jeton ise
// sunucuda GECERLI kalirdi -- en sinsi tur.
const uyeBul = S.match(/async function uyeBul\(istek, db\)\s*\{[\s\S]*?\n\}/);
dogru(uyeBul && uyeBul[0].includes("jetonOku(istek)"),
  "uyeBul jetonOku kullaniyor");
const cikis = S.match(/async function cikis\(istek, env\)\s*\{[\s\S]*?\n\}/);
dogru(cikis && cikis[0].includes("jetonOku(istek)"),
  "cikis jetonOku kullaniyor (uygulama cikisi GERCEKTEN kapatiyor)");
dogru(cikis && cikis[0].includes("DELETE FROM oturum"),
  "cikis oturumu veritabanindan siliyor");

console.log("");
console.log("5. uygulamaMi DAVRANISI");
const uygEs = S.match(/function uygulamaMi\(govde, istek\)\s*\{[\s\S]*?\n\}/);
dogru(uygEs, "uygulamaMi bulundu");
if (uygEs) {
  // eslint-disable-next-line no-new-func
  const uygulamaMi = new Function(
    `${uygEs[0]}; return uygulamaMi;`,
  )();
  const istek = (baslik) => ({
    headers: { get: (a) => (a === "x-netaris-istemci" ? baslik || "" : "") },
  });
  esit(uygulamaMi({ istemci: "uygulama" }, istek()), true, "govde ile");
  esit(uygulamaMi({}, istek("uygulama")), true, "baslik ile");
  esit(uygulamaMi({}, istek()), false, "WEB akisi: istemiyor");
  esit(uygulamaMi(null, istek()), false, "govde yok");
  esit(uygulamaMi({ istemci: "web" }, istek()), false, "baska istemci");
  esit(uygulamaMi({ istemci: "uygulamaa" }, istek()), false,
    "benzer ama farkli dizge");
  esit(uygulamaMi({}, istek("web")), false, "baslik baska deger");
}

console.log("");
console.log("6. JETON WEB AKISINDA GOVDEYE GIRMIYOR");
//
// EN ONEMLI KURAL. Govdeye kosulsuz konsa HttpOnly'nin anlami
// kalmazdi: bir XSS aciginda saldirgan jetonu dogrudan okurdu.
//
// Sinama yanit govdesini kuran blogu bulup, jeton atamasinin
// `uygulamaMi` KOSULUNUN ICINDE oldugunu dogruluyor.
const bloklar = [...S.matchAll(
  /const cikisGovdesi = \{[\s\S]*?return yanit\(cikisGovdesi[^;]*;/g,
)];
esit(bloklar.length, 2, "iki giris yolu da (e-posta + Google) bulundu");
for (const [i, b] of bloklar.entries()) {
  const g = b[0];
  const kosulYeri = g.indexOf("uygulamaMi(");
  const jetonYeri = g.indexOf("cikisGovdesi.jeton");
  dogru(kosulYeri >= 0, `giris ${i + 1}: uygulamaMi kosulu var`);
  dogru(jetonYeri >= 0, `giris ${i + 1}: jeton atamasi var`);
  dogru(
    kosulYeri >= 0 && jetonYeri > kosulYeri,
    `giris ${i + 1}: jeton atamasi KOSULDAN SONRA (kosulsuz degil)`,
  );
  // Cerez her durumda yazilmali -- web akisi bozulmasin.
  dogru(g.includes("cerezYaz(jeton, OTURUM_GUN)"),
    `giris ${i + 1}: cerez HER DURUMDA yaziliyor`);
}

console.log("");
console.log("7. JETON GUNLUGE YAZILMIYOR");
// Oturum jetonunun gunluge dusmesi, gunlugu okuyan herkese oturum
// vermek demek.
const gunlukte = [...S.matchAll(/console\.(log|warn|error)\([^)]*\)/g)]
  .filter((m) => /\bjeton\b/.test(m[0]) && !/jeton_ozeti|jetonOku/.test(m[0]));
esit(gunlukte.length, 0,
  `jeton console'a yazilmiyor${gunlukte.length ? ` (${gunlukte[0][0]})` : ""}`);

// Veritabaninda yalnizca OZET durmali.
dogru(
  /INSERT INTO oturum \(jeton_ozeti/.test(S),
  "veritabaninda yalnizca jeton OZETI saklaniyor",
);

console.log("");
if (dusen.length) {
  console.error(`DUSTU (${dusen.length}):`);
  for (const d of dusen) console.error(`  - ${d}`);
  process.exit(1);
}
console.log(`TUM TESTLER GECTI (${gecti})`);
