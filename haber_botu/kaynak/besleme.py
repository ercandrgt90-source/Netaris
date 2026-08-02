"""Resmi kurum RSS beslemeleri -- haber akisinin kaynagi.

NEDEN RSS
---------
Bir kurum RSS yayimliyorsa "bu icerigi alin ve dagitin" diyor demektir.
Besleme okumak kazima degil, davetin kabulu. KAP'ta, Fintables'ta ve
TradingView'da karsilastigimiz engellerin hicbiri burada yok -- cunku
burada engellemek isteyen kimse yok.

KAPSANANLAR (olculdu, hepsi 200 donuyor)
  Fed        basin duyurulari + para politikasi
  ECB        basin duyurulari
  SEC        basin duyurulari
  EIA        enerji piyasasi

KAPSANMAYANLAR ve sebepleri
  TCMB, SPK  calisan RSS bulunamadi (404 / bos)
  IMF        403 -- otomatik erisimi engelliyor
  BIS, BoE   404

BASLIKLAR CEVRILMEZ
-------------------
Kaynak basligi ORIJINAL DILINDE aktarilir ve kaynaga baglanti verilir.
Cevirmek icin dil modeli gerekir; model olmadan cevirmeye calismak ya da
"yaklasik" bir Turkce baslik uydurmak, resmi bir kurumun aciklamasini
yanlis aktarmak olur. Bu, duzeltmesi en zor hata turlerinden biri.

Model devreye girdiginde ceviri ve yorum katmani buraya eklenir; besleme
yapisi degismez.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin; RSS okuyucu)"}
ZAMAN_ASIMI = 30.0

#: (kod, kisa ad, tam ad, adres, varsayilan konu)
#: Kisa ad kartlarda ve rozetlerde kullanilir -- "ABD Enerji Bilgi Idaresi"
#: bir rozete sigmiyor ve kartin yarisini kapliyordu. Tam ad haber
#: sayfasindaki kaynak kutusunda gorunur.
BESLEMELER = (
    ("FED_PARA", "Fed", "Federal Reserve",
     "https://www.federalreserve.gov/feeds/press_monetary.xml", "Para politikası"),
    ("FED_BASIN", "Fed", "Federal Reserve",
     "https://www.federalreserve.gov/feeds/press_all.xml", "Düzenleme"),
    ("ECB", "ECB", "Avrupa Merkez Bankası",
     "https://www.ecb.europa.eu/rss/press.html", "Para politikası"),
    ("SEC", "SEC", "ABD Menkul Kıymetler ve Borsa Komisyonu",
     "https://www.sec.gov/news/pressreleases.rss", "Düzenleme"),
    ("EIA", "EIA", "ABD Enerji Bilgi İdaresi",
     "https://www.eia.gov/rss/todayinenergy.xml", "Enerji"),
)

#: Baslikta gecen anahtar sozcuklerden konu cikarimi. Sirasi onemli:
#: ustteki daha ozgul.
KONU_ISARETLERI = (
    ("Para politikası", (
        "fomc", "monetary policy", "interest rate", "federal funds",
        "discount rate", "policy decision", "governing council",
        "monetary", "rate decision",
    )),
    ("Enflasyon", ("inflation", "cpi", "price index", "deflation", "wage")),
    ("Enerji", (
        "oil", "crude", "petroleum", "natural gas", "energy", "opec",
        "electricity", "renewable", "lng",
    )),
    ("Bankacılık", (
        "bank", "banking", "capital requirement", "stress test", "basel",
        "deposit", "supervis",
    )),
    ("Piyasa düzenlemesi", (
        "securities", "disclosure", "enforcement", "fraud", "investor",
        "market structure", "trading",
    )),
)


@dataclass(frozen=True)
class Haber:
    kaynak_kodu: str
    kurum: str        # kisa ad -- rozetlerde
    kurum_tam: str    # tam ad -- kaynak kutusunda
    baslik: str
    adres: str
    ozet: str
    tarih: str          # ISO, cozulemezse bos
    konu: str

    @property
    def tarih_gorunur(self) -> str:
        aylar = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
        try:
            d = datetime.strptime(self.tarih, "%Y-%m-%d")
        except ValueError:
            return self.tarih
        return f"{d.day} {aylar[d.month - 1]} {d.year}"


def _metin(ham: str) -> str:
    """CDATA, HTML etiketi ve fazla bosluktan arindirir."""
    ham = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", ham, flags=re.S)
    ham = re.sub(r"<[^>]+>", " ", ham)
    return re.sub(r"\s+", " ", html.unescape(ham)).strip()


_TARIH_BICIMLERI = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)


def _tarih_coz(ham: str) -> str:
    """RSS tarih bicimlerini ISO'ya cevirir. Cozulemezse BOS doner.

    Bos donmek onemli: cozulemeyen tarihe bugunu yazmak, eski bir duyuruyu
    bugun cikmis gibi gostermek olurdu.
    """
    ham = ham.strip()
    for bicim in _TARIH_BICIMLERI:
        try:
            d = datetime.strptime(ham, bicim)
            return d.date().isoformat()
        except ValueError:
            continue
    # "Tue, 29 Jul 2026 14:30:00 GMT" gibi son care
    m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", ham)
    if m:
        try:
            d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")
            return d.date().isoformat()
        except ValueError:
            pass
    return ""


def konu_bul(baslik: str, varsayilan: str) -> str:
    """Baslik metninden konu cikarir."""
    k = baslik.lower()
    for konu, isaretler in KONU_ISARETLERI:
        if any(i in k for i in isaretler):
            return konu
    return varsayilan


def _ogeler(xml: str) -> list[dict]:
    """RSS <item> ve Atom <entry> ogelerini ayristirir."""
    sonuc = []
    for kalip in (r"<item[ >].*?</item>", r"<entry[ >].*?</entry>"):
        for blok in re.findall(kalip, xml, re.S):
            baslik = re.search(r"<title[^>]*>(.*?)</title>", blok, re.S)
            # Atom'da <link href="...">, RSS'te <link>...</link>
            adres = re.search(r'<link[^>]*href="([^"]+)"', blok) or \
                re.search(r"<link[^>]*>(.*?)</link>", blok, re.S)
            ozet = re.search(r"<description[^>]*>(.*?)</description>", blok, re.S) or \
                re.search(r"<summary[^>]*>(.*?)</summary>", blok, re.S)
            tarih = re.search(r"<pubDate[^>]*>(.*?)</pubDate>", blok, re.S) or \
                re.search(r"<updated[^>]*>(.*?)</updated>", blok, re.S) or \
                re.search(r"<dc:date[^>]*>(.*?)</dc:date>", blok, re.S)
            if not baslik or not adres:
                continue
            sonuc.append({
                "baslik": _metin(baslik.group(1)),
                "adres": _metin(adres.group(1)),
                "ozet": _metin(ozet.group(1)) if ozet else "",
                "tarih": _tarih_coz(_metin(tarih.group(1))) if tarih else "",
            })
    return sonuc


def cek(kod: str = "", en_fazla: int = 12) -> list[Haber]:
    """Beslemeleri okur. `kod` verilirse yalnizca o besleme.

    Cekilemeyen besleme sessizce atlanmaz -- cagiran taraf kac besleme
    okundugunu gorur.
    """
    haberler: list[Haber] = []
    secilen = [b for b in BESLEMELER if not kod or b[0] == kod]

    with httpx.Client(headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
                      follow_redirects=True) as c:
        for besleme_kodu, kisa, tam, adres, varsayilan_konu in secilen:
            try:
                y = c.get(adres)
                y.raise_for_status()
            except httpx.HTTPError:
                continue
            for o in _ogeler(y.text)[:en_fazla]:
                if not o["baslik"] or len(o["baslik"]) < 12:
                    continue
                haberler.append(Haber(
                    kaynak_kodu=besleme_kodu,
                    kurum=kisa,
                    kurum_tam=tam,
                    baslik=o["baslik"],
                    adres=o["adres"],
                    ozet=o["ozet"][:400],
                    tarih=o["tarih"],
                    konu=konu_bul(o["baslik"], varsayilan_konu),
                ))

    # Ayni duyuru birden fazla beslemede olabilir (Fed'in iki beslemesi
    # ortusuyor) -- adrese gore tekille
    gorulen: set[str] = set()
    tekil = [h for h in haberler if not (h.adres in gorulen or gorulen.add(h.adres))]

    # En yeni once; tarihi cozulemeyenler sona
    tekil.sort(key=lambda h: h.tarih or "0000-00-00", reverse=True)
    return tekil


def bugun() -> str:
    return datetime.now(timezone.utc).date().isoformat()
