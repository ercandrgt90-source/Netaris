# -*- coding: utf-8 -*-
"""BILANCO NOBETCISI: YENI CEYREGI GORMELI, SAHTE OLAY URETMEMELI.

BU DOSYA NEDEN VAR
------------------
Hat bilanco cekmeyi TAKVIME bagliyordu (Mart, Mayis, Agustos, Kasim --
konsolide bildirim son tarihleri). Konsolide OLMAYAN sirketler donem
bitiminden otuz gun sonra bildiriyor, yani 9 aylik tablolar EKIM
SONUNDA geliyor ve pencere Kasim'da aciliyor. Arada bildirimler
yayimlaniyor, biz hicbir sey cekmiyoruz.

Nobetci takvim yerine OLCUYOR: kaynakta yeni bir ceyrek belirdi mi?
Sirket basina tek istek, olculdu (2026-10-13) 0,3 saniye.

UC TUZAK, UCU DE BURADA SINANIYOR
---------------------------------
1. SOGUK BASLANGIC. Defter bosken her sirket "yeni bildirdi" gorunur,
   cunku karsilastirilacak onceki deger yok. Olculdu: ilk denemede 10
   sirketin 9'u "yeni" bildirildi -- hepsi elimizde ZATEN OLAN donem.
   Ilk gorulme TOHUMDUR, olay degil.

2. OLAY SIRKET BAZINDA OLMALI. Ilk yazimda olcut KURESEL son ceyrekti.
   O zaman ilk bildiren sirket esigi yukseltiyor ve ardindan gelen
   yuzlerce sirket bir daha HIC tetiklemiyor -- oysa istenen sey tam
   olarak "geldikce cikalim".

3. GELECEK CEYREK GERCEK DEGILDIR. Takvim disi mali yili olan
   sirketlerde kaynak donemleri ileri etiketliyor. ARENA'nin
   basliklari (2026-10-13'te olculdu): Q1 2027, Q4 2026, Q3 2026...
   Suzgec olmadan nobetci HER kosuda "yeni donem" derdi.
   Olcut `bilanco_ag.makul_ceyrek` icinde: ceyregin BITIS ayi
   gecmiste olmali.

AG KULLANILMIYOR. `son_donem` yerine sahte islev konuyor: gercek
kaynaga baglı bir sinama hem yavas hem kirilgan olurdu, ustelik
kaynagi bosuna yorardi.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))

import bilanco_ag                                  # noqa: E402
import bilanco_nobetci as nb                       # noqa: E402

_gecti = 0

#: Sahte islevler kurulmadan ONCE asillari saklaniyor.
#:
#: Ilk yazimda saklanmiyordu ve sinama KENDI KENDINI BOZDU: 2-5.
#: maddeler `son_donem`i sahteyle degistiriyor, 7. madde gercek
#: islevi sinamak istiyordu ama elinde hala sahte olani vardi ve
#: "None" donuyordu. Olcum araci, olctugu seyi bozmamali.
_ASIL_SON_DONEM = bilanco_ag.son_donem
_ASIL_CEK = bilanco_ag.cek
_ASIL_KODLAR = nb.ulasilabilir_kodlar
_ASIL_NOBET = nb.NOBET


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def kur(defter_sirket, cevaplar, nobet=None):
    """Gecici defter + sahte kaynak kurar, `bak()` sonucunu doner."""
    gecici = pathlib.Path(tempfile.mkdtemp())
    nb.NOBET = gecici / "nobet.json"
    if nobet is not None:
        nb.NOBET.write_text(json.dumps(nobet), encoding="utf-8")
    nb.ulasilabilir_kodlar = lambda: list(defter_sirket)
    bilanco_ag.son_donem = lambda kod, istemci=None, bugun=None: cevaplar.get(kod)
    return nb.bak(orneklem=len(defter_sirket))


print("")
print("Bilanco nobetcisi")

# --- 1) SOGUK BASLANGIC: her sey ilk gorulme, OLAY YOK ---------------
s = kur(["AAA", "BBB"], {"AAA": (2026, 2), "BBB": (2026, 2)})
esit(s["durum"], "tohumlandi", "ilk kosu tohumluyor, donem acmiyor")
esit(s["yeni_bildiren"], [], "ilk kosuda yeni bildiren yok")
esit(s["ilk_gorulen"], 2, "iki sirket ilk kez goruldu")

# --- 2) BIR SIRKET ILERLEDI: OLAY ------------------------------------
onceki = {"son_ceyrek": [2026, 2], "sirket": {"AAA": [2026, 2], "BBB": [2026, 2]},
          "imlec": 0}
s = kur(["AAA", "BBB"], {"AAA": (2026, 3), "BBB": (2026, 2)}, onceki)
esit(s["durum"], "yeni donem", "ilerleyen sirket donem aciyor")
esit(s["yeni_bildiren"], ["AAA"], "yalnizca ilerleyen sirket olay sayiliyor")

# --- 3) IKINCI SIRKET SONRA BILDIRIR: YINE OLAY ----------------------
# Kuresel esik kullanilsaydi burada OLAY OLMAZDI: son_ceyrek zaten
# 2026 Q3'e cikmis olurdu ve BBB "yeni" gorunmezdi.
onceki = {"son_ceyrek": [2026, 3], "sirket": {"AAA": [2026, 3], "BBB": [2026, 2]},
          "imlec": 0}
s = kur(["AAA", "BBB"], {"AAA": (2026, 3), "BBB": (2026, 3)}, onceki)
esit(s["durum"], "yeni donem", "sonradan bildiren sirket de olay uretiyor")
esit(s["yeni_bildiren"], ["BBB"], "olay sirketin KENDI gecmisine gore")

# --- 4) DEGISIKLIK YOK -----------------------------------------------
onceki = {"son_ceyrek": [2026, 3], "sirket": {"AAA": [2026, 3], "BBB": [2026, 3]},
          "imlec": 0}
s = kur(["AAA", "BBB"], {"AAA": (2026, 3), "BBB": (2026, 3)}, onceki)
esit(s["durum"], "degisiklik yok", "ilerleme yoksa donem acilmiyor")

# --- 5) DONEREK ORNEKLEMDE ILK GORULME, OLAY DEGIL -------------------
onceki = {"son_ceyrek": [2026, 2], "sirket": {"AAA": [2026, 2]}, "imlec": 0}
s = kur(["AAA", "CCC"], {"AAA": (2026, 2), "CCC": (2026, 2)}, onceki)
esit(s["durum"], "degisiklik yok", "ilk kez gorulen sirket sahte olay uretmiyor")
esit(s["ilk_gorulen"], 1, "ilk gorulme ayri sayiliyor")

# --- 6) GELECEK CEYREK SUZULUYOR -------------------------------------
# `makul_ceyrek` dogrudan sinaniyor; `son_donem` onu kullaniyor.
import datetime as _dt                             # noqa: E402
_b = _dt.date(2026, 10, 13)
esit(bilanco_ag.makul_ceyrek((2026, 3), _b), True, "biten ceyrek makul")
esit(bilanco_ag.makul_ceyrek((2026, 4), _b), False, "bitmemis ceyrek makul degil")
esit(bilanco_ag.makul_ceyrek((2027, 1), _b), False, "gelecek yil makul degil")
esit(bilanco_ag.makul_ceyrek(None, _b), False, "bos deger makul degil")

# --- 7) SUZGEC `son_donem` ICINDE GERCEKTEN UYGULANIYOR MU ----------
#
# Ustteki madde `makul_ceyrek`i dogrudan sinıyor; bu madde onun
# CAGRILDIGINI sinıyor. Bir islevin dogru olmasi, kullanildigi
# anlamina gelmiyor -- bu depoda ayni bosluk birkac kez yasandi.
# --- 8) MEVSIM ILERLEMESI: hic gormedigimiz sirket ilk bildirirse --
#
# Donerek orneklemde bir sirket ilk kez besinci kosuda gorulebiliyor
# ve Q3 bildiren ILK sirket o olabilir. Yalnizca "sirket ilerlemesi"
# sinyali olsaydi bu olay KACARDI: ilk gorulme tohumdur.
onceki = {"son_ceyrek": [2026, 2], "sirket": {"AAA": [2026, 2]}, "imlec": 0}
s = kur(["AAA", "YENI"], {"AAA": (2026, 2), "YENI": (2026, 3)}, onceki)
esit(s["durum"], "yeni donem", "ilk kez gorulen sirket MEVSIMI acabiliyor")
esit(s["mevsim_ilerledi"], True, "mevsim ilerlemesi ayri sinyal")
esit(s["yeni_bildiren"], [], "sirket ilerlemesi yok, yalnizca mevsim")

# Mevsim GERILEMEZ: eski ceyrek bildiren sirket donem acmaz.
onceki = {"son_ceyrek": [2026, 3], "sirket": {"AAA": [2026, 3]}, "imlec": 0}
s = kur(["AAA", "ESKI"], {"AAA": (2026, 3), "ESKI": (2026, 1)}, onceki)
esit(s["durum"], "degisiklik yok", "geride kalan sirket donem acmiyor")

bilanco_ag.son_donem = _ASIL_SON_DONEM          # sahteyi geri al
nb.ulasilabilir_kodlar = _ASIL_KODLAR
nb.NOBET = _ASIL_NOBET
_asil_cek = bilanco_ag.cek
try:
    # ARENA: basliklarinda GELECEK ceyrek var -> takvim disi.
    # Ilk yazimda bu durumda (2026, 3) beklenıyordu, yani "gelecek
    # olanlari atla, kalanin en yenisini al". OLCUM BUNU CURUTTU:
    # boyle bir sirketin "Q3 2026" etiketi TAKVIM Q3'u DEGIL. Onu
    # kullanmak sektoru yanlis etiketler ve nobetciye sahte mevsim
    # acilisi yaptirir. Dogru davranis: hic kullanma.
    bilanco_ag.cek = lambda k, t, i=None: (["Q1 2027", "Q4 2026", "Q3 2026",
                                            "Q2 2026"], {})
    esit(bilanco_ag.son_donem("ARENA gibi", bugun=_b), None,
         "takvim disi sirket (gelecek ceyrek tasiyan) None doniyor")
    bilanco_ag.cek = lambda k, t, i=None: (["Q2 2026", "Q1 2026"], {})
    esit(bilanco_ag.son_donem("normal", bugun=_b), (2026, 2),
         "normal sirkette en yeni ceyrek doniyor")
    bilanco_ag.cek = lambda k, t, i=None: (["Q1 2027", "Q4 2026"], {})
    esit(bilanco_ag.son_donem("hepsi ileri", bugun=_b), None,
         "hepsi gelecekse None doniyor")
    # TAKVIM DISI MALI YIL: basliklarda GELECEK ceyrek varsa sirketin
    # etiketleri takvim ceyregine denk dusmuyor -- hic kullanilmamali.
    # Olculdu (2026-10-13): ARENA ve BALSU boyleydi ve ikisi de
    # "Q3 2026" bildiriyordu; takvim Q3'u ise henuz gelmemisti.
    bilanco_ag.cek = lambda k, t, i=None: (["Q4 2026", "Q3 2026", "Q1 2026",
                                            "Q4 2025"], {})
    esit(bilanco_ag.son_donem("BALSU gibi", bugun=_b), None,
         "takvim disi sirket None doniyor (sahte Q3 uretmiyor)")
finally:
    bilanco_ag.cek = _asil_cek

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
