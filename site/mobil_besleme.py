# -*- coding: utf-8 -*-
"""MOBIL UYGULAMA BESLEMESI -- ayni icerigin JSON temsili.

NEDEN BU MODUL VAR
------------------
Olculdu (2026-10-18): sitenin 2.063 icerik sayfasinin TAMAMI yalnizca
HTML. Makine okunur olarak var olan tek sey `/arama.json` ve RSS.
Ikisi de mobil icin yetersiz: `arama.json` alan adlari kisaltilmis
(`b`, `o`, `y`), tarihi GORUNTU biciminde ("14 Ekim 2026"), govdesi,
gorseli, oranlari ve sayfalamasi yok.

Yani yerel bir mobil uygulama bugun haber ve analiz GOSTEREMEZ. Bu
modul o bosluğu kapatiyor.

TASARIM KARARI: YENI ARKA UC YOK
--------------------------------
Icerik zaten Python hattinda uretiliyor. Ikinci bir sunucu kurmak
yerine ayni kosu ikinci bir temsil daha basiyor:

    insa.py --> HTML (2.063 sayfa, DOKUNULMUYOR)
            --> RSS, sitemap          (DOKUNULMUYOR)
            --> arama.json            (DOKUNULMUYOR)
            --> /v1/*.json            (BU MODUL)

Sonuc: yeni calisma zamani maliyeti yok, tazelik mevcut hattin
tazeligi, ve tek bir URL degismiyor -- yalnizca yeni dosya yaziliyor.

BU MODUL HESAP YAPMAZ
---------------------
Oranlar, skorlar, yuzde degisimler BURADA YENIDEN HESAPLANMIYOR. Bu
depoda ayni seyi iki yerde hesaplamak yayinda yanlis sayi uretti
(negatif ozkaynakla +%128,5 ozkaynak karliligi; 15 ay oncesini "bir
yil once" diye etiketlemek). Besleme yalnizca TASIR.

YENI BIR YAYIN YUZEYI, TUM YAYIN KURALLARINA TABIDIR
----------------------------------------------------
En onemli tasarim notu bu. Mevcut denetimlerin cogu HTML CIKTISINA
bakiyor; JSON onlarin gormedigi yeni bir kapi. Bu depoda tam bu sinif
iki kez yasandi: kural uretimde siki, YAYINDA gevsekti.

Bu yuzden kurallar bu modulun ICINDE, veri kurulurken uygulaniyor --
sonradan denetleyen bir adima birakilmiyor:

* **CC BY atfi olmayan fotograf BESLEMEYE GIRMEZ** (`_foto_gec`).
  Atifsiz gorsel yayimlamak lisans ihlali; `_lisans_denetimi` bunu
  HTML icin "hata" seviyesinde tutuyor, JSON da ayni cizgide.
* **Ticari kaynakli haber kurum VE adres olmadan BESLEMEYE GIRMEZ**
  (`haber_ozeti` None doner). Kisa iktibas hakkinin sarti kaynak
  gostermek; atifsiz tasiyamayiz. Olculdu: bugun boyle kayit YOK,
  yani bedeli sifir, korudugu sey gercek.
* **Lisansi bizde olmayan seri piyasa beslemesine GIRMEZ**
  (`piyasa`). Kume ici uydurulmuyor, tek kaynaktan
  (`makro_uret_ucretsiz.LISANSSIZ_SERILER`) geliyor.
* **ISO olmayan tarih tasinmaz.** Gorüntü bicimli bir tarihi ISO
  alanina koymak, istemcide sessizce yanlis siralama demek.
* **`kurgusal` bayragi tasinir.** Kurgusal icerigi gercek gibi
  gostermemek icin isaretin istemciye ULASMASI gerekiyor.

Bu kurallarin her biri `site/test_mobil_besleme.py` icinde mutasyonla
sinaniyor: kurali bozup sinamanin kirmiziya dondugu goruluyor.
"""

from __future__ import annotations

import re

#: Besleme surumu. Istemci `/v1/surum.json` okuyup uyumu kontrol eder.
#: Kiran bir degisiklik olursa onek `/v2/` olur ve `/v1/` bir sure
#: daha yayinda kalir -- magazadaki eski uygulama bir anda bozulmasin.
SURUM = 1

#: Cikti oneki. Yol SURUM'den turetiliyor ki ikisi ayrisamasin.
ONEK = f"/v{SURUM}"

#: Liste sayfasindaki kayit sayisi.
#:
#: 24 secimi: telefonda bir ekran ~6 kart gosteriyor, yani dort ekran
#: kaydirma bir istege dusuyor. Daha kucuk sayfa daha cok istek, daha
#: buyuk sayfa ilk acilisi yavaslatir.
SAYFA_BOYU = 24

#: Ana sayfa beslemesinde kac kayit.
ONE_CIKAN_SAYISI = 8

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _dizge(x) -> str:
    """None'i bos dizgeye cevirir; sayilari metne."""
    return "" if x is None else str(x)


def _iso(deger) -> str:
    """YALNIZCA ISO tarih gecer; baska her sey bos doner.

    NEDEN KATI: `arama.json` tarihi gorüntü biciminde tasiyor
    ("14 Ekim 2026"). O degeri bir `tarih` alanina koymak istemcide
    sessizce yanlis siralama demek -- hicbir hata gorunmez, yalnizca
    haberler karisik siraya girer. Bos tarih, yanlis tarihten iyidir.
    """
    s = _dizge(deger).strip()
    return s if _ISO.match(s) else ""


