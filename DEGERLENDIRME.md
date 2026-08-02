# Değerlendirme — AI Finans Medya Platformu, Faz 1 Çekirdeği

**Tarih:** 30 Temmuz 2026
**Kapsam:** Bugün yazılan kod ve alınan kararlar
**Amaç:** Detaylı inceleme için artıları, eksileri ve açık riskleri tek yerde toplamak

Bu belge övgü için değil. Zayıf noktaları bilinçli olarak öne çıkardım, çünkü karar verirken işine yarayacak olan onlar.

---

## 0. ÖNCE BU: Bugün yakalanan kritik hata

Oran motorunu ilk yazdığımda **enflasyonu iki kez düşüyordu.** Bu, yayımlanmış olsaydı platformun güvenilirliğini bitirebilecek türden bir hataydı.

### Ne oldu

Türkiye'de nominal büyümenin yanıltıcı olduğunu bildiğim için motoru her büyüme rakamını TÜFE ile arıtacak şekilde yazdım. Ama doğrulamadığım bir varsayım vardı: **KAP'taki rakamların nominal olduğu.**

Doğrulayınca tablo değişti:

| Konu | Gerçek durum |
|---|---|
| TMS 29 (finansal raporlama) | BIST şirketleri **31.12.2023'te sona eren hesap dönemlerinden itibaren** uyguluyor |
| Karşılaştırmalı rakamlar | TMS 29, **önceki dönem rakamlarını da cari dönemin satın alma gücüne çeviriyor** |
| Sonuç | KAP tablolarındaki yıllık değişim **zaten reel** |
| VUK (vergi) ertelemesi 2025–2027 | **Vergi** enflasyon düzeltmesi ertelendi — TMS 29 finansal raporlaması ayrı rejim, devam ediyor. İkisi karıştırılmamalı. |

### Hatanın büyüklüğü

Aynı kurgusal veriyle, iki varsayım:

```
tms29    -> Net kâr: reel +32,3%   (doğru)
nominal  -> Net kâr: nominal +32,3%, reel -2,0%   (hatalı varsayım)
```

**34 puanlık fark ve tam ters sonuç.** Yayımladığım örnek makalenin ana tezi — "reel olarak kâr düştü" — bu hataya dayanıyordu. Hikâye "büyüyor görünen ama reel küçülen şirket"ten "reel büyüyen ama marjları daralan şirket"e dönüyor.

### Ne düzeltildi

`hesapla()` fonksiyonuna **zorunlu ve varsayılanı olmayan** `esas` parametresi eklendi:

- `EnflasyonEsasi.TMS29` → değişim zaten reel, TÜFE **verilmesi yasak**
- `EnflasyonEsasi.NOMINAL` → TÜFE **zorunlu**, verilmezse hesaplama reddedilir

Yanlış kombinasyonlar artık çalışma anında hata veriyor. Test edildi, dördü de doğru davranıyor.

### Bundan çıkan asıl ders

**Bu bir kodlama hatası değil, alan bilgisi hatasıydı.** Test yazsam da yakalamazdım — testi de aynı yanlış varsayımla yazardım. Bu tür hatalar ancak mevzuatın kendisine bakılarak yakalanır.

Platform için doğrudan sonucu şu: **finansal içerikte her muhasebe varsayımı kaynağından doğrulanmalı.** Hattaki her hesaplama için "bu rakam hangi esasta?" sorusu açıkça cevaplanmalı, sessizce varsayılmamalı.

### Bekleyen iş

Yayımladığım örnek makale sayfası **hâlâ yanlış analizi içeriyor.** Kurgusal veri olduğu açıkça yazılı, ama analitik çerçeve hatalı. Güncellenmeli — söyle, yaparım.

---

## 1. Elde ne var

| Dosya | İş | Durum |
|---|---|---|
| `analiz/oranlar.py` | Oran + büyüme + sinyal motoru | Çalışıyor, TMS 29 düzeltmesi yapıldı. **Testi yok.** |
| `analiz/ornek.py` | Kurgusal test verisi | Çalışıyor |
| `ai/guvenlik.py` | Al/sat dili taraması | Çalışıyor, 66 test geçti |
| `ai/test_guvenlik.py` | Tarama testleri | 66 doğrulama, diakritikli + diakritiksiz |
| `ai/prompt.py` | Bilanço prompt şablonu | Yazıldı, **modelde hiç denenmedi** |
| `ai/istemci.py` | Claude API katmanı | Derlendi, **hiç çağrı yapılmadı** |
| `uret.py` | Uçtan uca hat | Hat doğrulandı, API adımı test edilmedi |
| `karsilastir.py` | Opus 5 / Sonnet 5 karşılaştırması | Hazır, **çalıştırılmadı** |
| `tara_dosya.py` | Yayın kapısı (çıkış kodu 0/1) | Çalışıyor |

