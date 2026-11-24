"""Cekilen mali tablolarin DEFTERI -- bir kez cekilir, cok kez okunur.

NEDEN VAR
---------
Ayni veri hatta IKI KEZ cekiliyordu ve ikincisi kaynagi kapatiyordu.

OLCULDU (2026-11-21, bilanco kosusu #117):

    sayfa adimi   `donem_getir` -> sirket basina 3 istek   (ONCE kosar)
    veri adimi    `ara_donem`   -> sirket basina 3 istek   (SONRA kosar)

Ikisi AYNI sayfalari istiyor. Kosu gunlugu sonucu yaziyor:

    -> 60 sirket olculdu, 12 atlandi
       KAYNAK KAPANDI -- 8 ardisik red. Kalan istekler YAPILMIYOR.
    Bilisim: KAYNAK REDDEDIYOR, atlandi (veri eksikligi degil)
    Finans: KAYNAK REDDEDIYOR, atlandi (veri eksikligi degil)
    ... 9 sektorun hepsi
    okunamayan istek: 71

Yani on bir sektorun IKISI tazelendi, dokuzu kaynak kapandigi icin
onceki haliyle kaldi. Kapanmanin sebebi veri yoklugu degil, ayni
veriyi iki kez istemek.

Hat kendi yorumunda bunu zaten biliyordu -- `uret_bilanco.py`:
"kaynak butcesi sayfa adimina birakiliyor". Butceyi bolusmek yerine
IKINCI ISTEGI ORTADAN KALDIRMAK dogru cozum: veri adimi cektigini
buraya yaziyor, sayfa adimi agdan degil BURADAN okuyor.

NE SAKLANIYOR -- TURETILEN DEGIL, CEKILEN
-----------------------------------------
Defter `ara_donem`in DONDURDUGU yapiyi saklıyor; `donemi_kur`dan
gecmis halini DEGIL. Sebep: turetilmis bir kopya saklanirsa kural
(`donemi_kur`, `donem_toplami`, isaret cevirmeleri) iki yerde
uygulanmis olur ve biri degisince oteki sessizce eskir. Bu depoda
ayni hata dort kopyali `_degisim` hesabinda yasandi.

Ham cekim saklandiginda butun turetme TEK yerde kaliyor: okuyan
taraf `donemi_kur`u aynen cagiriyor, defter yalnizca AGI yerine
geciyor.

ETIKET SUZGECI -- NEDEN VE NEYE GORE
------------------------------------
Kaynak bilanco sayfasinda 54, nakit akisinda 35 satir veriyor ve
hat bunlarin 17'sini kullaniyor. Tamamini saklamak sirket basina
21 KB, 384 sirkette 8 MB demekti; suzulmus hali 3,5 KB.

Suzgec ESLESME ve OZDESLIK_ETIKETLERI'nden TURETILIYOR, elle
yazilmiyor. Yeni bir eslesme eklendigi an suzgec genisler ve
`SEMA` degisir; eski kayitlar gecersiz sayilir ve yeniden cekilir.
Elle yazilmis bir liste, eslesme buyudugunde sessizce eksik alan
donduruirdu.

ALT CIZGILI ANAHTARLAR BLOK LISTESIYLE ELENIYOR, BEYAZ LISTEYLE
DEGIL. Yeni bir ust veri anahtari (`_mali` gibi) eklenirse defter
onu KENDILIGINDEN tasir; beyaz liste olsa yeni anahtar sessizce
dusurdu ve okuyan taraf eksik ust veriyle calisirdi. Tek istisna
`_ham_bilanco`: ceyreklik tam seri tasiyor (buyuk) ve yalnizca
cekim aninda kosan ozdeslik denetimi icin gerekiyor.

NE ZAMAN GECERSIZ
-----------------
Kayit su durumlarda YOK sayilir ve cagiran taraf aga duser:

    * dosya yok ya da JSON bozuk
    * `sema` degismis (eslesme buyudu/degisti)
    * `ceyrek` istenenden farkli (ara donem uzunlugu)
    * `bitis` verildi ve kayittaki donem bitisi farkli
    * kayit `OMUR_GUN`den eski
    * `_seri_bitis` yok ya da bos -- SAYFA KURMAYA YETMIYOR

SON MADDE 2026-11-24'TE EKLENDI. `_seri_bitis` olmadan "Son dort
donem" bolumu uretilemez; boyle bir kayit sunulsa sayfa bolumsuz
kurulur, goc kuyrugu onu "bolum yok" diye geri alir ve kuyruk
ASLA TUKENMEZ. Defterdeki 232 kaydin BIRI boyleydi ve sebebi
ayristiricidaki kolon kaymasiydi (bkz. `bilanco_ag._tablo`);
olcut kaydin KENDI eksikligi oldugu icin duzeltme sonrasi kayit
kendiliginden yenilenir, elle silmek gerekmez.

BIRINCIL KORUMA `bitis`: ozet hangi donemi gosteriyorsa defterin de
o donemi tasimasi gerekir. Yas ikincil -- kapanmis bir donemin
rakamlari degismez, yalnizca yeniden duzenleme (restatement)
halinde degisir ve o nadir.
"""

