// OKUMA GECMISI -- YALNIZCA CIHAZDA
//
// NEDEN ARKA UC YOK
// -----------------
// Bu ozellik belgelerde uzun sure "arka uc gerekiyor" diye duruyordu.
// Gerekmiyor: okuma gecmisi okurun KENDI cihazinda isine yarayan bir
// liste. Sunucuda tutmak iki sey eklerdi -- bir tablo ve okurun ne
// okudugunun BIZDE durmasi. Ikincisi bu projenin gizlilik durusuna
// aykiri: "Reklam ve profilleme" bolumu profilleme YAPILMADIGINI
// yaziyor ve bunun dogru kalmasi gerekiyor.
//
// Yani burada eksik olan sey bir arka uc degildi, bir KARARDI.
//
// NE SAKLANIYOR
// -------------
// Yalnizca listeyi cizmeye yeten alanlar: tur, slug, baslik, yol ve
// okuma ani. Icerigin kendisi DEGIL -- o zaten onbellekte olabilir
// (`onbellek.ts`) ve iki kopya tutmanin anlami yok.
//
// HICBIR SEY GONDERILMIYOR
// ------------------------
// Bu modulde `fetch` YOK ve olmamali. Gizlilik metnindeki "uygulama
// cihazinizda ne saklar" bolumu bunu yaziyor; `test_gecmis.mjs`
// modulde ag cagrisi olmadigini sinamayla tutuyor.
//
// SINIR VAR
// ---------
// En fazla `EN_COK` kayit. Sinirsiz bir liste hem depoyu sisirir hem
// de okura faydasizdir -- kimse 900. haberi aramiyor. Sinir asilinca
// EN ESKI dusuyor.

import AsyncStorage from "@react-native-async-storage/async-storage";

const ANAHTAR = "netaris.gecmis";

/** En fazla kaç kayıt tutulur. Aşılınca en eski düşer. */
export const EN_COK = 200;

export type Kayit = {
  /** "haber" | "analiz" -- hangi ekrana döneceğini belirliyor. */
  tur: "haber" | "analiz";
  slug: string;
  baslik: string;
  /** Sitedeki yol -- paylaşım ve web bağlantısı için. */
  yol: string;
  /** Okuma anı (ISO). */
  an: string;
};

function gecerli(k: unknown): k is Kayit {
  if (!k || typeof k !== "object") return false;
  const o = k as Record<string, unknown>;
  return (
    (o.tur === "haber" || o.tur === "analiz") &&
    typeof o.slug === "string" &&
    o.slug.length > 0 &&
    typeof o.baslik === "string" &&
    o.baslik.length > 0 &&
    typeof o.an === "string" &&
    o.an.length > 0
  );
}

/** Kayıtlar, en yeni önce. Bozuk girdiler SESSİZCE ATILMIYOR, eleniyor. */
export async function oku(): Promise<Kayit[]> {
  try {
    const ham = await AsyncStorage.getItem(ANAHTAR);
    if (!ham) return [];
    const d = JSON.parse(ham);
    if (!Array.isArray(d)) return [];
    // Eski bir sürümden kalan ya da yarım yazılmış girdi listeyi
    // bozmamalı: ekran boş kalacağına eksik kalsın.
    return d.filter(gecerli);
  } catch {
    return [];
  }
}

/**
 * Bir okumayı kaydeder.
 *
 * AYNI İÇERİK İKİ KEZ GİRMİYOR: varsa anı güncellenip başa alınıyor.
 * Aksi hâlde bir haberi iki kez açan okur listesinde iki satır görür
 * ve liste hızla tek bir haberle dolar.
 */
export async function kaydet(k: Kayit): Promise<void> {
  if (!gecerli(k)) return;
  try {
    const eski = await oku();
    const yeni = [k, ...eski.filter(
      (x) => !(x.tur === k.tur && x.slug === k.slug),
    )].slice(0, EN_COK);
    await AsyncStorage.setItem(ANAHTAR, JSON.stringify(yeni));
  } catch {
    // Depo dolu ya da izin yok: OKUMAYI BOZMAMALI. Geçmiş bir
    // kolaylık; onun için haber ekranı hata göstermez.
  }
}

/** Tek bir kaydı siler. */
export async function sil(tur: Kayit["tur"], slug: string): Promise<void> {
  try {
    const kalan = (await oku()).filter(
      (x) => !(x.tur === tur && x.slug === slug),
    );
    await AsyncStorage.setItem(ANAHTAR, JSON.stringify(kalan));
  } catch {
    /* yoksay */
  }
}

/** Geçmişi tamamen siler (geçmiş ekranı ve profil → veri). */
export async function temizle(): Promise<void> {
  try {
    await AsyncStorage.removeItem(ANAHTAR);
  } catch {
    /* yoksay */
  }
}
