"""Hicbir sinama, YALNIZCA ZAMAN GECTIGI ICIN kirmiziya donemez.

BU DOSYA NEDEN VAR
------------------
2026-09-14'te olculdu: site 1 Eylul 23:04'ten beri guncellenmiyordu.
On uc gun boyunca HER otomasyon kosusu ayni yerde, bir saniyede dustu.

Sebep `test_tazelik.py`de duran bir sinamaydi: "varlik sayfalarinin
serileri ritminde mi" diye soruyor ve CANLI DEPOYA bakiyordu.
`otomasyon.yml`de adim sirasi soyle:

    Testleri calistir          <- kapi
    Veri topla ve icerik uret  <- seriyi TAZELEYEN adim

Veri bayatlayinca sinama dustu, is akisi durdu, duran is akisi de
veriyi tazeleyemedi. Bir kez durunca sistem kendi kendine ASLA
toparlanamazdi. Nobetci dogru calisti, her yarim saatte tetikledi --
hepsi ayni kapiya carpti. Kurtarma duzenegi vardi ve kurtaramadi,
cunku engel kurtarmanin ICINDEYDI.

O sinama YAZILDIGI GUN yesildi. Kirmiziya donmesi icin tek gereken
zamanin gecmesiydi.

NE OLCULUYOR
------------
Butun sinama dosyalari, saati ILERI ALINMIS bir ortamda yeniden
kosuluyor. Bugun gecen bir sinama, altmis gun sonra da gecmeli. Aksi
halde o sinama bir zaman bombasidir: yazildigi gun yesil, ileride bir
gun kirmizi -- ve neden kirmiziya dondugu hicbir kod degisikligiyle
aciklanamaz.

Bu kural, `test_tazelik.py`nin eski halini YAZILDIGI GUN yakalardi.

SAAT NASIL KAYDIRILIYOR
-----------------------
`sitecustomize.py` yorumlayici acilirken kendiliginden ice aktariliyor
-- yani sinama dosyasina DOKUNMADAN, o dosyanin gordugu `datetime`
degistirilebiliyor. Shim gecici bir dizine yaziliyor; depoda kalici
bir dosya birakmiyor.

Calistirma:  python test_zaman_bombasi.py
"""

from __future__ import annotations

import datetime as _dt
import os
import pathlib
import subprocess
import sys
import tempfile

_gecti = 0
_kaldi: list[str] = []


def dogru(aciklama: str, kosul) -> None:
    global _gecti
    if kosul:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi.append(aciklama)
        print(f"  KALDI  {aciklama}")


KOK = pathlib.Path(__file__).resolve().parent.parent
BEN = pathlib.Path(__file__).resolve()

#: Saat kac gun ileri alinacak.
#:
#: 60 gun: bu depoda gorulen kilit 1,5 SAATTE olustu, yani kucuk bir
#: kayma bile yeterdi. Genis tutmak, yalnizca cok yavas bayatlayan
#: (ceyreklik, yillik) seriler icin yazilmis bir sinamayi da yakalar.
KAYMA_GUN = 60

#: GUNUN SAATI DE KAYDIRILIYOR -- 2026-09-22'de eklendi.
#:
#: Kural once YALNIZCA gun kaydiriyordu, yani gunun saati sabit
#: kaliyordu. Saate bagli bir zaman bombasi bu agdan gecti ve dort gun
#: uretimde kaldi:
#:
#:   20-22 Eylul arasi 00:00-02:00 UTC penceresinde acilan 21 kosunun
#:   21'i de KIRMIZI; o pencerenin disindaki 79 kosunun hepsi yesil.
#:   Gunde iki saat hicbir icerik uretilmiyordu.
#:
#: Sebep `test_insa.py`de "26 saat once" yazan bir kurguydu. 01:10'da
#: 26 saat geri gitmek DUNE degil ONCEKI GUNE dusuyor, kalem
#: `ONE_CIKAN_PENCERE`nin disinda kaliyor ve iddia bozuluyordu.
#:
#: NEDEN BU IKI SAAT: kusur gun sinirinda yasiyor. 00:30 "tarih YENI
#: DONDU" durumunu, 23:30 "tarih DONMEK UZERE" durumunu kapsiyor.
#: Aradaki saatler bu iki ucun arasinda kaliyor; olculdu, gecis basina
#: ~37 saniye, yani her saati taramak hem pahali hem gereksiz.
#:
#: SAAT UTC'YE GORE: CI kosucusu UTC'de calisiyor ve kusur da UTC gun
#: sinirinda yasandi. Yerel makinede saat dilimi farkli olabilir; o
#: durumda naive `datetime.now()` kullanan sinamalar baska bir saatte
#: konumlanir ama UTC kullananlar -- kusurun ciktigi yer -- ayni.
SENARYO = (
    (0, 30, "gece yarisindan HEMEN SONRA"),
    (23, 30, "gece yarisindan HEMEN ONCE"),
)

