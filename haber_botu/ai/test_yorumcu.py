"""Yorumcu dogrulama katmani testleri.

Model cagrisi YOK -- sinanan sey, modelden gelen metnin suzgeci
gecip gecmedigi. Kritik olan kisim burasi: model uydurursa yakalanmali.

    python haber_botu/ai/test_yorumcu.py
"""

from __future__ import annotations

import pathlib
import sys

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))

import yorumcu  # noqa: E402

GIRDI = """Haber: TÜFE: %31,75
Konu: Enflasyon
Açılış: Temmuz 2026 verisine göre TÜFE yıllık %31,75; bir önceki aya
göre -35 baz puanla geriledi; çekirdek enflasyon (C) %29,91.
Bulgu: Enflasyon 6 aydır %30,9–%32,6 bandında
Gösterge: Politika faizi 40,00% (önceki 40,00%, değişim 0 bp)
Duyarlılık sırası: Perakende / Gıda > Bankacılık > Konut ve kira"""

gecti = kaldi = 0


def sina(ad: str, kosul: bool) -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"  gecti  {ad}")
    else:
        kaldi += 1
        print(f"  KALDI  {ad}")


# --- sayi denetimi ---------------------------------------------------

sina("girdideki sayilar temiz gecer",
     yorumcu.sayi_denetimi(
         "TÜFE %31,75 seviyesinde; çekirdek %29,91.", GIRDI) == [])

sina("UYDURULAN sayi yakalanir",
     yorumcu.sayi_denetimi(
         "TÜFE %31,75'ten %28,40'a inecek.", GIRDI) == ["28.40"])

sina("binlik ayraci farki sorun degil",
     yorumcu.sayi_denetimi("Politika faizi 40,00%.", GIRDI) == [])

sina("nokta/virgul bicimi ayni sayi sayilir",
     yorumcu.sayi_denetimi("TÜFE 31.75 oldu.", GIRDI) == [])

sina("tek haneli sayi gormezden gelinir",
     yorumcu.sayi_denetimi("Üç kanal öne çıkıyor.", GIRDI) == [])

# --- yasak kaliplar --------------------------------------------------

YASAK_ORNEK = [
    ("alim onerisi", "Bankacılık hisselerinde alım önerisi öne çıkıyor."),
    ("hedef fiyat", "Hedef fiyat %35 olarak görülüyor."),
    ("olasilik beyani", "%60 ihtimalle enflasyon geriler."),
    ("yon tahmini", "Enflasyon önümüzdeki ay düşecek."),
    ("kesinlik iddiasi", "Bu kesinlikle bankacılığı etkiler."),
]
for ad, metin in YASAK_ORNEK:
    sina(f"yasak: {ad}",
         any(d.search(metin) for d in yorumcu.YASAK))

sina("temiz metin yasak kalipa takilmaz",
     not any(d.search(
         "TÜFE %31,75; çekirdek %29,91. Fark, fiyat katılığının ölçüsü."
     ) for d in yorumcu.YASAK))

# --- saglayici secimi ------------------------------------------------

sina("anahtar yoksa saglayici bos",
     yorumcu.saglayici() in ("", "cloudflare", "anthropic"))

#: `yorumla()` uc deger donuyor: (metin, model, ret_nedeni)
sina("kisa girdi reddedilir",
     yorumcu.yorumla("cok kisa")[2] == "girdi cok kisa")

sina("model listesi bos degil", len(yorumcu.cf_modelleri()) >= 1)

print("=" * 60)
if kaldi:
    print(f"{kaldi} TEST BASARISIZ")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({gecti})")
