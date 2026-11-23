"""bilanco_defteri.py testleri -- AGA CIKMAZ.

Bu dosyanin varlik sebebi iki olculmus kusur:

1. SUZGEC BIR ETIKETI KACIRDI. `donemi_kur` "Capital Expenditures"
   etiketini SATIR ICI bir dizgeyle okuyordu; defter suzgeci
   sabitlerden turetildigi icin onu gormedi ve defterden okunan
   veride `yatirim_harcamasi` SESSIZCE None geldi. Hata vermedi,
   cunku o alan zaten istege bagli. Alti sirketin hepsinde oldu.

   Buradaki koruma iki yonlu: GERCEK bir cekim ornegi uzerinde
   `donemi_kur(suz(t)) == donemi_kur(t)` ve AST ile `donemi_kur`
   icinde adsiz etiket dizgesi kalmadigi.

2. OZDESLIK DENETIMI HIC KOSMADI. `uret_bilanco` `_ham_bilanco`
   anahtarini okuyordu, hicbir yer yazmiyordu. Birim sinamasi
   `ozdeslik_denetimi`i TEK BASINA sinadigi icin yesildi; eksik olan
   fonksiyon degil ONA VERI GIDEN YOLDU. Burada yol sinaniyor:
   bozuk bir bilancoyla `sektor_isle` cagriliyor ve sirketin
   "özdeşlik" sebebiyle atlanmasi bekleniyor.
"""

import ast
import io
import json
import pathlib
import sys
import time

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))
sys.path.insert(0, str(_BURASI.parent))
sys.path.insert(0, str(_BURASI.parent / "analiz"))

import bilanco_ag          # noqa: E402
import bilanco_defteri     # noqa: E402

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


def _kaynak(ad):
    return io.open(_BURASI.parent / ad, encoding="utf-8-sig").read()


def _kaynak_kaynak(ad):
    return io.open(_BURASI / ad, encoding="utf-8-sig").read()


def _islev(agac, ad):
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return d
    return None


# ---------------------------------------------------------------------
# 1. ESDEGERLIK -- GERCEK CEKIM ORNEGI UZERINDE
# ---------------------------------------------------------------------
#
# ORNEK GERCEK, SENTETIK DEGIL. Kendi uydurdugum bir `tablolar` ancak
# AKLIMA GELEN etiketleri tasir -- tam olarak kacirdigim kusuru
# tekrarlardi. `ornek_cekim.json` kaynaktan gercekten cekilmis iki
# sirketi tasiyor: TUPRS (sanayi, butun kalemler dolu) ve ISCTR
# (banka, kalemlerin bir kismi hic gelmiyor).
ORNEK = json.loads(_kaynak_kaynak("ornek_cekim.json"))
dogru("ornek cekim iki sirket tasiyor", set(ORNEK) == {"TUPRS", "ISCTR"})

for _kod, _tab in ORNEK.items():
    _dar = bilanco_defteri.suz(_tab)
    # TURETME HER VARYANTTA KARSILASTIRILIYOR.
    #
    # Yalnizca ana donemi karsilastirmak yetmezdi: `_onceki` ve
    # `_g1.._g3` AYRI anahtarlardan okuyor ve suzgec onlari da
    # suzuyor. Capex kusuru ana donemde de vardi ama serinin
    # tamaminda da vardi -- biri gecip oteki kalabilirdi.
    es(f"{_kod} ana donem suzulse de ayni",
       bilanco_ag.donemi_kur(_dar), bilanco_ag.donemi_kur(_tab))
    es(f"{_kod} onceki yil suzulse de ayni",
       bilanco_ag.donemi_kur(_dar, onceki=True),
       bilanco_ag.donemi_kur(_tab, onceki=True))
    for _a in range(1, bilanco_ag.GERIYE_DONEM):
        es(f"{_kod} seri _g{_a} suzulse de ayni",
           bilanco_ag.donemi_kur(_dar, ek=f"_g{_a}"),
           bilanco_ag.donemi_kur(_tab, ek=f"_g{_a}"))

