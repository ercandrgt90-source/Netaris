/* Ust menu acilir listesi -- DOKUNMATIK ICIN.
 *
 * NEDEN GEREKLI
 * -------------
 * Menu CSS ile aciliyordu: `:hover` ve `:focus-within`. Masaustunde
 * calisiyor, DOKUNMATIKTE calismiyor -- telefonda `:hover` diye bir
 * durum yok ve `:focus-within` ancak dugmeye basildiginda olusuyor,
 * ikinci dokunusta kapanmiyor.
 *
 * Bu yuzden mobil CSS acilir menuyu tamamen DUZLESTIRIYORDU
 * (`display: contents`): dort alt baglanti da satir icine dokuluyor ve
 * ust menu UC SATIRA yayiliyordu. Olculdu -- kullanicinin ekran
 * goruntusunde tam olarak bu goruluyor.
 *
 * Duzlestirmek bir cozum degil, cozumsuzlugun kabulüydu.
 *
 * NE YAPIYOR
 * ----------
 * `aria-expanded` degerini cevirip `data-acik` isaretini koyuyor. CSS
 * de acikligi ARTIK O ISARETTEN okuyor; `:hover` masaustunde ek yol
 * olarak kaliyor.
 *
 * BETIKSIZ DURUM: `<details>` gibi yerel bir kapanir/acilir ogeye
 * gecmedik cunku menu HTML'i sunucuda uretiliyor ve bu dosya
 * yuklenmezse `:hover`/`:focus-within` yolu hala calisiyor. Yani
 * betiksiz ziyaretcide menu ERISILEBILIR kaliyor, yalnizca dokunmatik
 * kullanicinin ikinci dokunusla kapatmasi calismiyor.
 */

(function () {
  "use strict";

  var grup = document.querySelector(".menu-grup");
  if (!grup) return;
  var dugme = grup.querySelector(".menu-baslik");
  if (!dugme) return;

  function ayarla(acik) {
    dugme.setAttribute("aria-expanded", acik ? "true" : "false");
    if (acik) grup.setAttribute("data-acik", "");
    else grup.removeAttribute("data-acik");
  }

  dugme.addEventListener("click", function (o) {
    o.preventDefault();
    ayarla(dugme.getAttribute("aria-expanded") !== "true");
  });

  /* DISARI DOKUNUNCA KAPANSIN. Acik kalan bir menu, altindaki
     icerigi ortuyor ve okur kapatmanin yolunu ariyor. */
  document.addEventListener("click", function (o) {
    if (!grup.contains(o.target)) ayarla(false);
  });

  /* ESC ile kapanma: klavye kullanicisi icin beklenen davranis. */
  document.addEventListener("keydown", function (o) {
    if (o.key === "Escape") ayarla(false);
  });

  /* Menu icindeki bir baglantiya gidildiginde kapanmali -- sayfa
     degisse de gecmise donuldugunde acik kalmasin. */
  grup.addEventListener("click", function (o) {
    if (o.target.closest("a")) ayarla(false);
  });
})();
