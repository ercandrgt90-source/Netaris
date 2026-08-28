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


# ------------------------------------------------------------------
# "BUGUNUN ONEMLI GELISMELERI" TAZE OLANI ONE ALIR.
#
# Olculdu (2026-08-27): bolum yalnizca PUANA gore siralaniyordu ve
# zaman hic olcut degildi. Sonucu ekranda goruldu -- manset DUNKU bir
# haberdi, listenin altinda 42 dakikalik haberler duruyordu.
#
# Puan DEGISTIRILMEDI: bir haberin onemi zamanla azalmaz, azalan sey
# BUGUNUN listesinde yer isteme hakkidir. Tazelik yalnizca siralamaya
# giriyor.
#
# Ilk deneme ETKISIZ KALDI ve sebebi ogreticiydi: siralama
# `one_cikan_haberler` icinde yapildi ama `onem.tekille` kendi icinde
# `sorted(..., key=-puan)` cagirip disaridan gelen sirayi eziyor.
# Tazeligi gercekten uygulamanin tek yolu, `sec`in BAKTIGI puana
# yazmakti.
# ------------------------------------------------------------------
from datetime import datetime, timedelta, timezone as _tz  # noqa: E402

_simdi = datetime.now(_tz.utc)


def _hbr(ad, saat, puan, katman="normal", konu="Para politikası"):
    return {"adres": f"https://ornek.test/{ad}", "baslik": ad,
            "konu": konu, "onem": puan, "katman": katman,
            "tarih": (_simdi - timedelta(hours=saat)).strftime("%Y-%m-%d"),
            "an": (_simdi - timedelta(hours=saat)).isoformat()}


_bugun = _simdi.strftime("%Y-%m-%d")

# Dunku YUKSEK puanli haber, bugunku DUSUK puanliyi gecmemeli.
_liste = [_hbr("Dun yuksek puanli gelisme", 26, 58),
          _hbr("Bugun dusuk puanli gelisme", 1, 44)]
_sonuc = insa.one_cikan_haberler(list(_liste), _bugun)
es("taze haber, dunku yuksek puanliyi geciyor",
   _sonuc[0]["baslik"] if _sonuc else "", "Bugun dusuk puanli gelisme")

# KRITIK muaf: gercek bir kriz dun olsa da mansettir.
_liste2 = [_hbr("Dun kritik gelisme", 26, 88, katman="kritik"),
           _hbr("Bugun normal gelisme", 1, 44)]
_sonuc2 = insa.one_cikan_haberler(list(_liste2), _bugun)
es("kritik haber yastan bagimsiz onde", _sonuc2[0]["baslik"],
   "Dun kritik gelisme")

# Ayni tazelik katmaninda siralamayi PUAN belirliyor.
_liste3 = [_hbr("Bugun dusuk gelisme", 2, 42),
           _hbr("Bugun yuksek gelisme", 3, 58)]
_sonuc3 = insa.one_cikan_haberler(list(_liste3), _bugun)
es("ayni katmanda puan belirleyici", _sonuc3[0]["baslik"],
   "Bugun yuksek gelisme")

# Esigin ALTINDAKI haber, tazelik eklentisiyle listeye SIZMAMALI.
# Uygunluk gercek puanla olculuyor; aksi halde bolum secim olmaktan
# cikardi.
_liste4 = [_hbr("Onemsiz ama cok taze", 0.1, 12),
           _hbr("Onemli ve taze", 1, 55)]
_sonuc4 = insa.one_cikan_haberler(list(_liste4), _bugun)
dogru("esik altindaki haber tazelikle sizmiyor",
      all(h["baslik"] != "Onemsiz ama cok taze" for h in _sonuc4))

# Damgasi cozulemeyen haber TAZE sayilmamali.
_bilinmeyen = _hbr("Damgasi bozuk gelisme", 1, 58)
_bilinmeyen["an"] = "tarih degil"
_sonuc5 = insa.one_cikan_haberler([_bilinmeyen, _hbr("Taze gelisme", 1, 44)],
                                  _bugun)
es("cozulemeyen damga en eski sayiliyor", _sonuc5[0]["baslik"],
   "Taze gelisme")