SHIM = '''
import datetime as _d
import os

_s = int(os.environ.get("SAHTE_SANIYE", "0"))
if _s:
    _K = _d.timedelta(seconds=_s)
    _T, _Z = _d.date, _d.datetime

    class date(_T):
        @classmethod
        def today(cls):
            return (_Z.now() + _K).date()

    class datetime(_Z):
        @classmethod
        def now(cls, tz=None):
            return _Z.now(tz) + _K

        @classmethod
        def utcnow(cls):
            return _Z.utcnow() + _K

        @classmethod
        def today(cls):
            return _Z.today() + _K

    _d.date = date
    _d.datetime = datetime
'''


def kayma_saniye(gun: int, saat: int, dakika: int) -> int:
    """`gun` gun sonrasinin UTC `saat`:`dakika` anina kadar kac saniye.

    Gun ve saat TEK BIR kaymada birlesiyor: ayri ayri iki gecis
    kosmak, her sinama dosyasini gereksiz yere bir kez daha
    calistirirdi.

    DAKIKA ORTASINA inis yapiliyor (`second=30`): kayma tam saniyeye
    yuvarlanirken saniyenin kesri kirpiliyor ve dakika basina nisan
    alinirsa inis bir ONCEKI dakikaya dusebiliyor. Olculdu -- hedef
    00:30:00 iken shim 00:29:59'a kondu; kendi kontrolu bunu dogru
    sekilde KALDI diye bildirdi. Otuz saniyelik pay hem bu kirpmayi
    hem surec baslatma gecikmesini sogurur.
    """
    su_an = _dt.datetime.now(_dt.timezone.utc)
    hedef = (su_an + _dt.timedelta(days=gun)).replace(
        hour=saat, minute=dakika, second=30, microsecond=0)
    return round((hedef - su_an).total_seconds())


def sinama_dosyalari() -> list[pathlib.Path]:
    cikti = []
    for kok in (KOK / "haber_botu", KOK / "site"):
        cikti += sorted(kok.rglob("test_*.py"))
    # KENDINI DISLA: yoksa bu dosya kendini kaydirilmis ortamda
    # calistirir, o da kendini calistirir... sonsuz ozyineleme.
    return [p for p in cikti if p.resolve() != BEN]


