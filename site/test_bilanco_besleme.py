"""Bilanco beslemesi testleri -- AGA CIKMAZ, DOSYA YAZMAZ.

Besleme NEDEN VAR: bilanco rakami bugune kadar yalnizca markdown
sayfasinda yayimlaniyordu ve o sayfa AI yorumuna bagliydi. Olculdu
(2026-11-22): ozette 384 sirket olculmus, 2026 3. ceyrek sayfasi
olan 341, mobil uygulamada bilanco ekrani 0.

Bu dosyanin korudugu sey tek cumleyle: BESLEME HESAP YAPMAZ. Oran,
degisim ve seri `haber_botu` tarafindaki tek kaynaklardan geliyor;
besleme yalnizca bicim veriyor. Bu depoda ayni degisim hesabi dort
kopyaya cikti ve biri duzeltilince oteki uc sessizce ayristi --
besleme besinci kopya olmayacak.
"""

import ast
import io
import json
import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_KOK = _SITE.parent
sys.path.insert(0, str(_SITE))
sys.path.insert(0, str(_KOK / "haber_botu"))
sys.path.insert(0, str(_KOK / "haber_botu" / "kaynak"))
sys.path.insert(0, str(_KOK / "haber_botu" / "analiz"))

import bilanco_ag          # noqa: E402
import bilanco_besleme     # noqa: E402
import bilanco_defteri     # noqa: E402
import mobil_besleme       # noqa: E402
import oranlar             # noqa: E402
import sektor_ozet         # noqa: E402

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


ORNEK = json.loads(
    io.open(_KOK / "haber_botu" / "kaynak" / "ornek_cekim.json",
            encoding="utf-8").read())

# Gercek cekimden bir defter KAYDI kuruluyor (dosyaya yazmadan).
_TAB = bilanco_defteri.suz(ORNEK["TUPRS"])
DEFTER_KAYDI = {
    "kod": "TUPRS",
    "cekildi": "2026-11-22T00:00:00Z",
    "ceyrek": bilanco_ag.VARSAYILAN_CEYREK,
    "sema": bilanco_defteri.sema(),
    "bitis": (_TAB.get("_seri_bitis") or [""])[0],
    "tablolar": _TAB,
}

SEKTOR = {
    "sektor": "Enerji",
    "donem": "2026 3. çeyrek",
    "sirket_sayisi": 2,
    "tazelendi": "2026-11-21T03:32:36+00:00",
    "medyan": {"brut_marj": 10.0, "net_marj": 5.0, "roe": 8.0,
               "cari_oran": 1.2, "borc_ozkaynak": 0.3},
    "sirket": {
        "TUPRS": {"brut_marj": 19.78, "net_marj": 14.47, "roe": 12.93,
                  "cari_oran": 1.38, "borc_ozkaynak": -0.38},
        "RUZYE": {"brut_marj": -46.09, "net_marj": -365.22},
    },
    "bitis": {"TUPRS": "2026-09-30", "RUZYE": "2026-09-30"},
}
SIRKETLER = {
    "TUPRS": {"unvan": "TÜPRAŞ A.Ş.", "sektor_tr": "Enerji",
              "alt_sektor": "Oil & Gas Refining"},
    "RUZYE": {"unvan": "RÜZGÂR ENERJİ A.Ş.", "sektor_tr": "Enerji",
              "alt_sektor": "Renewable Energy"},
}


def _kur(defterli=("TUPRS",)):
    def oku(kod, ceyrek, bitis=""):
        if kod.upper() in defterli:
            return DEFTER_KAYDI
        return None
    # HARITA IKI KADEMELI ve BILEREK IKI DONEM TASIYOR: dogru
    # donemin sayfasi secilmeli, otekini secmek sessiz bir yanlis
    # bag olurdu (olculdu: 379 bagin 316'si boyleydi).
    return bilanco_besleme.kur(
        {"Enerji": SEKTOR}, SIRKETLER,
        sayfalar={"TUPRS": {
            "2026 3. çeyrek": ("/analiz/tuprs-2026-3-ceyrek/",
                               "tuprs-2026-3-ceyrek"),
            "2026 2. çeyrek": ("/analiz/tuprs-2026-2-ceyrek/",
                               "tuprs-2026-2-ceyrek"),
        }},
        defter_oku=oku)


