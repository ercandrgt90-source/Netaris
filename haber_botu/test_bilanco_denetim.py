# -*- coding: utf-8 -*-
"""ONARIM OLCUTU: HANGI SAYFA BOZUK, VE KUYRUK GERCEKTEN KISALIYOR MU.

BU DOSYA NEDEN VAR
------------------
`bilanco_denetim` iki tarafin birlikte kullandigi TEK olcut:

    site/test_bilanco_donem_tutarliligi.py  -> koruma
    bilanco_tazele --onarim                 -> onarim

Olcut iki yerde ayri yazilsaydi birinin degisip otekinin unutulmasi
kacinilmazdi; bu depoda tam o sinif kusur yayina cikti (ara donemin
kac ceyrekten olustugu `uret_bilanco` ile `donem_getir` arasinda
farkliydi).

KUYRUK SIRASI DA SINANIYOR. Alfabetik sira + `--sinir`, kuyrugun
sonuna HIC ulasmiyor: her kosu ayni ilk N sayfayi yeniden kuruyor.
Ayni tuzaga sektor sirasinda dusulmustu (olculdu 2026-09-14: 11
sektorun hep ayni ilk ucu cekiliyordu). Onarim kuyrugu bu yuzden
IHTIYACA gore kuruluyor ve onarilan sayfa kuyruktan DUSUYOR.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_denetim as bd                       # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _sayfa(hasilat, brut, net, ozkaynak, brut_marj, roe,
           kilavuz="", kod="ZZZZ"):
    s = [
        "---", f"kod: {kod}", "kategori: Bilanço Analizi", "---", "",
        "## 2026 2. çeyrek dönemi ölçümleri", "",
        "| Kalem | Değer |", "| --- | ---: |",
        f"| Hasılat | {hasilat} milyar TL |",
        f"| Brüt kâr | {brut} milyar TL |",
        f"| Net kâr | {net} milyar TL |",
        f"| Özkaynak | {ozkaynak} milyar TL |", "",
        "## Sektör içindeki konum", "",
        "| Oran | Şirket | Sektör medyanı |", "| --- | ---: | ---: |",
        f"| Brüt kâr marjı | {brut_marj} | %20,0 |",
        f"| Özkaynak kârlılığı | {roe} | %5,0 |", "",
    ]
    if kilavuz:
        s += [f"## {kilavuz}", "", "Bir paragraf.", ""]
    return "\n".join(s)


print("1. Tutarli sayfa BOZUK sayilmiyor")
# 5,00 / 10,00 = %50,0 ;  1,00 / 10,00 = %10,0
_T = _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0")
esit(bd.bilanco_sayfasi(_T), True, "bilanço sayfası tanınıyor")
esit(len(bd.olc(_T)), 2, "iki oran da ölçülebiliyor")
esit(bd.donem_tutarsizligi(_T), [], "tutarlı sayfada uyuşmazlık yok")
esit(bd.onarim_gereken(_T), [], "onarım gerekmiyor")

print("")
print("2. Seviye ile oran uyusmuyorsa YAKALANIYOR")
_B = _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0")
_k = bd.donem_tutarsizligi(_B)
esit([a for a, _h, _y in _k], ["brut_marj"], "brüt marj uyuşmazlığı")
esit(round(_k[0][1], 1), 50.0, "seviyeden hesaplanan %50,0")
esit(round(_k[0][2], 1), 12.0, "yazılı %12,0")
esit(bd.onarim_gereken(_B), ["dönem tutarsız (brut_marj)"],
     "onarım sebebi yazılıyor")

print("")
print("3. Yuvarlanma payi TOLERE ediliyor, gercek fark EDILMIYOR")
# 1,48 / 16,20 = %9,136 -- iki ondalikli yazimin payi icinde.
esit(bd.donem_tutarsizligi(
    _sayfa("16,20", "1,48", "1,00", "10,00", "%9,1", "%10,0")), [],
    "yuvarlanma payı içindeki fark bozuk sayılmıyor")
# Ayni sayfada yazili %8,8 ise fark yuvarlanmayla aciklanamaz
# (olculdu: 2026-1-ceyrek-asuzu.md tam boyleydi).
esit(len(bd.donem_tutarsizligi(
    _sayfa("16,20", "1,48", "1,00", "10,00", "%8,0", "%10,0"))), 1,
    "payın dışındaki fark YAKALANIYOR")

print("")
print("4. Kapsam disi kilavuz YAKALANIYOR")
_TELEKOM = "Telekomünikasyonda borç ve amortisman neden yüksektir"
_F = _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
            kilavuz=_TELEKOM, kod="FENER")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", "Entertainment"), _TELEKOM,
     "futbol kulübünde telekom kılavuzu yakalanıyor")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", "Telecom Services"), "",
     "telekomda aynı kılavuz SORUN DEĞİL")
esit(bd.kilavuz_uyusmazligi(_F, "İletişim", ""), "",
     "alt sektör bilinmiyorsa kısıtlama yok")
esit(bd.onarim_gereken(_F, {"sektor_tr": "İletişim",
                            "alt_sektor": "Entertainment"}),
     [f"kapsam dışı kılavuz ({_TELEKOM})"],
     "onarım sebebi kılavuz olarak yazılıyor")
# Kilavuz sayfada YOKSA uyusmazlik da yok -- sebep sayfada olmali.
esit(bd.kilavuz_uyusmazligi(_T, "İletişim", "Entertainment"), "",
     "kılavuz sayfada yoksa uyuşmazlık YOK")

print("")
print("5. Iki sebep birlikte yaziliyor")
_IKI = _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0",
              kilavuz=_TELEKOM, kod="FENER")
esit(bd.onarim_gereken(_IKI, {"sektor_tr": "İletişim",
                              "alt_sektor": "Entertainment"}),
     ["dönem tutarsız (brut_marj)",
      f"kapsam dışı kılavuz ({_TELEKOM})"],
     "iki sebep birlikte")

print("")
print("6. Bilanco sayfasi OLMAYAN dosyaya dokunulmuyor")
esit(bd.onarim_gereken("---\nkategori: Haber\n---\n\nMetin."), [],
     "haber sayfası onarım kuyruğuna girmiyor")
esit(bd.olc("boş"), [], "kıyas bölümü yoksa ölçüm yok")

print("")
print("7. ONARIM KUYRUGU IHTIYACA gore kuruluyor, alfabetik DEGIL")
import uret_bilanco_sayfa as U                     # noqa: E402
import bilanco_tazele as BT                        # noqa: E402

_ASIL_SITE = U.SITE
try:
    g = pathlib.Path(tempfile.mkdtemp())
    U.SITE = g
    # Alfabetik olarak ONCE gelen sayfa SAGLAM, sonra gelen BOZUK.
    # Kuyruk alfabetikse saglam olan basta cikar ve `--sinir 1`
    # bozugu HIC onarmaz.
    (g / "aaa-saglam.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kod="AAA"), encoding="utf-8")
    (g / "zzz-bozuk.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%12,0", "%10,0",
               kod="ZZZ"), encoding="utf-8")
    kuyruk = BT.onarim_kuyrugu({})
    esit([y.stem for y, _ in kuyruk], ["zzz-bozuk"],
         "kuyrukta YALNIZCA bozuk sayfa var (saglam olan yok)")
    # Sayfa duzeltilince kuyruktan DUSUYOR -- adim kendiliginden
    # etkisiz hale geliyor, sonsuza kadar ayni isi yapmiyor.
    (g / "zzz-bozuk.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kod="ZZZ"), encoding="utf-8")
    esit(BT.onarim_kuyrugu({}), [], "onarılan sayfa kuyruktan DÜŞÜYOR")

    # KUYRUK DEFTERI GERCEKTEN OKUYOR MU.
    #
    # Alt sektor denetimi yalnizca defter kaydi gecirildiginde
    # calisiyor. Kuyruk kaydi gecirmezse kilavuz uyusmazligi SESSIZCE
    # gorunmez olur -- islev dogru olur, kullanimi yanlis.
    (g / "mmm-kulup.md").write_text(
        _sayfa("10,00", "5,00", "1,00", "10,00", "%50,0", "%10,0",
               kilavuz=_TELEKOM, kod="FENER"), encoding="utf-8")
    esit(BT.onarim_kuyrugu({}), [],
         "defter kaydı olmayan şirkette kılavuz kısıtlanmıyor")
    _defter = {"FENER": {"sektor_tr": "İletişim",
                         "alt_sektor": "Entertainment"}}
    esit([y.stem for y, _ in BT.onarim_kuyrugu(_defter)], ["mmm-kulup"],
         "DEFTERDEN okunan alt sektörle kılavuz uyuşmazlığı yakalanıyor")
finally:
    U.SITE = _ASIL_SITE

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
