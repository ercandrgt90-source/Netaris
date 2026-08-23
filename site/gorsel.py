"""Yaziya ozel gorsel uretir -- SVG, sayfaya gomulu, harici dosya yok.

NEDEN BOYLE
-----------
Stok fotograf kullanmiyoruz: lisans sorunu cikarir, konuyla ilgisi
gorsel yalandir ("petrol haberine varil fotografi" bilgi tasimaz), ve
harici istek KVKK tarafinda anlatilacak is acar.

Sirket amblemi de kullanmiyoruz: marka hakki baskasinin.

Bunun yerine gorsel **yazinin kendi rakamlarindan** ciziliyor. TERA
analizinin gorselinde TERA'nin gercek buyume rakamlari var; petrol
yazisinin gorselinde Brent'in gercek fiyat serisi. Gorsel sussuz bir
ozet -- bakinca veriyi goruyorsun.

Cikti SVG oldugu icin her boyutta net, dosya boyutu birkac kilobayt ve
sayfaya dogrudan gomuluyor: sifir ek istek.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

# Tema renkleri -- stil.css :root degerleriyle AYNI olmali. Ayrisirsa
# gorsel sayfadan kopuk durur.
#
# ACIK TEMA: gorsel zemini saf beyaz DEGIL, bir ton gri. Beyaz zeminli bir
# gorsel beyaz sayfada sinirsiz kalir ve "gorsel var mi yok mu" belli olmaz.
ZEMIN = "#eef2f8"
CIZGI = "#d3dcea"
VURGU = "#0a7ea4"
VURGU_KOYU = "#075c78"
YAZI = "#0f1b2d"
YAZI_3 = "#6b7c96"
ARTIS = "#0f8a4d"
AZALIS = "#cf2740"

# 16:9. Kart kutusu 16:9 oldugu icin gorsel de 16:9 uretilir.
# Onceden 1200x480 (2,5:1) uretiliyordu ve kart icinde yanlardan
# kirpiliyordu -- sagdaki son deger yazisi kesiliyordu. Ayni oranda
# uretince kirpma da gerekmiyor.
GEN = 1200
YUK = 675

#: Cizim alani sinirlari -- basliklar ustte, eksen altta
UST = 235
ALT = 560


@dataclass
class Nokta:
    etiket: str
    deger: float


def _kacis(m: str) -> str:
    return html.escape(m, quote=True)


def _zemin(kod_filigran: str = "") -> str:
    """Ortak zemin: gradyan, izgara ve isteğe bagli kod filigrani."""
    parcalar = [
        f'<rect width="{GEN}" height="{YUK}" fill="{ZEMIN}"/>',
        f'<rect width="{GEN}" height="{YUK}" fill="url(#parlama)"/>',
    ]
    # Ince izgara
    for x in range(0, GEN + 1, 60):
        parcalar.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{YUK}" stroke="{CIZGI}" '
            f'stroke-width="1" opacity="0.35"/>'
        )
    for y in range(0, YUK + 1, 60):
        parcalar.append(
            f'<line x1="0" y1="{y}" x2="{GEN}" y2="{y}" stroke="{CIZGI}" '
            f'stroke-width="1" opacity="0.35"/>'
        )
    if kod_filigran:
        parcalar.append(
            f'<text x="{GEN - 50}" y="{YUK - 46}" text-anchor="end" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="170" '
            f'font-weight="800" fill="{VURGU}" opacity="0.08" '
            f'letter-spacing="7">{_kacis(kod_filigran)}</text>'
        )
    return "".join(parcalar)


def _tanimlar() -> str:
    return (
        "<defs>"
        '<radialGradient id="parlama" cx="50%" cy="0%" r="90%">'
        f'<stop offset="0%" stop-color="#dce6f2" stop-opacity="0.9"/>'
        f'<stop offset="100%" stop-color="{ZEMIN}" stop-opacity="0"/>'
        "</radialGradient>"
        '<linearGradient id="sutun" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0%" stop-color="{VURGU_KOYU}"/>'
        f'<stop offset="100%" stop-color="{VURGU}"/>'
        "</linearGradient>"
        '<linearGradient id="cizgiDolgu" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{VURGU}" stop-opacity="0.28"/>'
        f'<stop offset="100%" stop-color="{VURGU}" stop-opacity="0"/>'
        "</linearGradient>"
        "</defs>"
    )


def _sar(govde: str, baslik_metni: str) -> str:
    # "meet" kullaniliyor, "slice" degil: slice kutuyu doldurmak icin
    # gorseli kirpiyor ve kenardaki sayi yazilarini yiyordu.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GEN} {YUK}" '
        f'role="img" aria-label="{_kacis(baslik_metni)}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f"{_tanimlar()}{govde}</svg>"
    )


_BUYUK = str.maketrans({"i": "İ", "ı": "I"})


def _tr_sayi(d: float, basamak: int = 2) -> str:
    """Turkce sayi: binlik nokta, ondalik virgul.

    Zincirleme replace ile yapilmaz -- '1,234.56' uzerinde once virgulu
    noktaya cevirmek '1.234.56' uretir. Ara isaret uzerinden gidilir.
    """
    return f"{d:,.{basamak}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _kirp(metin: str, en_fazla: int) -> str:
    """Uzun metni gorsele sigacak sekilde kisaltir.

    Kart icinde gorsel kucuk gorunuyor; sigmayan baslik ya tasiyor ya da
    okunmuyor. Kirpmak, tasan metinden iyi.
    """
    metin = metin.strip()
    return metin if len(metin) <= en_fazla else metin[: en_fazla - 1].rstrip() + "…"


def _buyut(metin: str) -> str:
    """Buyuk harfe cevirir -- ama YABANCI ADLARI Turkce kuralla bozmadan.

    "Bitcoin" Turkce kuralla "BİTCOİN" olur; kural dogru ama yabanci bir
    marka adinda yanlis durur. Kural: metinde Turkce'ye ozgu harf varsa
    Turkce buyutme, yoksa duz buyutme uygulanir.
    """
    if any(h in metin for h in "ıİşŞğĞüÜöÖçÇ"):
        return metin.translate(_BUYUK).upper()
    return metin.upper()


def _ust_yazi(ust: str, alt: str) -> str:
    """Sol ustte kategori ve konu etiketi."""
    return (
        f'<text x="56" y="86" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="24" font-weight="700" fill="{VURGU}" '
        f'letter-spacing="3.5">{_kacis(_kirp(_buyut(ust), 30))}</text>'
        f'<text x="56" y="142" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="42" font-weight="800" fill="{YAZI}" '
        f'letter-spacing="-0.8">{_kacis(_kirp(alt, 34))}</text>'
    )


# ---------------------------------------------------------------------------
# Sutun grafigi -- bilanco buyume kalemleri
# ---------------------------------------------------------------------------

def sutun_grafik(kod: str, konu: str, noktalar: list[Nokta]) -> str:
    """Buyume kalemlerini sutun olarak cizer.

    Negatif degerler sifir cizgisinin altina iner ve kirmiziya doner --
    yonun rengini degistirmek, okurun rakami okumadan once yonu gormesini
    saglar.
    """
    if not noktalar:
        return genel(konu, kod)

    sol, sag = 70, GEN - 70
    tepe, taban = UST, ALT
    alan = sag - sol
    n = len(noktalar)
    bosluk = alan / n
    kalinlik = min(104.0, bosluk * 0.52)

    en_buyuk = max(abs(p.deger) for p in noktalar) or 1.0
    # Sifir cizgisi: negatif varsa ortaya yakin, yoksa tabana
    negatif_var = any(p.deger < 0 for p in noktalar)
    sifir_y = (tepe + taban) / 2 if negatif_var else taban
    olcek = (taban - tepe) / (2 * en_buyuk) if negatif_var else (taban - tepe) / en_buyuk

    p: list[str] = [_zemin(kod), _ust_yazi(kod or "ANALİZ", konu)]

    p.append(
        f'<line x1="{sol}" y1="{sifir_y:.1f}" x2="{sag}" y2="{sifir_y:.1f}" '
        f'stroke="{CIZGI}" stroke-width="2"/>'
    )

    for i, nokta in enumerate(noktalar):
        merkez = sol + bosluk * (i + 0.5)
        x = merkez - kalinlik / 2
        h = abs(nokta.deger) * olcek
        h = max(h, 3.0)
        pozitif = nokta.deger >= 0
        y = sifir_y - h if pozitif else sifir_y
        renk = "url(#sutun)" if pozitif else AZALIS

        # Sutun: govde + isik alan sol yuz + ust kapak -- duz dikdortgen
        # yerine hacimli dursun
        p.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{kalinlik:.1f}" '
            f'height="{h:.1f}" rx="6" fill="{renk}"/>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{kalinlik * 0.32:.1f}" '
            f'height="{h:.1f}" rx="6" fill="#ffffff" opacity="0.22"/>'
        )
        if pozitif and h > 14:
            p.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{kalinlik:.1f}" '
                f'height="8" rx="4" fill="#ffffff" opacity="0.4"/>'
            )
        # Deger etiketi
        deger_y = y - 20 if pozitif else y + h + 36
        isaret = "+" if pozitif else "−"
        metin = f"{isaret}%{abs(nokta.deger):.0f}".replace(".", ",")
        p.append(
            f'<text x="{merkez:.1f}" y="{deger_y:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="28" '
            f'font-weight="800" fill="{YAZI if pozitif else AZALIS}">{metin}</text>'
        )
        # Kalem adi
        p.append(
            f'<text x="{merkez:.1f}" y="{YUK - 42}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="22" '
            f'fill="{YAZI_3}">{_kacis(_kirp(nokta.etiket, 15))}</text>'
        )

    return _sar("".join(p), f"{kod} {konu} — reel değişim grafiği")


# ---------------------------------------------------------------------------
# Cizgi grafigi -- makro seri
# ---------------------------------------------------------------------------

def cizgi_grafik(baslik: str, konu: str, degerler: list[float],
                 birim: str = "") -> str:
    """Zaman serisini cizgi olarak cizer, altini gradyanla doldurur."""
    if len(degerler) < 2:
        return genel(konu, baslik)

    sol, sag = 70, GEN - 70
    tepe, taban = UST + 20, ALT

    dip, zirve = min(degerler), max(degerler)
    aralik = (zirve - dip) or 1.0
    n = len(degerler)
    adim = (sag - sol) / (n - 1)

    def y_of(v: float) -> float:
        return taban - (v - dip) / aralik * (taban - tepe)

    noktalar = [(sol + i * adim, y_of(v)) for i, v in enumerate(degerler)]
    cizgi = " ".join(f"{x:.1f},{y:.1f}" for x, y in noktalar)
    dolgu = (
        f"{sol},{taban} "
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in noktalar)
        + f" {sag},{taban}"
    )

    yukseldi = degerler[-1] >= degerler[0]
    son_renk = ARTIS if yukseldi else AZALIS

    p: list[str] = [_zemin(), _ust_yazi(baslik, konu)]
    p.append(f'<polygon points="{dolgu}" fill="url(#cizgiDolgu)"/>')
    p.append(
        f'<path d="M{sol} {taban} H{sag}" stroke="{CIZGI}" stroke-width="3"/>'
        f'<polyline points="{cizgi}" fill="none" stroke="{VURGU}" '
        f'stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Zirve ve dip isaretleri
    for deger, etiket in ((zirve, "zirve"), (dip, "dip")):
        i = degerler.index(deger)
        x, y = sol + i * adim, y_of(deger)
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{YAZI_3}"/>')
        yer = y - 24 if etiket == "zirve" else y + 40
        p.append(
            f'<text x="{x:.1f}" y="{yer:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="21" '
            f'fill="{YAZI_3}">{_kacis(etiket)} {_tr_sayi(deger)}</text>'
        )

    # Son deger
    sx, sy = noktalar[-1]
    p.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="11" fill="{son_renk}"/>')
    p.append(
        f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="19" fill="none" '
        f'stroke="{son_renk}" stroke-width="3" opacity="0.4"/>'
    )
    son_metin = _tr_sayi(degerler[-1])
    if birim:
        son_metin += f" {birim}"
    # Son deger cizim alaninin USTUNDE, sag kosede -- cizgiyle cakismasin
    # ve kart icinde kirpilmasin
    p.append(
        f'<text x="{GEN - 56}" y="142" text-anchor="end" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="46" '
        f'font-weight="800" fill="{YAZI}">{_kacis(son_metin)}</text>'
    )

    return _sar("".join(p), f"{konu} — {baslik} seri grafiği")


# ---------------------------------------------------------------------------
# Genel gorsel -- veri yoksa
# ---------------------------------------------------------------------------

def genel(konu: str, etiket: str = "NETARIS") -> str:
    """Grafik verisi olmayan sayfalar icin sade zemin."""
    # DEKORATIF DALGA KALDIRILDI.
    # ---------------------------
    # Burada 25 noktali bir zikzak ciziliyordu ve yanindaki yorum
    # "soyut ama duzenli bir dalga -- veri iddiasi tasimaz" diyordu.
    #
    # Yazarken makul gorunmus olabilir; SONUCU oyle degil. Olculdu
    # (2026-08-23): 384 bilanco analizinin 298'inde `grafik:` alani
    # bostu ve bu cizim basiliyordu. Bir bilanco sayfasinda, hisse
    # kodunun altinda duran zikzak bir cizgi okur icin FIYAT
    # GRAFIGIDIR. Kullanicinin ilk tepkisi de tam buydu: "grafige
    # fiyatin gelmesi lazim" -- yani cizgi veri olarak okunmus.
    #
    # Bir cizimin "veri iddiasi tasimadigina" onu cizen karar veremez;
    # okuyan verir. Geriye sade zemin ve kimlik yazisi kaliyor.
    #
    # Gercek grafik nereden geliyor: `insa.govdeden_grafik` yazinin
    # govdesindeki "Reel degisim" tablosunu okuyor ve sutun grafigi o
    # rakamlardan ciziliyor.
    return _sar("".join([_zemin(etiket),
                         _ust_yazi(etiket or "NETARİS", konu)]), konu)


# ---------------------------------------------------------------------------
# Frontmatter'dan cizim
# ---------------------------------------------------------------------------

def coz_sutun(ham: str) -> list[Nokta]:
    """'Hasılat|40,0;Brüt kâr|23,2' -> [Nokta, ...]

    Ayrac NOKTALI VIRGUL. Turkce'de virgul ondalik ayracidir; liste ayraci
    olarak kullanmak sessizce yanlis sayi uretir. Bu tuzagi girdi
    dosyalarinda bir kez yasadik.
    """
    sonuc: list[Nokta] = []
    for parca in ham.split(";"):
        parca = parca.strip()
        if not parca or "|" not in parca:
            continue
        etiket, deger = parca.rsplit("|", 1)
        try:
            sonuc.append(Nokta(etiket.strip(), float(deger.strip().replace(",", "."))))
        except ValueError:
            continue
    return sonuc


def coz_cizgi(ham: str) -> list[float]:
    """'76,50;74,46;74,34' -> [76.5, 74.46, 74.34]"""
    degerler: list[float] = []
    for parca in ham.split(";"):
        parca = parca.strip()
        if not parca:
            continue
        try:
            degerler.append(float(parca.replace(",", ".")))
        except ValueError:
            continue
    return degerler


# Unvan sonundaki hukuki bicim ve genel tanimlayicilar. haber_botu tarafinda
# `bicim.kisa_ad` ayni isi daha genis yapiyor; buraya kucuk bir kopya
# konuyor cunku site ureteci haber_botu paketinden BAGIMSIZ calisabilmeli --
# icerik klasoru elden duzenlenip site tek basina insa edilebilmeli.
# "holding" ve "yatirim" bilincli olarak YOK: "Koç Holding", "Tera Yatırım"
# gunluk kullanilan adin kendisidir; atilirsa yanlis kisaltma cikar.
_ATILACAK = {
    "a.s.", "a.ş.", "a.o.", "t.a.s.", "t.a.ş.", "anonim", "sirketi", "şirketi",
    "sanayi", "sanayii", "ticaret", "menkul", "degerler", "değerler",
    "fabrikalari", "fabrikaları", "aracilik", "aracılık",
}
_KUCUK_TR = str.maketrans({"I": "ı", "İ": "i"})
_BUYUK_TR = str.maketrans({"i": "İ", "ı": "I"})


def kisa_unvan(unvan: str, en_fazla: int = 2) -> str:
    """Tam hukuki unvandan gorselde okunacak kisa adi uretir.

    'TERA YATIRIM MENKUL DEĞERLER A.Ş.' -> 'Tera Yatırım'

    KAP unvanlari tamamen buyuk harfle gelir; gorselde oldugu gibi birakmak
    bagirma etkisi yapar.
    """
    sozcukler = unvan.split()
    while sozcukler and sozcukler[-1].translate(_KUCUK_TR).lower() in _ATILACAK:
        sozcukler.pop()
    sozcukler = sozcukler[:en_fazla] or unvan.split()[:en_fazla]

    duzeltilmis = []
    for s in sozcukler:
        if s.isupper() and len(s) > 4 and "." not in s:
            kucuk = s.translate(_KUCUK_TR).lower()
            duzeltilmis.append(kucuk[0].translate(_BUYUK_TR).upper() + kucuk[1:])
        else:
            duzeltilmis.append(s)
    return " ".join(duzeltilmis)


# Haber gorseli: konuya gore renk ve simge. Fotograf ya da kurum amblemi
# KULLANILMAZ -- ilki lisans, ikincisi marka hakki sorunu cikarir. Gorsel
# konuyu isaret eden soyut bir kompozisyondur.
# Acik zemine gore koyulastirilmis konu renkleri
_KONU_GORSELI = {
    "Para politikası": ("#0a7ea4", "faiz"),
    "Enflasyon": ("#a45c00", "enflasyon"),
    "Enerji": ("#c2410c", "enerji"),
    "Bankacılık": ("#4338ca", "banka"),
    "Piyasa düzenlemesi": ("#0f8a4d", "duzenleme"),
    "Düzenleme": ("#0f8a4d", "duzenleme"),
}

_HABER_GEN, _HABER_YUK = 800, 450


def _koyu(renk: str, oran: float = 0.72) -> str:
    """Rengi koyultur -- golge ve derinlik icin."""
    r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * oran), int(g * oran), int(b * oran))


def _acik(renk: str, oran: float = 0.35) -> str:
    """Rengi beyaza dogru acar -- isik alan yuzeyler icin."""
    r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
    k = lambda v: int(v + (255 - v) * oran)  # noqa: E731
    return "#%02x%02x%02x" % (k(r), k(g), k(b))


def _simge(tur: str, renk: str) -> str:
    """Konuya ozgu kompozisyon.

    Duz cizgi ikonlar yerine KATMANLI sahneler: her nesnenin isik alan
    yuzu, golge alan yuzu ve zemine dusen golgesi var. Ayni SVG teknigi,
    ama sonuc ikondan cok editoryal cizim gibi duruyor -- kart icinde
    bakildiginda "bir sey cizilmis" degil "bir sahne var" hissi veriyor.
    """
    koyu = _koyu(renk)
    acik = _acik(renk)
    ekstra = _koyu(renk, 0.55)
    p: list[str] = []

    if tur == "enerji":
        # Petrol kulesi + varil + zemin -- katmanli sahne
        p.append(f'<ellipse cx="400" cy="368" rx="230" ry="18" fill="{koyu}" opacity="0.13"/>')
        # Kule iskeleti
        p.append(
            f'<path d="M250 350 L300 170 L340 170 L390 350 Z" fill="{acik}" opacity="0.55"/>'
            f'<path d="M320 350 L300 170 L340 170 L360 350 Z" fill="{renk}" opacity="0.9"/>'
            f'<path d="M262 305 h116 M274 262 h92 M286 218 h68" '
            f'stroke="{koyu}" stroke-width="5" opacity="0.65"/>'
            f'<rect x="292" y="146" width="56" height="26" rx="5" fill="{ekstra}"/>'
        )
        # Varil -- silindir govde, ust elips, seritler
        p.append(
            f'<rect x="452" y="216" width="128" height="134" rx="10" fill="{renk}"/>'
            f'<rect x="452" y="216" width="46" height="134" rx="10" fill="{acik}" opacity="0.5"/>'
            f'<ellipse cx="516" cy="216" rx="64" ry="17" fill="{acik}"/>'
            f'<ellipse cx="516" cy="216" rx="44" ry="11" fill="{koyu}" opacity="0.45"/>'
            f'<path d="M452 258 h128 M452 308 h128" stroke="{koyu}" '
            f'stroke-width="7" opacity="0.55"/>'
        )
        return "".join(p)

    if tur == "faiz":
        # Basamakli patika + sutunlar + isaret noktasi
        p.append(f'<ellipse cx="400" cy="368" rx="230" ry="18" fill="{koyu}" opacity="0.13"/>')
        basamaklar = ((230, 300), (300, 262), (370, 226), (440, 196), (510, 158))
        for i, (x, y) in enumerate(basamaklar):
            h = 350 - y
            p.append(
                f'<rect x="{x}" y="{y}" width="52" height="{h}" rx="5" '
                f'fill="{renk}" opacity="{0.35 + i * 0.16:.2f}"/>'
                f'<rect x="{x}" y="{y}" width="18" height="{h}" rx="5" '
                f'fill="{acik}" opacity="0.45"/>'
                f'<rect x="{x}" y="{y}" width="52" height="9" rx="4" fill="{acik}"/>'
            )
        p.append(
            f'<polyline points="256,300 326,262 396,226 466,196 536,158" '
            f'fill="none" stroke="{ekstra}" stroke-width="6" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>'
            f'<circle cx="536" cy="158" r="15" fill="{ekstra}"/>'
            f'<circle cx="536" cy="158" r="7" fill="{ZEMIN}"/>'
        )
        return "".join(p)

    if tur == "enflasyon":
        # Hizlanan egri + altinda dolgu + izgara
        p.append(f'<ellipse cx="400" cy="368" rx="230" ry="18" fill="{koyu}" opacity="0.13"/>')
        p.append(
            f'<path d="M200 350 L200 322 Q 320 316 400 250 T 600 122 L600 350 Z" '
            f'fill="{renk}" opacity="0.16"/>'
            f'<path d="M200 322 Q 320 316 400 250 T 600 122" fill="none" '
            f'stroke="{renk}" stroke-width="9" stroke-linecap="round"/>'
        )
        for x, y in ((200, 322), (400, 250), (600, 122)):
            p.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{ekstra}"/>')
            p.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{ZEMIN}"/>')
        p.append(f'<path d="M180 350 h440" stroke="{koyu}" stroke-width="4" opacity="0.35"/>')
        return "".join(p)

    if tur == "banka":
        # Sutunlu klasik cephe -- alinlik, sutunlar, basamak
        p.append(f'<ellipse cx="400" cy="372" rx="235" ry="16" fill="{koyu}" opacity="0.13"/>')
        p.append(
            f'<path d="M400 122 L590 208 L210 208 Z" fill="{renk}"/>'
            f'<path d="M400 122 L590 208 L400 208 Z" fill="{koyu}" opacity="0.4"/>'
            f'<rect x="196" y="208" width="408" height="20" rx="4" fill="{ekstra}"/>'
        )
        for i, x in enumerate((234, 306, 378, 450, 522)):
            p.append(
                f'<rect x="{x}" y="234" width="46" height="98" fill="{renk}" opacity="0.88"/>'
                f'<rect x="{x}" y="234" width="15" height="98" fill="{acik}" opacity="0.5"/>'
                f'<rect x="{x - 5}" y="228" width="56" height="10" rx="3" fill="{acik}"/>'
                f'<rect x="{x - 5}" y="330" width="56" height="10" rx="3" fill="{acik}"/>'
            )
        p.append(
            f'<rect x="186" y="340" width="428" height="13" rx="4" fill="{ekstra}"/>'
            f'<rect x="168" y="353" width="464" height="13" rx="4" fill="{koyu}" opacity="0.75"/>'
        )
        return "".join(p)

    # duzenleme -- terazi, katmanli
    p.append(f'<ellipse cx="400" cy="368" rx="180" ry="16" fill="{koyu}" opacity="0.13"/>')
    p.append(
        f'<rect x="392" y="140" width="16" height="200" rx="6" fill="{renk}"/>'
        f'<rect x="392" y="140" width="6" height="200" rx="3" fill="{acik}" opacity="0.6"/>'
        f'<rect x="262" y="180" width="276" height="14" rx="7" fill="{renk}"/>'
        f'<rect x="262" y="180" width="276" height="5" rx="3" fill="{acik}" opacity="0.6"/>'
        f'<circle cx="400" cy="130" r="18" fill="{ekstra}"/>'
    )
    for cx in (276, 524):
        p.append(
            f'<path d="M{cx} 194 v26" stroke="{koyu}" stroke-width="4" opacity="0.6"/>'
            f'<path d="M{cx - 54} 220 h108 l-30 46 h-48 z" fill="{renk}" opacity="0.9"/>'
            f'<path d="M{cx - 54} 220 h108 l-12 18 h-84 z" fill="{acik}" opacity="0.55"/>'
        )
    p.append(
        f'<rect x="330" y="340" width="140" height="16" rx="6" fill="{ekstra}"/>'
        f'<rect x="310" y="356" width="180" height="12" rx="5" fill="{koyu}" opacity="0.75"/>'
    )
    return "".join(p)


def haber_gorseli(konu: str, kurum: str, baslik: str) -> str:
    """Gundem haberi icin gorsel uretir -- konudan turer, fotograf yok."""
    renk, tur = _KONU_GORSELI.get(konu, ("#38dcf5", "duzenleme"))
    g, y = _HABER_GEN, _HABER_YUK

    p = [f'<rect width="{g}" height="{y}" fill="{ZEMIN}"/>']
    for x in range(0, g + 1, 50):
        p.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{y}" stroke="{CIZGI}" '
                 f'stroke-width="1" opacity="0.4"/>')
    for yy in range(0, y + 1, 50):
        p.append(f'<line x1="0" y1="{yy}" x2="{g}" y2="{yy}" stroke="{CIZGI}" '
                 f'stroke-width="1" opacity="0.4"/>')
    p.append(
        f'<circle cx="{g // 2}" cy="{y // 2 - 10}" r="185" fill="{renk}" '
        f'opacity="0.06"/>'
    )
    p.append(_simge(tur, renk))
    p.append(
        f'<text x="40" y="55" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="17" font-weight="700" fill="{renk}" letter-spacing="2.5">'
        f'{_kacis(_buyut(konu))}</text>'
    )
    p.append(
        f'<text x="40" y="{y - 30}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="17" fill="{YAZI_3}">{_kacis(kurum)}</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {g} {y}" '
        f'role="img" aria-label="{_kacis(konu)} — {_kacis(kurum)}" '
        f'preserveAspectRatio="xMidYMid slice">{"".join(p)}</svg>'
    )


def uret(tur: str, ham: str, kod: str, konu: str, birim: str = "") -> str:
    """Frontmatter alanlarindan gorsel uretir."""
    if tur == "sutun":
        # Ust satirda zaten hisse kodu var; altta tam unvani tekrarlamak
        # yerine kisa ad yaziliyor
        return sutun_grafik(kod, kisa_unvan(konu), coz_sutun(ham))
    if tur == "cizgi":
        return cizgi_grafik(kod or "GÖSTERGE", konu, coz_cizgi(ham), birim)
    return genel(konu, kod)
