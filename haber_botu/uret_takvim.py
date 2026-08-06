"""Veri aciklamalarini habere cevirir ve gundeme katar.

    FRED serisi -> yeni gozlem -> haber kaydi -> gundem.json

`uret_gundem.py`den SONRA calisir: o dosyayi okuyup ustune ekliyor.
Ayri bir hat olmasinin sebebi, kaynak turunun farkli olmasi -- besleme
RSS okur, bu hat VERI okur. Bir RSS coktugunde digeri calismali.

Yeniden calistirmak zararsiz: ayni gozlem icin ikinci haber
uretilmiyor (depoda `adres` benzersiz).
"""

from __future__ import annotations

import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz")]

import beyin          # noqa: E402
import besleme        # noqa: E402
import foto           # noqa: E402
import takvim         # noqa: E402

HEDEF = _KOK.parent / "site" / "icerik" / "gundem.json"

#: Veri aciklamalarinin kurum adi. Gercek ve dogrulanabilir: rakam
#: FRED'den geliyor, biz yorumlamiyoruz.
KURUM = "FRED"
KURUM_TAM = "FRED · St. Louis Fed"


def main() -> int:
    if not HEDEF.exists():
        print(f"{HEDEF} yok -- once uret_gundem.py calismali.")
        return 1
    veri = json.loads(HEDEF.read_text(encoding="utf-8"))
    bugun = veri.get("guncelleme") or besleme.bugun()

    print("VERI ACIKLAMALARI -- Turkiye (EVDS)")
    aciklamalar = takvim.cek_yerli(bugun)
    print("\nVERI ACIKLAMALARI -- ABD (FRED)")
    aciklamalar += takvim.cek(bugun)
    if not aciklamalar:
        print("  taze aciklama yok")
        return 0

    # Depoda olanlari ele: ayni gozlem icin ikinci haber uretilmez.
    with beyin.baglan() as b:
        var = {r[0] for r in b.execute(
            "SELECT adres FROM haber WHERE adres LIKE 'netaris:veri/%'")}
    yeni = [a for a in aciklamalar if a.adres not in var]
    print(f"  {len(aciklamalar)} taze gozlem, {len(yeni)} yeni haber")
    if not yeni:
        return 0

    # Fotograf havuzu: konu bazli, mevcut defterden. Indirme YOK --
    # bu hat aga yalnizca FRED icin cikiyor.
    kayit = foto.Kayit()

    kayitlar = []
    for a in sorted(yeni, key=lambda x: -x.onem):
        bas = takvim.baslik(a)
        f = kayit.sec(a.konu, a.adres)
        kayitlar.append({
            "baslik": bas,
            "baslik_kaynak": bas,
            "ozet": takvim.ozet(a),
            "cevrildi": False,
            "dil": "tr",
            # Ticari DEGIL: veri kamuya acik, kunye zorunlulugu yok.
            # Kaynak yine de sayfada yaziyor.
            "ticari": False,
            # Yerli seri -> TR sekmesi; Turkiye paneli ve duyarlilik
            # tablosu da bu haberlerde basiliyor.
            "bolge": "TR" if a.kod.startswith("TP.") else "DUNYA",
            "adres": a.adres,
            "kurum": "TCMB" if a.kod.startswith("TP.") else KURUM,
            "kurum_tam": ("TCMB EVDS" if a.kod.startswith("TP.")
                          else KURUM_TAM),
            "konu": a.konu,
            # HABERIN TARIHI = YAYIN GUNU, gozlem donemi DEGIL.
            #
            # Seri "2026-07-01" satirini temmuz verisi olarak tutuyor
            # ama o veri bugun aciklaniyor. Gozlem tarihini haber tarihi
            # yapinca sayfa "bu haber 34 gun once yayimlandi" uyarisi
            # basiyordu -- oysa haber bugunun haberi. Donem bilgisi
            # baslikta ve ozette zaten yaziyor.
            "tarih": bugun[:10],
            "tarih_gorunur": takvim.tarih_tr(bugun),
            #: Gozlem donemi ayrica saklaniyor (sayfada kullanilmiyor,
            #: arsivde hangi donemin verisi oldugunu bilmek icin).
            "donem": a.tarih[:10],
            # Veri aciklamasi TANIMI GEREGI yorumlanabilir: rakam,
            # onceki deger ve degisim elimizde. Besleme suzgecinden
            # gecirmeye gerek yok -- o suzgec basliktan olay CIKARMAK
            # icin, burada olayin kendisi zaten var.
            "yorumlanir": True,
            # Seriye ozgu YAPISAL gerekce. Konu tablosundan gelen genel
            # metin yerine serinin kendi tanimi yaziliyor: "Cekirdek PCE
            # Fed'in resmen tercih ettigi olcudur" cumlesi yalnizca o
            # seri icin dogru.
            "neden_onemli": (takvim.YERLI_NEDEN.get(a.kod)
                             or takvim.NEDEN.get(a.kod, "")),
            "kanallar": [],
            "kanal_basligi": "",
            "foto": f.dosya if f else "",
            "foto_atif": f.kisa_atif if f else "",
            "yol": "/haber/",
        })
        print(f"  + {bas[:70]}")

    # Gundemin BASINA ekleniyor: veri aciklamasi o gunun en taze ve en
    # onemli olayidir, listenin altinda kalmamali.
    veri["haberler"] = kayitlar + veri.get("haberler", [])
    veri["yorumlanan"] = veri.get("yorumlanan", 0) + len(kayitlar)
    HEDEF.write_text(json.dumps(veri, ensure_ascii=False, indent=2),
                     encoding="utf-8")

    with beyin.baglan() as b:
        with beyin.calisma_kaydi(b, "takvim") as ozet:
            n_yeni, n_tekrar = beyin.haber_yaz(b, kayitlar)
            ozet.update({"yeni": n_yeni, "tekrar": n_tekrar})
    print(f"\ndepo: {n_yeni} yeni, {n_tekrar} tekrar")
    print(f"gundem.json: {len(veri['haberler'])} haber")
    return 0


if __name__ == "__main__":
    sys.exit(main())
