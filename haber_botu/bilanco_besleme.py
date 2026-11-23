"""Bilanco verisini BESLEMEYE cevirir -- AI beklemeden, agsiz.

NEDEN VAR
---------
Bilanco rakamlari bugune kadar yalnizca MARKDOWN SAYFASINDA
yayimlaniyordu ve o sayfa bir AI yorumuna bagli: yorum uretilemezse
sayfa hic yazilmiyor (`uret_bilanco_sayfa` -> "YORUMSUZ SAYFA
YAYIMLANMIYOR"). Yani rakam elimizdeyken okur onu goremiyordu.

OLCULDU (2026-11-22):
    ozette olculmus sirket              384
    2026 3. ceyrek sayfasi olan         341
    mobil uygulamada bilanco ekrani       0   (besleme hic yok)

Yani 43 sirketin RRAKAMI VAR, sayfasi yok; mobil tarafta ise 384'un
tamami gorunmez. "Veri var, bag yok" -- bu depoda yazili bir kusur
sinifi ve olcutu URETILEN CIKTIDA SAYMAK.

Bu modul rakami yorumdan AYIRIYOR: olcum tamamlandigi an besleme
uretilebiliyor. Yorum geldiginde sayfa da yayimlaniyor ve besleme
ona `sayfa` alaniyla baglaniyor.

NE HESAPLAMIYOR
---------------
Hicbir oran, hicbir degisim BURADA hesaplanmiyor:

    seviyeler       `bilanco_ag.donemi_kur` + `oranlar.Donem`
    oranlar         `uret_bilanco._oranlari`
    degisim yuzdesi `oranlar._yuzde_degisim`
    kalem adlari    `uret_bilanco_sayfa.KALEMLER`
    oran adlari     `sektor_ozet.ORANLAR`
    medyan          `sektor_ozet.json` (kesitsel, burada uretilemez)

Sebep tek cumle: bu depoda ayni degisim hesabi DORT kopyaya cikti ve
biri duzeltilince oteki uc sessizce ayristi. Besleme besinci kopya
olmayacak.

VERI NEREDEN
------------
Iki katman, ikisi de agsiz:

    `sektor_ozet.json`   384 sirketin tamami -- donem, sektor, oranlar
    `bilanco_defteri`    cekilmis sirketler  -- TL seviyeleri, seri,
                                               onceki yil

Defter kaydi olmayan sirket beslemeden DUSMUYOR: oranlari ve donemi
yine yayimlaniyor, yalnizca `derinlik` alani "ozet" diyor. Yoklugu
gizlemek, okura eksik veriyi tam gibi gostermek olurdu.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
for _y in (str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import bicim               # noqa: E402
import bilanco_ag          # noqa: E402
import bilanco_defteri     # noqa: E402
import oranlar             # noqa: E402
import sektor_ozet         # noqa: E402

#: Oran -> birim. `sektor_ozet.ORANLAR` adlari veriyor, birimi
#: vermiyor; marj yuzde, cari oran ise KAT (1,38x).
#:
#: Yuzde isaretini kat cinsinden bir orana koymak okura "%1,38"
#: gosterir ve bu, gercek degerin yuzde biri demek. Bu yuzden birim
#: ADLA AYNI yerden degil, burada ve ACIKCA tanimli; `test_bilanco_
#: besleme.py` `sektor_ozet.ORANLAR`daki her anahtarin burada
#: karsiligi oldugunu sinamali -- yeni bir oran eklenirse birimi
#: unutulmasin.
ORAN_BIRIMI = {
    "brut_marj": "%",
    "net_marj": "%",
    "roe": "%",
    "cari_oran": "kat",
    "borc_ozkaynak": "kat",
}

#: Egilim serisinde tasinan alanlar.
#:
#: HEPSI GELIR TABLOSU AKISI. Bilanco kalemi (aktif toplami,
#: ozkaynak) bir ANIN stogu ve ardisik donemlerde kiyaslanmasi
#: anlamli ama okurun sordugu soru degil: "son ceyreklerde is nasil
#: gitti". Bes alan telefon genisliginde okunabilir bir cizim
#: veriyor; on alan okunamaz bir tablo verirdi.
SERI_ALANLARI = ("hasilat", "brut_kar", "faaliyet_kari", "favok", "net_kar")


def _kalemler():
    """Seviye tablosunun alan/ad cifti -- SAYFAYI KURAN SABITTEN.

    TEMBEL ICERI ALMA BILINCLI: `uret_bilanco_sayfa` icinde AI
    saglayici zincirini ceken `bilanco_yorum` da var. `insa.py` bu
    modulu her kosuda iceri aliyor; site insasinin AI zincirine
    bagimli hale gelmesi, bagimsiz olmasi gereken iki seyi
    birbirine baglamak olurdu.
    """
    import uret_bilanco_sayfa                        # noqa: PLC0415
    return uret_bilanco_sayfa.KALEMLER


def _oranlari(d):
    """`Donem` -> oran sozlugu. Hesap `uret_bilanco`da, burada DEGIL."""
    import uret_bilanco                              # noqa: PLC0415
    return uret_bilanco._oranlari(d)


def _mlr(d):
    """TL seviyesini okunabilir metne cevirir -- SAYFAYI BASAN ISLEVLE.

    BICIMLENDIRME BESLEMEDE YAPILIYOR, UYGULAMADA DEGIL.
    -----------------------------------------------------
    Alternatif, ham sayiyi gonderip uygulamada bicimlendirmekti. O
    zaman "474,39 milyar TL" karari IKI yerde verilirdi: Python'da
    (site) ve TypeScript'te (uygulama). Bu depoda ayni sinif
    defalarca yasandi -- iki yer zamanla ayrisiyor ve ayrisma hicbir
    hata uretmiyor, yalnizca ayni sirket iki yuzeyde iki farkli sayi
    gosteriyor.

    Varlik beslemesi de tam bu sebeple `deger` ve `birim` alanlarini
    HAZIR METIN olarak tasiyor.

    HAM SAYI DA GONDERILIYOR: cizim ve siralama icin gerekli. Metin
    gosterim, sayi hesap icin.
    """
    import uret_bilanco_sayfa                        # noqa: PLC0415
    return uret_bilanco_sayfa._mlr(d)


def _oran_metni(deger, birim: str) -> str:
    """Orani birimine gore bicimlendirir. `bicim`den, elle DEGIL."""
    if deger is None:
        return ""
    if birim == "%":
        return bicim.yuzde(deger)
    if birim == "kat":
        return bicim.kat(deger)
    return bicim.sayi(deger, 2)


def _sayi(x):
    """JSON'a yazilabilir sayi ya da None. NaN/sonsuz DISARIDA."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def sirket_kaydi(kod: str, bilgi: dict, sektor_kaydi: dict,
                 sayfa: str = "", defter=None,
                 slug: str = "") -> dict | None:
    """Bir sirketin besleme kaydi. Ozet kaydi yoksa None.

    `defter` DEFTER KAYDININ TAMAMI (`bilanco_defteri.oku_kayit`
    ciktisi), yalnizca `tablolar` degil: kaydin `bitis` ve `cekildi`
    alanlari da yayimlaniyor. Ikinci bir dosya okumasiyla almak,
    gecerlilik denetiminden GECMEMIS bir kaydi okumak olurdu.

    Verilmezse kayit yine donuyor -- oranlar ve donem ozetten
    geliyor, yalnizca `derinlik` alani "ozet" diyor.
    """
    kod = str(kod or "").upper()
    if not kod:
        return None
    oran = ((sektor_kaydi.get("sirket") or {}).get(kod)) or {}
    bitis = ((sektor_kaydi.get("bitis") or {}).get(kod)) or ""
    donem = str(sektor_kaydi.get("donem") or "")
    medyan = sektor_kaydi.get("medyan") or {}

    kayit: dict = {
        "kod": kod,
        "unvan": str(bilgi.get("unvan") or ""),
        "sektor": str(sektor_kaydi.get("sektor")
                      or bilgi.get("sektor_tr") or ""),
        "alt_sektor": str(bilgi.get("alt_sektor") or ""),
        "donem": donem,
        "donem_bitis": bitis,
        "sektor_sirket_sayisi": int(sektor_kaydi.get("sirket_sayisi") or 0),
        "sayfa": sayfa or None,
        # UYGULAMANIN KENDI YOLU ICIN SLUG.
        #
        # `sayfa` SITENIN adresi ("/analiz/<slug>/", sondaki egik
        # cizgiyle). Uygulama yonlendiricisi "/analiz/[slug]"
        # bekliyor; adresi orada kirpmak, site adres duzenini
        # TypeScript tarafina kopyalamak olurdu ve duzen degistigi
        # gun bag sessizce kirilirdi.
        "sayfa_slug": slug or None,
        "derinlik": "ozet",
        "guncellendi": str(sektor_kaydi.get("tazelendi") or ""),
        "oranlar": [],
        "olcumler": [],
        "seri": [],
    }

    # ORANLAR -- ADLARI VE SIRASI `sektor_ozet.ORANLAR`DAN.
    for _ad_k, _ad in sektor_ozet.ORANLAR:
        _d = _sayi(oran.get(_ad_k))
        if _d is None:
            continue
        kayit["oranlar"].append({
            "alan": _ad_k,
            "ad": _ad,
            "deger": _d,
            "deger_metin": _oran_metni(_d, ORAN_BIRIMI.get(_ad_k, "")),
            "birim": ORAN_BIRIMI.get(_ad_k, ""),
            "medyan_metin": _oran_metni(_sayi(medyan.get(_ad_k)),
                                        ORAN_BIRIMI.get(_ad_k, "")),
            # MEDYAN YOKSA ALAN None -- sifir DEGIL. Sifir bir
            # olcumdur; yokluk olcumsuzluktur ve ikisini ayni
            # gostermek okura yanlis kiyas verir.
            "medyan": _sayi(medyan.get(_ad_k)),
        })

    if not defter:
        return kayit
    _tablolar = (defter or {}).get("tablolar")
    if not isinstance(_tablolar, dict) or not _tablolar:
        return kayit

    # ---- DEFTER KATMANI: TL SEVIYELERI, DEGISIM, SERI ----
    try:
        simdi, once, _eksik, seri = bilanco_ag.donem_getir(
            kod, donem or "dönem", sektor_tr=kayit["sektor"],
            ciftli=True, seri=True, tablolar=_tablolar)
    except (TypeError, ValueError, KeyError):
        return kayit
    if simdi is None:
        return kayit

    kayit["derinlik"] = "defter"
    for alan, ad in _kalemler():
        _y = _sayi(getattr(simdi, alan, None))
        if _y is None:
            continue
        _e = _sayi(getattr(once, alan, None)) if once is not None else None
        _dg = _sayi(oranlar._yuzde_degisim(_y, _e))
        kayit["olcumler"].append({
            "alan": alan,
            "ad": ad,
            "deger": _y,
            "deger_metin": _mlr(_y),
            "once": _e,
            "once_metin": _mlr(_e) if _e is not None else "",
            # ISARETLI YUZDE: okur artis mi azalis mi oldugunu
            # sayinin kendisinden gormeli ("+%65,7").
            "degisim_metin": (bicim.yuzde(_dg, isaretli=True)
                              if _dg is not None else ""),
            # DEGISIM `oranlar._yuzde_degisim`DEN.
            #
            # O islev isaret degisimini (kardan zarara) REDDEDIYOR:
            # "%1.897,5 geriledi" gibi bir sayi uretilemez. Burada
            # yeniden bolmek, duzeltilen kusuru besinci kez geri
            # getirmek olurdu.
            "degisim": _dg,
        })

    # SIRKETIN KENDI ORANI, KENDI VERISINDEN.
    #
    # Ozetteki oran o sektorun TAZELENDIGI kosudan; defter ise bu
    # sirketin kendi cekiminden. Ikisi ayrilabilir ve sayfa tarafinda
    # tam bu kusur olculdu (258 sayfanin 203'u). Defter varsa oran
    # ONDAN kuruluyor; medyan yine ozetten, cunku o kesitsel.
    _kendi = _oranlari(simdi)
    if _kendi:
        for _o in kayit["oranlar"]:
            if _o["alan"] in _kendi:
                _o["deger"] = _sayi(_kendi[_o["alan"]])
                # METIN DE TAZELENMELI. Degeri guncelleyip metnini
                # birakmak, ayni satirda IKI AYRI SAYI gostermek
                # olurdu -- ve gosterilen, okurun gordugu olurdu.
                _o["deger_metin"] = _oran_metni(_o["deger"], _o["birim"])
        _var = {o["alan"] for o in kayit["oranlar"]}
        for _ad_k, _ad in sektor_ozet.ORANLAR:
            if _ad_k in _kendi and _ad_k not in _var:
                _bd = ORAN_BIRIMI.get(_ad_k, "")
                kayit["oranlar"].append({
                    "alan": _ad_k, "ad": _ad,
                    "deger": _sayi(_kendi[_ad_k]),
                    "deger_metin": _oran_metni(_sayi(_kendi[_ad_k]), _bd),
                    "birim": _bd,
                    "medyan_metin": _oran_metni(_sayi(medyan.get(_ad_k)), _bd),
                    "medyan": _sayi(medyan.get(_ad_k)),
                })

    for etiket, iso, donem_nesnesi in (seri or []):
        oge = {"etiket": str(etiket or ""), "bitis": str(iso or ""),
               "metin": {}}
        for alan in SERI_ALANLARI:
            _v = _sayi(getattr(donem_nesnesi, alan, None))
            oge[alan] = _v
            # METIN AYRI BIR SOZLUKTE: ham alanla ayni duzeyde
            # durursa "hasilat" ve "hasilat_metin" yan yana gelir ve
            # istemci hangisini cizecegini her alanda yeniden
            # ayirmak zorunda kalir.
            if _v is not None:
                oge["metin"][alan] = _mlr(_v)
        kayit["seri"].append(oge)

    # DEFTERIN KENDI DONEM BITISI -- ETIKETLE KARSILASTIRILABILIR
    # OLSUN DIYE. Ozetin `bitis` alani yalnizca sektorun tamami
    # cekildiginde doluyor; defter her sirket icin tasiyor.
    if defter.get("bitis"):
        kayit["donem_bitis"] = str(defter["bitis"])
    if defter.get("cekildi"):
        kayit["guncellendi"] = str(defter["cekildi"])
    return kayit