def _al(kayit, ad: str, varsayilan=""):
    """Hem sozluk hem nesne icin alan okur.

    Haberler `dict`, analizler `Analiz` nesnesi. Ikisini ayri
    yollardan okumak iki kod yolu demek; tek yol tutuluyor.
    """
    if isinstance(kayit, dict):
        deger = kayit.get(ad, varsayilan)
    else:
        deger = getattr(kayit, ad, varsayilan)
    return varsayilan if deger is None else deger


def _foto_gec(kayit) -> tuple[str, str]:
    """(foto, atif) -- ATIF YOKSA FOTOGRAF DA YOK.

    CC BY atfi zorunlu. Atifsiz bir gorseli beslemeye koymak, mobil
    uygulamada atifsiz yayimlamak demek. Gorseli dusurmek bir kayip
    ama lisans ihlali degil.
    """
    foto = _dizge(_al(kayit, "foto")).strip()
    atif = _dizge(_al(kayit, "foto_atif")).strip()
    if not foto or not atif:
        return "", ""
    return foto, atif


def _slug(yol: str) -> str:
    """"/haber/abc-def/" -> "abc-def"."""
    return yol.strip("/").rsplit("/", 1)[-1] if yol else ""


def haber_ozeti(h: dict) -> dict | None:
    """Liste karti icin haber kaydi. Kurala uymazsa None.

    None donen kayit beslemeye HIC girmiyor. Iki sebeple olur:

    1. Sayfasi yok -- tiklanamaz bir satir olurdu (`arama_dizini`
       ayni kurali uyguluyor).
    2. Ticari kaynak ama kurum ya da adres eksik -- kisa iktibas
       hakkinin sarti kaynak gostermek.
    """
    yol = _dizge(h.get("yol")).strip()
    if not yol:
        return None

    ticari = bool(h.get("ticari"))
    kurum = _dizge(h.get("kurum")).strip()
    adres = _dizge(h.get("adres")).strip()
    if ticari and not (kurum and adres):
        return None

    foto, atif = _foto_gec(h)
    return {
        "tur": "haber",
        "slug": _slug(yol),
        "yol": yol,
        "baslik": _dizge(h.get("baslik")),
        "ozet": _dizge(h.get("neden_onemli") or h.get("ozet")),
        "konu": _dizge(h.get("konu")),
        "bolge": _dizge(h.get("bolge")),
        "kurum": kurum,
        "kurum_tam": _dizge(h.get("kurum_tam")) or kurum,
        "ticari": ticari,
        "kaynak_adres": adres,
        "tarih": _iso(h.get("tarih")),
        "foto": foto,
        "foto_atif": atif,
    }


def haber_tam(h: dict) -> dict | None:
    """Detay ekrani icin haber kaydi -- ozetin ustune govde alanlari."""
    kayit = haber_ozeti(h)
    if kayit is None:
        return None
    kanallar = _al(h, "kanallar", [])
    kayit.update({
        "baslik_kaynak": _dizge(h.get("baslik_kaynak")),
        "kaynak_ozeti": _dizge(h.get("ozet")),
        "neden_onemli": _dizge(h.get("neden_onemli")),
        "kanal_basligi": _dizge(h.get("kanal_basligi")),
        "kanallar": [_dizge(k) for k in kanallar] if kanallar else [],
        "cevrildi": bool(h.get("cevrildi")),
        "dil": _dizge(h.get("dil")),
        "tarih_gorunur": _dizge(h.get("tarih_gorunur")),
    })
    return kayit


def analiz_ozeti(a) -> dict | None:
    """Liste karti icin analiz kaydi.

    `skor` ve oranlar BURADA HESAPLANMIYOR -- nesnede ne varsa o
    tasiniyor. Bkz. modul basi.
    """
    yol = _dizge(_al(a, "yol")).strip()
    slug = _dizge(_al(a, "slug")).strip()
    # SLUG DA ZORUNLU, yalnizca yol degil.
    #
    # `Analiz.yol` slug'dan turetiliyor, yani slug bos oldugunda yol
    # BOS DEGIL -- "/analiz//" oluyor. Yalnizca yolu denetlemek bu
    # kaydi gecirirdi: liste beslemesine bozuk adresli bir kart
    # girer, detay dosyasi ise hic yazilmaz (`uret` slug istiyor).
    # Okur karta dokununca 404 gorurdu.
    #
    # Kendi sinamam yakaladi; elle bakarak gorulmezdi.
    if not yol or not slug:
        return None
    foto, atif = _foto_gec(a)
    if not foto:
        # Sirket analizlerinde sayfa fotograf yerine amblem gosteriyor;
        # paylasim karti icin ayri bir alan var ve o da atif tasiyor.
        foto, atif = "", ""
    return {
        "tur": "analiz",
        "slug": slug,
        "yol": yol,
        "baslik": _dizge(_al(a, "baslik")),
        "ozet": _dizge(_al(a, "ozet")),
        "sirket": _dizge(_al(a, "sirket")),
        "kod": _dizge(_al(a, "kod")),
        "sektor": _dizge(_al(a, "sektor")),
        "donem": _dizge(_al(a, "donem")),
        "kategori": _dizge(_al(a, "kategori")),
        "tarih": _iso(_al(a, "tarih")),
        "skor": _dizge(_al(a, "skor")) or None,
        "okuma_dk": int(_al(a, "okuma_dk", 0) or 0),
        "yazar": _dizge(_al(a, "yazar")),
        "unvan": _dizge(_al(a, "unvan")),
        "imzali": bool(_al(a, "yazar")),
        # KURGUSAL BAYRAGI TASINIYOR: isaret istemciye ULASMAZSA
        # kurgusal icerik gercek gibi gorunur.
        "kurgusal": bool(_al(a, "kurgusal", False)),
        "amblem": _dizge(_al(a, "amblem_yol")),
        "foto": foto,
        "foto_atif": atif,
    }


