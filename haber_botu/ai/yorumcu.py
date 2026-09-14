"""Haber yorumcusu -- olculmus veriyi okunur cikarima cevirir.

    haber + olculmus veri  ->  saglayici  ->  dogrulama  ->  depo  ->  sayfa

TEMEL KURAL
-----------
MODEL RAKAM BULMAZ, VERILEN RAKAMI CUMLEYE CEVIRIR.

Sayfadaki butun olcumler (TUFE, cekirdek, politika faizi, beklenti,
duyarlilik siralamasi) `analiz/dosya.py` icinde deterministik olarak
hesaplaniyor. Modelin isi o olcumleri baglama oturtmak. Bu ayrim iki
isi birden goruyor: maliyeti dusuruyor ve UYDURMAYI KAPATIYOR --
modelin arayacagi bir sey yok.

NEDEN BUILD ZAMANINDA
---------------------
Ilk surum tarayicidan cagriliyordu ve olculdu: arama motoru o metni
HIC gormuyordu. Sitenin asil degeri olacak yorum, sayfanin HTML'ine
gomulu olmali. Ayrica build zamaninda uretilen metin DEPOYA yaziliyor;
ayni haber her kurulumda yeniden yorumlanmiyor, yani metin sabit
kaliyor ve okur sayfayi yenileyince degismiyor.

UC KATLI DOGRULAMA
------------------
1. SAYI DENETIMI  -- ciktidaki her sayi girdide de gecmeli.
2. GUVENLIK TARAMASI -- `ai/guvenlik.py`, uye yazilarinda kullanilan
   ayni suzgec: yatirim tavsiyesi, hedef fiyat, kesinlik iddiasi.
3. YASAK KALIP -- yon ve olasilik beyani.

Herhangi biri duserse metin TAMAMEN atilir. Duzeltmeye calismak yerine
susmak dogru: yorumsuz sayfa, yanlis yorumlu sayfadan iyidir.

SAGLAYICILAR
------------
"cloudflare" -- Workers AI. Ucretsiz gunluk kotasi var, site zaten
                Cloudflare'de. CLOUDFLARE_API_TOKEN ve
                CLOUDFLARE_ACCOUNT_ID yeterli (ikisi de mevcut).
"anthropic"  -- ANTHROPIC_API_KEY varsa. Daha iyi metin uretiyor.

Anahtar yoksa modul kendini atlar ve hat kirmizi DONMEZ.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

import httpx

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_BURASI), str(_BURASI.parent / "analiz")]

import guvenlik  # noqa: E402

#: Workers AI modelleri, SIRAYLA denenir.
#:
#: Ilki daha guclu ve Turkce'de belirgin sekilde daha iyi; ucretsiz
#: kotayi daha hizli tuketiyor. Kota dolar ya da model gecici olarak
#: erisilemez olursa ikinciye dusuluyor -- yorum uretmemektense daha
#: zayif bir modelle uretmek yeglenir, cunku cikti zaten uc katli
#: dogrulamadan geciyor.
#:
#: `NETARIS_AI_MODEL` ortam degiskeni verilirse YALNIZCA o kullanilir;
#: model degistirmek icin kod duzenlemek gerekmiyor.
CF_MODELLER = (
    "@cf/openai/gpt-oss-120b",
    "@cf/meta/llama-3.1-8b-instruct",
)
ANTHROPIC_MODEL = "claude-opus-5"

#: Anthropic'e ait model adlari. Bunun DISINDAKI her sey Cloudflare:
#: `NETARIS_AI_MODEL` yalnizca ucretsiz saglayicinin model listesini
#: degistiriyor (`_cf_modeller`), Anthropic'inkini degil.
ANTHROPIC_MODELLER = (ANTHROPIC_MODEL,)


def cf_modelleri() -> tuple[str, ...]:
    ozel = os.environ.get("NETARIS_AI_MODEL", "").strip()
    return (ozel,) if ozel else CF_MODELLER

ZAMAN_ASIMI = 60.0
# Jeton tavani. 420 iken model uc cumlelik yonergeyi tamamlayamadan
# tavana carpiyor ve cumleyi ortasinda birakiyordu; olculdu, yayimdaki
# yorumlarin bir kismi yarim cumleyle bitiyordu.
#
# Asil sinir CUMLE SAYISI (`EN_COK_CUMLE`) ve o zaten kontrol ediliyor.
# Jeton tavani bir icerik olcutu degil, maliyet korkulugu -- ve modelin
# cumlesini bitirmesine yetecek kadar genis olmali.
EN_COK_JETON = 700

SISTEM = """Sen bir finans veri editörüsün. Sana bir haberin ÖLÇÜLMÜŞ
verileri veriliyor. Görevin bu verileri okunur bir çıkarıma çevirmek.

GÖREV: Verileri TEKRARLAMA. Okur onları zaten yukarıda gördü. Sen
şunu yap: en önemli tek ölçümü seç, ne anlama geldiğini söyle ve
hangi mekanizmayla neyi etkilediğini yaz.

BAŞLIKLA ÇELİŞME. Yorumun, haberin başlığındaki bulguyla aynı şeyi
anlatmalı. Verilerde başlığa ait olmayan başka bir büyüklük varsa onu
ana konu yapma — başlık "X arttı" diyorsa, "Y azaldı" ile başlayan bir
çıkarım okuru yanıltır.

KURALLAR — hepsi zorunlu:
- YALNIZCA sana verilen sayıları kullan. Yeni sayı, oran, tarih ya da
  kurum adı EKLEME.
- Sayıyı VERİLDİĞİ ANLAMDA kullan. Bir fark ("0,90 puan geriledi")
  seviye değildir; seviye ("%1,60") fark değildir. Karıştırma.
- Süren eğilim iddiası YASAK. "Artıyor", "yükseliyor", "düşüyor"
  yazma — elinde iki gözlem var, bu bir seri iddiası olur. Geçmiş
  zaman serbest: "geriledi", "yükseldi".
- Tahmin, öngörü, yatırım tavsiyesi YASAK. "Yükselecek", "alım
  fırsatı", "hedef fiyat" gibi ifadeler yasak.
- Olasılık belirtme. "%60 ihtimalle" gibi ifadeler yasak.
- Sana verilen bağlam metnini KOPYALAMA. Kendi cümleni kur.
- Veri hangi ülkeye aitse o ülkenin bağlamında yaz. ABD verisine
  Türkiye'ye özgü açıklama (asgari ücret, TÜFE sepeti) ekleme.
