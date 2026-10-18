// HESABI SIL
//
// Google Play, hesap olusturulabilen her uygulamada UYGULAMA
// ICINDEN erisilebilen bir hesap silme yolu istiyor. E-posta ile
// talep o sartı karsilamiyor.
//
// NE SILINECEGI ONCEDEN, EKSIKSIZ YAZILI.
// "Hesabiniz silinecek" demek yetmez: okur senaryolarinin ve
// yazilarinin da gidecegini SONRADAN ogrenmemeli. Gizlilik
// beyaniyla birebir ayni liste basiliyor.
//
// GERI ALINAMAZ VE OYLE SOYLENIYOR. Islem tek dokunusla degil,
// kimlik dogrulamasi + ayri bir onay dugmesiyle yapiliyor.
//
// IKI KIMLIK YOLU: parolali hesapta parola, Google ile acilmis
// hesapta onay metni (orada parola YOK).

import { Stack, useRouter } from "expo-router";
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

import * as api from "../src/api";
import { useOturum } from "../src/oturum";
import { useTema } from "../src/tema";

const ONAY_METNI = "HESABIMI SIL";

/** Silinecekler — gizlilik beyanıyla birebir aynı liste. */
const SILINECEKLER = [
  "Hesap kaydınız (e-posta, ad, soyad, unvan, kısa özgeçmiş, profil fotoğrafı)",
  "Açık oturumlarınız",
  "Favorileriniz",
  "Yazdığınız senaryolar — yayımlanmış olanlar dahil",
  "Senaryolara verdiğiniz oylar",
  "Gönderdiğiniz yazılar",
];

