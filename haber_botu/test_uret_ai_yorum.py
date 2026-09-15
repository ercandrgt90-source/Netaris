"""uret_ai_yorum.girdi_kur testleri -- AGA CIKMAZ, MODEL CAGIRMAZ.

Girdi neyi tasirsa model onu anlatiyor. Buradaki durum uretimde
gorulen gercek bir hatanin dondurulmus halidir.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "ai"), str(_KOK / "analiz"),
                str(_KOK / "kaynak")]

import uret_ai_yorum as U  # noqa: E402
import yorumcu  # noqa: E402

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


class SahteDosya:
    """Dosyanin girdi_kur'un okudugu alanlari."""

    def __init__(self, acilis="", bulgular=(), turkiye=()):
        self.acilis = acilis
        self.bulgular = list(bulgular)
        self.turkiye = list(turkiye)
        self.duyarlilik = [("Enerji", 1, 1), ("Havayolu", 1, 1)]
        self.izlenecekler = ["Brent", "Hürmüz Boğazı"]

    # SAHTE, GERCEGINI YANSITMALI.
    # Gercek `Dosya` bu ikisini ozellik olarak hesapliyor; sahte
    # yalnizca alanlari tasisaydi, kural degistiginde test eski
    # davranisi dogrulamaya devam ederdi.
    @property
    def dolu(self):
        return bool(self.turkiye or self.duyarlilik or self.izlenecekler)

    @property
    def acilis_basilir(self):
        return bool(self.acilis) and not self.dolu


BULGU = "Brent 88,90 $ (bir ayda +%29,4)"


# ------------------------------------------------------------------
# OLCUMU OLMAYAN HABERE DOSYA BULGUSU GONDERILMEZ.
#
# Olculdu ve ANA SAYFADA YAN YANA YAYIMLANDI: "Yemen'de Mocha limanina
# saldiri", "Iran cumhurbaskani Hamaney'le gorustu" ve "Axios roportaji"
# haberlerinin UCU DE ayni cumleyle basladi -- "Brent petrolun kapanis
# fiyati 88,90 $...". Ucu de ayni jeopolitik dosyaya bagliydi ve o
# dosyadaki tek sayi Brent'ti; model elindeki tek olcumu anlatti.
# ------------------------------------------------------------------
print("Olcumu olmayan haber -- dosya bulgusu gonderilmemeli")
olcumsuz = {"baslik": "Yemen askeri sözcüsü: Mocha limanına saldırı",
            "konu": "Jeopolitik", "kurum": "AA", "ozet": ""}
g = U.girdi_kur(olcumsuz, SahteDosya(bulgular=[BULGU]))
dogru("bulgu satiri YOK", "Bulgu:" not in g)
dogru("Brent sayisi girdide YOK", "88,90" not in g)
dogru("haber basligi VAR", "Mocha" in g)
dogru("sektor listesi VAR -- sayi degil yapi", "Etkilenen sektörler" in g)
dogru("izlenecekler VAR", "İzlenecekler" in g)
es("mekanizma yonergesine dusuyor", yorumcu.olcum_var(g), False)

# ------------------------------------------------------------------
# HABERIN KENDI OLCUMU VARSA baglam GONDERILIR: orada dosya bulgusu
# yorumu saptirmiyor, zenginlestiriyor.
# ------------------------------------------------------------------
print("\nOlcumu olan haber -- baglam gonderilmeli")
olcumlu = {"baslik": "ABD TÜFE temmuzda %2,8", "konu": "Enflasyon",
           "kurum": "BLS", "ozet": "Gerçekleşen %2,8, beklenti %2,9"}
g2 = U.girdi_kur(olcumlu, SahteDosya(bulgular=[BULGU]))
dogru("bulgu satiri VAR", "Bulgu:" in g2)
dogru("haberin kendi verisi VAR", "beklenti %2,9" in g2)
es("veri yonergesine dusuyor", yorumcu.olcum_var(g2), True)

# Acilis cumlesi de haberin KENDI olcumu sayilir.
print("\nAcilis cumlesi haberin kendi olcumudur")
g3 = U.girdi_kur({"baslik": "TCMB faiz karari", "konu": "Para politikası",
                  "kurum": "TCMB", "ozet": ""},
                 SahteDosya(acilis="Politika faizi %37'de sabit",
                            bulgular=[BULGU]))
dogru("acilis varken bulgu da gonderiliyor", "Bulgu:" in g3)

# ------------------------------------------------------------------
# `neden_onemli` HICBIR DURUMDA gonderilmiyor -- model onu oldugu gibi
# kopyaliyordu ve uc yorum ayni cumleyle bitiyordu.
# ------------------------------------------------------------------
print("\nKopyalanmasini istemedigimiz metin hic gonderilmiyor")
dogru("neden_onemli girdide yok",
      "neden_onemli" not in U.girdi_kur(
          {**olcumlu, "neden_onemli": "Bu cumle kopyalanmamali"},
          SahteDosya()))


