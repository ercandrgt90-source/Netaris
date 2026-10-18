# Netaris Mobil — Faz 1 Teknik Denetim

Ölçüm tarihi: 2026-10-18. Bu belgedeki her sayı depoda ya da canlı
sitede ölçüldü; tahmin yok. Ölçülemeyen yerler açıkça "ölçülmedi"
diye işaretli.

---

## 1. Mevcut sistemin teknik denetimi

### 1.1 Yığın

| Katman | Teknoloji | Ölçülen |
|---|---|---|
| İçerik üretimi | Python 3.12 + Jinja2 (`site/insa.py`) | 2.063 `index.html` |
| Barındırma | Cloudflare Workers static assets | `site/wrangler.toml` |
| Dinamik uç | `site/worker.js` | 3.156 satır |
| Veritabanı | Cloudflare D1 | `oturum, begeni, senaryo, senaryo_oy, sayac, tel, nobet_izi, deneme, uye, yazi` |
| Otomasyon | GitHub Actions | `otomasyon.yml` (~10-50 dk), `bilanco.yml` (günlük) |
| Yerel araç zinciri | Node 24.18.1 / npm 11.16.0 | Expo derlenebilir |

### 1.2 İçerik envanteri

```
haber          1045
analiz          902
varlik           75
konu             15
olay              7
diğer (sabit)    19
---------------------
toplam         2063
```

### 1.3 Mevcut API — gerçekten ne var

`worker.js` tek bir önek altında çalışıyor: `/api/*`. Ölçülen uçlar:

**Kimlik ve hesap**
`kayit` · `giris` · `giris/google` · `giris/google/ayar` · `cikis`
`dogrula` · `ben` · `parola` · `profil` · `avatar` · `disari-aktar`

**Üye içeriği**
`yazi` (GET/POST/DELETE) · `begeni` · `begenilerim`
`senaryo` (GET/POST/DELETE) · `senaryo/{id}/oy` · `senaryo/acik`
`senaryo/hepsi` · `senaryo/one-cikan`

**Canlı ve ölçüm**
`tel` · `tel/durum` · `nobetci` · `goruntulenme` · `sayaclar`

**Yönetim**
`yonetim/ozet` · `yonetim/karar`

### 1.4 Canlı doğrulama

```
GET https://netaris.net/api/tel?limit=3      HTTP 200   19.798 B
GET https://netaris.net/api/tel/durum        HTTP 200
     öge_sayisi 78 · en_yeni 2026-10-18T14:05:08Z · besleme_sayisi 1
```

Canlı tel akışı **çalışıyor ve JSON dönüyor.** Mobil uygulamanın
"canlı yayın" bölümü için hazır bir uç var; yeniden yazmaya gerek yok.

Bir gözlem: `son_turlar` kayıtlarında FinancialJuice turları
dönüşümlü olarak `http: 429` veriyor (14:40 → 429, 14:30 → 200,
14:20 → 429). Yani tel akışı turların yaklaşık yarısında boş dönüyor.
Bu mobil işini engellemiyor ama ayrı bir kusur olarak kayda geçiyor.

### 1.5 EN ÖNEMLİ BULGU — içerik için makine okunur uç YOK

Haber, analiz, bilanço, makro ve varlık içeriğinin **tamamı yalnızca
HTML.** Makine okunur olarak var olan tek şey:

| Dosya | Boyut | İçerik |
|---|---|---|
| `/arama.json` | 563 KB | 1.276 kayıt: tür, başlık, özet, yol, kategori, kod, tarih |
| `/rss.xml` + 14 konu RSS | — | başlık + özet + bağlantı |
| `/statik/istatistik.json` | — | site geneli sayılar |
| `/tel-kurallari.json` | — | besleme kuralları |

`arama.json` bir içerik beslemesi sayılabilir ama mobil için yetersiz:
alan adları kısaltılmış (`b`, `o`, `y`), tarih **görüntü biçiminde**
(`"14 Ekim 2026"`, ISO değil), gövde yok, görsel yok, sayfalama yok,
bilanço oranları ve skor yok.

