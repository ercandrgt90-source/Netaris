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
import os
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

# Manset bicimi. `tazele()` uzun basliklari burada kisaltiyor -- kural
# degistiginde arsivin tamami kendiliginden yeniden hesaplaniyor.
try:
    import bicim as _bicim
except ImportError:
    _bicim = None

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

# Veri yayin takvimi + beklenti motoru. Ikisi de yoksa bolum basilmaz.
try:
    import yayin_takvimi as _yt
except ImportError:
    _yt = None
try:
    import beklenti as _beklenti
except ImportError:
    _beklenti = None

# Onem puani. Hangi haber one cikar, hangisi akista kalir.
try:
    import onem as _onem
except ImportError:
    _onem = None

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


def css_kucult(dosya: pathlib.Path) -> None:
    """Yayimlanan CSS'ten yorumlari cikarir. KAYNAK DOSYAYA DOKUNMAZ.

    Olculdu: `stil.css` 95 KB ve bunun dortte biri yorum. Yorumlar
    kaynakta KALMALI -- her kuralin gerekcesi yazili ve o gerekceler
    bir siniftan digerini ayirt etmemi saglayan sey. Ama okura
    gitmeleri gereksiz: CSS render'i bloklar.

    Yalnizca YORUM ve GEREKSIZ BOSLUK cikariliyor. Secici birlestirme,
    renk kisaltma, birim yeniden yazma YOK -- kazanci kucuk, sessiz
    bozma riski buyuk.

    Dizge farkindaligi sart: `content: "/*"` gecerli CSS'tir ve naif bir
    yorum sokucu oradan baslayip dosyanin yarisini yutar. Ayni tuzaga
    olu-kural temizliginde dusmustum: secici metnine karisan bir
    yorumu virgulde bolunce KAPANMAMIS yorum kaldi ve sonrasindaki her
    sey yok oldu (`/*` 158, `*/` 157 diye olculdu).
    """
    ham = dosya.read_text(encoding="utf-8")
    # DIZGELER YER TUTUCUYA CEKILIYOR. Boslugu ezen regexler dizgenin
    # ICINE de girer: `content: ", "` -> `content:","` sayfada gorunen
    # ayraci degistirir. Ilk yazimda tam bunu yapiyordum.
    dizgeler: list[str] = []
    parcalar: list[str] = []
    i = 0
    n = len(ham)
    while i < n:
        c = ham[i]
        if c in "\"'":
            j = i + 1
            while j < n and ham[j] != c:
                j += 2 if ham[j] == "\\" else 1
            dizgeler.append(ham[i:j + 1])
            parcalar.append(f"\x00{len(dizgeler) - 1}\x00")
            i = j + 1
        elif ham.startswith("/*", i):
            k = ham.find("*/", i + 2)
            i = n if k < 0 else k + 2
        else:
            parcalar.append(c)
            i += 1
    yeni = "".join(parcalar)
    yeni = re.sub(r"[ \t]+", " ", yeni)
    yeni = re.sub(r"\s*([{};:,>])\s*", r"\1", yeni)
    yeni = re.sub(r";}", "}", yeni).strip()
    yeni = re.sub(r"\x00(\d+)\x00", lambda m: dizgeler[int(m[1])], yeni)

    # DOGRULAMA: kucultme sessizce bozarsa insa DURMALI. Yayimlanmis
    # bozuk bir stil dosyasi, kazandirdigi 10 KB'nin cok otesinde zarar.
    for ad, olc in (
        ("suslu parantez", lambda s: s.count("{") - s.count("}")),
        ("bildirim sayisi", lambda s: s.count(":")),
        ("kural sayisi", lambda s: s.count("{")),
    ):
        onceki = olc(re.sub(r"/\*.*?\*/", "", ham, flags=re.S))
        if ad == "suslu parantez":
            if olc(yeni) != 0 or onceki != 0:
                raise SystemExit(f"css_kucult: {ad} dengesizligi")
        elif olc(yeni) != onceki:
            raise SystemExit(
                f"css_kucult: {ad} {onceki} -> {olc(yeni)} degisti")
    dosya.write_text(yeni, encoding="utf-8")
    print(f"  stil.css {len(ham) / 1024:.0f} KB -> "
          f"{len(yeni.encode()) / 1024:.0f} KB")

# ---------------------------------------------------------------------------
# Site ayarlari
# ---------------------------------------------------------------------------

#: Sitenin KENDI adresi. Tek kaynak: kanonik baglantilar, `og:url`,
#: `sitemap.xml`, `robots.txt` ve RSS'in tamami buradan uretiliyor --
#: olculdu, yayimlanan ciktida 2402 yerde geciyor.
#:
#: NEDEN CEVRE DEGISKENI, NEDEN BU VARSAYILAN
#: ------------------------------------------
#: Burada `https://netaris.com` YAZILIYDU ve o alan adi HIC
#: cozumlenmiyordu (DNS `gaierror`). Yani site, arama motoruna
#: "asil surumum su adreste" diyor, o adreste ise hicbir sey yok.
#: Var olmayan bir alan adina kanonik vermek, sayfayi dizine
#: girdirmemenin en etkili yoludur -- sitenin gorunmezligi bir
#: eksiklik degil, ETKIN olarak yayimlanan bir talimatti.
#:
#: Varsayilan artik GERCEKTEN YAYIN YAPAN adres. Kusurlu ama dogru:
#: `*.workers.dev` Turk Telekom'un "Guvenli Internet" suzgeci
#: tarafindan engelleniyor (olculdu: TLS el sikismasi
#: `Via: 1.0 middlebox` ile kesiliyor ve engel sayfasina
#: yonlendiriliyor; ust alan adi `workers.dev` de ayni sekilde
#: engelli, yani icerigimizle ilgisi olmayan bir KATEGORI engeli).
#:
#: Alan adi baglandiginda tek is: `NETARIS_ADRES` degiskenini kurmak
#: ya da asagidaki varsayilani degistirmek. Sonunda egik cizgi
#: OLMAYACAK.
TABAN_ADRES = os.environ.get(
    "NETARIS_ADRES", "https://netaris.ercandrgt90.workers.dev").rstrip("/")

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
    "adres": TABAN_ADRES,
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


#: Sayfada karsiligi bulunamayan yorumlarin basliklari. `insa` sonunda
#: ekrana yaziliyor -- sessizce dusurulen icerik, olculemeyen icerik
#: demek.
_dogrulanamayan: list[str] = []

#: Yorumda gecen ve sayfada aranacak sayi kalibi. Binlik ayraci ve
#: ondalik virgul dahil.
_SAYI = re.compile(r"\d[\d.]*,\d+|\d{1,3}(?:\.\d{3})+|\d+")

#: Bu uzunluktan kisa sayilar aranmiyor. Tek haneli sayilar ("3 ay",
#: "2 katina") metnin dogal parcasi; onlari veri sanip yorumu dusurmek
#: cozdugunden cok sorun uretir.
_EN_KISA_SAYI = 2


def _yorum_dogrulanabilir(metin: str, h: dict, d) -> bool:
    """Yorumdaki her sayinin sayfada karsiligi var mi?

    Karsilastirma sayfanin SABLONA GIDEN verisi uzerinden yapiliyor --
    uretilmis HTML uzerinden degil. Sebep sira: sayfa bu noktada henuz
    basilmadi, ve zaten sablonun bastigi seyler bunlar.

    Turetilmis sayilara IZIN VERILIYOR: yorum "35 baz puan" diyebilir
    ve o sayi hicbir yerde yazmaz, iki degerin farkidir. O yuzden olcut
    "her sayi birebir sayfada olacak" degil; sayilarin COGU sayfada
    varsa yorum dogrulanabilir sayiliyor. Tek bir uydurma sayi da bu
    esigi asagi cekiyor cunku uydurma sayilar tek basina gelmiyor --
    olculdu, dusen yorumlarda ortalama iki-uc kacak sayi vardi.
    """
    kaynak = [h.get("baslik", ""), h.get("ozet", "") or "",
              h.get("baslik_kaynak", "") or ""]
    if d is not None:
        kaynak.append(getattr(d, "acilis", "") or "")
        kaynak += list(getattr(d, "bulgular", ()) or ())
        for alan in ("turkiye", "dunya"):
            for g in (getattr(d, alan, ()) or ()):
                kaynak += [str(getattr(g, "son", "")),
                           str(getattr(g, "onceki", "")),
                           getattr(g, "degisim", "") or ""]
    havuz = " ".join(kaynak)
    havuz_sayilari = set(_SAYI.findall(havuz))
    # Sayfadaki sayilar nokta/virgul bicimiyle de, ham float olarak da
    # gecebiliyor ("47.6085" ve "47,61"). Ilk iki basamak esitse ayni
    # sayi kabul ediliyor.
    kisa = {s.replace(".", "").replace(",", "")[:4] for s in havuz_sayilari}

    yorum_sayilari = [s for s in _SAYI.findall(metin)
                      if len(s) >= _EN_KISA_SAYI]
    if not yorum_sayilari:
        return True
    bulunan = sum(
        1 for s in yorum_sayilari
        if s in havuz_sayilari
        or s.replace(".", "").replace(",", "")[:4] in kisa)
    return bulunan * 2 >= len(yorum_sayilari)


def _boy_foto(yol: str, klasor: str) -> str:
    """Buyuk gorselin baska boydaki esini dondurur; yoksa BOS."""
    if not yol or "/statik/foto/" not in yol:
        return ""
    ad = yol.rsplit("/", 1)[-1]
    hedef = STATIK / "foto" / klasor / ad
    return f"/statik/foto/{klasor}/{ad}" if hedef.exists() else ""


def orta_foto(yol: str) -> str:
    """KART gorseli -- 400 piksel.

    Olculdu: ana sayfa 1,88 MB iniyordu ve bunun 1,60 MB'i SEKIZ kart
    gorseliydi; hepsi 800 piksellik dosyaydi. Kart izgarada ~300
    piksel gorunuyor, yani yedi kat fazla bayt.

    BOS DONMESI NORMAL: orta boy yalnizca Commons kaynakli gorsellerde
    uretilebiliyor. Sablon o durumda BUYUGUNU basiyor -- gorselsiz kart
    izgarada delik birakirdi.
    """
    return _boy_foto(yol, "o")


def kucuk_foto(yol: str) -> str:
    """Buyuk gorselin 96 piksellik esini dondurur; yoksa BOS.

    Canli akista kirk satir var ve her satirin yanindaki kare gorsel
    yalnizca 40 piksel. Havuzdaki dosyalar haber sutunu genisliginde
    (800px, ortalama 165 KB) -- onlari CSS ile kucultmek okura yaklasik
    6 MB indirtir. Kucuk surumler ortalama 6 KB.

    BOS DONMESI NORMAL: kucuk surum yalnizca Commons kaynakli
    gorsellerde uretilebiliyor (olcekleme ucu orada). Sablon o satiri
    gorselsiz basiyor -- yer tutucu koymak "yuklenmemis gorsel"
    izlenimi verir, eksik gorsel ise sessizce dogru gorunur.
    """
    if not yol or "/statik/foto/" not in yol:
        return ""
    ad = yol.rsplit("/", 1)[-1]
    return f"/statik/foto/k/{ad}" if (STATIK / "foto" / "k" / ad).exists() else ""


#: Fotograf kullanim sayaci -- BUTUN hatlar (haber, analiz) ortak
#: kullaniyor. Tek havuzu iki ayri secim yontemiyle paylasmak dengeyi
#: bozuyordu; sayac ortak olunca "en az kullanilani al" kurali her yerde
#: ayni anlama geliyor.
_FOTO_SAYAC: dict[str, int] = {}


