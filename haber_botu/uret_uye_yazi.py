"""Uye yazilarini yayina alir.

    panel -> D1 -> [editor onayi] -> BU ADIM -> guvenlik taramasi -> site

NEDEN AYRI BIR ADIM
-------------------
Uye yazisi panelden dogrudan siteye yazilmiyor. Iki kapi var:

  1. EDITOR ONAYI (panelde, insan).
  2. GUVENLIK TARAMASI (burada, kod).

Ikisi de gecmeden yazi yayimlanmiyor. Onay tek basina yetmez: editor
gozunden kacan bir "hedef fiyat 250 TL" ifadesi, sitenin yatirim
danismanligi yapmadigi iddiasini bozar. Tarama tek basina da yetmez:
desen eslesmesi bir metnin dogru ya da yayina deger olduguna karar
veremez.

TARAMA GECMEZSE NE OLUR
-----------------------
Yazi yayimlanmaz ve durumu "reddedildi"ye doner; bulgu metni panelde
yazara gosterilir. Sessizce atlanmiyor -- yazar neden yayimlanmadigini
gormeli, yoksa ayni hatayi tekrarlar.

Kullanim:
    HAT_SIRRI=... python uret_uye_yazi.py
    HAT_SIRRI=... python uret_uye_yazi.py --kuru   # yazmadan dene
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys

import httpx

_KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(_KOK / "ai"))
sys.path.insert(0, str(_KOK))

import beyin  # noqa: E402
import guvenlik  # noqa: E402
import prompt  # noqa: E402
import yayin  # noqa: E402

TABAN = os.environ.get("NETARIS_TABAN", "https://netaris.ercandrgt90.workers.dev")
HEDEF = _KOK.parent / "site" / "icerik" / "analizler"

ZAMAN_ASIMI = 45.0

#: Uye yazisinin sonuna eklenen kunye. Yazinin siteye ait bir analiz mi
#: yoksa bir uye gorusu mu oldugu OKURA acikca soylenmeli.
UYE_KUNYESI = (
    "Bu yazı bir Netaris üyesi tarafından gönderilmiş, yayın ilkeleri "
    "kapsamında incelenerek yayımlanmıştır. İçerikteki görüşler yazarına "
    "aittir."
)


def _sir() -> str:
    s = os.environ.get("HAT_SIRRI", "").strip()
    if not s:
        print("HAT_SIRRI tanimli degil -- uye yazisi adimi ATLANDI.")
        print("  Yerelde:  $env:HAT_SIRRI = '...'")
        print("  Actions:  depo gizli degerlerine HAT_SIRRI eklenmeli")
    return s


def cek(sir: str) -> list[dict]:
    y = httpx.get(
        f"{TABAN}/api/disari-aktar",
        headers={"x-netaris-sir": sir},
        timeout=ZAMAN_ASIMI,
    )
    y.raise_for_status()
    return y.json().get("yazilar", [])


def bildir(sir: str, kayitlar: list[dict]) -> None:
    """Yayimlanan/reddedilen yazilari panele geri bildirir.

    Bu adim atlanirsa ayni yazi her calistirmada yeniden islenir ve
    yazar panelde hep "onaylandi, yayin sirasinda" gorur.
    """
    if not kayitlar:
        return
    httpx.post(
        f"{TABAN}/api/yayimlandi",
        headers={"x-netaris-sir": sir},
        json={"kayitlar": kayitlar},
        timeout=ZAMAN_ASIMI,
    ).raise_for_status()


def _metin_kur(y: dict) -> str:
    """Yayimlanacak tam metni kurar -- yasal uyari ve kunye dahil.

    Tarama bu metnin TAMAMI uzerinde calisiyor; yayimlanan sayfa neyse
    taranan da o. Yalnizca govdeyi tarayip uyariyi sonradan eklemek,
    taramanin gercek sayfayi gormemesi demek olurdu.
    """
    return (
        f"{y['govde'].strip()}\n\n"
        f"*{UYE_KUNYESI}*\n\n"
        f"{prompt.UYARI_METNI_SKORSUZ}\n"
    )


def isle(y: dict, kuru: bool) -> tuple[dict, str]:
    """Tek yaziyi isler. (bildirim kaydi, ekran satiri) doner."""
    metin = _metin_kur(y)
    tamam, bulgular = guvenlik.yayinlanabilir(metin)

    if not tamam:
        # Ayni terim metinde defalarca geciyor olabilir. Yazara ucuncu kez
        # "Hedef fiyat -- hedef fiyat beyani" yazmak bilgi eklemiyor,
        # yalnizca notu doldurup digerlerini disari itiyor.
        gorulen: dict[str, str] = {}
        for b in bulgular:
            gorulen.setdefault(b.terim.lower(), f"“{b.terim}” — {b.aciklama}")
        ozet = "; ".join(list(gorulen.values())[:4])[:560] or \
            "Yayın ilkelerine uymayan ifade bulundu."
        return (
            {"id": y["id"], "yayimlandi": False, "not": ozet},
            f"  RED    #{y['id']} {y['baslik'][:44]}\n         {ozet[:96]}",
        )

    if kuru:
        return (
            {},
            f"  gecti  #{y['id']} {y['baslik'][:44]}  (kuru calistirma, yazilmadi)",
        )

    dosya = yayin.yaz_makro(
        metin,
        konu=y["baslik"],
        kaynak="Üye gönderimi",
        kategori=y.get("kategori") or "Analist Yorumu",
        kod="UYE",
        yazar=y.get("yazar", ""),
        unvan="Netaris üyesi",
        ozet_metni=y.get("ozet", ""),
    )
    slug = dosya.stem
    return (
        {"id": y["id"], "yayimlandi": True, "slug": slug, "not": "Tarama temiz."},
        f"  YAYIN  #{y['id']} {y['baslik'][:44]}\n         {dosya.name}",
    )


def main() -> int:
    a = argparse.ArgumentParser(description="Uye yazilarini yayina alir")
    a.add_argument("--kuru", action="store_true", help="dosya yazmadan dene")
    args = a.parse_args()

    print("=" * 70)
    print("UYE YAZILARI")
    print("=" * 70)

    sir = _sir()
    if not sir:
        return 0        # eksik sir HATA degil: adim atlanir, hat devam eder

    try:
        yazilar = cek(sir)
    except httpx.HTTPError as e:
        print(f"Panel ucuna ulasilamadi: {type(e).__name__}: {e}")
        return 1

    if not yazilar:
        print("Onaylanmis bekleyen yazi yok.")
        return 0

    print(f"{len(yazilar)} onaylanmis yazi\n")
    HEDEF.mkdir(parents=True, exist_ok=True)

    bildirimler: list[dict] = []
    yayimlanan = reddedilen = 0
    for y in yazilar:
        kayit, satir = isle(y, args.kuru)
        print(satir)
        if kayit:
            bildirimler.append(kayit)
            if kayit["yayimlandi"]:
                yayimlanan += 1
            else:
                reddedilen += 1

    if not args.kuru:
        try:
            bildir(sir, bildirimler)
        except httpx.HTTPError as e:
            # Dosyalar yazildi ama panel guncellenemedi. Bunu yutmak,
            # ayni yazinin bir sonraki calistirmada tekrar yayimlanmasi
            # demek olurdu.
            print(f"\nUYARI: panel guncellenemedi -- {type(e).__name__}: {e}")
            print("Bir sonraki calistirmada ayni yazilar tekrar islenecek.")
            return 1

        with beyin.baglan() as b:
            with beyin.calisma_kaydi(b, "uye_yazi") as ozet:
                ozet.update({"yayimlanan": yayimlanan, "reddedilen": reddedilen})

    print(f"\n{yayimlanan} yayimlandi, {reddedilen} reddedildi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
