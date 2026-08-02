"""Yapistirilan finansal tabloyu ayristirip veri dosyasina cevirir.

NEDEN BOYLE
-----------
Bilanco rakamlari otomatik cekilemiyor: KAP'ta istemci tarafinda yukleniyor
ve o yol kasitli olarak kapali (bkz. hafiza: kap-veri-erisimi). Ucuncu parti
siteleri kazimak ise ticari bir yayin icin kullanim sartlarina aykiri.

Kalan mesru yol: **insan bakar, kopyalar; kod ayristirir.** Bir kisinin
baktigi sayfadan tablo kopyalamasi olagan kullanimdir. Bu modul o
yapistirmayi alip veri dosyasina cevirir -- alan alan yazmaya gore 20-30
kat hizli.

NE ILE CALISIR
--------------
Kaynak farketmez: KAP finansal tablo ekrani, TradingView, Fintables, Excel
ciktisi, sirketin kendi faaliyet raporu. Satirlarda kalem adi ve yaninda
sayilar oldugu surece ayristirir.

TASARIM: SESSIZ YANLIS YERINE GURULTULU EKSIK
---------------------------------------------
Eslesmeyen kalem doldurulmaz, uydurulmaz. Sonunda hangi alanlarin
bulundugu ve hangilerinin bulunamadigi acikca listelenir. Yanlis kalemi
dogru sanmaktansa eksik birakmak yeglenir -- eksik kalem skorda "olculemedi"
olur, yanlis kalem butun analizi bozar.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).parent
VERI = _KOK / "veri"

# ---------------------------------------------------------------------------
# Turkce metin normalizasyonu
# ---------------------------------------------------------------------------

# Kaynaklar Turkce'yi tutarsiz yaziyor: "Brüt Kâr", "Brut Kar", "BRÜT KAR".
# Desen eslestirmeden once her iki taraf da ASCII'ye katlanir. Bu tuzagi
# ifade taramasinda bir kez yasadik; ayni hata burada da yanlis negatif
# uretirdi -- kalem bulunmaz, sessizce eksik kalirdi.
_KATLAMA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
})


def katla(metin: str) -> str:
    """Diakritikleri atar, kucuk harfe cevirir, bosluklari tekler."""
    return re.sub(r"\s+", " ", metin.translate(_KATLAMA).lower()).strip()


# ---------------------------------------------------------------------------
# Sayi cozumleme
# ---------------------------------------------------------------------------

# DIKKAT: karakter sinifina bosluk KONMAZ. Bir kez konmustu ve iki sutunu
# tek sayiya yapistiriyordu -- "4.200.000   3.100.000" tek eslesmede
# "42003100" oluyordu. Hata firlatmiyor, sadece bilancoyu bozuyordu.
_SAYI_DESEN = re.compile(r"\(?-?\d[\d.,]*\)?")


def sayi_coz(ham: str) -> float | None:
    """Metindeki sayiyi cozer. Turkce ve Ingilizce bicimleri destekler.

        '17.360.000.000'  -> 17360000000
        '1.234,56'        -> 1234.56
        '1,234,567'       -> 1234567
        '(1.234)'         -> -1234        parantez = negatif (muhasebe)
        '-1.234'          -> -1234

    Ayirac belirsizliginde kural: hem nokta hem virgul varsa SONUNCUSU
    ondalik ayracidir. Tek tur ayirac varsa ve gruplar ucer haneliyse
    binlik ayracidir.
    """
    if ham is None:
        return None
    s = ham.strip()
    if not s:
        return None

    negatif = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(" ", "").replace(" ", "")
    if s.startswith("-"):
        negatif = True
        s = s[1:]
    if not s or not any(c.isdigit() for c in s):
        return None

    son_nokta, son_virgul = s.rfind("."), s.rfind(",")

    if son_nokta >= 0 and son_virgul >= 0:
        # Ikisi de var: sonuncusu ondalik
        if son_virgul > son_nokta:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif son_virgul >= 0:
        kuyruk = s[son_virgul + 1:]
        # "1,234" ucer haneli grup -> binlik; "1,5" -> ondalik
        s = s.replace(",", "") if len(kuyruk) == 3 and s.count(",") >= 1 and len(s.split(",")[0]) <= 3 else s.replace(",", ".")
        if s.count(".") > 1:  # coklu nokta kaldiysa binliktir
            s = s.replace(".", "")
    elif son_nokta >= 0:
        kuyruk = s[son_nokta + 1:]
        if len(kuyruk) == 3:
            s = s.replace(".", "")  # binlik
        elif s.count(".") > 1:
            s = s.replace(".", "")

    try:
        d = float(s)
    except ValueError:
        return None
    return -d if negatif else d


# ---------------------------------------------------------------------------
# Kalem adi sozlugu
# ---------------------------------------------------------------------------

# Her alan icin kabul edilen adlar. Sira ONEMLI: uzun ve ozgul olanlar
# once gelir, cunku "Ticari Alacaklar" ile "Kisa Vadeli Ticari Alacaklar"
# ayni satirda yarisir ve genel olan yanlis satiri kapabilir.
ADLAR: dict[str, tuple[str, ...]] = {
    "hasilat": (
        "hasilat", "satis gelirleri", "net satislar", "satis geliri",
        "toplam gelirler", "esas faaliyet gelirleri", "revenue",
        "total revenue", "net sales",
    ),
    "brut_kar": (
        "brut kar/zarar", "brut esas faaliyet kari", "brut kar", "brut karlar",
        "gross profit",
    ),
    "faaliyet_kari": (
        "esas faaliyet kari/zarari", "esas faaliyet kari", "faaliyet kari/zarari",
        "faaliyet kari", "operating income", "operating profit",
    ),
    "favok": ("favok", "ebitda", "amortisman oncesi faaliyet kari"),
    "net_kar": (
        "ana ortaklik paylari", "net donem kari/zarari", "net donem kari",
        "donem kari/zarari", "donem net kari", "donem kari", "net kar",
        "net income", "net profit",
    ),
    "faaliyet_disi_net": (
        "faaliyet disi net", "esas faaliyet disi",
    ),
    "aktif_toplami": (
        "toplam varliklar", "aktif toplami", "toplam aktifler", "total assets",
    ),
    "ozkaynak": (
        "ana ortakliga ait ozkaynaklar", "toplam ozkaynaklar", "ozkaynaklar",
        "ozsermaye", "total equity",
    ),
    "donen_varliklar": (
        "toplam donen varliklar", "donen varliklar", "current assets",
    ),
    "kisa_vadeli_yukumlulukler": (
        "toplam kisa vadeli yukumlulukler", "kisa vadeli yukumlulukler",
        "current liabilities",
    ),
    "ticari_alacaklar": (
        "kisa vadeli ticari alacaklar", "ticari alacaklar", "accounts receivable",
    ),
    "stoklar": ("stoklar", "inventory", "inventories"),
    "faaliyet_nakit_akisi": (
        "isletme faaliyetlerinden nakit akislari",
        "esas faaliyetlerden nakit akislari",
        "isletme faaliyetlerinden saglanan nakit",
        "operating cash flow", "cash from operations",
    ),
    "yatirim_harcamasi": (
        "maddi duran varlik alimlari", "yatirim harcamalari",
        "capital expenditures", "capex",
    ),
    "finansman_gideri": (
        "finansman giderleri", "finansman gideri", "finansman gelir gideri",
    ),
    "net_borc": ("net borc", "net finansal borc", "net debt"),
    # Net borc yoksa bilesenlerden hesaplanir
    "_finansal_borc": (
        "toplam finansal borclar", "finansal borclar", "toplam borclanmalar",
        "borclanmalar", "total debt",
    ),
    "_nakit": (
        "nakit ve nakit benzerleri", "nakit ve nakit benzeri",
        "cash and equivalents", "cash",
    ),
}

#: Olcek ipuclari -- KAP tablolari cogunlukla bin TL
OLCEKLER = {
    "bin": 1_000,
    "bin tl": 1_000,
    "bin turk lirasi": 1_000,
    "milyon": 1_000_000,
    "milyon tl": 1_000_000,
    "milyar": 1_000_000_000,
    "tam": 1,
    "tl": 1,
}


def olcek_sez(metin: str) -> tuple[int, str]:
    """Tablonun basligindan olcegi sezer.

    Yanlis olcek en tehlikeli hatalardan biri: butun rakamlar 1000 kat
    sapar ama oranlar DOGRU cikar, cunku pay ve payda ayni sapar. Yani
    hata skorda gorunmez, yalnizca mutlak rakamlarda gorunur. Bu yuzden
    sezilen olcek her zaman ekrana yazilir ve onaylanmasi istenir.
    """
    k = katla(metin[:2000])
    if re.search(r"\bbin\s*(tl|turk lirasi)\b", k) or re.search(r"\(bin\b", k):
        return 1_000, "bin TL (başlıktan sezildi)"
    if re.search(r"\bmilyon\s*(tl)?\b", k):
        return 1_000_000, "milyon TL (başlıktan sezildi)"
    return 1, "tam TL (ölçek ipucu bulunamadı — varsayılan)"


# ---------------------------------------------------------------------------
# Ayristirma
# ---------------------------------------------------------------------------

# Deger olmayan ama sayi iceren parcalar. Bunlar sayi cikarmadan ONCE
# temizlenir. Onceki surum "1900-2100 arasi tamsayilari at" diyordu; o kural
# bin TL olcekli bir tabloda "Stoklar 2.024" gibi MESRU bir degeri de
# silerdi. Deseni temizlemek, degeri elemekten guvenli.
_DEGER_OLMAYAN = re.compile(
    r"\b\d{4}\s*/\s*\d{1,2}\b"          # 2026/06
    r"|\b\d{1,2}[./]\d{1,2}[./]\d{4}\b"  # 31.12.2025
    r"|\b\d{4}-\d{2}-\d{2}\b"            # 2026-06-30
    r"|\(\s*(?:not|dipnot)\s*[:.]?\s*\d+[^)]*\)",  # (Not 12)
    re.IGNORECASE,
)


def _satir_sayilari(satir: str) -> list[float]:
    """Satirdaki deger sayilarini sirayla dondurur."""
    temiz = _DEGER_OLMAYAN.sub(" ", satir)
    # "( 1.234 )" -> "(1.234)"  parantez icindeki bosluk desenle celisiyor
    temiz = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", temiz))
    degerler = []
    for m in _SAYI_DESEN.finditer(temiz):
        d = sayi_coz(m.group(0))
        if d is not None:
            degerler.append(d)
    return degerler


def _kalem_ara(satir_katli: str) -> str | None:
    """Satirin hangi alana ait oldugunu bulur.

    En UZUN eslesme kazanir: "kisa vadeli ticari alacaklar" varsa onu
    "ticari alacaklar"a tercih eder.
    """
    en_iyi, en_uzun = None, 0
    for alan, adlar in ADLAR.items():
        for ad in adlar:
            if ad in satir_katli and len(ad) > en_uzun:
                en_iyi, en_uzun = alan, len(ad)
    return en_iyi


def ayristir(metin: str, olcek: int) -> tuple[dict[str, float], dict[str, float], list[str]]:
    """Yapistirilan metni (simdi, onceki, notlar) olarak coz.

    Her satirda ilk sayi CARI donem, ikincisi ONCEKI donem kabul edilir --
    finansal tablolarin evrensel duzeni budur. Tek sayi varsa yalnizca cari
    doneme yazilir.
    """
    simdi: dict[str, float] = {}
    once: dict[str, float] = {}
    notlar: list[str] = []

    for ham in metin.splitlines():
        satir = ham.strip()
        if not satir:
            continue
        katli = katla(satir)
        alan = _kalem_ara(katli)
        if alan is None:
            continue

        sayilar = _satir_sayilari(satir)
        # Kalem adinin icindeki yil/dipnot numaralarini ayikla: cok kucuk
        # tamsayilar (2024, 2026 gibi) deger degil basliktir
        sayilar = [d for d in sayilar if not (1900 <= d <= 2100 and d == int(d))]
        if not sayilar:
            continue

        if alan in simdi:
            notlar.append(f"{alan}: birden fazla satir eslesti, ilki korundu")
            continue

        simdi[alan] = sayilar[0] * olcek
        if len(sayilar) >= 2:
            once[alan] = sayilar[1] * olcek

    # Net borc verilmemisse bilesenlerden hesapla
    for hedef, kaynak in ((simdi, simdi), (once, once)):
        if "net_borc" not in hedef and "_finansal_borc" in kaynak:
            nakit = kaynak.get("_nakit", 0.0)
            hedef["net_borc"] = kaynak["_finansal_borc"] - nakit
            if kaynak is simdi:
                notlar.append(
                    "net_borc verilmedi, finansal borç − nakit olarak hesaplandı"
                )

    for d in (simdi, once):
        d.pop("_finansal_borc", None)
        d.pop("_nakit", None)

    return simdi, once, notlar


# ---------------------------------------------------------------------------
# Veri dosyasi yazimi
# ---------------------------------------------------------------------------

SIRA = (
    "hasilat", "brut_kar", "faaliyet_kari", "favok", "net_kar",
    "faaliyet_disi_net", "aktif_toplami", "ozkaynak", "donen_varliklar",
    "kisa_vadeli_yukumlulukler", "ticari_alacaklar", "stoklar", "net_borc",
    "faaliyet_nakit_akisi", "yatirim_harcamasi", "finansman_gideri",
)


def _bicimle(d: float) -> str:
    """Tam sayi ise binlik noktali, degilse ondalikli yaz."""
    if abs(d - round(d)) < 0.01:
        return f"{int(round(d)):,}".replace(",", ".")
    return f"{d:,.2f}".replace(",", "|").replace(".", ",").replace("|", ".")


def veri_dosyasi(
    kod: str, sirket: str, donem: str, onceki_donem: str,
    simdi: dict, once: dict, esas: str = "tms29",
) -> str:
    satirlar = [
        f"kod: {kod}",
        f"sirket: {sirket}",
        f"donem: {donem}",
        f"onceki_donem: {onceki_donem}",
        f"esas: {esas}",
    ]
    for alan in SIRA:
        if alan in simdi:
            satirlar.append(f"{alan}: {_bicimle(simdi[alan])}")
    for alan in SIRA:
        if alan in once:
            satirlar.append(f"onceki.{alan}: {_bicimle(once[alan])}")
    return "\n".join(satirlar) + "\n"


# ---------------------------------------------------------------------------
# Komut satiri
# ---------------------------------------------------------------------------

def main() -> int:
    a = argparse.ArgumentParser(
        description="Yapistirilan finansal tabloyu veri dosyasina cevirir",
    )
    a.add_argument("--kod", required=True, help="Hisse kodu, ornek: TERA")
    a.add_argument("--sirket", default="", help="Tam unvan")
    a.add_argument("--donem", required=True, help="ornek: 2026/06")
    a.add_argument("--onceki", default="", help="ornek: 2025/06")
    a.add_argument("--kaynak", required=True, help="Yapistirilan metin dosyasi")
    a.add_argument("--olcek", choices=sorted(OLCEKLER), default=None,
                   help="bin / milyon / tam -- verilmezse basliktan sezilir")
    a.add_argument("--esas", choices=("tms29", "nominal"), default="tms29")
    args = a.parse_args()

    yol = pathlib.Path(args.kaynak)
    if not yol.exists():
        print(f"Kaynak dosya yok: {yol}")
        return 1
    metin = yol.read_text(encoding="utf-8-sig")

    if args.olcek:
        olcek, aciklama = OLCEKLER[args.olcek], f"{args.olcek} (elle verildi)"
    else:
        olcek, aciklama = olcek_sez(metin)

    simdi, once, notlar = ayristir(metin, olcek)

    print("=" * 66)
    print(f"{args.kod}  {args.donem}")
    print("=" * 66)
    print(f"ölçek: {aciklama}")
    print(f"  -> okunan her rakam {olcek:,} ile çarpıldı".replace(",", "."))
    print()

    bulunan = [alan for alan in SIRA if alan in simdi]
    eksik = [alan for alan in SIRA if alan not in simdi]

    print(f"BULUNAN ({len(bulunan)})")
    for alan in bulunan:
        onc = f"   önceki: {_bicimle(once[alan])}" if alan in once else "   önceki: —"
        print(f"  {alan:<28} {_bicimle(simdi[alan]):>22}{onc}")

    if eksik:
        print(f"\nBULUNAMAYAN ({len(eksik)})  -- uydurulmadi, bos birakildi")
        for alan in eksik:
            print(f"  {alan}")

    for n in notlar:
        print(f"\nNOT: {n}")

    if not bulunan:
        print("\nHicbir kalem eslesmedi. Yapistirilan metin tablo mu?")
        return 1

    onceki_donem = args.onceki or "ONCEKI-DONEM-YAZ"
    icerik = veri_dosyasi(
        args.kod, args.sirket or args.kod, args.donem, onceki_donem,
        simdi, once, args.esas,
    )
    VERI.mkdir(exist_ok=True)
    hedef = VERI / f"{args.kod}-{args.donem.replace('/', '-')}.txt"
    hedef.write_text(icerik, encoding="utf-8")

    print(f"\nyazildi: {hedef.relative_to(_KOK)}")
    print("\nSIRADAKI ADIM")
    print(f"  1. {hedef.name} dosyasini ac, rakamlari KAP tablosuyla KARSILASTIR")
    print("  2. python uret_ucretsiz.py veri/" + hedef.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
