# -*- coding: utf-8 -*-
"""CIKTIYA BAKAN SINAMALARI, CIKTI VARKEN KOSTURUR.

BU DOSYA NEDEN VAR
------------------
Hat sinamalari CI'da icerik URETILMEDEN ONCE kosuyor (is akisinda
"Testleri calistir" adimi, "Veri topla ve icerik uret" adimindan
once). `site/cikti` ise `.gitignore` icinde ve depoda IZLENMIYOR --
yani taze bir kopyada o dizin YOK.

Sonuc: ciktiya bakan her sinama "ATLANDI cikti yok" deyip YESIL
donuyordu. OLCULDU (2026-10-11), cikti gecici olarak kaldirilip
butun sinamalar kosturuldu:

    cikti yokken atlayan sinama       42
    ornek: test_yetim_sayfa.py   ->  "TUM TESTLER GECTI (0)"
           test_erisim_yapisi.py ->  "TUM TESTLER GECTI (0)"

Sifir kontrol kosuyor, cikis kodu 0, CI yesil. Bu, kirmizi bir
sinamadan KOTU: kirmizi sorunu duyurur, korlesen sinama ORTBAS EDER.

Atlayanlar arasinda YASAL yukumluluk tasiyanlar da vardi:
`test_lisans.py` (lisansi bizde olmayan seriler), `test_lisans_atfi.py`
(CC BY atfi), `test_ticari_atif.py` (ticari kaynak atfi).

NE YAPIYOR
----------
1. Cikti VAR MI diye bakar. Yoksa KIRMIZI doner -- "atlandi, gecti"
   demez. Bu dosyanin butun varlik sebebi o sessizligi bozmak.
2. Ciktiya bakan sinamalari BULARAK secer, elle sayarak degil.
   Liste tutmak bu depoda bir kez denendi ve sessizce eskidi: yedi
   dosya yaziliydi, depoda on sinama vardi.
3. Her birini kosturur. Biri bile duserse kirmizi doner.
4. CIKTI VARKEN "ATLANDI" YAZAN SINAMA DA KIRMIZI SAYILIR. Cikti
   yerindeyken atlayan bir sinama yanlis yere bakiyordur; o da
   sessiz bir korluktur.

Maliyet olculdu: 42 sinama 45 saniye. Insa ~5 dakika.

NEREDE CAGRILIYOR
-----------------
`calistir.py` icinde, site uretiminden SONRA ve dagitimdan ONCE --
`denetim.py` ikinci kosusuyla ayni kapida. Ayni ders bu depoda
dorduncu kez uygulaniyor (yorum denetimi, beyan denetimi, cikti
denetimi, simdi de ciktiya bakan sinamalar).
"""

from __future__ import annotations

import pathlib
import concurrent.futures as cf
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent.parent
CIKTI = KOK / "site" / "cikti"
ARANAN = (KOK / "haber_botu", KOK / "site")

#: Cikti dizinine YOL olarak deginme izleri. Bkz. `ciktiya_bakan`.
YOL_IZI = ('"cikti"', 'CIKTI')

#: URETIM SIRASINDA YAZILAN IKINCI DIZIN: `site/icerik`.
#:
#: `site/cikti` HTML'i tutuyor, ama hattin urettigi MARKDOWN
#: `site/icerik` icine yaziliyor (bilanco analizleri, makro yazilar).
#: O dizine bakan sinamalar da uretimden SONRA kosmali; CI'in sinama
#: adimi uretimden ONCE kosuyor ve orada depodaki ESKI icerigi
#: denetliyorlar.
#:
#: Olculdu (2026-10-14): yalnizca icerige bakan dort sinama var
#: (`test_kumulatif_temizle`, `test_baski`,
#: `test_bilanco_sayfa_saglam`, `test_yinelenen_kelime`). Dordu de
#: o kosuda URETILEN icerigi degil oncekini goruyordu, yani yeni
#: bozuk bir sayfa ancak BIR SONRAKI kosuda yakalaniyordu.
#:
#: Ayni korluk bu depoda uc kez yasandi; bkz. dosya basligi.
ICERIK_IZI = ('"icerik"', "'icerik'")


