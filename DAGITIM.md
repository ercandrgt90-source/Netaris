# Yayına Alma — Netaris

**Git kurulumu gerekmiyor.** Cloudflare Pages'in "doğrudan yükleme" seçeneğiyle
klasörü olduğu gibi yükleyip ücretsiz bir adres alıyorsun. Otomatik dağıtımı
(git ile) sonra kurarız.

---

## Yerelde görmek

```powershell
cd "c:\Users\Lenovo\Desktop\Haber Sitesi\site"
python insa.py --sun
```

→ http://localhost:8000 · durdurmak için Ctrl+C

Sadece üretmek (sunucu açmadan): `python insa.py`
Çıktı: `site/cikti/` klasörü — yayına gidecek olan bu.

---

## Cloudflare Pages'e yükleme

### 1. Hesap
[dash.cloudflare.com](https://dash.cloudflare.com) → ücretsiz kayıt. Kredi
kartı istemiyor.

### 2. Proje oluştur
Sol menü → **Workers & Pages** → **Create** → **Pages** sekmesi →
**Upload assets** (git bağlantısı olan seçenek değil, bu).

Proje adı: `netaris`

### 3. Klasörü yükle
`site/cikti` klasörünün **içindekileri** sürükle bırak — klasörün kendisini
değil, içindeki `index.html`, `analiz/`, `statik/` vb.

### 4. Bitti
`netaris.pages.dev` adresinden yayında olur. Ücretsiz, sınırsız bant genişliği,
otomatik HTTPS, küresel CDN.

### 5. Kendi alan adın (netaris.com alındıktan sonra)
Proje → **Custom domains** → **Set up a domain** → `netaris.com`

Alan adı Cloudflare'de değilse iki DNS kaydı eklemen istenir. Yönlendirme
tamamlanınca HTTPS sertifikası otomatik gelir.

---

## Her güncellemede

1. İçerik ekle/düzenle (`site/icerik/` altında)
2. `python insa.py`
3. Cloudflare → proje → **Create deployment** → `cikti` içeriğini yükle

Bu üç adım sıkıcı gelmeye başladığında git + otomatik dağıtıma geçeriz:
`git push` yaptığın anda site kendiliğinden güncellenir.

---

## Yayına çıkmadan önce mutlaka

- [ ] **Künye sayfasındaki köşeli parantezler** — `[Ad Soyad]`, `[Açık adres]`,
      `[iletisim@alanadi]`. Eksik künye hem yasal risk hem de reklam ağlarının
      onay sürecinde sorun çıkarır.
- [ ] **Alan adı** — `insa.py` içinde `SITE["adres"]` şu an `https://netaris.com`.
      Farklı bir adres alırsan burayı değiştir; canonical etiket, RSS, sitemap
      ve yapılandırılmış veri hepsi buradan besleniyor.
- [ ] **Kurgusal içerik** — şu an sitedeki tek analiz "Örnek Çimento" ve
      kurgusal. Sayfada uyarı bandı çıkıyor ama gerçek içerik gelince
      `site/icerik/analizler/` altından silinmeli.

## Yayına çıktıktan sonra

- [ ] **Google Search Console** — siteyi doğrula, `sitemap.xml` gönder.
      Aramada görünmenin ilk şartı bu.
- [ ] **Gizlilik sayfası** — analitik ya da reklam eklediğin gün, **eklemeden
      önce** güncellenmeli. Şu an "çerez kullanmıyoruz" diyor ve bu doğru;
      Analytics eklersen beyan ile gerçek uyuşmaz.

---

## Neden statik, neden Cloudflare

**Maliyet sıfır.** Bant genişliği sınırsız, sertifika ücretsiz, sunucu bakımı
yok, güvenlik yaması yok.

**Hız.** Sayfalar önceden üretilmiş HTML; veritabanı sorgusu yok. Harici yazı
tipi, JavaScript, izleyici de yok — tarayıcı üçüncü taraflara hiç istek
göndermiyor. Bu hem hız hem KVKK tarafında sadelik demek.

**Taşınabilirlik.** URL yapısı `/analiz/<slug>/` biçiminde. Faz 2'de bir CMS'e
geçmek gerekirse adresler korunur, biriken SEO otoritesi yanmaz.
