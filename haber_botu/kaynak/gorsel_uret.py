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

#: Konu -> gorsel KAVRAMI. Olay degil, kavram; ve NESNE, grafik degil.
#:
#: Her biri soyut ya da genel bir sahne: bir olayi, bir kisiyi ya da
#: bir yeri temsil etmiyor.
#:
#: IKI KURAL, IKISI DE OLCULMUS BIR HATADAN GELIYOR
#: -----------------------------------------------
#: 1. KAVRAM GRAFIK OLAMAZ. Ilk uretimde "Borsa" icin "stock index
#:    board with candlestick shapes" istendi ve tamamen SAHTE BIR
#:    GRAFIK cikti: eksenli, mumlu. Bu site gercek olcum grafikleri
#:    yayimliyor (`grafik.py`); yaninda uydurma bir grafik, okurun
#:    ikisini ayirmasini imkansiz kilar.
#:
#: 2. KAVRAM YONLU OLAMAZ. Ikinci uretimde Borsa icin bir BOGA
#:    silueti geldi -- temiz, metinsiz, grafiksiz. Yine de reddedildi:
#:    boga yukselen piyasa demek ve bu gorsel Borsa konulu 759 haberin
#:    HEPSINDE gorunuyor, bir kismi dusus haberi.
#:
#:    Ayni kusur ilk turda onaylanan bes cizimde de vardi (yukselen ok
#:    ya da yukselen cizgi): "Enflasyon %31,75'e geriledi" haberinin
#:    yaninda buyuk bir yukselen ok yanlis duruyor.
#:
#:    Konu basina TEK gorsel kullanildigi surece yonlu sembol
#:    kullanilamaz. Cozum: kavramlar NESNE, yon tasimiyor.
KONU_KAVRAMI = {
    "Enflasyon": "a shopping basket filled with everyday groceries",
    # BINA VE MADENI PARA ISTENMIYOR -- ikisi de denendi, ikisi de
    # kendi sorununu getirdi:
    #   "central bank building facade" -> alinliga "CENTRAL BANK" YAZDI
    #   "a large abstract coin"        -> paranin ustune BITCOIN isareti
    # Ikisi de istemde acikca yasakliydi ("no text", "no brand marks").
    # Kalip egitim verisinde o ayrintiyla birlikte geliyor; ayrintiyi
    # yasaklamak yerine KALIBI degistirmek daha guvenilir.
    "Para politikası": "a plain circular dial gauge with a single needle, "
                       "mounted on a flat panel",
    # VARIL ISTENMIYOR: uretilen goruntude varillerin ustune "OIL"
    # yazdi. Ucuncu tur, "no text" istemde yaziliyken ucuncu metin
    # kazasi. Desen artik kesin -- gercek hayatta USTUNDE YAZI OLAN
    # nesne, gorselde de yazi tasiyor:
    #
    #     banka binasi -> "CENTRAL BANK"    petrol varili -> "OIL"
    #     otel binasi  -> "HOTEL"           acik kitap    -> "Rule"
    #     madeni para  -> para birimi isareti
    #
    # Cozum daha fazla yasak degil: gercekte uzerinde yazi OLMAYAN
    # nesne secmek. Petrol kuyusu pompasinin ustunde yazi olmaz.
    "Enerji": "a tall oil pump jack silhouette on open ground",
    "Borsa": "an empty stock exchange hall interior with rows of plain "
             "rectangular display panels",
    # Para birimi SEMBOLU istenmiyor: "$" agirlikli bir gorsel Turkce
    # bir sitede yanlis vurgu, ayrica sembol metin gibi davraniyor.
    "Döviz": "plain banknote sheets and coin discs arranged in a fan",
    "Dış ticaret": "stylised shipping containers and a cargo crane "
                   "silhouette",
    "İstihdam ve ücret": "abstract human pictogram figures standing in a "
                         "row",
    "Altın ve emtia": "stacked gold bars and plain coin discs",
    # UCUNCU DENEME. Bu konu iki kez okunaksiz cikti:
    #
    #   "cubes interlocking to form a chain"  -> anlamsiz sekiller
    #   "lattice of hexagonal tiles"          -> duz duvar kagidi dokusu
    #
    # Ikisinin de ortak kusuru fazla SOYUT olmasi: yazi tasimiyorlar
    # ama hicbir sey de anlatmiyorlar. Kavramin somut bir NESNE olmasi
    # gerekiyor -- zincir, "blok zinciri"nin birebir karsiligi ve
    # uzerinde yazi tasimayan bir nesne.
    #
    # Ucuncu kez basarisiz olursa bu konu listeden CIKARILIR: 52 haber
    # gorselsiz kalir ve bu, anlasilmayan bir gorselden iyidir.
    "Kripto varlıklar": "a chain of interlocking metal links lying on a "
                        "flat surface",
    "Bankacılık": "a stylised bank vault door with abstract coin stacks",
    "Konut ve kira": "simple house and apartment block silhouettes in a "
                     "row",
    "Tarım ve gıda": "wheat stalks and a grain silo silhouette",
    "Jeopolitik": "an abstract world map with dotted shipping lanes",
    "Vergi ve kamu maliyesi": "an abstract government ledger with coin "
                              "stacks",
    # DUZ SILUET isteniyor: onceki deneme taninabilir bir kule
    # (One World Trade Center anteni) uretti. Gercek bir yapiyi
    # cizmek, "gercek yer canlandirilmaz" kuralinin ihlali; ustelik
    # New York silueti Turk sirket haberinin gorseli degil.
    "Şirket haberleri": "plain flat rectangular office building blocks of varying heights, simple silhouette",
    # OTEL BINASI ISTENMIYOR: uretilen goruntude binaya "HOTEL"
    # yazdi. Ucak silueti ve kiyi tepeleri yazi tasimaz.
    "Turizm": "a stylised airplane silhouette above rolling coastal hills",
    "Piyasa düzenlemesi": "abstract balance scales beside a closed "
                          "rulebook",
    # ACIK/KAPALI KITAP ISTENMIYOR: uretilen goruntude sayfaya
    # "Rule" yazdi ve palet de kaydi. Terazi tek basina yeterli --
    # "Piyasa duzenlemesi" kavramindan da farkli kalsin diye zaten
    # ayri bir gorsel olmasi iyi.
    "Düzenleme": "a pair of abstract balance scales standing alone",
}

