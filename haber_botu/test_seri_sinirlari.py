"""Akla yatkinlik siniri YAZMA yolunda da gecerli mi?

NEDEN VAR
---------
2026-11-01 07:23 UTC -- TCMB EVDS, TP.FE25 grubunu bozuk dondurmeye
basladi. Ayni seri kodu bir ay yillik degisimi (%31,88), ertesi ay
aylik degisimi (%1,46) verdi; grubun TAMAMI (OKTG01..OKTG08) ayni
bicimde bozuldu, yani kaynak arizasi.

`veri_dogrula --duzelt` kaynagi KOSULSUZ dogru sayiyordu: depo ile
kaynak ayrisirsa depoyu kaynaga gore eziyordu. TP.FE25.OKTG04'un
48 gozlemi -- 2022-10'a kadar GERIYE -- cople degistirildi. 2026-09
cekirdek enflasyonu %28,71'den %-39,22'ye dondu.

`denetim.py` DOGRU davranip "-39,22 seri sinirinin disinda" dedi ve
yayini durdurdu. Ama yayin karari TUM siteyi kapsiyor: haber, piyasa,
bilanco, hepsi. Site bes saat yerde kaldi ve adim "basarili" gorundugu
icin (cikti kuyrugu kisa) EKRANDA HICBIR SEY GORUNMEDI.

Iki ayri kusur vardi:

  1. YAZICI, DENETLEYENIN OLCUTUNU KULLANMIYORDU. Sinirlar
     `denetim.py` icinde duruyordu ve yalnizca denetim okuyordu.
     Denetimin reddedecegi bir deger depoya hic girmemeli.

  2. "DUZELTME" SORGUSUZ KABUL EDILIYORDU. Kaynagin degismesi ile
     depomuzun yanlis olmasi ayni sey degil. Mesru revizyon son
     birkac gozleme dokunur; 48 gozlemi dort yil geriye yeniden yazan
     sey revizyon degil, serinin ANLAMININ degismesidir.

Bu dosya ikisini de olcuyor, hem davranis hem MEKANIK kural olarak:
yarin biri `sinir_disi` cagrisini silerse ya da sinirlari ikinci bir
yere kopyalarsa sinama kalir.
"""
import ast
import inspect
import json
import pathlib
import datetime
import sqlite3
import sys
import tempfile
import textwrap

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import beyin           # noqa: E402
import denetim         # noqa: E402
import seri_sinirlari as S   # noqa: E402
import veri_dogrula as V     # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama):
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


def dogru(bulunan, aciklama):
    esit(bool(bulunan), True, aciklama)


def _sapma(kod, tarih, bizdeki, dogru_deger):
    """`veri_dogrula`nin `sapan` listesindeki satir bicimi."""
    return (kod, tarih, bizdeki, dogru_deger,
            abs(dogru_deger - bizdeki), "EVDS aktarim")


# URETIM KARANTINA KAYDI IZOLE EDILIYOR.
#
# Bu sinamalarin hicbiri uretimdeki kaydin ICERIGINE bagli olmamali:
# sahiden bir seri karantinadaysa (bugun TP.FE25.OKTG04 oyle) 3.
# bolumun yazma sinamalari sebepsiz kalirdi. Karantina DAVRANISI 6.
# bolumde, kendi gecici kaydiyla olculuyor.
_URETIM_KARANTINA = S.KARANTINA
_IZOLE = pathlib.Path(tempfile.mkdtemp()) / "karantina-yok.json"
S.KARANTINA = _IZOLE
S.karantinadakiler.cache_clear()

print("\nSeri sinirlari -- yazma yolu denetimin olcutunu kullaniyor mu\n")

# ----------------------------------------------------------------------
# 1. OLCUT -- gercek olayin degerleri
# ----------------------------------------------------------------------
print("1. Olcut")

dogru(S.sinir_disi("TP.FE25.OKTG04", -39.21517672, "%"),
      "bugunun gercek degeri (-39,22) REDDEDILIYOR")
esit(S.sinir_disi("TP.FE25.OKTG04", 28.71184198, "%"), "",
     "dogru deger (28,71) geciyor")
dogru(S.sinir_disi("TP.FE25.OKTG04", 1131.36094675, "%"),
      "kaynaktan gelen 1131,36 REDDEDILIYOR")
# ESIK GERCEKTE ELEMELI: ucu gecer, hemen otesi gecmez.
esit(S.sinir_disi("TP.FE25.OKTG04", -30.0, "%"), "",
     "alt sinirin TAM UCU geciyor")
dogru(S.sinir_disi("TP.FE25.OKTG04", -30.01, "%"),
      "alt sinirin bir adim otesi reddediliyor")
dogru(S.sinir_disi("BILINMEYEN", 350.0, "%"),
      "seriye ozgu sinir yoksa BIRIM siniri uyguluyor")
esit(S.sinir_disi("BILINMEYEN", 1e9, "zirva birim"), "",
     "tanimsiz sinir, gecersiz deger demek DEGIL -- sessiz geciyor")
dogru(S.sinir_disi("UNRATE", float("nan")), "NaN reddediliyor")
# Sinirli seride NaN zaten karsilastirmaya takiliyor; GERCEK bosluk
# siniri TANIMSIZ seri. Mutasyon tam buradan kacti.
dogru(S.sinir_disi("SINIRSIZ", float("nan")),
      "NaN, siniri TANIMSIZ seride de reddediliyor")
dogru(S.sinir_disi("SINIRSIZ", float("inf")),
      "sonsuz, siniri TANIMSIZ seride de reddediliyor")
dogru(S.sinir_disi("UNRATE", float("inf")), "sonsuz reddediliyor")
dogru(S.sinir_disi("UNRATE", "yazi"), "sayi olmayan reddediliyor")

# ----------------------------------------------------------------------
# 2. TEK KAYNAK -- denetim kendi tablosunu TUTMUYOR
# ----------------------------------------------------------------------
print("\n2. Tek kaynak")

esit(denetim.SERI_ARALIK is S.SERI_ARALIK, True,
     "denetim.SERI_ARALIK ayni NESNE -- kopya degil")
