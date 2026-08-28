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
# KAVRAM GRAFIK OLMAMALI.
#
# Ilk uretimde "Borsa" icin "stock index board with candlestick shapes"
# istendi ve TAMAMEN SAHTE BIR GRAFIK cikti: eksenli, mumlu, yukselen.
#
# Bu site GERCEK olcum grafikleri yayimliyor (`grafik.py`). Yaninda
# uydurma bir grafik goruntusu, okurun ikisini ayirmasini imkansiz
# kilar -- ve bu, etiketle bile kapatilamayacak bir karisiklik.
#
# Kavramin OZNESI bir grafik olamaz. Grafik YAN OGE olabilir --
# sepetin yanindaki yukselen ok gibi; o okun eksen ya da degeri yok ve
# kimse onu veri sanmaz. Yasak olan, grafigin gorselin KENDISI olmasi.
#
# Olcut ilk bes sozcuk: Ingilizce'de ozne orada duruyor.
#
#     "a shopping basket with everyday groceries..."  -> ozne sepet, GECER
#     "an abstract stock index board with candle..."  -> ozne pano, KALIR
#
# Ilk denemem virgulden boluyordu ve yaniliyordu: kavramlarin cogu tek
# cumle, dolayisiyla butun metin "ilk boluma" giriyor ve sondaki
# "line chart" ozne saniliyordu.
# --------------------------------------------------------------------
_GRAFIK_SOZ = ("chart", "candlestick", "graph", "index board", "ticker",
               "price line", "trend line")
for konu in gu.KONU_KAVRAMI:
    for kavram in gu.kavramlar(konu):
        esit(any(s in kavram.lower() for s in _GRAFIK_SOZ), False,
             f"kavramda grafik YOK: {konu}")

# --------------------------------------------------------------------
# VARYANTLAR: TEKRARI BOLMEK ICIN, TAVAN KOYMAK ICIN DEGIL.
#
# Olculdu: cizimlerin %69'u tek konudaydi -- 295 sayfanin 205'i
# Jeopolitik ve TEK gorsel 205 sayfada goruntuleniyordu. Fotografta
# tekrar tavani 8'e cekilmisti; cizimde tavan yoktu.
#
# Tavan koymak cozum DEGIL: tavana takilan sayfa gorselsize geri
# doner, yani basa sarar. Varyant cozum.
# --------------------------------------------------------------------
esit(gu.kavramlar("Enflasyon"), (gu.KONU_KAVRAMI["Enflasyon"],),
     "tek metin kavram demete çevriliyor")
esit(len(gu.kavramlar("Jeopolitik")) >= 2, True,
     "yoğun konunun birden fazla varyantı var")
esit(gu.kavramlar("Boyle Bir Konu Yok"), (), "tanımsız konu boş demet")

# Her varyantin AYRI dosya adi olmali; yoksa ikinci varyant birincinin
# uzerine yazar ve varyant diye bir sey kalmaz.
for konu in gu.KONU_KAVRAMI:
    adlar = [gu._stem(konu, i) for i in range(len(gu.kavramlar(konu)))]
    esit(len(set(adlar)), len(adlar), f"varyant adları ayrı: {konu}")

# Secim ANAHTARA gore ve KARARLI: ayni haber her koşuda ayni varyanti
# almali, yoksa sayfa her kuruldugunda gorsel oynar.
_a = gu.dosyasi("Jeopolitik", "/haber/ornek/")
esit(gu.dosyasi("Jeopolitik", "/haber/ornek/"), _a,
     "aynı adres aynı varyantı alıyor")

