# -*- coding: utf-8 -*-
"""Yazi tiplerini uretir: degisken eksenleri sabitler, Turkce icin keser.

ELLE CALISTIRILIR, CI'DA DEGIL
------------------------------
`fontTools` ve `brotli` gerektiriyor; ikisi de `requirements.txt`e
KONMADI. O dosyanin basindaki ilke acik: "her yeni bagimlilik,
kirilabilecek yeni bir parca demek". Bunlar insa aninda degil, yazi
tipi degisecegi zaman -- yani yilda belki bir kez -- gerekiyor.

    python -m pip install fonttools brotli zopfli
    python site/yuz_kes.py

Cikti: `site/statik/yuz/*.woff2` ve `kapsam.json`.

KESIM SINIRI ICERIKTEN DEGIL, UNICODE BLOKLARINDAN
--------------------------------------------------
Sitede o an basilan karakterlere gore kesmek cazip: dosya cok daha
kucuk olurdu. Ama yarin yayimlanacak tek bir Lehce ada ("Szczecin"),
Romence bir soyada ("Isarescu") ya da bir para birimi isaretine
takilir ve o kelime SESSIZCE yedek yazi tipiyle cizilirdi. Sayfa
kirilmaz, kimse fark etmez -- bu depodaki en pahali kusur sinifi.

Sinir bu yuzden olculebilir bir yerde duruyor: Latin + Latin
Genisletilmis-A (Turkce, Lehce, Cekce, Macarca, Romence, Baltik,
Iskandinav adlarinin tamami), Romence virgullu harfler, noktalama,
para birimleri, oklar ve temel matematik isaretleri.

AGIRLIK ARALIGI 380-800
-----------------------
`stil.css` icinde kullanilan agirliklarin hepsi (400/500/600/650/700/
800) bu araliga giriyor. Dar tutulsaydi 800 isteyen basliklar SAHTE
KALIN cizilirdi: tarayici glifi kendi kalinlastirir ve sonuc bulanik
olur.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
HEDEF = KOK / "statik" / "yuz"

#: Kapsanan blok ve tek tek kod noktalari. Sira onemli degil.
ARALIKLAR: tuple[tuple[int, int], ...] = (
    (0x0000, 0x00FF),   # Latin + Latin-1 (c, o, u, a, â ...)
    (0x0100, 0x017F),   # Latin Genisletilmis-A (g, s, I, i, Lehce, Cek...)
    (0x0218, 0x021B),   # Romence virgullu S ve T
    (0x01E6, 0x01E7),
    (0x0237, 0x0237),   # noktasiz j
    (0x2010, 0x2027),   # tireler, tirnaklar, uc nokta
    (0x2030, 0x2044),   # binde, kesir cizgisi
    (0x205F, 0x205F),
    (0x20AC, 0x20AC),   # euro
    (0x20BA, 0x20BA),   # TURK LIRASI
    (0x20B9, 0x20B9),
    (0x20BD, 0x20BD),
    (0x2113, 0x2113), (0x2116, 0x2116), (0x2122, 0x2122),
    (0x00B0, 0x00B1),
    (0x2190, 0x2199),   # oklar
    (0x2212, 0x2212),   # matematik eksi (tireden farkli)
    (0x2217, 0x2217), (0x2248, 0x2248), (0x2260, 0x2260),
    (0x2264, 0x2265),
    (0x25A0, 0x25A0), (0x25AA, 0x25AA), (0x25B2, 0x25B2),
    (0x25B4, 0x25B4), (0x25BC, 0x25BC), (0x25BE, 0x25BE),
    (0x25CF, 0x25CF), (0x2022, 0x2022),
    (0x2713, 0x2714), (0x00D7, 0x00D7),
    (0xFEFF, 0xFEFF), (0xFFFD, 0xFFFD),
)

#: OpenType ozellikleri. `tnum` sutunlarda rakam hizasi icin sart,
#: `locl` Turkce i/I esleri icin, `kern` ve `liga` metin kalitesi icin.
OZELLIKLER = ("kern,liga,calt,tnum,lnum,onum,frac,ccmp,locl,mark,mkmk,"
              "case,ss01")

#: (kaynak ttf, sabitlenen eksenler, cikti)
ISLER = (
    # Serif YALNIZCA basliklarda; optik boyut baslik olceginde (28)
    # sabitlendi. Ekseni degisken birakmak 49 KB -> 111 KB yapiyordu
    # (olculdu) ve kazanc o bedele degmiyordu.
    ("Newsreader.ttf", ("opsz=28", "wght=380:800"), "newsreader-tr.woff2"),
    # Sans metin ve arayuz yuzu; genislik ekseni 100'de sabit.
    ("Archivo.ttf", ("wdth=100", "wght=380:800"), "archivo-tr.woff2"),
)


def birlesik_unicode() -> str:
    return ",".join(f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}"
                    for a, b in ARALIKLAR)


def kes(kaynak: pathlib.Path, eksenler: tuple[str, ...],
        cikti: pathlib.Path) -> None:
    ara = cikti.with_suffix(".ara.ttf")
    adimlar = (
        ["python", "-m", "fontTools.varLib.instancer", str(kaynak),
         *eksenler, "-o", str(ara)],
        ["python", "-m", "fontTools.subset", str(ara),
         f"--unicodes={birlesik_unicode()}",
         f"--layout-features={OZELLIKLER}",
         "--flavor=woff2", "--with-zopfli", "--no-hinting",
         "--desubroutinize", "--name-IDs=1,2,3,4,5,6",
         f"--output-file={cikti}"],
    )
    for adim in adimlar:
        sonuc = subprocess.run(adim, capture_output=True, text=True)
        if sonuc.returncode:
            raise SystemExit(f"{cikti.name}: {sonuc.stderr.strip()[-500:]}")
    ara.unlink(missing_ok=True)


def kapsam_yaz() -> None:
    """Kapsanan kod noktalarini, YAZI TIPLERININ KENDISINDEN yazar.

    ILK SURUM YANLISTI VE SESSIZCE YANLISTI
    ---------------------------------------
    Onceki hali yukaridaki `ARALIKLAR` listesini yaziyordu, yani
    ISTENEN kapsami -- GERCEKLESEN kapsami degil. fontTools'a bir
    aralik vermek, o araligin yazi tipinde BULUNDUGU anlamina gelmez:
    kaynak yazi tipinde olmayan glif cikti dosyasina da girmez.

    Olculdu (2026-10-04): takvim satirindaki ● (U+25CF) listede vardi
    ama Newsreader'da da Archivo'da da YOKTU. `insa.py` denetimi onu
    "kapsandi" sayiyor, tarayici ise yedek yuzle ciziyordu. Yani
    koruma, OLMAYAN bir kapsami bildiriyordu -- en kotu koruma turu:
    bakiliyor sanirsin, bakilmaz.

    Simdi liste cmap'ten geliyor ve uydurmasi mumkun degil.

    BIRLESIM, KESISIM DEGIL
    -----------------------
    `--yuz-baslik` zinciri "Netaris Serif, Netaris Sans, <sistem>".
    Yalnizca birinde bulunan bir karakter, SISTEM yuzune dusmeden o
    birinden geliyor. Sorulan soru "sistem yuzune dusuyor mu"
    oldugundan dogru olcu BIRLESIM. Yalnizca birinde olanlari
    `dogrula()` ayrica yaziyor.
    """
    from fontTools.ttLib import TTFont

    kodlar: set[int] = set()
    for _, _, ad in ISLER:
        kodlar |= set(TTFont(HEDEF / ad).getBestCmap())

    araliklar: list[list[int]] = []
    for kod in sorted(kodlar):
        if araliklar and kod == araliklar[-1][1] + 1:
            araliklar[-1][1] = kod
        else:
            araliklar.append([kod, kod])

    (HEDEF / "kapsam.json").write_text(
        json.dumps({"_not": "yuz_kes.py uretir -- elle duzenlemeyin;"
                            " degerler woff2 cmap'lerinin BIRLESIMI",
                    "araliklar": araliklar},
                    ensure_ascii=False, indent=1) + chr(10),
        encoding="utf-8")
    print(f"  kapsam.json: {len(kodlar)} kod nokta,"
          f" {len(araliklar)} aralik")


def dogrula() -> None:
    """Uretilen dosyalar sozlesmeyi saglıyor mu.

    SOZLESME IKI KADEMELI, cunku yedek zinciri oyle kurulu:

        --yuz-baslik: "Netaris Serif", "Netaris Sans", <sistem>

    1. TURKCE ICIN SART olan glifler IKISINDE DE olmali. Baslik
       serifle cizilir; serifte eksik bir "g" varsa o tek harf sans'tan
       gelir ve baslik ortasinda yuz degisir -- goze carpan ama sebebi
       anlasilmayan bir kusur.

    2. Geri kalan Latin Genisletilmis-A glifleri EN AZ BIRINDE yeterli.
       Newsreader'da Ĳ ĳ ŉ ſ yok (olculdu) -- bunlar Hollandaca
       digrafi, birakilmis bir kisaltma ve uzun s; bir Turkce finans
       sitesinde basilmalari pratikte imkansiz. Birinde bulunmalari,
       zincirin onlari dogru yerden almasina yetiyor. Yazi tipinin
       KENDISINDE olmayan glifi "eksik" diye kirmizi yakmak, duzeltmesi
       mumkun olmayan bir sinama olurdu.
    """
    from fontTools.ttLib import TTFont

    kapsamlar = {ad: set(TTFont(HEDEF / ad).getBestCmap())
                 for _, _, ad in ISLER}
    for ad, kodlar in kapsamlar.items():
        print(f"  {ad:26s} {len(kodlar):4d} kod nokta")

    #: Turkce metnin TAMAMI icin gereken kume -- ikisinde de aranir.
    #: ASCII noktalama ayrica yazilmiyor: U+0020-U+007E araligi
    #: asagidaki donguyle zaten kapsaniyor ve elle yazilan bir liste,
    #: ters bolu gibi karakterlerde kacis hatasina acik olurdu.
    SART = ("ıİğĞşŞçÇöÖüÜâÂîÎûÛ₺‰·—–…“”‘’"
            + "".join(chr(c) for c in range(0x20, 0x7F)))
    for ad, kodlar in kapsamlar.items():
        eksik = [c for c in SART if ord(c) not in kodlar]
        if eksik:
            raise SystemExit(f"{ad}: Turkce icin SART glifler eksik: "
                             f"{''.join(eksik)}")
    print("  sart kume: iki yuzde de tam")

    #: Avrupa adlari -- en az BIRINDE bulunmali.
    GENIS = [chr(c) for c in range(0x0100, 0x0180)] + ["ș", "ț", "Ș", "Ț"]
    hicbirinde = [c for c in GENIS
                  if not any(ord(c) in k for k in kapsamlar.values())]
    if hicbirinde:
        raise SystemExit("hicbir yuzde yok: " + "".join(hicbirinde))
    yalniz_birinde = [c for c in GENIS
                      if sum(ord(c) in k for k in kapsamlar.values()) == 1]
    print(f"  genis kume: hepsi en az bir yuzde"
          f" ({len(yalniz_birinde)} tanesi yalnizca birinde:"
          f" {''.join(yalniz_birinde) or '-'})")


def main() -> int:
    eksikler = [k for k, _, _ in ISLER if not (HEDEF / k).exists()]
    if eksikler:
        print("Once kaynak TTF dosyalarini bu klasore indirin:")
        print("  https://github.com/google/fonts/tree/main/ofl/newsreader")
        print("  https://github.com/google/fonts/tree/main/ofl/archivo")
        print("  eksik:", ", ".join(eksikler))
        return 1
    for kaynak, eksenler, ad in ISLER:
        kes(HEDEF / kaynak, eksenler, HEDEF / ad)
        kb = (HEDEF / ad).stat().st_size / 1024
        print(f"  {ad:26s} {kb:6.1f} KB")
    kapsam_yaz()
    dogrula()
    print("  kapsam.json yazildi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
