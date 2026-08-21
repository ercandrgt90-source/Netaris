"""Veri TAZELIGI -- seri kendi yayim ritminin gerisinde mi.

NEDEN HAM YAS YANLIS OLCUT
--------------------------
Ilk olcumumde "45 gunden eski seri" diye baktim ve 24 seri cikti. Ama
liste yaniltiyordu: aylik TUFE'nin Temmuz verisi 1 Temmuz etiketiyle
duruyor ve Agustos'ta yayimlaniyor -- 52 gunluk gorunuyor ve TAMAMEN
NORMAL. Ceyreklik GSYH 143 gun "eski" ve o da normal.

Ham yasa bakan bir uyari, dogru calisan serileri sikayet eder ve kisa
surede gormezden gelinir. Dogru soru: seri KENDI RITMININ gerisinde mi.

FREKANS VERIDEN CIKIYOR, ELLE YAZILMIYOR
----------------------------------------
Her seri icin son gozlemlerin arasindaki medyan gun farki hesaplaniyor
ve frekans oradan turuyor. Elle tutulan bir frekans tablosu, yeni seri
eklendiginde unutulmak uzere kurulmus demektir -- bu depoda ayni hata
daha once test listesinde yasandi.

Medyan kullaniliyor, ortalama degil: tek bir tatil bosluğu ortalamayi
kaydiriyor, medyani kaydirmiyor.

OLCULEN
-------
Ilk calistirmada yedi seri ritminin gerisindeydi. Bir tanesi gercek
ariza: DEXUSEU (EUR/USD) GUNLUK bir seri ama son verisi 22 gunluktu.
Bayat bir kur, "guncel veriler" basligi altinda gorunuyordu.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import sqlite3
import statistics

DEPO = pathlib.Path(__file__).resolve().parent.parent / "netaris.db"

#: Frekans -> tavan icin YEDEK degerler.
#:
#: Yalnizca serinin kendi gecmisi olculemedigi durumda kullaniliyor.
#: Asil olcut asagida: serinin KENDI yayim gecikmesi.
TAVAN = {"gunluk": 7, "haftalik": 14, "aylik": 70,
         "ceyreklik": 190, "olay": 190}

#: Olculen gecikmenin ustune eklenen pay (gun). Yayim bir kac gun
#: kayabiliyor; paysiz bir tavan her normal kaymayi uyari yapardi.
PAY = 10

#: Frekans -> bir periyodun gun karsiligi.
#:
#: TAVANA EKLENIYOR ve sebebi ince: iki yayim ARASINDA en yeni gozlem
#: dogal olarak bir periyot yaslaniyor. TUFE'nin Temmuz verisi 3
#: Agustos'ta cikiyor ve Eylul basina kadar EN TAZESI olarak kaliyor --
#: o sirada yasi 34 gunden 64 gune tirmaniyor ve hicbir sey bozulmuyor.
#:
#: Periyodu eklemeyen ilk surumum TUFE, YI-UFE ve issizligi "bayat"
#: gosterdi. Ucu de dogru calisiyordu; olcut yanlisti.
PERIYOT = {"gunluk": 1, "haftalik": 7, "aylik": 31,
           "ceyreklik": 92,
           # Olaya bagli seride "bir sonraki" ne zaman gelecegi
           # bilinmiyor; en genis pay veriliyor ki karar
           # alinmayan bir donem uyari uretmesin.
           "olay": 92}

#: Medyan gun farki -> frekans adi.
_ESIK = ((4, "gunluk"), (10, "haftalik"), (40, "aylik"))


#: Araliklarin degiskenlik katsayisi bu esigi asarsa seri DUZENLI
#: sayilmiyor.
#:
#: Olculdu -- ayrim keskin:
#:     TUFE            0,03   (30/31/30/31...)
#:     GSYH            0,01   (90/92/92/91...)
#:     Fed fonu        0,00   (1/1/1/1...)
#:     TCMB politika   1,37   (224/49/42/49/35/63...)
#:
#: Sonuncusu bir takvime degil TOPLANTIYA bagli. Onu "ceyreklik" sayip
#: "2026 3. ceyrek" diye yazmak yanlis: faiz bir ceyregin verisi degil,
#: BELIRLI BIR GUN alinan bir karar.
DUZENSIZ_ESIGI = 0.30


#: Duzenlilik testi yalnizca bu esikten UZUN araliklarda uygulaniyor.
#:
#: Degiskenlik katsayisi kisa periyotta anlamsiz: gunluk bir seride
#: hafta sonu boslugu [1, 1, 3, 1, 1] uretiyor ve oran 0,8 cikiyor --
#: yani duzenli calisan bir seri "olaya bagli" sayiliyor. Ilk yazimimda
#: bu oldu ve sinama yakaladi.
#:
#: Aylik ve daha uzun serilerde ayni bosluk oransal olarak kucuk kaliyor
#: ve test anlamli hale geliyor.
DUZENLILIK_ALT_SINIRI = 10


def duzenli_mi(gunler: list[int]) -> bool:
    """Seri sabit bir takvimde mi yayimlaniyor, yoksa olaya mi bagli."""
    if len(gunler) < 3:
        return True                      # olcemiyoruz: varsayilan duzenli
    m = statistics.median(gunler)
    if m <= DUZENLILIK_ALT_SINIRI:
        # Gunluk/haftalik seri: tatil ve hafta sonu bosluklari normal.
        return True
    return (statistics.pstdev(gunler) / m) <= DUZENSIZ_ESIGI


def frekans(gunler: list[int]) -> str:
    """Gozlem araliklarindan frekans adi.

    Duzensiz seriler "olay" donuyor: donem etiketi yerine GUN
    yazilsin diye. Bkz. `DUZENSIZ_ESIGI`.
    """
    if not gunler:
        return "ceyreklik"
    if not duzenli_mi(gunler):
        return "olay"
    m = statistics.median(gunler)
    for esik, ad in _ESIK:
        if m <= esik:
            return ad
    return "ceyreklik"


def _tarihler(b: sqlite3.Connection, kod: str, n: int = 14) -> list[_dt.date]:
    r = b.execute("SELECT tarih FROM gosterge WHERE kod = ?"
                  " ORDER BY tarih DESC LIMIT ?", (kod, n)).fetchall()
    cikti = []
    for (t,) in r:
        try:
            cikti.append(_dt.date.fromisoformat(t[:10]))
        except (ValueError, TypeError):
            continue
    return cikti


def yayim_gecikmesi(b: sqlite3.Connection, kod: str) -> int | None:
    """Serinin KENDI yayim gecikmesi -- gecmisimizden olculuyor.

    NEDEN SABIT TAVAN YETMIYOR
    --------------------------
    Ilk surumde frekans basina sabit tavan kullandim ("aylik -> 70
    gun") ve sinama uc seriyi bayat gosterdi: TUIK issizligi, cari
    islemler ve cekirdek PCE. Ucu de DOGRU calisiyordu -- TUIK
    issizligi yaklasik IKI AY gecikmeyle yayimlaniyor ve 70 gunluk
    tavan onu her ay sikayet ederdi.

    Bir uyari, dogru calisan seriyi sikayet ettigi anda gormezden
    gelinmeye baslar. Tavan tahmin edilmemeli, OLCULMELI.

    NEDEN EN KUCUK, MEDYAN DEGIL
    ----------------------------
    `kayit_ani` toplu yazimda butun gozlemlere AYNI damgayi basiyor,
    yani eski gozlemler devasa "gecikme" gosteriyor. Medyan bu yuzden
    sisiyor (issizlikte 200 gun). EN KUCUK fark, gozlemin ILK
    goruldugu andaki gercek gecikmeye en yakin deger -- olculdu:

        TUFE            34 gun   (aylik, ay sonrasi yayim)
        ABD issizlik    37 gun
        TUIK issizlik   64 gun   (iki ay -- sabit tavan bunu kaciriyordu)
        Dolar endeksi    3 gun   (gunluk)

    Dordu de gercek yayim takvimiyle ortusuyor.
    """
    r = b.execute(
        "SELECT tarih, kayit_ani FROM gosterge WHERE kod = ?"
        " ORDER BY tarih DESC LIMIT 12", (kod,)).fetchall()
    farklar = []
    for t, ka in r:
        try:
            g = (_dt.date.fromisoformat(ka[:10])
                 - _dt.date.fromisoformat(t[:10])).days
        except (ValueError, TypeError):
            continue
        if g >= 0:
            farklar.append(g)
    return min(farklar) if farklar else None


def seri_durumu(b: sqlite3.Connection, kod: str,
                bugun: _dt.date | None = None) -> dict | None:
    """Serinin frekansi, yasi ve gecikmesi. Olcemiyorsa None.

    Dort gozlemden az olan seride frekans olculemiyor -- tahmin edip
    uyari uretmek, olculmemis bir yargi olurdu.
    """
    d = _tarihler(b, kod)
    if len(d) < 4:
        return None
    bugun = bugun or _dt.date.today()
    farklar = [(d[i] - d[i + 1]).days for i in range(len(d) - 1)]
    f = frekans(farklar)
    yas = (bugun - d[0]).days
    olculen = yayim_gecikmesi(b, kod)
    tavan = ((olculen + PERIYOT[f] + PAY) if olculen is not None
             else TAVAN[f])
    return {
        "kod": kod,
        "frekans": f,
        "son_tarih": d[0].isoformat(),
        "yas": yas,
        "tavan": tavan,
        "olculen_gecikme": olculen,
        "gecikme": max(0, yas - tavan),
        "bayat": yas > tavan,
    }


def bayat_seriler(b: sqlite3.Connection,
                  bugun: _dt.date | None = None) -> list[dict]:
    """Ritminin gerisinde kalan seriler, en cok gecikenden baslayarak."""
    cikti = []
    for (kod,) in b.execute("SELECT DISTINCT kod FROM gosterge"):
        d = seri_durumu(b, kod, bugun)
        if d and d["bayat"]:
            cikti.append(d)
    return sorted(cikti, key=lambda x: -x["gecikme"])


def donem_etiketi(tarih: str, frekans_adi: str) -> str:
    """Veri DONEMINI okunur yazar -- yayin tarihinden ayrilsin diye.

    Okur icin "2026-07-01" bir gun gibi gorunuyor; oysa aylik seride o
    TEMMUZ AYININ verisi. Gun gibi okunan bir donem etiketi, haberin
    yayin tarihiyle karistiriliyor -- editoryal geri bildirimde
    bildirilen sorun tam buydu:

        olay tarihi   29 Temmuz  (Fed toplantisi)
        veri donemi   Temmuz 2026
        yayin tarihi  20 Agustos (tutanaklarin cikisi)

    Uc ayri sey ve ucu de farkli bir soruyu cevapliyor.
    """
    try:
        d = _dt.date.fromisoformat(tarih[:10])
    except (ValueError, TypeError):
        return tarih
    AY = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
    if frekans_adi == "aylik":
        return f"{AY[d.month - 1]} {d.year}"
    if frekans_adi == "ceyreklik":
        return f"{d.year} {(d.month - 1) // 3 + 1}. çeyrek"
    return f"{d.day} {AY[d.month - 1]} {d.year}"
