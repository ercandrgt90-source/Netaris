/* Tel -- yeniden insa beklemeden taze baslik.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * Olculdu (2026-09-30): zamanlanmis GitHub kosulari cron'un istedigi
 * ~37 kosunun %19'unu teslim ediyor; ardisik kosular arasindaki
 * ortanca boslук ~4 saat. Bosluğu kapatan nobetci GitHub'a jetonla
 * gidiyordu ve jeton olunce tempo tabana dustu. Tel, tazeligi
 * Cloudflare'in kendi cron'una tasiyarak o bagimliligi kaldiriyor.
 *
 * NEDEN SINANMASI SART
 * --------------------
 * Bu modulun iki yanlis davranisi da SESSIZ ve biri HUKUKI:
 *
 *   * Atifsiz oge yazarsa: `ticari` kaynakta kurum adi VE baglanti
 *     gostermek zorunlu (bkz. haber_botu/kaynak/besleme.py). Atifsiz
 *     bir baslik sayfada gorunurse ihlal SESSIZCE olusur -- sayfa
 *     duzgun gorunur, yalnizca kunye yoktur.
 *   * Hic oge yazmazsa: site yine bayat kalir ama mekanizma VARMIS
 *     gibi gorunur. Bugun tam bu bicimde bir kusur cikti: yanlis
 *     `import` bicimi `try/except` tarafindan yutuldu, blok hic
 *     calismadi ve site YESIL kuruldu.
 *
 * Calistirma:  node site/test_tel.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const crypto = require("crypto");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  const a = JSON.stringify(bulunan);
  const b = JSON.stringify(beklenen);
  if (a === b) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + b);
    console.log("         bulunan : " + a);
  }
}

const dogru = (k, a) => esit(Boolean(k), true, a);

/* worker.js bir ES modulu; `export default` blogu VM'de calismaz. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

/* --- Yayilan kurallarin GERCEGI okunuyor ------------------------
   Uydurma bir kural nesnesi kullansaydik, `insa.py`in yaydigi
   dosyanin bicimi degistiginde bu sinama yine gecerdi -- yani
   sinama, olcmesi gereken baglantinin tam ustunden atlardi. */
const KURAL_YOLU = path.join(__dirname, "cikti", "tel-kurallari.json");
const KURALLAR = fs.existsSync(KURAL_YOLU)
  ? JSON.parse(fs.readFileSync(KURAL_YOLU, "utf8"))
  : null;

let sahteYanitlar = [];
let fetchCagrilari = [];
function sahteFetch(url, ayar) {
  fetchCagrilari.push({ url: String(url), ayar: ayar || {} });
  const y = sahteYanitlar.shift();
  if (!y) return Promise.resolve({ ok: false, status: 500 });
  return Promise.resolve(y);
}

const ortam = {
  console: { log() {}, error() {} },
  fetch: sahteFetch,
  Date, Number, JSON, Promise, String, RegExp, Math, Array, Boolean,
  Object, Error, TextEncoder, encodeURIComponent, isNaN,
  crypto: { subtle: { digest: (_a, v) =>
    Promise.resolve(crypto.createHash("sha256").update(Buffer.from(v))
      .digest().buffer) } },
  URL,
  Uint8Array,
  Response: class {
    constructor(g, o) { this._g = g; this.status = (o && o.status) || 200; }
    json() { return Promise.resolve(JSON.parse(this._g)); }
  },
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const {
  telRssAyristir, telMetin, telOnekSil, telKonuSec, telTarih, telTopla,
  telListe,
} = ortam;

/* --- Sahte D1 ----------------------------------------------------
   Gercek D1 yok; yazilan satirlari TOPLUYOR ki "ne yazildi"
   sorulabilsin. Sema kisitlari burada YOK -- bu kasitli: kod
   tarafinin de elemesi gerektigini sinamak istiyoruz. Semadaki
   `CHECK` ikinci savunma hatti, birincisi degil. */
function sahteDB() {
  const yazilan = [];
  const izler = [];
  const semaCagrilari = [];
  const ceviri = new Map();
  return {
    yazilan,
    izler,
    semaCagrilari,
    /* `telSemaKur` bunu kullaniyor. Sahte DB'de `batch` OLMASAYDI
       cagri istisna atar, yutulur ve sema kurulumu sinamada HIC
       kosmazdi -- yani olculdugu sanilan sey olculmemis olurdu. */
    batch(ifadeler) {
      semaCagrilari.push(ifadeler.length);
      return Promise.resolve([]);
    },
    prepare(sorgu) {
      const s = sorgu;
      return {
        bind(...a) { this._a = a; return this; },
        async first() {
          if (/FROM tel_ceviri/.test(s)) {
            const v = ceviri.get(this._a[0]);
            return v ? { ceviri: v } : null;
          }
          return null;              /* tel'de kayit yok -> yeni oge */
        },
        async all() { return { results: [] }; },
        async run() {
          if (/INSERT OR REPLACE INTO tel_ceviri/.test(s)) {
            ceviri.set(this._a[0], this._a[1]);
          } else if (/INSERT INTO tel_iz/.test(s)) {
            izler.push({
              an: this._a[0], kod: this._a[1], http: this._a[2],
              ayrisan: this._a[3], yazilan: this._a[4],
              ceviri: this._a[5], hata: this._a[6],
            });
          } else if (/INSERT OR REPLACE INTO tel\b/.test(s)) {
            yazilan.push({
              kimlik: this._a[0], kod: this._a[1], kurum: this._a[2],
              kurum_tam: this._a[3], adres: this._a[4],
              baslik: this._a[5], baslik_tr: this._a[6], konu: this._a[7],
              ticari: this._a[8], tarih: this._a[9],
            });
          }
          return {};
        },
      };
    },
  };
}

function kuralliOrtam(db, kurallar) {
  return {
    DB: db,
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        json: () => Promise.resolve(kurallar),
      }),
    },
  };
}

