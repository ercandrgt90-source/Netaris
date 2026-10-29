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


# KELIME ICINDE ESLESME -- OLCULEN YANLISLAR.
#
# 2026-10-06'da depodaki 37.060 baslik tarandi ve her eslesmenin
# ICINDE OLDUGU TAM KELIME yazildi. Kaliptan farkli cikan 14 durumun
# 12'si gercek Turkce ekti; ikisi yanlisti ve ikisi de OKURA YANLIS
# ARSIV gosteriyordu:
#
#   "warship"/"warships" -> WARSH  (Kevin Warsh)      5 haber
#   "denizaltinin"       -> XAU    (altin)            1 haber
#   "Sec. Gen."/"Press Sec." -> SEC (ABD SEC kurumu) 34 baslik
#
# Son ikisi ayri duzenekle cozuldu: ilki kelime basi + Turkce ek
# kurali (`varlik.TEKIL_EK`), ikincisi ham metinde buyuk harf sarti
# (`varlik.BUYUK_HARF_SART`). Her iki durumda da GERCEK eslesmenin
# korundugu asagida ayrica sinaniyor -- "kalibi sil, yanlis bitsin"
# cozumu sinamayi da gecerdi ve arsivi bosaltirdi.
DURUMLAR += (
    # --- kelime icinde eslesme CIKMAMALI ---
    ("French warship, part of the EU Red Sea mission, escorted ships",
     (), ("WARSH",)),
    ("South Korea's presidential office: President Lee discussed "
     "warship building", (), ("WARSH",)),
    ("Rus denizaltının seyri Akdeniz'de izlendi", (), ("XAU",)),
    # --- ama GERCEGI eslesmeli ---
    ("Kevin Warsh Fed başkanlığı için öne çıktı", ("WARSH", "FED"), ()),
    ("Warsh: faiz indirimi için erken", ("WARSH",), ()),
    ("Altının onsu yeni rekor kırdı", ("XAU",), ()),
    ("Altınini satan yatırımcı", ("XAU",), ()),

    # --- "Sec." kisaltmasi SEC KURUMU DEGIL ---
    ("NATO Sec. Gen. Rutte: European allies prepared for attacks",
     (), ("SEC",)),
    ("WH Press Sec. Leavitt: No negotiations happening now", (), ("SEC",)),
    ("US Sec. of Defense Hegseth finishes remarks", (), ("SEC",)),
    # --- ama kurumun kendisi eslesmeli ---
    ("SEC Proposes New Regulation Crypto Assets", ("SEC",), ()),
    ("SEC'in Atkins'i: kripto yasası olsun veya olmasın", ("SEC",), ()),
)

