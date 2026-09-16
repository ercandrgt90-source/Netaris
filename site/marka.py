"""NETARIS MARKA ISARETI -- PNG uretici.

BU DOSYA NEDEN VAR
------------------
Marka isareti yalnizca `temel.html` icinde bir `data:` URI olarak
yasiyordu. Tarayicida calisiyor, ARAMA SONUCUNDA calismiyor.

Google'in favicon sartlari acik (developers.google.com, favicon-in-search):

  * "Google Search supports the following favicon file formats: BMP,
    GIF, ICO, PNG, JPEG, PPM, and TIFF."   -> SVG DESTEKLENMIYOR
  * "The favicon URL must be stable"       -> `data:` URI bir adres degil
  * "Googlebot-Image must be able to crawl the favicon file"
                                           -> `data:` URI taranamaz
  * kare, en az 8x8; 48x48'ten buyugu oneriliyor

Organization logosu icin ayri sart (structured-data/logo):

  * "The image must be 112x112px, at minimum."
  * "The image URL must be crawlable and indexable."
  * "Make sure the image looks how you intend it to look on a purely
    white background"  -> isaret kendi koyu karesini tasiyor, beyazda
    da kendi basina duruyor.

NEDEN YENI BAGIMLILIK YOK
-------------------------
`requirements.txt` bilincli olarak kucuk: "her yeni bagimlilik,
kirilabilecek yeni bir parca demek". Pillow/cairosvg eklemek yerine
isaret burada CIZILIYOR: PNG bicimi zlib + birkac parcadan ibaret ve
`zlib` standart kutuphanede. Isaret de basit geometri -- yuvarlak
kare, bir kirik cizgi, iki cubuk.

CIKTI DEPOYA GIRIYOR, HER KURULUMDA URETILMIYOR. Sebep Google'in
kendi sarti: adres SABIT olmali. Her kurulumda yeniden uretmek hem
gereksiz, hem de bir gun dosya adini degistirme riski.

Kullanim:  python site/marka.py
"""

from __future__ import annotations

import math
import pathlib
import struct
import zlib

KOK = pathlib.Path(__file__).resolve().parent
HEDEF = KOK / "statik" / "marka"

# --------------------------------------------------------------------
# ISARETIN GEOMETRISI -- `temel.html`deki SVG ile AYNI.
#
# Koordinatlar 32x32'lik SVG viewBox'inda; olcek carpani ile buyutuluyor.
# Tek kaynak olmasi icin degerler burada TEK YERDE duruyor; SVG
# degisirse burasi da degismeli (sinama ikisini karsilastiriyor).
# --------------------------------------------------------------------

TUVAL = 32.0
ZEMIN = (0x0b, 0x10, 0x18)          # #0b1018 -- koyu lacivert
CIZGI = (0xe8, 0xee, 0xf7)          # #e8eef7 -- acik gri
VURGU = (0x2d, 0xd4, 0xbf)          # #2dd4bf -- turkuaz

ZEMIN_YARICAP = 7.0                 # rx="7"

#: "N" harfi: M5 27 V6 l14 17 V6
N_YOLU = ((5.0, 27.0), (5.0, 6.0), (19.0, 23.0), (19.0, 6.0))
N_KALINLIK = 3.2                    # stroke-width
N_YARI = N_KALINLIK / 2.0

#: Iki cubuk: (x, y, genislik, yukseklik, yaricap)
CUBUKLAR = (
    (22.0, 19.0, 3.4, 8.0, 1.2),
    (26.6, 13.0, 3.4, 14.0, 1.2),
)

#: Piksel basina ornek (kenar yumusatma). 3 -> 9 ornek.
ORNEK = 3


def _yuvarlak_kare(x: float, y: float, kx: float, ky: float,
                   g: float, h: float, r: float) -> bool:
    """(x, y) noktasi yuvarlatilmis dikdortgenin icinde mi."""
    if not (kx <= x <= kx + g and ky <= y <= ky + h):
        return False
    # Kose bolgeleri disinda her nokta iceride.
    ix = min(max(x, kx + r), kx + g - r)
    iy = min(max(y, ky + r), ky + h - r)
    return (x - ix) ** 2 + (y - iy) ** 2 <= r * r


