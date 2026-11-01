# -*- coding: utf-8 -*-
"""GERI YAZMA KAPSAMI -- yazdigi dosya listede YOKSA kayit yok olur.

KUSUR (olculdu 2026-10-31, aylardir yayindaydi)
-----------------------------------------------
`uret_bilanco_sayfa.ret_yaz` reddedilen AI yorumlarini
`haber_botu/netaris.db`ye yaziyor ve gerekcesi kendi uzerinde
yazili: "hangi sayilarin uydurulduğu ... OLCULEMIYOR". Ama BILANCO
IS AKISI o dosyayi geri yazmiyor -- `bilanco.yml` bes yolu asamaya
aliyordu ve veritabani onlardan biri degildi.

Sonuc: kayitlar kosucu sonunce yok oluyordu. Depodaki `ai_ret`
tablosunda bilanco adresli 99 satirin HEPSI "saglayici yok", yani
yalnizca YEREL kosulardan; CI'nin urettigi "girdide olmayan sayi"
redlerinden tek satir yok. Kosu #64'te dort sayfa bu sebeple
yazilmadi (GARFA, ARCLK, AAGYO, AYES) ve neden oldugu
okunamiyordu.

Hicbir yerde kirmizi gorunmedi: yazma BASARILI, dosya gercekten
olusuyor. Yalnizca kimse onu commit'lemiyordu.

KURAL
-----
Bilanco hattinin kosturdugu bir betik kalici bir dosyaya YAZIYORSA,
o yol `bilanco.yml`in geri yazma listesinde OLMALI.

Bu sinama kurali MEKANIK tutuyor: betik listesi de yazma hedefleri
de ELLE yazilmiyor -- ikisi de kaynaktan turetiliyor. Elle liste,
yeni bir yazma hedefi eklendigi gun sessizce eskiyen bir liste
demekti; kusurun ta kendisi buydu.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
_DEPO = _KOK.parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))

AKIS = _DEPO / ".github" / "workflows" / "bilanco.yml"

NL = chr(10)
_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


#: Listede OLMAMASI gereken yazma hedefleri -- her biri gerekceli.
#:
#: `netaris.db` BILINCLI olarak disarida: haber hatti onu her ~50
#: dakikada yaziyor ve 47 MB'lik ikili bir dosyayi iki akisin
#: yazmasi, birinin otekinin satirlarini SESSIZCE ezmesi demek.
#: Bilanco redleri bu yuzden `bilanco_ai_ret.json`a da yaziliyor.
MUAF = {
    "haber_botu/netaris.db":
        "haber hatti ayni dosyayi yaziyor -- iki yazici birbirini ezer",
}


def _akis_metni() -> str:
    return AKIS.read_text(encoding="utf-8")


def akis_betikleri(metin: str) -> list[str]:
    """Is akisinin KOSTURDUGU python betikleri -- metinden turetiliyor."""
    return sorted(set(re.findall(r"python ([A-Za-z0-9_/]+\.py)", metin)))


def geri_yazilan_yollar(metin: str) -> set[str]:
    """`for y in ... ; do` listesindeki yollar."""
    m = re.search(r"for y in (.*?); do", metin, re.S)
    if not m:
        return set()
    # Satir devam eden ters bolu ve yorum satirlari ayiklaniyor.
    ham = m.group(1).replace(chr(92), " ")
    return {p for p in ham.split() if "/" in p or p.endswith(".json")}


def yazma_hedefleri(betik: pathlib.Path) -> set[str]:
    """`SABIT.write_text(...)` bicimindeki yazma hedefleri.

    Sabit, MODULUN KENDISINDEN okunuyor (ice alinip `getattr`), yani
    yolun nasil kuruldugu burada ikinci kez yazilmiyor.
    """
    agac = ast.parse(betik.read_text(encoding="utf-8"))
    adlar = set()
    for d in ast.walk(agac):
        if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and d.func.attr in ("write_text", "write_bytes")
                and isinstance(d.func.value, ast.Name)):
            adlar.add(d.func.value.id)
    if not adlar:
        return set()
    import importlib                                    # noqa: PLC0415
    modul = importlib.import_module(betik.stem)
    cikti = set()
    for ad in adlar:
        deger = getattr(modul, ad, None)
        if not isinstance(deger, pathlib.Path):
            continue
        try:
            goreli = deger.resolve().relative_to(_DEPO)
        except ValueError:
            continue                  # depo disi: gecici dosya
        cikti.add(goreli.as_posix())
    return cikti


# ---------------------------------------------------------------
print("1. Akis metni okunabiliyor ve LISTELER BOS DEGIL")

_metin = _akis_metni()
_betikler = akis_betikleri(_metin)
_liste = geri_yazilan_yollar(_metin)

esit(len(_betikler) > 0, True, f"akış {len(_betikler)} betik koşturuyor")
esit(len(_liste) > 0, True, f"geri yazma listesi {len(_liste)} yol taşıyor")
# ATILLIK KONTROLU: bilinen bir yol listede GERCEKTEN bulunuyor mu?
esit("haber_botu/kaynak/bilanco_nobet.json" in _liste, True,
     "atıllık kontrolü: nöbet defteri listede bulunuyor")
esit("uret_bilanco_sayfa.py" in [pathlib.Path(b).name for b in _betikler],
     True, "atıllık kontrolü: sayfa betiği taranan betikler arasında")

# ---------------------------------------------------------------
print("")
print("2. HER yazma hedefi geri yazma listesinde")

_bakilan = 0
_disarida: list[tuple[str, str]] = []
for _b in _betikler:
    _yol = _DEPO / _b
    if not _yol.is_file() or _yol.parent != _KOK:
        continue                    # yalnizca haber_botu betikleri
    for _hedef in sorted(yazma_hedefleri(_yol)):
        _bakilan += 1
        if _hedef in MUAF:
            continue
        if _hedef not in _liste:
            _disarida.append((_b, _hedef))

esit(_bakilan > 0, True, f"{_bakilan} yazma hedefi çözüldü")
for _b, _h in _disarida:
    print(f"    LISTEDE YOK: {_h}  ({_b})")
esit(_disarida, [], "geri yazma listesinin dışında yazma hedefi yok")

# ---------------------------------------------------------------
print("")
print("3. MUAF listesi GERCEKTEN muaf -- sessizce genisletilemez")

# Muaf bir yol listede DE olmamali: oradaysa muafiyet gerekcesi
# (iki yazici birbirini ezer) ihlal edilmis olur.
for _m in MUAF:
    esit(_m in _liste, False, f"muaf yol listede değil: {_m}")
esit(sorted(MUAF), ["haber_botu/netaris.db"],
     "muaf listesi tek yoldan oluşuyor (büyürse gerekçesi yazılmalı)")

# ---------------------------------------------------------------
print("")
print("4. Ret defteri: SINIRLI ve en YENILER kaliyor")

import json                                             # noqa: E402
import tempfile                                         # noqa: E402

import uret_bilanco_sayfa as U                          # noqa: E402

with tempfile.TemporaryDirectory() as _t:
    _asil = U.RET_DEFTERI
    U.RET_DEFTERI = pathlib.Path(_t) / "ret.json"
    try:
        for _i in range(U.RET_DEFTERI_SINIRI + 15):
            U._ret_defterine_yaz(f"K{_i:03d}", "Örnek A.Ş.",
                                 "2026 3. çeyrek",
                                 "girdide olmayan sayi: 54", "model",
                                 "Ham metin " + str(_i))
        _d = json.loads(U.RET_DEFTERI.read_text(encoding="utf-8"))
        _k = _d["kayitlar"]
        esit(len(_k), U.RET_DEFTERI_SINIRI,
             f"defter {U.RET_DEFTERI_SINIRI} kayıtta duruyor")
        esit(_k[-1]["kod"], f"K{U.RET_DEFTERI_SINIRI + 14:03d}",
             "en YENİ kayıt sonda")
        esit(_k[0]["kod"], "K015", "en eski 15 kayıt düştü")
        esit(_k[-1]["neden"], "girdide olmayan sayi: 54",
             "sebep aynen saklanıyor")
        esit("Ham metin" in _k[-1]["ham"], True,
             "HAM METİN saklanıyor (teşhisin tek yolu)")

        # HAM METIN KIRPILIYOR: sinirsiz metin dosyayi sisirir.
        U._ret_defterine_yaz("UZUN", "X", "2026 3. çeyrek", "sebep",
                             "model", "A" * 5000)
        _k2 = json.loads(U.RET_DEFTERI.read_text(
            encoding="utf-8"))["kayitlar"]
        esit(len(_k2[-1]["ham"]), U.RET_HAM_SINIRI,
             f"ham metin {U.RET_HAM_SINIRI} karakterde kırpılıyor")
    finally:
        U.RET_DEFTERI = _asil

# YAZAMAMAK ISI DUSURMEZ: uretim raporlamadan onemli.
_asil = U.RET_DEFTERI
U.RET_DEFTERI = pathlib.Path("Z:") / "olmayan" / "dizin" / "ret.json"
try:
    U._ret_defterine_yaz("X", "X", "d", "n", "m", "h")
    esit(True, True, "yazılamayan defter koşuyu DÜŞÜRMÜYOR")
finally:
    U.RET_DEFTERI = _asil

# ---------------------------------------------------------------
print("")
print("5. `ret_yaz` deftere GERCEKTEN yaziyor")

# OLCUT, AKISIN KENDISI OLMALI. Yukaridaki bolum
# `_ret_defterine_yaz`i DOGRUDAN cagiriyor; cagri yeri `ret_yaz`tan
# silinse o iddialarin hepsi gecer ve hicbir red kaydedilmezdi --
# bu depoda "hesaplandi ama kullanilmadi" kusuru tekrar tekrar
# cikti.
with tempfile.TemporaryDirectory() as _t:
    _ad, _av = U.RET_DEFTERI, U.VT
    U.RET_DEFTERI = pathlib.Path(_t) / "ret.json"
    # GERCEK VERITABANINA DOKUNULMUYOR: `ret_yaz` SQLite'a da
    # yaziyor ve sinama uretim dosyasini kirletmemeli.
    U.VT = pathlib.Path(_t) / "sahte.db"
    try:
        U.ret_yaz("ARCLK", "Arçelik A.Ş.", "2026 3. çeyrek",
                  "girdide olmayan sayi: 11", "model-x",
                  "Net kâr 11 kat arttı.")
        _kk = json.loads(U.RET_DEFTERI.read_text(
            encoding="utf-8"))["kayitlar"]
        esit(len(_kk), 1, "ret_yaz tek kayıt bıraktı")
        esit(_kk[0]["kod"], "ARCLK", "kod doğru yazıldı")
        esit(_kk[0]["neden"], "girdide olmayan sayi: 11",
             "sebep doğru yazıldı")
        esit("11 kat" in _kk[0]["ham"], True,
             "HAM METİN ret_yaz üzerinden de saklanıyor")
    finally:
        U.RET_DEFTERI, U.VT = _ad, _av

# ---------------------------------------------------------------
print("")
print("6. SINAMALAR uretim DURUMUNA dokunmuyor")

# OLCULDU: `test_bilanco_atlama.py` `u.VT`yi gecici dizine
# ceviriyordu ama `RET_DEFTERI`yi yamalamiyordu. Sonuc: sinama
# URETIM defterine yaziyordu ve CI onu commit'lerdi -- gercek
# defterde 10 sahte kayit ("ADEL", "X") duruyordu.
#
# OLCUT, AST DEGIL DAVRANIS. Ilk yazim "dosya bir yerde
# `RET_DEFTERI`ye atama yapiyor mu" diye soruyordu ve mutasyon onu
# KACIRDI: yamayi silmek `finally` icindeki GERI KOYMA satirini
# oldugu gibi birakiyor, o da bir atama. Soru "yama var mi" degil,
# "uretim dosyasina DOKUNULDU MU" olmali -- ve bu ancak gercekten
# kosturup bakmakla olculur.
# IKINCI KEZ OLCULDU (2026-11-01) VE BASKA BIR DOSYAYA:
# `test_donem_celiskisi.py` `sayfa_tazele`yi gecici bir dosya
# uzerinde cagiriyordu, ama tazeleme okudugu yere degil
# `yayin.SITE_ICERIK` altindaki KANONIK yola yaziyor. Mutasyon
# sinamasinda kapi kaldirilinca sinama GERCEK icerik dizinine
# `2026-2-ceyrek-akbnk.md` yazdi.
#
# Kural bu yuzden TEK DOSYAYI degil URETIM DURUMUNU izliyor:
# red defteri VE yayin dizininin icerigi. Yazma yolu her
# eklendiginde kurali genisletmek gerekirse, kural eksik
# yazilmis demektir.
URETIM_YAZANLAR = ("ret_yaz", "yaz_sektorel", "sayfa_tazele",
                   "sirket_isle")

_KENDI = pathlib.Path(__file__).name
_cagiran = []
for _p in sorted(_KOK.glob("test_*.py")):
    if _p.name == _KENDI:
        continue
    _agac = ast.parse(_p.read_text(encoding="utf-8"))
    if any(isinstance(_d, ast.Call) and isinstance(_d.func, ast.Attribute)
           and _d.func.attr in URETIM_YAZANLAR
           for _d in ast.walk(_agac)):
        _cagiran.append(_p)

# ATILLIK KONTROLU: tarama GERCEKTEN cagiran dosya buluyor mu?
esit(len(_cagiran) > 0, True,
     f"atıllık kontrolü: üretime yazan {len(_cagiran)} sınama bulundu")

import hashlib                                          # noqa: E402
import subprocess                                       # noqa: E402

import yayin                                            # noqa: E402


def _durum() -> tuple:
    """Izlenen URETIM DURUMU: red defteri + yayin dizini.

    Dizin ADLARLA DEGIL ICERIKLE ozetleniyor: var olan bir sayfanin
    uzerine yazmak da kirliliktir ve ad listesi onu gormez.
    """
    defter = (U.RET_DEFTERI.read_bytes()
              if U.RET_DEFTERI.is_file() else None)
    dizin = {}
    if yayin.SITE_ICERIK.is_dir():
        for _y in sorted(yayin.SITE_ICERIK.glob("*.md")):
            dizin[_y.name] = hashlib.sha256(_y.read_bytes()).hexdigest()
    return defter, dizin


_ONCE_DEFTER, _ONCE_DIZIN = _durum()
esit(len(_ONCE_DIZIN) > 0, True,
     f"atıllık kontrolü: yayın dizininde {len(_ONCE_DIZIN)} sayfa var, "
     f"kirlilik ölçülebilir")

_kirleten = []
for _p in _cagiran:
    subprocess.run([sys.executable, "-X", "utf8", "-B", _p.name],
                   cwd=_p.parent, capture_output=True, timeout=600)
    _sd, _sz = _durum()
    _neden = []
    if _sd != _ONCE_DEFTER:
        _neden.append("red defteri")
        # SONRAKI OLCUM BOZULMASIN: durum geri aliniyor.
        if _ONCE_DEFTER is None:
            U.RET_DEFTERI.unlink(missing_ok=True)
        else:
            U.RET_DEFTERI.write_bytes(_ONCE_DEFTER)
    if _sz != _ONCE_DIZIN:
        _yeni = sorted(set(_sz) - set(_ONCE_DIZIN))
        _degisen = sorted(a for a in set(_sz) & set(_ONCE_DIZIN)
                          if _sz[a] != _ONCE_DIZIN[a])
        _silinen = sorted(set(_ONCE_DIZIN) - set(_sz))
        _neden.append(f"yayın dizini (yeni {_yeni}, değişen {_degisen}, "
                      f"silinen {_silinen})")
        # YALNIZCA SINAMANIN DOGURDUGU DOSYA SILINIYOR; var olan bir
        # sayfayi bu sinamadan geri yazmak, kaybi gizlemek olurdu.
        for _a in _yeni:
            (yayin.SITE_ICERIK / _a).unlink(missing_ok=True)
    if _neden:
        _kirleten.append((_p.name, "; ".join(_neden)))

for _n, _s in _kirleten:
    print(f"    URETIME YAZDI: {_n} -- {_s}")
esit([n for n, _s in _kirleten], [],
     "hiçbir sınama üretim durumunu değiştirmiyor")

# ---------------------------------------------------------------
print("")
print("7. ASAMA KAPISI AYNI LISTEDEN TURETILIYOR")

# KUSUR IKI KEZ YAYINA CIKTI.
#
# Geri yazmada ayni karari veren IKI liste vardi: asamalanan yollar
# (`YOLLAR`) ve asamadakini denetleyen BEYAZ LISTE. Biri guncellenip
# oteki unutuldugunda kosu duser ve geri yazma TUMDEN durur:
#
#   2026-10-13  `bilanco_nobet.json`   -> kosu dustu
#   2026-11-01  `bilanco_ai_ret.json`  -> kosu #65 dustu ve O KOSUDA
#               URETILEN SAYFALARIN HEPSI KAYBOLDU
#
# Ikincisi, is akisindaki yorum tam bu tuzagi ANLATIRKEN oldu --
# yani uyari yazmak yetmiyor. Kapinin olcutu artik `YOLLAR`dan
# turetiliyor ve bu sinama turetmenin DURDUGUNU tutuyor.
# KURAL HER GERI YAZAN AKISA UYGULANIYOR.
#
# `bilanco.yml` duzeltildikten sonra `otomasyon.yml`de AYNI desen
# duruyordu (iki liste, ayni karar). Orada henuz ayrismamislardi --
# ama kanitlanmis bir duzeltmeyi benzer yere tasimamak, bu depoda
# tekrarlayan bir kusur. Olcut DOSYA ADI DEGIL YAPIDIR: "asama
# kapisi olan her akis".
import shutil                                           # noqa: E402
import textwrap                                         # noqa: E402

_AKISLAR = sorted(p for p in (_KOK.parent / ".github" / "workflows")
                  .glob("*.yml")
                  if "KACAK=" in p.read_text(encoding="utf-8"))
esit(len(_AKISLAR) >= 2, True,
     f"atillik kontrolu: asama kapisi olan {len(_AKISLAR)} akis "
     f"bulundu ({[p.name for p in _AKISLAR]})")

_bash = shutil.which("bash")


def _bash_kos(betik: str) -> subprocess.CompletedProcess:
    """Betigi DOSYAYA yazip kosturur.

    `bash -c "..."` KULLANILMIYOR: Windows'ta argüman aktarimi ters
    bolulari yiyor ve olculdu -- `sed 's/.../\\\\&/g'` kabukta
    `\\&`ye dusup `.` yerine `&` ureten bir desen verdi. Yani
    SINAMANIN KENDI ARACI, sinanan kodu bozuyordu. Dosyadan
    kosturmak CI'daki hale de daha yakin.
    """
    import tempfile                                     # noqa: PLC0415
    with tempfile.TemporaryDirectory() as _t:
        _y = pathlib.Path(_t) / "dene.sh"
        _y.write_text(betik, encoding="utf-8", newline=chr(10))
        return subprocess.run([_bash, str(_y)], capture_output=True,
                              text=True, encoding="utf-8",
                              errors="replace", timeout=60)


#: Kapidan GECMEMESI gereken ornekler -- her biri AYRI bir kusuru
#: yakaliyor. Genel yollar, akis fark etmeksizin gecerli.
# ELLE YAZILAN SAYFA BURADA DEGIL: `otomasyon.yml` `site/icerik`
# dizininin TAMAMINI yaziyor, yani `site/icerik/sayfalar/...` o
# akista bu kapinin DISINDA eleniyor (ayri `ELLE` kapisi ve
# pathspec). Onu buraya koymak, akisa gore degisen bir beklentiyi
# genel bir kural gibi sunmak olurdu -- ve olculdu, yanlis alarm
# verdi. Her akista ELLE kapisinin VARLIGI asagida ayrica iddia
# ediliyor.
IZINSIZ = [
    "site/insa.py",                          # kaynak kod
    ".github/workflows/bilanco.yml",         # is akisinin kendisi
]


def _kil_payi(yol: str) -> list[str]:
    """Bir izinli yoldan turetilen KIL PAYI ornekleri.

    Hepsi kapidan GECMEMELI. Uretilmelerinin sebebi, deseni kuran
    her adimin ayri bir kusur uretebilmesi.
    """
    return [
        yol + "X",                 # onek eslesmesi (son baglayici yok)
        yol + "X/a.md",            # dizin adinin oneki
        yol.replace(".", "X", 1) if "." in yol else yol + "Xjson",
        "eski/" + yol,             # bas baglayici yok -> ortada eslesir
    ]


if _bash:
    for _akis in _AKISLAR:
        _m = _akis.read_text(encoding="utf-8")
        _yol_listesi = sorted(geri_yazilan_yollar(_m))
        esit(len(_yol_listesi) >= 3, True,
             f"[{_akis.name}] atillik kontrolu: {len(_yol_listesi)} "
             f"geri yazma yolu bulundu")

        _kapi = re.search(r"KACAK=\$\(git diff --staged --name-only"
                          r"(.*?)\|\| true\)", _m, re.S)
        esit(_kapi is not None, True, f"[{_akis.name}] asama kapisi bulundu")
        esit('"$DESEN"' in _kapi.group(1), True,
             f"[{_akis.name}] kapi turetilmis deseni kullaniyor")
        # ELLE YAZILMIS YOL KALMAMALI: kalirsa ikinci liste geri
        # gelmis demektir.
        _elle = [y for y in _yol_listesi if y in _kapi.group(1)]
        esit(_elle, [], f"[{_akis.name}] kapida elle yazilmis yol YOK "
                        f"({_elle})")

        # ELLE YAZILAN SAYFA KAPISI HER AKISTA DURMALI.
        #
        # Turetilmis desen `site/icerik`i tumden kabul edebiliyor
        # (otomasyon akisi oyle), yani elle yazilan sayfalari o kapi
        # ELEMEZ. Onlari eleyen AYRI kapi var ve kaybolmamali --
        # kaybolursa okurun elle yazdigi sayfalar otomasyonla
        # ezilir.
        esit("site/icerik/sayfalar/" in _m, True,
             f"[{_akis.name}] elle yazilan sayfa kapisi duruyor")

        # DAVRANIS: AKISIN KENDI TURETMESI KOSTURULUYOR.
        #
        # Metin denetimi "desen kullaniliyor" der ama desenin DOGRU
        # kuruldugunu soylemez -- kacis karakteri yanlis olsa da
        # iddia gecerdi.
        _blok = re.search(chr(10) + r"\s*DESEN=" + '""' + chr(10)
                          + r"(.*?" + chr(10) + r"\s*done" + chr(10) + ")",
                          _m, re.S)
        esit(_blok is not None, True,
             f"[{_akis.name}] DESEN turetme blogu bulundu")
        _kod = 'DESEN=""' + chr(10) + textwrap.dedent(_blok.group(1))
        _betik = ("set -u" + chr(10) + 'YOLLAR="' + " ".join(_yol_listesi)
                  + '"' + chr(10) + _kod + "printf '%s' \"$DESEN\"" + chr(10))
        _c = _bash_kos(_betik)
        esit(_c.returncode, 0,
             f"[{_akis.name}] turetme hatasiz kostu ({_c.stderr[:120]})")
        _desen = _c.stdout.strip()
        esit(bool(_desen), True, f"[{_akis.name}] desen uretildi")

        _ornek = [y + "/x.md" if "." not in y.rsplit("/", 1)[-1] else y
                  for y in _yol_listesi]
        _izinsiz = list(IZINSIZ)
        for _y in _yol_listesi:
            _izinsiz += _kil_payi(_y)
        # Kil payi uretimi bir IZINLI yolla cakisirsa o ornek elenir:
        # yanlis bir beklenti kurmaktansa olcmemek dogru.
        _izinsiz = [y for y in dict.fromkeys(_izinsiz) if y not in _ornek]

        _kontrol = ("set -u" + chr(10) + "DESEN='" + _desen + "'" + chr(10)
                    + "for y in " + " ".join(_ornek + _izinsiz) + "; do"
                    + chr(10)
                    + "  if printf '%s" + chr(92) + "n' \"$y\" "
                    + "| grep -qE \"$DESEN\"; then" + chr(10)
                    + '    echo "GECTI $y"' + chr(10) + "  else" + chr(10)
                    + '    echo "KACAK $y"' + chr(10) + "  fi" + chr(10)
                    + "done" + chr(10))
        _c2 = _bash_kos(_kontrol)
        _sonuc = dict(s.split(" ", 1)[::-1]
                      for s in _c2.stdout.split(chr(10)) if " " in s)
        _yanlis_kacak = [y for y in _ornek if _sonuc.get(y) != "GECTI"]
        esit(_yanlis_kacak, [],
             f"[{_akis.name}] izinli yollar kapidan GECIYOR "
             f"({_yanlis_kacak})")
        _yanlis_gecen = [y for y in _izinsiz if _sonuc.get(y) != "KACAK"]
        esit(_yanlis_gecen, [],
             f"[{_akis.name}] izinsiz yollar kapiya TAKILIYOR "
             f"({_yanlis_gecen})")
else:                                                   # pragma: no cover
    print("    (bash yok -- turetmenin DAVRANIS denetimi atlandi; "
          "metin denetimleri kostu)")

# ---------------------------------------------------------------
print("")
print(f"TUM TESTLER GECTI ({_gecti})")
