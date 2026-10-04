# Yazı tipi lisansları

Bu klasördeki iki dosya da **SIL Open Font License 1.1** ile dağıtılan
Google Fonts ailelerinden üretildi. OFL, değiştirmeye ve yeniden
dağıtmaya izin verir; tek koşulu yazı tipinin kendisinin ücret
karşılığı satılmaması ve lisansın birlikte taşınmasıdır.

| Dosya | Aile | Tasarımcı | Kaynak |
|---|---|---|---|
| `newsreader-tr.woff2` | Newsreader | Production Type | <https://fonts.google.com/specimen/Newsreader> |
| `archivo-tr.woff2` | Archivo | Omnibus-Type | <https://fonts.google.com/specimen/Archivo> |

## Neden kendi sunucumuzda

`fonts.googleapis.com` üzerinden bağlamak, her okur için üçüncü bir
alan adına bağlantı açar: ek DNS + TLS el sıkışması, ve okurun IP
adresinin Google'a gitmesi. İkisi de gereksiz. Dosyalar kendi
kökümüzden geliyor.

## Nasıl üretildi

Değişken eksenler sabitlendi (`opsz=18`, `wdth=100`), ağırlık aralığı
400–700'e indirildi ve glif kümesi Latin + Latin Genişletilmiş-A +
Romence virgüllü harfler + noktalama/para/ok/matematik işaretleriyle
sınırlandı.

Kesim sınırı **içerikten değil, Unicode bloklarından** geliyor. Sitede
o an basılan karakterlere göre kesmek, yarın yayımlanacak tek bir
Lehçe ada ya da sembole takılıp sessizce yedek yazı tipine düşerdi.

Üretim betiği: `site/yuz_kes.py`. Kapsam sınaması:
`site/test_yuz.py` — basılan her karakterin kapsandığını doğrular.
