#pragma once

#include <TFT_eSPI.h>
#include "config.h"
#include "lesson.h"

static int scrollY = 0;
static int bodyContentH = 0;
static String wrappedBody;

inline void uiShowSplash(TFT_eSPI &tft) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("DIARIO ESTOICO", tft.width() / 2, tft.height() / 2 - 12, 4);
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString("Etapa 1", tft.width() / 2, tft.height() / 2 + 20, 2);
  delay(700);
}

inline int uiBodyTop() { return HEADER_H + 4; }
inline int uiBodyBottom(TFT_eSPI &tft) { return tft.height() - FOOTER_H - 2; }
inline int uiBodyHeight(TFT_eSPI &tft) { return uiBodyBottom(tft) - uiBodyTop(); }

inline String uiWrapText(TFT_eSPI &tft, const String &src, int maxWidth) {
  String out;
  String line;
  int start = 0;
  while (start < (int)src.length()) {
    int nextNl = src.indexOf('\n', start);
    String para = (nextNl < 0) ? src.substring(start) : src.substring(start, nextNl);
    start = (nextNl < 0) ? src.length() : nextNl + 1;

    if (para.length() == 0) {
      out += "\n";
      continue;
    }

    line = "";
    int i = 0;
    while (i < (int)para.length()) {
      int sp = para.indexOf(' ', i);
      String word = (sp < 0) ? para.substring(i) : para.substring(i, sp);
      String trial = line.length() ? line + " " + word : word;
      if (tft.textWidth(trial, 2) <= maxWidth) {
        line = trial;
      } else {
        if (line.length()) {
          out += line;
          out += "\n";
        }
        line = word;
      }
      if (sp < 0) break;
      i = sp + 1;
    }
    if (line.length()) {
      out += line;
      out += "\n";
    }
    out += "\n";
  }
  return out;
}

inline void uiDrawHeader(TFT_eSPI &tft, const LessonData &lesson) {
  tft.fillRect(0, 0, tft.width(), HEADER_H, TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(lesson.date, 8, 6, 2);

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  String title = lesson.title;
  if (tft.textWidth(title, 2) > tft.width() - 16) {
    // quebra título em 2 linhas simples
    int mid = title.length() / 2;
    int sp = title.lastIndexOf(' ', mid + 8);
    if (sp < 5) sp = mid;
    String t1 = title.substring(0, sp);
    String t2 = title.substring(sp + 1);
    tft.drawString(t1, 8, 26, 2);
    tft.drawString(t2, 8, 42, 2);
  } else {
    tft.drawString(title, 8, 30, 2);
  }
  tft.drawFastHLine(8, HEADER_H - 1, tft.width() - 16, TFT_DARKGREY);
}

inline void uiDrawTransport(TFT_eSPI &tft, bool paused) {
  int y = tft.height() - FOOTER_H;
  tft.fillRect(0, y, tft.width(), FOOTER_H, TFT_NAVY);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_NAVY);
  tft.drawString(paused ? "[ > ]  toque = play" : "[ || ]  toque = pause",
                 tft.width() / 2, y + FOOTER_H / 2, 2);
}

inline void uiSetStatus(TFT_eSPI &tft, const char *msg) {
  int y = tft.height() - FOOTER_H;
  tft.fillRect(0, y, tft.width(), FOOTER_H, TFT_NAVY);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_YELLOW, TFT_NAVY);
  tft.drawString(msg, tft.width() / 2, y + FOOTER_H / 2, 2);
}

inline void uiDrawBodyWindow(TFT_eSPI &tft) {
  int top = uiBodyTop();
  int h = uiBodyHeight(tft);
  tft.fillRect(0, top, tft.width(), h, TFT_BLACK);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

  int lineH = 16;
  int firstLine = scrollY / lineH;
  int pixelOffset = scrollY % lineH;
  int y = top - pixelOffset;

  int lineStart = 0;
  int lineIdx = 0;
  while (lineStart <= (int)wrappedBody.length()) {
    int nl = wrappedBody.indexOf('\n', lineStart);
    String line = (nl < 0) ? wrappedBody.substring(lineStart)
                           : wrappedBody.substring(lineStart, nl);
    if (lineIdx >= firstLine) {
      if (y >= top - lineH && y < top + h) {
        if (y >= top) {
          tft.drawString(line, 8, y, 2);
        }
      }
      y += lineH;
      if (y > top + h) break;
    }
    if (nl < 0) break;
    lineStart = nl + 1;
    lineIdx++;
  }
}

inline void uiShowLesson(TFT_eSPI &tft, const LessonData &lesson) {
  scrollY = 0;
  tft.fillScreen(TFT_BLACK);
  uiDrawHeader(tft, lesson);
  wrappedBody = uiWrapText(tft, lesson.body, tft.width() - 16);

  // altura aproximada do conteúdo
  int lines = 1;
  for (unsigned i = 0; i < wrappedBody.length(); i++) {
    if (wrappedBody[i] == '\n') lines++;
  }
  bodyContentH = lines * 16;
  uiDrawBodyWindow(tft);
  uiDrawTransport(tft, true);
}

inline void uiScrollStep(TFT_eSPI &tft, const LessonData &lesson) {
  (void)lesson;
  int maxScroll = bodyContentH - uiBodyHeight(tft);
  if (maxScroll < 0) maxScroll = 0;
  if (scrollY >= maxScroll) return;
  scrollY += SCROLL_PIXELS;
  if (scrollY > maxScroll) scrollY = maxScroll;
  uiDrawBodyWindow(tft);
}
