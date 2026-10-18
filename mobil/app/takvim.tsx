// EKONOMIK TAKVIM
//
// Sartname 10. bolum. ALTI SEKME OLMUYOR (en fazla bes) -- takvim
// Ana Sayfa ve Piyasalar ekranlarindan aciliyor.
//
// UC KURAL BU EKRANDA GORUNUR:
//
// 1. SAAT DILIMI YAZILI. Bir veri aciklamasinin saati, hangi
//    dilimde oldugu yazilmadan anlamsiz. Basta bir kez, sonra her
//    kalemde gun/saat.
//
// 2. SAATI KESIN OLMAYAN KALEM ISARETLI. Bazi yayinlarin saati
//    kurum tarafindan onaylanmamis; tahmini saati kesinmis gibi
//    gostermek okuru bos yere ekran basinda bekletir.
//
// 3. "BEKLENTI" ILE "ONCEKI DEGER" AYRI GOSTERILIYOR. Esik bazen
//    gercek bir piyasa konsensusu, bazen yalnizca onceki rakam.
//    Ikisini ayni etiketle basmak, olmayan bir konsensus uydurmak
//    olurdu -- ve "beklentinin ustunde geldi" cumlesi de o zaman
//    yalan olur.
//
// KOSULLU DALLAR: "su olursa su beklenir". Fiyat YONU iddia
// edilmiyor; mekanizma neyin neden degistigini anlatiyor, olcum ise
// gecmis gozlemleri -- ikisi AYRI basiliyor.

import { Stack } from "expo-router";
import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../src/api";
import { Durum, Etiket, tarihTR } from "../src/bilesen";
import { useTema } from "../src/tema";
import { useVeri } from "../src/veri";

/** Önem -> okunabilir etiket. Çıplak sayı okura bir şey söylemiyor. */
function onemEtiketi(n: number): string {
  if (n >= 3) return "YÜKSEK ETKİ";
  if (n === 2) return "ORTA ETKİ";
  return "DÜŞÜK ETKİ";
}

