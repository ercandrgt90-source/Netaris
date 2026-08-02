/* Istemci tarafi arama.
 *
 * NEDEN BOYLE: site sunucusuz. Arama icin ya ucuncu parti bir hizmet
 * (her aramada disariya istek, gizlilik yuku) ya da tarayicida calisan
 * kucuk bir dizin gerekir. Ikincisi secildi -- hicbir sorgu disariya
 * gitmiyor, kimse ne aradiginizi gormuyor.
 *
 * TURKCE ESLESME: dizindeki metin ve sorgu, ikisi de diakritiksiz
 * karsilastirilir. Kullanici "bilanco" yazip "bilanço" bulmayi bekler.
 */

(function () {
  "use strict";

  var kutu = document.querySelector("[data-ara-kutu]");
  var sonuc = document.querySelector("[data-ara-sonuc]");
  var sayac = document.querySelector("[data-ara-sayac]");
  if (!kutu || !sonuc) return;

  var DIZIN = null;
  var KATLAMA = {
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
    "â": "a", "î": "i", "û": "u"
  };

  function katla(m) {
    var c = "";
    for (var i = 0; i < m.length; i++) {
      var h = m[i];
      c += KATLAMA[h] !== undefined ? KATLAMA[h] : h;
    }
    return c.toLowerCase();
  }

  function kacis(m) {
    var d = document.createElement("div");
    d.textContent = m;
    return d.innerHTML;
  }

  function ciz(kayitlar, sorgu) {
    if (!kayitlar.length) {
      sonuc.innerHTML =
        '<li class="ara-bos">“' + kacis(sorgu) + '” için sonuç bulunamadı. ' +
        "Hisse kodu, şirket adı veya konu deneyebilirsiniz.</li>";
      if (sayac) sayac.textContent = "";
      return;
    }
    if (sayac) {
      sayac.textContent = kayitlar.length + " sonuç";
    }
    sonuc.innerHTML = kayitlar.map(function (k) {
      var rozetler = '<span class="rozet rozet-vurgu">' + kacis(k.k) + "</span>";
      if (k.kod) rozetler += '<span class="rozet rozet-kod">' + kacis(k.kod) + "</span>";
      return (
        '<li><a class="ara-kart" href="' + k.y + '">' +
        '<span class="ust-satir">' + rozetler + "</span>" +
        '<span class="ara-baslik">' + kacis(k.b) + "</span>" +
        '<span class="ara-ozet">' + kacis(k.o) + "</span>" +
        '<span class="kart-kunye"><span>' + kacis(k.t) + "</span>" +
        '<span class="ayrac">·</span><span>' + k.d + " dk okuma</span></span>" +
        "</a></li>"
      );
    }).join("");
  }

  function ara() {
    var sorgu = kutu.value.trim();
    if (!DIZIN) return;
    if (sorgu.length < 2) {
      sonuc.innerHTML = "";
      if (sayac) sayac.textContent = "";
      return;
    }
    var parcalar = katla(sorgu).split(/\s+/).filter(Boolean);
    // Butun sozcukler gecmeli -- "tera bilanco" ikisini birden arar
    var bulunan = DIZIN.filter(function (k) {
      return parcalar.every(function (p) { return k.a.indexOf(p) !== -1; });
    });
    ciz(bulunan, sorgu);
  }

  function baslat() {
    fetch("/arama.json", { cache: "no-cache" })
      .then(function (y) { return y.json(); })
      .then(function (veri) {
        DIZIN = veri;
        kutu.disabled = false;
        kutu.placeholder = "Hisse kodu, şirket veya konu ara…";
        // Adreste ?q= varsa dogrudan ara
        var q = new URLSearchParams(location.search).get("q");
        if (q) { kutu.value = q; }
        kutu.focus();
        ara();
      })
      .catch(function () {
        kutu.placeholder = "Arama dizini yüklenemedi";
      });
  }

  kutu.addEventListener("input", ara);
  baslat();
})();
