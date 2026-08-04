"""Gecmis haber sayfalarini git gecmisinden kurtarir.

NEDEN GEREKLI
-------------
`haber.sayfa_veri` sutunu sonradan eklendi. Ondan onceki haberlerin ozeti,
fotografi ve baglami hicbir yerde saklanmiyordu -- yalnizca o gunun
`site/icerik/gundem.json` dosyasinda vardi ve dosya her calistirmada
uzerine yaziliyordu.

Ama her otomatik yayin bir commit birakti. Yani her pencere git
gecmisinde duruyor. Bu betik o pencereleri okuyup depoyu geriye donuk
dolduruyor.

    python haber_botu/arsiv_kurtar.py

TEK SEFERLIK. Bundan sonra `beyin.haber_yaz` yuku zaten kaydediyor.
Yine de yeniden calistirmak zararsiz: var olan yuk KORUNUR, yalnizca
bos olanlar doldurulur.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import beyin  # noqa: E402

DOSYA = "site/icerik/gundem.json"


def _commitler() -> list[str]:
    r = subprocess.run(
        ["git", "log", "--format=%H", "--", DOSYA],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(_KOK.parent))
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


def _pencere(commit: str) -> list[dict]:
    r = subprocess.run(
        ["git", "show", f"{commit}:{DOSYA}"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(_KOK.parent))
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout).get("haberler", [])
    except ValueError:
        return []


def main() -> int:
    commitler = _commitler()
    print(f"{len(commitler)} surum taranacak")

    # ESKIDEN YENIYE gidiliyor. Ters yonde gidilse eski (ve muhtemelen
    # daha kotu cevrilmis) surum yenisinin uzerine yazardi; asagidaki
    # dogrudan atama son surumu birakiyor.
    havuz: dict[str, dict] = {}
    for c in reversed(commitler):
        for h in _pencere(c):
            if h.get("yorumlanir") and h.get("adres"):
                havuz[h["adres"]] = h
    print(f"{len(havuz)} benzersiz yorumlanabilir haber bulundu")

    dolduruldu = zaten = yok = 0
    with beyin.baglan() as b:
        for adres, h in havuz.items():
            satir = b.execute(
                "SELECT sayfa_veri FROM haber WHERE adres=?", (adres,)
            ).fetchone()
            if satir is None:
                yok += 1                 # depoda hic gorulmemis
                continue
            if satir[0]:
                zaten += 1               # yuku var, dokunulmuyor
                continue
            b.execute(
                "UPDATE haber SET sayfa_veri=? WHERE adres=?",
                (json.dumps(beyin._sayfa_yuku(h), ensure_ascii=False), adres))
            dolduruldu += 1

        # Sayfa yuku VARSA o haber bir kez yayimlanmis demektir; adresi
        # disariya verilmis olabilir. Aradan gecen surede siniflandirma
        # duzeltmeleri bazi haberleri `yorumlanir=0` yapmis olabilir ama
        # bu, YAYIMLANMIS bir adresi 404'e cevirmeyi hakli kilmaz.
        d = b.execute("UPDATE haber SET yorumlanir=1"
                      " WHERE sayfa_veri IS NOT NULL AND yorumlanir=0")
        if d.rowcount:
            print(f"{d.rowcount} haber yeniden yayimlanabilir isaretlendi "
                  f"(yayimlanmis adres 404 olmamali)")

        hazir = b.execute(
            "SELECT COUNT(*) FROM haber WHERE yorumlanir=1"
            " AND sayfa_veri IS NOT NULL").fetchone()[0]

    print(f"\n{dolduruldu} haberin sayfa yuku kurtarildi")
    print(f"{zaten} haberde yuk zaten vardi")
    if yok:
        print(f"{yok} haber depoda yok (gecmiste gorulup silinmis)")
    print(f"\nsayfasi uretilebilir toplam: {hazir} haber")
    return 0


if __name__ == "__main__":
    sys.exit(main())