from __future__ import annotations

import hashlib
import io
import json
import pathlib
import time

try:
    import bilanco_ag
except ImportError:  # pragma: no cover -- paket bicimiyle cagrildi
    from kaynak import bilanco_ag

#: Defter dizini. Sirket basina bir dosya: kosu 25 sirket olcerse
#: git 25 kucuk dosya goruyor. Tek buyuk JSON olsa her kosu 1,3 MB'i
#: bastan yazar ve depo gecmisi ceyrekte on megabayt buyurdu.
KOK = pathlib.Path(__file__).resolve().parent / "bilanco_defteri"

#: Kayit bu kadar gunden eskiyse yok sayilir.
#:
#: 120 GUN: bir ceyrek (91 gun) + SPK bildirim penceresi (40 gun)
#: toplamindan kisa, yani kapanmis bir donem icin hep gecerli kalir
#: ama bir yil onceki bir kayit asla kullanilmaz. Birincil koruma
#: `bitis` esitligi; bu, onun kacirdigi yeniden duzenleme halini
#: sinirliyor.
OMUR_GUN = 120

#: Defterde tutulmayan ust veri anahtarlari.
BLOK = frozenset({"_ham_bilanco"})


def etiketler() -> frozenset[str]:
    """Defterin sakladigi kalem etiketleri -- ESLESMEDEN TURETILIYOR.

    Elle yazilmis bir liste, `bilanco_ag.ESLESME` buyudugunde
    sessizce eksik kalirdi: okuyan taraf yeni alani None gorur ve
    "kaynak vermedi" sanardi. Turetme bunu imkansiz kiliyor.
    """
    ad = {e for _, _, e in bilanco_ag.ESLESME}
    ad.add(bilanco_ag.NET_NAKIT_ETIKETI)
    ad.add(bilanco_ag.AMORTISMAN_ETIKETI)
    # CAPEX UNUTULMUSTU VE OLCUM YAKALADI (2026-11-22).
    #
    # `donemi_kur` bu etiketi SATIR ICI bir dizgeyle okuyordu, yani
    # buradan gorunmuyordu. Alti sirketin hepsinde defterden okunan
    # veride `yatirim_harcamasi` None geliyordu -- ve hicbir sey
    # hata vermiyordu, cunku alan ZATEN istege bagli.
    #
    # Bu yuzden turetme artik ADLANDIRILMIS sabitlere dayaniyor ve
    # `test_bilanco_defteri.py` iki yonu birden tutuyor: (a) AST ile
    # `donemi_kur` icinde adsiz etiket dizgesi kalmadigini, (b)
    # GERCEK bir cekim ornegi uzerinde `donemi_kur(suz(t))` ile
    # `donemi_kur(t)`nin BIREBIR ayni cikti verdigini.
    ad.add(bilanco_ag.CAPEX_ETIKETI)
    ad |= set(bilanco_ag.OZDESLIK_ETIKETLERI)
    return frozenset(ad)


