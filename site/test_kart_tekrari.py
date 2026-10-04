# -*- coding: utf-8 -*-
"""HABERE OZEL OLMAYI VAAT EDEN KUTU, AYNI SAYFADA TEKRARLAMAMALI.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-10-04, uretilen `/gundem/`):

    "Bu neden kritik?"   26 kutu,  1 FARKLI metin
    "Netaris yorumu"     19 kutu, 19 FARKLI metin

Ikinci satir dogru calisan bir ozellik. Birinci satir ise ayni iki
cumlenin 26 kez basilmasi.

NEDEN SADECE "NETARIS YORUMU" SINANIYOR
---------------------------------------
Ikisi AYNI SEYI VAAT ETMIYOR.

"Bu neden kritik?" metni KATEGORIDEN tureniyor ve kategorinin aktarim
mekanizmasini anlatiyor -- habere ozel oldugu iddia edilmiyor. Modele
de hic gonderilmiyor (bkz. `test_uret_ai_yorum.py`), yani deponun
"haberi farkli cumlelerle tekrar etmek analiz sayilmaz" kurali bu
metni kapsamiyor.

Tekrari kesmek DENENDI ve GERI ALINDI: susturulunca 27 kart tamamen
bos kaldi ve `test_kart_metni.py` kirmizi yandi. O dosyanin gerekcesi
2026-08-23'te olcerek yazilmis -- bos kart, tekrardan once gelen ve
daha agir basan bir kusur. Bu 27 kartta ucuncu secenek de yok
(`ozet_kart` dagilimi sifir). Secim gercekten "ayni aciklama" ile
"hicbir sey" arasinda ve ikincisi daha kotu.

"Netaris yorumu" ise habere OZEL olmayi vaat ediyor. Orada ayni
metnin iki kez cikmasi, vaadin tutulmamasi demek -- ve sessiz olur:
sayfa calisir, kutular dolu gorunur, okur yalnizca "bunu okumustum"
hissi tasir. Korunan yer burasi.

NE SINANMIYOR
-------------
Metnin KALITESI degil, AYNI SAYFADA BENZERSIZ olmasi. Kalite ayri
denetimlerin isi (`yorum_denetimi.py`, `beyan_denetimi.py`).
"""

from __future__ import annotations

import collections
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


_C = _SITE / "cikti"
if not (_C / "index.html").exists():
    print("\n  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

#: Kart yorumu tasiyan LISTE sayfalari.
_SAYFALAR = ("gundem/index.html", "index.html")
#: Habere OZEL olmayi vaat eden etiket. Kategoriden turenen
#: "Bu neden kritik?" BILEREK disarida -- gerekce yukarida.
_OZEL_ETIKET = "netaris yorumu"
_KUTU = re.compile(r'class="kart-yorum-etiket">(.*?)</p>\s*<p[^>]*>(.*?)</p>',
                   re.S)


def _sade(parca: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", parca)).strip()


_bakilan = 0
_ozel_toplam = 0
_tekrar: list[str] = []
for _ad in _SAYFALAR:
    _p = _C / _ad
    if not _p.exists():
        continue
    _bakilan += 1
    _metinler: collections.Counter = collections.Counter()
    for _m in _KUTU.finditer(_p.read_text(encoding="utf-8",
                                          errors="replace")):
        if _sade(_m.group(1)).lower() != _OZEL_ETIKET:
            continue
        _metin = _sade(_m.group(2))
        if _metin:
            _metinler[_metin] += 1
    _ozel_toplam += sum(_metinler.values())
    for _metin, _kac in _metinler.items():
        if _kac > 1:
            _tekrar.append(f"{_ad}: {_kac}x  {_metin[:70]}")

esit(_bakilan > 0, True, f"liste sayfalari bulundu ({_bakilan})")
# Kutu HIC bulunmazsa sinama sessizce yesil doner ve hicbir sey
# korumaz. Varligin kendisi ayrica dogrulaniyor.
esit(_ozel_toplam > 0, True,
     f"habere ozel yorum kutusu bulundu ({_ozel_toplam})")
if _tekrar:
    print("\n  AYNI YORUM BIRDEN COK KARTTA:")
    for _t in _tekrar[:8]:
        print(f"    {_t}")
esit(len(_tekrar), 0,
     f"habere ozel yorumlarin hepsi benzersiz ({_ozel_toplam} kutu)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
