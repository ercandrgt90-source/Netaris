# Duyarlılık matrisi — kalibrasyon dosyası

Bu tablo haber sayfalarındaki **"En çok kim etkilenir?"** bölümünü üretiyor.
Şu anki değerler **benim taslağım** — kamuya açık, tartışmasız ilişkilerden
türetildim. Sizin alan bilginizle düzeltilmesi gereken kısım burası.

## Nasıl doldurulur

`Ş` sütunu = **şiddet, 1–5**. Ölçüt şu:

| Değer | Anlamı |
|---|---|
| 5 | Gider ya da gelir kaleminin **doğrudan** parçası. Yakıt havayolunda böyledir. |
| 4 | Doğrudan ama gecikmeli ya da kısmen aktarılabilen etki. |
| 3 | Gerçek ama başka değişkenlere bağlı. |
| 2 | Dolaylı; genelde ikinci bir kanaldan geçiyor. |
| 1 | Zayıf. Kalması gerekip gerekmediği tartışılır. |

**Sadece şu üç şeyi yapmanız yeterli:**

1. `Ş` sütunundaki sayıyı düzeltin (yanlışsa).
2. `Gerekçe` sütununu düzeltin — mekanizma yanlış yazılmışsa.
3. Eksik satır ekleyin, gereksiz satırı silin.

**Yazmayın:** yön ("yükselir/düşer") ve büyüklük ("%3 artar"). Tablo
"hangi sektör ne kadar duyarlı" diyor, "ne olacak" demiyor. Yönü veriden
okuyoruz.

Dosyayı düzenleyip kaydetmeniz yeterli; ben okuyup koda çeviririm.

---


## Altın ve emtia

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Kuyumculuk / Mücevher | 5 | Doğrudan girdi ve stok değeri |
| Bankacılık | 3 | Altın mevduatı ve kıymetli maden hesapları |
| Sanayi (bakır, çelik) | 4 | Girdi maliyeti |
| Perakende | 2 | Dolaylı |

## Bankacılık

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Bankacılık | 5 | Doğrudan düzenleme muhatabı |
| Reel sektör | 4 | Kredi arzının miktarı ve maliyeti |
| GYO / İnşaat | 3 | Proje finansmanına erişim |
| Aracı kurumlar | 2 | Dolaylı |

## Borsa

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Aracı kurumlar | 5 | İşlem hacmi komisyon gelirini belirler |
| Bankacılık | 4 | Portföy ve yatırım bankacılığı |
| Halka arz adayları | 4 | Değerleme ve iştah |
| Reel sektör | 2 | Öz kaynak maliyeti üzerinden dolaylı |

## Döviz

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| İthalatçı sanayi | 5 | Ara malı maliyeti döviz cinsinden |
| Bankacılık | 4 | Döviz pozisyonu ve kredi kalitesi |
| İhracatçı sanayi | 4 | Ters yönde çalışır — gelir tarafı döviz |
| Havacılık / Turizm | 3 | Gelir döviz, gider kısmen TL |
| Perakende | 3 | İthal ürün ağırlığına göre değişir |

## Dış ticaret

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| İhracatçı sanayi | 5 | Doğrudan gelir kalemi |
| Lojistik / Liman | 4 | Hacme bağlı |
| Bankacılık | 3 | Dış finansman ve kur üzerinden |
| İç piyasa perakendesi | 2 | Dolaylı |

## Enerji

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Havayolu / Lojistik | 5 | Yakıt gider kaleminin en büyük parçası |
| Petrokimya | 5 | Girdi maliyeti doğrudan bağlı |
| Enerji üretimi | 4 | Girdi ve satış fiyatı birlikte hareket eder |
| Çimento / Demir-çelik | 4 | Enerji yoğun üretim |
| Bankacılık | 2 | Cari denge üzerinden dolaylı |

