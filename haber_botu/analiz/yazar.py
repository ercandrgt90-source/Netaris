"""Kod tarafindan yazilan bilanco analizi -- SIFIR maliyet, sifir uydurma riski.

NEDEN VAR
---------
Urunun farklilastirici analizi zaten koddan geliyor: oranlar, sinyaller,
skor, TMS 29 ayrimi, kar kalitesi tespiti. Dil modeli bunlari uretmiyor,
etraflarina duzyazi yaziyor.

Bu modul o duzyaziyi da kod ile uretiyor. Sonuc:

  * **Maliyet sifir.** API cagrisi yok.
  * **Uydurma riski sifir.** Her cumle hesaplanan bir degerden turuyor;
    modelin olmadigi yerde halusinasyon da olmaz.
  * **Belirlenimci.** Ayni tablo her zaman ayni yaziyi uretir.

Bedeli: metin bir insanin ya da modelin yazdigi kadar akici degil. Cumleler
sablondan turuyor, uslup daha kuru. Ama finansal veri icin bu kabul
edilebilir bir takas -- rakam ve tablo zaten isin ozu.

KULLANIM BICIMI
---------------
Bu, AI hattinin yerine gecen bir sey degil, **tabani**. Butun bilancolar
bununla ucretsiz yayimlanabilir; one cikarilmak istenen analizler AI ile
zenginlestirilir. Kredi bittiginde ya da bittigi icin durulmasi gerektiginde
yayin akisi kesilmez.

DIL NOTU
--------
Gorunen butun sayilar `bicim` modulunden gecer: yuzde isareti sayinin
onunde, ondalik ayraci virgul. Kalem adlari `oranlar.Kalem` ve
`oranlar.OranAdi` sabitlerinden gelir -- burada elle yazilmaz, cunku elle
yazilan bir ad eslesmezse bolum sessizce "hesaplanamadi" der.
"""

from __future__ import annotations

import bicim
from oranlar import EnflasyonEsasi, Kalem, OranAdi, Rapor, SinyalTuru, Yon
from skor import Skor

# Sinyal turu -> okurun sonraki donemde bakmasi gereken sey
IZLEME_MADDELERI: dict[SinyalTuru, str] = {
    SinyalTuru.MARJ_DARALMASI:
        "Marj daralmasının geçici bir maliyet şoku mu, yapısal mı olduğu.",
    SinyalTuru.ALACAK_BUYUMESI:
        "Ticari alacakların hasılatla aynı hızda büyümeye dönüp dönmediği.",
    SinyalTuru.STOK_BUYUMESI:
        "Stok kalemlerinin hammadde/mamul dağılımı ve devir hızı.",
    SinyalTuru.KAR_KALITESI:
        "Faaliyet dışı gelirin dipnotlardaki dağılımı ve tekrarlanabilirliği.",
    SinyalTuru.BORCLULUK:
        "Borcun vade yapısı ve faiz karşılama oranının yönü.",
    SinyalTuru.LIKIDITE:
        "Kısa vadeli yükümlülüklerin çevrilme planı ve nakit pozisyonu.",
    SinyalTuru.REEL_KUCULME:
        "Faaliyet nakit akışının kârı destekleyip desteklemediği.",
    SinyalTuru.KAR_ZARAR_GECISI:
        "Kârlılığın sonraki dönemde sürüp sürmediği.",
}


# ---------------------------------------------------------------------------
# Rapor icinde arama
# ---------------------------------------------------------------------------

def _buyume(rapor: Rapor, ad: str) -> float | None:
    b = next((x for x in rapor.buyumeler if x.ad == ad), None)
    return b.reel if b else None


def _oran(rapor: Rapor, ad: str):
    return next((o for o in rapor.oranlar if o.ad == ad), None)


# ---------------------------------------------------------------------------
# Baslik
# ---------------------------------------------------------------------------

