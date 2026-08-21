"""Haber gorseli olarak GRAFIK -- stok fotograf yerine olcumun kendisi.

NEDEN
-----
Olculdu (2026-08-21): yayimlanan 1288 haberde 318 gorsel donuyordu ve
dagilim su:

    Jeopolitik   454 haber / 12 gorsel  -> her gorsel ~37 kez
    Borsa        190 haber /  9 gorsel  -> her gorsel ~21 kez
    Enerji       130 haber / 10 gorsel  -> her gorsel ~13 kez

Iki ayri sikayet var ve ikisinin sebebi de bu tabloda:

  "hala ayni dongu"  -> havuz dar, gorsel tekrar ediyor
  "alakasiz olabiliyor" -> havuz KONU duzeyinde; "Enerji" havuzundaki
     bir rafineri fotografi, Brent'in 88 dolara inmesiyle ilgili
     DEGIL. Genel bir fotograf, belirli bir habere dair olamaz.

Ikincisi havuzu buyuterek COZULMEZ. Ne kadar cok stok fotograf
eklersek ekleyelim, "petrol" fotografi bugunku petrol haberinin
kendisi olmuyor -- yalnizca konuyu isaret ediyor. Bloomberg ve NYT
veri haberlerinde bu yuzden fotograf degil GRAFIK kullaniyor: grafik
haberin sussu degil, konusu.

Grafik ayrica tekrar sorununu KOKUNDEN bitiriyor: her haberin serisi
ve tarih araligi farkli, yani her grafik tek.

KAPSAM DURUSTCE
---------------
Her habere grafik uretilemiyor. Olculdu: 1288 yayimli haberin 159'u
(%12) gosterge serisine bagli. Kalanina grafik URETILMIYOR -- veri
yokken grafik cizmek, olmayan olcumu varmis gibi gostermek olurdu.

NEDEN SVG, NEDEN ELLE
---------------------
Projede Pillow/matplotlib yok ve olmamali: ikisi de agir bagimlilik ve
CI suresini uzatiyor. SVG metin, yani sablona gomulebiliyor, her
cozunurlukte keskin, kilobaytlar mertebesinde ve renkleri CSS
jetonlarindan aliyor -- karanlik temada kendiliginden dogru gorunuyor.
"""

from __future__ import annotations

import datetime as _dt

#: Cizim alani. 16:9'a yakin -- kart gorselleriyle ayni oran, boylece
#: grafik ile fotograf yan yana geldiginde izgara kaymiyor.
EN, BOY = 640, 360
#: Kenar boslugu: eksen yazilari ve son nokta isareti icin.
PAY_SOL, PAY_SAG, PAY_UST, PAY_ALT = 8, 64, 26, 24


def _yol(noktalar: list[tuple[float, float]]) -> str:
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in noktalar)


def _tr_sayi(d: float) -> str:
    """Turkce sayi. Basamak olcumun buyuklugunden turuyor.

    Sabit iki basamak, 7543,59 gibi endekslerde dogru ama 88,90 $ gibi
    fiyatlarda gereksiz; 0,25 gibi oranlarda ise iki basamak SART.
    """
    b = 0 if abs(d) >= 1000 else (2 if abs(d) < 100 else 1)
    return f"{d:,.{b}f}".replace(",", " ").replace(".", ",")


