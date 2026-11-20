"""Kumulatif (2026/6) bilanco sayfalarini ceyrekligi VARSA kaldirir.

NEDEN
-----
KAP donemleri KUMULATIF: "2026/6" yilin ilk YARISI demek, ikinci
ceyrek degil. Sayfalar bir donem bu etiketle uretildi ve okur
"2026/6 bilanco analizi" basligini gorup ikinci ceyregi sandi.

Uretim ceyreklige cevrildi; bu arac ESKI kumulatif sayfalari
topluyor.

NEDEN HEPSI DEGIL
-----------------
Olculdu (2026-08-21): 144 kumulatif sayfa var ama yalnizca 33'unun
ceyreklik karsiligi uretilmis. Kalan 111 sirket icin ceyreklik sayfa
HENUZ YOK.

Hepsini silmek, 111 sirketi sayfasiz birakirdi -- yani bir bicim
sorununu icerik kaybina cevirmek. Arac yalnizca KARSILIGI OLANI
siliyor; kalanlar sonraki uretim kosularinda degisiyor ve o zaman
tekrar calistirilabiliyor.

Kosu basina ~60 sayfa uretiliyor, yani 111 sirket icin iki kosu daha
gerekiyor.
"""

from __future__ import annotations

import argparse
import pathlib
import re

KOK = pathlib.Path(__file__).resolve().parent.parent
ANALIZ = KOK / "site" / "icerik" / "analizler"

#: Sirket defteri -- "bu kod hic uretilebilir mi" sorusunun cevabi.
DEFTER = KOK / "haber_botu" / "kaynak" / "sirketler.json"


def uretilebilir_kodlar(defter: pathlib.Path | None = None) -> set[str]:
    """Bilanco hattinin ULASABILDIGI sirket kodlari.

    `uret_bilanco.py --hepsi` sektor listesini `sektor_tr` alanindan
    kuruyor ve sirketleri sektor sektor geziyor. Bu alani OLMAYAN bir
    sirket hicbir sektore dusmuyor, yani hattin gorus alaninda hic
    yok.

    Olculdu (2026-09-15): defterdeki 794 sirketin 441'inde `sektor_tr`
    yok. Cogu icin bu dogru ve kasitli -- fon, varant, yatirim
    ortakligi. Ama arada KUMULATIF SAYFASI OLAN biri varsa, o sayfanin
    ceyrekligi HICBIR ZAMAN uretilmeyecek demektir.

    Dosya okunamazsa BOS KUME degil, `None` gibi davranmak gerekirdi;
    burada bos kume donmek "hicbiri uretilemez" demek olurdu ve butun
    bekleyenleri oksuz gosterirdi. Bu yuzden okunamama hali
    `cagiranda` ele aliniyor: bkz. `main`.
    """
    import json                                        # noqa: PLC0415
    d = json.loads((defter or DEFTER).read_text(encoding="utf-8"))
    return {k.upper() for k, v in d["sirketler"].items()
            if v.get("sektor_tr")}


def bekleyen_ve_oksuz(kalan, uretilebilir) -> tuple[list, list]:
    """Karsiligi olmayanlari ikiye ayirir: kosu COZER / COZMEZ.

    NEDEN AYRI ISLEV
    ----------------
    Ilk yazimda ayni ayrim IKI YERDE duruyordu -- burada ve
    `denetim.py`de. Bu depoda en sik tekrarlayan kusur sinifi tam bu:
    ayni karari veren iki kod yolu, birinin degisip otekinin
    degismemesi demek. Ayrim tek yerde yasiyor, iki cagiran da onu
    cagiriyor.

    `uretilebilir` None ise AYRIM YAPILMIYOR: defter okunamadiginda
    "bilmiyorum" ile "uretilemez" ayni sey degil, ve birini oteki
    sanmak dogru calisan bir sirketi "oksuz" diye damgalardi.
    """
    if uretilebilir is None:
        return list(kalan), []
    bekleyen = [k for k in kalan if k.upper() in uretilebilir]
    oksuz = [k for k in kalan if k.upper() not in uretilebilir]
    return bekleyen, oksuz


#: Kaldirilacak donem etiketi. Kumulatif bicim: "YYYY/A" (A = ay).
KUMULATIF = re.compile(r"^\d{4}/\d{1,2}$")

#: Bilanco sayfasini tanitan etiket. Uretim bu degeri koyuyor.
KATEGORI = "Bilanço Analizi"