def analiz_tam(a) -> dict | None:
    """Detay ekrani icin analiz kaydi -- govde ve kriterler dahil."""
    kayit = analiz_ozeti(a)
    if kayit is None:
        return None
    kriterler = _al(a, "kriterler", []) or []
    bolumler = _al(a, "bolumler", ()) or ()
    sayimlar = _al(a, "sayimlar", ()) or ()
    kaynaklar = _al(a, "kaynaklar", ()) or ()
    kayit.update({
        "govde_html": _dizge(_al(a, "govde")),
        "kapsam": _dizge(_al(a, "kapsam")),
        "veri_kaynagi": _dizge(_al(a, "veri_kaynagi")),
        "kaynaklar": [_dizge(k) for k in kaynaklar],
        "kriterler": [
            {
                "ad": _dizge(_al(k, "ad")),
                "puan": _dizge(_al(k, "puan")),
                "tam": _dizge(_al(k, "tam")),
            }
            for k in kriterler
        ],
        "bolumler": [
            {"baslik": _dizge(b.get("baslik") if isinstance(b, dict) else b),
             "capa": _dizge(b.get("capa") if isinstance(b, dict) else "")}
            for b in bolumler
        ],
        "sayimlar": [[_dizge(s[0]), _dizge(s[1])]
                     for s in sayimlar if len(s) == 2],
        "kelime": int(_al(a, "kelime", 0) or 0),
    })
    return kayit


def piyasa(gostergeler: dict | None, lisanssiz) -> dict:
    """Piyasa seridi -- LISANSI BIZDE OLMAYAN SERI GIRMEZ.

    Kume burada yeniden yazilmiyor; cagiran
    `makro_uret_ucretsiz.LISANSSIZ_SERILER` degerini veriyor. O liste
    neden boyle oldugunu kendi yaninda aciklıyor: SP500 ve DJIA
    S&P Dow Jones Indices LLC, NASDAQCOM Nasdaq Inc., VIXCLS Cboe
    lisansi. FRED bunlari saglayicinin IZNIYLE dagitiyor ve o izin
    bize gecmiyor.

    BIST 100 de ayni sebeple yok: dagitim lisansi Borsa Istanbul'da ve
    bizde degil -- `makro.PANEL_GRUPLARI` yaninda yazili.

    Eksik bir grup, lisanssiz bir gruptan iyidir.
    """
    g = gostergeler or {}
    yasak = frozenset(lisanssiz or ())
    kalemler = []
    for k in (g.get("kalemler") or []):
        kod = _dizge(_al(k, "kod")).strip()
        if kod and kod in yasak:
            continue
        kalemler.append({
            "kod": kod,
            "ad": _dizge(_al(k, "ad")),
            "deger": _dizge(_al(k, "deger")),
            "fark": _dizge(_al(k, "fark")),
            "yon": _dizge(_al(k, "yon")),
            "tarih": _iso(_al(k, "tarih")),
            "bayat": bool(_al(k, "bayat", False)),
            "gun": int(_al(k, "gun", 0) or 0),
            "ritim": _dizge(_al(k, "ritim")),
        })
    return {
        # VERI TARIHI ZORUNLU ALAN, sus degil.
        #
        # Sayi tek basina "canli fiyat" izlenimi veriyor. Web tarafinda
        # bu tam olarak yasandi: tarih yalnizca `title` ozniteligindeydi,
        # yani TELEFONDA KIMSE goremiyordu ve kullanici "fiyat hic
        # islemedi" dedi. Uygulamada ayni hataya dusmemek icin tarih
        # verinin yanindan ayrilmiyor.
        "veri_tarihi": _iso(g.get("veri_tarihi")),
        "canli_degil": True,
        "aciklama": "Gecikmeli veri. Her kalemin kendi veri tarihi "
                    "yanindadir.",
        "kalemler": kalemler,
    }


def _alan(kayit, ad: str, varsayilan=""):
    """`beklenti` hem NESNE hem SOZLUK olarak gelebiliyor.

    Hat onu bir dataclass olarak koyuyor (`beklenti.Kutu`), bazi
    yollarda sozluk oluyor. Bu depoda `.get()` cagirmak tam burada
    AttributeError uretti ve kusur COKME olarak degil EKSIKLIK olarak
    gorundu -- surpriz alani sessizce hic uretilmedi.
    """
    if kayit is None:
        return varsayilan
    if isinstance(kayit, dict):
        d = kayit.get(ad, varsayilan)
    else:
        d = getattr(kayit, ad, varsayilan)
    return varsayilan if d is None else d


def _dal(d) -> dict:
    """Kosullu senaryo dali: esik asilirsa / altinda kalirsa.

    FIYAT YONU IDDIA EDILMIYOR -- `mekanizma` neyin neden degistigini
    anlatiyor, `olcum` ise gecmis gozlemleri. Ikisi ayri alan cunku
    biri akil yurutme, oteki olcum; karistirilirsa olcum bir tahmin
    gibi okunur.
    """
    return {
        "yon": _dizge(_alan(d, "yon")),
        "baslik": _dizge(_alan(d, "baslik")),
        "mekanizma": _dizge(_alan(d, "mekanizma")),
        "olcum": _dizge(_alan(d, "olcum")),
    }


