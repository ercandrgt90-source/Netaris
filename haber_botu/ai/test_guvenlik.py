"""guvenlik.py icin dogrulama testleri.

Bir ifade tarayicisinin iki sekilde bozulabilir: yakalamasi gerekeni
kacirir (yanlis negatif -> yasal risk) ya da masum metni engeller
(yanlis pozitif -> hat tikanir). Ikisini de test ediyoruz.

Calistirmak icin:  python -m haber_botu.ai.test_guvenlik
"""

from __future__ import annotations

import sys

from guvenlik import Seviye, normalize, tara, yasal_uyari_var_mi, yayinlanabilir

UYARI = "Bu içerik bilgilendirme amaçlıdır, yatırım tavsiyesi değildir."

# Yakalanmasi ZORUNLU ifadeler. Her cumle iki bicimde de test edilir:
# diakritikli (dogru yazim) ve diakritiksiz (sahada cok yaygin). Ikisi de
# yakalanmazsa tarayici gercek bir yasal risk tasir.
YAKALANMALI = [
    "Hisse bu seviyelerden alınabilir.",
    "Şirket için hedef fiyat 45 TL olarak belirlendi.",
    "Bilanço sonrası hisseyi portföyünüze ekleyin.",
    "Bu hisse kesinlikle yükselecek.",
    "Yatırımcılara bu hisseyi öneriyoruz.",
    "Kağıt önümüzdeki dönemde uçacak.",
    "Alım fırsatı olarak değerlendirilebilir.",
    "Satış fırsatı doğmuş durumda.",
    "Bu fırsatı kaçırmayın.",
    "Şirket için al tavsiyesi veriliyor.",
    "Pozisyon açılması düşünülebilir.",
    "Getiri garantisi sunuluyor.",
    "Hisse yakında düşecek.",
    "Bu kağıt satılabilir.",
]

# ASLA yakalanmamasi gereken masum metinler.
# Cogu "al", "sat", "tut" alt dizgesini icerir; kelime siniri kontrolunun
# calistigini burada dogruluyoruz.
YAKALANMAMALI = [
    "Şirketin ticari alacakları 1,2 milyar TL seviyesinde.",
    "Yapılan analiz, faaliyet kârının arttığını gösteriyor.",
    "Kalan borç tutarı önceki döneme göre azaldı.",
    "Şirketin faaliyet alanı perakende olarak tanımlanmış.",
    "Satışlar geçen yıla göre yüzde 30 arttı.",
    "Net satış hasılatı 4,5 milyar TL olarak açıklandı.",
    "Toplam varlıklar içinde stokların payı yükseldi.",
    "İhracat gelirleri toplam satışların yarısını oluşturuyor.",
    "Yönetim kurulu kâr dağıtım politikasını onayladı.",
    "Şirket tutarlı bir büyüme kaydetti.",
    "Alacak devir hızı yavaşladı.",
    "Bu tutar, aktif toplamının yüzde beşine karşılık geliyor.",
    # Sirket devralma haberi -- "satin al" birlesigi masum
    "Şirket, rakibinin yüzde 60 hissesini satın aldı.",
    "Yönetim, iştirakin tamamını satın alınmasına karar verdi.",
    # Alacak/alan gibi "al" iceren yaygin kelimeler
    "Şüpheli alacak karşılığı ayrıldı.",
    "Faaliyet alanı genişletildi.",
]


def _ascii_kat(metin: str) -> str:
    """Test amacli: diakritikleri kaldirip sahada gorulen yazimi uretir."""
    return metin.translate(
        str.maketrans(
            {
                "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
                "ü": "u", "Ü": "U", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C",
                "â": "a", "î": "i", "û": "u",
            }
        )
    )


def _basarili(etiket: str) -> None:
    print(f"  gecti  {etiket}")


def _basarisiz(etiket: str, detay: str) -> None:
    print(f"  HATA   {etiket}")
    print(f"         {detay}")