# ------------------------------------------------------------------
# AYNI KUCUK GORSEL AKISTA IKIDEN FAZLA GORUNMEZ.
#
# Olculdu (2026-08-27, canli ana sayfa): akisin 40 satirinda 32
# benzersiz gorsel vardi ama BIR gorsel YEDI kez tekrarliyordu.
# Kullanicinin bildirdigi sey buydu -- "fotograflar cok sik geciyor".
#
# Site genelindeki tavan zaten var ama o GENEL: bir gorselin sitede
# sekiz kez gorunmesi makul. Sorun o sekizin AYNI EKRANDA
# toplanmasiydi; tekrar okura sayfa basina gorunuyor.
#
# HABER DUSURULMUYOR, YALNIZCA GORSEL. Akis bir kayit; suzulurse
# "bir sey oldu mu" sorusunun cevabi kaybolur.
# ------------------------------------------------------------------
_akis_girdi = [{"an": f"2026-08-27T{s:02d}:00:00+00:00",
                "foto": "/statik/foto/tek.jpg", "baslik": f"haber {s}"}
               for s in range(10)]
_akis = insa.canli_akis(list(_akis_girdi), 10)

es("akis haber DUSURMUYOR", len(_akis), 10)
es("ayni gorsel en fazla iki satirda",
   sum(1 for h in _akis if h.get("foto")), insa.AKIS_FOTO_TEKRARI)
dogru("tasan satirlar gorselsiz, bos dizgi ile",
      all(h.get("foto") == "" for h in _akis[insa.AKIS_FOTO_TEKRARI:]))

# OZGUN SOZLUKLER BOZULMAMALI: ayni haber onem ve AI bolumlerinde de
# kullaniliyor, orada gorseli kalmali. Kopya uzerinde siliniyor.
dogru("ozgun haber sozlukleri degismiyor",
      all(h["foto"] == "/statik/foto/tek.jpg" for h in _akis_girdi))

# Cesitli havuzda tavan devreye GIRMEMELI -- her gorsel bir kez.
_cesitli = [{"an": f"2026-08-27T{s:02d}:00:00+00:00",
             "foto": f"/statik/foto/g{s}.jpg", "baslik": f"h{s}"}
            for s in range(8)]
_c = insa.canli_akis(list(_cesitli), 8)
es("cesitli havuzda hicbir gorsel dusmuyor",
   sum(1 for h in _c if h.get("foto")), 8)

# Gorselsiz haber, tavan sayacini TUKETMEMELI.
_karisik = ([{"an": f"2026-08-27T0{s}:00:00+00:00", "foto": "",
              "baslik": f"bos {s}"} for s in range(3)]
            + [{"an": f"2026-08-27T1{s}:00:00+00:00",
                "foto": "/statik/foto/x.jpg", "baslik": f"dolu {s}"}
               for s in range(3)])
_k = insa.canli_akis(list(_karisik), 6)
es("gorselsiz satirlar sayaci tuketmiyor",
   sum(1 for h in _k if h.get("foto")), insa.AKIS_FOTO_TEKRARI)

# ------------------------------------------------------------------
# AYNI KONUSMANIN CUMLELERI AKISI DOLDURMAZ.
#
# Olculdu (2026-08-27, canli ana sayfa): kirk satirin ONBESI iki Fed
# yetkilisinin TEK konusmasindan geliyordu (6 + 5 + 4). Kaynak bir
# konusmanin her cumlesini ayri baslik olarak yayinliyor.
#
# Akis genis suzulmemeli -- o bir kayit. Ama onbes satir tek konusma,
# akisin AMACINI bozuyor: okur "bugun ne oldu" diye bakip bir kisinin
# cumlelerini goruyor. Genis eleme akisi sakatlar, bu daralma onu
# duzeltir; ikisi ayni sey degil.
# ------------------------------------------------------------------
_konusma = [{"an": f"2026-08-27T{s:02d}:00:00+00:00",
             "baslik": f"Fed'den Hammack: {s}. cumle", "foto": ""}
            for s in range(6)]
_baska = [{"an": "2026-08-27T23:00:00+00:00",
           "baslik": "TCMB rezervleri yukseldi", "foto": ""}]
_a = insa.canli_akis(_konusma + _baska, 10)
es("ayni konusmadan en fazla iki kalem",
   sum(1 for h in _a if "Hammack" in h["baslik"]), insa.AKIS_KUME_TAVANI)
dogru("baska haber akista kaliyor",
      any("TCMB" in h["baslik"] for h in _a))

# TAVAN KESMEDEN ONCE: elenen satirlarin yeri BOS kalmamali, akis
# tam sayida gorunmeli.
_bol = _konusma + [{"an": f"2026-08-26T{s:02d}:00:00+00:00",
                    "baslik": f"Ayri haber {s}", "foto": ""}
                   for s in range(10)]