#: Her isteme eklenen SABIT kisim.
#:
#: "editorial illustration", "flat vector", "no text" -- ucu birlikte
#: fotogercekcilikten uzaklastiriyor. "no people, no faces, no logos"
#: gercek kisi ve markayi disarida tutuyor.
STIL = ("editorial flat vector illustration, minimal geometric shapes, "
        "muted teal and slate colour palette, clean background, "
        "no text, no letters, no numbers, no people, no faces, "
        "no logos, no brand marks, no currency symbols, "
        "no charts, no graphs, no trend lines, no arrows, "
        "no upward or downward direction, "
        "not photorealistic, not a photograph")

#: Uretilen gorselin altinda GORUNMESI ZORUNLU etiket.
#:
#: Kaldirilamaz: uretilmis bir gorseli fotograf gibi sunmak, sitenin
#: kaynak seffafligi ilkesinin ihlali olur. Fotograflarda CC atfi nasil
#: zorunluysa burada da bu etiket zorunlu.
ETIKET = "Görsel: Netaris tarafından yapay zeka ile üretilmiş kavram çizimi"

#: ONAYLI CIZIMLER -- konu -> dosyanin sha256'si.
#:
#: NEDEN LISTE VAR
#: ---------------
#: Istem yeterli bir koruma DEGIL. Ilk uretimde bu olculdu: istemde
#: "no text, no letters, no numbers" yazili oldugu halde
#:
#:     Para politikasi  -> binada "CENTRAL BANK" yaziyordu
#:     Enerji           -> gorselde "Price" yaziyordu
#:     Borsa            -> tamamen SAHTE BIR GRAFIK cikti
#:
#: Ucuncusu en tehlikelisi: bu site GERCEK olcum grafikleri yayimliyor
#: ve yaninda uydurma bir grafik goruntusu, okurun ikisini ayirmasini
#: imkansiz kilar.
#:
#: Yani modelin olumsuz talimatlara uydugu VARSAYILAMAZ ve "uretilen
#: gorsel yayimlanmadan once gorulmeli" bir aliskanlik olarak
#: birakilamaz. Liste onu KURAL yapiyor: hash'i burada olmayan dosya
#: `dosyasi()` tarafindan DONDURULMEZ, yani sayfaya cikamaz.
#:
#: LISTEYE NASIL EKLENIR
#: ---------------------
#: Cizime BAKILIR, sonra hash'i buraya yazilir. Sirasi bu; hash'i
#: bakmadan eklemek listeyi anlamsiz kilar.
#:
#:     python haber_botu/kaynak/gorsel_uret.py --hash
#: Ucuncu turda 13 cizim kabul, 5 red. Redler asagida `KONU_KAVRAMI`
#: icinde tek tek gerekcelendirildi.
ONAYLI: dict[str, str] = {
    "Enflasyon":
        "b3a237ba68bbabd7b312f10c1118c1d184890e6730248f51f30019f3da088ab3",
    "Para politikası":
        "1fa298f8fc7a80d92ce3f1d3f5511a3a5d21a3034b8eeb5c79c6cdc95db300bf",
    "Borsa":
        "378f7e41f11fce0a481d855807da4090b59b97bb00d90b1572b1390a84cad478",
    "Döviz":
        "5136acd4a89c91eb1d9ab3550a14c8af3902f062219d75a0477f041c170ab47e",
    "Dış ticaret":
        "266ed061b5865b619064d7aa120a399c553ff9d1fe8e8c450974153fbc69ceed",
    "İstihdam ve ücret":
        "96608237c6d4a66c353ce90766f743c0b6e2fa6da590a8f3d28a0013da76a0dc",
    "Altın ve emtia":
        "93620ec57dc32ce1476c216de419b2a796eff12d030a451e14284679a681b198",
    "Bankacılık":
        "b122a5bce921e2fbae3a4682c44bc13c06a151ee583c64fe41799bf4a1deb487",
    "Konut ve kira":
        "4402a09e716cb6e39b2037525fc506e888d0c9a9e73a6d924a218e596d88b816",
    "Tarım ve gıda":
        "92833f14802952dd2491df8bac3250abf9b022a466611da13ca05d8186b59a25",
    "Jeopolitik":
        "9be4971355c3aafc582f5821bffd6e7e7e5688f3f17623da1af5af7ee04b2a75",
    "Piyasa düzenlemesi":
        "de626d798785ed147478d4b9bb83682ac21b46f1037293562bc3913ee67baa0c",
    "Vergi ve kamu maliyesi":
        "c5666fe09d8b8716206e5bae0d8df979d57d172bb3f29de3e3dd829c9db7045c",
    # Dorduncu turda eklendi: yazi tasimayan nesneye gecis calisti.
    "Enerji":
        "c3a0a2cd21462d7cf345aa2dd421bb6194a2e89e26f472359e1441293a439cc4",
    "Turizm":
        "06bf92f753bc5fcaba5c1050ed202af307080263eba94f505ac48ff412eec5df",
    "Şirket haberleri":
        "62ab4237d8fd7a5a573526ba22dc62b32f844125151fbc071ddcb1d6f7308729",
    "Düzenleme":
        "426799e4fe32969beafa5edc65cab63d2bad89e9b2c888411fb34602c2f06b02",
}

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


