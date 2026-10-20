import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const svg = fs.readFileSync(process.argv[2], "utf8");
const cikti = process.argv[3];
const boy = Number(process.argv[4] || 1024);
const t = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  args: ["--no-sandbox", "--force-device-scale-factor=1"] });
try {
  const s = await t.newPage();
  await s.setViewport({ width: boy, height: boy, deviceScaleFactor: 1 });
  await s.setContent(`<!doctype html><meta charset="utf-8">
    <style>html,body{margin:0;padding:0;background:transparent}
    svg{width:${boy}px;height:${boy}px;display:block}</style>${svg}`,
    { waitUntil: "load" });
  await s.screenshot({ path: cikti, omitBackground: true });
  console.log("cizildi " + boy + "px -> " + cikti);
} finally { await t.close(); }
