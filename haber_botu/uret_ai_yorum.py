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

import besleme    # noqa: E402
import bicim      # noqa: E402
import beyin      # noqa: E402
import dosya      # noqa: E402
import olay       # noqa: E402
import yorumcu    # noqa: E402
import baglam as _baglam   # noqa: E402  (analiz/ yolda)

GUNDEM = _KOK.parent / "site" / "icerik" / "gundem.json"

#: Bir calistirmada en fazla kac yorum.
#:
#: 12 -> 40. Eski deger bir ONLEMDI, olcum degil: "ucretsiz kotayi tek
#: seferde bitirmemek".
#:
#: OLCULDU (2026-09-14):
#:   * kosuda 391 aday vardi, 12'si yorumlaniyordu -- 32 kat kisit;
#:   * yorumlanabilir 2355 haberin yalnizca %26'sinda yorum vardi;
#:   * Cloudflare'dan BUGUNE KADAR HIC kota ya da oran hatasi
#:     alinmamisti, yani onlem hic sinanmamis bir tahmine dayaniyordu;
#:   * yorum basina sure ~4 sn (12 cagri 38-49 sn). 40 yorum ~160 sn,
#:     is akisinin 25 dakikalik butcesi icinde rahat.
#:
#: Yukseltmeyi guvenli kilan sey `yorumcu` tarafindaki kota kesicisi:
#: kota dolarsa kalan adaylar icin istek YAPILMIYOR, sebep adiyla
#: yaziliyor ve kosu temiz bitiyor. Gercek tavan tahmin edilmiyor,
#: veriden OKUNUYOR.
#:
#: Adaylar olay siddetine gore sirali: kota biterse once onemli haber
#: yorumlanmis olur.
VARSAYILAN_SINIR = 40

SEMA = """
CREATE TABLE IF NOT EXISTS ai_yorum (
  adres       TEXT PRIMARY KEY,
  metin       TEXT NOT NULL,
  saglayici   TEXT NOT NULL,
  model       TEXT NOT NULL,
  kayit_ani   TEXT NOT NULL
);

-- RET KAYDI.
--
-- Ilk calistirmada 9 yorumun 9'u reddedildi ve sebep YALNIZCA gunluge
-- yazildigi icin depodan taniyamadim. Ret sebebi en az uretilen metin
-- kadar degerli: hangi kural kac kez tutuyor, model mi uyduruyor yoksa
-- saglayici mi erisilemiyor -- bunlar olculmeden yorumcu
-- iyilestirilemez.
CREATE TABLE IF NOT EXISTS ai_ret (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  adres       TEXT NOT NULL,
  baslik      TEXT NOT NULL DEFAULT '',
  neden       TEXT NOT NULL,
  model       TEXT NOT NULL DEFAULT '',
  -- Modelin dondugu metin. Reddedilse de saklaniyor: "neden
  -- reddedildi" sorusunu ancak metne bakarak cevaplayabiliriz.
  ham         TEXT NOT NULL DEFAULT '',
  kayit_ani   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ai_ret_neden ON ai_ret(neden);
"""


def haberin_kendi_metni(h: dict) -> str:
    """Haberin KENDI sozleri -- baslik ve ozet. Bizim ekledigimiz veri degil."""
    return " ".join(str(h.get(k) or "") for k in
                    ("baslik", "baslik_kaynak", "ozet"))