# ORNEGIN KENDISI BOS OLMAMALI -- yoksa yukaridaki esitlikler
# "bos == bos" diye gecer ve hicbir sey sinanmamis olur.
_t = bilanco_ag.donemi_kur(ORNEK["TUPRS"])
dogru("ornek gercekten veri tasiyor", len(_t) >= 10)
dogru("yatirim_harcamasi ornekte var", _t.get("yatirim_harcamasi") is not None)
dogru("favok ornekte var", _t.get("favok") is not None)

# SUZGEC GERCEKTEN SUZUYOR. Esitlikler suzgec HIC calismasa da
# gecerdi; `suz` kimlik islevi olmamali.
_ham_kalem = sum(len(v) for k, v in ORNEK["TUPRS"].items()
                 if isinstance(v, dict) and not k.startswith("_"))
_dar_kalem = sum(len(v) for k, v in
                 bilanco_defteri.suz(ORNEK["TUPRS"]).items()
                 if isinstance(v, dict) and not k.startswith("_"))
dogru(f"suzgec kalem sayisini dusuruyor ({_ham_kalem} -> {_dar_kalem})",
      _dar_kalem < _ham_kalem)

# ---------------------------------------------------------------------
# 2. ETIKET KUMESI TURETILIYOR, ELLE YAZILMIYOR
# ---------------------------------------------------------------------
_ET = bilanco_defteri.etiketler()
for _alan, _sayfa, _etiket in bilanco_ag.ESLESME:
    dogru(f"eslesme etiketi suzgecte: {_etiket}", _etiket in _ET)
for _sabit in (bilanco_ag.NET_NAKIT_ETIKETI, bilanco_ag.AMORTISMAN_ETIKETI,
               bilanco_ag.CAPEX_ETIKETI):
    dogru(f"turetilen alan etiketi suzgecte: {_sabit}", _sabit in _ET)
for _sabit in bilanco_ag.OZDESLIK_ETIKETLERI:
    dogru(f"ozdeslik etiketi suzgecte: {_sabit}", _sabit in _ET)

# SEMA ETIKET KUMESINE BAGLI. Degismezse eslesme buyudugunde eski
# kayitlar gecerli sayilir ve okuyan taraf eksik alanla calisir.
_s1 = bilanco_defteri.sema()
_gercek_eslesme = bilanco_ag.ESLESME
try:
    bilanco_ag.ESLESME = _gercek_eslesme + (("yeni", "gelir", "Yeni Kalem"),)
    es("eslesme buyurse sema degisiyor", bilanco_defteri.sema() != _s1, True)
    dogru("yeni etiket suzgece KENDILIGINDEN giriyor",
          "Yeni Kalem" in bilanco_defteri.etiketler())
finally:
    bilanco_ag.ESLESME = _gercek_eslesme
es("sema geri donuyor", bilanco_defteri.sema(), _s1)

# ---------------------------------------------------------------------
# 3. AST -- `donemi_kur` ICINDE ADSIZ ETIKET DIZGESI KALMASIN
# ---------------------------------------------------------------------
#
# OLCUT METIN DEGIL AST. Bu dosyadaki yorumlar "Capital Expenditures"
# dizgesini zaten tasiyor; metin aramasi kendi yorumunu bulurdu.
#
# IKI AYRI KURAL, CUNKU IKI AYRI KUSUR SINIFI VAR:
#
#   A) KALEM ETIKETI adsiz kalirsa defter suzgeci onu gormez ve
#      defterden okunan veride alan SESSIZCE bos kalir (capex).
#      Olcut: `tablolar.get(sayfa)` SONUCU uzerinden yapilan
#      `.get(X)` cagrisinda X dizge sabiti olamaz.
#
#   B) SAYFA ANAHTARI `_ek` tasimazsa hangi donem istenirse istensin
#      BU donem okunur (amortisman -> FAVOK). Olcut: dogrudan
#      `tablolar.get(X)` cagrisinda X dizge sabiti olamaz; `_ek` ile
#      birlesmis olmali.
#
# Kendi cikti sozlugunu okuyan `cikti.get("faaliyet_kari")` iki
# kuralin da DISINDA -- o kaynak etiketi degil, hattin alan adi.
_AG = ast.parse(_kaynak("kaynak/bilanco_ag.py"))
_dk = _islev(_AG, "donemi_kur")
dogru("donemi_kur bulundu", _dk is not None)


