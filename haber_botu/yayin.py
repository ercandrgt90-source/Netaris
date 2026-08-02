"""Uretilen analizi site icerik klasorune yazar.

Hattin son halkasi:
    veri -> oran -> skor -> AI yorum -> tarama -> **site icerigi**

Frontmatter'i kod uretir, model degil. Boylece slug, tarih, skor ve kriter
puanlari her zaman hesaplanan degerlerle birebir ayni olur; modelin
metninden ayristirmaya calismak sessiz tutarsizlik uretirdi.

Onemli: yazilan dosya SITE ICERIGIDIR ama otomatik yayimlanmaz. Site
uretecini calistirmak (site/insa.py) ayri bir adimdir ve insan onayindan
sonra yapilir.
"""

from __future__ import annotations

import pathlib
import re
import unicodedata
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Yalnizca tip denetimi icin. Calisma aninda import edilmezse makro
    # hatti bilanco modullerini yuklemek zorunda kalmaz -- iki hat
    # birbirinden bagimsiz calisabilmeli.
    from oranlar import Rapor
    from skor import Skor

# site/icerik/analizler -- haber_botu ile kardes klasor
SITE_ICERIK = pathlib.Path(__file__).parent.parent / "site" / "icerik" / "analizler"

_SLUG_ESLEME = str.maketrans(
    {
        "ı": "i", "İ": "i", "I": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
        "â": "a", "î": "i", "û": "u",
    }
)


def slugla(metin: str) -> str:
    metin = unicodedata.normalize("NFC", metin).translate(_SLUG_ESLEME).lower()
    return re.sub(r"[^a-z0-9]+", "-", metin).strip("-")


def _baslik_ayikla(govde: str) -> tuple[str, str]:
    """Metnin basindaki H1 basligi ayirir.

    Model bazen '# Baslik' ile basliyor, bazen dogrudan '## Ozet' ile.
    Baslik varsa frontmatter'a tasinir ve govdeden cikarilir -- sayfada
    basligi sablon basiyor, iki kez gorunmemeli.
    """
    satirlar = govde.lstrip().splitlines()
    if satirlar and satirlar[0].startswith("# "):
        return satirlar[0][2:].strip(), "\n".join(satirlar[1:]).lstrip("\n")
    return "", govde.lstrip()


def _ozet_ayikla(govde: str) -> str:
    """'## Ozet' bolumunun ilk paragrafini meta aciklama olarak kullanir."""
    eslesme = re.search(r"^##\s*Özet\s*$(.*?)(?=^##\s|\Z)", govde, re.M | re.S)
    if not eslesme:
        # Ozet bolumu yoksa ilk anlamli paragrafi al
        for parca in govde.split("\n\n"):
            temiz = parca.strip()
            if temiz and not temiz.startswith("#"):
                return " ".join(temiz.split())
        return ""
    parcalar = [p.strip() for p in eslesme.group(1).strip().split("\n\n") if p.strip()]
    return " ".join(parcalar[0].split()) if parcalar else ""


def _kisalt(metin: str, sinir: int = 300) -> str:
    """Meta aciklama icin kirp -- cumle ortasinda kesmemeye calisir."""
    if len(metin) <= sinir:
        return metin
    kirpik = metin[:sinir]
    son = max(kirpik.rfind(". "), kirpik.rfind("? "), kirpik.rfind("! "))
    return (kirpik[: son + 1] if son > sinir * 0.5 else kirpik.rstrip()) + "…"


