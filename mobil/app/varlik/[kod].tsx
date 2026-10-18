// VARLIK DETAYI
//
// Sitenin haber toplamaktan ayrildigi katman burada: tanim, GUNCEL
// DEGER (lisansi varsa), YAPISAL ILISKILER ve haber arsivi.
//
// IKI KURAL EKRANDA GORUNUR:
//
// 1. DEGER YOKSA SEBEBI BELLI. "veri_var" false olabilir cunku ya
//    seri lisansli (BIST, S&P 500, Nasdaq, VIX) ya da varligin
//    serisi hic yok (ulke, kurum). Ekran "veri yok" diye bos
//    birakmiyor; seri kodu varsa lisans notunu basiyor.
//
// 2. BAGIN DAYANAGI YAZILI. "yapisal" tanim geregi dogru; "veri"
//    gozlemden cikarilmis ve degisebilir. Ikisini ayni gostermek,
//    bir gozlemi muhasebe kimligi gibi sunmak olurdu. Sitede de
//    ayni ayrim basiliyor.
//
// ILISKILER ETKININ YONUNU SOYLEMEZ; yon veriden okunur -- site
// metninin aynisi, cunku kural ayni.

import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Durum, Etiket, tarihTR } from "../../src/bilesen";
import { useTema, yonRengi } from "../../src/tema";
import { useVeri } from "../../src/veri";

const DAYANAK_ADI: Record<string, string> = {
  yapisal: "yapısal",
  veri: "veri",
  kaynak: "kaynak",
};

const DAYANAK_ACIKLAMA: Record<string, string> = {
  yapisal: "Muhasebe kimliği ya da tanım gereği doğru.",
  veri: "Gözlemden çıkarılmış; değişebilir.",
  kaynak: "Kurumun kendi açıklamasına dayanıyor.",
};

/** Basit kıvılcım: seriyi dar bir alanda çubuklarla gösterir.
 *
 *  Grafik kütüphanesi EKLENMEDİ: tek bir eğri için ek paket ve ek
 *  boyut demekti. Çubuklar seriyi dürüstçe gösteriyor — eksik
 *  gözlem SIFIR gibi basılmıyor, atlanıyor. */
function Kivilcim({ seri }: { seri: { tarih: string; deger: number | null }[] }) {
  const t = useTema();
  const degerler = seri
    .map((x) => x.deger)
    .filter((x): x is number => typeof x === "number" && Number.isFinite(x));
  if (degerler.length < 3) return null;
  const enAz = Math.min(...degerler);
  const enCok = Math.max(...degerler);
  const aralik = enCok - enAz || 1;
  return (
    <View style={d.kivilcim} accessibilityLabel="Son dönem seyri">
      {degerler.map((v, i) => (
        <View
          key={i}
          style={{
            flex: 1,
            // En az 2 piksel: sifira yakin degerler tamamen
            // gorunmez olmasin.
            height: Math.max(2, ((v - enAz) / aralik) * 42),
            backgroundColor:
              i === degerler.length - 1 ? t.renk.vurgu : t.renk.cizgiParlak,
            borderRadius: 1,
          }}
        />
      ))}
    </View>
  );
}

