# -*- coding: utf-8 -*-
"""MOBILDE GIZLENEN HER SEY GEREKCESIYLE KAYITLI OLMALI.

BU DOSYA NEDEN VAR
------------------
2026-09-18'de canli akis mobilde HIC cizilmiyordu (`.masa-yan` 900px
altinda `display: none`). Kusuru kullanici bildirdi; hicbir sinama
gormuyordu. Sebep yapisal:

    CSS ile gizlenen icerik HTML'de DURMAYA DEVAM EDER.

Yani "sayfa uretiliyor mu, baglanti var mi, sema dogru mu, kirik bag
var mi" diye soran her sinama yesil kalir. Eksik olan soru "okur bunu
GOREBILIYOR mu" idi ve onu soran yoktu.

Tek kusuru duzeltmek yetmez -- ayni sinifta baskalari da vardi. Mobil
kirilimlardaki butun `display: none` kurallari tarandi ve ucu gercek
kayip cikti:

    .masa > .masa-yan       <=899px  canli akis TUMUYLE yoktu
    .sondakika-durdur       <=640px  akan seridi durdurmanin TEK yolu;
                                     WCAG 2.2 SC 2.2.2, Seviye A ihlali
    .duyarlilik .neden      <=560px  "Kim etkilenir?" tablosunda
                                     gerekce sutunu; 793 sayfa, 3.544
                                     satir. Geriye yalniz yildizlar
                                     kaliyordu -- ustelik tablonun
                                     kendi notu yildizin tek basina
                                     ne anlatmadigini soyluyor.

KURAL
-----
Mobilde bir seyi gizlemek serbest ama SESSIZ olamaz. Asagidaki
defterde karsiligi olmayan her yeni gizleme bu sinamayi KIRMIZI yapar.
Defter bir izin listesi degil, bir GEREKCE listesi: yeni bir satir
eklemek, "bunu neden gizliyoruz" sorusunu cevaplamayi zorunlu kilar.

Defterden DUSEN bir satir kirmizi yapmaz -- bir seyi mobilde geri
getirmek iyilesme, engellenmemeli.
"""

from __future__ import annotations

import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent

#: Telefon/tablet sayilan genislik. 899 dahil: kusur tam orada yasandi.
MOBIL_ESIK = 900

#: GEREKCE DEFTERI -- secici: neden gizli.
#:
#: Buraya bir satir eklemeden once sorulacak soru: "bu icerik mobilde
#: BASKA BIR YERDEN ulasilabiliyor mu?" Cevap hayirsa gizleme degil,
#: yeniden duzenleme gerekiyor.
GEREKCE = {
    # --- bicimsel: hicbir icerik kaybi yok ---
    ".akis-suzgec::-webkit-scrollbar":
        "kaydirma cubugu gorunumu; icerik degil",
    ".izgara::-webkit-scrollbar":
        "kaydirma cubugu gorunumu; icerik degil",
    ".ust nav::-webkit-scrollbar":
        "kaydirma cubugu gorunumu; icerik degil",

    # --- ayni bilgi komsusunda duruyor ---
    ".akis-tema":
        "kart uzerindeki konu etiketi; basligin kendisi zaten konuyu "
        "soyluyor, dar ekranda iki satir yer kapliyordu",
    ".arastirma-kart .rozet:nth-of-type(n+3)":
        "ucuncu rozetten sonrasi kirpiliyor; ilk ikisi en gucluleri "
        "ve tamami analiz sayfasinda duruyor",
    ".izgara .rozet-arastirma":
        "izgara kartinda tur rozeti; kartin gittigi sayfada basligin "
        "yaninda ayni bilgi var",

    # --- ikamesi olan ---
    ".ust-ic > nav":
        "ust menu; yerine `.alt-gezinme` (5 sekme) geliyor. Olculdu "
        "(2026-09-18): ust menunun 9 hedefinin 5'i alt menude, kalan "
        "4'u (/bilancolar/, /makro/, /yorum/, /teknik/) mobilde de "
        "ULASILABILIYOR -- ikisi 1 tik, ikisi Arastirma uzerinden 2 tik",
    ".masa > .masa-yan > .tv-kutu":
        "TradingView parcacigi; dar ekranda hem agir hem dar. AYNI "
        "VERI /gundem/ ve varlik sayfalarinda duruyor. Gizlenen sey "
        "bilesen, icerik degil",

    # --- kirpma, yok etme degil ---
    ".akis-liste > li:nth-child(n + 7)":
        "canli akis mobilde ALTI OGEYE iniyor (61 oge ~4.600 piksel, "
        "on iki ekran boyu). Gerisi 'Tum canli akisi gor' bagininda; "
        "sutunun KENDISI gizlenmiyor -- 2026-09-18 kusuru tam oydu",
}

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def yorumsuz(css: str) -> str:
    """CSS yorumlarini at.

    Olculdu: yorum icindeki ornek kurallar secici sanilip sahte bulgu
    uretiyordu (`.ust-ic` icin bir kez yasandi).
    """
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def mobil_gizlenenler(css: str) -> dict[str, int]:
    """Mobil kirilimlarda `display: none` verilen seciciler -> esik."""
    cikti: dict[str, int] = {}
    for m in re.finditer(r"@media([^{]+)\{", css):
        mw = re.search(r"max-width:\s*(\d+)px", m.group(1))
        if not mw or int(mw.group(1)) >= MOBIL_ESIK:
            continue
        bas, derinlik, i = m.end(), 1, m.end()
        while i < len(css) and derinlik:
            if css[i] == "{":
                derinlik += 1
            elif css[i] == "}":
                derinlik -= 1
            i += 1
        for r in re.finditer(r"([^{}\n;]+?)\{([^}]*)\}", css[bas:i - 1]):
            if re.search(r"display\s*:\s*none", r.group(2)):
                cikti[r.group(1).strip()] = int(mw.group(1))
    return cikti


