# -*- coding: utf-8 -*-
"""bundesbank.py testleri -- AGA CIKMAZ.

ASIL TUZAK: Bundesbank'in CSV'si BASLIK ve USTVERI satirlari
tasiyor ve ONLAR DA VIRGUL iceriyor ("Decimals,2,"). "Virgulle ayir
ve ikinciyi al" diyen bir ayristirici ustveriyi VERI sanar -- ve
hicbir hata firlamaz, yalnizca seriye uydurma bir kayit girer.
Ayristirici bu yuzden satiri TARIH BICIMIYLE suzuyor.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bundesbank  # noqa: E402

gecti = 0
kaldi = []


def es(ad, bulunan, beklenen):
    global gecti
    if bulunan == beklenen:
        gecti += 1
    else:
        kaldi.append(f"{ad}: {bulunan!r} != {beklenen!r}")


#: Ucun GERCEK bicimi -- 2026-10-29'da indirilen dosyadan kirpildi.
#: BOM, baslik, ustveri ve bos (tatil) gozlem dahil.
HAM = (
    '\ufeff"",BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A,'
    'BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A_FLAGS\n'
    '"","Yields, derived from the term structure of interest rates,'
    ' on listed Federal securities",\n'
    'Decimals,2,\n'
    'unit,%,\n'
    '2026-10-26,3.40,\n'
    '2026-10-27,3.39,\n'
    '2026-10-28,3.40,\n'
    '2026-10-29,,\n'          # tatil/eksik gozlem
)

cozulen = bundesbank.coz(HAM)

es("ustveri satirlari veri sayilmadi", len(cozulen), 3)
es("ilk kayit", cozulen[0], ("2026-10-26", 3.40))
es("son kayit", cozulen[-1], ("2026-10-28", 3.40))
es("eskiden yeniye sirali", cozulen[0][0] < cozulen[-1][0], True)

# BOS GOZLEM SIFIR DEGIL. "2026-10-29,," satiri atlanmali; 0.0 olarak
# yazilsaydi getiri grafigi dibe inen uydurma bir cizgi gosterirdi.
es("bos gozlem atlandi", [x for x in cozulen if x[1] == 0.0], [])

# USTVERI SATIRI SAYI TASIYOR: "Decimals,2," satiri virgulle
# ayrildiginda ikinci alan "2" -- yani gecerli bir float. Olcut tarih
# bicimi OLMASAYDI bu satir 2.0 degerinde bir kayit olurdu.
es("Decimals satiri kaydolmadi",
   [x for x in cozulen if x[1] == 2.0], [])
es("unit satiri kaydolmadi", [x for x in cozulen if x[0] == "unit"], [])

# BOM ILK VERI SATIRINI YEMEMELI. Dosya BOM ile basliyor; eger BOM
# ilk ALAN yerine ilk SATIRA yapissa ve siyrilmasa, ilk kayit
# kaybolurdu.
es("BOM bir kaydi yemedi", len(bundesbank.coz(HAM.lstrip("\ufeff"))),
   len(cozulen))

# Bos girdi cokmemeli.
es("bos metin", bundesbank.coz(""), [])
es("yalnizca baslik", bundesbank.coz('"",SERI,FLAGS\n'), [])

# KOD VE AD: `graf_tohum` bu kodu `seri_kodu` olarak tasiyor; burada
# degisirse orada sessizce kopar.
es("seri kodu", bundesbank.KOD, "BBK_DE10Y")
es("birim", bundesbank.BIRIM, "%")
es("kaynak adi", bundesbank.KAYNAK, "Deutsche Bundesbank")
# UC BIZE AIT OLMAYAN BIR ALANA GITMEMELI (bu depoda bir kez yasandi).
es("uc bundesbank alanında",
   bundesbank.UC.startswith("https://api.statistiken.bundesbank.de/"),
   True)

# ===============================================================
# UC NOKTASI TASINDI VE SERI ON IKI GUN DONDU -- OLCULDU 2026-11-25.
#
# Bundesbank `/rest/download/` -> `/rest/data/` tasidi; eskisi 301
# donuyor ve `httpx` varsayilan olarak yonlendirme IZLEMIYOR. Cekim
# 2026-11-13'ten beri her kosuda patliyordu. `uret_evds.py` satiri
# BASIYORDU ama adim 0 ile donuyordu, yani kosu YESIL kaldi ve
# yayindaki grafik 13 Kasim'da bitti.
#
# IKI AYRI IDDIA: dogru yol VE yonlendirme izlemesi. Yalnizca yolu
# sinamak yetmez -- kaynak bir daha tasidiginda ayni sessiz donma
# tekrarlar.
# ===============================================================
es("uc `rest/data` yolunu kullaniyor (download DEGIL)",
   "/rest/data/" in bundesbank.UC and "/rest/download/" not in bundesbank.UC,
   True)

# YONLENDIRME IZLENIYOR: olcut METIN degil, GERCEK cagri.
# Sahte istemci cagri argumanlarini yakaliyor; ag istegi YOK.
_cagri = {}


def _sahte_get(adres, **k):
    _cagri.update(k)
    _cagri["adres"] = adres

    class _C:
        text = '"2026-11-24",3.31,\n'

        @staticmethod
        def raise_for_status():
            return None
    return _C()


class _SahteIstemci:
    get = staticmethod(_sahte_get)


_sonuc = bundesbank.cek(_SahteIstemci())
es("sahte istemciyle cekim cozuluyor", _sonuc, [("2026-11-24", 3.31)])
es("cek() yonlendirmeyi IZLIYOR",
   _cagri.get("follow_redirects"), True)
es("cek() dogru adrese gidiyor", _cagri.get("adres"), bundesbank.UC)
es("cek() kimlik basligini geciriyor",
   _cagri.get("headers"), bundesbank.BASLIKLAR)

print(f"{gecti} gecti, {len(kaldi)} kaldi")
for k in kaldi:
    print("  DUSTU", k)
raise SystemExit(1 if kaldi else 0)
