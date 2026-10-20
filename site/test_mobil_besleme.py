# -*- coding: utf-8 -*-
"""MOBIL BESLEMESI YENI BIR YAYIN YUZEYIDIR -- KURALLAR ONDA DA GECERLI.

BU DOSYA NEDEN VAR
------------------
`/v1/*.json` beslemesi siteyle AYNI icerigi yayimliyor ama mevcut
denetimlerin cogu HTML CIKTISINA bakiyor. Yani JSON, korumalarin
gormedigi yeni bir kapi.

Bu depoda tam bu sinif iki kez yasandi:

* Suzgec uretimde sikiydi, YAYINDA gevsekti -- kurali sikilastirmak
  depodaki eski icerigi temizlemedi.
* Korumalarin 43'u ciktiya bakiyordu ama sinamalar URETIMDEN ONCE
  kosuyordu; hepsi bos donuyordu.

Bu yuzden besleme kurallari modulun ICINDE, veri kurulurken
uygulaniyor ve burada MUTASYONLA sinaniyor: kurali bozup sinamanin
kirmiziya dondugu goruluyor.

AG KULLANILMIYOR. DISKE YAZILMIYOR.
"""

from __future__ import annotations

import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK)]

import mobil_besleme as M                           # noqa: E402

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


def _haber(**ek) -> dict:
    """Kurala UYAN bir haber; sinamalar tek alani bozarak kullaniyor."""
    temel = {
        "yol": "/haber/ornek-haber/",
        "baslik": "Örnek haber",
        "ozet": "Kaynağın kendi özeti.",
        "neden_onemli": "Neden önemli olduğu.",
        "konu": "Enflasyon",
        "kurum": "Reuters",
        "kurum_tam": "Thomson Reuters",
        "ticari": True,
        "adres": "https://example.org/x",
        "tarih": "2026-10-18",
        "foto": "/statik/foto/x.jpg",
        "foto_atif": "Fotoğrafçı · CC BY 4.0",
    }
    temel.update(ek)
    return temel


class _Analiz:
    """`Analiz` nesnesini taklit eden en kucuk kabuk.

    Gercek sinifi ice almak `insa.py`yi ice almak demek; o modul
    uretim yolunu kuruyor ve bir sinamanin ona dokunmamasi gerekiyor.
    """

    def __init__(self, **alanlar):
        varsayilan = {
            "slug": "ornek-analiz", "baslik": "Örnek analiz",
            "ozet": "Özet.", "sirket": "Örnek A.Ş.", "kod": "ORNEK",
            "sektor": "Sanayi", "donem": "2026 2. çeyrek",
            "kategori": "Bilanço", "tarih": "2026-10-17",
            "skor": "72", "okuma_dk": 4, "yazar": "", "unvan": "",
            "kurgusal": False, "amblem_yol": "/statik/amblem/x.svg",
            "foto": "", "foto_atif": "", "govde": "<p>Gövde.</p>",
            "kapsam": "tam", "veri_kaynagi": "KAP",
            "kaynaklar": ("KAP",), "kriterler": [], "bolumler": (),
            "sayimlar": (), "kelime": 800,
        }
        varsayilan.update(alanlar)
        for k, v in varsayilan.items():
            setattr(self, k, v)

    @property
    def yol(self) -> str:
        return f"/analiz/{self.slug}/"


print("")
print("1. ISO OLMAYAN TARIH TASINMIYOR")
# `arama.json` tarihi GORUNTU biciminde tasiyor ("14 Ekim 2026"). O
# degeri bir `tarih` alanina koymak istemcide sessizce yanlis siralama
# demek: hicbir hata gorunmez, yalnizca haberler karisik siraya girer.
esit(M._iso("2026-10-18"), "2026-10-18", "ISO tarih geçiyor")
esit(M._iso("18 Ekim 2026"), "", "GÖRÜNTÜ biçimli tarih ELENİYOR")
esit(M._iso("2026-10-18T14:05:08Z"), "", "damga ISO tarih değil")
esit(M._iso("18.10.2026"), "", "nokta biçimi eleniyor")
esit(M._iso(None), "", "None boş")
esit(M._iso(""), "", "boş boş")
esit(M._iso("2026-13-45"), "2026-13-45",
     "bicim dogru ama gun gecersiz -- BICIM denetlenir, takvim degil")
k = M.haber_ozeti(_haber(tarih="18 Ekim 2026"))
esit(k["tarih"], "", "haber kaydinda da eleniyor")

