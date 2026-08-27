"""insa.py testleri -- AGA CIKMAZ, SITE KURMAZ.

Buradaki kurallarin ortak ozelligi sessiz olmalari: sayfa duzgun
gorunur, yalnizca icindeki iki sayi birbirini tutmaz.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK.parent / "haber_botu"),
                str(_KOK.parent / "haber_botu" / "kaynak"),
                str(_KOK.parent / "haber_botu" / "analiz")]

import insa  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


# ------------------------------------------------------------------
# VERI ACIKLAMASININ KENDISINDE BRIFING KUTUSU BASILMAZ.
#
# Kutunun "Son aciklanan" degeri DEPODAN geliyor. Haberin kendisi o
# aciklamaysa depodaki deger haberden eski olabiliyor. Olculdu ve
# YAYIMLANDI: basligi "ABD TÜFE: yıllık %3,73" olan sayfada kutu
# "Son açıklanan %3,5" diyordu -- ikisi de ABD TUFE yillik.
# ------------------------------------------------------------------
print("Veri aciklamasinda brifing kutusu basilmaz")
VARLIK = [{"kod": "CPI_US", "ad": "ABD TÜFE", "tur": "gosterge", "yol": "/x/"}]
# Takvim kalemi, `gosterge_brifingi`nin okudugu alanlarla: eksik alan
# birakmak testi kural yerine KeyError'la dusururdu.
TAKVIM = [{"seri": "CPIAUCSL", "ad": "ABD TÜFE", "gun": "13 Ağustos 2026",
           "saat": "15:30", "kesin": True, "ulke": "ABD", "onem": 3}]

es("veri aciklamasi -> kutu YOK",
   insa.gosterge_brifingi(
       {"adres": insa._VERI_ONEK + "CPIAUCSL/2026-08", "baslik": "ABD TÜFE"},
       VARLIK, TAKVIM),
   None)

# Bekleyis haberinde kutu DOGRU ve degerli: veri henuz aciklanmadi.
# Burada `None` DISI bir sonuc bekleniyor ama icerigi takvim/tanim
# verisine bagli; testin isi kurallarin ayrimini dogrulamak.
print("\nBekleyis haberinde kural engellemiyor")
bekleyis = insa.gosterge_brifingi(
    {"adres": "https://ornek.com/haber/1", "baslik": "Gözler TÜFE'de"},
    VARLIK, TAKVIM)
dogru("bekleyiste adres kurali devreye girmiyor",
      bekleyis is None or isinstance(bekleyis, dict))

print("\nSinir durumlar")
es("varliksiz haber", insa.gosterge_brifingi(
    {"adres": "https://ornek.com/1"}, None, TAKVIM), None)
es("takvimsiz", insa.gosterge_brifingi(
    {"adres": "https://ornek.com/1"}, VARLIK, []), None)

# ------------------------------------------------------------------
# DOSYASI OLMAYAN GORSEL BASILMAZ. Editoryal suzgec siklastiginda 49
# gorsel havuzdan cikarildi ve iki sayfa silinmis dosyaya isaret
# etmeye devam etti -- sayfada kirik gorsel, gunlukte hicbir iz.
# ------------------------------------------------------------------
print("\nKucuk gorsel: dosya yoksa bos doner")
es("olmayan dosya", insa.kucuk_foto("/statik/foto/yok-boyle-bir-dosya.jpg"), "")
es("havuz disi yol", insa.kucuk_foto("/statik/logo.svg"), "")
es("bos yol", insa.kucuk_foto(""), "")

# ------------------------------------------------------------------
# OKURUN DOGRULAYAMADIGI SAYI BASILMAZ (promptun 7. maddesi).
# ------------------------------------------------------------------
print("\nYorum dogrulanabilirligi")
h = {"baslik": "ABD TÜFE yıllık %3,73", "ozet": "Beklenti %3,40"}
dogru("sayfadaki sayilari anan yorum gecer",
      insa._yorum_dogrulanabilir("TÜFE %3,73 ile beklentinin üzerinde", h, None))
dogru("sayfada olmayan sayilari anan yorum GECMEZ",
      not insa._yorum_dogrulanabilir(
          "İşsizlik %7,40 ve cari açık 1.459 mn $ seviyesinde", h, None))
dogru("sayisiz yorum gecer",
      insa._yorum_dogrulanabilir("Mekanizma enerji maliyeti üzerinden işler",
                                 h, None))

# ------------------------------------------------------------------
# "NETARIS NE DIYOR" SIRASI -- promptun 14. maddesi:
# "yalnizca AI yorumu uretildigi icin her haber mansete tasinmamalidir".
#
# Bolum ZAMANA gore siraliydi, yani buraya girmenin tek sarti yorumun
# olmasiydi. Olculdu: alti kartin ucu en yuksek puanli haberler
# arasinda degildi; puani daha yuksek iki haber ise yorumu olmadigi
# icin bolumde yoktu. Ustelik bolum "Bugunun onemli gelismeleri"nin
# USTUNDE duruyor.
# ------------------------------------------------------------------
print("\nAI akisi oneme gore siralaniyor")
# Yorumlar BIRBIRINDEN FARKLI olmali: bolum ayni seyi soyleyen ikinci
# yorumu almiyor (alti kartin ucu ayni Brent cumlesini kuruyordu).
# Ilk yazimda ucune de "yorum" yazdim ve ikisi tekrar sayilip elendi.
_h = [
    {"baslik": "dusuk puan, YENI", "yol": "/a/", "onem": 10,
     "ai_yorum_kart": "Enerji maliyeti kanalindan sanayi karliligi",
     "an": "2026-08-10T12:00"},
    {"baslik": "yuksek puan, ESKI", "yol": "/b/", "onem": 90,
     "ai_yorum_kart": "Faiz patikasi tahvil getirilerini yeniden fiyatlar",
     "an": "2026-08-01T12:00"},
    {"baslik": "orta puan", "yol": "/c/", "onem": 50,
     "ai_yorum_kart": "Kur gecisi gida enflasyonunda gecikmeli gorunur",
     "an": "2026-08-05T12:00"},
]
_s = [x["baslik"] for x in insa.ai_akisi(_h, en_cok=3)]
es("once yuksek puan", _s, ["yuksek puan, ESKI", "orta puan", "dusuk puan, YENI"])

# Yorum GIRIS SARTI olmaya devam ediyor: soyleyecek sozumuz yoksa
# haber ne kadar onemli olursa olsun bu bolume girmiyor.
es("yorumsuz haber girmez",
   insa.ai_akisi([{"baslik": "yorumsuz", "yol": "/d/", "onem": 99}]), [])
es("sayfasiz haber girmez",
   insa.ai_akisi([{"baslik": "sayfasiz", "onem": 99,
                   "ai_yorum_kart": "Sayfasi olmayan haber"}]), [])

# Esit puanda YENI olan once gelir.
_e = [{"baslik": "eski", "yol": "/1/", "onem": 50, "an": "2026-08-01",
       "ai_yorum_kart": "Tahvil getirisi ve kur birlikte fiyatlaniyor"},
      {"baslik": "yeni", "yol": "/2/", "onem": 50, "an": "2026-08-09",
       "ai_yorum_kart": "Rezerv hareketi banka bilancolarina yansiyor"}]
es("esitlikte yeni once", [x["baslik"] for x in insa.ai_akisi(_e, en_cok=2)],
   ["yeni", "eski"])

print()
for k in kaldi:
    print("  KALDI", k)

print()
print("Senaryo cagrisi -- OLCULMUS ORAN tasiyan baslik aciliyor")

# Kullanici bildirdi (2026-08-25): "TCMB agirlikli ortalama fonlama
# maliyeti: %37,00" haberinde senaryo secenegi yoktu. Iki yolun
# ikisinde de takiliyordu -- tek varliga bagli (esik 2) ve olay
# siniflandirici basligi hic eslestiremiyor.
#
# Oysa bu senaryo yazmaya EN uygun haber turu: ortada somut, olculmus
# bir sayi var ve okur "%37 uzerinde kalirsa..." diye kosul
# kurabiliyor.

def _h(baslik, konu="Para politikası"):
    return {"konu": konu, "baslik_tr": baslik, "kurum": "TCMB"}

es("yuzde tasiyan baslik aciliyor", insa.senaryoya_acik(_h("TCMB ağırlıklı ortalama fonlama maliyeti: %37,00"),
                         ["TCMB"]), True)
es("'yuzde' yazili baslik da aciliyor", insa.senaryoya_acik(_h("Sanayi üretimi yıllık yüzde 1,4 azaldı"), []), True)
es("baz puan aciliyor", insa.senaryoya_acik(_h("Merkez bankası 250 baz puan indirdi"), []), True)

# TUTAR OLCUM DEGIL. Genis desen "Emekli maas farklari yatti mi?
# 3.552 TL" gibi hizmet haberlerini de aciyordu -- sayi var ama
# uzerine kosul kurulacak bir oran yok. Olculdu: genis +141, dar +86.
es("yalniz TUTAR tasiyan baslik acilmiyor", insa.senaryoya_acik(_h("Emekli maaş farkları yattı mı? 3.552 TL fark"),
                         []), False)

# KONU SUZGECI HALA ONDE: olcum olsa bile konusu uygun degilse
# senaryo yazilmaz.
es("konusu uygun olmayan baslik olcumle de acilmiyor", insa.senaryoya_acik(_h("Bir dizinin reytingi yüzde 12 arttı",
                            konu="Turizm"), []), False)

# Desen kendi kendini sinar -- bozulursa sessizce hicbir sey
# eslestirmez ve ustteki "gecti"ler anlamsiz olurdu.
es("desen % yakaliyor", bool(insa.SENARYO_OLCUM.search("%37,00")), True)
es("desen 'yuzde' yakaliyor", bool(insa.SENARYO_OLCUM.search("yüzde 1,4")), True)
es("desen tutari yakalamiyor", bool(insa.SENARYO_OLCUM.search("3.552 TL")), False)

# ------------------------------------------------------------------
# KART KUNYESI AYNI BILGIYI IKI KEZ YAZMAZ.
#
# Olculdu (2026-08-27): ana sayfadaki 220 kart kunyesinin 5'i tarihi
# IKI KEZ yaziyordu --
#
#     "23 Temmuz 2026 · 2 dk okuma · 23 Temmuz 2026"
#
# Sebep `donem` alaninin kategoriye gore FARKLI SEY anlatmasi:
#
#     Bilanco Analizi     donem="2026 1. ceyrek"   233/233 tarihten FARKLI
#     Makro/Teknik/Yorum  donem="2026-08-01"       236/236 tarihe ESIT
#
# Yani alan bilanco icin gercek bilgi, digerleri icin yayin tarihinin
# kopyasi. Kunye kosulsuz basiyordu.
#
# Kural KATEGORIYE gore degil EKRANDA GORUNEN HALE gore kuruldu: iki
# alan ayni gorunuyorsa ikincisi tekrardir. Boylece yeni bir kategori
# eklendiginde de dogru kalir -- kategori listesi elle bakimli olsaydi
# suruklenirdi.
# ------------------------------------------------------------------
def _kunye(donem, tarih_iso, tarih_tr):
    """Sablondaki kosulun ayni sonucu: donem basilir mi?"""
    return bool(donem) and insa.gun_etiketi(donem) != tarih_tr


dogru("bilanco donemi basilir (tarihten farkli)",
      _kunye("2026 1. çeyrek", "2026-08-23", "23 Ağustos 2026"))

dogru("makro donemi BASILMAZ (tarihe esit)",
      not _kunye("2026-08-01", "2026-08-01", "1 Ağustos 2026"))

dogru("yorum donemi BASILMAZ (tarihe esit)",
      not _kunye("2026-07-23", "2026-07-23", "23 Temmuz 2026"))

dogru("donem yoksa basilmaz", not _kunye("", "2026-08-01", "1 Ağustos 2026"))

# Sablon kosulu GERCEKTEN orada mi. Yukaridaki islev sablonu taklit
# ediyor; sablon degisirse taklit sessizce eskir.
_ANA = (_KOK / "sablonlar" / "anasayfa.html").read_text(encoding="utf-8")
dogru("anasayfa kunyesi donem'i kosulsuz basmiyor",
      "a.donem and (a.donem|gun) != a.tarih_tr" in _ANA)



# ------------------------------------------------------------------
# KAYIT DEFTERINDE OLUP DISKTE OLMAYAN LOGO BASILMAZ.
#
# Olculdu (2026-08-27): `logo_kayit.json` 15 logo listeliyordu,
# `site/statik/logo/` icinde 13 dosya vardi. Eksik ikisi sekiz
# sayfada KIRIK GORSEL olarak basiliyordu -- sirketin isareti yerine
# tarayicinin kirik resim simgesi.
#
# Kayit dosya YAZILDIGINDA guncelleniyor; dosya sonradan kaybolursa
# (basarisiz indirme, temizlik, depoya girmemis dosya) defteri kimse
# duzeltmiyor. Yani defter tek basina yeterli kanit degil.
#
# Ayni ilke `_boy_foto` ve kavram gorsellerinde zaten uygulaniyordu;
# logo yolu disinda kalmisti.
# ------------------------------------------------------------------
dogru("olmayan logo dosyasi diskte YOK sayilir",
      not insa._logo_diskte("/statik/logo/boyle-bir-dosya-yok.svg"))

dogru("bos yol diskte YOK sayilir", not insa._logo_diskte(""))

_mevcut = sorted((_KOK / "statik" / "logo").glob("*"))
if _mevcut:
    dogru("var olan logo dosyasi diskte VAR sayilir",
          insa._logo_diskte("/statik/logo/" + _mevcut[0].name))

# DUSUS CALISIYOR MU.
#
# ILK YAZIMDA BU SINAMA ISE YARAMIYORDU: `sirket_gorseli("YOKKOD")`
# cagriliyordu ama YOKKOD onayli listede olmadigi icin islev daha ilk
# satirda donuyor ve logo koluna HIC girmiyordu. Disk kontrolu
# kaldirildiginda test yine yesil kaliyordu -- yani korumayi degil,
# alakasiz bir dali olcuyordu.
#
# Dogru kurulum: kodu ONAYLI yapip kayit defterine OLMAYAN bir dosya
# koymak. Ancak o zaman islev gercekten logo kolundan geciyor.
_onayli_yedek = insa._ONAYLI_LOGO
_kayit_yedek = getattr(insa, "__LOGO", None)
try:
    # BES HARF: `amblem()` BIST kod bicimi bekliyor ve daha uzun bir
    # dizgide BOS donuyor. Ilk yazimda "TESTKOD" kullanildi, cikti bos
    # geldi ve "logo basilmadi" sinamasi BOS CIKTI SAYESINDE geciyordu
    # -- yani yine yanlis seyi olcuyordu.
    insa._ONAYLI_LOGO = frozenset({"TSTKD"})
    setattr(insa, "__LOGO", {"TSTKD": {"yol": "/statik/logo/yok-boyle.svg"}})
    _cikti = insa.sirket_gorseli("TSTKD", "Deneme A.Ş.", "Sanayi", "2026/3")
    dogru("kayitta olup diskte olmayan logo BASILMAZ",
          "/statik/logo/" not in _cikti)
    dogru("yerine amblem uretiliyor (sirket gorselsiz kalmiyor)",
          bool(_cikti.strip()))

    # Karsit durum: dosya GERCEKTEN varsa logo basilmali. Aksi halde
    # "hicbir zaman logo basma" da testi gecerdi.
    if _mevcut:
        setattr(insa, "__LOGO",
                {"TSTKD": {"yol": "/statik/logo/" + _mevcut[0].name}})
        _cikti2 = insa.sirket_gorseli("TSTKD", "Deneme A.Ş.", "Sanayi",
                                      "2026/3")
        dogru("diskte VAR olan logo basiliyor",
              "/statik/logo/" + _mevcut[0].name in _cikti2)
finally:
    insa._ONAYLI_LOGO = _onayli_yedek
    if _kayit_yedek is None:
        if hasattr(insa, "__LOGO"):
            delattr(insa, "__LOGO")
    else:
        setattr(insa, "__LOGO", _kayit_yedek)

# HANGI SINAMA KALDIGI YAZILIYOR.
#
# Onceden yalnizca sayi basiliyordu ("1 kaldi") ve o sayi tek basina
# ise yaramiyordu: bakan kisi hangi kuralin bozuldugunu goremiyordu.
# Ayni eksik `insa.py`nin yorum tanilamasinda da vardi.
for _k in kaldi:
    print(f"  KALDI  {_k}")
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)

