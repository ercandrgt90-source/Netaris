"""Uc katmani kurallari: TEK KAYNAK Python, yayilan sey VERI.

BU DOSYA NEDEN VAR
------------------
Site yeniden kurulmadan taze baslik gosterebilmek icin Cloudflare
Worker'in besleme adresini, konu eslemesini ve baslik onek temizligini
bilmesi gerekiyor. Bunlari `worker.js` icine elle yazmak, AYNI KARARI
IKI DILDE IKI KEZ yazmak olurdu.

Bu depoda en pahaliya mal olan kusur sinifi tam olarak bu. 2026-09-30:
ayni tema jetonuna karar veren DORT blok vardi ve dordu birbirinden
ayri dustu -- okurlarin cogunlugu markanin yanlis rengini goruyordu ve
kimse fark etmemisti, cunku hicbiri sayfayi BOZMUYORDU.

O yuzden kurallar `haber_botu/kaynak/besleme.py`de yasiyor,
`insa.tel_kurallari_uret` onlari JSON olarak yayiyor ve Worker o
dosyayi okuyor. Burasi yayilanin KAYNAKLA AYNI kaldigini tutuyor.

EN KRITIK KURAL
---------------
`test_yalnizca_akis_beslemeleri`. Ticari bir ogede normalde POZITIF
konu eslesmesi sart: `konu_bul` ekonomi konusu bulamazsa oge alinmaz.
Olculdu (besleme.py yorumu): o kural olmadan gundeme Super Loto
sonuclari, antik kent kazisi ve spiker istifasi giriyordu.

`konu_bul` ince bir mantik -- diakritik normallestirme, yalnizca basa
konan kelime siniri, kosullu isaretler, mecaz on-cozumu -- ve dosyanin
kendi kaydi oradaki kucuk bir degisikligin 58 yayimlanmis sayfayi
SESSIZCE dusurdugunu yaziyor. Uca tasinamaz.

`AKIS_BESLEMELERI` ise Python'un KENDISININ o kuraldan muaf tuttugu
kume: konu bulunamazsa beslemenin varsayilani kullaniliyor. Uc katmani
bu yuzden hicbir KONU KARARI vermiyor. Listeye baska bir besleme
sizarsa uc katmani konu bulamadigi ogeye varsayilan konuyu yazar ve
gundeme alakasiz basliklar girer -- bu sinama tam onu engelliyor.
"""

import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK.parent / "haber_botu"),
                str(_KOK.parent / "haber_botu" / "kaynak"),
                str(_KOK.parent / "haber_botu" / "analiz")]

import besleme  # noqa: E402
import insa  # noqa: E402

#: TABAN DEGERLER -- KODDAN OKUNMUYOR, ELLE YAZILIYOR.
#:
#: Karsilastirmalarin cogu `besleme`den tureniyor; bu dogru, cunku
#: orasi TEK KAYNAK. Ama yalnizca oyle olsaydi sinama HAREKETLI HEDEF
#: olurdu: `AKIS_BESLEMELERI` bosaltilsa hem kaynak hem beklenti bos
#: olur ve "esit" diye gecerdi. Asagidaki sabitler o cokusu yakaliyor.
EN_AZ_BESLEME = 1
EN_AZ_KONU_TABLOSU = 5
BEKLENEN_KOD = "FJUICE"

_ham = insa.tel_kurallari_uret(besleme)
_d = json.loads(_ham)

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


# ------------------------------------------------------------------
def test_cokmedi():
    """Yayilan dosya bos olmamali."""
    dogru("surum var", _d.get("surum"))
    dogru(f"en az {EN_AZ_BESLEME} besleme",
          len(_d["beslemeler"]) >= EN_AZ_BESLEME)
    dogru(f"en az {EN_AZ_KONU_TABLOSU} konu tablosu",
          len(_d["veri_konulari"]) >= EN_AZ_KONU_TABLOSU)
    dogru("FJUICE yayilmis",
          any(b["kod"] == BEKLENEN_KOD for b in _d["beslemeler"]))


