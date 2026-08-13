"""Yillik/aylik degisim hesabi -- BOSLUKLU seride de dogru mu?

NEDEN VAR
---------
Hesap konum aritmetigiyle yapiliyordu (`g[i - 12]`, "on iki gozlem
geri") ve bu, seri KESINTISIZ oldugu surece dogru. Degildi.

Olculdu ve yayimlandi:
  * FRED'in CPIAUCSL serisinde 2025-10 gozlemi YOK. Bosluktan
    sonraki her gozlem icin on iki konum geri gitmek ON UC AY geri
    gitmek demekti: ABD TUFE %3,73 basildi, dogrusu %3,46.
  * GDPC1 UC AYLIK bir seri. On iki konum geri = ON IKI CEYREK = UC
    YIL. Yayimlanan buyume rakamlari uc kat sisikti: %8,36 yerine
    %2,31.

Ikisi de ayni kok sebep: ZAMANI konumla saymak. Tarihle arama
bosluktan da frekanstan da etkilenmiyor.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import uret_takvim  # noqa: E402
import veri_dogrula  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama):
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


class G:
    def __init__(self, tarih, deger):
        self.tarih = tarih
        self.deger = deger


print("\nYillik/aylik degisim -- bosluklu ve ceyreklik seriler\n")

# --- tarih kaydirma ---
esit(uret_takvim._bir_yil_once("2026-06-01"), "2025-06-01", "yil geri: normal")
esit(uret_takvim._bir_yil_once("2026-01-01"), "2025-01-01", "yil geri: ocak")
esit(uret_takvim._bir_ay_once("2026-01-01"), "2025-12-01", "ay geri: yil sinirinda")
esit(uret_takvim._bir_ay_once("2026-03-01"), "2026-02-01", "ay geri: normal")

# --- BOSLUKLU AYLIK SERI (gercek olay: 2025-10 eksik) ---
aylik = [G("2025-06-01", 100.0), G("2025-07-01", 101.0), G("2025-08-01", 102.0),
         G("2025-09-01", 103.0),
         # 2025-10 YOK -- FRED'in CPIAUCSL serisindeki gercek bosluk
         G("2025-11-01", 105.0), G("2025-12-01", 106.0),
         G("2026-01-01", 107.0), G("2026-02-01", 108.0), G("2026-03-01", 109.0),
         G("2026-04-01", 110.0), G("2026-05-01", 111.0), G("2026-06-01", 112.0)]
y = veri_dogrula._beklenen("X", "yillik", aylik)
esit(round(y["2026-06-01"], 4), 12.0,
     "bosluktan SONRAKI gozlem dogru tabana bakiyor (100 -> 112 = %12)")
esit("2025-11-01" in y, False,
     "bir yil oncesi OLMAYAN gozlem icin deger URETILMIYOR")

# Konum aritmetigi olsaydi ne olurdu: 2026-06 icin 12 konum geri
# 2025-06 DEGIL, listede bir eksik oldugu icin daha eskisine giderdi.
esit(len(aylik), 12, "sinama serisi 12 gozlem (bir ay eksik, 13 aylik aralik)")

# --- CEYREKLIK SERI (gercek olay: GDPC1) ---
ceyrek = [G("2024-01-01", 100.0), G("2024-04-01", 101.0),
          G("2024-07-01", 102.0), G("2024-10-01", 103.0),
          G("2025-01-01", 104.0), G("2025-04-01", 105.0),
          G("2025-07-01", 106.0), G("2025-10-01", 107.0),
          G("2026-01-01", 108.0)]
q = veri_dogrula._beklenen("GDPC1", "yillik", ceyrek)
esit(round(q["2026-01-01"], 4), 3.8462,
     "ceyreklik seride yillik = DORT CEYREK geri (104 -> 108)")
esit(round(q["2025-01-01"], 4), 4.0,
     "ceyreklik seride ikinci yillik degisim de dogru")

# --- AYLIK DEGISIM, bosluk uzerinde ---
d = veri_dogrula._beklenen("Y", "degisim", aylik)
esit("2025-11-01" in d, False,
     "onceki AY yoksa aylik degisim URETILMIYOR -- iki aylik degisimi "
     "aylik diye yayimlamaktansa susmak")
esit(round(d["2026-06-01"], 4), 1.0, "bosluk disinda aylik degisim dogru")

# --- SEVIYE sunumu dokunulmadan geciyor ---
s = veri_dogrula._beklenen("Z", "seviye", aylik)
esit(s["2026-06-01"], 112.0, "seviye sunumu ham degeri koruyor")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