def _frontmatter(
    rapor: Rapor,
    skor: Skor | None,
    baslik: str,
    ozet: str,
    slug: str,
    kurgusal: bool,
) -> str:
    satirlar = [
        "---",
        f"slug: {slug}",
        f"baslik: {baslik}",
        f"ozet: {ozet}",
        f"sirket: {rapor.sirket}",
        f"kod: {rapor.kod}",
        f"donem: {rapor.donem}",
        "kategori: Bilanço Analizi",
        f"tarih: {date.today().isoformat()}",
        "veri_kaynagi: KAP finansal tabloları (TMS 29)",
        f"kurgusal: {'evet' if kurgusal else 'hayir'}",
    ]

    # Skor yalnizca yayina uygunsa frontmatter'a girer. Kapsami dusuk bir
    # skoru sayfada gostermek yaniltir.
    if skor is not None and skor.yayimlanabilir and skor.skor is not None:
        satirlar.append(f"skor: {skor.skor:.0f}")
        satirlar.append(f"kapsam: {skor.kapsam * 100:.0f}")
        for k in skor.kriterler:
            if k.olculdu:
                puan = f"{k.puan:.1f}".replace(".", ",")
                satirlar.append(f"kriter: {k.ad}|{puan}|{k.olculen_puan}")

    satirlar.append("---")
    return "\n".join(satirlar)


def grafik_alani(ciftler: list[tuple[str, float]]) -> str:
    """Gorsel icin veri satiri uretir: 'Etiket|deger;Etiket|deger'

    Ayrac NOKTALI VIRGUL -- Turkce'de virgul ondalik ayracidir. Virgulle
    ayirmak sessizce yanlis seri uretir; bu tuzaga girdi dosyalarinda bir
    kez dustuk.
    """
    return ";".join(f"{ad}|{deger:.1f}".replace(".", ",") for ad, deger in ciftler)


def yaz_sektorel(
    govde: str,
    sirket: str,
    kod: str,
    donem: str,
    sektor: str,
    kaynak: str = "KAP finansal tabloları (TMS 29)",
    grafik: str = "",
    kaynaklar: str = "",
    sayimlar: str = "",
    klasor: pathlib.Path | None = None,
) -> pathlib.Path:
    """Skor URETILMEYEN bilanco analizini yazar.

    Neden ayri: `yaz()` skor bekliyor ve sanayi motoruna bagli. Araci kurum
    gibi sektorlerde skor esikleri henuz kalibre edilmedi; kalibre edilmemis
    bir skoru yayimlamak, olculmemis bir seyi olculmus gibi gostermek olur.
    Skor yok, ama yazi bilanco kategorisinde ve kendi hisse koduyla yayimlanir
    -- makro kategorisine atmak sinifllandirmayi bozardi.
    """
    hedef = klasor or SITE_ICERIK
    hedef.mkdir(parents=True, exist_ok=True)

    baslik, temiz = _baslik_ayikla(govde)
    if not baslik:
        baslik = f"{sirket} {donem} bilanço analizi"

    slug = slugla(f"{kod} {donem}")
    on = "\n".join(
        [
            "---",
            f"slug: {slug}",
            f"baslik: {baslik}",
            f"ozet: {_kisalt(_ozet_ayikla(temiz))}",
            f"sirket: {sirket}",
            f"kod: {kod}",
            f"donem: {donem}",
            "kategori: Bilanço Analizi",
            f"sektor: {sektor}",
            f"tarih: {date.today().isoformat()}",
            f"veri_kaynagi: {kaynak}",
            "kurgusal: hayir",
            "grafik_tur: sutun",
            f"grafik: {grafik}",
            # Bu iki alan sayfadaki "nasil uretildi" kutusunu besler.
            # Rakamlar GERCEK sayimdir: kac oran hesaplandi, kac sinyal
            # esigi asti, kac kalem okundu. Pazarlama amacli yuvarlanmis
            # bir sayi degil.
            f"kaynaklar: {kaynaklar}",
            f"sayimlar: {sayimlar}",
            "---",
        ]
    )
    dosya = hedef / f"{slugla(donem)}-{slugla(kod)}.md"
    dosya.write_text(f"{on}\n\n{temiz.rstrip()}\n", encoding="utf-8")
    return dosya


