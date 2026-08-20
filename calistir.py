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


def _ozet(sonuclar: dict) -> None:
    """Adim ozeti. Denetim isi erken dusurdugunde de basiliyor."""
    print("\n" + "=" * 68)
    print("  ÖZET")
    print("=" * 68)
    for baslik, durum in sonuclar.items():
        print(f"  {'✓' if durum else '✗'}  {baslik}")


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
    # VERI DOGRULAMA -- makro cekildikten hemen SONRA, haber
    # uretilmeden ONCE.
    #
    # Sirasi kritik: yanlis bir gozlem depoya girdiginde ondan baslik,
    # AI yorumu ve dosya bulgusu tureiyor. Zincirin basinda yakalamak,
    # sonunda temizlemekten cok daha ucuz -- olculdu, 31 sapan deger
    # 23 veri haberinin ikisinin basligina ve iki AI yorumuna
    # islenmisti.
    #
    # `--duzelt` ile calisiyor: sapma bulunursa DEPODA duzeltiliyor ve
    # hat devam ediyor. Durdurmak yerine duzeltmek dogru, cunku sapma
    # cogu zaman kaynaktaki revizyondan geliyor ve o revizyonu almak
    # zaten istedigimiz sey.
    if "dogrula" not in args.atla:
        adimlar.append(("Veri doğrulama (depo ↔ kaynak)",
                        [str(BOT / "veri_dogrula.py"), "--duzelt"]))

    # BILANCO HATTI -- KENDI TAKVIMINE GORE.
    #
    # Adim her kosuda cagriliyor ama `uret_bilanco` icindeki takvim
    # kapisi bildirim ayi degilse hemen donuyor. Sirketler mali
    # tablolarini yilda dort kez bildiriyor; hattin yarim saatte bir
    # ~1000 istek atmasi hem kaynaga yuk hem bize maliyet, ve HICBIR
    # SEY degistirmez.
    #
    # Kapiyi burada degil modulde tutmanin sebebi: elle calistirmak
    # (`--zorla`) ile otomatik kosu ayni kodu kullansin. Iki yerde iki
    # takvim, bir gun ayrisir.
    if "bilanco" not in args.atla:
        adimlar.append(("Bilanço (sektör → mali tablo → medyan)",
                        [str(BOT / "uret_bilanco.py"), "--hepsi"]))

    # Turkiye makro verisi. Anahtar yoksa adim kendini atlar.
    if "evds" not in args.atla:
        adimlar.append(("Türkiye makro (TCMB EVDS)",
                        [str(BOT / "uret_evds.py")]))
    if "haber" not in args.atla:
        adimlar.append(("Haberler (RSS → çeviri → fotoğraf)",
                        # SINIR BURADA VERILMIYOR -- `uret_gundem.SINIR`
                        # gecerli.
                        #
                        # Once "--sinir 40" yaziyordu ve olculdu: modulde
                        # varsayilan 120'ye cikarildigi halde otomatik
                        # hat 40'ta kaldi, FinancialJuice kontenjani da
                        # 40'in yarisina (20) indi. Yani elle yapilan
                        # kurulum 120 haber uretirken, gercekte calisan
                        # hat 42 uretiyordu ve fark hicbir yerde
                        # gorunmuyordu.
                        #
                        # Ayni sayinin iki yerde yasamasi kacinilmaz
                        # olarak birinin unutulmasiyla bitiyor. Sayi
                        # modulde, gerekcesiyle birlikte duruyor.
                        [str(BOT / "uret_gundem.py"), "--yayinla"]))
    # Veri aciklamalari haberlerden HEMEN SONRA: gundem.json'u okuyup
    # ustune ekliyor. Ayri bir hat olmasinin sebebi kaynak turunun
    # farkli olmasi -- besleme RSS okur, bu hat VERI okur. RSS'te
    # olmayan haber siteye hic girmiyordu; 266 haberde tek bir ADP ya
    # da tarim disi istihdam kaydi yoktu.
    if "takvim" not in args.atla:
        adimlar.append(("Veri açıklamaları (FRED → haber)",
                        [str(BOT / "uret_takvim.py")]))

    # Olay motoru haberlerden SONRA calisir: haber akisini okuyup esigi
    # gecenler icin fiyat tepkisi olcuyor. Makro adimindan da sonra
    # olmali -- gecikmeli kalemleri gostergeler.json'dan aliyor.
    if "olay" not in args.atla:
        adimlar.append(("Olay motoru (haber → fiyat tepkisi → açıklama)",
                        [str(BOT / "uret_olay.py"), "--yayinla"]))

    # Uye yazilari haberlerden SONRA, site uretiminden ONCE. HAT_SIRRI
    # yoksa adim kendi kendini atlar ve hat kirmizi donmez -- uyelik
    # sistemi kapaliyken de site uretilebilmeli.
    if "uye" not in args.atla:
        adimlar.append(("Üye yazıları (onaylı → tarama → yayın)",
                        [str(BOT / "uret_uye_yazi.py")]))
    # AI yorumu haberlerden ve veri aciklamalarindan SONRA: girdisi
    # olculmus veri, dolayisiyla o veri hazir olmali. Site uretiminden
    # ONCE, cunku metin depoya yaziliyor ve sayfaya oradan gomuluyor.
    #
    # Anahtar yoksa adim kendini atlar ve hat kirmizi DONMEZ -- model
    # katmani coktugunde site yine kurulmali.
    if "aiyorum" not in args.atla:
        adimlar.append(("AI yorumu (ölçüm → çıkarım)",
                        [str(BOT / "uret_ai_yorum.py")]))

    # Varlik indeksi haberlerden SONRA, site uretiminden ONCE.
    #
    # Site kurulurken guncel pencere zaten indeksleniyor; bu adim ARSIVIN
    # TAMAMINI yeniden tariyor. Gerekli, cunku kalip listesi buyuyor:
    # bugun "bakir" kalibi eklendiginde dunku bakir haberi de o varliga
    # baglanmali, yoksa arsiv eksik kalir ve kimse fark etmez.
    if "varlik" not in args.atla:
        adimlar.append(("Varlık indeksi (haber → bilgi ağı)",
                        [str(BOT / "uret_varlik.py")]))
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

    # VERI DENETIMI SITE URETIMINDEN ONCE.
    #
    # Kullanici sayfada "Politika faizi %40" gordu; gercek politika
    # faizi %37 idi. Deger dogruydu, ETIKET yanlisti -- sayi fonlama
    # maliyeti serisinden geliyordu. Bir birim testi bunu yakalamaz
    # cunku kod dogru calisiyor; yakalayacak sey, yayimlanan sayiyi
    # TANIMIYLA karsilastiran bir denetim.
    #
    # HATA VARSA SITE URETILMIYOR: yanlis etiketli bir sayi
    # yayimlamaktansa site eski haliyle ayakta kalir. Uyari isi
    # dusurmuyor -- bayat veri kaynagin gecikmesi olabilir.
    denet, _ = _calistir("Veri denetimi", [str(BOT / "denetim.py")])
    sonuclar["Veri denetimi"] = denet
    if not denet:
        print("\n  VERI DENETIMI HATA VERDI -- site uretilmedi, "
              "dagitim yapilmadi.")
        sonuclar["Site üretimi"] = False
        _ozet(sonuclar)
        return 1

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

    _ozet(sonuclar)

    with beyin.baglan() as b:
        d = beyin.durum(b)
    print("\n  DEPO")
    print(f"  {d['gosterge_gozlem']} gösterge gözlemi, {d['gosterge_seri']} seri")
    print(f"  {d['haber']} haber ({d['haber_yayimlanan']} yayımlandı)")
    print(f"  {d['ceviri']} çeviri, {d['icerik']} içerik")

    return 0 if all(sonuclar.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