print("\nTarama gercekten calisiyor mu")
# Once taramayi BILINEN bir girdiyle sinariz. Sitenin icerigine
# baglanmayan bir capa: site nasil degisirse degissin gecerli kalir.
_deneme = ("@media (max-width: 500px) { .gizli-ornek { display: none; } "
           ".gorunur-ornek { color: red; } } "
           "@media (max-width: 1200px) { .genis-ornek { display: none; } } "
           "/* @media (max-width: 400px) { .yorumdaki { display: none } } */")
_b = mobil_gizlenenler(yorumsuz(_deneme))
esit(_b.get(".gizli-ornek"), 500, "gizli seciciyi ve esigini buluyor")
esit(".gorunur-ornek" in _b, False, "gizli olmayani saymiyor")
esit(".genis-ornek" in _b, False, "masaustu kirilimini saymiyor")
esit(".yorumdaki" in _b, False, "YORUM icindeki kurali saymiyor")

print("\nGerekce defteri")
_css = yorumsuz((_SITE / "statik" / "stil.css").read_text(encoding="utf-8"))
_gizli = mobil_gizlenenler(_css)
esit(len(_gizli) > 0, True, f"stil.css tarandi ({len(_gizli)} gizleme)")

_kayitsiz = {s: e for s, e in _gizli.items() if s not in GEREKCE}
if _kayitsiz:
    print("\n  GEREKCESI YAZILMAMIS GIZLEME:")
    for _s, _e in sorted(_kayitsiz.items()):
        print(f"    @media(max-width:{_e}px)  {_s}")
    print("\n  Bunlar mobilde GORUNMEZ. Icerik baska yerden ulasilabiliyorsa")
    print("  GEREKCE defterine sebebiyle ekleyin; ulasilamiyorsa gizlemeyin.")
esit(sorted(_kayitsiz), [], "her mobil gizlemenin yazili gerekcesi var")

# Defterden dusenler ENGEL DEGIL -- geri getirmek iyilesmedir.
_artik_yok = sorted(set(GEREKCE) - set(_gizli))
if _artik_yok:
    print(f"\n  not: defterde olup artik gizlenmeyen {len(_artik_yok)} satir"
          f" (mobilde geri gelmis -- defterden silinebilir):")
    for _s in _artik_yok:
        print(f"    {_s}")

print("\nGeri getirilenler bir daha gizlenmesin")
# 2026-09-18'de mobilde geri getirilen uc bilesen. Adlari burada
# ACIKCA yaziyor: defter kurali zaten yakalardi ama bu isim listesi,
# kusurun NE OLDUGUNU okuyana anlatiyor.
for _ad, _sec in (
        ("canli akis sutunu", r"\.masa\s*>\s*\.masa-yan\s*$"),
        ("son dakika duraklatma dugmesi", r"\.sondakika-durdur\s*$"),
        ("duyarlilik gerekce sutunu", r"\.duyarlilik\s+\.neden\s*$")):
    _suclu = [s for s in _gizli if re.search(_sec, s.strip())]
    esit(_suclu, [], f"{_ad} mobilde gizlenmiyor")

print(f"\nTUM TESTLER GECTI ({_gecti})")