---

## 2. ARTILAR

### 2.1 Model hiçbir sayı üretmiyor

Bütün rakamlar, oranlar ve büyüme hesapları kodda üretiliyor; prompt'a hazır veriliyor. Modele yalnızca yorum kalıyor.

**Neden önemli:** Finansal içerikte tek uydurma rakam biriktirdiğin güveni bitirir. Dil modelleri aritmetikte güvenilmez ve hatayı kendinden emin bir tonla yapar. Bu mimari o riski tamamen kaldırıyor — model matematik yapmıyorsa matematik hatası yapamaz.

### 2.2 Veri kaynağı takılıp çıkarılabilir

`oranlar.py` verinin nereden geldiğini bilmiyor. KAP, elle giriş, üçüncü parti — hepsi aynı `Donem` nesnesini üretir.

**Neden önemli:** KAP çıkarma stratejisi hâlâ çözülmedi. Bu mimari sayesinde o karar hattın geri kalanını etkilemiyor; prototipte bir kaynak, üretimde başka bir kaynak kullanmak bedava.

### 2.3 İki kademeli yasal savunma

Al/sat dili hem prompt seviyesinde yasak, hem yayın öncesi taranıyor. Yasal uyarı metni **model tarafından değil kod tarafından** ekleniyor.

**Neden önemli:** Sabit bir yasal metnin varlığı modelin talimata uymasına bağlı olmamalı. Kötü örnek testinde 7 yasak bulgu ile engellendi — kapı çalışıyor.

### 2.4 Diakritik açığı yakalandı ve kapatıldı

Türkçe metin sahada sık diakritiksiz yazılır (`yukselecek`). Desenler diakritikli yazılırsa tarama sessizce geçirir. Hem metin hem desenler ASCII'ye katlanıyor.

**Neden önemli:** Bu tam olarak sessiz yanlış negatif üreten bir açıktı ve yasal risk taşıyordu. Testte `firsati kacirmayin` diakritiksiz yazıldı ve yakalandı.

### 2.5 Sinyal katmanı gerçek analist bakışını taklit ediyor

Yedi sinyal otomatik yakalanıyor: marj daralması, alacakların hasılattan hızlı büyümesi, stok birikimi, kâr kalitesi, borçlulukta bozulma, likidite, zarar/kâr geçişleri.

**Neden önemli:** Ürünün farklılaştırıcısı bu. Ham bildirim aktaran bot bunları görmez. "Kârın %38'i esas faaliyetten gelmiyor" tespiti, okuyucunun başka yerde bulamayacağı bilgi.

### 2.6 Belirsizlik gizlenmiyor

Sinyaller "olabilir" diliyle üretiliyor, prompt modelin bunu kesinliğe çevirmesini yasaklıyor. Zarardan kâra geçiş gibi yüzde değişimin anlamsız olduğu durumlar hesaplanmıyor, ayrı sinyal olarak raporlanıyor.

**Neden önemli:** Yatırım tavsiyesi sınırının doğru tarafında kalmanın yolu da bu.

---

## 3. EKSİLER

### 3.1 Modelin ne yazdığını kimse görmedi — en büyük boşluk

Prompt şablonu yazıldı, API katmanı kuruldu, ama **tek bir gerçek çağrı yapılmadı.** API anahtarı yok.

Yayımladığım örnek makaleyi **ben** kaleme aldım, model değil. Yani şu an elimizde:

- Modelin bu prompt'la iyi yazıp yazmadığına dair **sıfır kanıt**
- Prompt'un al/sat yasağına uyulup uyulmadığına dair **sıfır kanıt**
- Modelin verilmeyen rakam uydurup uydurmadığına dair **sıfır kanıt**
- Maliyet tahminleri **ölçüm değil**, token boyutlarından hesap

