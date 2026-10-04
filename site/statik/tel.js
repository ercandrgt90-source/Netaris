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

  /* IKI SAYFA, IKI ISARETLEME -- AMA TEK ATIF KARARI.
     ================================================
     `/gundem/` rutin listesi `gundem-*` siniflarini, ana sayfanin
     "Canli akis" bolumu `akis-*` siniflarini kullaniyor. Ayni
     ogeyi iki bicimde basmak gerekiyor.

     RISK ACIK: ayni kurali iki yere yazmak, bu depoda en pahaliya
     mal olan kusur sinifi. O yuzden ATIF KARARI tek bir yerde
     (`atifGecerli` + `kunye`) yasiyor ve iki basici da onu
     cagiriyor; `test_tel_atif.js` ikisini birden tutuyor. */
  var liste = document.querySelector('[data-akis-kap="rutin"]');
  var akis = document.querySelector("[data-tel-akis]");
  if (!liste && !akis) return;

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

  /* ATIF SARTI -- TEK YERDE.
     `ticari` kaynakta kurum adi VE kaynaga baglanti gosterilmek
     zorunda (bkz. haber_botu/kaynak/besleme.py). Sarti saglamayan
     oge HIC basilmiyor: "once goster, atfi sonra ekle" diye bir ara
     durum yok, cunku atifsiz gosterim ihlalin kendisi.

     Iki basici da bunu cagiriyor; sart ikiye bolunmuyor. */
  function atifGecerli(o) {
    if (!o || !o.adres || !/^https?:\/\//i.test(o.adres)) return false;
    return Boolean(o.kurum && o.baslik);
  }

  /* Kunye isaretlemesi -- sayfaya gore sinif adlari degisiyor, ama
     BAGLANTININ VARLIGI degismiyor. */
  function kunyeHtml(o, sinif, baglantiSinifi, ok) {
    if (!o.ticari) {
      return '<span class="' + sinif + '">' + metin(o.kurum) + "</span>";
    }
    return '<a class="' + sinif + " " + baglantiSinifi + '" href="'
      + metin(o.adres) + '" rel="nofollow noopener" target="_blank"'
      + ' title="' + metin((o.kurum_tam || o.kurum) + " sitesinde aç")
      + '">' + metin(o.kurum)
      + (ok ? '<svg class="dis-ok" viewBox="0 0 12 12" width="9" height="9" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8 8.5 3.5"/><path d="M4.6 3.5h3.9v3.9"/></svg>' : "")
      + "</a>";
  }

  function oge(o) {
    if (!atifGecerli(o)) return null;

    var li = document.createElement("li");
    li.className = "gundem-oge gundem-duz tel-oge";
    li.setAttribute("data-tel", "1");

    var kunye = kunyeHtml(o, "rozet", "rozet-kaynak-bag", false);

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

  /* ANA SAYFA BICIMI.
     Sablonun kendi ifadesiyle "Canli akis" bir KAYIT, secim degil:
     "okur 'bir sey oldu mu' sorusunun cevabini burada buluyor".
     Su ana kadar o soruyu yalnizca son insa anina kadar
     cevapliyordu.

     BASLIK TIKLANMAZ: bu ogelerin sayfasi yok ve `anasayfa.html`in
     kendi notu acik -- "kendi ana sayfasindan okurunu baska siteye
     yollamak akisin isi degil". Zorunlu atif KUNYEDE baglanti
     olarak duruyor; aynen basilmis ogelerdeki gibi.

     "Sirket haberleri" TEMA OLARAK BASILMIYOR: o, siniflandirici
     bir sey bulamadiginda dusulen varsayilan kova. Sablon da ayni
     ayrimi yapiyor; yanlis etiket basmaktansa etiketsiz birakmak
     dogru. */
  function akisOgesi(o) {
    if (!atifGecerli(o)) return null;
    var li = document.createElement("li");
    li.className = "akis-normal tel-oge";
    li.setAttribute("data-tel", "1");
    var tema = (o.konu && o.konu !== "Şirket haberleri")
      ? '<span class="akis-tema">' + metin(o.konu) + "</span>" : "";
    li.innerHTML =
      '<span class="akis-zaman">' + metin(saat(o.tarih)) + "</span>"
      + '<span class="akis-baslik akis-sayfasiz">' + metin(o.baslik)
      + "</span>"
      + tema
      + kunyeHtml(o, "akis-kunye", "akis-kunye-baglanti", true)
      + '<span class="rozet tel-rozet" title="Bu başlık siteye henüz'
      + ' işlenmeden, kaynaktan doğrudan geldi">canlı</span>';
    return li;
  }

  function doldur(hedef, basici, ogeler) {
    /* Eskiden yeniye dizilip basa ekleniyor; sonuc en yeni ustte. */
    var parca = document.createDocumentFragment();
    var n = 0;
    ogeler.slice().reverse().forEach(function (o) {
      var li = basici(o);
      if (li) { parca.appendChild(li); n++; }
    });
    if (n) hedef.insertBefore(parca, hedef.firstChild);
    return n;
  }

  function getir() {
    fetch("/api/tel?sonra=" + encodeURIComponent(uretim),
          { headers: { accept: "application/json" } })
      .then(function (y) { return y.ok ? y.json() : null; })
      .then(function (d) {
        if (!d || !d.ogeler || !d.ogeler.length) return;
        var n = 0;
        if (liste) n = doldur(liste, oge, d.ogeler);
        else if (akis) n = doldur(akis, akisOgesi, d.ogeler);
        if (!n) return;
        /* SIRA ONEMLI: once GORUNUR yapiliyor, sonra sayi
           yaziliyor.
           `aria-live` bolgesi GIZLIYKEN yapilan degisiklikler
           duyurulmaz. Ters sirada ekran okuyucu kullanan okur
           canli basliklarin geldigini HIC duymazdi -- ogeler
           sayfada olur ama neden "canli" dediklerini aciklayan
           cumle sessizce belirirdi.

           Liste DEGIL bildirim duyuruluyor: kirk basligi
           okutmak gurultu olurdu; "N baslik ... geldi" tek
           cumlede ayni bilgiyi veriyor. */
        kap.removeAttribute("hidden");
        var sayi = kap.querySelector("[data-tel-sayi]");
        if (sayi) sayi.textContent = String(n);
      })
      .catch(function () { /* Tel dusse sayfa aynen kaliyor. */ });
  }

  getir();
})();
