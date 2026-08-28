"""Gizlilik BEYANI ile sitenin GERCEK davranisi ayrismasin.

NEDEN VAR
---------
Gizlilik metni sunu yaziyordu:

    "Cerez kullanilmamakta, analitik araci calistirilmamakta...
     Sitede uyelik sistemi ve iletisim formu yoktur."

Ucu de ARTIK DOGRU DEGILDI: Google girisi, uye paneli ve oturum
cerezi eklendi; 22 Agustos'ta da Cloudflare Web Analytics.

Metnin kendi icinde su uyari vardi: "bir hizmet eklendiginde bu sayfa
EKLEMEDEN ONCE guncellenmelidir -- aksi halde beyan ile gercek
usmaz." Uyari yazilmisti ama uygulanmadi; ozelligi ekleyen (ben)
sayfaya bakmadi.

Bir uyari, kontrol edilmedigi surece yalnizca iyi niyet beyanidir.
Bu arac onu KONTROL edilebilir hale getiriyor.

NASIL CALISIR
-------------
Uretilen sayfalarda ARANAN DAVRANIS izleri ile gizlilik metnindeki
BEYAN karsilastiriliyor. Ikisi ayrisirsa hata.

Kapsam bilincli olarak dar: yalnizca "yok" diyen beyanlar
denetleniyor. "Var" diyen bir beyanin fazladan olmasi okuru
yaniltmaz; "yok" deyip VAR olmasi yaniltir.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
CIKTI = KOK / "site" / "cikti"
#: Gizlilik metni KENDI SAYFASINDA: `/gizlilik/`.
#:
#: Bir donem `/hakkimizda/` icinde bir bolumdu ve bu sabit oraya
#: baglanmisti. 2026-08-28'de sayfalar ayrildi ve denetim KIRMIZI
#: DONDU -- "TradingView gizlilik metninde HIC gecmiyor" dedi. Metin
#: yerindeydi; araç yanlis dosyaya bakiyordu.
#:
#: Dosyanin kendi eski notu ilginc: "Ilk yazimimda
#: `/gizlilik/index.html` aradim ve 'sayfa uretilmemis' aldim." Ilk
#: sezgi dogruymus; yapi arada degisti, sonra geri dondu.
#:
#: DUSUS YOK, BILEREK. Sayfa bulunamazsa denetim "gizlilik sayfasi
#: uretilmemis" deyip duruyor. `/hakkimizda/`a geri dusmek, yapi
#: yeniden degistiginde hatayi SESSIZCE gizlerdi -- ve bu aracin isi
#: tam da sessiz celiskiyi gorunur kilmak.
GIZLILIK = CIKTI / "gizlilik" / "index.html"

#: (davranis adi, sayfalarda arayacagimiz iz, beyanda YASAK kalip)
#:
#: "iz" uretilen HTML'de aranıyor; bulunursa o davranis VAR demektir.
#: "yasak" gizlilik metninde aranıyor; varsa beyan "yok" diyor demektir.
KURALLAR = (
    ("analitik",
     re.compile(r"cloudflareinsights\.com|googletagmanager|google-analytics"),
     re.compile(r"analitik arac[^.]{0,40}(çalıştırılmam|kullanılmam|yok)",
                re.I)),
    ("üyelik",
     re.compile(r'href="/kayit/"|href="/giris/"|data-giris-gerek'),
     re.compile(r"üyelik sistemi[^.]{0,40}yok", re.I)),
    ("çerez",
     re.compile(r"set-cookie|netaris_oturum"),
     re.compile(r"çerez kullanılmamakta|çerez kullanmamaktadır", re.I)),
    # TRADINGVIEW -- ucuncu taraf betigi.
    #
    # Widget ziyaretcinin IP'sini ve tarayici bilgisini TradingView'a
    # gonderiyor. Beyan bunu ACIKCA yaziyor; yazmasaydi bu kural
    # yakalardi.
    #
    # Sitenin baska hicbir ucuncu taraf betigi yok ve bu bilincli --
    # LCP 338 ms olmasinin sebebi kismen bu. Bir gun ikinci bir
    # saglayici eklenirse ayni sekilde hem beyana hem buraya girmeli.
    ("üçüncü taraf içerik",
     re.compile(r"s3\.tradingview\.com|tradingview\.js"),
     re.compile(r"üçüncü taraf (içerik|betik|servis)[^.]{0,40}"
                r"(bulunmamakta|yok|kullanılmam)", re.I)),
)

#: DAVRANIS VARSA BEYANDA GECMESI ZORUNLU olan ifadeler.
#:
#: `KURALLAR` tersini deneteliyor: davranis VAR ve beyan YOK diyorsa
#: celiski. Ama bir ucuncu ihtimal daha var ve daha sinsi: davranis
#: var, beyan hicbir sey SOYLEMIYOR. O zaman beyan yalan degil ama
#: EKSIK -- ve okur bilgilendirilmemis oluyor.
#:
#: TradingView eklenirken tam bu risk dogdu: gizlilik metnine hicbir
#: sey yazmadan widget koymak, "yalan soylemedik" savunmasiyla
#: gecistirilebilirdi. Gecistirilemez.
ZORUNLU_BEYAN = (
    ("TradingView",
     re.compile(r"s3\.tradingview\.com|tradingview\.js"),
     re.compile(r"TradingView", re.I)),
    # GOOGLE ANALYTICS -- 2026-08-25'te Cloudflare Web Analytics'in
    # yerine gecti.
    #
    # Ayni risk TradingView'dakinden BUYUK: Cloudflare Web Analytics
    # cerezsiz ve kimliksizdi, GA4 ise `_ga` cerezi yaziyor ve
    # ziyaretciye kalici kimlik veriyor. Beyanda adi gecmeyen bir
    # analitik araci, okura verilen "cerez yazilmaz" sozunu sessizce
    # bozar.
    #
    # `_ga` CEREZI DE ARANIYOR: yalnizca "Google Analytics" yazmak,
    # hangi cerezin yazildigini soylemiyor. KVKK aydinlatma
    # yukumlulugu cerezin ADINI ve suresini istiyor.
    ("Google Analytics",
     re.compile(r"googletagmanager\.com|google-analytics\.com|gtag/js"),
     re.compile(r"Google Analytics", re.I)),
    ("analitik cerezi",
     re.compile(r"googletagmanager\.com|gtag/js"),
     re.compile(r"`?_ga`?", re.I)),
)

#: Yayina cikmamasi gereken yer tutucular.
YER_TUTUCU = ("GÜNCELLENECEK", "TODO", "XXX", "LOREM", "PLACEHOLDER",
              "DOLDURULACAK", "EKLENECEK:")


def _metin(p: pathlib.Path) -> str:
    if not p.exists():
        return ""
    ham = p.read_text(encoding="utf-8", errors="replace")
    return html.unescape(re.sub(r"<[^>]+>", " ", ham))


def denetle() -> list[str]:
    bulgular: list[str] = []
    if not GIZLILIK.exists():
        return ["gizlilik sayfasi uretilmemis"]

    beyan = _metin(GIZLILIK)

    # 1) Yer tutucu yayinda kalmis mi -- yalnizca YASAL sayfalarda.
    #
    # Butun sitede aramak yanlis alarm uretir: bir haber metninde
    # "TODO" gecebilir ve o bizim yer tutucumuz degildir.
    # Yer tutucu taramasi BUTUN yasal sayfalarda. Once yalnizca
    # `hakkimizda` taraniyordu cunku hepsi o sayfada birlesiyordu;
    # ayrildiktan sonra dordu de ayri ayri kontrol edilmeli.
    for ad in ("hakkimizda", "yayin-ilkeleri", "metodoloji", "gizlilik",
               "kunye"):
        p = CIKTI / ad / "index.html"
        m = _metin(p)
        for yt in YER_TUTUCU:
            if yt in m:
                bulgular.append(f"/{ad}/ sayfasinda yer tutucu: {yt}")

    # 2) Beyan ile gercek davranis ayrismasi.
    #
    # Davranis izi SITE GENELINDE araniyor: analitik betigi her sayfada,
    # uyelik baglantilari menude.
    ornek = CIKTI / "index.html"
    ham_sayfa = (ornek.read_text(encoding="utf-8", errors="replace")
                 if ornek.exists() else "")

    # BETIK DOSYALARI DA TARANIYOR -- denetim JS'e KOR KALIYORDU.
    #
    # Olculdu (2026-08-25): Cloudflare Web Analytics yerine Google
    # Analytics konuldu ve gtag adresi `onay.js` icinde kuruluyor
    # (`"https://www.googletagmanager.com/gtag/js?id=" + OLCUM`).
    # Sayfa HTML'inde `googletagmanager` GECMIYOR.
    #
    # Sonuc: beyandan "Google Analytics" ifadesi elle silindi ve
    # denetim yine "uyusuyor" dedi. Yani kural vardi ama HICBIR SEY
    # olcmuyordu.
    #
    # Bu, denetimin en tehlikeli hali: eski beacon dogrudan HTML'de
    # bir `<script src>` oldugu icin gorunuyordu; ucuncu taraf betigi
    # dinamik yuklendigi anda ayni kural sessizce kor oluyor. Bugun
    # gorunuyor olmasi, yarin gorunecegi anlamina gelmiyordu.
    for js in sorted((CIKTI / "statik").glob("*.js")):
        ham_sayfa += "\n" + js.read_text(encoding="utf-8", errors="replace")
    worker = (KOK / "site" / "worker.js")
    ham_worker = (worker.read_text(encoding="utf-8", errors="replace")
                  if worker.exists() else "")
    kaynak = ham_sayfa + "\n" + ham_worker

    for ad, iz, yasak in KURALLAR:
        var = bool(iz.search(kaynak))
        yok_diyor = bool(yasak.search(beyan))
        if var and yok_diyor:
            bulgular.append(
                f"BEYAN CELISKISI: site {ad} KULLANIYOR ama gizlilik "
                f"metni kullanmadigini soyluyor")

    # EKSIK BEYAN -- celiskiden daha sinsi.
    #
    # Celiskide beyan yanlis bir sey soyluyor; burada HIC bir sey
    # soylemiyor. Ikincisi "yalan soylemedik" savunmasiyla
    # gecistirilebilir ve tam da bu yuzden ayrica deneteniyor.
    for ad, iz, gerekli in ZORUNLU_BEYAN:
        if iz.search(kaynak) and not gerekli.search(beyan):
            bulgular.append(
                f"EKSIK BEYAN: site {ad} kullaniyor ama gizlilik "
                f"metninde HIC gecmiyor")
    return bulgular


def main() -> int:
    b = denetle()
    print("=== BEYAN DENETIMI ===")
    if not b:
        print("  Gizlilik beyani ile sitenin davranisi uyusuyor.")
        return 0
    for x in b:
        print(f"  HATA  {x}")
    print(f"\n{len(b)} celiski. Gizlilik metni yayindaki gercegi "
          f"anlatmali -- ozellik eklendiginde ONCE metin guncellenir.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
