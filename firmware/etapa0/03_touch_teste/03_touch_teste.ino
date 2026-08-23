/*
 * Etapa 0.3 — Teste do touchscreen resistivo (XPT2046)
 * Placa: ESP32-2432S028R
 *
 * Se o toque aparecer no lugar errado, mude só o MAP_MODE abaixo
 * (0, 1, 2 ou 3), grave de novo e teste.
 *
 * Sucesso: o ponto aparece onde o dedo toca.
 */

#include <SPI.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>

// ============================================================
// CALIBRAÇÃO: mude este número se o toque estiver desalinhado
// 0 = padrão
// 1 = inverte X e Y          ← tente este primeiro se estiver "espelhado"
// 2 = troca X com Y
// 3 = troca X/Y + inverte
// ============================================================
#define MAP_MODE 1

#define XPT2046_IRQ  36
#define XPT2046_MOSI 32
#define XPT2046_MISO 39
#define XPT2046_CLK  25
#define XPT2046_CS   33

// Faixa raw típica da CYD (pode ajustar depois se precisar)
#define RAW_X_MIN 200
#define RAW_X_MAX 3700
#define RAW_Y_MIN 240
#define RAW_Y_MAX 3800

TFT_eSPI tft = TFT_eSPI();
SPIClass touchSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(XPT2046_CS, XPT2046_IRQ);

void mapTouch(int16_t rawX, int16_t rawY, int16_t &x, int16_t &y) {
  int16_t a = map(rawX, RAW_X_MIN, RAW_X_MAX, 0, 320);
  int16_t b = map(rawY, RAW_Y_MIN, RAW_Y_MAX, 0, 240);

  switch (MAP_MODE) {
    case 1:  // inverte X e Y
      x = 319 - a;
      y = 239 - b;
      break;
    case 2:  // troca eixos
      x = map(rawY, RAW_Y_MIN, RAW_Y_MAX, 0, 320);
      y = map(rawX, RAW_X_MIN, RAW_X_MAX, 0, 240);
      break;
    case 3:  // troca + inverte
      x = 319 - map(rawY, RAW_Y_MIN, RAW_Y_MAX, 0, 320);
      y = 239 - map(rawX, RAW_X_MIN, RAW_X_MAX, 0, 240);
      break;
    default: // 0 padrão
      x = a;
      y = b;
      break;
  }

  if (x < 0) x = 0;
  if (x > 319) x = 319;
  if (y < 0) y = 0;
  if (y > 239) y = 239;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Toque na tela...", 10, 10, 2);

  char modeLine[32];
  snprintf(modeLine, sizeof(modeLine), "MAP_MODE = %d", MAP_MODE);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString(modeLine, 10, 35, 2);

  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

  Serial.printf("Touch pronto. MAP_MODE=%d\n", MAP_MODE);
}

void loop() {
  if (touch.tirqTouched() && touch.touched()) {
    TS_Point p = touch.getPoint();
    int16_t x, y;
    mapTouch(p.x, p.y, x, y);

    tft.fillCircle(x, y, 4, TFT_YELLOW);
    Serial.printf("raw(%d,%d) -> px(%d,%d) mode=%d\n", p.x, p.y, x, y, MAP_MODE);
    delay(40);
  }
}
