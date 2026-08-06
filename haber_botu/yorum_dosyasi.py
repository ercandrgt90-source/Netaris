"""Editor yorumu icin haber dosyasi uretir.

NEDEN BU BICIM
--------------
Duyarlilik matrisini bos bir tablo olarak doldurmak, alan bilgisini
yanlis yerden istemek oluyor: kimse "havayolu 5 mi 4 mu" diye
dusunmuyor. Insan HABERE bakip "bu su sektoru su kanaldan vurur" diyor;
sayi o cumleden CIKIYOR, once gelmiyor.

Bu betik arsivden gercek haberleri secip her birinin altina sitenin
SU AN ne dedigini yaziyor. Editor duzeltirken sifirdan yazmiyor,
karsilastiriyor -- hem daha hizli hem daha isabetli, cunku hatayi
gormek bos sayfayi doldurmaktan kolaydir.

    python haber_botu/yorum_dosyasi.py                 # varsayilan
    python haber_botu/yorum_dosyasi.py --sayi 25
    python haber_botu/yorum_dosyasi.py --konu Jeopolitik

Cikti: YORUM-<tarih>.md  (depo kokunde)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "analiz"), str(_KOK / "kaynak")]

import beyin          # noqa: E402
import dosya          # noqa: E402
import gundem_yorum   # noqa: E402
import olay           # noqa: E402

#: Once bu konulardan orneklenir. Sirali: en cok haber gelen ve senaryo
#: acilan konular basta, cunku duzeltmenin etkisi orada en buyuk.
ONCELIK = ("Jeopolitik", "Para politikası", "Enflasyon", "Enerji",
           "Dış ticaret", "Bankacılık", "İstihdam ve ücret",
           "Konut ve kira", "Tarım ve gıda", "Turizm", "Borsa",
           "Vergi ve kamu maliyesi", "Döviz", "Altın ve emtia")

#: Konu basina en fazla kac ornek. Ayni konudan on haber gostermek
#: tekrar olur; ucu farkli acilari yakalamaya yetiyor.
KONU_BASINA = 3


def _haberler(b, konu_suzgeci: str | None) -> list[dict]:
    r = b.execute(
        "SELECT baslik_tr, baslik_kaynak, kurum, konu, tarih, sayfa_veri"
        " FROM haber WHERE sayfa_veri IS NOT NULL"
        " ORDER BY tarih DESC, ilk_gorulme DESC").fetchall()
    cikti = []
    for tr, kaynak, kurum, konu, tarih, yuk in r:
        try:
            y = json.loads(yuk)
        except (TypeError, ValueError):
            y = {}
        k = y.get("konu") or konu or ""
        if konu_suzgeci and k != konu_suzgeci:
            continue
        cikti.append({
            "baslik": tr or kaynak or "", "kaynak_baslik": kaynak or "",
            "kurum": kurum or "", "konu": k, "tarih": tarih or "",
            "ozet": (y.get("ozet") or "")[:400],
        })
    return cikti


def _sec(haberler: list[dict], sayi: int) -> list[dict]:
    """Konulara DAGITARAK secer.

    Tarihe gore ilk N alinsaydi liste tek bir gunun bir konusuyla
    dolardi: 4 Agustos'ta on tane Hurmuz haberi var. Konu basina sinir
    farkli kanallarin gorunmesini sagliyor.
    """
    kova: dict[str, list[dict]] = {}
    for h in haberler:
        kova.setdefault(h["konu"], []).append(h)
    sirali = sorted(kova, key=lambda k: (ONCELIK.index(k)
                                         if k in ONCELIK else 99, k))
    cikti: list[dict] = []
    for tur in range(KONU_BASINA):
        for k in sirali:
            if len(cikti) >= sayi:
                return cikti
            if len(kova[k]) > tur:
                cikti.append(kova[k][tur])
    return cikti


def _mevcut(h: dict) -> dict:
    """Sitenin su an o haber icin ne dedigi."""
    konu = h["konu"]
    baglam = gundem_yorum.siniflandir(
        h["kaynak_baslik"] or h["baslik"], konu, h["kurum"], True)
    o = olay.siniflandir(h["kaynak_baslik"] or h["baslik"], h["kurum"])
    return {
        "neden": baglam.neden_onemli,
        "kanallar": list(baglam.kanallar),
        "duyarlilik": dosya.DUYARLILIK.get(konu, ()),
        "izlenecekler": dosya.IZLENECEKLER.get(konu, ()),
        "siddet": o.siddet if o else 0,
        "senaryoya_acik": olay.esigi_gecti(o),
    }


BASLIK = """# Haber yorumu — editör dosyası