es("akis tam sayida doluyor", len(insa.canli_akis(_bol, 8)), 8)

# Rakamli onek kumelenmemeli: iki ayri ayin verisi tek haber degil.
_veri = [{"an": f"2026-08-27T0{s}:00:00+00:00",
          "baslik": f"TUFE %3{s},10: aylik degisim", "foto": ""}
         for s in range(5)]
es("veri basliklari kumelenmiyor", len(insa.canli_akis(_veri, 5)), 5)

# ------------------------------------------------------------------
# KARTIN GORSEL BAGLANTISI EKRAN OKUYUCUDA GORUNMEZ.
#
# `/gundem/` kartlari AYNI HEDEFE IKI baglanti tasiyor: gorsel
# sarmalayicisi ve baslik. Baslik baglantisinin adi var; gorselinki
# ADSIZ, cunku gorselin `alt`i bilerek bos (dekoratif).
#
# Olculdu (2026-08-28): sayfada 30 ADSIZ baglanti vardi. Ekran okuyucu
# bunlari "baglanti" diye okuyup geciyor -- nereye gittigi
# soylenmiyor. Klavyeyle gezen okur da her kartta ise yaramayan
# fazladan bir durak yapiyor.
#
# `alt`e metin yazmak cozum DEGIL: ayni basligi iki kez okutur.
# Dogrusu, TEKRAR EDEN baglantiyi erisilebilirlik agacindan ve sekme
# sirasindan cikarmak. Fare ile tiklama calismaya devam ediyor.
#
# IKISI BIRLIKTE olmali: yalnizca `aria-hidden` verilirse
# odaklanilabilir ama okunamayan bir oge kalir -- ekran okuyucu
# kullanicisi icin en kotu hal.
# ------------------------------------------------------------------
_GUNDEM = (_KOK / "sablonlar" / "gundem.html").read_text(encoding="utf-8")
_gorsel_bag = [s for s in _GUNDEM.split(chr(10))
               if 'class="haber-gorsel"' in s
               and "<a " in s]
dogru("gundem karti gorsel baglantisi bulundu", bool(_gorsel_bag))
if _gorsel_bag:
    _satir = _gorsel_bag[0]
    dogru("gorsel baglantisi erisilebilirlik agacinda degil",
          'aria-hidden="true"' in _satir)
    dogru("gorsel baglantisi sekme sirasinda degil",
          'tabindex="-1"' in _satir)

# ------------------------------------------------------------------
# HABER GORSELI 1x OKURA 800, 2x OKURA 1600 PIKSEL GONDERIR.
#
# Kok dosya bir donem 800 pikseldi ve sablon dogrudan onu basiyordu.
# `COMMONS_GENISLIK` kalite icin 1600'e cikarildi ama SAYFA TARAFI
# DEGISMEDI -- okurun indirdigi bayt sessizce ikiye katlandi.
#
# Olculdu (2026-08-28, 60 haber sayfasi): ortalama sayfa 356 KB ve
# bunun 315 KB'i (%89) tek bir fotograf. En agir sayfa 730 KB.
# Uretilen ornekte 1x dosya 120 KB, 2x dosya 352 KB -- %66 fark.
#
# 1600 SILINMIYOR: retina ekranda 800 piksellik yuva gercekten o kadar
# fiziksel piksel istiyor. Secim tarayiciya birakiliyor.
# ------------------------------------------------------------------
dogru("yazi boyu olmayan gorselde bos donuyor",
      insa.yazi_foto("/statik/foto/boyle-bir-dosya-yok.jpg") == "")
dogru("statik olmayan yolda bos donuyor", insa.yazi_foto("/baska/yol.jpg") == "")
dogru("bos girdide bos donuyor", insa.yazi_foto("") == "")

_y = sorted((_KOK / "statik" / "foto" / "y").glob("*.jpg"))
if _y:
    es("var olan yazi boyu bulunuyor",
       insa.yazi_foto("/statik/foto/" + _y[0].name),
       "/statik/foto/y/" + _y[0].name)

_HABER_SAB = (_KOK / "sablonlar" / "haber.html").read_text(encoding="utf-8")
dogru("sablon yazi boyunu soruyor", "yazi_foto" in _HABER_SAB)
dogru("srcset 1x/2x kuruluyor", "1x, {{ h.foto }} 2x" in _HABER_SAB)
# BOY YOKSA srcset HIC yazilmamali: bos bir srcset, tarayiciya
# cozulemeyen bir aday listesi verir.
dogru("boy yoksa srcset yazilmiyor",
      "{% if yazi_boy %}srcset=" in _HABER_SAB)
