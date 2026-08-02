"""Kod tarafindan yazilan makro yorumu -- sifir maliyet, sifir uydurma riski.

`yazar.py` ile ayni felsefe: her cumle hesaplanan bir degerden turer.

NE YAZILIR, NE YAZILMAZ -- bu ayrim urunun guvenilirligi
--------------------------------------------------------
YAZILIR:
  * Serilerin ne yaptigi. Rakam ve tarih kaynaktan gelir.
  * Turkiye ekonomisine hangi KANALLARDAN gectigi. "Turkiye net enerji
    ithalatcisidir, ham petrol fiyati ithalat faturasini dogrudan etkiler"
    yapisal bir olgudur, tahmin degil.

YAZILMAZ:
  * **Hareketin NEDENI.** Petrolun neden yukseldigini veri soylemiyor;
    "arz endisesiyle yukseldi" demek uydurmaktir. Neden yazmak icin haber
    kaynagi gerekir, fiyat serisi yetmez.
  * **Gelecek yonu.** Ne fiyat, ne faiz, ne kur ongorusu.
  * **Etkinin buyuklugu.** "TUFE'yi 2 puan yukseltir" demek model kurmayi
    gerektirir; kanali soylemek yeterli, katsayi uydurulmaz.

Bu ayrimi kod duzeyinde tutmak, sonradan "acaba bunu yazabilir miydik"
tartismasini bitirir: sablonda olmayan cumle uretilmez.
"""

from __future__ import annotations

import bicim
from makro_analiz import Gorunum, Hareket

#: Yorum eklenecek gostergeler ve Turkiye'ye gecis kanallari
KANALLAR: dict[str, tuple[str, ...]] = {
    "DCOILBRENTEU": (
        "Türkiye net enerji ithalatçısıdır; ham petrol ve doğal gaz "
        "faturası cari işlemler dengesinin en büyük kalemlerinden biridir. "
        "Brent'teki hareket, ithalat faturasına doğrudan yansıyan bir "
        "girdidir.",
        "Akaryakıt fiyatları üzerinden tüketici enflasyonuna geçiş kanalı "
        "vardır. Geçişin hızı ve büyüklüğü vergi yapısına, kur seviyesine "
        "ve dağıtım marjlarına bağlı olduğu için doğrudan okunamaz.",
        "Yakıt maliyetinin gider içindeki payı yüksek olan sektörler bu "
        "kalemden daha erken etkilenir: havayolu taşımacılığı, karayolu "
        "lojistiği, petrokimya ve enerji yoğun üretim yapan sanayi kolları.",
    ),
    "DGS10": (
        "ABD uzun vadeli tahvil getirisi, gelişmekte olan ülkelerin dış "
        "borçlanma maliyeti için referans oluşturur. Getirilerin yükseldiği "
        "dönemlerde bu ülkelerin tahvillerine talep görece azalır.",
    ),
    "DFF": (
        "Politika faizi, küresel likiditenin fiyatını belirleyen ana "
        "değişkendir; gelişmekte olan ülke varlıklarına yönelen sermaye "
        "akımlarının arka planındaki referans budur.",
    ),
}


# ---------------------------------------------------------------------------
# Cumle parcalari
# ---------------------------------------------------------------------------

def _seviye(h: Hareket) -> str:
    """Gostergenin son degeri, birimiyle.

    Oran serilerinde IKI ondalik kullanilir: tahvil getirisinde %4,68 ile
    %4,7 arasindaki fark 2 baz puandir ve piyasa dilinde anlamlidir.
    """
    if h.oran_mi:
        return bicim.yuzde(h.son, basamak=2)
    return f"{bicim.sayi(h.son, 2)} {h.birim}"


def _donem_ifadesi(h: Hareket) -> str:
    """Pencere boyunca degisim -- oran serilerinde baz puan, fiyatta yuzde."""
    if h.oran_mi:
        bp = h.baz_puan
        yon = "yükseldi" if bp and bp > 0 else "geriledi" if bp else "yatay kaldı"
        return f"{abs(bp):.0f} baz puan {yon}" if bp else yon
    y = h.donem_yuzde
    if y is None:
        return "değişim hesaplanamadı"
    yon = "yükseldi" if y > 0 else "geriledi"
    return f"{bicim.yuzde(abs(y))} {yon}"


