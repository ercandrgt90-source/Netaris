"""Denetim, sablonun GORSEL ONCELIGINI dogru okumali.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-14): denetim "3 haber sayfasinda fotograf yok" uyarisi
uretti ve yayin kararini SARI'ya dusurdu. Uc sayfa elle incelendiginde
hepsinin GRAFIGI oldugu goruldu:

    <svg class="grafik grafik-dusus" aria-label="TÜFE (yıllık): 31,51 %">
    <svg class="grafik grafik-dusus" aria-label="TCMB ağırlıklı fonlama">
    <svg class="grafik grafik-yukselis" aria-label="Cari işlemler hesabı">

Yani denetim, urunun EN DOGRU davranisini kusur sayiyordu. `haber.html`
sablonunun kurali acik:

    SIRA ONEMLI: OLCUM FOTOGRAFTAN ONCE GELIR.
    ... fotograf konu havuzundan gelen bir illustrasyon, grafik ise
    haberin kendi olcumu.

Denetim yalnizca `src="/statik/foto/..."` ariyordu -- yani sablonun
dort dalindan yalnizca birini taniyordu.

IKI KOD YOLU, AYNI KARAR
------------------------
Gorseli SABLON seciyor. Denetim o karari dar bir bicimde YENIDEN
yaziyordu. Bu depoda tekrarlayan tuzak; cozum, ikisini ayni isarete
baglamak: sablonun dort dali da `<figure class="yazi-gorsel">`
uretiyor, denetim de artik onu ariyor.

YANLIS ALARMIN BEDELI
---------------------
`site/test_yayinla.py` icinde zaten yazili: "kirmizi donen ama aslinda
basarili olan bir kosu, sonraki GERCEK kirmiziyi de inandiriciliktan
dusurur."

NE SINANIYOR
------------
Olcum duzeltildi ama KONTROL ZAYIFLATILMADI: gercekten gorselsiz bir
sayfa hala yakalaniyor ve artik ADIYLA yaziliyor.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import denetim                                        # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Sablonun dort dali -- `site/sablonlar/haber.html` ile ayni sira.
GRAFIKLI = ('<article class="yazi"><figure class="yazi-gorsel">'
            '<svg class="grafik grafik-dusus"></svg></figure></article>')
FOTOGRAFLI = ('<article class="yazi">'
              '<figure class="yazi-gorsel yazi-foto">'
              '<img src="/statik/foto/tcmb-7.jpg"></figure></article>')
CIZIMLI = ('<article class="yazi">'
           '<figure class="yazi-gorsel yazi-foto yazi-uretilen">'
           '<img src="/statik/foto/uretilen/kavram-0b4769aa08.jpg">'
           "</figure></article>")
DESENLI = ('<article class="yazi"><figure class="yazi-gorsel">'
           '<svg class="desen"></svg></figure></article>')
GORSELSIZ = '<article class="yazi"><header><h1>Baslik</h1></header></article>'


def _kosu(sayfalar: dict[str, str]) -> list:
    """Sahte bir cikti dizini kurar, gorsel denetimini kosar."""
    with tempfile.TemporaryDirectory() as d:
        kok = pathlib.Path(d)
        (kok / "haber").mkdir(parents=True)
        for ad, govde in sayfalar.items():
            k = kok / "haber" / ad
            k.mkdir()
            (k / "index.html").write_text(govde, encoding="utf-8")
        asil = denetim.CIKTI_DIZINI
        denetim.CIKTI_DIZINI = kok
        try:
            return [b for b in denetim._gorsel_denetimi()
                    if b.alan == "gorsel" and "gorsel yok" in b.mesaj]
        finally:
            denetim.CIKTI_DIZINI = asil


print("\nSablonun DORT dali da gorsel sayiliyor")
for _ad, _govde in (("grafik", GRAFIKLI), ("fotograf", FOTOGRAFLI),
                    ("uretilen cizim", CIZIMLI), ("son care deseni", DESENLI)):
    esit(_kosu({"sayfa": _govde}), [], f"{_ad} olan sayfa uyari URETMIYOR")

print("\nGercekten gorselsiz sayfa HALA yakalaniyor")
# Olcum duzeltildi, kontrol zayiflatilmadi.
_b = _kosu({"bos-sayfa": GORSELSIZ})
esit(len(_b), 1, "gorselsiz sayfa uyari uretiyor")
esit(_b[0].agirlik, "uyari", "agirlik uyari")
esit("bos-sayfa" in _b[0].mesaj, True,
     f"sayfa ADIYLA yaziliyor: {_b[0].mesaj}")

print("\nKarisik dizin -- yalnizca gorselsiz olan isaretleniyor")
_b = _kosu({"grafikli": GRAFIKLI, "fotografli": FOTOGRAFLI,
            "desenli": DESENLI, "bos-bir": GORSELSIZ, "bos-iki": GORSELSIZ})
esit(len(_b), 1, "tek uyari")
esit("2 haber sayfasinda" in _b[0].mesaj, True,
     f"sayi dogru: {_b[0].mesaj}")
esit("bos-bir" in _b[0].mesaj and "bos-iki" in _b[0].mesaj, True,
     "ikisi de adiyla yaziliyor")
esit("grafikli" not in _b[0].mesaj, True, "grafikli sayfa ANILMIYOR")

print("\nGERCEK sablon ciktisi -- kalip degil, uretilen sayfa")
# Kalip uydurmak, kalibi sinamaktir. Diskte gercek cikti varsa
# ondan da okunuyor: sablonun bugun urettigi isaret bu.
_canli = denetim.CIKTI_DIZINI / "haber"
if _canli.exists():
    _ornek = next((p / "index.html" for p in _canli.iterdir()
                   if (p / "index.html").exists()), None)
    if _ornek is not None:
        esit(bool(denetim.GORSEL_FIGUR.search(
            _ornek.read_text(encoding="utf-8"))), True,
            f"uretilen sayfada isaret bulunuyor ({_ornek.parent.name[:28]})")
    else:
        print("  ATLANDI  cikti dizininde haber sayfasi yok")
else:
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
