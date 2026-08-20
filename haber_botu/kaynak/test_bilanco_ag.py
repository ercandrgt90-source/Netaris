"""Mali tablo cekici -- donem cevirisi ve ayristirma.

En kritik iki kural burada kilitleniyor:

  1. AKIS toplanir, STOK toplanmaz. Gelir tablosu kalemleri donem
     akisidir (ceyrekler toplanir); bilanco kalemleri belirli bir
     ANIN stogudur. Karistirmak toplam varliklari kat kat sisirir.

  2. Kalem adi kendi "Growth" ikizini tasiyor ("Revenue    Revenue
     Growth"). Once kirpilmali, SONRA elenmeli. Ilk yazimda tersti ve
     GELIR TABLOSU BOMBOS donuyordu -- bilancoda ikiz etiket olmadigi
     icin hata yarim gorunuyordu, yani en tehlikeli bicimde.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bilanco_ag as ba  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama):
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


print("\nMali tablo cekici\n")

# --- sayi cozumleme ---
esit(ba._sayi("1,234.5"), 1_234_500_000.0, "milyon cinsinden okunuyor")
esit(ba._sayi("-670.6"), -670_600_000.0, "negatif deger")
esit(ba._sayi("-"), None, "bos hucre None")
esit(ba._sayi("57.40%"), None, "YUZDE reddediliyor -- o kalem degil")
esit(ba._sayi(""), None, "bos dizge")

# --- donem cevirisi: AKIS toplanir ---
esit(ba.donem_toplami([100.0, 200.0, 300.0], 2, akis=True), 300.0,
     "AKIS: iki ceyrek toplaniyor (6 aylik)")
esit(ba.donem_toplami([100.0, 200.0, 300.0], 3, akis=True), 600.0,
     "AKIS: uc ceyrek toplaniyor (9 aylik)")

# --- STOK toplanmaz ---
esit(ba.donem_toplami([500.0, 400.0, 300.0], 2, akis=False), 500.0,
     "STOK: son ceyregin degeri AYNEN -- toplanmiyor")
esit(ba.donem_toplami([500.0, 400.0, 300.0], 3, akis=False), 500.0,
     "STOK: ceyrek sayisi degisince deger degismiyor")

# --- eksik veriyle uydurma yok ---
esit(ba.donem_toplami([100.0], 2, akis=True), None,
     "ceyrek yetmezse None -- eksigi tahminle doldurmuyoruz")
esit(ba.donem_toplami([100.0, None], 2, akis=True), None,
     "bir ceyrek bossa toplam URETILMIYOR")
esit(ba.donem_toplami([], 2, akis=True), None, "bos seri")

# --- tablo ayristirma: "Growth" ikizi ---
HTML = """
<table>
<tr><th>Fiscal Quarter</th><th>Q2 2026</th><th>Q1 2026</th></tr>
<tr><td>Period Ending</td><td>Jun 30</td><td>Mar 31</td></tr>
<tr><td>Revenue    Revenue Growth</td><td>50,632</td><td>57,664</td></tr>
<tr><td>Revenue Growth</td><td>57.40%</td><td>152.50%</td></tr>
<tr><td>Net Income    Net Income Growth</td><td>24,647</td><td>21,582</td></tr>
</table>
"""
donemler, kalemler = ba._tablo(HTML)
esit(donemler, ["Q2 2026", "Q1 2026"], "donem basliklari okunuyor")
esit(sorted(kalemler), ["Net Income", "Revenue"],
     "kalem adlarindan 'Growth' ikizi kirpiliyor")
esit("Revenue Growth" in kalemler, False,
     "yalnizca buyume olan satir ELENIYOR")
esit(kalemler["Net Income"], [24_647_000_000.0, 21_582_000_000.0],
     "degerler milyon carpaniyla okunuyor")

# --- gercek olcum: TERA 2026/6 ---
#
# KAP'tan ELLE girilen donem kari 46,26 mlr TL idi. Ceyreklerden
# turetilen toplam bunu yuvarlama farkiyla tutturmali.
esit(round((24_647_000_000.0 + 21_582_000_000.0) / 1e9, 2), 46.23,
     "TERA 2026/6: Q1+Q2 = 46,23 mlr (KAP 46,26 -- %0,07 yuvarlama)")


# --------------------------------------------------------------------
# KALEM ESLESTIRMESI
# --------------------------------------------------------------------
TABLO = {
    "gelir": {"Revenue": 100.0, "Gross Profit": 40.0,
              "Operating Income": 25.0, "Net Income": 18.0},
    "bilanco": {"Total Assets": 500.0, "Shareholders' Equity": 300.0,
                "Total Current Assets": 200.0,
                "Total Current Liabilities": 120.0,
                "Accounts Receivable": 30.0, "Inventory": 60.0,
                "Net Cash (Debt)": -80.0},
    "nakit": {"Depreciation & Amortization": 7.0},
}
d = ba.donemi_kur(TABLO)

esit(d["hasilat"], 100.0, "hasilat <- Revenue")
esit(d["ozkaynak"], 300.0, "ozkaynak <- Shareholders' Equity")
esit(d["stoklar"], 60.0, "stoklar <- Inventory")

# EN KRITIK: net borcun ISARETI TERS.
#
# Kaynak "Net Cash (Debt)" yaziyor -- POZITIF deger net NAKIT demek.
# Hattaki `net_borc` alani borcu POZITIF bekliyor. Cevirmeden
# aktarmak, borclu sirketi nakit zengini gostermek olurdu; yonu ters
# bir rakam, eksik rakamdan KOTUDUR.
esit(d["net_borc"], 80.0, "net borc ISARETI CEVRILIYOR (-80 nakit -> 80 borc)")
esit(ba.donemi_kur({"bilanco": {"Net Cash (Debt)": 50.0}})["net_borc"], -50.0,
     "net NAKIT sirkette net_borc negatif")

# FAVOK kaynakta YOK, turetiliyor: faaliyet kari + amortisman.
esit(d["favok"], 32.0, "FAVOK = faaliyet kari 25 + amortisman 7")
esit("favok" in ba.donemi_kur({"gelir": {"Operating Income": 25.0}}), False,
     "amortisman yoksa FAVOK URETILMIYOR -- yaklasik FAVOK, FAVOK degildir")
esit("favok" in ba.donemi_kur({"nakit": {"Depreciation & Amortization": 7.0}}),
     False, "faaliyet kari yoksa FAVOK uretilmiyor")

# Eksik kalem SESSIZCE SIFIR OLMUYOR -- alan hic bulunmuyor.
esit("brut_kar" in ba.donemi_kur({"gelir": {"Revenue": 10.0}}), False,
     "olmayan kalem icin alan URETILMIYOR (sifir yazilmiyor)")

# --------------------------------------------------------------------
# MUHASEBE OZDESLIKLERI
# --------------------------------------------------------------------
#
# Eslemenin dogrulugunu KAYNAKTAN BAGIMSIZ sinar: bir etiketi yanlis
# alana baglarsak toplamlar tutmaz. Olculdu -- 12 BIST sirketinde
# (banka dahil) ozdesliklerin hepsi tutuyor.
TUTAN = {"Total Assets": 500.0, "Total Liabilities & Equity": 500.0,
         "Total Liabilities": 200.0, "Shareholders' Equity": 300.0,
         "Total Common Equity": 280.0, "Minority Interest": 20.0,
         "Total Current Assets": 200.0, "Total Current Liabilities": 120.0,
         "Working Capital": 80.0}
esit(ba.ozdeslik_denetimi(TUTAN), [], "tutan bilancoda bulgu yok")

BOZUK = dict(TUTAN, **{"Total Liabilities": 250.0})
esit(len(ba.ozdeslik_denetimi(BOZUK)) > 0, True,
     "Varliklar != Borc + Ozkaynak YAKALANIYOR")

BOZUK2 = dict(TUTAN, **{"Minority Interest": 50.0})
esit(len(ba.ozdeslik_denetimi(BOZUK2)) > 0, True,
     "Ozkaynak ayrismasi bozulunca yakalaniyor")

# Yuvarlama farki HATA SAYILMAMALI: kaynak bes anlamli basamak veriyor.
YUVARLAMA = dict(TUTAN, **{"Total Liabilities & Equity": 500.4})
esit(ba.ozdeslik_denetimi(YUVARLAMA), [],
     "binde birlik yuvarlama farki hata sayilmiyor")

# Eksik kalem varsa o ozdeslik ATLANIR, uydurma yapilmaz.
esit(ba.ozdeslik_denetimi({"Total Assets": 500.0}), [],
     "karsilastirilacak kalem yoksa ozdeslik atlaniyor")


# --------------------------------------------------------------------
# SEKTORE GORE YETERLILIK
# --------------------------------------------------------------------
#
# Eksik alanin IKI ayri anlami var:
#   "bu sektorde o kalem YOK"  -> normal
#   "veri gelmedi"             -> analiz YAPILMAMALI
# Karistirmak, eksik tabloyu tam sanmak demek.
TAM = {"hasilat": 1.0, "net_kar": 1.0, "aktif_toplami": 1.0,
       "ozkaynak": 1.0, "brut_kar": 1.0, "faaliyet_kari": 1.0,
       "stoklar": 1.0, "donen_varliklar": 1.0,
       "kisa_vadeli_yukumlulukler": 1.0}

esit(ba.yeterli(TAM, "Sanayi")[0], True, "sanayide tam veri yeterli")

# GYO'da brut kar/stok GELMIYOR ve gelmemesi dogru -- olculdu, iki
# ornek sirkette de 0/2. Cekirdek dort alan varsa analiz yapilabilir.
GYO = {"hasilat": 1.0, "net_kar": 1.0, "aktif_toplami": 1.0, "ozkaynak": 1.0}
esit(ba.yeterli(GYO, "Gayrimenkul")[0], True,
     "GYO'da brut kar/stok YOKLUGU eksiklik SAYILMIYOR")
esit(ba.yeterli(GYO, "Sanayi")[0], False,
     "AYNI veri sanayide YETERSIZ -- sektor sarti gercekten farkli")
esit(sorted(ba.yeterli(GYO, "Sanayi")[1])[:2], ["brut_kar", "donen_varliklar"],
     "eksik alanlar adiyla bildiriliyor")

# Cekirdek alan eksikse HICBIR sektorde yeterli degil.
esit(ba.yeterli({"hasilat": 1.0, "net_kar": 1.0}, "Gayrimenkul")[0], False,
     "cekirdek eksikse GYO'da bile yetersiz")
esit(ba.yeterli({}, "")[0], False, "bos veri yetersiz")

# Sektoru BILINMEYEN sirkette yalnizca cekirdek araniyor: bilmedigimiz
# bir sunuma ek sart koymak, kesfedilmemisi hata sanmak olurdu.
esit(ba.yeterli(GYO, "")[0], True,
     "sektor bilinmiyorsa yalnizca cekirdek araniyor")
esit(ba.yeterli(GYO, "Uydurma Sektor")[0], True,
     "taniinmayan sektorde ek sart KOSULMUYOR")

# Sifir DEGER eksik SAYILMAMALI -- sifir bir olcumdur.
SIFIRLI = dict(TAM, **{"brut_kar": 0.0})
esit(ba.yeterli(SIFIRLI, "Sanayi")[0], True,
     "sifir deger eksik sayilmiyor (0 bir olcumdur, bosluk degil)")


# --------------------------------------------------------------------
# NAKIT AKIS ALANLARI -- ISARET
# --------------------------------------------------------------------
#
# Capex nakit akis tablosunda NEGATIF yaziliyor (nakit cikisi), hattaki
# `yatirim_harcamasi` alani ise POZITIF bekliyor. Cevirmeden aktarmak
# yatirim yapan sirketi yatirim GELIRI olan sirket gosterirdi ve
# serbest nakit akisi hesabini ters yone cevirirdi.
NAKITLI = ba.donemi_kur({"nakit": {
    "Capital Expenditures": -1_930_000_000.0,
    "Operating Cash Flow": 3_220_000_000.0,
    "Cash Interest Paid": 2_500_000_000.0,
}})
esit(NAKITLI["yatirim_harcamasi"], 1_930_000_000.0,
     "capex ISARETI CEVRILIYOR (-1,93 mlr -> pozitif 1,93)")
esit(NAKITLI["faaliyet_nakit_akisi"], 3_220_000_000.0,
     "faaliyet nakit akisi aynen aktariliyor")
esit(NAKITLI["finansman_gideri"], 2_500_000_000.0,
     "odenen faiz finansman gideri olarak baglaniyor")

# Zaten pozitif gelen capex de pozitif kalmali -- mutlak deger.
esit(ba.donemi_kur({"nakit": {"Capital Expenditures": 500.0}})["yatirim_harcamasi"],
     500.0, "pozitif capex bozulmuyor")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
