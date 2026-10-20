# Netaris Mobil — Mağaza Hazırlık Dosyası

Hazırlandı: 2026-10-19. Google Play **bireysel** geliştirici hesabı
kararına göre yazıldı.

Bu belgedeki veri güvenliği cevapları **tahmin değil**: `site/d1/sema.sql`,
`site/d1/gecis_sayac.sql` ve `site/worker.js` okunarak çıkarıldı.
Uygulamanın gerçekten gönderdiği alanlar `mobil/src/api.ts` içinde.

---

## 1. Yapılacaklar — sıra önemli

| # | İş | Kim yapabilir |
|---|---|---|
| 1 | Expo hesabı aç, `eas login` | **Sadece siz** |
| 2 | `eas build:configure` ve ilk `deneme` derlemesi | Siz (hesap gerekir) |
| 3 | Play Console hesabı (25 USD, bir kez) | **Sadece siz** |
| 4 | Uygulama kaydı, paket adı `net.netaris.app` | Siz |
| 5 | Mağaza metinleri (aşağıda hazır) | Kopyala-yapıştır |
| 6 | Ekran görüntüleri (aşağıda liste) | Derlemeden sonra |
| 7 | Veri güvenliği formu (aşağıda hazır) | Kopyala |
| 8 | İçerik derecelendirme anketi | Siz |
| 9 | **Kapalı test: 12 test kullanıcısı × 14 gün** | Siz |
| 10 | Üretim yayını | Siz |

**Takvimdeki gerçek darboğaz 9. madde.** Teknik iş bitse bile Play
yayını en erken iki hafta sonra. 9. madde 2. maddeden hemen sonra
başlatılabilir — beklemeye gerek yok.

---

## 2. Uygulama kimliği

| Alan | Değer |
|---|---|
| Uygulama adı | Netaris |
| Paket adı (Android) | `net.netaris.app` |
| Bundle ID (iOS) | `net.netaris.app` |
| Sürüm | 0.1.0 |
| Kategori | Finans |
| Hedef kitle | 18+ (finansal içerik) |
| Gizlilik politikası | https://netaris.net/gizlilik/ |
| Destek e-postası | destek@netaris.net |
| Web sitesi | https://netaris.net |

---

## 3. Mağaza metinleri

### Kısa açıklama (en çok 80 karakter)

```
Finansal haber, bilanço analizi ve makro veri — kaynağıyla birlikte.
```

(68 karakter)

### Tam açıklama

```
Netaris; finansal haberleri, şirket bilançolarını ve makroekonomik
verileri tek bir yerde toplayan bir araştırma uygulamasıdır.

NE YAPAR

• Günün önemli finansal gelişmeleri, kaynağı ve yayın saatiyle
• Ajans başlıklarının canlı akışı
• Şirket bilançolarının analizi: hasılat, marjlar, kârlılık,
  borçluluk ve sektör medyanıyla karşılaştırma
• Makroekonomik göstergeler: enflasyon, faiz, tahvil getirileri,
  döviz, emtia ve kripto
• Ekonomik takvim: hangi veri ne zaman açıklanacak, önceki değer
  ne, beklenti ne
• Koşullu senaryolar: "şu olursa şu beklenir" biçiminde
  değerlendirmeler, ölçülebilir tetikleyiciyle
• Varlık sayfaları: tanım, yapısal ilişkiler ve haber arşivi

NASIL ÇALIŞIR

Muhasebe verisi, türetilmiş oranlar ve yorum birbirinden ayrı
gösterilir. Oranlar doğrulanmış hesaplamalardan gelir; hiçbir sayı
tahmin edilmez.

Piyasa verileri gecikmelidir ve her değerin yanında kendi veri
tarihi yazılıdır. Canlı fiyat iddia edilmez.

Hisse senedi endeksleri (BIST 100, S&P 500, Nasdaq, DAX) uygulamada
yer almaz: bu endekslerin veri dağıtım lisansı Netaris'te değildir.
Eksik bir grup, lisanssız bir gruptan iyidir.

Haber özetlerinde kaynak kurum ve bağlantısı her zaman görünür.

ÜYELİK

İçeriğin tamamı üyelik olmadan okunabilir. Üyelik yalnızca
favoriler, kaydedilen araştırmalar ve senaryo yazmak için gerekir.

UYARI

Netaris yatırım danışmanlığı yapmaz. İçerik bilgilendirme amaçlıdır;
alım satım tavsiyesi değildir. Koşullu senaryolar kesin öngörü ya da
getiri vaadi değildir.
```

### Yapay zekâ bildirimi

Play Console "Üretken yapay zekâ" sorusuna verilecek cevap:

