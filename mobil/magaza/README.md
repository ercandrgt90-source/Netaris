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

## Eksik olan tek şey

**1024 px vektör ikon.** Depodaki en büyük marka rendisi 512×512
raster; `ikon_uret.py` onu büyütüyor ve sonuç kabul edilebilir, ama
mağaza teslimi için vektörden üretilmiş bir asıl dosya istenmeli.
Dosya geldiğinde betikte yalnızca `KAYNAK` yolu değişir.
