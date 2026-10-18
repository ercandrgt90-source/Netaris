// ARASTIRMA MERKEZI
//
// Sartname dort arastirma turunu AYIRMAYI istiyor: bilanco analizi,
// makro arastirma, teknik gorunum ve imzali yorum. Suzgec bunun
// uzerine kurulu -- turler karisik tek bir listede akmiyor.
//
// SURECE SAYFALAMA: besleme 24'luk sayfalar veriyor ve liste
// sonuna gelindiginde bir sonraki sayfa yukleniyor. Hepsini bir
// kerede indirmek 233 kaydi ve tum ozetleri ilk acilista cekmek
// olurdu.
//
// IMZALI YORUM OTOMATIK ANALIZDEN AYRI: kart yazarin adini
// gosteriyor (`AnalizKarti` icinde), suzgec de ayri bir tur olarak
// tutuyor.

import { useRouter } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import {
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { AnalizKarti, Durum } from "../../src/bilesen";
import { useTema } from "../../src/tema";

/** Suzgec tanimi. `sina` kaydin bu ture girip girmedigini soyler. */
const TURLER: { ad: string; sina: (a: api.Analiz) => boolean }[] = [
  { ad: "Tümü", sina: () => true },
  { ad: "Bilanço", sina: (a) => /bilan/i.test(a.kategori) },
  { ad: "Makro", sina: (a) => /makro/i.test(a.kategori) || a.kod === "MAKRO" },
  { ad: "Teknik", sina: (a) => /teknik/i.test(a.kategori) },
  { ad: "İmzalı", sina: (a) => a.imzali },
];

export default function Arastirma() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;

  const [kayitlar, setKayitlar] = useState<api.Analiz[]>([]);
  const [sayfa, setSayfa] = useState(0);
  const [toplamSayfa, setToplamSayfa] = useState<number | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [tur, setTur] = useState(0);

  const sonrakiSayfa = useCallback(
    async (sifirla = false) => {
      if (yukleniyor) return;
      const istenen = sifirla ? 1 : sayfa + 1;
      if (!sifirla && toplamSayfa !== null && istenen > toplamSayfa) return;
      setYukleniyor(true);
      setHata(null);
      try {
        const s = await api.analizSayfasi(istenen);
        setKayitlar((eski) => (sifirla ? s.ogeler : [...eski, ...s.ogeler]));
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

  // Ilk yuk.
  React.useEffect(() => {
    void sonrakiSayfa(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const gorunen = useMemo(
    () => kayitlar.filter(TURLER[tur].sina),
    [kayitlar, tur],
  );

  const analizAc = (slug: string) => router.push(`/analiz/${slug}`);

  return (
    <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
      {/* SUZGEC SERIDI */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={s.suzgec}
      >
        {TURLER.map((x, i) => {
          const secili = i === tur;
          return (
            <Pressable
              key={x.ad}
              onPress={() => setTur(i)}
              accessibilityRole="button"
              accessibilityState={{ selected: secili }}
              style={[
                s.cip,
                {
                  backgroundColor: secili ? t.renk.vurgu : t.renk.panel,
                  borderColor: secili ? t.renk.vurgu : t.renk.cizgi,
                  borderRadius: t.r.kucuk,
                },
              ]}
            >
              <Text
                style={{
                  color: secili ? t.renk.ustYazi : t.renk.yazi2,
                  fontSize: 13,
                  fontWeight: "600",
                }}
              >
                {x.ad}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <FlatList
        data={gorunen}
        keyExtractor={(a) => a.slug}
        renderItem={({ item }) => <AnalizKarti a={item} bas={analizAc} />}
        onEndReached={() => void sonrakiSayfa()}
        onEndReachedThreshold={0.6}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: alt + 28 }}
        ListEmptyComponent={
          <Durum
            yukleniyor={yukleniyor && kayitlar.length === 0}
            hata={hata}
            bos={!yukleniyor && !hata}
            bosMetin={
              kayitlar.length > 0
                ? "Bu türde kayıt yok. Başka bir süzgeç deneyin."
                : "Araştırma bulunamadı."
            }
            yenile={() => void sonrakiSayfa(true)}
          />
        }
        ListFooterComponent={
          <View style={{ paddingTop: 4 }}>
            {/* SAYFALAMA DURUMU GORUNUR: liste bittiginde "hepsi bu"
                demek, sessizce durmaktan iyidir. */}
            {yukleniyor && kayitlar.length > 0 ? (
              <Durum yukleniyor />
            ) : hata && kayitlar.length > 0 ? (
              <Durum hata={hata} yenile={() => void sonrakiSayfa()} />
            ) : toplamSayfa !== null && sayfa >= toplamSayfa ? (
              <Text style={[s.son, { color: t.renk.notr }]}>
                {kayitlar.length} araştırmanın tamamı yüklendi.
              </Text>
            ) : null}
          </View>
        }
      />
    </View>
  );
}

const s = StyleSheet.create({
  suzgec: { paddingHorizontal: 16, paddingVertical: 12, gap: 8 },
  cip: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 40,
    justifyContent: "center",
  },
  son: { fontSize: 12, textAlign: "center", paddingVertical: 18 },
});
