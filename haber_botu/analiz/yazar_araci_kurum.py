"""Araci kurum bilanco yazisi -- kod ile uretilir, API cagrisi yok.

`yazar.py` ile ayni felsefe, ama sektore ozgu iki ayrim yaziya islenmis:

1. **Satis gelirleri islem hacmidir.** Yazi bunu acikca soyler ve buyume
   cumlelerini brut kar uzerinden kurar. Aksi halde okur, aracilik hacmini
   sirket geliri sanir.
2. **Bilancodaki nakit ve borcun buyuk bolumu musteriye aittir.** "Sirket
   net nakit pozisyonunda" cumlesi bu sektorde yaniltir; yazi ticari
   borclarin aktife oranini vererek bunu gosterir.

Neden yazilmaz: hareketin nedeni (portfoy getirisinin kaynagi tablodan
okunmaz), gelecek yonu, hisse hakkinda herhangi bir degerlendirme.
"""

from __future__ import annotations

import bicim
from araci_kurum import Kalem, OranAdi, Rapor, Yon


def _mlr(d: float | None) -> str:
    """TL degeri milyar TL olarak yazar."""
    return "—" if d is None else f"{bicim.sayi(d / 1e9, 2)} milyar TL"


def _baslik(r: Rapor, simdi) -> str:
    fna = simdi.faaliyet_nakit_akisi
    kar_buyudu = (r.buyume(Kalem.NET_KAR) or 0) > 25
    yp = r.bul(OranAdi.YATIRIM_PAYI)

    ad = bicim.kisa_ad(r.sirket)
    if kar_buyudu and fna is not None and fna < 0:
        return f"{ad}: kâr ikiye katlandı, faaliyet nakit akışı negatif"
    if kar_buyudu and yp is not None and yp.deger >= 50:
        return f"{ad}: kâr büyüdü, motoru komisyon değil portföy"
    if kar_buyudu:
        return f"{ad}: kârlılık belirgin arttı"
    if (r.buyume(Kalem.BRUT_KAR) or 0) < 0:
        return f"{ad}: komisyon ve alım satım gelirleri geriledi"
    return f"{ad} {r.donem} bilanço tablosu"


def _ozet(r: Rapor, simdi, once) -> str:
    p: list[str] = []
    bk = r.buyume(Kalem.BRUT_KAR)
    nk = r.buyume(Kalem.NET_KAR)

    if bk is not None:
        p.append(
            f"{bicim.unvan_duzelt(r.sirket)} {r.donem} döneminde brüt kârını — aracı kurumda "
            f"gerçek gelir ölçüsü budur — reel olarak "
            f"{bicim.yuzde(abs(bk))} {'artırdı' if bk >= 0 else 'geriletti'}, "
            f"{_mlr(simdi.brut_kar)} seviyesine taşıdı."
        )
    if nk is not None and simdi.net_kar is not None:
        p.append(
            f"Dönem kârı {_mlr(simdi.net_kar)} ile reel "
            f"{bicim.yuzde(abs(nk), isaretli=False)} "
            f"{'arttı' if nk >= 0 else 'geriledi'}."
        )

    fna = simdi.faaliyet_nakit_akisi
    if fna is not None and fna < 0:
        p.append(
            f"Buna karşılık işletme faaliyetlerinden nakit akışı {_mlr(fna)} "
            "ile negatif; yazının en dikkat çeken bulgusu bu."
        )

    kotu = [s for s in r.sinyaller if s.yon is Yon.KOTU]
    dikkat = [s for s in r.sinyaller if s.yon is Yon.DIKKAT]
    iyi = [s for s in r.sinyaller if s.yon is Yon.IYI]
    if kotu or dikkat or iyi:
        p.append(
            f"Tabloda {len(iyi)} olumlu, {len(kotu)} olumsuz, {len(dikkat)} "
            "dikkat gerektiren bulgu öne çıkıyor."
        )
    return " ".join(p)


def _hacim_uyarisi(r: Rapor, simdi, once) -> str:
    if simdi.satis_gelirleri is None:
        return ""
    hacim_d = (
        (simdi.satis_gelirleri / once.satis_gelirleri - 1) * 100
        if once.satis_gelirleri else None
    )
    s = (
        f"Şirketin gelir tablosundaki **satış gelirleri kalemi "
        f"{_mlr(simdi.satis_gelirleri)}**"
    )
    if hacim_d is not None:
        s += f" ve yıllık {bicim.yuzde(hacim_d, isaretli=True)} değişim gösteriyor"
    s += (
        ". Bu rakam şirketin geliri değildir: aracı kurumun müşteri adına "
        "alıp sattığı menkul kıymetlerin brüt tutarını, yani **işlem hacmini** "
        "içerir. Karşısında neredeyse aynı büyüklükte bir satışların maliyeti "
        "kalemi durur.\n\nŞirkete kalan tutar **brüt kârdır**: komisyon "
        f"gelirleri ile net alım satım kârının toplamı, bu dönem "
        f"{_mlr(simdi.brut_kar)}. Aşağıdaki bütün büyüme hesapları bu kalem "
        "üzerinden yapılmıştır."
    )
    return s