def sema() -> str:
    """Etiket kumesinin parmak izi. Degisirse eski kayitlar duser."""
    ham = "\u0000".join(sorted(etiketler()))
    return hashlib.sha256(ham.encode()).hexdigest()[:16]


def yol(kod: str) -> pathlib.Path:
    return KOK / f"{str(kod).upper()}.json"


def suz(tablolar: dict) -> dict:
    """Cekimi defterde tutulacak hale indirger.

    Kalem sozlukleri etiket suzgecinden geciyor; ust veri (alt
    cizgiyle baslayan) BLOK disinda AYNEN tasiniyor.
    """
    izin = etiketler()
    cikti: dict = {}
    for ad, deger in (tablolar or {}).items():
        if ad in BLOK:
            continue
        if ad.startswith("_"):
            cikti[ad] = deger
            continue
        if isinstance(deger, dict):
            cikti[ad] = {e: d for e, d in deger.items() if e in izin}
        else:
            cikti[ad] = deger
    return cikti


def yaz(kod: str, tablolar: dict, ceyrek: int) -> pathlib.Path | None:
    """Cekimi deftere yazar. Bos cekim YAZILMAZ.

    Bos kayit yazmak, sayfa adimina "elimde veri var" demek olurdu;
    o da aga dusmeyi engeller ve sayfa hic uretilmez. Yokluk
    kaydedilmez, yoklugu kaydetmek yoklugu veri sanmaktir.
    """
    sz = suz(tablolar)
    if not any(isinstance(d, dict) and d
               for ad, d in sz.items() if not ad.startswith("_")):
        return None
    bitisler = sz.get("_seri_bitis") or []
    kayit = {
        "kod": str(kod).upper(),
        "cekildi": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ceyrek": int(ceyrek),
        "sema": sema(),
        "bitis": (bitisler[0] if bitisler else
                  ((sz.get("_mali") or {}).get("son_bitis") or "")),
        "tablolar": sz,
    }
    KOK.mkdir(parents=True, exist_ok=True)
    hedef = yol(kod)

    # ICERIK AYNIYSA DOSYAYA DOKUNULMUYOR.
    #
    # NEDEN: `cekildi` damgasi her kosuda degisiyor ve kayit her
    # kosuda yeniden yazilsa GIT 96 dosyayi degismis gorurdu --
    # icerik ayni oldugu halde. Bir ceyrekte ~60 kosu, her biri
    # ~0,5 MB fark: 30 MB depo gecmisi, hicbiri yeni bilgi
    # tasimadan.
    #
    # DAMGANIN ANLAMI DA DUZELIYOR: "en son ne zaman sorduk" degil,
    # "bu veri ne zaman GORULDU". Beslemede okura gosterilen sey de
    # tam olarak bu -- rakamin kendisi degismediyse tarihinin her gun
    # ilerlemesi, degismeyen bir veriyi her gun yenilenmis gibi
    # gostermek olurdu.
    #
    # YAS DENETIMI BOZULMUYOR: kayit `OMUR_GUN`u asinca yine
    # gecersiz sayiliyor ve o gun taze cekim yazilacak. Yani
    # degismeyen bir kayit sonsuza kadar yasamiyor.
    eski = kayit_oku(kod)
    if (eski and eski.get("sema") == kayit["sema"]
            and int(eski.get("ceyrek") or -1) == kayit["ceyrek"]
            and eski.get("tablolar") == kayit["tablolar"]):
        return hedef

    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return hedef


def kayit_oku(kod: str) -> dict | None:
    """Ham kaydi doner (gecerlilik SINAMADAN).

    ADI `kayit` DEGIL: `yaz` icindeki yerel degisken de `kayit` ve
    modul islevini GOLGELIYORDU. Golgelenen isme yapilan cagri
    "dict cagrilamaz" diye patlar -- gurultulu, ama ancak o dal
    yurundugunde. Ad ayriligi bunu imkansiz kiliyor.
    """
    p = yol(kod)
    if not p.exists():
        return None
    try:
        with io.open(p, encoding="utf-8") as f:
            k = json.load(f)
    except (ValueError, OSError):
        return None
    return k if isinstance(k, dict) else None


