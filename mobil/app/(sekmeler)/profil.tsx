// PROFIL
//
// BU EKRAN BUGUN NE YAPIYOR, NE YAPMIYOR -- acikca yazili.
//
// Site oturumu HttpOnly cerezle tasiniyor (`worker.js:323`). Yerel
// uygulamada cerez yonetimi platforma bagli ve kirilgan: iOS ve
// Android cerez depolari farkli davraniyor, uygulama
// guncellemelerinde temizlenebiliyor. Dogru cozum worker'a
// `Authorization: Bearer <jeton>` destegi eklemek ve bu Faz 3c'de
// planli.
//
// BU YUZDEN BURADA SAHTE BIR GIRIS FORMU YOK. Calismayan bir form
// koymak "tamamlandi" izlenimi vermek olurdu. Onun yerine:
//
// * `/api/ben` GERCEKTEN cagriliyor -- cerez varsa (ornegin web
//   gorunumunden donen bir oturum) uye bilgisi gosteriliyor.
// * Yoksa misafir hali ve eksik olanin NE oldugu yaziliyor.
// * Giris sitede yapilabiliyor ve baglanti calisiyor.
//
// Misafir kullanim engellenmiyor: icerigin tamami oturumsuz
// okunabiliyor, gereksiz giris duvari konmuyor.

import React from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Baslik, Durum } from "../../src/bilesen";
import { useTema, useTemaTaze } from "../../src/tema";
import { useVeri } from "../../src/veri";

/** Henuz baglanmamis bolumler -- her biri hangi faza bagli. */
const BEKLEYEN: { ad: string; aciklama: string }[] = [
  {
    ad: "Favori şirketler ve varlıklar",
    aciklama: "Oturum gerekiyor · /api/begeni ucu hazır",
  },
  {
    ad: "Kaydedilmiş araştırmalar",
    aciklama: "Oturum gerekiyor · /api/begenilerim ucu hazır",
  },
  {
    ad: "Senaryolarım",
    aciklama: "Oturum gerekiyor · /api/senaryo ucu hazır",
  },
  {
    ad: "Bildirim tercihleri",
    aciklama: "Arka uç gerekiyor: cihaz tablosu ve gönderim işi henüz yok",
  },
];

export default function Profil() {
  const t = useTema();
  const taze = useTemaTaze();
  const alt = useSafeAreaInsets().bottom;
  const u = useVeri(() => api.ben());

  return (
    <ScrollView
      style={{ backgroundColor: t.renk.zemin }}
      contentContainerStyle={{ paddingBottom: alt + 28 }}
    >
      <Baslik metin="Hesap" />
      <Durum yukleniyor={u.yukleniyor} hata={u.hata} yenile={u.yenile} />

      {!u.yukleniyor && !u.hata ? (
        <View
          style={[
            d.kart,
            {
              backgroundColor: t.renk.panel,
              borderColor: t.renk.cizgi,
              borderRadius: t.r.orta,
            },
          ]}
        >
          {u.veri ? (
            <>
              <Text style={[d.ad, { color: t.renk.yazi }]}>
                {u.veri.ad || "Üye"}
              </Text>
              {u.veri.eposta ? (
                <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
                  {u.veri.eposta}
                </Text>
              ) : null}
            </>
          ) : (
            <>
              <Text style={[d.ad, { color: t.renk.yazi }]}>
                Misafir olarak geziniyorsunuz
              </Text>
              <Text style={[d.govde, { color: t.renk.yazi2 }]}>
                İçeriğin tamamı üyelik olmadan okunabilir. Favoriler,
                kaydedilen araştırmalar ve senaryo oluşturma üyelik
                gerektiriyor.
              </Text>
              {/* DURUST ACIKLAMA: uygulama ici giris henuz YOK ve
                  sebebi teknik. Gizlemek yerine yaziyoruz. */}
              <Text style={[d.ufak, { color: t.renk.uyari }]}>
                Uygulama içi giriş henüz açık değil: site oturumu
                HttpOnly çerezle taşınıyor ve uygulama için jeton
                tabanlı oturum desteği gerekiyor. Şimdilik giriş sitede
                yapılabiliyor.
              </Text>
              <Pressable
                onPress={() => Linking.openURL(api.webAdresi("/giris/"))}
                accessibilityRole="link"
                style={[d.dugme, { borderColor: t.renk.vurgu }]}
              >
                <Text style={{ color: t.renk.vurgu, fontWeight: "600" }}>
                  Sitede giriş yap
                </Text>
              </Pressable>
            </>
          )}
        </View>
      ) : null}

      <Baslik
        metin="Henüz bağlanmayan bölümler"
        alt="Hangi uç hazır, hangisi arka uç bekliyor"
      />
      <View
        style={[
          d.liste,
          {
            backgroundColor: t.renk.panel,
            borderColor: t.renk.cizgi,
            borderRadius: t.r.orta,
          },
        ]}
      >
        {BEKLEYEN.map((b, i) => (
          <View
            key={b.ad}
            style={[
              d.satir,
              i > 0
                ? {
                    borderTopWidth: StyleSheet.hairlineWidth,
                    borderTopColor: t.renk.cizgi,
                  }
                : null,
            ]}
          >
            <Text style={[d.satirAd, { color: t.renk.yazi }]}>{b.ad}</Text>
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              {b.aciklama}
            </Text>
          </View>
        ))}
      </View>

      <Baslik metin="Gizlilik ve veri" />
      <View style={{ paddingHorizontal: 16, gap: 10 }}>
        {[
          ["Gizlilik politikası", "/gizlilik/"],
          ["Yayın ilkeleri", "/yayin-ilkeleri/"],
          ["Künye", "/kunye/"],
          ["Metodoloji", "/metodoloji/"],
        ].map(([ad, yol]) => (
          <Pressable
            key={yol}
            onPress={() => Linking.openURL(api.webAdresi(yol))}
            accessibilityRole="link"
            style={[d.bag, { borderColor: t.renk.cizgi }]}
          >
            <Text style={{ color: t.renk.yazi, fontSize: 15 }}>{ad}</Text>
          </Pressable>
        ))}
      </View>

      {/* GELISTIRICI BILGISI: tema uzaktan mi geldi. Palet ayrisirsa
          nereden geldigini bilmek gerekiyor. */}
      <Text style={[d.imza, { color: t.renk.notr }]}>
        Netaris mobil · sürüm 0.1.0{"\n"}
        Tema kaynağı: {taze ? "/v1/tema.json" : "uygulama içi yedek"}
      </Text>
    </ScrollView>
  );
}

const d = StyleSheet.create({
  kart: {
    marginHorizontal: 16,
    padding: 15,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 8,
  },
  liste: {
    marginHorizontal: 16,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  satir: { paddingVertical: 13, paddingHorizontal: 14, gap: 3 },
  satirAd: { fontSize: 15, fontWeight: "600" },
  ad: { fontSize: 17, fontWeight: "700" },
  govde: { fontSize: 14, lineHeight: 20 },
  ufak: { fontSize: 12, lineHeight: 17 },
  dugme: {
    marginTop: 6,
    paddingVertical: 13,
    paddingHorizontal: 18,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  bag: {
    paddingVertical: 14,
    paddingHorizontal: 15,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 10,
    minHeight: 48,
    justifyContent: "center",
  },
  imza: {
    fontSize: 11,
    lineHeight: 16,
    textAlign: "center",
    marginTop: 26,
  },
});
