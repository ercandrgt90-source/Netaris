"""AI yorumlarini inceleme dosyasi olarak yazar.

Uretilen her yorumu, uretildigi VERIYLE yan yana koyuyor. Amaç editorun
metni degil, metnin DAYANDIGI SEYI de gormesi: bir cumle kulaga dogru
gelip veriyle celisebiliyor -- bu projede iki kez oldu.

    python haber_botu/ai_dosyasi.py
    python haber_botu/ai_dosyasi.py --red      # yalnizca reddedilenler

Cikti: AI-YORUM-<tarih>.md (depo kokunde)

VAR OLAN DOSYANIN UZERINE YAZILMAZ -- editor uzerinde calisiyor
olabilir. `yorum_dosyasi.py`de bu bir kez yasandi ve yazilanlar
silindi.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date

_KOK = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(_KOK), str(_KOK / "ai"), str(_KOK / "analiz"),
                str(_KOK / "kaynak")]

import beyin   # noqa: E402
import dosya   # noqa: E402

GUNDEM = _KOK.parent / "site" / "icerik" / "gundem.json"

BASLIK = """# AI yorumları — inceleme dosyası

Her bölümde üç şey var: **haber**, modelin **gördüğü veri** ve
ürettiği **yorum**. Yorumu tek başına okumak yetmiyor — bir cümle
kulağa doğru gelip veriyle çelişebiliyor. Bu projede iki kez oldu:
biri "artıyor" deyip iki cümle sonra "geriledi" dedi, biri başlıktaki
bulgu yerine başka bir büyüklüğü anlattı.

## Ne arıyoruz

- **Veriyle çelişki.** Yorum, gördüğü veriyle aynı şeyi mi söylüyor?
- **Başlıkla çelişki.** Haberin ana bulgusunu mu anlatıyor?
- **Uydurma bağlam.** Verilmemiş bir mekanizma ya da kurum eklenmiş mi?
- **Dil.** Yanlış birim, yabancı yazım, bozuk ek.

## Nasıl işaretlenir

Her yorumun altındaki satırı doldurun:

    Değerlendirme:  iyi | düzeltilmeli | atılmalı
    Not:            neyin yanlış olduğu

Boş bıraktıklarınızı atlarım.

---
"""


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--red", action="store_true",
                   help="uretilenler yerine REDDEDILENLERI listele")
    args = a.parse_args()

    yuk = {}
    if GUNDEM.exists():
        for h in json.loads(GUNDEM.read_text(encoding="utf-8")).get(
                "haberler", []):
            yuk[h.get("adres")] = h

    with beyin.baglan() as b:
        if args.red:
            satirlar = b.execute(
                "SELECT adres, baslik, neden, model, ham FROM ai_ret"
                " ORDER BY id DESC LIMIT 40").fetchall()
        else:
            satirlar = b.execute(
                "SELECT y.adres, h.baslik_tr, y.metin, y.model"
                " FROM ai_yorum y LEFT JOIN haber h ON h.adres = y.adres"
                " ORDER BY y.kayit_ani DESC LIMIT 40").fetchall()

    if not satirlar:
        print("Kayit yok.")
        return 0

    p = [BASLIK]
    for i, s in enumerate(satirlar, 1):
        adres = s[0]
        h = yuk.get(adres, {})
        p.append(f"\n## {i}. {s[1] or adres}\n")
        p.append(f"`{h.get('konu', '?')}` · {h.get('kurum', '?')} · "
                 f"model: `{s[3]}`\n")

        if args.red:
            p.append(f"**REDDEDİLDİ:** {s[2]}\n")
            p.append("**Modelin yazdığı**\n")
            p.append(f"> {(s[4] or '(boş)')}\n")
        else:
            p.append("**Modelin gördüğü veri**\n")
            p.append("```")
            p.append(_girdi(h))
            p.append("```\n")
            p.append("**Ürettiği yorum**\n")
            p.append(f"> {s[2]}\n")

        p.append("```")
        p.append("Değerlendirme:  ")
        p.append("Not:            ")
        p.append("```\n")
        p.append("---")

    ad = f"AI-YORUM-{date.today().isoformat()}"
    if args.red:
        ad += "-red"
    yol = _KOK.parent / f"{ad}.md"
    n = 2
    while yol.exists():
        yol = _KOK.parent / f"{ad}-{n}.md"
        n += 1
    yol.write_text("\n".join(p) + "\n", encoding="utf-8")
    print(f"{yol.name} yazildi: {len(satirlar)} kayit")
    return 0


def _girdi(h: dict) -> str:
    """Modele giden metnin AYNISI -- uret_ai_yorum ile ayni kurulum."""
    if not h:
        return "(gündem penceresinde değil — veri gösterilemiyor)"
    d = dosya.kur(h.get("konu", ""), h.get("bolge", ""), h.get("tarih", ""),
                  baslik=h.get("baslik_kaynak") or h.get("baslik", ""),
                  ozetsiz=not (h.get("ozet") or "").strip())
    sys.path.insert(0, str(_KOK))
    from uret_ai_yorum import girdi_kur
    return girdi_kur(h, d)


if __name__ == "__main__":
    sys.exit(main())
