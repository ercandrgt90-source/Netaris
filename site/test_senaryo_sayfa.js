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

/* --- 7. PAYLASIM BLOGU (prompt 3) ------------------------------ */
/* Sunucuda uretiliyor: betiksiz de calismali. Uc bag da dogrudan
   <a>/<button>, tiklama dinleyicisi degil. */
sina("paylasim blogu var", kaynak.includes("paylas-blok"));
sina("onizleme karti var", kaynak.includes("paylas-onizleme"));
sina("X bagi", kaynak.includes("x.com/intent/post"));
sina("LinkedIn bagi", kaynak.includes("linkedin.com/sharing/share-offsite"));
sina("kopyalama dugmesi", kaynak.includes("data-paylas-kopyala"));

/* ONIZLEMEDEKI ALAN ADI adresten TURETILIYOR.
   Elle yazilsaydi alan adi degistiginde kart yalan soylerdi -- ve
   bu kart okura "paylasimin boyle gorunecek" diyor. */
sina("alan adi adresten turetiliyor",
     /new URL\(adres\)\.hostname/.test(kaynak));

/* X SINIRI: gonderi 280 karakter, adres ~23 sayiliyor. */
sina("X metni kirpiliyor", kaynak.includes("ozet.slice(0, 199)"));

/* Onizlemedeki metin `og:` etiketleriyle AYNI olmali: kart
   gosterdigi seyi gercekten paylasmali. */
sina("onizleme ozeti og ile ayni kaynaktan",
     kaynak.includes("paylasBlok(baslik, ozet, adres)"));

console.log(kaldi === 0
  ? `TUM TESTLER GECTI (${gecti})`
  : `${kaldi} test KALDI, ${gecti} gecti`);
process.exit(kaldi === 0 ? 0 : 1);
