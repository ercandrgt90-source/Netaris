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

  /* TOAST -- kopyalama onayi.
     ------------------------
     Dugmenin kendi metnini degistirmek de calisiyordu ama iki sorunu
     vardi: buyuk paylasim blogunda dugme ekranin disinda kalabiliyor
     ve ekran okuyucu degisikligi duyurmuyordu.
     `role="status"` ile duyuruluyor, `aria-live="polite"` ile de
     okurun o anki okumasini kesmiyor. */
  var toastZaman = null;

  function toast(mesaj) {
    var k = document.getElementById("paylas-toast");
    if (!k) {
      k = document.createElement("div");
      k.id = "paylas-toast";
      k.className = "paylas-toast";
      k.setAttribute("role", "status");
      k.setAttribute("aria-live", "polite");
      document.body.appendChild(k);
    }
    k.textContent = mesaj;
    k.classList.add("gorunur");
    clearTimeout(toastZaman);
    toastZaman = setTimeout(function () {
      k.classList.remove("gorunur");
    }, 2400);
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
      toast("Bağlantı kopyalandı");
      /* Dugme metni de degisiyor: toast ekranin altinda, dugme
         parmagin altinda. Ikisi ayni seyi soyluyor ama okur
         hangisine bakiyorsa onu goruyor. */
      var eski = d.textContent;
      d.textContent = "Kopyalandı";
      d.classList.add("paylas-tamam");
      setTimeout(function () {
        d.textContent = eski;
        d.classList.remove("paylas-tamam");
      }, 1800);
    }).catch(function () {
      /* Pano kapali ya da izin yok. SESSIZ KALMIYOR: okur dugmeye
         bastigini biliyor, hicbir sey olmamasi kirik gorunur. */
      toast("Kopyalanamadı — bağlantıyı elle seçin");
    });
  });

  window.NetarisPaylas = { html: html, adres: adres };

  /* SAYFA PAYLASIMINDAKI KOPYALA DUGMESI.
     ------------------------------------
     Dugme sablonda `hidden` basiliyor ve burasi aciyor: betik
     yuklenmediginde calismayan bir dugme gorunmesin. Calismayan dugme,
     olmayan dugmeden kotudur -- okur tiklar, bir sey olmaz, siteye
     guveni azalir.

     Tiklama isleyicisi zaten asagida (`data-paylas-kopyala`); burada
     yalnizca gorunurluk aciliyor. */
  function kopyaDugmeleriniAc() {
    /* SAVUNMALI: `querySelectorAll` her ortamda YOK.
       Ilk yazimda dogrudan cagirdim ve `test_paylas.js` COKTU --
       testin DOM taklidi o islevi saglamiyor. Ayni durum eski
       tarayicida ya da kismi bir ortamda da olusur ve o zaman
       dosyanin GERI KALANI da calismaz: bir IIFE icinde firlayan
       hata, altindaki tiklama isleyicisini de kaydettirmez.

       Yani savunmasiz tek satir, butun paylasim betigini
       dusurebilirdi. */
    if (!document || typeof document.querySelectorAll !== "function") return;
    var d = document.querySelectorAll(".sp-kopya[hidden]");
    for (var i = 0; i < d.length; i++) d[i].hidden = false;
  }

  /* YEREL PAYLASIM SAYFASI.
     ----------------------
     `navigator.share` isletim sisteminin kendi paylasim sayfasini
     aciyor: okurun KURULU uygulamalari cikiyor, bizim tahmin
     ettiklerimiz degil.

     Bir sey daha cozuyor: INSTAGRAM'IN WEB PAYLASIM ADRESI YOK. Bir
     web sayfasindan Instagram'a baglanti paylasilamaz -- ne biz ne
     baska bir site yapabilir. Yerel sayfa bunu isletim sistemi
     uzerinden cozuyor.

     KOSUL SADECE `navigator.share` DEGIL.
     Masaustu tarayicilarin bir kismi da destekliyor ama orada bes
     baglantilik seri DAHA IYI: tek tikla hedef belli, ustelik hangi
     kanallarda oldugumuz gorunuyor. Bu yuzden dar ekran kosulu da
     araniyor.

     `matchMedia` yoksa hicbir sey yapilmiyor: seri oldugu gibi
     kaliyor ve okur bir sey kaybetmiyor. */
  function yerelPaylasimiAc() {
    if (!document || typeof document.querySelectorAll !== "function") return;
    if (!navigator || typeof navigator.share !== "function") return;
    if (typeof window.matchMedia !== "function") return;
    if (!window.matchMedia("(max-width: 640px)").matches) return;

    var dugmeler = document.querySelectorAll("[data-paylas-yerel]");
    for (var i = 0; i < dugmeler.length; i++) {
      var d = dugmeler[i];
      d.hidden = false;
      /* Baglanti serisi gizleniyor: iki paylasim yolu yan yana
         durursa okur hangisinin ne yaptigini bilemiyor. */
      var kap = d.parentNode
        && d.parentNode.querySelector(".sayfa-paylas-dugmeler");
      if (kap) kap.hidden = true;
    }
  }

  document.addEventListener("click", function (o) {
    var d = o.target.closest && o.target.closest("[data-paylas-yerel]");
    if (!d) return;
    /* Iptal bir HATA DEGIL: okur sayfayi kapatinca `AbortError`
       firliyor ve yakalanmazsa kayda hata olarak dusuyor. */
    navigator.share({
      title: d.getAttribute("data-baslik") || document.title,
      text: d.getAttribute("data-metin") || "",
      url: d.getAttribute("data-adres") || window.location.href
    }).catch(function () {});
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      kopyaDugmeleriniAc();
      yerelPaylasimiAc();
    });
  } else {
    kopyaDugmeleriniAc();
    yerelPaylasimiAc();
  }

})();