def ciktiya_bakan() -> list:
    """Kaynaginda cikti dizini YOLUNA deginen sinamalar.

    OLCUT KELIME DEGIL YOL. Ilk yazimda olcut "kaynakta 'cikti'
    kelimesi geciyor mu" idi ve TURKCENIN KENDISINE takildi:
    "cikti" ayni zamanda yaygin bir fiil ("bu kusur uc kez CIKTI")
    ve bir degisken adi (`cikti = []`). Olculdu -- 81 sinama
    seciliyordu, ikisi tamamen alakasizdi ve biri
    (`test_zaman_bombasi.py`) TEK BASINA 181 saniye suruyordu.

    Yol izine bakan olcut 51 sinama seciyor. Dogrulandi (2026-10-11):
    cikti gecici olarak kaldirilip butun sinamalar kosturuldu ve
    "ATLANDI ... cikti" diyen 43 sinamanin TAMAMI bu 51'in icinde.
    Yani kacan yok.

    Yanlis pozitif zararsiz: ciktiya bakmayan hizli bir sinama bir
    kez daha kosar.
    """
    bulunan = []
    for kok in ARANAN:
        for p in sorted(kok.rglob("test_*.py")):
            if "__pycache__" in p.parts:
                continue
            try:
                k = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(x in k for x in YOL_IZI + ICERIK_IZI):
                bulunan.append(p)
    return bulunan


def main() -> int:
    if not (CIKTI / "index.html").exists():
        print("HATA: site/cikti yok -- bu kosu HICBIR SEY dogrulamaz.")
        print("  Bu dosyanin isi tam olarak o sessizligi bozmak:")
        print("  ciktiya bakan sinamalar cikti yokken 'gecti' der.")
        print("  Once `python site/insa.py` calistirilmali.")
        return 1

    sinamalar = ciktiya_bakan()
    print(f"Ciktiya bakan sinama: {len(sinamalar)}")
    # TABAN 35: olculen gercek bagimli sinama sayisi 43, secilen 51
    # (2026-10-14'te icerik izi eklenince 55).
    # Esik bu degerlerin ALTINA, ama anlamli bir dususu yakalayacak
    # kadar yakina kondu -- tarama bozulursa (yol degisir, dizin
    # tasinir) sayi bir anda duser ve bu kirmizi yanar. Esigi 10'da
    # birakmak, 40 sinamanin kaybolmasini sessizce gecirirdi.
    if len(sinamalar) < 35:
        print(f"HATA: yalnizca {len(sinamalar)} sinama bulundu -- "
              f"tarama bozuk olmali (beklenen ~55).")
        return 1

    bas = time.time()

    def kostur(p):
        s = subprocess.run([sys.executable, "-B", str(p)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(KOK))
        return p, s.returncode, (s.stdout or "") + (s.stderr or "")

    # PARALEL -- OLCUT GENIS TUTULABILSIN DIYE.
    #
    # Dar bir olcut (yalnizca yol referansi tasiyanlar) 51 sinama
    # seciyordu ve olculdu: atlayan 42 sinamanin BIRINI kaciriyordu
    # (`test_adres.py`). Metne dayali her olcut boyle bir kenar
    # birakir; bu depoda "liste sessizce eskidi" kusuru zaten yasandi.
    #
    # Cozum olcutu daraltmak degil, maliyeti dusurmek: sinamalar
    # dosya tarayan I/O isleri, paralel kosmaya uygun. Olculdu:
    # 81 sinama sirayla 230 saniye, sekiz is parcacigiyla ~45 saniye.
    dusen, korlesen = [], []
    with cf.ThreadPoolExecutor(max_workers=8) as havuz:
        for p, kod, metin in havuz.map(kostur, sinamalar):
            if kod != 0:
                dusen.append((p, metin))
            elif any("ATLANDI" in s and "cikti" in s.lower()
                     for s in metin.splitlines()):
                # CIKTI YERINDE ama sinama yine CIKTI YOK diyor:
                # yanlis yere bakiyor demektir. Yesil gorunup hicbir
                # sey olcmeyen sinama, kirmizi olandan tehlikeli.
                #
                # Olcut "ATLANDI gecen her satir" DEGIL: veri
                # yoklugundan atlayanlar mesru ve ayri bir sey
                # soyluyorlar ("takvimde aciklanmis deger yok").
                # Ilk yazimda bu ayrim yoktu ve `test_takvim_birimi`
                # yanlislikla korlesen diye bildirildi.
                korlesen.append(p)

    sure = time.time() - bas
    print(f"  {len(sinamalar) - len(dusen)} yesil / {len(dusen)} kirmizi "
          f"({sure:.0f} saniye)")
    for p, m in dusen:
        print("")
        print(f"  KIRMIZI {p.relative_to(KOK)}")
        for satir in m.strip().splitlines()[-12:]:
            print(f"      {satir}")
    if korlesen:
        print("")
        print("  CIKTI VARKEN ATLAYAN (yanlis yere bakiyor):")
        for p in korlesen:
            print(f"      {p.relative_to(KOK)}")
    return 1 if (dusen or korlesen) else 0


if __name__ == "__main__":
    sys.exit(main())