# ---------------------------------------------------------------------
# 1. DEFTERSIZ SIRKET BESLEMEDEN DUSMUYOR
# ---------------------------------------------------------------------
#
# "Veri var, bag yok" kusurunun tersi de bir kusur: defter kaydi
# olmayan sirketi tumden atlamak, oranlari BILINEN 384 sirketten
# yalnizca cekilenleri yayimlamak olurdu ve okur farki goremezdi.
_P = _kur()
es("iki sirket de beslemede", sorted(_P["sirket"]), ["RUZYE", "TUPRS"])
es("defterli sirket derin", _P["sirket"]["TUPRS"]["derinlik"], "defter")
es("deftersiz sirket ozet derinliginde",
   _P["sirket"]["RUZYE"]["derinlik"], "ozet")
es("deftersiz sirkette seviye yok", _P["sirket"]["RUZYE"]["olcumler"], [])
dogru("deftersiz sirkette oran VAR",
      len(_P["sirket"]["RUZYE"]["oranlar"]) >= 2)
es("sayfasi olmayan sirkette sayfa None",
   _P["sirket"]["RUZYE"]["sayfa"], None)
es("sayfasi olan sirkette adres tasiniyor",
   _P["sirket"]["TUPRS"]["sayfa"], "/analiz/tuprs-2026-3-ceyrek/")
# SLUG AYRICA TASINIYOR: uygulama yonlendiricisi site adresini
# kirpmak zorunda kalmasin. Adresi TypeScript'te kirpmak, adres
# duzenini iki yere yazmak demekti.
es("slug da tasiniyor",
   _P["sirket"]["TUPRS"]["sayfa_slug"], "tuprs-2026-3-ceyrek")
es("sayfasi olmayanda slug None", _P["sirket"]["RUZYE"]["sayfa_slug"], None)
dogru("liste ogesi slug tasiyor",
      "sayfa_slug" in mobil_besleme.bilanco_ogesi(_P["sirket"]["TUPRS"]))

# BASKA DONEMIN SAYFASI BAGLANMIYOR.
#
# A1CAP'in hem 2026-2 hem 2026-3 sayfasi var ve ilk yazim tek
# kademeli bir sozluk kullaniyordu: hangisi sonra geldiyse o
# kaliyordu. Bag CALISIYORDU, yalnizca bir onceki ceyregi aciyordu.
_P_eski = bilanco_besleme.kur(
    {"Enerji": SEKTOR}, SIRKETLER,
    sayfalar={"TUPRS": {"2026 2. çeyrek": (
        "/analiz/tuprs-2026-2-ceyrek/", "tuprs-2026-2-ceyrek")}},
    defter_oku=lambda k, c, bitis="": None)
es("donemi uyusmayan sayfa BAGLANMIYOR",
   _P_eski["sirket"]["TUPRS"]["sayfa"], None)

# Duz (tek kademeli) harita verilse de cokmemeli: eski bicimde
# cagiran biri yanlis bag degil HIC bag almali.
_P_duz = bilanco_besleme.kur(
    {"Enerji": SEKTOR}, SIRKETLER,
    sayfalar={"TUPRS": "/analiz/tuprs-2026-2-ceyrek/"},
    defter_oku=lambda k, c, bitis="": None)
es("tek kademeli harita yanlis bag URETMIYOR",
   _P_duz["sirket"]["TUPRS"]["sayfa"], None)

# ---------------------------------------------------------------------
# 2. HESAP BASKA YERDE -- BESLEME KOPYA DEGIL
# ---------------------------------------------------------------------
_T = _P["sirket"]["TUPRS"]
_olcum = {o["alan"]: o for o in _T["olcumler"]}
dogru("seviye tablosu dolu", len(_olcum) >= 10)

# Her degisim `oranlar._yuzde_degisim`in verdigi sayi olmali.
for _alan, _o in _olcum.items():
    es(f"{_alan} degisimi oranlar'dan",
       _o["degisim"],
       bilanco_besleme._sayi(oranlar._yuzde_degisim(_o["deger"], _o["once"])))