def _tablolar_get_mi(c):
    """`tablolar.get(...)` cagrisi mi (dogrudan, sonucu degil)?"""
    return (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "get" and isinstance(c.func.value, ast.Name)
            and c.func.value.id == "tablolar")


_adsiz_etiket = []
_eksiz_sayfa = []
if _dk is not None:
    for _c in ast.walk(_dk):
        if not (isinstance(_c, ast.Call)
                and isinstance(_c.func, ast.Attribute)
                and _c.func.attr == "get"):
            continue
        _sabitler = [a.value for a in _c.args
                     if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if _tablolar_get_mi(_c):
            # B: sayfa anahtari. `_ek` ile birlesmeli.
            _eksiz_sayfa += _sabitler
            continue
        _alici = {n.id for n in ast.walk(_c.func.value)
                  if isinstance(n, ast.Name)}
        if "tablolar" in _alici:
            # A: kalem etiketi.
            _adsiz_etiket += _sabitler
es("donemi_kur icinde adsiz kalem etiketi yok", _adsiz_etiket, [])
es("donemi_kur'da sayfa anahtari `_ek` tasimadan okunmuyor",
   _eksiz_sayfa, [])

# `_ek` GERCEKTEN KULLANILIYOR MU. Yukaridaki kural "dizge sabiti
# yok" diyor; sabit yerine baska bir degisken konsa yine gecerdi.
_ek_kullanan = sum(
    1 for _c in ast.walk(_dk or _AG)
    if _tablolar_get_mi(_c) and _c.args
    and "_ek" in {n.id for n in ast.walk(_c.args[0])
                  if isinstance(n, ast.Name)})
dogru(f"her sayfa okumasi `_ek` ile birlesiyor ({_ek_kullanan})",
      _ek_kullanan >= 4)

# FAVOK ONCEKI DONEMDE DE O DONEMIN AMORTISMANINI KULLANIYOR.
# AST yukarida bicimi tutuyor; burada SONUC olculuyor.
_fx = json.loads(json.dumps(ORNEK["TUPRS"]))
_fx["nakit_onceki"][bilanco_ag.AMORTISMAN_ETIKETI] = 1.0
_fx["nakit"][bilanco_ag.AMORTISMAN_ETIKETI] = 999_000_000_000.0
_once = bilanco_ag.donemi_kur(_fx, onceki=True)
_fo = (_fx.get("gelir_onceki") or {}).get("Operating Income")
es("onceki yil FAVOK'u ONCEKI yilin amortismaniyla kuruluyor",
   _once.get("favok"), _fo + 1.0)

# ---------------------------------------------------------------------
# 4. GECERSIZLIK KURALLARI
# ---------------------------------------------------------------------
import tempfile                                            # noqa: E402

_GERCEK_KOK = bilanco_defteri.KOK
bilanco_defteri.KOK = pathlib.Path(tempfile.mkdtemp()) / "defter"

_T = ORNEK["TUPRS"]
_BITIS = (_T.get("_seri_bitis") or [""])[0]
dogru("ornegin donem bitisi biliniyor", bool(_BITIS))

es("kayit yoksa None", bilanco_defteri.oku("YOKKK", 1), None)

_yol = bilanco_defteri.yaz("TUPRS", _T, 1)
dogru("yazildi", _yol is not None and _yol.exists())
dogru("gecerli kayit okunuyor",
      bilanco_defteri.oku("TUPRS", 1, bitis=_BITIS) is not None)
es("ceyrek farkliysa None", bilanco_defteri.oku("TUPRS", 2), None)
es("bitis farkliysa None",
   bilanco_defteri.oku("TUPRS", 1, bitis="1999-12-31"), None)
es("bitis verilmezse donem denetlenmiyor",
   bilanco_defteri.oku("TUPRS", 1) is not None, True)
es("yas sinirini asan kayit None",
   bilanco_defteri.oku("TUPRS", 1, azami_gun=-1), None)
es("kod kucuk harfle de okunuyor",
   bilanco_defteri.oku("tuprs", 1) is not None, True)

# SEMA DEGISIKLIGI KAYDI DUSURUYOR.
_kayit = json.loads(bilanco_defteri.yol("TUPRS").read_text(encoding="utf-8"))
_kayit["sema"] = "baskasema"
bilanco_defteri.yol("TUPRS").write_text(
    json.dumps(_kayit, ensure_ascii=False), encoding="utf-8")
es("sema uyusmazsa None", bilanco_defteri.oku("TUPRS", 1), None)

# BOZUK JSON COKERTMEZ.
bilanco_defteri.yol("BOZUK").parent.mkdir(parents=True, exist_ok=True)
bilanco_defteri.yol("BOZUK").write_text("{ bu json degil", encoding="utf-8")
es("bozuk JSON None donuyor", bilanco_defteri.oku("BOZUK", 1), None)

# BOS CEKIM YAZILMIYOR -- yoksa sayfa adimi "veri var" sanip aga
# dusmez ve sayfa HIC uretilmez.
es("bos cekim yazilmaz", bilanco_defteri.yaz("BOSS", {}, 1), None)
es("yalnizca ust veri tasiyan cekim yazilmaz",
   bilanco_defteri.yaz("BOSS2", {"_mali": {"yil_sonu_ayi": 12}}, 1), None)
es("bos kalem sozlugu tasiyan cekim yazilmaz",
   bilanco_defteri.yaz("BOSS3", {"gelir": {}}, 1), None)

# `_ham_bilanco` DEFTERE GIRMIYOR (buyuk ve yalnizca cekim aninda
# gerekli), ama YENI bir ust veri anahtari KENDILIGINDEN giriyor --
# blok listesi, beyaz liste degil.
_ek = dict(_T)
_ek["_ham_bilanco"] = {"Total Assets": [1.0, 2.0]}
_ek["_yeni_ust_veri"] = {"bir": 1}
bilanco_defteri.yaz("EKLI", _ek, 1)
_okunan = bilanco_defteri.kayit_oku("EKLI")["tablolar"]
dogru("_ham_bilanco deftere yazilmiyor", "_ham_bilanco" not in _okunan)
dogru("yeni ust veri anahtari kendiliginden tasiniyor",
      _okunan.get("_yeni_ust_veri") == {"bir": 1})

dogru("kodlar() kayitlari listeliyor",
      "EKLI" in bilanco_defteri.kodlar())

# ICERIK AYNIYSA DOSYAYA DOKUNULMUYOR.
#
# `cekildi` damgasi her kosuda degisiyor; kayit her kosuda yeniden
# yazilsa git 96 dosyayi degismis gorurdu, icerik ayni oldugu halde.
# Bir ceyrekte ~60 kosu x ~0,5 MB = 30 MB depo gecmisi, hicbiri yeni
# bilgi tasimadan.
import time as _t                                           # noqa: E402

bilanco_defteri.yaz("AYNI", _T, 1)
_ilk = bilanco_defteri.yol("AYNI").stat().st_mtime_ns
_damga = bilanco_defteri.kayit_oku("AYNI")["cekildi"]
_t.sleep(0.02)
bilanco_defteri.yaz("AYNI", _T, 1)
es("ayni icerik dosyayi DEGISTIRMIYOR",
   bilanco_defteri.yol("AYNI").stat().st_mtime_ns, _ilk)
es("damga da korunuyor (veri ne zaman GORULDU)",
   bilanco_defteri.kayit_oku("AYNI")["cekildi"], _damga)

# DEGISEN ICERIK YAZILIYOR -- yoksa kural "hic yazma"ya donerdi.
_degisik = json.loads(json.dumps(_T))
_degisik["gelir"]["Revenue"] = 1.0
bilanco_defteri.yaz("AYNI", _degisik, 1)
es("degisen icerik YAZILIYOR",
   (bilanco_defteri.kayit_oku("AYNI")["tablolar"]["gelir"]["Revenue"]), 1.0)

bilanco_defteri.KOK = _GERCEK_KOK

# ---------------------------------------------------------------------
# 5. AKIS -- DEFTER GERCEKTEN BAGLI MI
# ---------------------------------------------------------------------
#
# "Dugum eklendi, kural yazilmadi" sinifi: modulu yazmak onun
# cagrildigini GARANTI ETMIYOR. Asagidaki AST sinamalari defterin
# iki ucunu da bagli tutuyor.
_VERI = ast.parse(_kaynak("uret_bilanco.py"))
_si = _islev(_VERI, "sektor_isle")
dogru("uret_bilanco.sektor_isle bulundu", _si is not None)
_yazar = [c for c in ast.walk(_si or _VERI)
          if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
          and c.func.attr == "yaz"
          and isinstance(c.func.value, ast.Name)
          and c.func.value.id == "bilanco_defteri"]
dogru("veri adimi deftere YAZIYOR", len(_yazar) >= 1)

_ozd = [c for c in ast.walk(_si or _VERI)
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
        and c.func.attr == "ozdeslik_denetimi"]
dogru("veri adimi ozdeslik denetimini CAGIRIYOR", len(_ozd) >= 1)

# `ara_donem` `_ham_bilanco` URETMELI -- yoksa yukaridaki cagri
# yine bos sozlukle calisir ve hicbir sey denetlemez.
_ad = _islev(_AG, "ara_donem")
dogru("ara_donem bulundu", _ad is not None)
_ham_yazim = []
for _c in ast.walk(_ad or _AG):
    if isinstance(_c, ast.Assign):
        for _h in _c.targets:
            if (isinstance(_h, ast.Subscript)
                    and isinstance(_h.slice, ast.Constant)
                    and _h.slice.value == "_ham_bilanco"):
                _ham_yazim.append(_h)
dogru("ara_donem _ham_bilanco URETIYOR", len(_ham_yazim) >= 1)

_SAYFA = ast.parse(_kaynak("uret_bilanco_sayfa.py"))
_pi = _islev(_SAYFA, "sirket_isle")
dogru("uret_bilanco_sayfa.sirket_isle bulundu", _pi is not None)
_okur = [c for c in ast.walk(_pi or _SAYFA)
         if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
         and c.func.attr == "oku"
         and isinstance(c.func.value, ast.Name)
         and c.func.value.id == "bilanco_defteri"]
dogru("sayfa adimi defteri OKUYOR", len(_okur) >= 1)

# OKUMAK YETMEZ: okunan sey `donem_getir`e GECMELI.
#
# ILK YAZIM "tablolar= anahtar kelimesi var mi" diye bakiyordu ve
# MUTASYON KACTI (M5): `tablolar=None` yazildiginda sinama yesil
# kaldi. Anahtar duruyor, tasidigi sey yok -- bu depoda "garanti
# YARIM uygulanmis" diye yazili sinif, bu kez korumanin kendisinde.
#
# OLCUT ARTIK BAG: `bilanco_defteri.oku(...)` sonucunun BAGLANDIGI
# ad, `tablolar=` argumaninda GECMEK zorunda.
_defter_adlari = set()
for _c in ast.walk(_pi or _SAYFA):
    if isinstance(_c, ast.Assign):
        for _o in ast.walk(_c.value):
            if (isinstance(_o, ast.Call)
                    and isinstance(_o.func, ast.Attribute)
                    and _o.func.attr == "oku"
                    and isinstance(_o.func.value, ast.Name)
                    and _o.func.value.id == "bilanco_defteri"):
                for _h in _c.targets:
                    if isinstance(_h, ast.Name):
                        _defter_adlari.add(_h.id)
dogru("defter okumasi bir ADA baglaniyor", bool(_defter_adlari))

_gecen = []
for _c in ast.walk(_pi or _SAYFA):
    if (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Attribute)
            and _c.func.attr == "donem_getir"):
        for _kw in _c.keywords:
            if _kw.arg != "tablolar":
                continue
            _adlar = {n.id for n in ast.walk(_kw.value)
                      if isinstance(n, ast.Name)}
            if _adlar & _defter_adlari:
                _gecen.append(_kw)
