"""Haber yorumcusu -- olculmus veriyi okunur cikarima cevirir.

    haber + olculmus veri  ->  saglayici  ->  dogrulama  ->  depo  ->  sayfa

TEMEL KURAL
-----------
MODEL RAKAM BULMAZ, VERILEN RAKAMI CUMLEYE CEVIRIR.

Sayfadaki butun olcumler (TUFE, cekirdek, politika faizi, beklenti,
duyarlilik siralamasi) `analiz/dosya.py` icinde deterministik olarak
hesaplaniyor. Modelin isi o olcumleri baglama oturtmak. Bu ayrim iki
isi birden goruyor: maliyeti dusuruyor ve UYDURMAYI KAPATIYOR --
modelin arayacagi bir sey yok.

NEDEN BUILD ZAMANINDA
---------------------
Ilk surum tarayicidan cagriliyordu ve olculdu: arama motoru o metni
HIC gormuyordu. Sitenin asil degeri olacak yorum, sayfanin HTML'ine
gomulu olmali. Ayrica build zamaninda uretilen metin DEPOYA yaziliyor;
ayni haber her kurulumda yeniden yorumlanmiyor, yani metin sabit
kaliyor ve okur sayfayi yenileyince degismiyor.

UC KATLI DOGRULAMA
------------------
1. SAYI DENETIMI  -- ciktidaki her sayi girdide de gecmeli.
2. GUVENLIK TARAMASI -- `ai/guvenlik.py`, uye yazilarinda kullanilan
   ayni suzgec: yatirim tavsiyesi, hedef fiyat, kesinlik iddiasi.
3. YASAK KALIP -- yon ve olasilik beyani.

Herhangi biri duserse metin TAMAMEN atilir. Duzeltmeye calismak yerine
susmak dogru: yorumsuz sayfa, yanlis yorumlu sayfadan iyidir.

SAGLAYICILAR
------------
"cloudflare" -- Workers AI. Ucretsiz gunluk kotasi var, site zaten
                Cloudflare'de. CLOUDFLARE_API_TOKEN ve
                CLOUDFLARE_ACCOUNT_ID yeterli (ikisi de mevcut).
"anthropic"  -- ANTHROPIC_API_KEY varsa. Daha iyi metin uretiyor.

Anahtar yoksa modul kendini atlar ve hat kirmizi DONMEZ.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

import httpx

_BURASI = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_BURASI), str(_BURASI.parent / "analiz")]

import guvenlik  # noqa: E402

#: Workers AI modelleri, SIRAYLA denenir.
#:
#: Ilki daha guclu ve Turkce'de belirgin sekilde daha iyi; ucretsiz
#: kotayi daha hizli tuketiyor. Kota dolar ya da model gecici olarak
#: erisilemez olursa ikinciye dusuluyor -- yorum uretmemektense daha
#: zayif bir modelle uretmek yeglenir, cunku cikti zaten uc katli
#: dogrulamadan geciyor.
#:
#: `NETARIS_AI_MODEL` ortam degiskeni verilirse YALNIZCA o kullanilir;
#: model degistirmek icin kod duzenlemek gerekmiyor.
CF_MODELLER = (
    "@cf/openai/gpt-oss-120b",
    "@cf/meta/llama-3.1-8b-instruct",
)
ANTHROPIC_MODEL = "claude-opus-5"


def cf_modelleri() -> tuple[str, ...]:
    ozel = os.environ.get("NETARIS_AI_MODEL", "").strip()
    return (ozel,) if ozel else CF_MODELLER

ZAMAN_ASIMI = 60.0
EN_COK_JETON = 420

SISTEM = """Sen bir finans veri editörüsün. Sana bir haberin ÖLÇÜLMÜŞ
verileri veriliyor. Görevin bu verileri okunur bir çıkarıma çevirmek.

GÖREV: Verileri TEKRARLAMA. Okur onları zaten yukarıda gördü. Sen
şunu yap: en önemli tek ölçümü seç, ne anlama geldiğini söyle ve
hangi mekanizmayla neyi etkilediğini yaz.

BAŞLIKLA ÇELİŞME. Yorumun, haberin başlığındaki bulguyla aynı şeyi
anlatmalı. Verilerde başlığa ait olmayan başka bir büyüklük varsa onu
ana konu yapma — başlık "X arttı" diyorsa, "Y azaldı" ile başlayan bir
çıkarım okuru yanıltır.

KURALLAR — hepsi zorunlu:
- YALNIZCA sana verilen sayıları kullan. Yeni sayı, oran, tarih ya da
  kurum adı EKLEME.
- Sayıyı VERİLDİĞİ ANLAMDA kullan. Bir fark ("0,90 puan geriledi")
  seviye değildir; seviye ("%1,60") fark değildir. Karıştırma.
