// KOK YERLESIM
//
// Tema saglayici en ustte: alt butun ekranlar paleti buradan aliyor.
// Guvenli ekran bolgeleri (centik, ev dugmesi serid) burada
// yonetiliyor -- her ekranda ayri ayri yonetmek, bir ekranda
// unutmak demekti.

import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { OturumSaglayici } from "../src/oturum";
import { TemaSaglayici, useTema } from "../src/tema";

function Yiginlar() {
  const t = useTema();
  return (
    <>
      {/* Durum cubugu yazisi temaya gore: koyu zeminde acik yazi.
          Sabit birakilsa koyu temada okunmaz oluyordu. */}
      <StatusBar style={t.ad === "koyu" ? "light" : "dark"} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: t.renk.ustZemin },
          headerTintColor: t.renk.ustYazi,
          headerTitleStyle: { fontWeight: "700" },
          contentStyle: { backgroundColor: t.renk.zemin },
        }}
      >
        <Stack.Screen name="(sekmeler)" options={{ headerShown: false }} />
        <Stack.Screen
          name="haber/[slug]"
          options={{ title: "Haber", headerBackTitle: "Geri" }}
        />
        <Stack.Screen
          name="analiz/[slug]"
          options={{ title: "Araştırma", headerBackTitle: "Geri" }}
        />
        <Stack.Screen
          name="takvim"
          options={{ title: "Ekonomik takvim", headerBackTitle: "Geri" }}
        />
      </Stack>
    </>
  );
}

export default function KokYerlesim() {
  return (
    <SafeAreaProvider>
      <TemaSaglayici>
        {/* Oturum TEMANIN ICINDE: oturum ekranlari da paleti
            kullaniyor ve tema once kurulmali. */}
        <OturumSaglayici>
          <Yiginlar />
        </OturumSaglayici>
      </TemaSaglayici>
    </SafeAreaProvider>
  );
}
