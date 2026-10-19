# -*- coding: utf-8 -*-
"""Bildirim gonderir -- GERCEK BIR OLAY VARSA, BIR KEZ.

    python haber_botu/bildirim_gonder.py            # olcum
    python haber_botu/bildirim_gonder.py --uygula   # gonder

IKI KURAL BU DOSYANIN TAMAMINI BELIRLIYOR
-----------------------------------------
1. **Gercek bir olay olmadan bildirim gonderilmez.** Sartnamenin
   kendi kurali: "Gercek bir olay veya dogrulanmis tetikleyici
   olmadan bildirim gonderme." Burada olay DEPODAN okunuyor;
   uydurulmuyor, tahmin edilmiyor.

2. **Ayni sey iki kez gonderilmez.** Hat her kosuda "yeni olan ne"
   diye bakiyor. Iz tutulmazsa ayni bilanco her kosuda yeniden
   duyurulur -- gunde onlarca kez. Bu, kullanicinin bildirimleri
   tamamen kapatmasinin EN HIZLI yolu ve bir daha acmaz.
   `bildirim_izi` tablosu tam bunun icin.

SAGLAYICI: EXPO PUSH
--------------------
`https://exp.host/--/api/v2/push/send`. Bizde bir sir
TUTULMUYOR: Expo jetonu zaten cihaza ozel ve gonderim icin ek
kimlik gerekmiyor. Android uretim derlemesinde FCM yapilandirmasi
Expo projesinde duruyor -- depoda degil.

KAYITLI CIHAZ YOKSA SESSIZCE DEGIL, ACIKCA ATLANIR
--------------------------------------------------
"0 cihaz" bir ariza degil, normal bir durum (ozellik acilmadan
once). Ama "atlandi" YAZILIR; sessiz gecmek, hattin calisip
calismadigini bilinemez yapar. Ayni ilke depodaki oteki istege
bagli entegrasyonlarda da gecerli.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

KOK = pathlib.Path(__file__).resolve().parent.parent
DEPO = KOK / "haber_botu" / "netaris.db"
SITE = KOK / "site"
VERITABANI = "netaris-uyelik"
EXPO_UC = "https://exp.host/--/api/v2/push/send"

#: Tek istekte kac jeton. Expo'nun kendi siniri 100.
YIGIN = 100

#: Bir kosuda en fazla kac bildirim turu olayi.
#:
#: Ust sinir OKURU KORUYOR: hat bir aksama sonrasi birikmis on
#: olayi aynı anda gonderirse telefon on kez titrer ve kullanici
#: bildirimleri kapatir. Birikmis olanlar ATLANMIYOR, bir sonraki
#: kosuya kaliyor.
KOSU_SINIRI = 3

#: Takvim bildirimi kac saat once.
TAKVIM_ONCE_SAAT = 2


def _d1(sql: str, yaz: bool = False) -> list[dict]:
    """D1'e sorgu. Basarisizsa BOS liste ve sebep yazilir.

    `--json` KULLANILMIYOR: Windows'ta wrangler o bayrakla bir libuv
    iddiasiyla cokuyor (ayni tuzak `senaryo_sonuclandir` ve
    `panel_ozet` icinde de yasandi).
    """
    npx = shutil.which("npx")
    if npx is None:
        print("  npx bulunamadı -- Node kurulu değil.")
        return []
    try:
        s = subprocess.run(
            [npx, "wrangler", "d1", "execute", VERITABANI,
             "--remote", "--command", " ".join(sql.split())],
            cwd=SITE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        print("  D1 sorgusu zaman aşımına uğradı.")
        return []
    if "[" not in s.stdout:
        print("  D1 okunamadı:")
        print("  " + (s.stderr or s.stdout or "")[-300:])
        return []
    try:
        return json.loads(s.stdout[s.stdout.index("["):])[0]["results"]
    except (ValueError, KeyError, IndexError) as e:
        print(f"  Yanıt ayrıştırılamadı: {type(e).__name__}")
        return []


def _tirnak(s: str) -> str:
    """SQL dizgesi icin tek tirnak kacisi."""
    return str(s).replace("'", "''")


# --------------------------------------------------------- olaylar

def sayfasi_var(yol: str) -> bool:
    """Bu adres GERCEKTEN yayimlanmis mi.

    OLCULEN KUSUR (2026-10-19): `icerik` tablosundaki yirmi bilanco
    kaydinin SEKIZININ uretilmis sayfasi yoktu. Depodaki kayit
    "uretilmeye aday" demek; yayimlanmis olmasi ayri bir sey
    (ucretsiz AI kotasi, kaynak reddi, bicim gocu...).

    Dogrulanmadan gonderilse bildirim okuru 404'e goturuyordu --
    ve bu, bildirimi bir daha acmamanin en hizli sebebi.

    `site/cikti` HIC YOKSA False: dogrulayamadigimiz seyi
    "yayimlanmis" saymak, tam da kacindigimiz hatayi yapmak olurdu.
    """
    if not yol:
        return False
    kok = SITE / "cikti"
    if not kok.is_dir():
        return False
    return (kok / yol.strip("/") / "index.html").is_file()


def bilanco_olaylari(b: sqlite3.Connection, gonderilmis: set) -> list[dict]:
    """Yeni yayimlanmis bilanco analizleri.

    KAYNAK DEPO, tahmin degil: `icerik` tablosundaki yayimlanmis
    bilanco sayfalari okunuyor.
    """
    # SEMA DEPODAN OKUNDU, TAHMIN EDILMEDI:
    #   icerik(slug, tur, baslik, kod, kategori, tarih, kelime,
    #          kayit_ani)
    # `tur` degeri 'bilanco-analizi'; 'bilanco' DEGIL. Ilk yazimda
    # tahmin edilmisti ve sorgu sessizce BOS donerdi -- yani hat
    # calisiyor gorunup hicbir bildirim gondermezdi.
    #
    # SIRA `kayit_ani`a gore: `tarih` donem tarihi (bilanconun ait
    # oldugu ceyrek), `kayit_ani` ise BIZIM yayimladigimiz an.
    # "Yeni yayimlandi" sorusunun cevabi ikincisi.
    try:
        satir = b.execute(
            "SELECT kod, baslik, slug, tarih, kayit_ani FROM icerik"
            " WHERE tur = 'bilanco-analizi'"
            " ORDER BY kayit_ani DESC LIMIT 20").fetchall()
    except sqlite3.Error:
        return []
    cikti = []
    for r in satir:
        kod, baslik, slug, tarih = r[0], r[1], r[2], r[3]
        if not kod or not slug:
            continue
        anahtar = f"bilanco:{kod}:{tarih}"
        if anahtar in gonderilmis:
            continue
        yol = f"/analiz/{slug}/"
        # SAYFASI OLMAYAN ICIN BILDIRIM YOK -- okur 404 gormesin.
        if not sayfasi_var(yol):
            continue
        cikti.append({
            "anahtar": anahtar, "tur": "bilanco",
            "baslik": f"{kod} bilançosu yayımlandı",
            "govde": (baslik or "")[:140],
            "yol": yol,
        })
    return cikti


def takvim_olaylari(gonderilmis: set) -> list[dict]:
    """Yaklasan YUKSEK ETKILI veri aciklamalari.

    Besleme dosyasindan okunuyor -- yani okurun GORDUGU takvimin
    kendisi. Ikinci bir kaynak kullanmak, bildirimle ekranin ayri
    seyler soylemesi demekti.
    """
    dosya = SITE / "cikti" / "v1" / "takvim.json"
    if not dosya.is_file():
        return []
    try:
        d = json.loads(dosya.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    simdi = _dt.datetime.now(_dt.timezone.utc)
    sinir = simdi + _dt.timedelta(hours=TAKVIM_ONCE_SAAT)
    cikti = []
    for o in d.get("ogeler", []):
        # YALNIZCA YUKSEK ETKI. Her veri icin bildirim gondermek,
        # bildirimleri gurultuye cevirir.
        if int(o.get("onem") or 0) < 3:
            continue
        # SAATI KESINLESMEMIS aciklama icin bildirim YOK: okuru
        # yanlis saatte beklemeye cagirmak olurdu.
        if not o.get("kesin"):
            continue
        try:
            an = _dt.datetime.fromisoformat(o["an"])
        except (KeyError, ValueError):
            continue
        if an.tzinfo is None:
            an = an.replace(tzinfo=_dt.timezone.utc)
        if not (simdi <= an <= sinir):
            continue
        anahtar = f"takvim:{o.get('seri') or o.get('ad')}:{o['an'][:16]}"
        if anahtar in gonderilmis:
            continue
        cikti.append({
            "anahtar": anahtar, "tur": "takvim",
            "baslik": f"{o.get('ad', '')} yaklaşıyor",
            "govde": f"{o.get('gun', '')} {o.get('saat', '')} "
                     f"(Türkiye saati)".strip(),
            "yol": "/takvim/",
        })
    return cikti


# --------------------------------------------------------- gonderim

def gonder(jetonlar: list[str], baslik: str, govde: str,
           veri: dict) -> tuple[int, list[str]]:
    """Expo Push'a gonderir. Doner: (basarili, olu jetonlar).

    OLU JETON AYIKLANIYOR: uygulama silinince jeton gecersizlesiyor
    ve Expo `DeviceNotRegistered` donuyor. Temizlenmezse tablo
    zamanla olu kayitla doluyor ve her kosu onlara da gondermeye
    calisiyor.
    """
    basarili, olu = 0, []
    for i in range(0, len(jetonlar), YIGIN):
        parca = jetonlar[i:i + YIGIN]
        govdeler = [{
            "to": j, "title": baslik, "body": govde,
            "sound": "default", "data": veri,
        } for j in parca]
        istek = urllib.request.Request(
            EXPO_UC,
            data=json.dumps(govdeler).encode("utf-8"),
            headers={"content-type": "application/json",
                     "accept": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(istek, timeout=30) as c:
                cevap = json.loads(c.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as e:
            print(f"  gönderim başarısız: {type(e).__name__}")
            continue
        for j, s in zip(parca, cevap.get("data") or []):
            if s.get("status") == "ok":
                basarili += 1
            elif (s.get("details") or {}).get("error") == "DeviceNotRegistered":
                olu.append(j)
    return basarili, olu


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true",
                    help="ölçmekle kalma, gerçekten gönder")
    a = ap.parse_args()

    print("=== BILDIRIM ===")

    # KAPALIYKEN D1'E HIC DOKUNULMUYOR.
    #
    # Ozellik acilana kadar her kosuda bir `wrangler d1 execute`
    # cagirmak, sifir fayda icin saniyeler harciyor. Depodaki oteki
    # istege bagli entegrasyonlarin deseni ayni: "anahtar yoksa adim
    # kendini atlar, hat kirmizi DONMEZ".
    #
    # Acmak icin: is akisinda `BILDIRIM_ETKIN: "1"` tanimlayin.
    if os.environ.get("BILDIRIM_ETKIN", "").strip() not in ("1", "true"):
        print("  kapalı (BILDIRIM_ETKIN tanımlı değil) -- atlandı.")
        return 0

    cihazlar = _d1(
        "SELECT jeton, tercihler FROM cihaz"
        " WHERE son_gorulme > date('now', '-90 day')")
    if not cihazlar:
        # 0 CIHAZ ARIZA DEGIL -- ozellik henuz acilmamis olabilir.
        # Ama ACIKCA yaziliyor; sessiz gecmek hattin calisip
        # calismadigini bilinemez yapardi.
        print("  kayıtlı cihaz yok -- gönderilecek bir şey yok.")
        print("  (uygulama bildirim izni istemeye başlayınca dolacak)")
        return 0
    print(f"  kayıtlı cihaz: {len(cihazlar)}")

    izler = _d1("SELECT anahtar FROM bildirim_izi"
                " WHERE gonderim > date('now', '-30 day')")
    gonderilmis = {r["anahtar"] for r in izler if r.get("anahtar")}

    olaylar: list[dict] = []
    if DEPO.exists():
        with sqlite3.connect(f"file:{DEPO}?mode=ro", uri=True) as b:
            olaylar += bilanco_olaylari(b, gonderilmis)
    olaylar += takvim_olaylari(gonderilmis)

    if not olaylar:
        print("  yeni olay yok.")
        return 0

    # BIRIKMIS OLAYLAR ATLANMIYOR, ERTELENIYOR.
    kalan = len(olaylar) - KOSU_SINIRI
    olaylar = olaylar[:KOSU_SINIRI]
    print(f"  gönderilecek olay: {len(olaylar)}"
          + (f" ({kalan} tanesi sonraki koşuya)" if kalan > 0 else ""))

    for o in olaylar:
        # TERCIHI OLAN CIHAZLAR -- herkese degil.
        hedef = []
        for c in cihazlar:
            try:
                t = json.loads(c.get("tercihler") or "{}")
            except ValueError:
                continue
            if t.get(o["tur"]) is True:
                hedef.append(c["jeton"])
        print(f"    {o['anahtar']}  -> {len(hedef)} cihaz")
        if not a.uygula:
            continue
        if hedef:
            n, olu = gonder(hedef, o["baslik"], o["govde"],
                            {"yol": o["yol"], "tur": o["tur"]})
            print(f"      gönderildi {n}, ölü jeton {len(olu)}")
            for j in olu:
                _d1(f"DELETE FROM cihaz WHERE jeton = '{_tirnak(j)}'")
        else:
            n = 0
        # IZ HER DURUMDA YAZILIYOR -- hedef sifir olsa bile.
        #
        # Yazilmazsa, o turu kimse istemiyorken olay her kosuda
        # yeniden "yeni" sayilir ve sonsuza kadar islenir.
        _d1("INSERT OR REPLACE INTO bildirim_izi"
            " (anahtar, tur, baslik, gonderim, cihaz) VALUES"
            f" ('{_tirnak(o['anahtar'])}', '{_tirnak(o['tur'])}',"
            f" '{_tirnak(o['baslik'])}', datetime('now'), {int(n)})")

    if not a.uygula:
        print("\n  (ölçüm modu -- göndermek için --uygula)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
