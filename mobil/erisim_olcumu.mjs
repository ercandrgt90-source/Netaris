// ERISILEBILIRLIK OLCUMU -- GERCEK TARAYICIDA
//
// NE OLCER
//   1. Dokunulabilir her ogenin ERISILEBILIR ADI var mi. Adsiz bir
//      dugme ekran okuyucuda "dugme" diye okunur; gormeyen okur ne
//      yaptigini bilemez.
//   2. Dokunma hedefi en az 44x44 CSS piksel mi (WCAG 2.5.8).
//
// NICIN TARAYICI: ikisi de KAYNAKTAN okunamaz. `minHeight: 44` yazan
// bir dugme, icerigi tasarsa ya da sarmali kuculturse yine kucuk
// cikar. Olculdu (2026-10-20): arama dugmesi 42x44 idi -- simge ~10
// piksel, yatay dolgu 32. Kaynakta hicbir sey yanlis gorunmuyordu.
//
// `hitSlop` TUZAGI: yerli tarafta dokunma alanini buyutuyor ama DOM
// kutusunu buyutmuyor. Yani "hitSlop var, sorun yok" demek, web
// cikisinda gercekten kucuk kalan bir hedefi gormezden gelmektir.
//
// KOSTURMA (once web cikisi + spa sunucusu gerekiyor):
//   npx expo export --platform web --output-dir <dizin>
//   node mobil/spa_sunucu.mjs <dizin> &
//   node mobil/erisim_olcumu.mjs / /profil /gecmis
// `puppeteer-core` UYGULAMANIN BAGIMLILIGI DEGIL ve olmamali: olcum
// araci, sevk edilen pakete girmemeli. Yoksa yigin izi yerine NE
// YAPILACAGINI yaziyor -- kosturulamayan bir yordam, yazili olmayan
// yordamdan iyi degil.
let puppeteer;
try {
  puppeteer = (await import("puppeteer-core")).default;
} catch {
  console.error("puppeteer-core yok. Kurulum (uygulamaya DEGIL, gecici):");
  console.error("  npm i --no-save puppeteer-core");
  console.error("Ayrica masaustu Chrome gerekiyor; yolu CHROME_YOLU ile");
  console.error("verilebilir.");
  process.exit(2);
}
const CHROME = process.env.CHROME_YOLU ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
// Kapi degistirilebilsin: `spa_sunucu.mjs` ucuncu argumanla baska bir
// kapiya baglanabiliyor ve olcum onu izleyebilmeli.
const TABAN = process.env.TABAN || "http://127.0.0.1:8799";
const yollar = process.argv.slice(2);
const t = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  args: ["--no-sandbox"] });
try {
  for (const yol of yollar) {
    const s = await t.newPage();
    await s.setViewport({ width: 390, height: 844, deviceScaleFactor: 2,
                          isMobile: true, hasTouch: true });
    await s.goto(TABAN + yol, { waitUntil: "networkidle2", timeout: 45000 });
    await new Promise((r) => setTimeout(r, 3500));
    const o = await s.evaluate(() => {
      const ogeler = [...document.querySelectorAll(
        '[role="button"], [role="link"], button, a, input')];
      const adsiz = [], kucuk = [];
      for (const e of ogeler) {
        const ad = (e.getAttribute("aria-label") || e.innerText ||
                    e.getAttribute("placeholder") || "").trim();
        if (!ad) adsiz.push(e.outerHTML.slice(0, 70));
        const r = e.getBoundingClientRect();
        // WCAG 2.5.8 / Material: en az 44x44 CSS px onerilir.
        if (r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44)) {
          kucuk.push(`${Math.round(r.width)}x${Math.round(r.height)} ` +
                     (ad || e.tagName).slice(0, 30));
        }
      }
      return { toplam: ogeler.length, adsiz, kucuk };
    });
    console.log(JSON.stringify({ yol, ...o }, null, 1));
    await s.close();
  }
} finally { await t.close(); }
