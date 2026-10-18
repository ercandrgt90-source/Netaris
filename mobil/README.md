# Netaris Mobil

Netaris'in iOS ve Android uygulaması. Expo SDK 58 · React Native 0.88 ·
TypeScript.

İçerik `https://netaris.net/v1/*.json` beslemesinden, üye işlemleri
`https://netaris.net/api/*` worker ucundan geliyor. **Ayrı bir arka uç
yok** — besleme siteyi üreten Python hattının ikinci bir çıktısı.

---

## Telefonda açmak — en hızlı yol

Bilgisayar ve telefon **aynı Wi-Fi ağında** olmalı.

```bash
cd mobil
npm install
npx expo start
```

Terminalde bir QR kod çıkıyor:

- **Android:** Play Store'dan **Expo Go** kurun, uygulamadaki tarayıcıyla
  QR'ı okutun.
- **iPhone:** App Store'dan **Expo Go** kurun, **Kamera** uygulamasıyla
  QR'ı okutun.

Uygulama telefonda açılır ve canlı veriyi çeker. Kod değiştikçe
telefondaki ekran kendiliğinden yenilenir.

### Aynı ağda değilseniz

```bash
npx expo start --tunnel
```

Daha yavaş ama farklı ağlardan çalışır.

### Expo Go yeterli mi

Evet. Projedeki yerel modüllerin tamamı Expo Go içinde var:
`expo-router`, `expo-secure-store`, `expo-splash-screen`,
`react-native-safe-area-context`, `react-native-screens`,
`react-native-webview`. Ayrı bir derleme gerekmiyor.

Mağazaya göndermek için derleme ayrı konudur —
[`../MOBIL-MAGAZA.md`](../MOBIL-MAGAZA.md).

---

## Tarayıcıda açmak

```bash
npx expo export --platform web --output-dir /tmp/web
```

**SPA geri dönüşü olan bir sunucu gerekiyor**: `python -m http.server`
`/takvim` gibi yolları 404 veriyor, çünkü Expo Router gerçek yol
kullanıyor. Bilinmeyen yolu `index.html`e düşüren küçük bir sunucu yeterli.

Tarayıcıda **CORS** engeli var: `netaris.net` `Access-Control-Allow-Origin`
göndermiyor. Yerel uygulamada böyle bir sınır **yok**; bu yalnızca web
çıkışının sorunu.

---

## Dizin yapısı

```
app/                      expo-router — dosya adı = adres
  (sekmeler)/             alt gezinmedeki beş bölüm
    index.tsx             Ana Sayfa
    piyasalar.tsx  arastirma.tsx  senaryolar.tsx  profil.tsx
  haber/[slug].tsx        haber detayı
  analiz/[slug].tsx       araştırma / bilanço detayı
  varlik/[kod].tsx        varlık detayı
  haberler.tsx  takvim.tsx  varliklar.tsx  ara.tsx
  senaryo-yaz.tsx  hesap-sil.tsx
  _layout.tsx             kök yerleşim: tema + oturum sağlayıcı

src/
  api.ts                  besleme ve worker istemcisi; tek hata türü
  tema.tsx                renkler stil.css'ten; ilk açılış yedeği
  tema-yedek.ts           ÜRETİLİYOR — elle düzenlemeyin
  oturum.tsx              jeton expo-secure-store içinde
  veri.ts                 yükleniyor / hata / veri kancası
  bilesen.tsx             kartlar, durum ekranları, etiketler
  govde.tsx               makale gövdesi (bilanço tabloları için WebView)

sozlesme-sinamasi.mjs     besleme ↔ uygulama alan sözleşmesi
ikon_uret.py              uygulama ikonlarını markadan üretir
eas.json                  derleme profilleri
```

---

## Değiştirilmemesi gerekenler

**`src/tema-yedek.ts` üretiliyor.** `site/statik/stil.css`ten
çıkarılıyor; elle düzenlerseniz `site/test_tema_belirtec.py` kırmızıya
döner. Yeniden üretmek:

```bash
python site/tema_yedek_yaz.py
```

**Renkler uygulamaya gömülmüyor.** Palet `/v1/tema.json`dan okunuyor.
Renk değiştirmek isterseniz `site/statik/stil.css`i değiştirin;
uygulamaya kendiliğinden geçer.

**Senaryo ölçüt listesi uygulamada yok.** `/v1/senaryo-kurallari.json`dan
geliyor, kaynağı web formunun kendisi. Üçüncü bir kopya yazmayın.

---

## Sınamalar

```bash
# besleme ↔ uygulama sözleşmesi (site üretildikten sonra)
node mobil/sozlesme-sinamasi.mjs

# tip denetimi
cd mobil && npx tsc --noEmit

# proje sağlığı
cd mobil && npx expo-doctor

# paketin gerçekten derlendiği
cd mobil && npx expo export --platform android --output-dir /tmp/mp
```

Sözleşme sınaması CI'da da koşuyor: `site/test_mobil_sozlesme.py` onu
çağırıyor ve `cikti_sinamalari.py` tarafından **üretimden sonra**
seçiliyor. Besleme eksikse dağıtım kapısı kırmızı döner.

---

## Tasarım kuralları

Bunlar süs değil; her biri ölçülmüş bir kusurdan geliyor.

- **Sahte veri yok.** Veri gelmezse yükleniyor / hata / boş halleri
  ayrı ayrı gösterilir. "Veri yok" ile "veri gelemedi" farklı şeylerdir.
- **Piyasa değeri tarihiyle birlikte basılır.** Sayı tek başına canlı
  fiyat izlenimi veriyor.
- **Lisanssız seri gösterilmez.** BIST 100, S&P 500, Nasdaq, DAX —
  dağıtım lisansı Netaris'te değil. Sebebi ekranda yazılı.
- **Fotoğraf atfıyla basılır.** Atıf yoksa fotoğraf da basılmaz.
- **Ticari kaynağın adı ve bağlantısı görünür.**
- **Dokunma hedefi en az 44 piksel.**
- **Her ekranda açık ve koyu tema çalışır.**