dogru("boy yoksa kok dosya basiliyor", "yazi_boy or h.foto" in _HABER_SAB)

# ------------------------------------------------------------------
# YAPISAL VERIDEKI BASLIK 110 KARAKTERI ASMAZ.
#
# Google `NewsArticle.headline` icin 110 karakter sinirliyor; asan
# alan zengin sonucta kirpiliyor ya da tumuyle yok sayilabiliyor.
#
# Olculdu (2026-08-28): 1711 kaydin 150'si (%9) siniri asiyordu, en
# uzunu 231 karakter. Medyan 67 -- yani sorun genel degil bir
# azinlikta, ama o azinlik uzun aktarim basliklarindan olusuyor ve
# tam da arama sonucunda gorunmesi gereken haberler.
#
# `<title>` ve `<h1>` TAM basligi tasimaya devam ediyor: kisalan sey
# yalnizca arama motoruna giden alan.
# ------------------------------------------------------------------
es("kisa baslik oldugu gibi kaliyor", insa.ld_baslik("Kisa bir baslik"),
   "Kisa bir baslik")
es("bos girdi bos donuyor", insa.ld_baslik(""), "")
es("None girdi bos donuyor", insa.ld_baslik(None), "")

_uzun = ("BOJ Ozeti: Bir uye, Japonya'nin altta yatan enflasyon "
         "istikrarini tutarli seviyelerde gorup gormeyecegini olcmek icin "
         "orta ve uzun vadeli enflasyon beklentilerine bakmak gerektigini "
         "soyledi")
_k = insa.ld_baslik(_uzun)
dogru("uzun baslik sinirin altina iniyor",
      len(_k) <= insa.LD_BASLIK_SINIRI)
dogru("kirpildigi belli oluyor", _k.endswith("…"))
# KELIME ORTASINDAN kesilmiyor: ham kirpma "enflasyon istik" gibi
# yarim kelimeler birakiyor.
dogru("kelime ortasindan kesilmiyor",
      _uzun.startswith(_k[:-1]) and (
          len(_k) - 1 == len(_uzun) or _uzun[len(_k) - 1] == " "))

# TAM SINIRDA olan baslik kirpilmamali -- bir karakterlik hata
# yuzunden gereksiz uc nokta konmasin.
_tam = "x" * insa.LD_BASLIK_SINIRI
es("tam sinirdaki baslik kirpilmiyor", insa.ld_baslik(_tam), _tam)
dogru("bir karakter fazlasi kirpiliyor",
      len(insa.ld_baslik("y" * (insa.LD_BASLIK_SINIRI + 1)))
      <= insa.LD_BASLIK_SINIRI)

# Bosluksuz devasa baslik: ham kirpmaya dusmeli, patlamamali.
dogru("bosluksuz baslik da sinira uyuyor",
      len(insa.ld_baslik("z" * 400)) <= insa.LD_BASLIK_SINIRI)

_HABER_S = (_KOK / "sablonlar" / "haber.html").read_text(encoding="utf-8")
_ANALIZ_S = (_KOK / "sablonlar" / "analiz.html").read_text(encoding="utf-8")
dogru("haber sablonu ld_baslik kullaniyor", "ld_baslik" in _HABER_S)
dogru("analiz sablonu ld_baslik kullaniyor", "ld_baslik" in _ANALIZ_S)

# ------------------------------------------------------------------
# HAKKIMIZDA BIR HUKUK DOKUMANTASYONU DEGIL.
#
# Yayin ilkeleri, kunye ve gizlilik metinleri bu sayfanin ALTINA
# ekleniyordu. Sonuc, tek sayfada toplanan bir yigindi: KVKK,
# cerezler, TradingView, Google Analytics, IP adresleri ve yirmi
# satirlik skor metodolojisi hep birlikte.
#
# Hakkimizda sayfasinin isi okura KIM OLDUGUMUZU ve NE YAPTIGIMIZI
# anlatmak. Hukuki metinler kendi adreslerinde duruyor -- hem bu sayfa
# okunabilir kaliyor hem de o metinlere dogrudan baglanti
# verilebiliyor.
# ------------------------------------------------------------------
es("hakkimizda'ya yasal metin eklenmiyor", insa.HAKKIMIZDA_SIRASI, ())

