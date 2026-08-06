"""Haber yorumlarini uretir ve depoya yazar.

    gundem.json -> olculmus veri -> model -> dogrulama -> depo

Site kurulumu depodan okuyor; bu hat modelle konusan TEK yer.

NEDEN AYRI HAT
--------------
Yorum uretimi ag istegi ve para demek. Site kurulumunun (`insa.py`)
buna bagimli olmamasi gerekiyor: model coktugunde ya da kota
bittiginde site yine kurulmali, yalnizca yorum bolumu basilmasin.

HANGI HABERLER
--------------
Hepsi degil. Gunde 130 haber geliyor; her birine model cagirmak hem
kotayi bitirir hem degersiz. Olcut senaryo bolumuyle AYNI: olay
motorunun siddet esigi. Boylece yorum, sitenin zaten "onemli" dedigi
haberlerde birikiyor.

TEKRAR URETILMEZ
----------------
Bir haber bir kez yorumlanir. Depoda yorumu olan habere ikinci kez
model cagrilmiyor -- hem maliyet hem tutarlilik: okur sayfayi
yenileyince metin degismemeli.

    python haber_botu/uret_ai_yorum.py
    python haber_botu/uret_ai_yorum.py --sinir 5      # deneme
    python haber_botu/uret_ai_yorum.py --kuru         # cagirma, goster
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "ai"), str(_KOK / "analiz"),
                str(_KOK / "kaynak")]

import beyin      # noqa: E402
import dosya      # noqa: E402
import olay       # noqa: E402
import yorumcu    # noqa: E402

GUNDEM = _KOK.parent / "site" / "icerik" / "gundem.json"

#: Bir calistirmada en fazla kac yorum. Ucretsiz kotayi tek seferde
#: bitirmemek ve hattin suresini sinirlamak icin.
VARSAYILAN_SINIR = 12

SEMA = """
CREATE TABLE IF NOT EXISTS ai_yorum (
  adres       TEXT PRIMARY KEY,
  metin       TEXT NOT NULL,
  saglayici   TEXT NOT NULL,
  model       TEXT NOT NULL,
  kayit_ani   TEXT NOT NULL
);
"""


def girdi_kur(h: dict, d) -> str:
    """Modele gidecek metin -- SAYFADA NE VARSA O.

    Girdi sayfanin kendisinden turetiliyor; ikisi ayri kaynaktan
    gelseydi metin sayfada olmayan bir seyi anlatabilirdi.
    """
    p = [f"Haber: {h.get('baslik', '')}",
         f"Konu: {h.get('konu', '')}",
         f"Kaynak: {h.get('kurum_tam') or h.get('kurum', '')}"]
    if h.get("ozet"):
        p.append(f"Veri: {h['ozet']}")
    if d is not None:
        if d.acilis:
            p.append(f"Açılış: {d.acilis}")
        for b in d.bulgular:
            p.append(f"Bulgu: {b}")
        for g in d.turkiye:
            p.append(f"Gösterge: {g.ad} {g.son}{g.birim} "
                     f"(önceki {g.onceki}{g.birim}, değişim {g.degisim}, "
                     f"{g.tarih})")
        if d.duyarlilik:
            p.append("Duyarlılık sırası: " + " > ".join(
                f"{ad} ({neden})" for ad, _s, neden in d.duyarlilik[:4]))
        if d.izlenecekler:
            p.append("İzlenecekler: " + ", ".join(d.izlenecekler[:4]))
    if h.get("neden_onemli"):
        p.append(f"Bağlam: {h['neden_onemli']}")
    return "\n".join(p)[:2400]


def secilenler(haberler: list[dict], var: set[str], dosyalar: dict) -> list[dict]:
    """Yorumlanacak haberler.

    OLCUT "OLAY ESIGI" DEGIL, "ELIMIZDE VERI VAR MI".
    Ilk surumde olay esigi kullanildi ve 45 haberlik pencerede yalnizca
    BIR aday cikti -- esik senaryo bolumu icin dogru (az ama dolu
    tartisma), yorum icin fazla dar.

    Dogru olcut su: modelin anlatacagi olculmus bir sey var mi. Acilis
    cumlesi, bulgu, Turkiye paneli ya da haberin kendi ozeti varsa
    yorum kurulabilir; hicbiri yoksa model yalnizca basligi
    sisirecektir.

    Siralama olay siddetine gore: kota sinirliysa once onemli haber.
    """
    cikti = []
    for h in haberler:
        adres = h.get("adres", "")
        if not h.get("yorumlanir") or adres in var:
            continue
        d = dosyalar.get(adres)
        veri_var = bool(
            (h.get("ozet") or "").strip()
            or (d is not None and (d.acilis or d.bulgular or d.turkiye)))
        if not veri_var:
            continue
        o = olay.siniflandir(h.get("baslik_kaynak") or h.get("baslik", ""),
                             h.get("kurum", ""))
        cikti.append((o.siddet if o else 0, h))
    cikti.sort(key=lambda x: -x[0])
    return [h for _s, h in cikti]


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--sinir", type=int, default=VARSAYILAN_SINIR)
    a.add_argument("--kuru", action="store_true",
                   help="model cagirma, yalnizca ne yapilacagini goster")
    args = a.parse_args()

    s = yorumcu.saglayici()
    if not s and not args.kuru:
        print("Saglayici yok (ANTHROPIC_API_KEY ya da CLOUDFLARE_* "
              "tanimli degil) -- yorum uretilmedi.")
        return 0
    print(f"saglayici: {s or '(kuru calistirma)'}")

    if not GUNDEM.exists():
        print(f"{GUNDEM} yok -- once uret_gundem.py calismali.")
        return 1
    veri = json.loads(GUNDEM.read_text(encoding="utf-8"))

    with beyin.baglan() as b:
        b.executescript(SEMA)
        var = {r[0] for r in b.execute("SELECT adres FROM ai_yorum")}

    # Arastirma dosyalari BIR KEZ kuruluyor: hem secim hem girdi ayni
    # nesneyi kullaniyor. Iki kez kurmak depoyu iki kez okumak demekti.
    dosyalar = {}
    for h in veri.get("haberler", []):
        if h.get("yorumlanir") and h.get("adres"):
            dosyalar[h["adres"]] = dosya.kur(
                h.get("konu", ""), h.get("bolge", ""), h.get("tarih", ""),
                baslik=h.get("baslik_kaynak") or h.get("baslik", ""),
                ozetsiz=not (h.get("ozet") or "").strip())

    aday = secilenler(veri.get("haberler", []), var, dosyalar)
    print(f"{len(aday)} aday, sinir {args.sinir}")
    if not aday:
        return 0

    uretilen = reddedilen = 0
    with beyin.baglan() as b:
        b.executescript(SEMA)
        with beyin.calisma_kaydi(b, "ai_yorum") as ozet:
            for h in aday[:args.sinir]:
                girdi = girdi_kur(h, dosyalar.get(h["adres"]))
                if args.kuru:
                    print(f"\n--- {h['baslik'][:64]}\n{girdi[:400]}")
                    continue

                metin, neden = yorumcu.yorumla(girdi)
                if not metin:
                    reddedilen += 1
                    print(f"  RED  {h['baslik'][:52]}  ({neden})")
                    continue
                b.execute(
                    "INSERT OR REPLACE INTO ai_yorum"
                    " (adres, metin, saglayici, model, kayit_ani)"
                    " VALUES (?,?,?,?,?)",
                    (h["adres"], metin, s,
                     yorumcu.ANTHROPIC_MODEL if s == "anthropic"
                     else yorumcu.CF_MODEL, beyin.simdi()))
                uretilen += 1
                print(f"  ✓    {h['baslik'][:52]}")
                print(f"       {metin[:150]}")
            ozet.update({"uretilen": uretilen, "reddedilen": reddedilen})

    print(f"\n{uretilen} yorum uretildi, {reddedilen} reddedildi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
