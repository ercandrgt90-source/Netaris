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
    baglam: dict[str, tuple] = {}
    for sektor, v in ozet.items():
        for kod, oran in v["sirket"].items():
            medyan, n, donem, mali_not = U.kiyas_kumesi(v, kod)
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
        d, once, eksik, seri = _BELLEK[kod]
    else:
        d, once, eksik, seri = bilanco_ag.donem_getir(
            kod, donem, sektor_tr=sektor, ciftli=True, seri=True)
        # BASARISIZLIK DA SAKLANIYOR: kaynak bu sirketi vermediyse
        # ikinci sayfasi icin tekrar sormak, kapali kapiya ikinci
        # kez vurmaktir.
        _BELLEK[kod] = (d, once, eksik, seri)
    if d is None:
        return False, "eksik: " + ", ".join(eksik[:2])

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
    """"Son dort donem" bolumunu TASIMAYAN sayfalar.

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
        if U.SERI_BASLIGI in metin:
            continue
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
        kuyruk.append((yol, ["son dört dönem bölümü yok"]))
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
        print(f"bölüm göçü: {len(kuyruk)} sayfa 'son dört dönem' "
              f"bölümünü taşımıyor")
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
    for yol in yollar:
        if tazelenen >= n.sinir:
            print(f"\nsınıra ulaşıldı ({n.sinir})")
            break
        ok, not_ = sayfa_tazele(yol, baglam, defter, n.kuru_calis)
        if ok:
            tazelenen += 1
            print(f"  {yol.stem:<20}{not_}")
        elif not_:
            atlanan += 1
            print(f"  {yol.stem:<20}ATLANDI -- {not_}")

    print(f"\ntazelenen {tazelenen}, atlanan {atlanan}")
    print("model çağrısı: 0 — saklı yorumlar aynen yeniden kullanıldı")
    if n.onarim and not n.kuru_calis:
        kalan = onarim_kuyrugu(defter, baglam)
        print(f"onarım bekleyen: {len(kalan)} sayfa "
              f"(sonraki koşuda sürer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
