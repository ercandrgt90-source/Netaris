"""politika_faizi.py testleri -- AGA CIKMAZ.

Bu ayristirici yanlis okursa sayfada YANLIS BIR FAIZ ORANI cikar ve
duzgun gorunur. Tam olarak sifira indirmeye calistigimiz hata sinifi:
sayi dogru bicimli, anlami yanlis.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import politika_faizi as PF  # noqa: E402

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
# SABIT TUTMA -- tek oran var.
# --------------------------------------------------------------------
SABIT = """<p>Para Politikası Kurulu (Kurul), politika faizi olan bir
hafta vadeli repo ihale faiz oranının yüzde 37&rsquo;de sabit
tutulmasına karar vermiştir. Kurul ayrıca, Merkez Bankası gecelik
vadede borç verme faiz oranını yüzde 40&rsquo;ta, gecelik vadede
borçlanma faiz oranını ise yüzde 35,5&rsquo;te sabit tutmuştur.</p>"""
oran, cumle = PF.coz(SABIT.replace("&rsquo;", "’"))
es("sabit tutma orani", oran, 37.0)
dogru("cumle geri veriliyor", "repo ihale" in cumle)
# GECELIK FAIZLER KARISMAMALI: %40 ve %35,5 ayni paragrafta.
dogru("gecelik borc verme faizi alinmiyor", oran != 40.0)

# --------------------------------------------------------------------
# INDIRIM -- IKI oran var, YENI olan IKINCISI.
#
# Ilkini almak, faiz her degistiginde ESKI orani yayimlamak olurdu.
# --------------------------------------------------------------------
INDIRIM = """<p>Kurul, politika faizi olan bir hafta vadeli repo ihale
faiz oranının yüzde 39,5'ten yüzde 38'e indirilmesine karar
vermiştir.</p>"""
oran, _ = PF.coz(INDIRIM)
es("indirimde YENI oran aliniyor", oran, 38.0)

ARTIS = """<p>Kurul, politika faizi olan bir hafta vadeli repo ihale
faiz oranının yüzde 36'dan yüzde 38,5'e yükseltilmesine karar
vermiştir.</p>"""
oran, _ = PF.coz(ARTIS)
es("artista YENI oran aliniyor", oran, 38.5)

# --------------------------------------------------------------------
# ONDALIK VIRGULLE -- "39,5" ondalik, binlik degil.
# --------------------------------------------------------------------
oran, _ = PF.coz("politika faizi olan bir hafta vadeli repo ihale faiz "
                 "oranının yüzde 42,5'te sabit tutulmasına karar verdi.")
es("ondalik virgul cozuluyor", oran, 42.5)

# --------------------------------------------------------------------
# BULUNAMAYAN / BOZUK GIRDI -- UYDURMA YOK.
# --------------------------------------------------------------------
es("alakasiz metin", PF.coz("<p>Enflasyon raporu yayımlandı.</p>")[0], None)
es("bos girdi", PF.coz("")[0], None)
es("yuzdesiz cumle",
   PF.coz("politika faizi olan bir hafta vadeli repo ihale faiz oranı "
          "sabit tutulmuştur.")[0], None)

# Sinir disi okuma = yanlis cumleye takildik, sayi YAYIMLANMAZ.
es("sinir disi okuma reddedilir",
   PF.coz("politika faizi olan bir hafta vadeli repo ihale faiz "
          "oranının yüzde 850'de sabit tutulmasına karar verdi.")[0], None)

# --------------------------------------------------------------------
# TIRNAK BICIMI -- TCMB egri kesme isareti kullaniyor.
# Duz kesme isaretiyle yazilmis bir kalip TCMB metnini KACIRIRDI.
# --------------------------------------------------------------------
egri = ("politika faizi olan bir hafta vadeli repo ihale faiz oranının "
        "yüzde 37’de sabit tutulmasına karar vermiştir.")
duz = egri.replace("’", "'")
es("egri kesme isareti", PF.coz(egri)[0], 37.0)
es("duz kesme isareti", PF.coz(duz)[0], 37.0)

# --------------------------------------------------------------------
# HTML ETIKETLERI ARADAN GECIYOR.
# --------------------------------------------------------------------
etiketli = ("<div><span>politika faizi</span> olan <b>bir hafta vadeli "
            "repo ihale faiz oranının</b> yüzde <em>37</em>'de sabit "
            "tutulmasına karar vermiştir.</div>")
es("etiket arasindan okunuyor", PF.coz(etiketli)[0], 37.0)

print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  X", k)
sys.exit(1 if kaldi else 0)
