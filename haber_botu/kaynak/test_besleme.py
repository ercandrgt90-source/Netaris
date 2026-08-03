"""besleme.py testleri -- tarih cozumu, konu cikarimi, oge ayristirma.

Buradaki uc islev de HATA FIRLATMAZ. Yanlis calistiklarinda sonuc sessizce
bozulur ve ancak siteye bakinca fark edilir:

  * Tarih cozulemezse duyuru "tarihsiz" sayilip listenin dibine duser --
    TCMB'nin bugunku karari Fed'in bes gun onceki duyurusunun altinda kalir.
  * Konu bulunamazsa varsayilana duser ve habere alakasiz fotograf secilir.
  * Diakritikli yazilmis bir isaret HICBIR ZAMAN eslesmez.

Calistirma:  python kaynak/test_besleme.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import besleme  # noqa: E402

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


print("\nTarih -- TCMB Turkce ay adi yaziyor, strptime cozemez")
esit(besleme._tarih_coz("30 Tem 2026 14:00:00"), "2026-07-30", "kisaltilmis ay")
esit(besleme._tarih_coz("6 Tem 2026 18:00:00"), "2026-07-06", "tek haneli gun")
esit(besleme._tarih_coz("1 Şub 2026 09:00:00"), "2026-02-01", "Ş harfi -- katlanmali")
esit(besleme._tarih_coz("3 Ağu 2026 10:00:00"), "2026-08-03", "Ğ harfi")
esit(besleme._tarih_coz("15 Ağustos 2026"), "2026-08-15", "tam ay adi da calisir")
esit(besleme._tarih_coz("11 Ara 2025 14:00:00"), "2025-12-11", "Aralik")
esit(besleme._tarih_coz("9 Eyl 2026"), "2026-09-09", "Eylul -- Ekim ile karismaz")
esit(besleme._tarih_coz("9 Eki 2026"), "2026-10-09", "Ekim -- Eylul ile karismaz")
esit(besleme._tarih_coz("5 Mar 2026"), "2026-03-05", "Mart -- Mayis ile karismaz")
esit(besleme._tarih_coz("5 May 2026"), "2026-05-05", "Mayis -- Mart ile karismaz")

print("\nTarih -- cozulemeyen BOS doner, bugun YAZILMAZ")
esit(besleme._tarih_coz("31 Nis 2026"), "", "olmayan gun (Nisan 30 cekiyor)")
esit(besleme._tarih_coz("30 Zzz 2026"), "", "olmayan ay")
esit(besleme._tarih_coz(""), "", "bos giris")
esit(besleme._tarih_coz("yakinda"), "", "tarih olmayan metin")

print("\nTarih -- yabanci bicimler bozulmadi")
esit(besleme._tarih_coz("Thu, 30 Jul 2026 09:53:38 -0400"), "2026-07-30", "RFC 822")
esit(besleme._tarih_coz("Fri, 31 Jul 2026  09:00:00 EST"), "2026-07-31", "EIA bicimi")
esit(besleme._tarih_coz("2026-07-30T10:00:00Z"), "2026-07-30", "ISO")

print("\nKatlama -- once translate, SONRA lower")
esit(besleme._katla("İSTANBUL"), "istanbul", "buyuk I noktali")
esit(besleme._katla("TÜFE"), "tufe", "U umlaut")
esit(besleme._katla("Ağustos"), "agustos", "yumusak g")
esit(besleme._katla("IŞIK"), "isik", "noktasiz i ve S cedilla")

print("\nKonu -- Turkce basliklar")
esit(besleme.konu_bul("Para Politikası Kurulu Toplantı Özeti (2026-32)", "Düzenleme"),
     "Para politikası", "PPK ozeti")
esit(besleme.konu_bul("Faiz Oranlarına İlişkin Basın Duyurusu", "Düzenleme"),
     "Para politikası", "faiz karari")
esit(besleme.konu_bul("Aylık Fiyat Gelişmeleri (Haziran 2026)", "Düzenleme"),
     "Enflasyon", "fiyat gelismeleri")
esit(besleme.konu_bul("TÜFE Aylık Değişim", "Düzenleme"),
     "Enflasyon", "TUFE -- diakritikli yazilmis")
esit(besleme.konu_bul("Ödemeler Dengesi İstatistikleri", "Düzenleme"),
     "Bankacılık", "odemeler dengesi")
esit(besleme.konu_bul("Elektrik Üretiminde Doğal Gaz Payı", "Düzenleme"),
     "Enerji", "dogal gaz")

print("\nKonu -- Ingilizce basliklar bozulmadi")
esit(besleme.konu_bul("FOMC statement", "Düzenleme"), "Para politikası", "FOMC")
esit(besleme.konu_bul("China's crude oil imports fell", "Düzenleme"), "Enerji", "crude oil")
esit(besleme.konu_bul("SEC charges firm with fraud", "Düzenleme"),
     "Piyasa düzenlemesi", "fraud")
esit(besleme.konu_bul("Hava durumu raporu", "Düzenleme"),
     "Düzenleme", "eslesme yoksa varsayilan")

print("\nKonu -- her varsayilan foto.KONU_ARAMA'da olmali")
import foto  # noqa: E402
for b in besleme.BESLEMELER:
    esit(b[4] in foto.KONU_ARAMA, True, f"{b[0]} varsayilani '{b[4]}' fotografli")
for konu, _ in besleme.KONU_ISARETLERI:
    esit(konu in foto.KONU_ARAMA, True, f"konu '{konu}' fotografli")

print("\nAtom ayristirma -- TCMB bicimi")
_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title></title>
<updated>22 Tem 2024 17:13:31</updated><entry>
<title type="text"><![CDATA[Para Politikası Kurulu Toplantı Özeti (2026-32)]]></title>
<link rel="alternate" type="text/html" href="http://www.tcmb.gov.tr/duy2026-32"></link>
<published>30 Tem 2026 14:00:00</published>
<updated>30 Tem 2026 14:00:59</updated>
<summary type="html"> </summary>
</entry></feed>"""
_o = besleme._ogeler(_ATOM)
esit(len(_o), 1, "tek entry okundu")
esit(_o[0]["baslik"], "Para Politikası Kurulu Toplantı Özeti (2026-32)", "CDATA acildi")
esit(_o[0]["adres"], "http://www.tcmb.gov.tr/duy2026-32", "Atom link href")
esit(_o[0]["tarih"], "2026-07-30", "Turkce tarih cozuldu")

print("\nBesleme tanimlari -- alan sayisi ve tekillik")
esit(all(len(b) == 6 for b in besleme.BESLEMELER), True, "hepsi 6 alanli")
_kodlar = [b[0] for b in besleme.BESLEMELER]
esit(len(_kodlar), len(set(_kodlar)), "kodlar tekil")
_adresler = [b[3] for b in besleme.BESLEMELER]
esit(len(_adresler), len(set(_adresler)), "adresler tekil")
esit(all(b[5] in ("tr", "en") for b in besleme.BESLEMELER), True, "dil tr/en")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
