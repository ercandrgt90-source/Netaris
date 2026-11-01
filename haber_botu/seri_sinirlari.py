"""Gosterge degerleri icin akla yatkinlik sinirlari -- TEK KAYNAK.

NEDEN AYRI DOSYA
----------------
Bu sinirlar `denetim.py` icinde duruyordu ve YALNIZCA denetim onlari
okuyordu. Yazicilar (`beyin.gosterge_yaz`, `veri_dogrula --duzelt`)
hicbir sinir tanimiyordu. Sonucu olculdu:

  2026-11-01 -- son BASARILI kosu 07:23 UTC (#2438). Hemen sonra
  TCMB EVDS, TP.FE25 grubunu bozuk dondurmeye
  basladi. Ayni seri kodu bir ay yillik degisimi (%31,88), ertesi ay
  aylik degisimi (%1,46) veriyor. Butun grup (OKTG01..OKTG08) ayni
  bicimde bozuk; yani kaynak arizasi, tek seri sorunu degil.

  `veri_dogrula --duzelt` kaynagi KOSULSUZ dogru sayiyor: depo ile
  kaynak ayrisirsa depoyu kaynaga gore eziyor. TP.FE25.OKTG04'un
  48 gozlemi -- 2022-10'a kadar geriye -- cople degistirildi.
  2026-09 degeri %28,71'den %-39,22'ye dondu.

  `denetim.py` -- DOGRU davranarak -- "-39,22 seri sinirinin disinda"
  dedi ve yayini durdurdu. Ama yayin karari TUM siteyi kapsiyor:
  haber, piyasa, bilanco, her sey. Site bes saat yerde kaldi. Tek bir
  ucuncu taraf serisi butun yayini durdurdu.

Iki ayri kusur vardi ve ikisi de burada kapaniyor:

  1. YAZICI, DENETLEYENIN OLCUTUNU KULLANMIYORDU. Denetimin
     reddedecegi bir deger depoya hic girmemeli. `sinir_disi()` artik
     yazma yolunda da cagriliyor.

  2. "DUZELTME" SORGUSUZ KABUL EDILIYORDU. Kaynagin degismesi ile
     depomuzun yanlis olmasi ayni sey degil. `GERILEME_ESIGI` bunu
     ayiriyor: mesru revizyon son birkac gozleme dokunur, 48 gozlemi
     dort yil geriye dogru yeniden yazan sey revizyon degil kaynak
     gerilemesidir.

Sinirlarin amaci UC DEGERLERI degil BIRIM/ANLAM hatalarini yakalamak.
Cok dar sinir surekli alarm verir ve alarmi degersizlestirir.
"""

from __future__ import annotations

import json
import pathlib

#: Reddedilen "duzeltmelerin" kalici kaydi.
#:
#: Adimin cikti kuyrugu kisa (basarili adimda son 6 satir) -- yani
#: koru koruna basarili gorunen bir adim 48 gozlemi bozarken EKRANDA
#: HICBIR SEY GORUNMEDI. Kalici kayit bunu kapatiyor: `denetim.py`
#: dosyayi okuyup UYARI olarak raporluyor ve `gosterge_yaz` ayni
#: kaydi okuyup karantinadaki serinin YENI gozlemlerini de reddediyor.
KARANTINA = pathlib.Path(__file__).resolve().parent / "kaynak" \
    / "seri_karantina.json"

#: birim -> (alt, ust, okunabilir ad)
ARALIK: dict[str, tuple[float, float, str]] = {
    "%": (-100.0, 200.0, "yüzde"),
    "bin kişi": (-20000.0, 500000.0, "bin kişi"),
    "kişi": (-5_000_000.0, 400_000_000.0, "kişi"),
    "mn $": (-100_000.0, 100_000.0, "milyon dolar"),
    "$": (0.0, 100_000.0, "dolar"),
    "TL": (0.0, 10_000.0, "lira"),
    "bin adet": (0.0, 10_000.0, "bin adet"),
    "endeks": (0.0, 100_000.0, "endeks"),
}

