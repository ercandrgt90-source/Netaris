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
          olan_verilsin=True, yayimlanmis=None):
    """`olan_verilsin=False` -> cagiran kumeyi HIC vermiyor."""
    return [x[4] for x in US.kuyruk_kur(
        ozet, set(bekleyen), "",
        set(olan) if olan_verilsin else None, bitisler, yayimlanmis)]


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
print("7. GERCEK VERI: en taze bildirim kuyrugun basinda")
#
# OZELLIK sinaniyor, ANLIK LISTE degil. Ilk yazim "ilk dortte su
# dort kulup olmali" diyordu ve FENER'in sayfasi YAYIMLANINCA
# dustu -- sistem dogru calismisti, sinama anlik duruma cakiliydi.
#
# Dogru olcut: sayfasi olmayanlar arasinda EN YENI bitis tarihine
# sahip olanlar basta olmali.
_gercek = _KOK / "kaynak" / "sektor_ozet.json"
if _gercek.is_file():
    o = json.loads(_gercek.read_text(encoding="utf-8"))
    bit = US.bitis_haritasi(o)
    olan = {k for (k, _d) in US._yayimlanmis()}
    kod = [x[4] for x in US.kuyruk_kur(o, set(), "", olan, bit)]
    sayfasiz = [k for k in kod if k not in olan]
    bilinen = [(k, bit[k]) for k in sayfasiz if bit.get(k)]
    if len(bilinen) >= 3:
        enyeni = max(t for _k, t in bilinen)
        bastakiler = [k for k in sayfasiz[:len(
            [1 for _k, t in bilinen if t == enyeni])]]
        hepsi_taze = all(bit.get(k) == enyeni for k in bastakiler)
        esit(hepsi_taze, True,
             f"kuyruğun başındakilerin hepsi en yeni dönemde ({enyeni})")
        # Siralama MONOTON olmali: tarih bilinenlerde geriye gitmemeli.
        seri = [bit[k] for k in sayfasiz if bit.get(k)]
        esit(seri == sorted(seri, reverse=True), True,
             "bitiş tarihleri kuyrukta yeniden eskiye sıralı")
        # Bilinmeyenler SONDA.
        ilk_mechul = next((i for i, k in enumerate(sayfasiz)
                           if not bit.get(k)), len(sayfasiz))
        son_bilinen = max((i for i, k in enumerate(sayfasiz)
                           if bit.get(k)), default=-1)
        esit(ilk_mechul > son_bilinen, True,
             "bitişi bilinmeyenler bilinenlerden SONRA")
    else:
        print("  ATLANDI  bitisi bilinen sayfasiz sirket az")
else:
    print("  ATLANDI  sektor ozeti yok")

print("")
print("5. SAYFASI VAR AMA DONEMI ESKI -- kuyrugun basina")
# Sayfasi bir kez yazilan sirket YENI CEYREK bildirdiginde oncelik
# 2'ye, yani kuyrugun dibine dusuyordu. Olculdu (2026-10-30, Q3
# sezonunun ilk gunleri): 42 bayat sirketin kuyruk sirasi 94, 95,
# 96... ve `--sinir 60` ile ilk 60 icinde SIFIR tanesi vardi.
#
# Agustosta calismis GORUNMESI tesaduftu: o gun sirketlerin cogunun
# hic sayfasi yoktu, yani zaten oncelik 0'daydilar. Sayfalar
# doldukca kilit kendiliginden kapandi.
#
# BEKLENTI ELLE YAZILI. Etiketi `donem_etiketi`den uretmek,
# beklentiyi KORUDUGU koddan okumak olurdu ve mutasyonu sessizce
# yesil birakirdi. Olculen degerler (2026-10-30):
#     2026-06-30 -> "2026 2. ceyrek"
#     2026-09-30 -> "2026 3. ceyrek"
_o5 = _ozet(ESKI="2026-06-30", YENI="2026-09-30", GUNCEL="2026-09-30")
_bit5 = {"ESKI": "2026-06-30", "YENI": "2026-09-30",
         "GUNCEL": "2026-09-30"}