**Sonuç: yerel (native) bir uygulama bugün haber ve analiz
gösteremez.** Mobil işinin gerçek ilk adımı arayüz değil, veri
katmanıdır.

### 1.6 Oturum taşıyıcı — mobil için uyarlama gerekiyor

`site/worker.js:323`:

```
oturum=<jeton>; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=...
```

Oturum **HttpOnly çerez.** Veritabanında yalnızca SHA-256 özeti
tutuluyor (iyi tasarım). Ama yerel uygulamada HttpOnly çerez yönetimi
platforma bağlı ve kırılgan: iOS ve Android çerez depoları farklı
davranıyor, uygulama güncellemelerinde temizlenebiliyor.

Gereken **asgari** arka uç değişikliği: `oturumBul()` çerezin yanında
`Authorization: Bearer <jeton>` başlığını da kabul etsin; `giris`
yanıtı istemci istediğinde jetonu gövdede döndürsün. Mevcut web akışı
hiç değişmiyor, çerez olduğu gibi kalıyor.

### 1.7 CORS yok

`worker.js` içinde hiçbir `Access-Control-*` başlığı yok. Yerel
uygulama için sorun değil (yerel `fetch` tarayıcı CORS kurallarına
tabi değil). Ama uygulamanın web/PWA sürümü başka bir kökenden
çalışacaksa engel olur. Kayda geçiyor.

### 1.8 Tasarım sistemi var ve bilinçli kurulmuş

`site/statik/stil.css` — 332 KB, tamamı belirteç tabanlı:

```
--zemin  #f3f2ee     sıcak kâğıt zemin
--panel  #ffffff
--yazi   #17160f
--vurgu  #09726d     Netaris teal
--artis  #2f7a2e   --azalis #bb1f2e
--ust-zemin #15130d  koyu üst şerit
--r 14px   --kabuk 1320px   (yarıçap, tipo ölçeği, boşluk hepsi belirteç)
```

Bu doğrudan mobil tema belirteçlerine çevrilebilir.

### 1.9 LİSANS SINIRI — ana sayfa şartnamesiyle çatışıyor

Şartnamenin 5. bölümü ana sayfada şunları istiyor: *"BIST 100,
S&P 500, Nasdaq, DAX, altın, Brent petrol, USD/TRY ve Bitcoin"* —
son fiyat ve grafikle.

Bunların bir kısmını **yayımlama hakkımız yok.**

`haber_botu/kaynak/makro.py:129-158` bunu zaten belgeliyor ve ilgili
serileri bilinçli olarak yayından çekmiş:

| Seri | Lisans sahibi | Durum |
|---|---|---|
| BIST 100 | Borsa İstanbul | dağıtım lisansı YOK — hiç çekilmiyor |
| S&P 500, Dow Jones | S&P Dow Jones Indices LLC | yayından çekildi |
| Nasdaq Composite | Nasdaq, Inc. | yayından çekildi |
| VIX | Cboe Global Markets | yayından çekildi |
| DAX | Deutsche Börse | lisanslı — ölçülmedi, yayında fiyat yok |

Doğrulandı: `/varlik/bist100/` sayfası **hiçbir fiyat taşımıyor** —
yalnızca tanım, yapısal ilişkiler ve haber arşivi.

Yayımlanabilir olan: USD/TRY, EUR/TRY, EUR/USD (ECB), Brent, WTI
(EIA), FED politika faizi, ABD 2Y/10Y getirileri, DXY, BTC, ETH
(Binance/Kraken), TÜFE ve diğer makro seriler.

Şartnamenin kendi kuralı bu çatışmayı çözüyor: *"Sahte fiyatlar,
uydurma grafikler veya gerçekte çalışmayan canlı veriler üretme."*
Yani ana sayfa göstergeleri **lisansı bizde olan** kümeyle kurulacak;
endeksler için ya hiç fiyat gösterilmeyecek ya da TradingView
gömülüsü kullanılacak.

**TradingView gömülüsünün uygulama içi kullanım şartları doğrulanmadı.**
Web gömülüsü için atıf zorunluluğu biliniyor ve korunuyor
(`site/sablonlar/_tradingview.html` + 3 şablonda 8 gömülü). Uygulama
içinde `WebView` ile kullanmak ayrı bir izin sorusu ve **yayından önce
doğrulanmalı.** Doğrulanmadan uygulamaya endeks grafiği konmayacak.