def _en_az_kullanilan(havuz: list, tohum: str):
    """Havuzdan o ana kadar EN AZ kullanilmis gorseli secer.

    Esitlikte tohuma gore belirlenimci: ayni yazi, havuz degismedigi
    surece ayni gorseli alir.
    """
    if not havuz:
        return None
    f = min(havuz, key=lambda x: (
        _FOTO_SAYAC.get(x.dosya, 0),
        hashlib.sha256((tohum + x.dosya).encode()).hexdigest()))
    _FOTO_SAYAC[f.dosya] = _FOTO_SAYAC.get(f.dosya, 0) + 1
    return f


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
    # ANALIZLER DE AYNI SAYACI KULLANIYOR.
    #
    # Burasi `kayit.sec` ile bagimsiz hash aliyordu ve haber hattindaki
    # dengeli dagitimi GORMUYORDU. Denetim yakaladi: ana sayfada
    # `kripto-varliklar-2.jpg` iki kez, "Borsa" havuzunda kullanim
    # 13'e 10 dengesiz. Iki ayri secim yontemi tek havuzu paylasinca
    # dengeyi biri kuruyor digeri boziyordu.
    f = _en_az_kullanilan(kayit.havuz(konu), baslik)
    if f is None and konu != varsayilan:
        f = _en_az_kullanilan(kayit.havuz(varsayilan), baslik)
    if f is None or not (STATIK / f.dosya.split("/statik/", 1)[-1]).exists():
        # DOSYASI OLMAYAN GORSEL BASILMAZ. Defterde adi gecen bir dosya
        # diskte olmayabilir: editoryal suzgec siklastiginda 49 gorsel
        # cikarildi ve iki ANALIZ sayfasi silinmis dosyaya isaret etmeye
        # devam etti. Ayni koruma haber hattinda da var -- iki ayri
        # yoldan fotograf seciliyor ve ikisi de kendi kontrolunu yapmali.
        return "", ""
    # CC BY atfi zorunlu -- gorselin altinda basilir, kaldirilirsa lisans
    # ihlal edilir.
    return f.dosya, f.kisa_atif


def foto_dagit(haberler: list[dict], varlik_haritasi: dict,
               kayit) -> dict[str, object]:
    """Butun haberlere fotografi TEK SEFERDE, birbirini gorerek dagitir.

    Neden tek tek secilemiyor: `Kayit.sec` her haber icin BAGIMSIZ bir
    hash aliyor (`hash(adres) % havuz`). Bagimsiz secim, havuz buyuse
    bile carpismayi engellemiyor -- dogum gunu problemi. Olculdu: dort
    fotograflik jeopolitik havuzunda 19 haber vardi ve dagilim 9/4/3/3
    cikti; duzgun dagitilsa 5/5/5/4 olurdu. Yani tekrarin bir kismi
    havuzun darligindan, bir kismi SECIM YONTEMINDEN geliyordu.

    Burada her haber, o ana kadar EN AZ KULLANILMIS gorseli aliyor.
    Havuz haber sayisindan buyukse tekrar SIFIR; kucukse tekrar esit
    dagiliyor.

    ESKIDEN YENIYE isleniyor. Ters sirada islenseydi her yeni haber
    listenin basina girip kendinden sonraki herkesin gorselini
    kaydirirdi; boyle, yayimlanmis bir haberin gorseli havuz degismedigi
    surece sabit kaliyor ve yeni haber arta kalani aliyor.
    """
    if kayit is None:
        return {}
    sonuc: dict[str, object] = {}
    onceki = ""          # bir onceki satirin gorseli
    # SAYFASI OLMAYAN OGELER DE DAGITIMA GIRIYOR: canli akista onlarin
    # da yaninda kucuk gorsel var ve o gorseller de tekrarsiz olmali.
    sirali = sorted(
        haberler, key=lambda h: (h.get("tarih", ""), h.get("adres", "")))
    for h in sirali:
        adres = h.get("adres", "")
        # Havuz anahtari: once varlik, yoksa konu. `varlik_sec` ile ayni
        # kural -- birden fazla varlik varsa tohuma gore biri seciliyor.
        adaylar = [v for v in
                   (varlik_haritasi.get(adres, {}).get("varliklar") or [])
                   if kayit.havuz(v["kod"])]
        # BASLIKTA GECEN VARLIK ONCELIKLI.
        #
        # Eskiden adaylardan biri TOHUMA gore, yani rastgele seciliyordu.
        # Olculdu ve gorunur hataya yol acti:
        #   "Altin fiyatlarinda yukselis suruyor"  -> Hurmuz Bogazi haritasi
        #   "Altinin kilogram fiyati ... yukseldi" -> New York borsasi
        #   "ABD'de tarife iadeleri ..."           -> Ankara sokak fotografi
        # Ucunde de haber birden fazla varliga baglanmis (altin haberinde
        # Iran da geciyor) ve gorsel YANLIS olani anlatmis.
        #
        # Basligin kendisi haberin NEYLE ILGILI oldugunun en dogrudan
        # isareti. Baslikta adi gecen varlik varsa gorsel ondan seciliyor.
        if _dosya is not None and adaylar:
            bas = _dosya.katla(h.get("baslik") or h.get("baslik_kaynak") or "")
            gecen = [v for v in adaylar if _dosya.katla(v["ad"]) in bas]
            if gecen:
                adaylar = gecen
        if adaylar:
            i = int(hashlib.sha256((adres + "v").encode()).hexdigest(),
                    16) % len(adaylar)
            anahtar = adaylar[i]["kod"]
        else:
            anahtar = h.get("konu", "")
        # ART ARDA AYNI GORSEL VERILMIYOR.
        #
        # Dagitim kullanim sayisini dengeliyor ama SIRAYI gormuyordu;
        # canli akista iki komsu satir ayni gorseli alabiliyordu ve
        # okurun ikisini birlikte gordugu tek durum bu. Bir onceki
        # atama adaylardan cikariliyor -- havuzda tek gorsel varsa
        # elbette kaliyor.
        havuz = kayit.havuz(anahtar)
        if onceki and len(havuz) > 1:
            havuz = [x for x in havuz if x.dosya != onceki] or havuz
        f = _en_az_kullanilan(havuz, adres)
        if f is not None:
            sonuc[adres] = f
            onceki = f.dosya
    return sonuc


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

#: Kart gorsellerinin toplu kunyesi bu isaretin yerine yaziliyor.
_KUNYE_ISARETI = "</footer>"

#: `<figure>` disinda basilan havuz gorseli. Kucuk (akis) surumler
#: haric: onlar 40 piksel ve zaten ayni sayfada buyugu kunyeli basiliyor.
_KART_GORSELI = re.compile(r'src="(/statik/foto/(?!k/)[^"]+)"')


def _foto_kunyeleri(html_metni: str) -> str:
    """Sayfadaki kunyesiz kart gorselleri icin toplu atif satiri.

    NEDEN: CC BY atfi ZORUNLU ve bu projenin kendi kurali da oyle
    ("atifi dusuren bir kod degisikligi lisansi ihlal eder").
    Haber sayfasindaki buyuk gorsel `<figure>` icinde kunyesiyle
    basiliyor -- olculdu, 417'nin 417'si. Ama LISTE sayfalarindaki kart
    gorselleri figure disinda ve kunyesizdi: 48 gorsel.

    Kart basina kunye yazmak izgarayi bozar; kabul edilen yontem
    sayfanin altinda toplu atif. Tekrar edenler bir kez yaziliyor.

    BURADA, sablonda DEGIL: her liste sablonuna ayri ayri eklemek,
    birinde unutuldugunda sessizce ihlal demekti. `yaz` butun
    sayfalarin tek gecis noktasi.
    """
    if _foto is None:
        return ""
    yollar = set(_KART_GORSELI.findall(html_metni))
    # Zaten figure icinde kunyeli basilanlar cikariliyor.
    for m in re.finditer(r"<figure[^>]*>.*?</figure>", html_metni, re.S):
        if "figcaption" in m.group():
            yollar -= set(_KART_GORSELI.findall(m.group()))
    if not yollar:
        return ""
    kayit = foto_defteri()
    if kayit is None:
        return ""
    # BOY KLASORU AYRISTIRILIYOR.
    #
    # Kart gorselleri artik `/statik/foto/o/<ad>` (400 piksel) yolundan
    # basiliyor ama defterde `/statik/foto/<ad>` yaziyor. Ilk yazimda
    # birebir karsilastirma yapiyordum ve eslesme kacinca kunye
    # URETILMEDI -- denetim yakaladi: "bilancolar" ve "yorum"
    # sayfalarinda "1 gorsel ATIFSIZ basiliyor" hatasi. Ayni gorselin
    # farkli boyu ayni gorseldir; atif da aynidir.
    adlar = {y.rsplit("/", 1)[-1] for y in yollar}
    atiflar = []
    for f in (x for liste in kayit.veri.values() for x in liste):
        if f["dosya"].rsplit("/", 1)[-1] in adlar:
            k = _foto.Foto(**f).kisa_atif
            if k not in atiflar:
                atiflar.append(k)
    if not atiflar:
        return ""
    return ('<p class="foto-kunye-toplu">Görseller: '
            + " · ".join(html.escape(a) for a in sorted(atiflar))
            + "</p>\n")


def yaz(goreli: str, icerik: str) -> pathlib.Path:
    hedef = CIKTI / goreli.lstrip("/")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if goreli.endswith(".html") and _KUNYE_ISARETI in icerik:
        kunye = _foto_kunyeleri(icerik)
        if kunye:
            icerik = icerik.replace(
                _KUNYE_ISARETI, kunye + _KUNYE_ISARETI, 1)
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


#: "Bu haber hangi alanlari etkiliyor?" kutusundaki alanlar.
#:
#: Varlik kodu -> gorunen ad. Liste KISA tutuluyor: okurun bir bakista
#: sayabilecegi kadar. Alan, haberin bagli oldugu varliklardan ya da
#: konunun duyarlilik tablosundan geliyor.
#:
#: GUVEN SKORU YOK -- bilincli.
#: Kullanici "Guven Skoru %83" onerdi; yapilmadi. O sayinin arkasinda
#: bir hesap yok ve sitenin en temel ilkesi "hesaplamadigimizi olcum
#: gibi sunmayiz". Ayni gerekceyle daha once "Veri Gucu 97" kaldirildi.
#: Bu kutu ise TURETILMIS: her isaret, depodaki bir baga karsilik
#: geliyor.
ETKI_ALANLARI = (
    ("BIST100", "BIST"),
    ("USDTRY", "Dolar/TL"),
    ("US10Y", "Tahvil"),
    ("TCMB_FAIZ", "Faiz"),
    ("TUFE_TR", "Enflasyon"),
    ("SEK_BANKA", "Bankalar"),
    ("BRENT", "Petrol"),
    ("XAU", "Altın"),
    ("CARI_TR", "Cari denge"),
    ("DIS_TICARET_TR", "Dış ticaret"),
)

#: Konu -> o konunun her zaman etkiledigi alanlar.
#: Varlik indeksi haberin METNINDEN turetiyor; bu tablo KONUDAN.
#: Ikisi birlestiriliyor -- biri digerinin kacirdigini yakaliyor.
KONU_ETKISI = {
    "Enflasyon": ("TUFE_TR", "TCMB_FAIZ", "USDTRY", "SEK_BANKA"),
    "Para politikası": ("TCMB_FAIZ", "SEK_BANKA", "BIST100", "USDTRY"),
    "Dış ticaret": ("DIS_TICARET_TR", "CARI_TR", "USDTRY"),
    "Enerji": ("BRENT", "CARI_TR", "TUFE_TR"),
    "Jeopolitik": ("BRENT", "XAU", "USDTRY"),
    "Bankacılık": ("SEK_BANKA", "TCMB_FAIZ", "BIST100"),
    "Borsa": ("BIST100", "USDTRY"),
    "Altın ve emtia": ("XAU", "USDTRY"),
    "İstihdam ve ücret": ("TUFE_TR", "SEK_BANKA"),
}


