"""Elle girilen bilanco verisini okur ve dogrular.

Yari otomatik kopru: insan KAP'tan rakamlari okuyup bir metin dosyasina
yazar, gerisini hat otomatik yapar.

    veri/THYAO-2025-12.txt  ->  Donem nesneleri  ->  oran -> skor -> yazi

DOGRULAMA NEDEN BURADA
----------------------
Elle giris, hatanin dogdugu yerdir. En sik ikisi:

  * **Birim hatasi.** Bin TL'lik tabloyu TL sanmak, ya da tersi. Rakam bin
    kat sapar ve hicbir yerde uyari cikmaz -- motor kendinden emin sekilde
    yanlis analiz uretir.
  * **Satir kaymasi.** Brut kari faaliyet kari sutunundan okumak.

Bu tur hatalar sessizdir: sayilar makul gorunur, oranlar hesaplanir, yazi
yazilir, yanlis bilgi yayimlanir. Muhasebe ozdeslikleri (aktif = kaynaklar,
brut kar <= hasilat) bunlarin cogunu yakalar. Yakalayamadigini da buyukluk
karsilastirmasi yakalar.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from enum import Enum

from oranlar import Donem, EnflasyonEsasi

VERI = pathlib.Path(__file__).parent / "veri"

SABLON = """\
# =====================================================================
#  Bilanco veri girisi
#  Rakamlari KAP'taki finansal tablodan oldugu gibi kopyalayin.
#
#  ONEMLI: Tablonun birimini kontrol edin. KAP tablolari genellikle
#  "bin TL" olarak yayimlanir. Buraya TAM TL yazin -- bin TL'lik bir
#  rakami oldugu gibi yazarsaniz analiz bin kat yanlis cikar.
#
#  Bilmediginiz / tabloda olmayan satiri BOS BIRAKIN, sifir yazmayin.
#  Bos birakilan kalem "olculemedi" sayilir; sifir "deger sifir" demektir.
#
#  Sayilari nokta ya da bosluk ayracli yazabilirsiniz: 17.360.000.000
# =====================================================================

kod:
sirket:
donem:
onceki_donem:

# Enflasyon esasi:
#   tms29    -> TMS 29 duzeltilmis tablo (BIST sirketleri 2023 sonundan beri)
#   nominal  -> duzeltilmemis; bu durumda tufe alanini da doldurun
esas:           tms29
tufe:

# ---------------------------------------------------------------------
#  CARI DONEM
# ---------------------------------------------------------------------
hasilat:
brut_kar:
faaliyet_kari:
favok:
net_kar:
faaliyet_disi_net:

aktif_toplami:
ozkaynak:
donen_varliklar:
kisa_vadeli_yukumlulukler:
ticari_alacaklar:
stoklar:
net_borc:

faaliyet_nakit_akisi:
yatirim_harcamasi:
finansman_gideri:

# ---------------------------------------------------------------------
#  ONCEKI DONEM  (karsilastirma icin)
# ---------------------------------------------------------------------
onceki.hasilat:
onceki.brut_kar:
onceki.faaliyet_kari:
onceki.favok:
onceki.net_kar:
onceki.faaliyet_disi_net:

onceki.aktif_toplami:
onceki.ozkaynak:
onceki.donen_varliklar:
onceki.kisa_vadeli_yukumlulukler:
onceki.ticari_alacaklar:
onceki.stoklar:
onceki.net_borc:

onceki.faaliyet_nakit_akisi:
onceki.yatirim_harcamasi:
onceki.finansman_gideri:

