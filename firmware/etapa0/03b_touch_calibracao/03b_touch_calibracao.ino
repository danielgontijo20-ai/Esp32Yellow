/*
 * Etapa 0.3b — Calibração do touch por 4 cantos
 * Placa: ESP32-2432S028R
 *
 * Como usar:
 * 1) Toque exatamente no canto indicado (alvo amarelo)
 * 2) Repita nos 4 cantos
 * 3) Depois teste: o ponto deve aparecer sob o dedo
 *
 * Se houver microSD FAT32, salva em /system/touch.cal
 * (usado pela Etapa 1).
 */

#include <SPI.h>
#include <SD.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>

#define XPT2046_IRQ  36
#define XPT2046_MOSI 32
#define XPT2046_MISO 39
#define XPT2046_CLK  25
#define XPT2046_CS   33

#define SD_CS 5

TFT_eSPI tft = TFT_eSPI();
SPIClass sharedSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(XPT2046_CS, XPT2046_IRQ);

struct Corner {
  const char *name;
  int16_t screenX;
  int16_t screenY;
  int16_t rawX;
  int16_t rawY;
  bool done;
};

Corner corners[4] = {
  {"Canto SUPERIOR ESQUERDO", 20, 20, 0, 0, false},
  {"Canto SUPERIOR DIREITO", 0, 20, 0, 0, false},
  {"Canto INFERIOR ESQUERDO", 20, 0, 0, 0, false},
  {"Canto INFERIOR DIREITO", 0, 0, 0, 0, false},
};

int step = 0;
bool calibrated = false;
unsigned long lastTouchMs = 0;
bool sdOk = false;

int16_t mapFloat(int16_t v, float inMin, float inMax, float outMin, float outMax) {
  float t = (float)(v - inMin) / (inMax - inMin);
  return (int16_t)(outMin + t * (outMax - outMin));
}

bool saveCalibrationToSd() {
  if (!sdOk) return false;
  if (!SD.exists("/system")) SD.mkdir("/system");
  File f = SD.open("/system/touch.cal", FILE_WRITE);
  if (!f) return false;
  for (int i = 0; i < 4; i++) {
    f.printf("%d %d\n", corners[i].rawX, corners[i].rawY);
  }
  f.close();
  return true;
}

void drawPrompt() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Calibracao do touch", 10, 8, 2);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(corners[step].name, 10, 40, 2);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString("Toque no alvo amarelo", 10, 70, 2);

  int16_t ax = corners[step].screenX;
  int16_t ay = corners[step].screenY;
  tft.drawLine(ax - 12, ay, ax + 12, ay, TFT_YELLOW);
  tft.drawLine(ax, ay - 12, ax, ay + 12, TFT_YELLOW);
  tft.fillCircle(ax, ay, 4, TFT_YELLOW);
}

void finishCalibration() {
  calibrated = true;
  bool saved = saveCalibrationToSd();

  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Calibrado!", 10, 10, 2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Toque para testar", 10, 40, 2);
  tft.setTextColor(saved ? TFT_GREEN : TFT_YELLOW, TFT_BLACK);
  tft.drawString(saved ? "Salvo: /system/touch.cal" : "SD ausente (nao salvou)", 10, 70, 2);

  Serial.println("==== CALIBRACAO ====");
  for (int i = 0; i < 4; i++) {
    Serial.printf("%s -> raw(%d,%d) screen(%d,%d)\n",
                  corners[i].name, corners[i].rawX, corners[i].rawY,
                  corners[i].screenX, corners[i].screenY);
  }
  Serial.println(saved ? "Salvo em /system/touch.cal" : "Nao salvou no SD");
  Serial.println("====================");
}

bool readStableTouch(int16_t &rx, int16_t &ry) {
  if (!(touch.tirqTouched() && touch.touched())) return false;
  if (millis() - lastTouchMs < 400) return false;

  long sx = 0, sy = 0;
  int n = 0;
  for (int i = 0; i < 16; i++) {
    if (touch.touched()) {
      TS_Point p = touch.getPoint();
      sx += p.x;
      sy += p.y;
      n++;
    }
    delay(5);
  }
  if (n < 8) return false;

  rx = sx / n;
  ry = sy / n;
  lastTouchMs = millis();
  return true;
}

void mapCalibrated(int16_t rx, int16_t ry, int16_t &x, int16_t &y) {
  float xMin = (corners[0].rawX + corners[2].rawX) / 2.0f;
  float xMax = (corners[1].rawX + corners[3].rawX) / 2.0f;
  float yMin = (corners[0].rawY + corners[1].rawY) / 2.0f;
  float yMax = (corners[2].rawY + corners[3].rawY) / 2.0f;

  x = mapFloat(rx, xMin, xMax, 0, tft.width() - 1);
  y = mapFloat(ry, yMin, yMax, 0, tft.height() - 1);

  if (x < 0) x = 0;
  if (y < 0) y = 0;
  if (x >= tft.width()) x = tft.width() - 1;
  if (y >= tft.height()) y = tft.height() - 1;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);

  corners[1].screenX = tft.width() - 20;
  corners[2].screenY = tft.height() - 20;
  corners[3].screenX = tft.width() - 20;
  corners[3].screenY = tft.height() - 20;

  sharedSPI.begin(18, 19, 23, SD_CS);
  sdOk = SD.begin(SD_CS, sharedSPI);
  Serial.println(sdOk ? "SD OK" : "SD ausente");

  touch.begin(sharedSPI);
  touch.setRotation(1);

  drawPrompt();
  Serial.println("Inicie a calibracao tocando nos alvos.");
}

void loop() {
  int16_t rx, ry;
  if (!readStableTouch(rx, ry)) return;

  if (!calibrated) {
    corners[step].rawX = rx;
    corners[step].rawY = ry;
    corners[step].done = true;
    Serial.printf("Ponto %d raw=(%d,%d)\n", step, rx, ry);
    step++;
    if (step >= 4) {
      finishCalibration();
    } else {
      drawPrompt();
    }
    return;
  }

  int16_t x, y;
  mapCalibrated(rx, ry, x, y);
  tft.fillCircle(x, y, 4, TFT_YELLOW);
  Serial.printf("test raw(%d,%d) -> px(%d,%d)\n", rx, ry, x, y);
}
