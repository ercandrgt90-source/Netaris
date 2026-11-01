# -*- coding: utf-8 -*-
"""SEKTOR MEDYANI AYNI MALI TAKVIMDEKILERDEN KURULMALI.

BU DOSYA NEDEN VAR -- OLCULDU, YAYINDAYDI (2026-10-13)
------------------------------------------------------
`sektor_ozet.json` icindeki İletişim sektorunun brut kar marji
medyani **-%32,03** idi. Bir telekom sektoru icin olanaksiz bir sayi.
Sebep, sektordeki alti sirketten UCUNUN futbol kulubu olmasi:

    BIGTK    +24,94      <- dönem bitişi 2026-06-30
    IHYAY    +11,50      <- dönem bitişi 2026-06-30
    TTKOM    +39,32      <- dönem bitişi 2026-06-30
    BJKAS    -79,44      <- dönem bitişi 2026-05-31
    FENER   -100,86      <- dönem bitişi 2026-05-31
    TSPOR    -75,57      <- dönem bitişi 2026-05-31

Kuluplerin mali yili 31 Mayis'ta bitiyor; son bildirdikleri donem
MART-MAYIS. TTKOM'un donemi ise NISAN-HAZIRAN. Rakamlari yanlis
degil -- BASKA BIR ZAMAN ARALIGINA ait.

OLCUT BITIS TARIHI, MALI YIL SONU DEGIL. Olculdu: ARENA'nin mali
yili martta, BALSU'nun haziranda bitiyor ama ikisinin de son donemi
2026-06-30'da bitiyor -- yani TTKOM ile AYNI uc ay. Mali yil sonuna
gore gruplamak onlari gereksiz yere ayirirdi.

    Alti sirket birlikte : medyan -32,03
    Yalnizca takvim yili : medyan +24,94      <- 57 PUAN fark

Bu, canli sayfalarda duruyordu: TTKOM'un %39,3 brut marji "sektor
medyani -%32'nin uzerinde" diye sunuluyordu. Dogru kiyas +%24,9.

KURAL
-----
Medyan artik yalnizca ISPATLANMIS sekilde ayni mali takvimdeki
sirketlerden kuruluyor. Takvimi COZULEMEYEN sirket ana kumede
kaliyor -- kaynaktaki gecici bir aksaklik medyani bosaltmamali.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import pathlib
import statistics
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))
sys.path.insert(0, str(_KOK / "analiz"))

import sektor_ozet                                 # noqa: E402
import uret_bilanco as U                           # noqa: E402
import uret_bilanco_sayfa as US                    # noqa: E402

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


def yakin(bulunan, beklenen, tolerans, aciklama: str) -> None:
    global _gecti
    if bulunan is None or abs(bulunan - beklenen) > tolerans:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen} (arti eksi {tolerans})")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: OLCULEN GERCEK DEGERLER -- `sektor_ozet.json`, 2026-10-13.
_ILETISIM = {
    "BIGTK": 24.94, "IHYAY": 11.50, "TTKOM": 39.32,
    "BJKAS": -79.44, "FENER": -100.86, "TSPOR": -75.57,
}
#: kod -> son donemin BITIS TARIHI. Kaynaktan olculdu (2026-10-13).
_BITIS = {
    "BIGTK": "2026-06-30", "IHYAY": "2026-06-30", "TTKOM": "2026-06-30",
    "BJKAS": "2026-05-31", "FENER": "2026-05-31", "TSPOR": "2026-05-31",
}
#: kod -> mali yil bitis ayi. Yalnizca aciklama icin; AYRIM OLCUTU
#: DEGIL -- gruplama bitis tarihine gore yapiliyor.
_TAKVIM = {"BJKAS": 5, "FENER": 5, "TSPOR": 5}

print("1. Kusur gercek verilerle YENIDEN URETILIYOR")
_hepsi = statistics.median(_ILETISIM.values())
yakin(_hepsi, -32.03, 0.01, "karisik medyan -32,03 (yayindaki sayi)")
_ana = statistics.median(v for k, v in _ILETISIM.items()
                         if k not in _TAKVIM)
yakin(_ana, 24.94, 0.01, "takvim yili medyani +24,94")
if abs(_ana - _hepsi) < 50:
    print("  DUSTU  fark 50 puandan az -- olcum araci kusuru gostermiyor")
    raise SystemExit(1)
_gecti += 1
print(f"  gecti  iki medyan {abs(_ana - _hepsi):.1f} puan ayriliyor")

print("")
print("2. sektor_isle DONEME gore ayiriyor")
_ASIL_SEKTORDEKI = U.sektordeki
_ASIL_ARA = U.bilanco_ag.ara_donem
_ASIL_ARA_SN = U.bilanco_ag.ARA_SN


def _tablo_kur(brut_marj, ay, bitis):
    """Tam bir tablo; yalnizca brut kar ve donem degisiyor."""
    hasilat = 1000.0
    return {
        "gelir": {"Revenue": hasilat,
                  "Gross Profit": hasilat * brut_marj / 100.0,
                  "Operating Income": 50.0, "Net Income": 40.0},
        "bilanco": {"Total Assets": 5000.0, "Shareholders' Equity": 2000.0,
                    "Total Current Assets": 1500.0,
                    "Total Current Liabilities": 800.0,
                    "Accounts Receivable": 300.0, "Inventory": 200.0},
        "nakit": {"Operating Cash Flow": 60.0, "Cash Interest Paid": 10.0},
        "gelir_onceki": {}, "bilanco_onceki": {}, "nakit_onceki": {},
        "_mali": {"yil_sonu_ayi": ay, "son_bitis": bitis},
    }


try:
    # Bekleme artik `bilanco_ag.ara_ver()`den geliyor;
    # eskiden `uret_bilanco.ARA_SN` ayri bir sabitti.
    U.bilanco_ag.ARA_SN = 0
    U.sektordeki = lambda s: [(k, {"unvan": k}) for k in sorted(_ILETISIM)]
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo_kur(_ILETISIM[kod], _TAKVIM.get(kod, 12), _BITIS[kod]))
    _r = U.sektor_isle("İletişim", "2026 2. çeyrek", 1)

    esit(sorted(_r["sirket"]), sorted(_ILETISIM), "alti sirket de olculdu")
    esit(_r["ana_donem"], "2026-06-30",
         "ana donem EN COK sirketin bildirdigi tarih")
    esit(_r["sirket_sayisi"], 3, "ana kume UC sirket (kulupler ayrildi)")
    yakin(_r["medyan"]["brut_marj"], 24.94, 0.01,
          "ANA MEDYAN artik +24,94 (-32,03 DEGIL)")
    esit(sorted(_r["donem_gruplari"]), ["2026-05-31"],
         "tek bir ayri donem grubu kuruldu")
    _g = _r["donem_gruplari"]["2026-05-31"]
    esit(_g["sirket_sayisi"], 3, "grup uc sirket")
    esit(_g["donem"], "2026 mart–mayıs", "grup ay adlariyla")
    esit(sorted(_g["kodlar"]), ["BJKAS", "FENER", "TSPOR"],
         "gruptaki sirketler")
    yakin(_g["medyan"]["brut_marj"], -79.44, 0.01,
          "grup medyani kendi aralarindan (-79,44)")

    print("")
    print("2b. MALI YIL SONU ayrim olcutu DEGIL")
    # ARENA mali yilini martta bitiriyor ama donemi TTKOM ile ayni
    # uc ay. Mali yil sonuna gore gruplanirsa gereksiz ayrilirdi.
    _k = {"TTKOM": 39.32, "BIGTK": 24.94, "ARENA": 11.50}
    U.sektordeki = lambda s: [(x, {"unvan": x}) for x in sorted(_k)]
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo_kur(_k[kod], 3 if kod == "ARENA" else 12, "2026-06-30"))
    _r4 = U.sektor_isle("Karışık", "2026 2. çeyrek", 1)
    esit(_r4["donem_gruplari"], {},
         "ayni donemi bildirenler AYRILMIYOR (mali yil farkli olsa da)")
    esit(_r4["sirket_sayisi"], 3, "ucu de ana kumede")
    esit(sorted(_r4["mali"]), ["ARENA"],
         "mali yil farki yalnizca ACIKLAMA icin kaydediliyor")
    U.sektordeki = lambda s: [(x, {"unvan": x}) for x in sorted(_ILETISIM)]

    print("")
    print("3. Bitisi COZULEMEYEN sirket ana kumede kaliyor")
    # Kaynak tarih satirini vermedi: `yil_sonu_ayi` None. Boyle bir
    # sirketi dislamak, gecici bir aksaklikta medyani bosaltirdi.
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo_kur(_ILETISIM[kod], None, None))
    _r2 = U.sektor_isle("İletişim", "2026 2. çeyrek", 1)
    esit(_r2["sirket_sayisi"], 6, "altisi da ana kumede")
    esit(_r2["donem_gruplari"], {}, "grup kurulmadi")
    yakin(_r2["medyan"]["brut_marj"], -32.03, 0.01,
          "takvim bilinmiyorsa eski davranis korunuyor (tahmin YOK)")

    print("")
    print("4. Grupta yeterli sirket yoksa medyan URETILMIYOR")
    _tek = {"YALNIZ": 11.0, "A": 20.0, "B": 22.0, "C": 24.0}
    U.sektordeki = lambda s: [(k, {"unvan": k}) for k in sorted(_tek)]
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo_kur(_tek[kod], 12,
                   "2026-05-31" if kod == "YALNIZ" else "2026-06-30"))
    _r3 = U.sektor_isle("Bilişim", "2026 2. çeyrek", 1)
    _gy = _r3["donem_gruplari"]["2026-05-31"]
    esit(_gy["sirket_sayisi"], 1, "grupta bir sirket")
    esit(_gy["medyan"], {},
         f"medyan YOK (en az {sektor_ozet.EN_AZ_SIRKET} gerekiyor)")
    yakin(_r3["medyan"]["brut_marj"], 22.0, 0.01, "ana medyan saglam")
finally:
    U.sektordeki = _ASIL_SEKTORDEKI
    U.bilanco_ag.ara_donem = _ASIL_ARA
    U.bilanco_ag.ARA_SN = _ASIL_ARA_SN

print("")
print("5. Sayfa DOGRU kiyas kumesini aliyor")
_v = {
    "donem": "2026 2. çeyrek",
    "medyan": {"brut_marj": 24.94}, "sirket_sayisi": 3,
    "ana_donem": "2026-06-30",
    "mali": {"FENER": 5},
    "bitis": {"TTKOM": "2026-06-30", "FENER": "2026-05-31"},
    "donem_gruplari": {"2026-05-31": {"medyan": {"brut_marj": -79.44},
                                      "sirket_sayisi": 3,
                                      "donem": "2026 mart–mayıs"}},
}
esit(US.kiyas_kumesi(_v, "TTKOM"),
     ({"brut_marj": 24.94}, 3, "2026 2. çeyrek", ""),
     "ana donemdeki sirket ANA kumeyi aliyor")
_f = US.kiyas_kumesi(_v, "FENER")
esit(_f[:3], ({"brut_marj": -79.44}, 3, "2026 mart–mayıs"),
     "kulup KENDI kumesini ve ay adli donemi aliyor")
esit(_f[3], "Şirketin mali yılı mayıs sonunda bitiyor, takvim yılıyla "
            "örtüşmüyor; bu yüzden dönemi ay adlarıyla yazılıyor.",
     "MALI TAKVIM OKURA SOYLENIYOR")
esit(US.kiyas_kumesi(_v, "BILINMEYEN"),
     ({"brut_marj": 24.94}, 3, "2026 2. çeyrek", ""),
     "bitisi bilinmeyen sirket ANA kumede kaliyor")

# ESKI OZET DOSYASI BOZMAMALI: yeni anahtarlar yoksa eski davranis.
_eski = {"donem": "2026 2. çeyrek", "medyan": {"brut_marj": 1.0},
         "sirket_sayisi": 9}
esit(US.kiyas_kumesi(_eski, "X"),
     ({"brut_marj": 1.0}, 9, "2026 2. çeyrek", ""),
     "eski ozet dosyasi geriye donuk calisiyor")

# Grubun medyani yoksa BOS doniyor -- cagiran sayfayi yazmiyor.
_yetersiz = {"donem": "2026 2. çeyrek", "medyan": {"brut_marj": 1.0},
             "sirket_sayisi": 9, "ana_donem": "2026-06-30",
             "bitis": {"TEK": "2026-03-31"},
             "donem_gruplari": {"2026-03-31": {"medyan": {},
                                               "sirket_sayisi": 1}}}
esit(US.kiyas_kumesi(_yetersiz, "TEK")[0], {},
     "kiyas kumesi yetersizse medyan BOS (sayfa yazilmaz)")

print("")
print("6. ETIKET COGUNLUGA DEGIL TARIHE BAGLI")
#
# OLCULDU, GERCEK VERIYLE (2026-10-13). GSRAY'in sektoru doldugu
# icin İletişim yedi sirket oldu ve DORDU futbol kulubu:
#
#   -> ana donem 2026-05-31: 4 sirket   (BJKAS, FENER, GSRAY, TSPOR)
#   -> 2026 2. çeyrek: 3 sirket         (BIGTK, IHYAY, TTKOM)
#
# Yani kulupler COGUNLUK oldu ve ana grubu onlar olusturdu. Ilk
# surum ana gruba SEKTORUN takvim etiketini veriyordu; FENER
# "2026 2. çeyrek" etiketini devralirdi -- oysa donemi mart-mayis.
#
# Etiket artik yalnizca TARIHE bakiyor.
_kulup_cogunluk = {
    "donem": "2026 2. çeyrek",          # sektorun takvim etiketi
    "medyan": {"brut_marj": -79.44}, "sirket_sayisi": 4,
    "ana_donem": "2026-05-31",          # KULUPLER ana grup
    "mali": {"FENER": 5, "GSRAY": 5},
    "bitis": {"FENER": "2026-05-31", "GSRAY": "2026-05-31",
              "TTKOM": "2026-06-30"},
    "donem_gruplari": {"2026-06-30": {"medyan": {"brut_marj": 24.94},
                                      "sirket_sayisi": 3}},
}
_f = US.kiyas_kumesi(_kulup_cogunluk, "FENER")
esit(_f[2], "2026 mart–mayıs",
     "kulup ANA GRUPTA olsa da kendi donemini yaziyor")
yakin(_f[0]["brut_marj"], -79.44, 0.01, "kulup kendi medyanini aliyor")
esit(_f[1], 4, "kulup grubu dort sirket")
_t = US.kiyas_kumesi(_kulup_cogunluk, "TTKOM")
esit(_t[2], "2026 2. çeyrek",
     "takvim sirketi AZINLIKTA olsa da alisilmis etiketi aliyor")
yakin(_t[0]["brut_marj"], 24.94, 0.01, "takvim grubu medyani")
esit(_t[1], 3, "takvim grubu uc sirket")
# Bitisi bilinmeyen sirket sektorun etiketine dusuyor.
esit(US.kiyas_kumesi(_kulup_cogunluk, "BILINMEYEN")[2], "2026 2. çeyrek",
     "bitisi bilinmeyen sektor etiketini aliyor")

# ---------------------------------------------------------------
print("")
print("DONEM BITISI EN TAZE BILINEN KAYNAKTAN")
print("")

# KUSUR (olculdu 2026-11-01): ozetteki `bitis[kod]` yalnizca sektorun
# TAMAMI cekildiginde guncelleniyor ve bu, kaynagin kosu basina
# verdigi ~82 istekle buyuk sektorlerde mumkun degil. Olculdu: veri
# adimi #58-#64 arasinda 11 sektorun 11'ini "KAYNAK REDDEDIYOR" ile
# atladi -- ozet DONDU ve hicbir sirket yeni ceyrege gecemedi.
#
# Nobet defteri ayni bilgiyi sirket basina TEK istekle veriyor ve o
# istek zaten yapiliyor. Olculmus ama kullanilmayan veri vardi.

_DEFTER_Q3 = {"TTKOM": "2026-09-30"}

_y = US.kiyas_kumesi(_kulup_cogunluk, "TTKOM", _DEFTER_Q3)
esit(_y[2], "2026 3. çeyrek",
     "defter ozetten YENI ise etiket ilerliyor")
# MEDYAN UYDURULMUYOR: Q3 kiyas grubu YOK, sayfa kiyassiz yazilir.
esit(_y[0], {}, "o donemin grubu yoksa medyan BOS (kiyassiz sayfa)")
esit(_y[1], 0, "kiyassiz sayfada sirket sayisi sifir")
# ATILLIK: ayni cagri defter OLMADAN eski etiketi veriyor mu? Vermezse
# yukaridaki iddia etiketin ilerledigini DEGIL, hep Q3 oldugunu
# gosterirdi.
esit(US.kiyas_kumesi(_kulup_cogunluk, "TTKOM")[2], "2026 2. çeyrek",
     "atillik kontrolu: defter olmadan etiket ESKI kaliyor")
yakin(US.kiyas_kumesi(_kulup_cogunluk, "TTKOM")[0]["brut_marj"], 24.94,
      0.01, "atillik kontrolu: defter olmadan medyan DOLU")

# DAHA ESKISI KAZANMIYOR. Defter bayatsa (sirkete sira gelmediyse)
# ozet aynen gecerli -- yoksa tazelenmis bir sektor, eski bir defter
# kaydiyla geriye cekilirdi.
_g = US.kiyas_kumesi(_kulup_cogunluk, "TTKOM", {"TTKOM": "2026-03-31"})
esit(_g[2], "2026 2. çeyrek", "defter ESKI ise ozet kazaniyor")
yakin(_g[0]["brut_marj"], 24.94, 0.01, "eski defter medyani bozmuyor")

# AYNI TARIH: hicbir sey degismiyor.
esit(US.kiyas_kumesi(_kulup_cogunluk, "TTKOM",
                     {"TTKOM": "2026-06-30"})[2], "2026 2. çeyrek",
     "ayni tarih etiketi degistirmiyor")

# TAKVIM DISI DONEM AY ADLARIYLA. Defterden gelen tarih de ayni
# isleve giriyor; "3. ceyrek" demek kulubu yanlis yere gotururdu.
esit(US.kiyas_kumesi(_kulup_cogunluk, "FENER",
                     {"FENER": "2026-08-31"})[2], "2026 haziran–ağustos",
     "defterden gelen takvim disi tarih AY ADLARIYLA yaziliyor")

# OZETTE HIC BITISI OLMAYAN SIRKET de defterden ilerliyor.
esit(US.kiyas_kumesi(_kulup_cogunluk, "BILINMEYEN",
                     {"BILINMEYEN": "2026-09-30"})[2], "2026 3. çeyrek",
     "ozette bitisi olmayan sirket defterden etiket aliyor")

# MEKANIK: "yeni mi" karari IKINCI KEZ TANIMLANMIYOR.
#
# Olcut `bilanco_nobetci.daha_yeni` -- takvim disi mali yilda
# etiket yerine TARIH kiyaslama kurali orada yazili. Burada yeniden
# yazilsaydi, o ayrim degistigi gun biri guncellenip oteki
# unutulurdu.
import ast                                                # noqa: E402
import inspect                                            # noqa: E402

_agac = ast.parse(inspect.getsource(US.kiyas_kumesi))
_ice = [(d.module, [a.name for a in d.names])
        for d in ast.walk(_agac) if isinstance(d, ast.ImportFrom)]
_modul = [d.names[0].name for d in ast.walk(_agac)
          if isinstance(d, ast.Import)]
esit("bilanco_nobetci" in _modul, True,
     f"karar bilanco_nobetci'den okunuyor ({_modul})")
# Ciplak bir tarih kiyasi KALMAMALI: `iso > ...` gibi bir satir,
# kurali burada ikinci kez tanimlamak olurdu.
_kiyas = [d for d in ast.walk(_agac) if isinstance(d, ast.Compare)
          and any(isinstance(o, (ast.Gt, ast.Lt, ast.GtE, ast.LtE))
                  for o in d.ops)]
esit(_kiyas, [], "islev icinde ciplak tarih kiyasi YOK")

# ---------------------------------------------------------------
print("")
print("HER CAGRI YERI AYNI HARITAYI VERMELI")
print("")

# OLCULDU: mutasyon sinamasinda uc mutant KACTI -- `kiyas_kumesi`
# yardimcisi sinaniyordu ama CAGRI YERLERININ haritayi gectigi
# hicbir yerde sinanmiyordu. Haritayi gecmeyen tek bir cagri,
# etiketi iki ayri yerde iki ayri sekilde belirler:
#
#   uretim  defterden -> "2026 3. çeyrek"
#   tazeleme ozetten  -> "2026 2. çeyrek"
#
# Ve `sayfa_tazele` sayfa donemini bu etiketle karsilastirdigi icin
# uretimin yeni yazdigi her sayfayi "donem uyusmuyor" diye
# REDDEDERDI. Yani kusur sessiz: hicbir sey hata vermez, yalnizca
# hat kendi urettigini tanimaz.

_KOK_D = pathlib.Path(__file__).resolve().parent
_cagri_yerleri = []
for _dosya in (_KOK_D / "uret_bilanco_sayfa.py",
               _KOK_D / "bilanco_tazele.py"):
    _a = ast.parse(_dosya.read_text(encoding="utf-8"))
    for _d in ast.walk(_a):
        if not isinstance(_d, ast.Call):
            continue
        _f = _d.func
        _ad = (_f.attr if isinstance(_f, ast.Attribute)
               else _f.id if isinstance(_f, ast.Name) else "")
        if _ad != "kiyas_kumesi":
            continue
        _arg = len(_d.args) + len(_d.keywords)
        _cagri_yerleri.append((_dosya.name, _d.lineno, _arg))

# ATILLIK: tarama gercekten cagri buluyor mu? Bulamayan bir tarama
# "hepsi ucluyle cagriliyor" iddiasini her zaman gecirir.
esit(len(_cagri_yerleri) >= 4, True,
     f"atillik kontrolu: {len(_cagri_yerleri)} cagri yeri bulundu "
     f"({_cagri_yerleri})")
_eksik_cagri = [(d, s) for d, s, n in _cagri_yerleri if n < 3]
esit(_eksik_cagri, [],
     f"her cagri donem bitis haritasini veriyor ({_cagri_yerleri})")

# DAVRANIS: kuyruk bayatligi defterden gorebiliyor mu?
#
# Mekanik kural cagriyi garanti ediyor, bu iddia SONUCU olcuyor:
# sayfasi olan ama defterde yeni donem bildiren sirket kuyrugun
# BASINA (oncelik 0) gelmeli. Gelmezse sirkete hic sira gelmez --
# sessiz kilit, bu depoda bir kez yayina cikti.
_oz = {"Finans": {
    "donem": "2026 2. çeyrek",
    "medyan": {"brut_marj": 10.0}, "sirket_sayisi": 5,
    "ana_donem": "2026-06-30",
    "bitis": {"TTKOM": "2026-06-30"},
    "sirket": {"TTKOM": {"brut_marj": 11.0}},
}}
_yayim = {("TTKOM", "2026 2. çeyrek")}
_sayfali = {"TTKOM"}

_k_eski = US.kuyruk_kur(_oz, set(), sayfasi_olan=_sayfali,
                        bitisler={"TTKOM": "2026-06-30"},
                        yayimlanmis=_yayim)
esit([x[0] for x in _k_eski], [2],
     "atillik kontrolu: defter de Q2 derken sirket bayat DEGIL")

_k_yeni = US.kuyruk_kur(_oz, set(), sayfasi_olan=_sayfali,
                        bitisler={"TTKOM": "2026-09-30"},
                        yayimlanmis=_yayim)
esit([x[0] for x in _k_yeni], [0],
     "defter yeni donem derken sirket ONCELIK 0 (bayat)")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
