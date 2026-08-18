/*
 * Etapa 0.4 — Teste do cartão microSD
 * Placa: ESP32-2432S028R
 *
 * Pinos SD (VSPI): CS=5, MOSI=23, MISO=19, SCK=18
 *
 * Sucesso: "SD OK" na tela e lista de arquivos no Serial/tela.
 * Insira o cartão FAT32 com a placa DESLIGADA.
 */

#include <SPI.h>
#include <SD.h>
#include <TFT_eSPI.h>

#define SD_CS 5

TFT_eSPI tft = TFT_eSPI();

void drawStatus(const char *msg, uint16_t color) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(color, TFT_BLACK);
  tft.drawString(msg, 10, 10, 2);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(21, OUTPUT);
  digitalWrite(21, HIGH);

  tft.init();
  tft.setRotation(1);
  drawStatus("Iniciando SD...", TFT_YELLOW);

  // SD na VSPI padrão da CYD
  SPIClass sdSPI = SPIClass(VSPI);
  sdSPI.begin(18, 19, 23, SD_CS);

  if (!SD.begin(SD_CS, sdSPI)) {
    Serial.println("Falha ao montar SD");
    drawStatus("SD FALHOU", TFT_RED);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Cheque FAT32 / cartao", 10, 50, 2);
    return;
  }

  Serial.println("SD OK");
  drawStatus("SD OK", TFT_GREEN);

  uint64_t cardSize = SD.cardSize() / (1024 * 1024);
  char line[48];
  snprintf(line, sizeof(line), "Tamanho: %llu MB", cardSize);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString(line, 10, 40, 2);

  File root = SD.open("/");
  if (!root) {
    tft.drawString("Nao abriu raiz", 10, 70, 2);
    return;
  }

  int y = 70;
  File file = root.openNextFile();
  int count = 0;
  while (file && y < 220) {
    String name = file.name();
    Serial.println(name);
    tft.drawString(name.substring(0, 36), 10, y, 2);
    y += 18;
    count++;
    file = root.openNextFile();
  }
  root.close();

  if (count == 0) {
    tft.drawString("(raiz vazia - OK)", 10, 70, 2);
  }
}

void loop() {
  // nada
}