def anlatacak_veri_yok(b, girdi: str, h: dict) -> bool:
    """Bu habere model cagirmak BOSA gider mi.

    Kosul IKISI BIRDEN:
      * haberin KENDI olcumu yok (ozet bos ya da sayisiz), VE
      * elimizdeki veri baska bir ulkeye ait.

    O zaman modele verilen tek sayi yabanci oluyor; model onu
    kullaniyor ve ardindan baglam kapisi "yalnizca X verisi aniyor"
    diye REDDEDIYOR. Hat kendi kendisiyle celisiyor: baska secenek
    birakmadigi bir seyi cezalandiriyor.

    Olculdu (2026-09-15): 40 adayin 15'i tam boyleydi --

        Haber : Guangzhou Automobile hissesi neden yukseliste?
        Kaynak: Investing.com Turkiye          (haber_ulkesi = TR)
        Acilis: ABD 10 yillik tahvil getirisi %4,96

    Gunun 340 reddinin 259'u baglam kapisindandi.

    NEDEN VERIYI AYIKLAYIP "OLCUMSUZ" YONERGESINE DUSURMUYORUZ
    ---------------------------------------------------------
    Denendi ve olculdu: 15'inin 15'i olcumsuz kaliyor. Yani geriye
    yalnizca baslik kaliyor ve modelden mekanizma istemek, ozeti bile
    olmayan bir baslikdan cikarim uydurtmak olurdu. O doldurmadir.

    KENDI OLCUMU OLAN HABER BU KAPIYA TAKILMIYOR: kendi rakamini
    anlatabilir ve baglam kontrolu (haber_metni ile) onu zaten dogru
    degerlendiriyor.
    """
    # GIRDI HIC OLUSMADIYSA da anlatacak sey yoktur.
    #
    # `yorumla` bunu zaten reddediyor ve MODEL CAGIRMIYOR -- yani
    # maliyeti yok. Ama iki seye mal oluyordu: kota yuvasi harciyordu
    # ve model hatasi OLMADIGI halde `ai_ret`e "red" olarak
    # yaziliyordu, yani red istatistiklerini sisiriyordu. Bu oturumda
    # hattin teshisi tam da o istatistiklere dayandi.
    #
    # Esik `yorumcu.EN_AZ_GIRDI`den okunuyor, kopyalanmiyor.
    if len(girdi) < yorumcu.EN_AZ_GIRDI:
        return True
    kendi = haberin_kendi_metni(h)
    # `olcum_var` GIRDI BICIMINI bekliyor ("Veri:", "Gosterge:",
    # "Acilis:" onekli satirlar). Ham ozeti dogrudan vermek her zaman
    # False donduruyordu -- yani bu kosul hic calismiyordu ve kapi
    # kendi olcumu OLAN haberleri de atliyordu. Mutasyon sinamasi
    # yakaladi: korumayi kaldirmak hicbir sinamayi kirmamisti.
    #
    # Ayni kural ikinci kez yazilmiyor: ozet, girdideki "Veri:"
    # satirinin ta kendisi; oyle sarilip ayni olcute veriliyor.
    if yorumcu.olcum_var(f"Veri: {kendi}"):
        return False
    return _baglam.uyusmazlik(
        b, girdi, h.get("baslik_kaynak") or h.get("baslik", ""),
        h.get("kurum", ""), h.get("bolge", ""),
        haber_metni=kendi) is not None


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
    # HABERIN KENDI OLCUMU VAR MI?
    #
    # Dosyanin bulgulari HABERE degil KONUSUNA ait. Olcumu olmayan bir
    # habere onlari gondermek, modele anlatacak tek sayiyi vermek
    # demek -- ve model onu anlatiyor. Olculdu, ana sayfada yan yana
    # yayimlandi: "Yemen'de Mocha limanina saldiri", "Iran
    # cumhurbaskani Hamaney'le gorustu" ve "Axios roportaji"
    # haberlerinin UCU DE ayni cumleyle basladi -- "Brent petrolun
    # kapanis fiyati 88,90 $...". Ucu de ayni jeopolitik dosyaya bagli
    # ve o dosyadaki tek sayi Brent'ti.
    #
    # Cozum bulgulari kaldirmak degil, OLCUMU OLMAYAN HABERE
    # gondermemek: o durumda `olcum_var` False donuyor ve ikinci
    # yonerge (`SISTEM_OLCUMSUZ`) devreye giriyor -- "sayi arama,
    # MEKANIZMAYI anlat". Sektor listesi ve izlenecekler yine
    # gonderiliyor; onlar sayi degil yapi.
    kendi_olcumu = bool((h.get("ozet") or "").strip()
                        or (d is not None and d.acilis))
    if d is not None:
        # SAYFAYA CIKMAYAN ACILIS MODELE DE GONDERILMEZ.
        #
        # Kosulsuzdu ve olculdu (2026-08-27): 104 elenen yorumun 84'u
        # acilis cumlesindeki Brent fiyatini aniyordu. Kutu basilan
        # sayfalarda acilis basilmiyor -- yani model sayfada olmayan
        # bir sayiyi aliyor, yorum uretiliyor, sonra dogrulama
        # suzgecine takilip cope gidiyordu. AI cagrisi da bosa.
        if d.acilis_basilir:
            p.append(f"Açılış: {d.acilis}")
        for b in (d.bulgular if kendi_olcumu else ()):
            p.append(f"Bulgu: {b}")
        for g in (d.turkiye if kendi_olcumu else ()):
            # SAYI BICIMLENDIRILEREK GONDERILIYOR.
            #
            # `g.son` ham `float`; f-string onu tam hassasiyetle basiyor
            # ve model gordugunu KOPYALIYOR. Olculdu, ana sayfada
            # yayimlandi: "Enflasyon %31,75409679 seviyesine gerileyerek
            # onceki %32,10903603'ten...". Sayfanin kendisi ayni degeri
            # %31,8 diye basiyor -- yani model sayfada olmayan bir
            # hassasiyet uretiyordu.
            p.append(f"Gösterge: {g.ad} {bicim.sayi(g.son, 2)}{g.birim} "
                     f"(önceki {bicim.sayi(g.onceki, 2)}{g.birim}, "
                     f"değişim {g.degisim}, {g.tarih})")
        if d.duyarlilik:
            # MEKANIZMA METNI GONDERILMIYOR, YALNIZCA SEKTOR ADLARI.
            #
            # Olculdu: parantez icindeki gerekce ("Net faiz marji ve
            # kredi talebi dogrudan bagli") girdiye konuldugunda model
            # onu OLDUGU GIBI kopyaliyordu; uc ayri yorum ayni cumleyle
            # bitiyordu. Sektor adi verip mekanizmayi modele
            # kurdurunca metin haberin kendisine ozgu oluyor.
            p.append("Etkilenen sektörler (sırayla): " + ", ".join(
                ad for ad, _s, _n in d.duyarlilik[:4]))
        if d.izlenecekler:
            p.append("İzlenecekler: " + ", ".join(d.izlenecekler[:4]))
    # `neden_onemli` GONDERILMIYOR.
    #
    # Olculdu: o cumle girdiye konuldugunda model onu oldugu gibi
    # kopyaliyordu -- ayni konudaki uc yorum ayni cumleyle bitti
    # ("sirketlerin oz kaynak maliyetini ve halka arz istahini
    # belirler"). Ustelik metin sayfada ZATEN "Neden onemli" basligi
    # altinda duruyor ve AI paragrafi hemen altinda; tekrar saf
    # tekrardi.
    #
    # Yonergedeki "kopyalama" kurali yetmedi. Kopyalanmasini
    # istemedigimiz metni hic gondermemek daha saglam bir cozum.
    # Mekanizmayi model, sektor listesinden ve konudan kuruyor.
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
        # OLCUT "VERI VAR MI" DEGIL, "SAYFADA BASILACAK VERI VAR MI".
        #
        # Once `d.acilis` yeterliydi. Ama sablon acilisi yalnizca
        # `acilis_basilir` iken basiyor (kutu basilan sayfalarda
        # basmiyor). Yani sayfada GORUNMEYECEK bir veriye dayanip
        # yorum uretiliyor, sonra `insa.py` onu "sayfada karsiligi
        # olmayan sayi" diye ELIYOR.
        #
        # Olculdu (2026-09-15): 132 sayfa tam bu durumdaydi -- depoda
        # yorumu var, sayfada yorumu yok, ve `uret_ai_yorum` "yorumu
        # var" deyip bir daha uretmiyor. Sessiz bir kilit.
        # Olcut hizalaninca aday sayisi 132'den 31'e iniyor: kalan
        # 101'in gercekten anlatacak basili verisi yok.
        #
        # Ayni kosul `girdi_kur`, `haber.html` ve
        # `insa._yorum_dogrulanabilir` icinde de `acilis_basilir`
        # uzerinden soruluyor -- dordu de ayni soruyu sormali.
        veri_var = bool(
            (h.get("ozet") or "").strip()
            or (d is not None and ((d.acilis and d.acilis_basilir)
                                   or d.bulgular or d.turkiye)))
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
    # ARSIV DE ADAY.
    #
    # Aday havuzu yalnizca `gundem.json` penceresinden kuruluyordu ve
    # olculdu: 204 yayimlanmis haber sayfasinin 19'unda yorum vardi.
    # Sebep yapisal -- pencere doniyor, yorum almadan pencereden dusen
    # haber bir daha hic siraya girmiyordu. Sonuc: sayfalarin %90'inda
    # analiz konuya gore sablonlanmis metinden ibaret kaliyor ve okur
    # ucuncu sayfada bunu fark ediyor.
    #
    # KOTA ICIN SINIR ARTIRILMADI. Calistirma basina ayni sayida cagri
    # yapiliyor; guncel haberler once, arsiv kalan yerleri dolduruyor.
    # Boylece backlog gunler icinde eriyor, tek gunde kotayi yakmiyor.
    havuz = list(veri.get("haberler", []))
    arsiv_sayisi = 0
    try:
        with beyin.baglan() as _b:
            for _adres, _yuk in _b.execute(
                    "SELECT adres, sayfa_veri FROM haber"
                    " WHERE sayfa_veri IS NOT NULL AND yayimlandi=1"
                    " AND adres NOT IN (SELECT adres FROM ai_yorum)"
                    " ORDER BY tarih DESC LIMIT 400").fetchall():
                if _adres in {x.get("adres") for x in havuz}:
                    continue
                try:
                    _h = json.loads(_yuk)
                except (TypeError, ValueError):
                    continue
                _h["adres"] = _adres
                _h["yorumlanir"] = True
                # KONU VE BOLGE YENIDEN TURETILIYOR.
                #
                # `sayfa_veri` yalnizca HAM OLGU sakliyor (baslik, ozet,
                # kurum, tarih) -- turetilmis alanlar bilerek disarida,
                # cunku depoda saklandiklarinda siniflandirici
                # duzeldikten sonra bile eski degeri tasiyorlardi.
                #
                # Ama o yuzden arsiv kaydinda `konu` BOS geliyor ve
                # `dosya.kur("")` konusuz bir dosya uretiyor: model
                # habere ozgu hicbir sey goremiyor. Ilk denemede tam
                # bunu yapiyordu.
                _bas = _h.get("baslik_kaynak") or _h.get("baslik", "")
                _h["konu"] = besleme.konu_bul(_bas, _h.get("konu")
                                              or "Şirket haberleri")
                _h["bolge"] = besleme.bolge_bul(_bas, _h.get("dil", "tr"))
                havuz.append(_h)
                arsiv_sayisi += 1
    except Exception as e:
        print(f"  arsiv adaylari okunamadi: {e}")
    if arsiv_sayisi:
        print(f"  {arsiv_sayisi} arsiv haberi aday havuzuna eklendi")

    for h in havuz:
        if h.get("yorumlanir") and h.get("adres"):
            # `varliklar=[]` GECILIYOR, atlanmiyor.
            #
            # OLCULDU VE KANITLANDI: ayni haber, ayni islev, iki farkli
            # cevap --
            #     yorum yolu (varliklar=None) -> 5 Turkiye gostergesi
            #     sayfa yolu (varliklar=[])   -> 0 Turkiye gostergesi
            #
            # `turkiye_haberi` `varliklar is None` gorunce ESKI olcute
            # (`bolge == "TR"`) dusuyor; sayfa tarafi ise varlik
            # indeksini gecirdigi icin gercek cevabi aliyor. Sonuc:
            # model sayfada BASILMAYACAK bes olcumu goruyor ve
            # kullaniyor. Okur yorumda "4.194 milyon dolarlik cari
            # islemler acigi" okuyup sayfada hicbir yerde bulamiyor.
            #
            # Bu, sitenin en temel iddiasini deliyor: her rakam
            # dogrulanabilir olmali.
            #
            # Varlik indeksi bu hatta HESAPLANMIYOR, dolayisiyla
            # gercek listeyi gecemiyoruz. Bos liste geciliyor cunku
            # bilinmezlikte MUHAFAZAKAR taraf dogru olan: gosterge
            # gondermemek, gonderip sayfada gosterememekten iyidir.
            # Eksik bir yorum okuru yanlisa goturmez; dogrulanamaz bir
            # rakam goturur.
            dosyalar[h["adres"]] = dosya.kur(
                h.get("konu", ""), h.get("bolge", ""), h.get("tarih", ""),
                varliklar=[],
                baslik=h.get("baslik_kaynak") or h.get("baslik", ""),
                ozetsiz=not (h.get("ozet") or "").strip())

    aday = secilenler(havuz, var, dosyalar)
    print(f"{len(aday)} aday, sinir {args.sinir}")
    if not aday:
        return 0

    uretilen = reddedilen = atlanan = 0
    with beyin.baglan() as b:
        b.executescript(SEMA)
        with beyin.calisma_kaydi(b, "ai_yorum") as ozet:
            denenen = 0
            for h in aday:
                if denenen >= args.sinir:
                    break
                girdi = girdi_kur(h, dosyalar.get(h["adres"]))
                if args.kuru:
                    denenen += 1
                    print()
                    print(f"--- {h['baslik'][:64]}")
                    print(girdi[:400])
                    continue

                # ANLATACAK BIR SEYI OLMAYAN HABERE MODEL CAGRILMIYOR.
                # Gerekce ve olcum `anlatacak_veri_yok` belgesinde.
                if anlatacak_veri_yok(b, girdi, h):
                    atlanan += 1
                    continue

                denenen += 1
                metin, model, neden, ham = yorumcu.yorumla(girdi)
                if not metin:
                    reddedilen += 1
                    _kota = yorumcu.cf_kota_doldu()
                    # Ret sebebi DEPOYA da yaziliyor. Ilk calistirmada
                    # dokuz redden hicbirinin sebebi depoda yoktu ve
                    # gunluge bakmadan tani konamiyordu.
                    b.execute(
                        "INSERT INTO ai_ret"
                        " (adres, baslik, neden, model, ham, kayit_ani)"
                        " VALUES (?,?,?,?,?,?)",
                        (h["adres"], h.get("baslik", "")[:200], neden,
                         model, (ham or "")[:2000], beyin.simdi()))
                    print(f"  RED  {h['baslik'][:48]}  ({neden})")
                    if _kota:
                        # KOTA DOLDU: kalan adaylar icin donmeye devam
                        # etmek yalnizca ayni reddi tekrarlardi.
                        print("  kota doldu -- kalan adaylar bir sonraki "
                              "kosuya birakildi")
                        break
                    if ham:
                        print(f"       ham: {ham[:120]}")
                    continue
                # BAGLAM KAPISI -- sayi dogru mu degil, DOGRU YERDE mi.
                #
                # Var olan kontrol "model bu sayiyi uydurdu mu" diye
                # soruyordu. Fed tutanaklari sayfasinda %31,75 yaziyordu:
                # sayi GERCEKTI (TCMB TUFE serisi), sayfada da vardi,
                # uydurma degildi -- ama haber ABD'ydi.
                #
                # Ayni sinif uc katmanda tekrarlayip her seferinde tek tek
                # yamandi. Yayimdaki 204 yorum bu kontrolle tarandiginda
                # 11 uyusmazlik cikti ve iceride bir ECB haberi de vardi;
                # yani yamalarin sinifi bitirmedigi olculdu.
                #
                # Kapi URETIMDE: yanlis eslesmis yorum depoya hic
                # girmiyor. Sonradan temizlemek, once yayimlamak demek.
                # HABERIN KENDI METNI DE GECILIYOR.
                #
                # Kontrol, metindeki her sayiyi bizim serimizden
                # alinmis varsayiyordu; oysa sayi cogu zaman haberin
                # kendi ozetinden geliyor. Olculdu (2026-09-15): bir
                # kosudaki 32 uyusmazligin 17'si boyleydi ve ucu birden
                # TURKIYE haberi, TURKIYE verisiydi.
                uy = _baglam.uyusmazlik(
                    b, metin,
                    h.get("baslik_kaynak") or h.get("baslik", ""),
                    h.get("kurum", ""), h.get("bolge", ""),
                    haber_metni=" ".join(str(h.get(_k) or "") for _k in
                                         ("baslik", "baslik_kaynak",
                                          "ozet")))
                if uy:
                    reddedilen += 1
                    b.execute(
                        "INSERT INTO ai_ret"
                        " (adres, baslik, neden, model, ham, kayit_ani)"
                        " VALUES (?,?,?,?,?,?)",
                        (h["adres"], h.get("baslik", "")[:200],
                         "baglam-uyusmazligi", model, metin[:2000],
                         beyin.simdi()))
                    print(f"  RED  {h['baslik'][:48]}  "
                          f"({uy['aciklama']})")
                    continue

                b.execute(
                    "INSERT OR REPLACE INTO ai_yorum"
                    " (adres, metin, saglayici, model, kayit_ani)"
                    " VALUES (?,?,?,?,?)",
                    # SAGLAYICI MODELDEN TURETILIYOR, `s`den DEGIL.
                    #
                    # `s` dongu baslamadan BIR KEZ okunuyor; `yorumla`
                    # ise kosu ortasinda Anthropic'ten Cloudflare'e
                    # gecebiliyor (bakiye bitince). Olculdu: 21 satir
                    # Cloudflare'in urettigi yorumu Anthropic'e mal
                    # etmisti.
                    (h["adres"], metin,
                     yorumcu.model_saglayicisi(model) or s,
                     model, beyin.simdi()))
                uretilen += 1
                print(f"  ✓    {h['baslik'][:52]}")
                print(f"       {metin[:150]}")
            ozet.update({"uretilen": uretilen,
                         "reddedilen": reddedilen,
                         "atlanan": atlanan})

    print()
    # ATLANAN DA YAZILIYOR: sessiz atlama, olculemeyen atlama
    # demektir ve bu depoda kac kez "cevap uretildi, okunabilir
    # yerde durmuyor" durumuyla karsilasildiysa hepsi boyle
    # baslamisti.
    _ek = (f", {atlanan} aday atlandi (anlatacak veri yok)"
           if atlanan else "")
    print(f"{uretilen} yorum uretildi, {reddedilen} reddedildi{_ek}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
