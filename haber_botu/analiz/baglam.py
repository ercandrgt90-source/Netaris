"""Icerik BAGLAM dogrulayicisi -- sayi dogru mu degil, DOGRU YERDE mi.

NEDEN SAYI KONTROLU YETMIYOR
----------------------------
Var olan kontrol soyle calisiyordu:

    model "%31,75" yazdi -> bu sayi sayfada geciyor mu? -> evet -> yayimla

Sayi gercekti, kaynagi gercekti, sayfada da vardi. Ama haber ABD
Fed tutanaklariydi ve %31,75 TURKIYE TUFE'siydi. Kontrol "bu sayi
uydurma mi" sorusunu soruyordu; sorulmasi gereken "bu sayi BU HABERE
ait mi" idi.

Bu hata bir kez cikip gecmedi -- 2026-08 icinde ayni sinif UC ayri
katmanda tekrarladi:

    bolge siniflandirmasi   yabanci haber TR sayildi
    takip kalemleri         ABD haberine "Resmi Gazete'yi izleyin"
    acilis cumlesi          Fed haberi Turkiye TUFE'siyle acildi

Ucunu de tek tek yamadim. Dorduncusu baska bir kombinasyonla gelir:
ECB haberine ABD istihdami, TCMB haberine ABD TUFE'si. Tek tek yama
bu sinifi bitirmiyor; ZINCIRIN KENDISI dogrulanmali:

    haber -> olay -> kurum/ulke -> veri

NASIL CALISIYOR
---------------
1. Metindeki her sayi, DEPODAKI serilere geri izleniyor. Sayi hangi
   seriden gelmis olabilir?
2. Her serinin bir ULKESI var (asagidaki tablo -- ELLE yazildi, addan
   cikarilmadi; ad degisince sessizce bozulmasin diye).
3. Haberin de bir ulkesi var: kurumundan, bolgesinden ve basligindan.
4. Metin YALNIZCA baska bir ulkenin verisini aniyorsa, uyusmazlik var.

"YALNIZCA" SARTI ONEMLI
-----------------------
Turk okura "Fed karari Turkiye'yi nasil etkiler" anlatmak MESRU ve
sitenin isinin ta kendisi. Oyle bir metin HEM Fed verisini HEM Turkiye
verisini anar. Uyusmazlik, metnin haberin kendi ulkesinden HIC veri
anmayip bastan sona baska bir ulkeyi anlatmasidir -- Fed sayfasinin
bastan sona Turkiye TUFE'si anlatmasi gibi.

Bu yuzden kural asimetrik degil ama KAPSAYICI: ek ulke serbest, YERINE
GECME yasak.

KUSURSUZ DEGIL
--------------
Bir sayi birden fazla seriye uyabiliyor (120 gunde bes cakisma
olculdu). Cakismada karar VERILMIYOR -- belirsizken engellemek, dogru
icerigi de duserirdi. Kontrol yanlis negatif verebilir; yanlis pozitif
vermemeye ayarli.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3

DEPO = pathlib.Path(__file__).resolve().parent.parent / "netaris.db"

#: Seri kodu -> ulke. ELLE yazildi, seri ADINDAN cikarilmadi.
#:
#: Once addan cikarmayi denedim ("ABD" ile baslayanlar US) ve dokuz seri
#: siniflandirilamadi: SP500, DJIA, NASDAQCOM, VIXCLS, DTWEXBGS, T10Y2Y,
#: DCOILBRENTEU, DCOILWTICO, TCMB_POLITIKA. Ustelik ad bir gun
#: degistiginde siniflandirma SESSIZCE bozulurdu.
#:
#: "GLOBAL" bir kacamak degil, gercek bir kategori: Brent petrol ve
#: altin herhangi bir ulkenin gostergesi degil; her ulkenin haberinde
#: mesru sekilde anilabilir.
SERI_ULKE: dict[str, str] = {
    # --- Turkiye (TCMB / TUIK) ---
    "TCMB_POLITIKA": "TR",
    # TP.* onekli her seri TCMB EVDS'den geliyor; asagida `seri_ulkesi`
    # bunu onek kuraliyla yakaliyor, tek tek yazmaya gerek yok.

    # --- ABD ---
    "CPIAUCNS": "US", "CPIAUCSL": "US", "CPILFENS": "US", "CPILFESL": "US",
    "PCEPILFE": "US", "PPIFIS": "US", "UNRATE": "US", "PAYEMS": "US",
    "ICSA": "US", "CES0500000003": "US", "ADPMNUSNERSA": "US",
    "GDPC1": "US", "INDPRO": "US", "HOUST": "US", "RSAFS": "US",
    "UMCSENT": "US", "MICH": "US",
    "DFF": "US", "DGS10": "US", "DGS2": "US", "T10Y2Y": "US",
    "SP500": "US", "DJIA": "US", "NASDAQCOM": "US", "VIXCLS": "US",
    "DTWEXBGS": "US",

    # --- Avro Bolgesi ---
    "DEXUSEU": "EU",

    # --- Ulkesiz: emtia ve kripto ---
    #
    # Bunlar her ulkenin haberinde anilabiliyor ve anilmasi dogru:
    # Brent'in fiyati ne ABD'nin ne Turkiye'nin gostergesi.
    "DCOILBRENTEU": "GLOBAL", "DCOILWTICO": "GLOBAL",
    "PAXGUSD": "GLOBAL", "XBTUSD": "GLOBAL", "ETHUSD": "GLOBAL",
}

#: Haberi yayimlayan/konu eden kurum -> ulke. Kurum, haberin ulkesinin
#: EN GUCLU isareti: "Fed" gecen bir haber ABD haberidir.
KURUM_ULKE: dict[str, str] = {
    "FED": "US", "FOMC": "US", "SEC": "US", "EIA": "US", "BLS": "US",
    "ECB": "EU", "AVRUPA MERKEZ BANKASI": "EU",
    "TCMB": "TR", "TUIK": "TR", "TÜİK": "TR", "SPK": "TR", "BDDK": "TR",
    "BOJ": "JP", "BOE": "GB",
}

#: Baslikta gecerse haberin ulkesini belirleyen isaretler.
#: Bosluklu yazim bilincli -- kelime icinde eslesmesin.
BASLIK_ULKE: tuple[tuple[str, str], ...] = (
    (" fed ", "US"), ("fomc", "US"), ("federal reserve", "US"),
    ("powell", "US"), (" abd ", "US"), ("amerika", "US"),
    (" ecb ", "EU"), ("avrupa merkez bankasi", "EU"), ("lagarde", "EU"),
    ("avro bolge", "EU"),
    (" boj ", "JP"), ("bank of japan", "JP"), ("japonya", "JP"),
    ("ueda", "JP"),
    (" boe ", "GB"), ("bank of england", "GB"), ("ingiltere", "GB"),
    ("bailey", "GB"),
    ("tcmb", "TR"), ("merkez bankasi", "TR"), ("tuik", "TR"),
    ("turkiye", "TR"),
)

_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
})


def _katla(metin: str) -> str:
    return metin.translate(_KATLAMA).lower()


#: Ondalikli sayilar. Tam sayilar DISARIDA: "2026", "3 uye" olcum degil
#: ve onlari seriye baglamaya calismak gurultu uretir.
SAYI = re.compile(r"\d+(?:[.\s]\d{3})*,\d+")


def seri_ulkesi(kod: str) -> str:
    """Serinin ulkesi. Bilinmiyorsa bos dizge -- karar verilmez."""
    if kod.startswith("TP."):
        return "TR"          # TCMB EVDS onegi
    return SERI_ULKE.get(kod, "")


def haber_ulkesi(baslik: str, kurum: str = "", bolge: str = "") -> str:
    """Haberin ULKESI. Bulunamazsa bos dizge.

    Sira onemli: KURUM en guclu isaret (Fed'in kendi duyurusu ABD
    haberidir, basliginda "ABD" gecmese bile). Sonra baslik. Bolge en
    son ve yalnizca TR icin -- "DUNYA" bir ulke degil, bir kova.
    """
    kk = KURUM_ULKE.get((kurum or "").strip().upper())
    if kk:
        return kk
    b = " " + _katla(baslik) + " "
    for isaret, ulke in BASLIK_ULKE:
        if isaret in b:
            return ulke
    return "TR" if bolge == "TR" else ""


def _sayi_degeri(metin: str) -> float | None:
    """'31,75' -> 31.75 ; '1.459,20' -> 1459.20"""
    try:
        return float(metin.replace(".", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def sayiyi_coz(b: sqlite3.Connection, deger: float, basamak: int,
               gun: int = 400) -> set[str]:
    """Bu deger hangi serilerden gelmis OLABILIR.

    METNIN HASSASIYETINDE ESLESIYOR, tam degerde degil.
    Ilk yazimimda "tolerans yok" diye tam eslesme aradim ve SINAMA
    KIRILDI: asil yakalamasi gereken Fed vakasi kacti. Sebep --

        depoda  : 31.75409679   (TP.TUKFIY2025.GENEL, ham seri)
        metinde : 31,75         (sayfada gorunen, iki basamaga yuvarlanmis)

    Model sayfadaki degeri kopyaliyor, ham seriyi degil. Tam eslesme
    aramak, kontrolun HIC calismamasi demekti. Karsilastirma metnin
    yazdigi basamak sayisinda yapiliyor.

    Yuvarlama cakismayi artiriyor; cakisma `uyusmazlik` icinde
    "birden fazla ulke -> karar verme" kuraliyla ele aliniyor.
    """
    kodlar: set[str] = set()
    r = b.execute(
        "SELECT DISTINCT kod FROM gosterge"
        " WHERE ROUND(deger, ?) = ? AND tarih >= date('now', ?)",
        (basamak, round(deger, basamak), f"-{gun} days")).fetchall()
    kodlar |= {x[0] for x in r}
    try:
        r2 = b.execute(
            "SELECT DISTINCT sembol FROM fiyat"
            " WHERE ROUND(kapanis, ?) = ? AND tarih >= date('now', ?)",
            (basamak, round(deger, basamak), f"-{gun} days")).fetchall()
        kodlar |= {x[0] for x in r2}
    except sqlite3.Error:
        pass
    return kodlar


def uyusmazlik(b: sqlite3.Connection, metin: str, baslik: str,
               kurum: str = "", bolge: str = "") -> dict | None:
    """Metin, haberin ulkesi disinda BASKA bir ulkeyi mi anlatiyor.

    Doner: uyusmazlik varsa ayrinti sozlugu, yoksa None.

    KURAL: ek ulke SERBEST, yerine gecme YASAK.
      * Metin haberin ulkesinden veri aniyorsa -> sorun yok
        (baska ulkeleri de anmasi "etkisi" anlatimidir, mesru).
      * Metin YALNIZCA baska bir ulkenin verisini aniyorsa -> uyusmazlik.
      * GLOBAL seriler (Brent, altin, kripto) her yerde serbest.
      * Haberin ulkesi bilinmiyorsa karar VERILMEZ.
    """
    h_ulke = haber_ulkesi(baslik, kurum, bolge)
    if not h_ulke:
        return None

    kendi, yabanci = 0, {}
    for ham in SAYI.findall(metin):
        d = _sayi_degeri(ham)
        if d is None:
            continue
        # Metnin YAZDIGI basamak sayisi: "31,75" -> 2, "95,3" -> 1.
        basamak = len(ham.split(",")[-1])
        kodlar = sayiyi_coz(b, d, basamak)
        ulkeler = {seri_ulkesi(k) for k in kodlar} - {""}
        if not ulkeler:
            continue                      # seriye baglanamadi: bu kontrolun konusu degil
        if "GLOBAL" in ulkeler:
            continue                      # emtia/kripto her yerde serbest
        if h_ulke in ulkeler:
            kendi += 1                    # haberin kendi ulkesinden: dogru
            continue
        if len(ulkeler) > 1:
            continue                      # cakisma: belirsizken karar verilmez
        yabanci[ham] = ulkeler.pop()

    if yabanci and kendi == 0:
        return {
            "haber_ulkesi": h_ulke,
            "yabanci_sayilar": yabanci,
            "aciklama": (
                f"metin {h_ulke} haberi ama yalnizca "
                f"{'/'.join(sorted(set(yabanci.values())))} verisi aniyor"),
        }
    return None