def _gecis(dosyalar, t, gun, saat, dakika, etiket) -> list[tuple[str, str]]:
    """Bir senaryoyu kosar; zaman bombasi olan dosyalari dondurur."""
    sn = kayma_saniye(gun, saat, dakika)
    ort = dict(os.environ)
    ort["PYTHONPATH"] = t + os.pathsep + ort.get("PYTHONPATH", "")
    ort["SAHTE_SANIYE"] = str(sn)
    ort["PYTHONIOENCODING"] = "utf-8"
    ort_yok = dict(ort)
    ort_yok["SAHTE_SANIYE"] = "0"

    # SHIM GERCEKTEN CALISTI MI -- VE DOGRU YERE MI KONDU.
    #
    # Bu olmadan butun kural BOSA kosabilir: shim sessizce yuklenmezse
    # her dosya normal saatle calisir, hepsi gecer ve kural hicbir sey
    # olcmemis olur. Bu depoda "hicbir sey olcmeyen test" tuzagina
    # defalarca dusuldu, o yuzden yalnizca "kaydi mi" degil "DOGRU
    # SAATE mi kaydi" da soruluyor -- saat kontrolu olmasaydi gun
    # kaymasi dogru gorunur, saat sessizce yanlis kalirdi.
    kanit = subprocess.run(
        [sys.executable, "-B", "-c",
         "import datetime as d;"
         " n = d.datetime.now(d.timezone.utc);"
         " print(n.strftime('%Y-%m-%d %H:%M'))"],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=ort, cwd=str(KOK))
    temel = subprocess.run(
        [sys.executable, "-B", "-c",
         "import datetime as d;"
         " print(d.datetime.now(d.timezone.utc).strftime('%Y-%m-%d'))"],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=ort_yok, cwd=str(KOK))
    damga = (kanit.stdout or "").strip()
    try:
        ileri_g = _dt.date.fromisoformat(damga[:10])
        temel_g = _dt.date.fromisoformat((temel.stdout or "").strip()[:10])
        fark = (ileri_g - temel_g).days
    except ValueError:
        fark = -1
    saat_tam = damga[11:16] == f"{saat:02d}:{dakika:02d}"
    dogru(f"[{etiket}] saat {gun} gun ileri ve {saat:02d}:{dakika:02d}'e alindi"
          f" -> {damga or '(okunamadi)'}",
          fark == gun and saat_tam)
    if not (fark == gun and saat_tam):
        print(f"         fark: {fark}  hata: {kanit.stderr[:200]}")
        print("         SHIM CALISMIYOR -- bu senaryonun sonuclari"
              " ANLAMSIZ, kural hicbir sey olcmez.")
        return []

    # ONCE KAYDIRILMIS GECIS, SONRA GEREKIRSE NORMAL.
    #
    # Sira bilerek boyle: normal gecis, kaydirilmis gecis DUSTUGUNDE
    # anlamli -- "bu dosya bugun de kirmizi miydi, yoksa yalnizca zaman
    # yuzunden mi dustu" sorusunu ayirt etmek icin. Once ikisini birden
    # kosmak, saglikli bir depoda her dosyayi iki kez calistirmak
    # demekti. Beklenen durumda ikinci gecis HIC kosmuyor.
    bomba = []
    for p in dosyalar:
        ileri = subprocess.run([sys.executable, "-B", str(p)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=ort, cwd=str(KOK))
        if ileri.returncode == 0:
            continue
        # Bugun ZATEN kirmizi olan bir dosya bu kuralin konusu degil;
        # onu normal takim zaten yakaliyor.
        simdi = subprocess.run([sys.executable, "-B", str(p)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=ort_yok, cwd=str(KOK))
        if simdi.returncode != 0:
            continue
        son = [x for x in (ileri.stdout or "").splitlines()
               if "KALDI" in x or "DUSTU" in x or "kaldi" in x]
        bomba.append((p.relative_to(KOK).as_posix(),
                      son[-1].strip() if son else
                      (ileri.stderr or "")[-160:].strip()))
    return bomba


def main() -> int:
    dosyalar = sinama_dosyalari()
    dogru(f"sinama dosyasi bulundu ({len(dosyalar)})", len(dosyalar) >= 20)

    with tempfile.TemporaryDirectory() as t:
        (pathlib.Path(t) / "sitecustomize.py").write_text(SHIM,
                                                          encoding="utf-8")
        for saat, dakika, etiket in SENARYO:
            bomba = _gecis(dosyalar, t, KAYMA_GUN, saat, dakika, etiket)
            dogru(f"[{etiket}] zaman bombasi yok", not bomba)
            for ad, iz in bomba:
                print(f"         {ad}")
                print(f"           {iz}")

    print()
    print(f"{_gecti} gecti, {len(_kaldi)} kaldi")
    return 1 if _kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
