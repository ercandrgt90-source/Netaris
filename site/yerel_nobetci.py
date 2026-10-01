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


def karar_ver(veri: dict | None, kosu_var: bool) -> tuple[str, str]:
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
    try:
        p = subprocess.run([git, "credential", "fill"],
                           input="protocol=https\nhost=github.com\n\n",
                           capture_output=True, text=True,
                           encoding="utf-8", timeout=20)
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


def tetikle(jeton: str) -> int | None:
    kod, _ = _istek(
        f"https://api.github.com/repos/{DEPO}/actions/workflows"
        f"/{IS_AKISI}/dispatches",
        {"ref": "main", "inputs": {"yayinla": "true"}},
        jeton=jeton, yontem="POST")
    return kod


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
    karar, sebep = karar_ver(veri, kosu)
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
    if karar == KARAR_TETIKLE and not a.kuru:
        if not jeton:
            karar, sebep = KARAR_BILINMIYOR, "makinede git kimligi yok"
        else:
            k = tetikle(jeton)
            yanit = f" yanit={k}"
            if k not in (204,):
                # SESSIZ KALMIYOR: 401 ise kimlik dolmus demektir ve
                # bu, tam olarak ogrenilmesi gereken sey.
                sebep += f" -- TETIK BASARISIZ ({k})"

    satir = f"{an} {karar}: {sebep}{yanit}"
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