# --------------------------------------------------------------------
# KAVRAM YONLU OLAMAZ.
#
# Ikinci uretimde Borsa icin bir BOGA silueti geldi: temiz, metinsiz,
# grafiksiz. Yine de reddedildi -- boga yukselen piyasa demek ve o
# gorsel Borsa konulu 759 haberin HEPSINDE gorunuyor, bir kismi dusus
# haberi.
#
# Ayni kusur ilk turda onaylanan bes cizimde de vardi (yukselen ok ya
# da yukselen cizgi). "Enflasyon %31,75'e geriledi" haberinin yaninda
# buyuk bir yukselen ok yanlis duruyor.
#
# Konu basina TEK gorsel kullanildigi surece yonlu sembol
# kullanilamaz. Bu sinama kurali kalici kiliyor.
# --------------------------------------------------------------------
import re as _re  # noqa: E402

_YON_SOZ = ("rising", "falling", "upward", "downward", "growth",
            "declining", "increasing", "decreasing", "bull", "bear",
            "arrow", "volatile", "soaring", "plunging")
# KELIME SINIRI SART -- ALT DIZGE ARAMASI YANLIS ALARM URETIYOR.
#
# Once `s in kavram.lower()` yaziyordu. Olculdu (2026-08-28): yeni bir
# Jeopolitik kavrami olan "a NARROW sea strait ..." bu sinamaya
# takildi, cunku "narrow" kelimesi "arrow" iceriyor. Yonlu bir sembol
# yok; eslesme tamamen bicimsel.
#
# Ayni tuzak bu depoda birkac yerde daha yasandi ("ufe" ⊂
# "mufettisleri", "cat" ⊂ "indicator"). Sinir isareti olmadan bir
# yasak listesi, yasakladigi seyi degil ona benzeyen kelimeleri
# eliyor -- ve bunu SESSIZCE yapiyor: kural dogru gorunuyor, yalnizca
# mesru bir girdi reddediliyor.
_YON = _re.compile(r"\b(" + "|".join(_YON_SOZ) + r")\b", _re.I)
for konu in gu.KONU_KAVRAMI:
    for kavram in gu.kavramlar(konu):
        bulunan = _YON.findall(kavram)
        esit(bulunan, [], f"kavram YÖN taşımıyor: {konu}")

# Stil de yasagi tasimali: kavram temiz olsa bile model kendiliginden
# ok ekleyebiliyor, olculdu.
for zorunlu in ("no arrows", "no charts", "no trend lines",
                "no upward or downward direction", "no currency symbols"):
    esit(zorunlu in gu.STIL, True, f"stil yasağı var: '{zorunlu}'")

# --------------------------------------------------------------------
# ISTEM DEGISINCE DOSYA ADI DA DEGISMELI.
#
# Once ad yalnizca konu+stilden turuyordu ve bu SESSIZ BIR TUZAKTI:
# kavram metni degistiginde ad degismiyor, `_mevcut` eski dosyayi
# buluyor ve yeni istem HIC CALISMIYORDU. "Istemi duzelttim" diyen bir
# degisiklik hicbir seyi degistirmiyordu.
# --------------------------------------------------------------------
_once = gu._stem("Enflasyon")
_yedek_kavram = gu.KONU_KAVRAMI["Enflasyon"]
gu.KONU_KAVRAMI["Enflasyon"] = "something completely different"
esit(gu._stem("Enflasyon") != _once, True,
     "kavram değişince dosya adı DEĞİŞİYOR")
gu.KONU_KAVRAMI["Enflasyon"] = _yedek_kavram
esit(gu._stem("Enflasyon"), _once, "kavram geri alınınca ad da aynı")

# --------------------------------------------------------------------
# UZANTI VARSAYILMIYOR, BAYTTAN OKUNUYOR.
#
# Ilk uretim dosyalari `.png` adiyla yazdi ama icerik JPEG'di --
# `flux-1-schnell` JPEG donduruyor. Sunucu tipi UZANTIDAN belirledigi
# icin 18 dosya `image/png` basligiyla JPEG baytlari servis ediyordu.
# Tarayici icerigi kokledigi icin goruntuleniyordu, ama `nosniff`
# basligi eklendigi gun hepsi GORUNMEZ olurdu.
# --------------------------------------------------------------------
esit(gu._uzanti(b"\xff\xd8\xff\xe0" + b"\x00" * 8), ".jpg", "JPEG tanınıyor")
esit(gu._uzanti(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8), ".png", "PNG tanınıyor")
esit(gu._uzanti(b"RIFF\x00\x00\x00\x00WEBP"), ".webp", "WebP tanınıyor")
esit(gu._uzanti(b"tanimsiz veri"), "", "tanınmayan biçim BOŞ döner")

