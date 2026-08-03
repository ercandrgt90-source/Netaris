"""Olay yazisini uretir -- olculen tepki + yapisal kanal + tarihsel emsal.

YAZININ SOZLESMESI
------------------
Bu modul dort seyi ayri ayri, karistirmadan yazar:

  1. NE OLDU        kaynaktan gelen olay, aktarim
  2. PIYASA NE YAPTI olculmus rakam; pencere ve gozlem ani ile
  3. NEDEN BU KANAL yapisal iliski, graftan; mekanik aciklama
  4. DAHA ONCE      beyinden gelen emsal; varsa

Bu ayrim urunun tamami. Okur hangi cumlenin olculmus, hangisinin
yapisal, hangisinin gecmis oldugunu gormeli.

NE YAZILMAZ
-----------
Yon tahmini ("petrol yukselmeye devam eder"), buyukluk tahmini, al/sat
onerisi ve NEDENSEL IDDIA. "Petrol yukseldi CUNKU saldiri oldu" cumlesi
kurulmaz; "saldiri sonrasi ilk islem penceresinde petrol su kadar
yukseldi" kurulur. Ikisi arasindaki fark, kanitlanabilirlik.

Ayni sebeple gecmis emsal "boyle olacak" demez, "boyle olmustu" der.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import bicim

#: Olay turune gore giris cumlesinin cercevesi.
#: Hicbiri yon ya da sonuc soylemiyor -- yalnizca olayin ne oldugunu.
TUR_CERCEVE = {
    "faiz": "Para politikası kararı açıklandı.",
    "enflasyon": "Enflasyon verisi yayımlandı.",
    "istihdam": "İstihdam verisi yayımlandı.",
    "jeopolitik": "Jeopolitik bir gelişme yaşandı.",
    "arz": "Arz tarafında bir gelişme yaşandı.",
    "kur": "Kur tarafında bir gelişme yaşandı.",
}

#: Tepkinin nasil okunacagi. YON SOYLEMEZ, olculeni aktarir.
def _yon_sozu(d: float) -> str:
    if d >= 0.05:
        return "yükseldi"
    if d <= -0.05:
        return "geriledi"
    return "yatay kaldı"


def _tepki_satiri(t: dict) -> str:
    ad = t["ad"]
    d = t.get("degisim")
    deger = t.get("deger")
    pencere = t.get("pencere_adi", "")
    if d is None:
        return f"**{ad}** için karşılaştırılabilir veri yok."

    # "gunluk icinde geriledi" bozuk Turkce. Gun ici pencerelerde
    # "1 saat icinde", gunluk olcumde "gunluk bazda" dogru bicim.
    zarf = "günlük bazda" if pencere == "günlük" else f"{pencere} içinde"
    parca = f"**{ad}** {zarf} {_yon_sozu(d)}"
    if abs(d) >= 0.05:
        parca += f": {bicim.yuzde(d, isaretli=True, basamak=2)}"
    if deger is not None:
        parca += f" (son {bicim.sayi(deger, 2)})"
    if t.get("gecikmeli"):
        # Gecikmeli veriyi anlik gibi sunmak okuru yanlis bilgilendirir.
        parca += f" — {t.get('gozlem_tarih', 'son')} tarihli gözlem"
    return parca + "."


def _emsal_satiri(satir, tur_adi: str) -> str:
    """Gecmis olayi ve o zamanki tepkiyi aktarir."""
    try:
        tepkiler = json.loads(satir["tepkiler"] or "[]")
    except (json.JSONDecodeError, TypeError):
        tepkiler = []
    olculen = [t for t in tepkiler if t.get("degisim") is not None]
    tarih = (satir["an"] or "")[:10]
    if not olculen:
        return f"- {tarih} — {satir['baslik'][:90]}"
    ozet = ", ".join(
        f"{t['varlik']} {bicim.yuzde(t['degisim'], isaretli=True, basamak=1)}"
        for t in olculen[:4]
    )
    return f"- {tarih} — {satir['baslik'][:80]} ({ozet})"


def yaz(olay, tepkiler: list[dict], kanallar: list[dict],
        emsaller: list, kaynak_adi: str = "", kaynak_adres: str = "") -> str:
    """Olay yazisinin markdown govdesini uretir."""
    p: list[str] = []

    p.append(f"# {olay.baslik}")
    p.append("")

    # --- 1. NE OLDU ---
    cerceve = TUR_CERCEVE.get(olay.tur, "Piyasayı ilgilendiren bir gelişme yaşandı.")
    giris = cerceve
    if kaynak_adi:
        giris += f" Kaynak: {kaynak_adi}."
    p.append(giris)
    p.append("")

    # --- 2. PIYASA NE YAPTI ---
    olculen = [t for t in tepkiler if t.get("degisim") is not None]
    p.append("## Piyasada ne oldu")
    p.append("")
    if olculen:
        for t in olculen:
            p.append(f"- {_tepki_satiri(t)}")
        p.append("")
        p.append(
            "*Yukarıdaki rakamlar ölçülen fiyat hareketidir. Hareketin "
            "sebebinin bu gelişme olduğu iddia edilmemektedir; aynı "
            "pencerede başka etkenler de fiyatlanmış olabilir.*"
        )
    else:
        # Veri yoksa "hareket olmadi" DENMEZ -- olculmedigi soylenir.
        p.append(
            "Bu gelişme için karşılaştırılabilir fiyat verisi alınamadı. "
            "Ölçülemeyen bir hareket, olmamış sayılmaz."
        )
    p.append("")

    # --- 3. NEDEN BU KANAL ---
    if kanallar:
        p.append("## Hangi kanallardan yansır")
        p.append("")
        for k in kanallar:
            aciklama = k.get("aciklama") or ""
            satir = f"- **{k['hedef_ad']}**"
            if aciklama:
                satir += f" — {aciklama}"
            p.append(satir)
        p.append("")
        p.append(
            "*Bu maddeler yapısal aktarım kanallarıdır: mekanizmanın "
            "varlığını anlatır, yönünü ya da büyüklüğünü değil.*"
        )
        p.append("")

    # --- 4. DAHA ONCE ---
    if emsaller:
        p.append("## Daha önce ne olmuştu")
        p.append("")
        for e in emsaller:
            p.append(_emsal_satiri(e, olay.tur_adi))
        p.append("")
        p.append(
            "*Geçmiş hareketler benzer bir sonucun tekrarlanacağını "
            "göstermez; yalnızca bu kanalın daha önce nasıl işlediğini "
            "aktarır.*"
        )
        p.append("")

    return "\n".join(p).strip() + "\n"


def ozet_cikar(olay, tepkiler: list[dict]) -> str:
    """Kart ve liste ozeti. Olculen en buyuk hareketi one alir."""
    olculen = [t for t in tepkiler if t.get("degisim") is not None]
    if not olculen:
        return f"{olay.tur_adi}. Fiyat tepkisi ölçülemedi."
    en = max(olculen, key=lambda t: abs(t["degisim"]))
    return (
        f"{olay.tur_adi}. {en['ad']} {en.get('pencere_adi', '')} içinde "
        f"{bicim.yuzde(en['degisim'], isaretli=True, basamak=2)} "
        f"{_yon_sozu(en['degisim'])}."
    ).replace("  ", " ")
