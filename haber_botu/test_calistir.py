"""Hat sirasi testleri -- hangi denetim dagitimdan ONCE kosuyor.

BU DOSYA NEDEN VAR
------------------
`calistir.py` dagitim kararini veren dosya ve HIC TESTI YOKTU.

Olculdu (2026-08-28): gizlilik beyani denetimi is akisinda vardi ama
DAGITIMDAN SONRA kosuyordu. Sayfa ayriminda denetim "site TradingView
kullaniyor ama gizlilik metninde hic gecmiyor" dedi ve kosu kirmizi
dondu -- ama site ZATEN YAYIMLANMISTI.

Arac dogru calisti, yanlis anda konustu. Bir beyan denetiminin isi
yanlis beyanla yayina cikmayi ONLEMEK; sonradan haber vermek yalnizca
kaydini tutmak olur.

NEDEN KAYNAK SIRASI SINANIYOR
-----------------------------
Hattin kendisi calistirilamaz: agla konusuyor, AI anahtari istiyor ve
onbes dakika suruyor. Ama sorulan sey bir SIRA sorusu ve o kaynakta
gorunuyor: denetim cagrisi dagitim cagrisindan once mi?

Kaba bir olcut ama tam da kacan seyi yakaliyor. Davranisi degil
SIRAYI koruyor -- ve hata siradaydi.

Calistirma:  python haber_botu/test_calistir.py
"""

from __future__ import annotations

import pathlib
import sys

_gecti = 0
_kaldi: list[str] = []


def dogru(aciklama: str, kosul) -> None:
    global _gecti
    if kosul:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi.append(aciklama)
        print(f"  KALDI  {aciklama}")


KOK = pathlib.Path(__file__).resolve().parent.parent
KAYNAK = (KOK / "calistir.py").read_text(encoding="utf-8")

#: Kod satirlari -- aciklamalar disarida. Bir kural aciklamada
#: gecebilir; sira sorusunun cevabi yalnizca CALISAN kodda.
KOD = "\n".join(s.split("#")[0] for s in KAYNAK.split("\n"))


def _yer(parca: str) -> int:
    return KOD.find(parca)


_dagitim = _yer('"Cloudflare dağıtımı"')
dogru("dagitim cagrisi bulundu", _dagitim != -1)

for ad, parca in (
    ("gizlilik beyani", 'beyan_denetimi.py'),
    ("yorum kapisi", 'yorum_denetimi.py'),
    ("veri denetimi", '"Veri denetimi"'),
    ("site uretimi", '"Site üretimi"'),
):
    yer = _yer(parca)
    dogru(f"{ad} dagitimdan ONCE kosuyor", yer != -1 and yer < _dagitim)

# ENGELLEME: denetim kirmiziysa dagitim YAPILMAMALI. Sirada olmak
# yetmez -- sonucu `ok` degiskenine yazilmali, yoksa denetim kosar ve
# sonucu yok sayilir.
_beyan = _yer("beyan_denetimi.py")
_arasi = KOD[_beyan:_dagitim] if _beyan != -1 and _dagitim != -1 else ""
dogru("beyan denetimi basarisizsa dagitim engelleniyor",
      "ok = False" in _arasi)

# Dagitim `ok` bayragina BAKMALI.
dogru("dagitim ok bayragina bagli",
      "if args.yayinla and ok:" in KOD)

# KRITIK listesi: cikis kodu bu adimlara bakiyor. Beyan denetimi
# listede degilse, engelleme calissa bile kosu YESIL doner ve hata
# gorunmez olur.
# KRITIK LISTESI OZEL OLARAK OKUNUYOR.
#
# Once yalnizca `'"Beyan denetimi"' in KOD` bakiliyordu ve HICBIR SEY
# OLCMUYORDU: ayni dizge `sonuclar["Beyan denetimi"] = bd` satirinda
# da geciyor, yani KRITIK listesinden cikarilsa bile bulunuyordu.
# Bozarak dogrulamada kacti.
_kb = KOD.find("KRITIK = ")
_kritik = KOD[_kb:KOD.index(")", _kb) + 1] if _kb != -1 else ""
dogru("KRITIK listesi bulundu", bool(_kritik))
dogru("beyan denetimi KRITIK listesinde",
      '"Beyan denetimi"' in _kritik)
dogru("dagitim KRITIK listesinde", '"Dağıtım"' in _kritik)

