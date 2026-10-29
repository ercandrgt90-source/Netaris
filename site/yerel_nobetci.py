# -*- coding: utf-8 -*-
"""YEREL NOBETCI -- yeni jeton istemeden insa temposunu yukseltir.

BU DOSYA NEDEN VAR
------------------
Tel katmani BASLIKLARI taze tutuyor (bkz. `worker.js` -> telTopla),
ama analiz, AI yorumu ve fotograf uretimi hala INSAYA bagli. Insa
ise GitHub'in zamanlayicisina bagli ve o zamanlayici bu depoda
calismiyor.

OLCULDU (2026-10-01, son 66 zamanlanmis kosu):

    cron anindan gecikme   ortanca 15 dk, %90 27 dk, en buyuk 29 dk
    2 dk icinde dusen      6/66
    dakika dagilimi        saat boyunca DUZGUN (:00'dan :59'a)
    saat dagilimi          01,03,04,05,07,12 -> SIFIR kosu
                           02,08,23          -> 7-8 kosu
    istenen / dusen        ~37 / ~7 gunde  (%19)

Iki sonuc cikiyor:

  1. Gecikme saat basi yogunlugundan DEGIL -- dakikalar duzgun
     dagilmis, yani 0-30 dk arasi RASTGELE bir gecikme var.
     Dolayisiyla cron dakikasini kaydirmak hicbir sey degistirmez;
     denenmedi cunku veri onu desteklemiyor.
  2. Teslim, ISTENEN SIKLIKTAN bagimsiz: gece cron'u 00-04 arasi
     her saat istiyor, yalnizca 00 ve 02 dusuyor. Daha sik istemek
     daha cok vermiyor.

Yani GitHub tarafi sikistirilamaz. Nobetci tam bu yuzden yazilmisti
ama Cloudflare'dan GitHub'i tetiklemek JETON istiyor ve jeton
gecersiz.

BU DOSYANIN YAPTIGI
-------------------
Ayni nobetciyi BU MAKINEDE kosturuyor. Fark: GitHub kimligi burada
ZATEN VAR -- `git push` onu kullaniyor. Yani yeni bir jeton
uretilmiyor, kullaniciya hicbir sey kurdurulmuyor.

NE ZAMAN TETIKLER
-----------------
Karar `/api/nobetci` ucundan okunuyor; esik de ORADAN geliyor,
burada yazili degil (`esik_saat`). Tek kaynak Worker'da.

  icerik_yasi_saat yok      -> BILINMIYOR, tetiklenmez
  yas < esik                -> TAZE, tetiklenmez
  kosu zaten suruyor        -> SIRAYA SOKMAZ
  digerleri                 -> tetikler

"Ulasilamadi" ile "bayat" ayni sey DEGIL: bu depoda olcum aracinin
kendisi defalarca yanlis alarm uretti ve ulasilamayan bir ucu
"bozuk" saymak gercek arizayi da inandiriciliktan dusururdu.

SINIRLARI -- ACIKCA
-------------------
  * Yalnizca makine ACIK ve agda iken calisir. GitHub'in seyrek
    takvimi yerine GECMIYOR, onu TAMAMLIYOR; makine kapaliyken
    tempo yine ~7 kosu/gune duser.
  * Bu makinedeki git kimligini kullanir. O kimlik dolarsa yerel
    nobetci de durur -- ve bunu gunluge YAZAR, sessiz kalmaz.
  * Jeton SOHBETE ya da gunluge ASLA yazilmaz; yalnizca HTTP durum
    kodlari kaydedilir.

Calistirma:
    python site/yerel_nobetci.py            # bir kez bak
    python site/yerel_nobetci.py --kuru     # karar ver, TETIKLEMEZ
    python site/yerel_nobetci.py --zorla    # taze olsa da tetikle

ZAMANLANMIS GOREV (Windows) -- 2026-10-01'de kuruldu
----------------------------------------------------
Ad: `Netaris-yerel-nobetci`, on dakikada bir, konsolsuz
(`pythonw.exe`, pencere acmiyor).

Kurulumda IKI AYAR olmazsa gorev SESSIZCE calismaz ve ikisi de
`schtasks` varsayilanidir:

  * `Stop On Battery Mode, No Start On Batteries` -- dizustu pilde
    oldugu icin gorev HIC baslamadi, durumu "Queued"da kaldi.
    Cozum: `-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries`.
  * 72 saatlik calisma siniri -- takilan bir kosu uc gun boyunca
    sirayi kilitlerdi. Cozum: `-ExecutionTimeLimit 5 dakika`.

Ayrica `-MultipleInstances IgnoreNew` (ustuste kosmasin) ve
`-StartWhenAvailable` (makine uyanınca kacirilani telafi etsin).

Kurmak / kaldirmak:

    Get-ScheduledTask -TaskName "Netaris-yerel-nobetci"
    Unregister-ScheduledTask -TaskName "Netaris-yerel-nobetci"

Kararlar `site/yerel_nobet.log` dosyasina yaziliyor (gitignore'da).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEPO = "ercandrgt90-source/Netaris"
IS_AKISI = "otomasyon.yml"

#: Bilanco hatti -- KOTA TAZEYKEN tetiklenmesi gereken ayri is akisi.
BILANCO_AKISI = "bilanco.yml"

#: Bilanco tetiginin EN ERKEN saati (UTC, "SS:DD").
#:
#: NEDEN GECE YARISINDAN HEMEN SONRA -- OLCULDU (2026-10-29):
#: Cloudflare Workers AI gunluk ucretsiz kotasi 00:00 UTC'de
#: sifirlaniyor ve haber hatti onu gun icinde tuketiyor (gunde ~32
#: kosu x ~5 cagri = ~160 cagri). Ayni gunun gunluklerinden:
#:
#:     00:23  haber kosusu   -> 0 x 429        (kota acik)
#:     19:13  haber kosusu   -> 5 yorum, 0x429 (kota acik)
#:     21:48  haber kosusu   -> calisiyor      (kota acik)
#:     21:53  bilanco #55    -> ILK sirkette 429
#:     22:11  bilanco #56    -> ILK sirkette 429
#:
#: Bilanco sayfasi ancak dogrulanmis bir yorumla yayimlanabiliyor,
#: yani kota bittiginde SIFIR sayfa uretiliyor. Siraya girmek degil,
#: SIRANIN BASINA gecmek gerekiyor.
#:
#: NEDEN CRON DEGIL: `bilanco.yml` zaten "23 6" icin planli ama bu
#: depoda GitHub'in zamanlanmis kosulari saatlerce gecikiyor
#: (olculdu: 06:23 planli -> 11:48-13:40 arasi gercek, 5-7 saat).
#: Yerel nobetci ise her 10 dakikada bir guvenilir calisiyor.
BILANCO_SAATI = "00:10"

#: Tetigin SON saati (UTC). Pencere disinda ATILMIYOR.
#:
#: UST SINIR SART: alt sinir tek basina "bugun henuz atilmadi" diyen
#: her turu tetikliyordu -- yani kod ogleden sonra devreye girse
#: kotanin bittigi bir saatte bosuna kosu acardi. Bu degisikligin
#: TEK gerekcesi kotanin TAZE olmasi; taze olmadigi saatte tetik
#: gerekcesini kaybediyor.
#:
#: PENCERE GENIS TUTULDU (uc saat): makine gece yarisinda kapaliysa
#: gun tamamen kacmasin. Pencere de kacarsa `bilanco.yml`in kendi
#: cron'u yedek olarak duruyor.
BILANCO_SON_SAAT = "03:00"

#: Bu tetikte en fazla kac bilanco sayfasi yazilsin.
#:
#: KOTA ORTAK VE SABIT BIR PASTA -- OLCULDU (2026-10-29, kosu #2371
#: gunlugunden, 429'un KENDI metni):
#:
#:     AiError: you have used up your daily free allocation
#:
#: Yani gunluk tahsisat; haber hatti ve bilanco hatti AYNI havuzdan
#: iciyor. Bilanco hattini gunun ILK isi yapmak dogru, ama sinirsiz
#: birakmak haber tarafini gun boyu ac birakir -- kendi elimizle
#: yeni bir kusur yaratmak olurdu.
#:
#: 25 SECILDI, KEYFI DEGIL: ayni sayi "bolum gocu" adiminda da
#: kullaniliyor ve orada OLCULDU (kosu #57: 24 sayfa tazelendi,
#: kaynak kapanmadi). Q3 sezonunda ~300 sirket bildirecek; gunde 25
#: sayfa ~12 gunde kapatir.
#:
#: Is akisinin KENDI varsayilani 60 ve o DEGISMIYOR: elle
#: tetikleyen biri tam gazi hala secebilmeli.
BILANCO_PAYI = "25"

#: Gunluge yazilan damga. AYNI metin hem yazarken hem ararken
#: kullaniliyor -- iki yerde ayri yazilsaydi arama hic eslesmez ve
#: nobetci her turda YENIDEN tetiklerdi.
BILANCO_DAMGASI = "bilanco gunluk tetik"
DURUM_UCU = "https://netaris.net/api/nobetci"

#: Cloudflare varsayilan `Python-urllib` kimligini 403 ile reddediyor
#: (bkz. memory: olcum-araci-tuzaklari). Kendimizi tanitiyoruz.
KIMLIK = "Netaris-yerel-nobetci/1.0 (+https://netaris.net)"

#: Gunluk -- kararlar burada birikiyor.
#:
#: NEDEN DOSYA: "tetikledi mi, tetiklemedi mi, neden" sorusu
#: cevaplanabilir olmali. Bu depoda tam bu kor noktanin bedeli
#: odendi: nobetci 17 kez 401 aldi ve kimse gormedi, cunku tek
#: kayit `console.log`du.
GUNLUK = pathlib.Path(__file__).resolve().parent / "yerel_nobet.log"

#: Gunlukte tutulan en fazla satir. Teshis icin gecmis saatler
#: gerekiyor, aylar degil.
GUNLUK_SATIR = 400

KARAR_BILINMIYOR = "bilinmiyor"
KARAR_TAZE = "taze"
KARAR_KOSUYOR = "kosuyor"
KARAR_TETIKLE = "tetikle"
#: TETIKLEDIM AMA HICBIR SEY OLMADI.
#:
#: 2026-10-26 17:53 -- 22:13 arasi: nobetci 27 KEZ tetikledi, 27
#: kez 204 aldi ve icerik yasi 0.67 saatten 5.01 saate MONOTON
#: cikti. Her tur "tetikle: ... yanit=204" yaziyordu, yani gunluk
#: basarili gorunuyordu. Gercekte tetiklenen kosular `test_harita`
#: kirmizi yandigi icin dagitim adimina hic gelmiyordu.
#:
#: Kusur tetiklemede DEGIL olcutte: 204, "GitHub istegi kabul etti"
#: demek; "site tazelendi" demek DEGIL. Nobetci her turu bagimsiz
#: gordugu icin ayni sonucsuz isi 27 kez tekrarladi ve kesinti 4.3
#: saat boyunca hicbir yere duyurulmadi.
KARAR_BOZUK = "bozuk"

#: Kac ardisik sonucsuz tetiklemeden sonra hat BOZUK sayilir.
#:
#: OLCULDU (gunlukteki 400 satir, 2026-10-20 -> 10-26, 68 ardisik
#: tetikleme dizisi):
#:
#:     dizi uzunlugu   normal isleyiste   arizada
#:     1               cok                 --
#:     2               1 kez               --
#:     3+              HIC                 27
#:
#: Yani dagilimlar CAKISMIYOR: saglikli hat ucuncu ardisik
#: tetiklemeye hic ulasmiyor, cunku bir tetikleme sonuc verdiginde
#: sonraki tur "taze" yaziyor ve dizi kiriliyor. Esik bu yuzden
#: GERCEKTEN eliyor -- bu depoda esiklerin cogu elemedigi icin
#: kaldirilmisti, bu olcum onu ayirmak icin yapildi.
BOSA_TETIK_SINIRI = 3


def _satir_coz(satir: str) -> tuple[str, float | None] | None:
    """Gunluk satirindan (karar, icerik_yasi) cikarir.

    Bicim: `2026-10-26T22:13:10Z tetikle: icerik 5.01 saat, ...`

    DUZENLI IFADE KULLANILMIYOR. Bu depoda desenlere gomulu ters
    boluler birkac kez sessizce baska bir seye dondu (`chr(8)`,
    gercek satir sonu) ve desen hic eslesmedigi halde kimse
    farketmedi. Bolme ile ayristirmanin boyle bir sessiz modu yok.
    """
    parca = satir.split(" ", 2)
    if len(parca) < 3 or not parca[1].endswith(":"):
        return None
    yas: float | None = None
    if "icerik " in parca[2]:
        kuyruk = parca[2].split("icerik ", 1)[1]
        try:
            yas = float(kuyruk.split(" ", 1)[0])
        except ValueError:
            yas = None
    return parca[1][:-1], yas


def son_tetik_dizisi(satirlar) -> list[float]:
    """Gunlugun SONUNDAKI kesintisiz tetikleme dizisinin yaslari.

    Sondan geriye gidiyor ve tetikleme OLMAYAN ilk satirda duruyor:
    araya giren "taze" bir tur, bir onceki tetiklemenin SONUC
    VERDIGI anlamina gelir -- dizi orada bitmis sayilmali. Cozulemeyen
    bir satir (coku izi, bozuk bicim) da diziyi kirar; muhafazakar
    olan bu, cunku o satirin ne oldugu BILINMIYOR.
    """
    dizi: list[float] = []
    for satir in reversed(list(satirlar)):
        c = _satir_coz(satir)
        if c is None or c[0] != KARAR_TETIKLE or c[1] is None:
            break
        dizi.append(c[1])
    dizi.reverse()
    return dizi


def karar_ver(veri: dict | None, kosu_var: bool,
              dizi: list[float] | tuple = ()) -> tuple[str, str]:
    """SAF KARAR -- ag yok, yan etki yok, sinanabilir.

    Esik VERIDEN geliyor, burada yazili DEGIL: Worker'daki deger
    degisirse yerel nobetci kendiliginden ona uyuyor. Esigi buraya
    kopyalamak, ayni karari iki yerde tutmak olurdu -- bu depoda en
    pahaliya mal olan kusur sinifi.
    """
    if not isinstance(veri, dict):
        return KARAR_BILINMIYOR, "durum ucu okunamadi"
    yas = veri.get("icerik_yasi_saat")
    if yas is None:
        return KARAR_BILINMIYOR, "icerik yasi bildirilmiyor"
    try:
        yas = float(yas)
    except (TypeError, ValueError):
        return KARAR_BILINMIYOR, f"icerik yasi cozulemedi: {yas!r}"
    esik = veri.get("esik_saat")
    try:
        esik = float(esik)
    except (TypeError, ValueError):
        return KARAR_BILINMIYOR, f"esik cozulemedi: {esik!r}"
    if yas < esik:
        return KARAR_TAZE, f"icerik {yas:.2f} saat, esik {esik:.2f}"
    # KOSU SURUYORSA SIRAYA SOKMUYORUZ.
    #
    # Is akisinin `concurrency` grubu zaten ustuste kosmayi
    # engelliyor, ama bekleyen bir kosu eklemek de bir sey
    # kazandirmiyor: o kosu zaten bu bayatligi gorecek. Ustelik
    # GitHub ayni is akisi icin bekleyen kosulari degistirebiliyor,
    # yani sira eklemek hem bos hem belirsiz.
    if kosu_var:
        return KARAR_KOSUYOR, f"icerik {yas:.2f} saat ama kosu suruyor"
    # TETIKLEMEK YETMEZ -- SONUC VERDI MI?
    #
    # `dizi` bu nobetcinin KENDI gunlugunden okunan, kesintisiz
    # tetikleme turlerinin yas dizisi. Yas dizinin basindan beri
    # DUSMEMISSE tetikleme sonuc uretmiyor demektir: hat asagi bir
    # yerde kopuk (kirmizi sinama, dagitim jetonu, Cloudflare) ve
    # daha fazla tetiklemek onu duzeltmez.
    #
    # Karar yine tetiklemeyi SURDURUR (main'e bakin): hat duzeldigi
    # anda ilk tur yayina alsin. Degisen sey yalnizca bu: artik
    # DUYURULUYOR.
    if len(dizi) >= BOSA_TETIK_SINIRI and yas > dizi[0]:
        return KARAR_BOZUK, (
            f"{len(dizi)} ardisik tetikleme SONUC VERMEDI -- yas"
            f" {dizi[0]:.2f} -> {yas:.2f} saat; hat kopuk")
    return KARAR_TETIKLE, f"icerik {yas:.2f} saat, esik {esik:.2f}"


def _istek(adres: str, govde: dict | None = None,
           jeton: str = "", yontem: str = "GET") -> tuple[int | None, str]:
    """HTTP istegi. JETON HICBIR YERE YAZILMIYOR."""
    basliklar = {"User-Agent": KIMLIK, "Accept": "application/json"}
    if jeton:
        basliklar["Authorization"] = "Bearer " + jeton
        basliklar["Accept"] = "application/vnd.github+json"
        basliklar["X-GitHub-Api-Version"] = "2022-11-28"
    r = urllib.request.Request(
        adres,
        data=json.dumps(govde).encode() if govde is not None else None,
        method=yontem, headers=basliklar)
    try:
        with urllib.request.urlopen(r, timeout=25) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:                       # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


#: `git` PATH'TE ARANMAZ -- bulunur.
#:
#: OLCULDU (2026-10-01): zamanlanmis gorev `git`i bulamiyordu.
#: Gorev Zamanlayici isi minimal bir PATH ile baslatiyor ve `git`
#: oraya dahil degil; `subprocess.run(["git", ...])` FileNotFoundError
#: atiyor ve betik GUNLUGE HICBIR SEY YAZMADAN cokuyordu.
#:
#: Ikinci sessizlik katmani daha kotuydu: `pythonw.exe` izlemeyi
#: yutuyor VE cikis kodunu 0 raporluyor. Yani Gorev Zamanlayici
#: "Last Result: 0" diyordu -- yani "calisti". Her tur cokuyordu ve
#: hicbir yerde iz yoktu.
GIT_ADAYLARI = (
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
)


def git_yolu() -> str:
    """Once PATH, sonra bilinen kurulum yerleri. Bulamazsa bos."""
    import shutil                               # noqa: PLC0415

    yol = shutil.which("git")
    if yol:
        return yol
    for aday in GIT_ADAYLARI:
        if pathlib.Path(aday).exists():
            return aday
    return ""


def kimlik_al() -> str:
    """Makinede ZATEN KAYITLI git kimligini okur.

    YENI JETON URETILMIYOR: `git push` bu kimligi kullaniyor. Deger
    hicbir yere yazdirilmiyor, yalnizca istek basligina konuyor.
    """
    git = git_yolu()
    if not git:
        return ""
    # ETKILESIMLI SORU SORMASI ENGELLENIYOR.
    #
    # OLCULDU (2026-10-01 15:15): gorev baglaminda kimlik
    # okunamadi ("makinede git kimligi yok") ve ardindan ~50 tur
    # GUNLUGE HIC SATIR YAZMADI. Etkileşimli oturum yokken (ekran
    # kilitli ya da oturum kapali) kimlik yardimcisi SORU SORMAYA
    # calisabiliyor; soru cevapsiz kaldigi icin cagri suruncemede
    # kaliyor ve gorev 5 dakikalik sinira takilip oldurulunce
    # gunluge hicbir sey dusmuyor.
    #
    # `GIT_TERMINAL_PROMPT=0` ve `GCM_INTERACTIVE=never` sormayi
    # kapatiyor: yardimci ya hazir degeri verir ya HEMEN basarisiz
    # olur. Sure de 20 -> 8 saniyeye indirildi; bir yardimci sekiz
    # saniyede cevap vermiyorsa o turda vermeyecek.
    #
    # NOT: bu gozlem TAM OLARAK aciklanmis degil -- oturum kilidi
    # en olasi sebep ama kanitlanmadi. Bu yuzden asagidaki `sure`
    # olcumu de eklendi: yavaslama artik gunlukte gorunuyor.
    import os                                    # noqa: PLC0415

    cevre = dict(os.environ)
    cevre["GIT_TERMINAL_PROMPT"] = "0"
    cevre["GCM_INTERACTIVE"] = "never"
    # PENCERE ACMADAN CALISTIR -- KULLANICININ EKRANINA VURUYORDU.
    #
    # Gorev `pythonw.exe` ile kosuyor, yani KONSOLU YOK. Windows'ta
    # konsolsuz bir surecten baslatilan konsol uygulamasi KENDINE
    # konsol ayirir; varsayilan terminal Windows Terminal oldugu icin
    # bu, kucuk siyah bir kutu degil TAM BOY bir pencere demek.
    #
    # OLCULDU (2026-10-11). Kullanici "ara ara bir pencere acilip
    # kapaniyor, oyun oynarken oyundan atiyor" dedi. Gorev TEK BASINA
    # tetiklendi ve surekli calisan bir pencere izleyicisi yakaladi:
    #
    #   19:01:43  gorev tetiklendi
    #   19:01:44  1199x616  CASCADIA_HOSTING_WINDOW_CLASS
    #             WindowsTerminal.exe  'Windows Terminal'
    #
    # Gorev on dakikada bir kosuyor: tam ekran oyunda saatte alti kez
    # odak calinmasi demek.
    #
    # ILK OLCUMUM YANLIS NEGATIF VERDI: `MainWindowHandle` ve 25 ms
    # araliklı anlik Win32 taramasi pencereyi GORMEDI; "gorev temiz"
    # diye yazmistim. Kisa omurlu pencere anlik ornekleme ile
    # olculmuyor -- ancak surekli calisan bir izleyici goruyor.
    #
    # `CREATE_NO_WINDOW` yalnizca Windows'ta var; baska isletim
    # sisteminde bayrak 0 kaliyor ve cagri degismiyor.
    _pencereSiz = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.run([git, "credential", "fill"],
                           input="protocol=https\nhost=github.com\n\n",
                           capture_output=True, text=True,
                           encoding="utf-8", timeout=8, env=cevre,
                           creationflags=_pencereSiz)
    except (OSError, subprocess.SubprocessError):
        return ""
    if p.returncode != 0:
        return ""
    for satir in p.stdout.splitlines():
        if satir.startswith("password="):
            return satir.split("=", 1)[1].strip()
    return ""


def kosu_suruyor(jeton: str) -> bool:
    """Su an koşan ya da bekleyen bir otomasyon kosusu var mi?"""
    kod, govde = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/runs"
        f"?per_page=5&status=in_progress", jeton=jeton)
    if kod != 200:
        return False
    try:
        d = json.loads(govde)
    except ValueError:
        return False
    if d.get("total_count"):
        return True
    kod, govde = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/runs"
        f"?per_page=5&status=queued", jeton=jeton)
    if kod != 200:
        return False
    try:
        return bool(json.loads(govde).get("total_count"))
    except ValueError:
        return False


def bilanco_gerekli(simdi, gunluk: list[str]) -> bool:
    """Bugun bilanco tetigi atildi mi -- GUNLUKTEN okunuyor.

    Ayri bir durum dosyasi YOK: gunluk zaten bu makinede duruyor,
    budaniyor ve her turda okunuyor. Ikinci bir dosya, ikisinin
    ayrisabilecegi ikinci bir yer demekti.

    `gunluk` BOS ise "bugun tetiklenmedi" sayiliyor ve tetik atiliyor.
    Gunlugu okuyamamak bir ariza KANITI degil; en kotu ihtimalle
    gunde bir fazladan tetik olur, bu da zararsiz (hat zaten kendi
    kendini atlar).
    """
    ss = simdi.strftime("%H:%M")
    if not BILANCO_SAATI <= ss <= BILANCO_SON_SAAT:
        return False
    bugun = simdi.strftime("%Y-%m-%d")
    for satir in reversed(gunluk):
        if BILANCO_DAMGASI in satir and satir.startswith(bugun):
            return False
    return True


def bilanco_tetikle(jeton: str) -> int | None:
    """Bilanco is akisini elle tetikler.

    `zorla` VERILMIYOR: bildirim ayi olup olmadigina hattin kendisi
    karar veriyor ve o karar burada kopyalanmamali.

    `sinir` VERILIYOR cunku bu tetigin baglami farkli: gunun ILK isi
    olarak kosuyor ve gunluk AI tahsisatinin TAMAMINI tuketebilir.
    `BILANCO_PAYI` haber hattina pay birakiyor.
    """
    kod, _ = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/workflows"
        f"/{BILANCO_AKISI}/dispatches",
        {"ref": "main",
         "inputs": {"yayinla": "true", "sinir": BILANCO_PAYI}},
        jeton=jeton, yontem="POST")
    return kod


def tetikle(jeton: str) -> int | None:
    kod, _ = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/workflows"
        f"/{IS_AKISI}/dispatches",
        {"ref": "main", "inputs": {"yayinla": "true"}},
        jeton=jeton, yontem="POST")
    return kod


#: Duyuru konusunun basligi. AYNI metin hem acarken hem ararken
#: kullaniliyor: iki yerde ayri yazilsaydi arama hic eslesmez ve
#: nobetci her on dakikada YENI bir konu acardi.
DUYURU_BASLIGI = "Yerel nobetci tetikliyor ama site TAZELENMIYOR"

#: Satir sonu ACIK bir sabit olarak tutuluyor.
#:
#: Ters bolu kacislari bu depoda defalarca SESSIZCE baska bir seye
#: dondu: yazilan desen chr(8) oldu, yazilan iki karakterlik kacis
#: gercek satir sonu oldu ve kaynak dogru GORUNDUGU icin kimse
#: farketmedi. Bir dosya ters bolu HIC icermiyorsa o kusur sinifi
#: orada imkansizdir -- bedeli bir sabit.
NL = chr(10)


def son_kosu(jeton: str) -> str:
    """En son otomasyon kosusunun numarasi ve sonucu -- teshis icin.

    Hat kopuksa asil soru "hangi adim dusuyor" ve cevap kosunun
    kendisinde. Duyuru o kosuya DOGRUDAN baglanmali, yoksa okuyan
    kisi Actions sekmesinde aramak zorunda kalir.
    """
    kod, govde = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/workflows"
        f"/{IS_AKISI}/runs?per_page=1", jeton=jeton)
    if kod != 200:
        return f"son kosu okunamadi (HTTP {kod})"
    try:
        kosular = json.loads(govde).get("workflow_runs") or []
    except ValueError:
        return "son kosu cozulemedi"
    if not kosular:
        return "hic kosu yok"
    r = kosular[0]
    return (f"son kosu #{r.get('run_number')} -> "
            f"{r.get('status')}/{r.get('conclusion')}" + NL
            + str(r.get("html_url")))


def duyur(jeton: str, sebep: str) -> str:
    """Hat kopuklugunu GitHub konusu olarak duyurur.

    NEDEN GUNLUK YETMIYOR: `yerel_nobet.log` gitignore'da ve yalnizca
    bu makinede duruyor. 2026-10-26'da kesinti 4.3 saat surdu;
    gunluk her turu DOGRU yazdi ve kimse okumadi. Okunmayan bir
    uyari, uyari degildir.

    TEK KONU ACILIR: ayni baslikla acik bir konu varsa yenisi
    acilmaz. Gorev on dakikada bir kosuyor -- aksi halde bir gecede
    144 konu birikir ve duyurunun kendisi gurultuye donusurdu.
    """
    kod, govde = _istek(
        f"https://api.github.com/repos/{DEPO}/issues?state=open&per_page=50",
        jeton=jeton)
    if kod != 200:
        return f"duyuru ATLANDI: acik konular okunamadi (HTTP {kod})"
    try:
        acik = json.loads(govde)
    except ValueError:
        return "duyuru ATLANDI: konu listesi cozulemedi"
    for konu in acik if isinstance(acik, list) else []:
        if DUYURU_BASLIGI in (konu.get("title") or ""):
            return f"duyuru zaten acik (#{konu.get('number')})"

    govde_metni = NL.join((
        "Yerel nobetci GitHub kosusunu tetikliyor ve GitHub istegi"
        " KABUL ediyor (HTTP 204), ama sitedeki icerik tazelenmiyor.",
        "",
        f"Olcum: {sebep}",
        "",
        son_kosu(jeton),
        "",
        "Yani sorun tetiklemede DEGIL: tetiklenen kosu dagitim"
        " adimina ulasmiyor. En sik sebep bir sinamanin kirmizi"
        " yanmasi -- `calistir.py` ok=False dondurdugunde dagitim"
        " ATLANIR ve kosu yine yesil gorunebilir.",
        "",
        "Bakilacak yer: yukaridaki kosunun gunlugu, dusen adim.",
        "",
        "Bu konu nobetci tarafindan otomatik acildi ve hat"
        " duzeldiginde kendiliginden KAPANMAZ -- duzeldigini"
        " gordugunuzde elle kapatin.",
    ))
    kod, _ = _istek(
        f"https://api.github.com/repos/{DEPO}/issues",
        {"title": DUYURU_BASLIGI, "body": govde_metni},
        jeton=jeton, yontem="POST")
    if kod == 201:
        return "duyuru ACILDI"
    # SESSIZ KALMIYOR: duyurunun kendisi de basarisiz olabilir ve o
    # da tam olarak ogrenilmesi gereken sey.
    return f"duyuru BASARISIZ (HTTP {kod})"


def _yaz(metin: str, akis=None) -> None:
    """Yazdirir -- AMA `pythonw.exe` altinda cokmez.

    Konsolsuz Python'da (`pythonw.exe`) `sys.stdout` None olur ve
    duz `print()` `AttributeError` atar. Zamanlanmis gorev
    `pythonw` ile kosuyor (her on dakikada konsol penceresi
    acmamasi icin), yani bu korunmazsa gorev HER TURDA sessizce
    duser ve "kurulu ama calismiyor" haline gecerdi.

    Bu depoda tam o bicimde kusurlar yasandi; gunluge yazma ZATEN
    dosyaya gidiyor, dolayisiyla ekrana yazamamak bilgi kaybi
    degil.
    """
    hedef = akis if akis is not None else sys.stdout
    if hedef is None:
        return
    try:
        print(metin, file=hedef)
    except Exception:                            # noqa: BLE001
        pass


def gunluge_yaz(satir: str) -> None:
    """Gunluge ekler ve budar. HATA YUTULUYOR: gunluk yazilamazsa
    nobetci gorevini yapmaya DEVAM EDER."""
    try:
        eski = (GUNLUK.read_text(encoding="utf-8").splitlines()
                if GUNLUK.exists() else [])
        eski.append(satir)
        GUNLUK.write_text("\n".join(eski[-GUNLUK_SATIR:]) + "\n",
                          encoding="utf-8")
    except OSError as e:
        _yaz(f"gunluk yazilamadi: {e}", sys.stderr)


def gunluk_oku() -> list[str]:
    """Gunlugu satirlara ayirir. Okunamazsa BOS doner.

    Bos liste, `son_tetik_dizisi` icin "gecmis bilinmiyor" demek ve
    o da BOZUK karari uretmez. Gunlugu okuyamamak bir ariza kaniti
    DEGIL: bu depoda olcum aracinin kendi arizasini ariza sanmak
    birkac kez yanlis alarma yol acti.
    """
    try:
        return GUNLUK.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kuru", action="store_true",
                    help="karar ver ama TETIKLEME")
    # ELLE TAZELEME.
    #
    # "Simdi guncelle" dugmesinin komut satiri karsiligi: icerik taze
    # olsa bile insayi baslatir. Kaynak degisikligi gonderildikten
    # sonra siteyi beklemeden yayina almak icin -- is akisinda `push`
    # tetikleyicisi YOK, yani kaynak gonderimi kendiliginden yayina
    # girmiyor.
    #
    # Zamanlanmis gorev bunu KULLANMIYOR; orada karar hep yasa gore
    # veriliyor.
    ap.add_argument("--zorla", action="store_true",
                    help="icerik taze olsa da TETIKLE (elle tazeleme)")
    a = ap.parse_args()

    import time                                  # noqa: PLC0415

    baslangic = time.monotonic()
    an = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kod, govde = _istek(DURUM_UCU)
    veri = None
    if kod == 200:
        try:
            veri = json.loads(govde)
        except ValueError:
            veri = None

    jeton = kimlik_al()
    kosu = bool(jeton) and kosu_suruyor(jeton)
    # KENDI GECMISINE BAKIYOR.
    #
    # Tek bir tur "tetikledim, 204 aldim" der ve bu dogrudur; ayni
    # turu 27 kez tekrarlamanin SONUCSUZ oldugunu yalnizca gecmis
    # gosterir. Olculdu (2026-10-26): 4.3 saatlik kesinti boyunca
    # her tur dogru satiri yazdi, hicbiri aniz degildi -- eksik olan
    # turlerin BIRLIKTE ne soyledigiydi.
    dizi = son_tetik_dizisi(gunluk_oku())
    karar, sebep = karar_ver(veri, kosu, dizi)
    if a.zorla:
        # KOSU SURUYORSA ZORLAMA DA SIRAYA SOKMUYOR.
        #
        # Olculdu (2026-10-01): ilk yazimda kosul `karar !=
        # KARAR_KOSUYOR` idi ve bu YANLISTI -- icerik TAZE oldugunda
        # karar `taze` oluyor, yani kosu kontrolune hic
        # bakilmiyordu. Sonuc: zaten kosan #1508'in ustune #1509
        # siraya girdi. Bekleyen kosu ayni icerigi uretecek, yani
        # kazanci sifir.
        #
        # Dogru kosul KARARIN degil, KOSUNUN kendisi.
        if kosu:
            karar, sebep = KARAR_KOSUYOR, "ELLE zorlandi ama kosu suruyor"
        else:
            karar, sebep = KARAR_TETIKLE, f"ELLE zorlandi ({sebep})"

    yanit = ""
    # BOZUK DA TETIKLER.
    #
    # Hat kopukken tetiklemeyi KESMEK, duzelme anini da kacirmak
    # olurdu: kaynak duzeltildigi an ilk tur yayina almali. Bozuk
    # kararinin degistirdigi tek sey, durumun DUYURULMASI.
    if karar in (KARAR_TETIKLE, KARAR_BOZUK) and not a.kuru:
        if not jeton:
            karar, sebep = KARAR_BILINMIYOR, "makinede git kimligi yok"
        else:
            k = tetikle(jeton)
            yanit = f" yanit={k}"
            if karar == KARAR_BOZUK:
                yanit += " " + duyur(jeton, sebep)
            if k not in (204,):
                # SESSIZ KALMIYOR: 401 ise kimlik dolmus demektir ve
                # bu, tam olarak ogrenilmesi gereken sey.
                sebep += f" -- TETIK BASARISIZ ({k})"

    # BILANCO TETIGI -- ICERIK TAZELIGINDEN BAGIMSIZ.
    #
    # Yukaridaki karar "site bayat mi" sorusunu cevapliyor; bu ise
    # "bilanco hatti bugun kota tazeyken kostu mu". Ikisi ayri soru:
    # site tertemiz tazeyken de bilanco hatti hic kosmamis olabilir.
    #
    # Gerekce `BILANCO_SAATI` uzerinde yazili: ucretsiz AI kotasi
    # 00:00 UTC'de sifirlaniyor, haber hatti gun icinde tuketiyor ve
    # bilanco kosusu kotayi BITMIS buluyordu -- sifir sayfa.
    #
    # KURU KIPTE ATILMIYOR ve KIMLIK YOKSA ATILMIYOR; ikisi de
    # yukaridaki tetikle ayni kural.
    if not a.kuru and jeton:
        _simdi = datetime.now(timezone.utc)
        if bilanco_gerekli(_simdi, gunluk_oku()):
            _bk = bilanco_tetikle(jeton)
            _bsatir = (f"{an} {BILANCO_DAMGASI}: yanit={_bk}"
                       if _bk == 204 else
                       f"{an} {BILANCO_DAMGASI}: BASARISIZ yanit={_bk}")
            # DAMGA BASARISIZLIKTA DA YAZILIYOR.
            #
            # Yazilmazsa her on dakikada bir yeniden denenir ve
            # kimlik gecersizse gun boyu 144 bosa istek olur. Gunde
            # BIR deneme, teshis icin yeterli ve zararsiz.
            _yaz(_bsatir)
            gunluge_yaz(_bsatir)

    # SURE DE YAZILIYOR.
    #
    # 2026-10-01'de ~50 tur gunluge hic satir yazmadi ve sebebi
    # disaridan gorulemedi. Sure, yavaslayan bir turu (ve 5 dakikalik
    # gorev sinirina yaklasmayi) gorunur kiliyor.
    sure = time.monotonic() - baslangic
    satir = f"{an} {karar}: {sebep}{yanit} ({sure:.1f}s)"
    _yaz(satir)
    gunluge_yaz(satir)
    # HER ZAMAN 0: bu bir bakim isi; kirmizi donmesi gereken bir
    # sinama degil. Zamanlanmis gorev hata penceresi acmamali.
    return 0


if __name__ == "__main__":
    # TANILAMA KENDI COKUSUNU DE YAZAR.
    #
    # Olculdu (2026-10-01): `git` bulunamadigi icin betik gunluge
    # hicbir sey yazmadan coktu ve `pythonw.exe` hem izlemeyi yuttu
    # hem cikis kodunu 0 raporladi. Gorev Zamanlayici "Last Result:
    # 0" diyordu -- yani tam tersini.
    #
    # Bir tani aracinin en kor oldugu yer kendi arizasidir. Burasi
    # onu kapatiyor: ne olursa olsun gunluge bir satir dusuyor.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as _e:                  # noqa: BLE001
        import traceback                         # noqa: PLC0415

        _an = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        gunluge_yaz(f"{_an} COKTU: {type(_e).__name__}: {_e}")
        try:
            gunluge_yaz(traceback.format_exc()[-600:])
        except Exception:                        # noqa: BLE001
            pass
        # Cikis kodu 1: Gorev Zamanlayici "Last Result" alaninda
        # gorulebilsin. Gorev gunde ~144 kez kosuyor; sessiz bir
        # coku, olmayan bir ozellikten kotu.
        sys.exit(1)
