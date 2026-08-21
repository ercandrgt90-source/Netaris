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

#: KAP ARA DONEM BILDIRIM SINIRLARI (konsolide, aya gore).
#:
#: Sirketler mali tablolarini donem bitiminden sonra belli bir sure
#: icinde bildiriyor. Hat her yarim saatte kosarsa AYNI veriyi tekrar
#: tekrar cekip hicbir sey degistirmez; kaynaga yuk, bize maliyet.
#:
#: Bildirimlerin YOGUNLASTIGI aylar:
#:   3 aylik  -> Mayis
#:   6 aylik  -> Agustos
#:   9 aylik  -> Kasim
#:   12 aylik -> Mart
#: Ayin tamamı acik birakildi: sirketler ayni gun bildirmiyor.
BILDIRIM_AYLARI = {3: 12, 5: 3, 8: 6, 11: 9}


def donem_acik(bugun=None) -> tuple[bool, str]:
    """Bugun bilanco cekmenin anlamli oldugu bir ayda miyiz?

    Doner: (acik_mi, aciklama). Kapaliyken de ACIKLAMA doner --
    "neden calismadi" sorusu loga bakinca cevaplanabilsin.
    """
    import datetime as _dt
    bugun = bugun or _dt.date.today()
    ceyrek = BILDIRIM_AYLARI.get(bugun.month)
    if ceyrek is None:
        return False, (f"{bugun.month}. ay bildirim ayi degil "
                       f"(bildirim aylari: {sorted(BILDIRIM_AYLARI)})")
    return True, f"{ceyrek} aylik donem bildirimleri"


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
    # Donem etiketi artik CEYREKLIK. Bos birakilirsa
    # `bilanco_ag.ceyrek_etiketi` ile veriden turetiliyor.
    a.add_argument("--donem", default="")
    # CEYREKLIK: 2 -> 1.
    #
    # `ceyrek` kac ceyregin TOPLANACAGI. 2 iken alti aylik kumulatif
    # (Q1+Q2) hesaplaniyordu; 1 ile yalnizca en son ceyrek.
    #
    # Ikinci ceyregin kendi performansi kumulatifte GORUNMUYOR: guclu
    # bir Q1, zayif bir Q2'yi ortuyor. Ceyreklik hesap ayrica yillik
    # karsilastirmayi keskinlestiriyor -- Q2'ye karsi gecen yil Q2,
    # alti aya karsi alti ay degil.
    a.add_argument("--ceyrek", type=int, default=1)
    a.add_argument("--sinir", type=int, help="sektör başına en fazla şirket")
    a.add_argument("--kuru-calis", action="store_true", help="dosyaya yazma")
    a.add_argument("--zorla", action="store_true",
                   help="bildirim ayı olmasa da çalıştır")
    n = a.parse_args()

    if not n.sektor and not n.hepsi:
        a.error("--sektor ya da --hepsi gerekli")

    # TAKVIM KAPISI. `--zorla` ile atlanabiliyor: elle calistirmak
    # her zaman mumkun olmali, otomatik kosuda ise bosuna cekmemeli.
    if not n.zorla:
        acik, sebep = donem_acik()
        if not acik:
            print(f"bilanço hattı ATLANDI -- {sebep}")
            print("elle çalıştırmak için: --zorla")
            return 0
        print(f"bildirim dönemi: {sebep}")

    if n.hepsi:
        sektorler = sorted({v["sektor_tr"] for v in _defter().values()
                            if v.get("sektor_tr")})
    else:
        sektorler = [n.sektor]

    cikti = {}
    for s in sektorler:
        # DONEM ETIKETI VERIDEN TURETILIYOR, ELLE YAZILMIYOR.
        #
        # Once `--donem 2026/6` varsayilaniyla geliyordu ve KASIM'da
        # dokuz aylik tablolar ciktiginda hala "2026/6" yazacakti:
        # rakamlar yeni, etiket eski. Sessiz bir yanlis -- sayfa
        # uretilir, dogru gorunur, yalnizca donemi yanlistir.
        #
        # Artik kaynaktan okunuyor; elle vermek yalnizca `--donem` ile
        # mumkun ve o da bilerek yapilan bir sey.
        etiket = n.donem
        if not etiket:
            import bilanco_ag as _b                   # noqa: PLC0415
            ilk = sektordeki(s)
            son = _b.son_donem(ilk[0][0]) if ilk else None
            etiket = _b.ceyrek_etiketi(*son) if son else ""
            if not etiket:
                print(f"  {s}: donem belirlenemedi, atlandi")
                continue
        cikti[s] = sektor_isle(s, etiket, n.ceyrek, n.sinir)

    if n.kuru_calis:
        print("\n(kuru çalışma -- dosyaya yazılmadı)")
        return 0
    HEDEF.write_text(json.dumps(cikti, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"\n{HEDEF} yazıldı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
