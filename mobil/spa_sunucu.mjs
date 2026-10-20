// WEB CIKISINI SUNAN KUCUK SUNUCU -- OLCUM ICIN
//
// NICIN GEREKIYOR: `erisim_olcumu.mjs` ve tarayici olcumleri
// uygulamanin web cikisini ACIP olcuyor. `expo export` statik dosya
// birakiyor ama expo-router bir TEK SAYFA uygulamasi: `/gecmis`
// adresinde dosya YOK, istek `index.html`e dusmeli. Dosya protokolu
// (file://) ile acmak da olmuyor -- modul yuklemeleri kaynak
// kisitina takiliyor.
//
// Bu dosya depoda DURUYOR cunku olcum yordami onsuz kosturulamiyor.
// Belgede "su betigi calistir" yazip betigi depoya koymamak, bu
// depoda tanidik bir kusur: sunulan secenek CALISMALI.
//
// KOSTURMA:
//   npx expo export --platform web --output-dir <dizin>
//   node mobil/spa_sunucu.mjs <dizin>          # varsayilan: ./web
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const KOK = path.resolve(process.argv[2] || "web");
const KAPI = Number(process.argv[3] || 8799);
const TUR = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".ttf": "font/ttf",
  ".woff2": "font/woff2", ".map": "application/json",
};

if (!fs.existsSync(path.join(KOK, "index.html"))) {
  console.error(`web cikisi yok: ${KOK}/index.html`);
  console.error("once: npx expo export --platform web --output-dir <dizin>");
  process.exit(2);
}

http.createServer((istek, cevap) => {
  const yol = decodeURIComponent((istek.url || "/").split("?")[0]);
  let dosya = path.join(KOK, yol);
  // DIZIN DISINA CIKILMASIN.
  if (!dosya.startsWith(KOK)) {
    cevap.writeHead(403).end("yasak");
    return;
  }
  if (!fs.existsSync(dosya) || fs.statSync(dosya).isDirectory()) {
    const alt = path.join(dosya, "index.html");
    // TEK SAYFA GERI DONUSU: bilinmeyen yol index.html'e duser.
    dosya = fs.existsSync(alt) ? alt : path.join(KOK, "index.html");
  }
  cevap.writeHead(200, {
    "content-type": TUR[path.extname(dosya)] || "application/octet-stream",
  });
  cevap.end(fs.readFileSync(dosya));
}).listen(KAPI, "127.0.0.1",
  () => console.log(`spa sunucu http://127.0.0.1:${KAPI} <- ${KOK}`));
