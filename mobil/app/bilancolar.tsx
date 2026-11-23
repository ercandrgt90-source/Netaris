// BILANCOLAR
//
// BOSLUKTU VE OLCULDU (2026-11-22):
//   ozette olculmus sirket            384
//   2026 3. ceyrek sayfasi olan       341
//   uygulamada bilanco ekrani           0
//
// Yani 43 sirketin rakami elimizdeyken hicbir yuzeyde gorunmuyordu,
// 384'un tamami ise uygulamada hic gorunmuyordu. Sebep yapisal:
// bilanco rakami yalnizca markdown sayfasinda yayimlaniyor ve o
// sayfa AI yorumuna bagli ("YORUMSUZ SAYFA YAYIMLANMIYOR").
//
// DERINLIK GIZLENMIYOR. "ozet" derinligindeki sirkette TL seviyesi
// yok, yalnizca oranlar var; bunu sessizce bos tablo olarak
// gostermek okura ariza izlenimi verirdi. Satirda isaretli duruyor.
//
// SEKTOR SUZGECI YUKLEMEYI SURDURUYOR. Liste sektore gore sirali ve
// sayfalanmis; secilen sektor henuz yuklenmemis sayfalarda olabilir.
// Suzgec yalnizca yuklenene bakarsa okur "Enerji'de sirket yok"
// sanirdi -- oysa yuklenmemisti. O yuzden secimde, o sektoru GECENE
// kadar sayfa yuklemeye devam ediliyor.

import { Stack, useRouter } from "expo-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
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
import { CipSeridi, Durum, Etiket } from "../src/bilesen";
import { useTema, yonRengi } from "../src/tema";
import { useVeri } from "../src/veri";

