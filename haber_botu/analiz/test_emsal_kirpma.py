# -*- coding: utf-8 -*-
"""Emsal satirindaki baslik kirpmasi KELIME SINIRINDA mi?

OLCULEN OLAY (2026-11-13). `_emsal_satiri` basligi `baslik[:80]` ile
kesiyordu. Yayimlanmis 2036 emsal satirinin 308'i kelimenin ortasindan
kesikti ve hicbirinde uc nokta yoktu -- okur yarim kelimeyi basligin
kendisi saniyordu.

Biri dagitimi da durdurdu: "market functioning" -> "market function",
hemen ardinda fiyat parantezi, ve `denetim._COP_IZI` bunu JavaScript
govdesi sayip cikti denetimini kirmizi dondurdu.

Bu dosya iki yonu birden sinar:
  1. Kirpma artik kelimeyi bolmuyor ve kirpildigini belli ediyor.
  2. Koruma HALA gercek betigi yakaliyor -- gevsetilmedi.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_BURASI))
sys.path.insert(0, str(_BURASI.parent))

import bicim                                              # noqa: E402
import yazar_olay                                         # noqa: E402

GECTI = 0


def esit(a, b, ne=""):
    global GECTI
    if a != b:
        raise AssertionError(f"DUSTU {ne}: {a!r} != {b!r}")
    GECTI += 1


def dogru(k, ne=""):
    global GECTI
    if not k:
        raise AssertionError(f"DUSTU {ne}")
    GECTI += 1


# Olculen olayin TAM basligi (kaynaktan, 131 karakter).
LOGAN = ("Fed's Logan: Prudent for FOMC to strengthen tools for supporting "
         "market functioning without providing unnecessary economic stimulus")

# Dagitimi durduran cikti denetimi olcutu URETICIDEN okunuyor.
# Kopya cikarmak iki kapinin sessizce ayrismasi demek: koruma
# gevsetilirse bu sinama da gevser ve hicbir sey olcmez.
sys.path.insert(0, str(_BURASI.parent))
from denetim import _COP_IZI                               # noqa: E402

BETIK_KALIBI = dict(_COP_IZI)["betik govdesi"]


# ---------------------------------------------------------------- 1
print("1. kelime_kirp kelimeyi BOLMUYOR")

dogru(len(LOGAN) > 80, "atillik: fikstur zaten sinirin altinda olmamali")
esit(LOGAN[:80][-8:], "function", "ham dilimleme gercekten kelimeyi boluyor")
dogru(LOGAN[80] not in " ", "kesme noktasi kelimenin ORTASINDA")

for sinir in (40, 60, 80, 90, 100):
    cikti = bicim.kelime_kirp(LOGAN, sinir)
    dogru(cikti.endswith("…"), f"kirpilan metin uc nokta tasimali ({sinir})")
    govde = cikti[:-1].rstrip()
    son = govde.split()[-1]
    dogru(son in LOGAN.split(), f"son sozcuk TAM olmali ({sinir}): {son!r}")
    dogru(LOGAN.startswith(govde), f"onek korunmali ({sinir})")

esit(bicim.kelime_kirp("kisa", 80), "kisa", "sinirin altinda dokunulmaz")
esit(bicim.kelime_kirp("", 80), "", "bos metin")
esit(bicim.kelime_kirp(LOGAN, 0), LOGAN, "sinir 0 ise dokunulmaz")

# Tek uzun sozcuk: bolunecek bir sinir yok, ham kirpma kaliyor --
# ama uc nokta yine de var, yoksa okur tam sanir.
tek = "A" * 200
cikti = bicim.kelime_kirp(tek, 50)
dogru(cikti.endswith("…"), "tek uzun sozcukte de uc nokta")
dogru(len(cikti) <= 51, "tek uzun sozcuk sinira uyar")

# Kirpilan uctaki baglac/noktalama birakilmaz.
esit(bicim.kelime_kirp("Faiz karari ve enflasyon raporu", 13),
     "Faiz karari…", "uctaki baglac atilir")


# ---------------------------------------------------------------- 2
print("2. emsal satiri betik kalibini TETIKLEMIYOR")


class _Satir(dict):
    def __getitem__(self, k):
        return dict.get(self, k)


def _emsal(baslik, tepkiler):
    return yazar_olay._emsal_satiri(
        _Satir(an="2026-11-13T10:00:00", baslik=baslik,
               tepkiler=json.dumps(tepkiler)), "Para politikasi")


tepki = [{"varlik": "BTC", "degisim": -1.3},
         {"varlik": "XAU", "degisim": -0.5}]

# Kusurun TAM senaryosu: 80. karakterde "functioning" -> "function",
# hemen ardinda parantez. Once ham dilimlemenin gercekten tetikledigini
# gosteriyoruz -- yoksa asagidaki iddia bos olurdu.
hamsatir = f"- 2026-11-13 — {LOGAN[:80]} (BTC -%1,3, XAU -%0,5)"
dogru(BETIK_KALIBI.search(hamsatir), "atillik: ham dilimleme TETIKLEMELI")

satir = _emsal(LOGAN, tepki)
dogru(not BETIK_KALIBI.search(satir), f"duzeltilmis satir tetiklememeli: {satir}")
dogru("function (" not in satir, "yarim 'function (' kalmamali")
dogru("functioning" in satir or "…" in satir, "kirpma belli olmali")

# Tepki olmayan yol da ayni kirpmadan geciyor (sinir 90).
satir90 = _emsal(LOGAN, [])
dogru(not BETIK_KALIBI.search(satir90 + " (BTC -%1,3)"),
      "tepkisiz yol da kelime bolmemeli")
dogru(satir90.rstrip("…").split()[-1] in LOGAN.split(),
      f"tepkisiz yolda son sozcuk tam: {satir90}")

# Bos/None baslik cokmemeli.
dogru(_emsal(None, tepki).startswith("- 2026-11-13 —"), "None baslik")
dogru(_emsal("", []).startswith("- 2026-11-13 —"), "bos baslik")

# Kisa baslik DEGISMEDEN gecmeli -- gereksiz uc nokta bilgi kaybi gibi
# gorunur.
kisa = "Fed faizi sabit tuttu"
dogru(kisa in _emsal(kisa, tepki), "kisa baslik aynen gecer")
dogru("…" not in _emsal(kisa, tepki), "kisa baslikta uc nokta olmaz")


# ---------------------------------------------------------------- 3
print("3. ANLAM once: manset_kisalt kirpmadan ONCE deneniyor")

# Kaynak atfi atilinca sinirin altina inen baslik KIRPILMAMALI:
# bilgi yer degistiriyor, kaybolmuyor.
atifli = ("Merkez Bankasi faiz koridorunu daraltma karari aldi ve "
          "piyasalari uyardi - Reuters")
dogru(len(atifli) > 80, "atillik: atifli baslik sinirin ustunde")
cikti = yazar_olay._emsal_basligi(atifli, 80)
dogru("Reuters" not in cikti, "kaynak atfi atilir")
dogru("…" not in cikti, f"atif atilinca kirpmaya gerek kalmaz: {cikti}")


# ---------------------------------------------------------------- 4
print("4. koruma GEVSETILMEDI: gercek betik hala yakalaniyor")

gercekler = [
    'new TradingView.widget({"container_id": "tv_1"})',
    "function () { return 1; }",
    "var widget = new Widget();",
    "container_id",
]
for g in gercekler:
    dogru(BETIK_KALIBI.search(g), f"gercek betik yakalanmali: {g!r}")


# ---------------------------------------------------------------- 5
print("5. YAYIMLANMIS sayfalarda yarim kelime kalmadi")

_KOK = _BURASI.parent.parent
SAYFALAR = _KOK / "site" / "icerik" / "analizler"
_EMSAL = re.compile(r"^- (\d{4}-\d\d-\d\d) — (.+?)"
                    r"(?: \(([^()]*%[^()]*)\))?$")


def _basliklar() -> set[str]:
    """Deponun haber basliklari -- kirpmanin DOGRU hali buradan bilinir."""
    import sqlite3
    db = _KOK / "haber_botu" / "netaris.db"
    if not db.exists():
        return set()
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cikti = set()
        for sutun in ("baslik_kaynak", "baslik_tr"):
            cikti |= {b for (b,) in
                      c.execute(f"select {sutun} from haber "
                                f"where {sutun} is not null")}
        return cikti
    finally:
        c.close()


tum = _basliklar()
satirlar = 0
yarim = []
if tum and SAYFALAR.exists():
    for p in sorted(SAYFALAR.glob("*.md")):
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _EMSAL.match(ln.rstrip())
            if not m:
                continue
            satirlar += 1
            bas = m.group(2)
            if bas.endswith("…"):
                continue
            # Daha uzun bir gercek baslik bununla BASLIYOR ve kesme
            # noktasi bosluga denk gelmiyorsa: kelime bolunmus.
            for t in tum:
                # Kesme noktasindan sonra HARF/RAKAM geliyorsa kelime
                # bolunmus demektir. "Sonraki karakter bosluk degil"
                # yetmiyor: "...rate decisions" ile "...rate decisions."
                # ikilisinde baslik TAM, yalnizca nokta eksik -- bir
                # satir boyle yanlis suclandi.
                if len(t) > len(bas) and t.startswith(bas) \
                        and t[len(bas)].isalnum():
                    yarim.append((p.name, bas[-30:]))
                    break

    # ATILLIK: kaynak bosalirsa yukaridaki dongu hicbir sey olcmez ve
    # iddia bos kumeleri esitler.
    dogru(satirlar > 1000, f"atillik: emsal satiri sayisi {satirlar}")
    dogru(len(tum) > 1000, f"atillik: baslik sayisi {len(tum)}")
    esit(yarim[:5], [], f"yarim kelimeyle biten emsal satiri: {len(yarim)}")
else:
    print("   (depo verisi yok -- atlandi)")


print(f"\nGECTI={GECTI} KALDI=0")
