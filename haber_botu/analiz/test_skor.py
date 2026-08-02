"""Skor motoru dogrulama testleri.

Bir skorlama motorunun bozulabilecegi yerler:
  * eksik veriye sifir puan vermek (veri eksikligi kotu performans degildir)
  * ayni girdiye farkli skor uretmek (kural yayimlanamaz hale gelir)
  * kapsam dusukken skoru yayina uygun saymak
  * kismi olculen kriterde kapsam yuzdesini sisirmek

Calistirmak icin:  python test_skor.py
"""

from __future__ import annotations

import dataclasses
import sys

import skor as skor_modulu
from oranlar import EnflasyonEsasi, hesapla
from ornek import GECMIS_HASILAT_BUYUMELERI, ONCE, SIMDI


def _rapor():
    return hesapla(
        sirket="Test A.S.",
        kod="TEST",
        simdi=SIMDI,
        once=ONCE,
        esas=EnflasyonEsasi.TMS29,
    )


def _basarili(etiket: str) -> None:
    print(f"  gecti  {etiket}")


def _basarisiz(etiket: str, detay: str) -> None:
    print(f"  HATA   {etiket}")
    print(f"         {detay}")


def main() -> int:
    hata = 0
    rapor = _rapor()

    print("Tam veri")
    s = skor_modulu.hesapla(rapor, SIMDI, GECMIS_HASILAT_BUYUMELERI)
    if s.skor is not None and 0 <= s.skor <= 100:
        _basarili(f"skor uretildi: {s.skor:.0f}/100, kapsam %{s.kapsam*100:.0f}")
    else:
        _basarisiz("skor araligi", f"skor={s.skor}")
        hata += 1

    if s.yayimlanabilir:
        _basarili("tam veride yayimlanabilir")
    else:
        _basarisiz("yayimlanabilirlik", f"kapsam %{s.kapsam*100:.0f}")
        hata += 1

    print("\nBelirlenimcilik (ayni girdi -> ayni skor)")
    ikinci = skor_modulu.hesapla(_rapor(), SIMDI, GECMIS_HASILAT_BUYUMELERI)
    if ikinci.skor == s.skor:
        _basarili(f"iki calistirma ayni skoru verdi ({s.skor:.4f})")
    else:
        _basarisiz("belirlenimcilik", f"{s.skor} != {ikinci.skor}")
        hata += 1

    print("\nEksik veri sifir puan ALMAMALI")
    # Nakit akis tablosu olmayan bir donem
    nakitsiz = dataclasses.replace(
        SIMDI, faaliyet_nakit_akisi=None, yatirim_harcamasi=None
    )
    s2 = skor_modulu.hesapla(rapor, nakitsiz, GECMIS_HASILAT_BUYUMELERI)
    nakit_kriteri = next(k for k in s2.kriterler if k.ad == "Nakit akışı")
    if not nakit_kriteri.olculdu:
        _basarili("nakit akisi olculemedi olarak isaretlendi")
    else:
        _basarisiz("eksik nakit", f"puan verildi: {nakit_kriteri.puan}")
        hata += 1

    if nakit_kriteri.olculen_puan == 0:
        _basarili("olculemeyen kriter kapsama dahil edilmedi")
    else:
        _basarisiz("kapsam", f"olculen_puan={nakit_kriteri.olculen_puan}")
        hata += 1

    if s2.olculebilen_puan < s.olculebilen_puan:
        _basarili(
            f"olculebilen puan dustu: {s.olculebilen_puan} -> {s2.olculebilen_puan}"
        )
    else:
        _basarisiz("olculebilen puan", "eksik veriye ragmen degismedi")
        hata += 1

    print("\nKismi olcum kapsami sismemeli")
    # Finansman gideri yok -> borc yonetiminin yalnizca bir parcasi olculur
    faizsiz = dataclasses.replace(SIMDI, finansman_gideri=None)
    s3 = skor_modulu.hesapla(rapor, faizsiz, GECMIS_HASILAT_BUYUMELERI)
    borc = next(k for k in s3.kriterler if k.ad == "Borç yönetimi")
    if borc.olculdu and borc.olculen_puan < borc.tam_puan:
        _basarili(
            f"kismi olcum dogru isaretlendi: {borc.olculen_puan}/{borc.tam_puan}"
        )
    else:
        _basarisiz("kismi olcum", f"olculen={borc.olculen_puan} tam={borc.tam_puan}")
        hata += 1

    if s3.kapsam < 1.0:
        _basarili(f"kapsam %100'un altinda kaldi (%{s3.kapsam*100:.0f})")
    else:
        _basarisiz("kapsam sisti", "kismi olcume ragmen %100")
        hata += 1

    print("\nDusuk kapsamda skor yayimlanmamali")
    bos = dataclasses.replace(
        SIMDI,
        faaliyet_nakit_akisi=None,
        yatirim_harcamasi=None,
        finansman_gideri=None,
        net_borc=None,
        favok=None,
        donen_varliklar=None,
        kisa_vadeli_yukumlulukler=None,
    )
    rapor_bos = hesapla(
        sirket="Test", kod="TEST", simdi=bos, once=ONCE, esas=EnflasyonEsasi.TMS29
    )
    s4 = skor_modulu.hesapla(rapor_bos, bos, None)
    if not s4.yayimlanabilir:
        _basarili(f"kapsam %{s4.kapsam*100:.0f} -> yayimlanamaz olarak isaretlendi")
    else:
        _basarisiz("dusuk kapsam", f"kapsam %{s4.kapsam*100:.0f} ama yayimlanabilir")
        hata += 1

    print("\nSkor sinirlari")
    for etiket, s_test in (("tam veri", s), ("kismi", s3), ("cok eksik", s4)):
        if s_test.skor is None or 0 <= s_test.skor <= 100:
            _basarili(f"{etiket}: skor aralik icinde ({s_test.skor})")
        else:
            _basarisiz(etiket, f"aralik disi: {s_test.skor}")
            hata += 1

    print("\nTek cumle ozeti")
    cumle = skor_modulu.tek_cumle(s, rapor)
    if cumle and len(cumle) < 200:
        _basarili(f'"{cumle}"')
    else:
        _basarisiz("tek cumle", f"beklenmeyen: {cumle!r}")
        hata += 1

    print("\n" + "=" * 62)
    print("TUM TESTLER GECTI" if hata == 0 else f"{hata} TEST BASARISIZ")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
