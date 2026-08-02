# Faz 1 Spesifikasyonu — AI Bilanço Analisti

**Sürüm:** 1.0 · 30 Temmuz 2026
**Kaynak:** Senin 10 maddelik analiz çerçeven + AI Skoru önerisi
**Durum:** Skor motoru yazıldı ve test edildi; veri yolu açık

---

## Ürün tanımı

> Finansal tablo aktaran değil, **gerekçesiyle analiz eden** bir yapay zekâ analisti.

Her bilanço için üç çıktı üretilir:

1. **Bilanço Kalitesi Skoru** — 100 puan, koddan hesaplanır, kuralları yayımlanır
2. **Tek cümlelik özet** — skorun en güçlü ve en zayıf tarafını işaret eder
3. **Analiz yazısı** — 10 boyutu gerekçeleriyle açan metin

---

## Onaylanan üç karar

| Karar | Seçim | Gerekçe |
|---|---|---|
| **Skor çerçevesi** | Bilanço kalitesi skoru, fiyattan tamamen bağımsız | Derecelendirme yayımlamak SPK izni gerektirir. Skor yalnızca defterin sağlığını ölçer; hisseler skora göre asla sıralanmaz. |
| **Beklenti verisi** | Şirket öngörüsü + geçmiş trend | Analist konsensüsü lisanslı ve pahalı. Şirketin KAP'ta yayımladığı öngörü yasal olarak temiz; son 4 çeyrek ortalaması sıfır maliyetli ölçüt. |
| **Sektör kapsamı** | Önce yalnızca BIST rakipleri | THY ↔ Pegasus aynı muhasebe esası (TMS 29), aynı para birimi, aynı takvim. Delta/Ryanair TMS 29 uygulamıyor — kıyas ölçü birimi tuzağı taşıyor. |

---

## 10 boyut → uygulanabilirlik

| # | Senin maddesi | Durum | Gerekli veri |
|---|---|---|---|
| 1 | Satışlar (çeyreklik/yıllık büyüme) | ✅ Yazıldı | Gelir tablosu, geçmiş çeyrekler |
| 2 | Kârlılık (brüt/FAVÖK/net marj) | ✅ Yazıldı | Gelir tablosu |
| 3 | Net kâr — **neden** arttı | ✅ Yazıldı | Gelir tablosu + **dipnotlar** |
| 4 | Nakit — gerçekten para kazanıyor mu | ✅ Yazıldı | **Nakit akış tablosu** |
| 5 | Borç (net borç, karşılama, KV risk) | ✅ Yazıldı | Bilanço + gelir tablosu |
| 6 | Özkaynak (büyüyor mu, eriyor mu) | ✅ Yazıldı | Bilanço |
| 7 | Marjlar (büyüme makası) | ✅ Yazıldı | Gelir tablosu |
| 8 | Operasyonel kalite (stok/alacak sinyali) | ✅ Yazıldı | Bilanço + gelir tablosu |
| 9 | Beklenti analizi | ⚠️ Yeniden tanımlandı | Geçmiş çeyrekler (konsensüs yerine) |
| 10 | Sektör karşılaştırması | ⏳ Faz 1c | **Rakip şirketlerin tabloları** |

### 3. maddenin kritik detayı

"Net kâr neden arttı" sorusunu tam cevaplamak için faaliyet dışı kalemin **ayrıştırılması** gerekiyor:

- kur farkı
- faiz geliri
- **TMS 29 parasal kazanç/kayıp**
- iştirak/duran varlık satış kârı
- tek seferlik kalemler

Bunların tekrarlanabilirliği çok farklı: TMS 29 parasal kazanç enflasyon sürdükçe tekrar eder, iştirak satışı tek seferliktir. Motor şu an bunları **tek rakam** olarak alıyor. Ayrıştırma dipnotlardan okunmayı gerektiriyor — Faz 1b işi.

---

## Bilanço Kalitesi Skoru

### Rubrik

