/* Fiyat seridinin AKMASI icin sinama -- sahte DOM ile.
 *
 * NEDEN VAR
 * ---------
 * Serit sunucuda dolu basiliyor; `canli.js` yalnizca uzerine canli
 * kalem ekliyor. Buna ragmen seridin HAREKETI bir ag istegine
 * baglanmisti: `kopyaTazele()` -- ikinci kopyayi ve `akiyor` sinifini
 * ekleyen islev -- yalnizca Kraken ya da Binance istegi BASARILI
 * olursa cagriliyordu.
 *
 * Iki uc da Turkiye'den erisilemiyor. Ucuncu bir yol (Frankfurter kur
 * katmani) erisilebilir oldugu icin animasyonu pratikte O basliyordu;
 * o katman serit cakismasi yuzunden kaldirilinca akisin tek calisan
 * tetigi de kalkti ve serit dondu. Kullanici "fiyat ekrani
 * calismiyor" dedi.
 *
 * Bu sinama tam olarak o durumu kuruyor: BUTUN aglar basarisiz.
 * Serit yine de akmali.
 *
 * Kullanim:  node site/test_canli.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (bulunan === beklenen) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

// --- en kucuk sahte DOM -------------------------------------------
// Tam bir tarayici taklidi degil; `canli.js`in DOKUNDUGU yuzey kadar.
function ogeYap(ad) {
  const o = {
    etiket: ad,
    className: "",
    innerHTML: "",
    /* `textContent` BASLANGICTA TANIMLI: tanimsiz birakilirsa
       "dolmadi" sinamasi `undefined` gorur ve bos dizeyle
       karsilastirma yanlis yere kirmizi yanar -- olculen sey kod
       degil olcum araci olurdu. */
    textContent: "",
    title: "",
    cocuklar: [],
    ozellikler: {},
    siniflar: new Set(),
    classList: {
      add: (s) => o.siniflar.add(s),
      contains: (s) => o.siniflar.has(s),
    },
    setAttribute: (k, v) => { o.ozellikler[k] = v; },
    removeAttribute: (k) => { delete o.ozellikler[k]; },
    appendChild: (c) => { o.cocuklar.push(c); c.ebeveyn = o; return c; },
    insertBefore: (c) => { o.cocuklar.unshift(c); return c; },
    remove: () => {
      if (!o.ebeveyn) return;
      o.ebeveyn.cocuklar = o.ebeveyn.cocuklar.filter((x) => x !== o);
    },
    cloneNode: () => {
      const k = ogeYap(ad);
      k.className = o.className;
      k.ozellikler = Object.assign({}, o.ozellikler);
      return k;
    },
    querySelector: (s) => {
      // Yalnizca `[data-...]` bicimini destekliyor -- kullanilan tek bicim.
      const m = /^\[([a-z-]+)(?:="([^"]*)")?\]$/.exec(s);
      if (!m) return null;
      for (const c of o.cocuklar) {
        if (m[1] in c.ozellikler
            && (m[2] === undefined || c.ozellikler[m[1]] === m[2])) return c;
      }
      return null;
    },
  };
  return o;
}

function ortamKur({ aglarCalisir, hareketAzalt, analizKodu }) {
  const akis = ogeYap("div");
  const sira = ogeYap("div");
  sira.ozellikler["data-serit-sira"] = "";
  akis.appendChild(sira);

  /* ANALIZ SAYFASINDAKI CANLI FIYAT KUTUSU.
     Teknik gorunum analizleri fiyati METNIN ICINE yaziyor ve o
     rakam insa anindan; insa gunde ~7 kez kosuyor (olculdu
     2026-10-01) ve sayfadaki tek tarih GUN duzeyinde. Kutu, canli
     fiyati AYRI ve etiketli gosteriyor -- analizin rakamini
     DEGISTIRMIYOR, cunku metnin gerekcesi o rakamla yazildi. */
  let kutu = null;
  if (analizKodu) {
    kutu = ogeYap("p");
    kutu.ozellikler["data-canli-fiyat"] = analizKodu;
    kutu.ozellikler.hidden = "";
    const deger = ogeYap("b");
    deger.ozellikler["data-canli-deger"] = "";
    const yon = ogeYap("span");
    yon.ozellikler["data-canli-yon"] = "";
    kutu.appendChild(deger);
    kutu.appendChild(yon);
  }

  const belge = {
    querySelector: (s) => {
      if (s === "[data-serit-sira]") return sira;
      if (s === "[data-serit-akis]") return akis;
      const m = /^\[data-canli-fiyat="([^"]+)"\]$/.exec(s);
      if (m) return (kutu && analizKodu === m[1]) ? kutu : null;
      return null;
    },
    createElement: ogeYap,
  };

  const pencere = {
    document: belge,
    matchMedia: () => ({ matches: !!hareketAzalt }),
    setInterval: () => 0,
    fetch: () => (aglarCalisir
      ? Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            result: {
              XXBTZUSD: { c: ["100000.0"], o: "98000.0" },
            },
          }),
        })
      : Promise.reject(new Error("ag yok"))),
  };
  pencere.window = pencere;

  const kaynak = fs.readFileSync(
    path.join(__dirname, "statik", "canli.js"), "utf8");
  vm.createContext(pencere);
  vm.runInContext(kaynak, pencere);
  return { akis, sira, kutu };
}

console.log("\nFiyat seridi -- akis ag istegine BAGLI OLMAMALI\n");

// 1. Butun aglar basarisiz. Gercekte olan durum budur.
{
  const { akis } = ortamKur({ aglarCalisir: false, hareketAzalt: false });
  esit(akis.siniflar.has("akiyor"), true,
       "AG YOKKEN serit yine de akiyor (asil hata buydu)");
  esit(akis.querySelector("[data-serit-kopya]") !== null, true,
       "ag yokken ikinci kopya yine de ekleniyor");
}

