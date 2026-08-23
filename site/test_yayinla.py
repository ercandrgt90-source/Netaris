"""Yayin hatti SESSIZCE olmemeli.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): canli site OTUZ BIR commit geride duruyordu.
Iki gunluk tasarim calismasinin -- izgara duzeltmeleri, modul kalibi,
fotograf cozunurlugu, sayaclar, sirket logolari -- hicbiri yayinda
degildi. Kullanici "hala tasarim cop", "sana attigim ekranlarin
hicbiri olmamis" derken TAMAMEN HAKLIYDI: gonderilen hicbir sey
yayina gitmemisti.

Sebep tek satirdi:

    print("  " + "\\n  ".join((sonuc.stdout or "").strip().splitlines()))
    UnicodeEncodeError: 'charmap' codec can't encode character
    '\\ufffd' in position 591 ... cp1254

Zincir: `insa.py` ciktisi UTF-8 cozulurken bozuk baytin yerine
U+FFFD konuyor; sonra o metin cp1254 konsola yazdiriliyor ve U+FFFD'nin
cp1254 karsiligi YOK. `yayinla.py` `[1/3]` adiminda cokuyor,
`wrangler deploy` HIC CALISMIYOR.

IKI AYRI HATA, IKI AYRI KORUMA
------------------------------
1. YAZDIRMA COKUYORDU  -> `_konsol_kodlamasi()` cikti akisini tolere
   edici yapiyor. Asagida cp1254 zorlanmis bir alt surecte sinanyor.

2. COKTUGU ANLASILMIYORDU -> `yayini_dogrula()` dagitimdan sonra canli
   sayfayi cekip yerel yapinin surum izini ariyor. "Yayinladim" bir
   niyetti; artik bir OLCUM.

Ikinci koruma birincisinden onemli: yazdirma hatasi kapandi ama yayin
hattini bozacak BASKA hatalar da olabilir. Dogrulama adimi, sebebi ne
olursa olsun "yuklenen sey canlida gorunmuyor" durumunu yakalar.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import yayinla  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}\n         beklenen: {beklenen!r}"
              f"\n         bulunan : {bulunan!r}")


def _alt_surecte(kod: str) -> int:
    """Kodu cp1254 cikti kodlamasi ZORLANMIS ayri bir surecte calistirir.

    Windows Turkce konsolu birebir bu -- ve hata yalnizca orada
    goruluyordu. Testin kendi surecinde `sys.stdout` zaten UTF-8
    olabilir, o yuzden sinama ayri surecte yapiliyor.
    """
    cevre = dict(os.environ, PYTHONIOENCODING="cp1254")
    s = subprocess.run([sys.executable, "-c", kod], cwd=_SITE,
                       capture_output=True, env=cevre)
    return s.returncode


print("Sinama gercekten cp1254 zorluyor  (kendi kendini dogrulama)")

# KORUMASIZ hal: bu COKMELI. Cokmezse test bir sey olcmuyor demektir
# ve asagidaki "gecti" satiri anlamsiz olurdu.
esit(_alt_surecte("import sys; print('\\ufffd')") != 0, True,
     "korumasiz surecte U+FFFD yazdirmak COKUYOR")

esit(_alt_surecte("import sys; print('duz ascii')"), 0,
     "duz metin korumasiz da yazilabiliyor")


print("\nYayin betigi bozuk karakterle COKMUYOR")

esit(_alt_surecte("import yayinla; print('\\ufffd bozuk bayt')"), 0,
     "yayinla iceri alininca U+FFFD yazdirilabiliyor")

# Turkce harfler de cp1254'te var ama emoji YOK -- wrangler emoji
# basiyor ("Success!" satirinda). O da gecmeli.
esit(_alt_surecte("import yayinla; print('\\u2728 Success!')"), 0,
     "wrangler emojisi de yazdirilabiliyor")


print("\nSurum izi cikariliyor")

esit(yayinla._surum_izi('<link href="/statik/stil.css?v=48b5505a">'),
     "48b5505a", "baglantidan surum okunuyor")

esit(yayinla._surum_izi('<link href="/statik/stil.css">'), "",
     "surumsuz baglantida bos donuyor")

esit(yayinla._surum_izi(""), "", "bos metinde bos donuyor")

# ILK eslesme alinmali: sayfada baska surumlu varlik da olabilir ve
# stil.css baglantisi <head> icinde en ustte duruyor.
esit(yayinla._surum_izi(
    'a href="/statik/stil.css?v=aaa11122" b href="/statik/stil.css?v=bbb22233"'),
    "aaa11122", "ilk stil surumu aliniyor")

# Yerel cikti varsa gercekten okunabiliyor mu -- duzenli ifade
# sayfanin GERCEK bicimiyle eslesmezse sessizce bos doner ve
# dogrulama hep "DOGRULANAMADI" derdi.
_ana = _SITE / "cikti" / "index.html"
if _ana.exists():
    _iz = yayinla._surum_izi(_ana.read_text(encoding="utf-8"))
    esit(len(_iz), 8, f"uretilmis ana sayfada surum izi bulundu ({_iz})")
else:
    print("  atlandi  cikti/index.html yok (once insa.py calistirin)")


print("\nDogrulama, canliya ulasamadiginda YAYINI BASARISIZ SAYMIYOR")

# Cozumlenemeyecek bir adres: ag katmani hata atar. Dagitim basarili
# olup yalnizca dogrulama yapilamadiginda donus 0 olmali -- yoksa her
# agsiz ortamda yayin "basarisiz" gorunurdu.
esit(yayinla.yayini_dogrula("https://bulunmayan.netaris.gecersiz/"), 0,
     "ulasilamayan adres yayini basarisiz saymiyor")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
