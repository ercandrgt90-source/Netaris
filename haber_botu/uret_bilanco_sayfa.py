"""Sirket basina bilanco analiz sayfasi -- olculmus tablo + AI yorumu.

    sektor_ozet.json -> Donem -> tablo (deterministik) -> AI yorumu -> sayfa

    python uret_bilanco_sayfa.py --sinir 3 --kuru-calis
    python uret_bilanco_sayfa.py            # kosu basina 60

YORUMSUZ SAYFA YAYIMLANMIYOR
----------------------------
Karar acik: "her bilanco yapay zeka yorumundan gececek". Yorum
uretilemezse (anahtar yok, model bos dondu, dogrulama dusurdu) o
sirket icin sayfa YAZILMIYOR. Yarim bir sayfa yayimlamak, sozu
tutmadigini sessizce ilan etmek olurdu.

TABLO DETERMINISTIK, YORUM MODELDEN
-----------------------------------
Sayfadaki her rakam `oranlar.py` ve `sektor_ozet.py` tarafindan
hesaplaniyor; model yalnizca onlari cumleye ceviriyor ve ciktisi
`yorumcu` tarafindan dogrulaniyor (girdide olmayan sayi -> metin
tamamen atilir).

SINIR VAR -- TOPLU URETIMDE DE
------------------------------
Kosu basina 60 sayfa. 324 sirket ~6 CI kosusunda tamamlaniyor.
Sinirsiz yapilmadi ve sebebi teknik: 324 model cagrisi tek bir CI
kosusuna sigmaz, is zaman asimina ugrar ve o kosuda uretilenlerin
HICBIRI yazilmaz. Sinirli kosu yarim kalsa bile yazdigini koruyor.

TEKRAR URETMIYOR: sayfasi zaten olan sirket atlaniyor. Hat yeniden
kosturuldugunda ayni sayfayi yeniden yazmak, ayni model cagrisini
ikinci kez odemek demek.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "kaynak"), str(_KOK / "analiz"),
                str(_KOK / "ai")]

import bicim              # noqa: E402
import bilanco_ag         # noqa: E402
import bilanco_yorum      # noqa: E402
import guvenlik           # noqa: E402
import oranlar            # noqa: E402
import sektor_ozet        # noqa: E402
import yayin              # noqa: E402

OZET = _KOK / "kaynak" / "sektor_ozet.json"
DEFTER = _KOK / "kaynak" / "sirketler.json"
SITE = _KOK.parent / "site" / "icerik" / "analizler"

#: Tek kosuda en fazla kac sayfa.
#:
#: TOPLU URETIM: 5'ten 60'a cikarildi. 324 sirket bu hizla ~6 CI
#: kosusunda (yaklasik uc saat) tamamlaniyor.
#:
#: SINIRSIZ YAPILMADI ve sebebi teknik: 324 model cagrisi TEK bir CI
#: kosusuna sigmaz, is zaman asimina ugrar ve o kosuda uretilen
#: sayfalarin hicbiri yazilmaz. Sinirli kosu, yarim kalsa bile
#: yazdigini KORUYOR -- her sirket kendi sayfasi yazilir yazilmaz
#: kaliciya geciyor.
#:
#: Sayfasi olan sirket atlandigi icin hat kendini adim adim
#: dolduruyor; kosu sayisi arttikca kalan is azaliyor.
VARSAYILAN_SINIR = 60

KALEMLER = (
    ("hasilat", "Hasılat"), ("brut_kar", "Brüt kâr"),
    ("faaliyet_kari", "Faaliyet kârı"), ("favok", "FAVÖK"),
    ("net_kar", "Net kâr"), ("ozkaynak", "Özkaynak"),
    ("aktif_toplami", "Aktif toplamı"), ("net_borc", "Net borç"),
    ("faaliyet_nakit_akisi", "Faaliyet nakit akışı"),
    ("yatirim_harcamasi", "Yatırım harcaması"),
)


def _mlr(d):
    return f"{bicim.sayi(d / 1e9, 2)} milyar TL" if d is not None else "—"


def _degisim(simdi, once) -> float | None:
    """Reel yuzde degisim. TMS 29 nedeniyle TUFE ile ARITILMIYOR.

    KAP tablolari enflasyon muhasebesine gore duzenleniyor; iki donem
    de RAPOR TARIHI alim gucuyle ifade ediliyor. Uzerine TUFE
    uygulamak ayni duzeltmeyi ikinci kez yapmak -- cift sayim olur.

    Payda sifira yakinsa oran anlamsiz buyur; None doner.
    """
    if simdi is None or once is None or abs(once) < 1e-6:
        return None
    return (simdi - once) / abs(once) * 100


def govde_kur(kod, unvan, sektor, donem, d, oran, medyan, n, yorum,
              once=None) -> str:
    """Sayfanin govdesi. TABLO deterministik, YORUM modelden."""
    s = []

    # OZET EN BASTA -- meta aciklama da buradan okunuyor.
    #
    # Onceden govde TABLOYLA basliyordu ve `_ozet_ayikla` ilk
    # paragraf olarak ham tabloyu aliyordu; arama sonucunda ve kart
    # ozetinde boru isaretleri gorunuyordu. Ozet bir CUMLE olmali.
    if yorum:
        s += ["## Özet", "", yorum, ""]

    # YILLIK DEGISIM -- SEVIYE DEGIL, HAREKET.
    #
    # Bu bolum olmadan sayfa yalnizca "hasilat 662 milyar TL"
    # diyebiliyordu. Okurun sordugu soru ise degisim. Onceki yil
    # AYNI CEKIMDEN geliyor, ek istek yok.
    #
    # Yoksa bolum HIC yazilmiyor -- bos bir tablo, veri oldugunu
    # sanmaya yol acar.
    if once is not None:
        satir = []
        for ad, etiket in KALEMLER:
            y = _degisim(getattr(d, ad, None), getattr(once, ad, None))
            if y is not None:
                satir.append(f"| {etiket} | {bilanco_yorum._yuzde(y)} |")
        if satir:
            s += [f"## {donem} — bir yıl öncesine göre", "",
                  "| Kalem | Reel değişim |", "| --- | ---: |", *satir, "",
                  "*Finansal tablolar TMS 29 enflasyon muhasebesine göre "
                  "düzenlenmiştir; yukarıdaki değişimler **reeldir**, "
                  "ayrıca enflasyondan arındırmak gerekmez.*", ""]

    s += [f"## {donem} dönemi ölçümleri", "",
         "| Kalem | Değer |", "| --- | ---: |"]
    for ad, etiket in KALEMLER:
        v = getattr(d, ad, None)
        if v is not None:
            s.append(f"| {etiket} | {_mlr(v)} |")

    if oran:
        s += ["", f"## Sektör içindeki konum", "",
              f"Karşılaştırma {sektor} sektöründeki {n} şirketin "
              f"**medyanına** göre yapılıyor. Medyan seçildi çünkü tek bir "
              f"şirketin uç değeri ortalamayı tek başına taşıyabiliyor.", "",
              "| Oran | Şirket | Sektör medyanı |", "| --- | ---: | ---: |"]
        for anahtar, ad in sektor_ozet.ORANLAR:
            v = oran.get(anahtar)
            if v is None:
                continue
            katsayi = anahtar in ("cari_oran", "borc_ozkaynak")
            b = ((lambda x: bicim.sayi(x, 2)) if katsayi
                 else bilanco_yorum._yuzde)
            m = medyan.get(anahtar)
            s.append(f"| {ad} | {b(v)} | {b(m) if m is not None else '—'} |")
        s += ["", "*Medyana göre konum bir sıralamadır, değerlendirme "
              "değildir. Hangi oranın yüksek olmasının iyi olduğu iş "
              "modeline göre değişir.*"]


    # YASAL UYARI GOVDEDE OLMAK ZORUNDA.
    #
    # OLCULDU, PAHALIYA MAL OLDU. 2026-08-20 kosusunda 277 sirket
    # `guvenlik: [YASAK] '(eksik)'` ile atlandi: `yayinlanabilir()`
    # uyariyi METNIN ICINDE ariyor, ben ise govdeye koymamistim.
    #
    # Haber tarafinda uyari sayfa sablonunun altbilgisinde duruyor ve
    # oradan geliyordu; bilanco govdesini SIFIRDAN ben kurdugum icin
    # o miras yoktu. Denetim dogru calisti, eksik olan govdeydi.
    #
    # Maliyeti sessiz degil GERCEKTI: 277 model cagrisi yapildi,
    # metinler uretildi ve HEPSI atildi. Uretimden SONRA yapilan bir
    # denetim, girdi maliyetini geri getirmiyor.
    #
    # Ayrica bu sayfa TAM OLARAK uyarinin gerekli oldugu yer: tek bir
    # sirketin mali tablosu, sektor siralamasiyla birlikte.
    s += ["", "---", "",
          "*Bu sayfa ölçülmüş mali tablo verisinden üretilmiştir ve "
          "**yatırım tavsiyesi değildir.** Sektör medyanına göre konum "
          "bir sıralamadır, değerlendirme değildir.*"]
    return "\n".join(s)


def sirket_isle(kod, bilgi, sektor, donem, oran, medyan, n,
                kuru=False) -> tuple[bool, str]:
    d, once, eksik = bilanco_ag.donem_getir(
        kod, donem, sektor_tr=sektor, ciftli=True)
    if d is None:
        return False, "eksik: " + ", ".join(eksik[:3])

    girdi = bilanco_yorum.girdi_kur(
        kod, bilgi["unvan"], sektor, donem, simdi=d, once=once,
        oranlar_kendi=oran, medyanlar=medyan, sirket_sayisi=n)

    metin, model, sebep, _ham = bilanco_yorum.yorum_uret(girdi)
    if not metin:
        # YORUMSUZ SAYFA YAYIMLANMIYOR -- bkz. modul basi.
        return False, f"yorum yok: {sebep}"

    govde = govde_kur(kod, bilgi["unvan"], sektor, donem, d, oran,
                      medyan, n, metin, once=once)

    tamam, bulgular = guvenlik.yayinlanabilir(govde)
    if not tamam:
        return False, f"güvenlik: {bulgular[0] if bulgular else '?'}"

    if kuru:
        return True, "kuru çalışma"
    yol = yayin.yaz_sektorel(
        govde=govde, sirket=bilgi["unvan"], kod=kod, donem=donem,
        sektor=sektor,
        kaynak="Çeyreklik mali tablolardan türetildi; sektör medyanı "
               "Netaris hesabı")
    return True, str(yol.name)


def _yayimlanmis() -> set[tuple[str, str]]:
    """Yayimlanmis (kod, donem) ciftleri -- ON BILGIDEN okunur.

    DOSYA ADINDAN OKUNMUYOR ve sebebi olculdu. Onceki surum
    `p.stem` tarayip `f"{kod}-{donem}"` damgasini ariyordu; ama
    `yayin.yaz_sektorel` dosyayi TERS sirada adlandiriyor:

        damga aranan : tera-2026-6
        dosya adi    : 2026-6-tera
        eslesme      : YOK

    Yani atlama HIC calismiyordu. Gorunur bir belirtisi de yoktu:
    hat sessizce ayni sirketi yeniden uretip AYNI MODEL CAGRISINI
    ikinci kez odeyecek, ustune ayni sayfayi ezecekti. 324 sirketlik
    toplu uretimde bu, kosu basina tekrarlanan bir maliyet demek.

    On bilgideki `kod:` ve `donem:` alanlari dosya adlandirma
    kuralindan BAGIMSIZ; adlandirma yarin degisse de bu okuma
    calisir.
    """
    if not SITE.exists():
        return set()
    cikti: set[tuple[str, str]] = set()
    for p in SITE.glob("*.md"):
        kod = donem = ""
        for satir in p.read_text(encoding="utf-8").splitlines()[:25]:
            if satir.startswith("kod:"):
                kod = satir[4:].strip().upper()
            elif satir.startswith("donem:"):
                donem = satir[6:].strip()
            elif satir == "---" and kod:
                break
        # YALNIZCA BILANCO DONEMLERI. Ayni klasorde makro analizler de
        # duruyor ve onlarin `donem` alani tarih ("2026-08-20"), kodu
        # da MAKRO/BTC/OLAY gibi. Bilanco donemi her zaman "YIL/AY"
        # bicimi; suzgec bu farka dayaniyor, ada degil.
        if kod and "/" in donem:
            cikti.add((kod, donem))
    return cikti


def _dokum(sebepler: dict[str, int]) -> None:
    """Atlama sebeplerini SIKLIGA gore dok.

    Ozet satiri "kac tane" diyor, bu "neden" diyor -- ve ilki tek
    basina yaniltici olabiliyor. "atlanan 325" hem "hepsi zaten
    yayimlanmis" hem "hicbiri uretilemedi" anlamina gelebilir;
    aralarindaki fark ise her sey demek.

    2026-08-20'de tam bu yasandi: kosu "yazilan 0, atlanan 325" ile
    bitti ve sebebi 325 satiri tek tek okumadan anlasilmadi.
    """
    if not sebepler:
        return
    print("sebep dökümü:")
    for tur, n in sorted(sebepler.items(), key=lambda x: -x[1]):
        print(f"  {n:>4}  {tur}")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sinir", type=int, default=VARSAYILAN_SINIR)
    a.add_argument("--sektor")
    a.add_argument("--kuru-calis", action="store_true")
    n = a.parse_args()

    # SAGLAYICI DURUMU EN BASTA, TEK SATIRDA.
    #
    # NEDEN VAR. 2026-08-20'de kosu "yazilan 0, atlanan 325" ile bitti
    # ve sebebi log'dan OKUNAMADI: ozet satiri kac sayfa yazildigini
    # soyluyor ama NEDEN yazilmadigini soylemiyordu. Sebebi ogrenmek
    # icin 325 satirin arasindan tek tek okumak gerekiyordu.
    #
    # "Ne oldu" ile "neden oldu" ayri sorular; ozet yalnizca ilkini
    # cevapliyordu. Simdi ikisi de basta yaziyor.
    #
    # DEGER DEGIL VARLIK yaziliyor. Anahtarin kendisi log'a asla
    # dusmemeli -- log'lar paylasilir, ekran goruntusu alinir.
    import os                                          # noqa: PLC0415
    sys.path.insert(0, str(_KOK / "ai"))
    import yorumcu                                     # noqa: PLC0415
    s = yorumcu.saglayici()
    if s:
        print(f"AI sağlayıcı: {s}")
    else:
        eksik = [ad for ad in ("ANTHROPIC_API_KEY", "CLOUDFLARE_API_TOKEN",
                               "CLOUDFLARE_ACCOUNT_ID")
                 if not os.environ.get(ad, "").strip()]
        print("AI sağlayıcı: YOK -- hiçbir sayfa yazılmayacak.")
        print(f"  tanımsız değişken: {', '.join(eksik)}")
        print("  (Anthropic için ANTHROPIC_API_KEY; ya da Workers AI "
              "için CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID)")

    # SABLON KAPISI -- TEK BIR MODEL CAGRISINDAN ONCE.
    #
    # NEDEN VAR. 2026-08-20'de govde yasal uyariyi icermiyordu ve 277
    # sirket `guvenlik: [YASAK]` ile atlandi. Ama once 277 MODEL
    # CAGRISI YAPILDI: metinler uretildi, odendi, sonra atildi.
    # Uretimden SONRA yapilan denetim girdi maliyetini geri getirmiyor.
    #
    # Kusur sirkete ozel degildi, SABLONA aitti -- yani ilk sirkette
    # de bellidir. Sahte bir govde kurup denetimden gecirmek, ayni
    # bilgiyi SIFIR maliyetle veriyor.
    #
    # Kapi kapaliysa hat DURUYOR. Devam etmek, bilerek para yakmak
    # olurdu.
    class _Sahte:
        hasilat = 1.0e9
        net_kar = 2.0e8
        ozkaynak = 5.0e8
        aktif_toplami = 9.0e8
        brut_kar = favok = faaliyet_kari = None
        net_borc = faaliyet_nakit_akisi = yatirim_harcamasi = None

    ornek = govde_kur("TEST", "Test A.Ş.", "Sanayi", "2026/6", _Sahte(),
                      {"net_marj": 20.0}, {"net_marj": 12.0}, 5,
                      "Örnek yorum cümlesi.")
    tamam, bulgular = guvenlik.yayinlanabilir(ornek)
    if not tamam:
        print("ŞABLON DENETIMDEN GEÇMIYOR -- hiç model çağrılmadı.")
        for b in bulgular[:3]:
            print(f"  {b.aciklama}")
        print("  Sebep şirkete özel değil, gövdeye ait; düzeltmeden "
              "çalıştırmak 325 çağrıyı boşa harcar.")
        return 1

    if not OZET.exists():
        print(f"{OZET} yok -- önce uret_bilanco.py çalışmalı.")
        return 1
    ozet = json.loads(OZET.read_text(encoding="utf-8"))
    defter = json.loads(DEFTER.read_text(encoding="utf-8"))["sirketler"]

    var = _yayimlanmis()

    yazilan = atlanan = 0
    # SEBEP SAYIMI. Ozetin altinda "hangi sebepten kac tane" yaziyor.
    # 325 satiri okumak yerine uc satir okunuyor; ve sebepler
    # SIRALANIYOR, en cok goruleni once.
    sebepler: dict[str, int] = {}
    for sektor, v in sorted(ozet.items()):
        if n.sektor and sektor != n.sektor:
            continue
        for kod, oran in sorted(v["sirket"].items()):
            if yazilan >= n.sinir:
                print(f"\nsınıra ulaşıldı ({n.sinir})")
                print(f"yazılan {yazilan}, atlanan {atlanan}")
                _dokum(sebepler)
                return 0
            bilgi = defter.get(kod)
            if not bilgi:
                continue
            # DONEME GORE ATLIYOR, SONSUZA DEK DEGIL.
            #
            # Once yalnizca koda bakiyordu: sirketin bir sayfasi varsa
            # bir daha HIC uretilmiyordu. Yeni ceyrek geldiginde de
            # atlanacakti -- yani "bir sonraki bilancolar" hic
            # yayimlanmazdi. Sessiz bir kilit: hata vermeden, hicbir
            # sey yapmadan.
            #
            # Artik kod VE donem birlikte, ON BILGIDEN araniyor
            # (bkz. `_yayimlanmis`).
            if (kod.upper(), v["donem"]) in var:
                atlanan += 1
                sebepler["zaten yayımlanmış"] = \
                    sebepler.get("zaten yayımlanmış", 0) + 1
                continue
            ok, not_ = sirket_isle(kod, bilgi, sektor, v["donem"], oran,
                                   v["medyan"], v["sirket_sayisi"],
                                   kuru=n.kuru_calis)
            if ok:
                yazilan += 1
                print(f"  {kod:<8}{not_}")
            else:
                atlanan += 1
                # Sebebi TURUNE gore topla: ":" sonrasi sirkete ozel
                # ayrinti (hangi kalem eksik), oncesi TUR. Ayrintiyi da
                # saysaydik 325 ayri "sebep" cikar ve dokum ozet olmaktan
                # cikip ikinci bir liste olurdu.
                sebepler[not_.split(":")[0].strip() or not_] = \
                    sebepler.get(not_.split(":")[0].strip() or not_, 0) + 1
                print(f"  {kod:<8}ATLANDI -- {not_}")

    print(f"\nyazılan {yazilan}, atlanan {atlanan}")
    _dokum(sebepler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