def _alan(metin: str, ad: str) -> str:
    m = re.search(rf"^{ad}:\s*(.+)$", metin, re.M)
    return m.group(1).strip() if m else ""


def tara() -> tuple[dict[str, list], dict[str, list]]:
    """Bilanco sayfalarini kumulatif / ceyreklik diye ayirir."""
    kum: dict[str, list] = {}
    cey: dict[str, list] = {}
    for p in ANALIZ.rglob("*.md"):
        t = p.read_text(encoding="utf-8", errors="replace")
        # OLCUT SAYFANIN KENDI ETIKETI -- kelime avi DEGIL.
        #
        # Once "ilk 900 karakterde 'bilanço' geciyor mu" diye
        # bakiliyordu. Olculdu (2026-08-28): bu olcut 241 sayfa
        # buluyor, dogrusu 240. Fazladan sayilan sayfa su:
        #
        #   "Hürmüz Boğazı'nda savaşın bilançosu: 68 olay, 20 can
        #    kaybı"   kategori: Makro   kod: OLAY
        #
        # Yani bir savas haberi, basliginda "bilanço" gectigi icin
        # bilanco analizi sayildi. Bu depoda tekrar eden bir hata
        # sinifi: parcali eslesme (bilanço - bilançosu).
        #
        # BUGUN ZARARSIZ, YARIN DEGIL. O sayfanin `kod`u OLAY ve
        # `donem`i tarih bicimli; ceyreklik kovaya dusuyor ama hicbir
        # sirketle eslesmiyor. Ayni sey `kod`u BIST kodu olan bir
        # haberde olsaydi, arac o sirketin GERCEK kumulatif bilanco
        # sayfasini -- yerine ceyreklik URETILMEDEN -- silecekti.
        #
        # Yeni olcut, uretimin kendi koydugu etiket. Olculdu: 240
        # sayfanin 240'ini buluyor, yanlis pozitifi yok.
        #
        # KATI OLMASI BILEREK: etiketi olmayan bir sayfa hesap disi
        # kalir ve kumulatif karsiligi SILINMEZ. Yanlis tarafa
        # dusmek gerekiyorsa, silmemek tarafina dusmeli.
        if _alan(t, "kategori") != KATEGORI:
            continue
        kod, donem = _alan(t, "kod"), _alan(t, "donem")
        if not kod or not donem:
            continue
        hedef = kum if KUMULATIF.match(donem) else cey
        hedef.setdefault(kod, []).append(p)
    return kum, cey


#: "Son dort donem" tablosunun basligi -- BAGIMSIZ TANIK.
SERI_BASLIK = "## Son dört dönem"

#: Akis/stok orani bu degerin USTUNDEYSE sayfa tek ceyreklik DEGIL.
#:
#: NEDEN ORAN DEGIL ORANIN ORANI -- OLCULDU (2026-11-20).
#:
#: Sayfanin hasilatini baska bir sayfanin serisiyle duz
#: karsilastirmak ISE YARAMIYOR: TMS 29 enflasyon duzeltmesi eski
#: sayfayi bugune gore ~%10 dusuk gosteriyor, kumulatiflik ise ~2 kat
#: yuksek -- ve ikisi arasindaki bant dolu. Esik oynatmak yalnizca
#: hangi hatayi yapacagini secmek olurdu.
#:
#: ENFLASYON STOK VE AKISI AYNI ORANDA ETKILER, kumulatiflik YALNIZCA
#: AKISI carpar. Bu yuzden olcut akis oraninin stok oranina BOLUMU:
#: enflasyon sadelesiyor, geriye "kac ceyrek toplanmis" kaliyor.
#:
#: Olculen dagilim (86 sayfa, canli icerik):
#:
#:     1.01  1.10  |  1.41  1.52  1.60 ...  2.0+  (en buyuk 10.5)
#:            ^-- dogru sayfalar        ^-- kumulatif sayfalar
#:
#: 1,10 ile 1,41 arasinda GERCEK BIR BOSLUK var; sinir oraya konuyor.
#: 1,41 kumulatif olmasina ragmen 2'ye varmiyor cunku oran
#: `1 + Q2/Q1` ve o sirkette Q2 kucuk.
#:
#: CAPRAZ DOGRULANDI: secilen 57 sayfanin 52'si 21-25 Agustos'ta
#: uretilmis (kumulatif donem), temiz kalan 29'un cogu 26 Agustos ve
#: sonrasi. Iki bagimsiz sinyal %95 ortusuyor.
CELISKI_SINIRI = 1.25


