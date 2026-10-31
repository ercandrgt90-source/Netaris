# -*- coding: utf-8 -*-
"""BILDIRIM PENCERESI -- OLAY BIR KEZ OLUR, PENCERE SURER.

BU DOSYA NEDEN VAR
------------------
`uret_bilanco.donem_acik` bilanco hattinin ONUNDEKI tek kapi ve
bugune kadar HICBIR davranis sinamasi yoktu. Yalnizca is akisindaki
ADIM SIRASI sinaniyordu (`test_calistir`, `test_isakisi`); kapinin
kendisi -- hangi gun acik, hangi gun kapali -- hic olculmemisti.
Bir kerelik olma kusuru tam bu bosluktan gemiye bindi.

OLCULDU (2026-10-30/31, kosu #60-#61)
-------------------------------------
    #60  13:12  nobetci bayragi KALKTI
                -> veri adimi kostu, `sektor_ozet.json` 20 sirkette
                   `2026-09-30` gordu
                -> kosu sonunda `--kapat` bayragi INDIRDI
    #61  01:23  "10. ay bildirim ayi degil (bildirim aylari:
                 [3, 5, 8, 11]) ve nobetci yeni ceyrek gormedi"
                -> veri adimi ATLANDI
                -> sayfa adimi tam o 20 sirkete Q3 sayfasi yazdi

Yani ozet 14:00'teki fotografta DONDU. Sayfa adimi ancak OZETTE
`2026-09-30` yazan sirkete Q3 sayfasi yaziyor; ozeti tazeleyen adim
ise kapali. Sonraki her kosu SIFIR yeni Q3 sayfasi yazacakti ve
hepsi YESIL donecekti -- hicbir yerde kirmizi gorunmeden, 1 Kasim'a
kadar.

AYRIM: OLAY MI, DURUM MU
------------------------
Nobetci bayragi bir OLAY tasiyor: "kaynakta YENI bir ceyrek
GORDUM". Kosu sonunda inmesi DOGRU -- olay islendi. Yanlis olan,
hattin "bu donemde yapilacak IS KALDI MI" sorusunu ayni bayraga
sormasiydi. Iki ayri soru, tek bir bite baglanmisti.

Bu depo ayni sinifi daha once de yasadi: bkz. gun kaydiran korumanin
saat bombasini gormemesi. Bir kez gecen kapi, surekli bir durumun
yerine kullanilamaz.

PENCERE NEDEN OLCUM, TAHMIN DEGIL
---------------------------------
Pencerenin capasi `BILDIRIM_AYLARI` gibi bir takvim tahmini degil;
nobetcinin KAYNAKTA GORDUGU en yeni donem bitisi (`son_bitis`). O
deger nobet defterinde zaten yazili, yani pencere BEDAVA -- tek bir
ek ag istegi yok.

BU DOSYANIN IDDIA ETMEDIGI SEY
------------------------------
Pencerenin KAC GUN oldugu burada SABITLENMIYOR. Sayiyi koddan
okuyup "kod ne diyorsa o" demek, korudugu seyden beklentisini alan
bir sinama olurdu -- bu depoda dokuz mutasyon tam boyle kacti.
Onun yerine DAVRANIS tutuluyor: donem bitiminden otuz gun sonra
ACIK (konsolide olmayan son tarih), yuz gun sonra KAPALI. Pencere
makul araliktaysa iki iddia da gecer; kaldirilirsa ya da anlamsiz
bir degere cekilirse biri DUSER.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_ag                                        # noqa: E402
import uret_bilanco as U                                 # noqa: E402

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


def dogru(aciklama: str, kosul: bool) -> None:
    esit(bool(kosul), True, aciklama)


class Nobetci:
    """Nobetci yerine gecen en kucuk nesne -- AG YOK, DOSYA YOK.

    Gercek nobetciyi kullanmak, sinamayi depodaki nobet defterinin
    O ANKI icerigine baglardi: dosya guncellenince sinama sessizce
    baska bir seyi olcmeye baslardi.
    """

    def __init__(self, acik: bool, son_bitis):
        self._acik = acik
        self._son_bitis = son_bitis
        self.soruldu = 0

    def donem_acildi_mi(self) -> bool:
        return self._acik

    def nobet_oku(self) -> dict:
        self.soruldu += 1
        return {"son_bitis": self._son_bitis}


class Patlayan(Nobetci):
    """Nobetci cokerse hat eski davranisa DUSMELI, kosu olmemeli."""

    def donem_acildi_mi(self) -> bool:
        raise RuntimeError("nobet defteri okunamadi")

    def nobet_oku(self) -> dict:
        raise RuntimeError("nobet defteri okunamadi")


# =====================================================================
print("")
print("1. KOSU #61'IN TA KENDISI -- GERILEME SINAMASI")
# =====================================================================
#
# Tarih, bayrak durumu ve olculen donem uretimden AYNEN alindi.
# Bu iddia duserse hat yeniden ekim boyunca sessizce donar.
_61 = Nobetci(acik=False, son_bitis="2026-09-30")
_acik, _nicin = U.donem_acik(bugun=dt.date(2026, 10, 31), nobetci=_61)
dogru("31 Ekim, bayrak INMIS, Q3 olculmus -> hat ACIK", _acik)
dogru("gerekce pencereyi ADIYLA soyluyor",
      "pencere" in _nicin.lower())
dogru("gerekce HANGI donemin penceresi oldugunu soyluyor",
      "2026-09-30" in _nicin)

# PENCERE GERCEKTEN CALISTI MI, YOKSA BASKA BIR KAPI MI ACTI?
#
# Ayni gun `BILDIRIM_AYLARI` kapali (10. ay listede yok) ve bayrak
# inmis. Ama bunu VARSAYMAK yetmez: bir gun listeye 10 eklenirse bu
# bolum pencereyi olcmeyi BIRAKIR ve sessizce yesil kalir.
dogru("KONTROL: o gun takvim kapisi gercekten KAPALI",
      10 not in U.BILDIRIM_AYLARI)
dogru("KONTROL: o gun bayrak kapisi gercekten KAPALI",
      not _61.donem_acildi_mi())

# =====================================================================
print("")
print("2. PENCERE SURUYOR -- BIR KOSULUK DEGIL")
# =====================================================================
#
# Kusurun ozu "bir kez acilip kapanmasi"ydi. Ayni girdiyle ARKA ARKAYA
# sorulunca cevap DEGISMEMELI; degisirse kapi yine olay gibi davraniyor.
_s = Nobetci(acik=False, son_bitis="2026-09-30")
_cevaplar = [U.donem_acik(bugun=dt.date(2026, 10, 31), nobetci=_s)[0]
             for _ in range(5)]
esit(_cevaplar, [True] * 5, "aralikli bes sorguda hat ACIK KALIYOR")
dogru("KONTROL: her sorguda nobet defteri gercekten okundu",
      _s.soruldu == 5)

# Donem bitiminden sonraki gunler boyunca ACIK.
for _gun in (1, 15, 30, 45):
    _t = dt.date(2026, 9, 30) + dt.timedelta(days=_gun)
    dogru(f"donem bitiminden {_gun} gun sonra ACIK",
          U.donem_acik(bugun=_t, nobetci=Nobetci(False, "2026-09-30"))[0])

# =====================================================================
print("")
print("3. PENCERE KAPANIYOR -- SONSUZ ACIK BIR KAPI DA KUSURDUR")
# =====================================================================
#
# Kapanmayan kapi her kosuda 333 sirketi bosuna cektirirdi. Capa
# donemden UZAK bir gun secildi (100 gun): araliktan kesin disi.
# Bos bir ay seciliyor ki TAKVIM kapisi pencereyi gizlemesin.
_uzak = Nobetci(acik=False, son_bitis="2026-09-30")
_acik2, _nicin2 = U.donem_acik(bugun=dt.date(2027, 1, 8), nobetci=_uzak)
dogru("donem bitiminden 100 gun sonra KAPALI", not _acik2)
dogru("KONTROL: o gun takvim kapisi da kapali",
      1 not in U.BILDIRIM_AYLARI)
dogru("kapali gerekce penceresinin DISINDA oldugunu soyluyor",
      "pencere" in _nicin2.lower() and "DISINDA" in _nicin2)

# =====================================================================
print("")
print("4. GELECEKTE BITEN DONEM PENCEREYI ACMIYOR")
# =====================================================================
#
# Kaynak gelecekte biten kolonlar da yaziyor (ARENA icin "Q1 2027"
# olculdu). Negatif gun sayisi pencereyi acsaydi hat YIL BOYU acik
# kalirdi -- ve bu, kapanmayan kapinin en sinsi bicimi olurdu:
# sebebi bir baska sirketin takvimi oldugu icin gunlukte goze
# carpmazdi.
dogru("gelecekte biten donem hatti ACMIYOR",
      not U.donem_acik(bugun=dt.date(2026, 10, 31),
                       nobetci=Nobetci(False, "2027-03-31"))[0])

# =====================================================================
print("")
print("5. BILINMEYEN 'ACIK' SAYILMIYOR")
# =====================================================================
for _deger, _ad in ((None, "son_bitis yok"),
                    ("", "son_bitis bos"),
                    ("abc", "son_bitis cozulemiyor"),
                    (20260930, "son_bitis sayi (eski bicim)"),
                    ([2026, 3], "son_bitis liste (eski bicim)")):
    dogru(f"{_ad} -> pencere ACMIYOR",
          not U.donem_acik(bugun=dt.date(2026, 10, 31),
                           nobetci=Nobetci(False, _deger))[0])

# =====================================================================
print("")
print("6. VAR OLAN IKI KAPI BOZULMADI")
# =====================================================================
#
# Pencere EKLENDI; eskisinin yerine gecmedi. Her uc kapi da kendi
# basina acabilmeli.
dogru("bayrak kapisi: olay pencere kapaliyken de ACIYOR",
      U.donem_acik(bugun=dt.date(2026, 12, 20),
                   nobetci=Nobetci(True, "2026-09-30"))[0])
dogru("bayrak gerekcesi nobetciyi adiyla soyluyor",
      "nobetci" in U.donem_acik(bugun=dt.date(2026, 12, 20),
                                nobetci=Nobetci(True, "2026-09-30"))[1])

for _ay in sorted(U.BILDIRIM_AYLARI):
    # Takvim kapisi YALNIZ BASINA acmali: bayrak inmis, pencere yok.
    dogru(f"takvim kapisi: {_ay}. ay tek basina ACIYOR",
          U.donem_acik(bugun=dt.date(2026, _ay, 15),
                       nobetci=Nobetci(False, None))[0])

# NOBETCI YOKSA/COKERSE davranis eskisi gibi -- yalnizca takvim.
dogru("nobetci cokse bile takvim ayinda hat ACIK",
      U.donem_acik(bugun=dt.date(2026, 11, 15),
                   nobetci=Patlayan(True, "2026-09-30"))[0])
dogru("nobetci cokse bos ayda hat KAPALI",
      not U.donem_acik(bugun=dt.date(2026, 12, 20),
                       nobetci=Patlayan(True, "2026-09-30"))[0])

# =====================================================================
print("")
print("7. PENCERE SPK ARA DONEM SINIRLARINI KAPSIYOR")
# =====================================================================
#
# Kac gun oldugu KODDAN OKUNMUYOR -- davranisla tutuluyor. Capalar
# mevzuattan: konsolide olmayan ara donem 30 gun, konsolide 40 gun.
# Pencere ikisini de kapsamazsa gecikmeli bildiren sirketler hic
# yayimlanmaz; 90 gunu ascak kadar genisse bir sonraki donemin
# penceresiyle CAKISIR.
_q3 = dt.date(2026, 9, 30)


def _pencere_gunu(gun: int) -> bool:
    """O gun pencere mi acti? Diger iki kapi KAPALI secildi."""
    _t = _q3 + dt.timedelta(days=gun)
    if _t.month in U.BILDIRIM_AYLARI:
        raise AssertionError(f"capa {gun}. gun takvim ayina dustu "
                             f"({_t}) -- iddia pencereyi olcmuyor")
    return U.donem_acik(bugun=_t, nobetci=Nobetci(False, "2026-09-30"))[0]


dogru("30. gun (konsolide olmayan son tarih) ACIK", _pencere_gunu(30))
dogru("100. gun KAPALI", not _pencere_gunu(100))
# Pencere bir sonraki donemin penceresine TASMIYOR: bir sonraki
# ceyrek 31 Aralik'ta bitiyor, yani 92. gunde.
dogru("pencere bir sonraki donem bitisine TASMIYOR",
      bilanco_ag.BILDIRIM_PENCERESI_GUN < 92)

# =====================================================================
print("")
print("8. ETKISIZLIK KONTROLU -- IDDIALAR GERCEKTEN ELIYOR")
# =====================================================================
#
# Yukaridaki iddialarin hepsi `pencere_acik` HER ZAMAN False donerse
# de, HER ZAMAN True donerse de gecmemeli. Ikisi burada dogrudan
# olculuyor: gecen bir sinama, sinananin dogru oldugunu gostermez.
_asil = bilanco_ag.pencere_acik
try:
    bilanco_ag.pencere_acik = lambda sb, bugun: (False, 0)
    dogru("KONTROL: pencere hep KAPALI olsa 2. bolum duserdi",
          not U.donem_acik(bugun=dt.date(2026, 10, 31),
                           nobetci=Nobetci(False, "2026-09-30"))[0])
    bilanco_ag.pencere_acik = lambda sb, bugun: (True, 0)
    dogru("KONTROL: pencere hep ACIK olsa 3. bolum duserdi",
          U.donem_acik(bugun=dt.date(2027, 1, 8),
                       nobetci=Nobetci(False, "2026-09-30"))[0])
finally:
    bilanco_ag.pencere_acik = _asil

dogru("KONTROL: asil pencere geri konuldu",
      bilanco_ag.pencere_acik is _asil)

# =====================================================================
print("")
print("9. KAYNAGA NAZIK DAVRANMA -- OLCULEN DEGER KULLANILIYOR MU")
# =====================================================================
#
# OLCULDU (2026-10-31, kosu #61): sayfa adimi 20 sayfa yazdi, sonra
# kaynak 429 vermeye basladi; gunluge "istek araligi 2.0 -> 4.0 ->
# 8.0 sn" dustu ve "KAYNAK KAPANDI -- 8 ardisik red" geldi. Kalan
# 131 sirket "eksik: ..." diye atlandi ve bolum gocu ayni kosuda
# 128 sayfanin HICBIRINI tasiyamadi. AYNI KOSUDA veri adimi 333
# sirketi sonuna kadar cekti.
#
# Fark: veri adimi istekler arasinda `ARA_SN` bekliyordu, oteki iki
# adim HIC BEKLEMIYORDU. `_yavasla()` degeri buyutuyordu ve bekleyen
# kimse olmadigi icin uyarlama ETKISIZDI -- gunluk tedbirin
# alindigini soyluyor, alinan tedbir yok.
#
# BU BOLUM METNE DEGIL DAVRANISA BAKIYOR. "Yorum iddia eder, akis
# uygulamaz" bu depoda olculdu.
_uyku = []
_asil_uyu = bilanco_ag._uyu
_asil_ara = bilanco_ag.ARA_SN
_asil_kapandi = bilanco_ag.KAPANDI
try:
    bilanco_ag._uyu = lambda s: _uyku.append(s)

    bilanco_ag.KAPANDI = False
    bilanco_ag.ARA_SN = bilanco_ag.TABAN_ARA_SN
    _s1 = bilanco_ag.ara_ver()
    esit(_s1, bilanco_ag.TABAN_ARA_SN, "normalde taban aralik kadar BEKLIYOR")
    esit(_uyku, [bilanco_ag.TABAN_ARA_SN], "bekleme GERCEKTEN yapildi")
    dogru("bekleme sifir DEGIL", _s1 > 0)

    # UYARLAMA ETKILI MI: kaynak "yavasla" dedikten sonraki bekleme
    # BUYUMELI. Deger basta bir kez yakalanmis olsaydi bu iddia
    # duserdi -- kusurun ta kendisi buydu.
    _uyku.clear()
    bilanco_ag._yavasla()
    _s2 = bilanco_ag.ara_ver()
    dogru("kaynak yavaslatinca bekleme BUYUYOR", _s2 > _s1)
    esit(_uyku, [_s2], "buyuyen sure gercekten beklendi")
    dogru("KONTROL: yavaslatma araligi gercekten buyuttu",
          bilanco_ag.ARA_SN > bilanco_ag.TABAN_ARA_SN)

    # KAYNAK KAPANDIYSA BEKLEMEK YOK: istek atilmiyor, beklenecek
    # bir sey de yok. Beklemek kalan sirketler icin dakikalari
    # hicbir seye harcardi.
    _uyku.clear()
    bilanco_ag.KAPANDI = True
    esit(bilanco_ag.ara_ver(), 0.0, "kaynak KAPALIYKEN beklemiyor")
    esit(_uyku, [], "kapaliyken hic uyku cagrisi YOK")
finally:
    bilanco_ag._uyu = _asil_uyu
    bilanco_ag.ARA_SN = _asil_ara
    bilanco_ag.KAPANDI = _asil_kapandi

dogru("KONTROL: aralik geri konuldu", bilanco_ag.ARA_SN == _asil_ara)

# =====================================================================
print("")
print("10. KURAL: KAYNAGA GIDEN HER DONGU ARALIK BEKLEMELI")
# =====================================================================
#
# Bir hatayi duzeltmek yetmiyor; ayni hatanin yeni bir dongude
# TEKRAR olusmasini engelleyecek kural gerekiyor. Beklemeyi her
# donguye elle yazmak, bir sonraki dongude yine unutulmasi demekti
# -- ve bu depoda tam olarak boyle oldu: desen `uret_bilanco`da
# yillardir vardi, `uret_bilanco_sayfa` ve `bilanco_tazele`ye hic
# yayilmadi.
#
# OLCUT AST, METIN DEGIL. "Dosyada `ara_ver` geciyor mu" demek,
# yorumda gectigi icin de gecerdi.
#
# IKI KADEME IZLENIYOR: dongu kaynagi dogrudan cagiriyor olabilir
# (`cek`, `donem_getir`) ya da ayni dosyadaki kaynaga giden bir
# yerel fonksiyon uzerinden (`sirket_isle`, `sayfa_tazele`).
import ast                                              # noqa: E402

#: KAYNAK ARALIGI SAYILAN BEKLEME. Olcut `ara_ver` ya da uzerinde
#: `ARA_SN` yazan bir `sleep`.
#:
#: NEDEN "HERHANGI BIR SLEEP" DEGIL -- MUTASYON KACTI
#: --------------------------------------------------
#: Ilk yazim `{"ara_ver", "sleep", "_uyu"}` diyordu ve sayfa
#: dongusunden `ara_ver()` cagrisini SILEN mutasyon KACTI: ayni
#: dongu `_kota_bekle()`i de cagiriyor, o da `_uyu` kullaniyor.
#: Yani kural, AI kotasi icin yapilan yirmi dakikalik beklemeyi
#: kaynak araligi sandi.
#:
#: Iki bekleme ayri sorunu cozuyor ve biri otekinin yerine
#: GECMIYOR. Ayrim NEYIN beklendiginde: kaynak araligi `ARA_SN`,
#: kota beklemesi dakika.
_BEKLEYEN = {"ara_ver"}
_KOKDIZIN = _KOK.parent


def _cagri_adlari(dugum) -> set:
    cikti = set()
    for c in ast.walk(dugum):
        if isinstance(c, ast.Call):
            f = c.func
            if isinstance(f, ast.Name):
                cikti.add(f.id)
            elif isinstance(f, ast.Attribute):
                cikti.add(f.attr)
    return cikti


def _ceken_arayuzler(yol) -> set:
    """`bilanco_ag` icinde AG ISTEGINE ulasan butun arayuzler.

    ELLE YAZILAN LISTE BAYATLAR -- OLCULDU
    --------------------------------------
    Ilk yazim `{"donem_getir", "mali_takvim", "cek", "son_donem"}`
    diyordu ve bir mutasyon KACTI: `sektor_isle` mali tabloyu
    `ara_donem` uzerinden cekiyor ve o ad listede yoktu. Yani
    yuzlerce istek atan taraf kuralin GORUS ALANI DISINDAYDI;
    sirket basina beklemesi silinince kural yesil kaldi.

    Liste artik `cek`ten geriye dogru KAPANIS olarak uretiliyor:
    `cek`i cagiran, onu cagirani cagiran... Yeni bir sarmalayici
    eklendiginde kural onu kendiliginden goruyor.
    """
    ag = ast.parse(yol.read_text(encoding="utf-8"))
    cagri = {f.name: _cagri_adlari(f) for f in ast.walk(ag)
             if isinstance(f, ast.FunctionDef)}
    ulasan = {"cek"}
    while True:
        ek = {ad for ad, c in cagri.items()
              if ad not in ulasan and (c & ulasan)}
        if not ek:
            return ulasan
        ulasan |= ek


_CEKEN = _ceken_arayuzler(_KOK / "kaynak" / "bilanco_ag.py")
# ETKISIZLIK KONTROLU: kapanis bos ya da tek elemanli kalirsa kural
# hicbir sey olcmez. Bilinen sarmalayicilar ADIYLA bekleniyor --
# listeyi tekrar elle yazmak icin degil, kapanisin CALISTIGINI
# gostermek icin.
for _ad in ("cek", "ara_donem", "donem_getir", "mali_takvim", "son_donem"):
    dogru(f"KONTROL: `{_ad}` kaynaga ulasan arayuz sayiliyor",
          _ad in _CEKEN)
dogru("KONTROL: kaynaga ULASMAYAN arayuz listede YOK",
      "donem_toplami" not in _CEKEN and "ay_adi" not in _CEKEN)


def _aralik_cagrisi(dugum) -> bool:
    """Bu dugum bir kaynak-araligi beklemesi mi?

    Olcut cagrinin ARGUMANI: `sleep(KOTA_BEKLEME_DK * 60)` kaynak
    araligi DEGIL, AI kotasi beklemesidir. Ikisini ayni saymak bir
    mutasyonun kacmasina yol acti.
    """
    if not isinstance(dugum, ast.Call):
        return False
    ad = (dugum.func.id if isinstance(dugum.func, ast.Name)
          else dugum.func.attr if isinstance(dugum.func, ast.Attribute)
          else "")
    if ad == "ara_ver":
        return True
    return ad == "sleep" and any(
        isinstance(x, ast.Name) and "ARA_SN" in x.id
        or isinstance(x, ast.Attribute) and "ARA_SN" in x.attr
        for a in dugum.args for x in ast.walk(a))


def _aralik_bekliyor(dugum) -> bool:
    """Govdenin KOSULSUZ yolunda bir aralik beklemesi var mi?

    KOSULSUZ OLMASI SART -- BIR MUTASYON BUNDAN FAYDALANDI
    -----------------------------------------------------
    Ilk yazim `ast.walk` ile her yere bakiyordu, yani bir `if`in
    icindeki bekleme de sayiliyordu. `sektor_isle` beklemeyi UC
    cikis yolunda tekrarliyordu; yalnizca BASARI yolundaki silindi
    ve kural yesil kaldi, cunku oteki iki dal hala bekliyordu --
    oysa silinen, sirketlerin COGUNUN gectigi yoldu.

    Olcut artik govdenin DOGRUDAN ifadeleri (ve `try` govdesi /
    `finally` bloklari). Dal icine saklanmis bir tedbir, bir sonraki
    dal eklendiginde yine atlanir.
    """
    for st in (dugum.body if hasattr(dugum, "body") else []):
        if isinstance(st, ast.Expr) and _aralik_cagrisi(st.value):
            return True
        # DONGU ICINE INILIYOR: bir fonksiyonun beklemesi kendi
        # `for`unun icinde olur -- istekler orada atiliyor. Dongu
        # govdesi de kosulsuzdur.
        #
        # `try/finally` de kosulsuz: her yolda kosuyor.
        if isinstance(st, (ast.For, ast.While, ast.Try))                 and _aralik_bekliyor(st):
            return True
        if isinstance(st, ast.Try) and any(
                isinstance(a, ast.Expr) and _aralik_cagrisi(a.value)
                for a in st.finalbody):
            return True
    return False


def _beklemesiz_donguler(yollar) -> list:
    """Kaynaga giden ama aralik beklemeyen donguler.

    CEKIM VE BEKLEME AYNI DERINLIKTE ARANIYOR. Ilk yazim cekimi IKI
    kademe (dongu -> yerel fonksiyon -> kaynak), beklemeyi ise TEK
    kademe (yalnizca dongu govdesi) izliyordu. Bu asimetri hemen
    yanlis pozitif uretti: `uret_bilanco.py`nin sektor dongusu
    `sektor_isle`i cagiriyor ve bekleme O FONKSIYONUN icinde, sirket
    basina yapiliyor -- dogru olan bir kod kusurlu gorundu.

    Yanlis pozitif bir korumayi iki yolla oldurur: ya kural
    gevsetilir, ya koruma kapatilir. Ikisi de gercek kusuru geri
    getirirdi.
    """
    bulgu = []
    for yol in yollar:
        if yol.name.startswith("test_"):
            continue
        try:
            ag = ast.parse(yol.read_text(encoding="utf-8-sig"))
        except SyntaxError:
            continue
        yerel = {f.name: f for f in ast.walk(ag)
                 if isinstance(f, ast.FunctionDef)}
        ceken_fn = {ad for ad, f in yerel.items()
                    if _cagri_adlari(f) & _CEKEN}
        for d in ast.walk(ag):
            if not isinstance(d, (ast.For, ast.While)):
                continue
            a = _cagri_adlari(d)
            dolayli = a & ceken_fn
            if not ((a & _CEKEN) or dolayli):
                continue
            # DONGUNUN KENDISI BEKLIYORSA her yol kapanmis olur.
            if _aralik_bekliyor(d):
                continue
            # BEKLEMEYI CEKEN FONKSIYON YAPMALI -- baska biri degil.
            #
            # Ilk yazim "cagrilan fonksiyonlardan BIRI bekliyor mu"
            # diye soruyordu ve bir mutasyon KACTI: `uret_bilanco`nun
            # sektor dongusu hem `sektor_donemi` hem `sektor_isle`
            # cagiriyor. `sektor_isle`in sirket basina beklemesi
            # SILINDIGINDE kural yesil kaldi, cunku `sektor_donemi`
            # hala bekliyordu -- oysa yuzlerce istek atan taraf
            # `sektor_isle`di.
            #
            # Olcut artik HER cekim yolunun kendi beklemesi olmasi.
            if dolayli and all(_aralik_bekliyor(yerel[ad])
                               for ad in dolayli):
                continue
            bulgu.append(f"{yol.name}:{d.lineno}")
    return bulgu


# BILANCO HATTI: kaynak stockanalysis.com ve bizi KISITLIYOR.
_HAT = [_KOK / ad for ad in ("uret_bilanco.py", "uret_bilanco_sayfa.py",
                             "bilanco_tazele.py", "bilanco_nobetci.py",
                             "sektor_tazele.py")] + \
       [_KOK / "kaynak" / "bilanco_ag.py"]
for _y in _HAT:
    dogru(f"KONTROL: {_y.name} var", _y.exists())

_bulgu = _beklemesiz_donguler(_HAT)
esit(_bulgu, [], f"bilanco hattinda beklemesiz kaynak dongusu YOK")

# ETKISIZLIK KONTROLU: tarama gercekten eliyor mu?
#
# Bir tarama "hicbir sey bulamadim" diyerek de yesil doner. Bilerek
# bozulmus bir kaynak uzerinde AYNI tarama bulgu URETMELI, yoksa
# yukaridaki iddia bir sey olcmuyordu.
import tempfile                                         # noqa: E402

_gecici = pathlib.Path(tempfile.mkdtemp())


def _dongu_satiri(yol) -> str:
    """Ornek dosyadaki TEK dongunun "ad:satir" etiketi.

    Satir numarasini elle yazmak, ornek bir satir uzayinca sessizce
    kayardi. Beklenti ornegin KENDISINDEN okunuyor; ornek sinama
    verisi, korunan kod degil.
    """
    ag = ast.parse(yol.read_text(encoding="utf-8"))
    d = [x for x in ast.walk(ag) if isinstance(x, (ast.For, ast.While))]
    assert len(d) == 1, f"{yol.name}: {len(d)} dongu"
    return f"{yol.name}:{d[0].lineno}"

_kotu = _gecici / "ornek_kotu.py"
_kotu.write_text(
    "def yukle(kod):\n"
    "    return cek(kod, 'gelir')\n"
    "\n"
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        yukle(k)\n", encoding="utf-8")
dogru("KONTROL: tarama beklemesiz bir donguyu GERCEKTEN buluyor",
      _beklemesiz_donguler([_kotu]) == [_dongu_satiri(_kotu)])

_iyi = _gecici / "ornek_iyi.py"
_iyi.write_text(
    "def yukle(kod):\n"
    "    return cek(kod, 'gelir')\n"
    "\n"
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        yukle(k)\n"
    "        ara_ver()\n", encoding="utf-8")
dogru("KONTROL: beklemesi olan dongu bulgu URETMIYOR",
      _beklemesiz_donguler([_iyi]) == [])


_derin = _gecici / "ornek_derin.py"
_derin.write_text(
    "def yukle(kod):\n"
    "    d = cek(kod, 'gelir')\n"
    "    ara_ver()\n"
    "    return d\n"
    "\n"
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        yukle(k)\n", encoding="utf-8")
dogru("KONTROL: beklemesi CAGRILAN fonksiyonda olan dongu temiz",
      _beklemesiz_donguler([_derin]) == [])

# KOTA BEKLEMESI KAYNAK ARALIGI SAYILMAZ.
#
# Bu ayrimi kuran daraltma bir MUTASYON KACISINDAN dogdu: sayfa
# dongusunden `ara_ver()` silindiginde kural yesil kaldi, cunku
# ayni dongudeki `_kota_bekle()` de uyuyor. Asagidaki ornek tam o
# sekli tasiyor ve BULGU URETMELI.
_kota = _gecici / "ornek_kota.py"
_kota.write_text(
    "def bekle():\n"
    "    _uyu(20 * 60)\n"
    "\n"
    "def yukle(kod):\n"
    "    return cek(kod, 'gelir')\n"
    "\n"
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        bekle()\n"
    "        yukle(k)\n", encoding="utf-8")
dogru("KONTROL: yalnizca KOTA bekleyen dongu bulgu URETIYOR",
      _beklemesiz_donguler([_kota]) == [_dongu_satiri(_kota)])

# IKI CEKIM YOLU, BIRINDE BEKLEME YOK.
#
# Bu kontrol de bir MUTASYON KACISINDAN dogdu: `uret_bilanco`nun
# sektor dongusu hem `sektor_donemi` hem `sektor_isle` cagiriyor.
# `sektor_isle`in beklemesi silindiginde kural yesil kaldi, cunku
# oteki hala bekliyordu -- oysa yuzlerce istek atan taraf o.
_yarim = _gecici / "ornek_yarim.py"
_yarim.write_text(
    "def yokla(kod):\n"
    "    d = son_donem(kod)\n"
    "    ara_ver()\n"
    "    return d\n"
    "\n"
    "def olc(kod):\n"
    "    return cek(kod, 'gelir')\n"
    "\n"
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        yokla(k)\n"
    "        olc(k)\n", encoding="utf-8")
dogru("KONTROL: cekim yollarindan biri beklemiyorsa bulgu VAR",
      _beklemesiz_donguler([_yarim]) == [_dongu_satiri(_yarim)])

# BEKLEME DAL ICINE SAKLANAMAZ.
#
# `sektor_isle` beklemeyi UC cikis dalinda tekrarliyordu ve
# yalnizca BASARI dalindaki silindiginde kural yesil kaldi.
# Olcut artik KOSULSUZ yol; asagidaki ornek beklemeyi bir `if`in
# icine koyuyor ve BULGU URETMELI.
_dal = _gecici / "ornek_dal.py"
_dal.write_text(
    "def hepsi(kodlar):\n"
    "    for k in kodlar:\n"
    "        d = cek(k, 'gelir')\n"
    "        if d is None:\n"
    "            ara_ver()\n"
    "            continue\n", encoding="utf-8")
dogru("KONTROL: dal icine saklanmis bekleme bulgu URETIYOR",
      _beklemesiz_donguler([_dal]) == [_dongu_satiri(_dal)])

# =====================================================================
print("11. PENCERE ACIKKEN NOBETCI BUTCEYI YEMIYOR")
# =====================================================================
#
# OLCULDU (2026-10-31, kosu #62): kaynak bir kosuda ~82 mali tablo
# istegi veriyor, sonra 429 verip kapaniyor. Dagitim soyleydi:
#
#     nobetci  60 istek, 0 hata  -> 1 olay (GENIL, sayfasi #61'de
#                                   zaten yazilmisti)
#     sayfa    ~22 istek         -> 20 sayfa, sonra KAYNAK KAPANDI
#     veri      0                -> 11 sektorun 11'i atlandi
#                                   ("KAYNAK REDDEDIYOR, atlandi")
#
# Yani butcenin %73'u, cevabini zaten bildigimiz bir soruya gitti.
# Ustelik o istekler `cek(kod, "gelir")` ile yapiliyor: sayfa
# adiminin ihtiyac duydugu ceyreklik serinin ta kendisini cekip
# ATIYOR.
#
# Nobetcinin isi sezonun ACILISINI fark etmek. Pencere zaten acikken
# karar verecegi bir sey yok.
import bilanco_nobetci as NB                             # noqa: E402

_asil_oku = NB.nobet_oku
try:
    NB.nobet_oku = lambda: {"son_bitis": "2026-09-30"}
    _acik = dt.date(2026, 10, 31)
    _kapali = dt.date(2026, 12, 20)

    dogru("pencere ACIKKEN orneklem KUCULUYOR",
          NB.orneklem_boyu(bugun=_acik) < NB.VARSAYILAN_ORNEKLEM)
    esit(NB.orneklem_boyu(bugun=_kapali), NB.VARSAYILAN_ORNEKLEM,
         "pencere KAPALIYKEN tam orneklem")
    # KUCULME ANLAMLI OLMALI: bir iki istek kurtarmak isi cozmezdi.
    dogru("kucuk orneklem butcenin kucuk bir dilimi",
          NB.orneklem_boyu(bugun=_acik) <= NB.VARSAYILAN_ORNEKLEM / 4)
    dogru("kucuk orneklem SIFIR DEGIL -- yoklama surmeli",
          NB.orneklem_boyu(bugun=_acik) > 0)

    # ELLE VERILEN DEGER KAZANIR: kuculme bir varsayilan, tavan degil.
    esit(NB.orneklem_boyu(40, _acik), 40, "elle verilen orneklem kuculmuyor")
    esit(NB.orneklem_boyu(5, _kapali), 5, "elle verilen orneklem buyumuyor")

    # KARAR PENCEREYE BAGLI, TAKVIME DEGIL.
    #
    # `son_bitis` bilinmiyorsa pencere kapali sayiliyor ve tam
    # orneklemle donuluyor -- "bilmiyorum" ile "acik" ayni sey degil.
    NB.nobet_oku = lambda: {}
    esit(NB.orneklem_boyu(bugun=_acik), NB.VARSAYILAN_ORNEKLEM,
         "son_bitis bilinmiyorsa TAM orneklem")
    NB.nobet_oku = lambda: {"son_bitis": "2026-09-30"}

    # ETKISIZLIK KONTROLU: karar gercekten pencereyi OKUYOR mu?
    _asil_pencere = bilanco_ag.pencere_acik
    try:
        bilanco_ag.pencere_acik = lambda sb, bugun: (False, 0)
        esit(NB.orneklem_boyu(bugun=_acik), NB.VARSAYILAN_ORNEKLEM,
             "KONTROL: pencere kapali donerse tam orneklem")
        bilanco_ag.pencere_acik = lambda sb, bugun: (True, 0)
        dogru("KONTROL: pencere acik donerse kucuk orneklem",
              NB.orneklem_boyu(bugun=_kapali) < NB.VARSAYILAN_ORNEKLEM)
    finally:
        bilanco_ag.pencere_acik = _asil_pencere
    dogru("KONTROL: asil pencere geri konuldu",
          bilanco_ag.pencere_acik is _asil_pencere)

    # `bak()` KARARI GERCEKTEN KULLANIYOR MU -- OLCUT ISTEK SAYISI.
    #
    # Bir MUTASYON buradan kacti: `orneklem_boyu` dogru calisiyordu
    # ama `bak()` onu atlayip `VARSAYILAN_ORNEKLEM`e dusurulunca
    # sinama yesil kaldi. Karari sinamak, karari KULLANAN akisi
    # sinamak degil -- bu depoda "dugum eklendi, kural yazilmadi"
    # diye kayitli.
    #
    # Olcut KAC SIRKETE SORULDUGU: `mali_takvim` yamalanip sayiliyor,
    # yani ag yok.
    _sorulan = []
    _asil_takvim = bilanco_ag.mali_takvim
    _asil_pen = bilanco_ag.pencere_acik
    try:
        bilanco_ag.mali_takvim = lambda kod, *a, **k: (
            _sorulan.append(kod) or {"son_bitis": "2026-09-30",
                                     "yil_sonu_ayi": 12})
        # PENCERE SABITLENIYOR -- BU IDDIA TAKVIME BAGLI OLMAMALI.
        #
        # `bak()` tarihi KENDI okuyor (`date.today()`), yani iddia
        # dosyanin kosturuldugu GUNE baglanirdi: 2026-11-29'dan
        # sonra pencere kapanir ve bu bolum DUSERDI. Tam olarak
        # `test_zaman_bombasi`nin aradigi sey. Sabitleyince iddia
        # "pencere acikken az soruyor" olarak kaliyor -- olculmek
        # istenen de bu.
        bilanco_ag.pencere_acik = lambda sb, bugun: (True, 1)
        NB.bak(kuru=True)
        dogru("bak() pencere acikken AZ sirkete soruyor",
              0 < len(_sorulan) <= NB.PENCERE_ORNEKLEMI)
        dogru("bak() tam orneklem KADAR sormuyor",
              len(_sorulan) < NB.VARSAYILAN_ORNEKLEM)
        # KONTROL: ayni akis elle verilen degeri de uyguluyor mu?
        _sorulan.clear()
        NB.bak(orneklem=3, kuru=True)
        esit(len(_sorulan), 3, "KONTROL: bak() elle verilen orneklemi uyguluyor")
    finally:
        bilanco_ag.mali_takvim = _asil_takvim
        bilanco_ag.pencere_acik = _asil_pen
    dogru("KONTROL: asil pencere geri konuldu (bak bolumu)",
          bilanco_ag.pencere_acik is _asil_pen)

    # KURAL TEK YERDEN: nobetci kendi kopyasini TASIMIYOR.
    #
    # Ayni kurali iki yere yazmak `ARA_SN`in basina geleni
    # tekrarlamak olurdu. Olcut AST: nobetci dosyasinda gun
    # hesaplayan ikinci bir pencere tanimi OLMAMALI.
    _nb = ast.parse((_KOK / "bilanco_nobetci.py").read_text(encoding="utf-8"))
    esit([f.name for f in ast.walk(_nb)
          if isinstance(f, ast.FunctionDef) and f.name == "pencere_acik"],
         [], "nobetci kuralin KOPYASINI tasimiyor")
    dogru("nobetci kurali bilanco_ag'den OKUYOR",
          "pencere_acik" in _cagri_adlari(
              next(f for f in ast.walk(_nb) if isinstance(f, ast.FunctionDef)
                   and f.name == "pencere_acik_mi")))
finally:
    NB.nobet_oku = _asil_oku

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
