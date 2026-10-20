// OKUMA GECMISI
//
// Veri CIHAZDAN geliyor, aga cikilmiyor (`src/gecmis.ts`). Bu yuzden
// burada `useVeri` kullanilmiyor: yuklenme, bayatlik ve ag hatasi
// kavramlarinin hicbiri gecerli degil. Olmayan bir hata halini
// gostermek, okura yanlis bir sey soylemek olurdu.
//
// EKRANA DONUNCE TAZELENIYOR: okur bir haberi acip geri geldiginde
// listede gormeli. `useFocusEffect` tam bunun icin.

import { Stack, useFocusEffect, useRouter } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  Alert,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Etiket, tarihTR } from "../src/bilesen";
import * as gecmis from "../src/gecmis";
import { useTema } from "../src/tema";

export default function Gecmis() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const [kayitlar, setKayitlar] = useState<gecmis.Kayit[] | null>(null);

  useFocusEffect(
    useCallback(() => {
      let birakildi = false;
      void gecmis.oku().then((k) => {
        if (!birakildi) setKayitlar(k);
      });
      return () => {
        birakildi = true;
      };
    }, []),
  );

  const hepsiniSil = () => {
    Alert.alert(
      "Okuma geçmişi silinsin mi?",
      "Bu liste yalnızca bu cihazda tutuluyor. Silmek geri alınamaz.",
      [
        { text: "Vazgeç", style: "cancel" },
        {
          text: "Sil",
          style: "destructive",
          onPress: () => {
            void gecmis.temizle().then(() => setKayitlar([]));
          },
        },
      ],
    );
  };

  const bos = kayitlar !== null && kayitlar.length === 0;

  return (
    <>
      <Stack.Screen options={{ title: "Okuma geçmişi" }} />
      <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
        <FlatList
          data={kayitlar ?? []}
          keyExtractor={(x) => `${x.tur}:${x.slug}`}
          contentContainerStyle={{ paddingBottom: alt + 28, paddingTop: 12 }}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/${item.tur}/${item.slug}`)}
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
              <View style={{ flex: 1, gap: 6 }}>
                <Text style={[d.baslik, { color: t.renk.yazi }]}
                      numberOfLines={3}>
                  {item.baslik}
                </Text>
                <View style={d.ufakSatir}>
                  <Etiket metin={item.tur === "haber" ? "Haber" : "Analiz"} />
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    {tarihTR(item.an.slice(0, 10))}
                    {item.an.length >= 16 ? ` · ${item.an.slice(11, 16)}` : ""}
                  </Text>
                </View>
              </View>
            </Pressable>
          )}
          ListHeaderComponent={
            kayitlar && kayitlar.length > 0 ? (
              <View style={d.ustSatir}>
                <Text style={[d.not, { color: t.renk.notr }]}>
                  {kayitlar.length} kayıt · yalnızca bu cihazda
                </Text>
                <Pressable
                  onPress={hepsiniSil}
                  accessibilityRole="button"
                  hitSlop={8}
                  style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
                >
                  <Text style={[d.sil, { color: t.renk.uyari }]}>
                    Geçmişi sil
                  </Text>
                </Pressable>
              </View>
            ) : undefined
          }
          ListEmptyComponent={
            bos ? (
              <View style={d.orta}>
                <Text style={[d.bosBaslik, { color: t.renk.yazi }]}>
                  Geçmiş boş
                </Text>
                <Text style={[d.bosMetin, { color: t.renk.yazi3 }]}>
                  Okuduğun haber ve analizler burada birikir. Liste
                  yalnızca bu cihazda tutulur, hiçbir yere gönderilmez.
                </Text>
              </View>
            ) : undefined
          }
          ListFooterComponent={
            kayitlar && kayitlar.length >= gecmis.EN_COK ? (
              <Text style={[d.not, { color: t.renk.notr, marginTop: 12 }]}>
                En fazla {gecmis.EN_COK} kayıt tutuluyor; daha eskiler
                listeden düşüyor.
              </Text>
            ) : undefined
          }
        />
      </View>
    </>
  );
}

const d = StyleSheet.create({
  satir: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 14,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 64,
  },
  baslik: { fontSize: 15, fontWeight: "600", lineHeight: 21 },
  ufakSatir: { flexDirection: "row", alignItems: "center", gap: 7 },
  ufak: { fontSize: 12 },
  ustSatir: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginHorizontal: 16,
    marginBottom: 10,
    gap: 12,
  },
  not: { fontSize: 11, lineHeight: 16, marginHorizontal: 16, flex: 1 },
  sil: { fontSize: 13, fontWeight: "600" },
  orta: { padding: 32, gap: 8, alignItems: "center" },
  bosBaslik: { fontSize: 16, fontWeight: "700" },
  bosMetin: { fontSize: 13, lineHeight: 19, textAlign: "center" },
});
