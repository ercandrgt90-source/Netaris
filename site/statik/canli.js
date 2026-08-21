/* Kayan fiyat seridi.
 *
 * NOKTA NE ANLATIR
 * ----------------
 *   yesil, nabiz atan : gercek zamanli akis (Kraken / Binance) -- bu dosya
 *   gri, sabit        : son veri, gunluk resmi seri -- sunucu sablonu
 *   sari              : yayin ritmi seyrek, kalem beklenenden eski
 *
 * KIRMIZI NOKTA KULLANILMIYOR. Sebebi su: bu arayuzde kirmizi ve yesil
 * YALNIZCA sayinin yonunu anlatiyor (dustu / yukseldi). Ayni iki rengi bir
 * de "canli / canli degil" icin kullanmak, dusen bir fiyatin yaninda
 * kirmizi nokta gorunce hangi anlama geldigini belirsiz birakirdi.
 * Canli olmayan kalem gri nokta tasir.
 *
 * KAYNAKLAR
 *   Kraken       : gercek zamanli kripto ve altin, anahtarsiz, cografi
 *                  kisitsiz; 24 saatlik degisim
 *   Binance      : YALNIZCA USDT/TRY -- Kraken'de TRY paritesi yok
 *   FRED / TCMB  : sunucu tarafinda, insa aninda yazilmis gunluk seriler
 *
 * BU KATMAN KUR BASMAZ.
 * ---------------------
 * Eskiden Frankfurter'dan USD/TRY ve EUR/USD de cekiliyordu; o zaman
 * serit yalnizca FRED'den besleniyordu ve kur sunucuda YOKTU. Sunucu
 * tarafina TCMB kurlari eklenince bu katman gereksizlesti ama yerinde
 * kaldi ve iki kalem seritte IKI KEZ, FARKLI DEGERLE goruntulendi:
 * USD/TRY hem TCMB'den 47,71 (ayni gun) hem Frankfurter'dan 47,695
 * (bir onceki gun). Ayni enstrumanin iki fiyati bir okur icin veri
 * degil, guvensizliktir.
 *
 * Kaldirildi. Sunucu surumu her iki olcumde de daha iyi: TCMB kuru
 * AYNI GUN yayimliyor, EUR/USD ise zaten dogrudan ECB'den geliyor --
 * Frankfurter da ayni ECB verisini ikinci elden tasiyordu.
 *
 * Cakismayi `denetim.py` artik statik olarak yakaliyor: sunucunun
 * bastigi kalem adlariyla bu dosyanin ekledigi adlar kesisirse yayin
 * "hata" veriyor.
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

  /* Kraken cevap anahtarlari istek adindan farkli gelir: "XBTUSD" ->
     "XXBTZUSD". Eslesme bu yuzden anahtarla degil, icerdigi kodla
     yapiliyor.

     Seritte sembol GORUNMUYOR -- "ALTIN (PAXG)" seridi kalabaliklastiriyordu.
     Enstrumanin ne oldugu kaleme gelince cikan aciklamada yaziyor: PAXG
     bir ons altina dayali token, spot altini yakindan izler ama LBMA
     fiksingi degildir. Bilgi kayboluyor degil, yer degistiriyor. */
  var KRAKEN_ADLARI = [
    { iz: "XBT", ad: "BTC/USD", basamak: 0, aciklama: "Bitcoin — Kraken" },
    { iz: "ETH", ad: "ETH/USD", basamak: 0, aciklama: "Ethereum — Kraken" },
    { iz: "PAXG", ad: "ALTIN", basamak: 0,
      aciklama: "Altın — PAXG token fiyatı (Kraken). Bir ons altına "
              + "dayalıdır, LBMA fiksingi değildir." }
  ];

  function trSayi(deger, basamak) {
    return deger.toLocaleString("tr-TR", {
      minimumFractionDigits: basamak,
      maximumFractionDigits: basamak
    });
  }

  function yuzdeMetni(yuzde) {
    if (typeof yuzde !== "number" || !isFinite(yuzde)) return "—";
    /* TURKCE YUZDE: isaret sayidan ONCE gelir -- %0,04, "0,04%" degil.
       Artı/eksi de IFADENIN onunde: +%0,04.

       OLCULDU: serit "+0,04%" basiyordu, oysa `piyasa_kutusu._yuzde`
       ayni sayfada "+%0,04" basiyor. Iki bicim ayni ekranda yan yana
       duruyordu; okur hangisinin dogru oldugunu bilemez ve sitenin
       kendi kuralina uymadigini gorur. */
    return (yuzde > 0 ? "+" : yuzde < 0 ? "-" : "") +
           "%" + trSayi(Math.abs(yuzde), 2);
  }

  /* Bu dosyanin ekledigi HER kalem canli -- gunluk resmi seriler
     sunucuda basiliyor. Eskiden bir de "canli degil" dali vardi;
     ECB kur katmani kaldirilinca cagrilamaz hale geldi ve gri nokta
     ile "ECB gunluk referans" aciklamasini uretmeye devam ediyordu.
     Cagrilamayan dal, yanlis aciklama demektir. */
  function kalemKur(anahtar, ad, deger, yuzde, aciklama) {
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
      '<span class="nokta nokta-canli"></span>' +
      '<span class="kalem-ad">' + ad + "</span>" +
      '<span class="kalem-deger">' + deger + "</span>" +
      '<span class="kalem-fark ' + yon + '">' + yuzdeMetni(yuzde) + "</span>";
    /* Enstrumanin ne oldugu ve verinin nereden geldigi seritte degil
       BURADA duruyor -- serit dar, aciklama uzun. */
    kalem.title = aciklama || (ad + " — canlı akış, 24 saatlik değişim");
  }

  /* Kayan serit icin ikinci kopya. Animasyon -%50 kaydirdigi icin iki ayni
     dizi yan yana durunca gecis dikissiz olur. */
  /* Hareketi azaltma tercihi acikken kopya HIC eklenmiyor.
     CSS animasyonu zaten kapatiyor; kopyayi da eklememek ekran
     okuyucunun ayni fiyatlari iki kez okumasini onluyor. Son dakika
     seridinde bu kural bastan beri vardi, fiyat seridinde yoktu. */
  var AZALT = window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)");

  function kopyaTazele() {
    if (!AKIS) return;
    if (AZALT && AZALT.matches) return;
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
                   yuzde, tanim.aciklama);
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
                 isFinite(yuzde) ? yuzde : null);
        kopyaTazele();
      })
      .catch(function () { /* engellenmis olabilir -- serit calismaya devam */ });
  }

  /* AKIS ONCE BASLAR, VERI SONRA GELIR.
     ---------------------------------
     Serit sunucuda DOLU basiliyor; bu dosya yalnizca uzerine canli
     kalem EKLIYOR. Dolayisiyla hareketin bir ag istegine bagli olmasi
     icin hicbir sebep yok.

     Bagliydi ve KIRIKTI: `kopyaTazele()` yalnizca `krakenCek` ve
     `binanceCek` BASARILI olursa cagriliyordu, o da hem ikinci kopyayi
     hem `akiyor` sinifini ekliyordu. Iki uc da Turkiye'den erisilemiyor
     (olculdu: ikisi de baglanti kuramiyor; Binance ayrica yasal olarak
     engelli). Sonuc: serit hic akmiyordu.

     Ucuncu bir yol daha vardi -- Frankfurter'dan kur ceken katman
     erisilebilir oldugu icin pratikte animasyonu O baslatiyordu. Kur
     katmanini serit cakismasi yuzunden kaldirinca, farkinda olmadan
     akisin tek calisan tetigini de kaldirmis oldum.

     Artik koşulsuz: sayfa yuklenince serit akmaya basliyor, canli
     kalemler gelirse kopya tazeleniyor, gelmezse serit yine akiyor. */
  kopyaTazele();

  krakenCek();
  binanceCek();

  setInterval(function () {
    krakenCek();
    binanceCek();
  }, YENILEME_MS);
})();
