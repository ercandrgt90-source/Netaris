# -*- coding: utf-8 -*-
"""YAYINDAKI BILANCO SAYFASI SAGLAM OLMALI -- CIRCIRLI KORUMA.

OLCUT TEK YERDE: `haber_botu/bilanco_denetim.onarim_gereken`.
Onarim yolu (`bilanco_tazele --onarim`) AYNI islevi kullaniyor, yani
"hangi sayfa bozuk" sorusunun tek bir cevabi var. Iki yerde ayri
yazilsaydi biri degisip oteki unutulurdu -- bu depoda tam o sinif
kusur yayina cikti (asagida).

IKI KUSUR DENETLENIYOR, IKISI DE OLCULDU (2026-10-13)
-----------------------------------------------------
1. SAYFADA IKI AYRI DONEM. Seviye tablosu `donem_getir`den, oranlar
   sektor ozetinden geliyordu ve ara donemin kac ceyrekten olustugu
   IKI YERDE ayri yaziliydi (ozet 1, sayfa 2). Ikisini de kimse
   acikca vermiyordu, yani URETIMDE ikisi birden calisiyordu.

   Dogal bir deney kanitladi -- eski KUMULATIF etiketli sayfalar
   (`2026/6`) iki yolun da 2 kullandigi donemde uretilmisti:

       donem      n     seviyeden hesaplanan ile yazili marj farki
       -------  ----    ---------------------------------------
       2026/6     14    medyan 0,03 puan   (en kotu 0,43)
       2026 1.C   43    medyan 2,69 puan   (en kotu 48,03)
       2026 2.C  122    medyan 3,10 puan   (en kotu 51,59)

   Varsayilanla UYUSAN bicim tutarli, uyusmayan degil. En kotu:
   `2026-2-ceyrek-bulgs.md` -- seviyeden %45,7, yazili %97,3.
   Tek kaynak artik `bilanco_ag.VARSAYILAN_CEYREK`.

2. KAPSAM DISI OKUMA KILAVUZU. Kilavuz yalnizca `sektor_tr`ye
   bakiyordu; futbol kuluplerinin sayfasina telekom kilavuzu,
   gayrimenkul gelistiricisinin sayfasina GYO kilavuzu yaziliyordu.
   Tek kaynak `analiz/sektor_okuma.ALT_KAPSAM`.

CIRCIR -- SAYI DEGIL AD TUTULUYOR
---------------------------------
Duzeltmeden once uretilmis sayfalar `MIRAS` dosyasinda ADLARIYLA
sayili. Listede OLMAYAN her sayfa saglam olmak ZORUNDA. Sayi
tutulsaydi, bir eski sayfa duzelirken bir yeni sayfa bozuldugunda
toplam ayni kalir ve koruma KORLESIRDI.

Liste yalnizca kisalir: `bilanco_tazele --onarim` her kosuda bir
dilim onariyor ve bu sinama hangilerinin cikarilabilecegini YAZIYOR.
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK.parent / "haber_botu"))

import bilanco_denetim as bd                       # noqa: E402

ICERIK = _KOK / "icerik" / "analizler"
DEFTER = _KOK.parent / "haber_botu" / "kaynak" / "sirketler.json"
#: Duzeltmeden ONCE uretilmis, bozuklugu bilinen sayfalar.
MIRAS = _KOK / "bilanco_miras_bozuk.json"

_KOD = "kod:"


def _defter() -> dict:
    if not DEFTER.is_file():
        return {}
    return json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]


def _kod(metin: str) -> str:
    for satir in metin.splitlines()[:20]:
        if satir.startswith(_KOD):
            return satir[len(_KOD):].strip().upper()
    return ""


def budar(duzelen: list[str]) -> None:
    """Onarilmis sayfalari MIRAS listesinden cikarir.

    CIRCIR GERCEKTEN SIKISMALI. Liste budanmazsa onarilmis sayfalar
    listede kalir ve o sayfalar bir daha HIC denetlenmez -- 204
    sayfa kalici olarak korumasiz kalirdi. "Koruma var ama hicbir
    seyi korumuyor" bu depoda gorulmus bir durum.
    """
    if not duzelen or not MIRAS.is_file():
        return
    d = json.loads(MIRAS.read_text(encoding="utf-8"))
    kalan = [a for a in (d.get("sayfalar") or []) if a not in set(duzelen)]
    d["sayfalar"] = kalan
    d["budandi"] = True
    MIRAS.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"  MIRAS LISTESI BUDANDI: {len(duzelen)} sayfa çıkarıldı, "
          f"{len(kalan)} kaldı")


def main() -> int:
    a = argparse.ArgumentParser(description="bilanço sayfası sağlam mı")
    a.add_argument("--budar", action="store_true",
                   help="onarılmış sayfaları miras listesinden çıkarır")
    n = a.parse_args()
    if not ICERIK.is_dir():
        print(f"DUSTU  içerik dizini yok: {ICERIK}")
        return 1
    miras = set()
    if MIRAS.is_file():
        miras = set(json.loads(MIRAS.read_text(encoding="utf-8"))
                    .get("sayfalar") or [])
    # DEFTER YOKSA KORUMA KORLESIR -- SESSIZCE GECMEK YOK.
    #
    # Kilavuz kapsami denetimi alt sektoru DEFTERDEN okuyor. Defter
    # okunamazsa o denetim hicbir sey yapmaz ve sinama YESIL doner:
    # tam olarak bu depoda ucuncu kez goruldugu kusur sinifi (cikti
    # yokken atlayip gecen 43 sinama).
    defter = _defter()
    if not defter:
        print(f"DUSTU  defter okunamadı: {DEFTER}")
        print("  Kılavuz kapsamı denetimi onsuz çalışmaz; sessizce")
        print("  geçmek korumayı körleştirirdi.")
        return 1

    bakilan = saglam = miras_bozuk = 0
    yeni_bozuk: list[tuple[str, list[str]]] = []
    duzelen: list[str] = []
    for p in sorted(ICERIK.glob("*.md")):
        metin = io.open(p, encoding="utf-8").read()
        if not bd.bilanco_sayfasi(metin):
            continue
        bakilan += 1
        sebep = bd.onarim_gereken(metin, defter.get(_kod(metin)))
        if not sebep:
            saglam += 1
            if p.name in miras:
                duzelen.append(p.name)
            continue
        if p.name in miras:
            miras_bozuk += 1
        else:
            yeni_bozuk.append((p.name, sebep))

    print(f"  bilanço sayfası        : {bakilan}")
    print(f"  sağlam                 : {saglam}")
    print(f"  miras (bilinen, eski)  : {miras_bozuk}")
    if duzelen:
        print(f"  MIRAS LISTESINDEN ÇIKARILABILIR: {len(duzelen)} sayfa")
        print(f"    (ilk üç: {', '.join(duzelen[:3])})")
        if n.budar:
            budar(duzelen)
    if yeni_bozuk:
        print(f"\nDUSTU  {len(yeni_bozuk)} sayfa bozuk ve miras listesinde "
              f"DEĞİL")
        for ad, sebep in yeni_bozuk[:10]:
            print(f"    {ad}")
            print(f"      {', '.join(sebep)}")
        if len(yeni_bozuk) > 10:
            print(f"    ... ve {len(yeni_bozuk) - 10} sayfa daha")
        print("\n  Tek kaynaklar: bilanco_ag.VARSAYILAN_CEYREK ve")
        print("  analiz/sektor_okuma.ALT_KAPSAM")
        return 1
    print("\nGECTI  miras dışındaki her bilanço sayfası sağlam")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
