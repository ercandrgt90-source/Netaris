// NETARIS BESLEME ISTEMCISI
//
// Icerik `/v1/*.json` statik beslemesinden, uye islemleri `/api/*`
// worker ucundan geliyor. Ikisi ayri cunku biri insa aninda
// uretiliyor, oteki calisma aninda -- ve bu ayrim onbellek
// politikasini da belirliyor.
//
// SAHTE VERI URETILMIYOR. Hicbir islev "veri gelmedi" durumunda
// ornek deger dondurmuyor; cagiran katman yukleniyor / bos / hata
// durumlarini ayri ayri gostermek zorunda. Bir finans uygulamasinda
// uydurma fiyat gostermek, hic gostermemekten kat kat kotudur.

export const TABAN = "https://netaris.net";

/** Besleme oneki. `/v1/surum.json` icinde de bildiriliyor. */
export const ONEK = "/v1";

/** Ag istegi zaman asimi (ms). Telefon sebekesi yavas olabilir. */
const ZAMAN_ASIMI = 15000;

export type Haber = {
  tur: "haber";
  slug: string;
  yol: string;
  baslik: string;
  ozet: string;
  konu: string;
  bolge: string;
  kurum: string;
  kurum_tam: string;
  ticari: boolean;
  kaynak_adres: string;
  tarih: string;
  foto: string;
  foto_atif: string;
  // Yalnizca detay dosyasinda
  baslik_kaynak?: string;
  kaynak_ozeti?: string;
  neden_onemli?: string;
  kanal_basligi?: string;
  kanallar?: string[];
  cevrildi?: boolean;
  dil?: string;
  tarih_gorunur?: string;
};

export type Analiz = {
  tur: "analiz";
  slug: string;
  yol: string;
  baslik: string;
  ozet: string;
  sirket: string;
  kod: string;
  sektor: string;
  donem: string;
  kategori: string;
  tarih: string;
  skor: string | null;
  okuma_dk: number;
  yazar: string;
  unvan: string;
  imzali: boolean;
  kurgusal: boolean;
  amblem: string;
  foto: string;
  foto_atif: string;
  // Yalnizca detay dosyasinda
  govde_html?: string;
  kapsam?: string;
  veri_kaynagi?: string;
  kaynaklar?: string[];
  kriterler?: { ad: string; puan: string; tam: string }[];
  bolumler?: { baslik: string; capa: string }[];
  sayimlar?: [string, string][];
  kelime?: number;
};

export type PiyasaKalemi = {
  kod: string;
  ad: string;
  deger: string;
  fark: string;
  yon: string;
  tarih: string;
  bayat: boolean;
  gun: number;
  ritim: string;
};

export type Piyasa = {
  veri_tarihi: string;
  canli_degil: boolean;
  aciklama: string;
  kalemler: PiyasaKalemi[];
};

/** Koşullu senaryo dalı: eşik aşılırsa / altında kalırsa. */
export type TakvimDali = {
  yon: string;
  baslik: string;
  /** Neyin neden değiştiği -- akıl yürütme. */
  mekanizma: string;
  /** Geçmiş gözlemler -- ölçüm. Mekanizmadan AYRI tutuluyor. */
  olcum: string;
};

export type TakvimOgesi = {
  ad: string;
  ulke: string;
  seri: string;
  onem: number;
  /** UTC kayması dahil ISO an. */
  an: string;
  /** Türkiye saatiyle gösterim. */
  yerel: string;
  gun: string;
  saat: string;
  saat_dilimi: string;
  /** false ise saat kurum tarafından DOĞRULANMAMIŞ. */
  kesin: boolean;
  kaynak: string;
  aciklandi: boolean;
  dallar: TakvimDali[];
  onceki_deger?: string;
  onceki_tarih?: string;
  esik_deger?: string;
  /**
   * "beklenti" | "onceki".
   *
   * BU ALAN OKUNMAK ZORUNDA: eşik bazen gerçek piyasa konsensüsü,
   * bazen yalnızca önceki değer. İkisini "beklenti" diye göstermek,
   * olmayan bir konsensüs uydurmak olur.
   */
  esik_kaynak?: string;
  gerceklesen?: { deger: number | null; donem: string; birim: string };
  surpriz?: { fark: number | null; yon: string; metin: string };
};

export type Takvim = {
  surum: number;
  uretildi: string;
  saat_dilimi: string;
  aciklama: string;
  ogeler: TakvimOgesi[];
};

export const takvim = () => getir<Takvim>(`${ONEK}/takvim.json`);

/** Yapısal bağ: "X, Y'yi etkiler". Sitenin haber toplamaktan
 *  ayrıldığı katman. */