- BİRİM UYDURMA. Sayının birimi verilmemişse birimsiz yaz. "Puan"
  yalnızca oran farkları içindir; adet, kişi ya da endeks farkına
  "puan" deme.
- Yer ve kurum adlarını TÜRKÇE yaz: Hürmüz Boğazı (Hormuz değil),
  Kızıldeniz, Süveyş, Avro Bölgesi, Çin, Rusya.
- EN FAZLA 3 CÜMLE. Madde işareti yok, tek paragraf.
- Türkçe yaz. Yüzde işareti sayıdan ÖNCE gelir: %31,75 (31,75% DEĞİL).
  Ondalık ayracı virgüldür. Yıl ekini kesme işaretiyle yaz: 2025'te."""

#: OLCUMSUZ HABER ICIN AYRI YONERGE.
#:
#: Olculdu: 28 reddin 19'u tek bir sebeptendi -- model "sayisal bir
#: olcum bulunmadigi icin yorumlamak mumkun degildir" diyordu.
#:
#: MODEL HAKLIYDI. Yukaridaki yonerge "en onemli tek OLCUMU sec"
#: diyor; bekleyis haberinde ("gozler aciklanacak tarim disi istihdam
#: verisinde") olcum yok. Yanlis olan modelin cevabi degil, ona
#: sorulan soruydu.
#:
#: Bu yonerge ayni haberden BASKA bir sey istiyor: mekanizma. Elimizde
#: olcum yok ama konu, sektor listesi ve izlenecekler var -- bunlar
#: "bu neden onemli" sorusunu cevaplamaya yeter.
#:
#: SAYI DENETIMI YINE GECERLI: model sayi uyduramaz. Girdide sayi
#: yoksa cikti da sayisiz olur ve bu DOGRU olan.
SISTEM_OLCUMSUZ = """Sen bir finans editörüsün. Sana bir haber ve onun
bağlamı veriliyor. Bu haberde SAYISAL ÖLÇÜM YOK — olmaması normal.

GÖREV: Ölçüm arama. Bunun yerine MEKANİZMAYI anlat: bu gelişme hangi
kanaldan neyi etkiler, kim etkilenir, bundan sonra hangi veri izlenir.

Yapı şu olsun:
  gelişme → hangi kanaldan → kimi etkiler → ne izlenir

KURALLAR — hepsi zorunlu:
- SAYI UYDURMA. Girdide sayı yoksa yorumunda da sayı olmasın. Bu bir
  eksiklik değil; ölçüm yokken sayı yazmak uydurmak olur.
- "Ölçüm bulunmadığı için yorum yapılamaz" GİBİ CÜMLELER YASAK. Ölçüm
  olmadan da söylenecek şey var: mekanizma.
- Tahmin, öngörü, yatırım tavsiyesi YASAK.
- Olasılık belirtme.
- Süren eğilim iddiası YASAK ("artıyor", "yükseliyor").
- Fiyat yönü İDDİA ETME. "Altın düşer", "dolar güçlenir" yazma —
  mekanizma anlat, yön söyleme.
- Haberi TEKRAR ETME. Okur başlığı zaten okudu; sen neden önemli
  olduğunu yaz.
- Yer ve kurum adlarını TÜRKÇE yaz: Hürmüz Boğazı, Avro Bölgesi, Fed.
- EN FAZLA 3 CÜMLE. Madde işareti yok, tek paragraf.
- Türkçe yaz."""


def olcum_var(girdi: str) -> bool:
    """Girdide modelin okuyabilecegi bir sayi var mi.

    "Bulgu", "Gosterge" ve "Acilis" satirlari olcum tasiyor; "Haber" ve
    "Konu" satirlari tasimiyor. Basliktaki bir yil ("2026") olcum
    sayilmamali -- yoksa her haber olculmus gorunur.
    """
    for satir in girdi.splitlines():
        if satir.startswith(("Bulgu:", "Gösterge:", "Açılış:")):
            if re.search(r"\d", satir):
                return True
        if satir.startswith("Veri:") and re.search(r"\d+[.,]\d", satir):
            return True
    return False

#: Ciktida bulunmasi metni GECERSIZ kilan kaliplar.
#: Cop cikti eleyicisi AYRI MODULDE: bicim denetimi (yorum mu degil
#: mi) ile icerik denetimi (yorum dogru mu) ayri sorular.
from cop_cikti import sebep as COP_CIKTI  # noqa: E402


YASAK = (
    re.compile(r"\b(alım|satım|tut)\s*(öneri|tavsiye|sinyal)", re.I),
    re.compile(r"hedef fiyat", re.I),
    re.compile(r"%\s*\d+\s*(ihtimal|olasılık)", re.I),
    re.compile(r"\b(yükselecek|düşecek|artacak|azalacak|gerileyecek)\b", re.I),
    re.compile(r"\byatırım (tavsiyesi|önerisi)\b", re.I),
    re.compile(r"\b(kesinlikle|mutlaka|garanti)\b", re.I),

    # NOT: "politika faizi + deger" kalibi buradan KALDIRILDI ve yerine
    # `_politika_faizi_kusuru()` kondu. Sebebi asagida, o islevin
    # basinda yazili -- ozeti: yasak, kendi sebebini cozdukten sonra
    # dogru analizleri elemeye devam etti.

    # HAM ONDALIK. Ucten fazla basamak, hicbir finansal buyuklukte
    # anlamli degil ve okura "hesap makinesinden kopyalanmis" izlenimi
    # verir.
    #
    # Olculdu, ANA SAYFADA YAYIMLANDI: "Enflasyon %31,75409679
    # seviyesine gerileyerek onceki %32,10903603'ten...". Sayfanin
    # kendisi ayni degeri %31,8 diye basiyordu -- yani metin, sayfada
    # OLMAYAN bir hassasiyet uretmisti.
    #
    # Kok sebep girdideydi: gosterge satirlari ham `float` gonderiyordu
    # ve model gordugunu kopyaladi. Girdi bicimlendirildi; bu kural
    # ikinci savunma hatti, cunku girdi bir gun yine kayabilir.
    re.compile(r"\d+[.,]\d{4,}"),
)

