// SENARYO YAZMA
//
// CAPA ZORUNLU: bir senaryo neye dayandigini soylemeli. Bu yuzden
// ekran bir haber ya da varlik sayfasindan aciliyor ve capayi
// parametre olarak aliyor -- bos bir "senaryo yaz" dugmesi, neye
// bagli oldugu belirsiz metinler uretirdi.
//
// FORM KURALLARI BESLEMEDEN: gosterge listesi, ufuklar ve uzunluk
// sinirlari `/v1/senaryo-kurallari.json`dan okunuyor. Uygulamaya
// gommek, worker ve web formuyla UCUNCU bir kopya demekti -- ve
// ayrisma bir senaryonun SONUCLANIP sonuclanmayacagini degistirir.
//
// UZUNLUK SINIRI ONCEDEN UYGULANIYOR: kullanicinin 200 karakter
// yazip sunucudan hata almasi, 180'de uyarilmasindan kotu.
//
// OLCUT UCU BIRLIKTE: gosterge + yon + esik. Worker'in kendi notu
// bunu soyluyor -- "Yarim bir tetikleyici hic tetikleyici
// olmamasindan KOTUDUR". Ekran da ucunu birlikte zorunlu kiliyor.

import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
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
import { Durum } from "../src/bilesen";
import { useOturum } from "../src/oturum";
import { useTema } from "../src/tema";
import { useVeri } from "../src/veri";

function Alan({
  etiket,
  ipucu,
  deger,
  ayarla,
  enCok,
  enAz = 0,
  satirlar = 1,
}: {
  etiket: string;
  ipucu?: string;
  deger: string;
  ayarla: (s: string) => void;
  enCok: number;
  enAz?: number;
  satirlar?: number;
}) {
  const t = useTema();
  const kalan = enCok - deger.length;
  const kisa = enAz > 0 && deger.length > 0 && deger.length < enAz;
  return (
    <View style={{ gap: 6 }}>
      <Text style={[d.etiket, { color: t.renk.yazi }]}>{etiket}</Text>
      {ipucu ? (
        <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>{ipucu}</Text>
      ) : null}
      <TextInput
        value={deger}
        onChangeText={ayarla}
        multiline={satirlar > 1}
        // SINIR GIRDIDE UYGULANIYOR: sunucuya giden metin zaten
        // kirpilacak, ama kullanici yazdiginin kayboldugunu
        // GONDERDIKTEN SONRA ogrenmemeli.
        maxLength={enCok}
        style={[
          d.girdi,
          {
            backgroundColor: t.renk.panel2,
            borderColor: kisa ? t.renk.uyari : t.renk.cizgi,
            color: t.renk.yazi,
            borderRadius: t.r.kucuk,
            minHeight: satirlar > 1 ? 24 * satirlar + 20 : 48,
            textAlignVertical: satirlar > 1 ? "top" : "center",
          },
        ]}
        accessibilityLabel={etiket}
      />
      <View style={d.satir}>
        {kisa ? (
          <Text style={[d.ipucu, { color: t.renk.uyari }]}>
            en az {enAz} karakter
          </Text>
        ) : null}
        <View style={{ flex: 1 }} />
        <Text
          style={[
            d.ipucu,
            { color: kalan < 20 ? t.renk.uyari : t.renk.notr },
          ]}
        >
          {kalan}
        </Text>
      </View>
    </View>
  );
}

