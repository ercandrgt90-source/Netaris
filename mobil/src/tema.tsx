// TEMA -- renkler `stil.css`ten geliyor, uygulamaya GOMULU DEGIL.
//
// NEDEN BOYLE: palet iki yerde dururken biri duzelir, oteki
// unutulur. Renkte ayrilma hicbir hata uretmez; yalnizca uygulama
// ile site farkli gorunur ve kimse ne zaman ayrildigini bilemez.
//
// AKIS:
//   1. Ilk kare `tema-yedek.ts` ile boyanir (uretilmis, CSS'ten).
//   2. `/v1/tema.json` gelince uzerine yazilir.
//
// Yedek olmasa ilk kare renksiz basilirdi; ag beklenirken bos bir
// ekran gostermek, kullanicinin gordugu ILK seyi bozuk yapar.
//
// SITENIN KOYU TEMASI ZATEN VAR ve burada aynen kullaniliyor:
// sicak siyah zemin (#14130f), parlak teal vurgu (#2dd4bf),
// erisilebilirlik icin parlatilmis artis/azalis renkleri. Uygulamaya
// yeni bir palet uydurulmadi.

import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useColorScheme } from "react-native";

import * as api from "./api";
import { ACIK_YEDEK, KOYU_YEDEK, Palet } from "./tema-yedek";

export type TemaAdi = "acik" | "koyu";

export type Tema = {
  ad: TemaAdi;
  /** Ham jeton sozlugu -- `stil.css` adlariyla. */
  jeton: Palet;
  renk: {
    zemin: string;
    zemin2: string;
    panel: string;
    panel2: string;
    cizgi: string;
    cizgiParlak: string;
    yazi: string;
    yazi2: string;
    yazi3: string;
    vurgu: string;
    vurguKoyu: string;
    artis: string;
    azalis: string;
    uyari: string;
    notr: string;
    ustZemin: string;
    ustYazi: string;
  };
  /** Bosluk ve yaricap olcegi -- CSS ile ayni degerler. */
  r: { mini: number; kucuk: number; orta: number };
};

const SAYISAL = (deger: string | undefined, yedek: number): number => {
  if (!deger) return yedek;
  const n = parseFloat(deger);
  return Number.isFinite(n) ? n : yedek;
};

function temaKur(ad: TemaAdi, jeton: Palet): Tema {
  // `al` jeton yoksa SESSIZCE seffaf birakmiyor, acikca bir yedek
  // veriyor: seffaf bir yuzey ekranda "hicbir sey" demek ve hata
  // olarak gorunmez.
  const al = (anahtar: string, yedek: string) => jeton[anahtar] || yedek;
  return {
    ad,
    jeton,
    renk: {
      zemin: al("zemin", ad === "koyu" ? "#14130f" : "#f3f2ee"),
      zemin2: al("zemin-2", ad === "koyu" ? "#1c1a15" : "#eceae4"),
      panel: al("panel", ad === "koyu" ? "#1e1c17" : "#ffffff"),
      panel2: al("panel-2", ad === "koyu" ? "#26231d" : "#f7f6f2"),
      cizgi: al("cizgi", ad === "koyu" ? "#33302a" : "#e4e1d9"),
      cizgiParlak: al("cizgi-parlak", ad === "koyu" ? "#4e493f" : "#c7c2b6"),
      yazi: al("yazi", ad === "koyu" ? "#f3f1ea" : "#17160f"),
      yazi2: al("yazi-2", ad === "koyu" ? "#c0bbaf" : "#4a463b"),
      yazi3: al("yazi-3", ad === "koyu" ? "#978f82" : "#6a6458"),
      vurgu: al("vurgu", ad === "koyu" ? "#2dd4bf" : "#09726d"),
      vurguKoyu: al("vurgu-koyu", ad === "koyu" ? "#14b8a6" : "#055c58"),
      artis: al("artis", ad === "koyu" ? "#5fc45c" : "#2f7a2e"),
      azalis: al("azalis", ad === "koyu" ? "#fa6b73" : "#bb1f2e"),
      uyari: al("uyari", ad === "koyu" ? "#e0a44a" : "#90540a"),
      notr: al("notr", ad === "koyu" ? "#8d8679" : "#6a6458"),
      ustZemin: al("ust-zemin", "#15130d"),
      ustYazi: al("ust-yazi", "#f5f3ec"),
    },
    r: {
      mini: SAYISAL(jeton["r-mini"], 6),
      kucuk: SAYISAL(jeton["r-kucuk"], 10),
      orta: SAYISAL(jeton["r"], 14),
    },
  };
}

type Baglam = { tema: Tema; tazeMi: boolean };

const TemaBaglami = createContext<Baglam>({
  tema: temaKur("acik", ACIK_YEDEK),
  tazeMi: false,
});

export function TemaSaglayici({ children }: { children: React.ReactNode }) {
  // Isletim sisteminin temasi izleniyor. `userInterfaceStyle`
  // "automatic" oldugu icin bu deger kullanicinin sistem ayarini
  // takip ediyor -- sitedeki `prefers-color-scheme` davranisinin
  // aynisi.
  const sistem = useColorScheme();
  const ad: TemaAdi = sistem === "dark" ? "koyu" : "acik";
  const [uzak, setUzak] = useState<{ acik: Palet; koyu: Palet } | null>(null);

  useEffect(() => {
    let birakildi = false;
    api
      .tema()
      .then((t) => {
        if (!birakildi) setUzak({ acik: t.acik, koyu: t.koyu });
      })
      .catch(() => {
        // SESSIZ GECILIYOR VE BU BILINCLI: tema okunamadiginda
        // uygulama yedek paletle tamamen calisiyor. Kullaniciya hata
        // gostermek, onun icin yapabilecegi bir sey olmadigi halde
        // ekrani bozmak olurdu. `tazeMi` bayragi gelistirici icin
        // duruyor.
      });
    return () => {
      birakildi = true;
    };
  }, []);

  const deger = useMemo<Baglam>(() => {
    const yedek = ad === "koyu" ? KOYU_YEDEK : ACIK_YEDEK;
    const jeton = uzak ? (ad === "koyu" ? uzak.koyu : uzak.acik) : yedek;
    return { tema: temaKur(ad, jeton), tazeMi: uzak !== null };
  }, [ad, uzak]);

  return (
    <TemaBaglami.Provider value={deger}>{children}</TemaBaglami.Provider>
  );
}

export const useTema = () => useContext(TemaBaglami).tema;
export const useTemaTaze = () => useContext(TemaBaglami).tazeMi;

/** Yon -> renk. Sifir degisim NOTR, artis/azalis degil. */
export function yonRengi(tema: Tema, yon: string): string {
  if (yon === "artis") return tema.renk.artis;
  if (yon === "azalis") return tema.renk.azalis;
  return tema.renk.notr;
}