## Enflasyon

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Perakende / Gıda | 5 | Fiyatlama gücü ve stok devir hızı |
| Bankacılık | 4 | Reel getiri ve politika beklentisi |
| Konut ve kira | 4 | Kira TÜFE sepetinde ağırlıklı kalem |
| İhracatçı sanayi | 3 | Birim maliyet ve rekabet gücü |
| Savunma / Kamu ihalesi | 2 | Sözleşmeler çoğunlukla endeksli |

## Jeopolitik

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Havayolu / Lojistik | 5 | Yakıt maliyeti ve güzergâh riski |
| Enerji üretimi | 5 | Arz güvenliği ve girdi fiyatı |
| Savunma sanayi | 4 | Sipariş ve ihracat izinleri |
| İhracatçı sanayi | 4 | Pazar erişimi ve gümrük rejimi |
| Bankacılık | 3 | Ülke risk primi ve dış borçlanma maliyeti |
| Turizm | 3 | Bölgesel gerilim ziyaretçi planını etkiler |

## Konut ve kira

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| GYO / İnşaat | 5 | Doğrudan gelir ve stok değeri |
| Çimento / Demir-çelik | 4 | Bağlantılı talep |
| Beyaz eşya / Mobilya | 4 | Konut teslimine bağlı |
| Bankacılık | 3 | Konut kredisi hacmi |

## Kripto varlıklar

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Aracı platformlar | 5 | İşlem hacmi komisyon gelirini belirler |
| Bankacılık | 2 | Ödeme ve transfer kanalı |
| Perakende yatırımcı | 4 | Portföy değeri doğrudan etkilenir |

## Para politikası

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Bankacılık | 5 | Net faiz marjı ve kredi talebi doğrudan bağlı |
| GYO / İnşaat | 4 | Konut kredisi faizi talebi belirler |
| Otomotiv / Dayanıklı tüketim | 4 | Taksitli satış ve kredi kanalı |
| Perakende | 3 | İç talep üzerinden dolaylı |
| İhracatçı sanayi | 2 | Kur kanalı baskın, faiz ikincil |

## Piyasa düzenlemesi

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Aracı kurumlar | 5 | İşlem kuralları ve yükümlülükler doğrudan |
| Halka açık şirketler | 4 | Kamuyu aydınlatma yükümlülüğü |
| Bankacılık | 3 | Yatırım bankacılığı ve portföy yönetimi |
| Bireysel yatırımcı | 3 | Erişim ve koruma kuralları |

## Tarım ve gıda

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Gıda sanayi | 5 | Hammadde maliyeti doğrudan bağlı |
| Perakende / Market | 4 | Raf fiyatı ve marj |
| Gübre / Tarım kimyasalı | 4 | Talep rekolteyle birlikte hareket eder |
| Bankacılık | 3 | Tarım kredileri ve TARSİM |
| Lojistik | 3 | Hasat dönemi taşıma hacmi |

## Turizm

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Konaklama | 5 | Doğrudan gelir kalemi |
| Havayolu | 5 | Yolcu sayısı ve doluluk |
| Yeme-içme / Perakende | 4 | Turist harcaması |
| GYO — kıyı bölgeleri | 3 | Kira ve değerleme |
| Bankacılık | 2 | Cari denge üzerinden dolaylı |

## Vergi ve kamu maliyesi

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Tüm halka açık şirketler | 4 | Vergi oranı net kâra doğrudan yansır |
| Perakende / Otomotiv | 4 | ÖTV ve KDV nihai fiyata geçer |
| Bankacılık | 3 | İç borçlanma ve tahvil portföyü |
| İhracatçı sanayi | 2 | Teşvik ve iade rejimine bağlı |

## İstihdam ve ücret

| Sektör | Ş | Gerekçe (mekanizma) |
|---|:-:|---|
| Emek yoğun sanayi | 5 | Ücret gideri kâr marjının ana belirleyicisi |
| Perakende / Hizmet | 4 | Hem maliyet hem talep tarafı |
| Lojistik | 4 | Ücret gideri yüksek |
| Bankacılık | 2 | Dolaylı — iç talep üzerinden |
