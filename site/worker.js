/* Netaris uyelik ve yazi API'si -- Cloudflare Worker.
 *
 * ISTEK AKISI
 * -----------
 * Cloudflare once statik varlia bakar. `/giris/`, `/panel/` gibi adresler
 * `cikti/` altinda gercek dosya oldugu icin Worker'a HIC gelmez. Worker
 * yalnizca `/api/...` icin calisir; kalan her sey `env.ASSETS`e dusuyor.
 * Yani sitenin okuma tarafi eskisi gibi tamamen statik -- uyelik sistemi
 * coktugunde haberler yayinda kalir.
 *
 * PAROLA
 * ------
 * PBKDF2-SHA256. Dongu sayisi ozetin ICINDE saklaniyor ("pbkdf2$210000$..")
 * ki ileride artirildiginda eski kayitlar dogrulanmaya devam etsin.
 *
 * DIKKAT -- Workers ucretsiz katmaninda istek basina 10 ms CPU siniri var
 * ve PBKDF2 bu siniri zorlayabilir. Guvenligi dusurup dongu sayisini
 * kirpmak yerine sinir asilirsa Workers Paid ($5/ay) gerekiyor; bu bir
 * maliyet karari ve kullaniciya birakiliyor. Giris/kayit disindaki hicbir
 * uc PBKDF2 calistirmiyor, dolayisiyla gunluk trafigin tamami degil
 * yalnizca kimlik islemleri etkilenir.
 *
 * OTURUM
 * ------
 * Rastgele 32 bayt jeton cereze yaziliyor; veritabaninda yalnizca SHA-256
 * OZETI duruyor. Veritabani sizsa bile o kayitlarla oturum acilamaz.
 * Cerez HttpOnly + Secure + SameSite=Lax: JavaScript okuyamaz, siteler
 * arasi istekte gitmez.
 */

const OTURUM_CEREZ = "netaris_oturum";
const OTURUM_GUN = 30;
/* Cloudflare Workers PBKDF2'yi 100.000 dongude TAVANLIYOR:
 *   NotSupportedError: iteration counts above 100000 are not supported
 * Bu bir tercih degil, platform siniri. OWASP'in PBKDF2-SHA256 icin
 * onerdigi sayi daha yuksek; ulasilamiyor.
 *
 * Telafi: en az 10 karakter parola sarti ve giris denemesinde 15
 * dakikada 8 deneme siniri. Ozet bicimi dongu sayisini ICINDE tasiyor,
 * dolayisiyla platform tavani yukselirse eski kayitlar bozulmadan yeni
 * dongu sayisina gecilebilir.
 */
const PBKDF2_DONGU = 100000;

/* Yazi sinirlari. Ust sinir kotayi degil, MODERASYONU koruyor: 60 bin
   karakterlik bir gonderiyi insan okuyup onaylayamaz. */
const EN_AZ_GOVDE = 400;
const EN_COK_GOVDE = 24000;
const EN_COK_BASLIK = 140;
const EN_COK_OZET = 400;

const KATEGORILER = ["Analist Yorumu", "Makro", "Bilanço Analizi"];

/* --- Senaryo sinirlari ---
   Kosul ve sonuc KISA tutuluyor. Uzun serbest metin, kosullu bir
   onermeyi paragrafa cevirip degerlendirilemez hale getiriyor; sinir
   yazani tek cumleye zorluyor. Gerekce ayri ve daha uzun olabilir. */
const EN_COK_KOSUL = 180;
const EN_COK_SONUC = 180;
const EN_COK_GEREKCE = 1200;
/* Curutme kosulu TEK CUMLE olmali: "beni ne yanıltır" sorusunun cevabi
   uzarsa ikinci bir gerekceye donusuyor ve asil isini -- tek bir
   olcutu ONCEDEN yazmak -- kaybediyor. */
const EN_COK_CURUTME = 220;
const EN_COK_KAYNAK = 500;
const EN_AZ_KOSUL = 12;

/* Ufuk secenekleri ve gun karsiliklari. Serbest tarih ALINMIYOR:
   "2027-03-14" gibi bir tarih kesinlik izlenimi verir ama senaryo o
   kadar hassas degildir. Kapali liste hem dogrulamayi hem ileride
   toplu sonuclandirmayi basitlestiriyor. */
const UFUKLAR = {
  "1 hafta": 7,
  "1 ay": 30,
  "3 ay": 90,
  "6 ay": 180,
  "1 yıl": 365,
};
/* Senaryo tetikleyicisi olarak SECILEBILEN gosterge kodlari.
   Liste `analiz/senaryo_kapi.TETIKLEYICILER` ile ayni olmali; ikisi
   ayrisirsa formda gorunen bir secenek burada reddedilir ve kullanici
   sebebini anlamaz. Formu ureten sablon o listeden besleniyor. */
const OLCUT_KODLARI = [
  "TP.TUKFIY2025.GENEL", "TP.FE25.OKTG04", "TP.APIFON4",
  "TP.DK.USD.S.YTL", "DFF", "DGS10", "DGS2", "CPIAUCNS", "PCEPILFE",
  "UNRATE", "DCOILBRENTEU", "DTWEXBGS", "VIXCLS", "PAXGUSD", "XBTUSD",
];
const OLCUT_YONLERI = ["ustunde", "altinda"];

const CAPA_TURLERI = ["haber", "varlik", "konu"];

/* ------------------------------------------------------------------ araclar */

const kodla = (s) => new TextEncoder().encode(s);

function onaltilik(tampon) {
  return [...new Uint8Array(tampon)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256(metin) {
  return onaltilik(await crypto.subtle.digest("SHA-256", kodla(metin)));
}

function rastgele(bayt = 32) {
  return onaltilik(crypto.getRandomValues(new Uint8Array(bayt)));
}

async function pbkdf2(parola, tuz, dongu) {
  const anahtar = await crypto.subtle.importKey(
    "raw", kodla(parola), "PBKDF2", false, ["deriveBits"],
  );
  const bit = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: kodla(tuz), iterations: dongu, hash: "SHA-256" },
    anahtar, 256,
  );
  return onaltilik(bit);
}

async function parolaOzetle(parola) {
  const tuz = rastgele(16);
  return `pbkdf2$${PBKDF2_DONGU}$${tuz}$${await pbkdf2(parola, tuz, PBKDF2_DONGU)}`;
}

async function parolaDogrula(parola, kayit) {
  const p = String(kayit || "").split("$");
  if (p.length !== 4 || p[0] !== "pbkdf2") return false;
  const beklenen = p[3];
  const bulunan = await pbkdf2(parola, p[2], Number(p[1]) || PBKDF2_DONGU);
  /* Sabit sureli karsilastirma: uzunluk ayni oldugu icin XOR toplami
     yeterli. `===` erken cikip zamanlama bilgisi sizdirabilirdi. */
  if (beklenen.length !== bulunan.length) return false;
  let fark = 0;
  for (let i = 0; i < beklenen.length; i++) {
    fark |= beklenen.charCodeAt(i) ^ bulunan.charCodeAt(i);
  }
  return fark === 0;
}

const simdi = () => new Date().toISOString();
const damga = () => Math.floor(Date.now() / 1000);

function yanit(veri, durum = 200, ekBaslik = {}) {
  return new Response(JSON.stringify(veri), {
    status: durum,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...ekBaslik,
    },
  });
}

const hata = (mesaj, durum = 400) => yanit({ hata: mesaj }, durum);

function cerezOku(istek, ad) {
  const ham = istek.headers.get("cookie") || "";
  for (const parca of ham.split(";")) {
    const [k, ...d] = parca.trim().split("=");
    if (k === ad) return d.join("=");
  }
  return null;
}

function cerezYaz(jeton, gun) {
  const yas = gun * 86400;
  return `${OTURUM_CEREZ}=${jeton}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${yas}`;
}