def _stem(konu: str) -> str:
    """Konunun dosya adi (uzantisiz) -- ISTEMDEN turuyor.

    ISTEMIN TAMAMI ADA GIRIYOR (konu + kavram + stil). Once yalnizca
    konu ve stil giriyordu ve bu SESSIZ BIR TUZAKTI: kavram metni
    degistiginde dosya adi degismiyor, `_mevcut` eski dosyayi buluyor
    ve yeni istem HIC CALISMIYORDU. Yani "istemi duzelttim" diyen bir
    degisiklik hicbir seyi degistirmiyordu; ancak dosyayi elle silmek
    ise yariyordu.

    Simdi farkli istem = farkli dosya adi = eski onay hash'i gecersiz.
    Yani istemi degistiren kisi, sonucuna BAKMAK ZORUNDA kaliyor.
    """
    tohum = konu + KONU_KAVRAMI.get(konu, "") + STIL
    return "kavram-" + hashlib.sha1(
        tohum.encode("utf-8")).hexdigest()[:10]


def _uzanti(veri: bytes) -> str:
    """Baytlardan gercek bicimi bulur.

    UZANTI VARSAYILMAZ. Ilk uretim dosyalari `.png` adiyla yazdi ama
    icerik JPEG'di -- `flux-1-schnell` JPEG donduruyor. Sunucu tipi
    UZANTIDAN belirledigi icin 18 dosya `image/png` basligiyla JPEG
    baytlari servis ediyordu.

    Simdilik zararsiz (tarayici icerigi kokluyor) ama `nosniff`
    basligi eklendigi gun butun bu gorseller GORUNMEZ olurdu -- ve o
    an sebebi bulmak cok zor.
    """
    if veri[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if veri[:2] == b"\xff\xd8":
        return ".jpg"
    if veri[:4] == b"RIFF" and veri[8:12] == b"WEBP":
        return ".webp"
    return ""


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

    var = _mevcut(konu)
    if var is not None:
        return var

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

    uz = _uzanti(veri)
    if not uz:
        print(f"  görsel tanınmayan biçimde ({konu}): "
              f"{veri[:8]!r}")
        return None

    HEDEF.mkdir(parents=True, exist_ok=True)
    hedef = HEDEF / (_stem(konu) + uz)
    hedef.write_bytes(veri)
    return hedef


def _mevcut(konu: str) -> pathlib.Path | None:
    """Konunun diskteki cizimi -- uzantisi ne olursa olsun."""
    if konu not in KONU_KAVRAMI:
        return None
    kok = _stem(konu)
    for uz in (".jpg", ".png", ".webp"):
        p = HEDEF / (kok + uz)
        if p.exists():
            return p
    return None


def onayli_mi(konu: str) -> bool:
    """Diskteki cizim ONAYLI listesindeki dosya mi?

    Istem yeterli bir koruma degil: ilk uretimde "no text" yazili
    oldugu halde iki gorselde metin cikti, birinde de sahte bir grafik.
    Bu yuzden "yayimlanmadan once gorulmeli" bir aliskanlik degil,
    burada bir KURAL.
    """
    p = _mevcut(konu)
    if p is None:
        return False
    beklenen = ONAYLI.get(konu)
    if not beklenen:
        return False
    return hashlib.sha256(p.read_bytes()).hexdigest() == beklenen


def dosyasi(konu: str) -> str:
    """Konunun ONAYLI cizimi varsa site yolu, yoksa bos.

    Uretim YAPMIYOR -- yalnizca diskte hazir VE ONAYLI olani buluyor.
    Onaysiz bir dosya diskte dursa bile bos donuyor: boylece yeni
    uretilmis ama henuz bakilmamis bir cizim sayfaya CIKAMIYOR.
    """
    if not onayli_mi(konu):
        return ""
    p = _mevcut(konu)
    return f"/statik/foto/uretilen/{p.name}" if p else ""


def main() -> int:
    """Eksik kavram gorsellerini uretir.

    AYRI ADIM, insa sirasinda DEGIL. Iki sebep:

    1. Gorsel uretimi ag istegi ve saniyeler suruyor; her insa
       koşusunda tekrarlamak anlamsiz -- kalip sabit, sonuc ayni.
    2. Uretilen gorsel YAYIMLANMADAN ONCE GORULMELI. Bu adim once
       dosyalari depoya birakiyor, insa onlari ancak varsa kullaniyor.
       Yani hicbir gorsel goz onunden gecmeden sayfaya cikmiyor.
    """
    # EKSIK OLCUTU `_mevcut`, `dosyasi` DEGIL.
    #
    # `dosyasi` onaysiz cizim icin de bos donuyor. Olcut o olsaydi,
    # uretilmis ama HENUZ BAKILMAMIS bir cizim "eksik" sayilir ve
    # uzerine yeniden yazilirdi -- yani inceleme altindaki dosya her
    # koşuda degisirdi ve onaylanmasi imkansiz hale gelirdi.
    # OKSUZ DOSYALAR SILINIYOR.
    #
    # Kavram degisince `_stem` yeni bir ad uretiyor ve eski dosya
    # diskte OKSUZ kaliyor: hicbir konu ona isaret etmiyor, hicbir
    # sayfada gorunmuyor, ama depoda yer kapliyor ve bir sure sonra
    # "bu neydi" sorusuna donuyor. Elle temizlemek unutulur.
    gecerli = {_stem(k) for k in KONU_KAVRAMI}
    if HEDEF.exists():
        oksuz = [p for p in HEDEF.glob("*") if p.stem not in gecerli]
        for p in oksuz:
            p.unlink()
        if oksuz:
            print(f"{len(oksuz)} öksüz çizim silindi "
                  f"(kavramı değişmiş, artık kullanılmıyor).")

    eksik = [k for k in KONU_KAVRAMI if _mevcut(k) is None]
    bekleyen = [k for k in KONU_KAVRAMI
                if _mevcut(k) is not None and not onayli_mi(k)]
    if bekleyen:
        print(f"{len(bekleyen)} çizim ONAY BEKLİYOR "
              f"(sayfaya çıkmıyor): {', '.join(bekleyen)}")
        print("  bakıp onaylamak için: "
              "python haber_botu/kaynak/gorsel_uret.py --hash")
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
    print("\nYeni çizimler ONAY BEKLİYOR ve sayfaya çıkmayacak. "
          "Bakıp onaylamak için: --hash")
    return 0


def hashleri_yaz() -> int:
    """Diskteki cizimlerin hash'lerini `ONAYLI` bicimiyle basar.

    SIRA: once cizime BAKILIR, sonra hash'i listeye yazilir. Bakmadan
    yapistirmak listeyi anlamsiz kilar -- listenin tek isi, bakilmis
    olani bakilmamis olandan ayirmak.
    """
    for k in KONU_KAVRAMI:
        p = _mevcut(k)
        if p is None:
            print(f"    # {k}: dosya yok")
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        durum = "onaylı" if ONAYLI.get(k) == h else "ONAY BEKLİYOR"
        print(f"    # {p.name}  ({durum})")
        print(f"    {k!r}:\n        {h!r},")
    return 0


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--hash", action="store_true",
                     help="diskteki çizimlerin hash'lerini bas")
    _a = _ap.parse_args()
    raise SystemExit(hashleri_yaz() if _a.hash else main())
