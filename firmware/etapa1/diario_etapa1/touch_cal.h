#pragma once

#include <Arduino.h>
#include <FS.h>

struct TouchCal {
  int16_t raw[4][2];  // TL, TR, BL, BR
  bool valid = false;

  void useDefaults() {
    // Valores típicos CYD landscape — substituídos se houver touch.cal
    raw[0][0] = 200;  raw[0][1] = 240;
    raw[1][0] = 3700; raw[1][1] = 240;
    raw[2][0] = 200;  raw[2][1] = 3800;
    raw[3][0] = 3700; raw[3][1] = 3800;
    valid = true;
  }

  bool loadFromSd(fs::FS &fs) {
    File f = fs.open("/system/touch.cal", FILE_READ);
    if (!f) return false;
    for (int i = 0; i < 4; i++) {
      if (f.available() <= 0) {
        f.close();
        return false;
      }
      raw[i][0] = f.parseInt();
      raw[i][1] = f.parseInt();
    }
    f.close();
    valid = true;
    return true;
  }

  bool saveToSd(fs::FS &fs) {
    if (!fs.exists("/system")) {
      fs.mkdir("/system");
    }
    File f = fs.open("/system/touch.cal", FILE_WRITE);
    if (!f) return false;
    for (int i = 0; i < 4; i++) {
      f.printf("%d %d\n", raw[i][0], raw[i][1]);
    }
    f.close();
    return true;
  }

  void mapToScreen(int16_t rx, int16_t ry, int16_t &x, int16_t &y,
                   int16_t w, int16_t h) const {
    float xMin = (raw[0][0] + raw[2][0]) / 2.0f;
    float xMax = (raw[1][0] + raw[3][0]) / 2.0f;
    float yMin = (raw[0][1] + raw[1][1]) / 2.0f;
    float yMax = (raw[2][1] + raw[3][1]) / 2.0f;

    float nx = (rx - xMin) / (xMax - xMin);
    float ny = (ry - yMin) / (yMax - yMin);
    x = (int16_t)(nx * (w - 1));
    y = (int16_t)(ny * (h - 1));
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x >= w) x = w - 1;
    if (y >= h) y = h - 1;
  }
};