print()
print()
print("Kosu sonucu GitHub ozet sayfasina yaziliyor")
# --------------------------------------------------------------------
# Olculdu (2026-08-28): 16:30 otomasyon kosusu kirmizi dondu. HANGI
# kritik adimin dustugu gunluge basilmisti -- ama Actions gunlukleri
# API'den kimlik dogrulamasi istiyor (403) ve tarayicida da yuzlerce
# satirin altinda kaliyor. 18:30'daki tekrar AYNI KODLA yesil dondu,
# yani sorun gecici bir seydi; ama "hangi adim" cevaplanamadigi icin
# gecici mi kalici mi oldugu da bilinemedi.
#
# Bugun ucuncu kez ayni bicimde karsilasildi: cevap URETILMISTI,
# okunabilir yerde degildi.
# --------------------------------------------------------------------
import importlib.util  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402

_spec = importlib.util.spec_from_file_location("_calistir", KOK / "calistir.py")
_mod = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_mod)
    _yuklendi = True
except Exception as _e:                                # pragma: no cover
    _yuklendi = False
    print(f"  (calistir.py yuklenemedi: {_e})")
dogru("calistir.py ice aktarilabildi", _yuklendi)

if _yuklendi:
    def _ozet(sonuclar, kritik, veri):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / "ozet.md"
            p.write_text("", encoding="utf-8")
            eski = os.environ.get("GITHUB_STEP_SUMMARY")
            os.environ["GITHUB_STEP_SUMMARY"] = str(p)
            try:
                _mod._kosu_ozeti(sonuclar, kritik, veri)
            finally:
                if eski is None:
                    os.environ.pop("GITHUB_STEP_SUMMARY", None)
                else:
                    os.environ["GITHUB_STEP_SUMMARY"] = eski
            return p.read_text(encoding="utf-8")

    _c = _ozet({"Site üretimi": False, "Dağıtım": True},
               ["Site üretimi"], ["FRED"])
    # ADIM ADI TABLODA DA GECIYOR -- bu yuzden ciplak arama YETMEZ.
    # Ilk yazimda `"Site üretimi" in _c` deniyordu ve kritik liste
    # tumuyle kaldirildiginda test YINE YESIL donuyordu: ad, alttaki
    # adim tablosundan esleşiyordu. Mutasyon bunu gosterdi.
    dogru("kritik adim BASLIK ve madde olarak yaziliyor",
          "KRİTİK ADIM BAŞARISIZ" in _c and "- Site üretimi" in _c)
    dogru("guncellenemeyen veri kaynagi yaziliyor", "- FRED" in _c)
    dogru("adim tablosu basiliyor", "| adım | sonuç |" in _c)
    dogru("basarisiz adim tabloda isaretli", "| Site üretimi | ❌ |" in _c)

    # YESIL KOSUDA DA YAZILIYOR. "Yesil ama iki kaynak guncellenemedi"
    # bilgisi kirmizi kadar degerli -- sessiz bozulma boyle basliyor.
    _y = _ozet({"Dağıtım": True}, [], ["EVDS"])
    dogru("kritik hata yokken de ozet yaziliyor", "- EVDS" in _y)

    # CAGRI YERI DE SINANIYOR, yalnizca fonksiyon degil.
    #
    # Yukaridaki sinamalar `_kosu_ozeti`yi DOGRUDAN cagiriyor; cagrinin
    # `main()` icinde KOSULSUZ olup olmadigini olcmuyorlar. Mutasyon
    # (cagriyi `if kritik_hata:` icine almak) bu yuzden KACTI -- ve o
    # mutasyon tam da yesil kosularin ozetsiz kalmasi demekti.
    _cagri = KOD.find("_kosu_ozeti(sonuclar")
    _kosul = KOD.find("if kritik_hata:")
    dogru("ozet cagrisi kaynakta bulundu", _cagri > 0)
    dogru("ozet KOSULSUZ cagriliyor (kritik hata kapisindan ONCE)",
          0 < _cagri < _kosul)

    # Degisken tanimsizken (yerel calistirma) cokmemeli.
    _e = os.environ.pop("GITHUB_STEP_SUMMARY", None)
    try:
        _mod._kosu_ozeti({"a": True}, [], [])
        dogru("degisken tanimsizken cokmuyor", True)
    except Exception as _x:                            # pragma: no cover
        dogru(f"degisken tanimsizken cokmuyor ({_x})", False)
    finally:
        if _e is not None:
            os.environ["GITHUB_STEP_SUMMARY"] = _e

print()
for k in _kaldi:
    print(f"  KALDI  {k}")
print(f"{_gecti} gecti, {len(_kaldi)} kaldi")
sys.exit(1 if _kaldi else 0)