esit(denetim.ARALIK is S.ARALIK, True,
     "denetim.ARALIK ayni NESNE -- kopya degil")

_denetim_agaci = ast.parse(
    (_KOK / "denetim.py").read_text(encoding="utf-8"))
_kopya = []
for _d in _denetim_agaci.body:
    if isinstance(_d, (ast.Assign, ast.AnnAssign)):
        _hedefler = ([_d.target] if isinstance(_d, ast.AnnAssign)
                     else list(_d.targets))
        for _h in _hedefler:
            if (isinstance(_h, ast.Name)
                    and _h.id in ("ARALIK", "SERI_ARALIK")
                    and isinstance(_d.value, ast.Dict)):
                _kopya.append(_h.id)
esit(_kopya, [],
     "denetim.py icinde IKINCI bir sinir sozlugu TANIMLANMIYOR")

# ----------------------------------------------------------------------
# 3. YAZICI OLCUTU UYGULUYOR -- davranis
# ----------------------------------------------------------------------
print("\n3. Yazici -- davranis")

_b = sqlite3.connect(":memory:")
_b.executescript(beyin.SEMA)


def _kalem(kod, tarih, deger, birim="%"):
    return {"kod": kod, "tarih": tarih, "deger_ham": deger,
            "birim": birim, "ad": kod, "kaynak": "T"}


_red: list = []
_n = beyin.gosterge_yaz(_b, [
    _kalem("TP.FE25.OKTG04", "2026-10-01", -39.21517672),
    _kalem("TP.FE25.OKTG04", "2026-11-01", 29.5),
    _kalem("UNRATE", "2026-10-01", 4.2, ""),
], _red)
esit(_n, 2, "akla yatkin IKI gozlem yazildi")
esit(len(_red), 1, "yatkin olmayan BIR gozlem reddedildi")
esit(_red[0][0], "TP.FE25.OKTG04", "reddedilen kayit serisini bildiriyor")
dogru(_red[0][3], "reddedilen kayit SEBEBINI bildiriyor")
esit(_b.execute("SELECT COUNT(*) FROM gosterge WHERE deger < 0"
                ).fetchone()[0], 0,
     "bozuk deger depoya HIC girmedi")
esit(_b.execute("SELECT COUNT(*) FROM gosterge").fetchone()[0], 2,
     "depoda yalnizca gecen gozlemler var")

# `reddedilen` verilmezse de yazma yine suzuluyor (eski cagiranlar).
_b2 = sqlite3.connect(":memory:")
_b2.executescript(beyin.SEMA)
esit(beyin.gosterge_yaz(_b2, [_kalem("UNRATE", "2026-10-01", 999.0, "")]), 0,
     "`reddedilen` verilmese de suzgec calisiyor")

# ----------------------------------------------------------------------
# 3b. GELECEK TARIHLI GOZLEM YAZILMAZ -- davranis
#
# OLCULDU (2026-11-21, Cumartesi): depoda TAM IKI satir gelecek
# tarihliydi (TP.DK.USD.S.YTL ve TP.DK.EUR.S.YTL, 2026-11-23) ve
# ikisi de 2026-11-20'de yazilmisti -- yani iddia ettigi gunden UC
# GUN once. Sonuc 2.973 yayimlanmis sayfada gorundu: piyasa seridi
# her sayfada ve "23 Kasim 2026" yaziyordu, sayfanin kendi basligi
# ise "20 Kasim 2026 verileri".
#
# Kural MEKANIZMAYA dayaniyor, esige degil: olmamis bir gunun
# gozlemi olamaz.
# ----------------------------------------------------------------------
print("\n3b. Gelecek tarihli gozlem")

_bugun = beyin._bugun_iso()
_yarin = (datetime.date.fromisoformat(_bugun)
          + datetime.timedelta(days=1)).isoformat()
_dun = (datetime.date.fromisoformat(_bugun)
        - datetime.timedelta(days=1)).isoformat()

_b3 = sqlite3.connect(":memory:")
_b3.executescript(beyin.SEMA)
_red3: list = []
_n3 = beyin.gosterge_yaz(_b3, [
    _kalem("TP.DK.USD.S.YTL", _dun, 50.4694, "TL"),
    _kalem("TP.DK.USD.S.YTL", _bugun, 50.4936, "TL"),
    _kalem("TP.DK.USD.S.YTL", _yarin, 50.5200, "TL"),
], _red3)
esit(_n3, 2, "dun ve BUGUN yazildi -- bugun gelecek DEGIL")
esit(len(_red3), 1, "yalnizca YARIN reddedildi")
esit(_red3[0][1], _yarin, "reddedilen kayit TARIHINI bildiriyor")
dogru("gelecek" in (_red3[0][3] or ""),
      "red sebebi gelecek tarihi ACIKCA soyluyor")
esit(_b3.execute("SELECT COUNT(*) FROM gosterge WHERE tarih > ?",
                 (_bugun,)).fetchone()[0], 0,
     "gelecek tarihli satir depoya HIC girmedi")

# SINIR: tam bugun KABUL EDILMELI. ">" yerine ">=" yazilsa gununun
# verisi hic yazilmazdi ve site her gun bir gun geride kalirdi --
# kusuru duzeltirken calisani bozmanin klasik bicimi.
esit(_b3.execute("SELECT COUNT(*) FROM gosterge WHERE tarih = ?",
                 (_bugun,)).fetchone()[0], 1,
     "BUGUNUN verisi reddedilmiyor (sinir dahil)")

# Kural, akla yatkinlik olcutunu GOLGELEMEMELI: gecmis tarihli ama
# bozuk deger yine reddedilmeli.
_b4 = sqlite3.connect(":memory:")
_b4.executescript(beyin.SEMA)
_red4: list = []
beyin.gosterge_yaz(_b4, [_kalem("UNRATE", _dun, 999.0, "")], _red4)
esit(len(_red4), 1, "gecmis tarihli bozuk deger HALA reddediliyor")
dogru("gelecek" not in (_red4[0][3] or ""),
      "o reddin sebebi gelecek tarihi DEGIL")


