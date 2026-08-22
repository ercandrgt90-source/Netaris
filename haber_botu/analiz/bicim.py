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

import re

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
    """Ondalik ayraci virgul olan sayi.

    NEGATIF SIFIR BASILMIYOR.
    Olculdu: 13 sayfada "-0,00 milyar TL" yaziyordu. Deger gercekten
    negatifti (orn. -0,004 milyar) ama iki basamaga yuvarlanınca sifir
    oldu ve geriye yalnizca isaret kaldi.

    Okur icin "eksi sifir" diye bir buyukluk yok; gordugu sey ya bir
    yazim hatasi ya da anlamadigi bir gosterim. Isaret, yuvarlamadan
    SONRA hala bir buyukluk kaliyorsa anlamli.

    Deger buyuklugunu KAYBETMIYORUZ -- zaten yuvarlama onu kaybetti;
    biz yalnizca yaniltici isareti kaldiriyoruz. Daha fazla hassasiyet
    gerekiyorsa cagiran taraf `basamak` vermeli.
    """
    if d is None:
        return "—"
    # YUVARLANMIS DEGER SIFIRSA ISARET DUSUYOR -- artida da ekside de.
    #
    # "+0,00" da "-0,00" kadar yanlis: ikisi de bir yon iddia ediyor
    # ama gosterdikleri buyukluk sifir. Degisim yoksa isaret de yok.
    if round(d, basamak) == 0:
        return f"{0.0:.{basamak}f}".replace(".", ",")
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
    # SIFIR DEGISIMDE ISARET YOK.
    #
    # `sayi()` icinde ayni kural var ama `yuzde` isareti KENDI kuruyor
    # ve o yuzden oradan yararlanmiyordu: "-%0,00" ve "+%0,0" cikiyordu.
    # Ikisi de bir yon iddia ediyor ama gosterdikleri buyukluk sifir.
    #
    # Iki islevde ayni kurali iki kez yazmak yerine `sayi()`nin
    # ciktisina bakiliyor: sifir dondurduyse isaret basilmiyor.
    govde = sayi(abs(d), basamak)
    if float(govde.replace(",", ".")) == 0:
        return f"%{govde}"
    isaret = "+" if d >= 0 else "-"
    return f"{isaret}%{govde}"


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


#: Buyuk harf kalmasi gereken kisaltmalar. Liste kapali degil; asagidaki
#: kural "uc harfe kadar tamamen buyuk yazilmis sozcuk kisaltmadir"
#: varsayimini kullaniyor, bunlar ise daha uzun olduklari icin ayrica
#: yaziliyor.
KISALTMALAR = frozenset({
    "TCMB", "BDDK", "SPK", "TUIK", "TÜİK", "BIST", "BİST", "KAP", "TOKI",
    "TOKİ", "OPEC", "OPEC+", "FOMC", "ECB", "IMF", "OECD", "NATO", "USD",
    "EUR", "TRY", "TL", "BTC", "ETH", "GSYH", "TUFE", "TÜFE", "UFE", "ÜFE",
    "PPK", "SGK", "KDV", "OTV", "ÖTV", "ABD", "AB",
})

#: Ard arda kac bagiran sozcuk gorulurse baslik bagiriyor sayilir.
#: Ikiden basliyor: "BENZINE NE KADAR" iki sozcukte belli oluyor.
BAGIRAN_DIZI = 2


def _cekirdek(sozcuk: str) -> str:
    return sozcuk.strip(".,;:!?()[]\"'“”")


def _tamami_buyuk(sozcuk: str) -> bool:
    """Sozcugun butun harfleri buyuk mu (rakam ve noktalama sayilmaz)."""
    harf = [c for c in _cekirdek(sozcuk) if c.isalpha()]
    return bool(harf) and all(c.isupper() for c in harf)


#: Bu uzunluga kadar tamamen buyuk yazilmis sozcuk KISALTMA sayilir.
#: `unvan_duzelt` ve `kisa_ad` ayni esigi kullaniyor -- ayni dosyada iki
#: farkli "kisaltma nedir" tanimi olmasin.
KISALTMA_UZUNLUGU = 4


