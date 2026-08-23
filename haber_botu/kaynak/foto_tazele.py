"""Fotograf havuzunu TAZELER: dusuk cozunurluklu gorselleri degistirir.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): havuzdaki 318 gorselin medyan genisligi 960
piksel ve HICBIRI 1200'u gecmiyordu. Sebep indirme tavaniydi
(`COMMONS_GENISLIK = 800`). Kart yuvasi 800 piksel, manset daha genis
ve retina ekran iki kat piksel istiyor -- sonuc her gorselin bir tik
yumusak, hicbirinin "profesyonel" gorunmemesiydi.

Kullanicinin karsilastirdigi gorsel 1200 piksel genisligindeydi ve
aradaki fark tam olarak buydu.

NEDEN "SIL, YENIDEN INDIR" DEGIL
--------------------------------
Once silmek, aday bulunamayan bir konuda havuzu BOS birakirdi ve o
konudaki sayfalar gorselsiz kalirdi. Sira tersine kuruldu:

    1. Havuz hedefi +3 yukseltilir, `doldur` YENI ve 1600 piksellik
       adaylari indirir.
    2. Havuz eski boyuna dondurulurken EN DUSUK cozunurluklu olanlar
       cikarilir.

Boylece her adimda havuzda kullanilabilir gorsel duruyor ve degisim
ancak yerine daha iyisi geldiginde oluyor.

DEPO MALIYETI GERCEK
--------------------
`site/statik/foto` 79 MB, `.git` 189 MB. Bu yuzden havuz BUYUMUYOR:
yeni gelen her gorsel, cikan bir gorselin yerine geciyor.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI.parent))

from kaynak import foto  # noqa: E402

#: Tazelemeden ONCEKI havuz boylari. Doldurma bittikten sonra havuz
#: bu boya donduruluyor.
ESKI_HAVUZ = 6
ESKI_OZEL = {
    "US": 12, "TR": 12, "FED": 10, "IR": 14, "TCMB": 10, "BRENT": 10,
    "Jeopolitik": 12, "Enerji": 10,
    "TUFE_TR": 6, "XAU": 6, "BIST100": 6, "NFP": 6, "CPI_US": 6,
    "EA": 6, "RU": 6, "CN": 6,
}


def havuzlar() -> list[str]:
    """Doldurulacak butun havuz adlari."""
    ad = list(foto.KONU_ARAMA) + list(foto.VARLIK_ARAMA)
    # Sira sabit: yarida kesilirse ayni yerden devam edilebilsin.
    return sorted(dict.fromkeys(ad))


def doldur_hepsi(bekle: float = 0.5) -> int:
    kayit = foto.Kayit()
    toplam = 0
    adlar = havuzlar()
    for i, konu in enumerate(adlar, 1):
        try:
            n = foto.doldur(konu, kayit)
        except Exception as e:  # ag hatasi bir havuzu duşurmesin
            print(f"  [{i}/{len(adlar)}] {konu}: HATA {type(e).__name__}")
            continue
        if n:
            toplam += n
            print(f"  [{i}/{len(adlar)}] {konu}: +{n}")
        if n:
            time.sleep(bekle)
    kayit.kaydet()
    print(f"\n{toplam} yeni gorsel indirildi")
    return toplam


def budа_hepsi(uygula: bool = False) -> int:
    """Havuzlari eski boyuna dondurur -- EN DUSUK cozunurluklu gider.

    Esitlikte ATIF GEREKTIREN gorsel once cikiyor: kamu mali bir
    gorsel sayfada atif satiri gerektirmiyor ve o yuzden daha
    degerli.
    """
    kayit = foto.Kayit()
    cikan = 0
    for konu, liste in list(kayit.veri.items()):
        hedef = ESKI_OZEL.get(konu, ESKI_HAVUZ)
        if len(liste) <= hedef:
            continue
        atifsiz = foto.Kayit.ATIFSIZ

        def puan(f: dict) -> tuple:
            g = int(f.get("genislik") or 0)
            serbest = (f.get("lisans") or "").lower() in atifsiz
            return (g, 1 if serbest else 0)

        sirali = sorted(liste, key=puan, reverse=True)
        kalan, giden = sirali[:hedef], sirali[hedef:]
        for f in giden:
            ad = f["dosya"].rsplit("/", 1)[-1]
            print(f"  cikar [{konu}] {int(f.get('genislik') or 0):>5}px {ad}")
            if uygula:
                for klasor in (foto.FOTO_KLASORU, foto.ORTA_KLASOR,
                               foto.KUCUK_KLASOR):
                    p = klasor / ad
                    if p.exists():
                        p.unlink()
            cikan += 1
        if uygula:
            kayit.veri[konu] = kalan
    if uygula:
        kayit.kaydet()
    print(f"\n{cikan} gorsel cikarildi"
          f"{'' if uygula else '  (kuru calistirma -- yazmak icin --uygula)'}")
    return cikan


def main() -> int:
    import argparse
    a = argparse.ArgumentParser(description="Fotograf havuzu tazeleme")
    a.add_argument("--doldur", action="store_true",
                   help="yeni ve yuksek cozunurluklu gorselleri indir")
    a.add_argument("--buda", action="store_true",
                   help="havuzu eski boyuna dondur (en dusuk cozunurluk gider)")
    a.add_argument("--uygula", action="store_true",
                   help="budamayi gercekten yaz")
    s = a.parse_args()
    if s.doldur:
        doldur_hepsi()
    elif s.buda:
        budа_hepsi(s.uygula)
    else:
        a.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
