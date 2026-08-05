/* Tema dugmesi.
 *
 * Ilk secim <head> icindeki satir ici betikte yapiliyor -- bu dosya
 * yalnizca DEGISTIRME isini goruyor. Ayrimin sebebi: tema, sayfa
 * boyanmadan ONCE belli olmali; sayfa sonunda yuklenen bir betik koyu
 * tema secen okura her seferinde bir kare beyaz ekran gosterirdi.
 *
 * Uc durum var, ikisi degil:
 *   secim yok  -> sistem tercihi gecerli (`data-tema` yazili degil)
 *   "light"    -> kullanici acik istedi
 *   "dark"     -> kullanici koyu istedi
 *
 * Dugme, o an GORUNEN temanin tersine geciriyor.
 */

(function () {
  "use strict";

  var kok = document.documentElement;
  var dugme = document.getElementById("tema-dugme");
  if (!dugme) return;

  var ANAHTAR = "netaris-tema";
  var sistem = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");

  function koyuMu() {
    var secim = kok.getAttribute("data-tema");
    if (secim === "dark") return true;
    if (secim === "light") return false;
    return !!(sistem && sistem.matches);
  }

  function etiketle() {
    var koyu = koyuMu();
    // Dugme HEDEFI anlatir, mevcut durumu degil: koyu temadayken
    // "Acik temaya gec" yazar. Ekran okuyucuda "koyu tema" demek,
    // basildiginda ne olacagini belirsiz birakirdi.
    dugme.setAttribute("aria-label",
      koyu ? "Açık temaya geç" : "Koyu temaya geç");
    dugme.setAttribute("aria-pressed", koyu ? "true" : "false");
  }

  dugme.hidden = false;
  etiketle();

  dugme.addEventListener("click", function () {
    var yeni = koyuMu() ? "light" : "dark";
    kok.setAttribute("data-tema", yeni);
    try {
      localStorage.setItem(ANAHTAR, yeni);
    } catch (e) {
      /* Gizli sekmede yazilamaz; tema yine de bu sayfada degisti. */
    }
    etiketle();
  });

  // Kullanici HENUZ secim yapmadiysa sistem degisimini izle. Secim
  // yapildiysa dokunmuyoruz -- kullanicinin acik istegi, isletim
  // sisteminin varsayilanindan onceliklidir.
  if (sistem && sistem.addEventListener) {
    sistem.addEventListener("change", function () {
      if (!kok.getAttribute("data-tema")) etiketle();
    });
  }
})();