print("")
print("2. ATIFSIZ FOTOGRAF BESLEMEYE GIRMIYOR")
# CC BY atfi zorunlu; `_lisans_denetimi` bunu HTML icin "hata"
# seviyesinde tutuyor. JSON ayni cizgide olmali, yoksa atifsiz gorsel
# mobil uygulamada yayimlanir.
k = M.haber_ozeti(_haber(foto_atif=""))
esit(k["foto"], "", "atıf yoksa FOTOĞRAF da düşüyor")
esit(k["foto_atif"], "", "atıf alanı boş")
esit(k["baslik"], "Örnek haber", "haberin KENDISI düşmüyor")
k = M.haber_ozeti(_haber(foto_atif="   "))
esit(k["foto"], "", "yalnızca boşluktan oluşan atıf da geçersiz")
k = M.haber_ozeti(_haber())
esit(k["foto"], "/statik/foto/x.jpg", "atıf varsa fotoğraf GEÇİYOR")

print("")
print("3. TICARI KAYNAK ATIFSIZ TASINMIYOR")
# Kisa iktibas hakkinin sarti kaynak gostermek. Ticari bir kaynagin
# metnini kurum ya da baglanti olmadan tasimak o sarti bozar.
esit(M.haber_ozeti(_haber(adres="")), None, "ticari + adres yok -> KAYIT YOK")
esit(M.haber_ozeti(_haber(kurum="")), None, "ticari + kurum yok -> KAYIT YOK")
# TICARI OLMAYAN kaynak ICIN AYNI KATILIK UYGULANMIYOR: resmi
# kurumlarin (TCMB, Fed, EIA) kendi yayinina baglanti her zaman
# olmayabiliyor ve o metin iktibas degil.
k = M.haber_ozeti(_haber(ticari=False, adres="", kurum="TCMB"))
esit(k is not None, True, "ticari DEĞİLSE adres zorunlu değil")
esit(k["ticari"], False, "bayrak doğru taşınıyor")
k = M.haber_ozeti(_haber())
esit(k["kaynak_adres"], "https://example.org/x", "ticari kaynağın adresi var")
esit(k["kurum_tam"], "Thomson Reuters", "tam kurum adı taşınıyor")

print("")
print("4. SAYFASI OLMAYAN KAYIT GIRMIYOR")
# Tiklanamaz bir satir olurdu; `arama_dizini` ayni kurali uyguluyor.
esit(M.haber_ozeti(_haber(yol="")), None, "yol yok -> kayıt yok")
esit(M.analiz_ozeti(_Analiz(slug="")), None, "analizde de aynı")

print("")
print("5. KURGUSAL BAYRAGI ISTEMCIYE ULASIYOR")
# Isaret ulasmazsa kurgusal icerik gercek gibi gorunur.
esit(M.analiz_ozeti(_Analiz(kurgusal=True))["kurgusal"], True,
     "kurgusal=True taşınıyor")
esit(M.analiz_ozeti(_Analiz(kurgusal=False))["kurgusal"], False,
     "kurgusal=False taşınıyor")

print("")
print("6. BESLEME HESAP YAPMIYOR -- degerler AYNEN tasiniyor")
# Bu depoda ayni seyi iki yerde hesaplamak yayinda yanlis sayi
# uretti: negatif ozkaynakla +%128,5 ozkaynak karliligi, 15 ay
# oncesini "bir yil once" diye etiketlemek. Besleme TASIR.
esit(M.analiz_ozeti(_Analiz(skor="72"))["skor"], "72", "skor aynen")
esit(M.analiz_ozeti(_Analiz(skor=None))["skor"], None, "skor yoksa None")
esit(M.analiz_ozeti(_Analiz(skor=""))["skor"], None, "boş skor None")
_t = M.analiz_tam(_Analiz(
    kriterler=[{"ad": "Kârlılık", "puan": "18", "tam": "25"}]))
esit(_t["kriterler"], [{"ad": "Kârlılık", "puan": "18", "tam": "25"}],
     "kriter puanları aynen")
esit(_t["govde_html"], "<p>Gövde.</p>", "gövde aynen")

print("")
print("7. LISANSI BIZDE OLMAYAN SERI PIYASA BESLEMESINE GIRMIYOR")
# Tek kaynak `makro_uret_ucretsiz.LISANSSIZ_SERILER`. SP500 ve DJIA
# S&P Dow Jones Indices LLC, NASDAQCOM Nasdaq Inc., VIXCLS Cboe
# lisansi; FRED bunlari saglayicinin IZNIYLE dagitiyor ve o izin bize
# gecmiyor.
_yasak = frozenset({"SP500", "DJIA", "NASDAQCOM", "VIXCLS"})
_g = {
    "veri_tarihi": "2026-10-18",
    "kalemler": [
        {"kod": "ECB_USDTRY", "ad": "USD/TRY", "deger": "49,39",
         "fark": "+%0,05", "yon": "artis", "tarih": "2026-10-18"},
        {"kod": "SP500", "ad": "S&P 500", "deger": "6.712",
         "fark": "+%0,3", "yon": "artis", "tarih": "2026-10-17"},
        {"kod": "VIXCLS", "ad": "VIX", "deger": "14,2",
         "fark": "-%1", "yon": "azalis", "tarih": "2026-10-17"},
        {"kod": "DCOILBRENTEU", "ad": "Brent", "deger": "125,44",
         "fark": "-%0,06", "yon": "azalis", "tarih": "2026-10-16"},
    ],
}
_p = M.piyasa(_g, _yasak)
_kodlar = [k["kod"] for k in _p["kalemler"]]
esit(_kodlar, ["ECB_USDTRY", "DCOILBRENTEU"],
     "lisanssız seriler ÇIKARILDI, diğerleri kaldı")