def _tablo(r: Rapor) -> str:
    satirlar = ["| Kalem | Reel değişim |", "|---|---|"]
    for b in r.buyumeler:
        satirlar.append(f"| {b.ad} | {bicim.yuzde(b.reel, isaretli=True)} |")
    satirlar.append("")
    satirlar.append(
        "Şirketin finansal tabloları TMS 29 enflasyon muhasebesine göre "
        "düzenlenmiştir; karşılaştırmalı önceki dönem rakamları cari dönemin "
        "satın alma gücüne çevrildiği için yukarıdaki değişimler **reeldir**."
    )
    return "\n".join(satirlar)


def _oran_tablosu(r: Rapor) -> str:
    if not r.oranlar:
        return ""
    satirlar = ["| Oran | Önceki | Cari | Değişim |", "|---|---|---|---|"]
    for o in r.oranlar:
        yuzde_mi = o.birim == "%"
        onc = bicim.yuzde(o.onceki) if yuzde_mi else bicim.kat(o.onceki)
        car = bicim.yuzde(o.deger) if yuzde_mi else bicim.kat(o.deger)
        fark = (
            bicim.puan(o.degisim) if yuzde_mi
            else (bicim.sayi(o.degisim, 2, isaretli=True) + "x" if o.degisim is not None else "—")
        )
        satirlar.append(f"| {o.ad} | {onc} | {car} | {fark} |")
    return "\n".join(satirlar)


def _nakit_bolumu(r: Rapor, simdi) -> str:
    fna = simdi.faaliyet_nakit_akisi
    if fna is None or simdi.net_kar is None:
        return ""
    p: list[str] = []
    if fna < 0:
        p.append(
            f"Dönem kârı {_mlr(simdi.net_kar)} olarak açıklanırken işletme "
            f"faaliyetlerinden nakit akışı {_mlr(fna)} ile **negatif**. "
            "Muhasebe kârı ile şirkete giren nakit bu dönemde ters yönde "
            "hareket etmiş."
        )
        p.append(
            "Aracı kurumda bu tablo tek başına bir sorun göstergesi değildir: "
            "finansal yatırım portföyünün büyütülmesi ve müşteri "
            "pozisyonlarındaki değişim, nakit akış tablosunda işletme "
            "faaliyetleri altında yer alır ve kalemi negatife çevirebilir. "
            "Ancak kârın nakde dönüşmediği bir dönemin kaydedildiği de "
            "ortadadır; ayrıntı için nakit akış tablosunun işletme sermayesi "
            "bölümüne bakılması gerekir."
        )
    else:
        oran = fna / simdi.net_kar if simdi.net_kar > 0 else None
        if oran is not None:
            p.append(
                f"Faaliyet nakit akışı {_mlr(fna)}; dönem kârının "
                f"{bicim.yuzde(oran * 100)}'ine denk geliyor."
            )
    return " ".join(p)


def _kar_motoru(r: Rapor, simdi) -> str:
    yp = r.bul(OranAdi.YATIRIM_PAYI)
    if yp is None or simdi.yatirim_gelirleri_net is None:
        return ""
    p = [
        f"Esas faaliyet kârı {_mlr(simdi.faaliyet_kari)} iken yatırım "
        f"faaliyetlerinden gelirler {_mlr(simdi.yatirim_gelirleri_net)}. "
        f"İkincisi, vergi öncesi kârın {bicim.yuzde(yp.deger)}'ine denk."
    ]
    if yp.deger >= 50:
        p.append(
            "Yani bu dönemde kârın ağırlığı aracılık komisyonundan değil, "
            "şirketin kendi portföyünden geliyor. İki gelir kaleminin "
            "davranışı farklıdır: komisyon geliri işlem hacmine, portföy "
            "getirisi piyasa fiyatlarına bağlıdır ve ikincisi daha oynaktır."
        )
    if simdi.parasal_pozisyon is not None and simdi.parasal_pozisyon < 0:
        p.append(
            f"Aynı tabloda TMS 29 kapsamında {_mlr(abs(simdi.parasal_pozisyon))} "
            "net parasal pozisyon kaybı yer alıyor. Nakit ve alacak gibi "
            "parasal varlıkları parasal borçlarından fazla olan şirketler "
            "enflasyon ortamında bu satırda kayıp yazar."
        )
    if simdi.vergi is not None and simdi.vergi > 0:
        p.append(
            f"Vergi satırı da gider değil, {_mlr(simdi.vergi)} **gelir** "
            "olarak yazılmış; ertelenmiş vergi kaynaklı bu kalem dönem kârını "
            "yukarı taşımış ve her dönem tekrarlanmaz."
        )
    return " ".join(p)