# ---------------------------------------------------------------------
# DEPODAKI KOKEN KAYDI TUTARLI OLMALI
#
# Olculdu (2026-09-14): `ai_yorum` tablosunda 21 satir
# `saglayici='anthropic'` yaninda `model='@cf/openai/gpt-oss-120b'`
# tasiyordu -- yani Cloudflare'in urettigi yorum Anthropic'e mal
# edilmisti. Sebep: `uret_ai_yorum` saglayiciyi DONGUDEN ONCE bir kez
# soruyor, `yorumla` ise bakiye bitince kosu ortasinda gecebiliyor.
#
# Sitede gorunmuyor, bu yuzden hicbir yerde kirmizi yanmiyordu. Ama
# koken kaydi yanlis: saglayici basarimini ya da maliyetini olcmek
# isteyen herkesi yaniltir.
#
# Kural artik GERCEK VERI uzerinde nobet tutuyor: kod duzeltildi ama
# bir daha bozulursa depodaki satirlar bunu soyleyecek.
# ---------------------------------------------------------------------
import sqlite3  # noqa: E402

# KAYIT YOLU DA SINANIYOR, YALNIZCA SONUC DEGIL.
#
# Depo taramasi mevcut veriyi koruyor ama KODUN geri alinmasini
# yakalamiyor: satirlar zaten dogru oldugu icin tarama yesil kalirdi
# ve kusur ancak yeni bozuk veri birikince gorunurdu. Bu depoda
# `test_acilis_kurali` ayni sebeple kaynak metnini okuyor: iki yerin
# ayni karari vermemesi gerekiyorsa, bunu sinama soylemeli.
_kaynak = (_KOK / "uret_ai_yorum.py").read_text(encoding="utf-8")
dogru("koken INSERT'te modelden turetiliyor",
      "model_saglayicisi(model)" in _kaynak)

_db = _KOK / "netaris.db"
if _db.exists():
    _b = sqlite3.connect(f"file:{_db}?mode=ro", uri=True)
    try:
        _satir = _b.execute("SELECT saglayici, model FROM ai_yorum").fetchall()
    finally:
        _b.close()
    dogru("depoda yorum var", len(_satir) > 50)
    _uyusmaz = [(s, m) for s, m in _satir
                if yorumcu.model_saglayicisi(m) != s]
    es("koken kaydi model ile uyusuyor", _uyusmaz[:3], [])
else:
    print("  ATLANDI  netaris.db yok")


# ---------------------------------------------------------------------
# ANLATACAK VERISI OLMAYAN HABERE MODEL CAGRILMIYOR
#
# Olculdu (2026-09-15): 40 adayin 15'i su sekildeydi -- haberin KENDI
# olcumu yok (ozet bos) ve elimizdeki tek veri BASKA bir ulkeye ait:
#
#     Haber : Guangzhou Automobile hissesi neden yukseliste?
#     Kaynak: Investing.com Turkiye         (haber_ulkesi = TR)
#     Acilis: ABD 10 yillik tahvil getirisi %4,96
#
# Modele verilen tek sayi ABD'ye ait; model onu kullaniyor ve ardindan
# "TR haberi ama yalnizca US verisi aniyor" diye reddediliyor. Gunun
# 340 reddinin 259'u bu kapidandi.
# ---------------------------------------------------------------------
import sqlite3 as _sq3  # noqa: E402

_sahte = _sq3.connect(":memory:")
_sahte.execute("create table gosterge(kod text, tarih text, deger real,"
               " birim text, ad text, kaynak text, kayit_ani text)")
_sahte.execute("create table fiyat(sembol text, tarih text, kapanis real,"
               " yuksek real, dusuk real, hacim real)")
# DGS10 -> US, TP.* -> TR (bkz. baglam.seri_ulkesi).
import datetime as _dt  # noqa: E402
_bugun = _dt.date.today().isoformat()
_sahte.execute("insert into gosterge values('DGS10',?,4.96,'%','ABD 10Y',"
               "'FRED','')", (_bugun,))
_sahte.execute("insert into gosterge values('TP.TUKFIY2025.GENEL',?,31.75,"
               "'%','TUFE','TCMB','')", (_bugun,))

_YABANCI = "Açılış: ABD 10 yıllık tahvil getirisi %4,96; 1 ayda yükseldi."
_YERLI = "Gösterge: TÜFE %31,75 (önceki %32,10)."

_G_YABANCI = """Haber: Guangzhou Automobile hissesi neden yükselişte?
Açılış: ABD 10 yıllık tahvil getirisi %4,96; 1 ayda yükseldi.
Bulgu: Sektör görünümü değerlendirmesi sürüyor ve izlenecek başlıklar arasında yer alıyor.
Etkilenen sektörler (sırayla): Bankacılık, Sanayi"""