dogru("defterden okunan veri donem_getir'e GECIYOR", len(_gecen) >= 1)

# AYNI AD NEZAKET KOSULUNU DA BESLEMELI: `DEFTERDEN` kumesine
# ekleme, defter okumasinin SONUCUNA bagli olmali. `DEFTERDEN.add`
# kosulsuz yapilsa, aga dusulen sirkette de bekleme atlanirdi.
_dolduran = False
for _c in ast.walk(_pi or _SAYFA):
    if isinstance(_c, ast.If) and (
            {n.id for n in ast.walk(_c.test) if isinstance(n, ast.Name)}
            & _defter_adlari):
        for _g in ast.walk(_c):
            if (isinstance(_g, ast.Call)
                    and isinstance(_g.func, ast.Attribute)
                    and _g.func.attr == "add"
                    and isinstance(_g.func.value, ast.Name)
                    and _g.func.value.id == "DEFTERDEN"):
                _dolduran = True
dogru("DEFTERDEN yalnizca defter okunduysa doluyor", _dolduran)

# `donem_getir` verilen tablolari KULLANMALI -- aga cikmamali.
_dg = _islev(_AG, "donem_getir")
_kosullu = []
for _c in ast.walk(_dg or _AG):
    if isinstance(_c, ast.If):
        _metin = ast.dump(_c.test)
        if "tablolar" in _metin:
            for _g in ast.walk(_c):
                if (isinstance(_g, ast.Call)
                        and isinstance(_g.func, ast.Name)
                        and _g.func.id == "ara_donem"):
                    _kosullu.append(_g)