def _bilanco_bolumu(r: Rapor, simdi) -> str:
    p: list[str] = []
    kald = r.bul(OranAdi.KALDIRAC)
    op = r.bul(OranAdi.OZKAYNAK_PAYI)
    mb = r.bul(OranAdi.MUSTERI_BORCU_PAYI)

    if simdi.ozkaynak is not None:
        oz = r.buyume(Kalem.OZKAYNAK)
        p.append(
            f"Özkaynak {_mlr(simdi.ozkaynak)}"
            + (f", karşılaştırma dönemine göre {bicim.yuzde(oz, isaretli=True)}."
               if oz is not None else ".")
        )
    if kald is not None:
        p.append(
            f"Aktif/özkaynak oranı {bicim.kat(kald.deger)}"
            + (f" (önceki {bicim.kat(kald.onceki)})." if kald.onceki else ".")
        )
    if op is not None:
        p.append(f"Özkaynağın aktif içindeki payı {bicim.yuzde(op.deger)}.")

    if mb is not None and simdi.ticari_borclar is not None:
        p.append(
            f"\n\n**Bilançonun okunmasında dikkat edilecek nokta:** ticari "
            f"borçlar {_mlr(simdi.ticari_borclar)} ile aktifin "
            f"{bicim.yuzde(mb.deger)}'ini oluşturuyor. Aracı kurum "
            "bilançosunda bu kalem ağırlıklı olarak **müşterilere ait "
            "varlıklardan** doğar. Aynı şekilde nakit ve finansal yatırım "
            "kalemlerinin bir bölümü de müşteri hesaplarına aittir. Bu "
            "yüzden aracı kurumda 'şirket şu kadar net nakit taşıyor' türü "
            "bir okuma, sanayi şirketindeki anlamı taşımaz."
        )
    return " ".join(p)


def _sinyal_bolumu(r: Rapor) -> str:
    if not r.sinyaller:
        return "Eşikleri aşan bir sinyal üretilmedi."
    return "\n\n".join(
        f"**{s.baslik}.** {bicim.bas_harf(s.gerekce)}." for s in r.sinyaller
    )


def _izleme(r: Rapor, simdi) -> str:
    m: list[str] = []
    if simdi.faaliyet_nakit_akisi is not None and simdi.faaliyet_nakit_akisi < 0:
        m.append("Faaliyet nakit akışının sonraki dönemde pozitife dönüp dönmediği.")
    yp = r.bul(OranAdi.YATIRIM_PAYI)
    if yp is not None and yp.deger >= 50:
        m.append("Komisyon gelirlerinin toplam kâr içindeki payının seyri.")
        m.append("Portföy getirisinin piyasa koşulları değiştiğinde nasıl davrandığı.")
    if simdi.vergi is not None and simdi.vergi > 0:
        m.append("Ertelenmiş vergi kaleminin sonraki dönemde tersine dönüp dönmediği.")
    gider = r.bul(OranAdi.GIDER_ORANI)
    if gider is not None:
        m.append("Gider oranının brüt kâr büyümesi yavaşladığında koruyup korumadığı.")
    if not m:
        m.append("Brüt kâr ve özkaynak kârlılığının sonraki dönemdeki seyri.")

    gorulen: set[str] = set()
    return "\n".join(f"- {x}" for x in m if not (x in gorulen or gorulen.add(x)))


def yaz(r: Rapor, simdi, once) -> str:
    """Araci kurum raporundan tam analiz metni uretir."""
    bolumler: list[str] = [f"# {_baslik(r, simdi)}", ""]

    def ekle(baslik: str, icerik: str) -> None:
        if icerik and icerik.strip():
            bolumler.extend([f"## {baslik}", "", icerik, ""])

    ekle("Özet", _ozet(r, simdi, once))
    ekle("Önce bir yanlış anlamayı önleyelim: satış gelirleri nedir",
         _hacim_uyarisi(r, simdi, once))
    ekle("Büyüme", _tablo(r))
    ekle("Kâr nereden geliyor?", _kar_motoru(r, simdi))
    ekle("Nakit: muhasebe kârı mı, gerçek para mı?", _nakit_bolumu(r, simdi))
    ekle("Bilanço", _bilanco_bolumu(r, simdi))
    ekle("Oranlar", _oran_tablosu(r))
    ekle("Dikkat çeken noktalar", _sinyal_bolumu(r))
    ekle("Neye bakmalı", _izleme(r, simdi))

    return "\n".join(bolumler).rstrip() + "\n"
