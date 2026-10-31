# -*- coding: utf-8 -*-
"""MIRAS LISTESINDEN CIKMA KURALI -- saglam gorunmek yetmez.

KUSUR (olculdu 2026-10-31)
--------------------------
`test_bilanco_sayfa_saglam.py` bir sayfayi `onarim_gereken` bos
liste donduruyorsa "onarilmis" sayip MIRAS listesinden cikarmayi
oneriyordu (`--budar` ile gercekten cikariyordu).

Ama bos liste iki ayri seyi birden anlatiyor:

    saglam      -- denetlendi, kusur bulunamadi
    OLCULEMEZ   -- denetim calisamadi, kusur GORULEMEDI

Kiyas bolumu olmayan sayfada oran tablosu hic yok; `olc()` sifir
kalem donuyor ve dolayisiyla `donem_tutarsizligi` -- miras
listesinin BIRINCIL sebebi -- hicbir zaman bir sey bulamiyor. Boyle
bir sayfayi listeden cikarmak, kusuru duzeltmek degil tolerans
isaretini kaldirmak olurdu.

Olculdu: olcut kategoriye gecirilince denetime giren 10 kiyassiz
sayfanin ucu (ALGYO, RUZYE, TUPRS) miras listesindeydi ve ucunde de
olculebilen kalem YOK.

KURAL
-----
Bir sayfa MIRAS listesinden ancak GERCEKTEN OLCULDUYSE cikabilir.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK.parent / "haber_botu"))

import bilanco_denetim as bd                         # noqa: E402

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


def _yukle():
    """Korunan betigi MODUL olarak alir (adi `test_` ile basliyor)."""
    yol = _KOK / "test_bilanco_sayfa_saglam.py"
    belirtec = importlib.util.spec_from_file_location("_saglam", yol)
    m = importlib.util.module_from_spec(belirtec)
    belirtec.loader.exec_module(m)
    return m, yol


SG, _YOL = _yukle()


def _sayfa(kiyas: bool, brut_marj: str = "%50,0") -> str:
    """Bilanco sayfasi. `kiyas` ORAN TABLOSUNU getiriyor -- olcum
    ancak o tabloyla mumkun."""
    s = ["---", "slug: x", "kod: ZZZZ", "donem: 2026 3. çeyrek",
         "kategori: Bilanço Analizi", "tarih: 2026-10-31", "---", "",
         "## Özet", "", "Bir cümle.", "",
         "## 2026 3. çeyrek dönemi ölçümleri", "",
         "| Kalem | Değer |", "| --- | ---: |",
         "| Hasılat | 10,00 milyar TL |",
         "| Brüt kâr | 5,00 milyar TL |",
         "| Net kâr | 1,00 milyar TL |",
         "| Özkaynak | 10,00 milyar TL |", ""]
    if kiyas:
        s += ["## Sektör içindeki konum", "",
              "| Oran | Şirket | Sektör medyanı |",
              "| --- | ---: | ---: |",
              f"| Brüt kâr marjı | {brut_marj} | %20,0 |",
              "| Özkaynak kârlılığı | %10,0 | %5,0 |", ""]
    return NL.join(s) + NL


# ---------------------------------------------------------------
print("1. OLCULEBILEN saglam sayfa listeden CIKABILIR")

_olculur = _sayfa(kiyas=True)
esit(len(bd.olc(_olculur)) > 0, True, "oran tablosu olan sayfa ölçülüyor")
esit(bd.onarim_gereken(_olculur), [], "ve sağlam")
esit(SG.cikarilabilir(_olculur), True, "ölçülmüş sağlam sayfa çıkarılabilir")

# ---------------------------------------------------------------
print("")
print("2. OLCULEMEYEN sayfa listede KALIYOR")

_olculmez = _sayfa(kiyas=False)
esit(bd.bilanco_sayfasi(_olculmez), True,
     "kıyassız sayfa bilanço sayfası sayılıyor")
esit(bd.olc(_olculmez), [], "ama ölçülebilen kalem YOK")
esit(bd.onarim_gereken(_olculmez), [],
     "onarım gerekmiyor GÖRÜNÜYOR (boş liste)")
esit(SG.cikarilabilir(_olculmez), False,
     "ölçülemeyen sayfa listeden ÇIKARILAMAZ")

# ---------------------------------------------------------------
print("")
print("3. BOZUK sayfa zaten saglam sayilmiyor")

_bozuk = _sayfa(kiyas=True, brut_marj="%12,0")
esit(bool(bd.onarim_gereken(_bozuk)), True, "uyuşmazlık yakalanıyor")
esit(SG.cikarilabilir(_bozuk), True,
     "bozuk sayfa da ÖLÇÜLÜ (ayrım ölçüm, sağlamlık değil)")

# ---------------------------------------------------------------
print("")
print("4. MEKANIK -- karar `cikarilabilir` uzerinden veriliyor")

_agac = ast.parse(_YOL.read_text(encoding="utf-8"))
_main = next(d for d in ast.walk(_agac)
             if isinstance(d, ast.FunctionDef) and d.name == "main")
_adlar = {d.id for d in ast.walk(_main) if isinstance(d, ast.Name)}
esit("cikarilabilir" in _adlar, True,
     "main() kararı cikarilabilir'e soruyor")

# ATILLIK KONTROLU: tarama gercekten ad buluyor mu?
esit("duzelen" in _adlar, True,
     "atıllık kontrolü: tarama main() içindeki adları görüyor")

# ---------------------------------------------------------------
print("")
print("5. GERCEK KULLIYAT -- kural bos durmuyor")

_ICERIK = _KOK / "icerik" / "analizler"
_kiyassiz = _olculebilen = 0
if _ICERIK.is_dir():
    for _p in sorted(_ICERIK.glob("*.md")):
        _m = _p.read_text(encoding="utf-8")
        if not bd.bilanco_sayfasi(_m):
            continue
        if "## Sektör içindeki konum" in _m:
            continue
        _kiyassiz += 1
        if bd.olc(_m):
            _olculebilen += 1
esit(_olculebilen, 0,
     f"külliyattaki kıyassız sayfaların hiçbiri ölçülemiyor "
     f"({_kiyassiz} sayfa)")

# ---------------------------------------------------------------
print("")
print(f"TUM TESTLER GECTI ({_gecti})")
