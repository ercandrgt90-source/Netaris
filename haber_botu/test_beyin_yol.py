"""`beyin.baglan()` hangi depoya baglaniyor.

BU DOSYA NEDEN VAR
------------------
Imza soyle idi:

    def baglan(yol: pathlib.Path = VERITABANI):

Python varsayilan degeri ISLEV TANIMLANIRKEN bir kez hesapliyor. Yani
`beyin.VERITABANI` sonradan degistirildiginde `baglan()` ESKI yola
baglanmaya devam ediyordu: ayar YONLENDIRILEBILIR GORUNUP
yonlendirilemiyordu -- sessiz ve kendinden emin bir yanlis.

Olculdu (2026-09-15): hatti agsiz olcmek icin `beyin.VERITABANI` bir
kopyaya cevrildi. Olcum yine de GERCEK depoya yazdi:

    320 sahte `ai_ret` satiri   (neden='olcum' / 'stub')
      6 sahte `calisma` satiri  (0 saniyelik "kosu" kayitlari)

Artiklar temizlendi. Temizlenmeseydi red oranlarini olcen her
cozumleme bozulurdu -- ve bu oturumda red oranlari tam da hattin
teshisinde kullanildi.

NE SINANIYOR
------------
1. `beyin.VERITABANI` degistirilince `baglan()` YENI yola gidiyor.
2. Gercek depoya DOKUNULMUYOR.
3. Acik cagri (`baglan(yol=...)`) da calismaya devam ediyor.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

import beyin                                          # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _satir_sayisi(yol: pathlib.Path) -> int:
    """Baglantiyi KAPATARAK sayar.

    `with sqlite3.connect(...)` baglantiyi DEGIL islemi kapatiyor;
    acik kalan dosya Windows'ta gecici dizin silinirken WinError 32
    veriyor. Bu tuzaga bu depoda daha once de dusuldu.
    """
    b = sqlite3.connect(yol)
    try:
        return b.execute("SELECT COUNT(*) FROM gosterge").fetchone()[0]
    finally:
        b.close()


print("\nVERITABANI degistirilince baglan() ONU kullaniyor")
_asil = beyin.VERITABANI
_gercek_once = _satir_sayisi(_asil)
_d = tempfile.mkdtemp()
try:
    _hedef = pathlib.Path(_d) / "kopya.db"
    beyin.VERITABANI = _hedef
    with beyin.baglan() as _b:
        _b.execute("INSERT INTO gosterge(kod, tarih, deger, birim, ad,"
                   " kaynak, kayit_ani)"
                   " VALUES ('SINAMA','2026-01-01',1,'','','','')")
    beyin.VERITABANI = _asil

    esit(_hedef.exists(), True, "yeni yolda depo olustu")
    esit(_satir_sayisi(_hedef), 1, "yazma YENI depoya gitti")
    esit(_satir_sayisi(_asil), _gercek_once,
         f"gercek depoya DOKUNULMADI ({_gercek_once} satir)")

    print("\nAcik yol da calisiyor (geriye uyum)")
    _ikinci = pathlib.Path(_d) / "ikinci.db"
    with beyin.baglan(_ikinci) as _b:
        _b.execute("INSERT INTO gosterge(kod, tarih, deger, birim, ad,"
                   " kaynak, kayit_ani)"
                   " VALUES ('SINAMA2','2026-01-01',2,'','','','')")
    esit(_satir_sayisi(_ikinci), 1, "acik verilen yola yazildi")
    esit(_satir_sayisi(_asil), _gercek_once, "gercek depo yine dokunulmadi")
finally:
    beyin.VERITABANI = _asil
    import shutil
    shutil.rmtree(_d, ignore_errors=True)

print(f"\nTUM TESTLER GECTI ({_gecti})")
