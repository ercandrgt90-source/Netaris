/* "AI Sonucu" -- haber sayfasindaki uc satirlik cikarim.
 *
 * TEMEL KURAL: MODEL RAKAM BULMAZ, VERILEN RAKAMI CUMLEYE CEVIRIR.
 *
 * Sayfadaki butun olcumler (TUFE, cekirdek, politika faizi, beklenti,
 * duyarlilik siralamasi) zaten deterministik olarak hesaplaniyor. Model
 * yalnizca o olcumleri okunur bir paragrafa doner. Bu ayrim iki isi
 * birden goruyor:
 *
 *   1. Maliyeti dusuruyor -- kisa girdi, kisa cikti.
 *   2. UYDURMAYI KAPATIYOR -- modelin arayacagi bir sey yok.
 *
 * Uydurma yine de olabilir diye cikti DOGRULANIYOR: metinde gecen her
 * sayi girdide de gecmek zorunda. Gecmiyorsa cevap TAMAMEN atiliyor --
 * duzeltmeye calismak yerine susmak dogru.
 *
 * SAGLAYICI DEGISTIRMEK: `uret()` icindeki tek cagri degisir. Anthropic
 * ya da baska bir uca gecmek icin sayfanin geri kalanina dokunulmuyor.
 */

/* Ucretsiz kotada calisan, talimat izleyen kucuk model. */
const MODEL = "@cf/meta/llama-3.1-8b-instruct";

const EN_COK_JETON = 320;

/* Sistem yonergesi Turkce: model Turkce yazacak ve kurallar Turkce
   ifade edildiginde daha iyi izleniyor. */
const YONERGE = `Sen bir finans veri editörüsün. Sana bir haberin ölçülmüş
verileri veriliyor. Görevin bu verileri üç kısa cümleyle özetlemek.

KURALLAR:
- YALNIZCA sana verilen sayıları kullan. Yeni sayı, oran, tarih ya da
  kurum adı EKLEME.
- Tahmin, öngörü ya da yatırım tavsiyesi YAZMA. "Yükselecek", "alım
  fırsatı", "beklentimiz" gibi ifadeler yasak.
- Olasılık belirtme. "%60 ihtimalle" gibi ifadeler yasak.
- Yön yorumu yapma; ölçümü aktar. "Zayıf geldi" değil, "beklentinin
  0,3 puan altında" de.
- Üç cümleyi geçme. Madde işareti kullanma, düz metin yaz.
- Türkçe yaz.`;

/* Cikti dogrulamasi: metindeki her sayi girdide de gecmeli.
   Ondalik ayraci ve binlik noktasi temizlenerek karsilastiriliyor;
   "31,75" ile "31.75" ayni sayidir. */
function sayilar(metin) {
  const bulunan = String(metin).match(/-?\d[\d.,]*/g) || [];
  return new Set(bulunan.map((s) =>
    s.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".").replace(/\.$/, "")));
}

function guvenli(cikti, girdi) {
  const g = sayilar(girdi);
  for (const s of sayilar(cikti)) {
    /* Tek haneli sayilar ("üç cümle", "1 puan") gurultu; atlaniyor. */
    if (s.replace("-", "").length < 2) continue;
    if (!g.has(s)) return false;
  }
  return true;
}

/* Yasak kalip taramasi. Model kurala uymazsa cevap atiliyor. */
const YASAK = [
  /\b(alım|satım|tut)\s+(öneri|tavsiye)/i,
  /hedef fiyat/i,
  /%\s*\d+\s*(ihtimal|olasılık)/i,
  /\b(yükselecek|düşecek|artacak|azalacak)\b/i,
  /\byatırım (tavsiyesi|önerisi)\b/i,
];

export async function uret(env, girdi) {
  if (!env.AI || !girdi || girdi.length < 40) return null;
  let y;
  try {
    y = await env.AI.run(MODEL, {
      max_tokens: EN_COK_JETON,
      /* Sicaklik DUSUK: bu bir yaratici yazim isi degil, bicimlendirme
         isi. Yuksek sicaklik uydurma olasiligini artiriyor. */
      temperature: 0.2,
      messages: [
        { role: "system", content: YONERGE },
        { role: "user", content: girdi },
      ],
    });
  } catch (e) {
    /* Kota dolduysa ya da uc coktuyse sayfa AI bolumsuz basilir.
       Sitenin okuma tarafi bu katmana bagimli degil. */
    console.error("ai hatasi", e);
    return null;
  }

  const metin = (y && (y.response || y.result))?.trim();
  if (!metin) return null;
  if (YASAK.some((d) => d.test(metin))) {
    console.error("ai ciktisi yasak kalip icerdi, atildi");
    return null;
  }
  if (!guvenli(metin, girdi)) {
    console.error("ai ciktisi girdide olmayan sayi icerdi, atildi");
    return null;
  }
  return metin;
}
