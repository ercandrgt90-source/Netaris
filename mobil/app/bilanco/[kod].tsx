// BILANCO DETAYI
//
// RAKAM AI YORUMUNU BEKLEMIYOR. Site tarafinda bilanco sayfasi
// yorum uretilemezse HIC yazilmiyor; olculdu (2026-11-22): ozette
// 384 sirketin olcumu var, 2026 3. ceyrek sayfasi olan 341. Bu
// ekran rakami yorumdan ayirarak gosteriyor ve yorum yayimlanmissa
// sayfaya bag veriyor.
//
// UC KURAL EKRANDA GORUNUR:
//
// 1. DERINLIK GIZLENMIYOR. "ozet" derinliginde TL seviyeleri henuz
//    cekilmemis; tabloyu sessizce bos birakmak okura ariza
//    izlenimi verirdi. Sebebi yazili.
//
// 2. ISARET DEGISIMINDE YUZDE YOK. Kardan zarara gecen kalemde
//    "yuzde kac azaldi" sorusunun cevabi yoktur; besleme `degisim`i
//    null gonderiyor ve ekran iki donemin SEVIYESINI yan yana
//    basiyor. Sitede de ayni kural geciyor (olculdu: 220 sayfada
//    597 yaniltici yuzde uretilmisti).
//
// 3. DONEM VE CEKIM ZAMANI SAYIDAN AYRILMIYOR. Bir bilanco rakami
//    tek basina "guncel" izlenimi veriyor; hangi donem oldugu ve
//    verinin ne zaman alindigi birlikte duruyor.
//
// BICIMLENDIRME YOK: butun metinler beslemeden hazir geliyor
// (`deger_metin`, `degisim_metin`). Burada yeniden bicimlendirmek,
// "474,39 milyar TL" karari Python'da ve TypeScript'te ayri ayri
// verilmesi olurdu ve iki yer zamanla ayrisir.

import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Durum, Etiket, tarihTR } from "../../src/bilesen";
import { useTema, yonRengi } from "../../src/tema";
import { useVeri } from "../../src/veri";

/** Eğilim serisinde hangi kalem çizilsin. */
const SERI_ALANI = "hasilat";

/**
 * Basit kıvılcım: seriyi dar bir alanda çubuklarla gösterir.
 *
 * Grafik kütüphanesi EKLENMEDİ -- tek bir eğri için ek paket ve ek
 * boyut demekti; `varlik/[kod].tsx` de aynı gerekçeyle böyle.
 *
 * NEGATİF DEĞER DE ÇİZİLİYOR: taban serinin en küçüğü, yani zarar
 * eden çeyrek "sıfır" gibi görünmüyor. Eksik gözlem atlanıyor,
 * sıfır sayılmıyor -- "veri yok" ile "değer sıfır" ayrı şeyler.
 */
function Kivilcim({ degerler }: { degerler: number[] }) {
  const t = useTema();
  if (degerler.length < 3) return null;
  const enAz = Math.min(...degerler);
  const enCok = Math.max(...degerler);
  const aralik = enCok - enAz || 1;
  return (
    <View style={d.kivilcim} accessibilityLabel="Son dönemlerin seyri">
      {degerler.map((v, i) => (
        <View
          key={i}
          style={{
            flex: 1,
            height: Math.max(2, ((v - enAz) / aralik) * 40),
            backgroundColor:
              i === degerler.length - 1 ? t.renk.vurgu : t.renk.cizgiParlak,
            borderRadius: 1,
          }}
        />
      ))}
    </View>
  );
}