esit(any(k in _yasak for k in _kodlar), False, "yasak kümeden hiçbiri yok")
# Kume BOS verilirse hicbir sey elenmemeli -- ama o durum bir kurulum
# hatasidir ve `test_lisans.py` onu ayrica yakaliyor.
esit(len(M.piyasa(_g, frozenset())["kalemler"]), 4,
     "küme boşsa eleme yapılmıyor (kurulum hatası ayrı yakalanıyor)")

print("")
print("8. PIYASA BESLEMESI 'CANLI' IDDIA ETMIYOR")
# Sayi tek basina canli fiyat izlenimi veriyor. Web tarafinda bu tam
# olarak yasandi: tarih yalnizca `title` ozniteligindeydi ve
# TELEFONDA KIMSE goremiyordu; kullanici "fiyat hic islemedi" dedi.
esit(_p["canli_degil"], True, "canlı olmadığı AÇIKÇA bildiriliyor")
esit(_p["veri_tarihi"], "2026-10-18", "şeridin veri tarihi var")
esit(bool(_p["aciklama"]), True, "okura dönük açıklama var")
for _k in _p["kalemler"]:
    esit(bool(_k["tarih"]), True, f"{_k['kod']} KENDI veri tarihini taşıyor")

print("")
print("8b. EKONOMIK TAKVIM")


class _Beklenti:
    """Hat `beklenti`yi NESNE olarak koyuyor, sozluk olarak degil.

    Bu depoda `.get()` cagirmak tam burada AttributeError uretti ve
    kusur COKME degil EKSIKLIK olarak gorundu: surpriz alani sessizce
    hic uretilmedi. Bu yuzden sinama NESNE kullaniyor.
    """

    def __init__(self, **a):
        v = {"kod": "CPI", "ad": "TÜFE", "son_deger": "%23,70",
             "son_tarih": "2026-09-01", "esik_deger": "%23,70",
             "esik_kaynak": "onceki", "dallar": ()}
        v.update(a)
        for k, d in v.items():
            setattr(self, k, d)


class _Dal:
    def __init__(self, yon, baslik, mekanizma, olcum=""):
        self.yon, self.baslik = yon, baslik
        self.mekanizma, self.olcum = mekanizma, olcum


def _kutu(**ek):
    t = {
        "ad": "TCMB Piyasa Katılımcıları Anketi", "ulke": "TR",
        "onem": 2, "kesin": False,
        "an": "2026-10-19T11:00:00+00:00",
        "yerel": "2026-10-19 14:00:00+03:00",
        "gun": "19.10", "saat": "14:00", "kaynak": "",
        "seri": "TP.ENFBEK.PKA12ENF",
        "beklenti": _Beklenti(dallar=(
            _Dal("ustunde", "%23,70 üzerinde gelirse",
                 "Faiz indirimi beklentisi zayıflar.", "Geçmişte…"),
            _Dal("altinda", "%23,70 altında gelirse",
                 "Faiz indirimi için alan genişler.", "Geçmişte…"),
        )),
    }
    t.update(ek)
    return t


# --- SAAT DILIMI ---
# Bir veri aciklamasinin saati, hangi dilimde oldugu yazilmadan
# anlamsiz: okur 14:00'i kendi saatinde sanip aciklamayi kacirir.
_o = M.takvim_ogesi(_kutu())
esit(_o["saat_dilimi"], "Europe/Istanbul", "saat dilimi ÖĞEDE yazılı")
esit(_o["an"], "2026-10-19T11:00:00+00:00", "UTC anı korunuyor")
esit(_o["yerel"], "2026-10-19 14:00:00+03:00", "yerel gösterim de var")
_t = M.takvim([_kutu()], "2026-10-18T16:00:00Z")
esit(_t["saat_dilimi"], "Europe/Istanbul", "saat dilimi BESLEMEDE de yazılı")
esit(bool(_t["aciklama"]), True, "okura dönük açıklama var")
# BESLEME METNINDE BICIMLENDIRME ISARETI OLMAZ.
#
# Ilk yazimda aciklama "`kesin` yanlissa..." diyordu ve uygulamada
# TERS TIRNAKLAR AYNEN gorundu -- istemci duz metin basiyor.
# Gercek tarayicida goruldu, kaynaga bakarak gorulemezdi.
for _alan, _metin in (("takvim aciklamasi", _t["aciklama"]),):
    for _isaret in ("`", "**", "<", ">"):
        esit(_isaret in _metin, False,
             f"{_alan}: '{_isaret}' işareti YOK (düz metin)")