const RSS_ORNEK = `<rss><channel>
<item><title>FinancialJuice: US CPI YoY Actual 3.1% (Forecast 3.0%)</title>
<link>https://www.financialjuice.com/News/1/a.aspx</link>
<pubDate>Wed, 30 Sep 2026 11:31:51 GMT</pubDate>
<guid isPermaLink="false">111</guid></item>
<item><title>Fed&amp;apos;s Powell speaks on rates</title>
<link>https://www.financialjuice.com/News/2/b.aspx</link>
<pubDate>Wed, 30 Sep 2026 11:20:00 GMT</pubDate>
<guid isPermaLink="false">222</guid></item>
<item><title>BAGLANTISIZ OGE</title>
<link></link>
<pubDate>Wed, 30 Sep 2026 11:10:00 GMT</pubDate>
<guid isPermaLink="false">333</guid></item>
</channel></rss>`;

const TEST_KURAL = {
  surum: 2,
  saklama_saat: 36,
  ceviri: {
    uc: "https://ornek.ceviri/get",
    cift: "en|tr",
    iletisim: "destek@netaris.net",
    tur_siniri: 12,
  },
  beslemeler: [{
    kod: "FJUICE", kurum: "FinancialJuice", kurum_tam: "FinancialJuice",
    besleme: "https://ornek/rss", konu: "Şirket haberleri",
    dil: "en", ticari: true, sinir: 60,
  }],
  onekler: ["^\\s*FinancialJuice\\s*:\\s*"],
  veri_konulari: [[["cpi", "inflation"], "Enflasyon"],
                  [["interest rate", "fed"], "Para politikası"]],
};