#: SUREN EGILIM IDDIASI -- "artiyor", "yukseliyor", "dusuyor".
#:
#: Ilk gercek calistirmada olculdu:
#:
#:   Girdi : "Aciklanan deger 33,43. Onceki donem 45,85; geriledi."
#:   Cikti : "ABD'de isten cikarmalar ARTIYOR. Aciklanan deger 33,43.
#:            Onceki donem 45,85; geriledi (12,42)."
#:
#: Metin kendi icinde CELISIYOR: once "artiyor" diyor, iki cumle sonra
#: "geriledi". Butun sayilar girdide gectigi icin sayi denetimi bunu
#: yakalamadi -- uydurma sayi yok, YANLIS CUMLE var.
#:
#: Simdiki zaman kipiyle kurulan egilim iddiasi zaten yasak: elimizde
#: iki gozlem var, "artiyor" demek bir SERI iddiasi ve olcumu asiyor.
#: Gecmis zaman ("geriledi", "yukseldi") olcumun kendisidir, serbest.
SUREN_EGILIM = re.compile(
    r"\b(artıyor|azalıyor|yükseliyor|düşüyor|geriliyor|"
    r"artmakta|azalmakta|yükselmekte|düşmekte)\b", re.I)

#: CEVAPSIZ CIKTI -- modelin "yorum yapamam" dedigi metinler.
#:
#: Olculdu, sayfada aynen su duruyordu:
#:
#:     "Verilen metinde sayisal bir olcum bulunmadigi icin, olculen bir
#:      degeri secip yorumlamak mumkun degildir."
#:
#: MODEL HAKLI: bekleyis haberinde gercekten olcum yok. Yanlis olan,
#: ona olcum sormakti. Ama bu metin bir YORUM DEGIL, bir tutanak --
#: sayfada "Netaris yorumu" basligi altinda durmasi, okura soyleyecek
#: sozumuz oldugunu iddia edip hicbir sey soylememek oluyor.
#:
#: Bu tur cikti artik REDDEDILIYOR, yani depoya hic girmiyor ve bolum
#: BASILMIYOR. Ayni haberde gosterge brifingi zaten devreye giriyor;
#: bos bir "ilk bakis" kutusu onun yanina hicbir sey katmiyordu.
CEVAPSIZ = re.compile(
    r"(mümkün değildir|mümkün olmamaktadır|yorum yapılamaz|"
    r"yapmak mümkün değil|rapor edilememektedir|"
    r"bulunmadığı için|bulunmamaktadır|"
    r"yeterli (veri|bilgi) (yok|bulunmamakta)|"
    r"sayısal bir (ölçüm|değer)(?![^.]*\bolarak\b))", re.I)

#: Sayi denetiminde yok sayilan kisa sayilar. "3 cumle", "1 puan" gibi
#: ifadeler girdide gecmiyor ama uydurma da degil.
_KISA_SAYI = 2

#: En fazla cumle. Yonergede de yazili ama zayif model duzenli olarak
#: asiyor ve girdiyi tekrarlayan paragraflar uretiyor. Dort cumleye
#: musaade var: uc cumle hedef, biri pay.
EN_COK_CUMLE = 4

#: Cumle sonu. Ondalik ayraci noktayla yazilan sayilar ("31.75") cumle
#: sonu sanilmasin diye noktadan sonra BOSLUK ya da metin sonu araniyor.
_CUMLE_SONU = re.compile(r"[.!?](?:\s|$)")


def _cumle_sayisi(metin: str) -> int:
    return len([x for x in _CUMLE_SONU.split(metin) if x.strip()])


#: Yazim duzeltmeleri -- YONERGE YETMEDIGI ICIN var.
#:
#: Modele "Turkce yaz" demek ozel adlarda ise yaramiyor: egitim
#: verisinde "Hormuz" bicimi baskin ve model onu uretiyor. Olculdu:
#: "Hormoz Bogazi'ndaki arz kesintileri". Bunlar YAZIM duzeltmesi,
#: anlam degistirmiyor; sayilara DOKUNULMUYOR.
#:
#: Kural: yalnizca tartismasiz karsiligi olan ozel adlar. Bir sozcugun
#: dogru yazimi tartismaliysa buraya girmez -- metni sessizce
#: degistirmek, yanlis birakmaktan kotudur.
YAZIM = (
    (re.compile(r"\bHorm[ou]z\b", re.I), "Hürmüz"),
    (re.compile(r"\bSuez\b", re.I), "Süveyş"),
    (re.compile(r"\bRed Sea\b", re.I), "Kızıldeniz"),
    (re.compile(r"\bEurozone\b", re.I), "Avro Bölgesi"),
    (re.compile(r"\bEuro Bölgesi\b"), "Avro Bölgesi"),
    (re.compile(r"\bFED\b"), "Fed"),
    # Turkce olmayan tire ve kesme isaretleri. Model bazen U+2011
    # (kirilmaz tire) ve U+2019 uretiyor; ikisi de metinde yabanci
    # duruyor ve arama/kopyalamada sorun cikariyor.
    (re.compile("‑"), "-"),
    (re.compile("’"), "'"),
)


def yazimi_duzelt(metin: str) -> str:
    for desen, dogru in YAZIM:
        metin = desen.sub(dogru, metin)
    # "2025-de" / "2025-te" -> "2025'te". Model yil ekini bazen tireyle
    # yaziyor; kesme isareti dogrusu.
    metin = re.sub(r"\b(\d{4})[-‑]([dt]e|[dt]a)\b", r"\1'\2", metin)
    return metin


def _sayilar(metin: str) -> set[float]:
    """Metindeki sayilari SAYISAL DEGERE cevirir.

    METIN OLARAK KARSILASTIRMA YANLIS SONUC VERIYORDU -- olculdu:

        girdi "40,00"  -> "40.00"
        cikti "40"     -> "40"      -> "girdide olmayan sayi" (YANLIS)
        girdi "-3.018,00" -> "-3018.00"
        cikti "3.018"     -> "3018"    -> yine yanlis red

    Iki kayit da modelin dogru davrandigi hallerdi. Sayi olarak
    karsilastirinca 40 ile 40,00 ayni, 3018 ile -3018 ise MUTLAK
    degerde ayni: isaret cogu zaman kelimeye tasiniyor ("3.018 acik",
    "35 baz puan geriledi").
    """
    cikti: set[float] = set()
    for s in re.findall(r"-?\d[\d.,]*", metin):
        t = re.sub(r"[.,](?=\d{3}\b)", "", s)      # binlik ayraci
        t = t.replace(",", ".").rstrip(".")
        try:
            cikti.add(abs(float(t)))
        except ValueError:
            continue
    return cikti


#: Karsilastirma toleransi. Model "%31,75"i "%31,8" diye yuvarlayabilir;
#: bu uydurma degil, yuvarlamadir. Binde bir goreli fark serbest.
_TOLERANS = 0.001


