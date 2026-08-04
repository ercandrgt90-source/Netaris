"""Netaris merkezi veri deposu -- "beyin".

NE ISE YARAR
------------
Bugune kadar her hat kendi ciktisini bir JSON dosyasina yaziyordu ve her
calistirmada UZERINE yaziyordu. Yani gecmis yoktu: dun Brent kacti,
gecen hafta hangi haberler geldi, bir hisse kodunun kac analizi var --
hicbiri sorulamiyordu.

Bu modul SQLite'ta kalici bir depo tutar. Her calistirma verinin uzerine
YAZMAZ, ustune EKLER. Boylece zamanla:

  * gosterge gecmisi birikir (kendi zaman serimiz olur)
  * hangi haberi ne zaman gorduğumuz bilinir (tekrar yayimlanmaz)
  * ceviriler kalicilasir (kota harcanmaz)
  * uretilen her icerik kayda gecer

NEDEN SQLITE
------------
Python'da yerlesik, kurulum yok, tek dosya, yedeklemesi kopyalamak kadar
kolay. Ilerde Cloudflare D1'e tasinirsa sema aynen gecer -- D1 de SQLite.

TASARIM KURALI
--------------
Depo yalnizca SAKLAR. Hesap yapmaz, yorum uretmez, karar vermez. Bunlar
`analiz/` altindaki modullerin isi. Deponun tek sorumlulugu veriyi
kaybetmemek.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

VERITABANI = pathlib.Path(__file__).parent / "netaris.db"

SEMA = """
CREATE TABLE IF NOT EXISTS gosterge (
    kod        TEXT NOT NULL,
    tarih      TEXT NOT NULL,
    deger      REAL NOT NULL,
    birim      TEXT,
    ad         TEXT,
    kaynak     TEXT,
    kayit_ani  TEXT NOT NULL,
    PRIMARY KEY (kod, tarih)
);

CREATE TABLE IF NOT EXISTS haber (
    adres         TEXT PRIMARY KEY,
    baslik_kaynak TEXT NOT NULL,
    baslik_tr     TEXT,
    kurum         TEXT,
    konu          TEXT,
    tarih         TEXT,
    yorumlanir    INTEGER DEFAULT 0,
    ilk_gorulme   TEXT NOT NULL,
    son_gorulme   TEXT NOT NULL,
    yayimlandi    INTEGER DEFAULT 0,
    yayin_yolu    TEXT,
    -- Sayfayi yeniden uretmeye yeten TAM kayit (JSON).
    --
    -- NEDEN VAR: site her kurulumda `cikti/` klasorunu bosaltip yalnizca
    -- guncel besleme penceresini (son ~40 haber) yeniden uretiyordu.
    -- Olculen sonuc: depoda sayfa hak eden 53 haber varken sitede 10
    -- tanesi duruyordu, kalan 43'u 404'ti. Yani arsiv hic birikmiyordu
    -- ve dun paylasilan bir baglanti bugun kiriktir.
    --
    -- Ozet, fotograf, atif ve baglam yalnizca uretim aninda biliniyor;
    -- burada saklanmazsa geriye donuk uretilemez. Ayri sutunlar yerine
    -- JSON: bu alan sayfa sablonunun yuku, semanin parcasi degil.
    sayfa_veri    TEXT
);

