"""Haber sayfasindaki piyasa kutusu -- rakam, ortalama, konum.

NEDEN VAR
---------
"New York borsasi yukselisle kapandi" haberinin altinda "endeks seviyesi
sirketlerin oz kaynak maliyetini belirler" yaziyordu. Cumle genel olarak
dogru ama O HABERE dair hicbir sey soylemiyor -- hangi endeks, kac oldu,
nereye gore yuksek. Okur rakami baska yerde ariyor.

Bu modul o bosluga rakam koyuyor: ilgili araclarin son degeri, gunluk
degisimi ve kendi hareketli ortalamalarina gore konumu.

TAHMIN YOK
----------
Uretilen skor bir AL/SAT sinyali DEGIL, bir KONUM tarifi: fiyatin kendi
ortalamalarinin kac tanesinin uzerinde oldugunu sayiyor. "Yukselecek"
demiyor, "su an su ortalamalarin uzerinde" diyor. Bu ayrim sayfada da
acikca yaziyor; yoksa yatirim tavsiyesine doner.

VERI DEPODAN
------------
Ek istek yok. `gosterge` ve `fiyat` tablolari zaten biriktiriyor.
Yeterli gecmis yoksa kutu HIC BASILMAZ -- eksik veriyle hesaplanan bir
"200 gunluk ortalama" yaniltici olurdu.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

_KOK = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_KOK / "haber_botu" / "analiz"))

try:
    import teknik  # noqa: E402
except ImportError:      # analiz katmani yoksa kutu basilmaz
    teknik = None

DEPO = _KOK / "haber_botu" / "netaris.db"

#: EMA pencereleri. 200 gunluk en az 200 gozlem ister; seri kisaysa o
#: ortalama atlanir, kutu kalanlarla basilir.
PENCERELER = (20, 50, 200)

#: Konu -> gosterilecek araclar.
#:
#: (kaynak, kod, gorunur ad, birim)
#: kaynak "gosterge" ise FRED serisi, "fiyat" ise Kraken mumu.
#: Kod -> kutunun altinda basilacak aciklama.
#:
#: Etiketten sembolu kaldirmak bilgiyi silmek degil, YERINI degistirmek.
#: "Altın (PAXG)" seridi ve kutuyu kalabaliklastiriyordu; enstrumanin ne
#: oldugu buraya tasindi. Okur rakama bakarken sembolle ugrasmiyor ama
#: neye baktigini sormak isterse cevabi ayni sayfada.
ARAC_NOTLARI = {
    "PAXGUSD": "Altın fiyatı PAXG token verisidir (Kraken); bir ons altına "
               "dayanır, LBMA fiksingi değildir.",
}

#: TURKIYE kutusu -- bolgesi TR olan haberlerde konu ne olursa olsun
#: basiliyor.
#:
#: Sebep: bir Turk okuru icin "TUFE kac, faiz kac, dolar kac" sorusu her
#: haberde gecerli. Bunlar EVDS'den geliyor ve hepsi resmi.
#:
#: Bu seriler EMA tasimiyor: aylik yayimlanan bir enflasyon serisinde
#: "200 gunluk ortalama" anlamsiz olur. Onun yerine son deger, onceki
#: donem ve degisim gosteriliyor.
TURKIYE_GOSTERGELERI: tuple[tuple[str, str, str], ...] = (
    ("TP.TUKFIY2025.GENEL", "TÜFE (yıllık)", "%"),
    ("TP.FE25.OKTG04", "Çekirdek (C)", "%"),
    ("TP.APIFON4", "TCMB fonlama", "%"),
    ("TP.DK.USD.S.YTL", "USD/TRY", ""),
)

KONU_ARACLARI: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    "Borsa": (
        ("gosterge", "SP500", "S&P 500", ""),
        ("gosterge", "NASDAQCOM", "NASDAQ", ""),
        ("gosterge", "DJIA", "Dow Jones", ""),
    ),
    "Döviz": (
        ("gosterge", "DTWEXBGS", "Dolar endeksi", ""),
        ("gosterge", "DEXUSEU", "EUR/USD", ""),
    ),
    # PAXG tokenlestirilmis altin: spot altini yakindan izler ama LBMA
    # fiksingi degildir. Sembol ETIKETTEN kaldirildi -- "Altın (PAXG)"
    # okura bir sey anlatmiyor, kalabalik yapiyordu. Fark yok sayilmiyor:
    # kutunun altindaki notta yaziyor.
    "Altın ve emtia": (
        ("fiyat", "PAXGUSD", "Altın", "$"),
        ("gosterge", "DCOILBRENTEU", "Brent", "$"),
    ),
    "Enerji": (
        ("gosterge", "DCOILBRENTEU", "Brent", "$"),
        ("gosterge", "DCOILWTICO", "WTI", "$"),
    ),
    # Jeopolitik haberde okunacak yerler: arz riskinin fiyatlandigi
    # petrol, guvenli liman talebinin gorundugu altin ve risk istahini
    # ozetleyen oynaklik endeksi.
    "Jeopolitik": (
        ("gosterge", "DCOILBRENTEU", "Brent", "$"),
        ("fiyat", "PAXGUSD", "Altın", "$"),
        ("gosterge", "VIXCLS", "VIX", ""),
        ("gosterge", "DTWEXBGS", "Dolar endeksi", ""),
    ),
    "Kripto varlıklar": (
        ("fiyat", "XBTUSD", "Bitcoin", "$"),
        ("fiyat", "ETHUSD", "Ethereum", "$"),
    ),
    "Para politikası": (
        ("gosterge", "DGS2", "ABD 2 yıllık", "%"),
        ("gosterge", "DGS10", "ABD 10 yıllık", "%"),
        ("gosterge", "DTWEXBGS", "Dolar endeksi", ""),
    ),
    # Enflasyon haberinde okunacak asil yer tahvil piyasasi: getiri
    # egrisi, enflasyon beklentisinin fiyatlandigi ilk yerdir.
    "Enflasyon": (
        ("gosterge", "DGS2", "ABD 2 yıllık", "%"),
        ("gosterge", "DGS10", "ABD 10 yıllık", "%"),
        ("gosterge", "T10Y2Y", "10Y−2Y farkı", ""),
    ),
}

#: YURT ICI haberde kullanilan araclar. Yukaridaki tablo ABD verisi icin
#: yazildi ve olculen sonuc suydu:
#:
#:   TCMB'nin "Aylik Fiyat Gelismeleri (Temmuz 2026)" duyurusunun
#:   sayfasinda piyasa kutusu ABD 2 yillik, ABD 10 yillik ve 10Y-2Y
#:   farkini gosteriyordu.
#:
#: Turkiye enflasyon haberinde okunacak yer ABD tahvili degil; TL kuru,
#: yurt ici fonlama maliyeti ve enflasyonun kendisi. Konu ayni, BOLGE
#: farkli -- arac secimi ikisine birden bakmali.
YERLI_ARACLAR = {
    "Enflasyon": (
        ("gosterge", "TP.TUKFIY2025.GENEL", "TÜFE (yıllık)", "%"),
        ("gosterge", "TP.FE25.OKTG04", "Çekirdek (C)", "%"),
        ("gosterge", "TP.APIFON4", "TCMB fonlama", "%"),
        ("gosterge", "TP.DK.USD.S.YTL", "USD/TRY", ""),
    ),
    "Para politikası": (
        ("gosterge", "TP.APIFON4", "TCMB fonlama", "%"),
        ("gosterge", "TP.TUKFIY2025.GENEL", "TÜFE (yıllık)", "%"),
        ("gosterge", "TP.DK.USD.S.YTL", "USD/TRY", ""),
    ),
    "Bankacılık": (
        ("gosterge", "TP.APIFON4", "TCMB fonlama", "%"),
        ("gosterge", "TP.DK.USD.S.YTL", "USD/TRY", ""),
    ),
    "Döviz": (
        ("gosterge", "TP.DK.USD.S.YTL", "USD/TRY", ""),
        ("gosterge", "TP.DK.EUR.S.YTL", "EUR/TRY", ""),
        ("gosterge", "DTWEXBGS", "Dolar endeksi", ""),
    ),
    "Dış ticaret": (
        ("gosterge", "TP.HARICCARIACIK.K1", "Cari denge", ""),
        ("gosterge", "TP.DK.USD.S.YTL", "USD/TRY", ""),
        ("gosterge", "DCOILBRENTEU", "Brent", "$"),
    ),
    "İstihdam ve ücret": (
        ("gosterge", "TP.YISGUCU2.G8", "İşsizlik", "%"),
        ("gosterge", "TP.TUKFIY2025.GENEL", "TÜFE (yıllık)", "%"),
    ),
}

#: Konum skorunun bilesenleri -- sayfada da bu sirayla anlatiliyor.
#: Bes bilesen: uc ortalamanin uzerinde olmak + iki ortalama sirasi.
SKOR_BILESEN = 5


def _basamak(d: float) -> int:
    """Ondalik basamak sayisi buyuklukten turetilir.

    Sabit basamak iki ucta da bilgi kaybediyordu: dolar endeksi 120,71
    iken "120" cikiyor ve uc EMA'nin ucu de "120" gorunuyordu -- birbirinden
    ayirt edilemez. EUR/USD'de 1,15 yetmez, kur dort haneyle kotelenir.
    """
    a = abs(d)
    if a < 10:
        return 4
    if a < 1000:
        return 2
    return 0


def _sayi(d: float, birim: str) -> str:
    """Turkce bicim: binlik nokta, ondalik virgul."""
    m = f"{d:,.{_basamak(d)}f}"
    m = m.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{birim}{m}" if birim == "$" else (f"%{m}" if birim == "%" else m)


def _yuzde(d: float) -> str:
    m = f"{abs(d):.1f}".replace(".", ",")
    return f"{'+' if d >= 0 else '−'}%{m}"


def _seri_cek(b: sqlite3.Connection, kaynak: str,
              kod: str) -> tuple[list[float], list[str]]:
    tablo, sutun, anahtar = (
        ("gosterge", "deger", "kod") if kaynak == "gosterge"
        else ("fiyat", "kapanis", "sembol")
    )
    satirlar = b.execute(
        f"SELECT {sutun}, tarih FROM {tablo} WHERE {anahtar} = ? ORDER BY tarih",
        (kod,),
    ).fetchall()
    temiz = [(s[0], s[1]) for s in satirlar if s[0] is not None]
    return [t[0] for t in temiz], [t[1] for t in temiz]


#: Bir gozlem bu kadar gunden eskiyse sayfada "son veri" notu dusuluyor.
#:
#: Sebep olculdu: FRED'in Brent serisi bir hafta gecikmeli yayimlaniyor.
#: 4 Agustos tarihli bir haberin altinda 27 Temmuz'un Brent fiyatini
#: tarihsiz basmak, okura bugunku fiyati gostermek olurdu.
BAYAT_GUN = 3


def _arac_hesapla(degerler: list[float], tarihler: list[str],
                  ad: str, birim: str, bugun: str) -> dict | None:
    """Tek arac icin kutu satiri. Veri yetersizse None."""
    if teknik is None or len(degerler) < 21:
        return None

    son = degerler[-1]
    onceki = degerler[-2]
    gunluk = (son - onceki) / onceki * 100 if onceki else 0.0
    son_tarih, onceki_tarih = tarihler[-1], tarihler[-2]

    from datetime import date
    try:
        yas = (date.fromisoformat(bugun) - date.fromisoformat(son_tarih)).days
    except ValueError:
        yas = 0

    ortalamalar = []
    puan = 0
    olculen = 0
    ema_degerleri: dict[int, float] = {}

    for n in PENCERELER:
        if len(degerler) < n:
            continue
        seri = teknik.ema_serisi(degerler, n)
        if not seri:
            continue
        e = seri[-1]
        ema_degerleri[n] = e
        olculen += 1
        if son > e:
            puan += 1
        ortalamalar.append({
            "ad": f"EMA {n}",
            "deger": _sayi(e, birim),
            "fark": _yuzde((son - e) / e * 100),
            "yon": "artis" if son >= e else "azalis",
        })

    # Ortalamalarin KENDI sirasi da trend bilgisi: kisa vadeli ortalama
    # uzunun uzerindeyse yukseliyor demektir.
    sira_bileseni = 0
    if 20 in ema_degerleri and 50 in ema_degerleri:
        sira_bileseni += 1
        if ema_degerleri[20] > ema_degerleri[50]:
            puan += 1
    if 50 in ema_degerleri and 200 in ema_degerleri:
        sira_bileseni += 1
        if ema_degerleri[50] > ema_degerleri[200]:
            puan += 1

    toplam = olculen + sira_bileseni
    if not toplam:
        return None

    return {
        "ad": ad,
        "deger": _sayi(son, birim),
        "gunluk": _yuzde(gunluk),
        "gunluk_yon": "artis" if gunluk >= 0 else "azalis",
        "tarih": _tarih_tr(son_tarih),
        "onceki_tarih": _tarih_tr(onceki_tarih),
        "bayat": yas > BAYAT_GUN,
        "ortalamalar": ortalamalar,
        "skor": round(puan / toplam * 100),
        "skor_pay": puan,
        "skor_payda": toplam,
        "eksik_ortalama": len(PENCERELER) - olculen,
    }


_AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _tarih_tr(iso: str) -> str:
    try:
        y, a, g = (int(p) for p in iso.split("-"))
        return f"{g} {_AYLAR[a - 1]}"
    except (ValueError, IndexError):
        return iso


def turkiye(bugun: str = "") -> list[dict]:
    """Turkiye gostergeleri -- son deger, onceki donem, degisim.

    EMA yok: aylik yayimlanan bir enflasyon serisinde "200 gunluk
    ortalama" anlamsiz olurdu.
    """
    if not DEPO.exists():
        return []
    satirlar = []
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            for kod, ad, birim in TURKIYE_GOSTERGELERI:
                d, t = _seri_cek(b, "gosterge", kod)
                if len(d) < 2:
                    continue
                fark = d[-1] - d[-2]
                # Yuzde cinsinden bir seride "yuzde degisim" yaniltir:
                # %31,75'ten %31,40'a inis "%1,1 dusus" degil, 35 baz
                # puanlik bir GERILEME. Oran serilerinde fark, duzey
                # serilerinde yuzde gosteriliyor.
                if birim == "%":
                    degisim = f"{fark:+.2f} puan".replace(".", ",")
                else:
                    o = d[-2]
                    degisim = _yuzde((d[-1] - o) / o * 100) if o else "—"
                satirlar.append({
                    "ad": ad,
                    "deger": _sayi(d[-1], birim),
                    "degisim": degisim,
                    "yon": "artis" if fark >= 0 else "azalis",
                    "tarih": _tarih_tr(t[-1]),
                    "onceki_tarih": _tarih_tr(t[-2]),
                })
    except sqlite3.Error:
        return []
    return satirlar


def kutu(konu: str, bugun: str = "", yerli: bool = False) -> dict | None:
    """Konuya gore piyasa kutusu. Veri yoksa None -- kutu basilmaz.

    `yerli` verildiginde once YERLI_ARACLAR'a bakilir: ayni konunun
    yurt ici haberinde okunacak yer farklidir. Yerli karsiligi olmayan
    konu genel tabloya duser.
    """
    araclar = (YERLI_ARACLAR.get(konu) if yerli else None) \
        or KONU_ARACLARI.get(konu)
    if not araclar or not DEPO.exists():
        return None

    if not bugun:
        from datetime import date
        bugun = date.today().isoformat()

    satirlar = []
    notlar = []
    try:
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            for kaynak, kod, ad, birim in araclar:
                degerler, tarihler = _seri_cek(b, kaynak, kod)
                s = _arac_hesapla(degerler, tarihler, ad, birim, bugun)
                if s:
                    satirlar.append(s)
                    if kod in ARAC_NOTLARI:
                        notlar.append(ARAC_NOTLARI[kod])
    except sqlite3.Error:
        return None

    if not satirlar:
        return None
    return {
        "satirlar": satirlar,
        "notlar": notlar,
        # Bir aracin bile 200 gunlugu eksikse okura soyleniyor.
        "eksik_var": any(s["eksik_ortalama"] for s in satirlar),
        "bayat_var": any(s["bayat"] for s in satirlar),
    }