export default function BilancoDetayi() {
  const { kod } = useLocalSearchParams<{ kod: string }>();
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const b = useVeri(
    () => api.bilanco(String(kod)),
    [kod],
    `/v1/bilanco/${String(kod).toLowerCase()}.json`,
  );

  const v = b.veri;
  // SERI EN YENI BASTA GELIYOR; cizim SOLDAN SAGA eski -> yeni
  // olmali, yoksa artan bir egilim azaliyor gibi gorunur.
  const seri = v ? [...v.seri].reverse() : [];
  const cizim = seri
    .map((s) => s[SERI_ALANI])
    .filter((x): x is number => typeof x === "number" && Number.isFinite(x));

  return (
    <>
      <Stack.Screen options={{ title: v?.kod || String(kod || "Bilanço") }} />
      <ScrollView
        style={{ backgroundColor: t.renk.zemin }}
        contentContainerStyle={{
          padding: 16,
          paddingBottom: alt + 32,
          gap: 14,
        }}
      >
        <Durum
          yukleniyor={b.yukleniyor}
          hata={b.engelleyenHata}
          yenile={b.yenile}
        />

        {v ? (
          <>
            <View style={{ gap: 4 }}>
              <Text style={[d.baslik, { color: t.renk.yazi }]}>{v.kod}</Text>
              <Text style={[d.unvan, { color: t.renk.yazi2 }]}>{v.unvan}</Text>
            </View>

            <View style={d.satir}>
              {v.sektor ? <Etiket metin={v.sektor} /> : null}
              {v.alt_sektor ? (
                <Text style={[d.ufak, { color: t.renk.notr }]}>
                  {v.alt_sektor}
                </Text>
              ) : null}
            </View>

            {/* DONEM VE CEKIM ZAMANI -- SAYIDAN AYRILMIYOR. */}
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              {v.donem}
              {v.donem_bitis ? ` · dönem sonu ${tarihTR(v.donem_bitis)}` : ""}
              {v.guncellendi
                ? ` · veri ${tarihTR(v.guncellendi.slice(0, 10))}`
                : ""}
            </Text>

            {/* ORANLAR VE SEKTOR MEDYANI. Medyan kesitsel bir
                istatistik: tek sirketin verisinden uretilemez,
                beslemede sektor ozetinden geliyor. */}
            {v.oranlar.length > 0 ? (
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
                <Text style={[d.kutuBaslik, { color: t.renk.notr }]}>
                  ORANLAR
                </Text>
                {v.oranlar.map((o) => (
                  <View key={o.alan} style={d.oranSatiri}>
                    <Text style={[d.oranAd, { color: t.renk.yazi2 }]}>
                      {o.ad}
                    </Text>
                    <Text style={[d.oranDeger, { color: t.renk.yazi }]}>
                      {o.deger_metin}
                    </Text>
                    {/* MEDYAN YOKSA HICBIR SEY YAZILMIYOR.
                        Sektorde ucten az sirket varsa medyan
                        uretilmiyor ve "0" yazmak olcumsuzlugu
                        olcum gibi gostermek olurdu. */}
                    <Text style={[d.oranMedyan, { color: t.renk.notr }]}>
                      {o.medyan_metin ? `medyan ${o.medyan_metin}` : ""}
                    </Text>
                  </View>
                ))}
                {/* NOT YALNIZCA MEDYAN GERCEKTEN VARSA.
                    Ölçüldü (TUPRS, gerçek Chrome): Enerji sektöründe
                    iki şirket var, eşik üç -- yani hiçbir satırda
                    medyan basılmıyor ama not yine de "Medyan, 2
                    şirketlik sektör kümesinden" diyordu. Olmayan bir
                    kıyası varmış gibi duyurmak, boş bırakmaktan
                    kötü. */}
                {v.oranlar.some((o) => o.medyan_metin) ? (
                  <Text style={[d.ufak, { color: t.renk.notr }]}>
                    Medyan, {v.sektor_sirket_sayisi} şirketlik sektör
                    kümesinden.
                  </Text>
                ) : null}
              </View>
            ) : null}

            {/* SEVIYE TABLOSU -- yalnizca defter derinliginde. */}
            {v.olcumler.length > 0 ? (
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
                <Text style={[d.kutuBaslik, { color: t.renk.notr }]}>
                  ÖLÇÜMLER · ÖNCEKİ YILIN AYNI DÖNEMİNE GÖRE
                </Text>
                {v.olcumler.map((o) => (
                  <View key={o.alan} style={d.olcumSatiri}>
                    <Text style={[d.olcumAd, { color: t.renk.yazi2 }]}>
                      {o.ad}
                    </Text>
                    <View style={{ alignItems: "flex-end", gap: 1 }}>
                      <Text style={[d.olcumDeger, { color: t.renk.yazi }]}>
                        {o.deger_metin}
                      </Text>
                      {/* DEGISIM VARSA YUZDE, YOKSA ONCEKI SEVIYE.
                          Isaret degisiminde yuzde uretilmiyor ama
                          bilgi SILINMIYOR: okur "ne oldu" sorusunun
                          cevabini iki seviyeyi gorerek aliyor. */}
                      {o.degisim_metin ? (
                        <Text
                          style={[
                            d.olcumDegisim,
                            {
                              color: yonRengi(
                                t,
                                (o.degisim ?? 0) >= 0 ? "artis" : "azalis",
                              ),
                            },
                          ]}
                        >
                          {o.degisim_metin}
                        </Text>
                      ) : o.once_metin ? (
                        <Text style={[d.ufak, { color: t.renk.notr }]}>
                          önce {o.once_metin}
                        </Text>
                      ) : null}
                    </View>
                  </View>
                ))}
              </View>
            ) : (
              // DERINLIK "ozet": SEBEBI YAZILI.
              //
              // Bos tablo basmak ya da hic bolum gostermemek, okura
              // "uygulama bozuk" dusuncesi verirdi. Eksik olan sey
              // belirli: o sirketin mali tablosu henuz cekilmedi.
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
                  TABLO HENÜZ ÇEKİLMEDİ
                </Text>
                <Text style={[d.govde, { color: t.renk.yazi2 }]}>
                  Bu şirketin oranları ölçüldü, TL seviyeleri henüz
                  alınmadı. Mali tablolar şirket şirket ve kaynağa yük
                  bindirmeden çekiliyor; sıradaki koşularda bu bölüm
                  dolacak.
                </Text>
              </View>
            )}

            {/* EGILIM -- son donemler. */}
            {cizim.length >= 3 ? (
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
                <Text style={[d.kutuBaslik, { color: t.renk.notr }]}>
                  HASILAT · SON {cizim.length} DÖNEM
                </Text>
                <Kivilcim degerler={cizim} />
                {seri.map((s) => (
                  <View key={`${s.etiket}-${s.bitis}`} style={d.seriSatiri}>
                    <Text style={[d.ufak, { color: t.renk.notr }]}>
                      {s.etiket}
                    </Text>
                    <Text style={[d.seriDeger, { color: t.renk.yazi2 }]}>
                      {s.metin?.[SERI_ALANI] || "—"}
                    </Text>
                  </View>
                ))}
                {/* MEVSIMSELLIK NOTU: ardisik donemler bir yil
                    oncesiyle AYNI SORU DEGIL. Perakendede son ceyrek
                    her yil yuksektir ve bu buyume degil takvimdir --
                    ayni ayrim `bilanco_ag.donem_toplami` icinde de
                    yazili. */}
                <Text style={[d.ufak, { color: t.renk.notr }]}>
                  Ardışık dönemler; mevsimsellik taşır. Yukarıdaki
                  değişim oranları bir yıl öncesinin aynı dönemiyle
                  karşılaştırılıyor.
                </Text>
              </View>
            ) : null}

            {/* YORUM SAYFASI VARSA. Yoksa hicbir sey yazilmiyor:
                "yorum yok" demek, olmayan bir eksigi duyurmak
                olurdu -- rakam zaten burada. */}
            {v.sayfa_slug ? (
              <Pressable
                onPress={() => router.push(`/analiz/${v.sayfa_slug}`)}
                accessibilityRole="button"
                style={({ pressed }) => [
                  d.bag,
                  {
                    backgroundColor: t.renk.panel2,
                    borderColor: t.renk.cizgi,
                    borderRadius: t.r.kucuk,
                    opacity: pressed ? 0.7 : 1,
                  },
                ]}
              >
                <Text style={{ color: t.renk.vurgu, fontSize: 14 }}>
                  Bu dönemin analizini oku →
                </Text>
              </Pressable>
            ) : null}

            <Text style={[d.ufak, { color: t.renk.notr }]}>
              Kaynak: şirketlerin kamuya açıkladığı mali tablolar.
              Dönem rakamları kümülatif ara dönem değil, çeyrek
              bazındadır.
            </Text>
          </>
        ) : null}
      </ScrollView>
    </>
  );
}

