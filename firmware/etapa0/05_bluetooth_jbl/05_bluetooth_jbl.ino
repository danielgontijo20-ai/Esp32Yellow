/*
 * Etapa 0.5 — Teste Bluetooth A2DP → JBL CINEMA SB110
 * Placa: ESP32-2432S028R
 *
 * Biblioteca: ESP32-A2DP (Phil Schatzmann)
 *   Ferramentas → Gerenciar Bibliotecas → "ESP32-A2DP"
 *
 * Antes de gravar:
 * 1) Desconecte a JBL do celular
 * 2) Coloque a JBL em modo Bluetooth / pareamento
 *
 * Sucesso: tela mostra "Conectado: JBL CINEMA SB110"
 * e a caixa emite um tom curto periodicamente.
 */

#include <TFT_eSPI.h>
#include "BluetoothA2DPSource.h"

// Nome exatamente como a barra costuma aparecer.
// Se não conectar, veja no celular o nome exato e ajuste.
static const char *BT_SPEAKER_NAME = "JBL CINEMA SB110";

TFT_eSPI tft = TFT_eSPI();
BluetoothA2DPSource a2dp;

static bool connectedShown = false;
static uint32_t phase = 0;

// Gera um tom simples (onda senoidal aproximada) para validar áudio
int32_t get_data_frames(Frame *frame, int32_t frame_count) {
  static float t = 0.0f;
  const float freq = 440.0f;      // Lá 440 Hz
  const float two_pi_f = 2.0f * 3.14159265f * freq / 44100.0f;

  for (int i = 0; i < frame_count; i++) {
    // volume baixo (~10%)
    int16_t sample = (int16_t)(sinf(t) * 3000.0f);
    frame[i].channel1 = sample;
    frame[i].channel2 = sample;
    t += two_pi_f;
    if (t > 2.0f * 3.14159265f) t -= 2.0f * 3.14159265f;
  }
  return frame_count;
}

void showStatus(const char *title, const char *detail, uint16_t color) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Etapa 0.5 - Bluetooth", 10, 10, 2);
  tft.setTextColor(color, TFT_BLACK);
  tft.drawString(title, 10, 50, 2);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString(detail, 10, 90, 2);
  tft.drawString(BT_SPEAKER_NAME, 10, 130, 2);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);
  showStatus("Procurando JBL...", "Desparee do celular", TFT_YELLOW);

  Serial.printf("Conectando A2DP a: %s\n", BT_SPEAKER_NAME);

  // Volume 50%
  a2dp.set_volume(64);
  a2dp.start(BT_SPEAKER_NAME, get_data_frames);
}

void loop() {
  bool ok = a2dp.is_connected();
  if (ok && !connectedShown) {
    connectedShown = true;
    showStatus("Conectado!", "Tom 440Hz ativo", TFT_GREEN);
    Serial.println("JBL conectada via A2DP.");
  } else if (!ok && connectedShown) {
    connectedShown = false;
    showStatus("Desconectado", "Reative o pareamento", TFT_RED);
    Serial.println("JBL desconectada.");
  } else if (!ok && (millis() / 1000) != phase) {
    phase = millis() / 1000;
    Serial.println("Ainda procurando JBL...");
  }
  delay(200);
}
