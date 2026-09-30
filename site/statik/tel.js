/* TEL -- yeniden insa beklemeden taze baslik.
 *
 * NEDEN VAR
 * ---------
 * Site statik ve yalnizca yeniden kuruldugunda taze icerik tasiyor.
 * Olculdu (2026-09-30): zamanlanmis GitHub kosulari cron'un istedigi
 * ~37 kosunun yalnizca %19'unu teslim ediyor; ardisik kosular
 * arasindaki ortanca boslук ~4 saat, gorulen en buyuk ~7. Yani
 * 14:00'te dusen bir haber okura 18:00'de gorunebiliyordu.
 *
 * Bosluğu kapatan mekanizma GitHub'a jetonla gidiyordu; jeton olunce
 * tempo tabana dustu ve GitHub'da jetonsuz tetik YOK. Tel, tazeligi
 * Cloudflare'in kendi cron'una tasiyor: Worker on dakikada bir
 * beslemeyi cekiyor, bu betik de INSADAN DAHA YENI olanlari listenin
 * basina ekliyor.
 *
 * ATIF PAZARLIK KONUSU DEGIL
 * --------------------------
 * `ticari` kaynakta kurum adi VE kaynaga baglanti gosterilmek zorunda
 * (bkz. haber_botu/kaynak/besleme.py). Asagidaki isaretleme
 * `sablonlar/gundem.html`teki ile AYNI -- ayni sinif adlari, ayni
 * `rel`, ayni `title`. Ikinci bir bicim, zamanla ayrisan iki kural
 * demekti.
 *
 * Bir ogenin baglantisi yoksa oge HIC BASILMIYOR. "Once goster, atfi
 * sonra ekle" diye bir ara durum yok: atifsiz gosterim, ihlalin
 * kendisi.
 *
 * JAVASCRIPT YOKSA
 * ----------------
 * Hicbir sey olmuyor ve sayfa basildigi gibi kaliyor. Tel bir EK
 * katman; sitenin okuma tarafi ona bagli degil.
 */
(function () {
  "use strict";

  var kap = document.querySelector('[data-tel-kap]');
  if (!kap) return;

  /* Sayfanin kendi uretim ani. Yalnizca bundan YENI ogeler
     isteniyor; daha eskisini basilmis sayfa zaten tasiyor ve ayni
     haberi iki kez gostermek, sitenin kendini tekrar etmesi demek. */
  var uretim = kap.getAttribute("data-tel-uretim") || "";
  if (!uretim) return;

  var liste = document.querySelector('[data-akis-kap="rutin"]');
  if (!liste) return;

  function metin(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  /* Tarih okurun saatinde, kisa bicimde. */
  function saat(iso) {
    var t = new Date(iso);
    if (isNaN(t.getTime())) return "";
    try {
      return t.toLocaleTimeString("tr-TR",
        { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return iso.slice(11, 16);
    }
  }

  function oge(o) {
    /* ATIF SARTI. Baglantisi ya da kunyesi olmayan oge BASILMIYOR. */
    if (!o || !o.adres || !/^https?:\/\//i.test(o.adres)) return null;
    if (!o.kurum || !o.baslik) return null;

    var li = document.createElement("li");
    li.className = "gundem-oge gundem-duz tel-oge";
    li.setAttribute("data-tel", "1");

    var kunye = o.ticari
      ? '<a class="rozet rozet-kaynak-bag" href="' + metin(o.adres) + '"'
        + ' rel="nofollow noopener" target="_blank" title="'
        + metin((o.kurum_tam || o.kurum) + " sitesinde aç") + '">'
        + metin(o.kurum) + "</a>"
      : '<span class="rozet">' + metin(o.kurum) + "</span>";

    /* MAKINE CEVIRISI OLDUGU SOYLENIYOR.
       Ceviri yapmak kadar, ceviri oldugunu soylemek de gerekiyor:
       resmi bir aciklamada nuans kaybi olabilir ve okur isterse
       kaynaga gidip kendi okuyabilmeli. Ayni ilke `ceviri.py`
       basinda da yazili. */
    var not = o.cevrildi
      ? ' <span class="tel-ceviri" title="' + metin(o.baslik_kaynak || "")
        + '">makine çevirisi</span>'
      : "";

    li.innerHTML =
      '<span class="gundem-ust">'
      + '<span class="rozet rozet-vurgu">' + metin(o.konu) + "</span>"
      + kunye
      + '<span class="tarih">' + metin(saat(o.tarih)) + "</span>"
      + '<span class="rozet tel-rozet" title="Bu başlık siteye henüz'
      + ' işlenmeden, kaynaktan doğrudan geldi">canlı</span>'
      + "</span>"
      + '<span class="gundem-baslik">' + metin(o.baslik) + not + "</span>";
    return li;
  }

  function getir() {
    fetch("/api/tel?sonra=" + encodeURIComponent(uretim),
          { headers: { accept: "application/json" } })
      .then(function (y) { return y.ok ? y.json() : null; })
      .then(function (d) {
        if (!d || !d.ogeler || !d.ogeler.length) return;
        /* Eskiden yeniye dizilip basa ekleniyor; sonuc en yeni
           ustte. */
        var parca = document.createDocumentFragment();
        var n = 0;
        d.ogeler.slice().reverse().forEach(function (o) {
          var li = oge(o);
          if (li) { parca.appendChild(li); n++; }
        });
        if (!n) return;
        liste.insertBefore(parca, liste.firstChild);
        kap.removeAttribute("hidden");
        var sayi = kap.querySelector("[data-tel-sayi]");
        if (sayi) sayi.textContent = String(n);
      })
      .catch(function () { /* Tel dusse sayfa aynen kaliyor. */ });
  }

  getir();
})();