export type VarlikBagi = {
  hedef: string;
  hedef_ad: string;
  kaynak: string;
  kaynak_ad: string;
  tur: string;
  aciklama: string;
  /** "yapisal" (tanım gereği doğru) | "veri" (gözlemden çıkarılmış,
   *  değişebilir) | "kaynak". İkisi aynı şey DEĞİL. */
  dayanak: string;
  guc: number;
  yon: string;
};

export type VarlikVerisi = {
  deger: string;
  birim: string;
  degisim: string;
  yon: string;
  tarih: string;
  gozlem_sayisi: number;
  seri: { tarih: string; deger: number | null }[];
};

export type Varlik = {
  kod: string;
  yol: string;
  ad: string;
  ad_en: string;
  tur: string;
  aciklama: string;
  haber_sayisi: number;
  seri_kodu: string;
  /**
   * false ise DEĞER YAYIMLANMIYOR.
   *
   * Sebebi lisans olabilir (BIST, S&P, Nasdaq, VIX) ya da seri hiç
   * olmayabilir (ülke, kurum). İkisi de "değer gösterme" demek.
   */
  veri_var: boolean;
  veri?: VarlikVerisi;
  baglar: VarlikBagi[];
  haberler: { baslik: string; yol: string; tarih: string; kurum: string }[];
};

export type VarlikDizinOgesi = {
  kod: string;
  yol: string;
  ad: string;
  tur: string;
  haber_sayisi: number;
  veri_var: boolean;
  deger: string;
  /**
   * Ölçü birimi. BOŞ OLABİLİR ve bu doğrudur: oran serilerinde değer
   * zaten "%3,74" biçiminde geliyor, kur çiftinde ad birimi taşıyor.
   * Boşken hiçbir şey basılmamalı -- "49,58 " gibi bir boşluk değil.
   */
  birim: string;
  yon: string;
  tarih: string;
  dosya: string;
};

export const varlikDizini = () =>
  getir<{ surum: number; uretildi: string; toplam: number;
          ogeler: VarlikDizinOgesi[] }>(`${ONEK}/varlik.json`);

export const varlik = (kod: string) =>
  getir<Varlik>(`${ONEK}/varlik/${encodeURIComponent(kod.toLowerCase())}.json`);

export type AramaKaydi = {
  /** "haber" | "analiz" | "varlik" */
  t: string;
  /** başlık */
  b: string;
  /** slug (varlıkta kod) */
  s: string;
  /** ISO tarih; varlıkta boş */
  d: string;
  /** konu / kategori / tür */
  k: string;
  /** yalnızca analizde: şirket kodu */
  c?: string;
};

export type AramaDizini = {
  surum: number;
  uretildi: string;
  /**
   * Türkçe diakritik katlama tablosu -- SİTENİN KENDİ TABLOSU.
   *
   * Uygulamaya kopyalanmıyor: aynı tablo sitede iki yerde duruyor
   * ve bir sınama ikisinin aynı olduğunu doğruluyor. Üçüncü bir
   * kopya, "hurmuz" yazan okurun "Hürmüz"ü bulamaması riskini bir
   * kat daha büyütürdü -- ve o kusur hiçbir hata üretmiyor.
   */
  katlama: Record<string, string>;
  toplam: number;
  kayitlar: AramaKaydi[];
};

export const aramaDizini = () => getir<AramaDizini>(`${ONEK}/arama.json`);

export type Sayfa<T> = {
  surum: number;
  sayfa: number;
  sayfa_sayisi: number;
  toplam_kayit: number;
  sonraki: string | null;
  ogeler: T[];
};

export type OneCikan = {
  surum: number;
  uretildi: string;
  kaynak: "site" | "en-yeni";
  haberler: Haber[];
  analizler: Analiz[];
};

export type TelOgesi = {
  baslik: string;
  baslik_kaynak: string;
  cevrildi: boolean;
  kurum: string;
  kurum_tam: string;
  adres: string;
  konu: string;
  ticari: boolean;
  tarih: string;
};

/** Ag katmaninin tek hata turu -- cagiran tek seyi yakalasin. */
export class AgHatasi extends Error {
  constructor(
    message: string,
    readonly durum?: number,
    readonly yol?: string,
  ) {
    super(message);
    this.name = "AgHatasi";
  }
}

/**
 * Tek JSON istegi.
 *
 * ZAMAN ASIMI VAR: `fetch` kendi basina sonsuza kadar bekleyebiliyor
 * ve kullanici sonsuz donen bir carki goruyor. Asim, "baglanti yok"
 * durumunu GORUNUR bir hataya ceviriyor.
 */