// 2. Aglar calisiyor -- kopya bir kez daha tazeleniyor, cogalmiyor.
{
  const { akis } = ortamKur({ aglarCalisir: true, hareketAzalt: false });
  esit(akis.siniflar.has("akiyor"), true, "ag varken de akiyor");
  const kopyalar = akis.cocuklar.filter(
    (c) => "data-serit-kopya" in c.ozellikler);
  esit(kopyalar.length <= 1, true,
       "kopya COGALMIYOR -- her tazelemede eskisi siliniyor");
}

// 3. Hareket azaltma. Kopya HIC eklenmemeli: CSS animasyonu zaten
//    kapatiyor, kopya da ekran okuyucuya ayni fiyatlari iki kez
//    okuturdu.
{
  const { akis } = ortamKur({ aglarCalisir: false, hareketAzalt: true });
  esit(akis.querySelector("[data-serit-kopya]"), null,
       "hareket azaltma acikken kopya EKLENMIYOR");
  esit(akis.siniflar.has("akiyor"), false,
       "hareket azaltma acikken akis sinifi eklenmiyor");
}

/* ------------------------------------------------------------------
   ANALIZ SAYFASINDAKI CANLI FIYAT

   Uc sey ayni anda dogru olmali ve ucu de SESSIZCE bozulabilir:

     1. Eslesen varlikta kutu dolmali -- yoksa ozellik "kurulu ama
        calismiyor" halinde durur.
     2. BIST kodunda ASLA dolmamali. BIST verisi Borsa Istanbul
        dagitim lisansi gerektiriyor ve o veri siteye hic girmiyor;
        koruma YAPISAL olmali, hatirlanmasi gereken bir sey degil.
     3. Ikinci bir ag cagrisi acilmamali -- fiyati `krakenCek`
        zaten cekiyor.
   ------------------------------------------------------------------ */
/* SOZ COZULDUKTEN SONRA OLCULUYOR.
   `krakenCek()` bir soz donduruyor; fiyat mikro-gorev sirasinda
   yaziliyor. Ilk yazimda es zamanli olculdu ve uc sinama kirmizi
   yandi -- kod dogruydu, OLCUM erkendi. Bu depoda ayni sinif
   defalarca cikti: sahte ariza genelde olcumun kendisi. */
async function canliFiyatSinamalari() {
  const bekle = () => new Promise((r) => setTimeout(r, 5));

  console.log("\nAnaliz sayfasinda canli fiyat\n");

  // 4. Eslesen varlik: kutu doluyor ve GORUNUR oluyor.
  {
    const { kutu } = ortamKur({ aglarCalisir: true, hareketAzalt: false,
                                analizKodu: "BTC" });
    await bekle();
    const deger = kutu.querySelector("[data-canli-deger]");
    esit(deger.textContent !== "", true,
         "BTC kutusu DOLDU (sahte Kraken yaniti)");
    esit("hidden" in kutu.ozellikler, false, "kutu GORUNUR oldu");
  }

  // 5. BIST kodu: kutu dolmuyor, gizli kaliyor.
  //    `KRAKEN_ADLARI` yalnizca kripto/emtia tasiyor, dolayisiyla
  //    eslesme HIC olusmuyor -- koruma yapisal, hatirlanmasi
  //    gereken bir sey degil.
  {
    const { kutu } = ortamKur({ aglarCalisir: true, hareketAzalt: false,
                                analizKodu: "THYAO" });
    await bekle();
    const deger = kutu.querySelector("[data-canli-deger]");
    esit(deger.textContent, "", "BIST kodunda kutu DOLMADI (lisans)");
    esit("hidden" in kutu.ozellikler, true,
         "BIST kodunda kutu GIZLI kaldi");
  }

  // 6. Ag yokken kutu sessizce gizli kaliyor -- sayfa bozulmuyor.
  {
    const { kutu } = ortamKur({ aglarCalisir: false, hareketAzalt: false,
                                analizKodu: "BTC" });
    await bekle();
    esit("hidden" in kutu.ozellikler, true,
         "ag yokken kutu gizli kaliyor (sayfa aynen calisiyor)");
  }

  // 7. Esleme tablosunda BIST izi OLMAMALI -- kaynak denetimi.
  {
    const kaynak = fs.readFileSync(
      path.join(__dirname, "statik", "canli.js"), "utf8");
    const tablo = /var KRAKEN_ADLARI = \[([\s\S]*?)\];/.exec(kaynak);
    esit(tablo !== null, true, "KRAKEN_ADLARI tablosu okunabiliyor");
    const kodlar = [...tablo[1].matchAll(/kod:\s*"([^"]+)"/g)]
      .map((m) => m[1]).sort();
    esit(JSON.stringify(kodlar), JSON.stringify(["BTC", "ETH", "PAXG"]),
         "tabloda yalnizca kripto/emtia kodu var");
    esit(/BIST|XU100|THYAO|ASELS/i.test(tablo[1]), false,
         "tabloda BIST izi YOK");
    const govde = /function analizFiyatiKur\([\s\S]*?\n  \}/.exec(kaynak);
    esit(govde !== null, true, "analizFiyatiKur govdesi okunabiliyor");
    esit(/fetch\(/.test(govde[0]), false,
         "analizFiyatiKur AG CAGRISI yapmiyor (ayni veriden besleniyor)");
  }
}

canliFiyatSinamalari().then(() => {
    console.log("");
  if (kaldi.length) {
    console.log(kaldi.length + " TEST KALDI, " + gecti + " gecti");
    process.exit(1);
  }
  console.log("TUM TESTLER GECTI (" + gecti + ")");
}).catch((e) => { console.error(e); process.exit(1); });
