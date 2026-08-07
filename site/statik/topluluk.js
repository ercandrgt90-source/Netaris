/* Topluluk sayfasi -- yayimlanmis butun senaryolar.
 *
 * NEDEN CANLI UCTAN
 * Site statik ve gunde birkac kez kuruluyor. Senaryolar sayfaya
 * gomulseydi, yazilan bir senaryo bir sonraki kuruluma kadar (saatler)
 * gorunmezdi ve yazan kisi katkisinin kayboldugunu dusunurdu.
 *
 * ONE CIKANDAN FARKI: burada OY SARTI YOK. Ana sayfadaki "one cikan"
 * bir SECIM (oy gerekir); burasi bir KAYIT (oy gerekmez). Sifir oylu
 * senaryoyu hicbir yerde gostermemek soguk baslangic kilidi
 * yaratiyordu -- kimse gormedigi icin oy verilmiyor, oy verilmedigi
 * icin gorunmuyor.
 */

(function () {
  "use strict";

  var liste = document.getElementById("topluluk-liste");
  var durum = document.getElementById("topluluk-durum");
  if (!liste || !durum) return;

  function kacir(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function tarih(s) {
    if (!s) return "";
    var t = Date.parse(s);
    if (isNaN(t)) return "";
    return new Date(t).toLocaleDateString("tr-TR",
      { day: "numeric", month: "long", year: "numeric" });
  }

  fetch("/api/senaryo/hepsi", { headers: { accept: "application/json" } })
    .then(function (y) {
      if (!y.ok) throw new Error("uc " + y.status);
      return y.json();
    })
    .then(function (v) {
      var s = (v && v.senaryolar) || [];

      // Hic senaryo yoksa bu bir HATA DEGIL. Sayfa "henuz yok" diyor --
      // sahte ornek senaryo uretmek, toplulugun var olmadigi gercegini
      // gizlemek olurdu.
      if (!s.length) {
        durum.textContent = "Henüz yayımlanmış senaryo yok. İlkini siz " +
                            "yazabilirsiniz.";
        return;
      }

      var h = "";
      for (var i = 0; i < s.length; i++) {
        var x = s[i];
        h += '<li class="senaryo-satir">' +
             '<p class="senaryo-onerme">' +
             '<span class="senaryo-kosul">' + kacir(x.kosul) + '</span>' +
             '<span class="senaryo-ok" aria-hidden="true">→</span>' +
             '<span class="senaryo-sonuc">' + kacir(x.sonuc) + '</span>' +
             '</p>' +
             '<p class="senaryo-kunye">' +
             // Sifir oy da GORUNUYOR: gizlemek, oy sayisini bir basari
             // olcusu gibi sunmak olurdu. Sayi bir olgu.
             '<span class="one-oy">▲ ' + Number(x.oy || 0) + '</span> ' +
             '<b>' + kacir(x.yazar) + '</b>' +
             ' · ufuk ' + kacir(x.ufuk);
        var t = tarih(x.yayin);
        if (t) h += ' · ' + kacir(t);
        if (x.capa) {
          h += ' · <a href="' + kacir(x.capa) + '">' +
               kacir(x.capa_baslik || "habere git") + '</a>';
        }
        h += '</p></li>';
      }
      liste.innerHTML = h;
      liste.hidden = false;
      durum.hidden = true;
    })
    .catch(function () {
      // Uc coktugunde SESSIZ KALMIYORUZ: bos bir sayfa, senaryo
      // olmadigi izlenimi verir. Ikisi ayri sey ve okur farki bilmeli.
      durum.textContent = "Senaryolar şu an yüklenemedi. Sayfayı " +
                          "yenilemeyi deneyebilirsiniz.";
    });
})();
