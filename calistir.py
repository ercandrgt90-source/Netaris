"""Netaris tek komut -- butun hatlari sirayla calistirir ve yayimlar.

    python calistir.py            # topla, uret, insa et (yayimlamaz)
    python calistir.py --yayinla  # ustune Cloudflare'e dagit
    python calistir.py --durum    # yalnizca deponun ozetini bas

NE YAPAR
--------
  1. Makro gostergeler   FRED'den ceker, depoya yazar, panel verisi uretir
  2. Haberler            RSS -> ceviri -> siniflandirma -> fotograf -> sayfa
  3. Teknik gorunum      Binance mumlari -> gostergeler -> yazi
  4. Site                sablonlari isler, ciktiyi uretir
  5. Dagitim             (--yayinla ile) Cloudflare'e yukler ve dogrular

Bilanco hatti BURADA YOK: veri elle giriliyor (KAP otomatik cekilemiyor),
dolayisiyla zamanlanmis bir gorevde calistirmanin anlami olmaz.

HATA DAVRANISI
--------------
Bir hat coktugunde digerleri devam eder. Sebebi: gundem cekilemedi diye
teknik gorunumun de guncellenmemesi icin bir sebep yok. Her hattin durumu
depoya yazilir; "dun gece neden guncellenmedi" sorusunun cevabi orada.

ZAMANLAMA
---------
Windows'ta Gorev Zamanlayici, sunucuda cron. Ornek: gunde iki kez

    schtasks /create /tn "Netaris" /tr "python C:\\...\\calistir.py --yayinla"
             /sc daily /mo 1 /st 08:00
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).parent
BOT = KOK / "haber_botu"
SITE = KOK / "site"

sys.path.insert(0, str(BOT))
import beyin  # noqa: E402


def _calistir(baslik: str, komut: list[str]) -> tuple[bool, str]:
    """Alt sureci calistirir, ciktinin son satirlarini doner."""
    print(f"\n{'─' * 68}")
    print(f"  {baslik}")
    print("─" * 68)
    basla = time.time()
    try:
        s = subprocess.run(
            [sys.executable, *komut],
            cwd=str(KOK), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900,
        )
    except subprocess.TimeoutExpired:
        print("  ZAMAN ASIMI (15 dk)")
        return False, "zaman asimi"

    cikti = (s.stdout or "") + (s.stderr or "")
    satirlar = [x for x in cikti.splitlines() if x.strip()]
    for x in satirlar[-6:]:
        print(f"  {x}")
    sure = time.time() - basla
    ok = s.returncode == 0
    print(f"  {'tamam' if ok else 'HATA'} · {sure:.1f} sn")
    return ok, satirlar[-1] if satirlar else ""


def main() -> int:
    a = argparse.ArgumentParser(description="Netaris tek komut")
    a.add_argument("--yayinla", action="store_true", help="Cloudflare'e dagit")
    a.add_argument("--durum", action="store_true", help="yalnizca depo ozeti")
    a.add_argument("--atla", nargs="*", default=[],
                   help="atlanacak hatlar: makro haber teknik")
    args = a.parse_args()

    with beyin.baglan() as b:
        if args.durum:
            for k, v in beyin.durum(b).items():
                print(f"  {k:<22} {v}")
            return 0

    print("=" * 68)
    print("  NETARIS · tam calistirma")
    print("=" * 68)

    adimlar = []
    if "makro" not in args.atla:
        adimlar.append(("Makro göstergeler",
                        [str(BOT / "makro_uret_ucretsiz.py"), "--yayinla"]))
    if "haber" not in args.atla:
        adimlar.append(("Haberler (RSS → çeviri → fotoğraf)",
                        # TCMB eklenince aday sayisi 56'dan 116'ya cikti;
                        # 24'luk sinir yeni kaynagi gorunmez birakirdi.
                        [str(BOT / "uret_gundem.py"), "--yayinla", "--sinir", "40"]))
    if "teknik" not in args.atla:
        # Kraken cift adlari -- Bitcoin orada "XBT"
        for sembol in ("XBTUSD", "ETHUSD", "PAXGUSD"):
            adimlar.append((f"Teknik görünüm · {sembol}",
                            [str(BOT / "uret_teknik.py"),
                             "--sembol", sembol, "--yayinla"]))

    sonuclar: dict[str, bool] = {}
    for baslik, komut in adimlar:
        # Bir hat coktugunde digerleri DEVAM EDER -- gundem cekilemedi diye
        # teknik gorunumun de guncellenmemesi icin sebep yok
        ok, _ = _calistir(baslik, komut)
        sonuclar[baslik] = ok

    ok, _ = _calistir("Site üretimi", [str(SITE / "insa.py")])
    sonuclar["Site üretimi"] = ok

    if args.yayinla and ok:
        y, _ = _calistir("Cloudflare dağıtımı", [str(SITE / "yayinla.py")])
        sonuclar["Dağıtım"] = y
        if y:
            d, _ = _calistir("Doğrulama", [str(SITE / "dogrula.py")])
            sonuclar["Doğrulama"] = d
    elif args.yayinla:
        print("\n  Site uretimi basarisiz -- dagitim YAPILMADI")

    print("\n" + "=" * 68)
    print("  ÖZET")
    print("=" * 68)
    for baslik, durum in sonuclar.items():
        print(f"  {'✓' if durum else '✗'}  {baslik}")

    with beyin.baglan() as b:
        d = beyin.durum(b)
    print("\n  DEPO")
    print(f"  {d['gosterge_gozlem']} gösterge gözlemi, {d['gosterge_seri']} seri")
    print(f"  {d['haber']} haber ({d['haber_yayimlanan']} yayımlandı)")
    print(f"  {d['ceviri']} çeviri, {d['icerik']} içerik")

    return 0 if all(sonuclar.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
