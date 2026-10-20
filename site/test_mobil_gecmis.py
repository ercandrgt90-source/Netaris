# -*- coding: utf-8 -*-
"""OKUMA GECMISI CIHAZDA KALMALI -- VE "BEKLEYEN" LISTESI DURUST OLMALI.

BU DOSYA NEDEN VAR
------------------
Iki ayri soz veriliyor ve ikisi de SESSIZCE bozulabilir.

1. GIZLILIK SOZU. Okuma gecmisi `mobil/src/gecmis.ts` icinde yalnizca
   cihazda tutuluyor. Hem uygulama ekraninda hem gizlilik metninde
   "hicbir yere gonderilmiyor" yaziyor. O module bir gun bir `fetch`
   eklenirse yazili soz YALAN olur ve hicbir sey kirmizi yanmaz --
   ozellik calismaya devam eder, yalnizca anlattigimiz sey degisir.

   Okurun ne okudugunu sunucuda biriktirmek ayrica gizlilik
   metnindeki "profilleme yapilmiyor" cumlesini asindirirdi. Bu
   yuzden sunucuda tutulmamasi bir eksik degil, KARAR.

2. DURUSTLUK SOZU. Profil ekranindaki `BEKLEYEN` listesi "henuz
   baglanmamis" bolumleri sayiyor. Olculdu (2026-10-19): listede
   "Senaryo yazma -- ekran bir sonraki surumde" yaziyordu, oysa ekran
   AYNI GUN eklenmisti. Yapilmis bir isi "henuz yok" diye gostermek,
   okura yanlis bilgi vermektir -- ve sartnamenin kendi kurali
   ("tamamlanmis izlenimi verme") ters yonden de gecerli: VAR olani
   yok gostermek de yanlis bilgidir.

   Bu kusur yorumla onlenmeye calisilmisti ("BU LISTE GUNCEL TUTULMAK
   ZORUNDA"). Yorum bir kapi degil.

NE SINANIYOR
------------
1. `gecmis.ts` agla konusmuyor.
2. Kayit sinirli ve siniri gercekten uyguluyor.
3. Detay ekranlari yalnizca GERCEK veri geldiginde kayit dusuyor.
4. Ekrani olan hicbir bolum `BEKLEYEN` listesinde durmuyor.
"""

from __future__ import annotations

import pathlib
import re

_KOK = pathlib.Path(__file__).resolve().parent.parent
_MOBIL = _KOK / "mobil"
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def _kodu(metin: str) -> str:
    """Yorumlari ayiklar: aciklama metni kanit sayilmamali."""
    metin = re.sub(r"/\*[\s\S]*?\*/", " ", metin)
    return re.sub(r"(?m)^\s*//.*$", " ", metin)


print("Gecmis modulu cihazda kaliyor")
_g_yol = _MOBIL / "src" / "gecmis.ts"
esit(_g_yol.exists(), True, "src/gecmis.ts var")
_g = _kodu(_g_yol.read_text(encoding="utf-8"))

# AG CAGRISI YOK. Yorumda "fetch YOK" yazmasi yetmiyor -- yorum
# ayiklandiktan sonra KODDA aranıyor.
_ag = [k for k in ("fetch(", "XMLHttpRequest", "WebSocket", "axios",
                   "api.", "TABAN") if k in _g]
esit(_ag, [], "gecmis.ts hicbir ag cagrisi tasimiyor")

# Kayit sinirli ve sinir UYGULANIYOR.
esit(bool(re.search(r"EN_COK\s*=\s*\d+", _g)), True,
     "kayit sayisi sinirli (EN_COK)")
esit("slice(0, EN_COK)" in _g, True, "sinir gercekten uygulaniyor")

# Depo anahtari tek yerde ve yalnizca gecmise ait.
esit(len(re.findall(r'ANAHTAR\s*=\s*"netaris\.gecmis"', _g)), 1,
     "depo anahtari tek yerde tanimli")

print("\nYalnizca GERCEK veri kayit dusuyor")
# Okunmamis bir seyi "okundu" diye listelemek, okura yanlis bilgi
# vermek olurdu. Iki detay ekraninin ikisi de korumali olmali.
for _ad, _degisken in (("haber", "h"), ("analiz", "a")):
    _p = _MOBIL / "app" / _ad / "[slug].tsx"
    esit(_p.exists(), True, f"app/{_ad}/[slug].tsx var")
    _m = _kodu(_p.read_text(encoding="utf-8"))
    esit("gecmis.kaydet(" in _m, True, f"{_ad}: okuma kaydediliyor")
    # Veri gelmeden kayit dusmemeli.
    esit(bool(re.search(r"if\s*\(!\s*" + _degisken
                        + r"\.veri\?\.baslik\)\s*return;", _m)), True,
         f"{_ad}: veri gelmeden kayit DUSMUYOR")

print("\n`BEKLEYEN` listesi durust")
_profil = (_MOBIL / "app" / "(sekmeler)" / "profil.tsx").read_text(
    encoding="utf-8")
