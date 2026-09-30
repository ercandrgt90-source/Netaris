# -*- coding: utf-8 -*-
"""Tema paleti: OKURUN GORDUGU SONUC olculuyor, blok duzeni degil.

NEDEN VAR
---------
Okurun UC durumu var, iki degil:

    1. "light" secti  -> koke `data-tema="light"` yazilir
    2. "dark" secti   -> koke `data-tema="dark"` yazilir
    3. HIC SECMEDI    -> koke HICBIR SEY yazilmaz   <-- COGUNLUK

Ucuncusu varsayilan. `temel.html` acilis betigi damgayi yalnizca
localStorage'da acik bir secim varsa basiyor; `tema.js` de bunu
"secim yok -> sistem tercihi gecerli" diye belgeliyor. Aramadan
gelen ilk ziyaretin TAMAMI bu durumda.

OLCULDU (2026-09-30): ayni jetonlara karar veren DORT ayri blok
vardi -- taban `:root`, `[data-tema="light"]`, `[data-tema="dark"]`
ve dosyanin 3900'lu satirlarinda dorduncu bir `prefers-color-scheme`
blogu. Dordu birbirinden ayri dusmustu:

    --vurgu (koyu)   medya blogunda #6f9dfb MAVI, secili koyu temada
                     #2dd4bf TEAL. Ayni koyu temanin iki surumu; okur
                     hangisini gorecegini tema dugmesine BASMIS
                     olmasindan ogreniyordu. `a { color: var(--vurgu) }`
                     oldugu icin bu, sitedeki butun baglantilar demek.
    --vurgu-parlak   tabanda kobalt mavi, secili acik temada teal
    --vurgu-zar      tabanda teal, secili acik temada mavi
    --ust-*          yalnizca SECILI temalarda tanimliydi; varsayilan
                     durumda 21 bildirim yedeksiz `var()` cagiriyor ve
                     hepsi dusuyordu
    --t-* (kart)     koyu surumleri YALNIZCA medya blogundaydi; tema
                     dugmesiyle koyu secen okur, koyu zemin uzerinde
                     ACIK temanin kart renklerini goruyordu

Hicbiri "bozuk sayfa" uretmiyordu: `color` dusunce DEVRALIYOR ve
devralinan renk tesadufen okunakli tarafta kaliyordu. Kusurun yillarca
gorunmemesinin sebebi buydu -- bozulma degil, SESSIZ geri dusus.

`denetim.py`deki `jeton-tanimsiz` kurali bunu yakalayamaz: bir adin
DOSYADA HERHANGI BIR YERDE tanimli olup olmadigina bakiyor, HER TEMA
DURUMUNDA tanimli olup olmadigina degil.

NE OLCULUYOR
------------
Blok sayisi ya da blok sirasi DEGIL -- onlar yarin degisebilir ve
degismeleri bir kusur degil. Olculen sey, dort okur durumunun her
birinde jetonlarin ALDIGI SON DEGER. Kaskad burada kucuk olcekte
yeniden hesaplaniyor (ozgulluk, sonra belge sirasi).

Bu yuzden sinama, koyu listenin iki kez yazilmasindan sikayet etmiyor;
medya sorgusuyla oznitelik secicisi tek kurulda birlestirilemedigi
icin iki kopya ZORUNLU. Sinamanin tuttugu sey, iki kopyanin AYNI
KALMASI.
"""

import io
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
CSS = KOK / "statik" / "stil.css"

#: Kok elemani hedefleyen, TANIDIK secici bicimleri.
#:
#: Liste kapali TUTULUYOR: taninmayan bir kok secicisi cikarsa sinama
#: onu sessizce ATLAMIYOR, `test_taninmayan_kok_secici_yok` ile
#: kirmizi yaniyor. Bir kayit defterini sinirsiz birakmak, defterin
#: disinda kalan seyin gorunmez olmasi demek -- bu dosyanin varlik
#: sebebi zaten tam olarak o.
TANIDIK_KOK = {
    ":root": lambda damga: True,
    "html": lambda damga: True,
    ':root[data-tema="dark"]': lambda damga: damga == "dark",
    ':root[data-tema="light"]': lambda damga: damga == "light",
    ':root:not([data-tema="light"])': lambda damga: damga != "light",
    ':root:not([data-tema="dark"])': lambda damga: damga != "dark",
}

