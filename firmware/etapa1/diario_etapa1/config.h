#pragma once

// Lição fixa da Etapa 1 (depois virá o sorteio / Filosofar)
#ifndef LESSON_ID
#define LESSON_ID 7
#endif

// Bluetooth
static const char *BT_SPEAKER_NAME = "JBL CINEMA SB110";

// Pinos CYD
#define TFT_BL_PIN 21

#define TOUCH_IRQ  36
#define TOUCH_MOSI 32
#define TOUCH_MISO 39
#define TOUCH_CLK  25
#define TOUCH_CS   33

#define SD_CS   5
#define SD_MOSI 23
#define SD_MISO 19
#define SD_SCK  18

// UI
#define HEADER_H     58
#define FOOTER_H     28
#define SCROLL_INTERVAL_MS 80
#define SCROLL_PIXELS 1

// Texto
#define BODY_MAX_CHARS 3500
