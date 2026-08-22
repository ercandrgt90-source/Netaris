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
#: Gizlilik metni AYRI SAYFA DEGIL -- /hakkimizda/ icinde bir bolum.
#: Ilk yazimimda `/gizlilik/index.html` aradim ve "sayfa uretilmemis"
#: dedi; sayfa vardi, YERI farkliydi. Denetim aracinin kendi
#: varsayimini dogrulamasi gerekiyor.
GIZLILIK = CIKTI / "hakkimizda" / "index.html"

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
    for ad in ("hakkimizda",):
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
