# -*- coding: utf-8 -*-
"""Yerel nobetcinin KARARI -- aga cikmaz, tetiklemez.

BU DOSYA NEDEN VAR
------------------
Yerel nobetci yanlis davranirsa iki sonucu da PAHALI ve ikisi de
SESSIZ:

  * Fazla tetiklerse: her on dakikada gereksiz bir kosu baslatir.
    Depo herkese acik, dakika sinirsiz -- ama taze icerigi yeniden
    uretmek bos is ve kaynaklara saygisizlik.
  * Az tetiklerse: hicbir sey olmaz ve tempo yine ~7 kosu/gunde
    kalir. Yani mekanizma VARMIS gibi gorunur ama yoktur. Bu
    depoda tam o bicimde bir ariza 13 gun surdu.

"BILINMIYOR" AYRI BIR DURUM: uca ulasilamamasi ariza DEGIL. Olcum
aracinin kendisi bu depoda defalarca yanlis alarm uretti;
ulasilamayan bir ucu "bayat" sayip her on dakikada kosu baslatmak,
gercek arizayi da inandiriciliktan dusururdu.

ESIK BURADA YAZILI DEGIL: veriden geliyor. Esigi sinamaya kopyalamak
HAREKETLI HEDEF olurdu -- Worker'daki deger degisince sinama da
degisir ve ayrisma hic gorulmezdi.
"""

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import yerel_nobetci as yn  # noqa: E402

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


def _kod(kaynak: str) -> str:
    """Yorum satirlarini ayiklar.

    NEDEN: bu dosyadaki kaynak denetimleri bir ifadenin KODDA gecip
    gecmedigini soruyor. Yorumlar ayiklanmazsa dosyanin kendi
    aciklamasi -- ki bu depoda aciklamalar uzun ve ornek kod
    tasiyor -- sinamayi yaniltir. Ilk yazimda tam bu oldu.
    """
    return "\n".join(x for x in kaynak.splitlines()
                     if not x.lstrip().startswith(("#", "#:")))


def _veri(yas, esik=0.6):
    return {"icerik_yasi_saat": yas, "esik_saat": esik,
            "jeton_kurulu": True}


# ------------------------------------------------------------------
def test_bayat_icerik_tetikler():
    k, s = yn.karar_ver(_veri(2.5), kosu_var=False)
    es("bayat -> tetikle", k, yn.KARAR_TETIKLE)
    dogru("sebep yasi yaziyor", "2.50" in s)


def test_taze_icerik_tetiklemez():
    k, _ = yn.karar_ver(_veri(0.2), kosu_var=False)
    es("taze -> tetiklemez", k, yn.KARAR_TAZE)


def test_esik_veriden_geliyor():
    """Esik KODDA yazili olmamali.

    Ayni yas, farkli esik -> farkli karar. Esik sabit yazilsaydi bu
    sinama gecemezdi ve Worker'daki degisiklik yerel nobetciye hic
    yansimazdi.
    """
    k1, _ = yn.karar_ver(_veri(1.0, esik=0.6), kosu_var=False)
    k2, _ = yn.karar_ver(_veri(1.0, esik=4.0), kosu_var=False)
    es("esik 0.6 -> tetikle", k1, yn.KARAR_TETIKLE)
    es("esik 4.0 -> taze", k2, yn.KARAR_TAZE)


def test_sinirda_tetikler():
    """Yas esige ESIT ise tetikler -- `<` degil `>=`.

    Esik "bu yastan sonra bayat" demek; esikte durup beklemek,
    esigi bir tur daha oteye atmak olurdu.
    """
    k, _ = yn.karar_ver(_veri(0.6, esik=0.6), kosu_var=False)
    es("yas == esik -> tetikle", k, yn.KARAR_TETIKLE)


def test_kosu_varsa_siraya_sokmaz():
    k, s = yn.karar_ver(_veri(3.0), kosu_var=True)
    es("kosu suruyor -> tetiklemez", k, yn.KARAR_KOSUYOR)
    dogru("sebep kosuyu soyluyor", "kosu" in s)


def test_ulasilamayan_uc_bilinmiyor():
    """ULASILAMADI != BAYAT. Bkz. dosya basi."""
    for veri in (None, {}, "metin", {"esik_saat": 0.6},
                 {"icerik_yasi_saat": None, "esik_saat": 0.6}):
        k, _ = yn.karar_ver(veri, kosu_var=False)
        es(f"{veri!r} -> bilinmiyor", k, yn.KARAR_BILINMIYOR)


