"""Teknik gorunum yazisi -- kod ile uretilir, API cagrisi yok.

DIL KURALI -- bu modulun varlik sebebi
--------------------------------------
Teknik analiz, yatirim tavsiyesi diline en yakin duran icerik tipidir.
Kural: **gostergenin DURUMU bildirilir, EYLEM onerilmez.**

  YAZILIR : "RSI 72. Geleneksel yorumda 70 uzeri asiri alim bolgesi
            sayilir."                       -> olcum + yaygin tanim
  YAZILMAZ: "RSI yuksek, kar realizasyonu dusunulebilir"
            "hedef 75.000"
            "yukselis bekleniyor"           -> oneri ve ongoru

Destek/direnc seviyeleri GECMIS fiyat noktalaridir: "son 90 gunde birden
cok kez tepki verilen bolge" bir olgudur, tahmin degil.

Ayrica her yazi, teknik analizin ne olup ne olmadigini anlatan bir yontem
notuyla biter. Bu not sussuz degil: teknik gostergelerin gecmis fiyattan
turedigini ve gelecegi bilmedigini soylemek, bu icerik tipinde okura
borcumuz.
"""

from __future__ import annotations

import bicim
from teknik import Rapor

#: RSI yorum bolgeleri -- yaygin kabul goren esikler
RSI_BOLGELERI = (
    (70.0, "geleneksel yorumda **aşırı alım** bölgesi sayılan 70 seviyesinin üzerinde"),
    (55.0, "nötr bandın üst yarısında"),
    (45.0, "nötr bandın ortasında"),
    (30.0, "nötr bandın alt yarısında"),
    (0.0, "geleneksel yorumda **aşırı satım** bölgesi sayılan 30 seviyesinin altında"),
)


def _para(d: float | None, basamak: int | None = None) -> str:
    if d is None:
        return "—"
    if basamak is None:
        basamak = 0 if d >= 1000 else (2 if d >= 1 else 4)
    return bicim.sayi(d, basamak) + " $"


def _rsi_bolge(deger: float) -> str:
    for esik, metin in RSI_BOLGELERI:
        if deger >= esik:
            return metin
    return RSI_BOLGELERI[-1][1]


def _baslik(r: Rapor) -> str:
    """Iki parcali baslik: solda varlik, sagda o gunun en belirgin bulgusu.

    Yedek baslik ASLA "X teknik gorunum" gibi bos kalmaz. Boyle bir baslik
    okura hicbir sey soylemez ve listede diger yazilardan ayirt edilemez.
    Bulgular oncelik sirasiyla denenir; en zayif ihtimalde bile olculmus bir
    sey yazilir (RSI degeri, ortalamalara gore konum ya da haftalik degisim).
    """
    ad = r.ad

    # 1. Uc siniri: asiri alim/satim
    if r.rsi14 is not None and r.rsi14 >= 70:
        return f"{ad}: RSI aşırı alım bölgesinde"
    if r.rsi14 is not None and r.rsi14 <= 30:
        return f"{ad}: RSI aşırı satım bölgesinde"

    # 2. Ortalamalarin tam dizilimi
    if len(r.ort_ustunde) == 3:
        return f"{ad}: fiyat üç ortalamanın da üzerinde"
    if len(r.ort_altinda) == 3:
        return f"{ad}: fiyat üç ortalamanın da altında"

    # 3. Belirgin haftalik hareket
    if r.degisim_7g is not None and abs(r.degisim_7g) >= 8:
        yon = "yükseldi" if r.degisim_7g > 0 else "geriledi"
        return f"{ad}: haftada {bicim.yuzde(abs(r.degisim_7g))} {yon}"

    # 4. Bollinger bandi disi
    if r.bb_ust is not None and r.fiyat > r.bb_ust:
        return f"{ad}: fiyat Bollinger üst bandının üzerinde"
    if r.bb_alt is not None and r.fiyat < r.bb_alt:
        return f"{ad}: fiyat Bollinger alt bandının altında"

    # 5. 200 gunluge gore konum -- en genis gecerli ayrim
    if r.sma200 is not None:
        fark = (r.fiyat / r.sma200 - 1) * 100
        yon = "üzerinde" if fark > 0 else "altında"
        return (
            f"{ad}: 200 günlük ortalamanın {bicim.yuzde(abs(fark))} {yon}"
        )

    # 6. Son care: RSI degeri -- yine de olculmus bir bilgi
    if r.rsi14 is not None:
        return f"{ad}: RSI {bicim.sayi(r.rsi14, 1)}, nötr bantta"

    return f"{ad}: günlük teknik göstergeler"


