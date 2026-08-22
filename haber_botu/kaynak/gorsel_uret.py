"""Konu gorseli uretir -- KAVRAM cizer, OLAY CIZMEZ.

NEDEN GEREKLI
-------------
Fotograf havuzu 44 konuda 318 gorsel tasiyor ve tekrar tavani (8)
devreye girince haberlerin dortte biri gorselsiz kaliyor. Havuzu
buyutmek de asil sorunu cozmuyor: havuz KONU duzeyinde, yani
"Jeopolitik" havuzundaki Moskova fotografi Yemen haberinin gorseli
degil. Genel bir fotograf belirli bir haberin kendisi olamaz.

EN ONEMLI KURAL: GERCEK OLAY VE GERCEK KISI CIZILMEZ
----------------------------------------------------
Bu sitenin butun degeri "hicbir sey uydurulmaz" iddiasinda. Fotogercekci
bir "Fed toplantisi" ya da "Hurmuz'da tanker" gorseli uretmek, GERCEK
BIR OLAYIN SAHTE GORUNTUSUNU uretmek demektir -- ve bu, sitenin var
olma sebebiyle dogrudan celisir.

Fark, kullanicinin ornek olarak verdigi gorselde de gorunuyor: alisveris
sepeti + inen grafik bir KAVRAM anlatimi, bir olayin fotografi degil.
Kimse onu "bu gercekten oldu" diye okumaz.

Bu yuzden istem SABIT BIR KALIPTAN kuruluyor ve haber basligini
KULLANMIYOR:

    * haber basligi istemde GECMIYOR    -> olay canlandirilamaz
    * "photo", "realistic", "news"      -> yasakli sozcukler
    * kisi, yuz, logo, marka            -> yasak
    * her gorsel ETIKETLENIYOR          -> "yapay zeka ile üretilmiş"

Basligi isteme koymak en kolay yoldu ve tam da yapilmamasi gereken sey:
"Iran limanina saldiri" basligindan uretilen gorsel, olmamis bir
saldirinin goruntusu olur.

MALIYET
-------
Workers AI gunde 10.000 noron ucretsiz veriyor; `flux-1-schnell` ile
bir gorsel ~57 noron, yani ~175 gorsel/gun. Gunde ~120 haber
yayimlaniyor -- kota yetiyor ve site zaten bu hesabi metin icin
kullaniyor.

GORSEL FOTOGRAFIN YERINE GECMIYOR
---------------------------------
Once gercek fotograf, sonra olcum grafigi, en sonda uretilen kavram
gorseli. Sirasi bilincli: gercek olan her zaman uretilene tercih
edilir.
"""

from __future__ import annotations

import base64
import hashlib
import os
import pathlib
import re

import httpx

KOK = pathlib.Path(__file__).resolve().parent.parent.parent
HEDEF = KOK / "site" / "statik" / "foto" / "uretilen"

MODEL = "@cf/black-forest-labs/flux-1-schnell"
ZAMAN_ASIMI = 90.0

#: Konu -> gorsel KAVRAMI. Olay degil, kavram.
#:
#: Her biri soyut ya da genel bir sahne: bir olayi, bir kisiyi ya da
#: bir yeri temsil etmiyor. "Enflasyon" icin market sepeti + yukselen
#: cizgi -- bu bir fotograf iddiasi degil, bir anlatim.
KONU_KAVRAMI = {
    "Enflasyon": "a shopping basket with everyday groceries beside a "
                 "rising line chart",
    "Para politikası": "a stylised central bank building facade with an "
                       "abstract interest rate curve",
    "Enerji": "abstract oil barrels and a pipeline silhouette with a "
              "price line",
    "Borsa": "an abstract stock index board with candlestick shapes",
    "Döviz": "abstract currency symbols over a exchange rate line chart",
    "Dış ticaret": "stylised shipping containers and a cargo crane "
                   "silhouette",
    "İstihdam ve ücret": "abstract human figures forming a bar chart",
    "Altın ve emtia": "stacked gold bars beside an abstract price line",
    "Kripto varlıklar": "abstract blockchain cubes with a volatile line "
                        "chart",
    "Bankacılık": "a stylised bank vault door with abstract coin stacks",
    "Konut ve kira": "simple house silhouettes forming a bar chart",
    "Tarım ve gıda": "wheat stalks and a grain silo silhouette with a "
                     "price line",
    "Jeopolitik": "an abstract world map with shipping lanes and a "
                  "commodity price line",
    "Vergi ve kamu maliyesi": "an abstract government ledger with coin "
                              "stacks",
    "Şirket haberleri": "abstract office towers with a quarterly bar "
                        "chart",
    "Turizm": "a stylised airplane silhouette and hotel building with a "
              "visitor count bar chart",
    "Piyasa düzenlemesi": "abstract balance scales beside a stylised "
                          "rulebook and a market line chart",
    "Düzenleme": "abstract balance scales beside a stylised rulebook and "
                 "a market line chart",
}

