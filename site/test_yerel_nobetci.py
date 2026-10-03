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


for _ad, _f in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_f):
        _f()

if kaldi:
    print("yerel nobetci: KIRIK")
    for _x in kaldi:
        print("  ", _x)
    raise SystemExit(1)
print(f"yerel nobetci: {gecti} dogrulama gecti")