#: TEKRAR ESIGI -- yorumun ne kadari zaten girdide geciyor.
#:
#: Olculdu: 44 yorumun ortalama ortusmesi %28, ama dordu %60'in
#: uzerinde ve en kotusu %80 -- yani model haberi baska kelimelerle
#: yeniden yazmis. Ornek:
#:
#:   ozet : "Citigroup (Citi), 2026'nin ucuncu ceyregine iliskin
#:           ortalama Brent petrol fiyati tahminini..."
#:   yorum: "Citigroup, 2026'nin ucuncu ceyregi icin ortalama Brent
#:           petrol fiyati tahminini..."
#:
#: Bu bir analiz degil, bir aynadir. AI'in isi "ne oldu"yu tekrar etmek
#: degil, "bu neden onemli"yi anlatmak.
#:
#: Esik 0,65: olculen dagilimda normal yorumlar %28 civarinda, sorunlu
#: olanlar %80. Aradaki bosluk genis ve esik ortasina konuldu.
TEKRAR_ESIGI = 0.65

#: Sayilar ve kisa kelimeler ortusme hesabina GIRMIYOR. Modelin
#: sayilari girdiden almasi ZORUNLU (sayi_denetimi bunu sart kosuyor);
#: onlari tekrar saymak, dogru davranisi cezalandirmak olurdu.
_ORTUSME_KELIME = re.compile(r"[a-zçğıöşü]{4,}", re.I)


def tekrar_orani(cikti: str, girdi: str) -> float:
    """Yorumun ne kadari girdide zaten geciyor. 0..1

    YON ONEMLI: ciktinin ne kadari girdide var diye bakiliyor, tersi
    degil. Girdi uzun (bulgular, panel, ozet) ve kisa bir yorumun
    girdiyi "kapsamasi" beklenmez; asil soru, yorumun KENDI katkisi
    olup olmadigi.
    """
    kc = {k.lower() for k in _ORTUSME_KELIME.findall(cikti)}
    kg = {k.lower() for k in _ORTUSME_KELIME.findall(girdi)}
    if not kc:
        return 0.0
    return len(kc & kg) / len(kc)


#: "politika faizi ... %N" -- kavram adi ile ona ILISTIRILEN deger.
_PF_CIKTI = re.compile(r"politika faiz\w*[^.]{0,20}?%\s*([\d.,]+)", re.I)


def _politika_faizi_kusuru(cikti: str, girdi: str) -> str:
    """Politika faizine YANLIS bir deger iliStirilmis mi. Temizse "".

    NEDEN DEGER DENETIMI, NEDEN YASAK DEGIL
    ---------------------------------------
    Once kural soyleydi: "politika faizi" adina bir deger iliStirmek
    YASAK. Sebebi gercekti -- model "Politika faizi %40,00 seviyesinde"
    yazmisti ve o sayi TP.APIFON4'ten, yani agirlikli ortalama FONLAMA
    MALIYETINDEN geliyordu. Politika faizi (bir hafta vadeli repo) ayri
    bir buyukluk ve o gun %37 idi.

    O sebep SONRADAN COZULDU: hat artik politika faizini PPK basin
    duyurusundan okuyor ve depoda ayri bir seri olarak tutuyor
    (`TCMB_POLITIKA`). Girdi dogru degeri tasiyor.

    Ama yasak kaldi ve OLCULDU (2026-09-14): 659 ret bu kaliptan
    geliyordu -- TUM retlerin %42'si, ucretsiz saglayicinin retlerinin
    %94,9'u. Reddedilen metinler DOGRUYDU; ustelik bazilari kuralin
    korumak istedigi ayrimi tam olarak yapiyordu:

        "Fonlama maliyetinin %40,00'da sabit kalmasi, TCMB'nin ...
         politika faizi olan %37,00'in uzerinde bir efektif maliyetle
         fiyatlamayi surdurdugu anlamina geliyor"

    Yani kural, kendi sebebini cozdukten sonra tam da tesvik etmesi
    gereken analizleri elemeye devam etti.

    YENI OLCUT: kavramdan soz etmek serbest, DEGER ise girdideki
    politika faizi degerine uymak zorunda. Fonlama maliyetini politika
    faizi diye yazmak hala yakalaniyor -- korunan sey degismedi,
    yalnizca dogru olana yol acildi.

    GIRDIDE POLITIKA FAIZI YOKSA REDDEDILIYOR: dogrulanamayan bir
    iddiaya izin vermek, denetimi olmayan bir alan birakmak olurdu.
    """
    m = _PF_CIKTI.search(cikti)
    if not m:
        return ""
    yazilan = _sayilar("%" + m.group(1))
    if not yazilan:
        return ""
    # YALNIZCA YUZDE ISARETINE BITISIK SAYILAR.
    #
    # Ilk yazimda satirin TUM sayilari aliniyordu ve izinli kume
    # tarihten kirleniyordu: "Politika faizi %37,00 (2026-09-10)"
    # satiri 2026, 9 ve 10'u da izinli sayiyordu -- yani "politika
    # faizi %10" yazan bir metin GECERDI. Denetimi olmayan bir alan
    # birakmamak icin kondu, kendi icinde bir delik acmasin.
    #
    # Iki bicim de destekleniyor: "%37,00" ve "37,00%".
    izinli: set[float] = set()
    for satir in girdi.splitlines():
        if "politika faiz" not in satir.lower():
            continue
        for once, sonra in re.findall(r"%\s*([\d.,]+)|([\d.,]+)\s*%", satir):
            izinli |= _sayilar(once or sonra)
    if not izinli:
        return f"girdide politika faizi yok, cikti {m.group(1)!r} diyor"
    for y in yazilan:
        if any(abs(y - x) <= max(abs(x), 1.0) * _TOLERANS for x in izinli):
            return ""
        # Yuvarlanmis hali de kabul: %37,00 ~ %37
        if any(abs(y - round(x, 1)) <= 0.05 for x in izinli):
            return ""
    return (f"cikti {m.group(1)!r} diyor, girdideki politika faizi "
            f"{sorted(izinli)}")


def sayi_denetimi(cikti: str, girdi: str) -> list[str]:
    """Ciktida olup girdide olmayan sayilari dondurur.

    Bos liste = temiz. Bu, uydurmaya karsi en somut savunma: model
    rakam uretemiyorsa uydurma yapamaz.
    """
    g = _sayilar(girdi)
    kacak = []
    for s in _sayilar(cikti):
        if s < 10:            # tek haneli: "3 cumle", "1 puan"
            continue
        if any(abs(s - x) <= max(abs(x), 1.0) * _TOLERANS for x in g):
            continue
        # Yuvarlanmis hali de kabul: 31,8 ~ 31,75
        if any(abs(round(s, 1) - round(x, 1)) < 1e-9 for x in g):
            continue
        kacak.append(f"{s:g}")
    return kacak


