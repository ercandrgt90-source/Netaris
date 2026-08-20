"""Bilanco hatti -- sektor sektor cek, olc, sektor medyanini kur.

    sirket defteri -> sektor -> mali tablo -> Donem -> sektor medyani

    python uret_bilanco.py --sektor "Temel malzeme"
    python uret_bilanco.py --hepsi          # butun sektorler
    python uret_bilanco.py --sektor X --kuru-calis   # yazmadan olc

NEDEN SEKTOR SEKTOR
-------------------
Sektor medyani ancak sektorun TAMAMI cekildikten sonra hesaplanabilir.
Sirket sirket ilerleyip her birinde "sektorum ne durumda" diye sormak,
her sirket icin sektoru bastan cekmek demekti.

SIRKET SECIMI -- OLCULEBILIR KURAL
----------------------------------
"Hangi sirketler" editoryal bir soru ve cevabi burada YAZILI:
sektoru bilinen ve mali tablosu YETERLI olan her sirket. Ikisi de
olculebilir; "onemli sirketler" gibi tanimsiz bir olcut kullanilmadi.

Sektoru bilinmeyen 441 kaydin cogu BIST'te hisse senedi islem
gormuyor (banka, finansal kiralama, araci kurum, yatirim ortakligi);
onlar zaten bu kapiya gelmiyor.

CEKILEN VERI YAZILMADAN ONCE DENETLENIYOR
-----------------------------------------
Her sirketin bilancosu muhasebe ozdeslikleriyle sinaniyor
(`bilanco_ag.ozdeslik_denetimi`). Tutmayan sirket ATLANIYOR ve
sebebi raporlaniyor -- bir sirketin bozuk verisi sektor medyanini da
bozar.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import bilanco_ag      # noqa: E402
import oranlar         # noqa: E402
import sektor_ozet     # noqa: E402

DEFTER = _KOK / "kaynak" / "sirketler.json"
HEDEF = _KOK / "kaynak" / "sektor_ozet.json"

#: Sirketler arasi bekleme. Kaynak bizim degil.
ARA_SN = 0.5


def _defter() -> dict:
    return json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]


def sektordeki(sektor_tr: str) -> list[tuple[str, dict]]:
    """Sektordeki BENZERSIZ sirketler. Hisse siniflari tekillestirilir.

    Is Bankasi'nin bes kodu var; besini de cekmek ayni sirketi bes kez
    saymak ve sektor medyanini o sirkete dogru cekmek olurdu.
    """
    gorulen: set[str] = set()
    cikti: list[tuple[str, dict]] = []
    for kod, v in sorted(_defter().items()):
        if v.get("sektor_tr") != sektor_tr:
            continue
        kimlik = v.get("kap_kimlik") or kod
        if kimlik in gorulen:
            continue
        gorulen.add(kimlik)
        cikti.append((kod, v))
    return cikti


def sektor_isle(sektor_tr: str, donem_etiketi: str, ceyrek: int = 2,
                sinir: int | None = None) -> dict:
    """Bir sektorun tamamini ceker, olcer ve medyanini kurar."""
    sirketler = sektordeki(sektor_tr)
    if sinir:
        sirketler = sirketler[:sinir]
    print(f"\n=== {sektor_tr}  ({len(sirketler)} şirket)")

    olculen: dict[str, dict] = {}
    atlanan: list[tuple[str, str]] = []

    for kod, bilgi in sirketler:
        tablolar = bilanco_ag.ara_donem(kod, ceyrek)
        # OZDESLIK ONCE. Bozuk bilanco sektor medyanini da bozar.
        tekil = {ad: d[0] for ad, d in
                 (tablolar.get("_ham_bilanco") or {}).items()} \
            if tablolar.get("_ham_bilanco") else {}
        alanlar = bilanco_ag.donemi_kur(tablolar)
        tamam, eksik = bilanco_ag.yeterli(alanlar, sektor_tr)
        if not tamam:
            atlanan.append((kod, "eksik: " + ", ".join(eksik[:3])))
            time.sleep(ARA_SN)
            continue
        if tekil:
            bozuk = bilanco_ag.ozdeslik_denetimi(tekil)
            if bozuk:
                atlanan.append((kod, "özdeşlik: " + bozuk[0][:40]))
                time.sleep(ARA_SN)
                continue

        d = oranlar.Donem(etiket=donem_etiketi, **alanlar)
        olculen[kod] = _oranlari(d)
        print(f"  {kod:<8}ölçüldü")
        time.sleep(ARA_SN)

    medyanlar = sektor_ozet.sektor_medyanlari(olculen)
    print(f"  -> {len(olculen)} şirket ölçüldü, {len(atlanan)} atlandı")
    if not medyanlar:
        print(f"  -> medyan URETILMEDI (en az {sektor_ozet.EN_AZ_SIRKET} "
              f"şirket gerekiyor)")
    return {
        "sektor": sektor_tr,
        "donem": donem_etiketi,
        "sirket_sayisi": len(olculen),
        "medyan": medyanlar,
        "sirket": olculen,
        "atlanan": atlanan,
    }


def _oranlari(d) -> dict[str, float]:
    """`Donem`den karsilastirilacak oranlari cikarir.

    Oranlar BURADA YENIDEN HESAPLANMIYOR -- `oranlar.py` ne
    hesapliyorsa o kullaniliyor. Ikinci bir hesap, iki farkli dogru
    demek olurdu.
    """
    cikti: dict[str, float] = {}
    if d.hasilat:
        if d.brut_kar is not None:
            cikti["brut_marj"] = d.brut_kar / d.hasilat * 100
        if d.net_kar is not None:
            cikti["net_marj"] = d.net_kar / d.hasilat * 100
    if d.ozkaynak and d.net_kar is not None:
        cikti["roe"] = d.net_kar / d.ozkaynak * 100
    if d.kisa_vadeli_yukumlulukler and d.donen_varliklar is not None:
        cikti["cari_oran"] = d.donen_varliklar / d.kisa_vadeli_yukumlulukler
    if d.ozkaynak and d.net_borc is not None:
        cikti["borc_ozkaynak"] = d.net_borc / d.ozkaynak
    return cikti


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sektor")
    a.add_argument("--hepsi", action="store_true")
    a.add_argument("--donem", default="2026/6")
    a.add_argument("--ceyrek", type=int, default=2)
    a.add_argument("--sinir", type=int, help="sektör başına en fazla şirket")
    a.add_argument("--kuru-calis", action="store_true", help="dosyaya yazma")
    n = a.parse_args()

    if not n.sektor and not n.hepsi:
        a.error("--sektor ya da --hepsi gerekli")

    if n.hepsi:
        sektorler = sorted({v["sektor_tr"] for v in _defter().values()
                            if v.get("sektor_tr")})
    else:
        sektorler = [n.sektor]

    cikti = {}
    for s in sektorler:
        cikti[s] = sektor_isle(s, n.donem, n.ceyrek, n.sinir)

    if n.kuru_calis:
        print("\n(kuru çalışma -- dosyaya yazılmadı)")
        return 0
    HEDEF.write_text(json.dumps(cikti, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"\n{HEDEF} yazıldı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