# KURGU, YALNIZCA "kendi olcumu var" KORUMASININ BELIRLEYICI OLDUGU
# HALDE kuruldu.
#
# Ilk yazimda haberin kendi sayisi 4,96 idi -- yani girdideki yabanci
# sayiyla AYNI. O sayi zaten `haber_metni` ile haric tutuldugu icin
# uyusmazlik hic olusmuyordu ve koruma kaldirilsa bile sinama
# GECIYORDU: mutasyon kacti, sinama hicbir sey olcmuyordu.
#
# Simdi haberin kendi olcumu (2,5) hicbir seriye baglanmiyor, girdideki
# 4,96 ise ABD serisine baglaniyor. Yani uyusmazlik OLUSUYOR ve haberi
# kapidan yalnizca "kendi olcumu var" kurali gecirebiliyor.
_G_KENDI_OLCUM = """Haber: Sanayi üretimi açıklandı
Veri: Sanayi üretimi yüzde 2,5 azaldı.
Açılış: ABD 10 yıllık tahvil getirisi %4,96; 1 ayda yükseldi."""

_G_YERLI = """Haber: Enflasyon açıklandı
Gösterge: TÜFE %31,75 (önceki %32,10).
Bulgu: Sektör görünümü değerlendirmesi sürüyor ve izlenecek başlıklar arasında yer alıyor.
Etkilenen sektörler (sırayla): Bankacılık, Sanayi"""

_G_BAGLANMAYAN = """Haber: Bir başlık
Açılış: değer 777,77 seviyesinde.
Bulgu: Sektör görünümü değerlendirmesi sürüyor ve izlenecek başlıklar arasında yer alıyor.
Etkilenen sektörler (sırayla): Bankacılık, Sanayi"""

_G_ULKESIZ = """Haber: Bir başlık
Açılış: ABD 10 yıllık tahvil getirisi %4,96; 1 ayda yükseldi.
Bulgu: Sektör görünümü değerlendirmesi sürüyor ve izlenecek başlıklar arasında yer alıyor.
Etkilenen sektörler (sırayla): Bankacılık, Sanayi"""

# 0. GIRDI HIC OLUSMADIYSA da anlatacak sey yoktur.
#
# `yorumla` bunu zaten reddediyor ve MODEL CAGIRMIYOR -- maliyeti yok.
# Ama kota yuvasi harciyor ve model hatasi OLMADIGI halde `ai_ret`e
# "red" olarak yaziliyordu; red istatistiklerini sisiriyordu.
# Olculdu (2026-09-15): 55 girdinin 1'i bu durumda.
#
# ESIK KOPYALANMIYOR: `yorumcu.EN_AZ_GIRDI`den okunuyor. Sayiyi ikinci
# kez yazmak, bu depoda defalarca ayrisan "ayni karari veren iki kod
# yolu" demekti.
_KISA = "Haber: Kısa\nKonu: X"
dogru("kisa girdi kurgusu gercekten kisa",
      len(_KISA) < yorumcu.EN_AZ_GIRDI)
dogru("kisa girdi atlaniyor",
      U.anlatacak_veri_yok(
          _sahte, _KISA,
          {"baslik": "Kısa", "kurum": "TCMB", "bolge": "TR", "ozet": ""}))
# Esigin USTUNDEKI girdi bu kapiya takilmiyor.
dogru("yeterli uzunluktaki girdi bu kapiya takilmiyor",
      not U.anlatacak_veri_yok(
          _sahte, _G_YERLI + " " + "dolgu " * 30,
          {"baslik": "Enflasyon açıklandı", "kurum": "TCMB", "bolge": "TR",
           "ozet": ""}))

# 1. Kendi olcumu YOK + veri baska ulkeden -> ATLA.
dogru("olcumsuz haber + yabanci veri -> atlaniyor",
      U.anlatacak_veri_yok(
          _sahte, _G_YABANCI,
          {"baslik": "Guangzhou Automobile hissesi neden yükselişte?",
           "kurum": "Investing.com Türkiye", "bolge": "TR", "ozet": ""}))

# 2. Kendi olcumu VAR -> kapiya takilmiyor; baglam kontrolu karar verir.
dogru("KENDI olcumu olan haber atlanmiyor",
      not U.anlatacak_veri_yok(
          _sahte, _G_KENDI_OLCUM,
          {"baslik": "Sanayi üretimi açıklandı", "kurum": "TÜİK",
           "bolge": "TR", "ozet": "Sanayi üretimi yüzde 2,5 azaldı."}))

# 3. Veri haberin KENDI ulkesinden -> atlanmiyor.
dogru("yerli veri verilen haber atlanmiyor",
      not U.anlatacak_veri_yok(
          _sahte, _G_YERLI,
          {"baslik": "Enflasyon açıklandı", "kurum": "TCMB", "bolge": "TR",
           "ozet": ""}))

# 4. Hicbir sayi seriye baglanmiyorsa cakisma da yok -> atlanmiyor.
dogru("seriye baglanmayan sayi atlatmaz",
      not U.anlatacak_veri_yok(
          _sahte, _G_BAGLANMAYAN,
          {"baslik": "Bir başlık", "kurum": "Ekonomim", "bolge": "TR",
           "ozet": ""}))

# 5. Haberin ulkesi bilinmiyorsa karar VERILMEZ (baglam kurali).
dogru("ulkesi bilinmeyen haber atlanmiyor",
      not U.anlatacak_veri_yok(
          _sahte, _G_ULKESIZ,
          {"baslik": "Bir başlık", "kurum": "Ekonomim", "bolge": "DUNYA",
           "ozet": ""}))

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
