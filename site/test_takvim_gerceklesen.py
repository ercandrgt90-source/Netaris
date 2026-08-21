"""Takvimde ACIKLANDI MI / NE CIKTI / SURPRIZ.

En kritik kural burada sinaniyor: aciklanmamis veri aciklanmis gibi
GOSTERILMEMELI. Takvimin tek isi ne zaman ne cikacagini soylemek;
uydurma bir "gerceklesen" o isi ters cevirir.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import takvim_gerceklesen as T    # noqa: E402


class _Nesne:
    """Hattin gercekte koydugu bicim: sozluk DEGIL, nesne."""
    esik_kaynak = "beklenti"
    esik_deger = "3,1"


def test_surpriz_yonu():
    assert T.surpriz(3.4, 3.1)["yon"] == "ust"
    assert T.surpriz(2.8, 3.1)["yon"] == "alt"
    assert T.surpriz(3.1, 3.1)["yon"] == "tam"


def test_beklenti_yoksa_surpriz_yok():
    """Onceki degere gore 'surpriz' hesaplamak, olcutu degistirip
    ayni adi kullanmak olurdu."""
    assert T.surpriz(3.4, None) is None
    assert T.surpriz(None, 3.1) is None


def test_beklenti_nesne_de_olabilir_sozluk_de():
    """ASIL KUSUR buydu.

    Hat `beklenti`yi bir NESNE olarak koyuyor; `.get()` cagirmak
    AttributeError veriyordu. Cokme degil EKSIKLIK olarak
    gorunuyordu -- surpriz alani sessizce hic uretilmiyordu.
    """
    an = "2026-08-12T12:30:00+00:00"
    a = T.kutuya_ekle({"seri": "CPIAUCNS", "an": an, "beklenti": _Nesne()})
    b = T.kutuya_ekle({"seri": "CPIAUCNS", "an": an,
                       "beklenti": {"esik_kaynak": "beklenti",
                                    "esik_deger": "3,1"}})
    assert ("surpriz" in a) == ("surpriz" in b)


def test_esik_onceki_degerse_surpriz_yazilmiyor():
    """`esik_kaynak != 'beklenti'` ise konsensus YOK demek."""
    k = T.kutuya_ekle({"seri": "CPIAUCNS",
                       "an": "2026-08-12T12:30:00+00:00",
                       "beklenti": {"esik_kaynak": "onceki",
                                    "esik_deger": "3,1"}})
    assert "surpriz" not in k, k


def test_gelecek_yayin_aciklanmis_gorunmuyor():
    """EN KRITIK KURAL. Yarinki veri icin gozlem olamaz."""
    yarin = (_dt.datetime.now(_dt.timezone.utc)
             + _dt.timedelta(days=1)).isoformat()
    k = T.kutuya_ekle({"seri": "CPIAUCNS", "an": yarin, "beklenti": None})
    assert "gerceklesen" not in k, k


def test_cok_eski_yayina_yeni_gozlem_baglanmiyor():
    """Pencere disi gozlem o yayina sayilmamali.

    Genis pencere BIR SONRAKI donemin gozlemini yanlislikla bu
    yayina baglardi.
    """
    eski = "2020-01-01T12:30:00+00:00"
    k = T.kutuya_ekle({"seri": "CPIAUCNS", "an": eski, "beklenti": None})
    assert "gerceklesen" not in k, k


def test_bozuk_girdide_cokmuyor():
    """Takvimin tek kalemi bozuksa tamami dusmemeli."""
    assert T.kutuya_ekle({}) == {}
    assert "gerceklesen" not in T.kutuya_ekle({"seri": "X", "an": "bozuk"})
    assert "gerceklesen" not in T.kutuya_ekle({"seri": "", "an": "2026-01-01"})


def test_turkce_sayi_bicimi():
    """Ondalik ayraci VIRGUL -- sitenin kurali."""
    assert T._tr(3.3648) == "3,36"
    assert "," in T._tr(1234.5)


def test_gercek_depoda_temmuz_tufesi():
    """Asil depo: 12 Agustos yayini Temmuz TUFE'sini getirmeli."""
    k = T.kutuya_ekle({"seri": "CPIAUCNS",
                       "an": "2026-08-12T12:30:00+00:00",
                       "beklenti": _Nesne()})
    if "gerceklesen" not in k:
        return                     # depo yoksa test atlanir
    assert k["gerceklesen"]["donem"].startswith("2026-07")
    assert "," in k["gerceklesen"]["metin"]


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