def _baslik(g: Gorunum) -> str:
    """En buyuk hareketi yapan gostergeden baslik uretir."""
    petrol = g.bul("DCOILBRENTEU")
    if petrol is not None:
        cikis = petrol.dipten_zirveye_yuzde
        geri = petrol.zirveden_yuzde
        if cikis is not None and cikis >= 15 and geri is not None and geri <= -5:
            return (
                f"Brent {bicim.yuzde(cikis)} yükselip geri çekildi: "
                "Türkiye'ye hangi kanallardan geliyor"
            )
        if cikis is not None and cikis >= 15:
            return f"Brent petrolde {bicim.yuzde(cikis)} yükseliş: etkiler nereye düşüyor"
        y = petrol.donem_yuzde
        if y is not None and abs(y) >= 8:
            yon = "yükseliş" if y > 0 else "gerileme"
            return f"Brent petrolde {bicim.yuzde(abs(y))} {yon} ve Türkiye'ye etkisi"
    fark = g.getiri_farki
    if fark is not None and fark < 0:
        return "ABD getiri eğrisi ters döndü: gelişmekte olan piyasalara etkisi"
    return f"Küresel göstergeler: {bicim.tarih(g.en_son_tarih)} tablosu"


# ---------------------------------------------------------------------------
# Bolumler
# ---------------------------------------------------------------------------

def _ozet(g: Gorunum) -> str:
    p: list[str] = []
    petrol = g.bul("DCOILBRENTEU")
    if petrol is not None:
        p.append(
            f"Brent petrol {bicim.tarih(petrol.son_tarih)} itibarıyla "
            f"{_seviye(petrol)} seviyesinde. İzlenen {petrol.gozlem_sayisi} işlem "
            f"gününde {bicim.tarih(petrol.dip_tarih)} tarihli "
            f"{bicim.sayi(petrol.dip, 2)} dolarlık dibi ile "
            f"{bicim.tarih(petrol.zirve_tarih)} tarihli "
            f"{bicim.sayi(petrol.zirve, 2)} dolarlık zirvesi arasında hareket etti."
        )
    on = g.bul("DGS10")
    if on is not None:
        p.append(
            f"ABD 10 yıllık tahvil getirisi {_seviye(on)} "
            f"({bicim.tarih(on.son_tarih)}), aynı dönemde {_donem_ifadesi(on)}."
        )
    fark = g.getiri_farki
    if fark is not None:
        durum = "pozitif eğimli" if fark > 0 else "ters dönmüş"
        p.append(
            f"10 yıllık ile 2 yıllık arasındaki fark {abs(fark):.0f} baz puan; "
            f"getiri eğrisi {durum}."
        )
    return " ".join(p)


def _tablo(g: Gorunum) -> str:
    satirlar = [
        "| Gösterge | Son değer | Tarih | Dönem değişimi |",
        "|---|---|---|---|",
    ]
    for h in g.hareketler:
        satirlar.append(
            f"| {h.ad} | {_seviye(h)} | {bicim.tarih(h.son_tarih)} | "
            f"{_donem_ifadesi(h)} |"
        )
    satirlar.append("")
    satirlar.append(
        "Her göstergenin son gözlem tarihi farklı olabilir; tabloda her satır "
        "kendi tarihini taşır. Dönem değişimi, yukarıdaki pencerenin ilk "
        "gözlemine göre hesaplanmıştır."
    )
    return "\n".join(satirlar)


def _petrol_bolumu(g: Gorunum) -> str:
    h = g.bul("DCOILBRENTEU")
    if h is None:
        return ""
    p: list[str] = []

    cikis = h.dipten_zirveye_yuzde
    if cikis is not None:
        p.append(
            f"{bicim.tarih(h.dip_tarih)} tarihindeki {bicim.sayi(h.dip, 2)} "
            f"dolardan {bicim.tarih(h.zirve_tarih)} tarihindeki "
            f"{bicim.sayi(h.zirve, 2)} dolara kadar {bicim.yuzde(cikis)} yükseldi."
        )
    geri = h.zirveden_yuzde
    if geri is not None and geri < 0:
        p.append(
            f"Zirveden bugüne {bicim.yuzde(abs(geri))} geri çekilme var; "
            f"son değer {bicim.sayi(h.son, 2)} dolar."
        )

    son_d = h.son_degisim
    if son_d is not None and abs(son_d) >= 3:
        yon = "yükseliş" if son_d > 0 else "düşüş"
        p.append(
            f"Son iki gözlem arasında ({bicim.tarih(h.onceki_tarih)} → "
            f"{bicim.tarih(h.son_tarih)}) {bicim.sayi(abs(son_d), 2)} dolarlık "
            f"bir {yon} kaydedildi."
        )

    p.append(
        "**Bu hareketin nedeni bu yazının konusu değildir.** Fiyat serisi "
        "fiyatın ne yaptığını gösterir, neden öyle yaptığını göstermez; "
        "nedene ilişkin bir açıklama ancak birincil haber kaynaklarına "
        "dayanarak yapılabilir."
    )
    return " ".join(p)