CREATE TABLE IF NOT EXISTS ceviri (
    kaynak_ozet TEXT PRIMARY KEY,   -- kaynak metnin sha256 ozeti
    kaynak      TEXT NOT NULL,
    sonuc       TEXT NOT NULL,
    servis      TEXT,
    kayit_ani   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icerik (
    slug       TEXT PRIMARY KEY,
    tur        TEXT NOT NULL,       -- bilanco | makro | teknik | haber | yorum
    baslik     TEXT NOT NULL,
    kod        TEXT,
    kategori   TEXT,
    tarih      TEXT,
    kelime     INTEGER,
    kayit_ani  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fiyat (
    sembol     TEXT NOT NULL,
    tarih      TEXT NOT NULL,
    kapanis    REAL NOT NULL,
    yuksek     REAL,
    dusuk      REAL,
    hacim      REAL,
    PRIMARY KEY (sembol, tarih)
);

CREATE TABLE IF NOT EXISTS calisma (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    hat        TEXT NOT NULL,
    baslangic  TEXT NOT NULL,
    bitis      TEXT,
    durum      TEXT,               -- basarili | hatali
    ozet       TEXT
);

-- ===================================================================
-- GRAF KATMANI -- varlik, bag, olay, kanit
--
-- Yukaridaki tablolar bir KUTUK: ne zaman ne gorduk. Asagidakiler bir
-- AG: neyin neyle iliskili oldugu ve her iddianin neye dayandigi.
--
-- Ayrimin sebebi: kutuk "3 Agustos'ta su haber geldi" sorusunu
-- cevapliyor ama "bu daha once ne zaman oldu, o zaman ne olmustu"
-- sorusunu cevaplayamiyor. Ikinci soru, yaziyi yorumdan arastirmaya
-- ceviren tek sey.
-- ===================================================================

-- Dugum. Kurum, kisi, ulke, gosterge, sirket, sektor, emtia...
--
-- `kod` DILDEN BAGIMSIZ kimlik. Fed tek varliktir; Turkce adi "Fed",
-- Ingilizce adi "Federal Reserve". Cok dilli yayina gecildiginde ad
-- degisir, kod degismez -- bu yuzden baglar bozulmaz.
CREATE TABLE IF NOT EXISTS varlik (
    kod        TEXT PRIMARY KEY,
    tur        TEXT NOT NULL,      -- kurum|kisi|ulke|gosterge|sirket|sektor|emtia
    ad         TEXT NOT NULL,
    ad_en      TEXT,
    aciklama   TEXT,
    -- Fiyat/veri serisiyle eslesiyorsa kaynak kodu: "DCOILBRENTEU", "XAU"
    seri_kodu  TEXT,
    onem       INTEGER DEFAULT 0,  -- siralamada kullanilir
    kayit_ani  TEXT NOT NULL
);

-- Kenar. YONLU: (kaynak -> hedef).
--
-- `tur` iliskinin NE oldugunu soyler; "etkiler" ile "belirler" ayni sey
-- degil. Fed politika faizini BELIRLER, altini ETKILER.
--
-- `dayanak` bu bagin nereden geldigi. Elle yazilmis yapisal bir kanal mi,
-- yoksa veriden mi cikarildi? Ikisi ayni guvende degil ve okura ayni
-- sekilde sunulamaz.
CREATE TABLE IF NOT EXISTS bag (
    kaynak     TEXT NOT NULL REFERENCES varlik(kod),
    hedef      TEXT NOT NULL REFERENCES varlik(kod),
    tur        TEXT NOT NULL,      -- belirler|etkiler|uyesi|rakibi|ureticisi
    aciklama   TEXT,
    dayanak    TEXT NOT NULL DEFAULT 'yapisal',  -- yapisal|veri|kaynak
    guc        INTEGER DEFAULT 1,
    kayit_ani  TEXT NOT NULL,
    PRIMARY KEY (kaynak, hedef, tur)
);

-- Olay. Esigi gecen, hakkinda icerik uretilen haber.
--
-- Her haber olay DEGILDIR. Olay, fiyat tepkisi olculen ve aciklama
-- uretilen seydir; ayri tablo olmasinin sebebi bu.
CREATE TABLE IF NOT EXISTS olay (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anahtar     TEXT NOT NULL UNIQUE,   -- tekrar uretimi engeller
    tur         TEXT NOT NULL,          -- enflasyon|faiz|istihdam|jeopolitik|arz
    baslik      TEXT NOT NULL,
    ozet        TEXT,
    haber_adres TEXT REFERENCES haber(adres),
    an          TEXT NOT NULL,          -- olayin gerceklestigi an (ISO)
    siddet      INTEGER DEFAULT 0,      -- esik hesabinin ciktisi
    yayimlandi  INTEGER DEFAULT 0,
    kayit_ani   TEXT NOT NULL
);

-- Olayin fiyat tepkisi. Bir olay, birden cok varlikta olculur.
--
-- `pencere_sn` olcumun hangi araligi kapsadigi; `gozlem_ani` verinin
-- kendi tarihi. Ikisi de yaziliyor cunku "petrol %5 yukseldi" cumlesi
-- HANGI ARALIKTA ve HANGI TARIHLI veriyle soylendigini tasimali.
CREATE TABLE IF NOT EXISTS tepki (
    olay_id     INTEGER NOT NULL REFERENCES olay(id) ON DELETE CASCADE,
    varlik      TEXT NOT NULL,
    deger       REAL,
    degisim     REAL,               -- yuzde
    pencere_sn  INTEGER,
    gozlem_ani  TEXT,
    kaynak      TEXT,
    gecikmeli   INTEGER DEFAULT 0,  -- 1 ise veri gun ici degil, gecikmeli
    PRIMARY KEY (olay_id, varlik, pencere_sn)
);

-- Kanit. Her iddianin dayandigi belge.
--
-- "Resmi veri ile gorusu ayirmak" ancak her cumlenin arkasinda bir kayit
-- varsa mumkun. Okur "bu rakam nereden geliyor" diye sorabilmeli.
CREATE TABLE IF NOT EXISTS kanit (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    konu_turu  TEXT NOT NULL,       -- olay|bag|icerik
    konu_id    TEXT NOT NULL,
    tur        TEXT NOT NULL,       -- veri|belge|hesap
    kaynak     TEXT NOT NULL,
    adres      TEXT,
    alinti     TEXT,
    gozlem_ani TEXT,
    kayit_ani  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_gosterge_tarih ON gosterge(tarih);
CREATE INDEX IF NOT EXISTS ix_haber_tarih    ON haber(tarih);
CREATE INDEX IF NOT EXISTS ix_icerik_tur     ON icerik(tur, tarih);
CREATE INDEX IF NOT EXISTS ix_bag_hedef      ON bag(hedef);
CREATE INDEX IF NOT EXISTS ix_olay_tur       ON olay(tur, an);
CREATE INDEX IF NOT EXISTS ix_kanit_konu     ON kanit(konu_turu, konu_id);
"""


def simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


#: Sonradan eklenen sutunlar: (tablo, sutun, tanim).
#:
#: `CREATE TABLE IF NOT EXISTS` VAR OLAN TABLOYU DEGISTIRMEZ -- sessizce
#: hicbir sey yapar. Semaya yeni bir sutun yazmak, calisan bir depoda o
#: sutunun olusmasini SAGLAMAZ; kod yeni sutunu bekler, depo vermez.
#: Yeni sutun hem SEMA'ya hem buraya yazilmali.
GOCLER = (
    ("haber", "sayfa_veri", "TEXT"),
)


def _gocur(b) -> None:
    for tablo, sutun, tanim in GOCLER:
        mevcut = {s[1] for s in b.execute(f"PRAGMA table_info({tablo})")}
        if not mevcut:            # tablo henuz yok; SEMA olusturacak
            continue
        if sutun not in mevcut:
            b.execute(f"ALTER TABLE {tablo} ADD COLUMN {sutun} {tanim}")


@contextmanager
def baglan(yol: pathlib.Path = VERITABANI):
    """Baglanti acar, semayi garantiler, cikista kapatir."""
    b = sqlite3.connect(yol)
    b.row_factory = sqlite3.Row
    try:
        b.executescript(SEMA)
        _gocur(b)
        yield b
        b.commit()
    finally:
        b.close()


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------

def gosterge_yaz(b, kalemler: list[dict]) -> int:
    """Gosterge gozlemlerini ekler.

    `INSERT OR IGNORE` kullaniliyor: ayni kod+tarih ikinci kez gelirse
    sessizce atlanir. Boylece hat gunde bes kez calissa bile gecmis
    bozulmaz. Guncelleme DEGIL ekleme -- yayimlanmis bir gozlem sonradan
    degismez.
    """
    n = 0
    for k in kalemler:
        if k.get("deger_ham") is None or not k.get("tarih"):
            continue
        imlec = b.execute(
            "INSERT OR IGNORE INTO gosterge"
            " (kod, tarih, deger, birim, ad, kaynak, kayit_ani)"
            " VALUES (?,?,?,?,?,?,?)",
            (k.get("kod"), k.get("tarih"), k["deger_ham"], k.get("birim"),
             k.get("ad"), k.get("kaynak", "FRED"), simdi()),
        )
        n += imlec.rowcount
    return n


def haber_yaz(b, haberler: list[dict]) -> tuple[int, int]:
    """Haberleri ekler/gunceller. (yeni, tekrar) doner.

    Daha once gorulen haberin `son_gorulme` alani guncellenir ama
    `ilk_gorulme` KORUNUR -- bir duyurunun ne zaman ortaya ciktigini
    bilmek, ne zaman son goruldugunden daha degerli.
    """
    yeni = tekrar = 0
    for h in haberler:
        adres = h.get("adres")
        if not adres:
            continue
        # Sayfa yuku YALNIZCA sayfasi olacak haberlerde saklaniyor.
        # Rutin duyurulari (yorumlanmayan) da saklamak depoyu bes katina
        # cikarir ve hicbiri sayfa olmaz.
        yuk = json.dumps(_sayfa_yuku(h), ensure_ascii=False) \
            if h.get("yorumlanir") else None
        var = b.execute("SELECT 1 FROM haber WHERE adres=?", (adres,)).fetchone()
        if var:
            b.execute(
                "UPDATE haber SET son_gorulme=?, baslik_tr=COALESCE(?, baslik_tr),"
                " yayin_yolu=COALESCE(?, yayin_yolu),"
                " sayfa_veri=COALESCE(?, sayfa_veri),"
                " yayimlandi=MAX(yayimlandi, ?) WHERE adres=?",
                (simdi(), h.get("baslik"), h.get("yol"), yuk,
                 1 if h.get("yol") else 0, adres),
            )
            tekrar += 1
        else:
            b.execute(
                "INSERT INTO haber (adres, baslik_kaynak, baslik_tr, kurum,"
                " konu, tarih, yorumlanir, ilk_gorulme, son_gorulme,"
                " yayimlandi, yayin_yolu, sayfa_veri)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (adres, h.get("baslik_kaynak", ""), h.get("baslik"),
                 h.get("kurum"), h.get("konu"), h.get("tarih"),
                 1 if h.get("yorumlanir") else 0, simdi(), simdi(),
                 1 if h.get("yol") else 0, h.get("yol"), yuk),
            )
            yeni += 1
    return yeni, tekrar


#: Sayfayi yeniden uretmek icin saklanan HAM OLGULAR.
#:
#: TURETILMIS ALANLAR BURAYA GIRMEZ. Ilk surumde `konu`, `bolge`, `foto`
#: ve `neden_onemli` de saklaniyordu ve sonucu olculdu:
#:
#:     "Goldman Sachs'tan Turkiye icin faiz uyarisi: Indirim beklentisi
#:      OTELENEBILIR"  ->  konu: Turizm
#:
#: Bu, "otel" kalibinin "OTELenebilir" icinde eslesmesiydi; siniflandirici
#: sonradan duzeltildi ama arsivdeki yuk ESKI degeri tasidigi icin sayfa
#: otel fotografiyla, "Konaklama - Havayolu" duyarlilik listesiyle ve
#: "Turizm geliri doviz kazandirir" cumlesiyle YENIDEN yayimlandi.
#:
#: Yani arsiv, duzeltilmis hatalari geri diriltiyordu. Olgu ile turetilmis
#: ayrilmali: olgu degismez, turetilmis her kurulumda yeniden hesaplanir
#: ve siniflandirici duzeldikce ARSIV DE duzelir.
SAYFA_ALANLARI = (
    "baslik", "baslik_kaynak", "ozet", "cevrildi", "dil", "ticari",
    "adres", "kurum", "kurum_tam", "tarih", "tarih_gorunur",
)


def _sayfa_yuku(h: dict) -> dict:
    return {a: h.get(a) for a in SAYFA_ALANLARI if h.get(a) is not None}


def ceviri_yaz(b, onbellek: dict[str, str], servis: str = "") -> int:
    """Ceviri onbellegini depoya alir.

    Onbellek dosyasi silinse bile ceviriler burada kalir; kota yeniden
    harcanmaz. Ayni ceviri iki kez yazilmaz.
    """
    n = 0
    for ozet, sonuc in onbellek.items():
        imlec = b.execute(
            "INSERT OR IGNORE INTO ceviri (kaynak_ozet, kaynak, sonuc,"
            " servis, kayit_ani) VALUES (?,?,?,?,?)",
            (ozet, "", sonuc, servis, simdi()),
        )
        n += imlec.rowcount
    return n


def icerik_yaz(b, kayitlar: list[dict]) -> int:
    n = 0
    for k in kayitlar:
        if not k.get("slug"):
            continue
        b.execute(
            "INSERT INTO icerik (slug, tur, baslik, kod, kategori, tarih,"
            " kelime, kayit_ani) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(slug) DO UPDATE SET baslik=excluded.baslik,"
            " kelime=excluded.kelime, tarih=excluded.tarih",
            (k["slug"], k.get("tur", "?"), k.get("baslik", ""), k.get("kod"),
             k.get("kategori"), k.get("tarih"), k.get("kelime", 0), simdi()),
        )
        n += 1
    return n


def fiyat_yaz(b, sembol: str, mumlar: list[dict]) -> int:
    n = 0
    for m in mumlar:
        imlec = b.execute(
            "INSERT OR IGNORE INTO fiyat (sembol, tarih, kapanis, yuksek,"
            " dusuk, hacim) VALUES (?,?,?,?,?,?)",
            (sembol, m["tarih"], m["kapanis"], m.get("yuksek"),
             m.get("dusuk"), m.get("hacim")),
        )
        n += imlec.rowcount
    return n


@contextmanager
def calisma_kaydi(b, hat: str):
    """Bir hattin calismasini kaydeder -- basarili da olsa hatali da.

    Hatanin kaydedilmesi onemli: "dun gece gundem neden guncellenmedi"
    sorusunun cevabi burada durur.
    """
    imlec = b.execute(
        "INSERT INTO calisma (hat, baslangic, durum) VALUES (?,?,?)",
        (hat, simdi(), "calisiyor"),
    )
    kimlik = imlec.lastrowid
    ozet: dict = {}
    try:
        yield ozet
    except Exception as e:
        b.execute(
            "UPDATE calisma SET bitis=?, durum=?, ozet=? WHERE id=?",
            (simdi(), "hatali", f"{type(e).__name__}: {e}", kimlik),
        )
        b.commit()
        raise
    else:
        b.execute(
            "UPDATE calisma SET bitis=?, durum=?, ozet=? WHERE id=?",
            (simdi(), "basarili", json.dumps(ozet, ensure_ascii=False), kimlik),
        )


# ---------------------------------------------------------------------------
# Okuma
# ---------------------------------------------------------------------------

def durum(b) -> dict:
    """Deponun ozeti -- kac kayit, hangi araliklar."""
    def tek(sorgu, *p):
        s = b.execute(sorgu, p).fetchone()
        return s[0] if s and s[0] is not None else 0

    return {
        "gosterge_gozlem": tek("SELECT COUNT(*) FROM gosterge"),
        "gosterge_seri": tek("SELECT COUNT(DISTINCT kod) FROM gosterge"),
        "gosterge_ilk": tek("SELECT MIN(tarih) FROM gosterge"),
        "gosterge_son": tek("SELECT MAX(tarih) FROM gosterge"),
        "haber": tek("SELECT COUNT(*) FROM haber"),
        "haber_yayimlanan": tek("SELECT COUNT(*) FROM haber WHERE yayimlandi=1"),
        "ceviri": tek("SELECT COUNT(*) FROM ceviri"),
        "icerik": tek("SELECT COUNT(*) FROM icerik"),
        "fiyat_gozlem": tek("SELECT COUNT(*) FROM fiyat"),
        "fiyat_sembol": tek("SELECT COUNT(DISTINCT sembol) FROM fiyat"),
        "calisma": tek("SELECT COUNT(*) FROM calisma"),
        "son_calisma": tek("SELECT MAX(baslangic) FROM calisma"),
    }


def gosterge_serisi(b, kod: str, adet: int = 60) -> list[tuple[str, float]]:
    """Kendi biriktirdigimiz zaman serisi."""
    satirlar = b.execute(
        "SELECT tarih, deger FROM gosterge WHERE kod=?"
        " ORDER BY tarih DESC LIMIT ?", (kod, adet),
    ).fetchall()
    return [(s["tarih"], s["deger"]) for s in reversed(satirlar)]


def yeni_haberler(b, gun: int = 7) -> list[sqlite3.Row]:
    return b.execute(
        "SELECT * FROM haber WHERE ilk_gorulme >= date('now', ?)"
        " ORDER BY tarih DESC", (f"-{gun} days",),
    ).fetchall()


# =====================================================================
# GRAF -- varlik, bag, olay, tepki, kanit
# =====================================================================


def varlik_yaz(b, kayitlar: list[dict]) -> int:
    """Varlik ekler ya da gunceller.

    `INSERT OR REPLACE` degil, alan alan UPSERT: varligin `onem` degeri
    zamanla elle ayarlanabilir ve her calistirmada sifirlanmamali.
    """
    n = 0
    for k in kayitlar:
        b.execute(
            "INSERT INTO varlik (kod, tur, ad, ad_en, aciklama, seri_kodu,"
            " onem, kayit_ani) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(kod) DO UPDATE SET"
            "   ad=excluded.ad, ad_en=excluded.ad_en,"
            "   aciklama=excluded.aciklama, seri_kodu=excluded.seri_kodu",
            (k["kod"], k["tur"], k["ad"], k.get("ad_en"), k.get("aciklama"),
             k.get("seri_kodu"), k.get("onem", 0), simdi()),
        )
        n += 1
    return n


def bag_yaz(b, baglar: list[dict]) -> int:
    n = 0
    for g in baglar:
        b.execute(
            "INSERT OR IGNORE INTO bag (kaynak, hedef, tur, aciklama,"
            " dayanak, guc, kayit_ani) VALUES (?,?,?,?,?,?,?)",
            (g["kaynak"], g["hedef"], g["tur"], g.get("aciklama"),
             g.get("dayanak", "yapisal"), g.get("guc", 1), simdi()),
        )
        n += b.total_changes and 1 or 0
    return n


def komsular(b, kod: str, derinlik: int = 1) -> list[sqlite3.Row]:
    """Bir varliktan cikan baglar. Bilgi agacinin temel sorgusu.

    Derinlik 1'den buyukse genisleyerek ilerler. Dongu koruması var:
    Fed -> Dolar -> Fed gibi bir halka sonsuz donguye girerdi.
    """
    gorulen = {kod}
    sira = [kod]
    sonuc: list[sqlite3.Row] = []
    for _ in range(max(1, derinlik)):
        if not sira:
            break
        yer = ",".join("?" * len(sira))
        satirlar = b.execute(
            f"SELECT g.*, v.ad AS hedef_ad, v.tur AS hedef_tur"
            f" FROM bag g JOIN varlik v ON v.kod = g.hedef"
            f" WHERE g.kaynak IN ({yer}) ORDER BY g.guc DESC", sira,
        ).fetchall()
        sonuc.extend(satirlar)
        sira = [s["hedef"] for s in satirlar if s["hedef"] not in gorulen]
        gorulen.update(sira)
    return sonuc


def olay_yaz(b, olay: dict) -> int | None:
    """Olayi kaydeder. Zaten varsa None doner -- tekrar uretilmez.

    `anahtar` tekrari engelliyor: ayni olay iki kaynaktan gelirse ya da
    hat iki kez calisirsa ikinci kez icerik uretilmemeli.
    """
    var = b.execute("SELECT id FROM olay WHERE anahtar=?",
                    (olay["anahtar"],)).fetchone()
    if var:
        return None
    im = b.execute(
        "INSERT INTO olay (anahtar, tur, baslik, ozet, haber_adres, an,"
        " siddet, kayit_ani) VALUES (?,?,?,?,?,?,?,?)",
        (olay["anahtar"], olay["tur"], olay["baslik"], olay.get("ozet"),
         olay.get("haber_adres"), olay["an"], olay.get("siddet", 0), simdi()),
    )
    return im.lastrowid


def tepki_yaz(b, olay_id: int, tepkiler: list[dict]) -> int:
    n = 0
    for t in tepkiler:
        b.execute(
            "INSERT OR REPLACE INTO tepki (olay_id, varlik, deger, degisim,"
            " pencere_sn, gozlem_ani, kaynak, gecikmeli)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (olay_id, t["varlik"], t.get("deger"), t.get("degisim"),
             t.get("pencere_sn"), t.get("gozlem_ani"), t.get("kaynak"),
             1 if t.get("gecikmeli") else 0),
        )
        n += 1
    return n


def kanit_yaz(b, kayitlar: list[dict]) -> int:
    for k in kayitlar:
        b.execute(
            "INSERT INTO kanit (konu_turu, konu_id, tur, kaynak, adres,"
            " alinti, gozlem_ani, kayit_ani) VALUES (?,?,?,?,?,?,?,?)",
            (k["konu_turu"], str(k["konu_id"]), k["tur"], k["kaynak"],
             k.get("adres"), k.get("alinti"), k.get("gozlem_ani"), simdi()),
        )
    return len(kayitlar)


def benzer_olaylar(b, tur: str, haric_id: int | None = None,
                   adet: int = 5) -> list[sqlite3.Row]:
    """Ayni turden gecmis olaylar -- TARIHSEL EMSAL.

    Motorun en degerli sorgusu bu. "Bu daha once ne zaman oldu ve o zaman
    ne olmustu" sorusunun cevabi; yaziyi yorumdan arastirmaya ceviren sey.
    """
    return b.execute(
        "SELECT o.*, ("
        "  SELECT json_group_array(json_object("
        "    'varlik', t.varlik, 'degisim', t.degisim))"
        "  FROM tepki t WHERE t.olay_id = o.id AND t.degisim IS NOT NULL"
        ") AS tepkiler"
        " FROM olay o WHERE o.tur = ? AND o.id IS NOT ?"
        " ORDER BY o.an DESC LIMIT ?",
        (tur, haric_id, adet),
    ).fetchall()


def olay_gecmisi(b, varlik: str, adet: int = 20) -> list[sqlite3.Row]:
    """Bir varligin gecmiste hangi olaylarda nasil tepki verdigi."""
    return b.execute(
        "SELECT o.an, o.tur, o.baslik, t.degisim, t.pencere_sn"
        " FROM tepki t JOIN olay o ON o.id = t.olay_id"
        " WHERE t.varlik = ? AND t.degisim IS NOT NULL"
        " ORDER BY o.an DESC LIMIT ?", (varlik, adet),
    ).fetchall()


if __name__ == "__main__":
    with baglan() as b:
        d = durum(b)
    print("NETARIS VERI DEPOSU")
    print("=" * 50)
    for k, v in d.items():
        print(f"  {k:<22} {v}")
    print(f"\ndosya: {VERITABANI}")
