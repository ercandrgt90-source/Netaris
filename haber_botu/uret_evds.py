"""TCMB EVDS serilerini ceker ve depoya yazar.

    EVDS -> beyin.gosterge -> piyasa kutusu, serit, arastirma dosyasi

FRED hattinin Turkiye karsiligi. Ayni depoya yaziyor: `gosterge` tablosu
kaynak fark etmeksizin kod+tarih ile tekil, dolayisiyla FRED ve EVDS
serileri yan yana durabiliyor ve ayni sorgularla okunuyor.

Anahtar yoksa adim KENDINI ATLAR ve hat kirmizi donmez -- EVDS kapaliyken
de site uretilebilmeli.

Kullanim:
    python uret_evds.py
    python uret_evds.py --gun 3000     # daha derin gecmis
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "kaynak"))
sys.path.insert(0, str(_KOK))

import beyin  # noqa: E402
import evds  # noqa: E402

KAYNAK = "TCMB EVDS"


def main() -> int:
    a = argparse.ArgumentParser(description="TCMB EVDS serileri")
    a.add_argument("--gun", type=int, default=1400,
                   help="kac gunluk gecmis cekilsin")
    args = a.parse_args()

    print("=" * 70)
    print("TCMB EVDS")
    print("=" * 70)

    if not evds.anahtar():
        print("EVDS_ANAHTARI tanimli degil -- adim ATLANDI.")
        print("  Yerelde:  setx EVDS_ANAHTARI \"...\"")
        print("  Actions:  depo gizli degerlerine EVDS_ANAHTARI eklenmeli")
        return 0

    seriler = evds.hepsi(gun=args.gun)
    if not seriler:
        print("Hicbir seri cekilemedi.")
        return 1

    gozlemler = []
    for kod, ad, birim, _f, _fr in evds.SERILER:
        s = seriler.get(kod)
        if s is None:
            print(f"  --  {ad:<24} CEKILEMEDI")
            continue
        print(f"  OK  {ad:<24} {s.son.deger:>12,.2f} {birim:<5} {s.son.tarih}"
              f"  ({len(s.gozlemler)} gozlem)")
        for g in s.gozlemler:
            gozlemler.append({
                "kod": kod, "tarih": g.tarih, "deger_ham": g.deger,
                "birim": birim, "ad": ad, "kaynak": KAYNAK,
            })

    with beyin.baglan() as b:
        with beyin.calisma_kaydi(b, "evds") as ozet:
            n = beyin.gosterge_yaz(b, gozlemler)
            ozet.update({"yeni_gozlem": n, "seri": len(seriler)})
    print(f"\ndepo: {n} yeni gozlem ({len(gozlemler)} okundu), "
          f"{len(seriler)} seri")
    return 0


if __name__ == "__main__":
    sys.exit(main())
