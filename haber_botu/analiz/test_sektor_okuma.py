"""Sektor okuma kilavuzu -- kapsam ve DIL denetimi.

Bu bloklar OKUMA KILAVUZU, yorum degil. Testlerin isi tam olarak bu
ayrimi korumak: kilavuz "bu kalem ne anlama gelir" der, "bu sirket
iyidir" demez.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

_KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_KOK))

import sektor_okuma as S    # noqa: E402

#: Degerlendirme sozcukleri -- kilavuzda BULUNMAMALI.
#:
#: Ayni liste `bilanco_yorum.SISTEM` icinde modele de yasak. Kural
#: modelde varken kodda olmamasi tutarsizlik olurdu: okur metnin
#: hangisinden geldigini bilmiyor.
YARGI = ("cazip", "başarılı", "güçlü şirket", "kötü", "riskli",
         "fırsat", "ucuz", "pahalı", "tavsiye", "önerilir")

#: Gelecege donuk ifadeler -- kilavuz TANIMLAR, ONGORMEZ.
ONGORU = ("yükselecek", "düşecek", "artacak", "azalacak", "beklenir",
          "olacaktır")


def _metinler():
    for sektor, (baslik, paragraflar) in S.OKUMA.items():
        yield sektor, baslik, " ".join(paragraflar)


def test_yargi_sozcugu_yok():
    for sektor, _b, metin in _metinler():
        d = metin.lower()
        for y in YARGI:
            assert y not in d, f"{sektor}: '{y}'"


def test_ongoru_yok():
    for sektor, _b, metin in _metinler():
        d = metin.lower()
        for y in ONGORU:
            assert y not in d, f"{sektor}: '{y}'"


def test_sayi_yok():
    """Kilavuzda OLCUM olmamali.

    Olcumler tablodan geliyor ve donemle degisiyor; kilavuz ise
    sabit. Icine bir rakam yazilirsa bir sonraki ceyrekte YANLIS
    olur ve kimse fark etmez -- cunku kilavuz yeniden uretilmiyor.

    Muhasebe standardi adi (TMS 29) ve oran esigi (1'in altinda)
    olcum degil, tanim.
    """
    for sektor, _b, metin in _metinler():
        temiz = metin.replace("TMS 29", "").replace("1'in", "")
        assert not re.search(r"\d[.,]\d", temiz), sektor


def test_baslik_soru_bicimde():
    """Okur hangi bolumun kendi sorusunu cevapladigini gormeli."""
    for sektor, baslik, _m in _metinler():
        assert len(baslik) > 15, sektor
        assert not baslik.endswith("."), sektor


def test_taninmayan_sektor_bos_donuyor():
    """Kilavuz yoksa bolum HIC yazilmamali.

    Yanlis bir okuma kilavuzu, kilavuzsuzluktan KOTUDUR: okur ona
    guvenip yanlis kalemi okur.
    """
    assert S.blok("Olmayan sektör") is None
    assert S.markdown("Olmayan sektör") == []
    assert S.markdown("") == []


def test_markdown_baslik_uretiyor():
    m = S.markdown("Finans")
    assert any(x.startswith("## ") for x in m)
    assert any("net faiz geliri" in x for x in m)


def test_defterdeki_sektorlerin_hepsi_kapsandi():
    """Uretilen her sektorun kilavuzu OLMALI.

    Bu test kapsamı sessizce daralmaktan koruyor: yeni bir sektor
    eklendiginde kilavuzsuz kalirsa burada goruluyor.
    """
    yol = _KOK.parent / "kaynak" / "sektor_ozet.json"
    if not yol.exists():
        return
    d = json.loads(yol.read_text(encoding="utf-8"))
    eksik = [s for s in d if S.blok(s) is None]
    assert not eksik, f"kılavuzu olmayan sektör: {eksik}"


if __name__ == "__main__":
    n = 0
    for ad, f in sorted(globals().items()):
        if ad.startswith("test_"):
            f()
            n += 1
    print(f"{n} test gecti")
