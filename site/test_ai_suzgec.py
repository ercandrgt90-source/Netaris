# -*- coding: utf-8 -*-
"""DEPODAKI AI YORUMU DA GUVENLIK SUZGECINDEN GECMELI.

BU DOSYA NEDEN VAR
------------------
`haber_botu/ai/guvenlik.py` yorum URETILIRKEN calisiyor. Ama metin bir
kez depoya yazildiktan sonra bir daha sorgulanmiyordu. Sonuc: kural
SONRADAN sikilastirildiginda eski yorumlar yayinda kalmaya devam
ediyordu. Yani "deseni ekledim" demek, "icerik temizlendi" demek
DEGILDI.

OLCULDU (2026-10-11): depodaki 2.576 AI yorumunun tamami tarandi.
Yayimlanmis 578 yorumun BIRI bugunku kurala takiliyordu --

    "Bakir fiyatlari 2026 yili icin 12.000 dolar/ton seviyesine
     ulasacak."

Kaynak haberin basligi tahminin BofA'ya ait oldugunu soyluyor; yorum
atfi dusurup kesinlik olarak yazmis. Bu, bu sitenin en hassas cizgisi:
yon ve buyukluk tahmini yasak.

Desen o gun `guvenlik.py` icine eklendi -- ama METIN DEPODAYDI. Desen
tek basina hicbir seyi degistirmezdi. Suzgec artik HER INSADA
calisiyor; kural sikilastiginda eski icerik de kendiliginden
temizleniyor.

NE SINANIYOR
------------
1. YASAK bulgu tasiyan yorum ELENIYOR.
2. Temiz yorum KALIYOR -- suzgec her seyi silmiyor.
3. Olculen gercek ihlal metni eleniyor (deger sabitlemesi).
4. `yayinlanabilir()` DEGIL `tara()` olcutu kullaniliyor: birincisi
   yasal uyarinin METNIN ICINDE olmasini da sart kosar, oysa bu
   sitede uyari SABLONDA duruyor. O olcut kullanilsaydi yorumlarin
   TAMAMI elenirdi -- sinama bunu da dogruluyor.

SENTETIK VERI -- VE BU BILINCLI. Gercek depoya bakan bir sinama her
kosuda degisen veriye baglanirdi; bu depoda bir kez yasandi ve sinama
urunde hicbir kusur yokken kirmizi dondu.
"""

from __future__ import annotations

import pathlib
import sys

_SITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SITE))

import insa                                      # noqa: E402

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


print("")
print("AI yorumu guvenlik suzgeci")

TEMIZ = "Enflasyon verisi aciklandi; gida kalemi aylik bazda one cikti."
IHLAL = "Bakir fiyatlari 2026 yili icin 12.000 dolar/ton seviyesine ulasacak."
TAVSIYE = "Bu hisseyi portfoyunuze ekleyin."

esit(sorted(insa.yorum_suz({"a": IHLAL, "b": TEMIZ})), ["b"],
     "yasak bulgu tasiyan yorum eleniyor")
esit(sorted(insa.yorum_suz({"b": TEMIZ, "c": TEMIZ + " Ikinci cumle."})),
     ["b", "c"], "temiz yorum kaliyor")
esit(sorted(insa.yorum_suz({"a": TAVSIYE, "b": TEMIZ})), ["b"],
     "dogrudan tavsiye de eleniyor")
esit(insa.yorum_suz({}), {}, "bos girdi bos cikti")

# Olcut `tara()` olmali: `yayinlanabilir()` yasal uyari metnini de
# arar ve yorumlarin hicbirinde o metin YOK (sablonda duruyor).
# Yanlis olcut kullanilsaydi asagidaki temiz yorum da elenirdi.
esit(list(insa.yorum_suz({"b": TEMIZ})), ["b"],
     "yasal uyari metni yorumda olmadan da temiz yorum geciyor")

# --- 6) INSA YOLU GERCEKTEN SUZGECTEN GECIYOR MU -------------------
#
# ILK YAZIMDA BU KONTROL YOKTU VE MUTASYON HAYATTA KALDI: `ai_yorum_oku`
# icindeki `yorum_suz(...)` cagrisi kaldirildi, yani gercek insa
# yorumlari DENETLENMEDEN basmaya basladi -- ve sinama yesil kaldi.
# Ustteki maddeler fonksiyonun DOGRU calistigini gosteriyor, KULLANILDIGINI
# degil. Bu depoda tekrar eden kusur sinifi: koruma var ama durumu
# kacirıyor.
#
# Olcut davranissal: `yorum_suz` gecici olarak degistiriliyor ve
# `ai_yorum_oku` cagrildiginda ONDAN GECTIGI dogrulaniyor. Kaynak
# metnine bakmak yerine bu secildi -- kaynak kontrolu, cagrinin
# yorum satirinda durdugu durumu ayirt edemez.
_cagrildi = []
_asil = insa.yorum_suz
try:
    insa.yorum_suz = lambda d: (_cagrildi.append(len(d)), {})[1]
    _sonuc = insa.ai_yorum_oku()
finally:
    insa.yorum_suz = _asil
esit(len(_cagrildi), 1, "ai_yorum_oku suzgecten GECIYOR")
esit(_sonuc, {}, "suzgecin ciktisi dogrudan donuyor (es gecilmiyor)")
esit(_cagrildi[0] > 0, True,
     f"suzgece gercek kayit gidiyor ({_cagrildi[0] if _cagrildi else 0} yorum)")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
