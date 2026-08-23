/*
 * Etapa 0.2b — Teste de limpeza TOTAL da tela
 * Placa: ESP32-2432S028R
 *
 * Sucesso: a tela inteira muda de cor (vermelho, verde, azul, preto)
 * SEM sobrar a faixa do demo antigo (shop / CPU / FPS).
 */

#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

void fullFill(uint16_t color, const char *name) {
  tft.fillScreen(color);
  tft.setTextDatum(MC_DATUM);
  uint16_t textColor = (color == TFT_BLACK || color == TFT_BLUE) ? TFT_WHITE : TFT_BLACK;
  tft.setTextColor(textColor, color);
  tft.drawString(name, tft.width() / 2, tft.height() / 2, 4);

  // Marca os 4 cantos para ver se a área útil está correta
  tft.fillRect(0, 0, 12, 12, TFT_YELLOW);
  tft.fillRect(tft.width() - 12, 0, 12, 12, TFT_YELLOW);
  tft.fillRect(0, tft.height() - 12, 12, 12, TFT_YELLOW);
  tft.fillRect(tft.width() - 12, tft.height() - 12, 12, 12, TFT_YELLOW);

  Serial.printf("Fill %s  size=%dx%d\n", name, tft.width(), tft.height());
  delay(1200);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);  // landscape

  Serial.println("Teste de limpeza total da tela");
}

void loop() {
  fullFill(TFT_RED, "VERMELHO");
  fullFill(TFT_GREEN, "VERDE");
  fullFill(TFT_BLUE, "AZUL");
  fullFill(TFT_BLACK, "PRETO");
}
