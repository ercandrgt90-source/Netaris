/* Canli fiyat seridi -- TradingView ticker-tape widget'ini kuruyor.
 *
 * NEDEN AYRI BETIK
 * ----------------
 * Widget yapilandirmasi `<script>` etiketinin GOVDESINE JSON olarak
 * yaziliyor. Bu yapilandirmayi sablonda sabit yazsaydik tema secimini
 * okuyamazdik: widget rengini KURULUSTA aliyor ve bizim tema
 * dugmemizi sonradan izlemiyor. Burada once tema okunuyor, sonra
 * widget o renge gore kuruluyor.
 *
 * BETIK CALISMAZSA sablondaki <noscript> seridi gorunur: olculmus
 * degerler, akmayan ama okunabilir bir satir. Veri kaybi yok.
 */
(function () {
  "use strict";

  var kap = document.getElementById("serit-widget");
  if (!kap) return;

  /* Tema: once acik secim (`data-tema`), yoksa sistem tercihi.
     Sirasi onemli -- kullanicinin dugmeyle sectigi sey sistem
     tercihini ezmeli. */
  function tema() {
    var secim = document.documentElement.getAttribute("data-tema");
    if (secim === "dark" || secim === "light") return secim;
    try {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark" : "light";
    } catch (e) {
      return "light";
    }
  }

  /* SEMBOLLER.
     Sira Turk okura gore: once TL pariteleri, sonra enerji (seridin
     asil eksigi buydu -- EIA Brent'i haftalik yayimliyor), sonra
     maden ve endeksler. */
  var semboller = [
    { proName: "FX_IDC:USDTRY", title: "USD/TRY" },
    { proName: "FX_IDC:EURTRY", title: "EUR/TRY" },
    { proName: "TVC:UKOIL", title: "Brent" },
    { proName: "TVC:USOIL", title: "WTI" },
    { proName: "TVC:GOLD", title: "Ons altın" },
    { proName: "TVC:SILVER", title: "Gümüş" },
    { proName: "BIST:XU100", title: "BIST 100" },
    { proName: "SP:SPX", title: "S&P 500" },
    { proName: "TVC:DXY", title: "Dolar endeksi" },
    { proName: "BITSTAMP:BTCUSD", title: "Bitcoin" }
  ];

  var betik = document.createElement("script");
  betik.type = "text/javascript";
  betik.async = true;
  betik.src =
    "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
  betik.innerHTML = JSON.stringify({
    symbols: semboller,
    showSymbolLogo: false,
    isTransparent: true,
    displayMode: "adaptive",
    colorTheme: tema(),
    locale: "tr"
  });

  var ic = document.createElement("div");
  ic.className = "tradingview-widget-container__widget";
  kap.appendChild(ic);
  kap.appendChild(betik);

  /* TEMA DEGISINCE WIDGET YENIDEN KURULUYOR.
     Widget rengini kurulusta aliyor; tema dugmesine basildiginda
     koyu temada acik renk bir serit kaliyordu. Yeniden kurmak,
     desteklenmeyen bir ic API'ye dokunmadan calisan tek yol. */
  var son = tema();
  var gozlemci = new MutationObserver(function () {
    if (tema() === son) return;
    son = tema();
    kap.innerHTML = "";
    var b = betik.cloneNode(false);
    b.innerHTML = JSON.stringify({
      symbols: semboller,
      showSymbolLogo: false,
      isTransparent: true,
      displayMode: "adaptive",
      colorTheme: son,
      locale: "tr"
    });
    var i = document.createElement("div");
    i.className = "tradingview-widget-container__widget";
    kap.appendChild(i);
    kap.appendChild(b);
  });
  gozlemci.observe(document.documentElement,
                   { attributes: true, attributeFilter: ["data-tema"] });
})();
