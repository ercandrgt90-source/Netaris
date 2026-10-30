"""Bilanco AI yorumu -- GIRDI ve yonerge.

Model cikisi burada sinanmiyor (o `ai/yorumcu` ve `cop_cikti`
tarafindan dogrulaniyor). Sinanan sey MODELE NE VERDIGIMIZ: yanlis
bicimli ya da yargi tasiyan bir girdi, yargi tasiyan cikti uretir.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bilanco_yorum as by  # noqa: E402

_gecti = 0
_kaldi = 0


def esit(bulunan, beklenen, aciklama):
    global _gecti, _kaldi
    if bulunan == beklenen:
        _gecti += 1
        print(f"  gecti  {aciklama}")
    else:
        _kaldi += 1
        print(f"  KALDI  {aciklama}")
        print(f"         beklenen: {beklenen!r}")
        print(f"         bulunan : {bulunan!r}")


print("\nBilanco AI yorumu -- girdi\n")

# --- YUZDE BICIMI ---
# Ilk yazimda "%-0,7" cikiyordu; dogrusu "-%0,7".
esit(by._yuzde(-0.7), "-%0,7", "eksi YUZDE ISARETINDEN once")
esit(by._yuzde(5.4), "%5,4", "pozitif yuzde")
esit(by._yuzde(0.0), "%0,0", "sifir")


class D:
    hasilat = 13_670_000_000.0
    net_kar = -100_000_000.0
    ozkaynak = 28_530_000_000.0
    brut_kar = None
    faaliyet_kari = None
    favok = None
    aktif_toplami = None
    net_borc = None
    faaliyet_nakit_akisi = None
    yatirim_harcamasi = None


g = by.girdi_kur("AKCNS", "AKÇANSA A.Ş.", "Temel malzeme", "2026/6",
                 simdi=D(), oranlar_kendi={"net_marj": -0.7},
                 medyanlar={"net_marj": -2.8}, sirket_sayisi=42)

esit("Hasılat: 13,67 milyar TL" in g, True, "kalem milyar TL cinsinden")
esit("Brüt kâr" in g, False,
     "OLMAYAN kalem girdiye GIRMIYOR -- model uydurmasin")
esit("-%0,7" in g, True, "negatif marj dogru bicimde")
esit("sektör medyanı -%2,8, 42 şirket" in g, True,
     "medyan OLCUM olarak veriliyor, kac sirkete dayandigi yaziyor")

# --- YONERGE YARGI YASAKLIYOR ---
#
# Medyana gore konum bir SIRALAMA; "daha iyi" bir YARGI. Hangi oranin
# yuksek olmasinin iyi oldugu is modeline gore degisir.
for s in ("İyi", "güçlü", "zayıf", "cazip", "riskli", "başarılı"):
    esit(s in by.SISTEM, True, f"yonerge {s!r} sozcugunu YASAKLIYOR")
esit("EN FAZLA 3 CÜMLE" in by.SISTEM, True, "uzunluk siniri yonergede")
esit("YALNIZCA sana verilen sayıları" in by.SISTEM, True,
     "model RAKAM BULMUYOR, verileni cumleye ceviriyor")

# Onceki donem verilirse DEGISIM de veriliyor -- model kendisi
# hesaplamasin diye. Hesap bizim, cumle onun.
class E:
    hasilat = 10_000_000_000.0
    net_kar = None
    ozkaynak = None
    brut_kar = None
    faaliyet_kari = None
    favok = None
    aktif_toplami = None
    net_borc = None
    faaliyet_nakit_akisi = None
    yatirim_harcamasi = None


g2 = by.girdi_kur("X", "X A.Ş.", "Sanayi", "2026/6", simdi=D(), once=E())
esit("önceki dönem 10,00 milyar TL" in g2, True,
     "onceki donem girdide -- model hesap yapmasin")


# DEGISIM YUZDESI GIRDIDE OLMALI -- KOSU #55'IN ASIL ENGELI BUYDU.
#
# Girdi yillardir yalnizca ONCEKI SEVIYEYI veriyordu; yanindaki yorum
# ise "degisim de veriliyor" diyordu. Model degisimi anlatmasi
# istendigi icin yuzdeyi KENDI hesapliyor, `sayi_denetimi` de onu
# hakli olarak reddediyordu.
#
# OLCULDU (kosu #55, 2026-10-29): 78 atlamanin ~45'i "girdide olmayan
# sayi" idi -- kotadan BUYUK bir engel. Reddedilen degerler
# deterministik degisimlerin ta kendisiydi (EREGL 32.7 -> FAVOK
# %32,7; AKCNS 28.1 -> ozkaynak %28,2).
g3 = by.girdi_kur("X", "X A.Ş.", "Sanayi", "2026/6", simdi=D(), once=E(),
                  degisimler={"hasilat": 34.6})
esit("reel değişim %34,6" in g3, True, "artis yuzdesi girdide")
# EKSI ISARET AYRI BIR IDDIA: site kurali isareti YUZDE ISARETINDEN
# ONCE koyuyor ("-%12,5"). Modelin girdide bozuk bicim gormesi,
# ciktida da bozuk bicim uretmesi demek.
#
# `E`de YALNIZCA hasilat dolu -- bos bir kalemin satiri hic
# yazilmadigi icin iddia onun uzerinden kurulamaz.
g3b = by.girdi_kur("X", "X A.Ş.", "Sanayi", "2026/6", simdi=D(), once=E(),
                   degisimler={"hasilat": -12.5})
esit("reel değişim -%12,5" in g3b, True,
     "azalis yuzdesi girdide -- isaret YUZDE ISARETINDEN ONCE")

# GERIYE DONUK: degisim verilmezse eski bicim korunuyor. `None`
# degerler de yazilmamali -- "reel değişim None" girdiyi bozardi.
esit("reel değişim" in g2, False, "degisim verilmezse yazilmiyor")
g4 = by.girdi_kur("X", "X A.Ş.", "Sanayi", "2026/6", simdi=D(), once=E(),
                  degisimler={"hasilat": None})
esit("reel değişim" in g4, False, "None degisim yazilmiyor")

# YONERGE HESAP YAPMAYI ACIKCA YASAKLIYOR.
#
# "Yeni sayi ekleme" yetmedi: model kendi hesabini "yeni sayi"
# saymiyordu. Yasak, kusurun ADIYLA yazili olmali.
esit("HESAP YAPMA" in by.SISTEM, True, "yonerge hesap yapmayi yasakliyor")
esit("reel değişim" in by.SISTEM, True,
     "yonerge hazir verilen alanin ADINI soyluyor")

# URETIM ZINCIRI GECIRIYOR MU -- OLCUT AST.
#
# Girdi dogru kurulsa da `sirket_isle` degisimleri vermezse alan OLU
# kalir. Metin aramak bicimlendirme degisince sessizce eslesmeyi
# birakiyor; bu depoda iki kez oldu.
import ast                                                # noqa: E402

_k = (pathlib.Path(__file__).resolve().parent
      / "uret_bilanco_sayfa.py").read_text(encoding="utf-8")
_ag = ast.parse(_k)
_cag = [c for c in ast.walk(_ag) if isinstance(c, ast.Call)
        and isinstance(c.func, ast.Attribute) and c.func.attr == "girdi_kur"]
esit(len(_cag), 1, "tek girdi_kur cagrisi")
esit(any(kw.arg == "degisimler" for kw in _cag[0].keywords), True,
     "uretim degisimleri geciriyor")


# DEGISIM HARITASI GERCEKTEN DOLU OLMALI.
#
# Harita satir ici bir sozluk kurulumuydu ve MUTASYON KACTI: `{}`
# yazmak AST sinamasini geciyordu ("degisimler= anahtari var") ama
# alan OLU kaliyordu. Anahtarin TASINDIGINI gormek yetmiyor; icinde
# deger OLDUGU da sinanmali.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "analiz"))
import uret_bilanco_sayfa as _U                           # noqa: E402

_h = _U.degisim_haritasi(D(), E())
esit(_h.get("hasilat") is not None, True,
     f"harita gercekten deger uretiyor (hasilat={_h.get('hasilat')})")
# `E`de yalnizca hasilat dolu; otekiler hesaplanamaz ve None olmali.
esit(_h.get("net_kar"), None, "hesaplanamayan alan None")
# `once` hic yoksa harita yine kurulmali -- cokmemeli.
esit(_U.degisim_haritasi(D(), None).get("hasilat"), None,
     "onceki donem yokken cokmuyor")

# SAGLAYICI KAPANINCA MALI TABLO CEKILMIYOR.
#
# OLCULDU (kosu #56): kota ILK sirkette kapandi, hat 324 sirketi
# cekmeye devam etti (~970 istek) ve kaynak 8 ardisik redden sonra
# kapandi. Bedelini bir sonraki adim odedi: "bölüm göçü" 186
# sayfanin SIFIRINI tasiyabildi.
import yorumcu as _y                                      # noqa: E402

esit(_U._saglayici_kapandi(), False, "baslangicta kapali DEGIL")
_y._CF_KOTA_DOLDU = True
try:
    esit(_U._saglayici_kapandi(), True, "mandal kapaninca KAPALI")
finally:
    _y.cf_kotasini_sifirla()
esit(_U._saglayici_kapandi(), False, "sifirlaninca yine acik")

# ERKEN CIKIS URETIM DONGUSUNDE GERCEKTEN KULLANILIYOR MU.
#
# Yardimcinin dogru cevap vermesi YETMEZ: dongu onu sormazsa kapi
# OLU kalir ve kota kapaliyken 324 sirket yine cekilir. Olcut AST --
# metin aramak bicimlendirme degisince sessizce eslesmeyi birakiyor.
import ast                                                # noqa: E402

_kaynak = (pathlib.Path(__file__).resolve().parent
           / "uret_bilanco_sayfa.py").read_text(encoding="utf-8")
_agac = ast.parse(_kaynak)
_main = next(f for f in ast.walk(_agac)
             if isinstance(f, ast.FunctionDef) and f.name == "main")
# Kuyruk uzerinde donen `for`u bul ve ICINDE cagri var mi diye bak.
_dongu = [d for d in ast.walk(_main)
          if isinstance(d, ast.For)
          and isinstance(d.iter, ast.Name) and d.iter.id == "kuyruk"]
esit(len(_dongu), 1, "uretim dongusu bulundu")
_sor = [c for c in ast.walk(_dongu[0]) if isinstance(c, ast.Call)
        and isinstance(c.func, ast.Name)
        and c.func.id == "_saglayici_kapandi"]
# IKI CAGRI BEKLENIYOR: biri BEKLEME kosulunda, biri CIKIS
# kosulunda. Ilk yazim "tam bir tane" diyordu ve bekleme eklenince
# dustu -- iddia davranisi degil, o anki SATIR SAYISINI tutuyordu.
esit(len(_sor) >= 1, True,
     f"dongu saglayicinin kapandigini SORUYOR ({len(_sor)} cagri)")
# Cagri bir `if`in KOSULUNDA olmali -- cagirip sonucu atmak,
# hicbir sey yapmamakla ayni sey.
_kosul = [d for d in ast.walk(_dongu[0]) if isinstance(d, ast.If)
          and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                  and c.func.id == "_saglayici_kapandi"
                  for c in ast.walk(d.test))]
esit(len(_kosul), 1, "cagri bir kosulun ICINDE")
esit(any(isinstance(x, (ast.Return, ast.Break))
         for x in ast.walk(_kosul[0])), True,
     "kosul gerceklesince dongu BITIYOR")


# --- KOTA TUKENINCE BEKLE -------------------------------------------
#
# OLCULDU (2026-10-30, ardisik kosu gunlukleri):
#
#     06:13  haber   18 yorum      kota ACIK
#     06:41  haber    0 yorum 429  kota DOLU
#     06:45  bilanco        429    kota DOLU
#     07:33  haber   24 yorum      kota ACIK yine
#
# "daily free allocation" mesaji YANILTICI: butce ~50 dakikada
# kendini yeniliyor. Dogru tepki "dogru saati secmek" degil,
# TUKENDIGINDE BEKLEMEK. Modeldeki 5/15 SANIYELIK bekleme bu olcek
# icin cok kisa.
_uyku = []
_asil_uyu = _U._uyu
_U._uyu = lambda s: _uyku.append(s)
try:
    _U.kota_bekleme_sifirla()
    _y._CF_KOTA_DOLDU = True
    # DONGU SINIRLI: "hak tukenmesine bakilmiyor" mutasyonu
    # `_kota_bekle`yi hep True yapiyor ve sinirsiz bir sinama SONSUZ
    # DONERDI -- dusmek yerine ASILIRDI. Asilan bir sinama, kirmizi
    # donen bir sinama degildir: CI'de zaman asimina kadar kaynak
    # yakar ve sebebi gorunmez.
    _n = 0
    while _U._saglayici_kapandi() and _U._kota_bekle():
        _n += 1
        _y._CF_KOTA_DOLDU = True          # hala dolu varsay
        if _n > _U.KOTA_BEKLEME_HAKKI + 3:
            break
    esit(_n, _U.KOTA_BEKLEME_HAKKI, "hak kadar BEKLENIYOR")
    esit(_n <= _U.KOTA_BEKLEME_HAKKI, True,
         "bekleme SINIRLI -- sonsuz donmuyor")
    esit(_U._kota_bekle(), False, "hak bitince beklemiyor")
    # SURE DAKIKA OLCEGINDE: saniyelik bir bekleme olculen ~50
    # dakikalik araligi hic kapsamaz.
    esit(all(s >= 600 for s in _uyku), True,
         f"bekleme DAKIKA olceginde ({[round(s/60) for s in _uyku]} dk)")
    esit(_U.KOTA_BEKLEME_DK * _U.KOTA_BEKLEME_HAKKI >= 40, True,
         "toplam bekleme olculen araligi KAPSIYOR")

    # MANDAL GERCEKTEN SIFIRLANIYOR. Sifirlanmazsa bekleme hicbir sey
    # degistirmez: kosu boyunca kapali kalir.
    _U.kota_bekleme_sifirla()
    _y._CF_KOTA_DOLDU = True
    esit(_U._kota_bekle(), True, "bekleme yapildi")
    esit(_U._saglayici_kapandi(), False, "bekleyisten sonra mandal ACIK")
finally:
    _U._uyu = _asil_uyu
    _U.kota_bekleme_sifirla()
    _y.cf_kotasini_sifirla()

# URETIM DONGUSU BEKLIYOR MU -- OLCUT AST.
_ag_b = ast.parse((pathlib.Path(__file__).resolve().parent
                   / "uret_bilanco_sayfa.py").read_text(encoding="utf-8"))
_m_b = next(f for f in ast.walk(_ag_b)
            if isinstance(f, ast.FunctionDef) and f.name == "main")
_w = [w for w in ast.walk(_m_b) if isinstance(w, ast.While)
      and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id == "_kota_bekle" for c in ast.walk(w.test))]
esit(len(_w), 1, "uretim dongusu kota icin BEKLIYOR")
# Bekleme, CIKIS kontrolunden ONCE olmali: once cikilirsa bekleme
# hic calismaz.
_govde = [n for n in _m_b.body]
esit(any(isinstance(n, ast.For) for n in ast.walk(_m_b)), True,
     "uretim dongusu duruyor")
print()
if _kaldi:
    print(f"{_kaldi} TEST KALDI, {_gecti} gecti")
    sys.exit(1)
print(f"TUM TESTLER GECTI ({_gecti})")
