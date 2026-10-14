# -*- coding: utf-8 -*-
"""YAYINDAKI METINDE ARDISIK YINELENEN KELIME OLMAMALI.

BU KORUMA NEDEN VAR -- YAKALANDI (2026-10-14)
---------------------------------------------
Bilanco sayfasinin olcum basligi `f"## {donem} dönemi ölçümleri"`
diye kuruluyor. Takvim disi mali yila sahip sirketler icin eklenen
yeni donem etiketi "2026 mart–mayıs dönemi" ile BITIYORDU, yani
baslik:

    ## 2026 mart–mayıs dönemi dönemi ölçümleri

Kusur yayina CIKMADI -- sayfa uretilmeden once gozle okundugu icin
goruldu. Ama gozle okumak bir koruma degil: ayni sinif hata
(sablonun ekledigi kelimeyi degerin de tasimasi) her yeni etiket
bicimiyle yeniden uretilebilir.

OLCUT GENEL, BILANCOYA OZEL DEGIL. Butun uretilen metni tariyor:
sablon + veri birlesiminden dogan her kelime tekrarini yakalar.

YANLIS ALARM OLCULDU: kural, duzeltmeden sonraki 890 analiz ve
butun haber sayfalarinda SIFIR bulgu veriyor. Yani Turkce'de
mesru ardisik tekrar (varsa) bu derlemede yok; esik gevsetmeye
gerek kalmadi.

KOD BLOKLARI HARIC: tablo hizalama satirlari ve kod ornekleri
tekrar gibi gorunebiliyor.
"""

from __future__ import annotations

import io
import pathlib
import re

_KOK = pathlib.Path(__file__).resolve().parent
ICERIK = _KOK / "icerik"

#: Ardisik ayni kelime. En az iki harf: "bir bir" gercek bir tekrar,
#: tek harfli yineleme (madde isareti, tablo cizgisi) degil.
DESEN = re.compile(
    r"\b([0-9A-Za-zÇĞİÖŞÜçğıöşü]{2,})\s+\1\b")

#: Kod blogu ve on bilgi: metin degil, veri.
_KOD = re.compile(r"```.*?```", re.S)
_TABLO_CIZGI = re.compile(r"^\|[\s:|-]+\|$", re.M)


def temizle(metin: str) -> str:
    """Metin olmayan parcalari cikarir."""
    metin = _KOD.sub(" ", metin)
    return _TABLO_CIZGI.sub(" ", metin)


def main() -> int:
    if not ICERIK.is_dir():
        print(f"DUSTU  içerik dizini yok: {ICERIK}")
        return 1
    bakilan = 0
    bulgu: list[tuple[str, str, str]] = []
    for p in sorted(ICERIK.rglob("*.md")):
        bakilan += 1
        t = temizle(io.open(p, encoding="utf-8").read())
        for m in DESEN.finditer(t):
            bas = max(0, m.start() - 40)
            bulgu.append((p.name, m.group(1),
                          " ".join(t[bas:m.end() + 30].split())))
    print(f"  taranan sayfa : {bakilan}")
    print(f"  bulgu         : {len(bulgu)}")
    if bulgu:
        print(f"\nDUSTU  {len(bulgu)} yerde ardışık yinelenen kelime var")
        for ad, kelime, baglam in bulgu[:10]:
            print(f"    {ad}  ({kelime!r})")
            print(f"      ...{baglam}...")
        if len(bulgu) > 10:
            print(f"    ... ve {len(bulgu) - 10} yer daha")
        print("\n  Genelde sebep tek: şablonun eklediği kelimeyi değer de")
        print("  taşıyor (ör. \"{donem} dönemi\" + donem=\"... dönemi\").")
        return 1
    print("\nGECTI  ardışık yinelenen kelime yok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
