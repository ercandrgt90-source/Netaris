// ONBELLEK -- CEVRIMDISI OKUMA VE HIZLI ACILIS
//
// Sartname 13. bolum: "Baglanti kesintilerinde kontrollu davranis"
// ve "Gerektiginde cevrimdisi okunabilen kaydedilmis icerikler".
//
// IKI AYRI FAYDA, TEK MEKANIZMA
// -----------------------------
// 1. **Hizli acilis.** Uygulama acilinca once onbellekteki veriyi
//    gosteriyor, sonra tazesini cekiyor. Bos ekran + donen cark
//    yerine okunabilir icerik.
// 2. **Cevrimdisi okuma.** Metro, asansor, yurt disi. Besleme
//    gelmezse en son goruleni gosteriyor.
//
// BAYATLIK GIZLENMIYOR
// --------------------
// Onbellekten gelen veri GIZLICE taze gibi sunulmuyor: `bayat`
// bayragi ve `an` damgasi birlikte donuyor, ekran bunu yaziyor
// (`bilesen.BayatUyarisi`).
//
// Bu, projenin kendi kuralinin devami: piyasa degeri tarihiyle
// birlikte basiliyor cunku "sayi tek basina canli fiyat izlenimi
// veriyor". Bayat bir listeyi taze gibi gostermek ayni hatanin
// baska bir bicimi olurdu.
//
// NEDEN AsyncStorage, NEDEN expo-file-system DEGIL
// ------------------------------------------------
// Once `expo-file-system` (SDK 58'in yeni `File`/`Directory`
// arayuzu) kullanildi ve GERCEK TARAYICIDA SINANDI: calismadi.
//
//     ONBELLEK dizin: TypeError: this.validatePath is not a function
//
// Paketin WEB uygulamasi eksik. Yerelde muhtemelen calisirdi ama
// **dogrulanamazdi**: elimdeki olcum araci web cikisini aciyor.
// Dogrulayamadigim bir ozelligi sevk etmek, bu oturumda kacindigim
// seyin ta kendisi olurdu.
//
// AsyncStorage ikisinde de calisiyor: yerelde SQLite, web'de
// `localStorage`. Yani cevrimdisi okuma SINANABILIR hale geliyor.
//
// BOYUT SINIRI VAR
// ----------------
// `localStorage` kokeni basina ~5 MB, Android'de AsyncStorage
// varsayilan veritabani 6 MB. Arama dizini 264 KB ile en buyuk
// kayit; girdi basina sinir onun biraz ustunde tutuluyor. Sinirin
// UZERI SESSIZCE ATLANMIYOR -- sebebi gunluge yaziliyor, cunku
// "neden cevrimdisi calismiyor" sorusunun cevabi orada.
//
// NE ONBELLEKLENMEZ
// -----------------
// `/api/*` uclari ONBELLEKLENMIYOR. Canli tel akisini saklamak,
// "canli" diye bayat veri gostermek olurdu; oturum ve uye verisini
// saklamak ise cihazda gereksiz kisisel veri birakmak.

import AsyncStorage from "@react-native-async-storage/async-storage";

const ONEK = "netaris.onbellek.";

/**
 * Önbellek yaşı sınırı (ms). Bundan eskisi KULLANILMIYOR.
 *
 * Yedi gün: haber listesi bir haftadan eski olduğunda okura yanlış
 * bir "güncel" izlenimi verir. Ağ yoksa o noktadan sonra boş ekran
 * göstermek, yanlış içerik göstermekten dürüsttür.
 */
const EN_COK_YAS = 7 * 24 * 60 * 60 * 1000;

/** Girdi başına en büyük boyut (karakter). Arama dizini ~264 KB. */
const EN_COK_BOYUT = 400 * 1024;

export type Onbellekli<T> = {
  veri: T;
  /** Önbellekten mi geldi -- EKRANDA YAZILIYOR. */
  bayat: boolean;
  /** Ne zaman alındı (ISO). */
  an: string;
};

const anahtar = (yol: string) => ONEK + yol;

export async function yaz(yol: string, veri: unknown): Promise<void> {
  try {
    const metin = JSON.stringify({ an: new Date().toISOString(), veri });
    if (metin.length > EN_COK_BOYUT) {
      // SESSIZ ATLAMA YOK: "neden cevrimdisi calismiyor"
      // sorusunun cevabi tam burada.
      console.warn(
        `onbellek: ${yol} çok büyük (${Math.round(metin.length / 1024)} KB),` +
          ` yazılmadı`,
      );
      return;
    }
    await AsyncStorage.setItem(anahtar(yol), metin);
  } catch (e) {
    // Depo dolu ya da izin yok: okuma akisini bozmamali.
    console.warn("onbellek: yazılamadı", e);
  }
}

export async function oku<T>(yol: string): Promise<Onbellekli<T> | null> {
  try {
    const ham = await AsyncStorage.getItem(anahtar(yol));
    if (!ham) return null;
    const p = JSON.parse(ham) as { an: string; veri: T };
    if (!p || !p.an) return null;
    // COK ESKI ONBELLEK KULLANILMIYOR.
    if (Date.now() - new Date(p.an).getTime() > EN_COK_YAS) {
      await AsyncStorage.removeItem(anahtar(yol));
      return null;
    }
    return { veri: p.veri, bayat: true, an: p.an };
  } catch {
    return null;
  }
}

/** Önbelleği tamamen siler (profil → veri ve gizlilik). */
export async function temizle(): Promise<void> {
  try {
    const hepsi = await AsyncStorage.getAllKeys();
    const bizim = hepsi.filter((k) => k.startsWith(ONEK));
    if (bizim.length) await AsyncStorage.multiRemove(bizim);
  } catch {
    /* temizlenemezse bir sonraki denemede */
  }
}

/** Önbellekteki girdi sayısı ve toplam boyut (bayt). */
export async function durum(): Promise<{ girdi: number; bayt: number }> {
  try {
    const hepsi = await AsyncStorage.getAllKeys();
    const bizim = hepsi.filter((k) => k.startsWith(ONEK));
    if (!bizim.length) return { girdi: 0, bayt: 0 };
    const ciftler = await AsyncStorage.multiGet(bizim);
    let bayt = 0;
    for (const [, v] of ciftler) bayt += (v || "").length;
    return { girdi: bizim.length, bayt };
  } catch {
    return { girdi: 0, bayt: 0 };
  }
}
