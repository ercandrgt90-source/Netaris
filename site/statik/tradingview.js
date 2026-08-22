/* TradingView widget'lari -- GORUS ALANINA GIRINCE yukleniyor.
 *
 * NEDEN UCUNCU TARAF
 * ------------------
 * BIST verisini yayimlamak Borsa Istanbul veri dagitim lisansi
 * gerektiriyor ve bizde yok. TradingView'in ucretsiz widget'inda
 * lisans SAGLAYICIDA: veriyi biz dagitmiyoruz, onlarin cercevesi
 * gosteriyor. Yasal yol bu; kazimak degil.
 *
 * Bedeli gizlenmiyor: ziyaretcinin IP'si ve tarayici bilgisi
 * TradingView'a gidiyor. Gizlilik beyani bunu ACIKCA yaziyor ve
 * `beyan_denetimi.py` beyanin gercekle ortustugunu deneteliyor.
 *
 * VERI 15 DAKIKA GECIKMELI -- ucretsiz widget'ta BIST boyle geliyor.
 * Sayfada yazili: gecikmeli bir fiyati anlik saniyan okur yanilir ve
 * o yanilgi bizim sorumlulugumuz.
 *
 * NEDEN GECIKMELI YUKLEME
 * -----------------------
 * Sitenin LCP'si 338 ms ve bunun sebebi kismen ucuncu taraf betigi
 * OLMAMASI. Widget betigini sayfayla birlikte yuklemek o olcumu
 * dogrudan bozardi.
 *
 * Betik yalnizca kutu gorus alanina YAKLASINCA ekleniyor. Okur o
 * bolume hic inmezse TradingView'a HICBIR ISTEK gitmiyor -- yani
 * gizlilik maliyeti de yalnizca gercekten bakan okur icin doguyor.
 *
 * `IntersectionObserver` yoksa widget hic yuklenmiyor ve yerinde
 * aciklama kalir: eksik ozellik, bozuk sayfa degil.
 *
 * ATIF ZORUNLU
 * ------------
 * TradingView kullanim kosullari widget atfini kaldirmayi yasakliyor
 * ve yaptirim olarak kalici yasak, ihtarname ve tazminat sayiyor.
 * Atif blogu SABLONDA basili ve buradan silinmiyor.
 */
(function () {
  "use strict";

  var KOK = "https://s3.tradingview.com/external-embedding/";

  /* Tema TradingView'a AYRICA bildiriliyor: widget kendi CSS'ini
     tasiyor ve bizim jetonlarimizi gormuyor. Koyu temada acik bir
     kutu, sayfanin ortasinda beyaz bir delik olurdu. */
  function tema() {
    try {
      var t = document.documentElement.getAttribute("data-tema");
      if (t) return t === "dark" ? "dark" : "light";
      return window.matchMedia
        && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark" : "light";
    } catch (e) { return "light"; }
  }

  /* Tur -> (betik dosyasi, yapilandirma). Yeni bir widget turu
     eklemek buraya bir satir; kutu isaretlemesi ayni kaliyor. */
  function ayar(kutu) {
    var tur = kutu.getAttribute("data-tv-tur") || "";
    var sembol = kutu.getAttribute("data-tv-sembol") || "";

    if (tur === "serit") {
      /* Semboller BIST'in en cok izlenen uc olcusu. Genis liste
         seridi kalabaliklastirir ve okurun aradigini bulmasini
         zorlastirir -- ayni gerekce kendi fiyat seridimizde yazili. */
      return [KOK + "embed-widget-ticker-tape.js", {
        symbols: [
          { proName: "BIST:XU100", title: "BIST 100" },
          { proName: "BIST:XU030", title: "BIST 30" },
          { proName: "BIST:XBANK", title: "Bankacılık" }
        ],
        showSymbolLogo: false,
        isTransparent: true,
        displayMode: "compact",
        colorTheme: tema(),
        locale: "tr"
      }];
    }

    if (tur === "grafik" && sembol) {
      /* Bilanco sayfasinda ILGILI HISSENIN grafigi. Bilanco bir
         donemin fotografi; fiyat o donemden bu yana ne olduğunu
         gosteriyor ve ikisi birlikte okununca anlam kazaniyor.
         Bu yuzden 12 aylik pencere: son ceyrek tek basina bilancoyla
         karsilastirilamayacak kadar kisa. */
      return [KOK + "embed-widget-mini-symbol-overview.js", {
        symbol: sembol,
        width: "100%",
        height: 220,
        locale: "tr",
        dateRange: "12M",
        colorTheme: tema(),
        isTransparent: true,
        autosize: false,
        largeChartUrl: "",
        chartOnly: false,
        noTimeScale: false
      }];
    }
    return null;
  }

  function yukle(kutu) {
    if (kutu.getAttribute("data-tv-yuklendi")) return;
    var hedef = kutu.querySelector(".tradingview-widget-container__widget");
    if (!hedef) return;
    var a = ayar(kutu);
    if (!a) return;
    kutu.setAttribute("data-tv-yuklendi", "1");

    var s = document.createElement("script");
    s.type = "text/javascript";
    s.async = true;
    s.src = a[0];
    s.text = JSON.stringify(a[1]);
    hedef.appendChild(s);
  }

  var kutular = document.querySelectorAll("[data-tv]");
  if (!kutular.length) return;
  if (typeof IntersectionObserver !== "function") return;

  var gozcu = new IntersectionObserver(function (girisler) {
    for (var i = 0; i < girisler.length; i++) {
      if (girisler[i].isIntersecting) {
        yukle(girisler[i].target);
        gozcu.unobserve(girisler[i].target);
      }
    }
  }, { rootMargin: "200px" });   /* biraz once basla, bosluk gorunmesin */

  for (var i = 0; i < kutular.length; i++) gozcu.observe(kutular[i]);
})();