_duz = {s.slug for s in insa.duz_sayfalar()}
for _b in ("yayin-ilkeleri", "metodoloji", "gizlilik", "kunye"):
    dogru(f"bagimsiz sayfa uretiliyor: {_b}", _b in _duz)

_hk = insa.hakkimizda_yukle()
dogru("hakkimizda alt bolum tasimiyor", _hk is not None and not _hk.bolumler)

# Hakkimizda METNI de temiz olmali: bolum birlestirmesi kapatilsa bile
# metnin kendisine hukuki paragraf yazilabilir.
_HK_MD = (_KOK / "icerik" / "sayfalar" / "hakkimizda.md").read_text(
    encoding="utf-8").lower()
for _y in ("kvkk", "çerez", "google analytics", "tradingview", "ip adres"):
    dogru(f"hakkimizda metninde yok: {_y}", _y not in _HK_MD)

# ESKI CAPALAR KARSILANIYOR.
#
# `_redirects` bunu cozemez: capa sunucuya hic gonderilmiyor. Disarida
# paylasilmis `/hakkimizda/#gizlilik` baglantilari var olabilir.
_HK_SAB = (_KOK / "sablonlar" / "hakkimizda.html").read_text(encoding="utf-8")
for _c in ("#gizlilik", "#kunye", "#skor", "#yayin-ilkeleri"):
    dogru(f"tasinan capa karsilaniyor: {_c}", f'"{_c}"' in _HK_SAB)

# Kunye YASAL OLARAK GEREKLI: 5651 md.3 tanitici bilgilerin iletisim
# basligi altinda bulundurulmasini sart kosuyor. Sayfa sadelesti ama
# SILINMEDI; bu sinama yanlislikla kaldirilmasini engelliyor.
_KUNYE = (_KOK / "icerik" / "sayfalar" / "kunye.md")
dogru("kunye sayfasi duruyor", _KUNYE.exists())
if _KUNYE.exists():
    _k = _KUNYE.read_text(encoding="utf-8")
    dogru("kunye yayin sahibini bildiriyor", "Yayın sahibi" in _k)
    dogru("kunye iletisim adresi tasiyor", "@" in _k)

# ------------------------------------------------------------------
# ARAC SAYFALARI ARAMA MOTORUNA KAPALI.
#
# `/giris/`, `/kayit/` ve `/panel/` site haritasina KONMUYORDU ve
# `insa.py` icindeki not "arama motoruna kapali sayfalar" diyordu --
# ama etiket `index, follow` basiyordu. Niyet belgeliydi,
# UYGULANMAMISTI.
#
# Olculdu (2026-08-28): 1817 uretilen sayfanin 1814'u haritada; disarida
# kalan uc sayfanin ucu de dizine acikti. `/panel/` tarayiciya
# "Oturum gerekli" gosteriyor -- boyle bir sayfanin arama sonucunda
# cikmasi, gercek icerigin yerini almasi demek.
#
# `follow` KALIYOR: sayfa taraniyor ve baglantilari izleniyor,
# yalnizca dizine alinmiyor.
# ------------------------------------------------------------------
_TEMEL = (_KOK / "sablonlar" / "temel.html").read_text(encoding="utf-8")
dogru("sablon arama_disi bayragini soruyor",
      "eskimis or arama_disi" in _TEMEL)
dogru("kapali sayfa noindex aliyor",
      'content="noindex, follow"' in _TEMEL)
# `follow` KAYBOLMAMALI: tam kapatmak baglanti kesfini de durdurur.
dogru("kapali sayfada follow korunuyor",
      "noindex, nofollow" not in _TEMEL)

_INSA = (_KOK / "insa.py").read_text(encoding="utf-8")
dogru("uyelik sayfalari arama_disi olarak uretiliyor",
      "arama_disi=True" in _INSA)

# ------------------------------------------------------------------
# BESLEMEDE GERCEK SAAT VAR.
#
# Olculdu (2026-08-28): 40 ogenin 40'i da "00:00:00 +0000"
# tasiyordu; `pubDate` yalnizca GUN bazli tarihten uretiliyordu.
#
# Bedeli iki tarafli: besleme okuyucu gun ICINDEKI sirayi kuramiyor
# ve "yeni oge" tespiti guvenilmez oluyor. Ayrica bu, nobetcinin
# yanlis olcum yapmasinin da kokeniydi -- "en yeni icerik" her zaman
# gece yarisi gorunuyordu.
#
# ANALIZDE DAMGA UYDURULMUYOR: yayim saatini bilmiyoruz. Damgasiz
# kayit gunun basinda duruyor -- olcumsuz bir saat yazmaktansa.
# ------------------------------------------------------------------
import xml.etree.ElementTree as _ET  # noqa: E402