### 1.10 Diğer teknik riskler

| Risk | Ölçülen durum |
|---|---|
| Ücretsiz AI kotası | Bilanço sayfası üretimini kısıtlıyor; mobili etkilemiyor |
| `Clodflare token.txt` | Çalışma ağacında var, git'te **takip edilmiyor**, `.gitignore`'da — ama geçmişte duruyor (`06e1975`) |
| Üye verisi | Depo herkese açık; üye verisi asla işlenmeyecek |
| Bilanço sayfalarının 51'i | Onarılamayan eski biçim; kullanıcı kararıyla bırakıldı |

---

## 2. Önerilen teknoloji yığını ve gerekçesi

### Karar: **React Native + Expo**, veriyi **statik JSON beslemesinden** alacak

### 2.1 Neden Expo, neden Flutter değil

| Ölçüt | Expo (RN) | Flutter |
|---|---|---|
| Ekibin mevcut dili | JS zaten var (`worker.js` 3.156 satır, 14 istemci betiği) | Dart sıfırdan |
| Mevcut JS'in yeniden kullanımı | `ara.js` katlama tablosu, `oturum.js` akışı taşınabilir | taşınamaz |
| OTA güncelleme | Expo Updates — mağaza turu olmadan yayın | ek altyapı |
| Derleme makinesi | EAS Build bulutta; **Mac gerekmiyor** | iOS için Mac gerekir |
| Web hedefi | aynı koddan PWA çıkar | ayrı yol |

Belirleyici olan Mac maddesi: iOS derlemesi için EAS Build bulut
kuyruğu kullanılabiliyor, yerel Mac şartı kalkıyor.

### 2.2 Neden TWA/WebView sarmalayıcı değil

Önce bunu önermiştim; şartnamenin 3. bölümü bunu dışlıyor:
*"Uygulama, masaüstü web sitesinin sıkıştırılmış kopyası gibi
görünmemeli."* Ayrıca Google Play'in **Minimum Functionality**
politikası salt web sarmalayıcıları reddediyor. Yerel arayüz hem
şartnameye hem politikaya uyuyor.

### 2.3 Veri katmanı — yeni arka uç KURULMUYOR

Mimarinin özü şu: içerik **zaten** Python hattında üretiliyor. Aynı
hattın ikinci bir temsil daha basması gerekiyor — JSON.

```
haber_botu/  (veri toplama, değişmiyor)
      ↓
site/insa.py ─┬─→ HTML sayfalar        (2.063 — dokunulmuyor)
              ├─→ RSS, sitemap          (dokunulmuyor)
              ├─→ arama.json            (dokunulmuyor)
              └─→ /v1/*.json            ← YENİ, mobil beslemesi
      ↓
Cloudflare static assets + worker.js /api/*  (üye tarafı, neredeyse değişmiyor)
      ↓
Expo uygulaması
```

Bunun avantajları ölçülebilir:

* **Yeni sunucu yok, yeni çalışma zamanı maliyeti yok.** JSON dosyaları
  HTML ile aynı statik dağıtımdan servis ediliyor.
* **Tazelik otomatik.** İçerik hattı zaten 10-50 dakikada bir koşuyor;
  JSON aynı koşuda tazeleniyor.
* **Mevcut hiçbir şey bozulmuyor.** Yalnızca yeni dosya yazılıyor; tek
  bir HTML, tek bir URL değişmiyor.
* **Tek doğruluk kaynağı.** Oranlar `oranlar.py`'den geliyor; JSON
  yeniden hesaplamıyor. (Bu kural depoda pahalı öğrenildi: aynı şeyi
  iki yerde hesaplamak yayında yanlış sayı üretti.)

### 2.4 Dışlanan seçenek: ayrı bir REST arka ucu

Şartnamenin 13. kuralı: *"Mevcut backend'i incelemeden yeni bir
backend oluşturma."* İnceledim; gerek yok. İçerik statik ve günde
birkaç kez değişiyor — bir veritabanı sorgusuyla servis etmek ek
maliyet ve ek kusur yüzeyi, ek değer yok.