dogru("donem_getir ara_donem'i KOSULLU cagiriyor", len(_kosullu) >= 1)

# NEZAKET BEKLEMESI KOSULSUZ KALMALI -- DEFTERDEN OKUNSA BILE.
#
# Ilk yazim tersini sinaiyordu ("istek atilmadiysa bekleme") ve
# `test_bilanco_penceresi.py` onu reddetti: o kuralin olcutu
# "kaynaga giden dongude KOSULSUZ bekleme" ve uc ayri mutasyonla
# kazanilmis. Otuz saniye icin (60 sirket x 0,5 sn) bir korumayi
# gevsetmek dogru takas degil.
#
# Bu iddia TERS YONE bakiyor: `ara_ver` cagrisi bir `if` icine
# alinirsa kirmizi doner.
_kosullu_bekleme = []
for _c in ast.walk(_SAYFA):
    if not isinstance(_c, ast.If):
        continue
    for _g in ast.walk(_c):
        if (isinstance(_g, ast.Call)
                and isinstance(_g.func, ast.Attribute)
                and _g.func.attr == "ara_ver"):
            _kosullu_bekleme.append(_c.lineno)
es("ara_ver KOSULA BAGLANMAMIS", _kosullu_bekleme, [])

# ---------------------------------------------------------------------
# 5a. "AGA DUSULEN" SAYISI GERCEKTEN ISLENENDEN TURETILMELI
# ---------------------------------------------------------------------
#
# OLCULDU (kosu #123, 2026-11-23): gunluk
#
#     defterden okunan: 0 şirket (ağa düşülen: 389)
#
# yaziyordu. O kosuda 389 sirketin HEPSI "zaten yayımlanmış" diye
# `sirket_isle`e girmeden elendi -- tek bir istek atilmadi. Sayi
# `yazilan + atlanan - len(DEFTERDEN)` ile hesaplandigi icin,
# yapilmamis 389 istegi yapilmis gibi bildiriyordu.
#
# Kendi koydugum olcum, olcmedigi seyi raporladi. Sayinin VAR ve
# inandirici olmasi, yoklugundan daha kotu.
#
# OLCUT: "aga dusulen" ifadesi `atlanan`a DAYANMAMALI -- o degisken
# iki ayri eleme turunu (cekim denenmeden atlanan / cekim sonrasi
# atlanan) ayni torbaya koyuyor.
_aga_dusulen = []
for _c in ast.walk(_SAYFA):
    if not (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Name)
            and _c.func.id == "print"):
        continue
    _metin = ast.dump(_c)
    if "ağa düşülen" not in _metin:
        continue
    _adlar = {n.id for n in ast.walk(_c) if isinstance(n, ast.Name)}
    _aga_dusulen.append(_adlar)
