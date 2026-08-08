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
import makro          # noqa: E402
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
    # GOZLEMLER HABERDEN BAGIMSIZ YAZILIYOR.
    #
    # Bu hat simdiye kadar SADECE haber uretiyordu. Sonuc: ABD makro
    # serilerinin (PAYEMS, CPIAUCSL...) degerleri hicbir yerde yapisal
    # olarak durmuyordu -- yalnizca haber basliginin icinde metin
    # olarak. Olculdu: "Yaklaşan veriler" bolumu ABD verilerinde
    # "son aciklanan deger"i bulamadi, butun beklenti kutulari bos
    # kaldi.
    #
    # HABER TEKILLEMESINDEN ONCE yaziliyor: bir gozlemin haberi zaten
    # varsa yeni haber uretilmiyor ama GOZLEM yine de depoya girmeli.
    # Ilk yazimda yalnizca `yeni` listesi yaziliyordu ve tam bu yuzden
    # hicbir gozlem kaydedilmedi -- butun haberler zaten mevcuttu.
    #
    # `gosterge_yaz` INSERT OR IGNORE kullaniyor: ayni kod+tarih ikinci
    # kez gelirse sessizce atlaniyor, yani her calistirmada guvenle
    # cagrilabilir.
    # OKUNAN DEGER YAZILIYOR, HAM SERI DEGERI DEGIL.
    #
    # Ilk yazimda `a.deger` (ham seri) yaziliyordu ve olculdu:
    # CPIAUCSL icin depoya "332,568" ve birim "%" girdi. O sayi TUFE
    # ENDEKSININ SEVIYESI; sayfada "%332,57" diye gorunurdu. Serinin
    # `sunum` alani zaten neyin gosterilecegini soyluyor (seviye /
    # aylik degisim / yillik degisim) ve `okunan` onu uyguluyor.
    #
    # Bu, EVDS formulu `DUZEY`e sabitlendiginde "TÜFE: %132,31"
    # yazilmasina yol acan hatanin aynisi -- ayni tuzak, ikinci kez.
    with beyin.baglan() as b:
        n_gozlem = beyin.gosterge_yaz(b, [{
            "kod": a.kod, "tarih": a.tarih, "deger_ham": a.okunan,
            "birim": a.birim, "ad": a.ad,
            "kaynak": "EVDS" if a.kod.startswith("TP.") else "FRED",
        } for a in aciklamalar])
    if n_gozlem:
        print(f"  {n_gozlem} gozlem depoya yazildi")

    # SERI GECMISI DE YAZILIYOR, yalnizca son gozlem degil.
    #
    # Olculdu: 269 haber sayfasinin 37'sinde hicbir veri bolumu yoktu.
    # Sebep zincirin sonundaydi -- panel bir gostergeyi basmak icin EN
    # AZ IKI gozlem istiyor (degisimi gosterebilmek icin) ve bu hat
    # yalnizca EN YENI gozlemi yaziyordu. CPIAUCSL depoda tek satirdi.
    #
    # `makro.fred` ayni ucu kullanarak gecmisi zaten cekebiliyor;
    # burada yeniden yazmak yerine o kullaniliyor. `gosterge_yaz`
    # INSERT OR IGNORE oldugu icin tekrar calistirmak zararsiz.
    gecmis_kod = {a.kod for a in aciklamalar if not a.kod.startswith("TP.")}
    n_gecmis = 0
    if gecmis_kod:
        seriler = {s[0]: s for s in takvim.SERILER}
        with beyin.baglan() as b:
            var_gozlem = {
                (k, tr) for k, tr in b.execute(
                    "SELECT kod, tarih FROM gosterge WHERE kaynak='FRED'")}
            kalemler = []
            for kod in sorted(gecmis_kod):
                s = seriler.get(kod)
                if not s:
                    continue
                try:
                    seri = makro.fred(kod, son_n=26)
                except Exception:
                    continue
                if not seri or not getattr(seri, "gozlemler", None):
                    continue
                # SUNUM UYGULANIYOR: ham seri degeri degil, okura
                # gosterilen buyukluk yaziliyor. Endeks seviyesini "%"
                # birimiyle yazmak daha once "%332,57" hatasini
                # uretmisti.
                sunum = s[6]
                g = list(seri.gozlemler)
                for i, x in enumerate(g):
                    if sunum == "yillik":
                        if i < 12:
                            continue
                        onceki = g[i - 12].deger
                        if not onceki:
                            continue
                        deger = (x.deger - onceki) / onceki * 100
                    elif sunum == "degisim":
                        if i < 1:
                            continue
                        deger = x.deger - g[i - 1].deger
                    else:
                        deger = x.deger
                    if (kod, x.tarih) in var_gozlem:
                        continue
                    kalemler.append({
                        "kod": kod, "tarih": x.tarih, "deger_ham": deger,
                        "birim": s[2], "ad": s[1], "kaynak": "FRED"})
            if kalemler:
                n_gecmis = beyin.gosterge_yaz(b, kalemler)
    if n_gecmis:
        print(f"  {n_gecmis} gecmis gozlem depoya yazildi")

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
            ozet.update({"yeni": n_yeni, "tekrar": n_tekrar,
                         "gozlem": n_gozlem})
    print(f"\ndepo: {n_yeni} yeni, {n_tekrar} tekrar, {n_gozlem} gozlem")
    print(f"gundem.json: {len(veri['haberler'])} haber")
    return 0


if __name__ == "__main__":
    sys.exit(main())
