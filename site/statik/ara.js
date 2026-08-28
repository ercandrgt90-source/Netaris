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

  /* TURE GORE GRUPLAMA.
     -------------------
     Dizine haberler eklenince tek bir duz liste yetersiz kaldi:
     "Fed" aramasi 384 haberi ve 12 arastirmayi ayni yigin icinde
     donduruyordu ve okur arastirmalari goremiyordu.

     Sira bilincli: ARASTIRMA once. Haber "ne oldu"yu, arastirma "ne
     anlama geldigini" anlatiyor ve arayan kisi cogunlukla ikincisini
     ariyor -- ustelik haber sayisi arastirmayi her zaman ezer, yani
     tarihe gore siralanan tek listede arastirma hic gorunmezdi. */
  var GRUPLAR = [
    { tur: "arastirma", ad: "Araştırmalar" },
    { tur: "haber", ad: "Haberler" },
    /* SAYFALAR EN SONDA.

       Dizine 2026-08-28'de eklendiler; oncesinde metodoloji, gizlilik
       ve kunye sayfalari HIC ARANAMIYORDU.

       Sona konmalari bilincli: "bilanco" arayan okur 233 analiz
       istiyor, metodoloji sayfasini degil. Ama "metodoloji" ya da
       "gizlilik" arandiginda toplam sonuc zaten az oluyor ve sayfa
       hemen goruluyor. Grup basligi da onu bulunabilir kiliyor. */
    { tur: "sayfa", ad: "Sayfalar" }
  ];

  function kart(k) {
    var rozetler = "";
    if (k.k) {
      rozetler += '<span class="rozet rozet-vurgu">' + kacis(k.k) + "</span>";
    }
    if (k.kod) {
      rozetler += '<span class="rozet rozet-kod">' + kacis(k.kod) + "</span>";
    }
    /* Okuma suresi yalnizca ARASTIRMADA var. Haberde uydurmak yerine
       hic basmiyoruz -- olculmemis bir sayiyi olcum gibi gostermek,
       bu depoda birkac kez reddedilmis bir sey. */
    var kunye = '<span class="kart-kunye"><span>' + kacis(k.t || "") + "</span>";
    if (k.d) {
      kunye += '<span class="ayrac">·</span><span>' + k.d + " dk okuma</span>";
    }
    kunye += "</span>";
    return (
      '<li><a class="ara-kart" href="' + k.y + '">' +
      '<span class="ust-satir">' + rozetler + "</span>" +
      '<span class="ara-baslik">' + kacis(k.b) + "</span>" +
      '<span class="ara-ozet">' + kacis(k.o || "") + "</span>" +
      kunye + "</a></li>"
    );
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

    var parcalar = [];
    var kalan = kayitlar.slice();
    for (var g = 0; g < GRUPLAR.length; g++) {
      var grup = GRUPLAR[g];
      var uyanlar = [];
      var digerleri = [];
      for (var i = 0; i < kalan.length; i++) {
        if ((kalan[i].tur || "arastirma") === grup.tur) uyanlar.push(kalan[i]);
        else digerleri.push(kalan[i]);
      }
      kalan = digerleri;
      if (!uyanlar.length) continue;
      parcalar.push(
        '<li class="ara-grup"><h2>' + grup.ad +
        ' <span class="ara-grup-say">' + uyanlar.length + "</span></h2></li>"
      );
      for (var j = 0; j < uyanlar.length; j++) parcalar.push(kart(uyanlar[j]));
    }
    /* Bilinmeyen tur gelirse KAYBOLMASIN: dizine yeni bir icerik turu
       eklenip burasi guncellenmezse, o kayitlar sessizce gorunmez
       olurdu. Sessiz kayip, gorunur bir "Diğer" basligindan kotudur. */
    if (kalan.length) {
      parcalar.push('<li class="ara-grup"><h2>Diğer <span class="ara-grup-say">' +
        kalan.length + "</span></h2></li>");
      for (var m = 0; m < kalan.length; m++) parcalar.push(kart(kalan[m]));
    }
    sonuc.innerHTML = parcalar.join("");
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
      return parcalar.every(function (p) { return k._a.indexOf(p) !== -1; });
    });
    ciz(bulunan, sorgu);
  }

  function baslat() {
    fetch("/arama.json", { cache: "no-cache" })
      .then(function (y) { return y.json(); })
      .then(function (veri) {
        /* ESLESME METNI BURADA KURULUYOR.
           -----------------------------
           Once her kayit hazir bir `a` alani tasiyordu ve haberler
           dizine eklenince dosya 903 KB'a cikti -- o alanin neredeyse
           tamami ayni kaydin diger alanlarinin kopyasiydi.

           `katla` ile Python tarafindaki `_SLUG_ESLEME` BIREBIR
           AYNI, yani metni burada uretmek ayni sonucu veriyor.
           Ikisinin ayrisma riski gercek ve `test_arama.py` bunu
           siniyor: ayrisirsa "hurmuz" yazan okur "Hürmüz"u bulamaz
           ve HICBIR HATA GORUNMEZ.

           Bir kez, dizin yuklenirken hesaplaniyor -- her tus
           vurusunda degil. */
        DIZIN = veri;
        for (var i = 0; i < DIZIN.length; i++) {
          var k = DIZIN[i];
          k._a = katla(
            (k.b || "") + " " + (k.o || "") + " " + (k.k || "") + " " +
            (k.s || "") + " " + (k.kod || "") + " " + (k.kr || ""));
        }
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
