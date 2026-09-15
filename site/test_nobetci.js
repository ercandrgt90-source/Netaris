/* Nobetci -- GitHub takvimi durdugunda akisi geri getiren yedek tetik.
 *
 * BU DOSYA NEDEN VAR
 * ------------------
 * 2026-08-26 aksami GitHub Actions kotasi doldu. Kota bitince is
 * KIRMIZI DONMUYOR, sadece BASLAMIYOR -- yani hicbir yerde uyari
 * gorunmuyor. Depo ertesi gun herkese acildi (dakika sinirsiz) ama
 * zamanlanmis kosular geri gelmedi: 26 Agustos 16:36'dan sonra bir
 * tane bile dusmedi, elle tetiklenenler ise sorunsuz calisti. Yani
 * hat saglamdi; calismayan sey ZAMANLAYICIYDI. Site saatlerce bayat
 * kaldi ve bunu ancak birisi bakinca fark etti.
 *
 * Nobetci bu bosluğu kapatiyor: saat basi bakiyor, yayindaki icerik
 * esikten eskiyse GitHub'i tetikliyor.
 *
 * NEDEN SINANMASI GEREKIYOR
 * -------------------------
 * Bu kodun iki yanlis davranisi da PAHALI ve ikisi de SESSIZ:
 *
 *   * Fazla tetiklerse: her saat gereksiz kosu baslatir. GitHub'in
 *     kendi takvimi zaten calisirken ikinci bir kosu bosa is demek.
 *   * Az tetiklerse: hicbir sey olmaz ve site yine saatlerce bayat
 *     kalir -- yani nobetci VARMIS GIBI gorunur ama yoktur.
 *
 * Ozellikle "okunamadi" hali onemli: BILINMIYOR ile BAYAT ayni sey
 * degil. Bilinmezlikte tetiklemek, RSS'e gecici olarak ulasilamayan
 * her saatte bir kosu baslatmak olurdu.
 *
 * Calistirma:  node site/test_nobetci.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let gecti = 0;
const kaldi = [];

function esit(bulunan, beklenen, aciklama) {
  if (bulunan === beklenen) {
    gecti++;
    console.log("  gecti  " + aciklama);
  } else {
    kaldi.push(aciklama);
    console.log("  KALDI  " + aciklama);
    console.log("         beklenen: " + JSON.stringify(beklenen));
    console.log("         bulunan : " + JSON.stringify(bulunan));
  }
}

/* worker.js bir ES modulu; `export default` blogu VM'de calismaz.
   Yalnizca o blok cikariliyor, fonksiyonlarin kodu AYNEN kosuyor. */
let kaynak = fs.readFileSync(path.join(__dirname, "worker.js"), "utf8");
kaynak = kaynak.slice(0, kaynak.indexOf("export default"));

/* Tetik cagrilarini yakalayan sahte `fetch`. */
let cagrilar = [];
function sahteFetch(url, ayar) {
  cagrilar.push({ url: String(url), ayar: ayar || {} });
  return Promise.resolve({ status: 204, ok: true });
}

const ortam = {
  console: { log() {}, error() {} },   /* gunluk gurultusu bastiriliyor */
  fetch: sahteFetch,
  Date, Number, JSON, Promise, String,
  /*  bir Response uretiyor; VM baglaminda yok. */
  Response: class { constructor(g){ this._g = g; }
                    json(){ return Promise.resolve(JSON.parse(this._g)); } },
};
ortam.globalThis = ortam;
vm.createContext(ortam);
vm.runInContext(kaynak, ortam);

const nobetci = ortam.nobetci;

/* `const` bildirimleri VM baglaminda `globalThis`e BAGLANMIYOR --
   yalnizca `function` bildirimleri baglaniyor. Ilk yazimda
   `ortam.NOBET_ESIK_SAAT` okundu, `undefined` geldi ve sinir
   sinamalari sessizce `NaN` ile kostu: "esigin ustunde tetikliyor"
   sinamasi gecersiz bir tarih uretip tetiklemedigi icin KALDI verdi.
   Ayni baglamda ikinci bir betik calistirmak sozcuksel baglamayi
   goruyor. */
const ESIK = vm.runInContext("NOBET_ESIK_SAAT", ortam);

/* Verilen yasa sahip bir `istatistik.json` donduren sahte ASSETS. */
function ortamKur(saat, jeton) {
  const govde = saat === null
    ? JSON.stringify({ sayfa: 10 })              /* `uretim` alani YOK */
    : JSON.stringify({
        sayfa: 10,
        uretim: new Date(Date.now() - saat * 3600000).toISOString(),
      });
  return {
    GITHUB_TETIK_JETONU: jeton,
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        text: () => Promise.resolve(govde),
        json: () => Promise.resolve(JSON.parse(govde)),
      }),
    },
  };
}