def _bagiran_sozcuk(sozcuk: str) -> bool:
    """Tek sozcuk bagiriyor mu -- kisaltma degil, uzun ve tamamen buyuk.

    ESIK 3'TEN 4'E CIKTI. Uc harf esigiyle "Garanti BBVA, GMTN
    programinda..." basligi BAGIRIYOR sayildi ve "Garanti Bbva, Gmtn"
    diye bozuldu: dort harfli iki kisaltma yan yana gelince ardisik
    bagirma dizisi olusuyor. Kurum adini bozmak, bagiran basligi
    duzeltmemekten kotudur.
    """
    c = _cekirdek(sozcuk)
    if (len(c) <= KISALTMA_UZUNLUGU or c in KISALTMALAR
            or any(x.isdigit() for x in c)):
        return False
    return _tamami_buyuk(sozcuk)


def _notr(sozcuk: str) -> bool:
    """Diziyi kirmayan sozcuk: kisaltma boyunda ya da harfsiz.

    "BENZINE NE KADAR, KAC TL ZAM GELECEK?" dizisinde "NE", "KAC", "TL"
    ve "ZAM" kisa. Bunlari dizi kirici saymak, bagiran basligin hicbir
    yerinde iki ardisik bagiran sozcuk BULUNAMAMASINA yol aciyordu --
    kural hic tetiklenmiyordu.
    """
    c = _cekirdek(sozcuk)
    return len(c) <= KISALTMA_UZUNLUGU or not any(x.isalpha() for x in c)


def bagiriyor(baslik: str) -> bool:
    """Baslikta bagiran bir BOLUM var mi?

    Oran butun basliga bakiyordu ve ise yaramadi: gercek basliklar
    yalnizca BASINDA bagiriyor -- "BENZINE NE KADAR, KAC TL ZAM GELECEK?
    Guncel akaryakit fiyatlarinda son durum". Basligin yarisi normal
    yazildigi icin oran esigin altinda kaliyor ve hicbir sey olmuyordu.

    Olcut artik ard arda gelen bagiran sozcuk sayisi.
    """
    ardisik = 0
    for sozcuk in baslik.split():
        if _notr(sozcuk):
            continue                      # diziyi kirmiyor, saymiyor da
        ardisik = ardisik + 1 if _bagiran_sozcuk(sozcuk) else 0
        if ardisik >= BAGIRAN_DIZI:
            return True
    return False


def baslik_sadelestir(baslik: str) -> str:
    """Bagiran bolumleri normal yaziya cevirir, unlemi noktaya donusturur.

    NEDEN: kaynaklarin bir kismi tiklama icin yazilmis basliklar
    veriyor -- "BENZINE NE KADAR, KAC TL ZAM GELECEK?", "Altin
    yatirimcisina nefes aldiran aciklama!". Olculdu: 313 basligin
    17'sinde unlem var.

    Bu bir arastirma platformu; baslik bagirmaz. Ceviri zaten kendi
    basligimizi uretiyor, `baslik_kaynak` ayrica saklaniyor ve kaynak
    baglantisi her sayfada duruyor -- kaynagin ne dedigi gizlenmiyor,
    biz kendi uslubumuzla yaziyoruz.

    KISALTMALAR KORUNUYOR: "TCMB" kucultulurse kurum adi bozulur.
    """
    if not baslik:
        return baslik
    metin = baslik
    if bagiriyor(metin):
        # BASLIK BICIMINE cevriliyor, cumle bicimine DEGIL.
        #
        # Cumle bicimi ("hepsi kucuk, yalnizca ilk harf buyuk") ozel
        # adlari bozar: "TURKIYE" -> "turkiye". Baslik bicimi hicbir
        # sozcugun ilk harfini kucultmedigi icin bu riski tasimiyor.
        #
        # Kisa sozcukler de cevriliyor ("MI" -> "Mı"); yoksa bagiran
        # basligin icinde buyuk harfli adaciklar kaliyordu.
        metin = " ".join(
            s if _cekirdek(s) in KISALTMALAR or not _tamami_buyuk(s)
            else bas_harf(kucuk(s))
            for s in metin.split(" "))
    # UNLEM NOKTAYA DONUYOR, SILINMIYOR.
    #
    # Ilk yazimda siliyordum ve "...aciklama! Dev banka..." cumlesi
    # "...aciklama Dev banka..." haline geldi -- iki cumle birbirine
    # yapisti. Unlem burada ayni zamanda AYRAC.
    metin = re.sub(r"!+(\s+)", r".\1", metin)
    metin = metin.replace("!", "")
    return " ".join(metin.split()).strip(" .,;:")


