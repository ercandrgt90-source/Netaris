"""Sirket basina bilanco analiz sayfasi -- olculmus tablo + AI yorumu.

    sektor_ozet.json -> Donem -> tablo (deterministik) -> AI yorumu -> sayfa

    python uret_bilanco_sayfa.py --sinir 3 --kuru-calis
    python uret_bilanco_sayfa.py            # kosu basina 60

YORUMSUZ SAYFA YAYIMLANMIYOR
----------------------------
Karar acik: "her bilanco yapay zeka yorumundan gececek". Yorum
uretilemezse (anahtar yok, model bos dondu, dogrulama dusurdu) o
sirket icin sayfa YAZILMIYOR. Yarim bir sayfa yayimlamak, sozu
tutmadigini sessizce ilan etmek olurdu.

TABLO DETERMINISTIK, YORUM MODELDEN
-----------------------------------
Sayfadaki her rakam `oranlar.py` ve `sektor_ozet.py` tarafindan
hesaplaniyor; model yalnizca onlari cumleye ceviriyor ve ciktisi
`yorumcu` tarafindan dogrulaniyor (girdide olmayan sayi -> metin
tamamen atilir).

SINIR VAR -- TOPLU URETIMDE DE
------------------------------
Kosu basina `--sinir 60`. Sinirsiz yapilmadi ve sebebi teknik: 324
model cagrisi tek bir CI kosusuna sigmaz, is zaman asimina ugrar ve o
kosuda uretilenlerin HICBIRI yazilmaz. Sinirli kosu yarim kalsa bile
yazdigini koruyor.

AMA 60 BIR DENEME SINIRI, KAPASITE DEGIL. Bu docstring uzun sure
"324 sirket ~6 CI kosusunda tamamlaniyor" diyordu; olculdu
(2026-10-21) ve gercek bunun yaklasik kirkta biri:

    13-20 Ekim   12 kosu, 16 yeni analiz   (~1,3 / kosu)
    20 Ekim      denenen 324, YAZILAN 0
                 180 zaten yayimlanmis
                 141 yorum yok: ucretsiz saglayici kotasi doldu

Gercek darbogaz UCRETSIZ AI KOTASI. Kosu yesil doner, dokum dogruyu
yazar, yalnizca sayfa cikmaz. Olcum: 2026-06-30 donemini bildiren
337 sirketin 221'inin sayfasi var, 116'sinin YOK.

Bu bir ariza degil -- yukaridaki "yorumsuz sayfa yayimlanmiyor"
kararinin ucretsiz kotayla carpimi. Ama yanlis bir kapasite modeli,
"neden bitmiyor" sorusunu yanlis yerde aratir.

TEKRAR URETMIYOR: sayfasi zaten olan sirket atlaniyor. Hat yeniden
kosturuldugunda ayni sayfayi yeniden yazmak, ayni model cagrisini
ikinci kez odemek demek.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bicim              # noqa: E402
import bilanco_ag         # noqa: E402
import bilanco_yorum      # noqa: E402
import guvenlik           # noqa: E402
import oranlar            # noqa: E402
import one_cikan          # noqa: E402
import sektor_okuma       # noqa: E402
import sektor_ozet        # noqa: E402
import uret_bilanco        # noqa: E402
import yayin              # noqa: E402

OZET = _KOK / "kaynak" / "sektor_ozet.json"
DEFTER = _KOK / "kaynak" / "sirketler.json"
SITE = _KOK.parent / "site" / "icerik" / "analizler"

#: Tek kosuda en fazla kac sayfa.
#:
#: TOPLU URETIM: 5'ten 60'a cikarildi. 324 sirket bu hizla ~6 CI
#: kosusunda (yaklasik uc saat) tamamlaniyor.
#:
#: SINIRSIZ YAPILMADI ve sebebi teknik: 324 model cagrisi TEK bir CI
#: kosusuna sigmaz, is zaman asimina ugrar ve o kosuda uretilen
#: sayfalarin hicbiri yazilmaz. Sinirli kosu, yarim kalsa bile
#: yazdigini KORUYOR -- her sirket kendi sayfasi yazilir yazilmaz
#: kaliciya geciyor.
#:
#: Sayfasi olan sirket atlandigi icin hat kendini adim adim
#: dolduruyor; kosu sayisi arttikca kalan is azaliyor.
VARSAYILAN_SINIR = 60

KALEMLER = (
    ("hasilat", "Hasılat"), ("brut_kar", "Brüt kâr"),
    ("faaliyet_kari", "Faaliyet kârı"), ("favok", "FAVÖK"),
    ("net_kar", "Net kâr"), ("ozkaynak", "Özkaynak"),
    ("aktif_toplami", "Aktif toplamı"), ("net_borc", "Net borç"),
    ("faaliyet_nakit_akisi", "Faaliyet nakit akışı"),
    ("yatirim_harcamasi", "Yatırım harcaması"),
)


#: "Son dort donem" bolumunun basligi -- TEK YERDE.
#:
#: `bilanco_tazele` bu bolumu TASIMAYAN sayfalari bulmak icin ayni
#: sabiti okuyor. Iki yerde ayri yazilsaydi, baslik degistigi gun
#: goc kuyrugu sessizce BUTUN sayfalari eksik sayar ve her kosuda
#: hepsini yeniden kurardi -- bu depo o sinif kusuru kumulatif
#: gocunde bir kez yasadi.
SERI_BASLIGI = "## Son dört dönem"


def _mlr(d):
    return f"{bicim.sayi(d / 1e9, 2)} milyar TL" if d is not None else "—"


def _degisim(simdi, once) -> float | None:
    """Reel yuzde degisim. TMS 29 nedeniyle TUFE ile ARITILMIYOR.

    KAP tablolari enflasyon muhasebesine gore duzenleniyor; iki donem
    de RAPOR TARIHI alim gucuyle ifade ediliyor. Uzerine TUFE
    uygulamak ayni duzeltmeyi ikinci kez yapmak -- cift sayim olur.

    HESAP `oranlar.py`NIN KORUMALI ISLEVIYLE YAPILIYOR
    --------------------------------------------------
    Burada satir ici bolme vardi ve paydada `abs(once)` kullaniyordu:
    yani ONCEKI DEGER NEGATIFKEN de bir yuzde uretiyordu.
    `oranlar._yuzde_degisim` bunu reddediyor ve gerekcesi orada
    yazili: "Eski deger sifir ya da negatifse anlamsizdir. Zarardan
    kara gecis gibi durumlarda yuzde degisim yaniltici oldugu icin
    hesaplanmaz."

    OLCULDU, YAYINDAYDI (2026-10-15): FENER'in ozkaynagi -0,04
    milyardan 8,79 milyara cikmisti ve sayfada **%21391,8** yaziyordu.
    Negatiften pozitife gecis onemli bir haber ama YUZDE olarak
    anlamsiz; o gecis ayri bir sinyal olarak anlatilmali.

    Bu, ayni sinifin UCUNCU ornegi: kural `oranlar.py` icinde yazili,
    ikinci bir yer onu tasimadan yeniden hesapliyor (oncekiler
    `_oranlari` ve ara donem ceyrek sayisi).
    """
    # SIFIRA COK YAKIN TABAN AYRICA ELENIYOR. `_yuzde_degisim`
    # yalnizca `eski <= 0` bakiyor; 1e-9 gibi kucuk ama POZITIF bir
    # taban oradan gecer ve milyonluk bir yuzde uretir. Eski
    # koddaki bu koruma korunuyor.
    if once is not None and 0 < once < 1e-6:
        return None
    return oranlar._yuzde_degisim(simdi, once)


def _saglayici_kapandi() -> bool:
    """Ucretsiz saglayici BU KOSUDA kapandi mi.

    AYRI ISLEV, ICE AKTARMA ICERIDE: `yorumcu` modulu ag ve ortam
    degiskeni okuyor; modul basinda ice aktarmak sinamalari ona
    bagimli kilardi. Ice aktarilamazsa KAPALI DEGIL sayiliyor --
    bilinmezlik yuzunden uretimi durdurmak, calisan bir kosuyu
    bosuna kesmek olurdu.

    Anthropic yolunda mandal yok; o zaman da False donuyor ve hat
    eskisi gibi isliyor.
    """
    try:
        import yorumcu                                # noqa: PLC0415
    except ImportError:                                # pragma: no cover
        return False
    return bool(getattr(yorumcu, "cf_kota_doldu", lambda: False)())


def degisim_haritasi(simdi, once) -> dict:
    """{alan: reel yuzde degisim} -- modele verilecek hazir hesaplar.

    NEDEN AYRI ISLEV
    ----------------
    Satir ici bir sozluk kurulumuydu ve MUTASYON KACTI: `{}` yazmak
    sinamayi gecip alani OLU birakiyordu. Cagrinin `degisimler=`
    anahtarini TASIDIGINI gormek yetmiyor; icinde gercekten deger
    OLDUGU da sinanmali. Adi olan bir islev dogrudan sinanabiliyor.

    HESAP BURADA YAPILMIYOR: `_degisim`e devrediliyor, cunku o
    `oranlar._yuzde_degisim`e EK olarak sifira cok yakin tabani da
    eliyor. Sayfadaki tablo da ayni cagriyi kullaniyor -- modele
    giden yuzde ile okura basilan yuzde AYNI hesabin sonucu.
    """
    return {ad: _degisim(getattr(simdi, ad, None),
                         getattr(once, ad, None) if once else None)
            for ad, _etiket in KALEMLER}


def govde_kur(kod, unvan, sektor, donem, d, oran, medyan, n, yorum,
              mali_not="", alt_sektor="",
              once=None, seri=None) -> str:
    """Sayfanin govdesi. TABLO deterministik, YORUM modelden."""
    s = []

    # OZET EN BASTA -- meta aciklama da buradan okunuyor.
    #
    # Onceden govde TABLOYLA basliyordu ve `_ozet_ayikla` ilk
    # paragraf olarak ham tabloyu aliyordu; arama sonucunda ve kart
    # ozetinde boru isaretleri gorunuyordu. Ozet bir CUMLE olmali.
    if yorum:
        s += ["## Özet", "", yorum, ""]

    # YILLIK DEGISIM -- SEVIYE DEGIL, HAREKET.
    #
    # Bu bolum olmadan sayfa yalnizca "hasilat 662 milyar TL"
    # diyebiliyordu. Okurun sordugu soru ise degisim. Onceki yil
    # AYNI CEKIMDEN geliyor, ek istek yok.
    #
    # Yoksa bolum HIC yazilmiyor -- bos bir tablo, veri oldugunu
    # sanmaya yol acar.
    if once is not None:
        satir = []
        for ad, etiket in KALEMLER:
            y = _degisim(getattr(d, ad, None), getattr(once, ad, None))
            if y is not None:
                satir.append(f"| {etiket} | {bilanco_yorum._yuzde(y)} |")
        if satir:
            s += [f"## {donem} — bir yıl öncesine göre", "",
                  "| Kalem | Reel değişim |", "| --- | ---: |", *satir, "",
                  "*Finansal tablolar TMS 29 enflasyon muhasebesine göre "
                  "düzenlenmiştir; yukarıdaki değişimler **reeldir**, "
                  "ayrıca enflasyondan arındırmak gerekmez.*", ""]

    s += [f"## {donem} dönemi ölçümleri", "",
         "| Kalem | Değer |", "| --- | ---: |"]
    for ad, etiket in KALEMLER:
        v = getattr(d, ad, None)
        if v is not None:
            s.append(f"| {etiket} | {_mlr(v)} |")

    # SON DORT DONEM -- EGILIM, TEK NOKTA DEGIL.
    #
    # Yukaridaki iki bolum "su an ne kadar" ve "gecen yila gore ne
    # kadar degisti" sorularini cevapliyor. Ikisi de IKI NOKTA, yani
    # egilim gostermiyor: tek seferlik bir sicrama ile surekli bir
    # yukselis ayni gorunuyor.
    #
    # Dort donem bir TAM yillik dongu: mevsimsel bir isletmede inis
    # mevsimden mi egilimden mi, ancak boyle ayirt ediliyor.
    #
    # EK ISTEK YOK: seri `donem_getir(seri=True)` ile AYNI cekimden
    # geliyor (olculdu: CIMSA icin 3 HTTP istegi, seri oncesiyle
    # ayni). Ayri bir cekim 325 sirkette ~975 fazladan istek olurdu.
    #
    # IKIDEN AZ DONEMDE BOLUM YAZILMIYOR: tek sutunluk bir "egilim"
    # tablosu, yukaridaki olcum tablosunu tekrar etmekten baska bir
    # sey yapmaz ve egilim oldugu izlenimi verir.
    if seri and len(seri) >= 2:
        basliklar = [ad for ad, _iso, _dd in seri]
        s += ["", SERI_BASLIGI, "",
              "| Kalem (milyar TL) | " + " | ".join(basliklar) + " |",
              "| --- |" + " ---: |" * len(basliklar)]
        for ad, etiket in KALEMLER:
            hucre = [getattr(dd, ad, None) for _a, _i, dd in seri]
            # SATIRIN TAMAMI BOSSA YAZILMIYOR -- tire dizisi, veri
            # oldugu izlenimi verir.
            if all(v is None for v in hucre):
                continue
            yazi = [bicim.sayi(v / 1e9, 2) if v is not None else "—"
                    for v in hucre]
            s.append(f"| {etiket} | " + " | ".join(yazi) + " |")
        s += ["", "*Dönemler **ardışık** çeyreklerdir ve her biri "
              "TMS 29 enflasyon muhasebesine göre düzenlenmiş "
              "tablolardan alınmıştır; aralarındaki fark **reeldir**. "
              "Yukarıdaki \"bir yıl öncesine göre\" bölümü ise aynı "
              "dönemi bir yıl öncesiyle kıyaslar — mevsimselliği "
              "dışarıda bırakmak için.*"]

    if oran and not medyan:
        # KIYAS KUMESI YOKSA BOLUM HIC YAZILMIYOR -- BOS SUTUNLA DEGIL.
        #
        # Olculdu (2026-10-14): spor kulupleri mali yillari ayni olsa
        # da AYNI UC AYI bildirmiyor. GSRAY ve BJKAS haziran-agustos
        # bilancosunu acikladi, FENER ve TSPOR hala mart-mayista. Her
        # grup IKI sirket, yani `sektor_ozet.EN_AZ_SIRKET` esigi
        # altinda ve medyan URETILMIYOR.
        #
        # Onceki kural sayfayi tumden ATLIYORDU. Ama sayfanin geri
        # kalani gercek: olcum tablosu, bir yil oncesine gore degisim
        # ve AI yorumu kiyasa bagli degil. GSRAY'in aciklanmis
        # bilancosunu haftalarca yayimlamamak, okura hicbir sey
        # vermemek demekti.
        #
        # Bos bir medyan sutunu da yazilmiyor: her satirda tire
        # gormek, kiyas yapilmis izlenimi verirdi.
        #
        # SEBEP SOYLENIYOR. "Karsilastirma yok" demek yetmez; okur
        # neden olmadigini bilmeli.
        s += ["", "## Sektör karşılaştırması bu dönem yapılmadı", "",
              f"{sektor} sektöründe **aynı dönemi bildiren** en az "
              f"{sektor_ozet.EN_AZ_SIRKET} şirket yok, bu yüzden sektör "
              f"medyanı üretilmedi ve karşılaştırma tablosu yazılmadı. "
              f"İki şirketin ortasını \"sektör medyanı\" diye sunmak, "
              f"ölçülmemiş bir şeyi ölçülmüş gibi göstermek olurdu."]
        if mali_not:
            s += ["", mali_not]
        # YON DOGRU YAZILIYOR. Ilk yazim "Aşağıdaki" diyordu ama o
        # bolumler sayfada YUKARIDA: sira "bir yil oncesine gore" ->
        # "donem olcumleri" -> bu bolum.
        s += ["", "Yukarıdaki **bir yıl öncesine göre** değişim ve ölçüm "
              "tablosu şirketin kendi geçmişine dayanıyor; onlar için "
              "kıyas kümesi gerekmiyor."]
    elif oran:
        # "AYNI DONEMI BILDIREN" IBARESI BILEREK -- OLCULDU, YAYINDAYDI.
        #
        # Medyan eskiden sektorun TAMAMINDAN kuruluyordu ve sektorde
        # baska bir uc ayi bildiren sirket varsa sonuc bozuluyordu.
        # İletişim sektorunun brut marj medyani -%32,03 cikiyordu;
        # ucu futbol kulubuydu ve donemleri mart-mayisti. Yalnizca
        # ayni donemi bildirenlerle medyan +%24,94 -- 57 puan fark.
        #
        # Kume degisti, cumle de degisti: okura kiyasin NEYE gore
        # yapildigi dogru soylenmeli.
        s += ["", f"## Sektör içindeki konum", "",
              f"Karşılaştırma {sektor} sektöründe **aynı dönemi bildiren** "
              f"{n} şirketin **medyanına** göre yapılıyor. Medyan seçildi "
              f"çünkü tek bir şirketin uç değeri ortalamayı tek başına "
              f"taşıyabiliyor."]
        if mali_not:
            s += ["", mali_not]
        s += ["", "| Oran | Şirket | Sektör medyanı |",
              "| --- | ---: | ---: |"]
        for anahtar, ad in sektor_ozet.ORANLAR:
            v = oran.get(anahtar)
            if v is None:
                continue
            katsayi = anahtar in ("cari_oran", "borc_ozkaynak")
            b = ((lambda x: bicim.sayi(x, 2)) if katsayi
                 else bilanco_yorum._yuzde)
            m = medyan.get(anahtar)
            s.append(f"| {ad} | {b(v)} | {b(m) if m is not None else '—'} |")
        s += ["", "*Medyana göre konum bir sıralamadır, değerlendirme "
              "değildir. Hangi oranın yüksek olmasının iyi olduğu iş "
              "modeline göre değişir.*"]


    # ONE CIKAN OLCUMLER -- lehte / aleyhte, KURALDAN turetilmis.
    #
    # Okurun sordugu soru gercek: bu tabloda ne lehte, ne aleyhte
    # isliyor? Bunu yazmak, "iyi/kotu" demekten farkli -- fark
    # KAYNAKTA. Bir yargi kaynagini gostermez ("bu sirket guclu");
    # bir bulgu gosterir ("faaliyet nakit akisi net karin %38'i").
    # Her madde olcumunu YANINDA tasiyor.
    #
    # Sektore gore BASTIRMA var: yuksek borcluluk bankada olagan,
    # sanayide degil. Her sektorde ayni sinyali eksi saymak,
    # `sektor_okuma`da "bu olagandir" deyip burada tersini yazmak
    # olurdu -- okuru kendi sayfamiz icinde celiskiye dusururdu.
    s += one_cikan.markdown(d, once, oran, medyan, sektor)

    # SEKTOR OKUMA KILAVUZU -- DETERMINISTIK, MODELDEN DEGIL.
    #
    # TERA sayfasini zengin yapan sey model cikarimi degildi; kritik
    # cumle bir SEKTOR BILGISIYDI ("araci kurumda sirkete kalan tutar
    # brut kardir"). Sirkete gore degismeyen bir bilgiyi her sirket
    # icin ayri ayri uretmek, ayni seyi 325 kez satin almak olurdu.
    #
    # Sektor basina bir kez yazildi: marjinal maliyet SIFIR, ayni
    # sektordeki iki sayfa ayni seyi ayni sekilde soyluyor ve gelecek
    # ceyreklerde de calisiyor -- cunku bilgi KODDA, model ciktisinda
    # degil.
    #
    # Sektor taninmiyorsa bolum HIC yazilmiyor. Yanlis bir okuma
    # kilavuzu kilavuzsuzluktan kotudur: okur ona guvenip yanlis
    # kalemi okur.
    # ALT SEKTOR DE VERILIYOR -- kilavuz yanlis sirkete yazilmasin.
    # Olculdu: İletişim kilavuzu telekom icin yazilmis ama sektordeki
    # alti sirketin ucu futbol kulubu, ikisi yayinci. Gerekce
    # `sektor_okuma.ALT_KAPSAM` uzerinde yazili.
    s += sektor_okuma.markdown(sektor, alt_sektor)

    # YASAL UYARI GOVDEDE OLMAK ZORUNDA.
    #
    # OLCULDU, PAHALIYA MAL OLDU. 2026-08-20 kosusunda 277 sirket
    # `guvenlik: [YASAK] '(eksik)'` ile atlandi: `yayinlanabilir()`
    # uyariyi METNIN ICINDE ariyor, ben ise govdeye koymamistim.
    #
    # Haber tarafinda uyari sayfa sablonunun altbilgisinde duruyor ve
    # oradan geliyordu; bilanco govdesini SIFIRDAN ben kurdugum icin
    # o miras yoktu. Denetim dogru calisti, eksik olan govdeydi.
    #
    # Maliyeti sessiz degil GERCEKTI: 277 model cagrisi yapildi,
    # metinler uretildi ve HEPSI atildi. Uretimden SONRA yapilan bir
    # denetim, girdi maliyetini geri getirmiyor.
    #
    # Ayrica bu sayfa TAM OLARAK uyarinin gerekli oldugu yer: tek bir
    # sirketin mali tablosu, sektor siralamasiyla birlikte.
    s += ["", "---", "",
          "*Bu sayfa ölçülmüş mali tablo verisinden üretilmiştir ve "
          "**yatırım tavsiyesi değildir.** Sektör medyanına göre konum "
          "bir sıralamadır, değerlendirme değildir.*"]
    return "\n".join(s)


#: Ret kaydinin yazilacagi depo. Haber hatti ayni tabloyu kullaniyor.
VT = _KOK / "netaris.db"


def ret_yaz(kod: str, unvan: str, donem: str, neden: str,
            model: str, ham: str) -> None:
    """Reddedilen bilanco yorumunu `ai_ret`e yazar.

    NEDEN VAR
    ---------
    Olculdu (2026-08-28): bilanco kosusu 328 sirketten 287'sini
    atladi ve 286'sinin sebebi "girdide olmayan sayi" idi -- yani
    model, verilmeyen rakamlar uretti. O 286 kaydin TAMAMI gunluge
    basilip kayboldu; `ai_ret` tablosunda bilanco hattindan TEK
    SATIR yoktu (hepsi haber adresliydi).

    Sonucu su: hangi sayilarin uydurulduğu, hangi sektorde
    yogunlastigi, saglayici degisince duzelip duzelmedigi
    OLCULEMIYOR. Is akisindaki `saglayici` girdisi tam bu
    karsilastirma icin konmus ve olcecek verisi yok.

    Haber hatti bunu zaten yapiyor ve gerekcesi ayni satirlarla
    yazilmis: "Ilk calistirmada dokuz redden hicbirinin sebebi depoda
    yoktu ve gunluge bakmadan tani konamiyordu."

    HAM CIKTI DA SAKLANIYOR: "neden reddedildi" sorusu ancak metne
    bakarak cevaplanir. `_ham` daha once yakalanip ATILIYORDU.

    YAZAMAMAK ISI DUSURMEZ: uretim raporlamadan onemli. Depo kilitli
    ya da salt-okunursa sessizce geciliyor.
    """
    try:
        import contextlib                              # noqa: PLC0415
        import sqlite3                                 # noqa: PLC0415
        import beyin                                   # noqa: PLC0415
        # `closing` SART. `with sqlite3.connect(...)` yalnizca ISLEMI
        # kapatiyor, BAGLANTIYI degil -- dosya tanimlayicisi acik
        # kaliyor. Windows'ta bu, dosyanin silinememesine yol aciyor
        # (testte WinError 32 ile yakalandi); her yerde ise 328 sirketlik
        # bir kosuda 328 acik baglanti demek.
        with contextlib.closing(sqlite3.connect(VT)) as b, b:
            b.execute(
                "INSERT INTO ai_ret"
                " (adres, baslik, neden, model, ham, kayit_ani)"
                " VALUES (?,?,?,?,?,?)",
                (f"bilanco:{kod}:{donem}", (unvan or kod)[:200],
                 neden or "", model or "", (ham or "")[:2000],
                 beyin.simdi()))
    except Exception as e:                             # pragma: no cover
        print(f"    (ret kaydedilemedi: {e})")


def kiyas_kumesi(v: dict, kod: str) -> tuple[dict, int, str, str]:
    """Sirketin KIYASLANACAGI medyan, sirket sayisi, donem adi, aciklama.

    NEDEN SEKTOR TEK BIR KUME DEGIL
    -------------------------------
    Olculdu (2026-10-13): sektordeki sirketler AYNI UC AYI
    bildirmiyor. Spor kuluplerinin mali yili 31 Mayis'ta bitiyor
    (GSRAY, FENER, BJKAS, TSPOR) ve son bildirdikleri donem
    mart-mayis; ayni sektordeki TTKOM'un donemi nisan-haziran.

    Iki ayri zaman araligini ayni medyanda toplamak, farki tek
    basina mevsimsellikten dogurur. Olculen sonuc: İletişim
    sektorunun brut marj medyani -%32,03 cikiyordu; yalnizca ayni
    donemi bildirenlerle +%24,94.

    OLCUT BITIS TARIHI, MALI YIL SONU DEGIL. ARENA'nin mali yili
    martta bitiyor ama bildirdigi uc ay nisan-haziran, yani TTKOM
    ile AYNI -- onu ayirmak gereksiz bir ayrim olurdu.

    Donem adi ay adlariyla yaziliyor: kaynagin "Q1 2027" etiketi
    Ekim 2026'da okuru yanlis yere goturur.

    BITISI COZULEMEYEN SIRKET ANA KUMEDE KALIYOR: ayrim yapmanin
    ispat yuku ayrim yapanda. Kaynaktaki gecici bir aksaklik sirketi
    sessizce kiyassiz birakmamali.
    """
    # MALI TAKVIM OKURA SOYLENIYOR.
    #
    # Mali yili aralikta bitmeyen sirkette "2026 mart-mayis donemi"
    # basligi dogru ama EKSIK: okur neden baska bir aralik gorduyunu
    # bilmiyor. Olculen bilgi sayfada kullanilmazsa olculmemis
    # sayilir.
    ay = (v.get("mali") or {}).get(kod)
    mali_not = ""
    if ay:
        mali_not = (f"Şirketin mali yılı {bilanco_ag.ay_adi(ay)} "
                    f"sonunda bitiyor, takvim yılıyla örtüşmüyor; "
                    f"bu yüzden dönemi ay adlarıyla yazılıyor.")
    iso = (v.get("bitis") or {}).get(kod)
    ana = v.get("ana_donem") or ""
    # ETIKET COGUNLUGA DEGIL TARIHE BAGLI -- OLCULDU (2026-10-13).
    #
    # Ilk surum ana gruba SEKTORUN takvim etiketini veriyordu.
    # İletişim sektoru bunu curuttu: yedi sirketin DORDU futbol
    # kulubu, yani ana donem 2026-05-31 oldu ve FENER "2026 2.
    # çeyrek" etiketini devraldi -- oysa donemi mart-mayis.
    #
    # `donem_etiketi` takvim ceyregiyse alisilmis adi ("2026 2.
    # çeyrek"), degilse ay adlarini veriyor. Hangi grubun cogunlukta
    # oldugu artik etiketi etkilemiyor.
    etiket = (bilanco_ag.donem_etiketi(iso, bilanco_ag.VARSAYILAN_CEYREK)
              if iso else v["donem"])
    if not iso or iso == ana:
        return (v.get("medyan") or {}, v.get("sirket_sayisi") or 0,
                etiket, mali_not)
    g = (v.get("donem_gruplari") or {}).get(iso) or {}
    return (g.get("medyan") or {}, g.get("sirket_sayisi") or 0,
            etiket, mali_not)


def sirket_isle(kod, bilgi, sektor, donem, oran, medyan, n,
                kuru=False, mali_not="") -> tuple[bool, str]:
    alt_sektor = bilgi.get("alt_sektor") or ""
    d, once, eksik, seri = bilanco_ag.donem_getir(
        kod, donem, sektor_tr=sektor, ciftli=True, seri=True)
    if d is None:
        return False, "eksik: " + ", ".join(eksik[:3])

    # SIRKETIN KENDI ORANI, SAYFANIN KENDI VERISINDEN.
    #
    # Oran eskiden `sektor_ozet.json`dan geliyordu; seviye tablosu
    # ise burada TAZE cekilen `d`den. Ikisi ayri kaynak oldugu icin
    # ayni sayfada IKI AYRI DONEM anlatilabiliyordu ve olculdu
    # (2026-10-13): 258 bilanco sayfasinin 203'u boyleydi.
    #
    # Ara donemin kac ceyrekten olustugunu tek kaynaga baglamak o
    # kusuru kapatti ama KURAL duzeyinde kapatti. Burada YAPISAL
    # olarak kapaniyor: oran, sayfanin gosterdigi tablonun ta
    # kendisinden turetiliyor, yani ayrilmasi imkansiz.
    #
    # MEDYAN YINE OZETTEN: o kesitsel bir istatistik, tek sirketin
    # verisinden uretilemez.
    kendi = uret_bilanco._oranlari(d)
    if kendi:
        oran = kendi

    # DEGISIMLER SAYFAYI KURAN HESAPTAN GELIYOR.
    #
    # `govde_kur` ayni `_degisim`i kullaniyor, yani modele verilen
    # yuzde ile sayfada basilan yuzde AYNI cagrinin sonucu. Ikisini
    # ayri hesaplamak, bu depoda uc kez yasanan kusur sinifi: kural
    # `oranlar.py`de yaziliyken ikinci bir yer onu tasimadan yeniden
    # hesapliyor.
    girdi = bilanco_yorum.girdi_kur(
        kod, bilgi["unvan"], sektor, donem, simdi=d, once=once,
        oranlar_kendi=oran, medyanlar=medyan, sirket_sayisi=n,
        degisimler=degisim_haritasi(d, once))

    metin, model, sebep, ham = bilanco_yorum.yorum_uret(girdi)
    if not metin:
        # YORUMSUZ SAYFA YAYIMLANMIYOR -- bkz. modul basi.
        ret_yaz(kod, bilgi.get("unvan", ""), donem, sebep, model, ham)
        return False, f"yorum yok: {sebep}"

    govde = govde_kur(kod, bilgi["unvan"], sektor, donem, d, oran,
                      medyan, n, metin, mali_not=mali_not,
                      alt_sektor=alt_sektor, once=once, seri=seri)

    tamam, bulgular = guvenlik.yayinlanabilir(govde)
    if not tamam:
        # BU RET DE KAYDEDILIYOR. Ikinci basarisizlik bicimi ve
        # birincisinden AYRI bir tani gerektiriyor: sayi uydurma
        # modelin sorunu, guvenlik takilmasi SABLONUN ya da yonergenin
        # sorunu olabilir. Ayirt edebilmek icin ikisi de depoda.
        ret_yaz(kod, bilgi.get("unvan", ""), donem,
                f"güvenlik: {bulgular[0] if bulgular else '?'}",
                model, metin)
        return False, f"güvenlik: {bulgular[0] if bulgular else '?'}"

    if kuru:
        return True, "kuru çalışma"
    yol = yayin.yaz_sektorel(
        govde=govde, sirket=bilgi["unvan"], kod=kod, donem=donem,
        sektor=sektor,
        kaynak="Çeyreklik mali tablolardan türetildi; sektör medyanı "
               "Netaris hesabı")
    return True, str(yol.name)


def bitis_haritasi(ozet: dict) -> dict:
    """kod -> donem bitis tarihi (ISO). Iki kaynaktan birlestiriliyor.

    SEKTOR OZETI AUTORITE ama KAPSAMI DAR: `bitis` alani yalnizca
    yeni kodla tazelenmis sektorlerde var (olculdu 2026-10-16:
    324 sirketin 31'i).

    NOBET DEFTERI daha genis: nobetci her kosuda 60 sirkete bakiyor
    ve her birinin son donem bitisini yaziyor -- 234 kayit, ozetteki
    sirketlerin 214'u. Ek istek YOK, zaten toplanmis veri.

    Ozet once geliyor: o, sayfanin kuracagi veriyle AYNI kosuda
    olculdu; nobetci kaydi daha eski olabilir.
    """
    harita: dict[str, str] = {}
    try:
        import json                                  # noqa: PLC0415
        nobet = json.loads(
            (DEFTER.parent / "bilanco_nobet.json").read_text(
                encoding="utf-8"))
        for kod, iso in (nobet.get("sirket") or {}).items():
            if isinstance(iso, str) and iso:
                harita[kod.upper()] = iso
    except (OSError, ValueError):
        pass
    for v in ozet.values():
        if isinstance(v, dict):
            for kod, iso in (v.get("bitis") or {}).items():
                if iso:
                    harita[kod.upper()] = iso
    return harita


def _tazelik(iso: str) -> int:
    """Siralama anahtari: KUCUK = daha taze. Bilinmiyorsa en sona.

    BILINMEYEN NEDEN SONA: o sirketin ne zaman bildirdigini
    BILMIYORUZ ve bilmedigimizi one cikarmak, olculmemis bir
    tazeligi olculmus gibi sunmak olurdu. Nobetci her kosuda 60
    sirkete bakiyor, yani bilinmeyenlerin sayisi kendiliginden
    azaliyor.
    """
    if not iso:
        return 0
    try:
        return -int(iso.replace("-", ""))
    except ValueError:
        return 0


def kuyruk_kur(ozet: dict, bekleyen: set, sektor_suzgeci: str = "",
               sayfasi_olan: set | None = None,
               bitisler: dict | None = None,
               yayimlanmis: set | None = None) -> list:
    """Uretim kuyrugu -- BEKLEYENLER basta.

    Doner: (oncelik, ilk_gorulme, sektor, sektor_verisi, kod, oran)
    demetlerinden olusan liste.

    NEDEN AYRI ISLEV
    ----------------
    Sira `main` icinde satir iciydi ve sinanamiyordu: ilk yazilan
    sinama mantigi YENIDEN YAZIYORDU, dolayisiyla uretim kodundaki
    oncelik kaldirildiginda KIRMIZI DONMEDI. Mantigi kopyalayan bir
    sinama, o mantigi olcmuyor.

    ONCELIK NEDEN VAR
    -----------------
    Uretim ceyreklige cevrildi ama bir kisim sirket hala ESKI
    (kumulatif) sayfayla duruyor; ceyrekligi uretilene kadar da
    silinemiyorlar. Site o sure boyunca IKI YONTEMI birden tasiyor.

    Sira alfabetikti ve `--sinir` kuyrugun sonunu kesiyordu. Olculdu
    (2026-09-15): bekleyen 28 sirketin 24'u ilk 60'ta, 4'u 141. siraya
    kadar dagilmisti -- gocu bitirmek icin gereksiz yere IKINCI bir
    kosu gerekiyordu.

    GERI KALANIN SIRASI DEGISMIYOR: ikincil anahtar ilk gorulme
    sirasi, yani ayni oncelikte alfabetik duzen korunuyor.
    """
    # HIC SAYFASI OLMAYAN SIRKET EN ONDE.
    #
    # Siralama "once kumulatif gocu bitir" diye kurulmustu ve o zaman
    # dogruydu. Ama olculdu (2026-10-14): ozetteki 324 sirketten
    # 109'unun HIC sayfasi yok -- dort futbol kulubu dahil. Okur o
    # sirketler icin HICBIR SEY goruyor; bicimi eski bir sayfa ise
    # yine okunabiliyor.
    #
    # Yani sira tersine kurulmus: once hic olmayani yaz, sonra
    # bicimini tazele.
    #
    # Kaynak kosu basina ancak birkac sirketi veriyor (olculdu: 324
    # sirkette 151 "eksik", cogu HTTP 429), yani sira dogrudan
    # "okurun ne zaman gorecegini" belirliyor.
    # EN TAZE BILDIRIM ONCE.
    #
    # Sayfasi olmayan sirketler arasinda sira ALFABETIKTI (sektor,
    # sonra kod) ve bu bir haber sitesinde yanlis olcut: iki ay once
    # bildiren sirketle BUGUN bildiren sirket ayni siraya giriyor.
    #
    # Olculdu (2026-10-16): 324 sirketin 227'si 2026-06-30 donemini
    # bildiriyor, DORT futbol kulubu ise 2026-08-31 -- yani tek
    # basina en yeni donem onlarda. Alfabetik sirada 69. siradaydilar
    # ve gunde ~3 sayfa yazilabildigi icin haftalar beklerlerdi.
    #
    # Ucretsiz AI kotasi gunde birkac sayfaya izin veriyor (bkz.
    # `bilanco-yayin-hizi`), yani SIRA dogrudan "okur neyi ne zaman
    # gorecek" demek. En taze bildirim once.
    # BOS KUME ILE "VERILMEDI" AYNI SEY DEGIL.
    #
    # Ilk yazim `sayfasi_olan or set()` yapiyordu ve `if
    # sayfasi_olan and ...` ile kullaniyordu; bos kume yanlis
    # ("hicbir sirketin sayfasi yok") degil "olcut uygulanmasin"
    # diye okunuyordu. Sinama bunu yakaladi: hicbir sayfa
    # yayimlanmamisken HICBIR sirket "sayfasi yok" sayilmiyordu ve
    # tazelik siralamasi hic calismiyordu.
    bitisler = bitisler or {}
    kuyruk: list = []
    for sektor, v in sorted(ozet.items()):
        if sektor_suzgeci and sektor != sektor_suzgeci:
            continue
        for kod, oran in sorted(v["sirket"].items()):
            k = kod.upper()
            # SAYFASI VAR AMA DONEMI ESKI -> EN ONE.
            #
            # Olculdu (2026-10-30, bilanco sezonunun ilk gunleri):
            # sayfasi olan bir sirket YENI CEYREK bildirdiginde
            # oncelik 2'ye, yani 324 kisilik kuyrugun DIBINE
            # dusuyordu. `--sinir 60` ilk 60'i aliyor ve o 60'in
            # tamami oncelik 0 (94 sirket sayfasiz). Sonuc:
            #
            #     42 bayat sirketin kuyruk sirasi 94, 95, 96...
            #     ilk 60 icinde olan: 0
            #
            # Yani sayfasi bir kez yazilmis sirket, bir daha ASLA
            # yeni doneme gecmiyordu. Agustosta calismis gorunmesi
            # tesaduftu: o gun sirketlerin cogunun HIC sayfasi yoktu,
            # yani ayni sirketler zaten oncelik 0'daydi. Sayfalar
            # dolduk ca kilit kendiliginden kapandi.
            #
            # Sessiz kusur: hicbir sey hata vermiyor, kosu yesil
            # donuyor, gunluk "zaten yayimlanmis" bile demiyor --
            # sirkete SIRA GELMIYOR.
            #
            # OLCUT IKINCI KEZ TANIMLANMIYOR: donem etiketi, uretim
            # dongusunun atlama kararinda kullandigi `kiyas_kumesi`
            # ile AYNI cagridan geliyor. Etiket kurali degisirse
            # ikisi birlikte degisir. `kiyas_kumesi` saf: yalnizca
            # `ozet` sozlugunu okuyor, ag istegi yok.
            _bayat = (yayimlanmis is not None
                      and sayfasi_olan is not None
                      and k in sayfasi_olan
                      and (k, kiyas_kumesi(v, kod)[2]) not in yayimlanmis)
            if sayfasi_olan is not None and k not in sayfasi_olan:
                oncelik, ikincil = 0, 0   # hic sayfasi yok
            elif _bayat:
                oncelik, ikincil = 0, 1   # sayfa var, donemi eski
            elif k in bekleyen:
                oncelik, ikincil = 1, 0   # bicim gocu bekliyor
            else:
                oncelik, ikincil = 2, 0
            # Tazelik YALNIZCA sayfasi olmayanlarda sirayi
            # belirliyor. Bicim gocunde sira zaten tamamlanmis bir
            # listeyi bitirmek uzerine; orada tazelik anlamsiz.
            taze = _tazelik(bitisler.get(k, "")) if oncelik == 0 else 0
            # ESIT TAZELIKTE SAYFASIZ ONCE.
            #
            # Ikisi de bugun bildirdiyse okur acisindan fark var:
            # sayfasiz sirkette HICBIR SEY goruyor, bayat sayfada
            # bir onceki ceyregi goruyor. Once hicligi doldur.
            kuyruk.append((oncelik, taze, ikincil, len(kuyruk),
                           sektor, v, kod, oran))
    kuyruk.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    # Cagiranlar besli bekliyor: tazelik ve ikincil anahtarlar
    # siralamadan sonra dusuruluyor.
    return [(a, c, s, v, k, o) for a, _b, _i, c, s, v, k, o in kuyruk]


def _bilanco_sayfasi(kategori: str) -> bool:
    """Bu sayfa bir bilanco analizi mi.

    Sabit `kumulatif_temizle`den okunuyor: ayni ayrimi iki yerde
    tanimlamak, birinin degisip otekinin unutulmasi demekti. O modul
    de ayni sebeple donem bicimi yerine KATEGORI alanina gecmisti.
    """
    try:
        from kumulatif_temizle import KATEGORI          # noqa: PLC0415
    except ImportError:                                 # pragma: no cover
        KATEGORI = "Bilanço Analizi"
    return kategori.strip() == KATEGORI


def _yayimlanmis() -> set[tuple[str, str]]:
    """Yayimlanmis (kod, donem) ciftleri -- ON BILGIDEN okunur.

    DOSYA ADINDAN OKUNMUYOR ve sebebi olculdu. Onceki surum
    `p.stem` tarayip `f"{kod}-{donem}"` damgasini ariyordu; ama
    `yayin.yaz_sektorel` dosyayi TERS sirada adlandiriyor:

        damga aranan : tera-2026-6
        dosya adi    : 2026-6-tera
        eslesme      : YOK

    Yani atlama HIC calismiyordu. Gorunur bir belirtisi de yoktu:
    hat sessizce ayni sirketi yeniden uretip AYNI MODEL CAGRISINI
    ikinci kez odeyecek, ustune ayni sayfayi ezecekti. 324 sirketlik
    toplu uretimde bu, kosu basina tekrarlanan bir maliyet demek.

    On bilgideki `kod:` ve `donem:` alanlari dosya adlandirma
    kuralindan BAGIMSIZ; adlandirma yarin degisse de bu okuma
    calisir.
    """
    if not SITE.exists():
        return set()
    cikti: set[tuple[str, str]] = set()
    for p in SITE.glob("*.md"):
        kod = donem = kat = ""
        for satir in p.read_text(encoding="utf-8").splitlines()[:25]:
            if satir.startswith("kod:"):
                kod = satir[4:].strip().upper()
            elif satir.startswith("donem:"):
                donem = satir[6:].strip()
            elif satir.startswith("kategori:"):
                kat = satir[9:].strip()
            elif satir == "---" and kod:
                break
        # BILANCO SAYFASI KATEGORIDEN ANLASILIYOR, DONEM BICIMINDEN DEGIL.
        #
        # Suzgec once `"/" in donem` idi ve gerekcesi soyleydi:
        # "bilanco donemi her zaman YIL/AY bicimi". O gerekce DONEMLER
        # KUMULATIFKEN dogruydu (2026/6). Uretim CEYREKLIGE cevrilince
        # etiket "2026 2. ceyrek" oldu -- icinde "/" YOK.
        #
        # Olculdu (2026-09-15): 230 ceyreklik sayfanin HICBIRI
        # "yayimlanmis" sayilmiyordu; yalnizca 29 kumulatif sayfa
        # sayiliyordu. Yani atlama yine calismiyordu ve bu islevin
        # varlik sebebi tam olarak buydu: "hat sessizce ayni sirketi
        # yeniden uretip AYNI MODEL CAGRISINI ikinci kez odeyecek".
        #
        # Sonucu somut: her kosu bastaki ayni sirketleri yeniden
        # uretiyor, sinira takiliyor ve KUYRUKTAKILERE HIC SIRA
        # GELMIYOR. Ceyreklik karsiligi bekleyen 29 kumulatif sayfa
        # haftalardir bu yuzden bekliyordu.
        #
        # Varsayim, sebebinden sonra yasadi. Artik ayrim KATEGORIYE
        # dayaniyor -- `kumulatif_temizle` de ayni sebeple ayni
        # alani kullaniyor ve sabit ORADAN okunuyor.
        if kod and donem and _bilanco_sayfasi(kat):
            cikti.add((kod, donem))
    return cikti


def sebep_turu(not_: str) -> str:
    """Atlama notunu DOKUMDE gruplanacak TURE indirger.

    Kural eskiden "ilk `:`e kadar al" idi ve gerekcesi dogruydu:
    `eksik: hasilat, net_kar` notunda iki nokta sonrasi SIRKETE OZEL
    ayrinti, onu saymak 325 ayri "sebep" uretirdi.

    Ama ayni kural `yorum yok: ...` icin YANLIS. Orada iki nokta
    sonrasi sirkete ozel degil, ARIZANIN TURU -- ve dokumun cevaplamasi
    gereken soru tam olarak o.

    Olculdu (2026-09-16): 15 Eylul kosusu "yazilan 1, atlanan 322" ile
    bitti ve dokum soyle diyordu:

        171  zaten yayimlanmis
        150  yorum yok          <- 150 kez NE OLDU?
          1  eksik

    Sebep URETILMISTI (`yorum_uret` donduruyor) ve `ai_ret` tablosuna
    da yaziliyor -- ama `bilanco.yml` geri yazma adimi `netaris.db`yi
    gondermiyor, yani o satirlar kosucuda kalip siliniyor. Iki ayri
    yoldan ayni cevap kayboluyordu. Bu depoda tekrarlayan sinif:
    cevap uretiliyor, okunabilir yerde durmuyor.

    Ikinci parca da kendi icinde `:` tasiyabiliyor
    (`girdide olmayan sayi: 300, 27`) ve ORASI yine degerdir; bu
    yuzden yalnizca ilk parcasi aliniyor ve uzunlugu kirpiliyor --
    "anthropic HTTP 400 -- Your credit balance is too low..." gibi
    uzun bir gerekce dokumu ikinci bir listeye cevirmesin.
    """
    parcalar = [p.strip() for p in not_.split(":")]
    bas = parcalar[0] or not_
    if bas != "yorum yok" or len(parcalar) < 2:
        return bas
    ayrinti = parcalar[1].strip()
    return f"{bas}: {ayrinti[:44]}" if ayrinti else bas


def _dokum(sebepler: dict[str, int], yazilan: int = -1,
           atlanan: int = -1) -> None:
    """Atlama sebeplerini SIKLIGA gore dok.

    Ozet satiri "kac tane" diyor, bu "neden" diyor -- ve ilki tek
    basina yaniltici olabiliyor. "atlanan 325" hem "hepsi zaten
    yayimlanmis" hem "hicbiri uretilemedi" anlamina gelebilir;
    aralarindaki fark ise her sey demek.

    2026-08-20'de tam bu yasandi: kosu "yazilan 0, atlanan 325" ile
    bitti ve sebebi 325 satiri tek tek okumadan anlasilmadi.

    KOSU OZETINE DE YAZILIYOR
    -------------------------
    Olculdu (2026-08-28): kosu 44 dakika calisti ve 149 adaydan
    yalnizca IKISINI yazdi. Sebep dokumu gunluge basilmisti ama
    gunluk 328 satir; ustelik Actions gunlukleri API'den kimlik
    dogrulamasi istiyor (403). Yani "neden 2 sayfa" sorusu, cevabi
    URETILMIS olmasina ragmen okunamadi.

    `GITHUB_STEP_SUMMARY` kosu sayfasinin EN USTUNDE gorunuyor.
    Ayni bilgi, aramadan.
    """
    if not sebepler and yazilan < 0:
        return
    if sebepler:
        print("sebep dökümü:")
        for tur, n in sorted(sebepler.items(), key=lambda x: -x[1]):
            print(f"  {n:>4}  {tur}")

    import os                                          # noqa: PLC0415
    yol = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not yol:
        return
    satirlar = ["### Bilanço sayfaları", ""]
    if yazilan >= 0:
        satirlar.append(f"**yazılan {yazilan}, atlanan {atlanan}**")
        satirlar.append("")
    if sebepler:
        satirlar += ["| adet | sebep |", "|---:|---|"]
        satirlar += [f"| {n} | {tur} |"
                     for tur, n in sorted(sebepler.items(),
                                          key=lambda x: -x[1])]
    try:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(chr(10).join(satirlar) + chr(10))
    except OSError as e:                               # pragma: no cover
        # Ozet yazilamamasi isi DUSURMEZ: sayfalar zaten uretildi.
        print(f"(kosu ozetine yazilamadi: {e})")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=VARSAYILAN_SINIR)
    a.add_argument("--sektor")
    a.add_argument("--kuru-calis", action="store_true")
    n = a.parse_args()

    # SAGLAYICI DURUMU EN BASTA, TEK SATIRDA.
    #
    # NEDEN VAR. 2026-08-20'de kosu "yazilan 0, atlanan 325" ile bitti
    # ve sebebi log'dan OKUNAMADI: ozet satiri kac sayfa yazildigini
    # soyluyor ama NEDEN yazilmadigini soylemiyordu. Sebebi ogrenmek
    # icin 325 satirin arasindan tek tek okumak gerekiyordu.
    #
    # "Ne oldu" ile "neden oldu" ayri sorular; ozet yalnizca ilkini
    # cevapliyordu. Simdi ikisi de basta yaziyor.
    #
    # DEGER DEGIL VARLIK yaziliyor. Anahtarin kendisi log'a asla
    # dusmemeli -- log'lar paylasilir, ekran goruntusu alinir.
    import os                                          # noqa: PLC0415
    sys.path.insert(0, str(_KOK / "ai"))
    import yorumcu                                     # noqa: PLC0415
    s = yorumcu.saglayici()
    if s:
        print(f"AI sağlayıcı: {s}")
    else:
        eksik = [ad for ad in ("ANTHROPIC_API_KEY", "CLOUDFLARE_API_TOKEN",
                               "CLOUDFLARE_ACCOUNT_ID")
                 if not os.environ.get(ad, "").strip()]
        print("AI sağlayıcı: YOK -- hiçbir sayfa yazılmayacak.")
        print(f"  tanımsız değişken: {', '.join(eksik)}")
        print("  (Anthropic için ANTHROPIC_API_KEY; ya da Workers AI "
              "için CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID)")

    # SABLON KAPISI -- TEK BIR MODEL CAGRISINDAN ONCE.
    #
    # NEDEN VAR. 2026-08-20'de govde yasal uyariyi icermiyordu ve 277
    # sirket `guvenlik: [YASAK]` ile atlandi. Ama once 277 MODEL
    # CAGRISI YAPILDI: metinler uretildi, odendi, sonra atildi.
    # Uretimden SONRA yapilan denetim girdi maliyetini geri getirmiyor.
    #
    # Kusur sirkete ozel degildi, SABLONA aitti -- yani ilk sirkette
    # de bellidir. Sahte bir govde kurup denetimden gecirmek, ayni
    # bilgiyi SIFIR maliyetle veriyor.
    #
    # Kapi kapaliysa hat DURUYOR. Devam etmek, bilerek para yakmak
    # olurdu.
    class _Sahte:
        hasilat = 1.0e9
        net_kar = 2.0e8
        ozkaynak = 5.0e8
        aktif_toplami = 9.0e8
        brut_kar = favok = faaliyet_kari = None
        net_borc = faaliyet_nakit_akisi = yatirim_harcamasi = None

    ornek = govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026/6", _Sahte(),
                      {"net_marj": 20.0}, {"net_marj": 12.0}, 5,
                      "Örnek yorum cümlesi.")
    tamam, bulgular = guvenlik.yayinlanabilir(ornek)
    if not tamam:
        print("ŞABLON DENETIMDEN GEÇMIYOR -- hiç model çağrılmadı.")
        for b in bulgular[:3]:
            print(f"  {b.aciklama}")
        print("  Sebep şirkete özel değil, gövdeye ait; düzeltmeden "
              "çalıştırmak 325 çağrıyı boşa harcar.")
        return 1

    if not OZET.exists():
        print(f"{OZET} yok -- önce uret_bilanco.py çalışmalı.")
        return 1
    ozet = json.loads(OZET.read_text(encoding="utf-8"))
    defter = json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]

    var = _yayimlanmis()

    yazilan = atlanan = 0
    # SEBEP SAYIMI. Ozetin altinda "hangi sebepten kac tane" yaziyor.
    # 325 satiri okumak yerine uc satir okunuyor; ve sebepler
    # SIRALANIYOR, en cok goruleni once.
    sebepler: dict[str, int] = {}
    # GOCU BITIRMEK, YENI SAYFA URETMEKTEN ONCELIKLI.
    #
    # Uretim ceyreklige cevrildi ama bir kisim sirket hala ESKI
    # (kumulatif) sayfayla duruyor; ceyrekligi uretilene kadar da
    # silinemiyorlar. Site o sure boyunca IKI YONTEMI birden tasiyor --
    # okur ayni bolumde "2026/6" ve "2026 2. ceyrek" goruyor.
    #
    # Sira alfabetikti ve `--sinir` kuyrugun sonunu kesiyordu.
    # Olculdu (2026-09-15): bekleyen 28 sirketin 24'u ilk 60'ta, 4'u
    # 141. siraya kadar dagilmisti -- yani gocu bitirmek icin gereksiz
    # yere IKINCI bir kosu gerekiyordu.
    #
    # Bekleyenler one aliniyor; geri kalanin sirasi DEGISMIYOR.
    # Ayrim `kumulatif_temizle.tara` icinde yasiyor ve oradan
    # cagriliyor -- ikinci bir kopya, birinin duzeltilip otekinin
    # unutulmasi demekti.
    try:
        import kumulatif_temizle as _kt                # noqa: PLC0415
        _kum, _cey = _kt.tara()
        _bekleyen = {k.upper() for k in _kum if k not in _cey}
    except Exception:                                  # pragma: no cover
        _bekleyen = set()
    if _bekleyen:
        print(f"{len(_bekleyen)} şirket kümülatif karşılığını bekliyor")

    # HIC SAYFASI OLMAYAN SIRKETLER -- kuyrugun EN BASINA.
    # Gerekcesi `kuyruk_kur` uzerinde yazili.
    _sayfasi_olan = {k for (k, _d) in var}
    _hic = sum(1 for s, v in ozet.items() if isinstance(v, dict)
               for k in (v.get("sirket") or {})
               if k.upper() not in _sayfasi_olan)
    if _hic:
        print(f"{_hic} şirketin HİÇ sayfası yok -- kuyruğun başına alındı")

    _bitisler = bitis_haritasi(ozet)
    kuyruk = kuyruk_kur(ozet, _bekleyen, n.sektor, _sayfasi_olan,
                        _bitisler, var)

    for _oncelik, _sira, sektor, v, kod, oran in kuyruk:
        if yazilan >= n.sinir:
            print(f"\nsınıra ulaşıldı ({n.sinir})")
            print(f"yazılan {yazilan}, atlanan {atlanan}")
            _dokum(sebepler, yazilan, atlanan)
            return 0
        # SAGLAYICI KAPANDIYSA MALI TABLO DA CEKILMIYOR.
        #
        # `sirket_isle` ONCE tabloyu cekiyor, SONRA yorum istiyor.
        # Yorum kapisi kapandiginda kalan sirketlerin hepsi yine de
        # cekiliyordu -- yazilamayacagi KESIN olan sayfalar icin.
        #
        # OLCULDU (kosu #56, 2026-10-29): kota ilk sirkette kapandi,
        # hat 324 sirketi cekmeye DEVAM etti (~970 istek) ve
        # stockanalysis 8 ardisik redden sonra kapandi. Bedelini bir
        # sonraki adim odedi: "bölüm göçü" 186 sayfanin SIFIRINI
        # tasiyabildi, hepsi "eksik: hasilat, net_kar" dedi.
        #
        # BASKASININ SUNUCUSU: yazilamayacak bir sayfa icin istek
        # atmak, kendi isimize yaramadigi gibi kaynaga da yuk.
        if _saglayici_kapandi():
            print(f"\nsağlayıcı kapandı -- kalan {len(kuyruk) - yazilan - atlanan}"
                  f" şirket için mali tablo ÇEKİLMİYOR")
            print(f"yazılan {yazilan}, atlanan {atlanan}")
            _dokum(sebepler, yazilan, atlanan)
            return 0
        bilgi = defter.get(kod)
        if not bilgi:
            continue
        # DONEME GORE ATLIYOR, SONSUZA DEK DEGIL.
        #
        # Once yalnizca koda bakiyordu: sirketin bir sayfasi varsa
        # bir daha HIC uretilmiyordu. Yeni ceyrek geldiginde de
        # atlanacakti -- yani "bir sonraki bilancolar" hic
        # yayimlanmazdi. Sessiz bir kilit: hata vermeden, hicbir
        # sey yapmadan.
        #
        # Artik kod VE donem birlikte, ON BILGIDEN araniyor
        # (bkz. `_yayimlanmis`).
        # KIYAS KUMESI SIRKETE GORE -- bkz. `kiyas_kumesi`.
        # Takvim disi mali yila sahip sirket kendi takvimindekilerle
        # kiyaslaniyor ve donem adini ay adlariyla aliyor.
        _medyan, _n, _donem, _mali_not = kiyas_kumesi(v, kod)
        if (kod.upper(), _donem) in var:
            atlanan += 1
            sebepler["zaten yayımlanmış"] = \
                sebepler.get("zaten yayımlanmış", 0) + 1
            continue
        # KIYASSIZ SAYFA ARTIK YAZILIYOR -- bolum olmadan.
        #
        # Onceki kural sayfayi tumden atliyordu. Olculdu
        # (2026-10-14): spor kuluplerinin her donem grubu IKI sirket,
        # yani esik altinda ve medyan hic uretilmiyor. GSRAY'in
        # aciklanmis bilancosu bu yuzden haftalarca yayimlanmadan
        # kalirdi.
        #
        # Sayfanin geri kalani kiyasa bagli DEGIL: olcum tablosu, bir
        # yil oncesine gore degisim ve AI yorumu. Bolum yazilmiyor ve
        # NEDENI soyleniyor; bkz. `govde_kur`.
        ok, not_ = sirket_isle(kod, bilgi, sektor, _donem, oran,
                               _medyan, _n, kuru=n.kuru_calis,
                               mali_not=_mali_not)
        if ok:
            yazilan += 1
            print(f"  {kod:<8}{not_}")
        else:
            atlanan += 1
            # Sebebi TURUNE gore topla -- bkz. `sebep_turu`.
            # `eksik:` icin ":" sonrasi sirkete ozel ayrinti ve
            # atiliyor; `yorum yok:` icin ARIZANIN TURU ve
            # korunuyor. Ikisine ayni kurali uygulamak, dokumun
            # cevaplamasi gereken soruyu goturuyordu.
            _tur = sebep_turu(not_)
            sebepler[_tur] = sebepler.get(_tur, 0) + 1
            print(f"  {kod:<8}ATLANDI -- {not_}")

    print(f"\nyazılan {yazilan}, atlanan {atlanan}")
    _dokum(sebepler, yazilan, atlanan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
