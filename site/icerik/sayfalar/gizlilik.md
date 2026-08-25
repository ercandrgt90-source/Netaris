---
slug: gizlilik
baslik: Gizlilik ve Çerez Politikası
ozet: Hangi verilerin işlendiği, çerez kullanımı ve KVKK kapsamındaki haklar.
---

Son güncelleme: 23 Ağustos 2026

## Kısaca

Netaris'i **üye olmadan** kullanırken sizden hiçbir kişisel veri istenmez.
Ziyaret sayımı için Google Analytics kullanılır ve **onayınız olmadan çerez
yazılmaz**: onay vermezseniz yalnızca kimliksiz bir sayfa sayısı tutulur.
Sayfa üstündeki fiyat şeridi ve ziyaret sayımı için tarayıcınız birkaç dış
servise istek gönderir; ayrıntısı aşağıda.

**Üye olduğunuzda** hesabınızı kurmak ve oturumunuzu sürdürmek için ad,
e-posta ve oturum bilgisi işlenir. Bu bölüm yalnızca üye olan ziyaretçiler
için geçerlidir.

## Üyelik ve hesap verileri

Üyelik **isteğe bağlıdır**; sitenin haber, analiz ve veri içeriğinin tamamı
üye olmadan okunabilir.

Üye olduğunuzda aşağıdaki veriler işlenir:

| Veri | Neden | Nerede saklanır |
|---|---|---|
| Ad | Yazı ve senaryolarda künye | Cloudflare D1 (veritabanı) |
| E-posta | Hesap kimliği, doğrulama | Cloudflare D1 |
| Parola özeti | Girişte doğrulama | Cloudflare D1 — parolanın kendisi **saklanmaz** |
| Google hesap kimliği | Google ile giriş seçildiyse | Cloudflare D1 |
| Kayıt ve son giriş anı | Hesap güvenliği | Cloudflare D1 |
| Senaryo ve yazılarınız | Yayımlamak üzere gönderdikleriniz | Cloudflare D1 |

Parolanız düz metin olarak **hiçbir yerde tutulmaz**; yalnızca geri
döndürülemez bir özeti saklanır.

**Google ile giriş.** Bu seçeneği kullanırsanız kimlik doğrulaması Google
tarafından yapılır ve bize yalnızca adınız, e-posta adresiniz ve Google hesap
kimliğiniz iletilir. Google'ın kendi gizlilik politikası bu işlem için
geçerlidir.

## Çerezler

| Çerez | Ne zaman | Amaç | Süre | Özellikler |
|---|---|---|---|---|
| `netaris_oturum` | Giriş yaptığınızda | Oturumunuzu açık tutmak | 30 gün | `HttpOnly`, `Secure`, `SameSite=Lax` |
| `_ga`, `_ga_*` | **Yalnızca çerez onayı verirseniz** | Google Analytics ziyaret ölçümü | 2 yıl | Google tarafından yazılır |

`netaris_oturum` zorunlu bir işlev çerezidir: onsuz giriş yapılamaz. Reklam,
profilleme veya siteler arası takip amacıyla kullanılmaz ve üçüncü taraflarla
paylaşılmaz. Çıkış yaptığınızda silinir.

**Analitik çerezi yalnızca siz onay verirseniz yazılır.** Sitenin altında
çıkan bandda "Sadece gerekli" derseniz `_ga` çerezi hiç oluşturulmaz.
Kararınız tarayıcınızın yerel deposunda saklanır ve her sayfada yeniden
sorulmaz. Fikrinizi değiştirmek isterseniz tarayıcınızın site verilerini
temizlemeniz yeterli; band yeniden çıkar.

**Onay vermeyen ve üye olmayan ziyaretçinin tarayıcısına bu siteye ait
hiçbir çerez yazılmaz.** (Çerez dışında bir istisna vardır: görüntülenme
sayacının aynı sayfayı gün içinde tekrar saymaması için tarayıcınızın yerel
deposuna bir gün işareti yazılır. Ayrıntısı aşağıda.)

