"""Imzali analist yorumu hatti -- insan yazar, sistem denetler ve yayimlar.

NEDEN AYRI BIR ICERIK TIPI
--------------------------
Otomatik yazarlar (yazar.py, yazar_makro.py, yazar_teknik.py) yalnizca
hesaplanabilir seyleri yazar. Bilerek soyle kuruldu:

  * Hareketin NEDENI yazilmaz -- fiyat serisi nedeni gostermez
  * Yon yargisi verilmez     -- gelecegi bilmiyoruz
  * Veri olmayan varlik icin icerik uretilmez

Ama bir INSAN analist bunlarin hepsini yapabilir: haberi okur, karar
metnini okur, grafige bakar, baglanti kurar. Bu, makinenin eksigi degil,
insanin katkisidir.

Bu yuzden analist yorumu ayri bir tipte yayimlanir:

  * **Imzalidir.** Yazar adi sayfada gorunur; sorumluluk ona aittir.
  * **Isaretlidir.** "Yazarin kendi degerlendirmesidir" notu tasir.
  * **Ayni taramadan gecer.** Al/sat dili ve dayanaksiz deger yargisi
    burada da engellenir -- imza yasal cerceveyi gevsetmez.
  * **Veriye baglanir.** Yazida gecen gostergeler icin otomatik
    analizlerimize baglanti verilir.

Bu ayrim finans yayinciliginda standarttir: veri/haber ile kose yazisi
farkli seylerdir ve okurun hangisini okudugunu bilmesi gerekir.

Kullanim:
    python uret_yorum.py yorumlar/2026-08-01-tcmb.md
    python uret_yorum.py yorumlar/2026-08-01-tcmb.md --yayinla
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "ai"))

import guvenlik  # noqa: E402
import prompt  # noqa: E402
import yayin  # noqa: E402

YORUMLAR = _KOK / "yorumlar"
ARSIV = _KOK / "ciktilar"

SABLON = """\
---
baslik: Buraya başlık
yazar: Necati Ercan Durgut
unvan: Teknik ve temel analist
ozet: Tek cümlelik özet — arama sonucunda ve kartta görünür.
konular: TCMB, enflasyon, enerji
kaynaklar: TCMB, FRED
# Gecmis tarihli yazi icin doldurun (2026-07-24 gibi). Bos = bugun.
# Yazida "bugun", "bu hafta" gibi ifadeler varsa bu alan ZORUNLUDUR:
# yanlis tarihli bir merkez bankasi karari, duzeltilmesi en zor hatadir.
tarih:
---

Yazı buraya. Markdown kullanılabilir.
"""


def _on_ayristir(ham: str) -> tuple[dict, str]:
    """--- ile sinirlandirilmis basit anahtar: deger blogunu okur."""
    if not ham.startswith("---"):
        return {}, ham
    _, on, govde = ham.split("---", 2)
    alanlar: dict[str, str] = {}
    for satir in on.strip().splitlines():
        satir = satir.strip()
        if satir and not satir.startswith("#") and ":" in satir:
            anahtar, deger = satir.split(":", 1)
            alanlar[anahtar.strip()] = deger.strip()
    return alanlar, govde.lstrip("\n")


def _isle(yol: pathlib.Path, yayinla: bool) -> int:
    ham = yol.read_text(encoding="utf-8-sig")
    alanlar, govde = _on_ayristir(ham)

    baslik = alanlar.get("baslik", "").strip()
    yazar = alanlar.get("yazar", "").strip()

    print("=" * 70)
    print(baslik or yol.stem)
    print("=" * 70)

    eksik = [a for a in ("baslik", "yazar", "ozet") if not alanlar.get(a)]
    if eksik:
        print(f"EKSIK ALAN: {', '.join(eksik)}")
        print("Imzasiz yorum yayimlanmaz -- sorumlulugun kime ait oldugu")
        print("okurun gorebilecegi bir bilgidir.")
        return 1

    kelime = len(govde.split())
    print(f"yazar : {yazar}")
    print(f"uzunluk: {kelime} kelime, ~{max(1, round(kelime / 200))} dk okuma")

    # Yasal uyari altbilgide basiliyor; tarama yayimlanan sayfanin hali
    # uzerinden yapilir
    metin = f"{govde}\n\n{prompt.UYARI_METNI_SKORSUZ}\n"

    print("\nifade taramasi")
    print("-" * 70)
    print(guvenlik.rapor(metin))
    tamam, _ = guvenlik.yayinlanabilir(metin)

    ARSIV.mkdir(exist_ok=True)
    (ARSIV / f"yorum-{yol.stem}.md").write_text(metin, encoding="utf-8")

    if not tamam:
        print("\nDURUM: ENGELLENDI -- site icerigine yazilmadi")
        print("Imza yasal cerceveyi gevsetmez; ayni kurallar gecerli.")
        return 1

    if not yayinla:
        print("\nDURUM: yalnizca arsive yazildi (--yayinla ile siteye gider)")
        return 0

    dosya = yayin.yaz_makro(
        govde,
        konu=baslik,
        kaynak=alanlar.get("kaynaklar", "").replace(",", ", ") or "Yazarın değerlendirmesi",
        kategori="Analist Yorumu",
        kod="YORUM",
        kaynaklar=alanlar.get("kaynaklar", ""),
        sayimlar=f"{kelime}|kelime;1|imzalı yazar",
        yazar=yazar,
        unvan=alanlar.get("unvan", ""),
        ozet_metni=alanlar.get("ozet", ""),
        tarih_ustu=alanlar.get("tarih", ""),
    )
    print(f"\nsite icerigi: {dosya.relative_to(_KOK.parent)}")
    print("DURUM: taslak hazir -- 'python site/yayinla.py'")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description="Imzali analist yorumu hatti")
    a.add_argument("dosya", nargs="?", help="yorumlar/*.md")
    a.add_argument("--yayinla", action="store_true")
    a.add_argument("--yeni", metavar="AD", help="bos sablon olustur")
    args = a.parse_args()

    YORUMLAR.mkdir(exist_ok=True)

    if args.yeni:
        hedef = YORUMLAR / f"{args.yeni}.md"
        if hedef.exists():
            print(f"Zaten var: {hedef}")
            return 1
        hedef.write_text(SABLON, encoding="utf-8")
        print(f"olusturuldu: {hedef.relative_to(_KOK)}")
        return 0

    if args.dosya:
        yollar = [pathlib.Path(args.dosya)]
    else:
        yollar = sorted(YORUMLAR.glob("*.md"))

    if not yollar:
        print("Yorum dosyasi yok.  python uret_yorum.py --yeni 2026-08-01-tcmb")
        return 1

    hatali = sum(_isle(y, args.yayinla) for y in yollar)
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