# ISARET DEGISIMINDE YUZDE URETILMIYOR -- "%1.897,5 geriledi" sinifi.
_net_borc = _olcum.get("net_borc")
dogru("net borc iki donemde de negatif (ornekte)",
      _net_borc and _net_borc["deger"] < 0 and (_net_borc["once"] or 0) < 0)
es("negatif tabanda yuzde uretilmiyor", _net_borc["degisim"], None)

# Kalem ADLARI sayfayi kuran sabitten geliyor.
import uret_bilanco_sayfa                                   # noqa: E402

_beklenen_ad = dict(uret_bilanco_sayfa.KALEMLER)
for _alan, _o in _olcum.items():
    es(f"{_alan} adi KALEMLER'den", _o["ad"], _beklenen_ad.get(_alan))

# ORAN ADLARI `sektor_ozet.ORANLAR`DAN ve SIRASI korunuyor.
_oran_sira = [o["alan"] for o in _T["oranlar"]]
es("oran sirasi sektor_ozet'ten",
   _oran_sira, [a for a, _ in sektor_ozet.ORANLAR if a in set(_oran_sira)])
for _o in _T["oranlar"]:
    es(f"{_o['alan']} adi sektor_ozet'ten",
       _o["ad"], dict(sektor_ozet.ORANLAR).get(_o["alan"]))

# HER ORANIN BIRIMI TANIMLI. Yuzde isaretini kat cinsinden bir orana
# koymak degeri yuzde birine indirir.
for _a, _ in sektor_ozet.ORANLAR:
    dogru(f"{_a} birimi tanimli", _a in bilanco_besleme.ORAN_BIRIMI)
es("cari oran KAT", bilanco_besleme.ORAN_BIRIMI["cari_oran"], "kat")
es("net marj YUZDE", bilanco_besleme.ORAN_BIRIMI["net_marj"], "%")

# DEFTER VARSA ORAN SIRKETIN KENDI VERISINDEN.
#
# Ozetteki oran o sektorun tazelendigi kosudan; defter bu sirketin
# kendi cekiminden. Ikisi ayrilabilir ve sayfa tarafinda tam bu
# kusur olculdu (258 sayfanin 203'u iki ayri donemi anlatiyordu).
import uret_bilanco                                         # noqa: E402

_simdi, _once, _eksik, _seri = bilanco_ag.donem_getir(
    "TUPRS", "2026 3. çeyrek", sektor_tr="Enerji", ciftli=True, seri=True,
    tablolar=_TAB)
_kendi = uret_bilanco._oranlari(_simdi)
for _o in _T["oranlar"]:
    if _o["alan"] in _kendi:
        es(f"{_o['alan']} defterden hesaplandi",
           _o["deger"], bilanco_besleme._sayi(_kendi[_o["alan"]]))
dogru("ozetteki oran ile defterden hesaplanan GERCEKTEN farkli "
      "(yoksa sinama hicbir sey gostermiyor)",
      abs(_kendi["brut_marj"] - 19.78) > 1e-6)

# MEDYAN YINE OZETTEN -- kesitsel, tek sirketten uretilemez.
for _o in _T["oranlar"]:
    es(f"{_o['alan']} medyani ozetten",
       _o["medyan"], SEKTOR["medyan"].get(_o["alan"]))

# MEDYAN YOKSA None, SIFIR DEGIL.
_P2 = bilanco_besleme.kur(
    {"Enerji": dict(SEKTOR, medyan={})}, SIRKETLER,
    defter_oku=lambda k, c, bitis="": None)
es("medyan yoksa None", _P2["sirket"]["TUPRS"]["oranlar"][0]["medyan"], None)

# SERI AKIS KALEMLERINI TASIYOR ve donem adlari ile bitis tarihleri
# birlikte geliyor (etiket veriyle karsilastirilabilsin).
dogru("seri en az iki donem", len(_T["seri"]) >= 2)
for _s in _T["seri"]:
    dogru("seri ogesinde bitis tarihi var", bool(_s["bitis"]))
    for _alan in bilanco_besleme.SERI_ALANLARI:
        dogru(f"seri {_alan} alani tanimli", _alan in _s)

