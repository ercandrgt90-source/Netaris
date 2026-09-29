# -*- coding: utf-8 -*-
"""NOBETCI TETIKLEYEBILIYOR MU? -- sessiz arizayi duyulur kilar.

BU DOSYA NEDEN VAR
------------------
Olculdu (2026-09-29): sitenin kurulma tempsu 38 kosu/gunden 4'e
dustu. Sebep nobetcinin calismamasi DEGILDI -- nobetci kusursuz
calisiyordu:

    /api/nobetci
    {"jeton_kurulu":true, "icerik_yasi_saat":1.27, "esik_saat":0.6,
     "son_kararlar":[{"karar":"tetiklendi","yanit":401}, ... ]}

    17 tetigin 17'si 401. Basarili: 0.

Yani nobetci bayatligi goruyor, esigi asinca tetikliyor ve GitHub
her seferinde "yetkisiz" diyor. Jeton kurulu ama REDDEDILIYOR --
iptal edilmis ya da suresi dolmus.

NEDEN BU ARIZA GORUNMEZ
-----------------------
Depodaki CI alarmi KIRMIZI KOSUYU duyuruyor. Ama burada kirmizi kosu
yok: kosu hic BASLAMIYOR. Basarisiz bir dispatch, GitHub tarafinda
hicbir iz birakmiyor; yalnizca bu ucun tamponunda duruyor ve oraya
kimse bakmiyor.

"Cevap uretiliyor ama okunabilir degil" -- bu depoda tekrar eden
kusur sinifi. Tanilama zaten dogruydu; eksik olan ona BAKAN seydi.

NEDEN SINAMA DEGIL, AYRI BIR ADIM
---------------------------------
CI'da `calistir` dusen sinamada `exit 1` yapiyor, yani kirmizi bir
sinama BUTUN KOSUYU ve dagitimi durdurur. Bu arizayi sinamayla
duyurmak, "site bes saatte bir guncelleniyor" sorununu "site hic
guncellenmiyor"a cevirirdi.

Bu yuzden buradaki MANTIK sinaniyor (bkz. `test_nobet_denetimi.py`),
arizanin kendisi ise is akisinda DAGITIMI ENGELLEMEYEN bir adimda
duyuruluyor.

NEDEN "BILINMIYOR" AYRI BIR DURUM
---------------------------------
Uca ulasilamamasi ariza DEGIL. Bu depoda olcum aracinin kendisi
defalarca yanlis alarm uretti; ulasilamayan bir ucu "bozuk" saymak
gercek bir arizayi da inandiriciliktan dusururdu.

Kullanim:
    python site/nobet_denetimi.py
    python site/nobet_denetimi.py --adres https://netaris.net
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

#: Tetigin BASARILI sayildigi HTTP yanitlari. `repository_dispatch`
#: basarida 204 doner; 200 da kabul, GitHub degistirirse diye.
BASARILI_YANIT = frozenset({200, 204})

#: Bu kadar tetik gormeden "bozuk" denmiyor. Tek bir 401 gecici
#: olabilir; kararin dayanagi TEKRAR.
EN_AZ_TETIK = 3

DURUM_SAGLIKLI = "saglikli"
DURUM_BOZUK = "bozuk"
DURUM_BILINMIYOR = "bilinmiyor"


def degerlendir(veri: dict | None) -> tuple[str, str]:
    """(durum, aciklama) dondurur. Ag ERISIMI YOK -- saf mantik.

    Saf tutulmasinin sebebi sinanabilirlik: ariza senaryolari uydurma
    veriyle, ag olmadan kosuluyor.
    """
    if not isinstance(veri, dict):
        return DURUM_BILINMIYOR, "tanilama ucu okunamadi"

    if veri.get("jeton_kurulu") is False:
        return DURUM_BOZUK, "nobet jetonu HIC KURULMAMIS"

    kararlar = veri.get("son_kararlar")
    if not isinstance(kararlar, list) or not kararlar:
        return DURUM_BILINMIYOR, "karar kaydi yok"

    tetikler = [k for k in kararlar
                if isinstance(k, dict) and k.get("karar") == "tetiklendi"]
    if len(tetikler) < EN_AZ_TETIK:
        return (DURUM_BILINMIYOR,
                f"yeterli tetik yok ({len(tetikler)} < {EN_AZ_TETIK})")

    basarili = [t for t in tetikler if t.get("yanit") in BASARILI_YANIT]
    if basarili:
        return (DURUM_SAGLIKLI,
                f"{len(basarili)}/{len(tetikler)} tetik basarili")

    # Hepsi basarisiz. Baskin yanit kodu tesihisi soyluyor:
    # 401 iptal/suresi dolmus jeton, 403 yetki eksigi ya da kota.
    kodlar: dict = {}
    for t in tetikler:
        kodlar[t.get("yanit")] = kodlar.get(t.get("yanit"), 0) + 1
    baskin = max(kodlar, key=lambda k: kodlar[k])
    ipucu = {
        401: "jeton iptal edilmis ya da suresi dolmus",
        403: "jetonun yetkisi yetmiyor ya da kota bitmis",
        404: "depo adresi yanlis ya da jeton o depoyu gormuyor",
    }.get(baskin, "beklenmeyen yanit")
    return (DURUM_BOZUK,
            f"{len(tetikler)} tetigin hicbiri basarili degil; "
            f"baskin yanit {baskin} -- {ipucu}")


#: KENDI KIMLIGIMIZI SOYLUYORUZ -- VARSAYILAN UA ENGELLENIYOR.
#:
#: Olculdu (2026-09-29): `curl` ucu okuyabiliyordu ama `urllib`
#: 403 aliyordu. Sebep kodda ya da ucta degildi: Cloudflare
#: varsayilan `Python-urllib/3.x` kimligini reddediyor.
#:
#: Bu fark onemli cunku sessizce "bilinmiyor" uretirdi -- yani alarm
#: kurulur, hicbir zaman CALMAZDI. Ayni sinif tuzak `workers.dev`
#: notunda da yazili.
KIMLIK = "Netaris-nobet-denetimi/1.0 (+https://netaris.net)"


def getir(adres: str, saniye: float = 20.0) -> dict | None:
    """Tanilama ucunu okur. Ulasilamazsa None -- HATA DEGIL.

    Ulasamama SEBEBI stderr'e yaziliyor: "bilinmiyor" ile "ulasilamadi
    ama sebebi su" arasindaki fark, alarmin korlesip korlesmedigini
    anlamanin tek yolu.
    """
    istek = urllib.request.Request(
        f"{adres.rstrip('/')}/api/nobetci", headers={"User-Agent": KIMLIK})
    try:
        with urllib.request.urlopen(istek, timeout=saniye) as y:
            return json.loads(y.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"uc {e.code} dondu", file=sys.stderr)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        print(f"uca ulasilamadi: {type(e).__name__}", file=sys.stderr)
    return None


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--adres", default="https://netaris.net")
    n = a.parse_args()

    veri = getir(n.adres)
    durum, aciklama = degerlendir(veri)

    # ILK SATIR MAKINE ICIN: is akisi bunu okuyor.
    print(f"DURUM={durum}")
    print(f"ACIKLAMA={aciklama}")
    if isinstance(veri, dict):
        print(f"ICERIK_YASI_SAAT={veri.get('icerik_yasi_saat')}")
        print(f"ESIK_SAAT={veri.get('esik_saat')}")

    # CIKIS KODU HER ZAMAN 0. Karari is akisi veriyor; bu betigin
    # kendisi hicbir zaman bir kosuyu dusurmemeli.
    return 0


if __name__ == "__main__":
    sys.exit(main())