# ----------------------------------------------------------------------
# 3c. KURALDAN ONCE GIRMIS GELECEK TARIHLI SATIR DA TEMIZLENIR
#
# Kurali sikilastirmak DEPODA ZATEN OLANI temizlemez. Olculdu: kural
# yazildiginda iki satir duruyordu ve 2.973 sayfada gorunuyordu.
# Bu depoda ayni ders daha once de ogrenildi.
# ----------------------------------------------------------------------
print("\n3c. Eski gelecek tarihli satirin temizligi")

_b5 = sqlite3.connect(":memory:")
_b5.executescript(beyin.SEMA)
# Kurali ATLAYARAK, dogrudan SQL ile koyuyoruz: amac "kuraldan once
# girmis satir" durumunu birebir kurmak.
_b5.execute(
    "INSERT INTO gosterge (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
    " VALUES (?,?,?,?,?,?,?)",
    ("TP.DK.USD.S.YTL", _yarin, 50.52, "TL", "USD/TRY", "EVDS", "x"))
_b5.execute(
    "INSERT INTO gosterge (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
    " VALUES (?,?,?,?,?,?,?)",
    ("UNRATE", _yarin, 4.2, "", "UNRATE", "FRED", "x"))
esit(_b5.execute("SELECT COUNT(*) FROM gosterge WHERE tarih > ?",
                 (_bugun,)).fetchone()[0], 2, "baslangicta IKI eski satir var")

beyin.gosterge_yaz(_b5, [_kalem("TP.DK.USD.S.YTL", _dun, 50.4694, "TL")])

esit(_b5.execute("SELECT COUNT(*) FROM gosterge WHERE kod='TP.DK.USD.S.YTL'"
                 " AND tarih > ?", (_bugun,)).fetchone()[0], 0,
     "yazilan kodun eski gelecek tarihli satiri SILINDI")
# DOKUNULMAYAN KOD KORUNUYOR: tum tabloyu silmek, ilgisiz bir seride
# beklenmedik kayip olurdu.
esit(_b5.execute("SELECT COUNT(*) FROM gosterge WHERE kod='UNRATE'"
                 " AND tarih > ?", (_bugun,)).fetchone()[0], 1,
     "cagrida gecmeyen kodun satirina DOKUNULMUYOR")
esit(_b5.execute("SELECT COUNT(*) FROM gosterge WHERE kod='TP.DK.USD.S.YTL'"
                 " AND tarih = ?", (_dun,)).fetchone()[0], 1,
     "mesru gecmis gozlem yazilmaya devam ediyor")


# ----------------------------------------------------------------------
# 4. MEKANIK KURAL -- cagri DONGUNUN ICINDE
# ----------------------------------------------------------------------
# "sinir_disi herhangi bir yerde cagriliyor mu" YETERSIZ bir soru:
# dongunun ONUNDE bir kez cagrilsa da gecerdi. Dogru soru, cagrinin
# gozlem dongusunun ICINDE olup olmadigi.
print("\n4. Mekanik kural -- cagri yeri")


def _dongudeki_cagrilar(fn):
    agac = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    donguler = [d for d in ast.walk(agac) if isinstance(d, ast.For)]
    icte, tumu = set(), set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Call):
            ad = ""
            if isinstance(d.func, ast.Attribute):
                ad = d.func.attr
            elif isinstance(d.func, ast.Name):
                ad = d.func.id
            if ad:
                tumu.add(ad)
    for dongu in donguler:
        for d in ast.walk(dongu):
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
                icte.add(d.func.attr)
            elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
                icte.add(d.func.id)
    return icte, tumu


_ic, _tum = _dongudeki_cagrilar(beyin.gosterge_yaz)
esit("sinir_disi" in _ic, True,
     "gosterge_yaz: sinir_disi gozlem DONGUSUNUN ICINDE cagriliyor")
_ic2, _tum2 = _dongudeki_cagrilar(denetim.aralik_denetimi)
esit("sinir_disi" in _ic2, True,
     "aralik_denetimi: sinir_disi seri DONGUSUNUN ICINDE cagriliyor")
# Denetim artik kendi karsilastirmasini yapmamali; tek olcut kalmali.
_kaynak_ad = inspect.getsource(denetim.aralik_denetimi)
esit("SERI_ARALIK.get" in _kaynak_ad, False,
     "aralik_denetimi kendi elle karsilastirmasini YAPMIYOR")

_vd = ast.parse((_KOK / "veri_dogrula.py").read_text(encoding="utf-8"))
_duzelt_fn = [d for d in _vd.body
              if isinstance(d, ast.FunctionDef) and d.name == "calistir"][0]
