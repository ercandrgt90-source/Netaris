"""`sektor_ozet.json` YAZMA kurallari.

NEDEN BU DOSYA VAR
------------------
Cikti sozlugu her kosuda BOS basliyor ve dosyanin TAMAMINI eziyordu:

    cikti = {}
    ...
    HEDEF.write_text(json.dumps(cikti, ...))

Bunun iki sonucu vardi.

1. `--sektor Sanayi` calistirmak, dosyadaki DIGER ON SEKTORU
   siliyordu. Ustelik kapsam korumasi tam bu yolda BILEREK kapaliydi
   (`not n.sektor and ...`), cunku tek sektorluk kosuda kapsamin
   kuculmesi beklenen bir seydi. Yani korumanin kapatildigi tek yol,
   korumanin en cok gerektigi yoldu. Bu oturumda teshis icin tam da
   "Sanayi tek basina" kosusu yapildi.

2. Kaynak kosu ortasinda istekleri reddedince (olculdu 2026-09-14:
   56 ardisik HTTP 429) uc sektor cekilip sekizi kaybediliyor ve
   kapsam korumasi HICBIR SEYIN yazilmasina izin vermiyordu. Yani
   basariyla cekilen uc sektorun emegi de cope gidiyordu. Kosu ne
   veriyi koruyordu ne de ilerletiyordu -- yalnizca duruyordu.

Dogrusu BIRLESTIRMEK: cekilebilen sektor tazeleniyor, cekilemeyen
sektor ONCEKI HALIYLE kaliyor. Boylece art arda kosular yakinsiyor.

Birlestirme kendi tuzagini getiriyor: agir reddedilen bir sektor
otuz sirket yerine iki sirketle donerse, saglam veriyi ezer. Bu
yuzden ayni kuculme kurali SEKTOR duzeyinde de uygulaniyor -- dogru
ayrinti duzeyi bu.
"""

from __future__ import annotations

import io
import json
import os
import contextlib
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import uret_bilanco as ub          # noqa: E402

_gecen = 0


def esit(a, b, ad):
    global _gecen
    if a != b:
        print(f"  DUSTU  {ad}\n    beklenen: {b!r}\n    gelen:    {a!r}")
        raise SystemExit(1)
    _gecen += 1
    print(f"  gecti  {ad}")


def _sektor(n: int) -> dict:
    """n sirketlik sahte sektor kaydi."""
    return {"donem": "2026/6",
            "sirket": {f"K{i:03d}": {"roe": 1.0} for i in range(n)}}


def _defter_sektorleri() -> list[str]:
    """`--hepsi` kosusunun gercekte gezecegi sektor listesi."""
    return sorted({v["sektor_tr"] for v in ub._defter().values()
                   if v.get("sektor_tr")})


#: `_kosu` sirasinda kosu sayfasina yazilanlar. Cagri yerlerinin
#: hepsini degistirmemek icin burada tutuluyor.
SON_OZET = ""


#: `_kosu` sirasinda sektorlerin ISLENME sirasi.
SIRA: list[str] = []


def _kosu(baslangic: dict, uretilen: dict, argv: list[str],
          izin: int | None = None) -> tuple[dict, int]:
    """HEDEF'i baslangicla kurar, main()'i kosar, sonucu doner.

    `izin` verilirse kaynak yalnizca ilk o kadar sektore izin verir --
    kosu ortasinda kapanan kaynagi taklit eder.
    """
    global SON_OZET
    SIRA.clear()
    with tempfile.TemporaryDirectory() as d:
        hedef = pathlib.Path(d) / "sektor_ozet.json"
        ozet = pathlib.Path(d) / "ozet.md"
        os.environ["GITHUB_STEP_SUMMARY"] = str(ozet)
        hedef.write_text(json.dumps(baslangic, ensure_ascii=False),
                         encoding="utf-8")
        eski = (ub.HEDEF, ub.sektor_isle, ub.sektor_donemi, sys.argv)
        ub.HEDEF = hedef
        ub.sektor_isle = (lambda s, *a, **k: _sektor(5)) if izin             else (lambda s, *a, **k: uretilen[s])
        # Cekilemeyen sektor GERCEK yoldan eleniyor: donem etiketi bos
        # donuyor. Bugunku kosuda sekiz sektor tam buradan dustu.
        def _donem(sektor, *a, **k):
            SIRA.append(sektor)
            if izin is not None:
                return "2026/6" if len(SIRA) <= izin else ""
            return "2026/6" if sektor in uretilen else ""

        ub.sektor_donemi = _donem
        sys.argv = ["uret_bilanco", *argv]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                kod = ub.main()
        finally:
            (ub.HEDEF, ub.sektor_isle, ub.sektor_donemi,
             sys.argv) = eski
            os.environ.pop("GITHUB_STEP_SUMMARY", None)
        SON_OZET = (ozet.read_text(encoding="utf-8")
                    if ozet.exists() else "")
        return json.loads(hedef.read_text(encoding="utf-8")), kod


