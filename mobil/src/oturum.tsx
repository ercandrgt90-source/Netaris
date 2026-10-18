// OTURUM -- jeton CIHAZIN GUVENLI DEPOSUNDA.
//
// `expo-secure-store` iOS'ta Keychain, Android'de EncryptedSharedPreferences
// kullaniyor. Jetonu `AsyncStorage`a koymak duz metin dosyasina
// yazmak olurdu: rootlu/jailbreakli bir cihazda ya da yedekten
// okunabilir.
//
// WORKER TARAFI: `giris` cagrisina `istemci: "uygulama"` eklendiginde
// jeton yanit govdesinde donuyor. Tarayici akisi degismedi -- orada
// jeton hala yalnizca HttpOnly cerezde ve sayfadaki JavaScript onu
// okuyamiyor. Gerekce `worker.js` icindeki `uygulamaMi` yaninda.
//
// MISAFIR KULLANIM ENGELLENMIYOR: icerigin tamami oturumsuz
// okunabiliyor. Oturum yalnizca favoriler, kaydedilenler ve senaryo
// yazmak icin gerekiyor.

import * as SecureStore from "expo-secure-store";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import * as api from "./api";

const ANAHTAR = "netaris.oturum.jeton";

export type OturumDurumu = {
  uye: api.Uye;
  jeton: string | null;
  /** Ilk okuma bitene kadar true -- ekranlar "giris yapilmamis" diye
   *  yanlis karar vermesin. */
  hazirlaniyor: boolean;
  hata: string | null;
  girisYap: (eposta: string, parola: string) => Promise<boolean>;
  cikisYap: () => Promise<void>;
};

const Baglam = createContext<OturumDurumu>({
  uye: null,
  jeton: null,
  hazirlaniyor: true,
  hata: null,
  girisYap: async () => false,
  cikisYap: async () => {},
});

/** Guvenli depo bazi ortamlarda (web, kisitli cihaz) yok. */
async function depoOku(): Promise<string | null> {
  try {
    if (!(await SecureStore.isAvailableAsync())) return null;
    return await SecureStore.getItemAsync(ANAHTAR);
  } catch {
    // SESSIZ: depo okunamazsa kullanici misafir olarak devam ediyor.
    // Kullanicinin yapabilecegi bir sey yok ve icerik zaten acik.
    return null;
  }
}

async function depoYaz(jeton: string | null): Promise<void> {
  try {
    if (!(await SecureStore.isAvailableAsync())) return;
    if (jeton) await SecureStore.setItemAsync(ANAHTAR, jeton);
    else await SecureStore.deleteItemAsync(ANAHTAR);
  } catch {
    // Yazilamadiysa oturum yalnizca bu acilista gecerli olur.
  }
}

export function OturumSaglayici({ children }: { children: React.ReactNode }) {
  const [jeton, setJeton] = useState<string | null>(null);
  const [uye, setUye] = useState<api.Uye>(null);
  const [hazirlaniyor, setHazirlaniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);

  // ACILIS: depodaki jetonu oku ve SUNUCUYA DOGRULAT.
  //
  // Yalnizca jetonun varligina guvenmek yetmez: jeton sunucuda
  // suresi dolmus ya da silinmis olabilir (baska bir cihazdan cikis,
  // 90 gun asimi). O durumda uygulama "giris yapilmis" gorunur ama
  // her istek 401 doner -- kullanici icin aciklanamaz bir hal.
  useEffect(() => {
    let birakildi = false;
    (async () => {
      const kayitli = await depoOku();
      if (birakildi) return;
      if (!kayitli) {
        setHazirlaniyor(false);
        return;
      }
      try {
        const u = await api.ben(kayitli);
        if (birakildi) return;
        if (u) {
          setJeton(kayitli);
          setUye(u);
        } else {
          // Jeton artik gecerli degil -- depodan TEMIZLENIYOR.
          await depoYaz(null);
        }
      } catch {
        // AG HATASI JETONU SILMIYOR: cevrimdisi acilista jetonu
        // atmak, kullaniciyi internete baglandiginda yeniden giris
        // yapmaya zorlamak olurdu.
        if (!birakildi) setJeton(kayitli);
      } finally {
        if (!birakildi) setHazirlaniyor(false);
      }
    })();
    return () => {
      birakildi = true;
    };
  }, []);

  const girisYap = useCallback(async (eposta: string, parola: string) => {
    setHata(null);
    try {
      const c = await api.giris(eposta, parola);
      if (!c.jeton) {
        // Sunucu jeton dondurmediyse bu bir KURULUM hatasi:
        // `istemci: "uygulama"` isleniyor olmali. Sessizce "giris
        // oldu" demek, sonraki her istegin 401 donmesi demekti.
        setHata(
          "Sunucu oturum jetonu döndürmedi. Uygulama sürümü " +
            "güncellenmeli olabilir.",
        );
        return false;
      }
      await depoYaz(c.jeton);
      setJeton(c.jeton);
      setUye(c.uye);
      return true;
    } catch (h) {
      setHata(h instanceof Error ? h.message : "Giriş yapılamadı.");
      return false;
    }
  }, []);

  const cikisYap = useCallback(async () => {
    // SUNUCUYA DA BILDIRILIYOR: yalnizca yerel jetonu silmek, jetonu
    // sunucuda GECERLI birakirdi. `cikis` ucu `jetonOku` kullaniyor,
    // yani Bearer ile gelen cikis da oturumu gercekten kapatiyor.
    try {
      if (jeton) await api.cikis(jeton);
    } catch {
      // Ag hatasi olsa da yerel oturum kapatiliyor: kullanici
      // "cikis yaptim" dedi ve ekranda oyle gorunmeli.
    }
    await depoYaz(null);
    setJeton(null);
    setUye(null);
    setHata(null);
  }, [jeton]);

  const deger = useMemo<OturumDurumu>(
    () => ({ uye, jeton, hazirlaniyor, hata, girisYap, cikisYap }),
    [uye, jeton, hazirlaniyor, hata, girisYap, cikisYap],
  );

  return <Baglam.Provider value={deger}>{children}</Baglam.Provider>;
}

export const useOturum = () => useContext(Baglam);