def _baslik(rapor: Rapor) -> str:
    """En guclu bulgudan baslik uretir.

    Manset rakami degil, rakamin altindaki gercegi one cikarir -- AI
    hattina verdigimiz kuralin aynisi.

    Sirket adindan sonra iki nokta kullaniliyor, ek degil. "Turk Hava
    Yollari'nda" gibi unvanlarda bulunma eki tampon "n" istiyor ve bunu
    unvandan guvenilir sekilde cikaramayiz; iki nokta her unvanda dogru.
    """
    ad = bicim.kisa_ad(rapor.sirket)
    hasilat = _buyume(rapor, Kalem.HASILAT)
    marj = _oran(rapor, OranAdi.FAVOK_MARJI)
    fd = _oran(rapor, OranAdi.FAALIYET_DISI)

    marj_daraldi = marj is not None and marj.degisim is not None and marj.degisim <= -1.0
    kar_kalitesi_zayif = fd is not None and fd.deger >= 30
    buyudu = hasilat is not None and hasilat > 10

    if buyudu and marj_daraldi:
        return f"{ad}: hasılat büyüdü, marjlar daraldı"
    if buyudu and kar_kalitesi_zayif:
        return f"{ad}: kâr arttı, kaynağı esas faaliyet değil"
    if marj_daraldi:
        return f"{ad}: marjlar daralmaya devam ediyor"
    if buyudu:
        return f"{ad}: hasılat reel olarak büyüdü"
    if hasilat is not None and hasilat < 0:
        return f"{ad}: hasılat reel olarak geriledi"
    return f"{ad} {rapor.donem} bilanço tablosu"


# ---------------------------------------------------------------------------
# Bolumler
# ---------------------------------------------------------------------------

def _ozet(rapor: Rapor, skor: Skor | None) -> str:
    p: list[str] = []
    hasilat = _buyume(rapor, Kalem.HASILAT)
    net = _buyume(rapor, Kalem.NET_KAR)

    if hasilat is not None:
        yon = "arttı" if hasilat >= 0 else "geriledi"
        p.append(
            f"{rapor.sirket} {rapor.donem} döneminde hasılatı reel olarak "
            f"{bicim.yuzde(abs(hasilat))} {yon}."
        )
    if net is not None:
        yon = "artış" if net >= 0 else "gerileme"
        p.append(
            f"Net kârdaki reel {yon} {bicim.yuzde(abs(net))} düzeyinde."
        )

    if skor and skor.skor is not None and skor.yayimlanabilir:
        olculen = [k for k in skor.kriterler if k.olculdu and k.olculen_puan]
        if olculen:
            guclu = max(olculen, key=lambda k: (k.puan or 0) / k.olculen_puan)
            zayif = min(olculen, key=lambda k: (k.puan or 0) / k.olculen_puan)
            p.append(
                f"Bilanço Kalitesi Skoru 100 üzerinden {skor.skor:.0f}; "
                f"en güçlü kriter {bicim.kucuk(guclu.ad)}, "
                f"en zayıf kriter {bicim.kucuk(zayif.ad)}."
            )

    kotu = [s for s in rapor.sinyaller if s.yon is Yon.KOTU]
    dikkat = [s for s in rapor.sinyaller if s.yon is Yon.DIKKAT]
    if kotu or dikkat:
        p.append(
            f"Tabloda {len(kotu)} olumsuz, {len(dikkat)} dikkat gerektiren "
            "bulgu öne çıkıyor; ayrıntıları aşağıda."
        )
    return " ".join(p)


def _buyume_bolumu(rapor: Rapor) -> str:
    satirlar = ["| Kalem | Reel değişim |", "|---|---|"]
    for b in rapor.buyumeler:
        deger = b.reel if b.reel is not None else b.ham
        satirlar.append(f"| {b.ad} | {bicim.yuzde(deger, isaretli=True)} |")

    esas = (
        "Şirketin finansal tabloları TMS 29 enflasyon muhasebesine göre "
        "düzenlenmiştir. Karşılaştırmalı önceki dönem rakamları cari dönemin "
        "satın alma gücüne çevrildiği için aşağıdaki değişimler **reeldir**; "
        "üzerlerine ayrıca enflasyon düzeltmesi uygulanmaz."
        if rapor.esas is EnflasyonEsasi.TMS29
        else "Rakamlar nominal esasta olup dönem TÜFE'si "
        f"({bicim.yuzde(rapor.enflasyon)}) ile arındırılmıştır."
    )
    return esas + "\n\n" + "\n".join(satirlar)


