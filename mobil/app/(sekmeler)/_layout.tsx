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

import { Tabs } from "expo-router";
import React from "react";
import { ColorValue, Text } from "react-native";

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
    <Text style={{ color: renk, fontSize: 17, fontWeight: "700" }}>
      {metin}
    </Text>
  );
}

export default function SekmeYerlesimi() {
  const t = useTema();
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: t.renk.ustZemin },
        headerTintColor: t.renk.ustYazi,
        headerTitleStyle: { fontWeight: "700" },
        tabBarActiveTintColor: t.renk.vurgu,
        tabBarInactiveTintColor: t.renk.notr,
        tabBarStyle: {
          backgroundColor: t.renk.panel,
          borderTopColor: t.renk.cizgi,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
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