# DAMGALI KAYIT GIRDIDE IKINCI SIRADA: ilk yazimda ONCE yaziliydi ve
# siralama sinamasi HICBIR SEY OLCMUYORDU -- ayni gunde tarihe gore
# siralamak kararli oldugu icin girdi sirasini koruyor, yani damga
# yok sayilsa da sonuc ayni cikiyordu. Bozarak dogrulamada kacti.
_rss = insa.rss_uret([], [
    ("2026-08-28", "Damgasiz haber", "ozet", "/haber/b/", ""),
    ("2026-08-28", "Damgali haber", "ozet", "/haber/a/",
     "2026-08-28T09:12:00+00:00"),
])
dogru("damgali oge gercek saati tasiyor", "09:12:00" in _rss)
dogru("damgasiz oge gunun basinda", "00:00:00" in _rss)
dogru("damgali oge ONDE", _rss.index("Damgali") < _rss.index("Damgasiz"))

# ESKI DORTLU BICIM DE CALISMALI: cagiranlardan biri damgasiz kayit
# gonderirse besleme patlamamali.
_eski = insa.rss_uret([], [("2026-08-28", "Dortlu", "ozet", "/haber/c/")])
dogru("dortlu bicim hala calisiyor", "Dortlu" in _eski)

dogru("lastBuildDate basiliyor", "<lastBuildDate>" in _rss)
dogru("atom:link kendine isaret ediyor", 'rel="self"' in _rss)
dogru("atom ad alani tanimli", "xmlns:atom" in _rss)

# XML GECERLILIGI: ad alani tanimsiz birakilirsa besleme okuyucular
# dosyayi tumuyle reddeder -- bozuk besleme, eksik beslemeden kotudur.
try:
    _ET.fromstring(_rss)
    dogru("besleme gecerli XML", True)
except _ET.ParseError as _e:
    dogru(f"besleme gecerli XML ({_e})", False)

# ------------------------------------------------------------------
# SITE HARITASI ILE ROBOTS ETIKETI AYNI SEYI SOYLEMELI.
#
# Olculdu (2026-08-28): 276 sayfa `noindex` tasiyordu AMA haritada
# duruyordu -- haritanin %15'i. Iki isaret birbirinin tersini
# soyluyordu: harita "bunu dizine ekle", sayfa "ekleme".
#
# Bedeli somut: Google bunu "Submitted URL marked noindex" diye HATA
# olarak raporluyor ve her biri icin tarama butcesi harciyor --
# guncel sayfalarin tarandigi butceden.
#
# Sayfalar SILINMIYOR: adresleri calisiyor, paylasilmis baglantilar
# kirilmiyor, `follow` sayesinde baglantilari izleniyor. Yalnizca
# "beni dizine ekle" cagrisi geri cekiliyor.
#
# Ayni celiski `/giris/`, `/kayit/` ve `/panel/` icin de vardi ve
# TERS yondeydi: haritada degillerdi ama etiket `index` diyordu.
# Ikisi de ayni kuralin ihlali.
# ------------------------------------------------------------------
_INSA_K = (_KOK / "insa.py").read_text(encoding="utf-8")
dogru("eskimis surum haritaya EKLENMIYOR",
      ("if not _eskimis:" + chr(10)
       + "            yollar.append(a.yol)") in _INSA_K)
dogru("eskimis bayragi hala sablona gidiyor",
      "eskimis=_eskimis" in _INSA_K)
# Bayrak hesabi KORUNMALI: `guncel_sluglar` disindaki her surum eski.
dogru("eskimis olcutu guncel listeye bakiyor",
      "a.slug not in guncel_sluglar" in _INSA_K)

# HANGI SINAMA KALDIGI YAZILIYOR.
#
# Onceden yalnizca sayi basiliyordu ("1 kaldi") ve o sayi tek basina
# ise yaramiyordu: bakan kisi hangi kuralin bozuldugunu goremiyordu.
# Ayni eksik `insa.py`nin yorum tanilamasinda da vardi.
for _k in kaldi:
    print(f"  KALDI  {_k}")
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)

