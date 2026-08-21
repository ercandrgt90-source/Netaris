"""Yorumdaki her sayi SAYFADA gecmeli -- gecmiyorsa yorum dusuyor.

BULUNAN HATA
------------
Olculdu (2026-08-21): yayimdaki 291 yorumun 84'unde (%28) sayfada
HIC GECMEYEN sayi vardi. Ornek, Fed tutanaklari haberi:

    yorum : "yillik TUFE %31,75'e gerilerken cekirdek %29,91..."
    sayfa : ABD TUFE 3,36% / Cekirdek PCE 3,29% / ABD issizlik 4,10%

%31,75 Turkiye TUFE'si. ABD Fed haberinde Turkiye enflasyonu
yorumlanmis ve okur o sayiyi sayfada arayip bulamiyor.

KOK SEBEP: DOGRULAMA YANLIS SEYE BAKIYORDU
------------------------------------------
Dogrulama, modelin metnindeki sayilarin ISTEMDE (prompt) gecip
gecmedigine bakiyordu. Istem ile sayfa ayni sey degil: bir donem
`dosya.kur` yorum hattina bes Turkiye gostergesi veriyor, sayfa
hattina hic vermiyordu. Model istemdeki sayiyi kullanip dogrulamayi
geciyor, sayfa o sayiyi hic basmiyordu.

Yani dogrulama KAYNAGI denetliyordu, GORUNURLUGU degil. Okurun
yapabildigi tek kontrol ise gorunurluk: sayfada arar, bulamaz.

KURAL
-----
Olcut artik URETILMIS SAYFA. Bir sayi sayfada basilmiyorsa, nereden
geldigi onemsiz -- okur icin dogrulanamaz ve yayimda kalmamali.

Bu arac hem DENETLIYOR hem TEMIZLIYOR:
  (denetim)  ihlalleri sayar, cikis kodu 1 doner -- CI'da kirilir
  --temizle  ihlalli yorumlari depodan siler; sonraki uretim
             duzeltilmis girdiyle yeniden yazar
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sqlite3

KOK = pathlib.Path(__file__).resolve().parent.parent
VT = KOK / "haber_botu" / "netaris.db"
CIKTI = KOK / "site" / "cikti"

#: Ondalikli sayilar. Tam sayilar DISARIDA: "2026", "3 uye", "bir kac
#: hafta" gibi ifadeler olcum degil ve onlari aramak yanlis alarm
#: uretir. Olcumler bu sitede neredeyse her zaman ondalikli.
SAYI = re.compile(r"\d+[.,]\d+")


#: Yorum blogu. Sayfadan CIKARILIYOR -- asagiya bak.
#: Desen `denetim.py` ile AYNI olmali. Ilk yazimimda div/section
#: ariyordum ve HICBIR SEY eslesmiyordu -- blok aslinda bir <p>. Sonuc:
#: cikarma islemi hic calismadi ve kontrol yine vacuous kaldi. Iki
#: turda iki kez "0 ihlal" raporladim; ikisi de yanlisti.
_YORUM_BLOGU = re.compile(r'<p class="ai-metin">.*?</p>', re.S)


def sayfa_metni(yol: str) -> str | None:
    """Sayfanin metni -- YORUM BLOGU HARIC.

    ILK YAZIMIM VACUOUS BIR KONTROLDU.
    Yorumu cikarmadan kiyasliyordum, yani yorumdaki her sayi SAYFADA
    (yorumun kendi icinde) mutlaka bulunuyordu. Kontrol "bu sayi
    yorumda geciyor mu" sorusunu soruyordu ve cevap her zaman evet.

    Fark, `denetim.py`nin ayni kontrolu 10 ihlal bulup benimkinin 0
    bulmasiyla ortaya cikti. Iki arac ayni seye baktigini saniyordu.

    Dogru soru: sayi yorumun DISINDA, okurun bakabilecegi bir yerde
    geciyor mu. Gecmiyorsa okur dogrulayamaz ve iddia dayanaksiz.
    """
    p = CIKTI / yol.strip("/") / "index.html"
    if not p.exists():
        return None
    ham = p.read_text(encoding="utf-8", errors="replace")
    ham = _YORUM_BLOGU.sub(" ", ham)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", ham)).split())


def ihlaller(k: sqlite3.Connection) -> list[tuple[str, str, list[str]]]:
    r = k.execute(
        """SELECT a.adres, h.yayin_yolu, a.metin FROM ai_yorum a
             JOIN haber h ON h.adres = a.adres
            WHERE h.yayimlandi = 1 AND h.yayin_yolu IS NOT NULL""").fetchall()
    kotu = []
    for adres, yol, metin in r:
        sayfa = sayfa_metni(yol)
        if sayfa is None:
            # Sayfa henuz uretilmemis: bu bir ihlal DEGIL, bilgi
            # eksikligi. Uretilmemis sayfayi ihlal saymak, her temiz
            # kurulumda butun yorumlari silerdi.
            continue
        yok = sorted({s for s in SAYI.findall(metin) if s not in sayfa})
        if yok:
            kotu.append((adres, yol, yok))
    return kotu


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--temizle", action="store_true",
                    help="ihlalli yorumlari depodan sil")
    n = ap.parse_args()

    k = sqlite3.connect(VT)
    kotu = ihlaller(k)
    toplam = k.execute(
        """SELECT COUNT(*) FROM ai_yorum a JOIN haber h ON h.adres = a.adres
            WHERE h.yayimlandi = 1 AND h.yayin_yolu IS NOT NULL""").fetchone()[0]

    print(f"denetlenen yorum : {toplam}")
    print(f"ihlal            : {len(kotu)}")
    for _adres, yol, yok in kotu[:10]:
        print(f"  {', '.join(yok[:3]):<26} {yol}")
    if len(kotu) > 10:
        print(f"  ... {len(kotu) - 10} tane daha")

    if not kotu:
        print("\nHer yorumdaki her sayi sayfasinda geciyor.")
        return 0

    if not n.temizle:
        print("\nSilmek icin --temizle. Silinen yorum, sonraki uretimde"
              "\nduzeltilmis girdiyle yeniden yazilir.")
        return 1

    k.executemany("DELETE FROM ai_yorum WHERE adres = ?",
                  [(a,) for a, _y, _s in kotu])
    k.commit()
    print(f"\n{len(kotu)} yorum silindi -- yeniden uretilecek.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
