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
    # BINA ISTENMIYOR. Ilk deneme "central bank building facade"
    # istedi ve model alinliga "CENTRAL BANK" YAZDI -- istemde
    # "no text" oldugu halde. Bina kalibi egitim verisinde tabelayla
    # birlikte geliyor; tabelayi yasaklamak yerine BINAYI cikarmak
    # daha guvenilir. Ayrica Ingilizce bir tabela Turkce bir sitede
    # zaten yanlis, ustelik belirli bir kurumu ima ediyordu.
    "Para politikası": "a large abstract coin balanced on a fulcrum "
                       "beside simple geometric column shapes",
    # "price line" cikarildi: ilk deneme "Price" sozcugunu yazdi ve
    # kompozisyon kocaman bos bir alanda kucucuk ogeler oldu.
    "Enerji": "a group of oil barrels and a pipeline silhouette filling "
              "the frame",
    # GRAFIK OLMAMALI. Ilk deneme "stock index board with candlestick
    # shapes" istedi ve TAMAMEN SAHTE BIR GRAFIK cikti: eksenli,
    # mumlu, yukselen. Bu site GERCEK olcum grafikleri yayimliyor;
    # yaninda uydurma bir grafik, okurun ikisini ayirmasini imkansiz
    # kilar. Kavram artik grafik degil, bir NESNE.
    "Borsa": "a large abstract bull silhouette made of simple geometric "
             "shapes",
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
ONAYLI: dict[str, str] = {
    "Enflasyon":
        "538cb04d3fd4c37c9c3043600333cc7245511c898fa08aff1c464f08f9ad3b9d",
    "Döviz":
        "06619116c6e2a697ffcc7dea10303b30f0970a686fb645c98ca55333aacc05ab",
    "Dış ticaret":
        "bd39641b7d4dab2ed03b427fd8b088a6396ffe5e85bd9ffd792aeea5119f19e6",
    "İstihdam ve ücret":
        "1a828cbc4155c29c1ab6537221001159e3b3b5c60f19813f9793cfd791eff090",
    "Altın ve emtia":
        "23f0878bb7e0de82ab47dfaff0b7431e5211ba071404f30475e9ccc2f4daad25",
    "Kripto varlıklar":
        "0326bd27a2977ae6bfcfc315798bcd46be193efa885a740f2c7de243085030b2",
    "Bankacılık":
        "6c088967eeda3e9bce5174d98c217ea7191fbe82c5d2fb269d2a017f8fddd621",
    "Konut ve kira":
        "b692d79071a25224ab3fa9404e3deb87d28975b72a0fbfa061268c57d55298bd",
    "Tarım ve gıda":
        "ba05109030ab5451ef5ac0311db7f5e13fdf604582f609bee0042efdd3736096",
    "Jeopolitik":
        "8559c7b0c2c71b54b776cfbdfffb3ba21e66748cb1c18aaf6a80efd3f447e318",
    "Vergi ve kamu maliyesi":
        "4021e8b628dc5e33f704fa7af2a21625b6e942ef987f80a64a82112f09576693",
    "Şirket haberleri":
        "2c8ba517ef21d5fd3bb2a35c63916cc83df5eee9f442dd9a9636a252e341d651",
    "Turizm":
        "c5f3341ef9a1779ef9a0483f884f350d3a7a4300389d8a4c804d322897b8ccb6",
    "Piyasa düzenlemesi":
        "398a1038e60449dc0b2ea1b989e49a1b34370a69ae8b67b220d1f6ac20133bd4",
    "Düzenleme":
        "2be8e69eec3448c4364eec205aaea833ffc1b19d5f02133e55263f9c3ad04a0f",
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
    """Konunun dosya adi (uzantisiz).

    Istem sabit oldugu icin ayni konu her cagrida ayni adi uretiyor ve
    dosya varsa yeniden uretilmiyor.
    """
    return "kavram-" + hashlib.sha1(
        (konu + STIL).encode("utf-8")).hexdigest()[:10]


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
