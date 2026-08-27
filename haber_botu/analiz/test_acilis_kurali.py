"""Acilis cumlesi kuralinin UC YOLDA da ayni olmasini sinar.

NE OLMUSTU
----------
"Acilis sayfaya cikar mi?" sorusunun cevabi uc ayri yerde ELLE
tekrarlaniyordu:

    sablon (haber.html)   {% if dosya.acilis and not dosya.dolu %}
    dogrulama (insa.py)   if not d.dolu: ...
    AI girdisi            if d.acilis:            <-- KOSULSUZ

Ucuncusu ayristi. Olculdu (2026-08-27): 104 AI yorumu dogrulama
suzgecine takildi ve en cok kacan sayilar sunlardi --

    9,5 (91 kez), 95,29 (85), 12,5 (42)

Ucu de ayni yerden geliyordu: acilis cumlesindeki Brent verisi
("Brent 95,29 dolara ulasti, ayda %9,5 yukselis"). Kutu basilan
sayfada acilis BASILMIYOR, yani model sayfada hicbir yerde
gorunmeyen bir fiyati alintiliyordu.

Zarar iki kereydi: once AI cagrisi harcaniyor, sonra uretilen yorum
suzgece takilip cope gidiyordu. Kimse fark etmedi cunku her iki
tarafta da davranis "dogru" gorunuyordu.

NEDEN KAYNAK TARAMASI DA VAR
----------------------------
Ozelligin dogru calismasi yetmiyor: asil risk birinin ileride kurali
YENIDEN ELLE yazmasi. Bu yuzden test yalnizca davranisi degil,
kuralin TEK YERDE durdugunu da sinar.

Calistirma:  python analiz/test_acilis_kurali.py
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from dosya import Dosya  # noqa: E402

_gecti = 0
_kaldi = 0


def dogru(aciklama: str, kosul) -> None:
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")


KOK = pathlib.Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------
# 1. DAVRANIS
# --------------------------------------------------------------------
dogru("acilis var, kutu yok -> basilir",
      Dosya(acilis="Brent 95,29 dolar").acilis_basilir)

dogru("acilis var, turkiye kutusu var -> BASILMAZ",
      not Dosya(acilis="Brent 95,29 dolar",
                turkiye=[object()]).acilis_basilir)

dogru("acilis var, izlenecekler var -> BASILMAZ",
      not Dosya(acilis="x", izlenecekler=("y",)).acilis_basilir)

dogru("acilis var, duyarlilik var -> BASILMAZ",
      not Dosya(acilis="x", duyarlilik=(("Bankacilik", 1, "z"),)
                ).acilis_basilir)

dogru("acilis yok -> basilmaz",
      not Dosya(acilis="").acilis_basilir)

# `dolu` ile tutarli: ikisi ayni gercegin iki yuzu.
_d = Dosya(acilis="x", turkiye=[object()])
dogru("dolu dogruyken acilis_basilir yanlis",
      _d.dolu and not _d.acilis_basilir)

# --------------------------------------------------------------------
# 2. UC YOL DA OZELLIGI KULLANIYOR
# --------------------------------------------------------------------
YOLLAR = {
    "sablon": KOK / "site" / "sablonlar" / "haber.html",
    "dogrulama": KOK / "site" / "insa.py",
    "ai girdisi": KOK / "haber_botu" / "uret_ai_yorum.py",
}
for ad, yol in YOLLAR.items():
    metin = yol.read_text(encoding="utf-8", errors="replace")
    dogru(f"{ad} acilis_basilir kullaniyor",
          "acilis_basilir" in metin)

# --------------------------------------------------------------------
# 3. KURAL ELLE YENIDEN YAZILMAMIS.
#
# Aciklama satirlari kurali ANLATIYOR ve anlatmali; yalnizca CALISAN
# kod taranıyor. Aranan sey: ayni ifadede hem `acilis` hem `dolu`
# gecen bir kosul -- yani ozelligin elle kopyalanmis hali.
# --------------------------------------------------------------------
def _kodu(metin: str, sablon: bool) -> str:
    if sablon:
        # Jinja aciklamalari {# ... #}
        return re.sub(r"\{#.*?#\}", " ", metin, flags=re.S)
    return "\n".join(s.split("#")[0] for s in metin.split("\n"))


ELLE = re.compile(r"acilis[^\n]{0,60}\bdolu\b|\bdolu\b[^\n]{0,60}acilis")
for ad, yol in YOLLAR.items():
    kod = _kodu(yol.read_text(encoding="utf-8", errors="replace"),
                yol.suffix == ".html")
    bulunan = ELLE.findall(kod)
    dogru(f"{ad} kurali elle yeniden yazmiyor",
          not bulunan)

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