def etki_alanlari(h: dict, varliklar) -> list[str]:
    """Haberin etkiledigi alanlar -- TURETILMIS, tahmin degil.

    Kaynak iki tane: haberin bagli oldugu varliklar (metinden) ve
    konunun sabit etki listesi (tablodan). Biri digerinin kacirdigini
    yakaliyor: "TCMB faiz kararini acikladi" metninde BIST gecmiyor
    ama para politikasi kararı BIST'i her zaman ilgilendiriyor.
    """
    kodlar = {v["kod"] for v in (varliklar or [])}
    kodlar |= set(KONU_ETKISI.get(h.get("konu", ""), ()))
    return [ad for kod, ad in ETKI_ALANLARI if kod in kodlar]


def _panel_kodlari() -> frozenset[str]:
    """Turkiye panelinde gosterilen seri kodlari.

    Piyasa kutusu bunlari tekrarlamiyor. Tek kaynak `dosya.TURKIYE_PANEL`
    -- listeyi iki yerde tutmak, birini guncelleyip digerini unutmaya
    davetiye olurdu.
    """
    if _dosya is None:
        return frozenset()
    return frozenset(k for k, _ad, _b, _bas in _dosya.TURKIYE_PANEL)


#: Makale sonunda kac baglanti. Az olursa bosluk kapanmiyor, cok
#: olursa liste okunmuyor ve secim degerini kaybediyor.
DEVAM_SAYISI = 5

#: Izleme listesi kalemi -> varlik kodu.
#:
#: "Bundan sonra izlenecekler" kutucuklari tiklanabilir olsun istendi:
#: "PPK karari"na basinca PPK gecmisi acilsin. Hedef, varlik arsiv
#: sayfasi (`/varlik/<kod>/`).
#:
#: TAM ESLESME ARANMIYOR, ONEK aranıyor: liste "TÜFE" de yaziyor
#: "TÜFE — gıda kalemi" de. Ikisi de TUFE_TR arsivine gitmeli.
#:
#: Eslesmeyen kalem DUZ METIN kaliyor. Tiklanip hicbir yere gitmeyen
#: ya da bos sayfaya goturen bir baglanti, baglanti olmamasindan
#: kotudur -- "Rekolte tahminleri" icin arsivimiz yok, oyle de duruyor.
IZLEME_VARLIK = (
    ("PPK", "TCMB_FAIZ"),
    ("Politika faizi", "TCMB_FAIZ"),
    ("Ortalama fonlama", "TCMB_FAIZ"),
    ("TCMB piyasa katılımcıları anketi", "TUFE_TR"),
    ("TCMB rezervleri", "TCMB"),
    ("Bir sonraki TÜFE açıklaması", "TUFE_TR"),
    ("TÜFE", "TUFE_TR"),
    ("Çekirdek", "TUFE_TR"),
    ("Yİ-ÜFE", "UFE_TR"),
    ("Cari işlemler dengesi", "CARI_TR"),
    ("Aylık dış ticaret verisi", "DIS_TICARET_TR"),
    ("Brent petrol", "BRENT"),
    ("Doğal gaz fiyatı", "DGAZ"),
    ("Ons altın", "XAU"),
    ("Dolar endeksi", "DXY"),
    ("ABD 10 yıllık", "US10Y"),
    ("BIST 100", "BIST100"),
    ("BIST işlem hacmi", "BIST100"),
    ("Bitcoin", "BTC"),
    ("EUR/TRY", "EURUSD"),
    ("USD/TRY", "USDTRY"),
    ("İşsizlik oranı", "ISSIZLIK_TR"),
    ("Konut kredisi faizi", "SEK_INSAAT"),
    ("Konut satış istatistikleri", "SEK_INSAAT"),
    ("Turizm geliri istatistikleri", "SEK_TURIZM"),
    ("Ziyaretçi sayısı", "SEK_TURIZM"),
    ("Kredi büyümesi", "SEK_BANKA"),
    ("SPK bülteni", "SPK"),
)


def izleme_baglantilari(izlenecekler, varlik_sayfalari_var: set[str]) -> list[dict]:
    """Izleme kalemlerini varlik arsivine baglar.

    Yalnizca SAYFASI URETILMIS varliga baglaniyor: eslesme tablosunda
    olup da sayfasi olmayan bir kod 404 verirdi.
    """
    cikti = []
    for i in izlenecekler or ():
        yol = ""
        for onek, kod in IZLEME_VARLIK:
            if i.startswith(onek) and kod in varlik_sayfalari_var:
                yol = varlik_yolu(kod)
                break
        cikti.append({"ad": i, "yol": yol})
    return cikti


def ayni_konu_haberleri(h: dict, hepsi: list[dict],
                       haric: set | None = None) -> list[dict]:
    """Ayni konudaki diger haberler, yeniden eskiye.

    Varlik indeksinden gelen "bununla ilgili gelismeler" METINDEN
    turetiliyor ve ortak varlik yoksa bos kaliyor. Bu liste KONUDAN
    turetiliyor, yani her haberde dolu -- ikisi birbirini tamamliyor.
    """
    # SEYIR CIZELGESINDEKILER HARIC.
    #
    # Olculdu: 151 sayfada ayni baslik HEM "Bu dosyanin seyri" HEM
    # "Bunu da okuyun" bolumunde duruyordu. Iki bolum ayni sayfada, on
    # santim arayla, ayni baglantiyi veriyordu -- okur icin ikinci
    # listenin hicbir degeri yok.
    #
    # Seyir once kuruluyor ve adresleri buraya geciyor; "Bunu da
    # okuyun" yalnizca cizelgede OLMAYANLARI gosteriyor.
    haric = haric or set()
    cikti = []
    for x in hepsi:
        if x is h or not x.get("yorumlanir") or not x.get("yol"):
            continue
        if x.get("yol") in haric:
            continue
        if x.get("konu") != h.get("konu"):
            continue
        cikti.append({"baslik": x.get("baslik", ""), "yol": x["yol"],
                      "kurum": x.get("kurum", ""), "tarih": x.get("tarih", "")})
    cikti.sort(key=lambda x: x["tarih"], reverse=True)
    return cikti[:DEVAM_SAYISI]


def _seyir_adresleri(seyir: dict | None) -> set:
    """Cizelgede gecen haberlerin YOLLARI."""
    if not seyir:
        return set()
    return {a.get("yol") for a in seyir.get("adimlar", ()) if a.get("yol")}


def _seyir_basliklari(seyir: dict | None) -> set:
    """Cizelgede gecen BASLIKLAR.

    Yol yetmiyor: bir analiz o haberden URETILDIGI icin ayni basligi
    tasiyabiliyor ve yolu farkli oldugu icin yol suzgecinden geciyor.
    Olculdu: 151 sayfalik tekrar 18'e indi, kalan 18'in hepsi "Bu
    veriyi kullanan analizler" blogundandi -- ayni baslik, farkli yol.
    """
    if not seyir:
        return set()
    return {(a.get("baslik") or "").strip()
            for a in seyir.get("adimlar", ()) if a.get("baslik")}


#: Dosya zaman cizelgesinde en fazla kac gelisme.
#: Uzun liste sayfayi ikinci bir gundem listesine cevirir; kisa liste
#: dosyanin YASADIGINI gosteremez.
DOSYA_ADIM = 8

#: Dosya penceresi (gun). Bir gelisme zincirinin makul omru.
DOSYA_GUN = 14


def dosya_cizelgesi(h: dict, hepsi: list[dict], ilgili: list[dict],
                    bugun: str, varlik_haritasi: dict | None = None) -> dict:
    """Bu haberin AIT OLDUGU DOSYANIN seyri.

    NE DEGISTI
    ----------
    Haber tek seferlik bir icerikti: yayimlanir, okunur, biter. Oysa bir
    gelisme tek haberde bitmiyor -- ABD enflasyonu bekleyis, aciklama,
    Fed uyesi yorumu, tahvil tepkisi olarak siraya diziliyor ve her biri
    ayri bir sayfada oksuz duruyordu.

    Cizelge bu siralamayi GORUNUR yapiyor: okur haberin zincirin
    neresinde durdugunu goruyor, oncesini ve sonrasini tek bakista
    okuyabiliyor.

    DOSYA NEDEN ISARETLENMIYOR, TURETILIYOR
    ---------------------------------------
    Ayri bir "dosya" tablosu acip haberleri elle bagLAMAK, 130 haberlik
    gunluk akista tutulamayacak bir is. Zincir zaten elimizdeki iki
    olcumden turetiliyor:

      varlik indeksi  -- haber METNINDEN cikan ortak varliklar
      konu            -- siniflandiricidan gelen ortak konu

    Ikisi birlestiriliyor: biri digerinin kacirdigini yakaliyor.

    METIN YENIDEN YAZILMIYOR -- ve bu bilincli. "Makale kendini
    guncelliyor" demek, yayimlanmis bir cumlenin sessizce degismesi
    demek olurdu; okurun dun okudugu metin bugun baska bir sey soylerdi.
    Bunun yerine metin sabit kaliyor, DOSYA buyuyor. Guncelleme
    gorunur ve tarihli.
    """
    kendi_an = h.get("an") or h.get("tarih") or ""
    gorulen = {h.get("adres", "")}
    adimlar: list[dict] = []

    def ekle(x: dict) -> None:
        adres = x.get("adres") or x.get("yol") or ""
        if not adres or adres in gorulen:
            return
        if not x.get("yol"):
            return
        gorulen.add(adres)
        adimlar.append({
            "baslik": x.get("baslik", ""),
            "yol": x["yol"],
            "kurum": x.get("kurum", ""),
            "tarih": x.get("tarih", ""),
            "an": x.get("an", ""),
            "kendisi": False,
        })

    # 1) Varlik indeksinden -- metinden turetilmis, en guclu bag.
    for x in ilgili or []:
        ekle(x)
    # 2) Ayni konudan -- AMA ORTAK VARLIK SARTIYLA.
    #
    # Konu tek basina fazla gevsek ve olculdu: "Tarım ve gıda" konusu
    # findik fiyati haberiyle "Mutfaklara bereket getiren lezzetler:
    # 11-17 Ağustos" yazisini ayni dosyaya koyuyordu. Ikisi ayni konu
    # ama ayni GELISME degil.
    #
    # Ortak varlik sarti zinciri daraltiyor: iki haber ayni konudaysa
    # VE en az bir ortak varliga dokunuyorsa ayni dosyanin halkasi.
    # Varlik indeksi yoksa konu sarti tek basina kaliyor -- eksik bir
    # zincir, hic zincir olmamasindan iyi.
    kendi_varlik = set()
    if varlik_haritasi:
        kendi_varlik = {v["kod"] for v in
                        varlik_haritasi.get(h.get("adres", ""), {})
                        .get("varliklar", [])}
    for x in hepsi:
        if x is h or x.get("konu") != h.get("konu"):
            continue
        if gun_farki(x.get("tarih", ""), bugun) > DOSYA_GUN:
            continue
        if kendi_varlik and varlik_haritasi:
            o_varlik = {v["kod"] for v in
                        varlik_haritasi.get(x.get("adres", ""), {})
                        .get("varliklar", [])}
            if not (kendi_varlik & o_varlik):
                continue
        ekle(x)

    adimlar.append({
        "baslik": h.get("baslik", ""), "yol": h.get("yol", ""),
        "kurum": h.get("kurum", ""), "tarih": h.get("tarih", ""),
        "an": kendi_an, "kendisi": True,
    })

    # Zaman sirasi: ESKIDEN YENIYE. Ters sirada olsaydi "once su oldu,
    # sonra bu" okumasi kurulamazdi -- cizelgenin tek isi o.
    adimlar.sort(key=lambda x: x.get("an") or x.get("tarih") or "")

    # Cizelge uzunsa BASTAN kirpiliyor: en yeni gelismeler ve haberin
    # kendisi mutlaka kalmali.
    if len(adimlar) > DOSYA_ADIM:
        kendi_yer = next((i for i, a in enumerate(adimlar) if a["kendisi"]), 0)
        bas = max(0, min(kendi_yer - 2, len(adimlar) - DOSYA_ADIM))
        adimlar = adimlar[bas:bas + DOSYA_ADIM]

    # Bu haberden SONRA gelen gelisme sayisi. Sayfadaki "dosya
    # guncellendi" isareti buna bakiyor.
    sonraki = sum(1 for a in adimlar
                  if not a["kendisi"]
                  and (a.get("an") or a.get("tarih") or "") > kendi_an)

    return {"adimlar": adimlar, "sonraki": sonraki,
            "yeter": len(adimlar) >= 2}


