# -*- coding: utf-8 -*-
"""YAYIMLANMIS bir bilanco sayfasinin NESI BOZUK -- tek kaynak.

BU MODUL NEDEN VAR
------------------
Ayni soruyu iki yerde soruyoruz:

  * `site/test_bilanco_donem_tutarliligi.py` -- koruma: yeni bozuk
    sayfa cikti mi?
  * `bilanco_tazele --onarim`              -- onarim: hangi sayfalar
    yeniden kurulmali?

Olcut iki yerde ayri yazilsaydi birinin degisip otekinin unutulmasi
kacinilmazdi. Bu depoda "iki yerde ayni seye karar veren kod" sinifi
bir kusur zaten yayina cikti: ara donemin kac ceyrekten olustugu
`uret_bilanco` ile `donem_getir` arasinda farkliydi ve yayindaki 258
bilanco sayfasinin 203'u iki ayri donemi tek etiketle anlatiyordu.

NE DENETLENIYOR
---------------
1. DONEM TUTARLILIGI. Sayfanin seviye tablosundan hesaplanan oran,
   ayni sayfada YAZILI oranla ayni olmali. Olmuyorsa iki tablo ayni
   donemi anlatmiyor.

   Iki oran birden olculuyor cunku tek oran butun sayfalari
   gormuyor: brut marj hasilat gerektiriyor, banka ve yatirim
   ortakliginin seviye tablosunda hasilat satiri yok. Ozkaynak
   karliligi onlari da kapsiyor.

2. KILAVUZ KAPSAMI. Sektor okuma kilavuzu sirketin ALT SEKTORUNE
   uygun olmali. Olculdu: futbol kuluplerinin sayfasina telekom
   kilavuzu, gayrimenkul gelistiricisinin sayfasina GYO kilavuzu
   yaziliyordu (bkz. `analiz/sektor_okuma.ALT_KAPSAM`).
"""

from __future__ import annotations

import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK / "analiz"))

import sektor_okuma                                # noqa: E402

#: Seviyeler iki ondalikli "milyar TL" olarak yaziliyor, yani her
#: sayinin kendi yuvarlanma payi var. Pay hesaplanip uzerine emniyet
#: marji ekleniyor; bundan BUYUK fark yuvarlanmayla aciklanamaz.
EMNIYET_PUAN = 0.5

#: Kiyas bolumu olmayan sayfa bilanco analizi sayilmiyor.
KIYAS_BASLIGI = "## Sektör içindeki konum"

#: (oran adi, pay kalemi, bolen kalemi, oran tablosundaki ad)
OLCUMLER = (
    ("brut_marj", "| Brüt kâr |", "| Hasılat |", "Brüt kâr marjı"),
    ("roe", "| Net kâr |", "| Özkaynak |", "Özkaynak kârlılığı"),
)


def _sayi(s: str) -> float | None:
    s = s.strip().replace("%", "").replace("−", "-")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _milyar(satir: str) -> float | None:
    m = re.search(r"(-?[\d.,]+)\s*milyar", satir)
    return _sayi(m.group(1)) if m else None


def bilanco_sayfasi(metin: str) -> bool:
    """Bu metin kiyas bolumu tasiyan bir bilanco analizi mi."""
    return KIYAS_BASLIGI in metin


def olc(metin: str) -> list[tuple[str, float, float, float]]:
    """[(oran, hesaplanan, yazili, yuvarlanma_payi)] -- olculebilenler."""
    if not bilanco_sayfasi(metin):
        return []
    seviye: dict[str, float | None] = {}
    for satir in metin.splitlines():
        for _, pay_k, bolen_k, _ad in OLCUMLER:
            for k in (pay_k, bolen_k):
                if not satir.startswith(k):
                    continue
                # SEVIYE YALNIZCA "milyar" YAZAN SATIRDAN.
                #
                # Sayfada ayni anahtarla baslayan UC tablo var ve
                # hepsi `| Hasılat |` ile basliyor:
                #
                #   | Hasılat | %34,6 |                  <- yillik degisim
                #   | Hasılat | 71,29 milyar TL |        <- OLCUM
                #   | Hasılat | 71,29 | 64,88 | ... |    <- son dort donem
                #
                # Atama KOSULSUZDU ve son eslesme kazaniyordu. "Son
                # dort donem" bolumu eklendikten sonra o satir SERI
                # satiri oldu; `_milyar` orada None donuyor ve dogru
                # degeri EZIYORDU.
                #
                # OLCULDU (2026-10-31): 302 bilanco sayfasinin
                # 112'sinde seri tablosu var ve o 112'de `olc()`
                # SIFIR kalem donuyordu -- 302 - 112 = 190, bulunan
                # sayiyla tam olarak ayni. Yani yeni bolum, kendi
                # sayfalarinda bu korumayi tumden kor etmisti ve
                # goc tamamlandikca oran %100'e cikacakti.
                #
                # Olcut SATIRIN KENDISI, sirasi degil: "milyar"
                # yazmayan satir seviye tasimaz.
                d = _milyar(satir)
                if d is not None:
                    seviye[k] = d
    cikti = []
    for ad, pay_k, bolen_k, tablo_adi in OLCUMLER:
        pay_d, bolen = seviye.get(pay_k), seviye.get(bolen_k)
        if pay_d is None or not bolen:
            continue
        m = re.search(r"\|\s*" + re.escape(tablo_adi)
                      + r"\s*\|\s*(-?%[\d.,]+)\s*\|", metin)
        if not m:
            continue
        yazili = _sayi(m.group(1))
        if yazili is None:
            continue
        hesap = 100.0 * pay_d / bolen
        pay = 100.0 * (0.005 / abs(bolen)
                       + abs(pay_d) * 0.005 / bolen ** 2) + EMNIYET_PUAN
        cikti.append((ad, hesap, yazili, pay))
    return cikti