> Uygulama, yayımlanan bilanço analizlerinde yapay zekâ ile
> üretilmiş yorum bölümleri içerir. Bu bölümler kaynağında
> etiketlidir. Yapay zekâ **sayısal veri üretmez**; tüm sayılar
> doğrulanmış hesaplamalardan gelir ve modelin ürettiği metin,
> girdide bulunmayan bir sayı içeriyorsa yayımlanmadan reddedilir.
> Uygulamada kullanıcıya açık bir sohbet arayüzü **yoktur**.

Bu beyanın doğruluğu `haber_botu` tarafındaki doğrulama adımıyla
sağlanıyor — ölçülen ret oranı kayıtlı.

---

## 4. Veri güvenliği formu

### Toplanan veriler

| Veri türü | Toplanıyor mu | Paylaşılıyor mu | Zorunlu mu | Amaç |
|---|---|---|---|---|
| E-posta adresi | **Evet** | Hayır | Üyelik için | Hesap yönetimi |
| Ad, soyad | **Evet** | Hayır | Üyelik için | Hesap yönetimi, künye |
| Unvan, kısa özgeçmiş | **Evet** | Hayır | Hayır | Künye (yayımlanan içerikte görünür) |
| Profil fotoğrafı | **Evet** | Hayır | Hayır | Künye |
| Parola | **Evet** | Hayır | Üyelik için | Kimlik doğrulama |
| Kullanıcı içeriği (senaryo, yazı) | **Evet** | Hayır | Hayır | Yayımlanan içerik |
| Favoriler | **Evet** | Hayır | Hayır | Uygulama işlevi |
| IP adresi | **Evet** | Hayır | — | **Yalnızca güvenlik** (kötüye kullanım sınırlama) |

### Toplanmayanlar — açıkça

Konum · Kişiler · Takvim · Fotoğraf galerisi · Mikrofon · Kamera ·
Cihaz kimliği · Reklam kimliği · Kullanım analitiği · Çökme
günlüğü · Satın alma geçmişi · Sağlık verisi · SMS ·
Arama geçmişi · Üçüncü taraf reklam ağı

Uygulamada **reklam SDK'sı, analitik SDK'sı ve izleyici yoktur.**
Bağımlılık listesi `mobil/package.json` içinde ve doğrulanabilir.

### Form cevaplarının dayanağı

| İddia | Nerede doğrulanır |
|---|---|
| E-posta, ad, soyad, unvan, hakkında, avatar | `site/d1/sema.sql` → `uye` tablosu |
| Parola yalnızca özet olarak saklanıyor | `uye.parola_ozet` |
| Oturum jetonu yalnızca SHA-256 özeti | `sema.sql` → `oturum.jeton_ozeti` |
| Favoriler | `gecis_sayac.sql` → `begeni(yol, uye_id)` |
| Görüntülenme sayacı kullanıcıya bağlı DEĞİL | `sayac(yol, goruntulenme)` — üye kimliği yok |
| IP yalnızca hız sınırlama | `worker.js` → `denemeArtir("giris-ip:…")`, 900 sn pencere |
| Avatar EXIF'i düşürülüyor | `sema.sql` → `uye.avatar` notu (GPS koordinatı atılıyor) |

### Güvenlik uygulamaları

- Veriler aktarımda şifreleniyor (HTTPS, Cloudflare)
- Kullanıcı veri silinmesini talep edebilir → `destek@netaris.net`
- Kullanıcı verisini dışa aktarabilir → uygulama içi **değil**,
  sitede `/api/disari-aktar` (KVKK)

**Çözüldü (2026-10-19):** Uygulama içinden hesap silme eklendi —
**Profil → Hesabımı sil**. Uç: `POST /api/hesap-sil`. Kimlik
doğrulaması ister (parolalı hesapta parola, Google hesabında onay
metni), hız sınırı var ve üyeye bağlı altı tablonun tamamını açıkça
siliyor — şemada `ON DELETE CASCADE` yazılı olsa da
`PRAGMA foreign_keys` hiç açılmadığı için cascade'e güvenilmiyor.
`site/test_hesap_sil.js` tabloları şemadan okuyup kontrol ediyor.

Gizlilik beyanı da güncellendi ve `beyan_denetimi.py` uyuşmayı
doğruluyor.

Play formunda "Kullanıcılar uygulama içinden hesaplarını
silebiliyor mu" → **Evet**. Silme yolu URL'si istenirse:
https://netaris.net/gizlilik/#hesabinizi-kendiniz-silebilirsiniz

---

## 5. İçerik derecelendirme

Beklenen: **3+ / Herkes**, ancak finansal içerik nedeniyle
"Kullanıcılar arası etkileşim" ve "Kullanıcı tarafından oluşturulan
içerik" işaretlenmeli (senaryolar ve üye yazıları).