# --------------------------------------------------------------------
# ONAY LISTESI: BAKILMAMIS CIZIM SAYFAYA CIKAMAZ.
#
# EN ONEMLI SINAMA. Istem yeterli bir koruma degil ve bu olculdu: ilk
# uretimde istemde "no text, no letters, no numbers" yazili oldugu
# halde iki gorselde METIN cikti (biri "CENTRAL BANK", digeri "Price")
# ve bir gorsel tamamen sahte bir grafikti.
#
# Yani modelin olumsuz talimatlara uydugu VARSAYILAMAZ ve "uretilen
# gorsel yayimlanmadan once gorulmeli" bir aliskanlik olarak
# birakilamaz. Liste onu kural yapiyor.
# --------------------------------------------------------------------
esit(gu.onayli_mi("Boyle Bir Konu Yok"), False, "tanımsız konu onaylı DEĞİL")

# Listedeki her konu KONU_KAVRAMI icinde olmali; yoksa liste sessizce
# etkisiz kalir (`dosyasi` zaten `_mevcut` uzerinden None doner).
for k in gu.ONAYLI:
    esit(k in gu.KONU_KAVRAMI, True, f"onaylı konu tanımlı: {k}")

# Hash BICIMI de sinaniyor: kisaltilmis ya da elle yazilmis bir deger
# hicbir dosyayla eslesmez ve o konu sessizce gorselsiz kalir.
def _sha_mi(h):
    return len(h) == 64 and all(c in "0123456789abcdef" for c in h)


for k, h in gu.ONAYLI.items():
    # Varyantli konularda deger DEMET; tekli konularda duz metin.
    hepsi = (h,) if isinstance(h, str) else h
    esit(all(_sha_mi(x) for x in hepsi), True, f"hash tam sha256: {k}")
    # Onay sayisi varyant sayisiyla ORTUSMELI. Ortusmezse fazlalik
    # sessizce yok sayilir, eksiklik ise o varyanti gorunmez kilar --
    # ikisi de fark edilmeden gecer.
    esit(len(hepsi), len(gu.kavramlar(k)), f"onay sayısı = varyant: {k}")

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
# `sira` bir tamsayi indeks (kacinci varyant), metin degil -- yani
# baslik tasiyamaz. Liste TAM eslesiyor: yeni bir metin parametresi
# eklenirse bu sinama KALIR ve o parametre baslik olabilir.
esit(list(imza.parameters), ["konu", "sira"],
     "istem yalnızca konu ve varyant sırası alıyor -- başlık alamaz")
# `from __future__ import annotations` acik oldugu icin ek acikama
# METIN olarak duruyor -- `int` degil `'int'`.
esit(imza.parameters["sira"].annotation, "int", "varyant sırası tamsayı")

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
import tempfile  # noqa: E402

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
    # HEDEF gecici BOS dizine cevriliyor: butun cizimler onaylandiktan
    # sonra `main` "hepsi hazir" deyip 0 ile ciktigi icin kimlik
    # kontroluna HIC ULASMIYOR. Sinamanin olcmek istedigi sey uretim
    # yolu, dolayisiyla uretilecek bir sey OLMALI.
    _asil_hedef = gu.HEDEF
    _gecici = tempfile.TemporaryDirectory()
    gu.HEDEF = pathlib.Path(_gecici.name)
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
    gu.HEDEF = _asil_hedef
    _gecici.cleanup()
finally:
    for k in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
        os.environ.pop(k, None)
    for k, v in _yedek.items():
        if v is not None:
            os.environ[k] = v

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
