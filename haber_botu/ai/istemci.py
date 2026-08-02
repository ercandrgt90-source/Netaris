"""Claude API istemcisi.

Tek sorumlulugu: hazir prompt'u modele gonderip metni ve maliyeti dondurmek.
Oran hesaplama, ifade taramasi ve yayin bu modulun isi degil.

Tasarim notlari
---------------
* **Model:** claude-opus-5. Maliyet dusurmek icin kucuk modele gecis bilincli
  bir karar olmali; MODEL sabitini degistirmek yeterli. Sonnet 5 ayni API ile
  calisir ve belirgin olcude ucuzdur.

* **Onbellek:** sistem talimati her istekte ayni oldugu icin onbellege
  aliniyor. Onbellekten okuma normal fiyatin onda birine denk geliyor, yani
  gunde 10 icerikte gercek bir tasarruf. `rapor()` cikitisinda
  `onbellekten` alani sifir kaliyorsa onbellek calismiyor demektir.

* **Ornekleme parametreleri yok.** claude-opus-5 uzerinde temperature, top_p
  ve top_k gonderilirse istek 400 ile reddedilir. Uslup prompt ile
  yonlendirilir.

* **Yedek model.** Guvenlik siniflandiricisi bir istegi reddedebilir; bu
  durumda yanit HTTP 200 doner ama stop_reason "refusal" olur. `fallbacks`
  parametresi reddedilen istegi ayni cagri icinde baska bir modelde yeniden
  calistirir. Finans iceriginde reddedilme beklenmiyor, ama hattin sessizce
  bos icerik uretmesini engelliyor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic

MODEL = "claude-opus-5"

# Dusunme derinligi. claude-opus-5'te dusunme varsayilan olarak acik.
# "high" baslangic noktasi; maliyet icin "medium" ve "low" denenmeye deger --
# bu modelde alt seviyeler beklenenden guclu.
EFFORT = "high"

# Dusunme + yanit metni birlikte bu siniri paylasir. Turkce metin ayni
# icerik icin Ingilizce'den daha fazla token uretir; bol pay biraktik.
MAX_TOKENS = 16_000

# Milyon token basina dolar. Onbellek yazma girdinin 1.25 kati, onbellekten
# okuma onda biri. Sonnet 5'in fiyatlari 31 Agustos 2026'ya kadar gecerli
# tanitim fiyatlari -- o tarihten sonra $3.00 / $15.00'a cikacak.
FIYATLAR: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
}


def _fiyat(model: str) -> tuple[float, float]:
    for anahtar, deger in FIYATLAR.items():
        if model.startswith(anahtar):
            return deger
    # Bilinmeyen model: maliyet hesabini uydurmak yerine sifir dondur
    return (0.0, 0.0)


class RedEdildi(RuntimeError):
    """Guvenlik siniflandiricisi istegi reddetti ve yedek model de uretmedi."""


@dataclass(frozen=True)
class Sonuc:
    metin: str
    girdi_token: int
    cikti_token: int
    onbellek_yazma: int
    onbellekten: int
    kullanilan_model: str

    @property
    def maliyet(self) -> float:
        """Bu cagrinin yaklasik dolar maliyeti.

        Yanitin bildirdigi modelin fiyatiyla hesaplaniyor -- yedek model
        devreye girdiyse maliyet onun tarifesinden cikar.
        """
        girdi, cikti = _fiyat(self.kullanilan_model)
        return (
            self.girdi_token * girdi
            + self.cikti_token * cikti
            + self.onbellek_yazma * girdi * 1.25
            + self.onbellekten * girdi * 0.10
        ) / 1_000_000

    def rapor(self) -> str:
        return (
            f"model: {self.kullanilan_model}\n"
            f"girdi: {self.girdi_token:,} token  "
            f"cikti: {self.cikti_token:,} token\n"
            f"onbellek: {self.onbellekten:,} okundu, {self.onbellek_yazma:,} yazildi\n"
            f"maliyet: ${self.maliyet:.4f}"
        )


def _istemci() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY ayarlanmamis.\n"
            "Anahtari console.anthropic.com adresinden alip su sekilde tanimlayin:\n"
            '  PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-..."\n'
            "Kalici olmasi icin Windows ortam degiskenlerine ekleyin."
        )
    return anthropic.Anthropic()


# Yedek model parametresini destekleyen modeller. Sonnet 5'e `fallbacks`
# gonderilirse istek 400 ile reddediliyor -- bu yuzden model bazinda
# koşullu gonderiyoruz.
_YEDEK_DESTEKLI = ("claude-opus-5", "claude-fable-5", "claude-mythos-5")


def uret(sistem: str, kullanici: str, model: str = MODEL, effort: str = EFFORT) -> Sonuc:
    """Prompt'u modele gonderir ve uretilen metni dondurur."""
    istemci = _istemci()

    ek: dict = {}
    if any(model.startswith(m) for m in _YEDEK_DESTEKLI):
        ek["betas"] = ["server-side-fallback-2026-07-01"]
        ek["fallbacks"] = "default"

    yanit = istemci.beta.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        output_config={"effort": effort},
        **ek,
        system=[
            {
                "type": "text",
                "text": sistem,
                # Sistem talimati her istekte ayni -- onbellege alinabilir
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": kullanici}],
    )

    if yanit.stop_reason == "refusal":
        ayrinti = ""
        if yanit.stop_details is not None:
            ayrinti = f" (kategori: {yanit.stop_details.category})"
        raise RedEdildi(f"istek guvenlik siniflandiricisi tarafindan reddedildi{ayrinti}")

    parcalar = [b.text for b in yanit.content if b.type == "text"]
    if not parcalar:
        raise RuntimeError(f"modelden metin gelmedi (stop_reason: {yanit.stop_reason})")

    k = yanit.usage
    return Sonuc(
        metin="\n".join(parcalar).strip(),
        girdi_token=k.input_tokens,
        cikti_token=k.output_tokens,
        onbellek_yazma=k.cache_creation_input_tokens or 0,
        onbellekten=k.cache_read_input_tokens or 0,
        kullanilan_model=yanit.model,
    )
