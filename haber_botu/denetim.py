"""Veri denetimi -- yayimlanan her sayi kontrolden geciyor.

NEDEN VAR
---------
Kullanici sayfada "Politika faizi %40,00" gordu; gercek politika faizi
%37 idi. Deger dogruydu ama ETIKET yanlisti: sayi TP.APIFON4'ten, yani
TCMB agirlikli ortalama FONLAMA MALIYETINDEN geliyordu. Ayni depoda
serinin dogru adi ("TCMB agirlikli fonlama") yaziliydi ve
`takvim.TANIM` "politika faizinden sapabilir" diye aciklamisti --
yanlis olan yalnizca panelin elle yazilmis etiketiydi.

Bu, tek basina bir hata degil bir HATA SINIFI. Ayni turden olculmus
digerleri:

  * CPIAUCSL depoya "332,568" ve birim "%" olarak yazildi. O sayi TUFE
    ENDEKSININ SEVIYESI; sayfada "%332,57" gorunurdu.
  * "ABD ÜFE" etiketiyle PPIACO (tum emtialar) basiliyordu: %10,11.
    Manset UFE (PPIFIS) %5,51.
  * EVDS formulu DUZEY'e sabitlendiginde "TÜFE: %132,31" yazildi.
  * Ortalama saatlik kazanc SEVIYE ($37,64) olarak esik yapildi; oysa
    aciklamada manset olan aylik degisim.

Hepsinin ortak yani: SAYI DOGRU, ANLAMI YANLIS. Bir birim testi bunu
yakalamiyor cunku kod dogru calisiyor. Yakalayacak sey, yayimlanan
sayiyi TANIMIYLA karsilastiran bir denetim.

NE YAPIYOR
----------
1. ETIKET  -- ekranda kullanilan her ad, serinin kayitli adiyla
              uyusmali. Uyusmuyorsa `ETIKET_ISTISNA`da GEREKCESIYLE
              yazili olmali. Yeni bir sapma eklemek, gerekce yazmayi
              zorunlu kiliyor.
2. ARALIK  -- her seri turu icin makul sinir. TUFE %500 olamaz, faiz
              negatif olamaz, endeks yuzde olarak sunulamaz.
3. BIRIM   -- `sunum` alaniyla `birim` tutarli mi. "yillik" sunulan bir
              seri "%" birimli olmak zorunda.
4. TAZELIK -- gozlem, serinin yayin ritmine gore makul yaslikta mi.

Kullanim:
    python haber_botu/denetim.py          # rapor, cikis 0/1
    python haber_botu/denetim.py --sessiz # yalnizca hatalar
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys
from dataclasses import dataclass

# CIKTI UTF-8'E ZORLANIYOR -- denetim Windows'ta COKUYORDU.
#
# Rapordaki durum simgeleri emoji ve Windows konsolunun varsayilan
# kod sayfasi (cp1254) onlari basamiyor:
#
#     UnicodeEncodeError: 'charmap' codec can't encode '🟡'
#
# Coku raporun EN SONUNDA, "GENEL DURUM" satirinda oluyordu: butun
# bulgular basiliyor, sonra betik dusuyordu. Yani denetim calisiyor
# ama SONUCUNU soylemeden oluyordu -- ve cikis kodu da yayin
# kararini tasidigi icin karar hic verilmemis oluyordu.
#
# CI (Linux, UTF-8) etkilenmiyordu; sorun yalnizca yerelde goruluyor
# ve tam da bu yuzden fark edilmemisti.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import beyin    # noqa: E402
import takvim   # noqa: E402
import dosya    # noqa: E402
import evds     # noqa: E402
import politika_faizi  # noqa: E402


@dataclass(frozen=True)
class Bulgu:
    agirlik: str      # "hata" | "uyari"
    alan: str
    kod: str
    mesaj: str


# --------------------------------------------------------------------
# 1. ETIKET DENETIMI
# --------------------------------------------------------------------
#
# Ekranda kullanilan ad, serinin KAYITLI adindan farkliysa bu bir
# karardir ve gerekcesi yazilmalidir. "Politika faizi" etiketi tam da
# boyle sessizce eklenmisti.
#
# Anahtar: (seri kodu, ekranda kullanilan ad) -> gerekce.
ETIKET_ISTISNA: dict[tuple[str, str], str] = {
    ("TP.TUKFIY2025.GENEL", "Enflasyon"):
        "Panelde yer dar; TÜFE'nin okurun kullandığı adı 'enflasyon'.",
    ("TP.FE25.OKTG04", "Çekirdek (C)"):
        "Panelde kısaltma; tam ad 'Çekirdek enflasyon (C)'.",
    ("TP.YISGUCU2.G8", "İşsizlik"):
        "Panelde kısaltma; tam ad 'İşsizlik oranı'.",
    ("TP.DK.USD.S.YTL", "USD/TRY"):
        "Serinin kayıtlı adı zaten USD/TRY; birim alanı farklı.",
    ("TP.APIFON4", "Ortalama fonlama"):
        "Tam ad 'TCMB ağırlıklı ortalama fonlama maliyeti'; panelde "
        "sığmıyor. 'Politika faizi' DEĞİL -- ikisi ayrı büyüklük ve "
        "sapabiliyor.",
}

#: YANLIS SERIYE VERILMESI YASAK ADLAR: (seri kodu, ad) -> sebep.
#:
#: Yasak ADIN KENDISI degil, ADIN YANLIS SERIYE VERILMESI. "Politika
#: faizi" etiketi TCMB_POLITIKA serisinde DOGRU; TP.APIFON4'te (fonlama
#: maliyeti) yanlis ve tam bu yuzden %40 yazilirken gercek oran %37
#: idi.
#:
#: Ilk yazimda yasak liste ADA bakiyordu ve dogru seriyi de engellerdi.
YASAK_ETIKET: dict[tuple[str, str], str] = {
    ("TP.APIFON4", "Politika faizi"):
        "TP.APIFON4 ağırlıklı ortalama FONLAMA MALİYETİdir. Politika "
        "faizi (bir hafta vadeli repo) ayrı bir büyüklüktür ve sapar; "
        "bu ad %40 yazılırken gerçek oranın %37 olduğu hataya yol açtı. "
        "Politika faizi için TCMB_POLITIKA serisi var.",
    ("TP.APIFON4", "Faiz"):
        "Belirsiz ad; hangi faiz olduğu yazılmalı.",
    ("TP.FG.J0", "TÜFE"):
        "TP.FG.J0 endeks SEVİYESİ; sayfada yıllık değişim gösteriliyor.",
}


def kayitli_seriler() -> dict[str, str]:
    """Kod -> kayitli ad. IKI KAYNAK BIRDEN.

    `takvim` yayin takvimine giren serileri tutuyor, `evds` ise TCMB'den
    cekilen butun serileri. Panel ikisinden de kalem gosterebiliyor --
    ilk yazimda yalnizca `takvim` bakiliyordu ve USD/TRY "seri kayitli
    degil" diye HATA veriyordu, oysa `evds`de tanimli.
    """
    kayit = {s[0]: s[1] for s in takvim.SERILER + takvim.YERLI_SERILER}
    for s in getattr(evds, "SERILER", ()):
        kayit.setdefault(s[0], s[1])
    # Politika faizi EVDS serisi degil: TCMB'nin PPK duyurusundan
    # okunuyor (bkz. kaynak/politika_faizi.py).
    kayit.setdefault(politika_faizi.KOD, politika_faizi.AD)
    return kayit


def etiket_denetimi() -> list[Bulgu]:
    kayit = kayitli_seriler()
    bulgu: list[Bulgu] = []

    for kod, ad, _birim, _bas in dosya.TURKIYE_PANEL:
        sebep = YASAK_ETIKET.get((kod, ad))
        if sebep:
            bulgu.append(Bulgu(
                "hata", "etiket", kod,
                f"{ad!r} bu seride yasak -- {sebep}"))
            continue
        gercek = kayit.get(kod)
        if gercek is None:
            bulgu.append(Bulgu(
                "hata", "etiket", kod,
                f"panelde var ama seri kayitli degil ({ad!r})"))
            continue
        if ad == gercek:
            continue
        if (kod, ad) in ETIKET_ISTISNA:
            continue
        bulgu.append(Bulgu(
            "hata", "etiket", kod,
            f"panel {ad!r} diyor, seri kaydi {gercek!r}. Farkliysa "
            f"ETIKET_ISTISNA'ya GEREKCESIYLE yazilmali."))
    return bulgu


# --------------------------------------------------------------------
# 2. ARALIK DENETIMI
# --------------------------------------------------------------------
#
# Sinirlar GENIS tutuldu: dar sinir her olagandisi gelismede yanlis
# alarm verir ve alarmi degersizlestirir. Amac uc degerleri degil,
# BIRIM/ANLAM hatalarini yakalamak -- "%332" gibi.
ARALIK: dict[str, tuple[float, float, str]] = {
    "%": (-100.0, 200.0, "yüzde"),
    "bin kişi": (-20000.0, 500000.0, "bin kişi"),
    "kişi": (-5_000_000.0, 400_000_000.0, "kişi"),
    "mn $": (-100_000.0, 100_000.0, "milyon dolar"),
    "$": (0.0, 100_000.0, "dolar"),
    "TL": (0.0, 10_000.0, "lira"),
    "bin adet": (0.0, 10_000.0, "bin adet"),
    "endeks": (0.0, 100_000.0, "endeks"),
}

#: Seriye ozgu daha dar sinir. Genel birim sinirinin kacirdiklari icin.
SERI_ARALIK: dict[str, tuple[float, float]] = {
    "UNRATE": (0.0, 40.0),
    "ICSA": (0.0, 10_000_000.0),
    # NSA seriler manset icin kullaniliyor (bkz. takvim.SERILER);
    # SA olanlar gecmis kayitlarda duruyor, ikisinin de siniri ayni.
    "CPIAUCNS": (-30.0, 150.0),
    "CPILFENS": (-30.0, 150.0),
    "CPIAUCSL": (-30.0, 150.0),
    "CPILFESL": (-30.0, 150.0),
    "PCEPILFE": (-30.0, 150.0),
    "PPIFIS": (-40.0, 200.0),
    "CES0500000003": (-50.0, 100.0),
    "MICH": (0.0, 30.0),
    "GDPC1": (-30.0, 30.0),
    "RSAFS": (-50.0, 100.0),
    "INDPRO": (-40.0, 60.0),
    # --- Turkiye ---
    "TP.YISGUCU2.G8": (0.0, 60.0),
    "TP.APIFON4": (0.0, 100.0),
    "TCMB_POLITIKA": (0.0, 100.0),
    "TP.TUKFIY2025.GENEL": (-30.0, 300.0),
    "TP.FE25.OKTG04": (-30.0, 300.0),
    "TP.TUFE1YI.T1": (-30.0, 400.0),
    "TP.ENFBEK.PKA12ENF": (0.0, 200.0),
    "TP.ENFBEK.HBA12ENF": (0.0, 200.0),
    "TP.ENFBEK.IYA12ENF": (0.0, 200.0),
}


def aralik_denetimi(b) -> list[Bulgu]:
    bulgu: list[Bulgu] = []
    seriler = {s[0]: s for s in takvim.SERILER + takvim.YERLI_SERILER}
    for kod, s in seriler.items():
        r = b.execute("SELECT deger, birim, tarih FROM gosterge WHERE kod=?"
                      " ORDER BY tarih DESC LIMIT 1", (kod,)).fetchone()
        if not r:
            continue
        deger, birim, tarih = r[0], r[1] or "", r[2]
        ozel = SERI_ARALIK.get(kod)
        if ozel and not (ozel[0] <= deger <= ozel[1]):
            bulgu.append(Bulgu(
                "hata", "aralik", kod,
                f"{deger} seri sinirinin disinda ({ozel[0]}..{ozel[1]}) "
                f"-- birim/sunum hatasi olabilir"))
            continue
        sinir = ARALIK.get(birim)
        if sinir and not (sinir[0] <= deger <= sinir[1]):
            bulgu.append(Bulgu(
                "hata", "aralik", kod,
                f"{deger} {birim} makul araligin disinda "
                f"({sinir[0]}..{sinir[1]} {sinir[2]})"))
    return bulgu


# --------------------------------------------------------------------
# 3. BIRIM / SUNUM TUTARLILIGI
# --------------------------------------------------------------------
#
# `sunum` alani neyin gosterilecegini soyluyor. "yillik" sunulan bir
# seri yuzde degisimdir ve birimi "%" OLMAK ZORUNDA. CPIAUCSL tam
# burada kacmisti: sunum "yillik", ama depoya endeks SEVIYESI yazildi
# ve birim "%" kaldi.
def birim_denetimi() -> list[Bulgu]:
    bulgu: list[Bulgu] = []
    for s in takvim.SERILER + takvim.YERLI_SERILER:
        kod, _ad, birim, _konu, _frekans, _onem, sunum = s[:7]
        if sunum == "yillik" and birim != "%":
            bulgu.append(Bulgu(
                "hata", "birim", kod,
                f"sunum 'yillik' ama birim {birim!r} -- yillik degisim "
                f"yuzdedir"))
        if sunum == "seviye" and birim == "%" and kod not in SERI_ARALIK:
            bulgu.append(Bulgu(
                "uyari", "birim", kod,
                "sunum 'seviye' ve birim '%' -- seri gercekten oran mi, "
                "yoksa endeks seviyesi mi? SERI_ARALIK'a sinir ekleyin."))
    return bulgu


# --------------------------------------------------------------------
# 4. TAZELIK
# --------------------------------------------------------------------
#
# Bayat bir sayi, yanlis bir sayi kadar zararli olabilir: sayfa onu
# "bugunku gorunum" diye sunuyor.
def tazelik_denetimi(b) -> list[Bulgu]:
    from datetime import date, datetime
    bugun = date.today()
    bulgu: list[Bulgu] = []
    for s in takvim.SERILER + takvim.YERLI_SERILER:
        kod, ad, _birim, _konu, frekans = s[0], s[1], s[2], s[3], s[4]
        r = b.execute("SELECT tarih FROM gosterge WHERE kod=?"
                      " ORDER BY tarih DESC LIMIT 1", (kod,)).fetchone()
        if not r:
            bulgu.append(Bulgu("uyari", "tazelik", kod,
                               f"{ad}: depoda hic gozlem yok"))
            continue
        try:
            g = datetime.strptime(r[0][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        yas = (bugun - g).days
        sinir = takvim.BAYAT_GUN.get(frekans, takvim.BAYAT_VARSAYILAN)
        # Iki kat esik: bir donem gecikme normal, iki donem degil.
        if yas > sinir * 2:
            bulgu.append(Bulgu(
                "uyari", "tazelik", kod,
                f"{ad}: son gozlem {r[0]} ({yas} gun; {frekans} seri icin "
                f"esik {sinir})"))
    return bulgu


# --------------------------------------------------------------------
# 5. CIKTI TARAMASI -- yayimlanan sayfalarda yasak etiket
# --------------------------------------------------------------------
#
# NEDEN AYRI BIR ADIM: tablo denetimi `TURKIYE_PANEL`e bakiyordu ve
# panel etiketi duzeltildikten sonra 0 hata veriyordu. Ama AYNI YANLIS
# AD baska bir yerde daha yasiyordu -- `_bulgu_faiz` fonksiyonu
# "Politika faizi %40,00" diye bir bulgu cumlesi uretiyordu ve o cumle
# 14 sayfada basiliyordu.
#
# Ders: tabloyu denetlemek yetmiyor, CIKTIYI denetlemek gerekiyor.
# Okur tabloyu gormuyor, sayfayi goruyor.
CIKTI_DIZINI = _KOK.parent / "site" / "cikti"

#: Yayimlanan sayfada bir SAYIYLA yan yana gorulmemesi gereken adlar.
#: Kavramin kendisinden soz eden metin serbest ("politika faizinden
#: sapabilir"); yasak olan, o ada bir DEGER iliStirmek.
YASAK_ESLESME: tuple[tuple[str, str], ...] = (
    (r"TÜFE endeksi[^<]{0,12}%\s*\d",
     "endeks seviyesi yuzde olarak sunulamaz"),
    # "Ortalama fonlama %40" KURALI KALDIRILDI.
    #
    # Konuldugunda iki sayfayi isaretledi ve ikisi de DOGRUYDU:
    #
    #   "Ortalama fonlama maliyeti %40,00 seviyesinde sabit kalarak
    #    degismedi. Bu oran, bankalarin kisa vadeli borclanma
    #    maliyetini gosterir..."
    #
    # Fonlama maliyeti gercekten %40 ve cumle onu dogru tarif ediyor.
    # Panelden kaldirilmis olmasi, kavramin YOK oldugu anlamina
    # gelmiyor -- metinde gecmesi mesru.
    #
    # DERS: dogru icerigi isaretleyen bir denetim, denetimin kendisini
    # degersizlestirir. Okunmayan alarm, olmayan alarmdir. Asil koruma
    # zaten uc katmanda duruyor: (seri, etiket) cifti, `yorumcu.YASAK`
    # ve aralik/birim denetimi.
)


def cikti_denetimi() -> list[Bulgu]:
    import re
    if not CIKTI_DIZINI.exists():
        return [Bulgu("uyari", "cikti", "-",
                      "site/cikti yok -- once site kurulmali")]
    bulgu: list[Bulgu] = []
    for desen, sebep in YASAK_ESLESME:
        d = re.compile(desen)
        sayfalar = []
        for s in CIKTI_DIZINI.rglob("*.html"):
            if d.search(s.read_text(encoding="utf-8")):
                sayfalar.append(s.name)
        if sayfalar:
            bulgu.append(Bulgu(
                "hata", "cikti", desen[:28],
                f"{len(sayfalar)} sayfada deger iliStirilmis -- {sebep}"))
    return bulgu


# --------------------------------------------------------------------
# 6. EDITORYAL DENETIM -- yayimlanan sayfalarin icerik kalitesi
# --------------------------------------------------------------------
#
# Onceki bes baslik VERIYI denetliyor. Bu baslik ICERIGI: gorsel
# tekrari, bolumler arasi tekrar, son dakika disiplini.
#
# HEPSI OLCULEBILIR OLANLAR. "Gorsel haberle ilgili mi" ya da "baslik
# sansasyonel mi" gibi yargi gerektiren maddeler BURADA YOK -- bir
# denetim ancak olcebildigini denetlemeli, yoksa yanlis alarm uretir
# ve kendini degersizlestirir (bkz. kaldirilan "Ortalama fonlama"
# kurali).

#: Ayni fotografin kac haberde tekrar etmesi FAZLA sayilir.
#: Olculdu: 28 sayfali haberde 16 farkli fotograf, biri 5 haberde.
#: Konu bazli secim dogru calisiyor ama havuz dar.
FOTO_TEKRAR_ESIGI = 4

#: Ayni sayfada bir baslik en fazla kac bolumde gecebilir.
#: Seyir cizelgesi ile "Bunu da okuyun" ayni basligi veriyordu:
#: 151 sayfada, on santim arayla, ayni baglanti.
BASLIK_TEKRAR_ESIGI = 1


#: Yorumdaki sayilarin en az bu orani sayfada da gecmeli.
#:
#: Birebir "hepsi" istenmiyor: yorum iki degerin FARKINI yazabilir
#: ("35 baz puan") ve o sayi hicbir yerde durmaz. Ama uydurma sayilar
#: tek basina gelmiyor -- olculdu, dusen yorumlarda ortalama iki-uc
#: kacak sayi vardi.
YORUM_SAYI_ORANI = 0.5

_SAYI_KALIBI = re.compile(r"\d[\d.]*,\d+|\d{1,3}(?:\.\d{3})+|\d{2,}")


def _sayi_anahtari(ham: str) -> str:
    """Sayiyi ayrac ALISKANLIGINDAN bagimsiz bir anahtara cevirir.

    NEDEN GEREKLI
    -------------
    Olculdu (2026-08-24): "daha-uzun-kuyular-permiyen..." sayfasi
    "yorumdaki 15.000 sayfada gecmiyor" uyarisi aldi. Oysa sayi
    sayfada VARDI -- Ingilizce kaynak alintisinda:

        "...super-lateral wells that exceed 15,000 feet"   (sayfa)
        "...15.000 fitlik esigi asan super-lateral..."     (yorum)

    Ayni sayi, iki ayri ayrac aliskanligi. Duz dizge karsilastirmasi
    bunlari FARKLI goruyor ve okurun pekala dogrulayabildigi bir
    yorumu "dogrulanamaz" diye isaretliyor.

    Yanlis alarm zararsiz degil: denetimin isi gercek hatayi one
    cikarmak ve her kosuda tekrarlayan sahte bulgu, gercek bulgunun
    onunu kapatiyor. Ingilizce besleme sayisi arttikca (2026-08-24'te
    yedi resmi kaynak eklendi) bu her gun tekrarlardi.

    NASIL AYIRT EDILIYOR
    --------------------
    Son ayractan sonra TAM UC hane varsa ve butun gruplar uc haneliyse
    ayrac BINLIK sayilir; aksi halde ONDALIK. Boylece:

        "15,000" ve "15.000"  -> "15000"    (ayni sayi)
        "1,17"   ve "1.17"    -> "1.17"     (ayni sayi)
        "1.234,56"            -> "1234.56"

    Belirsiz tek durum "1.500": Turkce bin bes yuz, Ingilizce bir
    nokta bes. Binlik okunuyor -- Ingilizce metin 1,5 degerini
    "1.500" diye yazmiyor, "1.5" yaziyor.
    """
    s = ham.strip()
    if not re.fullmatch(r"\d[\d.,]*", s):
        return s
    son = max(s.rfind("."), s.rfind(","))
    if son == -1:
        return s
    kuyruk = s[son + 1:]
    if len(kuyruk) == 3 and re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        return s.replace(".", "").replace(",", "")
    tam = s[:son].replace(".", "").replace(",", "")
    return f"{tam}.{kuyruk}"


def _baslik_tekrari_denetimi() -> list[Bulgu]:
    """Iki sayfanin `<title>` etiketi ayni olmamali.

    Ayni baslik hem okur hem arama motoru icin ayirt edilemezlik demek.
    Olculdu, iki ayri sebeple 23 baslik ciftlenmisti:

      * Olay motorunun yazisi haberin basligini AYNEN kullaniyordu;
        sonuc `/haber/<slug>/` ve `/analiz/<slug>-<tarih>/` ciftiydi.
        Icerikleri farkli (fiyat tepkisi vs haberin kendisi) ama
        basliklari ayniydi.
      * Gunluk teknik yazilarin basligi olculen degerden uretiliyor;
        ayni yuvarlanmis deger iki gun ust uste cikinca baslik da
        tekrarliyordu ("Brent %29,7 yukselip geri cekildi" ALTI kez).
    """
    import collections as _c

    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu
    g: dict[str, list[str]] = _c.defaultdict(list)
    for p in CIKTI_DIZINI.rglob("index.html"):
        m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"),
                      re.S)
        if m:
            g[" ".join(m.group(1).split())].append(
                "/" + p.parent.relative_to(CIKTI_DIZINI).as_posix() + "/")
    for baslik, yollar in g.items():
        if len(yollar) > 1:
            bulgu.append(Bulgu(
                "uyari", "editoryal", baslik[:40],
                f"{len(yollar)} sayfada ayni <title>: "
                f"{', '.join(yollar[:2])}"))
    return bulgu


def _lisans_denetimi() -> list[Bulgu]:
    """Yayimlanan her havuz gorselinin atfi var mi?

    CC BY ATFI ZORUNLU -- hukuki bir yukumluluk, tercih degil. Bu
    yuzden agirligi HATA: eksik atif dagitimi durdurmali.

    Iki gecerli bicim var:
      * `<figure>` icinde `<figcaption>` -- haber sayfasindaki buyuk
        gorsel boyle basiliyor.
      * Sayfa altinda toplu kunye -- liste sayfalarindaki kart
        gorselleri icin; kart basina kunye izgarayi bozuyor.

    Olculdu: haber sayfalarinda 417/417 kunyeliydi ama liste
    sayfalarindaki 48 kart gorseli kunyesizdi ve bu hicbir yerde
    gorunmuyordu.
    """
    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu
    kart = re.compile(r'src="(/statik/foto/(?!k/)[^"]+)"')
    for p in CIKTI_DIZINI.rglob("index.html"):
        metin = p.read_text(encoding="utf-8")
        yollar = set(kart.findall(metin))
        if not yollar:
            continue
        for m in re.finditer(r"<figure[^>]*>.*?</figure>", metin, re.S):
            if "figcaption" in m.group():
                yollar -= set(kart.findall(m.group()))
        if yollar and "foto-kunye-toplu" not in metin:
            bulgu.append(Bulgu(
                "hata", "gorsel", (p.parent.name or "/")[:40],
                f"{len(yollar)} gorsel ATIFSIZ basiliyor -- CC BY ihlali"))
    return bulgu


#: Uretilen gorselin yaninda GECMESI ZORUNLU ifade.
#:
#: `gorsel_uret.ETIKET` ile ayni sozu tasiyor ama BURADAN okunmuyor:
#: denetim, uretim modulu silinse ya da etiket sessizce degistirilse
#: bile ayni seyi aramali. Etiketi tek yerden okumak, etiketi
#: bosaltarak denetimi de susturmayi mumkun kilardi.
_URETILEN_ETIKET = re.compile(r"yapay zeka ile üretilmiş", re.I)

#: Uretilen kavram cizimlerinin yolu.
_URETILEN_YOL = re.compile(r'src="(/statik/foto/uretilen/[^"]+)"')


def _uretilen_gorsel_denetimi() -> list[Bulgu]:
    """Uretilen her cizim, URETILDIGINI SOYLUYOR mu?

    NEDEN AGIRLIGI HATA
    -------------------
    Bu sitenin butun degeri "hicbir sey uydurulmaz" iddiasinda.
    Uretilmis bir gorseli etiketsiz basmak, okura onu bir olayin
    fotografi olarak sunmak demek -- yani tam da yapmadigimizi
    soyledigimiz sey.

    CC BY atfi nasil hukuki bir yukumlulukse bu da editoryal bir
    yukumluluk; ikisi de dagitimi durdurmali.

    `_lisans_denetimi` BU ISI GORMEZ: o yalnizca bir `<figcaption>`
    VARLIGINA bakiyor, icerigine degil. Uretilen cizime "Fotograf:
    Netaris" yazan bir kunye o denetimden gecerdi ve tam da onlenmek
    istenen yanlisi uretirdi.
    """
    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu
    for p in CIKTI_DIZINI.rglob("index.html"):
        metin = p.read_text(encoding="utf-8")
        yollar = set(_URETILEN_YOL.findall(metin))
        if not yollar:
            continue
        # Etiket gorselin KENDI `<figure>`inde olmali. Sayfanin baska
        # bir yerinde gecen bir ifade, o gorselin yaninda durmuyor.
        etiketli: set[str] = set()
        for m in re.finditer(r"<figure[^>]*>.*?</figure>", metin, re.S):
            if _URETILEN_ETIKET.search(m.group()):
                etiketli |= set(_URETILEN_YOL.findall(m.group()))
        eksik = yollar - etiketli
        if eksik:
            bulgu.append(Bulgu(
                "hata", "gorsel", (p.parent.name or "/")[:40],
                f"{len(eksik)} üretilen çizim ETİKETSİZ basılıyor -- "
                f"okur onu fotoğraf sanır"))
    return bulgu


#: Fiyat seridini besleyen istemci betigi.
CANLI_BETIK = _KOK.parent / "site" / "statik" / "canli.js"


def _serit_adlari_js(kaynak: str) -> set[str]:
    """`canli.js`in seride EKLEDIGI gorunen adlar.

    Adlar uc ayri bicimde yaziliyor ve UCUNU DE okumak sart --
    olculdu: yalnizca dogrudan `kalemKur(` cagrilarini arayan ilk
    surumum alti addan yalnizca birini buldu ve "cakisma yok" dedi.
    Eksik tarama, temiz rapor uretir; en tehlikeli yanlis budur.
    """
    return (
        set(re.findall(r'kalemKur\(\s*"[^"]+",\s*"([^"]+)"', kaynak))
        | set(re.findall(r'\bekle\(\s*"[^"]+",\s*"([^"]+)"', kaynak))
        | set(re.findall(r'\bad:\s*"([^"]+)"', kaynak))
    )


def _serit_cakismasi_denetimi() -> list[Bulgu]:
    """Ayni enstruman seride hem sunucudan hem istemciden giriyor mu?

    NEDEN VAR. Serit iki katmanli: gunluk resmi seriler sunucuda
    basiliyor, gercek zamanli kalemler `canli.js` ile ekleniyor.
    Istemci katmani kalemi `data-kalem` ile ARIYOR; sunucunun bastigi
    kalemlerde bu oznitelik YOK (olculdu: 72 kalemin 72'sinde yok).
    Yani eslesme hicbir zaman tutmaz -- ayni adli bir kalem
    guncellenmez, YENISI yaratilir.

    NASIL DOGDU. Serit basta yalnizca FRED'den besleniyordu, kur
    sunucuda yoktu ve USD/TRY ile EUR/USD'yi `canli.js` Frankfurter'dan
    cekiyordu. Sunucu tarafina TCMB kurlari eklenince eski katman
    yerinde kaldi; okur ayni seritte USD/TRY'yi iki kez, iki farkli
    degerle gordu (TCMB 47,71 / Frankfurter 47,695).

    Ikisinden hangisinin dogru oldugu onemli degil -- bir fiyat
    seridinde ayni enstrumanin iki fiyati veri degil, guvensizliktir.
    Bu yuzden agirlik HATA: dagitimi durdurur.

    Statik olarak yakalanabilir cunku iki liste de kaynak dosyalarda
    yazili; tarayici calistirmak gerekmiyor.
    """
    bulgu: list[Bulgu] = []
    anasayfa = CIKTI_DIZINI / "index.html"
    if not (CANLI_BETIK.exists() and anasayfa.exists()):
        return bulgu

    js_adlari = _serit_adlari_js(CANLI_BETIK.read_text(encoding="utf-8"))
    if not js_adlari:
        # Betik duruyor ama hicbir ad okunamadi: ya bicim degisti ya
        # katman bosaldi. Sessiz gecmek, denetimi ise yaramaz kilar.
        bulgu.append(Bulgu(
            "uyari", "veri", "serit",
            "canli.js'te kalem adi okunamadi -- denetim dogrulanamiyor"))
        return bulgu

    metin = anasayfa.read_text(encoding="utf-8")
    sunucu = {
        html.unescape(b).split(" —")[0]
        for b in re.findall(r'title="([^"]+)"', metin)
        if " — son veri" in html.unescape(b)
    }
    for ad in sorted(sunucu & js_adlari):
        bulgu.append(Bulgu(
            "hata", "veri", "serit",
            f"{ad} seride HEM sunucudan HEM canli.js'ten giriyor"
            " -- ayni enstruman iki farkli degerle gorunur"))
    return bulgu


#: Yayimlanan GORUNUR metinde asla bulunmamasi gereken izler.
#:
#: Her biri olculmus bir olaydan geliyor, tahminden degil: bir haberin
#: ozeti ham bir TradingView gomme betigiydi ve okur bunu "Ne oldu?"
#: sorusunun cevabi olarak gordu.
_COP_IZI = (
    ("cozulmemis yer tutucu", re.compile(r"\{\{|\{%|%%\w+%%")),
    ("kacirilmis etiket", re.compile(r"<\s*/?\s*(script|style|div|iframe|"
                                     r"span|table|img|br)\b", re.I)),
    ("betik govdesi", re.compile(r"\bfunction\s*\(|\bvar\s+\w+\s*=|"
                                 r"\bnew\s+[A-Z]\w+\s*\(|container_id")),
)


def _gorunur_metin(sayfa: str) -> str:
    """Sayfanin okur tarafindan GORULEN metni.

    `<script>`/`<style>`/`<svg>` govdeleri once atiliyor -- onlarin
    icinde kod bulunmasi olagan. Kalan etiketler silindikten SONRA
    hala kod izi varsa, o iz metnin kendisindedir.
    """
    m = re.search(r"<main[^>]*>(.*?)</main>", sayfa, re.S)
    ic = m.group(1) if m else ""
    ic = re.sub(r"<(script|style|svg)\b[^>]*>.*?</\1\s*>", " ", ic,
                flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", ic)


def _cop_denetimi() -> list[Bulgu]:
    """Sayfa govdesinde isaretleme/betik artigi var mi?

    NEDEN YAYIN UCUNDA. Asil duzeltme `besleme._metin`de: kacislar
    artik etiketler silinmeden ONCE cozuluyor. Ama o duzeltme yalnizca
    BESLEME alanini koruyor; ozet, baslik, kurum adi ve ileride
    eklenecek her alan ayni copu tasiyabilir. Burasi son kapi ve
    ALANDAN BAGIMSIZ calisir.

    Agirlik HATA: okur "Ne oldu?" sorusunun cevabi olarak JavaScript
    goruyorsa o sayfa yayimlanmamalidir.
    """
    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu
    for p in CIKTI_DIZINI.rglob("index.html"):
        gorunur = _gorunur_metin(p.read_text(encoding="utf-8"))
        for ad, kalip in _COP_IZI:
            m = kalip.search(gorunur)
            if m:
                bulgu.append(Bulgu(
                    "hata", "editoryal", (p.parent.name or "/")[:40],
                    f"govdede {ad}: {m.group()[:30]!r}"))
                break
    return bulgu


def _foto_butunluk_denetimi() -> list[Bulgu]:
    """Gorsel havuzu kendi icinde tutarli mi?

    UC AYRI HATA SINIFI, ucu de olculmus olaydan geliyor.

    1. OKSUZ BOY SURUMU. `foto.suz` bir gorseli elerken yalnizca buyuk
       dosyayi siliyordu; `o/` ve `k/` surumleri diskte kaliyordu.
       Gorevden ayrilan Fed baskaninin fotograflari boyle elendi ve
       `foto/o/fed-5.jpg` ile iki kardesi yayimlanmis halde,
       adresle ulasilabilir sekilde durdu. Hicbir sayfa kullanmiyordu
       -- yani hicbir denetim de gormuyordu. "Silindi" demek dosyanin
       gitmesi demektir.

    2. KAYIT-DISK AYRISMASI. Deftere yazili bir gorselin dosyasi yoksa
       sayfa kirik resimle cikar; dosyasi olup deftere yazili olmayan
       gorsel ise atifsiz yayimlanma riski tasir (CC BY yukumlulugu).

    3. ELENMIS KISI. Havuzdan elenen kisi gorselleri (bkz.
       `foto.GECMIS_GOREVLI`) yeniden indirilmis olabilir; defter
       kunyesi uzerinden aranıyor.
    """
    bulgu: list[Bulgu] = []
    try:
        import foto as _foto            # noqa: PLC0415
    except ImportError:
        return bulgu

    ana = _foto.FOTO_KLASORU
    if not ana.exists():
        return bulgu

    buyuk = {p.name for p in ana.glob("*") if p.is_file()}
    for klasor, etiket in ((_foto.ORTA_KLASOR, "o"), (_foto.KUCUK_KLASOR, "k")):
        if not klasor.exists():
            continue
        oksuz = sorted({p.name for p in klasor.glob("*") if p.is_file()} - buyuk)
        if oksuz:
            bulgu.append(Bulgu(
                "hata", "gorsel", f"foto/{etiket}",
                f"{len(oksuz)} oksuz boy surumu -- buyugu silinmis ama "
                f"bu surum duruyor: {', '.join(oksuz[:3])}"))

    kayit = _foto.Kayit()
    kayitli = {f["dosya"].rsplit("/", 1)[-1]
               for liste in kayit.veri.values() for f in liste}
    eksik = sorted(kayitli - buyuk)
    if eksik:
        bulgu.append(Bulgu(
            "hata", "gorsel", "foto",
            f"{len(eksik)} kayitli gorselin DOSYASI yok: {', '.join(eksik[:3])}"))
    fazla = sorted(buyuk - kayitli)
    if fazla:
        bulgu.append(Bulgu(
            "uyari", "gorsel", "foto",
            f"{len(fazla)} dosya deftere yazili degil -- atifi "
            f"dogrulanamaz: {', '.join(fazla[:3])}"))

    elenmis = tuple(getattr(_foto, "GECMIS_GOREVLI", ()))
    if elenmis:
        for konu, liste in kayit.veri.items():
            for f in liste:
                metin = f"{f.get('kunye', '')} {f.get('sorgu', '')}".lower()
                for kisi in elenmis:
                    if kisi in metin:
                        bulgu.append(Bulgu(
                            "hata", "gorsel", konu[:40],
                            f"elenmis kisi havuza geri girmis: {kisi}"))
    return bulgu


#: `stil.css` icinde OLMASI GEREKEN en az jeton kullanimi.
#:
#: Bu sayilar BASKA BIR DOSYADA duruyor ve sebebi tam olarak bu:
#: `stil.css` CI'in her kosusunda yeniden uretiliyor, bu yuzden
#: neredeyse her `git pull`da cakisiyor. Cakismada taraf secmek
#: (`--theirs`) kolay gorunuyor ama CI'in ciktisi jetonlari
#: ICERMIYOR -- yani secim, tasarim olcegini sessizce siliyor.
#:
#: Olculdu (2026-08-20): tipografi jetonlari `5c71dcc`de 49 kez
#: taniml, 169 kez kullanilmisti; iki tur sonra SIFIRDI. Boslugun
#: kendi turu de hicbir islemeye ulasmamisti. Iki turluk is kayipti
#: ve HICBIR denetim bunu gormedi.
#:
#: Gormemesinin sebebi onemli: EKSIK CSS JETONU HATA URETMIYOR.
#: `var(--p-l)` tanimsizsa tarayici o bildirimi atlar ve sayfayi
#: yine cizer. Test gecer, kirik bag cikmaz, gorsel denetim susar.
#: Kayip ancak SAYARAK goruluyor -- o yuzden burada sayiliyor.
JETON_TABANI = {"p-": 160, "b-": 300}


def _tasarim_jetonu_denetimi() -> list[Bulgu]:
    """Tipografi ve bosluk olcegi hala yerinde mi?

    Iki ayri sey olculuyor:
      1. KULLANIM SAYISI tabanin altina dustu mu (sessiz kayip)
      2. Tanimsiz jeton kullanilmis mi (yarim birlestirme)

    Yedegi olan `var(--x, deger)` kullanimlari SAYILMIYOR: onlar
    bilerek disaridan atanir (`analiz.html` ilerleme cubugunu satir
    ici `--w` ile veriyor) ve tanimsiz olmalari beklenen durumdur.
    """
    yol = _KOK.parent / "site" / "statik" / "stil.css"
    if not yol.exists():
        return [Bulgu("hata", "tasarim", "stil-yok", f"{yol.name} yok")]
    css = yol.read_text(encoding="utf-8")
    bulgu: list[Bulgu] = []

    for onek, taban in JETON_TABANI.items():
        n = len(re.findall(rf"var\(--{re.escape(onek)}", css))
        if n < taban:
            bulgu.append(Bulgu(
                "hata", "tasarim", f"jeton-{onek.strip('-')}",
                f"--{onek}* kullanimi {n}, taban {taban}. Olcek "
                f"dusmus -- muhtemelen birlestirmede CSS'in CI surumu "
                f"alindi. Onarim: yamayi `git apply --3way` ile "
                f"yeniden uygula, taraf secme."))

    tanim = set(re.findall(r"--([\w-]+)\s*:", css))
    # Yedeksiz kullanim: `var(--x)` -- virgul YOK.
    for ad in set(re.findall(r"var\(--([\w-]+)\s*\)", css)):
        if ad not in tanim:
            bulgu.append(Bulgu(
                "hata", "tasarim", "jeton-tanimsiz",
                f"--{ad} kullaniliyor ama TANIMLI DEGIL; yedegi de "
                f"yok. Tarayici bu bildirimi atlar, hata vermez."))
    return bulgu


def _kanonik_adres_denetimi() -> list[Bulgu]:
    """Sitenin kendi ilan ettigi adres GERCEKTEN var mi?

    NEDEN VAR. Yayimlanan ciktida kanonik adres 2402 yerde geciyordu ve
    hepsi `https://netaris.com` diyordu -- o alan adi ise HIC
    cozumlenmiyordu. Var olmayan bir alan adina kanonik vermek,
    `sitemap.xml`, `robots.txt`, RSS ve `og:url`in tamamini olu bir
    hedefe yollamak demek. Arama motoruna "asil surumum su adreste"
    denip o adreste hicbir sey olmamasi, sayfayi dizine SOKMAMANIN en
    etkili yolu; yani sitenin gorunmezligi bir eksiklik degil, ETKIN
    olarak yayimlanan bir talimatti.

    Hicbir test bunu yakalayamazdi: kod dogru calisiyor, sablon dogru
    basiyor, baglantilar bicim olarak gecerli. Yanlis olan tek sey
    hedefin var olmamasi -- bu yalnizca DISARIYA sorularak anlasilir.

    AGSIZ ORTAMDA SESSIZ. CI ya da cevrimdisi calistirmada ad
    cozumleme basarisiz olabilir; bu bir yayin hatasi degildir. Ayrimi
    KONTROL ADI ile yapiyoruz: o da cozulemiyorsa ag yok demektir ve
    denetim atlanir. Yalnizca kontrol cozulup BIZIM adres cozulemezse
    bulgu uretiliyor.
    """
    bulgu: list[Bulgu] = []
    cikti = CIKTI_DIZINI / "robots.txt"
    if not cikti.exists():
        return bulgu
    m = re.search(r"https?://([a-zA-Z0-9.-]+)", cikti.read_text(encoding="utf-8"))
    if not m:
        return bulgu
    konak = m.group(1)

    import socket        # noqa: PLC0415

    def cozulur(ad: str) -> bool:
        try:
            socket.getaddrinfo(ad, 443, proto=socket.IPPROTO_TCP)
            return True
        except OSError:
            return False

    if not cozulur("cloudflare.com"):
        return bulgu          # ag yok -- denetlenemez, hata da denemez
    if not cozulur(konak):
        bulgu.append(Bulgu(
            "hata", "editoryal", "adres",
            f"site kendi adresi olarak {konak} diyor ama bu ad "
            f"cozumlenmiyor -- kanonik, sitemap ve RSS olu hedefe bakiyor"))
    return bulgu


def _veri_tutarlilik_denetimi() -> list[Bulgu]:
    """Yorumdaki sayilarin sayfada karsiligi var mi?

    PROMPT MADDE 7. Bir veri birden fazla yerde kullaniliyorsa hepsinde
    ayni olmali; buradaki kural daha temel: sayfada OLMAYAN bir veri
    yorumda da olmamali, cunku okur onu kontrol edemez.
    """
    import html as _html

    bulgu: list[Bulgu] = []
    dizin = CIKTI_DIZINI / "haber"
    if not dizin.exists():
        return bulgu
    for p in dizin.iterdir():
        s = p / "index.html"
        if not s.exists():
            continue
        metin = s.read_text(encoding="utf-8")
        m = re.search(r'<p class="ai-metin">(.*?)</p>', metin, re.S)
        if not m:
            continue
        yorum = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        sayfa = _html.unescape(
            re.sub(r"<[^>]+>", " ", metin.replace(m.group(0), "")))
        # KARSILASTIRMA ANAHTAR UZERINDEN: sayfa Ingilizce kaynagi
        # "15,000", yorum Turkce "15.000" yaziyor olabilir ve ikisi
        # AYNI SAYI (bkz. `_sayi_anahtari`).
        sayfa_sayilari = {_sayi_anahtari(x) for x in _SAYI_KALIBI.findall(sayfa)}
        yorum_sayilari = _SAYI_KALIBI.findall(yorum)
        if not yorum_sayilari:
            continue
        bulunan = sum(1 for x in yorum_sayilari
                      if _sayi_anahtari(x) in sayfa_sayilari)
        if bulunan < len(yorum_sayilari) * YORUM_SAYI_ORANI:
            kacak = sorted({x for x in yorum_sayilari
                            if _sayi_anahtari(x) not in sayfa_sayilari})[:3]
            bulgu.append(Bulgu(
                "uyari", "veri", p.name[:44],
                f"yorumdaki {', '.join(kacak)} sayfada gecmiyor -- "
                f"okur dogrulayamaz"))
    return bulgu


def _gorsel_denetimi() -> list[Bulgu]:
    """Yayimlanan sayfalardaki gorsel kullanimini denetler."""
    import collections
    import json
    import re

    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu

    # 1. ANA SAYFA -- iki ayri olcut, cunku iki ayri sey.
    #
    # KARTLAR: sekiz kadar buyuk gorsel, hepsi ayni ekranda. Ikinci kez
    # gorunen bir gorsel dogrudan hata izlenimi verir -> tekrar YOK.
    #
    # CANLI AKIS: kirk satirlik liste ve satirlarin cogu ayni konudan
    # geliyor ("Sirket haberleri" tek basina 15 satir). Sekiz gorselli
    # bir havuzla o listede tekrar MATEMATIKSEL OLARAK kacinilmaz;
    # tekrari hata saymak, dogru bir durumu isaretlemek olurdu. Orada
    # kusur YAN YANA dusmesidir -- okur ikisini birlikte gorur.
    ana = CIKTI_DIZINI / "index.html"
    if ana.exists():
        metin = ana.read_text(encoding="utf-8")
        akis = re.search(r'<ol class="akis-liste">.*?</ol>', metin, re.S)
        akis_metni = akis.group() if akis else ""
        kartlar = [y for y in re.findall(r'src="(/statik/foto/[^"]+)"', metin)
                   if "/foto/k/" not in y]
        for yol, n in collections.Counter(kartlar).items():
            if n > 1:
                bulgu.append(Bulgu(
                    "uyari", "gorsel", yol.split("/")[-1],
                    f"ana sayfada {n} kez -- okur tek bakista goruyor"))
        sira = re.findall(r'src="(/statik/foto/k/[^"]+)"', akis_metni)
        komsu = [sira[i] for i in range(1, len(sira)) if sira[i] == sira[i - 1]]
        for yol in komsu:
            bulgu.append(Bulgu(
                "uyari", "gorsel", yol.split("/")[-1],
                "canli akista iki satir ust uste ayni gorsel"))

    # 2. HABER SAYFALARI -- havuz ici denge
    #
    # IKI SAYAC TUTULUYOR ve sebebi farkli sorulara hizmet etmeleri:
    #
    #   `kullanim`      sayfada YAZAN yol. "Dosya var mi" sorusu bunu
    #                   ister; `y/ad.jpg` kirilmissa `ad.jpg`ye bakmak
    #                   kirigi gizlerdi.
    #   `kullanim_kok`  boy turevi KOKUNE indirgenmis yol. "Havuzdaki
    #                   gorseller esit dagitiliyor mu" sorusu bunu
    #                   ister; `y/ad.jpg` ile `ad.jpg` AYNI gorseldir.
    #
    # Olculdu (2026-08-28): bu ayrim yoktu ve 800 piksellik es
    # eklendikten sonra 29 gorsel yalnizca `y/` yoluyla basiliyordu.
    # Havuz karsilastirmasi onlari "0 kez" sayip UC havuzda yanlis
    # dengesizlik alarmi uretti; gercek dagilim neredeyse kusursuzdu.
    kullanim: collections.Counter = collections.Counter()
    kullanim_kok: collections.Counter = collections.Counter()
    sayfasiz = 0
    haber_dizini = CIKTI_DIZINI / "haber"
    if haber_dizini.exists():
        # KOKE INDIRGEME ASIL KAYNAKTAN GELIYOR, ELLE YAZILMIYOR.
        # Boy klasorlerinin listesi `foto.py`de duruyor; buraya
        # kopyalanan bir liste, yeni bir boy eklendiginde ayni hatanin
        # ikinci kez olmasi demekti.
        try:
            from kaynak.foto import asil_foto as _asil
        except ImportError:  # pragma: no cover -- paket bicimiyle
            def _asil(y: str) -> str:
                return y
        for p in haber_dizini.iterdir():
            s = p / "index.html"
            if not s.exists():
                continue
            m = re.search(r'src="(/statik/foto/[^"]+)"',
                          s.read_text(encoding="utf-8"))
            if m:
                kullanim[m.group(1)] += 1
                kullanim_kok[_asil(m.group(1))] += 1
            else:
                sayfasiz += 1
    if sayfasiz:
        bulgu.append(Bulgu("uyari", "gorsel", "-",
                           f"{sayfasiz} haber sayfasinda fotograf yok"))

    # DOSYASI OLMAYAN GORSEL HATADIR, UYARI DEGIL.
    #
    # Okur kirik bir gorsel kutusu goruyor ve hicbir yerde iz yok.
    # Olculdu: editoryal suzgec siklastiktan sonra iki sayfa silinmis
    # dosyaya isaret ediyordu.
    for yol, n in kullanim.items():
        if not (CIKTI_DIZINI / yol.lstrip("/")).exists():
            bulgu.append(Bulgu(
                "hata", "gorsel", yol.split("/")[-1],
                f"{n} sayfada kullaniliyor ama DOSYA YOK -- kirik gorsel"))

    # Havuz ici dagilim: bir havuzun en cok ve en az kullanilan gorseli
    # arasinda BIRDEN fazla fark varsa dagitim bozulmustur.
    kayit_yolu = _KOK / "kaynak" / "foto_kayit.json"
    if not kayit_yolu.exists() or not kullanim:
        return bulgu
    try:
        kayit = json.loads(kayit_yolu.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return bulgu
    #: Atif GEREKTIRMEYEN lisanslar -- `foto.Kayit.ATIFSIZ` ile AYNI.
    #:
    #: Iki yerde tutulan bir deger zamanla ayrisir ve ayrisma HATA
    #: VERMEZ; bu depoda ayni sinif ayrisma birkac kez yasandi. Bu
    #: yuzden asagida `foto` modulunden okunmaya CALISILIYOR ve
    #: yalnizca okunamazsa buradaki liste kullaniliyor.
    # SUZGEC KOPYALANMIYOR, ASIL FONKSIYON CAGRILIYOR.
    # -------------------------------------------------
    # Burada lisans suzgeci ELLE tekrarlaniyordu. Sonra
    # `foto.havuz_yayin` dort katmanli hale geldi (net+atifsiz > net >
    # atifsiz > hepsi) ve denetim eski haliyle kaldi: yayina GIRMEYEN
    # gorselleri de sayip "en az 0 kez" diye dengesizlik raporladi.
    #
    # Bu depoda ayni sinif ayrisma bugun besinci kez cikti. Kural: iki
    # kod yolu ayni karari vermeliyse KARAR TEK YERDE verilir.
    try:
        from kaynak.foto import Kayit as _FotoKayit
        _kayit_nesnesi = _FotoKayit()
    except Exception:
        _kayit_nesnesi = None

    for havuz, liste in kayit.items():
        # YALNIZCA YAYINA GIREN GORSELLER OLCULUYOR.
        #
        # Secim artik atif gerektirmeyen lisanslara oncelik veriyor
        # (bkz. `foto.havuz_yayin`): bir havuzda CC0/PDM gorsel varsa
        # CC BY olanlar HIC kullanilmiyor. Tam havuza bakan olcum bunu
        # "en az 0 kez" diye rapor ediyordu ve on bes havuzda yanlis
        # alarm uretti -- oysa o gorsellerin kullanilmamasi KARARIN
        # kendisi, dagitim bozuklugu degil.
        if _kayit_nesnesi is not None:
            yollar = [f.dosya for f in _kayit_nesnesi.havuz_yayin(havuz)]
        else:
            yollar = [f["dosya"] for f in liste]
        if not yollar:
            continue
        # KOKE INDIRGENMIS sayac: havuz kok yollari tutuyor, sayfa ise
        # boy turevini basiyor olabilir.
        kullanilan = [kullanim_kok.get(y, 0) for y in yollar]
        # Havuzdan HIC kullanilmayan varsa o havuz o gun devrede degil;
        # kismen kullanilan havuzda denge aranir.
        etkin = [n for n in kullanilan if n]
        if len(etkin) < 2:
            continue
        # OLCUT HAVUZA GORE OLCEKLENIYOR, SABIT TOLERANS DEGIL.
        #
        # Once "en cok ile en az arasi 2'den fazlaysa" deniyordu ve bu
        # havuz buyudukce yanlis alarm uretti: 12 gorselli Borsa
        # havuzunda 32 kullanimin dagilimi 4-4-3-3-3-3-3-2-2-2-2-1
        # cikti. Kusursuzu 3'er; 1 ile 4 arasindaki fark dengesizlik
        # degil, tamsayiya bolunmenin ARTIGI.
        #
        # Dogru olcut BEKLENEN PAY: toplam kullanim / havuz boyu. Bir
        # gorsel bu payin bir uzerini de asiyorsa yigilma vardir.
        # Gercekten bozuk dagitimda olcum 19 haber / 4 gorsel icin
        # 9-4-3-3 idi: beklenen pay 5, en cok 9 -- bu kural onu
        # yakalar, dogru dagilimi ise rahat birakir.
        import math as _m
        beklenen = _m.ceil(sum(kullanilan) / len(yollar)) if yollar else 0
        if max(etkin) > beklenen + 1:
            bulgu.append(Bulgu(
                "uyari", "gorsel", havuz,
                f"havuz dengesiz: en cok {max(etkin)}, en az "
                f"{min(kullanilan)} kez -- dagitim bozuk olabilir"))
    return bulgu


def editoryal_denetim() -> list[Bulgu]:
    import collections
    import json
    import re

    bulgu: list[Bulgu] = []
    gundem_yolu = _KOK.parent / "site" / "icerik" / "gundem.json"
    if not gundem_yolu.exists():
        return bulgu
    try:
        g = json.loads(gundem_yolu.read_text(encoding="utf-8"))["haberler"]
    except Exception:
        return bulgu
    say = [x for x in g if x.get("yorumlanir")]

    # --- gorsel tekrari ---
    #
    # YANLIS SEYI OLCUYORDU. Sayim `gundem.json`dan yapiliyordu: 34
    # haber. Okurun gordugu ise 313 URETILEN SAYFA -- arsiv dahil. Ustelik
    # `gundem.json` fotografi haberin ILK secimini tasiyor; asil atama
    # insa sirasinda, varliklar bilindikten sonra yapiliyor. Yani denetim
    # yayimlanmayan bir secimi olcuyordu.
    #
    # Esik de anlamsizdi: 313 sayfa ve on fotograflik havuzla sekiz
    # tekrar YAPISALDIR, hata degil. Onemli olan iki sey:
    #   1. ANA SAYFADA ayni gorsel iki kez cikmasin -- okurun tek bakista
    #      gordugu yer burasi.
    #   2. Dagitim DENGELI olsun. Dengesizlik havuzun darligini degil
    #      `foto_dagit`in bozuldugunu gosterir; olculdu, bozuk halinde
    #      dagilim 9/4/3/3 iken duzgun halinde 22/22/21/21.
    bulgu += _gorsel_denetimi()
    bulgu += _veri_tutarlilik_denetimi()
    bulgu += _lisans_denetimi()
    bulgu += _uretilen_gorsel_denetimi()
    bulgu += _serit_cakismasi_denetimi()
    bulgu += _cop_denetimi()
    bulgu += _foto_butunluk_denetimi()
    bulgu += _kanonik_adres_denetimi()
    bulgu += _tasarim_jetonu_denetimi()
    bulgu += _baslik_tekrari_denetimi()

    # --- yayimlanmis gurultu ---
    #
    # Suzgec BESLEME aninda calisiyor; bir kalip sonradan eklenirse
    # daha once girmis ogeler kendiliginden cikmiyor. Olculdu: gurultu
    # listesine "taziye" ve urun tanitimi kaliplari eklendikten sonra
    # ALTI sayfa hala ayaktaydi -- silahli saldiri, taziye mesaji,
    # market indirim katalogu.
    #
    # Uyari, hata degil: `gurultu_mu` yanlis pozitif verirse gercek bir
    # haberi otomatik silmek, gurultuyu yayimlamaktan kotudur. Karar
    # insanda kaliyor.
    try:
        sys.path.insert(0, str(_KOK / "kaynak"))
        import besleme  # noqa: PLC0415

        # GIRDIYI DEGIL, YAYIMLANAN SAYFAYI OLCUYORUZ.
        #
        # `say` listesi `gundem.json`dan, yani GIRDIDEN geliyor.
        # Suzgec artik insa aninda da kosuyor (bkz. `insa.tazele`) --
        # yani bir oge girdide "yorumlanir" gorunurken SAYFASI HIC
        # URETILMEMIS olabilir. Olculdu: sivil kayip haberi girdide
        # duruyordu, sayfasi kaldirilmisti, denetim yine de uyariyordu.
        # Var olmayan bir sayfa icin uyarmak, uyariyi degersizlestirir.
        #
        # Basliklar insa aninda kisalabildigi icin (bkz.
        # `bicim.manset_kisalt`) tam esitlik aranmiyor: yayimlanan
        # baslik, ozgun basligin ONEKIDIR.
        yayimlanan: list[str] = []
        if CIKTI_DIZINI.exists():
            for p in (CIKTI_DIZINI / "haber").glob("*/index.html"):
                m = re.search(r"<h1[^>]*>(.*?)</h1>",
                              p.read_text(encoding="utf-8"), re.S)
                if m:
                    yayimlanan.append(" ".join(
                        html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).split()))

        def sayfasi_var(baslik: str) -> bool:
            if not CIKTI_DIZINI.exists():
                return True          # cikti yoksa olcemeyiz, susmayalim
            return any(b and baslik.startswith(b[:60]) for b in yayimlanan)

        kirli = [x for x in say
                 if besleme.gurultu_mu(x.get("baslik", ""))
                 and sayfasi_var(x.get("baslik", ""))]
        for x in kirli[:5]:
            bulgu.append(Bulgu(
                "uyari", "editoryal", "gurultu",
                f"ekonomi disi oge yayimlanmis: {x.get('baslik', '')[:56]}"))
        if len(kirli) > 5:
            bulgu.append(Bulgu("uyari", "editoryal", "gurultu",
                               f"...ve {len(kirli) - 5} tane daha"))
    except Exception:                                  # noqa: BLE001
        pass

    # --- son dakika disiplini ---
    kritik = [x for x in say if x.get("katman") == "kritik"]
    if len(kritik) > len(say) * 0.25 and len(say) > 8:
        bulgu.append(Bulgu(
            "hata", "sondakika", "-",
            f"{len(kritik)}/{len(say)} haber KRITIK -- etiket her seye "
            f"yapisinca hicbir seye yapismaz"))

    # --- ayni baslik birden fazla bolumde ---
    if CIKTI_DIZINI.exists():
        tekrarli = 0
        for s in (CIKTI_DIZINI / "haber").glob("*/index.html"):
            metin = s.read_text(encoding="utf-8")
            seyir = {x.strip() for x in re.findall(
                r'seyir-baslik"[^>]*>(?:<b>)?([^<]{10,})', metin)}
            devam: set = set()
            for d in re.findall(r"(?s)<section class=\"devam\">.*?</section>",
                                metin):
                devam |= {x.strip() for x in re.findall(
                    r'<a href="[^"]*">([^<]{10,})</a>', d)}
            if seyir & devam:
                tekrarli += 1
        if tekrarli:
            bulgu.append(Bulgu(
                "uyari", "tekrar", "-",
                f"{tekrarli} sayfada ayni baslik hem seyir hem 'bunu da "
                f"okuyun' bolumunde"))
    return bulgu


#: Ayni blokta iki kez tanimli olduğu BILINEN ve bilerek birakilan
#: seciciler. Aralarinda ayni ogeyi hedefleyen baska kural var; tek
#: kurala indirmek siralamayi -- dolayisiyla gorunumu -- degistirebilir.
#: Yeni bir cift cikarsa uyari verilir; asil is odur.
BILINEN_CIFT = {
    ".one-cikan", ".foto-atif", ".yazi-foto img", ".ozet-kutu dd",
    ".senaryo-cagri", ".ilgili-haber",
}


def cakisan_bildirimler(
        bloklar: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    """Ayni secicinin tanimlari arasinda GERCEKTEN carpisanlari verir.

    Ayni seciciyi iki kez yazmak tek basina hata degil: farkli
    ozellikler yaziyorlarsa birlesirler. Hata, AYNI ozelligin farkli
    degerle iki kez yazilmasi -- o zaman sonraki kazanir ve onceki OLU
    koddur. Tehlikesi de burada: olu blogu duzenleyen biri hicbir sey
    degismedigini gorur.

    AYRI FONKSIYON OLMASI BILEREK. Kural su an gercek `stil.css`te HIC
    ateslemiyor (olculdu 2026-08-28: 39 tekrarli secici, 0 carpisma).
    Yalnizca gercek dosyaya bakan bir sinama, kural tumuyle bozulsa
    bile yesil donerdi -- bu oturumda "hicbir sey olcmeyen test"
    tuzagina defalarca dusuldu. Buradan kurgu girdiyle sinaniyor.
    """
    carpisan: dict[str, tuple[str, str]] = {}
    for a in range(len(bloklar)):
        for b in range(a + 1, len(bloklar)):
            for oz in set(bloklar[a]) & set(bloklar[b]):
                onceki, sonraki = bloklar[a][oz], bloklar[b][oz]
                if onceki == sonraki:
                    continue
                # `!important` SIRAYI TERSINE CEVIRIR: oncekinde varsa
                # ve sonrakinde yoksa KAZANAN oncekidir, yani "onceki
                # olu" demek YANLIS olurdu.
                if "!important" in onceki and "!important" not in sonraki:
                    continue
                carpisan[oz] = (onceki, sonraki)
    return carpisan

#: CSS'te tanimli ama su anki gundemde UretILMEYEN siniflar. Silinmemeli:
#: uretilebilir olduklari olculdu, yalnizca bugun o deger gelmedi.
URETILEBILIR = {
    # `class="tur-{{ h|kart_turu }}"` -- gecerli kume KART_TURU.values().
    #
    # AILENIN TAMAMI yaziliyor, bugun basilmayanlar degil. Uyelik
    # KODLA belirleniyor, o gunun gundemiyle degil: ilk yazimda yalnizca
    # o an eksik olan ikisini ("haber", "duzenleme") beyaz listeye
    # almistim ve ertesi gun "sektor" konusundan haber dusmeyince
    # denetim onu da bildirdi. Liste veriye gore degil kaynaga gore
    # olmali, yoksa her gun baska bir uye uyari uretir.
    "tur-makro", "tur-jeopolitik", "tur-emtia", "tur-piyasa",
    "tur-sirket", "tur-duzenleme", "tur-sektor", "tur-haber",
    # TAKVIM_ONEM_ESIGI=2 suzuyor; esik bir ayar
    "onem-1", "onem-2", "onem-3",
}


#: CSS kurali OLMAYAN ama bilerek basilan siniflar. Her biri incelendi;
#: gerekcesi yaninda. Beyaz listeye alinmasalar her koşuda ayni sekiz
#: satiri tekrarlarlardi ve okunmayan bir uyari uyari degildir.
KANCA = {
    "masa-ana": "iki sutunlu `.masa` gridinin ilk cocugu; sutun tanimi yeter",
    "masa-akis": "",
    "ust-panel": "ust seridin anlamsal kabi; gorunumu `.ust` veriyor",
    "varlik-sayfa": "sayfa turu isareti",
    "haber-yorumlu": "AI yorumu olan haberin isareti",
    "bolum-baglanti": "bolum basligindaki baglanti; yalin `a` bicimi yeter",
    "kivilcim": "SVG'nin kendi adi; boyut ebeveynden, renk yon sinifindan",
    # Bu ikisi RENKSIZ birakildi. Yesil/kirmizi vermek "yukari iyi,
    # asagi kotu" diye okunur ve bu bir yargi olurdu -- dallar konumla
    # ayriliyor. Isim, ileride kapsamli bir kural gerekirse dursun diye.
    "takvim-dal-ustunde": "bilerek renksiz -- yargi bildirmemek icin",
    "takvim-dal-altinda": "bilerek renksiz -- yargi bildirmemek icin",
}


def stil_denetimi() -> list[Bulgu]:
    """Stil dosyasinin cakisma ve olu kural denetimi.

    Uc tuzak da bu oturumda GERCEKTEN yasandi:

    1. AYNI ADI IKI FARKLI SEYE VERMEK. `.devam` "Devamını oku"
       baglantisiydi; makale sonu bolumune de ayni ad verilince her
       baglantinin ustunde cift cizgi cikti. `.seyir` de 13 aylik sutun
       grafiginin kabiydi. Cakisma, ayni seciciyi iki kez tanimli
       gormekten anlasildi -- denetlenen olcut bu.

    2. OLU KURAL. Kaldirilmis ozelliklerin (piyasa paneli, TR/DUNYA
       sekmeleri, editoryal durum rozetleri) kurallari dosyada kaldi:
       63 kural. Isim havuzunu kirletiyor, yani (1)'i kolaylastiriyor.

    3. YANLIS OLU TESPITI. `tur-makro` gibi adlar sablonda
       BIRLESTIRILEREK uretiliyor (`tur-{{ h|kart_turu }}`), kaynakta
       duz metin olarak gecmiyor. Ilk taramada 20 canli sinifi olu
       sandim. Bu yuzden burada silme YOK -- yalnizca bildirim.
    """
    import collections
    import re

    css_yolu = _KOK.parent / "site" / "statik" / "stil.css"
    if not css_yolu.exists():
        return []
    ham = css_yolu.read_text(encoding="utf-8")
    # Yorumu BOSLUKLA doldur: uzunluk ve satir korunmali.
    c = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group()),
               ham, flags=re.S)

    def _bildirimler(govde: str) -> dict[str, str]:
        """`ozellik: deger` ciftlerini cikarir."""
        cikti: dict[str, str] = {}
        for parca in govde.split(";"):
            if ":" not in parca:
                continue
            ad, _, deger = parca.partition(":")
            cikti[ad.strip()] = " ".join(deger.split())
        return cikti

    kurallar: list[tuple[str, str]] = []          # (baglam, secici)
    #: (baglam, secici) -> her tanimin bildirimleri, KAYNAK SIRASINDA.
    govdeler: dict[tuple[str, str], list[dict[str, str]]] = {}
    baglam = ""
    d = i = sb = 0
    while i < len(c):
        if c[i] == "{":
            s = " ".join(c[sb:i].split())
            if s.startswith("@"):
                baglam, d, sb = s, d + 1, i + 1
            else:
                k, dd = i, 0
                while k < len(c):
                    if c[k] == "{":
                        dd += 1
                    elif c[k] == "}":
                        dd -= 1
                        if dd == 0:
                            break
                    k += 1
                kurallar.append((baglam, s))
                govdeler.setdefault((baglam, s), []).append(
                    _bildirimler(c[i + 1:k]))
                i = sb = k + 1
                continue
        elif c[i] == "}":
            d -= 1
            if d <= 0:
                d, baglam = 0, ""
            sb = i + 1
        i += 1

    # YALNIZCA GERCEK CAKISMA BILDIRILIYOR.
    #
    # Once ayni secicinin iki kez gecmesi tek basina uyari sayiliyordu.
    # Olculdu (2026-08-28): dosyada 106 tekrarli secici var ve 83'u
    # ZARARSIZ -- farkli ozellikler yaziyorlar, birlesiyorlar. Yani
    # uyarilarin dortte ucu eylem gerektirmiyordu.
    #
    # Sonucu, kuralin islevsiz kalmasi: ayirt etmeyen bir uyari yigini
    # icinde gercek olan da goze carpmiyor ve kimse hicbirine bakmiyor.
    # Bu depoda oyle oldu; 35 uyari haftalarca durdu.
    #
    # Olcut artik AYNI OZELLIGIN FARKLI DEGERLE yazilmasi. O zaman
    # sonraki kazanir ve onceki OLU koddur -- tehlikesi de burada:
    # olu blogu duzenleyen biri hicbir sey degismedigini gorur.
    bulgu: list[Bulgu] = []
    for (bg, sec), bloklar in govdeler.items():
        if len(bloklar) < 2 or sec in BILINEN_CIFT:
            continue
        carpisan = cakisan_bildirimler(bloklar)
        if not carpisan:
            continue
        adlar = ", ".join(sorted(carpisan)[:3])
        if len(carpisan) > 3:
            adlar += f" (+{len(carpisan) - 3})"
        bulgu.append(Bulgu(
            "uyari", "stil", sec[:40],
            f"{len(bloklar)} kez tanimli"
            f"{' (' + bg[:30] + ')' if bg else ''}"
            f" -- ayni ozellik farkli degerle: {adlar};"
            " oncekiler OLU"))

    tanimli = {a for _, s in kurallar
               for a in re.findall(r"\.([a-zA-Z][\w-]*)", s)}
    cikti = _KOK.parent / "site" / "cikti"
    if not cikti.exists():
        return bulgu
    uretilen: set[str] = set()
    for f in cikti.rglob("*.html"):
        for x in re.findall(r'class="([^"{}]+)"',
                            f.read_text(encoding="utf-8", errors="ignore")):
            uretilen |= set(x.split())

    # Sayfada var ama CSS'te yok: yazim hatasi ya da yeniden
    # adlandirmada unutulan sablon. `.devam` -> `.okumaya-devam`
    # gecisinde sablonun biri geride kalsaydi burada gorunurdu.
    for a in sorted(uretilen - tanimli - set(KANCA) - {"js", "hidden"}):
        if "-" in a or len(a) > 6:            # yardimci kisa adlari ele
            bulgu.append(Bulgu("uyari", "stil", a,
                               "sayfalarda kullaniliyor ama CSS'te tanimsiz"))
    # KAYNAK AGACI SUZGECI. "Sayfada yok" tek basina olu demek degil:
    # `akiyor`/`durdu` betigin ekledigi sinif, `ara-kart` yalnizca arama
    # sonucunda cikiyor. Suzgecsiz hali 56 sinif bildiriyordu ve boyle
    # bir liste okunmaz -- dogru iceriği isaretleyen denetim, denetimin
    # kendisini degersizlestirir.
    kaynak = []
    for dizin in ("site/sablonlar", "site", "haber_botu"):
        d = _KOK.parent / dizin
        if not d.exists():
            continue
        kaynak += [f.read_text(encoding="utf-8", errors="ignore")
                   for f in d.rglob("*")
                   if f.suffix in {".html", ".py", ".js"}
                   and "cikti" not in f.parts]
    metin = "\n".join(kaynak)
    olu = sorted(a for a in tanimli - uretilen - URETILEBILIR
                 if a not in metin)
    if olu:
        bulgu.append(Bulgu(
            "uyari", "stil", f"{len(olu)} sinif",
            "CSS'te tanimli, hicbir sayfada yok: " + ", ".join(olu[:8])))
    return bulgu


# --------------------------------------------------------------------
# SINIFLANDIRMA VE YAYIN KARARI  (yayin yonetmeni promptu, 15/19/20)
# --------------------------------------------------------------------
#
# Bulgular zaten toplaniyordu ama tek ayrim "hata / uyari" idi. Prompt
# yedi sinif istiyor ve sebebi su: "yanlis kurum adi" ile "ayni gorsel
# iki kez" ayni siddette degil ve ayni kisiye de gitmiyor. Sinif,
# bulguyu KIMIN duzeltecegini de soyluyor.
#
# Sinif ALANDAN turetiliyor; alan zaten her bulguda var. Boylece yeni
# bir denetim eklerken ayrica sinif yazmak gerekmiyor -- unutulacak bir
# alan daha olmuyor.
SINIFLAR: dict[str, tuple[str, str]] = {
    "etiket":    ("🔴", "KRITIK"),      # yanlis kurum/kavram adi
    "aralik":    ("🟡", "VERI"),
    "birim":     ("🟡", "VERI"),
    "tazelik":   ("🟡", "VERI"),
    "veri":      ("🟡", "VERI"),
    "ai":        ("🟠", "AI"),
    "gorsel":    ("🟣", "GORSEL"),
    "editoryal": ("🔵", "EDITORYAL"),
    "stil":      ("🔵", "EDITORYAL"),
    "tekrar":    ("⚪", "TEKRAR"),
}

#: Ciktida gorunecek bolum sirasi -- promptun 20. maddesindeki sira.
RAPOR_ALANLARI = (
    ("KAYNAK", ("tazelik",), "Uygun", "Sorunlu"),
    ("BASLIK", ("editoryal",), "Uygun", "Duzeltilmeli"),
    ("GORSEL", ("gorsel",), "Uygun", "Degistirilmeli"),
    ("AI YORUMU", ("ai",), "Uygun", "Hatali"),
    ("VERILER", ("etiket", "aralik", "birim", "veri"), "Uygun", "Hatali"),
    ("TEKRARLAR", ("tekrar",), "Yok", "Var"),
    # PROMPTUN LISTESINDE YOK, EKLENDI. Prompt icerik incelemesi icin
    # yazilmis; stil bulgulari (olu/tanimsiz CSS sinifi) icerik degil
    # sayfa yapisi. Bir bolume dusmezlerse bulgu URETILIR ama ozette
    # GORUNMEZ -- test bunu yakaladi.
    ("SAYFA YAPISI", ("stil",), "Uygun", "Kontrol edilmeli"),
)


def sinif(b: Bulgu) -> str:
    """Bulgunun sinif simgesi. Bilinmeyen alan UYARI sayilir."""
    simge, _ad = SINIFLAR.get(b.alan, ("🔵", "EDITORYAL"))
    # Ayni alandaki bir bulgu HATA agirligindaysa kritik isaretlenir:
    # "bayat veri" uyaridir, "imkansiz deger" degildir.
    if b.agirlik == "hata" and simge in ("🟡", "🔵", "⚪"):
        return "🔴"
    return simge


def yayin_karari(hata: list, uyari: list) -> tuple[str, str]:
    """Promptun 19. maddesi -- uc seviye."""
    if hata:
        return "🔴", "YAYINA UYGUN DEGIL"
    if uyari:
        return "🟡", "DUZELTILDIKTEN SONRA YAYINLANABILIR"
    return "🟢", "YAYINA HAZIR"


def _rapor_yaz(bulgular: list, hata: list, uyari: list) -> None:
    """Promptun 20. maddesindeki cikti bicimi."""
    simge, karar = yayin_karari(hata, uyari)
    alanlar = {b.alan for b in bulgular}

    print()
    print("-" * 70)
    print(f"  GENEL DURUM: {simge}")
    for ad, kodlar, iyi, kotu in RAPOR_ALANLARI:
        var = alanlar & set(kodlar)
        print(f"  {ad + ':':<14}{kotu if var else iyi}")
    print(f"  {'BULGU:':<14}{len(hata)} hata, {len(uyari)} uyari")

    if bulgular:
        sayim: dict[str, int] = {}
        for b in bulgular:
            s = sinif(b)
            sayim[s] = sayim.get(s, 0) + 1
        print("  SINIFLAR:     " + "  ".join(
            f"{k} {v}" for k, v in sorted(sayim.items())))

    print(f"  YAYIN KARARI: {simge} {karar}")
    print("-" * 70)


def calistir(sessiz: bool = False) -> int:
    bulgular: list[Bulgu] = []
    bulgular += etiket_denetimi()
    bulgular += birim_denetimi()
    with beyin.baglan() as b:
        bulgular += aralik_denetimi(b)
        bulgular += tazelik_denetimi(b)
    bulgular += cikti_denetimi()
    bulgular += editoryal_denetim()
    bulgular += stil_denetimi()

    hata = [x for x in bulgular if x.agirlik == "hata"]
    uyari = [x for x in bulgular if x.agirlik == "uyari"]

    # CIKTI KONSOLUN KALDIRABILECEGI BICIMDE.
    #
    # OLCULDU: `denetim.py` bulgu yazdirirken COKUYORDU --
    #   UnicodeEncodeError: 'charmap' codec can't encode '🟣'
    # Windows konsolu cp1254 ve simgeler (🔴 🟡 🟣) o kod sayfasinda
    # yok. Yani denetim, TAM SOYLEYECEK BIR SEYI OLDUGUNDA kiriliyordu;
    # bulgusuz kosularda sorunsuz gorunuyor, bulgu cikinca susuyordu.
    #
    # Bir hata bildiricisinin kendisi kirilirsa, bildirmesi gereken sey
    # bir daha teshis edilemez. CI'da (UTF-8) gorunmuyordu; yalnizca
    # yerelde ve tam da bakmak istendigi anda.
    def _yaz(metin: str) -> None:
        kod = getattr(sys.stdout, "encoding", None) or "utf-8"
        try:
            print(metin)
        except UnicodeEncodeError:
            print(metin.encode(kod, "replace").decode(kod, "replace"))

    if not sessiz:
        _yaz("=" * 70)
        _yaz("  VERI DENETIMI")
        _yaz("=" * 70)
    for x in hata:
        _yaz(f"  {sinif(x)}  [{x.alan}] {x.kod}: {x.mesaj}")
    if not sessiz:
        for x in uyari:
            _yaz(f"  {sinif(x)}  [{x.alan}] {x.kod}: {x.mesaj}")
        _rapor_yaz(bulgular, hata, uyari)

    # UYARI ISI DUSURMUYOR, HATA DUSURUYOR.
    # Bayat veri kaynagin gecikmesi olabilir ve site yine kurulmali;
    # yanlis etiket ya da imkansiz deger ise yayimlanmamali.
    return 1 if hata else 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Yayimlanan verinin denetimi")
    a.add_argument("--sessiz", action="store_true",
                   help="yalnizca hatalari yaz")
    sys.exit(calistir(a.parse_args().sessiz))