def test_bozuk_degerler_bilinmiyor():
    """Sayiya cevrilemeyen deger tetik uretmemeli."""
    for veri in ({"icerik_yasi_saat": "cok", "esik_saat": 0.6},
                 {"icerik_yasi_saat": 2.0, "esik_saat": None},
                 {"icerik_yasi_saat": 2.0, "esik_saat": "x"}):
        k, _ = yn.karar_ver(veri, kosu_var=False)
        es(f"{veri} -> bilinmiyor", k, yn.KARAR_BILINMIYOR)


def test_bilinmiyor_kosu_varliginda_da_bilinmiyor():
    """Bilinmezlik, kosu durumundan BAGIMSIZ.

    Karar sirasi onemli: once "biliyor muyuz", sonra "kosuyor mu".
    Ters sirada bilinmeyen bir durum "kosuyor" diye raporlanir ve
    teshis yanlis yere bakar.
    """
    k, _ = yn.karar_ver(None, kosu_var=True)
    es("bilinmiyor + kosu -> bilinmiyor", k, yn.KARAR_BILINMIYOR)


def test_jeton_gunluge_yazilmiyor():
    """Kaynakta jetonu yazdiran bir satir OLMAMALI.

    Bu depoda bir PAT sohbete ve ekran goruntusune dustu; o yuzden
    kural yapisal tutuluyor.
    """
    kaynak = (_KOK / "yerel_nobetci.py").read_text(encoding="utf-8")
    for kotu in ("print(jeton", "print(f\"{jeton", "gunluge_yaz(jeton",
                 "{jeton}", "+ jeton)"):
        dogru(f"{kotu!r} gecmiyor", kotu not in kaynak)
    # Yetkilendirme basligi KURULUYOR ama yazdirilmiyor.
    dogru("yetkilendirme basligi var", "Bearer " in kaynak)


def test_kimlik_tanitiliyor():
    """Cloudflare varsayilan `Python-urllib` kimligini 403 ile
    reddediyor (bkz. memory: olcum-araci-tuzaklari, tuzak 5)."""
    dogru("kimlik Netaris diyor", "Netaris" in yn.KIMLIK)
    dogru("kimlik iletisim tasiyor", "netaris.net" in yn.KIMLIK)


def test_esik_kaynakta_sabit_yazili_degil():
    """Esik degeri koda GOMULMEMIS olmali.

    `karar_ver` esigi yalnizca veriden okuyor. Bir gun biri
    "varsayilan" diye sabit bir esik eklerse, Worker'daki degisiklik
    sessizce etkisiz kalir.
    """
    kaynak = (_KOK / "yerel_nobetci.py").read_text(encoding="utf-8")
    govde = kaynak.split("def karar_ver(")[1].split("\ndef ")[0]
    # Yorum satirlari haric gercek kod.
    kod = "\n".join(x for x in govde.splitlines()
                    if not x.strip().startswith("#"))
    for sayi in ("0.6", "1.5", "2.0", "4.0"):
        dogru(f"karar_ver icinde {sayi} sabiti yok", sayi not in kod)


def test_git_path_e_guvenmiyor():
    """`git` PATH'te yoksa bilinen kurulum yerlerinde aranmali.

    Olculdu (2026-10-01): Gorev Zamanlayici isi MINIMAL bir PATH ile
    baslatiyor ve `git` oraya dahil degil.
    `subprocess.run(["git", ...])` FileNotFoundError atiyordu ve
    betik GUNLUGE HICBIR SEY YAZMADAN cokuyordu.

    Ikinci sessizlik katmani daha kotuydu: `pythonw.exe` izlemeyi
    yutuyor VE cikis kodunu 0 raporluyor -- Gorev Zamanlayici
    "Last Result: 0" diyordu, yani tam tersini.
    """
    dogru("GIT_ADAYLARI dolu", len(yn.GIT_ADAYLARI) >= 2)
    dogru("adaylar tam yol", all(a.endswith("git.exe")
                                 for a in yn.GIT_ADAYLARI))
    # `git` cagrisi CIPLAK ad ile yapilmiyor -- bulunmus yol ile.
    #
    # YORUMLAR AYIKLANIYOR: ilk yazimda ayiklanmiyordu ve sinama
    # kirmizi yandi -- cunku dosyanin KENDI ACIKLAMASI
    # `subprocess.run(["git", ...])` ifadesini ornek olarak
    # tasiyor. Yani sinama yorumu kod sanmisti. Bu depoda ayni
    # tuzaga bugun ucuncu kez dusuldu.
    dogru('["git", ...] ciplak cagrisi yok',
          'subprocess.run(["git"' not in _kod(
              (_KOK / "yerel_nobetci.py").read_text(encoding="utf-8")))
    dogru("git_yolu kullaniliyor",
          "git_yolu()" in (_KOK / "yerel_nobetci.py").read_text(
              encoding="utf-8"))
    # Bu makinede gercekten bulunmali; bulunamazsa yerel nobetci
    # tetikleyemez ve bunu BILMEK gerekir.
    dogru("bu makinede git bulundu", bool(yn.git_yolu()))


