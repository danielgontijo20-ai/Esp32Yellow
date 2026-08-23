// ============================================================
// TFT_eSPI — setup para ESP32-2432S028R (Cheap Yellow Display)
//
// COMO USAR:
// 1) Abra: Documentos\Arduino\libraries\TFT_eSPI\User_Setup.h
// 2) Faça backup do arquivo atual
// 3) Substitua TODO o conteúdo de User_Setup.h por este arquivo
// 4) Salve e recompile o sketch de tela
// ============================================================

#define USER_SETUP_INFO "ESP32-2432S028R CYD"

#define ILI9341_DRIVER

#define TFT_WIDTH  240
#define TFT_HEIGHT 320

#define TFT_MISO 12
#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_CS   15
#define TFT_DC    2
#define TFT_RST  -1
#define TFT_BL   21
#define TFT_BACKLIGHT_ON HIGH

#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SMOOTH_FONT

#define SPI_FREQUENCY  40000000
#define SPI_READ_FREQUENCY  20000000
#define SPI_TOUCH_FREQUENCY  2500000

#define USE_HSPI_PORT