def main() -> int:
    hata = 0

    print("Turkce normalizasyon")
    # "İ" harfi str.lower() ile "i" + birlesik nokta olarak cozumlenir;
    # normalize() bunu engellemeli
    for girdi, beklenen in (("İSTANBUL", "istanbul"), ("ILIK", "ilik"), ("Şişli", "sisli")):
        if normalize(girdi) == beklenen:
            _basarili(f"{girdi!r} -> {beklenen!r}")
        else:
            _basarisiz(girdi, f"beklenen {beklenen!r}, gelen {normalize(girdi)!r}")
            hata += 1

    # Diakritikli ve diakritiksiz yazim ayni normal bicime inmeli
    if normalize("yükselecek") == normalize("yukselecek"):
        _basarili("diakritikli/diakritiksiz yazim ayni bicime iniyor")
    else:
        _basarisiz("diakritik katlama", "iki yazim farkli normal bicim uretiyor")
        hata += 1

    print("\nYakalanmasi zorunlu ifadeler (diakritikli + diakritiksiz)")
    for cumle in YAKALANMALI:
        for etiket, varyant in (("dia ", cumle), ("ascii", _ascii_kat(cumle))):
            bulgular = [b for b in tara(varyant) if b.seviye is Seviye.YASAK]
            if bulgular:
                _basarili(f"{etiket} {varyant[:46]:<46} -> {bulgular[0].aciklama}")
            else:
                _basarisiz(f"{etiket} {varyant[:46]}", "YASAK bulgu yok (yanlis negatif)")
                hata += 1

    print("\nMasum metinler (yanlis pozitif kontrolu)")
    for cumle in YAKALANMAMALI:
        for etiket, varyant in (("dia ", cumle), ("ascii", _ascii_kat(cumle))):
            bulgular = [b for b in tara(varyant) if b.seviye is Seviye.YASAK]
            if not bulgular:
                _basarili(f"{etiket} {varyant[:46]}")
            else:
                _basarisiz(
                    f"{etiket} {varyant[:46]}",
                    f"yanlis pozitif: {bulgular[0].terim!r} ({bulgular[0].aciklama})",
                )
                hata += 1

    print("\nYasal uyari kontrolu")
    if yasal_uyari_var_mi(UYARI):
        _basarili("uyari metni tespit ediliyor")
    else:
        _basarisiz("uyari metni", "tespit edilemedi")
        hata += 1

    if yasal_uyari_var_mi(_ascii_kat(UYARI)):
        _basarili("uyari metni diakritiksiz yazimda da tespit ediliyor")
    else:
        _basarisiz("uyari metni (ascii)", "tespit edilemedi")
        hata += 1

    tamam, _ = yayinlanabilir("Şirketin net kârı arttı.")
    if not tamam:
        _basarili("uyari eksikse yayin engelleniyor")
    else:
        _basarisiz("uyari eksik", "yayina izin verildi")
        hata += 1

    tamam, bulgular = yayinlanabilir(f"Şirketin net kârı yüzde 20 arttı. {UYARI}")
    if tamam:
        _basarili("temiz icerik + uyari -> yayinlanabilir")
    else:
        engel = [b.aciklama for b in bulgular if b.seviye is Seviye.YASAK]
        _basarisiz("temiz icerik", f"engellendi: {engel}")
        hata += 1

    # Yasak ifade varsa uyari metni bulunsa bile engellenmeli
    tamam, _ = yayinlanabilir(f"Hisse kesinlikle yükselecek. {UYARI}")
    if not tamam:
        _basarili("yasak ifade, uyari metnine ragmen engelleniyor")
    else:
        _basarisiz("yasak ifade + uyari", "yayina izin verildi")
        hata += 1

    print("\n" + "=" * 60)
    print("TUM TESTLER GECTI" if hata == 0 else f"{hata} TEST BASARISIZ")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
