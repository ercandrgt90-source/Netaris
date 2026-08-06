"""onem.py testleri.

Bu motorun hatalari SESSIZDIR: yanlis puanlanmis bir haber, sayfada
"yanlis puan" diye gorunmez -- sadece yanlis yerde durur. O yuzden
sinirlar burada sabitleniyor.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_BU), str(_BU.parent / "kaynak")]

import onem  # noqa: E402

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


# --------------------------------------------------------------------
# Konu anahtarlari besleme listesiyle ayni olmali.
#
# Bu tam olarak `BULGU_KONULARI`'nda yasanan hata: uydurulmus bir konu
# anahtari sessizce varsayilana duser ve bir daha fark edilmez. Dort
# tane oyle anahtar bu testin ilk calismasinda yakalandi.
# --------------------------------------------------------------------
es("uydurma konu anahtari yok", onem.dogrula(), [])

# --------------------------------------------------------------------
# Bilesenlerin toplami 100'u gecemez.
# --------------------------------------------------------------------
es("bilesen tavani",
   onem.KONU_TABANI["Para politikası"] + onem.OLAY_EN_COK
   + onem.KAYNAK_BIRINCIL + onem.SURPRIZ_EN_COK + onem.KAPSAM_EN_COK,
   100)

# --------------------------------------------------------------------
# Faiz karari kritik olmali -- surpriz olmasa bile.
# --------------------------------------------------------------------
o = onem.puanla("TCMB politika faizini sabit tuttu",
                konu="Para politikası", kurum="TCMB", varlik_sayisi=4)
es("faiz karari kritik", o.katman, "kritik")
es("faiz olay turu", o.olay_turu, "faiz")

# --------------------------------------------------------------------
# Ayni haber AKTARIM kaynagindan gelirse kritik tabanina girmez.
# Editoryal taban yalnizca birincil kaynakta uygulanir; yoksa herhangi
# bir sitenin "faiz" gecen her yazisi son dakika olurdu.
# --------------------------------------------------------------------
o2 = onem.puanla("Faiz kararı öncesi beklentiler",
                 konu="Para politikası", kurum="FinancialJuice")
dogru("aktarim kaynak taban almaz", not o2.taban_uygulandi)

# --------------------------------------------------------------------
# Festival/turizm haberi akista kalmali.
# --------------------------------------------------------------------
o3 = onem.puanla("Antalya'da turizm sezonu açıldı", konu="Turizm",
                 kurum="FinancialJuice")
es("turizm haberi akista", o3.katman, "akis")
dogru("turizm senaryoya girmez", not o3.one_cikar)

# --------------------------------------------------------------------
# SURPRIZ
# --------------------------------------------------------------------
# Yuzde serisinde 0,2 puanlik sapma orta buyukluk.
oy = onem.puanla(
    "ABD TÜFE %3,1",
    "US CPI YoY Actual 3.1% (Forecast 2.9%, Previous 3.0%)",
    konu="Enflasyon", veri_mi=True, varlik_sayisi=3)
s = dict(oy.bilesenler)["surpriz"]
dogru("0,2 puanlik sapma surprizi 0'dan buyuk", s > 0)
dogru("0,2 puanlik sapma tavana vurmuyor", s < onem.SURPRIZ_EN_COK)

# Beklentiyi tam tutturan veri surpriz uretmemeli.
ot = onem.puanla(
    "ABD TÜFE %2,9",
    "US CPI YoY Actual 2.9% (Forecast 2.9%, Previous 3.0%)",
    konu="Enflasyon", veri_mi=True)
es("beklenti tutunca surpriz yok", dict(ot.bilesenler)["surpriz"], 0)

# Buyuk sapma tavana vurmali.
ob = onem.puanla(
    "ABD TÜFE %4,5",
    "US CPI YoY Actual 4.5% (Forecast 2.9%, Previous 3.0%)",
    konu="Enflasyon", veri_mi=True)
es("buyuk sapma tavanda", dict(ob.bilesenler)["surpriz"], onem.SURPRIZ_EN_COK)

# Beklentisi olmayan veri, onceki donemle olculur ama YARIM sayilir.
oo = onem.puanla(
    "İşten çıkarmalar 33,43",
    "US Challenger Layoffs Actual 33.429k (Forecast -, Previous 45.849k)",
    konu="İstihdam ve ücret", veri_mi=True)
og = dict(oo.bilesenler)["surpriz"]
dogru("beklentisiz veri de surpriz uretir", og > 0)
dogru("beklentisiz surpriz yarim olcekte", og <= onem.SURPRIZ_EN_COK // 2)

# Sifir beklenti bolme hatasi vermemeli.
oz = onem.puanla("X", "X Actual 5 (Forecast 0, Previous 0)", konu="Borsa")
dogru("sifir beklenti cokmuyor", isinstance(oz.puan, int))

# --------------------------------------------------------------------
# KAPSAM
# --------------------------------------------------------------------
a = onem.puanla("Brent petrol yükseldi", konu="Enerji", varlik_sayisi=0)
b = onem.puanla("Brent petrol yükseldi", konu="Enerji", varlik_sayisi=5)
dogru("cok varliga dokunan haber daha yuksek", b.puan > a.puan)
es("kapsam tavani", dict(b.bilesenler)["kapsam"], onem.KAPSAM_EN_COK)

# --------------------------------------------------------------------
# KAYNAK
# --------------------------------------------------------------------
es("birincil kaynak", dict(onem.puanla("x", kurum="TCMB").bilesenler)["kaynak"],
   onem.KAYNAK_BIRINCIL)
es("veri hatti birincil sayilir",
   dict(onem.puanla("x", veri_mi=True).bilesenler)["kaynak"],
   onem.KAYNAK_BIRINCIL)
es("aktarim kaynak",
   dict(onem.puanla("x", kurum="FinancialJuice").bilesenler)["kaynak"],
   onem.KAYNAK_AKTARIM)

# --------------------------------------------------------------------
# Puan hicbir zaman 100'u gecmez, hic negatif olmaz.
# --------------------------------------------------------------------
en_ust = onem.puanla(
    "TCMB politika faizi faiz kararı",
    "TR Rate Decision Actual 50% (Forecast 30%, Previous 30%)",
    konu="Para politikası", kurum="TCMB", varlik_sayisi=9, yayilim=6)
dogru("puan 100'u gecmiyor", 0 <= en_ust.puan <= 100)

# Bos girdi cokmemeli.
bos = onem.puanla("")
dogru("bos baslik cokmuyor", 0 <= bos.puan <= 100)

# --------------------------------------------------------------------
# SEC: katman 2 doldurmasi
# --------------------------------------------------------------------
sahte = [(onem.Onem(puan=p, katman="x"), {"i": p}) for p in range(10, 100, 3)]
secim = onem.sec(sahte)
es("secim ust siniri", len(secim), onem.EN_COK_SECIM)
dogru("secim puana gore sirali",
      all(secim[i][0].puan >= secim[i + 1][0].puan
          for i in range(len(secim) - 1)))
dogru("secimde esik alti yok", all(o.puan >= onem.NORMAL for o, _ in secim))

# Elde az haber varsa bolum kisa kalir -- doldurma yapilmaz.
az = [(onem.Onem(puan=p, katman="x"), {}) for p in (90, 80, 30, 20)]
es("az haberde doldurma yok", len(onem.sec(az)), 2)

# Hic uygun haber yoksa bos liste.
es("uygun haber yoksa bos", onem.sec([(onem.Onem(puan=5, katman="x"), {})]), [])


# --------------------------------------------------------------------
# TEKRAR ELEMESI
#
# Aktarim akislari tek konusmayi dort baslik yapiyor. Dordu birden
# "bugunun en onemlileri"ne girerse bolum tek olaya harcanir.
# --------------------------------------------------------------------
daly = [
    "Fed'den Daly: Güçlü enflasyon baskılarının yeniden canlanması",
    "Fed'den Daly: Halkın başka bir önemli enflasyon şokuna tepkisi",
    "Fed'den Daly: Enflasyon kötüleşirse merkez bankası müdahale eder",
]
dogru("ayni konusmanin basliklari benzer sayilir",
      onem.benzer(daly[0], daly[1]) and onem.benzer(daly[0], daly[2]))
dogru("farkli konudaki iki haber benzer sayilmaz",
      not onem.benzer("TCMB politika faizini sabit tuttu",
                      "Brent petrol varil başına 71 dolara geriledi"))
dogru("oneksiz ayni konu iki haberi ayri kalir",
      not onem.benzer("TCMB faiz kararını açıkladı",
                      "TCMB piyasa katılımcıları anketi yayımlandı"))
# Rakam tasiyan onek, onek SAYILMIYOR -- veriyi tasiyan bir onek akis
# adi degildir. (Ayni serinin iki ayi yine de kelime ortakligindan
# birlesir; istenen de budur.)
es("rakamli onek reddedilir", onem._onek("TÜFE %31,75: temmuz verisi"), "")
dogru("rakamli onekli FARKLI seriler birlesmez",
      not onem.benzer("TÜFE %31,75: temmuz verisi",
                      "Brent %2,10: günlük değişim"))
dogru("kisa onek sayilmaz",
      not onem.benzer("Not: petrol geriledi", "Not: altın yükseldi"))

kume = [(onem.Onem(puan=44 + i, katman="normal"), {"baslik": b})
        for i, b in enumerate(daly)]
kume.append((onem.Onem(puan=90, katman="kritik"),
             {"baslik": "TCMB politika faizini sabit tuttu"}))
t = onem.tekille(kume)
es("tekrarlar eleniyor", len(t), 2)
es("elenenden EN YUKSEK puanli kaliyor",
   sorted(o.puan for o, _ in t), [46, 90])

# Bos baslik cokmemeli.
dogru("bos baslik imzasi cokmuyor", not onem.benzer("", "x"))


# --------------------------------------------------------------------
# CESITLILIK -- ayni konudan en fazla uc kalem one cikar
# --------------------------------------------------------------------
# Basliklar BILINCLI OLARAK birbirine benzemiyor: benzeselerdi
# tekrar elemesine takilir ve cesitlilik kurali hic sinanmazdi.
# (Ilk yazimda "Jeopolitik haber 0..5" kullanildi ve testin olcmek
# istedigi sey yerine tekilleme olculdu.)
_jeo = ["Umman arabuluculugunda deniz yolu mutabakati",
        "Trump: goruSmeler iyi gidiyor",
        "Petrol tankerleri rota degistirdi",
        "Sigorta primleri iki katina cikti",
        "Katar dogal gaz sevkiyatini durdurdu",
        "Beyaz Saray yeni yaptirim paketi hazirliyor"]
_enf = ["Kira artis orani temmuzda yavasladi",
        "Uretici fiyatlari beklentinin altinda"]
cok = [(onem.Onem(puan=90 - i, katman="normal"),
        {"baslik": b, "konu": "Jeopolitik"}) for i, b in enumerate(_jeo)]
cok += [(onem.Onem(puan=50 - i, katman="normal"),
         {"baslik": b, "konu": "Enflasyon"}) for i, b in enumerate(_enf)]
s = onem.sec(cok, en_az=4, en_cok=5)
ilk = [h["konu"] for _, h in s[:4]]
es("konu basina sinir", ilk.count("Jeopolitik"), onem.KONU_BASINA_EN_COK)
dogru("sinira takilan konu disi haber one geliyor", "Enflasyon" in ilk)

# Elde BASKA konu yoksa bolum yine dolmali -- sinir bir eleme degil,
# bir siralama kurali.
tek = [(onem.Onem(puan=90 - i, katman="normal"),
        {"baslik": b, "konu": "Jeopolitik"})
       for i, b in enumerate(_jeo + _enf)]
es("baska konu yoksa yine doluyor", len(onem.sec(tek, en_az=8, en_cok=8)), 8)

print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  X", k)
sys.exit(1 if kaldi else 0)
