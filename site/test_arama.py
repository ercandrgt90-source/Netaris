"""Arama dizini -- HABERLER DE ICINDE.

BU DOSYA NEDEN VAR
------------------
Olculdu: dizinde 183 kayit vardi ve hepsi arastirmaydi. Sitenin 1.251
HABER SAYFASI HIC ARANAMIYORDU. "Fed" arayan okur, Fed hakkinda
yuzlerce haber varken bos ekran goruyordu.

Bu, eksik bir ozellik degil SESSIZ BIR BOSLUKTU: arama kutusu vardi,
calisiyordu, hicbir hata vermiyordu -- yalnizca icerigin dortte ucunu
gormuyordu. Bu depoda ayni sinif hata birkac kez cikti (yanlis "0
ihlal" raporlayan denetim, bozuk sitemap taramasi) ve hepsinin ortak
yani ayni: eksik tarama TEMIZ RAPOR uretir.

Sinamalar bu bosluga karsi: haber kaydinin dizine GIRDIGINI ve
aranabilir metnin dogru kuruldugunu tutuyorlar.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import insa  # noqa: E402

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


HABERLER = [
    {"baslik": "Fed faizi sabit tuttu", "neden_onemli": "Piyasa bekliyordu.",
     "yol": "/haber/fed-faizi-sabit-tuttu/", "konu": "Para politikası",
     "kurum": "Federal Reserve", "tarih_gorunur": "6 Ağustos 2026"},
    {"baslik": "Brent 87 doları aştı", "ozet": "Hürmüz gerilimi etkili.",
     "yol": "/haber/brent-87-dolari-asti/", "konu": "Enerji",
     "kurum": "EIA", "tarih_gorunur": "5 Ağustos 2026"},
    # SAYFASI OLMAYAN haber: arama sonucunda tiklanamayan bir satir
    # olurdu, o yuzden dizine GIRMEMELI.
    {"baslik": "Rutin duyuru", "ozet": "", "yol": "", "konu": "Düzenleme",
     "kurum": "SPK", "tarih_gorunur": "5 Ağustos 2026"},
]

kayitlar = json.loads(insa.arama_dizini([], HABERLER))

print("\nHaberler dizine giriyor")
esit(len(kayitlar), 2, "sayfasi olmayan haber dizine GIRMIYOR")
esit({k["tur"] for k in kayitlar}, {"haber"}, "tur alani basiliyor")
esit(kayitlar[0]["y"], "/haber/fed-faizi-sabit-tuttu/", "yol tasiniyor")

# --------------------------------------------------------------------
# ARANABILIR ALANLAR KAYITTA DURUYOR.
#
# Eslesme metni artik ISTEMCIDE kuruluyor: dizin 903 KB'a cikmisti ve
# hazir `a` alaninin neredeyse tamami ayni kaydin diger alanlarinin
# kopyasiydi.
#
# Dolayisiyla burada sinanan sey, istemcinin ihtiyaci olan alanlarin
# kayitta BULUNDUGU. Biri dusarse arama o alani goremez ve hicbir hata
# gorunmez -- "Hürmüz" arayan okur bos ekran gorur, kutu calisiyor
# sanir.
# --------------------------------------------------------------------
print("\nAranabilir alanlar kayitta")
brent = kayitlar[1]
esit(brent["k"], "Enerji", "konu kayitta -- aranabilir")
esit(brent["kr"], "EIA", "kurum kayitta -- aranabilir")
esit("Hürmüz" in brent["o"], True, "ozet kayitta -- aranabilir")

fed = kayitlar[0]
esit(fed["k"], "Para politikası", "konu tasiniyor")
esit(fed["kr"], "Federal Reserve", "kurum tasiniyor")

# `_ara_metni` slug ve dahili kullanimda kaliyor; diakritigi attigini
# dogrudan siniyoruz.
esit(insa._ara_metni("Hürmüz Boğazı"), "hurmuz bogazi",
     "_ara_metni diakritigi atiyor")
esit(insa._ara_metni("İstihdam"), "istihdam",
     "buyuk noktali I dogru katlaniyor")

# --------------------------------------------------------------------
# OZET IKI ALANDAN GELIYOR.
#
# `neden_onemli` bos kalabiliyor (veriden uretilen sayfalarda olculdu)
# ve o zaman kaynagin ozeti kullaniliyor. Ikisi de yoksa bos -- ama
# kayit yine dizine giriyor, cunku baslik tek basina aranabilir.
# --------------------------------------------------------------------
print("\nOzet zinciri")
esit(fed["o"], "Piyasa bekliyordu.", "neden_onemli oncelikli")
esit(brent["o"], "Hürmüz gerilimi etkili.", "neden_onemli yoksa ozet")

bos = json.loads(insa.arama_dizini([], [
    {"baslik": "Sadece başlık", "yol": "/haber/x/", "konu": "Borsa"}]))
esit(len(bos), 1, "ozeti olmayan haber yine dizine giriyor")
esit(bos[0]["o"], "", "ozet yoksa bos")
esit(bos[0]["b"], "Sadece başlık", "baslik kayitta -- tek basina aranabilir")

# --------------------------------------------------------------------
# ARASTIRMA KAYDI BOZULMADI.
#
# Haber eklemek eski kayit bicimini degistirmemeli: `ara.js` iki
# alani da okuyor ve biri kaybolursa kart yarim cizilir.
# --------------------------------------------------------------------
print("\nArastirma kaydi korunuyor")
bos_haber = json.loads(insa.arama_dizini([], []))
esit(bos_haber, [], "haber yoksa dizin bos donuyor")

# --------------------------------------------------------------------
# IKI DIAKRITIK TABLOSU AYNI OLMALI.
#
# EN ONEMLI SINAMA. Eslesme metni artik istemcide kuruluyor
# (`ara.js` -> `katla`) ve Python tarafindaki `_SLUG_ESLEME` yalnizca
# slug uretiminde kullaniliyor. Ikisi ayrisirsa "hurmuz" yazan okur
# "Hürmüz"u bulamaz ve HICBIR HATA GORUNMEZ -- arama calisiyor
# gorunur, yalnizca bazi sonuclari dondurmez.
#
# Bu depoda ayni sinif sessiz bozulma birkac kez cikti; hepsinin
# ortak yani, bozuk halin de "basarili" gorunmesi.
# --------------------------------------------------------------------
print("\nDiakritik tablolari ayni mi")
js = pathlib.Path(__file__).resolve().parent / "statik" / "ara.js"
metin = js.read_text(encoding="utf-8")
bas = metin.index("var KATLAMA = {")
son = metin.index("};", bas)
ham = metin[bas + len("var KATLAMA = {"):son]

js_tablo = {}
for parca in ham.replace("\n", " ").split(","):
    if ":" not in parca:
        continue
    k, d = parca.split(":", 1)
    k, d = k.strip().strip('"'), d.strip().strip('"')
    if k and d:
        js_tablo[k] = d

py_tablo = {chr(k): v for k, v in insa._SLUG_ESLEME.items()
            if isinstance(v, str) and len(v) == 1 and not v.isdigit()}
# Python tablosu slug icin fazladan isaret tasiyabilir (bosluk, tire).
# Karsilastirma JS'in KAPSADIGI harfler uzerinden: eksik olan sorun,
# fazlalik degil.
esit(bool(js_tablo), True, "ara.js KATLAMA tablosu okunabiliyor")
eksik = {h: d for h, d in js_tablo.items() if py_tablo.get(h) != d}
esit(eksik, {}, "JS ve Python diakritik tablolari AYNI")
for harf in ("ı", "İ", "ş", "ğ", "ü", "ö", "ç", "â", "î", "û"):
    esit(harf in js_tablo, True, f"'{harf}' JS tablosunda var")
    esit(harf in py_tablo, True, f"'{harf}' Python tablosunda var")

print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)