def test_kimlik_alinamazsa_cokmuyor():
    """`git` yoksa istisna DEGIL, bos deger donmeli."""
    eski = yn.GIT_ADAYLARI
    try:
        yn.GIT_ADAYLARI = (r"Z:\olmayan\git.exe",)
        import shutil as _sh  # noqa: PLC0415

        eski_which = _sh.which
        _sh.which = lambda *a, **k: None
        try:
            es("git yoksa bos kimlik", yn.kimlik_al(), "")
        finally:
            _sh.which = eski_which
    finally:
        yn.GIT_ADAYLARI = eski


def test_kimlik_okuma_asilamaz():
    """Kimlik yardimcisi SORU SORMAMALI ve suresi KISA olmali.

    OLCULDU (2026-10-01 15:15): gorev baglaminda kimlik okunamadi
    ("makinede git kimligi yok") ve ardindan ~50 tur gunluge HIC
    satir yazmadi. Etkileşimli oturum yokken kimlik yardimcisi soru
    sormaya calisabiliyor; soru cevapsiz kalinca cagri suruncemede
    kaliyor ve gorev 5 dakikalik sinira takilip oldurulunce gunluge
    hicbir sey dusmuyor -- yani ariza KENDI IZINI DE siliyor.

    Bu gozlem tam olarak aciklanmis DEGIL (oturum kilidi en olasi
    sebep, kanitlanmadi); bu yuzden hem sormak kapatildi hem sure
    kisaltildi hem de tur suresi gunluge yazildi.
    """
    kod = _kod((_KOK / "yerel_nobetci.py").read_text(encoding="utf-8"))
    dogru("GIT_TERMINAL_PROMPT kapatiliyor",
          'GIT_TERMINAL_PROMPT"] = "0"' in kod)
    dogru("GCM_INTERACTIVE kapatiliyor",
          'GCM_INTERACTIVE"] = "never"' in kod)
    dogru("cevre degiskeni gecirilmis", "env=cevre" in kod)
    # Sure 5 dakikalik gorev sinirindan COK kisa olmali.
    import re as _re  # noqa: PLC0415

    m = _re.search(r"credential[\s\S]{0,300}?timeout=(\d+)", kod)
    dogru("kimlik cagrisinda sure siniri var", m)
    if m:
        dogru(f"sure siniri kisa ({m.group(1)}s <= 10)",
              int(m.group(1)) <= 10)


def test_tur_suresi_gunluge_yaziliyor():
    """Yavaslayan tur gorunur olmali.

    ~50 turun hic satir yazmamasinin sebebi disaridan
    gorulemiyordu. Sure, bir turun gorev sinirina yaklasmasini
    gunlukte okunabilir kiliyor.
    """
    kod = _kod((_KOK / "yerel_nobetci.py").read_text(encoding="utf-8"))
    dogru("baslangic olculuyor", "time.monotonic()" in kod)
    dogru("sure satira yaziliyor", "{sure:.1f}s" in kod)


def test_coku_gunluge_yaziliyor():
    """Tani aracinin en kor oldugu yer kendi arizasi.

    Kaynakta `main()` cagrisi bir yakalayicinin ICINDE olmali ve
    coku gunluge dusmeli; yoksa her tur sessizce coker.
    """
    kaynak = (_KOK / "yerel_nobetci.py").read_text(encoding="utf-8")
    son = kaynak.split('if __name__ == "__main__":')[1]
    dogru("main try icinde", "try:" in son and "main()" in son)
    dogru("BaseException yakalaniyor", "except BaseException" in son)
    dogru("coku gunluge yaziliyor", "COKTU" in son)
    dogru("izleme de yaziliyor", "format_exc" in son)
    dogru("cikis kodu 1", "sys.exit(1)" in son)


