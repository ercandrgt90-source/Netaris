"""Varlik eslemesi testleri.

BU DOSYA NEDEN VAR
------------------
Bu projede en sik tekrarlayan hata sinifi tek bir sey: kisa kalibin
kelime ICINDE eslesmesi. On ikiden fazla kez yasandi ve her seferinde
SESSIZ yanlis siniflandirma uretti -- kimse hata gormedi, sadece haber
yanlis yere baglandi.

Olculen ornekler:

    "iran"  -> "hazIRANin"     her haziran tarihli haber Iran'a baglandi
    "gold"  -> "GOLDman"
    "otel"  -> "OTELenebilir"
    "ges "  -> "charGES "
    "ons "  -> "billiONS "
    "altin" -> "topragin ALTINDa"

Asagidaki testler o tuzaklari KALICI hale getiriyor. Yeni bir kalip
eklendiginde bu dosya calistirilmali:

    python haber_botu/analiz/test_varlik.py
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))

import graf_tohum  # noqa: E402
import varlik      # noqa: E402


def _bellek_depo() -> sqlite3.Connection:
    """Grafi bellekte kuran gecici depo. Gercek depoya DOKUNMAZ --
    testin yan etkisi olmamali."""
    b = sqlite3.connect(":memory:")
    b.execute("CREATE TABLE varlik (kod TEXT PRIMARY KEY, tur TEXT, ad TEXT,"
              " ad_en TEXT, aciklama TEXT, seri_kodu TEXT, onem INTEGER,"
              " kayit_ani TEXT)")
    b.executemany(
        "INSERT INTO varlik (kod, tur, ad, ad_en, seri_kodu, onem, aciklama)"
        " VALUES (?,?,?,?,?,?,?)", graf_tohum.VARLIKLAR)
    return b


#: (baslik, cikmasi GEREKEN kodlar, cikmamasi GEREKEN kodlar)
DURUMLAR: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    # --- tuzaklar: bunlar CIKMAMALI ---
    ("Yüzyıllarca toprağın altında kaldı: 2 bin 500 yıllık heykel bulundu",
     (), ("XAU",)),
    ("Goldman Sachs: indirim ötelenebilir", ("GOLDMAN",), ("SEK_TURIZM",)),
    ("SEC charges firm with fraud", ("SEC",), ("SEK_ENERJI",)),
    ("Şirket haziranın ikinci yarısında büyüdü", (), ("IR",)),
    ("Bu önemli bir gelişme, important development", (), ("DIS_TICARET_TR",)),
    ("Bankalar milyarlarca lira, billions of dollars", ("SEK_BANKA",), ("XAU",)),
    ("Hedeflenen fedakârlık: atletizmde abdest molası", (), ("FED", "US")),
    ("S&P 500 rekor kırdı", ("SP500",), ("SPRATING",)),
    ("Bakan Çiftçi açıklama yaptı", (), ("TR",)),

    # --- eslesmesi GEREKENLER ---
    ("ABD-İran geriliminde yumuşama sinyali petrolü düşürdü",
     ("US", "IR", "BRENT"), ()),
    ("Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)", ("TCMB_FAIZ",), ()),
    ("Temmuz ayı dış ticaret rakamları açıklandı", ("DIS_TICARET_TR",), ()),
    ("Bakırda iki haftanın zirvesi", ("XCU",), ()),
    ("TCMB faiz kararını açıkladı", ("TCMB", "TCMB_FAIZ"), ()),
    ("Fed Başkanı Powell konuştu", ("FED", "POWELL"), ()),
    ("Gram altın rekor tazeledi", ("XAU",), ()),
    ("Türkiye'nin fındık ihracatı arttı", ("TR", "DIS_TICARET_TR"), ()),

    # --- bastirma: yurt disi haberde Turkiye gostergeleri dusmeli ---
    ("Fed, enflasyon verisini bekliyor", ("FED",), ("TUFE_TR",)),
    ("TÜİK enflasyon verisini açıkladı", ("TUIK", "TUFE_TR"), ()),
)


def main() -> int:
    b = _bellek_depo()
    hata = 0

    # Grafta karsiligi olmayan kalip, sessizce hicbir seye baglanmaz.
    kayip = varlik.dogrula()
    if kayip:
        print(f"HATA kaliplar grafta yok: {', '.join(kayip)}")
        hata += 1

    for baslik, olmali, olmamali in DURUMLAR:
        kodlar = {v.kimlik for v in varlik.bul(b, baslik)}
        eksik = [k for k in olmali if k not in kodlar]
        fazla = [k for k in olmamali if k in kodlar]
        if eksik or fazla:
            hata += 1
            print(f"HATA {baslik[:58]}")
            if eksik:
                print(f"     eksik : {', '.join(eksik)}")
            if fazla:
                print(f"     FAZLA : {', '.join(fazla)}  <- yanlis eslesme")
            print(f"     bulunan: {', '.join(sorted(kodlar)) or '-'}")

    print("=" * 60)
    if hata:
        print(f"{hata} TEST BASARISIZ")
        return 1
    print(f"TUM TESTLER GECTI ({len(DURUMLAR)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
