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
    n = ap.parse_args()

    kum, cey = tara()
    silinecek = [(k, v) for k, v in kum.items() if k in cey]
    kalan = sorted(k for k in kum if k not in cey)

    print(f"kumulatif sayfa      : {sum(len(v) for v in kum.values())}")
    print(f"ceyreklik sayfa      : {sum(len(v) for v in cey.values())}")
    print(f"karsiligi VAR (silinir): {len(silinecek)}")
    print(f"karsiligi YOK (kalir)  : {len(kalan)}")
    if kalan:
        print(f"  ornek: {', '.join(kalan[:10])}")
        print(f"  -> bunlar icin ~{-(-len(kalan) // 60)} uretim kosusu daha")

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
