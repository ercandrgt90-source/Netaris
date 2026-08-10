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

import beyin
import politika_faizi  # noqa: E402
import ecb_kur  # noqa: E402
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

            # POLITIKA FAIZI EVDS'DEN DEGIL, PPK DUYURUSUNDAN.
            #
            # EVDS'de calisan bir politika faizi kodu bulunamadi
            # (TP.APIFON1..12, TP.FE.OKTG01, TP.PY.P01 denendi). Ama
            # gerek de yok: politika faizi olculen bir seri degil, ILAN
            # EDILEN bir karar ve TCMB onu PPK basin duyurusunda
            # yaziyor -- o duyuru zaten beslemede.
            #
            # Sayi ELLE YAZILMIYOR: her calistirmada duyurudan yeniden
            # okunuyor. Elle yazilsa bir kez dogru olur, sonra PPK
            # toplanir ve sayi sessizce yanlis olurdu.
            # Once GECMIS: panel bir gostergeyi basmak icin en az
            # IKI gozlem istiyor. Tek karar yazildiginda "Politika
            # faizi" satiri panelde HIC gorunmuyordu. Yalnizca depoda
            # olmayan duyurular cekiliyor.
            eski = politika_faizi.gecmis(b)
            if eski:
                beyin.gosterge_yaz(b, [{
                    "kod": politika_faizi.KOD, "tarih": e.tarih,
                    "deger_ham": e.oran, "birim": "%",
                    "ad": politika_faizi.AD, "kaynak": "TCMB PPK",
                } for e in eski])
                print(f"  {len(eski)} PPK karari gecmise eklendi")

            k = politika_faizi.son_karar(b)
            if k:
                pf = beyin.gosterge_yaz(b, [{
                    "kod": politika_faizi.KOD, "tarih": k.tarih,
                    "deger_ham": k.oran, "birim": "%",
                    "ad": politika_faizi.AD, "kaynak": "TCMB PPK",
                }])
                if pf:
                    print(f"  politika faizi %{k.oran} ({k.tarih}) "
                          f"duyurudan okundu")
                ozet["politika_faizi"] = k.oran
            else:
                # Okunamadi: ESKI DEGER KORUNUYOR. Sessiz degil --
                # denetim tazelik kontrolu bunu yakalar.
                print("  UYARI: politika faizi PPK duyurusundan "
                      "okunamadi; onceki deger korunuyor")

            # ECB REFERANS KURU -- ayni adimda, ANAHTARSIZ.
            #
            # Buraya konuldu cunku EVDS hatti zaten gunluk kurlari
            # tasiyor ve ikisi ayni tabloya yaziyor. Ayri bir hat
            # kurmak, calistirma listesinde unutulabilecek bir adim
            # daha demekti.
            #
            # EVDS ANAHTARINA BAGLI DEGIL: ECB anahtar istemiyor. Ust
            # taraftaki "anahtar yoksa atla" kurali bu cagriyi da
            # atlardi, o yuzden hata durumu ayrica yakalanıyor.
            try:
                kur = ecb_kur.cek()
                n_ecb = ecb_kur.depoya_yaz(b, kur)
                if kur:
                    print(f"  OK  {'EUR/USD (ECB)':<24} "
                          f"{kur[0][1]:>12,.4f}       {kur[0][0]}"
                          f"  ({n_ecb} yeni)")
                ozet["ecb_kur"] = n_ecb
            except Exception as e:                        # noqa: BLE001
                print(f"  --  {'EUR/USD (ECB)':<24} CEKILEMEDI: "
                      f"{type(e).__name__}")

            ozet.update({"yeni_gozlem": n, "seri": len(seriler)})
    print(f"\ndepo: {n} yeni gozlem ({len(gozlemler)} okundu), "
          f"{len(seriler)} seri")
    return 0


if __name__ == "__main__":
    sys.exit(main())
