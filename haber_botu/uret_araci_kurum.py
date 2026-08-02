"""Araci kurum bilanco hatti -- ucretsiz, API cagrisi yok.

    veri modulu -> araci_kurum motoru -> KOD ILE YAZI -> tarama -> site

Kullanim:
    python uret_araci_kurum.py veri/TERA-2026-06.py
    python uret_araci_kurum.py veri/TERA-2026-06.py --yayinla
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "analiz"))
sys.path.insert(0, str(_KOK / "ai"))

import araci_kurum as ak  # noqa: E402
import guvenlik  # noqa: E402
import prompt  # noqa: E402
import yayin  # noqa: E402
import yazar_araci_kurum  # noqa: E402

ARSIV = _KOK / "ciktilar"


def _veri_yukle(yol: pathlib.Path):
    spec = importlib.util.spec_from_file_location("veri_modulu", yol)
    if spec is None or spec.loader is None:
        raise ValueError(f"Veri modulu yuklenemedi: {yol}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    a = argparse.ArgumentParser(description="Araci kurum bilanco hatti")
    a.add_argument("dosya")
    a.add_argument("--yayinla", action="store_true")
    args = a.parse_args()

    yol = pathlib.Path(args.dosya)
    if not yol.exists():
        print(f"Dosya yok: {yol}")
        return 1

    v = _veri_yukle(yol)
    simdi = ak.Donem(etiket=v.DONEM, **v.SIMDI)
    once = ak.Donem(etiket=v.ONCEKI_DONEM, **v.ONCE)

    print("=" * 70)
    print(f"{v.SIRKET} ({v.KOD})")
    print(f"gelir tablosu: {v.DONEM} <- {v.ONCEKI_DONEM}")
    print(f"bilanco      : {v.DONEM} <- {v.BILANCO_KARSILASTIRMA}")
    print("=" * 70)

    r = ak.hesapla(v.SIRKET, v.KOD, simdi, once)
    print(f"{len(r.oranlar)} oran, {len(r.sinyaller)} sinyal")
    for s in r.sinyaller:
        print(f"  [{s.yon.value.upper():<6}] {s.baslik}")

    govde = yazar_araci_kurum.yaz(r, simdi, once)

    # Tarama SAYFANIN YAYIMLANAN HALI uzerinden yapilir: yasal uyari sayfa
    # altbilgisinde her yazida zaten basiliyor, bu yuzden taramaya dahil
    # ediliyor. Ama govdeye YAZILMIYOR -- yazilirsa okur ayni metni iki kez
    # gorurdu (bir govdede, bir altbilgide).
    metin = f"{govde}\n\n{prompt.UYARI_METNI_SKORSUZ}\n"

    print(f"\nyazi uretildi: {len(govde.split())} kelime, maliyet $0.00")
    print("\nifade taramasi")
    print("-" * 70)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    arsiv = ARSIV / f"{v.KOD}-{v.DONEM.replace('/', '-')}-taslak.md"
    arsiv.write_text(metin, encoding="utf-8")
    print(f"\ntaslak: {arsiv.relative_to(_KOK)}")

    if not tamam:
        print("DURUM: ENGELLENDI -- site icerigine yazilmadi")
        return 1

    if args.yayinla:
        # Skor yok: araci kurum skoru henuz kalibre edilmedi, uydurulmaz
        # Gorsel yazinin KENDI rakamlarindan cizilir: stok fotograf ya da
        # sirket amblemi degil, gercek buyume kalemleri
        kisa = {
            "Brüt kâr (komisyon + net alım satım)": "Brüt kâr",
            "Esas faaliyet kârı": "Faaliyet kârı",
            "Aktif toplamı": "Aktif",
        }
        dosya = yayin.yaz_sektorel(
            govde,
            sirket=v.SIRKET,
            kod=v.KOD,
            donem=v.DONEM,
            sektor="Aracı kurum",
            grafik=yayin.grafik_alani(
                [(kisa.get(b.ad, b.ad), b.reel) for b in r.buyumeler]
            ),
            kaynaklar="KAP",
            # Gercek sayim: kac kalem okundu, kac oran hesaplandi, kac sinyal
            # esigi asti, kac aritmetik kimlik dogrulandi
            sayimlar=";".join([
                f"{len([x for x in v.SIMDI.values() if x is not None])}|okunan kalem",
                f"{len(r.oranlar)}|hesaplanan oran",
                f"{len(r.buyumeler)}|büyüme kalemi",
                f"{len(r.sinyaller)}|eşik aşan sinyal",
                "2|karşılaştırılan dönem",
            ]),
        )
        print(f"site icerigi: {dosya.relative_to(_KOK.parent)}")
        print("DURUM: taslak hazir -- 'python site/yayinla.py'")
    else:
        print("DURUM: yalnizca arsive yazildi (--yayinla ile site icerigine gider)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
