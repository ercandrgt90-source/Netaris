"""GitHub Actions is akislarinin sinamalari.

NEDEN BU DOSYA VAR
------------------
Is akislari sitenin CALISMASINI saglayan kod ama hicbir testi yoktu.
Kirildiklarinda kimse gormuyor: bir cron yanlis yazilirsa is
BASARISIZ OLMUYOR, sadece hic kosmuyor -- ve kosmayan bir is hicbir
yerde kirmizi gorunmez.

Bu sinif hatalarin ucu bu depoda GERCEKTEN yasandi:

  * `0 6 * 3,5,8,11 *` "uc ayda bir" sanildi. Gercekte "bildirim
    aylarinin HER GUNU" demek. Ayda ~1550 dakika yedi ve kotayi
    bitirdi; kota bitince BUTUN isler durdu, haber akisi dahil.
  * Cron'da gun-of-month ve gun-of-week BIRLIKTE verilince VEYA gibi
    davraniyor -- beklenmedik gunlerde kosuyor.
  * Es zamanlilik grubu bir sure ortakti; kuyruktaki bilanco kosusu
    her yeni haber kosusunda iptal ediliyordu ("Canceling since a
    higher priority waiting request exists"). Ayrildi ama
    `otomasyon.yml`in aciklamasi ESKI HALI anlatmaya devam etti --
    yani dogru yapilandirmayi yanlis anlatan bir not.

DEPO HERKESE ACIK (2026-08-27)
------------------------------
Bunun test acisindan iki sonucu var:

  1. Actions GUNLUKLERI de herkese acik. Gizli deger yazdiran bir
     adim, sirri dunyaya yayinlar.
  2. `pull_request` tetikleyicisi olsaydi, herhangi biri catal
     depodan istek acip is akisini kendi kodyla kosturabilirdi.

Ikisi de su an dogru; test ONLARI KORUYOR.

Calistirma:  python test_isakisi.py
"""

from __future__ import annotations

import pathlib
import re
import sys

_gecti = 0
_kaldi = 0


def dogru(aciklama: str, kosul) -> None:
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")


KOK = pathlib.Path(__file__).resolve().parent.parent
AKIS = KOK / ".github" / "workflows"

try:
    import yaml
except ImportError:
    print("pyyaml yok -- is akisi testleri ATLANDI")
    sys.exit(0)

dosyalar = sorted(AKIS.glob("*.yml"))
dogru("is akisi dosyalari bulundu", len(dosyalar) >= 2)

cozulen = {}
for p in dosyalar:
    try:
        # `on:` YAML'de True olarak cozuluyor (Norway problemi).
        cozulen[p.name] = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        dogru(f"{p.name} gecerli YAML", False)
        print(f"         {e}")
for ad, d in cozulen.items():
    dogru(f"{ad} gecerli YAML", d is not None)


def tetik(d: dict) -> dict:
    return d.get(True) or d.get("on") or {}


def cronlar(d: dict) -> list[str]:
    z = tetik(d).get("schedule") or []
    return [x.get("cron", "") for x in z if isinstance(x, dict)]


# --------------------------------------------------------------------
# 1. CATAL ISTEGI GIZLI DEGERE ULASAMAMALI.
#    Depo herkese acik: `pull_request` tetikleyicisi, herhangi birinin
#    kendi kodunu bizim sirlarimizla kosturmasi demek olurdu.
# --------------------------------------------------------------------
for ad, d in cozulen.items():
    dogru(f"{ad} pull_request ile tetiklenmiyor",
          "pull_request" not in tetik(d)
          and "pull_request_target" not in tetik(d))

