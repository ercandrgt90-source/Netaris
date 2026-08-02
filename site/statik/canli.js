/* Kayan fiyat seridi.
 *
 * NOKTA NE ANLATIR
 * ----------------
 *   yesil, nabiz atan : gercek zamanli akis (Binance)
 *   gri, sabit        : son veri -- gunluk yayimlanan resmi seri
 *
 * KIRMIZI NOKTA KULLANILMIYOR. Sebebi su: bu arayuzde kirmizi ve yesil
 * YALNIZCA sayinin yonunu anlatiyor (dustu / yukseldi). Ayni iki rengi bir
 * de "canli / canli degil" icin kullanmak, dusen bir fiyatin yaninda
 * kirmizi nokta gorunce hangi anlama geldigini belirsiz birakirdi.
 * Canli olmayan kalem gri nokta tasir.
 *
 * KAYNAKLAR
 *   Binance      : gercek zamanli, anahtarsiz, 24 saatlik degisim yuzdesi
 *   Frankfurter  : ECB referans kurlari, gunluk; degisim icin son iki is
 *                  gunu tek istekte cekiliyor
 *   FRED         : sunucu tarafinda, insa aninda yazilmis gunluk seriler
 *
 * BOZULURSA: serit sunucudan dolu geliyor. Ag hatasi, engelleyici ya da
 * JavaScript kapali olmasi sayfayi bozmaz -- yalnizca canli kalemler
 * eklenmez ve nokta gri kalir.
 */

