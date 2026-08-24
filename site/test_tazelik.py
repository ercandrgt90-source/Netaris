"""Tazelik kontrolu: "site donmus mu" sorusunu GERCEKTEN olcuyor mu?

BU DOSYA NEDEN VAR
------------------
Kontrolun kendisi bir alarm ve alarmlarin iki bozulma bicimi var:
calmamak ve bosuna calmak. Ikisi de burada olculuyor.

Ozellikle `strptime` KULLANILMIYOR: RSS tarihleri Ingilizce ay adi
yaziyor ve `%b` sistemin diline bagli. Turkce yapilandirilmis bir
makinede cozumleme patlar, en yeni tarih None doner ve kontrol
sessizce "DOGRULANAMADI" deyip HER ZAMAN 0 dondurur -- yani alarm
kalici olarak susar. Ayni tuzak `besleme.py` icinde iki kez yasandi.
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import tazelik  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


print("RFC 822 tarihi cozuluyor  (sistem dilinden BAGIMSIZ)")

esit(tazelik.tarih_coz("Mon, 24 Aug 2026 00:00:00 +0000"),
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
     "tam RFC 822 tarihi")
esit(tazelik.tarih_coz("Tue, 3 Feb 2026 14:30:00 GMT"),
     datetime(2026, 2, 3, 14, 30, tzinfo=timezone.utc),
     "tek haneli gun ve saat")
esit(tazelik.tarih_coz("24 Aug 2026"),
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
     "gun adi olmadan da cozuluyor")
esit(tazelik.tarih_coz("Mon, 24 August 2026 00:00:00 +0000"),
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
     "tam ay adi da cozuluyor")

esit(tazelik.tarih_coz("Mon, 31 Feb 2026 00:00:00 +0000"), None,
     "olmayan gun None doner")
esit(tazelik.tarih_coz("Mon, 24 Zzz 2026"), None, "olmayan ay None doner")
esit(tazelik.tarih_coz(""), None, "bos giris None doner")
esit(tazelik.tarih_coz("yakinda"), None, "tarihsiz metin None doner")


print("\nBeslemedeki EN YENI tarih aliniyor")

_xml = """<rss><channel>
  <item><pubDate>Sat, 22 Aug 2026 00:00:00 +0000</pubDate></item>
  <item><pubDate>Mon, 24 Aug 2026 00:00:00 +0000</pubDate></item>
  <item><pubDate>Sun, 23 Aug 2026 00:00:00 +0000</pubDate></item>
</channel></rss>"""

# SIRAYLA ILKINI ALMAK YETMEZ: besleme sirasi bir gun degisirse
# kontrol sessizce yanlis olcerdi. Burada en yeni ORTADA duruyor.
esit(tazelik.en_yeni(_xml),
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
     "en yeni tarih siradan BAGIMSIZ bulunuyor")

esit(tazelik.en_yeni("<rss><channel></channel></rss>"), None,
     "tarihsiz beslemede None")
esit(tazelik.en_yeni(""), None, "bos beslemede None")

# Cozulemeyen tarihler ELENIYOR, digerleri kullanilmaya devam ediyor.
_karisik = ("<item><pubDate>bozuk</pubDate></item>"
            "<item><pubDate>Mon, 24 Aug 2026 00:00:00 +0000</pubDate></item>")
esit(tazelik.en_yeni(_karisik),
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
     "bozuk tarih digerlerini dusurmuyor")


print("\nYas hesabi ve esik")

_simdi = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)

esit(round(tazelik.yas_saat(
     datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc), _simdi)), 10,
     "ayni gun sabahi 10 saatlik")

# 2026-08-24'teki gercek donmada canli sitenin en yeni haberi 34
# saatlikti. Varsayilan esik onu yakalamali -- yakalamazsa bu kontrol
# tam olarak yasanan olayi kacirirdi.
_donma = tazelik.yas_saat(
    datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc), _simdi)
esit(round(_donma), 34, "bir gun onceki haber 34 saatlik")
esit(_donma > tazelik.VARSAYILAN_ESIK, True,
     "varsayilan esik GERCEK donmayi yakaliyor")

# Ayni gune ait haber, gunun en gec saatinde bile alarm URETMEMELI.
_gec = tazelik.yas_saat(
    datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 8, 24, 23, 59, tzinfo=timezone.utc))
esit(_gec <= tazelik.VARSAYILAN_ESIK, True,
     "ayni gun haberi gece yarisina kadar alarm uretmiyor")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