def donem_tutarsizligi(metin: str) -> list[tuple[str, float, float]]:
    """Seviye tablosu ile oran tablosunun UYUSMADIGI oranlar."""
    return [(ad, h, y) for ad, h, y, pay in olc(metin)
            if abs(h - y) > pay]


def kilavuz_uyusmazligi(metin: str, sektor_tr: str,
                        alt_sektor: str) -> str:
    """Sayfada KAPSAM DISI bir okuma kilavuzu varsa basligini doner."""
    s = (sektor_tr or "").strip()
    if not s or sektor_okuma.kapsamda(s, alt_sektor):
        return ""
    b = sektor_okuma.OKUMA.get(s)
    if not b:
        return ""
    return b[0] if f"## {b[0]}" in metin else ""


#: Duzeltmeden ONCE uretilmis, bozuklugu BILINEN sayfalar. Koruma
#: (`site/test_bilanco_sayfa_saglam.py`) bunlari tolere ediyor.
MIRAS = _KOK.parent / "site" / "bilanco_miras_bozuk.json"


def miras_sayfalar() -> set[str]:
    """Bozuklugu bilinen sayfa adlari; dosya yoksa bos kume."""
    if not MIRAS.is_file():
        return set()
    try:
        import json                                # noqa: PLC0415
        return set(json.loads(MIRAS.read_text(encoding="utf-8"))
                   .get("sayfalar") or [])
    except (ValueError, OSError):
        return set()


def ozkaynak_celiskisi(metin: str) -> str:
    """Ozkaynak SIFIR YA DA NEGATIFKEN ROE gosteriliyorsa aciklama.

    NEDEN KUSUR -- PROJENIN KENDI KURALI
    ------------------------------------
    `analiz/oranlar._bol` boleni sifir ya da negatif ise None
    donuyor ve gerekcesi orada yazili: "negatif ozkaynakla
    hesaplanan bir ozkaynak karliligi matematiksel olarak
    uretilebilir ama anlamsizdir ve yorumlandiginda yaniltir."

    `uret_bilanco._oranlari` bu korumayi tasimiyordu. Olculdu
    (2026-10-13), yayindaki alti sayfa:

        bizim  ozkaynak -0,22 milyar  ->  ROE  +%128,5
        vking  ozkaynak -0,16 milyar  ->  ROE   +%76,9
        arzum  ozkaynak -0,52 milyar  ->  ROE   +%12,2

    Yani ozkaynagi ERIMIS sirketler yuksek karlilikla gosteriliyor.
    Isaret sayfanin KENDI seviye tablosunda duruyor, bu yuzden
    disaridan veri gerekmiyor.
    """
    oz = None
    for satir in metin.splitlines():
        if satir.startswith("| Özkaynak |"):
            oz = _milyar(satir)
    if oz is None or oz > 0:
        return ""
    m = re.search(r"\|\s*Özkaynak kârlılığı\s*\|\s*(-?%[\d.,]+)\s*\|",
                  metin)
    if not m:
        return ""
    return f"özkaynak {oz} milyar iken ROE {m.group(1)} yazılı"


def onarim_gereken(metin: str, bilgi: dict | None = None) -> list[str]:
    """Sayfanin ONARIM gerektiren yanlari; saglamsa BOS liste.

    Defter kaydi (`bilgi`) verilmezse yalnizca donem tutarliligi
    bakiliyor -- alt sektor oradan okunuyor.
    """
    if not bilanco_sayfasi(metin):
        return []
    sebep = [f"dönem tutarsız ({ad})"
             for ad, _h, _y in donem_tutarsizligi(metin)]
    b = bilgi or {}
    kilavuz = kilavuz_uyusmazligi(metin, b.get("sektor_tr") or "",
                                  b.get("alt_sektor") or "")
    if kilavuz:
        sebep.append(f"kapsam dışı kılavuz ({kilavuz})")
    celiski = ozkaynak_celiskisi(metin)
    if celiski:
        sebep.append(f"anlamsız ROE ({celiski})")
    return sebep
