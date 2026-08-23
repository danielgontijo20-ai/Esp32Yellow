// ============================================================
// Diário Estoico — Etapa 1
// Placa: ESP32-2432S028R (driver ST7789 no User_Setup.h)
// Caixa: JBL CINEMA SB110
//
// SD (FAT32):
//   lessons/007.json
//   audio/007.mp3          (44.1 kHz stereo recomendado)
//   system/touch.cal       (opcional — gerado pelo 03b)
//
// Bibliotecas:
//   TFT_eSPI, XPT2046_Touchscreen, ArduinoJson,
//   ESP32-A2DP, ESP8266Audio
// ============================================================

#include <Arduino.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>
#include <ArduinoJson.h>

#include "AudioFileSourceSD.h"
#include "AudioGeneratorMP3.h"
#include "AudioOutput.h"
#include "BluetoothA2DPSource.h"

#include "config.h"
#include "touch_cal.h"
#include "lesson.h"
#include "ui.h"
#include "audio_bt.h"

TFT_eSPI tft = TFT_eSPI();
SPIClass sharedSPI = SPIClass(VSPI);
XPT2046_Touchscreen touch(TOUCH_CS, TOUCH_IRQ);

LessonData lesson;
TouchCal touchCal;
AudioPlayer audioPlayer;

bool uiPaused = false;
bool lessonReady = false;
unsigned long lastScrollMs = 0;
unsigned long lastTouchMs = 0;

void drawError(const char *msg) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_RED, TFT_BLACK);
  tft.drawString("Erro", 10, 10, 4);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString(msg, 10, 60, 2);
  Serial.println(msg);
}

bool initSd() {
  sharedSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS, sharedSPI)) {
    return false;
  }
  return true;
}

bool initTouch() {
  // Touch no mesmo VSPI (CS diferente do SD)
  touch.begin(sharedSPI);
  touch.setRotation(1);
  if (!touchCal.loadFromSd(SD)) {
    Serial.println("Sem system/touch.cal — usando mapeamento padrao");
    touchCal.useDefaults();
  } else {
    Serial.println("Calibracao touch carregada do SD");
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("Diario Estoico — Etapa 1");

  pinMode(TFT_BL_PIN, OUTPUT);
  digitalWrite(TFT_BL_PIN, HIGH);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  uiShowSplash(tft);

  if (!initSd()) {
    drawError("Falha no SD");
    return;
  }

  initTouch();

  char jsonPath[48];
  char mp3Path[48];
  snprintf(jsonPath, sizeof(jsonPath), "/lessons/%03d.json", LESSON_ID);
  snprintf(mp3Path, sizeof(mp3Path), "/audio/%03d.mp3", LESSON_ID);

  if (!SD.exists(jsonPath)) {
    drawError("JSON da licao nao encontrado");
    Serial.println(jsonPath);
    return;
  }

  if (!lessonLoadFromSd(SD, jsonPath, lesson)) {
    drawError("Falha ao ler JSON");
    return;
  }

  uiShowLesson(tft, lesson);
  lessonReady = true;

  // Bluetooth + MP3 (se o arquivo existir)
  if (SD.exists(mp3Path)) {
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("Conectando JBL...", 10, tft.height() - 22, 2);
    if (!audioPlayer.begin(BT_SPEAKER_NAME, mp3Path)) {
      Serial.println("Audio/BT falhou — seguindo so texto");
      uiSetStatus(tft, "Sem audio / so texto");
    } else {
      uiSetStatus(tft, "Tocando");
      uiPaused = false;
    }
  } else {
    Serial.println("MP3 nao encontrado — modo texto");
    uiSetStatus(tft, "Sem MP3 — so texto");
  }

  lastScrollMs = millis();
}

void handleTouch() {
  if (!(touch.tirqTouched() && touch.touched())) return;
  if (millis() - lastTouchMs < 350) return;
  lastTouchMs = millis();

  TS_Point p = touch.getPoint();
  int16_t x, y;
  touchCal.mapToScreen(p.x, p.y, x, y, tft.width(), tft.height());

  // Toque em qualquer lugar: pause / play
  if (!audioPlayer.isActive()) {
    Serial.printf("Toque em %d,%d (sem audio)\n", x, y);
    return;
  }

  uiPaused = !uiPaused;
  audioPlayer.setPaused(uiPaused);
  uiSetStatus(tft, uiPaused ? "Pausado" : "Tocando");
  uiDrawTransport(tft, uiPaused);
  Serial.println(uiPaused ? "PAUSE" : "PLAY");
}

void loop() {
  if (!lessonReady) {
    delay(100);
    return;
  }

  audioPlayer.loop();
  handleTouch();

  // Rolagem automatica do texto (pausa junto com o audio, se houver)
  bool shouldScroll = true;
  if (audioPlayer.isActive() && uiPaused) shouldScroll = false;

  if (shouldScroll && millis() - lastScrollMs >= SCROLL_INTERVAL_MS) {
    lastScrollMs = millis();
    uiScrollStep(tft, lesson);
  }

  // Fim do audio
  if (audioPlayer.isActive() && audioPlayer.finished()) {
    uiSetStatus(tft, "Fim da narracao");
    uiDrawTransport(tft, true);
  }
}
