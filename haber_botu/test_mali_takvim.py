# -*- coding: utf-8 -*-
"""MALI TAKVIM: TAKVIM DISI SIRKET ELENMEMELI, YANLIS ETIKETLENMEMELI.

BU DOSYA NEDEN VAR
------------------
Kaynagin donem etiketi ("Q3 2026") MALI ceyregi gosteriyor. Mali yili
takvim yiliyla ortusmeyen sirkette bu takvim ceyregi DEGIL. Olculdu
(2026-10-13), spor kuluplerinin mali yili 31 Mayis'ta bitiyor:

    GSRAY  2026-05-31  2026-02-28  2025-08-31  2025-05-31
    FENER  2026-05-31  2026-02-28  2025-08-31  2025-05-31
    BJKAS  2026-05-31  2026-02-28  2025-08-31  2025-05-31
    TSPOR  2026-05-31  2026-02-28  2025-11-30  2025-08-31
    THYAO  2026-06-30  2026-03-31  2025-12-31  2025-09-30

Ilk cozum bu sirketleri ELEMEKTI (`son_donem` None donuyor). Dogru
ama eksik: GSRAY'in bilancosu gercekten aciklandi ve biz onu hic
gormuyorduk. Bu katman onlari eliyor degil, KENDI TAKVIMIYLE
tanimliyor -- kiyaslamasi ayni takvimdeki sirketlerle yapiliyor.

OLCUT ETIKET DEGIL TARIH. Kaynak "Period Ending" satirinda gercek
bitis tarihini yaziyor; onceki kod bu satiri okuyup ATIYORDU.

AG KULLANILMIYOR: `cek` yerine sahte islev konuyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK / "kaynak"))

import bilanco_ag as b                             # noqa: E402

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

# Gercek sayfanin yapisi: baslik satiri etiketleri, ardindan
# "Period Ending" satiri tarihleri tasiyor. Tarih hucresi HEM mobil
# HEM masaustu bicimini icinde bulunduruyor.
_HTML = (
    "<tr><th>Fiscal Quarter</th><th>Q4 2026</th><th>Q3 2026</th>"
    "<th>Q2 2026</th></tr>"
    "<tr class='date-row'><th>Period Ending</th>"
    "<th><span class='inline sm:hidden'>May '26</span>"
    "<span class='hidden sm:inline'>May 31, 2026</span></th>"
    "<th><span>Feb '26</span><span>Feb 28, 2026</span></th>"
    "<th><span>Nov '25</span><span>Nov 30, 2025</span></th></tr>"
    "<tr><td>Revenue</td><td>1,000</td><td>900</td><td>800</td></tr>"
)

print("1. Period Ending satiri okunuyor")
_d, _k, _t = b._tablo(_HTML)
esit(_d, ["Q4 2026", "Q3 2026", "Q2 2026"], "etiketler okunuyor")
esit(_t, ["2026-05-31", "2026-02-28", "2025-11-30"],
     "bitis tarihleri okunuyor (mobil+masaustu ikizi ayiklandi)")
esit(len(_k["Revenue"]), 3, "kalem satiri tarih satirindan etkilenmiyor")

print("")
print("2. Cozulemeyen tarih hucresi HIZALAMAYI bozmuyor")
_bozuk = _HTML.replace("<span>Feb '26</span><span>Feb 28, 2026</span>",
                       "<span>belirsiz</span>")
_, _, _t2 = b._tablo(_bozuk)
esit(len(_t2), 3, "okunamayan hucre ATLANMIYOR, yerinde bos duruyor")
esit(_t2[1], "", "okunamayan hucre bos dizge")
esit(_t2[2], "2025-11-30", "sonraki tarih KAYMIYOR")

print("")
print("3. cek donus bicimi geriye donuk uyumlu")
esit(len(b._tablo(_HTML)), 3, "_tablo ucu birlikte doniyor")
try:
    b.KAPANDI = True
    esit(b.cek("X", "gelir"), ([], {}), "varsayilan IKILI doniyor")
    esit(b.cek("X", "gelir", None, True), ([], {}, []),
         "tarih istenince UCLU doniyor")
finally:
    b.KAPANDI = False
    b.OKUNAMAYAN.clear()

print("")
print("4. Mali yil sonu ayi etiket+tarihten cikariliyor")
esit(b.mali_yil_sonu(["Q4 2026", "Q3 2026", "Q2 2026"],
                     ["2026-05-31", "2026-02-28", "2025-11-30"]), 5,
     "spor kulubu: mayis sonu mali yil")
esit(b.mali_yil_sonu(["Q2 2026", "Q1 2026", "Q4 2025"],
                     ["2026-06-30", "2026-03-31", "2025-12-31"]), 12,
     "normal sirket: aralik (takvim yili)")
esit(b.mali_yil_sonu(["Q1 2027", "Q4 2026"],
                     ["2026-08-31", "2026-05-31"]), 5,
     "GELECEK etiketli kolon da ayni takvimi veriyor")

print("")
print("5. Guvenilmez girdide tahmin YOK")
esit(b.mali_yil_sonu([], []), None, "bos tablo None")
esit(b.mali_yil_sonu(["Q4 2026", "Q3 2026"], ["2026-05-31"]), None,
     "uzunluk uyusmazsa None (hizalama guvenilmez)")
esit(b.mali_yil_sonu(["Q4 2026", "Q3 2026"],
                     ["2026-05-31", "2026-09-30"]), None,
     "kolonlar farkli takvim veriyorsa None")
esit(b.mali_yil_sonu(["TTM", "Q3 2026", "Q2 2026", "Q1 2026"],
                     ["", "2026-02-28", "2025-11-30", "2025-08-31"]), 5,
     "cozulemeyen etiket atlaniyor, kalani okunuyor")
esit(b.mali_yil_sonu(["TTM", "Q3 2026"], ["", "2026-02-28"]), None,
     "tek kolon yetmiyor -- uyusma denetimi anlamsiz kalirdi")

# MALI YIL DEGISIMI MESRU -- EN YENI DIZI ALINIYOR.
#
# Olculdu (2026-10-13): ARENA aralik sonundan mart sonuna, BALSU
# aralik sonundan haziran sonuna gecmis. Butun kolonlarin uyusmasini
# sart kosan ilk surum ikisini de tumden eliyordu.
esit(b.mali_yil_sonu(
    ["Q1 2027", "Q4 2026", "Q3 2026", "Q1 2024", "Q4 2023"],
    ["2026-06-30", "2026-03-31", "2025-12-31",
     "2024-03-31", "2023-12-31"]), 3,
    "mali yili degismis sirkette EN YENI takvim doniyor")
esit(b.mali_yil_sonu(["Q1 2027", "Q4 2023", "Q3 2023"],
                     ["2026-06-30", "2023-12-31", "2023-09-30"]), None,
     "en yeni dizi iki kolondan kisaysa None")

print("")
print("6. Ay adi")
esit(b.ay_adi(5), "mayıs", "ay adi doniyor")
esit(b.ay_adi(12), "aralık", "aralik")
esit(b.ay_adi(None), "", "cozulemeyende bos")
esit(b.ay_adi(0), "", "gecersiz ay bos")

print("")
print("7. mali_takvim: takvim disi sirket ELENMIYOR")
import datetime as _dt                             # noqa: E402

_B = _dt.date(2026, 10, 13)
try:
    # GSRAY'in 2026-10-13'te kaynaktaki hali (olculdu).
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q4 2026", "Q3 2026", "Q1 2025"],
        {},
        ["2026-05-31", "2026-02-28", "2025-08-31"],
    )
    _m = b.mali_takvim("GSRAY", bugun=_B)
    esit(_m["yil_sonu_ayi"], 5, "mali yil sonu mayis")
    esit(_m["takvim_disi"], True, "takvim disi isaretleniyor")
    esit(_m["son_bitis"], "2026-05-31", "en yeni gerceklesmis donem")
    esit(_m["son_etiket"], (2026, 4), "etiketi de doniyor")

    # ASIL KAZANC: ETIKETI ILERIDE OLAN GERCEK DONEM ARTIK ELENMIYOR.
    #
    # Mali yili mayista biten sirkette haziran-agustos donemi "Q1
    # 2027" diye etiketleniyor. Etiket Ekim 2026'da sacma gorunuyor
    # ama donem GERCEKTEN bitti ve tablosu yayimlandi. Eski olcut
    # (`makul_ceyrek`) etikete baktigi icin butun sirketi atiyordu;
    # yeni olcut tarihe bakiyor ve donemi kabul ediyor.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q1 2027", "Q4 2026", "Q3 2026"],
        {},
        ["2026-08-31", "2026-05-31", "2026-02-28"],
    )
    _g = b.mali_takvim("GSRAY ileri etiketli", bugun=_B)
    esit(_g["son_bitis"], "2026-08-31",
         "etiketi 2027 olan GERCEK donem kabul ediliyor")
    esit(_g["son_etiket"], (2027, 1), "mali etiketi korunuyor")
    esit(b.son_donem.__name__, "son_donem", "eski yol duruyor")

    # GELECEKTE biten kolon ise ayiklaniyor.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q2 2027", "Q1 2027", "Q4 2026"],
        {},
        ["2026-11-30", "2026-08-31", "2026-05-31"],
    )
    esit(b.mali_takvim("GSRAY tahminli", bugun=_B)["son_bitis"],
         "2026-08-31", "henuz bitmemis 2026-11-30 atlaniyor")

    # Normal sirket: ayni kod yoluyla takvim yili cikmali.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q3 2026", "Q2 2026"], {}, ["2026-09-30", "2026-06-30"])
    _n = b.mali_takvim("THYAO", bugun=_B)
    esit(_n["yil_sonu_ayi"], 12, "normal sirket aralik")
    esit(_n["takvim_disi"], False, "takvim disi DEGIL")
    esit(_n["son_bitis"], "2026-09-30", "en yeni bitmis ceyrek")

    # Hepsi gelecekteyse olcum yok -- tahmin edilmiyor.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q1 2027"], {}, ["2026-11-30"])
    esit(b.mali_takvim("ileri", bugun=_B), None,
         "tum donemler gelecekteyse None")

    # Tarih satiri hic yoksa (eski/degisen sayfa yapisi) None.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q3 2026", "Q2 2026"], {}, [])
    esit(b.mali_takvim("tarihsiz", bugun=_B), None,
         "tarih satiri yoksa None (etikete guvenilmiyor)")

    # SINIR: bugun biten donem GECERLI sayiliyor.
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        ["Q4 2026", "Q3 2026", "Q2 2026"], {},
        ["2026-10-13", "2026-07-13", "2026-04-13"])
    esit(b.mali_takvim("bugun", bugun=_B)["son_bitis"], "2026-10-13",
         "bugun biten donem geleceğe atilmiyor")
finally:
    b.cek = _ASIL_CEK

print("")
print("8. ara_donem: takvim EK ISTEK OLMADAN geliyor, bitmemis donem kirpiliyor")
try:
    b.ARA_SN = 0
    _sayfalar = {}

    def _sahte(kod, sayfa="gelir", istemci=None, tarih_de=False):
        d, k, t = _sayfalar[sayfa]
        _cagri.append(sayfa)
        return (d, k, t) if tarih_de else (d, k)

    _cagri = []
    # Normal sirket: hicbir kolon gelecekte degil.
    _sayfalar = {
        "gelir": (["Q3 2026", "Q2 2026"], {"Revenue": [100.0, 90.0]},
                  ["2026-09-30", "2026-06-30"]),
        "bilanco": (["Q3 2026", "Q2 2026"], {"Total Assets": [500.0, 480.0]},
                    ["2026-09-30", "2026-06-30"]),
        "nakit": (["Q3 2026", "Q2 2026"],
                  {"Operating Cash Flow": [20.0, 18.0]},
                  ["2026-09-30", "2026-06-30"]),
    }
    b.cek = _sahte
    _r = b.ara_donem("THYAO", 2, bugun=_dt.date(2026, 10, 13))
    esit(_r["_mali"]["yil_sonu_ayi"], 12, "takvim yili okunuyor")
    esit(_r["_mali"]["son_bitis"], "2026-09-30", "son bitis okunuyor")
    esit("_kirpilan" in _r, False, "kirpilacak kolon yok")
    esit(_r["gelir"]["Revenue"], 190.0, "iki ceyrek toplandi (akis)")
    esit(len(_cagri), 3, "UC istek: sayfa basina bir (fazladan istek YOK)")

    # Takvim disi sirket: en ustteki kolon GELECEKTE bitiyor.
    _sayfalar = {
        "gelir": (["Q2 2027", "Q1 2027", "Q4 2026"],
                  {"Revenue": [999.0, 100.0, 90.0]},
                  ["2026-11-30", "2026-08-31", "2026-05-31"]),
        "bilanco": (["Q2 2027", "Q1 2027", "Q4 2026"],
                    {"Total Assets": [999.0, 500.0, 480.0]},
                    ["2026-11-30", "2026-08-31", "2026-05-31"]),
        "nakit": (["Q2 2027", "Q1 2027", "Q4 2026"],
                  {"Operating Cash Flow": [999.0, 20.0, 18.0]},
                  ["2026-11-30", "2026-08-31", "2026-05-31"]),
    }
    _r = b.ara_donem("GSRAY", 2, bugun=_dt.date(2026, 10, 13))
    esit(_r["_mali"]["yil_sonu_ayi"], 5, "mayis sonu mali yil okunuyor")
    esit(_r["_kirpilan"]["gelir"], 1, "bitmemis kolon kirpildi")
    esit(_r["gelir"]["Revenue"], 190.0,
         "999 TOPLAMA GIRMEDI (bitmemis donem atildi)")
    esit(_r["bilanco"]["Total Assets"], 500.0,
         "stok kalemi kirpilmis seriden aliniyor")

    # Tarih okunamadiysa KIRPMA YAPILMIYOR -- tahmin yerine dokunma.
    _sayfalar = {
        "gelir": (["Q3 2026", "Q2 2026"], {"Revenue": [100.0, 90.0]}, []),
        "bilanco": (["Q3 2026"], {"Total Assets": [500.0]}, []),
        "nakit": (["Q3 2026"], {"Operating Cash Flow": [20.0]}, []),
    }
    _r = b.ara_donem("tarihsiz", 2, bugun=_dt.date(2026, 10, 13))
    esit(_r["_mali"]["yil_sonu_ayi"], None, "takvim cozulemedi")
    esit("_kirpilan" in _r, False, "tarih yoksa kirpma YOK")
    esit(_r["gelir"]["Revenue"], 190.0, "veri yine de uretiliyor")
finally:
    b.cek = _ASIL_CEK
    b.ARA_SN = 0.5

print("")
print("9. Onceki yil kolonu TARIHTEN bulunuyor, sayilmiyor")
# Olculdu (2026-10-13): kaynagin ceyreklik serisinde bosluk olabiliyor
# ve sabit "dort kolon geri" varsayimi on bes ay oncesini gosteriyor.
_TAM = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30",
        "2025-06-30", "2025-03-31"]
esit(b.onceki_yil_kaydirmasi(_TAM, 1), 4, "kesiksiz seride dort")
# BALSU'nun gercek serisi: 2025-12-31 kolonu YOK.
_BOSLUKLU = ["2026-06-30", "2026-03-31", "2025-09-30", "2025-06-30",
             "2025-03-31", "2024-12-31"]
esit(b.onceki_yil_kaydirmasi(_BOSLUKLU, 1), 3,
     "boskuklu seride UC (sabit dort 15 ay oncesini gosterirdi)")
# GSRAY'in gercek serisi: 2025-11-30 kolonu YOK.
_GSRAY = ["2026-05-31", "2026-02-28", "2025-08-31", "2025-05-31",
          "2025-02-28", "2024-11-30"]
esit(b.onceki_yil_kaydirmasi(_GSRAY, 1), 3, "kulup serisinde UC")
esit(b.onceki_yil_kaydirmasi(["2026-06-30", "2026-03-31"], 1), None,
     "onceki yil kolonu yoksa None -- yanlis kiyas yapilmiyor")
esit(b.onceki_yil_kaydirmasi([], 1), None, "bos liste None")
esit(b.onceki_yil_kaydirmasi(["", "2025-06-30"], 1), None,
     "son donem tarihi okunamadiysa None")
# Kumulatif donemde pencere KESIKSIZ olmali.
esit(b.onceki_yil_kaydirmasi(_TAM, 2), 4, "iki ceyreklik pencere kesiksiz")
esit(b.onceki_yil_kaydirmasi(["2026-06-30", "2026-03-31", "2025-12-31",
                              "2025-09-30", "2025-06-30"], 2), None,
     "pencere tasarsa None (tek kolon kaldi)")
# PENCERE ICINDE BOSLUK: 2025-06-30'dan sonraki kolon dokuz ay geride.
# Iki ceyregi toplamak "bir yil once alti ay" demek olurdu; degil.
esit(b.onceki_yil_kaydirmasi(["2026-06-30", "2026-03-31", "2025-12-31",
                              "2025-09-30", "2025-06-30",
                              "2024-09-30"], 2), None,
     "pencere icinde bosluk varsa None (kolonlar ardisik degil)")
esit(b.onceki_yil_kaydirmasi(["2026-06-30", "2026-03-31", "2025-12-31",
                              "2025-09-30", "2025-06-30",
                              "2025-03-31"], 2), 4,
     "ardisik pencere kabul ediliyor")

print("")
print("10. ara_donem KAYDIRMAYI kullaniyor (islev dogru olmasi yetmez)")
try:
    b.ARA_SN = 0
    # Degerler kolon sirasina gore: onceki yil kolonu 3. sirada.
    _D = ["Q4 2026", "Q3 2026", "Q1 2026", "Q4 2025", "Q3 2025", "Q2 2025"]
    _T = ["2026-05-31", "2026-02-28", "2025-08-31", "2025-05-31",
          "2025-02-28", "2024-11-30"]
    _K = {"Revenue": [100.0, 90.0, 80.0, 70.0, 60.0, 50.0],
          "Gross Profit": [40.0, 36.0, 32.0, 28.0, 24.0, 20.0],
          "Operating Income": [10.0] * 6, "Net Income": [5.0] * 6}
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        (_D, dict(_K), _T) if tarih_de else (_D, dict(_K)))
    _r = b.ara_donem("GSRAY", 1, bugun=_dt.date(2026, 10, 13))
    esit(_r["gelir"]["Revenue"], 100.0, "bu donem en yeni kolon")
    esit(_r["gelir_onceki"]["Revenue"], 70.0,
         "onceki yil UCUNCU kolon (2025-05-31) -- sabit 4 olsa 60 gelirdi")
    # Onceki yil kolonu hic yoksa bolum URETILMIYOR.
    _D2, _T2 = _D[:2], _T[:2]
    _K2 = {ad: v[:2] for ad, v in _K.items()}
    b.cek = lambda k, s="gelir", i=None, tarih_de=False: (
        (_D2, dict(_K2), _T2) if tarih_de else (_D2, dict(_K2)))
    _r2 = b.ara_donem("kisa", 1, bugun=_dt.date(2026, 10, 13))
    esit("gelir_onceki" in _r2, False,
         "onceki yil yoksa kiyas HIC uretilmiyor")
    esit(_r2["_onceki_yok"]["gelir"], "önceki yılın aynı dönemi kaynakta yok",
         "sebebi yaziliyor -- sessiz eksiklik yok")
finally:
    b.cek = _ASIL_CEK
    b.ARA_SN = 0.5

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
