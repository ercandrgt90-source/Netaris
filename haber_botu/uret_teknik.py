"""Teknik gorunum hatti -- ucretsiz, API cagrisi yok, bastan sona otomatik.

    Binance klines -> gosterge hesabi -> KOD ILE YAZI -> tarama -> site

KAPSAM
------
Yalnizca kripto ve tokenlestirilmis altin. Sebebi veri:

  * BIST hissesi   : fiyat gecmisi lisansli, ucretsiz kaynak yok
  * Gumus          : borsalarda paritesi yok, FRED'de gunluk seri yok,
                     Stooq bot dogrulamasi calistiriyor

VERI KAYNAGI: Kraken. Binance ABD IP'lerini HTTP 451 ile engelledigi ve
GitHub Actions sunuculari ABD'de oldugu icin otomasyonda calismiyordu.

Ucretsiz ve mesru kaynak bulunana kadar bu varliklar icin teknik icerik
uretilmez. Veri olmadan gosterge uretmek, uydurmakla ayni sey olurdu.

Kullanim:
    python uret_teknik.py                 # butun varliklar, arsive
    python uret_teknik.py --yayinla       # site icerigine de yaz
    python uret_teknik.py --sembol BTCUSDT
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "analiz"))
sys.path.insert(0, str(_KOK / "ai"))
sys.path.insert(0, str(_KOK / "kaynak"))

import kraken  # noqa: E402
import guvenlik  # noqa: E402
import prompt  # noqa: E402
import teknik  # noqa: E402
import yayin  # noqa: E402
import yazar_teknik  # noqa: E402

ARSIV = _KOK / "ciktilar"

#: Gunluk mum, 260 gun -- 200 gunluk ortalama icin yeterli pay
ARALIK = "1d"
MUM_SAYISI = 260


def _isle(sembol: str, yayinla: bool) -> int:
    ad = kraken.VARLIKLAR.get(sembol, (sembol,))[0]
    print("=" * 70)
    print(f"{ad} ({sembol})")
    print("=" * 70)

    try:
        seri = kraken.klines(sembol, ARALIK, MUM_SAYISI)
    except (kraken.VeriYok, Exception) as e:
        print(f"VERI CEKILEMEDI: {type(e).__name__}: {e}")
        return 1

    r = teknik.hesapla(seri)
    print(f"{r.mum_sayisi} mum  |  fiyat {r.fiyat:,.2f}")
    print(f"  RSI(14)      {r.rsi14:.1f}" if r.rsi14 is not None else "  RSI yok")
    if r.macd_histogram is not None:
        print(f"  MACD hist    {r.macd_histogram:+.2f}")
    if r.sma200 is not None:
        print(f"  SMA 20/50/200  {r.sma20:,.0f} / {r.sma50:,.0f} / {r.sma200:,.0f}")
    print(f"  destek {len(r.destek)}, direnc {len(r.direnc)} seviye")

    govde = yazar_teknik.yaz(r)
    # Tarama yayimlanan sayfanin hali uzerinden -- yasal uyari altbilgide
    metin = f"{govde}\n\n{prompt.UYARI_METNI_SKORSUZ}\n"

    print(f"\nyazi: {len(govde.split())} kelime, maliyet $0.00")
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    (ARSIV / f"teknik-{r.kisa}.md").write_text(metin, encoding="utf-8")

    if not tamam:
        print("DURUM: ENGELLENDI -- site icerigine yazilmadi")
        return 1

    if yayinla:
        # Grafik: son 90 gunun kapanis serisi
        seriler = ";".join(
            f"{d:.2f}".replace(".", ",") for d in seri.kapanislar[-90:]
        )
        dosya = yayin.yaz_makro(
            govde,
            konu=f"{r.kisa} teknik görünüm",
            kaynak="Kraken kamuya açık piyasa verisi",
            grafik=seriler,
            grafik_kod=r.ad,
            grafik_birim="USD",
            kategori="Teknik Görünüm",
            kod=r.kisa,
            kaynaklar="Kraken",
            sayimlar=";".join([
                f"{r.mum_sayisi}|günlük mum",
                f"{len(r.destek) + len(r.direnc)}|fiyat seviyesi",
                "7|hesaplanan gösterge",
                "90|günlük pencere",
            ]),
        )
        print(f"site icerigi: {dosya.relative_to(_KOK.parent)}")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description="Teknik gorunum hatti")
    a.add_argument("--sembol", help="tek varlik, ornek: BTCUSDT")
    a.add_argument("--yayinla", action="store_true")
    args = a.parse_args()

    semboller = [args.sembol] if args.sembol else list(kraken.VARLIKLAR)
    hatali = sum(_isle(s, args.yayinla) for s in semboller)
    print(f"\n{len(semboller)} varlik, {len(semboller) - hatali} basarili")
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
