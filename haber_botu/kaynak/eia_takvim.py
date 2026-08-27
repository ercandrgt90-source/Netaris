"""EIA spot fiyat serilerinin YAYIN TAKVIMI -- ucretsiz, anahtarsiz.

    dnav sayfasi -> "Next Release Date" -> serit baloncugu

NEDEN VAR
---------
Brent ve WTI seritte bes is gunu geride gorunuyor ve bu BIZIM
gecikmemiz saniliyor. Degil: EIA bu gunluk spot serileri HAFTALIK
yayimliyor. Kendi sayfasi soyluyor --

    Release Date: 8/5/2026 · Next Release Date: 8/12/2026

Ikisi de carsamba.

UCRETSIZ DAHA TAZE KAYNAK ARANDI, YOK
-------------------------------------
Olculdu:
  EIA API v2          403, anahtar istiyor -- ve ANAHTAR DA COZMEZ,
                      cunku ayni haftalik ritmi tasiyor
  EIA dnav dosyalari  anahtarsiz iniyor ama eski Excel (BIFF) bicimi
  OPEC sepeti (ORB)   403; ana sayfa aciliyor ama fiyat JavaScript ile
                      geliyor ve veri ucu ayrica engelli
  Stooq               dogrulama duvari
  Kanada MB valet     emtia serisi ucta yok
  Dunya Bankasi       calisiyor ama AYLIK
  Alpha Vantage       ucretsiz anahtar veriyor AMA kendi belgesinde
                      "retrieved from FRED" yaziyor -- yani zaten
                      kullandigimiz serinin ta kendisi

Gunluk ham petrol fiyati vadeli piyasadan gelir; ucretsiz, anahtarsiz
ve kullanim sartlarina uygun bir ucu yok.

O HALDE YAPILACAK SEY
---------------------
Sayiyi taze GOSTERMEK degil, ne zaman tazelenecegini SOYLEMEK. Okur
"bu veri eski" yerine "bu veri carsamba gunu yenilenecek" okuyor --
ikincisi dogru ve kullanisli.
"""

from __future__ import annotations

import datetime
import re

import httpx

# Kimlik TEK yerden gelir (kaynak/kimlik.py); elle kopyalanan
# adres 20 dosyada surukledi ve ucu bize ait olmayan bir alan
# adina isaret ediyordu.
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan
BASLIKLAR = {"User-Agent": ajan("enerji takvimi")}
ZAMAN_ASIMI = 25.0

#: FRED seri kodu -> EIA sayfa kodu.
SAYFALAR = {
    "DCOILBRENTEU": "RBRTED",
    "DCOILWTICO": "RWTCD",
}

_UC = "https://www.eia.gov/dnav/pet/hist/{}.htm"
_SONRAKI = re.compile(r"Next Release Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})")

_AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _tr_tarih(ay: int, gun: int, bugun: datetime.date | None = None) -> str:
    """Yayin tarihini okurun kullandigi dille yazar.

    "sonraki 12 Ağustos" ifadesi 12 Ağustos GUNU okundugunda tuhaf
    kaciyor -- okur takvime bakip bugunun 12'si oldugunu kendisi
    cikarmak zorunda kaliyor. Yayin GUNU, tam da notun en cok ise
    yaradigi gun; o gun "bugün" demek gerekiyor.

    Yalnizca bugun ve yarin ozel yaziliyor; otesi tarihle daha net.
    """
    if not 1 <= ay <= 12:
        return ""
    bugun = bugun or datetime.date.today()
    try:
        d = datetime.date(bugun.year, ay, gun)
    except ValueError:
        return ""
    fark = (d - bugun).days
    # Yil sinirinda ay/gun ayni yila dusmeyebilir; yalnizca yakin
    # gunlerde ozel sozcuk kullaniliyor, uzakta tarih zaten dogru.
    if fark == 0:
        return "bugün"
    if fark == 1:
        return "yarın"
    return f"{gun} {_AYLAR[ay - 1]}"


def sonraki_yayin(seri: str, istemci=None) -> str:
    """Serinin bir sonraki yayin tarihi ("12 Ağustos"). Yoksa BOS.

    BOS DONMESI SORUN DEGIL: baloncukta yalnizca ritim yazar, tarih
    yazmaz. Erisilemedi diye serit bozulmuyor.
    """
    sayfa = SAYFALAR.get(seri)
    if not sayfa:
        return ""
    try:
        al = (istemci or httpx).get
        r = al(_UC.format(sayfa), headers=BASLIKLAR, timeout=ZAMAN_ASIMI,
               follow_redirects=True)
        r.raise_for_status()
        m = _SONRAKI.search(r.text)
    except (httpx.HTTPError, ValueError):
        return ""
    if not m:
        return ""
    ay, gun, _yil = (int(x) for x in m.groups())
    return _tr_tarih(ay, gun)


def hepsi(istemci=None) -> dict[str, str]:
    """Butun EIA serileri icin sonraki yayin tarihi."""
    return {k: sonraki_yayin(k, istemci) for k in SAYFALAR}
