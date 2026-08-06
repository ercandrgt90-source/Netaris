/* "AI Sonucu" bolumu.
 *
 * Sayfadaki OLCULMUS verileri toplayip uca gonderiyor; uc onlari uc
 * cumleye ceviriyor. Model rakam bulmuyor, verileni yaziyor.
 *
 * NEDEN CANLI UCTAN, KURULUM ANINDA DEGIL
 * Site gunde birkac kez kuruluyor ve o anda her sayfa icin model
 * cagirmak hem yavas hem kotayi bir kerede bitirir. Uc tarafinda
 * onbellek var: ayni girdi ayni metni donuyor, yani okur sayfayi
 * yenileyince metin DEGISMIYOR.
 *
 * UC COKERSE BOLUM HIC BASILMAZ. Sayfanin geri kalani -- ki hepsi
 * deterministik olcum -- bu katmandan bagimsiz.
 */

(function () {
  "use strict";

  var kutu = document.getElementById("ai-sonuc");
  if (!kutu) return;

  /* Girdi SAYFADAN toplaniyor, ayrica gomulmuyor: boylece sayfada ne
     yaziyorsa modele giden de o. Ikisi ayri kaynaktan gelseydi
     birbirinden sapabilirdi. */
  function topla() {
    var p = [];
    var b = document.querySelector("h1");
    if (b) p.push("Haber: " + b.textContent.trim());

    var konu = document.querySelector(".rozet-vurgu");
    if (konu) p.push("Konu: " + konu.textContent.trim());

    var acilis = document.querySelector(".acilis");
    if (acilis) p.push("Veri: " + acilis.textContent.trim());

    document.querySelectorAll(".ozet-kutu dt").forEach(function (dt) {
      var dd = dt.nextElementSibling;
      if (dd) {
        p.push(dt.textContent.trim() + " " +
               dd.textContent.replace(/\s+/g, " ").trim());
      }
    });

    document.querySelectorAll(".turkiye-panel .kalem").forEach(function (k) {
      p.push(k.textContent.replace(/\s+/g, " ").trim());
    });

    var neden = document.querySelector(".govde h2 + p");
    if (neden) p.push("Bağlam: " + neden.textContent.trim());

    return p.join("\n").slice(0, 2000);
  }

  var girdi = topla();
  if (girdi.length < 120) return;   /* Veri az; ozetlenecek bir sey yok */

  fetch("/api/ai/sonuc", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ girdi: girdi }),
  })
    .then(function (y) { return y.ok ? y.json() : null; })
    .then(function (v) {
      if (!v || !v.metin) return;
      var g = kutu.querySelector(".ai-metin");
      /* textContent -- innerHTML DEGIL. Model ciktisi guvenilmeyen
         metindir; HTML olarak basmak betik enjeksiyonuna acik kapi. */
      g.textContent = v.metin;
      kutu.hidden = false;
    })
    .catch(function () { /* sessiz */ });
})();
