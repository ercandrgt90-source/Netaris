"""tcmb_kur.py testleri -- AGA CIKMAZ.

Bu dosyanin varlik sebebi tek cumleyle: EVDS'nin tarihi kurun GECERLI
OLDUGU gun, bultenin tarihi ACIKLANDIGI gun. Ilki okura OLMAMIS BIR
GUNU gosteriyordu -- 2026-11-21 Cumartesi gunu 2.973 yayimlanmis
sayfada "23 Kasim 2026".
"""

import datetime
import pathlib
import sqlite3
import sys

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))
sys.path.insert(0, str(_BURASI.parent))

import tcmb_kur  # noqa: E402
import beyin  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


# TCMB'nin GERCEK bicimi (20.11.2026 bulteninden kisaltildi).
#
# IKI TARIH OZNITELIGI VAR VE SIRALARI FARKLI:
#     Tarih="20.11.2026"   gun.ay.yil
#     Date="11/20/2026"    ay/gun/yil
# Yanlisini okumak 11 Kasim'i 20 Kasim sanmak gibi SESSIZ bir kayma
# uretirdi. Asagidaki ornek bunu ayirt edebilecek bicimde secildi:
# gun ve ay BIRBIRINDEN FARKLI (20 ve 11).
BULTEN = """<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="20.11.2026" Date="11/20/2026" Bulten_No="2026/219">
<Currency CrossOrder="0" Kod="USD" CurrencyCode="USD">
 <Unit>1</Unit><Isim>ABD DOLARI</Isim>
 <ForexBuying>50.4028</ForexBuying><ForexSelling>50.4936</ForexSelling>
 <BanknoteBuying>50.3676</BanknoteBuying>
</Currency>
<Currency CrossOrder="9" Kod="EUR" CurrencyCode="EUR">
 <Unit>1</Unit><Isim>EURO</Isim>
 <ForexBuying>55.3021</ForexBuying><ForexSelling>55.3970</ForexSelling>
</Currency>
<Currency CrossOrder="5" Kod="JPY" CurrencyCode="JPY">
 <Unit>100</Unit><Isim>JAPON YENI</Isim>
 <ForexBuying>32.1000</ForexBuying><ForexSelling>32.2000</ForexSelling>
</Currency>
</Tarih_Date>"""

print("1. Bulten tarihi -- GUN.AY.YIL, ay/gun/yil DEGIL")
es("tarih cozuldu", tcmb_kur._tarih_coz("20.11.2026"), "2026-11-20")
# AYIRT EDICI: ay/gun/yil okunsaydi "2026-11-20" degil baska bir sey
# cikardi. Tek haneli gun/ay ile de sinaniyor.
es("tek haneli gun/ay", tcmb_kur._tarih_coz("3.7.2026"), "2026-07-03")
es("bozuk tarih bos doner", tcmb_kur._tarih_coz("20/11/2026"), "")
es("bos tarih bos doner", tcmb_kur._tarih_coz(""), "")

print("2. Bulten cozumu")
_c = dict((k, (t, d)) for k, t, d in tcmb_kur.coz(BULTEN))
es("USD satis kuru -- ALIS DEGIL",
   _c.get("TCMB_USDTRY"), ("2026-11-20", 50.4936))
es("EUR satis kuru", _c.get("TCMB_EURTRY"), ("2026-11-20", 55.3970))
es("tanimsiz para (JPY) alinmiyor", "TCMB_JPYTRY" in _c, False)
es("yalnizca tanimli iki seri", len(_c), 2)

# ALIS/SATIS KARISTIRILMAMALI: EVDS karsiligi `TP.DK.*.S.YTL` ve
# sondaki `S` SATIS demek. Alis okunsaydi deger 50.4028 olurdu.
dogru("okunan deger alis kuru DEGIL",
      _c["TCMB_USDTRY"][1] != 50.4028)

print("3. Tarih yoksa HICBIR SEY donmez")
# Tarihsiz bulten, tarihi BILINMEYEN gozlem demek. Bugune sabitlemek
# yanlis bir gun uydurmak olurdu.
es("tarihsiz bulten bos liste",
   tcmb_kur.coz(BULTEN.replace('Tarih="20.11.2026"', 'Tarih=""')), [])

print("4. Unit boluniyor -- 100'luk para 100 kat sapmasin")
_jpy = dict(tcmb_kur.KODLAR)
_jpy["JPY"] = ("TCMB_JPYTRY", "JPY/TRY")
_eski = tcmb_kur.KODLAR
try:
    tcmb_kur.KODLAR = _jpy
    _k = dict((k, d) for k, _t, d in tcmb_kur.coz(BULTEN))
    # 32.20 / 100 = 0.322. Bolunmeseydi 32.2 olurdu, yani 100 KAT.
    es("Unit=100 olan para bolunuyor", round(_k["TCMB_JPYTRY"], 4), 0.3220)
finally:
    tcmb_kur.KODLAR = _eski

