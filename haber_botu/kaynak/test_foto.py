"""foto.py testleri -- AGA CIKMAZ.

Buradaki hatalarin ortak ozelligi SESSIZ olmalari: yanlis gorsel de,
atifsiz gorsel de sayfada duzgun gorunur. Ucu de gercekten yasandi.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import foto

_KAYNAK = pathlib.Path(foto.__file__).read_text(encoding='utf-8')  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def dogru(ad, kosul):
    es(ad, bool(kosul), True)


# ---------------------------------------------------------------- editoryal
#
# "strait of hormuz" aramasindan gelen 48 sonucun 18'i ABD savas
# gemisiydi. Petrol sevkiyati haberinin yaninda savas gemisi, haberin
# SOYLEMEDIGI bir sey soyler.
print("Editoryal suzgec -- askeri ve facia gorselleri elenmeli")
for baslik in (
    "CVN 69 transits the Strait of Hormuz",
    "USS Tempest (PC 2) transits the Strait of Hormuz",
    "USCG Fast Response Cutter Glen Harris transit the Strait",
    "HMS Middleton in the Strait of Hormuz",
    "Flickr - Official U.S. Navy Imagery - U.S. Navy ships transit",
    "Sailors aboard the guided-missile destroyer",
    "The Eisenhower Carrier Strike Group Transits the Strait",
):
    dogru(f"red: {baslik[:38]}",
          not foto._editoryal_uygun({"title": baslik, "tags": []}))

# Ayni aramadan gelen dogru gorseller TUTULMALI. Suzgec fazla genis
# olsaydi havuz bosalirdi ve bu, cozdugu sorundan kotu olurdu.
print("\nEditoryal suzgec -- konuya ait gorseller GECMELI")
for baslik in (
    "Strait of Hormuz (MODIS 2020-12-04).jpg",
    "Crude oil, condensate, and petroleum products transported through",
    "ISS-46 Gulf of Oman with Strait of Hormuz at night.jpg",
    "Prime Minister Keir Starmer attends Strait of Hormuz Summit",
    "Bandar Imam Khomeini petrochemical complex.jpg",
):
    dogru(f"gecer: {baslik[:38]}",
          foto._editoryal_uygun({"title": baslik, "tags": []}))

# Facia gorseli ADINDA facia gecmeyebilir: "Iran Air 655" bir yolcu
# ucagi faciasi ama dosya adi bunu soylemiyor -- KATEGORI soyluyor.
# ARSIV. 2026 istihdam raporunun yaninda 1913 grev fotografi, okura o
# donemin haberi gibi gorunur. NFP havuzunun yarisi boyle doldu.
print("\nEditoryal suzgec -- arsiv gorselleri elenmeli")
for baslik in (
    "Garment Workers on Strike, New York City circa 1913.jpg",
    "Damm factory workers 1920.jpg",
    "1896 Strait of Hormuz map (cropped).jpg",
    "Floor of Toronto Stock Exchange 1956.jpg",
    "J. M. Price Grocery Store, Toledo, Ohio (approximately 1882)",
):
    dogru(f"arsiv: {baslik[:36]}",
          not foto._editoryal_uygun({"title": baslik, "tags": []}))
dogru("guncel yil geciyor", foto._editoryal_uygun(
    {"title": "Supermarket - Massachusetts - 2024.jpg", "tags": []}))

print("\nEditoryal suzgec -- kategoriden yakalama")
dogru("kategori taraniyor", not foto._editoryal_uygun({
    "title": "Iran Air 655 Strait of hormuz 80.jpg",
    "tags": ["Maps of Oman|Incident map images that should use vector"]}))

# ------------------------------------------------------------------- atif
#
# CC BY atfi ZORUNLU. Desen yalnizca Openverse cumlesine gore yazilmisti
# ve Commons'tan gelen ondort gorselin hepsi "bilinmeyen" diye basildi.
print("\nAtif -- iki kaynagin iki bicimi de okunmali")
ov = foto.Foto(
    dosya="/statik/foto/x.jpg",
    atif='"Oil rig" by Jane Doe is licensed under CC BY 2.0.',
    lisans="by", kaynak="https://example.org/x")
es("openverse bicimi", ov.kisa_atif, "Jane Doe · BY")

wc = foto.Foto(
    dosya="/statik/foto/y.jpg",
    atif="U.S. Energy Information Administration · Public domain",
    lisans="pdm", kaynak="https://commons.wikimedia.org/wiki/File:Y")
es("commons bicimi", wc.kisa_atif,
   "U.S. Energy Information Administration · PDM")

dogru("atifsizda bile lisans basiliyor",
      "bilinmeyen" in foto.Foto(dosya="a", atif="", lisans="by",
                                kaynak="b").kisa_atif)

# Eski kayitlar `kunye` alani olmadan yazildi; okunabilmeliler.
print("\nKayit bicimi -- eski kayitlar okunabilmeli")
try:
    foto.Foto(dosya="a", atif="b", lisans="by", kaynak="c")
    gecti += 1
except TypeError as e:                                    # pragma: no cover
    kaldi.append(f"eski kayit okunamadi: {e}")

# --------------------------------------------------------------- havuz adi
#
# `HAVUZ_OZEL`de yazim hatasi SESSIZ kalir: havuz varsayilan boyutta
# doldurulur ve kimse fark etmez.
print("\nHavuz adlari -- HAVUZ_OZEL anahtarlari tanimli olmali")
bilinen = set(foto.VARLIK_ARAMA) | set(foto.KONU_ARAMA)
for anahtar in foto.HAVUZ_OZEL:
    dogru(f"'{anahtar}' sorgusu var", anahtar in bilinen)

# Commons lisans eslemesi kabul listemize dusmeli.
print("\nLisans -- Commons kodlari kabul listesine cevrilmeli")
#
# Bu ceviri olmadan Commons'in butun CC BY gorselleri reddediliyordu:
# "european central bank" aramasinin 24 sonucunun 24'u eleniyor ve EA
# havuzu bos kaliyordu. Sebep "uygun lisansli gorsel yok" degil, kodu
# tanimamamizdi -- havuzlarin yalnizca kamu mali arsiv gorselleriyle
# dolmasinin sebebi de buydu.
for ham, beklenen in (
    ("cc0", "cc0"), ("cc-zero", "cc0"), ("pd", "pdm"),
    ("public domain", "pdm"), ("pd-old", "pdm"),
    ("cc-by-4.0", "by"), ("cc-by-2.0", "by"), ("by", "by"),
    ("cc-by-sa-3.0", "by-sa"), ("cc-by-sa-4.0", "by-sa"), ("by-sa", "by-sa"),
):
    es(f"'{ham}'", foto.lisans_kodu(ham), beklenen)

# ND ve NC KABUL EDILMEZ: kart icinde kirpiyoruz (turev tartismasi) ve
# site ticari sayilabilir.
for ham in ("cc-by-nd-4.0", "cc-by-nc-2.0", "cc-by-nc-sa-4.0"):
    dogru(f"'{ham}' reddediliyor",
          not foto._lisans_uygun({"license": ham}))
dogru("cc-by-4.0 kabul ediliyor",
      foto._lisans_uygun({"license": "cc-by-4.0"}))
for kod in ("by", "by-sa", "cc0", "pdm"):
    dogru(f"'{kod}' kabul ediliyor",
          foto._lisans_uygun({"license": kod, "license_version": ""}))
dogru("'by-nd' reddediliyor",
      not foto._lisans_uygun({"license": "by-nd", "license_version": "4.0"}))

# ---------------------------------------------------- turev kimlik bicimi
#
# Commons dosya sayfasina IKI bicimde baglanti veriliyor: baslikla
# (/wiki/File:...) ve sayfa kimligiyle (?curid=...). `boy_uret` uzun
# sure yalnizca birincisini taniyordu; curid'li kayit "bekleyen"
# listesine hic girmedigi icin `o/` ve `k/` surumu KALICI olarak
# uretilmiyordu. Sablon turevsiz gorseli atliyor -- sonuc gorselsiz
# sayfa, hem de tek bir uyari satiri bile olmadan.

dogru("curid adresinden sayfa kimligi okunuyor",
      foto._commons_kimligi(
          "https://commons.wikimedia.org/w/index.php?curid=27323") == "27323")
dogru("baska parametrelerin arasindaki curid de okunuyor",
      foto._commons_kimligi(
          "https://commons.wikimedia.org/w/index.php?title=X&curid=99") == "99")
dogru("baslikli adres kimlik yoluna DUSMUYOR",
      foto._commons_kimligi(
          "https://commons.wikimedia.org/wiki/File:Oil_Drilling.jpg") == "")
dogru("commons disi adres kabul edilmiyor",
      foto._commons_kimligi("https://example.com/w/?curid=5") == "")
dogru("bos adres bos donuyor", foto._commons_kimligi("") == "")

# Baslik yolu bozulmadi mi -- 460 kayit ondan geciyor.
dogru("baslikli adres hala basliga cevriliyor",
      foto._commons_basligi(
          "https://commons.wikimedia.org/wiki/File:Oil_Drilling.jpg")
      == "File:Oil Drilling.jpg")
dogru("curid adresi baslik URETMIYOR",
      foto._commons_basligi(
          "https://commons.wikimedia.org/w/index.php?curid=27323") == "")

# HER kayit iki yoldan BIRINE dusmeli. Dusmeyeni indirmek imkansiz ve
# bu sessiz bir kayip olurdu.
_kayit = foto.Kayit()
_yetim = [f.get("dosya", "") for l in _kayit.veri.values() for f in l
          if not foto._commons_basligi(f.get("kaynak", ""))
          and not foto._commons_kimligi(f.get("kaynak", ""))]
es("havuzdaki her gorsel indirilebilir bir kimlik tasiyor",
   sorted(_yetim), [])


# ------------------------------------------------------------------
# HAYVAN GORSELI REDDEDILIR.
#
# Kullanici bildirdi (2026-08-27): "finans arastirma platformuyuz,
# sincap resmi var". Havuzda iki gorsel vardi ve ikisi de arama
# terimini BASLIGINDA tasiyordu -- yani Commons eslesmesi dogru,
# gorselin KONUSU yanlisti:
#
#   "washington capitol" -> "Capitol Hill Squirrel"
#   "tax forms"          -> "Gillie 'helping' with the tax forms" (kedi)
# ------------------------------------------------------------------
print("\nEditoryal suzgec -- hayvan gorselleri REDDEDILMELI")
for baslik in (
    "Flickr - USCapitol - Capitol Hill Squirrel.jpg",
    "Kitten on a keyboard",
    "Wildlife of the Persian Gulf",
    "Birds over the harbour",
):
    dogru(f"red: {baslik[:38]}",
          not foto._editoryal_uygun({"title": baslik, "tags": []}))

# KANIT BASLIKTA DEGIL KATEGORIDE OLABILIR.
#
# Kedi gorselinin adi `Gillie "helping" with the tax forms` -- icinde
# hicbir hayvan kelimesi yok. Hayvan oldugunu yalnizca Commons
# kategorisi soyluyor ("Lying cats"). `_editoryal_uygun` bu yuzden
# baslik VE etiketleri birlikte tariyor; yalnizca basliga bakan bir
# suzgec bu gorseli kacirirdi.
dogru("kategoriden yakalaniyor (baslikta hayvan kelimesi yok)",
      not foto._editoryal_uygun({
          "title": 'Gillie "helping" with the tax forms (4316094077).jpg',
          "tags": ["Lying cats", "Flickr images reviewed by trusted users"]}))

dogru("ayni baslik, kategorisiz -> gecer (kanit yok)",
      foto._editoryal_uygun({
          "title": 'Gillie "helping" with the tax forms (4316094077).jpg',
          "tags": []}))

# ------------------------------------------------------------------
# FINANS KELIMELERI ELENMEMELI -- ALT DIZGE TUZAGI.
#
# Hayvan adlarinin cogu, sitenin en cok kullandigi kelimelerin
# ICINDE geciyor:
#
#     cat ⊂ indiCATor, alloCATion, CATegory
#     pet ⊂ PETroleum, comPETition
#     ant ⊂ significANT, quANTitative
#
# Duz dizge aramasi bu sitede felaket olurdu; desen sinir isaretli
# (``) yazildi. Bu blok, birinin ileride sinirlari kaldirmasini
# engelliyor.
#
# BOGA ve AYI bilerek listede YOK: piyasa terimi ve Wall Street
# bogasi mesru bir finans gorseli.
# ------------------------------------------------------------------
print("\nEditoryal suzgec -- finans kelimeleri GECMELI")
for baslik in (
    "Leading indicator dashboard 2026",
    "Allocation of capital across sectors",
    "Category of assets under management",
    "Petroleum refinery at dusk",
    "Cattle futures trading floor",
    "Charging Bull statue Wall Street",
    "Bear market chart 2026",
    "Zoology department budget hearing",
    "Quantitative easing explained",
    "Horsepower and engine output statistics",
):
    dogru(f"gecer: {baslik[:38]}",
          foto._editoryal_uygun({"title": baslik, "tags": []}))

# ------------------------------------------------------------------
# YAYIN HAVUZU BIRE DUSMEZ.
#
# `havuz_yayin` bir TERCIH MERDIVENI: once atifsiz+net, sonra net,
# sonra atifsiz, sonra hepsi. Once "ilk dolu katman kazanir" diye
# yaziliydi ve bedeli olculdu (2026-08-28):
#
#     Enerji           20 gorsel -> 1
#     Kripto varliklar  9 gorsel -> 1
#     TCMB             13 gorsel -> 1   (13 konuda ayni desen)
#
# Tek bir fotograf hem atifsiz hem 1200 piksel oldugunda havuz o teke
# iniyor, digerleri tamamen eleniyordu. `sec()` havuzdan uniform
# seciyor; havuz birse HER SAYFA ayni gorseli aliyor. Enerji gorseli
# 89 sayfada gorunuyordu, 78'i analiz sayfasi.
#
# Tercih sirasi KORUNUYOR: iyi katman havuzu dolduruyorsa alt katmana
# hic inilmiyor. Yalnizca havuz dar kalinca bir sonraki ekleniyor --
# "atifli ya da biraz yumusak bir gorsel", "ayni gorsel yuzuncu
# kez"den iyidir.
# ------------------------------------------------------------------
import json as _json          # noqa: E402
import tempfile as _tmp       # noqa: E402


def _kayit(ogeler):
    y = pathlib.Path(_tmp.mkdtemp()) / "k.json"
    y.write_text(_json.dumps({"K": ogeler}), encoding="utf-8")
    return foto.Kayit(y)


def _f(ad, lisans, genislik):
    return {"dosya": f"/statik/foto/{ad}", "genislik": genislik,
            "yukseklik": 800, "atif": "", "kunye": "", "sorgu": "",
            "lisans": lisans, "kaynak": "commons"}


print("\nYayin havuzu -- tek gorsele dusmuyor")

# TEK atifsiz+net gorsel + dokuz iyi aday: havuz teke DUSMEMELI.
_k = _kayit([_f("a.jpg", "cc0", 1600)]
            + [_f(f"b{i}.jpg", "cc-by", 1600) for i in range(9)])
_h = _k.havuz_yayin("K")
dogru(f"havuz bire dusmuyor ({len(_h)} gorsel)", len(_h) >= foto.Kayit.ASGARI_HAVUZ)
dogru("tercih edilen gorsel havuzda kaliyor",
      any(f.dosya.endswith("a.jpg") for f in _h))

# Iyi katman ZATEN genisse alt katmana INILMEMELI.
_k2 = _kayit([_f(f"n{i}.jpg", "cc0", 1600) for i in range(6)]
             + [_f("dusuk.jpg", "cc-by", 400)])
_h2 = _k2.havuz_yayin("K")
dogru("iyi katman yeterliyse alt katmana inilmiyor",
      all(not f.dosya.endswith("dusuk.jpg") for f in _h2))
es("iyi katman oldugu gibi geliyor", len(_h2), 6)

# Havuz gercekten kucukse oldugu gibi donuyor -- uydurma yok.
_k3 = _kayit([_f("tek.jpg", "cc0", 1600)])
es("gercekten tek gorselli havuz teke dusuyor", len(_k3.havuz_yayin("K")), 1)

# Ayni gorsel iki kez EKLENMIYOR: katmanlar cakisiyor.
_k4 = _kayit([_f("x.jpg", "cc0", 1600), _f("y.jpg", "cc0", 900)])
_h4 = _k4.havuz_yayin("K")
es("katmanlar cakissa da tekrar yok", len(_h4), len({f.dosya for f in _h4}))

# ------------------------------------------------------------------
# KAYNAK ZATEN KUCUKSE 800 PIKSELLIK ES URETILMEZ.
#
# Olculdu (2026-08-28): 800 piksellik boy eklendikten sonra uretilen
# 26 dosyanin 11'i (%42) KOK DOSYAYLA BIREBIR AYNI boyuttaydi --
#
#     bankacilik-7.jpg  960px  195 KB -> 195 KB
#     borsa-8.jpg       960px  105 KB -> 105 KB
#     duzenleme-5.jpg   960px  179 KB -> 179 KB
#
# Commons olcekleme ucu yalnizca KUCULTUYOR; kaynak istenen genislige
# yakinsa ayni dosyayi veriyor. Sonuc: depoda iki kopya, okur icin
# sifir kazanc.
#
# Havuzun 209 gorseli 1000 pikselin altinda. 960 piksellik bir
# kaynagi 800 piksellik yuvaya basmak zaten 1,2x -- kabul edilebilir.
#
# `k/` (96px) ve `o/` (400px) bu esikten ETKILENMIYOR: her kaynaktan
# cok kucukler, orada kopya sorunu yok.
# ------------------------------------------------------------------
print("\nBoy uretimi -- kucuk kaynak elenir")

import tempfile as _tmp2  # noqa: E402

# KARAR DOGRUDAN SINANIYOR. Once `boy_uret` uzerinden sinanmisti ve
# HICBIR SEY OLCMUYORDU: sahte kayitta gecerli bir Commons adresi
# olmadigi icin esik kaldirilsa da sonuc ayni cikiyordu. Bozarak
# dogrulama bunu ortaya cikardi.
dogru("960px kaynak icin 800px es URETILMEZ",
      not foto._boy_gerekli({"genislik": 960}, 1000))
dogru("1920px kaynak icin URETILIR",
      foto._boy_gerekli({"genislik": 1920}, 1000))
dogru("tam esikteki kaynak icin URETILIR",
      foto._boy_gerekli({"genislik": 1000}, 1000))
dogru("genislik bilinmiyorsa uretilmez (bilinmezlikte kopya uretme)",
      not foto._boy_gerekli({}, 1000))
# Esik 0: eleme YOK. `k/` ve `o/` bu yoldan geciyor.
dogru("esik yoksa her kaynak icin uretilir",
      foto._boy_gerekli({"genislik": 100}, 0)
      and foto._boy_gerekli({}, 0))

# Esik VERILMEZSE eski davranis: eleme yok. `k/` ve `o/` bu yoldan
# geciyor ve etkilenmemeli.
dogru("esik verilmezse eleme yapilmiyor",
      foto.YAZI_EN_AZ_KAYNAK > 0)
def _govde(ad):
    """Bir islevin YALNIZCA kendi govdesi.

    Ilk yazimda dilim `def kucuk_uret` ile `def orta_uret` arasi
    alinmisti; arada `yazi_uret` durdugu icin onun `en_az_kaynak`
    parametresi kucuk boya aitmis gibi gorundu ve sinama yanlis
    kirmizi verdi. Islev sinirini bir sonraki `def` belirlemeli.
    """
    i = _KAYNAK.index("def " + ad)
    j = _KAYNAK.find(chr(10) + "def ", i + 4)
    return _KAYNAK[i:j if j != -1 else len(_KAYNAK)]


dogru("kucuk boy esiksiz uretiliyor",
      "en_az_kaynak" not in _govde("kucuk_uret"))
dogru("orta boy esiksiz uretiliyor",
      "en_az_kaynak" not in _govde("orta_uret"))
dogru("yazi boyu govdesinde esik var",
      "en_az_kaynak" in _govde("yazi_uret"))

# KARARIN KULLANILDIGI DA SINANIYOR. Islev tek basina dogru olabilir
# ama cagrilmazsa hicbir sey yapmaz -- bozarak dogrulamada tam bu
# kacti: `_boy_gerekli` dogru calisiyordu, cagri satiri silininde
# butun sinamalar yesil kaldi.
dogru("boy uretimi karari SORUYOR",
      "_boy_gerekli(f, en_az_kaynak)" in _govde("boy_uret"))
dogru("yazi boyu esikle uretiliyor",
      "en_az_kaynak=YAZI_EN_AZ_KAYNAK" in _KAYNAK)

# ------------------------------------------------------------------ sonuc
print("\nBoy turevi kok gorsele indirgeniyor")
# --------------------------------------------------------------------
# `/statik/foto/y/ad.jpg` ile `/statik/foto/ad.jpg` AYNI gorseldir.
# Gorseli SAYAN her kod bu esitligi bilmek zorunda.
#
# Olculdu (2026-08-28): `denetim.py` bilmiyordu. 800 piksellik es
# eklendikten sonra 29 gorsel yalnizca `y/` yoluyla basiliyordu ve
# denetim onlari "0 kez kullanildi" sayip UC havuzda yanlis
# dengesizlik alarmi uretti. Gercek dagilim neredeyse kusursuzdu:
# Borsa'da 15,15,15,14,14,0 gorunuyordu, dogrusu 15,15,15,14,14,14.
# --------------------------------------------------------------------
es("y/ (yazi boyu) koke iner",
   foto.asil_foto("/statik/foto/y/ad.jpg"), "/statik/foto/ad.jpg")
es("o/ (kart boyu) koke iner",
   foto.asil_foto("/statik/foto/o/ad.jpg"), "/statik/foto/ad.jpg")
es("k/ (kucuk boy) koke iner",
   foto.asil_foto("/statik/foto/k/ad.jpg"), "/statik/foto/ad.jpg")
es("kok yol degismeden gecer",
   foto.asil_foto("/statik/foto/ad.jpg"), "/statik/foto/ad.jpg")

# `uretilen/` BOY DEGIL AYRI HAVUZ: kavram gorselleri orada duruyor ve
# kok karsiligi YOK. Kor bicimde "ilk klasoru at" diyen bir cozum
# onlari da indirger ve var olmayan bir yola sayardi.
es("uretilen/ AYRI HAVUZ -- indirgenmez",
   foto.asil_foto("/statik/foto/uretilen/kavram-1.jpg"),
   "/statik/foto/uretilen/kavram-1.jpg")
es("foto disi yol degismez",
   foto.asil_foto("/statik/amblem/x.svg"), "/statik/amblem/x.svg")
es("bos yol cokmez", foto.asil_foto(""), "")

# LISTE TURETILIYOR, ELLE YAZILMIYOR. Elle yazilan bir kopya, yeni bir
# boy eklendiginde ayni hatanin ikinci kez olmasi demekti.
dogru("boy klasorleri sabitlerden turetiliyor",
      set(foto.BOY_KLASORLERI) == {foto.KUCUK_KLASOR.name,
                                   foto.ORTA_KLASOR.name,
                                   foto.YAZI_KLASOR.name})

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
