// ARASTIRMA / BILANCO DETAYI
//
// SARTNAMENIN EN ONEMLI KURALI BU EKRANDA: muhasebe verisi,
// turetilmis oranlar ve yapay zeka yorumu BIRBIRINDEN AYRI.
//
// Bu ayrim beslemede de korunuyor: oranlar `oranlar.py`den geliyor
// ve besleme onlari YENIDEN HESAPLAMIYOR. Depoda ayni seyi iki
// yerde hesaplamak yayinda yanlis sayi uretti (negatif ozkaynakla
// +%128,5 ozkaynak karliligi). Uygulama da hesap yapmiyor; gosteriyor.
//
// GOVDE WEBVIEW ILE ISLENIYOR cunku bilanco tablolari analizin
// kendisi. Gerekce `src/govde.tsx` basinda.
//
// ETIKETLER ZORUNLU:
//   * `kurgusal` -> KURGUSAL rozeti
//   * imzali yorum -> yazar adi ve unvani
//   * skor -> metodoloji baglantisiyla birlikte

import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect } from "react";
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
import { Durum, Etiket, tarihTR } from "../../src/bilesen";
import * as gecmis from "../../src/gecmis";
import { Govde } from "../../src/govde";
import { useTema } from "../../src/tema";
import { useVeri } from "../../src/veri";

