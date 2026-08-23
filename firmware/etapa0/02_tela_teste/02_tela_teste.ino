/*
 * Etapa 0.2 — Teste da tela TFT
 * Placa: ESP32-2432S028R
 *
 * Pré-requisito: TFT_eSPI configurado com TFT_eSPI_User_Setup_CYD.h
 *
 * Sucesso: texto "DIARIO ESTOICO" / "Etapa 0 - Tela OK" na tela.
 */

#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

void setup() {
  Serial.begin(115200);
  delay(200);

  // Backlight
  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);  // landscape 320x240
  tft.fillScreen(TFT_BLACK);

  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("DIARIO ESTOICO", 160, 90, 4);

  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Etapa 0 - Tela OK", 160, 140, 2);

  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString("ESP32-2432S028R", 160, 190, 2);

  Serial.println("Tela inicializada.");
}

void loop() {
  // nada
}