#: Ucretsiz saglayici "kota doldu" dediginde ateslenen bayrak.
#:
#: NEDEN GEREKLI
#: -------------
#: Kosu basina yorum sayisi 12 ile sinirliydi ve gerekcesi "ucretsiz
#: kotayi tek seferde bitirmemek" idi -- yani bir ONLEM, olcum degil.
#:
#: Olculdu (2026-09-14): kosuda 391 aday varken yalnizca 12'si
#: yorumlaniyordu (32 kat kisit) ve Cloudflare'dan BUGUNE KADAR HIC
#: kota ya da oran hatasi alinmamisti. Yani onlem, hic sinanmamis bir
#: tahmine dayaniyordu ve ucretsiz kapasitenin buyuk kismi bosta
#: duruyordu.
#:
#: Sinirin yukseltilebilmesi icin kotaya carpmanin ZARARSIZ olmasi
#: gerekiyor: kota dolunca kalan adaylar icin istek YAPILMIYOR, sebep
#: adiyla yaziliyor ve kosu temiz bitiyor. Boylece gercek tavan
#: tahmin edilmiyor, OLCULUYOR.
_CF_KOTA_DOLDU = False

#: "Yavasla" ya da "kotan bitti" anlamina gelen durum kodlari.
_CF_KOTA_KODU = (429, 402)

#: Durum kodu vermeyen ama kotayi anlatan yanit metinleri.
_CF_KOTA_IZ = ("quota", "neuron", "rate limit", "capacity",
               "too many requests", "usage limit")


def cf_kota_doldu() -> bool:
    """Ucretsiz saglayici bu kosuda kapandi mi."""
    return _CF_KOTA_DOLDU


def _cf_kota_kapat(sebep: str) -> None:
    global _CF_KOTA_DOLDU
    if not _CF_KOTA_DOLDU:
        _CF_KOTA_DOLDU = True
        print(f"    ucretsiz saglayici kotasi doldu ({sebep[:80]}) "
              f"-- kalan adaylar icin istek YAPILMIYOR")


def cf_kotasini_sifirla() -> None:
    """Kosu durumunu basa alir (sinamalar icin)."""
    global _CF_KOTA_DOLDU
    _CF_KOTA_DOLDU = False


def _kota_hatasi(e: Exception) -> bool:
    """Hata "kota doldu" anlamina mi geliyor."""
    if not isinstance(e, httpx.HTTPStatusError):
        return False
    if e.response.status_code in _CF_KOTA_KODU:
        return True
    try:
        metin = (e.response.text or "").lower()
    except Exception:                                 # pragma: no cover
        return False
    return any(iz in metin for iz in _CF_KOTA_IZ)


def _cf_cagir(girdi: str, sistem: str = "") -> tuple[str, str]:
    """Workers AI. `(metin, kullanilan_model)` doner.

    Modeller SIRAYLA deneniyor: biri kota ya da gecici hata verirse
    digerine dusuluyor. Son model de duserse hata yukari firlatiliyor
    ki `yorumla()` sebebi yazabilsin.
    """
    hesap = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    jeton = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not hesap or not jeton:
        return "", ""
    # Kota dolduysa kalan adaylar icin istek atilmiyor: her biri iki
    # model x bir istek demekti ve hicbiri donmeyecekti.
    # ISTISNA FIRLATILMIYOR: `yorumla` yalnizca `httpx.HTTPError`
    # yakaliyor; buradan cikan baska bir istisna kosuyu cokertirdi.
    # Bos donus, cagiranin zaten bildigi yol.
    if _CF_KOTA_DOLDU:
        return "", ""
    son_hata: Exception | None = None
    for model in cf_modelleri():
        try:
            y = httpx.post(
                (f"https://api.cloudflare.com/client/v4/accounts/{hesap}"
                 f"/ai/run/{model}"),
                headers={"Authorization": f"Bearer {jeton}"},
                json=_istek_govdesi(model, girdi, sistem),
                timeout=ZAMAN_ASIMI,
            )
            y.raise_for_status()
            metin = _yaniti_coz(y.json())
            if metin:
                return metin, model
            # Bos yanit hata degil ama kullanilamaz: sonraki modele gec.
            son_hata = son_hata or RuntimeError(f"{model}: bos yanit")
        except httpx.HTTPError as e:
            son_hata = e
            if _kota_hatasi(e):
                # Kota BUTUN modelleri kapsar; ikinciyi denemek bosuna.
                _cf_kota_kapat(f"HTTP {e.response.status_code}")
                break
            continue
    if isinstance(son_hata, httpx.HTTPError):
        raise son_hata
    return "", ""


def _istek_govdesi(model: str, girdi: str, sistem: str = "") -> dict:
    """Modele gore istek bicimi.

    OLCULDU: `@cf/openai/gpt-oss-120b` cagrisi sessizce dusuyor ve hat
    yedek modele (llama-3.1-8b) iniyordu -- ilk gercek calistirmada
    dokuz yorumun dokuzu zayif modelden geldi.

    Sebep bicim farki: gpt-oss ailesi OpenAI'nin "responses" bicimini
    kullaniyor (`instructions` + `input`), digerleri sohbet bicimini
    (`messages`). Ayni govdeyi ikisine birden gondermek calismiyor.
    """
    if "gpt-oss" in model:
        return {
            "instructions": sistem or SISTEM,
            "input": girdi,
            "max_output_tokens": EN_COK_JETON,
            # Sicaklik DUSUK: bu yaratici yazim degil, bicimlendirme isi.
            "temperature": 0.2,
            # Akil yurutme cabasi dusuk: is kisa ve kurallari acik.
            # Yuksek caba hem yavaslatiyor hem kotayi hizli tuketiyor.
            "reasoning": {"effort": "low"},
        }
    return {
        "max_tokens": EN_COK_JETON,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": sistem or SISTEM},
            {"role": "user", "content": girdi},
        ],
    }


def _yaniti_coz(d: dict) -> str:
    """Farkli yanit bicimlerinden metni cikarir.

    Sohbet bicimi     : result.response
    Responses bicimi  : result.output[] -> content[] -> text
                        (ilk ogeler akil yurutme olabilir, ATLANIR)
    """
    sonuc = d.get("result") or {}
    duz = sonuc.get("response")
    if isinstance(duz, str) and duz.strip():
        return duz.strip()

    parcalar: list[str] = []
    for oge in sonuc.get("output") or []:
        if not isinstance(oge, dict):
            continue
        # Akil yurutme adimi CIKTI DEGIL: modelin kendi notlari,
        # okura gosterilecek metin degil.
        if oge.get("type") == "reasoning":
            continue
        for p in oge.get("content") or []:
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                parcalar.append(p["text"])
    return "\n".join(parcalar).strip()