def test_pythonw_altinda_yazdirma_cokmuyor():
    """`pythonw.exe` altinda `sys.stdout` None olur ve duz `print()`
    `AttributeError` atar. Gorev konsolsuz kostugu icin bu
    korunmazsa her tur duser."""
    kaynak = (_KOK / "yerel_nobetci.py").read_text(encoding="utf-8")
    govde = kaynak.split("def main(")[1].split("\nif __name__")[0]
    dogru("main icinde ciplak print yok", "print(" not in govde)
    dogru("_yaz kullaniliyor", "_yaz(" in govde)
    # GERCEK `pythonw` KOSULU: `sys.stdout` None.
    #
    # Ilk yazimda `_yaz("x", akis=None)` cagrilmisti ve bu YANLIS
    # kosuldu -- `akis=None` "akis yok" degil "varsayilani kullan"
    # demek, dolayisiyla sinama ekrana "sinama" yazdirdi ve hicbir
    # sey olcmedi.
    eski = sys.stdout
    try:
        sys.stdout = None
        yn._yaz("bu yazilmamali")
        dogru("stdout None iken `_yaz` cokmuyor", True)
    except Exception as e:                       # noqa: BLE001
        kaldi.append(f"stdout None iken `_yaz` coktu: {e}")
    finally:
        sys.stdout = eski


def test_alt_surec_pencere_acmiyor():
    """Her `subprocess` cagrisi `creationflags` tasimali.

    NEDEN: gorev `pythonw.exe` ile kosuyor, yani KONSOLU YOK.
    Windows'ta konsolsuz bir surecten baslatilan konsol uygulamasi
    KENDINE konsol ayirir; varsayilan terminal Windows Terminal
    oldugu icin bu, kucuk siyah bir kutu degil TAM BOY bir pencere.

    OLCULDU (2026-10-11), kullanici sikayetinden sonra: gorev tek
    basina tetiklendi ve surekli calisan bir pencere izleyicisi
    yakaladi --

        19:01:43  gorev tetiklendi
        19:01:44  1199x616  CASCADIA_HOSTING_WINDOW_CLASS
                  WindowsTerminal.exe

    On dakikada bir kosan gorev, tam ekran oyunda saatte alti kez
    odagi caliyordu. Duzeltmeden sonra ayni olcum: uc tetik, SIFIR
    pencere.

    BU SINAMA KAYNAGA BAKIYOR, ciktiya degil: pencerenin acilmadigini
    dogrulamak calisan bir izleyici gerektiriyor ve bu sinamanin isi
    o degil -- isi, bayragin bir daha DUSMEMESI.
    """
    kaynak = _kod((_KOK / "yerel_nobetci.py").read_text(encoding="utf-8"))
    import re as _re
    cagri = [m for m in _re.finditer(r"subprocess[.](?:run|Popen|call|check_output)[(]",
                                     kaynak)]
    dogru("en az bir subprocess cagrisi var (tarama dolu)", len(cagri) >= 1)
    for m in cagri:
        # Cagrinin kapanis parantezine kadar olan metni al.
        derinlik, son = 0, m.end()
        for i in range(m.end() - 1, len(kaynak)):
            if kaynak[i] == "(":
                derinlik += 1
            elif kaynak[i] == ")":
                derinlik -= 1
                if derinlik == 0:
                    son = i
                    break
        govde = kaynak[m.start():son]
        if "creationflags" not in govde:
            kaldi.append(f"subprocess cagrisi pencere bayragi tasimiyor: "
                         f"{govde[:60]}")
        else:
            dogru("subprocess cagrisi pencere acmiyor", True)


# ------------------------------------------------------------------
# TETIKLEMEK YETMEZ: SONUC VERDI MI?
#
# OLCULDU (2026-10-26 17:53 -> 22:13): nobetci 27 kez tetikledi, 27
# kez 204 aldi, icerik yasi 0.67 -> 5.01 saate MONOTON cikti. Her tur
# "tetikle: ... yanit=204" yaziyordu; gunluk BASARILI gorunuyordu.
# Tetiklenen kosular `test_harita` kirmizi yandigi icin dagitim
# adimina hic gelmiyordu.
#
# Kusur tetiklemede degil OLCUTTE: 204, "GitHub istegi kabul etti"
# demek -- "site tazelendi" demek DEGIL.

