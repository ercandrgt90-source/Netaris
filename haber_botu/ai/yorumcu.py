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

KURALLAR — hepsi zorunlu:
- YALNIZCA sana verilen sayıları kullan. Yeni sayı, oran, tarih ya da
  kurum adı EKLEME. Emin olmadığın hiçbir şeyi yazma.
- Tahmin, öngörü, yatırım tavsiyesi YAZMA. "Yükselecek", "alım fırsatı",
  "hedef fiyat", "beklentimiz" gibi ifadeler yasak.
- Olasılık belirtme. "%60 ihtimalle" gibi ifadeler yasak.
- Yön yorumu yapma, ölçümü aktar. "Zayıf geldi" değil, "beklentinin
  0,3 puan altında" de.
- Aktarım kanalını anlat: bu veri hangi mekanizmayla neyi etkiler.
  Mekanizma yaz, sonuç tahmini yazma.
- En fazla 3 cümle. Madde işareti yok, düz metin.
- Türkçe yaz, sayıları Türkçe biçimde yaz (virgül ondalık ayracı)."""

#: Ciktida bulunmasi metni GECERSIZ kilan kaliplar.
YASAK = (
    re.compile(r"\b(alım|satım|tut)\s*(öneri|tavsiye|sinyal)", re.I),
    re.compile(r"hedef fiyat", re.I),
    re.compile(r"%\s*\d+\s*(ihtimal|olasılık)", re.I),
    re.compile(r"\b(yükselecek|düşecek|artacak|azalacak|gerileyecek)\b", re.I),
    re.compile(r"\byatırım (tavsiyesi|önerisi)\b", re.I),
    re.compile(r"\b(kesinlikle|mutlaka|garanti)\b", re.I),
)

#: Sayi denetiminde yok sayilan kisa sayilar. "3 cumle", "1 puan" gibi
#: ifadeler girdide gecmiyor ama uydurma da degil.
_KISA_SAYI = 2


def _sayilar(metin: str) -> set[str]:
    """Metindeki sayilari karsilastirilabilir bicime indirger.

    "31,75" ile "31.75" ayni sayidir; binlik ayraci atiliyor.
    """
    cikti = set()
    for s in re.findall(r"-?\d[\d.,]*", metin):
        t = re.sub(r"[.,](?=\d{3}\b)", "", s)      # binlik ayraci
        t = t.replace(",", ".").rstrip(".")
        cikti.add(t)
    return cikti


def sayi_denetimi(cikti: str, girdi: str) -> list[str]:
    """Ciktida olup girdide olmayan sayilari dondurur.

    Bos liste = temiz. Bu, uydurmaya karsi en somut savunma: model
    rakam uretemiyorsa uydurma yapamaz.
    """
    g = _sayilar(girdi)
    kacak = []
    for s in _sayilar(cikti):
        if len(s.lstrip("-")) < _KISA_SAYI:
            continue
        if s not in g:
            kacak.append(s)
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
                json={
                    "max_tokens": EN_COK_JETON,
                    # Sicaklik DUSUK: bu yaratici yazim degil,
                    # bicimlendirme isi.
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SISTEM},
                        {"role": "user", "content": girdi},
                    ],
                },
                timeout=ZAMAN_ASIMI,
            )
            y.raise_for_status()
            d = y.json()
            sonuc = (d.get("result") or {})
            # Bazi modeller `response`, bazilari `output` donduruyor.
            metin = (sonuc.get("response")
                     or sonuc.get("output")
                     or "").strip()
            if metin:
                return metin, model
        except httpx.HTTPError as e:
            son_hata = e
            continue
    if son_hata is not None:
        raise son_hata
    return "", ""


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


def yorumla(girdi: str) -> tuple[str, str, str]:
    """Girdiden yorum uretir. `(metin, kullanilan_model, ret_nedeni)`.

    Metin bossa `ret_nedeni` NEDEN bos oldugunu soyluyor -- sessiz
    basarisizlik olmuyor, hattin ciktisinda goruluyor.
    """
    if len(girdi) < 120:
        return "", "", "girdi cok kisa"
    s = saglayici()
    if not s:
        return "", "", "saglayici yok (anahtar tanimli degil)"

    try:
        if s == "anthropic":
            metin, model = _anthropic_cagir(girdi), ANTHROPIC_MODEL
        else:
            metin, model = _cf_cagir(girdi)
    except httpx.HTTPStatusError as e:
        # 403 genellikle jetonun Workers AI iznine sahip olmadigini
        # gosterir -- Workers dagitimi icin uretilen jetonda o izin
        # varsayilan olarak YOK.
        ek = " (jetonda Workers AI izni olmayabilir)" \
            if e.response.status_code == 403 else ""
        return "", "", f"{s} HTTP {e.response.status_code}{ek}"
    except httpx.HTTPError as e:
        return "", "", f"{s} ag hatasi: {type(e).__name__}"
    if not metin:
        return "", "", f"{s} bos yanit"

    # --- 1. sayi denetimi ---
    kacak = sayi_denetimi(metin, girdi)
    if kacak:
        return "", model, f"girdide olmayan sayi: {', '.join(kacak[:4])}"

    # --- 2. yasak kalip ---
    for d in YASAK:
        m = d.search(metin)
        if m:
            return "", model, f"yasak kalip: {m.group(0)!r}"

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
        return "", model, f"guvenlik taramasi: {yasak[0].aciklama}"

    # Fazla uzun cevaplari kirpmiyoruz -- kirpmak cumleyi ortasindan
    # kesip anlamsiz birakabilir. Uc cumleyi asan cevap zaten yonergeye
    # uymamis demektir; oldugu gibi birakilip insan denetimine kaliyor.
    return metin, model, ""
