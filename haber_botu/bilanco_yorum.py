"""Bilanco icin AI yorumu -- olculmus kalemlerden cikarim.

    Donem + sektor medyani  ->  girdi metni  ->  yorumcu  ->  dogrulama

TEMEL KURAL, HABER TARAFIYLA AYNI
---------------------------------
MODEL RAKAM BULMAZ, VERILEN RAKAMI CUMLEYE CEVIRIR.

Butun sayilar `oranlar.py` ve `sektor_ozet.py` tarafindan
deterministik hesaplaniyor; modelin isi onlari baglama oturtmak.
Bu ayrim uydurmayi KAPATIYOR -- modelin arayacagi bir sey yok. Ayni
`ai/yorumcu.sayi_denetimi` ciktidaki her sayinin girdide de gectigini
dogruluyor; gecmiyorsa metin TAMAMEN atiliyor.

SEKTOR MEDYANI GIRDIYE GIRIYOR ama YARGI OLARAK DEGIL.
Medyan bir OLCUM; "sektorun uzerinde" bir SIRALAMA. Hangi oranin
yuksek olmasinin iyi oldugu is modeline gore degisir, o yuzden
yonerge modele "daha iyi / guclu / cazip" dedirtmiyor.

NEDEN AYRI YONERGE
------------------
Haber yonergesi "en onemli tek OLCUMU sec" diyor; bilancoda on bes
kalem var ve hepsi olculmus. Burada istenen sey farkli: KALEMLER
ARASINDAKI ILISKIYI kurmak -- kar artarken nakit akisi dusuyorsa
onu soylemek.
"""

from __future__ import annotations

import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bicim           # noqa: E402
import sektor_ozet     # noqa: E402

SISTEM = """Sen bir finans veri editörüsün. Sana bir şirketin ÖLÇÜLMÜŞ
bilanço kalemleri ve sektörünün medyanları veriliyor.

GÖREV: Rakamları TEKRARLAMA. Okur onları tabloda zaten gördü. Sen
kalemler ARASINDAKİ İLİŞKİYİ kur: hangi kalem hangisiyle birlikte
hareket ediyor, biri artarken diğeri neden düşüyor.

KURALLAR — hepsi zorunlu:
- YALNIZCA sana verilen sayıları kullan. Yeni sayı, oran ya da tarih
  EKLEME.
- Sayıyı VERİLDİĞİ ANLAMDA kullan. Marj yüzdedir, oran katsayıdır;
  karıştırma.
- DEĞERLENDİRME YAPMA. "İyi", "güçlü", "zayıf", "cazip", "riskli",
  "başarılı" gibi sözcükler YASAK. Sektör medyanına göre konum bir
  SIRALAMADIR, yargı değil — hangi oranın yüksek olmasının iyi olduğu
  iş modeline göre değişir.
- Tahmin, öngörü, yatırım tavsiyesi YASAK.
- Hedef fiyat, olasılık, "alım fırsatı" YASAK.
- Süren eğilim iddiası YASAK. Elinde iki dönem var; "artıyor" değil
  "arttı" yaz.
- EN FAZLA 3 CÜMLE. Madde işareti yok, tek paragraf.
- Türkçe yaz. Yüzde işareti sayıdan ÖNCE gelir: %19,3. Ondalık ayracı
  virgüldür."""


def _sayi(d, basamak=2, birim=""):
    return f"{bicim.sayi(d, basamak)}{birim}" if d is not None else None


def _yuzde(d, basamak=1) -> str:
    """Turkce yuzde: isaret YUZDE ISARETINDEN ONCE.

    Ilk yazimda "%-0,7" cikiyordu; dogrusu "-%0,7". Sitenin kendi
    bicim kurali yuzde isaretini sayidan ONCE koyuyor ve eksi de
    sayinin degil IFADENIN onune geliyor. Modelin girdisinde bozuk
    bicim gormesi, ciktida da bozuk bicim uretmesi demek.
    """
    m = bicim.sayi(abs(d), basamak)
    return f"-%{m}" if d < 0 else f"%{m}"


def girdi_kur(kod: str, unvan: str, sektor_tr: str, donem_etiketi: str,
              simdi, once=None, oranlar_kendi=None,
              medyanlar=None, sirket_sayisi=0) -> str:
    """Modele gidecek metin -- SAYFADA NE VARSA O.

    Girdi sayfanin kendisinden turetiliyor. Ikisi ayri kaynaktan
    gelseydi metin sayfada OLMAYAN bir seyi anlatabilirdi ve okur
    dogrulayamazdi.
    """
    p = [f"Şirket: {unvan} ({kod})",
         f"Sektör: {sektor_tr or 'bilinmiyor'}",
         f"Dönem: {donem_etiketi}"]

    ALAN = (("hasilat", "Hasılat"), ("brut_kar", "Brüt kâr"),
            ("faaliyet_kari", "Faaliyet kârı"), ("favok", "FAVÖK"),
            ("net_kar", "Net kâr"), ("ozkaynak", "Özkaynak"),
            ("aktif_toplami", "Aktif toplamı"),
            ("net_borc", "Net borç"),
            ("faaliyet_nakit_akisi", "Faaliyet nakit akışı"),
            ("yatirim_harcamasi", "Yatırım harcaması"))
    for ad, etiket in ALAN:
        d = getattr(simdi, ad, None)
        if d is None:
            continue
        satir = f"{etiket}: {_sayi(d / 1e9)} milyar TL"
        # ONCEKI DONEM VARSA DEGISIM DE VERILIYOR -- model kendisi
        # hesaplamasin diye. Hesap bizim, cumle onun.
        eski = getattr(once, ad, None) if once else None
        if eski:
            satir += f" (önceki dönem {_sayi(eski / 1e9)} milyar TL)"
        p.append(satir)

    for anahtar, ad in sektor_ozet.ORANLAR:
        d = (oranlar_kendi or {}).get(anahtar)
        if d is None:
            continue
        katsayi = anahtar in ("cari_oran", "borc_ozkaynak")
        bicimle = (lambda x: bicim.sayi(x, 2)) if katsayi else _yuzde
        satir = f"{ad}: {bicimle(d)}"
        m = (medyanlar or {}).get(anahtar)
        if m is not None:
            # MEDYAN OLCUM OLARAK veriliyor, yargi olarak degil.
            satir += (f" (sektör medyanı {bicimle(m)},"
                      f" {sirket_sayisi} şirket)")
        p.append(satir)

    return "\n".join(p)


def yorum_uret(girdi: str):
    """Yorumcuyu cagirir. Anahtar yoksa (girdi, "", sebep) doner.

    Anahtar YOKKEN sessizce bos yorum yazmiyoruz: sebep raporlaniyor,
    cunku "yorum uretilmedi" ile "yorum bos" ayri seyler.
    """
    import yorumcu                                   # noqa: PLC0415
    return yorumcu.uret(SISTEM, girdi)
