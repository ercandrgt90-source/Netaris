// KOSULLU SENARYOLAR
//
// Netaris'in ayirt edici islevi. Yapisi KORUNUYOR: hangi gelisme
// (capa), hangi kosul gerceklesirse, hangi sonuc beklenir, hangi
// degerlendirme ufku.
//
// IKI KURAL EKRANDA GORUNUR:
//
// 1. SENARYO TAHMIN DEGIL. Kesin ongoru ya da garanti edilmis getiri
//    gibi sunulmuyor; ekranin basinda bu acikca yaziyor.
// 2. KULLANICI ICERIGI EDITORYAL ICERIKTEN AYRI. Her senaryoda yazar
//    adi basiliyor -- bunu Netaris yazmadi, bir uye yazdi.
//
// YAZMA ISLEMI HENUZ YOK ve sahte bir dugme KONMADI: senaryo
// olusturma oturum gerektiriyor, oturum da uygulamada Bearer jetonu
// destegi geldiginde acilacak (Faz 3c). Calismayan bir dugme
// koymak, tamamlanmis izlenimi vermek olurdu.

import React from "react";
import { FlatList, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Durum, Etiket } from "../../src/bilesen";
import { useTema } from "../../src/tema";
import { useVeri } from "../../src/veri";

export default function Senaryolar() {
  const t = useTema();
  const alt = useSafeAreaInsets().bottom;
  const s = useVeri(api.senaryolar);

  return (
    <FlatList
      style={{ backgroundColor: t.renk.zemin }}
      data={s.veri?.senaryolar ?? []}
      keyExtractor={(x) => String(x.id)}
      contentContainerStyle={{ paddingBottom: alt + 28 }}
      ListHeaderComponent={
        <View
          style={[
            d.uyari,
            {
              backgroundColor: t.renk.panel2,
              borderColor: t.renk.cizgi,
              borderRadius: t.r.kucuk,
            },
          ]}
        >
          <Text style={[d.uyariBaslik, { color: t.renk.yazi }]}>
            Senaryolar tahmin değildir
          </Text>
          <Text style={[d.uyariYazi, { color: t.renk.yazi2 }]}>
            Koşullu senaryolar, "şu olursa şu beklenir" biçiminde
            kurulmuş değerlendirmelerdir. Kesin öngörü ya da getiri
            vaadi değildir. Buradaki senaryoları üyeler yazar; Netaris'in
            editoryal içeriğinden ayrıdır.
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <View
          style={[
            d.kart,
            {
              backgroundColor: t.renk.panel,
              borderColor: t.renk.cizgi,
              borderRadius: t.r.orta,
            },
          ]}
        >
          <View style={d.satir}>
            <Etiket metin={`${item.oy} oy`} renk={t.renk.vurgu} />
            {item.ufuk ? <Etiket metin={item.ufuk} /> : null}
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              {item.yayin ? item.yayin.slice(0, 10) : ""}
            </Text>
          </View>

          <Text style={[d.alan, { color: t.renk.yazi3 }]}>KOŞUL</Text>
          <Text style={[d.govde, { color: t.renk.yazi }]}>{item.kosul}</Text>

          <Text style={[d.alan, { color: t.renk.yazi3 }]}>BEKLENEN SONUÇ</Text>
          <Text style={[d.govde, { color: t.renk.yazi }]}>{item.sonuc}</Text>

          {/* CAPA: senaryo hangi gelismeye bagli. Baglantisiz bir
              senaryo neye dayandigini soylemez. */}
          {item.capa_baslik ? (
            <Pressable
              onPress={() =>
                item.capa
                  ? Linking.openURL(api.webAdresi(item.capa))
                  : undefined
              }
              accessibilityRole="link"
              style={[d.capa, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
                Dayandığı gelişme
              </Text>
              <Text style={{ color: t.renk.vurgu, fontSize: 13 }}>
                {item.capa_baslik}
              </Text>
            </Pressable>
          ) : null}

          {/* YAZAR GORUNUR -- uye icerigi, editoryal icerik degil. */}
          <Text style={[d.ufak, { color: t.renk.notr }]}>
            Yazan: {item.yazar} (Netaris üyesi)
          </Text>
        </View>
      )}
      ListEmptyComponent={
        <Durum
          yukleniyor={s.yukleniyor}
          hata={s.hata}
          bos={!s.yukleniyor && !s.hata}
          bosMetin="Yayımlanmış senaryo yok."
          yenile={s.yenile}
        />
      }
      ListFooterComponent={
        s.veri && s.veri.senaryolar.length > 0 ? (
          <Text style={[d.not, { color: t.renk.notr }]}>
            Senaryo yazmak için bir haber ya da varlık sayfasını açıp
            "senaryo yaz" deyin: her senaryo dayandığı gelişmeye
            bağlıdır. Oy vermek için oturum gerekiyor.
          </Text>
        ) : undefined
      }
    />
  );
}

const d = StyleSheet.create({
  uyari: {
    margin: 16,
    marginBottom: 6,
    padding: 13,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 4,
  },
  uyariBaslik: { fontSize: 14, fontWeight: "700" },
  uyariYazi: { fontSize: 12, lineHeight: 17 },
  kart: {
    marginHorizontal: 16,
    marginTop: 10,
    padding: 14,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 6,
  },
  satir: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  alan: { fontSize: 10, fontWeight: "700", letterSpacing: 0.6, marginTop: 4 },
  govde: { fontSize: 15, lineHeight: 21 },
  capa: {
    marginTop: 8,
    padding: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 10,
    gap: 2,
  },
  ufak: { fontSize: 11 },
  not: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginTop: 18,
  },
});