def kur(ozet: dict, sirketler: dict, sayfalar: dict | None = None,
        defter_oku=None) -> dict:
    """Butun sirketlerin besleme kayitlarini kurar.

    Donen yapi:
        {"sirket": {KOD: kayit}, "sektorler": [...], "toplam": n}

    `sayfalar` IKI KADEMELI: {KOD: {donem: yol}}. Tek kademeli
    olamaz, cunku bir sirketin BIRDEN COK donem sayfasi var.

    OLCULDU (2026-11-22), ilk yazim tek kademeliydi ve uretilen
    beslemede 379 bagin 316'SI YANLIS DONEMI gosteriyordu:

        A1CAP  donem "2026 3. ceyrek" -> /analiz/a1cap-2026-2-ceyrek/

    Iki sayfa da var (`a1cap-2026-2-ceyrek`, `a1cap-2026-3-ceyrek`);
    sozluk kurulurken hangisi SONRA geldiyse o kaliyordu. Hicbir
    hata uretmiyordu: bag calisiyor, sayfa aciliyor, yalnizca bir
    onceki ceyregi gosteriyor. "Etiket veriyle karsilastirilmali"
    diye yazili kusur sinifi.

    `defter_oku` sinamalar icin disaridan verilebilir; verilmezse
    `bilanco_defteri.oku` kullaniliyor. Varsayilani BIR ISLEV, bir
    bayrak degil: "defter kapali" diye bir mod olsa, uretimde yanlis
    tarafa dusmus bir bayrak butun TL seviyelerini sessizce
    yok ederdi.
    """
    oku = defter_oku or bilanco_defteri.oku_kayit
    yollar = {str(k).upper(): (v if isinstance(v, dict) else {})
              for k, v in (sayfalar or {}).items()}
    cikti: dict = {"sirket": {}, "sektorler": [], "toplam": 0}

    for _s, kayit in sorted((ozet or {}).items()):
        if not isinstance(kayit, dict):
            continue
        cikti["sektorler"].append({
            "sektor": str(kayit.get("sektor") or _s),
            "donem": str(kayit.get("donem") or ""),
            "sirket_sayisi": int(kayit.get("sirket_sayisi") or 0),
            "medyan": {a: _sayi(v) for a, v in
                       (kayit.get("medyan") or {}).items()
                       if _sayi(v) is not None},
            "tazelendi": str(kayit.get("tazelendi") or ""),
        })
        for kod in sorted((kayit.get("sirket") or {})):
            _k = str(kod).upper()
            _bilgi = (sirketler or {}).get(_k) or {}
            _bitis = ((kayit.get("bitis") or {}).get(_k)) or ""
            try:
                _defter = oku(_k, bilanco_ag.VARSAYILAN_CEYREK,
                              bitis=_bitis)
            except (OSError, TypeError, ValueError):
                _defter = None
            # SAYFA YALNIZCA AYNI DONEMINKI. Baska donemin sayfasi
            # BAG DEGIL, YANLIS BAG: okur "2026 3. ceyrek" yazan
            # karta basip 2. ceyrek sayfasini goruyordu.
            _bag = (yollar.get(_k) or {}).get(
                str(kayit.get("donem") or "")) or ("", "")
            if isinstance(_bag, str):
                # Eski (tek degerli) bicim: yol var, slug yok.
                _bag = (_bag, "")
            _kayit = sirket_kaydi(_k, _bilgi, kayit,
                                  sayfa=_bag[0], defter=_defter,
                                  slug=_bag[1] if len(_bag) > 1 else "")
            if _kayit:
                cikti["sirket"][_k] = _kayit
    cikti["toplam"] = len(cikti["sirket"])
    return cikti