#: Okurun gercekten icinde bulunabilecegi durumlar.
#: (ad, sistem_koyu, damga)
DURUMLAR = (
    ("sistem acik / secim yok", False, None),
    ("sistem acik / 'light' secili", False, "light"),
    ("sistem koyu / 'light' secili", True, "light"),
    ("sistem koyu / secim yok", True, None),
    ("sistem acik / 'dark' secili", False, "dark"),
    ("sistem koyu / 'dark' secili", True, "dark"),
)

ACIK_DURUMLAR = DURUMLAR[:3]
KOYU_DURUMLAR = DURUMLAR[3:]


def _yorumsuz(s: str) -> str:
    # BOM ATILIYOR. `stil.css` BOM ile basliyor ve atilmazsa dosyanin
    # ILK kurali `'﻿:root'` olarak okunuyor -- yani taban palet
    # hic gorulmuyordu. Ilk yazimda bu sinama tam da o yuzden
    # "acik temada 32 jeton tanimsiz" diyordu: kusur CSS'te degil,
    # OLCUMDE idi. Olcum araci once KENDINI dogrulamali.
    return re.sub(r"/\*.*?\*/", "", s.lstrip("﻿"), flags=re.S)


def _kok_secici_mi(tek: str) -> bool:
    """Bu secici KOK elemanini hedefliyor mu?

    Gevsek TUTULUYOR: `:root` gecen ya da `html` ile baslayan her sey
    kok sayiliyor, tam esleme aranmiyor. Sebep, yukaridaki BOM
    hikayesi -- ilk surum `startswith(":root")` ile suzuyordu ve
    `'﻿:root'` suzgecten sessizce dusuyordu. Suzgec ne kadar
    dar olursa, kayit defterinin disinda kalan o kadar cok sey
    GORUNMEZ olur; oysa defterin tamami bunu gormek icin var.

    Tanidik olmayanlari eleme isi `TANIDIK_KOK` kayitina ve
    `test_taninmayan_kok_secici_yok` sinamasina birakiliyor.
    """
    return ":root" in tek or re.match(r"^html\b", tek) is not None


def _bloklar(s: str, basla: int = 0):
    """(prelude, govde, konum) uretir -- verilen duzeydeki her kural."""
    i = basla
    n = len(s)
    prelude_bas = i
    while i < n:
        c = s[i]
        if c == "{":
            derinlik = 1
            j = i + 1
            while j < n and derinlik:
                if s[j] == "{":
                    derinlik += 1
                elif s[j] == "}":
                    derinlik -= 1
                j += 1
            yield s[prelude_bas:i].strip(), s[i + 1:j - 1], prelude_bas
            i = j
            prelude_bas = i
        elif c == "}":
            # Bu duzeyin sonu.
            return
        else:
            i += 1


def _bildirimler(govde: str) -> dict:
    """Yalnizca `--ad: deger` bildirimleri. Ic kurallar atlanir."""
    duz = re.sub(r"\{[^{}]*\}", "", govde)
    cikti = {}
    for ad, deger in re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", duz):
        cikti[ad] = " ".join(deger.split())
    return cikti


def _ozgulluk(secici: str) -> int:
    """Bu dosyadaki kok secicileri icin yeterli, kaba ozgulluk."""
    return 1 + len(re.findall(r"\[", secici))


