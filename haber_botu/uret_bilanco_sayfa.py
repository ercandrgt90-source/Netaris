"""Sirket basina bilanco analiz sayfasi -- olculmus tablo + AI yorumu.

    sektor_ozet.json -> Donem -> tablo (deterministik) -> AI yorumu -> sayfa

    python uret_bilanco_sayfa.py --sinir 3 --kuru-calis
    python uret_bilanco_sayfa.py            # kosu basina 60

YORUMSUZ SAYFA YAYIMLANMIYOR
----------------------------
Karar acik: "her bilanco yapay zeka yorumundan gececek". Yorum
uretilemezse (anahtar yok, model bos dondu, dogrulama dusurdu) o
sirket icin sayfa YAZILMIYOR. Yarim bir sayfa yayimlamak, sozu
tutmadigini sessizce ilan etmek olurdu.

TABLO DETERMINISTIK, YORUM MODELDEN
-----------------------------------
Sayfadaki her rakam `oranlar.py` ve `sektor_ozet.py` tarafindan
hesaplaniyor; model yalnizca onlari cumleye ceviriyor ve ciktisi
`yorumcu` tarafindan dogrulaniyor (girdide olmayan sayi -> metin
tamamen atilir).

SINIR VAR -- TOPLU URETIMDE DE
------------------------------
Kosu basina 60 sayfa. 324 sirket ~6 CI kosusunda tamamlaniyor.
Sinirsiz yapilmadi ve sebebi teknik: 324 model cagrisi tek bir CI
kosusuna sigmaz, is zaman asimina ugrar ve o kosuda uretilenlerin
HICBIRI yazilmaz. Sinirli kosu yarim kalsa bile yazdigini koruyor.

TEKRAR URETMIYOR: sayfasi zaten olan sirket atlaniyor. Hat yeniden
kosturuldugunda ayni sayfayi yeniden yazmak, ayni model cagrisini
ikinci kez odemek demek.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bicim              # noqa: E402
import bilanco_ag         # noqa: E402
import bilanco_yorum      # noqa: E402
import guvenlik           # noqa: E402
import oranlar            # noqa: E402
import sektor_ozet        # noqa: E402
import yayin              # noqa: E402

OZET = _KOK / "kaynak" / "sektor_ozet.json"
DEFTER = _KOK / "kaynak" / "sirketler.json"
SITE = _KOK.parent / "site" / "icerik" / "analizler"

#: Tek kosuda en fazla kac sayfa.
#:
#: TOPLU URETIM: 5'ten 60'a cikarildi. 324 sirket bu hizla ~6 CI
#: kosusunda (yaklasik uc saat) tamamlaniyor.
#:
#: SINIRSIZ YAPILMADI ve sebebi teknik: 324 model cagrisi TEK bir CI
#: kosusuna sigmaz, is zaman asimina ugrar ve o kosuda uretilen
#: sayfalarin hicbiri yazilmaz. Sinirli kosu, yarim kalsa bile
#: yazdigini KORUYOR -- her sirket kendi sayfasi yazilir yazilmaz
#: kaliciya geciyor.
#:
#: Sayfasi olan sirket atlandigi icin hat kendini adim adim
#: dolduruyor; kosu sayisi arttikca kalan is azaliyor.
VARSAYILAN_SINIR = 60

KALEMLER = (
    ("hasilat", "Hasılat"), ("brut_kar", "Brüt kâr"),
    ("faaliyet_kari", "Faaliyet kârı"), ("favok", "FAVÖK"),
    ("net_kar", "Net kâr"), ("ozkaynak", "Özkaynak"),
    ("aktif_toplami", "Aktif toplamı"), ("net_borc", "Net borç"),
    ("faaliyet_nakit_akisi", "Faaliyet nakit akışı"),
    ("yatirim_harcamasi", "Yatırım harcaması"),
)


def _mlr(d):
    return f"{bicim.sayi(d / 1e9, 2)} milyar TL" if d is not None else "—"


def govde_kur(kod, unvan, sektor, donem, d, oran, medyan, n, yorum) -> str:
    """Sayfanin govdesi. TABLO deterministik, YORUM modelden."""
    s = [f"## {donem} dönemi ölçümleri", "",
         "| Kalem | Değer |", "| --- | ---: |"]
    for ad, etiket in KALEMLER:
        v = getattr(d, ad, None)
        if v is not None:
            s.append(f"| {etiket} | {_mlr(v)} |")

    if oran:
        s += ["", f"## Sektör içindeki konum", "",
              f"Karşılaştırma {sektor} sektöründeki {n} şirketin "
              f"**medyanına** göre yapılıyor. Medyan seçildi çünkü tek bir "
              f"şirketin uç değeri ortalamayı tek başına taşıyabiliyor.", "",
              "| Oran | Şirket | Sektör medyanı |", "| --- | ---: | ---: |"]
        for anahtar, ad in sektor_ozet.ORANLAR:
            v = oran.get(anahtar)
            if v is None:
                continue
            katsayi = anahtar in ("cari_oran", "borc_ozkaynak")
            b = ((lambda x: bicim.sayi(x, 2)) if katsayi
                 else bilanco_yorum._yuzde)
            m = medyan.get(anahtar)
            s.append(f"| {ad} | {b(v)} | {b(m) if m is not None else '—'} |")
        s += ["", "*Medyana göre konum bir sıralamadır, değerlendirme "
              "değildir. Hangi oranın yüksek olmasının iyi olduğu iş "
              "modeline göre değişir.*"]

    s += ["", "## Netaris yorumu", "", yorum]
    return "\n".join(s)


def sirket_isle(kod, bilgi, sektor, donem, oran, medyan, n,
                kuru=False) -> tuple[bool, str]:
    d, eksik = bilanco_ag.donem_getir(kod, donem, sektor_tr=sektor)
    if d is None:
        return False, "eksik: " + ", ".join(eksik[:3])

    girdi = bilanco_yorum.girdi_kur(
        kod, bilgi["unvan"], sektor, donem, simdi=d,
        oranlar_kendi=oran, medyanlar=medyan, sirket_sayisi=n)

    metin, model, sebep, _ham = bilanco_yorum.yorum_uret(girdi)
    if not metin:
        # YORUMSUZ SAYFA YAYIMLANMIYOR -- bkz. modul basi.
        return False, f"yorum yok: {sebep}"

    govde = govde_kur(kod, bilgi["unvan"], sektor, donem, d, oran,
                      medyan, n, metin)

    tamam, bulgular = guvenlik.yayinlanabilir(govde)
    if not tamam:
        return False, f"güvenlik: {bulgular[0] if bulgular else '?'}"

    if kuru:
        return True, "kuru çalışma"
    yol = yayin.yaz_sektorel(
        govde=govde, sirket=bilgi["unvan"], kod=kod, donem=donem,
        sektor=sektor,
        kaynak="Çeyreklik mali tablolardan türetildi; sektör medyanı "
               "Netaris hesabı")
    return True, str(yol.name)


def _yayimlanmis() -> set[tuple[str, str]]:
    """Yayimlanmis (kod, donem) ciftleri -- ON BILGIDEN okunur.

    DOSYA ADINDAN OKUNMUYOR ve sebebi olculdu. Onceki surum
    `p.stem` tarayip `f"{kod}-{donem}"` damgasini ariyordu; ama
    `yayin.yaz_sektorel` dosyayi TERS sirada adlandiriyor:

        damga aranan : tera-2026-6
        dosya adi    : 2026-6-tera
        eslesme      : YOK

    Yani atlama HIC calismiyordu. Gorunur bir belirtisi de yoktu:
    hat sessizce ayni sirketi yeniden uretip AYNI MODEL CAGRISINI
    ikinci kez odeyecek, ustune ayni sayfayi ezecekti. 324 sirketlik
    toplu uretimde bu, kosu basina tekrarlanan bir maliyet demek.

    On bilgideki `kod:` ve `donem:` alanlari dosya adlandirma
    kuralindan BAGIMSIZ; adlandirma yarin degisse de bu okuma
    calisir.
    """
    if not SITE.exists():
        return set()
    cikti: set[tuple[str, str]] = set()
    for p in SITE.glob("*.md"):
        kod = donem = ""
        for satir in p.read_text(encoding="utf-8").splitlines()[:25]:
            if satir.startswith("kod:"):
                kod = satir[4:].strip().upper()
            elif satir.startswith("donem:"):
                donem = satir[6:].strip()
            elif satir == "---" and kod:
                break
        # YALNIZCA BILANCO DONEMLERI. Ayni klasorde makro analizler de
        # duruyor ve onlarin `donem` alani tarih ("2026-08-20"), kodu
        # da MAKRO/BTC/OLAY gibi. Bilanco donemi her zaman "YIL/AY"
        # bicimi; suzgec bu farka dayaniyor, ada degil.
        if kod and "/" in donem:
            cikti.add((kod, donem))
    return cikti


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=VARSAYILAN_SINIR)
    a.add_argument("--sektor")
    a.add_argument("--kuru-calis", action="store_true")
    n = a.parse_args()

    if not OZET.exists():
        print(f"{OZET} yok -- önce uret_bilanco.py çalışmalı.")
        return 1
    ozet = json.loads(OZET.read_text(encoding="utf-8"))
    defter = json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]

    var = _yayimlanmis()

    yazilan = atlanan = 0
    for sektor, v in sorted(ozet.items()):
        if n.sektor and sektor != n.sektor:
            continue
        for kod, oran in sorted(v["sirket"].items()):
            if yazilan >= n.sinir:
                print(f"\nsınıra ulaşıldı ({n.sinir})")
                print(f"yazılan {yazilan}, atlanan {atlanan}")
                return 0
            bilgi = defter.get(kod)
            if not bilgi:
                continue
            # DONEME GORE ATLIYOR, SONSUZA DEK DEGIL.
            #
            # Once yalnizca koda bakiyordu: sirketin bir sayfasi varsa
            # bir daha HIC uretilmiyordu. Yeni ceyrek geldiginde de
            # atlanacakti -- yani "bir sonraki bilancolar" hic
            # yayimlanmazdi. Sessiz bir kilit: hata vermeden, hicbir
            # sey yapmadan.
            #
            # Artik kod VE donem birlikte, ON BILGIDEN araniyor
            # (bkz. `_yayimlanmis`).
            if (kod.upper(), v["donem"]) in var:
                atlanan += 1
                continue
            ok, not_ = sirket_isle(kod, bilgi, sektor, v["donem"], oran,
                                   v["medyan"], v["sirket_sayisi"],
                                   kuru=n.kuru_calis)
            if ok:
                yazilan += 1
                print(f"  {kod:<8}{not_}")
            else:
                atlanan += 1
                print(f"  {kod:<8}ATLANDI -- {not_}")

    print(f"\nyazılan {yazilan}, atlanan {atlanan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
