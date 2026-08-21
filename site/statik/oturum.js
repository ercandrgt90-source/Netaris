/* Ust menudeki oturum baglantisi.
 *
 * Sayfa statik: herkese ayni HTML gidiyor, sunucu "bu okur giris yapmis
 * mi" sorusunu cevaplayamiyor. Bu yuzden ikisi de gizli basiliyor ve
 * dogru olan burada aciliyor.
 *
 * NEDEN uyelik.js'te DEGIL: uyelik.js yalnizca /giris/, /kayit/ ve
 * /panel/ sayfalarina yukleniyor. Ust menu HER sayfada var.
 *
 * Betik calismazsa iki baglanti da gizli kalir -- fazladan bir sey
 * gorunmez, menu eskisi gibi calisir.
 */
(function () {
  "use strict";

  /* BIRDEN COK oge olabilir: oturumsuz okur hem "Giris yap" hem
     "Uye ol" goruyor. `querySelector` yalnizca ILKINI buluyordu ve
     ikincisi sonsuza dek gizli kaliyordu. */
  var yok = document.querySelectorAll("[data-oturum-yok]");
  var var_ = document.querySelectorAll("[data-oturum-var]");
  if (!yok.length && !var_.length) return;

  function goster(girisli) {
    Array.prototype.forEach.call(yok, function (o) { o.hidden = girisli; });
    Array.prototype.forEach.call(var_, function (o) { o.hidden = !girisli; });
  }

  fetch("/api/ben", { credentials: "same-origin", cache: "no-store" })
    .then(function (y) { return y.ok ? y.json() : null; })
    .then(function (v) { goster(!!(v && v.uye)); })
    /* API yoksa ya da coktuyse "giris yap" gosteriyoruz: okuma tarafi
       calismaya devam etsin, en fazla tiklayinca giris sayfasi acilir. */
    .catch(function () { goster(false); });
})();