export default function TakvimEkrani() {
  const t = useTema();
  const alt = useSafeAreaInsets().bottom;
  const v = useVeri(api.takvim);

  return (
    <>
      <Stack.Screen options={{ title: "Ekonomik takvim" }} />
      <ScrollView
        style={{ backgroundColor: t.renk.zemin }}
        contentContainerStyle={{ paddingBottom: alt + 28 }}
      >
        <Durum
          yukleniyor={v.yukleniyor}
          hata={v.hata}
          bos={!!v.veri && v.veri.ogeler.length === 0}
          bosMetin="Yaklaşan veri açıklaması bulunamadı."
          yenile={v.yenile}
        />

        {v.veri && v.veri.ogeler.length > 0 ? (
          <>
            {/* SAAT DILIMI EN USTTE, BIR KEZ. */}
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
                Saatler Türkiye saatiyle (UTC+3)
              </Text>
              <Text style={[d.uyariYazi, { color: t.renk.yazi2 }]}>
                {v.veri.aciklama}
              </Text>
            </View>

            {v.veri.ogeler.map((o, i) => {
              // GERCEK KONSENSUS MU, ONCEKI DEGER MI -- etiket buna
              // gore degisiyor.
              const konsensus = o.esik_kaynak === "beklenti";
              return (
                <View
                  key={`${o.seri}-${o.an}-${i}`}
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
                    {o.ulke ? <Etiket metin={o.ulke} /> : null}
                    <Etiket
                      metin={onemEtiketi(o.onem)}
                      renk={o.onem >= 3 ? t.renk.uyari : t.renk.yazi3}
                    />
                    {o.aciklandi ? (
                      <Etiket metin="AÇIKLANDI" renk={t.renk.vurgu} />
                    ) : null}
                  </View>

                  <Text style={[d.ad, { color: t.renk.yazi }]}>{o.ad}</Text>

                  <View style={d.satir}>
                    <Text style={[d.zaman, { color: t.renk.vurgu }]}>
                      {o.gun} · {o.saat}
                    </Text>
                    {/* SAATI KESIN OLMAYAN KALEM ISARETLI. */}
                    {!o.kesin ? (
                      <Text style={[d.ufak, { color: t.renk.uyari }]}>
                        saat kesinleşmedi
                      </Text>
                    ) : null}
                  </View>

                  {/* DEGERLER */}
                  <View
                    style={[d.degerler, { borderTopColor: t.renk.cizgi }]}
                  >
                    {o.onceki_deger ? (
                      <View style={d.deger}>
                        <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                          ÖNCEKİ
                        </Text>
                        <Text style={[d.degerYazi, { color: t.renk.yazi }]}>
                          {o.onceki_deger}
                        </Text>
                        {o.onceki_tarih ? (
                          <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                            {tarihTR(o.onceki_tarih)}
                          </Text>
                        ) : null}
                      </View>
                    ) : null}

                    {o.esik_deger ? (
                      <View style={d.deger}>
                        {/* ETIKET ESIGIN NE OLDUGUNU SOYLUYOR. */}
                        <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                          {konsensus ? "BEKLENTİ" : "EŞİK (önceki değer)"}
                        </Text>
                        <Text style={[d.degerYazi, { color: t.renk.yazi }]}>
                          {o.esik_deger}
                        </Text>
                        {konsensus && o.kaynak ? (
                          <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                            {o.kaynak}
                          </Text>
                        ) : null}
                      </View>
                    ) : null}

                    {o.gerceklesen ? (
                      <View style={d.deger}>
                        <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                          AÇIKLANAN
                        </Text>
                        <Text
                          style={[d.degerYazi, { color: t.renk.vurgu }]}
                        >
                          {o.gerceklesen.deger ?? "—"}
                          {o.gerceklesen.birim ? ` ${o.gerceklesen.birim}` : ""}
                        </Text>
                        {o.gerceklesen.donem ? (
                          <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                            {o.gerceklesen.donem}
                          </Text>
                        ) : null}
                      </View>
                    ) : null}
                  </View>

                  {/* SURPRIZ: besleme bunu YALNIZCA gercek konsensus
                      varken uretiyor, yani burada ayrica kosul
                      aramaya gerek yok -- alan varsa anlamlidir. */}
                  {o.surpriz ? (
                    <Text
                      style={[
                        d.surpriz,
                        {
                          color:
                            o.surpriz.yon === "ustunde"
                              ? t.renk.artis
                              : t.renk.azalis,
                        },
                      ]}
                    >
                      Beklentinin {o.surpriz.yon === "ustunde" ? "üzerinde" : "altında"}
                      {o.surpriz.metin ? ` (${o.surpriz.metin} fark)` : ""}
                    </Text>
                  ) : null}

                  {/* KOSULLU DALLAR */}
                  {o.dallar.length > 0 ? (
                    <View style={{ gap: 10, marginTop: 4 }}>
                      {o.dallar.map((dal, j) => (
                        <View
                          key={j}
                          style={[
                            d.dal,
                            {
                              backgroundColor: t.renk.panel2,
                              borderLeftColor:
                                dal.yon === "ustunde"
                                  ? t.renk.artis
                                  : t.renk.azalis,
                              borderRadius: t.r.mini,
                            },
                          ]}
                        >
                          <Text style={[d.dalBaslik, { color: t.renk.yazi }]}>
                            {dal.baslik}
                          </Text>
                          <Text style={[d.dalYazi, { color: t.renk.yazi2 }]}>
                            {dal.mekanizma}
                          </Text>
                          {/* OLCUM AYRI BASILIYOR: mekanizma akil
                              yurutme, olcum gozlem. Birlestirilirse
                              gozlem bir TAHMIN gibi okunur. */}
                          {dal.olcum ? (
                            <Text
                              style={[d.dalOlcum, { color: t.renk.notr }]}
                            >
                              {dal.olcum}
                            </Text>
                          ) : null}
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              );
            })}

            <Text style={[d.not, { color: t.renk.notr }]}>
              Koşullu değerlendirmeler fiyat yönü iddia etmez:
              "mekanizma" neyin neden değişebileceğini, "geçmişte…"
              satırı ise ölçülmüş gözlemleri anlatır.
            </Text>
          </>
        ) : null}
      </ScrollView>
    </>
  );
}

const d = StyleSheet.create({
  uyari: {
    margin: 16,
    marginBottom: 4,
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
    gap: 8,
  },
  satir: { flexDirection: "row", alignItems: "center", gap: 7, flexWrap: "wrap" },
  ad: { fontSize: 16, fontWeight: "700", lineHeight: 22 },
  zaman: { fontSize: 14, fontWeight: "700", fontVariant: ["tabular-nums"] },
  degerler: {
    flexDirection: "row",
    gap: 18,
    flexWrap: "wrap",
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 10,
  },
  deger: { gap: 2, minWidth: 92 },
  degerYazi: { fontSize: 16, fontWeight: "700", fontVariant: ["tabular-nums"] },
  surpriz: { fontSize: 13, fontWeight: "600" },
  dal: { padding: 11, borderLeftWidth: 3, gap: 4 },
  dalBaslik: { fontSize: 14, fontWeight: "700" },
  dalYazi: { fontSize: 13, lineHeight: 19 },
  dalOlcum: { fontSize: 11, lineHeight: 16, fontStyle: "italic" },
  ufak: { fontSize: 12 },
  cokUfak: { fontSize: 10, fontWeight: "700", letterSpacing: 0.5 },
  not: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginTop: 20,
  },
});