async function kos() {
  console.log("\nAyristirma");
  const o = telRssAyristir(RSS_ORNEK);
  esit(o.length, 3, "uc oge ayristirildi");
  esit(o[0].guid, "111", "guid okundu");
  esit(o[0].adres, "https://www.financialjuice.com/News/1/a.aspx",
       "baglanti okundu");

  console.log("\nMetin cozme");
  esit(telMetin("a &amp;lt; b"), "a &lt; b",
       "&amp; EN SONA cozuluyor (cift cozme yok)");
  esit(telMetin("<![CDATA[Bir  baslik]]>"), "Bir  baslik", "CDATA cozuldu");
  esit(telMetin("&quot;x&quot;"), '"x"', "tirnak cozuldu");

  console.log("\nOnek ve konu");
  esit(telOnekSil("FinancialJuice: US CPI YoY", TEST_KURAL), "US CPI YoY",
       "kaynak onegi silindi");
  esit(telKonuSec("US CPI YoY Actual 3.1%", TEST_KURAL, "VARSAYILAN"),
       "Enflasyon", "veri tablosundan konu");
  esit(telKonuSec("Something entirely unrelated", TEST_KURAL, "VARSAYILAN"),
       "VARSAYILAN", "bulamazsa VARSAYILAN -- konu kararI VERILMIYOR");

  console.log("\nTarih");
  esit(telTarih("Wed, 30 Sep 2026 11:31:51 GMT"), "2026-09-30T11:31:51Z",
       "RFC-822 -> ISO");
  esit(telTarih("cozulemez"), null, "cozulemeyen tarih null");

  /* SEMAYI WORKER KENDISI KURUYOR.
     Olculdu (2026-09-30): "D1 göçü" adimi `success` bildirdi ama
     tablolar kurulmamisti -- `continue-on-error: true` olan bir
     adim, komut dusse bile adim API'sinde `success` gorunuyor.
     Worker D1'e BAGLANTI uzerinden eristigi icin kendi tablosunu
     kurabiliyor ve o ariza noktasi tumden dusuyor. */
  console.log("\nSema kurulumu");
  const dbSema = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: false, status: 500 }, { ok: false, status: 500 },
  ];
  await telTopla(kuralliOrtam(dbSema, TEST_KURAL));
  esit(dbSema.semaCagrilari.length, 1, "sema BIR KEZ kuruldu");
  esit(dbSema.semaCagrilari[0], 5, "bes ifade (3 tablo + 2 indeks)");
  const dbSema2 = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: false, status: 500 }, { ok: false, status: 500 },
  ];
  await telTopla(kuralliOrtam(dbSema2, TEST_KURAL));
  esit(dbSema2.semaCagrilari.length, 0,
       "ikinci turda yeniden kurulmuyor (izolasyon basina bir kez)");

  console.log("\nToplama -- ATIF ZORUNLU");
  let db = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    /* ceviri cagrilari */
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "ABD TÜFE yıllık %3,1" } }) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "Powell faiz konuştu" } }) },
  ];
  await telTopla(kuralliOrtam(db, TEST_KURAL));
  esit(db.yazilan.length, 2, "BAGLANTISIZ oge YAZILMADI (3 -> 2)");
  dogru(db.yazilan.every((s) => /^https?:\/\//.test(s.adres)),
        "yazilan her satirda gecerli baglanti var");
  dogru(db.yazilan.every((s) => s.kurum && s.kurum_tam),
        "yazilan her satirda kunye var");
  esit(db.yazilan[0].ticari, 1, "ticari bayragi korundu");
  esit(db.yazilan[0].baslik, "US CPI YoY Actual 3.1% (Forecast 3.0%)",
       "baslikta kaynak onegi yok");
  esit(db.yazilan[0].konu, "Enflasyon", "konu veri tablosundan");

  console.log("\nHiz siniri (429) -- TEKRAR DENENMIYOR");
  db = sahteDB();
  fetchCagrilari = [];
  sahteYanitlar = [{ ok: false, status: 429 }];
  await telTopla(kuralliOrtam(db, TEST_KURAL));
  esit(db.yazilan.length, 0, "429'da oge yazilmadi");
  esit(fetchCagrilari.length, 1,
       "429'da tek istek -- kaynagin sinirI zorlanmiyor");

  console.log("\nKimlik gonderiliyor");
  dogru(/Netaris/.test(fetchCagrilari[0].ayar.headers["User-Agent"]),
        "besleme istegi kendini TANITIYOR");

  /* IZ -- teshisin kendisi de dogrulanmali.
     Tel dagitildi, cron dondu, `/api/tel` BOS kaldi ve sebebi
     disaridan gorulemedi. Iz tam o sorunun cevabi; ama iz yazilmiyor
     olsaydi bunu da fark edemezdik. */
  console.log("\nTur izi");
  esit(db.izler.length, 1, "429 turunda da iz YAZILDI");
  esit(db.izler[0].http, 429, "izde besleme yanit kodu var");
  esit(db.izler[0].ayrisan, 0, "429'da ayrisan oge 0");
  esit(db.izler[0].yazilan, 0, "429'da yazilan oge 0");

  const db3 = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "ABD TÜFE yıllık %3,1" } }) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "Powell faiz konuştu" } }) },
  ];
  await telTopla(kuralliOrtam(db3, TEST_KURAL));
  esit(db3.izler.length, 1, "basarili turda da iz yazildi");
  esit(db3.izler[0].http, 200, "izde 200 kayitli");
  esit(db3.izler[0].ayrisan, 3, "ayrisan oge sayisi izde");
  esit(db3.izler[0].yazilan, 2, "yazilan oge sayisi izde (atifsiz elendi)");
  esit(db3.izler[0].ceviri, 2, "ceviri sayisi izde");
  esit(db3.izler[0].hata, null, "saglikli turda hata alani bos");

  /* CEVIRI ISTEMCISI PYTHON'UNKIYLE AYNI SOZLESMEYE UYMALI.
     Olculdu (2026-09-30, canli): ilk tur 60 oge yazdi ve SIFIR
     ceviri yapti. JS surumu `ceviri.py`den dort yerde ayrilmisti:
     `de` gonderilmiyordu (kota 1.000 -> 50.000), `quotaFinished`
     bakilmiyordu, "MYMEMORY WARNING" ceviri saniliyordu ve tur
     sinirI yoktu. */
  console.log("\nCeviri sozlesmesi");
  const cevIstek = fetchCagrilari.filter(
    (c) => c.url.indexOf("ornek.ceviri") !== -1);
  dogru(cevIstek.length >= 1, "ceviri ucu cagrildi");
  dogru(cevIstek[0].url.indexOf("de=destek%40netaris.net") !== -1,
        "`de` parametresi gonderiliyor (kota 1.000 -> 50.000)");
  dogru(cevIstek[0].url.indexOf("langpair=en%7Ctr") !== -1,
        "dil cifti gonderiliyor");

  /* Kota bitmis: uc 200 donuyor ama govdede soyluyor. */
  const dbKota = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: true, status: 200,
      json: () => Promise.resolve({ quotaFinished: true,
                                    responseData: { translatedText: "x" } }) },
    { ok: true, status: 200,
      json: () => Promise.resolve({ quotaFinished: true,
                                    responseData: { translatedText: "x" } }) },
  ];
  await telTopla(kuralliOrtam(dbKota, TEST_KURAL));
  esit(dbKota.yazilan.length, 2, "kota bitince oge YINE yaziliyor");
  esit(dbKota.yazilan[0].baslik_tr, "", "kota bitince ceviri bos");
  esit(dbKota.izler[0].ceviri, 0, "kota bitince ceviri sayisi 0");
  dogru(/kota bitti/.test(dbKota.izler[0].hata || ""),
        "kota bitimi IZDE yaziyor");

  /* Uc, ceviremedigini CEVIRI ALANINDA soyluyor. */
  const dbUyari = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText:
          "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS" } }) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "MYMEMORY WARNING: ..." } }) },
  ];
  await telTopla(kuralliOrtam(dbUyari, TEST_KURAL));
  esit(dbUyari.yazilan[0].baslik_tr, "",
       "MYMEMORY WARNING ceviri sayilmiyor");
  dogru(/MYMEMORY WARNING/.test(dbUyari.izler[0].hata || ""),
        "uyari metni IZDE yaziyor");

  /* Tur sinirI: bir turda sinirsiz ceviri istenmiyor. */
  const dbSinir = sahteDB();
  const azKural = JSON.parse(JSON.stringify(TEST_KURAL));
  azKural.ceviri.tur_siniri = 1;
  sahteYanitlar = [
    { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "Birinci çeviri" } }) },
    { ok: true, status: 200, json: () => Promise.resolve(
        { responseData: { translatedText: "Ikinci çeviri" } }) },
  ];
  await telTopla(kuralliOrtam(dbSinir, azKural));
  esit(dbSinir.izler[0].ceviri, 1, "tur sinirI uygulaniyor");
  esit(dbSinir.yazilan.length, 2,
       "sinira takilan oge YINE yaziliyor (cevirisiz)");

  /* KURALLAR OKUNAMAZSA -- tani aracinin en kor oldugu yer.
     Ilk surumde `telTopla` burada sessizce donuyordu ve iz dongunun
     ICINDE yaziliyordu; yani teshis edilmek istenen ILK durum hic
     iz birakmiyordu. */
  console.log("\nKurallar okunamadiginda");
  const db4 = sahteDB();
  sahteYanitlar = [{ ok: false, status: 404 }];   /* yedek fetch de dussun */
  await telTopla({
    DB: db4,
    ASSETS: { fetch: () => Promise.resolve({ ok: false, status: 404 }) },
  });
  esit(db4.yazilan.length, 0, "kuralsiz turda oge yazilmadi");
  esit(db4.izler.length, 1, "kuralsiz turda da IZ yazildi");
  esit(db4.izler[0].kod, "(kurallar)", "iz kuralsizligi isaretliyor");
  dogru(db4.izler[0].hata, "iz sebebi tasiyor");

  /* YEDEK YOL: varlik baglantisi susarsa duz fetch denenmeli.
     `scheduled` baglaminda varlik baglantisinin `fetch` baglamindaki
     gibi davranacagi bir VARSAYIMDI; yedek onu varsayim olmaktan
     cikariyor. */
  console.log("\nKurallarin yedek yolu");
  const db5 = sahteDB();
  sahteYanitlar = [
    { ok: true, status: 200,
      json: () => Promise.resolve(TEST_KURAL) },      /* yedek fetch */
    { ok: true, status: 200,
      text: () => Promise.resolve(RSS_ORNEK) },       /* besleme */
    { ok: false, status: 500 }, { ok: false, status: 500 },
  ];
  await telTopla({
    DB: db5,
    ASSETS: { fetch: () => { throw new Error("assets yok"); } },
  });
  esit(db5.yazilan.length, 2,
       "varlik baglantisi dusunce yedek fetch ile calisti");
  esit(db5.izler[0].http, 200, "yedek yolda da iz dogru");

  console.log("\nYayilan gercek kurallar");
  if (!KURALLAR) {
    /* CIKTI YOKSA ATLANIYOR -- KIRMIZI YANMIYOR.
     *
     * Deponun kurali bu: uretilen ciktiyi okuyan sinamalar cikti
     * yokken "ATLANDI" deyip 0 ile cikiyor (bkz.
     * `test_ticari_atif.py`). Sebebi CI sirasi: `otomasyon.yml`de
     * testler INSADAN ONCE kosuyor, yani o anda `site/cikti` henuz
     * yok.
     *
     * Ilk yazimda burasi KALDI veriyordu ve kosu #1497 tam bu
     * yuzden dustu -- yerelde 119 sinamanin 119'u yesildi cunku
     * yerelde cikti VARDI. Ardindan "gizlilik beyani" adimi da
     * dustu; o bagimsiz bir kusur degil, ayni zincirin devami:
     * insa atlandigi icin denetleyecek cikti yoktu.
     *
     * ATLAMAK BURADA GUVENLI, cunku sozlesmenin ASIL bekcisi
     * `test_tel_kurallari.py`: o, `insa.tel_kurallari_uret`i
     * DOGRUDAN cagiriyor ve ciktiya hic ihtiyac duymuyor. Burasi
     * yalnizca "yayilan dosya gercekten okunabiliyor mu" ek
     * kontrolu. */
    console.log("  ATLANDI  cikti/tel-kurallari.json yok "
                + "(once `python site/insa.py`)");
  } else {
    dogru(Array.isArray(KURALLAR.beslemeler) && KURALLAR.beslemeler.length > 0,
          "yayilan dosyada besleme var");
    dogru(KURALLAR.beslemeler.every((b) => b.kurum && b.kurum_tam && b.besleme),
          "yayilan her beslemede kunye alanlari tam");
    /* Gercek kurallarla da ayni RSS'i isleyebilmeli: yayilan bicim
       ile kodun bekledigi bicim AYRISIRSA burada goruluyor. */
    const db2 = sahteDB();
    sahteYanitlar = [
      { ok: true, status: 200, text: () => Promise.resolve(RSS_ORNEK) },
      { ok: false, status: 500 }, { ok: false, status: 500 },
    ];
    await telTopla(kuralliOrtam(db2, KURALLAR));
    esit(db2.yazilan.length, 2, "gercek kurallarla da iki oge yazildi");
    dogru(db2.yazilan.every((s) => s.adres && s.kurum),
          "gercek kurallarla atif alanlari dolu");
    /* Ceviri ucu dustu; oge YINE yazilmali, orijinal basligiyla. */
    esit(db2.yazilan[0].baslik_tr, "",
         "ceviri dusunce oge yine yazildi (bos ceviri)");
  }

  console.log("\nListe ucu");
  const listeDB = {
    prepare() {
      return {
        bind() { return this; },
        async all() {
          return { results: [{
            kurum: "FinancialJuice", kurum_tam: "FinancialJuice",
            adres: "https://x/1", baslik_kaynak: "US CPI",
            baslik_tr: "ABD TÜFE", konu: "Enflasyon", ticari: 1,
            tarih: "2026-09-30T11:00:00Z",
          }, {
            kurum: "FinancialJuice", kurum_tam: "FinancialJuice",
            adres: "https://x/2", baslik_kaynak: "Only source",
            baslik_tr: "", konu: "Borsa", ticari: 1,
            tarih: "2026-09-30T10:00:00Z",
          }] };
        },
      };
    },
  };
  /* `insa.py` `isoformat()` kullaniyor: `+00:00` bicimi. Uc bunu
     `Z` bicimine cevirmezse SQLite metin karsilastirmasi 19.
     karakterde `Z` ile `+`i kiyaslar ve suzgec sessizce yanlis
     calisir. Sinama bilerek O BICIMI gonderiyor. */
  const y = await telListe(
    { url: "https://netaris.net/api/tel?sonra=2026-09-30T09:00:00%2B00:00" },
    { DB: listeDB });
  const d = await y.json();
  esit(d.ogeler.length, 2, "iki oge dondu");
  esit(d.ogeler[0].baslik, "ABD TÜFE", "cevrili baslik tercih edildi");
  esit(d.ogeler[0].cevrildi, true, "ceviri BILDIRILIYOR");
  esit(d.ogeler[1].baslik, "Only source", "ceviri yoksa orijinal");
  esit(d.ogeler[1].cevrildi, false, "cevrilmemis oge boyle isaretlendi");
  dogru(d.ogeler.every((o) => o.adres && o.kurum),
        "her yanit ogesinde atif alanlari var");

  /* TANILAMA UCU -- "sessiz mi, bozuk mu" ayrimi.
     Bos liste dort ayri sebepten gelebiliyor ve disaridan bakan
     biri hicbirini ayirt edemez. Tanilama o dordunu ayiriyor; ama
     tanilamanin KENDISI dogrulanmazsa o da yalnizca bir iyi niyet
     beyani olur. */
  console.log("\nTanilama ucu");
  const { telDurum } = ortam;

  /* 1) Tablo YOK: goc kosmamis. */
  const tablosuz = {
    DB: { prepare() {
      return { bind() { return this; },
               first() { throw new Error("no such table: tel"); } };
    } },
    ASSETS: { fetch: () => Promise.resolve({
      ok: true, json: () => Promise.resolve(TEST_KURAL) }) },
  };
  const d1 = await (await telDurum(tablosuz)).json();
  esit(d1.tablo_var, false, "tablo yoksa tablo_var=false");
  dogru(d1.tablo_hatasi, "tablo yoksa SEBEBI bildiriliyor");
  esit(d1.kurallar_okundu, true, "kurallar ayrica okunabiliyor");

  /* 2) Kurallar YOK: insa calismamis ya da dosya yayilmamis. */
  const kuralsiz = {
    DB: { prepare() {
      return { bind() { return this; },
               first: async () => ({ n: 0, yeni: null, eski: null }) };
    } },
    ASSETS: { fetch: () => Promise.resolve({ ok: false, status: 404 }) },
  };
  const d2 = await (await telDurum(kuralsiz)).json();
  esit(d2.kurallar_okundu, false, "kurallar okunamazsa false");
  esit(d2.tablo_var, true, "tablo ayrica dogrulanabiliyor");

  /* 3) Her sey calisiyor, yalnizca yeni oge yok -- bu SAGLIK. */
  const saglikli = {
    DB: { prepare() {
      return { bind() { return this; },
               first: async () => ({ n: 12, yeni: "2026-09-30T12:00:00Z",
                                     eski: "2026-09-30T06:00:00Z" }) };
    } },
    ASSETS: { fetch: () => Promise.resolve({
      ok: true, json: () => Promise.resolve(TEST_KURAL) }) },
  };
  const d3 = await (await telDurum(saglikli)).json();
  esit(d3.oge_sayisi, 12, "oge sayisi bildiriliyor");
  esit(d3.en_yeni, "2026-09-30T12:00:00Z", "en yeni oge ani bildiriliyor");
  dogru(d3.tablo_var && d3.kurallar_okundu,
        "saglikli durumda iki taraf da yesil");
}

kos().then(() => {
  if (kaldi.length) {
    console.log("\ntel: " + kaldi.length + " KALDI");
    process.exit(1);
  }
  console.log("\ntel: " + gecti + " dogrulama gecti");
}).catch((e) => { console.error(e); process.exit(1); });
