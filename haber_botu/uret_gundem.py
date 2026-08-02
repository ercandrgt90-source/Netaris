"""Gundem akisi -- resmi kurum duyurulari, otomatik.

    RSS beslemeleri -> tekille -> konuya gore ayir -> site verisi

NE YAPAR, NE YAPMAZ
-------------------
YAPAR : Fed, ECB, SEC ve EIA duyurularini toplar, konuya gore siniflandirir,
        tarihe gore sirlar ve siteye yazar. Her baslik KAYNAGA baglanir.

YAPMAZ: **Basliklari cevirmez ve yorumlamaz.** Kaynak basligi orijinal
        dilinde aktarilir. Ceviri ve yorum icin dil modeli gerekir; model
        olmadan "yaklasik" bir Turkce baslik uretmek, resmi bir kurumun
        aciklamasini yanlis aktarmak olur.

Model devreye girdiginde ceviri + baglam katmani buraya eklenir. Besleme
yapisi ve site tarafi degismeyecek sekilde kuruldu.

Kullanim:
    python uret_gundem.py
    python uret_gundem.py --yayinla
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "kaynak"))
sys.path.insert(0, str(_KOK / "analiz"))

sys.path.insert(0, str(_KOK))

import besleme  # noqa: E402
import beyin  # noqa: E402
import ceviri  # noqa: E402
import foto  # noqa: E402
import gundem_yorum  # noqa: E402

HEDEF = _KOK.parent / "site" / "icerik" / "gundem.json"

#: Ana sayfada ve gundem sayfasinda gosterilecek en fazla oge
SINIR = 40


def main() -> int:
    a = argparse.ArgumentParser(description="Resmi duyuru akisi")
    a.add_argument("--yayinla", action="store_true",
                   help="site icerigine yaz (yoksa yalnizca ekrana basar)")
    a.add_argument("--sinir", type=int, default=SINIR)
    args = a.parse_args()

    print("=" * 70)
    print("GUNDEM AKISI -- resmi kurum duyurulari")
    print("=" * 70)

    haberler = besleme.cek()
    if not haberler:
        print("Hicbir besleme okunamadi.")
        return 1

    # Kurum ve konu dagilimi
    kurumlar: dict[str, int] = {}
    konular: dict[str, int] = {}
    for h in haberler:
        kurumlar[h.kurum] = kurumlar.get(h.kurum, 0) + 1
        konular[h.konu] = konular.get(h.konu, 0) + 1

    print(f"\n{len(haberler)} duyuru, {len(kurumlar)} kurum\n")
    for kurum, n in sorted(kurumlar.items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {kurum}")
    print()
    for konu, n in sorted(konular.items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {konu}")

    tarihsiz = sum(1 for h in haberler if not h.tarih)
    if tarihsiz:
        print(f"\n  {tarihsiz} duyurunun tarihi cozulemedi -- bugun YAZILMADI,"
              f"\n  tarihsiz olarak isaretlendi")

    print("\nEN YENI 8")
    for h in haberler[:8]:
        print(f"  [{h.konu:<18}] {h.tarih or '     ?    '}  {h.baslik[:78]}")

    if not args.yayinla:
        print("\nDURUM: yalnizca ekrana basildi (--yayinla ile siteye yazilir)")
        return 0

    # --- Fotograf havuzu ---
    print("\nFOTOGRAF HAVUZU")
    foto_kayit = foto.hazirla([h.konu for h in haberler[:args.sinir]])

    # --- Ceviri ve baglam ---
    print("\nCEVIRI VE BAGLAM")
    cevirmen = ceviri.Cevirmen()
    kayitlar = []
    yorumlanan = 0

    for h in haberler[:args.sinir]:
        tr = cevirmen.cevir(h.baslik)
        cevrildi = cevirmen.ceviri_yapildi(h.baslik, tr)
        baglam = gundem_yorum.siniflandir(h.baslik, h.konu)
        if baglam.yorumlanir:
            yorumlanan += 1

        # Fotograf: konudan, haberin adresine gore belirlenimci secim.
        # Ayni haber her zaman ayni fotografi alir.
        f = foto_kayit.sec(h.konu, h.adres)

        kayitlar.append({
            "baslik": tr,
            "baslik_kaynak": h.baslik,
            "cevrildi": cevrildi,
            "adres": h.adres,
            "kurum": h.kurum,
            "kurum_tam": h.kurum_tam,
            "konu": h.konu,
            "tarih": h.tarih,
            "tarih_gorunur": h.tarih_gorunur,
            "yorumlanir": baglam.yorumlanir,
            "neden_onemli": baglam.neden_onemli,
            "kanallar": list(baglam.kanallar),
            "foto": f.dosya if f else "",
            # CC BY atfi zorunlu kilar -- gorselin altinda basilir
            "foto_atif": f.kisa_atif if f else "",
        })

    cevirmen.kaydet()
    print(f"  {cevirmen.ozet()}")
    print(f"  {yorumlanan} haber yoruma acik, "
          f"{len(kayitlar) - yorumlanan} rutin (yalnizca cevrildi)")

    cevrilemeyen = sum(1 for k in kayitlar if not k["cevrildi"])
    if cevrilemeyen:
        print(f"  {cevrilemeyen} baslik CEVRILEMEDI -- kaynak dilinde birakildi")

    veri = {
        "guncelleme": besleme.bugun(),
        "kaynaklar": sorted(kurumlar),
        "ceviri_notu": (
            "Başlıklar makine çevirisiyle Türkçeleştirilmiştir. "
            "Özgün başlık ve kaynak bağlantısı her maddede yer alır."
        ),
        "yorumlanan": yorumlanan,
        "haberler": kayitlar,
        "sinir_notu": gundem_yorum.SINIR_NOTU,
    }
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(json.dumps(veri, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\nsite verisi: {HEDEF.relative_to(_KOK.parent)}")
    print(f"{len(veri['haberler'])} duyuru yazildi")

    # Depoya yaz -- JSON dosyasi her calistirmada uzerine yaziliyor,
    # depo ise birikiyor. Bir duyuruyu ilk ne zaman gordugumuz orada kalir.
    # Yayin yolu insa aninda belirleniyor ama kurali burada bilinir:
    # yorumlanan her habere sayfa uretilir. Depoya bunu simdi yaziyoruz ki
    # "kac haber yayimlandi" sorusu dogru cevaplanabilsin.
    for k in kayitlar:
        if k["yorumlanir"]:
            k["yol"] = "/haber/"

    with beyin.baglan() as b:
        with beyin.calisma_kaydi(b, "gundem") as ozet:
            yeni, tekrar = beyin.haber_yaz(b, kayitlar)
            n_ceviri = beyin.ceviri_yaz(b, cevirmen.onbellek, "MyMemory")
            ozet.update({"yeni": yeni, "tekrar": tekrar,
                         "yorumlanan": yorumlanan, "ceviri": n_ceviri})
    print(f"depo: {yeni} yeni haber, {tekrar} daha once gorulmus, "
          f"{n_ceviri} ceviri")
    return 0


if __name__ == "__main__":
    sys.exit(main())
