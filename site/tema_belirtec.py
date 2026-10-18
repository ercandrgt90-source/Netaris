# -*- coding: utf-8 -*-
"""TASARIM BELIRTECLERI -- tek kaynak `stil.css`, mobil ONDAN okuyor.

NEDEN AYRISTIRMA, NEDEN ELLE YAZMA DEGIL
----------------------------------------
Mobil uygulamanin da renklere ihtiyaci var. Iki yol vardi:

1. Paleti uygulama koduna elle yazmak.
2. `stil.css`ten OKUMAK.

Ikincisi secildi, cunku birincisi bu depoda bilinen bir kusur
sinifidir: ayni kural iki yerde durur, biri duzelir, oteki unutulur.
Renk ozellikle sinsi -- ayrilma hicbir hata uretmez, yalnizca
uygulama ile site farkli gorunur ve kimse ne zaman ayrildigini
bilemez.

Ayristirma tek yonlu: `stil.css` AUTORITE, bu modul onu okuyor.
CSS'e dokunan kimse mobil tarafi dusunmek zorunda degil.

SITENIN ZATEN BIR KOYU TEMASI VAR
---------------------------------
Olculdu (2026-10-18): koyu tema sicak bir siyaha (`--zemin #14130f`)
ve parlak teal vurguya (`--vurgu #2dd4bf`) dayaniyor; erisilebilirlik
icin artis/azalis renkleri ayrica parlatilmis. Yani uygulama icin
yeni bir koyu palet UYDURMAYA gerek yok -- karar verilmis ve yayinda
sinanmis.

AYRISTIRICI NEDEN BU KADAR TITIZ
--------------------------------
Ilk yazim duz bir duzenli ifadeydi ve YANLIS PALET uretti:

    --zemin  #fff     --yazi  #000    --cizgi  #bbb

Bunlar sitenin paleti degil, `@media print` blogunun paleti --
baskida siyah-beyaz zorlaniyor. Iki ayri sebeple kacti:

1. **Yorumlar.** Dosyada 610 yorum var ve 17'si suslu parantez
   iceriyor; "ic ice parantez yok" varsayimi bu yuzden kirildi.
2. **Medya baglami.** `:root` dosyada SEKIZ yerde geciyor; biri
   `@media print`, biri `@media (prefers-color-scheme: dark)`
   icinde. Secici tek basina hangi paleti kurdugunu SOYLEMIYOR.

Bu yuzden ayristirici yorumlari soyuyor ve her blogun at-kural
baglamini takip ediyor. `print`, `prefers-contrast` ve
`forced-colors` baglamlari DISLANIYOR: ucu de erisilebilirlik ya da
baski icin paleti bilincli olarak bozuyor.

CSS CASCADE'I TAKLIT EDILIYOR
-----------------------------
Kabul edilen bloklar DOSYA SIRASINDA uzerine yaziliyor. Tek bir
blogu okuyup "palet bu" demek, dosyanin asagisindaki duzeltmeleri
kacirmak olurdu.
"""

from __future__ import annotations

import pathlib
import re

#: Taban blogu -- damgasiz okurun gordugu palet.
#:
#: BU BLOK EN ONEMLISI. Olculdu (2026-09-30): bes jeton yalnizca
#: `[data-tema]` bloklarinda tanimliydi, taban `:root`ta yoktu. Tema
#: secimi yapmamis okur -- yani COGUNLUK -- o renkleri HIC gormuyordu
#: ve kusur sessizdi.
TABAN = ":root"

#: Koyu temayi kuran seciciler. Ikisi birden gerekli: biri isletim
#: sistemi koyu modunda (medya sorgusu icinde), oteki okur acikca
#: koyu sectiginde (ust duzeyde).
KOYU_SECICILER = (
    ':root:not([data-tema="light"])',
    ':root[data-tema="dark"]',
)

#: Acik temayi okurun ACIK SECIMIYLE kuran secici.
ACIK_SECICILER = (':root[data-tema="light"]',)

#: Bu at-kurallarin ICINDEKI palet SITENIN PALETI DEGIL.
#:
#: `print` baskida siyah-beyaz zorluyor; `prefers-contrast` ve
#: `forced-colors` erisilebilirlik icin kontrasti bilincli olarak
#: sertlestiriyor. Ucu de dogru CSS ama mobil temanin kaynagi
#: olamaz -- ilk yazimda tam bu yuzden yanlis palet cikti.
DISLANAN_BAGLAM = ("print", "prefers-contrast", "forced-colors")

