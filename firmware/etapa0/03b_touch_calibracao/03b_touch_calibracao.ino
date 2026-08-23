/*
 * Etapa 0.3b — Calibração CONFIÁVEL (anti toque fantasma)
 * Placa: ESP32-2432S028R
 *
 * COMO USAR (importante):
 * 1) Coloque o dedo no alvo amarelo
 * 2) Sem soltar, aperte o botão BOOT da placa (ao lado do USB)
 * 3) Solte o dedo e vá ao próximo canto
 *
 * O toque sozinho NÃO avança — só o BOOT confirma.
 * SD só é montado no final, para salvar /system/touch.cal
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
#define BOOT_BTN 0

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
  {"1/4 SUPERIOR ESQUERDO", 20, 20, 0, 0},
  {"2/4 SUPERIOR DIREITO", 0, 20, 0, 0},
  {"3/4 INFERIOR ESQUERDO", 20, 0, 0, 0},
  {"4/4 INFERIOR DIREITO", 0, 0, 0, 0},
};

int step = 0;
bool calibrated = false;
bool bootWasUp = true;
unsigned long lastCaptureMs = 0;

void drawPrompt(const char *msg = nullptr) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Calibracao (BOOT)", 10, 6, 2);

  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(corners[step].name, 10, 32, 2);

  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("1) Dedo no alvo amarelo", 10, 60, 2);
  tft.drawString("2) Aperte o botao BOOT", 10, 84, 2);

  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString("BOOT = botao ao lado do USB", 10, 112, 2);

  if (msg) {
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    tft.drawString(msg, 10, 140, 2);
  }

  int16_t ax = corners[step].screenX;
  int16_t ay = corners[step].screenY;
  tft.drawLine(ax - 16, ay, ax + 16, ay, TFT_YELLOW);
  tft.drawLine(ax, ay - 16, ax, ay + 16, TFT_YELLOW);
  tft.fillCircle(ax, ay, 5, TFT_YELLOW);
}

bool readTouchRaw(int16_t &rx, int16_t &ry) {
  // Média de várias leituras; se SPI estiver ruidoso, ainda assim
  // só confirma com BOOT.
  digitalWrite(XPT2046_CS, HIGH);
  delay(2);

  long sx = 0, sy = 0, sz = 0;
  int n = 0;
  for (int i = 0; i < 20; i++) {
    if (touch.touched()) {
      TS_Point p = touch.getPoint();
      sx += p.x;
      sy += p.y;
      sz += p.z;
      n++;
    }
    delay(3);
  }
  if (n < 5) return false;
  rx = sx / n;
  ry = sy / n;
  // z médio muito baixo = sem toque real
  if ((sz / n) < 200) return false;
  return true;
}

bool saveCalibrationToSd() {
  // Monta SD só agora (evita conflito SPI durante a calibração)
  SPIClass sdSPI = SPIClass(VSPI);
  sdSPI.begin(18, 19, 23, SD_CS);
  if (!SD.begin(SD_CS, sdSPI)) {
    Serial.println("SD falhou ao salvar");
    return false;
  }
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

  // Reabre touch SPI após uso do SD
  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Calibrado!", 10, 10, 4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("Toque para testar", 10, 55, 2);
  tft.setTextColor(saved ? TFT_GREEN : TFT_YELLOW, TFT_BLACK);
  tft.drawString(saved ? "Salvo: /system/touch.cal" : "Falha ao salvar SD", 10, 90, 2);

  Serial.println("==== CALIBRACAO ====");
  for (int i = 0; i < 4; i++) {
    Serial.printf("%d raw=(%d,%d)\n", i + 1, corners[i].rawX, corners[i].rawY);
  }
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
  pinMode(BOOT_BTN, INPUT_PULLUP);
  pinMode(XPT2046_CS, OUTPUT);
  digitalWrite(XPT2046_CS, HIGH);
  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);  // SD desativado durante calibração

  tft.init();
  tft.setRotation(1);

  corners[1].screenX = tft.width() - 20;
  corners[2].screenY = tft.height() - 20;
  corners[3].screenX = tft.width() - 20;
  corners[3].screenY = tft.height() - 20;

  // SOMENTE touch no VSPI (SD fica off)
  touchSPI.begin(XPT2046_CLK, XPT2046_MISO, XPT2046_MOSI, XPT2046_CS);
  touch.begin(touchSPI);
  touch.setRotation(1);

  drawPrompt();
  Serial.println("Calibracao por BOOT. Dedo no alvo + botao BOOT.");
}

void loop() {
  // Teste após calibrar
  if (calibrated) {
    if (touch.touched()) {
      TS_Point p = touch.getPoint();
      int16_t x, y;
      mapCalibrated(p.x, p.y, x, y);
      tft.fillCircle(x, y, 4, TFT_YELLOW);
      delay(20);
    }
    return;
  }

  bool bootDown = digitalRead(BOOT_BTN) == LOW;
  if (bootDown && bootWasUp && (millis() - lastCaptureMs > 600)) {
    bootWasUp = false;
    lastCaptureMs = millis();

    int16_t rx, ry;
    drawPrompt("Lendo toque...");
    bool ok = readTouchRaw(rx, ry);
    if (!ok) {
      drawPrompt("Sem toque! Dedo no alvo + BOOT");
      Serial.println("BOOT sem toque valido");
      return;
    }

    corners[step].rawX = rx;
    corners[step].rawY = ry;
    Serial.printf("Canto %d raw=(%d,%d)\n", step + 1, rx, ry);

    step++;
    if (step >= 4) {
      finishCalibration();
    } else {
      drawPrompt("Canto salvo! Proximo...");
      delay(500);
      drawPrompt();
    }
    return;
  }

  if (!bootDown) bootWasUp = true;
}