def takvim_ogesi(k: dict) -> dict | None:
    """Ekonomik takvim kalemi.

    UC KURAL BURADA YASIYOR:

    1. **SAAT DILIMI ACIK.** Hem UTC ani hem yerel metin tasiniyor ve
       `saat_dilimi` alani hangi dilimde gosterildigini soyluyor. Bir
       veri aciklamasinin saati, hangi dilimde oldugu yazilmadan
       anlamsiz: okur 14:00'i kendi saatinde sanar ve ucak kacirir
       gibi aciklamayi kacirir.

    2. **"KESIN DEGIL" BILGISI TASINIYOR.** Bazi yayinlarin saati
       kurum tarafindan onaylanmamis oluyor (`kesin=False`). Bunu
       dusurmek, tahmini bir saati kesinmis gibi gostermek demek.

    3. **BEKLENTI ILE ONCEKI DEGER AYRI.** Esik bazen gercek bir
       piyasa konsensusu, bazen yalnizca ONCEKI deger
       (`esik_kaynak`). Ikisini "beklenti" diye tek alana koymak,
       olmayan bir konsensus uydurmak olurdu -- ve surpriz hesabi da
       o zaman anlamsizlasir. Bu yuzden `esik_kaynak` aynen
       tasiniyor ve `surpriz` YALNIZCA gercek konsensus varken
       uretiliyor (hattaki kuralin aynisi).
    """
    ad = _dizge(k.get("ad")).strip()
    an = _dizge(k.get("an")).strip()
    if not ad or not an:
        return None

    b = k.get("beklenti")
    dallar = _alan(b, "dallar", ()) or ()
    g = k.get("gerceklesen")
    s = k.get("surpriz")

    kayit = {
        "ad": ad,
        "ulke": _dizge(k.get("ulke")),
        "seri": _dizge(k.get("seri")),
        "onem": int(k.get("onem") or 0),
        # SAAT DILIMI: `an` UTC kaymasiyla birlikte ISO; `yerel`
        # Turkiye saatiyle gosterim. Ikisi birlikte olmazsa istemci
        # ya yanlis donusturur ya da hic donusturmez.
        "an": an,
        "yerel": _dizge(k.get("yerel")),
        "gun": _dizge(k.get("gun")),
        "saat": _dizge(k.get("saat")),
        "saat_dilimi": "Europe/Istanbul",
        # SAATI KESIN MI: dusurulurse tahmini saat kesinmis gorunur.
        "kesin": bool(k.get("kesin", False)),
        # Konsensusun KAYNAGI: okur sayinin nereden geldigini bilmeli.
        "kaynak": _dizge(k.get("kaynak")),
        "aciklandi": g is not None,
    }

    if b is not None:
        kayit["onceki_deger"] = _dizge(_alan(b, "son_deger"))
        kayit["onceki_tarih"] = _dizge(_alan(b, "son_tarih"))
        kayit["esik_deger"] = _dizge(_alan(b, "esik_deger"))
        # "beklenti" | "onceki" -- istemci bunu OKUMAK ZORUNDA.
        kayit["esik_kaynak"] = _dizge(_alan(b, "esik_kaynak"))
        kayit["dallar"] = [_dal(d) for d in dallar]
    else:
        kayit["dallar"] = []

    if g is not None:
        kayit["gerceklesen"] = {
            "deger": _alan(g, "deger", None),
            "donem": _dizge(_alan(g, "donem")),
            "birim": _dizge(_alan(g, "birim")),
        }

    # SURPRIZ YALNIZCA GERCEK KONSENSUS VARKEN.
    #
    # Esik onceki degerse, "beklentinin ustunde geldi" demek yanlis
    # olur: ortada bir beklenti YOK, yalnizca bir onceki rakam var.
    if s is not None and kayit.get("esik_kaynak") == "beklenti":
        kayit["surpriz"] = {
            "fark": _alan(s, "fark", None),
            "yon": _dizge(_alan(s, "yon")),
            "metin": _dizge(_alan(s, "metin")),
        }
    return kayit


def takvim(kutular: list | None, uretildi: str = "") -> dict:
    """Ekonomik takvim beslemesi."""
    ogeler = [k for k in (takvim_ogesi(x) for x in (kutular or []))
              if k is not None]
    # EN YAKIN ONCE: takvim ileriye bakiyor, en yakin aciklama en
    # ustte olmali.
    ogeler.sort(key=lambda k: (k["an"], -k["onem"]))
    return {
        "surum": SURUM,
        "uretildi": _dizge(uretildi),
        "saat_dilimi": "Europe/Istanbul",
        # METIN DUZ YAZI -- MARKDOWN ISARETI YOK.
        #
        # Ilk yazimda "`kesin` yanlissa..." diye yazilmisti ve
        # uygulamada TERS TIRNAKLAR AYNEN gorundu: istemci duz metin
        # basiyor, Markdown islemiyor. Gercek tarayicida goruldu.
        #
        # Besleme metinleri okura dogrudan gidiyor; bicimlendirme
        # isareti tasimamali.
        "aciklama": "Saatler Türkiye saatiyle (UTC+3). Saati "
                    "kesinleşmemiş açıklamalar ayrıca işaretlidir.",
        "ogeler": ogeler,
    }