---

## 3. Ekran ve gezinme haritası

Alt gezinmede beş bölüm (şartname 4. bölüm):

```
┌─ Ana Sayfa
│    piyasa şeridi (lisanslı küme) · günün önemli gelişmesi
│    öne çıkan analiz · canlı tel akışı · takip edilenler
│    → Haber detayı · Analiz detayı · Tel arşivi
│
├─ Piyasalar
│    Döviz · Emtia · Tahvil getirileri · Kripto · Makro seriler
│    (Hisse endeksleri: lisans doğrulanana kadar fiyatsız)
│    → Varlık detayı (tanım · yapısal ilişkiler · haberler · analizler)
│
├─ Araştırma
│    süzgeçler: tür · şirket · sektör · tarih
│    A. Bilanço analizi   B. Makro   C. Teknik   D. İmzalı yorum
│    → Bilanço detayı (seviye tablosu · oranlar · sektör medyanı · AI yorumu)
│
├─ Senaryolar
│    açık senaryolar · oylama · kendi senaryom · sonuçlanmışlar
│    → Senaryo detayı · Yeni senaryo
│
└─ Profil
     favoriler · kaydedilenler · okuma geçmişi · senaryolarım
     bildirim tercihleri · hesap · gizlilik
```

İkincil erişim: üstteki arama her ekranda; ekonomik takvim Ana
Sayfa'daki "Yaklaşan veriler" kartından ve Piyasalar'dan.

---

## 4. API ↔ ekran eşleştirme tablosu

`YENİ` = bu planda `insa.py`'ye eklenecek statik JSON.
`VAR` = bugün çalışan uç.

| Ekran / bileşen | Uç | Durum |
|---|---|---|
| Ana sayfa piyasa şeridi | `/v1/piyasa.json` | YENİ |
| Günün önemli gelişmeleri | `/v1/one-cikan.json` | YENİ |
| Canlı tel akışı | `/api/tel?limit=` | **VAR** |
| Tel sağlık göstergesi | `/api/tel/durum` | **VAR** |
| Haber listesi | `/v1/haber/sayfa-{n}.json` | YENİ |
| Haber detayı | `/v1/haber/{slug}.json` | YENİ |
| Araştırma listesi + süzgeç | `/v1/analiz/sayfa-{n}.json` | YENİ |
| Analiz / bilanço detayı | `/v1/analiz/{slug}.json` | YENİ |
| Sektör medyanı kıyası | analiz JSON'u içinde | YENİ |
| Varlık dizini | `/v1/varlik.json` | YENİ |
| Varlık detayı | `/v1/varlik/{kod}.json` | YENİ |
| Ekonomik takvim | `/v1/takvim.json` | YENİ |
| Arama | `/v1/arama.json` (ISO tarihli, genişletilmiş) | YENİ |
| Site istatistikleri | `/statik/istatistik.json` | **VAR** |
| Kayıt | `POST /api/kayit` | **VAR** |
| Giriş (e-posta) | `POST /api/giris` | **VAR** + Bearer eki |
| Giriş (Google) | `POST /api/giris/google` | **VAR** + Bearer eki |
| Oturum bilgisi | `GET /api/ben` | **VAR** + Bearer eki |
| Çıkış | `POST /api/cikis` | **VAR** |
| Profil / parola / avatar | `POST /api/profil` vb. | **VAR** |
| Beğeni / favori | `POST /api/begeni`, `GET /api/begenilerim` | **VAR** |
| Senaryo listesi | `GET /api/senaryo`, `/api/senaryo/acik` | **VAR** |
| Senaryo oluştur / sil | `POST`/`DELETE /api/senaryo` | **VAR** |
| Senaryo oy | `POST /api/senaryo/{id}/oy` | **VAR** |
| Öne çıkan senaryo | `GET /api/senaryo/one-cikan` | **VAR** |
| Üye yazıları | `/api/yazi` | **VAR** |
| Veri dışa aktarma (KVKK) | `GET /api/disari-aktar` | **VAR** |
| Görüntülenme sayacı | `POST /api/goruntulenme` | **VAR** |
| Bildirimler | — | **ENGELLİ**, aşağıya bakın |
| AI araştırma sohbeti | — | **ENGELLİ**, aşağıya bakın |