# ---------------------------------------------------------------------
# 2b. BICIMLENDIRME BESLEMEDE, UYGULAMADA DEGIL
# ---------------------------------------------------------------------
#
# Ham sayiyi gonderip uygulamada bicimlendirmek, "474,39 milyar TL"
# kararini Python'da ve TypeScript'te AYRI AYRI vermek olurdu. Iki
# yer zamanla ayrisiyor ve ayrisma hicbir hata uretmiyor -- yalnizca
# ayni sirket iki yuzeyde iki farkli sayi gosteriyor.
import bicim                                               # noqa: E402

for _alan, _o in _olcum.items():
    es(f"{_alan} metni _mlr'den",
       _o["deger_metin"], uret_bilanco_sayfa._mlr(_o["deger"]))
    es(f"{_alan} onceki metni _mlr'den",
       _o["once_metin"],
       uret_bilanco_sayfa._mlr(_o["once"]) if _o["once"] is not None else "")
    es(f"{_alan} degisim metni bicim.yuzde'den (ISARETLI)",
       _o["degisim_metin"],
       bicim.yuzde(_o["degisim"], isaretli=True)
       if _o["degisim"] is not None else "")

dogru("seviye metni gercekten dolu",
      _olcum["hasilat"]["deger_metin"].endswith("milyar TL"))
dogru("artis metni isaret tasiyor",
      _olcum["hasilat"]["degisim_metin"].startswith("+"))
es("degisimi olmayan kalemde metin BOS", _net_borc["degisim_metin"], "")

for _o in _T["oranlar"]:
    _bek = (bicim.yuzde(_o["deger"]) if _o["birim"] == "%"
            else bicim.kat(_o["deger"]))
    es(f"{_o['alan']} metni bicim'den", _o["deger_metin"], _bek)
    es(f"{_o['alan']} medyan metni bicim'den",
       _o["medyan_metin"],
       ("" if _o["medyan"] is None else
        (bicim.yuzde(_o["medyan"]) if _o["birim"] == "%"
         else bicim.kat(_o["medyan"]))))

# SERI METNI AYRI SOZLUKTE -- ham alanla ayni duzeyde durmuyor.
for _s in _T["seri"]:
    dogru("seri ogesinde metin sozlugu var", isinstance(_s["metin"], dict))
    for _alan, _v in _s["metin"].items():
        es(f"seri {_alan} metni _mlr'den", _v,
           uret_bilanco_sayfa._mlr(_s[_alan]))

# LISTE METNI DETAYIN METNIYLE AYNI. Ikisi ayrisirsa liste ekrani ve
# detay ekrani ayni orani iki farkli yazar.
_D0 = mobil_besleme.bilanco_dosyalari(_P)
_liste_tuprs = [o for sf in range(
    1, _D0["/v1/bilanco.json"]["sayfa_sayisi"] + 1)
    for o in _D0[f"/v1/bilanco/sayfa-{sf}.json"]["ogeler"]
    if o["kod"] == "TUPRS"][0]
_oran_t = {o["alan"]: o for o in _T["oranlar"]}
es("liste net marj metni detayla ayni",
   _liste_tuprs["net_marj_metin"], _oran_t["net_marj"]["deger_metin"])
es("liste roe metni detayla ayni",
   _liste_tuprs["roe_metin"], _oran_t["roe"]["deger_metin"])
dogru("liste metni bos degil", bool(_liste_tuprs["net_marj_metin"]))

# ---------------------------------------------------------------------
# 3. AST -- BESLEMEDE HESAP YOK
# ---------------------------------------------------------------------
#
# Olcut METIN DEGIL AST: bu dosyanin ve modulun yorumlari "bolme"
# kelimesini zaten tasiyor.
#
# `_sayi` disinda bolme/carpma operatoru olmamali. `_sayi` yalnizca
# donusturuyor, hesap yapmiyor; o yuzden kural TUM modul icin
# geciyor -- bir istisna listesi, istisnanin buyumesine davettir.
_BB = ast.parse(io.open(_KOK / "haber_botu" / "bilanco_besleme.py",
                        encoding="utf-8").read())