# --- SAAT KESIN MI ---
# Bazi yayinlarin saati kurum tarafindan onaylanmamis. Bunu
# dusurmek, tahmini bir saati kesinmis gibi gostermek demek.
esit(_o["kesin"], False, "kesin=False TAŞINIYOR")
esit(M.takvim_ogesi(_kutu(kesin=True))["kesin"], True, "kesin=True taşınıyor")

# --- BEKLENTI ILE ONCEKI DEGER AYRI ---
# Esik bazen gercek piyasa konsensusu, bazen yalnizca ONCEKI deger.
# Ikisini "beklenti" diye tek alana koymak, olmayan bir konsensus
# uydurmak olurdu.
esit(_o["esik_kaynak"], "onceki", "eşik kaynağı AYNEN taşınıyor")
esit(_o["onceki_deger"], "%23,70", "önceki değer ayrı alan")
_k = M.takvim_ogesi(_kutu(
    beklenti=_Beklenti(esik_kaynak="beklenti", esik_deger="%24,10")))
esit(_k["esik_kaynak"], "beklenti", "gerçek konsensus işaretli")
esit(_k["esik_deger"], "%24,10", "eşik değeri")

# --- SURPRIZ YALNIZCA GERCEK KONSENSUS VARKEN ---
# Esik onceki degerse "beklentinin ustunde geldi" demek yanlis olur:
# ortada bir beklenti YOK, yalnizca bir onceki rakam var.
_s = {"fark": 0.4, "yon": "ustunde", "metin": "0,4"}
_g = {"deger": 24.5, "donem": "2026-10", "birim": "%"}
_y = M.takvim_ogesi(_kutu(gerceklesen=_g, surpriz=_s))
esit("surpriz" in _y, False,
     "eşik ÖNCEKİ değerse sürpriz ÜRETİLMİYOR")
esit(_y["aciklandi"], True, "açıklandı bayrağı yine doğru")
esit(_y["gerceklesen"]["deger"], 24.5, "gerçekleşen değer taşınıyor")
_y2 = M.takvim_ogesi(_kutu(
    beklenti=_Beklenti(esik_kaynak="beklenti", esik_deger="%24,10"),
    gerceklesen=_g, surpriz=_s))
esit(_y2["surpriz"]["fark"], 0.4, "gerçek konsensus varsa sürpriz ÜRETİLİYOR")

# --- ACIKLANMAMIS VERI ---
# `gerceklesen` yoksa bu bir EKSIKLIK degil, takvimin normal durumu.
esit(_o["aciklandi"], False, "henüz açıklanmadı")
esit("gerceklesen" in _o, False, "açıklanmayan veride alan YOK")

# --- KOSULLU DALLAR ---
esit(len(_o["dallar"]), 2, "iki dal da taşınıyor")
esit(_o["dallar"][0]["yon"], "ustunde", "dal yönü")
esit(bool(_o["dallar"][0]["mekanizma"]), True, "mekanizma metni var")
# MEKANIZMA ILE OLCUM AYRI ALAN: biri akil yurutme, oteki gozlem.
# Birlestirilirse olcum bir tahmin gibi okunur.
esit(bool(_o["dallar"][0]["olcum"]), True, "ölçüm ayrı alanda")
esit(M.takvim_ogesi(_kutu(beklenti=None))["dallar"], [],
     "beklenti yoksa dal listesi BOŞ (çökmüyor)")

# --- EKSIK KAYIT ELENIYOR ---
esit(M.takvim_ogesi(_kutu(ad="")), None, "adı olmayan kalem elenıyor")
esit(M.takvim_ogesi(_kutu(an="")), None, "anı olmayan kalem eleniyor")

# --- SIRALAMA: EN YAKIN ONCE ---
_sira = M.takvim([
    _kutu(ad="geç", an="2026-10-25T08:00:00+00:00"),
    _kutu(ad="erken", an="2026-10-19T08:00:00+00:00"),
    _kutu(ad="orta", an="2026-10-21T08:00:00+00:00"),
], "")
esit([o["ad"] for o in _sira["ogeler"]], ["erken", "orta", "geç"],
     "en yakın açıklama ÜSTTE")
# Bos liste cokmemeli.
esit(M.takvim(None, "")["ogeler"], [], "takvim yoksa boş liste")

print("")
print("8c. VARLIK BESLEMESI")