def yaz_makro(
    govde: str,
    konu: str,
    kaynak: str = "FRED, TCMB EVDS",
    grafik: str = "",
    grafik_kod: str = "",
    grafik_birim: str = "",
    kaynaklar: str = "",
    sayimlar: str = "",
    kategori: str = "Makro",
    kod: str = "MAKRO",
    yazar: str = "",
    unvan: str = "",
    ozet_metni: str = "",
    #: Gecmis tarihli yazi icin ISO tarih. Bos birakilirsa bugun kullanilir.
    #: Bir merkez bankasi kararini yanlis tarihle yayimlamak, finans
    #: yayininda geri donusu olmayan hatalardan biridir.
    tarih_ustu: str = "",
    klasor: pathlib.Path | None = None,
) -> pathlib.Path:
    """Makro yorumu site icerik klasorune yazar.

    Bilanco yazisindan farklari: skor yok (skor bilancoya ozgu), sirket/kod
    yok, dosya adi tarih + konu bicimide. Ayni gun ayni konuda ikinci bir
    yazi uretilirse uzerine yazilir -- duzeltme icin istenen davranis.
    """
    hedef = klasor or SITE_ICERIK
    hedef.mkdir(parents=True, exist_ok=True)

    baslik, temiz = _baslik_ayikla(govde)
    if not baslik:
        baslik = konu

    bugun = tarih_ustu.strip() or date.today().isoformat()
    slug = slugla(f"{konu} {bugun}")

    on = "\n".join(
        [
            "---",
            f"slug: {slug}",
            f"baslik: {baslik}",
            # Imzali yorumda ozeti yazar kendi yazar; otomatik ciktida
            # metnin ilk paragrafindan cikarilir
            f"ozet: {ozet_metni or _kisalt(_ozet_ayikla(temiz))}",
            f"sirket: {konu}",
            f"kod: {kod}",
            f"donem: {bugun}",
            f"kategori: {kategori}",
            f"tarih: {bugun}",
            f"veri_kaynagi: {kaynak}",
            f"yazar: {yazar}",
            f"unvan: {unvan}",
            "kurgusal: hayir",
            "grafik_tur: cizgi",
            f"grafik: {grafik}",
            f"grafik_kod: {grafik_kod}",
            f"grafik_birim: {grafik_birim}",
            f"kaynaklar: {kaynaklar}",
            f"sayimlar: {sayimlar}",
            "---",
        ]
    )
    dosya = hedef / f"{bugun}-makro-{slugla(konu)}.md"
    dosya.write_text(f"{on}\n\n{temiz.rstrip()}\n", encoding="utf-8")
    return dosya


def yaz(
    rapor: Rapor,
    govde: str,
    skor: Skor | None = None,
    kurgusal: bool = False,
    klasor: pathlib.Path | None = None,
) -> pathlib.Path:
    """Analizi site icerik klasorune frontmatter'li olarak yazar.

    Donen deger yazilan dosyanin yolu. Ayni sirket-donem icin tekrar
    calistirilirsa dosya UZERINE YAZILIR -- duzeltme yayimlamak icin
    istenen davranis bu.
    """
    hedef_klasor = klasor or SITE_ICERIK
    hedef_klasor.mkdir(parents=True, exist_ok=True)

    baslik, temiz_govde = _baslik_ayikla(govde)
    if not baslik:
        baslik = f"{rapor.sirket} {rapor.donem} bilanço analizi"

    ozet = _kisalt(_ozet_ayikla(temiz_govde))
    slug = slugla(f"{rapor.kod} {rapor.donem}")

    on = _frontmatter(rapor, skor, baslik, ozet, slug, kurgusal)
    dosya = hedef_klasor / f"{slugla(rapor.donem)}-{slugla(rapor.kod)}.md"
    dosya.write_text(f"{on}\n\n{temiz_govde.rstrip()}\n", encoding="utf-8")
    return dosya
