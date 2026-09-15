"""SEKTOR SUPURMESININ SURE BUTCESI.

BU DOSYA NEDEN VAR
------------------
`sektor_ozet.json` TEK SEFERDE, dongunun en sonunda yaziliyor. Yani
kosu ortada kesilirse o ana kadarki butun emek cope gidiyor: yarim
kalan bir kosu, hic kosmamis bir kosuyla ayni sonucu veriyor.

Olculdu (2026-09-15): calisan kosu "Bilanco verisi" adiminda 97
DAKIKAYI gecti ve hala tek satir yazmamisti. Is akisinin kendi siniri
`timeout-minutes: 330` -- yani en kotu durumda bes buçuk saat calisip
SIFIR uretebilirdi.

Butce dolunca durmak veri kaybettirmiyor, cunku uc duzenek birlikte
calisiyor:
  1. BIRLESTIRME  -- cekilmeyen sektorler `onceki_ozet`ten geliyor.
  2. BAYATLIK SIRASI -- siradaki kosu en geride kalandan basliyor.
  3. BUTCE        -- hicbir kosu sinirsiz surmuyor.
Ucu olmadan digeri ise yaramiyor: butce tek basina veri kaybettirir,
bayatlik sirasi tek basina yakinsamayi garanti etmez.

NE SINANIYOR
------------
1. Esik: butcenin altinda devam, ustunde duruyor.
2. ILK SEKTOR HER ZAMAN isleniyor -- yoksa kucuk bir butce, kosuyu
   hic is yapmadan bitirirdi.
3. Karar UYGULAMANIN KENDISINDEN cagriliyor (kopya mantik degil).
4. Butceyle atlanan, "hic cekilemeyen"den AYRI raporlaniyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import uret_bilanco as U   # noqa: E402


def test_butce_altinda_devam_ediyor():
    assert U.butce_doldu(gecen_dk=10, butce_dk=45, islenen=3) is False


def test_butce_ustunde_duruyor():
    assert U.butce_doldu(gecen_dk=46, butce_dk=45, islenen=3) is True


def test_tam_butcede_durmuyor():
    """Esik KATI: tam butcede biten kosu butceyi ASMIS sayilmaz."""
    assert U.butce_doldu(gecen_dk=45, butce_dk=45, islenen=3) is False


def test_ilk_sektor_her_zaman_isleniyor():
    """KORUMA -- ozen degil.

    Butce sifir ya da cok kucuk verildiginde dongu hic donmeden
    cikardi: `cikti` yalnizca onceki veriyi tasir, kosu "tazelenen 0"
    diye biter. Daha kotusu `--sektor` ile tek sektorluk kosularda
    butce o TEK sektoru de atlardi -- en cok is goren yol, hic is
    gormezdi.
    """
    assert U.butce_doldu(gecen_dk=9999, butce_dk=0, islenen=0) is False
    # Ikinciden itibaren butce isliyor.
    assert U.butce_doldu(gecen_dk=9999, butce_dk=0, islenen=1) is True


def test_varsayilan_butce_is_akisi_sinirinin_altinda():
    """Butce, `timeout-minutes` degerinden KUCUK olmali.

    Buyuk olsaydi butce hic ateslenmez, is akisi kosuyu OLDURURDU ve
    kosu hicbir sey yazmadan biterdi -- yani butce, korumasi gereken
    seyin ta kendisini kacirirdi.
    """
    import re
    y = (_KOK.parent / ".github" / "workflows" / "bilanco.yml")
    m = re.search(r"timeout-minutes:\s*(\d+)", y.read_text(encoding="utf-8"))
    assert m, "is akisinda timeout-minutes yok"
    assert U.SURE_BUTCESI_DK < int(m.group(1)), (U.SURE_BUTCESI_DK, m.group(1))


def test_karar_uygulamadan_cagriliyor():
    """Mantik KOPYALANMIYOR -- uretim kodu bu islevi cagiriyor.

    Bu depoda mantigi kopyalayan bir sinama daha once mutasyonu
    kacirdi (`kuyruk_kur`): uretimdeki kural kaldirildiginda sinama
    yine yesil kaldi, cunku olctugu sey kendi kopyasiydi.
    """
    k = (_KOK / "uret_bilanco.py").read_text(encoding="utf-8")
    # Cagriya OZEL: ciplak "butce_doldu" tanimda ve yorumlarda da
    # geciyor; onlari saymak, kaldirilmis bir cagriyi duruyor
    # gosterirdi.
    assert "if butce_doldu(_gecen, n.butce_dk, _i):" in k


def test_butceyle_atlanan_ariza_diye_sayilmiyor():
    """Planli durus ile gercek ariza AYNI SATIRDA sayilmamali.

    Ikisini birlestirmek iki yonde de yaniltir: planli bir durus
    ariza gibi okunur, ya da gercek bir ariza "zaten butce doldu"
    diye gecistirilir.
    """
    k = (_KOK / "uret_bilanco.py").read_text(encoding="utf-8")
    assert "and k not in butce_atladi]" in k, "_atlanan butceyi disliyor"
    assert "süre bütçesi" in k, "kosu ozetinde ayri satir var"


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
