# -*- coding: utf-8 -*-
"""AYNI OLAYIN IKI SAYFASI OLMAMALI -- AMA ZIT HABER AYRILMALI.

BU DOSYA NEDEN VAR
------------------
`insa.tekilles` "ayni gun + BIREBIR ayni baslik" diyordu. Gercek
tekrarlarin basligi ise farkli: ayni olayi iki kaynak iki ayri
cumleyle yaziyor.

OLCULDU (2026-10-07), yayimlanmis 1.060 haber ikili karsilastirildi:

  >= 0,70   10 cift  -- hepsi gercek tekrar
  >= 0,60   17 cift  -- hepsi gercek tekrar
  >= 0,50   24 cift  -- hala dogru
  >= 0,48            -- ILK YANLIS (kuresel piyasalar / tarim disi)
  >= 0,44            -- "Borsa YUKSELISLE" ile "Borsa DUSUSLE"

Ornek gercek cift:

  "Kuresel piyasalar yogun veri gundemine odaklandi"      [AA]
  "Gelecek hafta kuresel piyasalar yogun veri gundemine"  [BloombergHT]

`haber_botu/tekrar_temizle.py` BU SINIFI GORMUYOR: olcum kipinde
873 grup buluyor ama "kaldirilacak sayfa dosyasi: 0" diyor -- cunku
birebir ayni baslik ayni slug'i uretiyor ve diskte zaten tek dosya.

UC OLCUT, UCU DE AYRI BIR YANLISI KESIYOR
-----------------------------------------
1. ORTUSME ESIGI 0,70. Esik 0,60 degil: bir haberi YANLISLIKLA
   dusurmek, tekrari birakmaktan agir.
2. SAYI UYUSMAZLIGI. Iki baslik da sayi tasiyip hicbiri ortak
   degilse ayri veri aciklamasidir: "TUFE: %29,73" ile
   "Yi-UFE: %27,38" ortusmesi 0,62 idi.
3. YON CELISKISI. Ilk kosuda "VIOP'ta endeks kontrati gune DUSUSLE
   basladi", "VIOP endeks kontrati gune YUKSELISLE basladi" ile
   0,77 verip ELENDI. Esigi yukseltmek cozmezdi: yanlis 0,77'de,
   yani gercek tekrarlarin (0,72 ve 0,74) USTUNDEYDI. Esik hangi
   degere cekilse ya yanlisi birakir ya dogruyu keserdi -- eksik
   olan esik degil OLCUTTU.

NE SINANMIYOR -- VE BU BILINCLI
-------------------------------
Gercek depo verisine bakilmiyor. Veri her kosuda degisiyor; ona
bagli bir sinama bir gun kendiliginden kirmizi doner ve urunde
hicbir kusur yoktur. Buradaki durumlar olculen GERCEK ciftlerden
yazildi ama sabit.
"""

from __future__ import annotations

import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import insa                                      # noqa: E402

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


def haber(baslik, gun, ozet="", an="", yol=""):
    return {"baslik": baslik, "tarih": gun, "ozet": ozet, "an": an or gun,
            "yol": yol}


print("")
print("Benzer haber elemesi")

# --- YON CELISKISI ---------------------------------------------------
esit(insa._yon_celiskisi("VIOP endeks kontrati gune yukselisle basladi",
                         "VIOP'ta endeks kontrati gune dususle basladi"),
     True, "yukselis/dusus celiskisi goruluyor")
esit(insa._yon_celiskisi("Borsa haftaya yukselisle basladi",
                         "Borsa gune dususle basladi"),
     True, "borsa yon celiskisi goruluyor")
esit(insa._yon_celiskisi("Enflasyon yukselisten dususe dondu",
                         "Enflasyon dususe gecti"),
     False, "iki yonu birden anan baslik celiski saymiyor")
esit(insa._yon_celiskisi("Hurmuz krizinde petrol kesintisi",
                         "Hurmuz krizinde enerji kesintisi"),
     False, "yon kelimesi yoksa celiski yok")