#: Her isteme eklenen SABIT kisim.
#:
#: "editorial illustration", "flat vector", "no text" -- ucu birlikte
#: fotogercekcilikten uzaklastiriyor. "no people, no faces, no logos"
#: gercek kisi ve markayi disarida tutuyor.
STIL = ("editorial flat vector illustration, minimal geometric shapes, "
        "muted teal and slate colour palette, clean background, "
        "no text, no letters, no numbers, no people, no faces, "
        "no logos, no brand marks, not photorealistic, not a photograph")

#: Uretilen gorselin altinda GORUNMESI ZORUNLU etiket.
#:
#: Kaldirilamaz: uretilmis bir gorseli fotograf gibi sunmak, sitenin
#: kaynak seffafligi ilkesinin ihlali olur. Fotograflarda CC atfi nasil
#: zorunluysa burada da bu etiket zorunlu.
ETIKET = "Görsel: Netaris tarafından yapay zeka ile üretilmiş kavram çizimi"

#: Istemde ASLA gecmemesi gereken sozcukler.
#:
#: Kalip sabit oldugu icin normalde gecmezler; bu liste bir SON
#: KONTROL. Ileride kalip degistirilirse fotogercekcilige kayis burada
#: yakalanir.
YASAK = ("photo", "photograph", "photorealistic", "realistic", "render",
         "news footage", "portrait", "face", "person", "logo")


def istem(konu: str) -> str:
    """Konudan istem kurar. Haber basligi KULLANILMAZ.

    Basligi isteme koymak en kolay yoldu ve tam da yapilmamasi gereken
    sey: "Iran limanina saldiri" basligindan uretilen gorsel, olmamis
    bir saldirinin goruntusu olur.
    """
    kavram = KONU_KAVRAMI.get(konu)
    if not kavram:
        return ""
    return f"{kavram}, {STIL}"


#: "no X" / "not X" / "not a X" -- OLUMSUZ kullanim.
#:
#: Kalibin kendisi bu sozcuklerin cogunu OLUMSUZ kullaniyor
#: ("not photorealistic", "no people"). Once sozcugun onundeki 5
#: karaktere bakiliyordu ve iki yerde yaniliyordu:
#:
#:     "not a photograph"   -> pencere "ot a " goruyor, olumsuzu KACIRIYOR
#:     "photorealistic"     -> icindeki "realistic" ayri sozcuk saniliyor
#:
#: Ikisi de kendi kalibimizi reddediyordu. Simdi olumsuz obekler once
#: METINDEN CIKARILIYOR, kalanda sozcuk siniri ile araniyor -- yani
#: "photorealistic" icindeki "realistic" artik eslesmiyor, cunku
#: onunde sozcuk siniri yok.
_OLUMSUZ = re.compile(r"\b(?:no|not)\s+(?:an?\s+)?[a-z-]+", re.I)


def istem_guvenli(p: str) -> bool:
    """Istemde fotogercekcilige kayis var mi -- son kontrol."""
    kalan = _OLUMSUZ.sub(" ", p.lower())
    return not any(re.search(r"\b" + re.escape(y), kalan) for y in YASAK)


