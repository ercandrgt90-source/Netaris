"""foto.py testleri -- AGA CIKMAZ.

Buradaki hatalarin ortak ozelligi SESSIZ olmalari: yanlis gorsel de,
atifsiz gorsel de sayfada duzgun gorunur. Ucu de gercekten yasandi.
"""

import sys
import pathlib

_BU = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BU))

import foto  # noqa: E402

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

# ------------------------------------------------------------------ sonuc
print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
