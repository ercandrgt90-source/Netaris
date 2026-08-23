"""Bilanco sayfalari icin SIRKET AMBLEMI -- stok fotograf yerine.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-08-23): 384 bilanco analizinin HEPSINDE konu havuzundan
gelen bir stok fotograf vardi. Havuz konuya gore secim yapiyor, sirkete
gore degil; sonuc "Gayrimenkul" analizinin ustunde rastgele bir bina
fotografi oluyordu. Okurun sorusu ("bu hangi sirket") ile gordugu sey
(bir bina) arasinda hicbir bag yoktu.

Kullanici geri bildirimi acikti: "bilancolarda sirket logosu ve amblemi
kullan ki alakasiz fotograf payi kalmasin".

NEDEN GERCEK LOGO DEGIL
-----------------------
Sirket logolari TESCILLI MARKA. Haber baglaminda tanitici kullanim
genellikle mesru sayilir, ama:

  * guvenilir ve toplu bir kaynak yok -- sirket sitelerinden cekmek
    her sirket icin ayri kullanim kosulu demek,
  * Wikipedia'daki logolar "adil kullanim" gerekcesiyle duruyor ve o
    gerekce BIZE GECMIYOR (ayni tuzak fiyat serilerinde de yasandi),
  * 500+ BIST sirketi icin bunu tek tek dogrulamak surdurulemez.

Bu yuzden amblem KENDI URETTIGIMIZ bir isaret: sirketin BIST kodu,
sektor rengiyle birlikte. Lisans sorunu yok, her sirkette calisiyor,
ve en onemlisi HICBIR ZAMAN ALAKASIZ olmuyor -- gosterdigi sey tam
olarak sayfanin konusu.

NEDEN SAHTE GRAFIK YOK
----------------------
Amblemde susleme olarak grafik cizgisi kullanilmiyor. Bu depoda kural
zaten yazili: temsili ya da uydurma bir grafik cizilmez. Sayfadaki
grafik yazinin KENDI rakamlarindan uretiliyor ve amblemin onu taklit
etmesi o ayrimi bulandirirdi.
"""

from __future__ import annotations

import html
import re

#: Sektor -> zemin rengi.
#:
#: Renkler bilincli olarak DOYGUN DEGIL: amblem sayfanin en dikkat
#: ceken ogesi olmamali, konu basligi ve rakamlar ondan once okunmali.
#: Her renk beyaz yazi ile en az 4.5:1 karsitlik veriyor (WCAG AA).
SEKTOR_RENGI: dict[str, str] = {
    "Finans": "#1f4e79",
    "Aracı kurum": "#414a6b",
    "Sanayi": "#4f555c",
    "Gayrimenkul": "#6f5439",
    "Kamu hizmetleri": "#2b6157",
    "Bilişim": "#39447e",
    "İsteğe bağlı tüketim": "#7f4436",
    "Temel tüketim": "#45602c",
    "Temel malzeme": "#63532c",
    "Sağlık": "#2b6070",
    "Enerji": "#7d5f1c",
}

#: Sektoru bilinmeyen sirket. Rastgele renk ATANMIYOR: renk burada bir
#: BILGI (sektor), susleme degil. Bilinmiyorsa notr kaliyor ve okur
#: yanlis bir gruplama cikarimi yapmiyor.
NOTR = "#39424e"


def renk(sektor: str) -> str:
    return SEKTOR_RENGI.get((sektor or "").strip(), NOTR)


_KOD = re.compile(r"[A-Z0-9]{2,6}")


def kod_metni(kod: str, sirket: str = "") -> str:
    """Amblemde yazacak kisa isaret.

    Once BIST kodu; yoksa sirket adinin bas harfleri. Ikisi de yoksa
    bos donuyor ve cagiran taraf amblem BASMIYOR -- icinde bir sey
    yazmayan renkli bir kutu, hicbir seyden kotudur.
    """
    k = (kod or "").strip().upper()
    m = _KOD.fullmatch(k)
    if m:
        return k
    ad = (sirket or "").strip()
    if not ad:
        return ""
    # "Türk Hava Yolları A.O." -> "THY"
    atla = {"A.Ş.", "AŞ", "A.O.", "T.A.Ş.", "VE", "SANAYİ", "TİCARET",
            "HOLDİNG", "ANONİM", "ŞİRKETİ"}
    # TEK HARFLI PARCALAR DUSUYOR. "A.Ş." ve "A.O." nokta ayiricisiyla
    # "A" + "S" / "A" + "O" haline geliyor ve `atla` kumesine
    # yakalanmiyordu: "Türk Hava Yolları A.O." -> "THYA" cikiyordu.
    parca = [p for p in re.split(r"[\s.]+", ad.upper())
             if len(p) > 1 and p not in atla]
    bas = "".join(p[0] for p in parca[:4])
    return bas if len(bas) >= 2 else ""


def amblem(kod: str, sirket: str = "", sektor: str = "",
           donem: str = "") -> str:
    """Sirket amblemini SVG olarak dondurur (satir ici basilir).

    Satir ici basiliyor cunku: ek istek yok, `currentColor` ve tema
    degiskenleri calisiyor, ve dosya yonetimi gerekmiyor. 384 sayfa
    icin 384 ayri dosya uretmek, hicbir sey kazandirmadan depoyu
    sisirirdi.
    """
    metin = kod_metni(kod, sirket)
    if not metin:
        return ""

    zemin = renk(sektor)
    # Kod uzadikca punto kuculuyor -- 6 harfli kod kutuya sigmali.
    punto = {2: 132, 3: 124, 4: 108, 5: 92, 6: 78}.get(len(metin), 92)

    ad = html.escape((sirket or "").strip())
    alt = html.escape(" · ".join(x for x in ((sektor or "").strip(),
                                             (donem or "").strip()) if x))
    etiket = html.escape(f"{metin} amblemi")

    alt_satir = ""
    if ad:
        alt_satir += (
            f'<text x="600" y="286" text-anchor="middle" fill="#ffffff" '
            f'fill-opacity="0.88" font-size="34" font-weight="600" '
            f'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif"'
            f'>{ad[:46]}</text>'
        )
    if alt:
        alt_satir += (
            f'<text x="600" y="330" text-anchor="middle" fill="#ffffff" '
            f'fill-opacity="0.62" font-size="24" font-weight="500" '
            f'letter-spacing="1.6" '
            f'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif"'
            f'>{alt[:60]}</text>'
        )

    return (
        f'<svg class="amblem" viewBox="0 0 1200 400" width="1200" '
        f'height="400" role="img" aria-label="{etiket}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="1200" height="400" fill="{zemin}"/>'
        # Tek bir ince ust cizgi: kutuyu sayfadan ayiriyor, sus degil.
        f'<rect width="1200" height="4" fill="#ffffff" fill-opacity="0.22"/>'
        f'<text x="600" y="{200 if not alt_satir else 186}" '
        f'text-anchor="middle" dominant-baseline="middle" fill="#ffffff" '
        f'font-size="{punto}" font-weight="800" letter-spacing="{
            2 if len(metin) > 4 else 6}" '
        f'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif"'
        f'>{html.escape(metin)}</text>'
        f'{alt_satir}'
        f'</svg>'
    )
