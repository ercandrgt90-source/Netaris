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

    # BILANCO SAYFALARI -- veri cekildikten SONRA.
    #
    # Sinir kucuk (varsayilan 5): 324 sirketi tek kosuda yayimlamak
    # geri alinmasi zor bir islem ve 324 model cagrisi demek. Her
    # kosuda birkac sayfa ekleniyor, hat kendini zamanla dolduruyor.
    #
    # Sayfasi olan sirket ATLANIYOR; ayni sayfayi yeniden yazmak ayni
    # cagriyi ikinci kez odemek olurdu.
    #
    # YORUMSUZ SAYFA YAYIMLANMIYOR: AI saglayicisi yoksa adim sifir
    # sayfa yazip gecmis oluyor -- hata degil, kural.
    if "bilanco_sayfa" not in args.atla:
        adimlar.append(("Bilanço sayfaları (tablo + AI yorumu)",
                        [str(BOT / "uret_bilanco_sayfa.py")]))

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

    # YORUM DENETIMI DAGITIMDAN ONCE -- oncesinde SONRASINDAYDI.
    #
    # `yorum_denetimi.py` is akisinda dagitimin ARDINDAN kosuyordu:
    # icerik once yayina cikiyor, sonra CI kirmiziya donuyordu. Ve
    # `--temizle` bilincli olarak otomatik degil ("kosunun sessizce
    # icerik silmesi istenmiyor"), yani duzeltme elle yapilmali.
    #
    # Olculdu (2026-08-23): 8 ihlal YAYINDA duruyordu. Denetim
    # calisiyordu, yakaliyordu, CI kirmiziya donuyordu -- ama kimse
    # elle temizlemedigi icin sayfalarda kaliyordu.
    #
    # Yani koruma KAPIDAN SONRA duruyordu. Simdi once kosuyor:
    # dogrulanamayan sayi tasiyan bir yorum varsa DAGITIM YAPILMIYOR.
    #
    # `--temizle` ARTIK OTOMATIK -- ama yalnizca BIR KEZ ve ardindan
    # yeniden dogrulanarak.
    #
    # NEDEN DEGISTI
    # Onceki kural "ihlal varsa dagitma, temizligi insan yapsin"di ve
    # gerekcesi makuldu: kosu sessizce icerik silmesin. Olculen sonuc
    # baska cikti.
    #
    # 2026-08-24: kullanici "haberler akmiyor" dedi. Canli sitede en
    # yeni haber BIR GUN eskiydi; oysa CI saat basi haber topluyor ve
    # o gune ait altmis dokuz haber depoda duruyordu. Zincir:
    #
    #     yorum_denetimi.py -> 18 ihlal, cikis 1
    #     ok = False        -> `if args.yayinla and ok:` hic calismadi
    #
    # Kimse elle temizlemedi, cunku kimse kirmizi CI kaydina bakmiyor.
    # "Eski site ayakta kalir" varsayimi kagit uzerinde zararsizdi;
    # pratikte site DONDU ve bunu ancak okur fark etti.
    #
    # NEDEN SILMEK ARTIK GUVENLI
    # Kapi artik URETILEN SAYFAYI olcuyor (bkz. `yorum_denetimi.
    # sayfa_yorumu`). Bir ihlal buluyorsa, o metin GERCEKTEN okura
    # gidiyor demektir ve tanimi geregi dogrulanamaz. Silinen sey
    # kalici da degil: bir sonraki uretim duzeltilmis girdiyle
    # yeniden yaziyor.
    #
    # NEDEN TEK DENEME
    # Temizlikten sonra hala ihlal cikiyorsa sorun tek bir yorumda
    # degil, uretim hattindadir. Orada dagitimi durdurmak DOGRU --
    # ve dongude donup durmamak icin ikinci deneme yok.
    if ok:
        yd, _ = _calistir("Yorum sayıları sayfada mı",
                          [str(BOT / "yorum_denetimi.py")])
        if not yd:
            print()
            print("  IHLAL BULUNDU -- yorumlar temizlenip site yeniden")
            print("  uretiliyor. Haber akisi bir icerik hatasi yuzunden")
            print("  durmamali; dogrulanamayan yorum ise yayina cikmamali.")
            _calistir("Yorumları temizle",
                      [str(BOT / "yorum_denetimi.py"), "--temizle"])
            ok, _ = _calistir("Site üretimi (temizlik sonrası)",
                              [str(SITE / "insa.py")])
            sonuclar["Site üretimi"] = ok
            if ok:
                yd, _ = _calistir("Yorum sayıları sayfada mı (2. tur)",
                                  [str(BOT / "yorum_denetimi.py")])
        sonuclar["Yorum denetimi"] = yd
        if not yd:
            print()
            print("  TEMIZLIKTEN SONRA DA IHLAL VAR -- dagitim YAPILMADI.")
            print("  Sorun tek bir yorumda degil, uretim hattinda.")
            print("  Bakilacak yer: site/insa.py -> _yorum_dogrulanabilir")
            ok = False

    if args.yayinla and ok:
        y, _ = _calistir("Cloudflare dağıtımı", [str(SITE / "yayinla.py")])
        sonuclar["Dağıtım"] = y
        if y:
            d, _ = _calistir("Doğrulama", [str(SITE / "dogrula.py")])
            sonuclar["Doğrulama"] = d
    elif args.yayinla:
        print("\n  Site uretimi basarisiz -- dagitim YAPILMADI")

    # TAZELIK KONTROLU KOSULSUZ -- dagitim atlansa da kosar.
    #
    # NEDEN: site iki gun icinde iki kez sessizce dondu ve ikisini de
    # once KULLANICI fark etti. Sebepler tamamen farkliydi (bir kez
    # `yayinla.py` cokuyordu, bir kez yorum kapisi dagitimi
    # engelliyordu) ama sonuc ayniydi: haber toplaniyor, okura
    # ulasmiyor.
    #
    # Bu kontrol sebebe hic bakmiyor, yalnizca okurun gordugu seye
    # bakiyor. `dogrula.py` bunu yapamaz: o yalnizca BASARILI bir
    # dagitimdan sonra kosuyor, yani "dagitim hic olmadi" durumunu
    # tanimi geregi goremiyor.
    #
    # `sonuclar`a KONMUYOR: donus degeri kosunun basarisini
    # belirlememeli. Bayatlik bu kosunun urettigi bir sey degil,
    # onceki kosularin birakip gittigi bir durum -- ve bugunku kosu
    # dogru calistiysa kirmizi donmesi yaniltici olurdu.
    if args.yayinla:
        _calistir("Canlı site tazeliği", [str(SITE / "tazelik.py")])

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
