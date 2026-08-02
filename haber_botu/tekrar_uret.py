"""Mevcut bir veri dosyasini secilen modelle yeniden uretir.

uret.py varsayilan modeli kullanir. Bu betik model ve effort'u komut
satirindan almaya yarar -- kalibrasyon ve karsilastirma icin.

Kullanim:
    python tekrar_uret.py veri/ORNEK-2025-12.txt
    python tekrar_uret.py veri/ORNEK-2025-12.txt claude-opus-5 high
"""

from __future__ import annotations

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


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    yol = pathlib.Path(sys.argv[1])
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-5"
    effort = sys.argv[3] if len(sys.argv) > 3 else "medium"

    g = girdi.oku(yol)
    if not g.gecerli:
        for b in g.bulgular:
            print(f"  {b}")
        print("DURDURULDU -- veride hata var")
        return 1

    rapor = hesapla(
        sirket=g.sirket, kod=g.kod, simdi=g.simdi, once=g.once,
        esas=g.esas, enflasyon=g.tufe,
    )
    skor = skor_modulu.hesapla(rapor, g.simdi, g.gecmis_buyumeler or None)
    sistem, kullanici = prompt.olustur(rapor, skor=skor if skor.yayimlanabilir else None)

    print(f"{g.sirket} ({g.kod})  {model} / effort={effort}")
    print("modele gonderiliyor...")
    sonuc = istemci.uret(sistem, kullanici, model=model, effort=effort)

    metin = f"{sonuc.metin}\n\n---\n\n*{prompt.UYARI_METNI}*\n"
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ilk = sonuc.metin.lstrip().splitlines()[0]
    baslik = ilk.lstrip("# ").strip()

    print()
    print(f"  model    : {sonuc.kullanilan_model}")
    print(f"  maliyet  : ${sonuc.maliyet:.4f}")
    print(f"  kelime   : {len(sonuc.metin.split())}")
    print(f"  tarama   : {'temiz' if tamam else 'ENGELLENDI'}")
    print()
    print(f"  BASLIK   : {baslik}")
    print(f"  uzunluk  : {len(baslik)} karakter")

    (_KOK / "ciktilar").mkdir(exist_ok=True)
    (_KOK / "ciktilar" / f"{yol.stem}.md").write_text(metin, encoding="utf-8")

    if not tamam:
        print("\n  site icerigine YAZILMADI")
        return 1

    dosya = yayin.yaz(rapor, metin, skor=skor if skor.yayimlanabilir else None, kurgusal=True)
    print(f"  site     : {dosya.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
