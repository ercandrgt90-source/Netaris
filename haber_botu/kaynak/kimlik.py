"""Netaris'in dis servislere kendini tanitirken kullandigi TEK kimlik.

BU DOSYA NEDEN VAR
------------------
Iletisim adresi 20 ayri kaynak dosyasinda ELLE yazilmisti ve
kacinilmaz olarak surukledi. 2026-08-27'de olculdu:

    ercandrgt90@gmail.com          7 dosya   (gecerli)
    iletisim@netaris.com           3 dosya   (ALAN ADI BIZIM DEGIL)
    adres hic yok                  4 dosya
    tarayici taklidi               2 dosya

`netaris.com` bize ait degil -- alan adimiz `netaris.net`. Yani uc
kaynak, dis servislere BASKASININ alan adindaki bir adresi veriyordu.

BUNUN OLCULEBILIR BEDELI
------------------------
Suslemeden ibaret degil:

  * MyMemory ceviri servisi `de=` parametresindeki adrese bakarak
    kotayi gunde 1.000 kelimeden 50.000 kelimeye cikariyor. Adres
    dogrulanamazsa ayricalik SESSIZCE dusuyor -- hata donmuyor,
    yalnizca ceviri erken tukeniyor.
  * Veri saglayicilari asiri kullanimda once User-Agent'taki adrese
    yaziyor, cevap gelmezse UYARMADAN engelliyor. Ulasilamayan bir
    adres, uyariyi hic gormemek demek.
  * Adres gercekten baskasinin olsaydi, bizim trafigimizin sikayeti
    o kisiye giderdi.

NEDEN SABIT, NEDEN AYAR DEGIL
-----------------------------
Ortam degiskeni yapilabilirdi ama yanlis olurdu: tanimsiz kalinca
sessizce bos bir adrese duserdi ve tam olarak kacindigimiz duruma
geri donerdik. Kimlik, kodun bilmesi gereken bir OLGU -- dagitima
gore degismiyor.
"""

from __future__ import annotations

#: Ulasilabilir tek adres.
#:
#: 2026-08-28'de kisisel Gmail'den alan adi adresine gecildi.
#: Cloudflare Email Routing ile kuruldu ve ucundan uca dogrulandi:
#: SPF `_spf.mx.cloudflare.net` iceriyor, uc MX kaydi yerinde, hedef
#: adres `Verified` ve baska bir adresten atilan deneme Gmail'e dustu.
#:
#: Neden onemliydi: bu adres yalnizca kunyede degil, dis veri
#: saglayicilarina giden User-Agent basliklarinda da geciyor. Kisisel
#: bir adresi oraya koymak, sitenin kimligini bir kisinin ozel
#: hesabina baglamak demekti.
ILETISIM = "destek@netaris.net"

#: Kendi alan adimiz. `netaris.com` DEGIL; bkz. site/insa.py TABAN_ADRES.
ALAN_ADI = "netaris.net"

SURUM = "1.0"


def ajan(amac: str = "finans arastirma") -> str:
    """Bir istegin User-Agent metnini uretir.

    `amac` sunucu gunlugunde ne aradigimizi anlatir; bir saglayici
    trafigimizi merak ederse cevap adresle birlikte orada duruyor.
    """
    return f"Netaris/{SURUM} ({amac}; {ILETISIM})"


#: Cogu kaynagin dogrudan kullanabilecegi hazir baslik.
BASLIKLAR = {"User-Agent": ajan()}