# --------------------------------------------------------------------
# 2. GIZLI DEGER GUNLUGE YAZILMAMALI.
#    Gunlukler herkese acik. `secrets.X` yalnizca `env:` altinda
#    gecmeli; `echo`/`run` icinde gecmesi sizdirma riskidir.
# --------------------------------------------------------------------
SIR = re.compile(r"secrets[.][A-Z_]+")
for p in dosyalar:
    kotu = []
    for i, satir in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
        s = satir.strip()
        if not SIR.search(s):
            continue
        # `AD: ${{ secrets.X }}` bicimi guvenli -- ortam degiskeni.
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*[$][{][{]", s):
            continue
        kotu.append(f"{i}: {s[:60]}")
    dogru(f"{p.name} gizli degeri yalnizca env olarak gecirıyor", not kotu)
    for x in kotu:
        print(f"         {x}")

# --------------------------------------------------------------------
# 3. CRON'DA GUN-OF-MONTH VE GUN-OF-WEEK BIRLIKTE VERILMEMELI.
#
#    Cron'da ikisi de belirtilirse VEYA gibi davranir: "ayin 1'i VEYA
#    pazartesi". Beklenen ise VE'dir ve aradaki fark sessizdir --
#    is kosar, sadece yanlis gunlerde.
# --------------------------------------------------------------------
for ad, d in cozulen.items():
    for c in cronlar(d):
        alan = c.split()
        if len(alan) != 5:
            dogru(f"{ad} cron 5 alanli: {c}", False)
            continue
        _, _, gunay, _, gunhafta = alan
        dogru(f"{ad} cron gun-of-month/week cakismasi yok: {c}",
              gunay == "*" or gunhafta == "*")

# --------------------------------------------------------------------
# 4. ES ZAMANLILIK GRUPLARI AYRI OLMALI.
#
#    Ortak grup, kuyruktaki bilanco kosusunun her yeni haber kosusunda
#    iptal edilmesine yol aciyordu. Yazma yarisi es zamanlilikla degil
#    dar asamalama (`--ignore-removal`) ve push yeniden denemesiyle
#    cozuluyor -- ikisi de asagida sinaniyor.
# --------------------------------------------------------------------
gruplar = {ad: (d.get("concurrency") or {}).get("group")
           for ad, d in cozulen.items()
           if d.get("concurrency")}
dogru("es zamanlilik gruplari birbirinden AYRI",
      len(set(gruplar.values())) == len(gruplar))
if len(set(gruplar.values())) != len(gruplar):
    print(f"         {gruplar}")

# --------------------------------------------------------------------
# 5. YAZMA YARISI GERCEKTEN COZULMUS OLMALI.
#    Ayri gruplar ancak bu iki koruma varsa guvenli.
# --------------------------------------------------------------------
def _kod(metin: str) -> str:
    """Aciklama satirlarini atar.

    Ilk yazimda atmiyordu ve test kendi belgesini yakaladi: dosyalar
    `git add -A` ifadesini KULLANMAMAK GEREKTIGINI anlatmak icin
    yaziyor. Yasakladigi metni anlatan bir aciklama, ihlal degildir.
    """
    cikti = []
    for satir in metin.split(chr(10)):
        s = satir.split("#", 1)[0]
        if s.strip():
            cikti.append(s)
    return chr(10).join(cikti)


# GENIS ASAMALAMA YASAK. Dar olmanin birden fazla dogru yolu var:
# `--ignore-removal` ile kendi yollarini vermek, ya da tek bir acik
# yol eklemek (`kavram_gorseli.yml` boyle yapiyor). Kural "su bayragi
# kullan" degil, "HER SEYI asamaya alma" -- es zamanli kosan baska
# bir isin ciktisini da commit'lemek buradan cikiyor.
GENIS = ("git add -A", "git add .", "git add --all", "git commit -a")
for p in dosyalar:
    kod = _kod(p.read_text(encoding="utf-8"))
    if "git push" not in kod:
        continue
    bulunan = [g for g in GENIS if g in kod]
    dogru(f"{p.name} her seyi asamaya almiyor", not bulunan)
    if bulunan:
        print(f"         bulunan: {bulunan}")
    # YENIDEN DENEME: push tek satir ama bir DONGU icinde ve
    # reddedilince uzak uc yeniden aliniyor. Sayiya bakmak yanlis
    # olcut -- ilk yazimda oyleydi ve dogru kodu kirmizi dondurdu.
    dogru(f"{p.name} push reddedilirse yeniden deniyor",
          ("for " in kod or "while " in kod) and "git fetch" in kod)

    # ZORLAMA YASAK.
    #
    # Iki is akisi ayni depoya yaziyor. Zorlamak, digerinin ciktisini
    # SILMEK demek -- 2026-08-27'de tam bu yasandi ve 60 bilanco
    # sayfasi kayboldu. Dogru davranis yeniden denemek.
    ZORLAMA = ("push --force", "push -f ", "push --force-with-lease")
    zor = [z for z in ZORLAMA if z in kod]
    dogru(f"{p.name} push'u ZORLAMIYOR", not zor)
    if zor:
        print(f"         bulunan: {zor}")

# --------------------------------------------------------------------
# 6. BILANCO, BILDIRIM VE YAKLASMA AYLARINDA KOSMALI.
#
#    ESKI KURAL: yalnizca 3,5,8,11 -- "diger aylarda yeni bilanco
#    gelmiyor, kosmak bos yere depoya yazmak olur". O gerekce
#    YANLISTI: 3,5,8,11 KONSOLIDE bildirim son tarihleri. Konsolide
#    OLMAYAN sirketler donem bitiminden otuz gun sonra bildiriyor,
#    yani 9 aylik tablolar EKIM SONUNDA geliyor -- pencere ise
#    Kasim'da aciliyordu.
#
#    OLCULDU (2026-10-13): kullanici "bilancolar gelmeye basladi"
#    dedi; hat o gun kapaliydi, is akisi hic baslamiyordu bile.
#
#    Her donemin YAKLASMA ayi eklendi (2,4,7,10). O aylarda AGIR IS
#    YAPILMIYOR: `uret_bilanco` kendi kapisindan donuyor. Yapilan tek
#    sey nobetcinin BAKMASI -- sirket basina tek istek, 0,3 saniye.
#    Karar artik takvimde degil OLCUMDE.
# --------------------------------------------------------------------
BEKLENEN_AYLAR = "2,3,4,5,7,8,10,11"
bil = cozulen.get("bilanco.yml")
if bil:
    aylar = [c.split()[3] for c in cronlar(bil) if len(c.split()) == 5]
    dogru(f"bilanco bildirim + yaklasma aylarinda ({BEKLENEN_AYLAR})",
          all(a == BEKLENEN_AYLAR for a in aylar) and aylar)
    # HER AY ACIK OLMAMALI: bildirim gelmeyen aylarda kosmak kaynagi
    # ve kotayi bosa harcar. Dort ay (1,6,9,12) kapali kalmali.
    dogru("bilanco her ay kosmuyor",
          all(a != "*" for a in aylar))

# --------------------------------------------------------------------
# 7. GERI YAZMA, KOSU KESILSE BILE CALISMALI.
#
#    Olculdu (2026-08-27, kosu 33068672121): bilanco kosusu 50
#    dakikalik tavana carpip IPTAL edildi. "Siteyi kur" ve "Dagit"
#    adimlari atlandi -- ama geri yazma adimi `if: always()` tasidigi
#    icin o ana kadar uretilmis 9 sayfa depoya girdi ve kaybolmadi.
#
#    Bu bayrak olmasaydi 34 dakikalik AI uretimi cope giderdi. Biri
#    ileride "iptal olmus is neden hala yaziyor" deyip kaldirabilir;
#    kural onu durduruyor.
#
#    Dagitim adiminin `always()` OLMAMASI ise dogru: yarim kurulmus
#    bir siteyi canliya cikarmak, hic cikarmamaktan kotudur. Zaten
#    depoya yazilan sayfalar bir sonraki otomasyon kosusunda
#    kuruluyor ve yayimlaniyor.
# --------------------------------------------------------------------
for p_ in dosyalar:
    ham = p_.read_text(encoding="utf-8")
    if "git push" not in _kod(ham):
        continue
    # Geri yazma adimini bul: icinde `git push` gecen adim blogu.
    # ACIKLAMALAR ATILIYOR. Adimin kendi notu `always()` kelimesini
    # ANLATMAK icin yaziyor; ilk yazimda test o notu sayiyordu ve
    # `if: always()` satiri silindiginde yine yesil kaliyordu.
    # Bu tuzaga bu oturumda UC KEZ dusuldu -- kural her defasinda
    # yasakladigi metni aciklamak zorunda.
    adimlar = _kod(ham).split("- name:")
    yazan = [a for a in adimlar if "git push" in a]
    dogru(f"{p_.name} geri yazma adimi kosu kesilse de calisiyor",
          any("if: always()" in a for a in yazan))

# --------------------------------------------------------------------
# 8. ICERIK SILEN ADIM: SILDIGINI BILDIRMELI, GERI YAZMAYLA AYNI
#    KOSULU TASIMALI VE SILMESI SAHNELENMELI.
#
#    Olculdu (2026-08-28): `kumulatif_temizle.py` aylardir kosuyordu
#    ve TEK BIR SILMEYI bile depoya isleyememisti. Uc ayri eksik ust
#    uste binmisti:
#
#      * Geri yazma `git add --ignore-removal` kullaniyor; o bayrak
#        silmeleri sahnelemez. Yerel dogrulandi: temiz bir depoda
#        `--ignore-removal` yalnizca `A yeni.md` uretti, `D eski.md`
#        uretmedi.
#      * Temizlik adiminda `if: always()` YOKTU, geri yazmada VARDI.
#        Kosu uretim adiminda kesilince yeni ceyreklik sayfa depoya
#        giriyor, eski kumulatif sayfa kaliyordu.
#      * Sonuc canliya ciktı: ENDAE ve ENTRA'nin ayni donemi icin
#        IKISER analiz sayfasi yayimlandi -- biri "2026/6" etiketiyle,
#        yani okurun "ikinci ceyrek" sanacagi bicimde. Finans
#        sitesinde ayni sirketin ayni donemine dair iki farkli sayfa,
#        bicim hatasi degil GUVENILIRLIK hatasidir.
#
#    KURAL AYNI DOSYALARA DOKUNAN ADIMLAR HAKKINDA: silen adim ile
#    yazan adim ayni dosya kumesini degistiriyor. Kosullari
#    ayrisirsa, degisikligin yarisi islenip yarisi islenmeden kalir.
#
#    OLCUT NEDEN `.unlink()` DEGIL: ilk yazimda oyleydi ve UC ayri
#    betigi yanlislikla yakaladi -- `insa.py` ve `gorsel_uret.py`
#    de siliyor ama ikisi de `site/cikti` icinde, yani URETILEN ve
#    izlenmeyen dosyalari. Kaynaga bakarak "izlenen icerigi mi
#    siliyor" sorusunu guvenilir bicimde yanitlayamiyoruz.
#
#    Bu yuzden olcut DAVRANIS degil SOZLESME: sildigini `--liste` ile
#    bildiren bir arac, izlenen icerige dokundugunu beyan etmis
#    demektir. Kural o beyani takip ediyor.
#
#    Sozlesmenin kendisi de sabitlenmeli, yoksa `--liste`yi kaldiran
#    biri kurali sessizce bosa dusururdu: asagidaki CAPA testi,
#    bilanco hattinin temizleyiciyi `--liste` ile cagirmasini sart
#    kosuyor.
# --------------------------------------------------------------------
for ad, d in cozulen.items():
    for is_ in (d.get("jobs") or {}).values():
        basamaklar = is_.get("steps") or []
        # Geri yazma adimi: icinde `git push` gecen adim.
        yazanlar = [a for a in basamaklar
                    if "git push" in _kod(a.get("run") or "")]
        if not yazanlar:
            continue
        y = yazanlar[0]
        y_kod = _kod(y.get("run") or "")

        for a in basamaklar:
            # ACIKLAMALAR ATILIYOR. Bir adimin `run` blogu bu kurali
            # ANLATAN satirlar tasiyabilir; yasakladigi metni aciklayan
            # not ihlal degildir. Bu tuzaga bu depoda dort kez dusuldu.
            a_kod = _kod(a.get("run") or "")
            if "--liste" not in a_kod:
                continue
            etiket = f"{ad} silme adimi"
            dogru(f"{etiket} geri yazmayla AYNI kosulu tasiyor",
                  a.get("if") == y.get("if"))
            dogru(f"{etiket} bildirdigi silmeler sahneleniyor",
                  "git rm --cached" in y_kod)

# CAPA: sozlesmenin kendisi.
#
# Yukaridaki kural `--liste` gorunce isliyor. `--liste` kaldirilirsa
# kural bosa duser ve hata sessizce geri gelir -- bu oturumda "hicbir
# sey olcmeyen test" tuzagina dort kez dusuldu, kural kendi
# tetikleyicisini de korumak zorunda.
_bil = cozulen.get("bilanco.yml") or {}
_bas = [a for is_ in (_bil.get("jobs") or {}).values()
        for a in (is_.get("steps") or [])]
_temizlik = [a for a in _bas
             if "kumulatif_temizle.py" in _kod(a.get("run") or "")]
dogru("bilanco.yml kumulatif temizleyiciyi cagiriyor", len(_temizlik) == 1)
if _temizlik:
    _t = _kod(_temizlik[0].get("run") or "")
    dogru("bilanco.yml temizleyiciye --liste veriyor", "--liste" in _t)
    dogru("bilanco.yml temizleyiciye --uygula veriyor", "--uygula" in _t)

# --------------------------------------------------------------------
# 9. HER OTOMATIK TETIKLEYICI DAGITMALI.
#
#    Olculdu (2026-08-28): nobetcinin tetikledigi kosu 14:00'te
#    BASARIYLA bitti ama site 12:25'te kalmisti. Dagitim kapisi
#    soyleydi:
#
#        github.event_name == 'schedule' || inputs.yayinla
#
#    `repository_dispatch` ne `schedule`dir ne de `inputs` tasir --
#    yani nobetci tetikleyicisi eklendiginde bu satir guncellenmedi ve
#    kosu icerik uretip DAGITMADAN bitti.
#
#    Zarar tek bir kosu degil: icerik bayat kaldigi icin nobetci yarim
#    saat sonra YINE tetikliyor. Hepsi yesil donen, hicbiri yayimlamayan
#    sonsuz bir dongu -- ve disaridan sistem saglikli gorunuyor. Sessiz
#    kalan bir hat, kirmizi donen bir hattan tehlikelidir.
#
#    KURAL: dagitim kapisi tetikleyicileri SAYMAMALI. Elle kosuda
#    kullanicinin secimi gecerli; digerlerinde varsayilan DAGIT.
#    Sayan bir kapi, her yeni tetikleyicide yeniden unutulur.
# --------------------------------------------------------------------
#    KAPI IKI BICIMDE YAZILIYOR ve ikisi de sinaniyor:
#      * `otomasyon.yml`  bayragi kosullu uretiyor (`--yayinla`)
#      * `bilanco.yml`    adimin kendisini kosula bagliyor (`if:`)
#    Ikisi ayni karari veriyor, dolayisiyla ayni kurala tabi. Yalnizca
#    birine bakan bir sinama, hatanin digerine kacmasina izin verirdi.
# --------------------------------------------------------------------
# 8b. SINAMA, KENDISINI DUZELTECEK ADIMI ENGELLEYEMEZ.
#
#     `otomasyon.yml`de adim sirasi soyle:
#
#         Testleri calistir          <- kapi
#         Veri topla ve icerik uret  <- veriyi TAZELEYEN adim
#
#     `test_tazelik.py` "varlik serileri ritminde mi" diye soruyordu
#     ve CANLI DEPOYA bakiyordu. Veri bayatlayinca sinama dusuyor, is
#     akisi duruyor, duran is akisi veriyi tazeleyemiyor. Kisir dongu.
#
#     OLCULDU (2026-09-14): son basarili yazma 1 Eylul 23:04. On uc gun
#     boyunca HER kosu ayni kapida dustu. Nobetci calisiyordu ve her
#     yarim saatte tetikliyordu -- tetikledigi kosu da ayni yere
#     carpiyordu. Site 200 donuyor ama 12,7 gunluk donmus icerik
#     yayinliyordu; disaridan "calisiyor" gorunuyordu.
#
#     KURAL: bayatlik KODUN degil HATTIN durumudur. Yeri denetimdir --
#     raporlar, durdurmaz (`denetim.varlik_seri_tazeligi`). Bir sinama,
#     ancak boru hatti kosarsa saglanabilecek bir kosulu kapi yapamaz.
#
#     OLCUT: sinama dosyalari tazelik kararini (`bayat`) OKUYAMAZ.
#     Aciklamalar atiliyor -- bu notun kendisi kelimeyi anlatmak icin
#     yaziyor ve yasakladigi metni aciklayan bir not ihlal degildir.
# --------------------------------------------------------------------
_TAZELIK_KARARI = ('["bayat"]', "'bayat'", "bayat_seriler(", ".get(\"bayat\")")
for _p in sorted((KOK / "haber_botu").rglob("test_*.py")) + \
        sorted((KOK / "site").rglob("test_*.py")):
    # BU DOSYA KENDI TARAMASININ DISINDA.
    #
    # Kural, yasakladigi desenleri DIZGI olarak tasimak zorunda ve
    # `_kod` yalnizca aciklamalari atiyor -- dizgileri degil. Ilk
    # yazimda tarama kendi tanimini yakaladi ve kirmizi dondu. Bu
    # depoda ayni tuzaga defalarca dusuldu; farki, bu kez yasagin
    # KENDISININ kacinilmaz olmasi.
    if _p.name == pathlib.Path(__file__).name:
        continue
    _g = _kod(_p.read_text(encoding="utf-8", errors="replace"))
    _bulunan = [d for d in _TAZELIK_KARARI if d in _g]
    dogru(f"{_p.name} tazelik kararini kapi yapmiyor", not _bulunan)
    if _bulunan:
        print(f"         bulunan: {_bulunan}")

# --------------------------------------------------------------------
# 9b. FORMDAKI HER SECENEK, KODUN TANIDIGI BIR DEGER OLMALI.
#
#     `bilanco.yml`in "AI saglayici" listesi soyleydi:
#         ["varsayilan", "cloudflare", "anthropic"]   varsayilan: "varsayilan"
#
#     "varsayilan" bir saglayici DEGIL. Formu okuyan kisi bunu
#     "sistemin normal tercihi" diye anlar -- ki kodun normal tercihi
#     `yorumcu.saglayici()`de ANTHROPIC ONCELIKLI. Gercekte is akisi
#     onu CLOUDFLARE'e ceviriyordu. Secenegin adi, yaptiginin tersini
#     soyluyordu.
#
#     BEDELI OLCULDU (2026-08-28): kosu varsayilanla baslatildi, 44
#     dakika calisti, 328 sirketten 41'ini yazdi. 287 atlamanin 286'si
#     "girdide olmayan sayi" -- ucuz model verilmeyen rakamlar uretti.
#     Depodaki oranlar: anthropic %65, cloudflare %21.
#
#     KURAL: secenek listesi yalnizca kodun TANIDIGI degerleri
#     icermeli. Tanidigi kume `yorumcu.py`den TURETILIYOR, buraya
#     yazilmiyor -- elle yazilan bir kopya, kod degisince eskir ve bu
#     testin varlik sebebi tam olarak o.
# --------------------------------------------------------------------
# YOL DOGRULANIYOR, SESSIZCE ATLANMIYOR.
#
# Ilk yazimda `KOK / "ai" / "yorumcu.py"` deniyordu; `KOK` depo koku,
# dosya ise `haber_botu/ai/` altinda. Dosya bulunamayinca blok sessizce
# atlandi ve test HICBIR SEY OLCMEDI -- mutasyon (eski secenek
# listesini geri koymak) bile yakalanmadi. Varligi ayrica sinaniyor.
_yorumcu = KOK / "haber_botu" / "ai" / "yorumcu.py"
dogru("yorumcu.py bulundu", _yorumcu.is_file())
if _yorumcu.is_file():
    _kaynak = _yorumcu.read_text(encoding="utf-8")
    # `zorla == "cloudflare"` gibi karsilastirmalardan okunuyor.
    _taninan = set(re.findall(r'zorla\s*==\s*"([a-z]+)"', _kaynak))
    dogru("yorumcu.py'den saglayici kumesi okunabildi", len(_taninan) >= 2)
    for ad, d in cozulen.items():
        girdiler = (tetik(d).get("workflow_dispatch") or {}).get("inputs") or {}
        for g_ad, g in girdiler.items():
            if "saglayici" not in g_ad or not isinstance(g, dict):
                continue
            secenekler = [str(s) for s in (g.get("options") or [])]
            if not secenekler:
                continue
            kacak = [s for s in secenekler if s not in _taninan]
            dogru(f"{ad} '{g_ad}' secenekleri kodun tanidigi degerler",
                  not kacak)
            if kacak:
                print(f"         taninmayan: {kacak}  (taninan: "
                      f"{sorted(_taninan)})")
            dogru(f"{ad} '{g_ad}' varsayilani da taninan bir deger",
                  str(g.get("default", "")) in _taninan)

# --------------------------------------------------------------------
# 10. GERI YAZMA, BASKASININ BILEREK SILDIGINI DIRILTMEMELI.
#
#     `--ignore-removal` bir yonu koruyor -- baskasinin dosyasini
#     SILMIYORUZ -- ama tersi acikti: baskasinin SILDIGINI geri
#     ekliyordu.
#
#     Olculdu (2026-08-28), ayni dakikalar icinde:
#       14:44  bilanco kosusu `2026-6-garfa.md` ve `2026-6-yggyo.md`yi
#              sildi -- ceyreklikleri uretilmisti
#       14:45  otomasyon kosusu IKISINI DE geri ekledi (A)
#
#     Otomasyon 14:30'da checkout almisti ve dosyalar onun calisma
#     agacinda duruyordu; `reset` indeksi uzak uca esitleyince
#     `--ignore-removal` onlari YENI sanip asamaya aldi.
#
#     Sonucu tek bir commit degil: silme yalnizca bir sonraki es
#     zamanli kosuya kadar yasiyor. 63 sayfalik kumulatif gecis boyunca
#     her sayfa, her seferinde geri gelirdi -- ve hicbir kosu kirmizi
#     donmezdi.
#
#     KURAL: `--ignore-removal` kullanan her geri yazma, checkout'tan
#     bu yana uzak ucta silinen dosyalari calisma agacindan dusurmeli.
# --------------------------------------------------------------------
for p_ in dosyalar:
    kod = _kod(p_.read_text(encoding="utf-8"))
    if "--ignore-removal" not in kod:
        continue
    # ACIKLAMALAR ATILIYOR: adimlarin notlari `diff-filter=D` ifadesini
    # ANLATMAK icin yaziyor. Yasakladigi -- ya da zorunlu kildigi --
    # metni aciklayan bir not, kuralin karsilanmasi sayilamaz.
    dogru(f"{p_.name} uzak ucta silineni diriltmiyor",
          "--diff-filter=D" in kod and "GITHUB_SHA" in kod)
    # Bu kosunun YENIDEN URETTIGI dosya korunmali: silinmis olmasi,
    # taze icerigin atilmasi anlamina gelmemeli.
    dogru(f"{p_.name} bu kosunun urettigini koruyor",
          "git diff --quiet" in kod)

_KAPI = re.compile(r"\$\{\{([^{}]*--yayinla[^{}]*)\}\}")
for p_ in dosyalar:
    ham = p_.read_text(encoding="utf-8")
    d_ = cozulen.get(p_.name) or {}
    kapilar = []

    m_ = _KAPI.search(ham)
    if m_:
        kapilar.append(("bayrak", m_.group(1)))

    for is_ in (d_.get("jobs") or {}).values():
        for a in (is_.get("steps") or []):
            if "wrangler deploy" in _kod(a.get("run") or ""):
                kapilar.append(("adim", str(a.get("if") or "")))

    # Elle kosu disindaki her tetikleyici OTOMATIKtir.
    otomatik = {t for t in tetik(d_) if t != "workflow_dispatch"}
    for tur, ifade in kapilar:
        if not ifade:
            # Kosulsuz dagitim: her tetikleyicide dagitiyor demektir.
            dogru(f"{p_.name} dagitim kapisi ({tur}) kosulsuz", True)
        elif "!=" in ifade:
            # Ters cevrilmis kapi: yalnizca elle kosu disarida kalmali.
            dogru(f"{p_.name} dagitim kapisi ({tur}) yalnizca elle "
                  f"kosuyu ayiriyor", "workflow_dispatch" in ifade)
        else:
            eksik = sorted(t for t in otomatik if t not in ifade)
            dogru(f"{p_.name} dagitim kapisi ({tur}) hicbir otomatik "
                  f"tetikleyiciyi atlamiyor", not eksik)
            if eksik:
                print(f"         kapida gecmeyen: {eksik}")


# DURUMU KOSULAR ARASI TASIYAN DOSYA GERI YAZILMALI.
#
# CI her kosuda TAZE kopya aliyor. Bir arac "gecen sefer ne
# gormustum" diye bir dosyaya bakiyorsa, o dosya geri yazilmadiginda
# arac HER KOSUDA SIFIRDAN baslar ve hicbir degisimi fark edemez --
# sessizce olu olur.
#
# OLCULDU (2026-10-13): bilanco nobetcisi tam bu durumdaydi. Her
# sirketin en son hangi ceyregi bildirdigini `bilanco_nobet.json`
# icinde tutuyor ve yeni ceyregi ancak ONCEKI degerle karsilastirarak
# goruyor. Dosya listede olmadigi surece her kosu "ilk gorulme" sayar
# ve nobetci hicbir zaman tetiklemez.
#: Kosular arasinda YASAMASI gereken durum dosyalari. Her biri IKI
#: listede de bulunmali: `YOLLAR` (neyi asamaya al) ve `KACAK` kapisi
#: (asamada ne BULUNABILIR).
#:
#: `bilanco_miras_bozuk.json` circirin kendisi: onarilan sayfa
#: listeden cikariliyor ve bu budama geri yazilmazsa her kosuda
#: kayboluyor -- yani 204 sayfa kalici olarak korumasiz kalirdi.
_YASAMASI_GEREKEN = (
    ("haber_botu/kaynak/bilanco_nobet.json", "bilanco_nobet",
     "nöbet defteri"),
    ("site/bilanco_miras_bozuk.json", "bilanco_miras_bozuk",
     "miras listesi"),
)

_akislar = (KOK / ".github" / "workflows")
for _ad in ("otomasyon.yml", "bilanco.yml"):
    _m = (_akislar / _ad).read_text(encoding="utf-8")
    _kapi = _m.split("KACAK=")[-1][:600] if "KACAK=" in _m else ""
    for _yol, _iz, _anlam in _YASAMASI_GEREKEN:
        dogru(f"{_ad}: {_anlam} geri yazma listesinde", _yol in _m)
        # IKI LISTE VAR -- IKISI DE GUNCELLENMELI.
        #
        # `YOLLAR` neyi ASAMAYA ALACAGINI, kapi ise asamada NE
        # BULUNABILECEGINI soyluyor. 2026-10-13'te `bilanco.yml` tam
        # burada dustu: dosya birinci listeye eklenmis, kapiya
        # eklenmemisti ve kosu "beklenmeyen dosya asamada" diyerek
        # DURDU. Kapi dogru calisti; eksik olan ikinci listeydi.
        dogru(f"{_ad}: {_anlam} KAPIDAN da geciyor",
              _iz in _kapi if _kapi else True)

# ONARIM ADIMI IKI AKISTA DA OLMALI -- VE GERI YAZMADAN ONCE.
#
# Yayindaki 204 bilanco sayfasi bozuk (iki ayri donem ya da kapsam
# disi kilavuz) ve `bilanco_tazele --onarim` onlari model cagrisi
# olmadan yeniden kuruyor. Adim dusurulurse kural sikilasir ama
# YAYINDAKI icerik duzelmez -- bu depoda ayri bir ders olarak
# kayitli.
#
# `otomasyon.yml` icin ozellikle onemli: o akis bilanco adimlarini
# ATLIYOR (`--atla bilanco bilanco_sayfa`), yani onarim ancak AYRI
# bir adim olarak kosuyor. `bilanco.yml` ise onarimdan once butun
# sektorleri cekiyor ve kaynak ~100 istekten sonra reddediyor;
# onarim orada sifir sayfa yapabilir. Iki akista da bulunmasi
# tesadufi degil.
for _ad in ("otomasyon.yml", "bilanco.yml"):
    _m = (_akislar / _ad).read_text(encoding="utf-8")
    _o = _m.find("bilanco_tazele.py --onarim")
    dogru(f"{_ad}: onarim adimi var", _o != -1)
    _b = _m.find("test_bilanco_sayfa_saglam.py --budar")
    dogru(f"{_ad}: miras listesi budaniyor", _b != -1)
    dogru(f"{_ad}: budama onarimdan SONRA", _o != -1 and _b > _o)
    # HAT KENDINI IYILESTIRMELI.
    #
    # Koruma (`site/test_bilanco_sayfa_saglam.py`) sinama adiminda,
    # yani onarimdan ONCE kosuyor. Bir sayfa yeni bozulursa koruma
    # hakli olarak dusuyor ve kosu kirmiziya gidiyor.
    #
    # Ama onarim `always()` ile kostugu icin O KOSUDA sayfayi
    # duzeltiyor, geri yazma da `always()` oldugu icin duzeltme
    # depoya giriyor ve BIR SONRAKI kosu yesil donuyor. Kosul
    # kaldirilirsa hat kendini iyilestirmeyi birakir ve kirmizi
    # elle mudahale bekler.
    for _ara, _etiket in (("bilanco_tazele.py --onarim", "onarim"),
                          ("test_bilanco_sayfa_saglam.py --budar",
                           "budama")):
        _i = _m.find(_ara)
        _bas = _m.rfind("- name:", 0, _i)
        dogru(f"{_ad}: {_etiket} adimi kosu kesilse de calisiyor",
              _i != -1 and "always()" in _m[_bas:_i])
    # GERI YAZMADAN ONCE: sonra olsaydi onarilan sayfalar
    # islenmemis kalirdi ve her kosu ayni isi bastan yapardi.
    #
    # ADIM SATIRI araniyor, metinde "geri yaz" gecen her yer DEGIL.
    # Ilk yazim `_m.find("geri yaz")` kullaniyordu ve dosyadaki
    # YORUMLARA takiliyordu -- yani olcum yanlis yeri gosteriyordu.
    _gs = [m.start() for m in
           re.finditer(r"^      - name:.*geri yaz", _m, re.M)]
    dogru(f"{_ad}: geri yazma adimi bulundu", bool(_gs))
    if _gs:
        dogru(f"{_ad}: onarim geri yazmadan ONCE", _o < min(_gs))

# ONARIM KUYRUGU KENDINI KAPATIYOR MU -- arac duzeyinde.
# Kuyruk bos donunce arac hicbir istek atmadan cikmali; yoksa adim
# kalici bir kaynak yuku olurdu.
_tz = (KOK / "haber_botu" / "bilanco_tazele.py").read_text(encoding="utf-8")
dogru("bilanco_tazele: bos kuyrukta erken donuyor",
      "onarılacak sayfa YOK" in _tz)

# NOBETCI CEKIMDEN ONCE KOSMALI -- sonra kossaydi bayrak bir sonraki
# kosuya kadar islenmezdi ve "geldikce cikalim" bir tur gecikirdi.
_b = (_akislar / "bilanco.yml").read_text(encoding="utf-8")
_n = _b.find("bilanco_nobetci.py")
_v = _b.find("uret_bilanco.py")
dogru("bilanco.yml: nobetci cekimden ONCE", _n != -1 and _v != -1 and _n < _v)

# SAYFALAR VERIDEN ONCE KOSMALI -- KAYNAGIN IZNI SINIRLI.
#
# Iki adim ayni kaynaga gidiyor ve kaynak kosu basina ancak belirli
# sayida istege cevap veriyor. Veri adimi 324 sirketi x uc tablo
# denemek istedigi icin izni TEK BASINA tuketiyor; sayfa adimi
# ardindan ac kaliyor.
#
# OLCULDU (2026-10-14): 15 Eylul'den 14 Ekim'e kadar sayfa adimi
# TOPLAM iki sayfa yazdi. Ozetteki 324 sirketten 109'unun HIC sayfasi
# yoktu -- dort futbol kulubu dahil. Ayni kosu yerelde veri adimi
# OLMADAN denendi: İletişim'in yedi sirketi de sorunsuz cekildi.
#
# Sira tersine donerse okur yeni sayfa gormemeye baslar ve bu
# SESSIZ bir gerileme: kosu yesil kalir.
_sy = _b.find("uret_bilanco_sayfa.py")
_vr = _b.find("uret_bilanco.py --hepsi")
dogru("bilanco.yml: sayfa adimi veri adimindan ONCE",
      _sy != -1 and _vr != -1 and _sy < _vr)

# TAKVIM IKI YERDE OLMAMALI. Cron, `donem_acik`in yerine gecmemeli:
# yaklasma aylari acik olmali ki nobetci BAKABILSIN.
for _ay in ("2", "4", "7", "10"):
    dogru(f"bilanco.yml cron {_ay}. ayi kapsiyor",
          f",{_ay}," in _b or f"* {_ay}," in _b)

# ============================================================
# ALARM NE OLDUGUNU SOYLEMELI -- "BIR SEY BOZUK" YETMIYOR.
#
# Olculdu (2026-10-20): dagitim yedi buçuk saat durdu. Alarm CALISTI,
# kayit 12:59'da acildi. Ama govdesinde yalnizca "dusen adimi gormek
# icin kosu ozetine bakin" yaziyordu; hangi sinamanin dustugu
# YALNIZCA kosu gunlugundeydi ve gunluk indirmek yetki istiyor.
#
# Alarmin degeri "calmasi" degil, OKUNUNCA NE YAPILACAGINI
# soylemesi. Asagidaki iddialar o bilgi yolunun her halkasini
# tutuyor; biri kopsa alarm yine calar ama yine hicbir sey anlatmaz
# -- ve bu, sessiz kalmasindan daha sinsi olur.
# ============================================================
print("")
_oto = (AKIS / "otomasyon.yml").read_text(encoding="utf-8")

# 1. YETKI. Acik bir `permissions` blogu varken VERILMEYEN yetki
#    kapalidir. `actions: read` olmadan `gh api .../jobs` 403 doner
#    ve alarm sessizce "adim listesi alinamadi" yedegine duser:
#    ozellik calisir GORUNUR, hicbir zaman calismaz.
dogru("otomasyon.yml: alarm icin `actions: read` yetkisi var",
      "actions: read" in _oto)

# 2. SORGU. Dusen adimin adi kosunun kendi is listesinden okunuyor.
dogru("otomasyon.yml: alarm dusen ADIM adini sorguluyor",
      "/jobs" in _oto and 'conclusion=="failure"' in _oto)
# Ad listesi GOVDENIN ICINDE olmali. Dosyada bir yerde gecmesi
# yetmez: `adimlar=$(...)` atamasi ve `[ -z "$adimlar" ]` yedegi de
# ayni dizgiyi tasiyor, yani "dosyada var mi" iddiasi govdeden
# silinse bile YESIL kalirdi -- olculdu, mutasyon kacti.
_gv = re.search('govde="Koşu: [$]kosu(.*?)"', _oto, re.S)
dogru("otomasyon.yml: alarm govdesi bulundu", _gv is not None)
dogru("otomasyon.yml: adim adlari kayit GOVDESINE giriyor",
      _gv is not None and "$adimlar" in _gv.group(1))
dogru("otomasyon.yml: dusen sinamalar kayit GOVDESINE giriyor",
      _gv is not None and "$sinamalar" in _gv.group(1))

# 3. SOZLESME: koscu ile is akisi AYNI dosya adinda anlasmali.
#
# Iki yerde ayri ayri yazilmis bir dosya adi, bu depodaki tanidik
# kusur sinifi: biri degisir, oteki eski adi okumaya devam eder ve
# hicbir sey kirmizi yanmaz -- alarm yalnizca eksik bilgiyle calar.
# Ad KAYNAKTAN okunuyor, buraya elle yazilmiyor.
_ks = (KOK / "site" / "cikti_sinamalari.py").read_text(encoding="utf-8")
_md = re.search(r'_DUYURU = "([^"]+)"', _ks)
dogru("cikti_sinamalari.py: duyuru dosyasinin adi tanimli", _md is not None)
if _md:
    dogru("otomasyon.yml alarmi ayni dosyayi okuyor (" + _md.group(1) + ")",
          _md.group(1) in _oto)
# CAGRI ARANIYOR, TANIM DEGIL. "_duyur(" dizgisi `def _duyur(`
# satirinda da gecer, yorum satirina alinmis bir cagrida da --
# ikisinde de iddia yesil kalirdi. Olculdu, mutasyon kacti.
dogru("cikti_sinamalari.py: dusen adlari gercekten yaziliyor",
      re.search(r"(?m)^ {4}_duyur[(]", _ks) is not None
      and "GITHUB_STEP_SUMMARY" in _ks)


print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)