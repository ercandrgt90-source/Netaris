# -*- coding: utf-8 -*-
"""BILANCO SAYFASI OLCUTU -- ureten ile denetleyen ayni seyi saymali.

KUSUR (olculdu 2026-10-31, YAYINDAYDI)
--------------------------------------
`bilanco_denetim.bilanco_sayfasi` bir sayfayi "## Sektor icindeki
konum" bolumu varsa bilanco analizi sayiyordu. Ama medyani olmayan
sirketin sayfasi o bolum OLMADAN yaziliyor -- yani hattin KENDI
urettigi bir sayfa bicimi denetimin gozune hic gorunmuyordu.

    kategori: Bilanço Analizi olan sayfa   312
    kiyas bolumu tasiyan                   302
    UC KORUMANIN DISINDA kalan              10   <- dordu 3. ceyrek

Disarida kalmak su demekti: dort ceyreklik tablo gocune hic
girmemek, onarim kuyruguna hic girmemek ve
`site/test_bilanco_sayfa_saglam.py` tarafindan hic bakilmamak.
Kirmizi gorunmuyordu cunku `olc()` ve `onarim_gereken()` ilk satirda
bu isleve bakip BOS liste donuyor; bos liste "sayfa saglam" ile ayni
okunuyor.

KURAL
-----
Bir sayfanin "bizim sayfamiz" olup olmadigina ISTEGE BAGLI BIR
BOLUMUN VARLIGI karar veremez. Olcut ureticinin olcutu olmali:
on bilgideki `kategori` alani.

Bu dosya kurali UC KATTA tutuyor:
  1. davranis  -- bolumsuz sayfa taniniyor, yanlis kategorili sayfa
                  tanINMIyor;
  2. uyum      -- ureten (`uret_bilanco_sayfa._bilanco_sayfasi`) ile
                  denetleyen ayni cevabi veriyor, GERCEK kulliyatta;
  3. mekanik   -- `bilanco_sayfasi` AST'sinde hicbir bolum basligi
                  gecmiyor, yani karar bolumden verilemez.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import bilanco_denetim as bd                         # noqa: E402
import bilanco_tazele as BT                          # noqa: E402
import kumulatif_temizle as KT                       # noqa: E402
import uret_bilanco_sayfa as U                       # noqa: E402

NL = chr(10)
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


def _sayfa(kategori: str = "Bilanço Analizi", kiyas: bool = False,
           kilavuz: str = "", seri: bool = False,
           donem: str = "2026 3. çeyrek", kod: str = "ZZZZ") -> str:
    """Sahte analiz sayfasi.

    KIYAS BOLUMU VARSAYILAN OLARAK YOK -- kusurun yasandigi bicim
    tam olarak budur, o yuzden varsayilan o.
    """
    s = ["---", "slug: x", f"kod: {kod}", f"donem: {donem}",
         f"kategori: {kategori}", "tarih: 2026-10-31", "---", "",
         "## Özet", "", "Bir cümle.", "",
         f"## {donem} dönemi ölçümleri", "",
         "| Kalem | Değer |", "| --- | ---: |",
         "| Hasılat | 10,00 milyar TL |",
         "| Net kâr | 1,00 milyar TL |", ""]
    if seri:
        s += [U.SERI_BASLIGI, "",
              "| Kalem | 2026/9 | 2026/6 |", "| --- | ---: | ---: |",
              "| Hasılat | 10,00 | 9,00 |", ""]
    if kiyas:
        s += [U.KIYAS_BASLIGI, "",
              "| Oran | Şirket | Sektör medyanı |",
              "| --- | ---: | ---: |",
              "| Net kâr marjı | %10,0 | %5,0 |", ""]
    if kilavuz:
        s += [f"## {kilavuz}", "", "Bir paragraf.", ""]
    return NL.join(s) + NL


# ---------------------------------------------------------------
print("1. GERILEME VAKASI -- kiyas bolumu olmayan sayfa")

_kiyassiz = _sayfa()
esit(U.KIYAS_BASLIGI in _kiyassiz, False, "sahte sayfada kıyas bölümü YOK")
esit(bd.bilanco_sayfasi(_kiyassiz), True,
     "kıyassız sayfa bilanço sayfası SAYILIYOR")

_kiyasli = _sayfa(kiyas=True)
esit(U.KIYAS_BASLIGI in _kiyasli, True, "kıyaslı sahte sayfada bölüm VAR")
esit(bd.bilanco_sayfasi(_kiyasli), True,
     "kıyaslı sayfa da sayılıyor (kapsam daralmadı)")

# ---------------------------------------------------------------
print("")
print("2. OLCUT KATEGORI -- baska kategori SAYILMIYOR")

esit(bd.bilanco_sayfasi(_sayfa(kategori="Haber")), False,
     "kategori Haber ise sayılmıyor")
esit(bd.bilanco_sayfasi(_sayfa(kategori="Haber", kiyas=True)), False,
     "kıyas bölümü VARKEN bile kategori Haber ise sayılmıyor")
esit(bd.bilanco_sayfasi(_sayfa(kategori="Teknik Görünüm")), False,
     "teknik görünüm sayılmıyor")
esit(bd.bilanco_sayfasi(_sayfa(kategori="Makro")), False,
     "makro sayılmıyor")
esit(bd.bilanco_sayfasi(_sayfa(kategori="Bilanço")), False,
     "eksik kategori adı sayılmıyor (tam eşleşme)")
esit(bd.bilanco_sayfasi(_sayfa(kategori="Bilanço Analizi Özeti")), False,
     "önek eşleşmesi YETMİYOR")

# BEKLENTI SABITTEN TURETILMIYOR -- sabit degisirse bu satir duser.
esit(KT.KATEGORI, "Bilanço Analizi", "kanonik kategori sabiti")

# ---------------------------------------------------------------
print("")
print("3. YALNIZCA ON BILGIDEN")

_govdede = NL.join([
    "---", "kod: ZZZZ", "kategori: Haber", "---", "",
    "## Özet", "", "kategori: Bilanço Analizi", "",
]) + NL
esit(bd.bilanco_sayfasi(_govdede), False,
     "gövdedeki kategori satırı sayfayı bilanço YAPMIYOR")

_onbilgisiz = NL.join(["# Başlık", "", "kategori: Bilanço Analizi", ""]) + NL
esit(bd.bilanco_sayfasi(_onbilgisiz), False,
     "ön bilgi bloğu yoksa sayılmıyor")

# ON BILGIDE KATEGORI HIC YOKKEN govdedeki satir okunMAMAli.
#
# Yukaridaki `_govdede` bu kurali TEK BASINA tutamiyor: orada on
# bilgide `kategori: Haber` var, yani ilk eslesme zaten dogru
# cevabi veriyor ve kapanis `---` kirilmasi kaldirilsa bile sonuc
# degismiyor. Mutasyon bunu gosterdi (kacan mutant: "kapanis ---
# kirilmasi kaldirildi"). Ayrim ancak on bilgide HIC kategori
# yokken goruluyor.
_kategorisiz = NL.join([
    "---", "kod: ZZZZ", "donem: 2026 3. çeyrek", "---", "",
    "## Özet", "", "kategori: Bilanço Analizi", "",
]) + NL
esit(bd._on_bilgi_kategorisi(_kategorisiz), "",
     "ön bilgide kategori yoksa GÖVDEYE geçilmiyor")
esit(bd.bilanco_sayfasi(_kategorisiz), False,
     "gövdedeki kategori satırı ön bilgi yerine geçmiyor")

esit(bd.bilanco_sayfasi(""), False, "boş metin sayılmıyor")
esit(bd._on_bilgi_kategorisi(_sayfa()), "Bilanço Analizi",
     "ön bilgi kategorisi okunuyor")
esit(bd._on_bilgi_kategorisi(_onbilgisiz), "",
     "ön bilgi yoksa boş dizge")

# ---------------------------------------------------------------
print("")
print("4. YENI YETENEK -- kiyassiz sayfa artik DENETLENIYOR")

_TELEKOM = "Telekomünikasyonda borç ve amortisman neden yüksektir"
_bilgi = {"sektor_tr": "İletişim", "alt_sektor": "Entertainment"}

_bozuk = _sayfa(kilavuz=_TELEKOM, kod="FENER")
esit(U.KIYAS_BASLIGI in _bozuk, False, "bozuk sayfada kıyas bölümü YOK")
esit(bd.onarim_gereken(_bozuk, _bilgi),
     [f"kapsam dışı kılavuz ({_TELEKOM})"],
     "kıyassız sayfadaki kapsam dışı kılavuz YAKALANIYOR")

# ... ve kontrol her seye "bozuk" demiyor.
esit(bd.onarim_gereken(_bozuk, {"sektor_tr": "İletişim",
                                "alt_sektor": "Telecom Services"}),
     [], "doğru alt sektörde aynı sayfa sağlam")
esit(bd.onarim_gereken(_sayfa(kod="FENER"), _bilgi), [],
     "kılavuzsuz kıyassız sayfa sağlam")

# ---------------------------------------------------------------
print("")
print("5. GOC KUYRUGU kiyassiz sayfayi GORUYOR")

with tempfile.TemporaryDirectory() as _t:
    _d = pathlib.Path(_t)
    (_d / "kiyassiz-eksik.md").write_text(_sayfa(kod="AAA"),
                                          encoding="utf-8")
    (_d / "kiyassiz-seri.md").write_text(_sayfa(kod="BBB", seri=True),
                                         encoding="utf-8")
    (_d / "haber.md").write_text(_sayfa(kod="CCC", kategori="Haber"),
                                 encoding="utf-8")
    _asil = U.SITE
    U.SITE = _d
    try:
        _k = {p[0].name for p in BT.goc_kuyrugu({}, None)}
    finally:
        U.SITE = _asil
    esit("kiyassiz-eksik.md" in _k, True,
         "serisi olmayan kıyassız sayfa göç kuyruğunda")
    esit("kiyassiz-seri.md" in _k, False,
         "serisi OLAN sayfa kuyruğa girmiyor")
    esit("haber.md" in _k, False, "haber kuyruğa girmiyor")
    esit(len(_k), 1, "kuyrukta tam olarak bir sayfa")

# ---------------------------------------------------------------
print("")
print("6. URETEN ile DENETLEYEN ayni cevabi veriyor")

# Once SENTETIK -- kulliyat bos olsa bile bu kat her zaman kosar.
for _kat in ("Bilanço Analizi", "Haber", "Makro", "Teknik Görünüm",
             "Bilanço", ""):
    for _ky in (False, True):
        _m = _sayfa(kategori=_kat, kiyas=_ky)
        esit(bd.bilanco_sayfasi(_m),
             U._bilanco_sayfasi(bd._on_bilgi_kategorisi(_m)),
             f"sentetik uyum: kategori={_kat!r} kıyas={_ky}")

# Sonra GERCEK KULLIYAT. Bos olabilir (yeni kurulum); o zaman
# sessizce atlaniyor -- mesru sifiri kusur saymak dagitimi durdurur
# ve bu dosyanin korudugu sey MEKANIZMA, icerik degil.
_bakilan = _ayrilan = 0
if U.SITE.is_dir():
    for _yol in sorted(U.SITE.glob("*.md")):
        _m = _yol.read_text(encoding="utf-8")
        _bakilan += 1
        if bd.bilanco_sayfasi(_m) != U._bilanco_sayfasi(
                bd._on_bilgi_kategorisi(_m)):
            _ayrilan += 1
            print(f"    AYRISTI: {_yol.name}")
esit(_ayrilan, 0, f"külliyatta ayrışan sayfa yok ({_bakilan} dosya)")

# ---------------------------------------------------------------
print("")
print("7. MEKANIK KURAL -- karar BOLUMDEN verilemez")


def _islev(ad: str) -> ast.FunctionDef:
    agac = ast.parse(pathlib.Path(bd.__file__).read_text(encoding="utf-8"))
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return d
    raise AssertionError(f"{ad} bulunamadi")


_basliklar: list = []
_adlar: list = []
for _f in (_islev("bilanco_sayfasi"), _islev("_on_bilgi_kategorisi")):
    for _d in ast.walk(_f):
        if isinstance(_d, ast.Constant) and isinstance(_d.value, str):
            if _d.value.lstrip().startswith("#"):
                _basliklar.append(_d.value)
        elif isinstance(_d, ast.Name) and _d.id.endswith("_BASLIGI"):
            _adlar.append(_d.id)
        elif isinstance(_d, ast.Attribute) and _d.attr.endswith("_BASLIGI"):
            _adlar.append(_d.attr)

esit(_basliklar, [], "ölçütte markdown başlığı literali yok")
esit(_adlar, [], "ölçütte *_BASLIGI sabiti kullanılmıyor")

# ATILLIK KONTROLU: tarama GERCEKTEN baslik buluyor mu? Bulan bir
# islev uzerinde denenmezse yukaridaki iki iddia her zaman gecer ve
# hicbir seyi korumaz.
_kanit = [d.value for d in ast.walk(_islev("kilavuz_uyusmazligi"))
          if isinstance(d, ast.Constant) and isinstance(d.value, str)
          and d.value.lstrip().startswith("#")]
esit(bool(_kanit), True,
     f"atıllık kontrolü: tarama başlık literali buluyor ({_kanit!r})")

# ---------------------------------------------------------------
print("")
print(f"TUM TESTLER GECTI ({_gecti})")