def kok_kurallari(css: str):
    """[(sira, secici, medya_koyu, baski, bildirimler)] dondurur."""
    s = _yorumsuz(css)
    cikti = []
    sira = 0

    def gez(govde, medya_koyu, baski):
        nonlocal sira
        for prelude, ic, _ in _bloklar(govde):
            p = " ".join(prelude.split())
            if p.startswith("@media"):
                # BOSLUGA DUYARSIZ. Kaynakta kosul
                # `(prefers-color-scheme: dark)` diye yaziliyor ama
                # kucultulmus ciktida `(prefers-color-scheme:dark)`
                # oluyor. Ilk surum bosluklu metni ariyordu; canli
                # CSS'e dogrultuldugunda HER medya blogunu kosulsuz
                # sandi ve "sistem acik / secim yok" durumunu KOYU
                # palet gibi olctu. Sonuc imkansizdi, o yuzden fark
                # edildi -- ama imkansiz olmasaydi sessizce yanlis
                # olurdu.
                yeni_koyu = medya_koyu or re.search(
                    r"prefers-color-scheme\s*:\s*dark", p) is not None
                yeni_baski = baski or re.search(r"\bprint\b", p) is not None
                gez(ic, yeni_koyu, yeni_baski)
                continue
            if p.startswith("@"):
                continue
            for tek in p.split(","):
                tek = " ".join(tek.split())
                if not tek:
                    continue
                # Yalnizca KOK elemanini hedefleyen kurallar sayiliyor;
                # `.tur-makro { --tur: ... }` gibi bilesen kurallari
                # tema paleti degil.
                if not _kok_secici_mi(tek):
                    continue
                bild = _bildirimler(ic)
                if bild:
                    sira += 1
                    cikti.append((sira, tek, medya_koyu, baski, bild))

    gez(s, False, False)
    return cikti


def palet(kurallar, sistem_koyu: bool, damga, baski: bool = False) -> dict:
    """Verilen okur durumunda jetonlarin ALDIGI SON deger.

    BASKI KURALLARI AYRI HESAPLANMIYOR -- ekran kurallariyla AYNI
    kaskadda yarisiyor. Ilk surum once ekran paletini kurup baski
    paletini uzerine `update` ediyordu; o model "baski her zaman ezer"
    varsayimini SINAMANIN KENDISI garanti ediyordu, yani sorulan soru
    cevabin icine yazilmisti. Mutasyonla goruldu: baski sifirlamasinin
    ozgullugu dusuruldugunde sinama YESIL kaldi. Simdi ozgulluk ve
    belge sirasi gercekten karsilastiriliyor ve ayni mutasyon kirmizi
    yaniyor.
    """
    uygun = []
    for sira, secici, medya_koyu, k_baski, bild in kurallar:
        if k_baski and not baski:
            continue
        if medya_koyu and not sistem_koyu:
            continue
        esles = TANIDIK_KOK.get(secici)
        if esles is None or not esles(damga):
            continue
        uygun.append((_ozgulluk(secici), sira, bild))
    uygun.sort(key=lambda t: (t[0], t[1]))
    sonuc = {}
    for _, _, bild in uygun:
        sonuc.update(bild)
    return sonuc


# --------------------------------------------------------------------
# Sinamalar
# --------------------------------------------------------------------

def _css():
    return io.open(CSS, encoding="utf-8", newline="").read()


def test_taninmayan_kok_secici_yok():
    """Kok jetonu tanimlayan her secici TANIDIK_KOK'te olmali.

    Yeni bir bicim (ornegin `:root[data-yogunluk="sik"]`) eklenirse
    sinama onu sessizce atlamaz; burada durur ve kayit defterine
    eklenmesini ister. Aksi halde defterin disinda kalan her sey
    olculmemis olur.
    """
    bilinmeyen = sorted({
        secici for _, secici, _, _, _ in kok_kurallari(_css())
        if secici not in TANIDIK_KOK})
    assert not bilinmeyen, (
        "TANIDIK_KOK'te olmayan kok secici(ler): " + ", ".join(bilinmeyen))


def test_acik_tema_tek_surum():
    """Sistem acigi ile SECILMIS acik ayni paleti vermeli."""
    k = kok_kurallari(_css())
    temel = palet(k, *ACIK_DURUMLAR[0][1:])
    for ad, sistem_koyu, damga in ACIK_DURUMLAR[1:]:
        p = palet(k, sistem_koyu, damga)
        fark = {j: (temel.get(j), p.get(j))
                for j in set(temel) | set(p) if temel.get(j) != p.get(j)}
        assert not fark, f"{ACIK_DURUMLAR[0][0]} <-> {ad} ayrisiyor: {fark}"