| Kriter | Ağırlık | Ne ölçer |
|---|---:|---|
| Gelir büyümesi | 20 | Reel hasılat büyümesi |
| Kârlılık | 20 | FAVÖK ve net marj **değişimi** |
| Nakit akışı | 20 | FNA pozitif mi · FNA/FAVÖK · SNA pozitif mi |
| Borç yönetimi | 15 | Net borç/FAVÖK · faiz karşılama |
| Marj kalitesi | 10 | Kâr-hasılat makası · faaliyet dışı payı |
| Sermaye yapısı | 10 | Cari oran · ROE değişimi |
| Trend performansı | 5 | Bu çeyrek vs son 4 çeyrek ortalaması |
| **Toplam** | **100** | |

Senin önerdiğin ağırlıkları neredeyse aynen korudum. Tek değişiklik: "Beklenti Performansı" → "Trend Performansı" (konsensüs erişilemez).

### Dört tasarım kuralı

**1. Skoru model vermez, kod hesaplar.**
Aynı tablolar her zaman aynı skoru üretir. Test edildi: iki çalıştırma `64.2500` verdi. Modelin takdirine bırakılan puan yayımlanamaz, itiraz edilemez.

**2. Ölçülemeyen kriter sıfır almaz.**
Nakit akış tablosu yoksa "nakit akışı 0/20" demek yanlıştır — veri eksikliği kötü performans değildir. Ölçülemeyen kriter hesap dışı kalır, skor **ölçülebilen puan üzerinden** normalize edilir.

**3. Kapsam düşükse skor yayımlanmaz.**
Verinin yarısı eksikken üretilen "78/100" yanıltır. Kapsam **%60'ın altındaysa** skor yayına uygun sayılmaz.

**4. Marj seviyesi değil, marj değişimi puanlanır.**
Havacılıkla çimentonun marj seviyesi kıyaslanamaz. Değişim sektör nötrdür. Seviye karşılaştırması sektör modülünün işi (Faz 1c).

### Bilinen tehlike: eksik açıklama skoru yükseltebilir

Testte ortaya çıktı — verinin çoğu eksik olan senaryo **73/100** aldı, tam veri **64/100**. Ölçülmeyen zayıf kriterler hesap dışı kaldığı için.

Bu yüzden **kapsam yüzdesi skorun yanında her zaman görünmek zorunda**, ve %60 eşiği var. Ama şunu da bilmek gerekir: kapsamı düşük şirketler yapısal olarak avantajlı görünebilir. Sektör karşılaştırması bunu kısmen dengeleyecek.

### Örnek çıktı

```
Gelir buyumesi          20.0/20    reel +40.0%
Karlilik                 4.0/20    marjlar ortalama -2.3 puan
Nakit akisi             11.9/20    FNA pozitif, FNA/FAVOK 0.58, SNA negatif
Borc yonetimi            8.7/15    net borc/FAVOK 2.84x, faiz karsilama 2.4x
Marj kalitesi            6.5/10    kar-hasilat makasi -7.7 puan, faaliyet disi pay %38
Sermaye yapisi           8.2/10    cari oran 1.36x, ROE degisimi +0.3 puan
Trend performansi        5.0/5     +40.0% vs son 4 donem ort. +29.5%
SKOR                        64/100     kapsam 100%
```

Tek cümle: *"gelir büyümesi tarafında güçlü, kârlılık tarafında zayıf görünüyor."*

### Eşikler kalibre edilmedi

Rubrikteki bütün eşikler (`HASILAT_ESIKLERI`, `BORC_FAVOK_ESIKLERI` vb.) `analiz/skor.py` içinde tek yerde, isimlendirilmiş sabitler olarak duruyor. **Hiçbiri gerçek veriyle kalibre edilmedi.** 20–30 gerçek bilanço üzerinde çalıştırıp dağılıma bakmak gerekiyor: skorlar 55–75 arasında sıkışıyorsa ayrım gücü yok demektir.

---

## Veri gereksinimi — asıl darboğaz

Senin 10 maddelik çerçeven, veri ihtiyacını **dört kat** artırıyor:

