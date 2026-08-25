/* Cerez onayi ve Google Analytics -- ONAY MODU ile.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * Site Cloudflare Web Analytics kullaniyordu: cerezsiz, kimliksiz,
 * onay gerektirmeyen. Google Analytics 4'e gecildi ve GA4 bunlarin
 * ucunu de degistiriyor -- `_ga` cerezi yaziyor, ziyaretciye kalici
 * bir kimlik veriyor ve veriyi Google'a gonderiyor.
 *
 * KVKK ve GDPR bu tur cerezler icin ONCEDEN ACIK RIZA istiyor. Yani
 * betigi <head>'e yapistirmak yeterli degil: onay alinmadan cerez
 * yazilamaz.
 *
 * ONAY MODU (consent mode v2) NEDEN SECILDI
 * -----------------------------------------
 * Iki basit yol vardi:
 *
 *   a) Onay verilene kadar GA'yi HIC yukleme.
 *      Reddeden ziyaretci hicbir sayida gorunmez; sitenin gercek
 *      trafigi oldugundan az raporlanir.
 *
 *   b) Onay modu, varsayilan REDDEDILMIS.
 *      GA yukleniyor ama `analytics_storage: denied` ile: CEREZ
 *      YAZMIYOR, kimlik atamiyor. Yalnizca cerezsiz bir sayim
 *      sinyali gidiyor. Onay verilirse tam olcume yukseliyor.
 *
 * (b) secildi: reddeden okurun gizliligi korunuyor ve site yine de
 * kac ziyaret aldigini goruyor. Reddi "veri yok" saymak, okuru
 * onaylamaya zorlamanin dolayli yolu olurdu.
 *
 * SECIM SAKLANIYOR, SORULMUYOR
 * ----------------------------
 * Karar `localStorage`da; her sayfada yeniden sormak onay degil
 * yildirma olur. Depolama kapaliysa (gizli sekme, engelleyen
 * tarayici) try/catch yutuyor ve varsayilan REDDEDILMIS kaliyor --
 * yani belirsizlikte okurun lehine.
 */
(function () {
  "use strict";

  var ANAHTAR = "netaris-onay";
  var OLCUM = "G-LSJK3F2FC5";   /* GIZLI DEGIL: sayfa kaynaginda gorunur */

  function oku() {
    try {
      return localStorage.getItem(ANAHTAR);
    } catch (e) {
      return null;                 /* depolama yok -> her acilista sorulur */
    }
  }

  function yaz(deger) {
    try {
      localStorage.setItem(ANAHTAR, deger);
    } catch (e) { /* saklanamadi; secim bu oturum icin gecerli */ }
  }

  /* --- gtag temeli ---------------------------------------------------
     `dataLayer` ve `gtag` betik YUKLENMEDEN ONCE tanimlaniyor:
     `consent` cagrisi ilk olcum isteginden ONCE kuyruga girmeli,
     yoksa varsayilan "granted" gibi davranir ve cerez yazilir. */
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;

  var secim = oku();

  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: secim === "kabul" ? "granted" : "denied",
    functionality_storage: "granted",
    security_storage: "granted",
    wait_for_update: 500,
  });

  gtag("js", new Date());
  /* `anonymize_ip` GA4'te varsayilan ve kapatilamaz; yazmaya gerek
     yok. `send_page_view` varsayilan olarak aciik -- sayfa gorunumu
     onay modundan bagimsiz, cerezsiz olarak da gidiyor. */
  gtag("config", OLCUM);

  var betik = document.createElement("script");
  betik.async = true;
  betik.src = "https://www.googletagmanager.com/gtag/js?id=" + OLCUM;
  document.head.appendChild(betik);

  /* --- onay bandi ----------------------------------------------------
     Yalnizca secim YAPILMAMISSA gosteriliyor. Icerigi ORTMUYOR:
     ekranin altinda duruyor ve sayfa okunmaya devam edebiliyor --
     okuru karar vermeye zorlayan tam ekran bir katman, onay degil
     dayatma olurdu. */
  if (secim === "kabul" || secim === "ret") return;

  function bandiKur() {
    var b = document.createElement("div");
    b.className = "onay-bandi";
    b.setAttribute("role", "region");
    b.setAttribute("aria-label", "Çerez tercihi");
    b.innerHTML =
      '<p class="onay-metin">Ziyaret sayımı için Google Analytics kullanıyoruz. ' +
      '<b>Onay vermezseniz çerez yazılmaz</b>; yalnızca kimliksiz bir ' +
      'sayfa sayısı tutulur. ' +
      '<a href="/hakkimizda/#gizlilik">Ayrıntı</a>.</p>' +
      '<div class="onay-dugmeler">' +
      '<button type="button" class="dugme dugme-sade" data-onay="ret">Sadece gerekli</button>' +
      '<button type="button" class="dugme dugme-birincil" data-onay="kabul">Kabul et</button>' +
      '</div>';

    b.addEventListener("click", function (o) {
      var d = o.target.closest && o.target.closest("[data-onay]");
      if (!d) return;
      var karar = d.getAttribute("data-onay");
      yaz(karar);
      if (karar === "kabul") {
        gtag("consent", "update", { analytics_storage: "granted" });
      }
      b.remove();
    });

    document.body.appendChild(b);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bandiKur);
  } else {
    bandiKur();
  }
})();
