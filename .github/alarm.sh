#!/usr/bin/env bash
# KIRMIZI KOSUYU DUYUR / SAGLIGA DONUNCE KAPAT -- IKI AKIS ICIN TEK YOL.
#
# NEDEN AYRI DOSYA
# ----------------
# Bu mantik `otomasyon.yml` icinde satir ici duruyordu ve `bilanco.yml`de
# HIC YOKTU. Olculdu (2026-11-03): bilanco akisinda "duyur" gecen tek bir
# adim yok. Gunde BIR kosan bir hat sessizce dusuyor, yani bir gunluk
# bilanco uretimi kaybolup kimse duymuyor.
#
# Tam bu yasandi: kosu #65 (2026-11-01) geri yazma kapisindan dustu, o
# kosuda uretilen her sey kayboldu (25 sayfa, 7 sektor, 25 goc) ve hicbir
# sey otmedi -- Actions listesine bakarak buldum.
#
# Kopyalamak yanlis cozum olurdu: ayni karari iki yerde almak bu depoda
# UC KEZ kosu dusurdu. Tek dosya, iki cagiran.
#
# KURU CALISTIRMA SART
# --------------------
# Alarm, her sey bozuldugunda haber veren sey; dogrulanmadan
# degistirilemez. `KURU=1` ile hicbir `gh` cagrisi yapilmadan govde
# basiliyor ve sinama onu okuyor. Alarmin kendisini gercekten tetikleyip
# denemek, her denemede bir kayit acmak demekti.
#
# KULLANIM
#   KIP=duyur|kapat  DEPO=sahip/depo  KOSU_ID=...  SUNUCU=https://github.com
#   OLAY=schedule  SHA=...  BASLIK="..."  ETIKET=otomasyon
#   [SINAMA_DOSYASI=/tmp/dusen-sinamalar.txt]  [KURU=1]
set -u

KIP="${KIP:?KIP gerekli (duyur|kapat)}"
DEPO="${DEPO:?DEPO gerekli}"
ETIKET="${ETIKET:?ETIKET gerekli}"
KURU="${KURU:-}"

_gh() {
  if [ -n "$KURU" ]; then
    echo "KURU: gh $*"
    return 0
  fi
  gh "$@"
}

if [ "$KIP" = "kapat" ]; then
  # SAGLIGA DONUNCE ALARM KENDILIGINDEN SUSUYOR.
  #
  # Elle kapatilmasi gereken bir alarm, birkac gun sonra kapatilmayi
  # bekleyen bir gurultuye donusur ve bir sonraki gercek arizada kimse
  # bakmaz. Kayit yesil kosuda kapaniyor; yani ACIK bir kayit her zaman
  # "su anda bozuk" demek.
  #
  # `|| true` BILEREK: alarmi kapatamamak, YESIL bir kosuyu kirmizi
  # yapmamali. Kapanmayan kayit en fazla fazladan bir bildirim; saglikli
  # kosuyu kirmiziya cevirmek ise bu dosyanin cozmeye calistigi sorunun
  # ta kendisi.
  mevcut=$(_gh issue list --state open --label "$ETIKET" \
      --json number --jq '.[0].number // empty' 2>/dev/null || true)
  if [ -n "$mevcut" ] && [ -z "$KURU" ]; then
    gh issue close "$mevcut" \
      --comment "Koşu yeşile döndü; alarm kendiliğinden kapandı." \
      || true
    echo "kayit #$mevcut kapatildi"
  else
    echo "acik kayit yok -- kapatilacak bir sey de yok"
  fi
  exit 0
fi

KOSU_ID="${KOSU_ID:?KOSU_ID gerekli}"
SUNUCU="${SUNUCU:-https://github.com}"
OLAY="${OLAY:-bilinmiyor}"
SHA="${SHA:-bilinmiyor}"
BASLIK="${BASLIK:?BASLIK gerekli}"

kosu="$SUNUCU/$DEPO/actions/runs/$KOSU_ID"

