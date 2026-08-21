"""Bilancodan ONE CIKAN BULGULAR -- deterministik, modelden degil.

    Donem + onceki yil + sektor medyani  ->  lehte / aleyhte bulgular

NEDEN "IYI / KOTU" DEGIL DE "LEHTE / ALEYHTE"
--------------------------------------------
Site kurali acik: "iyi", "guclu", "cazip", "riskli" gibi
DEGERLENDIRME sozcukleri yasak. Ama okurun sordugu soru gercek: bu
tabloda ne lehte, ne aleyhte isliyor?

Ikisini ayiran sey KAYNAK. Bir yargi kaynagini gostermez ("bu sirket
guclu"); bir bulgu gosterir ("faaliyet nakit akisi net karin %38'i").
Buradaki her madde OLCUMDEN turetiliyor ve olcumu YANINDA yaziyor --
okur ayni sonuca kendi ulasabilsin diye.

Yon bilgisi de yargi degil: hasilatin reel artmasi sirket LEHINE bir
gelismedir; bu, hisseyi alma tavsiyesi degildir. Iki cumle arasindaki
mesafe, bu modulun tamamini haklı cikaran mesafedir.

SEKTORE GORE BASTIRMA -- EN KRITIK KISIM
----------------------------------------
Ayni olcum her sektorde ayni anlama GELMIYOR:

  net borc / ozkaynak yuksek   -> bankada OLAGAN, sanayide dikkat
  cari oran 1'in altinda       -> perakendede OLAGAN (negatif isletme
                                  sermayesi), uretimde dikkat
  amortisman agirligi          -> telekomda OLAGAN

Bunlari her sektorde "aleyhte" saymak, `sektor_okuma.py`de yazdigimiz
seyle CELISIRDI: orada "bu olagandir" deyip burada eksi yazmak,
okuru kendi sayfamiz icinde celiskiye dusurur.

O yuzden bastirilan sinyaller SESSIZCE atlanmiyor, hic uretilmiyor:
BASTIRMA tablosu hangi sektorde hangi kuralin gecersiz oldugunu
ACIKCA yaziyor.

ESIKLER OLCULMUS DEGIL SECILMIS -- VE BU YAZILI
-----------------------------------------------
%5 marj degisimi, 0,8 nakit karsilama gibi esikler bir editoryal
secim. Uydurma bir kesinlik iddiasi olmasin diye hepsi burada, tek
yerde ve gerekcesiyle duruyor.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Reel degisimde "kayda deger" sayilan esik (yuzde).
#:
#: TMS 29 sonrasi rakamlar reel; yine de kucuk oynamalar olcum
#: gurultusu olabiliyor. %5 secildi cunku altindaki degisim tabloda
#: gorunse de okur icin bir sey ifade etmiyor.
ESIK_DEGISIM = 5.0

#: Marj degisiminde esik (puan). Marj zaten yuzde oldugu icin
#: degisimi PUAN olarak olculuyor -- "yuzde degisimin yuzdesi"
#: okunmaz bir sayidir.
ESIK_MARJ_PUAN = 2.0

#: Faaliyet nakit akisinin net kari karsilama orani.
#:
#: 0,8 ve 1,2 secildi: tam 1,0 esik yapilirsa 0,99 ile 1,01 farkli
#: sinifa duser ve bu fark gercek degildir.
NAKIT_ZAYIF = 0.8
NAKIT_GUCLU = 1.2

#: Sektor medyanindan sapma esigi (goreli, yuzde).
#: Medyana cok yakin bir deger "farklilik" sayilmamali.
ESIK_MEDYAN = 15.0

#: Medyan bu degerin altindaysa ORANSAL karsilastirma YAPILMIYOR.
#:
#: OLCULDU: ASELS sayfasinda "Ozkaynak karliligi %4,7; sektor medyani
#: %0,1" yaziyordu. Olcum dogruydu ama karsilastirma yaniltici:
#: medyan sifira yaklastikca oransal sapma sonsuza gidiyor ve
#: %4,7 ile %0,1 arasindaki fark "kirk yedi kat" gibi okunuyor.
#:
#: Sifira yakin bir medyan, sektorde cok sayida sirketin basabasa
#: yakin oldugunu gosteriyor -- yani karsilastirilacak bir orta nokta
#: YOK. Boyle bir durumda susmak, buyuk bir sayi yazmaktan dogru.
MEDYAN_TABANI = 1.0

#: KURAL -> o kuralin GECERSIZ oldugu sektorler.
#:
#: `sektor_okuma.py` bu sektorlerde "bu olagandir" diyor; burada eksi
#: yazmak kendi sayfamiz icinde celiski uretirdi.
BASTIRMA: dict[str, frozenset[str]] = {
    # Borclanmak bu is modellerinin kendisi ya da yapisal geregi.
    "borc": frozenset({"Finans", "Kamu hizmetleri", "İletişim",
                       "Gayrimenkul"}),
    # Negatif isletme sermayesi perakendede is modelinin bir ozelligi.
    "cari": frozenset({"Temel tüketim", "İsteğe bağlı tüketim",
                       "Finans"}),
    # Bankada "hasilat" ve "brut marj" sanayidekiyle ayni sey degil.
    "marj": frozenset({"Finans"}),
    # GYO'da net kar ile nakit akisi yapisal olarak ayrisir
    # (yeniden degerleme kari nakit uretmez).
    "nakit": frozenset({"Finans", "Gayrimenkul"}),
}


@dataclass(frozen=True)
class Bulgu:
    """Tek bir bulgu. `lehte` None ise notr -- sadece bilgi."""
    lehte: bool | None
    metin: str


def _bastirildi(kural: str, sektor: str) -> bool:
    return sektor in BASTIRMA.get(kural, frozenset())


def _yuzde(d: float, basamak: int = 1) -> str:
    """Turkce yuzde: isaret YUZDE ISARETINDEN once."""
    from bicim import sayi                             # noqa: PLC0415
    m = sayi(abs(d), basamak)
    return f"-%{m}" if d < 0 else f"%{m}"


def _degisim(simdi, once) -> float | None:
    if simdi is None or once is None or abs(once) < 1e-6:
        return None
    return (simdi - once) / abs(once) * 100


def _marj(kar, hasilat) -> float | None:
    if kar is None or not hasilat:
        return None
    return kar / hasilat * 100


def bulgular(d, once=None, oran=None, medyan=None,
             sektor: str = "") -> tuple[list[Bulgu], list[Bulgu]]:
    """(lehte, aleyhte) bulgu listeleri.

    Her bulgu OLCUMUNU yaninda tasiyor: okur ayni sonuca kendi
    ulasabilsin ve bize inanmak zorunda kalmasin.
    """
    cikti: list[Bulgu] = []
    oran = oran or {}
    medyan = medyan or {}

    # --- 1. HASILAT (reel) -------------------------------------
    y = _degisim(getattr(d, "hasilat", None), getattr(once, "hasilat", None))
    if y is not None and abs(y) >= ESIK_DEGISIM:
        cikti.append(Bulgu(y > 0, f"Hasılat reel olarak {_yuzde(y)} "
                                  f"{'arttı' if y > 0 else 'geriledi'}."))

    # --- 2. NET KAR (reel) -------------------------------------
    y = _degisim(getattr(d, "net_kar", None), getattr(once, "net_kar", None))
    if y is not None and abs(y) >= ESIK_DEGISIM:
        cikti.append(Bulgu(y > 0, f"Net kâr reel olarak {_yuzde(y)} "
                                  f"{'arttı' if y > 0 else 'geriledi'}."))

    # --- 3. BRUT MARJ (puan) -----------------------------------
    if not _bastirildi("marj", sektor) and once is not None:
        m1 = _marj(getattr(d, "brut_kar", None), getattr(d, "hasilat", None))
        m0 = _marj(getattr(once, "brut_kar", None),
                   getattr(once, "hasilat", None))
        if m1 is not None and m0 is not None:
            f = m1 - m0
            if abs(f) >= ESIK_MARJ_PUAN:
                from bicim import sayi                  # noqa: PLC0415
                cikti.append(Bulgu(
                    f > 0,
                    f"Brüt marj {sayi(abs(f), 1)} puan "
                    f"{'genişledi' if f > 0 else 'daraldı'} "
                    f"({_yuzde(m0)} → {_yuzde(m1)})."))

    # --- 4. KAR ILE NAKIT AKISI AYRISMASI ----------------------
    #
    # En cok bilgi tasiyan bulgu bu: kar buyurken nakit uretilmiyorsa
    # kar tahsil edilmemis demektir. Sektore gore bastiriliyor cunku
    # GYO'da bu ayrisma YAPISAL (deger artisi nakit uretmez).
    if not _bastirildi("nakit", sektor):
        nk = getattr(d, "net_kar", None)
        fna = getattr(d, "faaliyet_nakit_akisi", None)
        if nk and fna is not None and nk > 0:
            k = fna / nk
            from bicim import sayi                      # noqa: PLC0415
            if k < NAKIT_ZAYIF:
                cikti.append(Bulgu(
                    False, f"Faaliyet nakit akışı net kârın "
                           f"{_yuzde(k * 100, 0)} kadarı; kâr ile nakit "
                           f"üretimi ayrışıyor."))
            elif k >= NAKIT_GUCLU:
                cikti.append(Bulgu(
                    True, f"Faaliyet nakit akışı net kârın "
                          f"{sayi(k, 2)} katı; kâr nakde dönüyor."))

    # --- 5. BORCLULUK, SEKTORE GORE ----------------------------
    if not _bastirildi("borc", sektor):
        v, m = oran.get("borc_ozkaynak"), medyan.get("borc_ozkaynak")
        if v is not None and m is not None and abs(m) >= MEDYAN_TABANI:
            from bicim import sayi                      # noqa: PLC0415
            fark = (v - m) / abs(m) * 100
            if abs(fark) >= ESIK_MEDYAN:
                cikti.append(Bulgu(
                    fark < 0,
                    f"Net borç / özkaynak {sayi(v, 2)}; sektör medyanı "
                    f"{sayi(m, 2)}."))

    # --- 6. LIKIDITE, SEKTORE GORE -----------------------------
    if not _bastirildi("cari", sektor):
        v = oran.get("cari_oran")
        if v is not None:
            from bicim import sayi                      # noqa: PLC0415
            if v < 1.0:
                cikti.append(Bulgu(
                    False, f"Cari oran {sayi(v, 2)}; kısa vadeli "
                           f"yükümlülükler dönen varlıkları aşıyor."))
            elif v >= 1.5:
                cikti.append(Bulgu(
                    True, f"Cari oran {sayi(v, 2)}; dönen varlıklar "
                          f"kısa vadeli yükümlülüklerin üzerinde."))

    # --- 7. OZKAYNAK KARLILIGI, MEDYANA GORE -------------------
    v, m = oran.get("roe"), medyan.get("roe")
    if v is not None and m is not None and abs(m) >= MEDYAN_TABANI:
        fark = (v - m) / abs(m) * 100
        if abs(fark) >= ESIK_MEDYAN:
            cikti.append(Bulgu(
                fark > 0,
                f"Özkaynak kârlılığı {_yuzde(v)}; sektör medyanı "
                f"{_yuzde(m)}."))

    # --- 8. YATIRIM, NAKIT AKISINA GORE ------------------------
    #
    # NOTR birakildi ve sebebi onemli: yatirimin nakit akisini asmasi
    # ne iyi ne kotudur -- buyume donemindeki sirkette beklenen bir
    # sey, olgun sirkette dikkat gerektiren bir sey. Hangisi oldugunu
    # TABLO SOYLEMIYOR, o yuzden yon de atamiyoruz.
    fna = getattr(d, "faaliyet_nakit_akisi", None)
    capex = getattr(d, "yatirim_harcamasi", None)
    if fna is not None and capex is not None and capex > 0 and fna > 0:
        if capex > fna:
            cikti.append(Bulgu(
                None, "Yatırım harcaması faaliyet nakit akışını aşıyor; "
                      "aradaki fark dış kaynakla karşılanıyor."))

    lehte = [b for b in cikti if b.lehte is True]
    aleyhte = [b for b in cikti if b.lehte is False]
    notr = [b for b in cikti if b.lehte is None]
    # Notr bulgular ALEYHTE listesine degil, sonuna ekleniyor --
    # yonu olmayan bir bulguyu eksi hanesine yazmak yon atamak olur.
    return lehte, aleyhte + notr


def markdown(d, once=None, oran=None, medyan=None,
             sektor: str = "") -> list[str]:
    """Sayfaya eklenecek satirlar. Bulgu yoksa BOS liste.

    Bos liste onemli: bulgusuz bir "Öne çıkanlar" baslgi, okura
    bakilip bir sey bulunamadigini degil, bakilmadigini dusundurur.
    """
    lehte, aleyhte = bulgular(d, once, oran, medyan, sektor)
    if not lehte and not aleyhte:
        return []
    s = ["", "## Öne çıkan ölçümler", ""]
    if lehte:
        s += ["**Şirket lehine işleyenler**", ""]
        s += [f"- {b.metin}" for b in lehte] + [""]
    if aleyhte:
        s += ["**Dikkat gerektirenler**", ""]
        s += [f"- {b.metin}" for b in aleyhte] + [""]
    s += ["*Bu maddeler tablodaki ölçümlerden kural ile türetildi; "
          "her biri dayandığı rakamı taşıyor. Bir kalemin lehte ya da "
          "aleyhte sayılması sektöre göre değişir — bankada yüksek "
          "borçluluk olağandır, sanayide değil — ve bu ayrım "
          "uygulanmıştır.*", ""]
    return s
