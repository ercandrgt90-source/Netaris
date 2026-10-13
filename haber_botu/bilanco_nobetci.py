# -*- coding: utf-8 -*-
"""YENI CEYREK BELIRDIGINDE HABER VER -- TAKVIME DEGIL OLCUME BAKARAK.

BU DOSYA NEDEN VAR
------------------
`uret_bilanco.donem_acik()` bilanco cekmeyi TAKVIME bagliyordu:
yalnizca Mart, Mayis, Agustos ve Kasim aylarinda. O aylar KONSOLIDE
bildirim son tarihlerine gore secilmis. Ama konsolide olmayan
sirketler donem bitiminden otuz gun sonra bildiriyor, yani 9 aylik
tablolar EKIM SONUNDA gelmeye basliyor -- hattin penceresi ise
Kasim'da aciliyor.

Sonuc: bildirimler gelmeye basladiktan sonra haftalarca hicbir sey
cekilmiyor ve okur rakamlari baska yerden ogreniyor.

OLCULDU (2026-10-13): kaynakta tek istek SIRKET BASINA 0,3 saniye
suruyor -- yalnizca gelir tablosunun donem basliklari ve bitis
tarihleri. Yani "yeni donem belirdi mi" sorusu yuzlerce sirkete
dakikalar icinde sorulabiliyor. Takvim tahmini yerine OLCUM
kullanmanin maliyeti pratikte sifir.

OLCUT DONEM BITIS TARIHI, ETIKET DEGIL. Kaynagin "Q3 2026" etiketi
MALI ceyregi gosteriyor; mali yili 31 Mayis'ta biten spor kulubunde
bu takvim ceyregine denk dusmuyor. Etiket olcutuyle calisan onceki
surum bu sirketleri ELEMEK zorundaydi -- yani GSRAY'in aciklanmis
bilancosunu hic gormuyordu. Bkz. `daha_yeni`.

NE YAPIYOR
----------
1. Defterden ulasilabilir sirketleri alir (`sektor_tr` tasiyanlar --
   bilanco hattinin gorus alani bu).
2. DONEREK orneklem secer: her kosu farkli bir dilimi yokluyor,
   boylece zamanla butun evren taranmis oluyor. Nobet defterinde
   kaldigi yeri tutuyor.
3. Her sirkete tek istek atar, en yeni GERCEKLESMIS donemin bitis
   tarihini ve sirketin mali takvimini okur.
4. Gorulen en yeni bitis tarihi defterdekinden YENIYSE "donem
   acildi" diye isaretler.

KARAR NEREDE KULLANILIYOR
-------------------------
`uret_bilanco.donem_acik()` bu defteri de okuyor: takvim kapaliyken
bile nobetci yeni ceyrek gormusse hat ACILIYOR. Yani takvim artik
UCUZ BIR ON SUZGEC, karar OLCUMDE.

TEK SIRKET YETER -- VE BU BILINCLI
----------------------------------
"Donem acildi" demek icin tek bir sirkette yeni ceyrek gormek
yeterli: istenen sey tam olarak "geldikce cikalim". Kalite kapisi
ayri yerde ve zaten var -- `sektor_ozet.EN_AZ_SIRKET` uc sirketten
az olan sektore medyan uretmiyor, dolayisiyla erken gelen tek bir
bilanco sahte bir "sektor karsilastirmasi" dogurmuyor.

KAYNAGA YUK
-----------
Istekler `bilanco_ag.ARA_SN` araligiyla atiliyor ve bir kosudaki
yoklama sayisi `VARSAYILAN_ORNEKLEM` ile sinirli. Kaynak 429
dondurmeye baslarsa `bilanco_ag` kendi geri cekilmesini uyguluyor.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))
sys.path.insert(0, str(_KOK / "analiz"))

import bilanco_ag                                  # noqa: E402

DEFTER = _KOK / "kaynak" / "sirketler.json"
NOBET = _KOK / "kaynak" / "bilanco_nobet.json"

#: Bir kosuda kac sirkete sorulacak.
#:
#: OLCULDU (2026-10-13): sirket basina 0,3 saniye. 60 sirket yaklasik
#: 20 saniye arti aralik beklemeleri. Hat zaten dakikalar suruyor; bu,
#: yeni bildirimleri gunlerce kacirmamanin bedeli olarak ucuz.
VARSAYILAN_ORNEKLEM = 60


def _oku(p, varsayilan):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return varsayilan


def nobet_oku() -> dict:
    d = _oku(NOBET, {})
    return d if isinstance(d, dict) else {}


def ulasilabilir_kodlar() -> list:
    """Bilanco hattinin gorus alanindaki sirketler.

    `uret_bilanco --hepsi` sektor listesini `sektor_tr` alanindan
    kuruyor; o alani olmayan sirket hicbir sektore dusmuyor ve
    cekilmiyor. Nobetci de ayni evrene bakmali -- goremeyecegimiz bir
    sirkette yeni ceyrek gormek hatti bosuna acardi.
    """
    d = _oku(DEFTER, {}).get("sirketler") or {}
    return sorted(k.upper() for k, v in d.items() if v.get("sektor_tr"))


def daha_yeni(a, b) -> bool:
    """a donemi b'den yeni mi? Ikisi de ISO bitis tarihi ya da None.

    NEDEN ETIKET DEGIL TARIH -- OLCULDU (2026-10-13)
    ------------------------------------------------
    Onceki olcut `(yil, ceyrek)` etiketiydi. Takvim disi mali yila
    sahip sirkette kaynagin etiketi MALI ceyregi gosteriyor ve
    takvim ceyregine denk DUSMUYOR:

        GSRAY  "Q1 2027"  ->  gercek donem haziran-agustos 2026
        THYAO  "Q3 2026"  ->  gercek donem temmuz-eylul 2026

    Etiketleri karsilastirmak bu iki sirketi yanlis siraya koyuyordu,
    bu yuzden onlar bastan ELENIYORDU (`son_donem` None donuyordu).
    Elemek sahte olayi onluyor ama gercek bir bildirimi de
    gormemek demek: GSRAY'in bilancosu aciklandi ve nobetci hic
    haberdar olmadi.

    Tarih her takvimde ayni seyi olcuyor, bu yuzden kiyas tek satir.
    ISO bicimi dizgesel olarak da dogru siralaniyor.
    """
    if not a:
        return False
    if not b:
        return True
    return str(a) > str(b)


def bak(orneklem: int = VARSAYILAN_ORNEKLEM, kuru: bool = False) -> dict:
    """Bir tur yoklama. Nobet defterini gunceller ve sonucu doner."""
    nobet = nobet_oku()
    bilinen = nobet.get("son_bitis") or None
    bilinen = bilinen if isinstance(bilinen, str) else None
    kodlar = ulasilabilir_kodlar()
    if not kodlar:
        print("nobetci: defter okunamadi ya da bos -- yoklama YAPILMADI")
        return {"durum": "defter yok", "bakilan": 0, "hata": 0}

    bas = int(nobet.get("imlec") or 0) % len(kodlar)
    kac = min(orneklem, len(kodlar))
    secilen = [kodlar[(bas + i) % len(kodlar)] for i in range(kac)]

    # ESKI BICIM DEFTERDEN TEMIZLENIYOR.
    #
    # Nobet defteri eskiden `[yil, ceyrek]` tutuyordu. Liste ile
    # tarih dizgesini karsilastirmak sessizce yanlis sonuc verirdi;
    # bu yuzden eski kayitlar YOK sayiliyor ve o sirketler bir kez
    # daha TOHUMLANIYOR. Bir kosuluk gorme kaybi, yanlis bir olaydan
    # iyidir.
    gorulen = {k: v for k, v in (nobet.get("sirket") or {}).items()
               if isinstance(v, str)}
    eski_bicim = len(nobet.get("sirket") or {}) - len(gorulen)
    if eski_bicim:
        print(f"nobetci: {eski_bicim} eski biçimli kayıt yeniden "
              f"tohumlanacak (etiket -> dönem bitiş tarihi)")
    takvim = dict(nobet.get("takvim") or {})
    en_yeni = bilinen
    yeni_bildiren = []
    ilk_gorulen = 0
    hata = 0
    for kod in secilen:
        try:
            m = bilanco_ag.mali_takvim(kod)
        except Exception:
            hata += 1
            m = None
        d = m["son_bitis"] if m else None
        if m and m.get("yil_sonu_ayi"):
            # MALI TAKVIM BEDAVA GELIYOR -- ayni istekten okunuyor.
            # Yayin hatti da bu bilgiye ihtiyac duyuyor; nobetci
            # zaten her sirkete bakiyor, ogrendigini saklasin.
            takvim[kod] = m["yil_sonu_ayi"]
        if d:
            onceki = gorulen.get(kod)
            # OLAY SIRKET BAZINDA -- KURESEL ESIGE GORE DEGIL.
            #
            # Ilk yazimda "yeni bildirdi" olcutu kuresel `son_ceyrek`
            # idi. O zaman ILK bildiren sirket esigi yukseltiyor ve
            # ardindan gelen yuzlerce sirket bir daha HIC tetiklemiyor
            # -- oysa istenen sey tam olarak "geldikce cikalim".
            #
            # Olcut artik sirketin KENDI onceki degeri: her sirketin
            # ilerlemesi ayri bir olay.
            if not onceki:
                # ILK GORULME TOHUMDUR, OLAY DEGIL. Donerek orneklem
                # yuzunden bir sirket ilk kez besinci kosuda
                # gorulebiliyor; onu "yeni bildirdi" saymak sahte
                # olay uretirdi.
                ilk_gorulen += 1
                gorulen[kod] = d
            elif daha_yeni(d, onceki):
                gorulen[kod] = d
                yeni_bildiren.append(kod)
            if daha_yeni(d, en_yeni):
                en_yeni = d
        time.sleep(bilanco_ag.ARA_SN)

    # SOGUK BASLANGIC TOHUMLAMA -- "BILMIYORUM" ILE "YENI" AYNI SEY DEGIL.
    #
    # Defter bosken her sirket "yeni ceyrek bildirdi" gorunuyor:
    # karsilastirilacak bir onceki deger yok. Ilk kosuda bu haliyle
    # birakmak, zaten elimizde olan bir donem icin butun hatti bosuna
    # calistirirdi. Olculdu: ilk denemede 10 sirketin 9'u "yeni" diye
    # bildirildi -- hepsi 2026 Q2, yani BIZDE OLAN donem.
    #
    # Ilk kosu yalnizca TOHUMLUYOR: ne gorduyse deftere yazar, "donem
    # acildi" DEMEZ. Karar ancak bir sonraki kosudaki DEGISIMDEN
    # dogabilir.
    # IKI SINYAL, IKISI DE GECERLI
    # ---------------------------
    # 1. SIRKET ILERLEMESI: bildigimiz bir sirket yeni ceyrege gecti.
    # 2. MEVSIM ILERLEMESI: gorulen en yeni ceyrek, defterdekinden
    #    yeni. Bu, ILK bildiren sirketi hic gormemis olsak bile
    #    mevsimin basladigini soyluyor -- donerek orneklemde bir
    #    sirket ilk kez besinci kosuda gorulebiliyor ve o sirket Q3
    #    bildiren ilk sirket olabilir.
    #
    # Ikinci sinyal, olcut TARIH oldugu icin takvim disi sirketlerde
    # de guvenilir. Onceki surum onlari ELIYORDU: Ekim 2026'da
    # "Q3 2026" bildiren iki sirket vardi (ARENA, BALSU) ve ikisi de
    # takvim disi mali yila sahipti; etiket olcutuyle her kosuda
    # sahte "yeni donem" uretiyorlardi, bu yuzden dislanmislardi.
    #
    # Tarih olcutu sahte olayi kendiliginden onluyor (gelecekte biten
    # donem zaten ayikliniyor) ve gercek bildirimi GORUYOR.
    tohumlama = bilinen is None
    mevsim_ilerledi = daha_yeni(en_yeni, bilinen) and not tohumlama
    acildi = bool(yeni_bildiren) or mevsim_ilerledi
    sonuc = {
        "durum": ("tohumlandi" if tohumlama
                  else "yeni donem" if acildi else "degisiklik yok"),
        "mevsim_ilerledi": mevsim_ilerledi,
        "bakilan": len(secilen),
        "ilk_gorulen": ilk_gorulen,
        "hata": hata,
        "bilinen": bilinen,
        "en_yeni": en_yeni,
        "takvim_disi": sorted(k for k, v in takvim.items() if v != 12),
        "yeni_bildiren": yeni_bildiren,
    }
    if not kuru:
        simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        NOBET.write_text(json.dumps({
            "son_bitis": en_yeni,
            "acik": acildi or bool(nobet.get("acik")),
            "acilis_ani": simdi if acildi else nobet.get("acilis_ani"),
            "son_bakis": simdi,
            "imlec": (bas + len(secilen)) % len(kodlar),
            "sirket": gorulen,
            "takvim": takvim,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


def donem_acildi_mi() -> bool:
    """Nobetcinin olctugu karar: yeni ceyrek goruldu mu?

    `uret_bilanco.donem_acik` bunu okuyor. Dosya yoksa FALSE --
    "bilmiyorum" ile "acik" ayni sey degil ve bilinmeyeni acik
    saymak, her kosuda bosuna cekmek olurdu.
    """
    return bool(nobet_oku().get("acik"))


def kapat() -> None:
    """Donem islendikten sonra bayragi indirir."""
    d = nobet_oku()
    if not d:
        return
    d["acik"] = False
    d["kapanis_ani"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    NOBET.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    a = argparse.ArgumentParser(description="Bilanco nobetcisi")
    a.add_argument("--orneklem", type=int, default=VARSAYILAN_ORNEKLEM)
    a.add_argument("--kuru-calis", action="store_true")
    a.add_argument("--kapat", action="store_true",
                   help="donem islendi, bayragi indir")
    n = a.parse_args()
    if n.kapat:
        kapat()
        print("nobetci: donem bayragi indirildi")
        return 0
    s = bak(n.orneklem, n.kuru_calis)
    print(f"nobetci: {s.get('bakilan', 0)} sirkete soruldu, "
          f"{s.get('ilk_gorulen', 0)} ilk gorulme, {s.get('hata', 0)} hata")
    print(f"  defterdeki dönem  : {s.get('bilinen')}")
    print(f"  kaynakta en yeni  : {s.get('en_yeni')}")
    if s.get("takvim_disi"):
        print(f"  takvim dışı mali yıl: "
              f"{', '.join(s['takvim_disi'][:12])}")
    if s.get("durum") == "yeni donem":
        print(f"  YENI DONEM ACILDI -- {len(s['yeni_bildiren'])} sirket "
              f"bildirdi: " + ", ".join(s["yeni_bildiren"][:8]))
    elif s.get("durum") == "tohumlandi":
        print("  ILK KOSU: defter tohumlandi, donem acilmadi "
              "(karsilastirilacak onceki deger yoktu)")
    else:
        print("  degisiklik yok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