# "BIR SEY BOZUK" ILE "NE BOZUK" ARASINDAKI FARK.
#
# Olculdu (2026-10-20): dagitim yedi bucuk saat durdu. Alarm CALISTI,
# kayit 12:59'da acildi -- ama govdesinde yalnizca "kosu ozetine bakin"
# yaziyordu. Hangi adimin, hangi sinamanin dustugu yalnizca GUNLUKTEYDI
# ve gunluk indirmek yetki istiyor. Alarmi okuyup ne yapacagini
# bilememek, alarmin yarisini bosa harcamak.
adimlar=""
if [ -z "$KURU" ]; then
  adimlar=$(gh api "repos/$DEPO/actions/runs/$KOSU_ID/jobs" \
    --jq '.jobs[].steps[]? | select(.conclusion=="failure") | "- " + .name' \
    2>/dev/null | head -8)
  # IPTALDE "dusen adim" YOK, "kesilen adim" VAR.
  #
  # Olculdu (2026-11-03): son 40 kosunun ikisi "cancelled" bitti ve
  # ikisi de alarmin disinda kaldi -- GitHub'da iptal `failure()`
  # sayilmiyor. Biri zararsizdi, oteki DEGIL: kosu #2468'de uretim
  # adimi ORTASINDA kesildi, o cevrimde site guncellenmedi.
  if [ -z "$adimlar" ]; then
    adimlar=$(gh api "repos/$DEPO/actions/runs/$KOSU_ID/jobs" \
      --jq '.jobs[].steps[]? | select(.conclusion=="cancelled") | "- (kesildi) " + .name' \
      2>/dev/null | head -8)
  fi
else
  adimlar="- (kuru calistirma -- adim listesi cekilmedi)"
fi
[ -z "$adimlar" ] && adimlar="- (adım listesi alınamadı -- koşu özetine bakın)"

# Ciktiya bakan koscu dusen dosya adlarini buraya yaziyor.
sinamalar=""
dosya="${SINAMA_DOSYASI:-}"
if [ -n "$dosya" ] && [ -s "$dosya" ]; then
  sinamalar="

Düşen sınamalar:
$(sed 's|^|- |' "$dosya" | head -12)"
fi

govde="Koşu: $kosu
Tetikleyici: $OLAY
Commit: $SHA
Zaman (UTC): $(date -u +'%Y-%m-%d %H:%M')

Düşen adımlar:
$adimlar$sinamalar

Bu kayıt, koşu yeşile döndüğünde KENDİLİĞİNDEN kapanır."

if [ -n "$KURU" ]; then
  echo "=== KURU CALISTIRMA: baslik ==="
  echo "$BASLIK"
  echo "=== KURU CALISTIRMA: etiket ==="
  echo "$ETIKET"
  echo "=== KURU CALISTIRMA: govde ==="
  echo "$govde"
  exit 0
fi

# TEK KAYIT: ayni kusur 21 kez dustugunde 21 kayit acmak alarmi
# degersizlestirirdi. Acik kayit varsa yenisi ACILMIYOR; yalnizca son
# yorumdan alti saat gectiyse bir satir ekleniyor, yani surmekte olan bir
# arizanin zaman cizelgesi olusuyor ama gurultu olmuyor.
mevcut=$(gh issue list --state open --label "$ETIKET" \
    --json number --jq '.[0].number // empty' 2>/dev/null || true)
if [ -z "$mevcut" ]; then
  gh label create "$ETIKET" --color B60205 \
    --description "Otomasyon kosusu basarisiz" 2>/dev/null || true
  # ALARMIN KENDI ARIZASI SESSIZ KALMAMALI.
  #
  # Kayit acilamazsa (yetki, kota, Issues kapali) alarm hic CALMAZ ve
  # "acik kayit yok" YANLISLIKLA "saglikli" diye okunur -- calmayan
  # alarm, alarmsizliktan kotudur.
  #
  # O yuzden hata YUTULMUYOR: adim kirmizi yaniyor. Kosu zaten kirmizi,
  # yani durumu kotulestirmiyor; yalnizca ADIM LISTESINDE "alarm da
  # bozuk" diye gorunur oluyor.
  if ! gh issue create --title "$BASLIK" --label "$ETIKET" --body "$govde"; then
    echo "::error::ALARM CALISMADI -- kayit acilamadi (yetki? Issues kapali?)"
    exit 1
  fi
  exit 0
fi

# ALTI SAATTE BIR: zaman cizelgesi olussun ama gurultu olmasin.
guncel=$(gh issue view "$mevcut" --json updatedAt --jq .updatedAt 2>/dev/null || echo "")
if [ -n "$guncel" ]; then
  gecen=$(( $(date -u +%s) - $(date -u -d "$guncel" +%s) ))
  if [ "$gecen" -lt 21600 ]; then
    echo "kayit #$mevcut acik ve $((gecen/60)) dk once guncellendi -- yorum eklenmiyor"
    exit 0
  fi
fi
gh issue comment "$mevcut" --body "$govde" || true
