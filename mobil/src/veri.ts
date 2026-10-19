// VERI CEKME KANCASI
//
// Tek bir yerden: yukleniyor / hata / veri / BAYAT. Her ekranin
// kendi `useEffect`ini yazmasi, her birinin hata halini AYRI
// unutmasi demekti -- ve unutulan hata hali bos bir ekran olarak
// gorunur, kullanici da uygulamanin dondugunu sanir.
//
// BIRAKMA KORUMASI: ekran kapandiktan sonra gelen cevap state'e
// yazilmiyor. Yazilsa React uyari basar ve daha onemlisi kapanmis
// ekranin verisi bir sonrakine karisabilir.
//
// ONBELLEK AKISI
// --------------
//   1. Onbellekte varsa HEMEN goster (bayat isaretli)
//   2. Agdan cek, gelirse uzerine yaz ve onbellege koy
//   3. Ag dusuerse onbellektekini KORU -- ama hata da bildir
//
// Ucuncu madde onemli: cevrimdisiyken eski haberi gostermek
// faydali, ama onu TAZE gibi gostermek degil. Ikisi birden
// donuyor; ekran `bayat` bayragini basiyor.

import { useCallback, useEffect, useState } from "react";

import { AgHatasi } from "./api";
import * as onbellek from "./onbellek";

export type Durum<T> = {
  veri: T | null;
  yukleniyor: boolean;
  hata: string | null;
  /** Gösterilen veri ÖNBELLEKTEN mi geldi. */
  bayat: boolean;
  /**
   * Ekranı BOŞ bırakan hata -- yani gösterilecek hiçbir şey yokken
   * oluşan hata.
   *
   * NEDEN AYRI ALAN: önbellekten içerik geldiğinde `hata` yine dolu
   * (tazelenemedi) ama ekran BOŞ DEĞİL. İkisini ayırmazsak ekranda
   * "Veri alınamadı · Yeniden dene" kutusu, hemen ALTINDA da gerçek
   * veri görünüyor -- okura çelişkili iki şey söylenmiş oluyor.
   *
   * Gerçek tarayıcıda görüldü (2026-10-19, çevrimdışı sınaması).
   *
   * Kural kancada: her ekranın ayrı ayrı hatırlaması gereken bir
   * nezaket değil, yapısal bir ayrım.
   */
  engelleyenHata: string | null;
  /** Önbellekten geldiyse ne zaman alındığı (ISO). */
  bayatAn: string | null;
  yenile: () => void;
};

export function useVeri<T>(
  cek: () => Promise<T>,
  bagimliliklar: unknown[] = [],
  /**
   * Önbellek anahtarı -- besleme yolu. Verilmezse önbellek
   * KULLANILMIYOR: `/api/*` uçları (canlı akış, oturum, üye
   * verisi) bilinçli olarak önbelleklenmiyor.
   */
  onbellekYolu?: string,
): Durum<T> {
  const [veri, setVeri] = useState<T | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const [bayat, setBayat] = useState(false);
  const [bayatAn, setBayatAn] = useState<string | null>(null);
  const [tur, setTur] = useState(0);

  const yenile = useCallback(() => setTur((t) => t + 1), []);

  useEffect(() => {
    let birakildi = false;
    setYukleniyor(true);
    setHata(null);

    (async () => {
      // 1. ONBELLEK ONCE -- varsa hemen goster.
      if (onbellekYolu) {
        const o = await onbellek.oku<T>(onbellekYolu);
        if (o && !birakildi) {
          setVeri(o.veri);
          setBayat(true);
          setBayatAn(o.an);
          // `yukleniyor` KAPATILIYOR: ekran artik bos degil.
          // Taze veri gelince sessizce uzerine yazilacak.
          setYukleniyor(false);
        }
      }

      // 2. AGDAN CEK.
      try {
        const d = await cek();
        if (birakildi) return;
        setVeri(d);
        setBayat(false);
        setBayatAn(null);
        setYukleniyor(false);
        if (onbellekYolu) void onbellek.yaz(onbellekYolu, d);
      } catch (h: unknown) {
        if (birakildi) return;
        // HATA METNI KORUNUYOR. "Bir seyler ters gitti" okura hicbir
        // sey anlatmiyor; 404 ile baglanti kopmasi ayri sorunlar ve
        // okurun yapabilecegi sey de ayri.
        setHata(
          h instanceof AgHatasi
            ? h.message
            : h instanceof Error
              ? h.message
              : "Bilinmeyen hata.",
        );
        setYukleniyor(false);
        // ONBELLEKTEKI VERI KORUNUYOR: ag dustu diye okurun
        // elindeki icerigi silmek, cevrimdisi okumanin tam tersi
        // olurdu. `bayat` bayragi zaten acik.
      }
    })();

    return () => {
      birakildi = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tur, onbellekYolu, ...bagimliliklar]);

  return {
    veri,
    yukleniyor,
    hata,
    // Veri VARSA hata ekrani engellemiyor: bayat uyarisi zaten
    // sebebi yaziyor.
    engelleyenHata: veri === null ? hata : null,
    bayat,
    bayatAn,
    yenile,
  };
}
