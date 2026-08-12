"""Yorum OLMAYAN model ciktisini eler.

NEDEN AYRI MODUL
----------------
Bu denetim modelin NE DEDIGINE degil, SOYLEDIGI SEYIN yorum olup
olmadigina bakiyor -- `yorumcu.YASAK` ise icerige bakiyor. Iki ayri
soru, iki ayri yer. Ayrica kendi basina sinanabiliyor.

OLCULDU, YAYIMLANDI
-------------------
Bir TCMB basin duyurusu sayfasinda ve ANA SAYFADA su metin "Netaris
yorumu" basligi altinda okura gosterildi (@cf/openai/gpt-oss-120b,
1293 karakter):

    analysis 0️⃣  We need to produce a " news release ( Basın Duyuru )"
    about inflation rates etc. The user wants a news release ...
    Haber: Fa Fa Or Or Or Or Or Or Or Or Or Or Or Or Or Or Or ...

Iki ariza ust uste: model DUSUNME KANALINI ciktiya sizdirdi
("analysis" bolumu, `gpt-oss` ailesinin harmony bicimi) ve ardindan
bozulup tek heceyi tekrarlamaya basladi.

HICBIR MEVCUT DENETIM YAKALAMADI. Sebebi olculdu: metinde nokta
neredeyse yok, dolayisiyla cumle sayaci 1293 karakterlik yigini TEK
CUMLE sayip uzunluk sinirindan geciriyordu. Sayi denetimi de temiz
gecti -- uydurma sayi yoktu, hic sayi yoktu.
"""

from __future__ import annotations

import re

#: Modelin dusunme kanali izleri. `gpt-oss` ailesi "harmony" bicimini
#: kullaniyor ve `analysis` / `final` kanallarini ayirmasi gerekiyor;
#: ayiramadiginda ic monolog dogrudan ciktiya dusuyor.
KANAL = re.compile(
    r"^\s*(analysis|assistantfinal|final)\b"
    r"|<\|(channel|start|end|message)\|>"
    r"|\bassistantfinal\b",
    re.I)

#: Modelin ISTEMI icerik sanmasi. Turkce bir finans yorumunda bu
#: cumleler bulunmaz.
ISTEM_YANKISI = re.compile(
    r"\b(we need to|the user wants?|as an ai|i should|let me\b|"
    r"here(?:'s| is) (?:a|the)|as requested|sure[,!]? here)",
    re.I)

#: Bozulma: ayni kisa sozcuk arka arkaya. Bes tekrar hicbir dogal
#: metinde olmuyor; "Or Or Or Or Or Or" tam olarak bu.
#:
#: Sinir SEKIZ karakter: uzun sozcuklerin yinelenmesi (madde basi,
#: liste) mesru olabiliyor, kisa hecelerinki olmuyor.
DONGU = re.compile(r"\b(\w{1,8})\b(?:\s+\1\b){4,}", re.I)

#: Turkceye ozgu harfler. Yorum Turkce yaziliyor; uzun bir metinde
#: hicbiri yoksa cikti baska dilde ya da bozuk demektir.
TR_HARF = frozenset("çğıöşüÇĞİÖŞÜ")

#: Turkce harf araminin altina inmedigi uzunluk. Kisa bir cumlede
#: hicbir ozel harf gecmeyebilir: "Fed faizi 25 baz puan indirdi."
TR_ESIK = 120


def sebep(metin: str) -> str:
    """Metin yorum DEGILSE sebebini doner; yorumsa bos dizge.

    Sirali bakiliyor ve ILK bulgu donuyor -- amac tam tani degil,
    metni elemek.
    """
    if not metin:
        return ""

    m = KANAL.search(metin)
    if m:
        return f"model dusunme kanali sizmis: {m.group(0).strip()!r}"

    m = ISTEM_YANKISI.search(metin)
    if m:
        return f"istem yankisi: {m.group(0)!r}"

    m = DONGU.search(metin)
    if m:
        return f"tekrar dongusu: {m.group(0)[:40]!r}"

    if len(metin) > TR_ESIK and not (TR_HARF & set(metin)):
        return "Turkce harf hic gecmiyor -- cikti baska dilde olabilir"

    return ""