Aşağıda arşivden seçilmiş gerçek haberler var. Her birinin altında
**sitenin şu an ne dediği** yazılı. Sizden istediğim, o değerlendirmeyi
düzeltmeniz — sıfırdan yazmanız değil.

## Nasıl doldurulur

Her haberin altındaki **`### Sizin yorumunuz`** bölümünü doldurun.
Boş bıraktığınız haberi atlarım.

    Kim etkilenir:  Havayolu (yakıt gideri) | Petrokimya (girdi) | ...
    Ne izlenmeli:   Brent | Cari denge | Navlun endeksi
    Not:            Serbest metin — yanlış olan neydi, neden.

`Kim etkilenir` satırında sektörü ve **parantez içinde mekanizmayı**
yazın. Sıralama önemlidir: en çok etkilenen başta. Ben o sıralamadan
şiddet puanını çıkarırım — siz sayı yazmayın.

**Yazmayın:** yön ("yükselir/düşer") ve büyüklük ("%3 artar"). Tablo
"hangi sektör hangi kanaldan etkilenir" diyor; yönü veriden okuyoruz.

Doldurduğunuz dosyayı söyleyin, okuyup koda çeviririm.

---
"""


def _sira(yol: pathlib.Path) -> int:
    """Ayni gun icin bir sonraki bos sira numarasi."""
    n = 2
    while yol.with_name(f"{yol.stem}-{n}.md").exists():
        n += 1
    return n


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--sayi", type=int, default=18)
    a.add_argument("--konu", default=None)
    a.add_argument("--uzerine-yaz", action="store_true",
                   help="var olan dosyanin uzerine yaz (VARSAYILAN DEGIL)")
    args = a.parse_args()

    with beyin.baglan() as b:
        hepsi = _haberler(b, args.konu)
    if not hepsi:
        print("Uygun haber bulunamadi.")
        return 1
    secilen = _sec(hepsi, args.sayi)

    p = [BASLIK]
    for i, h in enumerate(secilen, 1):
        m = _mevcut(h)
        p.append(f"\n## {i}. {h['baslik']}\n")
        p.append(f"`{h['konu']}` · {h['kurum']} · {h['tarih']}"
                 + (" · **senaryoya açık**" if m["senaryoya_acik"] else "")
                 + f" · olay şiddeti {m['siddet']}\n")
        if h["ozet"]:
            p.append(f"> {h['ozet']}\n")

        p.append("**Sitenin şu anki değerlendirmesi**\n")
        p.append(f"- *Neden önemli:* {m['neden'] or '— (yok)'}")
        if m["duyarlilik"]:
            kim = " | ".join(f"{ad} ({neden})" for ad, _, neden in m["duyarlilik"])
        else:
            kim = "— (bu konuda tablo yok)"
        p.append(f"- *Kim etkilenir:* {kim}")
        izl = " | ".join(m["izlenecekler"]) if m["izlenecekler"] else "— (yok)"
        p.append(f"- *Ne izlenmeli:* {izl}\n")

        p.append("### Sizin yorumunuz\n")
        p.append("```")
        p.append("Kim etkilenir:  ")
        p.append("Ne izlenmeli:   ")
        p.append("Not:            ")
        p.append("```\n")
        p.append("---")

    yol = pathlib.Path(_KOK.parent / f"YORUM-{date.today().isoformat()}.md")

    # VAR OLAN DOSYANIN UZERINE YAZILMAZ.
    #
    # Bu betik bir kez calistirildi, editor doldurmaya basladi ve betik
    # ikinci kez calisinca YAZILANLARI SILDI. Dosya gunluk ada sahip
    # oldugu icin ayni gun ikinci calistirmada ayni ada denk geliyor.
    #
    # Uretilen dosya bir CIKTI degil, uzerinde CALISILAN bir belge --
    # oyle davranilmali.
    if yol.exists() and not args.uzerine_yaz:
        yeni = yol.with_name(f"{yol.stem}-{_sira(yol)}.md")
        print(f"{yol.name} zaten var, uzerine YAZILMADI.")
        print(f"Yeni dosya: {yeni.name}")
        yol = yeni
    yol.write_text("\n".join(p) + "\n", encoding="utf-8")
    konular = sorted({h["konu"] for h in secilen})
    print(f"{yol.name} yazildi: {len(secilen)} haber, {len(konular)} konu")
    for k in konular:
        n = sum(1 for h in secilen if h["konu"] == k)
        print(f"  {n}x {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
