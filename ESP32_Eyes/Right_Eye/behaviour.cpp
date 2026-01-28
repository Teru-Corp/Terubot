#include <Arduino.h>
#include "behaviour.h"
#include "Expressions.h"

// Output gaze
static float gazeX = 0.0f;        // current gaze
static float targetGazeX = 0.0f;  // target gaze
static float gazeY = 0.0f;        // current vertical gaze
static float targetGazeY = 0.0f;  // target vertical gaze

// Idle motion
static float idlePhase = 0.0f;
static float idleTarget = 0.0f;
static float idleTimer = 0.0f;

// Tuning
static const float GAZE_SMOOTH = 6.0f;     // higher = faster response
static const float IDLE_SPEED  = 0.6f;     // base sine speed
static const float IDLE_RANGE  = 0.35f;    // how far idle moves (0..1)
static const float IDLE_HOLD_MIN = 1.0f;   // seconds
static const float IDLE_HOLD_MAX = 2.5f;   // seconds

static float clampf(float v, float a, float b) {
  if (v < a) return a;
  if (v > b) return b;
  return v;
}

void behaviourActivate(char cmd) {
  // L/R/U/D/C override idle target immediately
  if (cmd == 'L') targetGazeX = -0.9f;
  if (cmd == 'R') targetGazeX =  0.9f;
  if (cmd == 'U') targetGazeY = -0.9f;
  if (cmd == 'D') targetGazeY =  0.9f;
  if (cmd == 'C') {
    targetGazeX = 0.0f;   // center
    targetGazeY = 0.0f;
  }

  // If you want expressions (H/S/N) to return to idle:
  if (cmd == 'H' || cmd == 'S' || cmd == 'N') {
    // go back to idle (don’t force center, just let idle take over)
    // (no action needed)
  }
}

void behaviourUpdate(float dt) {
  // --- Idle target logic (slow wandering) ---
  idleTimer -= dt;
  if (idleTimer <= 0.0f) {
    // pick a new idleTarget randomly within range
    float r = (float)random(-1000, 1001) / 1000.0f; // -1..1
    idleTarget = r * IDLE_RANGE;

    // next change after a little while
    float hold = (float)random((int)(IDLE_HOLD_MIN * 1000), (int)(IDLE_HOLD_MAX * 1000)) / 1000.0f;
    idleTimer = hold;
  }

  idlePhase += IDLE_SPEED * dt;

  // Combine a gentle sine with a slowly changing random target
  float idle = 0.15f * sinf(idlePhase) + idleTarget;

  // If user didn't recently force L/R/C, you can always drift on idle:
  // Here we "pull" target toward idle unless target is strongly set.
  // Simple approach: if target is close to center-ish, use idle.
  if (fabsf(targetGazeX) < 0.2f) {
    targetGazeX = idle;
  }

  // --- Smoothly approach target ---
  float a = clampf(GAZE_SMOOTH * dt, 0.0f, 1.0f);
  gazeX = gazeX + (targetGazeX - gazeX) * a;
  gazeY = gazeY + (targetGazeY - gazeY) * a;

  gazeX = clampf(gazeX, -1.0f, 1.0f);
  gazeY = clampf(gazeY, -1.0f, 1.0f);
}

float behaviourGetGazeX() {
  return gazeX;
}

float behaviourGetGazeY() {
  return gazeY;
}

void drawBaseEye(float cx, float cy, float m, float gazeX, float gazeY) {
  float R = 120.0f;

  // 1. Eye Base
  canvas->fillCircle((int)cx, (int)cy, (int)R, COL_EYE_BG);
  
  // 2. Iris (shifted by gaze)
  float irisOffsetX = gazeX * 30.0f; // gaze range: -30 to +30 pixels
  float irisOffsetY = gazeY * 30.0f;
  canvas->fillCircle((int)(cx - 5 + irisOffsetX), (int)(cy - 5 + irisOffsetY), 80, COL_IRIS);
  
  // 3. Highlights
  canvas->fillCircle((int)(cx - 40 + irisOffsetX), (int)(cy - 35 + irisOffsetY), 23, COL_WHITE); 
  canvas->fillCircle((int)(cx + 50 + irisOffsetX), (int)(cy + 55 + irisOffsetY), 8, COL_WHITE);  

  // 4. Morphing Lid
  for (int x = -120; x <= 120; x++) {
    float xf = (float)x;
    if (xf * xf <= R * R) {
      float semiY = sqrt(R * R - xf * xf);
      float arcY = (2.0f * m - 1.0f) * semiY;
      int startY = (int)(cy - semiY + 0.5f);
      int endY   = (int)(cy + arcY + 0.5f);

      if (endY > startY) {
        canvas->drawFastVLine((int)cx + x, startY, endY - startY, COL_LID);
        canvas->drawPixel((int)cx + x, endY, COL_LID_EDGE);
        canvas->drawPixel((int)cx + x, endY - 1, COL_LID_EDGE);
      }
    }
  }
}

void updateBlink(float &m, bool &isBlinking, float &blinkSpeed, unsigned long &nextBlinkTime, float dt) {
  unsigned long now = millis();
  if (!isBlinking && now > nextBlinkTime) isBlinking = true;

  if (isBlinking) {
    m += blinkSpeed * dt;
    if (m >= 1.0) { m = 1.0; blinkSpeed = -fabs(blinkSpeed); }
    if (m <= 0.0) {
      m = 0.0; 
      isBlinking = false; 
      blinkSpeed = fabs(blinkSpeed); 
      nextBlinkTime = now + random(1000, 5000); 
    }
  }
}
