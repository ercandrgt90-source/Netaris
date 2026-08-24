/* Uyelik arayuzu -- giris, kayit ve yazar paneli.
 *
 * Panel icerigi SUNUCUDA URETILMEZ. `cikti/` altindaki her dosya herkese
 * acik; uyeye ozel veri statik HTML'e yazilamaz. Bu yuzden panel bos bir
 * kabuk olarak yayimlaniyor ve icerigi oturum cerezliyle API'den geliyor.
 *
 * Cerez HttpOnly -- bu dosya oturum jetonunu OKUYAMAZ. Oturum var mi
 * sorusunun cevabi yalnizca /api/ben cagrisindan geliyor.
 */
(function () {
  "use strict";

  var $ = function (s, k) { return (k || document).querySelector(s); };
  var $$ = function (s, k) { return [].slice.call((k || document).querySelectorAll(s)); };

  function istek(yol, secenek) {
    var s = secenek || {};
    return fetch(yol, {
      method: s.method || "GET",
      headers: s.govde ? { "content-type": "application/json" } : {},
      body: s.govde ? JSON.stringify(s.govde) : undefined,
      credentials: "same-origin",
      cache: "no-store",
    }).then(function (y) {
      return y.json().catch(function () { return {}; }).then(function (v) {
        return { tamam: y.ok, durum: y.status, veri: v };
      });
    });
  }

  function hataGoster(kutu, mesaj) {
    if (!kutu) return;
    kutu.textContent = mesaj || "";
    kutu.hidden = !mesaj;
  }

  function dugmeKilit(form, kilitli, metin) {
    $$("button", form).forEach(function (d) { d.disabled = kilitli; });
    var b = $("button[type=submit]", form);
    if (b && metin) b.textContent = metin;
  }

  /* ------------------------------------------------------------- giris */

  var girisForm = $('[data-form="giris"]');
  if (girisForm) {
    /* Dogrulama baglantisindan donen durum mesajlari */
    var durumKutu = $("[data-durum-kutusu]");
    var durum = new URLSearchParams(location.search).get("durum");
    var mesajlar = {
      dogrulandi: "Hesabınız doğrulandı. Şimdi giriş yapabilirsiniz.",
      "dogrulama-gecersiz":
        "Doğrulama bağlantısı geçersiz ya da süresi dolmuş. Yeni bağlantı için yönetime yazın.",
      cikildi: "Oturumunuz kapatıldı.",
    };
    if (durum && mesajlar[durum] && durumKutu) {
      durumKutu.textContent = mesajlar[durum];
      durumKutu.hidden = false;
      durumKutu.className =
        "uyelik-mesaj " + (durum === "dogrulandi" ? "iyi" : "uyari");
    }

    girisForm.addEventListener("submit", function (o) {
      o.preventDefault();
      var h = $("[data-hata]", girisForm);
      hataGoster(h, "");
      dugmeKilit(girisForm, true, "Giriş yapılıyor…");
      istek("/api/giris", {
        method: "POST",
        govde: {
          eposta: girisForm.eposta.value.trim(),
          parola: girisForm.parola.value,
        },
      }).then(function (y) {
        /* DONUS ADRESI KORUNUYOR. Once sabit "/panel/" yaziliydi ve
           okurun niyeti kayboluyordu: haber sayfasindan "Senaryo yaz"
           ile gelen kisi giris yaptiktan sonra BOS BIR PANELE
           dusuyordu. Hicbir hata gorunmuyordu -- yalnizca hangi
           habere yazdigi kayboluyordu. */
        if (y.tamam) {
          location.href = (window.NetarisDonus
            ? window.NetarisDonus.hedef() : "/panel/");
          return;
        }
        hataGoster(h, y.veri.hata || "Giriş yapılamadı.");
        dugmeKilit(girisForm, false, "Giriş yap");
      }).catch(function () {
        hataGoster(h, "Bağlantı kurulamadı.");
        dugmeKilit(girisForm, false, "Giriş yap");
      });
    });
  }

  /* ------------------------------------------------------------- kayit */

  var kayitForm = $('[data-form="kayit"]');
  if (kayitForm) {
    kayitForm.addEventListener("submit", function (o) {
      o.preventDefault();
      var h = $("[data-hata]", kayitForm);
      hataGoster(h, "");
      if (kayitForm.parola.value.length < 10) {
        hataGoster(h, "Parola en az 10 karakter olmalı.");
        return;
      }
      dugmeKilit(kayitForm, true, "Oluşturuluyor…");
      istek("/api/kayit", {
        method: "POST",
        govde: {
          ad: kayitForm.ad.value.trim(),
          eposta: kayitForm.eposta.value.trim(),
          parola: kayitForm.parola.value,
        },
      }).then(function (y) {
        if (y.tamam) {
          kayitForm.innerHTML =
            '<p class="uyelik-mesaj iyi">' + (y.veri.mesaj || "Kaydınız alındı.") +
            '</p><p><a class="dugme" href="/giris/">Giriş sayfasına dön</a></p>';
          return;
        }
        hataGoster(h, y.veri.hata || "Kayıt yapılamadı.");
        dugmeKilit(kayitForm, false, "Hesap oluştur");
      }).catch(function () {
        hataGoster(h, "Bağlantı kurulamadı.");
        dugmeKilit(kayitForm, false, "Hesap oluştur");
      });
    });
  }

  /* ------------------------------------------------------------- panel */

  var panel = $("[data-panel]");
  if (!panel) return;

  var girisGerek = $("[data-giris-gerek]");
  var yaziForm = $('[data-form="yazi"]');
  var listeKutu = $("[data-liste]");
  var yonetimKutu = $("[data-yonetim]");

  /* Uye durumlari YAZI durumlarindan AYRI sozlukte: ikisi farkli
     alan ve ortak bir anahtar ("reddedildi" gibi) ikisinde baska
     anlama gelir. Tek sozlukte birlestirmek, birinin digerini
     sessizce ezmesi demekti. */
  var UYE_DURUM = {
    beklemede: "E-posta doğrulanmadı",
    etkin: "Etkin",
    askida: "Askıda",
  };

  var DURUM_ADI = {
    taslak: "Taslak",
    incelemede: "İncelemede",
    onaylandi: "Onaylandı, yayın sırasında",
    reddedildi: "Yayımlanmadı",
    yayimlandi: "Yayımlandı",
  };

  function kacir(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (k) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[k];
    });
  }

  function tarih(d) {
    if (!d) return "—";
    var t = new Date(d);
    return isNaN(t) ? "—" : t.toLocaleDateString("tr-TR", {
      day: "numeric", month: "long", year: "numeric",
    });
  }

  function sekmeGec(ad) {
    $$("[data-bolum]").forEach(function (b) { b.hidden = b.dataset.bolum !== ad; });
    $$("[data-sekme]").forEach(function (d) {
      d.classList.toggle("etkin", d.dataset.sekme === ad);
    });
  }

  $$("[data-sekme]").forEach(function (d) {
    d.addEventListener("click", function () { sekmeGec(d.dataset.sekme); });
  });

  /* --- HESABIM: profil bilgileri ------------------------------------
     Ad ve soyad AYRI tutuluyor. Tek alanda toplandiginda kunye
     disinda hicbir yerde kullanilamiyordu; ayrildiginda hem kunye
     eskisi gibi calisiyor hem de siralama ve hitap mumkun oluyor.

     Form `/api/ben` yanitiyla dolduruluyor -- ayri bir istek YOK.
     Ikinci bir istek olsaydi form bir an bos gorunur, kullanici o
     arada yazmaya baslarsa yazdigi silinirdi. */
  function tamAd(u) {
    return ((u.ad || "") + " " + (u.soyad || "")).replace(/\s+/g, " ").trim();
  }

  /* KARSILAMA KARTI.
     Baslik alani "Panel" yerine kisinin ADI oluyor; altinda UNVANI.
     Unvan bos ise e-posta yaziliyor -- kart bos bir satirla degil,
     her zaman bir seyle acilmali.

     Avatar yoksa BAS HARF dairesi. `_imza.html` icindeki "vesikalik
     yok" kurali bununla CELISMIYOR: o kural KURUM imzasi icin --
     var olmayan bir insanin uydurma fotografi olmaz. Burada gorseli
     koyan, gercek bir uye ve kendi fotografi. */
  function kartiDoldur(u) {
    var ad = tamAd(u) || "Panel";
    var b = $("[data-tam-ad]");
    if (b) b.textContent = ad;
    var kim = $("[data-kim]");
    if (kim) kim.textContent = u.unvan ? u.unvan : u.eposta;
    var av = $("[data-avatar]");
    /* Avatar varsa bas harf BASILMIYOR: ikisi ust uste binerdi.
       Bas harfte `tr` yereli veriliyor -- yoksa "istanbul" -> "I"
       oluyor, "İ" degil. */
    if (av) av.textContent = u.avatar ? "" : ad.slice(0, 1).toLocaleUpperCase("tr");
  }

  /* --- AVATAR -------------------------------------------------------
     Gorsel TARAYICIDA yeniden uretiliyor ve asil sebebi boyut degil
     GIZLILIK: telefon fotografi EXIF icinde GPS KOORDINATI tasiyor.
     Canvas'a cizip yeniden kodlamak butun ust veriyi dusuruyor --
     yuklenen sey, kullanicinin evinin konumunu tasimayan yeni bir
     dosya oluyor.

     Sunucudaki 64 KB tavani bu adimin ATLANAMAMASINI sagliyor: ham
     telefon fotografi zaten sigmiyor.

     KARE KIRPMA merkezden: avatar daire icinde gosteriliyor ve
     orani bozmak yerine fazlasi kesiliyor. */
  var AVATAR_BOY = 256;

  function avatarKucult(dosya) {
    return new Promise(function (coz, at) {
      var okuyucu = new FileReader();
      okuyucu.onerror = function () { at(new Error("okunamadi")); };
      okuyucu.onload = function () {
        var im = new Image();
        im.onerror = function () { at(new Error("gorsel degil")); };
        im.onload = function () {
          var k = Math.min(im.width, im.height);
          if (!k) { at(new Error("bos gorsel")); return; }
          var t = document.createElement("canvas");
          t.width = t.height = AVATAR_BOY;
          var c = t.getContext("2d");
          /* Saydam PNG'ler siyah zemine dusmesin: JPEG saydamlik
             tasimiyor ve doldurmadan cizilirse saydam pikseller
             SIYAH cikiyor. */
          c.fillStyle = "#ffffff";
          c.fillRect(0, 0, AVATAR_BOY, AVATAR_BOY);
          c.drawImage(im, (im.width - k) / 2, (im.height - k) / 2, k, k,
                      0, 0, AVATAR_BOY, AVATAR_BOY);
          coz(t.toDataURL("image/jpeg", 0.82));
        };
        im.src = okuyucu.result;
      };
      okuyucu.readAsDataURL(dosya);
    });
  }

  function avatarGoster(veri) {
    var on = $("[data-avatar-onizleme]");
    var kartAv = $("[data-avatar]");
    var kaldir = $("[data-avatar-kaldir]");
    [on, kartAv].forEach(function (e) {
      if (!e) return;
      if (veri) {
        e.style.backgroundImage = 'url("' + veri + '")';
        e.classList.add("avatar-gorselli");
      } else {
        e.style.backgroundImage = "";
        e.classList.remove("avatar-gorselli");
      }
    });
    if (kaldir) kaldir.hidden = !veri;
  }

  function avatarGonder(veri, durumMetni) {
    var durum = $("[data-profil-durum]");
    if (durum) { durum.textContent = durumMetni; durum.className = "panel-durum"; }
    return istek("/api/avatar", { method: "POST", govde: { avatar: veri } })
      .then(function (y) {
        if (!y.tamam) {
          if (durum) {
            durum.textContent = (y.veri && y.veri.hata) || "Görsel kaydedilemedi.";
            durum.className = "panel-durum panel-durum-hata";
          }
          return false;
        }
        /* SUNUCUNUN DONDURDUGU deger gosteriliyor -- sakladigimizdan
           farkli bir sey gostermek sessiz bir yalan olurdu. */
        avatarGoster(y.veri.avatar);
        if (durum) {
          durum.textContent = veri ? "Fotoğraf kaydedildi." : "Fotoğraf kaldırıldı.";
          durum.className = "panel-durum panel-durum-tamam";
        }
        return true;
      });
  }

  var avatarGirdi = $("[data-avatar-girdi]");
  if (avatarGirdi) {
    avatarGirdi.addEventListener("change", function () {
      var d = avatarGirdi.files && avatarGirdi.files[0];
      if (!d) return;
      var durum = $("[data-profil-durum]");
      avatarKucult(d).then(function (veri) {
        return avatarGonder(veri, "Fotoğraf yükleniyor…");
      }).catch(function () {
        if (durum) {
          durum.textContent = "Görsel okunamadı. JPEG ya da PNG seçin.";
          durum.className = "panel-durum panel-durum-hata";
        }
      }).then(function () {
        /* Ayni dosya tekrar secilebilsin: `change` ayni degerde
           TETIKLENMIYOR ve kullanici ikinci denemesinde hicbir sey
           olmadigini gorurdu. */
        avatarGirdi.value = "";
      });
    });
  }

  var avatarKaldirDugme = $("[data-avatar-kaldir]");
  if (avatarKaldirDugme) {
    avatarKaldirDugme.addEventListener("click", function () {
      avatarGonder("", "Kaldırılıyor…");
    });
  }

  var profilForm = $("[data-profil-form]");

  function profilDoldur(u) {
    if (!profilForm) return;
    profilForm.ad.value = u.ad || "";
    profilForm.soyad.value = u.soyad || "";
    profilForm.unvan.value = u.unvan || "";
    profilForm.hakkinda.value = u.hakkinda || "";
    hakkindaSay();
    var e = $("[data-profil-eposta]");
    var r = $("[data-profil-rol]");
    var k = $("[data-profil-kayit]");
    if (e) e.textContent = u.eposta || "—";
    if (r) r.textContent = u.rol === "yonetici" ? "Yönetici" : "Yazar";
    if (k) k.textContent = tarih(u.kayit_ani);
    avatarGoster(u.avatar || "");
  }

  function hakkindaSay() {
    var s = $("[data-hakkinda-sayac]");
    if (s && profilForm) s.textContent = String(profilForm.hakkinda.value.length);
  }

  if (profilForm) {
    profilForm.hakkinda.addEventListener("input", hakkindaSay);

    profilForm.addEventListener("submit", function (o) {
      o.preventDefault();
      var durum = $("[data-profil-durum]");
      var dugme = $("[data-profil-kaydet]");
      /* Cift gonderim kapatiliyor: yavas baglantida iki kez
         tiklamak iki UPDATE demek ve ikincisi ilkini ezerdi. */
      if (dugme) dugme.disabled = true;
      if (durum) { durum.textContent = "Kaydediliyor…"; durum.className = "panel-durum"; }

      istek("/api/profil", {
        method: "POST",
        govde: {
          ad: profilForm.ad.value,
          soyad: profilForm.soyad.value,
          unvan: profilForm.unvan.value,
          hakkinda: profilForm.hakkinda.value,
        },
      }).then(function (y) {
        if (dugme) dugme.disabled = false;
        if (!y.tamam) {
          if (durum) {
            durum.textContent = (y.veri && y.veri.hata) || "Kaydedilemedi.";
            durum.className = "panel-durum panel-durum-hata";
          }
          return;
        }
        /* SUNUCUNUN DONDURDUGU degerle yeniden dolduruluyor.
           Sunucu tek satirlik alanlardan satir sonu ve gorunmez
           karakterleri temizliyor; ekranda kullanicinin yazdigi
           kalsaydi, sakladigimizdan farkli bir sey gosterirdik. */
        profilDoldur(y.veri.uye);
        kartiDoldur(y.veri.uye);
        if (durum) {
          durum.textContent = "Kaydedildi.";
          durum.className = "panel-durum panel-durum-tamam";
        }
      }).catch(function () {
        if (dugme) dugme.disabled = false;
        if (durum) {
          durum.textContent = "Bağlantı kurulamadı.";
          durum.className = "panel-durum panel-durum-hata";
        }
      });
    });
  }

  /* --- BEGENDIKLERIM ve PANEL SAYIMLARI ------------------------------
     Tek istek: liste ve uc sayi ayni cagriyla geliyor. Uc ayri istek
     panel acilisini uc kez beklemek olurdu.

     Sayim seridi `hidden` basiliyor ve ancak GERCEK sayi gelince
     aciliyor. Sifir basip sonra duzeltmek, okura once yanlis bir sayi
     gostermek demekti. */
  function bicimSayi(n) {
    var t = String(Math.floor(Math.abs(Number(n) || 0))), c = "";
    for (var i = 0; i < t.length; i++) {
      if (i > 0 && (t.length - i) % 3 === 0) c += ".";
      c += t.charAt(i);
    }
    return c;
  }

  /* --- BEGENDIKLERIM: akis bicimi ---------------------------------
     Once yalnizca baslik ve ham tarih ("2026-08-24") basiliyordu.
     Simdi her satir bir kart: bolum rozeti, baslik, begenme tarihi ve
     ETKILESIM SATIRI.

     Etkilesim sayilari GERCEK: `/api/sayaclar` yol basina
     goruntulenme ve begeni donuyor -- zaten var olan bir uc, tek
     cagriyla butun liste icin.

     Sayilar GELMEDEN BASILMIYOR. Sifir basip sonra duzeltmek, okura
     once yanlis bir sayi gostermek olurdu; ayni kural karsilama
     kartindaki seritte de gecerli. */
  var BOLUM_ADI = {
    haber: "Haber", analiz: "Araştırma", senaryo: "Senaryo",
    varlik: "Varlık", olay: "Olay", makro: "Makro", teknik: "Teknik",
    arastirmalar: "Araştırma", bilancolar: "Bilanço",
  };

  function bolumAdi(yol) {
    var p = String(yol || "").split("/").filter(Boolean)[0];
    return BOLUM_ADI[p] || "Sayfa";
  }

  function begeniCiz(kutu, liste) {
    /* Metin `textContent` ile yaziliyor, HTML birlestirmeyle DEGIL:
       baslik veritabanindan geliyor ve orada ne oldugunu varsaymak
       XSS acar. */
    kutu.innerHTML = "";
    liste.forEach(function (o) {
      var k = document.createElement("article");
      k.className = "panel-satir-kart begeni-kart";
      k.dataset.yol = o.yol;

      var ust = document.createElement("div");
      ust.className = "panel-satir-ust";
      var rozet = document.createElement("span");
      rozet.className = "rozet";
      rozet.textContent = bolumAdi(o.yol);
      ust.appendChild(rozet);
      if (o.an) {
        var t = document.createElement("span");
        t.className = "kart-kunye";
        t.textContent = tarih(o.an) + " tarihinde beğendiniz";
        ust.appendChild(t);
      }
      k.appendChild(ust);

      var h = document.createElement("h3");
      var a = document.createElement("a");
      a.href = o.yol;
      a.textContent = o.baslik || o.yol;
      h.appendChild(a);
      k.appendChild(h);

      var alt = document.createElement("div");
      alt.className = "begeni-alt";
      /* Sayi kutulari BOS ve gizli basliyor; `sayaclariDoldur`
         gercek deger gelince aciyor. */
      var g = document.createElement("span");
      g.className = "begeni-sayi";
      g.dataset.sayacG = "1";
      g.hidden = true;
      var b = document.createElement("span");
      b.className = "begeni-sayi";
      b.dataset.sayacB = "1";
      b.hidden = true;
      var kaldir = document.createElement("button");
      kaldir.type = "button";
      kaldir.className = "dugme dugme-sade begeni-kaldir";
      kaldir.dataset.begeniKaldir = o.yol;
      kaldir.textContent = "Beğeniyi kaldır";
      alt.appendChild(g);
      alt.appendChild(b);
      alt.appendChild(kaldir);
      k.appendChild(alt);

      kutu.appendChild(k);
    });
    sayaclariDoldur(kutu, liste.map(function (o) { return o.yol; }));
  }

  function sayaclariDoldur(kutu, yollar) {
    if (!yollar.length) return;
    istek("/api/sayaclar", { method: "POST", govde: { yollar: yollar } })
      .then(function (y) {
        if (!y.tamam || !y.veri || !y.veri.sayaclar) return;
        var s = y.veri.sayaclar;
        $$("[data-yol]", kutu).forEach(function (k) {
          var v = s[k.dataset.yol];
          if (!v) return;
          var g = $("[data-sayac-g]", k), b = $("[data-sayac-b]", k);
          if (g) { g.textContent = bicimSayi(v.g) + " görüntülenme"; g.hidden = false; }
          /* SIFIR BEGENI GOSTERILMIYOR: kullanici bu sayfayi zaten
             begendi, yani sayi en az 1 olmali. Sifir gorunuyorsa
             sayac hentiz islememis demektir ve "0 beğeni" yazmak
             yanlis bilgi olurdu. */
          if (b && v.b > 0) {
            b.textContent = bicimSayi(v.b) + " beğeni";
            b.hidden = false;
          }
        });
      })
      .catch(function () { /* sayac yoksa kart yine calisiyor */ });
  }

  /* BEGENIYI KALDIRMA -- olay DELEGASYONU ile.
     Her karta ayri dinleyici baglamak, liste her yenilendiginde
     eskilerini birakirdi. Tek dinleyici kapsayicida duruyor. */
  document.addEventListener("click", function (o) {
    var d = o.target.closest && o.target.closest("[data-begeni-kaldir]");
    if (!d) return;
    var yol = d.dataset.begeniKaldir;
    d.disabled = true;
    istek("/api/begeni", { method: "POST", govde: { yol: yol } })
      .then(function (y) {
        if (!y.tamam) { d.disabled = false; return; }
        var kart = d.closest("[data-yol]");
        if (kart) kart.remove();
        /* Serit sayisi da dusuyor -- kart gitti ama sayi kalsaydi
           panel kendi icinde tutarsiz olurdu. */
        var b = $("[data-sayim-begeni]");
        if (b) {
          var n = parseInt(b.textContent.replace(/[^0-9]/g, ""), 10);
          if (!isNaN(n) && n > 0) b.textContent = bicimSayi(n - 1);
        }
        var kutu = $("[data-begeni-liste]");
        if (kutu && !kutu.querySelector("[data-yol]")) {
          kutu.innerHTML = '<p class="uyelik-alt">Beğeni listeniz boş.</p>';
        }
      })
      .catch(function () { d.disabled = false; });
  });

  function begenileriYukle() {
    var kutu = $("[data-begeni-liste]");
    fetch("/api/begenilerim", { credentials: "same-origin" })
      .then(function (c) { return c.ok ? c.json() : null; })
      .then(function (v) {
        if (!v) return;
        var s = v.sayim || {};
        var y = $("[data-sayim-yazi]"), sn = $("[data-sayim-senaryo]"),
            b = $("[data-sayim-begeni]"), o = $("[data-sayim-oy]"),
            serit = $("[data-panel-sayim]");
        if (y) y.textContent = bicimSayi(s.yazi);
        if (sn) sn.textContent = bicimSayi(s.senaryo);
        if (b) b.textContent = bicimSayi(s.begeni);
        /* `oy` alani eski bir sunucu surumunden gelmeyebilir. `|| 0`
           yerine ACIKCA kontrol: `bicimSayi(undefined)` "NaN" basar
           ve okur panelde "NaN oy" gorurdu. */
        if (o) o.textContent = bicimSayi(typeof s.oy === "number" ? s.oy : 0);
        if (serit) serit.hidden = false;

        if (!kutu) return;
        var liste = v.begeniler || [];
        if (!liste.length) {
          kutu.innerHTML = '<p class="uyelik-alt">Henüz bir sayfayı ' +
            'beğenmediniz. Haber ve araştırma sayfalarındaki kalp ' +
            'düğmesiyle beğenebilirsiniz.</p>';
          return;
        }
        begeniCiz(kutu, liste);
      })
      .catch(function () {});
  }

  /* --- yazi listesi --- */

  function listeCiz(yazilar) {
    if (!yazilar.length) {
      listeKutu.innerHTML =
        '<p class="uyelik-alt">Henüz yazınız yok. “Yeni yazı” ile başlayın.</p>';
      return;
    }
    listeKutu.innerHTML = yazilar.map(function (y) {
      var duzenlenebilir = y.durum === "taslak" || y.durum === "reddedildi";
      return (
        '<article class="panel-satir-kart">' +
          '<div class="panel-satir-ust">' +
            '<span class="rozet rozet-durum durum-' + kacir(y.durum) + '">' +
              kacir(DURUM_ADI[y.durum] || y.durum) + '</span>' +
            '<span class="rozet">' + kacir(y.kategori) + '</span>' +
            '<span class="kart-kunye">' + tarih(y.guncelleme) + '</span>' +
          '</div>' +
          '<h3>' + kacir(y.baslik) + '</h3>' +
          (y.ozet ? '<p class="kart-ozet">' + kacir(y.ozet) + '</p>' : '') +
          (y.ret_nedeni
            ? '<p class="uyelik-mesaj uyari">Editör notu: ' + kacir(y.ret_nedeni) + '</p>'
            : '') +
          '<div class="panel-eylem">' +
            (duzenlenebilir
              ? '<button class="dugme" type="button" data-duzenle="' + y.id + '">Düzenle</button>' +
                '<button class="dugme dugme-sade" type="button" data-sil="' + y.id + '">Sil</button>'
              : '') +
            (y.durum === "yayimlandi" && y.slug
              ? '<a class="dugme" href="/analiz/' + kacir(y.slug) + '/">Yayındaki hâli</a>'
              : '') +
          '</div>' +
        '</article>'
      );
    }).join("");

    $$("[data-duzenle]", listeKutu).forEach(function (d) {
      d.addEventListener("click", function () { yaziAc(d.dataset.duzenle); });
    });
    $$("[data-sil]", listeKutu).forEach(function (d) {
      d.addEventListener("click", function () {
        if (!confirm("Bu yazı silinsin mi? Geri alınamaz.")) return;
        istek("/api/yazi/" + d.dataset.sil, { method: "DELETE" }).then(listeYukle);
      });
    });
  }

  function listeYukle() {
    return istek("/api/yazi").then(function (y) {
      if (y.tamam) listeCiz(y.veri.yazilar || []);
    });
  }

  /* --- yazi formu --- */

  var sayac = $("[data-sayac]");
  if (yaziForm) {
    yaziForm.govde.addEventListener("input", function () {
      if (sayac) sayac.textContent = yaziForm.govde.value.trim().length;
    });
  }

  function formTemizle() {
    yaziForm.reset();
    yaziForm.id.value = "";
    if (sayac) sayac.textContent = "0";
    hataGoster($("[data-hata]", yaziForm), "");
  }

  function yaziAc(id) {
    istek("/api/yazi/" + id).then(function (y) {
      if (!y.tamam) return;
      var v = y.veri.yazi;
      yaziForm.id.value = v.id;
      yaziForm.baslik.value = v.baslik || "";
      yaziForm.ozet.value = v.ozet || "";
      yaziForm.govde.value = v.govde || "";
      yaziForm.kategori.value = v.kategori || "Analist Yorumu";
      if (sayac) sayac.textContent = (v.govde || "").length;
      $('[data-sekme="duzenle"]').hidden = false;
      sekmeGec("duzenle");
    });
  }

  var yeniDugme = $("[data-yeni]");
  if (yeniDugme) {
    yeniDugme.addEventListener("click", function () {
      formTemizle();
      $('[data-sekme="duzenle"]').hidden = false;
      sekmeGec("duzenle");
    });
  }

  /* Vazgec dugmeleri FORMA GORE secilir. Sayfada iki form var (yazi ve
     senaryo); `$("[data-vazgec]")` ilkini alip senaryo formundakini
     olusuz birakiyordu. */
  if (yaziForm) {
    var vazgec = $("[data-vazgec]", yaziForm);
    if (vazgec) {
      vazgec.addEventListener("click", function () {
        formTemizle();
        sekmeGec("yazilarim");
      });
    }
  }

  /* Hangi dugmeye basildigini submit oncesi yakaliyoruz: "taslak kaydet"
     ile "incelemeye gonder" ayni formu gonderiyor ama farkli sey yapiyor. */
  var gonderModu = false;
  $$("[data-kaydet], [data-gonder]", yaziForm || document).forEach(function (d) {
    d.addEventListener("click", function () {
      gonderModu = d.hasAttribute("data-gonder");
    });
  });

  if (yaziForm) {
    yaziForm.addEventListener("submit", function (o) {
      o.preventDefault();
      var h = $("[data-hata]", yaziForm);
      hataGoster(h, "");
      var govde = yaziForm.govde.value.trim();
      if (gonderModu && govde.length < 400) {
        hataGoster(h, "Gönderim için metin en az 400 karakter olmalı.");
        return;
      }
      if (gonderModu &&
          !confirm("Yazı incelemeye gönderilecek. Gönderdikten sonra " +
                   "düzenleyemezsiniz. Devam edilsin mi?")) {
        return;
      }
      dugmeKilit(yaziForm, true);
      istek("/api/yazi", {
        method: "POST",
        govde: {
          id: yaziForm.id.value ? Number(yaziForm.id.value) : null,
          baslik: yaziForm.baslik.value.trim(),
          ozet: yaziForm.ozet.value.trim(),
          govde: govde,
          kategori: yaziForm.kategori.value,
          gonder: gonderModu,
        },
      }).then(function (y) {
        dugmeKilit(yaziForm, false);
        if (!y.tamam) { hataGoster(h, y.veri.hata || "Kaydedilemedi."); return; }
        formTemizle();
        sekmeGec("yazilarim");
        listeYukle();
      }).catch(function () {
        dugmeKilit(yaziForm, false);
        hataGoster(h, "Bağlantı kurulamadı.");
      });
    });
  }

  /* --- senaryolar --- */

  var senForm = $('[data-form="senaryo"]');
  var senListeKutu = $("[data-senaryo-liste]");

  function senaryoTemizle() {
    if (!senForm) return;
    senForm.reset();
    senForm.id.value = "";
    hataGoster($("[data-hata]", senForm), "");
  }

  /* CAPA TARAYICIDA DA SAKLANIYOR -- e-posta dogrulamasi araya
     giriyor.
     -------------------------------------------------------------
     Giris sonrasi donus adresi `donus.js` ile korunuyor, ama YENI
     UYE yolunda arada e-posta dogrulamasi var:

         /panel/?senaryo=...  ->  /giris/  ->  kayit
           ->  e-posta  ->  /giris/?durum=dogrulandi  ->  /panel/

     O son adimda adres worker'dan geliyor ve capayi TASIYAMIYOR --
     dogrulama baglantisi e-postanin icinde, sorgu ekleyecek yer yok.
     Sonuc: yeni uye -- yani buyume icin en onemli kisi -- yine bos
     panele dusuyordu.

     Capa ilk gorulduğunde saklaniyor, panelde adres bossa oradan
     okunuyor.

     SURE SINIRI VAR ve gerekli: eski bir capa gunler sonra devreye
     girerse okurun senaryosu ALAKASIZ bir habere baglanir. Iki saat,
     e-posta dogrulamasi icin fazlasiyla yeterli.

     Depolama try/catch icinde: gizli sekmede ve depolamayi engelleyen
     tarayicilarda `sessionStorage` erisimi HATA FIRLATIYOR ve
     yakalanmazsa butun panel betigi duserdi. */
  var CAPA_ANAHTAR = "netaris-capa";
  var CAPA_OMUR = 2 * 60 * 60 * 1000;   // iki saat

  function capaSakla(capa, baslik) {
    try {
      sessionStorage.setItem(CAPA_ANAHTAR, JSON.stringify(
        { capa: capa, baslik: baslik, an: Date.now() }));
    } catch (e) { /* depolama yoksa adres zaten calisiyor */ }
  }

  function capaOku() {
    try {
      var ham = sessionStorage.getItem(CAPA_ANAHTAR);
      if (!ham) return null;
      var v = JSON.parse(ham);
      if (!v || !v.capa || Date.now() - v.an > CAPA_OMUR) {
        sessionStorage.removeItem(CAPA_ANAHTAR);
        return null;
      }
      return v;
    } catch (e) { return null; }
  }

  function capaSil() {
    try { sessionStorage.removeItem(CAPA_ANAHTAR); } catch (e) { /* yok */ }
  }

  /* Capa (hangi habere yazildigi) ADRESTEN geliyor:
     /panel/?senaryo=/haber/xxx/&baslik=...
     Haber sayfasindaki "Senaryo yaz" dugmesi boyle baglaniyor. Okur
     konuyu yeniden secmek ya da yazmak zorunda kalmiyor. */
  function capaKur() {
    if (!senForm) return;
    var p = new URLSearchParams(location.search);
    var capa = p.get("senaryo") || "";
    var baslik = p.get("baslik") || "";
    if (capa) {
      capaSakla(capa, baslik);
    } else {
      /* Adreste yoksa saklanandan devam: e-posta dogrulamasindan
         donen okur capasini kaybetmiyor. */
      var saklanan = capaOku();
      if (saklanan) {
        capa = saklanan.capa;
        baslik = saklanan.baslik || "";
      }
    }
    var not = $("[data-capa-not]");
    if (capa) {
      senForm.capa.value = capa;
      senForm.capa_baslik.value = baslik;
      if (not) {
        $("[data-capa-baslik]", not).textContent = baslik || capa;
        not.hidden = false;
      }
    } else if (not) {
      not.hidden = true;
    }
    return capa;
  }


  /* PAYLASIM DUGMELERI -- YAZARIN KENDI PANELINDE.
     ---------------------------------------------
     Paylasim blogu senaryonun HERKESE ACIK sayfasinda vardi ama
     panelde YOKTU. Yazar senaryosunu yaziyor, gonderiyor, yayimlaniyor
     ve hicbir sey ona paylasmasini soylemiyordu.

     Buyume halkasinin ilk adimi tam burasi: senaryoyu YAZAN kisi
     paylasmazsa zincir hic baslamiyor.

     Metin URL DEGIL: her kanal kendi metnini aliyor ve metin
     kosul -> sonuc kalibini tasiyor. Ciplak adres paylasimi, okuyanin
     tiklamadan once ne oldugunu bilmemesi demek. */
  function paylasDugmeleri(s) {
    var adres = location.origin + "/senaryo/" + s.id + "/";
    var metin = s.kosul + " → " + s.sonuc;
    /* X siniri 280 ve adres ~23 sayiliyor; metin 200'e kirpiliyor.
       Ayni kural worker'daki `paylasBlok` icinde de var. */
    if (metin.length > 200) metin = metin.slice(0, 199).trim() + "…";
    var m = encodeURIComponent(metin);
    var a = encodeURIComponent(adres);
    var kanallar = [
      ["X", "https://x.com/intent/post?text=" + m + "&url=" + a],
      ["LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url=" + a],
      ["WhatsApp", "https://wa.me/?text=" + encodeURIComponent(metin + " " + adres)],
      ["Telegram", "https://t.me/share/url?url=" + a + "&text=" + m],
    ];
    return '<span class="panel-paylas">' +
      '<span class="panel-paylas-etiket">Paylaş:</span>' +
      kanallar.map(function (k) {
        return '<a class="panel-paylas-baglanti" href="' + k[1] +
               '" target="_blank" rel="noopener noreferrer">' + k[0] + '</a>';
      }).join("") + '</span>';
  }

  /* --- SENARYO KARTI: ufuk geri sayimi ve GERCEK oy ----------------
     Tasarim taslaginda kartta "%56 gosterilme, 16 etkilesim" vardi.
     Gosterim OLCULMUYOR; olculmeyen bir orani basmak, sitenin
     "hicbir sey uydurulmaz" iddiasini kendi panelimizde bozardi.
     Yerine gercekten sayilan iki sey konuyor: kalan gun ve oy. */

  function kalanGun(s) {
    if (!s.ufuk_biter) return null;
    var biter = new Date(s.ufuk_biter);
    if (isNaN(biter)) return null;
    return Math.ceil((biter - Date.now()) / 86400000);
  }

  function ufukRozeti(s) {
    /* Sonuclanmis senaryoda geri sayim ANLAMSIZ -- ufuk zaten doldu
       ve kart sonucu gosteriyor. */
    if (s.sonuclanma || s.durum !== "yayimlandi") return "";
    var g = kalanGun(s);
    if (g === null) return "";
    if (g < 0) return '<span class="rozet rozet-ufuk">ufku doldu</span>';
    if (g === 0) return '<span class="rozet rozet-ufuk">bugün doluyor</span>';
    return '<span class="rozet rozet-ufuk">' + g + ' gün kaldı</span>';
  }

  function oyRozeti(s) {
    /* SIFIR OY ROZETI BASILMIYOR. "0 oy", okura bilgi vermeyen ama
       kartta yer kaplayan bir isarettir; yeni bir senaryoda ise
       yaziyi kotu gosterir. Oy geldiginde beliriyor. */
    var n = typeof s.oy === "number" ? s.oy : 0;
    if (!n) return "";
    return '<span class="rozet rozet-oy">' + bicimSayi(n) + ' oy</span>';
  }

  function ufukCubugu(s) {
    /* Ilerleme cubugu: olusma -> ufuk_biter arasinda nerede oldugu.
       Iki tarih de gerekli; biri yoksa cubuk HIC cizilmiyor --
       tahmini bir doluluk gostermek, olculmemis bir sey gostermektir. */
    if (s.sonuclanma || s.durum !== "yayimlandi") return "";
    if (!s.olusma || !s.ufuk_biter) return "";
    var bas = new Date(s.olusma), son = new Date(s.ufuk_biter);
    if (isNaN(bas) || isNaN(son) || son <= bas) return "";
    var oran = (Date.now() - bas) / (son - bas);
    oran = Math.max(0, Math.min(1, oran));
    var yuzde = Math.round(oran * 100);
    return (
      '<div class="ufuk-cubuk" role="img" aria-label="Ufkun ' + yuzde +
        ' yüzdesi geçti">' +
        '<span style="width:' + yuzde + '%"></span>' +
      '</div>'
    );
  }

  function senaryoCiz(liste) {
    if (!senListeKutu) return;
    if (!liste.length) {
      senListeKutu.innerHTML =
        '<p class="uyelik-alt">Henüz senaryonuz yok. Bir haber sayfasındaki ' +
        '“Senaryo yaz” düğmesiyle başlayabilirsiniz.</p>';
      return;
    }
    senListeKutu.innerHTML = liste.map(function (s) {
      /* Yalnizca taslak ve reddedilen duzenlenebilir. Yayimlanmis
         senaryo DEGISMEZ -- sonradan duzeltilebilen bir onerme
         denetlenemez, senaryo fikrinin tamami bu. */
      var acik = s.durum === "taslak" || s.durum === "reddedildi";
      return (
        '<article class="panel-satir-kart">' +
          '<div class="panel-satir-ust">' +
            '<span class="rozet rozet-durum durum-' + kacir(s.durum) + '">' +
              kacir(DURUM_ADI[s.durum] || s.durum) + '</span>' +
            '<span class="rozet">ufuk ' + kacir(s.ufuk) + '</span>' +
            ufukRozeti(s) +
            oyRozeti(s) +
            '<span class="kart-kunye">' + tarih(s.olusma) + '</span>' +
          '</div>' +
          ufukCubugu(s) +
          '<p class="senaryo-onerme">' +
            '<span class="senaryo-kosul">' + kacir(s.kosul) + '</span>' +
            '<span class="senaryo-ok" aria-hidden="true">→</span>' +
            '<span class="senaryo-sonuc">' + kacir(s.sonuc) + '</span>' +
          '</p>' +
          (s.capa_baslik
            ? '<p class="kart-ozet">Bağlı haber: ' + kacir(s.capa_baslik) + '</p>'
            : '') +
          (s.ret_nedeni
            ? '<p class="uyelik-mesaj uyari">Editör notu: ' +
              kacir(s.ret_nedeni) + '</p>'
            : '') +
          '<div class="panel-eylem">' +
            (acik
              ? '<button class="dugme dugme-sade" type="button" ' +
                'data-sen-sil="' + s.id + '">Sil</button>'
              : '') +
            /* YAYIMLANAN SENARYO KENDI SAYFASINA BAGLANIYOR.
               Once `s.capa`ya (habere) gidiyordu -- yani yazar kendi
               senaryosunun sayfasina ULASAMIYORDU. Paylasilacak adres
               de o sayfa; baglanti yanlis olunca paylasim zinciri
               bastan kopuyordu. */
            (s.durum === "yayimlandi"
              ? '<a class="dugme" href="/senaryo/' + s.id + '/">Senaryo sayfası</a>' +
                paylasDugmeleri(s)
              : '') +
          '</div>' +
        '</article>'
      );
    }).join("");

    $$("[data-sen-sil]", senListeKutu).forEach(function (d) {
      d.addEventListener("click", function () {
        if (!confirm("Bu senaryo silinsin mi? Geri alınamaz.")) return;
        istek("/api/senaryo/" + d.dataset.senSil, { method: "DELETE" })
          .then(senaryoYukle);
      });
    });
  }

  function senaryoYukle() {
    if (!senListeKutu) return Promise.resolve();
    return istek("/api/senaryo").then(function (y) {
      if (y.tamam) senaryoCiz(y.veri.senaryolar || []);
    });
  }

  var yeniSenaryo = $("[data-yeni-senaryo]");
  if (yeniSenaryo) {
    yeniSenaryo.addEventListener("click", function () {
      senaryoTemizle();
      capaKur();
      $('[data-sekme="senaryo"]').hidden = false;
      sekmeGec("senaryo");
    });
  }

  if (senForm) {
    var senVazgec = $("[data-vazgec]", senForm);
    if (senVazgec) {
      senVazgec.addEventListener("click", function () {
        senaryoTemizle();
        sekmeGec("senaryolarim");
      });
    }

    var senGonderModu = false;
    $$("[data-kaydet], [data-gonder]", senForm).forEach(function (d) {
      d.addEventListener("click", function () {
        senGonderModu = d.hasAttribute("data-gonder");
      });
    });

    senForm.addEventListener("submit", function (o) {
      o.preventDefault();
      var h = $("[data-hata]", senForm);
      hataGoster(h, "");
      var kosul = senForm.kosul.value.trim();
      var sonuc = senForm.sonuc.value.trim();
      if (kosul.length < 12 || sonuc.length < 12) {
        hataGoster(h, "Koşul ve sonuç en az 12 karakter olmalı.");
        return;
      }
      if (!senForm.capa.value) {
        hataGoster(h, "Senaryo bir habere bağlı olmalı. Bir haber " +
                      "sayfasındaki “Senaryo yaz” düğmesini kullanın.");
        return;
      }
      /* Olasilik beyani ISTEMCIDE de engelleniyor. Sunucu tarafi zaten
         moderasyondan geciriyor ama uyariyi yazma aninda vermek,
         reddedilen bir gonderimden iyi. */
      if (/%\s*\d|yüzde\s*\d|olasılık|ihtimalle/i.test(kosul + " " + sonuc)) {
        hataGoster(h, "Senaryoda olasılık belirtilmez. Koşulu ve beklenen " +
                      "sonucu yazın; “%60 ihtimalle” gibi ifadeler " +
                      "yayımlanmaz.");
        return;
      }
      if (senGonderModu &&
          !confirm("Senaryo incelemeye gönderilecek. Gönderdikten sonra " +
                   "düzenleyemezsiniz. Devam edilsin mi?")) {
        return;
      }
      dugmeKilit(senForm, true);
      istek("/api/senaryo", {
        method: "POST",
        govde: {
          id: senForm.id.value ? Number(senForm.id.value) : null,
          capa: senForm.capa.value,
          capa_baslik: senForm.capa_baslik.value,
          capa_tur: "haber",
          kosul: kosul,
          sonuc: sonuc,
          gerekce: senForm.gerekce.value.trim(),
          /* Alanlar SAVUNMALI okunuyor: sablon guncellenmeden betik
             dagitilirsa `senForm.curutme` tanimsiz olur ve `.value`
             butun gonderimi dusururdu. */
          curutme: senForm.curutme ? senForm.curutme.value.trim() : "",
          kaynaklar: senForm.kaynaklar ? senForm.kaynaklar.value.trim() : "",
          ufuk: senForm.ufuk.value,
          /* OLCULEBILIR TETIKLEYICI -- istege bagli.
             Bos gonderilirse worker tarafinda null yaziliyor ve
             senaryo ufku dolunca 'belirsiz' isaretleniyor. */
          olcut_kod: senForm.olcut_kod ? senForm.olcut_kod.value : "",
          olcut_yon: senForm.olcut_yon ? senForm.olcut_yon.value : "",
          olcut_esik: senForm.olcut_esik ? senForm.olcut_esik.value : "",
          gonder: senGonderModu,
        },
      }).then(function (y) {
        dugmeKilit(senForm, false);
        if (!y.tamam) { hataGoster(h, y.veri.hata || "Kaydedilemedi."); return; }
        /* SAKLANAN CAPA SILINIYOR. Yoksa ayni oturumda yazilan IKINCI
           senaryo, sessizce ilk haberin capasini alirdi -- ve okur bunu
           gonderdikten sonra fark ederdi. */
        capaSil();
        senaryoTemizle();
        sekmeGec("senaryolarim");
        senaryoYukle();
        /* GONDERIM SONRASI PAYLASIM DAVETI.
           Form temizlenip liste yenileniyordu ve akis orada bitiyordu.
           Yazar "gonderdim, simdi ne olacak" sorusuyla kaliyordu.

           Senaryo INCELEMEDE oldugu icin henuz paylasilamaz -- yayim
           beklenmeli. Mesaj bunu soyluyor ve paylasim adiminin
           GELECEGINI haber veriyor; boylece yazar listeye donup
           bekliyor, siteden ayrilmiyor. */
        if (senGonderModu && senListeKutu) {
          /* `mesajGoster` diye bir islev UYDURDUM ve yoktu; bu dosyada
             mesaj kutulari dogrudan DOM'a yaziliyor. Var oldugunu
             varsaydigim ismi once kontrol etmem gerekirdi. */
          var bilgi = document.createElement("p");
          bilgi.className = "uyelik-mesaj iyi";
          bilgi.textContent =
            "Senaryonuz incelemeye alındı. Yayımlandığında " +
            "“Senaryolarım” altında paylaşım bağlantıları görünecek.";
          senListeKutu.parentNode.insertBefore(bilgi, senListeKutu);
        }
      }).catch(function () {
        dugmeKilit(senForm, false);
        hataGoster(h, "Bağlantı kurulamadı.");
      });
    });
  }

  /* Haber sayfasindan "Senaryo yaz" ile gelindiyse form DOGRUDAN
     aciliyor: okur zaten ne yapmak istedigini soyledi, bir de sekme
     aramasin. */
  if (senForm && new URLSearchParams(location.search).get("senaryo")) {
    capaKur();
    $('[data-sekme="senaryo"]').hidden = false;
    sekmeGec("senaryo");
  }

  /* --- yonetim --- */

  function yonetimCiz(v) {
    var p = "";
    if (v.uyeler.length) {
      p += "<h3>Onay bekleyen üyeler</h3>";
      p += v.uyeler.map(function (u) {
        return '<article class="panel-satir-kart"><div class="panel-satir-ust">' +
          '<b>' + kacir(u.ad) + '</b><span class="kart-kunye">' + kacir(u.eposta) +
          '</span><span class="kart-kunye">' + tarih(u.kayit_ani) + '</span></div>' +
          '<div class="panel-eylem">' +
          '<button class="dugme dugme-birincil" type="button" data-uye-etkin="' + u.id + '">Etkinleştir</button>' +
          '<button class="dugme dugme-sade" type="button" data-uye-askı="' + u.id + '">Askıya al</button>' +
          '</div></article>';
      }).join("");
    }
    if (v.yazilar.length) {
      p += "<h3>İnceleme bekleyen yazılar</h3>";
      p += v.yazilar.map(function (y) {
        return '<article class="panel-satir-kart"><div class="panel-satir-ust">' +
          '<span class="rozet">' + kacir(y.kategori) + '</span>' +
          '<span class="kart-kunye">' + kacir(y.yazar) + '</span>' +
          '<span class="kart-kunye">' + tarih(y.gonderim) + '</span></div>' +
          '<h4>' + kacir(y.baslik) + '</h4>' +
          (y.ozet ? '<p class="kart-ozet">' + kacir(y.ozet) + '</p>' : '') +
          (y.guvenlik_notu
            ? '<p class="uyelik-mesaj uyari">Tarama: ' + kacir(y.guvenlik_notu) + '</p>'
            : '') +
          '<div class="panel-eylem">' +
          '<button class="dugme dugme-birincil" type="button" data-yazi-onay="' + y.id + '">Onayla</button>' +
          '<button class="dugme dugme-sade" type="button" data-yazi-ret="' + y.id + '">Reddet</button>' +
          '</div></article>';
      }).join("");
    }
    if ((v.senaryolar || []).length) {
      p += "<h3>İnceleme bekleyen senaryolar</h3>";
      p += v.senaryolar.map(function (s) {
        return '<article class="panel-satir-kart"><div class="panel-satir-ust">' +
          '<span class="rozet">ufuk ' + kacir(s.ufuk) + '</span>' +
          '<span class="kart-kunye">' + kacir(s.yazar) + '</span>' +
          '<span class="kart-kunye">' + tarih(s.gonderim) + '</span></div>' +
          '<p class="senaryo-onerme">' +
            '<span class="senaryo-kosul">' + kacir(s.kosul) + '</span>' +
            '<span class="senaryo-ok" aria-hidden="true">→</span>' +
            '<span class="senaryo-sonuc">' + kacir(s.sonuc) + '</span></p>' +
          (s.gerekce
            ? '<p class="kart-ozet">' + kacir(s.gerekce) + '</p>' : '') +
          (s.capa_baslik
            ? '<p class="kart-kunye">Bağlı haber: ' +
              kacir(s.capa_baslik) + '</p>' : '') +
          '<div class="panel-eylem">' +
          /* Senaryo onaylandigi anda yayimlaniyor: yazidan farkli olarak
             statik dosya uretilmiyor, haber sayfasi canli uctan
             okuyor. O yuzden ara "onaylandi" durumu yok. */
          '<button class="dugme dugme-birincil" type="button" data-sen-onay="' + s.id + '">Yayımla</button>' +
          '<button class="dugme dugme-sade" type="button" data-sen-ret="' + s.id + '">Reddet</button>' +
          '</div></article>';
      }).join("");
    }
    if (!p) p = '<p class="uyelik-alt">Bekleyen iş yok.</p>';

    /* KAYITLI HESAPLAR -- onay kuyrugundan AYRI.
       Yukaridaki listeler bir IS LISTESI: bitince bosalirlar. Bu ise
       bir KAYIT ve hep dolu. Ikisini ayirmak, "bekleyen is yok"
       yazarken hesap listesinin de kaybolmasini engelliyor.

       `google` alani BOOLEAN geliyor: Google hesabinin kalici
       kimligi baska sistemlerde de ayni kisiyi isaret eden bir
       tanimlayici ve yonetim ekraninda gorunmesi gereken bilgi
       "bagli mi", kimligin kendisi degil. */
    var hepsi = v.hepsi || [];
    if (hepsi.length) {
      p += '<h3>Kayıtlı hesaplar <span class="kart-kunye">(' +
           hepsi.length + ')</span></h3>';
      p += '<div class="hesap-liste">' + hepsi.map(function (u) {
        var ad = ((u.ad || "") + " " + (u.soyad || "")).trim() || "(adsız)";
        return '<article class="panel-satir-kart hesap-kart">' +
          '<div class="panel-satir-ust">' +
            '<b>' + kacir(ad) + '</b>' +
            '<span class="rozet rozet-durum durum-' + kacir(u.durum) + '">' +
              kacir(UYE_DURUM[u.durum] || u.durum) + '</span>' +
            (u.rol === "yonetici"
              ? '<span class="rozet">Yönetici</span>' : '') +
            (u.google ? '<span class="rozet">Google</span>' : '') +
          '</div>' +
          '<p class="kart-kunye">' + kacir(u.eposta) + '</p>' +
          (u.unvan ? '<p class="kart-ozet">' + kacir(u.unvan) + '</p>' : '') +
          '<p class="kart-kunye">Kayıt: ' + tarih(u.kayit_ani) +
            ' · Son giriş: ' + tarih(u.son_giris) + '</p>' +
          '</article>';
      }).join("") + '</div>';
    }

    yonetimKutu.innerHTML = p;

    function karar(secici, tur, durumu, sorNeden) {
      $$(secici, yonetimKutu).forEach(function (d) {
        d.addEventListener("click", function () {
          var neden = sorNeden ? prompt("Gerekçe (yazara gösterilir):") : null;
          if (sorNeden && neden === null) return;
          istek("/api/yonetim/karar", {
            method: "POST",
            govde: {
              tur: tur, id: Number(d.getAttribute(secici.slice(1, -1))),
              durum: durumu, neden: neden,
            },
          }).then(yonetimYukle);
        });
      });
    }
    karar("[data-uye-etkin]", "uye", "etkin", false);
    karar("[data-uye-askı]", "uye", "askida", false);
    karar("[data-yazi-onay]", "yazi", "onaylandi", false);
    karar("[data-yazi-ret]", "yazi", "reddedildi", true);
    karar("[data-sen-onay]", "senaryo", "yayimlandi", false);
    karar("[data-sen-ret]", "senaryo", "reddedildi", true);
  }

  function yonetimYukle() {
    return istek("/api/yonetim/ozet").then(function (y) {
      if (y.tamam) yonetimCiz(y.veri);
    });
  }

  /* --- acilis --- */

  var cikisDugme = $("[data-cikis]");
  if (cikisDugme) {
    cikisDugme.addEventListener("click", function () {
      istek("/api/cikis", { method: "POST" }).then(function () {
        location.href = "/giris/?durum=cikildi";
      });
    });
  }

  istek("/api/ben").then(function (y) {
    if (!y.tamam || !y.veri.uye) {
      if (girisGerek) {
        /* Giris baglantisi SU ANKI adresi tasiyor: okur giris yapinca
           tam olarak buraya -- yani hangi habere yazacaksa o capayla --
           geri geliyor. */
        if (window.NetarisDonus) {
          var g = girisGerek.querySelector('a[href^="/giris/"]');
          if (g) window.NetarisDonus.baglantiyaEkle(g);
        }
        girisGerek.hidden = false;
      }
      return;
    }
    panel.hidden = false;
    kartiDoldur(y.veri.uye);
    profilDoldur(y.veri.uye);
    if (y.veri.uye.rol === "yonetici") {
      $("[data-yonetici]").hidden = false;
      yonetimYukle();
    }
    listeYukle();
    senaryoYukle();
    begenileriYukle();
  }).catch(function () {
    if (girisGerek) girisGerek.hidden = false;
  });
})();
