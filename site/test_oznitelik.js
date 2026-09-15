/* `data-*` oznitelik adlari ASCII olmali.
 *
 * NEDEN BU TEST VAR
 * -----------------
 * Depoda tek bir ASCII disi oznitelik adi vardi: `data-uye-askı`
 * (Turkce noktasiz i, U+0131). Yonetici panelindeki "Askıya al"
 * dugmesi onunla isaretleniyor ve `querySelectorAll` onunla
 * araniyordu.
 *
 * Bozuldugunu KANITLAYAMADIM -- elde DOM yok, tarayicida denemedim.
 * Ama oznitelik adlarinin islenmesi ASCII disinda uygulamadan
 * uygulamaya degisen bir yer: HTML'in oznitelik adlarini kucuk harfe
 * cevirmesi, CSS ident kacislari, ada dokunan her arac.
 *
 * "Muhtemelen calisiyor" bir olcum degil. Belirsizligi bedava
 * kaldirmak dogru olan; kural da onu koruyor.
 *
 * ESLESME ZATEN SESSIZ BOZULUR: `querySelectorAll` bulamadiginda
 * bos liste doner, hata vermez. Dugme tiklanir ve HICBIR SEY olmaz --
 * bu depoda tekrarlayan bicim.
 *
 * Kullanim:  node site/test_oznitelik.js
 */

"use strict";

const fs = require("fs");
const path = require("path");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (JSON.stringify(bulunan) === JSON.stringify(beklenen)) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

/* Taranan dosyalar: tarayiciya giden her sey. */
function dosyalar() {
  const y = [];
  for (const kok of ["statik", "sablonlar"]) {
    const d = path.join(__dirname, kok);
    if (!fs.existsSync(d)) continue;
    for (const ad of fs.readdirSync(d)) {
      if (/\.(js|html)$/.test(ad)) y.push(path.join(d, ad));
    }
  }
  return y;
}

/* `data-...` adlari. Deger DISARIDA: degerin Turkce olmasi serbest,
   sorun ADIN kendisinde. */
const AD = /\bdata-[^\s"'=>\/]+/g;

console.log("\nTarayiciya giden dosyalarda ASCII disi oznitelik adi\n");
const hepsi = dosyalar();
esit(hepsi.length > 3, true, `tarama dolu (${hepsi.length} dosya)`);

/* YORUMLAR AYIKLANIYOR.
   Kural, tarayiciya giden ISARETLEMEYI olcuyor -- onun hakkinda
   yazilan duzyaziyi degil. Ilk yazimda bu sinama kendi aciklama
   yorumumu yakaladi (eski adi aniyordu) ve yanlis alarm verdi;
   bugun bu depoda defalarca gorulen bicimin aynisi.

   `//` satirlari BILEREK ayiklanmiyor: dizge icindeki "https://"
   yanlislikla yorum sanilir ve kod parcalari kaybolurdu. Blok
   yorumlari yeterli -- aciklamalar zaten oyle yaziliyor. */
function yorumsuz(metin) {
  return metin
    .replace(/\/\*[\s\S]*?\*\//g, " ")      /* JS blok yorumu */
    .replace(/\{#[\s\S]*?#\}/g, " ")          /* Jinja yorumu   */
    .replace(/<!--[\s\S]*?-->/g, " ");          /* HTML yorumu    */
}

const kirli = [];
for (const y of hepsi) {
  const metin = yorumsuz(fs.readFileSync(y, "utf8"));
  for (const m of metin.match(AD) || []) {
    /* eslint-disable-next-line no-control-regex */
    if (/[^\x00-\x7F]/.test(m)) kirli.push(path.basename(y) + ": " + m);
  }
}
esit(kirli.slice(0, 5), [], "hicbir data- adinda ASCII disi karakter yok");

/* Kuralin gercekten olctugunu gosteren karsi ornek: ayni desen,
   ASCII disi bir ad uzerinde ATESLIYOR. */
console.log("\nKural gercekten olcuyor (karsi ornek)\n");
const ornek = '<button data-uye-askı="3">Askıya al</button>';
const bulunan = (ornek.match(AD) || [])
  .filter((m) => /[^\x00-\x7F]/.test(m));
esit(bulunan.length, 1, "ASCII disi ad yakalaniyor");
/* DEGER serbest: Turkce metin tasiyan bir deger yanlis alarm
   uretmemeli. */
const temiz = '<button data-uye-askiya="3">Askıya al</button>';
esit((temiz.match(AD) || []).filter((m) => /[^\x00-\x7F]/.test(m)).length, 0,
     "Turkce DEGER yanlis alarm uretmiyor");

console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
process.exit(kaldi.length ? 1 : 0);
