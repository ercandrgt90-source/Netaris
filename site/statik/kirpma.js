/* KIRPILAN METNE "devamı" ISARETI -- YALNIZCA GERCEKTEN KESILDIYSE.
 *
 * NEDEN BETIK
 * -----------
 * `-webkit-line-clamp` uc nokta basiyor ama "burada devami var"
 * bilgisini vermiyor: okur ucuncu satirin sonundaki uc noktayi
 * cumlenin kendi noktalamasi sanabiliyor.
 *
 * CSS ile "kirpildi mi" sorusu SORULAMAZ. Kosulsuz bir "devamı"
 * yazmak ise metin kirpilmadiginda yalan olurdu: tamamlanmis bir
 * ozetin altinda "devamı" gormek, okura olmayan bir sey vaat eder.
 *
 * Bu yuzden olcum: `scrollHeight > clientHeight` ise metin kesilmis
 * demektir. Isaret ancak o zaman konuyor.
 *
 * BETIK YOKSA NE OLUR
 * -------------------
 * Hicbir sey bozulmuyor: kirpma CSS'te ve uc nokta yine basiliyor.
 * Yalnizca "devamı" kelimesi gorunmuyor. Ozellik eksik kalir, sayfa
 * kalmaz.
 *
 * NEDEN BAGLANTI DEGIL
 * --------------------
 * Kartin KENDISI zaten bir baglanti; icine ikinci bir <a> koymak
 * gecersiz HTML olurdu. Isaret bir <span> ve tiklama kartin bagina
 * gidiyor -- okur farki gormuyor, tarayici dogru davraniyor.
 */
(function () {
  "use strict";

  var SECICI = "[data-kirpma]";

  function bak(oge) {
    /* 1 piksel tolerans: tarayicilar satir yuksekligini kesirli
       hesaplayabiliyor ve kirpilmamis metin de bazen 0,5 piksel
       tasiyor. Toleranssiz kontrol yanlis pozitif uretiyordu. */
    var kesik = oge.scrollHeight - oge.clientHeight > 1;
    oge.classList.toggle("kirpildi", kesik);
  }

  function hepsi() {
    var l = document.querySelectorAll(SECICI);
    for (var i = 0; i < l.length; i++) bak(l[i]);
  }

  /* Yeniden olculmesi gereken iki an var: yazi tipi yuklenince satir
     sayisi degisiyor, ekran doner ya da genisligi degisince de. */
  function bagla() {
    hepsi();
    if (document.fonts && document.fonts.ready &&
        typeof document.fonts.ready.then === "function") {
      document.fonts.ready.then(hepsi).catch(function () {});
    }
    var zaman = null;
    window.addEventListener("resize", function () {
      clearTimeout(zaman);
      zaman = setTimeout(hepsi, 150);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bagla);
  } else {
    bagla();
  }
})();
