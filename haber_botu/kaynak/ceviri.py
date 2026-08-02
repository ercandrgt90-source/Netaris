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
BASLIKLAR = {"User-Agent": "Netaris/0.1 (finansal yayin)"}
ZAMAN_ASIMI = 25.0

#: Kotayi 1.000 kelimeden 50.000 kelimeye cikarir
ILETISIM = "iletisim@netaris.com"

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

        ceviri = _duzelt(ceviri)
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
    (r"\s+'", "'"),
    # Cift bosluk
    (r"\s{2,}", " "),
    # Noktalama oncesi bosluk
    (r"\s+([,.;:!?])", r"\1"),
)


def _duzelt(metin: str) -> str:
    """Makine cevirisinin biraktigi bicim hatalarini toplar.

    MyMemory Turkce'de yuzde isaretini sayidan ayiriyor ("% 2,7") ve kesme
    isaretinden once bosluk birakiyor ("2027 'nin"). Ikisi de duzeltilebilir
    ve duzeltilmezse metin ceviri kokuyor.
    """
    for desen, yerine in _DUZELTMELER:
        metin = re.sub(desen, yerine, metin)
    return metin.strip()
