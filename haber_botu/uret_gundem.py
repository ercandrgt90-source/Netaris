"""Gundem akisi -- resmi kurum duyurulari, otomatik.

    RSS beslemeleri -> tekille -> konuya gore ayir -> site verisi

NE YAPAR
--------
TCMB, Fed, ECB, SEC ve EIA duyurularini toplar; yabanci olanlari Turkce'ye
cevirir, konuya gore siniflandirir, fotograf esler, tarihe gore sirlar ve
siteye yazar. Ozgun baslik her maddede saklanir.

DILE GORE AYRIM
---------------
TCMB beslemeleri zaten Turkce -- ceviri katmanina hic ugramazlar. Bu bir
eniyileme degil, dogruluk meselesi: Turkce bir basligi Ingilizce sanan bir
ceviri motoru metni bozar.

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

    # --- Resmi kaynaklara ayrilmis kontenjan ---
    #
    # Ticari akis gunde 100+ baslik uretiyor, TCMB gunde iki uc duyuru.
    # Saf tarih siralamasinda resmi kaynak PENCERENIN TAMAMEN DISINDA
    # kaliyor: olculdu, 40 ogenin 40'i ticariydi, TCMB ve Fed hic yoktu.
    #
    # Sitenin omurgasi resmi veri; ticari akis onun uzerine geliyor. Bu
    # yuzden resmi kaynaklara sabit kontenjan ayriliyor, kalani ticari
    # dolduruyor. Ikisi de kendi icinde tarihe gore sirali.
    resmi = [h for h in haberler if not h.ticari]
    ticari = [h for h in haberler if h.ticari]
    resmi_kota = min(len(resmi), max(1, args.sinir // 3))
    secili = resmi[:resmi_kota] + ticari[:args.sinir - resmi_kota]
    secili.sort(key=lambda h: h.tarih or "0000-00-00", reverse=True)
    haberler = secili
    print(f"\n  secim: {resmi_kota} resmi + {len(secili) - resmi_kota} ticari")

    # --- Fotograf havuzu ---
    print("\nFOTOGRAF HAVUZU")
    foto_kayit = foto.hazirla([h.konu for h in haberler])

    # --- Ceviri ve baglam ---
    print("\nCEVIRI VE BAGLAM")
    cevirmen = ceviri.Cevirmen()

    # Sozluge yeni terim eklendiginde onbellekteki eski ceviriler
    # kendiliginden duzelmez -- onbellekten geldikleri icin duzeltme
    # katmani hic calismaz. Her calistirmada bastan geciriliyor; kota
    # harcamaz cunku yeniden ceviri yapilmiyor.
    tazelenen = ceviri.onbellek_tazele(cevirmen.onbellek)
    if tazelenen:
        print(f"  {tazelenen} eski ceviri sozluge gore duzeltildi")

    kayitlar = []
    yorumlanan = 0

    for h in haberler:
        # TCMB zaten Turkce yayimliyor. Bu basligi ceviri motoruna vermek
        # iki sekilde zarar verir: motor onu Ingilizce sanip metni bozar
        # ("Kurul" -> "Board"), ve bosuna kota harcar.
        if h.dil == "tr":
            tr, cevrildi = h.baslik, False
        else:
            tr = cevirmen.cevir(h.baslik)
            cevrildi = cevirmen.ceviri_yapildi(h.baslik, tr)
        # Baslik ORIJINALIYLE siniflandirilir, cevirisiyle degil: makine
        # cevirisi "policy rate"i "politika orani" yapabilir ve isaret
        # eslesmez. Kurum bilgisi yerli/yabanci baglam ayrimi icin.
        baglam = gundem_yorum.siniflandir(h.baslik, h.konu, h.kurum, h.ticari)
        if baglam.yorumlanir:
            yorumlanan += 1

        # Fotograf: konudan, haberin adresine gore belirlenimci secim.
        # Ayni haber her zaman ayni fotografi alir.
        f = foto_kayit.sec(h.konu, h.adres)

        kayitlar.append({
            "baslik": tr,
            "baslik_kaynak": h.baslik,
            # Kaynagin KENDI ozeti. Bunu toplayip sayfaya hic tasimiyorduk:
            # her haber sayfasinda o habere dair TEK ozgul icerik buydu ve
            # cope gidiyordu. Kisa alinti + kunye + baglanti, RSS'in
            # zaten davet ettigi kullanim; tam metin alinmiyor.
            "ozet": h.ozet[:320],
            "cevrildi": cevrildi,
            "dil": h.dil,
            # Sayfada kunye basilacak mi -- ticari kaynakta ZORUNLU
            "ticari": h.ticari,
            # Ana sayfadaki Türkiye / Dünya sekmesi
            "bolge": besleme.bolge_bul(h.baslik, h.dil),
            "adres": h.adres,
            "kurum": h.kurum,
            "kurum_tam": h.kurum_tam,
            "konu": h.konu,
            "tarih": h.tarih,
            "tarih_gorunur": h.tarih_gorunur,
            "yorumlanir": baglam.yorumlanir,
            "neden_onemli": baglam.neden_onemli,
            "kanallar": list(baglam.kanallar),
            "kanal_basligi": baglam.kanal_basligi,
            "foto": f.dosya if f else "",
            # CC BY atfi zorunlu kilar -- gorselin altinda basilir
            "foto_atif": f.kisa_atif if f else "",
        })

    cevirmen.kaydet()
    print(f"  {cevirmen.ozet()}")
    print(f"  {yorumlanan} haber yoruma acik, "
          f"{len(kayitlar) - yorumlanan} rutin (yalnizca cevrildi)")

    # Turkce kaynaklari "cevrilemedi" diye saymak yanlis alarm olurdu --
    # onlar cevrilmesi GEREKMEYEN basliklar.
    ozgun_turkce = sum(1 for k in kayitlar if k["dil"] == "tr")
    cevrilemeyen = sum(1 for k in kayitlar
                       if k["dil"] != "tr" and not k["cevrildi"])
    print(f"  {ozgun_turkce} baslik zaten Turkce -- ceviriye girmedi")
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
    # Depoya "yayimlandi" bilgisini yazmak icin: yorumlanan her habere
    # sayfa uretilir, bu kural burada biliniyor. Gercek adres insa aninda
    # olusuyor; burada yalnizca yayimlanacagini isaretliyoruz.
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