print("5. Depoya yazma")
_b = sqlite3.connect(":memory:")
_b.executescript(beyin.SEMA)
es("yazilan satir", tcmb_kur.depoya_yaz(_b, tcmb_kur.coz(BULTEN)), 2)
es("deger depoda",
   _b.execute("SELECT deger FROM gosterge WHERE kod='TCMB_USDTRY'"
              ).fetchone()[0], 50.4936)
es("kaynak TCMB diye isaretli",
   _b.execute("SELECT kaynak FROM gosterge WHERE kod='TCMB_USDTRY'"
              ).fetchone()[0], "TCMB")
es("EVDS koduna YAZILMIYOR",
   _b.execute("SELECT COUNT(*) FROM gosterge WHERE kod='TP.DK.USD.S.YTL'"
              ).fetchone()[0], 0)
es("bos liste yazmaz", tcmb_kur.depoya_yaz(_b, []), 0)

print("6. Gecmis doldurma KENDILIGINDEN SONLANIR")
# Bu, bosa istek harcamamanin tek mekanizmasi. Bu depoda bir nobetci
# bilinen bir soruya kosu basina 60 istek harcamisti.
_b2 = sqlite3.connect(":memory:")
_b2.executescript(beyin.SEMA)
dogru("bos seride doldurma GEREKLI", tcmb_kur.gecmis_gerekli(_b2))

_bugun = datetime.date.today()


def _koy(b, gun_once, deger=50.0):
    g = (_bugun - datetime.timedelta(days=gun_once)).isoformat()
    b.execute("INSERT OR IGNORE INTO gosterge"
              " (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
              " VALUES ('TCMB_USDTRY',?,?,'TL','USD/TRY','TCMB','x')",
              (g, deger))


_koy(_b2, 1)
dogru("yalnizca DUNU olan seride doldurma hala gerekli",
      tcmb_kur.gecmis_gerekli(_b2))
_koy(_b2, tcmb_kur.GECMIS_PENCERE_GUN)
es("en eski satir pencerenin disina cikinca doldurma BITER",
   tcmb_kur.gecmis_gerekli(_b2), False)

print("7. Gecmis cekimi -- YALNIZCA EKSIK IS GUNLERI, TAVANLI")

_istenen: list[str] = []


class _SahteYanit:
    status_code = 200
    text = BULTEN


def _sahte_al(adres, headers=None, timeout=None):
    _istenen.append(adres)
    return _SahteYanit()


class _SahteIstemci:
    get = staticmethod(_sahte_al)


_b3 = sqlite3.connect(":memory:")
_b3.executescript(beyin.SEMA)
# Sabit bir "bugun": 2026-11-21 Cumartesi.
_cmt = datetime.date(2026, 11, 21)
_istenen.clear()
tcmb_kur.gecmis_cek(_b3, _SahteIstemci, bugun=_cmt)
es("istek sayisi TAVANI asmiyor",
   len(_istenen) <= tcmb_kur.GECMIS_TAVAN, True)
dogru("cuma (20.11) istendi", any("20112026" in a for a in _istenen))
# HAFTA SONU ISTENMEZ: bulten yok, istek bosa gider.
dogru("cumartesi (21.11) ISTENMEDI",
      not any("21112026" in a for a in _istenen))
dogru("pazar (15.11) ISTENMEDI",
      not any("15112026" in a for a in _istenen))

# DEPODA OLAN GUN YENIDEN ISTENMEZ.
_b4 = sqlite3.connect(":memory:")
_b4.executescript(beyin.SEMA)
_b4.execute("INSERT INTO gosterge"
            " (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
            " VALUES ('TCMB_USDTRY','2026-11-20',50.0,'TL','USD/TRY','TCMB','x')")
_istenen.clear()
tcmb_kur.gecmis_cek(_b4, _SahteIstemci, bugun=_cmt)
dogru("depoda OLAN gun yeniden istenmiyor",
      not any("20112026" in a for a in _istenen))
dogru("eksik gunler yine isteniyor", len(_istenen) > 0)


# 200 DISI YANIT GUNU ATLAR, ADIMI DUSURMEZ (tatil boyle gorunur).
#
# GOVDE AYRISTIRILABILIR OLMALI -- ILK YAZIMDA DEGILDI VE MUTASYON
# KACTI. Bos govdeyle sinanirsa, durum kodu kontrolu sokuldugunda
# XML ayristiricisi zaten patliyor ve `except` onu yutuyor: sinama
# yesil kaliyor ama OLCTUGU SEY durum kodu DEGIL, bozuk XML.
#
# Gercek tehlike tam tersi: sunucu 404/302 ile BASKA BIR GUNUN ya da
# bugunun bultenini dondurursa, tatil gunune BASKA BIR GUNUN kuru
# yazilirdi. Bu yuzden sahte yanit gecerli bir bulten tasiyor.
class _Dort04:
    status_code = 404
    text = BULTEN


class _HepDort04:
    get = staticmethod(lambda a, headers=None, timeout=None: _Dort04())


_b5 = sqlite3.connect(":memory:")
_b5.executescript(beyin.SEMA)
es("404 donen gunlerden kayit gelmez",
   tcmb_kur.gecmis_cek(_b5, _HepDort04, bugun=_cmt), [])

for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