const cerezSil = () =>
  `${OTURUM_CEREZ}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;

/* E-posta bicimi. Amac gecerliligi KANITLAMAK degil -- onu dogrulama
   baglantisi yapiyor. Buradaki kontrol yalnizca acikca bozuk girisleri
   eliyor; asiri kati bir desen gercek adresleri reddeder. */
function epostaGecerli(e) {
  return typeof e === "string" && e.length <= 254 && /^[^@\s]+@[^@\s.]+\.[^@\s]+$/.test(e);
}

function metinKirp(d, enCok) {
  return typeof d === "string" ? d.trim().slice(0, enCok) : "";
}

/* ------------------------------------------------------------- hiz sinirlama */

async function denemeArtir(db, anahtar, pencereSn, sinir) {
  const t = damga();
  const s = await db.prepare("SELECT sayi, sifirlanir FROM deneme WHERE anahtar = ?")
    .bind(anahtar).first();
  if (!s || s.sifirlanir < t) {
    await db.prepare(
      "INSERT INTO deneme (anahtar, sayi, sifirlanir) VALUES (?, 1, ?) " +
      "ON CONFLICT(anahtar) DO UPDATE SET sayi = 1, sifirlanir = excluded.sifirlanir",
    ).bind(anahtar, t + pencereSn).run();
    return false;
  }
  if (s.sayi >= sinir) return true;
  await db.prepare("UPDATE deneme SET sayi = sayi + 1 WHERE anahtar = ?")
    .bind(anahtar).run();
  return false;
}

async function denemeSifirla(db, anahtar) {
  await db.prepare("DELETE FROM deneme WHERE anahtar = ?").bind(anahtar).run();
}

/* ------------------------------------------------------------------- oturum */

async function oturumAc(db, uyeId) {
  const jeton = rastgele(32);
  await db.prepare(
    "INSERT INTO oturum (jeton_ozeti, uye_id, biter, olusma) VALUES (?, ?, ?, ?)",
  ).bind(await sha256(jeton), uyeId, damga() + OTURUM_GUN * 86400, simdi()).run();
  return jeton;
}

async function uyeBul(istek, db) {
  const jeton = cerezOku(istek, OTURUM_CEREZ);
  if (!jeton) return null;
  const s = await db.prepare(
    "SELECT u.id, u.eposta, u.ad, u.rol, u.durum FROM oturum o " +
    "JOIN uye u ON u.id = o.uye_id WHERE o.jeton_ozeti = ? AND o.biter > ?",
  ).bind(await sha256(jeton), damga()).first();
  return s && s.durum === "etkin" ? s : null;
}

/* --------------------------------------------------------- Google girisi */

/* GOOGLE ILE GIRIS -- kimlik jetonu (ID token) dogrulamasi.
 *
 * NEDEN BU YOL, "authorization code" DEGIL
 * ----------------------------------------
 * Google Identity Services tarayicida imzali bir JWT ("credential")
 * veriyor. Onu sunucuda dogrulamak icin YALNIZCA ISTEMCI KIMLIGI
 * gerekiyor; istemci kimligi GIZLI DEGIL, sayfada zaten gorunuyor.
 * Klasik yetkilendirme kodu akisi bir de ISTEMCI SIRRI ister ve o sirrin
 * saklanmasi, donmesi, sizmamasi ayri bir yuk. Burada ihtiyacimiz olan
 * tek sey "bu kisi bu e-postanin sahibi mi" sorusunun cevabi; kod akisi
 * bunun otesinde Google API'lerine erisim veriyor ki BIZE GEREKMIYOR.
 *
 * Az yetki isteyen yol, az sey kaybettiren yoldur.
 *
 * JETON KORU KORUNE KABUL EDILMEZ. Dogrulanan seyler:
 *   imza   -- Google'in acik anahtariyla (RS256), JWKS ucundan
 *   iss    -- accounts.google.com
 *   aud    -- BIZIM istemci kimligimiz; baska bir uygulamaya verilmis
 *             gecerli bir jeton burada ise yaramaz
 *   exp    -- suresi dolmus jeton kabul edilmez
 *   email_verified -- Google e-postayi dogrulamamissa hesap acilmaz
 *
 * `aud` denetimi atlanirsa herhangi bir sitenin Google jetonu burada
 * gecerli olur; bu, en sik yapilan ve en agir sonuclu atlamadir.
 */

const GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs";
const GOOGLE_ISS = ["accounts.google.com", "https://accounts.google.com"];

/* Anahtar onbellegi. Worker ornegi yasadigi surece duruyor; Google
   anahtarlari nadiren donuyor ve her girise bir istek eklemek hem yavas
   hem gereksiz. Kimligi bilinmeyen bir anahtar gelirse onbellek
   tazeleniyor -- yani anahtar donusu kendiliginden karsilaniyor. */
let _jwksOnbellek = { anahtarlar: null, zaman: 0 };
const JWKS_OMUR_SN = 3600;

async function googleAnahtarlari(zorla = false) {
  if (!zorla && _jwksOnbellek.anahtarlar
      && damga() - _jwksOnbellek.zaman < JWKS_OMUR_SN) {
    return _jwksOnbellek.anahtarlar;
  }
  const r = await fetch(GOOGLE_JWKS);
  if (!r.ok) throw new Error("jwks alinamadi");
  const v = await r.json();
  _jwksOnbellek = { anahtarlar: v.keys || [], zaman: damga() };
  return _jwksOnbellek.anahtarlar;
}

function b64urlCoz(m) {
  const d = m.replace(/-/g, "+").replace(/_/g, "/");
  const dolgu = d + "=".repeat((4 - (d.length % 4)) % 4);
  const ham = atob(dolgu);
  const bayt = new Uint8Array(ham.length);
  for (let i = 0; i < ham.length; i++) bayt[i] = ham.charCodeAt(i);
  return bayt;
}

async function jetonDogrula(jeton, istemciKimligi) {
  const parca = String(jeton || "").split(".");
  if (parca.length !== 3) return null;

  let bas;
  try {
    bas = JSON.parse(new TextDecoder().decode(b64urlCoz(parca[0])));
  } catch { return null; }
  if (bas.alg !== "RS256") return null;

  /* Anahtar bulunamazsa onbellek BIR KEZ tazeleniyor. Sonsuz denemek
     bir hata durumunda Google'a istek yagdirirdi. */
  let anahtarlar = await googleAnahtarlari();
  let jwk = anahtarlar.find((k) => k.kid === bas.kid);
  if (!jwk) {
    anahtarlar = await googleAnahtarlari(true);
    jwk = anahtarlar.find((k) => k.kid === bas.kid);
  }
  if (!jwk) return null;

  const anahtar = await crypto.subtle.importKey(
    "jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["verify"]);

  const imza = b64urlCoz(parca[2]);
  const govde = new TextEncoder().encode(parca[0] + "." + parca[1]);
  if (!await crypto.subtle.verify("RSASSA-PKCS1-v1_5", anahtar, imza, govde)) {
    return null;
  }

  let i;
  try {
    i = JSON.parse(new TextDecoder().decode(b64urlCoz(parca[1])));
  } catch { return null; }

  if (!GOOGLE_ISS.includes(i.iss)) return null;
  if (i.aud !== istemciKimligi) return null;
  if (!i.exp || Number(i.exp) <= damga()) return null;
  /* `email_verified` string gelebiliyor. Google dogrulamamis bir
     e-postayla hesap acmak, o e-postanin sahibinin hesabini baskasina
     vermek olurdu. */
  if (i.email_verified !== true && i.email_verified !== "true") return null;
  if (!i.email || !i.sub) return null;
  return i;
}

/* Istemci kimligi YAPILANDIRILMAMISSA ozellik KAPALI.
   Sayfa bu uca soruyor; bos donerse Google dugmesi HIC basilmiyor.
   Yarim yapilandirmayla calisan bir giris dugmesi, tiklayinca hata
   veren bir dugmedir. */
function googleAyar(env) {
  return yanit({ istemci: env.GOOGLE_ISTEMCI_KIMLIGI || "" }, 200,
    { "cache-control": "public, max-age=300" });
}

async function googleGiris(istek, env) {
  const db = env.DB;
  const istemciKimligi = env.GOOGLE_ISTEMCI_KIMLIGI || "";
  if (!istemciKimligi) return hata("Google girişi yapılandırılmamış.", 503);

  const g = await istek.json().catch(() => ({}));
  const bilgi = await jetonDogrula(g.jeton, istemciKimligi);
  if (!bilgi) return hata("Google doğrulaması başarısız.", 401);

  const eposta = String(bilgi.email).toLowerCase().slice(0, 254);
  const ad = metinKirp(bilgi.name || eposta.split("@")[0], 80);
  const googleId = String(bilgi.sub).slice(0, 64);

  let u = await db.prepare(
    "SELECT id, ad, eposta, rol, durum FROM uye WHERE google_id = ?",
  ).bind(googleId).first();

  if (!u) {
    /* E-POSTAYLA ESLESTIRME. Ayni e-postayla daha once parolayla
       kayit olmus bir hesap varsa IKINCI hesap acilmiyor, mevcut
       hesaba baglaniyor.

       Bu guvenli cunku Google `email_verified` diyor: kisi o
       e-postanin sahibi oldugunu Google'a kanitlamis. Aksi halde
       ayni kisi iki ayri hesapla iki ayri yazi gecmisine sahip
       olurdu.

       Beklemede kalmis hesap da ETKINLESIYOR: e-posta dogrulamasinin
       amaci tam olarak buydu ve Google onu zaten yapti. */
    const mevcut = await db.prepare(
      "SELECT id, ad, eposta, rol, durum FROM uye WHERE eposta = ?",
    ).bind(eposta).first();

    if (mevcut) {
      if (mevcut.durum === "askida") return hata("Hesabınız askıya alınmış.", 403);
      await db.prepare(
        "UPDATE uye SET google_id = ?, durum = 'etkin' WHERE id = ?",
      ).bind(googleId, mevcut.id).run();
      u = { ...mevcut, durum: "etkin" };
    } else {
      /* Parola alani BOS: bu hesabin parolasi yok. `parolaDogrula`
         "pbkdf2$..." bicimini sarti kostugu icin bos deger hicbir
         parolayla eslesmiyor -- yani parolayla girise KAPALI. */
      const y = await db.prepare(
        "INSERT INTO uye (eposta, ad, parola_ozet, durum, rol, google_id, kayit_ani)" +
        " VALUES (?, ?, '', 'etkin', 'yazar', ?, ?)",
      ).bind(eposta, ad, googleId, simdi()).run();
      const yeniId = y.meta && y.meta.last_row_id;
      u = { id: yeniId, ad, eposta, rol: "yazar", durum: "etkin" };
    }
  }

  if (u.durum === "askida") return hata("Hesabınız askıya alınmış.", 403);

  const jeton = await oturumAc(db, u.id);
  await db.prepare("UPDATE uye SET son_giris = ? WHERE id = ?")
    .bind(simdi(), u.id).run();

  return yanit(
    { tamam: true, uye: { ad: u.ad, eposta: u.eposta, rol: u.rol } },
    200,
    { "set-cookie": cerezYaz(jeton, OTURUM_GUN) },
  );
}

/* --------------------------------------------------------------- dogrulama */

/* E-posta gonderimi SAGLAYICI ANAHTARI varsa yapilir.
 *
 * Anahtar yokken hesap acilmiyor da degil, sessizce etkinlestiriliyor da
 * degil: "beklemede" kaliyor ve dogrulama baglantisi YONETICI PANELINDE
 * gorunuyor. Boylece sistem anahtar olmadan da calisiyor ve anahtar
 * eklendiginde kod degismeden otomatige geciyor.
 */
async function dogrulamaGonder(env, eposta, ad, baglanti) {
  if (!env.RESEND_API_KEY) return { gonderildi: false, sebep: "anahtar yok" };
  try {
    const y = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.POSTA_GONDEREN || "Netaris <onboarding@resend.dev>",
        to: [eposta],
        subject: "Netaris hesabınızı doğrulayın",
        text:
          `Merhaba ${ad},\n\n` +
          `Netaris hesabınızı etkinleştirmek için aşağıdaki bağlantıya gidin:\n\n` +
          `${baglanti}\n\n` +
          `Bağlantı 24 saat geçerlidir. Bu kaydı siz yapmadıysanız bu iletiyi ` +
          `yok sayabilirsiniz; hesap etkinleşmez.\n`,
      }),
    });
    return { gonderildi: y.ok, sebep: y.ok ? "" : `HTTP ${y.status}` };
  } catch (e) {
    return { gonderildi: false, sebep: String(e).slice(0, 120) };
  }
}

/* --------------------------------------------------------------------- uclar */

async function kayit(istek, env) {
  const db = env.DB;
  const g = await istek.json().catch(() => ({}));
  const eposta = metinKirp(g.eposta, 254).toLowerCase();
  const ad = metinKirp(g.ad, 80);
  const parola = typeof g.parola === "string" ? g.parola : "";

  if (!epostaGecerli(eposta)) return hata("Geçerli bir e-posta adresi girin.");
  if (ad.length < 2) return hata("Adınızı yazın.");
  if (parola.length < 10) {
    return hata("Parola en az 10 karakter olmalı.");
  }
  if (parola.length > 200) return hata("Parola çok uzun.");

  const ip = istek.headers.get("cf-connecting-ip") || "?";
  if (await denemeArtir(db, `kayit:${ip}`, 3600, 5)) {
    return hata("Çok fazla kayıt denemesi. Bir saat sonra tekrar deneyin.", 429);
  }

  const varOlan = await db.prepare("SELECT id FROM uye WHERE eposta = ?")
    .bind(eposta).first();
  /* Hesap varsa da AYNI yaniti veriyoruz. Farkli yanit vermek, siteye
     kimin uye oldugunu sorgulamaya izin verirdi. */
  if (varOlan) {
    return yanit({ tamam: true, mesaj: "Doğrulama adımı için e-postanızı kontrol edin." });
  }

  /* POSTA GONDERILEMIYORSA UYE DOGRUDAN ETKIN.
     -------------------------------------------
     OLCULDU: `RESEND_API_KEY` tanimli degil, dolayisiyla dogrulama
     e-postasi HIC gonderilmiyordu. Uye `beklemede` durumunda
     takiliyor, dogrulama baglantisini goremiyor ve giris yapamiyordu.
     Uc uyenin sifiri onayliydi.

     Sistem bunu "yonetici onayina duser" diye tarifliyordu ama o onay
     bir yere GITMIYORDU: ne posta var ne panel bildirimi. Yani kayit
     olan herkes sessizce olu bir kuyruga giriyordu -- kullanicinin
     "onay bana geliyor" dedigi sey aslinda hicbir yere gelmiyordu.

     ODUNU ACIKCA YAZIYORUM: e-posta dogrulamasi olmadan adresin
     gercekten kayit olana ait oldugu bilinmiyor. Bunu kabul
     edilebilir kilan iki sey var:
       1. Google ile giris zaten DOGRULANMIS adres veriyor ve asil
          yol o (uc uyenin ikisi oradan geldi).
       2. Icerik ayri bir kapida: senaryo ve yazi `taslak ->
          incelemede -> yayimlandi` surecinden geciyor. Uye olmak
          yayimlamak demek degil.

     Anahtar SONRADAN tanimlanirsa akis kendiliginde eski haline
     donuyor: posta gonderilebiliyorsa `beklemede` yaziliyor. */
  const jeton = rastgele(24);
  const postaVar = Boolean(env.RESEND_API_KEY);
  await db.prepare(
    "INSERT INTO uye (eposta, ad, parola_ozet, durum, rol, " +
    "dogrulama_ozeti, dogrulama_biter, kayit_ani) " +
    "VALUES (?, ?, ?, ?, 'yazar', ?, ?, ?)",
  ).bind(
    eposta, ad, await parolaOzetle(parola),
    postaVar ? "beklemede" : "etkin",
    await sha256(jeton), damga() + 86400, simdi(),
  ).run();

  const taban = new URL(istek.url).origin;
  const baglanti = `${taban}/api/dogrula?j=${jeton}&e=${encodeURIComponent(eposta)}`;
  const posta = postaVar
    ? await dogrulamaGonder(env, eposta, ad, baglanti)
    : { gonderildi: false, sebep: "posta kapali -- uye dogrudan etkin" };

  return yanit({
    tamam: true,
    /* MESAJ GERCEGI SOYLUYOR.
       Once posta gonderilemedigi durumda "yonetici onayindan sonra
       etkinlesecek" yaziyordu -- ama boyle bir onay adimi YOKTU ve
       kimseye bildirim gitmiyordu. Kullaniciya olmayan bir sureci
       beklettik. Artik hesap dogrudan etkin ve mesaj bunu soyluyor. */
    mesaj: posta.gonderildi
      ? "Doğrulama bağlantısı e-postanıza gönderildi."
      : "Kaydınız tamamlandı. Giriş yapabilirsiniz.",
    posta: posta.gonderildi,
  });
}

async function dogrula(istek, env) {
  const u = new URL(istek.url);
  const jeton = u.searchParams.get("j") || "";
  const eposta = (u.searchParams.get("e") || "").toLowerCase();
  const kayitli = await env.DB.prepare(
    "SELECT id, dogrulama_ozeti, dogrulama_biter FROM uye " +
    "WHERE eposta = ? AND durum = 'beklemede'",
  ).bind(eposta).first();

  const gecerli =
    kayitli &&
    kayitli.dogrulama_ozeti === (await sha256(jeton)) &&
    kayitli.dogrulama_biter > damga();

  if (!gecerli) {
    return Response.redirect(`${u.origin}/giris/?durum=dogrulama-gecersiz`, 302);
  }
  await env.DB.prepare(
    "UPDATE uye SET durum = 'etkin', dogrulama_ozeti = NULL, " +
    "dogrulama_biter = NULL WHERE id = ?",
  ).bind(kayitli.id).run();
  return Response.redirect(`${u.origin}/giris/?durum=dogrulandi`, 302);
}

async function giris(istek, env) {
  const db = env.DB;
  const g = await istek.json().catch(() => ({}));
  const eposta = metinKirp(g.eposta, 254).toLowerCase();
  const parola = typeof g.parola === "string" ? g.parola : "";
  if (!eposta || !parola) return hata("E-posta ve parola gerekli.");

  if (await denemeArtir(db, `giris:${eposta}`, 900, 8)) {
    return hata("Çok fazla başarısız deneme. 15 dakika sonra tekrar deneyin.", 429);
  }

  const u = await db.prepare(
    "SELECT id, ad, eposta, rol, durum, parola_ozet FROM uye WHERE eposta = ?",
  ).bind(eposta).first();

  /* Kullanici yoksa da PBKDF2 calistiriyoruz. Aksi halde yanit suresi
     "bu e-posta kayitli mi" sorusunu cevaplardi. */
  const dogru = u
    ? await parolaDogrula(parola, u.parola_ozet)
    : await parolaDogrula(parola, `pbkdf2$${PBKDF2_DONGU}$0$0`);

  /* Google ile acilmis hesabin parolasi YOK (`parola_ozet` bos).
     "E-posta veya parola hatalı" demek burada okuru yaniltirdi --
     parolasi yanlis degil, HIC yok. Kullanicinin ne yapacagini
     bilmesi, saldirganin ogrendigi seyden onemli; ustelik e-postanin
     kayitli oldugu zaten "Google ile girin" mesajindan anlasiliyor
     ve bu bilgi kayit formunda da elde edilebiliyor. */
  if (u && !u.parola_ozet) {
    return hata("Bu hesap Google ile açılmış. Google ile giriş yapın.", 409);
  }
  if (!u || !dogru) return hata("E-posta veya parola hatalı.", 401);
  if (u.durum === "askida") return hata("Hesabınız askıya alınmış.", 403);
  if (u.durum !== "etkin") {
    return hata("Hesabınız henüz doğrulanmadı.", 403);
  }

  await denemeSifirla(db, `giris:${eposta}`);
  const jeton = await oturumAc(db, u.id);
  await db.prepare("UPDATE uye SET son_giris = ? WHERE id = ?")
    .bind(simdi(), u.id).run();

  return yanit(
    { tamam: true, uye: { ad: u.ad, eposta: u.eposta, rol: u.rol } },
    200,
    { "set-cookie": cerezYaz(jeton, OTURUM_GUN) },
  );
}

async function cikis(istek, env) {
  const jeton = cerezOku(istek, OTURUM_CEREZ);
  if (jeton) {
    await env.DB.prepare("DELETE FROM oturum WHERE jeton_ozeti = ?")
      .bind(await sha256(jeton)).run();
  }
  return yanit({ tamam: true }, 200, { "set-cookie": cerezSil() });
}

async function ben(istek, env) {
  const u = await uyeBul(istek, env.DB);
  return u
    ? yanit({ uye: { ad: u.ad, eposta: u.eposta, rol: u.rol } })
    : yanit({ uye: null }, 401);
}

/* ---------------------------------------------------------------- yazilar */

async function yaziListe(istek, env, u) {
  const s = await env.DB.prepare(
    "SELECT id, baslik, ozet, kategori, durum, ret_nedeni, slug, " +
    "olusma, guncelleme FROM yazi WHERE uye_id = ? ORDER BY guncelleme DESC LIMIT 100",
  ).bind(u.id).all();
  return yanit({ yazilar: s.results || [] });
}

async function yaziKaydet(istek, env, u) {
  const g = await istek.json().catch(() => ({}));
  const baslik = metinKirp(g.baslik, EN_COK_BASLIK);
  const ozet = metinKirp(g.ozet, EN_COK_OZET);
  const govde = metinKirp(g.govde, EN_COK_GOVDE);
  const kategori = KATEGORILER.includes(g.kategori) ? g.kategori : KATEGORILER[0];
  const gonder = g.gonder === true;

  if (baslik.length < 8) return hata("Başlık en az 8 karakter olmalı.");
  if (gonder && govde.length < EN_AZ_GOVDE) {
    return hata(`Gönderim için metin en az ${EN_AZ_GOVDE} karakter olmalı.`);
  }

  const durum = gonder ? "incelemede" : "taslak";
  const t = simdi();

  if (g.id) {
    const v = await env.DB.prepare(
      "SELECT id, durum FROM yazi WHERE id = ? AND uye_id = ?",
    ).bind(g.id, u.id).first();
    if (!v) return hata("Yazı bulunamadı.", 404);
    /* Yayimlanmis ya da incelemedeki yazi yazar tarafindan degistirilemez:
       moderasyondan gecen metinle yayimlanan metin ayni olmali. */
    if (v.durum === "yayimlandi" || v.durum === "incelemede") {
      return hata("İncelemedeki veya yayımlanmış yazı düzenlenemez.", 409);
    }
    await env.DB.prepare(
      "UPDATE yazi SET baslik = ?, ozet = ?, govde = ?, kategori = ?, " +
      "durum = ?, ret_nedeni = NULL, guncelleme = ?, " +
      "gonderim = CASE WHEN ? = 'incelemede' THEN ? ELSE gonderim END " +
      "WHERE id = ? AND uye_id = ?",
    ).bind(baslik, ozet, govde, kategori, durum, t, durum, t, g.id, u.id).run();
    return yanit({ tamam: true, id: g.id, durum });
  }

  const s = await env.DB.prepare(
    "INSERT INTO yazi (uye_id, baslik, ozet, govde, kategori, durum, " +
    "olusma, guncelleme, gonderim) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
  ).bind(u.id, baslik, ozet, govde, kategori, durum, t, t,
         gonder ? t : null).run();
  return yanit({ tamam: true, id: s.meta.last_row_id, durum });
}

async function yaziGetir(env, u, id) {
  const y = await env.DB.prepare(
    "SELECT * FROM yazi WHERE id = ? AND uye_id = ?",
  ).bind(id, u.id).first();
  return y ? yanit({ yazi: y }) : hata("Yazı bulunamadı.", 404);
}

async function yaziSil(env, u, id) {
  const y = await env.DB.prepare(
    "SELECT durum FROM yazi WHERE id = ? AND uye_id = ?",
  ).bind(id, u.id).first();
  if (!y) return hata("Yazı bulunamadı.", 404);
  if (y.durum === "yayimlandi") {
    return hata("Yayımlanmış yazı silinemez. Kaldırma talebi için iletişime geçin.", 409);
  }
  await env.DB.prepare("DELETE FROM yazi WHERE id = ? AND uye_id = ?")
    .bind(id, u.id).run();
  return yanit({ tamam: true });
}

/* --------------------------------------------------------------- yonetim */

async function yonetimOzet(env) {
  const bekleyenUye = await env.DB.prepare(
    "SELECT id, eposta, ad, kayit_ani FROM uye WHERE durum = 'beklemede' " +
    "ORDER BY kayit_ani DESC LIMIT 50",
  ).all();
  const bekleyenYazi = await env.DB.prepare(
    "SELECT y.id, y.baslik, y.ozet, y.kategori, y.gonderim, y.guvenlik_notu, " +
    "u.ad AS yazar, u.eposta FROM yazi y JOIN uye u ON u.id = y.uye_id " +
    "WHERE y.durum = 'incelemede' ORDER BY y.gonderim ASC LIMIT 50",
  ).all();
  const bekleyenSenaryo = await env.DB.prepare(
    "SELECT s.id, s.capa, s.capa_baslik, s.kosul, s.sonuc, s.gerekce, " +
    "s.ufuk, s.gonderim, u.ad AS yazar, u.eposta FROM senaryo s " +
    "JOIN uye u ON u.id = s.uye_id WHERE s.durum = 'incelemede' " +
    "ORDER BY s.gonderim ASC LIMIT 50",
  ).all();
  return yanit({
    uyeler: bekleyenUye.results || [],
    yazilar: bekleyenYazi.results || [],
    senaryolar: bekleyenSenaryo.results || [],
  });
}

async function yonetimKarar(istek, env) {
  const g = await istek.json().catch(() => ({}));
  const id = Number(g.id);
  if (!id) return hata("id gerekli.");

  if (g.tur === "uye") {
    if (!["etkin", "askida"].includes(g.durum)) return hata("Geçersiz durum.");
    await env.DB.prepare(
      "UPDATE uye SET durum = ?, dogrulama_ozeti = NULL WHERE id = ?",
    ).bind(g.durum, id).run();
    return yanit({ tamam: true });
  }

  if (g.tur === "yazi") {
    if (!["onaylandi", "reddedildi", "taslak"].includes(g.durum)) {
      return hata("Geçersiz durum.");
    }
    await env.DB.prepare(
      "UPDATE yazi SET durum = ?, ret_nedeni = ?, guncelleme = ? WHERE id = ?",
    ).bind(g.durum, metinKirp(g.neden, 400) || null, simdi(), id).run();
    return yanit({ tamam: true });
  }

  if (g.tur === "senaryo") {
    /* Senaryo YAZIDAN FARKLI: onaydan sonra ayri bir yayin adimi yok.
       Yazi, statik siteye dosya olarak uretiliyor ve o yuzden
       "onaylandi" ile "yayimlandi" ayri; senaryo ise haber sayfasina
       canli uctan geliyor, onaylandigi anda gorunur oluyor. */
    if (!["yayimlandi", "reddedildi", "taslak"].includes(g.durum)) {
      return hata("Geçersiz durum.");
    }
    const t = simdi();
    /* Ufuk saati YAYINDA baslatiliyor: incelemede bekleyen sure yazarin
       hanesine yazilmamali. Bitis tarihi icin senaryonun UFUK degeri
       lazim, o yuzden once okunuyor -- SQL ifadesinin icinde
       hesaplanamaz. */
    let biter = null;
    if (g.durum === "yayimlandi") {
      const v = await env.DB.prepare(
        "SELECT ufuk FROM senaryo WHERE id = ?",
      ).bind(id).first();
      if (!v) return hata("Senaryo bulunamadı.", 404);
      biter = ufukBitisi(v.ufuk) || ufukBitisi("3 ay");
    }
    await env.DB.prepare(
      "UPDATE senaryo SET durum = ?, ret_nedeni = ?, guncelleme = ?, " +
      "yayin = COALESCE(?, yayin), ufuk_biter = COALESCE(?, ufuk_biter) " +
      "WHERE id = ?",
    ).bind(g.durum, metinKirp(g.neden, 400) || null, t,
           g.durum === "yayimlandi" ? t : null, biter, id).run();
    return yanit({ tamam: true });
  }
  return hata("Geçersiz tür.");
}

/* Yayin hattinin (GitHub Actions) cektigi uc.
 *
 * Oturum cerezi degil PAYLASILAN SIR ile korunuyor: cagiran bir tarayici
 * degil, bir betik. Sir yoksa uc TAMAMEN kapali -- yanlislikla acik
 * kalmasindansa hic calismamasi dogru.
 */
async function disariAktar(istek, env) {
  if (!env.HAT_SIRRI) return hata("Uç kapalı.", 503);
  const verilen = istek.headers.get("x-netaris-sir") || "";
  const a = await sha256(verilen);
  const b = await sha256(env.HAT_SIRRI);
  if (a !== b) return hata("Yetkisiz.", 401);

  const s = await env.DB.prepare(
    "SELECT y.id, y.baslik, y.ozet, y.govde, y.kategori, y.gonderim, " +
    "u.ad AS yazar FROM yazi y JOIN uye u ON u.id = y.uye_id " +
    "WHERE y.durum = 'onaylandi' ORDER BY y.gonderim ASC LIMIT 20",
  ).all();
  return yanit({ yazilar: s.results || [] });
}

async function yayimlandiIsaretle(istek, env) {
  if (!env.HAT_SIRRI) return hata("Uç kapalı.", 503);
  const a = await sha256(istek.headers.get("x-netaris-sir") || "");
  const b = await sha256(env.HAT_SIRRI);
  if (a !== b) return hata("Yetkisiz.", 401);

  const g = await istek.json().catch(() => ({}));
  const kayitlar = Array.isArray(g.kayitlar) ? g.kayitlar.slice(0, 50) : [];
  for (const k of kayitlar) {
    await env.DB.prepare(
      "UPDATE yazi SET durum = ?, slug = ?, guvenlik_notu = ?, yayin = ? " +
      "WHERE id = ?",
    ).bind(
      k.yayimlandi ? "yayimlandi" : "reddedildi",
      metinKirp(k.slug, 120) || null,
      metinKirp(k.not, 600) || null,
      simdi(), Number(k.id),
    ).run();
  }
  return yanit({ tamam: true, sayi: kayitlar.length });
}


/* CAPA HABERININ GORSELI -- paylasim karti icin.
   ---------------------------------------------
   Senaryo sayfasinda `og:image` YOKTU ve X/LinkedIn kucuk kart
   ("summary") gosteriyordu: gorselsiz, dar, dikkat cekmeyen.
   Kullanicinin kendi senaryosunu paylasmasi buyume motorunun ilk
   halkasi; gorselsiz bir kart o halkayi bastan kiriyor.

   GORSEL URETMIYORUZ. Kisiye ozel kart cizmek ya yeni bir bagimlilik
   (Pillow) ya da ucretli bir servis ister; ikisi de bu asamada gereksiz.
   Bunun yerine senaryonun BAGLI OLDUGU haberin gorseli kullaniliyor --
   zaten o haber icin secilmis, lisansi denetlenmis bir gorsel.

   Sema DEGISMIYOR: worker capa sayfasini zaten sunabiliyor, oradan
   `og:image` okunuyor. Mevcut senaryolar icin de calisiyor.

   Bulunamazsa bos donuyor ve kart "summary"de kaliyor -- uydurma bir
   gorsel koymaktansa kucuk kart daha durust. */
async function capaGorseli(env, capa, capaTur) {
  if (capaTur !== "haber" || !capa || !capa.startsWith("/haber/")) return "";
  try {
    const y = await env.ASSETS.fetch(
      new Request("https://netaris.net" + capa, { method: "GET" }));
    if (!y.ok) return "";
    const m = (await y.text()).match(
      /<meta property="og:image" content="([^"]+)"/);
    return m ? m[1] : "";
  } catch (e) {
    return "";   /* capa silinmis olabilir; kart gorselsiz kalir */
  }
}

/* --------------------------------------------------------------- senaryolar */

/* Senaryo = kullanicinin KOSULLU onermesi.
   Sitenin resmi veri / kullanici gorusu ayriminin somut hali. */

function ufukBitisi(ufuk) {
  const gun = UFUKLAR[ufuk];
  if (!gun) return null;
  const d = new Date(Date.now() + gun * 86400000);
  return d.toISOString().slice(0, 10);
}

async function senaryoKaydet(istek, env, u) {
  const g = await istek.json().catch(() => ({}));
  const kosul = metinKirp(g.kosul, EN_COK_KOSUL);
  const sonuc = metinKirp(g.sonuc, EN_COK_SONUC);
  const gerekce = metinKirp(g.gerekce, EN_COK_GEREKCE);
  /* CURUTME KOSULU -- bir senaryoyu bir GORUSTEN ayiran tek sey.
     Yazarin kendi kendini yanlislayabilecek gelismeyi ONCEDEN
     yazmasi. Onu yazmayan metin her sonucta hakli cikar.

     ZORUNLU DEGIL: zorunlu kilmak kisa ve gecerli senaryolari
     disarida birakirdi. Bos birakilirsa sayfada bolum gorunmuyor. */
  const curutme = metinKirp(g.curutme, EN_COK_CURUTME);
  const kaynaklar = metinKirp(g.kaynaklar, EN_COK_KAYNAK);
  const capa = metinKirp(g.capa, 240);
  const capaBaslik = metinKirp(g.capa_baslik, EN_COK_BASLIK);
  const capaTur = CAPA_TURLERI.includes(g.capa_tur) ? g.capa_tur : "haber";
  const ufuk = UFUKLAR[g.ufuk] ? g.ufuk : "3 ay";
  /* OLCULEBILIR TETIKLEYICI -- UCU BIRLIKTE gecerli olmali.
     Yarim bir tetikleyici hic tetikleyici olmamasindan KOTUDUR:
     kullanici "ayarladim" saniyor ama senaryo ufku dolunca yine
     'belirsiz' cikiyor. Ucu de yoksa ucu de null yaziliyor. */
  const olcutEsik = Number(g.olcut_esik);
  const olcutTam = OLCUT_KODLARI.includes(g.olcut_kod)
                && OLCUT_YONLERI.includes(g.olcut_yon)
                && Number.isFinite(olcutEsik);
  const olcutKod = olcutTam ? g.olcut_kod : null;
  const olcutYon = olcutTam ? g.olcut_yon : null;
  const olcutDeger = olcutTam ? olcutEsik : null;
  const gonder = g.gonder === true;

  if (kosul.length < EN_AZ_KOSUL) {
    return hata("Koşul en az " + EN_AZ_KOSUL + " karakter olmalı.");
  }
  if (sonuc.length < EN_AZ_KOSUL) {
    return hata("Beklenen sonuç en az " + EN_AZ_KOSUL + " karakter olmalı.");
  }
  if (!capa) return hata("Senaryo bir habere ya da konuya bağlı olmalı.");

  const durum = gonder ? "incelemede" : "taslak";
  const t = simdi();
  /* Ufuk saati GONDERIMDE isliyor, taslak yazilirken degil: aylarca
     taslakta bekleyen bir senaryonun suresi dolmus olarak yayimlanmasi
     anlamsiz olurdu. */
  const biter = gonder ? ufukBitisi(ufuk) : null;

  if (g.id) {
    const v = await env.DB.prepare(
      "SELECT id, durum FROM senaryo WHERE id = ? AND uye_id = ?",
    ).bind(g.id, u.id).first();
    if (!v) return hata("Senaryo bulunamadı.", 404);
    /* Yayimlanmis senaryo DEGISTIRILEMEZ. Bu, senaryo fikrinin
       tamami: sonradan duzeltilebilen bir onerme denetlenemez. */
    if (v.durum === "yayimlandi" || v.durum === "incelemede") {
      return hata("İncelemedeki veya yayımlanmış senaryo düzenlenemez.", 409);
    }
    await env.DB.prepare(
      "UPDATE senaryo SET kosul = ?, sonuc = ?, gerekce = ?, ufuk = ?, " +
      "ufuk_biter = COALESCE(?, ufuk_biter), durum = ?, ret_nedeni = NULL, " +
      "olcut_kod = ?, olcut_yon = ?, olcut_esik = ?, " +
      "curutme = ?, kaynaklar = ?, " +
      "guncelleme = ?, gonderim = CASE WHEN ? = 'incelemede' THEN ? " +
      "ELSE gonderim END WHERE id = ? AND uye_id = ?",
    ).bind(kosul, sonuc, gerekce, ufuk, biter, durum,
           olcutKod, olcutYon, olcutDeger, curutme, kaynaklar,
           t, durum, t, g.id, u.id).run();
    return yanit({ tamam: true, id: g.id, durum });
  }

  const s = await env.DB.prepare(
    "INSERT INTO senaryo (uye_id, capa_tur, capa, capa_baslik, kosul, " +
    "sonuc, gerekce, ufuk, ufuk_biter, durum, olcut_kod, olcut_yon, " +
    "olcut_esik, curutme, kaynaklar, olusma, guncelleme, gonderim) " +
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
  ).bind(u.id, capaTur, capa, capaBaslik, kosul, sonuc, gerekce, ufuk,
         biter, durum, olcutKod, olcutYon, olcutDeger,
         curutme, kaynaklar, t, t, gonder ? t : null).run();
  return yanit({ tamam: true, id: s.meta.last_row_id, durum });
}

async function senaryoListe(env, u) {
  const r = await env.DB.prepare(
    "SELECT id, capa, capa_baslik, kosul, sonuc, ufuk, ufuk_biter, durum, " +
    "ret_nedeni, sonuclanma, olusma FROM senaryo WHERE uye_id = ? " +
    "ORDER BY id DESC LIMIT 100",
  ).bind(u.id).all();
  return yanit({ senaryolar: r.results || [] });
}

async function senaryoSil(env, u, id) {
  const v = await env.DB.prepare(
    "SELECT durum FROM senaryo WHERE id = ? AND uye_id = ?",
  ).bind(id, u.id).first();
  if (!v) return hata("Senaryo bulunamadı.", 404);
  if (v.durum === "yayimlandi") {
    return hata("Yayımlanmış senaryo silinemez.", 409);
  }
  await env.DB.prepare("DELETE FROM senaryo WHERE id = ? AND uye_id = ?")
    .bind(id, u.id).run();
  return yanit({ tamam: true });
}

/* HERKESE ACIK. Haber sayfasi bu ucu cagirip yayimlanmis senaryolari
   listeliyor. Yalnizca `yayimlandi` donuyor; taslak ve incelemedeki
   hicbir sekilde disari cikmiyor. */
async function senaryoAcik(istek, env) {
  const u = new URL(istek.url);
  const capa = (u.searchParams.get("capa") || "").slice(0, 240);
  if (!capa) return hata("Çapa gerekli.");
  /* Oy sayisi ve okurun kendi oyu birlikte donuyor: iki istek yerine
     bir istek, ve dugme dogru durumda aciliyor. */
  const uye = await uyeBul(istek, env.DB);
  const r = await env.DB.prepare(
    "SELECT s.id, s.kosul, s.sonuc, s.gerekce, s.ufuk, s.ufuk_biter, " +
    "s.yayin, s.sonuclanma, u.ad AS yazar, " +
    "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id) AS oy, " +
    "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id " +
    " AND o.uye_id = ?) AS benim " +
    "FROM senaryo s JOIN uye u ON u.id = s.uye_id " +
    "WHERE s.capa = ? AND s.durum = 'yayimlandi' " +
    /* EN COK OY ALAN USTTE. Yayin sirasi ikincil olcut: ayni oyu alan
       iki senaryodan yeni olan once. */
    "ORDER BY oy DESC, s.yayin DESC LIMIT 20",
  ).bind(uye ? uye.id : 0, capa).all();
  return yanit(
    { senaryolar: r.results || [], oturum: !!uye },
    200,
    /* Oturuma gore degistigi icin ONBELLEKLENMEZ. Onceki surumde
       120 saniyelik ortak onbellek vardi ve bir okurun oy durumu
       digerine gorunebilirdi. */
    { "cache-control": "no-store" });
}

/* Oy ver / geri al. Ayni uc ikisini de yapiyor -- dugme bir anahtar,
   iki ayri uc olsaydi istemci hangi durumda oldugunu tahmin etmek
   zorunda kalirdi. */
async function senaryoOy(env, uye, id) {
  const s = await env.DB.prepare(
    "SELECT durum FROM senaryo WHERE id = ?",
  ).bind(id).first();
  if (!s || s.durum !== "yayimlandi") {
    return hata("Senaryo bulunamadı.", 404);
  }
  const var_ = await env.DB.prepare(
    "SELECT 1 FROM senaryo_oy WHERE senaryo_id = ? AND uye_id = ?",
  ).bind(id, uye.id).first();

  if (var_) {
    await env.DB.prepare(
      "DELETE FROM senaryo_oy WHERE senaryo_id = ? AND uye_id = ?",
    ).bind(id, uye.id).run();
  } else {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO senaryo_oy (senaryo_id, uye_id, an)" +
      " VALUES (?, ?, ?)",
    ).bind(id, uye.id, simdi()).run();
  }
  const say = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM senaryo_oy WHERE senaryo_id = ?",
  ).bind(id).first();
  return yanit({ tamam: true, oy: say ? say.n : 0, benim: !var_ });
}

/* Ana sayfadaki "one cikan senaryolar". Herkese acik.
 *
 * EN AZ BIR OY SARTI: sifir oylu senaryo one cikarilamaz -- "one cikan"
 * demek bir SECIM demek, henuz kimsenin bakmadigi bir metni oyle
 * sunmak okuru yanıltır. */
/* ONE CIKANLAR -- SON 7 GUNDE ALINAN OYA gore.
 *
 * NEDEN PENCERE VAR
 * -----------------
 * Once pencere YOKTU ve siralama TUM ZAMANLARIN oyuna bakiyordu.
 * Sonucu su: alti ay once 20 oy almis bir senaryo sonsuza dek tepede
 * kalir, yeni yazilan hicbir senaryo onu geceMEZ. Liste bir kez
 * doldugunda donuyor.
 *
 * PENCERE YAYIN TARIHINE DEGIL, OYUN TARIHINE bakiyor
 * (`senaryo_oy.an`). Iki sonucu birden veriyor:
 *   * yeni senaryo bir haftada hizla yukselebiliyor,
 *   * eski ama yeniden ilgi goren senaryo geri donebiliyor
 *     -- gundem ona dondugunde okurun aradigi sey zaten odur.
 * Yayin tarihine bakilsaydi ikincisi imkansiz olurdu.
 *
 * SESSIZ HAFTA SORUNU. Pencerede hic oy yoksa bolum tamamen
 * bosalirdi; oysa bos "one cikan" basligi siteyi terk edilmis
 * gosteriyor (ayni sebeple bolum zaten gizleniyor). Bu yuzden
 * pencere bossa TUM ZAMANLAR siralamasina duşuluyor ve yanitta
 * `pencere: false` donuyor -- arayuz basligi ona gore yaziyor.
 * Iki farkli siralamayi ayni etiketle sunmak okuru yanıltırdı.
 *
 * DONEN SAYI, SIRALAMAYI URETEN SAYIDIR. Pencere modunda haftalik oy
 * gosteriliyor; toplam oy da ayri alanda var. Siralamayi aciklamayan
 * bir sayi basmak, okura yanlis gerekce sunmak olur.
 */
const ONE_CIKAN_GUN = 7;
const ONE_CIKAN_ADET = 6;

/* ---------------------------------------------------------------------
   GORUNTULENME VE BEGENI
   ---------------------------------------------------------------------
   NEDEN VAR
   Tasarim taslaginda her kartin altinda goruntulenme ve begeni sayisi
   duruyor. Site bunlari hic olcmuyordu. Uydurma bir sayi basmak bu
   sitede en agir ihlal olurdu, o yuzden once olcum kuruldu.

   YOL DOGRULAMASI SART
   `yol` istemciden geliyor. Dogrulanmazsa herkes istedigi anahtari
   yazar ve tablo cop olur. Kabul edilen bicim: `/` ile baslayan, tek
   egik cizgiyle ayrilmis, yalnizca kucuk harf/rakam/tire iceren, en
   fazla 160 karakterlik bir yol. Sorgu ve capa KABUL EDILMIYOR --
   ayni sayfa iki ayri satira yazilirdi.
--------------------------------------------------------------------- */

/** Kabul edilen sayfa yolu bicimi. */
const YOL_BICIMI = /^\/[a-z0-9\-\/]{1,158}\/$/;

/** Sayacin tutuldugu bolumler. Her sayfa degil: yalnizca ICERIK. */
const SAYILAN_KOK = ["/haber/", "/analiz/", "/olay/", "/varlik/",
                     "/makro/", "/teknik/", "/yorum/", "/arastirmalar/"];

function yolGecerli(yol) {
  if (typeof yol !== "string" || !YOL_BICIMI.test(yol)) return false;
  if (yol.indexOf("//") !== -1) return false;
  return SAYILAN_KOK.some((k) => yol.startsWith(k));
}

/* Toplu sorguda kac yol kabul edilir. Liste sayfasinda ekranda bu
   kadar kart oluyor; daha fazlasi tek istekte sorulmamali. */
const TOPLU_SINIR = 60;

/** POST /api/goruntulenme  {yol}  -> {goruntulenme}
 *
 *  OTURUM ISTEMIYOR: okurun cogu uye degil ve goruntulenme sayisi
 *  uyelige bagli olsaydi olcum sitenin kucuk bir dilimini gosterirdi.
 *
 *  TEKRAR SAYIMI ISTEMCIDE ONLENIYOR (`sayac.js`, gunde bir kez).
 *  Sunucuda IP tutulsaydi daha saglam olurdu; tutulmuyor cunku IP
 *  kisisel veri ve bir sayacin dogrulugu okurun izini tutmaya
 *  degmez. Bu yuzden sayi "tekil ziyaretci" degil ACILIS sayisi ve
 *  gizlilik beyaninda da boyle yaziyor.
 */
async function goruntulenmeArtir(istek, env) {
  let g;
  try {
    g = await istek.json();
  } catch (e) {
    return hata("Geçersiz istek.", 400);
  }
  const yol = g && g.yol;
  if (!yolGecerli(yol)) return hata("Geçersiz yol.", 400);

  await env.DB.prepare(
    "INSERT INTO sayac (yol, goruntulenme, guncelleme) VALUES (?, 1, ?)" +
    " ON CONFLICT(yol) DO UPDATE SET goruntulenme = goruntulenme + 1," +
    " guncelleme = excluded.guncelleme",
  ).bind(yol, simdi()).run();

  const r = await env.DB.prepare(
    "SELECT goruntulenme FROM sayac WHERE yol = ?",
  ).bind(yol).first();
  return yanit({ tamam: true, goruntulenme: r ? r.goruntulenme : 1 });
}

/** POST /api/sayaclar  {yollar:[...]}  -> {sayaclar:{yol:{g,b}}, benim:[...]}
 *
 *  Liste sayfasi tek istekte butun kartlarin sayisini aliyor. Kart
 *  basina ayri istek 20-40 istek demekti ve sayfa acilisini bozardi.
 *
 *  Oturum VARSA `benim` alani da doluyor: okur hangilerini
 *  begendigini gorur. Yoksa bos liste doner ve begeni dugmesi giris
 *  sayfasina goturur -- calismayan bir dugme, olmayan dugmeden kotudur.
 */
async function sayaclariGetir(istek, env) {
  let g;
  try {
    g = await istek.json();
  } catch (e) {
    return hata("Geçersiz istek.", 400);
  }
  const ham = (g && g.yollar) || [];
  if (!Array.isArray(ham)) return hata("Geçersiz istek.", 400);
  const yollar = [];
  for (const y of ham) {
    if (yolGecerli(y) && yollar.indexOf(y) === -1) yollar.push(y);
    if (yollar.length >= TOPLU_SINIR) break;
  }
  if (!yollar.length) return yanit({ sayaclar: {}, benim: [] });

  const soru = yollar.map(() => "?").join(",");
  const g1 = await env.DB.prepare(
    `SELECT yol, goruntulenme FROM sayac WHERE yol IN (${soru})`,
  ).bind(...yollar).all();
  const b1 = await env.DB.prepare(
    `SELECT yol, COUNT(*) AS n FROM begeni WHERE yol IN (${soru})` +
    " GROUP BY yol",
  ).bind(...yollar).all();

  const sayaclar = {};
  for (const y of yollar) sayaclar[y] = { g: 0, b: 0 };
  for (const r of (g1.results || [])) {
    if (sayaclar[r.yol]) sayaclar[r.yol].g = r.goruntulenme;
  }
  for (const r of (b1.results || [])) {
    if (sayaclar[r.yol]) sayaclar[r.yol].b = r.n;
  }

  let benim = [];
  const uye = await uyeBul(istek, env.DB);
  if (uye) {
    const m = await env.DB.prepare(
      `SELECT yol FROM begeni WHERE uye_id = ? AND yol IN (${soru})`,
    ).bind(uye.id, ...yollar).all();
    benim = (m.results || []).map((r) => r.yol);
  }
  return yanit({ sayaclar, benim });
}

/** POST /api/begeni  {yol}  -> {begeni, benim}
 *
 *  UYELIK SART. Anonim begeni sayilabilir bir sey degil: ayni kisi
 *  yuz kez basar ve sayi anlamini kaybeder. `senaryo_oy` ile ayni
 *  gerekce.
 */
async function begeniDegistir(istek, env, uye) {
  let g;
  try {
    g = await istek.json();
  } catch (e) {
    return hata("Geçersiz istek.", 400);
  }
  const yol = g && g.yol;
  if (!yolGecerli(yol)) return hata("Geçersiz yol.", 400);

  const var_ = await env.DB.prepare(
    "SELECT 1 FROM begeni WHERE yol = ? AND uye_id = ?",
  ).bind(yol, uye.id).first();

  if (var_) {
    await env.DB.prepare(
      "DELETE FROM begeni WHERE yol = ? AND uye_id = ?",
    ).bind(yol, uye.id).run();
  } else {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO begeni (yol, uye_id, an) VALUES (?, ?, ?)",
    ).bind(yol, uye.id, simdi()).run();
  }
  const say = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM begeni WHERE yol = ?",
  ).bind(yol).first();
  return yanit({ tamam: true, begeni: say ? say.n : 0, benim: !var_ });
}


async function senaryoOneCikan(env) {
  const esik = new Date(Date.now() - ONE_CIKAN_GUN * 86400000).toISOString();

  const HAFTALIK =
    "(SELECT COUNT(*) FROM senaryo_oy o" +
    " WHERE o.senaryo_id = s.id AND o.an >= ?)";
  const TOPLAM =
    "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id)";

  const alanlar =
    "SELECT s.id, s.kosul, s.sonuc, s.capa, s.capa_baslik, s.ufuk," +
    " u.ad AS yazar, " + TOPLAM + " AS oy_toplam";

  let r = await env.DB.prepare(
    alanlar + ", " + HAFTALIK + " AS oy" +
    " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
    " WHERE s.durum = 'yayimlandi' AND " + HAFTALIK + " > 0" +
    " ORDER BY oy DESC, s.yayin DESC LIMIT ?",
  ).bind(esik, esik, ONE_CIKAN_ADET).all();

  let pencere = true;
  if (!r.results || !r.results.length) {
    pencere = false;
    r = await env.DB.prepare(
      alanlar + ", " + TOPLAM + " AS oy" +
      " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
      " WHERE s.durum = 'yayimlandi' AND " + TOPLAM + " > 0" +
      " ORDER BY oy DESC, s.yayin DESC LIMIT ?",
    ).bind(ONE_CIKAN_ADET).all();
  }

  return yanit(
    { senaryolar: r.results || [], pencere, gun: ONE_CIKAN_GUN },
    200,
    /* Onbellek KISA: siralama oyla degisiyor ve okur oy verdikten
       sonra degisimi gormeli. Bes dakika, bir oyun listeye
       yansimasi icin uzun. */
    { "cache-control": "public, max-age=60" },
  );
}

/* Topluluk sayfasi: YAYIMLANMIS BUTUN senaryolar. Herkese acik.
 *
 * `senaryoOneCikan`dan farki OY SARTI YOK. Ikisi ayri soruyu
 * cevapliyor:
 *
 *   one-cikan  "topluluk neyi degerli buldu"  -> bir SECIM, oy gerekir
 *   hepsi      "topluluk ne yazdi"            -> bir KAYIT, oy gerekmez
 *
 * Sifir oylu senaryoyu "one cikan" diye sunmak okuru yanıltırdı; ama
 * hicbir yerde gostermemek soguk baslangic kilidi yaratiyordu -- kimse
 * gormedigi icin oy verilmiyor, oy verilmedigi icin gorunmuyor. Kayit
 * sayfasi o kilidi aciyor.
 *
 * Yeni yazilan senaryo ustte: "en yeni" siralamasi, kimsenin oy
 * vermedigi bir senaryoyu da gorunur kiliyor. */
async function senaryoHepsi(env) {
  const r = await env.DB.prepare(
    /* `s.id` PAYLASIM CAPASI icin: her senaryo `#senaryo-<id>`
       adresiyle dogrudan gosterilebiliyor. Sorguda yoktu ve capa
       "senaryo-undefined" olurdu. */
    "SELECT s.id, s.kosul, s.sonuc, s.capa, s.capa_baslik, s.ufuk, s.yayin," +
    " u.ad AS yazar," +
    " (SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id) AS oy" +
    " FROM senaryo s JOIN uye u ON u.id = s.uye_id" +
    " WHERE s.durum = 'yayimlandi'" +
    " ORDER BY s.yayin DESC LIMIT 60",
  ).all();
  return yanit({ senaryolar: r.results || [] }, 200,
    { "cache-control": "public, max-age=120" });
}