export default function AnalizDetayi() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const a = useVeri(() => api.analiz(String(slug)), [slug],
    `/v1/analiz/${String(slug)}.json`);

  // Gerekce `app/haber/[slug].tsx` icinde: yalnizca gercek veri
  // geldiginde kayit dusuyor, liste cihazdan cikmiyor.
  useEffect(() => {
    if (!a.veri?.baslik) return;
    void gecmis.kaydet({
      tur: "analiz",
      slug: String(slug),
      baslik: a.veri.baslik,
      yol: a.veri.yol || "",
      an: new Date().toISOString(),
    });
  }, [a.veri, slug]);

  const paylas = async () => {
    if (!a.veri) return;
    await Share.share({
      message: `${a.veri.baslik}\n${api.webAdresi(a.veri.yol)}`,
      url: api.webAdresi(a.veri.yol),
      title: a.veri.baslik,
    });
  };

  return (
    <ScrollView
      style={{ backgroundColor: t.renk.zemin }}
      contentContainerStyle={{ padding: 16, paddingBottom: alt + 32, gap: 12 }}
    >
      <Durum yukleniyor={a.yukleniyor} hata={a.engelleyenHata} yenile={a.yenile} />

      {a.veri ? (
        <>
          <View style={d.satir}>
            {a.veri.kategori ? (
              <Etiket metin={a.veri.kategori} renk={t.renk.vurgu} />
            ) : null}
            {/* KURGUSAL ICERIK ETIKETLI -- isaret ulasmazsa kurgusal
                icerik gercek gibi gorunur. */}
            {a.veri.kurgusal ? (
              <Etiket metin="KURGUSAL" renk={t.renk.uyari} />
            ) : null}
            {a.veri.tarih ? (
              <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
                {tarihTR(a.veri.tarih)}
              </Text>
            ) : null}
            {a.veri.okuma_dk ? (
              <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
                · {a.veri.okuma_dk} dk
              </Text>
            ) : null}
          </View>

          <Text style={[d.baslik, { color: t.renk.yazi }]}>
            {a.veri.baslik}
          </Text>

          {/* SIRKET VE DONEM: hangi donemin olcuMu oldugu basligin
              hemen altinda. Donem belirsiz bir bilanco analizi
              yorumlanamaz. */}
          {a.veri.sirket || a.veri.donem ? (
            <Text style={[d.altSatir, { color: t.renk.yazi2 }]}>
              {a.veri.sirket}
              {a.veri.kod && a.veri.kod !== "MAKRO" && a.veri.kod !== "YORUM"
                ? ` (${a.veri.kod})`
                : ""}
              {a.veri.donem ? ` · ${a.veri.donem}` : ""}
              {a.veri.sektor ? ` · ${a.veri.sektor}` : ""}
            </Text>
          ) : null}

          {/* IMZALI YORUM OTOMATIK ANALIZDEN AYRI GOSTERILIYOR. */}
          {a.veri.imzali ? (
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
                İMZALI DEĞERLENDİRME
              </Text>
              <Text style={[d.govde, { color: t.renk.yazi }]}>
                {a.veri.yazar}
                {a.veri.unvan ? ` · ${a.veri.unvan}` : ""}
              </Text>
            </View>
          ) : null}

          {/* SKOR VE KRITERLER -- turetilmis olculer, ayri bir kutu.
              Metodoloji baglantisi veriliyor: aciklanamayan bir skor
              bir sayi degil, bir iddia olurdu. */}
          {a.veri.skor || (a.veri.kriterler && a.veri.kriterler.length) ? (
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
                TÜRETİLMİŞ ÖLÇÜLER
              </Text>
              {a.veri.skor ? (
                <Text style={[d.skor, { color: t.renk.yazi }]}>
                  Skor: {a.veri.skor}
                  {a.veri.kapsam ? (
                    <Text style={[d.ufak, { color: t.renk.notr }]}>
                      {"  "}({a.veri.kapsam})
                    </Text>
                  ) : null}
                </Text>
              ) : null}
              {(a.veri.kriterler || []).map((k) => (
                <View key={k.ad} style={d.kriter}>
                  <Text style={[d.govde, { color: t.renk.yazi2, flex: 1 }]}>
                    {k.ad}
                  </Text>
                  <Text
                    style={[
                      d.govde,
                      { color: t.renk.yazi, fontVariant: ["tabular-nums"] },
                    ]}
                  >
                    {k.puan} / {k.tam}
                  </Text>
                </View>
              ))}
              <Pressable
                onPress={() =>
                  Linking.openURL(api.webAdresi("/metodoloji/"))
                }
                accessibilityRole="link"
                style={{ paddingVertical: 10, minHeight: 44, justifyContent: "center" }}
              >
                <Text style={{ color: t.renk.vurgu, fontSize: 13 }}>
                  Skor nasıl hesaplanıyor? · Metodoloji
                </Text>
              </Pressable>
            </View>
          ) : null}

          {/* GOVDE -- tablolar dahil, oldugu gibi. */}
          <Govde
            html={a.veri.govde_html || ""}
            tema={t}
            disBaglanti={(adres) => {
              void Linking.openURL(adres);
            }}
          />

          {/* KAYNAKLAR. Bir bilanco analizinin hangi veriden
              uretildigi gorunmezse dogrulanamaz. */}
          {a.veri.kaynaklar && a.veri.kaynaklar.length > 0 ? (
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              Veri kaynağı: {a.veri.kaynaklar.join(" · ")}
              {a.veri.veri_kaynagi &&
              !a.veri.kaynaklar.includes(a.veri.veri_kaynagi)
                ? ` · ${a.veri.veri_kaynagi}`
                : ""}
            </Text>
          ) : null}

          {/* NASIL URETILDI sayimlari. */}
          {a.veri.sayimlar && a.veri.sayimlar.length > 0 ? (
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
              <Text style={[d.kutuBaslik, { color: t.renk.yazi3 }]}>
                NASIL ÜRETİLDİ
              </Text>
              {a.veri.sayimlar.map(([sayi, etiket], i) => (
                <Text key={i} style={[d.ufak, { color: t.renk.yazi2 }]}>
                  {sayi} {etiket}
                </Text>
              ))}
            </View>
          ) : null}

          <View style={d.satir}>
            <Pressable
              onPress={paylas}
              accessibilityRole="button"
              style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={{ color: t.renk.yazi }}>Paylaş</Text>
            </Pressable>
            <Pressable
              onPress={() => Linking.openURL(api.webAdresi(a.veri!.yol))}
              accessibilityRole="link"
              style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
            >
              <Text style={{ color: t.renk.yazi }}>Sitede aç</Text>
            </Pressable>
          </View>

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
  baslik: { fontSize: 23, fontWeight: "700", lineHeight: 30, letterSpacing: -0.4 },
  altSatir: { fontSize: 14, lineHeight: 20 },
  kutu: { padding: 14, borderWidth: StyleSheet.hairlineWidth, gap: 7 },
  kutuBaslik: { fontSize: 10, fontWeight: "700", letterSpacing: 0.7 },
  govde: { fontSize: 15, lineHeight: 22 },
  skor: { fontSize: 18, fontWeight: "700" },
  kriter: { flexDirection: "row", alignItems: "center", gap: 10 },
  ufak: { fontSize: 12, lineHeight: 18 },
  dugme: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderRadius: 10,
    minHeight: 44,
    justifyContent: "center",
  },
});
