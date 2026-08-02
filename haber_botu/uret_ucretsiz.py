"""Ucretsiz uretim hatti -- API cagrisi yok, maliyet sifir.

    veri dosyasi -> dogrulama -> oran -> skor -> KOD ILE YAZI -> tarama -> site

uret.py ile ayni zinciri kullanir, tek farki yazim adimi: dil modeli yerine
`analiz/yazar.py` sablon tabanli metni uretir.

NE ZAMAN HANGISI
----------------
* **uret_ucretsiz.py** -- gunluk akis. Butun bilancolar buradan gecebilir,
  maliyet sifir, uydurma riski sifir.
* **uret.py** -- one cikarilacak analizler. Dil modeli daha akici ve daha
  derin yaziyor; bunun bir bedeli var.

Ikisi ayni veriyi, ayni oranlari, ayni skoru kullaniyor. Fark yalnizca
duzyazinin kalitesinde -- analizin dogrulugunda degil.

Kullanim:
    python uret_ucretsiz.py                        # veri/ altindaki hepsi
    python uret_ucretsiz.py veri/THYAO-2025-12.txt
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
import prompt  # noqa: E402
import skor as skor_modulu  # noqa: E402
import yayin  # noqa: E402
import yazar  # noqa: E402
from oranlar import hesapla  # noqa: E402

ARSIV = _KOK / "ciktilar"


def _isle(yol: pathlib.Path, kurgusal: bool) -> int:
    print("=" * 66)
    print(f"{yol.name}   (ucretsiz hat)")
    print("=" * 66)

    try:
        g = girdi.oku(yol)
    except ValueError as e:
        print(f"GIRDI HATASI: {e}")
        return 1

    print(f"{g.sirket} ({g.kod})  {g.simdi.etiket} <- {g.once.etiket}")
    if g.bulgular:
        for b in g.bulgular:
            print(f"  {b}")
    if not g.gecerli:
        print("DURDURULDU -- veride hata var.")
        return 1

    rapor = hesapla(
        sirket=g.sirket, kod=g.kod, simdi=g.simdi, once=g.once,
        esas=g.esas, enflasyon=g.tufe,
    )
    skor = skor_modulu.hesapla(rapor, g.simdi, g.gecmis_buyumeler or None)

    print(f"{len(rapor.oranlar)} oran, {len(rapor.sinyaller)} sinyal")
    if skor.skor is not None:
        print(f"skor: {skor.skor:.0f}/100, kapsam %{skor.kapsam * 100:.0f}")

    govde = yazar.yaz(rapor, g.simdi, skor if skor.yayimlanabilir else None)
    # Tarama yayimlanan sayfanin hali uzerinden; uyari metni altbilgide
    # zaten var, govdeye ikinci kez yazilmiyor
    metin = f"{govde}\n\n{prompt.UYARI_METNI}\n"

    print(f"\nyazi uretildi: {len(govde.split())} kelime, maliyet $0.00")
    print("\nifade taramasi")
    print("-" * 66)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    (ARSIV / f"{yol.stem}-ucretsiz.md").write_text(metin, encoding="utf-8")

    if not tamam:
        print("\nDURUM: ENGELLENDI -- site icerigine yazilmadi")
        return 1

    dosya = yayin.yaz(rapor, govde, skor=skor if skor.yayimlanabilir else None,
                      kurgusal=kurgusal)
    print(f"\nsite icerigi: {dosya.relative_to(_KOK.parent)}")
    print("DURUM: taslak hazir -- onaydan sonra 'python site/yayinla.py'")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description="Ucretsiz bilanco analizi hatti")
    a.add_argument("dosya", nargs="?")
    a.add_argument("--kurgusal", action="store_true")
    args = a.parse_args()

    if args.dosya:
        yollar = [pathlib.Path(args.dosya)]
    else:
        girdi.VERI.mkdir(exist_ok=True)
        yollar = sorted(girdi.VERI.glob("*.txt"))

    if not yollar:
        print("Islenecek veri dosyasi yok.  python uret.py --yeni KOD DONEM")
        return 1

    hatali = sum(_isle(y, args.kurgusal) for y in yollar)
    if len(yollar) > 1:
        print(f"\n{len(yollar)} dosya, {len(yollar) - hatali} basarili")
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