def _anthropic_cagir(girdi: str, sistem: str = "") -> str:
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        return ""
    y = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": anahtar,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": EN_COK_JETON,
            "system": sistem or SISTEM,
            "messages": [{"role": "user", "content": girdi}],
        },
        timeout=ZAMAN_ASIMI,
    )
    y.raise_for_status()
    parcalar = y.json().get("content", [])
    return "".join(p.get("text", "") for p in parcalar).strip()


#: Anthropic bu kosuda kullanilamaz durumda mi.
#:
#: OLCULDU (2026-09-14): hesabin bakiyesi bitti ve her cagri
#:     HTTP 400 -- "Your credit balance is too low to access the
#:     Anthropic API"
#: donmeye basladi. Sonucu tek bir adim degil BUTUN HAT oldu: 12
#: yorumun 12'si reddedildi, "Yorum denetimi" kritik adimi dustu ve
#: kosu kirmizi bitti. Oysa ucretsiz saglayici (Workers AI) calisir
#: durumdaydi ve hicbir zaman denenmedi -- cunku secim yalnizca
#: ANAHTARIN VARLIGINA bakiyordu.
#:
#: Bir faturalandirma sorunu, sitenin tumunu durdurmamali. Bayrak bir
#: kez doldugunda `saglayici()` Anthropic'i atliyor ve kosunun geri
#: kalani ucretsiz saglayiciyla tamamlaniyor.
#:
#: SURECE OZEL, KALICI DEGIL: bir sonraki kosu yeniden Anthropic'i
#: deniyor. Bakiye yuklendiginde kod degisikligi gerekmiyor.
_ANTHROPIC_KAPALI = False

#: Saglayicinin BU KOSUDA kullanilamaz oldugunu gosteren durumlar.
#:
#: 400 TEK BASINA YETMEZ: "istem cok uzun" da 400 doner ve o istege
#: ozeldir, saglayiciya degil. Bu yuzden 400'de yanit metnine
#: bakiliyor; 401/403 (yetki) ve 429 (kota) ise dogrudan sayiliyor.
_KAPATAN_KOD = (401, 403, 429)
_KAPATAN_IZ = ("credit balance", "billing", "quota", "insufficient")


def _anthropic_kapali() -> bool:
    return _ANTHROPIC_KAPALI


def _anthropic_kapat(sebep: str) -> None:
    global _ANTHROPIC_KAPALI
    if not _ANTHROPIC_KAPALI:
        _ANTHROPIC_KAPALI = True
        print(f"    anthropic bu kosuda devre disi ({sebep[:90]})"
              f" -- ucretsiz saglayiciya geciliyor")


def model_saglayicisi(model: str) -> str:
    """Yorumu URETEN saglayici -- model adindan. Bilinmiyorsa bos.

    NEDEN MODELDEN TURETILIYOR
    --------------------------
    `uret_ai_yorum` saglayiciyi DONGUDEN ONCE bir kez soruyordu:

        s = yorumcu.saglayici()          # <- tek sefer
        ...
        INSERT INTO ai_yorum (..., saglayici, model, ...) VALUES (..., s, model, ...)

    Ama `yorumla` kosu ortasinda Anthropic'ten Cloudflare'e GECEBILIYOR
    (bakiye bitince). Model dogru yaziliyordu, saglayici eski degerde
    kaliyordu.

    Olculdu (2026-09-14): 21 satirda `saglayici='anthropic'` yaninda
    `model='@cf/openai/gpt-oss-120b'` yaziyordu -- yani Cloudflare'in
    urettigi yorum Anthropic'e mal edilmisti. Sitede gorunmuyor, ama
    koken kaydi yanlis: saglayici basarimini ya da maliyetini olcmek
    isteyen herkesi yaniltir.

    Iki ayri kaynak ayni soruya cevap veriyordu. Model, cagrinin
    kendisinden donuyor -- tek dogru kaynak o.
    """
    if not model:
        return ""
    return "anthropic" if model in ANTHROPIC_MODELLER else "cloudflare"


def saglayici() -> str:
    """Hangi saglayici kullanilabilir. Hicbiri yoksa bos.

    `NETARIS_AI_SAGLAYICI` ile ZORLANABILIR ("cloudflare" / "anthropic").

    NEDEN ZORLAMA GEREKIYOR. Iki saglayici arasindaki secim normalde
    dogru: Anthropic daha iyi metin uretiyor, o yuzden varsa o
    kullaniliyor. Ama KARSILASTIRMA yapmak icin ucuz olani bilerek
    secebilmek gerekiyor -- gizli degistirgeyi depodan silip geri
    eklemek, olcum yapmak icin fazla riskli bir yol.

    Zorlanan saglayicinin kimlik bilgisi yoksa zorlama YOK SAYILIYOR
    ve normal siraya donuluyor: eksik bir degiskene dayanip sifir
    sayfa uretmektense calisan saglayiciyla uretmek yeglenir.
    """
    zorla = os.environ.get("NETARIS_AI_SAGLAYICI", "").strip().lower()
    _cf = bool(os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
               and os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip())
    # ANAHTAR VAR AMA KULLANILAMIYOR OLABILIR. `_anthropic_kapali`,
    # bu kosuda Anthropic'in bakiye/yetki sebebiyle reddettigini
    # gordugumuz anda doluyor (bkz. `yorumla`). Anahtarin VARLIGI,
    # calistigi anlamina gelmiyor.
    _an = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()) \
        and not _anthropic_kapali()
    if zorla == "cloudflare" and _cf:
        return "cloudflare"
    if zorla == "anthropic" and _an:
        return "anthropic"

    if _an:
        return "anthropic"
    if (os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
            and os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()):
        return "cloudflare"
    return ""


