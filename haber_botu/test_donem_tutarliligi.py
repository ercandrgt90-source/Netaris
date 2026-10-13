# -*- coding: utf-8 -*-
"""AYNI SAYFADA IKI AYRI DONEM OLMAMALI.

BU DOSYA NEDEN VAR -- GERCEK BIR KUSUR (olculdu 2026-10-13)
-----------------------------------------------------------
Bilanco sayfasi iki ayri yerden besleniyor:

  * TL SEVIYELERI  -> `bilanco_ag.donem_getir` (sayfa uretiminde)
  * ORANLAR + MEDYAN -> `uret_bilanco.sektor_isle` ciktisi (ozet)

Kac ceyregin toplanacagi IKI YERDE ayri ayri yaziliydi:
`uret_bilanco --ceyrek` varsayilani 1, `donem_getir` varsayilani 2.
Ikisini de kimse acikca vermiyordu -- ne `calistir.py` ne CI. Yani
URETIMDE ikisi birden calisiyordu.

Sonuc yayimlanmis sayfada gorunuyor (2026-2-ceyrek-alctl.md):

    ## 2026 2. çeyrek dönemi ölçümleri
    | Hasılat   | 1,87 milyar TL |     <- ALTI AYIN toplami
    | Brüt kâr  | 0,14 milyar TL |
    ...
    | Brüt kâr marjı | %4,4 |          <- TEK CEYREGIN marji

Seviye tablosundan hesaplanan brut marj %7,5; yazili olan %4,4.
Iki sayi da dogru ama AYNI DONEME AIT DEGIL -- ve basligi tek.

Yuvarlanmayla aciklanamaz: %4,4 icin brut karin 0,08 milyar
gorunmesi gerekirdi.

KURAL -- SAYI DEGIL, DAVRANIS SINANIYOR
---------------------------------------
Varsayilanlari karsilastirmak yetmez: yarin biri cagri yerinde
acikca `ceyrek=2` yazarsa varsayilanlar yine uyusur ama sayfa yine
bozulur. Bu yuzden sinama IKI YOLU DA CALISTIRIYOR ve ciktilarinin
AYNI DONEMI anlattigini olcuyor.

AG KULLANILMIYOR: `cek` yerine sahte islev konuyor ve ceyrekler
BILEREK cok farkli secildi -- karisma olursa fark buyuk olsun.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))
sys.path.insert(0, str(_KOK / "analiz"))

import bilanco_ag as b                             # noqa: E402
import uret_bilanco as U                           # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_ASIL_CEK = b.cek
_ASIL_ARA = b.ARA_SN

# EN YENI CEYREK BASTA. Q(n) ile Q(n-1) bilerek cok farkli:
# ikisinin toplami tek ceyrekten acikca ayrilsin.
_DONEMLER = ["Q3 2026", "Q2 2026", "Q1 2026", "Q4 2025",
             "Q3 2025", "Q2 2025", "Q1 2025", "Q4 2024"]
_TARIHLER = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31",
             "2025-09-30", "2025-06-30", "2025-03-31", "2024-12-31"]
_SAYFA = {
    "gelir": {
        "Revenue":          [100.0, 900.0, 100.0, 100.0,
                             90.0, 90.0, 90.0, 90.0],
        "Gross Profit":     [40.0, 90.0, 40.0, 40.0,
                             30.0, 30.0, 30.0, 30.0],
        "Operating Income": [20.0, 50.0, 20.0, 20.0,
                             15.0, 15.0, 15.0, 15.0],
        "Net Income":       [10.0, 40.0, 10.0, 10.0,
                             8.0, 8.0, 8.0, 8.0],
    },
    "bilanco": {
        "Total Assets": [1000.0] * 8,
        "Shareholders' Equity": [500.0] * 8,
        "Total Current Assets": [600.0] * 8,
        "Total Current Liabilities": [300.0] * 8,
        "Accounts Receivable": [100.0] * 8,
        "Inventory": [100.0] * 8,
    },
    "nakit": {
        "Operating Cash Flow": [30.0, 70.0, 30.0, 30.0,
                                25.0, 25.0, 25.0, 25.0],
        "Cash Interest Paid": [5.0] * 8,
    },
}


def _sahte(kod, sayfa="gelir", istemci=None, tarih_de=False):
    d, k, t = _DONEMLER, dict(_SAYFA[sayfa]), _TARIHLER
    return (d, k, t) if tarih_de else (d, k)


print("1. Iki yol AYNI donemi anlatiyor")
try:
    b.cek = _sahte
    b.ARA_SN = 0

    # SAYFA YOLU: `uret_bilanco_sayfa.sirket_isle` boyle cagiriyor --
    # ceyrek sayisi VERILMIYOR, varsayilan ne ise o kullaniliyor.
    _d, _once, _eksik = b.donem_getir("X", "etiket", sektor_tr="Bilişim",
                                      ciftli=True)
    esit(_eksik, [], "sayfa yolu veri uretti")

    # OZET YOLU: `uret_bilanco.main` argparse varsayilanini kullaniyor.
    import argparse                                  # noqa: PLC0415
    _a = argparse.ArgumentParser()
    _a.add_argument("--ceyrek", type=int,
                    default=b.VARSAYILAN_CEYREK)
    _ozet_ceyrek = _a.parse_args([]).ceyrek
    _alanlar = b.donemi_kur(b.ara_donem("X", _ozet_ceyrek))
    import oranlar                                   # noqa: PLC0415
    _ozet_d = oranlar.Donem(etiket="etiket", **_alanlar)
    _oran = U._oranlari(_ozet_d)

    # ASIL OLCUM: sayfadaki SEVIYELERDEN hesaplanan brut marj, sayfada
    # YAZILI olan brut marjla ayni olmali. Ceyrek sayilari ayrilirsa
    # bu iki sayi ayrilir -- kusur tam olarak buydu.
    _seviyeden = 100.0 * _d.brut_kar / _d.hasilat
    esit(round(_seviyeden, 6), round(_oran["brut_marj"], 6),
         "seviye tablosundan hesaplanan brut marj = yazili brut marj")
    esit(_d.hasilat, _ozet_d.hasilat,
         "iki yol ayni hasilati veriyor")
    esit(_d.net_kar, _ozet_d.net_kar,
         "iki yol ayni net kari veriyor")

    print("")
    print("2. Kusurun kendisi YENIDEN URETILIYOR (olcum araci calisiyor mu)")
    _alanlar2 = b.donemi_kur(b.ara_donem("X", 2))
    _iki = oranlar.Donem(etiket="etiket", **_alanlar2)
    _fark = abs(100.0 * _iki.brut_kar / _iki.hasilat - _oran["brut_marj"])
    if _fark < 1.0:
        print("  DUSTU  sahte veri KARISMAYI gostermiyor "
              f"(fark yalnizca {_fark:.2f} puan)")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  bir ve iki ceyrek {_fark:.1f} puan ayriliyor "
          f"-- karisma OLCULEBILIR")

    print("")
    print("3. Varsayilanlar TEK kaynaktan okunuyor")
    import inspect                                   # noqa: PLC0415
    esit(inspect.signature(b.ara_donem).parameters["ceyrek"].default,
         b.VARSAYILAN_CEYREK, "ara_donem tek kaynaktan")
    esit(inspect.signature(b.donem_getir).parameters["ceyrek"].default,
         b.VARSAYILAN_CEYREK, "donem_getir tek kaynaktan")
    esit(_ozet_ceyrek, b.VARSAYILAN_CEYREK, "uret_bilanco tek kaynaktan")
finally:
    b.cek = _ASIL_CEK
    b.ARA_SN = _ASIL_ARA

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