# `pathlib` YOL BIRLESTIRMESI ARITMETIK DEGIL: `_KOK / "kaynak"`
# ayni `/` operatorunu kullaniyor. Olcut "dizge isleneni OLMAYAN
# bolme/carpma": gercek bir oran hesabinda hicbir islenen dizge
# olamaz. Ilk yazim bunu ayirmiyordu ve kendi `sys.path` kurulumunu
# "hesap" sayiyordu -- yani kural, korudugu seyle ilgisiz bir
# nedenden kirmizi doneyordu.
def _dizge_isleneni_var(d):
    return any(isinstance(y, ast.Constant) and isinstance(y.value, str)
               for y in (d.left, d.right))


_hesap = [f"{type(d.op).__name__}@{d.lineno}" for d in ast.walk(_BB)
          if isinstance(d, ast.BinOp)
          and isinstance(d.op, (ast.Div, ast.Mult, ast.Sub, ast.FloorDiv))
          and not _dizge_isleneni_var(d)]
es("beslemede aritmetik yok", _hesap, [])

# KURAL GERCEKTEN ELIYOR MU: ayni olcut, hesap YAPAN bir modulde
# dolu donmeli. Yoksa yukaridaki bos liste "kural calisiyor" degil
# "kural hicbir seyi gormuyor" anlamina gelirdi.
_ORAN_AGACI = ast.parse(
    io.open(_KOK / "haber_botu" / "analiz" / "oranlar.py",
            encoding="utf-8-sig").read())
_oran_hesap = [1 for d in ast.walk(_ORAN_AGACI)
               if isinstance(d, ast.BinOp)
               and isinstance(d.op, (ast.Div, ast.Mult, ast.Sub, ast.FloorDiv))
               and not _dizge_isleneni_var(d)]
dogru("olcut hesap yapan modulde ARITMETIK BULUYOR", len(_oran_hesap) > 5)

# Degisim `oranlar._yuzde_degisim` ile uretiliyor -- adi degisirse
# bu sinama kirmizi doner ve kopya yazilmadigi dogrulanir.
_cagrilar = {
    d.func.attr for d in ast.walk(_BB)
    if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
}
dogru("_yuzde_degisim cagriliyor", "_yuzde_degisim" in _cagrilar)

# BIRIM DIZGESI BESLEMEDE ELLE YAZILMAMIS: "milyar TL" soneki
# `uret_bilanco_sayfa._mlr` icinde duruyor ve sayfa da onu basiyor.
# Burada yazmak, sayfanin birimi degistigi gun uygulamanin eski
# birimi basmaya devam etmesi olurdu.
# DOC METNI DISARIDA: `_mlr`in kendi aciklamasi "474,39 milyar TL"
# ornegini zaten tasiyor. Aciklamayi kural ihlali saymak, gerekceyi
# yazmayi cezalandirmak olurdu -- ve bu depoda aciklama kodun bir
# parcasi. Olcut ISLEYEN dizge: bir deyim olarak tek basina duran
# dizge (doc metni) atlaniyor.
_doc = {id(d.value) for d in ast.walk(_BB)
        if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant)}
_birim_dizgesi = [d.value for d in ast.walk(_BB)
                  if isinstance(d, ast.Constant)
                  and isinstance(d.value, str)
                  and id(d) not in _doc
                  and ("milyar" in d.value or "TL" == d.value.strip())]
es("beslemede birim soneki elle yazilmamis", _birim_dizgesi, [])
dogru("oran hesabi devrediliyor (_oranlari)",
      "_oranlari" in _cagrilar or "_oranlari" in {
          d.func.id for d in ast.walk(_BB)
          if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)})

# ---------------------------------------------------------------------
# 4. DOSYA YOLLARI, SAYFALAMA, SURUM KAYDI
# ---------------------------------------------------------------------
_D = mobil_besleme.bilanco_dosyalari(_P, uretildi="2026-11-22T00:00:00Z")
dogru("dizin dosyasi var", "/v1/bilanco.json" in _D)
dogru("ilk liste sayfasi var", "/v1/bilanco/sayfa-1.json" in _D)
dogru("detay dosyasi var", "/v1/bilanco/tuprs.json" in _D)
es("dizin toplami", _D["/v1/bilanco.json"]["toplam"], 2)
es("defterli sayimi", _D["/v1/bilanco.json"]["defterli"], 1)

