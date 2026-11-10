"""Var olan bilanco sayfalarini SIFIR MODEL MALIYETIYLE yeniden kurar.

    python bilanco_tazele.py --sinir 60
    python bilanco_tazele.py --onarim          # yalnizca BOZUK sayfalar
    python bilanco_tazele.py --kuru-calis      # yazmadan goster

NEDEN AYRI BIR KIP
------------------
Sayfa yapisi degistiginde (yillik degisim tablosu eklendi, ozet basa
alindi) iki secenek vardi:

  1. Her sirketi YENIDEN URETMEK -- 60 model cagrisi, ikinci kez odenir
  2. Yalnizca OLCULEN kismi tazelemek -- sifir model cagrisi

Ikincisi secildi ve sebebi kesin: yorum GIRDIYE bagli, girdi ise
degismedi. Ayni girdiyle ikinci kez odemek, ayni seyi iki kez satin
almak olurdu.

NE YENIDEN HESAPLANIYOR, NE SAKLANIYOR
--------------------------------------
YENIDEN: yillik degisim, olcum tablosu, sektor konumu, yasal uyari.
         Hepsi deterministik -- ayni veriden ayni sonuc.
SAKLANAN: AI yorumu. Sayfanin kendisinden okunup aynen geri konuyor.

Ag istegi var (mali tablo yeniden cekiliyor) ama o UCRETSIZ; maliyet
model cagrisinda.

YORUMSUZ SAYFA URETILMIYOR -- BURADA DA
---------------------------------------
Sakli yorum bulunamazsa sayfaya DOKUNULMUYOR. Yorumsuz bir sayfa
uretmek, "her bilanco AI yorumundan gecer" kuralini tazeleme
kapisindan delmek olurdu.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bilanco_ag              # noqa: E402
import bilanco_denetim as bd   # noqa: E402
import guvenlik                # noqa: E402
import uret_bilanco as UB      # noqa: E402
import uret_bilanco_sayfa as U  # noqa: E402
import yayin                   # noqa: E402

#: Yorumun sayfada bulunabilecegi bolum basliklari.
#:
#: Iki bicim var: eski sayfalarda sonda "## Netaris yorumu",
#: yeni yapida basta "## Özet". Tazeleme ESKI sayfalar icin
#: yazildigi icin ikisi de araniyor.
BASLIKLAR = ("Özet", "Netaris yorumu")

_ON_DESEN = re.compile(r"(---\n)(.*?)(\n---\n)(.*)", re.S)
_KOD_DESEN = re.compile(r"^kod:\s*(\S+)", re.M)
#: Sayfanin ILK yayim tarihi. Tazeleme onu KORUMALI.
_TARIH_DESEN = re.compile(r"^tarih:\s*(\S+)", re.M)
#: Sayfanin KENDI donemi. Ozetin donemiyle ayni olmak ZORUNDA.
_DONEM_DESEN = re.compile(r"^donem:\s*(.+?)\s*$", re.M)


def yorumu_al(govde: str) -> str:
    """Sayfada SAKLI duran AI yorumunu cikarir.

    Bulamazsa bos doner ve cagiran taraf sayfaya dokunmaz -- yanlis
    bir yorum uretmektense hic dokunmamak dogru.
    """
    for baslik in BASLIKLAR:
        desen = re.compile(
            r"^##\s*" + re.escape(baslik) + r"\s*$\n+(.+?)(?=\n\n|\n##|\Z)",
            re.M | re.S)
        m = desen.search(govde)
        if m:
            return " ".join(m.group(1).split())
    return ""


def baglam_kur() -> tuple[dict, dict]:
    """kod -> (sektor, oran, medyan, n, donem, mali_not) + unvan defteri.

    Oranlar ve medyanlar YENIDEN HESAPLANMIYOR: `sektor_ozet.json`
    ne diyorsa o. Ikinci bir hesap, iki farkli dogru demek olurdu.

    KIYAS KUMESI SAYFA URETICISININ ISLEVINDEN OKUNUYOR
    ---------------------------------------------------
    Hangi medyanla kiyaslanacagi `U.kiyas_kumesi` ile belirleniyor --
    yani tazeleme ile ilk uretim AYNI kurali kullaniyor. Burada ayni
    karari ikinci kez yazmak, mali takvim ayrimi degistiginde birinin
    guncellenip otekinin unutulmasi demekti. Bu depoda ayni sinif
    kusur (iki yerde ayni seye karar veren kod) ceyrek sayisinda
    zaten bir kez yayina cikti.
    """
    ozet = json.loads(U.OZET.read_text(encoding="utf-8"))
    defter = json.loads(U.DEFTER.read_text(encoding="utf-8"))["sirketler"]
    # DONEM BITISLERI URETIMLE AYNI HARITADAN.
    #
    # `kiyas_kumesi` etiketi ozet ile nobet defterinden YENI olana
    # gore veriyor. Burada haritayi vermemek, tazelemenin ozete gore
    # Q2 derken uretimin defterden Q3 demesi olurdu -- ve
    # `sayfa_tazele` sayfa donemini bu etiketle karsilastirdigi icin
    # uretimin yeni yazdigi her sayfayi "donem uyusmuyor" diye
    # REDDEDERDI. Ayni karari iki yerde ayri vermek, bu depoda en sik
    # tekrarlayan kusur sinifi.
    _bitisler = U.bitis_haritasi(ozet)
    baglam: dict[str, tuple] = {}
    for sektor, v in ozet.items():
        for kod, oran in v["sirket"].items():
            medyan, n, donem, mali_not = U.kiyas_kumesi(v, kod, _bitisler)
            # KIYASSIZ SAYFA DA TAZELENIYOR. Medyan yoksa `govde_kur`
            # bolumu yazmiyor ve sebebini soyluyor; sayfayi hic
            # tazelememek o aciklamayi eski sayfalara ulastirmazdi.
            baglam[kod.upper()] = (sektor, oran, medyan, n, donem,
                                   mali_not)
    return baglam, defter


#: kod -> (donem, once, eksik). KOSU SURESINCE gecerli.
#:
#: AYNI SIRKETIN IKI SAYFASI AYNI VERIYI ISTIYOR.
#:
#: Onarim kuyrugunda bir sirketin hem 1. hem 2. ceyrek sayfasi
#: bulunabiliyor ve `donem_getir` her ikisi icin ayri ayri UC tablo
#: cekiyordu -- oysa donen veri birebir ayni (kaynak her zaman EN
#: YENI donemi veriyor, etiket yalnizca gosterim icin).
#:
#: Olculdu (2026-10-13): 187 sayfalik kuyrukta 169 benzersiz sirket,
#: yani 18 sayfa ikinci kez geciyordu -- 54 gereksiz istek.
#:
#: Bu onemli cunku DARBOGAZ KAYNAGIN IZNI. Kaynak kosu basina
#: yaklasik 17 sayfalik veri veriyor, sonra reddetmeye basliyor
#: (olculdu: bir CI kosusunda 25 denemenin 17'si gecti, ardindan
#: sekiz ardisik red -> `bilanco_ag.KAPANDI`). Tasarruf edilen her
#: istek, o pencerede onarilan sayfa sayisini artiriyor.
_BELLEK: dict[str, tuple] = {}


def bellegi_bosalt() -> None:
    """Kosu belleğini siler. Sinamalar icin."""
    _BELLEK.clear()


def sayfa_tazele(yol: pathlib.Path, baglam: dict, defter: dict,
                 kuru: bool) -> tuple[bool, str]:
    """Tek sayfa. Doner: (tazelendi_mi, aciklama)."""
    m = _ON_DESEN.match(yol.read_text(encoding="utf-8"))
    if not m or "kategori: Bilanço Analizi" not in m.group(2):
        return False, ""                     # bilanco sayfasi degil
    k = _KOD_DESEN.search(m.group(2))
    if not k:
        return False, "kod alanı yok"
    kod = k.group(1).upper()
    if kod not in baglam:
        return False, "sektör özetinde yok"

    yorum = yorumu_al(m.group(4))
    if not yorum:
        return False, "saklı yorum bulunamadı"

    sektor, oran, medyan, n, donem, mali_not = baglam[kod]

    # SAYFANIN DONEMI OZETIN DONEMIYLE AYNI OLMALI.
    #
    # OLCULDU, YAYINDAYDI (2026-10-13). `donem` OZETTEN geliyor ama
    # tazelenen dosya baska bir doneme ait olabiliyor. O zaman
    # `yaz_sektorel` kanonik yolu `kod + OZETIN donemi` ile kuruyor
    # ve BASKA BIR DOSYAYA yaziyor:
    #
    #   okunan : 2026-1-ceyrek-asuzu.md   (Q1)
    #   yazilan: 2026-2-ceyrek-asuzu.md   (Q2)  <- YENI DOSYA
    #
    # Sonuc uc katli:
    #   1. Okunan sayfa DEGISMIYOR -- onarim kuyrugundan hic
    #      dusmuyor, her kosuda ayni isi yapan bir saat bombasi.
    #   2. Istenmeyen YENI sayfa doguyor (bir kosuda sekiz tane).
    #   3. En kotusu: sakli AI yorumu Q1'i anlatiyor ama sayfa
    #      "2026 2. çeyrek" diyor. `2026-2-ceyrek-asuzu.md`
    #      "brüt kâr marjının %8,8'e gerilemesi" cumlesini Q1
    #      sayfasindan AYNEN tasidi. Sayfa bir donemi soyluyor,
    #      yorumu baskasini anlatiyor.
    #
    # Ozet baska bir donemdeyse DOKUNULMUYOR: o donemin medyani
    # elimizde yok ve olmayan bir kiyasla sayfa kurmak, duzeltmek
    # degil yeni bir hata uretmek olurdu.
    _d = _DONEM_DESEN.search(m.group(2))
    sayfa_donemi = _d.group(1) if _d else ""
    if sayfa_donemi and sayfa_donemi != donem:
        return False, f"dönem uyuşmuyor (sayfa {sayfa_donemi}, özet {donem})"
    # SERI BURADA DA ISTENIYOR -- YOKSA TAZELEME BOLUMU SILER.
    #
    # Tazeleme govdeyi SIFIRDAN kuruyor. `seri` istenmezse
    # `govde_kur` "Son dört dönem" bolumunu hic yazmaz ve tazelenen
    # her sayfa bolumu KAYBEDER. CI her kosuda `--onarim` calistirdigi
    # icin bu, yeni uretilen sayfalari da zamanla silerdi.
    #
    # Bedeli yok: seri zaten AYNI cekimden geliyor (olculdu, sirket
    # basina 3 istek -- seri oncesiyle ayni).
    if kod in _BELLEK:
        d, once, eksik, seri, okunamayan = _BELLEK[kod]
    else:
        # BU CEKIMDE KAYNAK NE DEDI -- AYRICA SAKLANIYOR.
        #
        # `bilanco_ag.OKUNAMAYAN` kosu boyunca birikiyor; bu sirkete
        # ait olanlari ayirmanin yolu cekimden ONCE ve SONRA boyuna
        # bakmak. Sayfa basina tek karar, tek yer.
        _n = len(bilanco_ag.OKUNAMAYAN)
        d, once, eksik, seri = bilanco_ag.donem_getir(
            kod, donem, sektor_tr=sektor, ciftli=True, seri=True)
        okunamayan = list(bilanco_ag.OKUNAMAYAN[_n:])
        # BASARISIZLIK DA SAKLANIYOR: kaynak bu sirketi vermediyse
        # ikinci sayfasi icin tekrar sormak, kapali kapiya ikinci
        # kez vurmaktir.
        _BELLEK[kod] = (d, once, eksik, seri, okunamayan)
    if d is None:
        # SEBEP DOGRU ADIYLA. "eksik: hasilat, net_kar" VERIDE bir
        # eksiklik varmis gibi okunuyor; oysa alanlar bos cunku
        # kaynak istegi REDDETTI.
        #
        # OLCULDU (2026-11-10, kosu #78): goc kuyrugundaki 28
        # sayfanin 28'i "ATLANDI -- eksik: hasilat, net_kar" dondu.
        # Ustteki uc satir gercek sebebi soyluyordu ("istek araligi
        # 2.0 -> 4.0 -> 8.0 sn", "KAYNAK KAPANDI") ama sayfa basina
        # yazilan satir bunu tasimiyordu. Gunluge bakan biri 28
        # sirketin verisinin bozuk oldugu sonucuna varirdi.
        #
        # AYNI KUSUR BIR KEZ DUZELTILMISTI: `uret_bilanco.main`
        # icinde "donem belirlenemedi" yerine "KAYNAK REDDEDIYOR
        # (veri eksikligi degil)" yaziliyor ve gerekcesi orada
        # "Yanlis teshis, dogru teshisten daha pahali" diye duruyor.
        # Buraya tasinmamisti. Bu dosyanin KENDI yorumu (asagida,
        # `ara_ver` yaninda) yanlis etiketi 2026-10-31'de ALINTILIYOR
        # ama duzeltmemis -- semptomu kaydedip sebebi birakmak.
        #
        # OLCUT CEKIMIN KENDISI: `bilanco_ag.KAPANDI`ya bakmak
        # yetmezdi, cunku kapiyi KAPATAN ilk sekiz istek daha kapi
        # acikken basarisiz oluyor ve onlar da yanlis etiketlenirdi.
        if okunamayan:
            _sebep = sorted({s for _k, s in okunamayan})
            return False, ("KAYNAK VERMEDI (veri eksikliği DEĞİL): "
                           + ", ".join(_sebep[:2]))
        return False, "eksik: " + ", ".join(eksik[:2])

    # ETIKETI VERISIYLE CELISEN SAYFA TAZELENMIYOR.
    #
    # BU SATIRIN YOKLUGU BES SAYFAYI YAYINA CIKARDI (olculdu
    # 2026-11-01; gerekce ve olcum `U.donem_celiskisi` uzerinde).
    #
    # Yukaridaki SAYFA-OZET karsilastirmasi bunu yakalamiyor ve
    # yakalayamaz: AKBNK'de sayfa Q2, ozet Q2, yani o kapi aciliyor.
    # Celisen ucuncu taraf CEKILEN VERI -- kaynak her zaman en yeni
    # donemi veriyor. Sonuc: Q3 tablosu Q2 basligi altinda, ustune
    # Q2 yorumu aynen geri konarak.
    #
    # ORADAKI KARAR BURADA DA GECERLI: dokunulmuyor. Sayfa eski
    # haliyle kaliyor, yani kendi doneminin verisini gostermeye
    # devam ediyor; ozet ilerledigi an sirket "bayat" sayilip
    # dogru etiketle, YENI yorumla uretiliyor.
    celiski = U.donem_celiskisi(donem, seri)
    if celiski:
        return False, f"dönem çelişkisi: {celiski}"

    # ORAN SAYFANIN KENDI VERISINDEN -- gerekcesi
    # `uret_bilanco_sayfa.sirket_isle` uzerinde yazili.
    #
    # ONARIM ICIN AYRICA SART: tazeleme oranlari ozetten okursa,
    # ozetteki bozuk bir oran sayfaya YENIDEN yazilir ve sayfa
    # onarim kuyrugundan HIC dusmez -- her kosuda ayni isi yapan
    # bir saat bombasi olurdu. Olculdu: negatif ozkaynakla
    # hesaplanmis alti ROE tam bu durumdaydi.
    kendi = UB._oranlari(d)
    if kendi:
        oran = kendi

    unvan = (defter.get(kod) or {}).get("unvan", kod)
    govde = U.govde_kur(kod, unvan, sektor, donem, d, oran, medyan,
                        n, yorum, mali_not=mali_not,
                        alt_sektor=(defter.get(kod) or {}).get(
                            "alt_sektor") or "",
                        once=once, seri=seri)

    tamam, bulgular = guvenlik.yayinlanabilir(govde)
    if not tamam:
        return False, "güvenlik: " + (bulgular[0].aciklama[:40]
                                      if bulgular else "?")
    if not kuru:
        # SAYFANIN KENDI TARIHI KORUNUYOR.
        #
        # Tazeleme yeniden YAYIMLAMA degil; icerigin olculdugu gun
        # degismiyor. Bu satir olmadan onarim kosusu butun eski
        # analizleri "bugun" damgaliyordu -- olculdu, EGEGY'nin
        # 2026-08-27 tarihli analizi 2026-10-13 oldu.
        _t = _TARIH_DESEN.search(m.group(2))
        yayin.yaz_sektorel(
            govde=govde, sirket=unvan, kod=kod, donem=donem, sektor=sektor,
            tarih_ustu=_t.group(1) if _t else "",
            kaynak="Çeyreklik mali tablolardan türetildi; sektör medyanı "
                   "Netaris hesabı")
    return True, "+yıllık değişim" if once is not None else "yenilendi"


def onarim_kuyrugu(defter: dict, baglam: dict | None = None) -> list:
    """Sayfalari ONARIM IHTIYACINA gore siralar: bozuk olanlar basa.

    NEDEN SIRA ONEMLI -- BU DEPODA YASANDI
    --------------------------------------
    Alfabetik sira + `--sinir`, kuyrugun sonuna HIC ulasmiyor: her
    kosu ayni ilk N sayfayi yeniden kuruyor. Ayni tuzaga sektor
    sirasinda da dusulmustu (olculdu 2026-09-14: 11 sektorun hep
    ayni ilk ucu cekiliyordu).

    Onarim ihtiyaci YERELDE olculuyor -- ag istegi yok. Kuyruk
    onarilan sayfa sayisinca KISALIYOR; bitince adim kendiliginden
    etkisiz hale geliyor.
    """
    miras = bd.miras_sayfalar()
    kuyruk = []
    for yol in sorted(U.SITE.glob("*.md")):
        metin = yol.read_text(encoding="utf-8")
        k = _KOD_DESEN.search(metin)
        bilgi = defter.get(k.group(1).upper()) if k else None
        sebep = bd.onarim_gereken(metin, bilgi)
        if not sebep:
            continue
        # BASLIGI KENDI TABLOSUYLA CELISEN SAYFA ONARILAMAZ.
        #
        # `sayfa_tazele` ayni celiskiyi gorup DOKUNMUYOR (gerekcesi
        # orada yazili), yani bu sayfa kuyrukta kalsa her kosuda
        # denenip her kosuda atlanirdi -- adim asla tukenmez ve
        # "onarim bekleyen" sayisi hic sifirlanmaz. Ayni gerekceyle
        # donemi ozetten farkli sayfalar da asagida dusuyor.
        #
        # Koruma (`site/test_bilanco_sayfa_saglam.py`) onlari
        # SAYMAYA devam ediyor: cozum tazeleme degil, dogru etiketli
        # ikizi varsa sayfanin silinmesi.
        if bd.donem_etiketi_celiskisi(metin):
            continue
        # ONARILAMAYAN SAYFA KUYRUKTA DURMAZ.
        #
        # Ozet baska bir donemdeyse o sayfa yeniden kurulamiyor:
        # kendi doneminin sektor medyani elimizde yok (gerekcesi
        # `sayfa_tazele` icinde yazili). Kuyrukta tutmak, her kosuda
        # denenip her kosuda atlanan bir kalem demek -- adim asla
        # tukenmez ve "onarim bekleyen" sayisi hic sifirlanmaz.
        #
        # Bu sayfalar miras listesinde KALIYOR, yani koruma onlari
        # tolere etmeye devam ediyor ve durum gorunur kaliyor.
        if baglam is not None:
            kayit = baglam.get(k.group(1).upper()) if k else None
            # Sektor ozetinde HIC OLMAYAN sirket de onarilamiyor:
            # oranlari ve medyani yok. Ayni gerekce.
            if not kayit:
                continue
            _d = _DONEM_DESEN.search(metin)
            if _d and _d.group(1) != kayit[4]:
                continue
        kuyruk.append((yol, sebep))
    # MIRAS LISTESINDE OLMAYAN BOZUK SAYFA ONCE.
    #
    # O sayfa korumanin tolere ETMEDIGI sayfadir, yani CI'i kirmizi
    # tutan sayfadir. Miras sayfalari zaten tolere ediliyor; onlari
    # onden gecirmek, kirmizi kosuyu bir dilim daha beklettirir.
    #
    # Ikincil anahtar dosya adi: ayni oncelikte duzen degismiyor.
    kuyruk.sort(key=lambda p: (p[0].name in miras, p[0].name))
    return kuyruk


def goc_kuyrugu(defter: dict, baglam: dict | None = None) -> list:
    """GUNCEL BICIMDE OLMAYAN sayfalar -- iki sebep, tek kuyruk.

    Sebepler: "son dort donem" bolumunun yoklugu ve girdileri
    sayfada duran bir TURETILMIS kalemin satirinin yoklugu. Olcum
    ve gerekce `sayfa` dongusunun icinde yazili.

    NEDEN ONARIM KUYRUGUNDAN AYRI
    -----------------------------
    `bilanco_denetim.onarim_gereken` iki isi birden yapiyor: onarim
    kuyrugunu besliyor VE `site/test_bilanco_sayfa_saglam.py`
    korumasini besliyor. Yeni bolumu oraya bir "eksiklik" olarak
    eklemek, var olan 275 sayfayi BIR ANDA bozuk ilan eder ve CI
    kirmiziya doner -- yani site dagitilmaz.

    Bolumun yoklugu bir KUSUR degil, bir GOC. Ayni ayrim kumulatif
    -> ceyreklik gocunde de yapilmisti (`kumulatif_temizle`).

    Kuyruk tazelendikce KISALIYOR; bitince adim kendiliginden
    etkisiz hale geliyor ve hicbir sey yapmadan doner.

    ONARILAMAYANLAR AYNI OLCUTLE ELENIYOR: sakli yorumu olmayan ya
    da donemi ozetin doneminden farkli olan sayfa yeniden
    kurulamiyor. Kuyrukta tutmak, her kosuda denenip her kosuda
    atlanan bir kalem demek -- kuyruk asla tukenmez.
    """
    kuyruk = []
    for yol in sorted(U.SITE.glob("*.md")):
        metin = yol.read_text(encoding="utf-8")
        if not bd.bilanco_sayfasi(metin):
            continue
        # IKI GOC SEBEBI, TEK KUYRUK.
        #
        # Baslangicta olcut yalnizca "son dort donem bolumu yok"tu.
        # OLCULDU (2026-11-01): o olcut 326 sayfanin 169'unu goruyor;
        # bolumu OLAN 157 sayfa hicbir kuyruga girmiyor ve bunlarin
        # 141'i, girdileri sayfada DURAN bir turetilmis kalemi
        # (serbest nakit akisi) gostermiyor.
        #
        # Yani bolum gocu tamamlandiginda adim kendini kapatacak ve
        # 141 sayfa eksik satirla kalacakti. Kuyruk bu yuzden
        # "GUNCEL BICIMDE OLMAYAN sayfa" olcutune genisliyor.
        #
        # OLCUT URETICIDEN: hangi kalemin turetilmis oldugu
        # `U.turetilmis_kalemler` ile `oranlar.Donem`in kendi
        # yapisindan okunuyor. Besinci bir turetme eklendigi gun bu
        # kuyruk onu kendiliginden kapsiyor.
        _eksik = []
        if U.SERI_BASLIGI not in metin:
            _eksik.append("son dört dönem bölümü yok")
        _eksik += [f"{a} satırı yok" for a in U.eksik_turetilmis(metin)]
        k = _KOD_DESEN.search(metin)
        if not k:
            continue
        if baglam is not None:
            kayit = baglam.get(k.group(1).upper())
            if not kayit:
                continue
            _d = _DONEM_DESEN.search(metin)
            if _d and _d.group(1) != kayit[4]:
                continue
            # KIYASSIZ YAZILMIS SAYFA, MEDYAN GELDIGINDE TAMAMLANIR.
            #
            # `kiyas_kumesi` donem etiketini nobet defterinden de
            # alabiliyor; o donemin kiyas grubu henuz yoksa sayfa
            # BILEREK kiyas bolumu olmadan yaziliyor (gerekcesi
            # `uret_bilanco_sayfa` icinde). Ama sektor tazelenip
            # medyan OLUSTUGUNDA o sayfaya bir daha dokunan hicbir
            # sey yoktu: `yayimlanmis` kontrolu onu "guncel"
            # sayiyor, onarim kuyrugu kiyas yoklugunu kusur
            # saymiyor (hakli olarak -- kiyassiz sayfa mesru).
            #
            # Yani sayfa kalici olarak kiyassiz kalirdi. Bu, bugun
            # iki kez duzeltilen kusurun aynisi: mekanizma eklendi,
            # onu besleyen kural yazilmadi.
            #
            # OLCUT MEDYANIN VARLIGI: yoksa eklenecek bir sey yok ve
            # sayfa kuyruga GIRMIYOR -- yoksa her kosuda denenip her
            # kosuda ayni sonucu veren bir kalem olurdu.
            if U.KIYAS_BASLIGI not in metin and kayit[2]:
                _eksik.append("sektör karşılaştırması eklenebilir")
        if not _eksik:
            continue
        # SEBEP OLCULEN SEBEP -- sabit metin DEGIL.
        #
        # Onceki hali her kalem icin "son dort donem bolumu yok"
        # yaziyordu. Olcut genisledikten sonra bu YANLIS bir teshis
        # olurdu: bolumu olan ama satiri eksik sayfa icin gunluk
        # var olan bir bolumu yok gosterirdi. Yanlis teshis, dogru
        # teshisten daha pahali.
        kuyruk.append((yol, _eksik))
    return kuyruk


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=60)
    a.add_argument("--kuru-calis", action="store_true")
    a.add_argument("--onarim", action="store_true",
                   help="yalnizca BOZUK sayfalari yeniden kurar")
    a.add_argument("--bolum-gocu", action="store_true",
                   help="yalnizca 'son dort donem' bolumu OLMAYAN "
                        "sayfalari yeniden kurar (sifir model cagrisi)")
    a.add_argument("--kod", nargs="+", metavar="KOD",
                   help="yalnizca bu sirketlerin sayfasi (kuyrugu "
                        "beklemeden)")
    n = a.parse_args()

    if not U.OZET.exists():
        print(f"{U.OZET} yok -- önce uret_bilanco.py çalışmalı.")
        return 1
    # BELLEK KOSUYA AIT. Uzun yasayan bir surecte ikinci cagri bayat
    # veri gormemeli; acikca bosaltiliyor.
    bellegi_bosalt()
    baglam, defter = baglam_kur()

    if n.kod:
        # BELIRLI SAYFA -- KUYRUGU BEKLEMEDEN.
        #
        # Bazi kusurlar sayfadan OKUNARAK tespit edilemiyor. Ornek
        # (2026-10-15): yuzde degisim negatif tabandan hesaplanmisti
        # (FENER ozkaynagi -0,04 -> 8,79, sayfada %21391,8). Sayfa
        # onceki degeri yazmadigi icin negatif taban ile cok kucuk
        # pozitif taban ayirt edilemiyor; esik uydurmak da
        # dagilimlar cakisirken yalnizca hangi hatayi yapacagini
        # secmek olurdu.
        #
        # Boyle durumlarda hedefi ELLE vermek dogrusu. Kural AYNEN
        # duruyor: sakli yorum yoksa dokunulmuyor, donem uyusmuyorsa
        # dokunulmuyor.
        istenen = {k.upper() for k in n.kod}
        yollar = []
        for yol in sorted(U.SITE.glob("*.md")):
            k = _KOD_DESEN.search(yol.read_text(encoding="utf-8"))
            if k and k.group(1).upper() in istenen:
                yollar.append(yol)
        print(f"hedefli tazeleme: {len(yollar)} sayfa "
              f"({', '.join(sorted(istenen))})")
    elif n.bolum_gocu:
        kuyruk = goc_kuyrugu(defter, baglam)
        # DOKUM SEBEBE GORE: iki ayri goc sebebi var ve hangisinin
        # kac sayfa oldugunu gunluge bakan biri gorebilmeli.
        _say: dict[str, int] = {}
        for _y, _s in kuyruk:
            for _n in _s:
                _say[_n] = _say.get(_n, 0) + 1
        print(f"göç kuyruğu: {len(kuyruk)} sayfa güncel biçimde değil")
        for _n, _c in sorted(_say.items(), key=lambda x: -x[1]):
            print(f"  {_c:>4}  {_n}")
        if not kuyruk:
            print("göç TAMAMLANDI -- hiçbir şey yapılmadı")
            return 0
        for yol, sebep in kuyruk[:8]:
            print(f"  {yol.stem:<24}{', '.join(sebep)}")
        yollar = [y for y, _s in kuyruk]
    elif n.onarim:
        kuyruk = onarim_kuyrugu(defter, baglam)
        print(f"onarım kipi: {len(kuyruk)} sayfa onarım bekliyor")
        # ONARILAMAYANLAR AYRICA SOYLENIYOR.
        #
        # Kuyruk sifirlandiginda miras listesinde sayfa KALIYOR ve
        # "koruma neden hala bunlari sayiyor" sorusu soruluyor.
        # Cevap burada, sorunun soruldugu yerde duruyor: o sayfalar
        # kendi doneminin sektor medyani olmadigi icin yeniden
        # kurulamiyor ve bilerek tolere ediliyor.
        _olmaz = len(onarim_kuyrugu(defter)) - len(kuyruk)
        if _olmaz:
            print(f"  ({_olmaz} sayfa ONARILAMAZ -- dönemi özetin "
                  f"döneminden farklı, o dönemin sektör medyanı yok; "
                  f"miras listesinde kalıyorlar)")
        if not kuyruk:
            print("onarılacak sayfa YOK -- hiçbir şey yapılmadı")
            return 0
        for yol, sebep in kuyruk[:8]:
            print(f"  {yol.stem:<24}{', '.join(sebep)}")
        if len(kuyruk) > 8:
            print(f"  ... ve {len(kuyruk) - 8} sayfa daha")
        yollar = [y for y, _ in kuyruk]
    else:
        yollar = sorted(U.SITE.glob("*.md"))

    tazelenen = atlanan = 0
    #: Atlama sebeplerinin dokumu. SON SATIR NE DIYORSA O OKUNUYOR:
    #: sayfa basina satirlar yuzlerce satirlik gunlugun icinde
    #: kayboluyor ve "tazelenen 0, atlanan 28" tek basina SEBEP
    #: soylemiyor -- kaynak mi vermedi, veri mi eksik, donem mi
    #: uyusmuyor? Ucu tamamen farkli isler gerektiriyor.
    _dokum: dict[str, int] = {}
    for yol in yollar:
        if tazelenen >= n.sinir:
            print(f"\nsınıra ulaşıldı ({n.sinir})")
            break
        ok, not_ = sayfa_tazele(yol, baglam, defter, n.kuru_calis)
        # KAYNAGA NAZIK DAVRANMA -- bkz. `bilanco_ag.ara_ver`.
        #
        # OLCULDU (2026-10-31, kosu #61): bolum gocu 128 sayfanin
        # HICBIRINI tasiyamadi. Gunluk once "istek araligi 2.0 ->
        # 4.0 -> 8.0 sn", sonra "KAYNAK KAPANDI -- 8 ardisik red"
        # yazdi; kalan her sayfa "ATLANDI -- eksik: hasilat,
        # net_kar" dondu. Bu dongu de istekler arasinda hic
        # beklemiyordu.
        bilanco_ag.ara_ver()
        if ok:
            tazelenen += 1
            print(f"  {yol.stem:<20}{not_}")
        elif not_:
            atlanan += 1
            print(f"  {yol.stem:<20}ATLANDI -- {not_}")
            # Ayrinti degil TUR sayiliyor: "eksik: hasilat, net_kar"
            # ile "eksik: ozkaynak" ayni ise isaret ediyor.
            _dokum[not_.split(":")[0].strip()] = (
                _dokum.get(not_.split(":")[0].strip(), 0) + 1)

    print(f"\ntazelenen {tazelenen}, atlanan {atlanan}")
    if _dokum:
        print("atlama sebebi dökümü:")
        for _s, _c in sorted(_dokum.items(), key=lambda x: -x[1]):
            print(f"  {_c:>4}  {_s}")
    print("model çağrısı: 0 — saklı yorumlar aynen yeniden kullanıldı")
    if n.onarim and not n.kuru_calis:
        kalan = onarim_kuyrugu(defter, baglam)
        print(f"onarım bekleyen: {len(kalan)} sayfa "
              f"(sonraki koşuda sürer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