async function getir<T>(yol: string, jeton?: string): Promise<T> {
  const kontrol = new AbortController();
  const sayac = setTimeout(() => kontrol.abort(), ZAMAN_ASIMI);
  try {
    const basliklar: Record<string, string> = { accept: "application/json" };
    if (jeton) basliklar.authorization = `Bearer ${jeton}`;
    const cevap = await fetch(TABAN + yol, {
      headers: basliklar,
      signal: kontrol.signal,
    });
    if (!cevap.ok) {
      throw new AgHatasi(
        `Sunucu ${cevap.status} döndü.`,
        cevap.status,
        yol,
      );
    }
    return (await cevap.json()) as T;
  } catch (h) {
    if (h instanceof AgHatasi) throw h;
    if (h instanceof Error && h.name === "AbortError") {
      throw new AgHatasi("Bağlantı zaman aşımına uğradı.", undefined, yol);
    }
    throw new AgHatasi("Bağlantı kurulamadı.", undefined, yol);
  } finally {
    clearTimeout(sayac);
  }
}

export const surum = () =>
  getir<{
    surum: number;
    uretildi: string;
    onek: string;
    sayfa_boyu: number;
    beslemeler: Record<string, Record<string, unknown>>;
  }>(`${ONEK}/surum.json`);

export const oneCikan = () => getir<OneCikan>(`${ONEK}/one-cikan.json`);

export const piyasa = () => getir<Piyasa>(`${ONEK}/piyasa.json`);

export const haberSayfasi = (no = 1) =>
  getir<Sayfa<Haber>>(`${ONEK}/haber/sayfa-${no}.json`);

export const analizSayfasi = (no = 1) =>
  getir<Sayfa<Analiz>>(`${ONEK}/analiz/sayfa-${no}.json`);

export const haber = (slug: string) =>
  getir<Haber>(`${ONEK}/haber/${encodeURIComponent(slug)}.json`);

export const analiz = (slug: string) =>
  getir<Analiz>(`${ONEK}/analiz/${encodeURIComponent(slug)}.json`);

export const tema = () =>
  getir<{
    surum: number;
    kaynak: string;
    zorunlu: string[];
    acik: Record<string, string>;
    koyu: Record<string, string>;
  }>(`${ONEK}/tema.json`);

/**
 * CANLI TEL AKISI -- statik beslemede DEGIL, worker ucunda.
 *
 * Besleme bu akisi kopyalamiyor: kopyalamak insa aninda donmus bir
 * "canli" akis uretirdi. Uc on dakikada bir tazeleniyor.
 */
export const tel = (limit = 30) =>
  getir<{ ogeler: TelOgesi[] }>(`/api/tel?limit=${limit}`);

export const telDurum = () =>
  getir<{
    oge_sayisi: number;
    en_yeni: string;
    en_eski: string;
    besleme_sayisi: number;
  }>("/api/tel/durum");

export type Senaryo = {
  id: number;
  kosul: string;
  sonuc: string;
  capa: string;
  capa_baslik: string;
  ufuk: string;
  yayin: string;
  yazar: string;
  oy: number;
};

export const senaryolar = () =>
  getir<{ senaryolar: Senaryo[] }>("/api/senaryo/hepsi");

export type SenaryoKurallari = {
  surum: number;
  olcutler: { kod: string; ad: string }[];
  yonler: { kod: string; ad: string }[];
  ufuklar: string[];
  sinirlar: Record<string, { en_az: number; en_cok: number }>;
  notlar: { curutme: string; olcut: string };
};

/**
 * Form kuralları BESLEMEDEN geliyor, uygulamaya gömülü değil.
 *
 * Aynı liste worker'da (doğrulama) ve web formunda (etiketler)
 * duruyor. Üçüncü bir kopya koymak, bir senaryonun sonuçlanıp
 * sonuçlanmayacağında sessiz ayrışma demekti.
 */
export const senaryoKurallari = () =>
  getir<SenaryoKurallari>(`${ONEK}/senaryo-kurallari.json`);

export type SenaryoGirdisi = {
  kosul: string;
  sonuc: string;
  gerekce?: string;
  curutme?: string;
  kaynaklar?: string;
  capa: string;
  capa_baslik?: string;
  capa_tur?: "haber" | "varlik" | "konu";
  ufuk?: string;
  olcut_kod?: string;
  olcut_yon?: string;
  olcut_esik?: string;
  /** true -> incelemeye gönder, false -> taslak olarak sakla. */
  gonder: boolean;
};

export const senaryoKaydet = (jeton: string, s: SenaryoGirdisi) =>
  gonder<{ tamam: boolean; id?: number; durum?: string }>(
    "/api/senaryo",
    s as unknown as Record<string, unknown>,
    jeton,
  );

export type Uye = { ad?: string; eposta?: string; rol?: string } | null;