def _faiz_bolumu(g: Gorunum) -> str:
    p: list[str] = []
    dff = g.bul("DFF")
    iki, on = g.bul("DGS2"), g.bul("DGS10")

    if dff is not None:
        sabit = dff.son_degisim is not None and abs(dff.son_degisim) < 0.01
        p.append(
            f"Efektif fed fonu faizi {_seviye(dff)} ({bicim.tarih(dff.son_tarih)})"
            + (
                f"; izlenen dönemde sabit kaldı."
                if sabit and abs(dff.donem_degisim) < 0.01
                else f"; dönem içinde {_donem_ifadesi(dff)}."
            )
        )

    if iki is not None and on is not None:
        p.append(
            f"Piyasa tarafında 2 yıllık getiri {_seviye(iki)}, 10 yıllık "
            f"{_seviye(on)}. Dönem içinde 2 yıllık {_donem_ifadesi(iki)}, "
            f"10 yıllık {_donem_ifadesi(on)}."
        )
        fark = g.getiri_farki
        if fark is not None:
            if fark > 0:
                p.append(
                    # "pahali" bir deger yargisidir ve ifade taramasi hakli
                    # olarak isaretliyor; "yuksek" olcumun kendisidir.
                    f"Aradaki {abs(fark):.0f} baz puanlık pozitif fark, uzun "
                    "vadeli borçlanma faizinin kısa vadeliden yüksek olduğu "
                    "normal eğim anlamına gelir."
                )
            else:
                p.append(
                    f"Aradaki {abs(fark):.0f} baz puanlık negatif fark, getiri "
                    "eğrisinin ters döndüğünü gösterir; tahvil piyasası uzun "
                    "vadede bugünkünden düşük faiz fiyatlıyor demektir."
                )
    return " ".join(p)


def _turkiye_bolumu(g: Gorunum) -> str:
    parcalar: list[str] = []
    for h in g.hareketler:
        kanallar = KANALLAR.get(h.kod)
        if not kanallar:
            continue
        parcalar.append(f"**{h.ad}.** " + " ".join(kanallar))

    if not parcalar:
        return ""

    parcalar.append(
        "Bu kanallar yapısal ilişkilerdir, öngörü değildir. Etkinin ne zaman "
        "ve ne ölçüde görüleceği kur seviyesi, vergi düzenlemeleri, stok "
        "politikaları ve sözleşme yapılarına bağlı olarak değişir; bu yazıda "
        "bir büyüklük tahmini yapılmamaktadır."
    )
    return "\n\n".join(parcalar)


def _izleme(g: Gorunum) -> str:
    maddeler: list[str] = []
    if g.bul("DCOILBRENTEU") is not None:
        maddeler.append(
            "Brent'in zirve seviyesine geri dönüp dönmediği; kalıcılık, tek "
            "seferlik sıçramadan farklı sonuç doğurur."
        )
        maddeler.append(
            "Enerji yoğun sektörlerin çeyrek bilançolarında maliyet kaleminin "
            "seyri."
        )
    if g.bul("DGS10") is not None:
        maddeler.append(
            "ABD uzun vadeli getirilerinin yönü ve gelişmekte olan ülke risk "
            "primlerine yansıması."
        )
    if g.getiri_farki is not None:
        maddeler.append("2 yıllık ile 10 yıllık arasındaki farkın yönü.")
    if not maddeler:
        maddeler.append("Göstergelerin bir sonraki yayım tarihindeki seyri.")

    gorulen: set[str] = set()
    benzersiz = [m for m in maddeler if not (m in gorulen or gorulen.add(m))]
    return "\n".join(f"- {m}" for m in benzersiz)


def _kaynak_bolumu(g: Gorunum) -> str:
    kaynaklar = sorted({h.kaynak for h in g.hareketler})
    s = (
        "Veriler " + ", ".join(kaynaklar) + " üzerinden alınmıştır. "
        "Seriler kamuya açıktır ve ticari kullanıma izin verir. "
        "Bu sayfadaki bütün değişim, yüzde ve baz puan hesapları ham "
        "serilerden tarafımızca yapılmıştır."
    )
    if g.notlar:
        s += " Bu yayında çekilemeyen göstergeler: " + ", ".join(g.notlar) + "."
    return s


# ---------------------------------------------------------------------------
# Genel arayuz
# ---------------------------------------------------------------------------

def yaz(g: Gorunum) -> str:
    """Gorunumden tam bir makro yazisi uretir. API cagrisi yapmaz."""
    bolumler: list[str] = [f"# {_baslik(g)}", ""]

    def ekle(baslik: str, icerik: str) -> None:
        if icerik and icerik.strip():
            bolumler.extend([f"## {baslik}", "", icerik, ""])

    ekle("Özet", _ozet(g))
    ekle("Göstergeler", _tablo(g))
    ekle("Enerji tarafı", _petrol_bolumu(g))
    ekle("ABD faiz tarafı", _faiz_bolumu(g))
    ekle("Türkiye'ye hangi kanallardan geliyor", _turkiye_bolumu(g))
    ekle("Neye bakmalı", _izleme(g))
    ekle("Veri kaynağı ve yöntem", _kaynak_bolumu(g))

    return "\n".join(bolumler).rstrip() + "\n"