dogru("'ağa düşülen' satiri bulundu", len(_aga_dusulen) == 1)
for _adlar in _aga_dusulen:
    es("'ağa düşülen' sayisi `atlanan`a DAYANMIYOR",
       "atlanan" in _adlar, False)
    dogru("'ağa düşülen' sayisi ISLENEN sayisindan turetiliyor",
          "islenen" in _adlar)

# `islenen` SAYACI GERCEKTEN `sirket_isle`IN YANINDA ARTIYOR.
# Dongunun basinda artsaydi yine atlananlari sayardi.
_sayac_dogru = False
for _c in ast.walk(_SAYFA):
    if not isinstance(_c, ast.For):
        continue
    _govde = list(_c.body)
    for _i, _d in enumerate(_govde):
        _artis = (isinstance(_d, ast.AugAssign)
                  and isinstance(_d.target, ast.Name)
                  and _d.target.id == "islenen")
        if not _artis:
            continue
        # Hemen SONRAKI ifade `sirket_isle` cagrisini tasimali.
        for _sonraki in _govde[_i + 1:_i + 2]:
            if "sirket_isle" in ast.dump(_sonraki):
                _sayac_dogru = True
dogru("`islenen` tam `sirket_isle` cagrisindan once artiyor", _sayac_dogru)