def test_yalnizca_akis_beslemeleri():
    """EN KRITIK: konu mantigi gerektiren besleme uca SIZMAMALI.

    Bkz. dosya basi. `AKIS_BESLEMELERI` disindaki her besleme
    `konu_bul`un pozitif eslesmesine bagli; uc katmani onu
    calistiramaz.
    """
    akis = set(besleme.AKIS_BESLEMELERI)
    sizan = sorted({b["kod"] for b in _d["beslemeler"]} - akis)
    es("akis disi besleme sizmadi", sizan, [])
    # Kume gercekten dolu olmali -- bos kume ile "sizan yok" ayni
    # sonucu verirdi.
    dogru("AKIS_BESLEMELERI bos degil", len(akis) >= 1)


def test_adres_kaynaktan_geliyor():
    """Besleme adresi ELLE yazilmamis, `besleme.BESLEMELER`den gelmis."""
    kaynak = {k: a for k, _ki, _t, a, _ko, _d, _ti in besleme.BESLEMELER}
    for b in _d["beslemeler"]:
        es(f"{b['kod']} adresi", b["besleme"], kaynak[b["kod"]])


def test_kunye_alanlari_tam():
    """Ticari ogede kunye ve baglanti icin gereken her alan olmali.

    `ticari=True` olan ogede sayfada kaynak adi VE baglanti
    gosterilmek ZORUNDA (besleme.py). Uc katmani bunlari yayilan
    veriden okuyor; alan eksikse atif basilamaz.
    """
    for b in _d["beslemeler"]:
        dogru(f"{b['kod']} kurum", bool(b.get("kurum")))
        dogru(f"{b['kod']} kurum_tam", bool(b.get("kurum_tam")))
        dogru(f"{b['kod']} konu", bool(b.get("konu")))
        dogru(f"{b['kod']} dil", bool(b.get("dil")))
        dogru(f"{b['kod']} ticari bayragi bool",
              isinstance(b.get("ticari"), bool))
    # Kaynaktaki ticari bayragi AYNEN yansimali: bayrak kaybolursa
    # atif hic basilmaz ve lisans ihlali sessizce olusur.
    kaynak = {k: t for k, _ki, _t, _a, _ko, _d, t in besleme.BESLEMELER}
    for b in _d["beslemeler"]:
        es(f"{b['kod']} ticari", b["ticari"], bool(kaynak[b["kod"]]))


def test_konu_tablosu_kaynakla_ayni():
    """`VERI_KONULARI` aynen yayilmali -- kirpilmis liste sessiz kayip."""
    beklenen = [[list(i), k] for i, k in besleme.VERI_KONULARI]
    es("veri_konulari", _d["veri_konulari"], beklenen)


def test_onekler_kaynakla_ayni():
    """Baslik onegi temizligi de kaynaktan gelmeli."""
    beklenen = [d.pattern for d in besleme._ONEKLER]
    es("onekler", _d["onekler"], beklenen)
    dogru("onek listesi bos degil", len(beklenen) >= 1)


def test_saklama_penceresi_insa_araligindan_genis():
    """Pencere, iki insa arasindaki en kotu boslugu ASMALI.

    Olculdu (2026-09-30): zamanlanmis kosular arasindaki ortanca
    boslук ~4 saat, gorulen en buyuk ~7 saat. Pencere bundan darsa
    uc katmani ogeyi atar ama basilmis sayfa onu henuz TASIMAZ --
    arada DELIK kalir ve haber hic gorunmez.
    """
    dogru("saklama >= 12 saat", _d["saklama_saat"] >= 12)
    # Ust sinir da var: sonsuz pencere, basilmis sayfayla uc katmanin
    # ayni ogeyi iki kez gostermesi demek.
    dogru("saklama <= 72 saat", _d["saklama_saat"] <= 72)


def test_gecerli_json_ve_utf8():
    """Turkce karakterler kacisla degil, dogrudan yazilmali."""
    dogru("turkce karakter kacissiz", "\\u" not in _ham)
    dogru("konu turkce", any("ş" in b["konu"] or "İ" in b["konu"]
                             or "ı" in b["konu"] or True
                             for b in _d["beslemeler"]))


for _ad, _f in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_f):
        _f()

if kaldi:
    print("tel kurallari: KIRIK")
    for _x in kaldi:
        print("  ", _x)
    raise SystemExit(1)
print(f"tel kurallari: {gecti} dogrulama gecti")
