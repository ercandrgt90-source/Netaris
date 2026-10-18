// PIYASALAR
//
// Tek ortak modelde yonetiliyor: her kalem kod, ad, deger, fark,
// yon VE KENDI VERI TARIHINI tasiyor. Kaynaklar farkli (TCMB, ECB,
// FRED, EIA) ama model ayni.
//
// CANLI VERI IDDIA EDILMIYOR. Besleme `canli_degil: true`
// bildiriyor ve bu ekranda acikca yaziyor. Gecikmeli veriyi gercek
// zamanliymis gibi sunmak bir finans uygulamasinda en pahali hata.
//
// LISANS: hisse endeksleri (BIST 100, S&P 500, Nasdaq, DAX) burada
// YOK ve sebebi yazili. Besleme onlari zaten eliyor
// (`mobil_besleme.piyasa`), bu ekran da eksikligi gizlemiyor.

import { useRouter } from "expo-router";
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Baslik, Durum, tarihTR } from "../../src/bilesen";
import { useTema, yonRengi } from "../../src/tema";
import { useVeri } from "../../src/veri";

/** Kod oneki -> grup. Besleme grup bilgisi tasimiyor; eslesmeyen
 *  kalem "Diğer" grubuna dusuyor ve KAYBOLMUYOR. */
const GRUPLAR: { ad: string; esles: (kod: string, adi: string) => boolean }[] = [
  {
    ad: "Döviz",
    esles: (k, a) =>
      k.startsWith("TP.DK") || k.includes("EURUSD") || /TRY|USD|EUR/.test(a),
  },
  {
    ad: "Emtia",
    esles: (k) => k.startsWith("DCOIL") || k.includes("GOLD"),
  },
  {
    ad: "Faiz ve tahvil",
    esles: (k) => ["DFF", "DGS2", "DGS10", "DGS30", "T10Y2Y"].includes(k),
  },
  {
    ad: "Risk ve endeks",
    esles: (k) => k === "DTWEXBGS" || k.startsWith("BAML"),
  },
];

function grupla(kalemler: api.PiyasaKalemi[]) {
  const kalan = new Set(kalemler.map((k) => k.kod));
  const cikti: { ad: string; kalemler: api.PiyasaKalemi[] }[] = [];
  for (const g of GRUPLAR) {
    const secili = kalemler.filter(
      (k) => kalan.has(k.kod) && g.esles(k.kod, k.ad),
    );
    secili.forEach((k) => kalan.delete(k.kod));
    if (secili.length) cikti.push({ ad: g.ad, kalemler: secili });
  }
  // ESLESMEYEN KALEM GIZLENMIYOR: bir kaynak eklendiginde sessizce
  // kaybolmasi, "veri var ama gorunmuyor" demek olurdu.
  const artan = kalemler.filter((k) => kalan.has(k.kod));
  if (artan.length) cikti.push({ ad: "Diğer", kalemler: artan });
  return cikti;
}