**Doğrulanmayan hipotez şu:** Bu hat gerçekten yayımlanabilir kalitede içerik üretiyor mu? Bilmiyoruz. Diğer her şey bu cevaba bağlı.

### 3.2 KAP çıkarma çözülmedi — projenin en büyük riski

Doğruladık: KAP'ın resmî API'si yok. Özel uç nokta zaman aşımına uğradı. Finansal tablolar ek dosya olarak, arayüz JavaScript ile çalışıyor. Üçüncü parti kütüphaneler ticari kullanıma uygun değil.

**Bu çözülmezse Faz 1 çalışmaz.** Şu an elimizde çalışan bir veri yolu yok — sadece kurgusal veri var.

Olası yollar, hiçbiri denenmedi:
- KAP'ın kendi "Finansal Tablo Kalem Sorgulama" aracı — yapılandırılmış veri tutuyor, araştırılmadı
- XBRL ek dosyalarını indirip ayrıştırmak — teknik olarak sağlam ama emek yoğun
- Yarı manuel giriş — reddettin, ama sezon başlarken geri dönülebilir

### 3.3 Tarama regex tabanlı — tavanı var

`guvenlik.py` desen eşleştiriyor. **Bağlamı anlamıyor.** Yakalayamayacağı ifadeler:

- "Şirketin değeri artabilir" (desende yok)
- "Bu seviyeler tarihsel ortalamanın altında" (dolaylı değerleme yargısı)
- "Analistler olumlu bakıyor" (üçüncü şahsa atıfla tavsiye)
- "Bu tabloyla portföy oluşturmak isteyenler..." (koşullu yönlendirme)

Ve tersi de var: ASCII katlaması yanlış pozitif riskini artırdı. Şu an 16 masum cümlede yanlış alarm vermiyor, ama gerçek içerik çeşitliliği bundan çok daha geniş.

**Ne yapılmalı:** İkinci bir katman — üretilen metni ayrı bir AI çağrısıyla "bu yatırım tavsiyesi sayılır mı?" diye denetlemek. Regex ilk elek, model ikinci elek olur. Bu henüz yok.

### 3.4 Veri doğrulama katmanı hiç yok

Motor girdi rakamlarını sorgusuz kabul ediyor. Yapılmayan kontroller:

- Aktif toplamı = pasif toplamı mı?
- Dönen varlıklar ≤ aktif toplamı mı?
- Özkaynak + yükümlülükler = aktif mi?
- Rakamlar makul büyüklükte mi (birim hatası: milyon/bin karışması)?
- Brüt kâr ≤ hasılat mı?

**Neden önemli:** Yanlış girdiyle motor kendinden emin şekilde yanlış çıktı üretir ve hiçbir yerde uyarı çıkmaz. Elle girişte birim hatası (bin TL / milyon TL) çok yaygın. Bu katman yazılmalı ve zor değil.

### 3.5 Sinyal eşikleri uydurma

Kodda gömülü eşikler: alacaklar hasılattan **1,3 kat** hızlıysa sinyal, faaliyet dışı kâr **%30** üstüyse sinyal, net borç/FAVÖK **0,5x** artışta sinyal, marj **2 puan** daralmada sinyal.

**Bu sayıları ben seçtim. Hiçbiri gerçek veriyle kalibre edilmedi.** Makul görünüyorlar ama:

- Çok gevşekse her şirket için sinyal üretir, gürültü olur
- Çok sıkıysa gerçek sorunları kaçırır
- Sektöre göre değişmesi gerekebilir (çimentoda stok davranışı perakendeden farklı)

**Ne yapılmalı:** 20–30 gerçek bilanço üzerinde çalıştırıp kaç sinyal ürettiğine bakmak. Şirket başına 8 sinyal çıkıyorsa eşikler gevşek.

### 3.6 Tek şirket analizi — karşılaştırma yok

Motor bir şirketi kendi geçmişiyle karşılaştırıyor. Yapmadığı: sektör ortalamasıyla, benzer şirketlerle, endeksle karşılaştırma.

**Neden önemli:** "Brüt marj 22%" tek başına az şey söyler. "Sektör ortalaması 28%, şirket 22%" çok şey söyler. Analitik değerin önemli bir kısmı burada ve şu an yok.

Bu Faz 1 için kabul edilebilir bir eksik — ama farkında olmak lazım, çünkü rakiplerden ayrışmanın en güçlü yollarından biri bu.

