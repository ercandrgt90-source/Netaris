"""Makro serilerden hareket raporu -- butun rakamlar burada hesaplanir.

Bilanco motoruyla ayni ilke: **model hicbir sayi uretmez.** Degisimler,
zirveler, dipler ve yuzdeler burada hesaplanir; yazi katmani yalnizca
bunlari cumleye dokur.

OLCU BIRIMI AYRIMI -- onemli
---------------------------
Faiz ve getiri serilerinde degisim BAZ PUAN ile ifade edilir. Getiri
%4,23'ten %4,68'e ciktiginda "yuzde 10,6 artti" demek teknik olarak dogru
ama piyasa dilinde yanlistir ve yaniltir; dogru ifade "45 baz puan"dir.

Fiyat serilerinde (petrol, endeks) yuzde degisim anlamlidir.

Bu ayrim `Hareket.oran_mi` uzerinden yurutulur ve yazi katmani buna gore
farkli cumle kurar.

TARIH AYRIMI -- onemli
----------------------
Her serinin son gozlem tarihi farkli olabilir. Petrol serisi tahvil
getirilerinden birkac gun geride kalabiliyor. Butun gostergelere tek bir
tarih yazmak sessiz bir hatadir; her hareket kendi tarihini tasir.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Hareket:
    """Tek bir gostergenin bir pencere icindeki hareketi."""

    kod: str
    ad: str
    birim: str
    kaynak: str

    son: float
    son_tarih: str
    onceki: float | None
    onceki_tarih: str | None

    ilk: float
    ilk_tarih: str
    zirve: float
    zirve_tarih: str
    dip: float
    dip_tarih: str

    gozlem_sayisi: int

    @property
    def oran_mi(self) -> bool:
        """Faiz/getiri serisi mi? Degisim baz puanla ifade edilir."""
        return self.birim == "%"

    @property
    def son_degisim(self) -> float | None:
        """Son iki gozlem arasindaki fark, serinin kendi biriminde."""
        if self.onceki is None:
            return None
        return self.son - self.onceki

    @property
    def donem_degisim(self) -> float:
        """Pencerenin basindan bugune fark."""
        return self.son - self.ilk

    @property
    def donem_yuzde(self) -> float | None:
        """Pencere basina gore yuzde degisim. Oran serilerinde kullanilmaz."""
        if self.oran_mi or self.ilk <= 0:
            return None
        return (self.son / self.ilk - 1) * 100

    @property
    def zirveden_yuzde(self) -> float | None:
        """Zirveye gore yuzde degisim -- geri cekilmenin buyuklugu."""
        if self.oran_mi or self.zirve <= 0:
            return None
        return (self.son / self.zirve - 1) * 100

    @property
    def dipten_zirveye_yuzde(self) -> float | None:
        """Pencere icindeki dipten zirveye hareketin buyuklugu.

        Yalnizca dip zirveden ONCE geldiyse anlamlidir; aksi halde
        "yukselis" diye adlandirmak yanlis olur.
        """
        if self.oran_mi or self.dip <= 0 or self.dip_tarih >= self.zirve_tarih:
            return None
        return (self.zirve / self.dip - 1) * 100

    @property
    def baz_puan(self) -> float | None:
        """Pencere degisimi baz puan cinsinden (yalnizca oran serilerinde)."""
        return self.donem_degisim * 100 if self.oran_mi else None


@dataclass
class Gorunum:
    """Bir grup gostergenin ortak goruntusu."""

    hareketler: list[Hareket] = field(default_factory=list)
    notlar: list[str] = field(default_factory=list)

    def bul(self, kod: str) -> Hareket | None:
        return next((h for h in self.hareketler if h.kod == kod), None)

    @property
    def en_son_tarih(self) -> str:
        return max((h.son_tarih for h in self.hareketler), default="")

    @property
    def getiri_farki(self) -> float | None:
        """10 yillik eksi 2 yillik, baz puan.

        Negatif deger getiri egrisinin ters dondugu anlamina gelir; bu,
        tahvil piyasasinin uzun vadede daha dusuk faiz fiyatladigi durumdur.
        """
        on, iki = self.bul("DGS10"), self.bul("DGS2")
        if on is None or iki is None:
            return None
        return (on.son - iki.son) * 100


def _hareket(seri, kod: str) -> Hareket | None:
    """makro.Seri nesnesinden Hareket uretir.

    Gozlem sayisi ikiden azsa hicbir degisim hesaplanamaz; boyle bir seriyi
    rapora koymak "veri var" izlenimi verir, oysa yoktur.
    """
    g = seri.gozlemler
    if len(g) < 2:
        return None

    zirve = max(g, key=lambda x: x.deger)
    dip = min(g, key=lambda x: x.deger)

    return Hareket(
        kod=kod,
        ad=seri.ad,
        birim=seri.birim,
        kaynak=seri.kaynak,
        son=g[-1].deger,
        son_tarih=g[-1].tarih,
        onceki=g[-2].deger,
        onceki_tarih=g[-2].tarih,
        ilk=g[0].deger,
        ilk_tarih=g[0].tarih,
        zirve=zirve.deger,
        zirve_tarih=zirve.tarih,
        dip=dip.deger,
        dip_tarih=dip.tarih,
        gozlem_sayisi=len(g),
    )


def hesapla(seriler: dict[str, object]) -> Gorunum:
    """Kod -> makro.Seri esleminden gorunum uretir.

    Cekilemeyen seriler sessizce atlanmaz; not olarak kaydedilir ki yazida
    "bu gosterge bu sefer yok" denebilsin.
    """
    gorunum = Gorunum()
    for kod, seri in seriler.items():
        if seri is None:
            gorunum.notlar.append(f"{kod}: veri çekilemedi")
            continue
        h = _hareket(seri, kod)
        if h is None:
            gorunum.notlar.append(f"{kod}: yeterli gözlem yok")
            continue
        gorunum.hareketler.append(h)
    return gorunum