/** POST istegi. `istemci: "uygulama"` worker'a jetonu istedigimizi
 *  soyluyor; gerekce `worker.js` icindeki `uygulamaMi` yaninda. */
async function gonder<T>(
  yol: string,
  govde: Record<string, unknown>,
  jeton?: string,
): Promise<T> {
  const kontrol = new AbortController();
  const sayac = setTimeout(() => kontrol.abort(), ZAMAN_ASIMI);
  try {
    const basliklar: Record<string, string> = {
      "content-type": "application/json",
      accept: "application/json",
      "x-netaris-istemci": "uygulama",
    };
    if (jeton) basliklar.authorization = `Bearer ${jeton}`;
    const cevap = await fetch(TABAN + yol, {
      method: "POST",
      headers: basliklar,
      body: JSON.stringify({ ...govde, istemci: "uygulama" }),
      signal: kontrol.signal,
    });
    const d = await cevap.json().catch(() => ({}));
    if (!cevap.ok) {
      // SUNUCUNUN KENDI MESAJI KORUNUYOR: "E-posta veya parola
      // hatalı" ile "Hesabınız henüz doğrulanmadı" kullanici icin
      // tamamen farkli iki durum ve ikisinde yapacagi sey ayri.
      throw new AgHatasi(
        (d && typeof d.hata === "string" && d.hata) ||
          `Sunucu ${cevap.status} döndü.`,
        cevap.status,
        yol,
      );
    }
    return d as T;
  } catch (h) {
    if (h instanceof AgHatasi) throw h;
    if (h instanceof Error && h.name === "AbortError") {
      throw new AgHatasi("Bağlantı zaman aşımına uğradı.", undefined, yol);
    }
    throw new AgHatasi("Bağlantı kurulamadı.", undefined, yol);
  } finally {
    clearTimeout(sayac);
  }
}

export const giris = (eposta: string, parola: string) =>
  gonder<{ tamam: boolean; uye: Uye; jeton?: string; biter_gun?: number }>(
    "/api/giris",
    { eposta, parola },
  );

export const cikis = (jeton: string) =>
  gonder<{ tamam: boolean }>("/api/cikis", {}, jeton);

/**
 * Begeni ac/kapa. Yanit: toplam begeni ve OKURUN KENDI durumu.
 *
 * `baslik` begeni aninda gonderiliyor cunku worker onu kaydediyor:
 * yalnizca yol saklansaydi panelde adresler gorunurdu. Okur
 * begenirken baslik zaten ekranda.
 */
/**
 * HESAP SILME -- geri alinamaz.
 *
 * Play, hesap olusturulabilen her uygulamada uygulama icinden
 * erisilebilen bir silme yolu istiyor.
 *
 * Parolali hesapta `parola`, Google ile acilmis hesapta `onay`
 * ("HESABIMI SIL") gerekiyor: calinmis bir oturumla hesap
 * silinememeli.
 */
export const hesapSil = (
  jeton: string,
  kimlik: { parola?: string; onay?: string },
) =>
  gonder<{ tamam: boolean; silindi: boolean }>(
    "/api/hesap-sil",
    kimlik as Record<string, unknown>,
    jeton,
  );

export const begeniDegistir = (jeton: string, yol: string, baslik: string) =>
  gonder<{ tamam: boolean; begeni: number; benim: boolean }>(
    "/api/begeni",
    { yol, baslik },
    jeton,
  );

export type Begeni = { yol: string; baslik: string | null; an: string };

export const begenilerim = (jeton: string) =>
  getir<{
    begeniler: Begeni[];
    sayim: { yazi: number; senaryo: number; begeni: number; oy: number };
  }>("/api/begenilerim", jeton);

/**
 * OTURUM DURUMU. 401 BIR HATA DEGIL, BIR CEVAPTIR.
 *
 * `/api/ben` oturum yokken `{"uye":null}` ile birlikte HTTP 401
 * donuyor. Bunu ag hatasi saymak, misafir kullaniciya "veri
 * alinamadi" ekrani gostermek olurdu -- oysa cevap basariyla geldi
 * ve icerigi "giris yapilmamis".
 */
export async function ben(jeton?: string): Promise<Uye> {
  try {
    const d = await getir<{ uye: Uye }>("/api/ben", jeton);
    return d.uye ?? null;
  } catch (h) {
    if (h instanceof AgHatasi && h.durum === 401) return null;
    throw h;
  }
}

/** Gorsel ve amblem yollari beslemede GORELI geliyor. */
export const varlikAdresi = (yol: string) =>
  yol ? (yol.startsWith("http") ? yol : TABAN + yol) : "";

/** Paylasim ve "sitede ac" baglantisi. */
export const webAdresi = (yol: string) => TABAN + yol;