### Engellenen iki özellik

**Bildirimler.** Hiçbir arka uç parçası yok: cihaz jetonu tablosu yok,
gönderim işi yok, tercih alanı yok. Gerekenler: D1'de `cihaz` tablosu,
`POST /api/cihaz` kaydı, FCM/APNs kimlik bilgileri (GitHub Secrets ya
da `wrangler secret put` ile — **asla depoya ya da sohbete
yazılmayacak**) ve bilanço/haber hattına bağlı bir tetikleyici.
Şartnamenin kuralı korunacak: *"Gerçek bir olay veya doğrulanmış
tetikleyici olmadan bildirim gönderme."* Faz 4.

**AI araştırma deneyimi.** Mevcut AI yalnızca üretim hattında, yorum
yazmak için kullanılıyor; etkileşimli bir uç yok. Dahası bugünkü
ücretsiz sağlayıcı ölçülen oranda sayı uyduruyor (25 denemenin 24'ü
"girdide olmayan sayı" diye reddedildi), yani kullanıcıya doğrudan
açılamaz. Sohbet arayüzü **sahte cevapla doldurulmayacak**; ya ödemeli
sağlayıcı kararı verilir ya da özellik Faz 4'e kalır.

---

## 5. Önceliklendirilmiş geliştirme planı

| Faz | İş | Mevcut yapıya dokunuyor mu |
|---|---|---|
| **1** | Teknik denetim (bu belge) | hayır |
| **2a** | `/v1/*.json` beslemesi `insa.py` içinde + koruma sınaması | **sadece yeni dosya** |
| **2b** | Tema belirteçlerini `stil.css`'ten çıkarıp paylaşılan JSON'a | hayır |
| **3a** | Expo iskeleti, gezinme, tasarım sistemi | hayır |
| **3b** | Ana Sayfa + Haber + Araştırma, gerçek veriyle | hayır |
| **3c** | Bearer oturum desteği (`worker.js`, çerez korunarak) | **geriye dönük uyumlu ek** |
| **3d** | Giriş, profil, favoriler | hayır |
| **4a** | Piyasalar ekranı (lisanslı küme) | hayır |
| **4b** | Senaryolar + oylama | hayır |
| **4c** | Ekonomik takvim | hayır |
| **4d** | Bildirimler (D1 `cihaz` tablosu + FCM) | **yeni tablo** |
| **5** | Erişilebilirlik, performans, mağaza hazırlığı | hayır |

### Google Play — bireysel hesap (kullanıcı kararı, 2026-10-18)

| Madde | Durum |
|---|---|
| Play geliştirici hesabı | 25 USD, bir kez |
| **12 test kullanıcısı × 14 gün** | Bireysel hesaplar için **zorunlu** — kapalı test şartı |
| Uygulama imzalama | Play App Signing, ücretsiz |
| EAS Build | ücretsiz kademe var; öncelikli kuyruk ücretli |
| Veri güvenliği formu | üyelik + sayaç + bildirim verisi bildirilecek |
| Haber uygulaması politikası | kaynak ve yazar görünürlüğü zaten korunuyor |
| AI içerik bildirimi | otomatik analizler açıkça etiketli olacak |
| Apple App Store | 99 USD/yıl — **iOS yayını ayrı karar** |

Takvimdeki gerçek darboğaz 12 test kullanıcısı × 14 gün: teknik iş
bitse bile Play yayını en az iki hafta sonra mümkün.

### Tasarım kimliği — ölçüm kararı değiştirdi

İlk bakışta şartnamenin koyu lacivert + elektrik mavisi paletini
(`#0A0E14`, `#2563EB`) uyarlamayı önerecektim. Ölçüm başka bir şey
gösterdi: **sitenin zaten tam bir koyu teması var** ve bilinçli
kurulmuş.

`stil.css` dört ayrı blokta tema tanımlıyor — taban `:root`,
`@media (prefers-color-scheme: dark)` içindeki
`:root:not([data-tema="light"])`, `:root[data-tema="dark"]` ve
`:root[data-tema="light"]`. Çıkarılan palet:

