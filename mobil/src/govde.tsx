// ANALIZ GOVDESI -- HTML'i temayla boyayarak basar.
//
// NEDEN WEBVIEW
// Bilanco analizlerinin govdesi TABLO iceriyor: seviye tablosu,
// oran tablosu, sektor medyani kiyasi. Bunlar analizin kendisi --
// dusurulurse sayfa "sirket iyi gidiyor" diyen bir paragrafa
// indirgenir ve asil kanit kaybolur.
//
// Tabloyu yerel bilesenlerle yeniden kurmak, hizalama ve kaydirma
// isini sifirdan yazmak demekti. Govde icin WebView, tablolari
// oldugu gibi ve dogru hizalanmis basiyor.
//
// BU, "UYGULAMA ASLINDA WEB SITESI" DEMEK DEGIL: ekranin kendisi
// yerel, gezinme yerel, basliklar ve kartlar yerel. Yalnizca MAKALE
// GOVDESI isleniyor -- bir metin bileseni gibi.
//
// YUKSEKLIK ICERIDEN BILDIRILIYOR: WebView kendi icerigine gore
// buyumuyor, sabit yukseklik aliyor. Icerikten gelen olcum olmadan
// ya metin kirpilir ya altinda bos alan kalir.

import React, { useMemo, useState } from "react";
import { StyleSheet, View } from "react-native";
import { WebView } from "react-native-webview";

import { Tema } from "./tema";

/** Baslangic yuksekligi -- ilk olcum gelene kadar. */
const ILK_YUKSEKLIK = 320;

function kacis(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Govde HTML'ini tema renkleriyle sararak tam bir belge uretir.
 *
 * RENKLER SABIT YAZILMIYOR, temadan geliyor -- yani `stil.css`ten.
 * Govde koyu temada beyaz zeminde kalirsa ekranin yarisi parlar.
 */
function belge(govde: string, t: Tema): string {
  const r = t.renk;
  return `<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: ${t.ad === "koyu" ? "dark" : "light"}; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0;
    background: ${r.zemin};
    color: ${r.yazi};
    font: 16px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI",
          Roboto, system-ui, sans-serif;
    -webkit-text-size-adjust: 100%;
    overflow-x: hidden;
  }
  h2 { font-size: 20px; line-height: 1.3; margin: 26px 0 10px;
       letter-spacing: -0.3px; }
  h3 { font-size: 17px; line-height: 1.35; margin: 22px 0 8px; }
  h2:first-child, h3:first-child { margin-top: 0; }
  p { margin: 0 0 14px; }
  ul, ol { margin: 0 0 14px; padding-left: 22px; }
  li { margin-bottom: 6px; }
  strong { font-weight: 700; }
  a { color: ${r.vurgu}; text-decoration: none;
      border-bottom: 1px solid ${r.cizgiParlak}; }
  code { background: ${r.panel2}; padding: 1px 4px; border-radius: 4px;
         font-size: 14px; }
  blockquote { margin: 0 0 14px; padding: 10px 14px;
    background: ${r.panel2}; border-left: 3px solid ${r.cizgiParlak};
    border-radius: 6px; }

  /* TABLO: GENISLIK TASARSA SAYFA DEGIL TABLO KAYIYOR.
     Govde yatay kayarsa okuma tamamen bozulur; sarmalayici
     kaydiriliyor. */
  .tablo-kap { overflow-x: auto; -webkit-overflow-scrolling: touch;
    margin: 0 0 16px; border: 1px solid ${r.cizgi};
    border-radius: ${t.r.kucuk}px; background: ${r.panel}; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  th, td { padding: 9px 11px; text-align: right;
    border-bottom: 1px solid ${r.cizgi}; white-space: nowrap;
    /* Rakamlar hizali olsun. */
    font-variant-numeric: tabular-nums; }
  th:first-child, td:first-child { text-align: left;
    white-space: normal; min-width: 130px; }
  thead th { background: ${r.panel2}; font-weight: 700;
    color: ${r.yazi2}; position: sticky; top: 0; }
  tbody tr:last-child td { border-bottom: 0; }

  img { max-width: 100%; height: auto; border-radius: ${t.r.kucuk}px; }
  hr { border: 0; border-top: 1px solid ${r.cizgi}; margin: 22px 0; }
  @media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
  }
</style>
</head><body>
<div id="k">${govde}</div>
<script>
  // TABLOLARI KAYDIRILABILIR BIR KABA AL.
  // Govde HTML'i siteden geliyor ve orada kabi CSS sagliyordu;
  // burada kap yoksa genis tablo tasiyor.
  document.querySelectorAll('table').forEach(function (tb) {
    if (tb.parentElement && tb.parentElement.className === 'tablo-kap') return;
    var kap = document.createElement('div');
    kap.className = 'tablo-kap';
    tb.parentNode.insertBefore(kap, tb);
    kap.appendChild(tb);
  });

  // YUKSEKLIGI BILDIR. Tek seferlik olcum yetmiyor: yazi tipi
  // yuklendikce ve resimler geldikce yukseklik degisiyor.
  function bildir() {
    var y = document.getElementById('k');
    var h = Math.max(y.scrollHeight, document.body.scrollHeight);
    window.ReactNativeWebView.postMessage(String(h));
  }
  bildir();
  window.addEventListener('load', bildir);
  if (window.ResizeObserver) {
    new ResizeObserver(bildir).observe(document.getElementById('k'));
  }
</script>
</body></html>`;
}

export function Govde({
  html,
  tema,
  disBaglanti,
}: {
  html: string;
  tema: Tema;
  /** Govde icindeki baglantiya dokununca cagrilir. */
  disBaglanti?: (adres: string) => void;
}) {
  const [yuksek, setYuksek] = useState(ILK_YUKSEKLIK);
  const kaynak = useMemo(() => belge(html, tema), [html, tema]);

  if (!html) return null;

  return (
    <View style={[s.kap, { height: yuksek }]}>
      <WebView
        originWhitelist={["*"]}
        source={{ html: kaynak, baseUrl: "https://netaris.net/" }}
        style={{ backgroundColor: "transparent" }}
        // Govde kendi icinde kaydirilmiyor: dis ScrollView kaydiriyor
        // ve ic ice kaydirma telefonda kullanilamaz hale geliyor.
        scrollEnabled={false}
        nestedScrollEnabled={false}
        showsVerticalScrollIndicator={false}
        onMessage={(o) => {
          const h = parseInt(o.nativeEvent.data, 10);
          // Olcum makul araliktaysa kabul ediliyor: bozuk bir olcum
          // ekrani tamamen bos ya da kilometrelerce uzun yapardi.
          if (Number.isFinite(h) && h > 40 && h < 60000) setYuksek(h);
        }}
        // DIS BAGLANTI UYGULAMA ICINDE ACILMIYOR: govde WebView'i bir
        // tarayici degil, bir metin bileseni. Baglantiya dokunan
        // kullanici sistem tarayicisina gidiyor.
        onShouldStartLoadWithRequest={(istek) => {
          if (istek.url === "about:blank" || istek.url.startsWith("data:")) {
            return true;
          }
          if (disBaglanti) disBaglanti(istek.url);
          return false;
        }}
      />
    </View>
  );
}

export { kacis };

const s = StyleSheet.create({
  kap: { width: "100%", overflow: "hidden" },
});