DURUMLAR += (
    # === KURESEL VARLIKLAR ===========================================
    #
    # Bu 13 varlik grafta duruyordu ama KALIPSIZDI: hicbiri hicbir
    # habere baglanmiyordu ve sayfalari "Arsivde 0 haber" diyordu.
    # Kaliplar 28.044 gercek baslikta olculerek secildi; asagidaki
    # NEGATIF durumlar o olcumde ELENEN adaylarin ta kendisi.

    # --- NIKKEI: gazete mi, endeks mi ---
    # "nikkei" kalibi 50 baslik yakaliyordu ve cogu Nikkei GAZETESI.
    ("Nikkei: Sony Group, TSMC yeni nesil sensörleri üretecek",
     (), ("NIKKEI",)),
    ("Nikkei, Sony'nin Kumamoto tesisine yatırımını yazdı",
     (), ("NIKKEI",)),
    ("Nikkei 225 endeksi günü yükselişle kapattı", ("NIKKEI",), ()),

    # --- EA_TUFE: euro bolgesi mi, uye ulke mi ---
    # " hicp " 12 baslik yakaliyordu, HEPSI uye ulke verisiydi.
    ("İspanyolca HICP Finali (aylık): %0,00", (), ("EA_TUFE",)),
    ("Fransız HICP Finali (aylık): %0,60", (), ("EA_TUFE",)),
    ("İtalyan HICP Ön Hazırlık (yıllık): %3,20", (), ("EA_TUFE",)),
    ("Euro Bölgesi TÜFE Finali (yıllık): %2,90", ("EA_TUFE", "EA"), ()),

    # --- USDJPY / GBPUSD: VIRGUL BOSLUGA CEVRILIYOR ---
    # "usd jpy" ve "gbp usd" kaliplari para birimi LISTESINI
    # karsiliyordu. USDJPY bu yuzden `KALIPSIZ_SERBEST` icinde.
    ("Döviz Gücü Grafiği: En Güçlü: AUD, NZD, EUR, USD, JPY, CHF, GBP",
     (), ("USDJPY", "GBPUSD")),
    ("Döviz Gücü Grafiği: En Güçlü: GBP, USD, AUD, CAD, NZD, JPY",
     (), ("USDJPY", "GBPUSD")),
    # --- ama sterlin haberi GBPUSD'ye baglanmali ---
    ("Sterlin dolara karşı toparlanma arayışında", ("GBPUSD",), ()),

    # --- CN_BUYUME: "iCIN BUYUMEyi" alt dize tuzagi ---
    # Bastaki bosluk olmadan " iran "/"haziranin" hatasinin aynisi:
    # kalip 8 baslik yakaliyordu, HEPSI yanlis.
    ("Esnek politika kararları için büyümeyi ve enflasyonu izliyor",
     (), ("CN_BUYUME",)),
    ("Avrupa İmar Bankası Türkiye için büyüme tahminini değiştirdi",
     (), ("CN_BUYUME",)),
    # --- ama gercek Cin buyume haberi eslesmeli ---
    ("Çin büyümede beklentiyi aştı: Konutta düşüş sürüyor",
     ("CN_BUYUME", "CN"), ()),

    # --- BOE_FAIZ / BOJ_FAIZ: LIKIDITE OPERASYONU FAIZ DEGIL ---
    # " boe " (303) ve " boj " (357) kaliplari elendi: repo ve ILTR
    # operasyonu haberlerini bir FAIZ dugumune baglamak,
    # politika_faizi.py'nin belgeledigi yanlis-buyukluk hatasi.
    ("Bankalar, BoE kısa vadeli repo operasyonunda 126,1 milyar £ borç "
     "alıyor", (), ("BOE_FAIZ",)),
    ("BoE: Altı aylık ILTR operasyonunda tahsis edilen 2,80 milyar £",
     (), ("BOE_FAIZ",)),
    # --- ama faiz haberi eslesmeli ---
    ("Yatırımcılar BoE faiz artırımı bahislerini artırıyor",
     ("BOE_FAIZ",), ()),
    ("İngiltere Merkez Bankası faizi sabit tuttu", ("BOE_FAIZ",), ()),
    ("BOJ faizleri 31 yılın en yüksek seviyesine çıkarttı",
     ("BOJ_FAIZ",), ()),

    # --- ECB ile ECB_FAIZ AYRI (FED/FED_FAIZ ayriminin aynisi) ---
    # Kurum dugumu genis kalip tasir, faiz dugumu dar. "ECB
    # toplantisi" haberi faiz arsivine DUSMEMELI.
    ("ECB'den Kazaks: ECB faizler konusunda rahat bir durumda",
     ("ECB", "ECB_FAIZ"), ()),
    ("ECB yıllık raporunu yayımladı", ("ECB",), ("ECB_FAIZ",)),

    # --- DE10Y ve JGB ---
    ("Alman 10 Yıl Bund Verimi: %3,26", ("DE10Y",), ()),
    ("Alman tahvil faizleri en yüksek seviyede", ("DE10Y",), ()),
    ("BoJ's Himino: JGB piyasalarında bozulma görmüyorum",
     ("JGB",), ()),

    # --- FTSE 100 ile FTSE Russell AYRI SEY ---
    # " ftse " kalibi endeks SAGLAYICISINI da yakaliyordu.
    ("FTSE Russell 24 Türk şirketini endekslerinden çıkardı",
     (), ("FTSE",)),
    ("HSBC, 2026 yıl sonu FTSE 100 hedefini yükseltti", ("FTSE",), ()),
)


