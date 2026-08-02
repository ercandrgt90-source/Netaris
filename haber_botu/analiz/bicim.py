"""Turkce sayi, yuzde ve unvan bicimlendirme.

Neden ayri bir modul: bu kurallarin hepsi Turkce'ye ozgu ve hepsi sessizce
yanlis sonuc uretebiliyor. Tek yerde toplanip test edilmeleri, her cagri
yerinde yeniden hatirlanmalarindan guvenli.

KURALLAR
--------
1. **Yuzde isareti sayinin ONUNDE.** Turkce'de "%40" dogru, "40%" degil.
   Isaretli degisimlerde isaret en basa gelir: "+%40,0", "-%5,2".
2. **Ondalik ayraci virgul.** "2,84x", "-3,0 puan".
3. **Buyuk harf cevrimi Turkce'ye gore.** Python'un `.upper()` metodu "i"
   harfini "I" yapar; Turkce'de "İ" olmasi gerekir. `str.lower()` de "I"yi
   "i" yapar, "ı" olmasi gerekirken.
4. **Ek uyumundan kacinilir.** "Turk Hava Yollari" gibi iyelik ekiyle biten
   unvanlara bulunma eki getirmek tampon "n" gerektirir ("Yollari'nda"),
   ve bunu unvandan guvenilir sekilde cikaramayiz. Bu yuzden basliklarda
   ek yerine iki nokta kullanilir -- her zaman dilbilgisel olarak dogru.
"""

from __future__ import annotations

# Turkce'ye ozgu harf esleri
_BUYUK = str.maketrans({"i": "İ", "ı": "I"})
_KUCUK = str.maketrans({"I": "ı", "İ": "i"})

# Unvanin sonundaki hukuki bicim ve genel tanimlayici sozcukler.
# Bunlar sirketin gunluk anilan adinin parcasi degildir.
_HUKUKI = {
    "a.s.", "a.ş.", "a.o.", "t.a.s.", "t.a.ş.", "anonim", "sirketi", "şirketi",
    "ortakligi", "ortaklığı", "as", "aş",
}
_TANIMLAYICI = {
    "sanayi", "sanayii", "ticaret", "tic.", "san.", "fabrikalari", "fabrikaları",
    "isletmeleri", "işletmeleri", "muessesesi", "müessesesi", "kurumu",
    "endustri", "endüstri", "pazarlama", "uretim", "üretim", "grubu",
    # Araci kurum unvanlarinin sonundaki genel tanimlayicilar:
    # "TERA YATIRIM MENKUL DEGERLER A.S." -> "Tera Yatirim"
    "menkul", "degerler", "değerler", "aracilik", "aracılık",
}
_BAGLAC = {"ve", "ile"}


def buyuk(metin: str) -> str:
    """Turkce buyuk harf. 'istanbul' -> 'İSTANBUL'."""
    return metin.translate(_BUYUK).upper()


def kucuk(metin: str) -> str:
    """Turkce kucuk harf. 'IZMIR' -> 'ızmır' degil 'izmir'."""
    return metin.translate(_KUCUK).lower()


def bas_harf(metin: str) -> str:
    """Ilk harfi Turkce kurallarina gore buyutur, gerisine dokunmaz."""
    if not metin:
        return metin
    return buyuk(metin[0]) + metin[1:]


def sayi(d: float | None, basamak: int = 1, isaretli: bool = False) -> str:
    """Ondalik ayraci virgul olan sayi."""
    if d is None:
        return "—"
    bicim = f"{d:+.{basamak}f}" if isaretli else f"{d:.{basamak}f}"
    return bicim.replace(".", ",")


