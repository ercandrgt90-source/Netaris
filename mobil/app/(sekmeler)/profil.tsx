// PROFIL
//
// Oturum GERCEKTEN calisiyor: worker `Authorization: Bearer <jeton>`
// kabul ediyor ve `giris` cagrisi uygulamaya jetonu donduruyor.
// Jeton cihazin guvenli deposunda (`expo-secure-store`).
//
// MISAFIR KULLANIM ENGELLENMIYOR: icerigin tamami oturumsuz
// okunabiliyor, gereksiz giris duvari yok. Oturum yalnizca
// favoriler, kaydedilenler ve senaryo yazmak icin gerekiyor.
//
// HENUZ BAGLANMAYAN BOLUMLER ACIKCA LISTELENIYOR -- calismayan bir
// dugme koyup tamamlanmis izlenimi vermek yerine, neyin eksik
// oldugu ve neye bagli oldugu yazili.
//
// KLAVYE: form `KeyboardAvoidingView` icinde. Telefonda klavye
// acilinca gonder dugmesi klavyenin altinda kalirsa form
// kullanilamaz hale geliyor.

import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "../../src/api";
import { Baslik, Durum } from "../../src/bilesen";
import { useOturum } from "../../src/oturum";
import { useTema, useTemaTaze } from "../../src/tema";
import { useVeri } from "../../src/veri";

/** Henuz baglanmamis bolumler -- her biri neye bagli. */
const BEKLEYEN: { ad: string; aciklama: string }[] = [
  {
    ad: "Okuma geçmişi",
    aciklama: "Arka uç gerekiyor: okuma kaydı tutulmuyor",
  },
  {
    ad: "Bildirim tercihleri",
    aciklama: "Arka uç gerekiyor: cihaz tablosu ve gönderim işi henüz yok",
  },
  {
    ad: "Senaryo yazma",
    aciklama: "Uç hazır (/api/senaryo) · ekran bir sonraki sürümde",
  },
];

function GirisFormu() {
  const t = useTema();
  const { girisYap, hata } = useOturum();
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [gonderiliyor, setGonderiliyor] = useState(false);

  const gonder = async () => {
    if (!eposta.trim() || !parola) return;
    setGonderiliyor(true);
    await girisYap(eposta.trim(), parola);
    setGonderiliyor(false);
  };

  const girdi = {
    backgroundColor: t.renk.panel2,
    borderColor: t.renk.cizgi,
    color: t.renk.yazi,
    borderRadius: t.r.kucuk,
  };

  return (
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
      <Text style={[d.ad, { color: t.renk.yazi }]}>Giriş yap</Text>
      <Text style={[d.govde, { color: t.renk.yazi2 }]}>
        İçeriğin tamamı üyelik olmadan okunabilir. Giriş yalnızca
        favoriler, kaydedilenler ve senaryolar için gerekiyor.
      </Text>

      <TextInput
        value={eposta}
        onChangeText={setEposta}
        placeholder="E-posta"
        placeholderTextColor={t.renk.notr}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        // Turkce klavyede otomatik duzeltme e-postayi bozuyor.
        autoCorrect={false}
        style={[d.girdi, girdi]}
        accessibilityLabel="E-posta adresi"
      />
      <TextInput
        value={parola}
        onChangeText={setParola}
        placeholder="Parola"
        placeholderTextColor={t.renk.notr}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="current-password"
        onSubmitEditing={() => void gonder()}
        returnKeyType="go"
        style={[d.girdi, girdi]}
        accessibilityLabel="Parola"
      />

      {/* SUNUCUNUN KENDI MESAJI GOSTERILIYOR: "parola hatalı" ile
          "hesabınız doğrulanmadı" kullanici icin farkli iki durum. */}
      {hata ? (
        <Text style={[d.hata, { color: t.renk.azalis }]}>{hata}</Text>
      ) : null}

      <Pressable
        onPress={() => void gonder()}
        disabled={gonderiliyor || !eposta.trim() || !parola}
        accessibilityRole="button"
        style={({ pressed }) => [
          d.dugme,
          {
            backgroundColor:
              gonderiliyor || !eposta.trim() || !parola
                ? t.renk.notr
                : t.renk.vurgu,
            opacity: pressed ? 0.8 : 1,
          },
        ]}
      >
        {gonderiliyor ? (
          <ActivityIndicator color={t.renk.ustYazi} />
        ) : (
          <Text style={{ color: t.renk.ustYazi, fontWeight: "700" }}>
            Giriş yap
          </Text>
        )}
      </Pressable>

      {/* KAYIT VE GOOGLE GIRISI SITEDE. Google girisi uygulamada
          ayri bir yerel akis gerektiriyor (expo-auth-session) ve
          henuz kurulmadi; calismayan bir dugme koymak yerine
          calisan bir baglanti veriliyor. */}
      <Pressable
        onPress={() => Linking.openURL(api.webAdresi("/kayit/"))}
        accessibilityRole="link"
        style={{ paddingVertical: 12, minHeight: 44, justifyContent: "center" }}
      >
        <Text style={{ color: t.renk.vurgu, fontSize: 14 }}>
          Hesabın yok mu? Sitede üye ol
        </Text>
      </Pressable>
      <Text style={[d.ufak, { color: t.renk.notr }]}>
        Google ile giriş şimdilik sitede yapılabiliyor; uygulama içi
        Google akışı henüz kurulmadı.
      </Text>
    </View>
  );
}