#: Seriye ozgu daha dar sinir. Genel birim sinirinin kacirdiklari icin.
SERI_ARALIK: dict[str, tuple[float, float]] = {
    "UNRATE": (0.0, 40.0),
    "ICSA": (0.0, 10_000_000.0),
    # NSA seriler manset icin kullaniliyor (bkz. takvim.SERILER);
    # SA olanlar gecmis kayitlarda duruyor, ikisinin de siniri ayni.
    "CPIAUCNS": (-30.0, 150.0),
    "CPILFENS": (-30.0, 150.0),
    "CPIAUCSL": (-30.0, 150.0),
    "CPILFESL": (-30.0, 150.0),
    "PCEPILFE": (-30.0, 150.0),
    "PPIFIS": (-40.0, 200.0),
    "CES0500000003": (-50.0, 100.0),
    "MICH": (0.0, 30.0),
    "GDPC1": (-30.0, 30.0),
    "RSAFS": (-50.0, 100.0),
    "INDPRO": (-40.0, 60.0),
    # --- Turkiye ---
    "TP.YISGUCU2.G8": (0.0, 60.0),
    "TP.APIFON4": (0.0, 100.0),
    "TCMB_POLITIKA": (0.0, 100.0),
    "TP.TUKFIY2025.GENEL": (-30.0, 300.0),
    "TP.FE25.OKTG04": (-30.0, 300.0),
    "TP.TUFE1YI.T1": (-30.0, 400.0),
    "TP.ENFBEK.PKA12ENF": (0.0, 200.0),
    "TP.ENFBEK.HBA12ENF": (0.0, 200.0),
    "TP.ENFBEK.IYA12ENF": (0.0, 200.0),
    # --- Avrupa ---
    # BIRIMSIZ yazilan seri: birim siniri uygulanamiyor, dolayisiyla
    # kendi siniri OLMAK ZORUNDA. EUR/USD 1973'ten bu yana 0,64-1,60
    # bandinda kaldi; sinir birim/olcek hatasini (1,08 yerine 108)
    # yakalayacak kadar dar, piyasayi yanlis suclamayacak kadar genis.
    "ECB_EURUSD": (0.3, 3.0),
    # Almanya 10 yillik getirisi: 2020'de -0,85'e kadar indi.
    "BBK_DE10Y": (-5.0, 25.0),
}

#: Bir KOSUDA tek serinin kac gozlemi "duzeltilebilir".
#:
#: Olculdu: mesru revizyonlar son bir-iki gozleme dokunuyor (FRED
#: endeksleri bir sonraki yayinda guncellenir). 2026-11-01'de bozuk
#: kaynak TEK serinin 48 gozlemini -- 2022-10'a kadar -- yeniden
#: yazdi. Esik ikisinin arasinda ve bilerek genis: gercek bir
#: birim gocu (CPIAUCSL olayi) elle `--gerilemeyi-yok-say` ile
#: yapilabilir, otomasyon bunu KENDILIGINDEN yapamaz.
GERILEME_ESIGI = 8


def sinir_disi(kod: str, deger: float, birim: str = "") -> str:
    """Deger sinirlarin disindaysa SEBEBI, degilse "" doner.

    Once seriye ozgu sinir, yoksa birim siniri bakilir. Hicbiri
    tanimli degilse "" doner -- tanimsiz sinir, gecersiz deger
    demek degil.
    """
    try:
        d = float(deger)
    except (TypeError, ValueError):
        return "sayi degil"
    if d != d or d in (float("inf"), float("-inf")):   # NaN / sonsuz
        return "sayi degil"

    ozel = SERI_ARALIK.get(kod)
    if ozel is not None:
        if not (ozel[0] <= d <= ozel[1]):
            return (f"{d} seri sinirinin disinda ({ozel[0]}..{ozel[1]}) "
                    f"-- birim/sunum hatasi olabilir")
        return ""

    sinir = ARALIK.get(birim or "")
    if sinir is not None and not (sinir[0] <= d <= sinir[1]):
        return (f"{d} {birim} makul araligin disinda "
                f"({sinir[0]}..{sinir[1]} {sinir[2]})")
    return ""


