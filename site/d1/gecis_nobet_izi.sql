-- NOBETCININ KARAR IZI
--
-- NEDEN VAR
-- ---------
-- Nobetci her on dakikada bir bakiyor ve dort karardan birini
-- veriyor. Hicbiri kalici iz birakmiyordu: tek kayit
-- `console.log`du -- Cloudflare gunlugu, Logpush olmadan saklanmiyor
-- ve depodan okunamiyor.
--
-- Sonucu olculdu (2026-09-15): otomasyon kosularinda 155 dakikalik
-- bir bosluk vardi ve `calisma` tablosunda o araliga ait HIC kayit
-- yoktu -- yani kosu dusmedi, HIC BASLAMADI. "Nobetci atesledi de
-- GitHub mi almadi, yoksa nobetci hic bakmadi mi" sorusu
-- CEVAPLANAMADI.
--
-- Bu, siteyi 13 gun donduran arizanin tam olarak ayni kor noktasi:
-- sistem calisiyor gorunuyor, calismadigini gosteren bir olcum yok.
--
-- `durum` alani neden ayri: "taze oldugu icin dokunmadim" ile
-- "bakamadim" AYNI SEY DEGIL. Ikisi de tetik uretmiyor ama biri
-- saglik, digeri ariza.
CREATE TABLE IF NOT EXISTS nobet_izi (
  an     TEXT NOT NULL,          -- ISO 8601, UTC
  yas    REAL,                   -- icerik yasi (saat); bilinmiyorsa NULL
  karar  TEXT NOT NULL,          -- jetonsuz | yas_bilinmiyor | taze
                                 -- | tetiklendi | tetik_hatasi
  yanit  INTEGER                 -- GitHub dispatch HTTP kodu
);

CREATE INDEX IF NOT EXISTS nobet_izi_an ON nobet_izi(an);