def yuzde(d: float | None, isaretli: bool = False, basamak: int = 1) -> str:
    """Turkce yuzde: isaret, sonra %, sonra sayi.

    yuzde(40.0)                -> '%40,0'
    yuzde(40.0, isaretli=True) -> '+%40,0'
    yuzde(-5.2, isaretli=True) -> '-%5,2'
    yuzde(4.68, basamak=2)     -> '%4,68'

    `basamak` faiz ve tahvil getirilerinde 2 olmalidir: %4,68 ile %4,7
    arasindaki fark tahvil piyasasinda 2 baz puandir ve anlamlidir.
    """
    if d is None:
        return "—"
    if not isaretli:
        return "%" + sayi(abs(d) if d == 0 else d, basamak)
    isaret = "+" if d >= 0 else "-"
    return f"{isaret}%{sayi(abs(d), basamak)}"


def kat(d: float | None) -> str:
    """Carpan: '2,84x'."""
    return "—" if d is None else sayi(d, 2) + "x"


def puan(d: float | None) -> str:
    """Yuzde puani cinsinden degisim: '-3,0 puan'."""
    return "—" if d is None else sayi(d, 1, isaretli=True) + " puan"


_AYLAR = (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)


def tarih(iso: str) -> str:
    """ISO tarihi Turkce okunusa cevirir: '2026-07-27' -> '27 Temmuz 2026'.

    Cozumlenemezse girdi aynen dondurulur -- okura ISO tarih gostermek,
    yanlis bir tarih gostermekten iyidir.
    """
    parcalar = iso.strip().split("-")
    if len(parcalar) != 3:
        return iso
    try:
        yil, ay, gun = int(parcalar[0]), int(parcalar[1]), int(parcalar[2])
    except ValueError:
        return iso
    if not 1 <= ay <= 12:
        return iso
    return f"{gun} {_AYLAR[ay - 1]} {yil}"


def unvan_duzelt(unvan: str) -> str:
    """KAP'tan gelen TAMAMEN BUYUK unvani cumle icine uygun hale getirir.

    'TERA YATIRIM MENKUL DEGERLER A.S.' -> 'TERA Yatırım Menkul Değerler A.Ş.'

    Dort harf ve kisasi (TERA, THY) ile noktali kisaltmalar (A.Ş., T.A.Ş.)
    oldugu gibi kalir -- onlar zaten buyuk yazilir.
    """
    parcalar = []
    for s in unvan.split():
        if s.isupper() and len(s) > 4 and "." not in s:
            parcalar.append(bas_harf(kucuk(s)))
        else:
            parcalar.append(s)
    return " ".join(parcalar)


def kisa_ad(unvan: str) -> str:
    """Resmi unvandan gunluk kullanilan kisa adi cikarir.

    'Ornek Cimento Sanayi A.S.'          -> 'Ornek Cimento'
    'Turk Hava Yollari A.O.'             -> 'Turk Hava Yollari'
    'Eregli Demir ve Celik Fabrikalari'  -> 'Eregli Demir'

    Amac dogru kisaltma degil, YANLIS kisaltma uretmemek: sondan hukuki ve
    tanimlayici sozcukler atilir, kalan en fazla uc sozcuge indirilir ve
    baglacla bitmesine izin verilmez.
    """
    sozcukler = unvan.split()
    while sozcukler and kucuk(sozcukler[-1].rstrip(",")) in _HUKUKI | _TANIMLAYICI:
        sozcukler.pop()

    sozcukler = sozcukler[:3]
    while sozcukler and kucuk(sozcukler[-1]) in _BAGLAC:
        sozcukler.pop()

    if not sozcukler:
        return unvan

    # KAP unvanlari TAMAMEN BUYUK HARFLE gelir ("TERA YATIRIM MENKUL...").
    # Baslikta oldugu gibi birakmak bagirma etkisi yapar. Kisaltmalar
    # (A.O., THY gibi 4 harfe kadar tumu buyuk parcalar) korunur.
    duzeltilmis = []
    for s in sozcukler:
        if s.isupper() and len(s) > 4 and "." not in s:
            duzeltilmis.append(bas_harf(kucuk(s)))
        else:
            duzeltilmis.append(s)
    return " ".join(duzeltilmis)
