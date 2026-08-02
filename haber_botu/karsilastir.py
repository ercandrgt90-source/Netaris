"""Ayni bilancoyu birden fazla modele yazdirip yan yana koyar.

Amac tek bir karari vermek: analiz kalitesindeki fark, maliyet farkini
hakli cikariyor mu? Ayni prompt, ayni veri, ayni oranlar -- degisen tek
sey model.

Calistirmak icin:
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python karsilastir.py

Cikti:
    ciktilar/karsilastirma/<model>.md   -- her modelin yazisi ayri dosya
    ekranda                             -- maliyet, uzunluk, tarama sonucu

Iki modeli sirayla cagiriyoruz, paralel degil: ilk cagri sistem talimatini
onbellege yaziyor ama onbellek modele ozel, yani ikinci model yine kendi
onbellegini yaziyor. Paralellestirmenin faydasi yok, hata ayiklamasi zor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "analiz"))
sys.path.insert(0, str(_KOK / "ai"))

import guvenlik  # noqa: E402
import istemci  # noqa: E402
import prompt  # noqa: E402
from oranlar import hesapla  # noqa: E402

MODELLER = ["claude-opus-5", "claude-sonnet-5"]

CIKTI = _KOK / "ciktilar" / "karsilastirma"

# Gunluk icerik sayisi -- aylik maliyet tahmini icin
GUNLUK_ICERIK = 10


def _olc(metin: str) -> tuple[int, int, int]:
    """(kelime, karakter, paragraf) dondurur."""
    paragraflar = [p for p in metin.split("\n\n") if p.strip()]
    return len(metin.split()), len(metin), len(paragraflar)


def main() -> int:
    from ornek import ENFLASYON, ONCE, SIMDI

    rapor = hesapla(
        sirket="Ornek Cimento Sanayi A.S.",
        kod="ORNEK",
        simdi=SIMDI,
        once=ONCE,
        enflasyon=ENFLASYON,
    )
    sistem, kullanici = prompt.olustur(rapor)

    print(f"Ayni veri, {len(MODELLER)} model")
    print(f"{len(rapor.oranlar)} oran, {len(rapor.sinyaller)} sinyal")
    print("=" * 64)

    CIKTI.mkdir(parents=True, exist_ok=True)
    sonuclar: list[tuple[str, istemci.Sonuc, str, bool]] = []

    for model in MODELLER:
        print(f"\n>>> {model}")
        try:
            sonuc = istemci.uret(sistem, kullanici, model=model)
        except istemci.RedEdildi as e:
            print(f"    REDDEDILDI: {e}")
            continue
        except Exception as e:  # noqa: BLE001 -- bir model duserse digeri devam etsin
            print(f"    HATA: {type(e).__name__}: {e}")
            continue

        metin = f"{sonuc.metin}\n\n---\n\n*{prompt.UYARI_METNI}*\n"
        tamam, bulgular = guvenlik.yayinlanabilir(metin)

        yol = CIKTI / f"{model}.md"
        yol.write_text(metin, encoding="utf-8")

        kelime, karakter, paragraf = _olc(sonuc.metin)
        print(f"    {sonuc.rapor().replace(chr(10), chr(10) + '    ')}")
        print(f"    uzunluk: {kelime} kelime, {paragraf} paragraf")
        print(f"    tarama: {'temiz' if tamam else 'ENGELLENDI'} ({len(bulgular)} bulgu)")
        print(f"    yazildi: {yol.relative_to(_KOK)}")

        sonuclar.append((model, sonuc, metin, tamam))

    if len(sonuclar) < 2:
        print("\nKarsilastirma icin en az iki basarili uretim gerekli.")
        return 1

    print("\n" + "=" * 64)
    print("OZET")
    print("=" * 64)
    print(f"{'model':<22} {'kelime':>7} {'maliyet':>10} {'aylik*':>10}  tarama")
    print("-" * 64)
    for model, sonuc, metin, tamam in sonuclar:
        kelime = len(sonuc.metin.split())
        aylik = sonuc.maliyet * GUNLUK_ICERIK * 30
        print(
            f"{model:<22} {kelime:>7} {sonuc.maliyet:>9.4f}$ "
            f"{aylik:>9.2f}$  {'temiz' if tamam else 'ENGELLENDI'}"
        )
    print(f"\n* gunde {GUNLUK_ICERIK} icerik varsayimiyla")

    en_ucuz = min(sonuclar, key=lambda s: s[1].maliyet)
    en_pahali = max(sonuclar, key=lambda s: s[1].maliyet)
    if en_ucuz[1].maliyet > 0:
        kat = en_pahali[1].maliyet / en_ucuz[1].maliyet
        fark = (en_pahali[1].maliyet - en_ucuz[1].maliyet) * GUNLUK_ICERIK * 30
        print(f"\n{en_pahali[0]}, {en_ucuz[0]}'dan {kat:.1f}x pahali -- ayda {fark:.2f}$ fark.")

    print("\nSimdi iki dosyayi yan yana okuyun. Karar sorusu:")
    print("  Pahali modelin analizi, aylik farki hakli cikaracak kadar mi iyi?")
    print("Bakilacak yerler: reel/nominal ayrimi dogru kurulmus mu, kar")
    print("kalitesi sinyali anlasilmis mi, 'bu terim ne demek' bolumu gercekten")
    print("ogretici mi, uydurma rakam var mi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
