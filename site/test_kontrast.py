# -*- coding: utf-8 -*-
"""RENK JETONLARI WCAG AA KONTRASTINI SAGLAMALI -- IKI TEMADA DA.

BU DOSYA NEDEN VAR
------------------
Mobil/erisilebilirlik denetiminde (2026-09-18) kontrasti olcen hicbir
sinama olmadigi goruldu. Olculunce acik temada bir acik cikti:

    --vurgu #0a7d78 / sayfa zemini #eef2f7   =  4.43   (AA esigi 4.5)

`a { color: var(--vurgu) }` sitedeki BUTUN baglantilar demek ve govde
metni dogrudan sayfa zemininin uzerinde duruyor (`main.kabuk >
.sayfa > .govde` -- hicbiri kendi zeminini vermiyor). Yani acik temada
her baglanti esigin 0,07 altindaydi. Marka bir tik koyultuldu
(#0a7974): ton 177,4 -> 177,3 derece, doygunluk %85,2 -> %84,7,
yalnizca aydinlik %26,5 -> %25,7. Yeni oran 4,67.

NEDEN JETON SEVIYESINDE
-----------------------
Her bilesenin kontrastini tek tek olcmek tarayici gerektirir. Ama
sitedeki renkler birkac JETONDAN geliyor; jetonlar gecerse bilesenler
de geciyor. Jeton seviyesi hem olculebilir hem de kusuru KAYNAGINDA
yakaliyor: bir jeton degistiginde onunla boyanan her sey degisir.

NE SINANIYOR
------------
1. Kontrast hesabi bilinen degerlerde dogru (kendi kendini sinar).
2. Iki temada da metin/zemin ciftleri AA esigini gecer.
3. Vurgu rengi hem sayfa zemininde hem panelde okunur.
4. Marka, ARTIS sinyalinden ton olarak yeterince uzak durur --
   `stil.css`te yazili "26 derece" karari korunuyor mu.
"""

from __future__ import annotations

import colorsys
import pathlib
import re

_SITE = pathlib.Path(__file__).resolve().parent

