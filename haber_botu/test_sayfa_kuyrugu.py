# -*- coding: utf-8 -*-
"""SAYFA KUYRUGU: SIRA, OKURUN NEYI NE ZAMAN GORECEGIDIR.

BU DOSYA NEDEN VAR
------------------
Bilanco sayfasi uretimi gunde ancak birkac sayfa yazabiliyor --
darbogaz ucretsiz AI saglayicisinin gunluk kotasi (olculdu
2026-10-16: iki gunde alti sayfa). Yani kuyruk sirasi akademik bir
ayrinti degil, dogrudan "okur neyi ne zaman gorecek" demek.

IKI KUSUR DUZELTILDI, IKISI DE OLCULEREK
----------------------------------------
1. SIRA "ONCE BICIM GOCUNU BITIR" DIYE KURULMUSTU. Olculdu: ozetteki
   324 sirketin 109'unun HIC sayfasi yok. Okur onlar icin hicbir sey
   goruyor; bicimi eski bir sayfa ise yine okunabiliyor. Sira
   tersine kurulmustu.

2. SAYFASI OLMAYANLAR ARASINDA SIRA ALFABETIKTI. Bir haber
   sitesinde yanlis olcut: iki ay once bildiren sirketle BUGUN
   bildiren ayni siraya giriyor. Olculdu (2026-10-16): 227 sirket
   2026-06-30 donemini bildiriyor, DORT futbol kulubu ise
   2026-08-31 -- tek basina en yeni donem onlarda. Alfabetik sirada
   65-69. siradaydilar, yani haftalarca beklerlerdi.

AG KULLANILMIYOR.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import uret_bilanco_sayfa as US                     # noqa: E402

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


def _ozet(**sirketler):
    """Tek sektorluk ozet; deger = (bitis ya da None)."""
    bitis = {k: v for k, v in sirketler.items() if v}
    return {"S": {"sektor": "S", "donem": "2026 2. çeyrek",
                  "medyan": {"brut_marj": 1.0}, "sirket_sayisi": 3,
                  "sirket": {k: {"brut_marj": 1.0} for k in sirketler},
                  "bitis": bitis}}


def _sira(ozet, olan=frozenset(), bekleyen=frozenset(), bitisler=None,
          olan_verilsin=True):
    """`olan_verilsin=False` -> cagiran kumeyi HIC vermiyor."""
    return [x[4] for x in US.kuyruk_kur(
        ozet, set(bekleyen), "",
        set(olan) if olan_verilsin else None, bitisler)]


print("")
print("1. HIC SAYFASI OLMAYAN once, bicim gocu sonra")
_o = _ozet(AAA=None, BBB=None, CCC=None)
# AAA sayfasi var ve bicim gocu bekliyor; BBB'nin sayfasi var ve
# guncel; CCC'nin HIC sayfasi yok.
esit(_sira(_o, olan={"AAA", "BBB"}, bekleyen={"AAA"}),
     ["CCC", "AAA", "BBB"],
     "sayfasi olmayan EN ONDE, sonra göç, sonra güncel")

print("")
print("2. Sayfasi olmayanlarda EN TAZE BILDIRIM once")
_o = _ozet(ESKI="2026-03-31", YENI="2026-08-31", ORTA="2026-06-30")
esit(_sira(_o, bitisler={"ESKI": "2026-03-31", "YENI": "2026-08-31",
                         "ORTA": "2026-06-30"}),
     ["YENI", "ORTA", "ESKI"], "en yeni dönem önce")

print("")
print("3. BILINMEYEN bitis EN SONA")
# Bilmedigimiz tazeligi one cikarmak, olculmemis bir seyi olculmus
# gibi sunmak olurdu. Nobetci her kosuda 60 sirkete bakiyor, yani
# bilinmeyenlerin sayisi kendiliginden azaliyor.
esit(_sira(_ozet(BILINEN="2026-06-30", MECHUL=None),
           bitisler={"BILINEN": "2026-06-30"}),
     ["BILINEN", "MECHUL"], "bitişi bilinmeyen sona")
esit(US._tazelik(""), 0, "boş bitiş sıfır (en sona)")
esit(US._tazelik("bozuk"), 0, "çözülemeyen bitiş sıfır")
if not US._tazelik("2026-08-31") < US._tazelik("2026-06-30") < 0:
    print("  DUSTU  tazelik anahtari yanlis siralaniyor")
    raise SystemExit(1)
_gecti += 1
print("  gecti  anahtar: yeni < eski < bilinmeyen")

print("")
print("4. TAZELIK BICIM GOCUNU YENIDEN SIRALAMIYOR")
# Goc, tamamlanmis bir listeyi bitirmek uzerine; orada tazelik
# anlamsiz ve siranin degismesi gocu uzatirdi.
_o = _ozet(AAA="2026-03-31", BBB="2026-08-31")
esit(_sira(_o, olan={"AAA", "BBB"}, bekleyen={"AAA", "BBB"},
           bitisler={"AAA": "2026-03-31", "BBB": "2026-08-31"}),
     ["AAA", "BBB"], "göç grubunda alfabetik düzen korunuyor")

print("")
print("5. Tazelik verilmezse ESKI davranis (geriye donuk)")
_o = _ozet(ZZZ="2026-08-31", AAA="2026-06-30")
esit(_sira(_o), ["AAA", "ZZZ"], "bitişler verilmezse alfabetik")
# `sayfasi_olan` HIC VERILMEZSE eski davranis: oncelik ayrimi yok.
esit(_sira(_o, olan_verilsin=False,
           bitisler={"ZZZ": "2026-08-31", "AAA": "2026-06-30"}),
     ["AAA", "ZZZ"], "küme hiç verilmezse öncelik uygulanmıyor")
# BOS KUME ise GERCEK bir deger: hicbir sayfa yok demek.
esit(_sira(_o, olan=frozenset(),
           bitisler={"ZZZ": "2026-08-31", "AAA": "2026-06-30"}),
     ["ZZZ", "AAA"], "BOŞ küme 'hiçbirinin sayfası yok' demek")

print("")
print("6. bitis_haritasi IKI kaynagi birlestiriyor")
_g = pathlib.Path(tempfile.mkdtemp())
_ASIL = US.DEFTER
try:
    (_g / "bilanco_nobet.json").write_text(json.dumps({
        "sirket": {"AAA": "2026-06-30", "BBB": "2026-05-31",
                   "CCC": None, "DDD": 123}}), encoding="utf-8")
    US.DEFTER = _g / "sirketler.json"
    h = US.bitis_haritasi(_ozet(BBB="2026-08-31"))
    esit(h.get("AAA"), "2026-06-30", "nöbetçiden geliyor")
    esit(h.get("BBB"), "2026-08-31",
         "ÖZET nöbetçiyi EZİYOR (aynı koşuda ölçüldü)")
    esit("CCC" in h, False, "boş değer alınmıyor")
    esit("DDD" in h, False, "dizge olmayan değer alınmıyor")
    # Nobet defteri YOKSA cokmuyor.
    US.DEFTER = _g / "yok" / "sirketler.json"
    esit(US.bitis_haritasi(_ozet(EEE="2026-07-31")), {"EEE": "2026-07-31"},
         "nöbet defteri yoksa yalnızca özet")
finally:
    US.DEFTER = _ASIL

print("")
print("7. GERCEK VERI: kulupler kuyrugun basinda")
# Olculdu 2026-10-16: dort kulup de 2026-08-31 bildiriyor ve bu
# tek basina en yeni donem. Alfabetik sirada 65-69. sirada
# olurlardi.
_gercek = pathlib.Path(_KOK / "kaynak" / "sektor_ozet.json")
if _gercek.is_file():
    o = json.loads(_gercek.read_text(encoding="utf-8"))
    bit = US.bitis_haritasi(o)
    if bit.get("GSRAY") == "2026-08-31":
        olan = {k for (k, _d) in US._yayimlanmis()}
        kod = [x[4] for x in US.kuyruk_kur(o, set(), "", olan, bit)]
        ilk4 = set(kod[:4])
        esit(ilk4, {"BJKAS", "FENER", "GSRAY", "TSPOR"},
             "dört kulüp kuyruğun ilk dördünde")
        kod_alf = [x[4] for x in US.kuyruk_kur(o, set(), "", olan)]
        if kod_alf.index("GSRAY") <= 10:
            print("  DUSTU  alfabetik sirada da basta -- olcum "
                  "tazeligin etkisini GOSTERMIYOR")
            raise SystemExit(1)
        _gecti += 1
        print(f"  gecti  alfabetik sirada {kod_alf.index('GSRAY') + 1}., "
              f"tazelikle {kod.index('GSRAY') + 1}.")
    else:
        print("  ATLANDI  veri degismis (GSRAY bitisi farkli)")
else:
    print("  ATLANDI  sektor ozeti yok")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