function UyePaneli() {
  const t = useTema();
  const { uye, jeton, cikisYap } = useOturum();
  const b = useVeri(
    () => (jeton ? api.begenilerim(jeton) : Promise.resolve(null)),
    [jeton],
  );

  return (
    <>
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
        <Text style={[d.ad, { color: t.renk.yazi }]}>
          {uye?.ad || "Üye"}
        </Text>
        {uye?.eposta ? (
          <Text style={[d.ufak, { color: t.renk.yazi3 }]}>{uye.eposta}</Text>
        ) : null}

        {b.veri?.sayim ? (
          <View style={d.sayimSatiri}>
            {[
              ["Favori", b.veri.sayim.begeni],
              ["Yazı", b.veri.sayim.yazi],
              ["Senaryo", b.veri.sayim.senaryo],
              ["Aldığın oy", b.veri.sayim.oy],
            ].map(([ad, n]) => (
              <View key={String(ad)} style={{ alignItems: "center", gap: 2 }}>
                <Text style={[d.sayi, { color: t.renk.yazi }]}>{n}</Text>
                <Text style={[d.cokUfak, { color: t.renk.notr }]}>{ad}</Text>
              </View>
            ))}
          </View>
        ) : null}

        <Pressable
          onPress={() => void cikisYap()}
          accessibilityRole="button"
          style={[d.dugmeCerceve, { borderColor: t.renk.cizgiParlak }]}
        >
          <Text style={{ color: t.renk.yazi }}>Çıkış yap</Text>
        </Pressable>
      </View>

      <Baslik metin="Favorilerim" />
      <Durum
        yukleniyor={b.yukleniyor}
        hata={b.hata}
        bos={!!b.veri && b.veri.begeniler.length === 0}
        bosMetin="Henüz favori eklemedin."
        yenile={b.yenile}
      />
      {b.veri && b.veri.begeniler.length > 0 ? (
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
          {b.veri.begeniler.map((x, i) => (
            <Pressable
              key={`${x.yol}-${i}`}
              onPress={() => Linking.openURL(api.webAdresi(x.yol))}
              accessibilityRole="link"
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
              <Text style={[d.satirAd, { color: t.renk.yazi }]}>
                {/* BASLIK YOKSA YOL GOSTERILIYOR: eski kayitlarda
                    baslik saklanmamis olabilir ve bos satir
                    gostermek kaydi kaybetmek olurdu. */}
                {x.baslik || x.yol}
              </Text>
              {x.an ? (
                <Text style={[d.cokUfak, { color: t.renk.notr }]}>
                  {String(x.an).slice(0, 10)}
                </Text>
              ) : null}
            </Pressable>
          ))}
        </View>
      ) : null}
    </>
  );
}

export default function Profil() {
  const t = useTema();
  const taze = useTemaTaze();
  const alt = useSafeAreaInsets().bottom;
  const { uye, hazirlaniyor } = useOturum();

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        style={{ backgroundColor: t.renk.zemin }}
        contentContainerStyle={{ paddingBottom: alt + 28 }}
        keyboardShouldPersistTaps="handled"
      >
        <Baslik metin="Hesap" />

        {/* ILK OKUMA BITENE KADAR KARAR VERILMIYOR: depodaki jeton
            okunurken "giris yapilmamis" gostermek, giris yapmis
            kullaniciya bir an form gostermek olurdu. */}
        {hazirlaniyor ? (
          <Durum yukleniyor />
        ) : uye ? (
          <UyePaneli />
        ) : (
          <GirisFormu />
        )}

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
          {BEKLEYEN.map((x, i) => (
            <View
              key={x.ad}
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
              <Text style={[d.satirAd, { color: t.renk.yazi }]}>{x.ad}</Text>
              <Text style={[d.ufak, { color: t.renk.notr }]}>
                {x.aciklama}
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

        <Text style={[d.imza, { color: t.renk.notr }]}>
          Netaris mobil · sürüm 0.1.0{"\n"}
          Tema kaynağı: {taze ? "/v1/tema.json" : "uygulama içi yedek"}
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const d = StyleSheet.create({
  kart: {
    marginHorizontal: 16,
    padding: 15,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 10,
  },
  liste: {
    marginHorizontal: 16,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  satir: { paddingVertical: 13, paddingHorizontal: 14, gap: 3, minHeight: 48 },
  satirAd: { fontSize: 15, fontWeight: "600" },
  ad: { fontSize: 17, fontWeight: "700" },
  govde: { fontSize: 14, lineHeight: 20 },
  ufak: { fontSize: 12, lineHeight: 17 },
  cokUfak: { fontSize: 11 },
  hata: { fontSize: 13, lineHeight: 18 },
  girdi: {
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 13,
    // 48 piksel: dokunma hedefi esigi ve klavye acilinca rahat
    // secilebilir yukseklik.
    height: 48,
    fontSize: 15,
  },
  dugme: {
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
  },
  dugmeCerceve: {
    paddingVertical: 13,
    paddingHorizontal: 18,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  sayimSatiri: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 8,
  },
  sayi: { fontSize: 19, fontWeight: "700", fontVariant: ["tabular-nums"] },
  bag: {
    paddingVertical: 14,
    paddingHorizontal: 15,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 10,
    minHeight: 48,
    justifyContent: "center",
  },
  imza: { fontSize: 11, lineHeight: 16, textAlign: "center", marginTop: 26 },
});