export default function VarlikDetayi() {
  const { kod } = useLocalSearchParams<{ kod: string }>();
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const v = useVeri(() => api.varlik(String(kod)), [kod]);

  return (
    <>
      <Stack.Screen options={{ title: v.veri?.ad || "Varlık" }} />
      <ScrollView
        style={{ backgroundColor: t.renk.zemin }}
        contentContainerStyle={{ padding: 16, paddingBottom: alt + 32, gap: 14 }}
      >
        <Durum yukleniyor={v.yukleniyor} hata={v.hata} yenile={v.yenile} />

        {v.veri ? (
          <>
            <View>
              <Text style={[d.baslik, { color: t.renk.yazi }]}>
                {v.veri.ad}
              </Text>
              {v.veri.ad_en && v.veri.ad_en !== v.veri.ad ? (
                <Text style={[d.ufak, { color: t.renk.notr }]}>
                  {v.veri.ad_en}
                </Text>
              ) : null}
            </View>

            <View style={d.satir}>
              {v.veri.tur ? <Etiket metin={v.veri.tur} /> : null}
              <Text style={[d.ufak, { color: t.renk.notr }]}>
                Arşivde {v.veri.haber_sayisi} haber
              </Text>
            </View>

            {v.veri.aciklama ? (
              <Text style={[d.govde, { color: t.renk.yazi2 }]}>
                {v.veri.aciklama}
              </Text>
            ) : null}

            {/* GUNCEL DEGER -- varsa. */}
            {v.veri.veri_var && v.veri.veri ? (
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
                <View style={d.degerSatiri}>
                  <Text style={[d.deger, { color: t.renk.yazi }]}>
                    {v.veri.veri.deger}
                    {v.veri.veri.birim ? ` ${v.veri.veri.birim}` : ""}
                  </Text>
                  {v.veri.veri.degisim ? (
                    <Text
                      style={[
                        d.degisim,
                        { color: yonRengi(t, v.veri.veri.yon) },
                      ]}
                    >
                      {v.veri.veri.degisim}
                    </Text>
                  ) : null}
                </View>

                <Kivilcim seri={v.veri.veri.seri} />

                {/* VERI TARIHI DEGERIN YANINDAN AYRILMIYOR: sayi
                    tek basina "canli fiyat" izlenimi veriyor. */}
                <Text style={[d.ufak, { color: t.renk.notr }]}>
                  Son veri {tarihTR(v.veri.veri.tarih)} ·{" "}
                  {v.veri.veri.gozlem_sayisi} gözlemlik seri · gecikmeli
                </Text>
              </View>
            ) : v.veri.seri_kodu ? (
              // SERI VAR AMA DEGER YOK -> LISANS. Sebebini yazmak,
              // "neden boş" sorusunu ortadan kaldiriyor.
              <View
                style={[
                  d.kutu,
                  {
                    backgroundColor: t.renk.panel2,
                    borderColor: t.renk.cizgi,
                    borderRadius: t.r.kucuk,
                  },
                ]}
              >
                <Text style={[d.kutuBaslik, { color: t.renk.uyari }]}>
                  DEĞER YAYIMLANMIYOR
                </Text>
                <Text style={[d.ufak, { color: t.renk.yazi2 }]}>
                  Bu serinin veri dağıtım lisansı Netaris'te değil.
                  Sayfa kalıyor çünkü tanım ve yapısal ilişkiler
                  bizim; yayımlanmayan şey yalnızca serinin değeri.
                </Text>
              </View>
            ) : null}

            {/* YAPISAL ILISKILER */}
            {v.veri.baglar.length > 0 ? (
              <View style={{ gap: 8 }}>
                <Text style={[d.bolum, { color: t.renk.yazi }]}>
                  Yapısal ilişkiler
                </Text>
                {v.veri.baglar.map((b, i) => {
                  const bu = b.kaynak === v.veri!.kod;
                  const oteki = bu ? b.hedef_ad : b.kaynak_ad;
                  const otekiKod = bu ? b.hedef : b.kaynak;
                  return (
                    <Pressable
                      key={`${b.kaynak}-${b.hedef}-${i}`}
                      onPress={() => router.push(`/varlik/${otekiKod}`)}
                      accessibilityRole="button"
                      style={[
                        d.bag,
                        {
                          backgroundColor: t.renk.panel,
                          borderColor: t.renk.cizgi,
                          borderRadius: t.r.kucuk,
                        },
                      ]}
                    >
                      <Text style={[d.bagBaslik, { color: t.renk.yazi }]}>
                        {bu ? v.veri!.ad : oteki}
                        <Text style={{ color: t.renk.vurgu }}>
                          {" "}
                          → {b.tur}{" "}
                        </Text>
                        {bu ? oteki : v.veri!.ad}
                      </Text>
                      {b.aciklama ? (
                        <Text style={[d.ufak, { color: t.renk.yazi2 }]}>
                          {b.aciklama}
                        </Text>
                      ) : null}
                      {/* DAYANAK: "yapisal" ile "veri" ayni sey degil. */}
                      {b.dayanak ? (
                        <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                          {DAYANAK_ADI[b.dayanak] || b.dayanak}
                          {DAYANAK_ACIKLAMA[b.dayanak]
                            ? ` · ${DAYANAK_ACIKLAMA[b.dayanak]}`
                            : ""}
                        </Text>
                      ) : null}
                    </Pressable>
                  );
                })}
                <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                  İlişkiler etkinin yönünü söylemez; yön veriden okunur.
                </Text>
              </View>
            ) : null}

            {/* HABER ARSIVI */}
            {v.veri.haberler.length > 0 ? (
              <View style={{ gap: 8 }}>
                <Text style={[d.bolum, { color: t.renk.yazi }]}>
                  Gelişmeler
                </Text>
                {v.veri.haberler.map((h, i) => (
                  <Pressable
                    key={`${h.yol}-${i}`}
                    onPress={() =>
                      router.push(
                        `/haber/${h.yol.replace(/\/$/, "").split("/").pop()}`,
                      )
                    }
                    accessibilityRole="button"
                    style={[
                      d.haber,
                      {
                        backgroundColor: t.renk.panel,
                        borderColor: t.renk.cizgi,
                        borderRadius: t.r.kucuk,
                      },
                    ]}
                  >
                    <Text style={[d.haberBaslik, { color: t.renk.yazi }]}>
                      {h.baslik}
                    </Text>
                    <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                      {tarihTR(h.tarih)}
                      {h.kurum ? ` · ${h.kurum}` : ""}
                    </Text>
                  </Pressable>
                ))}
              </View>
            ) : null}

            <Pressable
              onPress={() => Linking.openURL(api.webAdresi(v.veri!.yol))}
              accessibilityRole="link"
              style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={{ color: t.renk.yazi }}>Sitede aç</Text>
            </Pressable>
          </>
        ) : null}
      </ScrollView>
    </>
  );
}

const d = StyleSheet.create({
  baslik: { fontSize: 23, fontWeight: "700", lineHeight: 29, letterSpacing: -0.4 },
  satir: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap" },
  govde: { fontSize: 15, lineHeight: 22 },
  kutu: { padding: 14, borderWidth: StyleSheet.hairlineWidth, gap: 9 },
  kutuBaslik: { fontSize: 10, fontWeight: "700", letterSpacing: 0.7 },
  degerSatiri: { flexDirection: "row", alignItems: "baseline", gap: 10 },
  deger: { fontSize: 26, fontWeight: "700", fontVariant: ["tabular-nums"] },
  degisim: { fontSize: 14, fontWeight: "600" },
  kivilcim: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 2,
    height: 44,
  },
  bolum: { fontSize: 17, fontWeight: "700", marginTop: 4 },
  bag: { padding: 12, borderWidth: StyleSheet.hairlineWidth, gap: 4 },
  bagBaslik: { fontSize: 14, fontWeight: "600", lineHeight: 20 },
  haber: { padding: 12, borderWidth: StyleSheet.hairlineWidth, gap: 3 },
  haberBaslik: { fontSize: 14, lineHeight: 19 },
  ufak: { fontSize: 12, lineHeight: 17 },
  cokUfak: { fontSize: 11, lineHeight: 16 },
  dugme: {
    paddingVertical: 13,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
});
