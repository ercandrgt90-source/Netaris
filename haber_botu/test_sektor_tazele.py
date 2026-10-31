# -*- coding: utf-8 -*-
"""SEKTORU EKSIK SIRKET, HATTIN GORUS ALANINDA HIC YOK.

BU DOSYA NEDEN VAR
------------------
`uret_bilanco --hepsi` sektor listesini defterdeki `sektor_tr`
alanindan kuruyor. O alani olmayan sirket hicbir sektore dusmuyor --
kac kosu kosulursa kosulsun sayfasi URETILMIYOR.

Koddaki gerekce "cogu icin bu dogru ve kasitli -- fon, varant,
yatirim ortakligi" diyordu. YARISI DOGRUYDU.

OLCULDU (2026-10-13): defterdeki 794 sirketin 441'inde `sektor_tr`
yok. Bu 441'den rastgele 25 ornek kaynaga soruldu --

    sektoru BULUNAN      13   KONYA, OBAMS, LKMNH, OYYAT, GSRAY...
    gercekten sektorsuz  12   varlik kiralama, menkul degerler

Yani kabaca 230 GERCEK sirket yalnizca bir alan bos oldugu icin hic
yayimlanmiyordu. Kullanici "GSRAY'in bilancosu aciklandi, bizde ne
zaman cikar" diye sordugunda ortaya cikti: GSRAY da bu listedeydi
ve kaynakta sektoru VARDI (Iletisim).

EN ONEMLI KURAL -- "CEKILEMEDI" ILE "SEKTORU YOK" AYRI SEYLER
--------------------------------------------------------------
Ilk yazimda ikisi ayni sayiliyordu ve OLCUM YANILTTI: 40 sirketin
39'u "kaynakta yok" diye bildirildi, oysa hepsi HTTP 429 idi --
kaynak beni yavaslatiyordu. Ayni gun rastgele bir orneklem 25'te 13
sektor bulmustu.

Yanlis sayi tek basina zararsiz olabilirdi; asil tehlike KARARdi:
"kaynakta yok" diye isaretlenen bir sirket icin bir daha sorulmaz
ve hat onu sonsuza kadar gormezdi.

NE SINANIYOR
------------
1. Kaynak sektor verince deftere YAZILIYOR.
2. Kaynak sektor VERMEYINCE uydurulmuyor -- alan bos kaliyor.
3. Kaynak REDDEDINCE (429) "sektoru yok" sayilmiyor.
4. Ardisik redlerde kosu DURUYOR; kalan istekler yapilmiyor.
5. Kuru calismada deftere yazilmiyor.

AG KULLANILMIYOR: `sektor.cek` yerine sahte islev konuyor.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))

import sektor                                      # noqa: E402
import sektor_tazele as st                         # noqa: E402

#: GERCEK `sektor.cek` -- ILK ISTE yakalaniyor.
#:
#: `kur()` onu yamaliyor. Ilk yazim gercek islevi 6a bolumunde
#: aliyordu ve o noktada ZATEN yamanmisti: iddia sahte islevi
#: olcuyordu ve iki mutasyon buradan kacti.
_GERCEK_CEK = sektor.cek

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


def kur(sirketler, cevaplar, reddedilenler=(), bulunamayanlar=()):
    """Gecici defter + sahte kaynak."""
    gecici = pathlib.Path(tempfile.mkdtemp()) / "sirketler.json"
    gecici.write_text(json.dumps({"sirketler": sirketler}, ensure_ascii=False),
                      encoding="utf-8")
    st.DEFTER = gecici
    sektor.OKUNAMAYAN.clear()

    def sahte(kod, istemci=None):
        if kod in bulunamayanlar:
            # KAYNAKTA YOK -- `sektor.cek` bunu AYRI tur olarak
            # firlatiyor; 404 bir kisitlama degil.
            sektor.OKUNAMAYAN.append((kod, "HTTP 404"))
            raise sektor.Bulunamadi("HTTP 404")
        if kod in reddedilenler:
            sektor.OKUNAMAYAN.append((kod, "HTTP 429"))
            return {}
        return cevaplar.get(kod, {})
    sektor.cek = sahte
    sektor.ARA_SN = 0
    return gecici


print("")
print("Sektor tazeleme")

# --- 1) BULUNAN SEKTOR DEFTERE YAZILIYOR -----------------------------
d = kur({"AAA": {"kod": "AAA"}, "BBB": {"kod": "BBB", "sektor_tr": "Sanayi"}},
        {"AAA": {"sektor": "Communication Services", "sektor_tr": "İletişim",
                 "alt_sektor": "Entertainment"}})
s = st.tazele(sinir=10)
esit(s["yazilan"], 1, "kaynakta sektoru olan sirket yaziliyor")
_def = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(_def["AAA"]["sektor_tr"], "İletişim", "dogru sektor yazildi")
esit(_def["BBB"]["sektor_tr"], "Sanayi", "zaten dolu olan degismedi")

# --- 2) SEKTOR YOKSA UYDURULMUYOR ------------------------------------
d = kur({"CCC": {"kod": "CCC"}}, {"CCC": {}})
s = st.tazele(sinir=10)
esit(s["yazilan"], 0, "sektoru olmayan sirkete uydurulmuyor")
esit(s["bos"], 1, "kaynakta yok diye sayiliyor")
esit("sektor_tr" in json.loads(d.read_text(encoding="utf-8"))["sirketler"]["CCC"],
     False, "alan bos birakiliyor")

# --- 3) RED (429) "SEKTORU YOK" DEGILDIR -----------------------------
# ILK YAZIMDA BU AYRIM YOKTU ve 40 sirketin 39'u yanlis bildirildi.
d = kur({"DDD": {"kod": "DDD"}}, {}, reddedilenler={"DDD"})
s = st.tazele(sinir=10)
esit(s["bos"], 0, "red, 'kaynakta yok' olarak SAYILMIYOR")
esit(s["hata"], 1, "red hata olarak sayiliyor")

# --- 4) ARDISIK REDDE KOSU DURUYOR -----------------------------------
kodlar = {f"R{i:02d}": {"kod": f"R{i:02d}"} for i in range(12)}
d = kur(kodlar, {}, reddedilenler=set(kodlar))
s = st.tazele(sinir=12)
esit(s["hata"], 5, "bes ardisik redde duruyor (12 degil)")

# --- 5) KURU CALISMA DEFTERE YAZMIYOR --------------------------------
d = kur({"EEE": {"kod": "EEE"}},
        {"EEE": {"sektor": "Industrials", "sektor_tr": "Sanayi"}})
s = st.tazele(sinir=10, kuru=True)
esit(s["yazilan"], 1, "kuru calismada da olcum yapiliyor")
esit("sektor_tr" in json.loads(d.read_text(encoding="utf-8"))["sirketler"]["EEE"],
     False, "kuru calismada deftere YAZILMIYOR")

# --- 6) BELIRLI KOD: DONEN KUYRUGU BEKLEMEDEN ------------------------
#
# Donen kuyruk 441 sirketi kosu basina 40'tan geciyor; belirli bir
# sirkete sira gelmesi gunler aliyor. Okurun sordugu sirket (GSRAY)
# kuyrugun ortasindaydi ve sayfasi URETILMIYORDU.
#
# Kural DEGISMIYOR: alani dolu olana dokunulmuyor, kaynak sektor
# vermiyorsa yazilmiyor.
d = kur({"AAA": {"kod": "AAA"},
         "BBB": {"kod": "BBB"},
         "CCC": {"kod": "CCC", "sektor_tr": "Sanayi"}},
        {"AAA": {"sektor": "Communication Services",
                 "sektor_tr": "İletişim", "alt_sektor": "Entertainment"},
         "BBB": {"sektor": "Industrials", "sektor_tr": "Sanayi"}})
s = st.tazele(sinir=10, kodlar=["bbb"])
esit(s["yazilan"], 1, "yalnizca istenen sirket islendi")
_def = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(_def["BBB"].get("sektor_tr"), "Sanayi", "istenen sirket yazildi")
esit("sektor_tr" in _def["AAA"], False,
     "istenmeyen sirkete DOKUNULMADI (kuyrukta olsa bile)")
esit(s["eksik"], 2, "kalan eksik sayisi yine bildiriliyor")

# Alani ZATEN DOLU olan kod istenirse dokunulmuyor.
d = kur({"CCC": {"kod": "CCC", "sektor_tr": "Sanayi"}},
        {"CCC": {"sektor": "Health Care", "sektor_tr": "Sağlık"}})
s = st.tazele(sinir=10, kodlar=["CCC"])
esit(s["yazilan"], 0, "sektoru dolu olan sirket YENIDEN yazilmiyor")
esit(json.loads(d.read_text(encoding="utf-8"))["sirketler"]["CCC"]["sektor_tr"],
     "Sanayi", "var olan sektor DEGISMEDI")

# Defterde olmayan kod sessizce gecilmiyor, ama cokmuyor da.
d = kur({"AAA": {"kod": "AAA"}}, {})
s = st.tazele(sinir=10, kodlar=["YOKBOYLE"])
esit(s["yazilan"], 0, "defterde olmayan kod yazilmiyor")
esit(s["hata"], 0, "defterde olmayan kod HATA sayilmiyor")

# ISTENEN KOD ICIN DE kaynak sektor vermiyorsa YAZILMIYOR.
d = kur({"AAA": {"kod": "AAA"}}, {"AAA": {}})
s = st.tazele(sinir=10, kodlar=["AAA"])
esit(s["yazilan"], 0, "kaynak sektor vermiyorsa istenen koda da yazilmiyor")
esit(s["bos"], 1, "kaynakta yok olarak sayiliyor")

# --- 6) KAYNAKTA OLMAYAN SIRKET KUYRUGU TIKAMIYOR --------------------
#
# OLCULDU (2026-10-31, kosu #62): adim "5 x HTTP 404" alip
# "KAYNAK KAPANDI -- 5 ardisik red" diyerek kendini kapatti ve
# "sektoru bulunan : 0" yazdi. Kuyruk alfabetik ve her kosuda AYNI
# ilk 25 sirketi deniyordu, yani 438 sirket KALICI olarak kilitliydi
# -- ve kosu her seferinde YESIL dondu.
#
# `bilanco_ag` bu ayrimi yillardir yapiyor ("404 sayaci ISLETMIYOR");
# buraya hic yayilmamisti.
#
# GUN SAYILARI MUTLAK YAZILIYOR.
#
# Ilk yazim `st.YENIDEN_DENEME_GUN + 1` diyordu ve bir MUTASYON
# kacti: sabit 100000'e cekilince sinama beklentisini de onunla
# birlikte kaydirdi. Beklentisini korudugu seyden okuyan sinama,
# mutasyonu sessizce yesil birakiyor.
print("")
print("Kaynakta olmayan sirket")

# --- 6a) GERCEK `sektor.cek`: 404 ile 429 AYRI ----------------------
#
# Asagidaki bolumler `sektor.cek`i yamaliyor, yani gercek ayrimi
# OLCMUYOR. Iki mutasyon tam buradan kacti (404 firlatmasi
# kaldirildi; 429 da "bulunamadi" sayildi). Ayrim BURADA, agsiz bir
# sahte istemciyle tutuluyor.
import httpx as _httpx                              # noqa: E402

class _SahteIstemci:
    def __init__(self, durum):
        self.durum = durum

    def get(self, u, **k):
        _httpx.Response(self.durum,
                        request=_httpx.Request("GET", u)).raise_for_status()


sektor.OKUNAMAYAN.clear()
_firladi = False
try:
    _GERCEK_CEK("X404", istemci=_SahteIstemci(404))
except sektor.Bulunamadi:
    _firladi = True
esit(_firladi, True, "gercek cek(): 404 Bulunamadi FIRLATIYOR")

_firladi = False
try:
    _bos = _GERCEK_CEK("X429", istemci=_SahteIstemci(429))
except sektor.Bulunamadi:
    _firladi = True
esit(_firladi, False, "gercek cek(): 429 Bulunamadi FIRLATMIYOR")
esit(_bos, {}, "gercek cek(): 429 bos sonuc donuyor")
esit([s for _k, s in sektor.OKUNAMAYAN], ["HTTP 404", "HTTP 429"],
     "iki durum da durum KODUYLA kaydedildi")

# --- 6b) ADIM KENDINI KAPATMIYOR -------------------------------------
_yok = ["A01", "A02", "A03", "A04", "A05"]
_sirketler = {k: {"kod": k} for k in _yok}
_sirketler["Z99"] = {"kod": "Z99"}
d = kur(_sirketler, {"Z99": {"sektor": "Industrials", "sektor_tr": "Sanayi"}},
        bulunamayanlar=_yok)
s = st.tazele(sinir=10)

esit(s["yazilan"], 1, "bes 404'tan SONRAKI sirkete ulasiliyor")
esit(s["bulunamayan"], 5, "bes sirket kaynakta YOK diye sayiliyor")
esit(s["hata"], 0, "404 HATA sayilmiyor")
_def = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(_def["Z99"]["sektor_tr"], "Sanayi", "son sirketin sektoru yazildi")
esit(all("sektor_bulunamadi" in _def[k] for k in _yok), True,
     "kaynakta yok isareti DEFTERE yazildi")
esit(any("sektor_tr" in _def[k] for k in _yok), False,
     "sektor alanina DOKUNULMADI -- uydurma yok")

# --- 6c) HICBIR SEY BULUNMASA DA ISARET YAZILIYOR --------------------
#
# Yazma kosulu `not kuru and yazilan` idi ve arizali senaryoda
# `yazilan` SIFIR: isaretler bellekte kalip kaybolacakti, yani
# duzeltme calismis GORUNUP hicbir sey degistirmeyecekti. Bir
# mutasyon eski kosulu geri koyunca 6b bunu goremedi -- cunku orada
# Z99 yaziliyor.
d = kur({k: {"kod": k} for k in _yok}, {}, bulunamayanlar=_yok)
s = st.tazele(sinir=10)
esit(s["yazilan"], 0, "KONTROL: bu senaryoda hic sektor yazilmiyor")
esit(s["bulunamayan"], 5, "bes sirket kaynakta YOK")
_def0 = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(all("sektor_bulunamadi" in _def0[k] for k in _yok), True,
     "yazilan SIFIR olsa da isaret DEFTERE yazildi")

# --- 6d) KUYRUK GERCEKTEN ILERLIYOR ---------------------------------
#
# Fark ancak IKINCI kosuda gorunuyor: ilk kosuda isaret henuz yok ve
# `eksik` ile `kuyruk` ayni. Bir mutasyon (`secilen = eksik[:sinir]`)
# tam bu yuzden kacti.
_d2 = json.loads(d.read_text(encoding="utf-8"))
esit(st.eksikler(_d2), sorted(_yok), "hepsi hala EKSIK olarak sayiliyor")
esit(st.kuyruk(_d2), [], "ama hicbiri artik SORULABILIR kuyrukta degil")

# IKINCI KOSU: isaretli besi ATLAYIP yeni sirkete ulasmali.
_ikinci = dict(_d2["sirketler"])
_ikinci["Z98"] = {"kod": "Z98"}
d = kur(_ikinci, {"Z98": {"sektor": "Industrials", "sektor_tr": "Sanayi"}},
        bulunamayanlar=_yok)
s = st.tazele(sinir=1)          # TEK sirket: sira dogruysa Z98 secilir
esit(s["yazilan"], 1, "ikinci kosu isaretlileri ATLAYIP yeniye geciyor")
esit(json.loads(d.read_text(encoding="utf-8"))["sirketler"]["Z98"]["sektor_tr"],
     "Sanayi", "ikinci kosuda yeni sirketin sektoru yazildi")

# --- 6e) ISARET KALICI DEGIL ----------------------------------------
#
# Gun sayilari MUTLAK; sabitten turetilmiyor (yukaridaki not).
import datetime as _dt                              # noqa: E402

esit(st.kuyruk(_d2, _dt.date.today() + _dt.timedelta(days=200)),
     sorted(_yok), "200 gun sonra yeniden sorulabilir")
esit(st.kuyruk(_d2, _dt.date.today() + _dt.timedelta(days=30)), [],
     "30 gun sonra henuz sorulmuyor")
# Sure MAKUL ARALIKTA: sifir isareti etkisiz kilar, cok buyuk olan
# sirketi sonsuza kadar gormezden gelir.
dogru_aralik = 7 <= st.YENIDEN_DENEME_GUN <= 365
esit(dogru_aralik, True,
     f"yeniden deneme suresi makul ({st.YENIDEN_DENEME_GUN} gun)")

# BOZUK ISARET KUYRUKTAN DUSURMEZ.
#
# "Bilmiyorum" ile "sonsuza kadar atla" ayni sey degil. Bir mutasyon
# bozuk tarihi `continue` ile atlatiyordu ve kimse gormuyordu: tek
# bir bozuk alan, sirketi kalici olarak gorus alanindan cikarirdi.
for _bozuk in ("abc", "", "2026-13-99", 20261031, None, []):
    _dd = {"sirketler": {"Q01": {"kod": "Q01",
                                 "sektor_bulunamadi": _bozuk}}}
    esit(st.kuyruk(_dd), ["Q01"],
         f"bozuk isaret ({_bozuk!r}) kuyrukta BIRAKIYOR")

# --- 6f) KONTROL: 429 ESKISI GIBI KAPATIYOR -------------------------
#
# 404 ayrimi, kisitlama korumasini GEVSETMEMELI.
_red = ["B01", "B02", "B03", "B04", "B05", "B06"]
_s2 = {k: {"kod": k} for k in _red}
_s2["Y99"] = {"kod": "Y99"}
d = kur(_s2, {"Y99": {"sektor": "Industrials", "sektor_tr": "Sanayi"}},
        reddedilenler=_red)
s = st.tazele(sinir=10)
esit(s["yazilan"], 0, "KONTROL: ardisik 429'da kosu DURUYOR")
esit(s["bulunamayan"], 0, "KONTROL: 429 'kaynakta yok' sayilmiyor")
_defr = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(any("sektor_bulunamadi" in v for v in _defr.values()), False,
     "KONTROL: 429 alan sirket ISARETLENMIYOR")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