def _marj_bolumu(rapor: Rapor) -> str:
    oranlar = [o for o in rapor.oranlar if o.ad in OranAdi.MARJLAR]
    if not oranlar:
        return "Marj verisi hesaplanamadı."

    satirlar = ["| Marj | Önceki | Cari | Değişim |", "|---|---|---|---|"]
    for o in oranlar:
        satirlar.append(
            f"| {o.ad} | {bicim.yuzde(o.onceki)} | "
            f"{bicim.yuzde(o.deger)} | {bicim.puan(o.degisim)} |"
        )

    daralan = [o for o in oranlar if o.degisim is not None and o.degisim < 0]
    yorum = ""
    if len(daralan) >= 3:
        yorum = (
            "\n\nMarjların üçü ya da daha fazlası birlikte daralmış durumda. "
            "Bu, sorunun tek bir gider kaleminden değil, fiyat-maliyet "
            "dengesinden kaynaklandığına işaret edebilir."
        )
    elif daralan:
        yorum = f"\n\n{len(daralan)} marjda gerileme görülüyor."
    return "\n".join(satirlar) + yorum


def _kar_kalitesi(rapor: Rapor) -> str:
    p: list[str] = []
    net = _buyume(rapor, Kalem.NET_KAR)
    faaliyet = _buyume(rapor, Kalem.FAALIYET_KARI)
    fd = _oran(rapor, OranAdi.FAALIYET_DISI)

    if net is not None and faaliyet is not None:
        p.append(
            f"Net kâr reel {bicim.yuzde(net, isaretli=True)} değişirken faaliyet "
            f"kârı {bicim.yuzde(faaliyet, isaretli=True)} değişmiş."
        )
        if net - faaliyet > 10:
            p.append(
                "Aradaki fark, kârın bir bölümünün esas faaliyet dışından "
                "geldiğini gösteriyor."
            )

    if fd is not None:
        p.append(
            f"Faaliyet dışı net gelirin net kâra oranı {bicim.yuzde(fd.deger)}"
            + (
                f" (önceki dönem {bicim.yuzde(fd.onceki)}, {bicim.puan(fd.degisim)})."
                if fd.onceki is not None
                else "."
            )
        )
        if fd.deger >= 25:
            p.append(
                "Bu kalem tipik olarak kur farkı, faiz geliri, iştirak veya "
                "duran varlık satış kârı ve TMS 29 uygulamasından doğan "
                "parasal pozisyon kazancı gibi unsurları içerir. Bunların "
                "tekrarlanabilirlikleri birbirinden farklıdır; dağılım için "
                "gelir tablosu dipnotlarına bakılması gerekir."
            )
    return " ".join(p) if p else "Kâr kalitesi verisi hesaplanamadı."


def _nakit_bolumu(rapor: Rapor, simdi) -> str:
    fna = simdi.faaliyet_nakit_akisi
    if fna is None:
        return (
            "Nakit akış tablosu verisi bu analizde yer almıyor. Kârın nakde "
            "dönüşümü değerlendirilememiştir; bu, tablonun eksik kalan yönüdür."
        )

    p = [
        "Faaliyet nakit akışı "
        + (
            "pozitif."
            if fna > 0
            else "**negatif** — şirket esas faaliyetinden nakit üretememiş."
        )
    ]

    if simdi.favok and simdi.favok > 0:
        donusum = fna / simdi.favok
        p.append(
            f"FAVÖK'ün {bicim.yuzde(donusum * 100)}'i nakde dönüşmüş "
            f"(FNA/FAVÖK {bicim.kat(donusum)})."
        )
        if donusum < 0.7:
            p.append(
                "Oranın düşük kalması, satışların karşılığının alacak ya da "
                "stok olarak bilançoda beklediğine işaret edebilir."
            )

    sna = simdi.serbest_nakit_akisi
    if sna is not None:
        if sna > 0:
            p.append(
                "Serbest nakit akışı pozitif: yatırım harcamaları faaliyetten "
                "üretilen nakitle karşılanmış."
            )
        else:
            p.append(
                "**Serbest nakit akışı negatif:** yatırım harcamaları "
                "faaliyetten üretilen nakdi aşmış, fark dış kaynakla "
                "karşılanmak zorunda kalmış."
            )
    return " ".join(p)


