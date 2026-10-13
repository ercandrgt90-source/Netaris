# -*- coding: utf-8 -*-
"""SEKTORU EKSIK SIRKET, HATTIN GORUS ALANINDA HIC YOK.

BU DOSYA NEDEN VAR
------------------
`uret_bilanco --hepsi` sektor listesini defterdeki `sektor_tr`
alanindan kuruyor. O alani olmayan sirket hicbir sektore dusmuyor --
kac kosu kosulursa kosulsun sayfasi URETILMIYOR.

Koddaki gerekce "cogu icin bu dogru ve kasitli -- fon, varant,
yatirim ortakligi" diyordu. YARISI DOGRUYDU.

OLCULDU (2026-10-13): defterdeki 794 sirketin 441'inde `sektor_tr`
yok. Bu 441'den rastgele 25 ornek kaynaga soruldu --

    sektoru BULUNAN      13   KONYA, OBAMS, LKMNH, OYYAT, GSRAY...
    gercekten sektorsuz  12   varlik kiralama, menkul degerler

Yani kabaca 230 GERCEK sirket yalnizca bir alan bos oldugu icin hic
yayimlanmiyordu. Kullanici "GSRAY'in bilancosu aciklandi, bizde ne
zaman cikar" diye sordugunda ortaya cikti: GSRAY da bu listedeydi
ve kaynakta sektoru VARDI (Iletisim).

EN ONEMLI KURAL -- "CEKILEMEDI" ILE "SEKTORU YOK" AYRI SEYLER
--------------------------------------------------------------
Ilk yazimda ikisi ayni sayiliyordu ve OLCUM YANILTTI: 40 sirketin
39'u "kaynakta yok" diye bildirildi, oysa hepsi HTTP 429 idi --
kaynak beni yavaslatiyordu. Ayni gun rastgele bir orneklem 25'te 13
sektor bulmustu.

Yanlis sayi tek basina zararsiz olabilirdi; asil tehlike KARARdi:
"kaynakta yok" diye isaretlenen bir sirket icin bir daha sorulmaz
ve hat onu sonsuza kadar gormezdi.

NE SINANIYOR
------------
1. Kaynak sektor verince deftere YAZILIYOR.
2. Kaynak sektor VERMEYINCE uydurulmuyor -- alan bos kaliyor.
3. Kaynak REDDEDINCE (429) "sektoru yok" sayilmiyor.
4. Ardisik redlerde kosu DURUYOR; kalan istekler yapilmiyor.
5. Kuru calismada deftere yazilmiyor.

AG KULLANILMIYOR: `sektor.cek` yerine sahte islev konuyor.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))
sys.path.insert(0, str(_KOK / "kaynak"))

import sektor                                      # noqa: E402
import sektor_tazele as st                         # noqa: E402

_gecti = 0


def esit(bulunan, beklenen, aciklama: str) -> None:
    global _gecti
    if bulunan != beklenen:
        print(f"  DUSTU  {aciklama}")
        print(f"    beklenen: {beklenen!r}")
        print(f"    gelen   : {bulunan!r}")
        raise SystemExit(1)
    _gecti += 1
    print(f"  gecti  {aciklama}")


def kur(sirketler, cevaplar, reddedilenler=()):
    """Gecici defter + sahte kaynak."""
    gecici = pathlib.Path(tempfile.mkdtemp()) / "sirketler.json"
    gecici.write_text(json.dumps({"sirketler": sirketler}, ensure_ascii=False),
                      encoding="utf-8")
    st.DEFTER = gecici
    sektor.OKUNAMAYAN.clear()

    def sahte(kod, istemci=None):
        if kod in reddedilenler:
            sektor.OKUNAMAYAN.append((kod, "HTTPStatusError"))
            return {}
        return cevaplar.get(kod, {})
    sektor.cek = sahte
    sektor.ARA_SN = 0
    return gecici


print("")
print("Sektor tazeleme")

# --- 1) BULUNAN SEKTOR DEFTERE YAZILIYOR -----------------------------
d = kur({"AAA": {"kod": "AAA"}, "BBB": {"kod": "BBB", "sektor_tr": "Sanayi"}},
        {"AAA": {"sektor": "Communication Services", "sektor_tr": "İletişim",
                 "alt_sektor": "Entertainment"}})
s = st.tazele(sinir=10)
esit(s["yazilan"], 1, "kaynakta sektoru olan sirket yaziliyor")
_def = json.loads(d.read_text(encoding="utf-8"))["sirketler"]
esit(_def["AAA"]["sektor_tr"], "İletişim", "dogru sektor yazildi")
esit(_def["BBB"]["sektor_tr"], "Sanayi", "zaten dolu olan degismedi")

# --- 2) SEKTOR YOKSA UYDURULMUYOR ------------------------------------
d = kur({"CCC": {"kod": "CCC"}}, {"CCC": {}})
s = st.tazele(sinir=10)
esit(s["yazilan"], 0, "sektoru olmayan sirkete uydurulmuyor")
esit(s["bos"], 1, "kaynakta yok diye sayiliyor")
esit("sektor_tr" in json.loads(d.read_text(encoding="utf-8"))["sirketler"]["CCC"],
     False, "alan bos birakiliyor")

# --- 3) RED (429) "SEKTORU YOK" DEGILDIR -----------------------------
# ILK YAZIMDA BU AYRIM YOKTU ve 40 sirketin 39'u yanlis bildirildi.
d = kur({"DDD": {"kod": "DDD"}}, {}, reddedilenler={"DDD"})
s = st.tazele(sinir=10)
esit(s["bos"], 0, "red, 'kaynakta yok' olarak SAYILMIYOR")
esit(s["hata"], 1, "red hata olarak sayiliyor")

# --- 4) ARDISIK REDDE KOSU DURUYOR -----------------------------------
kodlar = {f"R{i:02d}": {"kod": f"R{i:02d}"} for i in range(12)}
d = kur(kodlar, {}, reddedilenler=set(kodlar))
s = st.tazele(sinir=12)
esit(s["hata"], 5, "bes ardisik redde duruyor (12 degil)")

# --- 5) KURU CALISMA DEFTERE YAZMIYOR --------------------------------
d = kur({"EEE": {"kod": "EEE"}},
        {"EEE": {"sektor": "Industrials", "sektor_tr": "Sanayi"}})
s = st.tazele(sinir=10, kuru=True)
esit(s["yazilan"], 1, "kuru calismada da olcum yapiliyor")
esit("sektor_tr" in json.loads(d.read_text(encoding="utf-8"))["sirketler"]["EEE"],
     False, "kuru calismada deftere YAZILMIYOR")

print("")
print(f"TUM TESTLER GECTI ({_gecti})")