/* --------------------------------------------------------------- yonlendirme */


/* --------------------------------------------------------------------
   SENARYO SAYFASI  --  /senaryo/<id>/
   --------------------------------------------------------------------
   Senaryolar D1'de yasiyor ve site statik; bu yuzden sayfa DERLEME
   aninda uretilemiyor. Okur bir senaryoyu paylastiginda karsi tarafin
   acacagi bir adres olmali -- yoksa paylasim `/topluluk/` sayfasina
   gider ve okur hangi senaryodan bahsedildigini bulamaz.

   NEDEN SUNUCUDA URETILIYOR
   Istemci tarafinda cizilseydi `og:title` ve `og:description` bos
   kalirdi: X ve LinkedIn sayfayi JavaScript calistirmadan okuyor.
   Paylasim kartinin dolu gorunmesi icin etiketlerin ILK YANITTA
   bulunmasi gerekiyor.

   YALNIZCA YAYIMLANMIS SENARYO. Taslak ya da incelemedeki bir
   senaryonun adresi acilmiyor -- 404 doniyor ve statik dosyaya
   dusuyor. Yayimlanmamis icerigin adresten sizmasi, inceleme
   surecini anlamsiz kilardi.
-------------------------------------------------------------------- */

function kacir(m) {
  return String(m == null ? "" : m)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/* Ufuk metni: "3 ay" -> "3 ay icinde". Sonuclanmis senaryoda ufuk
   gecmis zamanla yaziliyor -- "3 ay icinde" demek, suresi dolmus bir
   senaryoyu hala acik gostermek olurdu. */
function ufukMetni(s) {
  if (s.sonuclanma) {
    const k = { gerceklesti: "gerçekleşti", gerceklesmedi: "gerçekleşmedi",
                belirsiz: "sonucu belirsiz kaldı" };
    return k[s.sonuclanma] || "süresi doldu";
  }
  return (s.ufuk || "3 ay") + " içinde";
}

/* PAYLASIM BLOGU -- SUNUCUDA URETILIYOR.
   ---------------------------------------
   Betiksiz de calisiyor: uc bag da dogrudan `<a>`, tiklama dinleyicisi
   degil. Orta tikla yeni sekmede acilir, saga tiklayip kopyalanir,
   ekran okuyucu ne oldugunu soyler.

   ONIZLEME KARTI okurun ne paylasacagini GOSTERIYOR. Promptun istegi
   bu: kullanici baglantiyi atmadan once sosyal agda nasil gorunecegini
   gormeli. Kart uydurma degil -- ayni baslik ve ozet `og:` etiketlerine
   de basiliyor, yani gosterdigi sey gercekten paylasilan sey.

   X ILE LINKEDIN AYNI CALISMIYOR: X `text` aliyor, LinkedIn'in
   `share-offsite` ucu YALNIZCA adres aliyor ve basligi sayfanin
   Open Graph etiketlerinden okuyor. Bu yuzden sayfanin sunucuda
   uretilmesi bu isin onkosuluydu. */
/* Paylasim ikonlari -- satir ici SVG.
   `_paylas.html` makrosuyla AYNI yollar. Iki yerde iki farkli
   ikon seti, sitenin ayni islevi iki yuzle gostermesi olurdu.
   Dis kaynaktan yuklemek ek istek, gizlilik (ikon sunucusu okuru
   gorur) ve betik bagimliligi getirir. */
const PAYLAS_IKON = {
  x: "M18.9 2H22l-7.3 8.3L23.3 22h-6.7l-5.2-6.9L5.4 22H2.3l7.8-8.9L1.1 2h6.9l4.7 6.3L18.9 2Zm-1.1 18h1.7L7.3 3.8H5.4L17.8 20Z",
  li: "M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9h4v12H3V9Zm7 0h3.8v1.7h.05c.53-1 1.83-2.05 3.76-2.05C21.4 8.65 22 11 22 14.1V21h-4v-6.1c0-1.45-.03-3.3-2-3.3-2 0-2.3 1.57-2.3 3.2V21h-4V9Z",
  wa: "M12 2a10 10 0 0 0-8.6 15l-1.3 4.7 4.8-1.3A10 10 0 1 0 12 2Zm5.6 14.2c-.24.67-1.4 1.28-1.93 1.33-.5.05-.98.23-3.3-.7-2.78-1.1-4.53-3.9-4.67-4.08-.13-.18-1.1-1.47-1.1-2.8 0-1.33.7-1.98.94-2.25.25-.27.54-.34.72-.34h.52c.17 0 .4-.06.62.48.23.55.78 1.9.85 2.04.07.13.11.29.02.47-.09.18-.13.29-.27.44l-.4.47c-.13.13-.27.28-.12.55.15.27.67 1.1 1.44 1.79.99.88 1.82 1.15 2.09 1.28.27.14.42.12.58-.07.16-.18.67-.78.85-1.05.18-.27.36-.22.6-.13.25.09 1.58.74 1.85.88.27.13.45.2.52.31.07.11.07.65-.17 1.32Z",
  tg: "M21.9 4.3 18.8 19c-.23 1.03-.85 1.28-1.72.8l-4.75-3.5-2.3 2.2c-.25.26-.47.48-.96.48l.34-4.83 8.8-7.95c.38-.34-.08-.53-.6-.19L6.75 12.7 2.1 11.25c-1-.32-1.03-1 .21-1.5L20.6 2.83c.84-.31 1.57.2 1.3 1.47Z",
  kopya: "M10.6 13.4a4 4 0 0 0 5.66 0l2.83-2.83a4 4 0 0 0-5.66-5.66l-1.4 1.42 1.41 1.41 1.42-1.41a2 2 0 1 1 2.83 2.83l-2.83 2.83a2 2 0 0 1-2.83 0l-1.41 1.41Zm2.83-2.83a4 4 0 0 0-5.66 0l-2.83 2.83a4 4 0 1 0 5.66 5.66l1.4-1.42-1.41-1.41-1.42 1.41a2 2 0 0 1-2.83-2.83l2.83-2.83a2 2 0 0 1 2.83 0l1.41-1.41Z",
};

function ikon(ad) {
  return '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" '
       + 'height="16"><path fill="currentColor" d="' + PAYLAS_IKON[ad]
       + '"/></svg>';
}

function paylasBlok(baslik, ozet, adres) {
  /* X siniri 280 karakter ve adres ~23 sayiliyor. Metin 200'e
     kirpiliyor; kirpilirsa uc nokta ile bitiyor. */
  const ozet200 = ozet.length > 200 ? ozet.slice(0, 199).trim() + "…" : ozet;
  const x = "https://x.com/intent/post?text=" + encodeURIComponent(ozet200)
          + "&url=" + encodeURIComponent(adres);
  const li = "https://www.linkedin.com/sharing/share-offsite/?url="
           + encodeURIComponent(adres);
  /* TELEGRAM VE WHATSAPP -- mobilde en cok kullanilan iki kanal.
     Ikisi de metni ve adresi AYRI parametre aliyor; tek bir metne
     birlestirmek uygulamada cift adres gosteriyor.

     WhatsApp'in `wa.me` ucu masaustunde web surumune, telefonda
     uygulamaya aciliyor -- ayri bir mobil/masaustu ayrimi gerekmiyor. */
  const tg = "https://t.me/share/url?url=" + encodeURIComponent(adres)
           + "&text=" + encodeURIComponent(ozet200);
  const wa = "https://wa.me/?text="
           + encodeURIComponent(ozet200 + " " + adres);
  /* Onizlemede gosterilen alan adi, adresin KENDI alan adi.
     Elle yazilsaydi alan adi degistiginde kart yalan soylerdi. */
  let alan = adres;
  try { alan = new URL(adres).hostname.replace(/^www\./, ""); } catch (e) { }

  return `<section class="paylas-blok" aria-labelledby="paylas-bas">
  <h2 id="paylas-bas">Bu senaryoyu paylaş</h2>
  <p class="paylas-alt">Netaris'teki bu değerlendirmeyi kendi ağında paylaş.</p>

  <div class="paylas-onizleme" aria-hidden="true">
    <span class="paylas-onizleme-marka">NETARIS</span>
    <span class="paylas-onizleme-baslik">${kacir(baslik)}</span>
    <span class="paylas-onizleme-ozet">${kacir(ozet200)}</span>
    <span class="paylas-onizleme-alan">${kacir(alan)}</span>
  </div>
  <p class="paylas-onizleme-not">Paylaşımın sosyal ağda böyle görünmesi bekleniyor.</p>

  <div class="sayfa-paylas-dugmeler">
    <a class="sp-dugme sp-x" href="${kacir(x)}"
       target="_blank" rel="noopener noreferrer">${ikon("x")}<span>X</span></a>
    <a class="sp-dugme sp-li" href="${kacir(li)}"
       target="_blank" rel="noopener noreferrer">${ikon("li")}<span>LinkedIn</span></a>
    <a class="sp-dugme sp-wa" href="${kacir(wa)}"
       target="_blank" rel="noopener noreferrer">${ikon("wa")}<span>WhatsApp</span></a>
    <a class="sp-dugme sp-tg" href="${kacir(tg)}"
       target="_blank" rel="noopener noreferrer">${ikon("tg")}<span>Telegram</span></a>
    <button class="sp-dugme sp-kopya" type="button"
            data-paylas-kopyala="${kacir(adres)}">${ikon("kopya")}<span>Bağlantıyı kopyala</span></button>
  </div>
</section>`;
}


async function senaryoSayfa(istek, env, id) {
  if (!env.DB || !Number.isFinite(id)) return null;
  const r = await env.DB.prepare(
    "SELECT s.id, s.kosul, s.sonuc, s.gerekce, s.ufuk, s.ufuk_biter, " +
    "s.yayin, s.sonuclanma, s.sonuclanma_notu, s.capa, s.capa_tur, " +
    "s.capa_baslik, s.curutme, s.kaynaklar, u.ad AS yazar, " +
    "(SELECT COUNT(*) FROM senaryo_oy o WHERE o.senaryo_id = s.id) AS oy " +
    "FROM senaryo s JOIN uye u ON u.id = s.uye_id " +
    "WHERE s.id = ? AND s.durum = 'yayimlandi'"
  ).bind(id).first();
  if (!r) return null;

  const baslik = r.kosul;
  /* Ozet KOSUL + SONUC birlikte: tek basina kosul "ne olursa" der ama
     "ne olur" demez, ve paylasim kartinda yarim bir cumle kalir. */
  const ozet = r.kosul + " " + r.sonuc;
  const adres = new URL(istek.url).origin + "/senaryo/" + r.id + "/";
  const gorsel = await capaGorseli(env, r.capa, r.capa_tur);

  const govde = `<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${kacir(baslik)} — Netaris senaryo</title>
<meta name="description" content="${kacir(ozet).slice(0, 300)}">
<link rel="canonical" href="${kacir(adres)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Netaris">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="${kacir(baslik)}">
<meta property="og:description" content="${kacir(ozet).slice(0, 300)}">
<meta property="og:url" content="${kacir(adres)}">
${gorsel ? `<meta property="og:image" content="${kacir(
  /* CAPA SAYFASININ og:image'I ZATEN MUTLAK.
     Ilk yazimimda basina origin ekledim ve
     "https://netaris.nethttps://netaris.net/statik/..." cikti --
     yani kart gorseli hic yuklenmezdi. Goreli gelirse tamamlaniyor,
     mutlaksa oldugu gibi kullaniliyor. */
  gorsel.startsWith("http") ? gorsel
    : new URL(istek.url).origin + gorsel)}">
