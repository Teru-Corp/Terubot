#include <Arduino.h>
#include "Tracking.h"
#include "Motion.h"

extern float currentNod, currentTilt, currentPan;


// Tracking state
float trackPanOff = 0.0f;
float trackTiltOff = 0.0f;
static unsigned long lastTrackMs = 0;

// Safety / behavior
static const float TRACK_PAN_MAX  = 30.0f;
static const float TRACK_TILT_MAX = 20.0f;
static const unsigned long TRACK_TIMEOUT_MS = 350;
static const float TRACK_FADE = 0.90f;

void parseTrackingLine() {
  // We already consumed 'T'. Expect: ",12.3,-5.0\n"
  String rest = Serial.readStringUntil('\n');
  rest.trim();

  if (rest.length() == 0 || rest[0] != ',') return;

  int comma2 = rest.indexOf(',', 1);
  if (comma2 < 0) return;

  float p = rest.substring(1, comma2).toFloat();
  float t = rest.substring(comma2 + 1).toFloat();

  if (p >  TRACK_PAN_MAX)  p =  TRACK_PAN_MAX;
  if (p < -TRACK_PAN_MAX)  p = -TRACK_PAN_MAX;
  if (t >  TRACK_TILT_MAX) t =  TRACK_TILT_MAX;
  if (t < -TRACK_TILT_MAX) t = -TRACK_TILT_MAX;

  trackPanOff = p;
  trackTiltOff = t;
  lastTrackMs = millis();
}

void updateTrackingFade() {
  if (millis() - lastTrackMs > TRACK_TIMEOUT_MS) {
    trackPanOff  *= TRACK_FADE;
    trackTiltOff *= TRACK_FADE;
    if (abs(trackPanOff) < 0.2f) trackPanOff = 0.0f;
    if (abs(trackTiltOff) < 0.2f) trackTiltOff = 0.0f;
  }
}

void applyPoseWithTracking() {
  // If nothing is moving right now, we still want tracking to affect outputs.
  // Easiest safe way: do a tiny "refresh" by re-writing current pose via a very fast moveTo.
  // This keeps your logic unchanged and uses the same output path.
  updateTrackingFade();
  moveTo(currentNod, currentTilt, currentPan, 1.0f);
}