Ankette şunlar **Hayır**: şiddet, cinsellik, kumar, uyuşturucu,
korku, alkol/tütün.

**Dikkat:** "Kullanıcılar paylaşım yapabilir mi" → **Evet**
(senaryolar). Bu, moderasyon beyanı gerektirir. Netaris'te
senaryolar **inceleme kuyruğundan geçiyor** (`durum: incelemede` →
`yayimlandi`); bu, Play'in istediği moderasyon şartını karşılıyor ve
beyan edilebilir.

---

## 6. Ekran görüntüleri

Play en az 2, en çok 8 telefon ekran görüntüsü istiyor
(16:9 ya da 9:16, en az 320 px kenar).

Önerilen sıra — her biri uygulamanın bir farkını gösteriyor:

1. **Ana sayfa** — piyasa şeridi + günün gelişmeleri
2. **Bilanço analizi detayı** — tablo görünür olacak şekilde
3. **Ekonomik takvim** — koşullu dallar açık
4. **Varlık detayı** — yapısal ilişkiler bölümü
5. **Senaryolar** — "tahmin değildir" uyarısı görünür
6. **Arama** — tür süzgeçleri

Koyu ve açık tema karışık kullanılabilir; ikisi de markaya uygun.

**Not:** Ekran görüntülerinde gerçek veri olacak. Uydurma rakam
içeren maket görüntü **kullanılmayacak** — hem Play politikası hem
projenin kendi kuralı.

### Öne çıkan görsel (1024×500)

Marka varlığından türetilebilir: `site/statik/marka/netaris-kart.png`
zaten 1200×630. Kırpılarak kullanılabilir ya da aynı palette yeniden
üretilebilir (`#0b1018` zemin, `#2dd4bf` vurgu).

---

## 7. Derleme

```bash
cd mobil
npm install
npx eas login          # hesap gerekir
npx eas build:configure
npx eas build --profile deneme --platform android     # test APK
npx eas build --profile yayin --platform android      # AAB
```

`eas.json` hazır: `gelistirme`, `deneme`, `yayin` profilleri tanımlı.
`yayin` profili `app-bundle` üretiyor (Play'in istediği biçim) ve
sürüm numarasını otomatik artırıyor.

**Mac gerekmiyor:** iOS derlemesi de EAS bulut kuyruğunda yapılıyor.
iOS yayını ayrı karar (99 USD/yıl).

---

## 8. Yayından önce çözülmesi gerekenler

| Konu | Durum |
|---|---|
| **1024 px vektör ikon** | Depodaki en büyük marka rendisi 512 raster; büyütüldü, kabul edilebilir ama asıl dosya istenmeli |
| **Uygulama içi hesap silme** | ÇÖZÜLDÜ — Profil → Hesabımı sil |
| **TradingView uygulama içi şartları** | **Okundu (2026-10-20) — eklenmeyecek.** Madde 3 ayrı anlaşma olmadan ticari kullanımı ve "TradingView içeriğine dayalı ürün"ü yasaklıyor; mağazada dağıtılan ticari bir uygulama bu tanıma giriyor. Uygulamada gömülü YOK ve olmayacak; sitedekiler atfıyla kalıyor |
| **Bildirimler** | Arka uç yok; uygulamada bildirim izni İSTENMİYOR, dolayısıyla formda da beyan yok. Faz 4d |
| **12 test kullanıcısı** | Bireysel hesapta zorunlu, 14 gün |

### Play politikası açısından risk taraması

| Politika | Durum |
|---|---|
| Minimum Functionality (web sarmalayıcı) | **Risk yok** — yerel arayüz, yerel gezinme, yalnızca makale gövdesi WebView |
| Finansal ürünler ve hizmetler | **Risk yok** — alım satım, kredi, yatırım aracılığı yok; yalnızca haber ve analiz |
| Haber uygulamaları | **Uyumlu** — kaynak, yazar ve yayın tarihi görünür |
| Yanıltıcı iddialar | **Uyumlu** — getiri vaadi yok, senaryolar açıkça tahmin değil diye etiketli |
| Kullanıcı içeriği moderasyonu | **Uyumlu** — inceleme kuyruğu var |
| Veri güvenliği doğruluğu | Yukarıdaki tablo kaynaktan çıkarıldı |

---

## 9. Yapamayacaklarım

Hesap açma, kimlik bilgisi girme, derleme başlatma ve mağazaya
gönderme **sizin yapmanız gereken** adımlar. Kimlik bilgisi
istemiyorum ve sohbete yazılmamalı; EAS ve Play kimlikleri kendi
araçlarında kalmalı.

FCM anahtarları sırası geldiğinde GitHub Secrets ya da
`wrangler secret put` ile konacak — depoya ya da sohbete değil.
