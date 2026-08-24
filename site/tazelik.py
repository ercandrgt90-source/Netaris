"""CANLI sitede en yeni haber kac saatlik? -- "site donmus mu" sorusu.

BU DOSYA NEDEN VAR
------------------
Site IKI GUN ICINDE IKI KEZ sessizce dondu ve ikisini de once
KULLANICI fark etti:

  2026-08-23  `yayinla.py` cp1254 konsolunda `print` ederken
              cokuyordu; wrangler'a hic gelmiyordu. Canli site otuz
              bir commit geride kaldi.
  2026-08-24  `yorum_denetimi.py` on sekiz SAHTE ihlal bulup cikis 1
              donuyordu; `calistir.py` de `ok = False` yapip
              dagitimi hic calistirmiyordu. Canli sitede en yeni
              haber bir gun eskiydi, oysa depoda o gune ait altmis
              dokuz haber vardi.

Iki sebep tamamen farkli, SONUC AYNI: haber toplaniyor, depoya
yaziliyor, okura ulasmiyor. Ve her iki durumda da sistem "basarili"
diyordu -- CI kirmiziydi ama kimse kirmizi kayda bakmiyor.

NEDEN AYRI BIR OLCUM
--------------------
`dogrula.py` canli dosyalari yerelle karsilastiriyor ama YALNIZCA
basarili bir dagitimdan SONRA kosuyor. "Dagitim hic olmadi" durumunu
tanimi geregi goremez.

Bu kontrol sebebe hic bakmiyor: yalnizca okurun gordugu seye bakiyor.
Neden dondugu onemli degil, DONDUGU onemli.

OLCUT NEDEN RSS
---------------
`/rss.xml` makine okunur ve sitenin KENDI yayimladigi sey. Sayfa
duzeni degisince kirilan bir HTML deseni degil; okurun besleme
okuyucusunda gordugu tarihin aynisi.

Kullanim:
    python tazelik.py                 # varsayilan esik: 30 saat
    python tazelik.py --saat 12
    python tazelik.py --adres https://baska.example
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

import httpx

VARSAYILAN_ADRES = "https://netaris.net"

#: Esik neden 30 saat.
#:
#: `pubDate` GUN duzeyinde yaziliyor (saat 00:00). Yani ayni gune ait
#: bir haber, gunun sonunda bile en fazla 24 saatlik gorunur. Otuz
#: saat, "bugun hic haber yok" durumunu gunun ilk saatlerinde yanlis
#: alarma cevirmeden, "dun de yoktu" durumunu yakaliyor.
#:
#: Olculdu: 2026-08-24'teki donmada canli sitenin en yeni haberi 34
#: saatlikti -- bu esik onu yakalardi.
VARSAYILAN_ESIK = 30

_PUBDATE = re.compile(r"<pubDate>([^<]+)</pubDate>")

#: RSS tarihleri Ingilizce ay/gun adi yaziyor ve `%b`/`%a` sistemin
#: diline bagli -- Turkce yapilandirilmis bir makinede `strptime`
#: patliyor. Ayni tuzak `besleme.py` icinde iki kez yasandi; ay adi
#: burada da ELDE eslestiriliyor.
_AYLAR = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

_RFC822 = re.compile(
    r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})"
    r"(?:\s+(\d{2}):(\d{2}))?")


def tarih_coz(ham: str) -> datetime | None:
    """RFC 822 tarihini UTC `datetime`a cevirir. Cozemezse None."""
    e = _RFC822.search(ham or "")
    if not e:
        return None
    ay = _AYLAR.get(e.group(2).lower())
    if not ay:
        return None
    try:
        return datetime(int(e.group(3)), ay, int(e.group(1)),
                        int(e.group(4) or 0), int(e.group(5) or 0),
                        tzinfo=timezone.utc)
    except ValueError:          # 31 Nisan gibi olmayan gun
        return None


def en_yeni(xml: str) -> datetime | None:
    """Beslemedeki EN YENI tarih.

    Sirayla ilkini almak yetmez: besleme sirasi bir gun degisirse
    kontrol sessizce yanlis olcerdi. Hepsi okunup en buyugu aliniyor.
    """
    tarihler = [t for t in (tarih_coz(x) for x in _PUBDATE.findall(xml)) if t]
    return max(tarihler) if tarihler else None


def yas_saat(tarih: datetime, simdi: datetime | None = None) -> float:
    simdi = simdi or datetime.now(timezone.utc)
    return (simdi - tarih).total_seconds() / 3600


def main() -> int:
    a = argparse.ArgumentParser(description="Canli sitenin haber tazeligi")
    a.add_argument("--adres", default=VARSAYILAN_ADRES)
    a.add_argument("--saat", type=float, default=VARSAYILAN_ESIK,
                   help=f"bayat sayilma esigi (varsayilan {VARSAYILAN_ESIK})")
    s = a.parse_args()

    besleme = s.adres.rstrip("/") + "/rss.xml"
    try:
        y = httpx.get(besleme, timeout=25, follow_redirects=True,
                      headers={"cache-control": "no-cache"})
        y.raise_for_status()
    except Exception as e:      # ag katmani cok cesitli hata atiyor
        # AGA CIKAMAMAK BAYATLIK DEGIL. Bunu hata saymak, agsiz her
        # ortamda sahte alarm uretirdi -- ve sahte alarm, gercek
        # alarmin onunu kapatir.
        print(f"  DOGRULANAMADI: {besleme} okunamadi "
              f"({e.__class__.__name__})")
        return 0

    tarih = en_yeni(y.text)
    if tarih is None:
        print(f"  DOGRULANAMADI: {besleme} icinde tarih bulunamadi")
        return 0

    yas = yas_saat(tarih)
    gun = tarih.date().isoformat()
    if yas <= s.saat:
        print(f"  canli sitede en yeni haber {gun} "
              f"({yas:.0f} saatlik) -- taze")
        return 0

    print(f"  BAYAT: canli sitede en yeni haber {gun} "
          f"({yas:.0f} saatlik, esik {s.saat:.0f})")
    print("  Site guncellenmiyor. Haber toplansa bile okura")
    print("  ulasmiyor demektir. Bakilacak yerler sirasiyla:")
    print("    1. calistir.py ciktisinda 'Dağıtım' satiri var mi")
    print("    2. python haber_botu/yorum_denetimi.py   (kapi acik mi)")
    print("    3. python site/yayinla.py                (elle yayin)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