- Süren eğilim iddiası YASAK. "Artıyor", "yükseliyor", "düşüyor"
  yazma — elinde iki gözlem var, bu bir seri iddiası olur. Geçmiş
  zaman serbest: "geriledi", "yükseldi".
- Tahmin, öngörü, yatırım tavsiyesi YASAK. "Yükselecek", "alım
  fırsatı", "hedef fiyat" gibi ifadeler yasak.
- Olasılık belirtme. "%60 ihtimalle" gibi ifadeler yasak.
- Sana verilen bağlam metnini KOPYALAMA. Kendi cümleni kur.
- Veri hangi ülkeye aitse o ülkenin bağlamında yaz. ABD verisine
  Türkiye'ye özgü açıklama (asgari ücret, TÜFE sepeti) ekleme.
- EN FAZLA 3 CÜMLE. Madde işareti yok, tek paragraf.
- Türkçe yaz. Yüzde işareti sayıdan ÖNCE gelir: %31,75 (31,75% DEĞİL).
  Ondalık ayracı virgüldür."""

#: Ciktida bulunmasi metni GECERSIZ kilan kaliplar.
YASAK = (
    re.compile(r"\b(alım|satım|tut)\s*(öneri|tavsiye|sinyal)", re.I),
    re.compile(r"hedef fiyat", re.I),
    re.compile(r"%\s*\d+\s*(ihtimal|olasılık)", re.I),
    re.compile(r"\b(yükselecek|düşecek|artacak|azalacak|gerileyecek)\b", re.I),
    re.compile(r"\byatırım (tavsiyesi|önerisi)\b", re.I),
    re.compile(r"\b(kesinlikle|mutlaka|garanti)\b", re.I),
)

#: SUREN EGILIM IDDIASI -- "artiyor", "yukseliyor", "dusuyor".
#:
#: Ilk gercek calistirmada olculdu:
#:
#:   Girdi : "Aciklanan deger 33,43. Onceki donem 45,85; geriledi."
#:   Cikti : "ABD'de isten cikarmalar ARTIYOR. Aciklanan deger 33,43.
#:            Onceki donem 45,85; geriledi (12,42)."
#:
#: Metin kendi icinde CELISIYOR: once "artiyor" diyor, iki cumle sonra
#: "geriledi". Butun sayilar girdide gectigi icin sayi denetimi bunu
#: yakalamadi -- uydurma sayi yok, YANLIS CUMLE var.
#:
#: Simdiki zaman kipiyle kurulan egilim iddiasi zaten yasak: elimizde
#: iki gozlem var, "artiyor" demek bir SERI iddiasi ve olcumu asiyor.
#: Gecmis zaman ("geriledi", "yukseldi") olcumun kendisidir, serbest.
SUREN_EGILIM = re.compile(
    r"\b(artıyor|azalıyor|yükseliyor|düşüyor|geriliyor|"
    r"artmakta|azalmakta|yükselmekte|düşmekte)\b", re.I)

#: Sayi denetiminde yok sayilan kisa sayilar. "3 cumle", "1 puan" gibi
#: ifadeler girdide gecmiyor ama uydurma da degil.
_KISA_SAYI = 2

#: En fazla cumle. Yonergede de yazili ama zayif model duzenli olarak
#: asiyor ve girdiyi tekrarlayan paragraflar uretiyor. Dort cumleye
#: musaade var: uc cumle hedef, biri pay.
EN_COK_CUMLE = 4

#: Cumle sonu. Ondalik ayraci noktayla yazilan sayilar ("31.75") cumle
#: sonu sanilmasin diye noktadan sonra BOSLUK ya da metin sonu araniyor.
_CUMLE_SONU = re.compile(r"[.!?](?:\s|$)")


def _cumle_sayisi(metin: str) -> int:
    return len([x for x in _CUMLE_SONU.split(metin) if x.strip()])


def _sayilar(metin: str) -> set[float]:
    """Metindeki sayilari SAYISAL DEGERE cevirir.

    METIN OLARAK KARSILASTIRMA YANLIS SONUC VERIYORDU -- olculdu:

        girdi "40,00"  -> "40.00"
        cikti "40"     -> "40"      -> "girdide olmayan sayi" (YANLIS)
        girdi "-3.018,00" -> "-3018.00"
        cikti "3.018"     -> "3018"    -> yine yanlis red

    Iki kayit da modelin dogru davrandigi hallerdi. Sayi olarak
    karsilastirinca 40 ile 40,00 ayni, 3018 ile -3018 ise MUTLAK
    degerde ayni: isaret cogu zaman kelimeye tasiniyor ("3.018 acik",
    "35 baz puan geriledi").
    """
    cikti: set[float] = set()
    for s in re.findall(r"-?\d[\d.,]*", metin):
        t = re.sub(r"[.,](?=\d{3}\b)", "", s)      # binlik ayraci
        t = t.replace(",", ".").rstrip(".")
        try:
            cikti.add(abs(float(t)))
        except ValueError:
            continue
    return cikti


#: Karsilastirma toleransi. Model "%31,75"i "%31,8" diye yuvarlayabilir;
#: bu uydurma degil, yuvarlamadir. Binde bir goreli fark serbest.
_TOLERANS = 0.001


def sayi_denetimi(cikti: str, girdi: str) -> list[str]:
    """Ciktida olup girdide olmayan sayilari dondurur.

    Bos liste = temiz. Bu, uydurmaya karsi en somut savunma: model
    rakam uretemiyorsa uydurma yapamaz.
    """
    g = _sayilar(girdi)
    kacak = []
    for s in _sayilar(cikti):
        if s < 10:            # tek haneli: "3 cumle", "1 puan"
            continue
        if any(abs(s - x) <= max(abs(x), 1.0) * _TOLERANS for x in g):
            continue
        # Yuvarlanmis hali de kabul: 31,8 ~ 31,75
        if any(abs(round(s, 1) - round(x, 1)) < 1e-9 for x in g):
            continue
        kacak.append(f"{s:g}")
    return kacak


def _cf_cagir(girdi: str) -> tuple[str, str]:
    """Workers AI. `(metin, kullanilan_model)` doner.

    Modeller SIRAYLA deneniyor: biri kota ya da gecici hata verirse
    digerine dusuluyor. Son model de duserse hata yukari firlatiliyor
    ki `yorumla()` sebebi yazabilsin.
    """
    hesap = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    jeton = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not hesap or not jeton:
        return "", ""
    son_hata: Exception | None = None
    for model in cf_modelleri():
        try:
            y = httpx.post(
                (f"https://api.cloudflare.com/client/v4/accounts/{hesap}"
                 f"/ai/run/{model}"),
                headers={"Authorization": f"Bearer {jeton}"},
                json=_istek_govdesi(model, girdi),
                timeout=ZAMAN_ASIMI,
            )
            y.raise_for_status()
            metin = _yaniti_coz(y.json())
            if metin:
                return metin, model
            # Bos yanit hata degil ama kullanilamaz: sonraki modele gec.
            son_hata = son_hata or RuntimeError(f"{model}: bos yanit")
        except httpx.HTTPError as e:
            son_hata = e
            continue
    if isinstance(son_hata, httpx.HTTPError):
        raise son_hata
    return "", ""


def _istek_govdesi(model: str, girdi: str) -> dict:
    """Modele gore istek bicimi.

    OLCULDU: `@cf/openai/gpt-oss-120b` cagrisi sessizce dusuyor ve hat
    yedek modele (llama-3.1-8b) iniyordu -- ilk gercek calistirmada
    dokuz yorumun dokuzu zayif modelden geldi.

    Sebep bicim farki: gpt-oss ailesi OpenAI'nin "responses" bicimini
    kullaniyor (`instructions` + `input`), digerleri sohbet bicimini
    (`messages`). Ayni govdeyi ikisine birden gondermek calismiyor.
    """
    if "gpt-oss" in model:
        return {
            "instructions": SISTEM,
            "input": girdi,
            "max_output_tokens": EN_COK_JETON,
            # Sicaklik DUSUK: bu yaratici yazim degil, bicimlendirme isi.
            "temperature": 0.2,
            # Akil yurutme cabasi dusuk: is kisa ve kurallari acik.
            # Yuksek caba hem yavaslatiyor hem kotayi hizli tuketiyor.
            "reasoning": {"effort": "low"},
        }
    return {
        "max_tokens": EN_COK_JETON,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SISTEM},
            {"role": "user", "content": girdi},
        ],
    }


def _yaniti_coz(d: dict) -> str:
    """Farkli yanit bicimlerinden metni cikarir.

    Sohbet bicimi     : result.response
    Responses bicimi  : result.output[] -> content[] -> text
                        (ilk ogeler akil yurutme olabilir, ATLANIR)
    """
    sonuc = d.get("result") or {}
    duz = sonuc.get("response")
    if isinstance(duz, str) and duz.strip():
        return duz.strip()

    parcalar: list[str] = []
    for oge in sonuc.get("output") or []:
        if not isinstance(oge, dict):
            continue
        # Akil yurutme adimi CIKTI DEGIL: modelin kendi notlari,
        # okura gosterilecek metin degil.
        if oge.get("type") == "reasoning":
            continue
        for p in oge.get("content") or []:
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                parcalar.append(p["text"])
    return "\n".join(parcalar).strip()


def _anthropic_cagir(girdi: str) -> str:
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        return ""
    y = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": anahtar,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": EN_COK_JETON,
            "system": SISTEM,
            "messages": [{"role": "user", "content": girdi}],
        },
        timeout=ZAMAN_ASIMI,
    )
    y.raise_for_status()
    parcalar = y.json().get("content", [])
    return "".join(p.get("text", "") for p in parcalar).strip()


def saglayici() -> str:
    """Hangi saglayici kullanilabilir. Hicbiri yoksa bos."""
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "anthropic"
    if (os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
            and os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()):
        return "cloudflare"
    return ""


def yorumla(girdi: str) -> tuple[str, str, str, str]:
    """Girdiden yorum uretir.

    `(metin, kullanilan_model, ret_nedeni, ham_cikti)` doner.

    `ham_cikti` reddedilse DE dolu: "neden reddedildi" sorusu ancak
    modelin ne yazdigina bakarak cevaplanabiliyor. Sessiz basarisizlik
    olmuyor -- hem gunluge hem depoya yaziliyor.
    """
    if len(girdi) < 120:
        return "", "", "girdi cok kisa", ""
    s = saglayici()
    if not s:
        return "", "", "saglayici yok (anahtar tanimli degil)", ""

    try:
        if s == "anthropic":
            metin, model = _anthropic_cagir(girdi), ANTHROPIC_MODEL
        else:
            metin, model = _cf_cagir(girdi)
    except httpx.HTTPStatusError as e:
        # 401 VE 403 ikisi de kapsam sorununa isaret ediyor.
        #
        # Olculdu: dagitim jetonu gecerli (ayni jetonla `wrangler deploy`
        # calisiyor) ama AI ucu 401 donuyor. Yani sorun jetonun gecersiz
        # olmasi degil, Workers AI KAPSAMINI tasimamasi -- "Edit
        # Cloudflare Workers" sablonuyla uretilen jetonda o izin
        # varsayilan olarak YOK.
        #
        # Ilk yazimda ipucu yalnizca 403'e bagliydi ve gercek hata 401
        # gelince sebep sessiz kaldi.
        kod = e.response.status_code
        ek = ""
        if kod in (401, 403):
            ek = (" -- jetonda 'Workers AI' izni yok gibi gorunuyor; "
                  "Cloudflare > My Profile > API Tokens uzerinden ekleyin")
        return "", "", f"{s} HTTP {kod}{ek}", ""
    except httpx.HTTPError as e:
        return "", "", f"{s} ag hatasi: {type(e).__name__}", ""
    if not metin:
        return "", "", f"{s} bos yanit", ""

    # --- 1. sayi denetimi ---
    kacak = sayi_denetimi(metin, girdi)
    if kacak:
        return "", model, f"girdide olmayan sayi: {', '.join(kacak[:4])}", metin

    # --- 2. yasak kalip ---
    for d in YASAK:
        m = d.search(metin)
        if m:
            return "", model, f"yasak kalip: {m.group(0)!r}", metin

    m = SUREN_EGILIM.search(metin)
    if m:
        return "", model, f"suren egilim iddiasi: {m.group(0)!r}", metin

    # --- 2b. uzunluk ---
    #
    # Yonerge "en fazla 3 cumle" diyor; zayif model bunu duzenli olarak
    # asiyor ve girdiyi oldugu gibi tekrarlayan paragraflar uretiyor.
    # Kirpmak cumleyi ortasindan kesecegi icin metin TAMAMEN atiliyor.
    n = _cumle_sayisi(metin)
    if n > EN_COK_CUMLE:
        return "", model, f"{n} cumle (en fazla {EN_COK_CUMLE})", metin

    # --- 3. yayin ilkeleri (uye yazilariyla AYNI tarayici) ---
    #
    # `yayinlanabilir()` DEGIL `tara()` kullaniliyor: birincisi metnin
    # ICINDE "yatirim tavsiyesi degildir" uyarisi ariyor ve uc cumlelik
    # bir paragrafta bunu istemek yanlis olurdu -- uyari sayfanin
    # kendisinde, her haber sayfasinin altinda duruyor. Aranan sey
    # yasak seviyesindeki bulgular.
    yasak = [b for b in guvenlik.tara(metin)
             if b.seviye is guvenlik.Seviye.YASAK]
    if yasak:
        return "", model, f"guvenlik taramasi: {yasak[0].aciklama}", metin

    # Fazla uzun cevaplari kirpmiyoruz -- kirpmak cumleyi ortasindan
    # kesip anlamsiz birakabilir. Uc cumleyi asan cevap zaten yonergeye
    # uymamis demektir; oldugu gibi birakilip insan denetimine kaliyor.
    return metin, model, "", metin