<meta property="og:image:alt" content="${kacir(r.capa_baslik || baslik)}">
<meta name="twitter:card" content="summary_large_image">`
  : `<meta name="twitter:card" content="summary">`}
<link rel="stylesheet" href="/statik/stil.css">
<!-- Oy dugmesi ve oturum durumu icin. Ertelenmis yukleniyor:
     sayfa metni betige bagli degil, yalnizca etkilesim bagli.
     NOT: bu yorumda TERS TIRNAK KULLANILAMAZ -- sablon dizgesini
     kapatir ve dosya sozdizimi hatasi verir. Bir kez yasandi. -->
<script src="/statik/oturum.js" defer></script>
<script src="/statik/senaryo.js" defer></script>
</head><body>
<!-- SENARYO ARTIK BIR YAZI, HABER ALTINDA YORUM DEGIL.
     ==================================================
     Once duz bir baslik ve tek satir kunye vardi; sayfa "bir haberin
     altindaki yorumun kendi adresi" gibi duruyordu. Oysa senaryo bir
     ONERME: kosulu, sonucu, gerekcesi ve ufku olan bagimsiz bir
     icerik.

     Kunye bir YAZI kunyesi olarak kuruluyor: tur rozeti, ufuk,
     tarih, yazar. Ayni bilgi -- ama okur simdi bir yaziya baktigini
     anliyor.

     BASLIK KOSUL -> SONUC. Once yalnizca kosul basiliyordu ve okur
     baslikta onermenin YARISINI goruyordu. Paylasimda da oyle
     gidiyordu. -->
<main class="kabuk senaryo-sayfa">
  <header class="senaryo-bas">
    <p class="senaryo-rozetler">
      <span class="rozet rozet-vurgu">TOPLULUK SENARYOSU</span>
      <span class="rozet">${kacir(ufukMetni(r))}</span>
      ${r.sonuclanma ? `<span class="rozet rozet-sonuc rozet-${kacir(r.sonuclanma)}">${
        {gerceklesti: "Gerçekleşti", gerceklesmedi: "Gerçekleşmedi",
         belirsiz: "Belirsiz"}[r.sonuclanma] || ""}</span>` : ""}
    </p>

    <h1>${kacir(r.kosul)}
      <span class="senaryo-ok-bas" aria-hidden="true">→</span>
      <span class="senaryo-sonuc-bas">${kacir(r.sonuc)}</span></h1>

    <div class="senaryo-yazar">
      <!-- Bas harf dairesi, vesikalik DEGIL: uyelerin fotografi yok ve
           uydurma bir avatar koymak kimligi yanlis tanitmak olurdu.
           Ayni kural sitenin kurum imzasinda da gecerli. -->
      <span class="senaryo-yazar-harf" aria-hidden="true">${
        kacir((r.yazar || "N").trim().charAt(0).toLocaleUpperCase("tr"))}</span>
      <span class="senaryo-yazar-ad">
        <b>${kacir(r.yazar || "Netaris okuru")}</b>
        <span>${r.yayin ? kacir(String(r.yayin).slice(0, 10)) : ""}
          ${r.oy ? `· ${r.oy} kişi değerli buldu` : ""}</span>
      </span>
    </div>
  </header>

  <section class="senaryo-blok">
    <h2>Tetikleyici</h2>
    <p>${kacir(r.kosul)}</p>
  </section>

  <section class="senaryo-blok">
    <h2>Beklenen sonuç</h2>
    <p>${kacir(r.sonuc)}</p>
  </section>

  ${r.gerekce ? `<section class="senaryo-blok">
    <h2>Neden böyle düşünüyor</h2>
    <p>${kacir(r.gerekce)}</p>
  </section>` : ""}

  <!-- CURUTME KOSULU. Bir senaryoyu bir GORUSTEN ayiran tek sey,
       yazarin kendi kendini yanlislayabilecek gelismeyi ONCEDEN
       yazmasi. Onu yazmayan metin her sonucta hakli cikar.

       Vurgulu bir kutuda duruyor cunku sayfadaki en degerli cumle bu:
       okur senaryonun ciddiyetini once buradan olcer.

       Bos ise BOLUM HIC BASILMIYOR -- bos bir "Beni ne yanıltır?"
       basligi, alanin doldurulmadigini degil, yazarin cevabi
       olmadigini dusundururdu. -->
  ${r.curutme ? `<section class="senaryo-blok senaryo-curutme">
    <h2>Yazarına göre bu senaryoyu ne çürütür</h2>
    <p>${kacir(r.curutme)}</p>
  </section>` : ""}

  ${r.kaynaklar ? `<section class="senaryo-blok">
    <h2>Kaynaklar</h2>
    <p class="senaryo-kaynak">${kacir(r.kaynaklar)}</p>
  </section>` : ""}

  ${r.sonuclanma ? `<section class="senaryo-blok senaryo-sonuc">
    <h2>Sonuç</h2>
    <p>Bu senaryo <b>${kacir(ufukMetni(r))}</b>.</p>
    ${r.sonuclanma_notu ? `<p>${kacir(r.sonuclanma_notu)}</p>` : ""}
  </section>` : ""}

  ${r.capa && r.capa_tur === "haber" ? `<p class="senaryo-capa">
    Bağlam: <a href="${kacir(r.capa)}">${kacir(r.capa_baslik || "ilgili haber")}</a>
  </p>` : ""}

  <!-- DEGERLI BULDUM -- sayfada oy verme yolu YOKTU.
     Sayfa oy SAYISINI gosteriyordu ("1 destek") ama okuyan kisi
     katkida bulunamiyordu; sayac vardi, dugme yoktu.

     "Katiliyorum" DEGIL: katilim oyu bir olasilik gibi okunur ve
     hesaplamadigimiz bir sayiyi olcum gibi sunar. Gerekcesi
     d1/sema.sql icinde senaryo_oy tablosunun bas yorumunda yazili.

     Giris gerekiyor: anonim oy sayilabilir bir sey degil. Girisi
     olmayan okur dugmeye bastiginda senaryo.js giris sayfasina
     yonlendiriyor. -->
  <div class="senaryo-oyla">
    <button class="dugme dugme-ikincil" type="button"
            data-oy="${r.id}">Değerli buldum</button>
    <span class="senaryo-oy-sayi">${r.oy} kişi değerli buldu</span>
  </div>

  ${paylasBlok(baslik, ozet, adres)}

  <!-- DONGUYU KAPATAN HALKA.
     Okur bu sayfaya bir paylasimdan geliyor. Senaryoyu okudu; simdi
     KENDI senaryosunu yazabilmeli. Bu baglanti olmadan ziyaret
     okumayla bitiyor ve dongu tek yonlu kaliyor. -->
  <section class="senaryo-davet senaryo-davet-alt">
    <div class="senaryo-davet-ic">
      <p class="senaryo-davet-etiket">Sen ne düşünüyorsun?</p>
      <h2>Kendi senaryonu yaz</h2>
      <p>Aynı gelişme için farklı bir koşul ve sonuç görüyorsan
        senaryonu yazabilirsin. İncelendikten sonra kendi sayfasında
        adınla yayımlanır.</p>
      <a class="dugme dugme-birincil" href="/panel/?bolum=senaryo">Senaryonu yaz</a>
    </div>
  </section>

  <p class="senaryo-uyari"><strong>Yatırım tavsiyesi değildir.</strong>
  Senaryo bir koşullu değerlendirmedir; koşulun gerçekleşeceği iddia
  edilmez. Yazan okurun kendi görüşüdür.</p>

  <p class="senaryo-geri"><a href="/topluluk/">← Tüm senaryolar</a></p>
</main>
</body></html>`;

  return new Response(govde, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      /* Kisa onbellek: senaryo oy alabiliyor ve sonuclanabiliyor,
         ama her istekte D1 sorgulamak da gereksiz. */
      "cache-control": "public, max-age=300",
    },
  });
}


