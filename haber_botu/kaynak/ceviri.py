"""Ingilizce -> Turkce ceviri, ucretsiz ve anahtarsiz.

KAYNAK SECIMI
-------------
MyMemory ceviri bellegi. Anahtar istemiyor, CORS aciyor, e-posta
parametresiyle gunluk 50.000 kelime kota veriyor. Olculdu:

    "Federal Reserve issues FOMC statement"
    -> "Federal Rezerv, FOMC bildirisi yayınladı"

Denenip elenenler: LibreTranslate kamu ornekleri (400/502/403 -- hepsi
kapali ya da anahtar istiyor), DeepL (ucretsiz katman var ama anahtar
gerekiyor).

ONBELLEK NEDEN SART
-------------------
Gundem her calistirmada ayni basliklarin cogunu yeniden gorur. Onbelleksiz
her calistirma kotayi bastan harcar ve gunde birkac kez calistirmak
imkansiz hale gelir. Onbellek dosyaya yazilir, surecler arasi kalicidir.

CEVIRI SINIRI -- durust olmak gerekiyor
---------------------------------------
Bu bir makine cevirisidir. Resmi bir kurumun aciklamasinda nuans kaybi
olabilir; bu yuzden site tarafinda cevirinin makine cevirisi oldugu
YAZILIR ve orijinal baslik ile kaynak baglantisi her zaman gosterilir.
Okur isterse kaynaga gidip kendi okuyabilmeli.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time

import httpx

UC = "https://api.mymemory.translated.net/get"
# Kimlik TEK yerden gelir; 20 dosyada elle yazilinca surukledi.
# Iki bicim de kullaniliyor: `import ceviri` (kaynak/ sys.path'te)
# ve `from kaynak import ceviri` (haber_botu/ sys.path'te).
try:
    from kimlik import ajan
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak.kimlik import ajan

BASLIKLAR = {"User-Agent": ajan("haber cevirisi")}
ZAMAN_ASIMI = 25.0

#: Kotayi 1.000 kelimeden 50.000 kelimeye cikarir. Adres GECERLI
#: olmali: MyMemory dogrulayamazsa ayricalik sessizce dusuyor.
#: `netaris.com` bizim degil -- bkz. kimlik.py.
try:
    from kimlik import ILETISIM
except ImportError:  # pragma: no cover
    from kaynak.kimlik import ILETISIM

ONBELLEK_YOLU = pathlib.Path(__file__).parent / "ceviri_onbellek.json"

#: Istekler arasi bekleme -- ucretsiz servise saygili davranmak
BEKLEME_SN = 0.35


class Cevirmen:
    """Onbellekli ceviri istemcisi."""

    def __init__(self, onbellek_yolu: pathlib.Path = ONBELLEK_YOLU):
        self.yol = onbellek_yolu
        self.onbellek: dict[str, str] = {}
        self.yeni_ceviri = 0
        self.onbellekten = 0
        self.basarisiz = 0
        self._yukle()

    def _yukle(self) -> None:
        if self.yol.exists():
            try:
                self.onbellek = json.loads(self.yol.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.onbellek = {}

    def kaydet(self) -> None:
        self.yol.write_text(
            json.dumps(self.onbellek, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    @staticmethod
    def _anahtar(metin: str) -> str:
        return hashlib.sha256(metin.strip().encode("utf-8")).hexdigest()[:16]

    def cevir(self, metin: str) -> str:
        """Metni Turkce'ye cevirir. Basarisiz olursa ORIJINALI dondurur.

        Basarisizlikta orijinali dondurmek bilincli: yarim ya da bozuk bir
        ceviri yayimlamaktansa kaynak dilinde birakmak dogru. Cagiran taraf
        `ceviri_yapildi` ile hangisinin oldugunu ogrenir.
        """
        metin = metin.strip()
        if not metin:
            return metin

        anahtar = self._anahtar(metin)
        if anahtar in self.onbellek:
            self.onbellekten += 1
            return self.onbellek[anahtar]

        try:
            r = httpx.get(
                UC,
                params={"q": metin, "langpair": "en|tr", "de": ILETISIM},
                headers=BASLIKLAR,
                timeout=ZAMAN_ASIMI,
            )
            r.raise_for_status()
            veri = r.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError):
            self.basarisiz += 1
            return metin

        if veri.get("quotaFinished"):
            self.basarisiz += 1
            return metin

        ceviri = (veri.get("responseData") or {}).get("translatedText", "").strip()
        if not ceviri or ceviri.upper().startswith("MYMEMORY WARNING"):
            self.basarisiz += 1
            return metin

        ceviri = tire_duzelt(_duzelt(ceviri), metin)
        self.onbellek[anahtar] = ceviri
        self.yeni_ceviri += 1
        time.sleep(BEKLEME_SN)
        return ceviri

    def ceviri_yapildi(self, orijinal: str, sonuc: str) -> bool:
        return orijinal.strip() != sonuc.strip()

    def ozet(self) -> str:
        return (f"{self.yeni_ceviri} yeni ceviri, {self.onbellekten} onbellekten, "
                f"{self.basarisiz} basarisiz")


#: Makine cevirisinin Turkce'de siklikla bozdugu bicim kurallari
_DUZELTMELER = (
    # "% 2,7" -> "%2,7"  (Turkce'de isaret sayiya bitisiktir)
    (r"%\s+(\d)", r"%\1"),
    # "2027 'nin" -> "2027'nin"  (kesme isaretinden onceki bosluk)
    #
    # DESEN DARALTILDI. Once `\s+'` idi ve ACILIS TIRNAGINI da yiyordu:
    #   "Deutsche Bank 'gerçek değeri' açıkladı"
    #   -> "Deutsche Bank'gerçek değeri' açıkladı"
    # Olculdu: bes basligin dordu boyle bozuldu.
    #
    # Ayirt edici, kesme isaretinden SONRA gelen: Turkce ek en fazla
    # dort harftir ve orada biter ("'nin ", "'de,"). Alintinin ilk
    # sozcugu ise daha uzun ("'gerçek", "'zorlu"). Ek olamayacak kadar
    # uzunsa bosluk korunuyor.
    (r"\s+'(?=[a-zçğıöşü]{1,4}(?:\s|$|[.,;:!?]))", "'"),
    # Cift bosluk
    (r"\s{2,}", " "),
    # Noktalama oncesi bosluk
    (r"\s+([,.;:!?])", r"\1"),
)

#: FINANSAL TERIM SOZLUGU -- ceviriden SONRA uygulanir.
#:
#: Genel amacli ceviri motorlari finansal terimleri gunluk anlamlariyla
#: cevirir ve sonuc teknik olarak yanlis olur. Olculen ornekler:
#:
#:   "enforcement action" -> "icra davasi"
#:       Icra davasi borc tahsilatidir. Bankacilik duzenlemesinde bu
#:       "yaptirim karari"dir; ikisinin hukuki anlami tamamen farkli.
#:
#: Desenler kelime siniriyla eslesir; "icra" kelimesi baska bir baglamda
#: gectiginde bozulmamasi icin cevresindeki sozcuklerle birlikte aranir.
_TERIMLER = (
    (r"\bicra (davası|davaları) açtı\b", "yaptırım kararı verdi"),
    (r"\bicra (davası|davaları)\b", "yaptırım kararı"),
    (r"\bicra (işlemleri|işlemi) başlattı\b", "yaptırım işlemi başlattı"),
    (r"\bicra (işlemleri|işlemi)\b", "yaptırım işlemi"),
    (r"\bkarşılıklı bankacılık\b", "karşılıklı tasarruf bankacılığı"),
    (r"\biçerdeki(ler|lere)?\b", r"içeriden öğrenenler"),
    (r"\bgörüş talep ediyor\b", "görüşe açtı"),
    (r"\byorum yapılmasını talep ediyor\b", "görüşe açtı"),
    (r"\byorum talep ediyor\b", "görüşe açtı"),
    (r"\bpara politikası beyanı\b", "para politikası açıklaması"),
    (r"\bücret izleyicisi\b", "ücret göstergesi"),

    # "inflation runs hot" -> "enflasyon sicak calisirsa".
    # Deyim kelimesi kelimesine cevrilince makine cumlesi cikiyor;
    # finansal anlami "enflasyon yuksek seyrederse".
    (r"\benflasyon sıcak çalışırsa\b", "enflasyon yüksek seyrederse"),
    (r"\benflasyon sıcak çalışıyor\b", "enflasyon yüksek seyrediyor"),
    (r"\bsıcak çalışırsa\b", "yüksek seyrederse"),

    # KURUM KISALTMASI ANLAMINA GORE CEVRILIYOR.
    # Olculdu: "EIA Natural Gas Change BCF" -> "ÇED Doğal Gaz Değişimi".
    # ÇED cevresel etki degerlendirmesidir; buradaki EIA ABD Enerji
    # Bilgi Idaresi'dir. Kisaltma yanlis acilinca haber baska bir
    # kurumun aciklamasi gibi okunuyor.
    (r"\bÇED\b", "EIA"),
    (r"\bÇevresel Etki Değerlendirmesi (Doğal Gaz|Ham Petrol|Petrol)",
     r"EIA \1"),
    # "BCF" hacim birimi (milyar kubik feet); ceviri motoru bazen
    # bosluk ekleyip parcaliyor.
    (r"\bB\s?C\s?F\b", "BCF"),
)

#: OZEL ADLAR -- cevrilmemeli.
#:
#: Ceviri motoru kurum adlarini anlamlarina gore ceviriyor:
#:   "Regions Bank" -> "Bölgeler Bankası"
#: Bu, var olmayan bir kurum adi uretmek demek. Ozel ad oldugu gibi kalir.
#: SIRA ONEMLI: EKLI BICIMLER ONCE.
#: "Bölgeler Bankası" once degistirilirse geriye "Regions Bank'nın" kalir --
#: Turkce'de ek son sesliye gore degisiyor ("Bankası'nın" ama "Bank'ın"),
#: ve kisa desen once eslesince ek duzeltilemez hale geliyor.
_OZEL_ADLAR = (
    ("Bölgeler Bankası'nın", "Regions Bank'ın"),
    ("Bölgeler Bankası'na", "Regions Bank'a"),
    ("Bölgeler Bankası'nda", "Regions Bank'ta"),
    ("Bölgeler Bankası", "Regions Bank"),
    ("Beşinci Üçüncü Banka", "Fifth Third Bank"),
    ("Zenginlik Yönetimi", "Wealth Management"),
    ("Vadeli İşlemler Borsası", "Futures Exchange"),
    ("Federal Rezerv Kurulu'nun", "Fed Kurulu'nun"),
    ("Federal Rezerv Kurulu", "Fed Kurulu"),
    ("Federal Rezerv'in", "Fed'in"),
    ("Federal Rezerv", "Fed"),
)

#: Duzeltme sonrasi kalabilecek ek uyumsuzluklari toplar.
#: "Bank'nın" gibi bir bicim, ozel ad degisimi sirasinda olusabiliyor;
#: Turkce'de sessizle biten sozcuk "'nın" almaz.
_EK_DUZELTME = (
    (r"Bank'nın\b", "Bank'ın"),
    (r"Bank'na\b", "Bank'a"),
    (r"Bank'nda\b", "Bank'ta"),
    (r"Fed'nin\b", "Fed'in"),
)


#: Bosluklu tire: "ABD - Kanada". Iki yanindaki TEK kelimeyi yakalar.
_BOSLUKLU_TIRE = re.compile(r"(?<=\w)\s+[-–]\s+(?=\w)")


def tire_duzelt(ceviri: str, kaynak: str) -> str:
    """Ceviri sirasinda tirenin etrafina eklenen bosluklari kaldirir.

    Olculdu -- 313 basligin 12'sinde var:
        kaynak "U.S.-Canada energy trade"  -> bizim "ABD - Kanada ..."
        kaynak "Monetary policy (with Q&A)" -> bizim "... (Soru - Cevap ile)"
        kaynak "tele-rally"                 -> bizim "tele - miting"

    AMA HER " - " HATA DEGIL. Turkce'de bosluklu tire iki cumleyi ayirir
    ve kaynaklarin kendisi de kullaniyor:
        "Finansal Hesaplar - 2026 I. Ceyrek"
        "Sandisk, Block kazanclari - piyasalari neler etkiliyor"
    Bunlari duzeltmek yeni bir hata olurdu.

    AYIRT EDICI KAYNAK METNIDIR: kaynakta bosluga komsu tire varsa
    bizimki de oyle kalir.
    KURAL SAYIYA DAYANIYOR. Ilk yazimda yalnizca "kaynakta bosluklu tire
    var mi" diye bakiyordum ve iki basligi BOZDUM:
        "May-July vs Year Earlier" -> cevirmen "vs"i de " - " yapmisti;
            duzeltme "Mayis-Temmuz-Bir Onceki Yil" uretti
        "in July -Lloyds"          -> kaynak eki tireyle baglamis;
            duzeltme "artti-Lloyd's" uretti
    Ikisinde de kaynaktaki tire sayisi ile cevirideki bosluklu tire
    sayisi TUTMUYOR. Tutmuyorsa hangi tirenin hangisine karsilik geldigi
    belirsizdir ve belirsizken dokunmuyoruz.
    """
    if not ceviri or not kaynak:
        return ceviri
    # Bosluga komsu tire AYIRICIDIR (" - ", " -Lloyds"): kaynagin uslubu.
    if re.search(r"\s[-–]|[-–]\s", kaynak):
        return ceviri
    kaynak_birlesik = len(re.findall(r"\w[-–]\w", kaynak))
    ceviri_bosluklu = len(_BOSLUKLU_TIRE.findall(ceviri))
    if ceviri_bosluklu == 0:
        return ceviri
    # Kaynakta hic tire yoksa bosluklu tire cevirmenin ekledigidir
    # ("Q&A" -> "Soru - Cevap"); ama yalnizca tek bir tane varsa.
    if kaynak_birlesik == 0:
        return _BOSLUKLU_TIRE.sub("-", ceviri) if ceviri_bosluklu == 1 else ceviri
    if kaynak_birlesik != ceviri_bosluklu:
        return ceviri
    return _BOSLUKLU_TIRE.sub("-", ceviri)


def _duzelt(metin: str) -> str:
    """Makine cevirisinin biraktigi hatalari toplar.

    Uc katman:
      1. Bicim  -- "% 2,7" -> "%2,7", "2027 'nin" -> "2027'nin"
      2. Terim  -- "icra davasi" -> "yaptirim karari"
      3. Ozel ad -- "Bölgeler Bankası" -> "Regions Bank"

    Sira onemli: ozel adlar en sonda, cunku terim duzeltmeleri ozel ad
    iceren cumleleri de degistirebiliyor.
    """
    for desen, yerine in _DUZELTMELER:
        metin = re.sub(desen, yerine, metin)
    for desen, yerine in _TERIMLER:
        metin = re.sub(desen, yerine, metin, flags=re.IGNORECASE)
    for yanlis, dogru in _OZEL_ADLAR:
        metin = metin.replace(yanlis, dogru)
    for desen, yerine in _EK_DUZELTME:
        metin = re.sub(desen, yerine, metin)
    return metin.strip()


def onbellek_tazele(onbellek: dict[str, str]) -> int:
    """Onbellekteki cevirilere guncel duzeltmeleri uygular.

    Sozluge yeni terim eklendiginde eski ceviriler kendiliginden
    duzelmez -- onbellekten geldikleri icin `_duzelt` hic calismaz. Bu
    islev onbellegi bastan gecirir; kota harcamaz cunku yeniden ceviri
    yapilmaz.
    """
    n = 0
    for anahtar, deger in list(onbellek.items()):
        yeni = _duzelt(deger)
        if yeni != deger:
            onbellek[anahtar] = yeni
            n += 1
    return n