### 3.7 Oran motorunun testi yok

`guvenlik.py`'nin 66 testi var. `oranlar.py`'nin **hiç testi yok** — ve TMS 29 hatası tam oradaydı.

Dürüst olmak gerekirse test o hatayı yakalamazdı (testi de aynı yanlış varsayımla yazardım). Ama yakalayacağı başka şeyler var: negatif özkaynakla ROE, sıfıra bölme, zarardan kâra geçiş, eksik kalemler. Bu yollar kodda ele alınmış ama doğrulanmamış.

### 3.8 Maliyet modeli doğrulanmadı

İçerik başı $0,042 (Opus 5) / $0,017 (Sonnet 5) tahminleri, karakter sayısından kaba token çevrimiyle hesaplandı. Gerçek token sayımı yapılmadı.

Türkçe metin İngilizce'den daha fazla token üretir ve oran içeriğe göre değişir. **Gerçek maliyet tahminin 1,5 katı da çıkabilir.** Aylık $13 yerine $20 olması planı bozmaz ama bilmek gerekir.

### 3.9 Faaliyet dışı kalem ayrıştırılmıyor

"Faaliyet dışı net" tek rakam olarak giriyor. Ama içinde çok farklı şeyler var: kur farkı, faiz geliri, TMS 29 parasal kazanç/kayıp, iştirak satış kârı.

**Neden önemli:** Bunların tekrarlanabilirliği çok farklı. TMS 29 parasal kazanç enflasyon sürdükçe tekrarlanır; iştirak satış kârı tek seferliktir. Motor ikisini aynı kefeye koyuyor, yorum da öyle oluyor.

---

## 4. Karar bekleyen konular

| # | Konu | Durum |
|---|---|---|
| 1 | **Marka / alan adı** | Sen belirleyip ileteceksin |
| 2 | **Model seçimi** | Opus 5 varsayılan; karşılaştırma çalıştırılmadı |
| 3 | **KAP veri yolu** | Çözülmedi — en acil teknik konu |
| 4 | **Örnek makale sayfası** | Yanlış analizi içeriyor, güncellenmeli |

---

## 5. Önerdiğim sıra

Önem sırasına göre, en kritik önce:

1. **API anahtarı al, `karsilastir.py`'yi çalıştır.** Tek bir gerçek çıktı görmeden başka hiçbir şey inşa etmenin anlamı yok. İçerik hipotezi doğrulanmadan KAP kazıyıcısı yazmak boşa emek riski.

2. **Veri doğrulama katmanı yaz.** Küçük iş, büyük koruma. Aktif=pasif, birim kontrolü, makullük kontrolleri.

3. **KAP çıkarma yolunu çöz.** Faz 1'in bel kemiği. "Finansal Tablo Kalem Sorgulama" aracından başlamak mantıklı.

4. **Sinyal eşiklerini gerçek veriyle kalibre et.** 20–30 bilanço, kaç sinyal çıkıyor, hangileri gürültü.

5. **İkinci elek olarak AI denetimi ekle.** Regex'in göremediği dolaylı tavsiye dilini yakalamak için.

6. **Oran motoruna test yaz.** Sınır durumları: negatif özkaynak, sıfır bölen, zarar geçişleri.

---

## 6. Genel değerlendirme

**Güçlü taraf:** Mimari doğru kurulmuş. Model sayı üretmiyor, veri kaynağı takılıp çıkarılabilir, yasal savunma iki kademeli, yasal uyarı koda gömülü. Bunlar sonradan düzeltilmesi pahalı olan kararlar ve doğru tarafta.

**Zayıf taraf:** Hattın en kritik halkası — modelin gerçekten iyi yazıp yazmadığı — hiç test edilmedi. Ve besleyecek gerçek veri yolu yok.

**En değerli çıktı:** Bugün yakalanan TMS 29 hatası. Yayına geçmiş olsaydı, "reel olarak küçüldü" diyen bir analiz aslında %32 reel büyüyen bir şirket için yayımlanacaktı. Bir kez olsa toparlanır; sistematik olsa platform biter.

Bu, projenin en önemli işletme kuralını da ortaya koyuyor: **finansal içerikte her muhasebe varsayımı kaynağından doğrulanır, sessizce varsayılmaz.**