# Tuzak kelimeler: ikinci bir eslestirici yazilmadigi icin
# "karar" -> kar, "zaman" -> zam isareti URETMEMELI.
esit(insa._yon_isaretleri("Mahkeme kararini acikladi"), set(),
     "karar kelimesi yon isareti uretmiyor")
esit(insa._yon_isaretleri("Zaman zaman dalgalanma var"), set(),
     "zaman kelimesi zam isareti uretmiyor")

# --- SAYI UYUSMAZLIGI ------------------------------------------------
esit(insa._sayi_uyusmazligi("TUFE: %29,73", "Yi-UFE: %27,38"), True,
     "farkli sayilar ayri haber demek")
esit(insa._sayi_uyusmazligi("Pezeskiyan: mutabakata bagliyiz",
                            "17 Haziran'da imzaladigimiz mutabakat"), False,
     "tek tarafli sayi uyusmazlik sayilmiyor")
esit(insa._sayi_uyusmazligi("Kesinti yuzde 14'u buldu",
                            "Kesinti yuzde 14'u asti"), False,
     "ayni sayi uyusmazlik degil")

# --- ELEME ------------------------------------------------------------
_OZET = ("kuresel piyasalarda tahvil satis baskisi etkisiyle hafta "
         "satis agirlikli gecti yatirimcilar veri gundemini izliyor")
insa.BENZER_YONLENDIRME.clear()
_liste = [haber("Kuresel piyasalar yogun veri gundemine odaklandi",
                "2026-10-04", _OZET, "2026-10-04T08:00", "/haber/eski/"),
          haber("Gelecek hafta kuresel piyasalar yogun veri gundemine odaklandi",
                "2026-10-04", _OZET, "2026-10-04T09:00", "/haber/kalan/")]
_sonuc = insa._benzer_tekilles(_liste)
esit(len(_sonuc), 1, "ayni olayin ikinci sayfasi eleniyor")
esit(_sonuc[0]["an"], "2026-10-04T09:00", "en guncel surum kaliyor")

# ELENEN SAYFA 404 VERMEMELI.
#
# Eleme once yonlendirmesiz yayina cikti ve CANLIDA goruldu:
# /haber/kuresel-piyasalar-yogun-veri-gundemine-odaklandi/ -> 404.
# O sayfa yayindaydi; arama motoru biliyor, paylasilmis olabilir.
# `tekrar_temizle.py` kendi bas yorumunda tam bunu soyluyordu --
# ayni hatayi yeni bir yerde tekrarlamis olduk.
esit(insa.BENZER_YONLENDIRME.get("/haber/eski/"), "/haber/kalan/",
     "elenen sayfa icin yonlendirme yaziliyor")

_zit = [haber("VIOP endeks kontrati gune yukselisle basladi", "2026-10-04",
              "viop endeks kontrati seans basinda islem goruyor sozlesme", "a"),
        haber("VIOP'ta endeks kontrati gune dususle basladi", "2026-10-05",
              "viop endeks kontrati seans basinda islem goruyor sozlesme", "b")]
esit(len(insa._benzer_tekilles(_zit)), 2, "zit yonlu haber ELENMIYOR")

_sayi = [haber("TUFE: %29,73", "2026-10-04",
               "tuketici fiyat endeksi yillik degisim acikland istatistik kurumu", "a"),
         haber("Yi-UFE: %27,38", "2026-10-04",
               "tuketici fiyat endeksi yillik degisim acikland istatistik kurumu", "b")]
esit(len(insa._benzer_tekilles(_sayi)), 2, "farkli sayili veri haberi ELENMIYOR")

_uzak = [haber("Kuresel piyasalar yogun veri gundemine odaklandi",
               "2026-10-01", _OZET, "a"),
         haber("Gelecek hafta kuresel piyasalar yogun veri gundemine odaklandi",
               "2026-10-09", _OZET, "b")]
esit(len(insa._benzer_tekilles(_uzak)), 2, "gunu uzak haber elenmiyor")

# Esik, YALNIZCA ortusmeye bakildiginda olculen en kotu yanlisin
# (0,48) uzerinde olmali. 0,77'deki VIOP yanlisini esik DEGIL yon
# olcutu kesiyor -- ikisi ayri is ve ikisi de gerekli.
esit(insa.BENZER_ESIGI >= 0.60, True,
     "esik, olculen en kotu ortusme yanlisinin (0,48) uzerinde")