# LISTE SINIRSIZ OLMAYACAK. Bu depoda ayni esige uc kez carpildi ve
# ders her seferinde ayni: kusur kart sayisi degil, listenin
# sinirsiz olmasi.
dogru("liste sayfa boyu tanimli",
      isinstance(mobil_besleme.BILANCO_SAYFA_BOYU, int)
      and mobil_besleme.BILANCO_SAYFA_BOYU > 0)
_cok = bilanco_besleme.kur(
    {"Enerji": dict(
        SEKTOR,
        sirket={f"K{n:04d}": {"net_marj": 1.0} for n in range(200)},
        bitis={})},
    {f"K{n:04d}": {"unvan": f"Şirket {n}"} for n in range(200)},
    defter_oku=lambda k, c, bitis="": None)
_DC = mobil_besleme.bilanco_dosyalari(_cok)
_boy = mobil_besleme.BILANCO_SAYFA_BOYU
es("200 sirket sayfalara bolundu",
   _DC["/v1/bilanco.json"]["sayfa_sayisi"],
   (200 + _boy - 1) // _boy)
for _no in range(1, _DC["/v1/bilanco.json"]["sayfa_sayisi"] + 1):
    _sf = _DC[f"/v1/bilanco/sayfa-{_no}.json"]
    dogru(f"sayfa {_no} boyu asmiyor", len(_sf["ogeler"]) <= _boy)
es("son sayfanin sonraki'si None",
   _DC[f"/v1/bilanco/sayfa-{_DC['/v1/bilanco.json']['sayfa_sayisi']}.json"]
   ["sonraki"], None)

# BOS PAKET DE DOSYA URETIYOR: dosyanin olmamasi 404, iceriginin
# olmamasi "henuz veri yok" ekrani. Ikisi ayni sey degil.
_DB = mobil_besleme.bilanco_dosyalari(None)
dogru("bos pakette dizin yine var", "/v1/bilanco.json" in _DB)
dogru("bos pakette sayfa-1 yine var", "/v1/bilanco/sayfa-1.json" in _DB)
es("bos pakette toplam sifir", _DB["/v1/bilanco.json"]["toplam"], 0)
es("bos pakette defterli sifir", _DB["/v1/bilanco.json"]["defterli"], 0)

# LISTE OGESI DETAYIN TAMAMINI TASIMIYOR -- 384 sirketin seviye
# tablosunu liste icin indirmek ~2 MB olurdu.
_oge = _D["/v1/bilanco/sayfa-1.json"]["ogeler"][0]
dogru("liste ogesinde seviye tablosu YOK", "olcumler" not in _oge)
dogru("liste ogesinde seri YOK", "seri" not in _oge)
dogru("liste ogesi detaya isaret ediyor", _oge["dosya"].endswith(".json"))
dogru("liste ogesi derinligi bildiriyor", _oge["derinlik"] in ("ozet", "defter"))

# SURUM KAYDI -- istemci ilk burayi okuyor.
_HEPSI = mobil_besleme.uret(
    analizler=[], haberler=[], gostergeler=None,
    uretildi="2026-11-22T00:00:00Z", bilanco=_P)
_sur = _HEPSI[f"{mobil_besleme.ONEK}/surum.json"]["beslemeler"]
dogru("surum.json bilanco beslemesini bildiriyor", "bilanco" in _sur)
es("surum kaydi dizine isaret ediyor",
   _sur["bilanco"]["dizin"], f"{mobil_besleme.ONEK}/bilanco.json")
es("surum kaydi kayit sayisini bildiriyor", _sur["bilanco"]["kayit"], 2)
es("surum kaydi defterli sayisini bildiriyor",
   _sur["bilanco"]["defterli"], 1)
dogru("uret() bilanco dosyalarini da uretiyor",
      f"{mobil_besleme.ONEK}/bilanco/tuprs.json" in _HEPSI)

# BILANCO VERILMESE DE BESLEME COKMUYOR.
_HEPSI2 = mobil_besleme.uret(analizler=[], haberler=[], gostergeler=None,
                             uretildi="2026-11-22T00:00:00Z")
dogru("bilanco verilmezse dizin yine uretiliyor",
      f"{mobil_besleme.ONEK}/bilanco.json" in _HEPSI2)
es("bilanco verilmezse toplam sifir",
   _HEPSI2[f"{mobil_besleme.ONEK}/bilanco.json"]["toplam"], 0)

# ---------------------------------------------------------------------
# 5. INSA HATTI PAKETI GERCEKTEN GECIRIYOR MU
# ---------------------------------------------------------------------
#
# "Dugum eklendi, kural yazilmadi": besleme islevini yazmak, onun
# uretimde cagrildigini garanti etmiyor. `insa.py` paketi kurmali VE
# `mobil_besleme.uret`e GECIRMELI.
_INSA = ast.parse(io.open(_SITE / "insa.py", encoding="utf-8").read())
_kuran = [d for d in ast.walk(_INSA)
          if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
          and d.func.attr == "kur"
          and isinstance(d.func.value, ast.Name)
          and d.func.value.id.endswith("bb")]
dogru("insa.py bilanco paketini KURUYOR", len(_kuran) >= 1)

_gecen = []
for _c in ast.walk(_INSA):
    if (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Attribute)
            and _c.func.attr == "uret"
            and isinstance(_c.func.value, ast.Name)
            and _c.func.value.id == "mobil_besleme"):
        for _kw in _c.keywords:
            if _kw.arg == "bilanco":
                # DEGER BIR ADA BAGLI OLMALI: `bilanco=None` ya da
                # `bilanco={}` yazilsa anahtar durur, tasidigi sey
                # olmazdi -- bu depoda "garanti YARIM uygulanmis"
                # diye yazili sinif ve bir mutasyon tam buradan
                # kacmisti.
                _gecen += [n.id for n in ast.walk(_kw.value)
                           if isinstance(n, ast.Name)]