def cizgi(seri: list[tuple[str, float]], ad: str, birim: str = "") -> str:
    """Bir zaman serisinden SVG alan grafigi uretir.

    `seri` ESKIDEN YENIYE sirali (tarih, deger) ciftleri.

    Bos ya da tek noktali seride BOS DIZGE donuyor -- iki noktasi
    olmayan bir seriden cizgi cizmek, egilimi uydurmak olur.
    """
    seri = [(t, float(d)) for t, d in seri if d is not None]
    if len(seri) < 2:
        return ""

    degerler = [d for _t, d in seri]
    en_az, en_cok = min(degerler), max(degerler)
    # DUZ SERI DE CIZILEBILMELI. Aralik sifirsa boleni sifir yapmadan
    # cizgiyi ortaya koyuyoruz; "degismedi" de bir bulgudur.
    aralik = (en_cok - en_az) or 1.0

    ic_en = EN - PAY_SOL - PAY_SAG
    ic_boy = BOY - PAY_UST - PAY_ALT
    n = len(seri) - 1
    noktalar = [
        (PAY_SOL + ic_en * i / n,
         PAY_UST + ic_boy * (1 - (d - en_az) / aralik))
        for i, (_t, d) in enumerate(seri)
    ]

    # YON RENGI SEMANTIK, MARKA RENGI DEGIL. Yukselis/dusus jetonlari
    # zaten sitede tanimli; grafik onlari kullaniyor ki okur ayni
    # renkleri ayni anlamda gormeye devam etsin.
    yon = "yukselis" if degerler[-1] >= degerler[0] else "dusus"

    son_x, son_y = noktalar[-1]
    alan = (_yol(noktalar)
            + f" L{son_x:.1f},{BOY - PAY_ALT:.1f}"
            + f" L{PAY_SOL:.1f},{BOY - PAY_ALT:.1f} Z")

    ilk_t, son_t = seri[0][0][:10], seri[-1][0][:10]

    def _gun(t: str) -> str:
        try:
            return _dt.date.fromisoformat(t).strftime("%d.%m.%Y")
        except ValueError:
            return t

    birim_ek = f" {birim}" if birim and birim != "endeks" else ""
    etiket = f"{ad}: {_tr_sayi(degerler[-1])}{birim_ek}"

    return f"""<svg class="grafik grafik-{yon}" viewBox="0 0 {EN} {BOY}" \
role="img" aria-label="{etiket}, {_gun(ilk_t)} - {_gun(son_t)}" \
>
  <path class="grafik-alan" d="{alan}"/>
  <path class="grafik-cizgi" d="{_yol(noktalar)}" fill="none"/>
  <circle class="grafik-son" cx="{son_x:.1f}" cy="{son_y:.1f}" r="4"/>
  <text class="grafik-deger" x="{son_x + 8:.1f}" y="{son_y + 4:.1f}">\
{_tr_sayi(degerler[-1])}</text>
  <text class="grafik-tarih" x="{PAY_SOL}" y="{BOY - 6}">{_gun(ilk_t)}</text>
  <text class="grafik-tarih grafik-tarih-sag" x="{EN - PAY_SAG}" \
y="{BOY - 6}">{_gun(son_t)}</text>
  <text class="grafik-ad" x="{PAY_SOL}" y="16">{ad}</text>
</svg>"""


def haber_grafigi(b, adres: str, en_cok_nokta: int = 90) -> str:
    """Haberin bagli oldugu varligin serisinden grafik uretir.

    Bulunamazsa BOS DIZGE -- cagiran taraf `if` ile bakiyor ve grafik
    yoksa fotografa dusuyor.
    """
    satir = b.execute(
        """SELECT v.seri_kodu, v.ad FROM haber_varlik hv
             JOIN varlik v ON v.kod = hv.varlik_kimlik
            WHERE hv.adres = ? AND v.seri_kodu IS NOT NULL
            ORDER BY v.onem DESC LIMIT 1""", (adres,)).fetchone()
    if not satir or not satir[0]:
        return ""
    kod, ad = satir
    veri = b.execute(
        """SELECT tarih, deger, birim, ad FROM gosterge
            WHERE kod = ? ORDER BY tarih DESC LIMIT ?""",
        (kod, en_cok_nokta)).fetchall()
    if len(veri) < 2:
        return ""
    veri.reverse()   # sorgu YENIDEN ESKIYE geldi; cizim tersini istiyor
    return cizgi([(t, d) for t, d, _bi, _a in veri],
                 veri[-1][3] or ad, veri[-1][2] or "")