# ---------------------------------------------------------------------
# 5b. TAZELEME ADIMI DA DEFTERDEN OKUYOR
# ---------------------------------------------------------------------
#
# Bu adimin tikandigi yer olculmustu (kosu #117): goc kuyrugundaki
# 145 sayfanin 145'i "KAYNAK VERMEDI" dondu ve gercek verim ~0,2
# sayfa/kosu cikti. Sebep veri eksikligi degil, ayni kosuda ayni
# sayfanin iki kez istenmesiydi.
_TAZELE = ast.parse(_kaynak("bilanco_tazele.py"))
_st = _islev(_TAZELE, "sayfa_tazele")
dogru("bilanco_tazele.sayfa_tazele bulundu", _st is not None)

_t_adlari = set()
for _c in ast.walk(_st or _TAZELE):
    if isinstance(_c, ast.Assign):
        for _o in ast.walk(_c.value):
            if (isinstance(_o, ast.Call)
                    and isinstance(_o.func, ast.Attribute)
                    and _o.func.attr == "oku"
                    and isinstance(_o.func.value, ast.Name)
                    and _o.func.value.id == "bilanco_defteri"):
                for _h in _c.targets:
                    if isinstance(_h, ast.Name):
                        _t_adlari.add(_h.id)
dogru("tazeleme defteri OKUYOR", bool(_t_adlari))

_t_gecen = []
for _c in ast.walk(_st or _TAZELE):
    if (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Attribute)
            and _c.func.attr == "donem_getir"):
        for _kw in _c.keywords:
            if _kw.arg != "tablolar":
                continue
            if {n.id for n in ast.walk(_kw.value)
                    if isinstance(n, ast.Name)} & _t_adlari:
                _t_gecen.append(_kw)
dogru("tazelemede defter verisi donem_getir'e GECIYOR", len(_t_gecen) >= 1)

# BITIS HARITASI OLMADAN DEFTER OKUNMAZ: gecerlilik olcutu donem
# bitisinin esitligi ve harita verilmezse eski davranis (aga cikis)
# korunuyor. `main` haritayi GECIRMELI -- yoksa uretimde defter hic
# okunmaz ve bu bolumun tamami yesil ama ETKISIZ olur.
_t_main = _islev(_TAZELE, "main")
_bitis_gecen = []
for _c in ast.walk(_t_main or _TAZELE):
    if (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Name)
            and _c.func.id == "sayfa_tazele"):
        _bitis_gecen += [kw.arg for kw in _c.keywords if kw.arg == "bitisler"]
dogru("main sayfa_tazele'ye bitis haritasini GECIRIYOR",
      len(_bitis_gecen) >= 1)

