// HABER DETAYI
//
// ATIF BU EKRANIN OMURGASI:
//   * Kaynak kurum adi gorunur.
//   * Kaynaga giden baglanti calisir.
//   * Kaynagin KENDI ozeti alinti olarak, isaretli basilir.
//   * Fotograf atfiyla birlikte basilir.
//
// Ticari kaynaklardan kisa iktibas FSEK m.35 kapsaminda mesru; sarti
// kaynak gostermek ve kisa tutmak. Besleme atifsiz ticari kaydi
// zaten dusuruyor, bu ekran da atfi gizlemiyor.
//
// `neden_onemli` NETARIS'IN kendi degerlendirmesi, `kaynak_ozeti`
// kaynagin metni. Ikisi AYRI basliklar altinda: okur hangisinin kimin
// sozu oldugunu bilmeli.

import { useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import {
  Linking,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Durum, Etiket, Gorsel, KaynakBagi, tarihTR } from "../../src/bilesen";
import { useTema } from "../../src/tema";
import { useVeri } from "../../src/veri";

export default function HaberDetayi() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const h = useVeri(() => api.haber(String(slug)), [slug]);

  const paylas = async () => {
    if (!h.veri) return;
    // PAYLASIM BAGLANTISI SITEDEKI SAYFAYA GIDIYOR: uygulama ici bir
    // adres paylasilamaz ve paylasan kisi karsi tarafin uygulamayi
    // kurmus olmasini bekleyemez.
    await Share.share({
      message: `${h.veri.baslik}\n${api.webAdresi(h.veri.yol)}`,
      url: api.webAdresi(h.veri.yol),
      title: h.veri.baslik,
    });
  };

  return (
    <ScrollView
      style={{ backgroundColor: t.renk.zemin }}
      contentContainerStyle={{ padding: 16, paddingBottom: alt + 32, gap: 12 }}
    >
      <Durum
        yukleniyor={h.yukleniyor}
        hata={h.hata}
        yenile={h.yenile}
      />

      {h.veri ? (
        <>
          <View style={d.satir}>
            {h.veri.konu ? (
              <Etiket metin={h.veri.konu} renk={t.renk.vurgu} />
            ) : null}
            {h.veri.cevrildi ? <Etiket metin="ÇEVİRİ" /> : null}
            {h.veri.tarih ? (
              <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
                {tarihTR(h.veri.tarih)}
              </Text>
            ) : null}
          </View>

          <Text style={[d.baslik, { color: t.renk.yazi }]}>
            {h.veri.baslik}
          </Text>

          <Gorsel
            yol={h.veri.foto}
            atif={h.veri.foto_atif}
            yuksek={200}
          />

          {/* NETARIS'IN DEGERLENDIRMESI */}
          {h.veri.neden_onemli ? (
            <View
              style={[
                d.kutu,
                {
                  backgroundColor: t.renk.panel,
                  borderColor: t.renk.cizgi,
                  borderRadius: t.r.orta,
                },
              ]}
            >
              <Text style={[d.kutuBaslik, { color: t.renk.vurgu }]}>
                NEDEN ÖNEMLİ
              </Text>
              <Text style={[d.govde, { color: t.renk.yazi }]}>
                {h.veri.neden_onemli}
              </Text>
            </View>
          ) : null}

          {/* KAYNAGIN KENDI METNI -- ALINTI OLARAK ISARETLI */}
          {h.veri.kaynak_ozeti ? (
            <View
              style={[
                d.alinti,
                {
                  borderLeftColor: t.renk.cizgiParlak,
                  backgroundColor: t.renk.panel2,
                  borderRadius: t.r.mini,
                },
              ]}
            >
              <Text style={[d.kutuBaslik, { color: t.renk.yazi3 }]}>
                KAYNAĞIN ÖZETİ
              </Text>
              <Text style={[d.govde, { color: t.renk.yazi2 }]}>
                {h.veri.kaynak_ozeti}
              </Text>
              {/* Kaynagin KENDI basligi da gosteriliyor: ne dedigi
                  gizlenmiyor. Netaris basligi sadelestirebiliyor. */}
              {h.veri.baslik_kaynak &&
              h.veri.baslik_kaynak !== h.veri.baslik ? (
                <Text style={[d.ufak, { color: t.renk.notr }]}>
                  Kaynağın başlığı: {h.veri.baslik_kaynak}
                </Text>
              ) : null}
            </View>
          ) : null}

          {/* ETKI KANALLARI */}
          {h.veri.kanallar && h.veri.kanallar.length > 0 ? (
            <View
              style={[
                d.kutu,
                {
                  backgroundColor: t.renk.panel,
                  borderColor: t.renk.cizgi,
                  borderRadius: t.r.orta,
                },
              ]}
            >
              <Text style={[d.kutuBaslik, { color: t.renk.yazi3 }]}>
                {(h.veri.kanal_basligi || "ETKİ KANALLARI").toUpperCase()}
              </Text>
              {h.veri.kanallar.map((k, i) => (
                <Text
                  key={i}
                  style={[d.govde, { color: t.renk.yazi2 }]}
                >
                  • {k}
                </Text>
              ))}
            </View>
          ) : null}

          <Text style={[d.kaynakSatiri, { color: t.renk.notr }]}>
            Kaynak: {h.veri.kurum_tam || h.veri.kurum}
            {h.veri.ticari ? " · ticari kaynak" : ""}
          </Text>

          <KaynakBagi
            adres={h.veri.kaynak_adres}
            kurum={h.veri.kurum}
          />

          <View style={d.satir}>
            <Pressable
              onPress={paylas}
              accessibilityRole="button"
              style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={{ color: t.renk.yazi }}>Paylaş</Text>
            </Pressable>
            <Pressable
              onPress={() =>
                Linking.openURL(api.webAdresi(h.veri!.yol))
              }
              accessibilityRole="link"
              style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={{ color: t.renk.yazi }}>Sitede aç</Text>
            </Pressable>
          </View>

          {/* SENARYO YAZ -- CAPA BURADAN GELIYOR.
              Senaryo neye dayandigini soylemeli; bos bir "senaryo
              yaz" dugmesi neye bagli oldugu belirsiz metinler
              uretirdi. Bu yuzden ekran haberden aciliyor. */}
          <Pressable
            onPress={() =>
              router.push({
                pathname: "/senaryo-yaz",
                params: {
                  capa: h.veri!.yol,
                  capa_baslik: h.veri!.baslik,
                  capa_tur: "haber",
                },
              })
            }
            accessibilityRole="button"
            style={[d.dugme, { borderColor: t.renk.vurgu }]}
          >
            <Text style={{ color: t.renk.vurgu, fontWeight: "600" }}>
              Bu gelişme için senaryo yaz
            </Text>
          </Pressable>

          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            style={{ paddingVertical: 14, minHeight: 44 }}
          >
            <Text style={{ color: t.renk.vurgu }}>‹ Geri</Text>
          </Pressable>
        </>
      ) : null}
    </ScrollView>
  );
}

const d = StyleSheet.create({
  satir: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap" },
  baslik: { fontSize: 24, fontWeight: "700", lineHeight: 31, letterSpacing: -0.4 },
  kutu: { padding: 14, borderWidth: StyleSheet.hairlineWidth, gap: 7 },
  kutuBaslik: { fontSize: 10, fontWeight: "700", letterSpacing: 0.7 },
  alinti: { padding: 14, borderLeftWidth: 3, gap: 7 },
  govde: { fontSize: 15, lineHeight: 23 },
  ufak: { fontSize: 12, lineHeight: 17 },
  kaynakSatiri: { fontSize: 12, marginTop: 4 },
  dugme: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderRadius: 10,
    minHeight: 44,
    justifyContent: "center",
  },
});
