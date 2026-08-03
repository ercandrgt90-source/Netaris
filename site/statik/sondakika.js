/* Son dakika seridinin akisi ve duraklatma dugmesi.
 *
 * NEDEN AYRI DOSYA
 * canli.js piyasa verisi cekiyor ve ag hatasi alabiliyor. Serit akisi
 * ondan bagimsiz olmali: veri ucu coktugunde haber seridi de durmasin.
 *
 * NEDEN JAVASCRIPT GEREKIYOR
 * Animasyon -%50 kaydiriyor; dikissiz gorunmesi icin ayni dizinin ikinci
 * bir kopyasi gerekiyor. Kopyayi sunucuda basmak HTML'i iki katina
 * cikarirdi. Betik calismazsa serit AKMAZ ama basliklar yerinde durur ve
 * tiklanabilir -- islev kaybi yok, yalnizca hareket yok.
 */
(function () {
  "use strict";

  var SERIT = document.querySelector(".sondakika");
  var AKIS = document.querySelector("[data-sd-akis]");
  var SIRA = document.querySelector("[data-sd-sira]");
  var DUGME = document.querySelector("[data-sd-durdur]");
  if (!SERIT || !AKIS || !SIRA) return;

  /* Hareketi azaltma tercihi acikken kopya HIC eklenmiyor.
     CSS animasyonu zaten kapatiyor; kopyayi da eklememek ekran
     okuyucunun ayni basliklari iki kez okumasini onluyor. */
  var azalt = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)");
  if (azalt && azalt.matches) return;

  /* Serit tasmiyorsa akitmanin anlami yok -- birkac baslik varken
     kaydirmak okumayi zorlastirir, bilgi eklemez. */
  if (SIRA.scrollWidth <= AKIS.clientWidth + 8) return;

  var kopya = SIRA.cloneNode(true);
  kopya.removeAttribute("data-sd-sira");
  kopya.setAttribute("aria-hidden", "true");
  /* Kopyadaki baglantilar sekmeyle gezilirken tekrar odaklanmasin */
  var baglar = kopya.querySelectorAll("a");
  for (var i = 0; i < baglar.length; i++) baglar[i].setAttribute("tabindex", "-1");

  var sarmal = document.createElement("div");
  sarmal.className = "sondakika-sira akiyor";
  sarmal.appendChild(SIRA.cloneNode(true));
  sarmal.appendChild(kopya);

  AKIS.innerHTML = "";
  AKIS.appendChild(sarmal);

  if (DUGME) {
    DUGME.addEventListener("click", function () {
      var durdu = SERIT.classList.toggle("durdu");
      DUGME.setAttribute("aria-label", durdu ? "Akışı sürdür" : "Akışı duraklat");
      DUGME.setAttribute("title", durdu ? "Akışı sürdür" : "Akışı duraklat");
    });
  }
})();
