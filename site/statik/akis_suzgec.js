/* Akis suzgeci -- 86 kalemi TURE gore daraltir.
 *
 * NEDEN VAR
 * ---------
 * `/gundem/` sayfasinda 86 kalem var ve ayni anda jeopolitik, enerji,
 * kripto, sirket ve makro basliklar yan yana duruyor. "Fed ne yapti"
 * sorusuyla gelen okur 86 kalemi taramak zorundaydi.
 *
 * BETIKSIZ TAM LISTE
 * ------------------
 * Suzgec serisi HTML'de `hidden` basiliyor ve burada aciliyor. Betik
 * yuklenmezse seri HIC gorunmuyor ve okur tam listeyi goruyor -- ki
 * sayfanin isi zaten o. Bozulma yonu dogru: eksik ozellik, bozuk
 * sayfa degil.
 *
 * Calismayan bir dugme, olmayan dugmeden kotudur; ayni gerekce
 * `_paylas.html` icindeki kopyalama dugmesinde de yazili.
 *
 * SECIM ADRESTE TASINIYOR
 * -----------------------
 * `?tur=makro` desteklenmesi bilincli: okur bir turu suzup baglantiyi
 * paylasabiliyor ve geri tusu calisiyor. Suzgec bir gorunum durumu
 * degil, sayfanin bir hali.
 */
(function () {
  "use strict";

  var seri = document.querySelector("[data-akis-suzgec]");
  if (!seri) return;

  var ogeler = document.querySelectorAll("[data-tur]");
  if (!ogeler.length) return;

  var bos = document.querySelector("[data-akis-bos]");
  var dugmeler = seri.querySelectorAll(".suzgec-dugme");

  /* Bolum basliklari: bir bolumun tamami suzulurse basligi da
   * gizleniyor. Yoksa "Piyasa etkisi olanlar (12)" yazip altinda
   * hicbir sey olmayan bir baslik kaliyor -- okur bir hata sanir. */
  function bolumleriTazele() {
    var kaplar = document.querySelectorAll("[data-akis-kap]");
    var toplam = 0;
    for (var i = 0; i < kaplar.length; i++) {
      var kap = kaplar[i];
      var gorunen = kap.querySelectorAll("[data-tur]:not([hidden])").length;
      toplam += gorunen;
      var ad = kap.getAttribute("data-akis-kap");
      var bas = document.querySelector('[data-akis-bolum="' + ad + '"]');
      if (bas) {
        bas.hidden = gorunen === 0;
        /* Sayi da guncelleniyor: suzulmus listede "(12)" yazip 3 oge
         * gostermek, sayiyi yanlis bir olcum haline getirir. */
        var say = bas.querySelector("[data-akis-say]");
        if (say) say.textContent = "(" + gorunen + ")";
      }
      kap.hidden = gorunen === 0;
    }
    if (bos) bos.hidden = toplam !== 0;
  }

  function uygula(tur, adresYaz) {
    for (var i = 0; i < ogeler.length; i++) {
      ogeler[i].hidden = !!tur && ogeler[i].getAttribute("data-tur") !== tur;
    }
    for (var j = 0; j < dugmeler.length; j++) {
      var d = dugmeler[j];
      var etkin = (d.getAttribute("data-tur") || "") === (tur || "");
      d.setAttribute("aria-pressed", etkin ? "true" : "false");
      d.classList.toggle("suzgec-etkin", etkin);
    }
    bolumleriTazele();

    if (adresYaz && window.history && window.history.replaceState) {
      var u = new URL(window.location.href);
      if (tur) u.searchParams.set("tur", tur);
      else u.searchParams.delete("tur");
      window.history.replaceState(null, "", u);
    }
  }

  seri.addEventListener("click", function (e) {
    var d = e.target.closest ? e.target.closest(".suzgec-dugme") : null;
    if (!d) return;
    uygula(d.getAttribute("data-tur") || "", true);
  });

  seri.hidden = false;

  /* Adreste tur varsa onunla acilir -- paylasilan baglanti dogru
   * gorunumu getirsin. Tanimsiz bir tur gelirse tam liste aciliyor;
   * bos ekran, yanlis adresten daha kotu bir cevap olurdu. */
  var istenen = new URL(window.location.href).searchParams.get("tur") || "";
  var gecerli = false;
  for (var k = 0; k < dugmeler.length; k++) {
    if ((dugmeler[k].getAttribute("data-tur") || "") === istenen) gecerli = true;
  }
  uygula(gecerli ? istenen : "", false);
})();
