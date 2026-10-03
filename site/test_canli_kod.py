# -*- coding: utf-8 -*-
"""Canli fiyat kodlari: TEK KAYNAK `canli.js`, tuketen iki taraf.

BU DOSYA NEDEN VAR
------------------
Analiz sayfasindaki canli fiyat kutusu yalnizca belirli varliklar
icin basiliyor. O liste `site/statik/canli.js` icindeki
`KRAKEN_ADLARI` tablosunda duruyor ve `insa.py` onu OKUYARAK
sablona veriyor (`canli_kodlar`).

Listeyi sablona elle yazmak, ayni karari iki yerde tutmak olurdu --
bu depoda en pahaliya mal olan kusur sinifi. 2026-09-30/10-01'de
bedeli iki kez odendi: tema paletinde ayni jetona karar veren dort
blok, ve ceviri istemcisinde Python sozlesmesinden dort ayrim.

OLCULDU (2026-10-03): kutu kosulsuz basildiginda 147 sayfada
doluyor ama 292 "OLAY" ve 221 BIST kodu sayfasinda -- yani ~730
sayfada -- HIC dolmuyordu. Olu isaretleme hem DOM agirligi hem de
okuyan icin "bu neden burada?" sorusu.

EN KRITIK KURAL
---------------
`test_bist_kodu_sizmiyor`. BIST verisi Borsa Istanbul dagitim
lisansi gerektiriyor ve o veri bu siteye HIC girmiyor. Listeye bir
BIST kodu sizarsa analiz sayfasina lisansli fiyat dusme yolu acilir.
Koruma yapisal: liste kaynagi `canli.js` ve o dosya yalnizca Kraken
(kripto/emtia) cekiyor.
"""

import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

_JS = (_KOK / "statik" / "canli.js").read_text(encoding="utf-8")
_INSA = (_KOK / "insa.py").read_text(encoding="utf-8")
_SABLON = (_KOK / "sablonlar" / "analiz.html").read_text(encoding="utf-8")

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


def _js_kodlari():
    m = re.search(r"var KRAKEN_ADLARI = \[(.*?)\];", _JS, re.S)
    if not m:
        return []
    return sorted(set(re.findall(r'kod:\s*"([^"]+)"', m.group(1))))


# ------------------------------------------------------------------
def test_js_listesi_okunabiliyor():
    k = _js_kodlari()
    dogru("KRAKEN_ADLARI tablosu okunuyor", k)
    dogru("en az iki varlik var", len(k) >= 2)


def test_insa_listeyi_JS_TEN_okuyor():
    """`insa.py` listeyi ELLE yazmamis olmali.

    Kodlar `insa.py` icinde duz metin olarak gecmemeli; dosya onlari
    `canli.js`ten cikarmali. Aksi halde `canli.js`e yeni bir varlik
    eklendiginde sayfa onu hic gostermez ve kimse fark etmez.
    """
    dogru("canli.js okunuyor", 'STATIK / "canli.js"' in _INSA)
    dogru("KRAKEN_ADLARI araniyor", "KRAKEN_ADLARI" in _INSA)
    dogru("kod alani ayiklaniyor", r'kod:\s*"([^"]+)"' in _INSA)
    # KOD SABIT YAZILMAMIS OLMALI -- AMA YALNIZCA ILGILI BLOKTA.
    #
    # Ilk yazimda butun dosyada arandi ve sinama kirmizi yandi:
    # `insa.py` satir ~3009'da `("Bitcoin", "BTC")` var ve o
    # grafik etiketiyle ilgili, bu ozellikle alakasiz MEVCUT kod.
    # Fazla genis desen, bu depoda tekrar eden tuzak (bkz. memory:
    # olcum-araci-tuzaklari, tuzak 4) -- bayraklanan ornegin ham
    # baglamina bakmadan karar verilmemeli.
    blok = _INSA.split("canli_kodlar = (")
    dogru("canli_kodlar atamasi bulundu", len(blok) > 1)
    if len(blok) > 1:
        atama = blok[1][:400]
        for k in _js_kodlari():
            dogru(f"{k} atamada sabit yazili degil", f'"{k}"' not in atama)


def test_sablon_listeyi_kullaniyor():
    """Sablon kutuyu KOSULSUZ basmamali."""
    dogru("canli_kodlar kullaniliyor", "in canli_kodlar" in _SABLON)
    # Eski kosul (her kod) KALMAMIS olmali.
    dogru('eski kosul kalmadi',
          'a.kod != "MAKRO"' not in _SABLON.split("canli-fiyat")[0][-400:])


def test_bist_kodu_sizmiyor():
    """EN KRITIK: listede BIST kodu OLMAMALI.

    BIST verisi Borsa Istanbul dagitim lisansi gerektiriyor. Liste
    kaynagi `canli.js` ve o dosya yalnizca Kraken'den kripto/emtia
    cekiyor; bir BIST kodu buraya girerse analiz sayfasina lisansli
    fiyat dusme yolu acilir.
    """
    k = _js_kodlari()
    # Bilinen BIST kodlari ve kalip: BIST kodlari 4-5 harf ve
    # kripto/emtia kisaltmalarindan ayri.
    yasak = {"THYAO", "ASELS", "GARAN", "AKBNK", "XU100", "BIST",
             "EREGL", "KCHOL", "SISE", "TUPRS"}
    es("yasak kod yok", sorted(set(k) & yasak), [])
    dogru("liste yalnizca kripto/emtia",
          set(k) <= {"BTC", "ETH", "PAXG", "XRP", "SOL", "XAU", "XAG"})
    # `canli.js` BIST ucuna hic istek atmamali.
    #
    # YALNIZCA GERCEK ADRESLERE bakiliyor. Ilk yazimda butun dosya
    # taranmisti ve sinama kirmizi yandi -- cunku BIST kelimesi
    # dosyanin KENDI YORUMUNDA geciyor ("BIST hisseleri buraya ASLA
    # giremez"). Yani sinama, kurali ANLATAN cumleyi kuralin IHLALI
    # sandi. Fazla genis desen, bu depoda tekrar eden tuzak.
    adresler = re.findall(r'"(https?://[^"]+)"', _JS)
    dogru("en az bir uc adresi okundu", len(adresler) >= 2)
    for a in adresler:
        for kotu in ("bist", "borsaistanbul", "matriks", "tradingview"):
            dogru(f"{a[:38]} {kotu!r} icermiyor", kotu not in a.lower())


def test_tablo_kod_alani_tasiyor():
    """Her varlik `kod` alani tasimali.

    `kod` olmayan bir varlik seritte gorunur ama analiz sayfasinda
    HIC gorunmez -- yani kusur yalnizca bir sayfada ortaya cikar ve
    gozden kacar.
    """
    m = re.search(r"var KRAKEN_ADLARI = \[(.*?)\];", _JS, re.S)
    dogru("tablo okunuyor", m)
    if m:
        iz = re.findall(r'iz:\s*"([^"]+)"', m.group(1))
        kod = re.findall(r'kod:\s*"([^"]+)"', m.group(1))
        es("her iz icin bir kod var", len(kod), len(iz))


for _ad, _f in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_f):
        _f()

if kaldi:
    print("canli fiyat kodlari: KIRIK")
    for _x in kaldi:
        print("  ", _x)
    raise SystemExit(1)
print(f"canli fiyat kodlari: {gecti} dogrulama gecti")