_V = {"kod": "FED_FAIZ", "yol": "/varlik/fed-faiz/", "ad": "Fed politika faizi",
      "tur": "gosterge", "sayi": 42}
_KUNYE = {"kod": "FED_FAIZ", "ad": "Fed politika faizi",
          "ad_en": "Fed Funds Rate", "tur": "gosterge",
          "aciklama": "ABD gecelik politika faizi.", "seri_kodu": "DFF",
          "onem": 100}
_VERI = {"deger": "%3,88", "birim": "", "degisim": "değişmedi",
         "yon": "yatay", "tarih": "2026-10-15", "gozlem": 60,
         "seri": [{"tarih": f"2026-09-{g:02d}", "deger": 3.8 + g / 100}
                  for g in range(1, 29)]}
_BAGLAR = [{"kaynak": "FED_FAIZ", "hedef": "DXY", "tur": "etkiler",
            "aciklama": "Faiz farkı sermaye akımını belirler.",
            "dayanak": "yapisal", "guc": 3,
            "kaynak_ad": "Fed politika faizi", "hedef_ad": "Dolar endeksi",
            "yon": "cift"}]
_HABERLER = [{"baslik": "Fed kararı", "yol": "/haber/fed-karari/",
              "tarih": "2026-10-17", "kurum": "Dünya"}]

_o = M.varlik_ogesi(_V, _KUNYE, _VERI, _BAGLAR, _HABERLER, lisanssiz=())
esit(_o["kod"], "FED_FAIZ", "kod taşınıyor")
esit(_o["veri_var"], True, "veri var işareti")
esit(_o["veri"]["deger"], "%3,88", "değer taşınıyor")
esit(_o["veri"]["tarih"], "2026-10-15", "VERİ TARİHİ taşınıyor")
esit(len(_o["veri"]["seri"]), 28, "gözlem serisi taşınıyor")
esit(_o["veri"]["gozlem_sayisi"], 60, "toplam gözlem sayısı ayrı")

# --- LISANS: DEGER GITMIYOR, SAYFA KALIYOR ---
#
# Olculdu (yayinda): /varlik/nasdaq/, /varlik/sp500/ ve /varlik/vix/
# sayfalari "26.180 endeks +%0,4" yaziyordu -- yani seriyi yeniden
# yayimliyorduk. Lisans bizde degil.
#
# Kisitlama VERIYE, isim anmaya degil: yapisal iliskiler BIZIM.
_lis = M.varlik_ogesi(_V, _KUNYE, _VERI, _BAGLAR, _HABERLER,
                      lisanssiz={"DFF"})
esit(_lis["veri_var"], False, "LİSANSSIZ seride veri_var FALSE")
esit("veri" in _lis, False, "LİSANSSIZ serinin DEĞERİ hiç yazılmıyor")
esit(_lis["seri_kodu"], "DFF",
     "seri KODU yine yazılı (tanım, veri değil)")
esit(len(_lis["baglar"]), 1, "yapısal bağlar KALIYOR -- onlar bizim")
esit(len(_lis["haberler"]), 1, "haber arşivi de kalıyor")
esit(_lis["aciklama"], "ABD gecelik politika faizi.", "tanım kalıyor")

# --- BAGLARDA DAYANAK AYRIMI ---
# "yapisal" (tanim geregi dogru) ile "veri" (gozlemden cikarilmis,
# degisebilir) ayni sey degil; okur ayrimi gormeli.
esit(_o["baglar"][0]["dayanak"], "yapisal", "bağın dayanağı taşınıyor")
esit(_o["baglar"][0]["guc"], 3, "bağ gücü taşınıyor")

# --- EKSIK KAYIT ELENIYOR ---
esit(M.varlik_ogesi({"kod": "", "yol": "/x/"}, None, None, None, None),
     None, "kodu olmayan varlık eleniyor")
esit(M.varlik_ogesi({"kod": "X", "yol": ""}, None, None, None, None),
     None, "yolu olmayan varlık eleniyor")
# Kunyesiz varlik COKMEMELI: depoda kunyesi olmayan kod olabilir.
_bos = M.varlik_ogesi({"kod": "X", "yol": "/varlik/x/", "ad": "X",
                       "tur": "gosterge", "sayi": 0},
                      None, None, None, None)
esit(_bos is not None, True, "künyesiz varlık çökmüyor")
esit(_bos["veri_var"], False, "künyesiz varlıkta veri yok")
esit(_bos["baglar"], [], "bağ yoksa boş liste")

# --- SAYFASI OLMAYAN HABER GIRMIYOR ---
_h = M.varlik_ogesi(_V, _KUNYE, None, None,
                    [{"baslik": "yolsuz", "yol": "", "tarih": "2026-01-01"},
                     {"baslik": "yollu", "yol": "/haber/a/",
                      "tarih": "2026-01-02"}])
