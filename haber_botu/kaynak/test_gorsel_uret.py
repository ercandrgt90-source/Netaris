"""Uretilen gorsel: KAVRAM cizer, OLAY CIZMEZ.

BU DOSYA NEDEN VAR
------------------
Uretilen gorselde asil risk teknik degil EDITORYAL: fotogercekci bir
"Fed toplantisi" gorseli, gercek bir olayin sahte goruntusudur ve bu
sitenin butun degeri "hicbir sey uydurulmaz" iddiasinda.

Sinamalar tek bir seye bakiyor: istem, olayi canlandirabilecek hicbir
sey TASIMIYOR mu. Ozellikle haber basligi -- basligi isteme koymak en
kolay yoldu ve tam da yapilmamasi gereken sey.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from kaynak import gorsel_uret as gu  # noqa: E402

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
# HER ISTEM FOTOGERCEKCILIKTEN UZAK DURUYOR.
# --------------------------------------------------------------------
for konu in gu.KONU_KAVRAMI:
    p = gu.istem(konu)
    esit(bool(p), True, f"istem uretiliyor: {konu}")
    esit(gu.istem_guvenli(p), True, f"fotogercekci degil: {konu}")
    for zorunlu in ("not photorealistic", "no people", "no logos",
                    "flat vector"):
        esit(zorunlu in p, True, f"{konu}: '{zorunlu}' var")

# --------------------------------------------------------------------
# TANIMSIZ KONU GORSEL URETMIYOR.
#
# Bilinmeyen konuya "genel finans" gorseli uretmek, konusuyla ilgisiz
# bir gorsel basmak demek -- kullanicinin bastan sikayet ettigi sey.
# Gorselsiz kalmak, alakasiz gorselden iyidir.
# --------------------------------------------------------------------
esit(gu.istem("Boyle Bir Konu Yok"), "", "tanimsiz konu istem URETMIYOR")
esit(gu.uret("Boyle Bir Konu Yok"), None, "tanimsiz konu gorsel URETMIYOR")

# --------------------------------------------------------------------
# HABER BASLIGI ISTEME GIRMIYOR.
#
# En onemli sinama. "Iran limanina saldiri" basligindan uretilen
# gorsel, olmamis bir saldirinin goruntusu olur. Kalip sabit oldugu
# icin baslik zaten girmiyor; bu sinama ileride biri `istem`e baslik
# parametresi eklerse KALIR.
# --------------------------------------------------------------------
import inspect  # noqa: E402
imza = inspect.signature(gu.istem)
esit(list(imza.parameters), ["konu"],
     "istem YALNIZCA konu aliyor -- baslik alamaz")

# --------------------------------------------------------------------
# YASAK SOZCUK SUZGECI CALISIYOR.
#
# Kalip degistirilirse fotogercekcilige kayis burada yakalanmali.
# --------------------------------------------------------------------
esit(gu.istem_guvenli("a photorealistic photo of a central bank"), False,
     "fotogercekci istem REDDEDILIYOR")
esit(gu.istem_guvenli("a portrait of a person"), False,
     "kisi iceren istem REDDEDILIYOR")
esit(gu.istem_guvenli("realistic news footage"), False,
     "haber goruntusu istemi REDDEDILIYOR")
# Olumsuz kullanim serbest olmali, yoksa kendi kalibimiz reddedilirdi.
esit(gu.istem_guvenli("flat vector, not photorealistic, no people"), True,
     "olumsuz kullanim serbest")

# --------------------------------------------------------------------
# ETIKET ZORUNLU VE URETILDIGINI SOYLUYOR.
#
# Uretilmis gorseli fotograf gibi sunmak, sitenin kaynak seffafligi
# ilkesinin ihlali. Fotograflarda CC atfi nasil zorunluysa bu da oyle.
# --------------------------------------------------------------------
esit("yapay zeka" in gu.ETIKET.lower(), True,
     "etiket uretildigini SOYLUYOR")

# --------------------------------------------------------------------
# KIMLIK BILGISI OLMADAN AG ISTEGI YAPILMIYOR.
#
# ORTAM DEGISKENLERI SILINEREK sinaniyor. `uret` bos argumanlari ortam
# degiskenine dusuruyor; sinama onlari temizlemezse ve bir gun test
# adimina kimlik eklenirse BU SINAMA GERCEK BIR AG ISTEGI ATARDI --
# kota yakar ve sinamayi ag durumuna bagimli kilar.
# --------------------------------------------------------------------
import os  # noqa: E402

_yedek = {k: os.environ.pop(k, None)
          for k in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN")}
try:
    esit(gu.uret("Enflasyon", hesap="", jeton=""), None,
         "kimlik yoksa None -- ağ isteği YOK")

    # ------------------------------------------------------------------
    # SESSIZLIK BASARI SAYILMAZ.
    #
    # Ilk koşu tam bunu yasadi: uretim basarisiz oldu, betik 0 ile cikti,
    # is akisi YESIL gorundu ve depoya hicbir sey dusmedi. "Calisti" gibi
    # duran bir koşu hicbir sey yapmamisti.
    #
    # Bu depoda ayni ders birkac kez tekrarlandi: yanlis "0 ihlal"
    # raporlayan denetim, "189 sayfa eksik" diyen bozuk sitemap taramasi.
    # Eksik tarama temiz rapor uretir; en tehlikeli yanlis budur.
    # ------------------------------------------------------------------
    esit(gu.main(), 1, "kimlik yoksa main HATA döndürüyor")

    # ------------------------------------------------------------------
    # BOSLUKLU KIMLIK KIRPILIYOR.
    #
    # GitHub gizli degeri panodan alirken sonuna satir sonu takilabiliyor
    # ve h11 baslik degerinde bosluk KABUL ETMIYOR:
    #
    #     LocalProtocolError: Illegal header value b'***'
    #
    # Bir CI koşusu tam bunu yasadi. Ayni tuzak depoda daha once de
    # cikmisti ve `ai/yorumcu.py` `.strip()` ile cozmustu; yeni dosya o
    # deseni izlemeyince hata ikinci kez ciktı.
    #
    # Sinama YALNIZCA BOSLUKTAN ibaret bir kimligin "kimlik yok" sayilip
    # sayilmadigina bakiyor -- yani `.strip()` kaldirilirsa KALIR ve ag
    # istegi atmaz.
    # ------------------------------------------------------------------
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = "  \n"
    os.environ["CLOUDFLARE_API_TOKEN"] = "\n  "
    esit(gu.uret("Enflasyon"), None,
         "yalnızca boşluktan ibaret kimlik = kimlik YOK")
    esit(gu.main(), 1, "boşluklu kimlikte main HATA döndürüyor")
finally:
    for k in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
        os.environ.pop(k, None)
    for k, v in _yedek.items():
        if v is not None:
            os.environ[k] = v

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