#: WCAG 2.2 esikleri.
AA_NORMAL = 4.5
AA_BUYUK = 3.0

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}\n    beklenen: {beklenen!r}"
              f"\n    gelen:    {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def rgb(renk: str) -> tuple[int, int, int] | None:
    h = (renk or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def isik(c: tuple[int, int, int]) -> float:
    """Bagil parlaklik -- WCAG 2.x tanimi."""
    def k(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * k(c[0]) + 0.7152 * k(c[1]) + 0.0722 * k(c[2])


def oran(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = isik(a), isik(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def ton(renk: str) -> float:
    c = rgb(renk)
    return colorsys.rgb_to_hls(*[v / 255 for v in c])[0] * 360


print("\nHesap gercekten calisiyor mu")
# Bilinen degerler: standardin kendisinden, siteden bagimsiz.
esit(round(oran(rgb("#000000"), rgb("#ffffff"))), 21, "siyah/beyaz = 21")
esit(round(oran(rgb("#777777"), rgb("#777777"))), 1, "ayni renk = 1")
esit(round(oran(rgb("#767676"), rgb("#ffffff")), 1), 4.5,
     "#767676/beyaz = 4.5 (AA sinir ornegi)")
esit(oran(rgb("#0a7974"), rgb("#eef2f7")) > oran(rgb("#0a7d78"), rgb("#eef2f7")),
     True, "koyultmak orani ARTIRIYOR (yon dogru)")
esit(rgb("#xyzxyz"), None, "gecersiz renk cozulmuyor")

print("\nJetonlar okunuyor")
_css = re.sub(r"/\*.*?\*/", " ",
              (_SITE / "statik" / "stil.css").read_text(encoding="utf-8"),
              flags=re.S)


# PALET BLOK ARANARAK DEGIL, HESAPLANARAK BULUNUYOR.
#
# OLCULDU (2026-09-30) -- bu dosyanin BASINA gelen sey:
# Onceki surum acik paleti `:root[data-tema="light"] { ... }` blogunu
# regexle arayarak okuyordu. Tema yapisi sadelestirilip o blok
# kaldirilinca desen, `@media print` sifirlamasinin secici listesinde
# gecen AYNI metne dustu ve BASKI paletini okumaya basladi:
#     --zemin #fff   --panel #fff   --yazi #000   --cizgi #bbb
# Yani bu dosya, kagit paletini "acik tema" diye olcuyordu. Siyah
# uzerine beyaz 21:1 oldugu icin BUTUN ciftler kolayca geciyordu --
# sinama kirmizi yanmadi, SESSIZCE KORLESTI. Kirmizi bir sinama
# sorunu duyurur; korlesen bir sinama sorunu ORTBAS EDER.
#
# Asagidaki "etiketler dogru mu" korumasi da yakalayamadi: o, acik
# zeminin koyu zeminden aydinlik oldugunu sinar ve #fff bunu fazlasiyla
# saglar. Bir korumanin var olmasi yetmiyor; KACIRDIGI durumu
# sormak gerekiyor.
import test_tema_paleti as _tema  # noqa: E402

_KURALLAR = _tema.kok_kurallari(_tema._css())
#: Damgasiz okur -- yani ziyaretcilerin COGUNLUGU. Ekran paleti;
#: `baski=False` oldugu icin `@media print` kurallari HARIC.
ACIK = _tema.palet(_KURALLAR, False, None)
KOYU = _tema.palet(_KURALLAR, True, None)
esit(len(ACIK) > 10 and len(KOYU) > 10, True,
     f"iki tema jetonu okundu (acik {len(ACIK)}, koyu {len(KOYU)})")
# BASKI PALETI SIZMADI. Yukaridaki kusurun dogrudan bekcisi: kagit
# sifirlamasi saf beyaz/siyah kullaniyor ve sayfa paleti kullanmiyor.
esit(ACIK["--zemin"] != "#fff" and ACIK["--yazi"] != "#000", True,
     "acik palet BASKI blogundan gelmiyor")
# Etiketler DOGRU mu: acik temanin zemini gercekten acik olmali.
# Olculdu: ilk taramada `:root` blogunu "acik tema" diye etiketlemistim
# ve dogru cikti -- ama dogrulamadan gecmek, etiket kaydiginda butun
# sonuclari sessizce tersine cevirirdi.
esit(isik(rgb(ACIK["--zemin"])) > isik(rgb(KOYU["--zemin"])), True,
     "acik temanin zemini koyu temadan DAHA AYDINLIK (etiketler dogru)")


def coz(ad: str, jeton: dict[str, str], derin: int = 0) -> str | None:
    d = (jeton.get(ad) or "").strip()
    if derin > 6:
        return None
    if d.startswith("#"):
        return d
    m = re.match(r"var\(\s*(--[\w-]+)", d)
    return coz(m.group(1), jeton, derin + 1) if m else None


#: (aciklama, on plan jetonu, arka plan jetonu, esik)
CIFTLER = [
    ("govde yazisi / sayfa", "--yazi", "--zemin", AA_NORMAL),
    ("ikincil yazi / sayfa", "--yazi-2", "--zemin", AA_NORMAL),
    ("ucuncul yazi / sayfa", "--yazi-3", "--zemin", AA_NORMAL),
    ("govde yazisi / panel", "--yazi", "--panel", AA_NORMAL),
    ("ikincil yazi / panel", "--yazi-2", "--panel", AA_NORMAL),
    ("ucuncul yazi / panel", "--yazi-3", "--panel", AA_NORMAL),
    # `a { color: var(--vurgu) }` -- BUTUN baglantilar, normal punto.
    ("BAGLANTI / sayfa", "--vurgu", "--zemin", AA_NORMAL),
    ("BAGLANTI / panel", "--vurgu", "--panel", AA_NORMAL),
    # Sinyal renkleri sayi ve etiketlerde, normal puntoda kullaniliyor.
    ("artis / sayfa", "--artis", "--zemin", AA_NORMAL),
    ("azalis / sayfa", "--azalis", "--zemin", AA_NORMAL),
    ("uyari / sayfa", "--uyari", "--zemin", AA_NORMAL),
    ("artis / panel", "--artis", "--panel", AA_NORMAL),
    ("azalis / panel", "--azalis", "--panel", AA_NORMAL),
    ("uyari / panel", "--uyari", "--panel", AA_NORMAL),

    # --- 2026-10-04'TE EKLENEN CIFTLER ----------------------------
    # Hepsi sitede GERCEKTEN kullanilan ama bu listede OLMAYAN
    # ciftlerdi. Yukarida "baski paleti sizmasi" olayinin dersi
    # buydu zaten: bir korumanin VAR OLMASI yetmiyor, NEYE
    # BAKMADIGINI sormak gerekiyor. Liste o soruyla genisletildi.

    # `--zit-yazi` vurgu zeminli her seyin yazisi: ust bardaki
    # "Uye ol", `.dugme-mini`, `.asama-no`, `.sp-yerel`. OLCULDU:
    # jeton KOYU blokta hic tanimli degildi, tabandan (#ffffff)
    # dusuyordu ve koyu temada vurgu parlak turkuaz -- oran 1,87.
    # Yani o dugmelerin yazisi koyu temada okunmuyordu.
    ("zit yazi / vurgu", "--zit-yazi", "--vurgu", AA_NORMAL),
    # `.sondakika-etiket` AZALIS zeminli, ayni jetonla yaziliyor.
    ("zit yazi / azalis", "--zit-yazi", "--azalis", AA_NORMAL),

    # `--notr` "degismedi" sinyali; seritte ve fiyat kutularinda
    # yesil/kirmizinin YANINDA, ayni puntoda okunuyor.
    ("notr / sayfa", "--notr", "--zemin", AA_NORMAL),
    ("notr / cokuk yuzey", "--notr", "--zemin-2", AA_NORMAL),
    ("notr / panel", "--notr", "--panel", AA_NORMAL),

    # COKUK YUZEY: rozet, girdi alani, ilerleme cubugu zeminleri --
    # 33 yerde zemin olarak kullaniliyor ama tek cift sinanmiyordu.
    ("BAGLANTI / cokuk yuzey", "--vurgu", "--zemin-2", AA_NORMAL),
    ("ikincil yazi / cokuk", "--yazi-2", "--zemin-2", AA_NORMAL),
    ("ucuncul yazi / cokuk", "--yazi-3", "--zemin-2", AA_NORMAL),
    ("ucuncul yazi / panel-2", "--yazi-3", "--panel-2", AA_NORMAL),

    # UST SERIT her iki temada da AYNI koyu zemin tasiyor; yazisi
    # sayfa paletinden DEGIL, kendi jetonlarindan geliyor.
    ("ust yazi / ust serit", "--ust-yazi", "--ust-zemin", AA_NORMAL),
    ("ust ikincil / ust serit", "--ust-yazi-2", "--ust-zemin", AA_NORMAL),
]

for _tema_ad, _j in (("ACIK", ACIK), ("KOYU", KOYU)):
    print(f"\n{_tema_ad} tema")
    _dusuk = []
    for _ad, _on, _arka, _esik in CIFTLER:
        _c1, _c2 = coz(_on, _j), coz(_arka, _j)
        _r1, _r2 = rgb(_c1 or ""), rgb(_c2 or "")
        if not _r1 or not _r2:
            print(f"    ATLANDI  {_ad}  ({_on}={_c1}, {_arka}={_c2})")
            continue
        _o = oran(_r1, _r2)
        if _o < _esik:
            _dusuk.append((_ad, _c1, _c2, round(_o, 2), _esik))
    if _dusuk:
        print("\n  ESIGIN ALTINDA:")
        for _d in _dusuk:
            print(f"    {_d[0]:<24} {_d[1]} / {_d[2]}  =  {_d[3]}"
                  f"  (esik {_d[4]})")
    esit(_dusuk, [], f"{_tema_ad.lower()} temada butun ciftler AA gecer"
                     f" ({len(CIFTLER)} cift)")

print("\nMarka ile sinyal rengi ayirt edilebiliyor")
# `stil.css`te yazili karar: marka yesil "artis" sinyaliyle
# karistirilmasin, yoksa okur "yesil = artis" ile "yesil = Netaris"
# arasinda ayrim yapamaz.
#
# ESIK 20 -> 45 DERECE (2026-10-04). Eskisi fiilen HICBIR SEY
# ELEMIYORDU: olculen deger 26 derece idi ve iki renk ayni
# doygunlukta (%85) ve ayni aydinlikta (%26 / %27) duruyordu --
# yani aralarindaki TEK fark tondu, o da goz icin ayirt
# edilemeyecek kadar azdi. Sinama "gecti" diyordu cunku esik,
# gercekte karsilasilan degerin ALTINA birakilmisti. Gecen bir
# sinama, sinanan seyin DOGRU oldugunu gostermez -- yalnizca
# esigin asilmadigini gosterir.
#
# IKI TEMA DA OLCULUYOR. Onceki surum yalnizca ACIK paleti
# okuyordu. Koyu temada vurgu #2dd4bf (173 derece) ve artis
# #3ecf8e (156 derece) idi: 17 DERECE, yani kendi esiginin bile
# ALTINDA -- ve kimse gormedi, cunku o palet HIC olculmuyordu.
# Bir korumanin var olmasi yetmiyor; NEYE BAKMADIGINI sormak
# gerekiyor.
_ESIK_TON = 45
for _tad, _p in (("acik", ACIK), ("koyu", KOYU)):
    _mark, _art = coz("--vurgu", _p), coz("--artis", _p)
    _fark = abs(ton(_mark) - ton(_art))
    _fark = min(_fark, 360 - _fark)
    esit(_fark >= _ESIK_TON, True,
         f"{_tad}: marka ({_mark}) / artis ({_art}) arasi"
         f" {_fark:.1f} derece (esik {_ESIK_TON})")


print(chr(10) + "Konu renkleri yon renklerini KULLANMIYOR")
# `stil.css`in ILK SAYFASINDAKI kural, bu dosyadaki her seyden once
# gelir ve kesindir:
#
#   "YESIL VE KIRMIZI YALNIZCA SAYISAL YON ICINDIR. Arayuzun baska
#    hicbir yerinde kullanilmaz: buton, etiket, baglanti, uyari...
#    hicbiri. Okur bu iki rengi gordugunde her zaman 'bir rakam
#    degisti' diye okumali."
#
# OLCULDU (2026-10-04): kart TURU renkleri o kurali cigniyordu ve bu,
# benzerlik degil AYNILIK duzeyindeydi --
#
#   --t-jeopolitik  #c8203a  = o gunku --azalis ile BAYT BAYT AYNI
#   --t-sektor      #0a7f47  = o gunku --artis  ile BAYT BAYT AYNI
#   --t-sirket      #0a7f6b  = markanin bir tonu
#
# Yani okur, jeopolitik bir haberin seridini "dusus" diye
# okuyabiliyordu. Kural dosyanin basinda YAZILIYDI; uygulayan hicbir
# sey YOKTU. Bu depodaki en pahali kusur sinifi tam olarak bu:
# yazilmis ama zorlanmamis kural.
#
# Konu renkleri yalnizca ince sol seritlerde kullaniliyor (7 yerde
# `border-left`), bu yuzden AA araniyor DEGIL -- aranan sey, yon ve
# marka tonlarindan YETERINCE UZAK durmalari.
_YON_TONLARI = ("--artis", "--azalis", "--vurgu", "--uyari")
_KONULAR = ("--t-makro", "--t-duzenleme", "--t-jeopolitik", "--t-piyasa",
            "--t-sirket", "--t-sektor", "--t-emtia", "--t-haber")
#: Ton ayrimi DOYGUNLUGU dusuk renkler icin anlamsiz: %6 doygunluktaki
#: bir gri, tonu ne olursa olsun "kirmizi" diye okunmaz. Esik bu yuzden
#: yalnizca doygun renklere uygulaniyor -- aksi halde her notr gri,
#: tonu uyariya yakin diye kirmizi yanardi ve kural anlamini yitirirdi.
_DOYGUNLUK_ESIGI = 0.20
_TON_ESIGI = 30


def doygunluk(renk: str) -> float:
    return colorsys.rgb_to_hls(*[v / 255 for v in rgb(renk)])[2]


for _tad, _p in (("acik", ACIK), ("koyu", KOYU)):
    _carpisma = []
    for _k in _KONULAR:
        _kr = coz(_k, _p)
        if not _kr or doygunluk(_kr) < _DOYGUNLUK_ESIGI:
            continue
        for _y in _YON_TONLARI:
            _yr = coz(_y, _p)
            if not _yr:
                continue
            if _kr.lower() == _yr.lower():
                _carpisma.append(f"{_k} {_kr} == {_y}  (AYNI RENK)")
                continue
            _d = abs(ton(_kr) - ton(_yr))
            _d = min(_d, 360 - _d)
            if _d < _TON_ESIGI:
                _carpisma.append(f"{_k} {_kr} / {_y} {_yr}: {_d:.0f} derece")
    if _carpisma:
        print(chr(10) + "  CAKISMA:")
        for _c in _carpisma:
            print(f"    {_c}")
    esit(_carpisma, [], f"{_tad}: konu renkleri yon/marka tonlarindan"
                        f" en az {_TON_ESIGI} derece uzak")

# Konular BIRBIRINDEN de ayirt edilebilmeli -- yoksa renk bilgi
# tasimaz, yalnizca gurultu ekler. Dusuk doygunlukta olanlar kiyasin
# DISINDA: onlar zaten "notr" rolunde ve kromatik komsulariyla
# karismazlar.
for _tad, _p in (("acik", ACIK), ("koyu", KOYU)):
    _doygun = [(_k, coz(_k, _p)) for _k in _KONULAR
               if coz(_k, _p) and doygunluk(coz(_k, _p)) >= _DOYGUNLUK_ESIGI]
    _yakin = []
    for _i in range(len(_doygun)):
        for _j in range(_i + 1, len(_doygun)):
            _a, _b = _doygun[_i], _doygun[_j]
            _d = abs(ton(_a[1]) - ton(_b[1]))
            _d = min(_d, 360 - _d)
            if _d < 18:
                _yakin.append(f"{_a[0]} {_a[1]} / {_b[0]} {_b[1]}: {_d:.0f}")
    esit(_yakin, [], f"{_tad}: doygun konu renkleri birbirinden >= 18 derece")


print(f"\nTUM TESTLER GECTI ({_gecti})")
