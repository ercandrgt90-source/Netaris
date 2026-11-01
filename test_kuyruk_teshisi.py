# -*- coding: utf-8 -*-
"""DUSEN ADIM NEDENINI YAZDIRMALI.

KUSUR (olculdu 2026-11-01, 12 SAATLIK KESINTI)
----------------------------------------------
`calistir.py` her adimin yalnizca SON ALTI satirini basiyordu.
Gecen adim icin bu dogru -- ozet yeter. Dusen adimda ise son alti
satir `denetim.py`nin OZET KUTUSU oluyor ve BULGULAR hemen ustunde
kesiliyordu:

    BULGU:        1 hata, 1 uyari, 2 bilgi
    YAYIN KARARI: YAYINA UYGUN DEGIL

Yani gunluk "yayinlanamaz" diyor ama NEDEN yayinlanamadigini
soylemiyor. Haber hatti o gun her 10 dakikada bir ayni hatayla
dustu, son otomatik yayin 2026-10-31 23:08'de kaldi ve gunluge
bakarak teshis KONULAMADI -- hata yerelde uretilemiyordu, cunku
kosunun o an urettigi icerige bagliydi.

"Ne oldu" ile "neden oldu" ayri sorular. Bu ders depoda defalarca
yazilmis; kuyrugun kendisi onu uygulamiyordu.

NE SINANIYOR
------------
1. Dusen adim GENIS pencereyle basiyor, gecen adim DAR.
2. Kirpma olunca KAC satirin atlandigi soyleniyor.
3. Ciktisi olmayan dusen adim sessiz gecmiyor.
4. Iki pencere birbirinden FARKLI -- esitlenirse kural olur.
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _yukle():
    """`calistir.py`yi ICE ALIR -- main() kosmadan.

    Dosya betik olarak da calisiyor; `spec` ile yuklemek yan
    etkisiz.
    """
    spec = importlib.util.spec_from_file_location(
        "_calistir_modulu", _KOK / "calistir.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M = _yukle()


def _say(metin: str) -> int:
    """Basilan ADIM satirlarini sayar.

    "satir " araması yetmiyordu: kirpma bildirimi de ("... ilk N
    satir atlandi") o dizgeyi tasiyor ve sayiyi bir fazla
    gosteriyordu -- olcum aracinin kendi hatasi.
    """
    return sum(1 for s in metin.splitlines()
               if s.strip().startswith("satir "))


def _kos(satir_sayisi: int, cikis: int) -> str:
    """Sahte bir adim calistirip BASILAN metni doner."""
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "sahte.py"
        p.write_text(
            "import sys" + chr(10)
            + f"for i in range({satir_sayisi}): print('satir', i)" + chr(10)
            + f"sys.exit({cikis})" + chr(10),
            encoding="utf-8")
        yakala = io.StringIO()
        with contextlib.redirect_stdout(yakala):
            M._calistir("DENEME", [str(p)])
        return yakala.getvalue()


print(__doc__.splitlines()[0])
print("")

# ---------------------------------------------------------------
print("1) PENCERELER FARKLI")

esit(M.SATIR_HATA > M.SATIR_BASARI, True,
     f"dusen adim penceresi daha genis ({M.SATIR_HATA} > "
     f"{M.SATIR_BASARI})")
# OLCUT GERCEK IHTIYAC: `denetim.py`nin bulgu bolumu ozet kutusuyla
# birlikte sigmali. Alti satir sigmiyordu -- kusur tam buydu.
esit(M.SATIR_HATA >= 40, True,
     f"pencere denetim bulgularini tasiyacak kadar genis "
     f"({M.SATIR_HATA})")

# ---------------------------------------------------------------
print("")
print("2) DAVRANIS -- DUSEN ADIM NEDENINI YAZIYOR")

_metin = _kos(30, 1)
_sayi = _say(_metin)
esit(_sayi, 30, f"dusen adim 30 satirin hepsini yazdi ({_sayi})")
esit("HATA" in _metin, True, "dusen adim HATA diyor")

# ATILLIK KONTROLU: gecen adim DAR pencerede kaliyor mu? Kalmazsa
# yukaridaki iddia "her sey basiliyor"dan ayirt edilemez.
_gecen = _kos(30, 0)
_g_sayi = _say(_gecen)
esit(_g_sayi, M.SATIR_BASARI,
     f"atillik kontrolu: gecen adim yalnizca {M.SATIR_BASARI} satir "
     f"yazdi ({_g_sayi})")

# ---------------------------------------------------------------
print("")
print("3) KIRPMA SOYLENIYOR")

# Kirpilan satir sayisi yazilmazsa, okuyan kisi gordugunun TAMAMI
# oldugunu sanar ve eksik bir teshisle yola cikar.
_uzun = _kos(M.SATIR_HATA + 25, 1)
esit("satir atlandi" in _uzun, True,
     "pencereyi asan ciktida kac satirin atlandigi yaziliyor")
esit("25 satir atlandi" in _uzun, True,
     f"atlanan sayi DOGRU (25) -- {[s for s in _uzun.splitlines() if 'atlandi' in s]}")
# Kirpilmayan ciktida bu satir OLMAMALI: her kosuda 'atlandi'
# yazmak, uyariyi gurultuye cevirirdi.
esit("satir atlandi" in _kos(3, 1), False,
     "kirpma yoksa 'atlandi' satiri YOK")

# ---------------------------------------------------------------
print("")
print("4) SESSIZ DUSEN ADIM DA SOYLENIYOR")

# Hic cikti basmadan dusen adim, eski halde HICBIR SEY yazdirmiyordu
# ve gunlukte yalnizca "HATA" goruluyordu -- arizanin bos cikti
# oldugu bile anlasilmiyordu.
_bos = _kos(0, 1)
esit("(cikti yok)" in _bos, True, "ciktisiz dusen adim soyleniyor")
esit("(cikti yok)" in _kos(3, 1), False,
     "ciktisi OLAN adimda bu satir YOK")

# ---------------------------------------------------------------
print("")
print(f"TUM TESTLER GECTI ({_gecti})")
