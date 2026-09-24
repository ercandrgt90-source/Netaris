# -*- coding: utf-8 -*-
"""AKTARIM ZINCIRI YASAL AYRIM NOTU OLMADAN YAYIMLANAMAZ.

BU DOSYA NEDEN VAR
------------------
Site nedensel zincirler yayimliyor: "FED -> politika faizi -> 2 yillik
tahvil getirisi". Bu zincir YAPISAL bir iddiadir, yon tahmini degil --
ve aradaki farki soyleyen cumle `.kanal-not`:

    "Bu zincir yapisal bir aktarim kanalidir; yon ve buyukluk tahmini
     icermez."

Deponun kendi ifadesiyle (stil.css:6939) bu fark "sitenin en hassas
cizgisi". Sitenin altbilgisi de "Yatirim tavsiyesi degildir" diyor.

OLCULDU (2026-09-24): 26 SAYFA NOTSUZDU
---------------------------------------
177 sayfa aktarim zinciri basiyordu; 151'i notu tasiyordu, 26'si
tasimiyordu. Sebep: not sablonda YALNIZCA `yerel_kanal` blogunun
icindeydi. Yalnizca `piyasa_kanali` olan sayfalarda -- ornegin ABD
piyasasi zinciri -- hic basilmiyordu.

Kural yaziliydi, zorlanmiyordu. Bu depoda tekrar eden kusur sinifi.

NE SINANIYOR
------------
1. Zincir basan HER sayfa notu tasiyor.
2. Not zincirden SONRA geliyor (okur once iddiayi, sonra sinirini
   gormemeli -- tersi kafa karistirir; sira kontrol ediliyor).
3. Notun metni yerinde -- "tahmini icermez" ifadesi silinmemis.
4. Hicbir CSS kurali notu gizlemiyor ya da okunmaz kilmiyor.
5. Kontrollerin kendisi calisiyor.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
_CSS = _SITE / "statik" / "stil.css"

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


ZINCIR = '<ol class="kanal">'
NOT = 'class="kanal-not"'
#: Notun YASAL CEKIRDEGI. Metin duzenlenebilir ama bu ifade
#: kaybolursa mekanizma ile tahmin arasindaki fark kaybolur.
CEKIRDEK = "tahmini içermez"

print("\nCSS notu gizlemiyor")
_css = _CSS.read_text(encoding="utf-8", errors="replace")
_gizli = []
for _sec, _gov in re.findall(r"([^{}]+)\{([^{}]*)\}", _css):
    if "kanal-not" not in _sec:
        continue
    if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|"
                 r"opacity\s*:\s*0(?!\.)|font-size\s*:\s*0", _gov):
        _gizli.append(_sec.strip()[:50])
if _gizli:
    print(f"\n  NOTU GIZLEYEN KURAL: {_gizli}")
esit(_gizli, [], "hicbir kural yasal notu gizlemiyor")
esit(".kanal-not" in _css, True, "not stilde tanimli (silik birakilmamis)")

print("\nUretilen ciktida")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_zincirli = _notlu = 0
_notsuz: list[str] = []
_ters_sira: list[str] = []
_cekirdeksiz: list[str] = []
for _p in _CIKTI.rglob("*.html"):
    _g = _p.read_text(encoding="utf-8", errors="replace")
    if ZINCIR not in _g:
        continue
    _zincirli += 1
    _yol = "/" + _p.relative_to(_CIKTI).as_posix()
    if NOT not in _g:
        _notsuz.append(_yol)
        continue
    _notlu += 1
    # Not, SON zincirden sonra gelmeli.
    if _g.rindex(NOT) < _g.rindex(ZINCIR):
        _ters_sira.append(_yol)
    _m = re.search(r'class="kanal-not"[^>]*>(.*?)</p>', _g, re.S)
    # BOSLUK NORMALLESTIRILIYOR. Sablon cumleyi SATIR SONUYLA boluyor
    # ("...buyukluk tahmini" / yeni satir / "icermez."), yani duz metin
    # aramasi ifadeyi BULAMIYOR. Ilk yazimda tam bu yuzden 180 sayfa
    # yanlis yere kirmizi yandi -- kusur sayfada degil, OLCUMDEYDI.
    if not (_m and CEKIRDEK in " ".join(_m.group(1).split())):
        _cekirdeksiz.append(_yol)

esit(_zincirli > 0, True, f"aktarim zinciri basan sayfa var ({_zincirli})")
if _notsuz:
    print(f"\n  YASAL NOTSUZ ZINCIR: {len(_notsuz)} -> {_notsuz[:5]}")
esit(_notsuz, [], f"zincir basan HER sayfa yasal notu tasiyor ({_notlu})")
if _ters_sira:
    print(f"\n  NOT ZINCIRDEN ONCE: {_ters_sira[:3]}")
esit(_ters_sira, [], "not zincirden SONRA geliyor")
if _cekirdeksiz:
    print(f"\n  CEKIRDEK IFADE YOK: {_cekirdeksiz[:3]}")
esit(_cekirdeksiz, [],
     f"her notta \"{CEKIRDEK}\" ifadesi duruyor")

print("\nKONTROLLERIN KENDISI CALISIYOR MU")
# Zincir basip not basmayan uydurma bir sayfa YAKALANMALI.
_sahte = f'<article>{ZINCIR}<li>a</li></ol></article>'
esit(ZINCIR in _sahte and NOT not in _sahte, True,
     "notsuz zincir YAKALANIYOR (kural sahte degil)")
# Ters sirali sayfa da yakalanmali.
_ters = f'<p {NOT}>{CEKIRDEK}</p>{ZINCIR}</ol>'
esit(_ters.rindex(NOT) < _ters.rindex(ZINCIR), True,
     "not zincirden ONCE gelirse YAKALANIYOR")
# Cekirdek ifadesi silinmis not da yakalanmali.
_bos = f'<p {NOT}>Bu bir aciklamadir.</p>'
_mm = re.search(r'class="kanal-not"[^>]*>(.*?)</p>', _bos, re.S)
esit(CEKIRDEK in " ".join((_mm.group(1) if _mm else "").split()), False,
     "cekirdek ifadesi silinmis not YAKALANIYOR")
# Satir sonuyla bolunmus cumle GECERLI sayilmali -- sablon boyle yaziyor.
_bolunmus = "<p " + NOT + ">yon ve buyukluk tahmini" + chr(10) + \
    "      icermez.</p>"
_mb = re.search(r'class="kanal-not"[^>]*>(.*?)</p>', _bolunmus, re.S)
esit("tahmini icermez" in " ".join(_mb.group(1).split()), True,
     "satir sonuyla bolunmus cumle taniniyor (olcum dar degil)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