def _gunluk(*yaslar, arasina_taze=False):
    """Yas dizisinden gunluk satirlari uretir."""
    satir = []
    for i, y in enumerate(yaslar):
        if arasina_taze and i == len(yaslar) - 1:
            satir.append(f"2026-10-26T1{i}:00:00Z taze: icerik 0.10 saat")
        satir.append(f"2026-10-26T1{i}:10:00Z tetikle: icerik {y:.2f} saat,"
                     f" esik 0.60 yanit=204 (4.0s)")
    return satir


def test_gunluk_satiri_cozuluyor():
    es("tetikle satiri", yn._satir_coz(
        "2026-10-26T22:13:10Z tetikle: icerik 5.01 saat, esik 0.60"
        " yanit=204 (4.1s)"), ("tetikle", 5.01))
    es("taze satiri", yn._satir_coz(
        "2026-10-25T21:13:11Z taze: icerik 0.10 saat, esik 0.60 (1.9s)"),
        ("taze", 0.1))
    # Yassiz satirlar: karar okunur, yas None kalir.
    es("bilinmiyor satiri", yn._satir_coz(
        "2026-10-01T10:00:00Z bilinmiyor: durum ucu okunamadi (2.0s)"),
        ("bilinmiyor", None))
    for bozuk in ("", "tek", "2026 iki", "COKTU kayit yok"):
        es(f"{bozuk!r} cozulemez", yn._satir_coz(bozuk), None)


def test_dizi_araya_giren_taze_turda_kiriliyor():
    """Araya giren bir `taze` tur, onceki tetiklemenin SONUC VERDIGI
    anlamina gelir -- dizi orada bitmeli.

    Bu kirilma olmasaydi dizi gunler boyunca birikir ve saglikli bir
    hat da bir sure sonra BOZUK sayilirdi.
    """
    es("taze turdan sonrasi sayiliyor",
       yn.son_tetik_dizisi(_gunluk(1.0, 2.0, 3.0, 4.0, arasina_taze=True)),
       [4.0])
    es("kesintisiz dizi tam sayiliyor",
       yn.son_tetik_dizisi(_gunluk(1.0, 2.0, 3.0)), [1.0, 2.0, 3.0])
    es("bos gunluk -> bos dizi", yn.son_tetik_dizisi([]), [])


def test_sonucsuz_dizi_bozuk_diyor():
    v = {"icerik_yasi_saat": 5.01, "esik_saat": 0.6}
    k, s = yn.karar_ver(v, kosu_var=False, dizi=[0.67, 1.0, 2.0, 3.0])
    es("sonucsuz dizi -> bozuk", k, yn.KARAR_BOZUK)
    dogru("sebep dizi uzunlugunu yaziyor", "4 ardisik" in s)
    dogru("sebep iki ucu da yaziyor", "0.67" in s and "5.01" in s)


def test_esik_altindaki_dizi_bozuk_DEMIYOR():
    """ESIK GERCEKTEN ELIYOR -- bu depoda cogu esik elemedigi icin
    kaldirilmisti, o yuzden olculdu.

    Gunlukteki 400 satirda (2026-10-20 -> 10-26) 68 ardisik tetikleme
    dizisi vardi:

        dizi uzunlugu   saglikli hat   arizada
        1               cok             --
        2               1 kez           --
        3+              HIC             27

    Dagilimlar CAKISMIYOR: saglikli hat ucuncu ardisik tetiklemeye
    hic ulasmiyor, cunku bir tetikleme sonuc verdiginde sonraki tur
    `taze` yaziyor ve dizi kiriliyor.
    """
    v = {"icerik_yasi_saat": 2.5, "esik_saat": 0.6}
    for dizi in ([], [1.0], [1.0, 2.0]):
        k, _ = yn.karar_ver(v, kosu_var=False, dizi=dizi)
        es(f"{len(dizi)} ardisik -> tetikle (bozuk DEGIL)",
           k, yn.KARAR_TETIKLE)


