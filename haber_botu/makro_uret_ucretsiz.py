"""Ucretsiz makro uretim hatti -- API cagrisi yok, maliyet sifir.

    FRED / EVDS -> hareket hesabi -> KOD ILE YAZI -> tarama -> site

Bilanco hattindan farki veri kaynagi: burada rakamlar resmi istatistik
kurumlarindan otomatik cekilir. Bilanco tarafinda KAP otomatik cekilemedigi
icin elle giris gerekiyor; makro tarafinda boyle bir engel yok, o yuzden bu
hat bastan sona otomatiktir.

MALIYET
-------
FRED anahtar istemiyor ve ticari kullanima aciktir. TCMB EVDS ucretsiz ama
kayit ister; anahtar yoksa Turkiye serileri atlanir, yazi kuresel
gostergelerle uretilir.

Kullanim:
    python makro_uret_ucretsiz.py
    python makro_uret_ucretsiz.py --yayinla     # dogrudan site icerigine
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "analiz"))
sys.path.insert(0, str(_KOK / "ai"))
sys.path.insert(0, str(_KOK / "kaynak"))

sys.path.insert(0, str(_KOK))

import beyin  # noqa: E402
import guvenlik  # noqa: E402
import makro  # noqa: E402
import makro_analiz  # noqa: E402
import prompt_makro  # noqa: E402
import yayin  # noqa: E402
import yazar_makro  # noqa: E402

ARSIV = _KOK / "ciktilar"

#: Yaziya giren gostergeler -- yorum bunlar uzerinden kuruluyor
SERILER = ("DCOILBRENTEU", "DFF", "DGS2", "DGS10")

#: Sitenin serit ve piyasa ozeti panelinde gorunecek genis set.
#: Yazidan ayri tutuluyor: panelde 13 gosterge olmasi iyi, yazida 13
#: gostergeyi yorumlamaya calismak metni dagitir.
PANEL_SERILERI = (
    "SP500", "NASDAQCOM", "DJIA",
    "DCOILBRENTEU", "DCOILWTICO",
    "DFF", "DGS2", "DGS10", "T10Y2Y",
    "VIXCLS", "DTWEXBGS", "DEXUSEU",
)

#: Kac gozlemlik pencere. 14 islem gunu iki haftalik bir hareketi gosterir;
#: daha uzun pencere gunluk yorumu bulaniklastirir.
PENCERE = 14


def _cek() -> dict:
    """Serileri ceker. Cekilemeyen seri None olarak isaretlenir.

    Tek bir seri cekilemedi diye butun yayin durmaz, ama sessizce de
    atlanmaz -- rapora not olarak duser ve yazida gorunur.
    """
    sonuc: dict = {}
    for kod in SERILER:
        try:
            sonuc[kod] = makro.fred(kod, son_n=PENCERE)
            s = sonuc[kod]
            print(f"  {kod:<14} {len(s.gozlemler):>3} gozlem, son {s.son.tarih}")
        except Exception as e:
            sonuc[kod] = None
            print(f"  {kod:<14} CEKILEMEDI: {type(e).__name__}: {e}")
    return sonuc


#: Seritte gorunecek kisa adlar
SERIT_ADLARI = {
    "SP500": "S&P 500",
    "NASDAQCOM": "NASDAQ",
    "DJIA": "DOW",
    "DCOILBRENTEU": "BRENT",
    "DCOILWTICO": "WTI",
    "DGS10": "ABD 10Y",
    "DGS2": "ABD 2Y",
    "DGS30": "ABD 30Y",
    "T10Y2Y": "10Y-2Y",
    "DFF": "FED",
    "VIXCLS": "VIX",
    "DTWEXBGS": "DXY",
    "DEXUSEU": "EUR/USD",
}

#: Panelde gosterilecek ad (seritteki kisaltmadan daha acik)
PANEL_ADLARI = {
    "SP500": "S&P 500",
    "NASDAQCOM": "Nasdaq",
    "DJIA": "Dow Jones",
    "DCOILBRENTEU": "Brent",
    "DCOILWTICO": "WTI",
    "DFF": "Fed politika faizi",
    "DGS2": "ABD 2 yıllık",
    "DGS10": "ABD 10 yıllık",
    "T10Y2Y": "10Y − 2Y farkı",
    "VIXCLS": "VIX",
    "DTWEXBGS": "Dolar endeksi",
    "DEXUSEU": "EUR/USD",
}

#: Panel gruplari -- (baslik, kod listesi)
PANEL_GRUPLARI = (
    ("Endeksler", ("SP500", "NASDAQCOM", "DJIA")),
    ("Emtia", ("DCOILBRENTEU", "DCOILWTICO")),
    ("Faiz", ("DFF", "DGS2", "DGS10", "T10Y2Y")),
    ("Risk ve kur", ("VIXCLS", "DTWEXBGS", "DEXUSEU")),
)

SERIT_DOSYASI = _KOK.parent / "site" / "icerik" / "gostergeler.json"


def _tr(d: float, basamak: int = 2) -> str:
    """Turkce sayi: binlik nokta, ondalik virgul."""
    return f"{d:,.{basamak}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _bicimle(h, ad: str) -> dict:
    """Bir hareketi serit/panel kalemine cevirir."""
    fark = h.son_degisim

    if h.oran_mi:
        # Faiz ve getirilerde gunluk degisim BAZ PUAN ile yazilir.
        # "%4,23'ten %4,68'e yuzde 10,6 artti" teknik olarak dogru ama
        # piyasa dilinde yanlistir; dogrusu "45 baz puan".
        deger = "%" + _tr(h.son)
        fark_metin = (
            f"{fark * 100:+.0f} bp"
            if fark is not None and abs(fark) >= 0.005
            else "0 bp"
        )
    elif h.birim == "puan":
        # Getiri farki ve kredi primi zaten puan cinsinden
        deger = _tr(h.son)
        fark_metin = (
            f"{fark * 100:+.0f} bp" if fark is not None else "—"
        )
    else:
        # Fiyat ve endekslerde yuzde degisim anlamli.
        # Endeksler binlik basamakli, ondalik gerekmez.
        basamak = 0 if h.son >= 1000 else 2
        deger = _tr(h.son, basamak)
        if fark is not None and h.onceki:
            yuzde = (h.son / h.onceki - 1) * 100
            fark_metin = f"{yuzde:+.2f}".replace(".", ",") + "%"
        else:
            fark_metin = "—"

    yon = "yatay"
    if fark is not None and fark > 0:
        yon = "artis"
    elif fark is not None and fark < 0:
        yon = "azalis"

    return {
        "kod": h.kod, "ad": ad, "deger": deger, "fark": fark_metin,
        "yon": yon, "tarih": h.son_tarih, "birim": h.birim,
    }

def _panel_yaz(panel_gorunum) -> None:
    """Serit ve piyasa ozeti panelinin verisini siteye yazar.

    Bu CANLI bir akis DEGIL: her kalem kendi son gozlem tarihini tasir ve
    sayfada gri noktayla "son veri" olarak isaretlenir. Canli olanlar
    (kripto, altin) tarayicida `canli.js` tarafindan eklenir ve yesil
    noktayla ayrilir.
    """
    kalemler = [
        _bicimle(h, SERIT_ADLARI.get(h.kod, h.ad)) for h in panel_gorunum.hareketler
    ]
    bul = {k["kod"]: k for k in kalemler}

    gruplar = []
    for baslik, kodlar in PANEL_GRUPLARI:
        icerik = []
        for kod in kodlar:
            k = bul.get(kod)
            if k is None:
                continue
            icerik.append({**k, "ad": PANEL_ADLARI.get(kod, k["ad"])})
        if icerik:
            gruplar.append({"baslik": baslik, "kalemler": icerik})

    SERIT_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    SERIT_DOSYASI.write_text(
        json.dumps(
            {
                "guncelleme": panel_gorunum.en_son_tarih,
                "kaynak": "FRED (St. Louis Fed)",
                "kalemler": kalemler,
                "gruplar": gruplar,
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"panel verisi: {len(kalemler)} gosterge, {len(gruplar)} grup "
          f"-> {SERIT_DOSYASI.relative_to(_KOK.parent)}")


def main() -> int:
    a = argparse.ArgumentParser(description="Ucretsiz makro yorum hatti")
    a.add_argument("--yayinla", action="store_true",
                   help="site icerik klasorune de yaz")
    args = a.parse_args()

    print("=" * 66)
    print("MAKRO GORUNUM  (ucretsiz hat)")
    print("=" * 66)

    seriler = _cek()
    gorunum = makro_analiz.hesapla(seriler)

    if not gorunum.hareketler:
        print("\nHicbir gosterge cekilemedi -- yazi uretilmedi.")
        return 1

    print(f"\n{len(gorunum.hareketler)} gosterge yaziya girecek")
    for h in gorunum.hareketler:
        print(f"  {h.ad}: {h.son} {h.birim} ({h.son_tarih})")

    # Panel icin genis set ayrica cekilir -- yazi 4 gostergeyi yorumluyor,
    # panel 12'sini gosteriyor
    print("\npanel gostergeleri")
    panel_seriler: dict = {}
    for kod in PANEL_SERILERI:
        try:
            panel_seriler[kod] = makro.fred(kod, son_n=PENCERE)
        except Exception as e:
            panel_seriler[kod] = None
            print(f"  {kod:<14} CEKILEMEDI: {type(e).__name__}")
    panel_gorunum = makro_analiz.hesapla(panel_seriler)
    _panel_yaz(panel_gorunum)

    # Depoya butun gozlemleri yaz -- panel yalnizca SON degeri gosterir,
    # depo GECMISI biriktirir. Zamanla kendi zaman serimiz olusur ve
    # FRED'e gitmeden "gecen ay Brent kacti" sorulabilir.
    gozlemler = []
    for kod, seri in panel_seriler.items():
        if seri is None:
            continue
        for g in seri.gozlemler:
            gozlemler.append({
                "kod": kod, "tarih": g.tarih, "deger_ham": g.deger,
                "birim": seri.birim, "ad": seri.ad, "kaynak": seri.kaynak,
            })
    with beyin.baglan() as b:
        with beyin.calisma_kaydi(b, "makro") as ozet:
            n = beyin.gosterge_yaz(b, gozlemler)
            ozet.update({"yeni_gozlem": n, "seri": len(panel_seriler)})
    print(f"depo: {n} yeni gozlem ({len(gozlemler)} okundu)")

    govde = yazar_makro.yaz(gorunum)
    # Tarama yayimlanan sayfanin hali uzerinden; uyari metni altbilgide
    # zaten var, govdeye ikinci kez yazilmiyor
    metin = f"{govde}\n\n{prompt_makro.UYARI_METNI}\n"

    print(f"\nyazi uretildi: {len(govde.split())} kelime, maliyet $0.00")
    print("\nifade taramasi")
    print("-" * 66)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    arsiv_yolu = ARSIV / f"makro-{gorunum.en_son_tarih}-ucretsiz.md"
    arsiv_yolu.write_text(metin, encoding="utf-8")
    print(f"\narsiv: {arsiv_yolu.relative_to(_KOK)}")

    if not tamam:
        print("DURUM: ENGELLENDI -- site icerigine yazilmadi")
        return 1

    if args.yayinla:
        # Gorsel, yazidaki EN BUYUK hareketi yapan serinin gercek
        # gozlemlerinden cizilir -- temsili bir grafik degil, verinin kendisi
        cizilecek = seriler.get("DCOILBRENTEU") or next(
            (s for s in seriler.values() if s is not None), None
        )
        grafik = birim = kod = ""
        if cizilecek is not None:
            grafik = ";".join(
                f"{g.deger:.2f}".replace(".", ",") for g in cizilecek.gozlemler
            )
            kod, birim = cizilecek.ad, cizilecek.birim

        dosya = yayin.yaz_makro(
            govde,
            konu="Küresel göstergeler",
            kaynak="FRED (St. Louis Fed)",
            grafik=grafik,
            grafik_kod=kod,
            grafik_birim=birim,
            kaynaklar="FRED",
            sayimlar=";".join([
                f"{len(gorunum.hareketler)}|yorumlanan gösterge",
                f"{sum(len(s.gozlemler) for s in seriler.values() if s)}|gözlem noktası",
                f"{PENCERE}|işlem günü penceresi",
                f"{len(panel_seriler)}|panelde izlenen seri",
            ]),
        )
        print(f"site icerigi: {dosya.relative_to(_KOK.parent)}")
        print("DURUM: taslak hazir -- 'python site/yayinla.py'")
    else:
        print("DURUM: yalnizca arsive yazildi (--yayinla ile site icerigine gider)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
