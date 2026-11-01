// UYGULAMA KAYNAGINDA, OLCULEMEYEN DALLARIN KURALLARI
//
// NEDEN STATIK
// Uygulamayi dogrulama yolum web cikisini gercek Chrome'da kosmak.
// YERLI dal (WebView, `onShouldStartLoadWithRequest`) o yolda hic
// calismiyor, yani orada bir gerileme OLCULEMEZ. Olculemeyen yuzey,
// kusurun saklandigi yerdir; bu dosya o yuzeyin kurallarini metin
// ve AST duzeyinde tutuyor.
//
// KOSTURMA
//   node mobil/kaynak-sinamasi.mjs

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const KOK = path.resolve(import.meta.dirname);
let gecti = 0;
const dusen = [];

function dogru(aciklama, kosul) {
  if (kosul) {
    gecti += 1;
    console.log(`  gecti  ${aciklama}`);
  } else {
    dusen.push(aciklama);
    console.log(`  DUSTU  ${aciklama}`);
  }
}

console.log("");
console.log("Govde: iki kabuk, tek belge");

const govde = fs.readFileSync(path.join(KOK, "src", "govde.tsx"), "utf8");

// TEK BELGE: webde olculen sey, yerlide sevk edilenle AYNI olmali.
// Iki ayri HTML uretici olsaydi, Chrome'da olctugum belge urunde
// kosmayan bir belge olurdu.
const belgeCagrisi = (govde.match(/belge\(html, tema\)/g) || []).length;
dogru("HTML tek yerde uretiliyor (belge() bir kez cagriliyor)",
  belgeCagrisi === 1);
dogru("web dali iframe kullaniyor", /srcDoc: kaynak/.test(govde));
dogru("yerli dal WebView kullaniyor", /<WebView/.test(govde));
dogru("iframe ayni kaynagi basiyor (srcDoc: kaynak)",
  /srcDoc:\s*kaynak/.test(govde));

// IFRAME YALITIMI: `allow-same-origin` VERILMEMELI. Verilirse
// besleme govdesindeki bir betik ebeveyn DOM'una erisir.
// OLCUT NITELIGIN DEGERI, DOSYANIN TAMAMI DEGIL.
// Ilk yazimda butun dosyada "allow-same-origin" ariyordu ve KENDI
// aciklama yorumumdaki gecisi yakalayip kirmizi dondu -- bu depoda
// ayni tuzak bugun bir kez daha yasandi (bir kural dosya adini
// yorumda bulup "cagriliyor" sanmisti).
const _sandbox = (govde.match(/sandbox:\s*"([^"]*)"/) || [])[1];
dogru("iframe sandbox yalnizca allow-scripts",
  _sandbox === "allow-scripts");

