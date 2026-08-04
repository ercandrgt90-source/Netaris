"""Depodaki TUM haberleri varlik indeksine isler (geriye donuk tarama).

Gunluk isleme site kurulurken oluyor (`site/insa.py`); bu betik indeks
ILK KURULDUGUNDA ya da varlik listesi genisletildiginde calistirilir:
yeni kalip eklendiginde eski haberler de o varliga baglanmalidir.

    python haber_botu/uret_varlik.py

Yeniden calistirmak zararsiz: `INSERT OR IGNORE` kullaniliyor, mevcut
baglar bozulmuyor, yalnizca eksik olanlar ekleniyor.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "analiz"))

import beyin                       # noqa: E402
import graf_tohum                  # noqa: E402
import varlik                      # noqa: E402


def main() -> int:
    # Kalip kodlarinin grafta karsiligi var mi. Bir kod degistirilirse
    # kalip sessizce hicbir seye baglanmaz -- bu kontrol o sessizligi
    # bozuyor ve indeks bozuk yazilmadan once duruyoruz.
    kayip = varlik.dogrula()
    if kayip:
        print("HATA: grafta karsiligi olmayan kalip kodlari:", ", ".join(kayip))
        return 1

    with beyin.baglan() as b:
        # Graf ONCE tohumlaniyor: yeni bir varlik eklendiginde kalibi de
        # ayni turda ekleniyor, ama depoya yazilmamis bir koda bag
        # yazilamaz. Tohum yeniden calistirmaya dayanikli.
        nv, ng = graf_tohum.tohumla(b)
        print(f"graf: {nv} varlik, {ng} bag guncel")
        varlik.sema_kur(b)

        # INDEKS SIFIRDAN KURULUYOR.
        #
        # `INSERT OR IGNORE` yalnizca ekler; bir kalip DUZELTILDIGINDE
        # eski yanlis bag yerinde kalirdi. Olculen ornek: "Altin ne zaman
        # yukselecek? DEV BANKA..." haberi Bankacilik sektorune baglanmisti;
        # kalip duzeltildikten sonra da bagli kalacakti.
        #
        # Silmek guvenli, cunku indeks tamamen turetilmis: girdisi haber
        # basliklari ve kalip listesi, ikisi de duruyor.
        eski = b.execute("DELETE FROM haber_varlik").rowcount
        if eski:
            print(f"indeks sifirlandi: {eski} eski bag silindi")

        satirlar = b.execute(
            "SELECT adres, baslik_tr, baslik_kaynak, kurum FROM haber"
        ).fetchall()

        yeni_bag = 0
        bagli = 0
        for s in satirlar:
            adres, tr, kaynak, kurum = s[0], s[1], s[2], s[3]
            # Turkce baslik oncelikli: kaliplarin cogu Turkce yazili.
            # Ikisi de varsa ikisine birden bakiyoruz -- "Fed" Ingilizce
            # baslikta, "Merkez Bankasi" Turkcesinde geciyor olabilir.
            # Kurum, Turkiye baglami icin gerekli.
            vs = varlik.bul(b, tr or "", kaynak or "", kurum=kurum or "")
            if not vs:
                continue
            bagli += 1
            yeni_bag += varlik.yaz(b, adres, vs)

        toplam = b.execute("SELECT COUNT(*) FROM haber_varlik").fetchone()[0]
        dagilim = b.execute(
            "SELECT v.ad, COUNT(*) n FROM haber_varlik hv"
            " JOIN varlik v ON v.kod = hv.varlik_kimlik"
            " GROUP BY v.kod ORDER BY n DESC LIMIT 12").fetchall()

    print(f"{len(satirlar)} haber tarandi")
    print(f"{bagli} haberde varlik bulundu "
          f"({len(satirlar) - bagli} haber hicbir varliga baglanmadi)")
    print(f"{yeni_bag} yeni bag yazildi, depoda toplam {toplam} bag\n")
    print("en cok gecen varliklar:")
    for ad, n in dagilim:
        print(f"  {ad:<28} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
