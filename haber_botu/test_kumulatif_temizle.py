"""`kumulatif_temizle.py` sinamalari.

NEDEN BU DOSYA VAR
------------------
Bu aracin HIC testi yoktu ve aylardir yanlis calisiyordu. 2026-08-28'de
olculdu: bugune kadar TEK BIR SILMEYI bile depoya isleyememisti.

Sebep aracin kendisinde degil, ciktisinin nereye gittigindeydi -- geri
yazma adimi `git add --ignore-removal` kullaniyor ve o bayrak silmeleri
sahnelemiyor. Arac her kosuda dosyayi siliyor, o kosunun sitesi temiz
cikiyor, sonra dosya depoda durdugu icin bir sonraki kurulumda geri
geliyordu. Disaridan bakinca "calisiyor" gorunuyordu.

Sonuc canliya cikti: ENDAE ve ENTRA'nin ayni donemi icin IKISER analiz
sayfasi yayimlandi -- biri "2026/6" etiketiyle, yani okurun "ikinci
ceyrek" sanacagi bicimde. Ayni sirketin ayni donemine dair iki farkli
sayfa, bir bicim sorunu degil GUVENILIRLIK sorunudur.

BURADA NE KORUNUYOR
-------------------
  1. Arac yalnizca KARSILIGI URETILMIS sayfayi siler. Karsiligi
     olmayani silmek, bir bicim sorununu icerik kaybina cevirir.
  2. `--liste` GERCEKTEN silinenleri yazar -- ne eksik ne fazla.
     Silinmemis bir yolu bildirmek, geri yazma adiminin depoda duran
     saglam bir sayfayi silmesi demek olurdu.
  3. Olcum modu hicbir sey silmez ve BOS liste yazar.
  4. Liste dosyasi her durumda olusur. Geri yazma adimi "arac hic
     kosmadi" ile "kostu, silecek sey bulmadi" arasindaki farki
     gormek zorunda.
  5. Yollar depo koklu ve POSIX ayracli. Is akisindaki
     `git rm --cached -- <yol>` tam olarak bu bicimi bekliyor;
     Windows ayraci ya da mutlak yol sessizce eslesmez.

Calistirma:  python test_kumulatif_temizle.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import kumulatif_temizle as kt  # noqa: E402

_gecti = 0
_kaldi = 0


def dogru(aciklama: str, kosul) -> None:
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")


SAYFA = """---
slug: {slug}
baslik: {ad} {donem} bilanço analizi
kod: {kod}
donem: {donem}
kategori: Bilanço Analizi
---

