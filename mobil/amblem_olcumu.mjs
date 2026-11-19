// AMBLEM KAROLARI GERCEKTEN CIZILIYOR MU -- GERCEK TARAYICIDA
//
// NE OLCER
//   1. Analiz kartlarinda amblem karosu CIZILIYOR mu (sayi > 0).
//   2. Karonun zemini GERCEK bir renk mi (saydam degil).
//   3. Icinde yazi VAR mi -- bos renkli kutu basilmamali.
//   4. Yazi KIRPILMIYOR mu  <- 4. madde bir kusur YAKALADI.
//
// NICIN TARAYICI: besleme alani dolu, bilesen yazili olabilir ve
// kart yine yanlis cikabilir. Olculdu (2026-11-19): karo `width: 34`
// idi, bes harfli BIST kodlari sigmadi ve ekranda "HAT…" goruldu.
// DOM'da `textContent` hala "HATEK" donuyordu -- yani "yazi dolu"
// kontrolu YESIL geciyordu. Kirpilmayi once EKRAN GORUNTUSU
// gosterdi; olcum sonradan `scrollWidth > clientWidth` ile
// guclendirildi ve ayni paket uzerinde 6 karonun 5'ini kirpik
// bildirdi.
//
// Ders: gecen bir olcum, olculenin dogru oldugunu gostermiyor --
// olcutun KENDISI eksik olabilir.
//
// NICIN CI'DA KOSMUYOR: masaustu Chrome, web cikisi (`expo export`)
// ve URETILMIS besleme gerekiyor. `test_isakisi.py` icinde adiyla
// ve gerekcesiyle MUAF; muafiyetin SAYISI da bagli.
//
// KOSTURMA
//   python site/insa.py                       # besleme uretilsin
//   cd mobil && npx expo export --platform web --output-dir <dizin>
//   node mobil/spa_sunucu.mjs <dizin> &
//   node mobil/amblem_olcumu.mjs /arastirma [ekran.png]
//
// TUZAK (Git Bash): `/arastirma` argumani Windows yoluna cevriliyor.
//   MSYS_NO_PATHCONV=1 node mobil/amblem_olcumu.mjs "/arastirma"
//
// BESLEME YAKALANIYOR: web cikisinda `netaris.net` CORS vermiyor.
// Istekler YEREL `site/cikti` icindeki GERCEK besleme dosyalarindan
// karsilaniyor ve cevaba `access-control-allow-origin` EKLENIYOR --
// yoksa tarayici yine reddediyor.
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import puppeteer from "puppeteer-core";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const TABAN = process.env.TABAN || "http://127.0.0.1:8799";
const CIKTI = "C:/Users/Lenovo/Desktop/Haber Sitesi/site/cikti";
const YOL = process.argv[2] || "/arastirma";

const t = await puppeteer.launch({
  executablePath: CHROME, headless: "new", args: ["--no-sandbox"],
});
const s = await t.newPage();
await s.setViewport({ width: 420, height: 900 });
await s.setRequestInterception(true);

let karsilanan = 0;
let eksik = 0;
s.on("request", (r) => {
  const u = r.url();
  const m = u.match(/^https?:\/\/netaris\.net(\/.+)$/);
  if (!m) return void r.continue();
  const dosya = path.join(CIKTI, m[1].split("?")[0]);
  if (fs.existsSync(dosya) && fs.statSync(dosya).isFile()) {
    karsilanan += 1;
    const govde = fs.readFileSync(dosya);
    const tur = dosya.endsWith(".json") ? "application/json"
      : dosya.endsWith(".svg") ? "image/svg+xml" : "application/octet-stream";
    return void r.respond({
      status: 200,
      headers: { "content-type": tur, "access-control-allow-origin": "*" },
      body: govde,
    });
  }
  eksik += 1;
  return void r.respond({ status: 404, headers: {
    "access-control-allow-origin": "*" }, body: "yok" });
});

const hatalar = [];
s.on("pageerror", (e) => hatalar.push(String(e)));
s.on("console", (c) => {
  if (c.type() === "error") hatalar.push("console: " + c.text());
});

await s.goto(TABAN + YOL, { waitUntil: "networkidle2", timeout: 60000 });
// Kart listesinin dolmasini bekle -- "sayfa yuklendi" ile "veri
// geldi" ayni sey degil.
await new Promise((r) => setTimeout(r, 4000));

const olcum = await s.evaluate(() => {
  const hepsi = [...document.querySelectorAll("*")];
  // Amblem karosunun imzasi: erisilebilir adi "... amblemi".
  const karolar = hepsi.filter((e) =>
    (e.getAttribute("aria-label") || "").endsWith(" amblemi"));
  const ayrinti = karolar.slice(0, 6).map((e) => {
    const k = e.getBoundingClientRect();
    const b = getComputedStyle(e);
    // KIRPILMA: `textContent` tam metni dondurur, EKRANDA kirpik
    // olsa bile. Olculdu -- ilk surumde "HATEK" kutuya sigmiyordu
    // ve "HAT..." goruluyordu ama bu olcum YESIL geciyordu.
    // Gercek olcut, yazi dugumunun TASIP TASMADIGI.
    const yaziDugum = [...e.querySelectorAll("*")].find(
      (x) => (x.textContent || "").trim() && !x.children.length) || e;
    const tasan = yaziDugum.scrollWidth > yaziDugum.clientWidth + 1;
    return {
      ad: e.getAttribute("aria-label"),
      yazi: (e.textContent || "").trim(),
      kirpik: tasan,
      genis: Math.round(k.width),
      yuksek: Math.round(k.height),
      zemin: b.backgroundColor,
      gorunur: k.width > 0 && k.height > 0 && b.visibility !== "hidden"
        && b.display !== "none" && Number(b.opacity) > 0.01,
    };
  });
  const metin = document.body.innerText || "";
  return {
    karo: karolar.length,
    ayrinti,
    bosZemin: ayrinti.filter((a) =>
      /rgba\(0, 0, 0, 0\)|transparent/.test(a.zemin)).length,
    yazisiz: ayrinti.filter((a) => !a.yazi).length,
    kirpik: ayrinti.filter((a) => a.kirpik).length,
    gorunmez: ayrinti.filter((a) => !a.gorunur).length,
    metinUzunluk: metin.length,
  };
});

console.log("yol              :", YOL);
console.log("karsilanan istek :", karsilanan, " eksik:", eksik);
console.log("sayfa metni      :", olcum.metinUzunluk, "karakter");
console.log("AMBLEM KAROSU    :", olcum.karo);
console.log("  bos zeminli    :", olcum.bosZemin);
console.log("  yazisiz        :", olcum.yazisiz);
console.log("  KIRPIK yazili  :", olcum.kirpik);
console.log("  gorunmez       :", olcum.gorunmez);
for (const a of olcum.ayrinti) {
  console.log(`    ${a.ad.padEnd(18)} yazi=${a.yazi.padEnd(7)}`
    + ` ${a.genis}x${a.yuksek} zemin=${a.zemin}`
    + ` gorunur=${a.gorunur} kirpik=${a.kirpik}`);
}
if (hatalar.length) {
  console.log("SAYFA HATALARI:");
  for (const h of hatalar.slice(0, 6)) console.log("   ", h.slice(0, 160));
}
const png = process.argv[3];
if (png) {
  await s.screenshot({ path: png, fullPage: false });
  console.log("ekran goruntusu  :", png);
}
await t.close();
process.exit(olcum.karo > 0 && olcum.bosZemin === 0 && olcum.yazisiz === 0
  && olcum.gorunmez === 0 && olcum.kirpik === 0 ? 0 : 1);
