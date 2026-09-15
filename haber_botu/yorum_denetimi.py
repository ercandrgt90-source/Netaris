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
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analiz import baglam as _baglam  # noqa: E402

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

#: Ayni blok, ICERIGIYLE birlikte -- basilan yorumu okumak icin.
_YORUM_ICERIGI = re.compile(r'<p class="ai-metin">(.*?)</p>', re.S)

#: Sayi karsilastirmasi `denetim.py` ile AYNI anahtardan geciyor.
#:
#: Kopyalanmadi, ICE AKTARILDI ve sebebi olculdu: bu depoda "iki kod
#: yolu ayni karari veriyor" hatasi bes kez tekrarladi ve her seferinde
#: iki taraf zamanla ayristi. Ayrisma HATA VERMIYOR -- yalnizca iki
#: arac farkli sonuc raporluyor ve hangisinin dogru oldugu
#: anlasilmiyor. Karar TEK YERDE veriliyor.
from denetim import _sayi_anahtari  # noqa: E402


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


def sayfa_yorumu(yol: str) -> str | None:
    """Sayfada GERCEKTEN BASILAN yorum metni. Basilmamissa None.

    NEDEN DEPODAKI METIN YETMIYOR
    -----------------------------
    Olculdu (2026-08-24) ve site bir gun boyunca guncellenmedi:
    bu kapi 18 ihlal bulup cikis 1 donuyordu, `calistir.py` de
    `ok = False` yapip DAGITIMI HIC YAPMIYORDU. Bu arada CI haber
    toplamaya devam ediyordu -- haberler depoya akiyor, okura
    ulasmiyordu.

    On sekiz ihlalin ON ALTISI sayfada HIC BASILMAYAN yorumlardi.
    `insa.py` onlari zaten eliyor ("... yorum sayfada karsiligi
    olmayan sayi tasidigi icin BASILMADI"). Yani kapi, okurun
    goremedigi bir metin yuzunden butun siteyi durduruyordu.

    Kalan ikisi de sahteydi:
      * biri ayrac farkiydi (sayfa "15,000 feet", yorum "15.000"),
      * digerinde DEPODAKI metin eskiydi: depo "0,85 / 14.637",
        sayfada basilan yorum ise "0,21 / 13.827" diyordu.

    Ortak sebep tek: kapi yorumu DEPODAN, sayilari SAYFADAN okuyordu.
    Iki ayri kaynak, ayni soru. Bu dosyanin kendi kurali zaten
    "olcut URETILMIS SAYFA" diyordu; kural sayilar icin uygulanmis,
    METIN icin uygulanmamisti.

    DOGRU ILISKI
    ------------
    Eleyici `insa.py`de karar verir, bu kapi URETILEN SAYFAYI
    dogrular. Eleyicide bir delik varsa kapi onu yakalar ve dagitimi
    durdurur -- ki asil isi bu. Eleyici dogru calistiginda ise kapi
    sifir bulur ve haber akisi kesilmez.
    """
    p = CIKTI / yol.strip("/") / "index.html"
    if not p.exists():
        return None
    e = _YORUM_ICERIGI.search(p.read_text(encoding="utf-8", errors="replace"))
    if not e:
        return None
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", e.group(1))).split())


