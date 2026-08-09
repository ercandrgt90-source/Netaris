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
import pathlib
import sys
from dataclasses import dataclass

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


def _gorsel_denetimi() -> list[Bulgu]:
    """Yayimlanan sayfalardaki gorsel kullanimini denetler."""
    import collections
    import json
    import re

    bulgu: list[Bulgu] = []
    if not CIKTI_DIZINI.exists():
        return bulgu

    # 1. ANA SAYFA -- ayni gorsel iki kart
    ana = CIKTI_DIZINI / "index.html"
    if ana.exists():
        kartlar = re.findall(r'src="(/statik/foto/[^"]+)"',
                             ana.read_text(encoding="utf-8"))
        for yol, n in collections.Counter(kartlar).items():
            if n > 1:
                bulgu.append(Bulgu(
                    "uyari", "gorsel", yol.split("/")[-1],
                    f"ana sayfada {n} kez -- okur tek bakista goruyor"))

    # 2. HABER SAYFALARI -- havuz ici denge
    kullanim: collections.Counter = collections.Counter()
    sayfasiz = 0
    haber_dizini = CIKTI_DIZINI / "haber"
    if haber_dizini.exists():
        for p in haber_dizini.iterdir():
            s = p / "index.html"
            if not s.exists():
                continue
            m = re.search(r'src="(/statik/foto/[^"]+)"',
                          s.read_text(encoding="utf-8"))
            if m:
                kullanim[m.group(1)] += 1
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
    for havuz, liste in kayit.items():
        yollar = [f["dosya"] for f in liste]
        kullanilan = [kullanim.get(y, 0) for y in yollar]
        # Havuzdan HIC kullanilmayan varsa o havuz o gun devrede degil;
        # kismen kullanilan havuzda denge aranir.
        etkin = [n for n in kullanilan if n]
        if len(etkin) < 2:
            continue
        # TOLERANS 2. Atama sayaci, sayfasi sonradan uretilmeyen birkac
        # adayi da sayiyor; bu yuzden mukemmel dagilimda bile bir-iki
        # birim sapma normal. Olculdu: 36 haber / 4 gorsel dagitimi
        # 9-10-8-9 cikti, kusursuzu 9-9-9-9. Esigi 1'de tutmak bu dogru
        # dagitimi hata diye isaretliyordu.
        #
        # Yakalamasi gereken sey bu degil: bozuk dagitimda ayni olcum
        # 9-4-3-3 idi, yani fark 6.
        if max(etkin) - min(kullanilan) > 2:
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

        kirli = [x for x in say if besleme.gurultu_mu(x.get("baslik", ""))]
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

    kurallar: list[tuple[str, str]] = []          # (baglam, secici)
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
                i = sb = k + 1
                continue
        elif c[i] == "}":
            d -= 1
            if d <= 0:
                d, baglam = 0, ""
            sb = i + 1
        i += 1

    bulgu: list[Bulgu] = []
    for (bg, sec), n in collections.Counter(kurallar).items():
        if n > 1 and sec not in BILINEN_CIFT:
            bulgu.append(Bulgu(
                "uyari", "stil", sec[:40],
                f"ayni blokta {n} kez tanimli"
                f"{' (' + bg[:30] + ')' if bg else ''}"
                " -- hangisi kazandigi belirsiz, cakisma olabilir"))

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

    if not sessiz:
        print("=" * 70)
        print("  VERI DENETIMI")
        print("=" * 70)
    for x in hata:
        print(f"  HATA  [{x.alan}] {x.kod}: {x.mesaj}")
    if not sessiz:
        for x in uyari:
            print(f"  uyari [{x.alan}] {x.kod}: {x.mesaj}")
        print(f"\n  {len(hata)} hata, {len(uyari)} uyari")

    # UYARI ISI DUSURMUYOR, HATA DUSURUYOR.
    # Bayat veri kaynagin gecikmesi olabilir ve site yine kurulmali;
    # yanlis etiket ya da imkansiz deger ise yayimlanmamali.
    return 1 if hata else 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Yayimlanan verinin denetimi")
    a.add_argument("--sessiz", action="store_true",
                   help="yalnizca hatalari yaz")
    sys.exit(calistir(a.parse_args().sessiz))