def main() -> int:
    b = _bellek_depo()
    hata = 0

    # Grafta karsiligi olmayan kalip, sessizce hicbir seye baglanmaz.
    kayip = varlik.dogrula()
    if kayip:
        print(f"HATA kaliplar grafta yok: {', '.join(kayip)}")
        hata += 1

    # NORMALLESTIRMEDEN SAG CIKMAYAN KALIP = SESSIZ KALIP.
    # Icinde kesme isareti/nokta/tire tasiyan bir kalip, aranan
    # metinde hicbir zaman bulunamaz; listede DURUR ve dogru GORUNUR.
    # Olculdu (2026-10-06): alti tane vardi, biri 38 basligi
    # kaciriyordu ("Fed'in faiz politikasi" -> FED_FAIZ yok).
    olu = varlik.olu_kaliplar()
    if olu:
        print(f"HATA normallestirmeden gecmeyen kalip: {', '.join(olu)}")
        hata += 1

    # KALIPSIZ VARLIK = SESSIZ BOSLUK.
    #
    # `dogrula()` ters yonu tutuyordu (kalip var, varlik yok). BU YON
    # TUTULMUYORDU ve olculen sonuc su (2026-10-29): grafa 13 kuresel
    # varlik eklenmis, yapisal iliskileri yazilmis, kalip
    # yazilmamisti. ECB_FAIZ'i 495 baslik aniyordu, bagli haber
    # sayisi SIFIRDI. 13 varlik sayfasi "Arsivde 0 haber" diyordu.
    #
    # Kalipsiz varlik yanlis baglanmaz, HIC baglanir -- bu yuzden
    # hicbir hata firlamiyor. Istisna `KALIPSIZ_SERBEST` icinde
    # gerekcesiyle yazilir.
    kalipsiz = varlik.kalipsiz_varliklar()
    if kalipsiz:
        print(f"HATA grafta duran kalipsiz varlik: {', '.join(kalipsiz)}")
        print("  kalip yaz ya da KALIPSIZ_SERBEST'e gerekcesiyle ekle")
        hata += 1

    # ISTISNA KUMESI BURADA ELLE YAZILI -- VE SEBEBI OLCULDU.
    #
    # Yukaridaki denetim tek basina KACIS KAPISI tasiyor: bir varligi
    # `KALIPSIZ_SERBEST`e eklemek denetimi SUSTURUYOR. Mutasyonla
    # olculdu (2026-10-29): DAX'a uydurma bir gerekce yazildiginda
    # butun sinamalar YESIL dondu.
    #
    # Kume MODULDEN OKUNMUYOR, elle yazili. Okumak hareketli hedef
    # olurdu: korudugu koddan beklentisini alan sinama, kendi
    # mutasyonunu gecer. Elle yazim, istisna eklemeyi bilincli bir
    # harekete ceviriyor -- sinama da guncellenmek zorunda kaliyor.
    BEKLENEN_KALIPSIZ = {"USDJPY"}
    serbest = set(varlik.KALIPSIZ_SERBEST)
    if serbest != BEKLENEN_KALIPSIZ:
        yeni = ", ".join(sorted(serbest - BEKLENEN_KALIPSIZ)) or "-"
        giden = ", ".join(sorted(BEKLENEN_KALIPSIZ - serbest)) or "-"
        print("HATA KALIPSIZ_SERBEST degismis "
              f"(eklenen: {yeni}; cikan: {giden})")
        print("  her istisna OLCULMUS bir gerekce ister; "
              "sinamadaki kume de guncellenmeli")
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