def ihlaller(k: sqlite3.Connection) -> list[tuple[str, str, list[str]]]:
    """Iki ayri soru, tek kapi.

      1. DOGRULANABILIRLIK -- sayi sayfada geciyor mu?
      2. BAGLAM            -- sayi BU HABERE ait mi?

    Ikincisi olmadan birincisi yetersiz: Fed tutanaklari sayfasindaki
    %31,75 gercek bir sayiydi (TCMB TUFE serisi) ve sayfada da vardi --
    yalnizca yanlis haberdeydi. Ilk kontrol onu "uygun" sayiyordu.
    """
    r = k.execute(
        """SELECT a.adres, h.yayin_yolu, a.metin,
                  COALESCE(h.baslik_kaynak, h.baslik_tr, ''), h.kurum,
                  h.sayfa_veri
             FROM ai_yorum a JOIN haber h ON h.adres = a.adres
            WHERE h.yayimlandi = 1 AND h.yayin_yolu IS NOT NULL""").fetchall()
    kotu = []
    for adres, yol, depo_metni, baslik, kurum, _sayfa_veri in r:
        # OLCUT: OKURUN GORDUGU METIN.
        #
        # Sayfa henuz uretilmemisse bu bir ihlal DEGIL, bilgi
        # eksikligi -- uretilmemis sayfayi ihlal saymak her temiz
        # kurulumda butun yorumlari silerdi.
        #
        # Sayfa uretilmis ama yorum BASILMAMISSA da ihlal yok:
        # `insa.py` onu zaten elemis, okura ulasan bir iddia yok.
        # Var olmayan bir metni ihlal sayip dagitimi durdurmak,
        # tam olarak sitenin bir gun donmasina yol acan hataydi.
        metin = sayfa_yorumu(yol)
        if metin is None:
            continue
        del depo_metni
        # KESIK CEVAP -- cumle bitiricisiyle bitmiyor.
        #
        # Olculdu: yayimdaki 168 yorumun 36'si yarim cumleyle
        # bitiyordu ("...yen borclanip baska varliklara yatirilan").
        # Sebep uretimde jeton tavani; kural oraya da kondu ama
        # YAYIMDAKILER temizlenmeli.
        #
        # Yarim cumle yayimlamak hic yayimlamamaktan kotudur: okur
        # eksigi gorur ve sayfanin geri kalanina da guvenmez.
        if not metin.rstrip().endswith((".", "!", "?", "…", '."', ".)")):
            kotu.append((adres, yol, ["KESIK: cümle bitmiyor"]))
            continue
        # HABERIN KENDI METNI DE GECILIYOR.
        #
        # Bu denetim bulduklarini SILIYOR. Kontrol yanlis alarm
        # verdiginde yayimlanmis DOGRU yorumlar siliniyordu: metindeki
        # sayi cogu zaman haberin kendi ozetinden geliyor, bizim
        # serimizden degil (olculdu 2026-09-15, yanlis alarm %53).
        _ozet = ""
        try:
            import json as _json                       # noqa: PLC0415
            _ozet = (_json.loads(_sayfa_veri or "{}") or {}).get("ozet", "")
        except (TypeError, ValueError):
            _ozet = ""
        uy = _baglam.uyusmazlik(k, metin, baslik, kurum or "", "",
                                haber_metni=f"{baslik} {_ozet}")
        if uy:
            kotu.append((adres, yol, [f"BAGLAM: {uy['aciklama']}"]))
            continue
        sayfa = sayfa_metni(yol)
        if sayfa is None:
            # Sayfa henuz uretilmemis: bu bir ihlal DEGIL, bilgi
            # eksikligi. Uretilmemis sayfayi ihlal saymak, her temiz
            # kurulumda butun yorumlari silerdi.
            continue
        # ALT DIZE DEGIL, TAM SAYI KARSILASTIRMASI.
        #
        # `"9,5" in sayfa` yaziyordu ve sayfadaki "$95,29" icinde
        # eslesiyordu -- yani var olmayan bir sayi "dogrulandi" sayildi.
        # Olculdu: `denetim.py` uc ihlal bulurken bu arac SIFIR
        # buluyordu ve fark tam buydu.
        #
        # Bu, ayni aracin UCUNCU kusuru (once yorumu sayfadan
        # cikarmiyordu, sonra yanlis etiketi ariyordu). Ortak sebep:
        # metin uzerinde calisip TOKEN uzerinde calismamak.
        # AYRAC ALISKANLIGI SAYIYI DEGISTIRMEZ.
        #
        # Olculdu: "15.000" ihlal sayildi, oysa sayfa ayni sayiyi
        # Ingilizce kaynak alintisinda "15,000 feet" diye basiyordu.
        # Ingilizce besleme sayisi arttikca (2026-08-24'te yedi resmi
        # kaynak eklendi) bu her kosuda tekrarlar ve her seferinde
        # dagitimi durdururdu.
        sayfa_sayilari = {_sayi_anahtari(s) for s in SAYI.findall(sayfa)}
        yok = sorted({s for s in SAYI.findall(metin)
                      if _sayi_anahtari(s) not in sayfa_sayilari})
        if yok:
            kotu.append((adres, yol, yok))
    return kotu


def elenenler(k) -> list[tuple[str, str]]:
    """Sayfasi VAR ama yorumu BASILMAMIS kayitlar -- (adres, yol).

    NEDEN AYRI BIR KATEGORI
    -----------------------
    `insa.py` sayfada karsiligi olmayan sayi tasiyan yorumu ELIYOR ve
    bu dogru: okur, yorumda gordugu rakami sayfada bulamamali.

    Ama elenen yorum DEPODA KALIYOR ve `uret_ai_yorum` "bu adresin
    yorumu var" deyip bir daha uretmiyor. Sonuc sessiz bir kilit:
    sayfa KALICI olarak yorumsuz kaliyor, hicbir yerde kirmizi
    yanmiyor.

    Olculdu (2026-09-15): 110 sayfa bu durumda. 97'si Jeopolitik ve
    sayfalarinda hicbir veri yok (ozet yok, acilis basilmiyor, bulgu
    ve gosterge sifir). Yorumlar 22-27 Agustos'ta, girdinin daha genis
    oldugu donemde uretilmisti; icerikleri sayfayla artik ortusmuyor.

    Bazilari ayrica LISANSSIZ endeks degeri tasiyor:

        "S&P 500'un 20 Agustos 2026 kapanisindaki 7641,16 seviyesi..."

    Yayimlanmiyorlar -- render suzgeci onlari zaten dusuruyor -- ama
    depoda durmalarinin da bir faydasi yok.

    TEMIZLIK NEDEN DONGU YARATMIYOR
    -------------------------------
    `uret_ai_yorum.secilenler` adayligi "anlatacak olculmus bir sey
    var mi" olcutune bagliyor: ozet, acilis, bulgu ya da Turkiye
    paneli. Bu sayfalarda hicbiri yok, yani silinen kayit ADAY
    OLARAK GERI GELMIYOR ve ikinci bir model cagrisi olusmuyor.

    IHLAL DEGIL: cikis kodunu etkilemiyor. Bu kapi bir kez butun
    siteyi durdurmustu (2026-08-24, 18 ihlalin 16'si tam bu
    kategoriydi) ve dersi kodda yazili -- okurun goremedigi bir metin
    yayini durdurmamali.
    """
    cikti: list[tuple[str, str]] = []
    for adres, yol in k.execute(
            """SELECT a.adres, h.yayin_yolu FROM ai_yorum a
                 JOIN haber h ON h.adres = a.adres
                WHERE h.yayimlandi = 1 AND h.yayin_yolu IS NOT NULL"""):
        if sayfa_yorumu(yol) is not None:
            continue
        # SAYFA GERCEKTEN VAR MI: uretilmemis sayfayi "elenmis"
        # saymak, her temiz kurulumda butun yorumlari silerdi.
        p = CIKTI / yol.strip("/") / "index.html"
        if p.exists():
            cikti.append((adres, yol))
    return cikti


