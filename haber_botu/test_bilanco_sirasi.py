# -*- coding: utf-8 -*-
"""SEKTOR ICINDEKI SIRA VE SIRKET DUZEYINDE BIRLESTIRME.

BU DOSYA NEDEN VAR -- OLCULDU, YAYINDAYDI (2026-11-10)
------------------------------------------------------
Iki kusur ayni kosuda birlikte olculdu (kosu #78, 04:21 UTC).

1) SIRA ALFABETIKTI. Kaynak her kosuda bir yerde kapaniyor
   (`bilanco_ag.ARDISIK_RED_SINIRI`, 8 ardisik red) ve kalan
   istekler YAPILMIYOR. Sira sabit olunca her kosuda AYNI kuyruk
   atiliyor:

       Gayrimenkul (38 sirket): 27 olculdu, kaynak PSGYO'da kapandi
       atlanan 11: alfabetik kuyruk -- her kosuda ayni 11

   Bu kuyrukta TDGYO ve TURGG vardi; nobet defterine gore ikisi de
   2026-09-30 donemini BILDIRMISTI ve sayfasi YOKTU. Yani hat yeni
   veriyi, elindeki kanita ragmen hic istemiyordu.

   AYNI KUSUR BIR DUZEY YUKARIDA 2026-09-14'TE COZULMUSTU: sektor
   sirasi bayatliga baglandi. Sirket duzeyi dokunulmadan kaldi.

2) BIRLESTIRME SEKTOR DUZEYINDE KALMIS. `cikti[s] = yeni_sektor`
   sektoru TUMDEN degistiriyor; o kosuda olculemeyen sirket
   dosyadan SILINIYOR. Olculdu:

       11-02  Gayrimenkul 36 sirket, dosyada toplam 336
       11-10  Gayrimenkul 27 sirket, dosyada toplam 299
       kaybolan: RGYAS, RYGYO, SEGYO, SURGY, SVGYO, VKGYO, VRGYO, YGGYO

   `kapsam_coktu` bunu gormuyor -- 27, 36'nin %75'i. Hat yeni
   sirket eklemekte gecikirken ELINDEKINI de kaybediyordu.

IKISI BIRLIKTE ANLAMLI: birlestirme olmadan sirayi degistirmek,
one alinanlari olcerken alfabetik bastakileri SILERDI.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import ast
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

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


def dogru(kosul, aciklama: str) -> None:
    esit(bool(kosul), True, aciklama)


def _kodlar(liste) -> list[str]:
    return [k for k, _ in liste]


# ---------------------------------------------------------------- 1
print("1. sira_kur -- KANITI OLAN ONCE")

#: Gayrimenkul'un alfabetik kuyrugundan olculmus bir dilim.
_SIRKETLER = [(k, {"unvan": k}) for k in
              ["AAGYO", "ADESE", "AKFGY", "TDGYO", "TURGG", "YGGYO"]]

# Dosyada olculmus donem: hepsi Q2.
_BITIS = {k: "2026-06-30" for k, _ in _SIRKETLER}
# Nobetcinin gordugu: iki sirket Q3'e gecmis.
_NOBET = dict(_BITIS, TDGYO="2026-09-30", TURGG="2026-09-30")

_sira = _kodlar(U.sira_kur(_SIRKETLER, _BITIS, _NOBET))
esit(_sira[:2], ["TDGYO", "TURGG"],
     "nobet defteri Q3 diyen iki sirket EN BASTA (alfabetik son ikisi)")
esit(_sira[2:], ["AAGYO", "ADESE", "AKFGY", "YGGYO"],
     "kaniti olmayanlar arkada ve alfabetik -- sira KARARLI")

# ASIL KUSUR, KANITLI SEKILDE: alfabetik sirada ilk 3 olculup kaynak
# kapanirsa TDGYO/TURGG HIC istenmiyor. Yeni sirada isteniyor.
_alfabetik = _kodlar(sorted(_SIRKETLER))[:3]
dogru("TDGYO" not in _alfabetik and "TURGG" not in _alfabetik,
      "alfabetik sirada ilk 3 istek yeni veriyi HIC istemiyor")
dogru("TDGYO" in _sira[:3] and "TURGG" in _sira[:3],
      "yeni sirada ilk 3 istek yeni veriyi ISTIYOR")

print("")
print("2. sira_kur -- BILINMEYEN ONE ALINMIYOR")
# Nobetci bu sirkete HIC bakmamis: yeni verisi olup olmadigini
# BILMIYORUZ. Bilmedigimiz bir tazeligi olculmus gibi sunmak,
# `uret_bilanco_sayfa._tazelik` icinde de reddedilen seydir.
_n2 = {"AAGYO": "2026-06-30"}
_s2 = _kodlar(U.sira_kur(_SIRKETLER, _BITIS, _n2))
esit(_s2, ["AAGYO", "ADESE", "AKFGY", "TDGYO", "TURGG", "YGGYO"],
     "defterde kaydi olmayan sirket one alinmiyor")

# Nobetci ile olcum AYNI donemi soyluyorsa yeni veri YOK.
_s3 = _kodlar(U.sira_kur(_SIRKETLER, _BITIS, dict(_BITIS)))
esit(_s3, ["AAGYO", "ADESE", "AKFGY", "TDGYO", "TURGG", "YGGYO"],
     "nobetci ile olcum ayni donemdeyse sira degismiyor")

# Olculmemis sirket (dosyada bitis YOK) ama nobetci bir donem
# goruyor -> kanit var, one aliniyor.
_s4 = _kodlar(U.sira_kur(_SIRKETLER, {}, {"YGGYO": "2026-09-30"}))
esit(_s4[0], "YGGYO",
     "hic olculmemis ama nobetcide donemi olan sirket basa geciyor")

print("")
print("3. sira_kur -- EN YENI BILDIREN BASTA")
_n5 = {"TDGYO": "2026-09-30", "TURGG": "2026-08-31", "YGGYO": "2026-10-31"}
_s5 = _kodlar(U.sira_kur(_SIRKETLER, _BITIS, _n5))
esit(_s5[:3], ["YGGYO", "TDGYO", "TURGG"],
     "one alinanlar arasinda donem bitisi EN YENI olan basta")

print("")
print("3b. OLCUT 'YENI', 'AYNI' DEGIL")
# Bir mutasyon tam buradan kacti: `gorulen > olculen` yerine
# `gorulen >= olculen` yazildiginda yukaridaki kurallarin HEPSI
# yesil kaldi. Cunku esitlik durumunda one alinanlar yine ayni
# tarihi tasiyor ve siralama alfabetige donuyordu -- ayni ciktiyi
# veren farkli bir kural.
#
# Burada ayrim ZORLANIYOR: YGGYO'nun olcumu zaten Q3 (yapacak is
# YOK), TDGYO'nun olcumu Q2 ama nobetci Q3 goruyor (yapacak is VAR).
_b6 = dict(_BITIS, YGGYO="2026-09-30")
_n6 = {"YGGYO": "2026-09-30", "TDGYO": "2026-09-30"}
_s6 = _kodlar(U.sira_kur(_SIRKETLER, _b6, _n6))
esit(_s6, ["TDGYO", "AAGYO", "ADESE", "AKFGY", "TURGG", "YGGYO"],
     "olcumu zaten guncel olan sirket ONE ALINMIYOR, yalnizca yenisi")


# ---------------------------------------------------------------- 4
print("")
print("4. sektor_isle -- SIRKET DUZEYINDE BIRLESTIRME")


def _tablo():
    """Yeterli bir tablo. Degerler onemsiz; yeterlilik onemli."""
    return {
        "gelir": {"Revenue": 1000.0, "Gross Profit": 300.0,
                  "Operating Income": 50.0, "Net Income": 40.0},
        "bilanco": {"Total Assets": 5000.0,
                    "Shareholders' Equity": 2000.0,
                    "Total Current Assets": 1500.0,
                    "Total Current Liabilities": 800.0,
                    "Accounts Receivable": 300.0, "Inventory": 200.0},
        "nakit": {"Operating Cash Flow": 60.0, "Cash Interest Paid": 10.0},
        "gelir_onceki": {}, "bilanco_onceki": {}, "nakit_onceki": {},
        "_mali": {"yil_sonu_ayi": 12, "son_bitis": "2026-09-30"},
    }


_ASIL = (U.sektordeki, U.bilanco_ag.ara_donem, U.bilanco_ag.ARA_SN,
         U.nobet_bitisleri)

#: Onceki kosudan gelen sektor kaydi. KORUNMASI GEREKEN veri bu.
_ONCEKI = {
    "sektor": "Kurgu",
    "sirket": {"AAGYO": {"brut_marj": 11.0}, "ADESE": {"brut_marj": 12.0},
               "SILINMIS": {"brut_marj": 99.0}},
    "bitis": {"AAGYO": "2026-06-30", "ADESE": "2026-06-30",
              "SILINMIS": "2026-06-30"},
    "mali": {"ADESE": 5},
    "onceki_yok": ["ADESE"],
    "kirpilan": ["AAGYO"],
}

try:
    U.bilanco_ag.ARA_SN = 0
    U.nobet_bitisleri = lambda: {"TDGYO": "2026-09-30"}
    U.sektordeki = lambda s: [(k, {"unvan": k})
                              for k in ["AAGYO", "ADESE", "TDGYO"]]
    # KAYNAK TDGYO'DAN SONRA KAPANIYOR: AAGYO ve ADESE icin bos
    # tablo donuyor. Gercek kosunun aynisi.
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo() if kod == "TDGYO" else {})

    _r = U.sektor_isle("Kurgu", "2026 3. çeyrek", 3, onceki=_ONCEKI)

    esit(sorted(_r["sirket"]), ["AAGYO", "ADESE", "TDGYO"],
         "olculemeyen iki sirket dosyada KALIYOR, yenisi EKLENIYOR")
    esit(_r["sirket"]["AAGYO"], {"brut_marj": 11.0},
         "korunan sirketin onceki olcumu degismiyor")
    esit(_r["bitis"].get("AAGYO"), "2026-06-30",
         "korunan sirketin donem bitisi de devrediyor")
    esit(_r["bitis"].get("TDGYO"), "2026-09-30",
         "taze olculenin donem bitisi kaynaktan geliyor")
    esit(_r["mali"].get("ADESE"), 5,
         "korunan sirketin mali yil sonu devrediyor")
    esit(_r["onceki_yok"], ["ADESE"], "devralinan onceki_yok bayragi duruyor")
    esit(_r["kirpilan"], ["AAGYO"], "devralinan kirpilan bayragi duruyor")

    # DEFTERDE OLMAYAN SIRKET SONSUZA KADAR TASINMIYOR.
    dogru("SILINMIS" not in _r["sirket"],
          "sektorde artik olmayan sirket devralinmiyor")
    dogru("SILINMIS" not in _r["bitis"],
          "sektorde artik olmayan sirketin bitisi de devralinmiyor")

    # KAPSAM KORUMASI ARTIK SPONTANE TETIKLENMIYOR.
    esit(U.sirket_sayisi(_r), 3, "kapsam 3 sirket -- kuculme YOK")

    # BU KOSUDA NE OLCULDU -- AYRI VE DOGRU.
    #
    # `main` sektorun `tazelendi` damgasini buna bakarak atiyor.
    # Devralinani da sayan bir surum, hic cekilemeyen sektoru "taze"
    # gosterir ve sektor sirasini TERSINE cevirirdi.
    esit(_r["taze_olculen"], ["TDGYO"],
         "taze_olculen yalnizca bu kosuda olculeni tasiyor")

    # ------------------------------------------------------------ 5
    print("")
    print("5. ETIKET ILE VERI AYNI OLCUMDEN")
    # Taze olcum donem tarihini VEREMEDIYSE devralinan tarih
    # TEMIZLENMELI; yoksa yeni rakamlarin yanina eski donem yazilir.
    _t = _tablo()
    _t["_mali"] = {"yil_sonu_ayi": 12}          # son_bitis YOK
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _t if kod == "AAGYO" else {})
    _r2 = U.sektor_isle("Kurgu", "2026 3. çeyrek", 3, onceki=_ONCEKI)
    dogru("AAGYO" not in _r2["bitis"],
          "donemi okunamayan taze olcum, devralinan tarihi SILIYOR")
    esit(_r2["bitis"].get("ADESE"), "2026-06-30",
         "olculmeyen sirketin devralinan tarihi yerinde")

    # Devralinan bayrak, taze olcumle YENILENIYOR.
    dogru("AAGYO" not in _r2["kirpilan"],
          "taze olculen sirketin devralinan kirpilan bayragi dusuyor")
finally:
    (U.sektordeki, U.bilanco_ag.ara_donem, U.bilanco_ag.ARA_SN,
     U.nobet_bitisleri) = _ASIL


# ---------------------------------------------------------------- 6
print("")
print("6. LOGDAKI SAYIM DOGRU ADIYLA")
# `olculen` artik devralinani da tasiyor. Onun boyunu "olculdu" diye
# yazmak, bu kosuda YAPILMAYAN olcumu yapilmis gibi gostermek olur.
# Gun sonunda hattin durumu bu satirdan okunuyor.
#
# OLCUT BASILAN METIN, KAYNAKTAKI AD DEGIL. Ilk surum bu kurali
# AST ile yazdi -- f-dizgisinde `olculen` gecmesin diye. Bir
# MUTASYON ordan kacti: sayim f-dizgisinin DISINDA hesaplaniyor,
# dizgi yalnizca degiskeni tasiyor. Kural, kuralin olcmek istedigi
# seyi olcmuyordu.
import contextlib                                  # noqa: E402
import io                                          # noqa: E402

_ASIL6 = (U.sektordeki, U.bilanco_ag.ara_donem, U.bilanco_ag.ARA_SN,
          U.nobet_bitisleri)
try:
    U.bilanco_ag.ARA_SN = 0
    U.nobet_bitisleri = lambda: {}
    U.sektordeki = lambda s: [(k, {"unvan": k})
                              for k in ["AAGYO", "ADESE", "TDGYO"]]
    U.bilanco_ag.ara_donem = (
        lambda kod, ceyrek=1, istemci=None, bugun=None:
        _tablo() if kod == "TDGYO" else {})
    _yakala = io.StringIO()
    with contextlib.redirect_stdout(_yakala):
        U.sektor_isle("Kurgu", "2026 3. çeyrek", 3, onceki=_ONCEKI)
    _log = _yakala.getvalue()
finally:
    (U.sektordeki, U.bilanco_ag.ara_donem, U.bilanco_ag.ARA_SN,
     U.nobet_bitisleri) = _ASIL6

dogru("1 şirket ölçüldü" in _log,
      "log BU KOSUDA olculeni soyluyor (1 sirket)")
dogru("3 şirket ölçüldü" not in _log,
      "devralinan kayitlar 'olculdu' diye SAYILMIYOR")
dogru("2 şirket önceki ölçümüyle korundu" in _log,
      "devralinan kayitlar ayri ve dogru adiyla raporlaniyor")


# ---------------------------------------------------------------- 7
print("")
print("7. AKIS KURALI -- YORUM DEGIL CAGRI")
# Yorum "birlestirme var" diye yazabilir; olcut CAGRININ KENDISI.
_agac = ast.parse((_KOK / "uret_bilanco.py").read_text(encoding="utf-8"))
_isle = next(d for d in ast.walk(_agac)
             if isinstance(d, ast.FunctionDef) and d.name == "sektor_isle")
_main = next(d for d in ast.walk(_agac)
             if isinstance(d, ast.FunctionDef) and d.name == "main")
_cagrilar = [c for c in ast.walk(_main)
             if isinstance(c, ast.Call)
             and isinstance(c.func, ast.Name)
             and c.func.id == "sektor_isle"]
esit(len(_cagrilar), 1, "main icinde tek bir sektor_isle cagrisi var")
esit(sorted(k.arg for k in _cagrilar[0].keywords), ["onceki"],
     "cagri onceki sektor kaydini ICERIYE geciriyor")

_sira_cagrisi = [c for c in ast.walk(_isle)
                 if isinstance(c, ast.Call)
                 and isinstance(c.func, ast.Name)
                 and c.func.id == "sira_kur"]
esit(len(_sira_cagrisi), 1, "sektor_isle sirayi sira_kur'dan aliyor")
# Sira kanita bakmali: nobet defteri CAGRIYA giriyor mu.
_arg_adlari = {a.id for arg in _sira_cagrisi[0].args
               for a in ast.walk(arg) if isinstance(a, ast.Name)} | \
              {f.attr for arg in _sira_cagrisi[0].args
               for f in ast.walk(arg) if isinstance(f, ast.Attribute)}
_cagirilan = {f.func.id for arg in _sira_cagrisi[0].args
              for f in ast.walk(arg)
              if isinstance(f, ast.Call) and isinstance(f.func, ast.Name)}
dogru("nobet_bitisleri" in _cagirilan,
      "sira nobet defterini okuyor -- kanit kaynagi bagli")


print("")
print("8. AYNI SIRKETIN IKI KODU -- PAY KODU SECILIR")
# OLCULDU (2026-11-10): defterde ayni `kap_kimlik`i tasiyan alti
# cift var. Alfabetik secim besinde TESADUFEN dogru kodu tutuyordu;
# altincisinda TSK'yi secip TSKB'yi eliyordu. Kaynak TSK'yi
# tanimadigi icin Turkiye Sinai Kalkinma Bankasi HIC olculmedi --
# `sektor_ozet.json`da kaydi, sitede hicbir donemde sayfasi yoktu.
_CIFTLER = [("A1CAP", "ACP"), ("ALBRK", "ALK"), ("GARAN", "TGB"),
            ("INFO", "IYF"), ("ISMEN", "IYM"), ("TSKB", "TSK")]
for _pay, _kisa in _CIFTLER:
    _s = min([_pay, _kisa], key=U.kod_tercihi)
    esit(_s, _pay, f"{_pay}/{_kisa} ciftinden pay kodu seciliyor")

# KURAL DEFTERDEN BAGIMSIZ OLARAK DA DOGRU: uc harfli kod,
# alfabetik olarak once gelse bile elenir.
esit(min(["AAA", "ZZZZ"], key=U.kod_tercihi), "ZZZZ",
     "uc harfli kod, alfabetik onceligine ragmen elenir")
esit(min(["BBBB", "AAAA"], key=U.kod_tercihi), "AAAA",
     "iki pay kodu arasinda sira KARARLI (alfabetik)")

print("")
print("8b. sektordeki -- MEKANIZMA, SAYI DEGIL")
# OLCUT ICERIKTEN BAGIMSIZ: defterde kac sirket oldugu degil,
# "her kimlik grubundan TEK ve TERCIH EDILEN kod" kurali sinaniyor.
# Sayiya baglanmis bir kural, defter buyudugunde CI'yi kirardi.
_defter = U._defter()
_sektorler = sorted({v["sektor_tr"] for v in _defter.values()
                     if v.get("sektor_tr")})
_hepsi: list[str] = []
_hata: list[str] = []
for _s in _sektorler:
    _secilen = [k for k, _ in U.sektordeki(_s)]
    _hepsi += _secilen
    # Ayni kimligin defterdeki butun kodlari
    for _kod in _secilen:
        _kim = (_defter[_kod].get("kap_kimlik") or _kod)
        _kardes = [k for k, v in _defter.items()
                   if (v.get("kap_kimlik") or k) == _kim
                   and v.get("sektor_tr") == _s]
        _dogrusu = min(_kardes, key=U.kod_tercihi)
        if _kod != _dogrusu:
            _hata.append(f"{_kod} yerine {_dogrusu} olmaliydi")
esit(_hata, [], "her kimlik grubundan TERCIH EDILEN kod secilmis")
esit(len(_hepsi), len(set(_hepsi)), "hicbir kod iki kez gecmiyor")
dogru("TSKB" in _hepsi, "TSKB artik olculecek sirketler arasinda")
dogru("TSK" not in _hepsi, "kisa kod TSK artik istenmiyor")

print("")
print("9. SESSIZ DUSUS OLCULUYOR (kapi DEGIL)")
# OLCULDU (2026-11-10): sektor ici birlestirme yokken, bir kosuda
# olculemeyen sirket ozetten SILINIYORDU. Silinen sirket IKI
# kuyruktan birden dusuyor:
#
#   * sayfa adimi adaylarini OZETTEN okuyor      -> yeni sayfa YOK
#   * goc kuyrugu ozette kaydi olmayani atliyor  -> bolum gocu YOK
#
# Yani sirket sessizce donuyor ve hicbir kosu bunu soylemiyor.
# Canli veriyle olculdu: **41 sirketin** bilanco sayfasi var ama
# ozette kaydi yok -- GARAN, PETKM, SAHOL, KORDS, ASTOR dahil.
# Ilk tespitim "yedi sirket" demisti; o olcum yalnizca "en yeni
# sayfasinda dort ceyrek yok" yolundan bakiyordu ve gercegin alti
# katini kaciriyordu.
import io as _io9                                   # noqa: E402
import contextlib as _c9                            # noqa: E402

_OZET9 = {"Sanayi": {"sirket": {"AAAA": {}, "BBBB": {}}}}
_y9 = _io9.StringIO()
with _c9.redirect_stdout(_y9):
    _d9 = U.dusenleri_bildir(_OZET9, kodlar={"AAAA", "BBBB", "CCCC"})
esit(_d9, ["CCCC"], "sayfasi olup ozette olmayan sirket BULUNUYOR")
dogru("CCCC" in _y9.getvalue(), "kod gunluge YAZILIYOR")

_y9b = _io9.StringIO()
with _c9.redirect_stdout(_y9b):
    _d9b = U.dusenleri_bildir(_OZET9, kodlar={"AAAA", "BBBB"})
esit(_d9b, [], "hepsi ozette ise liste BOS")
dogru("YOK" in _y9b.getvalue(),
      "bos durum da gunluge yaziliyor -- sessizlik 'olculmedi' demek")

# OLCUM, KAPI DEGIL. Mesru sifir (borsadan cikan sirket, kod
# degisikligi) dagitimi durdurmamali. Olcut: `main` icinde cagri
# CIPLAK bir ifade -- degere baglanmiyor, kosula girmiyor.
_cagrilar9 = [n for n in ast.walk(_main)
              if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name)
              and n.func.id == "dusenleri_bildir"]
esit(len(_cagrilar9), 1, "main icinde tek cagri var")
_ciplak = [n for n in ast.walk(_main)
           if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
           and isinstance(n.value.func, ast.Name)
           and n.value.func.id == "dusenleri_bildir"]
esit(len(_ciplak), 1,
     "cagri CIPLAK ifade -- donusu cikis kodunu etkilemiyor")

print("")
print("9b. OLCUT URETICIDEN -- SIRKET OLMAYAN SAYILMIYOR")
# Suzgec olmadan BTC ve ETH de listeye giriyordu: ikisinin "Teknik
# Gorunum" sayfasi var ama ikisi de SIRKET degil. Olcum 47 diyordu,
# dogrusu 41. Olcum araci kendi yanlisini uretiyordu.
import sayfa_kodlari as _SK9                        # noqa: E402

with __import__("tempfile").TemporaryDirectory() as _g9:
    _k9 = pathlib.Path(_g9)
    (_k9 / "2026-3-ceyrek-aaaa.md").write_text(
        "---\nkod: AAAA\nkategori: Bilanço Analizi\n---\n\ngövde\n",
        encoding="utf-8")
    (_k9 / "btc-teknik.md").write_text(
        "---\nkod: BTC\nkategori: Teknik Görünüm\n---\n\ngövde\n",
        encoding="utf-8")
    esit(_SK9.sayfasi_olan_kodlar(_k9), {"AAAA", "BTC"},
         "suzgecsiz cagri HER sayfayi sayiyor (sektor kuyrugu boyle istiyor)")
    esit(_SK9.sayfasi_olan_kodlar(_k9, kategori=_SK9.BILANCO_KATEGORI),
         {"AAAA"}, "bilanco suzgeci sirket olmayani ELIYOR")
    # Kategori dizgisi URETICIDEN: sayfayi yazan taraf ne yaziyorsa o.
    esit(_SK9.BILANCO_KATEGORI, "Bilanço Analizi",
         "kategori dizgisi uretilen on bilgiyle AYNI")

print("")
print("10. OLCULEMEYEN ILE TAZELENEMEYEN AYRI")
# OLCULDU (2026-11-13): `atlanan` sebepleri ozete YAZILIYOR ama
# hicbir yerde raporlanmiyordu. Gunluk yalnizca "-> 36 sirket
# olculdu, 2 atlandi" diyor; KIM ve NEDEN gorunmuyor.
#
# Somut: TDGYO ve TURGG her Gayrimenkul tazelemesinde ILK deneniyor
# (kanitli grup) ve her seferinde "eksik: hasilat" ile atlaniyor.
# Kaynak ikisine de veri VERIYOR -- cekim hatasi yok -- ama gelir
# tablosunda HASILAT SATIRI YOK. Yani kusur degil, veri gercegi.
# "Bekleyen 6" sayisi bu yuzden asla sifira inemiyordu.
#
# AYRIM SART: `atlanan` O KOSUYA ait. Sirket ici birlestirme
# sayesinde daha once olculmus bir sirket atlansa bile verisi
# DURUYOR. Ilk yazimda ayrim yoktu ve rapor 29 sirket icin "bu
# sayfa uretilemez" diyordu -- aralarinda AKBNK ve PGSUS vardi ve
# ikisinin de sayfasi VAR. Dogru olcut: atlandi VE ozette kaydi yok.
_OZET10 = {
    "Sanayi": {
        "sirket": {"VARDIR": {}},
        "atlanan": [["VARDIR", "eksik: stoklar"],
                    ["YOKTUR", "eksik: hasilat"]],
    },
    "Gayrimenkul": {
        "sirket": {},
        "atlanan": [["TDGYO", "eksik: hasilat"]],
    },
}
_y10 = _io9.StringIO()
with _c9.redirect_stdout(_y10):
    _d10 = U.atlananlari_bildir(_OZET10)
_log10 = _y10.getvalue()

esit(_d10, {"eksik: hasilat": ["YOKTUR", "TDGYO"]},
     "yalnizca ozette KAYDI OLMAYANLAR 'hic olculemeyen' sayiliyor")
dogru("VARDIR" not in _log10,
     "onceki olcumu duran sirket 'uretilemez' diye YAZILMIYOR")
dogru("1 şirket bu koşuda atlandı" in _log10,
      "tazeleme eksigi AYRI ve dogru adiyla raporlaniyor")
dogru("TDGYO" in _log10 and "YOKTUR" in _log10,
      "engelli sirketler adiyla yaziliyor")

# Sebep TURU korunuyor: farkli eksik alanlar ayni kovaya girmemeli,
# cunku farkli is gerektiriyorlar.
_y10b = _io9.StringIO()
with _c9.redirect_stdout(_y10b):
    _d10b = U.atlananlari_bildir(
        {"X": {"sirket": {}, "atlanan": [["A", "eksik: stoklar"],
                                         ["B", "eksik: hasilat"]]}})
esit(sorted(_d10b), ["eksik: hasilat", "eksik: stoklar"],
     "farkli eksik alanlar AYRI sebep olarak sayiliyor")

# BOS DURUM DA SOYLENIYOR: sessizlik "olculmedi" demek.
_y10c = _io9.StringIO()
with _c9.redirect_stdout(_y10c):
    U.atlananlari_bildir({"X": {"sirket": {"A": {}}, "atlanan": []}})
dogru("YOK" in _y10c.getvalue(),
      "atlanan yoksa da gunluge yaziliyor")

# OLCUM, KAPI DEGIL: `main` icinde cagri CIPLAK ifade.
_ciplak10 = [n for n in ast.walk(_main)
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
             and isinstance(n.value.func, ast.Name)
             and n.value.func.id == "atlananlari_bildir"]
esit(len(_ciplak10), 1,
     "cagri CIPLAK ifade -- donusu cikis kodunu etkilemiyor")

print("")
print("=" * 30)
print(f"GECTI={_gecti}  KALDI=0")
