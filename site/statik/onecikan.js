/* Ana sayfadaki "Öne çıkan senaryolar".
 *
 * Zincirin son halkasi: veri -> cikarim -> gorus -> TOPLULUK SECIMI.
 * En cok "degerli bulundu" oyu alan senaryolar ana sayfaya cikiyor.
 *
 * NEDEN CANLI UCTAN
 * Site statik ve gunde birkac kez kuruluyor; oy her an degisebiliyor.
 * Kurulum aninda gomulseydi siralama saatlerce eski kalirdi.
 *
 * SIFIR OYLU SENARYO CIKMAZ. "One cikan" demek bir SECIM demek; henuz
 * kimsenin bakmadigi bir metni oyle sunmak okuru yaniltir. Hic oy
 * yoksa bolum HIC basilmiyor -- bos bir "one cikan" basligi, sitenin
 * terk edilmis gorunmesine yol acar.
 */

(function () {
  "use strict";

  var kutu = document.getElementById("one-cikan-senaryo");
  if (!kutu) return;

  function kacir(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  fetch("/api/senaryo/one-cikan", { headers: { accept: "application/json" } })
    .then(function (y) { return y.ok ? y.json() : null; })
    .then(function (v) {
      var liste = (v && v.senaryolar) || [];
      if (!liste.length) return;

      var h = "";
      for (var i = 0; i < liste.length; i++) {
        var s = liste[i];
        h += '<li class="one-senaryo">' +
             '<p class="senaryo-onerme">' +
             '<span class="senaryo-kosul">' + kacir(s.kosul) + '</span>' +
             '<span class="senaryo-ok" aria-hidden="true">→</span>' +
             '<span class="senaryo-sonuc">' + kacir(s.sonuc) + '</span>' +
             '</p>' +
             '<p class="senaryo-kunye">' +
             '<span class="one-oy">▲ ' + Number(s.oy || 0) + '</span> ' +
             '<b>' + kacir(s.yazar) + '</b> · ufuk ' + kacir(s.ufuk);
        if (s.capa) {
          h += ' · <a href="' + kacir(s.capa) + '">' +
               kacir(s.capa_baslik || "habere git") + '</a>';
        }
        h += '</p></li>';
      }
      kutu.querySelector(".one-senaryo-liste").innerHTML = h;
      kutu.hidden = false;
    })
    .catch(function () { /* sessiz -- bolum basilmaz */ });
})();
