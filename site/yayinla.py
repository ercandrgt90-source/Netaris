"""Siteyi uretip Cloudflare'e yayimlar -- tek komut.

    python yayinla.py

Elle ZIP paketleyip panele surukleme dongusu bitiyor. Betik bes isi
sirayla yapiyor:

  1. depo durumu      -> gonderilmemis commit varsa UYARIR, cunku CI
                         uzak ucu dagitiyor ve onlari geri alir
  2. site/insa.py     -> icerikten HTML uretir
  3. yayin denetimi   -> yer tutucu ve islenmemis etiket arar
  4. wrangler deploy  -> Cloudflare'e yukler
  5. canli dogrulama  -> yuklenen yapinin GERCEKTEN yayinda oldugunu
                         canli sayfadan okuyarak dogrular

1. ve 5. adimlar sonradan eklendi ve sebebi olculdu: canli site otuz
bir commit geride kalmisti, ikisi de bunu sessizce mumkun kiliyordu
(bkz. `depo_uyarisi` ve `yayini_dogrula`).

Ilk kullanimdan once bir kez kimlik dogrulamasi gerekiyor:

    npx wrangler login

Tarayicida onay verildikten sonra kimlik makinede saklanir; bir daha
sorulmaz.

Yayina almadan once dogrulama yapar: yer tutucu alan adi, doldurulmamis
kunye alani ve islenmemis sablon etiketi varsa dagitimi DURDURUR. Bir kez
yer tutucu bilgilerle yayina cikildi; bu kontrol onu tekrarlatmamak icin.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

KOK = pathlib.Path(__file__).parent
CIKTI = KOK / "cikti"

# Yayina cikmasi kabul edilemez izler
ENGELLER = (
    ("ALAN-ADI-BELIRLENMEDI", "site adresi hala yer tutucu (insa.py icinde SITE['adres'])"),
    ("[Ad Soyad", "kunye sayfasinda doldurulmamis alan"),
    ("[Acik adres", "kunye sayfasinda doldurulmamis alan"),
    ("[Açık adres", "kunye sayfasinda doldurulmamis alan"),
    ("DOLDURULACAK", "yayina cikmamasi gereken not blogu"),
    ("{{", "islenmemis sablon etiketi"),
    ("{%", "islenmemis sablon etiketi"),
)


def _node_yolu() -> None:
    """Node kurulum dizinini PATH'e ekler.

    winget ile kurulan Node yeni acilan kabuklarda PATH'te gorunuyor ama
    calisan oturumda gorunmeyebiliyor. Elle eklemek bu farki kapatiyor.
    """
    for aday in (r"C:\Program Files\nodejs", r"C:\Program Files (x86)\nodejs"):
        if pathlib.Path(aday).exists() and aday not in os.environ["PATH"]:
            os.environ["PATH"] = f"{aday};{os.environ['PATH']}"


# Windows'ta alt surec ciktisi varsayilan olarak sistem kod sayfasiyla
# (Turkce kurulumda cp1254) cozulmeye calisiliyor. Wrangler UTF-8 yaziyor
# ve emoji kullaniyor -- cozumleme UnicodeDecodeError ile patliyor, stdout
# None kaliyor. Kodlamayi acikca vermek bunu kapatiyor.
_CALISTIR = {"text": True, "capture_output": True, "encoding": "utf-8", "errors": "replace"}


def _konsol_kodlamasi() -> None:
    """Kendi ciktimizi da kayipsiz DEGIL ama KESINTISIZ yazdirir.

    OLCULDU (2026-08-23): canli site 31 commit geride kalmisti. Sebep
    bu betigin `[2/5]` adiminda COKMESIYDI:

        UnicodeEncodeError: 'charmap' codec can't encode
        character '\\ufffd' ... cp1254

    Zincir su: alt surecin ciktisi UTF-8 cozulurken bozuk bayta
    `errors="replace"` ile U+FFFD konuyor (yukaridaki `_CALISTIR`).
    Sonra o metin cp1254 konsola YAZDIRILIYOR ve U+FFFD'nin cp1254
    karsiligi YOK -- print patliyor.

    Yani cozumleme duzeltilmisti, YAZDIRMA duzeltilmemisti. Betik
    wrangler'a hic gelmeden oluyordu ve `deploy` calismadigi icin
    hata ekranda "yayin basarisiz" gibi degil, sadece bir yigin izi
    olarak goruluyordu.

    NEDEN BURADA, `print` SARMALAYICISINDA DEGIL: patlayan tek yer
    bu dosya degil; `sys.stdout` kodlayicisini bastan tolere edici
    yapmak, sonradan eklenen her `print` icin de gecerli olur.
    Sarmalayici olsaydi bir sonraki yeni `print` yine patlardi.
    """
    for akis in (sys.stdout, sys.stderr):
        yeniden = getattr(akis, "reconfigure", None)
        if yeniden is None:      # yonlendirilmis akis her zaman desteklemez
            continue
        try:
            yeniden(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


_konsol_kodlamasi()


def insa_et() -> int:
    print("[2/5] site uretiliyor")
    sonuc = subprocess.run([sys.executable, str(KOK / "insa.py")], cwd=KOK, **_CALISTIR)
    print("  " + "\n  ".join((sonuc.stdout or "").strip().splitlines()))
    if sonuc.returncode:
        print(sonuc.stderr or "")
    return sonuc.returncode


def denetle() -> list[str]:
    print("[3/5] yayin oncesi denetim")
    bulgular: list[str] = []
    for dosya in CIKTI.rglob("*.html"):
        metin = dosya.read_text(encoding="utf-8")
        goreli = dosya.relative_to(CIKTI).as_posix()
        for iz, aciklama in ENGELLER:
            if iz in metin:
                bulgular.append(f"{goreli}: {aciklama}")
    return sorted(set(bulgular))


def dagit(kuru: bool) -> int:
    print("[4/5] Cloudflare'e yukleniyor")
    npx = shutil.which("npx")
    if not npx:
        print("  HATA: npx bulunamadi -- Node.js kurulu mu?")
        return 1

    komut = [npx, "--yes", "wrangler@latest", "deploy"]
    if kuru:
        komut.append("--dry-run")

    sonuc = subprocess.run(komut, cwd=KOK, **_CALISTIR)
    cikti = ((sonuc.stdout or "") + (sonuc.stderr or "")).strip()
    print("  " + "\n  ".join(cikti.splitlines()[-18:]))

    if "You are not authenticated" in cikti:
        print("\n  Once bir kez kimlik dogrulamasi gerekiyor:")
        print("      npx wrangler login")
    return sonuc.returncode


def depo_uyarisi() -> None:
    """Gonderilmemis commit varsa UYARIR -- CI onlari geri alir.

    NEDEN VAR
    ---------
    OLCULDU (2026-08-23): yerel dal `origin/main`in OTUZ ALTI commit
    onundeydi ve bu hicbir yerde gorunmuyordu. Sonucu su oldu:

      * `otomasyon.yml` saat basi kosuyor ve `origin/main`i checkout
        edip dagitiyor. Yani CI, iki gunluk tasarim calismasinin
        HICBIRINI gormeden eski kaynagi yayinliyordu.
      * Elle yapilan her dagitim en fazla bir saat yasiyordu; sonraki
        bot kosusu ustune eski yapiyi yaziyordu.

    Yani "yayinladim" demek yetmiyor: GONDERILMEMIS kaynak yayinda
    KALMIYOR. Bu satirlar o sessiz geri alisi gorunur kiliyor.

    NEDEN DURDURMUYOR: gonderemeden hizli bir deneme yayini yapmak
    mesru bir istek. Karar kullanicinin; bilgi eksikligi degil.
    """
    def _git(*a: str) -> str:
        try:
            s = subprocess.run(["git", *a], cwd=KOK.parent,
                               **_CALISTIR)
        except OSError:
            return ""
        return (s.stdout or "").strip() if s.returncode == 0 else ""

    dal = _git("rev-parse", "--abbrev-ref", "HEAD")
    if not dal or dal == "HEAD":
        return
    uzak = f"origin/{dal}"
    if not _git("rev-parse", "--verify", "--quiet", uzak):
        return                      # uzak uc yok -- soylenecek bir sey de yok

    for satir in _depo_mesajlari(_git("rev-list", "--count", f"{uzak}..HEAD"),
                                 _git("rev-list", "--count", f"HEAD..{uzak}"),
                                 uzak):
        print(satir)


def _depo_mesajlari(onde: str, geride: str, uzak: str) -> list[str]:
    """Sayilardan uyari satirlarini kurar -- `git` cagirmadan.

    Ayri durmasinin sebebi sinanabilirlik: uyarinin GERCEKTEN cikip
    cikmadigini olcmek icin depoyu 36 commit one almak gerekmesin.
    Uyarinin kendisi sessiz kalirsa, onu yakalayacak olan yine bu
    kontroldu -- yani sinanmayan bir uyari, olmayan bir uyaridir.
    """
    satirlar: list[str] = []
    if onde and onde != "0":
        satirlar += [
            f"  UYARI: {onde} commit {uzak} ucuna GONDERILMEDI.",
            "         Otomasyon uzak ucu dagitiyor; bir sonraki bot",
            "         kosusu bu yayini GERI ALIR.  ->  git push",
        ]
    if geride and geride != "0":
        satirlar += [
            f"  UYARI: {uzak} ucunda {geride} commit yerelde YOK.",
            "         Once birlestirin; yoksa botun urettigi veri",
            "         bu yayinda eksik kalir.",
        ]
    return satirlar


#: Canli sayfada aranan surum izi. `insa.py` stil dosyasinin sha1'ini
#: baglantiya yaziyor (bkz. `_surum`), yani bu jeton yayimlanan yapinin
#: PARMAK IZI: yerelde ve canlida ayni ise ayni yapi yayinda demektir.
_SURUM_IZI = re.compile(r"stil\.css\?v=(\w+)")


def _surum_izi(metin: str) -> str:
    e = _SURUM_IZI.search(metin)
    return e.group(1) if e else ""


def yayini_dogrula(adres: str = "https://netaris.net/") -> int:
    """Yayindan SONRA canli sayfayi cekip yerel ciktiyla karsilastirir.

    NEDEN VAR
    ---------
    OLCULDU (2026-08-23): canli site otuz bir commit geride
    duruyordu. Iki gunluk tasarim calismasinin hicbiri yayinda
    degildi ve bunu kimse fark etmedi -- cunku "yayinladim" bir
    NIYETTI, olcum degildi. Yayin betigi `[2/5]` adiminda cokuyor,
    wrangler'a hic gelmiyordu.

    Bu kontrol o bosluğu kapatiyor: dagitim bittikten sonra canli
    sayfa gercekten cekiliyor ve yerel ciktinin surum izini tasiyip
    tasimadigina BAKILIYOR.

    NEDEN AGA CIKAMAMAK BASARISIZLIK DEGIL
    --------------------------------------
    Dagitim basarili olup dogrulama agsizliktan yapilamadiginda
    "yayin basarisiz" demek yanlis olurdu. O durumda satir acikca
    DOGRULANAMADI yaziyor -- sessiz kalmiyor ama yalan da soylemiyor.
    Yanlis eslesme ise gercek bir olcum; orada donus degeri 1.
    """
    print("[5/5] canli sayfa dogrulaniyor")
    try:
        yerel = _surum_izi((CIKTI / "index.html").read_text(encoding="utf-8"))
    except OSError as e:
        print(f"  DOGRULANAMADI: yerel cikti okunamadi ({e.__class__.__name__})")
        return 0
    if not yerel:
        print("  DOGRULANAMADI: yerel ciktida stil surumu bulunamadi")
        return 0

    try:
        import httpx
        y = httpx.get(adres, timeout=25, follow_redirects=True,
                      headers={"cache-control": "no-cache"})
        y.raise_for_status()
        canli = _surum_izi(y.text)
    except Exception as e:      # ag katmani cok cesitli hata atiyor
        print(f"  DOGRULANAMADI: {adres} okunamadi ({e.__class__.__name__})")
        print("  Yayin yapildi ama canli surum GORULEMEDI.")
        return 0

    if canli == yerel:
        print(f"  canli surum yerelle ayni ({yerel})")
        return 0
    print(f"  UYUSMUYOR: yerel {yerel or '(yok)'} / canli {canli or '(yok)'}")
    print("  Yuklenen yapi canlida GORUNMUYOR -- yayin eksik kalmis olabilir.")
    return 1


def main() -> int:
    a = argparse.ArgumentParser(description="Netaris yayina alma")
    a.add_argument("--kuru", action="store_true", help="yuklemeden dene (dry-run)")
    a.add_argument("--zorla", action="store_true", help="denetim bulgularina ragmen devam et")
    args = a.parse_args()

    _node_yolu()

    # DEPO KONTROLU EN BASTA: insa birkac dakika suruyor ve uyari
    # sonda gorunse, kullanici zaten beklemis olurdu.
    print("[1/5] depo durumu")
    depo_uyarisi()

    if insa_et():
        return 1

    bulgular = denetle()
    if bulgular:
        for b in bulgular:
            print(f"  ENGEL  {b}")
        if not args.zorla:
            print("\nDAGITIM DURDURULDU. Duzeltip tekrar calistirin.")
            print("(bilerek devam etmek icin --zorla)")
            return 1
        print("\n  --zorla verildi, bulgulara ragmen devam ediliyor")
    else:
        print("  temiz")

    if dagit(args.kuru):
        return 1

    if args.kuru:
        print("\nKURU DENEME TAMAM (yukleme yapilmadi).")
        return 0

    if yayini_dogrula():
        return 1

    print("\nYAYINDA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