def _parca_uzakligi(x: float, y: float, ax: float, ay: float,
                    bx: float, by: float) -> float:
    """Noktanin [a, b] dogru PARCASINA uzakligi.

    Parcaya (dogruya degil) uzaklik olmasi, YUVARLAK UCLARI ve
    YUVARLAK KOSELERI bedavaya getiriyor: SVG'deki
    `stroke-linecap="round"` ve `stroke-linejoin="round"` tam olarak
    bu.
    """
    dx, dy = bx - ax, by - ay
    uzunluk2 = dx * dx + dy * dy
    if uzunluk2 == 0:
        return math.hypot(x - ax, y - ay)
    t = ((x - ax) * dx + (y - ay) * dy) / uzunluk2
    t = min(1.0, max(0.0, t))
    return math.hypot(x - (ax + t * dx), y - (ay + t * dy))


def renk(x: float, y: float) -> tuple[int, int, int, int] | None:
    """SVG koordinatindaki bir NOKTANIN rengi; disarida ise None.

    Katman sirasi SVG ile ayni: zemin -> "N" -> cubuklar. Uste cizilen
    alttakini ortuyor.
    """
    if not _yuvarlak_kare(x, y, 0.0, 0.0, TUVAL, TUVAL, ZEMIN_YARICAP):
        return None
    for kx, ky, g, h, r in CUBUKLAR:
        if _yuvarlak_kare(x, y, kx, ky, g, h, r):
            return (*VURGU, 255)
    for i in range(len(N_YOLU) - 1):
        (ax, ay), (bx, by) = N_YOLU[i], N_YOLU[i + 1]
        if _parca_uzakligi(x, y, ax, ay, bx, by) <= N_YARI:
            return (*CIZGI, 255)
    return (*ZEMIN, 255)


def ciz(boy: int) -> bytes:
    """`boy` x `boy` RGBA piksel dizisi uretir (kenarlari yumusatilmis).

    Her piksel `ORNEK`x`ORNEK` noktadan ortalaniyor. Ortalamanin
    ALFAYLA CARPILARAK yapilmasi sart: seffaf orneklerin rengi yok ve
    onlari renk ortalamasina katmak, kenarlarda siyah bir hale
    birakirdi.
    """
    olcek = TUVAL / boy
    adim = olcek / ORNEK
    veri = bytearray()
    for py in range(boy):
        for px in range(boy):
            r = g = b = a = 0
            for oy in range(ORNEK):
                for ox in range(ORNEK):
                    x = (px * ORNEK + ox + 0.5) * adim
                    y = (py * ORNEK + oy + 0.5) * adim
                    n = renk(x, y)
                    if n is None:
                        continue
                    r += n[0]; g += n[1]; b += n[2]; a += 255
            if a == 0:
                veri += b"\x00\x00\x00\x00"
                continue
            k = a // 255                      # ortulu ornek sayisi
            veri += bytes((r // k, g // k, b // k, a // (ORNEK * ORNEK)))
    return bytes(veri)


def png(boy: int, pikseller: bytes) -> bytes:
    """Ham RGBA'yi PNG'ye cevirir -- yalnizca `zlib` ve `struct` ile.

    PNG, uzunluk + tur + veri + CRC dizisinden olusuyor. Her satirin
    basindaki sifir bayti "suzgec yok" demek; suzgecler sikistirmayi
    iyilestiriyor ama bu boyutta gereksiz karmasiklik.
    """
    satirli = b"".join(b"\x00" + pikseller[y * boy * 4:(y + 1) * boy * 4]
                       for y in range(boy))

    def parca(tur: bytes, veri: bytes) -> bytes:
        return (struct.pack(">I", len(veri)) + tur + veri
                + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + parca(b"IHDR", struct.pack(">IIBBBBB", boy, boy, 8, 6, 0, 0, 0))
            + parca(b"IDAT", zlib.compress(satirli, 9))
            + parca(b"IEND", b""))


#: Uretilecek boyutlar ve NEDEN.
BOYUTLAR = {
    # Google favicon'u: "48x48'ten buyugu" oneriliyor; 192 ayrica
    # Android ana ekran simgesi olarak da kullaniliyor.
    192: "favicon + Android",
    # apple-touch-icon'un beklenen olcusu.
    180: "apple-touch-icon",
    # Organization.logo: Google en az 112x112 istiyor; 512 zengin
    # sonuclarda ve paylasim onizlemelerinde de net duruyor.
    512: "Organization.logo",
}


def uret(hedef: pathlib.Path | None = None) -> list[pathlib.Path]:
    h = hedef or HEDEF
    h.mkdir(parents=True, exist_ok=True)
    yazilan = []
    for boy, sebep in BOYUTLAR.items():
        p = h / f"netaris-{boy}.png"
        p.write_bytes(png(boy, ciz(boy)))
        print(f"  {p.name:18s} {p.stat().st_size:6d} bayt   ({sebep})")
        yazilan.append(p)
    return yazilan


if __name__ == "__main__":
    print("Netaris marka isareti uretiliyor:")
    uret()
