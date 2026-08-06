/* Goreli zaman: "3 dk önce", "2 saat önce", "dün".
 *
 * NEDEN ISTEMCIDE
 * Site statik ve gunde birkac kez kuruluyor. Goreli zaman kurulum
 * aninda gomulseydi, yayimlandigi dakikada dogru, iki saat sonra yanlis
 * olurdu -- ve okur "3 dk önce" yazan iki saatlik bir haber gorurdu.
 * Bu, tazelik konusunda dogrudan yanlis bilgi vermek olur.
 *
 * KAPALI JAVASCRIPT'TE DE DOGRU KALIR
 * Sunucu HTML'e tam tarihi basiyor ("6 Ağustos 2026"). Bu betik onun
 * YERINE goreli metni yaziyor. Betik calismazsa tarih goruntude kalir
 * -- daha kaba ama dogru. Bos bir etiket kalmaz.
 *
 * DAMGA NE ANLAMA GELIYOR
 * `datetime` alani haberin BIZIM HATTIMIZA dustugu an (ilk_gorulme).
 * Yayin ani degil. Hat sik calistigi icin ikisi birbirine yakin, ama
 * esit degil; o yuzden sayfada hicbir yerde "yayımlandı" demiyoruz.
 */

(function () {
  "use strict";

  var DAKIKA = 60000;
  var SAAT = 60 * DAKIKA;
  var GUN = 24 * SAAT;

  function metin(fark) {
    // Ileri tarihli damga: saat farki ya da kaynak hatasi. "-3 dk önce"
    // yazmaktansa en yakin dogru ifadeye yuvarliyoruz.
    if (fark < DAKIKA) return "az önce";
    if (fark < SAAT) return Math.floor(fark / DAKIKA) + " dk önce";
    if (fark < GUN) return Math.floor(fark / SAAT) + " saat önce";
    if (fark < 2 * GUN) return "dün";
    return null; // 2 gunden eskiyse tarih daha bilgilendirici
  }

  function tazele() {
    var simdi = Date.now();
    var hepsi = document.querySelectorAll("time.goreli[datetime]");

    for (var i = 0; i < hepsi.length; i++) {
      var e = hepsi[i];
      var t = Date.parse(e.getAttribute("datetime"));
      if (isNaN(t)) continue;

      // Tam tarih ILK CALISMADA saklaniyor: 2 gunu geceni geri
      // yazabilmek icin. Saklanmasaydi bir kez goreli yazildiktan
      // sonra tarih geri getirilemezdi.
      if (!e.dataset.tam) e.dataset.tam = e.textContent.trim();

      var m = metin(simdi - t);
      e.textContent = m === null ? e.dataset.tam : m;
      if (m !== null) e.title = e.dataset.tam;
    }
  }

  tazele();
  // Dakikada bir: acik birakilan sekmede "3 dk önce" saatlerce
  // donmus kalmasin.
  setInterval(tazele, DAKIKA);
})();
