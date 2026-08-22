"""Canli siteyi yerel yapiyla karsilastirir.

Yayindan sonra "gercekten guncel mi" sorusunu kesin cevaplar: her dosyanin
sha256 ozetini karsilastirir. Bir kez yanlis projeyi kontrol edip saatler
kaybettik; bu betik o belirsizligi kaldiriyor.

YENIDEN DENEME NEDEN VAR
------------------------
Cloudflare kenar dugumleri yeni surumu birkac saniye icinde aliyor ama
ANINDA degil. Yayindan hemen sonra calistirilan ilk kontrol, gercekte
sorun olmadigi halde "farkli" diyebiliyor -- bir kez oyle oldu. Yanlis
alarm, alarm olmamasindan daha kotudur: insani olmayan bir sorunu aramaya
yonlendirir. Bu yuzden farkli cikan yollar bir sure sonra tekrar sorulur;
kalici fark ancak butun denemeler tukendiginde bildirilir.

Kullanim:
    python dogrula.py
    python dogrula.py https://baska-adres.example
"""

from __future__ import annotations

import hashlib
import pathlib
import random
import sys
import time

import httpx

#: Kenar dugumlerin yayilmasi icin taninan sure.
#:
#: 4 x 5 sn = 15 sn idi ve yetmedi: ticari haber kaynaklari eklendiginde
#: tek calistirmada 10 yeni konunun fotograflari (~40 dosya) ve 24 yeni
#: haber sayfasi birden yuklendi, dogrulama hepsi yayilmadan calisti ve
#: hat kirmizi dondu -- oysa site sagliklidi.
#:
#: Bu bekleme yalnizca eslesmeyen yol KALDIGINDA harcanir; her sey yerine
#: oturmussa ilk denemede cikiliyor. Saatlik otomasyonda her calistirma
#: yeni sayfa ekledigi icin pay genis tutuldu.
DENEME_SAYISI = 6
BEKLEME_SN = 8

KOK = pathlib.Path(__file__).parent
CIKTI = KOK / "cikti"
# ALAN ADI: `insa.TABAN_ADRES` ile AYNI olmali. Ikisi ayrisirsa
# dogrulama baska bir siteyi kontrol eder ve "her sey yolunda"
# der -- yayimlanan sayfalara hic bakmadan.
VARSAYILAN = "https://netaris.net"

def yollari_bul() -> list[tuple[str, str]]:
    """Kontrol edilecek yollari CIKTI klasorunden turetir.

    Onceden elle yazilmis bir listeydi. Sorun su ki her yeni yazi listeye
    eklenmedigi surece dogrulama disinda kaliyordu -- site buyudukce
    dogrulanan oran kucululuyor ve bunu kimse fark etmiyordu. Klasorden
    turetmek bu sessiz daralmayi ortadan kaldiriyor.
    """
    bulunan: list[tuple[str, str]] = []
    for p in sorted(CIKTI.rglob("*")):
        if not p.is_file():
            continue
        goreli = p.relative_to(CIKTI).as_posix()
        # index.html dosyalari klasor adresiyle sunuluyor
        if goreli == "index.html":
            bulunan.append(("/", goreli))
        elif goreli.endswith("/index.html"):
            bulunan.append(("/" + goreli[: -len("index.html")], goreli))
        else:
            bulunan.append(("/" + goreli, goreli))
    return bulunan


def _karsilastir(c: httpx.Client, taban: str, yol: str, yerel: pathlib.Path):
    """Tek bir yolu kontrol eder. (ayni_mi, durum_kodu) dondurur."""
    # Sorgu parametresi kenar onbellegini atlatmak icin
    r = c.get(f"{taban}{yol}?v={random.randint(1, 10**9)}")
    ayni = (
        r.status_code == 200
        and hashlib.sha256(r.content).hexdigest()
        == hashlib.sha256(yerel.read_bytes()).hexdigest()
    )
    return ayni, r.status_code


def main() -> int:
    taban = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else VARSAYILAN
    print(f"{taban}\n")

    yollar = yollari_bul()
    if not yollar:
        print(f"{CIKTI} bos -- once 'python site/insa.py' calistirin.")
        return 1

    eksik: list[tuple[str, str]] = []
    bekleyen = yollar
    durumlar: dict[str, int] = {}

    with httpx.Client(timeout=30.0, headers={"Cache-Control": "no-cache"}) as c:
        for deneme in range(1, DENEME_SAYISI + 1):
            kalan = []
            for yol, dosya in bekleyen:
                ayni, kod = _karsilastir(c, taban, yol, CIKTI / dosya)
                durumlar[yol] = kod
                if not ayni:
                    kalan.append((yol, dosya))

            if not kalan:
                bekleyen = []
                break
            if deneme < DENEME_SAYISI:
                print(
                    f"  {len(kalan)} yol henuz eslesmedi, kenar dugumler icin "
                    f"{BEKLEME_SN} sn bekleniyor ({deneme}/{DENEME_SAYISI - 1})"
                )
                time.sleep(BEKLEME_SN)
            bekleyen = kalan

    farkli = {y for y, _ in bekleyen}
    for yol, _ in yollar:
        etiket = "FARKLI" if yol in farkli else "ayni"
        print(f"  {durumlar[yol]}  {etiket:<7} {yol}")

    print()
    fark = len(farkli) + len(eksik)
    if fark:
        print(f"{fark} dosyada fark var -- dagitim tamamlanmamis olabilir.")
        return 1
    print("Canli site yerel yapiyla birebir ayni.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
