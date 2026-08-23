#pragma once

#include <Arduino.h>
#include <FS.h>
#include <ArduinoJson.h>
#include "config.h"

struct LessonData {
  int id = 0;
  String date;
  String title;
  String quoteText;
  String quoteSource;
  String quotePhilosopher;
  String reflection;
  String body;  // citação + reflexão para a tela
};

inline bool lessonLoadFromSd(fs::FS &fs, const char *path, LessonData &out) {
  File f = fs.open(path, FILE_READ);
  if (!f) return false;

  // Documento JSON da lição (texto longo)
  DynamicJsonDocument doc(24 * 1024);
  DeserializationError err = deserializeJson(doc, f);
  f.close();
  if (err) {
    Serial.printf("JSON erro: %s\n", err.c_str());
    return false;
  }

  out.id = doc["id"] | 0;
  out.date = doc["date"] | "";
  out.title = doc["title"] | "";
  out.quoteText = doc["quote"]["text"] | "";
  out.quoteSource = doc["quote"]["source"] | "";
  out.quotePhilosopher = doc["quote"]["philosopher"] | "";
  out.reflection = doc["text"] | "";

  out.body = "";
  if (out.quoteText.length()) {
    out.body += out.quoteText;
    if (out.quoteSource.length()) {
      out.body += "\n\n";
      out.body += out.quoteSource;
    }
    out.body += "\n\n";
  }
  out.body += out.reflection;

  if (out.body.length() > BODY_MAX_CHARS) {
    out.body = out.body.substring(0, BODY_MAX_CHARS);
  }
  return out.title.length() > 0;
}
