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

// `--kok <dizin>` ILE BASKA BIR AGACA BAKABILIYOR.
//
// NEDEN: bu dosyadaki kurallar BIRER KAPI ve kapilarin kendisi de
// sinanmali. Olculdu (2026-11-19, mutasyon M12): bir kurali "her
// zaman gecer" hale getiren mutasyon KACTI -- hicbir sey onu
// tutmuyordu. `sozlesme-sinamasi.mjs` ayni ihtiyac icin `--kok`
// aliyor ve `test_mobil_besleme.py` beslemeyi BOZUP kirmizi donmesini
// bekliyor; ayni desen buraya tasindi (`test_mobil_kaynak.py`).
//
// Varsayilan DEGISMIYOR: argumansiz cagri kendi dizinine bakiyor.
const _kokArg = process.argv.indexOf("--kok");
const KOK = _kokArg >= 0 && process.argv[_kokArg + 1]
  ? path.resolve(process.argv[_kokArg + 1])
  : path.resolve(import.meta.dirname);
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
console.log("Etiket veriyle celismemeli");

const piyasaEkran = fs.readFileSync(
  path.join(KOK, "app", "(sekmeler)", "piyasalar.tsx"), "utf8");

// `veri_tarihi` "EN YENI" DEGIL.
//
// Olculdu (2026-11-01): deger 2026-10-30 iken seritte 2026-11-02
// tarihli USD/TRY duruyordu. Uretici ileri tarihli kalemi bilerek
// disliyor (TCMB sonraki is gununun kurunu onceden yayimliyor),
// yani deger seridin EN YENISI degil. Uygulama onu "seritteki en
// yeni veri" diye sunuyordu ve bu cumle YANLISTI.
//
// Beslemenin anlami `sozlesme-sinamasi.mjs`de sabitlendi; burada
// o anlama aykiri CUMLE tutuluyor.
dogru("piyasa etiketi `en yeni` iddiasinda bulunmuyor",
  !/en yeni veri/i.test(piyasaEkran));
dogru("piyasa etiketi ileri tarihli kalemi ACIKCA soyluyor",
  /ileri tarihli kalemler kendi tarihini/.test(piyasaEkran));
console.log("");
console.log("Amblem: SVG YOLU DEGIL, VERI");

// NEDEN BURADA -- OLCULEMEYEN DAL.
//
// Besleme `amblem` alaninda bir SVG yolu tasiyor. O yolu
// `<Image source={{uri}}>` ile basmak WEB CIKISINDA CALISIR -- yani
// benim dogrulama yuzeyimde dogru gorunur -- ama React Native'in
// yerlesik `Image`i SVG basmiyor ve bu projede `react-native-svg`
// ya da `expo-image` YOK. Yani iOS/Android'de kart SESSIZCE bos
// kalirdi ve bunu olcemezdim. Tam olarak bu dosyanin konusu.
//
// YORUMLAR AYIKLANIYOR. Bu depoda IKI KEZ ayni tuzaga dusuldu:
// bir kural dosya adini YORUMDA bulup "cagriliyor" sandi, bir
// digeri `allow-same-origin`i kendi aciklamasinda yakaladi. Olcut
// daima KOD olmali.
const _yorumsuz = (m) =>
  m.replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, " ")
    .replace(/^\s*\/\/.*$/gm, " ");

const bilesen = fs.readFileSync(path.join(KOK, "src", "bilesen.tsx"), "utf8");
const bilesenKod = _yorumsuz(bilesen);

// `Amblem` govdesi: tanimdan sonraki ilk `export function`a kadar.
const _amBas = bilesenKod.indexOf("export function Amblem(");
const _amSon = bilesenKod.indexOf("export function", _amBas + 10);
const amblemGovde = _amBas >= 0
  ? bilesenKod.slice(_amBas, _amSon > _amBas ? _amSon : undefined)
  : "";

dogru("Amblem bileseni VAR", amblemGovde.length > 0);
dogru("Amblem View+Text ile ciziliyor",
  /<View/.test(amblemGovde) && /<Text/.test(amblemGovde));