def test_koyu_tema_tek_surum():
    """Sistem koyusu ile SECILMIS koyu ayni paleti vermeli.

    Kusur tam buradaydi: medya blogu #6f9dfb MAVI, oznitelik blogu
    #2dd4bf TEAL veriyordu.
    """
    k = kok_kurallari(_css())
    temel = palet(k, *KOYU_DURUMLAR[0][1:])
    for ad, sistem_koyu, damga in KOYU_DURUMLAR[1:]:
        p = palet(k, sistem_koyu, damga)
        fark = {j: (temel.get(j), p.get(j))
                for j in set(temel) | set(p) if temel.get(j) != p.get(j)}
        assert not fark, f"{KOYU_DURUMLAR[0][0]} <-> {ad} ayrisiyor: {fark}"


def test_iki_tema_gercekten_farkli():
    """Acik ve koyu palet AYNI olmamali.

    Bu, yukaridaki iki sinamanin HAREKETLI HEDEF olmasini engelliyor:
    koyu blogun tamami silinse "acik tek surum" ve "koyu tek surum"
    sinamalari ikisi de gecerdi -- cunku geriye tek palet kalirdi.
    Burasi en az bir avuc jetonun gercekten ayrismasini sart kosuyor.
    """
    k = kok_kurallari(_css())
    a = palet(k, False, None)
    ko = palet(k, True, None)
    ayrisan = {j for j in set(a) | set(ko) if a.get(j) != ko.get(j)}
    assert len(ayrisan) >= 15, (
        f"acik ve koyu palet yalnizca {len(ayrisan)} jetonda ayrisiyor; "
        "koyu tema kaybolmus olabilir")
    for zorunlu in ("--zemin", "--yazi", "--panel", "--vurgu"):
        assert zorunlu in ayrisan, f"{zorunlu} iki temada AYNI"


def test_her_jeton_her_durumda_tanimli():
    """Bir tema jetonu bir durumda tanimliysa HEPSINDE tanimli olmali.

    `--ust-yazi` ve uc kardesi yalnizca secili temalarda tanimliydi.
    Varsayilan durumdaki okur icin `var(--ust-yazi)` cozulemiyor,
    bildirim dusuyor ve `color` DEVRALIYOR. Sayfa okunakli kaliyor,
    yani hata hicbir yerde gorunmuyor -- ama tasarim karari
    okurlarin cogunluguna hic ulasmiyor.

    Bilesen jetonlari (`--tur`, `--w`) kapsam DISI: onlar bilerek
    disaridan atanir. Olcut "bir KOK kapsaminda tanimli olmak".
    """
    k = kok_kurallari(_css())
    tum = set()
    for _, _, _, baski, bild in k:
        if not baski:
            tum |= set(bild)

    eksik = {}
    for ad, sistem_koyu, damga in DURUMLAR:
        p = palet(k, sistem_koyu, damga)
        yok = sorted(tum - set(p))
        if yok:
            eksik[ad] = yok
    assert not eksik, f"bazi durumlarda TANIMSIZ jetonlar: {eksik}"


def test_yedeksiz_kullanilan_jeton_kok_kapsaminda():
    """`var(--x)` yedeksiz cagriliyorsa `--x` bir yerde tanimli olmali.

    `denetim.py` bunu zaten yapiyor; burada da tutuluyor cunku
    yukaridaki sinama "tanimli olan her jeton" kumesini KOK
    kurallarindan cikariyor. O kume bos kalirsa yukarisi bos bos
    gecerdi; burasi kumenin gercekten dolu oldugunu da gosteriyor.
    """
    s = _yorumsuz(_css())
    tanim = set(re.findall(r"(--[\w-]+)\s*:", s))
    yedeksiz = set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", s))
    assert len(yedeksiz) > 40, f"yedeksiz kullanim {len(yedeksiz)}, az"
    eksik = sorted(yedeksiz - tanim)
    assert not eksik, f"tanimsiz ama yedeksiz kullanilan: {eksik}"