def _yas_gun(cekildi: str) -> float | None:
    try:
        t = time.strptime(str(cekildi), "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None
    return (time.time() - time.mktime(t) + time.timezone) / 86400.0


def oku_kayit(kod: str, ceyrek: int, bitis: str = "",
              azami_gun: float = OMUR_GUN) -> dict | None:
    """Gecerli kaydin TAMAMINI doner (ust veriyle), yoksa None.

    None donmesi bir kusur DEGIL: cagiran taraf aga duser. Bu yuzden
    her gecersizlik sebebi sessiz -- yazan taraf (`yaz`) zaten
    kosu gunlugune sayiyi basiyor.

    NEDEN `oku`DAN AYRI: besleme kaydin `bitis` ve `cekildi`
    alanlarini da yayimliyor ("bu rakam hangi donem, ne zaman
    cekildi"). Onlari ikinci bir dosya okumasiyla almak, GECERLILIK
    DENETIMINDEN GECMEMIS bir kaydi okumaya ve sinamada enjekte
    edilen okuyucuyu atlamaya yol aciyordu -- yani sinama gercek
    defteri okuyor, olctugunu sandigi seyi olcmuyordu.
    """
    k = kayit_oku(kod)
    if not k:
        return None
    if k.get("sema") != sema():
        return None
    if int(k.get("ceyrek") or 0) != int(ceyrek):
        return None
    if bitis and str(k.get("bitis") or "") != str(bitis):
        return None
    yas = _yas_gun(k.get("cekildi") or "")
    if yas is None or yas > azami_gun:
        return None
    t = k.get("tablolar")
    if not (isinstance(t, dict) and t):
        return None
    # SAYFA KURMAYA YETMEYEN KAYIT SUNULMUYOR.
    #
    # `_seri_bitis` olmadan "Son dort donem" bolumu URETILEMEZ:
    # kolonlarin hangi doneme ait oldugu soylenemez ve
    # `bilanco_ag.donem_getir` o adimlari seriye hic koymaz.
    # Boyle bir kayit sunuldugunda sayfa bolumsuz kuruluyor,
    # ardindan goc kuyrugu onu "bolum yok" diye geri aliyor ve
    # kuyruk ASLA TUKENMIYOR -- her kosuda ayni isi yapan bir
    # saat bombasi.
    #
    # OLCULDU (2026-11-24): defterdeki 232 kaydin BIRI boyleydi
    # (KARCL) ve sebebi ayristiricidaki kolon kaymasiydi. Kok sebep
    # `bilanco_ag._tablo` icinde duzeltildi; bu denetim AYRI bir
    # soruyu kapatiyor: eski ayristiriciyla yazilmis kayit ne
    # olacak? Cevap: sunulmaz, sirket bir kez daha cekilir ve
    # kayit kendiliginde duzelir. Elle silmek gerekmiyor.
    #
    # BUTUN DEFTERI GECERSIZ KILMAK SECENEK DEGILDI: semaya
    # ayristirici surumu eklemek 232 sirketi birden aga
    # dusururdu ve kaynak ~100-130 istekte kapaniyor -- defterin
    # cozdugu sorunun ta kendisi. Olcut, kaydin KENDI eksikligi.
    if not (t.get("_seri_bitis") or []):
        return None
    return k


def oku(kod: str, ceyrek: int, bitis: str = "",
        azami_gun: float = OMUR_GUN) -> dict | None:
    """Gecerli kayitin `tablolar`ini doner, yoksa None."""
    k = oku_kayit(kod, ceyrek, bitis, azami_gun)
    return k["tablolar"] if k else None


def kodlar() -> list[str]:
    """Defterde kaydi olan sirket kodlari."""
    if not KOK.exists():
        return []
    return sorted(p.stem.upper() for p in KOK.glob("*.json"))