#: Mobil uygulamanin EN AZ ihtiyac duydugu jetonlar.
#:
#: Liste bir sozlesme: bu jetonlardan biri CSS'ten kalkarsa uygulama
#: renksiz bir yuzey basar ve bunu kimse fark etmez.
ZORUNLU = (
    "zemin", "panel", "cizgi", "yazi", "vurgu",
    "artis", "azalis", "uyari", "notr",
    "ust-zemin", "ust-yazi",
)

_YORUM = re.compile(r"/\*.*?\*/", re.S)
_JETON = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+?)\s*(?:;|$)", re.I)
_BOSLUK = re.compile(r"\s+")


def _deger(ham: str) -> str:
    """Jeton degerini tek satira indirir.

    NEDEN GEREKLI: CSS'te uzun degerler satira boluniyor. Yazi tipi
    yiginlari bunun tipik ornegi:

        --yuz-baslik: "Netaris Serif", "Netaris Sans",
                      "Iowan Old Style", Charter, Georgia, serif;

    Deger GERCEK satir sonu tasiyor. Olculdu: uretilen TypeScript
    dosyasi bu yuzden derlenmedi (TS1002 "unterminated string
    literal") -- satir sonu dizgenin icinde kaldi.

    CSS acisindan bosluk dizisi tek bosluga esdeger, yani
    normalizasyon anlami DEGISTIRMIYOR.
    """
    return _BOSLUK.sub(" ", ham).strip()


def _yorumsuz(css: str) -> str:
    """Yorumlari soyar. Ayristirmanin ON SARTI -- bkz. modul basi."""
    return _YORUM.sub("", css)


def bloklar(css: str) -> list[tuple[tuple[str, ...], str, dict[str, str]]]:
    """(baglam, secici, jetonlar) uclulerini DOSYA SIRASINDA dondurur.

    `baglam` ice ice at-kural preludlerinin demeti; ust duzey bloklar
    icin bos demet.

    Elle yazilmis bir tarayici: duzenli ifade ic ice parantezi
    sayamiyor ve bu dosyada medya sorgulari gercekten ic ice.
    """
    s = _yorumsuz(css)
    cikti: list[tuple[tuple[str, ...], str, dict[str, str]]] = []
    yigin: list[str] = []          # at-kural preludleri
    i, n, basla = 0, len(s), 0
    while i < n:
        c = s[i]
        if c == "{":
            onek = s[basla:i].strip()
            if onek.startswith("@"):
                yigin.append(onek)
            else:
                # Bildirim blogu: eslesen kapanisa kadar oku.
                derin, j = 1, i + 1
                while j < n and derin:
                    if s[j] == "{":
                        derin += 1
                    elif s[j] == "}":
                        derin -= 1
                    j += 1
                govde = s[i + 1:j - 1]
                jetonlar = {a: _deger(d) for a, d in _JETON.findall(govde)}
                if jetonlar:
                    cikti.append((tuple(yigin), onek, jetonlar))
                i = j
                basla = i
                continue
            i += 1
            basla = i
            continue
        if c == "}":
            if yigin:
                yigin.pop()
            i += 1
            basla = i
            continue
        i += 1
    return cikti


def _uygun(baglam: tuple[str, ...]) -> bool:
    """Bu baglam sitenin PALETINI kuruyor mu."""
    birlesik = " ".join(baglam).lower()
    return not any(d in birlesik for d in DISLANAN_BAGLAM)


def _birlestir(hepsi, seciciler) -> dict[str, str]:
    """Secilen bloklari SIRAYLA uzerine yazar -- CSS cascade'i gibi."""
    toplam: dict[str, str] = {}
    for baglam, secici, jetonlar in hepsi:
        if secici in seciciler and _uygun(baglam):
            toplam.update(jetonlar)
    return toplam


def cikar(css: str) -> dict:
    """CSS metninden iki temayi cikarir.

    Donus: {"taban": {...}, "acik": {...}, "koyu": {...}}

    `acik` ve `koyu` TAM palet: uygulama tarafi iki sozlugu
    birlestirmek zorunda kalmasin, cunku o birlestirmeyi unutmak
    yarim boyanmis bir ekran demek.
    """
    hepsi = bloklar(css)
    taban = _birlestir(hepsi, (TABAN,))
    acik = dict(taban)
    acik.update(_birlestir(hepsi, ACIK_SECICILER))
    koyu = dict(taban)
    koyu.update(_birlestir(hepsi, KOYU_SECICILER))
    return {"taban": taban, "acik": acik, "koyu": koyu}