(function () {
  "use strict";

  var SIRA = document.querySelector("[data-serit-sira]");
  var AKIS = document.querySelector("[data-serit-akis]");
  if (!SIRA) return;

  var YENILEME_MS = 30000;

  /* Kraken birincil kaynak: cografi kisiti yok, her ulkeden calisir.
     Binance ABD IP'lerini HTTP 451 ile engelliyor -- ABD'den bakan bir
     ziyaretcide serit sessizce eksik kalirdi. */
  var KRAKEN =
    "https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD,PAXGUSD";

  /* Binance YALNIZCA USDT/TRY icin: Kraken'de TRY paritesi yok. Turk
     ziyaretcide calisir; engellenen bir ulkeden bakilirsa bu tek kalem
     sessizce eklenmez, serit calismaya devam eder. */
  var BINANCE =
    "https://api.binance.com/api/v3/ticker/24hr?symbol=USDTTRY";

  // Son 8 gunu ister, son iki is gununu kullanir (hafta sonu bosluklari icin)
  var FRANKFURTER_TABAN = "https://api.frankfurter.app/";

  /* Kraken cevap anahtarlari istek adindan farkli gelir: "XBTUSD" ->
     "XXBTZUSD". Eslesme bu yuzden anahtarla degil, icerdigi kodla
     yapiliyor.
     PAXG bir ons altina %100 dayali token; spot altini yakindan izler ama
     LBMA fiksingi DEGILDIR, o yuzden "ALTIN (PAXG)" diye etiketleniyor. */
  var KRAKEN_ADLARI = [
    { iz: "XBT", ad: "BTC/USD", basamak: 0 },
    { iz: "ETH", ad: "ETH/USD", basamak: 0 },
    { iz: "PAXG", ad: "ALTIN (PAXG)", basamak: 0 }
  ];

  function trSayi(deger, basamak) {
    return deger.toLocaleString("tr-TR", {
      minimumFractionDigits: basamak,
      maximumFractionDigits: basamak
    });
  }

  function gunOnce(gunSayisi) {
    var d = new Date();
    d.setDate(d.getDate() - gunSayisi);
    return d.toISOString().slice(0, 10);
  }

  function yuzdeMetni(yuzde) {
    if (typeof yuzde !== "number" || !isFinite(yuzde)) return "—";
    return (yuzde > 0 ? "+" : yuzde < 0 ? "-" : "") +
           trSayi(Math.abs(yuzde), 2) + "%";
  }

  function kalemKur(anahtar, ad, deger, yuzde, canliMi) {
    var kalem = SIRA.querySelector('[data-kalem="' + anahtar + '"]');
    if (!kalem) {
      kalem = document.createElement("span");
      kalem.className = "kalem";
      kalem.setAttribute("data-kalem", anahtar);
      // Canli kalemler sunucudan gelen sabit kalemlerin ONUNE girer
      var ilkSabit = SIRA.querySelector(".kalem:not([data-kalem])");
      if (ilkSabit) SIRA.insertBefore(kalem, ilkSabit);
      else SIRA.appendChild(kalem);
    }

    var yon = "yatay";
    if (typeof yuzde === "number" && yuzde > 0) yon = "artis";
    else if (typeof yuzde === "number" && yuzde < 0) yon = "azalis";

    kalem.innerHTML =
      '<span class="nokta ' + (canliMi ? "nokta-canli" : "nokta-gecmis") + '"></span>' +
      '<span class="kalem-ad">' + ad + "</span>" +
      '<span class="kalem-deger">' + deger + "</span>" +
      '<span class="kalem-fark ' + yon + '">' + yuzdeMetni(yuzde) + "</span>";
    kalem.title = ad + (canliMi
      ? " — canlı akış (Binance), 24 saatlik değişim"
      : " — son veri (ECB günlük referans)");
  }

  /* Kayan serit icin ikinci kopya. Animasyon -%50 kaydirdigi icin iki ayni
     dizi yan yana durunca gecis dikissiz olur. */
  function kopyaTazele() {
    if (!AKIS) return;
    var eski = AKIS.querySelector("[data-serit-kopya]");
    if (eski) eski.remove();
    var kopya = SIRA.cloneNode(true);
    kopya.removeAttribute("data-serit-sira");
    kopya.setAttribute("data-serit-kopya", "");
    kopya.setAttribute("aria-hidden", "true");
    AKIS.appendChild(kopya);
    AKIS.classList.add("akiyor");
  }

  function krakenCek() {
    return fetch(KRAKEN, { cache: "no-store" })
      .then(function (y) { return y.ok ? y.json() : Promise.reject(y.status); })
      .then(function (veri) {
        var sonuc = veri && veri.result;
        if (!sonuc) return;
        Object.keys(sonuc).forEach(function (anahtar) {
          var t = sonuc[anahtar];
          var tanim = null;
          for (var i = 0; i < KRAKEN_ADLARI.length; i++) {
            if (anahtar.indexOf(KRAKEN_ADLARI[i].iz) !== -1) {
              tanim = KRAKEN_ADLARI[i];
              break;
            }
          }
          if (!tanim || !t || !t.c || !t.o) return;
          // c[0] = son islem fiyati, o = bugunun acilisi
          var fiyat = parseFloat(t.c[0]);
          var acilis = parseFloat(t.o);
          if (!isFinite(fiyat)) return;
          var yuzde = (isFinite(acilis) && acilis > 0)
            ? (fiyat / acilis - 1) * 100
            : null;
          kalemKur(anahtar, tanim.ad, trSayi(fiyat, tanim.basamak),
                   yuzde, true);
        });
        kopyaTazele();
      })
      .catch(function () { /* sessizce vazgec */ });
  }

  function binanceCek() {
    // Yalnizca USDT/TRY -- Kraken'de TRY paritesi yok
    return fetch(BINANCE, { cache: "no-store" })
      .then(function (y) { return y.ok ? y.json() : Promise.reject(y.status); })
      .then(function (t) {
        var fiyat = parseFloat(t.lastPrice);
        var yuzde = parseFloat(t.priceChangePercent);
        if (!isFinite(fiyat)) return;
        kalemKur("USDTTRY", "USDT/TRY", trSayi(fiyat, 2),
                 isFinite(yuzde) ? yuzde : null, true);
        kopyaTazele();
      })
      .catch(function () { /* engellenmis olabilir -- serit calismaya devam */ });
  }

  function ecbCek() {
    var u = FRANKFURTER_TABAN + gunOnce(8) + ".." + "?from=USD&to=TRY,EUR";
    return fetch(u, { cache: "no-store" })
      .then(function (y) { return y.ok ? y.json() : Promise.reject(y.status); })
      .then(function (veri) {
        if (!veri || !veri.rates) return;
        var gunler = Object.keys(veri.rates).sort();
        if (!gunler.length) return;
        var son = veri.rates[gunler[gunler.length - 1]];
        var onceki = gunler.length > 1 ? veri.rates[gunler[gunler.length - 2]] : null;

        function ekle(anahtar, ad, cikar, basamak) {
          var s = cikar(son);
          if (typeof s !== "number" || !isFinite(s)) return;
          var o = onceki ? cikar(onceki) : null;
          var yuzde = (typeof o === "number" && o > 0) ? (s / o - 1) * 100 : null;
          kalemKur(anahtar, ad, trSayi(s, basamak), yuzde, false);
        }

        ekle("USDTRY_ECB", "USD/TRY", function (r) { return r.TRY; }, 3);
        ekle("EURUSD_ECB", "EUR/USD", function (r) { return r.EUR ? 1 / r.EUR : null; }, 4);
        kopyaTazele();
      })
      .catch(function () { /* sessizce vazgec */ });
  }

  krakenCek();
  binanceCek();
  ecbCek();

  // Kripto ve altin yenilenir; ECB gunluk oldugu icin tekrar cekilmez
  setInterval(function () {
    krakenCek();
    binanceCek();
  }, YENILEME_MS);
})();
