// ALT GEZINME -- BES BOLUM
//
// Sartname en fazla bes ana bolum istiyor:
//   Ana Sayfa · Piyasalar · Araştırma · Senaryolar · Profil
//
// Haberler, ekonomik takvim, sirket arama ve favoriler bu bes
// ekranin icinden ya da duzenli bir ikincil menuden aciliyor; alt
// serit kalabaliklasmiyor.
//
// IKON METIN YERINE SEMBOL DEGIL, IKISI BIRLIKTE: yalnizca ikon
// kullanmak Turkce bir finans uygulamasinda tahmine dayali gezinme
// uretir. Etiketler acik yazili.

import { Tabs, useRouter } from "expo-router";
import React from "react";
import { ColorValue, Pressable, Text } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useTema } from "../../src/tema";

/**
 * Sekme simgesi.
 *
 * Simdilik tipografik: ikon kutuphanesi eklemek ek paket ve ek
 * boyut demek, ve marka ikon seti henuz tasarlanmadi. Erisilebilirlik
 * icin etiketler zaten yazili; simge ikincil bir isaret.
 */
function Simge({
  metin,
  renk,
}: {
  metin: string;
  // `ColorValue`, `string` DEGIL: gezinme kutuphanesi aktif/pasif
  // rengi bu turde veriyor ve null olabiliyor.
  renk: ColorValue;
}) {
  return (
    <Text style={{ color: renk, fontSize: 15, lineHeight: 20,
                   fontWeight: "700" }}>
      {metin}
    </Text>
  );
}

export default function SekmeYerlesimi() {
  const t = useTema();
  const router = useRouter();
  const alt = useSafeAreaInsets().bottom;
  return (
    <Tabs
      screenOptions={{
        // ARAMA HER SEKMEDE ULASILABILIR: sartname "uygulama
        // genelinde arama" istiyor ve alt seritte yer yok (en
        // fazla bes bolum). Baslik dugmesi her ekranda duruyor.
        headerRight: () => (
          <Pressable
            onPress={() => router.push("/ara")}
            accessibilityRole="button"
            accessibilityLabel="Ara"
            hitSlop={10}
            style={{ paddingHorizontal: 16, minHeight: 44,
                     justifyContent: "center" }}
          >
            <Text style={{ color: t.renk.ustYazi, fontSize: 17 }}>⌕</Text>
          </Pressable>
        ),
        headerStyle: { backgroundColor: t.renk.ustZemin },
        headerTintColor: t.renk.ustYazi,
        headerTitleStyle: { fontWeight: "700" },
        tabBarActiveTintColor: t.renk.vurgu,
        tabBarInactiveTintColor: t.renk.notr,
        // SERIT YUKSEKLIGI ACIKCA VERILIYOR -- OLCULDU.
        //
        // Gercek tarayicida (390x844, 2x) olculdu: varsayilan
        // serit 48 piksel ve icinde 17 piksellik simge + 15
        // piksellik etiket sigmiyordu. Etiket kutusuna 10, sonra
        // 2 piksel kaliyordu; bes sekmenin BESINDE de yazi
        // alttan kesiliyordu.
        //
        // GUVENLI ALAN EKLENIYOR: ev gostergesi olan cihazlarda
        // serit onun altinda kalirdi. Yukseklik SABIT verilince
        // React Navigation kendi payini eklemiyor, bu yuzden
        // insed elle toplanıyor. Web'de `alt` sifir.
        tabBarStyle: {
          backgroundColor: t.renk.panel,
          borderTopColor: t.renk.cizgi,
          height: 58 + alt,
          paddingBottom: alt + 6,
          paddingTop: 6,
        },
        // Simge ile etiket arasini daraltiyor; ikisi 46 piksellik
        // ic alana birlikte sigmali.
        tabBarIconStyle: { height: 20, marginBottom: 1 },
        // `lineHeight` ZORUNLU -- olculdu, yoksa ETIKET KIRPILIYOR.
        //
        // Gercek tarayicida olculdu (390x844, 2x): etiket kutusu 10
        // piksel, metnin gerektirdigi 15 piksel. Bes sekmenin
        // BESINDE de "Ana Sayfa", "Piyasalar", "Araştırma",
        // "Senaryolar", "Profil" yazilari alttan kesiliyordu.
        //
        // `fontSize` verilip `lineHeight` verilmeyince satir kutusu
        // yazi tipinin varsayilanina kaliyor ve Turkce'deki
        // alt uzantilar (ş, ç) ile buyuk harfler sigmiyor.
        tabBarLabelStyle: { fontSize: 11, lineHeight: 15,
                            fontWeight: "600" },
        sceneStyle: { backgroundColor: t.renk.zemin },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Netaris",
          tabBarLabel: "Ana Sayfa",
          tabBarIcon: ({ color }) => <Simge metin="◆" renk={color} />,
        }}
      />
      <Tabs.Screen
        name="piyasalar"
        options={{
          title: "Piyasalar",
          tabBarIcon: ({ color }) => <Simge metin="▦" renk={color} />,
        }}
      />
      <Tabs.Screen
        name="arastirma"
        options={{
          title: "Araştırma",
          tabBarIcon: ({ color }) => <Simge metin="▤" renk={color} />,
        }}
      />
      <Tabs.Screen
        name="senaryolar"
        options={{
          title: "Senaryolar",
          tabBarIcon: ({ color }) => <Simge metin="◇" renk={color} />,
        }}
      />
      <Tabs.Screen
        name="profil"
        options={{
          title: "Profil",
          tabBarIcon: ({ color }) => <Simge metin="●" renk={color} />,
        }}
      />
    </Tabs>
  );
}
