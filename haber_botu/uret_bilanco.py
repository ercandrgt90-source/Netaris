"""Bilanco hatti -- sektor sektor cek, olc, sektor medyanini kur.

    sirket defteri -> sektor -> mali tablo -> Donem -> sektor medyani

    python uret_bilanco.py --sektor "Temel malzeme"
    python uret_bilanco.py --hepsi          # butun sektorler
    python uret_bilanco.py --sektor X --kuru-calis   # yazmadan olc

NEDEN SEKTOR SEKTOR
-------------------
Sektor medyani ancak sektorun TAMAMI cekildikten sonra hesaplanabilir.
Sirket sirket ilerleyip her birinde "sektorum ne durumda" diye sormak,
her sirket icin sektoru bastan cekmek demekti.

SIRKET SECIMI -- OLCULEBILIR KURAL
----------------------------------
"Hangi sirketler" editoryal bir soru ve cevabi burada YAZILI:
sektoru bilinen ve mali tablosu YETERLI olan her sirket. Ikisi de
olculebilir; "onemli sirketler" gibi tanimsiz bir olcut kullanilmadi.

Sektoru bilinmeyen 441 kaydin cogu BIST'te hisse senedi islem
gormuyor (banka, finansal kiralama, araci kurum, yatirim ortakligi);
onlar zaten bu kapiya gelmiyor.

CEKILEN VERI YAZILMADAN ONCE DENETLENIYOR
-----------------------------------------
Her sirketin bilancosu muhasebe ozdeslikleriyle sinaniyor
(`bilanco_ag.ozdeslik_denetimi`). Tutmayan sirket ATLANIYOR ve
sebebi raporlaniyor -- bir sirketin bozuk verisi sektor medyanini da
bozar.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_ag      # noqa: E402
import oranlar         # noqa: E402
import sektor_ozet     # noqa: E402

#: KAP ARA DONEM BILDIRIM SINIRLARI (konsolide, aya gore).
#:
#: Sirketler mali tablolarini donem bitiminden sonra belli bir sure
#: icinde bildiriyor. Hat her yarim saatte kosarsa AYNI veriyi tekrar
#: tekrar cekip hicbir sey degistirmez; kaynaga yuk, bize maliyet.
#:
#: Bildirimlerin YOGUNLASTIGI aylar:
#:   3 aylik  -> Mayis
#:   6 aylik  -> Agustos
#:   9 aylik  -> Kasim
#:   12 aylik -> Mart
#: Ayin tamamı acik birakildi: sirketler ayni gun bildirmiyor.
BILDIRIM_AYLARI = {3: 12, 5: 3, 8: 6, 11: 9}

#: PENCERE KURALI ARTIK `bilanco_ag`DE.
#:
#: Kurali hem bu dosya hem `bilanco_nobetci` kullaniyor. Iki yere
#: yazmak, `ARA_SN`in basina geleni tekrarlamak olurdu: ayni adi
#: tasiyan iki sabitten biri sessizce donmustu ve uyarlamayi hic
#: gormuyordu.
#:
#: Sabit `bilanco_ag.BILDIRIM_PENCERESI_GUN` olarak OKUNUYOR, ice
#: ALINMIYOR -- `from ... import SABIT` bir FOTOGRAF cekiyor ve tam
#: o tuzagi geri getirirdi.

#: Yeni kapsam, oncekinin bu oraninin altina duserse dosya YAZILMAZ.
#:
#: Olculdu (2026-09-14): kosu yesil bitti ve kapsam 327 sirketten
#: 47'ye dustu; ardindan sayfa uretimi 11 saniyede bos dondu. Tek bir
#: kotu kosu, hattin tamamini bosa dusurdu ve hicbir yerde kirmizi
#: gorunmedi.
#:
#: 0,6 secildi: bir sektorun gecici olarak cekilememesi normal
#: (11 sektorde biri ~%9 kayip), ucte birden fazlasinin birden
#: dusmesi ariza. Buyume ve kucuk dalgalanma serbest.
KUCULME_ESIGI = 0.6

#: Sektorun donemini belirlemek icin en fazla kac sirkete sorulur.
#:
#: Once TEK sirkete soruluyordu ve o istek basarisiz olunca butun
#: sektor atlaniyordu. Olculdu (2026-09-14): 11 sektorun 8'i boyle
#: elendi, kapsam 327 sirketten 47'ye dustu ve kosu YESIL bitti.
#:
#: Sektor supurmesinin SURE BUTCESI (dakika). Asilinca kalan
#: sektorler atlaniyor ve o ana kadarki veri NORMAL YOLDAN yaziliyor.
#:
#: NEDEN VAR -- olculdu 2026-09-15.
#:
#: `sektor_ozet.json` TEK SEFERDE, dongunun en sonunda yaziliyor.
#: Yani kosu ortada kesilirse o ana kadarki butun emek cope gidiyor:
#: yarim kalan bir kosu, hic kosmamis bir kosuyla ayni sonucu
#: veriyordu.
#:
#: O gun calisan kosu "Bilanco verisi" adiminda 97 DAKIKAYI gecti ve
#: hala tek satir yazmamisti. Is akisinin kendi siniri
#: `timeout-minutes: 330` -- yani en kotu durumda bes buçuk saat
#: calisip SIFIR uretebilirdi.
#:
#: Butce dolunca durmak veri kaybettirmiyor: cekilmeyen sektorler
#: `onceki_ozet`ten geliyor (birlestirme) ve sira BAYATLIGA gore
#: kuruldugu icin bir sonraki kosu kaldigi yerden devam ediyor. Uc
#: duzenek birlikte yakinsiyor.
SURE_BUTCESI_DK = 45

#: Bes yeterli: ayni sektordeki bes sirketin hepsinin ayni anda
#: cekilememesi, tek bir sirketin cekilememesinden cok daha guclu bir
#: ariza isareti -- o durumda sektoru atlamak dogru. Maliyet en kotu
#: ihtimalle sektor basina dort ek istek.
DONEM_DENEME = 5


def kapsam(ozet: dict) -> int:
    """Ozetin kac sirketi kapsadigi."""
    return sum(len(v.get("sirket") or {})
               for v in (ozet or {}).values() if isinstance(v, dict))


def sektor_donemi(sektor_tr: str, son_donem, ceyrek_etiketi) -> str:
    """Sektorun donem etiketi -- ILK YANIT VEREN sirketten. Yoksa "".

    NEDEN BIRDEN FAZLA SIRKET
    -------------------------
    Once yalnizca sektorun ILK sirketine soruluyordu. O tek istek
    basarisiz olunca BUTUN SEKTOR atlaniyordu.

    Olculdu (2026-09-14): kosu YESIL bitti ve kapsam 327 sirketten
    47'ye dustu -- 11 sektorun 8'i bu tek satirda elendi. Ardindan
    sayfa uretimi 11 saniyede bos dondu ve bekleyen 29 bilanco icin
    hicbir sey uretilmedi. Veri adimi 16 dakika yerine 131 saniye
    surdu, cunku elenen sektor basina yalnizca BIR basarisiz istek
    yapiliyordu.

    Tek bir sirketin gecici olarak cekilememesi, o sektordeki otuz
    sirketin hepsini kaybettirmemeli.

    ISLEVLER DISARIDAN VERILIYOR (`son_donem`, `ceyrek_etiketi`):
    kural boylece agsiz sinanabiliyor. Satir ici kalsaydi
    sinanamazdi ve bu depoda sinanmayan kural eskiyor.
    """
    for kod, _ in sektordeki(sektor_tr)[:DONEM_DENEME]:
        try:
            son = son_donem(kod)
        except Exception:                             # noqa: BLE001
            continue
        finally:
            # KAYNAGA NAZIK DAVRANMA -- bkz. `bilanco_ag.ara_ver`.
            # Bu yoklama her sektorde kosuyor; beklemesiz hali veri
            # adiminin basina onlarca ardisik istek ekliyordu.
            bilanco_ag.ara_ver()
        if not son:
            continue
        etiket = ceyrek_etiketi(*son)
        if etiket:
            return etiket
    return ""


def kosu_ozeti(satirlar: list[str]) -> None:
    """Kosu sayfasinin ustune yazar (GitHub Actions).

    NEDEN GEREKLI
    -------------
    Birlestirmeden sonra yarim kalan kosu artik KIRMIZI donmuyor --
    dogrusu bu, cunku cekilebilen sektorlerin sayfalari uretilmeli.
    Ama "yesil ama bozuk" tam olarak 13 gunluk kesintiyi doguran
    sessizlikti: hat calisiyor gorunuyordu, icerik donmustu.

    Kosu yesil kalsin ama EKSIK oldugunu sayfanin ustunde soylesin.
    """
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if not yol:
        return
    try:
        with open(yol, "a", encoding="utf-8") as f:
            for satir in satirlar:
                print(satir, file=f)
    except OSError:                                   # pragma: no cover
        pass


def _simdi_iso() -> str:
    """Saniye cozunurluklu UTC damgasi."""
    from datetime import datetime, timezone         # noqa: PLC0415
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def butce_doldu(gecen_dk: float, butce_dk: float, islenen: int) -> bool:
    """Sektor supurmesi burada kesilmeli mi.

    NEDEN AYRI ISLEV
    ----------------
    Karar `main` icinde satir iciydi ve sinanamiyordu. Bu depoda
    mantigi KOPYALAYAN bir sinama daha once mutasyonu kacirdi
    (`kuyruk_kur`): uretimdeki kural kaldirildiginda sinama yine
    yesil kaldi, cunku olctugu sey kendi kopyasiydi.

    ILK SEKTOR HER ZAMAN ISLENIYOR (`islenen` sifirken False).
    Bu bir ozen degil, KORUMA: butce sifir ya da cok kucuk
    verildiginde dongu hic donmeden cikardi, `cikti` yalnizca onceki
    veriyi tasirdi ve kosu "tazelenen 0" diye biterdi. Daha kotusu,
    `--sektor` ile tek sektorluk kosularda butce o tek sektoru de
    atlardi -- yani en cok is goren yol, hic is gormezdi.

    Esik KATI (`>`): tam butcede duran bir kosu, butceyi "asmadan"
    bitmis sayilir.
    """
    return bool(islenen) and gecen_dk > butce_dk


def mevcut_ozet() -> dict:
    """Diskteki ozeti verir. Okunamazsa BOS -- uydurulmaz."""
    if not HEDEF.exists():
        return {}
    try:
        d = json.loads(HEDEF.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return d if isinstance(d, dict) else {}


def sirket_sayisi(sektor: dict | None) -> int:
    """Bir sektor kaydindaki sirket sayisi."""
    return len(((sektor or {}).get("sirket")) or {})


def kapsam_coktu(yeni: int, onceki: int) -> bool:
    """Yeni kapsam, oncekine gore KATASTROFIK bicimde kucuk mu.

    AYRI ISLEV OLMASI BILEREK: kural `main()` icinde satir ici kalsaydi
    sinanamazdi ve bu depoda sinanmayan kural eskiyor.

    Onceki kapsam BILINMIYORSA (dosya yok ya da bozuk) cokme YOK
    sayiliyor: ilk kosuda yazmayi engellemek, korumanin kendisini
    kilide cevirirdi.
    """
    if onceki <= 0:
        return False
    return yeni < onceki * KUCULME_ESIGI


def donem_acik(bugun=None, nobetci=None) -> tuple[bool, str]:
    """Bugun bilanco cekmenin anlamli oldugu bir anda miyiz?

    Doner: (acik_mi, aciklama). Kapaliyken de ACIKLAMA doner --
    "neden calismadi" sorusu loga bakinca cevaplanabilsin.

    UC KAPI: TAKVIM, OLAY VE PENCERE
    --------------------------------
    Takvim (`BILDIRIM_AYLARI`) KONSOLIDE bildirim son tarihlerine
    gore kurulmus: Mart, Mayis, Agustos, Kasim. Ama konsolide
    OLMAYAN sirketler donem bitiminden otuz gun sonra bildiriyor --
    9 aylik tablolar EKIM SONUNDA gelmeye basliyor ve hattin
    penceresi Kasim'da aciliyor. Arada kalan haftalarda bildirimler
    yayimlaniyor, biz hicbir sey cekmiyoruz.

    Takvimi genisletmek tahmini buyutmek olurdu. Onun yerine OLCUM
    eklendi: `bilanco_nobetci` kaynakta yeni bir ceyrek belirip
    belirmedigine BAKIYOR (sirket basina tek istek, 0,3 saniye).
    Nobetci yeni ceyrek gormusse takvim kapaliyken de hat ACILIYOR.

    Yani takvim artik UCUZ BIR ON SUZGEC, karar OLCUMDE. Nobetci
    yoksa ya da okunamazsa davranis eskisi gibi -- yalnizca takvim.

    AMA BAYRAK BIR OLAYDIR, BIR DURUM DEGIL. Kosu sonunda
    `bilanco_nobetci --kapat` onu INDIRIYOR; bu dogru, cunku olay
    ISLENDI. Yanlis olan, hattin "is kaldi mi" sorusunu ayni bayraga
    sormasi: bayrak inince ekim boyunca kapi kapaniyor ve ozet tek
    bir kosunun fotografinda DONUYOR (olcum `bilanco_ag.BILDIRIM_PENCERESI_GUN`
    yaninda).

    UCUNCU KAPI o yuzden PENCERE: nobetcinin kaynakta gordugu en yeni
    donem bitisinden bu yana kac gun gectigi. Olay bir kez olur,
    pencere SURER. Ek istek yok -- `son_bitis` nobet defterinde
    zaten yazili.
    """
    import datetime as _dt
    bugun = bugun or _dt.date.today()

    if nobetci is None:
        try:
            import bilanco_nobetci as nobetci       # noqa: PLC0415
        except Exception:                            # noqa: BLE001
            nobetci = None
    son_bitis = None
    if nobetci is not None:
        try:
            if nobetci.donem_acildi_mi():
                return True, "nobetci kaynakta YENI CEYREK gordu"
        except Exception:                            # noqa: BLE001
            pass
        try:
            son_bitis = nobetci.nobet_oku().get("son_bitis")
        except Exception:                            # noqa: BLE001
            son_bitis = None

    acik, gun = bilanco_ag.pencere_acik(son_bitis, bugun)
    if acik:
        return True, (f"{son_bitis} donemi bildirim penceresinde "
                      f"({gun}. gun / {bilanco_ag.BILDIRIM_PENCERESI_GUN})")

    ceyrek = BILDIRIM_AYLARI.get(bugun.month)
    if ceyrek is None:
        return False, (f"{bugun.month}. ay bildirim ayi degil "
                       f"(bildirim aylari: {sorted(BILDIRIM_AYLARI)}), "
                       f"nobetci yeni ceyrek gormedi ve "
                       f"{son_bitis or 'bilinmeyen'} donemi bildirim "
                       f"penceresi DISINDA ({gun}. gun / "
                       f"{bilanco_ag.BILDIRIM_PENCERESI_GUN})")
    return True, f"{ceyrek} aylik donem bildirimleri"


DEFTER = _KOK / "kaynak" / "sirketler.json"
HEDEF = _KOK / "kaynak" / "sektor_ozet.json"

#: SIRKETLER ARASI BEKLEME ARTIK BURADA DEGIL.
#:
#: Bu dosyada `ARA_SN = 0.5` duruyordu ve `bilanco_ag.ARA_SN` ile
#: AYNI ADI tasiyan AYRI bir sabitti. Kaynak "yavasla" dediginde
#: `bilanco_ag._yavasla()` yalnizca KENDI degerini buyutuyor; bu
#: kopya 0,5'te KALIYORDU. Yani bu adim uyarlamayi hic gormuyordu:
#: gunluk "istek araligi 8.0 sn" yazarken burada hala yarim saniye
#: bekleniyordu.
#:
#: Ayni adi tasiyan iki sabitten birinin sessizce donmasi, bu
#: depoda tekrar eden bir kusur. Bekleme artik TEK YERDEN:
#: `bilanco_ag.ara_ver()`.


def _defter() -> dict:
    return json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]


def sektordeki(sektor_tr: str) -> list[tuple[str, dict]]:
    """Sektordeki BENZERSIZ sirketler. Hisse siniflari tekillestirilir.

    Is Bankasi'nin bes kodu var; besini de cekmek ayni sirketi bes kez
    saymak ve sektor medyanini o sirkete dogru cekmek olurdu.
    """
    gorulen: set[str] = set()
    cikti: list[tuple[str, dict]] = []
    for kod, v in sorted(_defter().items()):
        if v.get("sektor_tr") != sektor_tr:
            continue
        kimlik = v.get("kap_kimlik") or kod
        if kimlik in gorulen:
            continue
        gorulen.add(kimlik)
        cikti.append((kod, v))
    return cikti


def sektor_isle(sektor_tr: str, donem_etiketi: str, ceyrek: int = 2,
                sinir: int | None = None) -> dict:
    """Bir sektorun tamamini ceker, olcer ve medyanini kurar."""
    sirketler = sektordeki(sektor_tr)
    if sinir:
        sirketler = sirketler[:sinir]
    print(f"\n=== {sektor_tr}  ({len(sirketler)} şirket)")

    olculen: dict[str, dict] = {}
    atlanan: list[tuple[str, str]] = []
    #: kod -> mali yilin bittigi ay. Medyan gruplari bundan kuruluyor.
    mali: dict[str, int | None] = {}
    #: kod -> donem bitis tarihi (ISO). Takvim disi sirkette donem
    #: adi buradan uretiliyor; takvim ceyregi onlar icin yanlis.
    bitis: dict[str, str] = {}
    #: Onceki yilin ayni donemi kaynakta bulunamayan sirketler.
    onceki_yok: list[str] = []
    #: Bitmemis kolonu kirpilan sirketler.
    kirpilan: list[str] = []

    for kod, bilgi in sirketler:
        tablolar = bilanco_ag.ara_donem(kod, ceyrek)
        # BEKLEME CEKIMIN HEMEN ARDINDA, KOSULSUZ.
        #
        # Onceki sekil beklemeyi UC cikis yolunda tekrarliyordu
        # (eksik, ozdeslik, basari). Bir MUTASYON bundan faydalandi:
        # yalnizca BASARI yolundaki bekleme silindiginde oteki ikisi
        # kurali yesil tuttu -- oysa silinen, sirketlerin COGUNUN
        # gectigi yoldu.
        #
        # Aralik zaten ISTEKLER ARASI bir bekleme; cekimden hemen
        # sonra beklemek ayni seyi TEK ve KOSULSUZ bir yerde
        # garanti ediyor. Yola gore tekrarlanan bir tedbir, bir
        # sonraki yol eklendiginde yine unutulur.
        bilanco_ag.ara_ver()
        # OZDESLIK ONCE. Bozuk bilanco sektor medyanini da bozar.
        tekil = {ad: d[0] for ad, d in
                 (tablolar.get("_ham_bilanco") or {}).items()} \
            if tablolar.get("_ham_bilanco") else {}
        alanlar = bilanco_ag.donemi_kur(tablolar)
        tamam, eksik = bilanco_ag.yeterli(alanlar, sektor_tr)
        if not tamam:
            atlanan.append((kod, "eksik: " + ", ".join(eksik[:3])))
            continue
        if tekil:
            bozuk = bilanco_ag.ozdeslik_denetimi(tekil)
            if bozuk:
                atlanan.append((kod, "özdeşlik: " + bozuk[0][:40]))
                continue

        d = oranlar.Donem(etiket=donem_etiketi, **alanlar)
        olculen[kod] = _oranlari(d)
        _m = tablolar.get("_mali") or {}
        mali[kod] = _m.get("yil_sonu_ayi")
        if _m.get("son_bitis"):
            bitis[kod] = _m["son_bitis"]
        # OLCULEN SEY DOKUME GIRIYOR.
        #
        # `ara_donem` iki ayrintiyi daha biliyor: bitmemis kolon
        # kirpildi mi, onceki yilin ayni donemi bulundu mu. Ikisi de
        # sayfanin ICERIGINI degistiriyor (degisim bolumu olmayabilir)
        # ve sessizce gecerse "neden bu sayfada degisim yok" sorusu
        # cevapsiz kalir.
        if tablolar.get("_onceki_yok"):
            onceki_yok.append(kod)
        if tablolar.get("_kirpilan"):
            kirpilan.append(kod)
        print(f"  {kod:<8}ölçüldü")

    # MEDYAN AYNI DONEMI BILDIRENLERDEN KURULUYOR.
    #
    # OLCUT MALI YIL SONU DEGIL, DONEMIN BITIS TARIHI. Once mali yil
    # sonuna gore gruplanmisti; olcum bunun yanlis ayrim oldugunu
    # gosterdi (2026-10-13, kaynaktan okunan gercek tarihler):
    #
    #   TTKOM  yil sonu aralik  -> son donem bitisi 2026-06-30
    #   THYAO  yil sonu aralik  -> son donem bitisi 2026-06-30
    #   ARENA  yil sonu mart    -> son donem bitisi 2026-06-30
    #   BALSU  yil sonu haziran -> son donem bitisi 2026-06-30
    #   GSRAY  yil sonu mayis   -> son donem bitisi 2026-05-31
    #
    # ARENA'nin mali takvimi farkli ama bildirdigi UC AY aynı:
    # nisan-haziran. Onu TTKOM'dan ayirmak gereksiz bir ayrim olurdu.
    # Kulupler ise gercekten baska bir araligi bildiriyor
    # (mart-mayis) ve ayrilmalari gerekiyor.
    #
    # Kiyaslanabilirligi belirleyen sey hangi UC AYIN olculdugu;
    # sirketin mali yilini nerede bitirdigi degil.
    #
    # NEDEN ONEMLI -- OLCULDU, YAYINDAYDI:
    # İletişim sektorunun brut marj medyani -%32,03 idi. Sektordeki
    # alti sirketten ucu futbol kulubu ve onlarin donemi lig
    # oynanmayan aylara denk geliyordu. Yalnizca ayni donemi
    # bildirenlerle medyan +%24,94. Elli yedi puan fark, canli
    # sayfalarda.
    #
    # ANA DONEM = sektorde EN COK sirketin bildirdigi bitis tarihi.
    # Sektorun etiketi ve medyani ondan kuruluyor; digerleri kendi
    # gruplarini aliyor.
    #
    # ISPAT YUKU AYRIM YAPANDA. Bitis tarihi COZULEMEYEN sirket (tarih
    # satiri okunamadi, kaynak reddetti) ana grupta KALIYOR. Aksi
    # halde kaynaktaki gecici bir aksaklik medyani sessizce
    # bosaltirdi -- yanlis kiyas kadar kotu bir sonuc.
    import collections                              # noqa: PLC0415
    sayim = collections.Counter(bitis.get(k) for k in olculen
                                if bitis.get(k))
    # Esitlikte EN YENI donem kazaniyor: sektorun gittigi yon o.
    ana_donem = max(sayim, key=lambda t: (sayim[t], t)) if sayim else ""
    ana = {k: v for k, v in olculen.items()
           if bitis.get(k) in (None, "", ana_donem)}
    medyanlar = sektor_ozet.sektor_medyanlari(ana)
    print(f"  -> {len(olculen)} şirket ölçüldü, {len(atlanan)} atlandı")
    if kirpilan:
        print(f"  -> bitmemiş dönem kırpıldı: {len(kirpilan)} şirket "
              f"({', '.join(sorted(kirpilan)[:6])})")
    if onceki_yok:
        print(f"  -> önceki yılın aynı dönemi YOK: {len(onceki_yok)} "
              f"şirket ({', '.join(sorted(onceki_yok)[:6])}) "
              f"-- değişim bölümü üretilmeyecek")
    if ana_donem:
        print(f"  -> ana dönem {ana_donem}: {len(ana)} şirket")
    if not medyanlar:
        print(f"  -> medyan URETILMEDI (en az {sektor_ozet.EN_AZ_SIRKET} "
              f"şirket gerekiyor)")

    gruplar: dict[str, dict] = {}
    for iso in sorted({t for t in sayim if t != ana_donem}, reverse=True):
        uyeler = {k: v for k, v in olculen.items() if bitis.get(k) == iso}
        g_medyan = sektor_ozet.sektor_medyanlari(uyeler)
        gruplar[iso] = {
            "donem": bilanco_ag.donem_etiketi(iso, ceyrek),
            "sirket_sayisi": len(uyeler),
            "medyan": g_medyan,
            "kodlar": sorted(uyeler),
        }
        print(f"  -> {bilanco_ag.donem_etiketi(iso, ceyrek)}: "
              f"{len(uyeler)} şirket, medyan "
              f"{'var' if g_medyan else 'YOK'}")
    return {
        "sektor": sektor_tr,
        "donem": donem_etiketi,
        "sirket_sayisi": len(ana),
        "medyan": medyanlar,
        "sirket": olculen,
        "atlanan": atlanan,
        "ana_donem": ana_donem,
        "bitis": bitis,
        "onceki_yok": sorted(onceki_yok),
        "kirpilan": sorted(kirpilan),
        #: Mali yil sonu AYRIM OLCUTU DEGIL -- yalnizca aciklama
        #: icin tutuluyor (sayfada "mali yili mayista biten sirket").
        "mali": {k: v for k, v in mali.items() if v and v != 12},
        "donem_gruplari": gruplar,
    }


def _oranlari(d) -> dict[str, float]:
    """`Donem`den karsilastirilacak oranlari cikarir.

    HESAP `oranlar.py`NIN KORUMALI BOLMESIYLE YAPILIYOR
    ---------------------------------------------------
    Doc metni bastan beri "oranlar burada yeniden hesaplanmiyor"
    diyordu ama KOD satir ici bolme yapiyordu. Ikisi ayni sonucu
    vermiyordu ve fark sessizdi.

    `oranlar._bol` boleni SIFIR YA DA NEGATIF ise None donuyor ve
    gerekcesi orada yazili: "negatif ozkaynakla hesaplanan bir
    ozkaynak karliligi matematiksel olarak uretilebilir ama
    anlamsizdir ve yorumlandiginda yaniltir."

    Buradaki satir ici hesap bu kurali TASIMIYORDU. Olculdu
    (2026-10-13):

        net kar -100, ozkaynak -500  ->  _oranlari: roe = +20,0
                                         oranlar  : roe = None

    Yani zarar eden bir sirket POZITIF ozkaynak karliligi ile
    gosteriliyordu -- hem kendi sayfasinda hem SEKTOR MEDYANINDA.
    Negatif ozkaynak spor kuluplerinde ve borclu sirkette olagan,
    yani bu kurgusal bir risk degil.

    Artik tek hesap var. `borc_ozkaynak` yalnizca burada tanimli
    (sektor kiyasi icin) ama ayni korumali bolmeyi kullaniyor.
    """
    cikti: dict[str, float] = {}
    for ad, deger in (
        ("brut_marj", oranlar._marj(d.brut_kar, d.hasilat)
         if d.hasilat else None),
        ("net_marj", oranlar._marj(d.net_kar, d.hasilat)
         if d.hasilat else None),
        ("roe", oranlar._yuz(oranlar._bol(d.net_kar, d.ozkaynak))),
        ("cari_oran", oranlar._bol(d.donen_varliklar,
                                   d.kisa_vadeli_yukumlulukler)),
        ("borc_ozkaynak", oranlar._bol(d.net_borc, d.ozkaynak)),
    ):
        if deger is not None:
            cikti[ad] = deger
    return cikti


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sektor")
    a.add_argument("--hepsi", action="store_true")
    # Donem etiketi artik CEYREKLIK. Bos birakilirsa
    # `bilanco_ag.ceyrek_etiketi` ile veriden turetiliyor.
    a.add_argument("--donem", default="")
    # CEYREKLIK: 2 -> 1.
    #
    # `ceyrek` kac ceyregin TOPLANACAGI. 2 iken alti aylik kumulatif
    # (Q1+Q2) hesaplaniyordu; 1 ile yalnizca en son ceyrek.
    #
    # Ikinci ceyregin kendi performansi kumulatifte GORUNMUYOR: guclu
    # bir Q1, zayif bir Q2'yi ortuyor. Ceyreklik hesap ayrica yillik
    # karsilastirmayi keskinlestiriyor -- Q2'ye karsi gecen yil Q2,
    # alti aya karsi alti ay degil.
    a.add_argument("--ceyrek", type=int,
                   default=bilanco_ag.VARSAYILAN_CEYREK)
    a.add_argument("--sinir", type=int, help="sektör başına en fazla şirket")
    a.add_argument("--kuru-calis", action="store_true", help="dosyaya yazma")
    a.add_argument("--butce-dk", type=float, default=SURE_BUTCESI_DK,
                   help="sektor supurmesi sure butcesi (dakika)")
    a.add_argument("--zorla-yaz", action="store_true",
                   help="kapsam cokse de yaz (bkz. KUCULME_ESIGI)")
    a.add_argument("--zorla", action="store_true",
                   help="bildirim ayı olmasa da çalıştır")
    n = a.parse_args()

    if not n.sektor and not n.hepsi:
        a.error("--sektor ya da --hepsi gerekli")

    # TAKVIM KAPISI. `--zorla` ile atlanabiliyor: elle calistirmak
    # her zaman mumkun olmali, otomatik kosuda ise bosuna cekmemeli.
    if not n.zorla:
        acik, sebep = donem_acik()
        if not acik:
            print(f"bilanço hattı ATLANDI -- {sebep}")
            print("elle çalıştırmak için: --zorla")
            return 0
        print(f"bildirim dönemi: {sebep}")

    if n.hepsi:
        sektorler = sorted({v["sektor_tr"] for v in _defter().values()
                            if v.get("sektor_tr")})
        # EN BAYAT SEKTOR ONCE.
        #
        # Once alfabetik isleniyordu ve kaynak her kosuda yaklasik
        # ayni yerde kapaniyordu (olculdu 2026-09-14: ~100 istek
        # sonrasi 56 ardisik HTTP 429). Alfabetik sira sabit oldugu
        # icin hep AYNI ilk uc sektor cekiliyor, sonrakiler HIC
        # sirasini alamiyordu:
        #
        #   Bilisim, Enerji, Finans | Gayrimenkul, ... (hicbir zaman)
        #
        # Birlestirme veriyi koruyor ama tek basina yakinsamiyor:
        # korunan veri sonsuza kadar bayatlardi. Sira bayatliga gore
        # kurulunca her kosu en geride kalani one aliyor ve art arda
        # kosular butun sektorleri dolasiyor.
        _ozet_simdi = mevcut_ozet()
        sektorler.sort(key=lambda k: (
            (_ozet_simdi.get(k) or {}).get("tazelendi") or "", k))
    else:
        sektorler = [n.sektor]

    # CIKTI BOS BASLAMIYOR -- onceki dosya TEMEL ALINIYOR.
    #
    # Once `cikti = {}` idi ve dosya oldugu gibi eziliyordu. Iki ayri
    # sekilde veri kaybettiriyordu:
    #
    # 1. `--sektor Sanayi` calistirmak DIGER ON SEKTORU siliyordu.
    #    Kapsam korumasi tam bu yolda BILEREK kapaliydi, cunku tek
    #    sektorluk kosuda kuculme beklenen bir seydi. Yani korumanin
    #    kapatildigi tek yol, korumanin en cok gerektigi yoldu.
    #
    # 2. Kaynak kosu ortasinda reddetmeye baslayinca (olculdu
    #    2026-09-14: 56 ardisik HTTP 429) cekilebilen uc sektorun
    #    emegi de cope gidiyordu: koruma HICBIR SEYIN yazilmasina
    #    izin vermiyordu. Kosu ne koruyordu ne ilerletiyordu.
    #
    # Birlestirme ikisini de cozuyor: cekilen tazeleniyor, cekilemeyen
    # onceki haliyle kaliyor, art arda kosular yakinsiyor.
    onceki_ozet = mevcut_ozet()
    cikti = dict(onceki_ozet)
    tazelenen: list[str] = []
    korunan: list[str] = []
    butce_atladi: list[str] = []
    _baslangic = time.monotonic()
    for _i, s in enumerate(sektorler):
        # SURE BUTCESI -- bkz. `SURE_BUTCESI_DK`.
        #
        # Butce dolunca kalan sektorler atlaniyor ve donguden
        # CIKILIYOR; yazma asagida, NORMAL yoldan oluyor. Burada ayri
        # bir yazma yok: ayni karari iki yerde vermek, birinin
        # korumalari atlamasi demekti.
        _gecen = (time.monotonic() - _baslangic) / 60
        if butce_doldu(_gecen, n.butce_dk, _i):
            butce_atladi = list(sektorler[_i:])
            print(f"\n  SURE BUTCESI DOLDU ({_gecen:.0f} dk > "
                  f"{n.butce_dk:.0f} dk) -- {len(butce_atladi)} sektor atlandi: "
                  f"{', '.join(butce_atladi)}")
            print("    Bunlar onceki verileriyle korunuyor; siradaki kosu "
                  "en bayat olandan basliyor.")
            break
        # DONEM ETIKETI VERIDEN TURETILIYOR, ELLE YAZILMIYOR.
        #
        # Once `--donem 2026/6` varsayilaniyla geliyordu ve KASIM'da
        # dokuz aylik tablolar ciktiginda hala "2026/6" yazacakti:
        # rakamlar yeni, etiket eski. Sessiz bir yanlis -- sayfa
        # uretilir, dogru gorunur, yalnizca donemi yanlistir.
        #
        # Artik kaynaktan okunuyor; elle vermek yalnizca `--donem` ile
        # mumkun ve o da bilerek yapilan bir sey.
        etiket = n.donem
        if not etiket:
            import bilanco_ag as _b                   # noqa: PLC0415
            # DONEM BIRDEN FAZLA SIRKETTEN SORULUYOR.
            #
            # Once yalnizca sektorun ILK sirketine bakiliyordu:
            #     son = _b.son_donem(ilk[0][0])
            # O tek istek basarisiz olunca BUTUN SEKTOR atlaniyordu.
            #
            # Olculdu (2026-09-14): kosu YESIL bitti ve kapsam 327
            # sirketten 47'ye dustu -- 11 sektorun 8'i bu satirda
            # elendi. Ardindan sayfa uretimi 11 saniyede bos dondu.
            # Veri adimi 16 dakika yerine 131 saniye surdu; cunku
            # elenen sektor basina yalnizca BIR basarisiz istek
            # yapiliyordu.
            #
            # Tek bir sirketin gecici olarak cekilememesi, o sektordeki
            # otuz sirketin hepsini kaybettirmemeli. Ilk yanit veren
            # kazanir.
            etiket = sektor_donemi(s, _b.son_donem, _b.ceyrek_etiketi)
            if not etiket:
                # SEBEP DOGRU ADIYLA YAZILIYOR.
                #
                # Olculdu (2026-09-14): sekiz sektor "donem
                # belirlenemedi" diye elendi. Bu, VERIDE bir eksiklik
                # varmis gibi okunuyor; gercek sebep ise kaynagin
                # istekleri reddetmesiydi (56 ardisik HTTP 429).
                # Yanlis teshis, dogru teshisten daha pahali.
                if getattr(_b, "KAPANDI", False):
                    print(f"  {s}: KAYNAK REDDEDIYOR, atlandi "
                          f"(veri eksikligi degil)")
                else:
                    print(f"  {s}: donem belirlenemedi "
                          f"({DONEM_DENEME} sirket denendi), atlandi")
                continue
        yeni_sektor = sektor_isle(s, etiket, n.ceyrek, n.sinir)

        # AYNI KURAL, DOGRU AYRINTI DUZEYINDE.
        #
        # Birlestirme kendi tuzagini getiriyor: agir reddedilen bir
        # sektor otuz sirket yerine ikiyle donerse, saglam veriyi ezer.
        # Kuculme kurali bu yuzden SEKTOR duzeyinde de isliyor.
        _eski_n = sirket_sayisi(onceki_ozet.get(s))
        _yeni_n = sirket_sayisi(yeni_sektor)
        if not n.zorla_yaz and kapsam_coktu(_yeni_n, _eski_n):
            print(f"  {s}: kapsam coktu ({_eski_n} -> {_yeni_n}), "
                  f"ONCEKI VERI KORUNDU")
            korunan.append(s)
            continue
        # Tazelenme ani, bir sonraki kosunun sirasini belirliyor.
        yeni_sektor["tazelendi"] = _simdi_iso()
        cikti[s] = yeni_sektor
        tazelenen.append(s)

    if n.kuru_calis:
        print("\n(kuru çalışma -- dosyaya yazılmadı)")
        return 0

    # KATASTROFIK KUCULME KORUMASI.
    #
    # OLCULDU (2026-09-14): kosu YESIL bitti ve `sektor_ozet.json`
    # 327 sirketten 47'ye dustu -- 2100 satir silindi. Ardindan
    # "Bilanco sayfalari" adimi 11 SANIYEDE bitti cunku isleyecek
    # sirket kalmamisti. Hicbir yerde kirmizi gorunmedi.
    #
    # Sebep: yazma KOSULSUZDU. Sektorlerin cogu icin veri
    # cekilemediginde `cikti` az sayida sektor iceriyor ve dosya
    # oldugu gibi eziliyor. Bir sonraki kosu da o eksik dosyayi
    # okuyor -- yani tek bir kotu kosu, hattin tamamini bosa
    # dusuruyor.
    #
    # Buyume ya da kucuk dalgalanma serbest; KATASTROFIK kayip
    # degil. Esik yuzde 60: bir sektorun gecici olarak dusmesi
    # normal, ucte ikisinin birden dusmesi ariza.
    #
    # `--zorla-yaz` ile gecilebiliyor: kapsam GERCEKTEN daraldiysa
    # (sektor listesi kisaldi, `--sektor` ile tek sektor kosuldu)
    # karar insanin.
    # OKUNAMAYAN ISTEKLERIN DOKUMU.
    #
    # Olculdu (2026-09-14): kosu 11 sektorun 8'ini kaybetti ve gunlukte
    # yalnizca "donem belirlenemedi" yaziyordu. Isteklerin NEDEN
    # okunamadigi hicbir yerde gorunmuyordu -- `bilanco_ag.OKUNAMAYAN`
    # kaydi TUTUYORDU ama kimse basmiyordu.
    #
    # "Ne oldu" ile "neden oldu" ayri sorular; bu depoda bugun ucuncu
    # kez ayni bicimde karsilasildi.
    try:
        import bilanco_ag as _ba                      # noqa: PLC0415
        if _ba.OKUNAMAYAN:
            import collections as _c                  # noqa: PLC0415
            _say = _c.Counter(t for _, t in _ba.OKUNAMAYAN)
            print(f"\n  okunamayan istek: {len(_ba.OKUNAMAYAN)}")
            for _t, _n in _say.most_common(6):
                print(f"    {_n:5}  {_t}")
    except Exception:                                  # pragma: no cover
        pass

    # DEFTERDE OLMAYAN SEKTOR GERCEKTEN YOK DEMEKTIR.
    #
    # Birlestirme, kaldirilmis bir sektoru sonsuza kadar tasima
    # riskini getiriyor. Yalnizca TAM SUPURME (`--hepsi`) sektorlerin
    # tam listesini bilir; orada defter yetkilidir.
    if n.hepsi:
        for _s in [k for k in cikti if k not in sektorler]:
            print(f"  {_s}: defterde yok, dosyadan cikarildi")
            del cikti[_s]

    if tazelenen:
        print()
        print(f"  tazelenen sektor ({len(tazelenen)}): "
              f"{', '.join(sorted(tazelenen))}")
    _dokunulmayan = [k for k in cikti if k not in tazelenen]
    if _dokunulmayan:
        print(f"  onceki haliyle kalan ({len(_dokunulmayan)}): "
              f"{', '.join(sorted(_dokunulmayan))}")

    # EKSIK TAZELENEN KOSU, KOSU SAYFASINDA GORUNUR.
    #
    # BUTCEYLE ATLANAN, "HIC CEKILEMEYEN" DEGILDIR. Ikisini ayni
    # satirda saymak, planli bir durusu ariza gibi okuturdu -- ve
    # tersi daha kotu: gercek bir arizayi "zaten butce doldu" diye
    # gecistirirdi.
    _atlanan = [k for k in sektorler
                if k not in tazelenen and k not in korunan
                and k not in butce_atladi]
    if korunan or _atlanan or butce_atladi:
        _u = ["### Bilanço verisi EKSİK tazelendi", "",
              f"tazelenen: **{len(tazelenen)} / {len(sektorler)}** sektör",
              ""]
        if _atlanan:
            _u.append(f"- hiç çekilemeyen: {', '.join(sorted(_atlanan))}")
        if korunan:
            _u.append("- kapsamı çöktüğü için önceki hâliyle korunan: "
                      f"{', '.join(sorted(korunan))}")
        if butce_atladi:
            _u.append(f"- **süre bütçesi** ({n.butce_dk:.0f} dk) dolduğu "
                      "için sıraya bırakılan: "
                      f"{', '.join(sorted(butce_atladi))}")
            _u.append("  (arıza değil: sıra bayatlığa göre kurulduğu için "
                      "sonraki koşu bunlardan başlıyor)")
        try:
            import bilanco_ag as _bx                  # noqa: PLC0415
            if getattr(_bx, "KAPANDI", False):
                _u.append("- **kaynak istekleri reddetti** "
                          "(veri eksikliği değil); sonraki koşu kaldığı "
                          "yerden tamamlar")
        except Exception:                             # pragma: no cover
            pass
        kosu_ozeti(_u)

    _yeni = kapsam(cikti)
    _onceki = kapsam(onceki_ozet)
    # KORUMA ARTIK `--sektor` YOLUNDA DA ACIK.
    #
    # Once `not n.sektor` kosulu vardi: tek sektorluk kosuda kapsamin
    # kuculmesi beklendigi icin koruma kapatiliyordu. Ama ayni kosu
    # dosyanin TAMAMINI eziyordu -- yani koruma, en cok gerektigi
    # yerde kapaliydi. Birlestirmeden sonra tek sektorluk kosu kapsami
    # kucultmuyor; koruma da bedelsiz olarak acik kalabiliyor.
    if not n.zorla_yaz and kapsam_coktu(_yeni, _onceki):
        print(f"\n  KAPSAM COKTU -- dosya YAZILMADI.")
        print(f"    onceki {_onceki} sirket, yeni {_yeni} "
              f"(esik: {_onceki * KUCULME_ESIGI:.0f})")
        print("    Veri cekilemeyen sektorler eksik ciktiyi tam ciktinin")
        print("    uzerine yazacakti; mevcut dosya KORUNDU.")
        print("    Gercekten daraldiysa: --zorla-yaz")
        return 1

    HEDEF.write_text(json.dumps(cikti, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"\n{HEDEF} yazıldı ({_yeni} şirket)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