esit([x["baslik"] for x in _h["haberler"]], ["yollu"],
     "yolu olmayan haber beslemeye girmiyor")

# --- DIZIN: DETAYIN TAMAMINI TASIMIYOR ---
# 75 varligin butun baglarini ve haberlerini ilk acilista indirmek
# olurdu.
_d = M.varlik_dosyalari([_o, _bos], "2026-10-19T00:00:00Z")
esit("/v1/varlik.json" in _d, True, "dizin dosyası")
esit("/v1/varlik/fed_faiz.json" in _d, True, "detay dosyası (küçük harf)")
_dz = _d["/v1/varlik.json"]
esit(_dz["toplam"], 2, "dizin toplamı")
esit("baglar" in _dz["ogeler"][0], False, "DİZİNDE bağlar YOK")
esit("haberler" in _dz["ogeler"][0], False, "DİZİNDE haberler YOK")
esit(_dz["ogeler"][0]["kod"], "FED_FAIZ",
     "dizin haber sayısına göre sıralı (42 > 0)")
esit(_dz["ogeler"][0]["dosya"], "/v1/varlik/fed_faiz.json",
     "dizin detay dosyasını gösteriyor")
# LISANSSIZ VARLIK DIZINDE DE DEGERSIZ.
_dl = M.varlik_dosyalari([_lis], "")["/v1/varlik.json"]
esit(_dl["ogeler"][0]["deger"], "", "lisanssız varlık DİZİNDE de değersiz")
esit(_dl["ogeler"][0]["veri_var"], False, "dizinde de işaretli")
esit(M.varlik_dosyalari(None, "")["/v1/varlik.json"]["toplam"], 0,
     "varlık yoksa boş dizin (çökmüyor)")

# --- BIRIM DIZINDE DE OLMALI -- SAYI TEK BASINA ANLAMSIZ ---
#
# Olculdu (2026-10-21): dizinde "Tarım Dışı İstihdam 29,00" goruluyordu
# ve birim ("bin kişi") yalnizca DETAY dosyasindaydi. Sitenin kendi
# varlik sayfasi onu basiyor ("126,55 USD/varil", "4.053 mn $") -- yani
# ayni sayi iki yuzeyde iki anlam tasiyordu.
#
# Bos birim DOGRU bir deger: oran serilerinde deger zaten "%3,88"
# biciminde geliyor. Sinanan sey alanin VARLIGI ve birim doluyken
# TASINMASI.
_bo = M.varlik_ogesi(
    {"kod": "NFP", "yol": "/varlik/nfp/", "ad": "Tarım Dışı İstihdam",
     "tur": "gosterge", "sayi": 3},
    _KUNYE,
    {"deger": "29,00", "birim": "bin kişi", "degisim": "+1,00",
     "yon": "artis", "tarih": "2026-09-01", "gozlem": 27,
     "seri": [{"tarih": "2026-09-01", "deger": 29.0}]},
    None, None, lisanssiz=())
_bd = M.varlik_dosyalari([_bo], "")["/v1/varlik.json"]["ogeler"][0]
# `.get` KULLANILIYOR: alan tamamen silinirse `_bd["birim"]` ciplak
# bir KeyError firlatir ve neyin eksik oldugu yigin izinde kalir.
# `.get` ile dusus OKUNUR oluyor -- beklenen "bin kişi", gelen None.
esit(_bd.get("birim"), "bin kişi", "DİZİNDE birim taşınıyor")
esit(_bd["deger"], "29,00", "değer birimden ayrı duruyor")
# Oran serisinde birim BOS ama alan DURUYOR: istemci "alan yok" ile
# "birim yok" arasinda ayrim yapmak zorunda kalmasin.
esit(_dz["ogeler"][0].get("birim"), "", "oran serisinde birim boş ama ALAN var")

print("")
print("8d. ARAMA DIZINI")

