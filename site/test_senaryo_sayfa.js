/* Senaryo sayfasi -- /senaryo/<id>/
 *
 * En kritik iki kural burada sinaniyor:
 *   1. YAYIMLANMAMIS senaryonun adresi acilmiyor
 *   2. Okur metni HTML olarak SIZMIYOR (senaryo metni kullanicidan
 *      geliyor; kacirilmazsa sayfaya betik girer)
 */

const fs = require("fs");
const path = require("path");

const kaynak = fs.readFileSync(
  path.join(__dirname, "worker.js"), "utf8");

let gecti = 0, kaldi = 0;
function sina(ad, kosul) {
  if (kosul) { gecti++; }
  else { kaldi++; console.error("KALDI: " + ad); }
}

/* --- 1. YOL DESENI --------------------------------------------- */
const desen = /^\/senaryo\/(\d+)\/?$/;
sina("id'li adres eslesiyor", desen.test("/senaryo/12/"));
sina("sondaki bolu istege bagli", desen.test("/senaryo/7"));
sina("harf eslesmiyor", !desen.test("/senaryo/abc/"));
sina("topluluk eslesmiyor", !desen.test("/topluluk/"));
sina("alt yol eslesmiyor", !desen.test("/senaryo/12/duzenle/"));

/* Kaynakta DIZGE degil DEGISMEZ kullanilmali: dizgede "\d" yalnizca
   "d" olur ve desen /senaryo/ddd/ arardi. Bir kez tam bu oldu. */
sina("desen degismez olarak yazilmis",
     /const sp = u\.pathname\.match\(\/\^/.test(kaynak));

/* --- 2. YAYIN DURUMU ------------------------------------------- */
sina("yalnizca yayimlanmis senaryo aciliyor",
     kaynak.includes("s.durum = 'yayimlandi'"));

/* --- 3. KACIRMA ------------------------------------------------- */
/* Senaryo metni KULLANICIDAN geliyor. Kacirilmazsa okurun yazdigi
   `<script>` sayfaya girer -- ve bu sayfa paylasim icin var, yani
   dogrudan yayilir. */
/* Alan `kacir(` cagrisinin hemen ARDINDAN gecmeli. Birebir
   "kacir(r.yazar)" aramak fazla kati olurdu: kod
   "kacir(r.yazar || ...)" yaziyor ve o da kaciriyor. */
for (const alan of ["r.kosul", "r.sonuc", "r.gerekce", "r.yazar"]) {
  sina(alan + " kaciriliyor", kaynak.includes("kacir(" + alan));
}
sina("kacir islevi bes karakteri de kapsiyor",
     /replace\(\/&\/g/.test(kaynak) && /replace\(\/</.test(kaynak) &&
     /replace\(\/>/.test(kaynak) && /&quot;/.test(kaynak) &&
     /&#39;/.test(kaynak));

/* --- 4. PAYLASIM ETIKETLERI ------------------------------------ */
/* Istemci tarafinda cizilseydi bu etiketler bos kalirdi: X ve
   LinkedIn sayfayi JavaScript calistirmadan okuyor. */
for (const e of ["og:title", "og:description", "og:url", "og:type",
                 "twitter:card", "canonical"]) {
  sina(e + " basiliyor", kaynak.includes(e));
}

/* --- 5. YASAL UYARI -------------------------------------------- */
sina("yatirim tavsiyesi uyarisi var",
     kaynak.includes("Yatırım tavsiyesi değildir"));

/* --- 6. BULUNAMAYAN SENARYO ------------------------------------ */
/* null donunce statik akisa dusuyor: worker kendi 404 sayfasini
   uydurmuyor, sitenin normal 404'u cikiyor. */
sina("bulunamayinca null donuyor",
     /if \(!r\) return null;/.test(kaynak));
sina("null donunce statik akisa dusuyor",
     /if \(y\) return y;/.test(kaynak));

console.log(kaldi === 0
  ? `TUM TESTLER GECTI (${gecti})`
  : `${kaldi} test KALDI, ${gecti} gecti`);
process.exit(kaldi === 0 ? 0 : 1);
