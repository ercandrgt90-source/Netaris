# -*- coding: utf-8 -*-
"""KAYNAKTA GORUNMEZ DENETIM KARAKTERI OLMAMALI.

BU DOSYA NEDEN VAR
------------------
`insa.py` icinde su desen uzun sure durdu (gorunmez hali):

    re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>")

Yazilmak istenen kelime siniri ve geri basvuruydu. Ikisi de yazim
sirasinda GERCEK denetim karakterine donmustu: 0x08 (backspace) ve
0x01. Sonuc, desenin ilk seceneginin HICBIR ZAMAN eslesmemesi --
betik ve stil bloklarinin icerigi metne karisti ve okura cizilmeyen
karakterler "kapsam disi" diye raporlandi.

Kusurun tamami GORUNMEZ: kaynak dogru yazilmis gibi durur, editor
bir sey gostermez, sozdizimi gecerlidir, sinamalar yesil kalir.
Bu depodaki en pahali kusur sinifi tam olarak budur -- yazilan ile
calisan arasindaki fark.

AYNI TUZAK BIR GUNDE UC KEZ ISLEDI (2026-10-20) ve her seferinde ayni
yerden: yama betikleri `python - <<PY` ile yaziliyor, ters bolu bir
kat eksiliyor, Python kalan diziyi gercek karaktere ceviriyor.
Duzeltmek yetmez; buraya bir KAPI gerekiyordu.

NE SINANIYOR
------------
Depodaki kaynak dosyalarinda satir sonu ve sekme DISINDA denetim
karakteri yok. Uretilen cikti ve ucuncu taraf paketler haric --
oralarda bizim yazdigimiz bir sey yok.
"""

from __future__ import annotations

import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}" + chr(10) + f"    beklenen: {beklenen!r}"
              + chr(10) + f"    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Bizim yazdigimiz kaynak turleri.
UZANTI = (".py", ".js", ".mjs", ".ts", ".tsx", ".html", ".css",
          ".json", ".yml", ".yaml", ".md", ".txt", ".sh")

#: Bizim yazmadigimiz ya da uretilen yerler.
DISLANAN = ("node_modules", ".git", "cikti", "__pycache__", ".wrangler",
            "venv", ".venv", "dist", "build")

#: Izin verilenler: satir sonu, sekme, satir basi (CRLF dosyalar).
IZINLI = {0x09, 0x0A, 0x0D}


def _sorunlu(metin: str):
    """(satir, sutun, kod) uclusu dondurur."""
    for i, satir in enumerate(metin.splitlines(), 1):
        for j, k in enumerate(satir, 1):
            if ord(k) < 32 and ord(k) not in IZINLI:
                yield i, j, ord(k)
            # 0x7F (delete) da gorunmez ve hicbir isi yok.
            elif ord(k) == 0x7F:
                yield i, j, 0x7F


print("Kaynak dosyalari taraniyor")
_bakilan = 0
_bulgu: list[str] = []
for _p in KOK.rglob("*"):
    if not _p.is_file() or _p.suffix.lower() not in UZANTI:
        continue
    if any(_d in _p.parts for _d in DISLANAN):
        continue
    try:
        _m = _p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        continue
    _bakilan += 1
    for _satir, _sutun, _kod in _sorunlu(_m):
        _bulgu.append(f"{_p.relative_to(KOK)}:{_satir}:{_sutun}  "
                      f"0x{_kod:02X}")

# TARAMA GERCEKTEN CALISMALI. Dosya bulunamazsa sinama sessizce yesil
# doner ve hicbir sey korumaz -- bu depoda ayni kusur dagitimi
# durdurdu, ters yonden.
esit(_bakilan > 50, True, f"kaynak dosyalari tarandi ({_bakilan})")

if _bulgu:
    print(chr(10) + "  GORUNMEZ DENETIM KARAKTERI:")
    for _b in _bulgu[:20]:
        print(f"    {_b}")
    print(chr(10) + "  Bunlar editorde GORUNMEZ. Kaynakta dogru yazilmis"
          + chr(10) + "  gibi duran desen, aslinda baska bir sey ariyor.")
esit(len(_bulgu), 0, f"hicbir kaynakta gizli denetim karakteri yok "
                     f"({_bakilan} dosya)")

# KONTROLUN KENDISI CALISIYOR MU.
#
# Tarayici dogru calismiyorsa yukaridaki iddia da degersiz: bos bir
# kume her zaman bos kume dondurur. Bilerek bozulmus bir ornek
# veriliyor ve YAKALANMASI bekleniyor.
_ornek = "desen = re.compile(" + chr(34) + "<a" + chr(8) + ">" + chr(34) + ")"
esit([x[2] for x in _sorunlu(_ornek)], [0x08],
     "tarayici bilerek bozulmus ornegi yakaliyor")
esit(list(_sorunlu("normal" + chr(9) + "satir" + chr(10) + "ikinci")), [],
     "satir sonu ve sekme sorun sayilmiyor")

print(chr(10) + f"TUM TESTLER GECTI ({_gecti})")
