"""BIST sirketlerinin GERCEK logolari -- Wikimedia Commons, kamu mali.

BU DOSYA NEDEN VAR
------------------
Bilanco sayfalarinda once konu havuzundan gelen alakasiz stok
fotograflar vardi; sonra uretilmis bir amblem (BIST kodu + sektor
rengi) kondu. Kullanici gercek logo istedi ve ilk cevabim "logolar
tescilli marka, guvenilir kaynak yok" oldu.

O CEVAP EKSIKTI. Olculdu (2026-08-23): Commons'ta Turk sirketlerinin
logolari KAMU MALI olarak duruyor --

    File:ASELSAN logo.svg          Public domain
    File:Garanti BBVA 2019.svg     Public domain
    File:Turkish Airlines logo...  Public domain

Sebep telif hukukunda "ozgunluk esigi" (threshold of originality):
duz yazi ve basit geometriden olusan bir logo TELIF DOGURMAZ. Marka
hakki ayri bir sey ve haber/analiz baglaminda sirketi TANITMAK icin
kullanmak tanitici kullanimdir.

Yani engel hukuki degildi, benim eksik aramamdi.

NE INDIRILIYOR
--------------
YALNIZCA kamu mali ve CC0. "Adil kullanim" gerekcesiyle duran logolar
ALINMIYOR: o gerekce Wikipedia'ya ait ve bize gecmez -- ayni tuzak
fiyat serilerinde de yasanmisti (FRED'den alabilmek yayimlama hakki
vermiyordu).

ESLESME YANLIS OLMAMALI
-----------------------
Arama gurultulu. "Garanti BBVA logo" sorgusu su sonucu da veriyor:

    File:Logo Garanti Koza Tournament of Champions Sofia 2013.svg

Bu bir TENIS TURNUVASI. Yanlis logo basmak, alakasiz fotograftan
DAHA kotudur: okur onu sirketin kendi isareti sanar.

Bu yuzden esleme kati: dosya adi sirketin ayirt edici adini
icermeli, "logo" gecmeli, ve turnuva/etkinlik/tarihce gibi
gurultu isaretleri GECMEMELI. Eslesmeyen sirkette logo yok ve
uretilmis amblem duruyor -- eksik logo, yanlis logodan iyidir.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

_KOK = pathlib.Path(__file__).resolve().parent
KAYIT = _KOK / "logo_kayit.json"
KLASOR = _KOK.parent.parent / "site" / "statik" / "logo"

API = "https://commons.wikimedia.org/w/api.php"
# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {"User-Agent": ajan("kurum logosu")}
ZAMAN_ASIMI = 25

#: Kabul edilen lisanslar -- ATIF DA GEREKTIRMEYENLER.
#: `cc by` DISARIDA: logo sayfanin kunyesinde degil basinda duruyor ve
#: her bilanco sayfasina bir atif satiri eklemek istemiyoruz. Kamu mali
#: logo bu sorunu dogurmuyor.
KABUL = ("public domain", "cc0", "pd")

#: Dosya adinda gecerse ESLESME REDDEDILIR.
#:
#: "tournament", "sponsor", "stadium": sirket adini tasiyan ama sirketin
#: logosu OLMAYAN dosyalar. "1933", "1956": tarihce logolari -- gecerli
#: ama guncel degil ve okur bugunku sirketi ariyor.
GURULTU = re.compile(
    r"tournament|championship|sponsor|stadium|arena|cup\b|trophy|"
    r"open\b|rally|team|jersey|kit\b|award|festival|"
    r"old\b|former|history|historic", re.I)

#: Tarihce logosu: yil ARALIGI ("1933-1956") ya da 2000 oncesi tek yil.
#:
#: Ilk surumde "herhangi bir yil" reddediliyordu ve DOGRU logolari da
#: eledi: `File:Garanti BBVA 2019.svg` guncel logo ve dosya adinda
#: surum yili tasiyor. Suzgec fazla genisti.
_ESKI_YIL = re.compile(
    r"\b(18|19|20)\d{2}\s*[-–—]\s*(18|19|20)\d{2}\b"
    r"|\b1[89]\d{2}\b")

#: Tek basina AYIRT ETMEYEN adlar. "TURK HAVA YOLLARI" -> "turk" olurdu
#: ve "turk" gecen her dosyayla eslesirdi.
_GENEL = {"turk", "turkiye", "turkish", "anadolu", "ege", "akdeniz",
          "marmara", "avrupa", "global", "euro", "national", "united"}

#: Sirket adinda ayirt edicilik tasimayan kelimeler -- eslemede
#: kullanilmiyor. "GAYRIMENKUL YATIRIM ORTAKLIGI A.S." iki farkli
#: sirkette de geciyor.
_ETKISIZ = {
    "a.s.", "as", "a.ş.", "aş", "t.a.ş.", "anonim", "şirketi", "sirketi",
    "holding", "gayrimenkul", "yatirim", "yatırım", "ortaklığı",
    "ortakligi", "sanayi", "ticaret", "ve", "grubu", "group",
    "enerji", "insaat", "inşaat", "turizm", "finansal", "kiralama",
    "faktoring", "menkul", "değerler", "degerler", "bankası", "bankasi",
    # FAALIYET KONUSU MARKA DEGIL.
    # "ASELSAN ELEKTRONIK SANAYI" -> marka "aselsan"; "elektronik"
    # yuzlerce sirkette geciyor ve tek basina arandiginda rastgele bir
    # dosyayla eslesir.
    "elektronik", "otomotiv", "kimya", "tekstil", "gida", "gıda",
    "madencilik", "cimento", "çimento", "demir", "celik", "çelik",
    "hava", "yollari", "yolları", "denizcilik", "lojistik", "saglik",
    "sağlık", "teknoloji", "bilisim", "bilişim", "iletisim", "iletişim",
    "sigorta", "emeklilik", "perakende", "market", "magazacilik",
    "mağazacılık", "uretim", "üretim", "isletme", "işletme",
}


def _sadelestir(metin: str) -> str:
    d = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g",
                       "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o",
                       "ç": "c", "Ç": "c"})
    return metin.translate(d).lower()


def ayirt_edici(ad: str) -> str:
    """Sirket adinin ayirt edici parcasi.

    "AKMERKEZ GAYRIMENKUL YATIRIM ORTAKLIGI A.S." -> "akmerkez"

    Marka adi Turk sirket unvanlarinda neredeyse her zaman BASTA
    duruyor; sonrasi faaliyet konusu ve hukuki bicim. Bu yuzden ILK
    ayirt edici kelime aliniyor.

    "En uzun kelime" denenmisti ve yanlisti: "ASELSAN ELEKTRONIK
    SANAYI" icin "elektronik" cikiyordu -- en uzun kelime, ama marka
    degil.

    Iki liste birlikte calisiyor: `_ETKISIZ` faaliyet ve hukuki bicim
    kelimelerini, `_GENEL` ise tek basina ayirt etmeyen cografi adlari
    ("turk", "anadolu") duşuruyor.

    Bos donerse arama YAPILMIYOR. Ornegin "TURK HAVA YOLLARI"nin her
    kelimesi eleniyor ve sirket amblemle kaliyor -- eksik logo, yanlis
    logodan iyidir.
    """
    # Uc harf de kabul: "KOC HOLDING" ve "SOK MARKETLER" gibi kisa
    # markalar dorde takiliyordu.
    for p in re.split(r"[\s.]+", _sadelestir(ad)):
        if len(p) >= 3 and p not in _ETKISIZ and p not in _GENEL:
            return p
    return ""


#: Dosya adinda gecmesi normal olan, sirket unvaninda ARANMAYACAK
#: kelimeler. Bunlar dosya adlandirma artiklari, sirketin adi degil.
_SERBEST = {"logo", "logotype", "wordmark", "svg", "png", "vector",
            "vertical", "horizontal", "new", "current", "official",
            "of", "the", "and", "ve", "file", "en", "tr"}


def dogrulandi(baslik: str, ad: str) -> bool:
    """Dosya adindaki HER kelime sirketin unvaninda geciyor mu?

    NEDEN BU KAPI GEREKLI
    ---------------------
    Anahtar eslesmesi ve "logo" sarti yetmedi. Olculdu (2026-08-23):
    188 sirkette 62 "logo bulundu" dendi ve yarisindan cogu yanlisti --

        ANHYT (Anadolu Hayat)  -> Al-Hayat Media Center Logo
        ATATP                  -> ATP Tour logo
        BULGS                  -> Chicago Bulls logo
        DAGI                   -> IslamDagiTaburuFlag

    Hepsinde ANAHTAR gerçekten dosya adinda geciyordu ("hayat",
    "bulls"...). Sorun anahtarin bulunmasi degil, dosyanin BASKA BIR
    SEYE ait olmasiydi.

    Bu kapi tersinden bakiyor: dosya adindaki her kelime sirketin
    kendi unvaninda da gecmeli. "Al-Hayat Media Center" icinde
    "media" ve "center" var; Anadolu Hayat Emeklilik'in unvaninda
    yok -> reddediliyor. "Akbank logo" icinde yalnizca "akbank" var
    ve unvanda geciyor -> kabul.

    Yanlis bir logo, alakasiz bir fotograftan DAHA kotudur: okur onu
    sirketin kendi isareti sanar. Bu yuzden kapi kati tarafta
    duruyor ve kapsam dusuyor -- kabul edilen bedel.
    """
    b = _sadelestir(baslik)
    b = re.sub(r"^file:", "", b).rsplit(".", 1)[0]
    b = re.sub(r"[^a-z0-9]+", " ", b)
    unvan = set(re.split(r"[\s.]+", _sadelestir(ad)))
    unvan = {w for w in unvan if w}
    for kelime in b.split():
        if kelime in _SERBEST or kelime.isdigit():
            continue
        # Unvanda birebir ya da ONEK olarak gecmeli: "akbank" ile
        # "akbanka" ayni sirket, "bulls" ile "anadolu" degil.
        if not any(w == kelime or w.startswith(kelime) or
                   kelime.startswith(w) for w in unvan):
            return False
    return True


#: ELLE ONAYLANMIS ESLESMELER -- yayina YALNIZCA bunlar giriyor.
#:
#: NEDEN LISTE, NEDEN OTOMATIK DEGIL
#: Uc kat suzgec kuruldu (anahtar, "logo" sarti, unvan dogrulamasi) ve
#: her katta yanlis eslesme azaldi ama BITMEDI. Son olcum: 188
#: sirkette 72 eslesme, dogrulama kapisindan 25'i gecti ve o 25'in de
#: yaklasik yarisi yanlisti --
#:
#:     ARDYZ (ARD Grup Bilisim) -> ARD 2019 logo   (Alman kanali)
#:     DAPGM (DAP Gayrimenkul)  -> Aerovías Dap    (Sili havayolu)
#:     AYCES (Altin Yunus)      -> Logo Altin      (baska bir sey)
#:
#: Desen su: kisa ve yaygin bir marka adi dunyada baska bir seyin de
#: adi. Hicbir metin kurali bunu ayirt edemez, cunku fark METINDE
#: DEGIL DUNYADA.
#:
#: Bu yuzden karar: otomatik arama BULUR, insan ONAYLAR. Ayni desen
#: `gorsel_uret.ONAYLI` icinde de var ve ayni sebeple.
#:
#: Kapsam dusuk (188'de ~15) ve bu KABUL EDILEN bedel. Onaysiz sirket
#: uretilmis amblemle kaliyor; amblem hicbir zaman yanlis olmuyor.
ONAYLI: frozenset = frozenset({
    "AKBNK",   # Akbank logo.svg
    "ALARK",   # Alarko Holding logo.svg
    "ALCTL",   # Alcatel logo 2016.svg  (Alcatel Lucent Teletas)
    "ALTNY",   # Altinay Teknoloji Grubu logo.svg
    "ARZUM",   # Arzum logo.png
    "ASELS",   # ASELSAN logo.svg
    "AYGAZ",   # Aygaz logo.svg
    "ENERY",   # Enerya logo.svg
    "ENJSA",   # EnerjiSA logo.svg
    "ENKAI",   # Enka logo.svg
    "FORTE",   # Forte logo.svg
    "FZLGY",   # Fuzul logo.png
    "GARAN",   # Garanti Bankasi Logo.svg
    "INGRM",   # Ingram Micro logo.svg
    "MAVI",    # Mavi logo.svg
})


def _uygun_lisans(em: dict) -> bool:
    lis = _sadelestir((em.get("LicenseShortName") or {}).get("value", ""))
    return any(k in lis for k in KABUL)


def _eslesiyor(baslik: str, anahtar: str) -> bool:
    """Dosya adi gercekten BU SIRKETIN logosu mu?

    Kural dort parcali ve hepsi ZORUNLU:
      1. Gurultu kelimesi ya da TARIHCE yili gecmeyecek.
      2. Dosya adinda "logo" gececek.
      3. Anahtar KELIME SINIRINDA gececek.
      4. Dosya adi kisa olacak (en cok bes kelime).

    Ikinci madde bir ara gevsetilmisti ("logo gecsin YA DA ad kisa
    olsun"), cunku `File:Garanti BBVA 2019.svg` gibi dogru logolar
    eleniyordu. Ama gevseklik cok daha fazla YANLIS eslesme getirdi.
    Kapsam yerine dogruluk secildi: eksik logo, yanlis logodan iyidir.

    Ucuncu madde de olculdu: duz `in` kontrolu "ard" anahtarini
    "bundesarbeitskreis" icinde bulabiliyor. Kelime siniri sart.
    """
    # KISA ANAHTAR HICBIR ZAMAN KABUL EDILMEZ.
    # Uc harfli bir anahtar ("eth", "ard") dunyada yuzlerce baska
    # seyin kisaltmasi. Sinir `ara()` icinde de var; burada da
    # duruyor ki kural TEK BASINA bu fonksiyonu okuyan icin de
    # gorunur olsun -- iki yerde tutulan bir kural ayrisir, ama bu
    # ikisi ayni dosyada ve yan yana.
    if len(anahtar) < 4:
        return False
    b = _sadelestir(baslik)
    b = re.sub(r"^file:", "", b).rsplit(".", 1)[0]
    if GURULTU.search(b) or _ESKI_YIL.search(b):
        return False
    if "logo" not in b:
        return False
    if not re.search(r"(?<![a-z0-9])" + re.escape(anahtar) + r"(?![a-z0-9])",
                     b):
        return False
    return len(b.split()) <= 5


def ara(kod: str, ad: str, adet: int = 10) -> dict | None:
    """Commons'ta logo arar. Uygun sonuc yoksa None.

    Iki sorgu deneniyor: once sirket adi, sonra BIST kodu. Kodun tek
    basina aranmasi riskli (uc harfli kodlar baska seylerle eslesir),
    bu yuzden kod sorgusunda da ayni katı esleme uygulaniyor.
    """
    if httpx is None:
        return None
    # BIST KODUYLA ARAMA KALDIRILDI.
    # ------------------------------
    # Ilk surumde unvandan anahtar cikmazsa BIST kodu kullaniliyordu.
    # Olculdu (2026-08-23): 44 sirketin 20'sinde "logo bulundu" dendi
    # ve cogu YANLISTI --
    #
    #     ETH   -> File:ETH Zürich Logo.svg        (Isvicre universitesi)
    #     ATATP -> File:ATP Tour logo.svg          (tenis turnuvasi)
    #     DAGI  -> File:IslamDagiTaburuFlag.png    (bir milis bayragi)
    #     BAKAB -> Alman ogretmen dernegi
    #
    # Dort-bes harfli kodlar dunyada yuzlerce baska seyin kisaltmasi.
    # Kendi yazdigim "yanlis logo, eksik logodan kotudur" kuralini
    # kendi yedegim cigniyordu.
    #
    # Anahtar yalnizca SIRKET UNVANINDAN cikiyor. Cikmazsa logo yok.
    anahtar = ayirt_edici(ad)
    if not anahtar or len(anahtar) < 4:
        return None

    for sorgu in (f"{anahtar} logo",):
        try:
            r = httpx.get(API, params={
                "action": "query", "format": "json",
                "generator": "search", "gsrsearch": sorgu,
                "gsrnamespace": 6, "gsrlimit": adet,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size|mime",
            }, headers=BASLIKLAR, timeout=ZAMAN_ASIMI)
            r.raise_for_status()
        except Exception:
            continue
        sayfalar = (r.json().get("query") or {}).get("pages", {})
        adaylar = []
        for pg in sayfalar.values():
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata") or {}
            baslik = pg.get("title", "")
            if not _eslesiyor(baslik, anahtar):
                continue
            if not _uygun_lisans(em):
                continue
            mime = ii.get("mime", "")
            if mime not in ("image/svg+xml", "image/png"):
                continue
            adaylar.append({
                "baslik": baslik,
                "url": ii.get("url", ""),
                "mime": mime,
                "lisans": (em.get("LicenseShortName") or {}).get("value", ""),
                "kaynak": ii.get("descriptionurl", ""),
            })
        if adaylar:
            # SVG once: her boyutta net ve dosyasi kucuk.
            adaylar.sort(key=lambda a: (a["mime"] != "image/svg+xml",
                                        len(a["baslik"])))
            return adaylar[0]
    return None


def indir(aday: dict, kod: str) -> str | None:
    """Logoyu diske yazar, site ici yolu doner."""
    if httpx is None:
        return None
    uz = ".svg" if aday["mime"] == "image/svg+xml" else ".png"
    KLASOR.mkdir(parents=True, exist_ok=True)
    hedef = KLASOR / f"{kod.lower()}{uz}"
    try:
        g = httpx.get(aday["url"], headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                      follow_redirects=True)
        g.raise_for_status()
    except Exception:
        return None
    if not g.headers.get("content-type", "").startswith("image/"):
        return None
    hedef.write_bytes(g.content)
    return f"/statik/logo/{hedef.name}"


def kayit_oku() -> dict:
    if KAYIT.exists():
        try:
            return json.loads(KAYIT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def kayit_yaz(d: dict) -> None:
    KAYIT.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def doldur(sirketler: dict[str, str], bekle: float = 0.4) -> dict:
    """{kod: ad} icin logo arar ve indirir. Kayit sozlugunu doner.

    ZATEN BAKILMIS SIRKETE TEKRAR BAKILMIYOR -- bulunamayanlar da
    kayda "yok" olarak yaziliyor. Yoksa her calistirmada 188 sorgu
    tekrarlanir ve Commons'a gereksiz yuk biner.
    """
    kayit = kayit_oku()
    yeni = 0
    for kod, ad in sirketler.items():
        if kod in kayit:
            continue
        aday = ara(kod, ad)
        if aday is None:
            kayit[kod] = {"yok": True}
        else:
            yol = indir(aday, kod)
            if yol is None:
                kayit[kod] = {"yok": True}
            else:
                kayit[kod] = {"yol": yol, "lisans": aday["lisans"],
                              "kaynak": aday["kaynak"],
                              "baslik": aday["baslik"]}
                yeni += 1
                print(f"  + {kod:8} {aday['baslik'][:56]}")
        kayit_yaz(kayit)
        time.sleep(bekle)
    print(f"\n{yeni} yeni logo, kayitta toplam "
          f"{sum(1 for v in kayit.values() if not v.get('yok'))}")
    return kayit


def main() -> int:
    site = _KOK.parent.parent / "site" / "icerik" / "analizler"
    sirketler: dict[str, str] = {}
    for p in sorted(site.glob("*.md")):
        m = p.read_text(encoding="utf-8")
        k = re.search(r"^kod:\s*(.+)$", m, re.M)
        s = re.search(r"^sirket:\s*(.+)$", m, re.M)
        if k and s and k.group(1).strip().isalpha():
            sirketler.setdefault(k.group(1).strip(), s.group(1).strip())
    print(f"{len(sirketler)} sirket taranacak")
    doldur(sirketler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
