"""Topluluk ozeti -- uye, senaryo, oy sayilari tek komutta.

    python haber_botu/panel_ozet.py

NEDEN AYRI BIR ARAC
-------------------
Bu sayilari her seferinde elle SQL yazarak okumak, her okumada
sorguyu yeniden dogru yazmayi gerektiriyor. Bir kez yazilip
kaydedilen sorgu hem tekrarlanabilir hem de zamanla karsilastirilabilir
oluyor.

VERI D1'DE, DEPODA DEGIL
------------------------
Uyelik ve senaryolar Cloudflare D1'de yasiyor; `netaris.db` (haber
beyni) ile ilgisi yok. Bu yuzden okuma `wrangler` uzerinden gidiyor
ve AG BAGLANTISI gerektiriyor -- calismadigi yerde sessizce sifir
donmuyor, sebebini yaziyor.

SAYI YORUMLANMIYOR
------------------
Arac yalnizca sayiyor. "Uye sayisi az/cok" gibi bir yargi yok:
esigi olmayan bir olcume yargi eklemek, olcumu bozar.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"
VERITABANI = "netaris-uyelik"

#: Tek sorguda butun sayimlar. Ayri ayri sorgu atmak hem yavas hem de
#: sayimlarin FARKLI ANLARA ait olmasina yol acar -- uye eklenirken
#: okunan iki sayi tutarsiz gorunur.
SORGU = """
SELECT
  (SELECT COUNT(*) FROM uye)                                   AS uye,
  (SELECT COUNT(*) FROM uye WHERE google_id IS NOT NULL)       AS google_ile,
  (SELECT COUNT(*) FROM uye WHERE durum = 'etkin')             AS etkin,
  (SELECT COUNT(*) FROM uye WHERE son_giris IS NOT NULL)       AS giris_yapan,
  (SELECT COUNT(*) FROM senaryo)                               AS senaryo,
  (SELECT COUNT(*) FROM senaryo WHERE durum = 'yayimlandi')    AS senaryo_yayimli,
  (SELECT COUNT(*) FROM senaryo WHERE durum = 'incelemede')    AS senaryo_bekleyen,
  (SELECT COUNT(*) FROM senaryo_oy)                            AS oy,
  (SELECT COUNT(*) FROM yazi)                                  AS yazi,
  (SELECT COUNT(*) FROM yazi WHERE durum = 'yayimlandi')       AS yazi_yayimli
"""

ETIKET = (
    ("uye", "Üye"),
    ("google_ile", "  Google ile kayıtlı"),
    ("giris_yapan", "  En az bir kez giriş yapmış"),
    ("etkin", "  Etkin"),
    ("senaryo", "Senaryo"),
    ("senaryo_yayimli", "  Yayımlanmış"),
    ("senaryo_bekleyen", "  İncelemede"),
    ("oy", "Senaryo oyu"),
    ("yazi", "Üye yazısı"),
    ("yazi_yayimli", "  Yayımlanmış"),
)


def _tek_satir(sql: str) -> str:
    """Sorguyu TEK SATIRA indirir.

    wrangler `--command` cok satirli SQL'i bozuyor ve
    `incomplete input: SQLITE_ERROR` veriyor. Sorgu kaynakta okunakli
    kalsin diye cok satirli yaziliyor, gonderilirken duzlestiriliyor.
    """
    return " ".join(sql.split())


def _yazilabilir(metin: str) -> str:
    """Windows konsolunun (cp1254) yazamayacagi karakterleri ayikla.

    wrangler ciktisinda emoji var ve `print` bunu UnicodeEncodeError
    ile dusuruyordu -- yani HATA MESAJINI YAZDIRMAYA CALISIRKEN ikinci
    bir hata cikiyor, asil sebep hic gorunmuyordu.
    """
    kod = sys.stdout.encoding or "utf-8"
    return metin.encode(kod, "replace").decode(kod, "replace")


def oku() -> dict | None:
    """D1'den sayimlari okur. Basarisizsa None ve SEBEP yazilir."""
    npx = shutil.which("npx")
    if npx is None:
        print("npx bulunamadı -- Node kurulu değil.")
        return None
    try:
        s = subprocess.run(
            [npx, "wrangler", "d1", "execute", VERITABANI,
             "--remote", "--command", _tek_satir(SORGU)],
            cwd=SITE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        print("D1 sorgusu zaman aşımına uğradı.")
        return None
    # CIKIS KODUNA DEGIL CIKTIYA BAKILIYOR.
    #
    # wrangler basarili kosuda da sifir disi kod donebiliyor (Windows'ta
    # libuv kapanis iddiasi). Kodu olcut almak, calisan bir sorguyu
    # basarisiz saymak olurdu. Olcut: JSON blogu geldi mi.
    if "[" not in s.stdout:
        print("D1 okunamadı:")
        print(_yazilabilir((s.stderr or s.stdout or "")[-400:]))
        return None
    # `--json` KULLANILMIYOR. Windows'ta wrangler o bayrakla bir
    # libuv iddiasiyla cokuyor:
    #     Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)
    # Normal cikti zaten JSON blogu iceriyor; ilk `[`ten itibaren
    # ayristirmak yeterli ve platformdan bagimsiz calisiyor.
    try:
        ham = s.stdout[s.stdout.index("["):]
        return json.loads(ham)[0]["results"][0]
    except (ValueError, KeyError, IndexError) as e:
        print(f"Yanıt ayrıştırılamadı: {type(e).__name__}")
        return None


def main() -> int:
    d = oku()
    if d is None:
        return 1
    print("=== TOPLULUK ÖZETİ ===")
    for anahtar, ad in ETIKET:
        print(f"  {ad:<30}{d.get(anahtar, 0):>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