# ---------------------------------------------------------------------
#  Gecmis hasilat buyumeleri (reel %) -- trend karsilastirmasi icin.
#  AYRAC NOKTALI VIRGUL:  28,0; 34,0; 31,0; 25,0
#  Virgul ondalik ayracidir, ayrac olarak KULLANILMAZ. Bilmiyorsaniz bos birakin.
# ---------------------------------------------------------------------
gecmis_buyumeler:
"""


class Seviye(Enum):
    HATA = "hata"
    UYARI = "uyari"


@dataclass(frozen=True)
class Bulgu:
    seviye: Seviye
    mesaj: str

    def __str__(self) -> str:
        return f"[{self.seviye.value.upper()}] {self.mesaj}"


def _sayi(ham: str) -> float | None:
    """Turkce bicimli sayiyi cozer. Bos ise None.

    Kabul edilenler: 17.360.000.000 | 17 360 000 000 | 17360000000
    Ondalik virgul de desteklenir: 2,84
    """
    temiz = ham.strip()
    if not temiz:
        return None

    negatif = temiz.startswith("-")
    temiz = temiz.lstrip("-+").strip()

    # Ondalik virgul varsa: noktalar binlik ayraci
    if "," in temiz:
        temiz = temiz.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        temiz = temiz.replace(".", "").replace(" ", "")

    try:
        d = float(temiz)
    except ValueError:
        raise ValueError(f"sayi cozulemedi: {ham!r}")
    return -d if negatif else d


def _gecmis_buyumeler(ham: str, dosya: str) -> list[float]:
    """Gecmis donem buyume yuzdelerini cozer. Ayrac NOKTALI VIRGUL.

    Neden virgul degil: Turkce'de virgul ondalik ayracidir. "28,0 , 34,0"
    ifadesini virgulle bolmek [28, 0, 34, 0] uretir -- sessizce iki kat
    fazla deger ve araya sifirlar. Ortalama yariya duser ve hicbir yerde
    hata cikmaz; model de kendisine verilen bozuk rakami sadakatle yazar.

    Bu hata bir kez gercekten yasandi: ortalama %29,5 yerine %14,8 hesaplandi
    ve yayina hazir metne girdi. Bu yuzden eski bicim artik sessizce
    kabul edilmiyor, acik hata veriyor.
    """
    ham = ham.strip()
    if not ham:
        return []

    if ";" not in ham and "," in ham:
        raise ValueError(
            f"{dosya}: 'gecmis_buyumeler' alaninda ayrac NOKTALI VIRGUL olmali.\n"
            "  Turkce'de virgul ondalik ayracidir; virgulle ayirmak degerleri boler.\n"
            f"  Yanlis: {ham}\n"
            f"  Dogru : {ham.replace(' , ', '; ').replace(',', ',')}"
        )

    degerler = [d for d in (_sayi(p) for p in ham.split(";")) if d is not None]

    # Buyume serisinde tam sifir olagandisi -- bolme hatasinin izi olabilir
    if degerler and degerler.count(0.0) > len(degerler) / 3:
        raise ValueError(
            f"{dosya}: 'gecmis_buyumeler' icinde cok sayida sifir var {degerler}.\n"
            "  Ayrac hatasi olabilir -- degerleri noktali virgulle ayirin."
        )
    return degerler


def _alanlar(metin: str) -> dict[str, str]:
    sonuc: dict[str, str] = {}
    for ham in metin.splitlines():
        satir = ham.split("#", 1)[0].strip()
        if not satir or ":" not in satir:
            continue
        anahtar, deger = satir.split(":", 1)
        sonuc[anahtar.strip()] = deger.strip()
    return sonuc


def _donem_kur(alanlar: dict[str, str], etiket: str, onek: str = "") -> Donem:
    def al(ad: str) -> float | None:
        return _sayi(alanlar.get(f"{onek}{ad}", ""))

    hasilat = al("hasilat")
    if hasilat is None:
        raise ValueError(f"{onek or 'cari donem'}: hasilat zorunlu")

    return Donem(
        etiket=etiket,
        hasilat=hasilat,
        brut_kar=al("brut_kar"),
        faaliyet_kari=al("faaliyet_kari"),
        favok=al("favok"),
        net_kar=al("net_kar"),
        aktif_toplami=al("aktif_toplami"),
        ozkaynak=al("ozkaynak"),
        donen_varliklar=al("donen_varliklar"),
        kisa_vadeli_yukumlulukler=al("kisa_vadeli_yukumlulukler"),
        ticari_alacaklar=al("ticari_alacaklar"),
        stoklar=al("stoklar"),
        net_borc=al("net_borc"),
        faaliyet_disi_net=al("faaliyet_disi_net"),
        faaliyet_nakit_akisi=al("faaliyet_nakit_akisi"),
        yatirim_harcamasi=al("yatirim_harcamasi"),
        finansman_gideri=al("finansman_gideri"),
    )


# ---------------------------------------------------------------------------
# Dogrulama
# ---------------------------------------------------------------------------

def _tutarlilik(d: Donem, etiket: str) -> list[Bulgu]:
    """Tek donem icindeki muhasebe ozdesliklerini denetler."""
    b: list[Bulgu] = []

    def var(*x: float | None) -> bool:
        return all(v is not None for v in x)

    if var(d.brut_kar) and d.brut_kar > d.hasilat:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: brut kar hasilattan buyuk -- satir kaymasi olabilir"))

    if var(d.faaliyet_kari, d.brut_kar) and d.faaliyet_kari > d.brut_kar:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: faaliyet kari brut kardan buyuk"))

    if var(d.donen_varliklar, d.aktif_toplami) and d.donen_varliklar > d.aktif_toplami:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: donen varliklar aktif toplamindan buyuk"))

    if var(d.ozkaynak, d.aktif_toplami) and d.ozkaynak > d.aktif_toplami:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: ozkaynak aktif toplamindan buyuk"))

    if var(d.stoklar, d.donen_varliklar) and d.stoklar > d.donen_varliklar:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: stoklar donen varliklardan buyuk"))

    if var(d.ticari_alacaklar, d.donen_varliklar) and d.ticari_alacaklar > d.donen_varliklar:
        b.append(Bulgu(Seviye.HATA, f"{etiket}: ticari alacaklar donen varliklardan buyuk"))

    # FAVOK faaliyet karindan kucuk olmasi beklenmez (amortisman eklenir)
    if var(d.favok, d.faaliyet_kari) and d.favok < d.faaliyet_kari:
        b.append(Bulgu(Seviye.UYARI, f"{etiket}: FAVOK faaliyet karindan kucuk -- alanlar yer degistirmis olabilir"))

    # Net kar hasilattan buyukse ya olaganustu bir kalem var ya da hata
    if var(d.net_kar) and d.net_kar > d.hasilat:
        b.append(Bulgu(Seviye.UYARI, f"{etiket}: net kar hasilattan buyuk -- olaganustu gelir mi, hata mi?"))

    return b


def _buyukluk(simdi: Donem, once: Donem) -> list[Bulgu]:
    """Iki donem arasinda birim hatasi arar.

    Bir donemi bin TL, digerini TL girmek en sinsi hata. Buyukluk orani
    100 kati asiyorsa neredeyse kesin birim karisikligidir -- gercek bir
    sirket bir yilda yuz kat buyumez.
    """
    b: list[Bulgu] = []
    ciftler = (
        ("hasilat", simdi.hasilat, once.hasilat),
        ("aktif toplami", simdi.aktif_toplami, once.aktif_toplami),
        ("ozkaynak", simdi.ozkaynak, once.ozkaynak),
    )
    for ad, y, e in ciftler:
        if y is None or e is None or e <= 0 or y <= 0:
            continue
        oran = max(y / e, e / y)
        if oran > 100:
            b.append(
                Bulgu(
                    Seviye.HATA,
                    f"{ad}: iki donem arasinda {oran:.0f} kat fark -- "
                    "bir donem bin TL, digeri TL girilmis olabilir",
                )
            )
        elif oran > 10:
            b.append(
                Bulgu(Seviye.UYARI, f"{ad}: iki donem arasinda {oran:.1f} kat fark -- kontrol edin")
            )
    return b


def dogrula(simdi: Donem, once: Donem) -> list[Bulgu]:
    return (
        _tutarlilik(simdi, "cari donem")
        + _tutarlilik(once, "onceki donem")
        + _buyukluk(simdi, once)
    )


# ---------------------------------------------------------------------------
# Genel arayuz
# ---------------------------------------------------------------------------

@dataclass
class Girdi:
    kod: str
    sirket: str
    simdi: Donem
    once: Donem
    esas: EnflasyonEsasi
    tufe: float | None
    gecmis_buyumeler: list[float]
    bulgular: list[Bulgu]

    @property
    def gecerli(self) -> bool:
        return not any(b.seviye is Seviye.HATA for b in self.bulgular)


def oku(yol: pathlib.Path) -> Girdi:
    alanlar = _alanlar(yol.read_text(encoding="utf-8-sig"))

    for zorunlu in ("kod", "sirket", "donem", "onceki_donem"):
        if not alanlar.get(zorunlu):
            raise ValueError(f"{yol.name}: '{zorunlu}' alani bos")

    esas_ham = alanlar.get("esas", "tms29").lower()
    if esas_ham not in ("tms29", "nominal"):
        raise ValueError(f"{yol.name}: esas 'tms29' ya da 'nominal' olmali")
    esas = EnflasyonEsasi.TMS29 if esas_ham == "tms29" else EnflasyonEsasi.NOMINAL

    tufe = _sayi(alanlar.get("tufe", ""))
    if esas is EnflasyonEsasi.NOMINAL and tufe is None:
        raise ValueError(f"{yol.name}: nominal esasta 'tufe' zorunlu")
    if esas is EnflasyonEsasi.TMS29 and tufe is not None:
        raise ValueError(
            f"{yol.name}: TMS 29 esasinda tufe verilmez -- enflasyon iki kez dusulur"
        )

    gecmis = _gecmis_buyumeler(alanlar.get("gecmis_buyumeler", ""), yol.name)

    simdi = _donem_kur(alanlar, alanlar["donem"])
    once = _donem_kur(alanlar, alanlar["onceki_donem"], onek="onceki.")

    return Girdi(
        kod=alanlar["kod"].upper(),
        sirket=alanlar["sirket"],
        simdi=simdi,
        once=once,
        esas=esas,
        tufe=tufe,
        gecmis_buyumeler=gecmis,
        bulgular=dogrula(simdi, once),
    )


def sablon_olustur(kod: str, donem: str) -> pathlib.Path:
    """Doldurulacak bos bir veri dosyasi olusturur."""
    VERI.mkdir(exist_ok=True)
    ad = f"{kod.upper()}-{re.sub(r'[^0-9]+', '-', donem).strip('-')}.txt"
    dosya = VERI / ad
    if dosya.exists():
        raise FileExistsError(f"{ad} zaten var")
    dosya.write_text(SABLON, encoding="utf-8")
    return dosya