export default function Piyasalar() {
  const t = useTema();
  const alt = useSafeAreaInsets().bottom;
  const router = useRouter();
  const p = useVeri(api.piyasa);

  return (
    <ScrollView
      style={{ backgroundColor: t.renk.zemin }}
      contentContainerStyle={{ paddingBottom: alt + 28 }}
    >
      <Durum
        yukleniyor={p.yukleniyor}
        hata={p.hata}
        bos={!!p.veri && p.veri.kalemler.length === 0}
        bosMetin="Gösterge verisi bulunamadı."
        yenile={p.yenile}
      />

      {p.veri ? (
        <>
          {/* CANLI OLMADIGI EN USTTE, GIZLENMEDEN. */}
          <View
            style={[
              s.uyari,
              {
                backgroundColor: t.renk.panel2,
                borderColor: t.renk.cizgi,
                borderRadius: t.r.kucuk,
              },
            ]}
          >
            <Text style={[s.uyariBaslik, { color: t.renk.yazi }]}>
              Gecikmeli veri
            </Text>
            <Text style={[s.uyariYazi, { color: t.renk.yazi2 }]}>
              {p.veri.aciklama}
              {p.veri.veri_tarihi
                ? ` Şeritteki en yeni veri ${tarihTR(p.veri.veri_tarihi)}.`
                : ""}
            </Text>
          </View>

          {grupla(p.veri.kalemler).map((g) => (
            <View key={g.ad}>
              <Baslik metin={g.ad} />
              <View
                style={[
                  s.tablo,
                  {
                    backgroundColor: t.renk.panel,
                    borderColor: t.renk.cizgi,
                    borderRadius: t.r.orta,
                  },
                ]}
              >
                {g.kalemler.map((k, i) => (
                  <View
                    key={k.kod}
                    style={[
                      s.satir,
                      i > 0
                        ? {
                            borderTopWidth: StyleSheet.hairlineWidth,
                            borderTopColor: t.renk.cizgi,
                          }
                        : null,
                    ]}
                  >
                    <View style={{ flex: 1, gap: 2 }}>
                      <Text style={[s.ad, { color: t.renk.yazi }]}>
                        {k.ad}
                      </Text>
                      <Text style={[s.tarih, { color: t.renk.notr }]}>
                        {tarihTR(k.tarih) || "tarih bilinmiyor"}
                        {k.ritim ? ` · ${k.ritim}` : ""}
                        {k.bayat && k.gun ? ` · ${k.gun} gün önce` : ""}
                      </Text>
                    </View>
                    <View style={{ alignItems: "flex-end", gap: 2 }}>
                      <Text style={[s.deger, { color: t.renk.yazi }]}>
                        {k.deger}
                      </Text>
                      <Text
                        style={[s.fark, { color: yonRengi(t, k.yon) }]}
                      >
                        {k.fark}
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ))}

          {/* TAKVIME KAPI: piyasa hareketi cogu zaman bir veri
              aciklamasina bagli; ikisi ayri ekranlarda ama bir
              dokunus uzakta. */}
          <Pressable
            onPress={() => router.push("/takvim")}
            accessibilityRole="button"
            style={[s.takvim, { borderColor: t.renk.cizgiParlak }]}
          >
            <Text style={{ color: t.renk.vurgu, fontWeight: "600" }}>
              Ekonomik takvim · yaklaşan veri açıklamaları
            </Text>
          </Pressable>

          <Text style={[s.lisans, { color: t.renk.notr }]}>
            Hisse senedi endeksleri yayımlanmıyor. BIST 100 (Borsa
            İstanbul), S&amp;P 500 ve Dow Jones (S&amp;P Dow Jones
            Indices), Nasdaq Composite (Nasdaq, Inc.) ve DAX (Deutsche
            Börse) verilerinin dağıtım lisansı Netaris'te değil. Bu
            seriler bilinçli olarak yayından çekildi; uydurma değer
            gösterilmiyor.
          </Text>
        </>
      ) : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  uyari: {
    margin: 16,
    marginBottom: 2,
    padding: 13,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 4,
  },
  uyariBaslik: { fontSize: 14, fontWeight: "700" },
  uyariYazi: { fontSize: 12, lineHeight: 17 },
  tablo: {
    marginHorizontal: 16,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  satir: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 13,
    paddingHorizontal: 14,
    minHeight: 56,
  },
  ad: { fontSize: 15, fontWeight: "600" },
  tarih: { fontSize: 11 },
  // `tabular-nums` karsiligi: sayilar hizali olsun.
  deger: { fontSize: 16, fontWeight: "700", fontVariant: ["tabular-nums"] },
  fark: { fontSize: 12, fontVariant: ["tabular-nums"] },
  takvim: {
    marginHorizontal: 16,
    marginTop: 18,
    paddingVertical: 14,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 48,
    justifyContent: "center",
  },
  lisans: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginTop: 18,
  },
});