#: Varlik kodu -> takvimdeki seri kodu.
#:
#: Varlik indeksi haberin METNINDEN cikiyor ("tarim disi istihdam" ->
#: NFP); takvim ise seri koduyla calisiyor (PAYEMS). Ikisini
#: baglamadan, bekleyis haberini yaklasan aciklamayla eslestiremiyoruz.
VARLIK_SERI = {
    "NFP": "PAYEMS",
    "CPI_US": "CPIAUCSL",
    "TUFE_TR": "TP.TUKFIY2025.GENEL",
    "UFE_TR": "TP.TUFE1YI.T1",
    "ISSIZLIK_TR": "TP.YISGUCU2.G8",
    "TCMB_FAIZ": "TP.APIFON4",
    "CARI_TR": "TP.HARICCARIACIK.K1",
    "FED": "FED_FAIZ",
}

#: Brifing kac gun ileriye bakiyor. Iki haftadan uzagi "yaklasan"
#: sayilmaz; haberin bekledigi aciklama olmaktan cikar.
BRIFING_GUN = 14


def gosterge_brifingi(h: dict, h_varliklar, takvim: list[dict]) -> dict | None:
    """Haber yaklasan bir veri aciklamasini bekliyorsa brifing kutusu.

    NEDEN VAR
    ---------
    Bekleyis haberinde ("gözler ABD'de açıklanacak tarım dışı istihdam
    verisinde") sayfada su cikiyordu:

        "Verilen metinde sayisal bir olcum bulunmadigi icin, olculen bir
         degeri secip yorumlamak mumkun degildir."

    Aciklanmamis bir veri icin dogru ama ise yaramaz bir cumle. Oysa
    veri gelmeden once de soylenecek gercek seyler var ve hepsi
    elimizde:

        1. gosterge NEDIR        -> takvim.TANIM
        2. NEYI ETKILER          -> takvim.NEDEN
        3. ne zaman, beklenti ne -> yayin takvimi + konsensus
        4. iki dalda MEKANIZMA   -> beklenti motoru

    ESLEME HABERIN VARLIKLARINDAN. Baslikta kelime aramak yerine varlik
    indeksi kullaniliyor: indeks zaten ekleri ve diakritigi cozuyor,
    ikinci bir eslestirici yazmak ayni hatayi ikinci kez yapmak olurdu.
    """
    if _takvim is None or not takvim or not h_varliklar:
        return None

    # VERI ACIKLAMASININ KENDISINDE BRIFING BASILMAZ.
    #
    # Brifing "yaklasan aciklamada ne izlenecek" kutusu ve icindeki
    # "Son aciklanan" degeri DEPODAN geliyor. Ama haberin KENDISI o
    # aciklamaysa, depodaki deger haberden daha eski olabiliyor ve
    # sayfada ayni gosterge icin IKI FARKLI GUNCEL DEGER goruluyor.
    #
    # Olculdu ve yayimlandi: basligi "ABD TÜFE: yıllık %3,73" olan
    # sayfada kutu "Son açıklanan %3,5" diyordu. Ikisi de ABD TUFE
    # yillik; okur hangisinin guncel oldugunu secemez.
    #
    # Bekleyis haberinde ("gozler TUFE verisinde") kutu DOGRU ve
    # degerli; yalnizca aciklamanin kendisinde yeri yok.
    if (h.get("adres") or "").startswith(_VERI_ONEK):
        return None

    kodlar = {VARLIK_SERI.get(v["kod"]) for v in h_varliklar}
    kodlar.discard(None)
    if not kodlar:
        return None

    for k in takvim:
        seri = k.get("seri")
        if not seri or seri not in kodlar:
            continue
        tanim = _takvim.TANIM.get(seri, "")
        neden = (_takvim.YERLI_NEDEN.get(seri) or _takvim.NEDEN.get(seri, ""))
        if not tanim:
            # Tanimi olmayan gosterge icin brifing BASILMIYOR: kutunun
            # ilk sorusu "bu nedir" ve cevabi yoksa geri kalani havada
            # kalir.
            continue
        return {
            "ad": k["ad"], "gun": k["gun"], "saat": k["saat"],
            "ulke": k["ulke"], "kesin": k["kesin"],
            "tanim": tanim, "neden": neden,
            "beklenti": k.get("beklenti"),
        }
    return None


#: Seri kodu onekine gore kaynak kunyesi.
#:
#: Baglanti YALNIZCA gercekten cozulen adreslere veriliyor. FRED her
#: seri icin kalici bir sayfa yayimliyor; EVDS'de seri bazli kalici
#: adres YOK (tek sayfalik uygulama), o yuzden yalnizca kurum adi ve
#: kok adres yaziliyor. Cozmeyecek bir baglanti vermek, okuru
#: dogrulayamayacagi bir yere gondermek olurdu.
KAYNAK_KUNYE = (
    ("TP.", "TCMB EVDS", "https://evds2.tcmb.gov.tr/", False),
    ("TCMB_POLITIKA", "TCMB · PPK basın duyurusu",
     "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/"
     "Duyurular/Basin", True),
    ("", "FRED · St. Louis Fed", "https://fred.stlouisfed.org/series/", True),
)


def _seri_kaynagi(kod: str) -> dict:
    """Seri kodundan kaynak kaydi. Kod bosluksa None."""
    if not kod:
        return {}
    for onek, ad, adres, seri_baglantisi in KAYNAK_KUNYE:
        if onek and not kod.startswith(onek):
            continue
        if onek == kod == "TCMB_POLITIKA":
            return {"ad": ad, "adres": adres, "not": "politika faizi kararı"}
        if onek == "TP.":
            return {"ad": ad, "adres": adres, "not": kod}
        # FRED: seri bazli kalici sayfa var
        return {"ad": ad, "adres": adres + kod, "not": kod}
    return {}


def kaynaklar(h: dict, d, brifing: dict | None) -> list[dict]:
    """Bu SAYFANIN gercekten kullandigi kaynaklar.

    NEDEN VAR
    ---------
    Sitenin butun iddiasi "dogrulanabilir olcum". Ama okur bir sayiyi
    dogrulamak istediginde nereye bakacagini bilmiyordu: kaynak adi
    sayfanin ustunde bir yerde, seri kodu baska bir kutuda, fotograf
    atfi baska yerde.

    Bu bolum hepsini tek yere topluyor -- ve SABIT BIR LISTE DEGIL,
    sayfanin O AN kullandigi kaynaklardan turetiliyor. Kullanilmayan
    bir kaynagi listelemek, dogrulanabilirlik iddiasini sahte bir
    genislikle sismek olurdu.
    """
    cikti: list[dict] = []
    gorulen: set = set()

    def ekle(kayit: dict) -> None:
        if not kayit or not kayit.get("ad"):
            return
        im = (kayit["ad"], kayit.get("not", ""))
        if im in gorulen:
            return
        gorulen.add(im)
        cikti.append(kayit)

    # 1. Haberin kendi kaynagi. TICARI KAYNAKTA ZORUNLU.
    if h.get("adres", "").startswith("http"):
        ekle({"ad": h.get("kurum_tam") or h.get("kurum", ""),
              "adres": h["adres"],
              "not": "haberin kaynağı"})

    # 2. Sayfada gosterilen seriler.
    if d is not None:
        for g in getattr(d, "turkiye", ()) or ():
            ekle(_seri_kaynagi(getattr(g, "kod", "")))

    # 3. Brifingdeki gosterge ve takvim kaynagi.
    if brifing:
        ekle({"ad": "BLS · ABD Çalışma İstatistikleri Bürosu",
              "adres": "https://www.bls.gov/schedule/news_release/",
              "not": "yayın takvimi"})
        b = brifing.get("beklenti")
        if b is not None and getattr(b, "esik_kaynak", "") == "beklenti":
            ekle({"ad": "ForexFactory", "adres": "https://www.forexfactory.com/calendar",
                  "not": "beklenti (konsensüs)"})

    return cikti


#: Haberin kendi yapisal baglarindan en fazla kac tanesi basilir.
DUZENEK_SAYISI = 4


def duzenek(h_varliklar) -> list[dict]:
    """Haberin KENDI varliklarinin yapisal baglari.

    NEDEN VAR
    ---------
    Olculdu: 204 haber sayfasinda "Bu neden kritik?" metni yalnizca 40
    farkli surumde vardi ve en siki 34 sayfada AYNIYDI. Sebep, o metnin
    KONU tablosundan gelmesi: ayni konudaki her haber ayni cumleyi
    tasiyor.

    Bu bolum konudan degil, HABERIN KENDI VARLIKLARINDAN kuruluyor.
    Ayni olcumde 149 haberin 59 farkli varlik kumesi vardi -- yani
    konuya gore uc kattan fazla ayrisiyor. Ustelik her satir depodaki
    bir baga karsilik geliyor, uydurulmuyor.

    YON IDDIA EDILMIYOR. Bag "etkiler" der, "dusurur" demez -- varlik
    sayfalarindaki kuralin aynisi. `dayanak` alani da basiliyor:
    muhasebe kimligi ile gozlem ayni sey degil.
    """
    if _varlik is None or _beyin is None or not h_varliklar:
        return []
    kodlar = [v["kod"] for v in h_varliklar]
    cikti: list[dict] = []
    gorulen: set = set()
    try:
        with _beyin.baglan() as b:
            for kod in kodlar:
                for g in _varlik.baglar(b, kod):
                    if not g.get("aciklama"):
                        # Aciklamasiz bag SATIR OLARAK basilmiyor:
                        # "A -> B" tek basina okura mekanizmayi
                        # anlatmiyor, yalnizca yer kapliyor.
                        continue
                    im = (g["kaynak"], g["hedef"])
                    if im in gorulen:
                        continue
                    gorulen.add(im)
                    cikti.append(g)
    except Exception:
        return []
    cikti.sort(key=lambda g: -(g.get("guc") or 0))
    return cikti[:DUZENEK_SAYISI]


#: Haber konusu -> analiz kategorisi. Makale sonunda "bu veriyi kullanan
#: analizler" bolumunu besliyor.
KONU_KATEGORI = {
    "Para politikası": "Makro", "Enflasyon": "Makro", "Döviz": "Makro",
    "Enerji": "Makro", "Altın ve emtia": "Makro", "Jeopolitik": "Makro",
    "Dış ticaret": "Makro", "Borsa": "Makro",
    "Kripto varlıklar": "Teknik Görünüm",
    "Şirket haberleri": "Bilanço Analizi",
    "Bankacılık": "Bilanço Analizi",
}


def ilgili_analizler(h: dict, analizler: list,
                    haric_baslik: set | None = None) -> list[dict]:
    """Haberin konusuyla ilgili yayimlanmis analizler.

    Kategori eslemesi kaba ama DOGRU yonde: makro haberin altina
    bilanco analizi koymak okuru bosa goturur. Eslesme yoksa bolum
    hic basilmaz -- alakasiz baglanti, baglanti olmamasindan kotudur.
    """
    kat = KONU_KATEGORI.get(h.get("konu", ""))
    if not kat:
        return []
    # SEYIR CIZELGESINDEKI BASLIKLAR HARIC.
    #
    # Bir analiz o haberden URETILDIGI icin ayni basligi tasiyabiliyor
    # ve yolu farkli oldugu icin yol suzgecinden geciyordu. Olculdu:
    # 151 sayfalik tekrar once 18'e indi, kalan 18'in hepsi "Bu veriyi
    # kullanan analizler" blogundandi -- ayni baslik, farkli yol.
    haric_baslik = haric_baslik or set()
    return [{"baslik": a.baslik, "yol": a.yol, "tarih": a.tarih}
            for a in analizler
            if a.kategori == kat
            and (a.baslik or "").strip() not in haric_baslik][:DEVAM_SAYISI]