## Ziyaret sayımı (analitik)

Site **Google Analytics 4** kullanır (ölçüm kimliği `G-LSJK3F2FC5`).
Daha önce Cloudflare Web Analytics kullanılıyordu; 25 Ağustos 2026'da
değiştirildi.

Google Analytics **onay moduyla** çalışır ve varsayılan durumu
**reddedilmiştir**:

| | Onay vermeden | Onay verdikten sonra |
|---|---|---|
| Çerez | **yazılmaz** | `_ga`, `_ga_*` yazılır |
| Kalıcı kimlik | **atanmaz** | atanır |
| Toplanan | kimliksiz sayfa sayısı | oturum, yönlendiren, ülke, cihaz |

Her iki durumda da tarayıcınız Google'ın sunucusuna (`googletagmanager.com`)
istek gönderir ve bu istekte **IP adresiniz Google'a ulaşır**. Google IP'yi
konum tahmini için kullanıp saklamadan atar, ancak isteğin kendisi
engellenemez — bunu bilerek kabul etmeniz gerekir.

Reklam ve kişiselleştirme sinyalleri (`ad_storage`, `ad_user_data`,
`ad_personalization`) **her durumda kapalıdır**; onay verseniz bile
açılmaz. Netaris reklam göstermiyor.

Analitiği tümüyle kapatmak isterseniz bandda "Sadece gerekli" seçeneği ya da
tarayıcınızın betik engelleme özelliği yeterlidir; sitenin işleyişi
etkilenmez.

## Görüntülenme ve beğeni sayacı

Haber ve analiz sayfalarında **görüntülenme** ve **beğeni** sayısı gösterilir.
Bu sayım Netaris'in kendi sunucusunda tutulur; üçüncü bir tarafa gitmez.

**Ne saklanır:** yalnızca sayfanın adresi ve o adresin açılma sayısı.
IP adresiniz, tarayıcı bilginiz veya size ait herhangi bir kimlik
**saklanmaz**. Kim olduğunuz sorulmaz ve kaydedilmez.

**Bu sayı tekil ziyaretçi sayısı değildir**, sayfa açılış sayısıdır. Aynı
kişi farklı günlerde açarsa birden çok kez sayılır. Daha kesin bir sayım
için ziyaretçiyi tanımak gerekirdi ve bunu tercih etmiyoruz.

**Tarayıcınızda tutulan tek şey:** aynı sayfayı gün içinde yenilediğinizde
sayacın şişmemesi için tarayıcınızın *yerel deposuna* (`localStorage`) bir
gün işareti yazılır. Bu bir çerez değildir, sunucuya gönderilmez ve
yalnızca sizin cihazınızda kalır. Tarayıcı verilerini temizlerseniz silinir.

**Beğeni üyelik gerektirir.** Beğendiğiniz sayfaların listesi hesabınıza
bağlı olarak saklanır; hesabınızı silerseniz beğenileriniz de silinir.
Üye değilseniz beğeni düğmesi sizi giriş sayfasına yönlendirir ve
tarayıcınıza hiçbir kayıt yazılmaz.

## Barındırma kaynaklı teknik kayıtlar

Site Cloudflare üzerinde yayımlanmaktadır. Bu tür hizmetler teknik zorunluluk
gereği isteklere ilişkin kayıt (IP adresi, tarayıcı bilgisi, istenen sayfa,
zaman damgası) tutabilir. Bu kayıtlar sağlayıcının güvenlik ve altyapı
amaçlarıyla tuttuğu teknik kayıtlardır.

## Fiyat şeridi ve dış servisler

Sayfaların üstündeki fiyat şeridi güncel verileri göstermek için tarayıcınızdan
şu adreslere istek gönderir:

- **api.binance.com** — kripto para ve USDT/TRY paritesi için, gerçek zamanlı
- **api.frankfurter.app** — Avrupa Merkez Bankası referans döviz kurları için,
  günlük

