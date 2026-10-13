"""Var olan bilanco sayfalarini SIFIR MODEL MALIYETIYLE yeniden kurar.

    python bilanco_tazele.py --sinir 60
    python bilanco_tazele.py --onarim          # yalnizca BOZUK sayfalar
    python bilanco_tazele.py --kuru-calis      # yazmadan goster

NEDEN AYRI BIR KIP
------------------
Sayfa yapisi degistiginde (yillik degisim tablosu eklendi, ozet basa
alindi) iki secenek vardi:

  1. Her sirketi YENIDEN URETMEK -- 60 model cagrisi, ikinci kez odenir
  2. Yalnizca OLCULEN kismi tazelemek -- sifir model cagrisi

Ikincisi secildi ve sebebi kesin: yorum GIRDIYE bagli, girdi ise
degismedi. Ayni girdiyle ikinci kez odemek, ayni seyi iki kez satin
almak olurdu.

NE YENIDEN HESAPLANIYOR, NE SAKLANIYOR
--------------------------------------
YENIDEN: yillik degisim, olcum tablosu, sektor konumu, yasal uyari.
         Hepsi deterministik -- ayni veriden ayni sonuc.
SAKLANAN: AI yorumu. Sayfanin kendisinden okunup aynen geri konuyor.

Ag istegi var (mali tablo yeniden cekiliyor) ama o UCRETSIZ; maliyet
model cagrisinda.

YORUMSUZ SAYFA URETILMIYOR -- BURADA DA
---------------------------------------
Sakli yorum bulunamazsa sayfaya DOKUNULMUYOR. Yorumsuz bir sayfa
uretmek, "her bilanco AI yorumundan gecer" kuralini tazeleme
kapisindan delmek olurdu.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bilanco_ag              # noqa: E402
import bilanco_denetim as bd   # noqa: E402
import guvenlik                # noqa: E402
import uret_bilanco as UB      # noqa: E402
import uret_bilanco_sayfa as U  # noqa: E402
import yayin                   # noqa: E402

#: Yorumun sayfada bulunabilecegi bolum basliklari.
#:
#: Iki bicim var: eski sayfalarda sonda "## Netaris yorumu",
#: yeni yapida basta "## Özet". Tazeleme ESKI sayfalar icin
#: yazildigi icin ikisi de araniyor.
BASLIKLAR = ("Özet", "Netaris yorumu")

_ON_DESEN = re.compile(r"(---\n)(.*?)(\n---\n)(.*)", re.S)
_KOD_DESEN = re.compile(r"^kod:\s*(\S+)", re.M)


def yorumu_al(govde: str) -> str:
    """Sayfada SAKLI duran AI yorumunu cikarir.

    Bulamazsa bos doner ve cagiran taraf sayfaya dokunmaz -- yanlis
    bir yorum uretmektense hic dokunmamak dogru.
    """
    for baslik in BASLIKLAR:
        desen = re.compile(
            r"^##\s*" + re.escape(baslik) + r"\s*$\n+(.+?)(?=\n\n|\n##|\Z)",
            re.M | re.S)
        m = desen.search(govde)
        if m:
            return " ".join(m.group(1).split())
    return ""


def baglam_kur() -> tuple[dict, dict]:
    """kod -> (sektor, oran, medyan, n, donem, mali_not) + unvan defteri.

    Oranlar ve medyanlar YENIDEN HESAPLANMIYOR: `sektor_ozet.json`
    ne diyorsa o. Ikinci bir hesap, iki farkli dogru demek olurdu.

    KIYAS KUMESI SAYFA URETICISININ ISLEVINDEN OKUNUYOR
    ---------------------------------------------------
    Hangi medyanla kiyaslanacagi `U.kiyas_kumesi` ile belirleniyor --
    yani tazeleme ile ilk uretim AYNI kurali kullaniyor. Burada ayni
    karari ikinci kez yazmak, mali takvim ayrimi degistiginde birinin
    guncellenip otekinin unutulmasi demekti. Bu depoda ayni sinif
    kusur (iki yerde ayni seye karar veren kod) ceyrek sayisinda
    zaten bir kez yayina cikti.
    """
    ozet = json.loads(U.OZET.read_text(encoding="utf-8"))
    defter = json.loads(U.DEFTER.read_text(encoding="utf-8"))["sirketler"]
    baglam: dict[str, tuple] = {}
    for sektor, v in ozet.items():
        for kod, oran in v["sirket"].items():
            medyan, n, donem, mali_not = U.kiyas_kumesi(v, kod)
            if not medyan:
                # Kiyassiz sayfa tazelenmiyor -- bos bir medyan
                # sutunu yayimlamaktansa sayfa oldugu gibi kalsin.
                continue
            baglam[kod.upper()] = (sektor, oran, medyan, n, donem,
                                   mali_not)
    return baglam, defter


def sayfa_tazele(yol: pathlib.Path, baglam: dict, defter: dict,
                 kuru: bool) -> tuple[bool, str]:
    """Tek sayfa. Doner: (tazelendi_mi, aciklama)."""
    m = _ON_DESEN.match(yol.read_text(encoding="utf-8"))
    if not m or "kategori: Bilanço Analizi" not in m.group(2):
        return False, ""                     # bilanco sayfasi degil
    k = _KOD_DESEN.search(m.group(2))
    if not k:
        return False, "kod alanı yok"
    kod = k.group(1).upper()
    if kod not in baglam:
        return False, "sektör özetinde yok"

    yorum = yorumu_al(m.group(4))
    if not yorum:
        return False, "saklı yorum bulunamadı"

    sektor, oran, medyan, n, donem, mali_not = baglam[kod]
    d, once, eksik = bilanco_ag.donem_getir(
        kod, donem, sektor_tr=sektor, ciftli=True)
    if d is None:
        return False, "eksik: " + ", ".join(eksik[:2])

    # ORAN SAYFANIN KENDI VERISINDEN -- gerekcesi
    # `uret_bilanco_sayfa.sirket_isle` uzerinde yazili.
    #
    # ONARIM ICIN AYRICA SART: tazeleme oranlari ozetten okursa,
    # ozetteki bozuk bir oran sayfaya YENIDEN yazilir ve sayfa
    # onarim kuyrugundan HIC dusmez -- her kosuda ayni isi yapan
    # bir saat bombasi olurdu. Olculdu: negatif ozkaynakla
    # hesaplanmis alti ROE tam bu durumdaydi.
    kendi = UB._oranlari(d)
    if kendi:
        oran = kendi

    unvan = (defter.get(kod) or {}).get("unvan", kod)
    govde = U.govde_kur(kod, unvan, sektor, donem, d, oran, medyan,
                        n, yorum, mali_not=mali_not,
                        alt_sektor=(defter.get(kod) or {}).get(
                            "alt_sektor") or "",
                        once=once)

    tamam, bulgular = guvenlik.yayinlanabilir(govde)
    if not tamam:
        return False, "güvenlik: " + (bulgular[0].aciklama[:40]
                                      if bulgular else "?")
    if not kuru:
        yayin.yaz_sektorel(
            govde=govde, sirket=unvan, kod=kod, donem=donem, sektor=sektor,
            kaynak="Çeyreklik mali tablolardan türetildi; sektör medyanı "
                   "Netaris hesabı")
    return True, "+yıllık değişim" if once is not None else "yenilendi"


def onarim_kuyrugu(defter: dict) -> list:
    """Sayfalari ONARIM IHTIYACINA gore siralar: bozuk olanlar basa.

    NEDEN SIRA ONEMLI -- BU DEPODA YASANDI
    --------------------------------------
    Alfabetik sira + `--sinir`, kuyrugun sonuna HIC ulasmiyor: her
    kosu ayni ilk N sayfayi yeniden kuruyor. Ayni tuzaga sektor
    sirasinda da dusulmustu (olculdu 2026-09-14: 11 sektorun hep
    ayni ilk ucu cekiliyordu).

    Onarim ihtiyaci YERELDE olculuyor -- ag istegi yok. Kuyruk
    onarilan sayfa sayisinca KISALIYOR; bitince adim kendiliginden
    etkisiz hale geliyor.
    """
    miras = bd.miras_sayfalar()
    kuyruk = []
    for yol in sorted(U.SITE.glob("*.md")):
        metin = yol.read_text(encoding="utf-8")
        k = _KOD_DESEN.search(metin)
        bilgi = defter.get(k.group(1).upper()) if k else None
        sebep = bd.onarim_gereken(metin, bilgi)
        if sebep:
            kuyruk.append((yol, sebep))
    # MIRAS LISTESINDE OLMAYAN BOZUK SAYFA ONCE.
    #
    # O sayfa korumanin tolere ETMEDIGI sayfadir, yani CI'i kirmizi
    # tutan sayfadir. Miras sayfalari zaten tolere ediliyor; onlari
    # onden gecirmek, kirmizi kosuyu bir dilim daha beklettirir.
    #
    # Ikincil anahtar dosya adi: ayni oncelikte duzen degismiyor.
    kuyruk.sort(key=lambda p: (p[0].name in miras, p[0].name))
    return kuyruk


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=60)
    a.add_argument("--kuru-calis", action="store_true")
    a.add_argument("--onarim", action="store_true",
                   help="yalnizca BOZUK sayfalari yeniden kurar")
    n = a.parse_args()

    if not U.OZET.exists():
        print(f"{U.OZET} yok -- önce uret_bilanco.py çalışmalı.")
        return 1
    baglam, defter = baglam_kur()

    if n.onarim:
        kuyruk = onarim_kuyrugu(defter)
        print(f"onarım kipi: {len(kuyruk)} sayfa onarım bekliyor")
        if not kuyruk:
            print("onarılacak sayfa YOK -- hiçbir şey yapılmadı")
            return 0
        for yol, sebep in kuyruk[:8]:
            print(f"  {yol.stem:<24}{', '.join(sebep)}")
        if len(kuyruk) > 8:
            print(f"  ... ve {len(kuyruk) - 8} sayfa daha")
        yollar = [y for y, _ in kuyruk]
    else:
        yollar = sorted(U.SITE.glob("*.md"))

    tazelenen = atlanan = 0
    for yol in yollar:
        if tazelenen >= n.sinir:
            print(f"\nsınıra ulaşıldı ({n.sinir})")
            break
        ok, not_ = sayfa_tazele(yol, baglam, defter, n.kuru_calis)
        if ok:
            tazelenen += 1
            print(f"  {yol.stem:<20}{not_}")
        elif not_:
            atlanan += 1
            print(f"  {yol.stem:<20}ATLANDI -- {not_}")

    print(f"\ntazelenen {tazelenen}, atlanan {atlanan}")
    print("model çağrısı: 0 — saklı yorumlar aynen yeniden kullanıldı")
    if n.onarim and not n.kuru_calis:
        kalan = onarim_kuyrugu(defter)
        print(f"onarım bekleyen: {len(kalan)} sayfa "
              f"(sonraki koşuda sürer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
