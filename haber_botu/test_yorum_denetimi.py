"""Yorum kapisi: OKURUN GORDUGU metni denetler, depodakini degil.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-24): kullanici "haberler akmiyor" dedi ve haklıydi.
Canli sitede en yeni haber bir gun eskiydi, oysa CI saat basi haber
topluyor ve depoya yaziyordu -- `gundem.json` icinde o gune ait
altmis dokuz haber duruyordu.

Zincir su:

    yorum_denetimi.py  ->  18 ihlal, cikis kodu 1
    calistir.py        ->  ok = False
    `if args.yayinla and ok:`  ->  DAGITIM HIC CALISMADI

Yani haberler depoya akiyor, okura ulasmiyordu. Site donmustu ve
hicbir yerde "site donmus" yazmiyordu.

ON SEKIZ IHLALIN HEPSI SAHTEYDI
-------------------------------
  * 16'si sayfada HIC BASILMAYAN yorumlardi. `insa.py` onlari zaten
    eliyor. Kapi, okurun goremedigi bir metin yuzunden butun siteyi
    durduruyordu.
  * 1'i ayrac farkiydi: sayfa Ingilizce kaynagi "15,000 feet" diye
    basiyor, yorum ayni sayiyi "15.000" yaziyordu.
  * 1'inde DEPODAKI metin eskiydi: depo "0,85 / 14.637" diyordu,
    sayfada basilan yorum ise "0,21 / 13.827".

Ortak sebep tek: kapi yorumu DEPODAN, sayilari SAYFADAN okuyordu.
Iki ayri kaynak, tek soru. Dosyanin kendi kurali zaten "olcut
URETILMIS SAYFA" diyordu; kural sayilara uygulanmis, METNE
uygulanmamisti.

DOGRU ILISKI
------------
Eleyici `insa.py`de KARAR VERIR, bu kapi URETILEN SAYFAYI DOGRULAR.
Kapi bir ihlal buluyorsa bu artik "eleyicide delik var" demektir --
ve o zaman dagitimi durdurmak dogrudur.

NEDEN BU SINAMA
---------------
Bu arac gecmiste IKI KEZ vacuous calisti ve iki kez "0 ihlal"
raporladi; ikisi de yanlisti. Simdi "0 ihlal" yine goruluyor --
aradaki farkin gercek olmasi icin, gercek bir ihlalin HALA
yakalandigi burada olculuyor.
"""

from __future__ import annotations

import pathlib
import shutil
import sqlite3
import sys
import tempfile

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))

import yorum_denetimi as yd  # noqa: E402

gecti = 0
kaldi: list[str] = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def _depo() -> sqlite3.Connection:
    k = sqlite3.connect(":memory:")
    k.execute("create table ai_yorum(adres text, metin text)")
    k.execute("create table haber(adres text, yayin_yolu text, "
              "yayimlandi int, baslik_kaynak text, baslik_tr text, "
              "kurum text)")
    # `analiz.baglam` bu tabloyu okuyor; bos olmasi yeterli.
    k.execute("create table gosterge(kod text, tarih text, deger real, "
              "birim text, ad text, kaynak text, kayit_ani text)")
    return k


def _kur(kok: pathlib.Path, k: sqlite3.Connection,
         yol: str, govde: str, yorum: str | None, depo_metni: str) -> None:
    """Bir sayfa uretir ve depoya karsilik gelen yorumu yazar.

    `yorum=None` ise sayfa yorum blogu ICERMIYOR -- yani `insa.py`
    onu elemis demektir.
    """
    k.execute("insert into ai_yorum values(?,?)", (yol, depo_metni))
    k.execute("insert into haber values(?,?,1,?,?,?)",
              (yol, yol, "Baslik", "Baslik", "TCMB"))
    p = kok / yol.strip("/") / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    blok = f'<p class="ai-metin">{yorum}</p>' if yorum is not None else ""
    p.write_text(f"<html><body><p>{govde}</p>{blok}</body></html>",
                 encoding="utf-8")


