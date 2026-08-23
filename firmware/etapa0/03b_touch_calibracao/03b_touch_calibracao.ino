/*
 * Etapa 0.3b — Calibração do touch por 4 cantos (versão estável)
 * Placa: ESP32-2432S028R
 *
 * - Segure o alvo ~0,5s (barrinha verde)
 * - Solte o dedo (ou espere 2s) para ir ao próximo canto
 * - Salva /system/touch.cal no SD
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

#define MIN_PRESSURE 600
#define HOLD_MS 500
#define GAP_MS 700
#define RELEASE_NEED 25          // leituras seguidas "solto"
#define RELEASE_TIMEOUT_MS 2000  // se travar, avança sozinho

TFT_eSPI tft = TFT_eSPI();
SPIClass sharedSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(XPT2046_CS, XPT2046_IRQ);

struct Corner {
  const char *name;
  int16_t screenX;
  int16_t screenY;
  int16_t rawX;
  int16_t rawY;
};

Corner corners[4] = {
  {"1/4 SUPERIOR ESQUERDO", 20, 20, 0, 0},
  {"2/4 SUPERIOR DIREITO", 0, 20, 0, 0},
  {"3/4 INFERIOR ESQUERDO", 20, 0, 0, 0},
  {"4/4 INFERIOR DIREITO", 0, 0, 0, 0},
};

int step = 0;
bool calibrated = false;
bool waitingRelease = false;
bool sdOk = false;
unsigned long pressStartMs = 0;
unsigned long readyAtMs = 0;
unsigned long releaseWaitStartMs = 0;
int releaseCount = 0;
long accX = 0, accY = 0;
int accN = 0;

bool isPressed(TS_Point &p) {
  // Nao usar so tirqTouched — na CYD ele pode ficar "preso"
  if (!touch.touched()) return false;
  p = touch.getPoint();
  return p.z >= MIN_PRESSURE;
}

void drawPrompt(const char *extra = nullptr) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Calibracao do touch", 10, 8, 2);

  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(corners[step].name, 10, 36, 2);

  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("Pressione o alvo e SEGURE", 10, 64, 2);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString("Depois SOLTE o dedo", 10, 88, 2);

  if (extra) {
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.drawString(extra, 10, 120, 2);
  }

  int16_t ax = corners[step].screenX;
  int16_t ay = corners[step].screenY;
  tft.drawLine(ax - 14, ay, ax + 14, ay, TFT_YELLOW);
  tft.drawLine(ax, ay - 14, ax, ay + 14, TFT_YELLOW);
  tft.fillCircle(ax, ay, 5, TFT_YELLOW);
}

bool saveCalibrationToSd() {
  if (!sdOk) return false;
  if (!SD.exists("/system")) SD.mkdir("/system");
  if (SD.exists("/system/touch.cal")) SD.remove("/system/touch.cal");
  File f = SD.open("/system/touch.cal", FILE_WRITE);
  if (!f) return false;
  for (int i = 0; i < 4; i++) {
    f.printf("%d %d\n", corners[i].rawX, corners[i].rawY);
  }
  f.close();
  return true;
}

void finishCalibration() {
  calibrated = true;
  bool saved = saveCalibrationToSd();

  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Calibrado!", 10, 10, 4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Toque para testar os pontos", 10, 55, 2);
  tft.setTextColor(saved ? TFT_GREEN : TFT_YELLOW, TFT_BLACK);
  tft.drawString(saved ? "Salvo: /system/touch.cal" : "SD ausente (nao salvou)", 10, 90, 2);

  Serial.println("==== CALIBRACAO ====");
  for (int i = 0; i < 4; i++) {
    Serial.printf("%d raw=(%d,%d)\n", i + 1, corners[i].rawX, corners[i].rawY);
  }
  Serial.println(saved ? "Salvo /system/touch.cal" : "Nao salvou SD");
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

void goNextCornerOrFinish() {
  step++;
  pressStartMs = 0;
  accX = accY = 0;
  accN = 0;
  releaseCount = 0;

  if (step >= 4) {
    finishCalibration();
    return;
  }
  waitingRelease = true;
  releaseWaitStartMs = millis();
  drawPrompt("Solte o dedo (ou espere 2s)...");
}

void setup() {
  Serial.begin(115200);
  delay(300);

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

  readyAtMs = millis() + 1000;
  drawPrompt();
  Serial.println("Calibracao pronta.");
}

void loop() {
  TS_Point p;

  if (calibrated) {
    if (isPressed(p)) {
      int16_t x, y;
      mapCalibrated(p.x, p.y, x, y);
      tft.fillCircle(x, y, 4, TFT_YELLOW);
      delay(30);
    }
    return;
  }

  if (millis() < readyAtMs) return;

  // Esperando soltar entre cantos
  if (waitingRelease) {
    bool down = isPressed(p);
    if (!down) {
      releaseCount++;
    } else {
      releaseCount = 0;
    }

    bool released = releaseCount >= RELEASE_NEED;
    bool timedOut = (millis() - releaseWaitStartMs) >= RELEASE_TIMEOUT_MS;

    if (released || timedOut) {
      waitingRelease = false;
      releaseCount = 0;
      readyAtMs = millis() + GAP_MS;
      drawPrompt(timedOut ? "Ok, proximo canto" : nullptr);
      Serial.println(timedOut ? "Timeout soltar — seguindo" : "Dedo solto");
    }
    return;
  }

  // Captura do canto atual
  if (isPressed(p)) {
    if (pressStartMs == 0) {
      pressStartMs = millis();
      accX = 0;
      accY = 0;
      accN = 0;
    }
    accX += p.x;
    accY += p.y;
    accN++;

    unsigned long held = millis() - pressStartMs;
    int bar = (int)(held * 200 / HOLD_MS);
    if (bar > 200) bar = 200;
    tft.fillRect(10, 150, 200, 12, TFT_DARKGREY);
    tft.fillRect(10, 150, bar, 12, TFT_GREEN);

    if (held >= HOLD_MS && accN >= 10) {
      corners[step].rawX = accX / accN;
      corners[step].rawY = accY / accN;
      Serial.printf("Canto %d raw=(%d,%d)\n", step + 1, corners[step].rawX, corners[step].rawY);
      goNextCornerOrFinish();
    }
  } else {
    if (pressStartMs != 0) {
      pressStartMs = 0;
      accX = accY = 0;
      accN = 0;
      tft.fillRect(10, 150, 200, 12, TFT_DARKGREY);
    }
  }
}
