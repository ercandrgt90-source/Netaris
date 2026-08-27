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

    uretilen = reddedilen = 0
    with beyin.baglan() as b:
        b.executescript(SEMA)
        with beyin.calisma_kaydi(b, "ai_yorum") as ozet:
            for h in aday[:args.sinir]:
                girdi = girdi_kur(h, dosyalar.get(h["adres"]))
                if args.kuru:
                    print(f"\n--- {h['baslik'][:64]}\n{girdi[:400]}")
                    continue

                metin, model, neden, ham = yorumcu.yorumla(girdi)
                if not metin:
                    reddedilen += 1
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
                uy = _baglam.uyusmazlik(
                    b, metin,
                    h.get("baslik_kaynak") or h.get("baslik", ""),
                    h.get("kurum", ""), h.get("bolge", ""))
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
                    (h["adres"], metin, s, model, beyin.simdi()))
                uretilen += 1
                print(f"  ✓    {h['baslik'][:52]}")
                print(f"       {metin[:150]}")
            ozet.update({"uretilen": uretilen, "reddedilen": reddedilen})

    print(f"\n{uretilen} yorum uretildi, {reddedilen} reddedildi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
