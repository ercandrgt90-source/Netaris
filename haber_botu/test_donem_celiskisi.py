# -*- coding: utf-8 -*-
"""SAYFANIN BASLIGI KENDI TABLOSUYLA CELISMEMELI.

KUSUR (olculdu 2026-11-01, YAYINDAYDI)
--------------------------------------
Bilanco sayfasinda ETIKET ile VERI iki ayri kaynaktan geliyor:

    etiket : `kiyas_kumesi` -> `sektor_ozet.json` -> `bitis[kod]`
    veri   : `bilanco_ag.donem_getir` -> kaynak, HER ZAMAN en yeni

Ikisi hicbir yerde karsilastirilmiyordu. Ozet bir kosu geride
kalinca sayfa bir donemi SOYLUYOR, baska bir donemi GOSTERIYOR:

    2026-2-ceyrek-akbnk.md
      baslik     AKBANK T.A.Ş. 2026 2. çeyrek bilanço analizi
      seri basi  2026 3. çeyrek      <- sayfanin kendi tablosu
      ozet       Q2 yorumu           <- sakli AI metni aynen geri

331 bilanco sayfasinin BESI boyleydi ve besinin de dogru etiketli
bir IKIZI vardi:

    AGESA, AKBNK, ANHYT   Q3 verisi, "2026 2. çeyrek" basligi
    ALGYO                 Q1 verisi, "2026 2. çeyrek" basligi
    MAVI             mayıs–temmuz verisi, "2026 2. çeyrek" basligi

ALGYO YONU TERSINE CEVIRIYOR ve tani bu yuzden kesin: orada ozet
veriden ILERIDEYDI. Yani kusur "kaynak ozetten yeni" degil, "ikisi
hic karsilastirilmiyor".

NEDEN VAR OLAN KORUMA YAKALAMADI
--------------------------------
Ayni kusur sinifi bir kez daha yayina cikti (ASUZU, 2026-10-13) ve o
zaman eklenen kapi SAYFA ile OZETI karsilastiriyor. Bunu yapisal
olarak yakalayamaz: AKBNK'de sayfa Q2, ozet Q2 -- o kapi aciliyor.
Celisen ucuncu taraf VERININ KENDISI.

Bu dosya kurali UC KATTA tutuyor:
  1. olcut    -- `bilanco_denetim.donem_etiketi_celiskisi` besinin
                 bicimini de goruyor, dogru etiketli ikizlerde
                 sessiz kaliyor;
  2. davranis -- IKI uretici yol (yeni sayfa ve tazeleme) celiskiyi
                 gorunce YAZMIYOR; kuyruk onlari TUTMUYOR;
  3. mekanik  -- denetim seri basligini URETICIDEN okuyor, kendi
                 kopyasini tasimiyor.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bilanco_denetim as bd                          # noqa: E402
import bilanco_tazele as T                            # noqa: E402
import uret_bilanco_sayfa as U                        # noqa: E402

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


def sayfa(donem: str, seri_ilk: str = "", kod: str = "AKBNK",
          yorum: str = "Hasılat arttı, kâr düştü.") -> str:
    """Uretimin yazdigi bicimde bir bilanco sayfasi.

    `seri_ilk` bos ise "Son dort donem" bolumu HIC yazilmiyor --
    goc henuz bitmedigi icin 169 gercek sayfa boyle.
    """
    s = ["---",
         f"slug: {kod.lower()}-x",
         f"baslik: {kod} {donem} bilanço analizi",
         f"ozet: {yorum}",
         f"sirket: {kod} A.Ş.",
         f"kod: {kod}",
         f"donem: {donem}",
         "kategori: Bilanço Analizi",
         "sektor: Finans",
         "tarih: 2026-08-28",
         "---",
         "",
         "## Özet",
         "",
         yorum,
         "",
         f"## {donem} dönemi ölçümleri",
         "",
         "| Kalem | Değer |",
         "| --- | ---: |",
         "| Hasılat | 56,60 milyar TL |",
         "| Net kâr | 11,60 milyar TL |",
         ""]
    if seri_ilk:
        s += [U.SERI_BASLIGI, "",
              f"| Kalem (milyar TL) | {seri_ilk} | 2026 1. çeyrek |",
              "| --- | ---: | ---: |",
              "| Hasılat | 56,60 | 63,61 |",
              ""]
    return "\n".join(s)


print(__doc__.splitlines()[0])
print("")

# ---------------------------------------------------------------
print("1) OLCUT -- yayindaki bes sayfanin bicimi")

# Besinin de bicimi AYNI: on bilgi bir donem, seri basi baskasi.
for _ad, _bas, _seri in (
        ("AGESA/AKBNK/ANHYT", "2026 2. çeyrek", "2026 3. çeyrek"),
        ("ALGYO (ozet veriden ILERIDE)", "2026 2. çeyrek",
         "2026 1. çeyrek"),
        ("MAVI (takvim disi mali yil)", "2026 2. çeyrek",
         "2026 mayıs–temmuz")):
    _c = bd.donem_etiketi_celiskisi(sayfa(_bas, _seri))
    esit(bool(_c), True, f"{_ad}: çelişki görülüyor ({_c})")

esit(bd.donem_etiketi_celiskisi(sayfa("2026 3. çeyrek",
                                      "2026 3. çeyrek")),
     "", "başlık tablosuyla aynıysa çelişki YOK")

esit(bd.donem_etiketi_celiskisi(sayfa("2026 mayıs–temmuz",
                                      "2026 mayıs–temmuz")),
     "", "takvim dışı dönem de kendisiyle uyuşuyorsa sessiz")

# SERI BOLUMU YOKSA OLCUM YOK -- yoklugu kusur saymak, olcemedigimiz
# seyi kusur ilan etmek olurdu.
esit(bd.donem_etiketi_celiskisi(sayfa("2026 2. çeyrek")), "",
     "seri bölümü yoksa çelişki İDDİA EDİLMİYOR")

# BILANCO SAYFASI OLMAYANA BAKILMIYOR.
_makro = sayfa("2026 2. çeyrek", "2026 3. çeyrek").replace(
    "kategori: Bilanço Analizi", "kategori: Analiz")
esit(bd.donem_etiketi_celiskisi(_makro), "",
     "bilanço sayfası olmayan metinde ölçüm yapılmıyor")

# ON BILGI ILE GOVDE AYRIMI: govdede gecen "donem:" satiri olcuyu
# kaydirmamali.
_govdeli = sayfa("2026 3. çeyrek", "2026 3. çeyrek").replace(
    "## Özet", "## Özet\n\ndonem: 2026 2. çeyrek")
esit(bd.donem_etiketi_celiskisi(_govdeli), "",
     "gövdedeki 'donem:' satırı ön bilginin yerine geçmiyor")

# UC TABLO TUZAGI: olcum SERI bolumunun ilk kolonundan, sayfadaki
# ilk `| Kalem` satirindan DEGIL.
_s = sayfa("2026 3. çeyrek", "2026 3. çeyrek")
esit("| Kalem | Değer |" in _s, True,
     "atıllık kontrolü: sayfada seri DIŞINDA da '| Kalem' satırı var")
esit(bd.donem_etiketi_celiskisi(_s), "",
     "ölçüm seri bölümünden okunuyor (ilk '| Kalem' satırından değil)")

# ---------------------------------------------------------------
print("")
print("2) OLCUT ONARIM SEBEBI OLARAK SAYILIYOR")

_bozuk = sayfa("2026 2. çeyrek", "2026 3. çeyrek")
_sebep = bd.onarim_gereken(_bozuk, {"sektor_tr": "Finans"})
esit(any("dönem etiketi" in s for s in _sebep), True,
     f"onarim_gereken çelişkiyi sayıyor ({_sebep})")
esit(bd.onarim_gereken(sayfa("2026 3. çeyrek", "2026 3. çeyrek"),
                       {"sektor_tr": "Finans"}), [],
     "uyuşan sayfa onarım gerektirmiyor")

# ---------------------------------------------------------------
print("")
print("3) URETICI YOL -- celiski gorunce YAZMIYOR")

# `donem_celiskisi` ureticinin ortak olcutu. Ikinci kez
# tanimlanmamasi onemli: iki yerde yazilsa biri degisip oteki
# unutulurdu.
_seri_q3 = [("2026 3. çeyrek", "2026-09-30", None)]
esit(bool(U.donem_celiskisi("2026 2. çeyrek", _seri_q3)), True,
     "etiket Q2, çekilen Q3 -> çelişki")
esit(U.donem_celiskisi("2026 3. çeyrek", _seri_q3), "",
     "etiket Q3, çekilen Q3 -> çelişki yok")
esit(U.donem_celiskisi("2026 2. çeyrek", []), "",
     "seri hiç yoksa çelişki İDDİA EDİLMİYOR")
# ISO YOKSA ETIKET KAYNAGIN YER TUTUCUSU ("-1 dönem") olabilir;
# onu celiski saymak olcemedigimizi kusur ilan etmek olurdu.
esit(U.donem_celiskisi("2026 2. çeyrek", [("-1 dönem", "", None)]), "",
     "bitiş tarihi bilinmiyorsa ölçüm yapılmıyor")

# DAVRANIS: tazeleme celisen sayfaya DOKUNMUYOR.
#
# Olcut dosyanin BAYTLARI -- "dokunmadi" iddiasini metinden degil
# diskten okuyor.
_GERCEK_CEK = T.bilanco_ag.donem_getir


def _sahte_cek(kod, etiket, **kw):
    """Kaynak Q3 veriyor; sayfa ve ozet Q2 diyor."""
    import oranlar                                    # noqa: PLC0415
    d = oranlar.Donem(etiket=etiket, hasilat=56.6, net_kar=11.6,
                      ozkaynak=100.0, aktif_toplami=900.0)
    return d, None, [], [("2026 3. çeyrek", "2026-09-30", d)]


# YAYIN HEDEFI DE YAMALANIYOR -- SINAMA URETIME YAZAMAZ.
#
# `sayfa_tazele` dosyayi okudugu yere degil, `yayin.SITE_ICERIK`
# altindaki KANONIK yola yaziyor. Yamasiz hali olculdu: mutasyon
# sinamasinda 2 numarali mutant (tazeleme kapisi silindi)
# calistirildiginda bu sinama GERCEK icerik dizinine
# `2026-2-ceyrek-akbnk.md` yazdi ve ardindan kosan koruma onu
# gordu. Yani "mutant yakalandi" sinyalinin bir kismi kuralin
# calismasi degil, sinamanin kirliligiydi.
#
# Ayni kusur bu depoda bir kez daha goruldu (`ret_yaz` gercek
# red defterine 10 sahte kayit yazmisti).
_GERCEK_HEDEF = T.yayin.SITE_ICERIK

with tempfile.TemporaryDirectory() as _d:
    _p = pathlib.Path(_d) / "2026-2-ceyrek-akbnk.md"
    _p.write_text(sayfa("2026 2. çeyrek", "2026 3. çeyrek"),
                  encoding="utf-8")
    _once = _p.read_bytes()
    _baglam = {"AKBNK": ("Finans", {"net_kar_marji": 20.0},
                         {"net_kar_marji": 18.0}, 24,
                         "2026 2. çeyrek", "")}
    T.bilanco_ag.donem_getir = _sahte_cek
    T.yayin.SITE_ICERIK = pathlib.Path(_d)
    T.bellegi_bosalt()
    try:
        _ok, _not = T.sayfa_tazele(_p, _baglam,
                                   {"AKBNK": {"unvan": "AKBANK T.A.Ş."}},
                                   kuru=False)
    finally:
        T.bilanco_ag.donem_getir = _GERCEK_CEK
        T.yayin.SITE_ICERIK = _GERCEK_HEDEF
        T.bellegi_bosalt()
    esit(_ok, False, f"tazeleme çelişen sayfayı YAZMIYOR ({_not})")
    esit("dönem çelişkisi" in _not, True,
         f"sebep doğru adıyla söyleniyor ({_not})")
    esit(_p.read_bytes(), _once,
         "dosyanın baytları DEĞİŞMEDİ (iddia diskten okunuyor)")
    esit(sorted(p.name for p in pathlib.Path(_d).iterdir()),
         ["2026-2-ceyrek-akbnk.md"],
         "hiçbir YENİ dosya doğmadı (kanonik yola da yazılmadı)")

# ATILLIK KONTROLU: ayni yol celiski OLMADAN gercekten yaziyor mu?
# Yazmayan bir yolda "yazmadi" iddiasi her zaman gecer.
with tempfile.TemporaryDirectory() as _d:
    _p = pathlib.Path(_d) / "2026-3-ceyrek-akbnk.md"
    _p.write_text(sayfa("2026 3. çeyrek", "2026 3. çeyrek"),
                  encoding="utf-8")
    _baglam = {"AKBNK": ("Finans", {"net_kar_marji": 20.0},
                         {"net_kar_marji": 18.0}, 24,
                         "2026 3. çeyrek", "")}
    T.bilanco_ag.donem_getir = _sahte_cek
    T.bellegi_bosalt()
    try:
        _ok2, _not2 = T.sayfa_tazele(_p, _baglam,
                                     {"AKBNK": {"unvan": "AKBANK T.A.Ş."}},
                                     kuru=True)
    finally:
        T.bilanco_ag.donem_getir = _GERCEK_CEK
        T.bellegi_bosalt()
    esit(_ok2, True,
         f"atıllık kontrolü: çelişki yokken aynı yol TAZELİYOR ({_not2})")

# DAVRANIS: YENI SAYFA yolu da yazmiyor.
#
# Bu yol tazelemeden ONEMLI olani: celisen bir sayfayi SIFIRDAN
# uretirdi ve ustune model cagrisi oderdi. Olcut MODELE HIC
# GIDILMEDIGI: celiski kapisi yorum isteginden ONCE olmali.
_GERCEK_YORUM = U.bilanco_yorum.yorum_uret
_cagri = []


def _sahte_yorum(girdi):
    _cagri.append(girdi)
    return "Hasılat arttı, kâr düştü.", "sahte", "", ""


U.bilanco_ag.donem_getir = _sahte_cek
U.bilanco_yorum.yorum_uret = _sahte_yorum
try:
    _ok3, _not3 = U.sirket_isle(
        "AKBNK", {"unvan": "AKBANK T.A.Ş."}, "Finans", "2026 2. çeyrek",
        {"net_kar_marji": 20.0}, {"net_kar_marji": 18.0}, 24, kuru=True)
    _ok4, _not4 = U.sirket_isle(
        "AKBNK", {"unvan": "AKBANK T.A.Ş."}, "Finans", "2026 3. çeyrek",
        {"net_kar_marji": 20.0}, {"net_kar_marji": 18.0}, 24, kuru=True)
finally:
    U.bilanco_ag.donem_getir = _GERCEK_CEK
    U.bilanco_yorum.yorum_uret = _GERCEK_YORUM

esit(_ok3, False, f"yeni sayfa yolu çelişkide ÜRETMİYOR ({_not3})")
esit("dönem çelişkisi" in _not3, True,
     f"sebep doğru adıyla söyleniyor ({_not3})")
esit(len(_cagri), 1,
     "model çağrısı yalnızca ÇELİŞKİSİZ koşuda yapıldı "
     "(çelişki kapısı yorumdan ÖNCE)")
esit(_ok4, True,
     f"atıllık kontrolü: çelişki yokken aynı yol ÜRETİYOR ({_not4})")

# ---------------------------------------------------------------
print("")
print("4) KUYRUK -- onarilamayan sayfayi TUTMUYOR")

# Celisen sayfa tazelemeyle onarilamiyor (yukarida olculdu), yani
# kuyrukta kalsa her kosuda denenip her kosuda atlanirdi.
with tempfile.TemporaryDirectory() as _d:
    _dizin = pathlib.Path(_d)
    (_dizin / "2026-2-ceyrek-akbnk.md").write_text(
        sayfa("2026 2. çeyrek", "2026 3. çeyrek"), encoding="utf-8")
    # ROE'si anlamsiz, celiskisi OLMAYAN bir sayfa: kuyrugun
    # gercekten dolabildigini gosteriyor. Negatif ozkaynakla ROE
    # yazmak `ozkaynak_celiskisi`nin olctugu kusur.
    _roe = sayfa("2026 3. çeyrek", "2026 3. çeyrek", kod="GARAN")
    _roe = _roe.replace(
        "| Net kâr | 11,60 milyar TL |",
        "| Net kâr | 11,60 milyar TL |\n"
        "| Özkaynak | -2,00 milyar TL |\n"
        "| Özkaynak kârlılığı | %12,2 |")
    (_dizin / "2026-3-ceyrek-garan.md").write_text(_roe,
                                                   encoding="utf-8")
    _ASIL_SITE = U.SITE
    U.SITE = _dizin
    try:
        _k = T.onarim_kuyrugu({"AKBNK": {"sektor_tr": "Finans"},
                               "GARAN": {"sektor_tr": "Finans"}})
        _adlar = [y.name for y, _s in _k]
    finally:
        U.SITE = _ASIL_SITE
    esit("2026-2-ceyrek-akbnk.md" in _adlar, False,
         f"çelişen sayfa onarım kuyruğunda DEĞİL ({_adlar})")
    esit("2026-3-ceyrek-garan.md" in _adlar, True,
         f"atıllık kontrolü: kuyruk gerçekten dolabiliyor ({_adlar})")

# ---------------------------------------------------------------
print("")
print("5) MEKANIK -- denetim seri basligini URETICIDEN okuyor")

_kaynak = (_KOK / "bilanco_denetim.py").read_text(encoding="utf-8")
_agac = ast.parse(_kaynak)


def _islev(ad: str) -> ast.FunctionDef:
    for d in ast.walk(_agac):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return d
    raise AssertionError(f"{ad} bulunamadi")


# Basligi veren islev URETICIDEN ice aliyor olmali.
_ici = [d for d in ast.walk(_islev("_seri_basligi"))
        if isinstance(d, ast.ImportFrom)]
esit([(d.module, [a.name for a in d.names]) for d in _ici],
     [("uret_bilanco_sayfa", ["SERI_BASLIGI"])],
     "başlık üreticinin sabitinden geliyor")

# Celiski olcen islev kendi baslik kopyasini TASIMIYOR.
_literal = [d.value for d in ast.walk(_islev("donem_etiketi_celiskisi"))
            if isinstance(d, ast.Constant) and isinstance(d.value, str)
            and d.value.lstrip().startswith("##")]
esit(_literal, [],
     "donem_etiketi_celiskisi içinde bölüm başlığı literali YOK")

# ATILLIK KONTROLU: tarama baslik literali bulabiliyor mu? Bulamayan
# bir tarama yukaridaki iddiayi her zaman gecirir.
_kanit = [d.value for d in ast.walk(_islev("_seri_basligi"))
          if isinstance(d, ast.Constant) and isinstance(d.value, str)
          and d.value.lstrip().startswith("##")]
esit(bool(_kanit), True,
     f"atıllık kontrolü: tarama başlık literalini buluyor ({_kanit!r})")

# IKI SABIT AYNI SEYI SOYLUYOR -- yedek deger sessizce sapmasin.
esit(bd._seri_basligi(), U.SERI_BASLIGI,
     f"denetim ile üretici aynı başlığı kullanıyor ({U.SERI_BASLIGI})")

# ---------------------------------------------------------------
print("")
print("6) GERCEK KULLIYAT -- yayinda celisen sayfa KALMADI")

_ICERIK = _KOK.parent / "site" / "icerik" / "analizler"
if _ICERIK.is_dir():
    _bakilan = 0
    _celisen = []
    _serili = 0
    for _y in sorted(_ICERIK.glob("*.md")):
        _m = _y.read_text(encoding="utf-8")
        if not bd.bilanco_sayfasi(_m):
            continue
        _bakilan += 1
        if U.SERI_BASLIGI in _m:
            _serili += 1
        if bd.donem_etiketi_celiskisi(_m):
            _celisen.append(_y.name)
    esit(_celisen, [],
         f"{_bakilan} bilanço sayfasında çelişki yok")
    # ATILLIK: olcum GERCEKTEN kosuyor mu? Seri bolumu olmayan
    # sayfada olcu yapilamiyor; hic serili sayfa yoksa yukaridaki
    # iddia bos gecer.
    esit(_serili > 0, True,
         f"atıllık kontrolü: {_serili} sayfada seri bölümü var, "
         f"ölçüm yapılabiliyor")
else:                                                 # pragma: no cover
    print("  (icerik dizini yok -- kulliyat denetimi atlandi)")

# ---------------------------------------------------------------
print("")
print(f"TUM TESTLER GECTI ({_gecti})")
