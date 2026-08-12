"""EIA yayin takvimi -- tarih dili sinamasi.

`_tr_tarih` yalnizca bicimlendirme yapiyor gibi gorunuyor ama okurun
gordugu cumleyi belirliyor. "sonraki 12 Ağustos" ifadesi 12 Ağustos
GUNU okundugunda okuru takvime bakmaya zorluyordu -- ve yayin gunu,
tam da notun en cok ise yaradigi gun.
"""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import eia_takvim  # noqa: E402

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


BUGUN = datetime.date(2026, 8, 12)   # carsamba

print("\nEIA yayin takvimi -- tarih dili\n")

esit(eia_takvim._tr_tarih(8, 12, BUGUN), "bugün",
     "yayin GUNU 'bugün' diyor -- notun en cok ise yaradigi gun")
esit(eia_takvim._tr_tarih(8, 13, BUGUN), "yarın", "ertesi gun 'yarın'")
esit(eia_takvim._tr_tarih(8, 19, BUGUN), "19 Ağustos",
     "uzak tarih AYNEN yaziliyor -- 'bir hafta sonra' belirsiz olurdu")
esit(eia_takvim._tr_tarih(9, 2, BUGUN), "2 Eylül", "ay gecisi")

# Bozuk girdi sessizce bos donmeli: serit bir tarih yuzunden bozulmaz.
esit(eia_takvim._tr_tarih(13, 1, BUGUN), "", "gecersiz ay -> bos")
esit(eia_takvim._tr_tarih(0, 5, BUGUN), "", "sifir ay -> bos")
esit(eia_takvim._tr_tarih(2, 30, BUGUN), "", "olmayan gun (30 Şubat) -> bos")

# Varsayilan bugun: cagri `bugun` vermeden de calismali.
esit(isinstance(eia_takvim._tr_tarih(6, 15), str), True,
     "bugun verilmezse bugunun tarihi kullaniliyor")

print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
