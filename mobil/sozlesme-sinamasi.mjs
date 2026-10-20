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

// VARSAYILAN: yerel uretilmis cikti. `--kok <dizin>` ile BASKA bir
// besleme kopyasi da sinanabilir -- ornegin uretimden indirilmis
// olani. Yerelde gecip CANLIDA bozuk olan bir besleme mumkun:
// dagitim eksik dosya yukleyebilir, eski surum kalabilir. "Yerelde
// calisiyor" bu depoda yeterli bir cumle degil.
const _i = process.argv.indexOf("--kok");
const KOK = _i > 0 && process.argv[_i + 1]
  ? path.resolve(process.argv[_i + 1])
  : path.resolve(import.meta.dirname, "..", "site", "cikti", "v1");
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

console.log("6. takvim.json");
const takvim = oku("takvim.json");
dogrula("takvim", takvim, {
  surum: "number",
  uretildi: "string",
  saat_dilimi: "string",
  aciklama: "string",
  ogeler: "array",
});
if (takvim) {
  // SAAT DILIMI BESLEMEDE YAZILI OLMALI: bir veri aciklamasinin
  // saati, hangi dilimde oldugu yazilmadan anlamsiz.
  if (!takvim.saat_dilimi) {
    dusen.push("takvim: saat_dilimi BOS -- saatler yorumlanamaz");
  } else gecti += 1;

  if (takvim.ogeler.length === 0) {
    // Bos takvim bir kusur DEGIL (o hafta buyuk yayin olmayabilir),
    // ama sessizce gecilmemeli.
    console.log("    (takvim bos -- alan denetimi atlandi)");
  } else {
    const o = takvim.ogeler[0];
    dogrula("takvim ogesi", o, {
      ad: "string",
      ulke: "string",
      seri: "string",
      onem: "number",
      an: "string",
      yerel: "string",
      gun: "string",
      saat: "string",
      saat_dilimi: "string",
      kesin: "boolean",
      kaynak: "string",
      aciklandi: "boolean",
      dallar: "array",
    });

    // HER OGE KENDI SAAT DILIMINI TASIMALI.
    const dilimsiz = takvim.ogeler.filter((x) => !x.saat_dilimi);
    if (dilimsiz.length) {
      dusen.push(`takvim: ${dilimsiz.length} ogede saat_dilimi yok`);
    } else gecti += 1;

    // SURPRIZ YALNIZCA GERCEK KONSENSUS VARKEN OLMALI.
    //
    // Esik onceki degerse "beklentinin ustunde geldi" demek yanlis:
    // ortada bir beklenti YOK, yalnizca bir onceki rakam var.
    const yanlisSurpriz = takvim.ogeler.filter(
      (x) => x.surpriz && x.esik_kaynak !== "beklenti",
    );
    if (yanlisSurpriz.length) {
      dusen.push(
        `takvim: ${yanlisSurpriz.length} ogede KONSENSUS YOKKEN surpriz`,
      );
    } else gecti += 1;

    // ACIKLANMAMIS VERIDE `gerceklesen` OLMAMALI.
    const sahteAciklama = takvim.ogeler.filter(
      (x) => !x.aciklandi && x.gerceklesen,
    );
    if (sahteAciklama.length) {
      dusen.push(
        `takvim: ${sahteAciklama.length} ogede aciklanmadan gerceklesen var`,
      );
    } else gecti += 1;

    // SIRALAMA: en yakin once.
    const anlar = takvim.ogeler.map((x) => x.an);
    if (anlar.join("|") !== [...anlar].sort().join("|")) {
      dusen.push("takvim: ogeler zamana gore SIRALI DEGIL");
    } else gecti += 1;
  }
}

