/* Haber sayfasindaki topluluk senaryolari.
 *
 * NEDEN CANLI UCTAN, SAYFAYA GOMULU DEGIL
 * Site statik uretiliyor ve gunde birkac kez kuruluyor. Senaryolar ise
 * her an eklenebiliyor; sayfaya gomulseler bir sonraki kuruluma kadar
 * gorunmezlerdi. Bolum bu yuzden `/api/senaryo/acik` ucundan besleniyor.
 *
 * UC COKERSE BOLUM HIC BASILMAZ. Hata mesaji gostermiyoruz: okur icin
 * "senaryo servisi calismiyor" bilgisi degersiz, haberin geri kalani
 * ise saglam. Sitenin okuma tarafinin uyelik sisteminden BAGIMSIZ
 * kalmasi bilincli bir karar.
 */

(function () {
  "use strict";

  var kutu = document.getElementById("senaryo-bolum");
  if (!kutu) return;

  var capa = kutu.getAttribute("data-capa");
  if (!capa) return;

  function kacir(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function tarihTR(iso) {
    if (!iso) return "";
    var a = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
    var p = String(iso).slice(0, 10).split("-");
    if (p.length !== 3) return "";
    return Number(p[2]) + " " + a[Number(p[1]) - 1] + " " + p[0];
  }

  var SONUC = {
    gerceklesti: ["Gerçekleşti", "olumlu"],
    gerceklesmedi: ["Gerçekleşmedi", "olumsuz"],
    belirsiz: ["Belirsiz", "notr"],
  };

  fetch("/api/senaryo/acik?capa=" + encodeURIComponent(capa), {
    headers: { accept: "application/json" },
  })
    .then(function (y) { return y.ok ? y.json() : null; })
    .then(function (v) {
      var liste = (v && v.senaryolar) || [];
      if (!liste.length) return;

      var h = "";
      for (var i = 0; i < liste.length; i++) {
        var s = liste[i];
        var d = SONUC[s.sonuclanma];
        h += '<li class="senaryo">' +
             '<p class="senaryo-onerme">' +
             '<span class="senaryo-kosul">' + kacir(s.kosul) + '</span>' +
             '<span class="senaryo-ok" aria-hidden="true">→</span>' +
             '<span class="senaryo-sonuc">' + kacir(s.sonuc) + '</span>' +
             '</p>';
        if (s.gerekce) {
          h += '<p class="senaryo-gerekce">' + kacir(s.gerekce) + '</p>';
        }
        h += '<p class="senaryo-kunye">' +
             '<b>' + kacir(s.yazar) + '</b>' +
             ' · ufuk ' + kacir(s.ufuk);
        if (s.ufuk_biter) h += ' (' + kacir(tarihTR(s.ufuk_biter)) + ')';
        if (d) {
          h += ' · <span class="senaryo-sonuclanma ' + d[1] + '">' +
               d[0] + '</span>';
        }
        h += '</p></li>';
      }

      kutu.querySelector(".senaryo-liste").innerHTML = h;
      kutu.hidden = false;
    })
    .catch(function () {
      /* Sessiz. Bolum zaten `hidden`; bir sey yapmiyoruz. */
    });
})();
