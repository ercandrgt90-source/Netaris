"""denetim.py siniflandirma ve yayin karari testleri -- AGA CIKMAZ.

Yayin karari dagitimi durduran seydir (`calistir.py` hata gorunce
yayimlamiyor). Bu yuzden esiklerinin sessizce kaymasi, bozuk icerigin
yayimlanmasi demek.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import denetim  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


def B(alan, agirlik="uyari"):
    return denetim.Bulgu(agirlik, alan, "kod", "mesaj")


# ------------------------------------------------------------------
# SINIFLANDIRMA -- promptun 15. maddesi.
# ------------------------------------------------------------------
print("Siniflandirma -- alan simgeye cevriliyor")
es("etiket hatasi kritik", denetim.sinif(B("etiket", "hata")), "🔴")
es("gorsel uyarisi", denetim.sinif(B("gorsel")), "🟣")
es("ai uyarisi", denetim.sinif(B("ai")), "🟠")
es("editoryal uyari", denetim.sinif(B("editoryal")), "🔵")
es("tekrar uyarisi", denetim.sinif(B("tekrar")), "⚪")
es("veri uyarisi", denetim.sinif(B("veri")), "🟡")

# AGIRLIK SINIFI YUKSELTIR. "Bayat veri" uyaridir ama "imkansiz deger"
# ayni alanda HATA agirligindadir ve kritik isaretlenmeli.
print("\nAgirlik sinifi yukseltiyor")
es("veri HATASI kritik olur", denetim.sinif(B("veri", "hata")), "🔴")
es("aralik HATASI kritik olur", denetim.sinif(B("aralik", "hata")), "🔴")
# Gorsel ve AI kendi simgesini KORUYOR: onlar zaten ayri sinif ve
# "kritik" demek hangi turden hata oldugunu kaybettirirdi.
es("gorsel HATASI simgesini korur", denetim.sinif(B("gorsel", "hata")), "🟣")

print("\nBilinmeyen alan sessizce dusmuyor")
es("bilinmeyen alan editoryal sayilir", denetim.sinif(B("yeni_alan")), "🔵")

# ------------------------------------------------------------------
# YAYIN KARARI -- promptun 19. maddesi, uc seviye.
# ------------------------------------------------------------------
print("\nYayin karari uc seviye")
es("bulgu yoksa hazir", denetim.yayin_karari([], [])[0], "🟢")
es("yalniz uyari varsa sarti", denetim.yayin_karari([], [B("gorsel")])[0], "🟡")
es("hata varsa uygun degil",
   denetim.yayin_karari([B("etiket", "hata")], [])[0], "🔴")
es("hata uyariyi bastirir",
   denetim.yayin_karari([B("etiket", "hata")], [B("gorsel")])[0], "🔴")
es("karar metni", denetim.yayin_karari([], [])[1], "YAYINA HAZIR")

# ------------------------------------------------------------------
# HER SINIF ALANI RAPORDA BIR BOLUME DUSMELI. Bir alan hicbir bolume
# dusmezse bulgu uretilir ama raporun ust ozetinde GORUNMEZ.
# ------------------------------------------------------------------
print("\nHer alan raporda bir bolume dusuyor")
rapor_alanlari = {k for _ad, kodlar, _i, _k in denetim.RAPOR_ALANLARI
                  for k in kodlar}
for alan in denetim.SINIFLAR:
    es(f"'{alan}' raporda", alan in rapor_alanlari, True)

# ------------------------------------------------------------------
# LISANS DENETIMI -- CC BY atfi hukuki yukumluluk, bu yuzden HATA.
#
# Olculdu: haber sayfalarinda 417/417 gorsel kunyeliydi ama LISTE
# sayfalarindaki 48 kart gorseli kunyesizdi ve hicbir yerde gorunmuyordu.
# ------------------------------------------------------------------
print("\nLisans denetimi -- atifsiz gorsel HATA")
import tempfile  # noqa: E402

_ASIL = denetim.CIKTI_DIZINI
with tempfile.TemporaryDirectory() as gecici:
    kok = pathlib.Path(gecici)
    denetim.CIKTI_DIZINI = kok

    def sayfa(ad, govde):
        d = kok / ad
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(govde, encoding="utf-8")

    KART = '<img src="/statik/foto/borsa-1.jpg">'
    sayfa("atifsiz", f"<main>{KART}</main>")
    es("kunyesiz kart yakalanir",
       [(b.agirlik, b.alan) for b in denetim._lisans_denetimi()],
       [("hata", "gorsel")])

    sayfa("atifsiz", f'<main>{KART}<p class="foto-kunye-toplu">Görseller: X</p></main>')
    es("toplu kunye yeterli", denetim._lisans_denetimi(), [])

    sayfa("atifsiz",
          f"<main><figure>{KART}<figcaption>Foto: X</figcaption></figure></main>")
    es("figcaption yeterli", denetim._lisans_denetimi(), [])

    # Kucuk (akis) surumler sayilmiyor: 40 piksellik gorsel ve ayni
    # sayfada buyugu kunyeli basiliyor.
    sayfa("atifsiz", '<main><img src="/statik/foto/k/borsa-1.jpg"></main>')
    es("kucuk surum kunye istemez", denetim._lisans_denetimi(), [])

    sayfa("atifsiz", "<main>gorselsiz sayfa</main>")
    es("gorselsiz sayfa", denetim._lisans_denetimi(), [])
denetim.CIKTI_DIZINI = _ASIL

# --------------------------------------------------------------------
# SERIT CAKISMASI
# --------------------------------------------------------------------
#
# Ayni enstrumanin seride hem sunucudan hem `canli.js`ten girmesi.
# Gercekte olustu: sunucuya TCMB kurlari eklendikten sonra USD/TRY
# seritte iki kez, iki farkli degerle gorundu.
_ASIL_BETIK = denetim.CANLI_BETIK

with tempfile.TemporaryDirectory() as gecici:
    kok = pathlib.Path(gecici)
    denetim.CIKTI_DIZINI = kok / "cikti"
    denetim.CIKTI_DIZINI.mkdir()
    denetim.CANLI_BETIK = kok / "canli.js"

    def kur(sunucu_adlari, js_metni):
        (denetim.CIKTI_DIZINI / "index.html").write_text(
            "".join(f'<span class="kalem" title="{a} &mdash; son veri 2026-08-11">'
                    f"</span>" for a in sunucu_adlari).replace("&mdash;", "—"),
            encoding="utf-8")
        denetim.CANLI_BETIK.write_text(js_metni, encoding="utf-8")

    # Adlarin UC yazim bicimi de taranmali. Ilk surumum yalnizca
    # dogrudan `kalemKur(` cagrilarina bakiyordu ve alti addan birini
    # buluyordu -- eksik tarama, sahte "temiz" rapor uretir.
    es("uc bicim de taranir",
       sorted(denetim._serit_adlari_js(
           'kalemKur("A", "USDT/TRY", x);'
           ' ekle("B", "USD/TRY", f);'
           ' var t = [{ iz: "XBT", ad: "BTC/USD" }];')),
       ["BTC/USD", "USD/TRY", "USDT/TRY"])

    kur(["USD/TRY", "BRENT"], 'kalemKur("K", "BTC/USD", x);')
    es("cakisma yoksa temiz", denetim._serit_cakismasi_denetimi(), [])

    kur(["USD/TRY", "BRENT"], 'ekle("USDTRY_ECB", "USD/TRY", f);')
    _b = denetim._serit_cakismasi_denetimi()
    es("cakisma HATA verir", [(x.agirlik, x.alan) for x in _b], [("hata", "veri")])
    es("mesaj enstrumani soyler", "USD/TRY" in _b[0].mesaj, True)

    # Betik duruyor ama ad okunamiyorsa sessiz gecilmez: bicim
    # degismis olabilir ve denetim ise yaramaz hale gelir.
    kur(["USD/TRY"], "// kalem eklemeyen betik")
    es("ad okunamazsa uyarir",
       [x.agirlik for x in denetim._serit_cakismasi_denetimi()], ["uyari"])

denetim.CIKTI_DIZINI = _ASIL
denetim.CANLI_BETIK = _ASIL_BETIK

print()
for k in kaldi:
    print("  KALDI", k)
print(f"{gecti} gecti, {len(kaldi)} kaldi")
sys.exit(1 if kaldi else 0)
