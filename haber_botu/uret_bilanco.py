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


def donem_acik(bugun=None) -> tuple[bool, str]:
    """Bugun bilanco cekmenin anlamli oldugu bir ayda miyiz?

    Doner: (acik_mi, aciklama). Kapaliyken de ACIKLAMA doner --
    "neden calismadi" sorusu loga bakinca cevaplanabilsin.
    """
    import datetime as _dt
    bugun = bugun or _dt.date.today()
    ceyrek = BILDIRIM_AYLARI.get(bugun.month)
    if ceyrek is None:
        return False, (f"{bugun.month}. ay bildirim ayi degil "
                       f"(bildirim aylari: {sorted(BILDIRIM_AYLARI)})")
    return True, f"{ceyrek} aylik donem bildirimleri"


DEFTER = _KOK / "kaynak" / "sirketler.json"
HEDEF = _KOK / "kaynak" / "sektor_ozet.json"

#: Sirketler arasi bekleme. Kaynak bizim degil.
ARA_SN = 0.5


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

    for kod, bilgi in sirketler:
        tablolar = bilanco_ag.ara_donem(kod, ceyrek)
        # OZDESLIK ONCE. Bozuk bilanco sektor medyanini da bozar.
        tekil = {ad: d[0] for ad, d in
                 (tablolar.get("_ham_bilanco") or {}).items()} \
            if tablolar.get("_ham_bilanco") else {}
        alanlar = bilanco_ag.donemi_kur(tablolar)
        tamam, eksik = bilanco_ag.yeterli(alanlar, sektor_tr)
        if not tamam:
            atlanan.append((kod, "eksik: " + ", ".join(eksik[:3])))
            time.sleep(ARA_SN)
            continue
        if tekil:
            bozuk = bilanco_ag.ozdeslik_denetimi(tekil)
            if bozuk:
                atlanan.append((kod, "özdeşlik: " + bozuk[0][:40]))
                time.sleep(ARA_SN)
                continue

        d = oranlar.Donem(etiket=donem_etiketi, **alanlar)
        olculen[kod] = _oranlari(d)
        print(f"  {kod:<8}ölçüldü")
        time.sleep(ARA_SN)

    medyanlar = sektor_ozet.sektor_medyanlari(olculen)
    print(f"  -> {len(olculen)} şirket ölçüldü, {len(atlanan)} atlandı")
    if not medyanlar:
        print(f"  -> medyan URETILMEDI (en az {sektor_ozet.EN_AZ_SIRKET} "
              f"şirket gerekiyor)")
    return {
        "sektor": sektor_tr,
        "donem": donem_etiketi,
        "sirket_sayisi": len(olculen),
        "medyan": medyanlar,
        "sirket": olculen,
        "atlanan": atlanan,
    }


def _oranlari(d) -> dict[str, float]:
    """`Donem`den karsilastirilacak oranlari cikarir.

    Oranlar BURADA YENIDEN HESAPLANMIYOR -- `oranlar.py` ne
    hesapliyorsa o kullaniliyor. Ikinci bir hesap, iki farkli dogru
    demek olurdu.
    """
    cikti: dict[str, float] = {}
    if d.hasilat:
        if d.brut_kar is not None:
            cikti["brut_marj"] = d.brut_kar / d.hasilat * 100
        if d.net_kar is not None:
            cikti["net_marj"] = d.net_kar / d.hasilat * 100
    if d.ozkaynak and d.net_kar is not None:
        cikti["roe"] = d.net_kar / d.ozkaynak * 100
    if d.kisa_vadeli_yukumlulukler and d.donen_varliklar is not None:
        cikti["cari_oran"] = d.donen_varliklar / d.kisa_vadeli_yukumlulukler
    if d.ozkaynak and d.net_borc is not None:
        cikti["borc_ozkaynak"] = d.net_borc / d.ozkaynak
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
    a.add_argument("--ceyrek", type=int, default=1)
    a.add_argument("--sinir", type=int, help="sektör başına en fazla şirket")
    a.add_argument("--kuru-calis", action="store_true", help="dosyaya yazma")
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
    for s in sektorler:
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
    _atlanan = [k for k in sektorler
                if k not in tazelenen and k not in korunan]
    if korunan or _atlanan:
        _u = ["### Bilanço verisi EKSİK tazelendi", "",
              f"tazelenen: **{len(tazelenen)} / {len(sektorler)}** sektör",
              ""]
        if _atlanan:
            _u.append(f"- hiç çekilemeyen: {', '.join(sorted(_atlanan))}")
        if korunan:
            _u.append("- kapsamı çöktüğü için önceki hâliyle korunan: "
                      f"{', '.join(sorted(korunan))}")
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