console.log("7. varlik.json ve varlik detayi");
const vdizin = oku("varlik.json");
dogrula("varlik dizini", vdizin, {
  surum: "number",
  uretildi: "string",
  toplam: "number",
  ogeler: "array",
});
if (vdizin?.ogeler?.length) {
  dogrula("varlik dizin ogesi", vdizin.ogeler[0], {
    kod: "string",
    yol: "string",
    ad: "string",
    tur: "string",
    haber_sayisi: "number",
    veri_var: "boolean",
    deger: "string",
    // Birim LISTEDE de olmali: "29,00" tek basina ne oldugunu
    // soylemiyor. Bos olabilir (oran serilerinde deger zaten "%"
    // tasiyor) ama ALAN bulunmali -- dususu sessiz kalmasin.
    birim: "string",
    yon: "string",
    tarih: "string",
    dosya: "string",
  });

  // DIZIN DETAYIN TAMAMINI TASIMAMALI: 75 varligin butun baglarini
  // ve haberlerini ilk acilista indirmek olurdu.
  const sismis = vdizin.ogeler.filter((x) => x.baglar || x.haberler);
  if (sismis.length) {
    dusen.push(`varlik dizini: ${sismis.length} ogede detay alanlari var`);
  } else gecti += 1;

  // DIZIN HABER SAYISINA GORE SIRALI.
  const say = vdizin.ogeler.map((x) => x.haber_sayisi);
  const sirali = [...say].sort((a, b) => b - a);
  if (say.join("|") !== sirali.join("|")) {
    dusen.push("varlik dizini: haber sayisina gore SIRALI DEGIL");
  } else gecti += 1;

  // DEGERI OLMAYAN OGEDE `deger` BOS OLMALI -- tersi, yayimlanmamasi
  // gereken bir degeri dizinde sizdirmak demek.
  const celiski = vdizin.ogeler.filter((x) => !x.veri_var && x.deger);
  if (celiski.length) {
    dusen.push(
      `varlik dizini: ${celiski.length} ogede veri_var=false AMA deger dolu`,
    );
  } else gecti += 1;

  // DETAY DOSYALARI: ilk ucu acilabilmeli.
  for (const o of vdizin.ogeler.slice(0, 3)) {
    const yol = o.dosya.replace(/^\/v1\//, "");
    const det = oku(yol);
    if (!det) {
      dusen.push(`varlik detayi YOK: ${yol}`);
      continue;
    }
    dogrula(`varlik detayi ${o.kod}`, det, {
      kod: "string",
      yol: "string",
      ad: "string",
      tur: "string",
      aciklama: "string",
      haber_sayisi: "number",
      seri_kodu: "string",
      veri_var: "boolean",
      baglar: "array",
      haberler: "array",
    });
  }

  // LISANS: LISANSSIZ SERIYE BAGLI VARLIGIN DEGERI OLMAMALI.
  //
  // Olculdu (yayinda, duzeltildi): /varlik/nasdaq/, /varlik/sp500/
  // ve /varlik/vix/ sayfalari "26.180 endeks +%0,4" yaziyordu --
  // seriyi yeniden yayimliyorduk ve lisans bizde degil.
  const LISANSSIZ = ["SP500", "DJIA", "NASDAQCOM", "VIXCLS"];
  const kacak = [];
  let bakilan = 0;
  for (const o of vdizin.ogeler) {
    const det = oku(o.dosya.replace(/^\/v1\//, ""));
    if (!det) continue;
    bakilan += 1;
    if (LISANSSIZ.includes(det.seri_kodu) && det.veri) {
      kacak.push(det.kod);
    }
  }
  if (kacak.length) {
    dusen.push(`varlik: LISANSSIZ serinin DEGERI yayimlanmis: ${kacak}`);
  } else {
    gecti += 1;
    console.log(`    ${bakilan} varlik detayi lisans acisindan tarandi`);
  }
}

console.log("8. senaryo-kurallari.json");
const skur = oku("senaryo-kurallari.json");
dogrula("senaryo kurallari", skur, {
  surum: "number",
  olcutler: "array",
  yonler: "array",
  ufuklar: "array",
  sinirlar: "object",
  notlar: "object",
});
if (skur) {
  // HER OLCUTUN OKUNABILIR ADI OLMALI: ciplak "TP.FE25.OKTG04"
  // kullaniciya hicbir sey anlatmiyor.
  const adsiz = skur.olcutler.filter((o) => !o.kod || !o.ad);
  if (adsiz.length) {
    dusen.push(`senaryo: ${adsiz.length} olcutte kod ya da ad eksik`);
  } else gecti += 1;

  if (skur.olcutler.length < 5) {
    dusen.push(
      `senaryo: yalnizca ${skur.olcutler.length} olcut --` +
        " web formu ayristirilamamis olabilir",
    );
  } else gecti += 1;

  // UZUNLUK SINIRLARI UYGULAMAYA ULASMALI: kullanicinin sunucudan
  // hata almasi, girdide uyarilmasindan kotu.
  for (const alan of ["kosul", "sonuc", "gerekce", "curutme"]) {
    const s = skur.sinirlar[alan];
    if (!s || typeof s.en_cok !== "number" || s.en_cok <= 0) {
      dusen.push(`senaryo: "${alan}" uzunluk siniri yok`);
    } else gecti += 1;
  }

  // YON KODLARI worker'in kabul ettikleri olmali.
  const yonKod = skur.yonler.map((y) => y.kod).sort().join(",");
  if (yonKod !== "altinda,ustunde") {
    dusen.push(`senaryo: yon kodlari beklenmedik: ${yonKod}`);
  } else gecti += 1;

  // CURUTME NOTU TASINMALI: bir senaryoyu bir gorusten ayiran tek
  // sey, yazarin kendi kendini yanlislayabilecek gelismeyi
  // onceden yazmasi. Not dusmezse o alan anlamsiz gorunur.
  if (!skur.notlar.curutme || !skur.notlar.olcut) {
    dusen.push("senaryo: aciklama notlari eksik");
  } else gecti += 1;
}

console.log("9. arama.json");
const arama = oku("arama.json");
dogrula("arama", arama, {
  surum: "number",
  uretildi: "string",
  katlama: "object",
  toplam: "number",
  kayitlar: "array",
});
if (arama?.kayitlar?.length) {
  dogrula("arama kaydi", arama.kayitlar[0], {
    t: "string",
    b: "string",
    s: "string",
    d: "string",
    k: "string",
  });

  // KATLAMA TABLOSU BOS OLMAMALI: bos olursa uygulama yedek
  // tabloya duser ve site ile uygulama FARKLI sonuc verebilir.
  if (Object.keys(arama.katlama).length < 10) {
    dusen.push(
      `arama: katlama tablosu eksik (${Object.keys(arama.katlama).length})` +
        " -- uygulama yedege duser, site ile ayrisir",
    );
  } else gecti += 1;

  // TURKCE HARFLERIN HEPSI TABLODA OLMALI.
  const gerekli = ["ı", "ş", "ğ", "ü", "ö", "ç"];
  const eksik = gerekli.filter((h) => !arama.katlama[h]);
  if (eksik.length) {
    dusen.push(`arama: katlama tablosunda eksik harf: ${eksik.join(", ")}`);
  } else gecti += 1;

  // ARANAMAZ KAYIT OLMAMALI.
  const aranamaz = arama.kayitlar.filter((k) => !k.b || !k.s);
  if (aranamaz.length) {
    dusen.push(`arama: ${aranamaz.length} kayitta baslik ya da slug yok`);
  } else gecti += 1;

  // UC TUR DE BULUNMALI: biri dusesse arama sessizce eksilirdi.
  const turler = new Set(arama.kayitlar.map((k) => k.t));
  for (const tur of ["haber", "analiz", "varlik"]) {
    if (!turler.has(tur)) {
      dusen.push(`arama: "${tur}" turunden HIC kayit yok`);
    } else gecti += 1;
  }

  // DIZIN OZET TASIMAMALI -- boyutu iki katina cikarirdi.
  const sismis = arama.kayitlar.filter((k) => k.o || k.ozet);
  if (sismis.length) {
    dusen.push(`arama: ${sismis.length} kayitta ozet var (dizin sismis)`);
  } else gecti += 1;
}

console.log("10. tema.json");
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
