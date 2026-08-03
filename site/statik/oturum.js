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

  var yok = document.querySelector("[data-oturum-yok]");
  var var_ = document.querySelector("[data-oturum-var]");
  if (!yok && !var_) return;

  function goster(girisli) {
    if (yok) yok.hidden = girisli;
    if (var_) var_.hidden = !girisli;
  }

  fetch("/api/ben", { credentials: "same-origin", cache: "no-store" })
    .then(function (y) { return y.ok ? y.json() : null; })
    .then(function (v) { goster(!!(v && v.uye)); })
    /* API yoksa ya da coktuyse "giris yap" gosteriyoruz: okuma tarafi
       calismaya devam etsin, en fazla tiklayinca giris sayfasi acilir. */
    .catch(function () { goster(false); });
})();
