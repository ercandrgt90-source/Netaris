"""BIST sirketlerinin sektor siniflandirmasi.

    stockanalysis.com/quote/IST/{kod}/  ->  Sector + Industry

NE OLDUGU -- VE NE OLMADIGI
---------------------------
Bu siniflandirma GICS duzenine yakin, ONBIR sektorluk uluslararasi
bir semadir (Financials, Materials, Industrials...). Borsa
Istanbul'un KENDI sektor endeksleri (XBANK, XUSIN, XMANA...) BUNDAN
FARKLIDIR ve bu dosya onlari temsil etmiyor.

Ayrimi yazmak onemli: okur "BIST sektoru" ile "uluslararasi sektor"
ayni sey saniyorsa, iki farkli kaynaktan gelen iki farkli listeyi
karsilastirdiginda tutmadigini gorur ve haksiz yere veriye guvenini
kaybeder. Sayfada hangisi oldugu YAZILMALI.

TURKCE ADLAR BIZIM. Kaynak Ingilizce veriyor; ceviri tablosu asagida
ve BIZE ait. Yani "BIST soyle diyor" degil, "biz boyle adlandirdik"
-- ikisi ayri iddia ve karistirilmamali.

IZIN
----
stockanalysis.com robots.txt yalnizca `/e/` ve `/p/` yollarini
kapatiyor; `/quote/...` acik. Ayni gerekceyle Is Yatirim'in
`/_layouts/` ucu ELENDI (bkz. `bilanco_ag`).
"""

from __future__ import annotations

import re
import time

import httpx

UC = "https://stockanalysis.com/quote/IST/{kod}/"
# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {
    "User-Agent": ajan("sektor verisi"),
}
ZAMAN_ASIMI = 30.0

#: Istekler arasi bekleme. 794 sirket icin ~5 dakika; acele edecek
#: bir sey yok ve kaynak bizim degil.
ARA_SN = 0.35

#: Sayfada sektor yapisal olarak gomulu:
#:     infoTable:[{t:"Industry",v:"Steel",...},{t:"Sector",v:"Materials",...}]
#: Gorunur metinden okumak yerine BURADAN aliniyor -- gorunur metinde
#: menu ogeleri de "Industry" diye geciyor ve ilk denemem menuyu
#: yakalamisti ("Stock Lists").
_INFO = re.compile(r"infoTable:\[(.*?)\]", re.S)
_CIFT = re.compile(r'\{t:"([^"]+)",v:"([^"]*)"')

#: Ingilizce sektor -> Turkce ad. BIZIM cevirimiz.
SEKTOR_TR = {
    "Financials": "Finans",
    "Materials": "Temel malzeme",
    "Industrials": "Sanayi",
    "Energy": "Enerji",
    "Consumer Discretionary": "İsteğe bağlı tüketim",
    "Consumer Staples": "Temel tüketim",
    "Communication Services": "İletişim",
    "Health Care": "Sağlık",
    "Healthcare": "Sağlık",
    "Information Technology": "Bilişim",
    "Technology": "Bilişim",
    "Utilities": "Kamu hizmetleri",
    "Real Estate": "Gayrimenkul",
}

#: Cekilemeyen kodlar burada birikiyor -- sessiz basarisizlik yok.
OKUNAMAYAN: list[tuple[str, str]] = []


def _coz(metin: str) -> dict[str, str]:
    m = _INFO.search(metin)
    if not m:
        return {}
    return {t: v for t, v in _CIFT.findall(m.group(1))}


def cek(kod: str, istemci: httpx.Client | None = None) -> dict[str, str]:
    """Bir sirketin sektor bilgisi. Bulunamazsa BOS sozluk.

    Bos donmesi sorun degil ve UYDURMA yapilmiyor: sektoru bilinmeyen
    sirket "Diger" kovasina atilmiyor, sektorsuz kaliyor. Yanlis
    sektore koymak, sektor ortalamasini da bozar.
    """
    try:
        al = (istemci or httpx).get
        r = al(UC.format(kod=kod.upper()), headers=BASLIKLAR,
               timeout=ZAMAN_ASIMI, follow_redirects=True)
        r.raise_for_status()
    except (httpx.HTTPError, ValueError) as e:
        OKUNAMAYAN.append((kod, type(e).__name__))
        return {}

    d = _coz(r.text)
    sektor = d.get("Sector", "").strip()
    if not sektor:
        OKUNAMAYAN.append((kod, "sektor alani yok"))
        return {}
    return {
        "sektor": sektor,
        "sektor_tr": SEKTOR_TR.get(sektor, sektor),
        "alt_sektor": d.get("Industry", "").strip(),
    }


def hepsi(kodlar, ilerleme=None) -> dict[str, dict]:
    """Cok sayida sirket icin sektor. Tek istemciyle, araliklı."""
    cikti: dict[str, dict] = {}
    with httpx.Client() as c:
        for i, kod in enumerate(kodlar, 1):
            d = cek(kod, c)
            if d:
                cikti[kod] = d
            if ilerleme and i % 25 == 0:
                ilerleme(i, len(kodlar), len(cikti))
            time.sleep(ARA_SN)
    return cikti