/* Sahte D1. `prepare().bind().run()` ve `.all()` zincirini tasiyor;
   calistirilan her ifade `sorgular`a yaziliyor. */
function sahteDB(patlat) {
  const sorgular = [];
  const db = {
    sorgular,
    prepare(sql) {
      const kayit = { sql, par: null };
      return {
        bind(...p) { kayit.par = p; return this; },
        run() {
          if (patlat) return Promise.reject(new Error("D1 dustu"));
          sorgular.push(kayit);
          return Promise.resolve({});
        },
        all() {
          if (patlat) return Promise.reject(new Error("D1 dustu"));
          sorgular.push(kayit);
          return Promise.resolve({ results: [
            { an: "2026-09-15T11:00:00Z", yas: 0.7,
              karar: "tetiklendi", yanit: 204 },
          ] });
        },
      };
    },
  };
  return db;
}

/* Yazilan iz satirlarinin `karar` alanlari. */
function kararlar(db) {
  return db.sorgular
    .filter((x) => x.sql.startsWith("INSERT INTO nobet_izi"))
    .map((x) => x.par[2]);
}


async function kos() {
  console.log("\nNobetci -- alan yuklendi mi\n");
  esit(typeof nobetci, "function", "nobetci bulundu");
  esit(typeof ESIK, "number", "esik sayi olarak tanimli");

  console.log("\nJETON YOKSA HICBIR SEY YAPMAZ\n");
  /* Bu kodun dagitilmasi risksiz olmali: jeton eklenene kadar
     davranis degismemeli. */
  cagrilar = [];
  await nobetci(ortamKur(99, undefined));
  esit(cagrilar.length, 0, "jeton tanimsizken tetiklemiyor");
  cagrilar = [];
  await nobetci(ortamKur(99, ""));
  esit(cagrilar.length, 0, "jeton bos dizgiyken tetiklemiyor");

  console.log("\nTAZEYKEN KARISMIYOR\n");
  /* GitHub'in kendi takvimi calisirken nobetci sessiz durmali;
     aksi halde her sey iki kez kosar. */
  cagrilar = [];
  await nobetci(ortamKur(0.1, "jtn"));
  esit(cagrilar.length, 0, "6 dakikalik icerikte tetiklemiyor");
  cagrilar = [];
  await nobetci(ortamKur(ESIK - 0.2, "jtn"));
  esit(cagrilar.length, 0, "esigin hemen altinda tetiklemiyor");

  /* CIFT KOSU OLMAMALI -- ama "olmamali" olcusu OLCULDU.
     Bu blok once soyle diyordu: "GitHub'in takvimi hafta ici yarim
     saatte bir kosuyor, nobetci o araliga karismamali; esik asagi
     cekilirse once bu sinama kirilir -- amaci tam olarak bu."

     Tuzak teli isini yapti: 2026-09-14'te esik dusurulmek istendi ve
     once bu sinama kirildi. Sonra VARSAYIM olculdu ve tutmadigi
     gorildu -- son 100 zamanlanmis kosu:

         ardisik aralik  ortanca 173 dk, %90 295 dk, en buyuk 369 dk
         99 araligin 93'u 45 dakikayi asiyor

     GitHub yarim saatlik cron yaziyor ama cagrilarin buyuk kismini DUSURUYOR.
     Sapma degil atlama: sapma ayrica olculdu, 15 dakikayi hic
     gecmiyor. Yani carpisilacak duzenli bir takvim YOK ve nobetci
     akisin tek duzenleyicisi.

     KORUNAN SEY DEGISMEDI: nobetci, hattin NORMAL turunun ortasina
     karismamali. Degisen, o turun ne kadar surdugu. */
  cagrilar = [];
  await nobetci(ortamKur(0.5, "jtn"));
  esit(cagrilar.length, 0, "normal tur icinde (30 dk) susuyor");
  /* 45 dakika ARTIK tetikliyor: takvim seyrek dustugu icin bu yas
     "biraz gecikmis saglikli tur" degil, "tur hic gelmedi" demek. */
  cagrilar = [];
  await nobetci(ortamKur(0.75, "jtn"));
  esit(cagrilar.length, 1, "45 dakikada tetikliyor (takvim seyrek)");

  console.log("\nBAYATLAYINCA TETIKLIYOR\n");
  cagrilar = [];
  await nobetci(ortamKur(ESIK + 0.2, "jtn"));
  esit(cagrilar.length, 1, "esigin hemen ustunde tetikliyor");
  cagrilar = [];
  await nobetci(ortamKur(9, "jtn"));
  esit(cagrilar.length, 1, "9 saatlik icerikte tetikliyor");

  console.log("\nISTEK DOGRU KURULUYOR\n");
  /* BOS OLABILIR. Ilk yazimda dogrudan `cagrilar[0].ayar` okunuyordu
     ve onceki bir sinama tetiklemedigi anda betik TypeError ile
     coküyordu -- geriye kalan sinamalar hic kosmuyordu. Cikis kodu 1
     donuyordu, yani "yakaladi" gibi gorunuyordu ama asil kural
     sinanmamis oluyordu. Bir cokme, bir sinamanin yerini tutmaz. */
  if (!cagrilar.length) {
    kaldi.push("istek kurulumu sinanamadi -- onceki adim tetiklemedi");
    console.log("  KALDI  istek kurulumu sinanamadi (cagri yok)");
  }
  const c = cagrilar[0] || { url: "", ayar: { headers: {}, body: "{}" } };
  esit(c.url.endsWith("/dispatches"), true, "dispatches ucuna gidiyor");
  esit(c.ayar.method, "POST", "POST kullaniyor");
  /* GitHub API User-Agent'i ZORUNLU kiliyor; yoksa 403 doner ve
     tetik sessizce calismaz. */
  esit(typeof c.ayar.headers["User-Agent"], "string",
       "User-Agent gonderiliyor (GitHub zorunlu kiliyor)");
  esit(c.ayar.headers["Authorization"], "Bearer jtn",
       "jeton Authorization basliginda");
  esit(JSON.parse(c.ayar.body).event_type, "tazele",
       "olay turu is akisindakiyle ayni");

  /* TANILAMA UCU -- JETONU HICBIR KOSULDA SIZDIRMAMALI.
     Nobetci yapilandirilmamisken de dogru calisirken de sessiz;
     ikisi disaridan ayni gorunuyordu. Uc bu ayrimi yapiyor ama
     bunu yaparken sirri acmamali. */
  const durum = ortam.nobetciDurum;
  esit(typeof durum, "function", "nobetciDurum bulundu");

  {
    const y = await durum(ortamKur(9, "cok-gizli-jeton-degeri"));
    const g = await y.json();
    esit(g.jeton_kurulu, true, "jeton kuruluyken bildiriyor");
    esit(g.tetikler, true, "bayat icerikte tetiklerim diyor");
    const ham = JSON.stringify(g);
    esit(ham.includes("cok-gizli-jeton-degeri"), false,
         "jeton DEGERI yanitta gecmiyor");
    esit(ham.includes("gizli"), false, "jetonun parcasi bile gecmiyor");
  }
  {
    const y = await durum(ortamKur(9, undefined));
    const g = await y.json();
    esit(g.jeton_kurulu, false, "jeton yokken bildiriyor");
    esit(g.tetikler, false, "jeton yokken tetiklemem diyor");
  }
  {
    const y = await durum(ortamKur(0.2, "jtn"));
    const g = await y.json();
    esit(g.tetikler, false, "taze icerikte tetiklemem diyor");
    esit(g.icerik_yasi_saat < 1, true, "yasi saat cinsinden veriyor");
  }

  /* GERILEME SINAMASI: OLCU RSS'TEN OKUNMAMALI.

     Once `/rss.xml` icindeki en yeni `pubDate` okunuyordu. O alan GUN
     bazinda uretiliyor ("Fri, 28 Aug 2026 00:00:00 +0000") -- saat
     tasimiyor. Yani site az once kurulmus olsa bile en yeni haber
     GECE YARISI gorunuyordu.

     Olculdu (2026-08-28 08:24): kosu 08:05'te bitti, uc "icerik 8,41
     saatlik" dedi. Jeton kurulu olsaydi sonuc bir DONGU olurdu: her
     gun 01:30'dan sonra tetikle, kur, `pubDate` yine gece yarisi
     kalsin, yarim saat sonra tekrar tetikle.

     Asagidaki ortam tam o tuzagi kuruyor: `uretim` TAZE ama RSS gun
     bazinda ve bayat gorunuyor. Nobetci tetiklememeli. */
  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          uretim: new Date(Date.now() - 0.2 * 3600000).toISOString(),
        }),
        text: () => Promise.resolve(
          "<rss><item><pubDate>" + new Date(Date.now() - 9 * 3600000)
            .toUTCString() + "</pubDate></item></rss>"),
      }),
    },
  });
  esit(cagrilar.length, 0,
       "gun bazli RSS bayat gorunse de kurulum taze ise tetiklemiyor");

  console.log("\nBILINMIYOR, BAYAT DEMEK DEGIL\n");
  /* RSS okunamazsa tetiklememeli: gecici bir okuma hatasi her saat
     kosu baslatmamali. */
  cagrilar = [];
  await nobetci(ortamKur(null, "jtn"));
  esit(cagrilar.length, 0, "pubDate yoksa tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: { fetch: () => Promise.resolve({ ok: false }) },
  });
  esit(cagrilar.length, 0, "RSS 404 verirse tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: { fetch: () => Promise.reject(new Error("ag yok")) },
  });
  esit(cagrilar.length, 0, "RSS istegi patlarsa tetiklemiyor");

  cagrilar = [];
  await nobetci({
    GITHUB_TETIK_JETONU: "jtn",
    ASSETS: {
      fetch: () => Promise.resolve({
        ok: true,
        text: () => Promise.resolve(
          "<rss><item><pubDate>tarih degil</pubDate></item></rss>"),
      }),
    },
  });
  esit(cagrilar.length, 0, "tarih cozulemezse tetiklemiyor");

  /* ------------------------------------------------------------
     KARAR IZI
     ---------
     Nobetcinin tek kaydi `console.log`du -- Cloudflare gunlugu,
     Logpush olmadan saklanmiyor ve depodan okunamiyor.

     Olculdu (2026-09-15): otomasyon kosularinda 155 dakikalik bir
     bosluk vardi ve o araliga ait HIC calisma kaydi yoktu. "Nobetci
     atesledi de GitHub mi almadi, yoksa nobetci hic bakmadi mi"
     sorusu CEVAPLANAMADI -- siteyi 13 gun donduran arizanin ayni
     kor noktasi.

     DORT KARARIN DORDU DE yaziliyor: "taze oldugu icin dokunmadim"
     ile "bakamadim" ayni sey degil; ikisi de tetik uretmiyor ama
     biri saglik, digeri ariza. ------------------------------------ */
  console.log("\nKarar izi\n");

  let db = sahteDB(false);
  let env = ortamKur(ESIK + 0.5, "jeton");
  env.DB = db;
  await nobetci(env);
  esit(kararlar(db).join(","), "tetiklendi", "tetikleme iz birakiyor");

  db = sahteDB(false);
  env = ortamKur(ESIK - 0.3, "jeton");
  env.DB = db;
  await nobetci(env);
  esit(kararlar(db).join(","), "taze", "TAZE karari da iz birakiyor");

  db = sahteDB(false);
  env = ortamKur(null, "jeton");            /* yas okunamadi */
  env.DB = db;
  await nobetci(env);
  esit(kararlar(db).join(","), "yas_bilinmiyor",
       "BILINMIYOR ile TAZE ayri kaydediliyor");

  db = sahteDB(false);
  env = ortamKur(ESIK + 0.5, undefined);    /* jeton yok */
  env.DB = db;
  await nobetci(env);
  esit(kararlar(db).join(","), "jetonsuz", "jeton yoksa sebep yaziliyor");

  /* GOZLEM YENI BIR ARIZA KAYNAGI OLMAMALI. */
  const once = cagrilar.length;
  env = ortamKur(ESIK + 0.5, "jeton");      /* env.DB YOK */
  await nobetci(env);
  esit(cagrilar.length, once + 1, "DB yokken nobetci yine tetikliyor");

  const once2 = cagrilar.length;
  env = ortamKur(ESIK + 0.5, "jeton");
  env.DB = sahteDB(true);                   /* her yazma patliyor */
  await nobetci(env);
  esit(cagrilar.length, once2 + 1, "DB patlasa da nobetci tetikliyor");

  /* Durum uc noktasi gecmisi de donuyor: "su an tetikler mi" sorusu,
     "son iki saatte ne yapti" sorusunu cevaplamiyor. */
  env = ortamKur(0.1, "jeton");
  env.DB = sahteDB(false);
  const d = await (ortam.nobetciDurum)(env);
  const g = await d.json();
  esit(Array.isArray(g.son_kararlar), true, "durum son kararlari donuyor");
  esit(g.son_kararlar.length > 0, true, "gecmis dolu");

  console.log("\n" + gecti + " gecti, " + kaldi.length + " kaldi");
  process.exit(kaldi.length ? 1 : 0);
}

kos();
