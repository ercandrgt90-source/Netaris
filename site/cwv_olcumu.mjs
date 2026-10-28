// CANLI SITE -- TELEFON OLCUSUNDE CEKIRDEK WEB OLCUTLERI
//
// NE OLCER: LCP (en buyuk icerik cizimi), CLS (yerlesim kaymasi),
// aktarilan bayt, istek sayisi, DOM ogesi -- ve LCP'nin HANGI OGE
// oldugunu. Son kisim olmadan duzeltme hedefsiz kalir.
//
// NICIN SINAMA DEGIL: CI'da tarayici yok ve bu olcu AGA bagli.
// `test_dom_agirligi` bir VEKIL olcu tutuyor (dugum sayisi), gercek
// cizim suresi degil.
//
// IKI TUZAK -- IKISI DE YASANDI (2026-10-23):
//
//   1. AYNI TARAYICIDA ART ARDA olcmek. Ikinci sayfa yazi tipini ve
//      CSS'i onbellekten alir: /gundem/ 6388 ms olculdu, ardindan
//      ayni oturumda haber sayfasi 1668 ms "cikti". Soguk acilis
//      sanilan sey isinmis olcumdu. Her sayfa icin AYRI baglam.
//   2. ILK baglamin kurulum maliyeti sayfaya yaziliyor: ilk olcum
//      47440 ms gosterdi. Once bir ISINMA sayfasi aciliyor.
//
// KOSTURMA (puppeteer-core uygulamaya DEGIL, gecici kurulur):
//   npm i --no-save puppeteer-core
//   node site/cwv_olcumu.mjs / /gundem/ /makro/
//
// Chrome yolu CHROME_YOLU ile verilebilir.
//
// TABAN -- DAGITMADAN ONCE OLCMEK ICIN.
//
// Adres bu dosyada SABIT yaziliydi (`"https://netaris.net" + yol`).
// Olculdu (2026-10-28): yerel bir sunucu kuruldu ve `TABAN` verildi
// sanilarak olculdu; arac onu HIC OKUMUYORDU ve canli siteyi
// olcmeye devam etti. Yerel HTML'de hic bulunmayan bir gorsel LCP
// ogesi olarak raporlandi -- kusur ancak o tutarsizlik farkedilince
// goruldu.
//
// Sonuc: bir degisikligin LCP'ye etkisi, DAGITILMADAN once
// olculemiyordu. Artik olculebilir:
//
//   python -m http.server 8765 --directory site/cikti --bind 127.0.0.1
//   TABAN=http://127.0.0.1:8765 node site/cwv_olcumu.mjs /gundem/
//
// UYARI -- YEREL OLCUM CANLIYLA AYNI DEGIL: Cloudflare onbellegi,
// HTTP/2 coklamasi ve gercek gecikme yok. Yerel olcum IKI SURUMU
// birbiriyle kiyaslamak icin gecerli; mutlak LCP degeri icin canli
// olcum sart.
let puppeteer;
try {
  puppeteer = (await import("puppeteer-core")).default;
} catch {
  console.error("puppeteer-core yok:  npm i --no-save puppeteer-core");
  console.error("Ayrica masaustu Chrome gerekiyor (CHROME_YOLU).");
  process.exit(2);
}
const TABAN = (process.env.TABAN || "https://netaris.net")
  .replace(/\/$/, "");
const CHROME = process.env.CHROME_YOLU ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const yollar = process.argv.slice(2);
const t = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  args: ["--no-sandbox"] });
try {
  // ISINMA: ilk baglamin kurulum maliyeti olculen sayfaya yazilmasin.
  // Olculdu (2026-10-23): isinmasiz ilk olcum 47440 ms gosterdi;
  // ayni sayfa isinmadan sonra 4112 ms. Aradaki fark sayfada degil,
  // tarayici baslangicindaydi.
  try {
    const i = await t.newPage();
    await i.goto(TABAN + "/makro/", { waitUntil: "load",
                                                 timeout: 60000 });
    await i.close();
  } catch { /* isinma basarisizsa olcum yine de yapilir */ }

  for (const yol of yollar) {
    // HER SAYFA ICIN TEMIZ BAGLAM -- YOKSA OLCUM YALAN SOYLER.
    //
    // Olculdu (2026-10-23): ayni tarayicida art arda uc sayfa
    // olculdu ve ikincisi 1668 ms, ucuncusu 744 ms cikti. Sebep
    // sayfalar degil ONBELLEKTI: yazi tipi ve CSS ilk sayfada
    // inmisti. Soguk acilis olcmek isterken isinmis olcum alindi.
    const baglam = await t.createBrowserContext();
    const s = await baglam.newPage();
    await s.setViewport({ width: 390, height: 844, deviceScaleFactor: 2,
                          isMobile: true, hasTouch: true });
    // GERCEK TELEFON SARTI: hizli bir masaustu baglantisi, mobil
    // okurun gordugu sey degil.
    const cdp = await s.createCDPSession();
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8,
      uploadThroughput: 750 * 1024 / 8 });
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await s.evaluateOnNewDocument(() => {
      window.__lcp = 0; window.__cls = 0;
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) {
          window.__lcp = e.startTime;
          // HANGI OGE: duzeltme ancak bu bilinince hedefli olur.
          const el = e.element;
          window.__lcpOge = el
            ? (el.tagName.toLowerCase()
               + (el.id ? "#" + el.id : "")
               + (el.className && typeof el.className === "string"
                  ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".")
                  : "")
               + (el.currentSrc ? "  src=" + el.currentSrc.slice(-48) : "")
               + "  metin=" + (el.textContent || "").trim().slice(0, 42))
            : "(oge yok -- " + (e.url || "").slice(-48) + ")";
          window.__lcpBoyut = e.size || 0;
        }
      }).observe({ type: "largest-contentful-paint", buffered: true });
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;
      }).observe({ type: "layout-shift", buffered: true });
    });
    const bas = Date.now();
    await s.goto(TABAN + yol, { waitUntil: "load", timeout: 60000 });
    await new Promise((r) => setTimeout(r, 4000));
    const o = await s.evaluate(() => {
      const n = performance.getEntriesByType("navigation")[0] || {};
      const kay = performance.getEntriesByType("resource");
      return {
        lcp_ms: Math.round(window.__lcp),
        lcp_oge: window.__lcpOge || "(yok)",
        lcp_alan: window.__lcpBoyut || 0,
        cls: Number((window.__cls || 0).toFixed(4)),
        dcl_ms: Math.round(n.domContentLoadedEventEnd || 0),
        yuk_ms: Math.round(n.loadEventEnd || 0),
        istek: kay.length,
        bayt_kb: Math.round(kay.reduce((a, r) => a + (r.transferSize || 0), 0) / 1024),
        dom: document.getElementsByTagName("*").length,
        yavaslar: performance.getEntriesByType("resource")
          .sort((a, b) => b.duration - a.duration).slice(0, 3)
          .map((r) => `${Math.round(r.duration)}ms ${Math.round((r.transferSize||0)/1024)}kb ${r.name.slice(-42)}`),
      };
    });
    console.log(JSON.stringify({ yol, gecen_ms: Date.now() - bas, ...o }));
    await s.close();
    await baglam.close();
  }
} finally { await t.close(); }
