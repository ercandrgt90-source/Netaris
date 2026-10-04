# -*- coding: utf-8 -*-
"""GIRIS EKRANLARI -- MOBILDE KULLANILABILIR OLMALI.

BU DOSYA NEDEN VAR
------------------
`/giris/`, `/kayit/` ve `/panel/` hicbir sinamanin ADIYLA bakmadigi
sayfalardi. Genis taramalar (guvenlik basligi, kirik baglanti, baski
kurallari, DOM agirligi) onlari da suporuyor ama TURE OZEL hicbir
sozlesme yoktu -- oysa bunlar sitenin tek FORM tasiyan sayfalari ve
okurun en tereddutlu oldugu an orada.

OLCULDU (2026-10-05, 390x844 mobil gorus alani):

  * `/panel/` oturum kapaliyken tek eylemi CUMLE ICINDE bir metin
    baglantisiydi ("Panele girmek icin giris yapin"). Hedef ~52x15
    piksel; dokunma hedefi esigi 44. Okur bos bir karta bakip ne
    yapacagini ariyordu.
  * Kisa sayfalarda altbilgi ekranin ORTASINDA kaliyordu: `/panel/`
    belgesi 493 piksel, masaustu gorus alani 900 -- altinda 407
    piksel ciplak zemin. "Sayfa yuklenmedi" gibi gorunuyor.

Ikisi de duzeltildi. Bu dosya duzeltmelerin ve ZATEN DOGRU OLAN
kararlarin geri gitmesini engelliyor.

NE SINANIYOR
------------
1. Form alanlari: dogru `type`, dogru `autocomplete`, ETIKET
   (placeholder etiket yerine gecmez), `required`.
2. 16 PIKSEL KURALI: iOS, 16 pikselin altindaki bir form alanina
   odaklanildiginda sayfayi YAKINLASTIRIYOR ve geri donmuyor. Kural
   `stil.css` icinde gerekcesiyle yazili; burada korunuyor.
3. `/panel/` oturum kapaliyken GERCEK bir eylem sunuyor (dugme),
   yalnizca cumle ici baglanti degil.
4. Yapiskan altbilgi: kisa sayfa gorus alanini dolduruyor.
5. Bu sayfalardaki her ic baglanti, uretilen bir adrese gidiyor --
   olmayan bir akisa ("sifremi unuttum") baglanti konmasin diye.
"""

from __future__ import annotations

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


# --- 1) 16 piksel kurali (kaynak CSS'ten) ---
_CSS = (_SITE / "statik" / "stil.css").read_text(encoding="utf-8")
_m = re.search(r"\.uyelik-form input,(?:[^{}]*?)\{[^{}]*?font-size:\s*var\(--p-ml\)",
               _CSS, re.S)
esit(bool(_m), True,
     "uyelik formu alanlari --p-ml (16px) aliyor -- iOS yakinlastirmasini onler")
_pml = re.search(r"--p-ml:\s*([^;]+);", _CSS)
esit(bool(_pml) and _pml.group(1).strip() == "1rem", True,
     f"--p-ml gercekten 16px (1rem), gelen: {_pml.group(1).strip() if _pml else None}")

# --- 2) yapiskan altbilgi ---
esit(bool(re.search(r"\bmin-height:\s*100dvh", _CSS)), True,
     "govde 100dvh taban yukseklik aliyor")
esit(bool(re.search(r"^main\s*\{[^}]*flex:\s*1 0 auto", _CSS, re.M)), True,
     "main buyuyor -- altbilgi kisa sayfada dibe iniyor")

# --- 3) uretilen sayfalar ---
_C = _SITE / "cikti"
if not (_C / "index.html").exists():
    print("\n  ATLANDI  cikti yok (once `python site/insa.py`)")
    print(f"\nTUM TESTLER GECTI ({_gecti})")
    raise SystemExit(0)

#: (sayfa, alan adi, beklenen type, beklenen autocomplete)
_ALANLAR = (
    ("giris", "eposta", "email", "email"),
    ("giris", "parola", "password", "current-password"),
    ("kayit", "ad", "text", "name"),
    ("kayit", "eposta", "email", "email"),
    ("kayit", "parola", "password", "new-password"),
)
_sayfalar = {}
for _ad in ("giris", "kayit", "panel"):
    _p = _C / _ad / "index.html"
    esit(_p.exists(), True, f"/{_ad}/ uretildi")
    _sayfalar[_ad] = _p.read_text(encoding="utf-8", errors="replace")

for _sayfa, _alan, _tur, _oto in _ALANLAR:
    _s = _sayfalar[_sayfa]
    _im = re.search(rf'<input[^>]*name="{re.escape(_alan)}"[^>]*>', _s)
    esit(bool(_im), True, f"/{_sayfa}/ icinde `{_alan}` alani var")
    _et = _im.group(0)
    esit(bool(re.search(rf'type="{_tur}"', _et)), True,
         f"/{_sayfa}/ {_alan}: type={_tur}")
    esit(bool(re.search(rf'autocomplete="{_oto}"', _et)), True,
         f"/{_sayfa}/ {_alan}: autocomplete={_oto}")
    esit("required" in _et, True, f"/{_sayfa}/ {_alan}: required")
    # ETIKET: `id` uzerinden `<label for>` ya da sarmalayan <label>.
    _id = re.search(r'id="([^"]+)"', _et)
    _etiketli = bool(_id and f'for="{_id.group(1)}"' in _s)
    if not _etiketli:
        # sarmalayan label: alandan geriye dogru en yakin <label>
        _ic = _s[:_im.start()]
        _etiketli = _ic.rfind("<label") > _ic.rfind("</label>")
    esit(_etiketli, True,
         f"/{_sayfa}/ {_alan}: ETIKETI var (placeholder etiket sayilmaz)")

# --- 4) panel oturum kapaliyken gercek eylem sunuyor ---
_pm = re.search(r"<div data-giris-gerek[^>]*>(.*?)</div>", _sayfalar["panel"], re.S)
esit(bool(_pm), True, "/panel/ oturum-gerekli blogu var")
_blok = _pm.group(1)
_dugmeler = re.findall(r'<a[^>]*class="[^"]*\bdugme\b[^"]*"[^>]*href="([^"]+)"', _blok)
esit(len(_dugmeler) >= 1, True,
     f"/panel/ oturum kapaliyken DUGME sunuyor ({len(_dugmeler)})")
esit("/giris/" in _dugmeler, True, "/panel/ birincil eylemi /giris/")

# --- 5) olmayan adrese baglanti yok ---
_kirik = []
for _ad, _s in _sayfalar.items():
    for _h in set(re.findall(r'href="(/[^"#?]*)"', _s)):
        _y = _h.strip("/")
        if not _y:
            continue
        if (_C / _y).exists() or (_C / _y / "index.html").exists():
            continue
        _kirik.append(f"/{_ad}/ -> {_h}")
if _kirik:
    print(f"\n  HEDEFI OLMAYAN BAGLANTI: {len(_kirik)}")
    for _k in _kirik[:8]:
        print(f"    {_k}")
esit(_kirik, [], "giris ekranlarinda olmayan adrese baglanti yok")

print(f"\nTUM TESTLER GECTI ({_gecti})")