Bu istekler doğrudan sizin tarayıcınızdan yapılır ve bizim sunucumuzdan geçmez.
Teknik zorunluluk gereği ilgili servisler bu isteklerde **IP adresinizi ve
tarayıcı bilgilerinizi** görür. Bu servislere tarafımızca herhangi bir kişisel
veri gönderilmez; istek yalnızca fiyat verisi talebinden ibarettir.

Şeritte çerez kullanılmaz ve hiçbir bilgi saklanmaz. Tarayıcınızda JavaScript
kapalıysa ya da bu adresler engellenmişse şerit yalnızca resmî istatistik
kurumlarının günlük verileriyle çalışmaya devam eder; sitenin geri kalanı
etkilenmez.

Bu servislerin kendi gizlilik politikaları geçerlidir.

## Borsa İstanbul verisi (TradingView)

Ana sayfadaki **Borsa İstanbul** şeridi ve bilanço analizlerindeki hisse
fiyat grafiği **TradingView** tarafından sağlanmaktadır. Sebebi hukuki:
BIST verisini kendimiz yayımlamak Borsa İstanbul veri dağıtım lisansı
gerektiriyor; TradingView'in widget'ında lisans sağlayıcıdadır.

Bu içerik **tarayıcınıza doğrudan TradingView'dan yüklenir** ve teknik
zorunluluk gereği TradingView **IP adresinizi ve tarayıcı bilgilerinizi**
görür. TradingView kendi çerezlerini yazabilir ve kendi gizlilik
politikası geçerlidir.

Önemli iki nokta:

- **Widget yalnızca ekranınıza girerse yüklenir.** O bölüme hiç
  inmezseniz TradingView'a hiçbir istek gitmez.
- **Veri 15 dakika gecikmelidir** ve Netaris'in kendi ölçümü değildir.
  Sitenin kendi fiyat şeridi ayrı bir kutudadır ve kamu kaynaklı
  verilerden (Fed, ECB, EIA, TCMB) oluşur.

Bu içeriği hiç yüklememek isterseniz tarayıcınızın betik engelleme
özelliğini kullanabilirsiniz; sitenin geri kalanı etkilenmez.

## Reklam ve profilleme

Sitede reklam ağı, davranışsal reklam kodu veya profilleme amaçlı izleme
**bulunmamaktadır**. Verileriniz üçüncü taraflara satılmaz veya pazarlama
amacıyla aktarılmaz.

## Saklama süresi

Hesap verileriniz üyeliğiniz sürdüğü sürece saklanır. Hesabınızın silinmesini
talep ettiğinizde hesap kaydınız ve ona bağlı oturum bilgisi silinir.
Yayımlanmış katkılarınız (senaryo, yazı) talebiniz üzerine künyeden ayrılır
veya kaldırılır.

## KVKK kapsamındaki haklarınız

6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında; kişisel
verilerinizin işlenip işlenmediğini öğrenme, işlenmişse bilgi talep etme,
işlenme amacını öğrenme, düzeltilmesini veya silinmesini isteme ve işlemeye
itiraz etme haklarına sahipsiniz.

Talep ve sorularınızı [künye](/hakkimizda/#kunye) sayfasındaki e-posta adresine
iletebilirsiniz.

## Dış bağlantılar

İçeriklerimizde Kamuyu Aydınlatma Platformu gibi dış kaynaklara bağlantı
verilebilir. Bu sitelerin gizlilik uygulamalarından sorumlu değiliz; ziyaret
ettiğinizde ilgili sitenin kendi politikası geçerlidir.

## Değişiklikler

Bu politikada değişiklik yapılması durumunda güncel metin bu sayfada yayımlanır
ve yukarıdaki "son güncelleme" tarihi yenilenir. Sitenin veri işleme
uygulamalarını değiştiren bir ekleme yapılması hâlinde, değişiklik uygulamaya
alınmadan **önce** bu sayfa güncellenir.