def _tablo_degeri(metin: str, kalem: str):
    """Sayfanin SEVIYE tablosundan bir kalem (milyar TL)."""
    m = re.search(rf"\| {re.escape(kalem)} \| ([-0-9,.]+) milyar", metin)
    return _sayi(m.group(1)) if m else None


def _sayi(x):
    if x is None or x == "—":
        return None
    try:
        return float(x.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _seri(metin: str) -> tuple[list, dict]:
    """Sayfanin "Son dort donem" tablosu: (donem sirasi, kalem->donem->deger)."""
    # DESEN PARCA PARCA KURULUYOR -- here-doc tuzagi.
    #
    # Bu dosya bir kez here-doc ile yazildi ve `\s`, `\n`, `\|`
    # dizileri dosyaya BASKA bir sey olarak dustu; desen sessizce
    # bozuldu. Kacislari tek tek `chr()` ile kurmak o yolu kapatiyor.
    bs = chr(92)
    nl = bs + "n"
    desen = (re.escape(SERI_BASLIK)
             + bs + r"s*" + nl + bs + r"s*" + nl
             + bs + r"| Kalem " + bs + r"(milyar TL" + bs + r") "
             + bs + r"| (.+?) " + bs + "|" + nl
             + bs + "|[^" + nl + "]*" + nl
             + "(.*?)(?:" + nl + nl + "|" + bs + "Z)")
    m = re.search(desen, metin, re.S)
    if not m:
        return [], {}
    sira = [x.strip() for x in m.group(1).split("|")]
    cikti: dict = {}
    for satir in m.group(2).splitlines():
        if satir.count("|") < 3:
            continue
        ad = satir.split("|")[1].strip()
        if not ad:
            continue
        deg = [x.strip() for x in satir.split("|")[2:-1]]
        cikti[ad] = dict(zip(sira, deg))
    return sira, cikti


def celiskili_sayfalar() -> list:
    """Verisi KENDI etiketiyle celisen bilanco sayfalari.

    NEDEN BU ARAC -- OLCULDU, 57 SAYFA YAYINDAYDI (2026-11-20)
    ----------------------------------------------------------
    Bu dosyanin ust kismi KUMULATIF ETIKETLI sayfalari topluyor
    ("2026/6"). Ama goc sirasinda bir grup sayfa CEYREKLIK ETIKET
    alip KUMULATIF VERI tasidi: baslik "2026 1. çeyrek", tablo alti
    aylik. Etikete bakan olcut onlari goremiyor.

    Somut (AKMGY, 2026 1. çeyrek sayfasi vs kendi Q3 sayfamizin
    serisi):

        Hasilat         0,63  ->  dogrusu 0,32   (akis, 2 kat)
        Net kar         0,31  ->  dogrusu 0,03   (akis, 10 kat)
        Aktif toplami  13,74  ->  dogrusu 13,11  (stok, degismiyor)
        Ozkaynak       11,13  ->  dogrusu 10,58  (stok, degismiyor)

    AKIS iki kat, STOK ayni: kumulatif raporun imzasi tam budur.
    Sayfa ustelik `veri_kaynagi: Çeyreklik mali tablolardan
    türetildi` diyor -- yani YANLIS BIR KOKEN iddiasi tasiyor ve AI
    ozeti bu sayilari duz metinde tekrarliyor.

    BAGIMSIZ TANIK: ayni sirketin DAHA YENI sayfasindaki "Son dort
    donem" tablosu. `bilanco_denetim.donem_etiketi_celiskisi` ayni
    isi tek sayfa icinde yapiyor ama "seri bolumu yoksa olcum yok"
    diyor ve bu 57 sayfada o bolum YOK. Tanik baska sayfada duruyordu.

    SILINMELERI GUVENLI: her birinin ayni sirket icin daha yeni bir
    sayfasi var (tanik oradan geliyor) ve o sayfanin serisi ayni
    donemin DOGRU rakamini zaten yayimliyor.
    """
    import collections                                   # noqa: PLC0415

    sayfalar: dict = collections.defaultdict(list)
    for p in sorted(ANALIZ.rglob("*.md")):
        t = p.read_text(encoding="utf-8", errors="replace")
        if _alan(t, "kategori") != KATEGORI:
            continue
        kod, donem = _alan(t, "kod"), _alan(t, "donem")
        if not kod or not donem:
            continue
        sira, seri = _seri(t)
        sayfalar[kod].append({"yol": p, "donem": donem,
                              "metin": t, "seri": seri})

    cikti = []
    for _kod, kayitlar in sayfalar.items():
        tanik: dict = {}
        for r in kayitlar:
            for kalem, m in (r["seri"] or {}).items():
                tanik.setdefault(kalem, {}).update(m)
        for r in kayitlar:
            if r["seri"]:
                continue              # kendi tanigi var, oteki kural bakar
            d = r["donem"]
            akis_s = _sayi((tanik.get("Hasılat") or {}).get(d))
            stok_s = _sayi((tanik.get("Aktif toplamı") or {}).get(d))
            akis_p = _tablo_degeri(r["metin"], "Hasılat")
            stok_p = _tablo_degeri(r["metin"], "Aktif toplamı")
            if None in (akis_s, stok_s, akis_p, stok_p):
                continue
            if min(akis_s, stok_s, akis_p, stok_p) <= 0:
                continue
            oran = (akis_p / akis_s) / (stok_p / stok_s)
            if oran >= CELISKI_SINIRI:
                cikti.append((r["yol"], _kod, d, round(oran, 2)))
    return sorted(cikti, key=lambda x: x[0].name)


def _celiski_kipi(n) -> int:
    """`--celiski`: verisi etiketiyle celisen sayfalari bildirir/siler."""
    celiskili = celiskili_sayfalar()
    print(f"verisi etiketiyle CELISEN sayfa: {len(celiskili)}")
    if not celiskili:
        print("celiski YOK")
        return 0
    for yol, kod, donem, oran in celiskili[:12]:
        print(f"  {kod:8s} {donem:18s} akis/stok {oran:>5}  {yol.name}")
    if len(celiskili) > 12:
        print(f"  ... ve {len(celiskili) - 12} tane daha")
    print(f"  OLCUT: akis orani / stok orani >= {CELISKI_SINIRI} "
          f"(enflasyon sadelesiyor, geriye kumulatiflik kaliyor)")
    if not n.uygula:
        print("KURU KOSU -- silmek icin --uygula")
        return 0
    silinen = []
    for yol, _kod, _donem, _oran in celiskili:
        try:
            yol.unlink()
            silinen.append(str(yol.relative_to(KOK)).replace(chr(92), "/"))
        except OSError as e:                             # noqa: BLE001
            print(f"  SILINEMEDI {yol.name}: {e}")
    print(f"silindi: {len(silinen)}")
    if n.liste and silinen:
        pathlib.Path(n.liste).write_text(
            chr(10).join(silinen) + chr(10), encoding="utf-8")
        print(f"liste yazildi: {n.liste}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true",
                    help="olcmekle kalma, gercekten sil")
    # SILINENLERIN LISTESI -- geri yazma adimi icin.
    #
    # Olculdu (2026-08-28): bu arac bugune kadar TEK BIR SILMEYI bile
    # depoya isleyememis. Sebep burada degil, is akisinda: geri yazma
    # adimi asamalamayi `git add --ignore-removal` ile yapiyor ve o
    # bayrak -- adi ustunde -- SILMELERI asamaya almiyor. Yerel olarak
    # dogrulandi:
    #
    #     git add --ignore-removal <klasor>  ->  A yeni.md
    #     git rm --cached -- <silinen yol>   ->  A yeni.md + D eski.md
    #
    # Sonuc: kosu sirasinda silinen sayfa o kosunun sitesinde yok ama
    # DEPODA duruyor, bir sonraki kurulumda geri geliyor. Arac
    # calisiyor gorunuyordu; hicbir sey degismiyordu.
    #
    # `--ignore-removal` KALIYOR ve dogru: genis silme yetkisi, es
    # zamanli kosan digerinin ciktisini silmek demek -- 2026-08-20'de
    # 60 sayfa tam boyle kayboldu. Cozum yetkiyi genisletmek degil,
    # BU ARACIN sildigi yollari acikca bildirmesi.
    ap.add_argument("--liste", metavar="DOSYA",
                    help="silinen yollari bu dosyaya yaz (geri yazma icin)")
    # ETIKET DEGIL VERI OLCUTU -- AYRI BAYRAK.
    #
    # Ustteki tarama sayfanin ETIKETINE bakiyor ("2026/6"). Bu ise
    # VERIYE bakiyor: ceyreklik etiket tasiyip kumulatif rakam
    # yayimlayan sayfalari buluyor (gerekce `celiskili_sayfalar`).
    # Ayri bayrak, cunku calisan davranisi degistirmemeli.
    ap.add_argument("--celiski", action="store_true",
                    help="etiketi ceyreklik ama verisi kumulatif olan "
                         "sayfalari bul (veri olcutu)")
    n = ap.parse_args()

    if n.celiski:
        return _celiski_kipi(n)

    kum, cey = tara()
    silinecek = [(k, v) for k, v in kum.items() if k in cey]
    kalan = sorted(k for k in kum if k not in cey)

    print(f"kumulatif sayfa      : {sum(len(v) for v in kum.values())}")
    print(f"ceyreklik sayfa      : {sum(len(v) for v in cey.values())}")
    print(f"karsiligi VAR (silinir): {len(silinecek)}")
    # "BIR KOSU DAHA BEKLIYOR" ILE "HICBIR KOSU URETEMEZ" AYRI SEYLER.
    #
    # Eskiden hepsi tek satirdi ve hepsi icin "~N uretim kosusu daha"
    # yaziyordu. Olculdu (2026-09-15): bekleyen 29 sayfanin 1'i
    # (TERA) defterde `sektor_tr` TASIMIYOR -- yani hicbir sektore
    # dusmuyor ve kac kosu kosulursa kosulsun ceyrekligi
    # URETILMEYECEK.
    #
    # Sonucu bir sayidan fazlasi: denetim her kosuda "uretim kosusu
    # gerekiyor" diye bildiriyordu. Hic kapanmayan bir uyari, okunmayan
    # bir uyariya donusur -- ve o zaman yaninda duran GERCEK uyari da
    # okunmaz.
    try:
        _uretilebilir = uretilebilir_kodlar()
    except Exception as _e:                            # pragma: no cover
        # Defter okunamadi: "bilmiyorum" ile "uretilemez" ayni sey
        # degil. Hepsi bekleyen sayiliyor, oksuz DENMIYOR.
        print(f"  (defter okunamadi: {_e} -- oksuz ayrimi yapilmadi)")
        _uretilebilir = None
    bekleyen, oksuz = bekleyen_ve_oksuz(kalan, _uretilebilir)

    print(f"karsiligi YOK (kalir)  : {len(kalan)}")
    if bekleyen:
        print(f"  uretim BEKLEYEN ({len(bekleyen)}): "
              f"{', '.join(bekleyen[:10])}")
        print(f"  -> bunlar icin ~{-(-len(bekleyen) // 60)} uretim kosusu daha")
    if oksuz:
        print(f"  OKSUZ ({len(oksuz)}): {', '.join(oksuz)}")
        print("  -> defterde `sektor_tr` yok; KOSU COZMEZ. Ya sektor "
              "atanmali ya da sayfa elle kaldirilmali.")

    def _liste_yaz(yollar: list[str]) -> None:
        """Silinen yollari yazar -- HIC SILINMESE DE dosyayi olusturur.

        Bos dosya ile OLMAYAN dosya ayni sey degil. Geri yazma adimi
        "arac hic kosmadi" ile "kostu, silecek bir sey bulmadi"
        arasindaki farki gormek zorunda; dosyayi her durumda yazmak o
        adimin kosulunu tek anlamli kiliyor.
        """
        if not n.liste:
            return
        pathlib.Path(n.liste).write_text(
            "".join(y + chr(10) for y in yollar), encoding="utf-8")

    if not silinecek:
        print("\nSilinecek sayfa yok.")
        _liste_yaz([])
        return 0

    if not n.uygula:
        print("\n(olcum modu -- silmek icin --uygula)")
        for kod, yollar in silinecek[:6]:
            print(f"  {yollar[0].name}  ->  {cey[kod][0].name}")
        # OLCUM MODU HICBIR SEY SILMEZ -- listesi de bos olmali.
        # Burada `return` etmeden gecmek, silinmemis dosyalari
        # "silindi" diye bildirmek olurdu.
        _liste_yaz([])
        return 0

    adet = 0
    silinen: list[str] = []
    for kod, yollar in silinecek:
        for p in yollar:
            p.unlink()
            silinen.append(p.relative_to(KOK).as_posix())
            adet += 1
    _liste_yaz(silinen)
    print(f"\n{adet} kumulatif sayfa silindi "
          f"({len(silinecek)} sirketin ceyrekligi yerini aldi).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
