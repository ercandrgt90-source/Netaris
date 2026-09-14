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

SHIM = '''
import datetime as _d
import os

_g = int(os.environ.get("SAHTE_GUN", "0"))
if _g:
    _K = _d.timedelta(days=_g)
    _T, _Z = _d.date, _d.datetime

    class date(_T):
        @classmethod
        def today(cls):
            return _T.today() + _K

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


def sinama_dosyalari() -> list[pathlib.Path]:
    cikti = []
    for kok in (KOK / "haber_botu", KOK / "site"):
        cikti += sorted(kok.rglob("test_*.py"))
    # KENDINI DISLA: yoksa bu dosya kendini kaydirilmis ortamda
    # calistirir, o da kendini calistirir... sonsuz ozyineleme.
    return [p for p in cikti if p.resolve() != BEN]


def main() -> int:
    dosyalar = sinama_dosyalari()
    dogru(f"sinama dosyasi bulundu ({len(dosyalar)})", len(dosyalar) >= 20)

    with tempfile.TemporaryDirectory() as t:
        (pathlib.Path(t) / "sitecustomize.py").write_text(SHIM,
                                                          encoding="utf-8")

        # ONCE SHIM'IN CALISTIGINI DOGRULA.
        #
        # Bu olmadan butun sinama BOSA calisabilir: shim sessizce
        # yuklenmezse her dosya normal saatle kosar, hepsi gecer ve
        # kural hicbir sey olcmemis olur. Bu depoda "hicbir sey
        # olcmeyen test" tuzagina defalarca dusuldu.
        ort = dict(os.environ)
        ort["PYTHONPATH"] = t + os.pathsep + ort.get("PYTHONPATH", "")
        ort["SAHTE_GUN"] = str(KAYMA_GUN)
        ort["PYTHONIOENCODING"] = "utf-8"
        kanit = subprocess.run(
            [sys.executable, "-B", "-c",
             "from datetime import date, timedelta;"
             " import sys;"
             " print((date.today() - date(2000, 1, 1)).days)"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=ort, cwd=str(KOK))
        ort_yok = dict(ort)
        ort_yok["SAHTE_GUN"] = "0"
        temel = subprocess.run(
            [sys.executable, "-B", "-c",
             "from datetime import date;"
             " print((date.today() - date(2000, 1, 1)).days)"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=ort_yok, cwd=str(KOK))
        try:
            fark = int(kanit.stdout.strip()) - int(temel.stdout.strip())
        except ValueError:
            fark = -1
        dogru(f"saat gercekten {KAYMA_GUN} gun ileri alindi",
              fark == KAYMA_GUN)
        if fark != KAYMA_GUN:
            print(f"         fark: {fark}  hata: {kanit.stderr[:200]}")
            print("         SHIM CALISMIYOR -- asagidaki sonuclar"
                  " ANLAMSIZ, kural hicbir sey olcmez.")
            return 1

        # ONCE KAYDIRILMIS GECIS, SONRA GEREKIRSE NORMAL.
        #
        # Sira bilerek boyle: normal gecis, kaydirilmis gecis DUSTUGUNDE
        # anlamli -- "bu dosya bugun de kirmizi miydi, yoksa yalnizca
        # zaman yuzunden mi dustu" sorusunu ayirt etmek icin. Once
        # ikisini birden kosmak, saglikli bir depoda her dosyayi iki kez
        # calistirmak demekti (olculdu: 57 dosya, gecis basina ~31 sn).
        # Beklenen durumda ikinci gecis HIC kosmuyor.
        bomba = []
        for p in dosyalar:
            ileri = subprocess.run([sys.executable, "-B", str(p)],
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   env=ort, cwd=str(KOK))
            if ileri.returncode == 0:
                continue
            # Bugun ZATEN kirmizi olan bir dosya bu kuralin konusu
            # degil; onu normal takim zaten yakaliyor.
            simdi = subprocess.run([sys.executable, "-B", str(p)],
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   env=ort_yok, cwd=str(KOK))
            if simdi.returncode != 0:
                continue
            son = [s for s in (ileri.stdout or "").splitlines()
                   if "KALDI" in s or "kaldi" in s]
            bomba.append((p.relative_to(KOK).as_posix(),
                          son[-1].strip() if son else
                          (ileri.stderr or "")[-160:].strip()))

        dogru("zaman bombasi yok (bugun gecen, 60 gun sonra da geciyor)",
              not bomba)
        for ad, iz in bomba:
            print(f"         {ad}")
            print(f"           {iz}")

    print(f"\n{_gecti} gecti, {len(_kaldi)} kaldi")
    return 1 if _kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