// ASIL KURAL: govdede Image/SVG/varlik adresi GECMIYOR.
dogru("Amblem `Image` KULLANMIYOR (yerlide SVG basmaz)",
  !/\bImage\b/.test(amblemGovde));
dogru("Amblem `varlikAdresi` CAGIRMIYOR (dosya degil veri)",
  !/varlikAdresi/.test(amblemGovde));
dogru("Amblem govdesinde `.svg` GECMIYOR",
  !/\.svg/.test(amblemGovde));
// EKSIK VERIDE KARO BASILMIYOR.
//
// Besleme kapisi (sozlesme) bos renk/etiket tasiyan kaydi zaten
// eliyor; ama bilesen BUNA GUVENMEMELI -- ikinci bir besleme yolu
// ya da onbellekten gelen eski bir kayit, icinde yazi olmayan
// renkli bir kutu ya da saydam bir bosluk basardi.
//
// Mutasyon (M6) tam buradan kacmisti: gercek veride iki alan hep
// dolu oldugu icin korumayi sokmek hicbir sinamayi dusurmuyordu.
dogru("Amblem eksik veride `null` donuyor",
  /if\s*\(\s*!\s*kod\s*\|\|\s*!\s*renk\s*\)\s*return null/
    .test(amblemGovde));

// AMBLEM ALANI HICBIR YERDE GORSEL KAYNAGI OLMUYOR.
//
// Yukaridaki kural yalnizca bilesenin KENDISINE bakiyor; alan baska
// bir ekranda dogrudan `Image`a verilebilirdi. Olcut `varlikAdresi`
// cagrilarinin ARGUMANI -- dosyanin tamami degil.
const _ekranlar = [];
const _gez = (dizin) => {
  for (const ad of fs.readdirSync(dizin)) {
    const tam = path.join(dizin, ad);
    if (fs.statSync(tam).isDirectory()) {
      if (ad !== "node_modules") _gez(tam);
    } else if (/\.tsx?$/.test(ad)) _ekranlar.push(tam);
  }
};
for (const d of ["src", "app"]) {
  const tam = path.join(KOK, d);
  if (fs.existsSync(tam)) _gez(tam);
}
let amblemGorsel = 0;
for (const f of _ekranlar) {
  const k = _yorumsuz(fs.readFileSync(f, "utf8"));
  for (const m of k.matchAll(/varlikAdresi\(([^)]*)\)/g)) {
    if (/amblem(?!_)/.test(m[1])) amblemGorsel += 1;
  }
}
dogru("`amblem` alani hicbir yerde gorsel kaynagi DEGIL",
  amblemGorsel === 0);
// ATILLIK: tarayici gercekten dosya buldu mu ve `varlikAdresi`
// cagrisi gercekten var mi? Yoksa ustteki iddia bos gecer.
dogru(`tarayici ${_ekranlar.length} kaynak dosyasi gordu`,
  _ekranlar.length >= 5);
let _vaCagri = 0;
for (const f of _ekranlar) {
  _vaCagri += (_yorumsuz(fs.readFileSync(f, "utf8"))
    .match(/varlikAdresi\(/g) || []).length;
}
dogru(`varlikAdresi gercekten cagriliyor (${_vaCagri})`, _vaCagri >= 1);

// SVG CIZEN PAKET YOKSA KURAL GECERLI KALIR.
//
// Birisi `react-native-svg` eklerse bu kuralin gerekcesi degisir ve
// o zaman BILINCLI olarak gozden gecirilmeli. Bu yuzden varsayim
// sinaniyor, sessizce dogru kabul edilmiyor.
const _pkg = JSON.parse(
  fs.readFileSync(path.join(KOK, "package.json"), "utf8"));
const _bag = Object.keys(_pkg.dependencies || {});
dogru("SVG cizen paket yok -- kuralin dayanagi duruyor",
  !_bag.includes("react-native-svg") && !_bag.includes("expo-image"));

console.log("");
if (dusen.length) {
  console.error(`DUSTU (${dusen.length}):`);
  for (const d of dusen) console.error(`  - ${d}`);
  process.exit(1);
}
console.log(`TUM KAYNAK SINAMALARI GECTI (${gecti})`);