def denetlenen_sayisi(k: sqlite3.Connection) -> int:
    """Sayfada GERCEKTEN basilmis, yani denetlenebilen yorum sayisi.

    NEDEN AYRI RAPORLANIYOR
    -----------------------
    Bu arac iki kez VACUOUS calisti ve iki kez "0 ihlal" dedi -- ikisi
    de yanlisti (bkz. `sayfa_metni` ve `_YORUM_BLOGU` notlari). Her
    ikisinde de ekranda gorunen sey ayniydi: buyuk bir "denetlenen"
    sayisi ve sifir ihlal.

    O sayi depodan geliyordu ve kontrolun gercekte kac yorumu
    okudugunu SOYLEMIYORDU. Artik iki sayi da basiliyor: depoda kac
    yorum var ve bunlarin kaci sayfada basilmis. Ikisi arasindaki
    ucurum, eleyicinin fazla agresif oldugunu ya da kontrolun bosa
    dustugunu ANINDA gosterir.
    """
    n = 0
    for (yol,) in k.execute(
            """SELECT h.yayin_yolu FROM ai_yorum a
                 JOIN haber h ON h.adres = a.adres
                WHERE h.yayimlandi = 1 AND h.yayin_yolu IS NOT NULL"""):
        if sayfa_yorumu(yol) is not None:
            n += 1
    return n


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

    basili = denetlenen_sayisi(k)
    print(f"depodaki yorum   : {toplam}")
    print(f"sayfada basilan  : {basili}   <- DENETLENEN")
    print(f"ihlal            : {len(kotu)}")
    _elenen = elenenler(k)
    print(f"elenmis (kilitli): {len(_elenen)}"
          + ("   <- sayfa kalici olarak yorumsuz" if _elenen else ""))
    if toplam and not basili:
        # Sifir basili yorum + sifir ihlal = kontrol HICBIR SEY
        # olcmuyor demek. Bu arac iki kez tam bu durumda "temiz"
        # raporladi. Sessiz gecilmemeli.
        print("\n  UYARI: hicbir yorum sayfada basilmamis -- bu kontrol")
        print("  su an HICBIR SEY olcmuyor. Once `site/insa.py` kosun.")
    for _adres, yol, yok in kotu[:10]:
        print(f"  {', '.join(yok[:3]):<26} {yol}")
    if len(kotu) > 10:
        print(f"  ... {len(kotu) - 10} tane daha")

    # ELENENLERIN TEMIZLIGI -- IHLAL DEGIL.
    #
    # `insa.py` sayfada karsiligi olmayan sayi tasiyan yorumu eliyor
    # ve bu dogru. Ama elenen yorum DEPODA KALIYOR ve
    # `uret_ai_yorum` "bu adresin yorumu var" deyip bir daha
    # uretmiyor: sayfa KALICI olarak yorumsuz kaliyor.
    #
    # Cikis kodunu ETKILEMIYOR. Bu kapi bir kez butun siteyi
    # durdurmustu (2026-08-24) ve dersi yukarida yazili: okurun
    # goremedigi bir metin yayini durdurmamali.
    if _elenen and n.temizle:
        k.executemany("DELETE FROM ai_yorum WHERE adres = ?",
                      [(a,) for a, _y in _elenen])
        k.commit()
        print(f"{len(_elenen)} elenmis yorum depodan silindi.")
    elif _elenen:
        print("Silmek icin --temizle. Bu kayitlar sayfaya HIC "
              "ulasmiyor;\ndepoda durmalari yalnizca yeniden "
              "uretimi engelliyor.")

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