export default {
  async fetch(istek, env) {
    const u = new URL(istek.url);

    /* SENARYO SAYFASI statik dosyadan ONCE. Bulunamazsa (taslak,
       silinmis, gecersiz id) statik akisa dusuyor ve normal 404
       sayfasi cikiyor -- worker kendi hata sayfasini uydurmuyor. */
    const sp = u.pathname.match(/^\/senaryo\/(\d+)\/?$/);
    if (sp) {
      const y = await senaryoSayfa(istek, env, Number(sp[1]));
      if (y) return y;
    }

    /* BOLUM KOKU YONLENDIRMESI -- statik akistan ONCE.
       Olculdu: `/haber/` 404 donuyordu. Dizinde tek tek haber
       sayfalari var ama liste sayfasi yok.

       Once bunu `_redirects` dosyasiyla cozmeye calistim ve
       CALISMADI: istek buraya once giriyor, `env.ASSETS.fetch`
       dosyayi bulamayinca 404 donuyor ve `_redirects` hic
       degerlendirilmiyor. Yonlendirme, statik akisa DUSMEDEN once
       burada olmali.

       Hedef `/gundem/`: zaten tam olarak o liste. Ikinci bir kopya
       uretmek iki adreste ayni icerik demek ve ikisi birbirinin
       arama siralamasini yer. */
    const kok = { "/haber": "/gundem", "/haber/": "/gundem/" };
    if (kok[u.pathname]) {
      return Response.redirect(new URL(kok[u.pathname], u.origin), 301);
    }

    if (!u.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(istek);
    }
    if (!env.DB) {
      return hata("Veritabanı bağlı değil.", 503);
    }

    const y = u.pathname.slice(5);
    const m = istek.method;

    try {
      if (y === "kayit" && m === "POST") return await kayit(istek, env);
      if (y === "giris" && m === "POST") return await giris(istek, env);
      /* Google girisi oturum ISTEMEZ -- oturumu bu uc ACIYOR. */
      if (y === "giris/google" && m === "POST")
        return await googleGiris(istek, env);
      if (y === "giris/google/ayar" && m === "GET") return googleAyar(env);
      if (y === "cikis" && m === "POST") return await cikis(istek, env);
      if (y === "dogrula" && m === "GET") return await dogrula(istek, env);
      if (y === "ben" && m === "GET") return await ben(istek, env);
      if (y === "disari-aktar" && m === "GET") return await disariAktar(istek, env);
      if (y === "yayimlandi" && m === "POST") return await yayimlandiIsaretle(istek, env);
      /* Haber sayfasindaki senaryo bolumu -- oturum ISTEMEZ, yalnizca
         yayimlanmis senaryolari doner. */
      if (y === "senaryo/acik" && m === "GET") return await senaryoAcik(istek, env);
      if (y === "senaryo/hepsi" && m === "GET") return await senaryoHepsi(env);
      /* SAYACLAR OTURUM ISTEMEZ.
         Okurun cogu uye degil; goruntulenme uyelige bagli olsaydi
         olcum sitenin kucuk bir dilimini gosterirdi. Begeni ise
         asagida, oturum sartinin ARDINDA. */
      if (y === "goruntulenme" && m === "POST")
        return await goruntulenmeArtir(istek, env);
      if (y === "sayaclar" && m === "POST")
        return await sayaclariGetir(istek, env);
      if (y === "senaryo/one-cikan" && m === "GET")
        return await senaryoOneCikan(env);

      /* Buradan sonrasi oturum istiyor */
      const uye = await uyeBul(istek, env.DB);
      if (!uye) return hata("Oturum gerekli.", 401);

      if (y === "yazi" && m === "GET") return await yaziListe(istek, env, uye);
      if (y === "yazi" && m === "POST") return await yaziKaydet(istek, env, uye);

      const tek = y.match(/^yazi\/(\d+)$/);
      if (tek && m === "GET") return await yaziGetir(env, uye, Number(tek[1]));
      if (tek && m === "DELETE") return await yaziSil(env, uye, Number(tek[1]));

      if (y === "begeni" && m === "POST")
        return await begeniDegistir(istek, env, uye);
      if (y === "senaryo" && m === "GET") return await senaryoListe(env, uye);
      if (y === "senaryo" && m === "POST") return await senaryoKaydet(istek, env, uye);
      const sen = y.match(/^senaryo\/(\d+)$/);
      if (sen && m === "DELETE") return await senaryoSil(env, uye, Number(sen[1]));
      const oy = y.match(/^senaryo\/(\d+)\/oy$/);
      if (oy && m === "POST") return await senaryoOy(env, uye, Number(oy[1]));

      if (y.startsWith("yonetim/")) {
        if (uye.rol !== "yonetici") return hata("Yetkiniz yok.", 403);
        if (y === "yonetim/ozet" && m === "GET") return await yonetimOzet(env);
        if (y === "yonetim/karar" && m === "POST") return await yonetimKarar(istek, env);
      }

      return hata("Bulunamadı.", 404);
    } catch (e) {
      /* Hata metni istemciye SIZDIRILMAZ -- SQL hatasi sema bilgisi verir. */
      console.error("api hatasi", u.pathname, e);
      return hata("Beklenmeyen bir hata oluştu.", 500);
    }
  },
};