_KATLAMA = {"ı": "i", "İ": "i", "ş": "s", "ğ": "g", "ü": "u",
            "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
_ad = M.arama_dizini(
    [{"baslik": "Fed kararı", "slug": "fed-karari", "tarih": "2026-10-18",
      "konu": "Para politikası"}],
    [{"baslik": "THY bilançosu", "slug": "thyao-2026-2", "tarih": "2026-10-17",
      "kategori": "Bilanço", "kod": "THYAO"}],
    [{"ad": "Brent petrol", "kod": "BRENT", "tur": "emtia"}],
    _KATLAMA, "2026-10-19T00:00:00Z")
esit(_ad["toplam"], 3, "üç tür de dizine giriyor")
esit([k["t"] for k in _ad["kayitlar"]], ["haber", "analiz", "varlik"],
     "tür alanı doğru")
esit(_ad["kayitlar"][1]["c"], "THYAO",
     "şirket KODU aranabilir (okur 'THYAO' yazar)")
esit(_ad["kayitlar"][0]["d"], "2026-10-18", "ISO tarih taşınıyor")

# --- KATLAMA TABLOSU TASINIYOR ---
# Turkce diakritik katlamasi sitede IKI yerde duruyor ve bir sinama
# ikisinin ayni oldugunu dogruluyor. Uygulamaya UCUNCU bir kopya
# yazmak o riski bir kat daha buyutmek olurdu -- ve ayrisma hicbir
# hata uretmez, yalnizca "hurmuz" yazan okur "Hürmüz"u bulamaz.
esit(_ad["katlama"], _KATLAMA, "katlama tablosu AYNEN taşınıyor")
esit(M.arama_dizini([], [], [], None, "")["katlama"], {},
     "tablo verilmezse boş (uygulama yedeğine düşer)")

# --- DIZIN OZET TASIMIYOR ---
# Ozet YOK: okur sonuca dokununca detay dosyasi zaten geliyor.
# Ozeti tasimak dizini iki katina cikarirdi.
esit("o" in _ad["kayitlar"][0], False, "özet dizine GİRMİYOR")
esit("ozet" in _ad["kayitlar"][0], False, "uzun ad da yok")

# --- ARANAMAZ KAYIT GIRMIYOR ---
_bos = M.arama_dizini(
    [{"baslik": "", "slug": "x", "tarih": "2026-01-01"},
     {"baslik": "var", "slug": "", "tarih": "2026-01-01"},
     {"baslik": "iyi", "slug": "iyi", "tarih": "2026-01-01"}],
    [], [], _KATLAMA, "")
esit(_bos["toplam"], 1, "başlıksız ve slug'sız kayıt ELENİYOR")
esit(_bos["kayitlar"][0]["b"], "iyi", "geçen kayıt doğru")

print("")
print("9. SAYFALAMA")
_kayit = [{"slug": f"k{i}", "tarih": "2026-10-18"} for i in range(50)]
_s = M.sayfala(_kayit, 24)
esit([len(g) for g in _s], [24, 24, 2], "50 kayıt 24'lük sayfalara")
esit(M.sayfala([], 24), [[]],
     "BOŞ liste bile BİR sayfa üretiyor (404 ile 'içerik yok' ayrı şey)")
esit([len(g) for g in M.sayfala(_kayit[:48], 24)], [24, 24],
     "tam katta fazladan boş sayfa YOK")
_d = M._liste_dosyalari("/v1/haber", _kayit, 24)
esit(sorted(_d), ["/v1/haber/sayfa-1.json", "/v1/haber/sayfa-2.json",
                  "/v1/haber/sayfa-3.json"], "sayfa dosyaları")
esit(_d["/v1/haber/sayfa-1.json"]["sonraki"], "/v1/haber/sayfa-2.json",
     "ileri bağlantı")
esit(_d["/v1/haber/sayfa-3.json"]["sonraki"], None, "son sayfada ileri yok")
esit(_d["/v1/haber/sayfa-2.json"]["toplam_kayit"], 50, "toplam kayıt sayısı")

print("")
print("10. SIRALAMA: EN YENI USTTE, TARIHSIZ SONA")
# Tarihi bos olani basa koymak, olculmemis bir tazeligi olculmus gibi
# sunmak olurdu.
_sirali = M._tarihe_gore([
    {"slug": "eski", "tarih": "2026-01-01"},
    {"slug": "mechul", "tarih": ""},
    {"slug": "yeni", "tarih": "2026-10-18"},
    {"slug": "orta", "tarih": "2026-06-15"},
])
esit([k["slug"] for k in _sirali], ["yeni", "orta", "eski", "mechul"],
     "yeniden eskiye, tarihsiz SONA")

print("")
print("11. uret() BUTUN DOSYALARI KURUYOR, DISKE DOKUNMUYOR")
_cikti = M.uret(
    analizler=[_Analiz(slug="a1"), _Analiz(slug="a2", tarih="2026-10-18")],
    haberler=[_haber(yol="/haber/h1/"), _haber(yol="/haber/h2/")],
    gostergeler=_g, lisanssiz=_yasak, uretildi="2026-10-18T15:00:00Z")
for _zorunlu in ("/v1/surum.json", "/v1/piyasa.json", "/v1/one-cikan.json",
                 "/v1/haber/sayfa-1.json", "/v1/analiz/sayfa-1.json",
                 "/v1/haber/h1.json", "/v1/analiz/a1.json"):
    esit(_zorunlu in _cikti, True, f"{_zorunlu} üretildi")
esit(_cikti["/v1/surum.json"]["surum"], M.SURUM, "sürüm bildiriliyor")
esit(_cikti["/v1/surum.json"]["beslemeler"]["haber"]["kayit"], 2,
     "haber sayısı sürüm dosyasında")
# TEL AKISI KOPYALANMIYOR -- adresi bildiriliyor.
_tel = _cikti["/v1/surum.json"]["beslemeler"]["tel"]
esit(_tel["statik"], False, "canlı tel akışı statik DEĞİL")
esit(_tel["uc"], "/api/tel", "tel ucu bildiriliyor (kopyalanmıyor)")
# Tum cikti JSON'a cevrilebilmeli: cevrilemeyen bir nesne insayi
# patlatirdi.
esit(isinstance(json.dumps(_cikti, ensure_ascii=False), str), True,
     "tüm çıktı JSON'a çevrilebiliyor")

print("")
print("12. ONE CIKAN SECIMI BESLEMEDE YENIDEN YAPILMIYOR")
# Iki yerin ayri secim yapmasi, uygulamanin siteden FARKLI bir "günün
# önemli gelişmesi" gostermesi demek olurdu.
_oc = M.uret(analizler=[], haberler=[_haber(yol="/haber/h1/"),
                                     _haber(yol="/haber/h2/")],
             gostergeler=None, lisanssiz=_yasak,
             one_cikan=[_haber(yol="/haber/secilen/")])
esit([h["slug"] for h in _oc["/v1/one-cikan.json"]["haberler"]], ["secilen"],
     "sitenin seçimi taşınıyor")
esit(_oc["/v1/one-cikan.json"]["kaynak"], "site", "kaynak işaretli")
_oc2 = M.uret(analizler=[], haberler=[_haber(yol="/haber/h1/")],
              gostergeler=None, lisanssiz=_yasak)
esit(_oc2["/v1/one-cikan.json"]["kaynak"], "en-yeni",
     "seçim verilmezse en yeniler ve bu İŞARETLİ")

print("")
print("13. GERCEK VERI: gundem.json uzerinde butun kurallar")
#
# `yol` ALANI BURADA EKLENIYOR -- gundem.json onu TASIMIYOR.
# `insa.py` her haber icin `h["yol"] = haber_yolu(h)` atiyor, yani yol
# INSA ANINDA kuruluyor. Bu bolum atif ve tarih kurallarini GERCEK
# alan degerleri uzerinde sinamak icin var; yolu kendisi veriyor.
#
# ILK YAZIMDA BU BOLUM ATILDI: `yol` olmadigi icin 120 haberden 0
# kayit uretildi, `if _kayitlar:` yanlis dondu ve bolumun TAMAMI
# sessizce atlandi -- sinama YESIL yaziyordu. Bu depoda ayni sinif
# daha once yasandi (`test_araci_kurum.py` kapinin arkasinda kalmisti).
# Bu yuzden artik SIFIR KAYIT BIR BASARISIZLIKTIR.
_gundem = _KOK / "icerik" / "gundem.json"
if _gundem.is_file():
    _d = json.loads(_gundem.read_text(encoding="utf-8"))
    _hs = _d.get("haberler") or []
    for _i, _h in enumerate(_hs):
        _h.setdefault("yol", f"/haber/gercek-{_i}/")
    _kayitlar = [k for k in (M.haber_ozeti(h) for h in _hs) if k]
    print(f"  {len(_hs)} haber okundu, {len(_kayitlar)} kayit uretildi")
    if _hs and not _kayitlar:
        print("  DUSTU  gercek veriden HIC kayit uretilmedi -- bu bolum")
        print("         atil kalirdi; girdi var, cikti yok.")
        raise SystemExit(1)
    if _kayitlar:
        _bos_tarih = [k["slug"] for k in _kayitlar if not k["tarih"]]
        esit(_bos_tarih, [], "GERÇEK veride ISO olmayan tarih yok")
        _atifsiz = [k["slug"] for k in _kayitlar
                    if k["foto"] and not k["foto_atif"]]
        esit(_atifsiz, [], "GERÇEK veride atıfsız fotoğraf yok")
        _ticari_atifsiz = [k["slug"] for k in _kayitlar
                           if k["ticari"] and not (k["kurum"]
                                                   and k["kaynak_adres"])]
        esit(_ticari_atifsiz, [], "GERÇEK veride atıfsız ticari kayıt yok")
        # ELENEN KAYIT SAYISI OLCULUYOR: kurallar sessizce icerigin
        # yarisini yemiyor olmali.
        _oran = len(_kayitlar) / len(_hs)
        if _oran < 0.9:
            print(f"  DUSTU  kurallar iceriğin %{100 - _oran * 100:.0f}'ini "
                  f"eliyor -- fazla")
            raise SystemExit(1)
        _gecti += 1
        print(f"  gecti  eleme orani makul (%{100 - _oran * 100:.1f})")
else:
    print("  ATLANDI  gundem.json yok")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
