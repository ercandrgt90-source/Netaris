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
    foto = collections.Counter(x.get("foto", "") for x in say if x.get("foto"))
    for yol, n in foto.most_common():
        if n >= FOTO_TEKRAR_ESIGI:
            bulgu.append(Bulgu(
                "uyari", "gorsel", yol.split("/")[-1],
                f"{n} haberde ayni fotograf -- konu havuzu dar"))
    eksik = sum(1 for x in say if not x.get("foto"))
    if eksik:
        bulgu.append(Bulgu("uyari", "gorsel", "-",
                           f"{eksik} sayfali haberde fotograf yok"))

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


def calistir(sessiz: bool = False) -> int:
    bulgular: list[Bulgu] = []
    bulgular += etiket_denetimi()
    bulgular += birim_denetimi()
    with beyin.baglan() as b:
        bulgular += aralik_denetimi(b)
        bulgular += tazelik_denetimi(b)
    bulgular += cikti_denetimi()
    bulgular += editoryal_denetim()

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