def test_yas_dusuyorsa_bozuk_degil():
    """Uzun dizi tek basina ariza DEGIL: hat yavas ama CALISIYOR
    olabilir. Olcut dizinin uzunlugu degil, yasin DUSMEMESI.
    """
    v = {"icerik_yasi_saat": 0.9, "esik_saat": 0.6}
    k, _ = yn.karar_ver(v, kosu_var=False, dizi=[3.0, 2.0, 1.5, 1.0])
    es("yas dustu -> tetikle", k, yn.KARAR_TETIKLE)


def test_bozuk_taze_ve_kosan_durumu_EZMIYOR():
    """Karar sirasi: once bilinmezlik, sonra tazelik, sonra kosu.

    Bozuk kontrolu en sona konmali. Basa konsaydi taze bir site
    "bozuk" diye duyurulur ve duyuru inandiriciligini yitirirdi.
    """
    uzun = [1.0, 2.0, 3.0, 4.0]
    es("taze + uzun dizi -> taze", yn.karar_ver(
        {"icerik_yasi_saat": 0.1, "esik_saat": 0.6}, False, uzun)[0],
       yn.KARAR_TAZE)
    es("kosuyor + uzun dizi -> kosuyor", yn.karar_ver(
        {"icerik_yasi_saat": 5.0, "esik_saat": 0.6}, True, uzun)[0],
       yn.KARAR_KOSUYOR)
    es("bilinmiyor + uzun dizi -> bilinmiyor",
       yn.karar_ver(None, False, uzun)[0], yn.KARAR_BILINMIYOR)


def test_bozuk_karari_tetiklemeyi_KESMIYOR():
    """Hat kopukken tetiklemeyi kesmek, duzelme anini kacirmak olurdu:
    kaynak duzeltildigi an ilk tur yayina almali.
    """
    kaynak = _kod((_KOK / "yerel_nobetci.py").read_text(encoding="utf-8"))
    dogru("tetikleme kosulu BOZUK'u da kapsiyor",
          "karar in (KARAR_TETIKLE, KARAR_BOZUK)" in kaynak)
    # CAGRI ARANIYOR, TANIM DEGIL.
    #
    # Ilk yazimda iddia `"duyur(jeton" in kaynak` idi ve mutasyon
    # KACTI: cagri satiri silindiginde bile dizge dosyada kaliyordu,
    # cunku fonksiyonun KENDI TANIMI (`def duyur(jeton: str, ...)`)
    # ayni dizgeyi tasiyor. Bir dizgenin dosyada gecmesi, DOGRU
    # YERDE gectigini kanitlamaz -- bu depoda `sayac.js` ayni
    # bicimde yakalanmisti.
    govde = kaynak.split("def main()")[1]
    dogru("main icinde BOZUK dali var", "if karar == KARAR_BOZUK:" in govde)
    dal = govde.split("if karar == KARAR_BOZUK:")[1].lstrip(chr(10))
    # Dalin govdesi: girintisi SURDUGU surece.
    girinti = len(dal) - len(dal.lstrip(" "))
    satirlar = []
    for satir in dal.splitlines():
        if satir.strip() and len(satir) - len(satir.lstrip(" ")) < girinti:
            break
        satirlar.append(satir)
    dogru(f"BOZUK dali duyuru cagiriyor ({len(satirlar)} satir)",
          "duyur(" in chr(10).join(satirlar))


def test_duyuru_basligi_TEK_YERDE():
    """Baslik hem ararken hem acarken kullaniliyor. Iki yerde ayri
    yazilsaydi arama hic eslesmez ve nobetci her on dakikada YENI bir
    konu acardi -- duyuru kendisi gurultuye donusurdu.
    """
    kaynak = _kod((_KOK / "yerel_nobetci.py").read_text(encoding="utf-8"))
    govde = kaynak.split("def duyur(")[1].split(chr(10) + "def ")[0]
    dogru("sabit kullaniliyor", govde.count("DUYURU_BASLIGI") >= 2)
    dogru("baslik duyur icinde SABIT YAZILI degil",
          yn.DUYURU_BASLIGI not in govde)