def ai_yorum_oku() -> dict[str, str]:
    """Depodaki AI yorumlari: adres -> metin.

    Tablo yoksa BOS sozluk. Yorum hatti hic calismamis olabilir ve bu
    sitenin kurulmasini engellememeli.
    """
    if _beyin is None:
        return {}
    try:
        with _beyin.baglan() as b:
            r = b.execute("SELECT adres, metin FROM ai_yorum").fetchall()
    except Exception:
        return {}
    return {x[0]: x[1] for x in r}


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

    # MANSET UZUNLUGU: turetilmis alan, depoda SAKLANMIYOR.
    #
    # Kisaltma burada yapiliyor cunku bir GORUNUM kararidir; depoda tam
    # baslik duruyor ve kural degisirse arsivin tamami kendiliginden
    # yeniden hesaplaniyor -- `tazele`nin var olma sebebi bu.
    #
    # Olculdu: yayimlanan 31 basligin uzunlugu 110 karakteri asiyordu,
    # en uzunu 231 karakterdi. Bunlar manset degil, tel-ajans
    # uyarisinin cumlesinin tamamiydi.
    #
    # BILGI KAYBOLMUYOR: sayfa govdesi basligin TAM metnini zaten
    # tekrar ediyor (olculdu, bire bir). Okur kisa manseti gorup tam
    # cumleyi hemen altinda buluyor.
    if _bicim is not None and h.get("baslik"):
        h["baslik"] = _bicim.manset_kisalt(h["baslik"])

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
            # `yorumlanir` SARTI EKLENDI.
            #
            # Arsiv yalnizca `sayfa_veri`ye bakiyordu ve bayrak hic
            # okunmuyordu. Sonuc: bir oge sonradan "yayimlanmaz" diye
            # isaretlense bile sayfasi her insada YENIDEN uretiliyordu.
            # Olculdu -- gurultu suzgeci siklastirildiktan sonra alti
            # sayfa hala ayaktaydi: silahli saldiri, taziye mesaji,
            # market indirim katalogu.
            #
            # Bayragi indirmek artik gercekten sayfayi kaldiriyor.
            satirlar = b.execute(
                "SELECT adres, sayfa_veri FROM haber"
                " WHERE sayfa_veri IS NOT NULL AND yorumlanir = 1"
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
            # YAYIMLANDI BAYRAGI ONCE SIFIRLANIYOR.
            #
            # Bayrak yalnizca 1'e cekiliyordu, hic 0'a donmuyordu. Sonuc:
            # yeniden siniflandirmada "yorumlanmaz" cikan bir haberin
            # sayfasi uretilmiyor (dogru davranis) ama varlik sayfalari
            # ve "ayni dosyadaki gelismeler" bolumu depodaki eski
            # `yayin_yolu` degerine baglanmaya devam ediyordu.
            #
            # Olculdu: uc kirik baglanti. Ikisi varlik sayfasindan
            # ("Fed yetkililerinden sahin aciklamalar"), biri haber
            # sayfasindan. Sayi kucuk gorunuyor ama kalici: siniflandirici
            # her duzeldiginde bir yenisi ekleniyor ve hicbiri
            # kendiliginden kapanmiyor.
            #
            # Sifirlama ayni islemin icinde: `baglan()` baglam yoneticisi
            # hata durumunda geri aliyor, yani yarim kalmis bir
            # calistirma butun haberleri yayimdan kaldirmiyor.
            b.execute("UPDATE haber SET yayimlandi=0 WHERE yayimlandi=1")
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


def onem_puanla(haberler: list[dict], varlik_haritasi: dict) -> None:
    """Her habere `onem`, `katman`, `katman_adi` yazar. Yerinde degistirir.

    `onem` alani SABLONA GIDIYOR ama HICBIR SABLONDA BASILMIYOR --
    siralama ve `--onem` dokumu icin duruyor. Ekranda gorunen tek sey
    katman adi; bir sayi degil bir yargi (bkz. onem.py bas yorumu).

    Modul yoksa herkes "normal": eksik bir siralamayla site kurulur,
    puanlama olmadigi icin kurulmamasi sacma olurdu.
    """
    for h in haberler:
        if _onem is None:
            h["onem"], h["katman"] = 0, "normal"
            h["katman_adi"] = "Normal"
            continue
        adres = h.get("adres", "")
        v = varlik_haritasi.get(adres, {}).get("varliklar") or []
        o = _onem.puanla(
            h.get("baslik", ""),
            h.get("baslik_kaynak", ""),
            konu=h.get("konu", ""),
            # KISA KOD geciyor, `kurum_tam` DEGIL. Kaynak tablolari
            # ("TCMB", "Fed") kisa kodla anahtarli; tam ad gecildiginde
            # "Türkiye Cumhuriyet Merkez Bankası" hicbir tabloya
            # dusmuyor ve TCMB duyurulari birincil kaynak sayilmiyordu.
            # Varlik indeksi TERSINI istiyor (tam ad) -- ikisi ayri
            # ihtiyac, ayni alan degil.
            kurum=h.get("kurum", ""),
            varlik_sayisi=len(v),
            # Veri hattinin iddia sahibi FRED/EVDS -- birincil kaynak.
            # `kurum` alani ise hattimizin sekli
            # ("FinancialJuice") ve puanda yaniltirdi.
            veri_mi=adres.startswith(_VERI_ONEK),
        )
        h["onem"] = o.puan
        # Bilesenler `--onem` dokumu icin saklaniyor. Dokum bunlari
        # yeniden hesapliyordu ve varlik sayisini gecemedigi icin
        # kapsam HER ZAMAN 0 gorunuyordu; yani denetim araci, denetledigi
        # motorun puanini gostermiyordu.
        h["onem_bilesen"] = list(o.bilesenler)
        h["onem_taban"] = o.taban_uygulandi
        h["katman"] = o.katman
        h["katman_adi"] = o.ad
        h["olay_turu"] = o.olay_turu


#: Takvimde kac gun ileri bakiliyor.
#:
#: Daha uzun pencere ana sayfayi bir takvim uygulamasina cevirir; daha
#: kisa olan "bu hafta ne var" sorusunu cevaplayamaz.
TAKVIM_GUN = 10
TAKVIM_EN_COK = 8

#: Takvimde yalnizca bu onem ve ustu gorunuyor. Dusuk onemli BLS
#: yayinlari ("ilce istihdami") listeyi doldurup asil olani gizlerdi.
TAKVIM_ONEM_ESIGI = 2


def _seri_son(b, kod: str) -> tuple[float | None, str, str]:
    """Bir serinin son gozlemi: (deger, birim, tarih)."""
    try:
        r = b.execute("SELECT deger, birim, tarih FROM gosterge WHERE kod=?"
                      " ORDER BY tarih DESC LIMIT 1", (kod,)).fetchone()
    except Exception:
        return None, "", ""
    return (r[0], r[1] or "", r[2]) if r else (None, "", "")


def _tepkiler(b, tur: str) -> list[tuple[str, float]]:
    """Bir olay TURUNDE olculmus fiyat tepkileri.

    Uydurulmuyor: `tepki` tablosu haber sonrasi gercek fiyat
    hareketlerini kaydediyor. Gozlem azsa `beklenti._tepki_ozeti`
    zaten hicbir sey yazmiyor.
    """
    if not tur:
        return []
    try:
        r = b.execute(
            "SELECT t.varlik, t.degisim FROM tepki t"
            " JOIN olay o ON o.id = t.olay_id"
            " WHERE o.tur = ? AND t.pencere_sn = 3600", (tur,)).fetchall()
    except Exception:
        return []
    # NULL degisim ATLANIYOR. Olcum tamamlanmamis bir tepki kaydi var
    # (fiyat cekilememis) ve `None * 100` butun bolumu dusuruyordu.
    return [(x[0], x[1] * 100.0) for x in r if x[1] is not None]


#: Seri kodu -> (konu, olay turu). Beklenti kutusunun hangi mekanizmayi
#: ve hangi gecmis tepkileri kullanacagini belirliyor.
TAKVIM_KONUSU = {
    "PAYEMS": ("İstihdam ve ücret", "istihdam"),
    "UNRATE": ("İstihdam ve ücret", "istihdam"),
    "CES0500000003": ("İstihdam ve ücret", "istihdam"),
    "CPIAUCSL": ("Enflasyon", "enflasyon"),
    "CPILFESL": ("Enflasyon", "enflasyon"),
    "PPIFIS": ("Enflasyon", "enflasyon"),
    "FED_FAIZ": ("Para politikası", "faiz"),
    "TP.TUKFIY2025.GENEL": ("Enflasyon", "enflasyon"),
    "TP.TUFE1YI.T1": ("Enflasyon", "enflasyon"),
    "TP.FE25.OKTG04": ("Enflasyon", "enflasyon"),
    "TP.YISGUCU2.G8": ("İstihdam ve ücret", "istihdam"),
    "TP.HARICCARIACIK.K1": ("Dış ticaret", ""),
    "TP.ENFBEK.PKA12ENF": ("Enflasyon", "enflasyon"),
}


def beklenti_yaz(b, yayinlar) -> int:
    """Kaynaktan gelen konsensusu depoya yazar.

    NEDEN DEPOYA: kaynak hiz sinirli ve otomasyon yarim saatte bir
    calisiyor. Onbellek dosyasi .gitignore'da, yani CI her calistirmada
    sifirdan cekiyor; kaynak o an vermezse site beklentisiz kuruluyor
    ve bir onceki iyi surumu SESSIZCE eziyor -- islem bile olusmadigi
    icin iz kalmiyor.
    """
    n = 0
    for y in yayinlar:
        if not (y.kod and y.beklenti):
            continue
        try:
            n += b.execute(
                "INSERT INTO yayin_beklenti"
                " (kod, an, beklenti, onceki, kaynak, kayit_ani)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(kod, an) DO UPDATE SET"
                "   beklenti=excluded.beklenti, onceki=excluded.onceki,"
                "   kayit_ani=excluded.kayit_ani",
                (y.kod, y.an.isoformat(), y.beklenti, y.onceki, y.kaynak,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ).rowcount
        except Exception:
            continue
    return n


def beklenti_oku(b, kod: str, an) -> tuple[str, str, str]:
    """Depodaki konsensus: (beklenti, onceki, kaynak). Yoksa uc bos.

    GUN esleSmesi kullaniliyor, tam an degil: kaynak saati bir dakika
    kaydirdiginda kayit bulunamaz olurdu.
    """
    try:
        r = b.execute(
            "SELECT beklenti, onceki, kaynak FROM yayin_beklenti"
            " WHERE kod=? AND substr(an,1,10)=? LIMIT 1",
            (kod, an.date().isoformat())).fetchone()
    except Exception:
        return "", "", ""
    return (r[0] or "", r[1] or "", r[2] or "") if r else ("", "", "")


def takvim_kutulari() -> list[dict]:
    """Ana sayfadaki "Yaklaşan veriler" bolumu.

    Her kalem: ne zaman, hangi ulke, son deger ne, esik nerede ve iki
    dalda hangi MEKANIZMA calisir. Fiyat yonu IDDIA EDILMIYOR (bkz.
    beklenti.py bas yorumu).
    """
    if _yt is None:
        return []
    try:
        yayinlar = _yt.cek(TAKVIM_GUN)
    except Exception as e:
        print(f"  yayin takvimi cekilemedi: {e}")
        return []
    if _yt.OKUNAMAYAN:
        for k, h in _yt.OKUNAMAYAN:
            print(f"  takvim kaynagi okunamadi: {k} -- {h}")

    yayinlar = [y for y in yayinlar if y.onem >= TAKVIM_ONEM_ESIGI]
    cikti: list[dict] = []

    def kutula(y, b) -> dict:
        # Kaynak bu calistirmada beklenti vermediyse DEPODAN okunuyor.
        # Bayat bir konsensus, konsensus olmamasindan iyidir ve rakamlar
        # gun icinde nadiren degisiyor.
        if b is not None and y.kod and not y.beklenti:
            bk, on, kyn = beklenti_oku(b, y.kod, y.an)
            if bk:
                y = _yt.replace_yayin(y, beklenti=bk, onceki=on, kaynak=kyn)
        kutu = {
            "ad": y.ad, "ulke": y.ulke, "onem": y.onem, "kesin": y.kesin,
            "an": y.an.isoformat(), "yerel": y.yerel,
            "gun": y.yerel.strftime("%d.%m"),
            "saat": y.yerel.strftime("%H:%M"),
            "beklenti": None,
            # Konsensus kaynagi ekranda YAZILIYOR: okur sayinin
            # nereden geldigini bilmeli.
            "kaynak": y.kaynak,
            # Seri kodu: haber brifingi bu alanla eslesiyor.
            "seri": y.kod,
        }
        if b is None or not y.kod or _beklenti is None:
            return kutu
        # HATA YUTULMUYOR. Ilk yazimda bu blok sessizce bosa dusuyordu
        # ve butun beklenti kutulari yoktu; sebebi ancak elle deneyince
        # goruldu. Tek kalem coktugunde takvimin tamami dusmesin diye
        # yakalaniyor, ama SESSIZ degil.
        try:
            konu, olay_turu = TAKVIM_KONUSU.get(y.kod, ("", ""))
            deger, birim, tarih = _seri_son(b, y.kod)
            # BICIMLENDIRME TAKVIM MODULUNDEN.
            #
            # `beklenti.bicimle` ikinci bir bicimlendiriciydi ve ayni
            # sayi iki yerde iki turlu goruniyordu: haber sayfasinda
            # "44 bin kişi", takvim kutusunda "44.000,00 kişi". Tek
            # bicimlendirici, tek gorunum.
            son_metin = ""
            if deger is not None and _takvim is not None:
                son_metin = _takvim.bicim(deger, birim)
            esik = esik_birim = None
            bs = _beklenti.BEKLENTI_SERISI.get(y.kod)
            if bs:
                esik, esik_birim, _ = _seri_son(b, bs)
            # KONSENSUS VARSA ESIK ODUR.
            #
            # Takvim kaynagi beklenti veriyorsa hem esik hem "son
            # aciklanan" ONDAN aliniyor -- ikisi ayni kaynaktan geldigi
            # icin birimleri kesinlikle uyumlu. Kendi depomuzun degeriyle
            # kaynagin beklentisini ayni cumlede kullanmak iki farkli
            # bicimi ("85K" ve "57,00 bin kişi") karistirmak olurdu.
            k = _beklenti.kur(y.kod, y.ad, konu, deger, birim, tarih,
                              esik_deger=esik, esik_birim=esik_birim or "",
                              tepkiler=_tepkiler(b, olay_turu),
                              esik_metin=y.beklenti,
                              kaynak_onceki=y.onceki,
                              son_metin=son_metin)
            if k.dolu:
                kutu["beklenti"] = k
        except Exception as e:
            print(f"  takvim: {y.kod} beklenti kutusu kurulamadi: {e}")
        return kutu

    # `baglan()` BIR BAGLAM YONETICISI, baglantinin kendisi degil.
    #
    # Once `b = _beyin.baglan()` yaziliyordu ve `b` bir sarmalayici
    # nesneydi; `b.execute(...)` AttributeError veriyor, `_seri_son`
    # onu yakalayip None donuyor ve BUTUN beklenti kutulari sessizce
    # bos kaliyordu. Hicbir hata mesaji yoktu -- sayfa yalnizca eksik
    # basiliyordu.
    if _beyin is None:
        cikti = [kutula(y, None) for y in yayinlar[:TAKVIM_EN_COK]]
    else:
        try:
            with _beyin.baglan() as b:
                yazilan = beklenti_yaz(b, yayinlar)
                if yazilan:
                    print(f"takvim: {yazilan} beklenti depoya yazildi")
                cikti = [kutula(y, b) for y in yayinlar[:TAKVIM_EN_COK]]
        except Exception as e:
            print(f"  takvim: depo acilamadi ({e}); beklenti kutulari yok")
            cikti = [kutula(y, None) for y in yayinlar[:TAKVIM_EN_COK]]

    dolu = sum(1 for k in cikti if k["beklenti"])
    print(f"takvim: {len(cikti)} yaklasan veri, {dolu} beklenti kutusu")
    return cikti


#: Canli akista kac kalem. Akis SAYFAYI DOLDURMAK icin degil, hareketi
#: gostermek icin var; sonsuz liste ana sayfayi yeniden haber listesine
#: cevirirdi. Devami /gundem/'de.
#:
#: 20 -> 40: besleme penceresi 40'tan 120'ye cikinca 20 kalem gunun
#: yalnizca son bir saatini gosteriyordu. Liste kendi icinde kayiyor
#: (sutun yapiskan ve `overflow-y: auto`), yani uzun liste sayfayi
#: uzatmiyor -- sadece akisin kapsadigi sure uzuyor.
AKIS_SAYISI = 40


#: One cikan bolumunun zaman penceresi (gun).
#:
#: BUGUNLE SINIRLI DEGIL, ve sebebi olculdu: gunun yayimlanabilir haber
#: sayisi 9 civari ve bunlarin puani esigi gecenler dorde iniyor. Tek
#: gunle sinirlansa bolum surekli yarim kalirdi.
#:
#: Yaniltmiyor cunku HER KALEMDE goreli zaman basiliyor -- dunku bir
#: haberin yaninda "dun" yaziyor. Tarihi gizleyip "bugun" demek
#: yaniltmak olurdu; tarihi gostererek pencereyi genisletmek degil.
ONE_CIKAN_PENCERE = 2


def one_cikan_haberler(haberler: list[dict], bugun: str = "") -> list[dict]:
    """Katman 2: one cikan gelismeler.

    Puan siralamasi + tekrar elemesi `onem.sec` icinde. Burada yalnizca
    haberin kendisi geri veriliyor -- puan sablona gitmiyor, cunku
    sablonun puani BASMA ihtimali olmamali.
    """
    if bugun:
        haberler = [h for h in haberler
                    if gun_farki(h.get("tarih", ""), bugun) < ONE_CIKAN_PENCERE]
    if _onem is None:
        return haberler[:_ONEM_YEDEK_SAYISI]
    ciftler = [(_onem.Onem(puan=h.get("onem", 0),
                           katman=h.get("katman", "normal")), h)
               for h in haberler]
    return [h for _, h in _onem.sec(ciftler, anahtar=_veri_kumesi)]


def _veri_kumesi(h: dict) -> str:
    """Ayni gun, ayni konudaki VERI aciklamalari tek kume.

    Enflasyon gunu TUFE, Yi-UFE, cekirdek enflasyon ve hanehalki
    beklentisi olarak DORT ayri haber uretiyor. Basliklari birbirine hic
    benzemiyor, o yuzden metin karsilastirmasi bunlari yakalamiyor --
    ama dordu de tek enflasyon hikayesinin yuzleri ve dordunu birden
    one cikan listeye koymak, listenin yarisini tek konuya harcamak
    demek.

    Elenen seriler kaybolmuyor: her biri kendi sayfasinda duruyor ve
    secilen haberin "ayni konuda son gelismeler" bolumu hepsini
    listeliyor.

    Veri aciklamasi OLMAYAN haberde bos donuyor -- kume elemesi yalnizca
    kendi urettigimiz seri haberlerine uygulaniyor, gercek habere
    degil.
    """
    if not h.get("adres", "").startswith(_VERI_ONEK):
        return ""
    return f"{h.get('tarih', '')}|{h.get('konu', '')}"


#: Puanlama yoksa ana sayfa yine dolmali: en yeni haberler.
_ONEM_YEDEK_SAYISI = 10


#: AI yorum akisinda kac kalem.
AI_AKIS_SAYISI = 6


def ai_akisi(haberler: list[dict], en_cok: int = AI_AKIS_SAYISI) -> list[dict]:
    """Ana sayfadaki "Netaris ne diyor" akisi.

    NEDEN PIYASA OZETININ YERINE
    ----------------------------
    Orada endeks, Brent, faiz ve kur tablosu duruyordu. O tabloyu onlarca
    platform gosteriyor ve hicbirinden farkimizi anlatmiyordu -- ustelik
    ayni sayilar haber sayfalarindaki "Güncel veriler" bolumunde zaten
    var, yani ana sayfadaki kopya ikinci bir tekrardi.

    Buradaki kalemler VERI DEGIL, VERININ ANLAMI: her biri olculmus bir
    sayidan uretilmis bir cikarim ve kendi haberine baglaniyor.

    UYDURULMUYOR: yalnizca depoda GERCEKTEN yorumu olan haberler
    giriyor. Yorum yoksa bolum kisa kalir, hicbiri yoksa hic basilmaz --
    bos bir "Netaris ne diyor" basligi, soyleyecek sozu olmadigini
    ilan etmenin en gurultulu yolu olurdu.
    """
    # SIRA ONEME GORE, ZAMANA GORE DEGIL.
    #
    # Bolum zamana gore siralaniyordu, yani bir haberin buraya girmesi
    # icin tek sart YORUMUNUN OLMASIYDI. Olculdu: alti kartin UCU en
    # yuksek puanli haberler arasinda degildi; puani 54 ve 48 olan iki
    # haber ise (yorumlari olmadigi icin) bolumde yoktu. Ustelik bu
    # bolum "Bugunun onemli gelismeleri"nin USTUNDE duruyor.
    #
    # Promptun 14. maddesi tam bunu yasakliyor: "yalnizca AI yorumu
    # uretildigi icin her haber mansete tasinmamalidir". Yorum bir
    # GIRIS SARTI (soyleyecek sozumuz var mi), siralama olcutu degil.
    #
    # Zaman ikincil olcut olarak kaldi: esit puanli iki haberde yeni
    # olan once gelsin.
    olan = [h for h in haberler
            if h.get("ai_yorum_kart") and h.get("yol")]
    olan.sort(key=lambda h: (h.get("onem") or 0,
                             h.get("an") or h.get("tarih") or ""),
              reverse=True)

    # AYNI SEYI SOYLEYEN IKINCI YORUM ALINMIYOR.
    #
    # Olculdu: bolumun alti kartindan UCU ayni cumleyi kuruyordu --
    # "Brent petrolun kapanis fiyati 88,90 $...". Uc ayri haberdi
    # (Yemen'de liman saldirisi, Iran cumhurbaskaninin gorusmesi,
    # Axios roportaji) ama ucu de ayni dosyaya bagli ve o dosyadaki tek
    # sayi Brent'ti; model elindeki tek olcumu anlatti.
    #
    # Kok sebep uretimde: yorum girdisi haberin DOSYASINDAKI bulgulari
    # tasiyor ve olcumu olmayan haberlerde model onlara tutunuyor.
    # Burasi o sorunu cozmuyor, GORUNMESINI engelliyor -- ayni cumleyi
    # uc kez basan bir bolum, ne dedigimize dair guveni de ucuruyor.
    secilen: list[dict] = []
    for h in olan:
        metin = h.get("ai_yorum_kart", "")
        if _onem is not None and any(
                _onem.benzer(metin, s.get("ai_yorum_kart", ""))
                for s in secilen):
            continue
        secilen.append(h)
        if len(secilen) >= en_cok:
            break
    return secilen


def canli_akis(haberler: list[dict], en_cok: int = AKIS_SAYISI) -> list[dict]:
    """Katman 1: ham akis, en yeni ustte.

    ELEME YOK. Katman 2 bir SECIM, burasi bir KAYIT -- akis suzulurse
    okur "bir sey oldu mu" sorusunun cevabini burada bulamaz ve akisin
    tek isi o.

    Siralama `an` (ilk gorulme damgasi) uzerinden. Damgasi olmayan
    haber tarihine gore siraya giriyor; ikisi de yoksa listenin sonuna
    dusuyor -- ama LISTEDEN CIKMIYOR.
    """
    def anahtar(h: dict) -> str:
        return h.get("an") or (h.get("tarih") or "")
    return sorted(haberler, key=anahtar, reverse=True)[:en_cok]


#: Kart turu -> gorunen ad. Kartlarin hepsi ayni gorunmemeli: okur
#: bakmadan once neye baktigini bilsin.
#:
#: Tur KONUDAN turetiliyor, elle etiketlenmiyor -- elle etiket, 130
#: haberde tutarli kalmaz.
KART_TURU = {
    "Para politikası": "makro",
    "Enflasyon": "makro",
    "İstihdam ve ücret": "makro",
    "Dış ticaret": "makro",
    "Vergi ve kamu maliyesi": "makro",
    "Jeopolitik": "jeopolitik",
    "Enerji": "emtia",
    "Altın ve emtia": "emtia",
    "Tarım ve gıda": "emtia",
    "Döviz": "piyasa",
    "Borsa": "piyasa",
    "Kripto varlıklar": "piyasa",
    "Bankacılık": "sirket",
    "Şirket haberleri": "sirket",
    "Piyasa düzenlemesi": "duzenleme",
    "Konut ve kira": "sektor",
    "Turizm": "sektor",
}
KART_VARSAYILAN = "haber"


def kart_turu(h: dict) -> str:
    return KART_TURU.get(h.get("konu", ""), KART_VARSAYILAN)


#: Kartta gorunecek en fazla cumle ve karakter.
#:
#: Kart MERAK UYANDIRMALI, doyurmamali. Uzun yorum kartta okununca
#: habere girmek icin sebep kalmiyor -- kartlardan analizi cikarmamizin
#: sebebi zaten buydu.
KART_CUMLE = 2
KART_HARF = 220


def kart_yorumu(metin: str) -> str:
    """Metni kart boyuna indirir. CUMLE SINIRINDA keser.

    Karakterden kesmek cumleyi ortasindan bolerdi ("...faiz oranlarini
    art") ve yarim cumle, yanlis cumleden beter okunur. Once cumleye
    bolunuyor; ilk cumle bile sinirdan uzunsa kelime sinirinda kesilip
    uc nokta konuyor.
    """
    metin = (metin or "").strip()
    if not metin:
        return ""

    cumleler = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", metin)
    parca = "".join(cumleler[:KART_CUMLE]).strip()

    if len(parca) <= KART_HARF:
        return parca
    kirp = parca[:KART_HARF].rsplit(" ", 1)[0].rstrip(" ,;:")
    return kirp + "…"


def an_yaz(haberler: list[dict]) -> None:
    """Her habere `an` yazar: ISO zaman damgasi, saat dahil.

    NEDEN DEPODAN
    -------------
    `gundem.json` yalnizca TARIH tasiyor ("2026-08-06"). "3 dk once"
    yazabilmek icin saat gerek ve o yalnizca depodaki `ilk_gorulme`
    alaninda var.

    `ilk_gorulme` yayin ani DEGIL, BIZIM GORDUGUMUZ an. Hat sik
    calistigi icin ikisi birbirine yakin; ama esit degiller ve sayfada
    "yayimlandi" diye sunulmuyorlar. Damga bulunamazsa alan hic
    yazilmiyor -- tarih basilir, goreli zaman basilmaz. Uydurma bir
    saat, yanlis bir tazelik izlenimi verirdi.
    """
    if _beyin is None:
        return
    try:
        with _beyin.baglan() as b:
            damga = dict(b.execute(
                "SELECT adres, ilk_gorulme FROM haber"
                " WHERE ilk_gorulme IS NOT NULL").fetchall())
    except Exception:
        return
    for h in haberler:
        d = damga.get(h.get("adres", ""))
        if d:
            h["an"] = d


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


def varlik_sayfalari(ortam, yaz, ortak: dict,
                     dizin_yaz: bool = True) -> list[str]:
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
            # `dizin_yaz=False` iken tek tek sayfalar uretiliyor ama
            # gezilebilir DIZIN basilmiyor: okur bu sayfalara yalnizca
            # izleme listesinden ulassin.
            if dizin and dizin_yaz:
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
    # Kart turu de KODDA yasiyor: sablonda konu->tur eslemesi yazmak,
    # ayni tabloyu uc sablonda tekrarlamak olurdu.
    ortam.filters["kart_turu"] = kart_turu
    ortam.filters["kucuk_foto"] = kucuk_foto
    ortam.filters["orta_foto"] = orta_foto

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
    # "Haberler" MENU LISTESINDE DEGIL: ust menude kendi basina duruyor
    # (bkz. temel.html). Listede kalsaydi "Araştırmalar" acilir menusunun
    # icinde gorunurdu -- oysa haber bir arastirma degil.

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
    # CANLI HABERLER DE TAZELENIYOR, arsiv gibi.
    #
    # `gundem.json` turetilmis alanlari da tasiyor (konu, bolge,
    # yorumlanir, neden_onemli, kanal basligi) ve onlar YAZILDIKLARI
    # ANIN siniflandiricisini tasiyor. Yalnizca arsiv tazelendiginde iki
    # ayri sonuc cikiyordu: ayni site icinde dun yazilan haber eski
    # basligi, bugunku yenisini gosteriyordu. Ustelik siniflandirici
    # duzeltildiginde canli haberler duzelmiyordu -- Goldman
    # "otelenebilir" -> Turizm hatasinin arsivde yeniden yayimlanmasinin
    # sebebi tam olarak buydu.
    #
    # Olculdu: bu adim 40 haberin hicbirinin konusunu ya da yayimlanma
    # kararini degistirmiyor (9 -> 9). Yaptigi tek sey turetilmis metni
    # BUGUNKU kurallara getirmek.
    foto_kayit = foto_defteri()
    gundem["haberler"] = [tazele(h, foto_kayit)
                          for h in gundem.get("haberler", [])]

    for h in gundem["haberler"]:
        if h.get("yorumlanir"):
            h["yol"] = haber_yolu(h)

    # ARSIV + VARLIK INDEKSI BURADA, HER RENDER'DAN ONCE.
    #
    # Ikisi de asagida, haber dongusunun hemen oncesindeydi. Ama onem
    # puani varlik SAYISINA bakiyor ve puan `ortak` sozlugune giren son
    # dakika seridini belirliyor; `ortak` ise analiz sayfalarindan da
    # once kuruluyor. Indeks asagida kalsaydi serit puansiz, ana sayfa
    # puanli olur ve ikisi ayni haberi farkli siralardi.
    arsiv = arsiv_haberleri({h["adres"] for h in gundem["haberler"]},
                            foto_defteri())
    if arsiv:
        print(f"arsiv: {len(arsiv)} eski haber sayfasi yeniden uretiliyor")
    uretilecek = gundem["haberler"] + arsiv
    varlik_haritasi = varlik_indeksle(uretilecek)

    # ONEM PUANI. Her habere katman ve puan yaziliyor; puan EKRANA
    # BASILMIYOR (bkz. onem.py bas yorumu), yalnizca sirali ve katmani
    # belirliyor.
    #
    # ARSIV DE PUANLANIYOR. Gerekcesi olculdu: `gundem.json` son besleme
    # penceresini tasiyor (40 haber) ve bunlarin yalnizca 9'unun sayfasi
    # var -- geri kalan basliklarin GOVDESI YOK (kaynak yalnizca baslik
    # veriyor), o yuzden sayfa uretilmiyor ve uretilmemeli. Sadece bu
    # pencereden secilseydi "one cikan gelismeler" bolumu dort kalemde
    # kalirdi. Arsivdeki yayimlanmis haberler gercek sayfalar; onlari
    # katmaktan kacinmak icin bir sebep yok.
    onem_puanla(uretilecek, varlik_haritasi)
    an_yaz(uretilecek)

    # AI YORUMU HER HABERE YAZILIYOR, yalnizca haber sayfasina degil.
    #
    # Once yalnizca `haber.html` render'ina parametre olarak geciyordu.
    # Ama kartlar da yorumu gosteriyor artik (kartta analiz yok, yorum
    # var) ve gundem sayfasi ayri bir sablonda. Alani habere yazmak,
    # ayni degeri iki ayri yoldan gecirmekten guvenli.
    # TAKVIM BIR KEZ HESAPLANIYOR.
    #
    # Hem ana sayfa bolumu hem her haberin brifingi ayni listeyi
    # kullaniyor. Her haberde yeniden cagirmak, aga 200 kez cikmak ve
    # konsensus kaynagini hiz sinirina sokmak demekti.
    takvim_ondbellek = takvim_kutulari()

    ai_yorumlari = ai_yorum_oku()
    if ai_yorumlari:
        print(f"ai: {len(ai_yorumlari)} haberde yorum var")
    for h in uretilecek:
        m = ai_yorumlari.get(h.get("adres", ""), "")
        h["ai_yorum"] = m
        h["ai_yorum_kart"] = kart_yorumu(m) if m else ""
        h["ozet_kart"] = kart_yorumu(h.get("ozet", ""))

    # SON DAKIKA ARTIK BIR SECIM.
    #
    # Once "en yeni 12 haber" idi ve sonuc her haberin son dakika gibi
    # gorunmesiydi -- Goldman raporu ile TCMB faiz karari ayni seritte,
    # ayni renkte. Etiket her seye yapisinca hicbir seye yapismaz.
    # Artik yalnizca KRITIK katman giriyor; hicbiri yoksa serit
    # BASILMIYOR (bkz. temel.html).
    son_dakika = [
        h for h in gundem.get("haberler", [])
        if h.get("yorumlanir") and h.get("katman") == "kritik"
    ][:6]

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
        # Adres atamasi, arsiv ve varlik indeksi YUKARIDA yapildi --
        # `ortak` sozlugu (son dakika seridi) onlara bagli ve o sozluk
        # analiz sayfalarindan da once kuruluyor.

        # AI yorumlari DEPODAN okunuyor, burada uretilmiyor.
        # Site kurulumu modele bagimli olmamali: kota bittiginde ya da
        # uc coktugunde site yine kurulmali, yalnizca o bolum basilmasin.
        # VARLIK SAYFALARI URETILIYOR AMA DIZIN YOK.
        #
        # Ikisi ayri karar. "Konular" diye gezilebilir bir bolum
        # istenmiyordu -- site haber ve cozumleme yayimliyor, konu
        # dizini degil; o yuzden `/varlik/` dizini ve menu girisi YOK.
        #
        # Ama tek tek sayfalar gerekiyor: "Bundan sonra izlenecekler"
        # listesindeki kalemlerin tiklaninca gidecegi bir yer olmali
        # ("PPK karari" -> PPK gecmisi). Hedefsiz baglanti veremeyiz.
        #
        # Sonuc: sayfalar var, kapisi yok. Okur onlara yalnizca izleme
        # listesinden ulasiyor.
        for v_yol in varlik_sayfalari(ortam, yaz, ortak, dizin_yaz=False):
            yollar.append(v_yol)
        varlik_sayfasi_olan = {
            y.strip("/").split("/")[-1].upper().replace("-", "_")
            for y in yollar if y.startswith("/varlik/")}

        # Fotograf dagitimi TEK SEFERDE, butun haberler goruldukten
        # sonra. Dongu icinde tek tek secmek carpismayi engelleyemiyor.
        foto_atamasi = (foto_dagit(uretilecek, varlik_haritasi, foto_kayit)
                        if _foto is not None else {})

        # DAGITIM SAYFASI OLMAYAN OGELERE DE UYGULANIYOR.
        #
        # Atama yalnizca sayfa uretilen haberlere yaziliyordu; canli
        # akistaki sayfasiz satirlar `uret_gundem`in ilk (hash'e dayali)
        # secimini tasimaya devam ediyordu. Olculdu: akisin 24 gorselli
        # satirinda 16 farkli gorsel vardi ve ikisi DORDER kez
        # goruluyordu -- hepsi tek ekranda.
        for h in uretilecek:
            f = foto_atamasi.get(h.get("adres", ""))
            if f is not None and not h.get("yorumlanir"):
                h["foto"], h["foto_atif"] = f.dosya, f.kisa_atif

        for h in uretilecek:
            if not h.get("yorumlanir"):
                continue
            h_yol = h["yol"]
            h_varliklar = varlik_haritasi.get(h["adres"], {}).get("varliklar")
            # FOTOGRAF VARLIGA GORE YENIDEN SECILIYOR.
            #
            # Ilk secim `uret_gundem`de yapiliyor ve orada yalnizca KONU
            # biliniyor -- varlik indeksi henuz calismamis. Sonuc: Hurmuz
            # Bogazi haberi ile Kuzey Kore fuzesi ayni "diplomacy
            # meeting" fotografini aliyordu; ikisi de jeopolitik ama ayni
            # gelisme degil.
            #
            # Burada varliklar belli. Varlik havuzu bos ya da tanimsizsa
            # KONU havuzuna dusuyor -- eksik eslesme, yanlis eslesmeden
            # iyidir.
            yeni_f = foto_atamasi.get(h.get("adres", ""))
            if yeni_f is not None:
                h["foto"] = yeni_f.dosya
                h["foto_atif"] = yeni_f.kisa_atif
            # DOSYASI OLMAYAN GORSEL BASILMAZ.
            #
            # `gundem.json` fotografi haberin ILK secimiyle tasiyor. O
            # dosya sonradan silinmis olabilir -- editoryal suzgec
            # siklastiginda 49 gorsel havuzdan cikarildi ve iki haber
            # hala silinmis dosyaya isaret ediyordu. Sonuc: sayfada
            # KIRIK GORSEL, hicbir hata mesaji yok.
            if h.get("foto"):
                if not (STATIK / h["foto"].split("/statik/", 1)[-1]).exists():
                    h["foto"] = h["foto_atif"] = ""

            # `dosya.kur` BIR KEZ: hem sablon hem kaynaklar ayni
            # nesneyi kullaniyor.
            h_dosya = (_dosya.kur(
                h["konu"], h.get("bolge", ""), h.get("tarih", ""),
                varliklar=([v["kod"] for v in h_varliklar]
                           if h_varliklar is not None else None),
                baslik=h.get("baslik_kaynak") or h.get("baslik", ""),
                # Ozeti olmayan haberde acilis cumlesi uretilsin:
                # aksi halde sayfada hicbir metin kalmiyor.
                ozetsiz=not (h.get("ozet") or "").strip())
                if _dosya else None)
            h_brifing = gosterge_brifingi(h, h_varliklar, takvim_ondbellek)

            # OKURUN DOGRULAYAMADIGI SAYI BASILMAZ.
            #
            # Yorumlar DONMUS, dosyalar CANLI. Yorum yazildiginda
            # sayfada duran bir bulgu, sonraki insada dosyadan cikmis
            # olabilir -- dosya her seferinde yeniden hesaplaniyor
            # (dogru davranis). Sonuc: yorum sayfada HICBIR YERDE
            # olmayan bir sayiyi aniyor ve okur onu kontrol edemiyor.
            #
            # Olculdu: 69 sayfanin 12'sinde boyle bir sayi vardi --
            # "issizlik orani %7,4", "onceki %32,11", "cari acik
            # 1.459 mn $". Hicbiri o sayfada basilmiyordu.
            #
            # Prompt'un 7. maddesi tam olarak bunu istiyor: bir veri
            # birden fazla yerde kullaniliyorsa hepsinde AYNI olmali.
            # Buradaki kural daha da temel: sayfada olmayan bir veri
            # yorumda da olmamali.
            if h.get("ai_yorum") and not _yorum_dogrulanabilir(
                    h["ai_yorum"], h, h_dosya):
                h["ai_yorum"] = h["ai_yorum_kart"] = ""
                _dogrulanamayan.append(h.get("baslik", "")[:60])

            # Seyir ONCE kuruluyor: "Bunu da okuyun" bolumu cizelgede
            # zaten gecen basliklari tekrar etmesin.
            h_seyir = dosya_cizelgesi(
                h, uretilecek,
                varlik_haritasi.get(h["adres"], {}).get("ilgili", []),
                gundem.get("guncelleme", ""), varlik_haritasi)
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
                        # Turkiye panelindeki seriler kutuda TEKRARLANMAZ:
                        # ikisi ayni dort rakami gosteriyordu.
                        haric=_panel_kodlari(),
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
                    dosya=h_dosya,
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
                    # HABERIN KENDI ALANINDAN, sozlukten DEGIL.
                    #
                    # Burasi `ai_yorumlari.get(...)` idi, yani depodan
                    # dogrudan okuyordu. Sonuc: `h["ai_yorum"]` uzerinde
                    # yapilan her duzeltme sayfaya HIC yansimiyordu --
                    # dogrulanamayan yorumlari dusuren kontrol calisti,
                    # "10 yorum basilmadi" diye yazdi ve sayfalarda
                    # hicbir sey degismedi. Sessiz etkisizlik.
                    ai_yorum=h.get("ai_yorum", ""),
                    etki=etki_alanlari(h, h_varliklar),
                    # Haberin KENDI yapisal baglari -- konu tablosundan
                    # degil, metinden cikan varliklardan.
                    duzenek=duzenek(h_varliklar),
                    # KAYNAKLAR: sayfanin O AN kullandigi kaynaklar,
                    # sabit bir liste degil.
                    kaynaklar=kaynaklar(h, h_dosya, h_brifing),
                    # Bekleyis haberinde "ilk bakis" yerine gosterge
                    # brifingi: bu veri nedir, neyi etkiler, beklenti ne.
                    brifing=h_brifing,
                    # Makale sonu: okur bosluga dusmesin.
                    ayni_konu=ayni_konu_haberleri(
                        h, uretilecek, _seyir_adresleri(h_seyir)),
                    ilgili_analiz=ilgili_analizler(
                        h, listelenen, _seyir_basliklari(h_seyir)),
                    # DOSYA: haberin ait oldugu gelisme zincirinin seyri.
                    # Haber tek seferlik bir icerik degil, bir zincirin
                    # halkasi -- cizelge o halkanin yerini gosteriyor.
                    dosya_seyri=h_seyir,
                    # Izleme kalemleri tiklanabilir: hedef varlik arsivi
                    izleme=izleme_baglantilari(
                        (_dosya.IZLENECEKLER.get(h.get("konu", ""))
                         if _dosya else ()), varlik_sayfasi_olan),
                ),
            )
            yollar.append(h_yol)


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
            # Katman 2 -- SAYFASI OLAN haberler arasindan, puana gore
            # secilmis, tekrari elenmis. Arsiv de dahil (bkz. yukarida).
            one_cikanlar=one_cikan_haberler(
                [h for h in uretilecek if h.get("yol")],
                datetime.now().strftime("%Y-%m-%d")),
            # Katman 1 -- ham akis, en yeni ustte, ELEME YOK
            akis=canli_akis(gundem.get("haberler", [])),
            # Piyasa ozetinin yerini alan AI yorum akisi
            ai_akis=ai_akisi(uretilecek),
            # Yaklasan veri aciklamalari + beklenti kutulari
            takvim=takvim_ondbellek,
        ),
    )

    # TOPLULUK. Ust menude baglantisi var, yani sayfa MUTLAKA
    # uretilmeli -- menude olup sayfasi olmayan bir baslik 404 demek.
    yaz(
        "/topluluk/index.html",
        ortam.get_template("topluluk.html").render(**ortak, yol="/topluluk/"),
    )
    yollar.append("/topluluk/")


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
    css_kucult(CIKTI / "statik" / "stil.css")

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
    if _dogrulanamayan:
        print(f"ai: {len(_dogrulanamayan)} yorum sayfada karsiligi olmayan "
              f"sayi tasidigi icin BASILMADI")
        for x in _dogrulanamayan[:3]:
            print(f"    {x}")
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