def _bilanco_bolumu(rapor: Rapor) -> str:
    p: list[str] = []
    nb = _oran(rapor, OranAdi.NET_BORC_FAVOK)
    cari = _oran(rapor, OranAdi.CARI_ORAN)
    roe = _oran(rapor, OranAdi.ROE)

    if nb is not None:
        p.append(f"Net borcun FAVÖK'e oranı {bicim.kat(nb.deger)}")
        if nb.onceki is not None:
            yon = "yükselmiş" if nb.degisim and nb.degisim > 0 else "gerilemiş"
            p[-1] += f" (önceki dönem {bicim.kat(nb.onceki)}, {yon})."
        else:
            p[-1] += "."

    if cari is not None:
        durum = "1'in üzerinde" if cari.deger >= 1 else "**1'in altında**"
        p.append(f"Cari oran {bicim.kat(cari.deger)} ile {durum}.")
        if cari.deger < 1:
            p.append("Kısa vadeli yükümlülükler dönen varlıkları aşıyor.")

    if roe is not None and roe.degisim is not None:
        yon = "yükselmiş" if roe.degisim > 0 else "gerilemiş"
        p.append(
            f"Özkaynak kârlılığı {bicim.yuzde(roe.deger)} "
            f"({bicim.puan(roe.degisim)} ile {yon})."
        )
    return " ".join(p) if p else "Bilanço oranları hesaplanamadı."


def _sinyal_bolumu(rapor: Rapor) -> str:
    if not rapor.sinyaller:
        return "Eşikleri aşan bir sinyal üretilmedi."
    satirlar = [
        f"**{s.baslik}.** {bicim.bas_harf(s.gerekce)}." for s in rapor.sinyaller
    ]
    return "\n\n".join(satirlar)


def _skor_bolumu(skor: Skor | None) -> str:
    if skor is None or skor.skor is None or not skor.yayimlanabilir:
        return ""
    satirlar = [
        f"Bilanço Kalitesi Skoru **{skor.skor:.0f}/100**, "
        f"veri kapsamı %{skor.kapsam * 100:.0f}.",
        "",
        "| Kriter | Puan |",
        "|---|---|",
    ]
    for k in skor.kriterler:
        if k.olculdu:
            satirlar.append(
                f"| {k.ad} | {bicim.sayi(k.puan)} / {k.olculen_puan} |"
            )
        else:
            satirlar.append(f"| {k.ad} | ölçülemedi |")
    satirlar.append("")
    satirlar.append(
        "Skor finansal tabloların sağlığını ölçer; hissenin fiyatı, "
        "değerlemesi veya getirisi hakkında bir değerlendirme içermez."
    )
    return "\n".join(satirlar)


def _izleme(rapor: Rapor) -> str:
    """Sinyal TURUNE gore izleme maddeleri.

    Baslik metninde sozcuk aramak yerine tur alani kullaniliyor: baslik
    degistiginde eslesme sessizce kaybolmaz.
    """
    maddeler = [
        IZLEME_MADDELERI[s.tur] for s in rapor.sinyaller if s.tur in IZLEME_MADDELERI
    ]
    if not maddeler:
        maddeler.append("Marjların ve nakit üretiminin sonraki dönemdeki seyri.")

    # Yinelenenleri at, sirayi koru
    gorulen: set[str] = set()
    benzersiz = [m for m in maddeler if not (m in gorulen or gorulen.add(m))]
    return "\n".join(f"- {m}" for m in benzersiz)


# ---------------------------------------------------------------------------
# Genel arayuz
# ---------------------------------------------------------------------------

def yaz(rapor: Rapor, simdi, skor: Skor | None = None) -> str:
    """Rapordan tam bir analiz metni uretir. API cagrisi yapmaz."""
    bolumler: list[str] = [f"# {_baslik(rapor)}", ""]

    def ekle(baslik: str, icerik: str) -> None:
        if icerik and icerik.strip():
            bolumler.extend([f"## {baslik}", "", icerik, ""])

    ekle("Özet", _ozet(rapor, skor))
    ekle("Büyüme", _buyume_bolumu(rapor))
    ekle("Kârlılık ve marjlar", _marj_bolumu(rapor))
    ekle("Kâr nereden geldi?", _kar_kalitesi(rapor))
    ekle("Nakit: muhasebe kârı mı, gerçek para mı?", _nakit_bolumu(rapor, simdi))
    ekle("Bilanço sağlamlığı", _bilanco_bolumu(rapor))
    ekle("Dikkat çeken noktalar", _sinyal_bolumu(rapor))
    ekle("Skor ne diyor?", _skor_bolumu(skor))
    ekle("Neye bakmalı", _izleme(rapor))

    return "\n".join(bolumler).rstrip() + "\n"