export default function HesapSil() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const { jeton, uye, cikisYap } = useOturum();

  const [parola, setParola] = useState("");
  const [onay, setOnay] = useState("");
  const [calisiyor, setCalisiyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [bitti, setBitti] = useState(false);

  // GOOGLE HESABINI AYIRT EDEMIYORUZ -- ve bu bilincli.
  //
  // `/api/ben` parola olup olmadigini bildirmiyor. Her iki alani da
  // gostermek yerine, kullanici hangisini doldurursa o gonderiliyor;
  // sunucu dogru olani dogruluyor ve yanlissa KENDI mesajini veriyor
  // ("Parola yanlış." ya da "Onaylamak için ... yazın.").
  //
  // Tahmin etmek yerine sunucunun cevabina guvenmek, iki yerde iki
  // ayri kural tutmaktan iyi.
  const hazir = parola.length > 0 ||
    onay.trim().toLocaleUpperCase("tr") === ONAY_METNI;

  const sil = async () => {
    if (!jeton || !hazir) return;
    setCalisiyor(true);
    setHata(null);
    try {
      await api.hesapSil(jeton, {
        parola: parola || undefined,
        onay: onay.trim() || undefined,
      });
      setBitti(true);
      // Yerel oturum da temizleniyor; sunucu jetonu zaten sildi.
      await cikisYap();
    } catch (h) {
      setHata(h instanceof Error ? h.message : "Silinemedi.");
    } finally {
      setCalisiyor(false);
    }
  };

  if (bitti) {
    return (
      <>
        <Stack.Screen options={{ title: "Hesap silindi" }} />
        <View style={[d.orta, { backgroundColor: t.renk.zemin }]}>
          <Text style={[d.baslik, { color: t.renk.yazi }]}>
            Hesabınız silindi
          </Text>
          <Text
            style={[d.govde, { color: t.renk.yazi2, textAlign: "center" }]}
          >
            Hesap kaydınız ve ona bağlı veriler kaldırıldı. İçeriğin
            tamamı üyelik olmadan okunmaya devam ediyor.
          </Text>
          <Pressable
            onPress={() => router.replace("/")}
            accessibilityRole="button"
            style={[d.dugme, { backgroundColor: t.renk.vurgu }]}
          >
            <Text style={{ color: t.renk.ustYazi, fontWeight: "700" }}>
              Ana sayfaya dön
            </Text>
          </Pressable>
        </View>
      </>
    );
  }

  if (!uye) {
    return (
      <>
        <Stack.Screen options={{ title: "Hesabı sil" }} />
        <View style={[d.orta, { backgroundColor: t.renk.zemin }]}>
          <Text style={[d.govde, { color: t.renk.yazi2 }]}>
            Bu işlem için giriş yapmış olmanız gerekiyor.
          </Text>
        </View>
      </>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: "Hesabı sil" }} />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          style={{ backgroundColor: t.renk.zemin }}
          contentContainerStyle={{
            padding: 16,
            paddingBottom: alt + 40,
            gap: 16,
          }}
          keyboardShouldPersistTaps="handled"
        >
          <View
            style={[
              d.uyari,
              {
                backgroundColor: t.renk.panel,
                borderColor: t.renk.azalis,
                borderRadius: t.r.orta,
              },
            ]}
          >
            <Text style={[d.uyariBaslik, { color: t.renk.azalis }]}>
              Bu işlem geri alınamaz
            </Text>
            <Text style={[d.govde, { color: t.renk.yazi2 }]}>
              Aşağıdakiler kalıcı olarak silinir:
            </Text>
            {SILINECEKLER.map((x) => (
              <Text key={x} style={[d.madde, { color: t.renk.yazi2 }]}>
                •  {x}
              </Text>
            ))}
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              Okuma için üyelik gerekmiyor; silme sonrası içeriğe
              erişiminiz sürer.
            </Text>
          </View>

          {/* VERIYI ONCE DISA AKTARMA SECENEGI: silmeden once
              kopyasini almak isteyen okur icin. Silme dugmesinin
              yanina koymak, "once bir dusun" demenin en somut
              bicimi. */}
          <Pressable
            onPress={() => Linking.openURL(api.webAdresi("/panel/"))}
            accessibilityRole="link"
            style={[d.dugmeCerceve, { borderColor: t.renk.cizgiParlak }]}
          >
            <Text style={{ color: t.renk.yazi }}>
              Önce verilerimi dışa aktarayım
            </Text>
          </Pressable>

          <View style={{ gap: 8 }}>
            <Text style={[d.etiket, { color: t.renk.yazi }]}>
              Parolanız
            </Text>
            <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
              Hesabınız Google ile açıldıysa boş bırakın ve alttaki
              onay kutusunu doldurun.
            </Text>
            <TextInput
              value={parola}
              onChangeText={setParola}
              placeholder="Parola"
              placeholderTextColor={t.renk.notr}
              secureTextEntry
              autoCapitalize="none"
              style={[
                d.girdi,
                {
                  backgroundColor: t.renk.panel2,
                  borderColor: t.renk.cizgi,
                  color: t.renk.yazi,
                  borderRadius: t.r.kucuk,
                },
              ]}
              accessibilityLabel="Parola"
            />
          </View>

          <View style={{ gap: 8 }}>
            <Text style={[d.etiket, { color: t.renk.yazi }]}>
              Google ile açılmış hesaplar için onay
            </Text>
            <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
              Onaylamak için “{ONAY_METNI}” yazın.
            </Text>
            <TextInput
              value={onay}
              onChangeText={setOnay}
              placeholder={ONAY_METNI}
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
              accessibilityLabel="Silme onayı"
            />
          </View>

          {hata ? (
            <Text style={[d.hataYazi, { color: t.renk.azalis }]}>{hata}</Text>
          ) : null}

          <Pressable
            onPress={() => void sil()}
            disabled={!hazir || calisiyor}
            accessibilityRole="button"
            style={[
              d.dugme,
              {
                backgroundColor:
                  hazir && !calisiyor ? t.renk.azalis : t.renk.notr,
              },
            ]}
          >
            {calisiyor ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={{ color: "#fff", fontWeight: "700" }}>
                Hesabımı kalıcı olarak sil
              </Text>
            )}
          </Pressable>

          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            style={[d.dugmeCerceve, { borderColor: t.renk.cizgiParlak }]}
          >
            <Text style={{ color: t.renk.yazi }}>Vazgeç</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

const d = StyleSheet.create({
  orta: { flex: 1, padding: 28, alignItems: "center", justifyContent: "center", gap: 14 },
  baslik: { fontSize: 19, fontWeight: "700", textAlign: "center" },
  uyari: { padding: 15, borderWidth: 1, gap: 7 },
  uyariBaslik: { fontSize: 16, fontWeight: "700" },
  madde: { fontSize: 14, lineHeight: 21 },
  govde: { fontSize: 14, lineHeight: 21 },
  ufak: { fontSize: 12, lineHeight: 17 },
  etiket: { fontSize: 15, fontWeight: "700" },
  hataYazi: { fontSize: 13, lineHeight: 18 },
  girdi: {
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 13,
    height: 48,
    fontSize: 15,
  },
  dugme: {
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 50,
    paddingHorizontal: 22,
  },
  dugmeCerceve: {
    paddingVertical: 13,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    minHeight: 46,
    justifyContent: "center",
  },
});
