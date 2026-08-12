/* Senaryo paylasimi -- X ve LinkedIn.
 *
 * NEDEN AYRI DOSYA
 * ----------------
 * Senaryolar IKI yerde listeleniyor: haber sayfasinda (`senaryo.js`) ve
 * topluluk sayfasinda (`topluluk.js`). Ayni kodu iki dosyaya yazmak,
 * birini duzeltip digerini unutmak demektir.
 *
 * NE PAYLASILIYOR
 * ---------------
 * Senaryonun KENDISI: "kosul → sonuc". Yalnizca sayfa adresi
 * paylasilsaydi okur neyi paylastigini gormezdi.
 *
 * Adres, senaryonun CAPASI: bir habere baglıysa o haberin sayfasi,
 * degilse topluluk sayfasi. Sonuna `#senaryo-<id>` capasi ekleniyor ki
 * baglantiya tiklayan dogrudan o senaryoya gitsin.
 *
 * X ILE LINKEDIN AYNI SEKILDE CALISMIYOR
 * --------------------------------------
 * X, `text` parametresini kabul ediyor -- senaryo metnini gonderiyoruz.
 * LinkedIn'in `share-offsite` ucu YALNIZCA adres aliyor; metin
 * parametreleri kaldirildi. LinkedIn kartin basligini ve gorselini
 * sayfanin Open Graph etiketlerinden okuyor -- bu yuzden `og:image`
 * eklenmesi bu isin ONKOSULUYDU.
 *
 * X SINIRI: gonderi 280 karakter ve adres ~23 karakter sayiliyor.
 * Metin 200'e kirpiliyor; kirpilirsa uc nokta ile bitiyor.
 *
 * BETIKSIZ DURUM: bu dosya yuklenmezse dugmeler HIC basilmiyor.
 * Senaryonun kendisi zaten JavaScript ile geliyor; yani betiksiz
 * ziyaretcide kaybolan fazladan bir sey yok.
 */

(function () {
  "use strict";

  var X_SINIR = 200;

  function kacir(m) {
    var d = document.createElement("div");
    d.textContent = m == null ? "" : String(m);
    return d.innerHTML;
  }

  function kirp(m, n) {
    m = String(m || "").replace(/\s+/g, " ").trim();
    return m.length <= n ? m : m.slice(0, n - 1).replace(/\s+\S*$/, "") + "…";
  }

  /* Senaryonun tam adresi. `capa` goreli yol ("/haber/...") ya da bos. */
  function adres(senaryo) {
    /* Capa yoksa BULUNULAN sayfa. Haber sayfasindaki senaryolar
       zaten o sayfaya bagli oldugu icin `capa` alani gonderilmiyor;
       sabit "/topluluk/" yazmak onlari yanlis adrese yollardi. */
    var yol = senaryo.capa || location.pathname;
    /* Capa mutlak adres olarak gelirse oldugu gibi birakiliyor; kendi
       alan adimiz degisebilir (bkz. site/wrangler.toml) ve burada
       sabit bir alan adi yazmak o degisikligi kacirirdi. */
    var tam = /^https?:\/\//.test(yol) ? yol : location.origin + yol;
    return tam + (senaryo.id ? "#senaryo-" + senaryo.id : "");
  }

  function metin(senaryo) {
    var onerme = (senaryo.kosul || "") + " → " + (senaryo.sonuc || "");
    return kirp(onerme, X_SINIR);
  }

  /* Dugmelerin HTML'i. Cagiran taraf bunu kartin icine koyuyor.
     Dogrudan BAGLANTI uretiliyor, tiklama dinleyicisi degil: baglanti
     orta tikla yeni sekmede acilabiliyor, saga tiklayip kopyalanabiliyor
     ve ekran okuyucu ne oldugunu soyluyor. */
  function html(senaryo) {
    var u = adres(senaryo);
    var x = "https://x.com/intent/post?text="
          + encodeURIComponent(metin(senaryo))
          + "&url=" + encodeURIComponent(u);
    var li = "https://www.linkedin.com/sharing/share-offsite/?url="
           + encodeURIComponent(u);

    return '<span class="paylas">' +
      '<span class="paylas-etiket">Paylaş</span>' +
      '<a class="paylas-dugme" href="' + kacir(x) + '"' +
      ' target="_blank" rel="noopener noreferrer"' +
      ' title="Bu senaryoyu X\'te paylaş">X</a>' +
      '<a class="paylas-dugme" href="' + kacir(li) + '"' +
      ' target="_blank" rel="noopener noreferrer"' +
      ' title="Bu senaryoyu LinkedIn\'de paylaş">LinkedIn</a>' +
      '<button class="paylas-dugme" type="button" data-paylas-kopyala="' +
      kacir(u) + '" title="Bağlantıyı kopyala">Bağlantı</button>' +
      '</span>';
  }

  /* Kopyalama tek bir dinleyiciyle, BELGE duzeyinde. Kartlar sonradan
     ve birden cok kez uretildigi icin her karta ayri dinleyici baglamak
     hem tekrar hem sizinti kaynagi olurdu. */
  document.addEventListener("click", function (o) {
    var d = o.target.closest && o.target.closest("[data-paylas-kopyala]");
    if (!d) return;
    var u = d.getAttribute("data-paylas-kopyala");
    if (!navigator.clipboard) return;
    o.preventDefault();
    navigator.clipboard.writeText(u).then(function () {
      var eski = d.textContent;
      d.textContent = "Kopyalandı";
      d.classList.add("paylas-tamam");
      setTimeout(function () {
        d.textContent = eski;
        d.classList.remove("paylas-tamam");
      }, 1800);
    }).catch(function () { /* pano kapaliysa sessiz */ });
  });

  window.NetarisPaylas = { html: html, adres: adres };
})();