kok = pathlib.Path(tempfile.mkdtemp())
onceki = yd.CIKTI
yd.CIKTI = kok
try:
    k = _depo()

    # 1) GERCEK IHLAL -- basilan yorumda 7,77 var, sayfada yok.
    #    Kapinin asil isi bu ve KORUNMALI.
    _kur(kok, k, "/haber/a1/", "Sayfada 3,33 yaziyor.",
         "Enflasyon %7,77 seviyesinde.", "Enflasyon %7,77 seviyesinde.")

    # 2) TEMIZ -- sayi sayfada geciyor.
    _kur(kok, k, "/haber/a2/", "Sayfada 3,33 yaziyor.",
         "Enflasyon %3,33 seviyesinde.", "Enflasyon %3,33 seviyesinde.")

    # 3) AYRAC FARKI -- sayfa "15,000 feet", yorum "15.000 fit".
    #    Ayni sayi; ihlal DEGIL.
    _kur(kok, k, "/haber/a3/", "Wells exceed 15,000 feet.",
         "Esik 15.000 fit.", "Esik 15.000 fit.")

    # 4) BASILMAYAN YORUM -- sayfada blok yok. Okura ulasan bir iddia
    #    yok, dolayisiyla denetlenecek bir sey de yok. Bunu ihlal
    #    saymak tam olarak siteyi bir gun donduran hataydi.
    _kur(kok, k, "/haber/a4/", "govde", None, "dayanaksiz 9,99 sayisi")

    # 5) DEPO ESKI, SAYFA YENI -- kapi SAYFAYA bakmali.
    #    Depodaki eski metin sayfada olmayan bir sayi tasiyor; sayfada
    #    basilan yeni metin ise temiz.
    _kur(kok, k, "/haber/a5/", "Endeks 13.827 seviyesinde.",
         "Endeks 13.827 seviyesinde.", "Endeks 14.637 seviyesinde.")

    bulunan = {yol for _adres, yol, _yok in yd.ihlaller(k)}

    es("gercek ihlal YAKALANIYOR", "/haber/a1/" in bulunan, True)
    es("temiz sayfa ihlal degil", "/haber/a2/" in bulunan, False)
    es("ayrac farki ihlal degil", "/haber/a3/" in bulunan, False)
    es("basilmayan yorum denetlenmiyor", "/haber/a4/" in bulunan, False)
    es("eski depo metni sayfayi ezmiyor", "/haber/a5/" in bulunan, False)
    es("baska ihlal uretilmiyor", sorted(bulunan), ["/haber/a1/"])

    # Sayim GERCEKTEN denetleneni soylemeli. Depoda bes yorum var,
    # sayfada dordu basili (a4 elenmis).
    es("denetlenen sayisi basili olanlari sayiyor",
       yd.denetlenen_sayisi(k), 4)

    # Basilan yorum metni sayfadan okunuyor mu -- a5'te depo ile sayfa
    # FARKLI ve okunmasi gereken sayfadaki.
    es("yorum sayfadan okunuyor",
       yd.sayfa_yorumu("/haber/a5/"), "Endeks 13.827 seviyesinde.")
    es("blok yoksa None donuyor", yd.sayfa_yorumu("/haber/a4/"), None)
    es("sayfa yoksa None donuyor", yd.sayfa_yorumu("/haber/yok/"), None)

    # Sayfa metni yorumu DISLAMALI -- yoksa kontrol vacuous olur:
    # yorumdaki her sayi "sayfada" bulunurdu, cunku yorum sayfanin
    # icinde. Bu hata bu dosyada bir kez gercekten yasandi.
    _metin = yd.sayfa_metni("/haber/a1/")
    es("sayfa metni yorum blogunu dislar", "7,77" in (_metin or ""), False)
    es("sayfa metni govdeyi tutar", "3,33" in (_metin or ""), True)

    # KAPI TAMAMEN BOSA DUSERSE FARK EDILMELI: hicbir sayfada yorum
    # basilmamissa denetlenen sayisi sifir olur ve arac bunu
    # soylemek zorunda (main icinde uyari basiliyor).
    k2 = _depo()
    _kur(kok, k2, "/haber/b1/", "govde", None, "9,99")
    es("hic basili yorum yoksa sayim sifir", yd.denetlenen_sayisi(k2), 0)
    es("hic basili yorum yoksa ihlal de yok", yd.ihlaller(k2), [])
finally:
    yd.CIKTI = onceki
    shutil.rmtree(kok, ignore_errors=True)

print()
for x in kaldi:
    print("  KALDI", x)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
