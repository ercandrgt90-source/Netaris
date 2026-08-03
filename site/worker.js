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

  const jeton = rastgele(24);
  await db.prepare(
    "INSERT INTO uye (eposta, ad, parola_ozet, durum, rol, " +
    "dogrulama_ozeti, dogrulama_biter, kayit_ani) " +
    "VALUES (?, ?, ?, 'beklemede', 'yazar', ?, ?, ?)",
  ).bind(
    eposta, ad, await parolaOzetle(parola),
    await sha256(jeton), damga() + 86400, simdi(),
  ).run();

  const taban = new URL(istek.url).origin;
  const baglanti = `${taban}/api/dogrula?j=${jeton}&e=${encodeURIComponent(eposta)}`;
  const posta = await dogrulamaGonder(env, eposta, ad, baglanti);

  return yanit({
    tamam: true,
    mesaj: posta.gonderildi
      ? "Doğrulama bağlantısı e-postanıza gönderildi."
      : "Kaydınız alındı. Hesabınız yönetici onayından sonra etkinleşecek.",
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
  return yanit({
    uyeler: bekleyenUye.results || [],
    yazilar: bekleyenYazi.results || [],
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

/* --------------------------------------------------------------- yonlendirme */

export default {
  async fetch(istek, env) {
    const u = new URL(istek.url);

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
      if (y === "cikis" && m === "POST") return await cikis(istek, env);
      if (y === "dogrula" && m === "GET") return await dogrula(istek, env);
      if (y === "ben" && m === "GET") return await ben(istek, env);
      if (y === "disari-aktar" && m === "GET") return await disariAktar(istek, env);
      if (y === "yayimlandi" && m === "POST") return await yayimlandiIsaretle(istek, env);

      /* Buradan sonrasi oturum istiyor */
      const uye = await uyeBul(istek, env.DB);
      if (!uye) return hata("Oturum gerekli.", 401);

      if (y === "yazi" && m === "GET") return await yaziListe(istek, env, uye);
      if (y === "yazi" && m === "POST") return await yaziKaydet(istek, env, uye);

      const tek = y.match(/^yazi\/(\d+)$/);
      if (tek && m === "GET") return await yaziGetir(env, uye, Number(tek[1]));
      if (tek && m === "DELETE") return await yaziSil(env, uye, Number(tek[1]));

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
