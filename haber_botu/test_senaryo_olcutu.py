# -*- coding: utf-8 -*-
"""SUNULAN HER OLCUT GERCEKTEN SONUCLANABILMELI.

BU DOSYA NEDEN VAR -- OLCULDU (2026-10-19)
------------------------------------------
Senaryo formu `worker.js` icindeki `OLCUT_KODLARI` listesinden on
bes "olculebilir tetikleyici" sunuyor. Sonuclandirma ise Python
tarafinda `senaryo_sonuclandir.esik_gecildi` ile yapiliyor.

Liste JS'te, cozucu Python'da. Iki dil, iki dosya, tek kural -- ve
ayristi:

    esik_gecildi yalnizca `gosterge` tablosunu okuyordu
    PAXGUSD (altin) ve XBTUSD (Bitcoin) ise `fiyat` tablosunda

Veri VARDI (337'ser gozlem), yanlis tabloya bakiliyordu. Kusur
sessiz VE GECIKMELI: kullanici tetikleyiciyi kuruyor, uygulama
kabul ediyor, AYLAR SONRA ufku dolunca senaryo "belirsiz -- veri
bulunamadi" diye kapaniyordu. O noktada ne kullanici ne de biz
sebebini anlayabilirdik.

`worker.js` uyariyi zaten tasiyor:

    "Yarim bir tetikleyici hic tetikleyici olmamasindan KOTUDUR:
     kullanici 'ayarladim' saniyor ama senaryo ufku dolunca yine
     'belirsiz' cikiyor."

Kod o uyariyi iki kod icin ihlal ediyordu. Bu sinama sinifi
kapatiyor: LISTE WORKER'DAN OKUNUYOR, her kod DEPODA aranIYOR.
Yarin listeye bir kod eklenir ve verisi yoksa, aylar sonra degil
BURADA kirmizi doner.

AG KULLANILMIYOR. Yalnizca yerel depo okunuyor.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

WORKER = _KOK.parent / "site" / "worker.js"
DEPO = _KOK / "netaris.db"

import senaryo_sonuclandir as S                     # noqa: E402

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


def olcut_kodlari() -> list[str]:
    """`worker.js` icindeki listeyi OKUR -- burada yeniden yazmaz.

    Yeniden yazmak, sinamanin korudugu seyi kendi icinde
    kopyalamasi olurdu: liste degisince sinama ESKI listeyi
    dogrulamaya devam eder ve yesil kalir. Bu depoda tam bu tuzak
    kayitli ("beklentisini korudugu koddan okuyan sinama").
    """
    ham = WORKER.read_text(encoding="utf-8")
    m = re.search(r"const OLCUT_KODLARI\s*=\s*\[(.*?)\]", ham, re.S)
    if not m:
        print("  DUSTU  worker.js icinde OLCUT_KODLARI bulunamadi")
        raise SystemExit(1)
    return re.findall(r'"([^"]+)"', m.group(1))


print("")
print("1. LISTE WORKER'DAN OKUNUYOR")
KODLAR = olcut_kodlari()
print(f"  {len(KODLAR)} olcut kodu okundu")
if len(KODLAR) < 5:
    print("  DUSTU  olcut listesi beklenmedik sekilde kisa")
    raise SystemExit(1)
_gecti += 1

print("")
print("2. HER KOD DEPODA COZULEBILIYOR")
#
# "Cozulebilir" = `esik_gecildi` o kod icin veri BULABILIYOR.
# Dogrudan o islev cagriliyor: tabloyu elle sorgulamak, islevin
# hangi tabloya baktigini VARSAYMAK olurdu ve kusur tam oradaydi.
if not DEPO.exists():
    print(f"  ATLANDI  depo yok: {DEPO}")
else:
    b = sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True)
    try:
        cozulemeyen = []
        for kod in KODLAR:
            # Cok genis pencere: "veri var mi" soruluyor, esigin
            # gecilip gecilmedigi degil. Esik -1e18 ve yon
            # "ustunde" -> veri varsa True, yoksa None.
            sonuc = S.esik_gecildi(b, kod, "ustunde", -1e18,
                                   "1900-01-01", "2100-01-01")
            if sonuc is None:
                cozulemeyen.append(kod)
        if cozulemeyen:
            print(f"  DUSTU  {len(cozulemeyen)} olcut kodu COZULEMIYOR:")
            for k in cozulemeyen:
                print(f"           {k}")
            print("")
            print("  Bu kodlar senaryo formunda SUNULUYOR ama ufku")
            print("  dolunca 'belirsiz -- veri bulunamadi' donecekler.")
            print("  Kullanici olculebilir bir tetikleyici kurdugunu")
            print("  saniyor; aylar sonra sonuc cikmiyor.")
            print("")
            print("  Cozum: ya seriyi topla, ya kodu listeden cikar.")
            raise SystemExit(1)
        _gecti += 1
        print(f"  gecti  {len(KODLAR)} kodun TAMAMI cozulebiliyor")

        print("")
        print("3. IKI TABLO DA GERCEKTEN KULLANILIYOR")
        # Bu, 2. maddenin yesil kalmasinin SEBEBINI olcuyor: eger
        # yarin biri `fiyat` dalini silerse 2. madde kirmizi doner,
        # ama bu madde NEDENINI de yazar.
        gosterge_kod = [k for k in KODLAR if b.execute(
            "SELECT 1 FROM gosterge WHERE kod = ? LIMIT 1", (k,)).fetchone()]
        fiyat_kod = [k for k in KODLAR if b.execute(
            "SELECT 1 FROM fiyat WHERE sembol = ? LIMIT 1", (k,)).fetchone()]
        print(f"  gosterge tablosundan: {len(gosterge_kod)}")
        print(f"  fiyat tablosundan   : {len(fiyat_kod)}  {fiyat_kod}")
        if not fiyat_kod:
            print("  (fiyat tablosunda olcut kodu yok -- yedek dal"
                  " su an kullanilmiyor)")
        else:
            # Yedek dal GERCEKTEN caliskan olmali: `gosterge`de
            # OLMAYAN bir kod `fiyat`tan cozulebilmeli.
            yalniz_fiyat = [k for k in fiyat_kod if k not in gosterge_kod]
            if yalniz_fiyat:
                for k in yalniz_fiyat:
                    s = S.esik_gecildi(b, k, "ustunde", -1e18,
                                       "1900-01-01", "2100-01-01")
                    esit(s, True,
                         f"{k} YALNIZCA fiyat tablosunda ve cozuluyor")
            else:
                _gecti += 1
                print("  gecti  fiyat kodlarinin hepsi gostergede de var")

        print("")
        print("4. VERI YOKSA None -- False DEGIL")
        # "Gecmedi" bir olcum, "veri yok" bir bilgi eksikligi.
        # Ikisini birlestirmek, olcemedigimiz senaryoyu
        # "gerceklesmedi" saymak olurdu.
        esit(S.esik_gecildi(b, "HIC_OLMAYAN_KOD", "ustunde", 1.0,
                            "1900-01-01", "2100-01-01"),
             None, "olmayan kod None donuyor")
        # Pencere disi veri de None.
        esit(S.esik_gecildi(b, KODLAR[0], "ustunde", 1.0,
                            "1800-01-01", "1800-12-31"),
             None, "pencerede veri yoksa None")
    finally:
        b.close()

print("")
print("5. UC KAYNAK AYRISMIYOR: worker · web formu · mobil beslemesi")
#
# Ayni liste bugun UC yerde yasiyor:
#
#   worker.js      OLCUT_KODLARI   -- dogrulama (kabul/ret)
#   uyelik.html    <select>        -- web formu, okunabilir adlar
#   /v1/...json    besleme         -- mobil form, uyelik.html'den
#
# Ucuncusu ikincisinden URETILIYOR, yani o ikisi ayrisamaz. Ama
# worker ile form AYRI yazilmis ve ayrisabilir: forma eklenen bir
# gosterge worker tarafindan REDDEDILIR (kullanici kaydedemez),
# workera eklenip forma eklenmeyen gosterge ise hic gorunmez.
#
# Ikisi de sessiz: ne hata cikar ne gunluge bir sey duser.
sys.path[:0] = [str(_KOK.parent / "site")]
import mobil_besleme as MB                          # noqa: E402

_FORM = _KOK.parent / "site" / "sablonlar" / "uyelik.html"
if not _FORM.is_file():
    print(f"  DUSTU  web formu bulunamadi: {_FORM}")
    raise SystemExit(1)

_olcutler = MB.senaryo_olcutleri(_FORM.read_text(encoding="utf-8"))
_form_kod = [o["kod"] for o in _olcutler]
print(f"  worker: {len(KODLAR)} kod · form: {len(_form_kod)} kod")

_formda_yok = [k for k in KODLAR if k not in _form_kod]
if _formda_yok:
    print(f"  DUSTU  worker'da VAR, formda YOK: {_formda_yok}")
    print("         Bu gostergeler kullaniciya hic gorunmuyor.")
    raise SystemExit(1)
_gecti += 1
print("  gecti  worker'daki her kod formda da var")

_workerda_yok = [k for k in _form_kod if k not in KODLAR]
if _workerda_yok:
    print(f"  DUSTU  formda VAR, worker'da YOK: {_workerda_yok}")
    print("         Kullanici seciyor, sunucu REDDEDIYOR.")
    raise SystemExit(1)
_gecti += 1
print("  gecti  formdaki her kod worker tarafindan kabul ediliyor")

# HER OLCUTUN OKUNABILIR ADI OLMALI: ciplak "TP.FE25.OKTG04"
# kullaniciya hicbir sey anlatmiyor.
_adsiz = [o["kod"] for o in _olcutler if not o["ad"]]
esit(_adsiz, [], "her ölçütün okunabilir adı var")

print("")
print("6. UFUKLAR VE SINIRLAR WORKER ILE AYNI")
_ham = WORKER.read_text(encoding="utf-8")

_u = re.search(r"const UFUKLAR\s*=\s*\{(.*?)\}", _ham, re.S)
if not _u:
    print("  DUSTU  worker.js icinde UFUKLAR bulunamadi")
    raise SystemExit(1)
_worker_ufuk = re.findall(r'"([^"]+)"\s*:', _u.group(1))
esit(list(MB.UFUKLAR), _worker_ufuk, "ufuk listesi worker ile AYNI")

# Uzunluk sinirlari: uygulama bunlari BILMELI. Kullanicinin 200
# karakter yazip sunucudan hata almasi, 180'de uyarilmasindan kotu.
_ESLEME = (
    ("kosul", "EN_AZ_KOSUL", "EN_COK_KOSUL"),
    ("sonuc", "EN_AZ_KOSUL", "EN_COK_SONUC"),
    ("gerekce", None, "EN_COK_GEREKCE"),
    ("curutme", None, "EN_COK_CURUTME"),
    ("kaynaklar", None, "EN_COK_KAYNAK"),
    ("capa_baslik", None, "EN_COK_BASLIK"),
)


def _sabit(ad: str) -> int:
    m = re.search(r"const " + ad + r"\s*=\s*(\d+)\s*;", _ham)
    if not m:
        print(f"  DUSTU  worker.js icinde {ad} bulunamadi")
        raise SystemExit(1)
    return int(m.group(1))


for _alan, _az_ad, _cok_ad in _ESLEME:
    _bizim = MB.SENARYO_SINIRLARI[_alan]
    esit(_bizim["en_cok"], _sabit(_cok_ad),
         f"{_alan}: en cok uzunluk worker ile AYNI")
    if _az_ad:
        esit(_bizim["en_az"], _sabit(_az_ad),
             f"{_alan}: en az uzunluk worker ile AYNI")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
