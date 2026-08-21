"""Ayni haberin ikinci kaydini kaldirir -- EN GUNCELI KALIR.

NEDEN GEREKIYOR
---------------
Ayni olay birden fazla kaynaktan giriyor ve her biri ayri adres, ayri
sayfa uretiyor. Olculdu: 1657 yayimlanmis sayfanin 188'i baska bir
sayfanin tekrariydi. Okur icin bu, ayni haberi listede uc kez gormek
demek; arama motoru icin ise KENDI KENDIMIZLE REKABET -- ayni icerigi
tasiyan uc adres birbirinin siralamasini yiyor.

"AYNI HABER" NASIL TANIMLANDI
-----------------------------
Ayni gun + ayni baslik. Yalnizca baslik yeterli DEGIL: "Borsa gunu
yukselisle tamamladi" her yukselis gununde yeniden yaziliyor ve bunlar
farkli gunlerin ayri haberleri. Olculdu, yalnizca baslige baksaydik
1003 kayit silinecekti ve arsivin buyuk kismi yok olacakti.

Gun olcutu da tek basina yetmez; ikisi BIRLIKTE ayni olayi isaret
ediyor.

SILINEN ADRES 404 VERMIYOR
--------------------------
Kaldirilan sayfalar yayimlanmisti; arama motorlari ve paylasilan
baglantilar onlari biliyor. Silip birakmak, okuru bos sayfaya
gondermek olurdu. Her silinen adres icin KALAN adrese yonlendirme
yaziliyor ve worker onu 301 olarak sunuyor.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sqlite3

KOK = pathlib.Path(__file__).resolve().parent.parent
VT = KOK / "haber_botu" / "netaris.db"
CIKTI = KOK / "site" / "cikti"
HARITA = KOK / "site" / "yonlendirme.json"

#: Ayni olayin kayitlarini bulan sorgu. Siralama, HANGISININ KALACAGINI
#: belirliyor: en son gorulen kayit basta.
SORGU = """
SELECT TRIM(LOWER(COALESCE(baslik_tr, baslik_kaynak))) AS anahtar,
       substr(tarih, 1, 10) AS gun,
       adres, yayin_yolu, COALESCE(son_gorulme, ilk_gorulme, '') AS an
  FROM haber
 WHERE yayimlandi IS NOT NULL AND yayin_yolu IS NOT NULL
 ORDER BY anahtar, gun, an DESC
"""


def gruplar(k: sqlite3.Connection) -> dict[tuple, list]:
    g: dict[tuple, list] = {}
    for anahtar, gun, adres, yol, an in k.execute(SORGU):
        g.setdefault((anahtar, gun), []).append((adres, yol, an))
    return {a: v for a, v in g.items() if len(v) > 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true",
                    help="olcmekle kalma, gercekten sil")
    n = ap.parse_args()

    k = sqlite3.connect(VT)
    g = gruplar(k)
    harita: dict[str, str] = {}
    silinecek: list[tuple[str, str]] = []
    kayit_dusur: list[str] = []  # dosyasi ortak olan fazla kayitlar

    for (_anahtar, _gun), kayitlar in g.items():
        # Ilk kayit EN GUNCEL (sorgu `an DESC` siraliyor) -- o kaliyor.
        kalan_yol = kayitlar[0][1]
        for adres, yol, _an in kayitlar[1:]:
            # SAYFA COGU ZAMAN ORTAK. Adres slug'i baslikten turuyor,
            # yani ayni basligi tasiyan kayitlar ayni dosyayi gosteriyor.
            # Olculdu: 177 tekrarli grubun 176'sinda dosya ORTAKTI --
            # yani diskte tekrar yok, fazlalik KAYITTA. Dosyayi silmek
            # o durumda KALAN kaydin sayfasini da silerdi.
            if yol == kalan_yol:
                kayit_dusur.append(adres)
                continue
            # Kok dizine ya da bolum koküne yonlendirme yapilmiyor:
            # "/haber/" bir haber degil, liste sayfasi. Okuru oraya
            # atmak, aradigini bulamadigi bir yere atmaktir.
            # HEM kaynak HEM HEDEF gercek bir haber olmali.
            if not yol or yol.strip("/").count("/") < 1:
                continue
            if not kalan_yol or kalan_yol.strip("/").count("/") < 1:
                # Kalan kaydin yolu bozuk (orn. "/haber/"). Yonlendirme
                # yazmak okuru liste sayfasina atardi; kaydi da
                # dusurmuyoruz -- bozuk veriyi silmek, bozuklugu
                # gizlemek olur. Ayri bir sorun olarak duruyor.
                continue
            harita[yol] = kalan_yol
            silinecek.append((adres, yol))

    print(f"tekrarli grup : {len(g)}")
    print(f"kaldirilacak  : {len(silinecek)} sayfa dosyasi")
    print(f"yayimdan dusecek kayit: {len(kayit_dusur) + len(silinecek)}")

    if not n.uygula:
        print("\n(olcum modu -- silmek icin --uygula)")
        for _adres, yol in silinecek[:8]:
            print(f"  {yol}  ->  {harita[yol]}")
        return 0

    # YEDEK ONCE. Silme geri alinamaz; veritabani kopyasi olmadan
    # yanlis bir olcutle calistirmak arsivi bitirir.
    yedek = VT.with_suffix(".db.yedek")
    shutil.copy2(VT, yedek)
    print(f"yedek         : {yedek.name}")

    kaldirilan = 0
    for adres, yol in silinecek:
        d = CIKTI / yol.strip("/") / "index.html"
        if d.exists():
            d.unlink()
            try:
                d.parent.rmdir()
            except OSError:
                pass  # icinde baska dosya varsa dizin kalir
            kaldirilan += 1
        # Kayit SILINMIYOR, yayimdan dusuruluyor. Silmek, ayni haberin
        # yarin yeniden cekilip yeniden yayimlanmasina yol acardi --
        # kaydi tutmak "bunu gorduk ve gecdik" demek.
        k.execute("UPDATE haber SET yayimlandi = NULL, yayin_yolu = NULL "
                  "WHERE adres = ?", (adres,))
    # Dosyasi ORTAK olan fazla kayitlar: dosyaya dokunulmuyor, yalnizca
    # kayit yayimdan dusuyor -- listelerde ikinci kez gorunmesin.
    for adres in kayit_dusur:
        k.execute("UPDATE haber SET yayimlandi = NULL, yayin_yolu = NULL "
                  "WHERE adres = ?", (adres,))
    k.commit()

    HARITA.write_text(json.dumps(harita, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"dosya silindi : {kaldirilan}")
    print(f"yonlendirme   : {len(harita)} -> {HARITA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
