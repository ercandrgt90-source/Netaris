"""Statik site ureteci.

    site/icerik/*.md  ->  site/cikti/**/index.html

Calistirmak icin:
    python insa.py            # siteyi uret
    python insa.py --sun      # uret ve yerel sunucuda ac (http://localhost:8000)

Tasarim notlari
---------------
* **Harici bagimlilik yok.** Yazi tipleri sistemden, CSS tek dosya, JavaScript
  yok. Sayfa hizli acilir; ucuncu parti istegi olmadigi icin KVKK/GDPR
  tarafinda cerez/izleyici sorunu cikmaz.

* **URL yapisi WordPress'e tasinabilir.** /analiz/<slug>/ bicimi hem statik
  hem WordPress'te ayni sekilde kurulabilir. Faz 2'de CMS'e gecilirse
  adresler korunur, SEO otoritesi yanmaz.

* **Kurgusal icerik isaretlenir.** Frontmatter'da `kurgusal: evet` varsa
  sayfada uyari bandi cikar. Ornek icerigin gercek analiz gibi gorunmesi
  kabul edilemez.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

import gorsel
import kivilcim
import piyasa_kutusu

# Arastirma dosyasi motoru haber_botu/analiz altinda; site buradan
# YALNIZCA OKUYOR (depoya salt-okunur baglaniyor).
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent
                       / "haber_botu" / "analiz"))
try:
    import dosya as _dosya
except ImportError:
    _dosya = None
try:
    import varlik as _varlik
except ImportError:
    _varlik = None

# Depo. Site buraya YAZIYOR (yalnizca iki alan: haberin gercek adresi ve
# varlik baglari) -- ikisi de ancak site kurulurken belli oluyor.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "haber_botu"))
try:
    import beyin as _beyin
except ImportError:      # depo yoksa site varlik indeksi olmadan kurulur
    _beyin = None

# Fotograf havuzu ve konu siniflandirici haber hattinda yasiyor. Buradan
# YALNIZCA OKUNUYOR -- `Kayit()` var olan defteri aciyor, indirme yapmaz.
# Site uretimi sirasinda ag istegi olmamali: hat coktugunde site yine
# kurulabilmeli.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent
                       / "haber_botu" / "kaynak"))
try:
    import besleme as _besleme
    import foto as _foto
except ImportError:      # haber_botu yoksa site fotografsiz kurulur
    _besleme = None
    _foto = None

# Haber baglami (neden onemli / aktarim kanallari). Arsiv sayfalari
# yeniden uretilirken bu da yeniden hesaplaniyor -- bkz. `tazele()`.
try:
    import gundem_yorum as _yorum
except ImportError:
    _yorum = None

# Olay motoru. Senaryo bolumu YALNIZCA esigi gecen haberlerde aciliyor.
try:
    import olay as _olay
except ImportError:
    _olay = None

# Veri aciklamasi hatti. Bu haberler seriden uretiliyor; konusu ve
# gerekcesi baslikten degil serinin tanimindan geliyor.
try:
    import takvim as _takvim
except ImportError:
    _takvim = None

#: Veri aciklamasi haberlerinin adres oneki (bkz. `takvim.Aciklama.adres`)
_VERI_ONEK = "netaris:veri/"

KOK = pathlib.Path(__file__).parent
ICERIK = KOK / "icerik"
SABLON = KOK / "sablonlar"
STATIK = KOK / "statik"
CIKTI = KOK / "cikti"

# ---------------------------------------------------------------------------
# Site ayarlari
# ---------------------------------------------------------------------------
# ADRES alan adi belli olunca degistirilecek. Sonunda egik cizgi OLMAYACAK.
# Yer tutucu bilincli olarak dikkat cekici: yayina cikmadan once degismeli.

SITE = {
    "ad": "Netaris",
    # Marka adi TEK PARCA yaziliyor. Onceden "Net" ve "aris" iki ayri renkti;
    # kelimeyi ikiye bolunmus gosteriyordu. Renk gecisi artik kelimenin
    # tamamina uygulaniyor (stil.css .marka), yani ad bitisik okunuyor.
    "ad_html": '<span class="marka">Netaris</span>',
    "slogan": "Yapay zekâ destekli finans araştırma platformu",
    #: Hero altindaki tek satirlik konumlandirma
    "hero_satirlar": (
        "Bilançoları okur.",
        "Merkez bankalarını takip eder.",
        "Makro verileri yorumlar.",
        "Küresel gelişmeleri ilişkilendirir.",
    ),
    # Ana sayfadaki giris metni. Arama sonuclarinda ve paylasim onizlemesinde
    # de bu gorunur, o yuzden tek yerde tutuluyor.
    "aciklama": (
        "Netaris; şirket bilançolarını, ekonomik verileri, merkez bankası "
        "kararlarını ve küresel gelişmeleri yapay zekâ destekli analiz "
        "motoruyla bir araya getirir. Her içerik; doğrulanmış veriler, resmî "
        "kaynaklar ve neden-sonuç ilişkileriyle hazırlanır. Amacımız yalnızca "
        "haber sunmak değil; yatırımcıların, araştırmacıların ve içerik "
        "üreticilerinin daha doğru kararlar almasını sağlayacak kapsamlı bir "
        "finansal bilgi ekosistemi oluşturmaktır."
    ),
    # Meta aciklama icin kisa surum -- arama sonucunda uzun metin kirpilir
    "meta_aciklama": (
        "Şirket bilançoları, ekonomik veriler ve küresel gelişmeler; "
        "doğrulanmış verilere ve neden-sonuç ilişkilerine dayanan analizlerle."
    ),
    "adres": "https://netaris.com",
    "yil": datetime.now().year,
    "yasal_uyari": (
        "Bu içerik yalnızca bilgilendirme amaçlıdır, yatırım tavsiyesi "
        "değildir. Kullanılan veriler şirketin KAP'ta yayımlanan finansal "
        "tablolarından alınmıştır; hesaplamalar ve skor tarafımızca "
        "yapılmıştır. Bilanço Kalitesi Skoru finansal tabloların sağlığını "
        "ölçer; hissenin fiyatı, değerlemesi veya getirisi hakkında bir "
        "değerlendirme içermez."
    ),
}

AYLAR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

#: (slug, menu basligi, frontmatter kategorisi, sayfa aciklamasi)
#: Bos kategori sayfasi URETILMEZ -- tiklayinca bos sayfa cikan bir menu
#: sekmesi, o sekmenin hic olmamasindan kotudur.
KATEGORILER = (
    (
        "bilancolar", "Bilançolar", "Bilanço Analizi",
        "BIST şirketlerinin finansal tabloları. Her analizde oranlar ve "
        "sinyaller koddan hesaplanır; sektöre göre farklı motor çalışır.",
    ),
    (
        "makro", "Makro", "Makro",
        "Küresel göstergeler, faiz kararları ve emtia fiyatları; bunların "
        "Türkiye'ye hangi kanallardan geçtiği.",
    ),
    (
        "yorum", "Yorum", "Analist Yorumu",
        "İmzalı analist değerlendirmeleri. Otomatik analizlerimizden farklı "
        "olarak yorum, neden-sonuç ilişkisi ve gelecek senaryoları içerir; "
        "sorumluluk yazarına aittir.",
    ),
    (
        "teknik", "Teknik", "Teknik Görünüm",
        "Kripto varlıklar ve altın için hareketli ortalamalar, RSI, MACD, "
        "oynaklık ve fiyat seviyeleri. Göstergelerin durumu bildirilir; "
        "işlem önerisi içermez.",
    ),
)

#: Kaynak rozetlerinin acik adlari -- kisaltma tek basina anlam tasimayabilir
KAYNAK_ADLARI = {
    "KAP": "Kamuyu Aydınlatma Platformu",
    "FRED": "FRED — St. Louis Fed",
    "TCMB": "Türkiye Cumhuriyet Merkez Bankası",
    "ECB": "Avrupa Merkez Bankası",
    "TUIK": "Türkiye İstatistik Kurumu",
}

# Turkce harfleri URL'de guvenli karsiliklarina cevir. unicodedata tek
# basina "ı" harfini dogru cozmez, bu yuzden elle esleme yapiyoruz.
_SLUG_ESLEME = str.maketrans(
    {
        "ı": "i", "İ": "i", "I": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
        "â": "a", "î": "i", "û": "u",
    }
)


def slugla(metin: str) -> str:
    metin = unicodedata.normalize("NFC", metin).translate(_SLUG_ESLEME).lower()
    metin = re.sub(r"[^a-z0-9]+", "-", metin)
    return metin.strip("-")


def tarih_tr(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.day} {AYLAR[d.month - 1]} {d.year}"


# ---------------------------------------------------------------------------
# Frontmatter ayristirma
# ---------------------------------------------------------------------------

@dataclass
class Kriter:
    ad: str
    puan: str
    tam: str

    @property
    def yuzde(self) -> float:
        """Olcer genisligi. Kayan nokta gurultusu HTML'e sizmasin diye
        yuvarlaniyor -- "57.99999999999999%" gibi degerler ciktiyi kirletir."""
        try:
            oran = float(self.puan.replace(",", ".")) / float(self.tam.replace(",", "."))
        except (ValueError, ZeroDivisionError):
            return 0.0
        return round(min(1.0, max(0.0, oran)) * 100, 1)


@dataclass
class Belge:
    alanlar: dict[str, str] = field(default_factory=dict)
    kriterler: list[Kriter] = field(default_factory=list)
    govde_md: str = ""

    def al(self, anahtar: str, varsayilan: str = "") -> str:
        return self.alanlar.get(anahtar, varsayilan)


def ayristir(yol: pathlib.Path) -> Belge:
    """--- ile sinirlandirilmis basit anahtar: deger blogunu okur.

    YAML kullanmiyoruz: tek bir kucuk bagimlilik daha eklemeye degmez ve
    ihtiyacimiz olan bicim bu kadar basit. `kriter:` satiri tekrarlanabilir
    ve `ad|puan|tam` bicimindedir.

    `utf-8-sig` bilincli bir secim: Windows araclari (PowerShell'in
    Set-Content'i, Not Defteri) dosya basina gorunmez bir BOM isareti
    ekliyor. Duz utf-8 ile okunursa dosya "---" ile baslamiyor gorunur,
    frontmatter sessizce yok sayilir ve sayfa meta aciklamasiz cikar.
    Hicbir hata mesaji da vermez -- bu yuzden tam burada engelliyoruz.
    """
    ham = yol.read_text(encoding="utf-8-sig")
    belge = Belge()

    if not ham.startswith("---"):
        belge.govde_md = ham
        return belge

    _, on, govde = ham.split("---", 2)
    belge.govde_md = govde.lstrip("\n")

    for satir in on.strip().splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        if ":" not in satir:
            continue
        anahtar, deger = satir.split(":", 1)
        anahtar, deger = anahtar.strip(), deger.strip()
        if anahtar == "kriter":
            parcalar = [p.strip() for p in deger.split("|")]
            if len(parcalar) == 3:
                belge.kriterler.append(Kriter(*parcalar))
        else:
            belge.alanlar[anahtar] = deger
    return belge


#: `attr_list` OLMADAN "## Baslik {#capa}" yazimi calismaz: capa
#: uretilmez ve "{#capa}" metni sayfada AYNEN gorunur. Bu sessiz bir
#: bicimlendirme hatasiydi -- yayin ilkelerinde "{#skor}" ekranda yaziyordu.
MD_EKLENTILER = ["tables", "sane_lists", "attr_list"]


def md_html(metin: str) -> str:
    cikti = markdown.markdown(metin, extensions=MD_EKLENTILER)
    # Genis tablolar dar ekranda sayfayi degil kendi kutusunu kaydirmali
    return cikti.replace("<table>", '<div class="tablo-kaydir"><table>').replace(
        "</table>", "</table></div>"
    )


def _basliklari_indir(metin: str) -> str:
    """Markdown baslik seviyelerini bir kademe asagi ceker.

    Birlestirilmis sayfada her kaynak dosya bir <h2> bolumu oluyor; kendi
    icindeki "##" basliklari da "###" olmali ki belge hiyerarsisi bozulmasin.
    Satir basindaki diyezler hedeflenir, metin icindekilere dokunulmaz.
    """
    return re.sub(r"(?m)^(#{1,5})(\s)", r"#\1\2", metin)


# ---------------------------------------------------------------------------
# Icerik yukleme
# ---------------------------------------------------------------------------

@dataclass
class Analiz:
    slug: str
    baslik: str
    ozet: str
    sirket: str
    kod: str
    donem: str
    kategori: str
    tarih: str
    tarih_tr: str
    veri_kaynagi: str
    kurgusal: bool
    skor: str | None
    kapsam: str
    kriterler: list[Kriter]
    govde: str
    sektor: str = ""
    gorsel_svg: str = ""
    kelime: int = 0
    #: ("KAP", "FRED") gibi -- sayfada kaynak rozeti olarak gorunur
    kaynaklar: tuple[str, ...] = ()
    #: (sayi, etiket) ciftleri -- "nasil uretildi" kutusunu besler
    sayimlar: tuple[tuple[str, str], ...] = ()
    #: Imzali yorumlarda dolu; otomatik analizlerde bos
    yazar: str = ""
    unvan: str = ""
    #: Kartlarda ve yazi basinda kullanilan gercek fotograf. Havuzda konuya
    #: uygun gorsel yoksa bos kalir ve SVG grafige dusulur.
    foto: str = ""
    foto_atif: str = ""

    @property
    def imzali(self) -> bool:
        return bool(self.yazar)

    @property
    def gun_yasi(self) -> int:
        """Yayin tarihinden bu yana gecen gun."""
        try:
            d = datetime.strptime(self.tarih, "%Y-%m-%d").date()
        except ValueError:
            return 0
        return (datetime.now().date() - d).days

    @property
    def eskimis(self) -> bool:
        """Piyasa yorumunun tazeligini yitirdigi esik.

        Bir haftadan eski bir piyasa yorumunda "su an", "bugun", "surduruyor"
        gibi ifadeler okuru yanilir: yazildiginda dogruydu ama artik oyle
        olmayabilir. Ornegin 23 Temmuz'da zirvede olan Brent, dort gun sonra
        %12,8 asagidaydi. Yaziyi degistirmek yerine tarihini one cikarmak
        dogru olan -- yazar o gun yazdigini yazdi.
        """
        return self.gun_yasi >= 7

    @property
    def yol(self) -> str:
        return f"/analiz/{self.slug}/"

    @property
    def okuma_dk(self) -> int:
        """Tahmini okuma suresi. Dakikada ~200 kelime kabul edilir."""
        return max(1, round(self.kelime / 200))

    @property
    def skor_yuzde(self) -> float:
        """Skor halkasi icin doldurma orani."""
        try:
            return round(min(100.0, max(0.0, float(str(self.skor).replace(",", ".")))), 1)
        except (TypeError, ValueError):
            return 0.0


#: (slug, sablon adi, sayfa basligi, aciklama)
#:
#: Uculu de arama motoruna KAPALI ve site haritasina girmiyor: giris formu
#: ve panel dizine girecek icerik degil, ayrica indekslenmis bir panel
#: adresi gereksiz bot trafigi ceker.
UYELIK_SAYFALARI = (
    ("giris", "giris", "Giriş yap",
     "Netaris hesabınıza giriş yapın."),
    ("kayit", "kayit", "Üye ol",
     "Netaris'te yazı yazmak için hesap oluşturun."),
    ("panel", "panel", "Panel",
     "Yazılarınızı buradan yazar ve incelemeye gönderirsiniz."),
)


#: Analiz kategorisi -> fotograf konusu. Baslikta bir konu bulunamazsa
#: buraya dusulur. Anahtarlar `foto.KONU_ARAMA` ile ayni olmali.
KATEGORI_FOTO = {
    "Bilanço Analizi": "Şirket haberleri",
    "Makro": "Para politikası",
    "Analist Yorumu": "Para politikası",
    "Teknik Görünüm": "Kripto varlıklar",
}


def analiz_fotografi(kayit, baslik: str, kategori: str, kod: str) -> tuple[str, str]:
    """Analize gercek fotograf secer. (yol, atif) doner; yoksa ("", "").

    Konu once BASLIKTAN cikarilir -- haber hattindaki siniflandiricinin
    aynisi kullaniliyor, boylece "Brent %41,7 yukselip geri cekildi"
    enerji fotografi, "Altin (PAXG)" emtia fotografi aliyor. Baslik bir sey
    soylemezse kategori varsayilanina dusuluyor.
    """
    if kayit is None or _besleme is None:
        return "", ""
    varsayilan = KATEGORI_FOTO.get(kategori, "Para politikası")
    # Teknik yazilarda kodu da metne katiyoruz: "PAXG" gecince emtia,
    # "BTC/ETH" gecince kripto fotografi secilsin.
    konu = _besleme.konu_bul(f"{baslik} {kod}", varsayilan)
    f = kayit.sec(konu, baslik)
    if f is None and konu != varsayilan:
        f = kayit.sec(varsayilan, baslik)
    if f is None:
        return "", ""
    # CC BY atfi zorunlu -- gorselin altinda basilir, kaldirilirsa lisans
    # ihlal edilir.
    return f.dosya, f.kisa_atif


#: Imzasi olmayan yazilarin kunyesi.
#:
#: Bu yazilari bir insan yazmiyor: gostergeler cekiliyor, hesap koda gomulu
#: kurallarla yapiliyor, metin sablondan uretiliyor. Kunyeye uydurma bir
#: yazar adi koymak -- mockup'ta oldugu gibi bes ayri isim ve vesikalik --
#: okura yalan soylemek olurdu. Uretici neyse o yaziliyor.
KURUM_IMZASI = ("Netaris Analiz", "Kural tabanlı üretim")


def yorum_kartlari(analizler: list, en_fazla: int = 6) -> list[dict]:
    """Ana sayfadaki "Yorum ve kose yazilari" seridi.

    IMZALI yazilar once. Kalan yerler otomatik analizlerle doluyor ve
    onlar KURUM_IMZASI ile basiliyor.
    """
    imzali = [a for a in analizler if a.imzali]
    imzasiz = [a for a in analizler if not a.imzali]
    kartlar = []
    for a in (imzali + imzasiz)[:en_fazla]:
        ad = a.yazar or KURUM_IMZASI[0]
        kartlar.append({
            "yol": a.yol,
            "baslik": a.baslik,
            "ozet": a.ozet,
            "yazar_adi": ad,
            "yazar_unvani": a.unvan or (a.kategori if a.imzali
                                        else KURUM_IMZASI[1]),
            # Vesikalik yok -- var olmayan insanin fotografi olmaz.
            # Bas harf hem imzali hem kurumsal kunyede calisiyor.
            "bas_harf": bicim_buyut(ad[:1]),
            "imzali": a.imzali,
        })
    return kartlar


def bicim_buyut(harf: str) -> str:
    """Turkce'ye gore buyutur: "i" -> "İ", "ı" -> "I".

    `str.upper()` "islem"i "ISLEM" yapiyor ve bas harf "I" cikiyor;
    dogrusu "İ". Tek harf icin bile onemli, cunku kunye dairesinde
    tek basina duruyor.
    """
    return harf.translate(str.maketrans({"i": "İ", "ı": "I"})).upper()


def kunye_rakamlari(analizler: list) -> list[dict]:
    """Ana sayfadaki guven seridi -- HEPSI GERCEK SAYIM.

    Hicbiri elle yazilmis bir hedef ya da yuvarlanmis bir pazarlama rakami
    degil: analiz sayisi klasordeki dosyadan, sirket sayisi KAP'tan cekilen
    defterden, gosterge sayisi cekilen seri sayisindan geliyor. Sitede
    "12.450 analiz" yazip 2 analiz yayimlamak, kurmaya calistigimiz guveni
    ilk gun bitirirdi.
    """
    kayit = KOK.parent / "haber_botu" / "kaynak" / "sirketler.json"
    sirket_sayisi = 0
    if kayit.exists():
        try:
            sirket_sayisi = json.loads(kayit.read_text(encoding="utf-8"))["sirket_sayisi"]
        except (json.JSONDecodeError, KeyError, OSError):
            sirket_sayisi = 0

    g = gostergeleri_yukle()
    gosterge_sayisi = len(g.get("kalemler", []))

    rakamlar = [{"sayi": f"{len(analizler)}", "etiket": "yayımlanmış analiz"}]
    if sirket_sayisi:
        rakamlar.append({
            "sayi": f"{sirket_sayisi:,}".replace(",", "."),
            "etiket": "BIST şirketi izleniyor",
        })
    if gosterge_sayisi:
        rakamlar.append({"sayi": f"{gosterge_sayisi}", "etiket": "küresel gösterge"})
    rakamlar.append({"sayi": "%100", "etiket": "hesaplama koddan"})
    return rakamlar


#: Haber konusu -> o haberle ilgili gosterge kodlari.
#: Haber sayfasina KENDI verimizi ekliyoruz: petrol haberinin yaninda
#: bizim Brent serimiz, faiz haberinin yaninda bizim getiri serimiz durur.
#: Boylece sayfa yalnizca ceviri degil, veriyle desteklenmis bir ozet olur.
KONU_GOSTERGELERI = {
    "Para politikası": ("DFF", "DGS2", "DGS10", "T10Y2Y"),
    "Enflasyon": ("DGS10", "T10Y2Y", "VIXCLS"),
    "Enerji": ("DCOILBRENTEU", "DCOILWTICO"),
    "Jeopolitik": ("DCOILBRENTEU", "VIXCLS", "DTWEXBGS"),
    "Bankacılık": ("DGS10", "VIXCLS"),
    "Piyasa düzenlemesi": ("SP500", "VIXCLS"),
    "Düzenleme": ("SP500", "VIXCLS"),
}


def ilgili_gostergeler(konu: str, gostergeler: dict) -> list[dict]:
    """Haberin konusuyla ilgili kendi gosterge verimizi dondurur.

    Ilgili gosterge yoksa BOS liste doner ve sayfada o bolum hic basilmaz --
    konuyla alakasiz bir gosterge koymak, veriyle destekliyormus gibi
    gorunup aslinda gurultu eklemek olur.
    """
    kodlar = KONU_GOSTERGELERI.get(konu, ())
    if not kodlar:
        return []
    bul = {k.get("kod"): k for k in gostergeler.get("kalemler", [])}
    return [bul[k] for k in kodlar if k in bul]


def gundem_yukle() -> dict:
    """Resmi kurum duyuru akisini okur.

    Dosya yoksa gundem bolumu hic basilmaz -- bos bir akis, guncellenmeyen
    bir bolum izlenimi verir.
    """
    yol = ICERIK / "gundem.json"
    if not yol.exists():
        return {}
    try:
        return json.loads(yol.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def gostergeleri_yukle() -> dict:
    """Ust seritteki gosterge verisini okur.

    Dosya yoksa serit hic basilmaz -- bos ya da yer tutucu bir serit,
    olmayan bir veri akisi varmis izlenimi verir.
    """
    yol = ICERIK / "gostergeler.json"
    if not yol.exists():
        return {}
    try:
        return json.loads(yol.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


#: Fotograf defteri. BIR KEZ aciliyor -- her yazi icin yeniden okumak
#: ayni JSON'u onlarca kez ayristirmak olurdu. Hem analiz hem arsiv
#: sayfalari ayni defteri kullaniyor; `Kayit()` var olan defteri acar,
#: indirme YAPMAZ (site uretimi sirasinda ag istegi olmamali).
_foto_defteri = None


def foto_defteri():
    global _foto_defteri
    if _foto_defteri is None and _foto is not None:
        _foto_defteri = _foto.Kayit()
    return _foto_defteri


def analizleri_yukle() -> list[Analiz]:
    klasor = ICERIK / "analizler"
    liste: list[Analiz] = []
    _foto_kayit = foto_defteri()

    for yol in sorted(klasor.glob("*.md")):
        b = ayristir(yol)
        tarih = b.al("tarih", datetime.now().strftime("%Y-%m-%d"))
        baslik = b.al("baslik", yol.stem)
        skor = b.al("skor") or None

        kod = b.al("kod")
        kategori = b.al("kategori", "Bilanço Analizi")

        # Gorsel yazinin kendi rakamlarindan cizilir. Grafik verisi yoksa
        # sade zemin uretilir -- temsili/uydurma bir grafik CIZILMEZ.
        gorsel_svg = gorsel.uret(
            tur=b.al("grafik_tur"),
            ham=b.al("grafik"),
            kod=b.al("grafik_kod") or (kod if kod and kod != "MAKRO" else ""),
            konu=b.al("sirket") or baslik,
            birim=b.al("grafik_birim"),
        )
        foto_yol, foto_atif = analiz_fotografi(_foto_kayit, baslik, kategori, kod)

        liste.append(
            Analiz(
                slug=b.al("slug") or slugla(yol.stem),
                baslik=baslik,
                ozet=b.al("ozet"),
                sirket=b.al("sirket"),
                kod=kod,
                donem=b.al("donem"),
                kategori=kategori,
                tarih=tarih,
                tarih_tr=tarih_tr(tarih),
                veri_kaynagi=b.al("veri_kaynagi", "KAP finansal tabloları"),
                kurgusal=b.al("kurgusal", "hayir").lower() in ("evet", "yes", "true"),
                skor=skor,
                kapsam=b.al("kapsam", "100"),
                kriterler=b.kriterler,
                govde=md_html(b.govde_md),
                sektor=b.al("sektor"),
                gorsel_svg=gorsel_svg,
                foto=foto_yol,
                foto_atif=foto_atif,
                kelime=len(b.govde_md.split()),
                kaynaklar=tuple(
                    x.strip() for x in b.al("kaynaklar").split(",") if x.strip()
                ),
                sayimlar=tuple(
                    tuple(p.strip() for p in parca.split("|", 1))  # type: ignore[misc]
                    for parca in b.al("sayimlar").split(";")
                    if "|" in parca
                ),
                yazar=b.al("yazar"),
                unvan=b.al("unvan"),
            )
        )

    # En yeni en ustte
    liste.sort(key=lambda a: (a.tarih, a.slug), reverse=True)
    return liste


def guncel_olanlar(analizler: list[Analiz]) -> list[Analiz]:
    """Yinelenen otomatik analizlerden yalnizca EN GUNCELINI birakir.

    NEDEN GEREKLI -- misafir gozuyle olculdu:
    Ana sayfadaki 16 analizin 13'u birbirinin ayniydi.

        Bitcoin: 200 gunluk ortalamanin %10,0 altinda      (3 gun)
        Ethereum: 200 gunluk ortalamanin %10,1 altinda     (3 gun)
        Altin: 200 gunluk ortalamanin %11,6 altinda        (3 gun)
        Brent %41,7 yukselip geri cekildi: ...             (4 gun, AYNI baslik)

    Teknik gorunum ve makro ozet her gun yeniden uretiliyor; dun ile
    bugun arasindaki fark birkac ondalik. Okur icin bu bir arsiv degil,
    tekrar. Ustelik ayni baslik dort ayri adreste durdugu icin arama
    motoruna da yinelenen icerik sinyali gidiyor.

    ELEME LISTEDE, DOSYADA DEGIL: eski sayfalar yayimlanmaya devam
    ediyor, adresleri kirilmiyor. Yalnizca listelerde en guncel surum
    gorunuyor.

    Olcut `(kategori, kod)`: ayni varligin ayni turdeki analizi. Elle
    yazilmis yazilarda `kod` bos oldugu icin onlar HIC elenmez -- her
    biri kendi basina icerik.
    """
    gorulen: set[tuple[str, str]] = set()
    cikti: list[Analiz] = []
    for a in analizler:                       # liste zaten yeniden eskiye
        if not a.kod:
            cikti.append(a)
            continue
        imza = (a.kategori, a.kod)
        if imza in gorulen:
            continue
        gorulen.add(imza)
        cikti.append(a)
    return cikti


@dataclass
class Sayfa:
    slug: str
    baslik: str
    ozet: str
    govde: str

    @property
    def yol(self) -> str:
        return f"/{self.slug}/"


@dataclass
class Bolum:
    """Hakkimizda sayfasindaki tek bir alt bolum."""

    capa: str
    baslik: str
    ozet: str
    govde: str


#: Yasal metinler, hakkimizda sayfasinin ALTINDA bu sirayla.
HAKKIMIZDA_SIRASI = ("yayin-ilkeleri", "kunye", "gizlilik")

#: Sayfa ici gezinmede h2 basliklarini yakalar. Capalar markdown'da
#: "{#capa}" ile elle verilir; boylece baglantilar baslik metni degisse
#: bile kirilmaz.
_H2_DESEN = re.compile(r'<h2 id="([^"]+)">(.*?)</h2>', re.S)


@dataclass
class Hakkimizda:
    lead: str
    govde: str
    bolumler: list[Bolum]
    #: (capa, baslik) ciftleri -- sayfa ici gezinme icin
    gezinme: list[tuple[str, str]]


def hakkimizda_yukle() -> Hakkimizda | None:
    """Giris metnini ve yasal bolumleri tek sayfada birlestirir.

    Dosyalar AYRI kaliyor -- birlestirme insa aninda yapiliyor. Elle
    kopyalamak, dort metni tek dosyaya yapistirmak demek olurdu ve sonraki
    duzenlemede hangisinin guncel oldugu karisirdi.
    """
    giris_yolu = ICERIK / "sayfalar" / "hakkimizda.md"
    if not giris_yolu.exists():
        return None

    g = ayristir(giris_yolu)
    giris_html = md_html(g.govde_md)

    # Giris icindeki h2'ler dogrudan gezinmeye girer
    gezinme = [
        (capa, re.sub(r"<[^>]+>", "", baslik).strip())
        for capa, baslik in _H2_DESEN.findall(giris_html)
    ]

    bolumler: list[Bolum] = []
    for ad in HAKKIMIZDA_SIRASI:
        yol = ICERIK / "sayfalar" / f"{ad}.md"
        if not yol.exists():
            continue
        b = ayristir(yol)
        capa = b.al("slug") or slugla(yol.stem)
        baslik = b.al("baslik", yol.stem)
        bolumler.append(
            Bolum(
                capa=capa,
                baslik=baslik,
                ozet=b.al("ozet", ""),
                govde=md_html(_basliklari_indir(b.govde_md)),
            )
        )
        gezinme.append((capa, baslik))

    return Hakkimizda(
        lead=g.al("lead", ""),
        govde=giris_html,
        bolumler=bolumler,
        gezinme=gezinme,
    )


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------

def yaz(goreli: str, icerik: str) -> pathlib.Path:
    hedef = CIKTI / goreli.lstrip("/")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(icerik, encoding="utf-8")
    return hedef


def arama_dizini(analizler: list[Analiz]) -> str:
    """Istemci tarafi arama icin dizin.

    Sunucusuz bir sitede arama iki yolla yapilir: ucuncu parti arama
    hizmeti (harici istek, gizlilik yuku) ya da tarayicida calisan kucuk
    bir dizin. Ikincisi secildi -- 6 yazi icin dizin birkac kilobayt, ve
    hicbir sey disariya gitmiyor.
    """
    kayitlar = [
        {
            "b": a.baslik,
            "o": a.ozet,
            "y": a.yol,
            "k": a.kategori,
            "kod": a.kod if a.kod not in ("MAKRO", "YORUM") else "",
            "s": a.sirket,
            "t": a.tarih_tr,
            "d": a.okuma_dk,
            # Aramada eslesecek metin: diakritiksiz ve kucuk harfli
            "a": _ara_metni(f"{a.baslik} {a.ozet} {a.sirket} {a.kod} {a.kategori}"),
        }
        for a in analizler
    ]
    return json.dumps(kayitlar, ensure_ascii=False, separators=(",", ":"))


def _ara_metni(metin: str) -> str:
    """Arama icin normalize eder: diakritik atilir, kucuk harfe cevrilir.

    Turkce'de kullanici "bilanco" yazip "bilanço" bulmayi bekler. Diakritigi
    her iki tarafta da atmadan bu eslesme olmaz -- ifade taramasinda
    yasadigimiz tuzagin aynisi.
    """
    return metin.translate(_SLUG_ESLEME).lower()


def rss_uret(analizler: list[Analiz]) -> str:
    ogeler = []
    for a in analizler[:30]:
        try:
            d = datetime.strptime(a.tarih, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            pub = d.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except ValueError:
            pub = ""
        ogeler.append(
            "    <item>\n"
            f"      <title>{html.escape(a.baslik)}</title>\n"
            f"      <link>{SITE['adres']}{a.yol}</link>\n"
            f"      <guid isPermaLink=\"true\">{SITE['adres']}{a.yol}</guid>\n"
            f"      <description>{html.escape(a.ozet)}</description>\n"
            f"      <pubDate>{pub}</pubDate>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{html.escape(SITE['ad'])}</title>\n"
        f"    <link>{SITE['adres']}/</link>\n"
        f"    <description>{html.escape(SITE['aciklama'])}</description>\n"
        "    <language>tr-TR</language>\n"
        + "\n".join(ogeler)
        + "\n  </channel>\n</rss>\n"
    )


def sitemap_uret(yollar: list[str]) -> str:
    girdiler = "\n".join(
        f"  <url><loc>{SITE['adres']}{y}</loc></url>" for y in yollar
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{girdiler}\n"
        "</urlset>\n"
    )


def _cikti_temizle() -> None:
    """Cikti klasorunun ICINI bosaltir, klasorun kendisini silmez.

    Klasoru silmek, baska bir surec onu acik tuttugunda (yerel sunucu
    calisiyorsa, ya da kabuk o dizindeyse) Windows'ta PermissionError
    veriyor. Icerigi silmek ayni iso yapar ve bu tuzaga dusmez.
    """
    CIKTI.mkdir(parents=True, exist_ok=True)
    for oge in CIKTI.iterdir():
        if oge.is_dir():
            shutil.rmtree(oge)
        else:
            oge.unlink()


def haber_yolu(h: dict) -> str:
    """Haberin site adresi. Slug BASLIKTAN uretiliyor.

    Turkce baslik bosalirsa (nadir; ceviri dusmusse) kaynak basliga
    duser. Ikisi de bos kalirsa adres "/haber//" olurdu -- bu durumda
    adresten turetilen bir capa kullaniliyor.
    """
    s = (slugla(h.get("baslik") or "") or slugla(h.get("baslik_kaynak") or ""))
    s = s[:70].strip("-")
    if not s:
        # `hash()` KULLANILMAZ: Python'da dizgi ozeti surec basina
        # rastgeleleniyor (PYTHONHASHSEED), yani ayni haber her kurulumda
        # BASKA bir adres alirdi ve arsiv her gun bastan kirilirdi.
        s = "haber-" + hashlib.sha1(
            (h.get("adres") or "").encode("utf-8")).hexdigest()[:10]
    return f"/haber/{s}/"


#: Arsivden yeniden uretilecek en fazla haber sayisi.
#:
#: Sinir var cunku kurulum suresi ve Cloudflare'e yuklenen dosya sayisi
#: bununla dogru orantili. 1500 haber ~2 yillik birikim demek; o noktaya
#: gelindiginde sayfalama gerekecek, bugun gereksiz karmasiklik olurdu.
ARSIV_SINIRI = 1500


#: Senaryonun HER HABERDE degil, yalnizca kritik olanlarda acilmasi.
#:
#: Gunde 130 haber geliyor; hepsine senaryo cagrisi koymak okuru
#: seyreltir. Bir sayfada bir senaryo, digerinde otuz senaryo olur ve
#: ikisi de kotudur -- ilki terk edilmis gorunur, ikincisi okunmaz.
#:
#: Olcut UYDURULMADI: olay motoru zaten "her haber olay degildir" diye
#: kurulmus ve siddet puani hesapliyor (`olay.ESIK`). Faiz karari,
#: enflasyon verisi, istihdam verisi, jeopolitik ve arz soku o esigi
#: geciyor; haftalik istatistik bulteni gecmiyor.
#:
#: Ayrica konu suzgeci: kullanicinin isaret ettigi "senaryo yazmaya
#: deger" alanlar. Ikisi BIRLIKTE araniyor -- tek basina konu yetmez,
#: cunku "Para politikasi" konulu bir duyuru takvimi de var.
SENARYO_KONULARI = frozenset({
    "Jeopolitik", "Para politikası", "Enflasyon", "Enerji",
    "Dış ticaret", "Döviz",
})


def senaryoya_acik(h: dict) -> bool:
    """Bu haber senaryo yazmaya deger mi.

    Olay motoru yoksa (haber_botu erisilemiyor) KONUYA duser: eksik bir
    suzgec, hic suzgec olmamasindan iyi.
    """
    if h.get("konu") not in SENARYO_KONULARI:
        return False
    if _olay is None:
        return True
    o = _olay.siniflandir(h.get("baslik_kaynak") or h.get("baslik", ""),
                          h.get("kurum", ""))
    return _olay.esigi_gecti(o)


def gun_farki(tarih: str, bugun: str) -> int:
    """Iki ISO tarih arasindaki gun. Cozulemezse 0 -- yani "taze" sayilir.

    Bilinmeyen tarihte uyari BASILMIYOR: yanlis uyari, uyarinin kendisini
    degersizlestirir.
    """
    try:
        a = datetime.strptime(tarih[:10], "%Y-%m-%d")
        b = datetime.strptime((bugun or "")[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0
    return max(0, (b - a).days)


def tazele(h: dict, foto_kayit) -> dict:
    """Turetilmis alanlari BUGUNKU siniflandiricilarla yeniden hesaplar.

    Depoda yalnizca ham olgu saklaniyor (baslik, ozet, kurum, tarih).
    Konu, bolge, fotograf ve baglam burada uretiliyor.

    NEDEN BOYLE: turetilmis alanlar depoda saklandiginda, siniflandirici
    duzeldikten sonra bile ESKI degeri tasiyorlardi. Olculen sonuc --
    "Goldman Sachs'tan Turkiye icin faiz uyarisi: Indirim beklentisi
    OTELENEBILIR" haberi, "otel" kalibi "otelenebilir" icinde eslestigi
    icin Turizm sayilmis; siniflandirici duzeltildikten SONRA bile otel
    fotografiyla ve "Turizm geliri doviz kazandirir" cumlesiyle yeniden
    yayimlanmisti.

    Simdi tersi calisiyor: bir siniflandirma hatasi duzeltildiginde
    ARSIVIN TAMAMI kendiliginden duzeliyor.
    """
    # VERI ACIKLAMALARI BASLIKTAN SINIFLANDIRILMAZ.
    #
    # Bu haberler RSS'ten degil seriden uretiliyor; konusu, gerekcesi ve
    # bolgesi serinin KENDI tanimindan geliyor. Baslik siniflandiricisina
    # sokmak, "ABD cekirdek PCE: yillik %3,29" basligini yeniden tahmin
    # etmeye calismak olurdu -- ve `neden_onemli` alanini silerdi.
    #
    # Turetilmis alanlar yine YENIDEN hesaplaniyor, ama dogru kaynaktan:
    # adreste yazili seri kodundan.
    adres = h.get("adres", "")
    if adres.startswith(_VERI_ONEK) and _takvim is not None:
        kod = adres[len(_VERI_ONEK):].split("/")[0]
        # HER IKI TABLO da taraniyor. Yalnizca `SERILER` bakildiginda
        # yerli (TP.*) seriler eslesmiyor ve `konu` HIC atanmiyordu;
        # sablon `h["konu"]` bekledigi icin kurulum KeyError ile
        # duruyordu -- sessiz degil, ama gec fark edilen bir hata.
        for s in (_takvim.SERILER + _takvim.YERLI_SERILER):
            if s[0] == kod:
                h["konu"] = s[3]
                break
        # Seri tablodan kaldirilmis olabilir; konu yine de dolmali.
        h.setdefault("konu", "Şirket haberleri")
        h["neden_onemli"] = (_takvim.YERLI_NEDEN.get(kod)
                             or _takvim.NEDEN.get(kod)
                             or h.get("neden_onemli", ""))
        h["bolge"] = "TR" if kod.startswith("TP.") else "DUNYA"
        h["yorumlanir"] = True
        h.setdefault("kanallar", [])
        if foto_kayit is not None and not h.get("foto"):
            f = foto_kayit.sec(h.get("konu", ""), adres)
            h["foto"] = f.dosya if f else ""
            h["foto_atif"] = f.kisa_atif if f else ""
        return h

    baslik_ozgun = h.get("baslik_kaynak") or h.get("baslik") or ""
    # Siniflandirma ORIJINAL baslikla yapilir, cevirisiyle degil: makine
    # cevirisi "policy rate"i "politika orani" yapabilir ve isaret
    # eslesmez. (uret_gundem.py ayni kurali uyguluyor.)
    if _besleme is not None:
        h["konu"] = _besleme.konu_bul(baslik_ozgun, h.get("konu")
                                      or "Şirket haberleri")
        h["bolge"] = _besleme.bolge_bul(baslik_ozgun, h.get("dil", "tr"))
    if _yorum is not None:
        baglam = _yorum.siniflandir(baslik_ozgun, h.get("konu", ""),
                                    h.get("kurum", ""), bool(h.get("ticari")))
        h["yorumlanir"] = baglam.yorumlanir
        h["neden_onemli"] = baglam.neden_onemli
        h["kanallar"] = list(baglam.kanallar)
        h["kanal_basligi"] = baglam.kanal_basligi
    if foto_kayit is not None:
        # Ayni haber her zaman ayni fotografi alir (adres belirleyici).
        f = foto_kayit.sec(h.get("konu", ""), h.get("adres", ""))
        h["foto"] = f.dosya if f else ""
        # CC BY atfi zorunlu -- gorselin altinda basiliyor.
        h["foto_atif"] = f.kisa_atif if f else ""
    return h


def arsiv_haberleri(guncel_adresler: set[str], foto_kayit) -> list[dict]:
    """Depoda sayfa yuku olan ama guncel pencerede olmayan haberler.

    Yalnizca `sayfa_veri` dolu olanlar donuyor: bu alan eklenmeden once
    kaydedilmis haberlerin ozeti hic saklanmadi, dolayisiyla sayfalari
    yeniden uretilemez. Onlari eksik veriyle basmak, bos kabuk sayfalar
    yayimlamak olurdu.
    """
    if _beyin is None:
        return []
    try:
        with _beyin.baglan() as b:
            satirlar = b.execute(
                "SELECT adres, sayfa_veri FROM haber"
                " WHERE sayfa_veri IS NOT NULL"
                " ORDER BY tarih DESC, ilk_gorulme DESC"
                " LIMIT ?", (ARSIV_SINIRI,)).fetchall()
    except Exception as e:
        print(f"  arsiv okunamadi: {e}")
        return []

    cikti: list[dict] = []
    dusen = 0
    for adres, yuk in satirlar:
        if adres in guncel_adresler:
            continue
        try:
            h = json.loads(yuk)
        except (TypeError, ValueError):
            continue
        h["adres"] = adres
        h["arsiv"] = True
        tazele(h, foto_kayit)
        # Yeniden siniflandirmada "yorumlanmaz" cikan haber sayfasiz
        # kaliyor. Bu, duzeltmenin CALISTIGI anlamina geliyor: eskiden
        # yanlislikla yorumlanan bir duyuru artik yorumlanmiyor.
        if not h.get("yorumlanir"):
            dusen += 1
            continue
        # Adres BASLIKTAN yeniden turetiliyor: tek dogru kaynak baslik.
        h["yol"] = haber_yolu(h)
        cikti.append(h)
    if dusen:
        print(f"  {dusen} arsiv haberi yeniden siniflandirmada elendi")
    return cikti


def varlik_indeksle(haberler: list[dict]) -> dict[str, dict]:
    """Varliklari cikarir, depoya yazar, ilgili haberleri geri okur.

    Depo yoksa ya da yazilamiyorsa BOS harita doner: varlik indeksi
    sayfanin sussu, gerekcesi degil. Site depoya erisemedigi icin
    kurulamamali degil.
    """
    if _varlik is None or _beyin is None:
        return {}
    harita: dict[str, dict] = {}
    try:
        with _beyin.baglan() as b:
            for h in haberler:
                if not h.get("yorumlanir"):
                    continue
                # `kurum` BAGLAM olarak geciyor: "Sektorel Enflasyon
                # Beklentileri" basliginda tek Turkiye isareti yok ama
                # TCMB duyurusu. Kurum verilmezse TUFE'ye baglanmiyordu.
                vs = _varlik.bul(b, h.get("baslik", ""), h.get("ozet", ""),
                                 kurum=h.get("kurum_tam") or h.get("kurum", ""))
                _varlik.yaz(b, h["adres"], vs)
                # Gercek adres depoya geri yaziliyor -- varlik
                # sayfalarindaki baglantilar buradan besleniyor.
                b.execute("UPDATE haber SET yayin_yolu=?, yayimlandi=1"
                          " WHERE adres=?", (h["yol"], h["adres"]))
                harita[h["adres"]] = {
                    # Sablon adres uretmesin: kod -> adres kurali tek
                    # yerde (varlik_yolu) yasamali, yoksa uc sablonda uc
                    # ayri kural olur ve biri sessizce kayar.
                    "varliklar": [{"kod": v.kimlik, "ad": v.ad, "tur": v.tur,
                                   "yol": varlik_yolu(v.kimlik)} for v in vs],
                    "ilgili": [],
                }
            # Ikinci gecis: artik BU partinin varliklari da yazili, yani
            # ayni gun cikan iki ilgili haber birbirini gorebilir.
            for adres in harita:
                harita[adres]["ilgili"] = _varlik.ilgili_haberler(b, adres)
    except Exception as e:                       # depo kilitli / bozuk
        print(f"  varlik indeksi atlandi: {e}")
        return {}
    return harita


#: Dizin sayfasinda listelenmek icin gereken en az haber sayisi.
#:
#: Sayfa uretimi bundan BAGIMSIZ: yapisal bagi olan her varligin sayfasi
#: uretiliyor. Sebebi somut -- "Brent → Cari islemler dengesi" bagi
#: sayfada baglanti olarak basiliyor; hedefin sayfasi yoksa o baglanti
#: 404 verir. Dizin ise okur icin, orada haberi olmayan varliklari
#: listelemek gurultu olurdu.
DIZIN_ESIGI = 1


def varlik_yolu(kod: str) -> str:
    """Varlik kodundan site adresi: "DIS_TICARET_TR" -> /varlik/dis-ticaret-tr/

    ALT CIZGI TIREYE CEVRILIYOR. Arama motorlari alt cizgiyi kelime
    BIRLESTIRICI, tireyi AYIRICI okur: "dis_ticaret_tr" tek kelime
    sayilir, "dis-ticaret-tr" uc kelime. Bu sayfalarin tek isi arananda
    bulunmak oldugu icin ayrim onemli.

    Adres kucuk harf: kodlar buyuk harfli ("FED"), ikisini karistirmak
    bir isletim sisteminde calisip digerinde 404 veren baglantilar
    uretir.
    """
    return f"/varlik/{kod.lower().replace('_', '-')}/"


def varlik_sayfalari(ortam, yaz, ortak: dict) -> list[str]:
    """Varlik sayfalarini uretir: /varlik/<kod>/.

    Bu sayfalar sitenin arama motorundaki tasiyicisi: "Fed faiz karari"
    arayan biri tek bir habere degil, o konunun BIRIKMIS arsivine
    dusuyor. Ustelik sayfada haberden fazlasi var -- varligin tanimi ve
    yapisal baglari, yani sitenin haber toplamaktan ayrildigi katman.
    """
    if _varlik is None or _beyin is None:
        return []
    yollar: list[str] = []
    try:
        with _beyin.baglan() as b:
            # Haber sayilari. "/haber/" YER TUTUCU -- haber hatti gercek
            # adresi bilmediginden onu yaziyor; `_%` en az bir karakter
            # daha istiyor, yani yalnizca gercek sayfalar sayiliyor.
            sayilar = dict(b.execute(
                "SELECT hv.varlik_kimlik, COUNT(*)"
                " FROM haber_varlik hv JOIN haber h ON h.adres = hv.adres"
                " WHERE h.yayimlandi = 1 AND h.yayin_yolu LIKE '/haber/_%'"
                " GROUP BY hv.varlik_kimlik").fetchall())

            # SAYFASI URETILECEKLER: yapisal bagi ya da haberi olan her
            # varlik. Esik uygulanmiyor, cunku bir bag sayfada baglanti
            # olarak basiliyor ve hedefin sayfasi yoksa 404 veriyor --
            # olculdu: "Brent → Cari islemler dengesi" bagi kirikti.
            bagli = {x[0] for x in b.execute(
                "SELECT kaynak FROM bag UNION SELECT hedef FROM bag")}
            kodlar = b.execute(
                "SELECT kod, ad, tur FROM varlik ORDER BY onem DESC, ad"
            ).fetchall()

            dizin = []
            for kod, ad, tur in kodlar:
                n = sayilar.get(kod, 0)
                if n == 0 and kod not in bagli:
                    continue          # ne haberi ne bagi var; sayfasi bos olurdu
                v = {"yol": varlik_yolu(kod), "kod": kod, "ad": ad,
                     "tur": tur, "sayi": n}
                k = _varlik.kunye(b, kod)
                # Gostergenin GUNCEL DEGERI. Sayfanin en yararli tek
                # bilgisi buydu ve yoktu: "TCMB politika faizi" sayfasi
                # tanimi ve iliskileri anlatip rakami hic yazmiyordu.
                veri = _varlik.seri_ozet(b, (k or {}).get("seri_kodu"))
                yaz(f"{v['yol']}index.html",
                    ortam.get_template("varlik.html").render(
                        **ortak, yol=v["yol"], v=v, kunye=k, veri=veri,
                        kivilcim=(kivilcim.cizgi(veri["seri"])
                                  if veri else ""),
                        baglar=_varlik.baglar(b, kod),
                        haberler=_varlik.varlik_gecmisi(b, kod, 30)))
                yollar.append(v["yol"])
                if n >= DIZIN_ESIGI:
                    dizin.append(v)

            # Dizin haber sayisina gore siralaniyor: okur "en cok ne
            # konusuluyor" cevabini ust sirada gormek istiyor.
            dizin.sort(key=lambda x: (-x["sayi"], x["ad"]))
            if dizin:
                yaz("/varlik/index.html",
                    ortam.get_template("varlik_dizin.html").render(
                        **ortak, yol="/varlik/", dizin=dizin))
                yollar.append("/varlik/")
    except Exception as e:
        print(f"  varlik sayfalari atlandi: {e}")
        return []
    return yollar


def insa() -> int:
    _cikti_temizle()

    ortam = Environment(
        loader=FileSystemLoader(SABLON),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Kod -> adres kurali TEK YERDE. Sablonlarda elle "/varlik/{{ kod|lower }}/"
    # yazmak, alt cizgi/tire donusumunu her sablonda tekrar etmek demekti;
    # biri unutuldugunda 404 sessizce olusuyordu.
    ortam.filters["varlik_yolu"] = varlik_yolu

    # `analizler`  -- SAYFASI URETILECEK olanlar (hepsi; adresler kirilmasin)
    # `listelenen` -- LISTELERDE gorunecek olanlar (yinelenenler elenmis)
    analizler = analizleri_yukle()
    listelenen = guncel_olanlar(analizler)
    guncel_sluglar = {a.slug for a in listelenen}
    if len(listelenen) < len(analizler):
        print(f"listeleme: {len(analizler) - len(listelenen)} yinelenen "
              f"otomatik analiz gizlendi (sayfalari duruyor)")
    hakkimizda = hakkimizda_yukle()
    gostergeler = gostergeleri_yukle()
    gundem = gundem_yukle()
    yollar = ["/"]

    # Menude yalnizca DOLU kategoriler gorunur
    menu = [
        (f"/{slug}/", baslik)
        for slug, baslik, kategori, _ in KATEGORILER
        if any(a.kategori == kategori for a in listelenen)
    ]
    if gundem.get("haberler"):
        menu.append(("/gundem/", "Haberler"))

    # Yorumlanan haberlere gorsel. Rutin duyurulara gorsel URETILMEZ --
    # listede goruntuluyorlar ve her birine gorsel koymak sayfayi
    # gurultuye bogar.
    gundem_gorseller = {
        h["adres"]: gorsel.haber_gorseli(h["konu"], h["kurum"], h["baslik"])
        for h in gundem.get("haberler", [])
        if h.get("yorumlanir")
    }

    # Serit ve panel icin kucuk seri grafikleri. Depodan okunur, ek veri
    # cekilmez. Depo yoksa bos doner ve serit kivilcimsiz basilir --
    # grafik sus, deger asil bilgi.
    kivilcimlar = kivilcim.gosterge_kivilcimlari(
        [k["kod"] for k in gostergeler.get("kalemler", [])]
    )

    # HABER ADRESLERI BURADA ATANIYOR -- her sayfadan ONCE.
    #
    # Once haber donguSUNDE atanıyordu ve o dongu analiz sayfalarindan
    # SONRA calisiyor. Sonuc: analiz sayfalarindaki son dakika seridi
    # haberin gercek adresini degil yer tutucusunu ("/haber/")
    # gosteriyordu -- 312 kirik baglanti. Sozlukler ayni nesne oldugu
    # icin burada atamak butun sayfalara yansiyor.
    for h in gundem.get("haberler", []):
        if h.get("yorumlanir"):
            h["yol"] = haber_yolu(h)

    # Son dakika seridi: en yeni, KENDI SAYFASI OLAN haberler. Disari
    # yonlendiren baglanti yok; serit sitenin kendi sayfalarina gider.
    son_dakika = [
        h for h in gundem.get("haberler", []) if h.get("yorumlanir")
    ][:12]

    ortak = {
        "site": SITE,
        "gostergeler": gostergeler,
        "gundem": gundem,
        "gundem_gorseller": gundem_gorseller,
        "kivilcimlar": kivilcimlar,
        "son_dakika": son_dakika,
        "menu": menu,
        "kaynak_adlari": KAYNAK_ADLARI,
    }

    # Analizler
    for a in analizler:
        yaz(
            f"{a.yol}index.html",
            ortam.get_template("analiz.html").render(
                **ortak, yol=a.yol, a=a,
                # Listeden elenmis surum: sayfasi duruyor ama dizine
                # girmiyor (bkz. temel.html'deki robots blogu).
                eskimis=a.slug not in guncel_sluglar),
        )
        yollar.append(a.yol)

    # Kategori sayfalari. Menude bos sekme birakmamak icin YALNIZCA icerigi
    # olan kategoriler uretilir -- tiklayinca bos sayfa cikan bir menu,
    # eksik menuden kotudur.
    for slug, baslik, kategori, aciklama in KATEGORILER:
        secilen = [a for a in listelenen if a.kategori == kategori]
        if not secilen:
            continue
        yol_k = f"/{slug}/"
        yaz(
            f"{yol_k}index.html",
            ortam.get_template("kategori.html").render(
                **ortak, yol=yol_k, analizler=secilen,
                kategori_baslik=baslik, kategori_aciklama=aciklama,
            ),
        )
        yollar.append(yol_k)

    # Hakkimizda -- vizyon/misyon + yayin ilkeleri, kunye, gizlilik; capalarla
    if hakkimizda is not None:
        yaz(
            "/hakkimizda/index.html",
            ortam.get_template("hakkimizda.html").render(
                **ortak, yol="/hakkimizda/", h=hakkimizda
            ),
        )
        yollar.append("/hakkimizda/")

    # Gundem -- resmi kurum duyurulari
    if gundem.get("haberler"):
        # Once haber sayfalari: her birine kendi adresini yaziyoruz ki
        # gundem sayfasi ic baglanti verebilsin. Sira onemli -- gundem
        # sayfasi bu adresleri bekliyor.
        for h in gundem["haberler"]:
            if not h.get("yorumlanir"):
                continue
            h["yol"] = haber_yolu(h)

        # ARSIV: guncel pencerede olmayan, daha once yayimlanmis haberler.
        #
        # `gundem.json` yalnizca son besleme penceresini tasiyor (~40
        # haber). Sayfalar sadece ondan uretilirse, dun yayimlanan haber
        # bugun 404 olur -- olculdu: depoda sayfa hak eden 53 haber
        # varken sitede 10'u duruyordu. Paylasilan her baglanti bir gun
        # sonra kiriliyordu ve arama motoru kaybolan sayfalari
        # indeksliyordu.
        #
        # Arsiv kayitlari gundem listesinin SONUNA ekleniyor; boylece
        # ana sayfa ve gundem sirasi degismiyor, yalnizca sayfalari
        # yeniden uretiliyor.
        arsiv = arsiv_haberleri({h["adres"] for h in gundem["haberler"]},
                                foto_defteri())
        if arsiv:
            print(f"arsiv: {len(arsiv)} eski haber sayfasi yeniden uretiliyor")
        uretilecek = gundem["haberler"] + arsiv

        # VARLIK INDEKSI ONCE YAZILIR, SONRA RENDER EDILIR.
        #
        # Sira onemli: "bununla ilgili diger gelismeler" bolumu depoya
        # sorulunca cevaplaniyor. Bu partinin varliklari yazilmadan render
        # edilirse, ayni gun yayimlanan iki ilgili haber birbirini
        # goremez -- ancak BIR SONRAKI calistirmada baglanirlardi.
        #
        # Ayrica gercek adres burada belli oluyor: haber hatti depoya
        # "/haber/" yaziyor (yer tutucu), tam adres slug'la burada
        # olusuyor. Baglantilarin calismasi icin geri yazilmali.
        varlik_haritasi = varlik_indeksle(uretilecek)

        for h in uretilecek:
            if not h.get("yorumlanir"):
                continue
            h_yol = h["yol"]
            h_varliklar = varlik_haritasi.get(h["adres"], {}).get("varliklar")
            yaz(
                f"{h_yol}index.html",
                ortam.get_template("haber.html").render(
                    **ortak, yol=h_yol, h=h,
                    gorsel_svg=gundem_gorseller.get(h["adres"], ""),
                    ilgili=ilgili_gostergeler(h["konu"], gostergeler),
                    # Piyasa kutusu BOLGEYE duyarli: Turkiye enflasyon
                    # haberinde ABD tahvil getirisi degil, TUFE ve TCMB
                    # fonlama okunur.
                    piyasa=piyasa_kutusu.kutu(
                        h["konu"], gundem.get("guncelleme", ""),
                        yerli=_dosya.turkiye_haberi(
                            h.get("bolge", ""),
                            ([v["kod"] for v in h_varliklar]
                             if h_varliklar is not None else None))
                        if _dosya else False),
                    # Turkiye bolumleri YALNIZCA Turkiye haberinde.
                    # Olcut `bolge` degil VARLIK INDEKSI: bolge, Turkce
                    # basligi varsayilan olarak TR sayiyor ve Turk
                    # kaynagin cevirdigi yabanci haber de TR oluyordu.
                    # `varliklar` None ise indeks calismamis demektir --
                    # o zaman dosya.py eski olcute duser.
                    dosya=(_dosya.kur(
                        h["konu"], h.get("bolge", ""), h.get("tarih", ""),
                        varliklar=([v["kod"] for v in h_varliklar]
                                   if h_varliklar is not None else None),
                        baslik=h.get("baslik_kaynak") or h.get("baslik", ""),
                        # Ozeti olmayan haberde acilis cumlesi uretilsin:
                        # aksi halde sayfada hicbir metin kalmiyor.
                        ozetsiz=not (h.get("ozet") or "").strip())
                           if _dosya else None),
                    varliklar=h_varliklar or [],
                    ilgili_haberler=varlik_haritasi.get(h["adres"], {}).get("ilgili", []),
                    # Haberin uzerinden gecen gun. Sayfadaki gosterge ve
                    # piyasa kutulari BUGUNUN verisi; eski bir haberi
                    # bugunun sayilariyla cerceveleyip susmak, okura o
                    # sayilari haberin baglami gibi gostermek olurdu.
                    yas=gun_farki(h.get("tarih", ""),
                                  gundem.get("guncelleme", "")),
                    # Senaryo bolumu yalnizca kritik haberlerde
                    senaryo_acik=senaryoya_acik(h),
                ),
            )
            yollar.append(h_yol)

        # VARLIK SAYFALARI YAYIMLANMIYOR.
        #
        # Varlik indeksi ic bir katman olarak KALIYOR ve calisiyor: haberi
        # Turkiye baglami acisindan siniflandiriyor, "bununla ilgili diger
        # gelismeler" bolumunu besliyor ve arsivi birbirine bagliyor.
        # Yalnizca okura ayri bir "Konular" bolumu olarak GOSTERILMIYOR --
        # site haber ve cozumleme yayimliyor, konu dizini degil.
        #
        # `varlik_sayfalari()` ve sablonlari duruyor: karar yayin
        # kararidir, kod silmeyi gerektirmiyor.

        yaz(
            "/gundem/index.html",
            ortam.get_template("gundem.html").render(**ortak, yol="/gundem/"),
        )
        yollar.append("/gundem/")

    # Uyelik sayfalari.
    #
    # Uculu de BOS KABUK olarak uretiliyor: icerik oturuma bagli ve
    # `cikti/` altindaki her dosya herkese acik. Uyeye ozel veriyi statik
    # HTML'e yazmak, o veriyi yayimlamak olurdu. Icerik `/api/...`ten
    # geliyor, Worker oturumu cerezle dogruluyor.
    for slug, ad, sayfa_baslik, sayfa_aciklama in UYELIK_SAYFALARI:
        yol_u = f"/{slug}/"
        yaz(
            f"{yol_u}index.html",
            ortam.get_template("uyelik.html").render(
                **ortak, yol=yol_u, sayfa=ad,
                sayfa_baslik=sayfa_baslik, sayfa_aciklama=sayfa_aciklama,
            ),
        )
        # Arama motoruna kapali sayfalar site haritasina GIRMEZ; `yollar`
        # listesine eklenmemesi bilincli.

    # Ana sayfa EN SONDA uretilir.
    #
    # Sebebi: haber seridi yalnizca kendi sayfasi OLAN haberleri listeliyor
    # ve o adresler yukaridaki dongude olusuyor. Ana sayfa once uretilirse
    # `h.yol` henuz bos olur, filtre hicbir haberi gecirmez ve serit
    # kabi bos basilir -- sayfada "Haberler" basligi gorunur ama alti
    # bostur. Bir kez oyle oldu; hata mesaji vermedigi icin ancak canli
    # sayfa incelenince fark edildi.
    yaz(
        "/index.html",
        ortam.get_template("anasayfa.html").render(
            **ortak, yol="/", analizler=listelenen,
            yorumlar=yorum_kartlari(listelenen),
            rakamlar=kunye_rakamlari(analizler),
        ),
    )

    # Arama: dizin + sayfa
    yaz("/arama.json", arama_dizini(listelenen))
    yaz(
        "/ara/index.html",
        ortam.get_template("ara.html").render(**ortak, yol="/ara/"),
    )
    yollar.append("/ara/")

    # Besleme ve arama motoru dosyalari
    yaz("/rss.xml", rss_uret(listelenen))
    yaz("/sitemap.xml", sitemap_uret(yollar))
    yaz(
        "/robots.txt",
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE['adres']}/sitemap.xml\n",
    )

    # Varliklar
    shutil.copytree(STATIK, CIKTI / "statik")

    # Uretilen icerigi depoya bildir. Site ureteci butun icerigi tek yerde
    # gordugu icin bu kaydi atmak icin en dogru yer burasi; her hattin ayri
    # ayri yazmasi hem tekrar hem de tutarsizlik riski olurdu.
    try:
        sys.path.insert(0, str(KOK.parent / "haber_botu"))
        import beyin  # noqa: PLC0415

        with beyin.baglan() as b:
            beyin.icerik_yaz(b, [
                {
                    "slug": a.slug, "tur": slugla(a.kategori),
                    "baslik": a.baslik, "kod": a.kod,
                    "kategori": a.kategori, "tarih": a.tarih,
                    "kelime": a.kelime,
                }
                for a in analizler
            ])
    except Exception as e:
        # Depo yazimi siteyi uretmeyi ENGELLEMEZ -- kayit tutmak yan is,
        # site uretimi asil is.
        print(f"  (depo kaydi atlandi: {type(e).__name__})")

    bolum_sayisi = len(hakkimizda.gezinme) if hakkimizda else 0
    print(f"{len(analizler)} analiz, hakkimizda {bolum_sayisi} bolum")
    print(f"{len(yollar)} adres, cikti: {CIKTI.relative_to(KOK.parent)}")

    if "ALAN-ADI-BELIRLENMEDI" in SITE["adres"]:
        print(
            "\nUYARI: site adresi hala yer tutucu. Yayina cikmadan once\n"
            "       insa.py icindeki SITE['adres'] degerini gercek alan\n"
            "       adiyla degistirin -- canonical, RSS, sitemap ve yapisal\n"
            "       veri bu adresi kullaniyor."
        )
    return 0


def sun(port: int = 8000) -> None:
    """Yerel onizleme sunucusu.

    ThreadingHTTPServer bilincli bir secim: tek baglantili TCPServer,
    tarayici baglantiyi acik tuttugunda sonraki istekleri kuyruga alir ve
    sunucu donmus gibi gorunur. Es zamanli baglanti onizlemede sart --
    tarayici zaten sayfa + CSS + favicon icin ayni anda birden fazla
    baglanti aciyor.
    """
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Isleyici(SimpleHTTPRequestHandler):
        # Onizlemede onbellek istemiyoruz: yeniden insa ettikten sonra
        # tarayicinin eski sayfayi gostermesi kafa karistirir.
        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    isleyici = functools.partial(Isleyici, directory=str(CIKTI))
    sunucu = ThreadingHTTPServer(("127.0.0.1", port), isleyici)
    sunucu.daemon_threads = True

    print(f"\n  http://localhost:{port}")
    print("  (durdurmak icin Ctrl+C)\n")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\ndurduruldu")
    finally:
        sunucu.server_close()


if __name__ == "__main__":
    ayristirici = argparse.ArgumentParser(description="Statik site ureteci")
    ayristirici.add_argument("--sun", action="store_true", help="uretimden sonra yerel sunucu ac")
    ayristirici.add_argument("--port", type=int, default=8000)
    args = ayristirici.parse_args()

    kod = insa()
    if kod == 0 and args.sun:
        sun(args.port)
    sys.exit(kod)