/**
 * Türkçe arama için diakritik sadeleştirme.
 *
 * "turkiye" yazan okur "Türkiye"yi BULMALI. Bu depoda aynı tuzak
 * sessiz yanlış negatif üretti: desen eşleşiyor görünüyor ama
 * eşleşmiyor ve hiçbir hata çıkmıyor. Aynı tablo `varliklar.tsx`
 * içinde de var; ortak bir yere taşımak ayrı bir tur işi ve bu
 * turda ölçmediğim bir davranışı değiştirmek olurdu.
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

export default function Bilancolar() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const dz = useVeri(api.bilancoDizini, [], "/v1/bilanco.json");

  const [kayitlar, setKayitlar] = useState<api.BilancoDizinOgesi[]>([]);
  const [sayfa, setSayfa] = useState(0);
  const [toplamSayfa, setToplamSayfa] = useState<number | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [sektor, setSektor] = useState("");
  const [arama, setArama] = useState("");

  const sonraki = useCallback(async () => {
    if (yukleniyor) return false;
    const istenen = sayfa + 1;
    if (toplamSayfa !== null && istenen > toplamSayfa) return false;
    setYukleniyor(true);
    setHata(null);
    try {
      const s = await api.bilancoSayfasi(istenen);
      setKayitlar((e) => [...e, ...s.ogeler]);
      setSayfa(s.sayfa);
      setToplamSayfa(s.sayfa_sayisi);
      return s.sayfa < s.sayfa_sayisi;
    } catch (h) {
      setHata(h instanceof Error ? h.message : "Bilinmeyen hata.");
      return false;
    } finally {
      setYukleniyor(false);
    }
  }, [sayfa, toplamSayfa, yukleniyor]);

  useEffect(() => {
    void sonraki();
    // Yalnizca ilk acilista.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // SECILEN SEKTOR GECILENE KADAR YUKLEMEYI SURDUR.
  //
  // Liste sektore gore sirali geldigi icin, yuklenen son ogenin
  // sektoru secilenden SONRA geliyorsa o sektorun tamami elimizde.
  // Bu yuzden "hepsini yukle" degil, GEREKTIGI KADAR yukle.
  useEffect(() => {
    if (!sektor || yukleniyor || hata) return;
    if (toplamSayfa !== null && sayfa >= toplamSayfa) return;
    const son = kayitlar[kayitlar.length - 1];
    if (son && son.sektor.localeCompare(sektor, "tr") > 0) return;
    void sonraki();
  }, [sektor, kayitlar, sayfa, toplamSayfa, yukleniyor, hata, sonraki]);

  const gorunen = useMemo(() => {
    let x = kayitlar;
    if (sektor) x = x.filter((k) => k.sektor === sektor);
    const q = sadele(arama.trim());
    if (q) {
      x = x.filter(
        (k) => sadele(k.kod).includes(q) || sadele(k.unvan).includes(q),
      );
    }
    return x;
  }, [kayitlar, sektor, arama]);

  const tumu = toplamSayfa !== null && sayfa >= toplamSayfa;
  const toplam = dz.veri?.toplam ?? 0;

  return (
    <>
      <Stack.Screen options={{ title: "Bilançolar" }} />
      <View style={{ flex: 1, backgroundColor: t.renk.zemin }}>
        <View style={{ padding: 16, paddingBottom: 8 }}>
          <TextInput
            value={arama}
            onChangeText={setArama}
            placeholder="Şirket kodu ya da adı…"
            placeholderTextColor={t.renk.notr}
            autoCapitalize="characters"
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
            accessibilityLabel="Şirket ara"
          />
        </View>

        {/* SECENEK SAYISI BESLEMEDEN: sektor listesi icerikle
            degisiyor ve ekrana yazmak, yeni bir sektor eklendiginde
            onun hic gorunmemesi demek olurdu. Sirket sayilari da
            dizinden geliyor -- burada sayilmiyor, cunku yuklenmemis
            sayfalardaki sirketler eksik sayilirdi. */}
        <CipSeridi
          secenekler={[{ kod: "", ad: `Tümü (${toplam})` }].concat(
            (dz.veri?.sektorler ?? [])
              .filter((s) => s.sektor)
              .map((s) => ({
                kod: s.sektor,
                ad: `${s.sektor} (${s.sirket_sayisi})`,
              })),
          )}
          secili={sektor}
          sec={setSektor}
        />

        <FlatList
          data={gorunen}
          keyExtractor={(x) => x.kod}
          contentContainerStyle={{ paddingBottom: alt + 28 }}
          onEndReachedThreshold={0.6}
          onEndReached={() => {
            if (!tumu && !yukleniyor && !hata) void sonraki();
          }}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/bilanco/${item.kod}`)}
              accessibilityRole="button"
              accessibilityLabel={`${item.kod} bilançosu`}
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
                <Text style={[d.kod, { color: t.renk.yazi }]}>{item.kod}</Text>
                <Text
                  numberOfLines={1}
                  style={[d.unvan, { color: t.renk.notr }]}
                >
                  {item.unvan}
                </Text>
                <View style={d.ufakSatir}>
                  {item.sektor ? <Etiket metin={item.sektor} /> : null}
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    {item.donem}
                  </Text>
                  {/* DERINLIK ISARETI -- yoklugu bildiriyor.
                      "ozet" demek: oranlar var, TL seviyeleri henuz
                      cekilmedi. Gizlemek, bos tabloyu ariza
                      sandirmak olurdu. */}
                  {item.derinlik !== "defter" ? (
                    <Text style={[d.ufak, { color: t.renk.notr }]}>
                      · tablo bekliyor
                    </Text>
                  ) : null}
                </View>
              </View>

              <View style={{ alignItems: "flex-end", gap: 2 }}>
                {/* METIN BESLEMEDEN GELIYOR. Burada bicimlendirme
                    yapilsa ayni oran sitede ve uygulamada iki
                    farkli yazilabilirdi. */}
                {item.net_marj_metin ? (
                  <Text
                    style={[
                      d.deger,
                      {
                        color:
                          item.net_marj === null
                            ? t.renk.yazi
                            : yonRengi(
                                t,
                                item.net_marj >= 0 ? "artis" : "azalis",
                              ),
                      },
                    ]}
                  >
                    {item.net_marj_metin}
                  </Text>
                ) : null}
                <Text style={[d.birim, { color: t.renk.notr }]}>net marj</Text>
                {item.roe_metin ? (
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    ROE {item.roe_metin}
                  </Text>
                ) : null}
              </View>
            </Pressable>
          )}
          ListEmptyComponent={
            <Durum
              yukleniyor={yukleniyor || dz.yukleniyor}
              hata={kayitlar.length === 0 ? hata : null}
              bos={!yukleniyor && !hata}
              bosMetin={
                arama || sektor
                  ? "Eşleşen şirket yok."
                  : "Bilanço verisi bulunamadı."
              }
              yenile={() => void sonraki()}
            />
          }
          ListFooterComponent={
            gorunen.length > 0 ? (
              <View style={{ gap: 6 }}>
                {!tumu ? (
                  <Pressable
                    onPress={() => void sonraki()}
                    disabled={yukleniyor}
                    accessibilityRole="button"
                    style={({ pressed }) => [
                      d.dahaFazla,
                      {
                        borderColor: t.renk.cizgi,
                        backgroundColor: t.renk.panel2,
                        borderRadius: t.r.kucuk,
                        opacity: pressed || yukleniyor ? 0.6 : 1,
                      },
                    ]}
                  >
                    <Text style={{ color: t.renk.vurgu, fontSize: 14 }}>
                      {yukleniyor ? "Yükleniyor…" : "Daha fazla şirket"}
                    </Text>
                  </Pressable>
                ) : null}
                <Text style={[d.not, { color: t.renk.notr }]}>
                  {/* SAYIM DURUST: kac sirket YUKLENDI ve toplam kac
                      var. "384 şirket" yazip 48'ini gostermek,
                      okurun aradigini bulamadiginda veriyi yok
                      sanmasina yol acardi. */}
                  {gorunen.length} şirket gösteriliyor ·{" "}
                  {kayitlar.length}/{toplam} yüklendi
                  {dz.veri
                    ? ` · ${dz.veri.defterli} şirkette tam tablo var`
                    : ""}
                  . Sıra sektöre, sonra koda göre.
                </Text>
              </View>
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
  kod: { fontSize: 15, fontWeight: "700", letterSpacing: 0.4 },
  unvan: { fontSize: 12 },
  ufakSatir: { flexDirection: "row", alignItems: "center", gap: 7 },
  ufak: { fontSize: 12 },
  deger: { fontSize: 16, fontWeight: "700", fontVariant: ["tabular-nums"] },
  birim: { fontSize: 10, fontWeight: "500" },
  dahaFazla: {
    alignSelf: "center",
    paddingHorizontal: 18,
    paddingVertical: 11,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 44,
    justifyContent: "center",
  },
  not: {
    fontSize: 12,
    lineHeight: 18,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
});
