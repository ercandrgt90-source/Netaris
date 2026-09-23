# -*- coding: utf-8 -*-
"""GUN SINIRI OKURUN TAKVIMINDE BELIRLENIR, SUNUCUNUNKINDE DEGIL.

BU DOSYA NEDEN VAR
------------------
OLCULDU (2026-09-23): arsivdeki 1045 yayimlanmis haberin 77'sinde
gosterilen tarih UTC gunune esitti ve TURKIYE gunune DEGILDI.

Dagilim tesadufi degildi -- hepsi tek pencerede toplaniyordu:

    21:00 UTC   32 haber
    22:00 UTC   37 haber
    23:00 UTC    8 haber

Yani UTC ile TR tarihinin ayrildigi UC SAAT. 74'u tek kaynaktan
(FinancialJuice). Sebep `_tarih_coz` icindeydi:

    datetime.strptime(ham, bicim).date()      # dilim ATILIYOR

Somut sonuc: Turkiye saatiyle 00:30'da gelen TAZE bir haber, okura
DUNUN tarihiyle gorunuyordu. Site Turkce, okuru Turkiye'de.

NEDEN HER DAMGA CEVRILMIYOR
---------------------------
Dilimi BELLI OLMAYAN bir damgayi UTC varsaymak kusuru ters yone
cevirirdi: Turkce bir kaynak "23 Eyl 2026 23:00" yazdiginda o zaten
TR saati; UTC sayip cevirmek tarihi bir gun ILERI atardi. Yani
"hepsini cevir" cozumu, cozdugunden fazlasini bozardi.

O yuzden kural dar: yalnizca dilimini ACIKCA bildiren damgalar
cevriliyor (`+0000`, `GMT`, sondaki `Z`), digerleri oldugu gibi
kaliyor.

NE SINANIYOR
------------
1. Dilimi bilinen damgalar TR gunune cevriliyor.
2. Dilimi BILINMEYEN damgalara DOKUNULMUYOR.
3. Gun sinirini gecmeyen damgalar degismiyor.
4. Cozulemeyen tarih BOS doner (bugunu yazmak, eski duyuruyu bugun
   cikmis gibi gosterirdi).
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK / "kaynak"), str(_KOK)]

import besleme  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


print("\nDilimi BILINEN damga -> TR gunune cevriliyor")
# 21:30 UTC = ertesi gun 00:30 TR. Kusurun tam olarak yasandigi an.
esit(besleme._tarih_coz("Tue, 22 Sep 2026 21:30:00 +0000"), "2026-09-23",
     "acik ofset (+0000) gun sinirini geciyor")
esit(besleme._tarih_coz("Tue, 22 Sep 2026 21:30:00 GMT"), "2026-09-23",
     "dilim ADI (GMT) taniniyor")
esit(besleme._tarih_coz("2026-09-22T21:30:00Z"), "2026-09-23",
     "sondaki 'Z' UTC sayiliyor")
esit(besleme._tarih_coz("2026-09-22T21:30:00+00:00"), "2026-09-23",
     "ISO ofset cevriliyor")

print("\nDilimi BILINMEYEN damgaya DOKUNULMUYOR")
# Bunu cevirmek, TR saatiyle yazan bir kaynagi bir gun ILERI atardi.
esit(besleme._tarih_coz("2026-09-22 23:00:00"), "2026-09-22",
     "dilimsiz damga oldugu gibi kaliyor")
esit(besleme._tarih_coz("2026-09-22"), "2026-09-22",
     "yalniz tarih (saat yok) oldugu gibi kaliyor")

print("\nGun sinirini gecmeyen damga degismiyor")
esit(besleme._tarih_coz("Tue, 22 Sep 2026 10:00:00 +0000"), "2026-09-22",
     "gunduz saati ayni gunde kaliyor")
esit(besleme._tarih_coz("Tue, 22 Sep 2026 21:30:00 +0300"), "2026-09-22",
     "zaten TR ofsetliyse kaymiyor")
# Ters yon: TR'de gun DONMEDEN once, UTC'de donmus olabilir.
esit(besleme._tarih_coz("Wed, 23 Sep 2026 00:30:00 +0000"), "2026-09-23",
     "UTC gunu donmus ama TR ayni gunde (03:30)")

print("\nCozulemeyen tarih BOS doner")
esit(besleme._tarih_coz(""), "", "bos giris")
esit(besleme._tarih_coz("yakinda"), "", "tarihsiz metin")

print("\nSaat dilimi GERCEKTEN +03:00")
# Olculdu (mutasyon E): yedek ofseti +2 yapmak sinamayi KIRMIZI
# yapmiyordu -- cunku bu makinede `ZoneInfo` calisiyor ve yedek dala
# hic girilmiyor. Yani yanlis bir yedek, tzdata'si olmayan bir
# makinede saatleri bir saat kaydirir ve kimse gormez.
#
# Bu iddia DAVRANISI olcuyor: dilim nasil elde edilmis olursa olsun
# (ZoneInfo ya da sabit ofset) sonuc +03:00 olmali.
from datetime import datetime as _dt, timedelta as _td, timezone as _tz  # noqa: E402

_ofset = _dt(2026, 9, 23, 12, tzinfo=_tz.utc).astimezone(besleme._TR).utcoffset()
esit(_ofset, _td(hours=3), f"TR dilimi UTC+3 ({_ofset})")
# Turkiye 2016'dan beri YAZ SAATI uygulamiyor: kisin da ayni olmali.
_kis = _dt(2026, 1, 15, 12, tzinfo=_tz.utc).astimezone(besleme._TR).utcoffset()
esit(_kis, _td(hours=3), "kis aylarinda da UTC+3 (yaz saati yok)")

print("\nYEDEK DAL da dogru: tzdata olmayan makine")
# Olculdu (mutasyon E): yedek ofseti +2 yapmak sinamayi KIRMIZI
# YAPMIYORDU, cunku bu makinede `ZoneInfo` calisiyor ve yedek dala hic
# girilmiyor. Ama o dal, tz veritabani OLMAYAN makinelerde calisan
# kodun ta kendisi -- orada yanlis bir ofset saatleri bir saat kaydirir
# ve kimse gormez.
#
# `zoneinfo` ice aktarimi gecici olarak bozuluyor ki yedek dal
# GERCEKTEN kossun.
_yedek_modul = sys.modules.get("zoneinfo", "__yok__")
sys.modules["zoneinfo"] = None          # `from zoneinfo import ...` -> ImportError
try:
    _yedek_bolge = besleme._tr_bolgesi()
finally:
    if _yedek_modul == "__yok__":
        sys.modules.pop("zoneinfo", None)
    else:
        sys.modules["zoneinfo"] = _yedek_modul
_yo = _dt(2026, 9, 23, 12, tzinfo=_tz.utc).astimezone(_yedek_bolge).utcoffset()
esit(_yo, _td(hours=3), f"tzdata yokken de UTC+3 ({_yo})")

print("\nCEVIRI GERCEKTEN CALISIYOR MU -- kendi kendini sinar")
# Olculdu: bu depoda "hicbir sey olcmeyen sinama" tuzagina defalarca
# dusuldu. Asagidaki iddia, cevirinin ETKISIZ hale gelmesini yakalar:
# ayni an iki bicimde veriliyor ve IKISI DE ayni TR gununu vermeli.
_a = besleme._tarih_coz("Tue, 22 Sep 2026 22:00:00 +0000")
_b = besleme._tarih_coz("2026-09-23T01:00:00+03:00")   # ayni an, TR ofsetli
esit(_a, _b, f"ayni an, iki bicim -> ayni gun ({_a})")
esit(_a, "2026-09-23", "ve o gun TR gunu")

print(f"\nTUM TESTLER GECTI ({_gecti})")