_blok = re.search(r"const BEKLEYEN[^=]*=\s*\[(.*?)\n\];", _profil, re.S)
esit(_blok is not None, True, "BEKLEYEN listesi bulundu")
_adlar = re.findall(r'ad:\s*"([^"]+)"', _blok.group(1))
print(f"  liste: {_adlar}")

#: Bolum adi -> o bolumun ekrani. Ekran VARSA ad listede DURAMAZ.
#:
#: Tablo elle yaziliyor ve bilerek: ad ile dosyayi otomatik
#: eslestirmek (basligi slug'a cevirip dosya aramak) yanlis negatif
#: uretirdi -- eslesme tutmazsa sinama sessizce "sorun yok" derdi.
EKRANI_OLAN = {
    "Okuma geçmişi": "app/gecmis.tsx",
    "Senaryo yazma": "app/senaryo-yaz.tsx",
    "Arama": "app/ara.tsx",
    "Ekonomik takvim": "app/takvim.tsx",
    "Hesabımı sil": "app/hesap-sil.tsx",
}
_yanlis = []
for _bolum, _ekran in EKRANI_OLAN.items():
    if (_KOK / "mobil" / _ekran).exists() and _bolum in _adlar:
        _yanlis.append(f"{_bolum} -> {_ekran} VAR ama listede duruyor")
if _yanlis:
    print("\n  YAPILMIS ISI 'HENUZ YOK' DIYE GOSTERIYOR:")
    for _y in _yanlis:
        print(f"    {_y}")
esit(_yanlis, [], "ekrani olan hicbir bolum BEKLEYEN listesinde degil")

# Tablonun kendisi curumesin: saydigi ekranlarin en az biri gercekten
# var olmali, yoksa yukaridaki dongu hicbir seyi kontrol etmez.
_mevcut = [e for e in EKRANI_OLAN.values() if (_KOK / "mobil" / e).exists()]
esit(len(_mevcut) >= 3, True,
     f"tablo gercek ekranlara deginiyor ({len(_mevcut)}/{len(EKRANI_OLAN)})")

print("\nBelge ile uygulama ayni seyi soyluyor")
# IKI YER AYNI SEYI KARARA BAGLIYOR: uygulamadaki `BEKLEYEN` listesi ve
# `MOBIL-DENETIM.md` icindeki "Henuz yapilmayanlar" bolumu. Biri
# guncellenip oteki unutuldugunda hicbir sey bozulmaz -- yalnizca
# ikisinden biri YALAN soyler. Bu depoda tanidik kusur sinifi.
#
# Olcut "birebir ayni" DEGIL: belge daha fazlasini izleyebilir
# (ornegin uygulamada hic gorunmeyen bir ozellik). Tutulan sey tek
# yonlu -- UYGULAMANIN bekliyor dedigi her sey BELGEDE de bekliyor
# olmali. Tersi, okura "yapilmadi" deyip belgede "yapildi" yazmakti.
_belge = (_KOK / "MOBIL-DENETIM.md").read_text(encoding="utf-8")
_bolum = re.search(r"###[ ]*Hen[uuü]z yap[iiı]lmayanlar(.*?)"
                   r"(?:\n##|$)", _belge, re.S)
# TEK BIR GUNCEL BOLUM OLMALI.
#
# Olculdu (2026-10-20): belgede IKI tane "Henuz yapilmayanlar" basligi
# vardi. Ilki 18 Ekim gunlugunun icindeydi ve yedi madde sayiyordu --
# yedisi de o tarihten sonra yapilmisti. Baslik tarihsiz oldugu icin
# BUGUNKU durum gibi okunuyordu. Gunluk geriye donuk silinmedi,
# TARIHLENDIRILDI; bu iddia da ayni seyin tekrarini engelliyor.
_tumu = re.findall(r"###[ ]*Hen[uuü]z yap[iiı]lmayanlar",
                   _belge)
esit(len(_tumu), 1,
     f"belgede TEK bir guncel bekleyenler bolumu var ({len(_tumu)})")
esit(_bolum is not None, True, "belgedeki bekleyenler bolumu bulundu")
_madde = _bolum.group(1)

#: Uygulamadaki ad -> belgede aranacak anahtar. Adlar birebir ayni
#: yazilmiyor, o yuzden esleme ELLE. Eslemesi olmayan bir ad da
#: KIRMIZI yaniyor: sessizce atlanan madde, hic kontrol edilmeyen
#: madde demek.
BELGE_ANAHTARI = {
    "Bildirimler": "Bildirimler",
    "Google ile giriş (uygulama içi)": "Google ile giriş",
}
_eksik = []
for _ad in _adlar:
    _anahtar = BELGE_ANAHTARI.get(_ad)
    if _anahtar is None:
        _eksik.append(f"{_ad} -> esleme tablosunda YOK")
    elif _anahtar not in _madde:
        _eksik.append(f"{_ad} -> belgede bekleyen olarak gecmiyor")
if _eksik:
    print("\n  UYGULAMA ILE BELGE AYRISMIS:")
    for _e in _eksik:
        print(f"    {_e}")
esit(_eksik, [],
     f"uygulamanin bekleyenleri belgede de bekliyor ({len(_adlar)} madde)")

print(f"\nTUM TESTLER GECTI ({_gecti})")