# UCUNUN DE sayfasi var. GUNCEL'in 3. ceyregi yayimlanmis; YENI 3.
# ceyregi BILDIRDI ama sayfasi hala 2. ceyrekte; ESKI zaten 2.
# ceyrekte ve o yayimlanmis.
_yay5 = {("ESKI", "2026 2. çeyrek"), ("YENI", "2026 2. çeyrek"),
         ("GUNCEL", "2026 3. çeyrek")}
esit(_sira(_o5, olan={"ESKI", "YENI", "GUNCEL"}, bitisler=_bit5,
           yayimlanmis=_yay5),
     ["YENI", "ESKI", "GUNCEL"],
     "donemi gecmis sayfa EN ONDE")

# ESIT TAZELIKTE SAYFASIZ ONCE: ikisi de bugun bildirdiyse okur
# acisindan fark var -- sayfasizda HICBIR SEY, bayatta bir onceki
# ceyrek goruluyor.
_o6 = _ozet(SAYFASIZ="2026-09-30", BAYAT="2026-09-30")
esit(_sira(_o6, olan={"BAYAT"},
           bitisler={"SAYFASIZ": "2026-09-30", "BAYAT": "2026-09-30"},
           yayimlanmis={("BAYAT", "2026 2. çeyrek")}),
     ["SAYFASIZ", "BAYAT"],
     "esit tazelikte sayfasiz once")

# GERIYE DONUK: kume HIC verilmezse eski davranis korunuyor.
esit(_sira(_o5, olan={"ESKI", "YENI", "GUNCEL"}, bitisler=_bit5),
     ["ESKI", "GUNCEL", "YENI"],
     "yayimlanmis kumesi verilmezse eski siralama")

# ATILLIK -- POZITIF KONTROL.
#
# "Bayat sayma" olcutu gercekten KUMEYI okuyor mu? Bos kume
# verildiginde UCU DE bayat sayilmali ve tazelige gore
# siralanmali. Olcut atil olsaydi (hep False dondurseydi) sira
# alfabetik kalirdi.
esit(_sira(_o5, olan={"ESKI", "YENI", "GUNCEL"}, bitisler=_bit5,
           yayimlanmis=set())[:2],
     ["GUNCEL", "YENI"],
     "bos kumede hepsi bayat, tazelige gore siralaniyor")

print("")
print("6. URETIM DONGUSU KUMEYI GERCEKTEN GECIRIYOR")
# Kuyruk dogru siralasa da `main` kumeyi vermezse olcut OLU kalir:
# `yayimlanmis=None` eski davranisa donuyor. Olcut AST -- metin
# aramak bicimlendirme degisince sessizce eslesmeyi birakiyor.
import ast                                          # noqa: E402
_ag = ast.parse(pathlib.Path(US.__file__).read_text(encoding="utf-8"))
_cagri = [d for d in ast.walk(_ag)
          if isinstance(d, ast.Call)
          and isinstance(d.func, ast.Name)
          and d.func.id == "kuyruk_kur"]
esit(len(_cagri), 1, "uretimde tek kuyruk_kur cagrisi")
_arg = len(_cagri[0].args) + len(_cagri[0].keywords)
esit(_arg >= 6, True, f"cagri yayimlanmis kumesini de geciriyor ({_arg} arguman)")

print("")
print("8. GECIKME OLCUMU -- BILDIRDI AMA YAYIMLANMADI")
# `bilanco_nobetci` yeni donemi dogru goruyor ve bayragi aciyor;
# bayrak kosu sonunda KAPANIYOR -- sayfa yazilsa da yazilmasa da.
# Yani "uc sirket bildirdi, hicbirine sayfa yazilamadi" HICBIR
# YERDE gorunmuyordu. Olculdu: bes kosu ust uste sifir sayfa yazdi
# ve kosular YESIL dondu.
#
# KIRMIZI KAPI DEGIL: gecikmenin sebebi kodda degil ucretsiz AI
# tahsisatinda. Mesru bir sifiri kusur sayan kontrol dagitimi
# durdururdu; burada yalnizca GORUNUR kiliniyor.
import datetime as _dt                                 # noqa: E402

