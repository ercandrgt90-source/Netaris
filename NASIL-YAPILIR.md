# Nasıl Yapılır — Netaris Kurulum Adımları

Dört iş var. **1 ve 2 bağımsız, aynı anda yapılabilir.** 3 ve 4 sonra.

| # | İş | Süre | Maliyet |
|---|---|---|---|
| 1 | Siteyi yayına alma | ~10 dk | Ücretsiz |
| 2 | Künye bilgileri | ~5 dk | Ücretsiz |
| 3 | Anthropic API anahtarı | ~10 dk | Kredi yüklemek gerekiyor |
| 4 | TCMB EVDS anahtarı | ~5 dk | Ücretsiz |

---

## 1. Siteyi yayına alma (Cloudflare Pages)

Hazır paket masaüstündeki proje klasöründe: **`netaris-yayin.zip`**

### Adımlar

**1.** [dash.cloudflare.com](https://dash.cloudflare.com) → **Sign up**
E-posta ve şifre yeter. **Kredi kartı istemiyor.**

**2.** Sol menü → **Workers & Pages**

**3.** **Create** düğmesi → üstteki **Pages** sekmesi → **Upload assets**
(git bağlantısı isteyen seçeneği değil, bunu seç)

**4.** Proje adı: `netaris` → **Create project**

**5.** Yükleme ekranında `netaris-yayin.zip` dosyasını sürükle bırak

**6.** **Deploy site**

Bir dakika içinde `netaris.pages.dev` adresinden yayında olur. HTTPS
otomatik, bant genişliği sınırsız, ücret yok.

### Kontrol et

Açılan adreste şunları görmelisin: ana sayfada bir analiz kartı, üstte
Netaris logosu, analiz sayfasında skor kartı. Türkçe karakterler düzgün
görünmeli.

### Kendi alan adın (netaris.com aldıktan sonra)

Proje sayfası → **Custom domains** → **Set up a domain** → `netaris.com`
Cloudflare sana iki DNS kaydı verir; alan adını aldığın firmada bunları
eklersin. Sertifika otomatik gelir.

### Sonraki güncellemelerde

```powershell
cd "c:\Users\Lenovo\Desktop\Haber Sitesi\site"
python insa.py
```

Sonra proje klasöründe yeni ZIP oluşur; Cloudflare → proje →
**Create deployment** → yeni ZIP'i yükle.

---

## 2. Künye bilgileri

Dosya: `site/icerik/sayfalar/kunye.md`

Herhangi bir metin düzenleyiciyle aç (Not Defteri olur), köşeli parantezli
yerleri doldur:

```
**Yayın sahibi:** [Ad Soyad / Şirket unvanı]
**Sorumlu kişi:** [Ad Soyad]
**Adres:** [Açık adres]
**E-posta:** [iletisim@alanadi]
```

Üstteki "DOLDURULACAK" uyarı bloğunu da sil (`>` ile başlayan üç satır).

**Neden gerekli:** Eksik künye hem yasal risk taşır hem de reklam ağlarının
(AdSense vb.) onay sürecinde reddedilme sebebidir.

**Not:** Şahıs olarak da başlayabilirsin, şirket şart değil. Adres olarak
ikametgâh yazmak istemezsen bir sanal ofis adresi de olur.

Kaydettikten sonra `python insa.py` çalıştır, ZIP'i yeniden yükle.

---

## 3. Anthropic API anahtarı

**Bu adım ücretli.** Model çağrıları kullandıkça faturalanır — hesabımıza
göre içerik başına ~0,04 dolar, günde 10 içerikle ayda ~13 dolar.

### Adımlar

**1.** [console.anthropic.com](https://console.anthropic.com) → kayıt ol

**2.** Sol menü → **Billing** → **Add credits**
Başlangıç için 5 dolar yeterli; 100'den fazla içerik demek.

**3.** Sol menü → **API Keys** → **Create Key**
İsim ver (örn. `netaris`), oluştur.

**4.** Anahtarı kopyala — **bir daha gösterilmiyor**, kaybedersen yenisini
oluşturman gerekir.

### Windows'a kalıcı tanımlama

PowerShell aç, `sk-ant-...` kısmına kendi anahtarını yapıştır:

```powershell
setx ANTHROPIC_API_KEY "sk-ant-buraya-kendi-anahtarin"
```

`setx` kalıcıdır ama **yeni açtığın PowerShell pencerelerinde geçerli olur.**
Tanımladıktan sonra pencereyi kapat, yenisini aç.

### Doğrulama

```powershell
cd "c:\Users\Lenovo\Desktop\Haber Sitesi\haber_botu"
python uret.py veri/ORNEK-2025-12.txt --kurgusal
```

Artık "ANTHROPIC_API_KEY ayarlanmamis" demek yerine modele gitmeli ve
yazıyı üretmeli.

> **Güvenlik:** Anahtarı kimseyle paylaşma, ekran görüntüsüne alma, dosyaya
> yazma. Sızarsa console'dan silip yenisini oluştur.

---

## 4. TCMB EVDS anahtarı (ücretsiz)

Türkiye makro verisi için: TÜFE, politika faizi, kur, rezervler.

**1.** [evds2.tcmb.gov.tr](https://evds2.tcmb.gov.tr) → sağ üst **Giriş** →
**Kayıt Ol**

**2.** Giriş yaptıktan sonra kullanıcı adının altındaki **Profilim**

**3.** Sayfanın altında **API Key Kopyala** düğmesi

**4.** PowerShell'de:

```powershell
setx EVDS_API_ANAHTARI "buraya-kendi-anahtarin"
```

Yeni PowerShell penceresi aç, sonra:

```powershell
cd "c:\Users\Lenovo\Desktop\Haber Sitesi\haber_botu"
python makro_uret.py --sadece-veri
```

Artık "EVDS anahtari yok" demek yerine Türkiye göstergeleri de listelenmeli.

---

## Hepsi bitince

```powershell
cd "c:\Users\Lenovo\Desktop\Haber Sitesi\haber_botu"

# Yeni bir şirket için boş şablon
python uret.py --yeni THYAO 2025/12

# Şablonu doldur (veri/THYAO-2025-12.txt), sonra:
python uret.py

# Makro yorum
python makro_uret.py

# Siteyi güncelle
cd ..\site
python insa.py
```

Üretilen taslakları `site/icerik/analizler/` altında görürsün. **Okuyup
onayladıktan sonra** ZIP'i yeniden yükle.

---

## Takılırsan

Hata mesajının tamamını bana ilet. Kod tarafındaki her adım test edildi;
takılma olursa büyük ihtimalle ortam değişkeni ya da yükleme adımındadır,
ikisi de hızlı çözülür.