def onem_dokumu() -> int:
    """Onem puanlarini ekrana doker. Site KURULMAZ.

    NEDEN VAR
    ---------
    Puan sayfada gorunmuyor -- gorunmemesi de dogru (bkz. onem.py bas
    yorumu). Ama gorunmeyen bir siralamayi kalibre etmek imkansiz: hangi
    haberin neden one ciktigini, hangisinin neden elendigini gormeden
    esikler tahmine dayanir.

    Bu dokum o yuzden var ve YALNIZCA terminale yaziliyor -- siteye
    hicbir sey eklemiyor.
    """
    gundem = gundem_yukle()
    foto_kayit = foto_defteri()
    gundem["haberler"] = [tazele(h, foto_kayit)
                          for h in gundem.get("haberler", [])]
    for h in gundem["haberler"]:
        if h.get("yorumlanir"):
            h["yol"] = haber_yolu(h)

    arsiv = arsiv_haberleri({h["adres"] for h in gundem["haberler"]},
                            foto_kayit)
    uretilecek = gundem["haberler"] + arsiv
    onem_puanla(uretilecek, varlik_indeksle(uretilecek))
    an_yaz(uretilecek)

    bugun = datetime.now().strftime("%Y-%m-%d")
    sayfali = [h for h in uretilecek if h.get("yol")]
    secilen = one_cikan_haberler(sayfali, bugun)
    secilen_adres = {h["adres"] for h in secilen}

    def satir(h: dict, isaret: str = " ") -> str:
        b = (h.get("baslik") or "")[:56]
        return (f"{isaret} {h.get('onem', 0):>3} {h.get('katman_adi', ''):<7}"
                f" {(h.get('kurum') or '')[:14]:<14} {b}")

    print(f"\n{'=' * 78}\nKATMAN 2 -- one cikan gelismeler ({len(secilen)} kalem)")
    print(f"{'=' * 78}")
    for h in secilen:
        print(satir(h, "*"))

    # Esigi gectigi halde SECILMEYENLER: tekrar/kume elemesine takilanlar.
    # Kalibrasyonda en cok bakilacak liste bu -- yanlis eleme buradan
    # gorunur.
    esik = _onem.NORMAL if _onem else 40
    elenen = [h for h in sayfali
              if h.get("onem", 0) >= esik
              and h["adres"] not in secilen_adres
              and gun_farki(h.get("tarih", ""), bugun) < ONE_CIKAN_PENCERE]
    print(f"\nESIGI GECTI AMA ELENDI ({len(elenen)}) -- tekrar/kume elemesi")
    print("-" * 78)
    for h in sorted(elenen, key=lambda x: -x.get("onem", 0)):
        print(satir(h))

    print(f"\nCANLI AKIS ({AKIS_SAYISI} kalem, eleme yok)")
    print("-" * 78)
    for h in canli_akis(gundem["haberler"]):
        nerede = "sayfa" if h.get("yol") else "kaynak"
        print(f"  {h.get('onem', 0):>3} {nerede:<7} {(h.get('baslik') or '')[:58]}")

    print(f"\nPUAN BILESENLERI -- en yuksek 8")
    print("-" * 78)
    for h in sorted(sayfali, key=lambda x: -x.get("onem", 0))[:10]:
        bil = "  ".join(f"{k}={v}" for k, v in h.get("onem_bilesen", []) if v)
        ham = sum(v for _, v in h.get("onem_bilesen", []))
        taban = f"  [editoryal taban: {ham} -> 85]" if h.get("onem_taban") else ""
        print(f"  {h.get('onem', 0):>3}  {(h.get('baslik') or '')[:46]}")
        print(f"       {bil}{taban}")
    return 0


if __name__ == "__main__":
    ayristirici = argparse.ArgumentParser(description="Statik site ureteci")
    ayristirici.add_argument("--sun", action="store_true", help="uretimden sonra yerel sunucu ac")
    ayristirici.add_argument("--port", type=int, default=8000)
    ayristirici.add_argument("--onem", action="store_true",
                             help="onem puanlarini doker, site kurmaz")
    args = ayristirici.parse_args()

    if args.onem:
        sys.exit(onem_dokumu())

    kod = insa()
    if kod == 0 and args.sun:
        sun(args.port)
    sys.exit(kod)
