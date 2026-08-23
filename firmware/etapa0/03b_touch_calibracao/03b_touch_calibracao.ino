/*
 * Etapa 0.3b — Calibração simples (versão que funcionou melhor)
 * Placa: ESP32-2432S028R
 *
 * Como usar:
 * 1) Toque no alvo amarelo de cada canto
 * 2) Espere ~1s entre um canto e outro
 * 3) No final testa o toque
 *
 * Salva/sobrescreve: /system/touch.cal
 * (SD só é usado no final, para não atrapalhar o touch)
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
SPIClass touchSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(XPT2046_CS, XPT2046_IRQ);

struct Corner {
  const char *name;
  int16_t screenX;
  int16_t screenY;
  int16_t rawX;
  int16_t rawY;
};

Corner corners[4] = {
  {"Canto SUPERIOR ESQUERDO", 20, 20, 0, 0},
  {"Canto SUPERIOR DIREITO", 0, 20, 0, 0},
  {"Canto INFERIOR ESQUERDO", 20, 0, 0, 0},
  {"Canto INFERIOR DIREITO", 0, 0, 0, 0},
};

int step = 0;
bool calibrated = false;
unsigned long lastTouchMs = 0;
unsigned long ignoreUntilMs = 0;

void drawPrompt() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Calibracao do touch", 10, 8, 2);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(corners[step].name, 10, 40, 2);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("Toque no alvo amarelo", 10, 70, 2);

  int16_t ax = corners[step].screenX;
  int16_t ay = corners[step].screenY;
  tft.drawLine(ax - 12, ay, ax + 12, ay, TFT_YELLOW);
  tft.drawLine(ax, ay - 12, ax, ay + 12, TFT_YELLOW);
  tft.fillCircle(ax, ay, 4, TFT_YELLOW);
}

bool saveCalibrationToSd() {
  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);

  SPIClass sdSPI = SPIClass(VSPI);
  sdSPI.begin(18, 19, 23, SD_CS);
  if (!SD.begin(SD_CS, sdSPI)) {
    Serial.println("SD falhou");
    return false;
  }
  if (!SD.exists("/system")) SD.mkdir("/system");

  // Sempre sobrescreve
  if (SD.exists("/system/touch.cal")) {
    SD.remove("/system/touch.cal");
  }

  File f = SD.open("/system/touch.cal", FILE_WRITE);
  if (!f) return false;
  for (int i = 0; i < 4; i++) {
    f.printf("%d %d\n", corners[i].rawX, corners[i].rawY);
  }
  f.flush();
  f.close();
  Serial.println("touch.cal sobrescrito");
  return true;
}

void finishCalibration() {
  calibrated = true;
  bool saved = saveCalibrationToSd();

  // Reativa o SPI do touch depois do SD
  digitalWrite(SD_CS, HIGH);
  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

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
    Serial.printf("%s -> raw(%d,%d)\n",
                  corners[i].name, corners[i].rawX, corners[i].rawY);
  }
}

bool readStableTouch(int16_t &rx, int16_t &ry) {
  if (!(touch.tirqTouched() && touch.touched())) return false;
  if (millis() - lastTouchMs < 700) return false;
  if (millis() < ignoreUntilMs) return false;

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

int16_t mapFloat(int16_t v, float inMin, float inMax, float outMin, float outMax) {
  if (inMax == inMin) return (int16_t)outMin;
  float t = (float)(v - inMin) / (inMax - inMin);
  return (int16_t)(outMin + t * (outMax - outMin));
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

  // Garante SD desligado durante a calibração
  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);

  tft.init();
  tft.setRotation(1);

  corners[1].screenX = tft.width() - 20;
  corners[2].screenY = tft.height() - 20;
  corners[3].screenX = tft.width() - 20;
  corners[3].screenY = tft.height() - 20;

  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

  ignoreUntilMs = millis() + 1000;  // 1s para a tela assentar
  drawPrompt();
  Serial.println("Calibracao simples pronta. Toque nos alvos.");
}

void loop() {
  int16_t rx, ry;

  if (calibrated) {
    if (touch.tirqTouched() && touch.touched()) {
      TS_Point p = touch.getPoint();
      int16_t x, y;
      mapCalibrated(p.x, p.y, x, y);
      tft.fillCircle(x, y, 4, TFT_YELLOW);
      delay(30);
    }
    return;
  }

  if (!readStableTouch(rx, ry)) return;

  corners[step].rawX = rx;
  corners[step].rawY = ry;
  Serial.printf("Ponto %d raw=(%d,%d)\n", step + 1, rx, ry);

  step++;
  if (step >= 4) {
    finishCalibration();
  } else {
    ignoreUntilMs = millis() + 900;
    drawPrompt();
  }
}