#: Varlik detayinda kac gozlem tasiniyor (kivilcim grafigi icin).
#:
#: Sayfadaki kivilcim zaten bu seriden ciziliyor; uygulamada da ayni
#: grafigi cizebilmek icin ham noktalar gerekiyor. 30 nokta bir aylik
#: hareketi gosteriyor ve dosyayi kucuk tutuyor.
VARLIK_GOZLEM = 30

#: Varlik detayinda kac haber.
VARLIK_HABER = 12


def varlik_ogesi(v: dict, kunye: dict | None, veri: dict | None,
                 baglar: list | None, haberler: list | None,
                 lisanssiz=()) -> dict | None:
    """Varlik detay kaydi.

    LISANS KURALI BURADA DA GECERLI -- VE IKI KEZ UYGULANIYOR.
    -------------------------------------------------------
    `insa.py` degeri zaten suzuyor: `veri = None if seri_kodu in
    LISANSSIZ_SERI else seri_ozet(...)`. Yani cagiran dogru davraniyor.

    Buna ragmen burada IKINCI bir kapi var ve bu bilincli: bu modul
    cagiranin dogru davranmasina GUVENMEMELI. Bu depoda tam bu sinif
    yasandi -- bir kural bir yerde yaziliydi, baska bir yerde ihlal
    ediliyordu ve hicbir sey patlamiyordu.

    SAYFA KALIYOR, DEGER GITMIYOR: yapisal iliskiler ("S&P 500 ->
    NASDAQ etkiler") BIZIM ve degerli. Kisitlama VERIYE, isim anmaya
    degil -- ayni ayrim `test_lisans.py` icinde de yazili.
    """
    kod = _dizge(v.get("kod")).strip()
    yol = _dizge(v.get("yol")).strip()
    if not kod or not yol:
        return None

    k = kunye or {}
    seri_kodu = _dizge(k.get("seri_kodu"))
    # IKINCI KAPI: cagiran suzmeyi unutursa burada eleniyor.
    if seri_kodu and seri_kodu in frozenset(lisanssiz or ()):
        veri = None

    kayit = {
        "kod": kod,
        "yol": yol,
        "ad": _dizge(v.get("ad")) or _dizge(k.get("ad")),
        "ad_en": _dizge(k.get("ad_en")),
        "tur": _dizge(v.get("tur")) or _dizge(k.get("tur")),
        "aciklama": _dizge(k.get("aciklama")),
        "haber_sayisi": int(v.get("sayi") or 0),
        # Seri kodu her zaman yaziliyor; DEGER yazilmayabilir.
        # Ikisi ayri sey: "hangi seri" bir tanim, "kac" bir veri.
        "seri_kodu": seri_kodu,
        "veri_var": veri is not None,
    }

    if veri is not None:
        gozlem = list(veri.get("seri") or [])[-VARLIK_GOZLEM:]
        kayit["veri"] = {
            "deger": _dizge(veri.get("deger")),
            "birim": _dizge(veri.get("birim")),
            "degisim": _dizge(veri.get("degisim")),
            "yon": _dizge(veri.get("yon")),
            # VERI TARIHI ZORUNLU: sayi tek basina "canli fiyat"
            # izlenimi veriyor.
            "tarih": _iso(veri.get("tarih")),
            "gozlem_sayisi": int(veri.get("gozlem") or 0),
            "seri": [
                {"tarih": _iso(_al(g, "tarih")),
                 "deger": _al(g, "deger", None)}
                for g in gozlem
            ],
        }

    # YAPISAL BAGLAR -- sitenin haber toplamaktan ayrildigi katman.
    #
    # `dayanak` tasiniyor: "yapisal" (tanim geregi dogru) ile "veri"
    # (gozlemden cikarilmis, degisebilir) ayni sey degil ve okur
    # ayrimi gormeli. Sayfada da boyle basiliyor.
    kayit["baglar"] = [
        {
            "hedef": _dizge(_al(b, "hedef")),
            "hedef_ad": _dizge(_al(b, "hedef_ad")),
            "kaynak": _dizge(_al(b, "kaynak")),
            "kaynak_ad": _dizge(_al(b, "kaynak_ad")),
            "tur": _dizge(_al(b, "tur")),
            "aciklama": _dizge(_al(b, "aciklama")),
            "dayanak": _dizge(_al(b, "dayanak")),
            "guc": int(_al(b, "guc", 0) or 0),
            "yon": _dizge(_al(b, "yon")),
        }
        for b in (baglar or [])
    ]

    kayit["haberler"] = [
        {
            "baslik": _dizge(_al(h, "baslik")),
            "yol": _dizge(_al(h, "yol")),
            "tarih": _iso(_al(h, "tarih")),
            "kurum": _dizge(_al(h, "kurum")),
        }
        for h in (haberler or [])[:VARLIK_HABER]
        if _dizge(_al(h, "yol"))
    ]
    return kayit