dogru("insa.py paketi mobil_besleme.uret'e GECIRIYOR", len(_gecen) >= 1)
dogru("gecirilen deger bir ADA bagli", any(_a for _a in _gecen))

# SAYFA HARITASININ OLCUTU URETENIN SABITINDEN.
#
# KURAL YALNIZCA BU HARITAYA: `insa.py` kategori dizgesini baska
# dokuz yerde zaten elle tasiyor (kategori eslestirme tablolari,
# ilgili akran suzgeci). Onlari bu turda degistirmek, olcmedigim bir
# davranisi degistirmek olurdu. Buradaki haritada ise dizge yazmak,
# baslik degistigi gun BUTUN sayfa baglantilarinin sessizce
# kaybolmasi demek -- ve sessiz, cunku besleme yine uretiliyor,
# yalnizca `sayfa` alanlari None oluyor.
_harita = [d for d in ast.walk(_INSA)
           if isinstance(d, (ast.DictComp, ast.For))
           and "BILANCO_KATEGORI" in ast.dump(d)]
dogru("sayfa haritasi BILANCO_KATEGORI sabitini kullaniyor", len(_harita) >= 1)
_harita_dizgesi = []
for _h in _harita:
    for _d in ast.walk(_h):
        if (isinstance(_d, ast.Constant) and isinstance(_d.value, str)
                and _d.value == "Bilanço Analizi"):
            _harita_dizgesi.append(_d.value)
es("sayfa haritasinda kategori dizgesi elle yazilmamis",
   _harita_dizgesi, [])

# HARITA DONEMI DE ANAHTAR YAPMALI.
#
# Olcut: haritayi kuran dongude `donem` ozniteligi GECMELI. Yoksa
# kod tek anahtar olur ve bir sirketin iki donem sayfasindan
# rastgele biri secilir -- uretimde tam bu oldu.
_donem_anahtari = any(
    isinstance(_d, ast.Attribute) and _d.attr == "donem"
    for _h in _harita for _d in ast.walk(_h))
dogru("sayfa haritasi donemi de anahtar yapiyor", _donem_anahtari)

for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