| Jeton | Açık | Koyu |
|---|---|---|
| `--zemin` | `#f3f2ee` | `#14130f` |
| `--panel` | `#ffffff` | `#1e1c17` |
| `--yazi` | `#17160f` | `#f3f1ea` |
| `--vurgu` | `#09726d` | `#2dd4bf` |
| `--artis` | `#2f7a2e` | `#5fc45c` |
| `--azalis` | `#bb1f2e` | `#fa6b73` |

Koyu tema sıcak bir siyaha ve parlak teal vurguya dayanıyor;
artış/azalış renkleri koyu zeminde erişilebilirlik için ayrıca
parlatılmış. Yani uygulama için yeni bir palet **uydurmaya gerek
yok** — karar verilmiş ve yayında sınanmış.

**Uygulanan çözüm:** renkler uygulamaya gömülmedi. `tema_belirtec.py`
`stil.css`i ayrıştırıp `/v1/tema.json` yazıyor; uygulama onu okuyor.
İlk açılış için `mobil/src/tema-yedek.ts` **üretiliyor** (elle
yazılmıyor) ve `test_tema_belirtec.py` dosyanın CSS ile bire bir aynı
olduğunu sınıyor. Böylece palet tek yerde duruyor; ayrışırsa sınama
kırmızıya dönüyor.

Şartnamenin paleti istenirse `stil.css` üzerinden değiştirilir ve
uygulamaya kendiliğinden geçer.

---

---

## Faz 2 ve 3a — yapılan iş (2026-10-18)

### Yazılan dosyalar

| Dosya | İş |
|---|---|
| `site/mobil_besleme.py` | `/v1/*.json` beslemesini kuran saf modül |
| `site/test_mobil_besleme.py` | 63 sınama; 10 mutasyon yakalandı |
| `site/tema_belirtec.py` | `stil.css` → tema belirteçleri |
| `site/test_tema_belirtec.py` | 57 sınama, yedek paletin ayrışmasını da yakalıyor |
| `site/tema_yedek_yaz.py` | Yedek paleti yeniden üretir |
| `site/insa.py` | Besleme hatta bağlandı (+ öne çıkan seçimi tek değişkene) |
| `mobil/` | Expo SDK 58 · RN 0.88 · React 19.3 · TypeScript 6 |
| `mobil/sozlesme-sinamasi.mjs` | Besleme ↔ uygulama alan sözleşmesi |

### Ölçülen sonuç

```
mobil beslemesi: 1360 dosya (/v1/)
  haber   1069 kayıt · 45 sayfa
  analiz   233 kayıt · 10 sayfa
  piyasa    10 kalem · lisanssız kaçak YOK
  boyut    7,9 MB
site sınamaları: 72/72 yeşil
Android paketi: 1.155 modül · 2,6 MB Hermes bytecode
TypeScript: hata yok
```

Mevcut yapıya etkisi: **tek bir HTML, tek bir URL değişmedi.**
Besleme yalnızca yeni dosya yazıyor ve site haritasına girmiyor.

### Bu turda bulunan ve düzeltilen kusurlar

1. **Besleme boş slug'lı analizi listeye alıyordu.** `Analiz.yol`
   slug'dan türetiliyor, yani slug boşken yol boş değil — `/analiz//`
   oluyor. Yalnızca yolu denetlemek bu kaydı geçiriyordu: kart
   listede görünür, detay dosyası yazılmaz, okur 404 görür. Kendi
   sınamam yakaladı.
2. **Gerçek veri sınaması atıldı.** 120 haberden 0 kayıt üretti ve
   `if _kayitlar:` yüzünden bölümün tamamı sessizce atlandı — sınama
   yeşil yazıyordu. Sebep: `yol` alanı `gundem.json`da yok, inşa
   anında atanıyor. Artık **sıfır kayıt bir başarısızlık.**
