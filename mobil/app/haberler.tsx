// HABERLER
//
// BOSLUKTU: beslemede 1.075 haber var ama uygulamada ana sayfadaki
// sekiz one cikandan baskasina ulasilamiyordu. Sartname 9. bolum
// hizli taranabilir bir haber ekrani istiyor; konu bolumleri de
// orada sayili.
//
// KONU SUZGECI BESLEMEDEN TURETILIYOR, listeye yazilmiyor: konu
// kumesi icerikle birlikte degisiyor (yeni bir konu eklenince
// listeyi guncellemeyi unutmak, o konunun hic gorunmemesi demek).
// Ilk sayfadaki konular sayilip en cok kullanilanlar one aliniyor.
//
// CANLI AKIS AYRI BIR BOLUMDE: `/api/tel` ajans basliklarini on
// dakikada bir tazeliyor ve bu YAYIMLANMIS haberden farkli bir sey
// -- biri bizim sayfamiz, oteki ham ajans basligi. Karistirilmamasi
// icin ayri sekmede ve kurum adiyla birlikte.

import { Stack, useRouter } from "expo-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../src/api";
import { Durum, HaberKarti } from "../src/bilesen";
import { useTema } from "../src/tema";
import { useVeri } from "../src/veri";

/** Konu süzgecinde en çok kaç seçenek gösterilsin. */
const EN_COK_KONU = 8;

function Akis() {
  const t = useTema();
  const alt = useSafeAreaInsets().bottom;
  const tl = useVeri(() => api.tel(40));

  return (
    <FlatList
      style={{ backgroundColor: t.renk.zemin }}
      data={tl.veri?.ogeler ?? []}
      keyExtractor={(o, i) => `${o.adres}-${i}`}
      contentContainerStyle={{ paddingBottom: alt + 28 }}
      ListHeaderComponent={
        <Text style={[d.not, { color: t.renk.notr }]}>
          Ajans başlıkları, on dakikada bir tazeleniyor. Bunlar ham
          kaynak başlıklarıdır; Netaris'in yayımladığı haberlerden
          ayrıdır.
        </Text>
      }
      renderItem={({ item }) => (
        <View
          style={[
            d.akisOge,
            { borderBottomColor: t.renk.cizgi },
          ]}
        >
          <Text style={[d.akisSaat, { color: t.renk.vurgu }]}>
            {item.tarih ? item.tarih.slice(11, 16) : "—"}
          </Text>
          <View style={{ flex: 1, gap: 3 }}>
            <Text style={[d.akisBaslik, { color: t.renk.yazi }]}>
              {item.baslik}
            </Text>
            {/* TICARI KAYNAK ADI GORUNUR -- kisa iktibas hakkinin
                sarti. */}
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              {item.kurum_tam || item.kurum}
              {item.cevrildi ? " · çeviri" : ""}
              {item.konu ? ` · ${item.konu}` : ""}
            </Text>
          </View>
        </View>
      )}
      ListEmptyComponent={
        <Durum
          yukleniyor={tl.yukleniyor}
          hata={tl.hata}
          bos={!tl.yukleniyor && !tl.hata}
          bosMetin="Akışta şu an öge yok."
          yenile={tl.yenile}
        />
      }
    />
  );
}