print("\nTek sektorluk kosu, DIGER SEKTORLERI SILMEMELI")
_bas = {"Sanayi": _sektor(69), "Finans": _sektor(30),
        "Enerji": _sektor(12)}
_son, _kod = _kosu(_bas, {"Sanayi": _sektor(70)},
                   ["--sektor", "Sanayi", "--zorla"])
esit(sorted(_son), ["Enerji", "Finans", "Sanayi"], "uc sektor de duruyor")
esit(len(_son["Sanayi"]["sirket"]), 70, "Sanayi TAZELENDI")
esit(len(_son["Finans"]["sirket"]), 30, "Finans dokunulmadan kaldi")
esit(len(_son["Enerji"]["sirket"]), 12, "Enerji dokunulmadan kaldi")
esit(_kod, 0, "cikis kodu 0")

print("\nYarim kalan --hepsi kosusu, CEKILENI YAZAR gerisini korur")
_bas = {"Sanayi": _sektor(69), "Finans": _sektor(30),
        "Enerji": _sektor(12)}
# Kaynak reddetti: yalnizca Finans cekilebildi.
_son, _kod = _kosu(_bas, {"Finans": _sektor(31)},
                   ["--hepsi", "--zorla"])
esit(len(_son["Finans"]["sirket"]), 31, "cekilen sektor tazelendi")
esit(len(_son["Sanayi"]["sirket"]), 69, "cekilemeyen sektor KORUNDU")
esit(ub.kapsam(_son), 112, "kapsam korundu (69+31+12)")
esit(_kod, 0, "yarim kosu YESIL -- ilerleme kaydedildi")

print("\nCOKEN sektor, saglam veriyi EZMEMELI")
# GENEL KORUMA BU SENARYOYU KURTARAMAZ -- bilerek boyle kuruldu.
#
# Ilk yazimda baslangic {Sanayi 69, Finans 30} idi ve Sanayi 2'ye
# dusunce TOPLAM kapsam da coktu (99 -> 32). Yani sinama, sektor
# korumasi tamamen kapatilsa bile GECIYORDU: onu genel koruma
# kurtariyordu. Mutasyon kacti, sinama hicbir sey OLCMUYORDU.
#
# Finans buyuk tutuluyor ki toplam kapsam esigin USTUNDE kalsin
# (302 > 369 * 0,6 = 221) ve Sanayi'yi yalnizca SEKTOR korumasi
# kurtarabilsin.
_bas = {"Sanayi": _sektor(69), "Finans": _sektor(300)}
# Sanayi agir reddedildi: 69 yerine 2 sirketle dondu.
_son, _kod = _kosu(_bas, {"Sanayi": _sektor(2)},
                   ["--sektor", "Sanayi", "--zorla"])
esit(ub.kapsam(_son) > ub.kapsam(_bas) * ub.KUCULME_ESIGI, True,
     "genel koruma bu senaryoda ATESLEMEZ")
esit(len(_son["Sanayi"]["sirket"]), 69, "coken sektor YAZILMADI")
esit(len(_son["Finans"]["sirket"]), 300, "saglam sektor duruyor")

print("\nSektor GERCEKTEN kuculduyse --zorla-yaz gecirir")
_son, _kod = _kosu({"Sanayi": _sektor(69)}, {"Sanayi": _sektor(2)},
                   ["--sektor", "Sanayi", "--zorla",
                    "--zorla-yaz"])
