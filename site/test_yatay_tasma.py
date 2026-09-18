# -*- coding: utf-8 -*-
"""DAR EKRANDA SAYFA YATAY KAYMAMALI.

BU DOSYA NEDEN VAR
------------------
Mobil denetimi (2026-09-18) sirasinda tasma korumasinin VAR oldugu
ama HICBIR SINAMANIN tutmadigi goruldu. Koruma stil.css'in sonundaki
"yatay tasma yok" blogunda yasiyor ve tek bir satirin silinmesi
sayfayi her telefonda yana kaydirir -- kimse fark etmeden.

Ayni gun canli akisin mobilde yok oldugu, son dakika duraklatma
dugmesinin gizlendigi ve duyarlilik gerekcesinin dustugu bulundu;
ucu de CSS'te tek satirdi ve ucu de sessizce olmustu. Tasma korumasi
ayni kirilganliga sahipti.

NEDEN "GREP" DEGIL, HESAP
-------------------------
"Su satir dosyada var mi" diye sormak SAHTE GUVEN uretir: satir
yorumun icinde olabilir, sonraki bir kural onu ezebilir, ya da metin
degisip iddia sessizce anlamsizlasir. Burada sorular hesaplanarak
cevaplaniyor:

  * dar ekranda uygulanan kurallar arasinda 320 pikseli ASAN sabit
    genislik var mi (medya kosullari cozulerek),
  * uretilen ciktidaki her <table> korumali mi (sarmal ya da kural).

NE SINANIYOR
------------
1. Tarayici bilinen girdide dogru cevap veriyor (kendi kendini sinar).
2. 320px ekranda uygulanan hicbir kural sabit 320px+ genislik vermiyor.
3. Uretilen ciktidaki her tablo ya `.tablo-kaydir` sarmalinda ya da
   mobil kuralla kendi kutusunda kayiyor.
4. Uzun kirilamayan dizgeler icin `overflow-wrap` korumasi duruyor.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

#: En dar yaygin telefon (iPhone SE 1. nesil). Buna sigan her sey
#: daha genis telefonlara da sigar.
DAR = 320

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def bloklari_coz(css: str) -> list[tuple[str, str, str]]:
    """(secici, govde, medya_kosulu) -- ic ice @media'lari cozer."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    out: list[tuple[str, str, str]] = []

    def gez(metin: str, medya: str = "") -> None:
        i = 0
        while i < len(metin):
            m = re.compile(r"@media([^{]+)\{").search(metin, i)
            k = re.compile(r"([^{}@]+)\{([^{}]*)\}").search(metin, i)
            if m and (not k or m.start() < k.start()):
                bas, d, j = m.end(), 1, m.end()
                while j < len(metin) and d:
                    if metin[j] == "{":
                        d += 1
                    elif metin[j] == "}":
                        d -= 1
                    j += 1
                gez(metin[bas:j - 1], m.group(1).strip())
                i = j
            elif k:
                out.append((k.group(1).strip(), k.group(2), medya))
                i = k.end()
            else:
                break

    gez(css)
    return out


def dar_ekranda_gecerli(medya: str) -> bool:
    """Bu blok DAR piksellik ekranda uygulanir mi?"""
    if not medya:
        return True
    mn = re.search(r"min-width:\s*(\d+)px", medya)
    mw = re.search(r"max-width:\s*(\d+)px", medya)
    if mn and int(mn.group(1)) > DAR:
        return False
    if mw and int(mw.group(1)) < DAR:
        return False
    return True


def genis_bulgular(css: str) -> list[tuple[int, str, str]]:
    """DAR'i asan sabit genislikler: (px, ozellik, secici)."""
    b = []
    for sec, govde, medya in bloklari_coz(css):
        if not dar_ekranda_gecerli(medya):
            continue
        for mm in re.finditer(
                r"(?<![-\w])(min-width|width|flex-basis)\s*:\s*(\d+)px", govde):
            if int(mm.group(2)) > DAR:
                b.append((int(mm.group(2)), mm.group(1), sec))
        # `minmax(NNNpx, ...)` izgara tasmasinin en yaygin sebebi ve
        # `width` aramasina TAKILMAZ -- ayri sorulmali.
        for mm in re.finditer(r"minmax\(\s*(\d+)px", govde):
            if int(mm.group(1)) > DAR:
                b.append((int(mm.group(1)), "minmax", sec))
    return b