#: Manset icin ust sinir. Asan baslik bozuk degil ama MANSET degil --
#: kartlari tasiriyor, arama sonucunda kirpiliyor.
MANSET_SINIRI = 110

#: Basligin sonuna yapisan kaynak atfi.
#:
#: " - Truth Social", " - IRIB News", ": devlet medyasi" gibi. Bu bilgi
#: KAYBOLMUYOR: kaynak kurum her sayfada rozet olarak ve "Haber
#: kaynagi:" satirinda ayrica duruyor.
#:
#: Kalip DAR: ayrac bosluklu tire ya da iki nokta, ardindan en fazla
#: dort sozcuk ve cumle sonu. "Trump: Iran ..." gibi bir ONEK asla
#: eslesmiyor cunku kalip yalnizca dizgenin SONUNA bakiyor.
_ATIF_KUYRUGU = re.compile(
    r"\s+[-–—]\s+[^-–—.]{3,40}$|:\s*[a-zçğıöşü][^:.]{2,30}$")


def manset_kisalt(baslik: str, sinir: int = MANSET_SINIRI) -> str:
    """Cok uzun basligi ANLAMINI BOZMADAN kisaltir.

    NEDEN. Olculdu: yayimlanan 31 basligin uzunlugu 110 karakteri
    asiyordu, en uzunu 231. Bunlar manset degil, tel-ajans uyarisinin
    cumlesinin tamami: "BOJ Ozeti: Bir uye, ... incelemesi gerektigini
    soyledi".

    NE YAPMIYOR: CUMLEYI ORTADAN KESMIYOR.
    ---------------------------------------
    Turkcede yuklem ve OLUMSUZLUK sonda. "gerektigini soyledi" ile
    "gerekmedigini soyledi" yalnizca son ekte ayriliyor; ortadan
    kesilen bir Turkce cumle anlamsizlasmakla kalmaz, TERSINE
    donebilir. Bu yuzden burada karakter sayarak kirpma YOK.

    NE YAPIYOR, ikisi de anlami koruyan islem:

      1. Sondaki kaynak atfini atar. Kaynak zaten rozette ve "Haber
         kaynagi:" satirinda yaziyor -- bilgi yer degistiriyor,
         kaybolmuyor.
      2. Birden fazla TAM cumle varsa ilkini alir. Tam cumle kendi
         basina dogru kalir; gerisi sayfanin govdesinde aynen
         duruyor (olculdu: baslik metni govdede bire bir tekrar
         ediyor).

    Sinirin altina inmiyorsa baslik OLDUGU GIBI birakilir. Uzun bir
    baslik kusurludur; yanlis bir baslik kabul edilemez.
    """
    if not baslik or len(baslik) <= sinir:
        return baslik

    metin = baslik.strip()

    kuyruksuz = _ATIF_KUYRUGU.sub("", metin).strip(" .,;:-–—")
    if len(kuyruksuz) >= 40:
        metin = kuyruksuz
    if len(metin) <= sinir:
        return metin

    # Cumle sonu: nokta + bosluk + BUYUK harf. Kisaltma noktalari
    # ("A.B.D.") ve ondalik ayraclar bu kalibi tutturmuyor.
    parcalar = re.split(r"(?<=[.?])\s+(?=[A-ZÇĞİÖŞÜ])", metin)
    if len(parcalar) > 1 and len(parcalar[0]) >= 50:
        ilk = parcalar[0].strip().rstrip(".")
        if len(ilk) < len(metin):
            return ilk
    return metin