def test_duyuru_acik_konu_varken_YENISINI_ACMIYOR():
    """Ag yok: `_istek` gecici olarak degistiriliyor."""
    import json as _json

    cagrilar = []

    def _sahte(adres, govde=None, jeton="", yontem="GET"):
        cagrilar.append((yontem, adres))
        if "issues?state=open" in adres:
            return 200, _json.dumps(
                [{"number": 7, "title": "x " + yn.DUYURU_BASLIGI + " y"}])
        return 201, "{}"

    gercek = yn._istek
    try:
        yn._istek = _sahte
        sonuc = yn.duyur("jeton-yok", "sebep")
    finally:
        yn._istek = gercek
    dogru("zaten acik diyor", "zaten acik" in sonuc)
    dogru("konu numarasini yaziyor", "#7" in sonuc)
    es("HICBIR POST yapilmadi",
       [y for y, _a in cagrilar if y == "POST"], [])


def test_duyuru_basarisizligi_SESSIZ_KALMIYOR():
    """Duyurunun kendisi de basarisiz olabilir (yetki, ag) ve o da
    tam olarak ogrenilmesi gereken sey.
    """
    def _sahte(adres, govde=None, jeton="", yontem="GET"):
        if "issues?state=open" in adres:
            return 200, "[]"
        return 403, "{}"

    gercek = yn._istek
    try:
        yn._istek = _sahte
        sonuc = yn.duyur("jeton-yok", "sebep")
    finally:
        yn._istek = gercek
    dogru("basarisizlik raporlaniyor", "BASARISIZ" in sonuc)
    dogru("durum kodu yaziliyor", "403" in sonuc)


def test_gunluk_okunamazsa_bozuk_DEMIYOR():
    """Olcum aracinin kendi arizasi, olculen seyin arizasi DEGIL.

    Gunluk okunamadiginda gecmis BILINMIYOR; bilinmeyen bir gecmis
    "27 ardisik tetikleme" kadar bilgi tasimaz.
    """
    gercek = yn.GUNLUK
    try:
        yn.GUNLUK = _KOK / "olmayan-dizin-xyz" / "yok.log"
        es("okunamayan gunluk -> bos", yn.gunluk_oku(), [])
    finally:
        yn.GUNLUK = gercek


def test_duyuru_govdesi_OKUNABILIR():
    """Duyuru govdesi satirlara bolunmus olmali.

    NEDEN IDDIA: govde `NL` ile birlestiriliyor. Bir gun biri onu
    bosluk ile birlestirse konu metni TEK PARAGRAF olur -- icerik
    aynidir, hata vermez, sinama kirmizi yanmaz; yalnizca okunmasi
    gereken an okunmaz hale gelir.

    Ilk yazimda buranin yerinde "kaynakta hic ters bolu olmasin"
    iddiasi vardi ve YANLISTI: dosyadaki 17 ters bolunun hepsi
    mesru (Windows yollari, git credential protokolu, gunluk
    birlestirme). Yani gecerli kodu kusur sayiyordu. Kontrol
    karakteri taramasi ZATEN `test_kacis.py` dosyasinda yapiliyor.
    """
    import json as _json

    yakalanan = {}

    def _sahte(adres, govde=None, jeton="", yontem="GET"):
        if "issues?state=open" in adres:
            return 200, "[]"
        if yontem == "POST" and govde:
            yakalanan.update(govde)
            return 201, "{}"
        return 200, _json.dumps({"workflow_runs": []})

    gercek = yn._istek
    try:
        yn._istek = _sahte
        yn.duyur("jeton-yok", "4 ardisik tetikleme SONUC VERMEDI")
    finally:
        yn._istek = gercek

    govde = yakalanan.get("body", "")
    dogru("govde uretildi", bool(govde))
    satirlar = govde.splitlines()
    dogru(f"govde satirlara bolunmus ({len(satirlar)})", len(satirlar) >= 5)
    # Iki karakterlik kacis dizgesi METINDE kalmamali: kalmissa
    # birlestirme yapilmamis, kacis okura HAM gorunur.
    dogru("ham kacis dizgesi yok", (chr(92) + "n") not in govde)
    dogru("olcum govdede geciyor", "4 ardisik" in govde)
    dogru("bakilacak yeri soyluyor", "dusen adim" in govde)
    es("NL gercek satir sonu", yn.NL, chr(10))


# ---------------------------------------------------------------------
# BILANCO GUNLUK TETIGI
# ---------------------------------------------------------------------
#
# NEDEN VAR: ucretsiz AI kotasi 00:00 UTC'de sifirlaniyor ve haber
# hatti gun icinde tuketiyor (~32 kosu x ~5 cagri). Bilanco kosusu
# kotayi BITMIS buluyordu ve sifir sayfa uretiyordu -- olculdu,
# kosu #55 ve #56'da ILK sirkette 429.
#
# Cron ile cozulemiyor: bu depoda GitHub'in zamanlanmis kosulari
# 5-7 saat gecikiyor (06:23 planli -> 11:48-13:40 gercek).

