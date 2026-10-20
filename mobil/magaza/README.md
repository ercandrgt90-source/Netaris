# Mağaza varlıkları

Bu klasördeki her şey **üretiliyor**, elle hazırlanmıyor. Logo ya da
uygulama değişince yeniden üretin; aksi halde mağazadaki görsel sessizce
eskir.

```bash
python mobil/magaza_gorsel.py        # öne çıkan görsel (1024×500)
python mobil/ikon_uret.py            # uygulama ikonları
```

Ekran görüntüleri gerçek uygulamadan alınıyor (aşağıda).

---

## `ekran/` — telefon ekran görüntüleri

**1242×2208 (9:16)** · Play'in istediği orana uygun, en az iki en çok
sekiz görüntü sınırının içinde.

| Dosya | Ekran | Tema |
|---|---|---|
| `1-anasayfa.png` | piyasa şeridi + günün gelişmeleri | açık |
| `2-haberler.png` | konu süzgeçli haber listesi | açık |
| `3-takvim.png` | ekonomik takvim, koşullu dallar | koyu |
| `4-piyasalar.png` | gruplu tablo, gecikmeli uyarısı | açık |
| `5-varliklar.png` | 75 varlık dizini | koyu |
| `6-arastirma.png` | tür süzgeçli araştırma listesi | açık |
| `7-senaryolar.png` | "tahmin değildir" uyarısıyla | açık |
| `8-arama.png` | çok türlü arama sonucu | koyu |

Açık ve koyu tema karışık: ikisi de markaya uygun ve ikisi de
çalışıyor.

### Nasıl üretiliyor

Uygulama web'e çıkarılıp gerçek Chrome'da 414×736 görüş alanında, 3×
piksel yoğunluğuyla açılıyor. İstekler yakalanıp `site/cikti` içindeki
**gerçek üretilmiş besleme dosyalarından** karşılanıyor.

**Maket yok, uydurma rakam yok.** Hem Play politikası hem projenin
kendi kuralı bunu dışlıyor; ekranlardaki her sayı hattın kendi
çıktısı.

Betik oturumluk: `scratchpad/magaza_goruntu.mjs`. Kurulumu
[`../README.md`](../README.md) ve `uygulamayi-gercekten-calistir`
notunda anlatılıyor.

### Yeniden üretmek gerektiğinde

- Arayüz değiştiğinde
- Veri belirgin şekilde eskidiğinde (ekranlarda tarih görünüyor)
- Yeni bir ekran eklendiğinde

---

## `one-cikan-gorsel.png`

**1024×500** · Play'in "feature graphic" alanı. Her listede en üstte,
arama sonuçlarında ve tanıtım alanlarında görünüyor.

İçinde **metin yok** ve bu bilinçli: uygulama adı ve kısa açıklama
zaten görselin altında basılıyor, üst üste binince kalabalık oluyor.
Ayrıca görseldeki metin çevrilmiyor, yani tek dile çakılıyor.

Marka işareti tam ortada, arkasında çok hafif teal parıltı. Play bazı
yerleşimlerde kenarları kırpıyor; ortada durması her kırpımda sağlam
kalmasını sağlıyor.

---

## Vektör asıl dosya — artık var (2026-10-20)

`netaris-marka.svg` deponun vektör marka aslıdır; `netaris-1024.png`
ondan çizilmiştir ve `ikon_uret.py` artık onu kaynak alır.

Vektör dosya **aranmış, bulunamamıştı.** Çözüm, 512'lik rasterin
geometrisini ölçerek geri çıkarmak oldu — raster zaten vektörden
üretilmişti (kenar yumuşatma pikselleri toplamın yalnızca %0,5'i),
yani şekiller tam olarak kurtarılabilirdi:

| Ölçülen | Değer | Nereden |
|---|---|---|
| Kalem kalınlığı | 50 | Sol kolun yatay dilimi `x=55..104` |
| N çokgen çizgisi | `M 80 431 L 80 96 L 304 367 L 304 96` | Kol merkezleri ve yuvarlak uç payı (25) |
| Çubuk A | `x=352 y=304 54×128` | Teal sütun grupları |
| Çubuk B | `x=426 y=208 54×224` | Teal sütun grupları |
| İkon köşe yarıçapı | 101,5 | `y=0` satırında opak aralık `x=101..410` |
| Çubuk köşe yarıçapı | 18 | **Ölçüldü, tahmin edilmedi** (aşağıda) |

Çubuk yarıçapı için sekiz aday (12–27) Chrome ile çizilip özgün
rasterle piksel piksel karşılaştırıldı. En küçük fark `r=18`:

    r12  ortalama fark 1.49    r18  ortalama fark 1.34  <-- en iyi
    r14  ortalama fark 1.45    r20  ortalama fark 1.35
    r16  ortalama fark 1.39    r22  ortalama fark 1.42
                               r27  ortalama fark 1.64

1,34/255 = **%0,5**; kalan fark kenar yumuşatmasıdır.

### Yeniden çizmek gerektiğinde

    node magaza/svg_ciz.mjs magaza/netaris-marka.svg cikti.png 1024

Chrome ile çizdiriyor. Betik bir **bağımlılık eklemiyor**: üretilmiş
PNG depoda duruyor, kurulum sırasında hiçbir şey çizilmiyor.

### Site varlıklarına dokunulmadı

`site/statik/marka/netaris-512.png` favicon ve apple-touch-icon
olarak yayında; olduğu gibi kaldı. Bu dizindekiler yalnızca
uygulamayı besliyor.
