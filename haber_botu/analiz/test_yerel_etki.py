"""Aktarim kanali -- KENDI PIYASASI ONCE, TURKIYE SONRA.

BU DOSYA NEDEN VAR
------------------
Kanal yalnizca Turkiye uclarina cikiyordu (`YEREL_UC`). Bir Alman
enflasyon haberinin gidecegi tek yer USDTRY ya da BIST100'du; okurun
ilk sorusu -- "bu Avrupa'da neyi etkiler" -- hic cevaplanmiyordu.
Almanya haberinde DAX yoktu, Japonya haberinde Nikkei yoktu.

Daha kotusu: agda DAX, Nikkei, FTSE, EURUSD, Bund, ECB faizi HICBIRI
YOKTU. Yani kanal yalnizca dar degildi, cogu yabanci haberde HIC
CALISMIYORDU -- olculdu, sifir sayfada gorunuyordu.

Yerel bakis yanlis degil, Turk okur icin gerekli. Ama TEK bakis
olmasi, kuresel bir olayi dar bir mercekten anlatmak demekti.

SINAMALAR IKI SEYI TUTUYOR
--------------------------
1. Her ulkenin kendi piyasa uclari var ve kanal oraya varabiliyor.
2. Turkiye kanali BOZULMADI -- yeni yol eskisini gotürmemeli.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from analiz import graf_tohum, yerel_etki as ye  # noqa: E402

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


def bellek_depo() -> sqlite3.Connection:
    """Tohumdan kurulan BELLEK ICI graf.

    Depoya bagli sinama, depo bozuksa sessizce atlanir. Tohum
    dogrudan okunuyor: sinanan sey `graf_tohum` + `yerel_etki`
    ikilisi, veritabaninin o anki hali degil.
    """
    b = sqlite3.connect(":memory:")
    b.execute("""CREATE TABLE bag (kaynak TEXT, hedef TEXT, tur TEXT,
                 dayanak TEXT, guc INTEGER, aciklama TEXT)""")
    b.executemany("INSERT INTO bag VALUES (?,?,?,?,?,?)",
                  [(k, h, t, d, g, a) for k, h, t, d, g, a in graf_tohum.BAGLAR])
    return b


B = bellek_depo()


def zincir(baslangic, ulke, kendi):
    yol = ye.kanal(B, baslangic, ye.uclar(ulke), kendi_piyasasi=kendi)
    if not yol:
        return None
    return [yol[0]["kaynak"]] + [a["hedef"] for a in yol]


# --------------------------------------------------------------------
# KURESEL PIYASA UCLARI TANIMLI.
#
# Bu liste bos kalirsa kanal sessizce Turkiye'ye geri doner ve hicbir
# hata gorunmez -- tam da duzeltilen durum.
# --------------------------------------------------------------------
print("\nHer bolgenin kendi piyasa ucleri var")
for ulke, beklenen in (("EU", "DAX"), ("JP", "NIKKEI"), ("GB", "FTSE"),
                       ("US", "SP500"), ("CN", "XCU"), ("TR", "BIST100")):
    esit(beklenen in ye.uclar(ulke), True, f"{ulke} uclarinda {beklenen}")

# --------------------------------------------------------------------
# IKI SOZLUK AYNI ULKE KODLARINI KULLANMALI.
#
# EN ONEMLI SINAMA -- cunku tam bu hata yapildi.
#
# `PIYASA_UCLARI` ilk yazimda Euro Bolgesi icin "EA" kullaniyordu;
# `baglam` ise "EU" donduruyor. Sonuc: `uclar("EU")` BOS donuyordu ve
# YENI YAZILMIS BUTUN AVRUPA KANALI hic ateslenmiyordu. Kod calisti,
# testler gecti, hicbir hata gorunmedi -- ozellik olu dogdu.
#
# Bu depoda ayni sinif sessiz uyusmazlik birkac kez cikti (JS/Python
# diakritik tablolari, `_stem` ile kavram metni). Ortak yani: iki yerde
# tutulan bir sozluk, zamanla ayrisiyor ve ayrisma HATA VERMIYOR.
# --------------------------------------------------------------------
print("\nUlke kodlari iki sozlukte de ayni")
from analiz import baglam  # noqa: E402

_baglam_kodlari = (set(baglam.KURUM_ULKE.values())
                   | {u for _, u in baglam.BASLIK_ULKE}
                   | {u for _, u in baglam.ULKE_ADLARI})
_bilinmeyen = sorted(set(ye.PIYASA_UCLARI) - _baglam_kodlari)
esit(_bilinmeyen, [],
     "PIYASA_UCLARI'ndaki her kod baglam tarafindan URETILEBILIYOR")

# Ters yon UYARI DEGIL: baglam 24 ulke tanıyor, hepsinin piyasa ucu
# olmasi gerekmiyor (Cekya haberinde Prag borsasi anlatmiyoruz).
# Onemli olan, tanimladigimiz her ucun ULASILABILIR olmasi.

# Tanimsiz ulkede BOS donmeli: bilmedigimiz bir ulke icin Turkiye
# ucuna zorlamak, haberi olmadigi bir sey hakkinda anlatmak olurdu.
esit(ye.uclar("XX"), frozenset(), "tanimsiz ulke BOS uc donduruyor")
esit(ye.uclar(None), frozenset(), "ulke yoksa BOS")
esit(ye.kanal(B, ["FED_FAIZ"], frozenset()), None, "bos hedefte kanal YOK")

# --------------------------------------------------------------------
# KENDI PIYASASINA ULASIYOR.
#
# EN ONEMLI SINAMA: bunlar eskiden HEPSI None donuyordu, cunku hedef
# dugumleri agda YOKTU.
# --------------------------------------------------------------------
print("\nKendi piyasasina ulasan zincirler")
for ad, bas, ulke in (("Euro Bölgesi TÜFE", ["EA_TUFE"], "EU"),
                      ("ECB faizi", ["ECB_FAIZ"], "EU"),
                      ("BoJ faizi", ["BOJ_FAIZ"], "JP"),
                      ("Çin büyümesi", ["CN_BUYUME"], "CN"),
                      ("Fed faizi", ["FED_FAIZ"], "US")):
    z = zincir(bas, ulke, True)
    esit(z is not None, True, f"{ad} kendi piyasasina ulasiyor: {z}")

# --------------------------------------------------------------------
# BASLANGIC KENDI HEDEFINE DONMUYOR.
#
# `kendi_piyasasi` bayragi baslangici hedeften cikariyor; yoksa zincir
# "ECB faizi -> ECB faizi" gibi bir sey uretebilirdi.
# --------------------------------------------------------------------
print("\nZincir kendi uzerine donmuyor")
z = zincir(["ECB_FAIZ"], "EU", True)
esit(z[-1] != "ECB_FAIZ", True, "son uc baslangictan FARKLI")
esit(len(set(z)), len(z), "zincirde tekrar eden dugum yok")

# --------------------------------------------------------------------
# TURKIYE KANALI BOZULMADI.
#
# Yeni yol eskisini goturmemeli. Ayrica Turkiye hedefinde eski
# davranis korunuyor: haber ZATEN yurt ici bir varliga bagliysa kanal
# gosterilmiyor (sayfa onu dogrudan gosteriyor).
# --------------------------------------------------------------------
print("\nTurkiye kanali korunuyor")
for ad, bas in (("Fed faizi", ["FED_FAIZ"]), ("ECB faizi", ["ECB_FAIZ"]),
                ("Euro Bölgesi TÜFE", ["EA_TUFE"]), ("Brent", ["BRENT"])):
    z = zincir(bas, "TR", False)
    esit(z is not None, True, f"{ad} -> Turkiye: {z}")
    if z:
        esit(z[-1] in ye.YEREL_UC, True, f"{ad} zinciri yurt ici ucta bitiyor")

esit(zincir(["USDTRY"], "TR", False), None,
     "zaten yurt ici varlikta kanal GOSTERILMIYOR")

# --------------------------------------------------------------------
# HER KENAR GEREKCELI.
#
# Gerekcesi olmayan bir ok okura "bir sekilde etkiliyor" demekten
# baska bir sey soylemez. `_kenarlar` aciklamasiz kenari zaten
# eliyor; burada YENI eklenen kenarlarin gerekcesiz olmadigi
# siniyor -- eksik gerekce sessizce zinciri kisaltir.
# --------------------------------------------------------------------
print("\nZincirdeki her adimin gerekcesi var")
for bas, ulke, kendi in ((["EA_TUFE"], "EU", True), (["BOJ_FAIZ"], "JP", True),
                         (["FED_FAIZ"], "TR", False)):
    yol = ye.kanal(B, bas, ye.uclar(ulke), kendi_piyasasi=kendi)
    if not yol:
        continue
    bos = [a for a in yol if not (a["aciklama"] or "").strip()]
    esit(bos, [], f"{bas[0]} -> {ulke}: her adimda gerekce var")

# --------------------------------------------------------------------
# HICBIR BAGDA YON YOK.
#
# `graf_tohum` bas yorumundaki kural: "etkiler" var, "yukseltir" yok.
# "Fed faiz artirirsa altin duser" yanlis bir genellemedir -- 2022'de
# faiz de altin da yukseldi. Yeni eklenen kuresel baglar da bu kurala
# uymali.
# --------------------------------------------------------------------
print("\nBaglarda yon yok")
_YON = ("yukselt", "dusur", "azalt", "artir", "guclend", "zayiflat")
kusurlu = [(k, h) for k, h, t, *_ in graf_tohum.BAGLAR
           if any(y in t for y in _YON)]
esit(kusurlu, [], "hicbir bag turu YON bildirmiyor")

# Yeni dugumlerin hepsi VARLIKLAR icinde tanimli olmali; tanimsiz
# dugume isaret eden bag sessizce hicbir sey yapmaz.
kodlar = {v[0] for v in graf_tohum.VARLIKLAR}
yetim = sorted({k for k, h, *_ in graf_tohum.BAGLAR if k not in kodlar}
               | {h for k, h, *_ in graf_tohum.BAGLAR if h not in kodlar})
esit(yetim, [], "her bag TANIMLI dugumlere isaret ediyor")

# VARLIK KODU BENZERSIZ OLMALI.
#
# Kuresel dugumleri eklerken EURUSD'yi ikinci kez tanimladim ve
# `varlik.kod` benzersizlik kisiti dustu -- `test_varlik.py` yakaladi.
# Kontrol buraya da konuyor cunku sorun `graf_tohum`da: tohum listesi
# buyuduce ayni sey yeniden olur ve hangi sinamanin yakalayacagi
# tesadufe kalmamali.
import collections as _c  # noqa: E402

_say = _c.Counter(v[0] for v in graf_tohum.VARLIKLAR)
esit([k for k, n in _say.items() if n > 1], [], "varlik kodlari BENZERSIZ")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