def gerileme_mi(sayi: int) -> bool:
    """Tek seride bu kadar gozlemin degismesi revizyon mu, geri
    gidis mi? Esigin USTU kaynak gerilemesi sayilir."""
    return sayi > GERILEME_ESIGI


def karantina_yaz(kayitlar) -> None:
    """Karantina kaydini yazar. Bos listede de YAZAR, silmez.

    `kayitlar`: (kod, sebep) ikilileri.

    SILMIYOR, cunku geri yazma listesi `[ -e "$y" ]` ile suzuluyor:
    silinen dosya listeye hic girmez, yani silme CI'da hicbir zaman
    gonderilmez ve depodaki eski karantina sonsuza kadar uyari
    uretirdi. Bos kayit ise gonderilir ve uyariyi kaldirir.

    Bos kayitta zaman damgasi YOK: boylece her kosuda ayni icerik
    uretilir ve temiz gunler commit gurultusu yapmaz.

    DEGISMEDIYSE DOKUNULMUYOR. Ilk surumde `an` her kosuda
    yenileniyordu; olculdu: haber hatti on dakikada bir kostugu icin
    dosya gunde 144 kez, YALNIZCA zaman damgasi yuzunden commit'e
    giriyordu. Daha onemlisi `an`in anlami yanlisti -- "ne zaman
    oldu" gibi okunuyor ama "en son ne zaman goruldu" demek
    oluyordu. Artik sebepler kumesi ayniysa dosya oldugu gibi
    kaliyor, yani `an` karantinanin BASLADIGI an.
    """
    kayitlar = list(kayitlar)
    try:
        KARANTINA.parent.mkdir(parents=True, exist_ok=True)
        if kayitlar:
            from datetime import datetime, timezone
            yeni_sebep = [s for _k, s in kayitlar]
            onceki = _karantina_oku()
            if (onceki.get("sebepler") or []) == yeni_sebep:
                return
            yuk = {
                "an": datetime.now(timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "seriler": sorted({k for k, _s in kayitlar}),
                "sebepler": yeni_sebep,
            }
        else:
            yuk = {"seriler": [], "sebepler": []}
        KARANTINA.write_text(
            json.dumps(yuk, ensure_ascii=False, indent=1) + chr(10),
            encoding="utf-8")
    except OSError:
        pass
    karantinadakiler.cache_clear()


def _karantina_oku() -> dict:
    try:
        return json.loads(KARANTINA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def karantinadakiler() -> frozenset:
    """Kaynagi bozuk oldugu OLCULEN serilerin kodlari.

    NEDEN YENI GOZLEM DE REDDEDILIYOR: `veri_dogrula` yalnizca
    depoda ZATEN olan tarihleri kaynakla karsilastiriyor; yeni bir
    tarih icin karsilastiracak sey yok. Siniri gecen ama YANLIS bir
    deger (bozuk kaynak %23,39 dondurdu, dogrusu %28,71 civari) bu
    yuzden hicbir kontrole takilmadan yayimlanirdi.

    Burada esik yok, OLCUM var: seri zaten "kaynagi baska bir
    buyukluk dondurüyor" diye isaretli. Kaynak duzelip depoyla
    uyusunca kayit kendiliginden bosaliyor ve seri geri aciliyor.
    """
    return frozenset(_karantina_oku().get("seriler") or ())


# `lru_cache` surec basina bir kez okusun; `karantina_yaz` temizliyor.
def _onbellekle(fn):
    import functools
    sarili = functools.lru_cache(maxsize=1)(fn)
    return sarili


karantinadakiler = _onbellekle(karantinadakiler)