| Kaynak | Hangi boyutlar için | Durum |
|---|---|---|
| Bilanço | 5, 6, 8 | Çıkarma yolu yok |
| Gelir tablosu | 1, 2, 3, 7 | Çıkarma yolu yok |
| **Nakit akış tablosu** | **4** (en önemli boyut) | Çıkarma yolu yok |
| Dipnotlar | 3 (faaliyet dışı ayrıştırma) | Çıkarma yolu yok |
| Geçmiş 4 çeyrek | 1, 9 | Aynı × 4 |
| Rakip şirketler | 10 | Aynı × 3–5 |

**Tek şirketin tek çeyreği için 4 belge; trend için 16; sektör için 60–80.**

KAP çıkarma çözülmeden bu ölçek imkânsız. Bu, Faz 1'in **tek gerçek engeli** — kod tarafı hazır olsa da veri olmadan çalışmaz.

---

## Fazlama önerisi

Veri gerçekliği bunu üçe bölmeyi zorunlu kılıyor:

### Faz 1a — Tek şirket, tek çeyrek
Bilanço + gelir tablosu. Boyut 1, 2, 5, 6, 7, 8. Skor kapsamı ~%65 (nakit ve trend eksik, ama eşiğin üstünde).
**Bu, en kısa sürede yayına girebilecek sürüm.**

### Faz 1b — Nakit + geçmiş
Nakit akış tablosu ve son 4 çeyrek eklenir. Boyut 3 (tam), 4, 9. Skor kapsamı %100.
**Ürünün asıl farklılaştırıcısı burada devreye giriyor** — "gerçekten para kazanıyor mu" sorusu.

### Faz 1c — Sektör
BIST rakipleri eklenir. Boyut 10. Marj seviyesi karşılaştırması mümkün hale gelir.
**Rakiplerden ayrışmanın en güçlü hamlesi, ama veri yükü en ağır olanı.**

---

## Dil kuralı — senin örnek yorumun üzerine

Yazdığın örnek paragraf içerik olarak doğru. Tek düzeltme, bir cümlede:

> ~~"...**yatırımcıların** özellikle nakit akışı, borçluluk eğilimi ve faaliyet marjlarındaki değişimi yakından **takip etmesi gerekmektedir**."~~

Doğrudan "yatırımcılara" seslenip ne yapmaları gerektiğini söylemek, tavsiye sınırına yaklaşıyor. Kişisiz biçim aynı bilgiyi verir, riski taşımaz:

> "Önümüzdeki çeyreklerde **izlenmesi gereken başlıklar**: nakit akışı, borçluluk eğilimi ve faaliyet marjlarındaki değişim."

Aynı paragrafın ilk yarısında zaten bu biçimi kullanmışsın ("izlenmesi gereken başlıklar arasında yer alırken") — kural şu: **tabloyu anlat, okuyucuya görev verme.**

---

## Yazılan kod

| Dosya | İş | Test |
|---|---|---|
| `analiz/skor.py` | Skor motoru, 7 kriter, yayımlanmış eşikler | 14 test |
| `analiz/test_skor.py` | Belirlenimcilik, eksik veri, kapsam, sınırlar | ✅ geçti |
| `analiz/oranlar.py` | Nakit akışı, capex, finansman gideri eklendi | — |

Doğrulanan davranışlar: aynı girdi aynı skoru veriyor · eksik veri sıfır puan almıyor · kısmi ölçüm kapsamı şişirmiyor · düşük kapsamda skor yayına uygun sayılmıyor · skor 0–100 aralığını aşmıyor.

---

## Sıradaki adımlar

1. **API anahtarı + ilk gerçek üretim.** Hâlâ modelin ne yazdığını görmedik. Skor motoru hazır ama yorum katmanı doğrulanmadı.
2. **Prompt'u 10 boyuta göre yeniden yaz.** Mevcut şablon 5 bölümlü; senin çerçeven 10 boyut + skor yorumu istiyor.
3. **KAP çıkarma.** Faz 1a için bilanço + gelir tablosu yeterli — en dar kapsamla başlamak mantıklı.
4. **Eşik kalibrasyonu.** Gerçek veri gelince skor dağılımına bakılmalı.
5. **Veri doğrulama katmanı.** Aktif=pasif, birim kontrolü — skor yanlış veriyle çalışırsa güvenilirliği biter.