_BUGUN = _dt.date(2026, 10, 30)
_o8 = _ozet(GUNCEL="2026-09-30", BAYAT="2026-06-30", SAYFASIZ="2026-09-30",
            MECHUL=None)
_bit8 = {"GUNCEL": "2026-09-30", "BAYAT": "2026-06-30",
         "SAYFASIZ": "2026-09-30"}
# BEKLENTI ELLE YAZILI: etiketi `donem_etiketi`den uretmek,
# beklentiyi korudugu koddan okumak olurdu.
_yay8 = {("GUNCEL", "2026 3. çeyrek"), ("BAYAT", "2026 1. çeyrek"),
         ("MECHUL", "2026 2. çeyrek")}
_olan8 = {"GUNCEL", "BAYAT", "MECHUL"}

_sayi, _eski, _ornek = US.gecikme_olc(_o8, _yay8, _olan8, _bit8,
                                      bugun=_BUGUN)
esit(_sayi, 1, f"yalnizca BAYAT bekliyor ({_ornek})")
esit(_ornek, ["BAYAT"], "ornekte dogru sirket")
# 2026-06-30 -> 2026-10-30 arasi 122 gun.
esit(_eski, 122, "bekleme suresi donem BITISINDEN olculuyor")

# SAYFASI HIC OLMAYAN BURADA SAYILMIYOR -- ayri olculuyor ve ayri
# raporlaniyor ("N sirketin HIC sayfasi yok").
esit("SAYFASIZ" in _ornek, False, "sayfasiz sirket bu olcumde YOK")

# BITISI BILINMEYEN: sayiliyor ama YAS IDDIA EDILMIYOR. Uydurma bir
# gun sayisi, olculmemis bir seyi olculmus gibi gosterirdi.
_s2, _e2, _o2 = US.gecikme_olc(
    _ozet(MECHUL=None), {("MECHUL", "zzz")}, {"MECHUL"}, {},
    bugun=_BUGUN)
esit(_s2, 1, "bitisi bilinmeyen de bekleyenlerde")
esit(_e2, 0, "bitisi bilinmeyende yas SIFIR -- uydurulmuyor")

# HICBIRI BAYAT DEGILSE SIFIR. Mesru sifir, kusur degil.
_s3, _e3, _o3 = US.gecikme_olc(
    _ozet(GUNCEL="2026-09-30"), {("GUNCEL", "2026 3. çeyrek")},
    {"GUNCEL"}, {"GUNCEL": "2026-09-30"}, bugun=_BUGUN)
esit((_s3, _e3), (0, 0), "hepsi guncelse gecikme YOK")

print("")
print("9. URETIM GECIKMEYI GERCEKTEN BILDIRIYOR")
# Olcum dogru calissa da `main` onu cagirmazsa rapor OLU kalir.
_ag9 = ast.parse(pathlib.Path(US.__file__).read_text(encoding="utf-8"))
_m9 = next(f for f in ast.walk(_ag9)
           if isinstance(f, ast.FunctionDef) and f.name == "main")
_c9 = [c for c in ast.walk(_m9) if isinstance(c, ast.Call)
       and isinstance(c.func, ast.Name) and c.func.id == "_gecikme_bildir"]
esit(len(_c9), 1, "main gecikmeyi bildiriyor")
# Rapor KIRMIZI DONDURMEMELI: cagri bir kosulun icinde olmamali ve
# ardindan `return 1` gelmemeli.
_d9 = ast.parse(pathlib.Path(US.__file__).read_text(encoding="utf-8"))
_fn = next(f for f in ast.walk(_d9)
           if isinstance(f, ast.FunctionDef) and f.name == "_gecikme_bildir")
esit([r for r in ast.walk(_fn)
      if isinstance(r, ast.Return) and r.value is not None], [],
     "bildirim deger DONDURMUYOR -- kapi degil, olcum")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