def _ozet(r: Rapor) -> str:
    p = [f"{r.ad} {_para(r.fiyat)} seviyesinde."]

    degisimler = []
    for etiket, d in (("günlük", r.degisim_1g), ("haftalık", r.degisim_7g),
                      ("aylık", r.degisim_30g)):
        if d is not None:
            degisimler.append(f"{etiket} {bicim.yuzde(d, isaretli=True)}")
    if degisimler:
        p.append("Değişim: " + ", ".join(degisimler) + ".")

    if r.rsi14 is not None:
        p.append(
            f"RSI(14) {bicim.sayi(r.rsi14, 1)} ile {_rsi_bolge(r.rsi14)}."
        )

    ust, alt = r.ort_ustunde, r.ort_altinda
    if len(ust) == 3:
        p.append("Fiyat 20, 50 ve 200 günlük ortalamaların tamamının üzerinde.")
    elif len(alt) == 3:
        p.append("Fiyat 20, 50 ve 200 günlük ortalamaların tamamının altında.")
    elif ust and alt:
        p.append(
            f"Fiyat {', '.join(ust)} ortalamanın üzerinde, "
            f"{', '.join(alt)} ortalamanın altında."
        )
    return " ".join(p)


def _tablo(r: Rapor) -> str:
    satirlar = ["| Gösterge | Değer |", "|---|---|", f"| Fiyat | {_para(r.fiyat)} |"]
    for ad, d in (("20 günlük ortalama", r.sma20),
                  ("50 günlük ortalama", r.sma50),
                  ("200 günlük ortalama", r.sma200)):
        if d is not None:
            satirlar.append(f"| {ad} | {_para(d)} |")
    if r.rsi14 is not None:
        satirlar.append(f"| RSI (14) | {bicim.sayi(r.rsi14, 1)} |")
    if r.macd_histogram is not None:
        satirlar.append(
            f"| MACD histogram | {bicim.sayi(r.macd_histogram, 2, isaretli=True)} |"
        )
    if r.atr_yuzde is not None:
        satirlar.append(f"| Günlük oynaklık (ATR/fiyat) | {bicim.yuzde(r.atr_yuzde)} |")
    if r.bb_genislik is not None:
        satirlar.append(f"| Bollinger bant genişliği | {bicim.yuzde(r.bb_genislik)} |")
    if r.donem_zirve is not None:
        satirlar.append(f"| 90 günlük zirve | {_para(r.donem_zirve)} |")
    if r.donem_dip is not None:
        satirlar.append(f"| 90 günlük dip | {_para(r.donem_dip)} |")
    return "\n".join(satirlar)


def _ortalamalar(r: Rapor) -> str:
    if r.sma20 is None:
        return ""
    p: list[str] = []
    ust, alt = r.ort_ustunde, r.ort_altinda

    if len(ust) == 3:
        p.append(
            "Fiyat 20, 50 ve 200 günlük hareketli ortalamaların üçünün de "
            "üzerinde. Teknik yorumda bu dizilim, kısa ve uzun vadeli "
            "ortalamaların aynı yönde sıralandığı bir yapı olarak tanımlanır."
        )
    elif len(alt) == 3:
        p.append(
            "Fiyat 20, 50 ve 200 günlük hareketli ortalamaların üçünün de "
            "altında. Teknik yorumda bu dizilim, kısa ve uzun vadeli "
            "ortalamaların aşağı yönlü sıralandığı bir yapı olarak tanımlanır."
        )
    else:
        if ust:
            p.append(f"Fiyat {', '.join(ust)} ortalamanın üzerinde.")
        if alt:
            p.append(f"Fiyat {', '.join(alt)} ortalamanın altında.")
        p.append(
            "Ortalamaların karışık dizilimi, kısa ve uzun vadeli seyrin "
            "ayrıştığı dönemlerde görülür."
        )

    if r.sma50 is not None and r.sma200 is not None:
        fark = (r.sma50 / r.sma200 - 1) * 100
        durum = "üzerinde" if fark > 0 else "altında"
        p.append(
            f"50 günlük ortalama, 200 günlüğün {bicim.yuzde(abs(fark))} {durum} "
            f"({_para(r.sma50)} / {_para(r.sma200)})."
        )
    return " ".join(p)


