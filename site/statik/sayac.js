/* GORUNTULENME VE BEGENI SAYACLARI
 *
 * NEDEN VAR
 * ---------
 * Tasarim taslaginda her kartin altinda goruntulenme ve begeni sayisi
 * duruyor. Site bunlari hic olcmuyordu. Sayfaya uydurma bir sayi
 * basmak bu sitede en agir ihlal olurdu -- once olcum kuruldu, sonra
 * gosterim.
 *
 * SAYI SUNUCUDAN GELIYOR, SAYFAYA BASILMIYOR
 * ------------------------------------------
 * Sayfalar statik ve gunde birkac kez uretiliyor. Sayiyi HTML'e
 * basmak, okura saatler once dondurulmus bir sayi gostermek olurdu ve
 * "1.248 goruntulenme" yazan bir kutu, sayinin canli oldugu izlenimi
 * verir. Bu yuzden sayilar sayfa acilinca aliniyor; alinamazsa kutu
 * HIC GORUNMUYOR (bkz. `hidden`). Bos bir sayac, yanlis bir sayactan
 * iyidir.
 *
 * TEK ISTEK, KART BASINA DEGIL
 * ----------------------------
 * Liste sayfasinda 20-40 kart var. Her kart icin ayri istek acilis
 * suresini bozardi; hepsi tek `POST /api/sayaclar` cagrisinda
 * soruluyor.
 *
 * GORUNTULENME GUNDE BIR KEZ
 * --------------------------
 * Ayni okurun ayni sayfayi yenilemesi sayaci sisirmesin diye tarayici
 * tarafinda gunluk bir isaret tutuluyor. Sunucu tarafinda IP
 * TUTULMUYOR: saklansa daha saglam bir sayim olurdu ama IP kisisel
 * veri ve bir sayacin dogrulugu okurun izini tutmaya degmez.
 *
 * Bunun sonucu durustce soyleniyor: bu sayi "tekil ziyaretci" degil,
 * SAYFA ACILISI. Gizlilik beyaninda da boyle yaziyor.
 */
(function () {
  "use strict";

  var API_SAYAC = "/api/sayaclar";
  var API_GORUNTULENME = "/api/goruntulenme";
  var API_BEGENI = "/api/begeni";

  /* Turkce binlik ayirici NOKTA. `toLocaleString` tarayiciya gore
     degisebiliyor ve bazi ortamlarda virgul veriyor -- sayi bicimi
     tahmine birakilmayacak kadar gorunur bir sey. */
  function bicim(n) {
    n = Number(n) || 0;
    var s = String(Math.floor(Math.abs(n)));
    var c = "";
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 === 0) c += ".";
      c += s.charAt(i);
    }
    return (n < 0 ? "-" : "") + c;
  }

  function gunAnahtari(yol) {
    var d = new Date();
    var g = d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate();
    return "gor:" + g + ":" + yol;
  }

  /* Yerel depo BAZI TARAYICILARDA ERISILDIGI ANDA HATA ATIYOR (gizli
     pencere, site verisi engelli). Okumasi da yazmasi da sarilmali;
     yoksa tek bir ayar butun sayaclari susturur. */
  function gorulduMu(yol) {
    try {
      return window.localStorage.getItem(gunAnahtari(yol)) === "1";
    } catch (e) { return false; }
  }
  function goruldu(yol) {
    try { window.localStorage.setItem(gunAnahtari(yol), "1"); } catch (e) {}
  }

  function gonder(adres, govde) {
    return fetch(adres, {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(govde)
    });
  }

  function yollariTopla() {
    var kutular = document.querySelectorAll("[data-sayac-yol]");
    var yollar = [];
    for (var i = 0; i < kutular.length; i++) {
      var y = kutular[i].getAttribute("data-sayac-yol");
      if (y && yollar.indexOf(y) === -1) yollar.push(y);
    }
    return yollar;
  }

  function yaz(yol, sayilar, benimMi) {
    var kutular = document.querySelectorAll(
      '[data-sayac-yol="' + yol.replace(/"/g, '\\"') + '"]');
    for (var i = 0; i < kutular.length; i++) {
      var k = kutular[i];
      var g = k.querySelector("[data-sayac-goruntulenme]");
      var b = k.querySelector("[data-sayac-begeni]");
      if (g) g.textContent = bicim(sayilar.g);
      if (b) b.textContent = bicim(sayilar.b);
      var d = k.querySelector("[data-begeni-dugme]");
      if (d) {
        d.setAttribute("aria-pressed", benimMi ? "true" : "false");
        d.classList.toggle("begenildi", !!benimMi);
      }
      /* Kutu ancak GERCEK bir sayi geldiginde goruluyor. */
      k.hidden = false;
    }
  }

  function sayaclariAl() {
    var yollar = yollariTopla();
    if (!yollar.length) return;
    gonder(API_SAYAC, { yollar: yollar })
      .then(function (c) { return c.ok ? c.json() : null; })
      .then(function (v) {
        if (!v || !v.sayaclar) return;
        var benim = v.benim || [];
        for (var yol in v.sayaclar) {
          if (!Object.prototype.hasOwnProperty.call(v.sayaclar, yol)) continue;
          yaz(yol, v.sayaclar[yol], benim.indexOf(yol) !== -1);
        }
      })
      .catch(function () { /* sayac yoksa sayfa yine calisiyor */ });
  }

  function goruntulenmeBildir() {
    var k = document.querySelector("[data-sayac-birincil]");
    if (!k) return;
    var yol = k.getAttribute("data-sayac-yol");
    if (!yol || gorulduMu(yol)) return;
    goruldu(yol);
    gonder(API_GORUNTULENME, { yol: yol }).catch(function () {});
  }

  document.addEventListener("click", function (o) {
    var d = o.target.closest && o.target.closest("[data-begeni-dugme]");
    if (!d) return;
    o.preventDefault();
    var kutu = d.closest("[data-sayac-yol]");
    if (!kutu) return;
    var yol = kutu.getAttribute("data-sayac-yol");
    if (!yol) return;
    d.disabled = true;
    gonder(API_BEGENI, { yol: yol })
      .then(function (c) {
        if (c.status === 401) {
          /* GIRIS SAYFASINA NIYETLE GIDIYOR.
             Okur begenmek icin basti; girisden sonra ayni sayfaya
             donmeli. `donus.js` bu adresi okuyup geri getiriyor. */
          var geri = location.pathname + location.search + location.hash;
          location.href = "/giris/?donus=" + encodeURIComponent(geri);
          return null;
        }
        return c.ok ? c.json() : null;
      })
      .then(function (v) {
        if (!v) return;
        var b = kutu.querySelector("[data-sayac-begeni]");
        if (b) b.textContent = bicim(v.begeni);
        d.setAttribute("aria-pressed", v.benim ? "true" : "false");
        d.classList.toggle("begenildi", !!v.benim);
      })
      .catch(function () {})
      .then(function () { d.disabled = false; });
  });

  function basla() {
    sayaclariAl();
    goruntulenmeBildir();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", basla);
  } else {
    basla();
  }
})();