def uret(konu: str, hesap: str = "", jeton: str = "") -> pathlib.Path | None:
    """Konu icin gorsel uretir. Basarisizsa None -- hat kirmizi DONMEZ.

    Ayni konu icin ayni dosya adi: istem sabit oldugu icin her cagri
    ayni kavrami uretiyor ve her koşuda yeniden uretmek kota israfi
    olurdu. Dosya varsa dogrudan donuyor.
    """
    p = istem(konu)
    if not p or not istem_guvenli(p):
        return None
    # `.strip()` ZORUNLU -- suslemesi degil, calismasi icin.
    #
    # GitHub gizli degeri panodan alirken sonuna satir sonu takilabiliyor
    # ve h11 baslik degerinde bosluk KABUL ETMIYOR:
    #
    #     LocalProtocolError: Illegal header value b'***'
    #
    # (`***` GitHub'in maskesi; asil bilgi "Illegal header value".)
    # Wrangler ayni gizli degerle sorunsuz calisiyor cunku onu kendi
    # kirpiyor -- bu yuzden eksiklik bugune kadar hic gorunmedi.
    #
    # Ayni tuzak bu depoda bir kez yasandi ve `ai/yorumcu.py` orada
    # `.strip()` ekleyerek cozdu. Yeni dosya o deseni izlemeyince ayni
    # hata ikinci kez cikti.
    hesap = (hesap or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")).strip()
    jeton = (jeton or os.environ.get("CLOUDFLARE_API_TOKEN", "")).strip()
    if not (hesap and jeton):
        return None

    ad = "kavram-" + hashlib.sha1(
        (konu + STIL).encode("utf-8")).hexdigest()[:10] + ".png"
    hedef = HEDEF / ad
    if hedef.exists():
        return hedef

    # HATA SEBEBI YAZILIYOR -- eskiden yazilmiyordu ve bir koşu bosa
    # gitti.
    #
    # Once yalnizca `type(e).__name__` basiliyordu ("HTTPStatusError").
    # O ad, 401 (jeton yanlis) ile 403 (jetonun Workers AI izni yok)
    # arasindaki farki GIZLIYOR -- ve iki durumun cozumu tamamen farkli.
    # Cloudflare sebebi govdede duz Turkce/Ingilizce yaziyor; onu
    # basmamak, elimizdeki tek ipucunu atmak demekti.
    #
    # Jeton govdede YANKILANMIYOR; Cloudflare hata metni kimlik bilgisi
    # tasimiyor.
    try:
        y = httpx.post(
            f"https://api.cloudflare.com/client/v4/accounts/{hesap}"
            f"/ai/run/{MODEL}",
            headers={"Authorization": f"Bearer {jeton}"},
            json={"prompt": p, "steps": 4},
            timeout=ZAMAN_ASIMI)
    except httpx.HTTPError as e:
        print(f"  görsel üretilemedi ({konu}): ağ hatası "
              f"{type(e).__name__}: {e}")
        return None
    if y.status_code != 200:
        print(f"  görsel üretilemedi ({konu}): HTTP {y.status_code}")
        print(f"    yanıt: {y.text[:400]}")
        if y.status_code in (401, 403):
            print("    -> CLOUDFLARE_API_TOKEN'ın 'Workers AI: Read' "
                  "izni olmalı. Dağıtım jetonunda bu izin YOK; "
                  "Cloudflare panelinden jetona eklenmeli.")
        return None
    try:
        d = y.json()
    except ValueError:
        print(f"  görsel üretilemedi ({konu}): yanıt JSON değil")
        print(f"    ilk baytlar: {y.content[:80]!r}")
        return None

    # IKI ZARF DA KABUL EDILIYOR.
    #
    # REST ucu her seyi `{"result": {...}, "success": true}` icine
    # sariyor ve goruntu `result.image` altinda base64 duruyor. Ama
    # zarf modele gore degisebiliyor ve YANLIS ALAN ADI, koşunun
    # tamamini sessizce bosa cikarir -- 18 istek atilir, sifir dosya
    # yazilir ve hicbir hata gorunmez.
    #
    # Iki yeri de denemek bir satir; bir CI koşusunu geri kazaniyor.
    ham = (d.get("result") or {}).get("image") or d.get("image")
    if not ham:
        print(f"  görsel yanıtı boş ({konu}): alanlar = "
              f"{sorted(d)[:6]}")
        return None
    try:
        veri = base64.b64decode(ham)
    except (ValueError, TypeError):
        print(f"  görsel çözülemedi ({konu})")
        return None

    HEDEF.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(veri)
    return hedef


def dosyasi(konu: str) -> str:
    """Konunun URETILMIS gorseli varsa site yolu, yoksa bos.

    Uretim YAPMIYOR -- yalnizca diskte hazir olani buluyor. Boylece
    `insa.py` her koşuda ag istegi atmiyor ve gorsel uretimi ayri bir
    adim olarak kaliyor.
    """
    if konu not in KONU_KAVRAMI:
        return ""
    ad = "kavram-" + hashlib.sha1(
        (konu + STIL).encode("utf-8")).hexdigest()[:10] + ".png"
    return f"/statik/foto/uretilen/{ad}" if (HEDEF / ad).exists() else ""


def main() -> int:
    """Eksik kavram gorsellerini uretir.

    AYRI ADIM, insa sirasinda DEGIL. Iki sebep:

    1. Gorsel uretimi ag istegi ve saniyeler suruyor; her insa
       koşusunda tekrarlamak anlamsiz -- kalip sabit, sonuc ayni.
    2. Uretilen gorsel YAYIMLANMADAN ONCE GORULMELI. Bu adim once
       dosyalari depoya birakiyor, insa onlari ancak varsa kullaniyor.
       Yani hicbir gorsel goz onunden gecmeden sayfaya cikmiyor.
    """
    eksik = [k for k in KONU_KAVRAMI if not dosyasi(k)]
    if not eksik:
        print(f"{len(KONU_KAVRAMI)} kavram görselinin hepsi hazır.")
        return 0
    print(f"{len(eksik)} kavram görseli üretilecek "
          f"({len(KONU_KAVRAMI) - len(eksik)} hazır).")
    if not (os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
            and os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()):
        print("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN tanımlı "
              "değil -- görsel üretilemez.")
        return 1
    uretilen = 0
    ustuste = 0
    for k in eksik:
        if uret(k) is not None:
            uretilen += 1
            ustuste = 0
            print(f"  üretildi: {k}")
            continue
        # ART ARDA UC BASARISIZLIKTA DURULUYOR.
        #
        # Jeton yanlissa ya da kota bittiyse kalan 15 istek de ayni
        # sebeple basarisiz olur. Denemeye devam etmek iki sey yapar:
        # kaydi ayni hata mesajiyla doldurur ve gercek sebebi ekranin
        # yukarisina iter. Ilk uc satir zaten sebebi soyluyor.
        ustuste += 1
        if ustuste >= 3:
            print(f"  art arda {ustuste} başarısızlık -- duruluyor "
                  f"({len(eksik) - eksik.index(k) - 1} konu denenmedi).")
            break
    print(f"\n{uretilen}/{len(eksik)} görsel üretildi.")
    # HIC URETILEMEDIYSE HATA. Sessizlik basari sayilmaz.
    #
    # Ilk koşu tam bunu yasadi: uretim basarisiz oldu, adim "0 ile
    # cikti", is akisi yesil gorundu ve depoya hicbir sey dusmedi --
    # yani "calisti" gibi duran bir koşu hicbir sey yapmamisti.
    #
    # Tek tuk basarisizlik hata degil (bir konu atlanir, sayfa gorselsiz
    # cikar) ama HEPSININ basarisiz olmasi yapisal bir sorundur: yanlis
    # jeton, eksik izin, kota. Onu gormek icin koşunun KIRMIZI donmesi
    # gerekiyor.
    if uretilen == 0:
        print("HİÇBİR görsel üretilemedi -- yukarıdaki sebebe bakın.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
