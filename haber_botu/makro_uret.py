"""Makro yorum uretim hatti.

    ucretsiz veri kaynaklari -> gosterge anlik goruntusu -> AI yorum
    -> ifade taramasi -> site icerigi

Kullanim:
    python makro_uret.py                       # varsayilan gosterge seti
    python makro_uret.py --odak "Brent petrol" # belirli bir gostergeye odaklan
    python makro_uret.py --sadece-veri         # AI cagirmadan veriyi goster

Bilanco hattiyla ayni mimari: rakamlari kod hesaplar, model yorumlar.
Fark, bu hattin bilanco sezonundan bagimsiz calismasi -- makro veri her
gun guncelleniyor, dolayisiyla yayin takvimindeki bosluklar bununla
doluyor.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from datetime import date

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "ai"))
sys.path.insert(0, str(_KOK / "kaynak"))

import guvenlik  # noqa: E402
import istemci  # noqa: E402
import makro  # noqa: E402
import prompt_makro  # noqa: E402
import yayin  # noqa: E402

ARSIV = _KOK / "ciktilar"

# Varsayilan gosterge seti. FRED anahtar gerektirmiyor, EVDS gerektiriyor;
# EVDS anahtari yoksa Turkiye serileri sessizce atlanir ve yazi yalnizca
# kuresel gostergelerle yazilir -- eksik veriyle uretmek, uydurmaktan iyi.
FRED_SET = ("DFF", "DGS10", "DGS2", "DCOILBRENTEU")
EVDS_SET = ("TP.FG.J0", "TP.DK.USD.A.YTL")


def gostergeleri_topla() -> tuple[str, list[str]]:
    """Gosterge metnini ve kullanilan kaynaklari dondurur."""
    bolumler: list[str] = []
    kaynaklar: list[str] = []

    kuresel: list[str] = []
    for kod in FRED_SET:
        try:
            s = makro.fred(kod)
        except Exception as e:  # noqa: BLE001 -- tek seri duserse digerleri devam
            print(f"  uyari: {kod} cekilemedi ({type(e).__name__})")
            continue
        satir = "  " + s.bicimle()
        d30 = s.degisim(30)
        if d30 is not None:
            satir += f"\n      30 gozlem oncesine gore: {d30:+.2f} {s.birim}"
        kuresel.append(satir)

    if kuresel:
        bolumler.append("KURESEL GOSTERGELER\n" + "\n".join(kuresel))
        kaynaklar.append("FRED (St. Louis Fed)")

    turkiye: list[str] = []
    for kod in EVDS_SET:
        try:
            s = makro.evds(kod)
        except makro.EvdsAnahtariYok:
            break  # anahtar yoksa hepsi ayni sonucu verir
        except Exception as e:  # noqa: BLE001
            print(f"  uyari: {kod} cekilemedi ({type(e).__name__})")
            continue
        turkiye.append("  " + s.bicimle())

    if turkiye:
        bolumler.append("TURKIYE GOSTERGELERI\n" + "\n".join(turkiye))
        kaynaklar.append("TCMB EVDS")
    else:
        print("  not: EVDS anahtari yok -- yalnizca kuresel gostergelerle devam")

    return "\n\n".join(bolumler), kaynaklar


def main() -> int:
    a = argparse.ArgumentParser(description="Makro yorum uretim hatti")
    a.add_argument("--odak", help="yazinin merkezine konacak gosterge")
    a.add_argument("--konu", help="dosya adi ve baslik icin kisa konu etiketi")
    a.add_argument("--sadece-veri", action="store_true", help="AI cagirma, veriyi goster")
    args = a.parse_args()

    print("=" * 66)
    print(f"Makro yorum -- {date.today().isoformat()}")
    print("=" * 66)

    gostergeler, kaynaklar = gostergeleri_topla()
    if not gostergeler:
        print("Hicbir gosterge cekilemedi.")
        return 1

    print()
    print(gostergeler)

    if args.sadece_veri:
        return 0

    odak = args.odak or "(belirli bir odak yok -- en dikkat cekici degisimi sec)"
    sistem, kullanici = prompt_makro.olustur(gostergeler, odak=odak)

    print("\nmodele gonderiliyor...")
    try:
        sonuc = istemci.uret(sistem, kullanici)
    except (istemci.RedEdildi, RuntimeError) as e:
        print(f"HATA: {e}")
        return 1

    print(sonuc.rapor())

    metin = f"{sonuc.metin}\n\n---\n\n*{prompt_makro.UYARI_METNI}*\n"

    print("\nifade taramasi")
    print("-" * 66)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    konu = args.konu or (args.odak or "makro gorunum")
    arsiv = ARSIV / f"{date.today().isoformat()}-makro.md"
    arsiv.write_text(metin, encoding="utf-8")
    print(f"\narsiv: {arsiv.relative_to(_KOK)}")

    if not tamam:
        print("DURUM: ENGELLENDI -- site icerigine YAZILMADI")
        return 1

    dosya = yayin.yaz_makro(metin, konu=konu, kaynak=", ".join(kaynaklar))
    print(f"site icerigi: {dosya.relative_to(_KOK.parent)}")
    print("DURUM: taslak hazir -- onaydan sonra 'python site/insa.py'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