function Yayimlananlar() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;

  const [kayitlar, setKayitlar] = useState<api.Haber[]>([]);
  const [sayfa, setSayfa] = useState(0);
  const [toplamSayfa, setToplamSayfa] = useState<number | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [konu, setKonu] = useState("");

  const sonraki = useCallback(
    async (sifirla = false) => {
      if (yukleniyor) return;
      const istenen = sifirla ? 1 : sayfa + 1;
      if (!sifirla && toplamSayfa !== null && istenen > toplamSayfa) return;
      setYukleniyor(true);
      setHata(null);
      try {
        const s = await api.haberSayfasi(istenen);
        setKayitlar((e) => (sifirla ? s.ogeler : [...e, ...s.ogeler]));
        setSayfa(s.sayfa);
        setToplamSayfa(s.sayfa_sayisi);
      } catch (h) {
        setHata(h instanceof Error ? h.message : "Bilinmeyen hata.");
      } finally {
        setYukleniyor(false);
      }
    },
    [sayfa, toplamSayfa, yukleniyor],
  );

  useEffect(() => {
    void sonraki(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // KONULAR ICERIKTEN SAYILIYOR -- sabit liste tutulmuyor.
  const konular = useMemo(() => {
    const say = new Map<string, number>();
    for (const h of kayitlar) {
      if (h.konu) say.set(h.konu, (say.get(h.konu) || 0) + 1);
    }
    return [...say.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, EN_COK_KONU)
      .map(([ad, n]) => ({ ad, n }));
  }, [kayitlar]);

  const gorunen = useMemo(
    () => (konu ? kayitlar.filter((h) => h.konu === konu) : kayitlar),
    [kayitlar, konu],
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
      {konular.length > 1 ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={d.cipler}
        >
          {[{ ad: "", n: kayitlar.length }].concat(konular).map((x) => {
            const aktif = x.ad === konu;
            return (
              <Pressable
                key={x.ad || "hepsi"}
                onPress={() => setKonu(x.ad)}
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
                  {x.ad || "Tümü"} ({x.n})
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}

      <FlatList
        data={gorunen}
        keyExtractor={(h, i) => `${h.slug}-${i}`}
        renderItem={({ item }) => (
          <HaberKarti h={item} bas={(s) => router.push(`/haber/${s}`)} />
        )}
        onEndReached={() => void sonraki()}
        onEndReachedThreshold={0.6}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: alt + 28 }}
        ListEmptyComponent={
          <Durum
            yukleniyor={yukleniyor && kayitlar.length === 0}
            hata={hata}
            bos={!yukleniyor && !hata}
            bosMetin={
              konu
                ? "Bu konuda yüklenmiş haber yok. Aşağı kaydırıp daha çok yükleyin."
                : "Haber bulunamadı."
            }
            yenile={() => void sonraki(true)}
          />
        }
        ListFooterComponent={
          <View style={{ paddingTop: 4 }}>
            {yukleniyor && kayitlar.length > 0 ? (
              <Durum yukleniyor />
            ) : hata && kayitlar.length > 0 ? (
              <Durum hata={hata} yenile={() => void sonraki()} />
            ) : toplamSayfa !== null && sayfa >= toplamSayfa ? (
              <Text style={[d.not, { color: t.renk.notr }]}>
                {kayitlar.length} haberin tamamı yüklendi.
              </Text>
            ) : null}
          </View>
        }
      />
    </View>
  );
}

export default function Haberler() {
  const t = useTema();
  const [sekme, setSekme] = useState<"yayin" | "akis">("yayin");

  return (
    <>
      <Stack.Screen options={{ title: "Haberler" }} />
      <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
        {/* IKI AYRI SEY, IKI AYRI SEKME: yayimlanmis haber bizim
            sayfamiz, canli akis ham ajans basligi. */}
        <View style={[d.sekmeler, { borderBottomColor: t.renk.cizgi }]}>
          {[
            { kod: "yayin", ad: "Yayımlananlar" },
            { kod: "akis", ad: "Canlı akış" },
          ].map((x) => {
            const aktif = x.kod === sekme;
            return (
              <Pressable
                key={x.kod}
                onPress={() => setSekme(x.kod as "yayin" | "akis")}
                accessibilityRole="button"
                accessibilityState={{ selected: aktif }}
                style={[
                  d.sekme,
                  aktif ? { borderBottomColor: t.renk.vurgu } : null,
                ]}
              >
                <Text
                  style={{
                    color: aktif ? t.renk.vurgu : t.renk.yazi3,
                    fontSize: 14,
                    fontWeight: aktif ? "700" : "600",
                  }}
                >
                  {x.ad}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {sekme === "yayin" ? <Yayimlananlar /> : <Akis />}
      </View>
    </>
  );
}

const d = StyleSheet.create({
  sekmeler: { flexDirection: "row", borderBottomWidth: StyleSheet.hairlineWidth },
  sekme: {
    flex: 1,
    paddingVertical: 14,
    alignItems: "center",
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
    minHeight: 48,
  },
  cipler: { paddingHorizontal: 16, paddingVertical: 12, gap: 8 },
  cip: {
    paddingHorizontal: 13,
    paddingVertical: 9,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 40,
    justifyContent: "center",
  },
  akisOge: {
    flexDirection: "row",
    gap: 10,
    paddingVertical: 13,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  akisSaat: { fontSize: 12, fontWeight: "700", width: 40 },
  akisBaslik: { fontSize: 14, lineHeight: 19 },
  ufak: { fontSize: 11 },
  not: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginVertical: 12,
  },
});
