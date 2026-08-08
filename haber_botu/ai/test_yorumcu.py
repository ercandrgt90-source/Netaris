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

# --------------------------------------------------------------------
# HABERI TEKRAR ETME
#
# "AI'in haberi farkli cumlelerle tekrar etmesi analiz olarak kabul
# edilmez." Olculdu: 44 yorumun ortalama ortusmesi %28, ama dordu
# %60'in uzerinde ve en kotusu %80 -- model haberi baska kelimelerle
# yeniden yazmis.
# --------------------------------------------------------------------
# ESIK NEREDEN: mevcut 45 yorumda bu yonle olculen ortusme ortalama
# %14, medyan %12, en yuksek %60 -- ve o %60'lik yorum MESRU (haberi
# aktardiktan sonra mekanizma ekliyor). Gercek tekrar ornegi ise %83.
# Esik 0,65 ikisinin arasinda.
_G = ("Haber: Citigroup, 2026'nın üçüncü çeyreğine ilişkin ortalama Brent "
      "petrol fiyatı tahminini 65 dolardan 70 dolara yükseltti. "
      "Veri: Brent 88,90 dolar; önceki kapanış 96,95 dolar.")

_tekrar = ("Citigroup, 2026'nın üçüncü çeyreği için ortalama Brent petrol "
           "fiyatı tahminini 65 dolardan 70 dolara yükseltti.")
sina("haberi tekrar eden yorum esigi asiyor",
     yorumcu.tekrar_orani(_tekrar, _G) >= yorumcu.TEKRAR_ESIGI)

_analiz = ("Brent 88,90 dolara gerilerken tahmin yukarı çekildi; bu ayrışma, "
           "arz riskinin fiyatlanmadığı bir dönemde talep beklentisinin "
           "güçlendiğine işaret eder. Türkiye net enerji ithalatçısı olduğu "
           "için bu kalem cari dengeye ve maliyet enflasyonuna yazılır.")
sina("gercek analiz esigin ALTINDA",
     yorumcu.tekrar_orani(_analiz, _G) < yorumcu.TEKRAR_ESIGI)

# Sayilar hesaba GIRMIYOR: modelin sayilari girdiden almasi ZORUNLU
# (sayi_denetimi bunu sart kosuyor). Onlari tekrar saymak, dogru
# davranisi cezalandirmak olurdu.
_sayili = "88,90 96,95 65 70 2026"
sina("yalnizca sayidan olusan metin ortusme uretmez",
     yorumcu.tekrar_orani(_sayili, _G) == 0.0)

sina("bos cikti sifir", yorumcu.tekrar_orani("", _G) == 0.0)
sina("alakasiz metin dusuk ortusme",
     yorumcu.tekrar_orani("Deprem bolgesinde konut teslimleri surdu.", _G) < 0.3)


# --------------------------------------------------------------------
# OLCUM VAR MI -- hangi yonergenin kullanilacagini bu belirliyor.
#
# Olculdu: 28 reddin 19'u "sayisal bir olcum bulunmadigi icin
# yorumlamak mumkun degildir" idi. Model haklıydı; yanlis olan ona
# sorulan soruydu.
# --------------------------------------------------------------------
_OLCULU = """Haber: TÜFE açıklandı
Konu: Enflasyon
Bulgu: TÜFE %31,75; önceki dönem %32,11"""
_OLCUMSUZ = """Haber: Gözler açıklanacak tarım dışı istihdam verisinde
Konu: İstihdam ve ücret
Kaynak: Anadolu Ajansı
Etkilenen sektörler (sırayla): Gelişen ülke varlıkları
İzlenecekler: ABD 10 yıllık, Dolar endeksi"""

sina("olculu girdi taniniyor", yorumcu.olcum_var(_OLCULU))
sina("olcumsuz girdi taniniyor", not yorumcu.olcum_var(_OLCUMSUZ))

# BASLIKTAKI YIL OLCUM SAYILMAMALI -- yoksa her haber olculmus gorunur
# ve olcumsuz yonerge hic devreye girmez.
sina("basliktaki yil olcum degil",
     not yorumcu.olcum_var("Haber: ABD 2026'da ticaret acigini artirdi\n"
                           "Konu: Dış ticaret"))
# "Veri:" satirinda ondalik sayi varsa olcum sayilir.
sina("ondalik veri olcum sayilir",
     yorumcu.olcum_var("Haber: x\nVeri: Açıklanan değer 33,43"))

# Iki yonerge de yasak kaliplari tasimali.
for _y in ("uydurma", "tavsiye", "TÜRKÇE"):
    sina(f"olcumsuz yonergede {_y!r} kurali var",
         _y.lower() in yorumcu.SISTEM_OLCUMSUZ.lower())
# Olcumsuz yonerge OLCUM ISTEMEMELI.
sina("olcumsuz yonerge olcum istemiyor",
     "en önemli tek ölçümü seç" not in yorumcu.SISTEM_OLCUMSUZ.lower())


print("=" * 60)
if kaldi:
    print(f"{kaldi} TEST BASARISIZ")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({gecti})")