print("\nTarama gercekten calisiyor mu")
# Bilinen girdi. Sitenin icerigine baglanmiyor: site nasil degisirse
# degissin bu capa gecerli kalir.
_DENEME = """
.genis { width: 900px; }
.dar { width: 200px; }
.izgara { grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); }
.iyi { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.cizgi { border-width: 900px; }
@media (min-width: 900px) { .masaustu { width: 1200px; } }
@media (max-width: 640px) { .mobil { min-width: 500px; } }
/* @media (max-width: 400px) { .yorumdaki { width: 800px } } */
"""
_d = {(px, oz) for px, oz, _ in genis_bulgular(_DENEME)}
esit((900, "width") in _d, True, "sabit genis kurali yakaliyor")
esit((360, "minmax") in _d, True, "minmax tasmasini yakaliyor")
esit((500, "min-width") in _d, True, "mobil kirilimdaki genisligi yakaliyor")
esit(any(p == 200 or p == 240 for p, _ in _d), False, "dar olani saymiyor")
esit(any(p == 1200 for p, _ in _d), False, "MASAUSTU kuralini saymiyor")
esit(any(p == 900 and o not in ("width",) for p, o in _d), False,
     "`border-width` genislik sanilmiyor")
esit(any(p == 800 for p, _ in _d), False, "YORUM icindeki kurali saymiyor")

print("\n320 piksellik ekranda sabit genislik")
_css = (_SITE / "statik" / "stil.css").read_text(encoding="utf-8")
_b = sorted(genis_bulgular(_css), reverse=True)
if _b:
    print("\n  SAYFAYI YANA KAYDIRABILECEK KURALLAR:")
    for _px, _oz, _sec in _b[:10]:
        print(f"    {_px:>5}px  {_oz:<11} {_sec[:56]}")
esit([(p, o) for p, o, _ in _b], [], f"{DAR}px'i asan sabit genislik yok")

print("\nUzun dizge korumasi")
_bloklar = bloklari_coz(_css)
_sarmali = [(sec, medya) for sec, govde, medya in _bloklar
            if re.search(r"overflow-wrap\s*:\s*(anywhere|break-word)", govde)
            and dar_ekranda_gecerli(medya)]
esit(len(_sarmali) > 0, True,
     f"dar ekranda `overflow-wrap` korumasi var ({len(_sarmali)} kural)")
# Koruma METIN bloklarini kapsamali -- yalnizca bir kose bileseni degil.
_metin = [s for s, _ in _sarmali if re.search(r"(^|,)\s*(p|li|h1|h2|dd)\b", s)]
esit(len(_metin) > 0, True, "koruma metin ogelerini (p/li/h*) kapsiyor")

print("\nUretilen ciktida tablolar")
if not (_CIKTI / "index.html").exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

# Tabloyu KORUYAN iki yol: `.tablo-kaydir` sarmali, ya da dar ekranda
# tabloyu kendi kutusunda kaydiran bir kural.
_kural_korumasi = any(
    re.search(r"(^|,)\s*table\s*$", sec.strip())
    and re.search(r"overflow-x\s*:\s*auto", govde)
    and dar_ekranda_gecerli(medya) and medya
    for sec, govde, medya in _bloklar)

_sarmalsiz: dict[str, int] = {}
_toplam = 0
for _p in _CIKTI.rglob("index.html"):
    _m = _p.read_text(encoding="utf-8", errors="replace")
    for _mm in re.finditer(r"<table([^>]*)>", _m):
        _toplam += 1
        if "tablo-kaydir" in _m[max(0, _mm.start() - 140):_mm.start()]:
            continue
        _c = re.search(r'class="([^"]*)"', _mm.group(1))
        _sarmalsiz[_c.group(1) if _c else "(sinifsiz)"] = \
            _sarmalsiz.get(_c.group(1) if _c else "(sinifsiz)", 0) + 1

esit(_toplam > 100, True, f"ciktida tablo bulundu ({_toplam})")
if _sarmalsiz and not _kural_korumasi:
    print("\n  SARMALSIZ VE KURALSIZ TABLOLAR (dar ekranda sayfayi kaydirir):")
    for _ad, _n in sorted(_sarmalsiz.items(), key=lambda x: -x[1]):
        print(f"    {_n:>5}  {_ad[:40]}")
esit(bool(_sarmalsiz) and not _kural_korumasi, False,
     f"her tablo korumali ({_toplam - sum(_sarmalsiz.values())} sarmalli,"
     f" {sum(_sarmalsiz.values())} taban kuralla)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