def _an(gun, saat):
    import datetime as _dt
    return _dt.datetime.fromisoformat(f"{gun}T{saat}:00+00:00")


def test_bilanco_tetigi_SAATTEN_ONCE_atilmiyor():
    dogru("00:05'te atilmiyor (esik 00:10)",
          yn.bilanco_gerekli(_an("2026-10-30", "00:05"), []) is False)
    dogru("00:15'te atiliyor",
          yn.bilanco_gerekli(_an("2026-10-30", "00:15"), []) is True)


def test_bilanco_tetigi_GUNDE_BIR():
    g = [f"2026-10-30T00:12:00Z {yn.BILANCO_DAMGASI}: yanit=204"]
    dogru("ayni gun IKINCI kez atilmiyor",
          yn.bilanco_gerekli(_an("2026-10-30", "06:00"), g) is False)
    dogru("ERTESI gun yine atiliyor",
          yn.bilanco_gerekli(_an("2026-10-31", "00:15"), g) is True)


def test_bilanco_damgasi_TEK_YERDE():
    """Yazarken ve ararken AYNI sabit.

    Iki yerde ayri yazilsaydi arama hic eslesmez ve nobetci her on
    dakikada YENIDEN tetiklerdi -- gunde 144 kosu. Ayni ders
    `DUYURU_BASLIGI` icin de yazili.
    """
    kaynak = (pathlib.Path(__file__).resolve().parent
              / "yerel_nobetci.py").read_text(encoding="utf-8")
    dogru("damga govdede SABIT YAZILI degil",
          kaynak.count('"' + yn.BILANCO_DAMGASI + '"') == 1)


def test_bilanco_tetigi_DOGRU_IS_AKISINI_cagiriyor():
    """Ag yok: `_istek` gecici olarak degistiriliyor.

    ATILLIK: cagri gercekten yapilmis olmali. Hicbir cagri olmasaydi
    "dogru adres" iddiasi bos bir listeden gecerdi.
    """
    cagrilar = []

    def _sahte(adres, govde=None, jeton="", yontem="GET"):
        cagrilar.append((yontem, adres, govde))
        return 204, ""

    gercek = yn._istek
    try:
        yn._istek = _sahte
        kod = yn.bilanco_tetikle("jeton")
    finally:
        yn._istek = gercek
    dogru("cagri YAPILDI", len(cagrilar) == 1)
    dogru("yanit kodu donuyor", kod == 204)
    _yontem, _adres, _govde = cagrilar[0]
    dogru("POST ile", _yontem == "POST")
    dogru("BILANCO is akisi cagriliyor", yn.BILANCO_AKISI in _adres)
    # YANLIS AKISI CAGIRMAK SESSIZ BIR KUSUR OLURDU: tetik 204
    # doner, gunluge "tamam" yazilir ve bilanco hic kosmaz.
    dogru("haber akisi DEGIL", yn.IS_AKISI not in _adres)
    dogru("main dalinda", (_govde or {}).get("ref") == "main")


def test_bilanco_tetigi_ANA_AKISTA_cagriliyor():
    """Islev dogru calissa da `main` onu sormazsa kapi OLU kalir.

    Olcut AST: metin aramak bicimlendirme degisince sessizce
    eslesmeyi birakiyor -- bu depoda iki kez oldu.
    """
    import ast

    kaynak = (pathlib.Path(__file__).resolve().parent
              / "yerel_nobetci.py").read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    ana = next(f for f in ast.walk(agac)
               if isinstance(f, ast.FunctionDef) and f.name == "main")
    adlar = {c.func.id for c in ast.walk(ana)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    dogru("main bilanco_gerekli SORUYOR", "bilanco_gerekli" in adlar)
    dogru("main bilanco_tetikle CAGIRIYOR", "bilanco_tetikle" in adlar)



for _ad, _f in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_f):
        _f()

if kaldi:
    print("yerel nobetci: KIRIK")
    for _x in kaldi:
        print("  ", _x)
    raise SystemExit(1)
print(f"yerel nobetci: {gecti} dogrulama gecti")