def test_ust_serit_jetonlari_kokte():
    """Serit jetonlari TABAN `:root`ta olmali -- yalnizca temalarda degil.

    Kusurun tam olcusu. Taban kapsam, damgasi olmayan okurun aldigi
    tek kapsam; serit jetonlari oraya yazilmazsa varsayilan ziyaretci
    onlari HIC gormez.
    """
    k = kok_kurallari(_css())
    taban = {}
    for _, secici, medya_koyu, baski, bild in k:
        if secici == ":root" and not medya_koyu and not baski:
            taban.update(bild)
    for ad in ("--ust-zemin", "--ust-yazi", "--ust-yazi-2",
               "--ust-cizgi", "--ust-panel"):
        assert ad in taban, f"{ad} taban :root'ta tanimli degil"


def test_baski_koyu_temayi_eziyor():
    """Yazdirmada palet BEYAZ kagit olmali -- sistem koyu olsa bile.

    Koyu tema `:root:not([data-tema="light"])` ile yaziliyor; ozgullugu
    0,1,1. Baski blogundaki sifirlama sadece `:root` olsaydi (0,1,0)
    kaybederdi ve sistem koyusundaki okur sayfayi SIMSIYAH basardi.
    Dosyada daha sonra gelmek yetmez: once ozgulluk bakilir.
    """
    k = kok_kurallari(_css())
    for ad, sistem_koyu, damga in DURUMLAR:
        p = palet(k, sistem_koyu, damga, baski=True)
        assert p["--zemin"] == "#fff", (ad, p["--zemin"])
        assert p["--panel"] == "#fff", (ad, p["--panel"])
        assert p["--yazi"] == "#000", (ad, p["--yazi"])


def test_baski_sinyal_renkleri_kagitta_okunuyor():
    """Parlak koyu tema renkleri beyaz kagida gitmemeli.

    `--vurgu: #2dd4bf` beyaz uzerinde ~1,9:1. Baglantilar ve
    artis/azalis rakamlari kagitta okunmuyordu.
    """
    k = kok_kurallari(_css())

    def parlaklik(x):
        x = x.strip().lstrip("#")
        r, g, b = (int(x[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    for ad, sistem_koyu, damga in DURUMLAR:
        p = palet(k, sistem_koyu, damga, baski=True)
        for jeton in ("--vurgu", "--artis", "--azalis", "--uyari"):
            oran = (parlaklik(p[jeton]) + 0.05)
            oran = (1.0 + 0.05) / oran
            assert oran >= 4.5, (
                f"{ad}: {jeton} = {p[jeton]}, beyaz kagitta {oran:.2f}:1")


def test_durum_noktasi_zemininde_gorunuyor():
    """Serit durum noktalari KENDI zeminlerinde 3:1 gecmeli.

    `.nokta` ailesi metin degil; WCAG 1.4.11'e gore esik 4,5 degil
    3,0. Ama zemin de sayfa zemini DEGIL: nokta `.serit` icinde
    duruyor ve `.serit` arka plani `--zemin-2`. Yanlis zemine gore
    olcmek, esigi gecmis gibi gosterebilirdi.

    Olculdu (2026-09-30): `--notr` #93a1b5 ile 2,16:1 idi.
    """
    k = kok_kurallari(_css())

    def gri(x):
        x = x.strip().lstrip("#")
        if len(x) == 3:
            x = "".join(c * 2 for c in x)
        r, g, b = (int(x[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    for ad, sistem_koyu, damga in DURUMLAR:
        p = palet(k, sistem_koyu, damga)
        zemin = gri(p["--zemin-2"])
        for jeton in ("--notr", "--yazi-3", "--artis", "--uyari"):
            n = gri(p[jeton])
            hi, lo = max(n, zemin), min(n, zemin)
            o = (hi + 0.05) / (lo + 0.05)
            assert o >= 3.0, f"{ad}: {jeton} = {p[jeton]}, seritte {o:.2f}:1"


def _kosk():
    gecen = kirik = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_") and callable(f):
            try:
                f()
                gecen += 1
            except AssertionError as e:
                kirik += 1
                print(f"KIRIK {ad}: {e}")
            except Exception as e:  # noqa: BLE001
                kirik += 1
                print(f"HATA  {ad}: {type(e).__name__}: {e}")
    print(f"tema paleti: {gecen} gecti, {kirik} kirik")
    return 1 if kirik else 0


if __name__ == "__main__":
    sys.exit(_kosk())
