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

#: Ret listesi artik SAYISAL degerden uretiliyor ("28.4"), ham dizgi
#: degil; tam esitlik yerine "yakalandi mi" sinaniyor.
sina("UYDURULAN sayi yakalanir",
     yorumcu.sayi_denetimi(
         "TÜFE %31,75'ten %28,40'a inecek.", GIRDI) == ["28.4"])

sina("binlik ayraci farki sorun degil",
     yorumcu.sayi_denetimi("Politika faizi 40,00%.", GIRDI) == [])

sina("nokta/virgul bicimi ayni sayi sayilir",
     yorumcu.sayi_denetimi("TÜFE 31.75 oldu.", GIRDI) == [])

sina("tek haneli sayi gormezden gelinir",
     yorumcu.sayi_denetimi("Üç kanal öne çıkıyor.", GIRDI) == [])

# --- ilk gercek calistirmada olculen YANLIS REDLER ------------------
#
# Ikisi de modelin dogru davrandigi haldi; denetim metin olarak
# karsilastirdigi icin reddediyordu.

sina("40 ile 40,00 ayni sayi",
     yorumcu.sayi_denetimi("Politika faizi %40.", GIRDI) == [])

sina("isaret kelimeye tasinabilir (-35 -> 35)",
     yorumcu.sayi_denetimi("35 baz puan geriledi.", GIRDI) == [])

sina("binlik ayracli negatif -- mutlak deger",
     yorumcu.sayi_denetimi(
         "Denge 3.018 açık verdi.",
         "Önceki dönem −3.018,00 mn $.") == [])

sina("yuvarlama serbest (31,75 -> 31,8)",
     yorumcu.sayi_denetimi("TÜFE %31,8 seviyesinde.", GIRDI) == [])

sina("gercekten uydurulan sayi HALA yakalanir",
     yorumcu.sayi_denetimi("TÜFE %28,40'a inecek.", GIRDI) != [])

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

# --- suren egilim (ilk gercek calistirmada olculen hata) -------------
#
# "ABD'de isten cikarmalar ARTIYOR. ... Onceki donem 45,85; geriledi."
# Butun sayilar girdide geciyordu; sayi denetimi yakalamadi.
for ad, metin, beklenen in [
    ("artiyor yakalanir", "ABD'de işten çıkarmalar artıyor.", True),
    ("yukseliyor yakalanir", "Enflasyon yükseliyor.", True),
    ("dusuyor yakalanir", "Talep düşüyor.", True),
    ("gecmis zaman SERBEST", "Enflasyon geriledi.", False),
    ("yukseldi SERBEST", "Çekirdek yükseldi.", False),
]:
    sina(f"egilim: {ad}",
         bool(yorumcu.SUREN_EGILIM.search(metin)) is beklenen)

# --- cumle sayimi ---------------------------------------------------

sina("uc cumle gecerli",
     yorumcu._cumle_sayisi("Bir. İki. Üç.") == 3)

sina("ondalik nokta cumle sonu SAYILMAZ",
     yorumcu._cumle_sayisi("TÜFE 31.75 seviyesinde ölçüldü.") == 1)

sina("uzun metin esigi asar",
     yorumcu._cumle_sayisi("A. B. C. D. E.") > yorumcu.EN_COK_CUMLE)

# --- istek bicimi (gpt-oss farkli bicim istiyor) ---------------------

sina("gpt-oss responses bicimi",
     "input" in yorumcu._istek_govdesi("@cf/openai/gpt-oss-120b", "x"))

sina("llama sohbet bicimi",
     "messages" in yorumcu._istek_govdesi("@cf/meta/llama-3.1-8b-instruct", "x"))

sina("sohbet yaniti cozulur",
     yorumcu._yaniti_coz({"result": {"response": "merhaba"}}) == "merhaba")

# --- yazim duzeltmesi (yonergenin yetmedigi yerler) ------------------

for ad, girdi_m, beklenen in [
    ("Hormuz -> Hürmüz", "Hormuz Boğazı'nda gerilim.", "Hürmüz Boğazı'nda gerilim."),
    ("Hormoz -> Hürmüz", "Hormoz Boğazı kapandı.", "Hürmüz Boğazı kapandı."),
    ("Euro Bölgesi -> Avro", "Euro Bölgesi verisi.", "Avro Bölgesi verisi."),
    ("kirilmaz tire", "2025‑de arttı.", "2025'de arttı."),
    ("egri kesme", "Çin’in ithalatı.", "Çin'in ithalatı."),
    ("FED -> Fed", "FED kararı.", "Fed kararı."),
]:
    sina(f"yazim: {ad}", yorumcu.yazimi_duzelt(girdi_m) == beklenen)

sina("yazim duzeltmesi SAYIYA dokunmuyor",
     yorumcu.yazimi_duzelt("TÜFE %31,75 ve 1.929,00 mn $.")
     == "TÜFE %31,75 ve 1.929,00 mn $.")

sina("responses yaniti cozulur, akil yurutme ATLANIR",
     yorumcu._yaniti_coz({"result": {"output": [
         {"type": "reasoning", "content": [{"text": "dusunuyorum"}]},
         {"type": "message", "content": [{"text": "sonuc"}]},
     ]}}) == "sonuc")

print("=" * 60)
if kaldi:
    print(f"{kaldi} TEST BASARISIZ")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({gecti})")