const d = StyleSheet.create({
  baslik: { fontSize: 24, fontWeight: "800", letterSpacing: 0.5 },
  unvan: { fontSize: 14, lineHeight: 20 },
  satir: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap" },
  ufak: { fontSize: 12, lineHeight: 17 },
  govde: { fontSize: 14, lineHeight: 21 },
  kutu: {
    borderWidth: StyleSheet.hairlineWidth,
    padding: 14,
    gap: 8,
  },
  kutuBaslik: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.8,
  },
  oranSatiri: { flexDirection: "row", alignItems: "center", gap: 8 },
  oranAd: { flex: 1, fontSize: 13 },
  oranDeger: {
    fontSize: 14,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
    minWidth: 64,
    textAlign: "right",
  },
  oranMedyan: {
    fontSize: 11,
    fontVariant: ["tabular-nums"],
    minWidth: 86,
    textAlign: "right",
  },
  olcumSatiri: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    minHeight: 34,
  },
  olcumAd: { flex: 1, fontSize: 13 },
  olcumDeger: { fontSize: 14, fontWeight: "700", fontVariant: ["tabular-nums"] },
  olcumDegisim: { fontSize: 12, fontWeight: "600", fontVariant: ["tabular-nums"] },
  kivilcim: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 3,
    height: 44,
    marginVertical: 4,
  },
  seriSatiri: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  },
  seriDeger: { fontSize: 13, fontVariant: ["tabular-nums"] },
  bag: {
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 16,
    paddingVertical: 13,
    minHeight: 44,
    justifyContent: "center",
    alignItems: "center",
  },
});
