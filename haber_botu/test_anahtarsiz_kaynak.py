# -*- coding: utf-8 -*-
"""ANAHTARSIZ KAYNAK, ANAHTARA BAGLI OLMAMALI.

BU DOSYA NEDEN VAR
------------------
`uret_evds.py` icinde ECB referans kuru yaziliyordu ve yanindaki
yorum aynen soyle diyordu:

    "EVDS ANAHTARINA BAGLI DEGIL: ECB anahtar istemiyor."

Akis bunu UYGULAMIYORDU. Olculdu (2026-10-29, AST ile):

    main() icindeki ilk `return`   satir  49
    ecb_kur.cek() cagrisi          satir 126

Yani `EVDS_ANAHTARI` tanimli degilse fonksiyon ECB'ye HIC
ULASMIYORDU. Ikinci cikis da ayni sonucu veriyordu: `evds.hepsi()`
hic seri dondurmezse `return 1`.

NEDEN ONEMLI: EUR/USD `temel.html` icindeki fiyat seridinde, yani
sitedeki HER sayfada gorunuyor. Anahtar dusse ya da EVDS ucu gecici
olarak bos donse, kur sessizce bayatlayacakti -- hicbir hata
firlamadan.

NIYET BELGELENMIS, UYGULANMAMISTI. Bu depoda ayni sinif daha once
de yasandi: `/giris/` ve `/panel/` "arama motoruna kapali" diye
yaziliydi ama `index, follow` basiyordu.

OLCUT AST, METIN DEGIL
----------------------
"Kaynakta ecb_kur.cek() `return`dan once geciyor mu" diye metne
bakmak kirilgan olurdu: yorum satirlari, siralama ve bicimlendirme
degisince sessizce yanlis cevap verir. Burada fonksiyonun SOYUT
SOZDIZIM AGACI okunuyor ve satir numaralari karsilastiriliyor.
"""

from __future__ import annotations

import ast
import pathlib

_BURASI = pathlib.Path(__file__).resolve().parent

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_YOL = _BURASI / "uret_evds.py"
_AGAC = ast.parse(_YOL.read_text(encoding="utf-8"))
_MAIN = next((n for n in _AGAC.body
              if isinstance(n, ast.FunctionDef) and n.name == "main"), None)

print("uret_evds.py akisi")
esit(_MAIN is not None, True, "main() bulundu")

_returnler = sorted(n.lineno for n in ast.walk(_MAIN)
                    if isinstance(n, ast.Return))
_cagrilar = sorted(n.lineno for n in ast.walk(_MAIN)
                   if isinstance(n, ast.Call)
                   and getattr(n.func, "id", "") == "_anahtarsiz_yaz")

# ATILLIK: `return` hic bulunamazsa karsilastirma anlamsiz olur ve
# iddia bos yere gecer.
esit(len(_returnler) > 0, True,
     f"main() icinde return var ({len(_returnler)})")
esit(len(_cagrilar), 1,
     "anahtarsiz kaynak TEK yerden cagriliyor")
esit(min(_cagrilar) < min(_returnler), True,
     f"anahtarsiz cagri ilk return'den ONCE "
     f"(satir {min(_cagrilar)} < {min(_returnler)})")

# ECB CAGRISI ARTIK EVDS BOLGESINDE OLMAMALI. Fonksiyon govdesine
# geri tasinirsa kusur geri gelir ve ustteki satir karsilastirmasi
# bunu YAKALAMAZ (cagri hem onde hem icerde olabilirdi).
_ecb_main = [n.lineno for n in ast.walk(_MAIN)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "cek"
             and getattr(n.func.value, "id", "") == "ecb_kur"]
esit(_ecb_main, [], "ecb_kur.cek() main() icinde DEGIL")

# ...ve gercekten anahtarsiz fonksiyonun icinde olmali.
_FN = next((n for n in _AGAC.body
            if isinstance(n, ast.FunctionDef)
            and n.name == "_anahtarsiz_yaz"), None)
esit(_FN is not None, True, "_anahtarsiz_yaz() tanimli")
_ecb_fn = [n.lineno for n in ast.walk(_FN)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "cek"
           and getattr(n.func.value, "id", "") == "ecb_kur"]
esit(len(_ecb_fn), 1, "ecb_kur.cek() anahtarsiz fonksiyonda")

# ANAHTAR DENETIMI O FONKSIYONUN ICINDE OLMAMALI -- olsa bagimsizlik
# yine kaybolurdu ve yukaridaki satir testi bunu gormezdi.
_anahtar = [n.lineno for n in ast.walk(_FN)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "anahtar"]
esit(_anahtar, [], "anahtarsiz fonksiyon anahtar SORMUYOR")

print("")
print("makro_uret_ucretsiz.py sirasi")
# AYNI SINIF, IKINCI BICIM: veri YAZMA adimi, BASARISIZ OLABILEN bir
# adima bagli olmamali.
#
# `DEPO_SERILERI` varlik sayfalarinin grafigini besliyor ve depoya
# `gosterge_yaz` ile yaziliyor. Ayni fonksiyon daha sonra
# `yazar_makro.yaz()` cagiriyor -- o adim UCRETSIZ AI KOTASINA bagli
# ve kotanin tukenmesi bu depoda zaten olculmus bir darbogaz.
#
# Yazma su an AI cagrisindan ONCE. Siralama ters cevrilirse kota
# tukendigi gun seriler SESSIZCE yazilmaz: sayfa bos kalir ve hicbir
# hata firlamaz. Bu yuzden sira elle degil SINAMAYLA tutuluyor.
_M = _BURASI / "makro_uret_ucretsiz.py"
_MA = ast.parse(_M.read_text(encoding="utf-8"))
_MFN = next((n for n in _MA.body
             if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
esit(_MFN is not None, True, "makro main() bulundu")

_yazma = [n.lineno for n in ast.walk(_MFN)
          if isinstance(n, ast.Call)
          and isinstance(n.func, ast.Attribute)
          and n.func.attr == "gosterge_yaz"]
_ai = [n.lineno for n in ast.walk(_MFN)
       if isinstance(n, ast.Call)
       and isinstance(n.func, ast.Attribute)
       and n.func.attr == "yaz"
       and getattr(n.func.value, "id", "") == "yazar_makro"]

# ATILLIK: iki listeden biri bossa karsilastirma anlamsiz olur ve
# iddia bos yere gecer.
esit(len(_yazma) > 0, True, f"gosterge_yaz cagrisi var ({len(_yazma)})")
esit(len(_ai) > 0, True, f"yazar_makro.yaz cagrisi var ({len(_ai)})")
esit(max(_yazma) < min(_ai), True,
     f"depoya yazma AI adimindan ONCE "
     f"(satir {max(_yazma)} < {min(_ai)})")

# DEPO_SERILERI gercekten o yazmaya giriyor mu. Tanimli ama
# KULLANILMAYAN bir liste, sessiz bir bosluk olurdu.
_kaynak = _M.read_text(encoding="utf-8")
esit(_kaynak.count("DEPO_SERILERI") >= 2, True,
     f"DEPO_SERILERI tanimlanip KULLANILIYOR "
     f"({_kaynak.count('DEPO_SERILERI')} kez geciyor)")
esit("depo_seriler.items()" in _kaynak, True,
     "depo serileri gozlem listesine katiliyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
