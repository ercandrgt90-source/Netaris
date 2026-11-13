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
import os
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
print("5. YAYIMLANMIS sayfalar -- uretim ONCESI olcum, SONRASI kapi")

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


#: Hangi ASAMADA kosuyoruz. Bayragi `site/cikti_sinamalari.py`
#: kuruyor -- asamayi BILEN tek yer orasi. Sinamanin kendisi tahmin
#: etmeye calisirsa (dosya tarihine bakmak gibi) kirilgan olur.
_URETIM_SONRASI = os.environ.get("NETARIS_URETIM_SONRASI") == "1"

# ASAMA AYRIMI ATIL OLABILIR -- IKI YONDEN, ikisi de sinaniyor.
#
# 1. `_URETIM_SONRASI` sabit False'a donerse kati iddia HIC kosmaz
#    ve sinama iki asamada da yesil doner.
# 2. Kapi bayragi cocuk ortamina GECIRMEZSE ayni sonuc olusur --
#    sinama kusursuz, kapi sessiz. Olcut: bayrak o dosyada hem
#    TANIMLI hem `env=` icinde KULLANILMIS olmali. (Yalnizca tanima
#    bakan iddia bu depoda mutasyonla KACTI.)
if os.environ.get("NETARIS_URETIM_SONRASI") == "1":
    esit(_URETIM_SONRASI, True, "asama bayragi gercekten okunuyor")

_KAPI = _BURASI.parent.parent / "site" / "cikti_sinamalari.py"
_kapi_k = _KAPI.read_text(encoding="utf-8", errors="replace")
esit("NETARIS_URETIM_SONRASI" in _kapi_k, True,
     "uretim sonrasi kapisi bayragi taniyor")
esit('ASAMA_DEGISKENI: "1"' in _kapi_k, True,
     "kapi bayragi cocuk ortamina geciriyor")
# BU DOSYA KAPININ SECIMINE GERCEKTEN GIRIYOR MU.
#
# Kapi sinamalari KAYNAKTAKI yol izine gore seciyor. Bu dosya
# "icerik" dizinine bakiyor; iz kaybolursa (yol bir sabite tasinirsa
# ornegin) dosya uretim sonrasi kosudan SESSIZCE duser ve kati iddia
# hic calismaz. Olcut, kapinin kendi listesini URETMESI.
sys.path.insert(0, str(_BURASI.parent.parent / "site"))
import cikti_sinamalari as _ks                             # noqa: E402

esit(pathlib.Path(__file__).resolve() in
     {p.resolve() for p in _ks.ciktiya_bakan()}, True,
     "bu dosya uretim sonrasi listede")


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

    # IDDIA ASAMAYA BAGLI -- ATILMADI, DOGRU YERE TASINDI.
    #
    # Ilk yazimda burada `esit(yarim, [])` vardi ve DAGITIMI
    # KILITLEDI (kosu #2665). Sebep tam olarak bu dosyanin konusu
    # olan tuzagin kendisi:
    #
    #   1. Sinamalar `calistir.py`den ONCE kosuyor.
    #   2. Bu sayfalari URETEN adim `calistir.py`nin icinde.
    #   3. Olay sayfalari her kosuda SIFIRDAN yeniden uretiliyor
    #      (olculdu: tek otomatik gonderi 231 analiz sayfasina
    #      dokundu ve elle yaptigim 303 satirlik onarimi geri aldi).
    #
    # Yani depodaki eski icerik, kendisini duzeltecek adimi
    # arkasinda birakip kilitliyordu. Iddia DOGRUYDU, yeri yanlisti.
    #
    # Garanti URETICININ kendisinde: 1-4. bolumler `_emsal_basligi`
    # ve `kelime_kirp` davranisini icerikten BAGIMSIZ sinar ve
    # mutasyonla olculdu. Uretici dogruysa yeniden uretilen her
    # sayfa dogru cikar; burada sayilan kalinti, o uretimin heniz
    # kosmadigi sayfalardir.
    #
    # URETIMDEN SONRA iddia KATI: o asamada sayfalar bu kosuda
    # yeniden uretilmis durumda, yani kalan her yarim kelime gercek
    # bir uretici kusurudur ve yayini durdurmasi DOGRUDUR.
    # `site/cikti_sinamalari.py` bu dosyayi zaten seciyor (kaynakta
    # hem "icerik" hem "netaris.db" gecıyor) ve bayragi cocuk
    # ortamina geciriyor.
    #
    # URETIMDEN ONCE yalnizca OLCUM: sayi basilir, cikis kodunu
    # etkilemez. Sifirdan uzaklasirsa ya uretici bozulmus ya da
    # yeniden uretilmeyen bir yol kalmis demektir.
    if _URETIM_SONRASI:
        esit(yarim[:5], [],
             f"URETIM SONRASI yarim kelimeyle biten emsal satiri:"
             f" {len(yarim)}")
    else:
        print(f"   olcum: yarim kelimeyle biten emsal satiri = {len(yarim)}"
              f" / {satirlar}")
        if yarim:
            print(f"          ornek: {yarim[0][0][:60]} {yarim[0][1]!r}")
else:
    print("   (depo verisi yok -- atlandi)")


print(f"\nGECTI={GECTI} KALDI=0")
