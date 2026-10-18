// ANA SAYFA
//
// Bilgi bakimindan zengin, gorsel olarak sade. Oncelik sirasi:
//   1. Piyasa ozeti (LISANSI BIZDE OLAN kume)
//   2. Gunun onemli gelismeleri
//   3. Canli tel akisi
//   4. One cikan arastirmalar
//
// LISANS NOTU -- OKURA DA SOYLENIYOR
// Sartname ana sayfada BIST 100, S&P 500, Nasdaq ve DAX istiyordu.
// Bu endekslerin dagitim lisansi bizde DEGIL (Borsa Istanbul,
// S&P Dow Jones Indices, Nasdaq Inc., Deutsche Boerse) ve besleme
// onlari zaten elemis durumda. Ekranda bir aciklama satiri var:
// eksikligin sebebi gorunur olsun, okur "neden yok" diye merak
// etmesin. Eksik bir grup, lisanssiz bir gruptan iyidir.
//
// SAHTE VERI YOK: her bolum kendi yukleniyor/hata/bos halini
// gosteriyor.

import { useRouter } from "expo-router";
import React from "react";
import { FlatList, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import {
  AnalizKarti,
  Baslik,
  Durum,
  HaberKarti,
  PiyasaKarti,
  tarihTR,
} from "../../src/bilesen";
import { useTema } from "../../src/tema";
import { useVeri } from "../../src/veri";

export default function AnaSayfa() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;

  const p = useVeri(api.piyasa);
  const o = useVeri(api.oneCikan);
  const tl = useVeri(() => api.tel(12));

  const haberAc = (slug: string) => router.push(`/haber/${slug}`);
  const analizAc = (slug: string) => router.push(`/analiz/${slug}`);

  return (
    <ScrollView
      style={{ backgroundColor: t.renk.zemin }}
      contentContainerStyle={{ paddingBottom: alt + 28 }}
    >
      {/* ---- PIYASA OZETI ---- */}
      <Baslik
        metin="Piyasa özeti"
        alt={
          p.veri?.veri_tarihi
            ? `${tarihTR(p.veri.veri_tarihi)} verileri · gecikmeli`
            : undefined
        }
      />
      <Durum
        yukleniyor={p.yukleniyor}
        hata={p.hata}
        bos={!!p.veri && p.veri.kalemler.length === 0}
        bosMetin="Gösterge verisi bulunamadı."
        yenile={p.yenile}
      />
      {p.veri && p.veri.kalemler.length > 0 ? (
        <>
          <FlatList
            horizontal
            data={p.veri.kalemler}
            keyExtractor={(k) => k.kod}
            renderItem={({ item }) => <PiyasaKarti k={item} />}
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 16 }}
          />
          {/* LISANS ACIKLAMASI. Hisse endeksi neden yok -- okur
              gorsun. */}
          <Text style={[s.not, { color: t.renk.notr }]}>
            Hisse endeksleri (BIST 100, S&amp;P 500, Nasdaq, DAX) burada
            yer almıyor: bu endekslerin veri dağıtım lisansı Netaris'te
            değil. Eksik bir grup, lisanssız bir gruptan iyidir.
          </Text>
        </>
      ) : null}

      {/* ---- GUNUN ONEMLI GELISMELERI ---- */}
      <Baslik
        metin="Günün önemli gelişmeleri"
        alt={
          o.veri?.kaynak === "site"
            ? "Sitedeki öne çıkan seçimiyle aynı"
            : o.veri?.kaynak === "en-yeni"
              ? "En yeni yayınlar"
              : undefined
        }
      />
      <Durum
        yukleniyor={o.yukleniyor}
        hata={o.hata}
        bos={!!o.veri && o.veri.haberler.length === 0}
        yenile={o.yenile}
      />
      {o.veri?.haberler.map((h) => (
        <HaberKarti key={h.slug} h={h} bas={haberAc} />
      ))}

      {/* ---- CANLI TEL AKISI ---- */}
      <Baslik
        metin="Canlı akış"
        alt="Ajans başlıkları · on dakikada bir tazeleniyor"
      />
      <Durum
        yukleniyor={tl.yukleniyor}
        hata={tl.hata}
        bos={!!tl.veri && tl.veri.ogeler.length === 0}
        bosMetin="Akışta şu an öge yok."
        yenile={tl.yenile}
      />
      {tl.veri && tl.veri.ogeler.length > 0 ? (
        <View
          style={[
            s.akis,
            {
              backgroundColor: t.renk.panel,
              borderColor: t.renk.cizgi,
              borderRadius: t.r.orta,
            },
          ]}
        >
          {tl.veri.ogeler.map((oge, i) => (
            <View
              key={`${oge.adres}-${i}`}
              style={[
                s.akisOge,
                i > 0 ? { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.renk.cizgi } : null,
              ]}
            >
              <Text style={[s.akisSaat, { color: t.renk.vurgu }]}>
                {oge.tarih ? oge.tarih.slice(11, 16) : "—"}
              </Text>
              <View style={{ flex: 1, gap: 3 }}>
                <Text style={[s.akisBaslik, { color: t.renk.yazi }]}>
                  {oge.baslik}
                </Text>
                {/* TICARI KAYNAK ADI GORUNUR -- kisa iktibas hakkinin
                    sarti. */}
                <Text style={[s.akisKurum, { color: t.renk.notr }]}>
                  {oge.kurum_tam || oge.kurum}
                  {oge.cevrildi ? " · çeviri" : ""}
                </Text>
              </View>
            </View>
          ))}
        </View>
      ) : null}

      {/* ---- ONE CIKAN ARASTIRMALAR ---- */}
      <Baslik metin="Öne çıkan araştırmalar" />
      {o.veri?.analizler.length ? (
        o.veri.analizler.map((a) => (
          <AnalizKarti key={a.slug} a={a} bas={analizAc} />
        ))
      ) : (
        <Durum
          yukleniyor={o.yukleniyor}
          hata={o.hata}
          bos={!o.yukleniyor && !o.hata}
          bosMetin="Araştırma bulunamadı."
        />
      )}

      <Pressable
        onPress={() => router.push("/arastirma")}
        accessibilityRole="button"
        style={[s.tumu, { borderColor: t.renk.cizgiParlak }]}
      >
        <Text style={{ color: t.renk.vurgu, fontWeight: "600" }}>
          Tüm araştırmaları gör
        </Text>
      </Pressable>

      {o.veri?.uretildi ? (
        <Text style={[s.not, { color: t.renk.notr }]}>
          İçerik {o.veri.uretildi.slice(0, 10)} tarihinde üretildi.
        </Text>
      ) : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  not: {
    fontSize: 11,
    lineHeight: 16,
    marginHorizontal: 16,
    marginTop: 10,
    marginBottom: 2,
  },
  akis: {
    marginHorizontal: 16,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  akisOge: { flexDirection: "row", gap: 10, padding: 12 },
  akisSaat: { fontSize: 12, fontWeight: "700", width: 40 },
  akisBaslik: { fontSize: 14, lineHeight: 19 },
  akisKurum: { fontSize: 11 },
  tumu: {
    marginHorizontal: 16,
    marginTop: 8,
    paddingVertical: 13,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
});