// BAGLANTI YAKALAMA YALNIZCA WEBDE OLMALI.
//
// Yerlide bu isi `onShouldStartLoadWithRequest` yapiyor. Enjekte
// edilen betik her iki kabukta da `preventDefault` cagirsaydi, o
// yerli kanca HIC tetiklenmez ve govdedeki baglantilar olurdu.
// Bunu web cikisinda olcmek IMKANSIZ: yerli dal orada kosmuyor.
const yakalamaDali = /if \(!window\.ReactNativeWebView\) \{[\s\S]{0,400}?preventDefault/
  .test(govde);
dogru("baglanti yakalama `!window.ReactNativeWebView` dalinda",
  yakalamaDali);
dogru("yerli dal onShouldStartLoadWithRequest ile baglantiyi yonetiyor",
  /onShouldStartLoadWithRequest/.test(govde));

// MESAJ KANALI IKI KABUKTA DA CALISMALI.
dogru("gonder() ReactNativeWebView yoksa parent'a yaziyor",
  /window\.parent\.postMessage/.test(govde)
  && /window\.ReactNativeWebView\.postMessage/.test(govde));
// Yukseklik dogrudan degil `gonder()` uzerinden bildirilmeli;
// aksi halde webde hic ulasmaz ve govde 320 pikselde kirpilir.
dogru("yukseklik gonder() uzerinden bildiriliyor",
  /gonder\(String\(h\)\)/.test(govde));

// OLCUM SINIRI: `react-native-webview` webde islenmiyor ve yerine
// Ingilizce bir satir basiyor. O satirin uygulamada GORUNMEMESI
// gerekiyor -- web dali eklenmeden once goruyordu.
dogru("Platform ayrimi var (web dali gercekten ayri)",
  /Platform\.OS === "web"/.test(govde));

console.log("");
console.log("Bolum listesi: olcumden geliyor, tahminden degil");

const ekran = fs.readFileSync(
  path.join(KOK, "app", "analiz", "[slug].tsx"), "utf8");

// CAPA KONUMLARI OLCULEREK geliyor. Govde bir WebView/iframe
// icinde isleniyor ve yuksekligi yazi tipi yuklendikce degisiyor;
// konumu disaridan TAHMIN etmek, baslige dokunan okuru yanlis
// yere goturur.
dogru("govde capa konumlarini bildiriyor",
  /gonder\(.capa:. \+ JSON\.stringify\(kon\)\)/.test(govde));
// Olcut: `capa:` gonderimi `bildir()` govdesinin ICINDE olmali.
// Pencere genisligi tahminle degil, govdenin gercek uzunluguyla
// belirleniyor -- ilk yazimda 600 karakter yetmedi ve kural
// kodu degil KENDINI dusurdu.
const _bildir = govde.slice(govde.indexOf("function bildir()"));
const _bildirSonu = _bildir.indexOf(String.fromCharCode(10) + "  }");
dogru("capalar YUKSEKLIKLE AYNI olcumde gonderiliyor",
  _bildirSonu > 0 && _bildir.slice(0, _bildirSonu).includes("capa:"));
dogru("ekran capalari aliyor (onCapalar)", /onCapalar=\{/.test(ekran));
dogru("kaydirma OLCULEN konuma gidiyor",
  /govdeY\.current \+ ic/.test(ekran));

// LISTE YALNIZCA OLCUM GELDIYSE cizilmeli: konumu bilinmeyen bir
// bolum dokunulamaz bir dugme olurdu.
// IKI YERDE suzuluyor: listenin CIZILIP cizilmeyecegine karar
// veren kosulda ve ogeleri ureten `map` zincirinde. Yalnizca
// birini sormak yetmiyor -- otekini silen mutasyon kacti.
const _suzgec = (ekran.match(/capalar\[b\.capa\] !== undefined/g)
  || []).length;
dogru(`olcumu olmayan bolum IKI yerde de eleniyor (${_suzgec})`,
  _suzgec >= 2);
dogru("tek bolumde liste cizilmiyor", /\.length > 1 \?/.test(ekran));

// DOKUNMA HEDEFI 44 PIKSEL. Alt sekmelerde tam bu kusur olculmustu
// (etiket 10 piksellik kutuda 15 piksel) -- yukseklik SABIT degil,
// dolguyla veriliyor ki etiket kirpilmasin.
// OLCUT `bolum:` STILININ ICI. Dosyada baska bir `minHeight: 44`
// daha var (metodoloji baglantisi) ve serbest arama onu
// yakalayip mutasyonu kacirdi.
const _bolumStil = (ekran.match(/\n  bolum: \{[\s\S]*?\},/) || [""])[0];
dogru("bolum dugmesi minHeight 44",
  /minHeight:\s*44/.test(_bolumStil));

// MESAJ COZUMU TEK YERDE: iki kabuk ayrilirsa webde olctugum
// davranis yerlide gecerli olmaz.
// Olcut sayi degil, IKI CAGRI YERI: web dinleyicisi ve yerli
// `onMessage`. Sayi esigi (">= 3") kodu degil kendini dusurdu.
dogru("web dinleyicisi ortak cozucuyu cagiriyor",
  /dinle = \(o: MessageEvent\)[\s\S]{0,200}?mesaj\(/.test(govde));
dogru("yerli onMessage ortak cozucuyu cagiriyor",
  /onMessage=\{\(o\)[\s\S]{0,400}?mesaj\(/.test(govde));
console.log("");
if (dusen.length) {
  console.error(`DUSTU (${dusen.length}):`);
  for (const d of dusen) console.error(`  - ${d}`);
  process.exit(1);
}
console.log(`TUM KAYNAK SINAMALARI GECTI (${gecti})`);
