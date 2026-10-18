// BESLEME <-> UYGULAMA SOZLESMESI
//
// NEDEN BU SINAMA VAR
// Uygulama `/v1/*.json` icindeki alan adlarina gore yaziliyor.
// Python tarafinda bir alan adi degisirse ya da bir alan dusurulurse
// TypeScript BUNU GORMEZ: JSON calisma aninda geliyor, tip denetimi
// derleme aninda kosuyor. Sonuc sessiz: ekranda bos bir satir, ya da
// `undefined` yazisi.
//
// Bu depoda tam bu sinif birkac kez yasandi: kural bir yerde
// duzeldi, ona bagli oteki yer sessizce ayristi.
//
// NE SINANIYOR
// Uretilmis gercek cikti (`site/cikti/v1/`) okunuyor ve uygulamanin
// OKUDUGU her alanin var oldugu dogrulaniyor. Ag kullanilmiyor.
//
// KOSTURMA
//   node mobil/sozlesme-sinamasi.mjs

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const KOK = path.resolve(import.meta.dirname, "..", "site", "cikti", "v1");
let gecti = 0;
const dusen = [];

function oku(goreli) {
  const p = path.join(KOK, goreli);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function dogrula(ad, nesne, alanlar) {
  if (!nesne) {
    dusen.push(`${ad}: dosya YOK`);
    return;
  }
  for (const [alan, tur] of Object.entries(alanlar)) {
    const d = nesne[alan];
    if (d === undefined) {
      dusen.push(`${ad}: "${alan}" alani YOK`);
      continue;
    }
    // `null` bilincli olarak izinli oldugu yerler var (skor, sonraki).
    if (d === null && tur.endsWith("?")) {
      gecti += 1;
      continue;
    }
    const gercek = Array.isArray(d) ? "array" : typeof d;
    const beklenen = tur.replace(/\?$/, "");
    if (gercek !== beklenen) {
      dusen.push(
        `${ad}: "${alan}" turu ${gercek}, beklenen ${beklenen}`,
      );
      continue;
    }
    gecti += 1;
  }
}

if (!fs.existsSync(KOK)) {
  console.error(`besleme bulunamadi: ${KOK}`);
  console.error("Once siteyi uretin: python site/insa.py");
  process.exit(1);
}

console.log("");
console.log("1. surum.json");
const surum = oku("surum.json");
dogrula("surum", surum, {
  surum: "number",
  uretildi: "string",
  onek: "string",
  sayfa_boyu: "number",
  beslemeler: "object",
});
if (surum) {
  for (const b of ["haber", "analiz", "piyasa", "one_cikan", "tel"]) {
    if (!surum.beslemeler[b]) dusen.push(`surum: "${b}" beslemesi bildirilmemis`);
    else gecti += 1;
  }
  // TEL AKISI STATIK OLMAMALI: kopyalanmis bir "canli" akis, insa
  // aninda donmus demektir.
  if (surum.beslemeler.tel?.statik !== false) {
    dusen.push("surum: tel beslemesi statik isaretli -- canli akis kopyalanmis");
  } else gecti += 1;
}

console.log("2. piyasa.json");
const piyasa = oku("piyasa.json");
dogrula("piyasa", piyasa, {
  veri_tarihi: "string",
  canli_degil: "boolean",
  aciklama: "string",
  kalemler: "array",
});
if (piyasa) {
  // CANLI IDDIA EDILMEMELI.
  if (piyasa.canli_degil !== true) {
    dusen.push("piyasa: canli_degil true DEGIL -- gecikmeli veri canli sunulur");
  } else gecti += 1;

  // LISANSSIZ SERI KACMAMALI. Kume Python tarafindan eleniyor; bu
  // sinama ciktida IKINCI bir kapi.
  const YASAK = ["SP500", "DJIA", "NASDAQCOM", "VIXCLS"];
  const kacak = piyasa.kalemler.filter((k) => YASAK.includes(k.kod));
  if (kacak.length) {
    dusen.push(
      `piyasa: LISANSSIZ seri ciktida: ${kacak.map((k) => k.kod).join(", ")}`,
    );
  } else gecti += 1;

  if (piyasa.kalemler.length === 0) {
    dusen.push("piyasa: hic kalem yok");
  } else {
    dogrula("piyasa.kalem[0]", piyasa.kalemler[0], {
      kod: "string",
      ad: "string",
      deger: "string",
      fark: "string",
      yon: "string",
      tarih: "string",
      bayat: "boolean",
      gun: "number",
      ritim: "string",
    });
    // HER KALEM KENDI VERI TARIHINI TASIMALI: sayi tek basina canli
    // fiyat izlenimi veriyor.
    const tarihsiz = piyasa.kalemler.filter((k) => !k.tarih);
    if (tarihsiz.length) {
      dusen.push(
        `piyasa: ${tarihsiz.length} kalem veri tarihi tasimiyor ` +
          `(${tarihsiz.map((k) => k.kod).join(", ")})`,
      );
    } else gecti += 1;
  }
}

console.log("3. one-cikan.json");
const one = oku("one-cikan.json");
dogrula("one-cikan", one, {
  surum: "number",
  uretildi: "string",
  kaynak: "string",
  haberler: "array",
  analizler: "array",
});

console.log("4. haber listesi ve detayi");
const hliste = oku("haber/sayfa-1.json");
dogrula("haber/sayfa-1", hliste, {
  surum: "number",
  sayfa: "number",
  sayfa_sayisi: "number",
  toplam_kayit: "number",
  sonraki: "string?",
  ogeler: "array",
});
if (hliste?.ogeler?.length) {
  dogrula("haber ozeti", hliste.ogeler[0], {
    tur: "string",
    slug: "string",
    yol: "string",
    baslik: "string",
    ozet: "string",
    konu: "string",
    kurum: "string",
    kurum_tam: "string",
    ticari: "boolean",
    kaynak_adres: "string",
    tarih: "string",
    foto: "string",
    foto_atif: "string",
  });
  const detay = oku(`haber/${hliste.ogeler[0].slug}.json`);
  dogrula("haber detayi", detay, {
    baslik_kaynak: "string",
    kaynak_ozeti: "string",
    neden_onemli: "string",
    kanallar: "array",
    cevrildi: "boolean",
    dil: "string",
    tarih_gorunur: "string",
  });

  // ATIF KURALLARI CIKTIDA DA GECERLI.
  const atifsizFoto = hliste.ogeler.filter((h) => h.foto && !h.foto_atif);
  if (atifsizFoto.length) {
    dusen.push(`haber: ${atifsizFoto.length} kayitta atifsiz fotograf`);
  } else gecti += 1;

  const atifsizTicari = hliste.ogeler.filter(
    (h) => h.ticari && !(h.kurum && h.kaynak_adres),
  );
  if (atifsizTicari.length) {
    dusen.push(`haber: ${atifsizTicari.length} ticari kayit atifsiz`);
  } else gecti += 1;

  // TARIH ISO OLMALI: uygulama siralama ve bicimlendirme icin ISO
  // bekliyor. Gorüntü bicimli tarih sessizce yanlis sira uretir.
  const ISO = /^\d{4}-\d{2}-\d{2}$/;
  const bozukTarih = hliste.ogeler.filter((h) => h.tarih && !ISO.test(h.tarih));
  if (bozukTarih.length) {
    dusen.push(`haber: ${bozukTarih.length} kayitta ISO olmayan tarih`);
  } else gecti += 1;
}

console.log("5. analiz listesi ve detayi");
const aliste = oku("analiz/sayfa-1.json");
dogrula("analiz/sayfa-1", aliste, {
  sayfa: "number",
  sayfa_sayisi: "number",
  ogeler: "array",
});
if (aliste?.ogeler?.length) {
  dogrula("analiz ozeti", aliste.ogeler[0], {
    tur: "string",
    slug: "string",
    yol: "string",
    baslik: "string",
    ozet: "string",
    sirket: "string",
    kod: "string",
    sektor: "string",
    donem: "string",
    kategori: "string",
    tarih: "string",
    skor: "string?",
    okuma_dk: "number",
    yazar: "string",
    unvan: "string",
    imzali: "boolean",
    kurgusal: "boolean",
    amblem: "string",
    foto: "string",
    foto_atif: "string",
  });
  const detay = oku(`analiz/${aliste.ogeler[0].slug}.json`);
  dogrula("analiz detayi", detay, {
    govde_html: "string",
    kapsam: "string",
    veri_kaynagi: "string",
    kaynaklar: "array",
    kriterler: "array",
    bolumler: "array",
    sayimlar: "array",
    kelime: "number",
  });
  // SLUG BOS OLAMAZ: bos slug "/analiz//" gibi bozuk bir adres ve
  // detay dosyasi da yazilmiyor -- karta dokunan okur 404 gorur.
  const slugsuz = aliste.ogeler.filter((a) => !a.slug);
  if (slugsuz.length) {
    dusen.push(`analiz: ${slugsuz.length} kayitta slug bos`);
  } else gecti += 1;
}

console.log("6. tema.json");
const tema = oku("tema.json");
dogrula("tema", tema, {
  surum: "number",
  kaynak: "string",
  zorunlu: "array",
  acik: "object",
  koyu: "object",
});
if (tema) {
  for (const jeton of tema.zorunlu) {
    if (!tema.acik[jeton]) dusen.push(`tema: acik temada --${jeton} YOK`);
    else gecti += 1;
    if (!tema.koyu[jeton]) dusen.push(`tema: koyu temada --${jeton} YOK`);
    else gecti += 1;
  }
}

console.log("");
if (dusen.length) {
  console.error(`DUSTU (${dusen.length} sorun):`);
  for (const d of dusen) console.error(`  - ${d}`);
  process.exit(1);
}
console.log(`TUM SOZLESME SINAMALARI GECTI (${gecti} alan)`);