def eksik_jetonlar(css: str) -> list[str]:
    """Tema blogunda tanimli ama TABANDA olmayan jetonlar.

    OLCULEN GERCEK BIR KUSUR (2026-09-30): bes jeton yalnizca
    `[data-tema]` bloklarinda tanimliydi. Tema damgasi yalnizca okur
    acikca secim yaptiginda yaziliyor; secmeyen okur -- cogunluk --
    o renkleri hic gormuyordu. Hicbir sey patlamiyordu, palet
    eksikti.

    Bos liste = saglam.
    """
    hepsi = bloklar(css)
    taban = _birlestir(hepsi, (TABAN,))
    tema = set(_birlestir(hepsi, KOYU_SECICILER))
    tema |= set(_birlestir(hepsi, ACIK_SECICILER))
    return sorted(tema - set(taban))


def dosyadan(yol: pathlib.Path) -> dict:
    return cikar(yol.read_text(encoding="utf-8"))


#: Satir sonu SABIT OLARAK tutuluyor.
#:
#: Bu depoda ters boluler kabuk here-doc'undan gecerken sessizce
#: baska bir seye donusuyor ("\\n" -> "n") ve sonuc derlenmeyen ya da
#: daha kotusu YANLIS derlenen kod oluyor. Sabit, o tuzagi tamamen
#: ortadan kaldiriyor.
SATIR = chr(10)

#: Uretilen TypeScript dosyasinin basligi.
TS_BASLIK = (
    "// OTOMATIK URETILDI -- ELLE DUZENLEMEYIN." + SATIR
    + "//" + SATIR
    + "// Kaynak: site/statik/stil.css" + SATIR
    + "// Ureten: site/tema_belirtec.py  (ts_yedek)" + SATIR
    + "//" + SATIR
    + "// Bu dosya uygulamanin ILK ACILIS paletidir. Calisma aninda"
    + SATIR
    + "// /v1/tema.json okunuyor ve bu degerlerin uzerine yaziliyor;"
    + SATIR
    + "// yedek yalnizca ag henuz cevap vermemisken kullaniliyor."
    + SATIR
    + "//" + SATIR
    + "// Yeniden uretmek: python site/tema_yedek_yaz.py" + SATIR
)


def ts_yedek(yol: pathlib.Path) -> str:
    """Yedek paleti TypeScript kaynagi olarak uretir.

    NEDEN YEDEK GEREKLI: uygulama paleti `/v1/tema.json`dan okuyor ama
    ILK ACILISTA ag henuz cevap vermemis olabilir. Yedek olmadan ilk
    kare renksiz basilir -- kullanicinin gordugu ilk sey bozuk bir
    ekran olur.

    DOSYA ELLE DUZENLENMEZ: `test_tema_belirtec.py` dosyanin CSS ile
    bire bir ayni oldugunu siniyor, yani ayrilma sessiz kalmiyor.
    """
    temalar = dosyadan(yol)

    def blok(ad: str, jetonlar: dict) -> str:
        govde = "".join(
            '  "' + anahtar + '": "' + deger.replace('"', r"\"") + '",'
            + SATIR
            for anahtar, deger in sorted(jetonlar.items()))
        return ("export const " + ad + ": Palet = {" + SATIR
                + govde + "};" + SATIR)

    zorunlu = "".join('  "' + z + '",' + SATIR for z in ZORUNLU)
    return (TS_BASLIK + SATIR
            + "export type Palet = Record<string, string>;" + SATIR + SATIR
            + blok("ACIK_YEDEK", temalar["acik"]) + SATIR
            + blok("KOYU_YEDEK", temalar["koyu"]) + SATIR
            + "export const ZORUNLU_JETONLAR = [" + SATIR
            + zorunlu + "] as const;" + SATIR)


def besleme(yol: pathlib.Path, surum: int = 1) -> dict:
    """Mobil icin tema dosyasinin icerigi.

    `zorunlu` listesi de yaziliyor: uygulama hangi jetonlara
    guvenebilecegini dosyadan ogreniyor, kendi icine gommuyor.
    """
    temalar = dosyadan(yol)
    return {
        "surum": surum,
        "kaynak": "site/statik/stil.css",
        "zorunlu": list(ZORUNLU),
        "acik": temalar["acik"],
        "koyu": temalar["koyu"],
    }
