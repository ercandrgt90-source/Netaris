"""Veri aciklamasi basliklarini cozer ve Turkce cumleye cevirir.

    "Eurozone Retail Sales YoY Actual 0.7% (Forecast 1%, Previous 1.6%)"
      -> gosterge : Euro Bölgesi perakende satışları (yıllık)
         gelen    : %0,7   beklenti: %1   önceki: %1,6
      -> "Beklentinin 0,3 puan altında kaldı; önceki döneme göre
          0,9 puan geriledi."

NEDEN ONEMLI
------------
Bu kalip BEKLENTIYI tasiyor. Ucretsiz konsensus verisi bulunamadigi
icin veri haberlerinde "beklenti neydi" sorusu cevapsiz kaliyordu ve
sitenin en zayif yani buydu. Kaynak basligin kendisinde veriyor.

NE URETILIR
-----------
YALNIZCA OLCUM. "Beklentinin 0,3 puan altinda" bir cikarma islemidir.
"Zayif geldi" ise bir yorumdur ve burada URETILMEZ -- zayifligin
esigini kim koyuyor sorusu cevapsizdir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: "Actual 0.7% (Forecast 1%, Previous 1.6%)" kalibi.
#:
#: Alanlar "-" olabiliyor (beklenti yayimlanmamis); o durumda None.
#: Sayilar negatif, ondalikli, binlik ayracli ve birimli gelebiliyor:
#:   "Actual -1.0%", "Actual 1,929", "Actual 44.7", "Actual A$1,929 mln"
_SAYI = r"(-?[\d.,]+\s*(?:%|K|M|B|bn|mln|k)?|-)"
KALIP = re.compile(
    r"^(?P<ad>.+?)\s+Actual\s+(?P<gelen>" + _SAYI + r")"
    r"(?:\s*\(\s*(?:Forecast|Consensus)\s+(?P<beklenti>" + _SAYI + r")"
    r"(?:\s*,\s*Previous\s+(?P<onceki>" + _SAYI + r"))?\s*\))?",
    re.I)

#: Kaynagin basliga ekledigi onek. Sayfada kunye zaten var; basligin
#: icinde ikinci kez tasimak gereksiz.
ONEK = re.compile(r"^\s*FinancialJuice\s*:\s*", re.I)


@dataclass(frozen=True)
class VeriBasligi:
    ad: str
    gelen: float | None
    beklenti: float | None
    onceki: float | None
    birim: str          # "%" ya da ""

    @property
    def beklenti_farki(self) -> float | None:
        if self.gelen is None or self.beklenti is None:
            return None
        return self.gelen - self.beklenti

    @property
    def donem_farki(self) -> float | None:
        if self.gelen is None or self.onceki is None:
            return None
        return self.gelen - self.onceki


def _sayi(m: str | None) -> tuple[float | None, str]:
    """Metinden sayi ve birim. Cozulemezse (None, "")."""
    if not m or m.strip() in ("-", ""):
        return None, ""
    s = m.strip()
    birim = "%" if "%" in s else ""
    # Binlik ayraci nokta DEGIL virgul (kaynak Ingilizce bicim
    # kullaniyor): "1,929.5" -> 1929.5
    t = re.sub(r"[^\d.,\-]", "", s).replace(",", "")
    try:
        return float(t), birim
    except ValueError:
        return None, birim


def coz(baslik: str) -> VeriBasligi | None:
    """Basligi cozer. Kalip tutmuyorsa None -- zorlanmiyor."""
    b = ONEK.sub("", baslik).strip()
    m = KALIP.match(b)
    if not m:
        return None
    gelen, birim = _sayi(m.group("gelen"))
    if gelen is None:
        return None
    beklenti, b2 = _sayi(m.group("beklenti"))
    onceki, b3 = _sayi(m.group("onceki"))
    return VeriBasligi(
        ad=m.group("ad").strip(),
        gelen=gelen, beklenti=beklenti, onceki=onceki,
        birim=birim or b2 or b3,
    )


def _vir(x: float, b: int = 1) -> str:
    s = f"{abs(x):,.{b}f}"
    s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return ("−" if x < 0 else "") + s


def _deger(x: float | None, birim: str) -> str:
    """Sayiyi birimiyle yazar.

    ISARET YUZDENIN ONUNDE: "%−0,30" degil "−%0,30". Turkce'de yuzde
    isareti sayidan once gelir, eksi ondan da once.
    """
    if x is None:
        return "—"
    if birim != "%":
        return _vir(x, 2)
    return ("−" if x < 0 else "") + f"%{_vir(abs(x), 2)}"


def _fark_sozu(x: float, birim: str) -> str:
    """Fark ifadesi. "PUAN" YALNIZCA ORAN SERILERINDE.

    Ticaret dengesi 1.929'dan -3.018'e giderken fark "4.947 puan"
    degildir -- puan bir ORAN farkinin birimi. Oransiz serilerde
    yalnizca sayi yaziliyor.
    """
    return f"{_vir(abs(x), 2)} puan" if birim == "%" else _vir(abs(x), 2)


def ozet(v: VeriBasligi) -> str:
    """Turkce olcum cumlesi. YORUM YOK.

    "Beklentinin 0,3 puan altinda" bir cikarma islemidir.
    "Zayif geldi" bir yorumdur ve uretilmez: zayifligin esigini kim
    koyuyor sorusu cevapsizdir.
    """
    p = [f"Açıklanan değer {_deger(v.gelen, v.birim)}."]
    if v.beklenti is not None:
        f = v.beklenti_farki
        yon = ("beklentiyle aynı" if abs(f) < 1e-9
               else ("beklentinin üzerinde" if f > 0 else "beklentinin altında"))
        p.append(f"Beklenti {_deger(v.beklenti, v.birim)}; "
                 f"{yon}"
                 + ("" if abs(f) < 1e-9 else f" ({_fark_sozu(f, v.birim)})")
                 + ".")
    if v.onceki is not None:
        d = v.donem_farki
        yon = ("değişmedi" if abs(d) < 1e-9
               else ("yükseldi" if d > 0 else "geriledi"))
        p.append(f"Önceki dönem {_deger(v.onceki, v.birim)}; "
                 f"{yon}"
                 + ("" if abs(d) < 1e-9 else f" ({_fark_sozu(d, v.birim)})")
                 + ".")
    return " ".join(p)


def temiz_baslik(baslik: str) -> str:
    """Kaynak onekini kaldirir. Kunye sayfada ayrica basiliyor."""
    return ONEK.sub("", baslik).strip()


def turkce_baslik(v: VeriBasligi, ad_tr: str) -> str:
    """Cozulmus veri basligini Turkce KURAR -- cevirmez.

    Makine cevirisi bu kalibi bozuyordu:

        "Italian Industrial Production MoM Actual -1.0% (Forecast 0.3%)"
        -> "Italyan Sanayi Uretimi Gerceklesen Aylik % -1.0 (Tahmin %0.3"

    Sayilar Ingilizce bicimde kaliyor (nokta ondalik), yuzde isareti
    yer degistiriyor ve kelime sirasi bozuluyor. Cozum ceviriyi
    duzeltmek degil: sayilari CEVIRMEMEK. Gosterge ADI cevriliyor,
    rakamlar bizim bicimimizle yeniden yaziliyor.
    """
    p = f"{ad_tr}: {_deger(v.gelen, v.birim)}"
    ek = []
    if v.beklenti is not None:
        ek.append(f"beklenti {_deger(v.beklenti, v.birim)}")
    if v.onceki is not None:
        ek.append(f"önceki {_deger(v.onceki, v.birim)}")
    return p + (" — " + ", ".join(ek) if ek else "")


#: Gosterge adindaki donem eklerinin Turkcesi. Ceviriye birakildiginda
#: "YoY" cogu zaman oldugu gibi kaliyor ya da "Yillik Yillik" oluyor.
_DONEM_EKI = (
    (re.compile(r"\s*\bYoY\b", re.I), " (yıllık)"),
    (re.compile(r"\s*\bMoM\b", re.I), " (aylık)"),
    (re.compile(r"\s*\bQoQ\b", re.I), " (çeyreklik)"),
    (re.compile(r"\s*\bWoW\b", re.I), " (haftalık)"),
    (re.compile(r"\s*\bYTD\b", re.I), " (yıl başından beri)"),
)


def ad_ayir(ad: str) -> tuple[str, str]:
    """Gosterge adini "cevrilecek kisim" ve "Turkce donem eki" olarak
    ayirir. Donem eki ceviriye HIC girmiyor."""
    ek = ""
    for desen, tr in _DONEM_EKI:
        if desen.search(ad):
            ek = tr
            ad = desen.sub("", ad)
            break
    return ad.strip(), ek
