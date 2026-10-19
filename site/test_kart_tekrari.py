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

"KUTU YOK" ILE "MEKANIZMA BOZUK" AYRI SEYLER
--------------------------------------------
Bu dosya 2026-10-20'de dagitimi DORT SAATTEN FAZLA durdurdu. CI
kosusunda `_ozel_toplam > 0` dustu -- ama kusur yoktu:

    0 yorum uretildi, 5 reddedildi, 23 aday atlandi
    ai: 3 yorum sayfada karsiligi olmayan sayi tasidigi icin BASILMADI

Yani kutu basilmadi cunku BASILACAK YORUM YOKTU. Ucretsiz saglayici
o kosuda hicbir sey uretmedi, uretilen 3 tanesi de kalite denetiminden
gecemedi. Deponun KURALI CALISTI ve sonucu "sinama kirmizi" oldu.

Ozgun kaygi dogruydu: kutu hic bulunmazsa tekrar denetimi atil kalir.
Yanlis olan OLCUTtu -- "bu kosuda kutu var mi" sorusu, "mekanizma
duruyor mu" sorusunun cevabi degil. Ilki ucretsiz AI kotasina bagli ve
her gun degisiyor; ikincisi kodda duruyor.

Mekanizma artik ICERIKTEN BAGIMSIZ olculuyor:

  1. Uretilen sayfada HERHANGI bir yorum kutusu var mi (`_tum_kutu`).
     Yoksa ya sablondaki biçimlendirme ya buradaki desen cürümüs --
     gercek kusur, kirmizi.
  2. Sablon `Netaris yorumu` dalini hala basiyor mu. Ozellik silinirse
     kirmizi; "yorum yok" diye sessizce gecmiyor.

Ikisi de yesilken `_ozel_toplam == 0` ise: korunacak kutu yok, sebebi
EKRANA YAZILIYOR, kosu yesil kaliyor.

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


def _sablon_dali_var() -> bool:
    """Sablon `ai_yorum_kart` dalinda `_OZEL_ETIKET` basiyor mu.

    "Yorum yok" ile "ozellik kaldirilmis" ayri seyler. Birincisi
    normal, ikincisi kusur -- ve yalnizca uretilen HTML'e bakarak
    ikisi ayirt edilemiyor: yorum uretilmeyen bir kosuda ikisi de
    sifir kutu verir. Ayrim KAYNAKTAN okunuyor.
    """
    _s = _SITE / "sablonlar" / "gundem.html"
    if not _s.exists():
        return False
    _ham = _s.read_text(encoding="utf-8", errors="replace")
    # `{% if h.ai_yorum_kart %}` ile bir sonraki dal arasini al:
    # etiket BU dalin icinde olmali. Baska bir dala tasinmis olsa
    # (ornegin kaynak ozetine) vaat tutulmamis olurdu.
    _dal = re.search(r"\{%-?\s*if\s+h\.ai_yorum_kart\s*-?%\}(.*?)"
                     r"\{%-?\s*(?:elif|else|endif)(?![a-z])", _ham, re.S)
    if not _dal:
        return False
    return _OZEL_ETIKET in _sade(_dal.group(1)).lower()


_SABLON_DALI = _sablon_dali_var()

_bakilan = 0
_ozel_toplam = 0
#: Etiketi NE OLURSA OLSUN bulunan kutu sayisi. Mekanizmanin
#: canliligi bununla olculuyor -- "Bu neden kritik?" ve kaynak ozeti
#: dallari AI kotasina bagli degil, her kosuda basiliyor.
_tum_kutu = 0
_tekrar: list[str] = []
for _ad in _SAYFALAR:
    _p = _C / _ad
    if not _p.exists():
        continue
    _bakilan += 1
    _metinler: collections.Counter = collections.Counter()
    for _m in _KUTU.finditer(_p.read_text(encoding="utf-8",
                                          errors="replace")):
        _metin = _sade(_m.group(2))
        if not _metin:
            continue
        _tum_kutu += 1
        if _sade(_m.group(1)).lower() != _OZEL_ETIKET:
            continue
        _metinler[_metin] += 1
    _ozel_toplam += sum(_metinler.values())
    for _metin, _kac in _metinler.items():
        if _kac > 1:
            _tekrar.append(f"{_ad}: {_kac}x  {_metin[:70]}")

esit(_bakilan > 0, True, f"liste sayfalari bulundu ({_bakilan})")

# MEKANIZMA CANLI MI -- gerekce dosya basindaki bolumde.
esit(_tum_kutu > 0, True, f"kart yorum kutusu uretiliyor ({_tum_kutu})")
esit(_SABLON_DALI, True, "sablon 'Netaris yorumu' dalini hala basiyor")

if _ozel_toplam == 0:
    # SESSIZ GECIS YOK: tekrar denetiminin neden bos dondugu yaziliyor.
    print("  not    bu kosuda habere ozel yorum kutusu yok -- yorum"
          " uretilmemis ya da denetimden gecmemis; tekrar denetimi"
          " bos donuyor")
if _tekrar:
    print("\n  AYNI YORUM BIRDEN COK KARTTA:")
    for _t in _tekrar[:8]:
        print(f"    {_t}")
esit(len(_tekrar), 0,
     f"habere ozel yorumlarin hepsi benzersiz ({_ozel_toplam} kutu)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
