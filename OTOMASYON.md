# Kesintisiz otomasyon — kurulum

GitHub Actions, siteyi **bilgisayarınız kapalıyken de** günde üç kez
güncelleyecek: veriyi toplar, içeriği üretir, siteyi kurar, Cloudflare'e
dağıtır ve doğrular.

Yerel depo hazır (`git init` yapıldı, ilk commit atıldı, 126 dosya).
Aşağıdaki üç adım sizde.

---

## 1 · GitHub deposu oluşturun

1. [github.com/new](https://github.com/new) adresine gidin
2. **Repository name:** `netaris`
3. **Private** seçin

   > Depoda `netaris.db` var — biriken bütün veri orada. Ayrıca gelecekte
   > taslak içerik de girecek. Private başlamak, sonradan public yapmaktan
   > kolaydır; tersi mümkün değil.

4. "Add a README" ve benzeri kutuları **işaretlemeyin** (bizde zaten var)
5. **Create repository**

Sonra bu klasörde şu komutları çalıştırın — `KULLANICI` yerine kendi
GitHub kullanıcı adınızı yazın:

```
cd "C:\Users\Lenovo\Desktop\Haber Sitesi"
git remote add origin https://github.com/KULLANICI/netaris.git
git branch -M main
git push -u origin main
```

İlk `push` sizden GitHub girişi isteyecek; tarayıcı açılır, onaylarsınız.

---

## 2 · Cloudflare dağıtım jetonu üretin

GitHub Actions'ın sitenizi yayına alabilmesi için bir jeton gerekiyor.

1. [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. **Create Token**
3. **Edit Cloudflare Workers** şablonunun yanındaki **Use template**
4. **Account Resources:** kendi hesabınız
5. **Zone Resources:** All zones (ya da boş bırakın — workers.dev için
   gerekmiyor)
6. **Continue to summary** → **Create Token**
7. Çıkan uzun metni **kopyalayın**

> Bu jeton yalnızca bir kez gösterilir. Kaybederseniz yenisini
> üretebilirsiniz — eskisini silmeyi unutmayın.

**Bu jetonu bana ya da başka kimseye göndermeyin.** Doğrudan GitHub'a
gireceksiniz; sonraki adım.

Hesap kimliğiniz de gerekiyor: Cloudflare panelinde sağ sütunda
**Account ID** olarak yazıyor.

---

## 3 · GitHub'a gizli değerleri girin

Deponuzda: **Settings → Secrets and variables → Actions →
New repository secret**

İki tane ekleyin:

| Name | Secret |
|---|---|
| `CLOUDFLARE_API_TOKEN` | 2. adımda kopyaladığınız jeton |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare panelindeki Account ID |

GitHub bunları şifreli saklar, kayıtlarda maskeler ve depoyu klonlayan
kimse göremez. Dosyaya yazılmazlar.

---

## Bitti

Otomasyon **06:00, 11:00 ve 16:00 UTC**'de çalışır — Türkiye saatiyle
**09:00, 14:00 ve 19:00**.

Elle çalıştırmak için: depoda **Actions** sekmesi → *Netaris otomasyon* →
**Run workflow**.

### Her çalıştırmada ne oluyor

```
1  Testler            5 test dosyası — biri kalırsa iş durur, site
                      eski hâliyle ayakta kalır
2  Makro göstergeler  FRED'den 12 seri, depoya yazılır
3  Haberler           RSS → çeviri → sınıflandırma → fotoğraf → sayfa
4  Teknik görünüm     Binance mumları → BTC, ETH, altın
5  Site               şablonlar işlenir, çıktı üretilir
6  Dağıtım            Cloudflare'e yüklenir
7  Doğrulama          canlı site ile yerel yapı sha256 ile karşılaştırılır
8  Geri yazma         biriken veri depoya commit edilir
```

Son adım önemli: veritabanı, çeviri önbelleği ve indirilen fotoğraflar
depoya geri yazılıyor. Böylece bir sonraki çalıştırma kaldığı yerden
devam ediyor — çeviri kotası baştan harcanmıyor, fotoğraflar yeniden
indirilmiyor, ve geçmiş makineden bağımsız kalıyor.

### Bir şey ters giderse

**Actions** sekmesinde her çalıştırmanın kaydı duruyor. Ayrıca depo
kendi içinde de tutuyor:

```
python haber_botu/beyin.py
```

`calisma` tablosunda hangi hattın ne zaman çalıştığı, başarılı mı
olduğu ve hata mesajı yazılı.

### Maliyet

Sıfır. GitHub Actions genel depolarda sınırsız, özel depolarda ayda
2.000 dakika ücretsiz. Bizim çalıştırma ~3 dakika sürüyor; günde üç kez
= ayda ~270 dakika.

---

## Yerel çalıştırma

Otomasyon dururken elle de çalıştırabilirsiniz:

```
python calistir.py            # üret, yayımlama
python calistir.py --yayinla  # üret ve dağıt
python calistir.py --durum    # yalnızca depo özeti
```
