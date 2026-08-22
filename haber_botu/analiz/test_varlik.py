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


#: (baslik, cikmasi GEREKEN kodlar, cikmamasi GEREKEN kodlar, kurum)
DURUMLAR: tuple[tuple, ...] = (
    # --- Turkce ekler: dar kalip yuzunden kacanlar ---
    ("Altını sollayan gümüşte yeni dalga kapıda", ("XAU", "XAG"), ()),
    ("İş Bankası 2026 ilk yarı finansal sonuçlarını açıkladı",
     ("SEK_BANKA",), (), "Dünya"),
    ("Goldman Sachs'tan Türkiye için faiz uyarısı: İndirim beklentisi "
     "ötelenebilir", ("GOLDMAN", "TR", "TCMB_FAIZ"), ("SEK_TURIZM",)),

    # --- Turkiye baglami olmayan haberde Turkiye varliklari dusmeli ---
    ("Meksika analistleri 2026 enflasyon tahminini düşürdü", (), ("TUFE_TR",)),
    ("ABD'de inşaat harcamaları haziranda geriledi",
     ("US",), ("SEK_INSAAT",)),
    ("Altın yatırımcısına nefes aldıran açıklama! Dev banka yıl sonu "
     "tahminini yükseltti", ("XAU",), ("SEK_BANKA",)),
    # Baslikta tek Turkiye isareti yok ama TCMB duyurusu.
    ("Sektörel Enflasyon Beklentileri (Temmuz 2026)",
     ("TUFE_TR",), (), "TCMB"),
)

DURUMLAR += (
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
    # Ikisinde de baslikta Turkiye isareti YOK; baglami kurum tasiyor.
    # Uretimde de boyle geliyorlar.
    ("Faiz Oranlarına İlişkin Basın Duyurusu (2026-28)",
     ("TCMB_FAIZ",), (), "TCMB"),
    ("Temmuz ayı dış ticaret rakamları açıklandı",
     ("DIS_TICARET_TR",), (), "TÜİK"),
    # Kurumsuz ve isaretsiz ayni baslik Turkiye'ye baglanmamali.
    ("Temmuz ayı dış ticaret rakamları açıklandı", (), ("DIS_TICARET_TR",)),
    ("Bakırda iki haftanın zirvesi", ("XCU",), ()),
    ("TCMB faiz kararını açıkladı", ("TCMB", "TCMB_FAIZ"), ()),
    # GOREVDEKI baskan ve ONCEKI baskan AYRI varliklar. Gorev
    # degistiginde tanim guncelleniyor ama eski kayit SILINMIYOR --
    # arsivdeki haberler ona baglaniyor ve o baglanti dogru.
    ("Fed Başkanı Warsh faiz sinyali verdi", ("FED", "WARSH"), ()),
    ("Fed Başkanı Powell konuştu", ("FED", "POWELL"), ()),
    ("Gram altın rekor tazeledi", ("XAU",), ()),
    ("Türkiye'nin fındık ihracatı arttı", ("TR", "DIS_TICARET_TR"), ()),

    # --- bastirma: yurt disi haberde Turkiye gostergeleri dusmeli ---
    ("Fed, enflasyon verisini bekliyor", ("FED",), ("TUFE_TR",)),
    ("TÜİK enflasyon verisini açıkladı", ("TUIK", "TUFE_TR"), ()),

    # --- TARIFE: "tarife" Turkce'de IKI ANLAMLI ---
    #
    # Gumruk tarifesi ile abonelik fiyat cetveli ayni kelime ve
    # ikincisi bu akista daha sik geciyor. Ilk yazimda kaliplar genisti
    # ("ek vergi", "~tarifeler") ve olculen yanlislar:
    #
    #     "Kurumlar vergisinde EK VERGI duzenlemesi"  -> TARIFE
    #     "Dogal gaz TARIFELERINDE degisiklik"        -> TARIFE
    #
    # Her kalip artik TICARET baglamini kendi icinde tasiyor. Iki yon
    # de sinaniyor: kacirmak kadar yanlis yakalamak da hata -- yanlis
    # yakalanan haber, olmadigi bir konuya ait bir aktarim kanali
    # gosterir.
    ("ABD yüzde 50 gümrük vergisi uyguluyor", ("TARIFE", "US"), ()),
    ("Kanada-USMCA görüşmeleri yeniden başlıyor", ("TARIFE",), ()),
    ("Çin ile ticaret savaşı yeniden alevlendi", ("TARIFE", "CN"), ()),
    ("ABD ithalat vergilerini artırdı", ("TARIFE", "US"), ()),
    # Yurt ici vergi ve abonelik tarifesi TARIFE DEGIL.
    ("Kurumlar vergisinde ek vergi düzenlemesi", (), ("TARIFE",)),
    ("Doğal gaz tarifelerinde değişiklik", ("DGAZ",), ("TARIFE",)),
    ("Elektrik tarifesi yüzde 25 zamlandı", (), ("TARIFE",)),
    ("Gelir vergisi dilimleri yeniden belirlendi", (), ("TARIFE",)),
)


def main() -> int:
    b = _bellek_depo()
    hata = 0

    # Grafta karsiligi olmayan kalip, sessizce hicbir seye baglanmaz.
    kayip = varlik.dogrula()
    if kayip:
        print(f"HATA kaliplar grafta yok: {', '.join(kayip)}")
        hata += 1

    for durum in DURUMLAR:
        baslik, olmali, olmamali = durum[0], durum[1], durum[2]
        # Kurum istege bagli -- yalnizca baglamin belirleyici oldugu
        # durumlarda yaziliyor.
        kurum = durum[3] if len(durum) > 3 else ""
        kodlar = {v.kimlik for v in varlik.bul(b, baslik, kurum=kurum)}
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
