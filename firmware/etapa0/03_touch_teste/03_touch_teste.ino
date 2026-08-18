/*
 * Etapa 0.3 — Teste do touchscreen resistivo (XPT2046)
 * Placa: ESP32-2432S028R
 *
 * Bibliotecas: TFT_eSPI + XPT2046_Touchscreen
 * Sucesso: ao tocar, aparece um ponto na tela e X/Y no Serial.
 */

#include <SPI.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>

// Pinos do touch na CYD (SPI separado)
#define XPT2046_IRQ  36
#define XPT2046_MOSI 32
#define XPT2046_MISO 39
#define XPT2046_CLK  25
#define XPT2046_CS   33

TFT_eSPI tft = TFT_eSPI();
SPIClass touchSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(XPT2046_CS, XPT2046_IRQ);

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

  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

  Serial.println("Touch pronto. Toque na tela.");
}

void loop() {
  if (touch.tirqTouched() && touch.touched()) {
    TS_Point p = touch.getPoint();

    // Mapeamento aproximado raw -> pixels (320x240 landscape)
    int16_t x = map(p.x, 200, 3700, 0, 320);
    int16_t y = map(p.y, 240, 3800, 0, 240);
    if (x < 0) x = 0;
    if (x > 319) x = 319;
    if (y < 0) y = 0;
    if (y > 239) y = 239;

    tft.fillCircle(x, y, 4, TFT_YELLOW);

    Serial.printf("raw(%d,%d) -> px(%d,%d) z=%d\n", p.x, p.y, x, y, p.z);
    delay(40);
  }
}