def varlik_dosyalari(kayitlar: list | None, uretildi: str = "") -> dict:
    """Varlik dizini + her varlik icin detay dosyasi."""
    ogeler = [k for k in (kayitlar or []) if k]
    cikti: dict = {}
    for k in ogeler:
        cikti[f"{ONEK}/varlik/{k['kod'].lower()}.json"] = k

    # DIZIN: detayin TAMAMINI tasimiyor -- liste ekrani icin yeterli
    # alanlar. Tam detayi dizine koymak, 75 varligin butun
    # baglarini ve haberlerini ilk acilista indirmek olurdu.
    dizin = sorted(
        (
            {
                "kod": k["kod"],
                "yol": k["yol"],
                "ad": k["ad"],
                "tur": k["tur"],
                "haber_sayisi": k["haber_sayisi"],
                "veri_var": k["veri_var"],
                "deger": (k.get("veri") or {}).get("deger", ""),
                # BIRIM LISTEDE DE OLMALI -- SAYI TEK BASINA ANLAMSIZ.
                #
                # Olculdu (2026-10-21): listede "Tarım Dışı İstihdam
                # 29,00" goruluyordu. Birim ("bin kişi") yalnizca
                # DETAY dosyasindaydi; sitenin kendi varlik sayfasi
                # onu basiyor ("126,55 USD/varil", "4.053 mn $").
                # Yani ayni sayi iki yuzeyde iki anlam tasiyordu.
                #
                # BURADA YENI BIR KURAL YOK. Deger ne ise birim de
                # odur: `varlik.seri_ozet` oran serilerinde ("%")
                # birimi zaten bosaltiyor, geri kalanda oldugu gibi
                # birakiyor -- sitenin varlik sayfasi da tam olarak
                # bunu basiyor ("49,58 TL"). Ikinci bir sadelestirme
                # kurali yazmak, ayni karari iki yerde vermek olurdu
                # ve iki yer zamanla ayrisir.
                "birim": (k.get("veri") or {}).get("birim", ""),
                "yon": (k.get("veri") or {}).get("yon", ""),
                "tarih": (k.get("veri") or {}).get("tarih", ""),
                "dosya": f"{ONEK}/varlik/{k['kod'].lower()}.json",
            }
            for k in ogeler
        ),
        key=lambda x: (-x["haber_sayisi"], x["ad"]),
    )
    cikti[f"{ONEK}/varlik.json"] = {
        "surum": SURUM,
        "uretildi": _dizge(uretildi),
        "toplam": len(dizin),
        "ogeler": dizin,
    }
    return cikti


_SECENEK = re.compile(
    r'<option\s+value="([^"]+)"\s*>\s*(.*?)\s*</option>', re.S | re.I)


def senaryo_olcutleri(uyelik_html: str) -> list[dict]:
    """Senaryo formundaki "olculebilir tetikleyici" listesi.

    KAYNAK WEB FORMUNUN KENDISI -- liste burada YENIDEN YAZILMIYOR.

    Ayni liste bugun iki yerde duruyor: `worker.js` (kodlar,
    dogrulama icin) ve `uyelik.html` (kodlar + okunabilir adlar).
    Uygulamaya UCUNCU bir kopya koymak, bu depoda defalarca
    yasanan "iki yer ayrisir" kusurunu bir kat daha buyutmek
    olurdu -- ustelik renk ya da metin gibi gorunur bir seyde
    degil, bir senaryonun SONUCLANIP sonuclanmayacaginda.

    `test_senaryo_olcutu.py` uc tarafi birlikte sinıyor: listedeki
    her kod `worker.js`te de olmali ve depoda COZULEBILMELI.
    """
    m = re.search(
        r'<select\s+name="olcut_kod"\s*>(.*?)</select>',
        uyelik_html, re.S | re.I)
    if not m:
        return []
    cikti = []
    for kod, etiket in _SECENEK.findall(m.group(1)):
        kod = kod.strip()
        if not kod:
            continue              # "— seçmeyin —" secenegi
        # Etiket icindeki olasi ic etiketler temizleniyor.
        ad = re.sub(r"<[^>]+>", "", etiket).strip()
        cikti.append({"kod": kod, "ad": ad})
    return cikti


#: Senaryo ufuklari -- `worker.js` icindeki `UFUKLAR` ile AYNI olmali.
#: Sinama ikisini karsilastiriyor.
UFUKLAR = ("1 hafta", "1 ay", "3 ay", "6 ay", "1 yıl")

#: Alan uzunluk sinirlari -- `worker.js` ile AYNI olmali.
#:
#: Uygulamanin bunlari BILMESI gerekiyor: kullanici 200 karakter
#: yazip "kaydet"e bastiginda sunucudan hata almasi, 180'de
#: uyarilmasindan kotu. Sinama sunucudaki degerlerle karsilastiriyor.
SENARYO_SINIRLARI = {
    "kosul": {"en_az": 12, "en_cok": 180},
    "sonuc": {"en_az": 12, "en_cok": 180},
    "gerekce": {"en_az": 0, "en_cok": 1200},
    "curutme": {"en_az": 0, "en_cok": 220},
    "kaynaklar": {"en_az": 0, "en_cok": 500},
    "capa_baslik": {"en_az": 0, "en_cok": 140},
}


def senaryo_kurallari(uyelik_html: str) -> dict:
    """Uygulamanin senaryo formunu kurmak icin ihtiyaci olan her sey."""
    return {
        "surum": SURUM,
        "olcutler": senaryo_olcutleri(uyelik_html),
        "yonler": [
            {"kod": "ustunde", "ad": "eşiğin üstüne çıkarsa"},
            {"kod": "altinda", "ad": "eşiğin altına inerse"},
        ],
        "ufuklar": list(UFUKLAR),
        "sinirlar": SENARYO_SINIRLARI,
        # CURUTME KOSULU neden onemli -- uygulamada da yazili olsun.
        "notlar": {
            "curutme": "Bir senaryoyu bir görüşten ayıran tek şey, "
                       "yazarın kendi kendini yanlışlayabilecek "
                       "gelişmeyi önceden yazmasıdır. Zorunlu değil.",
            "olcut": "Koşulunuzu bir göstergeye bağlarsanız ufkunuz "
                     "dolduğunda senaryo otomatik sonuçlandırılır. "
                     "Bağlamazsanız 'belirsiz' olarak işaretlenir.",
        },
    }


