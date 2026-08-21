"""Takvimdeki bir yayin ACIKLANDI MI, aciklandiysa ne cikti.

    yayin (kod + saat)  ->  depodaki gozlem  ->  gerceklesen + surpriz

NEDEN KAYIT ANINA BAKILIYOR, TARIHE DEGIL
-----------------------------------------
`gosterge.tarih` verinin AIT OLDUGU donem: Temmuz TUFE'sinin tarihi
2026-07-01'dir, halbuki 12 Agustos'ta aciklanir. Yayin saatiyle
karsilastirilacak alan bu degil, `kayit_ani` -- verinin BIZE ne zaman
ulastigi.

Tarihe bakilsaydi her yayin "coktan aciklanmis" gorunurdu, cunku
donem tarihi yayin tarihinden her zaman once gelir.

SURPRIZ NEYE GORE
-----------------
Beklentiye gore. Beklenti yoksa surpriz de YOK -- onceki degere gore
"surpriz" hesaplamak, olcutu degistirip ayni adi kullanmak olurdu.
Okur "surpriz" gorunce konsensusa gore sapmayi anlar.

ACIKLANMAMIS VERI ACIKLANMIS GIBI GOSTERILMIYOR
-----------------------------------------------
Kural net: gozlem yoksa ya da gozlem yayin saatinden ONCE
kaydedilmisse, o yayin ACIKLANMAMIS sayiliyor. Yaklasan bir veriye
uydurma bir "gerceklesen" yazmak, takvimin tek isini -- ne zaman ne
cikacagini soylemeyi -- ters cevirirdi.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import sqlite3

DEPO = pathlib.Path(__file__).resolve().parent.parent / "haber_botu" / "netaris.db"

#: Yayin saatinden sonra kac saat icinde gelen gozlem o yayina sayilir.
#:
#: 48 secildi: kurum bazen saatinde yayimlamiyor, bizim hattimiz da
#: yarim saatte bir kosuyor. Daha dar bir pencere gecikmis yayini
#: kaciracak; daha genis olan BIR SONRAKI donemin gozlemini yanlislikla
#: bu yayina baglayabilir.
PENCERE_SAAT = 48


def _baglan():
    if not DEPO.exists():
        return None
    try:
        b = sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True)
        b.row_factory = sqlite3.Row
        return b
    except sqlite3.Error:
        return None


def gerceklesen(kod: str, an: _dt.datetime, b=None) -> dict | None:
    """`an`de yayimlanmasi beklenen serinin gerceklesen degeri.

    Doner: {"deger": float, "donem": str} ya da None.

    None, "aciklanmadi" demek -- ve bu bir eksiklik degil, takvimin
    normal durumu. Yaklasan verilerin cogu henuz aciklanmamistir.
    """
    if not kod:
        return None
    kapat = b is None
    b = b or _baglan()
    if b is None:
        return None
    try:
        alt = an.astimezone(_dt.timezone.utc).replace(tzinfo=None)
        ust = alt + _dt.timedelta(hours=PENCERE_SAAT)
        s = b.execute(
            "SELECT deger, tarih FROM gosterge "
            "WHERE kod = ? AND kayit_ani >= ? AND kayit_ani <= ? "
            "ORDER BY tarih DESC, kayit_ani DESC LIMIT 1",
            (kod, alt.isoformat(sep=" "), ust.isoformat(sep=" "))).fetchone()
        if s is None:
            return None
        return {"deger": float(s["deger"]), "donem": s["tarih"]}
    except (sqlite3.Error, TypeError, ValueError):
        return None
    finally:
        if kapat:
            b.close()


def surpriz(gercek: float | None, beklenti: float | None) -> dict | None:
    """Gerceklesenin beklentiye gore sapmasi.

    Doner: {"fark": float, "yon": "ust"|"alt"|"tam"} ya da None.

    Beklenti YOKSA None: onceki degere gore "surpriz" hesaplamak,
    olcutu degistirip ayni adi kullanmak olurdu.
    """
    if gercek is None or beklenti is None:
        return None
    f = gercek - beklenti
    # Sifira cok yakin fark "tam isabet" sayiliyor: kayan nokta
    # artiklarini surpriz diye sunmak yanlis olurdu.
    if abs(f) < 1e-9:
        return {"fark": 0.0, "yon": "tam"}
    return {"fark": f, "yon": "ust" if f > 0 else "alt"}


def _tr(d: float, basamak: int = 2) -> str:
    """Turkce sayi: ondalik ayraci VIRGUL.

    Bicimlendirme SABLONDA degil burada: sablon hesap yapmamali,
    yalnizca basmali. Ayrica ayni sayi iki yerde farkli
    bicimlenirse okur hangisinin dogru oldugunu bilemez.
    """
    return f"{d:,.{basamak}f}".replace(",", " ").replace(".", ",")


def kutuya_ekle(kutu: dict, b=None) -> dict:
    """Takvim kutusuna `gerceklesen` ve `surpriz` alanlarini ekler.

    Kutu YERINDE degistiriliyor ve geri donuyor. Aciklanmamis veri
    icin alanlar eklenmiyor -- sablon `{% if %}` ile bakiyor ve
    olmayan alan "henuz aciklanmadi" demek.
    """
    kod = kutu.get("seri")
    an_metin = kutu.get("an")
    if not kod or not an_metin:
        return kutu
    try:
        an = _dt.datetime.fromisoformat(an_metin)
    except ValueError:
        return kutu

    g = gerceklesen(kod, an, b)
    if g is None:
        return kutu
    g["metin"] = _tr(g["deger"])
    kutu["gerceklesen"] = g

    # BEKLENTI SOZLUK OLMAYABILIR. Hat onu bir NESNE olarak koyuyor
    # (`beklenti.Kutu`); `.get()` cagirmak AttributeError veriyordu ve
    # bu, surpriz alaninin sessizce hic uretilmemesine yol aciyordu --
    # cokme degil, EKSIKLIK olarak gorunuyordu.
    #
    # Ikisi de destekleniyor: hangi bicimde gelirse gelsin okunuyor.
    bek = kutu.get("beklenti")

    def _al(ad, varsayilan=""):
        if bek is None:
            return varsayilan
        if isinstance(bek, dict):
            return bek.get(ad, varsayilan)
        return getattr(bek, ad, varsayilan)

    # Surpriz YALNIZCA gercek konsensus varken hesaplaniyor. Esik
    # onceki degerse (`esik_kaynak != "beklenti"`) surpriz yazilmiyor.
    if _al("esik_kaynak") == "beklenti":
        try:
            e = float(str(_al("esik_deger")).replace(",", "."))
        except (TypeError, ValueError):
            return kutu
        s = surpriz(g["deger"], e)
        if s:
            s["metin"] = _tr(abs(s["fark"]))
            kutu["surpriz"] = s
    return kutu
