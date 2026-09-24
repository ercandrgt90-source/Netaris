# -*- coding: utf-8 -*-
"""TICARI KAYNAK GOSTERILIYORSA BAGLANTISI DA GOSTERILIR.

BU DOSYA NEDEN VAR
------------------
Deponun kendi kurali acik (`haber_botu/kaynak/besleme.py`):

    RSS yayimlamak "basligi al, ozetle, bana baglanti ver" davetidir;
    "kaynagi sil, kendi icerigin gibi sun" degil. Bu yuzden
    `ticari=True` olan her ogede kaynak adi ve baglanti SAKLANIR ve
    sayfada gosterilir.

Olculdu (2026-09-24): `/gundem/` sayfasinin "Diger duyurular"
listesinde 96 oge vardi; 69'u ticari kaynaktandi (FinancialJuice 46,
Investing 5, Cointelegraph 5, Dunya 4) ve HICBIRI kaynaga
baglanmiyordu. Kaynak ADI yaziyordu, baglantisi yoktu.

VARSAYIM SEBEBINDEN SONRA DA YASAMIS
------------------------------------
Sablondaki gerekce "bunlar yorum gerektirmeyen idari bildirimler"
diyordu ve DUZENLEYICILER icin dogruydu. Liste sonradan ticari ajans
basliklariyla doldu; gerekce yerinde kaldi, dayanagi kayboldu.

Bu ogelerin kendi sayfasi YOK -- yani baglanti sayfanin baska bir
yerinde de degildi, hicbir yerde degildi. Kart rozetiyle karistirmamak
gerekiyor: kart bizim sayfamiza gider ve o sayfa kunyede kaynaga
baglanir; zincir orada kapaniyor.

NE SINANIYOR
------------
1. Ticari kaynak listesi hala ticari isaretli (kural bosaltilmamis).
2. `/gundem/` rutin listesinde ticari oge kaynagina BAGLANIYOR.
3. Baglanti gercekten dis adres ve `rel` korumalari yerinde.
4. Resmi kurum ogesi baglanmak ZORUNDA degil (kamu belgesi) --
   kural gereginden fazla genisletilmemis.
5. Kontrolun kendisi calisiyor: baglantisiz ticari oge YAKALANIYOR.
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"
sys.path[:0] = [str(_SITE.parent)]

from haber_botu.kaynak import besleme  # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Bu dosyanin BILDIGI ticari kaynaklar -- `besleme.py`den OKUNMUYOR.
#:
#: Kaynak kumesini yalnizca `besleme.py`den almak, korumayi hareketli
#: hedefe cevirirdi: biri `ticari=False` yaparsa kume kuculur, iddia
#: da kuculur ve sinama YESIL kalir. Asagidaki adlar elle yaziyor.
BILINEN_TICARI = {"FinancialJuice", "Investing", "Dünya", "Ekonomim",
                  "Cointelegraph", "AA"}

print("\nKaynak siniflandirmasi")
_ticari = {t[1] for t in besleme.BESLEMELER if t[6]}
_resmi = {t[1] for t in besleme.BESLEMELER if not t[6]}
_kaymis = sorted(BILINEN_TICARI - _ticari)
if _kaymis:
    print(f"\n  ARTIK TICARI SAYILMAYAN: {_kaymis}")
esit(_kaymis, [], f"bilinen ticari kaynaklar hala ticari ({len(_ticari)} kaynak)")
esit("TCMB" in _resmi and "ECB" in _resmi, True,
     "resmi kurumlar ticari sayilmiyor (kural gereginden genis degil)")

print("\nUretilen ciktida")
_g_yol = _CIKTI / "gundem" / "index.html"
if not _g_yol.exists():
    print("  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

_g = _g_yol.read_text(encoding="utf-8", errors="replace")
_blok = re.search(r'data-akis-kap="rutin".*?</ul>', _g, re.S)
esit(_blok is not None, True, "rutin duyuru listesi sayfada var")
_ogeler = re.findall(r"<li\b.*?</li>", _blok.group(0), re.S)
esit(len(_ogeler) > 0, True, f"rutin oge var ({len(_ogeler)})")


def _kaynak_adi(oge: str) -> str:
    """Ogede yazan kaynak adi -- bagli ya da bagsiz, FARK ETMEZ."""
    m = re.search(r'<(?:span|a) class="rozet(?! rozet-vurgu)[^"]*"[^>]*>'
                  r'\s*([^<]{1,40}?)\s*</(?:span|a)>', oge)
    return m.group(1).strip() if m else ""


_baglantisiz, _ticari_oge, _resmi_oge = [], 0, 0
for _o in _ogeler:
    _ad = _kaynak_adi(_o)
    if _ad in _ticari:
        _ticari_oge += 1
        if not re.search(r'<a[^>]+href="https?://', _o):
            _baglantisiz.append(_ad)
    elif _ad in _resmi:
        _resmi_oge += 1

esit(_ticari_oge > 0, True,
     f"listede ticari oge var ({_ticari_oge} ticari, {_resmi_oge} resmi)")
if _baglantisiz:
    print(f"\n  BAGLANTISIZ TICARI OGE: {len(_baglantisiz)} "
          f"({sorted(set(_baglantisiz))})")
esit(_baglantisiz, [],
     f"her ticari oge kaynagina BAGLANIYOR ({_ticari_oge} oge)")

print("\nBaglantinin kendisi dogru")
_baglar = re.findall(r'<a class="rozet rozet-kaynak-bag"[^>]*>', _blok.group(0))
esit(len(_baglar) >= _ticari_oge, True,
     f"her ticari oge icin bir kunye bagi ({len(_baglar)})")
_korumasiz = [b for b in _baglar if "nofollow" not in b or "noopener" not in b]
esit(_korumasiz[:2], [],
     "her kunye bagi `rel=\"nofollow noopener\"` tasiyor")

print("\nKural gereginden GENIS degil")
# Resmi kurum duyurusu kamu belgesi; disari yonlendirme yoklugu
# bilincli bir karar ve bu sinama onu ZORLAMIYOR.
esit(_resmi_oge > 0, True,
     f"resmi kurum ogeleri de listede duruyor ({_resmi_oge})")

print("\nKONTROLUN KENDISI CALISIYOR MU")
# Baglantisiz bir ticari oge UYDURULUYOR ve yakalanmasi bekleniyor.
# Mekanizmayi kendi sinamasindan gecirmemek, bu oturumda mutasyonu
# defalarca sessizce yesil birakan kusurdu.
_sahte = ('<li class="gundem-oge gundem-duz">'
          '<span class="rozet rozet-vurgu">Enflasyon</span>'
          '<span class="rozet">FinancialJuice</span>'
          '<span class="gundem-baslik">Uydurma baslik</span></li>')
esit(_kaynak_adi(_sahte), "FinancialJuice", "kaynak adi okunabiliyor")
esit(bool(re.search(r'<a[^>]+href="https?://', _sahte)), False,
     "baglantisiz ticari oge YAKALANIYOR (kural sahte degil)")

# Ters yon: bagli oge yanlislikla yakalanmiyor.
_saglam = _sahte.replace(
    '<span class="rozet">FinancialJuice</span>',
    '<a class="rozet rozet-kaynak-bag" href="https://financialjuice.com/x" '
    'rel="nofollow noopener">FinancialJuice</a>')
esit(_kaynak_adi(_saglam), "FinancialJuice", "bagli ogede de ad okunuyor")
esit(bool(re.search(r'<a[^>]+href="https?://', _saglam)), True,
     "bagli oge sorunlu sayilmiyor (yanlis pozitif yok)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
