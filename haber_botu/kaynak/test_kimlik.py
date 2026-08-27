"""Kimlik sabiti testleri -- dis servislere DOGRU adresi verdigimizi sinar.

NEDEN BU TEST VAR
-----------------
2026-08-27'de olculdu: iletisim adresi 20 kaynak dosyasinda ELLE
yazilmisti ve uc tanesi `iletisim@netaris.com` diyordu. O alan adi
BIZIM DEGIL -- bizimki `netaris.net`.

Bu, sessiz bozulan turden bir hata: kod calisiyor, istek gidiyor,
hicbir sey kirmizi donmuyor. Bedeli ancak sonradan goruluyor --
MyMemory ceviri kotasi 50.000 kelimeden 1.000'e dusuyor ya da bir
saglayici uyari e-postasini bize degil baskasina gonderip sonra
sessizce engelliyor.

Adresi duzeltmek yeterli degildi: SEBEP kopyalanmis olmasiydi. On
dosya artik `kimlik.ajan()` cagiriyor ve bu test yeni bir kopyanin
sizmasini engelliyor.

NEDEN AST, NEDEN DUZ METIN ARAMASI DEGIL
----------------------------------------
Aciklama satirlari ve belge dizgileri gecmisteki hatayi ANLATMAK icin
`netaris.com` yaziyor -- ve yazmali. Duz `grep` bunlari da yakalar,
test surekli kirmizi doner ve sonunda kapatilir. Bu yuzden yalnizca
CALISAN KOD icindeki dizgiler taraniyor: belge dizgileri ve
aciklamalar disarida.

Calistirma:  python kaynak/test_kimlik.py
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import kimlik  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


# Ters bolu YOK: heredoc'ta kacis dizileri bozulabiliyor, `[.]` ayni isi
# goruyor ve her ortamda ayni okunuyor.
EPOSTA = re.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}")

#: Bize ait olan alan adlari. Baskasina ait bir adres dis servise
#: gonderilirse hem uyarilari kaciririz hem de o kisiye trafik sikayeti
#: gider.
BIZIM = ("gmail.com", "netaris.net")

KOKLER = ("haber_botu", "site")

#: Kuralin KENDISI, yasakladigi dizgileri yazmak zorunda.
#: Disarida birakilmazsa test kendini yakalar -- ilk kosuda
#: tam olarak bu oldu.
KENDI = {"kimlik.py", "test_kimlik.py"}


def _belge_dugumleri(agac: ast.AST) -> set[int]:
    """Belge dizgisi olan Constant dugumlerinin kimlikleri."""
    bulunan: set[int] = set()
    for n in ast.walk(agac):
        if isinstance(n, (ast.Module, ast.ClassDef,
                          ast.FunctionDef, ast.AsyncFunctionDef)):
            ilk = n.body[0] if n.body else None
            if (isinstance(ilk, ast.Expr)
                    and isinstance(ilk.value, ast.Constant)
                    and isinstance(ilk.value.value, str)):
                bulunan.add(id(ilk.value))
    return bulunan


def kod_dizgileri():
    """(yol, dizgi) -- yalnizca CALISAN koddaki metinler."""
    kok_dizin = pathlib.Path(__file__).resolve().parent.parent.parent
    for kok in KOKLER:
        for p in (kok_dizin / kok).rglob("*.py"):
            if "_onbellek" in p.parts:
                continue
            try:
                agac = ast.parse(p.read_text(encoding="utf-8",
                                             errors="replace"))
            except SyntaxError:
                continue
            belge = _belge_dugumleri(agac)
            for n in ast.walk(agac):
                if (isinstance(n, ast.Constant)
                        and isinstance(n.value, str)
                        and id(n) not in belge):
                    yield p, n.value


# --------------------------------------------------------------------
# 1. KANONIK ADRES BIZE AIT BIR ALAN ADINDA OLMALI.
#    Sabitin kendisi yanlissa asagidaki tum testler yanlisi dogrular.
# --------------------------------------------------------------------
esit(kimlik.ILETISIM.split("@")[-1] in BIZIM, True,
     f"kanonik adres bize ait bir alan adinda ({kimlik.ILETISIM})")

esit(kimlik.ALAN_ADI, "netaris.net", "alan adi netaris.net")

# --------------------------------------------------------------------
# 2. KODDA BASKA HICBIR E-POSTA GECMEMELI.
#    Yeni bir kaynak dosyasi adresi elle yazarsa burasi kirmizi doner.
# --------------------------------------------------------------------
yabanci: dict[str, set[str]] = {}
for yol, metin in kod_dizgileri():
    for e in EPOSTA.findall(metin):
        if e != kimlik.ILETISIM:
            yabanci.setdefault(e, set()).add(yol.name)

esit(yabanci, {},
     "kodda kanonik adres disinda e-posta yok")

# --------------------------------------------------------------------
# 3. `netaris.com` CALISAN KODDA GECMEMELI.
#    Aciklamalarda gecebilir -- gecmisteki hatayi anlatiyorlar.
# --------------------------------------------------------------------
YANLIS_ALAN = "netaris" + ".com"   # bitisik yazilirsa test kendini yakalar
yanlis_alan = {yol.name for yol, metin in kod_dizgileri()
               if YANLIS_ALAN in metin and yol.name not in KENDI}

esit(yanlis_alan, set(),
     "calisan kodda netaris.com yok (bize ait degil)")

# --------------------------------------------------------------------
# 4. `ajan()` HEM AMACI HEM ADRESI TASIMALI.
#    Saglayici gunlugunde kim oldugumuz ve neden geldigimiz gorunmeli;
#    ikisinden biri eksikse User-Agent isini yapmiyor demektir.
# --------------------------------------------------------------------
u = kimlik.ajan("kur verisi")
esit("kur verisi" in u, True, "ajan() amaci tasiyor")
esit(kimlik.ILETISIM in u, True, "ajan() iletisim adresini tasiyor")
esit(u.startswith("Netaris/"), True, "ajan() urun adiyla basliyor")

# Varsayilan cagri da adresi tasimali -- `BASLIKLAR` bunu kullaniyor.
esit(kimlik.ILETISIM in kimlik.BASLIKLAR["User-Agent"], True,
     "hazir BASLIKLAR adresi tasiyor")

# --------------------------------------------------------------------
# 5. ADRES TASIYAN HER KAYNAK `ajan()` UZERINDEN GECMELI.
#    Ikinci kez kopyalanmasini engelleyen asil kural bu: dogru degeri
#    ELLE yazmak da yasak, cunku bir dahaki degisiklikte yine surukler.
# --------------------------------------------------------------------
elle_yazan = {yol.name for yol, metin in kod_dizgileri()
              if kimlik.ILETISIM in metin and yol.name not in KENDI}

esit(elle_yazan, set(),
     "hicbir kaynak adresi elle yazmiyor (hepsi ajan() kullaniyor)")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