def _momentum(r: Rapor) -> str:
    p: list[str] = []
    if r.rsi14 is not None:
        p.append(
            f"RSI(14) {bicim.sayi(r.rsi14, 1)} ile {_rsi_bolge(r.rsi14)}. "
            "RSI, son 14 dönemdeki yükseliş ve düşüşlerin göreli büyüklüğünü "
            "ölçer; 0-100 aralığında hareket eder."
        )
    if r.macd_cizgi is not None and r.macd_isaret is not None:
        ustunde = r.macd_cizgi > r.macd_isaret
        p.append(
            f"MACD çizgisi {bicim.sayi(r.macd_cizgi, 2)}, işaret çizgisi "
            f"{bicim.sayi(r.macd_isaret, 2)}; histogram "
            f"{bicim.sayi(r.macd_histogram, 2, isaretli=True)}. "
            + ("Çizgi işaretin üzerinde." if ustunde else "Çizgi işaretin altında.")
        )
        p.append(
            "MACD iki üstel ortalamanın farkını izler; histogram bu farkın "
            "kendi ortalamasından ne kadar ayrıştığını gösterir."
        )
    return " ".join(p)


def _oynaklik(r: Rapor) -> str:
    p: list[str] = []
    if r.atr_yuzde is not None:
        p.append(
            f"Ortalama günlük hareket aralığı (ATR-14) {_para(r.atr14)}, "
            f"fiyatın {bicim.yuzde(r.atr_yuzde)}'ine denk geliyor."
        )
    if r.bb_alt is not None:
        konum = "üst bandın üzerinde" if r.fiyat > r.bb_ust else (
            "alt bandın altında" if r.fiyat < r.bb_alt else "bantların içinde"
        )
        p.append(
            f"Bollinger bantları {_para(r.bb_alt)} — {_para(r.bb_ust)} aralığında; "
            f"fiyat {konum}. Bant genişliği {bicim.yuzde(r.bb_genislik)}."
        )
    if r.zirveden_uzaklik is not None:
        p.append(
            f"Fiyat, 90 günlük zirveye göre "
            f"{bicim.yuzde(r.zirveden_uzaklik, isaretli=True)} konumda."
        )
    return " ".join(p)


def _seviyeler(r: Rapor) -> str:
    if not r.destek and not r.direnc:
        return ""
    p = [
        "Aşağıdaki seviyeler, son 90 günün fiyat verisinden çıkarılmıştır: "
        "birden çok kez tepki verilen salınım dipleri ve tepeleridir. "
        "**Bunlar geçmiş fiyat noktalarıdır, gelecek için bir öngörü değildir.**"
    ]
    if r.direnc:
        p.append(
            "Fiyatın üzerindeki seviyeler: "
            + ", ".join(_para(d) for d in r.direnc) + "."
        )
    if r.destek:
        p.append(
            "Fiyatın altındaki seviyeler: "
            + ", ".join(_para(d) for d in r.destek) + "."
        )
    return " ".join(p)


def _yontem(r: Rapor) -> str:
    kaynak = (
        "tokenleştirilmiş altın (PAXG) fiyatından"
        if r.sembol == "PAXGUSDT"
        else "Binance spot piyasa verisinden"
    )
    metin = (
        f"Bu sayfadaki bütün göstergeler {kaynak}, {r.mum_sayisi} günlük "
        "kapanış serisi üzerinden yazılım tarafından hesaplanmıştır. "
        "Yapay zekâ hiçbir sayı üretmez.\n\n"
        "Teknik göstergeler geçmiş fiyat hareketinden türer ve gelecekteki "
        "fiyatı bilmez. Aynı gösterge farklı zaman dilimlerinde farklı sonuç "
        "verir. Bu sayfa, göstergelerin o anki değerlerini ve bu değerlerin "
        "teknik analizde yaygın olarak nasıl tanımlandığını aktarır; "
        "herhangi bir işlem önerisi içermez."
    )
    if r.sembol == "PAXGUSDT":
        metin += (
            "\n\nPAXG, bir ons altına %100 dayalı bir token'dır ve spot altını "
            "yakından izler; ancak LBMA fiksingi değildir. Fiyat farkı ve "
            "likidite koşulları ayrışabilir."
        )
    return metin


def yaz(r: Rapor) -> str:
    """Teknik gorunum yazisi uretir. API cagrisi yapmaz."""
    bolumler: list[str] = [f"# {_baslik(r)}", ""]

    def ekle(baslik: str, icerik: str) -> None:
        if icerik and icerik.strip():
            bolumler.extend([f"## {baslik}", "", icerik, ""])

    ekle("Özet", _ozet(r))
    ekle("Göstergeler", _tablo(r))
    ekle("Hareketli ortalamalar", _ortalamalar(r))
    ekle("Momentum", _momentum(r))
    ekle("Oynaklık", _oynaklik(r))
    ekle("Fiyat seviyeleri", _seviyeler(r))
    ekle("Yöntem ve sınırlar", _yontem(r))

    return "\n".join(bolumler).rstrip() + "\n"