3. **CSS ayrıştırıcısı `@media print` paletini sitenin paleti sandı.**
   İlk çıktı `--zemin #fff`, `--yazi #000` verdi. İki sebep: 610
   yorumun 17'sinde süslü parantez var, ve `:root` dosyada sekiz
   yerde geçiyor — biri baskı, biri koyu tema medya sorgusu içinde.
   Ayrıştırıcı artık yorumları soyuyor ve at-kural bağlamını takip
   ediyor; `print`, `prefers-contrast`, `forced-colors` dışlanıyor.
4. **Üretilen TypeScript derlenmedi.** CSS'te yazı tipi yığını birden
   çok satıra yayılmış, yani jeton değeri gerçek satır sonu
   taşıyordu (TS1002). Ayrıştırıcı artık boşluk dizilerini tek
   boşluğa indiriyor.
5. **`react` 19.3.0 ile `react-dom` 19.3.1 çakışıyordu** ve
   `react-native-webview` kurulumunu engelliyordu. `react-dom`
   şablonun seçtiği sürüme sabitlendi.

Bir de yanlış teşhis kayda geçiyor: `ticari` alanını dizge sanıp
"gerçek bir kusur" dedim. `repr()` ile okuduğum için `True` bool'u
dizge gibi göründü. Alan sağlam — JSON'da gerçek `true`/`false`.

### Henüz yapılmayanlar

* Bearer oturum desteği (`worker.js`) — Faz 3c
* Uygulama içi giriş, favoriler, senaryo yazma — oturum sonrası
* Ekonomik takvim beslemesi ve ekranı — Faz 4c
* Bildirimler — Faz 4d, arka uç gerekiyor
* Varlık detay beslemesi (`/v1/varlik/*`)
* Marka ikon seti (şu an Expo şablon ikonları duruyor)
* Uygulama mağaza görselleri ve metinleri

### Dağıtım — doğrulandı (2026-10-18 16:09 UTC)

`/v1/` beslemesi **canlıda**. Üretim üzerinde, yerel çıktıda değil:

```
/v1/surum.json          HTTP 200    382 B   üretildi 16:09:48Z
/v1/tema.json           HTTP 200  3.979 B
/v1/piyasa.json         HTTP 200  1.497 B
/v1/haber/sayfa-1.json  HTTP 200 19.343 B
/v1/analiz/sayfa-1.json HTTP 200 18.895 B

haber 1.077 kayıt / 45 sayfa · analiz 233 kayıt
```

Canlı veri üzerinde kural denetimi (3 haber sayfası, 72 kayıt):

```
lisanssız seri                 0
atıfsız fotoğraf               0
atıfsız ticari kayıt           0
ISO olmayan tarih              0
slug'ı boş analiz              0
her piyasa kalemi veri tarihli EVET
canli_degil bayrağı            True
tel akışı statik               False
tema: zorunlu jetonlar iki temada da  TAM
```

Worker tarafı da doğrulandı: oturumsuz `/api/ben` yine `401` +
`{"uye":null}` (değişmedi), geçersiz Bearer jetonu reddediliyor,
bozuk başlık biçimi reddediliyor, canlı tel akışı ve senaryo uçları
çalışıyor.

Site bozulmadı: ana sayfa, araştırmalar, bilançolar, makro, arama,
giriş ve panel `HTTP 200`. Besleme **site haritasına girmiyor**
(makine için, okur için değil) — doğrulandı, `sitemap.xml` içinde
`/v1/` geçmiyor.

**Not:** Cloudflare, Python `urllib`'in varsayılan kullanıcı aracını
`403` ile reddediyor; aynı adres `curl` ile `200` dönüyor. Beslemeyi
betikle doğrulayan herkes bir `User-Agent` başlığı göndermeli.

---

## Kalan sorular ve engeller

1. **TradingView uygulama içi şartları doğrulanmadı.** Doğrulanmadan
   uygulamaya endeks grafiği konmayacak.
2. **AI sohbeti sağlayıcı kararı bekliyor.** Ücretsiz model sayı
   uyduruyor; ölçüldü.
3. **Bildirimler için FCM kimlik bilgisi gerekecek.** Sırası geldiğinde
   GitHub Secrets / `wrangler secret put` ile konacak, sohbete
   yazılmayacak.
4. **iOS yayını ayrı karar** (99 USD/yıl).
