// VERI CEKME KANCASI
//
// Tek bir yerden: yukleniyor / hata / veri. Her ekranin kendi
// `useEffect`ini yazmasi, her birinin hata halini AYRI unutmasi
// demekti -- ve unutulan hata hali bos bir ekran olarak gorunur,
// kullanici da uygulamanin dondugunu sanir.
//
// BIRAKMA KORUMASI: ekran kapandiktan sonra gelen cevap state'e
// yazilmiyor. Yazilsa React uyari basar ve daha onemlisi kapanmis
// ekranin verisi bir sonrakine karisabilir.

import { useCallback, useEffect, useState } from "react";

import { AgHatasi } from "./api";

export type Durum<T> = {
  veri: T | null;
  yukleniyor: boolean;
  hata: string | null;
  yenile: () => void;
};

export function useVeri<T>(
  cek: () => Promise<T>,
  bagimliliklar: unknown[] = [],
): Durum<T> {
  const [veri, setVeri] = useState<T | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const [tur, setTur] = useState(0);

  const yenile = useCallback(() => setTur((t) => t + 1), []);

  useEffect(() => {
    let birakildi = false;
    setYukleniyor(true);
    setHata(null);
    cek()
      .then((d) => {
        if (birakildi) return;
        setVeri(d);
        setYukleniyor(false);
      })
      .catch((h: unknown) => {
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
      });
    return () => {
      birakildi = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tur, ...bagimliliklar]);

  return { veri, yukleniyor, hata, yenile };
}