def arama_dizini(haberler: list, analizler: list, varliklar: list | None,
                 katlama: dict | None = None, uretildi: str = "") -> dict:
    """Uygulama ici arama dizini -- KOMPAKT.

    NEDEN AYRI BIR DIZIN
    --------------------
    Sitenin `/arama.json` dosyasi 563 KB ve mobil icin uygun degil:
    telefon sebekesinde ilk arama yarim megabayt indirmekle
    basliyor. Ustelik alan adlari kisaltilmis (`b`, `o`, `y`) ve
    tarih GORUNTU biciminde ("14 Ekim 2026") -- istemci onu
    siralayamaz.

    Buradaki dizin yalnizca SONUC SATIRI icin gerekeni tasiyor:
    tur, baslik, slug, ISO tarih, kategori. Ozet YOK -- okur
    sonuca dokununca detay dosyasi zaten geliyor.

    KAYNAK AYNI KAYITLAR: `uret` icinde zaten kurulmus ozet
    listeleri kullaniliyor, yani dizin ile listeler ayrisamaz.

    KATLAMA TABLOSU DA TASINIYOR
    ----------------------------
    Turkce diakritik katlamasi ("turkiye" -> "Türkiye") sitede IKI
    yerde duruyor: `insa._SLUG_ESLEME` ve `ara.js` icindeki
    `KATLAMA`. Bir sinama ikisinin AYNI oldugunu dogruluyor, cunku
    ayrisirlarsa "hurmuz" yazan okur "Hürmüz"u bulamaz ve hicbir
    hata gorunmez.

    Uygulamaya UCUNCU bir kopya yazmak o riski bir kat daha
    buyutmek olurdu. Tablo beslemeyle tasiniyor ve uygulama onu
    kullaniyor.
    """
    kayitlar = []
    for h in (haberler or []):
        kayitlar.append({
            "t": "haber",
            "b": h.get("baslik", ""),
            "s": h.get("slug", ""),
            "d": h.get("tarih", ""),
            "k": h.get("konu", ""),
        })
    for a in (analizler or []):
        kayitlar.append({
            "t": "analiz",
            "b": a.get("baslik", ""),
            "s": a.get("slug", ""),
            "d": a.get("tarih", ""),
            "k": a.get("kategori", ""),
            # Sirket kodu aranabilir olmali: okur "THYAO" yazar.
            "c": a.get("kod", ""),
        })
    for v in (varliklar or []):
        kayitlar.append({
            "t": "varlik",
            "b": v.get("ad", ""),
            "s": v.get("kod", ""),
            "d": "",
            "k": v.get("tur", ""),
        })
    # Baslik ya da slug'i olmayan kayit ARANAMAZ, dizine girmiyor.
    kayitlar = [k for k in kayitlar if k["b"] and k["s"]]
    return {
        "surum": SURUM,
        "uretildi": _dizge(uretildi),
        "katlama": dict(katlama or {}),
        "toplam": len(kayitlar),
        "kayitlar": kayitlar,
    }


def sayfala(kayitlar: list, boyu: int = SAYFA_BOYU) -> list[list]:
    """Listeyi sabit boylu sayfalara boler. Bos liste -> bir bos sayfa.

    BOS LISTE ICIN DE BIR SAYFA URETILIYOR: istemci `sayfa-1.json`i
    her zaman bulabilsin. Dosyanin olmamasi ile icerigin olmamasi ayni
    sey degil -- ilki 404, ikincisi "henuz icerik yok" ekrani.
    """
    if boyu < 1:
        boyu = SAYFA_BOYU
    if not kayitlar:
        return [[]]
    return [kayitlar[i:i + boyu] for i in range(0, len(kayitlar), boyu)]


def _liste_dosyalari(onek: str, kayitlar: list,
                     boyu: int = SAYFA_BOYU) -> dict:
    """Sayfalanmis liste dosyalari + her sayfada gezinme bilgisi."""
    sayfalar = sayfala(kayitlar, boyu)
    toplam = len(sayfalar)
    cikti = {}
    for no, grup in enumerate(sayfalar, start=1):
        cikti[f"{onek}/sayfa-{no}.json"] = {
            "surum": SURUM,
            "sayfa": no,
            "sayfa_sayisi": toplam,
            "toplam_kayit": len(kayitlar),
            "sonraki": (f"{onek}/sayfa-{no + 1}.json"
                        if no < toplam else None),
            "ogeler": grup,
        }
    return cikti


def _tarihe_gore(kayitlar: list) -> list:
    """EN YENI USTTE. Tarihi olmayan kayit SONA.

    Tarihi bos olani basa koymak, olculmemis bir tazeligi olculmus gibi
    sunmak olurdu (ayni gerekce `uret_bilanco_sayfa._tazelik` icinde
    de yazili).
    """
    return sorted(kayitlar,
                  key=lambda k: (k.get("tarih") or "", k.get("slug") or ""),
                  reverse=True)