# HARITA `baglam_kur`DAN GELIYOR -- ikinci bir harita kurulmuyor.
_bk = _islev(_TAZELE, "baglam_kur")
dogru("baglam_kur donem bitislerini de donduruyor",
      any(isinstance(_c, ast.Return) and isinstance(_c.value, ast.Tuple)
          and len(_c.value.elts) == 3
          for _c in ast.walk(_bk or _TAZELE)))

# ---------------------------------------------------------------------
# 6. OZDESLIK DENETIMI GERCEKTEN ELIYOR MU -- AKIS UCTAN UCA
# ---------------------------------------------------------------------
#
# AST yukarida cagrinin VARLIGINI tutuyor; burada ETKISI olculuyor.
# Ag yok: `ara_donem` yerine ornekten uretilen sahte bir cekim
# konuyor ve bilanco BILEREK bozuluyor.
import uret_bilanco                                        # noqa: E402

_gercek_ara_donem = bilanco_ag.ara_donem
_gercek_sektordeki = uret_bilanco.sektordeki
_gercek_nobet = uret_bilanco.nobet_bitisleri
_gercek_hedef = uret_bilanco.HEDEF
_gercek_defter_kok = bilanco_defteri.KOK


def _sahte_cekim(bozuk):
    t = json.loads(json.dumps(ORNEK["TUPRS"]))
    ham = {e: [t["bilanco"].get(e)] for e in bilanco_ag.OZDESLIK_ETIKETLERI
           if t["bilanco"].get(e) is not None}
    # Ozdeslik etiketlerinin bir kismi ESLESMEDE yok; ornek cekim
    # tamamini tasiyor, `t["bilanco"]` suzulmemis haliyle duruyor.
    if bozuk:
        ham["Total Liabilities & Equity"] = [
            (ham.get("Total Assets") or [1.0])[0] * 3.0]
    t["_ham_bilanco"] = ham
    return t


try:
    bilanco_defteri.KOK = pathlib.Path(tempfile.mkdtemp()) / "defter2"
    uret_bilanco.sektordeki = lambda s: [("TUPRS", {"unvan": "T", "kod": "TUPRS"})]
    uret_bilanco.nobet_bitisleri = lambda: {}
    bilanco_ag.ara_ver = lambda: 0.0
    bilanco_ag._uyu = lambda s: None
    time_sleep = time.sleep
    time.sleep = lambda s: None

    bilanco_ag.ara_donem = lambda kod, ceyrek=1, istemci=None: _sahte_cekim(False)
    _iyi = uret_bilanco.sektor_isle("Enerji", "T", ceyrek=1)
    dogru("tutan bilanco olculuyor", "TUPRS" in (_iyi.get("sirket") or {}))
    dogru("tutan bilanco deftere yaziliyor",
          bilanco_defteri.kayit_oku("TUPRS") is not None)

    bilanco_defteri.KOK = pathlib.Path(tempfile.mkdtemp()) / "defter3"
    bilanco_ag.ara_donem = lambda kod, ceyrek=1, istemci=None: _sahte_cekim(True)
    _koo = uret_bilanco.sektor_isle("Enerji", "T", ceyrek=1)
    _atlanan = dict(_koo.get("atlanan") or [])
    dogru("BOZUK bilanco OLCULMUYOR", "TUPRS" not in (_koo.get("sirket") or {}))
    dogru("atlama sebebi ozdeslik",
          "özdeşlik" in (_atlanan.get("TUPRS") or ""))
    # BOZUK VERI DEFTERE DE GIRMIYOR: girerse sayfa adimi onu
    # agdan gelmis gibi okur ve denetimi atlar.
    dogru("bozuk bilanco deftere YAZILMIYOR",
          bilanco_defteri.kayit_oku("TUPRS") is None)
finally:
    bilanco_ag.ara_donem = _gercek_ara_donem
    uret_bilanco.sektordeki = _gercek_sektordeki
    uret_bilanco.nobet_bitisleri = _gercek_nobet
    uret_bilanco.HEDEF = _gercek_hedef
    bilanco_defteri.KOK = _gercek_defter_kok
    time.sleep = time_sleep

for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