Gövde metni.
"""


def kur(kok: pathlib.Path, sayfalar: list[tuple[str, str, str]]) -> None:
    """Gecici bir analiz klasoru kurar ve modulu ona bagler."""
    analiz = kok / "site" / "icerik" / "analizler"
    analiz.mkdir(parents=True, exist_ok=True)
    for dosya, kod, donem in sayfalar:
        (analiz / dosya).write_text(
            SAYFA.format(slug=dosya[:-3], ad=f"{kod} A.Ş.",
                         kod=kod, donem=donem),
            encoding="utf-8")
    kt.KOK = kok
    kt.ANALIZ = analiz


def calistir(argv: list[str]) -> int:
    eski = sys.argv
    sys.argv = ["kumulatif_temizle.py", *argv]
    try:
        return kt.main()
    finally:
        sys.argv = eski


# --------------------------------------------------------------------
# 1. SINIFLANDIRMA: "2026/6" kumulatif, "2026 2. ceyrek" degil.
#
#    KAP donemleri kumulatif okunur: "2026/6" yilin ilk YARISI demek,
#    ikinci ceyrek degil. Aracin butun karari bu ayrima dayaniyor.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [
        ("2026-6-aaa.md", "AAA", "2026/6"),
        ("2026-2-ceyrek-aaa.md", "AAA", "2026 2. çeyrek"),
        ("2026-6-bbb.md", "BBB", "2026/6"),
    ])
    kum, cey = kt.tara()
    dogru("kumulatif donem tanindi", set(kum) == {"AAA", "BBB"})
    dogru("ceyreklik donem tanindi", set(cey) == {"AAA"})

# --------------------------------------------------------------------
# 2. KARSILIGI OLMAYAN SILINMEZ.
#
#    Bu kural aracin varlik sebebi. 2026-08-21'de olculmustu: 144
#    kumulatif sayfanin yalnizca 33'unun ceyrekligi vardi. Hepsini
#    silmek 111 sirketi SAYFASIZ birakirdi.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [
        ("2026-6-aaa.md", "AAA", "2026/6"),
        ("2026-2-ceyrek-aaa.md", "AAA", "2026 2. çeyrek"),
        ("2026-6-bbb.md", "BBB", "2026/6"),
    ])
    liste = kok / "silinen.txt"
    calistir(["--uygula", "--liste", str(liste)])
    analiz = kok / "site" / "icerik" / "analizler"
    dogru("karsiligi olan kumulatif silindi",
          not (analiz / "2026-6-aaa.md").exists())
    dogru("karsiligi OLMAYAN kumulatif KORUNDU",
          (analiz / "2026-6-bbb.md").exists())
    dogru("ceyreklik sayfaya dokunulmadi",
          (analiz / "2026-2-ceyrek-aaa.md").exists())

    # --------------------------------------------------------------
    # 3. LISTE: NE EKSIK NE FAZLA.
    #
    #    Fazla bildirmek, is akisindaki `git rm --cached`in depoda
    #    duran SAGLAM bir sayfayi silmesi demek olurdu.
    # --------------------------------------------------------------
    # OKUMA KORUMALI. Ilk yazimda dogrudan `read_text()` cagriliyordu
    # ve liste hic yazilmadiginda test COKUYORDU. Coken test yalnizca
    # kendi olcumunu degil, KENDINDEN SONRAKILERI de kaybettiriyor --
    # bu oturumda `test_nobetci.js`de tam bu yasandi ve sekiz sinama
    # goze gorunmeden kayboldu.
    dogru("silme sonrasi liste dosyasi yazildi", liste.exists())
    satirlar = ([s for s in liste.read_text(encoding="utf-8").split(chr(10))
                 if s.strip()] if liste.exists() else [])
    dogru("liste yalnizca silineni bildiriyor",
          satirlar == ["site/icerik/analizler/2026-6-aaa.md"])

    # --------------------------------------------------------------
    # 4. YOL BICIMI: depo koklu ve POSIX ayracli.
    #
    #    Is akisi `git rm --cached -- <yol>` cagiriyor. Windows
    #    ayraci ya da mutlak yol, git'te SESSIZCE eslesmez --
    #    `--ignore-unmatch` yuzunden hata da vermez.
    # --------------------------------------------------------------
    #
    # `satirlar and ...` SART: bos listede `all(...)` DOGRU doner ve
    # sinama hicbir sey olcmeden yesil kalir. Bu oturumda dort ayri
    # sinama tam bu sekilde bos calisiyordu.
    dogru("yol POSIX ayracli",
          satirlar and all(chr(92) not in s for s in satirlar))
    dogru("yol depo koklu (mutlak degil)",
          satirlar and all(not pathlib.PurePosixPath(s).is_absolute()
                           and ":" not in s for s in satirlar))

# --------------------------------------------------------------------
# 5. OLCUM MODU: hicbir sey silmez, BOS liste yazar.
#
#    Silmedigi bir yolu bildirse, geri yazma adimi o sayfayi depodan
#    silerdi -- yani olcum modu icerik silerdi.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [
        ("2026-6-aaa.md", "AAA", "2026/6"),
        ("2026-2-ceyrek-aaa.md", "AAA", "2026 2. çeyrek"),
    ])
    liste = kok / "silinen.txt"
    calistir(["--liste", str(liste)])
    analiz = kok / "site" / "icerik" / "analizler"
    dogru("olcum modu hicbir sey silmedi",
          (analiz / "2026-6-aaa.md").exists())
    dogru("olcum modu BOS liste yazdi",
          liste.exists() and liste.read_text(encoding="utf-8").strip() == "")

# --------------------------------------------------------------------
# 6. SILECEK SEY YOKKEN DE LISTE OLUSUR.
#
#    Geri yazma adimi `[ -s "$SILINEN" ]` ile bakiyor. Dosyanin HIC
#    olmamasi ile BOS olmasi ayni sonucu veriyor ama sebepleri farkli;
#    aracin her kosuda dosyayi yazmasi o adimin kosulunu tek anlamli
#    kiliyor.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [("2026-6-bbb.md", "BBB", "2026/6")])
    liste = kok / "silinen.txt"
    calistir(["--uygula", "--liste", str(liste)])
    dogru("silecek sey yokken de liste dosyasi olustu", liste.exists())
    dogru("o liste bos", liste.read_text(encoding="utf-8").strip() == "")

# --------------------------------------------------------------------
# 7. `--liste` VERILMEZSE COKMEZ.
#
#    Arac elle de calistiriliyor; liste yalnizca is akisinin ihtiyaci.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [
        ("2026-6-aaa.md", "AAA", "2026/6"),
        ("2026-2-ceyrek-aaa.md", "AAA", "2026 2. çeyrek"),
    ])
    try:
        cikis = calistir(["--uygula"])
        dogru("--liste'siz calisti", cikis == 0)
    except Exception as e:  # pragma: no cover
        dogru(f"--liste'siz calisti ({e})", False)

# --------------------------------------------------------------------
# 8. BASLIGINDA "BILANCO" GECEN HABER, BILANCO SAYILMAZ.
#
#    GERCEK ORNEK. Onceki olcut "ilk 900 karakterde 'bilanço' geciyor
#    mu" idi ve su sayfayi bilanco analizi sayiyordu:
#
#      "Hürmüz Boğazı'nda savaşın bilançosu: 68 olay, 20 can kaybı"
#      kategori: Makro
#
#    Parcali eslesme: "bilanço" ⊂ "bilançosu". Bu depoda tekrar eden
#    hata sinifi.
#
#    Asagidaki kurgu o sayfanin TEHLIKELI halini kuruyor: ayni baslik
#    ama `kod` bir BIST kodu. Eski olcutle bu sayfa AAA'nin ceyreklik
#    bilancosu sayilir ve arac, AAA'nin GERCEK kumulatif sayfasini --
#    yerine hicbir sey uretilmeden -- silerdi.
# --------------------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    kok = pathlib.Path(t)
    kur(kok, [("2026-6-aaa.md", "AAA", "2026/6")])
    analiz = kok / "site" / "icerik" / "analizler"
    (analiz / "haber.md").write_text(
        "---" + chr(10) + "slug: haber" + chr(10)
        + "baslik: Hürmüz Boğazı'nda savaşın bilançosu: 68 olay"
        + chr(10) + "kod: AAA" + chr(10)
        + "donem: 2026 2. çeyrek" + chr(10)
        + "kategori: Makro" + chr(10) + "---" + chr(10) * 2
        + "Jeopolitik gelişme." + chr(10),
        encoding="utf-8")
    kum, cey = kt.tara()
    dogru("basliginda 'bilanço' gecen haber ceyreklik sayilmadi",
          "AAA" not in cey)

    liste = kok / "silinen.txt"
    calistir(["--uygula", "--liste", str(liste)])
    dogru("o haber yuzunden gercek kumulatif sayfa SILINMEDI",
          (analiz / "2026-6-aaa.md").exists())

print(f"{chr(10)}{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
