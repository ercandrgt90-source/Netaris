// PAYLASILAN BILESENLER
//
// BURADAKI KURALLAR OKURA DONUK, SUS DEGIL:
//
// * `Durum` dort ayri hali ayirir: yukleniyor / hata / bos / dolu.
//   Bir finans uygulamasinda bunlari birbirine karistirmak en
//   yanlis sonucu verir -- "veri yok" ile "veri gelemedi" ayni sey
//   degildir ve okurun hangisi oldugunu bilmesi gerekir.
// * Fotograf ATFIYLA birlikte basilir. Atifsiz fotograf beslemeye
//   zaten girmiyor; burada da atif alani kosulsuz basiliyor.
// * Ticari kaynagin adi ve baglantisi GORUNUR. Kisa iktibas hakkinin
//   sarti bu.
// * `kurgusal` icerik ETIKETLI basilir.
// * Piyasa degeri TARIHIYLE basilir. Sayi tek basina "canli fiyat"
//   izlenimi veriyor; sitede tam bu yasandi (tarih yalnizca fare
//   ustunde gorunuyordu, telefonda kimse goremiyordu).

import React from "react";
import {
  ActivityIndicator,
  ScrollView,
  Image,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import * as api from "./api";
import { Tema, useTema, yonRengi } from "./tema";

/** Yukleniyor / hata / bos hallerini TEK yerden basar. */
export function Durum({
  yukleniyor,
  hata,
  bos,
  bosMetin = "Henüz içerik yok.",
  yenile,
}: {
  yukleniyor?: boolean;
  hata?: string | null;
  bos?: boolean;
  bosMetin?: string;
  yenile?: () => void;
}) {
  const t = useTema();
  if (yukleniyor) {
    return (
      <View style={d.orta}>
        <ActivityIndicator color={t.renk.vurgu} />
        <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>Yükleniyor…</Text>
      </View>
    );
  }
  if (hata) {
    return (
      <View style={d.orta}>
        <Text style={[d.hataBaslik, { color: t.renk.yazi }]}>
          Veri alınamadı
        </Text>
        {/* HATA METNI GOSTERILIYOR: "bir seyler ters gitti" okura
            hicbir sey anlatmiyor ve sorunu bildirmesini de
            engelliyor. */}
        <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>{hata}</Text>
        {yenile ? (
          <Pressable
            onPress={yenile}
            accessibilityRole="button"
            style={[d.dugme, { borderColor: t.renk.vurgu }]}
          >
            <Text style={{ color: t.renk.vurgu, fontWeight: "600" }}>
              Yeniden dene
            </Text>
          </Pressable>
        ) : null}
      </View>
    );
  }
  if (bos) {
    return (
      <View style={d.orta}>
        <Text style={[d.ipucu, { color: t.renk.yazi3 }]}>{bosMetin}</Text>
      </View>
    );
  }
  return null;
}

/** Çip şeridinin yüksekliği: çip 40 + dikey dolgu 12×2. */
const CIP_SERIT_YUKSEKLIGI = 64;

export type Cip = { kod: string; ad: string };

/**
 * YATAY SUZGEC SERIDI -- TEK YERDE.
 *
 * NEDEN BILESEN: ayni serit uc ekranda ayri ayri yazilmisti
 * (arastirma, haberler, arama) ve UCUNDE DE AYNI KUSUR vardi.
 *
 * KUSUR OLCULDU (2026-10-19, gercek tarayici): `ScrollView horizontal`
 * bir `flex: 1` sutun icinde YUKSEKLIGINI KAYBEDIYOR. Olculen
 * kapsayici zinciri:
 *
 *     cip (Pressable)   ust  76   yukseklik  40
 *     contentContainer  ust  64   yukseklik  24
 *     ScrollView        ust  64   yukseklik   7   <- COKTU
 *
 * `overflow: auto hidden` oldugu icin 40 piksellik cipler 7
 * piksellik kutuda kirpiliyordu. Cipler DOM'da vardi, `visibility`
 * gorunurdu, `getBoundingClientRect` dogru degerleri veriyordu --
 * yani kaynaga ya da olcume bakarak "var" diye gecilebilirdi.
 * Yalnizca EKRAN GORUNTUSUNDE yoktular.
 *
 * Cozum: seride ACIK yukseklik veriliyor ve `flexGrow: 0` ile
 * sutun akisindan cikariliyor.
 */
export function CipSeridi({
  secenekler,
  secili,
  sec,
}: {
  secenekler: Cip[];
  secili: string;
  /** Aynı çipe tekrar basmak seçimi kaldırır. */
  sec: (kod: string) => void;
}) {
  const t = useTema();
  if (secenekler.length < 2) return null;
  // SARMALAYICI `View` -- `ScrollView`in kendi `style`i YETMEDI.
  //
  // Olculdu: `style={{height: 64}}` verildiginde bile RN Web'in
  // kaydirma kabi 7,3 piksel kaliyordu (satir ici stil bos, atomik
  // sinifa cevriliyor ve sutun akisinda ezilyor). Sabit yuksekligi
  // ONUN DISINDAKI bir View'a vermek tek belirsizlik birakmayan yol:
  // View'in yuksekligi her platformda aynidir.
  return (
    <View style={d.seritKap}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={d.serit}
        contentContainerStyle={d.seritIc}
      >
        {secenekler.map((x) => {
          const aktif = x.kod === secili;
          return (
            <Pressable
              key={x.kod || "hepsi"}
              onPress={() => sec(aktif && x.kod ? "" : x.kod)}
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
                {x.ad}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function Baslik({ metin, alt }: { metin: string; alt?: string }) {
  const t = useTema();
  return (
    <View style={d.bolumBasi}>
      <Text style={[d.bolumBaslik, { color: t.renk.yazi }]}>{metin}</Text>
      {alt ? (
        <Text style={[d.bolumAlt, { color: t.renk.yazi3 }]}>{alt}</Text>
      ) : null}
    </View>
  );
}

export function Etiket({
  metin,
  renk,
  zemin,
}: {
  metin: string;
  renk?: string;
  zemin?: string;
}) {
  const t = useTema();
  return (
    <View
      style={[
        d.etiket,
        {
          backgroundColor: zemin || t.renk.panel2,
          borderColor: t.renk.cizgi,
          borderRadius: t.r.mini,
        },
      ]}
    >
      <Text style={[d.etiketYazi, { color: renk || t.renk.yazi3 }]}>
        {metin}
      </Text>
    </View>
  );
}

/** Fotograf + ZORUNLU atif. Atif yoksa gorsel de basilmiyor. */
export function Gorsel({
  yol,
  atif,
  yuksek = 170,
}: {
  yol: string;
  atif: string;
  yuksek?: number;
}) {
  const t = useTema();
  // CC BY atfi zorunlu. Besleme atifsiz fotografi zaten dusuruyor;
  // burada ikinci bir kapi var cunku bu bilesen baska bir kaynaktan
  // da beslenebilir.
  if (!yol || !atif) return null;
  return (
    <View>
      <Image
        source={{ uri: api.varlikAdresi(yol) }}
        style={{
          width: "100%",
          height: yuksek,
          borderRadius: t.r.kucuk,
          backgroundColor: t.renk.panel2,
        }}
        resizeMode="cover"
        accessible
        accessibilityLabel="Haber görseli"
      />
      <Text style={[d.atif, { color: t.renk.yazi3 }]}>{atif}</Text>
    </View>
  );
}

function tarihTR(iso: string): string {
  if (!iso) return "";
  const ay = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
  ];
  const p = iso.split("-");
  if (p.length !== 3) return iso;
  const a = parseInt(p[1], 10);
  if (!a || a > 12) return iso;
  return `${parseInt(p[2], 10)} ${ay[a - 1]} ${p[0]}`;
}

export function HaberKarti({
  h,
  bas,
}: {
  h: api.Haber;
  bas: (slug: string) => void;
}) {
  const t = useTema();
  return (
    <Pressable
      onPress={() => bas(h.slug)}
      accessibilityRole="button"
      style={({ pressed }) => [
        d.kart,
        {
          backgroundColor: t.renk.panel,
          borderColor: t.renk.cizgi,
          borderRadius: t.r.orta,
          opacity: pressed ? 0.75 : 1,
        },
      ]}
    >
      <Gorsel yol={h.foto} atif={h.foto_atif} yuksek={150} />
      <View style={d.kartIc}>
        <View style={d.satir}>
          {h.konu ? <Etiket metin={h.konu} renk={t.renk.vurgu} /> : null}
          {h.tarih ? (
            <Text style={[d.ufak, { color: t.renk.yazi3 }]}>
              {tarihTR(h.tarih)}
            </Text>
          ) : null}
        </View>
        <Text style={[d.kartBaslik, { color: t.renk.yazi }]}>{h.baslik}</Text>
        {h.ozet ? (
          <Text
            style={[d.kartOzet, { color: t.renk.yazi2 }]}
            numberOfLines={3}
          >
            {h.ozet}
          </Text>
        ) : null}
        {/* KAYNAK GORUNUR. Ticari kaynakta bu zorunlu; digerlerinde de
            okurun nereden geldigini bilmesi dogru. */}
        {h.kurum ? (
          <Text style={[d.ufak, { color: t.renk.notr }]}>
            Kaynak: {h.kurum_tam || h.kurum}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
}

export function AnalizKarti({
  a,
  bas,
}: {
  a: api.Analiz;
  bas: (slug: string) => void;
}) {
  const t = useTema();
  return (
    <Pressable
      onPress={() => bas(a.slug)}
      accessibilityRole="button"
      style={({ pressed }) => [
        d.kart,
        {
          backgroundColor: t.renk.panel,
          borderColor: t.renk.cizgi,
          borderRadius: t.r.orta,
          opacity: pressed ? 0.75 : 1,
        },
      ]}
    >
      <View style={d.kartIc}>
        <View style={d.satir}>
          {a.kategori ? (
            <Etiket metin={a.kategori} renk={t.renk.vurgu} />
          ) : null}
          {/* KURGUSAL ICERIK ETIKETLI. Isaret ulasmazsa kurgusal
              icerik gercek gibi gorunur. */}
          {a.kurgusal ? (
            <Etiket metin="KURGUSAL" renk={t.renk.uyari} />
          ) : null}
          {a.skor ? (
            <Etiket metin={`Skor ${a.skor}`} renk={t.renk.yazi2} />
          ) : null}
        </View>
        <Text style={[d.kartBaslik, { color: t.renk.yazi }]}>{a.baslik}</Text>
        {a.ozet ? (
          <Text
            style={[d.kartOzet, { color: t.renk.yazi2 }]}
            numberOfLines={3}
          >
            {a.ozet}
          </Text>
        ) : null}
        <View style={d.satir}>
          {a.sirket ? (
            <Text style={[d.ufak, { color: t.renk.notr }]}>{a.sirket}</Text>
          ) : null}
          {a.donem ? (
            <Text style={[d.ufak, { color: t.renk.notr }]}>· {a.donem}</Text>
          ) : null}
          {a.okuma_dk ? (
            <Text style={[d.ufak, { color: t.renk.notr }]}>
              · {a.okuma_dk} dk
            </Text>
          ) : null}
        </View>
        {/* IMZALI YORUM OTOMATIK ANALIZDEN AYRI GOSTERILIYOR. */}
        {a.imzali ? (
          <Text style={[d.ufak, { color: t.renk.vurgu }]}>
            {a.yazar}
            {a.unvan ? ` · ${a.unvan}` : ""}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
}

/** Piyasa kalemi -- DEGER VE TARIH BIRLIKTE. */
export function PiyasaKarti({ k }: { k: api.PiyasaKalemi }) {
  const t = useTema();
  return (
    <View
      style={[
        d.piyasa,
        {
          backgroundColor: t.renk.panel,
          borderColor: t.renk.cizgi,
          borderRadius: t.r.kucuk,
        },
      ]}
    >
      <Text style={[d.piyasaAd, { color: t.renk.yazi3 }]} numberOfLines={1}>
        {k.ad}
      </Text>
      <Text style={[d.piyasaDeger, { color: t.renk.yazi }]}>{k.deger}</Text>
      <View style={d.satir}>
        <Text style={[d.ufak, { color: yonRengi(t, k.yon) }]}>{k.fark}</Text>
        {/* BAYAT KALEM ISARETLI: kac gun once oldugu yaziliyor. */}
        {k.bayat && k.gun ? (
          <Text style={[d.ufak, { color: t.renk.uyari }]}>· {k.gun}g</Text>
        ) : null}
      </View>
      {/* VERI TARIHI HER KALEMDE. Sayi tek basina canli fiyat
          izlenimi veriyor; sitede tam bu kusur yasandi. */}
      <Text style={[d.cokUfak, { color: t.renk.notr }]}>
        {tarihTR(k.tarih)}
      </Text>
    </View>
  );
}

/** Kaynaga giden dis baglanti. */
export function KaynakBagi({ adres, kurum }: { adres: string; kurum: string }) {
  const t = useTema();
  if (!adres) return null;
  return (
    <Pressable
      onPress={() => Linking.openURL(adres)}
      accessibilityRole="link"
      style={[d.dugme, { borderColor: t.renk.cizgiParlak }]}
    >
      <Text style={{ color: t.renk.vurgu }}>
        Kaynakta oku{kurum ? ` · ${kurum}` : ""}
      </Text>
    </Pressable>
  );
}

export { tarihTR };

const d = StyleSheet.create({
  // SERIT YUKSEKLIGI ACIK: `flexGrow: 0` olmadan yatay ScrollView
  // sutun akisinda yukseklik kaybedip 7 piksele cokuyor (olculdu).
  seritKap: { height: CIP_SERIT_YUKSEKLIGI },
  serit: { flexGrow: 0 },
  seritIc: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
    alignItems: "center",
  },
  cip: {
    paddingHorizontal: 13,
    paddingVertical: 9,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 40,
    justifyContent: "center",
  },
  orta: { padding: 28, alignItems: "center", gap: 10 },
  ipucu: { fontSize: 14, textAlign: "center", lineHeight: 20 },
  hataBaslik: { fontSize: 17, fontWeight: "700" },
  dugme: {
    marginTop: 6,
    paddingVertical: 11,
    paddingHorizontal: 18,
    borderWidth: 1,
    borderRadius: 10,
    // 44 piksel dokunma hedefi: sitede de ayni esik korunuyor.
    minHeight: 44,
    justifyContent: "center",
  },
  bolumBasi: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 8 },
  bolumBaslik: { fontSize: 19, fontWeight: "700", letterSpacing: -0.3 },
  bolumAlt: { fontSize: 13, marginTop: 3, lineHeight: 18 },
  etiket: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderWidth: StyleSheet.hairlineWidth,
  },
  etiketYazi: { fontSize: 11, fontWeight: "700", letterSpacing: 0.3 },
  kart: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  kartIc: { padding: 14, gap: 7 },
  kartBaslik: { fontSize: 16, fontWeight: "700", lineHeight: 22 },
  kartOzet: { fontSize: 14, lineHeight: 20 },
  satir: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  ufak: { fontSize: 12 },
  cokUfak: { fontSize: 11 },
  atif: { fontSize: 10, marginTop: 4, marginHorizontal: 14, lineHeight: 14 },
  piyasa: {
    width: 128,
    padding: 11,
    marginRight: 9,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 3,
  },
  piyasaAd: { fontSize: 11, fontWeight: "600", letterSpacing: 0.2 },
  piyasaDeger: { fontSize: 17, fontWeight: "700" },
});
