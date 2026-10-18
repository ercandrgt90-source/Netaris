// ARAMA
//
// Sartname 12. bolum: uygulama genelinde sirket, sembol, haber,
// arastirma ve makro konu aramasi; sonuclar ICERIK TURUNE GORE
// ayrilmis.
//
// KATLAMA TABLOSU BESLEMEDEN GELIYOR. Turkce diakritik katlamasi
// ("turkiye" -> "Türkiye") sitede iki yerde duruyor ve bir sinama
// ikisinin ayni oldugunu dogruluyor. Uygulamaya ucuncu bir kopya
// yazmak o riski bir kat daha buyutmek olurdu -- ve o kusur
// hicbir hata uretmiyor, yalnizca okur aradigini bulamiyor.
//
// Tablo gelmezse YEDEK kullaniliyor: arama calismaya devam
// etmeli, yalnizca katlama eksik kalir.
//
// DIZIN BIR KEZ INDIRILIYOR ve bellekte kaliyor. 1300 kayitlik
// kompakt dizin (~120 KB); sitenin 563 KB'lik dizini mobil icin
// agir oldugundan ayri bir dizin uretiliyor.

import { Stack, useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../src/api";
import { Durum, Etiket, tarihTR } from "../src/bilesen";
import { useTema } from "../src/tema";
import { useVeri } from "../src/veri";

/** Besleme ulasmazsa kullanilan yedek tablo. */
const YEDEK_KATLAMA: Record<string, string> = {
  ı: "i", İ: "i", I: "i", ş: "s", Ş: "s", ğ: "g", Ğ: "g",
  ü: "u", Ü: "u", ö: "o", Ö: "o", ç: "c", Ç: "c",
  â: "a", î: "i", û: "u",
};

function katlayici(tablo: Record<string, string>) {
  const t = Object.keys(tablo).length ? tablo : YEDEK_KATLAMA;
  return (m: string) => {
    let c = "";
    for (const h of m) c += t[h] !== undefined ? t[h] : h;
    return c.toLowerCase();
  };
}

const TUR_ADI: Record<string, string> = {
  haber: "Haberler",
  analiz: "Araştırmalar",
  varlik: "Varlıklar",
};

const TUR_SIRA = ["analiz", "haber", "varlik"];

/** Sonuç sayısı — tek seferde basılan en fazla kayıt.
 *
 *  Sınırsız liste, iki harflik bir sorguda 1300 satır basmak
 *  demekti; telefonda ilk çizim donar. */
const EN_COK = 60;

export default function Ara() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const dz = useVeri(api.aramaDizini);
  const [sorgu, setSorgu] = useState("");
  const [tur, setTur] = useState("");

  const katla = useMemo(
    () => katlayici(dz.veri?.katlama ?? {}),
    [dz.veri],
  );

  const sonuclar = useMemo(() => {
    const q = katla(sorgu.trim());
    if (q.length < 2 || !dz.veri) return [];
    const bulunan = dz.veri.kayitlar.filter((k) => {
      if (tur && k.t !== tur) return false;
      return (
        katla(k.b).includes(q) ||
        katla(k.k || "").includes(q) ||
        katla(k.c || "").includes(q)
      );
    });
    // EN YENI USTTE; tarihsiz (varlik) kayitlar sona.
    bulunan.sort((a, b) => (b.d || "").localeCompare(a.d || ""));
    return bulunan.slice(0, EN_COK);
  }, [sorgu, tur, dz.veri, katla]);

  const sayim = useMemo(() => {
    const s: Record<string, number> = {};
    for (const k of sonuclar) s[k.t] = (s[k.t] || 0) + 1;
    return s;
  }, [sonuclar]);

  const ac = (k: api.AramaKaydi) => {
    if (k.t === "haber") router.push(`/haber/${k.s}`);
    else if (k.t === "analiz") router.push(`/analiz/${k.s}`);
    else router.push(`/varlik/${k.s}`);
  };

  const kisa = sorgu.trim().length > 0 && katla(sorgu.trim()).length < 2;

  return (
    <>
      <Stack.Screen options={{ title: "Ara" }} />
      <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
        <View style={{ padding: 16, paddingBottom: 8, gap: 10 }}>
          <TextInput
            value={sorgu}
            onChangeText={setSorgu}
            placeholder="Şirket, haber, araştırma, gösterge…"
            placeholderTextColor={t.renk.notr}
            autoCapitalize="none"
            autoCorrect={false}
            autoFocus
            returnKeyType="search"
            style={[
              d.girdi,
              {
                backgroundColor: t.renk.panel2,
                borderColor: t.renk.cizgi,
                color: t.renk.yazi,
                borderRadius: t.r.kucuk,
              },
            ]}
            accessibilityLabel="Arama"
          />

          {/* ICERIK TURUNE GORE AYIRMA -- sartnamenin istedigi. */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: 8 }}
          >
            {[{ kod: "", ad: "Tümü" }].concat(
              TUR_SIRA.map((x) => ({ kod: x, ad: TUR_ADI[x] })),
            ).map((x) => {
              const aktif = x.kod === tur;
              const n = x.kod ? sayim[x.kod] : sonuclar.length;
              return (
                <Pressable
                  key={x.kod || "hepsi"}
                  onPress={() => setTur(x.kod)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: aktif }}
                  style={[
                    d.cip,
                    {
                      backgroundColor: aktif ? t.renk.vurgu : t.renk.panel,
                      borderColor: aktif ? t.renk.vurgu : t.renk.cizgi,
                      borderRadius: t.r.kucuk,
                    },
                  ]}
                >
                  <Text
                    style={{
                      color: aktif ? t.renk.ustYazi : t.renk.yazi2,
                      fontSize: 13,
                      fontWeight: "600",
                    }}
                  >
                    {x.ad}
                    {sorgu.trim() && n ? ` (${n})` : ""}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        <FlatList
          data={sonuclar}
          keyExtractor={(k, i) => `${k.t}-${k.s}-${i}`}
          contentContainerStyle={{ paddingBottom: alt + 28 }}
          keyboardShouldPersistTaps="handled"
          renderItem={({ item }) => (
            <Pressable
              onPress={() => ac(item)}
              accessibilityRole="button"
              style={({ pressed }) => [
                d.satir,
                {
                  backgroundColor: t.renk.panel,
                  borderColor: t.renk.cizgi,
                  borderRadius: t.r.orta,
                  opacity: pressed ? 0.75 : 1,
                },
              ]}
            >
              <View style={d.ufakSatir}>
                <Etiket
                  metin={TUR_ADI[item.t] || item.t}
                  renk={t.renk.vurgu}
                />
                {item.c ? <Etiket metin={item.c} /> : null}
                {item.d ? (
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    {tarihTR(item.d)}
                  </Text>
                ) : null}
              </View>
              <Text style={[d.baslik, { color: t.renk.yazi }]}>{item.b}</Text>
              {item.k ? (
                <Text style={[d.ufak, { color: t.renk.notr }]}>{item.k}</Text>
              ) : null}
            </Pressable>
          )}
          ListEmptyComponent={
            dz.yukleniyor || dz.hata ? (
              <Durum
                yukleniyor={dz.yukleniyor}
                hata={dz.hata}
                yenile={dz.yenile}
              />
            ) : (
              <View style={d.orta}>
                <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>
                  {!sorgu.trim()
                    ? `${dz.veri?.toplam ?? 0} kayıt içinde arayın.`
                    : kisa
                      ? "En az iki harf yazın."
                      : "Sonuç bulunamadı."}
                </Text>
              </View>
            )
          }
          ListFooterComponent={
            sonuclar.length >= EN_COK ? (
              <Text style={[d.not, { color: t.renk.notr }]}>
                İlk {EN_COK} sonuç gösteriliyor. Aramayı daraltın.
              </Text>
            ) : undefined
          }
        />
      </View>
    </>
  );
}

const d = StyleSheet.create({
  girdi: {
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 13,
    height: 48,
    fontSize: 15,
  },
  cip: {
    paddingHorizontal: 13,
    paddingVertical: 9,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 40,
    justifyContent: "center",
  },
  satir: {
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 13,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 5,
    minHeight: 60,
  },
  ufakSatir: { flexDirection: "row", alignItems: "center", gap: 7, flexWrap: "wrap" },
  baslik: { fontSize: 15, fontWeight: "600", lineHeight: 21 },
  ufak: { fontSize: 12 },
  orta: { padding: 28, alignItems: "center" },
  ipucu: { fontSize: 14, textAlign: "center", lineHeight: 20 },
  not: {
    fontSize: 11,
    textAlign: "center",
    marginHorizontal: 16,
    marginTop: 10,
  },
});