def uret(analizler: list, haberler: list, gostergeler: dict | None,
         lisanssiz=(), uretildi: str = "",
         one_cikan: list | None = None,
         takvim_kutulari: list | None = None,
         varliklar: list | None = None,
         uyelik_html: str = "",
         katlama: dict | None = None) -> dict:
    """Butun besleme dosyalarini kurar: {goreli yol: JSON nesnesi}.

    DOSYA YAZMIYOR. Saf islev olmasi bilincli: sinama diske hic
    dokunmadan tum ciktiyi inceleyebiliyor. Bu depoda bir sinama
    `yaz_sektorel` cagirdigi icin GERCEK bir analiz dosyasi yazmisti;
    saf islev o kazayi mumkun kilmiyor.
    """
    h_ozet = [k for k in (haber_ozeti(h) for h in (haberler or []))
              if k is not None]
    a_ozet = [k for k in (analiz_ozeti(a) for a in (analizler or []))
              if k is not None]
    h_ozet = _tarihe_gore(h_ozet)
    a_ozet = _tarihe_gore(a_ozet)

    cikti: dict = {}
    cikti.update(_liste_dosyalari(f"{ONEK}/haber", h_ozet))
    cikti.update(_liste_dosyalari(f"{ONEK}/analiz", a_ozet))

    # DETAY DOSYALARI. Her oge icin bir dosya: yerel ekran HTML
    # ayristirmak zorunda kalmasin.
    for h in (haberler or []):
        tam = haber_tam(h)
        if tam and tam["slug"]:
            cikti[f"{ONEK}/haber/{tam['slug']}.json"] = tam
    for a in (analizler or []):
        tam = analiz_tam(a)
        if tam and tam["slug"]:
            cikti[f"{ONEK}/analiz/{tam['slug']}.json"] = tam

    cikti[f"{ONEK}/piyasa.json"] = piyasa(gostergeler, lisanssiz)
    cikti[f"{ONEK}/takvim.json"] = takvim(takvim_kutulari, uretildi)
    cikti.update(varlik_dosyalari(varliklar, uretildi))
    if uyelik_html:
        cikti[f"{ONEK}/senaryo-kurallari.json"] = senaryo_kurallari(
            uyelik_html)

    # ARAMA DIZINI -- AYNI ozet kayitlarindan kuruluyor, yani
    # listelerle ayrisamaz.
    cikti[f"{ONEK}/arama.json"] = arama_dizini(
        h_ozet, a_ozet, varliklar, katlama, uretildi)

    # ANA SAYFA BESLEMESI. Secim BURADA YAPILMIYOR: `one_cikan`
    # verilirse sitenin kendi one cikan karari tasiniyor, yoksa en
    # yeniler. Iki yerin ayri secim yapmasi, uygulamanin siteden
    # farkli bir "gunun onemli gelismesi" gostermesi demek olurdu.
    secilen = one_cikan if one_cikan is not None else []
    if secilen:
        one = [k for k in (haber_ozeti(h) for h in secilen)
               if k is not None][:ONE_CIKAN_SAYISI]
    else:
        one = h_ozet[:ONE_CIKAN_SAYISI]
    cikti[f"{ONEK}/one-cikan.json"] = {
        "surum": SURUM,
        "uretildi": _dizge(uretildi),
        "kaynak": "site" if secilen else "en-yeni",
        "haberler": one,
        "analizler": a_ozet[:ONE_CIKAN_SAYISI],
    }

    # SURUM BILDIRIMI. Istemci ilk bunu okuyor: hangi beslemeler var,
    # kac sayfa, ne zaman uretildi.
    cikti[f"{ONEK}/surum.json"] = {
        "surum": SURUM,
        "uretildi": _dizge(uretildi),
        "onek": ONEK,
        "sayfa_boyu": SAYFA_BOYU,
        "beslemeler": {
            "haber": {
                "liste": f"{ONEK}/haber/sayfa-1.json",
                "sayfa_sayisi": len(sayfala(h_ozet)),
                "kayit": len(h_ozet),
            },
            "analiz": {
                "liste": f"{ONEK}/analiz/sayfa-1.json",
                "sayfa_sayisi": len(sayfala(a_ozet)),
                "kayit": len(a_ozet),
            },
            "piyasa": {"dosya": f"{ONEK}/piyasa.json"},
            "takvim": {
                "dosya": f"{ONEK}/takvim.json",
                "kayit": len(cikti[f"{ONEK}/takvim.json"]["ogeler"]),
            },
            "varlik": {
                "dizin": f"{ONEK}/varlik.json",
                "kayit": cikti[f"{ONEK}/varlik.json"]["toplam"],
            },
            "arama": {
                "dosya": f"{ONEK}/arama.json",
                "kayit": cikti[f"{ONEK}/arama.json"]["toplam"],
            },
            "senaryo": {
                "liste": "/api/senaryo/hepsi",
                "kurallar": (f"{ONEK}/senaryo-kurallari.json"
                             if uyelik_html else None),
                "yazma_ucu": "/api/senaryo",
                "statik": False,
            },
            "one_cikan": {"dosya": f"{ONEK}/one-cikan.json"},
            # Canli tel akisi STATIK DEGIL: worker ucundan geliyor ve
            # on dakikada bir tazeleniyor. Besleme onu kopyalamiyor,
            # yalnizca adresini bildiriyor -- kopyalamak insa aninda
            # donmus bir "canli" akis olurdu.
            "tel": {"uc": "/api/tel", "durum": "/api/tel/durum",
                    "statik": False},
        },
    }
    return cikti