_cagrilar = {d.func.id for d in ast.walk(_duzelt_fn)
             if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
esit("gerilemeyi_ayikla" in _cagrilar, True,
     "calistir: duzeltmeler gerilemeyi_ayikla'dan GECIYOR")
esit("karantina_yaz" in _cagrilar, True,
     "calistir: karantina kaydi YAZILIYOR")

# DENETIM RAPORA BAGLI MI.
#
# `karantina_denetimi()`yi dogrudan cagirip dogru bulgu urettigini
# gormek YETMIYOR: rapor onu hic toplamiyorsa bulgu hicbir yere
# ulasmaz. Mutasyon tam buradan kacti.
_dn = ast.parse((_KOK / "denetim.py").read_text(encoding="utf-8"))
_dn_calistir = [d for d in _dn.body
                if isinstance(d, ast.FunctionDef) and d.name == "calistir"][0]
_dn_cagri = {d.func.id for d in ast.walk(_dn_calistir)
             if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
esit("karantina_denetimi" in _dn_cagri, True,
     "denetim.calistir: karantina bulgusu RAPORA toplaniyor")
esit("aralik_denetimi" in _dn_cagri, True,
     "denetim.calistir: aralik bulgusu RAPORA toplaniyor")

# UPDATE, suzgecten SONRA olmali -- sira tersine donerse koruma yok.
_satirlar = inspect.getsource(V.calistir).splitlines()
_i_suzgec = next(i for i, x in enumerate(_satirlar)
                 if "gerilemeyi_ayikla" in x)
_i_update = next(i for i, x in enumerate(_satirlar)
                 if "UPDATE gosterge" in x)
esit(_i_suzgec < _i_update, True,
     "suzgec UPDATE'ten ONCE kosuyor -- sira korumanin kendisi")

# ----------------------------------------------------------------------
# 5. GERILEME SUZGECI -- dort dal
# ----------------------------------------------------------------------
print("\n5. Gerileme suzgeci")

_bugun = [_sapma("TP.FE25.OKTG04", f"2026-{i:02d}-01", 29.0, -39.2)
          for i in range(1, 10)]
_kalan, _sebep = V.gerilemeyi_ayikla(_bugun)
esit(_kalan, [], "TOPLU yeniden yazma: hicbiri uygulanmiyor")
esit(len(_sebep), 1, "tek seri, tek sebep satiri")
dogru("48" not in _sebep[0][1] and "9" in _sebep[0][1],
      "sebep OLCULEN gozlem sayisini yaziyor")

# OLCULEN OLAYIN SEKLI, sabitten BAGIMSIZ.
#
# Asagidaki iki sinama esigi `S.GERILEME_ESIGI`den turetiyor; yani
# sabit 10000 yapilsa beklenti de onunla birlikte kayardi ve mutasyon
# sessizce kacardi (gercekten kacti). Bu iki satir sabiti DEGIL,
# olculen olayi capa aliyor: 48 gozlem reddedilmeli, mesru bir-iki
# gozlemlik revizyon gecmeli.
esit(S.gerileme_mi(48), True,
     "48 gozlem (bugunun olculen olayi) GERILEME sayiliyor")
esit(S.gerileme_mi(2), False,
     "iki gozlemlik revizyon gerileme SAYILMIYOR")
dogru(2 <= S.GERILEME_ESIGI <= 20,
      f"esik makul bantta ({S.GERILEME_ESIGI}) -- etkisizlestirilemez")

# Esik GERCEKTE elemeli: esik kadar gecer, bir fazlasi gecmez.
_esikte = [_sapma("UNRATE", f"2026-{i:02d}-01", 4.0, 4.2)
           for i in range(1, S.GERILEME_ESIGI + 1)]
_k, _s = V.gerilemeyi_ayikla(_esikte)
esit((len(_k), len(_s)), (S.GERILEME_ESIGI, 0),
     f"esik kadar ({S.GERILEME_ESIGI}) duzeltme UYGULANIYOR")
_asan = _esikte + [_sapma("UNRATE", "2026-09-01", 4.0, 4.2)]
_k, _s = V.gerilemeyi_ayikla(_asan)
esit((len(_k), len(_s)), (0, 1),
     "esigi BIR asan duzeltme kumesi tumden reddediliyor")

# Az sayida ama akla yatkin olmayan tek duzeltme de reddedilmeli.
_tek = [_sapma("TP.FE25.OKTG04", "2026-09-01", 28.71, -39.2)]
_k, _s = V.gerilemeyi_ayikla(_tek)
esit(_k, [], "TEK duzeltme de olsa yatkin olmayan deger yazilmiyor")
dogru(_s and "sinirinin disinda" in _s[0][1],
      "sebep, sinir ihlalini acikca yaziyor")

# Mesru revizyon GECMELI -- koruma her seyi durdurmuyor.
_mesru = [_sapma("UNRATE", "2026-09-01", 4.1, 4.3)]
_k, _s = V.gerilemeyi_ayikla(_mesru)
esit((len(_k), len(_s)), (1, 0), "mesru revizyon UYGULANIYOR")

# ===============================================================
# SEKIL OLCUTU -- SAYI TEK BASINA YETMIYOR.
#
# OLCULDU (2026-11-25), URETIMDE: `INDPRO` karantinaya alindi,
# sebep "18 gozlem birden yeniden yazilacakti (esik 8) -- revizyon
# degil, serinin anlami degismis". Olcum bunun YANLIS oldugunu
# gosterdi. Asagidaki iki dizi GERCEK: ilki depodaki yillik yuzde
# degisim, ikincisi ayni tarihler icin FRED'in guncel endeksinden
# yeniden hesaplanani.
#
# Turetilmis seride kaynaktaki TEK yillik revizyon BUTUN noktalari
# degistirir; yani sayi, turetilmis seride revizyonu bozulmadan
# ayirt edemez.
# ===============================================================
print("")
INDPRO_DEPO = [0.102, 0.579, 1.919, 1.189, 1.863, 1.759, 1.754, 1.163,
               0.973, 0.797, 0.686, 1.434, 1.710, 1.461, 1.250, 1.447,
               2.142, 2.150]
INDPRO_FRED = [-0.054, 0.281, 1.478, 0.700, 1.364, 1.246, 1.106, 0.536,
               0.033, 0.131, 0.235, 0.826, 1.211, 0.937, 0.920, 1.143,
               1.673, 1.659]
esit(len(INDPRO_DEPO), len(INDPRO_FRED), "gercek diziler ayni boyda")
dogru(len(INDPRO_DEPO) > S.GERILEME_ESIGI,
      f"olcum SAYI esigini asiyor ({len(INDPRO_DEPO)} > "
      f"{S.GERILEME_ESIGI}) -- yani eski olcut bunu REDDEDERDI")

_karar, _ac = S.sekil_korunuyor(INDPRO_DEPO, INDPRO_FRED)
esit(_karar, True, f"INDPRO: sekil KORUNUYOR ({_ac})")
esit(S.gerileme_mi(len(INDPRO_DEPO), INDPRO_DEPO, INDPRO_FRED), False,
     "INDPRO: sayi esigi asiyor ama GERILEME SAYILMIYOR")
# Eski cagri bicimi davranisini KORUYOR: sekil verilmezse sayi karar
# verir. Bu olmadan eski cagiranlar sessizce davranis degistirirdi.
esit(S.gerileme_mi(len(INDPRO_DEPO)), True,
     "sekil verilmezse davranis ESKISI gibi (sayi karar verir)")

# UC EKSEN, UCU DE YUK TASIYOR -- VE HER BIRI AYRI KANITLANIYOR.
#
# ILK YAZIMIM YETERSIZDI VE MUTASYON YAKALADI: "isaret tersinmesi"
# ve "20 kat genlik" durumlarinin ikisi de SEVIYE ekseninden de
# dusuyordu. Yani korelasyon ya da olcek ekseni kodtan cikarilsa
# sinamalar YESIL kaliyordu -- eksenlerin gerekliligi
# KANITLANMAMISTI.
#
# Her eksen icin artik YALNIZCA o eksenin yakaladigi bir durum var:
# oteki iki eksen o durumda GECIYOR ve bu ayrica dogrulaniyor.
_ORT = sum(INDPRO_DEPO) / len(INDPRO_DEPO)


def _eksen_durumu(ad, bozuk, beklenen_dusen):
    """Durumu uc eksende tek tek olcer ve YALNIZCA birinin
    dustugunu dogrular."""
    import statistics as _st
    sa, sb = _st.pstdev(INDPRO_DEPO), _st.pstdev(bozuk)
    kor = _st.correlation(INDPRO_DEPO, bozuk)
    oran = sb / sa
    olcek = max(_st.median([abs(x) for x in INDPRO_DEPO]), sa)
    fark = _st.median([abs(y - x) for x, y in zip(INDPRO_DEPO, bozuk)])
    dusen = set()
    if kor < S.SEKIL_KORELASYON:
        dusen.add("korelasyon")
    if not (S.SEKIL_OLCEK_ALT <= oran <= S.SEKIL_OLCEK_UST):
        dusen.add("olcek")
    if fark > olcek:
        dusen.add("seviye")
    esit(S.sekil_korunuyor(INDPRO_DEPO, bozuk)[0], False,
         f"{ad}: sekil BOZUK sayiliyor")
    esit(dusen, {beklenen_dusen},
         f"{ad}: YALNIZCA `{beklenen_dusen}` ekseni dusuyor "
         f"(kor {kor:.3f}, oran {oran:.3f}, fark {fark:.3f}/"
         f"{olcek:.3f})")


# 1. KORELASYON: ayni degerler, KARISIK sira. Olcek birebir ayni,
#    seviye farki kucuk; yalnizca sekil bozuldu.
_karisik = sorted(INDPRO_DEPO, reverse=True)
_eksen_durumu("ters sirali ayni degerler", _karisik, "korelasyon")

# 2. OLCEK: ayni sekil (korelasyon 1), ortalama ayni, genlik 1/5.
#    Seviye farki kucuk kaliyor -- yalnizca genlik bozuldu.
_sikisik = [_ORT + (x - _ORT) * 0.2 for x in INDPRO_DEPO]
_eksen_durumu("genlik bestebire sikistirilmis", _sikisik, "olcek")

# 3. SEVIYE: ayni sekil, ayni genlik, +100 kayma (yeniden
#    tabanlama). Korelasyon TAM 1 ve olcek TAM 1 -- yalnizca
#    seviye bozuldu.
_taban = [x + 100 for x in INDPRO_DEPO]
_eksen_durumu("yeniden tabanlama (+100)", _taban, "seviye")

# OLCULEMEYEN ILE BOZUK AYRI: None, False degil.
esit(S.sekil_korunuyor([1.0, 2.0], [1.0, 3.0])[0], None,
     "az nokta: OLCULEMEDI (None), bozuk DEGIL")
esit(S.sekil_korunuyor([4.0] * 9, [4.2] * 9)[0], None,
     "sabit seri: OLCULEMEDI (None)")
esit(S.gerileme_mi(9, [4.0] * 9, [4.2] * 9), True,
     "olculemeyen durumda SAYI olcutu gecerli kaliyor")

# TAM YOL: `gerilemeyi_ayikla` gercek INDPRO degisimini UYGULUYOR.
_indpro = [_sapma("INDPRO", f"2025-{i + 1:02d}-01",
                  INDPRO_DEPO[i], INDPRO_FRED[i])
           for i in range(len(INDPRO_DEPO))]
_k, _s = V.gerilemeyi_ayikla(_indpro)
esit((len(_k), len(_s)), (len(INDPRO_DEPO), 0),
     "INDPRO: 18 gozlemlik revizyonun TAMAMI uygulaniyor, red YOK")

# ANLAM DEGISMESI HALA REDDEDILIYOR -- TCMB TP.FE25 bicimi.
# Belgelenmis olcum: grup yillik degisim yerine aylik degisim
# dondurmeye basladi (31,88 -> 1,46; 28,71 -> -39,22).
_yillik = [31.88, 28.71, 26.40, 24.15, 22.90, 21.33, 19.87, 23.04,
           25.61, 27.19, 29.44, 30.12]
_aylik = [1.46, -39.22, 2.01, -1.33, 0.87, -2.14, 1.09, -0.76,
          2.33, -1.02, 0.44, 1.87]
esit(S.sekil_korunuyor(_yillik, _aylik)[0], False,
     "TCMB anlam degismesi: sekil BOZULDU")
_tcmb = [_sapma("TP.FE25.OKTG04", f"2026-{i + 1:02d}-01",
                _yillik[i], _aylik[i])
         for i in range(len(_yillik))]
_k, _s = V.gerilemeyi_ayikla(_tcmb)
esit(len(_k), 0, "TCMB: hicbiri uygulanmiyor")
dogru(_s and "sekil de bozuldu" in _s[0][1],
      "sebep sekil olcumunu de yaziyor")

# KABUL KARARI SESSIZ KALMAMALI.
#
# Esigi ASAN bir degisimi uyguluyoruz; bunu gunluge yazmamak,
# gercek bir bozulmayi tam bu kapidan gecirip kimsenin bakmamasina
# yol acar. Mutasyon bunu yakaladi: `print` susturuldugunda hicbir
# sinama kirmizi yanmiyordu.
import contextlib                                      # noqa: E402
import io as _io                                        # noqa: E402

_yakala = _io.StringIO()
with contextlib.redirect_stdout(_yakala):
    V.gerilemeyi_ayikla(_indpro)
_cikti = _yakala.getvalue()
dogru("INDPRO" in _cikti and "SEKIL KORUNUYOR" in _cikti,
      "esigi asan KABUL karari gunluge yaziliyor")
dogru("korelasyon" in _cikti,
      "kabul satiri OLCUMU de tasiyor (hangi gerekceyle gecti)")
# Esigin ALTINDAKI sessiz yol degismedi: gurultu uretmiyoruz.
_yakala2 = _io.StringIO()
with contextlib.redirect_stdout(_yakala2):
    V.gerilemeyi_ayikla([_sapma("UNRATE", "2026-09-01", 4.1, 4.3)])
esit(_yakala2.getvalue().strip(), "",
     "esigin ALTINDAKI revizyon sessiz kaliyor -- gurultu yok")

# SABITLER ETKISIZLESTIRILEMEZ BANTTA.
dogru(0.5 <= S.SEKIL_KORELASYON <= 0.99,
      f"korelasyon esigi makul bantta ({S.SEKIL_KORELASYON})")
dogru(S.SEKIL_OLCEK_ALT < 1.0 < S.SEKIL_OLCEK_UST,
      "olcek bandi 1,0'i iceriyor -- degismeyen genlik gecmeli")
dogru(S.SEKIL_EN_AZ_NOKTA >= 4,
      f"sekil olcumu en az dort nokta istiyor ({S.SEKIL_EN_AZ_NOKTA})")


# Elle zorlama yolu acik kalmali (CPIAUCSL turu gercek birim gocu).
_k, _s = V.gerilemeyi_ayikla(_bugun, zorla=True)
esit((len(_k), len(_s)), (len(_bugun), 0),
     "--gerilemeyi-yok-say suzgeci atliyor")
esit("gerilemeyi_yok_say" in inspect.signature(V.calistir).parameters, True,
     "zorlama yolu CLI'dan erisilebilir")

# ----------------------------------------------------------------------
# 6. KARANTINA KAYDI -- gorunurluk
# ----------------------------------------------------------------------
print("\n6. Karantina kaydi")

_uretim = _URETIM_KARANTINA
_uretim_once = (_uretim.read_bytes() if _uretim.is_file() else None)
esit(V.KARANTINA, _URETIM_KARANTINA,
     "yol TEK YERDE -- yazan, okuyan ve raporlayan ayni sabiti kullaniyor")
esit(denetim.seri_sinirlari.KARANTINA, S.KARANTINA,  # ayni nesne
     "denetim de ayni sabiti okuyor")

with tempfile.TemporaryDirectory() as _gecici:
    S.KARANTINA = pathlib.Path(_gecici) / "k.json"
    S.karantina_yaz([("TP.X", "TP.X: sebep")])
    esit(S.KARANTINA.is_file(), True, "dolu kayit yaziliyor")
    _d = json.loads(S.KARANTINA.read_text(encoding="utf-8"))
    esit(_d["sebepler"], ["TP.X: sebep"], "sebepler kayitta duruyor")
    esit(_d["seriler"], ["TP.X"], "seri KODU da kayitta -- metinden ayri")
    dogru(_d.get("an"), "dolu kayitta zaman damgasi var")
    esit(S.karantinadakiler(), frozenset({"TP.X"}),
         "karantinadaki seri okunabiliyor")

    # AYNI SEBEP -> DOSYAYA DOKUNULMUYOR.
    #
    # Ilk surumde `an` her kosuda yenileniyordu: haber hatti on
    # dakikada bir kostugu icin dosya gunde 144 kez, YALNIZCA zaman
    # damgasi yuzunden commit'e giriyordu. Daha onemlisi `an`in
    # anlami yanlisti -- "ne zaman oldu" gibi okunuyor, "en son ne
    # zaman goruldu" demek oluyordu.
    _ISARET = "1970-01-01T00:00:00Z"
    _d2 = json.loads(S.KARANTINA.read_text(encoding="utf-8"))
    _d2["an"] = _ISARET
    S.KARANTINA.write_text(json.dumps(_d2), encoding="utf-8")
    S.karantina_yaz([("TP.X", "TP.X: sebep")])
    esit(json.loads(S.KARANTINA.read_text(encoding="utf-8")).get("an"),
         _ISARET,
         "ayni sebep kumesi dosyaya DOKUNMUYOR -- `an` baslangic ani")
    S.karantina_yaz([("TP.X", "TP.X: BASKA sebep")])
    dogru(json.loads(S.KARANTINA.read_text(encoding="utf-8")).get("an")
          != _ISARET,
          "sebep degisince damga yenileniyor")
    S.karantina_yaz([("TP.X", "TP.X: sebep")])

    # KARANTINADAKI SERIDEN YENI GOZLEM DE ALINMIYOR.
    #
    # `veri_dogrula` yalnizca depoda ZATEN olan tarihleri kaynakla
    # karsilastirabiliyor; yeni bir tarihte karsilastiracak sey yok.
    # Siniri gecen ama YANLIS bir deger (bozuk kaynak %23,39
    # donduruyor, dogrusu %28,71 civari) bu yuzden hicbir kontrole
    # takilmadan yayimlanirdi.
    _b3 = sqlite3.connect(":memory:")
    _b3.executescript(beyin.SEMA)
    _red3: list = []
    _n3 = beyin.gosterge_yaz(_b3, [
        _kalem("TP.X", "2026-10-01", 23.39),
        _kalem("TP.TUKFIY2025.GENEL", "2026-10-01", 29.0),
    ], _red3)
    esit(_n3, 1, "karantinada OLMAYAN seri yazilmaya devam ediyor")
    esit([r[0] for r in _red3], ["TP.X"],
         "karantinadaki serinin siniri GECEN degeri de reddediliyor")
    dogru("karantina" in _red3[0][3], "sebep karantinayi soyluyor")

    # SILMIYOR: geri yazma listesi `[ -e "$y" ]` ile suzuluyor, silinen
    # dosya hic gonderilmez ve depodaki eski karantina sonsuza kadar
    # uyari uretirdi.
    S.karantina_yaz([])
    esit(S.KARANTINA.is_file(), True,
         "bos kayit da YAZILIYOR -- dosya silinmiyor")
    esit(S.karantinadakiler(), frozenset(),
         "kaynak duzelince seri geri ACILIYOR")
    _bos1 = S.KARANTINA.read_bytes()
    S.karantina_yaz([])
    esit(S.KARANTINA.read_bytes(), _bos1,
         "bos kayit her kosuda AYNI -- commit gurultusu yok")
    esit(json.loads(_bos1.decode("utf-8")).get("an"), None,
         "bos kayitta zaman damgasi YOK")

    # Denetim kaydi okuyup raporluyor mu?
    S.KARANTINA = pathlib.Path(_gecici) / "yok.json"
    esit(denetim.karantina_denetimi(), [], "kayit yoksa bulgu yok")
    S.KARANTINA = pathlib.Path(_gecici) / "k2.json"
    S.KARANTINA.write_text(json.dumps({"sebepler": []}), encoding="utf-8")
    esit(denetim.karantina_denetimi(), [],
         "BOS kayit bulgu uretmiyor -- kaynak duzelince uyari kalkiyor")
    S.KARANTINA.write_text(
        json.dumps({"an": "2026-11-01T00:00:00Z",
                    "seriler": ["TP.X"],
                    "sebepler": ["TP.X: 48 gozlem"]}), encoding="utf-8")
    _bulgu = denetim.karantina_denetimi()
    esit(len(_bulgu), 1, "dolu kayit BIR bulgu uretiyor")
    esit(_bulgu[0].agirlik, "uyari",
         "karantina UYARI -- tek bozuk seri butun siteyi indirmiyor")
    dogru("TP.X" in _bulgu[0].mesaj, "bulgu seriyi adiyla yaziyor")
    S.KARANTINA.write_text("{bozuk", encoding="utf-8")
    _bozuk = denetim.karantina_denetimi()
    esit((len(_bozuk), _bozuk[0].agirlik), (1, "uyari"),
         "okunamayan kayit da sessiz kalmiyor")

S.KARANTINA = _URETIM_KARANTINA
S.karantinadakiler.cache_clear()
_uretim_sonra = (_uretim.read_bytes() if _uretim.is_file() else None)
esit(_uretim_sonra, _uretim_once,
     "SINAMA URETIM KAYDINA DOKUNMADI")

# ----------------------------------------------------------------------
# 7. KAYIT GERI YAZILIYOR MU
# ----------------------------------------------------------------------
# Geri yazilmayan kayit yok olur: kosucu sonunce dosya gider ve
# karantina her kosuda sifirdan baslar, yani uyari hic gorunmez.
print("\n7. Geri yazma")

_akis = (_KOK.parent / ".github" / "workflows" / "otomasyon.yml"
         ).read_text(encoding="utf-8")
_goreli = str(S.KARANTINA.relative_to(_KOK.parent)).replace("\\", "/")
esit(_goreli, "haber_botu/kaynak/seri_karantina.json",
     "kayit yolu beklenen yerde")
dogru(_goreli in _akis,
      "karantina kaydi GERI YAZMA listesinde -- yoksa kosu sonunda yok olur")

# ----------------------------------------------------------------------
# 8. ATILLIK DENETIMI -- gercek depo
# ----------------------------------------------------------------------
# Yukaridaki sinamalarin hepsi sahte veriyle kosuyor; bu bolum kuralin
# GERCEK depoda da isledigini gosteriyor.
#
# ONEMLI: "bugun hicbir gozlem sinir disi degil" diye SORMUYOR. Oyle
# sormustum ve kosu 2455'te tam o yuzden kirmizi dondu: depo zehirliyse
# sinama adimi dusuyor, sinama adimi URETIMDEN ONCE kostugu icin de hat
# karantinaya alip kendini onaracak adima HIC gelemiyor. Yani korumanin
# kendisi, kapatmasi gereken kusuru tekrar uretiyordu -- bu depoda
# kapiyi ureticinin onune koymak tekrarlayan bir hata.
#
# Veri durumunu `denetim.py` zaten raporluyor ve YAYINI durduruyor;
# dogru yer orasi. Burada sorulan soru icerikten bagimsiz: denetimin
# verdigi karar, olcutun verdigi kararla AYNI MI?
print(chr(10) + "8. Gercek depo")

try:
    import takvim  # noqa: E402
    with beyin.baglan() as _db:
        _bulgular = denetim.aralik_denetimi(_db)
        _say = _db.execute("SELECT COUNT(DISTINCT kod) FROM gosterge"
                           ).fetchone()[0]
        _seriler = {s[0] for s in takvim.SERILER + takvim.YERLI_SERILER}
        _beklenen = {}
        for _k in sorted(_seriler):
            _r = _db.execute(
                "SELECT deger, birim FROM gosterge WHERE kod=?"
                " ORDER BY tarih DESC LIMIT 1", (_k,)).fetchone()
            if not _r:
                continue
            _s = S.sinir_disi(_k, _r[0], _r[1] or "")
            if _s:
                _beklenen[_k] = _s
    esit({x.kod: x.mesaj for x in _bulgular}, _beklenen,
         "denetimin karari OLCUTUN karariyla birebir ayni (gercek depo)")
    dogru(_say > 20, f"denetim bos donmedi: depoda {_say} seri var")
    dogru(len(_seriler) > 10, f"takvimde {len(_seriler)} seri tanimli")
    # Durumu bildir, ama karara BAGLAMA.
    print(f"  bilgi  gercek depoda {len(_beklenen)} seri sinir disi"
          + (f": {sorted(_beklenen)}" if _beklenen else ""))
except sqlite3.Error as _e:
    print(f"  ATLANDI  gercek depo okunamadi: {_e}")


# ----------------------------------------------------------------------
# 8b. IYILESME KARANTINAYI KALDIRMALI
# ----------------------------------------------------------------------
# Temizleme ilk yazimda `if duzelt and sapan:` blogunun ICINDEydi ve
# bu EN IYI DURUMU disarida birakiyordu: kaynak tamamen duzelince
# sapma SIFIR olur, blok hic calismaz, karantina SONSUZA KADAR acik
# kalir -- ve karantinadaki seriden yeni gozlem de alinmadigi icin
# seri kalici olarak donar.
#
# Olculdu (2026-11-03): TCMB seriyi yeniden tabanlandirdi,
# `veri_dogrula` 3091 gozlemde 'sapan 0' dedi, ama karantina kaydi
# 2 Kasim'dan beri ayni duruyordu ve 2026-10 cekirdek enflasyonu
# depoya giremiyordu. Olay bayragi, DURUM sorusuna cevap vermiyordu.
print(chr(10) + '8b. Iyilesme karantinayi kaldiriyor mu')

_ck = ast.parse((_KOK / 'veri_dogrula.py').read_text(encoding='utf-8'))
_cf = [d for d in _ck.body
       if isinstance(d, ast.FunctionDef) and d.name == 'calistir'][0]


def _kosullar(dugum):
    """`karantina_yaz` cagrisini saran `if` kosullarinin metni."""
    yol = []

    def gez(d, zincir):
        if isinstance(d, ast.Call) and getattr(d.func, 'id', '') == 'karantina_yaz':
            yol.append(list(zincir))
        for alt in ast.iter_child_nodes(d):
            if isinstance(d, ast.If) and alt in d.body:
                gez(alt, zincir + [ast.unparse(d.test)])
            else:
                gez(alt, zincir)
    gez(dugum, [])
    return yol


_yollar = _kosullar(_cf)
dogru(_yollar, 'calistir icinde karantina_yaz cagrisi var')
# HICBIR CAGRI `sapan` KOSULUNA BAGLI OLMAMALI: sapma yokken de
# karar verilmeli.
_sapana_bagli = [y for y in _yollar if any('sapan' in k for k in y)]
esit(_sapana_bagli, [],
     'karantina karari `sapan` kosuluna BAGLI DEGIL')

# DAVRANIS: sapma yokken karantina BOSALIYOR.
_uk = S.KARANTINA
with tempfile.TemporaryDirectory() as _g5:
    S.KARANTINA = pathlib.Path(_g5) / 'k.json'
    S.karantina_yaz([('TP.X', 'TP.X: sebep')])
    esit(S.karantinadakiler(), frozenset({'TP.X'}), 'once karantinada')
    # `gerilemeyi_ayikla([])` bos liste doner -> `karantina_yaz([])`
    _kalan, _ger = V.gerilemeyi_ayikla([])
    esit((_kalan, _ger), ([], []), 'sapma yokken gerileme de yok')
    S.karantina_yaz(_ger)
    esit(S.karantinadakiler(), frozenset(),
         'sapma yokken karantina BOSALIYOR')
S.KARANTINA = _uk
S.karantinadakiler.cache_clear()
# ----------------------------------------------------------------------
# 9. TEK YAZMA YOLU -- ucuncu bir atlama imkansiz olmali
# ----------------------------------------------------------------------
# Suzgec `beyin.gosterge_yaz` icinde. Ilk yazildiginda IKI modul
# (`kaynak/bundesbank.py`, `kaynak/ecb_kur.py`) kendi `INSERT`ini
# kullaniyordu, yani suzgeci atliyorlardi -- olculdu, sayildi, ikisi de
# ayni yola alindi. Bu bolum ucuncusunun eklenmesini engelliyor.
print(chr(10) + "9. Tek yazma yolu")

_MUAF = {
    # Suzgecin KENDI yazma noktasi.
    "haber_botu/beyin.py": "gosterge_yaz",
    # Duzeltme yolu: `gerilemeyi_ayikla`dan GECEN satirlari yaziyor.
    # 5. bolum bunu davranis olarak, 4. bolum sirayi AST olarak
    # olcuyor.
    "haber_botu/veri_dogrula.py": "calistir",
}
_YAZMA = ("INSERT INTO gosterge", "INSERT OR IGNORE INTO gosterge",
          "INSERT OR REPLACE INTO gosterge", "UPDATE gosterge",
          "REPLACE INTO gosterge", "DELETE FROM gosterge")

_kacak = []
for _p in sorted((_KOK.parent).rglob("*.py")):
    _g = str(_p.relative_to(_KOK.parent)).replace("\\", "/")
    if "/test_" in _g or _g.startswith("test_") or "__pycache__" in _g:
        continue
    try:
        _ic = _p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        continue
    if any(x in _ic for x in _YAZMA) and _g not in _MUAF:
        _kacak.append(_g)
esit(_kacak, [],
     "gosterge tablosuna HAM SQL ile yazan muaf olmayan modul yok")
dogru(len(_MUAF) == 2, "muafiyet listesi iki gerekceli girdiyle sinirli")

# Iki eski yazici gercekten suzgecten geciyor mu -- DAVRANIS.
import importlib  # noqa: E402
for _mod, _kod, _bozuk, _bozuk2, _saglam in (
        ("bundesbank", "BBK_DE10Y", 332.57, 90.0, 2.41),
        ("ecb_kur", "ECB_EURUSD", 108.0, 4.5, 1.08)):
    _m = importlib.import_module(_mod)
    _bb = sqlite3.connect(":memory:")
    _bb.executescript(beyin.SEMA)
    esit(_m.depoya_yaz(_bb, [("2026-10-01", _bozuk)]), 0,
         f"{_mod}: birim/olcek hatasi ({_bozuk}) depoya GIRMIYOR")
    # Birim sinirinin ICINDE ama SERI sinirinin disinda: seriye ozgu
    # sinirin kendisi olculuyor. Bu satir olmadan mutasyon kaciyordu.
    esit(_m.depoya_yaz(_bb, [("2026-10-03", _bozuk2)]), 0,
         f"{_mod}: birim sinirini GECEN ama seri sinirini asan "
         f"({_bozuk2}) deger de girmiyor")
    esit(_m.depoya_yaz(_bb, [("2026-10-02", _saglam)]), 1,
         f"{_mod}: makul deger ({_saglam}) yazilmaya devam ediyor")
    esit(_bb.execute("SELECT COUNT(*) FROM gosterge WHERE kod=?",
                     (_kod,)).fetchone()[0], 1,
         f"{_mod}: depoda yalnizca makul gozlem var")
    esit(_m.depoya_yaz(_bb, []), 0, f"{_mod}: bos liste sorun degil")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
