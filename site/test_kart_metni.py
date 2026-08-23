"""Kart, bolumunun vaadini tutmali -- bos kart olmasin.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): `/gundem/` sayfasindaki "Piyasa etkisi olanlar"
bolumunde 35 kartin 12'sinde HICBIR metin yoktu -- ne Netaris yorumu,
ne kaynagin ozeti, ne baska bir sey. Okur yalnizca bir baslik ve
"Haberi oku ->" goruyordu.

Bolumun adi "piyasa etkisi olanlar" iken kart o etkiye dair TEK
KELIME etmiyordu. Bu yalnizca bir bosluk degil, verilmis bir sozun
tutulmamasi.

Hicbir hata gorunmuyordu: sablonda `{% if %}` dallari var, veri
eksikse blok basilmiyor ve kart yine de gecerli cikiyor. Kartin bos
oldugu ancak SAYFAYA BAKINCA goruluyordu -- ve orada da 23 kart dolu
oldugu icin goze carpmiyordu.

NASIL DOLDURULUYOR (sirayla)
    1. ai_yorum_kart   modelin yazdigi degerlendirme
    2. ozet_kart       KAYNAGIN kendi ozeti (oyle de etiketleniyor)
    3. neden_kart      sitenin kendi "bu neden kritik" cikarimı

Ucu de AYRI ETIKETLE basiliyor. Kimin sozu oldugu hicbir zaman
belirsiz kalmiyor -- bu sitenin en temel kurali.

NE SINANMIYOR
-------------
Metnin KALITESI degil VARLIGI. Kalite ayri denetimlerin isi
(`yorum_denetimi.py`, `beyan_denetimi.py`).
"""

from __future__ import annotations

import pathlib
import re
import sys

_SITE = pathlib.Path(__file__).resolve().parent
_CIKTI = _SITE / "cikti"

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


_sayfa = _CIKTI / "gundem" / "index.html"

print("\nPiyasa etkisi olan kartlarda metin var")
if not _sayfa.exists():
    print("  ATLANDI  cikti yok (once `python insa.py`)")
    print(f"\n{_gecti} gecti, {_kaldi} kaldi")
    raise SystemExit(0)

_m = _sayfa.read_text(encoding="utf-8")
_i = _m.find('data-akis-kap="yorumlu"')
_j = _m.find('data-akis-kap="', _i + 20)
_kartlar = re.findall(r'<article class="haber.*?</article>',
                      _m[_i:_j if _j > 0 else len(_m)], re.S)

esit(len(_kartlar) > 0, True, f"bolum kart tasiyor ({len(_kartlar)})")

_bos = [k for k in _kartlar if "kart-yorum-metin" not in k]
esit(len(_bos), 0, "metinsiz kart yok")

# --------------------------------------------------------------------
# UC KAYNAGIN DA ETIKETI AYRI OLMALI.
#
# Metnin var olmasi yetmez: okur o cumlenin KIMIN sozu oldugunu
# bilmeli. "Netaris yorumu" ile kaynagin ozeti ayni kutuda ayni
# gorunumle basilsaydi, ajansin cumlesi bizim degerlendirmemiz gibi
# okunurdu.
# --------------------------------------------------------------------
print()
print("Her metnin kaynagi etiketli")
_etiketli = [k for k in _kartlar
             if "kart-yorum-metin" in k and "kart-yorum-etiket" in k]
esit(len(_etiketli), len(_kartlar) - len(_bos),
     "metni olan her kartta etiket de var")

_tur = {
    "Netaris yorumu": sum(1 for k in _kartlar if "Netaris yorumu" in k),
    "kaynak ozeti": sum(1 for k in _kartlar if "kart-yorum-kaynak" in k),
    "bu neden kritik": sum(1 for k in _kartlar if "kart-yorum-neden" in k),
}
print(f"         dagilim: {_tur}")
esit(sum(_tur.values()), len(_kartlar) - len(_bos),
     "her metin uc turden birine ait (sinifsiz kutu yok)")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
