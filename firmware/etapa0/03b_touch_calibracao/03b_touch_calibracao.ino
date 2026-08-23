/*
 * Etapa 0.3b — Calibração do touch por 4 cantos (versão estável)
 * Placa: ESP32-2432S028R
 *
 * Regras anti-falso-toque:
 * - precisa pressionar o alvo por ~0,4s
 * - precisa SOLTAR o dedo antes do próximo canto
 * - espera 1s entre cantos
 *
 * Com SD FAT32, salva em /system/touch.cal
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

// Pressão mínima (z) — aumente se ainda "clicar sozinho"
#define MIN_PRESSURE 400
#define HOLD_MS 400
#define GAP_MS 1000

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
long accX = 0, accY = 0;
int accN = 0;

void drawPrompt() {
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

  if (waitingRelease) {
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.drawString("Solte o dedo para continuar...", 10, 120, 2);
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
  // remove antigo
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

bool touchedNow(TS_Point &p) {
  if (!(touch.tirqTouched() && touch.touched())) return false;
  p = touch.getPoint();
  if (p.z < MIN_PRESSURE) return false;
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

  // Se já existe calibração ruim, avisa
  if (sdOk && SD.exists("/system/touch.cal")) {
    Serial.println("AVISO: touch.cal antigo sera sobrescrito ao terminar");
  }

  touch.begin(sharedSPI);
  touch.setRotation(1);

  readyAtMs = millis() + 800;  // ignora toques nos primeiros 0,8s
  drawPrompt();
  Serial.println("Calibracao pronta. Pressione e segure cada alvo.");
}

void loop() {
  TS_Point p;

  // Modo teste depois de calibrar
  if (calibrated) {
    if (touchedNow(p)) {
      int16_t x, y;
      mapCalibrated(p.x, p.y, x, y);
      tft.fillCircle(x, y, 4, TFT_YELLOW);
      delay(30);
    }
    return;
  }

  if (millis() < readyAtMs) return;

  // Precisa soltar entre um canto e outro
  if (waitingRelease) {
    if (!touchedNow(p)) {
      waitingRelease = false;
      pressStartMs = 0;
      accX = accY = 0;
      accN = 0;
      readyAtMs = millis() + GAP_MS;
      drawPrompt();
      Serial.println("Dedo solto. Proximo canto...");
    }
    return;
  }

  if (touchedNow(p)) {
    if (pressStartMs == 0) {
      pressStartMs = millis();
      accX = 0;
      accY = 0;
      accN = 0;
    }
    accX += p.x;
    accY += p.y;
    accN++;

    // barra de progresso visual simples
    unsigned long held = millis() - pressStartMs;
    int bar = (int)(held * 200 / HOLD_MS);
    if (bar > 200) bar = 200;
    tft.fillRect(10, 150, 200, 12, TFT_DARKGREY);
    tft.fillRect(10, 150, bar, 12, TFT_GREEN);

    if (held >= HOLD_MS && accN >= 8) {
      corners[step].rawX = accX / accN;
      corners[step].rawY = accY / accN;
      Serial.printf("Canto %d salvo raw=(%d,%d)\n",
                    step + 1, corners[step].rawX, corners[step].rawY);

      step++;
      pressStartMs = 0;
      accX = accY = 0;
      accN = 0;

      if (step >= 4) {
        finishCalibration();
      } else {
        waitingRelease = true;
        tft.setTextColor(TFT_ORANGE, TFT_BLACK);
        tft.drawString("Solte o dedo...", 10, 180, 2);
      }
    }
  } else {
    // soltou cedo demais: reinicia contagem
    if (pressStartMs != 0) {
      pressStartMs = 0;
      accX = accY = 0;
      accN = 0;
      tft.fillRect(10, 150, 200, 12, TFT_DARKGREY);
    }
  }
}
