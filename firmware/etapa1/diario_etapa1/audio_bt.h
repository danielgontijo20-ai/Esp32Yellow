#pragma once

#include <Arduino.h>
#include "AudioFileSourceSD.h"
#include "AudioGeneratorMP3.h"
#include "AudioOutput.h"
#include "BluetoothA2DPSource.h"

// Saída que alimenta um ring buffer PCM 16-bit stereo para o A2DP
class AudioOutputRing : public AudioOutput {
 public:
  static const int FRAMES = 4096;
  int16_t left[FRAMES];
  int16_t right[FRAMES];
  volatile int head = 0;
  volatile int tail = 0;
  bool paused = false;

  bool begin() override { return true; }
  bool stop() override { return true; }

  bool ConsumeSample(int16_t sample[2]) override {
    if (paused) return true;
    int next = (head + 1) % FRAMES;
    // Se cheio, sinaliza backpressure
    if (next == tail) return false;
    left[head] = sample[0];
    right[head] = sample[1];
    head = next;
    return true;
  }

  int availableFrames() const {
    int h = head;
    int t = tail;
    if (h >= t) return h - t;
    return FRAMES - (t - h);
  }

  bool pop(int16_t &l, int16_t &r) {
    if (tail == head) return false;
    l = left[tail];
    r = right[tail];
    tail = (tail + 1) % FRAMES;
    return true;
  }
};

class AudioPlayer {
 public:
  BluetoothA2DPSource a2dp;
  AudioOutputRing out;
  AudioFileSourceSD *file = nullptr;
  AudioGeneratorMP3 *mp3 = nullptr;
  bool started = false;
  bool done = false;
  String path;

  static AudioPlayer *instance;

  static int32_t framesCallback(Frame *frame, int32_t count) {
    AudioPlayer *self = AudioPlayer::instance;
    if (!self) return count;
    for (int i = 0; i < count; i++) {
      int16_t l = 0, r = 0;
      if (!self->out.paused) {
        if (!self->out.pop(l, r)) {
          // underrun: silêncio
          l = 0;
          r = 0;
        }
      }
      frame[i].channel1 = l;
      frame[i].channel2 = r;
    }
    return count;
  }

  bool begin(const char *btName, const char *mp3Path) {
    instance = this;
    path = mp3Path;
    out.paused = false;
    done = false;

    file = new AudioFileSourceSD(mp3Path);
    if (!file || !file->isOpen()) {
      Serial.println("Nao abriu MP3");
      return false;
    }
    mp3 = new AudioGeneratorMP3();
    if (!mp3->begin(file, &out)) {
      Serial.println("MP3 begin falhou");
      return false;
    }

    a2dp.set_volume(80);
    a2dp.start(btName, framesCallback);
    started = true;
    Serial.printf("BT+MP3 iniciado: %s\n", mp3Path);
    return true;
  }

  void loop() {
    if (!started || !mp3) return;
    if (out.paused) return;
    if (mp3->isRunning()) {
      if (!mp3->loop()) {
        mp3->stop();
        done = true;
        Serial.println("MP3 terminou");
      }
    } else {
      done = true;
    }
  }

  void setPaused(bool p) { out.paused = p; }
  bool isActive() const { return started; }
  bool finished() const { return done; }
};

AudioPlayer *AudioPlayer::instance = nullptr;
