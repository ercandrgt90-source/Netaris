/* Giris sonrasi DONUS ADRESI -- okurun niyetini kaybetmemek icin.
 *
 * OLCULEN SIZINTI
 * ---------------
 * Haber sayfasindaki "Senaryo yaz" dugmesi su adrese gidiyor:
 *
 *     /panel/?senaryo=/haber/xxx/&baslik=...
 *
 * Okur oturum acmamissa panel "Oturum gerekli" diyor, okur giris
 * yapiyor ve `location.href = "/panel/"` calisiyor -- SORGU
 * PARAMETRELERI DUSUYOR.
 *
 * Sonuc: okur bir haber icin senaryo yazmaya geldi, BOS BIR PANELE
 * dustu. Hangi habere yazdigini yeniden bulmasi, geri gidip dugmeye
 * tekrar basmasi gerekiyor -- ve cogu kisi bunu yapmiyor.
 *
 * Hicbir hata gorunmuyordu: giris basarili, panel aciliyor, her sey
 * "calisiyor". Yalnizca okurun NIYETI kayboluyordu.
 *
 * ACIK YONLENDIRME RISKI
 * ----------------------
 * Donus adresi ADRESTEN geliyor, yani saldirgan kontrolunde. Dogrudan
 * kullanilirsa `/giris/?donus=https://kotu.example/` gibi bir baglanti
 * okuru giris yaptiktan sonra baska siteye atardi -- klasik acik
 * yonlendirme.
 *
 * Bu yuzden `guvenli` YALNIZCA tek egik cizgiyle baslayan goreli
 * yollari kabul ediyor. "//baska.site" ve "/\baska.site" de
 * REDDEDILIYOR: tarayicilar ikisini de protokol-goreli mutlak adres
 * olarak cozuyor.
 */
(function (kok) {
  "use strict";

  var VARSAYILAN = "/panel/";

  /* Yalnizca AYNI SITEDE bir yol. Baska her sey varsayilana duser --
     sessizce, cunku bu bir kullanici hatasi degil saldiri denemesi ve
     okura aciklanacak bir sey yok. */
  function guvenli(yol) {
    if (typeof yol !== "string" || yol.charAt(0) !== "/") return VARSAYILAN;
    /* Ikinci karakter egik cizgi ya da ters egik cizgiyse adres
       protokol-gorelidir ve baska bir siteye cikar. */
    var ikinci = yol.charAt(1);
    if (ikinci === "/" || ikinci === "\\") return VARSAYILAN;
    return yol;
  }

  /* Suanki sayfanin tam yolu (sorgu ve capa dahil) -- giris
     baglantisina eklenecek deger. */
  function suanki() {
    return guvenli(location.pathname + location.search + location.hash);
  }

  /* Adresteki `donus` degeri; yoksa varsayilan. */
  function hedef() {
    try {
      return guvenli(new URLSearchParams(location.search).get("donus") || "");
    } catch (e) {
      return VARSAYILAN;
    }
  }

  /* Giris baglantisina donus adresini ekler.
     Ornek: /giris/  ->  /giris/?donus=%2Fpanel%2F%3Fsenaryo%3D... */
  function baglantiyaEkle(a) {
    if (!a || !a.getAttribute) return;
    var h = a.getAttribute("href") || "";
    if (h.indexOf("donus=") !== -1) return;
    a.setAttribute("href",
      h + (h.indexOf("?") === -1 ? "?" : "&") +
      "donus=" + encodeURIComponent(suanki()));
  }

  kok.NetarisDonus = {
    guvenli: guvenli,
    suanki: suanki,
    hedef: hedef,
    baglantiyaEkle: baglantiyaEkle,
    VARSAYILAN: VARSAYILAN
  };
})(typeof window !== "undefined" ? window : globalThis);
