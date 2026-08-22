"""Senaryo KAPISI -- yargilamaz, DOGRULANABILIR ozellikleri denetler.

NEDEN "AI KALITE PUANI" DEGIL
-----------------------------
Kullanici kalite katmanlarini yapay zeka performansina baglamayi sordu.
Modele "bu senaryo kaliteli mi" sorup gorunur bir rozet vermek YANLIS
olurdu ve bu depo ayni konuda iki kez karar verdi:

    "Guven Skoru %83"  -> reddedildi
    "Veri Gucu 97"     -> kaldirildi

Gerekce her ikisinde de ayni: hesaplanmamis bir yargiyi olcum gibi
sunmak. Modelin "iyi senaryo" demesi tekrarlanabilir degil, iki
calistirmada farkli cikabilir ve okur onu bir derecelendirme sanir.

BUNUN YERINE: DOGRULANABILIR OZELLIKLER
---------------------------------------
Kapi bir yargi uretmiyor, OLCULEBILIR sorular soruyor:

    Kosul yanlislanabilir mi?   (esik/karsilastirma iceriyor mu)
    Gerekce bos mu?
    Sayilar sitenin verisinde geciyor mu?
    Yatirim tavsiyesi dili var mi?

Hepsinin cevabi EVET/HAYIR ve her cevap gosterilebilir. "Bu senaryo
iyi" demiyoruz; "bu senaryonun kosulu yanlislanabilir" diyoruz -- ve
okur isterse kendisi bakar.

YANLISLANABILIRLIK NEDEN MERKEZDE
---------------------------------
Sonucu olculemeyen bir senaryo hicbir zaman sonuclanamaz; sonuclanmayan
senaryo sicil olusturamaz; sicil olmadan katman kurulamaz.

    "Piyasalar dalgalanabilir"        -> hicbir zaman yanlislanmaz
    "TUFE %30'un altina inerse"       -> Eylul'de bakilir, cevap belli

Yani butun katman sisteminin temeli bu tek ozellik.

KAPI ENGELLEMIYOR, ISARETLIYOR
------------------------------
Yalnizca yatirim tavsiyesi dili YAYINI ENGELLIYOR (yasal). Digerleri
bir NOT: yazara "kosulunuz yanlislanabilir degil" denir, yazar duzeltir
ya da duzeltmez. Zayif senaryoyu yasaklamak yerine gorunur kilmak,
toplulugu kendi standardini kurmaya birakiyor.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
import sys

_KOK = pathlib.Path(__file__).resolve().parent
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

DEPO = _KOK.parent / "netaris.db"

#: Kosulu YANLISLANABILIR yapan isaretler.
#:
#: Uc aile: sayisal esik, karsilastirma, ve tarihli olay. Ucu de
#: "ne zaman bakacagiz, neye bakacagiz" sorusunu cevapliyor.
#:
#: Liste tam degil ve olmasi da gerekmiyor: eksik isaret yalnizca bir
#: NOT uretiyor, yayini engellemiyor.
_ESIK = re.compile(
    r"%\s?\d|"                                  # yuzde esigi
    r"\d+[.,]?\d*\s*(?:puan|bp|baz puan|dolar|tl|\$|₺|milyar|milyon)|"
    r"\b(?:üzerin|altın|üstün|aşar|geçer|iner|düşer|çıkar|kalır)"
    r"(?:d[ae]|a|e)?\b|"                        # karsilastirma fiilleri
    r"\b(?:artır|indir|sabit tut|açıkla|onayla|imzala|kapan)"
    r"(?:ır|ir|ur|ür|ar|er)?sa\b",              # kosul kipi
    re.I)

#: Yanlislanabilirligi ZAYIFLATAN kaliplar -- kacamak dil.
_BULANIK = re.compile(
    r"\b(?:dalgalan|belirsiz kal|etkilen|hareketlen|değişebil|olabil)"
    r"[a-zçğıöşü]*\b", re.I)

#: Ondalikli sayilar -- gerekcedeki sayilarin dogrulanmasi icin.
_SAYI = re.compile(r"\d+[.,]\d+")



#: FORMDA SUNULAN TETIKLEYICILER -- kuratorlu, 42'nin hepsi degil.
#:
#: Depoda 42 olculebilir seri var ama hepsini acilir listeye koymak
#: okuru bogar ve secim yapmasini zorlastirir. Buradakiler okurun
#: TANIDIGI ve bir senaryonun etrafinda kurulabilecegi olculer.
#:
#: Sira bilincli: en cok senaryo yazilacak olanlar ustte.
#:
#: (kod, gorunen ad, birim) -- birim formda esik alaninin yaninda
#: gosteriliyor ki okur "3,63 mi 363 mu" diye tereddut etmesin.
TETIKLEYICILER: tuple[tuple[str, str, str], ...] = (
    ("TP.TUKFIY2025.GENEL", "Türkiye TÜFE (yıllık)", "%"),
    ("TP.FE25.OKTG04",      "Türkiye çekirdek enflasyon (C)", "%"),
    ("TP.APIFON4",          "TCMB ağırlıklı fonlama maliyeti", "%"),
    ("TP.DK.USD.S.YTL",     "USD/TRY", "TL"),
    ("DFF",                 "ABD efektif fed fonu oranı", "%"),
    ("DGS10",               "ABD 10 yıllık tahvil getirisi", "%"),
    ("DGS2",                "ABD 2 yıllık tahvil getirisi", "%"),
    ("CPIAUCNS",            "ABD TÜFE (yıllık)", "%"),
    ("PCEPILFE",            "ABD çekirdek PCE", "%"),
    ("UNRATE",              "ABD işsizlik oranı", "%"),
    ("DCOILBRENTEU",        "Brent petrol", "$"),
    ("DTWEXBGS",            "Dolar endeksi", "endeks"),
    ("VIXCLS",              "VIX oynaklık endeksi", "endeks"),
    ("PAXGUSD",             "Ons altın", "$"),
    ("XBTUSD",              "Bitcoin", "$"),
)

#: Kod -> (ad, birim). Dogrulama ve gosterim icin.
TETIKLEYICI_HARITA = {k: (a, b) for k, a, b in TETIKLEYICILER}


def tetikleyici_gecerli(kod: str, yon: str, esik) -> bool:
    """Uc alan birlikte gecerli mi.

    Ucu de gerekli: eksik biri sonuclandirmayi imkansiz kilar ve
    yarim bir tetikleyici, hic tetikleyici olmamasindan kotudur --
    kullanici "ayarladim" saniyor ama senaryo 'belirsiz' cikiyor.
    """
    if not kod or kod not in TETIKLEYICI_HARITA:
        return False
    if yon not in ("ustunde", "altinda"):
        return False
    try:
        float(esik)
    except (TypeError, ValueError):
        return False
    return True


def _veri_sayilari(gun: int = 400) -> set[str]:
    """Depodaki gostergelerin YAZILI hallerini dondurur.

    Karsilastirma metin uzerinden: yazar "31,75" yaziyor, depoda
    31.75409679 duruyor. Iki basamaga yuvarlanmis hali uretiliyor --
    ayni yaklasim `yorum_denetimi` icinde de var ve sebebi ayni:
    okurun gordugu deger yuvarlanmis olan.
    """
    if not DEPO.exists():
        return set()
    cikti: set[str] = set()
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            for (d,) in b.execute(
                    "SELECT DISTINCT deger FROM gosterge"
                    " WHERE tarih >= date('now', ?)", (f"-{gun} days",)):
                if d is None:
                    continue
                for basamak in (1, 2):
                    cikti.add(f"{d:.{basamak}f}".replace(".", ","))
    except sqlite3.Error:
        return set()
    return cikti


def yanislanabilir(kosul: str) -> bool:
    """Kosulun ne zaman/nasil kontrol edilecegi belli mi.

    Olcut ISARET VARLIGI, dil kalitesi degil. "TUFE %30'un altina
    inerse" geciyor; "piyasalar dalgalanabilir" gecmiyor.
    """
    k = (kosul or "").strip()
    if len(k) < 12:
        return False
    if _ESIK.search(k):
        return True
    return False


def kacamak_dil(metin: str) -> list[str]:
    """Yanlislanabilirligi zayiflatan ifadeler."""
    return sorted({m.group(0).lower() for m in _BULANIK.finditer(metin or "")})


def dogrulanmayan_sayilar(gerekce: str,
                          veri: set[str] | None = None) -> list[str]:
    """Gerekcede gecip DEPODA BULUNMAYAN sayilar.

    Yazarin uydurdugunu iddia etmiyoruz -- baska bir kaynaktan almis
    olabilir. Ama bu sitede gosterilen bir sayi degilse okur onu BURADA
    dogrulayamaz ve not bunu soyluyor.
    """
    if veri is None:
        veri = _veri_sayilari()
    if not veri:
        return []
    return sorted({s for s in _SAYI.findall(gerekce or "") if s not in veri})


def denetle(kosul: str, sonuc: str, gerekce: str,
            veri: set[str] | None = None) -> dict:
    """Senaryonun dogrulanabilir ozellikleri.

    Doner: {"yanislanabilir": bool, "notlar": [str], "engel": [str]}

    `engel` YALNIZCA yayini durduran seyler icin. Su an bos donuyor --
    yatirim tavsiyesi taramasi worker tarafinda `guvenlik` ile zaten
    yapiliyor ve burada tekrarlanmiyor (iki yerde iki kural, zamanla
    ayrisir).
    """
    notlar: list[str] = []
    yl = yanislanabilir(kosul)
    if not yl:
        notlar.append(
            "Koşulda ölçülebilir bir eşik yok. \"TÜFE %30'un altına "
            "inerse\" gibi bir eşik yazarsanız senaryonuz ufku "
            "dolduğunda sonuçlandırılabilir.")
    kacamak = kacamak_dil(kosul + " " + sonuc)
    if kacamak:
        notlar.append(
            "Kaçamak ifade: " + ", ".join(kacamak[:3]) +
            ". Bu tür ifadeler her durumda doğru çıkar ve senaryo "
            "sınanamaz hale gelir.")
    if not (gerekce or "").strip():
        notlar.append("Gerekçe boş. Neden böyle düşündüğünüzü yazmak, "
                      "senaryoyu bir tahminden değerlendirmeye çevirir.")
    dogrulanmaz = dogrulanmayan_sayilar(gerekce, veri)
    if dogrulanmaz:
        notlar.append(
            "Şu sayılar sitenin verisinde geçmiyor: " +
            ", ".join(dogrulanmaz[:3]) +
            ". Okur bunları burada doğrulayamaz; kaynağını "
            "gerekçede belirtmeniz iyi olur.")
    return {"yanislanabilir": yl, "notlar": notlar, "engel": []}