function Secim({
  etiket,
  secenekler,
  secili,
  sec,
}: {
  etiket: string;
  secenekler: { kod: string; ad: string }[];
  secili: string;
  sec: (k: string) => void;
}) {
  const t = useTema();
  return (
    <View style={{ gap: 6 }}>
      <Text style={[d.etiket, { color: t.renk.yazi }]}>{etiket}</Text>
      <View style={d.cipler}>
        {secenekler.map((s) => {
          const aktif = s.kod === secili;
          return (
            <Pressable
              key={s.kod}
              onPress={() => sec(aktif ? "" : s.kod)}
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
                {s.ad}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export default function SenaryoYaz() {
  const { capa, capa_baslik, capa_tur } = useLocalSearchParams<{
    capa: string;
    capa_baslik?: string;
    capa_tur?: string;
  }>();
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  const { jeton, uye } = useOturum();
  const k = useVeri(api.senaryoKurallari, [], "/v1/senaryo-kurallari.json");

  const [kosul, setKosul] = useState("");
  const [sonuc, setSonuc] = useState("");
  const [gerekce, setGerekce] = useState("");
  const [curutme, setCurutme] = useState("");
  const [kaynaklar, setKaynaklar] = useState("");
  const [ufuk, setUfuk] = useState("3 ay");
  const [olcutKod, setOlcutKod] = useState("");
  const [olcutYon, setOlcutYon] = useState("");
  const [olcutEsik, setOlcutEsik] = useState("");
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [bitti, setBitti] = useState<string | null>(null);

  const s = k.veri?.sinirlar;
  const enAz = s?.kosul?.en_az ?? 12;

  // OLCUT YA TAM YA HIC. Worker ucu birlikte istiyor; yarim
  // tetikleyici senaryoyu "belirsiz"e mahkum eder.
  const olcutYarim = useMemo(() => {
    const dolu = [olcutKod, olcutYon, olcutEsik.trim()].filter(Boolean).length;
    return dolu > 0 && dolu < 3;
  }, [olcutKod, olcutYon, olcutEsik]);

  const gecerli =
    kosul.trim().length >= enAz &&
    sonuc.trim().length >= enAz &&
    !!capa &&
    !olcutYarim;

  const kaydet = async (gonder: boolean) => {
    if (!jeton || !gecerli) return;
    setGonderiliyor(true);
    setHata(null);
    try {
      const c = await api.senaryoKaydet(jeton, {
        kosul: kosul.trim(),
        sonuc: sonuc.trim(),
        gerekce: gerekce.trim(),
        curutme: curutme.trim(),
        kaynaklar: kaynaklar.trim(),
        capa: String(capa),
        capa_baslik: capa_baslik ? String(capa_baslik) : "",
        capa_tur: (capa_tur as "haber" | "varlik" | "konu") || "haber",
        ufuk,
        olcut_kod: olcutKod,
        olcut_yon: olcutYon,
        olcut_esik: olcutEsik.trim(),
        gonder,
      });
      if (!c.tamam) {
        setHata("Kaydedilemedi.");
      } else {
        setBitti(
          gonder
            ? "Senaryon incelemeye gönderildi. Yayımlanınca Senaryolar " +
                "bölümünde görünecek."
            : "Taslak olarak kaydedildi.",
        );
      }
    } catch (h) {
      // SUNUCUNUN KENDI MESAJI KORUNUYOR: "Koşul en az 12 karakter"
      // ile "Senaryo bir habere bağlı olmalı" ayrı sorunlar.
      setHata(h instanceof Error ? h.message : "Kaydedilemedi.");
    } finally {
      setGonderiliyor(false);
    }
  };

  // --- OTURUM YOKSA ---
  if (!uye) {
    return (
      <>
        <Stack.Screen options={{ title: "Senaryo yaz" }} />
        <View style={[d.orta, { backgroundColor: t.renk.zemin }]}>
          <Text style={[d.baslik, { color: t.renk.yazi }]}>
            Senaryo yazmak için giriş gerekiyor
          </Text>
          <Text style={[d.ipucu, { color: t.renk.yazi2, textAlign: "center" }]}>
            İçeriğin tamamı üyelik olmadan okunabilir; yazmak için
            hesap gerekiyor.
          </Text>
          <Pressable
            onPress={() => router.push("/profil")}
            accessibilityRole="button"
            style={[d.dugme, { backgroundColor: t.renk.vurgu }]}
          >
            <Text style={{ color: t.renk.ustYazi, fontWeight: "700" }}>
              Profile git
            </Text>
          </Pressable>
        </View>
      </>
    );
  }

  // --- KAYDEDILDI ---
  if (bitti) {
    return (
      <>
        <Stack.Screen options={{ title: "Senaryo yaz" }} />
        <View style={[d.orta, { backgroundColor: t.renk.zemin }]}>
          <Text style={[d.baslik, { color: t.renk.yazi }]}>Kaydedildi</Text>
          <Text style={[d.ipucu, { color: t.renk.yazi2, textAlign: "center" }]}>
            {bitti}
          </Text>
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            style={[d.dugme, { backgroundColor: t.renk.vurgu }]}
          >
            <Text style={{ color: t.renk.ustYazi, fontWeight: "700" }}>
              Geri dön
            </Text>
          </Pressable>
        </View>
      </>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: "Senaryo yaz" }} />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          style={{ backgroundColor: t.renk.zemin }}
          contentContainerStyle={{
            padding: 16,
            paddingBottom: alt + 40,
            gap: 18,
          }}
          keyboardShouldPersistTaps="handled"
        >
          <Durum yukleniyor={k.yukleniyor} hata={k.engelleyenHata} yenile={k.yenile} />

          {k.veri ? (
            <>
              {/* CAPA: senaryo neye dayaniyor. */}
              <View
                style={[
                  d.capa,
                  {
                    backgroundColor: t.renk.panel2,
                    borderColor: t.renk.cizgi,
                    borderRadius: t.r.kucuk,
                  },
                ]}
              >
                <Text style={[d.ipucu, { color: t.renk.notr }]}>
                  DAYANDIĞI GELİŞME
                </Text>
                <Text style={[d.capaBaslik, { color: t.renk.yazi }]}>
                  {capa_baslik || capa}
                </Text>
              </View>

              <Alan
                etiket="Koşul"
                ipucu="Hangi gelişme gerçekleşirse? Örnek: “Gıda kaynaklı düşüş çekirdeğe yayılırsa”"
                deger={kosul}
                ayarla={setKosul}
                enAz={s?.kosul?.en_az ?? 12}
                enCok={s?.kosul?.en_cok ?? 180}
                satirlar={3}
              />

              <Alan
                etiket="Beklenen sonuç"
                ipucu="O zaman ne beklersiniz? Hangi piyasa ya da varlık etkilenir?"
                deger={sonuc}
                ayarla={setSonuc}
                enAz={s?.sonuc?.en_az ?? 12}
                enCok={s?.sonuc?.en_cok ?? 180}
                satirlar={3}
              />

              <Alan
                etiket="Gerekçe (isteğe bağlı)"
                ipucu="Neden böyle düşünüyorsunuz?"
                deger={gerekce}
                ayarla={setGerekce}
                enCok={s?.gerekce?.en_cok ?? 1200}
                satirlar={5}
              />

              {/* CURUTME KOSULU -- aciklamasi BESLEMEDEN geliyor. */}
              <Alan
                etiket="Çürütme koşulu (isteğe bağlı)"
                ipucu={k.veri.notlar.curutme}
                deger={curutme}
                ayarla={setCurutme}
                enCok={s?.curutme?.en_cok ?? 220}
                satirlar={3}
              />

              <Alan
                etiket="Kaynaklar (isteğe bağlı)"
                deger={kaynaklar}
                ayarla={setKaynaklar}
                enCok={s?.kaynaklar?.en_cok ?? 500}
                satirlar={3}
              />

              <Secim
                etiket="Değerlendirme ufku"
                secenekler={k.veri.ufuklar.map((u) => ({ kod: u, ad: u }))}
                secili={ufuk}
                sec={(x) => setUfuk(x || "3 ay")}
              />

              {/* OLCULEBILIR TETIKLEYICI */}
              <View
                style={[
                  d.bolum,
                  {
                    backgroundColor: t.renk.panel,
                    borderColor: olcutYarim ? t.renk.uyari : t.renk.cizgi,
                    borderRadius: t.r.orta,
                  },
                ]}
              >
                <Text style={[d.etiket, { color: t.renk.yazi }]}>
                  Ölçülebilir tetikleyici (isteğe bağlı)
                </Text>
                <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>
                  {k.veri.notlar.olcut}
                </Text>

                <Secim
                  etiket="Gösterge"
                  secenekler={k.veri.olcutler}
                  secili={olcutKod}
                  sec={setOlcutKod}
                />
                <Secim
                  etiket="Yön"
                  secenekler={k.veri.yonler}
                  secili={olcutYon}
                  sec={setOlcutYon}
                />
                <Alan
                  etiket="Eşik"
                  ipucu="Sayı yazın. Örnek: 30"
                  deger={olcutEsik}
                  ayarla={setOlcutEsik}
                  enCok={24}
                />

                {/* YARIM TETIKLEYICI UYARISI: worker'in kendi notu
                    "yarim bir tetikleyici hic tetikleyici
                    olmamasindan KOTUDUR" diyor. */}
                {olcutYarim ? (
                  <Text style={[d.ipucu, { color: t.renk.uyari }]}>
                    Üçü birlikte gerekli: gösterge, yön ve eşik.
                    Yarım bırakılırsa tetikleyici hiç kaydedilmez ve
                    senaryo ufku dolunca “belirsiz” olarak kapanır.
                  </Text>
                ) : null}
              </View>

              {hata ? (
                <Text style={[d.hata, { color: t.renk.azalis }]}>{hata}</Text>
              ) : null}

              <View style={{ gap: 10 }}>
                <Pressable
                  onPress={() => void kaydet(true)}
                  disabled={!gecerli || gonderiliyor}
                  accessibilityRole="button"
                  style={[
                    d.dugme,
                    {
                      backgroundColor:
                        gecerli && !gonderiliyor ? t.renk.vurgu : t.renk.notr,
                    },
                  ]}
                >
                  {gonderiliyor ? (
                    <ActivityIndicator color={t.renk.ustYazi} />
                  ) : (
                    <Text
                      style={{ color: t.renk.ustYazi, fontWeight: "700" }}
                    >
                      İncelemeye gönder
                    </Text>
                  )}
                </Pressable>

                <Pressable
                  onPress={() => void kaydet(false)}
                  disabled={!gecerli || gonderiliyor}
                  accessibilityRole="button"
                  style={[d.dugmeCerceve, { borderColor: t.renk.cizgiParlak }]}
                >
                  <Text style={{ color: t.renk.yazi }}>
                    Taslak olarak kaydet
                  </Text>
                </Pressable>
              </View>

              <Text style={[d.ipucu, { color: t.renk.notr }]}>
                Senaryolar kesin öngörü ya da getiri vaadi değildir.
                Yayımlanan senaryolar üye içeriğidir ve Netaris'in
                editoryal içeriğinden ayrı gösterilir.
              </Text>
            </>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

const d = StyleSheet.create({
  orta: { flex: 1, padding: 28, alignItems: "center", justifyContent: "center", gap: 14 },
  baslik: { fontSize: 19, fontWeight: "700", textAlign: "center" },
  etiket: { fontSize: 15, fontWeight: "700" },
  ipucu: { fontSize: 12, lineHeight: 17 },
  hata: { fontSize: 13, lineHeight: 18 },
  girdi: {
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 13,
    paddingVertical: 10,
    fontSize: 15,
    lineHeight: 21,
  },
  satir: { flexDirection: "row", alignItems: "center", gap: 8 },
  capa: { padding: 12, borderWidth: StyleSheet.hairlineWidth, gap: 4 },
  capaBaslik: { fontSize: 14, fontWeight: "600", lineHeight: 20 },
  bolum: { padding: 14, borderWidth: StyleSheet.hairlineWidth, gap: 12 },
  cipler: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  cip: {
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 40,
    justifyContent: "center",
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
