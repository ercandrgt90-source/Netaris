"""Ufku dolan senaryolari sonuclandirir -- OLCEREK, yorumlayarak degil.

NEDEN VAR
---------
`sonuclanma` alani semada en bastan beri vardi ve senaryo sayfasinda
gosteriliyordu -- ama HICBIR SUREC onu yazmiyordu. Yani "ufku dolunca
ne oldugu gorunur" vaadi kodda duruyor, uygulamada calismiyordu.

Bu, sicil sisteminin de onunu kesiyordu: sonuclanmayan senaryo sicil
olusturamaz, sicil olmadan kalite katmani kurulamaz.

NASIL SONUCLANDIRIYOR
---------------------
Yalnizca OLCULEBILIR tetikleyicisi olan senaryolar otomatik
sonuclanir:

    olcut_kod   hangi seri       (TP.TUKFIY2025.GENEL)
    olcut_yon   hangi yon        ('altinda' | 'ustunde')
    olcut_esik  hangi esik       (30.0)

Ufuk penceresinde serinin degeri esigi gecti mi, bakilir. Gecti ise
'gerceklesti', gecmedi ise 'gerceklesmedi'.

TETIKLEYICISI OLMAYAN 'BELIRSIZ' KALIR
--------------------------------------
Her senaryo sayisal esige indirgenemez ("Hurmuz fiilen kapanirsa").
Onlari modele sordurup "gerceklesti mi" dedirtmek YANLIS olurdu: model
yanlis ayristirdiginda yanlis sonuclandirma uretir ve yanlis
sonuclandirma, sonuclandirmamaktan KOTUDUR -- yazarin sicilini
haksizca bozar.

'belirsiz' durust bir cevaptir ve sayfada oyle gorunur.

PENCERE: YAYIN -> UFUK
----------------------
Esik yalnizca senaryo YAYIMLANDIKTAN sonra ve ufku DOLMADAN once
gecilmisse sayilir. Yayin oncesi gecilmis bir esik senaryonun
ongorusu degil, zaten olmus bir sey.

    python haber_botu/senaryo_sonuclandir.py            # olcum
    python haber_botu/senaryo_sonuclandir.py --uygula   # yaz
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess

KOK = pathlib.Path(__file__).resolve().parent.parent
DEPO = KOK / "haber_botu" / "netaris.db"
SITE = KOK / "site"
VERITABANI = "netaris-uyelik"

YONLER = ("ustunde", "altinda")


def _d1(sql: str) -> list[dict]:
    """D1'e sorgu. Basarisizsa BOS liste ve sebep yazilir.

    `--json` KULLANILMIYOR: Windows'ta wrangler o bayrakla bir libuv
    iddiasiyla cokuyor. Ayni tuzak `panel_ozet.py` icinde de yasandi ve
    cozum orada da bu: normal cikti zaten JSON blogu iceriyor.
    """
    npx = shutil.which("npx")
    if npx is None:
        print("npx bulunamadı -- Node kurulu değil.")
        return []
    try:
        s = subprocess.run(
            [npx, "wrangler", "d1", "execute", VERITABANI,
             "--remote", "--command", " ".join(sql.split())],
            cwd=SITE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        print("D1 sorgusu zaman aşımına uğradı.")
        return []
    if "[" not in s.stdout:
        print("D1 okunamadı:")
        print((s.stderr or s.stdout or "")[-300:])
        return []
    try:
        return json.loads(s.stdout[s.stdout.index("["):])[0]["results"]
    except (ValueError, KeyError, IndexError) as e:
        print(f"Yanıt ayrıştırılamadı: {type(e).__name__}")
        return []


def esik_gecildi(b: sqlite3.Connection, kod: str, yon: str, esik: float,
                 baslangic: str, bitis: str) -> bool | None:
    """Seri, pencerede esigi gecti mi. Veri yoksa None.

    None ile False AYRI: "gecmedi" bir olcum, "veri yok" bir bilgi
    eksikligi. Ikisini birlestirmek, olcemedigimiz senaryoyu
    "gerceklesmedi" saymak olurdu.
    """
    r = b.execute(
        "SELECT deger FROM gosterge WHERE kod = ?"
        "   AND tarih >= ? AND tarih <= ?",
        (kod, baslangic[:10], bitis[:10])).fetchall()
    if not r:
        return None
    degerler = [x[0] for x in r if x[0] is not None]
    if not degerler:
        return None
    if yon == "ustunde":
        return max(degerler) > esik
    return min(degerler) < esik


def sonuclandir(uygula: bool = False) -> int:
    if not DEPO.exists():
        print(f"{DEPO} yok -- gösterge verisi olmadan sonuçlandırılamaz.")
        return 1

    bekleyen = _d1(
        """SELECT id, kosul, ufuk_biter, yayin, olcut_kod, olcut_yon,
                  olcut_esik
             FROM senaryo
            WHERE durum = 'yayimlandi'
              AND sonuclanma IS NULL
              AND ufuk_biter IS NOT NULL
              AND ufuk_biter <= date('now')""")
    if not bekleyen:
        print("Ufku dolan, sonuçlanmamış senaryo yok.")
        return 0

    b = sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True)
    kararlar: list[tuple[int, str, str]] = []
    for s in bekleyen:
        kod, yon, esik = s.get("olcut_kod"), s.get("olcut_yon"), s.get("olcut_esik")
        if not kod or yon not in YONLER or esik is None:
            kararlar.append((s["id"], "belirsiz",
                             "Ölçülebilir bir tetikleyici tanımlanmamış."))
            continue
        g = esik_gecildi(b, kod, yon, float(esik),
                         s.get("yayin") or "", s.get("ufuk_biter") or "")
        if g is None:
            kararlar.append((s["id"], "belirsiz",
                             f"{kod} serisinde bu dönem için veri bulunamadı."))
        elif g:
            kararlar.append((s["id"], "gerceklesti",
                             f"{kod} serisi ufuk içinde eşiği ({esik}) geçti."))
        else:
            kararlar.append((s["id"], "gerceklesmedi",
                             f"{kod} serisi ufuk boyunca eşiği ({esik}) geçmedi."))

    import collections
    say = collections.Counter(d for _i, d, _n in kararlar)
    print(f"ufku dolan senaryo : {len(bekleyen)}")
    for d, n in say.most_common():
        print(f"   {d:<16} {n}")
    for i, d, not_ in kararlar[:8]:
        print(f"   #{i} -> {d}: {not_}")

    if not uygula:
        print("\n(ölçüm modu -- yazmak için --uygula)")
        return 0

    for i, d, not_ in kararlar:
        _d1(f"UPDATE senaryo SET sonuclanma = '{d}', "
            f"sonuclanma_notu = '{not_.replace(chr(39), chr(39) * 2)}' "
            f"WHERE id = {int(i)}")
    print(f"\n{len(kararlar)} senaryo sonuçlandırıldı.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true",
                    help="ölçmekle kalma, D1'e yaz")
    return sonuclandir(ap.parse_args().uygula)


if __name__ == "__main__":
    raise SystemExit(main())
