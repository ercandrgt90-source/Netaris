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
        if (y.tamam) { location.href = "/panel/"; return; }
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

  var vazgec = $("[data-vazgec]");
  if (vazgec) {
    vazgec.addEventListener("click", function () {
      formTemizle();
      sekmeGec("yazilarim");
    });
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
    yonetimKutu.innerHTML = p || '<p class="uyelik-alt">Bekleyen iş yok.</p>';

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
      if (girisGerek) girisGerek.hidden = false;
      return;
    }
    panel.hidden = false;
    var kim = $("[data-kim]");
    if (kim) kim.textContent = y.veri.uye.ad + " · " + y.veri.uye.eposta;
    if (y.veri.uye.rol === "yonetici") {
      $("[data-yonetici]").hidden = false;
      yonetimYukle();
    }
    listeYukle();
  }).catch(function () {
    if (girisGerek) girisGerek.hidden = false;
  });
})();
