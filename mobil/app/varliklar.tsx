// VARLIK DIZINI
//
// 75 varlik: ulkeler, kurumlar, gostergeler, emtialar. Piyasalar
// ekranindan aciliyor.
//
// DEGERI OLMAYAN VARLIK GIZLENMIYOR. Olculdu: 75 varligin 16'sinda
// deger var. Gerisi ulke ("ABD", 246 haber), kurum ("Fed") ya da
// lisansi bizde olmayan seri. Yalnizca degeri olanlari gostermek,
// sitenin en cok okunan varliklarini (ABD, Iran, Rusya, Turkiye)
// uygulamadan silmek olurdu -- oysa onlarin degeri YOK, iceri�i VAR.
//
// SIRA HABER SAYISINA GORE: okur "en cok ne konusuluyor" cevabini
// ust sirada gormek istiyor. Besleme zaten boyle siralı geliyor;
// burada yeniden siralanmiyor.

import { Stack, useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../src/api";
import { BayatUyarisi, Durum, Etiket } from "../src/bilesen";
import { useTema, yonRengi } from "../src/tema";
import { useVeri } from "../src/veri";

/** Tür kodunu okunabilir etikete çevirir. */
const TUR_ADI: Record<string, string> = {
  gosterge: "Gösterge",
  emtia: "Emtia",
  kurum: "Kurum",
  ulke: "Ülke",
  piyasa: "Piyasa",
  kripto: "Kripto",
  doviz: "Döviz",
};

/**
 * Türkçe arama için diakritik sadeleştirme.
 *
 * "turkiye" yazan okur "Türkiye"yi BULMALI. Bu depoda aynı tuzak
 * daha önce sessiz yanlış negatif üretti: desen eşleşiyor görünüyor
 * ama eşleşmiyor ve hiçbir hata çıkmıyor.
 */
function sadele(s: string): string {
  return s
    .toLocaleLowerCase("tr")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/â/g, "a")
    .replace(/î/g, "i")
    .replace(/û/g, "u");
}

export default function Varliklar() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const v = useVeri(api.varlikDizini, [], "/v1/varlik.json");
  const [arama, setArama] = useState("");

  const gorunen = useMemo(() => {
    const hepsi = v.veri?.ogeler ?? [];
    const q = sadele(arama.trim());
    if (!q) return hepsi;
    return hepsi.filter(
      (x) => sadele(x.ad).includes(q) || sadele(x.kod).includes(q),
    );
  }, [v.veri, arama]);

  return (
    <>
      <Stack.Screen options={{ title: "Varlıklar" }} />
      <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
        <View style={{ padding: 16, paddingBottom: 8 }}>
          <TextInput
            value={arama}
            onChangeText={setArama}
            placeholder="Varlık ara…"
            placeholderTextColor={t.renk.notr}
            autoCapitalize="none"
            autoCorrect={false}
            style={[
              d.girdi,
              {
                backgroundColor: t.renk.panel2,
                borderColor: t.renk.cizgi,
                color: t.renk.yazi,
                borderRadius: t.r.kucuk,
              },
            ]}
            accessibilityLabel="Varlık ara"
          />
        </View>

        <BayatUyarisi bayat={v.bayat} an={v.bayatAn}
                    hata={v.hata} />

      <FlatList
          data={gorunen}
          keyExtractor={(x) => x.kod}
          contentContainerStyle={{ paddingBottom: alt + 28 }}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/varlik/${item.kod}`)}
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
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={[d.ad, { color: t.renk.yazi }]}>{item.ad}</Text>
                <View style={d.ufakSatir}>
                  {item.tur ? (
                    <Etiket metin={TUR_ADI[item.tur] || item.tur} />
                  ) : null}
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    {item.haber_sayisi} haber
                  </Text>
                </View>
              </View>

              {/* DEGER VARSA basiliyor, yoksa bos birakiliyor --
                  "veri yok" yazmak gereksiz gurultu olurdu; ulke ve
                  kurum sayfalarinda deger ZATEN beklenmiyor. */}
              {item.veri_var && item.deger ? (
                <View style={{ alignItems: "flex-end", gap: 2 }}>
                  <Text style={[d.deger, { color: t.renk.yazi }]}>
                    {item.deger}
                  </Text>
                  {item.yon ? (
                    <Text
                      style={[d.ufak, { color: yonRengi(t, item.yon) }]}
                    >
                      {item.yon === "artis"
                        ? "▲"
                        : item.yon === "azalis"
                          ? "▼"
                          : "—"}
                    </Text>
                  ) : null}
                </View>
              ) : null}
            </Pressable>
          )}
          ListEmptyComponent={
            <Durum
              yukleniyor={v.yukleniyor}
              hata={v.engelleyenHata}
              bos={!v.yukleniyor && !v.hata}
              bosMetin={
                arama ? "Eşleşen varlık yok." : "Varlık bulunamadı."
              }
              yenile={v.yenile}
            />
          }
          ListFooterComponent={
            v.veri && gorunen.length > 0 ? (
              <Text style={[d.not, { color: t.renk.notr }]}>
                {gorunen.length} varlık gösteriliyor
                {arama ? ` (${v.veri.toplam} içinden)` : ""}. Sıra, o
                varlık hakkında yayımlanan haber sayısına göre.
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
    height: 46,
    fontSize: 15,
  },
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
  ad: { fontSize: 15, fontWeight: "600" },
  ufakSatir: { flexDirection: "row", alignItems: "center", gap: 7 },
  ufak: { fontSize: 12 },
  deger: { fontSize: 16, fontWeight: "700", fontVariant: ["tabular-nums"] },
  not: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginTop: 12,
  },
});
