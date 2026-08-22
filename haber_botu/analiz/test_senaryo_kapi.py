"""Senaryo kapisi: YARGI degil, dogrulanabilir ozellik.

BU DOSYA NEDEN VAR
------------------
Kullanici kalite katmanlarini yapay zeka performansina baglamayi sordu.
Modele "bu senaryo kaliteli mi" sorup gorunur rozet vermek yanlis
olurdu; bu depo ayni konuda iki kez karar verdi ("Guven Skoru %83" ve
"Veri Gucu 97" reddedildi). Gerekce: hesaplanmamis yargiyi olcum gibi
sunmak.

Kapi bunun yerine EVET/HAYIR sorulari soruyor. Sinamalar iki yonu
birlikte tutuyor:
  * sinanabilir kosul GECMELI
  * kacamak kosul GECMEMELI
Ikincisi olmadan kapi zamanla her seyi gecirir ve anlamsizlasir.

YANLISLANABILIRLIK NEDEN MERKEZDE
---------------------------------
Sonucu olculemeyen senaryo hicbir zaman sonuclanamaz; sonuclanmayan
senaryo sicil olusturamaz; sicil olmadan katman kurulamaz. Butun
katman sisteminin temeli bu tek ozellik.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from analiz import senaryo_kapi as sk  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


# --------------------------------------------------------------------
# SINANABILIR KOSULLAR GECMELI.
# --------------------------------------------------------------------
for k in ("TÜFE %30'un altına inerse",
          "Fed Eylül'de faizi 25 baz puan indirirse",
          "Brent 100 doların üzerine çıkarsa",
          "TCMB politika faizini sabit tutarsa",
          "Dolar 50 TL'yi aşarsa"):
    esit(sk.yanislanabilir(k), True, f"sinanabilir: {k[:38]}")

# --------------------------------------------------------------------
# KACAMAK KOSULLAR GECMEMELI.
#
# Bu yon olmadan kapi zamanla her seyi gecirir. "Piyasalar
# dalgalanabilir" HER DURUMDA dogru cikar -- yani hicbir sey
# soylemiyor ve sonuclandirilamaz.
# --------------------------------------------------------------------
for k in ("Piyasalar dalgalanabilir",
          "Belirsizlik sürebilir",
          "Bir şeyler olabilir",
          "Etkilenme görülebilir"):
    esit(sk.yanislanabilir(k), False, f"sinanamaz: {k[:38]}")

# Cok kisa kosul da sinanamaz sayiliyor.
esit(sk.yanislanabilir("olur"), False, "cok kisa kosul")
esit(sk.yanislanabilir(""), False, "bos kosul")

# --------------------------------------------------------------------
# KACAMAK DIL ISARETLENIYOR.
# --------------------------------------------------------------------
esit(bool(sk.kacamak_dil("Piyasalar dalgalanabilir")), True,
     "kacamak dil yakalaniyor")
esit(sk.kacamak_dil("TÜFE %30'un altına iner"), [],
     "kesin ifade kacamak sayilmiyor")

# --------------------------------------------------------------------
# SAYI DOGRULAMA -- depodaki degerlere karsi.
# --------------------------------------------------------------------
veri = {"31,75", "95,29", "3,29"}
esit(sk.dogrulanmayan_sayilar("TÜFE %31,75 ile geriledi.", veri), [],
     "depodaki sayi dogrulaniyor")
esit(sk.dogrulanmayan_sayilar("Enflasyon %99,99 oldu.", veri), ["99,99"],
     "depoda olmayan sayi isaretleniyor")
# Veri yoksa KARAR VERILMIYOR: bos kumeyle her sayi "dogrulanmaz"
# gorunurdu ve kapi yanlis alarm uretirdi.
esit(sk.dogrulanmayan_sayilar("Enflasyon %99,99 oldu.", set()), [],
     "veri yoksa sayi denetimi karar VERMIYOR")

# --------------------------------------------------------------------
# KAPI ENGELLEMIYOR, ISARETLIYOR.
#
# Zayif senaryoyu yasaklamak yerine gorunur kilmak, toplulugu kendi
# standardini kurmaya birakiyor. Yalnizca yasal engel (yatirim
# tavsiyesi) yayini durdurur ve o kontrol worker tarafinda.
# --------------------------------------------------------------------
d = sk.denetle("Piyasalar dalgalanabilir", "Belirsizlik artar", "", veri)
esit(d["engel"], [], "kapi YAYINI ENGELLEMIYOR")
esit(len(d["notlar"]) >= 3, True, "zayif senaryoda birden fazla not")

d2 = sk.denetle("TÜFE %30'un altına inerse", "TCMB faiz indirir",
                "Temmuz TÜFE %31,75.", veri,
                curutme="Gıda enflasyonu tekrar hızlanırsa")
esit(d2["notlar"], [], "saglam senaryoda not YOK")
esit(d2["yanislanabilir"], True, "saglam senaryo sinanabilir")

# --------------------------------------------------------------------
# CURUTME KOSULU -- KAPININ EN DEGERLI SORUSU.
#
# `yanislanabilir` KOSULUN olculebilirligine bakiyor: gerekli ama
# YETERLI DEGIL. "TÜFE %30'un altına inerse" olculebilir bir kosul,
# ama yazar "peki ne olursa tezim cokerdi" sorusunu cevaplamadan da
# yazabilir -- ve o soruyu cevaplamayan metin HER SONUCTA hakli cikar.
#
# Bir senaryoyu bir gorusten ayiran tek sey bu.
#
# ENGEL DEGIL NOT: zorunlu kilmak kisa ve gecerli senaryolari disarida
# birakirdi. Kapi engellemiyor, gorunur kiliyor -- ayni ilke butun
# modul boyunca gecerli.
# --------------------------------------------------------------------
print()
print("Curutme kosulu")
d3 = sk.denetle("TÜFE %30'un altına inerse", "TCMB faiz indirir",
                "Temmuz TÜFE %31,75.", veri)
esit(len(d3["notlar"]), 1, "curutme bos: TEK not uretiliyor")
esit("yanıltır" in d3["notlar"][0], True, "not curutmeyi soruyor")
esit(d3["engel"], [], "curutme eksikligi YAYINI ENGELLEMIYOR")

# Kacamak bir curutme, curutme OLMAMASI kadar kotu: "piyasalar
# dalgalanabilir" her durumda dogru cikar, yani yazari hicbir zaman
# yaniltmaz.
d4 = sk.denetle("TÜFE %30'un altına inerse", "TCMB faiz indirir",
                "Temmuz TÜFE %31,75.", veri,
                curutme="Piyasalar dalgalanabilir")
esit(len(d4["notlar"]), 1, "kacamak curutme not uretiyor")
esit("kaçamak" in d4["notlar"][0].lower(), True, "not kacamagi soyluyor")

# Eski cagri bicimi bozulmadi: `curutme` verilmeyen cagri calisiyor
# ve yalnizca not ekliyor.
d5 = sk.denetle("Piyasalar dalgalanabilir", "Belirsizlik artar", "", veri)
esit(d5["engel"], [], "eski cagri bicimi calisiyor")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
