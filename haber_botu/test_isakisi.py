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
# 6. BILANCO YALNIZCA BILDIRIM AYLARINDA KOSMALI.
#    Diger aylarda yeni bilanco gelmiyor; kosmak bos yere depoya
#    yazmak olur.
# --------------------------------------------------------------------
bil = cozulen.get("bilanco.yml")
if bil:
    aylar = [c.split()[3] for c in cronlar(bil) if len(c.split()) == 5]
    dogru("bilanco yalnizca bildirim aylarinda (3,5,8,11)",
          all(a == "3,5,8,11" for a in aylar) and aylar)

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


print(f"\n{_gecti} gecti, {_kaldi} kaldi")
sys.exit(1 if _kaldi else 0)