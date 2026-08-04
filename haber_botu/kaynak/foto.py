"""Konuya uygun GERCEK fotograf -- Openverse, ucretsiz ve anahtarsiz.

KAYNAK SECIMI
-------------
Openverse (WordPress.org'un acik gorsel arama servisi). Anahtar istemiyor,
`license_type=commercial` filtresiyle ticari kullanima acik sonuc veriyor
ve her sonucla birlikte hazir atif metni donuyor.

Denenip elenenler:
  Unsplash  401 -- anahtar zorunlu
  Pexels    anahtarsiz cevap verdi ama belgelenmis kullanim anahtarli;
            "calisiyor gorunuyor" uzerine sistem kurulmaz

LISANS -- atif zorunlu
----------------------
Sonuclarin cogu CC BY ya da CC BY-SA. Ikisi de ticari kullanima aciktir
ama **atif sarttir**: fotografcinin adi ve lisans, gorselin altinda
yazilir. Atif metnini Openverse hazir veriyor, biz saklayip basiyoruz.
Atifi dusuren bir kod degisikligi lisansi ihlal eder.

YEREL KOPYA
-----------
Gorseller indirilip kendi sunucumuzdan servis edilir. Sebepleri:
  * Uzaktan baglamak her sayfa acilisinda ucuncu partiye istek demek --
    ziyaretcinin IP'si Flickr'a gider, gizlilik sayfasinda anlatilacak
    yeni bir madde acilir
  * Kaynak gorsel silinirse ya da adres degisirse sayfada kirik gorsel kalir

KONU BASINA HAVUZ
-----------------
Her habere ayri fotograf indirmiyoruz. Konu basina kucuk bir havuz tutulup
haberin adresine gore belirlenimci sekilde secim yapiliyor: ayni haber her
zaman ayni fotografi alir, konu gorsel dili tutarli kalir, ve indirilen
dosya sayisi sinirli olur.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass

import httpx

UC = "https://api.openverse.org/v1/images/"
BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin; iletisim@netaris.com)"}
ZAMAN_ASIMI = 40.0

_KOK = pathlib.Path(__file__).parent.parent.parent
FOTO_KLASORU = _KOK / "site" / "statik" / "foto"
KAYIT_YOLU = pathlib.Path(__file__).parent / "foto_kayit.json"

#: Konu -> sirali arama terimleri. Ingilizce aranir; Openverse'te Turkce
#: etiketli gorsel sayisi cok az.
#:
#: DIKKAT: Openverse butun terimleri AND'liyor. "oil pump jack refinery"
#: SIFIR sonuc doner cunku dort etiketi birden tasiyan gorsel yok. Iki-uc
#: kelimelik sorgular calisiyor; havuz dolana kadar sirayla denenir.
#: Her konu icin en az iki terim olmali: ilki bos donerse sonrakine
#: geciliyor. Terimler `besleme.KONU_ISARETLERI` ile birebir ayni
#: anahtarlari kullanir -- test bunu dogruluyor, cunku eksik anahtar
#: fotografsiz habere yol aciyor ve hicbir hata firlatmiyor.
KONU_ARAMA = {
    "Enerji": ("oil pump jack", "oil refinery", "oil rig", "petroleum"),
    # Catisma gorseli ARANMIYOR: haber sayfasinin gorseli olayin siddetini
    # degil, konusunu isaret etmeli. Diplomasi, liman ve konteyner
    # gorselleri hem dogru hem izleyiciyi rahatsiz etmeyen secim.
    "Jeopolitik": ("diplomacy meeting", "united nations", "cargo ship port",
                   "shipping containers", "world map"),
    "Para politikası": ("federal reserve", "central bank", "bank building"),
    "Enflasyon": ("supermarket shopping", "grocery store", "market prices"),
    "Bankacılık": ("bank building", "financial district", "skyscraper finance"),
    "Piyasa düzenlemesi": ("stock exchange", "trading floor", "wall street"),
    "Düzenleme": ("courthouse", "government building", "capitol"),
    "Döviz": ("currency exchange", "banknotes", "money exchange"),
    "Altın ve emtia": ("gold bars", "gold bullion", "precious metal"),
    "Kripto varlıklar": ("bitcoin", "cryptocurrency", "blockchain"),
    "Borsa": ("stock exchange", "trading floor", "stock market"),
    "Dış ticaret": ("container port", "cargo ship", "shipping containers"),
    "İstihdam ve ücret": ("factory workers", "office workers", "job interview"),
    "Konut ve kira": ("apartment buildings", "housing construction", "real estate"),
    "Vergi ve kamu maliyesi": ("tax forms", "government building", "parliament"),
    "Tarım ve gıda": ("wheat field", "farm tractor", "harvest"),
    "Turizm": ("hotel resort", "airport terminal", "tourists"),
    "Şirket haberleri": ("office building", "corporate headquarters", "boardroom"),
}

#: Konu basina indirilecek fotograf sayisi
HAVUZ = 4

#: Ust boyut siniri. Pillow kurulu olmadigi icin yeniden boyutlandiramiyoruz;
#: 1,7 MB'lik bir kart gorseli sayfayi yavaslatir. Buyuk dosya atlanir.
EN_FAZLA_BAYT = 900_000

#: Kabul edilen lisanslar. ND (NoDerivatives) DISARIDA: kart icinde
#: `object-fit: cover` ile kirpiyoruz ve kirpmanin turev sayilip
#: sayilmadigi tartismalidir. Tartismali olani hic almamak basit.
KABUL_LISANSLAR = ("by", "by-sa", "cc0", "pdm")


@dataclass(frozen=True)
class Foto:
    dosya: str        # /statik/foto/... site ici yol
    atif: str         # "X" by Y is licensed under CC BY 2.0
    lisans: str
    kaynak: str       # orijinal sayfa adresi

    @property
    def kisa_atif(self) -> str:
        """Gorsel altinda basilacak kisa atif: 'Ad / CC BY 2.0'."""
        m = re.search(r'"[^"]*"\s+by\s+(.+?)\s+is licensed', self.atif)
        kim = m.group(1).strip() if m else "bilinmeyen"
        return f"{kim} · {self.lisans.upper()}"


class Kayit:
    """Indirilen gorsellerin defteri -- konu -> foto listesi."""

    def __init__(self, yol: pathlib.Path = KAYIT_YOLU):
        self.yol = yol
        self.veri: dict[str, list[dict]] = {}
        if yol.exists():
            try:
                self.veri = json.loads(yol.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.veri = {}

    def kaydet(self) -> None:
        self.yol.write_text(
            json.dumps(self.veri, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def havuz(self, konu: str) -> list[Foto]:
        return [Foto(**f) for f in self.veri.get(konu, [])]

    def sec(self, konu: str, tohum: str) -> Foto | None:
        """Konudan belirlenimci secim -- ayni haber her zaman ayni gorseli alir."""
        h = self.havuz(konu)
        if not h:
            return None
        i = int(hashlib.sha256(tohum.encode("utf-8")).hexdigest(), 16) % len(h)
        return h[i]


#: Turkce harfleri dosya adinda guvenli karsiliklarina cevirir.
#: `str.lower()` tek basina "Ü" harfini cozmez ve "d-zenleme" gibi bozuk
#: dosya adlari uretir -- bir kez oyle oldu.
_SLUG = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _dosya_adi(url: str, konu: str, sira: int) -> str:
    uzanti = pathlib.Path(url.split("?")[0]).suffix.lower()
    if uzanti not in (".jpg", ".jpeg", ".png", ".webp"):
        uzanti = ".jpg"
    kisa = re.sub(r"[^a-z0-9]+", "-", konu.translate(_SLUG).lower()).strip("-")
    return f"{kisa}-{sira}{uzanti}"


def _lisans_uygun(s: dict) -> bool:
    return (s.get("license") or "").lower() in KABUL_LISANSLAR


def doldur(konu: str, kayit: Kayit, adet: int = HAVUZ) -> int:
    """Konu icin fotograf havuzunu doldurur. Yeni indirilen sayisini doner.

    Havuz zaten doluysa AG ISTEGI YAPILMAZ -- her calistirmada yeniden
    indirmek hem bant genisligi hem de ucretsiz servise saygisizlik olur.

    Sorgular sirayla denenir: ilk sorgu az sonuc verirse ikinciye gecilir.
    """
    if len(kayit.havuz(konu)) >= adet:
        return 0

    sorgular = KONU_ARAMA.get(konu)
    if not sorgular:
        return 0

    FOTO_KLASORU.mkdir(parents=True, exist_ok=True)
    mevcut = kayit.veri.setdefault(konu, [])
    eklendi = 0
    gorulen = {f["kaynak"] for f in mevcut}

    for sorgu in sorgular:
        if len(mevcut) >= adet:
            break
        try:
            r = httpx.get(
                UC,
                params={
                    "q": sorgu,
                    "license_type": "commercial",
                    "page_size": adet * 4,   # bir kismi elenecek
                    "mature": "false",
                },
                headers=BASLIKLAR,
                timeout=ZAMAN_ASIMI,
            )
            r.raise_for_status()
            sonuclar = r.json().get("results", [])
        except (httpx.HTTPError, ValueError, KeyError):
            continue

        for s in sonuclar:
            if len(mevcut) >= adet:
                break
            url = s.get("url")
            atif = (s.get("attribution") or "").strip()
            sayfa = s.get("foreign_landing_url") or url
            # Atif metni olmayan gorsel ALINMAZ: CC BY atfi zorunlu kilar
            if not url or not atif or sayfa in gorulen:
                continue
            if not _lisans_uygun(s):
                continue

            try:
                g = httpx.get(url, headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                              follow_redirects=True)
                g.raise_for_status()
                if not g.headers.get("content-type", "").startswith("image/"):
                    continue
                if len(g.content) > EN_FAZLA_BAYT:
                    continue
            except httpx.HTTPError:
                continue

            ad = _dosya_adi(url, konu, len(mevcut) + 1)
            (FOTO_KLASORU / ad).write_bytes(g.content)
            gorulen.add(sayfa)
            mevcut.append({
                "dosya": f"/statik/foto/{ad}",
                "atif": atif,
                "lisans": (s.get("license") or "cc") +
                          (" " + str(s.get("license_version") or "")).rstrip(),
                "kaynak": sayfa,
            })
            eklendi += 1

    return eklendi


#: Gundemde o gun hic haberi olmasa bile havuzu DOLU tutulan konular.
#:
#: Sebep: analiz yazilari da bu havuzdan fotograf aliyor ve onlar gunun
#: haber akisindan bagimsiz. Bir kez oyle oldu -- gunun haberlerinde
#: sirket haberi yoktu, havuz bos kaldi ve TERA bilanco analizi
#: fotografsiz yayimlandi. Hicbir hata mesaji cikmadi.
TEMEL_KONULAR = (
    "Şirket haberleri", "Para politikası", "Enerji", "Enflasyon",
    "Altın ve emtia", "Kripto varlıklar", "Borsa",
)


def hazirla(konular: list[str]) -> Kayit:
    """Verilen konularin havuzlarini doldurup defteri doner.

    `TEMEL_KONULAR` her zaman listeye ekleniyor. `doldur` havuz zaten
    doluysa ag istegi yapmiyor, dolayisiyla bunun gunluk maliyeti yok.
    """
    kayit = Kayit()
    for konu in dict.fromkeys(list(konular) + list(TEMEL_KONULAR)):
        n = doldur(konu, kayit)
        if n:
            print(f"  {konu:<20} {n} yeni fotograf")
    kayit.kaydet()
    return kayit
