/* Google ile giris -- istemci tarafi.
 *
 * NASIL CALISIYOR
 * ---------------
 * Google Identity Services tarayicida imzali bir kimlik jetonu (JWT)
 * veriyor; biz onu `/api/giris/google` ucuna gonderiyoruz ve DOGRULAMA
 * SUNUCUDA yapiliyor (imza, `aud`, `iss`, `exp`, `email_verified`).
 * Tarayicidan gelen hicbir sey dogrulanmadan kabul edilmiyor.
 *
 * ISTEMCI SIRRI YOK. Bu akista yalnizca istemci KIMLIGI gerekiyor ve o
 * gizli bir deger degil -- sayfada gorunmesi normal.
 *
 * YAPILANDIRILMAMISSA HIC GORUNMUYOR
 * ----------------------------------
 * Once `/api/giris/google/ayar` soruluyor. Istemci kimligi bos donerse
 * ne Google betigi yukleniyor ne dugme basiliyor. Tiklayinca hata veren
 * bir giris dugmesi, olmayan dugmeden kotudur; ayrica yapilandirma
 * yapilmadan ucuncu tarafa istek gitmiyor.
 *
 * BETIK YUKLENEMEZSE: parolayla giris formu oldugu yerde duruyor.
 * Google'a erisilemeyen bir agda site calismaya devam ediyor.
 */

(function () {
  "use strict";

  var YUVALAR = document.querySelectorAll("[data-google-giris]");
  if (!YUVALAR.length) return;

  var GIS = "https://accounts.google.com/gsi/client";

  function hataYaz(mesaj) {
    for (var i = 0; i < YUVALAR.length; i++) {
      var k = YUVALAR[i].querySelector("[data-google-hata]");
      if (k) { k.textContent = mesaj; k.hidden = false; }
    }
  }

  /* Google'in dondurdugu jetonu sunucuya veriyoruz. Yanit basariliysa
     oturum cerezi yaziliyor ve panele gidiliyor -- parolayla girisin
     yaptigi seyin aynisi. */
  function jetonGonder(yanit) {
    fetch("/api/giris/google", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jeton: yanit.credential }),
    })
      .then(function (y) {
        return y.json().catch(function () { return {}; })
          .then(function (v) { return { ok: y.ok, v: v }; });
      })
      .then(function (s) {
        if (!s.ok) {
          hataYaz(s.v.hata || "Google ile giriş yapılamadı.");
          return;
        }
        /* Sunucudan gelen adrese GITMIYORUZ -- acik yonlendirme
           riskini bastan kapatiyoruz. Hedef burada sabit. */
        /* Parola girisiyle AYNI donus mantigi: okurun niyeti
           Google ile girerken de kaybolmamali. */
        location.href = (window.NetarisDonus
          ? window.NetarisDonus.hedef() : "/panel/");
      })
      .catch(function () {
        hataYaz("Bağlantı kurulamadı. Tekrar deneyin.");
      });
  }

  function dugmeleriBas(istemci) {
    if (!window.google || !window.google.accounts
        || !window.google.accounts.id) {
      hataYaz("Google giriş bileşeni yüklenemedi.");
      return;
    }
    window.google.accounts.id.initialize({
      client_id: istemci,
      callback: jetonGonder,
      /* FedCM tarayicinin kendi kimlik arayuzunu kullaniyor; ucuncu
         taraf cerezleri kapaliyken de calisiyor. */
      use_fedcm_for_prompt: true,
    });
    for (var i = 0; i < YUVALAR.length; i++) {
      var hedef = YUVALAR[i].querySelector("[data-google-dugme]");
      if (!hedef) continue;
      window.google.accounts.id.renderButton(hedef, {
        theme: "outline",
        size: "large",
        shape: "rectangular",
        text: "continue_with",
        locale: "tr",
        width: 280,
      });
      YUVALAR[i].hidden = false;
    }
  }

  fetch("/api/giris/google/ayar", { headers: { accept: "application/json" } })
    .then(function (y) { return y.ok ? y.json() : {}; })
    .then(function (v) {
      if (!v || !v.istemci) return;      // yapilandirilmamis: sessiz
      var b = document.createElement("script");
      b.src = GIS;
      b.async = true;
      b.defer = true;
      b.onload = function () { dugmeleriBas(v.istemci); };
      b.onerror = function () { hataYaz("Google giriş bileşeni yüklenemedi."); };
      document.head.appendChild(b);
    })
    .catch(function () { /* uc yoksa Google girisi yok, form calisiyor */ });
})();
