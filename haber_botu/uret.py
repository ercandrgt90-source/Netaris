"""Bilanco analizi uretim hatti -- uctan uca.

    veri dosyasi -> dogrulama -> oran -> skor -> AI yorum -> tarama -> site

Kullanim:
    python uret.py                          # veri/ altindaki tum dosyalar
    python uret.py veri/THYAO-2025-12.txt   # tek dosya
    python uret.py --yeni THYAO 2025/12     # bos sablon olustur

Yari otomatik kopru: insan KAP'tan rakamlari okuyup veri dosyasina yazar,
gerisini hat otomatik yapar. Girdi dogrulamasi hatta girmeden calisir --
hatali veriyle uretilen analiz, hic uretilmemis analizden kotudur.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "analiz"))
sys.path.insert(0, str(_KOK / "ai"))

import girdi  # noqa: E402
import guvenlik  # noqa: E402
import istemci  # noqa: E402
import prompt  # noqa: E402
import skor as skor_modulu  # noqa: E402
import yayin  # noqa: E402
from oranlar import hesapla  # noqa: E402

ARSIV = _KOK / "ciktilar"


def _isle(yol: pathlib.Path, kurgusal: bool) -> int:
    print("=" * 66)
    print(f"{yol.name}")
    print("=" * 66)

    try:
        g = girdi.oku(yol)
    except ValueError as e:
        print(f"GIRDI HATASI: {e}")
        return 1

    print(f"{g.sirket} ({g.kod})  {g.simdi.etiket} <- {g.once.etiket}")
    print(f"esas: {g.esas.value}" + (f", TUFE %{g.tufe}" if g.tufe else ""))

    if g.bulgular:
        print(f"\ndogrulama: {len(g.bulgular)} bulgu")
        for b in g.bulgular:
            print(f"  {b}")
    else:
        print("dogrulama: temiz")

    if not g.gecerli:
        print("\nDURDURULDU -- veride hata var, duzeltmeden devam edilmez.")
        return 1

    rapor = hesapla(
        sirket=g.sirket,
        kod=g.kod,
        simdi=g.simdi,
        once=g.once,
        esas=g.esas,
        enflasyon=g.tufe,
    )
    skor = skor_modulu.hesapla(rapor, g.simdi, g.gecmis_buyumeler or None)

    print(f"\n{len(rapor.oranlar)} oran, {len(rapor.sinyaller)} sinyal")
    if skor.skor is not None:
        uygun = "yayina uygun" if skor.yayimlanabilir else "KAPSAM DUSUK"
        print(f"skor: {skor.skor:.0f}/100, kapsam %{skor.kapsam * 100:.0f} ({uygun})")

    sistem, kullanici = prompt.olustur(
        rapor, skor=skor if skor.yayimlanabilir else None
    )

    print("\nmodele gonderiliyor...")
    try:
        sonuc = istemci.uret(sistem, kullanici)
    except istemci.RedEdildi as e:
        print(f"HATA: {e}")
        return 1
    except RuntimeError as e:
        print(f"HATA: {e}")
        return 1

    print(sonuc.rapor())

    # Yasal uyariyi kod ekler -- modelin talimata uymasina birakilmaz
    metin = f"{sonuc.metin}\n\n---\n\n*{prompt.UYARI_METNI}*\n"

    print("\nifade taramasi")
    print("-" * 66)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    # Ham cikti her zaman arsivlenir -- tarama engellese de ne uretildigini
    # gormek gerekiyor
    ARSIV.mkdir(exist_ok=True)
    arsiv = ARSIV / f"{yol.stem}.md"
    arsiv.write_text(metin, encoding="utf-8")
    print(f"\narsiv: {arsiv.relative_to(_KOK)}")

    if not tamam:
        print("DURUM: ENGELLENDI -- site icerigine YAZILMADI")
        return 1

    dosya = yayin.yaz(
        rapor,
        metin,
        skor=skor if skor.yayimlanabilir else None,
        kurgusal=kurgusal,
    )
    print(f"site icerigi: {dosya.relative_to(_KOK.parent)}")
    print("DURUM: taslak hazir -- onaydan sonra 'python site/insa.py'")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description="Bilanco analizi uretim hatti")
    a.add_argument("dosya", nargs="?", help="veri dosyasi (bos ise veri/ altindaki hepsi)")
    a.add_argument("--yeni", nargs=2, metavar=("KOD", "DONEM"), help="bos sablon olustur")
    a.add_argument("--kurgusal", action="store_true", help="ornek icerik olarak isaretle")
    args = a.parse_args()

    if args.yeni:
        kod, donem = args.yeni
        try:
            yol = girdi.sablon_olustur(kod, donem)
        except FileExistsError as e:
            print(f"HATA: {e}")
            return 1
        print(f"olusturuldu: {yol.relative_to(_KOK)}")
        print("Doldurup 'python uret.py' calistirin.")
        return 0

    if args.dosya:
        yollar = [pathlib.Path(args.dosya)]
    else:
        girdi.VERI.mkdir(exist_ok=True)
        yollar = sorted(girdi.VERI.glob("*.txt"))

    if not yollar:
        print("Islenecek veri dosyasi yok.")
        print("Yeni sablon icin:  python uret.py --yeni THYAO 2025/12")
        return 1

    hatali = 0
    for i, yol in enumerate(yollar):
        if i:
            print()
        if _isle(yol, args.kurgusal):
            hatali += 1

    if len(yollar) > 1:
        print(f"\n{len(yollar)} dosya, {len(yollar) - hatali} basarili, {hatali} hatali")
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