def yorumla(girdi: str, sistem_ozel: str = "") -> tuple[str, str, str, str]:
    """Girdiden yorum uretir.

    `(metin, kullanilan_model, ret_nedeni, ham_cikti)` doner.

    `ham_cikti` reddedilse DE dolu: "neden reddedildi" sorusu ancak
    modelin ne yazdigina bakarak cevaplanabiliyor. Sessiz basarisizlik
    olmuyor -- hem gunluge hem depoya yaziliyor.
    """
    if len(girdi) < 120:
        return "", "", "girdi cok kisa", ""
    s = saglayici()
    if not s:
        return "", "", "saglayici yok (anahtar tanimli degil)", ""
    # KOTA DOLDUYSA ISTEK YAPILMIYOR, SEBEP ADIYLA YAZILIYOR.
    #
    # "bos yanit" demek sebebi gizlerdi; kota dolmasi ile modelin bos
    # donmesi ayri seyler ve ayri cozumleri var.
    if s == "cloudflare" and cf_kota_doldu():
        return "", "", "ucretsiz saglayici kotasi doldu", ""

    # OLCUM YOKSA BASKA BIR SORU SORULUYOR.
    #
    # Olculdu: 28 reddin 19'u "sayisal bir olcum bulunmadigi icin
    # yorumlamak mumkun degildir" idi. Model HAKLIYDI -- ana yonerge
    # "en onemli tek OLCUMU sec" diyor ve bekleyis haberinde olcum yok.
    # Yanlis olan cevap degil, soruydu.
    #
    # Ikinci yonerge ayni haberden MEKANIZMA istiyor: hangi kanaldan
    # neyi etkiler, kim etkilenir, ne izlenir. Sayi denetimi yine
    # gecerli; girdide sayi yoksa ciktida da olmaz ve bu dogru olan.
    # OZEL YONERGE, ayni DOGRULAMA ZINCIRI.
    #
    # Bilanco yorumu farkli bir sey istiyor (kalemler arasindaki
    # iliski), haber yorumu farkli (en onemli tek olcum). Ama ciktinin
    # gecmesi gereken denetimler AYNI: cop cikti, sayi denetimi, yasak
    # kalip, guvenlik taramasi.
    #
    # Yeni bir `yorumla` kopyasi yazmak, o zincirin ikinci bir
    # surumunu yaratirdi ve biri duzeltilirken digeri unutulurdu.
    # Yalnizca YONERGE degisiyor.
    sistem = sistem_ozel or (SISTEM if olcum_var(girdi) else SISTEM_OLCUMSUZ)

    try:
        if s == "anthropic":
            metin, model = _anthropic_cagir(girdi, sistem), ANTHROPIC_MODEL
        else:
            metin, model = _cf_cagir(girdi, sistem)
    except httpx.HTTPStatusError as e:
        # 401 VE 403 ikisi de kapsam sorununa isaret ediyor.
        #
        # Olculdu: dagitim jetonu gecerli (ayni jetonla `wrangler deploy`
        # calisiyor) ama AI ucu 401 donuyor. Yani sorun jetonun gecersiz
        # olmasi degil, Workers AI KAPSAMINI tasimamasi -- "Edit
        # Cloudflare Workers" sablonuyla uretilen jetonda o izin
        # varsayilan olarak YOK.
        #
        # Ilk yazimda ipucu yalnizca 403'e bagliydi ve gercek hata 401
        # gelince sebep sessiz kaldi.
        kod = e.response.status_code
        ek = ""
        if kod in (401, 403):
            ek = (" -- jetonda 'Workers AI' izni yok gibi gorunuyor; "
                  "Cloudflare > My Profile > API Tokens uzerinden ekleyin")
        # SAGLAYICININ KENDI ACIKLAMASI. Ciplak "HTTP 400" hicbir sey
        # soylemiyor: bakiye bitmis de olabilir, model adi yanlis da,
        # istem cok uzun da. Uc ayri sebep, uc ayri cozum.
        #
        # Olculdu: 48 sirket "anthropic HTTP 400" ile atlandi ve sebep
        # koddan CIKARILAMADI -- gerekcesi ancak yanit govdesinde
        # yaziyordu. Saglayici zaten soyluyordu, ben dinlemiyordum.
        #
        # Govde KISALTILIYOR (200 karakter): hata yanitlari bazen
        # istemin tamamini geri yansitiyor ve log'a sizabilir.
        mesaj = ""
        try:
            g = e.response.json().get("error", {})
            mesaj = (g.get("message") or "").strip()
        except Exception:                              # noqa: BLE001
            mesaj = (e.response.text or "").strip()
        if mesaj:
            ek += f" -- {mesaj[:200]}"

        # SAGLAYICI KULLANILAMAZ HALE GELDIYSE DIGERINE GEC.
        #
        # Olculdu (2026-09-14): Anthropic bakiyesi bitti ve her cagri
        # HTTP 400 "credit balance is too low" dondu. 12 yorumun 12'si
        # reddedildi, "Yorum denetimi" kritik adimi dustu, kosu kirmizi
        # bitti -- ve ucretsiz saglayici butun bu sure boyunca CALISIR
        # DURUMDAYDI, hic denenmedi.
        #
        # Bir faturalandirma sorunu sitenin tumunu durdurmamali.
        #
        # 400 TEK BASINA YETMIYOR: "istem cok uzun" da 400 doner ve o
        # bu iSTEGE ozeldir, saglayiciya degil. Bu yuzden 400'de
        # yanitin METNINE bakiliyor.
        _kapatan = kod in _KAPATAN_KOD or (
            kod == 400
            and any(iz in mesaj.lower() for iz in _KAPATAN_IZ))
        _gecildi = False
        if s == "anthropic" and _kapatan:
            _anthropic_kapat(mesaj or f"HTTP {kod}")
            # Bayrak dolduktan sonra `saglayici()` artik cloudflare
            # donuyor -- yalnizca kimlik bilgisi varsa.
            if saglayici() == "cloudflare":
                try:
                    metin, model = _cf_cagir(girdi, sistem)
                    _gecildi = True
                except httpx.HTTPError as e2:
                    return "", "", (f"anthropic kapandi, cloudflare da "
                                    f"basarisiz: {type(e2).__name__}"), ""
        if not _gecildi:
            return "", "", f"{s} HTTP {kod}{ek}", ""
        # DOGRULAMA ZINCIRI KOPYALANMIYOR: akis asagida, `try` blogunun
        # normal ciktisiyla AYNI yoldan devam ediyor. Ikinci bir kopya,
        # birinin duzeltilip digerinin unutulmasi demekti -- bu modulun
        # kendi notu ayni sebeple `yorumla`nin kopyalanmasini
        # yasakliyor.
    except httpx.HTTPError as e:
        return "", "", f"{s} ag hatasi: {type(e).__name__}", ""
    if not metin:
        return "", "", f"{s} bos yanit", ""

    # Yazim duzeltmesi DOGRULAMADAN ONCE: duzeltmeler sayilara
    # dokunmuyor, dolayisiyla denetimin sonucunu degistirmiyor; ama
    # kaydedilen ham metin de duzgun olsun.
    metin = yazimi_duzelt(metin)

    # --- 0. COP CIKTI ---
    #
    # Bunlar "kotu yorum" degil, YORUM OLMAYAN sey. Digerlerinden ONCE
    # bakiliyor: bir istem yankisi ya da tekrar dongusu, sayi
    # denetiminden de cumle sayimindan da temiz gecebiliyor.
    #
    # OLCULDU, YAYIMLANDI. Bir TCMB basin duyurusu sayfasinda ve ana
    # sayfada su metin "Netaris yorumu" basligi altinda okura
    # gosterildi (@cf/openai/gpt-oss-120b, 1293 karakter):
    #
    #   analysis 0️⃣ We need to produce a " news release ( Basın
    #   Duyuru )" about inflation rates etc. The user wants ...
    #   Haber: Fa Fa Or Or Or Or Or Or Or Or Or Or Or Or Or ...
    #
    # Iki ayri ariza ust uste: model DUSUNME KANALINI ciktiya sizdirdi
    # ("analysis" bolumu) ve ardindan bozulup tek heceyi tekrarlamaya
    # basladi.
    #
    # HICBIR MEVCUT DENETIM YAKALAMADI. Sebebi olculdu: metinde nokta
    # neredeyse yok, dolayisiyla `_cumle_sayisi` 1293 karakterlik
    # yigini TEK CUMLE sayip uzunluk sinirindan geciriyordu.
    m = COP_CIKTI(metin)
    if m:
        return "", model, f"cop cikti: {m}", metin

    # --- 1. sayi denetimi ---
    kacak = sayi_denetimi(metin, girdi)
    if kacak:
        return "", model, f"girdide olmayan sayi: {', '.join(kacak[:4])}", metin

    # --- 1b. cevapsiz cikti ---
    #
    # "Olcum bulunmadigi icin yorum yapilamaz" bir yorum degil, bir
    # tutanak. Sayfada "Netaris yorumu" basligi altinda durmasi, okura
    # soyleyecek sozumuz oldugunu iddia edip hicbir sey sOylememek
    # oluyor. Bolum hic basilmasin diye metin REDDEDILIYOR.
    m = CEVAPSIZ.search(metin)
    if m:
        # Olcumsuz haberde bile gecerli: ikinci yonerge modelden
        # MEKANIZMA istiyor ve "yapamam" hala bir tutanak, yorum degil.
        return "", model, f"cevapsiz cikti: {m.group(0)!r}", metin

    # --- 1c. haberi tekrar etme ---
    #
    # "AI'in haberi farkli cumlelerle tekrar etmesi analiz olarak kabul
    # edilmez." Model girdiyi yeniden yazdiginda cikti dogru ve akici
    # olur -- ama okura hicbir sey katmaz ve sayfada "Netaris yorumu"
    # basligi altinda durur.
    oran = tekrar_orani(metin, girdi)
    if oran >= TEKRAR_ESIGI:
        return "", model, f"haberi tekrar ediyor (ortusme %{oran*100:.0f})", metin

    # --- 2. yasak kalip ---
    for d in YASAK:
        m = d.search(metin)
        if m:
            return "", model, f"yasak kalip: {m.group(0)!r}", metin

    # --- 2b. politika faizine ILISTIRILEN deger dogru mu ---
    #
    # Kavramdan soz etmek serbest; deger girdideki politika faizine
    # uymak zorunda. Gerekcesi `_politika_faizi_kusuru`nun basinda.
    _pf = _politika_faizi_kusuru(metin, girdi)
    if _pf:
        return "", model, f"politika faizine yanlis deger: {_pf}", metin

    m = SUREN_EGILIM.search(metin)
    if m:
        return "", model, f"suren egilim iddiasi: {m.group(0)!r}", metin

    # --- 2b. uzunluk ---
    #
    # Yonerge "en fazla 3 cumle" diyor; zayif model bunu duzenli olarak
    # asiyor ve girdiyi oldugu gibi tekrarlayan paragraflar uretiyor.
    # Kirpmak cumleyi ortasindan kesecegi icin metin TAMAMEN atiliyor.
    n = _cumle_sayisi(metin)
    if n > EN_COK_CUMLE:
        return "", model, f"{n} cumle (en fazla {EN_COK_CUMLE})", metin

    # --- 3. yayin ilkeleri (uye yazilariyla AYNI tarayici) ---
    #
    # `yayinlanabilir()` DEGIL `tara()` kullaniliyor: birincisi metnin
    # ICINDE "yatirim tavsiyesi degildir" uyarisi ariyor ve uc cumlelik
    # bir paragrafta bunu istemek yanlis olurdu -- uyari sayfanin
    # kendisinde, her haber sayfasinin altinda duruyor. Aranan sey
    # yasak seviyesindeki bulgular.
    yasak = [b for b in guvenlik.tara(metin)
             if b.seviye is guvenlik.Seviye.YASAK]
    if yasak:
        return "", model, f"guvenlik taramasi: {yasak[0].aciklama}", metin

    # --- 4. KESIK CEVAP YAYIMLANMAZ ---
    #
    # OLCULEN HATA: sayfada yorum "...yen borclanip baska varliklara
    # yatirilan..." diye bitiyordu. CSS kirpmasi degil; DEPODAKI METIN
    # yarimdi: "Kanal iki ucl".
    #
    # Sebep `EN_COK_JETON = 420`: model tavana carpiyor ve cumleyi
    # ortasinda birakiyor. Yukaridaki cumle sayisi kontrolu bunu
    # GECIRIYOR -- kesik cevap zaten az cumleli gorunuyor, yani kontrol
    # tam ters yonde koruma sagliyordu.
    #
    # Olcut: metin CUMLE BITIRICI bir noktalama ile bitmeli. Bitmiyorsa
    # cevap tamamlanmamis demektir ve yarim cumle yayimlamak, hic
    # yayimlamamaktan kotudur -- okur eksigi gorur ve guveni gider.
    #
    # Kirpmiyoruz, REDDEDIYORUZ: kirpmak "yatirilan..." yerine
    # "...getirdi." birakirdi ama modelin kurmak istedigi cumleyi biz
    # kesmis olurduk. Ret, bir sonraki kosuda yeniden uretilmesini
    # sagliyor.
    if not metin.rstrip().endswith((".", "!", "?", "…", '."', ".)")):
        return "", model, "kesik cevap (cumle bitmiyor)", metin

    # Fazla uzun cevaplari kirpmiyoruz -- kirpmak cumleyi ortasindan
    # kesip anlamsiz birakabilir. Uc cumleyi asan cevap zaten yonergeye
    # uymamis demektir; oldugu gibi birakilip insan denetimine kaliyor.
    return metin, model, "", metin