esit(len(_son["Sanayi"]["sirket"]), 2, "--zorla-yaz kararı insana birakiyor")

print("\nOlculu kuculme normaldir -- esigin USTU gecer")
# 30 -> 26 (bugunku gercek kosu). Esik 0,6 => 18.
_son, _kod = _kosu({"Finans": _sektor(30)}, {"Finans": _sektor(26)},
                   ["--sektor", "Finans", "--zorla"])
esit(len(_son["Finans"]["sirket"]), 26, "30 -> 26 kabul edildi")

print("\nYENI sektor eklenebiliyor")
_son, _kod = _kosu({"Sanayi": _sektor(69)}, {"Enerji": _sektor(3)},
                   ["--hepsi", "--zorla"])
esit(sorted(_son), ["Enerji", "Sanayi"], "yeni sektor eklendi")

print("")
print("EKSIK kosu, kosu sayfasinda GORUNUR")
# Yesil ama bozuk kosu, tam olarak 13 gunluk kesintiyi doguran
# sessizlikti. Birlestirmeden sonra yarim kosu artik kirmizi
# donmuyor; eksikligi baska bir yerden soylemesi SART.
_bas = {"Sanayi": _sektor(69), "Finans": _sektor(30),
        "Enerji": _sektor(12)}
_son, _kod = _kosu(_bas, {"Finans": _sektor(31)}, ["--hepsi", "--zorla"])
esit(_kod, 0, "eksik kosu YESIL")
esit("EKSİK tazelendi" in SON_OZET, True,
     "eksiklik kosu sayfasina YAZILDI")
esit("Sanayi" in SON_OZET, True, "cekilemeyen sektor adiyla yaziliyor")

print("")
print("TAM kosu, gereksiz uyari URETMEZ")
_tam = {k: _sektor(5) for k in _defter_sektorleri()}
_son, _kod = _kosu({}, _tam, ["--hepsi", "--zorla"])
esit(SON_OZET, "", "her sektor cekilince uyari YOK")

print("")
print("EN BAYAT SEKTOR ONCE islenir")
# Alfabetik sirada kaynak hep ayni yerde kapaniyordu: ilk uc sektor
# her kosuda cekiliyor, sonrakiler HIC sirasini almiyordu.
#
# Kurgu, bayatlik sirasini alfabetik siradan KESIN ayiriyor:
# alfabetik olarak EN SONDAKI sektor en bayat yapiliyor. Sira
# alfabetik kalsaydi bu sinama kirmizi donerdi.
_tersi = sorted(_defter_sektorleri(), reverse=True)
_bas = {k: dict(_sektor(5),
                tazelendi=f"2026-09-{i + 1:02d}T00:00:00+00:00")
        for i, k in enumerate(_tersi)}
_son, _kod = _kosu(_bas, {}, ["--hepsi", "--zorla"])
esit(SIRA, _tersi, "sira BAYATLIGA gore, alfabetik DEGIL")
print("")
print("Art arda kosular BUTUN sektorleri dolasiyor (yakinsama)")
# Kaynak her kosuda yalnizca ILK UC sektore izin veriyor -- gercekte
# olculen davranis bu (~100 istek sonrasi kapaniyor). Birlestirme
# tek basina yakinsamiyordu: korunan veri sonsuza kadar bayatlardi.
_dosya: dict = {}
_hepsi = _defter_sektorleri()
_kosu_sayisi = 0
for _ in range(12):
    _dosya, _ = _kosu(_dosya, {}, ["--hepsi", "--zorla"], izin=3)
    _kosu_sayisi += 1
    if all((_dosya.get(k) or {}).get("tazelendi") for k in _hepsi):
        break
esit(sorted(_dosya) == sorted(_hepsi), True,
     "butun sektorler dosyada")
esit(all((_dosya.get(k) or {}).get("tazelendi") for k in _hepsi), True,
     "butun sektorler TAZELENDI -- hicbiri ac kalmadi")
# 11 sektor, kosu basina 3 -> dort kosu yeter.
esit(_kosu_sayisi <= 4, True,
     f"dort kosuda yakinsadi ({_kosu_sayisi} kosu)")

print(f"\nTUM TESTLER GECTI ({_gecen})")