print("")
# --------------------------------------------------------------------
# ELEME YARIM UYGULANMAMALI -- gundem listesi de suzulmeli.
#
# OLCULDU (2026-11-21): `tekilles` elemesi yalnizca `uretilecek`e
# yansiyordu; gundem sablonu `gundem["haberler"]`i, yani ELENMEMIS
# listeyi geziyordu. Iki sonucu vardi:
#
#   1. Elenen haberin `yol`u elemeden ONCE atandigi icin karti
#      baglantisini koruyor, sayfasi hic uretilmiyordu --
#      `test_kirik_baglanti` kirmizi dondu ve DAGITIM 4,5 SAAT
#      kilitlendi (120 gundem haberinin 2'si eleniyordu, biri
#      kartli: tam olarak bir kirik baglanti).
#   2. Elemenin AMACI bosa cikiyordu: gerekce "okur ayni haberi
#      listede uc kez gormesin" ama liste onlari gosteriyordu.
#
# NEDEN AYLARCA SESSIZ KALDI: tam kopya elendiginde hayatta kalan
# ikizin basligi AYNI, yani slug de ayni -- baglanti cozuluyor.
# BENZERLIK elemesinde (esik 0.70) basliklar FARKLI, slug farkli ve
# baglanti bosa dusuyor. Yani kusuru ancak bu dosyanin konusu olan
# eleme turu tetikliyor.
#
# OLCUT AST -- metin degil: bu dosyanin ve `insa.py`nin kendi
# aciklamalari `tekilles`, `uretilecek`, `gundem` adlarini
# tasiyor. Metin aramasi kendi yorumunu yakalardi; bu depoda ayni
# tuzaga iki kez dusuldu.
import ast                                              # noqa: E402

_kaynak = (_SITE / "insa.py").read_text(encoding="utf-8")
_agac = ast.parse(_kaynak)


def _tekilles_atamasi(agac):
    """`X = tekilles(...)` atamalarini ve kapsayan govdeyi dondurur."""
    for dugum in ast.walk(agac):
        govde = getattr(dugum, "body", None)
        if not isinstance(govde, list):
            continue
        for i, st in enumerate(govde):
            if not isinstance(st, ast.Assign):
                continue
            d = st.value
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                    and d.func.id == "tekilles"):
                yield govde, i, st


_bulunan = list(_tekilles_atamasi(_agac))
# ATILLIK: tarama hicbir atama bulmazsa asagidaki iddia BEDAVA gecer.
esit(len(_bulunan) >= 1, True,
     f"insa.py icinde tekilles atamasi var ({len(_bulunan)})")

for _govde, _i, _st in _bulunan:
    _ad = _st.targets[0].id if isinstance(_st.targets[0], ast.Name) else ""
    # Ayni govdede, ATAMADAN SONRA `gundem["haberler"]` yeniden
    # atanmali ve atanan deger elenmis kumeye BAGLI olmali.
    _suzuldu = False
    for _sonraki in _govde[_i + 1:]:
        if not isinstance(_sonraki, ast.Assign):
            continue
        _h = _sonraki.targets[0]
        if not (isinstance(_h, ast.Subscript)
                and isinstance(_h.value, ast.Name)
                and _h.value.id == "gundem"
                and isinstance(_h.slice, ast.Constant)
                and _h.slice.value == "haberler"):
            continue
        _adlar = {n.id for n in ast.walk(_sonraki) if isinstance(n, ast.Name)}
        # Dogrudan `uretilecek`e ya da ondan turetilen bir kumeye
        # bakmali. Ikisini de kabul etmek bicime degil BAGLILIGA
        # bakmak demek.
        if _ad in _adlar or "_kalan" in _adlar:
            _suzuldu = True
            break
    esit(_suzuldu, True,
         f"`{_ad}` elemesinden sonra gundem listesi de suzuluyor")


print(f"TUM TESTLER GECTI ({_gecti})")
